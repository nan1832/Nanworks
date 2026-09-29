#!/usr/bin/env python3
import argparse
import csv
import gc
import hashlib
import json
import math
import os
import sys
import time
import traceback
from collections import defaultdict
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
from utils import load_vllm_for_edit
from utils.nethook import TraceDict


METHOD_NAME = "Perturb-KL-Direct"
SCORE_SOURCE = "visual_token_noise_altseq_kl"

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


def parse_csv_list(raw, cast):
    return [cast(x.strip()) for x in raw.split(",") if x.strip()]


def stable_seed(*items):
    payload = json.dumps(items, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


def short_hash(obj):
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_mmke_data(data_path, img_root, data_n=None):
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    if data_n is not None:
        raw_data = raw_data[:data_n]
    data = []
    for row_i, row in enumerate(tqdm(raw_data, desc="Loading MMKE data")):
        image_path = Path(row["image"])
        if not image_path.is_absolute():
            image_path = Path(img_root) / image_path
        with Image.open(image_path) as image:
            pil_image = image.convert("RGB").copy()
        data.append(
            {
                "case_id": row.get("case_id", row.get("id", f"mmke_{row_i}")),
                "image_path": str(image_path),
                "request": {
                    "image": pil_image,
                    "prompt": f"{row['src']} The answer is:",
                    "target_new": row["alt"],
                },
            }
        )
    return data


def load_edit_data(dataset_name, data_path, img_root, data_n=None):
    if dataset_name == "evqa-pilot500":
        return EVQA(data_path, img_root, data_n).data
    return build_mmke_data(data_path, img_root, data_n)


def get_sample_id(row, sample_i):
    for key in ("case_id", "id", "sample_id"):
        if key in row:
            return str(row[key])
    req = row.get("request", {})
    return short_hash(
        {
            "i": sample_i,
            "prompt": req.get("prompt", ""),
            "target_new": req.get("target_new", ""),
        }
    )


def get_logits(output):
    if hasattr(output, "logits"):
        return output.logits
    if isinstance(output, (tuple, list)):
        return output[0]
    raise TypeError(f"Cannot read logits from output type: {type(output)}")


def first_hidden(output):
    hidden = output[0] if isinstance(output, (tuple, list)) else output
    if not torch.is_tensor(hidden):
        raise TypeError(f"Hook output does not contain a tensor hidden state: {type(hidden)}")
    return hidden


def hidden_visual_slice(hidden, vt_range):
    start, end = int(vt_range[0]), int(vt_range[1])
    if hidden.dim() == 3:
        seq_len = hidden.shape[1]
        if not (0 <= start < end <= seq_len):
            raise ValueError(f"invalid visual span {vt_range} for seq_len={seq_len}")
        return hidden[:, start:end, :]
    if hidden.dim() == 2:
        seq_len = hidden.shape[0]
        if not (0 <= start < end <= seq_len):
            raise ValueError(f"invalid visual span {vt_range} for seq_len={seq_len}")
        return hidden[start:end, :]
    raise ValueError(f"unsupported hidden dim: {hidden.dim()}")


def replace_visual_slice(hidden, vt_range, noise):
    start, end = int(vt_range[0]), int(vt_range[1])
    updated = hidden.clone()
    if hidden.dim() == 3:
        updated[:, start:end, :] = hidden[:, start:end, :] + noise.to(hidden.dtype)
    elif hidden.dim() == 2:
        updated[start:end, :] = hidden[start:end, :] + noise.to(hidden.dtype)
    else:
        raise ValueError(f"unsupported hidden dim: {hidden.dim()}")
    return updated


def make_noise_like(vis_hidden, sigma, seed):
    device = vis_hidden.device
    generator = torch.Generator(device=device.type if device.type == "cuda" else "cpu")
    generator.manual_seed(int(seed))
    noise = torch.randn(
        vis_hidden.shape,
        device=device,
        dtype=torch.float32,
        generator=generator,
    )
    return noise * float(sigma)


def perturb_output(output, vt_range, sigma, seed):
    hidden = first_hidden(output)
    vis_hidden = hidden_visual_slice(hidden, vt_range)
    noise = make_noise_like(vis_hidden, sigma, seed)
    updated_hidden = replace_visual_slice(hidden, vt_range, noise)
    if isinstance(output, tuple):
        return (updated_hidden,) + output[1:]
    if isinstance(output, list):
        updated = list(output)
        updated[0] = updated_hidden
        return updated
    return updated_hidden


def compute_kl(clean_logits, pert_logits, label_masks):
    clean = clean_logits[:, -label_masks.shape[1] :].float()
    pert = pert_logits[:, -label_masks.shape[1] :].float()
    log_p_clean = torch.log_softmax(clean, -1)
    log_p_pert = torch.log_softmax(pert, -1)
    p_clean = torch.softmax(clean, -1)
    kl = (p_clean * (log_p_clean - log_p_pert)).sum(-1)
    mask = label_masks.float()
    denom = mask.sum()
    if denom.item() <= 0:
        raise ValueError("target mask is empty")
    value = (kl * mask).sum() / denom
    if not torch.isfinite(value):
        raise FloatingPointError("non-finite KL")
    return float(value.detach().cpu().item())


def rank_values_desc(values_by_layer):
    ordered = sorted(values_by_layer.items(), key=lambda kv: (-kv[1], kv[0]))
    ranks = {}
    idx = 0
    while idx < len(ordered):
        j = idx + 1
        while j < len(ordered) and ordered[j][1] == ordered[idx][1]:
            j += 1
        avg_rank = (idx + 1 + j) / 2.0
        for k in range(idx, j):
            ranks[ordered[k][0]] = avg_rank
        idx = j
    return ranks


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def spearman(values_a, values_b):
    common = sorted(set(values_a) & set(values_b))
    if len(common) < 2:
        return None
    ra = rank_values_desc({k: values_a[k] for k in common})
    rb = rank_values_desc({k: values_b[k] for k in common})
    return pearson([ra[k] for k in common], [rb[k] for k in common])


def validate_visual_span(vt_range, seq_len):
    start, end = int(vt_range[0]), int(vt_range[1])
    if not (0 <= start < end <= seq_len):
        raise ValueError(f"invalid visual span {vt_range} for seq_len={seq_len}")
    return start, end


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

    noise_scales = parse_csv_list(args.noise_scales, float)
    repeats = parse_csv_list(args.repeats, int)
    groups = [(alpha, repeat) for alpha in noise_scales for repeat in repeats]

    ds = DEFAULT_DATASETS[dataset_name]
    data_path = args.data_path or ds["data_path"]
    img_root = args.img_root or ds["img_root"]
    data = load_edit_data(dataset_name, data_path, img_root, args.data_n)

    cfg = PTrackConfig.from_yaml(str(resolve_path(CONFIG_PATHS[model_name])))
    layer_ids = list(range(int(cfg.num_layers)))
    layer_names = {layer: cfg.layer_module_tmp.format(layer) for layer in layer_ids}
    trace_layers = [layer_names[layer] for layer in layer_ids]

    torch.set_grad_enabled(False)
    vllm = load_vllm_for_edit(model_name, args.device)
    vllm.model.eval()

    sums = defaultdict(float)
    counts = defaultdict(int)
    hidden_std_sum = defaultdict(float)
    hidden_std_min = defaultdict(lambda: float("inf"))
    hidden_std_max = defaultdict(float)
    excluded = []
    precheck_errors = []
    clean_repeat_kls = []
    zero_noise_kls = []
    common_ok = 0
    started = time.time()

    progress_path = out_dir / "progress.jsonl"
    with progress_path.open("w", encoding="utf-8") as pf:
        for sample_i, row in enumerate(tqdm(data, desc=f"{dataset_name}/{model_name}")):
            sample_id = get_sample_id(row, sample_i)
            req = row["request"]
            prompt = req["prompt"]
            image = req["image"]
            target = req["target_new"]
            sample_temp = {}
            sample_hidden_stats = {}
            try:
                if target is None or str(target).strip() == "":
                    raise ValueError("empty target_new / alt")
                (input_embeds, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
                    [prompt], [image], [target]
                )
                with torch.no_grad(), TraceDict(
                    vllm.model,
                    trace_layers,
                    retain_output=True,
                    with_kwargs=True,
                    clone=True,
                    detach=True,
                ) as td:
                    clean_output = vllm.get_llm_outpt(input_embeds, vt_range)
                    clean_logits = get_logits(clean_output).detach()
                validate_visual_span(vt_range, clean_logits.shape[1])
                if label_masks.sum().item() <= 0:
                    raise ValueError("empty target mask")
                if not torch.isfinite(clean_logits).all():
                    raise FloatingPointError("non-finite clean logits")

                if sample_i < args.sanity_samples:
                    with torch.no_grad():
                        clean_output_2 = vllm.get_llm_outpt(input_embeds, vt_range)
                        clean_logits_2 = get_logits(clean_output_2).detach()
                    clean_repeat_kls.append(compute_kl(clean_logits, clean_logits_2, label_masks))

                for layer in layer_ids:
                    layer_name = layer_names[layer]
                    clean_hidden = first_hidden(td[layer_name].output)
                    vis_hidden = hidden_visual_slice(clean_hidden, vt_range)
                    std = float(vis_hidden.float().std(unbiased=False).detach().cpu().item())
                    safe_std = max(std, float(args.epsilon_sigma))
                    sample_hidden_stats[layer] = std

                    if sample_i < args.sanity_samples:
                        seed0 = stable_seed(
                            dataset_name,
                            model_name,
                            sample_id,
                            "alpha0",
                            repeats[0],
                            int(vis_hidden.numel() // max(vis_hidden.shape[-1], 1)),
                            int(vis_hidden.shape[-1]),
                        )

                        def zero_edit(output, layer=None, target_layer=layer_name, seed=seed0):
                            if layer != target_layer:
                                return output
                            return perturb_output(output, vt_range, 0.0, seed)

                        with torch.no_grad(), TraceDict(
                            vllm.model,
                            [layer_name],
                            with_kwargs=True,
                            edit_output=zero_edit,
                            clone=True,
                            detach=True,
                        ):
                            zero_output = vllm.get_llm_outpt(input_embeds, vt_range)
                            zero_logits = get_logits(zero_output).detach()
                        zero_noise_kls.append(compute_kl(clean_logits, zero_logits, label_masks))

                    for alpha, repeat in groups:
                        seed = stable_seed(
                            dataset_name,
                            model_name,
                            sample_id,
                            f"{alpha:g}",
                            repeat,
                            int(vis_hidden.numel() // max(vis_hidden.shape[-1], 1)),
                            int(vis_hidden.shape[-1]),
                        )
                        sigma = float(alpha) * safe_std

                        def edit_output(output, layer=None, target_layer=layer_name, sig=sigma, sd=seed):
                            if layer != target_layer:
                                return output
                            return perturb_output(output, vt_range, sig, sd)

                        with torch.no_grad(), TraceDict(
                            vllm.model,
                            [layer_name],
                            with_kwargs=True,
                            edit_output=edit_output,
                            clone=True,
                            detach=True,
                        ):
                            pert_output = vllm.get_llm_outpt(input_embeds, vt_range)
                            pert_logits = get_logits(pert_output).detach()
                        kl = compute_kl(clean_logits, pert_logits, label_masks)
                        sample_temp[(layer, alpha, repeat)] = kl
                        del pert_output, pert_logits

                for key, value in sample_temp.items():
                    sums[key] += value
                    counts[key] += 1
                for layer, std in sample_hidden_stats.items():
                    hidden_std_sum[layer] += std
                    hidden_std_min[layer] = min(hidden_std_min[layer], std)
                    hidden_std_max[layer] = max(hidden_std_max[layer], std)
                common_ok += 1
                pf.write(json.dumps({"sample": sample_i, "sample_id": sample_id, "status": "ok"}, ensure_ascii=False) + "\n")
                pf.flush()
            except Exception as exc:
                item = {
                    "sample": sample_i,
                    "sample_id": sample_id,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(limit=4),
                }
                excluded.append(item)
                if len(precheck_errors) < 50:
                    precheck_errors.append(item)
                pf.write(json.dumps({"sample": sample_i, "sample_id": sample_id, "status": "excluded", "error": repr(exc)}, ensure_ascii=False) + "\n")
                pf.flush()
            finally:
                for local_name in [
                    "input_embeds",
                    "label_ids",
                    "label_masks",
                    "clean_output",
                    "clean_logits",
                    "clean_output_2",
                    "clean_logits_2",
                    "zero_output",
                    "zero_logits",
                    "td",
                ]:
                    if local_name in locals():
                        try:
                            del locals()[local_name]
                        except Exception:
                            pass
                if torch.cuda.is_available() and (sample_i + 1) % args.empty_cache_every == 0:
                    torch.cuda.empty_cache()
                gc.collect()

    score_by_group_layer = {}
    group_meta = {}
    all_counts = []
    for alpha, repeat in groups:
        vals = {}
        group_counts = []
        for layer in layer_ids:
            key = (layer, alpha, repeat)
            count = counts[key]
            group_counts.append(count)
            all_counts.append(count)
            vals[layer] = sums[key] / count if count else float("nan")
        finite_vals = [v for v in vals.values() if math.isfinite(v)]
        if finite_vals:
            dyn = max(finite_vals) - min(finite_vals)
            mag = max(abs(v) for v in finite_vals)
            threshold = max(float(args.epsilon_abs), float(args.epsilon_rel) * mag)
            valid = dyn >= threshold
        else:
            dyn = float("nan")
            mag = float("nan")
            threshold = float(args.epsilon_abs)
            valid = False
        group_meta[(alpha, repeat)] = {
            "dynamic_range": dyn,
            "max_abs": mag,
            "threshold": threshold,
            "valid": valid,
            "processed_sample_count_min": min(group_counts) if group_counts else 0,
            "processed_sample_count_max": max(group_counts) if group_counts else 0,
        }
        for layer, value in vals.items():
            score_by_group_layer[(layer, alpha, repeat)] = value

    valid_groups = [g for g in groups if group_meta[g]["valid"]]
    normalized = {}
    ranks = {}
    for alpha, repeat in groups:
        vals = {
            layer: score_by_group_layer[(layer, alpha, repeat)]
            for layer in layer_ids
            if math.isfinite(score_by_group_layer[(layer, alpha, repeat)])
        }
        if vals:
            ranks[(alpha, repeat)] = rank_values_desc(vals)
        else:
            ranks[(alpha, repeat)] = {}
        if not group_meta[(alpha, repeat)]["valid"] or not vals:
            continue
        min_v = min(vals.values())
        max_v = max(vals.values())
        denom = max(max_v - min_v, 1e-30)
        for layer, value in vals.items():
            normalized[(layer, alpha, repeat)] = (value - min_v) / denom

    layer_rows = []
    for layer in layer_ids:
        norm_vals = [normalized[(layer, a, r)] for a, r in valid_groups if (layer, a, r) in normalized]
        raw_vals = [
            score_by_group_layer[(layer, a, r)]
            for a, r in valid_groups
            if math.isfinite(score_by_group_layer[(layer, a, r)])
        ]
        rank_vals = [ranks[(a, r)][layer] for a, r in valid_groups if layer in ranks[(a, r)]]
        robust = sum(norm_vals) / len(norm_vals) if norm_vals else float("nan")
        raw_mean = sum(raw_vals) / len(raw_vals) if raw_vals else float("nan")
        mean_rank = sum(rank_vals) / len(rank_vals) if rank_vals else float("nan")
        rank_std = (
            math.sqrt(sum((x - mean_rank) ** 2 for x in rank_vals) / len(rank_vals))
            if rank_vals and math.isfinite(mean_rank)
            else float("nan")
        )
        std_seen = max(common_ok, 1)
        layer_rows.append(
            {
                "dataset_key": dataset_name,
                "dataset": DATASET_DISPLAY[dataset_name],
                "model_key": model_name,
                "model": MODEL_DISPLAY[model_name],
                "layer": layer,
                "layer_name": f"L{layer}",
                "score_kl_robust": robust,
                "score_kl_raw_mean": raw_mean,
                "mean_rank": mean_rank,
                "rank_std": rank_std,
                "valid_alpha_repeat_count": len(norm_vals),
                "processed_sample_count": common_ok,
                "hidden_std_mean": hidden_std_sum[layer] / std_seen if common_ok else float("nan"),
                "hidden_std_min": hidden_std_min[layer] if common_ok else float("nan"),
                "hidden_std_max": hidden_std_max[layer] if common_ok else float("nan"),
            }
        )
    layer_rows.sort(
        key=lambda r: (
            -(r["score_kl_robust"] if math.isfinite(r["score_kl_robust"]) else -1e30),
            -(r["score_kl_raw_mean"] if math.isfinite(r["score_kl_raw_mean"]) else -1e30),
            r["mean_rank"] if math.isfinite(r["mean_rank"]) else 1e30,
            r["layer"],
        )
    )
    for idx, row in enumerate(layer_rows, start=1):
        row["rank"] = idx

    long_rows = []
    for alpha, repeat in groups:
        meta = group_meta[(alpha, repeat)]
        for layer in layer_ids:
            value = score_by_group_layer[(layer, alpha, repeat)]
            long_rows.append(
                {
                    "dataset_key": dataset_name,
                    "dataset": DATASET_DISPLAY[dataset_name],
                    "model_key": model_name,
                    "model": MODEL_DISPLAY[model_name],
                    "layer": layer,
                    "layer_name": f"L{layer}",
                    "alpha": alpha,
                    "repeat": repeat,
                    "seed_method": "sha256(dataset,model,sample_id,alpha,repeat,visual_token_count,hidden_size)",
                    "valid_alpha_repeat": meta["valid"],
                    "kl_mean": value,
                    "normalized_kl": normalized.get((layer, alpha, repeat), float("nan")),
                    "rank_within_alpha_repeat": ranks[(alpha, repeat)].get(layer, float("nan")),
                    "processed_sample_count": counts[(layer, alpha, repeat)],
                    "dynamic_range": meta["dynamic_range"],
                    "relative_dynamic_range": (
                        meta["dynamic_range"] / meta["max_abs"]
                        if math.isfinite(meta["dynamic_range"]) and math.isfinite(meta["max_abs"]) and meta["max_abs"] > 0
                        else float("nan")
                    ),
                    "invalid_reason": "" if meta["valid"] else "near_constant_or_nonfinite_group",
                }
            )

    stability_rows = []
    for alpha in noise_scales:
        repeat_scores = {}
        for repeat in repeats:
            repeat_scores[repeat] = {
                layer: score_by_group_layer[(layer, alpha, repeat)]
                for layer in layer_ids
                if math.isfinite(score_by_group_layer[(layer, alpha, repeat)])
            }
        pair_corrs = []
        for i, r1 in enumerate(repeats):
            for r2 in repeats[i + 1 :]:
                corr = spearman(repeat_scores[r1], repeat_scores[r2])
                if corr is not None and math.isfinite(corr):
                    pair_corrs.append(corr)
        stability_rows.append(
            {
                "dataset": DATASET_DISPLAY[dataset_name],
                "model": MODEL_DISPLAY[model_name],
                "alpha": alpha,
                "repeat_count": len(repeats),
                "valid_repeat_pair_count": len(pair_corrs),
                "spearman_between_repeats_by_alpha": sum(pair_corrs) / len(pair_corrs) if pair_corrs else float("nan"),
            }
        )

    def write_rows(path, rows):
        if not rows:
            return
        with Path(path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    long_csv = out_dir / "perturb_kl_scores_long.csv"
    layer_csv = out_dir / "perturb_kl_layer_scores.csv"
    stability_csv = out_dir / "perturb_kl_stability.csv"
    write_rows(long_csv, long_rows)
    write_rows(layer_csv, layer_rows)
    write_rows(stability_csv, stability_rows)

    top3 = [r["layer_name"] for r in layer_rows[:3]]
    top5 = [r["layer_name"] for r in layer_rows[:5]]
    coverage_ratio = common_ok / len(data) if data else 0.0
    counts_consistent = len(set(all_counts)) <= 1
    valid_group_count = len(valid_groups)
    status = "done"
    failure_reasons = []
    if common_ok == 0:
        status = "failed"
        failure_reasons.append("no_common_valid_samples")
    if not counts_consistent:
        status = "low_confidence" if status == "done" else status
        failure_reasons.append("inconsistent_sample_coverage_across_layers")
    if valid_group_count == 0:
        status = "failed"
        failure_reasons.append("no_informative_alpha_repeat_group")
    if coverage_ratio < args.min_coverage and status == "done":
        status = "low_confidence"
        failure_reasons.append("low_coverage")

    summary = {
        "dataset_key": dataset_name,
        "dataset": DATASET_DISPLAY[dataset_name],
        "model_key": model_name,
        "model": MODEL_DISPLAY[model_name],
        "method": METHOD_NAME,
        "score_source": SCORE_SOURCE,
        "target_sequence": "complete alt sequence",
        "perturb_scope": "visual tokens only",
        "candidate_conversion": "direct",
        "ranking_metric": "score_kl_robust",
        "num_layers": cfg.num_layers,
        "noise_scales": noise_scales,
        "repeats": repeats,
        "epsilon_sigma": args.epsilon_sigma,
        "epsilon_abs": args.epsilon_abs,
        "epsilon_rel": args.epsilon_rel,
        "manifest_sample_count": len(data),
        "base_valid_sample_count": len(data) - len(excluded),
        "common_valid_sample_count": common_ok,
        "coverage_ratio": coverage_ratio,
        "per_layer_processed_count_consistent": counts_consistent,
        "valid_alpha_repeat_count": valid_group_count,
        "invalid_alpha_repeat_count": len(groups) - valid_group_count,
        "zero_noise_max_kl": max(zero_noise_kls) if zero_noise_kls else None,
        "zero_noise_mean_kl": sum(zero_noise_kls) / len(zero_noise_kls) if zero_noise_kls else None,
        "zero_noise_pass": (max(zero_noise_kls) <= args.zero_kl_tolerance) if zero_noise_kls else None,
        "clean_repeat_max_kl": max(clean_repeat_kls) if clean_repeat_kls else None,
        "clean_repeat_pass": (max(clean_repeat_kls) <= args.clean_kl_tolerance) if clean_repeat_kls else None,
        "top3_layers": top3,
        "top5_layers": top5,
        "status": status,
        "failure_reasons": failure_reasons,
        "duration_sec": time.time() - started,
        "scores_long_csv": str(long_csv),
        "layer_scores_csv": str(layer_csv),
        "stability_csv": str(stability_csv),
        "excluded_sample_count": len(excluded),
        "excluded_sample_ids": [x["sample_id"] for x in excluded[:200]],
        "errors": precheck_errors,
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
                status = (
                    f"{summary.get('status', 'done')}; "
                    f"n={summary.get('common_valid_sample_count')}/{summary.get('manifest_sample_count')}; "
                    f"valid_groups={summary.get('valid_alpha_repeat_count')}"
                )
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
                    "Method": METHOD_NAME,
                    "Score source": SCORE_SOURCE,
                    "Top-3": top3,
                    "Top-5": top5,
                    "Status": status,
                }
            )

    csv_path = run_root / "perturb_kl_direct_candidates_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_path = run_root / "perturb_kl_direct_candidates_summary.md"
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
    parser = argparse.ArgumentParser(description="Compute Perturb-KL-Direct candidate layers.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-one")
    run.add_argument("--model-name", required=True)
    run.add_argument("--dataset-name", required=True, choices=DATASET_ORDER)
    run.add_argument("--out-dir", required=True)
    run.add_argument("--device", default="cuda:0")
    run.add_argument("--data-path", default=None)
    run.add_argument("--img-root", default=None)
    run.add_argument("--data-n", type=int, default=None)
    run.add_argument("--noise-scales", default="0.1,0.5,1,3")
    run.add_argument("--repeats", default="2026,2027,2028")
    run.add_argument("--epsilon-sigma", type=float, default=1e-6)
    run.add_argument("--epsilon-abs", type=float, default=1e-8)
    run.add_argument("--epsilon-rel", type=float, default=1e-3)
    run.add_argument("--sanity-samples", type=int, default=3)
    run.add_argument("--zero-kl-tolerance", type=float, default=1e-6)
    run.add_argument("--clean-kl-tolerance", type=float, default=1e-6)
    run.add_argument("--min-coverage", type=float, default=0.8)
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
