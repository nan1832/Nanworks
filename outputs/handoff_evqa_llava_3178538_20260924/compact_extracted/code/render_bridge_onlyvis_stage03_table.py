import csv
import json
from pathlib import Path


DEFAULT_SUMMARY = Path(
    "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/records/job_logs/bridge_onlyvis_stage03_eval_summary.json"
)
DEFAULT_MD = DEFAULT_SUMMARY.with_name("bridge_onlyvis_stage03_eval_table.md")
DEFAULT_CSV = DEFAULT_SUMMARY.with_name("bridge_onlyvis_stage03_eval_table.csv")
DEFAULT_TEX = DEFAULT_SUMMARY.with_name("bridge_onlyvis_stage03_eval_table.tex")

ORDER = ["l1", "l18", "l20"]
LABELS = {"l1": "1", "l18": "18", "l20": "20"}


def pct(x: float) -> float:
    return round(float(x) * 100.0, 2)


def fmt_count(block: dict, key: str) -> str:
    correct_key = "strict_correct" if key == "strict_acc" else "loose_correct"
    return f"{block[correct_key]}/{block['total']}"


def load_rows(summary_path: Path):
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = []
    for tag in ORDER:
        ckpt = data["checkpoints"][tag]
        entity = data["entity_recognition"][tag]
        open_end = data["open_end_qa"][tag]
        rows.append(
            {
                "tag": tag,
                "layer": LABELS[tag],
                "checkpoint": Path(ckpt["ckpt_path"]).name,
                "ema_loss": float(ckpt["ema_loss"]),
                "entity_strict_count": fmt_count(entity, "strict_acc"),
                "entity_strict_pct": pct(entity["strict_acc"]),
                "entity_loose_count": fmt_count(entity, "loose_acc"),
                "entity_loose_pct": pct(entity["loose_acc"]),
                "open_strict_count": fmt_count(open_end, "strict_acc"),
                "open_strict_pct": pct(open_end["strict_acc"]),
                "open_loose_count": fmt_count(open_end, "loose_acc"),
                "open_loose_pct": pct(open_end["loose_acc"]),
            }
        )
    return rows


def write_csv(rows, out_path: Path):
    fieldnames = [
        "layer",
        "checkpoint",
        "ema_loss",
        "entity_strict_count",
        "entity_strict_pct",
        "entity_loose_count",
        "entity_loose_pct",
        "open_strict_count",
        "open_strict_pct",
        "open_loose_count",
        "open_loose_pct",
    ]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})


def write_md(rows, out_path: Path):
    lines = [
        "# Bridge only-vis stage-0.3 comparison",
        "",
        "| Layer | Checkpoint | EMA loss | Entity strict | Entity loose | Open-end strict | Open-end loose |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['layer']} | `{row['checkpoint']}` | {row['ema_loss']:.4f} | "
            f"{row['entity_strict_count']} ({row['entity_strict_pct']:.2f}\\%) | "
            f"{row['entity_loose_count']} ({row['entity_loose_pct']:.2f}\\%) | "
            f"{row['open_strict_count']} ({row['open_strict_pct']:.2f}\\%) | "
            f"{row['open_loose_count']} ({row['open_loose_pct']:.2f}\\%) |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tex(rows, out_path: Path):
    body = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Loss-matched stage-$0.3$ comparison of only-vision adapter insertion layers on the bridge validation set.}",
        r"\label{tab:bridge_onlyvis_stage03_layers}",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"Layer & EMA Loss & Entity Strict (\%) & Entity Loose (\%) & Open-end Strict (\%) & Open-end Loose (\%) & Checkpoint \\",
        r"\midrule",
    ]
    for row in rows:
        body.append(
            f"{row['layer']} & {row['ema_loss']:.4f} & {row['entity_strict_pct']:.2f} & "
            f"{row['entity_loose_pct']:.2f} & {row['open_strict_pct']:.2f} & "
            f"{row['open_loose_pct']:.2f} & \\texttt{{{row['checkpoint']}}} \\\\"
        )
    body.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    out_path.write_text("\n".join(body) + "\n", encoding="utf-8")


def main():
    summary_path = DEFAULT_SUMMARY
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary file: {summary_path}")
    rows = load_rows(summary_path)
    write_csv(rows, DEFAULT_CSV)
    write_md(rows, DEFAULT_MD)
    write_tex(rows, DEFAULT_TEX)
    print(DEFAULT_MD)
    print(DEFAULT_CSV)
    print(DEFAULT_TEX)


if __name__ == "__main__":
    main()
