import argparse
import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
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
    parser.add_argument("--noise-level", type=float, default=0.30)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--layer-start", type=int, default=0)
    parser.add_argument("--layer-end", type=int, default=-1)
    parser.add_argument(
        "--output-dir",
        type=str,
        default="records/bridge_layer_output_kl",
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
                image_path=image_path,
            )
        )
    return samples


def extract_hidden_tensor(output) -> torch.Tensor:
    hidden = output[0] if isinstance(output, (list, tuple)) else output
    if hidden.dim() == 2:
        hidden = hidden.unsqueeze(0)
    return hidden


def kl_p0_p1(p0: torch.Tensor, p1: torch.Tensor) -> float:
    value = torch.sum(p0 * (torch.log(p0) - torch.log(p1))).item()
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


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


def find_text_anchor_indices(vllm, prompt: str, image, vt_range: Tuple[int, int], fallback_idx: int) -> List[int]:
    anchor_word = extract_anchor_word(prompt)
    if anchor_word is None:
        return [fallback_idx]

    try:
        proc = vllm.processor([prompt], [image], return_tensors="pt", padding=True)
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
            return sorted(set(matches))
    except Exception:
        pass

    return [fallback_idx]


def apply_noise_to_hidden(hs: torch.Tensor, token_ids: List[int], noise_level: float) -> torch.Tensor:
    if len(token_ids) == 0:
        return hs
    hidden = hs.clone()
    device = hidden.device
    index = torch.tensor(token_ids, device=device, dtype=torch.long)
    noise = torch.randn((len(token_ids), hidden.shape[-1]), device=device, dtype=hidden.dtype)
    hidden[0, index] = hidden[0, index] + noise * noise_level
    return hidden


def run_with_layer_perturb_and_capture_layer(vllm, llm_inpt, vt_range, layer_name, token_ids, noise_level):
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
        retain_output=True,
        with_kwargs=True,
        edit_output=edit_output,
        clone=True,
        detach=True,
    ) as td:
        _ = vllm.get_llm_outpt(llm_inpt, vt_range).logits
    return extract_hidden_tensor(td[layer_name].output)


def rep_to_vocab_dist(norm, voc, rep: torch.Tensor) -> torch.Tensor:
    logits = voc(norm(rep))
    probs = torch.softmax(logits, dim=-1)
    return torch.clamp(probs, min=1e-12)


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_kl(rows: List[Dict], out_png: str):
    layers = [r["layer"] for r in rows]
    kl_visual = [r["kl_visual_layer_out"] for r in rows]
    kl_text = [r["kl_text_layer_out"] for r in rows]
    kl_joint = [r["kl_joint_layer_out"] for r in rows]

    plt.figure(figsize=(10.5, 5.5), dpi=180)
    plt.plot(layers, kl_visual, marker="o", label="Visual perturbation")
    plt.plot(layers, kl_text, marker="s", label="Text perturbation")
    plt.plot(layers, kl_joint, marker="^", label="Visual+Text perturbation")
    plt.xlabel("Layer")
    plt.ylabel("KL Divergence (Layer Output Dist)")
    plt.title("Layer-wise KL on Same-Layer Output Distribution")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png)


def main():
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    cfg = read_config(args.config_path)
    num_layers = int(cfg["num_layers"])
    layer_tmp = cfg["layer_module_tmp"]
    norm = None
    voc = None

    layer_start = max(0, args.layer_start)
    layer_end = num_layers if args.layer_end < 0 else min(num_layers, args.layer_end)
    layers = list(range(layer_start, layer_end))
    layer_names = [layer_tmp.format(idx) for idx in layers]

    samples = load_bridge_samples(args.data_path, args.bridge_root, args.max_samples)
    if len(samples) == 0:
        raise RuntimeError("No bridge samples were loaded.")

    vllm = load_vllm_for_edit(args.model_name, args.device)
    norm = get_module(vllm.model, cfg["norm_path"])
    voc = get_module(vllm.model, cfg["voc_path"])

    aggregated = {
        layer: {
            "kl_visual_layer_out": [],
            "kl_text_layer_out": [],
            "kl_joint_layer_out": [],
        }
        for layer in layers
    }

    for sample in tqdm(samples, desc="Scan layer-output KL"):
        llm_inpt, vt_range = vllm.get_llm_input_embeds([sample.prompt], [sample.image])
        seq_len = int(llm_inpt["inputs_embeds"].shape[1])
        track_idx = seq_len - 1
        vis_ids = list(range(int(vt_range[0]), int(vt_range[1])))
        text_ids = find_text_anchor_indices(vllm, sample.prompt, sample.image, vt_range, track_idx)
        joint_ids = sorted(set(vis_ids + text_ids))

        with torch.no_grad(), TraceDict(
            vllm.model,
            layer_names,
            retain_output=True,
            with_kwargs=True,
            clone=True,
            detach=True,
        ) as td:
            _ = vllm.get_llm_outpt(llm_inpt, vt_range).logits

        for layer, layer_name in zip(layers, layer_names):
            base_hidden = extract_hidden_tensor(td[layer_name].output)
            base_rep = base_hidden[0, track_idx]
            p0 = rep_to_vocab_dist(norm, voc, base_rep)

            vis_hidden = run_with_layer_perturb_and_capture_layer(
                vllm, llm_inpt, vt_range, layer_name, vis_ids, args.noise_level
            )
            txt_hidden = run_with_layer_perturb_and_capture_layer(
                vllm, llm_inpt, vt_range, layer_name, text_ids, args.noise_level
            )
            jnt_hidden = run_with_layer_perturb_and_capture_layer(
                vllm, llm_inpt, vt_range, layer_name, joint_ids, args.noise_level
            )

            p_vis = rep_to_vocab_dist(norm, voc, vis_hidden[0, track_idx])
            p_txt = rep_to_vocab_dist(norm, voc, txt_hidden[0, track_idx])
            p_jnt = rep_to_vocab_dist(norm, voc, jnt_hidden[0, track_idx])

            aggregated[layer]["kl_visual_layer_out"].append(kl_p0_p1(p0, p_vis))
            aggregated[layer]["kl_text_layer_out"].append(kl_p0_p1(p0, p_txt))
            aggregated[layer]["kl_joint_layer_out"].append(kl_p0_p1(p0, p_jnt))

    rows = []
    for layer in layers:
        row = {"layer": layer}
        row["kl_visual_layer_out"] = float(np.mean(aggregated[layer]["kl_visual_layer_out"]))
        row["kl_text_layer_out"] = float(np.mean(aggregated[layer]["kl_text_layer_out"]))
        row["kl_joint_layer_out"] = float(np.mean(aggregated[layer]["kl_joint_layer_out"]))
        rows.append(row)

    csv_path = os.path.join(args.output_dir, "layer_output_kl.csv")
    png_path = os.path.join(args.output_dir, "layer_output_kl.png")
    summary_path = os.path.join(args.output_dir, "summary.json")

    write_csv(
        csv_path,
        rows,
        ["layer", "kl_visual_layer_out", "kl_text_layer_out", "kl_joint_layer_out"],
    )
    plot_kl(rows, png_path)

    summary = {
        "sample_count": len(samples),
        "noise_level": args.noise_level,
        "csv": csv_path,
        "plot": png_path,
        "note": "KL is computed on same-layer output distribution projected via norm+lm_head at tracked answer position.",
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
