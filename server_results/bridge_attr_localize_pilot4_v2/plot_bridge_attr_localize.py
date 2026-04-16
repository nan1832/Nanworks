import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "layer_metrics.csv"
SUMMARY_PATH = BASE_DIR / "summary.json"
SAMPLE_PATH = BASE_DIR / "samples" / "train_0.json"
OUT_PNG = BASE_DIR / "bridge_attr_localize_overview.png"
OUT_PDF = BASE_DIR / "bridge_attr_localize_overview.pdf"


def load_rows():
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key, value in list(row.items()):
            if key == "layer":
                row[key] = int(value)
            else:
                row[key] = float(value)
    rows = sorted(rows, key=lambda x: x["layer"])
    return rows


def normalized(values):
    arr = np.asarray(values, dtype=float)
    if np.allclose(arr.max(), arr.min()):
        return np.zeros_like(arr)
    return (arr - arr.min()) / (arr.max() - arr.min())


def main():
    rows = load_rows()
    summary = json.load(open(SUMMARY_PATH, "r", encoding="utf-8"))
    sample = json.load(open(SAMPLE_PATH, "r", encoding="utf-8"))

    layers = [row["layer"] for row in rows]
    kl_visual = [row["kl_visual"] for row in rows]
    kl_text = [row["kl_text_anchor"] for row in rows]
    kl_joint = [row["kl_joint"] for row in rows]
    att = [max(0.0, row["att_target_pxv"]) for row in rows]
    mlp = [max(0.0, row["mlp_target_pxv"]) for row in rows]
    visual_norm = [row["visual_rep_norm"] for row in rows]
    visual_cos = [row["visual_track_cos"] for row in rows]

    n_att = normalized(att)
    n_mlp = normalized(mlp)
    n_vnorm = normalized(visual_norm)
    n_vcos = normalized(visual_cos)

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
            f"Predicted token: {sample['pred_token']}",
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
    for x in summary["top_visual_layers"][:3]:
        ax_kl.axvline(x, color="#2A9D8F", linestyle="--", linewidth=1.1, alpha=0.65)
    for x in summary["top_text_layers"][:3]:
        ax_kl.axvline(x, color="#E76F51", linestyle=":", linewidth=1.0, alpha=0.55)
    ax_kl.set_xlim(-0.5, 31.5)
    ax_kl.set_xticks(range(0, 32, 2))
    ax_kl.set_ylabel("KL Divergence")
    ax_kl.set_xlabel("Layer")
    ax_kl.set_title("Layer-wise Causal Sensitivity")
    ax_kl.legend(loc="upper right", ncol=2)
    ax_kl.text(1.0, max(kl_visual) * 0.93, "Peak visual layer = 1", color="#2A9D8F", fontsize=9)
    ax_kl.text(0.1, max(kl_text) * 0.90, "Peak text-sensitivity layer = 0", color="#E76F51", fontsize=9)

    ax_mod.axvspan(-0.5, 4.5, color=early_color, alpha=0.08)
    ax_mod.axvspan(27.5, 31.5, color=late_color, alpha=0.10)
    ax_mod.plot(layers, n_att, color="#0072B2", marker="o", label="Normalized attention contribution")
    ax_mod.plot(layers, n_mlp, color="#D55E00", marker="s", label="Normalized MLP contribution")
    ax_mod.plot(layers, n_vnorm, color="#6C757D", linestyle="--", label="Normalized visual rep norm")
    ax_mod.plot(layers, n_vcos, color="#009E73", linestyle="-.", label="Normalized visual-track cosine")
    ax_mod.set_xlim(-0.5, 31.5)
    ax_mod.set_xticks(range(0, 32, 2))
    ax_mod.set_ylim(-0.02, 1.05)
    ax_mod.set_ylabel("Normalized Score")
    ax_mod.set_xlabel("Layer")
    ax_mod.set_title("Module Contribution and Visual Representation Trend")
    ax_mod.legend(loc="upper left", ncol=2)
    ax_mod.text(30.1, 0.98, "MLP peak = 30", color="#D55E00", fontsize=9, ha="right")
    ax_mod.text(31.0, 0.89, "Attention peak = 31", color="#0072B2", fontsize=9, ha="right")

    fig.suptitle(
        "Bridge Attribution-Based Layer Screening on LLaVA-v1.5-7B",
        y=0.98,
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.015,
        "DualEdit-style perturbation KL localizes visual sensitivity in early layers, while VisEdit-style target-centric "
        "module attribution shows target-word writing concentrates in late attention/MLP layers.",
        ha="center",
        fontsize=9,
    )

    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    print(f"saved {OUT_PNG}")
    print(f"saved {OUT_PDF}")


if __name__ == "__main__":
    main()
