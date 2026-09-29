import argparse
import csv
import json
from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=str,
        default="records/bridge_attr_localize_pred",
        help="Directory containing layer_metrics.csv, summary.json and samples/*.json",
    )
    parser.add_argument(
        "--sample-id",
        type=str,
        default="",
        help="Optional sample id, e.g. train_0. If empty, use first sample file found.",
    )
    return parser.parse_args()


def load_rows(csv_path: Path):
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key, value in list(row.items()):
            if key == "layer":
                row[key] = int(value)
            else:
                row[key] = float(value)
    return sorted(rows, key=lambda x: x["layer"])


def normalized(values):
    arr = np.asarray(values, dtype=float)
    if np.allclose(arr.max(), arr.min()):
        return np.zeros_like(arr)
    return (arr - arr.min()) / (arr.max() - arr.min())


def pick_sample(samples_dir: Path, sample_id: str) -> Path:
    if sample_id:
        p = samples_dir / f"{sample_id}.json"
        if not p.exists():
            raise FileNotFoundError(f"Sample file not found: {p}")
        return p
    files = sorted(samples_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No sample json found in {samples_dir}")
    return files[0]


def main():
    args = parse_args()
    in_dir = Path(args.input_dir).resolve()
    csv_path = in_dir / "layer_metrics.csv"
    summary_path = in_dir / "summary.json"
    samples_dir = in_dir / "samples"
    sample_path = pick_sample(samples_dir, args.sample_id)

    out_png = in_dir / "bridge_attr_localize_pred_overview.png"
    out_pdf = in_dir / "bridge_attr_localize_pred_overview.pdf"

    rows = load_rows(csv_path)
    summary = json.load(open(summary_path, "r", encoding="utf-8"))
    sample = json.load(open(sample_path, "r", encoding="utf-8"))

    layers = [row["layer"] for row in rows]
    kl_visual = [row["kl_visual"] for row in rows]
    kl_text = [row["kl_text_anchor"] for row in rows]
    kl_joint = [row["kl_joint"] for row in rows]

    att_pred = [max(0.0, row["att_pred_pxv"]) for row in rows]
    mlp_pred = [max(0.0, row["mlp_pred_pxv"]) for row in rows]
    visual_norm = [row["visual_rep_norm"] for row in rows]
    visual_cos = [row["visual_track_cos"] for row in rows]

    n_att_pred = normalized(att_pred)
    n_mlp_pred = normalized(mlp_pred)
    n_vnorm = normalized(visual_norm)
    n_vcos = normalized(visual_cos)

    top_att_pred = summary.get("top_attention_pred_layers", summary.get("top_attention_layers", []))
    top_mlp_pred = summary.get("top_mlp_pred_layers", summary.get("top_mlp_layers", []))
    peak_att_pred = top_att_pred[0] if top_att_pred else 0
    peak_mlp_pred = top_mlp_pred[0] if top_mlp_pred else 0
    peak_visual = summary.get("top_visual_layers", [0])[0]
    peak_text = summary.get("top_text_layers", [0])[0]

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
            "axes.grid": True,
            "grid.alpha": 0.15,
        }
    )

    fig = plt.figure(figsize=(12.8, 7.6))
    gs = gridspec.GridSpec(
        2, 2, width_ratios=[1.05, 3.2], height_ratios=[1.0, 1.0], wspace=0.28, hspace=0.30
    )

    ax_img = fig.add_subplot(gs[:, 0])
    ax_kl = fig.add_subplot(gs[0, 1])
    ax_mod = fig.add_subplot(gs[1, 1])

    ax_img.axis("off")
    img = plt.imread(sample["image_path"])
    ax_img.imshow(img)
    ax_img.set_title("Pilot Sample", pad=8)
    prompt = sample["prompt"].replace(" The answer is:", "")
    text_block = "\n".join(
        [
            f"Prompt: {prompt}",
            f"Entity: {sample['entity_name']}",
            f"Predicted token: {sample['pred_token']!r}",
            f"Visual token span: {sample['vt_range'][0]}-{sample['vt_range'][1] - 1}",
            f"Tracked text pos: {sample['track_position']}",
            f"Pilot size: {summary['sample_count']} bridge samples",
        ]
    )
    ax_img.text(
        0.0,
        -0.06,
        text_block,
        transform=ax_img.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7f7f5", edgecolor="#d0d0d0"),
    )

    early_color = "#F4A261"
    late_color = "#56B4E9"
    ax_kl.axvspan(-0.5, 4.5, color=early_color, alpha=0.12, label="Visual-edit candidate zone")
    ax_kl.axvspan(27.5, 31.5, color=late_color, alpha=0.08, label="Late text/module zone")
    ax_kl.plot(layers, kl_visual, color="#2A9D8F", marker="o", label="Visual perturbation KL")
    ax_kl.plot(layers, kl_text, color="#E76F51", marker="s", label="Text perturbation KL")
    ax_kl.plot(layers, kl_joint, color="#264653", marker="^", label="Joint perturbation KL")
    for x in summary.get("top_visual_layers", [])[:3]:
        ax_kl.axvline(x, color="#2A9D8F", linestyle="--", linewidth=1.1, alpha=0.65)
    for x in summary.get("top_text_layers", [])[:3]:
        ax_kl.axvline(x, color="#E76F51", linestyle=":", linewidth=1.0, alpha=0.55)
    ax_kl.set_xlim(-0.5, 31.5)
    ax_kl.set_xticks(range(0, 32, 2))
    ax_kl.set_ylabel("KL Divergence")
    ax_kl.set_xlabel("Layer")
    ax_kl.set_title("Layer-wise Causal Sensitivity")
    ax_kl.legend(loc="upper right", ncol=2)
    ax_kl.text(peak_visual + 0.2, max(kl_visual) * 0.93, f"Peak visual layer = {peak_visual}", color="#2A9D8F", fontsize=9)
    ax_kl.text(peak_text + 0.2, max(kl_text) * 0.90, f"Peak text-sensitivity layer = {peak_text}", color="#E76F51", fontsize=9)

    ax_mod.axvspan(-0.5, 4.5, color=early_color, alpha=0.08)
    ax_mod.axvspan(27.5, 31.5, color=late_color, alpha=0.10)
    ax_mod.plot(layers, n_att_pred, color="#0072B2", marker="o", label="Normalized attention contribution (pred)")
    ax_mod.plot(layers, n_mlp_pred, color="#D55E00", marker="s", label="Normalized MLP contribution (pred)")
    ax_mod.plot(layers, n_vnorm, color="#6C757D", linestyle="--", label="Normalized visual rep norm")
    ax_mod.plot(layers, n_vcos, color="#009E73", linestyle="-.", label="Normalized visual-track cosine")
    ax_mod.set_xlim(-0.5, 31.5)
    ax_mod.set_xticks(range(0, 32, 2))
    ax_mod.set_ylim(-0.02, 1.05)
    ax_mod.set_ylabel("Normalized Score")
    ax_mod.set_xlabel("Layer")
    ax_mod.set_title("Prediction-Centric Module Contribution Trend")
    ax_mod.legend(loc="upper left", ncol=2)
    ax_mod.text(peak_mlp_pred + 0.2, 0.93, f"MLP pred peak = {peak_mlp_pred}", color="#D55E00", fontsize=9)
    ax_mod.text(peak_att_pred + 0.2, 0.84, f"Attention pred peak = {peak_att_pred}", color="#0072B2", fontsize=9)

    fig.suptitle(
        "Bridge Prediction-Centric Layer Screening on LLaVA-v1.5-7B",
        y=0.98,
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.015,
        "Prediction-centric view: module contribution is computed against the model's own chosen token, "
        "to explain how the unedited model's answer gets selected.",
        ha="center",
        fontsize=9,
    )

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    print(f"saved {out_png}")
    print(f"saved {out_pdf}")


if __name__ == "__main__":
    main()
