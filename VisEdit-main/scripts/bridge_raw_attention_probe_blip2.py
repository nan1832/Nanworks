import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


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


def map_blip2_text_tokens_to_merged_positions(
    input_ids: Sequence[int],
    query_token_n: int,
) -> List[Dict[str, int]]:
    mapping: List[Dict[str, int]] = []
    for idx, token_id in enumerate(input_ids):
        mapping.append(
            {
                "original_idx": int(idx),
                "merged_idx": int(idx + query_token_n),
                "token_id": int(token_id),
            }
        )
    return mapping


def reshape_query_attention_to_grid(weights: Sequence[float], cols: int = 8):
    if cols <= 0:
        raise ValueError("cols must be positive")
    if len(weights) % cols != 0:
        raise ValueError(f"Query token count {len(weights)} is not divisible by cols={cols}")
    rows = len(weights) // cols
    values = [float(v) for v in weights]
    grid = [values[row * cols : (row + 1) * cols] for row in range(rows)]
    try:
        import numpy as np

        return np.asarray(grid, dtype=float)
    except ImportError:
        return grid


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


def top_weighted_labels(labels: Sequence[str], weights: Sequence[float], topk: int) -> List[Dict[str, float]]:
    ranked = []
    for idx, (label, weight) in enumerate(zip(labels, weights)):
        ranked.append({"label": label, "index": int(idx), "weight": float(weight)})
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
    query_token_n = int(vt_range[1] - vt_range[0])
    track_idx = int(llm_inpt["inputs_embeds"].shape[1] - 1)

    proc = vllm.processor([sample.image], [sample.prompt], return_tensors="pt", padding=True)
    input_ids = proc["input_ids"][0].tolist()
    text_mapping = map_blip2_text_tokens_to_merged_positions(input_ids=input_ids, query_token_n=query_token_n)
    token_labels = [clean_token_label(tokenizer.convert_ids_to_tokens(item["token_id"])) for item in text_mapping]
    token_positions = [item["merged_idx"] for item in text_mapping]
    query_labels = [f"q{idx:02d}" for idx in range(query_token_n)]

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
    query_heatmap = []
    query_mass = []
    text_mass = []
    self_mass = []
    layer_records: List[Dict[str, Any]] = []
    selected_maps: Dict[int, Any] = {}

    q_begin, q_end = int(vt_range[0]), int(vt_range[1])
    for layer in layers:
        attn = outputs.attentions[layer]
        if attn is None:
            raise RuntimeError(f"Attention for layer {layer} is None")
        query_weights_by_head = attn[0, :, track_idx, :].detach().float().cpu()
        avg_weights = query_weights_by_head.mean(dim=0).numpy()

        layer_query_weights = avg_weights[q_begin:q_end]
        layer_text_weights = [float(avg_weights[pos]) for pos in token_positions]

        query_heatmap.append(layer_query_weights.tolist())
        text_heatmap.append(layer_text_weights)
        query_mass.append(float(np.sum(layer_query_weights)))
        text_mass.append(float(sum(layer_text_weights)))
        self_mass.append(float(avg_weights[track_idx]))

        record = {
            "layer": int(layer),
            "query_mass": float(np.sum(layer_query_weights)),
            "text_mass": float(sum(layer_text_weights)),
            "self_mass": float(avg_weights[track_idx]),
            "top_query_tokens": top_weighted_labels(query_labels, layer_query_weights.tolist(), topk=8),
            "top_text_tokens": top_weighted_labels(token_labels, layer_text_weights, topk=8),
        }
        layer_records.append(record)

        if layer in selected_layers:
            selected_maps[int(layer)] = {
                "query_grid": np.asarray(reshape_query_attention_to_grid(layer_query_weights.tolist(), cols=8), dtype=float),
                "query_weights": np.asarray(layer_query_weights, dtype=float),
                "text_weights": np.asarray(layer_text_weights, dtype=float),
                "head_count": int(query_weights_by_head.shape[0]),
            }

    return {
        "sample_id": sample.sample_id,
        "entity_name": sample.entity_name,
        "target_text": sample.target_text,
        "pred_token": pred_token,
        "prompt": sample.prompt,
        "image_path": sample.image_path,
        "vt_range": [q_begin, q_end],
        "track_position": track_idx,
        "query_labels": query_labels,
        "token_labels": token_labels,
        "token_positions": token_positions,
        "selected_layers": [int(layer) for layer in selected_layers],
        "query_heatmap": np.asarray(query_heatmap, dtype=float),
        "text_heatmap": np.asarray(text_heatmap, dtype=float),
        "query_mass": np.asarray(query_mass, dtype=float),
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

    payload = {
        "sample_id": result["sample_id"],
        "entity_name": result["entity_name"],
        "target_text": result["target_text"],
        "pred_token": result["pred_token"],
        "prompt": result["prompt"],
        "image_path": result["image_path"],
        "vt_range": result["vt_range"],
        "track_position": result["track_position"],
        "query_labels": result["query_labels"],
        "token_labels": result["token_labels"],
        "token_positions": result["token_positions"],
        "selected_layers": result["selected_layers"],
        "layer_records": result["layer_records"],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    arrays = {
        "query_heatmap": result["query_heatmap"],
        "text_heatmap": result["text_heatmap"],
        "query_mass": result["query_mass"],
        "text_mass": result["text_mass"],
        "self_mass": result["self_mass"],
    }
    for layer, data in result["selected_maps"].items():
        arrays[f"query_grid_layer_{layer:02d}"] = data["query_grid"]
        arrays[f"query_weights_layer_{layer:02d}"] = data["query_weights"]
        arrays[f"text_weights_layer_{layer:02d}"] = data["text_weights"]
    np.savez_compressed(npz_path, **arrays)
    return json_path, npz_path


def plot_attention_figure(result: Dict[str, Any], output_dir: str) -> Tuple[str, str]:
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt
    import numpy as np

    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, "bridge_raw_attention_blip2_overview.png")
    pdf_path = os.path.join(output_dir, "bridge_raw_attention_blip2_overview.pdf")

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

    fig = plt.figure(figsize=(14.8, 9.0))
    gs = gridspec.GridSpec(
        3,
        2,
        width_ratios=[1.1, 3.6],
        height_ratios=[1.1, 1.0, 0.9],
        wspace=0.25,
        hspace=0.32,
    )

    ax_img = fig.add_subplot(gs[:, 0])
    ax_text = fig.add_subplot(gs[0, 1])
    ax_query = fig.add_subplot(gs[1, 1])
    ax_mass = fig.add_subplot(gs[2, 1])

    ax_img.axis("off")
    image = plt.imread(result["image_path"])
    ax_img.imshow(image)
    ax_img.set_title("Bridge Sample", pad=8)
    metadata = "\n".join(
        [
            f"Entity: {result['entity_name']}",
            f"Prompt: {result['prompt'].replace(ANSWER_STUB, '')}",
            f"Predicted token: {result['pred_token']!r}",
            f"Answer position: {result['track_position']}",
            f"Query token span: {result['vt_range'][0]}-{result['vt_range'][1] - 1}",
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

    im_text = ax_text.imshow(result["text_heatmap"], aspect="auto", cmap="YlOrRd")
    ax_text.set_title("Raw Answer-Position Attention to Text Tokens")
    ax_text.set_ylabel("Layer")
    ax_text.set_xlabel("Text Token")
    ax_text.set_yticks(range(0, len(layers), 2))
    ax_text.set_xticks(range(len(result["token_labels"])))
    ax_text.set_xticklabels(result["token_labels"], rotation=60, ha="right", fontsize=8)
    for layer in selected_layers:
        ax_text.axhline(layer, color="#264653", linestyle="--", linewidth=0.85, alpha=0.5)
    cbar_text = fig.colorbar(im_text, ax=ax_text, fraction=0.025, pad=0.02)
    cbar_text.set_label("Attention Weight")

    im_query = ax_query.imshow(result["query_heatmap"], aspect="auto", cmap="magma")
    ax_query.set_title("Raw Answer-Position Attention to 32 Query Tokens")
    ax_query.set_ylabel("Layer")
    ax_query.set_xlabel("Query Token")
    ax_query.set_yticks(range(0, len(layers), 2))
    ax_query.set_xticks(range(0, len(result["query_labels"]), 2))
    ax_query.set_xticklabels(result["query_labels"][::2], rotation=0, fontsize=8)
    for layer in selected_layers:
        ax_query.axhline(layer, color="#56B4E9", linestyle="--", linewidth=0.85, alpha=0.55)
    cbar_query = fig.colorbar(im_query, ax=ax_query, fraction=0.025, pad=0.02)
    cbar_query.set_label("Attention Weight")

    ax_mass.plot(layers, result["query_mass"], color="#2A9D8F", marker="o", label="Query-token mass")
    ax_mass.plot(layers, result["text_mass"], color="#E76F51", marker="s", label="Text-token mass")
    ax_mass.plot(layers, result["self_mass"], color="#264653", marker="^", label="Self mass")
    for layer in selected_layers:
        ax_mass.axvline(layer, color="#7B8794", linestyle=":", linewidth=0.9, alpha=0.5)
    ax_mass.set_title("Where the Answer Position Looks Across Layers")
    ax_mass.set_xlabel("Layer")
    ax_mass.set_ylabel("Summed Attention Weight")
    ax_mass.set_xlim(-0.5, len(layers) - 0.5)
    ax_mass.legend(loc="upper right", ncol=3)

    fig.suptitle(
        "Raw Attention from the Answer Position in Unedited BLIP2-OPT-2.7B",
        y=0.98,
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.015,
        "BLIP2's language model directly attends to 32 query tokens rather than original image patches, so the query-token heatmap "
        "is the LM-level raw view of which visual representations support the answer position.",
        ha="center",
        fontsize=9,
    )

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    return png_path, pdf_path


def parse_args():
    bridge_root = find_bridge_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", type=str, default="blip2-opt-2.7b")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(bridge_root / "bridge_train" / "edit_30_bridge_train_only_vis.json"),
    )
    parser.add_argument("--bridge-root", type=str, default=str(bridge_root))
    parser.add_argument("--sample-id", type=str, default="train_0")
    parser.add_argument("--layers", type=str, default="4,15,29")
    parser.add_argument("--output-dir", type=str, default="records/bridge_raw_attention_blip2")
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
