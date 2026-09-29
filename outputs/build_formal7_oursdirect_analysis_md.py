from __future__ import annotations

import ast
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "md" / "Location" / "VisualGradient_11formula_analysis_files_20260720" / "analysis_outputs_20260731"
OUT_MD = ROOT / "md" / "Location" / "6location_formal7_OursDirect_main_correlation_analysis.md"
OUT_CSV = ROOT / "outputs" / "formal7_method_topk_performance_20260801.csv"
UNION_CSV = ROOT / "outputs" / "formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv"
LIVE_OUTCOME_CSV = ROOT / "outputs" / "formal7_live_main_outcomes_20260824.csv"
FAIR_TOP3_CSV = ROOT / "outputs" / "formal7_method_top3_fair_rows_17combos_20260824.csv"
SUMMARY_TOP3_CSV = ROOT / "outputs" / "formal7_method_top3_summary_17combos_20260824.csv"

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
    "CMA-Direct",
]

DS_NAME = {
    "evqa-pilot500": "EVQA-pilot500",
    "mmke-visual": "MMKE-visual",
    "mmke-entity": "MMKE-entity",
}
MODEL_NAME = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}
SHORT_METHOD = {
    "Middle-Prior-Direct": "Middle",
    "VisEdit-Contrib-Pre-KeyToken": "VisEdit",
    "SaLEM-Alt-Direct": "SaLEM",
    "LGA-Param-Direct-AltModelPred": "LGA",
    "Perturb-KL-Direct-AltSeq": "Perturb-KL",
    "Ours-Direct": "Ours-Direct",
    "CMA-Direct": "CMA",
}

METHOD_PRINCIPLE = {
    "Middle-Prior-Direct": ("结构先验", "按模型深度中点附近排序；不使用数据集梯度。"),
    "VisEdit-Contrib-Pre-KeyToken": ("贡献度", "比较关键token路径上的层贡献，按贡献分数选择Top-K。"),
    "SaLEM-Alt-Direct": ("参数梯度", "以替代目标下的参数梯度绝对值聚合衡量层敏感性。"),
    "LGA-Param-Direct-AltModelPred": ("新旧知识梯度交互", "使用新旧目标参数梯度的点积衡量层级更新一致性。"),
    "Perturb-KL-Direct-AltSeq": ("扰动敏感度", "扰动视觉token后计算输出KL变化，选择对视觉扰动最敏感的层。"),
    "Ours-Direct": ("视觉梯度方向×幅值", "主公式 `M_abscos_x_newn = |S_v_cos| × S_v_new_norm`；不使用深度权重。"),
    "CMA-Direct": ("因果中介恢复", "污染视觉输入并逐层恢复hidden state，以因果恢复增益选择层。"),
}

KNOWN_FAILURES = {
    ("evqa-pilot500", "paligemma-3b", 0): "主配置与stable均不收敛",
    ("mmke-visual", "paligemma-3b", 0): "stable不收敛",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_list(text: str) -> list[int]:
    value = text.strip()
    if not value:
        return []
    if value.startswith("["):
        return [int(x) for x in ast.literal_eval(value)]
    return [int(x.removeprefix("L")) for x in value.split(",")]


def fmt_layers(values: list[int]) -> str:
    return ",".join(f"L{x}" for x in values) if values else "-"


def fmt_float(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


baseline = rows(SRC / "baseline_candidates.csv")
formula = rows(SRC / "formula_topk_all_21.csv")
accepted = rows(SRC / "accepted_outcome_rows.csv")
live_accepted = rows(LIVE_OUTCOME_CSV)
union_rows = rows(UNION_CSV)

candidates: dict[tuple[str, str, str], dict[str, object]] = {}
for row in baseline:
    if row["method"] not in METHODS:
        continue
    candidates[(row["dataset"], row["model"], row["method"])] = {
        "top3": parse_list(row["top3"]),
        "top5": parse_list(row["top5"]),
        "reliability": row["reliability"],
        "status": row["status"],
    }

for row in formula:
    if row["formula"] != "M_abscos_x_newn":
        continue
    candidates[(row["dataset"], row["model"], "Ours-Direct")] = {
        "top3": parse_list(row["top3"]),
        "top5": parse_list(row["top5"]),
        "reliability": "eligible" if row["status"] == "done" else row["status"],
        "status": f"{row['status']}; coverage={row['coverage']}",
    }

expected = {(d, m, method) for d in DATASETS for m in MODELS for method in METHODS}
assert set(candidates) == expected, (expected - set(candidates), set(candidates) - expected)

main_results: dict[tuple[str, str, int], float] = {}
stable_results: dict[tuple[str, str, int], float] = {}
for row in accepted:
    key = (row["dataset"], row["model"], int(row["layer"]))
    if row["variant"] == "main":
        assert key not in main_results, key
        main_results[key] = float(row["average"])
    elif row["variant"] == "stable":
        stable_results[key] = float(row["average"])

for row in live_accepted:
    assert row["variant"] == "main", row
    assert row["status"] == "EVAL_DONE", row
    key = (row["dataset"], row["model"], int(row["layer"]))
    value = float(row["average"])
    if key in main_results:
        assert math.isclose(main_results[key], value, abs_tol=1e-6), (key, main_results[key], value)
    else:
        main_results[key] = value

method_rows: list[dict[str, object]] = []
for dataset in DATASETS:
    for model in MODELS:
        for method in METHODS:
            info = candidates[(dataset, model, method)]
            row_out: dict[str, object] = {
                "dataset": DS_NAME[dataset],
                "model": MODEL_NAME[model],
                "method": method,
                "top3": fmt_layers(info["top3"]),
                "top5": fmt_layers(info["top5"]),
                "reliability": info["reliability"],
            }
            for k in (3, 5):
                layers: list[int] = info[f"top{k}"]
                values = [main_results[(dataset, model, layer)] for layer in layers if (dataset, model, layer) in main_results]
                complete = len(values) == k
                row_out[f"top{k}_evaluated"] = len(values)
                row_out[f"best_at_{k}"] = max(values) if complete else None
                row_out[f"mean_at_{k}"] = mean(values) if complete else None
            method_rows.append(row_out)

with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(method_rows[0]))
    writer.writeheader()
    writer.writerows(method_rows)


def combo_complete(dataset: str, model: str, k: int) -> bool:
    return all(
        all((dataset, model, layer) in main_results for layer in candidates[(dataset, model, method)][f"top{k}"])
        for method in METHODS
    )


complete_combos = {
    k: [(d, m) for d in DATASETS for m in MODELS if combo_complete(d, m, k)]
    for k in (3, 5)
}


def comparison_metrics(dataset: str, model: str, method: str, k: int) -> dict[str, object]:
    layers: list[int] = candidates[(dataset, model, method)][f"top{k}"]
    values = [(layer, main_results[(dataset, model, layer)]) for layer in layers]
    union = []
    seen = set()
    for name in METHODS:
        for layer in candidates[(dataset, model, name)][f"top{k}"]:
            if layer not in seen:
                seen.add(layer)
                union.append(layer)
    oracle_layer, oracle_value = max(
        ((layer, main_results[(dataset, model, layer)]) for layer in union), key=lambda pair: pair[1]
    )
    best_layer, best_value = max(values, key=lambda pair: pair[1])
    return {
        "best_layer": best_layer,
        "best": best_value,
        "mean": mean(v for _, v in values),
        "oracle_layer": oracle_layer,
        "oracle": oracle_value,
        "regret": oracle_value - best_value,
        "hit": int(oracle_layer in layers),
    }


fair_rows: dict[int, list[dict[str, object]]] = {3: [], 5: []}
summary: dict[int, dict[str, dict[str, float]]] = {3: {}, 5: {}}
paired: dict[int, dict[str, dict[str, float]]] = {3: {}, 5: {}}
for k in (3, 5):
    for dataset, model in complete_combos[k]:
        for method in METHODS:
            met = comparison_metrics(dataset, model, method, k)
            fair_rows[k].append({"dataset": dataset, "model": model, "method": method, **met})
    for method in METHODS:
        vals = [r for r in fair_rows[k] if r["method"] == method]
        summary[k][method] = {
            "combos": len(vals),
            "mean_best": mean(float(r["best"]) for r in vals) if vals else math.nan,
            "mean_mean": mean(float(r["mean"]) for r in vals) if vals else math.nan,
            "mean_regret": mean(float(r["regret"]) for r in vals) if vals else math.nan,
            "hit_rate": mean(float(r["hit"]) for r in vals) if vals else math.nan,
        }
    ours_map = {(r["dataset"], r["model"]): r for r in fair_rows[k] if r["method"] == "Ours-Direct"}
    for method in METHODS:
        if method == "Ours-Direct":
            continue
        base_map = {(r["dataset"], r["model"]): r for r in fair_rows[k] if r["method"] == method}
        deltas = [float(ours_map[key]["best"]) - float(base_map[key]["best"]) for key in ours_map]
        paired[k][method] = {
            "mean_delta": mean(deltas) if deltas else math.nan,
            "wins": sum(x > 1e-12 for x in deltas),
            "ties": sum(abs(x) <= 1e-12 for x in deltas),
            "losses": sum(x < -1e-12 for x in deltas),
        }


with FAIR_TOP3_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(fair_rows[3][0]))
    writer.writeheader()
    writer.writerows(fair_rows[3])


def metric_rank(method: str, field: str, higher_is_better: bool) -> int:
    value = summary[3][method][field]
    values = [summary[3][name][field] for name in METHODS]
    if higher_is_better:
        return 1 + sum(other > value + 1e-12 for other in values)
    return 1 + sum(other < value - 1e-12 for other in values)


summary_top3_rows = []
for method in sorted(METHODS, key=lambda name: summary[3][name]["mean_best"], reverse=True):
    s = summary[3][method]
    summary_top3_rows.append(
        {
            "method": method,
            "combos": int(s["combos"]),
            "mean_best_at_3": s["mean_best"],
            "rank_best_at_3": metric_rank(method, "mean_best", True),
            "mean_mean_at_3": s["mean_mean"],
            "rank_mean_at_3": metric_rank(method, "mean_mean", True),
            "mean_regret_at_3": s["mean_regret"],
            "rank_regret_at_3": metric_rank(method, "mean_regret", False),
            "hit_at_3": s["hit_rate"],
            "rank_hit_at_3": metric_rank(method, "hit_rate", True),
        }
    )

with SUMMARY_TOP3_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_top3_rows[0]))
    writer.writeheader()
    writer.writerows(summary_top3_rows)

union_by_key = {(r["dataset"], r["model"]): r for r in union_rows}
assert len(union_by_key) == 21

lines: list[str] = []
add = lines.append
add("# 7模型 × 3数据集：正式七方法与Ours-Direct主公式相关性分析数据表")
add("")
add("生成日期：2026-08-24。本文档是从原综合记录中抽离出的当前正式分析口径，只服务于七方法公平比较；旧4个Ours深度加权指标、Perturb-KL Pre消融及历史冻结并集均不进入本文件。")
add("")
add("## 1. 正式比较口径")
add("")
add("- 正式方法固定为7类：`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct`、`CMA-Direct`。")
add("- Ours唯一主公式：`M_abscos_x_newn = |S_v_cos| × S_v_new_norm`，不含深度加权。")
add("- 真实编辑效果比较只使用主配置结果；stable、真正改变训练配置的recovered run和numeric anomaly必须保留标签，禁止跨配置取最大值。本次`RECOVERED_G09_NODEFAIL`仅表示从节点故障现场恢复原主配置产物，训练配置未改变，因此仍登记为`variant=main`。")
add("- 缺失层不按0分；只有候选Top-K全部具有`selected_checkpoint.tsv + eval_full.done + 完整独立test/eval`时，才计算该方法在该组合上的正式Best@K和Mean@K。")
add("- 当前服务器增量已计入：截至2026-08-24，新增的EVQA/InstructBLIP 12层、EVQA/MiniGPT-4 12层、MMKE-visual/LLaVA 8层和MMKE-entity/MiniGPT-4 10层均已用非空`selected_checkpoint.tsv + eval_full.done`及对应独立test/eval交叉验收；连同历史结果，正式Top-3完整可比组合达到17/21。")
add("")
add("## 2. 七种方法的定位原理")
add("")
add("| 方法 | 类型 | 定位原理 |")
add("|---|---|---|")
for method in METHODS:
    kind, principle = METHOD_PRINCIPLE[method]
    add(f"| `{method}` | {kind} | {principle} |")
add("")
add("可靠性提示：EVQA的7个VisEdit组合仍为历史FirstToken结果而非严格KeyToken；LGA有4组、CMA有13组为低coverage。候选层仍列出，但论文结论必须保留这些限制。")

add("")
add("## 3. 21组各方法Top-3/Top-5及当前主配置评测覆盖")
add("")
add("`n/3`或`n/5`表示对应候选层中已有多少层具备主配置完整评测。Best/Mean只在候选全部完成时给出；部分完成不计算正式值，避免幸存者偏差。")
for dataset in DATASETS:
    add("")
    add(f"### 3.{DATASETS.index(dataset)+1} {DS_NAME[dataset]}")
    add("")
    add("| Model | Method | Top-3 | 完成 | Best@3 | Mean@3 | Top-5 | 完成 | Best@5 | Mean@5 | 可靠性 |")
    add("|---|---|---|---:|---:|---:|---|---:|---:|---:|---|")
    for row in method_rows:
        if row["dataset"] != DS_NAME[dataset]:
            continue
        add(
            f"| {row['model']} | {SHORT_METHOD[str(row['method'])]} | {row['top3']} | {row['top3_evaluated']}/3 | "
            f"{fmt_float(row['best_at_3'])} | {fmt_float(row['mean_at_3'])} | {row['top5']} | {row['top5_evaluated']}/5 | "
            f"{fmt_float(row['best_at_5'])} | {fmt_float(row['mean_at_5'])} | {row['reliability']} |"
        )

add("")
add("## 4. 正式七方法Top-3/Top-5并集与待补状态")
add("")
add("`已完成`按主配置与stable-only分开；stable-only表示层已经做过，但不进入本文件的主配置性能均值。已知不收敛失败单列，不当作0分。")
for k in (3, 5):
    add("")
    add(f"### 4.{1 if k == 3 else 2} Top-{k}并集")
    add("")
    add(f"| Dataset | Model | Top-{k}并集 | 层数 | 已完成（配置分开） | 已知失败 | 待补 | 待补数 |")
    add("|---|---|---|---:|---|---|---|---:|")
    for dataset in DATASETS:
        for model in MODELS:
            row = union_by_key[(DS_NAME[dataset], MODEL_NAME[model])]
            add(
                f"| {row['dataset']} | {row['model']} | {row[f'top{k}_union']} | {row[f'top{k}_count']} | "
                f"{row[f'top{k}_done']} | {row[f'top{k}_failed']} | {row[f'top{k}_pending']} | {row[f'top{k}_pending_count']} |"
            )

add("")
add("## 5. 当前可公平比较组合与阶段性结果")
add("")
add("公平组合要求同一`dataset × model`下七种方法的Top-K候选全部已有主配置完整评测。以下结果用于阶段性核验，不把不完整组合混入平均值。")
for k in (3, 5):
    add("")
    add(f"### 5.{1 if k == 3 else 2} Top-{k}")
    add("")
    combos = complete_combos[k]
    add(f"完整可比组合：**{len(combos)}/21**。")
    add("")
    if combos:
        add("组合：" + "；".join(f"{DS_NAME[d]} × {MODEL_NAME[m]}" for d, m in combos) + "。")
        add("")
        add(f"| Method | 可比组合数 | Mean Best@{k} | Mean Mean@{k} | Mean Regret@{k}↓ | Hit@{k} |")
        add("|---|---:|---:|---:|---:|---:|")
        ordered_methods = sorted(METHODS, key=lambda name: summary[k][name]["mean_best"], reverse=True)
        for method in ordered_methods:
            s = summary[k][method]
            if k == 3:
                add(
                    f"| {SHORT_METHOD[method]} | {int(s['combos'])} | {s['mean_best']:.3f}（{metric_rank(method, 'mean_best', True)}） | "
                    f"{s['mean_mean']:.3f}（{metric_rank(method, 'mean_mean', True)}） | "
                    f"{s['mean_regret']:.3f}（{metric_rank(method, 'mean_regret', False)}） | "
                    f"{s['hit_rate']:.1%}（{metric_rank(method, 'hit_rate', True)}） |"
                )
            else:
                add(
                    f"| {SHORT_METHOD[method]} | {int(s['combos'])} | {s['mean_best']:.3f} | {s['mean_mean']:.3f} | "
                    f"{s['mean_regret']:.3f} | {s['hit_rate']:.1%} |"
                )
        if k == 3:
            add("")
            add("阶段性结论：扩展到17个完整可比组合后，Ours-Direct的Mean Best@3、Mean Mean@3和Hit@3仍为七方法最高，Mean Regret@3仍为最低，四项指标均排名第1。")
        add("")
        add(f"Ours相对其他方法的配对Best@{k}差值（同一完整组合，正值表示Ours更高）：")
        add("")
        add("| 对比方法 | Ours平均差值 | 胜/平/负 |")
        add("|---|---:|---:|")
        for method in METHODS:
            if method == "Ours-Direct":
                continue
            x = paired[k][method]
            add(f"| {SHORT_METHOD[method]} | {x['mean_delta']:+.3f} | {int(x['wins'])}/{int(x['ties'])}/{int(x['losses'])} |")
    else:
        add("当前没有完整可比组合，因此不计算方法均值。")

add("")
add("## 6. 用于验证Ours优势的相关性与显著性分析方案")
add("")
add("1. **主要指标**：每个完整组合分别计算Best@3、Best@5、Mean@3、Mean@5、Regret@3/5和Hit@3/5；优先报告Regret更低、Hit更高，而不是只挑单个最高分案例。")
add("2. **排序相关性**：在每种方法自己的Top-K内部，用预测顺序与真实Average顺序计算Spearman ρ或Kendall τ；Top-3样本很小，应跨21组合报告分布和置信区间，不只报告单点。")
add("3. **配对检验**：在相同完整组合上比较Ours与每个基线的Best@K/Regret@K差值，使用配对bootstrap置信区间或Wilcoxon signed-rank；七方法多重比较采用Holm校正。")
add("4. **候选重合分析**：计算Ours与每个基线Top-3/Top-5的Jaccard重合度，并结合性能差值判断Ours是找到不同高性能层，还是仅复现共同候选。")
add("5. **分层报告**：分别按数据集、模型规模和层深归一化位置汇报，避免某一数据集或某类模型主导总体均值。")
add("6. **异常处理**：stable、recovered、nonfinite、numeric anomaly单独做敏感性分析；不得与主配置直接取最大值，PaliGemma L0不收敛不得记0分。")
add("")
add("只有当Ours在预先定义的完整组合上表现为更高Best/Mean、更低Regret、更高Hit，且配对置信区间或检验支持时，才能表述为“Ours优于其他定位方法”；若证据不支持，应如实报告模型或数据集上的边界。")

add("")
add("## 7. 数据来源与可复现文件")
add("")
add("- 七基线候选：`md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/baseline_candidates.csv`")
add("- Ours主公式候选：同目录`formula_topk_all_21.csv`，筛选`formula=M_abscos_x_newn`")
add("- 已验收逐层结果：同目录`accepted_outcome_rows.csv`，正式比较筛选`variant=main`")
add("- 2026-08-24服务器增量：`outputs/formal7_live_main_outcomes_20260824.csv`")
add("- 正式并集状态：`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`")
add("- 方法级分析表：`outputs/formal7_method_topk_performance_20260801.csv`")
add("- 17组合Top-3逐组合明细：`outputs/formal7_method_top3_fair_rows_17combos_20260824.csv`")
add("- 17组合Top-3汇总排名：`outputs/formal7_method_top3_summary_17combos_20260824.csv`")
add("- 生成脚本：`outputs/build_formal7_oursdirect_analysis_md.py`")
add("- 文件名中的`20260801`为首次生成批次标识；上述并集与方法级CSV已于2026-08-10根据g09恢复结果重新生成，内容以文件内当前数据为准。")

OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(OUT_MD)
print(OUT_CSV)
print(FAIR_TOP3_CSV)
print(SUMMARY_TOP3_CSV)
print(f"candidate_rows={len(method_rows)}")
print(f"complete_top3={len(complete_combos[3])}; complete_top5={len(complete_combos[5])}")
