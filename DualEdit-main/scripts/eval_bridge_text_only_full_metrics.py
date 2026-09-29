import argparse
import json
import os
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from time import time
import sys

import torch
from tqdm import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dataset.edit_bridge_loader import EditBridge  # noqa: E402
from editor.vllm_editors.vead.vead import VEAD, VEADConfig  # noqa: E402
from utils import load_vllm_for_edit  # noqa: E402


VISEDIT_ROOT = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
TEN_CLASSES_ROOT = "/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--config", required=True)
    parser.add_argument("--ckpt-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--eval-name", required=True)
    parser.add_argument("--bridge-root", default=os.path.join(TEN_CLASSES_ROOT, "bridge"))
    parser.add_argument("--coco-root", default=os.path.join(VISEDIT_ROOT, "data/easy-edit-mm/images"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--device", "-dvc", required=True)
    parser.add_argument("--data-n", "-dn", type=int, default=None)
    return parser.parse_args()


def set_decimal(value, decimal=4):
    if isinstance(value, list):
        return [set_decimal(item, decimal) for item in value]
    if isinstance(value, dict) or isinstance(value, defaultdict):
        return {key: set_decimal(item, decimal) for key, item in value.items()}
    if isinstance(value, float):
        return round(value, decimal)
    return value


def save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(set_decimal(payload), f, ensure_ascii=False, indent=2)
        f.write("\n")


def accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks):
    assert len(label_ids) == 1 and len(label_masks) == 1
    logits = vllm.get_llm_outpt(input_embeds, vt_range).logits
    pred_ids = torch.softmax(logits, -1).argmax(-1)
    pred_ids = pred_ids[:, -label_ids.shape[1] :]
    acc = ((pred_ids == label_ids) * label_masks).sum() / label_masks.sum()
    return float(acc), pred_ids


def set_prompt_end_for_text_adaptors(editor, prompt_end):
    prompt_end_tensor = torch.tensor([int(prompt_end)], device=editor.device)
    for adaptor in editor.adaptors.values():
        if hasattr(adaptor, "set_prompt_end"):
            adaptor.set_prompt_end(prompt_end_tensor)


def score_target(editor, tokenizer, item):
    (input_embeds, vt_range), label_ids, label_masks = editor.vllm.prompts_imgs_target_to_xym(
        [item["prompt"]], [item["image"]], [item["target"]]
    )
    prompt_end = input_embeds["inputs_embeds"].shape[1] - label_ids.shape[1]
    set_prompt_end_for_text_adaptors(editor, prompt_end)
    acc, pred_ids = accuracy_and_prediction(editor.vllm, input_embeds, vt_range, label_ids, label_masks)
    return acc, tokenizer.decode(pred_ids[label_masks.to(bool)])


def mean(values):
    return sum(values) / len(values) if values else None


def compute_mean_results(results):
    metric_values = {
        "reliability": defaultdict(list),
        "generality": defaultdict(lambda: defaultdict(list)),
        "locality": defaultdict(lambda: defaultdict(list)),
        "portability": defaultdict(lambda: defaultdict(list)),
    }

    for row in results:
        for key, value in row["reliability"].items():
            if isinstance(value, (int, float)):
                metric_values["reliability"][key].append(value)

        for group_name, items in row["generality"].items():
            for item in items:
                for key, value in item.items():
                    if isinstance(value, (int, float)):
                        metric_values["generality"][group_name][key].append(value)

        for group_name, items in row["locality"].items():
            for item in items:
                for key, value in item.items():
                    if isinstance(value, (int, float)):
                        metric_values["locality"][group_name][key].append(value)

        for group_name, items in row.get("portability", {}).items():
            for item in items:
                for key, value in item.items():
                    if isinstance(value, (int, float)):
                        metric_values["portability"][group_name][key].append(value)

    out = {"reliability": {}, "generality": {}, "locality": {}, "portability": {}, "metric_item_counts": {}}
    for key, values in metric_values["reliability"].items():
        out["reliability"][key] = mean(values)
    out["metric_item_counts"]["reliability"] = len(results)

    for metric_name in ["generality", "locality", "portability"]:
        all_acc_values = []
        out["metric_item_counts"][metric_name] = {}
        for group_name, group_values in metric_values[metric_name].items():
            out[metric_name][group_name] = {}
            out["metric_item_counts"][metric_name][group_name] = len(group_values.get("acc", []))
            for key, values in group_values.items():
                out[metric_name][group_name][key] = mean(values)
            all_acc_values.extend(group_values.get("acc", []))
        out[metric_name]["overall"] = {"acc": mean(all_acc_values)}
        out["metric_item_counts"][metric_name]["overall"] = len(all_acc_values)

    return out


def evaluate_full_metrics(editor, eval_data, eval_name, output_root):
    print("Evaluating request/generality/locality/portability for %s." % (editor.name_of_editor_and_model(),))
    editor_name, model_name = editor.name_of_editor_and_model()
    result_dir = os.path.join(output_root, editor_name, model_name, eval_name)

    eval_rows = deepcopy(eval_data.data_with_img)
    result_rows = deepcopy(eval_data.data_with_img_path)
    tokenizer = editor.vllm.get_llm_tokenizer()

    editor.restore_to_original_model()
    results = []

    for result_row, eval_row in zip(tqdm(result_rows, desc="Evaluating"), eval_rows):
        result_row["reliability"] = result_row.pop("request")
        result_row["reliability"]["target"] = result_row["reliability"].pop("target_new")

        for loc_name in eval_row["locality"].keys():
            for idx, loc_item in enumerate(eval_row["locality"][loc_name]):
                (input_embeds, vt_range), label_ids, label_masks = editor.vllm.prompts_imgs_target_to_xym(
                    [loc_item["prompt"]], [loc_item["image"]], [loc_item["target"]]
                )
                logits = editor.vllm.get_llm_outpt(input_embeds, vt_range).logits
                before_edit_ids = torch.softmax(logits, -1).argmax(-1)[:, -label_ids.shape[1] :]
                result_row["locality"][loc_name][idx]["predict_before_edit"] = tokenizer.decode(
                    before_edit_ids[label_masks.to(bool)]
                )
                loc_item["before_edit_ids"] = before_edit_ids

        start_t = time()
        editor.edit_one_piece(eval_row["request"])
        result_row["reliability"]["edit_time"] = time() - start_t

        request_item = {
            "image": eval_row["request"]["image"],
            "prompt": eval_row["request"]["prompt"],
            "target": eval_row["request"]["target_new"],
        }
        acc, pred = score_target(editor, tokenizer, request_item)
        result_row["reliability"]["predict_after_edit"] = pred
        result_row["reliability"]["acc"] = acc

        for gen_name in eval_row["generality"].keys():
            for idx, gen_item in enumerate(eval_row["generality"][gen_name]):
                acc, pred = score_target(editor, tokenizer, gen_item)
                result_row["generality"][gen_name][idx]["acc"] = acc
                result_row["generality"][gen_name][idx]["predict_after_edit"] = pred

        for loc_name in eval_row["locality"].keys():
            for idx, loc_item in enumerate(eval_row["locality"][loc_name]):
                (input_embeds, vt_range), _, label_masks = editor.vllm.prompts_imgs_target_to_xym(
                    [loc_item["prompt"]], [loc_item["image"]], [loc_item["target"]]
                )
                prompt_end = input_embeds["inputs_embeds"].shape[1] - label_masks.shape[1]
                set_prompt_end_for_text_adaptors(editor, prompt_end)
                acc, pred_ids = accuracy_and_prediction(
                    editor.vllm, input_embeds, vt_range, loc_item["before_edit_ids"], label_masks
                )
                result_row["locality"][loc_name][idx]["acc"] = acc
                result_row["locality"][loc_name][idx]["predict_after_edit"] = tokenizer.decode(
                    pred_ids[label_masks.to(bool)]
                )

        for port_name in eval_row.get("portability", {}).keys():
            for idx, port_item in enumerate(eval_row["portability"][port_name]):
                acc, pred = score_target(editor, tokenizer, port_item)
                result_row["portability"][port_name][idx]["acc"] = acc
                result_row["portability"][port_name][idx]["predict_after_edit"] = pred

        results.append(result_row)
        editor.restore_to_original_model()

    save_dir = os.path.join(result_dir, "single_edit")
    save_json(os.path.join(save_dir, "results.json"), results)
    mean_results = compute_mean_results(results)
    mean_results["sample_count"] = len(results)
    save_json(os.path.join(save_dir, "mean_results.json"), mean_results)
    return result_dir, results, mean_results


def main():
    args = parse_args()
    config = VEADConfig.from_yaml(args.config)
    model_name = args.model_name or config.edit_model_name
    vllm = load_vllm_for_edit(model_name, args.device)
    editor = VEAD(vllm, config, args.device)
    editor.load_ckpt(args.ckpt_path, True, False)

    eval_data = EditBridge(
        args.data_path,
        img_root_dir=args.bridge_root,
        coco_img_dir=args.coco_root,
        data_n=args.data_n,
        img_path_map={"train/images": "bridge_train/bridge_images", "val/images": "bridge_val/bridge_images"},
    )
    result_dir, _, mean_results = evaluate_full_metrics(editor, eval_data, args.eval_name, args.output_root)

    manifest_path = os.path.join(args.output_root, "eval_manifest.json")
    os.makedirs(args.output_root, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                **vars(args),
                "model_name": model_name,
                "result_dir": result_dir,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "mean_results": set_decimal(mean_results),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.write("\n")


if __name__ == "__main__":
    main()
