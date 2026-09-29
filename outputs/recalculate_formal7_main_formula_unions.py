from __future__ import annotations

import ast
import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "md"
    / "Location"
    / "VisualGradient_11formula_analysis_files_20260720"
    / "analysis_outputs_20260731"
)
OUT = ROOT / "outputs"

DATASET_ORDER = ["evqa-pilot500", "mmke-visual", "mmke-entity"]
MODEL_ORDER = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b",
    "paligemma-3b",
    "smolvlm-1.7b",
]
DISPLAY_DATASET = {
    "evqa-pilot500": "EVQA-pilot500",
    "mmke-visual": "MMKE-visual",
    "mmke-entity": "MMKE-entity",
}
DISPLAY_MODEL = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}

# Formal comparison methods. Perturb-KL Pre is an ablation and is intentionally excluded.
BASELINE_METHODS = [
    "Middle-Prior-Direct",
    "VisEdit-Contrib-Pre-KeyToken",
    "SaLEM-Alt-Direct",
    "LGA-Param-Direct-AltModelPred",
    "Perturb-KL-Direct-AltSeq",
]
OURS_METHOD = "Ours-Direct: M_abscos_x_newn"
CMA_METHOD = "CMA-Direct"
METHOD_ORDER = BASELINE_METHODS + [OURS_METHOD, CMA_METHOD]

# Results completed after the 2026-07-31 structured snapshot and verified on-server.
LIVE_MAIN_COMPLETIONS = {
    ("mmke-visual", "smolvlm-1.7b", 2),
    ("mmke-visual", "llava-v1.5-7b", 0),
    ("mmke-visual", "llava-v1.5-7b", 1),
}

# Incremental results accepted after 2026-08-01. Each entry was checked
# against a non-empty selected_checkpoint.tsv and eval_full.done on shared
# storage; keeping this list explicit makes the generated status reproducible.
LIVE_MAIN_COMPLETIONS.update(
    {
        ("mmke-visual", "llava-v1.5-7b", layer)
        for layer in (2, 3, 7, 8, 9, 12, 14, 15, 16, 22, 24, 26, 27)
    }
)
LIVE_MAIN_COMPLETIONS.update(
    {
        ("mmke-entity", "minigpt-4-vicuna-7b", layer)
        for layer in (0, 1, 3, 4, 6, 14, 16, 22, 26, 27)
    }
)
LIVE_MAIN_COMPLETIONS.update(
    {
        ("evqa-pilot500", "minigpt-4-vicuna-7b", layer)
        for layer in (0, 1, 2, 7, 8, 9, 10, 14, 15, 19, 22, 29)
    }
)
LIVE_MAIN_COMPLETIONS.update(
    {
        ("evqa-pilot500", "instructblip-vicuna-7b", layer)
        for layer in (0, 1, 2, 3, 4, 11, 14, 15, 16, 18, 19, 25)
    }
)
LIVE_MAIN_COMPLETIONS.update(
    {
        ("evqa-pilot500", "llava-v1.5-7b", layer)
        for layer in (15, 16)
    }
)
LIVE_MAIN_COMPLETIONS.update(
    {
        ("mmke-visual", "paligemma-3b", 4),
        ("mmke-entity", "blip2-opt-2.7b", 1),
        ("evqa-pilot500", "paligemma-3b", 3),
    }
)

# Known terminal failures without an accepted full evaluation. These are recorded as
# failures instead of being silently treated as ordinary pending work.
KNOWN_FAILURES = {
    ("evqa-pilot500", "paligemma-3b", 0): "主配置与stable均不收敛",
    ("mmke-visual", "paligemma-3b", 0): "stable不收敛",
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (SOURCE / name).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_baseline_layers(value: str) -> list[int]:
    return [int(x) for x in ast.literal_eval(value)]


def parse_formula_layers(value: str) -> list[int]:
    if not value.strip():
        return []
    return [int(x.removeprefix("L")) for x in value.split(",")]


def ordered_union(groups: list[list[int]]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for group in groups:
        for layer in group:
            if layer not in seen:
                seen.add(layer)
                result.append(layer)
    return result


def fmt_layers(layers: list[int]) -> str:
    return ",".join(f"L{x}" for x in layers) if layers else "-"


baseline_rows = read_csv("baseline_candidates.csv")
formula_rows = read_csv("formula_topk_all_21.csv")
accepted_rows = read_csv("accepted_outcome_rows.csv")

candidates: dict[tuple[str, str, str], dict[str, list[int]]] = {}
for row in baseline_rows:
    method = row["method"]
    if method not in BASELINE_METHODS and method != CMA_METHOD:
        continue
    key = (row["dataset"], row["model"], method)
    candidates[key] = {
        "top3": parse_baseline_layers(row["top3"]),
        "top5": parse_baseline_layers(row["top5"]),
    }

ours_rows = [r for r in formula_rows if r["formula"] == "M_abscos_x_newn"]
for row in ours_rows:
    key = (row["dataset"], row["model"], OURS_METHOD)
    candidates[key] = {
        "top3": parse_formula_layers(row["top3"]),
        "top5": parse_formula_layers(row["top5"]),
    }

completed_main: dict[tuple[str, str], set[int]] = defaultdict(set)
completed_stable: dict[tuple[str, str], set[int]] = defaultdict(set)
for row in accepted_rows:
    if row["variant"] == "main":
        completed_main[(row["dataset"], row["model"])].add(int(row["layer"]))
    elif row["variant"] == "stable":
        completed_stable[(row["dataset"], row["model"])].add(int(row["layer"]))
for dataset, model, layer in LIVE_MAIN_COMPLETIONS:
    completed_main[(dataset, model)].add(layer)

expected_combos = {(d, m) for d in DATASET_ORDER for m in MODEL_ORDER}
actual_ours = {(r["dataset"], r["model"]) for r in ours_rows}
assert actual_ours == expected_combos, (expected_combos - actual_ours, actual_ours - expected_combos)
for dataset, model in sorted(expected_combos):
    for method in METHOD_ORDER:
        assert (dataset, model, method) in candidates, (dataset, model, method)

summary_rows: list[dict[str, object]] = []
ours_summary_rows: list[dict[str, str]] = []
for dataset in DATASET_ORDER:
    for model in MODEL_ORDER:
        groups3 = [candidates[(dataset, model, method)]["top3"] for method in METHOD_ORDER]
        groups5 = [candidates[(dataset, model, method)]["top5"] for method in METHOD_ORDER]
        union3 = ordered_union(groups3)
        union5 = ordered_union(groups5)
        assert set(union3).issubset(union5)
        main_done = completed_main[(dataset, model)]
        stable_only = completed_stable[(dataset, model)] - main_done
        failed = {layer for d, m, layer in KNOWN_FAILURES if (d, m) == (dataset, model)}

        main_done3 = [x for x in union3 if x in main_done]
        stable_only3 = [x for x in union3 if x in stable_only]
        failed3 = [x for x in union3 if x in failed and x not in main_done and x not in stable_only]
        pending3 = [x for x in union3 if x not in main_done and x not in stable_only and x not in failed]
        done3 = main_done3 + stable_only3

        main_done5 = [x for x in union5 if x in main_done]
        stable_only5 = [x for x in union5 if x in stable_only]
        failed5 = [x for x in union5 if x in failed and x not in main_done and x not in stable_only]
        pending5 = [x for x in union5 if x not in main_done and x not in stable_only and x not in failed]
        done5 = main_done5 + stable_only5

        def completed_display(main_layers: list[int], stable_layers: list[int]) -> str:
            chunks: list[str] = []
            if main_layers:
                chunks.append("主:" + fmt_layers(main_layers))
            if stable_layers:
                chunks.append("stable-only:" + fmt_layers(stable_layers))
            return "；".join(chunks) if chunks else "-"
        ours = candidates[(dataset, model, OURS_METHOD)]
        ours_summary_rows.append(
            {
                "dataset": DISPLAY_DATASET[dataset],
                "model": DISPLAY_MODEL[model],
                "top3": fmt_layers(ours["top3"]),
                "top5": fmt_layers(ours["top5"]),
            }
        )
        summary_rows.append(
            {
                "dataset": DISPLAY_DATASET[dataset],
                "model": DISPLAY_MODEL[model],
                "top3_union": fmt_layers(union3),
                "top3_count": len(union3),
                "top3_done": completed_display(main_done3, stable_only3),
                "top3_done_count": len(done3),
                "top3_failed": fmt_layers(failed3),
                "top3_failed_count": len(failed3),
                "top3_pending": fmt_layers(pending3),
                "top3_pending_count": len(pending3),
                "top5_union": fmt_layers(union5),
                "top5_count": len(union5),
                "top5_done": completed_display(main_done5, stable_only5),
                "top5_done_count": len(done5),
                "top5_failed": fmt_layers(failed5),
                "top5_failed_count": len(failed5),
                "top5_pending": fmt_layers(pending5),
                "top5_pending_count": len(pending5),
            }
        )

csv_path = OUT / "formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv"
with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_rows[0]))
    writer.writeheader()
    writer.writerows(summary_rows)

md_path = OUT / "formal7_M_abscos_x_newn_top3_top5_union_status_20260801.md"
with md_path.open("w", encoding="utf-8", newline="\n") as f:
    f.write("### Ours-Direct 主公式 Top-3 / Top-5（21 组）\n\n")
    f.write("| Dataset | Model | Top-3 | Top-5 |\n|---|---|---|---|\n")
    for row in ours_summary_rows:
        f.write(f"| {row['dataset']} | {row['model']} | {row['top3']} | {row['top5']} |\n")
    f.write("\n### 正式 7 方法 Top-3 并集及主配置完成情况\n\n")
    f.write("| Dataset | Model | Top-3并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |\n")
    f.write("|---|---|---|---:|---|---:|---|---|---:|\n")
    for row in summary_rows:
        f.write(
            f"| {row['dataset']} | {row['model']} | {row['top3_union']} | {row['top3_count']} | "
            f"{row['top3_done']} | {row['top3_done_count']} | {row['top3_failed']} | "
            f"{row['top3_pending']} | {row['top3_pending_count']} |\n"
        )
    f.write("\n### 正式 7 方法 Top-5 并集及主配置完成情况\n\n")
    f.write("| Dataset | Model | Top-5并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |\n")
    f.write("|---|---|---|---:|---|---:|---|---|---:|\n")
    for row in summary_rows:
        f.write(
            f"| {row['dataset']} | {row['model']} | {row['top5_union']} | {row['top5_count']} | "
            f"{row['top5_done']} | {row['top5_done_count']} | {row['top5_failed']} | "
            f"{row['top5_pending']} | {row['top5_pending_count']} |\n"
        )

print(csv_path)
print(md_path)
print(f"ours_rows={len(ours_summary_rows)} summary_rows={len(summary_rows)}")
print(
    "top3_total/done/pending="
    f"{sum(int(r['top3_count']) for r in summary_rows)}/"
    f"{sum(int(r['top3_done_count']) for r in summary_rows)}/"
    f"{sum(int(r['top3_pending_count']) for r in summary_rows)}"
)
print(
    "top3_failed="
    f"{sum(int(r['top3_failed_count']) for r in summary_rows)}"
)
print(
    "top5_total/done/pending="
    f"{sum(int(r['top5_count']) for r in summary_rows)}/"
    f"{sum(int(r['top5_done_count']) for r in summary_rows)}/"
    f"{sum(int(r['top5_pending_count']) for r in summary_rows)}"
)
print(
    "top5_failed="
    f"{sum(int(r['top5_failed_count']) for r in summary_rows)}"
)
