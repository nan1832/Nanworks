#!/usr/bin/env python3
"""Compute Ours-Direct candidate layers for 7 VLMs on 3 training datasets.

The GPU path intentionally mirrors ``run_perturb_kl_direct_candidate_layers.py``
so the same dataset/model registry is used across candidate-layer methods.
Pure ranking helpers live at top level for fast local tests.
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
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

METHOD_NAME = "Ours-Direct"
SCORE_SOURCE = "virtual_delta_h_visual_gradient"
RANKING_METRIC = "S_ours"

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


def short_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "t"}


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


def _visual_range_invalid(row: Dict[str, Any]) -> bool:
    start = row.get("visual_token_start", row.get("visual_start"))
    end = row.get("visual_token_end", row.get("visual_end"))
    if start in (None, "") or end in (None, ""):
        return True
    if start == "mixed" or end == "mixed":
        return False
    try:
        return int(end) <= int(start)
    except (TypeError, ValueError):
        return True


def _rank_desc(rows: Sequence[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -(row[key] if math.isfinite(row.get(key, float("nan"))) else -1e30),
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


def rank_ours_direct_layers(
    rows: Sequence[Dict[str, Any]],
    topk: int = 5,
    num_layers: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not rows:
        return [], {
            "method": METHOD_NAME,
            "ranking_metric": RANKING_METRIC,
            "status": "failed",
            "failure_reasons": ["no_layer_rows"],
            "top3_layers": [],
            "top5_layers": [],
        }

    max_layer = max(int(row["layer"]) for row in rows)
    layer_count = int(num_layers or (max_layer + 1))
    ranked_rows: List[Dict[str, Any]] = []
    invalid_layers: List[Dict[str, str]] = []
    for raw in rows:
        row = dict(raw)
        layer = int(row["layer"])
        row["layer"] = layer
        cos = finite_float(row.get("S_v_cos"))
        new_norm = finite_float(row.get("S_v_new_norm"))
        reasons: List[str] = []
        if cos is None:
            reasons.append("nonfinite_S_v_cos")
        if new_norm is None:
            reasons.append("nonfinite_S_v_new_norm")
        if parse_bool(row.get("S_v_zero_grad", False)):
            reasons.append("S_v_zero_grad")
        if _visual_range_invalid(row):
            reasons.append("empty_visual_range")

        neg_cos = max(0.0, -cos) if cos is not None else float("nan")
        depth2 = ((layer + 1) / layer_count) ** 2 if layer_count > 0 else float("nan")
        score = neg_cos * new_norm * depth2 if new_norm is not None and math.isfinite(neg_cos) else float("nan")
        if not math.isfinite(score):
            reasons.append("nonfinite_S_ours")

        row["S_v_neg_cos"] = neg_cos
        row["S_v_depth2"] = depth2
        row["S_ours"] = score
        row["invalid_reason"] = ";".join(dict.fromkeys(reasons))
        row["valid_for_ours_direct"] = not reasons
        if reasons:
            invalid_layers.append({"layer": layer_label(layer), "reason": row["invalid_reason"]})
        ranked_rows.append(row)

    valid_ranked = _rank_desc([row for row in ranked_rows if row["valid_for_ours_direct"]], "S_ours")
    raw_ranked = valid_ranked
    candidate_ranked = _rank_desc(
        [row for row in valid_ranked if finite_float(row.get("S_ours")) is not None and float(row["S_ours"]) > 0.0],
        "S_ours",
    )
    for rank, row in enumerate(candidate_ranked, 1):
        row["ours_rank"] = rank
    for row in ranked_rows:
        row.setdefault("ours_rank", "")

    top3 = _dedup_layer_labels(candidate_ranked, 3)
    top5 = _dedup_layer_labels(candidate_ranked, topk)
    status = "done" if top3 else "failed"
    failure_reasons = [] if top3 else ["no_valid_ours_direct_layer"]
    summary = {
        "method": METHOD_NAME,
        "score_source": SCORE_SOURCE,
        "ranking_metric": RANKING_METRIC,
        "rank_formula": "max(0, -S_v_cos) * S_v_new_norm * ((layer + 1) / num_layers)^2",
        "num_layers": layer_count,
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
    return _rank_desc(ranked_rows, "S_ours"), summary


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


def load_imgs_with_closed_files(self, data: Any) -> None:
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


def get_sample_id(row: Dict[str, Any], sample_i: int) -> str:
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


def set_model_eval(vllm: Any) -> None:
    vllm.model.eval()
    for param in vllm.model.parameters():
        param.requires_grad_(False)


def clean_generated_text(text: str, prompt: str) -> str:
    cleaned = (text or "").strip()
    for marker in ["ASSISTANT:", "Assistant:", "assistant:", "[/INST]"]:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[-1].strip()
    if prompt and prompt in cleaned:
        cleaned = cleaned.split(prompt, 1)[-1].strip()
    for token in ["</s>", "<|im_end|>", "<eos>"]:
        if token in cleaned:
            cleaned = cleaned.split(token, 1)[0].strip()
    return cleaned.replace("<s>", "").strip()


def generate_model_pred(vllm: Any, model_name: str, prompt: str, image: Any, max_new_tokens: int) -> str:
    import torch

    name = normalize_model_name(model_name)
    with torch.no_grad():
        if name == "minigpt-4-vicuna-7b":
            # MiniGPT-4 expects exactly one <ImageHere> placeholder for each image.
            # Dataset prompts are plain text, so add the visual placeholder here.
            minigpt_prompt = prompt if "<ImageHere>" in prompt else f"<ImageHere>\n{prompt}"
            img_tensor = vllm.img_processor(image).unsqueeze(0)
            answer = vllm.model.generate(
                img_tensor,
                [minigpt_prompt],
                max_new_tokens=max_new_tokens,
                num_beams=1,
                do_sample=False,
                temperature=1,
            )[0]
            return clean_generated_text(answer, prompt)

        if name == "llava-v1.5-7b":
            text = prompt if "<image>" in prompt else f"<image>\n{prompt}"
            inputs = vllm.processor(text=text, images=image, return_tensors="pt")
        elif name == "qwen2.5-vl-3b":
            image = image.convert("RGB").resize((getattr(vllm, "image_size", 448), getattr(vllm, "image_size", 448)))
            text = f"{vllm.get_img_special_token_str()}\n{prompt}"
            inputs = vllm.processor(text=[text], images=[image], return_tensors="pt", padding=True)
        elif name == "smolvlm-1.7b":
            messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
            if hasattr(vllm.processor, "apply_chat_template"):
                text = vllm.processor.apply_chat_template(messages, add_generation_prompt=True)
                inputs = vllm.processor(text=[text], images=[[image]], return_tensors="pt", padding=True)
            else:
                inputs = vllm.processor(text=[prompt], images=[[image]], return_tensors="pt", padding=True)
        elif name in {"blip2-opt-2.7b", "instructblip-vicuna-7b", "paligemma-3b"}:
            inputs = vllm.processor(images=image, text=prompt, return_tensors="pt", padding=True)
        else:
            raise ValueError(f"Generation is not implemented for {model_name}")

        inputs = {k: v.to(vllm.device) if hasattr(v, "to") else v for k, v in inputs.items()}
        if name == "paligemma-3b":
            # PaliGemma is loaded in bf16 on this server; processor pixel_values
            # default to fp32, which breaks generate unless they match.
            model_dtype = next(vllm.model.parameters()).dtype
            for key, value in list(inputs.items()):
                if hasattr(value, "is_floating_point") and value.is_floating_point():
                    inputs[key] = value.to(dtype=model_dtype)
        generated = vllm.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, num_beams=1)
        tokenizer = vllm.get_llm_tokenizer()
        if name in {"llava-v1.5-7b", "qwen2.5-vl-3b", "paligemma-3b", "smolvlm-1.7b"}:
            input_len = int(inputs["input_ids"].shape[1]) if "input_ids" in inputs else 0
            generated_ids = generated[:, input_len:] if input_len and generated.shape[1] > input_len else generated
            text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        else:
            text = vllm.processor.batch_decode(generated, skip_special_tokens=True)[0]
        return clean_generated_text(text, prompt)


def load_model_pred_cache(path: Path) -> Dict[str, Dict[str, Any]]:
    cache: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return cache
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sample_id = str(row.get("sample_id") or "")
            if sample_id:
                cache[sample_id] = row
    return cache


def ensure_model_pred_cache(
    vllm: Any,
    model_name: str,
    data: Sequence[Dict[str, Any]],
    cache_path: Path,
    max_new_tokens: int,
) -> Dict[str, Dict[str, Any]]:
    cache = load_model_pred_cache(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("a", encoding="utf-8") as f:
        for sample_i, row in enumerate(data):
            sample_id = get_sample_id(row, sample_i)
            if sample_id in cache:
                continue
            req = row["request"]
            try:
                answer = generate_model_pred(vllm, model_name, req["prompt"], req["image"], max_new_tokens)
                status = "ok" if answer else "empty_model_pred"
                item = {
                    "sample_i": sample_i,
                    "sample_id": sample_id,
                    "prompt": req["prompt"],
                    "answer": answer,
                    "status": status,
                    "old_field": "model_pred",
                }
            except Exception as exc:  # generation failures should not poison the cache file
                item = {
                    "sample_i": sample_i,
                    "sample_id": sample_id,
                    "prompt": req["prompt"],
                    "answer": "",
                    "status": "generation_failed",
                    "error": repr(exc),
                    "traceback": traceback.format_exc(limit=3),
                    "old_field": "model_pred",
                }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()
            cache[sample_id] = item
    return cache


def tensor_from_layer_output(output: Any) -> Any:
    if isinstance(output, tuple):
        output = output[0]
    return output


def prepare_llm_inputs_for_hidden_grad(llm_inpt: Dict[str, Any]) -> Dict[str, Any]:
    prepared = {}
    for key, value in llm_inpt.items():
        if key == "inputs_embeds":
            prepared[key] = value.detach().clone().requires_grad_(True)
        elif hasattr(value, "detach"):
            prepared[key] = value.detach()
        else:
            prepared[key] = value
    return prepared


def answer_loss_positions(label_masks: Any, seq_len: int) -> set:
    import torch

    label_len = int(label_masks.shape[1])
    tail_start = max(seq_len - label_len, 0)
    mask = label_masks[0].detach()
    indices = torch.nonzero(mask > 0, as_tuple=False).reshape(-1).tolist()
    return {tail_start + int(idx) for idx in indices if tail_start + int(idx) < seq_len}


def prompt_text_indices(seq_len: int, vt_range: Tuple[int, int], llm_inpt: Dict[str, Any], label_masks: Any) -> List[int]:
    import torch

    attention_mask = llm_inpt.get("attention_mask")
    if attention_mask is None:
        valid = set(range(seq_len))
    else:
        mask = attention_mask[0].detach()
        valid = {int(idx) for idx in torch.nonzero(mask > 0, as_tuple=False).reshape(-1).tolist() if int(idx) < seq_len}

    vt_start, vt_end = int(vt_range[0]), int(vt_range[1])
    visual = set(range(vt_start, min(vt_end, seq_len)))
    answer_like = answer_loss_positions(label_masks, seq_len)
    indices = sorted(valid - visual - answer_like)
    if indices:
        return indices

    label_len = int(label_masks.shape[1])
    tail_start = max(seq_len - label_len, 0)
    return sorted(idx for idx in (valid - visual) if idx < tail_start)


def grad_stats(old_grad: Any, new_grad: Any, eps: float) -> Dict[str, float]:
    import torch

    old_flat = old_grad.float().reshape(-1)
    new_flat = new_grad.float().reshape(-1)
    dot = float(torch.sum(old_flat * new_flat).item())
    old_norm = float(torch.linalg.vector_norm(old_flat).item())
    new_norm = float(torch.linalg.vector_norm(new_flat).item())
    joint = old_norm * new_norm
    numel = max(int(old_flat.numel()), 1)
    return {
        "dot": dot,
        "conflict": -dot,
        "dot_per_dim": dot / numel,
        "cos": dot / (joint + 1e-12),
        "old_norm": old_norm,
        "new_norm": new_norm,
        "joint_norm": joint,
        "old_nonzero_ratio": float((old_flat.abs() > eps).float().mean().item()),
        "new_nonzero_ratio": float((new_flat.abs() > eps).float().mean().item()),
        "numel": float(numel),
    }


def compute_virtual_delta_target_grad(
    vllm: Any,
    layer_module: Any,
    prompt: str,
    image: Any,
    target: str,
    zero_grad_eps: float,
) -> Dict[str, Any]:
    import torch

    captured: Dict[str, Any] = {}

    def retain_hidden_hook(module, args, output):
        hidden = tensor_from_layer_output(output)
        if not torch.is_tensor(hidden):
            raise TypeError(f"Expected tensor layer output, got {type(hidden)!r}")
        if not hidden.requires_grad:
            raise RuntimeError("Captured hidden state does not require grad")
        hidden.retain_grad()
        captured["hidden"] = hidden

    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym([prompt], [image], [target])
    if vt_range is None:
        raise RuntimeError("Ours-Direct requires a non-empty visual token range")
    vt_start, vt_end = int(vt_range[0]), int(vt_range[1])
    if vt_end <= vt_start:
        raise RuntimeError(f"Invalid visual token range: {vt_range}")
    if label_masks.sum().item() <= 0:
        raise RuntimeError("Target mask is empty")

    llm_inpt = prepare_llm_inputs_for_hidden_grad(llm_inpt)
    vllm.model.zero_grad(set_to_none=True)
    hook = layer_module.register_forward_hook(retain_hidden_hook)
    try:
        output = vllm.get_llm_outpt(llm_inpt, vt_range)
        loss = vllm.label_loss(output.logits, label_ids, label_masks, average=True)
        loss.backward()
        hidden = captured.get("hidden")
        if hidden is None or hidden.grad is None:
            raise RuntimeError("Layer hidden gradient was not captured")
        grad = hidden.grad.detach().float().cpu().contiguous()
        if vt_end > grad.shape[1]:
            raise RuntimeError(f"Visual token range {vt_start}:{vt_end} exceeds seq len {grad.shape[1]}")
        text_idx = prompt_text_indices(int(grad.shape[1]), (vt_start, vt_end), llm_inpt, label_masks)
        if not text_idx:
            raise RuntimeError("No text prompt tokens remained after excluding visual and answer positions")

        text_index = torch.tensor(text_idx, dtype=torch.long)
        visual_grad = grad[:, vt_start:vt_end, :]
        text_grad = grad.index_select(1, text_index)
        return {
            "loss": float(loss.detach().float().cpu().item()),
            "visual_grad": visual_grad,
            "text_grad": text_grad,
            "visual_span": (vt_start, vt_end),
            "text_token_count": len(text_idx),
            "seq_len": int(grad.shape[1]),
            "answer_loss_position_count": len(answer_loss_positions(label_masks, int(grad.shape[1]))),
            "visual_nonzero_ratio": float((visual_grad.abs() > zero_grad_eps).float().mean().item()),
            "text_nonzero_ratio": float((text_grad.abs() > zero_grad_eps).float().mean().item()),
        }
    finally:
        hook.remove()
        vllm.model.zero_grad(set_to_none=True)


def find_module(module: Any, module_path: str) -> Any:
    for comp in module_path.split("."):
        if hasattr(module, comp):
            module = getattr(module, comp)
        elif comp.isdigit():
            module = module[int(comp)]
        else:
            raise RuntimeError(f"Could not find child module {comp} in {module_path}")
    return module


def init_accum() -> Dict[str, Any]:
    return {
        "v_dot": 0.0,
        "v_conflict": 0.0,
        "v_dot_per_dim": 0.0,
        "v_cos": 0.0,
        "v_old_norm": 0.0,
        "v_new_norm": 0.0,
        "v_joint_norm": 0.0,
        "v_old_nonzero_ratio": 0.0,
        "v_new_nonzero_ratio": 0.0,
        "v_positive_count": 0,
        "v_dots": [],
        "t_dot": 0.0,
        "t_conflict": 0.0,
        "t_dot_per_dim": 0.0,
        "t_cos": 0.0,
        "t_old_norm": 0.0,
        "t_new_norm": 0.0,
        "t_joint_norm": 0.0,
        "t_old_nonzero_ratio": 0.0,
        "t_new_nonzero_ratio": 0.0,
        "t_positive_count": 0,
        "t_dots": [],
        "n_request": 0,
        "visual_spans": set(),
        "text_token_count_sum": 0,
        "answer_loss_position_count_sum": 0,
    }


def add_stats(accum: Dict[str, Any], old_out: Dict[str, Any], new_out: Dict[str, Any], zero_grad_eps: float) -> None:
    v_stats = grad_stats(old_out["visual_grad"], new_out["visual_grad"], zero_grad_eps)
    t_stats = grad_stats(old_out["text_grad"], new_out["text_grad"], zero_grad_eps)
    for prefix, stats in [("v", v_stats), ("t", t_stats)]:
        accum[f"{prefix}_dot"] += stats["dot"]
        accum[f"{prefix}_conflict"] += stats["conflict"]
        accum[f"{prefix}_dot_per_dim"] += stats["dot_per_dim"]
        accum[f"{prefix}_cos"] += stats["cos"]
        accum[f"{prefix}_old_norm"] += stats["old_norm"]
        accum[f"{prefix}_new_norm"] += stats["new_norm"]
        accum[f"{prefix}_joint_norm"] += stats["joint_norm"]
        accum[f"{prefix}_old_nonzero_ratio"] += stats["old_nonzero_ratio"]
        accum[f"{prefix}_new_nonzero_ratio"] += stats["new_nonzero_ratio"]
        accum[f"{prefix}_positive_count"] += 1 if stats["dot"] > 0 else 0
        accum[f"{prefix}_dots"].append(stats["dot"])
    accum["n_request"] += 1
    accum["visual_spans"].add(tuple(old_out["visual_span"]))
    accum["text_token_count_sum"] += old_out["text_token_count"]
    accum["answer_loss_position_count_sum"] += old_out["answer_loss_position_count"]


def layer_rows_from_accum(
    dataset_name: str,
    model_name: str,
    layer_ids: Sequence[int],
    layer_names: Dict[int, str],
    accum: Dict[int, Dict[str, Any]],
    zero_grad_eps: float,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for layer in layer_ids:
        a = accum[layer]
        n = int(a["n_request"])
        spans = sorted(a["visual_spans"])
        if n <= 0:
            row = {
                "dataset_key": dataset_name,
                "dataset": DATASET_DISPLAY[dataset_name],
                "model_key": model_name,
                "model": MODEL_DISPLAY[model_name],
                "layer": layer,
                "layer_name": f"L{layer}",
                "layer_path": layer_names[layer],
                "n_request": 0,
                "visual_token_start": "",
                "visual_token_end": "",
                "S_v_cos": float("nan"),
                "S_v_new_norm": float("nan"),
                "S_v_zero_grad": True,
            }
            rows.append(row)
            continue
        visual_start = spans[0][0] if len(spans) == 1 else "mixed"
        visual_end = spans[0][1] if len(spans) == 1 else "mixed"
        v_old_norm = a["v_old_norm"] / n
        v_new_norm = a["v_new_norm"] / n
        t_old_norm = a["t_old_norm"] / n
        t_new_norm = a["t_new_norm"] / n
        rows.append(
            {
                "dataset_key": dataset_name,
                "dataset": DATASET_DISPLAY[dataset_name],
                "model_key": model_name,
                "model": MODEL_DISPLAY[model_name],
                "layer": layer,
                "layer_name": f"L{layer}",
                "layer_path": layer_names[layer],
                "n_request": n,
                "visual_token_start": visual_start,
                "visual_token_end": visual_end,
                "text_token_count_mean": a["text_token_count_sum"] / n,
                "answer_loss_position_count_mean": a["answer_loss_position_count_sum"] / n,
                "S_v_dot": a["v_dot"] / n,
                "S_v_conflict": a["v_conflict"] / n,
                "S_v_dot_per_dim": a["v_dot_per_dim"] / n,
                "S_v_cos": a["v_cos"] / n,
                "S_v_old_norm": v_old_norm,
                "S_v_new_norm": v_new_norm,
                "S_v_joint_norm": a["v_joint_norm"] / n,
                "S_v_positive_ratio": a["v_positive_count"] / n,
                "S_v_zero_grad": bool(v_old_norm < zero_grad_eps or v_new_norm < zero_grad_eps),
                "S_v_old_nonzero_ratio": a["v_old_nonzero_ratio"] / n,
                "S_v_new_nonzero_ratio": a["v_new_nonzero_ratio"] / n,
                "median_v_dot": median(a["v_dots"]) if a["v_dots"] else float("nan"),
                "S_t_dot": a["t_dot"] / n,
                "S_t_conflict": a["t_conflict"] / n,
                "S_t_dot_per_dim": a["t_dot_per_dim"] / n,
                "S_t_cos": a["t_cos"] / n,
                "S_t_old_norm": t_old_norm,
                "S_t_new_norm": t_new_norm,
                "S_t_joint_norm": a["t_joint_norm"] / n,
                "S_t_positive_ratio": a["t_positive_count"] / n,
                "S_t_zero_grad": bool(t_old_norm < zero_grad_eps or t_new_norm < zero_grad_eps),
                "S_t_old_nonzero_ratio": a["t_old_nonzero_ratio"] / n,
                "S_t_new_nonzero_ratio": a["t_new_nonzero_ratio"] / n,
                "median_t_dot": median(a["t_dots"]) if a["t_dots"] else float("nan"),
            }
        )
    ranked, _ = rank_ours_direct_layers(rows, topk=5, num_layers=len(layer_ids))
    return ranked


def run_one(args: argparse.Namespace) -> None:
    import torch
    from p_track.p_track import PTrackConfig
    from tqdm import tqdm
    from utils import load_vllm_for_edit

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
    layer_ids = list(range(int(cfg.num_layers)))
    layer_names = {layer: cfg.layer_module_tmp.format(layer) for layer in layer_ids}

    vllm = load_vllm_for_edit(model_name, args.device)
    set_model_eval(vllm)

    model_pred_cache_path = out_dir / "model_pred_cache.jsonl"
    model_pred_cache = ensure_model_pred_cache(
        vllm,
        model_name,
        data,
        model_pred_cache_path,
        max_new_tokens=args.max_new_tokens,
    )

    started = time.time()
    accum: Dict[int, Dict[str, Any]] = {layer: init_accum() for layer in layer_ids}
    excluded: List[Dict[str, Any]] = []
    sample_path = out_dir / "ours_direct_sample_layer_scores.jsonl"
    progress_path = out_dir / "progress.jsonl"

    with sample_path.open("w", encoding="utf-8") as sample_f, progress_path.open("w", encoding="utf-8") as progress_f:
        for layer in layer_ids:
            layer_module = find_module(vllm.model, layer_names[layer])
            for sample_i, row in enumerate(tqdm(data, desc=f"{dataset_name}/{model_name}/L{layer}")):
                sample_id = get_sample_id(row, sample_i)
                req = row["request"]
                cache_item = model_pred_cache.get(sample_id, {})
                old_answer = str(cache_item.get("answer") or "").strip()
                if not old_answer:
                    excluded.append(
                        {
                            "sample_i": sample_i,
                            "sample_id": sample_id,
                            "layer": layer,
                            "reason": cache_item.get("status", "missing_model_pred"),
                        }
                    )
                    continue
                try:
                    old_out = compute_virtual_delta_target_grad(
                        vllm, layer_module, req["prompt"], req["image"], old_answer, args.zero_grad_eps
                    )
                    new_out = compute_virtual_delta_target_grad(
                        vllm, layer_module, req["prompt"], req["image"], str(req["target_new"]), args.zero_grad_eps
                    )
                    add_stats(accum[layer], old_out, new_out, args.zero_grad_eps)
                    sample_f.write(
                        json.dumps(
                            {
                                "sample_i": sample_i,
                                "sample_id": sample_id,
                                "layer": layer,
                                "old_field": "model_pred",
                                "old_answer": old_answer,
                                "target_new": req["target_new"],
                                "old_loss": old_out["loss"],
                                "new_loss": new_out["loss"],
                                "visual_span": old_out["visual_span"],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                except Exception as exc:
                    excluded.append(
                        {
                            "sample_i": sample_i,
                            "sample_id": sample_id,
                            "layer": layer,
                            "reason": "gradient_failed",
                            "error": repr(exc),
                            "traceback": traceback.format_exc(limit=3),
                        }
                    )
                finally:
                    progress_f.write(
                        json.dumps(
                            {
                                "sample_i": sample_i,
                                "sample_id": sample_id,
                                "layer": layer,
                                "n_request_layer": accum[layer]["n_request"],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    progress_f.flush()
                    if torch.cuda.is_available() and (sample_i + 1) % args.empty_cache_every == 0:
                        torch.cuda.empty_cache()
                    gc.collect()

    layer_rows = layer_rows_from_accum(dataset_name, model_name, layer_ids, layer_names, accum, args.zero_grad_eps)
    _, candidates = rank_ours_direct_layers(layer_rows, topk=5, num_layers=cfg.num_layers)
    for row in layer_rows:
        row["candidate_rank_metric"] = RANKING_METRIC
    layer_csv = out_dir / "ours_direct_layer_scores.csv"
    write_rows(layer_csv, layer_rows)

    common_counts = [int(accum[layer]["n_request"]) for layer in layer_ids]
    common_valid = min(common_counts) if common_counts else 0
    max_valid = max(common_counts) if common_counts else 0
    coverage_ratio = common_valid / len(data) if data else 0.0
    status = candidates["status"]
    failure_reasons = list(candidates.get("failure_reasons", []))
    if common_valid == 0 and "no_common_valid_samples" not in failure_reasons:
        status = "failed"
        failure_reasons.append("no_common_valid_samples")
    elif coverage_ratio < args.min_coverage and status == "done":
        status = "low_confidence"
        failure_reasons.append("low_coverage")
    if common_valid != max_valid and status == "done":
        status = "low_confidence"
        failure_reasons.append("inconsistent_sample_coverage_across_layers")

    summary = {
        "dataset_key": dataset_name,
        "dataset": DATASET_DISPLAY[dataset_name],
        "model_key": model_name,
        "model": MODEL_DISPLAY[model_name],
        "method": METHOD_NAME,
        "score_source": SCORE_SOURCE,
        "old_field": "model_pred",
        "new_field": "alt",
        "ranking_metric": RANKING_METRIC,
        "candidate_conversion": "direct",
        "num_layers": cfg.num_layers,
        "manifest_sample_count": len(data),
        "common_valid_sample_count": common_valid,
        "max_valid_sample_count": max_valid,
        "coverage_ratio": coverage_ratio,
        "top3_layers": candidates["top3_layers"],
        "top5_layers": candidates["top5_layers"],
        "raw_top3_layers": candidates["raw_top3_layers"],
        "raw_top5_layers": candidates["raw_top5_layers"],
        "status": status,
        "failure_reasons": failure_reasons,
        "invalid_layers": candidates["invalid_layers"],
        "duration_sec": time.time() - started,
        "model_pred_cache": str(model_pred_cache_path),
        "layer_scores_csv": str(layer_csv),
        "sample_layer_scores_jsonl": str(sample_path),
        "excluded_count": len(excluded),
        "excluded_examples": excluded[:100],
    }
    with (out_dir / "ours_direct_candidates.json").open("w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
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
                    f"n={summary.get('common_valid_sample_count')}/{summary.get('manifest_sample_count')}"
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

    csv_path = run_root / "ours_direct_candidates_summary.csv"
    write_rows(csv_path, rows)
    md_path = run_root / "ours_direct_candidates_summary.md"
    lines = [
        "| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['Dataset']} | {row['Model']} | {row['Method']} | {row['Score source']} | "
            f"{row['Top-3']} | {row['Top-5']} | {row['Status']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {md_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute Ours-Direct candidate layers.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-one")
    run.add_argument("--model-name", required=True)
    run.add_argument("--dataset-name", required=True, choices=DATASET_ORDER)
    run.add_argument("--out-dir", required=True)
    run.add_argument("--device", default="cuda:0")
    run.add_argument("--data-path", default=None)
    run.add_argument("--img-root", default=None)
    run.add_argument("--data-n", type=int, default=None)
    run.add_argument("--max-new-tokens", type=int, default=32)
    run.add_argument("--zero-grad-eps", type=float, default=1e-8)
    run.add_argument("--min-coverage", type=float, default=0.8)
    run.add_argument("--empty-cache-every", type=int, default=1)
    run.add_argument("--resume", action="store_true")
    run.set_defaults(func=run_one)

    col = sub.add_parser("collect")
    col.add_argument("--run-root", required=True)
    col.set_defaults(func=collect)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
