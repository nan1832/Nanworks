import csv
import json
from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "layer_metrics.csv"
SUMMARY_PATH = BASE_DIR / "summary.json"
SAMPLE_PATH = BASE_DIR / "samples" / "train_0.json"
OUT_PNG = BASE_DIR / "bridge_attr_localize_blip2_overview.png"
OUT_PDF = BASE_DIR / "bridge_attr_localize_blip2_overview.pdf"


def load_rows():
    with open(CSV_PATH, "r", encoding="utf-8") as f:
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

    peak_visual = summary["top_visual_layers"][0]
    peak_text = summary["top_text_layers"][0]
    peak_att = summary["top_attention_layers"][0]
    peak_mlp = summary["top_mlp_layers"][0]

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

    fig = plt.figure(figsize=(12.8, 7.8))
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
    ax_kl.axvspan(1.5, 5.5, color=early_color, alpha=0.12, label="Early visual zone (2-5)")
    ax_kl.axvspan(23.5, 31.5, color=late_color, alpha=0.08, label="Late module zone (24-31)")
    ax_kl.axvline(15, color="#8E5EA2", linestyle="--", linewidth=1.2, alpha=0.65, label="Mid-layer attention bridge")
    ax_kl.plot(layers, kl_visual, color="#2A9D8F", marker="o", label="Visual perturbation KL")
    ax_kl.plot(layers, kl_text, color="#E76F51", marker="s", label="Text perturbation KL")
    ax_kl.plot(layers, kl_joint, color="#264653", marker="^", label="Joint perturbation KL")
    for x in summary["top_visual_layers"][:5]:
        ax_kl.axvline(x, color="#2A9D8F", linestyle="--", linewidth=0.9, alpha=0.35)
    for x in summary["top_text_layers"][:5]:
        ax_kl.axvline(x, color="#E76F51", linestyle=":", linewidth=0.9, alpha=0.28)
    ax_kl.set_xlim(-0.5, 31.5)
    ax_kl.set_xticks(range(0, 32, 2))
    ax_kl.set_ylabel("KL Divergence")
    ax_kl.set_xlabel("Layer")
    ax_kl.set_title("Layer-wise Causal Sensitivity")
    ax_kl.legend(loc="upper right", ncol=2)
    ax_kl.text(peak_visual + 0.2, max(kl_visual) * 0.93, f"Peak visual layer = {peak_visual}", color="#2A9D8F", fontsize=9)
    ax_kl.text(peak_text + 0.2, max(kl_text) * 0.90, f"Peak text-sensitivity layer = {peak_text}", color="#E76F51", fontsize=9)

    ax_mod.axvspan(1.5, 5.5, color=early_color, alpha=0.08)
    ax_mod.axvspan(23.5, 31.5, color=late_color, alpha=0.10)
    ax_mod.axvline(15, color="#8E5EA2", linestyle="--", linewidth=1.0, alpha=0.55)
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
    ax_mod.text(peak_att + 0.2, 0.93, f"Attention peak = {peak_att}", color="#0072B2", fontsize=9)
    ax_mod.text(peak_mlp + 0.2, 0.82, f"MLP peak = {peak_mlp}", color="#D55E00", fontsize=9)

    fig.suptitle(
        "Bridge Attribution-Based Layer Screening on BLIP2-OPT-2.7B",
        y=0.98,
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.015,
        "BLIP2 pilot4 shows a mixed visual-sensitivity pattern: early layers 2-5 remain important, layer 15 emerges as a strong "
        "attention-mediated bridge, and target-word writing shifts toward late MLP layers around 29-31.",
        ha="center",
        fontsize=9,
    )

    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    print(f"saved {OUT_PNG}")
    print(f"saved {OUT_PDF}")


if __name__ == "__main__":
    main()
