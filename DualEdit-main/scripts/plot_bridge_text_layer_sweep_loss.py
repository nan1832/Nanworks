import argparse
import csv
import json
from pathlib import Path


def rows_from_inventory_payload(payload):
    layer = int(payload["layer"])
    rows = []
    for checkpoint in payload.get("checkpoints", []):
        rows.append(
            {
                "layer": layer,
                "epoch": int(checkpoint["epoch"]),
                "iter": int(checkpoint["iter"]),
                "loss": float(checkpoint["loss"]),
                "loss_kind": checkpoint.get("loss_kind", "loss"),
            }
        )
    return rows


def collect_loss_rows_from_out_root(out_root):
    out_root = Path(out_root)
    rows = []
    for inventory_path in sorted(out_root.glob("layer_*/checkpoint_inventory.json")):
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        rows.extend(rows_from_inventory_payload(payload))
    return sorted(rows, key=lambda row: (row["layer"], row["epoch"], row["iter"]))


def collect_loss_rows_from_layer_mapping(payload):
    rows = []
    for layer_key, checkpoints in payload.items():
        rows.extend(
            rows_from_inventory_payload(
                {
                    "layer": int(layer_key),
                    "checkpoints": checkpoints,
                }
            )
        )
    return sorted(rows, key=lambda row: (row["layer"], row["epoch"], row["iter"]))


def collect_loss_rows(out_root=None, inventory_json=None):
    if inventory_json is not None:
        payload = json.loads(Path(inventory_json).read_text(encoding="utf-8-sig"))
        return collect_loss_rows_from_layer_mapping(payload)
    if out_root is None:
        raise ValueError("Either out_root or inventory_json must be provided.")
    return collect_loss_rows_from_out_root(out_root)


def write_rows_csv(rows, csv_path):
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["layer", "epoch", "iter", "loss", "loss_kind"],
        )
        writer.writeheader()
        writer.writerows(rows)


def plot_loss_curves(rows, output_path, title, log_y=True):
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    layer_to_rows = {}
    for row in rows:
        layer_to_rows.setdefault(int(row["layer"]), []).append(row)

    fig, ax = plt.subplots(figsize=(12, 7))
    cmap = plt.get_cmap("tab20")
    ordered_layers = sorted(layer_to_rows)
    for idx, layer in enumerate(ordered_layers):
        layer_rows = sorted(layer_to_rows[layer], key=lambda item: (item["epoch"], item["iter"]))
        epochs = [item["epoch"] for item in layer_rows]
        losses = [item["loss"] for item in layer_rows]
        ax.plot(
            epochs,
            losses,
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=cmap(idx % 20),
            label=f"L{layer}",
        )

    ax.set_title(title)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("EMA Loss")
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.4)
    ax.legend(
        title="Text Edit Layer",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        ncol=1,
    )
    fig.tight_layout(rect=(0, 0, 0.84, 1))
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Plot epoch-loss curves for the bridge text-adapter layer sweep."
    )
    parser.add_argument("--out_root", default=None)
    parser.add_argument("--inventory_json", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--csv_output", default=None)
    parser.add_argument(
        "--title",
        default="Bridge Text-Adapter Sweep: Epoch vs EMA Loss",
    )
    parser.add_argument("--linear_y", action="store_true")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    rows = collect_loss_rows(out_root=args.out_root, inventory_json=args.inventory_json)
    if not rows:
        raise ValueError("No checkpoint rows found for plotting.")
    csv_output = args.csv_output or str(Path(args.output).with_suffix(".csv"))
    write_rows_csv(rows, csv_output)
    plot_loss_curves(
        rows,
        output_path=args.output,
        title=args.title,
        log_y=not args.linear_y,
    )
    print(f"rows={len(rows)}")
    print(f"csv={csv_output}")
    print(f"figure={args.output}")


if __name__ == "__main__":
    main()
