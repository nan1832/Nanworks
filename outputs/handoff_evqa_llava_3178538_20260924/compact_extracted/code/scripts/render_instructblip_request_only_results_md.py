import argparse
import csv
import pathlib


def read_selected(path: pathlib.Path):
    rows = []
    for layer in range(32):
        selected = path / f"layer_{layer}_target0003" / "selected_checkpoint.tsv"
        if not selected.exists():
            rows.append({"layer": layer, "status": "MISSING"})
            continue
        with selected.open(encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            row = list(reader)[-1]
        row["layer"] = layer
        rows.append(row)
    return rows


def read_metrics(summary: pathlib.Path):
    if not summary.exists():
        return {}
    with summary.open(encoding="utf-8") as f:
        return {int(row["layer"]): row for row in csv.DictReader(f, delimiter="\t")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    out_root = pathlib.Path(args.out_root)
    metrics_path = out_root / "eval_same_entity_full_metrics_rephrase_split" / "selected_full_metrics_summary.tsv"
    selected_rows = read_selected(out_root)
    metrics = read_metrics(metrics_path)

    lines = []
    lines.append("## InstructBLIP Request-Only Full Layer Sweep Results")
    lines.append("")
    lines.append("### Selected Checkpoints")
    lines.append("")
    lines.append("| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |")
    lines.append("|---:|---|---:|---:|---:|---|")
    for row in selected_rows:
        ckpt = pathlib.Path(row.get("checkpoint", "")).name if row.get("checkpoint") else ""
        lines.append(
            f"| {row['layer']} | {row.get('status', '')} | {row.get('epoch', '')} | "
            f"{row.get('ema_loss', '')} | {row.get('diff', '')} | `{ckpt}` |"
        )

    lines.append("")
    lines.append("### Same-Entity Full Metrics")
    lines.append("")
    lines.append(
        "| Layer | Request Acc | Generality Acc | Gen Text | Gen Image | "
        "Locality Acc | Loc Text | Loc Image | Portability Acc | Port 1hop | Port 2hop |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in selected_rows:
        layer = row["layer"]
        m = metrics.get(layer, {})
        lines.append(
            f"| {layer} | {m.get('request_acc', '')} | {m.get('generality_acc', '')} | "
            f"{m.get('generality_text_acc', '')} | {m.get('generality_image_acc', '')} | "
            f"{m.get('locality_acc', '')} | {m.get('locality_text_acc', '')} | "
            f"{m.get('locality_image_acc', '')} | {m.get('portability_acc', '')} | "
            f"{m.get('portability_1hop_acc', '')} | {m.get('portability_2hop_acc', '')} |"
        )

    lines.append("")
    lines.append(f"Selected checkpoint TSV root: `{out_root}`")
    lines.append(f"Metrics summary TSV: `{metrics_path}`")
    lines.append("")

    output = pathlib.Path(args.output_md)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
