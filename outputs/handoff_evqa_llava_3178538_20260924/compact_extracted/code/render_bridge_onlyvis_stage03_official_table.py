import csv
import json
from pathlib import Path


RUN_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
SUMMARY_PATH = RUN_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_official_eval_summary.json"
MD_PATH = RUN_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_official_eval_table.md"
CSV_PATH = RUN_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_official_eval_table.csv"
TEX_PATH = RUN_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_official_eval_table.tex"


FIELDS = [
    ("Layer", "layer"),
    ("EMA loss", "ema_loss"),
    ("Reliability", "reliability_acc"),
    ("Gen-text", "generality_text_rephrase_acc"),
    ("Gen-image", "generality_image_rephrase_acc"),
    ("Loc-text", "locality_text_loc_acc"),
    ("Loc-image", "locality_image_loc_acc"),
    ("Port overall", "portability_overall_acc"),
    ("1-hop", "portability_1hop_acc"),
    ("2-hop", "portability_2hop_acc"),
]


def fmt(value):
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> int:
    rows = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    header = [title for title, _ in FIELDS]
    data_rows = [[fmt(row.get(key)) for _, key in FIELDS] for row in rows]

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data_rows)

    md_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in data_rows:
        md_lines.append("| " + " | ".join(row) + " |")
    MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    tex_lines = [
        "\\begin{tabular}{lccccccccc}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    for row in data_rows:
        tex_lines.append(" & ".join(row) + " \\\\")
    tex_lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    TEX_PATH.write_text("\n".join(tex_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
