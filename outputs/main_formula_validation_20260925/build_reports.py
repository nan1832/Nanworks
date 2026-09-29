"""Render evidence reports and a static, exportable scientific figure."""
from pathlib import Path
from statistics import mean
import csv
import json
import hashlib
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
S = json.loads((OUT / "analysis_summary.json").read_text(encoding="utf-8"))
C = json.loads((OUT / "case_aggregation_audit.json").read_text(encoding="utf-8"))
CASES = json.loads((OUT / "selected_real_cases.json").read_text(encoding="utf-8"))
N = next(r for r in S["primary_top3"] if r["comparator"] == "new_norm_only")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
                     + ["| " + " | ".join(str(x).replace("|", "／").replace("\n", " ") for x in row) + " |" for row in rows])


def link(path, label=None):
    return f"[{label or path.name}](<{path.as_posix()}>)"


def f(x):
    return f"{x:.3f}"


def signed(x):
    return f"{x:+.3f}"


names = {"evqa-pilot500": "EVQA", "mmke-entity": "MMKE-entity", "mmke-visual": "MMKE-visual"}
models = {"minigpt-4-vicuna-7b": "MiniGPT-4", "qwen2.5-vl-3b": "Qwen2.5-VL"}
diff = S["norm_different_complete"]
font = FontProperties(fname="C:/Windows/Fonts/msyh.ttc")
plt.rcParams.update({"font.family": font.get_name(), "axes.unicode_minus": False, "font.size": 10})
fig, ax = plt.subplots(figsize=(9.2, 4.8), layout="constrained")
labels = [names[r["dataset"]] + " × " + models[r["model"]] for r in diff]
vals = [r["delta_best"] for r in diff]
ax.barh(range(len(diff)), vals, color=["#bd514b" if v < 0 else "#267b74" for v in vals], height=.55)
ax.axvline(0, color="#46515b", lw=.8)
ax.set_yticks(range(len(diff)), labels)
ax.invert_yaxis()
ax.set_xlim(-7.3, 2.0)
for i, v in enumerate(vals):
    ax.text(v + (.10 if v >= 0 else -.10), i, f"{v:+.3f}", ha="right" if v < 0 else "left", va="center")
ax.set_xlabel("Best@3 差值（主公式 − 纯新梯度范数，百分点）")
ax.set_title("方向项改变候选集合的 4 组完整对照", loc="left", fontweight="bold")
ax.text(0, -.28, "完整配对共 15 组：其余 11 组候选集合相同。总体均值差 −0.271；属于既有数据事后消融。",
        transform=ax.transAxes, fontsize=9, color="#4b5663")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.grid(axis="x", alpha=.15)
fig.savefig(OUT / "direction_ablation_different_cases.png", dpi=220, bbox_inches="tight")
fig.savefig(OUT / "direction_ablation_different_cases.svg", bbox_inches="tight")
plt.close(fig)

formula_table = table(["设置", "层评分", "检验对象"], [
    ["当前主公式", "abs(c̄ₗ) × n̄ₗ", "固定参照，无深度权重"],
    ["去方向项", "n̄ₗ", "旧知识方向是否带来额外价值"],
    ["去幅度项", "abs(c̄ₗ)", "新知识梯度幅度是否必要"],
    ["保留符号", "c̄ₗ × n̄ₗ", "绝对值的作用"],
    ["仅负方向", "max(0, −c̄ₗ) × n̄ₗ", "只保留冲突方向；零分不作为合格候选"],
    ["方向替代", "(1 − c̄ₗ) × n̄ₗ", "另一种方向加权规则"],
    ["增加深度", "abs(c̄ₗ) × n̄ₗ × ((l+1)/L)²", "固定深度先验"],
    ["范数增加深度", "n̄ₗ × ((l+1)/L)²", "另一深度对照"],
    ["视觉 LGA", "meanᵢ〈g_old,i,l, g_new,i,l〉", "将原始梯度内积换至视觉隐藏状态"],
])
ablation_table = table(["对照方法", "完整配对组数", "主公式胜／平／负", "ΔBest@3", "ΔMean@3"], [
    [S["method_names"][r["comparator"]], r["n"], f'{r["main_wins"]}/{r["ties"]}/{r["main_losses"]}',
     signed(r["delta_best"]), signed(r["delta_mean"])] for r in S["primary_top3"]])
norm_table = table(["指标", "主公式", "纯新梯度范数", "主公式减对照"], [
    ["平均 Best@3", f(N["main_best"]), f(N["comparator_best"]), signed(N["delta_best"])],
    ["平均 Mean@3", f(N["main_mean"]), f(N["comparator_mean"]), signed(N["delta_mean"])],
    ["平均 Regret@3（低为好）", f(N["main_regret"]), f(N["comparator_regret"]), signed(N["delta_regret"])],
    ["Hit@3", "6/15", "5/15", "+1 组"],
])
diff_table = table(["组合", "主公式 Top-3", "纯范数 Top-3", "主公式 Best@3", "纯范数 Best@3", "差值"], [
    [names[r["dataset"]]+" × "+models[r["model"]], r["main_candidates"], r["comparator_candidates"],
     f(r["main_best"]), f(r["comparator_best"]), signed(r["delta_best"])] for r in diff])
corr_table = table(["对照", "组数", "主公式平均ρ", "对照平均ρ", "主公式平均τ", "对照平均τ"], [
    [S["method_names"][r["comparator"]], r["n"], f(r["main_spearman"]), f(r["comparator_spearman"]),
     f(r["main_kendall"]), f(r["comparator_kendall"])]
    for r in S["primary_correlations"] if r["comparator"] in ("new_norm_only", "visual_lga_dot", "abs_cos_only", "main_depth2")])
agg_table = table(["模型（早期 bridge30）", "聚合公式", "Top-3"], [
    [r["model"], {"current_product": "abs(mean cos) × mean norm", "mean_absolute_projection": "mean(abs(cos) × norm)",
                   "absolute_mean_projection": "abs(mean(cos × norm))", "new_norm_only": "mean norm"}[r["formula"]], r["top3"]]
    for r in C["aggregation_topk"]])

report = f"""# 主公式实证核验：方向项消融、聚合诊断与真实案例

生成日期：2026-09-25。状态：已完成本地重算和原始案例核验；尚未执行新的独立确认实验。当前主公式、历史实验记录和论文章节均未改写。

> **组数口径补充：** 现有扫层台账是19/21组已有评测覆盖。主公式与纯范数双方Top-3在同配置下完整可比为16组；本报告原主表的15组另加了“梯度覆盖率至少80%”这一分析筛选，不能解释为只有15组实验完成。16组与15组结果、四个额外排除组合及逐组证据见 {link(OUT/'组数口径核对_19组与15组.md', '组数口径核对')}。

## 1. 结论先行

**当前证据支持把主公式保留为冻结的候选规则，但不足以支持“方向项稳定优于纯新知识梯度范数”。** 15 组完整 Top-3 配对中，主公式 Best@3 为 {f(N['main_best'])}，纯范数为 {f(N['comparator_best'])}，差 {signed(N['delta_best'])} 个百分点；主公式 3 胜、11 平、1 负。方向项确实会改变部分候选层，但收益具有条件性。

主公式相对视觉 LGA 内积、仅余弦、以及加入深度平方的版本，在各自完整配对集合中表现较好。**这些结果不能替代“主公式对纯范数”的关键消融，也不能把不同配对集合的均值排成一个总体名次。**

真实自由生成案例表明，有些评分改善伴随目标实体出现，有些主要反映描述模板或词汇重合变化。需要分别验证定位评分的预测能力与编辑成功指标的含义。

## 2. 数据与比较口径

- 梯度来源为 21 组归档 `ours_direct_layer_scores.csv`，新旧目标、视觉 token 范围、层索引和原有效样本保持一致；未重新运行模型。
- 编辑效果读取上一轮已审计的 `verified_outcomes_with_flags.csv`，仅使用 `clean_exclusion` 为空的主配置结果，不挑选更高成绩的 checkpoint。另输出包含历史早停／数值标记结果的敏感性口径。
- 主统计要求梯度覆盖率至少 80%，且双方全部 K 个候选层均有合格编辑评测。缺失层不填零，也不把部分候选中的最高成绩当作完整 Best@K。
- MMKE-entity × BLIP2 的当前归档梯度仅 284/636（44.654%），从主统计排除。其 955 条自由生成诊断另列，不补入第一阶段 954 条的定位表。
- Average 是历史五项编辑指标的平均分，本文数值采用 0–100 尺度；差值单位为百分点。Regret 和 Hit 的参照仅为本组合已合格实测层中的最好值，不是全网络全层的未知最优。
- 以上组合曾参与公式比较，所有本节性能数字属于事后复核。源文件 SHA-256、脚本、逐层分数、候选集合、排除原因均随报告保存。已核验上一轮的 {S['unchanged_prior_source_count']} 个输入源未变化，主公式／视觉 LGA 重算与上一轮一致。

## 3. 单因素消融设计

记 c̄ₗ = meanᵢ cos(g_old,i,l, g_new,i,l)，n̄ₗ = meanᵢ ||g_new,i,l||₂；梯度对象是编辑接口的视觉隐藏状态。当前主公式是先求均值、再取绝对值并相乘。所有分数降序取候选层，并列时按层号升序。

{formula_table}

“保留符号”与“仅负方向”两项直接在无深度权重的主公式上改动方向处理；避免把方向与深度同时改变后，误认为得到了方向项的单独作用。

{ablation_table}

表中差值均为主公式减对应对照。每行独立使用该行双方的完整配对集合，因此组数不同。五种核心对照的共同完整集合只有 5 组；共同集合结果在 `common_cohort_top3.csv`，其中主公式 Best@3 为 66.791、纯范数为 68.024，也未呈现主公式占优。该小集合不能代表全部 21 组。

## 4. 方向项：最关键的 15 组对照

{norm_table}

全部 21 组中，两种规则的 Top-3 集合相同 13 组，顺序完全相同 12 组。完整纳入的 15 组里，11 组集合相同，因此 Best@3 相同并非 11 次独立的方向机制验证；真正改变集合且已完成双方评测的是以下 4 组。

{diff_table}

![方向项改变候选集合的四组对照](<{(OUT/'direction_ablation_different_cases.png').as_posix()}>)

EVQA × MiniGPT-4 是必须保留的反例：主公式的 L18/L19/L16 中最好为 L16（64.940），纯范数 L0/L1/L2 中最好为 L1（71.104）。其 6.164 点损失抵消了另外三组的小幅收益，不能只报告“3 胜 1 负”而省略幅度。

**Top-1 与 Top-3 要分开。** Top-1 完整配对有 17 组，主公式平均提高 {signed(S['norm_top1']['delta_best'])} 点，4 胜、13 平、0 负；限定回同一批 15 组，Top-1 仍提高 {signed(S['top1_on_norm_top3_cohort']['delta_top1'])} 点。因此差异不只是换了配对集合。但是本文原本讨论固定候选预算 K=3，不能因为 Top-1 较有利便事后替换主指标。Top-5 的完整配对只有 6 组，两者候选集合及结果全部相同，证据范围有限。

## 5. 层评分与真实成绩的排序关系

同一组合内，两种规则都在相同的合格实测层上计算相关性；至少 5 层、覆盖率至少 80%，再对组合等权平均。未把各模型梯度幅度直接混合相关。

{corr_table}

纯范数的平均 Spearman ρ=0.361，高于主公式 0.324；目前“方向项改善整体层排序”的说法也没有得到支持。视觉 LGA 仅 0.080，所以“优于视觉内积”和“优于纯范数”是两个不同命题。相关性来自已有、并非随机抽取的实测层，不等于对所有未测层的预测能力。

## 6. 聚合次序确实会改变候选层

在非零梯度且不计数值稳定项时，单样本 abs(cos)×||g_new|| 是新梯度在旧梯度单位方向上的投影绝对值。但当前层评分 abs(mean cos)×mean norm 并不等于 mean(abs(cos)×norm)。平均余弦可能受正负样本抵消；范数与方向的样本协变关系也被分开。

找到的逐样本缓存是 **2026 年 5 月早期桥梁 train30**：BLIP2 与 LLaVA 各 30 个样本、32 层；最后一层全零梯度排除后为 31 个有效层。下面只诊断数值聚合，不比较正式编辑性能。

{agg_table}

BLIP2 的 Top-3 从 L13/L15/L14 变为 L0/L1/L2，说明这不是可以略去的实现细节。当前完整 21 组正式材料中本次未定位到对应逐样本 cos/norm 缓存，不能由层均值准确重建 mean(abs(cos)×norm)。正式扩展需要保留相同样本 ID 的逐样本梯度统计后重算；**早期 30 条结果不替代正式 21 组消融，也不证明新聚合一定更好。**

## 7. 真实案例及评分可信性

已对 BLIP2 L0、epoch-24、MMKE-entity 官方 955 条完成重新核验：两个阶段样本 ID 一一对应，checkpoint 和数据哈希一致；从预测文本重算了 {C['raw_string_metric_checks']:,} 项 F1/EM，匹配原始记录。该任务本轮无模型参数更新。

直接目标的 teacher-forcing token accuracy 从 50.989% 至 57.710%；自由生成 word-F1 从 4.283% 至 13.896%。955 条中 F1 提高 913 条、下降 42 条、持平 0 条。40 条出现 teacher-forcing accuracy 上升而自由生成 F1 未上升。自由生成 EM 前后均为 0%，编辑后 732/955 条达到长度上限；EM 为零本身也不能替代人工语义判断。

完整问题、目标、编辑前后原文、样本哈希、各分数及选例规则见 {link(OUT/'真实案例核验.md')}。这里的目标是数据集构造的编辑目标，不应当作现实世界事实。

这个诊断只有 L0，能说明编辑前后的变化及评分差异，**不能证明 L0 优于其他层，也不能单独证明方向项优于纯范数**。而且本组归档定位覆盖率较低，更不能借案例绕过主比较的覆盖率门槛。

## 8. 独立确认与最小补全

{link(ROOT/'md/Location/6edit_layer_localization_candidate_methods_简洁说明版.md', '方法手册')} 第 6.9 节明确记载主公式由真实扫层比较选定。已有 21 组不能事后重新命名为独立测试。后补评测完成得较晚、重新随机划分既有成绩、或对这些成绩 bootstrap，都不能自动消除公式选择造成的偏差。

方向项不同集合尚缺本地合格结果的组合为：EVQA × InstructBLIP（L9）；EVQA × LLaVA（L2/L3）；MMKE-visual × LLaVA（L5/L6）；MMKE-entity × LLaVA（L0/L1/L6/L11/L12/L13），共 11 个层位置。应先核对已有服务器成品，再决定是否真要补跑；“本地未核验”不等于“从未训练”。另有 MMKE-visual × PaliGemma 的 L3/L5 仅 stable 配置，虽然影响覆盖，两种规则的候选集合相同，不能作为方向项差异证据。

2026-09-25 追加核验：同配置要求不等于必须使用原 main 配方。该组可保留 stable L3/L5，补普通 stable L4，形成独立的同配置 stable 配对；若修订主表协议，应公开说明并让所有方法共用同一结果池。当前尚未补跑，不改变本报告既有统计。详见 [PaliGemma主配置异常与stable可比性核验.md](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/main_formula_validation_20260925/PaliGemma主配置异常与stable可比性核验.md>)。

待执行的协议已经写入 {link(OUT/'独立确认实验_冻结协议草案.md')}。当前未找到足以确认“从未参与设计／选层／调参”的新请求集合，也没有执行新训练或新独立评测。无需先替换主公式；下一步应先锁定可证明未使用的新请求与数据哈希，再按冻结比较完成检验。

## 9. 论文可以采用的表述

> 本文以新旧目标在视觉编辑接口上的梯度关系构建候选层评分，并通过去方向项、去幅度项、符号处理及深度先验的消融考察各组成因素。已有完整配对结果表明，绝对方向加权能够改变部分模型—任务组合的层推荐，但其相对于纯新目标梯度范数的收益并不一致；在 15 组 Top-3 完整配对中，两者平均 Best@3 分别为 72.493 和 72.764。因此，本文将该评分作为候选层筛选的经验规则，并结合实际编辑评测考察适用条件，而不将其解释为普遍最优的定位准则。

上述是当前证据范围内的文字，可用于第 4 章候选评分比较与第 6 章讨论。它不宣称已经完成新的独立验证。

## 10. 文件与复算

- `recompute_ablations.py`：9 个公式、21 组 Top-1/3/5、逐层相关性、成对对照和缺层清单。
- `audit_cases_and_aggregation.py`：955 条原始案例、字符串指标复算、早期 bridge30 聚合诊断。
- `build_reports.py`：报告、案例文件和可导出 PNG/SVG 图。
- `analysis_summary.json`、`case_aggregation_audit.json`：精确数值、参数口径和源文件哈希。
- `paired_comparisons.csv`、`paired_summary.csv`：逐组及汇总结果；`direction_top3_missing_layers.csv`：缺失／排除原因。

依次运行以上三个 Python 脚本即可复算。脚本输出仅位于本目录，不改写原始梯度、训练结果或既有手册。
"""
(OUT / "主公式实证核验报告.md").write_text(report, encoding="utf-8")

case_report = """# 真实案例核验：完整自由生成及评分边界

来源：BLIP2-OPT-2.7B，L0，epoch-24，MMKE-entity 官方 955 条。固定编辑器，无新增训练。与第一阶段 954 条定位表分开。

这些案例的编辑目标由基准构造，可能是反事实陈述；此处仅核验输出与指定目标的关系，不将目标或生成内容当作现实知识。

## 选例规则

1. 对全部 955 条直接目标按自由生成 F1 差值分组：913 条提高、42 条下降、0 条持平。在非空组内按差值及源索引排序，取下中位条目，得到源索引 276 和 263。没有人为构造“持平案例”。
2. 固定源索引 0 用于检查 F1 上涨是否意味着关键目标实体已更改。
3. 补充一个正面实体示例：从目标首句 `corresponds to ...` 提取实体名称，要求完整词组在编辑后首行出现、编辑前全文未出现、F1 上升且编辑后未截断；满足条件后按源索引升序取首条。此规则为看过数据后的展示规则，且实体提取具有格式限制，不能把筛选数量解释为实体准确率或完整事实成功率。

所有示例均保存完整预测，不把 teacher-forcing 的逐位置预测拼接当作自由生成答案。`selected_real_cases.json` 还包含同一样本的关联问答与其他测试项，便于追溯。

"""
for i, r in enumerate(CASES, 1):
    q = r["free_reliability"]
    t = r["teacher_reliability"]
    case_report += f"## 案例 {i}：{r['selection']}\n\n"
    case_report += f"- 原始索引：**{r['source_record_index']}**（零起算），原始 JSONL 行号：{r['source_record_index']+1}。\n- sample_id：`{r['sample_id']}`。\n- 图片路径：`{q['image_path']}`。\n\n"
    case_report += table(["评分／属性", "编辑前", "编辑后"], [
        ["自由生成 word-F1（%）", f(100*r['free_before_f1']), f(100*r['free_after_f1'])],
        ["自由生成 EM", r['free_before_em'], r['free_after_em']],
        ["达到长度上限", r['truncated_before'], r['truncated_after']],
        ["teacher-forcing token accuracy（%）", f(100*r['teacher_before_acc']), f(100*r['teacher_after_acc'])],
    ]) + "\n\n"
    for label, value in (("问题", q["prompt"]), ("指定编辑目标", q["target"]),
                          ("编辑前自由生成（完整）", q["before"]["prediction"]),
                          ("编辑后自由生成（完整）", q["after"]["prediction"])):
        case_report += f"### {label}\n\n```text\n{value}\n```\n\n"
    comments = {
        276: "F1 上升约 6.919 点，但目标实体为 Porcellio scaber，编辑后首句为 Cephalopoda。这个例子体现词汇／模板更接近目标，不能据此判为目标实体已经编辑成功。",
        263: "teacher-forcing token accuracy 上升约 6.186 点，而自由生成 F1 下降约 2.595 点；目标 American pika 被回答为 American beaver。两个评价口径不一致，且目标实体未命中。",
        0: "F1 从 6.292% 升至 10.298%，但目标 Pixies 编辑前后均被回答为 The Beatles。F1 的上涨不能单独证明目标知识已经写入。",
        767: "编辑前首句只说 it's a tick；编辑后出现指定实体 Ixodes scapularis，且未达到长度上限。这是目标实体名称命中的正面示例。全文仍需逐项核对指定事实，实体名称正确不等于完整知识全部修改成功。",
    }
    case_report += f"**解读：** {comments.get(r['source_record_index'], '用于展示指定目标实体的出现；完整事实需另外标注。')}\n\n"
case_report += f"""## 可以支持什么

可以支持“固定 L0 编辑器引发输出变化，存在目标实体命中的实例，同时自动评分有解释边界”。不能支持“L0 是最优层”“方向项优于纯范数”或“关联知识整体改善”。后一类结论需要同样本跨候选层的自由生成对照及一致的人工标注。

原始自由生成文件：{link(ROOT.parent/'phase2_p3/g1_paired_official955_20260921/free/samples.jsonl')}。

逐样本复算表：{link(OUT/'free_generation_reliability_955.csv')}。原始哈希及核验摘要：{link(OUT/'case_aggregation_audit.json')}。
"""
(OUT / "真实案例核验.md").write_text(case_report, encoding="utf-8")

protocol = """# 独立确认实验：待执行冻结协议草案

状态：2026-09-25 草案。已经根据现有材料列明配置和缺口；尚未取得可核验的独立请求清单，未执行新训练／评测，未宣称完成预注册。

## 1. 要回答的唯一主问题

在固定候选预算 K=3 下，当前主公式 abs(mean cos) × mean new_norm 是否比纯新目标梯度范数提供更好的实际编辑候选层？保持原论文主问题，不因本次 Top-1 更有利而改动主终点。

主终点是独立请求集上、每组合固定 Top-3 候选的 Best@3 差值（主公式减纯范数），随后对预先列定组合等权平均。Best@3 是候选集合的回顾性潜力，不是无需验证就能部署的选层策略。部署终点另报：只用预先划定验证集从各自 3 层中选一层，再一次性在独立测试集评测。补报 Mean@3、Top-1、已有层范围内 Regret/Hit；不将 Best 与由其派生的 Regret 当作两项独立胜利。

## 2. 冻结事项

- 公式：只保留当前主公式与纯范数作为关键确认对照；视觉 LGA 可作为预先声明的参照。无深度权重，不再用测试结果选聚合方式或方向变体。
- 候选：沿用本目录 `candidate_topk.csv` 中固定的层列表；同一组合的重复层只评测一次。旧目标仍使用既定模型输出，新目标为既定 alt，保持完整答案损失及视觉 token 截取实现。若重新计算梯度，必须另冻结代理样本列表、有效样本规则及缓存哈希。
- 编辑训练：两种规则候选层使用同一编辑器、训练请求、训练步数／停止标准和 checkpoint 选择方法。可以复用满足该协议的已完成 checkpoint，但不能按新测试成绩重新挑选 epoch。
- 数据：以编辑请求／实体为划分单位，将同一请求的改写、图像变体、关联问答绑定，避免跨集合泄漏。新测试请求不得参与公式设计、训练、选层或参数选择。仅将已有 21 组成绩再次拆分不能产生此类独立性。
- 缺失：尚未找到的完整层结果先核查是否已存在；确实未完成的才进入补评／补训计划。保留用户已暂停队列的状态，不自动恢复它们。
- 结果：记录每个组合的覆盖率和有效样本，预先保留低覆盖分组为诊断，主分析仍使用同一 80% 门槛；不用新成绩决定剔除哪些模型。

## 3. 优先完成的既有证据补全

这是扩大既有开发集证据，不等于新的独立确认。

| 组合 | 本地缺合格结果的层 | 对方向项判断的作用 |
|---|---|---|
| EVQA × InstructBLIP | L9 | 1 个层即可补全该组双方 Top-3，是最小单组缺口 |
| EVQA × LLaVA | L2、L3 | 补齐两种规则分歧层 |
| MMKE-visual × LLaVA | L5、L6 | 补齐纯范数差异层 |
| MMKE-entity × LLaVA | L0、L1、L6、L11、L12、L13 | 两个候选集合均需核验／补全 |

共 11 个层位置，应优先查证现有服务器结果，不应直接等同于 11 次新训练。MMKE-visual × PaliGemma 的 L3/L5 仅 stable 配置，需同配置结果才能入表；该组两种规则候选集合相同，不能提供方向差异证据。MMKE-entity × BLIP2 还需解决正式归档梯度低覆盖的问题，补几层成绩不能修复这一点。

2026-09-25 修正补全建议：PaliGemma 同配置比较允许采用明确记录的普通 stable 协议。对上述两个公式的 Top-3，最小补全改为 stable L4，复用已完成的 stable L3/L5；不要求强行重跑主配置 L3/L5。需匹配完整训练/评测协议并单独汇总，暂不改变旧统计。该历史数据补全不属于新的独立确认实验。

## 4. 真正独立确认的入口

优先寻找同任务分布、同字段协议、从未使用的新编辑请求。数据进入确认实验前，建立请求清单、实体／图片／问题去重报告，并对照既有训练、代理、验证和测试清单记录交集。数据来源、许可和标签构造必须可追溯。新模型／新任务也是外部验证途径，但若未保证新请求未参与训练／调参，仍需分别披露。

最初可先跑小样本检查图像、目标 token、视觉掩码与生成接口，此阶段仅验证实现，不能据其效果反复筛选正式数据。独立评测的样本量应根据预先指定的最小有意义差异、开发集方差及可用实体数量确定，不把任意数量的样本宣称为充分功效。

本轮尚缺：新请求文件及其使用历史；可复用／需补跑的 checkpoint 清单；独立评测的固定验证／测试划分与样本量。以上落实后才能填写正式冻结清单及启动确认实验。现有 955 条 L0 诊断来自原有 benchmark 评测范围，且只有一个候选层，不能代替该步骤。

## 5. 评分、真实案例与不确定性

1. 延续历史五项指标便于比较，但同步保存各分项、逐样本结果和真正的编辑前预测。不要用参考答案冒充编辑前模型输出。
2. 同请求、同生成参数比较未编辑与各候选层：保存完整自由生成、截断标记、EM 与 word-F1。teacher forcing 单独报告。
3. 对全部预先抽取的案例做方法盲审：至少标记“目标主体／实体”“被改属性”“相关知识”“无关知识保持”四个方面；标注员见到的是随机化输出，不是方法名称或分数。人工语义正确性不得由 F1 自动代替。保留成功、失败和评分不一致的例子及明确抽样规则。
4. 以编辑请求／实体为重采样单位，对同一请求的层结果配对 bootstrap；一个请求的多条关联问答不可当作相互独立样本。固定组合等权汇总。若要声称跨训练随机性稳定，需要额外重复训练种子；只 bootstrap 固定 checkpoint 的请求，不能估计训练种子的不确定性。
5. 模型架构解释保持检验性质：先按已有模型结构分组，再报告同任务内方向项效果；不能把七模型之间的差异全部归因于架构。至少需要区分视觉接口位置、token 范围、表示维度、梯度统计和编辑器训练差异。

## 6. 结果出来后的决策规则

- 主公式在独立主终点上有一致且有实际意义的优势，且不是以其他编辑分项恶化为代价：保留作为主版本，按实际证据限定范围。
- 仅某些预先定义条件有效：报告交互／分组结果；新提出的适用规则需要另一批验证，不回头按结果给模型分组以包装胜利。
- 两者近似或纯范数更好：优先采用证据充分的简单规则，主公式保留为消融。现有“视觉编辑接口定位”的研究价值不依赖方向项必须获胜。

本协议不保证预设方法取胜，而是让无论哪种结果都能被清楚、可复查地解释。
"""
(OUT / "独立确认实验_冻结协议草案.md").write_text(protocol, encoding="utf-8")

# Direct case table for every changed and fully comparable group: show the
# prediction rank and real outcome together, including failures and overlap.
raw_scores = list(csv.DictReader((OUT / "layer_scores.csv").read_text(encoding="utf-8-sig").splitlines()))
outcomes = list(csv.DictReader((ROOT / "outputs/visual_lga_vs_main_20260925/verified_outcomes_with_flags.csv").read_text(encoding="utf-8-sig").splitlines()))
case_layers = []
for r in diff:
    ds, model = r["dataset"], r["model"]
    selected = {int(l[1:]) for key in ("main_candidates", "comparator_candidates") for l in r[key].split(",")}
    for l in sorted(selected):
        a = next(x for x in raw_scores if (x["dataset"], x["model"], int(x["layer"]), x["method"]) == (ds, model, l, "main_abs_cos_new_norm"))
        b = next(x for x in raw_scores if (x["dataset"], x["model"], int(x["layer"]), x["method"]) == (ds, model, l, "new_norm_only"))
        y = next(x for x in outcomes if (x["dataset"], x["model"], int(x["layer"])) == (ds, model, l))
        assert not y["clean_exclusion"]
        case_layers.append(dict(dataset=ds, model=model, layer=l, main_score=a["score"], main_rank=a["rank"],
                                new_norm_score=b["score"], new_norm_rank=b["rank"], actual_average=y["average"],
                                eval_samples=y["eval_samples"], outcome_source=y["source"], source_line=y["source_line"]))
with (OUT / "changed_candidate_cases_layer_evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(case_layers[0]))
    w.writeheader()
    w.writerows(case_layers)

manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "artifact_sha256.json"}
(OUT / "artifact_sha256.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(dict(reports=["主公式实证核验报告.md", "真实案例核验.md", "独立确认实验_冻结协议草案.md"],
                      selected_cases=[r["source_record_index"] for r in CASES], changed_group_layer_rows=len(case_layers)), ensure_ascii=False))
