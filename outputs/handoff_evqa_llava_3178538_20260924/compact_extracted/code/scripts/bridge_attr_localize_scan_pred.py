import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import yaml
from PIL import Image
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils import load_vllm_for_edit
from utils.nethook import TraceDict, get_module


ANSWER_STUB = " The answer is:"


@dataclass
class BridgeSample:
    image: Image.Image
    prompt: str
    sample_id: str
    target_text: str
    entity_name: str
    image_path: str


def find_bridge_root() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    search_roots = [
        repo_root.parent,
        repo_root.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
        Path.cwd().parent.parent,
    ]
    for base in search_roots:
        candidate = base / "Ten_Classes" / "bridge"
        if candidate.exists():
            return candidate
    return repo_root.parent / "Ten_Classes" / "bridge"


def parse_args():
    bridge_root = find_bridge_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", type=str, default="llava-v1.5-7b")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--config-path", type=str, default="configs/p_track/llava-v1.5-7b.yaml")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(bridge_root / "bridge_train" / "edit_30_bridge_train_only_vis.json"),
    )
    parser.add_argument("--bridge-root", type=str, default=str(bridge_root))
    parser.add_argument("--max-samples", type=int, default=4)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--noise-level", type=float, default=0.30)
    parser.add_argument("--layer-start", type=int, default=0)
    parser.add_argument("--layer-end", type=int, default=-1)
    parser.add_argument("--topk-layers", type=int, default=5)
    parser.add_argument(
        "--output-dir",
        type=str,
        default="records/bridge_attr_localize_pred",
    )
    return parser.parse_args()


def read_config(config_path: str) -> Dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_bridge_image_path(
    rel_path: str,
    bridge_root: str,
    img_path_map: Optional[Dict[str, str]] = None,
) -> str:
    if img_path_map is None:
        img_path_map = {
            "train/images": "bridge_train/bridge_images",
            "val/images": "bridge_val/bridge_images",
        }
    remapped = rel_path
    for src_prefix, dst_prefix in img_path_map.items():
        if remapped.startswith(src_prefix):
            remapped = dst_prefix + remapped[len(src_prefix) :]
            break
    return os.path.join(bridge_root, remapped)


def load_bridge_samples(
    data_path: str,
    bridge_root: str,
    max_samples: Optional[int] = None,
) -> List[BridgeSample]:
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    samples: List[BridgeSample] = []
    for i, item in enumerate(raw):
        if max_samples is not None and i >= max_samples:
            break
        req = item["request"]
        image_path = resolve_bridge_image_path(req["image"], bridge_root)
        prompt = req["prompt"]
        if not prompt.endswith(ANSWER_STUB):
            prompt = f"{prompt}{ANSWER_STUB}"
        image = Image.open(image_path).convert("RGB")
        samples.append(
            BridgeSample(
                image=image,
                prompt=prompt,
                sample_id=str(item.get("case_id", f"bridge_{i}")),
                target_text=req["target_new"],
                entity_name=item.get("entity_name", req["target_new"]),
                image_path=image_path,
            )
        )
    return samples


def safe_softmax_last(logits: torch.Tensor) -> torch.Tensor:
    probs = torch.softmax(logits[0, -1], dim=-1)
    return torch.clamp(probs, min=1e-12)


def kl_p0_p1(p0: torch.Tensor, p1: torch.Tensor) -> float:
    value = torch.sum(p0 * (torch.log(p0) - torch.log(p1))).item()
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


def apply_noise_to_hidden(hs: torch.Tensor, token_ids: List[int], noise_level: float) -> torch.Tensor:
    if len(token_ids) == 0:
        return hs
    hidden = hs.clone()
    device = hidden.device
    index = torch.tensor(token_ids, device=device, dtype=torch.long)
    noise = torch.randn((len(token_ids), hidden.shape[-1]), device=device, dtype=hidden.dtype)
    hidden[0, index] = hidden[0, index] + noise * noise_level
    return hidden


def extract_hidden_tensor(output) -> torch.Tensor:
    hidden = output[0] if isinstance(output, (list, tuple)) else output
    if hidden.dim() == 2:
        hidden = hidden.unsqueeze(0)
    return hidden


def perturb_one_layer(
    vllm,
    llm_inpt,
    vt_range: Tuple[int, int],
    layer_name: str,
    token_ids: List[int],
    noise_level: float,
) -> torch.Tensor:
    def edit_output(output, layer=None):
        if layer != layer_name:
            return output
        if isinstance(output, tuple):
            hidden = apply_noise_to_hidden(output[0], token_ids, noise_level)
            return (hidden,) + output[1:]
        if isinstance(output, list):
            updated = list(output)
            updated[0] = apply_noise_to_hidden(updated[0], token_ids, noise_level)
            return updated
        return apply_noise_to_hidden(output, token_ids, noise_level)

    with torch.no_grad(), TraceDict(
        vllm.model,
        [layer_name],
        with_kwargs=True,
        edit_output=edit_output,
        clone=True,
        detach=True,
    ):
        out = vllm.get_llm_outpt(llm_inpt, vt_range).logits
    return out


def normalize_token_piece(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^0-9a-z]+", "", lowered)
    return lowered


def extract_anchor_word(prompt: str) -> Optional[str]:
    question = prompt.split(ANSWER_STUB)[0]
    words = re.findall(r"[A-Za-z0-9]+", question.lower())
    if not words:
        return None
    return words[-1]


def find_subsequence(values: List[int], query: List[int]) -> Optional[int]:
    if len(query) == 0 or len(query) > len(values):
        return None
    end = len(values) - len(query) + 1
    for start in range(end):
        if values[start : start + len(query)] == query:
            return start
    return None


def find_text_anchor_indices(
    vllm,
    sample: BridgeSample,
    vt_range: Tuple[int, int],
    track_idx: int,
) -> Tuple[Optional[str], List[int]]:
    anchor_word = extract_anchor_word(sample.prompt)
    if anchor_word is None:
        return None, [track_idx]

    try:
        proc = vllm.processor([sample.prompt], [sample.image], return_tensors="pt", padding=True)
        input_ids = proc["input_ids"][0].tolist()
        tokenizer = vllm.get_llm_tokenizer()
        image_token_id = vllm.get_img_special_token_id()
        image_pos = input_ids.index(image_token_id)
        shift = vllm.get_img_token_n() - 1

        text_only_ids = []
        text_only_to_merged = []
        for idx, token_id in enumerate(input_ids):
            if token_id == image_token_id:
                continue
            merged_idx = idx if idx < image_pos else idx + shift
            text_only_ids.append(token_id)
            text_only_to_merged.append(merged_idx)

        stub_ids = tokenizer(ANSWER_STUB, add_special_tokens=False).input_ids
        stub_start = find_subsequence(text_only_ids, stub_ids)
        if stub_start is None:
            stub_start = len(text_only_ids)

        stopwords = {"what", "is", "the", "name", "of", "this", "which", "shown", "picture"}
        matches = []
        for text_pos in range(stub_start - 1, -1, -1):
            token_id = text_only_ids[text_pos]
            token_piece = tokenizer.convert_ids_to_tokens(token_id)
            piece = normalize_token_piece(token_piece)
            if not piece or piece in stopwords:
                continue
            matches.append(text_only_to_merged[text_pos])
            if anchor_word in piece or piece in anchor_word:
                break
            if len(matches) >= 2:
                break
        if matches:
            return anchor_word, sorted(set(matches))
    except Exception:
        pass
    return anchor_word, [track_idx]


def get_target_token_info(tokenizer, target_text: str) -> Tuple[int, str]:
    token_ids = tokenizer(f" {target_text}", add_special_tokens=False).input_ids
    if len(token_ids) == 0:
        token_ids = tokenizer(target_text, add_special_tokens=False).input_ids
    if len(token_ids) == 0:
        raise ValueError(f"Failed to tokenize target text: {target_text}")
    token_id = int(token_ids[0])
    token_text = tokenizer.convert_ids_to_tokens(token_id)
    return token_id, token_text


def rep_token_stats(norm, voc, rep: torch.Tensor, token_id: int) -> Tuple[float, float]:
    logits = voc(norm(rep))
    probs = torch.softmax(logits, dim=-1)
    return float(logits[token_id]), float(probs[token_id])


def cosine_similarity_safe(x: torch.Tensor, y: torch.Tensor) -> float:
    if torch.norm(x) == 0 or torch.norm(y) == 0:
        return 0.0
    return float(torch.nn.functional.cosine_similarity(x.unsqueeze(0), y.unsqueeze(0), dim=-1)[0])


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def top_layers(rows: List[Dict], key: str, topk: int) -> List[int]:
    sorted_rows = sorted(rows, key=lambda row: row[key], reverse=True)
    return [int(row["layer"]) for row in sorted_rows[:topk]]


def main():
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, "samples"), exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, "visual_reps"), exist_ok=True)

    cfg = read_config(args.config_path)
    num_layers = int(cfg["num_layers"])
    layer_tmp = cfg["layer_module_tmp"]
    attn_tmp = cfg["attn_module_tmp"]
    mlp_tmp = cfg["mlp_module_tmp"]

    layer_start = max(0, args.layer_start)
    layer_end = num_layers if args.layer_end < 0 else min(num_layers, args.layer_end)
    layers = list(range(layer_start, layer_end))
    layer_names = [layer_tmp.format(idx) for idx in layers]
    attn_names = [attn_tmp.format(idx) for idx in layers]
    mlp_names = [mlp_tmp.format(idx) for idx in layers]
    trace_names = layer_names + attn_names + mlp_names

    samples = load_bridge_samples(args.data_path, args.bridge_root, args.max_samples)
    if len(samples) == 0:
        raise RuntimeError("No bridge samples were loaded.")

    vllm = load_vllm_for_edit(args.model_name, args.device)
    tokenizer = vllm.get_llm_tokenizer()
    norm = get_module(vllm.model, cfg["norm_path"])
    voc = get_module(vllm.model, cfg["voc_path"])

    metric_names = [
        "visual_rep_norm",
        "visual_track_cos",
        "layer_target_logit",
        "layer_target_prob",
        "layer_pred_logit",
        "layer_pred_prob",
        "att_target_logit",
        "att_target_prob",
        "att_target_pxv",
        "mlp_target_logit",
        "mlp_target_prob",
        "mlp_target_pxv",
        "att_pred_logit",
        "att_pred_prob",
        "att_pred_pxv",
        "mlp_pred_logit",
        "mlp_pred_prob",
        "mlp_pred_pxv",
        "kl_visual",
        "kl_text_anchor",
        "kl_joint",
    ]
    aggregated: Dict[int, Dict[str, List[float]]] = {
        layer: {metric: [] for metric in metric_names} for layer in layers
    }

    for sample in tqdm(samples, desc="Bridge localization scan (pred)"):
        llm_inpt, vt_range = vllm.get_llm_input_embeds([sample.prompt], [sample.image])
        seq_len = int(llm_inpt["inputs_embeds"].shape[1])
        track_idx = seq_len - 1
        vis_ids = list(range(int(vt_range[0]), int(vt_range[1])))
        target_token_id, target_token_text = get_target_token_info(tokenizer, sample.target_text)

        with torch.no_grad(), TraceDict(
            vllm.model,
            trace_names,
            retain_output=True,
            with_kwargs=True,
            clone=True,
            detach=True,
        ) as td:
            out_base = vllm.get_llm_outpt(llm_inpt, vt_range).logits

        p0 = safe_softmax_last(out_base)
        pred_token_id = int(torch.argmax(p0).item())
        pred_token_text = tokenizer.decode([pred_token_id])
        anchor_word, text_anchor_ids = find_text_anchor_indices(vllm, sample, vt_range, track_idx)

        sample_record = {
            "sample_id": sample.sample_id,
            "entity_name": sample.entity_name,
            "target_text": sample.target_text,
            "target_first_token": target_token_text,
            "pred_token": pred_token_text,
            "pred_token_id": pred_token_id,
            "prompt": sample.prompt,
            "image_path": sample.image_path,
            "track_position": track_idx,
            "anchor_word": anchor_word,
            "text_anchor_ids": text_anchor_ids,
            "vt_range": [int(vt_range[0]), int(vt_range[1])],
            "layers": [],
        }
        visual_npz: Dict[str, np.ndarray] = {}

        layer_rows_by_idx: Dict[int, Dict] = {}
        for layer, layer_name, attn_name, mlp_name in zip(layers, layer_names, attn_names, mlp_names):
            layer_hidden = extract_hidden_tensor(td[layer_name].output)
            attn_hidden = extract_hidden_tensor(td[attn_name].output)
            mlp_hidden = extract_hidden_tensor(td[mlp_name].output)

            visual_mean = layer_hidden[0, vis_ids].mean(dim=0)
            layer_track = layer_hidden[0, track_idx]
            attn_track = attn_hidden[0, track_idx]
            mlp_track = mlp_hidden[0, track_idx]

            layer_target_logit, layer_target_prob = rep_token_stats(norm, voc, layer_track, target_token_id)
            layer_pred_logit, layer_pred_prob = rep_token_stats(norm, voc, layer_track, pred_token_id)

            att_target_logit, att_target_prob = rep_token_stats(norm, voc, attn_track, target_token_id)
            mlp_target_logit, mlp_target_prob = rep_token_stats(norm, voc, mlp_track, target_token_id)

            att_pred_logit, att_pred_prob = rep_token_stats(norm, voc, attn_track, pred_token_id)
            mlp_pred_logit, mlp_pred_prob = rep_token_stats(norm, voc, mlp_track, pred_token_id)

            row = {
                "layer": layer,
                "visual_rep_norm": float(torch.norm(visual_mean).item()),
                "visual_track_cos": cosine_similarity_safe(visual_mean, layer_track),
                "layer_target_logit": layer_target_logit,
                "layer_target_prob": layer_target_prob,
                "layer_pred_logit": layer_pred_logit,
                "layer_pred_prob": layer_pred_prob,
                "att_target_logit": att_target_logit,
                "att_target_prob": att_target_prob,
                "att_target_pxv": float(att_target_logit * att_target_prob),
                "mlp_target_logit": mlp_target_logit,
                "mlp_target_prob": mlp_target_prob,
                "mlp_target_pxv": float(mlp_target_logit * mlp_target_prob),
                "att_pred_logit": att_pred_logit,
                "att_pred_prob": att_pred_prob,
                "att_pred_pxv": float(att_pred_logit * att_pred_prob),
                "mlp_pred_logit": mlp_pred_logit,
                "mlp_pred_prob": mlp_pred_prob,
                "mlp_pred_pxv": float(mlp_pred_logit * mlp_pred_prob),
            }
            layer_rows_by_idx[layer] = row
            sample_record["layers"].append(dict(row))
            visual_npz[f"layer_{layer:02d}"] = visual_mean.detach().float().cpu().numpy()

        for layer, layer_name in zip(layers, layer_names):
            p_vis = safe_softmax_last(
                perturb_one_layer(vllm, llm_inpt, vt_range, layer_name, vis_ids, args.noise_level)
            )
            p_txt = safe_softmax_last(
                perturb_one_layer(vllm, llm_inpt, vt_range, layer_name, text_anchor_ids, args.noise_level)
            )
            joint_ids = sorted(set(vis_ids + text_anchor_ids))
            p_joint = safe_softmax_last(
                perturb_one_layer(vllm, llm_inpt, vt_range, layer_name, joint_ids, args.noise_level)
            )

            layer_rows_by_idx[layer]["kl_visual"] = kl_p0_p1(p0, p_vis)
            layer_rows_by_idx[layer]["kl_text_anchor"] = kl_p0_p1(p0, p_txt)
            layer_rows_by_idx[layer]["kl_joint"] = kl_p0_p1(p0, p_joint)

        for layer_dict in sample_record["layers"]:
            layer = int(layer_dict["layer"])
            layer_dict.update(
                {
                    "kl_visual": layer_rows_by_idx[layer]["kl_visual"],
                    "kl_text_anchor": layer_rows_by_idx[layer]["kl_text_anchor"],
                    "kl_joint": layer_rows_by_idx[layer]["kl_joint"],
                }
            )
            for metric in metric_names:
                aggregated[layer][metric].append(float(layer_dict[metric]))

        with open(
            os.path.join(args.output_dir, "samples", f"{sample.sample_id}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(sample_record, f, ensure_ascii=False, indent=2)
        np.savez_compressed(
            os.path.join(args.output_dir, "visual_reps", f"{sample.sample_id}.npz"),
            **visual_npz,
        )

    rows = []
    for layer in layers:
        row = {"layer": layer}
        for metric in metric_names:
            values = aggregated[layer][metric]
            row[metric] = float(np.mean(values)) if values else 0.0
        rows.append(row)

    fieldnames = [
        "layer",
        "visual_rep_norm",
        "visual_track_cos",
        "layer_target_logit",
        "layer_target_prob",
        "layer_pred_logit",
        "layer_pred_prob",
        "att_target_logit",
        "att_target_prob",
        "att_target_pxv",
        "mlp_target_logit",
        "mlp_target_prob",
        "mlp_target_pxv",
        "att_pred_logit",
        "att_pred_prob",
        "att_pred_pxv",
        "mlp_pred_logit",
        "mlp_pred_prob",
        "mlp_pred_pxv",
        "kl_visual",
        "kl_text_anchor",
        "kl_joint",
    ]
    write_csv(os.path.join(args.output_dir, "layer_metrics.csv"), rows, fieldnames)

    counter_target = Counter()
    for group in [
        top_layers(rows, "kl_visual", args.topk_layers),
        top_layers(rows, "kl_text_anchor", args.topk_layers),
        top_layers(rows, "kl_joint", args.topk_layers),
        top_layers(rows, "att_target_pxv", args.topk_layers),
        top_layers(rows, "mlp_target_pxv", args.topk_layers),
    ]:
        for layer in group:
            counter_target[layer] += 1

    counter_pred = Counter()
    for group in [
        top_layers(rows, "kl_visual", args.topk_layers),
        top_layers(rows, "kl_text_anchor", args.topk_layers),
        top_layers(rows, "kl_joint", args.topk_layers),
        top_layers(rows, "att_pred_pxv", args.topk_layers),
        top_layers(rows, "mlp_pred_pxv", args.topk_layers),
    ]:
        for layer in group:
            counter_pred[layer] += 1

    summary = {
        "sample_count": len(samples),
        "top_visual_layers": top_layers(rows, "kl_visual", args.topk_layers),
        "top_text_layers": top_layers(rows, "kl_text_anchor", args.topk_layers),
        "top_joint_layers": top_layers(rows, "kl_joint", args.topk_layers),
        "top_attention_layers": top_layers(rows, "att_target_pxv", args.topk_layers),
        "top_mlp_layers": top_layers(rows, "mlp_target_pxv", args.topk_layers),
        "top_attention_pred_layers": top_layers(rows, "att_pred_pxv", args.topk_layers),
        "top_mlp_pred_layers": top_layers(rows, "mlp_pred_pxv", args.topk_layers),
        "consensus_layers": [layer for layer, _ in counter_target.most_common(args.topk_layers)],
        "consensus_pred_layers": [layer for layer, _ in counter_pred.most_common(args.topk_layers)],
        "output_dir": args.output_dir,
    }
    with open(os.path.join(args.output_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
