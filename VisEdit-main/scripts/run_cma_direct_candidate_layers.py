#!/usr/bin/env python3
"""Compute CMA-Direct candidate layers for VLM edit-layer localization.

This script follows ``md/Location/Equations/CMA-Direct_v1.3.md``:

* clean forward caches every decoder layer's visual-token hidden states;
* corrupt forward adds Gaussian noise to the decoder input visual embeddings;
* restore forward uses the corrupted input while replacing one layer's visual
  hidden states with the clean visual hidden states;
* main ranking uses complete-target-sequence restoration score ``cr_seq_mean``.
"""

from __future__ import annotations

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
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

METHOD_NAME = "CMA-Direct"
SCORE_SOURCE = "cr_seq_mean"
RANKING_METRIC = "cr_seq_mean"

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


def normalize_model_name(raw: str) -> str:
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


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def parse_csv_list(raw: str, cast: Any) -> List[Any]:
    return [cast(x.strip()) for x in str(raw).split(",") if x.strip()]


def stable_seed(*items: Any) -> int:
    payload = json.dumps(items, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


def short_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def layer_label(layer: Any) -> str:
    if isinstance(layer, str) and layer.startswith("L"):
        return layer
    return f"L{int(layer)}"


def get_sample_id(row: Dict[str, Any], sample_i: int) -> str:
    for key in ("case_id", "id", "sample_id"):
        if key in row:
            return str(row[key])
    req = row.get("request", {})
    return short_hash({"i": sample_i, "prompt": req.get("prompt", ""), "target_new": req.get("target_new", "")})


def get_logits(output: Any) -> Any:
    if hasattr(output, "logits"):
        return output.logits
    if isinstance(output, (tuple, list)):
        return output[0]
    raise TypeError(f"Cannot read logits from output type: {type(output)}")


def first_hidden(output: Any) -> Any:
    hidden = output[0] if isinstance(output, (tuple, list)) else output
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("torch is required for tensor helpers") from exc
    if not torch.is_tensor(hidden):
        raise TypeError(f"Hook output does not contain a tensor hidden state: {type(hidden)}")
    return hidden


def validate_visual_span(vt_range: Sequence[int], seq_len: int) -> Tuple[int, int]:
    start, end = int(vt_range[0]), int(vt_range[1])
    if not (0 <= start < end <= seq_len):
        raise ValueError(f"invalid visual span {vt_range} for seq_len={seq_len}")
    return start, end


def hidden_visual_slice(hidden: Any, vt_range: Sequence[int]) -> Any:
    start, end = int(vt_range[0]), int(vt_range[1])
    if hidden.dim() == 3:
        validate_visual_span((start, end), hidden.shape[1])
        return hidden[:, start:end, :]
    if hidden.dim() == 2:
        validate_visual_span((start, end), hidden.shape[0])
        return hidden[start:end, :]
    raise ValueError(f"unsupported hidden dim: {hidden.dim()}")


def replace_visual_slice_with_clean(hidden: Any, vt_range: Sequence[int], clean_visual: Any) -> Any:
    updated = hidden.clone()
    start, end = int(vt_range[0]), int(vt_range[1])
    clean_visual = clean_visual.to(device=hidden.device, dtype=hidden.dtype)
    if hidden.dim() == 3:
        updated[:, start:end, :] = clean_visual
    elif hidden.dim() == 2:
        updated[start:end, :] = clean_visual
    else:
        raise ValueError(f"unsupported hidden dim: {hidden.dim()}")
    return updated


def restore_output_visual_slice(output: Any, vt_range: Sequence[int], clean_visual: Any) -> Any:
    hidden = first_hidden(output)
    updated_hidden = replace_visual_slice_with_clean(hidden, vt_range, clean_visual)
    if isinstance(output, tuple):
        return (updated_hidden,) + output[1:]
    if isinstance(output, list):
        updated = list(output)
        updated[0] = updated_hidden
        return updated
    return updated_hidden


def clone_llm_input(llm_input: Any) -> Any:
    if isinstance(llm_input, dict):
        out = {}
        for key, value in llm_input.items():
            out[key] = value.detach().clone() if hasattr(value, "detach") else value
        return out
    if hasattr(llm_input, "detach"):
        return llm_input.detach().clone()
    raise TypeError(f"Unsupported llm input type for corruption: {type(llm_input)}")


def get_inputs_embeds(llm_input: Any) -> Any:
    if isinstance(llm_input, dict):
        if "inputs_embeds" not in llm_input:
            raise KeyError("llm_input dict has no inputs_embeds")
        return llm_input["inputs_embeds"]
    return llm_input


def make_noise_like(tensor: Any, sigma: float, seed: int) -> Any:
    import torch

    device = tensor.device
    generator = torch.Generator(device=device.type if device.type == "cuda" else "cpu")
    generator.manual_seed(int(seed))
    noise = torch.randn(tensor.shape, device=device, dtype=torch.float32, generator=generator)
    return noise.to(dtype=tensor.dtype) * float(sigma)


def corrupt_llm_input(llm_input: Any, vt_range: Sequence[int], sigma: float, seed: int) -> Any:
    corrupted = clone_llm_input(llm_input)
    embeds = get_inputs_embeds(corrupted)
    start, end = int(vt_range[0]), int(vt_range[1])
    if embeds.dim() != 3:
        raise ValueError(f"inputs_embeds must be [B,T,D], got {tuple(embeds.shape)}")
    validate_visual_span((start, end), embeds.shape[1])
    noise = make_noise_like(embeds[:, start:end, :], sigma, seed)
    embeds[:, start:end, :] = embeds[:, start:end, :] + noise
    return corrupted


def sequence_logprob(logits: Any, label_ids: Any, label_masks: Any) -> float:
    import torch

    logits = logits[:, -label_ids.shape[1] :].float()
    log_probs = torch.log_softmax(logits, -1)
    token_log_probs = log_probs.gather(-1, label_ids.unsqueeze(-1)).squeeze(-1)
    mask = label_masks.float()
    denom = mask.sum()
    if denom.item() <= 0:
        raise ValueError("target mask is empty")
    value = (token_log_probs * mask).sum() / denom
    if not torch.isfinite(value):
        raise FloatingPointError("non-finite sequence logprob")
    return float(value.detach().cpu().item())


def first_token_logprob(logits: Any, label_ids: Any, label_masks: Any) -> float:
    import torch

    logits = logits[:, -label_ids.shape[1] :].float()
    log_probs = torch.log_softmax(logits, -1)
    token_log_probs = log_probs.gather(-1, label_ids.unsqueeze(-1)).squeeze(-1)
    mask = label_masks[0] > 0
    indices = torch.nonzero(mask, as_tuple=False).reshape(-1)
    if int(indices.numel()) <= 0:
        raise ValueError("target mask is empty")
    value = token_log_probs[0, int(indices[0].item())]
    if not torch.isfinite(value):
        raise FloatingPointError("non-finite first-token logprob")
    return float(value.detach().cpu().item())


def compute_kl(clean_logits: Any, other_logits: Any, label_masks: Any) -> float:
    import torch

    clean = clean_logits[:, -label_masks.shape[1] :].float()
    other = other_logits[:, -label_masks.shape[1] :].float()
    log_p_clean = torch.log_softmax(clean, -1)
    log_p_other = torch.log_softmax(other, -1)
    p_clean = torch.softmax(clean, -1)
    kl = (p_clean * (log_p_clean - log_p_other)).sum(-1)
    mask = label_masks.float()
    denom = mask.sum()
    if denom.item() <= 0:
        raise ValueError("target mask is empty")
    value = (kl * mask).sum() / denom
    if not torch.isfinite(value):
        raise FloatingPointError("non-finite KL")
    return float(value.detach().cpu().item())


def restoration_score(s_restore: float, s_corrupt: float, s_clean: float, eps: float) -> float:
    denom = (s_clean - s_corrupt) + float(eps)
    if denom <= 0:
        return float("nan")
    value = (s_restore - s_corrupt) / denom
    return value if math.isfinite(value) else float("nan")


def mean_std_se(values: Sequence[float]) -> Tuple[float, float, float]:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if not vals:
        return float("nan"), float("nan"), float("nan")
    mean = sum(vals) / len(vals)
    std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
    se = std / math.sqrt(len(vals))
    return mean, std, se


def _rank_rows_desc(rows: Sequence[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -(float(row[key]) if math.isfinite(float(row.get(key, float("nan")))) else -1e30),
            int(row["layer"]),
        ),
    )


def _dedup_layer_labels(rows: Iterable[Dict[str, Any]], limit: int) -> List[str]:
    out: List[str] = []
    seen = set()
    for row in rows:
        label = layer_label(row["layer"])
        if label in seen:
            continue
        seen.add(label)
        out.append(label)
        if len(out) >= limit:
            break
    return out


def rank_cma_layers(
    rows: Sequence[Dict[str, Any]],
    topk: int = 5,
    num_layers: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ranked_rows: List[Dict[str, Any]] = []
    invalid_layers: List[Dict[str, str]] = []
    for raw in rows:
        row = dict(raw)
        row["layer"] = int(row["layer"])
        reasons: List[str] = []
        score = finite_float(row.get(RANKING_METRIC))
        valid_count = int(row.get("valid_sample_count") or row.get("valid_samples") or 0)
        if score is None:
            reasons.append(f"nonfinite_{RANKING_METRIC}")
        if valid_count <= 0:
            reasons.append("no_valid_restore_samples")
        if row.get("invalid_reason"):
            reasons.append(str(row["invalid_reason"]))
        row["valid_for_cma_direct"] = not reasons
        row["invalid_reason"] = ";".join(dict.fromkeys(reasons))
        if reasons:
            invalid_layers.append({"layer": layer_label(row["layer"]), "reason": row["invalid_reason"]})
        ranked_rows.append(row)

    raw_ranked = _rank_rows_desc(ranked_rows, RANKING_METRIC)
    clean_ranked = _rank_rows_desc([row for row in ranked_rows if row["valid_for_cma_direct"]], RANKING_METRIC)
    for rank, row in enumerate(clean_ranked, 1):
        row["cma_rank"] = rank
    for row in ranked_rows:
        row.setdefault("cma_rank", "")

    top3 = _dedup_layer_labels(clean_ranked, 3)
    top5 = _dedup_layer_labels(clean_ranked, topk)
    status = "done" if len(top3) >= 3 else "failed"
    failure_reasons = [] if status == "done" else ["valid_layer_count_lt_top3"]
    summary = {
        "method": METHOD_NAME,
        "score_source": SCORE_SOURCE,
        "ranking_metric": RANKING_METRIC,
        "num_layers": num_layers,
        "raw_top3_layers": _dedup_layer_labels(raw_ranked, 3),
        "raw_top5_layers": _dedup_layer_labels(raw_ranked, topk),
        "cleaned_top3_layers": top3,
        "cleaned_top5_layers": top5,
        "top3_layers": top3,
        "top5_layers": top5,
        "invalid_layers": invalid_layers,
        "status": status,
        "failure_reasons": failure_reasons,
    }
    return _rank_rows_desc(ranked_rows, RANKING_METRIC), summary


def load_imgs_with_closed_files(self: Any, data: Any) -> None:
    from PIL import Image

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


def build_mmke_data(data_path: str, img_root: str, data_n: Optional[int] = None) -> List[Dict[str, Any]]:
    from PIL import Image
    from tqdm import tqdm

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


def load_edit_data(dataset_name: str, data_path: str, img_root: str, data_n: Optional[int] = None) -> List[Dict[str, Any]]:
    from dataset.vllm import BaseVLLMEditData, EVQA

    BaseVLLMEditData.__load_imgs_for_data_with_img_path__ = load_imgs_with_closed_files
    if dataset_name == "evqa-pilot500":
        return EVQA(data_path, img_root, data_n).data
    return build_mmke_data(data_path, img_root, data_n)


def write_rows(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_one(args: argparse.Namespace) -> None:
    import torch
    from p_track.p_track import PTrackConfig
    from tqdm import tqdm
    from utils import load_vllm_for_edit
    from utils.nethook import TraceDict

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
    groups = [(scale, repeat) for scale in noise_scales for repeat in repeats]
    if not groups:
        raise ValueError("empty noise-scale/repeat grid")

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

    cr_seq_vals: Dict[int, List[float]] = defaultdict(list)
    cr_first_vals: Dict[int, List[float]] = defaultdict(list)
    kcr_vals: Dict[int, List[float]] = defaultdict(list)
    restore_counts: Dict[int, int] = defaultdict(int)
    hidden_std_sum: Dict[int, float] = defaultdict(float)
    hidden_std_count: Dict[int, int] = defaultdict(int)
    excluded: List[Dict[str, Any]] = []
    started = time.time()
    progress_path = out_dir / "progress.jsonl"

    with progress_path.open("w", encoding="utf-8") as pf:
        for sample_i, row in enumerate(tqdm(data, desc=f"{dataset_name}/{model_name}")):
            sample_id = get_sample_id(row, sample_i)
            try:
                req = row["request"]
                prompt = req["prompt"]
                image = req["image"]
                target = req["target_new"]
                if target is None or str(target).strip() == "":
                    raise ValueError("empty target_new / alt")

                (llm_input, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
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
                    clean_output = vllm.get_llm_outpt(llm_input, vt_range)
                    clean_logits = get_logits(clean_output).detach()
                embeds = get_inputs_embeds(llm_input)
                vt_start, vt_end = validate_visual_span(vt_range, embeds.shape[1])
                if label_masks.sum().item() <= 0:
                    raise ValueError("empty target mask")

                clean_visual_by_layer = {}
                for layer in layer_ids:
                    clean_hidden = first_hidden(td[layer_names[layer]].output)
                    clean_vis = hidden_visual_slice(clean_hidden, vt_range).detach().clone()
                    clean_visual_by_layer[layer] = clean_vis
                    hidden_std_sum[layer] += float(clean_vis.float().std(unbiased=False).detach().cpu().item())
                    hidden_std_count[layer] += 1

                s_clean_seq = sequence_logprob(clean_logits, label_ids, label_masks)
                s_clean_first = first_token_logprob(clean_logits, label_ids, label_masks)

                sample_valid_groups = 0
                for noise_scale, repeat in groups:
                    seed = stable_seed(dataset_name, model_name, sample_id, noise_scale, repeat, vt_start, vt_end)
                    visual_embeds = embeds[:, vt_start:vt_end, :]
                    sigma = float(noise_scale) * max(
                        float(visual_embeds.float().std(unbiased=False).detach().cpu().item()),
                        float(args.epsilon_sigma),
                    )
                    corrupt_input = corrupt_llm_input(llm_input, vt_range, sigma, seed)
                    with torch.no_grad():
                        corrupt_output = vllm.get_llm_outpt(corrupt_input, vt_range)
                        corrupt_logits = get_logits(corrupt_output).detach()

                    s_corrupt_seq = sequence_logprob(corrupt_logits, label_ids, label_masks)
                    s_corrupt_first = first_token_logprob(corrupt_logits, label_ids, label_masks)
                    gap = s_clean_seq - s_corrupt_seq
                    if not math.isfinite(gap) or gap <= float(args.delta_logprob):
                        pf.write(
                            json.dumps(
                                {
                                    "sample": sample_i,
                                    "sample_id": sample_id,
                                    "status": "low_corruption_gap",
                                    "noise_scale": noise_scale,
                                    "repeat": repeat,
                                    "gap": gap,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        pf.flush()
                        continue
                    sample_valid_groups += 1
                    kl_corrupt = compute_kl(clean_logits, corrupt_logits, label_masks)

                    for layer in layer_ids:
                        layer_name = layer_names[layer]
                        clean_vis = clean_visual_by_layer[layer]

                        def edit_output(output: Any, layer: Optional[str] = None, target_layer: str = layer_name, clean: Any = clean_vis) -> Any:
                            if layer != target_layer:
                                return output
                            return restore_output_visual_slice(output, vt_range, clean)

                        with torch.no_grad(), TraceDict(
                            vllm.model,
                            [layer_name],
                            with_kwargs=True,
                            edit_output=edit_output,
                            clone=True,
                            detach=True,
                        ):
                            restore_output = vllm.get_llm_outpt(corrupt_input, vt_range)
                            restore_logits = get_logits(restore_output).detach()
                        s_restore_seq = sequence_logprob(restore_logits, label_ids, label_masks)
                        s_restore_first = first_token_logprob(restore_logits, label_ids, label_masks)
                        cr_seq_vals[layer].append(restoration_score(s_restore_seq, s_corrupt_seq, s_clean_seq, args.eps))
                        cr_first_vals[layer].append(
                            restoration_score(s_restore_first, s_corrupt_first, s_clean_first, args.eps)
                        )
                        if kl_corrupt > args.eps:
                            kl_restore = compute_kl(clean_logits, restore_logits, label_masks)
                            kcr_vals[layer].append((kl_corrupt - kl_restore) / (kl_corrupt + args.eps))
                        restore_counts[layer] += 1
                        del restore_output, restore_logits

                    del corrupt_output, corrupt_logits, corrupt_input

                pf.write(
                    json.dumps(
                        {
                            "sample": sample_i,
                            "sample_id": sample_id,
                            "status": "ok" if sample_valid_groups else "excluded",
                            "valid_noise_repeat_count": sample_valid_groups,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                pf.flush()
                del clean_output, clean_logits, td, clean_visual_by_layer, llm_input, label_ids, label_masks
            except Exception as exc:
                item = {
                    "sample": sample_i,
                    "sample_id": sample_id,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(limit=4),
                }
                excluded.append(item)
                pf.write(json.dumps({"sample": sample_i, "sample_id": sample_id, "status": "excluded", "error": repr(exc)}, ensure_ascii=False) + "\n")
                pf.flush()
            finally:
                if torch.cuda.is_available() and (sample_i + 1) % args.empty_cache_every == 0:
                    torch.cuda.empty_cache()
                gc.collect()

    layer_rows = []
    for layer in layer_ids:
        cr_mean, cr_std, cr_se = mean_std_se(cr_seq_vals[layer])
        first_mean, first_std, first_se = mean_std_se(cr_first_vals[layer])
        kcr_mean, kcr_std, kcr_se = mean_std_se(kcr_vals[layer])
        count = int(restore_counts[layer])
        row = {
            "dataset_key": dataset_name,
            "dataset": DATASET_DISPLAY[dataset_name],
            "model_key": model_name,
            "model": MODEL_DISPLAY[model_name],
            "layer": layer,
            "layer_name": f"L{layer}",
            "cr_seq_mean": cr_mean,
            "cr_seq_std": cr_std,
            "cr_seq_se": cr_se,
            "cr_first_token_mean": first_mean,
            "cr_first_token_std": first_std,
            "cr_first_token_se": first_se,
            "kcr_seq_mean": kcr_mean,
            "kcr_seq_std": kcr_std,
            "kcr_seq_se": kcr_se,
            "valid_sample_count": count,
            "valid_restore_forward_count": count,
            "hidden_std_mean": (
                hidden_std_sum[layer] / hidden_std_count[layer] if hidden_std_count[layer] else float("nan")
            ),
            "invalid_reason": "" if count else "no_valid_restore_samples",
        }
        layer_rows.append(row)

    ranked_rows, rank_summary = rank_cma_layers(layer_rows, topk=5, num_layers=int(cfg.num_layers))
    for idx, row in enumerate(_rank_rows_desc([r for r in ranked_rows if r["valid_for_cma_direct"]], RANKING_METRIC), 1):
        row["rank"] = idx
    for row in ranked_rows:
        row.setdefault("rank", "")

    layer_csv = out_dir / "cma_direct_layer_scores.csv"
    write_rows(layer_csv, ranked_rows)

    coverage_ratio = (
        max((int(r.get("valid_sample_count", 0)) for r in layer_rows), default=0) / max(len(data) * max(len(groups), 1), 1)
    )
    status = rank_summary["status"]
    failure_reasons = list(rank_summary["failure_reasons"])
    if status == "done" and coverage_ratio < args.min_valid_ratio:
        status = "low_confidence"
        failure_reasons.append("low_valid_coverage")

    summary = {
        "dataset_key": dataset_name,
        "dataset": DATASET_DISPLAY[dataset_name],
        "model_key": model_name,
        "model": MODEL_DISPLAY[model_name],
        "method": METHOD_NAME,
        "score_source": SCORE_SOURCE,
        "ranking_metric": RANKING_METRIC,
        "target_sequence": "complete alt sequence",
        "corrupt_scope": "decoder input visual embeddings",
        "restore_scope": "visual tokens only",
        "num_layers": int(cfg.num_layers),
        "noise_scales": noise_scales,
        "repeats": repeats,
        "delta_logprob": args.delta_logprob,
        "manifest_sample_count": len(data),
        "excluded_sample_count": len(excluded),
        "max_layer_valid_restore_count": max((int(r.get("valid_sample_count", 0)) for r in layer_rows), default=0),
        "valid_coverage_ratio": coverage_ratio,
        "top3_layers": rank_summary["top3_layers"],
        "top5_layers": rank_summary["top5_layers"],
        "raw_top3_layers": rank_summary["raw_top3_layers"],
        "raw_top5_layers": rank_summary["raw_top5_layers"],
        "status": status,
        "failure_reasons": failure_reasons,
        "duration_sec": time.time() - started,
        "layer_scores_csv": str(layer_csv),
        "errors": excluded[:50],
    }
    with (out_dir / "candidates_raw.json").open("w", encoding="utf-8") as f:
        json.dump({"top3_layers": summary["raw_top3_layers"], "top5_layers": summary["raw_top5_layers"]}, f, ensure_ascii=False, indent=2)
    with (out_dir / "candidates_clean.json").open("w", encoding="utf-8") as f:
        json.dump({"top3_layers": summary["top3_layers"], "top5_layers": summary["top5_layers"]}, f, ensure_ascii=False, indent=2)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with (out_dir / "summary.md").open("w", encoding="utf-8") as f:
        f.write(f"# {METHOD_NAME}: {DATASET_DISPLAY[dataset_name]} / {MODEL_DISPLAY[model_name]}\n\n")
        f.write(f"- Status: `{status}`\n")
        f.write(f"- Top-3: {','.join(summary['top3_layers']) or '-'}\n")
        f.write(f"- Top-5: {','.join(summary['top5_layers']) or '-'}\n")
        f.write(f"- Score source: `{SCORE_SOURCE}`\n")
        f.write(f"- Valid coverage: {coverage_ratio:.4f}\n")
    (out_dir / "DONE").write_text("done\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def collect(args: argparse.Namespace) -> None:
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
                    f"n={summary.get('max_layer_valid_restore_count', 0)}/{summary.get('manifest_sample_count', 0)}; "
                    f"coverage={summary.get('valid_coverage_ratio', 0):.4f}"
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

    csv_path = run_root / "cma_direct_candidates_summary.csv"
    md_path = run_root / "cma_direct_candidates_summary.md"
    write_rows(csv_path, rows)
    with md_path.open("w", encoding="utf-8") as f:
        f.write("| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for row in rows:
            f.write(
                f"| {row['Dataset']} | {row['Model']} | {row['Method']} | {row['Score source']} "
                f"| {row['Top-3']} | {row['Top-5']} | {row['Status']} |\n"
            )
    print(f"Wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute CMA-Direct candidate layers.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-one")
    run.add_argument("--model-name", required=True)
    run.add_argument("--dataset-name", required=True, choices=DATASET_ORDER)
    run.add_argument("--out-dir", required=True)
    run.add_argument("--device", default="cuda:0")
    run.add_argument("--data-path", default=None)
    run.add_argument("--img-root", default=None)
    run.add_argument("--data-n", type=int, default=None)
    run.add_argument("--noise-scales", default="1")
    run.add_argument("--repeats", default="2026")
    run.add_argument("--delta-logprob", type=float, default=0.05)
    run.add_argument("--min-valid-ratio", type=float, default=0.05)
    run.add_argument("--epsilon-sigma", type=float, default=1e-6)
    run.add_argument("--eps", type=float, default=1e-8)
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
