#!/usr/bin/env python3
import argparse
import csv
import gc
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import torch
from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dataset.vllm import BaseVLLMEditData, EVQA
from p_track.p_track import PTrackConfig
from utils import find_module, load_vllm_for_edit


MODEL_ORDER = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b",
    "paligemma-3b",
    "smolvlm-1.7b",
]

DATASET_ORDER = ["evqa-pilot500", "mmke-visual", "mmke-entity"]

MODEL_DISPLAY = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}

DATASET_DISPLAY = {
    "evqa-pilot500": "EVQA-pilot500",
    "mmke-visual": "MMKE-visual",
    "mmke-entity": "MMKE-entity",
}

CONFIG_PATHS = {
    "blip2-opt-2.7b": "configs/p_track/blip2-opt-2.7b.yaml",
    "instructblip-vicuna-7b": "configs/p_track/instructblip-vicuna-7b.yaml",
    "minigpt-4-vicuna-7b": "configs/p_track/minigpt-4-vicuna-7b.yaml",
    "llava-v1.5-7b": "configs/p_track/llava-v1.5-7b.yaml",
    "qwen2.5-vl-3b": "configs/p_track/qwen2.5-vl-3b.yaml",
    "paligemma-3b": "configs/p_track/paligemma-3b.yaml",
    "smolvlm-1.7b": "configs/p_track/smolvlm-1.7b.yaml",
}

DEFAULT_DATASETS = {
    "evqa-pilot500": {
        "kind": "evqa",
        "data_path": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json",
        "img_root": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images",
    },
    "mmke-visual": {
        "kind": "mmke",
        "data_path": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json",
        "img_root": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image",
    },
    "mmke-entity": {
        "kind": "mmke",
        "data_path": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json",
        "img_root": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image",
    },
}


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


def normalize_model_name(raw):
    key = raw.lower().replace("_", "-").replace("/", "-")
    aliases = {
        "instructblip": "instructblip-vicuna-7b",
        "minigpt4": "minigpt-4-vicuna-7b",
        "minigpt-4": "minigpt-4-vicuna-7b",
        "llava": "llava-v1.5-7b",
        "llava-v1.5-7b-hf": "llava-v1.5-7b",
        "qwen": "qwen2.5-vl-3b",
        "qwen2.5-vl-3b-instruct": "qwen2.5-vl-3b",
        "paligemma": "paligemma-3b",
        "smolvlm": "smolvlm-1.7b",
        "smolvlm-instruct": "smolvlm-1.7b",
    }
    if key in MODEL_ORDER:
        return key
    if key in aliases:
        return aliases[key]
    for name in MODEL_ORDER:
        if name in key:
            return name
    raise ValueError(f"Unknown model name: {raw}")


def resolve_path(path):
    p = Path(path)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def build_mmke_data(data_path, img_root, data_n=None):
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    if data_n is not None:
        raw_data = raw_data[:data_n]
    data = []
    for row in tqdm(raw_data, desc="Loading MMKE data"):
        image_path = Path(row["image"])
        if not image_path.is_absolute():
            image_path = Path(img_root) / image_path
        with Image.open(image_path) as image:
            pil_image = image.convert("RGB").copy()
        data.append(
            {
                "request": {
                    "image": pil_image,
                    "prompt": f"{row['src']} The answer is:",
                    "target_new": row["alt"],
                }
            }
        )
    return data


def load_edit_data(dataset_name, data_path, img_root, data_n=None):
    if dataset_name == "evqa-pilot500":
        return EVQA(data_path, img_root, data_n).data
    return build_mmke_data(data_path, img_root, data_n)


def get_logits(output):
    if hasattr(output, "logits"):
        return output.logits
    if isinstance(output, (tuple, list)):
        return output[0]
    raise TypeError(f"Cannot read logits from output type: {type(output)}")


def prepare_mlp_modules(vllm, cfg):
    for p in vllm.model.parameters():
        p.requires_grad_(False)
    modules = []
    for layer in range(cfg.num_layers):
        module_path = cfg.mlp_module_tmp.format(layer)
        module = find_module(vllm.model, module_path)
        params = list(module.parameters())
        for p in params:
            p.requires_grad_(True)
        param_count = sum(p.numel() for p in params)
        modules.append(
            {
                "layer": layer,
                "module_path": module_path,
                "module": module,
                "params": params,
                "param_count": param_count,
            }
        )
    return modules


def zero_target_grads(vllm):
    vllm.model.zero_grad(set_to_none=True)


def sample_layer_scores(modules):
    scores = {}
    grad_param_counts = {}
    for item in modules:
        abs_sum = 0.0
        grad_param_count = 0
        for p in item["params"]:
            if p.grad is not None:
                g = p.grad.detach()
                abs_sum += float(g.abs().float().sum().item())
                grad_param_count += p.numel()
        denom = max(item["param_count"], 1)
        scores[item["layer"]] = abs_sum / denom
        grad_param_counts[item["layer"]] = grad_param_count
    return scores, grad_param_counts


def run_one(args):
    model_name = normalize_model_name(args.model_name)
    dataset_name = args.dataset_name
    if dataset_name not in DEFAULT_DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    if args.resume and summary_path.exists():
        print(f"[SKIP] Existing summary: {summary_path}")
        return

    ds = DEFAULT_DATASETS[dataset_name]
    data_path = args.data_path or ds["data_path"]
    img_root = args.img_root or ds["img_root"]
    data = load_edit_data(dataset_name, data_path, img_root, args.data_n)

    cfg = PTrackConfig.from_yaml(str(resolve_path(CONFIG_PATHS[model_name])))
    torch.set_grad_enabled(True)
    vllm = load_vllm_for_edit(model_name, args.device)
    vllm.model.eval()
    modules = prepare_mlp_modules(vllm, cfg)

    layer_sums = {item["layer"]: 0.0 for item in modules}
    layer_seen = {item["layer"]: 0 for item in modules}
    layer_grad_params = {item["layer"]: 0 for item in modules}
    losses = []
    errors = []
    ok_count = 0
    started = time.time()

    progress_path = out_dir / "progress.jsonl"
    with progress_path.open("w", encoding="utf-8") as pf:
        for sample_i, row in enumerate(tqdm(data, desc=f"{dataset_name}/{model_name}")):
            request = row["request"]
            image = request["image"]
            prompt = request["prompt"]
            target = request["target_new"]
            zero_target_grads(vllm)
            try:
                (input_embeds, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
                    [prompt], [image], [target]
                )
                output = vllm.get_llm_outpt(input_embeds, vt_range)
                loss = vllm.label_loss(get_logits(output), label_ids, label_masks, average=True)
                if not torch.isfinite(loss):
                    raise FloatingPointError(f"non-finite loss: {float(loss.detach().cpu())}")
                loss.backward()
                scores, grad_counts = sample_layer_scores(modules)
                for layer, score in scores.items():
                    if math.isfinite(score):
                        layer_sums[layer] += score
                        layer_seen[layer] += 1
                        layer_grad_params[layer] += grad_counts[layer]
                ok_count += 1
                losses.append(float(loss.detach().cpu().item()))
                pf.write(json.dumps({"sample": sample_i, "loss": losses[-1]}, ensure_ascii=False) + "\n")
                pf.flush()
            except Exception as exc:
                err = {
                    "sample": sample_i,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(limit=3),
                }
                errors.append(err)
                pf.write(json.dumps(err, ensure_ascii=False) + "\n")
                pf.flush()
            finally:
                zero_target_grads(vllm)
                for name in ("input_embeds", "label_ids", "label_masks", "output", "loss"):
                    if name in locals():
                        del locals()[name]
                if torch.cuda.is_available() and (sample_i + 1) % args.empty_cache_every == 0:
                    torch.cuda.empty_cache()
                gc.collect()

    rows = []
    for item in modules:
        layer = item["layer"]
        denom = max(layer_seen[layer], 1)
        layer_score = layer_sums[layer] / denom
        rows.append(
            {
                "dataset": DATASET_DISPLAY[dataset_name],
                "model": MODEL_DISPLAY[model_name],
                "layer": layer,
                "layer_name": f"L{layer}",
                "layer_score": layer_score,
                "samples_used": layer_seen[layer],
                "total_samples": len(data),
                "module_path": item["module_path"],
                "param_count": item["param_count"],
                "grad_param_count_sum": layer_grad_params[layer],
            }
        )
    rows.sort(key=lambda r: (-r["layer_score"], r["layer"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank

    csv_path = out_dir / "salem_layer_scores.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    top3 = [r["layer_name"] for r in rows[:3]]
    top5 = [r["layer_name"] for r in rows[:5]]
    summary = {
        "dataset_key": dataset_name,
        "dataset": DATASET_DISPLAY[dataset_name],
        "model_key": model_name,
        "model": MODEL_DISPLAY[model_name],
        "formula": "S_l(D)=mean_samples(mean_abs(grad_W_l loss(prompt,image,target_new_alt)))",
        "target_field": "request.target_new / alt",
        "layer_type": "MLP/FFN parameters from configs/p_track mlp_module_tmp",
        "num_layers": cfg.num_layers,
        "total_samples": len(data),
        "ok_samples": ok_count,
        "error_samples": len(errors),
        "loss_mean": sum(losses) / len(losses) if losses else None,
        "top3_layers": top3,
        "top5_layers": top5,
        "duration_sec": time.time() - started,
        "scores_csv": str(csv_path),
        "errors": errors[:20],
    }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    (out_dir / "DONE").write_text("done\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def collect(args):
    run_root = Path(args.run_root).resolve()
    rows = []
    for dataset_name in DATASET_ORDER:
        for model_name in MODEL_ORDER:
            summary_path = run_root / dataset_name / model_name / "summary.json"
            if summary_path.exists():
                with summary_path.open("r", encoding="utf-8") as f:
                    summary = json.load(f)
                status = f"done; n={summary.get('ok_samples')}/{summary.get('total_samples')}"
                top3 = ",".join(summary.get("top3_layers", []))
                top5 = ",".join(summary.get("top5_layers", []))
            else:
                status = "missing"
                top3 = "-"
                top5 = "-"
            rows.append(
                {
                    "Dataset": DATASET_DISPLAY[dataset_name],
                    "Model": MODEL_DISPLAY[model_name],
                    "Method": "SaLEM",
                    "Score source": "mean_abs_param_grad_alt",
                    "Top-3": top3,
                    "Top-5": top5,
                    "Status": status,
                }
            )

    csv_path = run_root / "salem_candidates_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_path = run_root / "salem_candidates_summary.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for row in rows:
            f.write(
                f"| {row['Dataset']} | {row['Model']} | {row['Method']} | {row['Score source']} "
                f"| {row['Top-3']} | {row['Top-5']} | {row['Status']} |\n"
            )
    print(f"Wrote {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Compute SaLEM layer candidates.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-one")
    run.add_argument("--model-name", required=True)
    run.add_argument("--dataset-name", required=True, choices=DATASET_ORDER)
    run.add_argument("--out-dir", required=True)
    run.add_argument("--device", default="cuda:0")
    run.add_argument("--data-path", default=None)
    run.add_argument("--img-root", default=None)
    run.add_argument("--data-n", type=int, default=None)
    run.add_argument("--empty-cache-every", type=int, default=1)
    run.add_argument("--resume", action="store_true")
    run.set_defaults(func=run_one)

    col = sub.add_parser("collect")
    col.add_argument("--run-root", required=True)
    col.set_defaults(func=collect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
