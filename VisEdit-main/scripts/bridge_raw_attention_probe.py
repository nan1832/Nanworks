import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


ANSWER_STUB = " The answer is:"


@dataclass
class BridgeAttentionSample:
    sample_id: str
    prompt: str
    target_text: str
    entity_name: str
    image_path: str
    image: Any = None


def find_bridge_root() -> Path:
    search_roots = [
        REPO_ROOT.parent,
        REPO_ROOT.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
        Path.cwd().parent.parent,
    ]
    for base in search_roots:
        candidate = base / "Ten_Classes" / "bridge"
        if candidate.exists():
            return candidate
    return REPO_ROOT.parent / "Ten_Classes" / "bridge"


def resolve_bridge_image_path(rel_path: str, bridge_root: str) -> str:
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


def ensure_answer_stub(prompt: str) -> str:
    return prompt if prompt.endswith(ANSWER_STUB) else f"{prompt}{ANSWER_STUB}"


def load_bridge_sample(data_path: str, bridge_root: str, sample_id: str) -> BridgeAttentionSample:
    from PIL import Image

    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    for i, item in enumerate(raw):
        case_id = str(item.get("case_id", f"bridge_{i}"))
        if case_id != sample_id:
            continue
        req = item["request"]
        image_path = resolve_bridge_image_path(req["image"], bridge_root)
        return BridgeAttentionSample(
            sample_id=case_id,
            prompt=ensure_answer_stub(req["prompt"]),
            target_text=req["target_new"],
            entity_name=item.get("entity_name", req["target_new"]),
            image_path=image_path,
            image=Image.open(image_path).convert("RGB"),
        )
    raise KeyError(f"Sample id '{sample_id}' not found in {data_path}")


def map_text_tokens_to_merged_positions(
    input_ids: Sequence[int],
    image_token_id: int,
    img_token_n: int,
) -> List[Dict[str, int]]:
    image_pos = list(input_ids).index(image_token_id)
    shift = img_token_n - 1
    mapping: List[Dict[str, int]] = []
    for idx, token_id in enumerate(input_ids):
        if token_id == image_token_id:
            continue
        merged_idx = idx if idx < image_pos else idx + shift
        mapping.append(
            {
                "original_idx": int(idx),
                "merged_idx": int(merged_idx),
                "token_id": int(token_id),
            }
        )
    return mapping


def reshape_visual_attention_to_grid(
    weights: Sequence[float],
    vt_range: Optional[Tuple[int, int]] = None,
):
    span = len(weights) if vt_range is None else int(vt_range[1]) - int(vt_range[0])
    side = int(round(math.sqrt(span)))
    if side * side != span:
        raise ValueError(f"Visual token count {span} does not form a square grid")
    values = [float(v) for v in weights]
    grid = [values[row * side : (row + 1) * side] for row in range(side)]
    try:
        import numpy as np

        return np.asarray(grid, dtype=float)
    except ImportError:
        return grid


def parse_layer_list(raw: str) -> List[int]:
    layers = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        layers.append(int(piece))
    if not layers:
        raise ValueError("Expected at least one layer index")
    return layers


def clean_token_label(token_text: str) -> str:
    text = token_text.replace("▁", " ")
    text = text.replace("<s>", "<bos>")
    text = text.replace("</s>", "<eos>")
    text = text.replace("\n", "\\n")
    return text


def prepare_processor_text(vllm, prompt: str, has_image: bool) -> str:
    if not has_image:
        return prompt
    image_token = vllm.get_img_special_token_str()
    if not image_token:
        return prompt
    if prompt.find(image_token) != -1:
        return prompt
    if getattr(vllm, "auto_add_img_special_token", False):
        return f"{image_token}\n{prompt}"
    return prompt


def normalize_for_display(array):
    import numpy as np

    arr = np.asarray(array, dtype=float)
    if arr.size == 0:
        return arr
    min_value = float(arr.min())
    max_value = float(arr.max())
    if math.isclose(min_value, max_value):
        return np.zeros_like(arr)
    return (arr - min_value) / (max_value - min_value)


def ensure_eager_attention(model) -> None:
    for obj in [model, getattr(model, "config", None), getattr(model, "language_model", None)]:
        if obj is None:
            continue
        config = getattr(obj, "config", None)
        if config is not None and hasattr(config, "_attn_implementation"):
            config._attn_implementation = "eager"


def top_text_tokens(
    token_labels: Sequence[str],
    token_positions: Sequence[int],
    token_weights: Sequence[float],
    track_idx: int,
    topk: int,
    include_self: bool,
) -> List[Dict[str, float]]:
    ranked = []
    for label, pos, weight in zip(token_labels, token_positions, token_weights):
        if not include_self and pos == track_idx:
            continue
        ranked.append({"token": label, "merged_idx": int(pos), "weight": float(weight)})
    ranked.sort(key=lambda item: item["weight"], reverse=True)
    return ranked[:topk]


def extract_raw_attention(
    sample: BridgeAttentionSample,
    model_name: str,
    device: str,
    selected_layers: Sequence[int],
) -> Dict[str, Any]:
    import numpy as np
    import torch

    from utils import load_vllm_for_edit

    vllm = load_vllm_for_edit(model_name, device)
    tokenizer = vllm.get_llm_tokenizer()
    llm_inpt, vt_range = vllm.get_llm_input_embeds([sample.prompt], [sample.image])
    track_idx = int(llm_inpt["inputs_embeds"].shape[1] - 1)

    processor_text = prepare_processor_text(vllm, sample.prompt, has_image=True)
    proc = vllm.processor([processor_text], [sample.image], return_tensors="pt", padding=True)
    input_ids = proc["input_ids"][0].tolist()
    mapping = map_text_tokens_to_merged_positions(
        input_ids=input_ids,
        image_token_id=vllm.get_img_special_token_id(),
        img_token_n=vllm.get_img_token_n(),
    )
    token_labels = [clean_token_label(tokenizer.convert_ids_to_tokens(item["token_id"])) for item in mapping]
    token_positions = [item["merged_idx"] for item in mapping]

    ensure_eager_attention(vllm.model)
    ensure_eager_attention(vllm.model.language_model)

    with torch.no_grad():
        outputs = vllm.model.language_model(
            **llm_inpt,
            use_cache=False,
            output_attentions=True,
            return_dict=True,
        )

    if getattr(outputs, "attentions", None) is None:
        raise RuntimeError("Model did not return attention weights. Try eager attention implementation.")

    layers = list(range(len(outputs.attentions)))
    pred_token_id = int(outputs.logits[0, -1].argmax().item())
    pred_token = tokenizer.decode([pred_token_id])

    text_heatmap = []
    visual_mass = []
    text_mass = []
    self_mass = []
    layer_records: List[Dict[str, Any]] = []
    selected_maps: Dict[int, Any] = {}

    vt_begin, vt_end = int(vt_range[0]), int(vt_range[1])
    for layer in layers:
        attn = outputs.attentions[layer]
        if attn is None:
            raise RuntimeError(f"Attention for layer {layer} is None")
        query_weights = attn[0, :, track_idx, :].detach().float().cpu()
        avg_weights = query_weights.mean(dim=0).numpy()

        text_weights = [float(avg_weights[pos]) for pos in token_positions]
        visual_weights = avg_weights[vt_begin:vt_end]
        text_heatmap.append(text_weights)
        visual_mass.append(float(np.sum(visual_weights)))
        text_mass.append(float(sum(text_weights)))
        self_mass.append(float(avg_weights[track_idx]))

        visual_grid = np.asarray(reshape_visual_attention_to_grid(visual_weights.tolist(), vt_range), dtype=float)
        record = {
            "layer": int(layer),
            "visual_mass": float(np.sum(visual_weights)),
            "text_mass": float(sum(text_weights)),
            "self_mass": float(avg_weights[track_idx]),
            "top_text_tokens": top_text_tokens(
                token_labels,
                token_positions,
                text_weights,
                track_idx=track_idx,
                topk=8,
                include_self=False,
            ),
        }
        layer_records.append(record)

        if layer in selected_layers:
            selected_maps[int(layer)] = {
                "avg_visual_grid": visual_grid,
                "avg_text_weights": np.asarray(text_weights, dtype=float),
                "head_count": int(query_weights.shape[0]),
            }

    return {
        "sample_id": sample.sample_id,
        "entity_name": sample.entity_name,
        "target_text": sample.target_text,
        "pred_token": pred_token,
        "prompt": sample.prompt,
        "image_path": sample.image_path,
        "vt_range": [vt_begin, vt_end],
        "track_position": track_idx,
        "token_labels": token_labels,
        "token_positions": token_positions,
        "selected_layers": [int(layer) for layer in selected_layers],
        "text_heatmap": np.asarray(text_heatmap, dtype=float),
        "visual_mass": np.asarray(visual_mass, dtype=float),
        "text_mass": np.asarray(text_mass, dtype=float),
        "self_mass": np.asarray(self_mass, dtype=float),
        "selected_maps": selected_maps,
        "layer_records": layer_records,
    }


def save_attention_artifacts(result: Dict[str, Any], output_dir: str) -> Tuple[str, str]:
    import numpy as np

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "raw_attention_summary.json")
    npz_path = os.path.join(output_dir, "raw_attention_arrays.npz")

    json_payload = {
        "sample_id": result["sample_id"],
        "entity_name": result["entity_name"],
        "target_text": result["target_text"],
        "pred_token": result["pred_token"],
        "prompt": result["prompt"],
        "image_path": result["image_path"],
        "vt_range": result["vt_range"],
        "track_position": result["track_position"],
        "token_labels": result["token_labels"],
        "token_positions": result["token_positions"],
        "selected_layers": result["selected_layers"],
        "layer_records": result["layer_records"],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, indent=2)

    arrays = {
        "text_heatmap": result["text_heatmap"],
        "visual_mass": result["visual_mass"],
        "text_mass": result["text_mass"],
        "self_mass": result["self_mass"],
    }
    for layer, payload in result["selected_maps"].items():
        arrays[f"visual_grid_layer_{layer:02d}"] = payload["avg_visual_grid"]
        arrays[f"text_weights_layer_{layer:02d}"] = payload["avg_text_weights"]
    np.savez_compressed(npz_path, **arrays)
    return json_path, npz_path


def plot_attention_figure(result: Dict[str, Any], output_dir: str) -> Tuple[str, str]:
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt
    import numpy as np

    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, "bridge_raw_attention_overview.png")
    pdf_path = os.path.join(output_dir, "bridge_raw_attention_overview.pdf")

    layers = np.arange(result["text_heatmap"].shape[0])
    selected_layers = result["selected_layers"]

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
        }
    )

    n_visual = len(selected_layers)
    fig = plt.figure(figsize=(14.5, 8.5))
    gs = gridspec.GridSpec(
        3,
        n_visual + 1,
        width_ratios=[1.15] + [1.0] * n_visual,
        height_ratios=[1.25, 0.85, 1.0],
        wspace=0.28,
        hspace=0.35,
    )

    ax_img = fig.add_subplot(gs[:, 0])
    ax_text = fig.add_subplot(gs[0, 1:])
    ax_mass = fig.add_subplot(gs[1, 1:])
    visual_axes = [fig.add_subplot(gs[2, idx + 1]) for idx in range(n_visual)]

    ax_img.axis("off")
    image = plt.imread(result["image_path"])
    ax_img.imshow(image)
    ax_img.set_title("Bridge Sample", pad=8)
    metadata = "\n".join(
        [
            f"Entity: {result['entity_name']}",
            f"Prompt: {result['prompt'].replace(ANSWER_STUB, '')}",
            f"Predicted token: {result['pred_token']}",
            f"Answer position: {result['track_position']}",
            f"Visual token span: {result['vt_range'][0]}-{result['vt_range'][1] - 1}",
        ]
    )
    ax_img.text(
        0.0,
        -0.06,
        metadata,
        transform=ax_img.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7f7f5", edgecolor="#d0d0d0"),
    )

    heatmap = result["text_heatmap"]
    im = ax_text.imshow(heatmap, aspect="auto", cmap="YlOrRd")
    ax_text.set_title("Raw Answer-Position Attention to Text Tokens")
    ax_text.set_ylabel("Layer")
    ax_text.set_xlabel("Text Token")
    ax_text.set_yticks(range(0, len(layers), 2))
    ax_text.set_xticks(range(len(result["token_labels"])))
    ax_text.set_xticklabels(result["token_labels"], rotation=60, ha="right", fontsize=8)
    for layer in selected_layers:
        ax_text.axhline(layer, color="#264653", linestyle="--", linewidth=0.8, alpha=0.55)
    cbar = fig.colorbar(im, ax=ax_text, fraction=0.025, pad=0.02)
    cbar.set_label("Attention Weight")

    ax_mass.plot(layers, result["visual_mass"], color="#2A9D8F", marker="o", label="Visual mass")
    ax_mass.plot(layers, result["text_mass"], color="#E76F51", marker="s", label="Text mass")
    ax_mass.plot(layers, result["self_mass"], color="#264653", marker="^", label="Self mass")
    for layer in selected_layers:
        ax_mass.axvline(layer, color="#7B8794", linestyle=":", linewidth=0.9, alpha=0.5)
    ax_mass.set_title("Where the Answer Position Looks Across Layers")
    ax_mass.set_xlabel("Layer")
    ax_mass.set_ylabel("Summed Attention Weight")
    ax_mass.set_xlim(-0.5, len(layers) - 0.5)
    ax_mass.legend(loc="upper right", ncol=3)

    for ax, layer in zip(visual_axes, selected_layers):
        visual_grid = result["selected_maps"][layer]["avg_visual_grid"]
        display_grid = normalize_for_display(visual_grid)
        ax.imshow(image)
        ax.imshow(display_grid, cmap="magma", alpha=0.55, interpolation="bilinear")
        top_patch = np.unravel_index(np.asarray(visual_grid).argmax(), np.asarray(visual_grid).shape)
        ax.set_title(f"Layer {layer} visual patches\npeak={top_patch[0]},{top_patch[1]}")
        ax.set_xticks([])
        ax.set_yticks([])

    fig.suptitle(
        "Raw Attention from the Answer Position in Unedited LLaVA-v1.5-7B",
        y=0.98,
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.015,
        "Top: raw head-averaged attention from the answer position to text tokens across all 32 layers. "
        "Bottom: selected-layer attention to visual patches, normalized per layer for display.",
        ha="center",
        fontsize=9,
    )

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    return png_path, pdf_path


def parse_args():
    bridge_root = find_bridge_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", type=str, default="llava-v1.5-7b")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(bridge_root / "bridge_train" / "edit_30_bridge_train_only_vis.json"),
    )
    parser.add_argument("--bridge-root", type=str, default=str(bridge_root))
    parser.add_argument("--sample-id", type=str, default="train_0")
    parser.add_argument("--layers", type=str, default="1,30,31")
    parser.add_argument("--output-dir", type=str, default="records/bridge_raw_attention")
    return parser.parse_args()


def main():
    args = parse_args()
    sample = load_bridge_sample(args.data_path, args.bridge_root, args.sample_id)
    selected_layers = parse_layer_list(args.layers)
    result = extract_raw_attention(sample, args.model_name, args.device, selected_layers)
    json_path, npz_path = save_attention_artifacts(result, args.output_dir)
    png_path, pdf_path = plot_attention_figure(result, args.output_dir)

    summary = {
        "sample_id": result["sample_id"],
        "entity_name": result["entity_name"],
        "pred_token": result["pred_token"],
        "selected_layers": selected_layers,
        "json_path": json_path,
        "npz_path": npz_path,
        "png_path": png_path,
        "pdf_path": pdf_path,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
