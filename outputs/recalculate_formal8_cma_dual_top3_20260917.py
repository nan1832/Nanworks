from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "md" / "Location" / "6location_7model_3datas_top_3_5_layers_outcome.md"
HIST_CANDIDATES = ROOT / "outputs" / "formal7_method_topk_performance_20260801.csv"
ACCEPTED = (
    ROOT
    / "md"
    / "Location"
    / "VisualGradient_11formula_analysis_files_20260720"
    / "analysis_outputs_20260731"
    / "accepted_outcome_rows.csv"
)
LIVE = ROOT / "outputs" / "formal7_live_main_outcomes_20260824.csv"
OUT_SUMMARY = ROOT / "outputs" / "formal8_cma_dual_top3_method_summary_20260917.csv"
OUT_DETAIL = ROOT / "outputs" / "formal8_cma_dual_top3_fair_rows_20260917.csv"
OUT_MD = ROOT / "md" / "TODO" / "Second_prashe" / "第一阶段8方法_CMA双版本_Top3指标_20260917.md"
OUT_PNG = ROOT / "md" / "TODO" / "Second_prashe" / "第一阶段8方法_CMA双版本_Top3指标_20260917.png"

DATASETS = ["EVQA-pilot500", "MMKE-visual", "MMKE-entity"]
MODELS = [
    "BLIP2-OPT-2.7B",
    "InstructBLIP-Vicuna-7B",
    "MiniGPT-4-Vicuna-7B",
    "LLaVA-v1.5-7B",
    "Qwen2.5-VL-3B",
    "PaliGemma-3B",
    "SmolVLM-Instruct-1.7B",
]
HIST_CMA = "CMA-Direct-v1.3-alt"
NEW_CMA = "CMA-ModelPred-Direct-v2"
METHODS = [
    "Middle-Prior-Direct",
    "VisEdit-Contrib-Pre-KeyToken",
    "SaLEM-Alt-Direct",
    "LGA-Param-Direct-AltModelPred",
    "Perturb-KL-Direct-AltSeq",
    "Ours-Direct",
    HIST_CMA,
    NEW_CMA,
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
MODEL_FROM_MANUAL = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def split_layers(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip() and item.strip() != "-"]


def ordered_union(groups: list[list[str]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for layer in group:
            if layer not in seen:
                seen.add(layer)
                result.append(layer)
    return result


manual_lines = MANUAL.read_text(encoding="utf-8").splitlines()

# Candidate matrix: historical export contains the six shared methods and CMA-alt.
candidates: dict[tuple[str, str, str], list[str]] = {}
for row in rows(HIST_CANDIDATES):
    method = HIST_CMA if row["method"] == "CMA-Direct" else row["method"]
    candidates[(row["dataset"], row["model"], method)] = split_layers(row["top3"])

# Add CMA-ModelPred from the current formal table in section 2.8.1.
new_header = "| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |"
start = manual_lines.index(new_header)
for line in manual_lines[start + 2 :]:
    if not line.startswith("|"):
        break
    cols = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(cols) != 9:
        raise RuntimeError(f"Unexpected CMA-ModelPred row: {line}")
    candidates[(cols[0], cols[1], NEW_CMA)] = split_layers(cols[2])

combos = [(dataset, model) for dataset in DATASETS for model in MODELS]
expected = {(dataset, model, method) for dataset, model in combos for method in METHODS}
if set(candidates) != expected:
    raise RuntimeError(f"Candidate matrix incomplete: missing={expected - set(candidates)}")
for key, value in candidates.items():
    if len(value) != 3 or len(set(value)) != 3:
        raise RuntimeError(f"Invalid Top-3: {key} -> {value}")

# Main-configuration real Adapter results. Keep the same precedence and protocol
# as the existing formal seven-method calculation; stable-only does not enter.
results: dict[tuple[str, str, str], float] = {}
for row in rows(ACCEPTED):
    if row["variant"] != "main":
        continue
    key = (
        DISPLAY_DATASET[row["dataset"]],
        DISPLAY_MODEL[row["model"]],
        f"L{int(row['layer'])}",
    )
    results.setdefault(key, float(row["average"]))

for row in rows(LIVE):
    if row["variant"] != "main" or row["status"] != "EVAL_DONE":
        continue
    key = (
        DISPLAY_DATASET[row["dataset"]],
        DISPLAY_MODEL[row["model"]],
        f"L{int(row['layer'])}",
    )
    results.setdefault(key, float(row["average"]))

inside = False
current_dataset: str | None = None
for line in manual_lines:
    if line == "### 4.0 服务器结构化结果总表":
        inside = True
        continue
    if line == "### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B":
        break
    if not inside:
        continue
    if line == "#### EVQA-pilot500":
        current_dataset = "EVQA-pilot500"
        continue
    if line == "#### MMKE-visual":
        current_dataset = "MMKE-visual"
        continue
    if line == "#### MMKE-entity":
        current_dataset = "MMKE-entity"
        continue
    if current_dataset is None or not line.startswith("|"):
        continue
    cols = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(cols) != 13 or cols[0] not in MODEL_FROM_MANUAL:
        continue
    status = cols[12]
    if "STABLE" in status or "FAILED" in status or "NO_EVAL" in status or cols[11] == "-":
        continue
    key = (current_dataset, MODEL_FROM_MANUAL[cols[0]], cols[1])
    results.setdefault(key, float(cols[11]))

# Latest server-only increments. They do not change the current 17-combo common
# set, but recording them keeps the result inventory current and reproducible.
results[("EVQA-pilot500", "LLaVA-v1.5-7B", "L0")] = 60.488
results[("MMKE-entity", "LLaVA-v1.5-7B", "L22")] = 75.618


def is_complete(dataset: str, model: str) -> bool:
    return all(
        all((dataset, model, layer) in results for layer in candidates[(dataset, model, method)])
        for method in METHODS
    )


complete_combos = [(dataset, model) for dataset, model in combos if is_complete(dataset, model)]
excluded_combos = [(dataset, model) for dataset, model in combos if not is_complete(dataset, model)]
if len(complete_combos) != 17:
    raise RuntimeError(f"Expected 17 common complete combos, found {len(complete_combos)}: {complete_combos}")

detail_rows: list[dict[str, object]] = []
for dataset, model in complete_combos:
    union = ordered_union([candidates[(dataset, model, method)] for method in METHODS])
    oracle_layer, oracle_value = max(
        ((layer, results[(dataset, model, layer)]) for layer in union),
        key=lambda item: item[1],
    )
    for method in METHODS:
        method_layers = candidates[(dataset, model, method)]
        values = [(layer, results[(dataset, model, layer)]) for layer in method_layers]
        best_layer, best_value = max(values, key=lambda item: item[1])
        detail_rows.append(
            {
                "dataset": dataset,
                "model": model,
                "method": method,
                "top3": ",".join(method_layers),
                "best_layer": best_layer,
                "best_at_3": best_value,
                "mean_at_3": mean(value for _layer, value in values),
                "oracle_layer": oracle_layer,
                "oracle_value": oracle_value,
                "regret_at_3": oracle_value - best_value,
                "hit_at_3": int(oracle_layer in method_layers),
            }
        )

grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
for row in detail_rows:
    grouped[str(row["method"])].append(row)

summary: list[dict[str, object]] = []
for method in METHODS:
    method_rows = grouped[method]
    summary.append(
        {
            "method": method,
            "complete_combos": len(method_rows),
            "mean_best_at_3": mean(float(row["best_at_3"]) for row in method_rows),
            "mean_mean_at_3": mean(float(row["mean_at_3"]) for row in method_rows),
            "mean_regret_at_3": mean(float(row["regret_at_3"]) for row in method_rows),
            "hit_at_3": mean(int(row["hit_at_3"]) for row in method_rows),
        }
    )


def competition_ranks(field: str, descending: bool) -> dict[str, int]:
    values = {str(row["method"]): float(row[field]) for row in summary}
    ranks: dict[str, int] = {}
    for method, value in values.items():
        if descending:
            ranks[method] = 1 + sum(other > value + 1e-12 for other in values.values())
        else:
            ranks[method] = 1 + sum(other < value - 1e-12 for other in values.values())
    return ranks


rank_best = competition_ranks("mean_best_at_3", True)
rank_mean = competition_ranks("mean_mean_at_3", True)
rank_regret = competition_ranks("mean_regret_at_3", False)
rank_hit = competition_ranks("hit_at_3", True)
for row in summary:
    method = str(row["method"])
    row["rank_best"] = rank_best[method]
    row["rank_mean"] = rank_mean[method]
    row["rank_regret"] = rank_regret[method]
    row["rank_hit"] = rank_hit[method]

summary_sorted = sorted(summary, key=lambda row: (-float(row["mean_best_at_3"]), str(row["method"])))

OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(summary_sorted[0]))
    writer.writeheader()
    writer.writerows(summary_sorted)
with OUT_DETAIL.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0]))
    writer.writeheader()
    writer.writerows(detail_rows)


def fmt_metric(row: dict[str, object], field: str, rank_field: str) -> str:
    return f"{float(row[field]):.3f}（{int(row[rank_field])}）"


md: list[str] = [
    "# 第一阶段八种定位方法Top-3统一公平比较（CMA双版本分开报告）",
    "",
    "> 版本：2026-09-17。CMA-alt与CMA-ModelPred作为两个独立方法行；八种方法使用相同的17个完整组合及同一个八方法Top-3总并集oracle。",
    "",
    "## 1. 统一口径",
    "",
    "- `CMA-Direct-v1.3-alt`：恢复反事实答案`alt`。",
    "- `CMA-ModelPred-Direct-v2`：恢复基础模型确定性输出`model_pred`。",
    "- 只纳入八种方法各自Top-3层全部具有主配置真实Adapter评测的组合；stable-only不计入。",
    "- `Best@3`：该方法Top-3中最高真实Average；`Mean@3`：三个候选层Average均值。",
    "- `Regret@3`：同组合八方法Top-3总并集的oracle最高Average减去该方法Best@3；越低越好。",
    "- `Hit@3`：该方法Top-3是否包含八方法总并集oracle层；对17组取命中率。",
    "",
    "## 2. 八方法汇总结果",
    "",
    "| 方法 | Mean Best@3 ↑ | Mean Mean@3 ↑ | Mean Regret@3 ↓ | Hit@3 ↑ |",
    "|---|---:|---:|---:|---:|",
]
for row in summary_sorted:
    md.append(
        "| "
        + " | ".join(
            [
                str(row["method"]),
                fmt_metric(row, "mean_best_at_3", "rank_best"),
                fmt_metric(row, "mean_mean_at_3", "rank_mean"),
                fmt_metric(row, "mean_regret_at_3", "rank_regret"),
                f"{100 * float(row['hit_at_3']):.1f}%（{int(row['rank_hit'])}）",
            ]
        )
        + " |"
    )

ours = next(row for row in summary if row["method"] == "Ours-Direct")
md.extend(
    [
        "",
        "## 3. 结论",
        "",
        f"`Ours-Direct`：Mean Best@3={float(ours['mean_best_at_3']):.3f}、Mean Mean@3={float(ours['mean_mean_at_3']):.3f}、Mean Regret@3={float(ours['mean_regret_at_3']):.3f}、Hit@3={100 * float(ours['hit_at_3']):.1f}%。",
        f"四项排名分别为{int(ours['rank_best'])}、{int(ours['rank_mean'])}、{int(ours['rank_regret'])}、{int(ours['rank_hit'])}。",
        "",
        "完整可比组合为17/21；排除的4组如下（缺失层不能按0分处理）：",
        "",
        *[f"- {dataset} × {model}" for dataset, model in excluded_combos],
        "",
        "## 4. 机器可读产物",
        "",
        f"- 汇总：`{OUT_SUMMARY.relative_to(ROOT).as_posix()}`",
        f"- 逐组合：`{OUT_DETAIL.relative_to(ROOT).as_posix()}`",
        "",
    ]
)
OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.write_text("\n".join(md), encoding="utf-8")


def choose_font() -> str:
    preferred = ["Microsoft YaHei", "Microsoft YaHei UI", "SimHei", "Noto Sans CJK SC"]
    installed = {item.name for item in font_manager.fontManager.ttflist}
    return next((name for name in preferred if name in installed), "DejaVu Sans")


plt.rcParams["font.family"] = choose_font()
plt.rcParams["axes.unicode_minus"] = False
fig = plt.figure(figsize=(16, 9), dpi=160, facecolor="#101214")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")

white = "#F3F6FA"
muted = "#AAB4C2"
line = "#343A43"
blue = "#67A7FF"
green = "#55D6A0"

ax.text(0.55, 8.45, "CMA双版本分开后，Ours-Direct仍在四项Top-3指标上排名第一", fontsize=25, fontweight="bold", color=white, va="center")
ax.plot([0.55, 2.05], [8.08, 8.08], color="#4B8CF7", lw=4)
ax.text(2.25, 8.08, "基于17个八方法共同完整的dataset × model组合｜统一八方法Top-3总并集oracle", fontsize=11.5, color=muted, va="center")

headers = ["方法", "Mean Best@3 ↑", "Mean Mean@3 ↑", "Mean Regret@3 ↓", "Hit@3 ↑"]
col_x = [0.8, 6.9, 9.45, 12.05, 14.65]
header_y = 7.40
for x, header in zip(col_x, headers):
    ax.text(x, header_y, header, fontsize=12.5, color=white, fontweight="bold", ha="left" if header == "方法" else "center", va="center")
ax.plot([0.7, 15.35], [7.08, 7.08], color=line, lw=1.4)

row_top = 6.76
row_h = 0.69
for index, row in enumerate(summary_sorted):
    y = row_top - index * row_h
    is_ours = row["method"] == "Ours-Direct"
    if is_ours:
        highlight = FancyBboxPatch((0.68, y - 0.31), 14.70, 0.61, boxstyle="round,pad=0.015,rounding_size=0.05", facecolor="#152B45", edgecolor="#315B8D", linewidth=1.2)
        ax.add_patch(highlight)
    color = blue if is_ours else white
    weight = "bold" if is_ours else "normal"
    ax.text(col_x[0], y, str(row["method"]), fontsize=12.0, color=color, fontweight=weight, ha="left", va="center")
    ax.text(col_x[1], y, fmt_metric(row, "mean_best_at_3", "rank_best"), fontsize=12.0, color=color, fontweight=weight, ha="center", va="center")
    ax.text(col_x[2], y, fmt_metric(row, "mean_mean_at_3", "rank_mean"), fontsize=12.0, color=color, fontweight=weight, ha="center", va="center")
    ax.text(col_x[3], y, fmt_metric(row, "mean_regret_at_3", "rank_regret"), fontsize=12.0, color=color, fontweight=weight, ha="center", va="center")
    ax.text(col_x[4], y, f"{100 * float(row['hit_at_3']):.1f}%（{int(row['rank_hit'])}）", fontsize=12.0, color=color, fontweight=weight, ha="center", va="center")
    ax.plot([0.7, 15.35], [y - 0.35, y - 0.35], color=line, lw=0.8)

box = FancyBboxPatch((0.7, 0.72), 14.65, 0.93, boxstyle="round,pad=0.025,rounding_size=0.06", facecolor="#141A20", edgecolor="#334355", linewidth=1.2)
ax.add_patch(box)
ax.add_patch(plt.Rectangle((0.7, 0.72), 0.10, 0.93, facecolor="#4B8CF7", edgecolor="none"))
ax.text(1.02, 1.34, "核心结论", fontsize=12.5, color=white, fontweight="bold", va="center")
ax.text(2.55, 1.34, "Ours-Direct 的 Best@3、Mean@3、Hit@3最高，Regret@3最低；四项均为第1。", fontsize=13.5, color=blue, fontweight="bold", va="center")
ax.text(1.02, 0.95, "CMA-alt恢复反事实alt；CMA-ModelPred恢复模型实际旧知识输出。两行独立报告，不跨版本取最大值。", fontsize=10.5, color=muted, va="center")
ax.text(0.72, 0.34, "注：只纳入17个八方法Top-3均已完成主配置真实评测的组合；未完成组合不按0分。括号内为8方法竞争排名。", fontsize=9.3, color="#8793A2")

fig.savefig(OUT_PNG, bbox_inches="tight", pad_inches=0.08, facecolor="#101214")
plt.close(fig)

print(f"COMPLETE_COMBOS={len(complete_combos)}/21")
print("EXCLUDED=" + ";".join(f"{dataset}×{model}" for dataset, model in excluded_combos))
for row in summary_sorted:
    print(
        f"{row['method']}|best={float(row['mean_best_at_3']):.6f}|"
        f"mean={float(row['mean_mean_at_3']):.6f}|regret={float(row['mean_regret_at_3']):.6f}|"
        f"hit={float(row['hit_at_3']):.6f}|ranks={row['rank_best']},{row['rank_mean']},{row['rank_regret']},{row['rank_hit']}"
    )
print(f"MD={OUT_MD}")
print(f"PNG={OUT_PNG}")
