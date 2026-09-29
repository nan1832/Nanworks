import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "md" / "Location" / "VisualGradient_11formula_analysis_files_20260720" / "analysis_outputs_20260731"
OUT = ROOT / "outputs"

DATASETS = ["evqa-pilot500", "mmke-visual", "mmke-entity"]
MODELS = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "llava-v1.5-7b",
    "minigpt-4-vicuna-7b",
    "paligemma-3b",
    "qwen2.5-vl-3b",
    "smolvlm-1.7b",
]
METHODS = [
    "Middle-Prior-Direct",
    "VisEdit-Contrib-Pre-KeyToken",
    "SaLEM-Alt-Direct",
    "LGA-Param-Direct-AltModelPred",
    "Perturb-KL-Direct-AltSeq",
    "CMA-Direct",
    "Ours-Direct (M_abscos_x_newn)",
]


def read_csv(name):
    with (SOURCE / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_layers(value):
    value = (value or "").strip()
    if not value:
        return []
    if value.startswith("["):
        return [int(item) for item in json.loads(value)]
    return [int(item.strip().lstrip("L")) for item in value.split(",") if item.strip()]


def join_layers(values):
    return ",".join(f"L{item}" for item in values)


accepted = read_csv("accepted_outcome_rows.csv")
measured_main = {
    (row["dataset"], row["model"], int(row["layer"]))
    for row in accepted
    if row["variant"] == "main"
}

# Live server marker cross-check after the accepted-outcome snapshot was generated.
# Job 3117562, verified 2026-08-01 12:13 CST: all three formal markers exist.
measured_main.add(("mmke-visual", "llava-v1.5-7b", 0))

candidate_rows = []
for row in read_csv("baseline_candidates.csv"):
    candidate_rows.append(
        {
            "method": row["method"],
            "dataset": row["dataset"],
            "model": row["model"],
            "top3": parse_layers(row["top3"]),
            "top5": parse_layers(row["top5"]),
            "reliability": row["reliability"],
            "candidate_status": row["status"],
            "formal_candidate_complete": "否" if row["method"] == "VisEdit-Contrib-Pre-KeyToken" and row["dataset"] == "evqa-pilot500" else "是",
        }
    )

for row in read_csv("formula_topk_all_21.csv"):
    if row["formula"] != "M_abscos_x_newn":
        continue
    candidate_rows.append(
        {
            "method": "Ours-Direct (M_abscos_x_newn)",
            "dataset": row["dataset"],
            "model": row["model"],
            "top3": parse_layers(row["top3"]),
            "top5": parse_layers(row["top5"]),
            "reliability": "eligible",
            "candidate_status": f"{row['status']}; valid={row['valid_samples']}/{row['total_samples']}; coverage={float(row['coverage']):.4f}",
            "formal_candidate_complete": "是",
        }
    )

detail_rows = []
for row in candidate_rows:
    key_prefix = (row["dataset"], row["model"])
    done3 = [layer for layer in row["top3"] if (*key_prefix, layer) in measured_main]
    done5 = [layer for layer in row["top5"] if (*key_prefix, layer) in measured_main]
    missing3 = [layer for layer in row["top3"] if layer not in done3]
    missing5 = [layer for layer in row["top5"] if layer not in done5]
    detail_rows.append(
        {
            "method": row["method"],
            "dataset": row["dataset"],
            "model": row["model"],
            "candidate_output": "已生成" if len(row["top3"]) == 3 and len(row["top5"]) == 5 else "不完整",
            "formal_candidate_complete": row["formal_candidate_complete"],
            "reliability": row["reliability"],
            "candidate_status": row["candidate_status"],
            "top3": join_layers(row["top3"]),
            "top3_evaluated": join_layers(done3),
            "top3_missing": join_layers(missing3),
            "top3_evaluated_count": len(done3),
            "top3_complete": "是" if not missing3 else "否",
            "top5": join_layers(row["top5"]),
            "top5_evaluated": join_layers(done5),
            "top5_missing": join_layers(missing5),
            "top5_evaluated_count": len(done5),
            "top5_complete": "是" if not missing5 else "否",
            "evaluation_profile": "main（PaliGemma stable 不并入主统计）",
        }
    )

detail_rows.sort(key=lambda row: (METHODS.index(row["method"]), DATASETS.index(row["dataset"]), MODELS.index(row["model"])))

summary_rows = []
for method in METHODS:
    for scope in ["ALL", *DATASETS]:
        rows = [row for row in detail_rows if row["method"] == method and (scope == "ALL" or row["dataset"] == scope)]
        reliability = Counter(row["reliability"] for row in rows)
        summary_rows.append(
            {
                "method": method,
                "dataset_scope": scope,
                "combo_count": len(rows),
                "candidate_output_complete_combos": sum(row["candidate_output"] == "已生成" for row in rows),
                "formal_candidate_complete_combos": sum(row["formal_candidate_complete"] == "是" for row in rows),
                "eligible_combos": reliability.get("eligible", 0),
                "low_candidate_coverage_combos": reliability.get("low_candidate_coverage", 0),
                "historical_firsttoken_combos": reliability.get("historical_firsttoken_not_strict_keytoken", 0),
                "top3_complete_combos": sum(row["top3_complete"] == "是" for row in rows),
                "top3_completed_layers": sum(int(row["top3_evaluated_count"]) for row in rows),
                "top3_total_layers": 3 * len(rows),
                "top3_remaining_layers": 3 * len(rows) - sum(int(row["top3_evaluated_count"]) for row in rows),
                "top5_complete_combos": sum(row["top5_complete"] == "是" for row in rows),
                "top5_completed_layers": sum(int(row["top5_evaluated_count"]) for row in rows),
                "top5_total_layers": 5 * len(rows),
                "top5_remaining_layers": 5 * len(rows) - sum(int(row["top5_evaluated_count"]) for row in rows),
            }
        )

OUT.mkdir(parents=True, exist_ok=True)
summary_csv = OUT / "7模型3数据集候选层方法完成情况_M_abscos主公式_20260801.csv"
detail_csv = OUT / "7模型3数据集候选层方法逐组合明细_M_abscos主公式_20260801.csv"
model_csv = OUT / "7模型3数据集候选层方法分模型完成情况_M_abscos主公式_20260801.csv"
report_md = OUT / "7模型3数据集候选层方法完成情况_M_abscos主公式_20260801.md"

with summary_csv.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
    writer.writeheader()
    writer.writerows(summary_rows)

with detail_csv.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0]))
    writer.writeheader()
    writer.writerows(detail_rows)

model_rows = []
for method in METHODS:
    for model in MODELS:
        rows = [row for row in detail_rows if row["method"] == method and row["model"] == model]
        reliability = Counter(row["reliability"] for row in rows)
        model_rows.append(
            {
                "method": method,
                "model": model,
                "candidate_output_complete_combos": sum(row["candidate_output"] == "已生成" for row in rows),
                "candidate_combo_total": 3,
                "formal_candidate_complete_combos": sum(row["formal_candidate_complete"] == "是" for row in rows),
                "eligible_combos": reliability.get("eligible", 0),
                "top3_complete_dataset_combos": sum(row["top3_complete"] == "是" for row in rows),
                "top3_dataset_combo_total": 3,
                "top3_completed_layers": sum(int(row["top3_evaluated_count"]) for row in rows),
                "top3_layer_total": 9,
                "top3_remaining_layers": 9 - sum(int(row["top3_evaluated_count"]) for row in rows),
            }
        )

with model_csv.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(model_rows[0]))
    writer.writeheader()
    writer.writerows(model_rows)

global_rows = {row["method"]: row for row in summary_rows if row["dataset_scope"] == "ALL"}
dataset_rows = {(row["method"], row["dataset_scope"]): row for row in summary_rows if row["dataset_scope"] != "ALL"}

formula_summary = next(
    row
    for row in read_csv("formula_global_summary.csv")
    if row["profile"] == "main" and row["formula"] == "M_abscos_x_newn"
)

lines = [
    "# 7模型 × 3数据集候选层方法完成情况",
    "",
    "生成日期：2026-08-01",
    "",
    "> 服务器交叉核验快照：2026-08-01 12:13 CST。Job 3117562 正在运行；MMKE-visual / LLaVA L0 已有 `selected_checkpoint.tsv`、`train.done`、`eval_full.done`，L1 仍在训练且尚无完整评测标记，因此 L1 未计入完成数。",
    "",
    "## 口径与 Ours-Direct 主公式",
    "",
    "- 正式比较的 7 种方法：Middle、VisEdit、SaLEM、LGA、Perturb-KL、CMA、Ours-Direct。`Perturb-KL-Pre` 仅作消融，不列入正式 7 方法。",
    "- Ours-Direct 主公式固定为 `M_abscos_x_newn = |S_v_cos| × S_v_new_norm`，属于 7 个基础视觉梯度公式之一，不使用深度权重。原 4 个深度加权 Ours 指标降为消融/敏感性分析。",
    "- “候选已生成”只表示方法已经给出 Top-3/Top-5；“真实评测完成”要求该候选层已有 main 配置训练结果和独立 test/eval 结果。PaliGemma stable 仅作敏感性分析，不与 main 取最大值。",
    "- 该主公式在 11 个公式的 main 口径中按平均 Spearman 排名第 1；19 个可比较组合中 18 个有相关系数，平均 Spearman 为 " + f"{float(formula_summary['spearman_mean']):.4f}" + "，其中 15/18 为正。",
    "",
    "## 候选计算完成情况",
    "",
    "| 方法 | 候选输出 | 严格方法口径完成 | 可靠/高覆盖 | 当前限制 |",
    "|---|---:|---:|---:|---|",
]

candidate_notes = {
    "Middle-Prior-Direct": "21/21；数据集无关的中层先验",
    "VisEdit-Contrib-Pre-KeyToken": "14/21 严格 KeyToken；EVQA 7/7 仍是历史 FirstToken",
    "SaLEM-Alt-Direct": "21/21",
    "LGA-Param-Direct-AltModelPred": "17/21 可靠；4/21 低候选覆盖",
    "Perturb-KL-Direct-AltSeq": "21/21",
    "CMA-Direct": "8/21 可靠；13/21 低候选覆盖",
    "Ours-Direct (M_abscos_x_newn)": "21/21；主公式已固定",
}

for method in METHODS:
    row = global_rows[method]
    lines.append(
        f"| {method} | {row['candidate_output_complete_combos']}/21 | {row['formal_candidate_complete_combos']}/21 | {row['eligible_combos']}/21 | {candidate_notes[method]} |"
    )

lines.extend(
    [
        "",
        "## Top-3 真实训练与独立评测完成情况",
        "",
        "单元格格式为：完整组合数/7（已评测候选层数/21）。总计列为：完整组合数/21（已评测候选层数/63）。",
        "",
        "| 方法 | EVQA-pilot500 | MMKE-visual | MMKE-entity | 总计 | 尚缺 Top-3 层槽位 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
)

for method in METHODS:
    cells = []
    for dataset in DATASETS:
        row = dataset_rows[(method, dataset)]
        cells.append(f"{row['top3_complete_combos']}/7（{row['top3_completed_layers']}/21）")
    total = global_rows[method]
    lines.append(
        f"| {method} | {cells[0]} | {cells[1]} | {cells[2]} | {total['top3_complete_combos']}/21（{total['top3_completed_layers']}/63） | {total['top3_remaining_layers']} |"
    )

lines.extend(
    [
        "",
        "## Top-3 按模型汇报",
        "",
        "每个模型对应三个数据集，因此“完整评测组合”分母为 3，“已评测候选层”分母为 9。",
        "",
        "| 方法 | 模型 | 候选计算 | Top-3完整评测组合 | 已评测Top-3层 | 尚缺层 |",
        "|---|---|---:|---:|---:|---:|",
    ]
)

for row in model_rows:
    lines.append(
        f"| {row['method']} | {row['model']} | {row['candidate_output_complete_combos']}/3 | {row['top3_complete_dataset_combos']}/3 | {row['top3_completed_layers']}/9 | {row['top3_remaining_layers']} |"
    )

lines.extend(
    [
        "",
        "## Top-5 总体完成情况",
        "",
        "| 方法 | 完整组合 | 已评测候选层 | 尚缺候选层 |",
        "|---|---:|---:|---:|",
    ]
)

for method in METHODS:
    row = global_rows[method]
    lines.append(
        f"| {method} | {row['top5_complete_combos']}/21 | {row['top5_completed_layers']}/105 | {row['top5_remaining_layers']} |"
    )

lines.extend(
    [
        "",
        "## 结论",
        "",
        "1. 七种方法均已有 21 个数据集×模型组合的候选输出，但严格正式口径尚未全部齐：VisEdit 的 EVQA 7 个组合仍需补 KeyToken；LGA 有 4 个、CMA 有 13 个低候选覆盖组合，需要在结论中降置信度或重算。",
        "2. 真实评测尚未覆盖所有方法的全部 Top-3/Top-5。当前完成比例高低主要反映已有扫层是否覆盖该方法候选，并不能直接证明某一方法更优。",
        "3. Ours-Direct 主公式的候选计算已完成 21/21；main 口径 Top-3 已完整评测 9/21 个组合、38/63 个候选层。应优先补其缺失候选层，才能形成 7 模型×3 数据集的完整主结论。",
        "4. 逐组合候选、已评测层和缺失层见配套明细 CSV；它可直接作为补跑清单。",
        "",
        "## 数据来源",
        "",
        "- `baseline_candidates.csv`",
        "- `formula_topk_all_21.csv`",
        "- `formula_global_summary.csv`",
        "- `accepted_outcome_rows.csv`",
    ]
)

report_md.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

print(report_md)
print(summary_csv)
print(detail_csv)
print(model_csv)
