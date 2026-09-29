from __future__ import annotations

import ast
import csv
import re
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "md" / "Location" / "6location_7model_3datas_top_3_5_layers_outcome.md"
HIST_METHODS = ROOT / "outputs" / "formal7_method_topk_performance_20260801.csv"
HIST_UNIONS = ROOT / "outputs" / "formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv"
NEW_UNIONS = ROOT / "outputs" / "formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv"
RAW_SOURCE = (
    ROOT
    / "md"
    / "Location"
    / "VisualGradient_11formula_analysis_files_20260720"
    / "analysis_outputs_20260731"
)
TARGET = ROOT / "md" / "TODO" / "Second_prashe" / "Firstprash_7_location_recommend.md"

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
COMMON_METHODS = [
    "Middle-Prior-Direct",
    "VisEdit-Contrib-Pre-KeyToken",
    "SaLEM-Alt-Direct",
    "LGA-Param-Direct-AltModelPred",
    "Perturb-KL-Direct-AltSeq",
    "Ours-Direct",
]
HIST_CMA = "CMA-Direct-v1.3-alt"
NEW_CMA = "CMA-ModelPred-Direct-v2"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def split_layers(value: str) -> list[str]:
    layers = [item.strip() for item in value.split(",") if item.strip() and item.strip() != "-"]
    for layer in layers:
        if not re.fullmatch(r"L\d+", layer):
            raise ValueError(f"Invalid layer token: {layer!r}")
    return layers


def normalize_raw_layers(value: str) -> str:
    parsed = ast.literal_eval(value)
    return ",".join(f"L{int(layer)}" for layer in parsed)


def ordered_union(groups: list[list[str]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for layer in group:
            if layer not in seen:
                seen.add(layer)
                result.append(layer)
    return result


def parse_manual_table(
    lines: list[str], header: str, expected_columns: int, section_heading: str | None = None
) -> list[list[str]]:
    search_start = 0
    if section_heading is not None:
        try:
            search_start = lines.index(section_heading)
        except ValueError as exc:
            raise RuntimeError(f"Manual section heading not found: {section_heading}") from exc
    try:
        start = lines.index(header, search_start)
    except ValueError as exc:
        raise RuntimeError(f"Manual table header not found: {header}") from exc
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) != expected_columns:
            raise RuntimeError(f"Unexpected manual table row ({len(columns)} columns): {line}")
        rows.append(columns)
    return rows


manual_lines = MANUAL.read_text(encoding="utf-8").splitlines()

# Historical seven-method export: six shared methods plus CMA-alt v1.3.
historical_rows = read_csv(HIST_METHODS)
candidates: dict[tuple[str, str, str], dict[str, str]] = {}
for row in historical_rows:
    method = HIST_CMA if row["method"] == "CMA-Direct" else row["method"]
    candidates[(row["dataset"], row["model"], method)] = {
        "top3": row["top3"],
        "top5": row["top5"],
        "note": row.get("reliability", "") or "-",
    }

# Parse both CMA tables directly from the current manual and require the historical
# CSV to agree exactly with the retained CMA-alt table.
old_header = "| Dataset | Model | Score source | Top-3 | Top-5 | Status |"
old_cma_rows = parse_manual_table(
    manual_lines,
    old_header,
    6,
    "### 2.8 CMA-Direct（历史 v1.3，原结果保留）",
)
if len(old_cma_rows) != 21:
    raise RuntimeError(f"Expected 21 historical CMA rows, found {len(old_cma_rows)}")
for dataset, model, _score, top3, top5, status in old_cma_rows:
    key = (dataset, model, HIST_CMA)
    if key not in candidates:
        raise RuntimeError(f"Historical CMA key missing from CSV: {key}")
    if candidates[key]["top3"] != top3 or candidates[key]["top5"] != top5:
        raise RuntimeError(f"Historical CMA manual/CSV mismatch: {key}")
    candidates[key]["note"] = status

new_header = "| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |"
new_cma_rows = parse_manual_table(manual_lines, new_header, 9)
if len(new_cma_rows) != 21:
    raise RuntimeError(f"Expected 21 CMA-ModelPred rows, found {len(new_cma_rows)}")
for dataset, model, top3, top5, modelpred, cma_valid, coverage, pairs, stability in new_cma_rows:
    candidates[(dataset, model, NEW_CMA)] = {
        "top3": top3,
        "top5": top5,
        "note": (
            f"ModelPred可用={modelpred}；CMA有效={cma_valid}；总体覆盖率={coverage}；"
            f"有效参数对={pairs}；{stability.replace('**', '')}"
        ),
    }

combos = [(dataset, model) for dataset in DATASETS for model in MODELS]
all_methods = COMMON_METHODS + [HIST_CMA, NEW_CMA]
expected = {(dataset, model, method) for dataset, model in combos for method in all_methods}
if set(candidates) != expected:
    raise RuntimeError(
        f"Candidate matrix mismatch; missing={sorted(expected - set(candidates))}; "
        f"extra={sorted(set(candidates) - expected)}"
    )

# Cross-check the six non-CMA methods against the experiment-derived candidate
# exports that were used to build the manual. This catches a stale summary row.
display_dataset = {
    "evqa-pilot500": "EVQA-pilot500",
    "mmke-visual": "MMKE-visual",
    "mmke-entity": "MMKE-entity",
}
display_model = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}
raw_checked = 0
for row in read_csv(RAW_SOURCE / "baseline_candidates.csv"):
    if row["method"] not in COMMON_METHODS[:5]:
        continue
    key = (display_dataset[row["dataset"]], display_model[row["model"]], row["method"])
    current = candidates[key]
    expected_top3 = normalize_raw_layers(row["top3"])
    expected_top5 = normalize_raw_layers(row["top5"])
    if current["top3"] != expected_top3 or current["top5"] != expected_top5:
        raise RuntimeError(f"Baseline candidate source mismatch: {key}")
    raw_checked += 1

for row in read_csv(RAW_SOURCE / "formula_topk_all_21.csv"):
    if row["formula"] != "M_abscos_x_newn":
        continue
    key = (display_dataset[row["dataset"]], display_model[row["model"]], "Ours-Direct")
    current = candidates[key]
    if current["top3"] != row["top3"] or current["top5"] != row["top5"]:
        raise RuntimeError(f"Ours candidate source mismatch: {key}")
    raw_checked += 1
if raw_checked != 126:
    raise RuntimeError(f"Expected 126 raw non-CMA checks, performed {raw_checked}")

# Structural validation for every versioned method row.
for key, row in candidates.items():
    top3 = split_layers(row["top3"])
    top5 = split_layers(row["top5"])
    if len(top3) != 3 or len(set(top3)) != 3:
        raise RuntimeError(f"Top-3 must contain exactly 3 unique layers: {key} -> {top3}")
    if len(top5) != 5 or len(set(top5)) != 5:
        raise RuntimeError(f"Top-5 must contain exactly 5 unique layers: {key} -> {top5}")
    if not set(top3).issubset(top5):
        raise RuntimeError(f"Top-3 is not a subset of Top-5: {key}")

version_methods = {
    "历史 CMA-alt v1.3": COMMON_METHODS + [HIST_CMA],
    "正式 CMA-ModelPred v2": COMMON_METHODS + [NEW_CMA],
}

recomputed_unions: dict[tuple[str, str, str], dict[str, str | int]] = {}
for version, methods in version_methods.items():
    for dataset, model in combos:
        top3 = ordered_union([split_layers(candidates[(dataset, model, method)]["top3"]) for method in methods])
        top5 = ordered_union([split_layers(candidates[(dataset, model, method)]["top5"]) for method in methods])
        if not set(top3).issubset(top5):
            raise RuntimeError(f"Union Top-3 not subset of Top-5: {(version, dataset, model)}")
        recomputed_unions[(version, dataset, model)] = {
            "top3": ",".join(top3),
            "top3_count": len(top3),
            "top5": ",".join(top5),
            "top5_count": len(top5),
        }


def validate_union_export(path: Path, version: str) -> None:
    rows = read_csv(path)
    if len(rows) != 21:
        raise RuntimeError(f"Expected 21 union rows in {path}, found {len(rows)}")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        combo = (row["dataset"], row["model"])
        seen.add(combo)
        computed = recomputed_unions[(version, *combo)]
        checks = {
            "top3_union": computed["top3"],
            "top3_count": str(computed["top3_count"]),
            "top5_union": computed["top5"],
            "top5_count": str(computed["top5_count"]),
        }
        for field, expected_value in checks.items():
            if row[field] != expected_value:
                raise RuntimeError(
                    f"Union export mismatch in {path.name} for {combo}, {field}: "
                    f"export={row[field]!r}, recomputed={expected_value!r}"
                )
    if seen != set(combos):
        raise RuntimeError(f"Union export combo mismatch in {path}: {set(combos) - seen}")


validate_union_export(HIST_UNIONS, "历史 CMA-alt v1.3")
validate_union_export(NEW_UNIONS, "正式 CMA-ModelPred v2")


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]


out: list[str] = []
out.extend(
    [
        "# 第一阶段七种定位方法：21组 Top-3 / Top-5 候选层与两版 CMA 并集",
        "",
        "> 生成日期：2026-09-17。本文是候选层的完整提取表，不以层是否已完成Adapter评测为筛选条件，避免漏掉待补、失败或低覆盖候选。",
        "",
        "## 1. 口径与版本边界",
        "",
        "每套正式比较都只有七种方法：前六种方法固定，第七种CMA按版本二选一。本文同时保留两版CMA，因此展示时共有8个“版本化方法行”，但不得把两版CMA同时并入同一个七方法并集。",
        "",
        "固定的六种方法：",
        "",
        "1. `Middle-Prior-Direct`",
        "2. `VisEdit-Contrib-Pre-KeyToken`",
        "3. `SaLEM-Alt-Direct`",
        "4. `LGA-Param-Direct-AltModelPred`",
        "5. `Perturb-KL-Direct-AltSeq`",
        "6. `Ours-Direct`：只采用正式主公式 `M_abscos_x_newn`",
        "",
        "CMA二选一版本：",
        "",
        "- `CMA-Direct-v1.3-alt`：历史协议，恢复目标为反事实新答案 `alt`；历史低覆盖结果原样保留。",
        "- `CMA-ModelPred-Direct-v2`：当前正式协议，恢复目标为冻结基础模型确定性输出的完整 `model_pred`；用于新版七方法比较。",
        "",
        "禁止跨CMA版本取最大值、拼接候选层或混合计算指标。旧版与新版分别形成一套七方法Top-3/Top-5并集。",
        "",
        "## 2. 数据来源与实验交叉核验",
        "",
        f"- 主手册：`{MANUAL.relative_to(ROOT).as_posix()}`。",
        f"- 历史七方法逐方法表：`{HIST_METHODS.relative_to(ROOT).as_posix()}`，147行 = 7方法 × 21组合。",
        f"- 历史CMA-alt并集：`{HIST_UNIONS.relative_to(ROOT).as_posix()}`。",
        f"- 新版CMA-ModelPred并集：`{NEW_UNIONS.relative_to(ROOT).as_posix()}`。",
        f"- 五种基线与Ours主公式的实验候选源：`{RAW_SOURCE.relative_to(ROOT).as_posix()}/baseline_candidates.csv`、`formula_topk_all_21.csv`。",
        "- CMA-ModelPred服务器实验已于2026-09-12完成21/21组合；本文直接读取主手册2.8.1中由正式实验回填的21行Top-3、Top-5、覆盖率和稳定性。",
        "- 历史CMA候选逐行与主手册2.8历史表核对；两版七方法并集均由逐方法候选重新计算，并与对应机器可读并集CSV逐字段核对。",
        "",
        "## 3. 各方法在21组上的Top-3与Top-5",
        "",
    ]
)

method_titles = OrderedDict(
    [
        ("Middle-Prior-Direct", "3.1 Middle-Prior-Direct"),
        ("VisEdit-Contrib-Pre-KeyToken", "3.2 VisEdit-Contrib-Pre-KeyToken"),
        ("SaLEM-Alt-Direct", "3.3 SaLEM-Alt-Direct"),
        ("LGA-Param-Direct-AltModelPred", "3.4 LGA-Param-Direct-AltModelPred"),
        ("Perturb-KL-Direct-AltSeq", "3.5 Perturb-KL-Direct-AltSeq"),
        ("Ours-Direct", "3.6 Ours-Direct（M_abscos_x_newn）"),
        (HIST_CMA, "3.7 CMA-Direct v1.3（历史alt目标）"),
        (NEW_CMA, "3.8 CMA-ModelPred-Direct v2（正式model_pred目标）"),
    ]
)

for method, title in method_titles.items():
    out.extend([f"### {title}", ""])
    rows: list[list[str]] = []
    for dataset, model in combos:
        item = candidates[(dataset, model, method)]
        note = item["note"] if method in (HIST_CMA, NEW_CMA) else "-"
        rows.append([dataset, model, item["top3"], item["top5"], note])
    out.extend(md_table(["数据集", "模型", "Top-3", "Top-5", "覆盖/状态注释"], rows))
    out.append("")

out.extend(
    [
        "## 4. 21组数据集×模型：七方法候选层与两版并集",
        "",
        "每个组合先列固定六方法，再分别列历史CMA-alt和正式CMA-ModelPred。其后两行并集分别对应两套七方法版本。",
        "",
    ]
)

combo_index = 0
for dataset, model in combos:
    combo_index += 1
    out.extend([f"### 4.{combo_index} {dataset} × {model}", ""])
    method_rows: list[list[str]] = []
    for method in all_methods:
        item = candidates[(dataset, model, method)]
        role = "固定方法"
        if method == HIST_CMA:
            role = "历史CMA（alt）"
        elif method == NEW_CMA:
            role = "正式CMA（model_pred）"
        method_rows.append([method, role, item["top3"], item["top5"]])
    out.extend(md_table(["方法", "版本角色", "Top-3", "Top-5"], method_rows))
    out.append("")
    union_rows: list[list[str]] = []
    for version in version_methods:
        union = recomputed_unions[(version, dataset, model)]
        union_rows.append(
            [
                version,
                str(union["top3"]),
                str(union["top3_count"]),
                str(union["top5"]),
                str(union["top5_count"]),
            ]
        )
    out.extend(md_table(["七方法版本", "Top-3并集", "层数", "Top-5并集", "层数"], union_rows))
    out.append("")

out.extend(["## 5. 21组两版七方法并集总表", ""])
summary_rows: list[list[str]] = []
for dataset, model in combos:
    old = recomputed_unions[("历史 CMA-alt v1.3", dataset, model)]
    new = recomputed_unions[("正式 CMA-ModelPred v2", dataset, model)]
    summary_rows.append(
        [
            dataset,
            model,
            str(old["top3"]),
            str(old["top3_count"]),
            str(new["top3"]),
            str(new["top3_count"]),
            str(old["top5"]),
            str(old["top5_count"]),
            str(new["top5"]),
            str(new["top5_count"]),
        ]
    )
out.extend(
    md_table(
        [
            "数据集",
            "模型",
            "历史alt Top-3并集",
            "数",
            "ModelPred Top-3并集",
            "数",
            "历史alt Top-5并集",
            "数",
            "ModelPred Top-5并集",
            "数",
        ],
        summary_rows,
    )
)
out.append("")

out.extend(["## 6. 两版CMA逐组合变化", ""])
cma_compare_rows: list[list[str]] = []
cma_top3_changed = 0
cma_top5_changed = 0
for dataset, model in combos:
    old = candidates[(dataset, model, HIST_CMA)]
    new = candidates[(dataset, model, NEW_CMA)]
    changed3 = set(split_layers(old["top3"])) != set(split_layers(new["top3"]))
    changed5 = set(split_layers(old["top5"])) != set(split_layers(new["top5"]))
    cma_top3_changed += changed3
    cma_top5_changed += changed5
    cma_compare_rows.append(
        [
            dataset,
            model,
            old["top3"],
            new["top3"],
            "变化" if changed3 else "不变",
            old["top5"],
            new["top5"],
            "变化" if changed5 else "不变",
        ]
    )
out.extend(
    md_table(
        [
            "数据集",
            "模型",
            "CMA-alt Top-3",
            "CMA-ModelPred Top-3",
            "集合",
            "CMA-alt Top-5",
            "CMA-ModelPred Top-5",
            "集合",
        ],
        cma_compare_rows,
    )
)
out.extend(
    [
        "",
        f"CMA候选集合变化统计：Top-3为{cma_top3_changed}/21组，Top-5为{cma_top5_changed}/21组。顺序变化但集合相同不计入该数字；完整排序仍以上表为准。",
        "",
    ]
)

totals: dict[str, tuple[int, int]] = {}
for version in version_methods:
    totals[version] = (
        sum(int(recomputed_unions[(version, dataset, model)]["top3_count"]) for dataset, model in combos),
        sum(int(recomputed_unions[(version, dataset, model)]["top5_count"]) for dataset, model in combos),
    )

top3_changed = 0
top5_changed = 0
for dataset, model in combos:
    old = recomputed_unions[("历史 CMA-alt v1.3", dataset, model)]
    new = recomputed_unions[("正式 CMA-ModelPred v2", dataset, model)]
    top3_changed += set(split_layers(str(old["top3"]))) != set(split_layers(str(new["top3"])))
    top5_changed += set(split_layers(str(old["top5"]))) != set(split_layers(str(new["top5"])))

out.extend(
    [
        "## 7. 完整性校验与使用说明",
        "",
        f"- 组合覆盖：21/21（3个数据集 × 7个模型）。",
        f"- 候选矩阵：168/168个版本化方法行（固定六方法126行 + CMA-alt 21行 + CMA-ModelPred 21行）。",
        "- 每一行均通过：Top-3恰好3个唯一层、Top-5恰好5个唯一层、Top-3是Top-5子集。",
        f"- 历史CMA-alt七方法并集总量：Top-3共{totals['历史 CMA-alt v1.3'][0]}项，Top-5共{totals['历史 CMA-alt v1.3'][1]}项。",
        f"- 正式CMA-ModelPred七方法并集总量：Top-3共{totals['正式 CMA-ModelPred v2'][0]}项，Top-5共{totals['正式 CMA-ModelPred v2'][1]}项。",
        f"- 替换CMA版本后，21组中Top-3并集集合有{top3_changed}组变化，Top-5并集集合有{top5_changed}组变化。",
        f"- CMA方法自身的候选集合变化：Top-3有{cma_top3_changed}/21组，Top-5有{cma_top5_changed}/21组。",
        "- 两版并集均与现有机器可读并集CSV逐组合、逐字段一致；若后续候选公式或CMA协议改变，应新建版本，不能原地覆盖本表。",
        "- 本文只冻结推荐候选层及并集。真实Adapter训练/评测数值、失败层与待补层仍以主手册第4章及服务器完成标记为准；不得把未评测层当0分。",
        "",
    ]
)

TARGET.parent.mkdir(parents=True, exist_ok=True)
TARGET.write_text("\n".join(out), encoding="utf-8")

print(f"WROTE={TARGET}")
print(f"LINES={len(out)}")
print(f"CANDIDATE_ROWS={len(candidates)}")
for version, (top3_total, top5_total) in totals.items():
    print(f"{version}: TOP3_UNION_TOTAL={top3_total}; TOP5_UNION_TOTAL={top5_total}")
print(f"UNION_SET_CHANGED: TOP3={top3_changed}/21; TOP5={top5_changed}/21")
