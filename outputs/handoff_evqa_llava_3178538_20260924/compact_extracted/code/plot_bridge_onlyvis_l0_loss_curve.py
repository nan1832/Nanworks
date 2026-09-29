import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "server_results" / "bridge_onlyvis_l0_loss_curve"
CSV_PATH = OUT_DIR / "l0_loss_curve_points.csv"
PNG_PATH = OUT_DIR / "bridge_onlyvis_l0_loss_curve.png"
PDF_PATH = OUT_DIR / "bridge_onlyvis_l0_loss_curve.pdf"

CHECKPOINT_NAMES = [
    "epoch-4-i-100-ema_loss-5.9568",
    "epoch-7-i-200-ema_loss-1.9095",
    "epoch-10-i-300-ema_loss-0.5991",
    "epoch-14-i-400-ema_loss-0.4625",
    "epoch-17-i-500-ema_loss-0.4225",
    "epoch-20-i-600-ema_loss-0.4010",
    "epoch-24-i-700-ema_loss-0.3741",
    "epoch-27-i-800-ema_loss-0.4027",
    "epoch-30-i-900-ema_loss-0.3704",
    "epoch-34-i-1000-ema_loss-0.3652",
    "epoch-37-i-1100-ema_loss-0.3644",
    "epoch-40-i-1200-ema_loss-0.3427",
    "epoch-44-i-1300-ema_loss-0.3891",
    "epoch-47-i-1400-ema_loss-0.3794",
    "epoch-50-i-1500-ema_loss-0.3802",
    "epoch-54-i-1600-ema_loss-0.3584",
    "epoch-57-i-1700-ema_loss-0.3746",
    "epoch-60-i-1800-ema_loss-0.3217",
    "epoch-64-i-1900-ema_loss-0.3503",
    "epoch-67-i-2000-ema_loss-0.3014",
    "epoch-70-i-2100-ema_loss-0.3469",
    "epoch-74-i-2200-ema_loss-0.3332",
    "epoch-77-i-2300-ema_loss-0.3383",
    "epoch-80-i-2400-ema_loss-0.3285",
    "epoch-84-i-2500-ema_loss-0.3691",
    "epoch-87-i-2600-ema_loss-0.3332",
    "epoch-90-i-2700-ema_loss-0.3471",
    "epoch-94-i-2800-ema_loss-0.2961",
    "epoch-97-i-2900-ema_loss-0.3718",
    "epoch-100-i-3000-ema_loss-0.3437",
    "epoch-104-i-3100-ema_loss-0.3272",
    "epoch-107-i-3200-ema_loss-0.3446",
    "epoch-110-i-3300-ema_loss-0.3262",
    "epoch-114-i-3400-ema_loss-0.3093",
    "epoch-117-i-3500-ema_loss-0.3375",
    "epoch-120-i-3600-ema_loss-0.2804",
    "epoch-124-i-3700-ema_loss-0.3326",
    "epoch-127-i-3800-ema_loss-0.3251",
    "epoch-130-i-3900-ema_loss-0.3233",
    "epoch-134-i-4000-ema_loss-0.2993",
    "epoch-137-i-4100-ema_loss-0.2786",
    "epoch-140-i-4200-ema_loss-0.3223",
    "epoch-144-i-4300-ema_loss-4.6250",
    "epoch-147-i-4400-ema_loss-0.8114",
    "epoch-150-i-4500-ema_loss-0.6709",
    "epoch-154-i-4600-ema_loss-0.4485",
    "epoch-157-i-4700-ema_loss-0.8597",
    "epoch-160-i-4800-ema_loss-0.4924",
    "epoch-164-i-4900-ema_loss-0.4816",
    "epoch-167-i-5000-ema_loss-0.3641",
    "epoch-170-i-5100-ema_loss-0.3308",
]

PATTERN = re.compile(r"epoch-(\d+)-i-(\d+)-ema_loss-([0-9.]+)")


def parse_points():
    rows = []
    for name in CHECKPOINT_NAMES:
        match = PATTERN.fullmatch(name)
        if not match:
            raise ValueError(f"Bad checkpoint name: {name}")
        epoch, step, loss = match.groups()
        rows.append(
            {
                "checkpoint": name,
                "epoch": int(epoch),
                "step": int(step),
                "ema_loss": float(loss),
            }
        )
    return rows


def write_csv(rows):
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["checkpoint", "epoch", "step", "ema_loss"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot(rows):
    epochs = [row["epoch"] for row in rows]
    losses = [row["ema_loss"] for row in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)

    ax.plot(
        epochs,
        losses,
        color="#1f77b4",
        marker="o",
        markersize=4,
        linewidth=2.2,
        label="EMA loss from saved checkpoints",
    )

    ax.axhline(0.30, color="#d62728", linestyle="--", linewidth=1.6, label="Target loss = 0.30")

    best_row = min(rows, key=lambda row: abs(row["ema_loss"] - 0.30))
    ax.scatter(
        [best_row["epoch"]],
        [best_row["ema_loss"]],
        s=70,
        color="#2ca02c",
        zorder=5,
        label=f"Closest to 0.30: epoch {best_row['epoch']}",
    )
    ax.annotate(
        f"epoch {best_row['epoch']}\nloss {best_row['ema_loss']:.4f}",
        xy=(best_row["epoch"], best_row["ema_loss"]),
        xytext=(best_row["epoch"] + 7, best_row["ema_loss"] + 0.35),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="#2ca02c"),
        fontsize=9,
        color="#2ca02c",
    )

    spike_row = max(rows, key=lambda row: row["ema_loss"])
    ax.scatter([spike_row["epoch"]], [spike_row["ema_loss"]], s=60, color="#ff7f0e", zorder=5)
    ax.annotate(
        f"spike at epoch {spike_row['epoch']}\nloss {spike_row['ema_loss']:.4f}",
        xy=(spike_row["epoch"], spike_row["ema_loss"]),
        xytext=(spike_row["epoch"] - 34, spike_row["ema_loss"] - 1.1),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="#ff7f0e"),
        fontsize=9,
        color="#ff7f0e",
    )

    ax.set_title("Bridge only-vis l0 training loss curve", fontsize=14, weight="bold")
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel("EMA loss", fontsize=11)
    ax.set_xlim(min(epochs) - 2, max(epochs) + 2)
    ax.set_ylim(0, max(losses) * 1.08)
    ax.legend(frameon=True, fontsize=9, loc="upper right")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.45)

    fig.tight_layout()
    fig.savefig(PNG_PATH, bbox_inches="tight")
    fig.savefig(PDF_PATH, bbox_inches="tight")
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = parse_points()
    write_csv(rows)
    plot(rows)
    print(CSV_PATH)
    print(PNG_PATH)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
