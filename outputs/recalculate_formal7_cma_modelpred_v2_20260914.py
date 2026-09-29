from __future__ import annotations

import ast
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "md"
    / "Location"
    / "VisualGradient_11formula_analysis_files_20260720"
    / "analysis_outputs_20260731"
)
MANUAL = ROOT / "md" / "Location" / "6location_7model_3datas_top_3_5_layers_outcome.md"
LIVE = ROOT / "outputs" / "formal7_live_main_outcomes_20260824.csv"
OUT = ROOT / "outputs"

VERSION = "formal7-cma-modelpred-v2-20260914"
DATASETS = ["evqa-pilot500", "mmke-visual", "mmke-entity"]
MODELS = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b",
    "paligemma-3b",
    "smolvlm-1.7b",
]
METHODS = [
    "Middle-Prior-Direct",
    "VisEdit-Contrib-Pre-KeyToken",
    "SaLEM-Alt-Direct",
    "LGA-Param-Direct-AltModelPred",
    "Perturb-KL-Direct-AltSeq",
    "Ours-Direct",
    "CMA-ModelPred-Direct",
]
BASELINES = METHODS[:5]

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
DATASET_FROM_DISPLAY = {value: key for key, value in DISPLAY_DATASET.items()}
MODEL_FROM_DISPLAY = {value: key for key, value in DISPLAY_MODEL.items()}
MODEL_FROM_MANUAL = {
    "blip2-opt-2.7b": "blip2-opt-2.7b",
    "instructblip-vicuna-7b": "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b": "minigpt-4-vicuna-7b",
    "llava-v1.5-7b": "llava-v1.5-7b",
    "qwen2.5-vl-3b": "qwen2.5-vl-3b",
    "paligemma-3b": "paligemma-3b",
    "smolvlm-1.7b": "smolvlm-1.7b",
}

KNOWN_FAILURES = {
    ("evqa-pilot500", "paligemma-3b", 0): "main_and_stable_nonconvergent_no_eval",
    ("mmke-visual", "paligemma-3b", 0): "stable_nonconvergent_no_eval",
}


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_layers(text: str) -> list[int]:
    value = text.strip()
    if not value or value == "-":
        return []
    if value.startswith("["):
        return [int(item) for item in ast.literal_eval(value)]
    return [int(item.strip().removeprefix("L")) for item in value.split(",")]


def fmt_layers(layers: list[int]) -> str:
    return ",".join(f"L{layer}" for layer in layers) if layers else "-"


def ordered_union(groups: list[list[int]]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for group in groups:
        for layer in group:
            if layer not in seen:
                seen.add(layer)
                result.append(layer)
    return result


manual_lines = MANUAL.read_text(encoding="utf-8").splitlines()

# Read the five unchanged baselines.
candidates: dict[tuple[str, str, str], dict[str, object]] = {}
for row in csv_rows(SOURCE / "baseline_candidates.csv"):
    method = row["method"]
    if method not in BASELINES:
        continue
    candidates[(row["dataset"], row["model"], method)] = {
        "top3": parse_layers(row["top3"]),
        "top5": parse_layers(row["top5"]),
        "status": row["status"],
    }

# Read the single formal Ours formula.
for row in csv_rows(SOURCE / "formula_topk_all_21.csv"):
    if row["formula"] != "M_abscos_x_newn":
        continue
    candidates[(row["dataset"], row["model"], "Ours-Direct")] = {
        "top3": parse_layers(row["top3"]),
        "top5": parse_layers(row["top5"]),
        "status": f"{row['status']}; coverage={row['coverage']}",
    }

# Read CMA-ModelPred candidates from section 2.8.1, not the historical CMA rows.
cma_header = "| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |"
try:
    cma_start = manual_lines.index(cma_header)
except ValueError as exc:
    raise RuntimeError("CMA-ModelPred table header was not found in the manual") from exc

for line in manual_lines[cma_start + 2 :]:
    if not line.startswith("|"):
        break
    columns = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(columns) != 9:
        raise RuntimeError(f"Unexpected CMA-ModelPred row: {line}")
    dataset = DATASET_FROM_DISPLAY[columns[0]]
    model = MODEL_FROM_DISPLAY[columns[1]]
    candidates[(dataset, model, "CMA-ModelPred-Direct")] = {
        "top3": parse_layers(columns[2]),
        "top5": parse_layers(columns[3]),
        "status": (
            f"modelpred={columns[4]}; cma_valid={columns[5]}; "
            f"coverage={columns[6]}; {columns[8].replace('**', '')}"
        ),
    }

expected_candidates = {
    (dataset, model, method)
    for dataset in DATASETS
    for model in MODELS
    for method in METHODS
}
if set(candidates) != expected_candidates:
    raise RuntimeError(
        f"Candidate coverage mismatch: missing={expected_candidates - set(candidates)}, "
        f"extra={set(candidates) - expected_candidates}"
    )

# Merge historical accepted results, later server increments, and the latest detailed
# manual rows. Existing machine-readable precision wins; manual rows only fill gaps.
main_results: dict[tuple[str, str, int], float] = {}
stable_results: dict[tuple[str, str, int], float] = {}

for row in csv_rows(SOURCE / "accepted_outcome_rows.csv"):
    key = (row["dataset"], row["model"], int(row["layer"]))
    target = main_results if row["variant"] == "main" else stable_results
    target.setdefault(key, float(row["average"]))

for row in csv_rows(LIVE):
    if row["variant"] != "main" or row["status"] != "EVAL_DONE":
        continue
    key = (row["dataset"], row["model"], int(row["layer"]))
    main_results.setdefault(key, float(row["average"]))

current_dataset: str | None = None
in_detailed_results = False
for line in manual_lines:
    if line == "### 4.0 服务器结构化结果总表":
        in_detailed_results = True
        continue
    if line == "### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B":
        break
    if not in_detailed_results:
        continue
    if line == "#### EVQA-pilot500":
        current_dataset = "evqa-pilot500"
        continue
    if line == "#### MMKE-visual":
        current_dataset = "mmke-visual"
        continue
    if line == "#### MMKE-entity":
        current_dataset = "mmke-entity"
        continue
    if current_dataset is None or not line.startswith("|"):
        continue
    columns = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(columns) != 13 or columns[0] not in MODEL_FROM_MANUAL:
        continue
    model = MODEL_FROM_MANUAL[columns[0]]
    layer = int(columns[1].removeprefix("L"))
    status = columns[12]
    key = (current_dataset, model, layer)
    if "FAILED" in status or "NO_EVAL" in status or columns[11] == "-":
        continue
    average = float(columns[11])
    if "STABLE" in status:
        stable_results.setdefault(key, average)
    else:
        main_results.setdefault(key, average)


def completion_parts(dataset: str, model: str, union: list[int]) -> dict[str, list[int]]:
    main = [layer for layer in union if (dataset, model, layer) in main_results]
    stable_only = [
        layer
        for layer in union
        if (dataset, model, layer) not in main_results
        and (dataset, model, layer) in stable_results
    ]
    failed = [
        layer
        for layer in union
        if (dataset, model, layer) in KNOWN_FAILURES
        and layer not in main
        and layer not in stable_only
    ]
    pending = [
        layer
        for layer in union
        if layer not in main and layer not in stable_only and layer not in failed
    ]
    return {"main": main, "stable_only": stable_only, "failed": failed, "pending": pending}


def fmt_completed(parts: dict[str, list[int]]) -> str:
    chunks: list[str] = []
    if parts["main"]:
        chunks.append("主:" + fmt_layers(parts["main"]))
    if parts["stable_only"]:
        chunks.append("stable-only:" + fmt_layers(parts["stable_only"]))
    return "；".join(chunks) if chunks else "-"


union_rows: list[dict[str, object]] = []
for dataset in DATASETS:
    for model in MODELS:
        union3 = ordered_union(
            [list(candidates[(dataset, model, method)]["top3"]) for method in METHODS]
        )
        union5 = ordered_union(
            [list(candidates[(dataset, model, method)]["top5"]) for method in METHODS]
        )
        if not set(union3).issubset(union5):
            raise RuntimeError(f"Top-3 is not a subset of Top-5 for {(dataset, model)}")
        parts3 = completion_parts(dataset, model, union3)
        parts5 = completion_parts(dataset, model, union5)
        union_rows.append(
            {
                "version": VERSION,
                "dataset": DISPLAY_DATASET[dataset],
                "model": DISPLAY_MODEL[model],
                "top3_union": fmt_layers(union3),
                "top3_count": len(union3),
                "top3_done": fmt_completed(parts3),
                "top3_done_count": len(parts3["main"]) + len(parts3["stable_only"]),
                "top3_failed": fmt_layers(parts3["failed"]),
                "top3_failed_count": len(parts3["failed"]),
                "top3_pending": fmt_layers(parts3["pending"]),
                "top3_pending_count": len(parts3["pending"]),
                "top5_union": fmt_layers(union5),
                "top5_count": len(union5),
                "top5_done": fmt_completed(parts5),
                "top5_done_count": len(parts5["main"]) + len(parts5["stable_only"]),
                "top5_failed": fmt_layers(parts5["failed"]),
                "top5_failed_count": len(parts5["failed"]),
                "top5_pending": fmt_layers(parts5["pending"]),
                "top5_pending_count": len(parts5["pending"]),
            }
        )


def combo_complete(dataset: str, model: str, k: int) -> bool:
    return all(
        all(
            (dataset, model, layer) in main_results
            for layer in candidates[(dataset, model, method)][f"top{k}"]
        )
        for method in METHODS
    )


complete_combos = {
    k: [
        (dataset, model)
        for dataset in DATASETS
        for model in MODELS
        if combo_complete(dataset, model, k)
    ]
    for k in (3, 5)
}


def method_metrics(dataset: str, model: str, method: str, k: int) -> dict[str, object]:
    method_layers = list(candidates[(dataset, model, method)][f"top{k}"])
    method_values = [(layer, main_results[(dataset, model, layer)]) for layer in method_layers]
    union = ordered_union(
        [list(candidates[(dataset, model, name)][f"top{k}"]) for name in METHODS]
    )
    oracle_layer, oracle_value = max(
        ((layer, main_results[(dataset, model, layer)]) for layer in union),
        key=lambda pair: pair[1],
    )
    best_layer, best_value = max(method_values, key=lambda pair: pair[1])
    return {
        "version": VERSION,
        "dataset": DISPLAY_DATASET[dataset],
        "model": DISPLAY_MODEL[model],
        "method": method,
        "topk": k,
        "layers": fmt_layers(method_layers),
        "best_layer": f"L{best_layer}",
        "best": best_value,
        "mean": mean(value for _, value in method_values),
        "oracle_layer": f"L{oracle_layer}",
        "oracle": oracle_value,
        "regret": oracle_value - best_value,
        "hit": int(oracle_layer in method_layers),
    }


fair_rows: list[dict[str, object]] = []
for k in (3, 5):
    for dataset, model in complete_combos[k]:
        for method in METHODS:
            fair_rows.append(method_metrics(dataset, model, method, k))


summary_rows: list[dict[str, object]] = []
for k in (3, 5):
    for method in METHODS:
        rows = [row for row in fair_rows if row["topk"] == k and row["method"] == method]
        summary_rows.append(
            {
                "version": VERSION,
                "topk": k,
                "method": method,
                "complete_combos": len(rows),
                "mean_best": mean(float(row["best"]) for row in rows) if rows else math.nan,
                "mean_mean": mean(float(row["mean"]) for row in rows) if rows else math.nan,
                "mean_regret": mean(float(row["regret"]) for row in rows) if rows else math.nan,
                "hit_rate": mean(float(row["hit"]) for row in rows) if rows else math.nan,
            }
        )


def add_ranks(k: int) -> None:
    rows = [row for row in summary_rows if row["topk"] == k]
    for row in rows:
        row["rank_best"] = 1 + sum(other["mean_best"] > row["mean_best"] + 1e-12 for other in rows)
        row["rank_mean"] = 1 + sum(other["mean_mean"] > row["mean_mean"] + 1e-12 for other in rows)
        row["rank_regret"] = 1 + sum(other["mean_regret"] < row["mean_regret"] - 1e-12 for other in rows)
        row["rank_hit"] = 1 + sum(other["hit_rate"] > row["hit_rate"] + 1e-12 for other in rows)


add_ranks(3)
add_ranks(5)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


write_csv(OUT / "formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv", union_rows)
write_csv(OUT / "formal7_cma_modelpred_v2_method_fair_rows_20260914.csv", fair_rows)
write_csv(OUT / "formal7_cma_modelpred_v2_method_summary_20260914.csv", summary_rows)

report_lines: list[str] = []
report_lines.append("### 3.4.6 正式7方法 + CMA-ModelPred v2并集、完成状态与阶段指标")
report_lines.append("")
report_lines.append(
    "版本标识：`formal7-cma-modelpred-v2-20260914`。本节是追加的新版本，"
    "不删除、不覆盖3.4.5的历史`CMA-Direct v1.3/alt`并集及阶段指标。"
    "除CMA改为2.8.1的`CMA-ModelPred-Direct`外，其余六种方法保持原正式口径："
    "`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、"
    "`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、"
    "`Ours-Direct(M_abscos_x_newn)`。"
)
report_lines.append("")
report_lines.append(
    "完成验收仍要求对应层具有主配置或明确分栏的stable结果、有效selected checkpoint、"
    "独立test/eval完整结果和`eval_full.done`。缺失不记0分；PaliGemma L0不收敛失败单列。"
    "服务器只读复核至2026-09-14 10:59 CST：Job 3178538仍在训练EVQA/LLaVA L0，"
    "Job 3178423仍等待MMKE-entity/LLaVA L22正式评测，二者均未提前计为完成。"
)
report_lines.append("")
report_lines.append("#### 3.4.6.1 CMA-ModelPred v2 Top-3并集与完成状态")
report_lines.append("")
top3_total = sum(int(row["top3_count"]) for row in union_rows)
top3_done = sum(int(row["top3_done_count"]) for row in union_rows)
top3_failed = sum(int(row["top3_failed_count"]) for row in union_rows)
top3_pending = sum(int(row["top3_pending_count"]) for row in union_rows)
report_lines.append(
    f"汇总：21组Top-3并集共{top3_total}项；已完整评测{top3_done}项，"
    f"已知不收敛失败{top3_failed}项，待补{top3_pending}项，满足"
    f"`{top3_done}+{top3_failed}+{top3_pending}={top3_total}`。"
)
report_lines.append("")
report_lines.append(
    "| Dataset | Model | v2 Top-3并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |"
)
report_lines.append("|---|---|---|---:|---|---:|---|---|---:|")
for row in union_rows:
    report_lines.append(
        f"| {row['dataset']} | {row['model']} | {row['top3_union']} | {row['top3_count']} | "
        f"{row['top3_done']} | {row['top3_done_count']} | {row['top3_failed']} | "
        f"{row['top3_pending']} | {row['top3_pending_count']} |"
    )
report_lines.append("")
report_lines.append("#### 3.4.6.2 17个完整可比组合上的七方法Top-3阶段指标")
report_lines.append("")
report_lines.append(
    "完整可比组合仍为17/21：EVQA除PaliGemma和LLaVA外的5组；MMKE-visual除PaliGemma外的6组；"
    "MMKE-entity除LLaVA外的6组。两组PaliGemma L0终止失败不以0分填充；两组LLaVA仍有未评测层。"
)
report_lines.append("")
report_lines.append("| 方法 | Mean Best@3 ↑ | Mean Mean@3 ↑ | Mean Regret@3 ↓ | Hit@3 ↑ |")
report_lines.append("|---|---:|---:|---:|---:|")
top3_summary = sorted(
    (row for row in summary_rows if row["topk"] == 3),
    key=lambda item: float(item["mean_best"]),
    reverse=True,
)
for row in top3_summary:
    report_lines.append(
        f"| {'**' if row['method'] == 'Ours-Direct' else ''}{row['method']}"
        f"{'**' if row['method'] == 'Ours-Direct' else ''} | "
        f"{float(row['mean_best']):.3f}（{row['rank_best']}） | "
        f"{float(row['mean_mean']):.3f}（{row['rank_mean']}） | "
        f"{float(row['mean_regret']):.3f}（{row['rank_regret']}） | "
        f"{float(row['hit_rate']):.1%}（{row['rank_hit']}） |"
    )
report_lines.append("")
report_lines.append(
    "**阶段结论：** 替换为`CMA-ModelPred-Direct`后，Ours-Direct仍在Mean Best@3、"
    "Mean Mean@3、Mean Regret@3和Hit@3四项指标上全部排名第1。"
    "新版CMA相对历史CMA的`68.826 / 65.404 / 4.031 / 23.5%`提升为"
    "`69.899 / 67.369 / 2.958 / 29.4%`，在Best、Mean和Regret上升至第2，"
    "但仍未超过Ours-Direct。"
)
report_lines.append("")
report_lines.append("#### 3.4.6.3 CMA-ModelPred v2 Top-5并集与完成状态")
report_lines.append("")
top5_total = sum(int(row["top5_count"]) for row in union_rows)
top5_done = sum(int(row["top5_done_count"]) for row in union_rows)
top5_failed = sum(int(row["top5_failed_count"]) for row in union_rows)
top5_pending = sum(int(row["top5_pending_count"]) for row in union_rows)
report_lines.append(
    f"汇总：21组Top-5并集共{top5_total}项；已完整评测{top5_done}项，"
    f"已知不收敛失败{top5_failed}项，待补{top5_pending}项，满足"
    f"`{top5_done}+{top5_failed}+{top5_pending}={top5_total}`。"
    "严格只使用主配置完整结果时，目前仅MMKE-entity/PaliGemma达到七方法Top-5完整可比；"
    "因此暂不把单组合Top-5方法均值作为总体结论。"
)
report_lines.append("")
report_lines.append(
    "| Dataset | Model | v2 Top-5并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |"
)
report_lines.append("|---|---|---|---:|---|---:|---|---|---:|")
for row in union_rows:
    report_lines.append(
        f"| {row['dataset']} | {row['model']} | {row['top5_union']} | {row['top5_count']} | "
        f"{row['top5_done']} | {row['top5_done_count']} | {row['top5_failed']} | "
        f"{row['top5_pending']} | {row['top5_pending_count']} |"
    )
report_lines.append("")
report_lines.append("#### 3.4.6.4 版本边界与机器可读结果")
report_lines.append("")
report_lines.append(
    "- 3.4.5及其CSV继续代表历史`CMA-Direct v1.3/alt`版本；本节代表"
    "`CMA-ModelPred-Direct v2`，两版不得混合平均、跨版本取最大值或互相覆盖。"
)
report_lines.append(
    "- v2并集与状态：`outputs/formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv`。"
)
report_lines.append(
    "- v2逐组合方法指标：`outputs/formal7_cma_modelpred_v2_method_fair_rows_20260914.csv`。"
)
report_lines.append(
    "- v2方法汇总：`outputs/formal7_cma_modelpred_v2_method_summary_20260914.csv`。"
)
report_lines.append(
    "- 可复现脚本：`outputs/recalculate_formal7_cma_modelpred_v2_20260914.py`。"
)

(OUT / "formal7_cma_modelpred_v2_report_20260914.md").write_text(
    "\n".join(report_lines) + "\n", encoding="utf-8"
)

# Sensitivity analysis requested after the formal version was frozen: exclude L0
# uniformly, then refill each method's Top-3 from its already frozen Top-5 order.
# This preserves three candidates per method and avoids comparing 2-layer lists with
# 3-layer lists. Stable-only outcomes remain excluded from the main comparison.
l0_excluded_candidates: dict[tuple[str, str, str], list[int]] = {}
for dataset in DATASETS:
    for model in MODELS:
        for method in METHODS:
            filtered = [
                layer
                for layer in candidates[(dataset, model, method)]["top5"]
                if layer != 0
            ][:3]
            if len(filtered) != 3:
                raise RuntimeError(f"Cannot refill L0-excluded Top-3 for {(dataset, model, method)}")
            l0_excluded_candidates[(dataset, model, method)] = filtered


def l0_excluded_combo_complete(dataset: str, model: str) -> bool:
    return all(
        all(
            (dataset, model, layer) in main_results
            for layer in l0_excluded_candidates[(dataset, model, method)]
        )
        for method in METHODS
    )


l0_excluded_complete_combos = [
    (dataset, model)
    for dataset in DATASETS
    for model in MODELS
    if l0_excluded_combo_complete(dataset, model)
]

l0_excluded_fair_rows: list[dict[str, object]] = []
for dataset, model in l0_excluded_complete_combos:
    union = ordered_union(
        [l0_excluded_candidates[(dataset, model, method)] for method in METHODS]
    )
    oracle_layer, oracle_value = max(
        ((layer, main_results[(dataset, model, layer)]) for layer in union),
        key=lambda pair: pair[1],
    )
    for method in METHODS:
        layers = l0_excluded_candidates[(dataset, model, method)]
        values = [(layer, main_results[(dataset, model, layer)]) for layer in layers]
        best_layer, best_value = max(values, key=lambda pair: pair[1])
        l0_excluded_fair_rows.append(
            {
                "version": VERSION + "-l0-excluded-sensitivity",
                "dataset": DISPLAY_DATASET[dataset],
                "model": DISPLAY_MODEL[model],
                "method": method,
                "layers": fmt_layers(layers),
                "best_layer": f"L{best_layer}",
                "best": best_value,
                "mean": mean(value for _, value in values),
                "oracle_layer": f"L{oracle_layer}",
                "oracle": oracle_value,
                "regret": oracle_value - best_value,
                "hit": int(oracle_layer in layers),
            }
        )

l0_excluded_summary: list[dict[str, object]] = []
for method in METHODS:
    rows = [row for row in l0_excluded_fair_rows if row["method"] == method]
    l0_excluded_summary.append(
        {
            "version": VERSION + "-l0-excluded-sensitivity",
            "method": method,
            "complete_combos": len(rows),
            "mean_best": mean(float(row["best"]) for row in rows),
            "mean_mean": mean(float(row["mean"]) for row in rows),
            "mean_regret": mean(float(row["regret"]) for row in rows),
            "hit_rate": mean(float(row["hit"]) for row in rows),
        }
    )

for row in l0_excluded_summary:
    row["rank_best"] = 1 + sum(
        other["mean_best"] > row["mean_best"] + 1e-12
        for other in l0_excluded_summary
    )
    row["rank_mean"] = 1 + sum(
        other["mean_mean"] > row["mean_mean"] + 1e-12
        for other in l0_excluded_summary
    )
    row["rank_regret"] = 1 + sum(
        other["mean_regret"] < row["mean_regret"] - 1e-12
        for other in l0_excluded_summary
    )
    row["rank_hit"] = 1 + sum(
        other["hit_rate"] > row["hit_rate"] + 1e-12
        for other in l0_excluded_summary
    )

write_csv(
    OUT / "formal7_cma_modelpred_v2_l0_excluded_top3_fair_rows_20260914.csv",
    l0_excluded_fair_rows,
)
write_csv(
    OUT / "formal7_cma_modelpred_v2_l0_excluded_top3_summary_20260914.csv",
    l0_excluded_summary,
)

print(f"version={VERSION}")
for k in (3, 5):
    total = sum(int(row[f"top{k}_count"]) for row in union_rows)
    done = sum(int(row[f"top{k}_done_count"]) for row in union_rows)
    failed = sum(int(row[f"top{k}_failed_count"]) for row in union_rows)
    pending = sum(int(row[f"top{k}_pending_count"]) for row in union_rows)
    print(
        f"top{k}: total={total} done={done} failed={failed} pending={pending} "
        f"complete_combos={len(complete_combos[k])}"
    )
print("complete_top3=" + ";".join(f"{d}/{m}" for d, m in complete_combos[3]))
for row in sorted(
    (row for row in summary_rows if row["topk"] == 3),
    key=lambda item: float(item["mean_best"]),
    reverse=True,
):
    print(
        f"top3_summary {row['method']}: best={row['mean_best']:.3f} "
        f"mean={row['mean_mean']:.3f} regret={row['mean_regret']:.3f} "
        f"hit={row['hit_rate']:.4f} ranks={row['rank_best']}/"
        f"{row['rank_mean']}/{row['rank_regret']}/{row['rank_hit']}"
    )
print(
    "l0_excluded_complete_top3="
    + ";".join(f"{dataset}/{model}" for dataset, model in l0_excluded_complete_combos)
)
for row in sorted(
    l0_excluded_summary,
    key=lambda item: float(item["mean_best"]),
    reverse=True,
):
    print(
        f"l0_excluded_summary {row['method']}: best={row['mean_best']:.3f} "
        f"mean={row['mean_mean']:.3f} regret={row['mean_regret']:.3f} "
        f"hit={row['hit_rate']:.4f} ranks={row['rank_best']}/"
        f"{row['rank_mean']}/{row['rank_regret']}/{row['rank_hit']}"
    )
