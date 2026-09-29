import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dataset.vllm import BaseVLLMEditData, EVQA
from p_track.p_track import PTrack, PTrackConfig
from utils import get_full_model_name, load_vllm_for_edit


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


def make_predict_word(text: str, leading_space: bool = True) -> str:
    text = (text or "").strip()
    return (" " + text) if leading_space else text


def build_mmke_data(data_path: str, img_root_dir: str, data_n=None):
    if data_n is None:
        data_n = 99999999
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    data_n = min(len(raw_data), data_n)
    data = []
    for i in tqdm(range(data_n), "Loading MMKE data"):
        row = raw_data[i]
        image_path = Path(row["image"])
        if not image_path.is_absolute():
            image_path = Path(img_root_dir) / image_path
        with Image.open(image_path) as image:
            pil_image = image.convert("RGB").copy()
        data.append(
            {
                "request": {
                    "image": pil_image,
                    "prompt": f"{row['src']} The answer is:",
                    "target_new": row.get("alt", ""),
                }
            }
        )
    return data


def load_contribution_data(dataset_type: str, data_path: str, img_root_dir: str, data_n=None):
    if dataset_type == "evqa":
        return EVQA(data_path, img_root_dir, data_n).data
    if dataset_type == "mmke":
        return build_mmke_data(data_path, img_root_dir, data_n)
    raise ValueError(f"Unsupported dataset_type: {dataset_type}")


def rank_desc(values):
    order = np.argsort(-values)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(values) + 1)
    return ranks, order


def signed_contribution(vs, ps, eps=1e-12):
    infl_att, infl_mlp = [], []
    for i in range(vs["att"].shape[0]):
        finite_abs = np.concatenate(
            [
                np.abs(vs["att"][i][np.isfinite(vs["att"][i])]),
                np.abs(vs["mlp"][i][np.isfinite(vs["mlp"][i])]),
            ]
        )
        denom = max(float(np.max(finite_abs)) if finite_abs.size else 0.0, eps)
        att_v = np.nan_to_num(vs["att"][i] / denom, nan=0.0, posinf=0.0, neginf=0.0)
        mlp_v = np.nan_to_num(vs["mlp"][i] / denom, nan=0.0, posinf=0.0, neginf=0.0)
        att_p = np.nan_to_num(ps["att"][i], nan=0.0, posinf=0.0, neginf=0.0)
        mlp_p = np.nan_to_num(ps["mlp"][i], nan=0.0, posinf=0.0, neginf=0.0)
        att = np.sign(att_v) * np.sqrt(np.abs(att_v) + eps) * np.sqrt(np.maximum(att_p, 0.0))
        mlp = np.sign(mlp_v) * np.sqrt(np.abs(mlp_v) + eps) * np.sqrt(np.maximum(mlp_p, 0.0))
        infl_att.append(att)
        infl_mlp.append(mlp)
    return np.stack(infl_att, axis=0), np.stack(infl_mlp, axis=0)


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_bars(out_dir, layers, attn, mlp, suffix="", positive=False):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 14,
            "axes.labelsize": 18,
            "axes.titlesize": 22,
            "legend.fontsize": 17,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
        }
    )
    if positive:
        attn = np.maximum(attn, 0.0)
        mlp = np.maximum(mlp, 0.0)
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    width = 0.35
    x = np.asarray(layers)
    ax.bar(x - width / 2, attn, width=width, color="green", label="Attn")
    ax.bar(x + width / 2, mlp, width=width, color="red", label="MLP")
    ax.set_xlim(-1, max(layers) + 1.5)
    ymin = min(0.0, float(np.min(attn)), float(np.min(mlp)))
    ymax = max(float(np.max(attn)), float(np.max(mlp)), 1e-4)
    pad = max((ymax - ymin) * 0.12, 1e-4)
    ax.set_ylim(ymin - pad * 0.2, ymax + pad)
    ax.set_xlabel("Layer")
    ax.set_ylabel("Module Output Contribution")
    title_suffix = " (positive)" if positive else ""
    ax.set_title(f"Module Contribution of BLIP2-OPT (2.7B){title_suffix}", pad=14)
    ax.set_xticks(np.arange(0, max(layers) + 1, 5))
    ax.legend(loc="lower left", frameon=False)
    ax.annotate(
        "",
        xy=(1.02, 0),
        xytext=(0, 0),
        xycoords=("axes fraction", "axes fraction"),
        textcoords=("axes fraction", "axes fraction"),
        arrowprops=dict(arrowstyle="->", color="black", linewidth=1.6),
    )
    ax.annotate(
        "",
        xy=(0, 1.03),
        xytext=(0, 0),
        xycoords=("axes fraction", "axes fraction"),
        textcoords=("axes fraction", "axes fraction"),
        arrowprops=dict(arrowstyle="->", color="black", linewidth=1.6),
    )
    # Match the visual cue in the reference figure: deep layers are highlighted as a region.
    if max(layers) >= 31:
        y0 = ax.get_ylim()[0]
        ax.annotate(
            "high-contribution layers",
            xy=(25, y0),
            xytext=(25, y0 - (ax.get_ylim()[1] - y0) * 0.08),
            ha="center",
            va="top",
            fontsize=14,
            arrowprops=dict(arrowstyle="-[,widthB=5.0,lengthB=0.35", lw=1.2, color="black"),
            annotation_clip=False,
        )
    fig.tight_layout()
    base = out_dir / f"module_contribution_bar{suffix}"
    fig.savefig(base.with_suffix(".png"))
    fig.savefig(base.with_suffix(".pdf"))
    fig.savefig(base.with_suffix(".svg"))
    plt.close(fig)
    return base.with_suffix(".png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="blip2-opt-2.7b")
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--img-root-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-n", type=int, default=None)
    parser.add_argument("--dataset-type", choices=["evqa", "mmke"], default="evqa")
    parser.add_argument("--key-mode", choices=["alt", "pred", "model_pred"], default="alt")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config-path", default="configs/p_track/blip2-opt-2.7b.yaml")
    parser.add_argument("--leading-space", action="store_true", default=True)
    parser.add_argument("--no-leading-space", dest="leading_space", action="store_false")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_name = get_full_model_name(args.model_name)

    with open(args.data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    sample_count = min(len(raw_data), args.data_n or len(raw_data))

    config_payload = {
        "model_name": model_name,
        "data_path": args.data_path,
        "img_root_dir": args.img_root_dir,
        "sample_count": sample_count,
        "dataset_type": args.dataset_type,
        "key_mode": args.key_mode,
        "device": args.device,
        "config_path": args.config_path,
        "score_formula": "sign(v/M)*sqrt(abs(v/M))*sqrt(p)",
        "rank_formula": "max(0, attn_mean)+max(0, mlp_mean)",
        "token_rule": "first token of target answer; leading space enabled unless --no-leading-space",
    }
    (out_dir / "config.json").write_text(json.dumps(config_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    data = load_contribution_data(args.dataset_type, args.data_path, args.img_root_dir, args.data_n)
    requests = [d["request"] for d in data]
    cfg = PTrackConfig.from_yaml(args.config_path)
    vllm = load_vllm_for_edit(model_name, args.device)
    pt = PTrack(vllm, cfg)

    keys = ["layer", "att", "mlp"]
    ps = {key: [] for key in keys}
    vs = {key: [] for key in keys}
    sample_rows = []

    for sample_idx, request in enumerate(tqdm(requests, desc="module contribution")):
        pt.forward_and_trace(request["prompt"], request["image"])
        if args.key_mode == "model_pred":
            predict_word = None
        elif args.key_mode == "pred":
            predict_word = make_predict_word(raw_data[sample_idx].get("pred", ""), args.leading_space)
        else:
            predict_word = make_predict_word(request["target_new"], args.leading_space)
        _, _, total_p, total_v = pt.p_tracking(save_results=False, predict_word=predict_word)
        for key in keys:
            ps[key].append(total_p[key])
            vs[key].append(total_v[key])
        for layer in range(cfg.num_layers):
            sample_rows.append(
                {
                    "sample_idx": sample_idx,
                    "layer": layer,
                    "att_p": total_p["att"][layer],
                    "att_v": total_v["att"][layer],
                    "mlp_p": total_p["mlp"][layer],
                    "mlp_v": total_v["mlp"][layer],
                    "layer_p": total_p["layer"][layer],
                    "layer_v": total_v["layer"][layer],
                }
            )
        if hasattr(pt, "td"):
            del pt.td
        if torch.cuda.is_available() and (sample_idx + 1) % 25 == 0:
            torch.cuda.empty_cache()

    ps = {key: np.asarray(value, dtype=np.float64) for key, value in ps.items()}
    vs = {key: np.asarray(value, dtype=np.float64) for key, value in vs.items()}
    att_infl, mlp_infl = signed_contribution(vs, ps)

    mean_att = att_infl.mean(axis=0)
    mean_mlp = mlp_infl.mean(axis=0)
    score_positive = np.maximum(mean_att, 0.0) + np.maximum(mean_mlp, 0.0)
    score_signed = mean_att + mean_mlp
    score_abs = np.abs(mean_att) + np.abs(mean_mlp)
    rank_positive, order_positive = rank_desc(score_positive)
    rank_signed, order_signed = rank_desc(score_signed)
    rank_abs, order_abs = rank_desc(score_abs)
    layers = list(range(cfg.num_layers))

    np.savez_compressed(
        out_dir / "contribution_raw.npz",
        ps_layer=ps["layer"],
        ps_att=ps["att"],
        ps_mlp=ps["mlp"],
        vs_layer=vs["layer"],
        vs_att=vs["att"],
        vs_mlp=vs["mlp"],
        att_infl=att_infl,
        mlp_infl=mlp_infl,
    )

    layer_rows = []
    for layer in layers:
        layer_rows.append(
            {
                "layer": layer,
                "attn_mean": mean_att[layer],
                "mlp_mean": mean_mlp[layer],
                "score_positive": score_positive[layer],
                "score_signed": score_signed[layer],
                "score_abs": score_abs[layer],
                "rank_positive": int(rank_positive[layer]),
                "rank_signed": int(rank_signed[layer]),
                "rank_abs": int(rank_abs[layer]),
            }
        )
    write_csv(
        out_dir / "contribution_layer.csv",
        [
            "layer",
            "attn_mean",
            "mlp_mean",
            "score_positive",
            "score_signed",
            "score_abs",
            "rank_positive",
            "rank_signed",
            "rank_abs",
        ],
        layer_rows,
    )
    write_csv(
        out_dir / "contribution_sample_layer.csv",
        ["sample_idx", "layer", "att_p", "att_v", "mlp_p", "mlp_v", "layer_p", "layer_v"],
        sample_rows,
    )
    rank_rows = []
    for pos, layer in enumerate(order_positive[: cfg.num_layers], start=1):
        rank_rows.append({"rank_type": "positive", "rank": pos, "layer": int(layer), "score": score_positive[layer]})
    for pos, layer in enumerate(order_signed[: cfg.num_layers], start=1):
        rank_rows.append({"rank_type": "signed", "rank": pos, "layer": int(layer), "score": score_signed[layer]})
    for pos, layer in enumerate(order_abs[: cfg.num_layers], start=1):
        rank_rows.append({"rank_type": "abs", "rank": pos, "layer": int(layer), "score": score_abs[layer]})
    write_csv(out_dir / "contribution_rank.csv", ["rank_type", "rank", "layer", "score"], rank_rows)

    plot_bars(out_dir, layers, mean_att, mean_mlp)
    plot_bars(out_dir, layers, mean_att, mean_mlp, suffix="_positive", positive=True)

    summary = {
        "sample_count": sample_count,
        "key_mode": args.key_mode,
        "top10_positive": [int(x) for x in order_positive[:10]],
        "top10_signed": [int(x) for x in order_signed[:10]],
        "top10_abs": [int(x) for x in order_abs[:10]],
        "outputs": {
            "layer_csv": str(out_dir / "contribution_layer.csv"),
            "rank_csv": str(out_dir / "contribution_rank.csv"),
            "sample_csv": str(out_dir / "contribution_sample_layer.csv"),
            "plot_png": str(out_dir / "module_contribution_bar.png"),
            "plot_positive_png": str(out_dir / "module_contribution_bar_positive.png"),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
