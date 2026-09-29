from __future__ import annotations

import hashlib
import csv
from pathlib import Path


SOURCE = Path("md/Location/6location_7model_3datas_top_3_5_layers_outcome.md")
TARGET = Path("md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md")
SUPPLEMENT = Path("outputs/firstphase_oursdirect_verified_eval_supplement_20260915.csv")


def table_after_prefix(lines: list[str], prefix: str, start: int = 0) -> list[dict[str, str]]:
    heading = next(i for i, line in enumerate(lines[start:], start) if line.strip().startswith(prefix))
    cursor = heading + 1
    while cursor < len(lines) and not lines[cursor].startswith("|"):
        cursor += 1
    header = [cell.strip() for cell in lines[cursor].strip("|").split("|")]
    cursor += 2
    rows: list[dict[str, str]] = []
    while cursor < len(lines) and lines[cursor].startswith("|"):
        values = [cell.strip() for cell in lines[cursor].strip("|").split("|")]
        rows.append(dict(zip(header, values)))
        cursor += 1
    return rows


def config_name(status: str) -> str:
    if "RECOVERED_EARLY" in status:
        return "main/recovered-early"
    if "STABLE" in status:
        return "stable"
    if "MAIN" in status:
        return "main"
    return "main/legacy"


def row_priority(row: dict[str, str]) -> int:
    status = row.get("Train Status", "")
    if "STABLE" in status:
        priority = 0
    elif "MAIN" in status:
        priority = 2
    else:
        priority = 1
    if row.get("Layer", "").endswith("-2"):
        priority = 3
    return priority


def display_metric(value: str | None) -> str:
    return value if value not in (None, "") else "—"


def layer_sort_key(row: dict[str, str]) -> tuple[int, str]:
    layer = row["Layer"]
    return (int(layer.split("-", 1)[0][1:]), layer)


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    lines = source_bytes.decode("utf-8").splitlines()
    ours_rows = table_after_prefix(lines, "#### 2.7.0 Ours-Direct")
    section4 = next(i for i, line in enumerate(lines) if line.startswith("## 4. "))

    records: list[dict[str, str]] = []
    for dataset in ("EVQA-pilot500", "MMKE-visual", "MMKE-entity"):
        for row in table_after_prefix(lines, f"#### {dataset}", section4):
            item = dict(row)
            item["Dataset"] = dataset
            records.append(item)

    # EVQA × BLIP2 is intentionally kept in section 4.1 rather than section 4.0.
    for row in table_after_prefix(lines, "### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B", section4):
        item = dict(row)
        item["Dataset"] = "EVQA-pilot500"
        item["Model"] = "blip2-opt-2.7b"
        item["Samples"] = "2093"
        item["Train Status"] = "TRAIN_DONE"
        records.append(item)

    # Server-verified evaluations omitted from the source section 4 tables.
    # Keep their original markers and configuration/recovery distinctions.
    existing = {(r["Dataset"], r["Model"], r["Layer"]) for r in records}
    with SUPPLEMENT.open(encoding="utf-8", newline="") as stream:
        supplement_rows = list(csv.DictReader(stream))
    for item in supplement_rows:
        key = (item["Dataset"], item["Model"], item["Layer"])
        if key not in existing:
            records.append(dict(item))
            existing.add(key)

    canonical_models = {
        "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
        "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
        "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
        "llava-v1.5-7b": "LLaVA-v1.5-7B",
        "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
        "paligemma-3b": "PaliGemma-3B",
        "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
    }
    for row in records:
        row["Canonical Model"] = canonical_models.get(row["Model"].lower(), row["Model"])
        row["Config"] = config_name(row.get("Train Status", ""))

    # Prefer main results; use stable only when the source has no main result for that layer.
    evidence: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in records:
        base_layer = row["Layer"].replace("-2", "")
        key = (row["Dataset"], row["Canonical Model"], base_layer)
        if key not in evidence or row_priority(row) > row_priority(evidence[key]):
            evidence[key] = row

    ours_map: dict[tuple[str, str], dict[str, object]] = {}
    for row in ours_rows:
        top3 = row["Top-3"].split(",")
        ours_map[(row["Dataset"], row["Model"])] = {
            "top1": top3[0],
            "top3": top3,
            "top5": row["Top-5"].split(","),
        }

    out: list[str] = []
    out.extend(
        [
            "# 第一阶段真实评测数据与 Ours-Direct 推荐层",
            "",
            "> 生成日期：2026-09-15（Asia/Shanghai）  ",
            f"> 来源：`{SOURCE.as_posix()}`；第4节漏行补证：`{SUPPLEMENT.as_posix()}`  ",
            f"> 来源文件 SHA-256：`{hashlib.sha256(source_bytes).hexdigest()}`",
            "",
            "## 1. 口径与使用规则",
            "",
            "- Ours-Direct正式主公式固定为 `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm`，不含深度权重。",
            "- `Top-1`是公式分数排名第一的预测层；`Top-3`是前三个预测层，顺序即公式排名。",
            "- 第二阶段没有独立validation时，主实验直接使用Ours预测Top-1；有预先划分且与test/eval隔离的validation时，才允许在Top-3内选层。",
            "- 本文件展示的真实评测值只能用于第一阶段方法分析与证据核验，禁止依据test/eval中Average最高的层反向选择第二阶段主实验层，否则会产生测试集泄漏。",
            "- 真实结果继承原手册第4节验收口径：只有完成训练、选出minimum-EMA checkpoint并完成独立test/eval的层才进入明细。",
            "- `stable`结果与`main`不是同一配置；stable-only只能作为已有证据展示，不能直接并入主配置公平比较。",
            "- 原手册第3.4.6节把EVQA×InstructBLIP L0/L1/L11、EVQA×MiniGPT-4 L19、MMKE-entity×MiniGPT-4 L26/L27及MMKE-visual×LLaVA L3登记为完成，但第4节漏了详细行；逐层服务器审计又查出另外34条第4节漏行。本文件从共享盘逐层`eval_full.done`、`selected_checkpoint.tsv`、实体checkpoint和`results.json`补录指标，证据路径保存在补证CSV；源手册不在本次操作中修改。",
            "- EVQA×InstructBLIP L14/L15/L16/L19虽完成2093条独立eval，但共享盘`loss_history.csv`和`train.done`分别只记录到Epoch 40/38/37/41，属于`main/recovered-early`，不可冒充训练满50 epoch的常规主配置结果；在严格50-epoch公平比较中应单独分栏或待后续续训。",
            "- MMKE-visual×LLaVA L3的评测输出目录沿用`EVQA_full_test_pilot500`旧命名；评测日志实际加载`vqa_mmke_visual_eval_evqa_compat.json`，`results.json`的293条可靠性图像全部来自MMKE-Bench visual，不能按目录名误判为EVQA评测。",
            "",
            "## 2. 21组 Ours-Direct Top-1 / Top-3 与推荐层",
            "",
            "| 数据集 | 模型 | Ours Top-1 | Ours Top-3（有序） | Top-1真实评测 | Top-3已有评测 | 主配置可比 | 第二阶段推荐层 |",
            "|---|---|---:|---|---|---:|---:|---:|",
        ]
    )

    for row in ours_rows:
        dataset, model = row["Dataset"], row["Model"]
        top3 = row["Top-3"].split(",")
        top1_record = evidence.get((dataset, model, top3[0]))
        if top1_record:
            top1_eval = f"Average {top1_record['Average']}（{top1_record['Config']}）"
        else:
            top1_eval = "待完成"
        available = 0
        main_comparable = 0
        for layer in top3:
            result = evidence.get((dataset, model, layer))
            if result:
                available += 1
                if result["Config"] != "stable":
                    main_comparable += 1
        out.append(
            f"| {dataset} | {model} | **{top3[0]}** | {','.join(top3)} | {top1_eval} | {available}/3 | {main_comparable}/3 | **{top3[0]}** |"
        )

    complete_eval_combos = sum(
        all((row["Dataset"], row["Model"], layer) in evidence for layer in row["Top-3"].split(","))
        for row in ours_rows
    )
    main_comparable_combos = sum(
        all(
            (result := evidence.get((row["Dataset"], row["Model"], layer))) is not None
            and result["Config"] != "stable"
            for layer in row["Top-3"].split(",")
        )
        for row in ours_rows
    )
    out.extend(
        [
            "",
            f"**当前Top-3证据覆盖：** {complete_eval_combos}/21组的Ours前三层均已有正式评测；严格不混用stable-only时，主配置可比为{main_comparable_combos}/21组。缺失层及stable-only层分别见第5.1、5.2节。",
        ]
    )

    out.extend(
        [
            "",
            "### 2.1 第二阶段直接配置表",
            "",
            "下表可直接转成第二阶段配置；`recommended_layer`严格等于Ours预测Top-1，而不是Top-3中测试分数最高层。",
            "",
            "| dataset | model | recommended_layer | fallback_top3 | selection_policy |",
            "|---|---|---:|---|---|",
        ]
    )
    for row in ours_rows:
        top3 = row["Top-3"].split(",")
        out.append(
            f"| {row['Dataset']} | {row['Model']} | {top3[0]} | {','.join(top3)} | Top-1 direct；仅独立validation可在Top-3内选择 |"
        )

    out.extend(
        [
            "",
            "## 3. Ours Top-3候选层的真实训练与评测证据",
            "",
            "指标为原手册及服务器补证登记的百分制结果：`Rel`（Reliability）、`T-Gen`/`M-Gen`（文本/多模态Generality）、`T-Loc`/`M-Loc`（文本/多模态Locality），`Average`为五项平均。`—`表示尚无完成评测，不能填0。",
        ]
    )

    for dataset in ("EVQA-pilot500", "MMKE-visual", "MMKE-entity"):
        out.extend(["", f"### 3.{('EVQA-pilot500','MMKE-visual','MMKE-entity').index(dataset)+1} {dataset}", ""])
        for ours_row in [row for row in ours_rows if row["Dataset"] == dataset]:
            model = ours_row["Model"]
            top3 = ours_row["Top-3"].split(",")
            out.extend(
                [
                    f"#### {model}",
                    "",
                    f"- Ours Top-1 / 第二阶段直接推荐：`{top3[0]}`",
                    f"- Ours Top-3：`{','.join(top3)}`",
                    "",
                    "| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |",
                    "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
                ]
            )
            for rank, layer in enumerate(top3, 1):
                result = evidence.get((dataset, model, layer))
                if result is None:
                    out.append(f"| {rank} | {layer} | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |")
                else:
                    values = [
                        str(rank),
                        layer,
                        result["Config"],
                        display_metric(result.get("Ckpt Epoch")),
                        display_metric(result.get("Raw Loss")),
                        display_metric(result.get("EMA Loss")),
                        display_metric(result.get("Samples")),
                        display_metric(result.get("Rel")),
                        display_metric(result.get("T-Gen")),
                        display_metric(result.get("M-Gen")),
                        display_metric(result.get("T-Loc")),
                        display_metric(result.get("M-Loc")),
                        display_metric(result.get("Average")),
                        result.get("Train Status", "EVAL_DONE"),
                    ]
                    out.append("| " + " | ".join(values) + " |")
            out.append("")

    out.extend(
        [
            "## 4. 原手册已完成候选层与服务器补证评测明细",
            "",
            "本节保留原手册第4节中所有已登记的逐层状态，并追加41条服务器补证评测记录，不只包含Ours候选。`Ours标记`用于指出该层是否为本组合的主公式Top-1/Top-3；未标记不表示结果无效，只表示不是Ours主公式前三名。原表中PaliGemma stable L0失败行继续保留，但它无正式评测，不能计入完成数。",
        ]
    )

    model_order = [row["Model"] for row in ours_rows[:7]]
    for dataset_index, dataset in enumerate(("EVQA-pilot500", "MMKE-visual", "MMKE-entity"), 1):
        out.extend(["", f"### 4.{dataset_index} {dataset}", ""])
        for model in model_order:
            group = [row for row in records if row["Dataset"] == dataset and row["Canonical Model"] == model]
            if not group:
                continue
            ours = ours_map[(dataset, model)]
            top1 = str(ours["top1"])
            top3 = list(ours["top3"])
            out.extend(
                [
                    f"#### {model}",
                    "",
                    f"Ours Top-1：`{top1}`；Top-3：`{','.join(top3)}`。",
                    "",
                    "| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |",
                    "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
                ]
            )
            for result in sorted(group, key=layer_sort_key):
                base_layer = result["Layer"].replace("-2", "")
                if base_layer == top1:
                    ours_mark = "Top-1"
                elif base_layer in top3:
                    ours_mark = "Top-3"
                else:
                    ours_mark = "—"
                values = [
                    result["Layer"],
                    result["Config"],
                    ours_mark,
                    display_metric(result.get("Ckpt Epoch")),
                    display_metric(result.get("Raw Loss")),
                    display_metric(result.get("EMA Loss")),
                    display_metric(result.get("Samples")),
                    display_metric(result.get("Rel")),
                    display_metric(result.get("T-Gen")),
                    display_metric(result.get("M-Gen")),
                    display_metric(result.get("T-Loc")),
                    display_metric(result.get("M-Loc")),
                    display_metric(result.get("Average")),
                    result.get("Train Status", "EVAL_DONE"),
                ]
                out.append("| " + " | ".join(values) + " |")
            out.append("")

    out.extend(
        [
            "## 5. 当前缺失与解释限制",
            "",
            "### 5.1 Ours Top-3尚无任何正式评测的层",
            "",
            "| 数据集 | 模型 | 缺失层 |",
            "|---|---|---|",
        ]
    )
    for row in ours_rows:
        dataset, model = row["Dataset"], row["Model"]
        missing = [
            layer
            for layer in row["Top-3"].split(",")
            if (dataset, model, layer) not in evidence
        ]
        if missing:
            out.append(f"| {dataset} | {model} | {','.join(missing)} |")

    out.extend(
        [
            "",
            "### 5.2 已有评测但仅为stable配置的Ours层",
            "",
            "| 数据集 | 模型 | stable-only层 | 说明 |",
            "|---|---|---|---|",
        ]
    )
    for row in ours_rows:
        dataset, model = row["Dataset"], row["Model"]
        stable_only = []
        for layer in row["Top-3"].split(","):
            result = evidence.get((dataset, model, layer))
            if result and result["Config"] == "stable":
                stable_only.append(layer)
        if stable_only:
            out.append(f"| {dataset} | {model} | {','.join(stable_only)} | 有真实评测，但不能替代main配置结果 |")

    out.extend(
        [
            "",
            "### 5.3 解释限制",
            "",
            "- 表中Top-3行出现`待完成正式评测`时，只能说明定位预测已经存在，不能声称该层已有真实编辑效果。",
            "- PaliGemma的stable与main必须分开解释；本文件保留二者，但第二阶段主配置证据优先读取main。",
            "- 当前正在服务器运行且尚无完整正式评测的层不会提前进入本文件；新完成层须凭selected与独立eval补录，不能只凭状态文字。",
            "- 第二阶段跨模型扩展时，每个组合读取本文件第2.1节自己的`recommended_layer`，禁止把BLIP2的L0直接类推给其他模型。",
            "",
            "## 6. 可复核来源",
            "",
            "- Ours Top-1/Top-3：来源手册第2.7.0节。",
            "- 真实训练与评测值：来源手册第4、4.1节。",
            "- 第4节漏行的6层完整评测补证：`outputs/firstphase_oursdirect_verified_eval_supplement_20260915.csv`，每行附共享盘`eval_full.done`绝对路径。",
            "- 原始Ours排名CSV：`md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/formula_topk_all_21.csv`。",
            "- 本文件生成脚本：`outputs/build_firstphase_testvalue_oursdirect_recommend.py`。",
            "",
        ]
    )
    content = "\n".join(out)
    TARGET.write_text(content, encoding="utf-8", newline="\n")
    print(f"WROTE {TARGET.as_posix()} lines={len(out)} chars={len(content)}")


if __name__ == "__main__":
    main()
