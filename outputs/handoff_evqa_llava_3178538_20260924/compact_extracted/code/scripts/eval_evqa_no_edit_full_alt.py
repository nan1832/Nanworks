import argparse
import csv
import json
import os
import sys
import time
import traceback
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import torch
from tqdm import tqdm
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dataset.vllm import EVQA
from dataset.vllm import BaseVLLMEditData
from utils import get_full_model_name, load_vllm_for_edit


METRIC_COLUMNS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
MODEL_ORDER = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b-instruct",
    "paligemma-3b",
    "smolvlm-1.7b",
]


def load_imgs_with_closed_files(self, data):
    if isinstance(data, dict):
        for key in data.keys():
            if key == "image":
                if data[key] is not None:
                    with Image.open(data[key]) as image:
                        data[key] = image.convert("RGB").copy()
            else:
                load_imgs_with_closed_files(self, data[key])
    elif isinstance(data, list):
        for item in data:
            load_imgs_with_closed_files(self, item)
    elif isinstance(data, str):
        return
    else:
        raise TypeError(f"Unsupported data type while loading images: {type(data)}")


BaseVLLMEditData.__load_imgs_for_data_with_img_path__ = load_imgs_with_closed_files


def now():
    return time.strftime("%F %T")


def log(msg):
    print(f"[{now()}] {msg}", flush=True)


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def set_decimal(value, decimal=4):
    if isinstance(value, list):
        return [set_decimal(item, decimal) for item in value]
    if isinstance(value, dict) or isinstance(value, defaultdict):
        return {key: set_decimal(item, decimal) for key, item in value.items()}
    if isinstance(value, float):
        return round(value, decimal)
    return value


def set_eval_mode(vllm):
    if hasattr(vllm, "eval"):
        try:
            vllm.eval()
        except Exception:
            pass
    for attr in ["llm", "model", "vllm", "language_model"]:
        module = getattr(vllm, attr, None)
        if hasattr(module, "eval"):
            try:
                module.eval()
            except Exception:
                pass


def decode_token_ids(tokenizer, ids):
    try:
        return tokenizer.decode(ids)
    except TypeError:
        return tokenizer.decode(ids.detach().cpu().tolist())


def accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks):
    assert len(label_ids) == 1 and len(label_masks) == 1
    logits = vllm.get_llm_outpt(input_embeds, vt_range).logits
    pred_ids = logits.argmax(-1)
    pred_ids = pred_ids[:, -label_ids.shape[1] :]
    mask = label_masks.to(bool)
    acc = ((pred_ids == label_ids) * mask).sum() / mask.sum()
    return float(acc), pred_ids


def score_target(vllm, tokenizer, item):
    (input_embeds, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [item["prompt"]], [item["image"]], [item["target"]]
    )
    acc, pred_ids = accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks)
    return acc, decode_token_ids(tokenizer, pred_ids[label_masks.to(bool)])


def compute_mean_results(results):
    metric_values = {
        "reliability": defaultdict(list),
        "generality": defaultdict(lambda: defaultdict(list)),
        "locality": defaultdict(lambda: defaultdict(list)),
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

    out = {"reliability": {}, "generality": {}, "locality": {}, "metric_item_counts": {}}
    out["metric_item_counts"]["reliability"] = len(results)
    for key, values in metric_values["reliability"].items():
        out["reliability"][key] = sum(values) / len(values) if values else None

    for metric_name in ["generality", "locality"]:
        all_acc_values = []
        out[metric_name] = {}
        out["metric_item_counts"][metric_name] = {}
        for group_name, group_values in metric_values[metric_name].items():
            out[metric_name][group_name] = {}
            out["metric_item_counts"][metric_name][group_name] = len(group_values.get("acc", []))
            for key, values in group_values.items():
                out[metric_name][group_name][key] = sum(values) / len(values) if values else None
            all_acc_values.extend(group_values.get("acc", []))
        out[metric_name]["overall"] = {"acc": sum(all_acc_values) / len(all_acc_values) if all_acc_values else None}
        out["metric_item_counts"][metric_name]["overall"] = len(all_acc_values)
    return out


def pct(value):
    return None if value is None else value * 100.0


def get_nested(payload, *keys):
    cur = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def metrics_from_mean(model_name, mean_results):
    rel = pct(get_nested(mean_results, "reliability", "acc"))
    t_gen = pct(get_nested(mean_results, "generality", "text_rephrase", "acc"))
    m_gen = pct(get_nested(mean_results, "generality", "image_rephrase", "acc"))
    t_loc = pct(get_nested(mean_results, "locality", "text_loc", "acc"))
    m_loc = pct(get_nested(mean_results, "locality", "image_loc", "acc"))
    available = [x for x in [rel, t_gen, m_gen, t_loc, m_loc] if x is not None]
    avg = sum(available) / len(available) if available else None
    return {
        "model": model_name,
        "eval_samples": mean_results.get("sample_count"),
        "Rel": rel,
        "T-Gen": t_gen,
        "M-Gen": m_gen,
        "T-Loc": t_loc,
        "M-Loc": m_loc,
        "Average": avg,
        "status": "DONE",
    }


def evaluate_no_edit(args):
    model_name = get_full_model_name(args.model_name)
    model_dir = args.out_root / model_name
    done_path = model_dir / "no_edit_metrics.json"
    if done_path.exists() and not args.overwrite:
        log(f"[skip] {model_name} already done: {done_path}")
        return json.loads(done_path.read_text(encoding="utf-8"))

    model_dir.mkdir(parents=True, exist_ok=True)
    run_config = {k: str(v) for k, v in vars(args).items()}
    run_config["model_name_normalized"] = model_name
    save_json(model_dir / "run_config.json", run_config)
    if str(args.device).startswith("cuda"):
        log(
            "[cuda] visible_devices=%s available=%s count=%s"
            % (os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count())
        )
        if torch.cuda.is_available():
            torch.cuda.init()
            log("[cuda] initialized before data loading")
    log(f"[data] loading EVQA data: {args.eval_data}")
    eval_data = EVQA(str(args.eval_data), str(args.eval_img_root), args.eval_sample_n)
    log(f"[data] samples={len(eval_data.data)}")
    log(f"[model] loading {model_name} on {args.device}")
    vllm = load_vllm_for_edit(model_name, args.device)
    set_eval_mode(vllm)
    tokenizer = vllm.get_llm_tokenizer()

    eval_rows = deepcopy(eval_data.data_with_img)
    result_rows = deepcopy(eval_data.data_with_img_path)
    results = []

    with torch.inference_mode():
        for result_row, eval_row in zip(tqdm(result_rows, desc=f"no-edit {model_name}"), eval_rows):
            result_row["reliability"] = result_row.pop("request")
            result_row["reliability"]["target"] = result_row["reliability"].pop("target_new")

            request_item = {
                "image": eval_row["request"]["image"],
                "prompt": eval_row["request"]["prompt"],
                "target": eval_row["request"]["target_new"],
            }
            acc, pred = score_target(vllm, tokenizer, request_item)
            result_row["reliability"]["predict_no_edit"] = pred
            result_row["reliability"]["acc"] = acc

            for gen_name in eval_row["generality"].keys():
                for idx, gen_item in enumerate(eval_row["generality"][gen_name]):
                    acc, pred = score_target(vllm, tokenizer, gen_item)
                    result_row["generality"][gen_name][idx]["acc"] = acc
                    result_row["generality"][gen_name][idx]["predict_no_edit"] = pred

            for loc_name in eval_row["locality"].keys():
                for idx, loc_item in enumerate(eval_row["locality"][loc_name]):
                    (input_embeds, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
                        [loc_item["prompt"]], [loc_item["image"]], [loc_item["target"]]
                    )
                    _, before_ids = accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks)
                    result_row["locality"][loc_name][idx]["predict_before_no_edit"] = decode_token_ids(
                        tokenizer, before_ids[label_masks.to(bool)]
                    )

                    (input_embeds2, vt_range2), _, label_masks2 = vllm.prompts_imgs_target_to_xym(
                        [loc_item["prompt"]], [loc_item["image"]], [loc_item["target"]]
                    )
                    acc, after_ids = accuracy_and_prediction(vllm, input_embeds2, vt_range2, before_ids, label_masks2)
                    result_row["locality"][loc_name][idx]["acc"] = acc
                    result_row["locality"][loc_name][idx]["predict_after_no_edit"] = decode_token_ids(
                        tokenizer, after_ids[label_masks2.to(bool)]
                    )

            results.append(result_row)

    mean_results = compute_mean_results(results)
    mean_results["sample_count"] = len(results)
    metrics = metrics_from_mean(model_name, mean_results)
    metrics["finished_at"] = now()
    metrics["result_dir"] = str(model_dir)

    save_json(model_dir / "no_edit_results.json", set_decimal(results))
    save_json(model_dir / "no_edit_mean_results.json", set_decimal(mean_results))
    save_json(model_dir / "no_edit_metrics.json", set_decimal(metrics))
    log(f"[done] {model_name} avg={metrics['Average']:.2f} rel={metrics['Rel']:.2f}")
    return metrics


def fmt(value):
    if value is None or value == "":
        return "-"
    return f"{float(value):.2f}"


def summarize_root(out_root):
    rows = []
    for model_name in MODEL_ORDER:
        path = out_root / model_name / "no_edit_metrics.json"
        if path.exists():
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        else:
            rows.append({"model": model_name, "status": "PENDING"})

    csv_path = out_root / "no_edit_full_evqa_alt_7models_metrics.csv"
    fields = ["model", "eval_samples", *METRIC_COLUMNS, "status", "finished_at", "result_dir"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})

    md_lines = [
        "# No-Edit Full E-VQA Alt Baseline Metrics",
        "",
        "| Model | Eval samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        md_lines.append(
            "| {model} | {n} | {rel} | {tgen} | {mgen} | {tloc} | {mloc} | {avg} | {status} |".format(
                model=row.get("model", ""),
                n=row.get("eval_samples", "-"),
                rel=fmt(row.get("Rel")),
                tgen=fmt(row.get("T-Gen")),
                mgen=fmt(row.get("M-Gen")),
                tloc=fmt(row.get("T-Loc")),
                mloc=fmt(row.get("M-Loc")),
                avg=fmt(row.get("Average")),
                status=row.get("status", "-"),
            )
        )
    md_path = out_root / "no_edit_full_evqa_alt_7models_metrics.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    log(f"[summary] wrote {csv_path} and {md_path}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--eval-data", type=Path, default=PROJECT_ROOT / "data/easy-edit-mm/vqa/vqa_eval.json")
    parser.add_argument("--eval-img-root", type=Path, default=PROJECT_ROOT / "data/easy-edit-mm/images")
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--eval-sample-n", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    if args.summarize_only:
        summarize_root(args.out_root)
        return
    if not args.model_name:
        raise ValueError("--model-name is required unless --summarize-only is set")
    metrics = evaluate_no_edit(args)
    summarize_root(args.out_root)
    return metrics


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
