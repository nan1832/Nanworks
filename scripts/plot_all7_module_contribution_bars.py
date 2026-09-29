from pathlib import Path
import argparse
import csv

import matplotlib.pyplot as plt


DEFAULT_ROOT = Path("downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822")
DEFAULT_BLIP_CSV = Path(
    "downloads/evqa_module_contribution/blip2/"
    "evqa_proxy500_blip2_module_contribution_20260602_160202/contribution_layer.csv"
)


def model_paths(root, blip_csv):
    return [
        ("BLIP2-OPT-2.7B", blip_csv),
        ("InstructBLIP-Vicuna-7B", root / "instructblip-vicuna-7b/contribution_layer.csv"),
        ("MiniGPT-4-Vicuna-7B", root / "minigpt-4-vicuna-7b/contribution_layer.csv"),
        ("LLaVA-v1.5-7B", root / "llava-v1.5-7b/contribution_layer.csv"),
        ("Qwen2.5-VL-3B", root / "qwen2.5-vl-3b/contribution_layer.csv"),
        ("PaliGemma-3B", root / "paligemma-3b/contribution_layer.csv"),
        ("SmolVLM-Instruct-1.7B", root / "smolvlm-1.7b/contribution_layer.csv"),
    ]


def load_layers(paths):
    frames = []
    missing = []
    for name, path in paths:
        if not path.exists():
            missing.append(str(path))
            continue
        rows = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "layer": int(row["layer"]),
                        "attn_mean": float(row["attn_mean"]),
                        "mlp_mean": float(row["mlp_mean"]),
                        "score_positive": float(row["score_positive"]),
                        "score_signed": float(row["score_signed"]),
                        "score_abs": float(row["score_abs"]),
                    }
                )
        frames.append({"model": name, "rows": rows})
    if missing:
        raise FileNotFoundError("Missing contribution CSV files:\n" + "\n".join(missing))
    return frames


def top3_label(df):
    top = sorted(df["rows"], key=lambda row: row["score_positive"], reverse=True)[:3]
    return "top3: " + ",".join(str(row["layer"]) for row in top)


def plot(root, frames, key_mode, title_prefix, positive=False):
    fig, axes = plt.subplots(len(frames), 1, figsize=(15, 18), constrained_layout=True)
    colors = {"attn": "#2f6f9f", "mlp": "#d07a2d"}

    for ax, df in zip(axes, frames):
        layers = [row["layer"] for row in df["rows"]]
        attn = [max(0.0, row["attn_mean"]) if positive else row["attn_mean"] for row in df["rows"]]
        mlp = [max(0.0, row["mlp_mean"]) if positive else row["mlp_mean"] for row in df["rows"]]

        ax.bar([layer - 0.18 for layer in layers], attn, width=0.36, label="attn", color=colors["attn"])
        ax.bar([layer + 0.18 for layer in layers], mlp, width=0.36, label="mlp", color=colors["mlp"])
        ax.axhline(0, color="#333333", linewidth=0.7)
        ax.set_xlim(min(layers) - 0.8, max(layers) + 0.8)
        ax.set_ylabel("contribution")
        ax.set_title(f"{df['model']}  ({top3_label(df)})", loc="left", fontsize=11)
        ax.grid(axis="y", color="#dddddd", linewidth=0.6, alpha=0.7)

    axes[-1].set_xlabel("text decoder layer")
    axes[0].legend(loc="upper right", ncols=2, frameon=False)
    kind = "positive" if positive else "signed"
    fig.suptitle(f"{title_prefix} Module Contribution by Layer ({kind}, key token = {key_mode})", fontsize=15)

    stem = root / ("all7_module_contribution_bar_positive" if positive else "all7_module_contribution_bar")
    for suffix in (".png", ".pdf", ".svg"):
        fig.savefig(stem.with_suffix(suffix), dpi=220)
    plt.close(fig)


def write_summary(root, frames):
    rows = []
    for df in frames:
        by_positive = sorted(df["rows"], key=lambda row: row["score_positive"], reverse=True)
        by_signed = sorted(df["rows"], key=lambda row: row["score_signed"], reverse=True)
        by_abs = sorted(df["rows"], key=lambda row: row["score_abs"], reverse=True)
        row = {
            "model": df["model"],
            "num_layers": max(row["layer"] for row in df["rows"]) + 1,
            "top10_positive": ",".join(str(row["layer"]) for row in by_positive[:10]),
            "top10_signed": ",".join(str(row["layer"]) for row in by_signed[:10]),
            "top10_abs": ",".join(str(row["layer"]) for row in by_abs[:10]),
        }
        rows.append(row)
    with (root / "all7_module_contribution_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "num_layers", "top10_positive", "top10_signed", "top10_abs"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--blip-csv", type=Path, default=DEFAULT_BLIP_CSV)
    parser.add_argument("--key-mode", default="alt")
    parser.add_argument("--title-prefix", default="Pilot500")
    args = parser.parse_args()

    frames = load_layers(model_paths(args.root, args.blip_csv))
    plot(args.root, frames, args.key_mode, args.title_prefix, positive=False)
    plot(args.root, frames, args.key_mode, args.title_prefix, positive=True)
    write_summary(args.root, frames)


if __name__ == "__main__":
    main()
