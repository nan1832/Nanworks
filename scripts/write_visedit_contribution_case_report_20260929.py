"""Validate selected cases and render an evidence-bound Chinese case report."""
import hashlib
import json
from pathlib import Path
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/visedit_contribution_cases_20260929"
REPORT = ROOT / "md/Location/贡献度归因与编辑效果不一致_案例分析_20260929.md"
load = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
A = load(OUT / "analysis.json")
LEDGER = ROOT / "outputs/sweep_ledger_20260928_110311/ledger.json"
ledger = load(LEDGER)
assert sha(LEDGER) == A["inputs"]["ledger_sha256"]
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
MODULES = ["attn", "mlp", "attn+mlp"]
MINI, LLAVA = "minigpt-4-vicuna-7b", "llava-v1.5-7b"
pool = {(r["model"], r["layer"]): r for r in ledger["rows"]
        if r["recipe"] == "main" and r["dataset"] == "evqa-pilot500"}


def get(model, target, module):
    return next(r for r in A["rows"] if r["dataset"] == "evqa-pilot500"
                and r["model"] == model and r["target"] == target and r["module"] == module)


def link(label, relative):
    return f"[{label}](<{(ROOT / relative).as_posix()}>)"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                       "| " + " | ".join(["---"] * len(headers)) + " |"]
                      + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def fmt(x, places=3):
    return f"{x:.{places}f}"


def metric_row(label, model, layer):
    return [label, f"L{layer}"] + [fmt(pool[model, layer]["metrics"][m]) for m in METRICS]


# Check the stored training/evaluation verification, and compare recorded configs
# without assuming that seed, hardware, or all launch arguments were identical.
audits = []
for model, layers in [(MINI, [14, 15, 16, 24, 25, 26, 28, 30, 31]),
                      (LLAVA, [14, 15, 16, 26, 27, 28, 30])]:
    configs = []
    for layer in layers:
        r = pool[model, layer]
        v = r["verification"]
        assert r["training"] == "50轮已核验" and r["samples"] == 2093
        assert v["all_50_epochs_present"] and v["evaluation_verified"] and v["minimum_ema_matches"]
        assert not v["errors"] and v["results_count"] == 2093
        config, n = re.subn(r"(?m)^edit_layers:\n- \d+\n", "edit_layers:\n- LAYER\n", v["model_config_text"])
        assert n == 1
        configs.append(config)
        for m in METRICS[:-1]:
            assert abs(r["metrics"][m] - v["recomputed_metrics"][m]) < 1e-8
        assert abs(r["metrics"]["Average"] - sum(r["metrics"][m] for m in METRICS[:-1]) / 5) < 1e-8
        audits.append({"dataset": r["dataset"], "model": model, "layer": layer,
                       "metrics": r["metrics"], "selected_epoch": r["epoch"],
                       "selected_ema_loss": r["ema_loss"], "training": r["training"],
                       "config_sha256_except_edit_layers": hashlib.sha256(config.encode()).hexdigest(),
                       "source": r["source"], "verification": v})
    assert len(set(configs)) == 1

# Independently recompute every reported Spearman rho with pandas average ranks.
aligned = pd.read_csv(OUT / "layer_alignment.csv", float_precision="round_trip")
checked_rhos = 0
for r in A["rows"]:
    group = aligned[(aligned.dataset == r["dataset"]) & (aligned.model == r["model"])
                    & (aligned.target == r["target"]) & (aligned.module == r["module"])
                    & aligned.evaluated]
    for m in METRICS:
        x, y = group.positive_contribution, group[m]
        expected = x.rank().corr(y.rank()) if x.nunique() > 1 and y.nunique() > 1 else None
        actual = r["rho_" + m]
        assert (expected is None and actual is None) or (actual is not None and abs(expected - actual) < 1e-12), (r["dataset"], r["model"], r["target"], r["module"], m, expected, actual)
        checked_rhos += 1

mini = [get(MINI, "alt", m) for m in MODULES]
assert [r["peak_layer"] for r in mini] == [31, 30, 28]
assert all(r["samples"] == 500 and r["pre_layers"] == [26, 25, 24] for r in mini)
assert all(r["pre_complete"] and r["middle_complete"] for r in mini)
pre, middle = mini[0]["pre_performance"], mini[0]["middle_performance"]

parts = []
parts.append("# 贡献度归因与编辑效果不一致：已有扫层实验案例分析\n\n"
             "分析日期：2026-09-29。真实编辑结果使用 2026-09-28T11:10:16+08:00 冻结台账；本次只复算本地已存贡献度与评测结果，没有新增训练。\n\n"
             "**已有实测反例，且 attn、MLP、attn+MLP 三种贡献度都有。最清楚的案例是 MiniGPT4 × E-VQA：三种贡献度的全局最高层都不如固定中层 L15，差距同时出现在 Rel、T-Gen、M-Gen 和 Average。实际 VisEdit-Contrib-Pre 候选在这个组合上也低于相同预算的固定中层候选。**\n\n"
             "这些结果支持的结论是：**高贡献度不是良好编辑位置的充分条件，贡献度及其 Pre 规则不能直接充当编辑适宜性的保证。** 不能将其扩大为所有贡献度归因方法都无效，也不能据此认定第七类梯度公式已优于其他基线。")

parts.append("## 1. 比较口径与证据范围\n\n"
             "本分析排除全部 PaliGemma，仅采用其余 6 个模型 × 3 个数据集的 main 配方，合计 349 条真实层评测。没有混用 stable 或复测择优分数。36 份贡献度来源对应 18 个组合 × 2 种目标口径，每份分出 attn、MLP、attn+MLP，形成 108 条分析记录；它们共享编辑结果，**不是 108 次独立实验**。\n\n"
             "主要案例的贡献度由 500 个归因样本汇总，真实编辑指标来自 2,093 个评测样本。层号从 0 开始，MiniGPT4 和 LLaVA 均为 L0–L31。指标以百分数记录，差值单位为百分点。Rel 为编辑可靠性；T-Gen、M-Gen 为文本与图像泛化；T-Loc、M-Loc 为文本与图像局部性；Average 是这五项的均值。\n\n"
             "归因分数按现有代码口径计算：先对样本的带符号贡献取均值，再截取正值；联合贡献是两个模块的正值之和。具体为 `C_attn=max(0,attn_mean)`，`C_mlp=max(0,mlp_mean)`，`C_joint=C_attn+C_mlp`。三种分数各自独立排序，不能跨模块比较数值尺度。\n\n"
             "必须区分两种选层：①贡献度最高层，是该模型全部层中分数最大的位置（主案例为 32 层）；②现有 VisEdit-Contrib-Pre，是先用窗口 3 平滑，取超过均值加 0.5 倍标准差的高贡献区间，再推荐区间开始位置之前的三层。本报告分别评价二者。没有把最高贡献层冒充 Pre 的推荐。\n\n"
             "E-VQA 的 `alt` 归因针对新答案首 token；本地名为 `model_pred` 的程序实际取原始图文输入末位的下一 token argmax，本文明确标为 **model_pred-NextTokenArgmax（首预测位置对照）**。它不等于对模型完整旧回答的全序列归因。MMKE 的 alt 则沿用其已登记的实体/视觉语义 KeyToken，不能把不同目标口径无说明地混为同一实验。")

parts.append("## 2. 主案例：MiniGPT4 × E-VQA，三种最高贡献层均弱于低贡献中层\n\n"
             "选择固定中层 L15 作参照：它只由网络深度确定，不是查看评测结果后挑出的最优层。三种贡献度的 L15 得分和排名如下。\n\n" +
             table(["贡献类型（alt）", "全局最高贡献层", "该层贡献度", "L15 贡献度", "L15 贡献排名"],
                   [[r["module"], f"L{r['peak_layer']}", fmt(r["peak_score"], 9), fmt(r["middle_score"], 9),
                     f"{r['middle_contribution_rank']}/32"] for r in mini]) +
             "\n\n对应的真实编辑结果：\n\n" +
             table(["选层依据", "层", *METRICS],
                   [metric_row(r["module"] + " 最高贡献", MINI, r["peak_layer"]) for r in mini]
                   + [metric_row("固定中层", MINI, 15)]) +
             "\n\n固定中层 L15 相对最高贡献层的提升（正数表示 L15 更好）：\n\n" +
             table(["比较", *METRICS], [[f"L15 − L{r['peak_layer']}（{r['module']}）"]
                   + [f"{r['middle_minus_peak'][m]:+.3f}" for m in METRICS] for r in mini]) +
             "\n\n三种贡献度都出现了明确的排序反例：**贡献更低的 L15，Rel 和两种 Gen 反而全部更高**，并非仅由 Average 中的局部性权重造成。MLP 案例中 L15 的 M-Loc 也更高；attn 与联合贡献案例中 M-Loc 并非更高，不能声称所有单项指标都支配对方。尤其 L31 的 M-Loc=100 并不抵消其较低的编辑与泛化表现。")

training = [[f"L{l}", pool[MINI, l]["epoch"], fmt(pool[MINI, l]["raw_loss"], 6),
             fmt(pool[MINI, l]["ema_loss"], 6), pool[MINI, l]["training"]] for l in [15, 26, 28, 30, 31]]
parts.append("### 2.1 这不是把未完成训练的层当作差结果\n\n" +
             table(["层", "选中 checkpoint 轮次", "Raw loss", "EMA loss", "训练预算核验"], training) +
             "\n\n主案例、Pre 候选和中层候选共 9 个层的训练历史都覆盖 1–50 轮，选点均通过最小 EMA 记录一致性检查，评测均有 2,093 个结果。9 份归档模型配置去掉唯一变化的 `edit_layers` 后完全一致，使用相同 main 配方，学习率为 1e-4，adapter 中间维度为 1024。这里确认的是登记配置、预算与评测口径一致，没有声称所有运行的随机种子或硬件完全一致。\n\n"
             "**训练完成不等于收敛。** L31 的选中 EMA loss=10.222642 明显高于其他层，所以该 attn 反例包含末层优化困难，不能将差距完全归因于贡献度排序本身。MLP 的 L30 和联合贡献的 L28 则没有同类高损失现象，仍然落后于 L15；下一节还有 attn 在较低损失层上的补充反例。以上不构成多随机种子显著性检验。")

parts.append("### 2.2 层级排序关系也没有呈现‘贡献越高越好’\n\n"
             "在该组合当前已扫的 21 层上，将贡献度与各层实测指标逐层对齐，得到描述性 Spearman 相关系数：\n\n" +
             table(["贡献类型（alt）", "Rel ρ", "T-Gen ρ", "M-Gen ρ", "Average ρ"],
                   [[r["module"]] + [fmt(r["rho_" + m]) for m in ["Rel", "T-Gen", "M-Gen", "Average"]] for r in mini]) +
             "\n\n这说明反例不只来自挑选一对层；该组合已测层上的整体排序同样不支持正向对应。其中联合贡献与 Average 的 ρ=-0.530，与 Rel、两种 Gen 也均为负。但已扫 21 层不是随机采样，也不是全部 32 层，这里不报告统计显著性、不外推未测层，也不据此反向制定‘专挑最低贡献层’的规则。T-Loc 在这些层上恒为 100，其相关系数无定义。")

parts.append("## 3. 实际 Pre 规则是否仍有效：相同 Top-3 预算的检验\n\n"
             "MiniGPT4 × E-VQA 的 alt 三种贡献度最终都给出 **Pre=[L26,L25,L24]**；固定中层候选为 **Middle=[L15,L16,L14]**。两边三层均已完成评测，没有缺层补零，也没有从其他层替换候选。三种 Pre 集合相同，因此下表是同一组编辑结果，不能当作三次独立胜负。\n\n" +
             table(["候选集合", "Average Top-1", "Average Best@3", "Average Mean@3"],
                   [[name] + [fmt(perf["Average"][k]) for k in ["top1", "best3", "mean3"]]
                    for name, perf in [("Pre：26,25,24", pre), ("Middle：15,16,14", middle)]]
                   + [["Middle − Pre"] + [f"{middle['Average'][k]-pre['Average'][k]:+.3f}" for k in ["top1", "best3", "mean3"]]]) +
             "\n\nTop-1 取候选首层；Best@3 取三个候选的最高 Average；Mean@3 是三个候选 Average 的均值。进一步分开看 Mean@3：\n\n" +
             table(["指标", "Pre Mean@3", "Middle Mean@3", "Middle − Pre"],
                   [[m, fmt(pre[m]["mean3"]), fmt(middle[m]["mean3"]),
                     f"{middle[m]['mean3']-pre[m]['mean3']:+.3f}"] for m in METRICS]) +
             "\n\n**这个案例直接说明了贡献度驱动的 Pre 推荐也可能失效。** 其三层最好的 Average 为 58.466，仍比固定中层三候选的最好值 64.938 低 6.472 个百分点；Mean@3 低 6.335 个百分点。差距同时涉及 Rel 与 Gen，不是单纯牺牲局部性换取编辑成功率。")

old = [get(MINI, "model_pred", m) for m in MODULES]
parts.append("## 4. 补充反例：首预测位置贡献，不只发生在高损失末层\n\n"
             "对同一 MiniGPT4 × E-VQA 组合，改用 `model_pred-NextTokenArgmax` 首预测位置贡献，attn 与 attn+MLP 的最高贡献位置均变为 L26，MLP 仍为 L30。归因样本仍为 500。\n\n" +
             table(["贡献类型", "最高贡献层", "峰值贡献度", "L15 贡献度", "L15 排名", "峰值层 Average", "L15 − 峰值 Average"],
                   [[r["module"], f"L{r['peak_layer']}", fmt(r["peak_score"], 9), fmt(r["middle_score"], 9),
                     f"{r['middle_contribution_rank']}/32", fmt(r["peak_evidence"]["metrics"]["Average"]),
                     f"{r['middle_minus_peak']['Average']:+.3f}"] for r in old]) +
             "\n\nL26 的 EMA loss 为 0.374355，Rel/T-Gen/M-Gen 分别为 39.33/34.25/36.79；L15 分别为 49.54/46.31/46.96，提升 **10.21/12.06/10.17** 个百分点，Average 提升 **6.802** 个百分点。这给出了不依赖 L31 高损失异常的 attn 反例。它复用同一套扫层结果，是另一种归因目标的检验，不是新增独立训练。该目标部分 Pre 候选尚缺真实评测，本节只评价已测峰值层，不补造 Pre 总分。")

lr = get(LLAVA, "alt", "attn+mlp")
parts.append("## 5. 跨模型补充与边界：LLaVA × E-VQA\n\n"
             "LLaVA 的 alt-MLP 与 alt-attn+MLP 最高贡献位置都为 L30，贡献度分别为 0.448895527 与 0.471731257。固定中层 L15 在这两种贡献度中分别排第 26/32、27/32。\n\n" +
             table(["选层依据", "层", *METRICS], [metric_row("MLP/联合贡献最高", LLAVA, 30), metric_row("固定中层", LLAVA, 15)]) +
             "\n\nL15 的 Rel、T-Gen、M-Gen、Average 分别高 **2.59、1.13、4.93、3.386** 个百分点，M-Loc 也高 8.28 个百分点。L30 与 L15 均有完整 50 轮记录，EMA loss 分别为 0.531518 与 0.366532；同样不是只比较未完成训练层。\n\n"
             "不过，这个组合的实际 Pre=[L28,L27,L26] 有部分收益，必须保留：\n\n" +
             table(["候选集合", "Average Top-1", "Average Best@3", "Average Mean@3"],
                   [[name] + [fmt(p["Average"][k]) for k in ["top1", "best3", "mean3"]]
                    for name, p in [("Pre：28,27,26", lr["pre_performance"]), ("Middle：15,16,14", lr["middle_performance"])]]) +
             "\n\nPre 的 Top-1 和 Mean@3 略高于 Middle，Best@3 则较低。它的 Mean@3 中 Rel、T-Gen 较高，但 M-Gen、M-Loc 较低。因此，不能从 MiniGPT4 反例进一步宣称 Pre 在所有模型、所有指标上都无效。更准确的问题是：**贡献排序、高贡献区间与实际编辑收益之间缺少稳定的一致对应。**")

parts.append("## 6. 全部已存结果的覆盖检查\n\n"
             "为避免只展示一个失败组合，下表统计 18 个非 PaliGemma 组合中，真实全局峰值层与固定中层首选都已有评测，且中层贡献严格更低的组合。‘中层全胜/峰值全胜’均要求 Rel、T-Gen、M-Gen、Average 四项同时更高；剩余组合为混合表现或含持平。\n\n" +
             table(["目标", "模块", "可比组合/18", "低贡献中层四项全胜", "高贡献峰值四项全胜"],
                   [["alt" if s["target"] == "alt" else "首预测位置对照", s["module"],
                     f"{s['middle_comparable']}/18", s["middle_beats_peak_all_rel_gen_avg"],
                     s["middle_loses_to_peak_all_rel_gen_avg"]] for s in A["summary"]]) +
             "\n\n各行可比组合不同，归因目标和模型/数据集也有差异；不能合并这些行当作独立样本总胜率，也不能按这些分母直接给模块排名。该表用于展示已存在的反例及相反案例。峰值层未测的组合不纳入分母，未用‘已测层中最高贡献’偷换‘全局最高贡献’。汇总统计还含部分历史验收层，主案例和 LLaVA 补充案例则均逐层通过完整训练记录核验。")

parts.append("## 7. 对论文论证的作用\n\n"
             "直觉上，贡献度衡量当前前向计算中某层模块对所选输出目标的贡献，而本实验需要选择的是：在哪个视觉表征接口训练 adapter，能够取得可靠、可泛化且保持局部性的编辑效果。两者目标不同。末层贡献集中可能反映输出形成过程，却不保证该层适合通过当前 adapter 与训练预算实现修改；现有层间差异支持研究这一错位，但还没有单独隔离其因果机制。\n\n"
             "第三章可以据此提出‘预测贡献与编辑位置适宜性存在差异’，再分别展示峰值排序反例和实际 Pre 候选失效。后续第七类十个梯度公式仍需与前六类方法按相同候选预算、相同可比组合比较，不能凭本案例预先认定胜者。当前证据已足够撰写这一动机案例，无需为了建立反例追加视觉表征相似性实验或重跑上述层。\n\n"
             "### 可用于论文的表述\n\n"
             "> 已有扫层结果表明，预测贡献与编辑位置适宜性并不必然一致。以 MiniGPT4 在 E-VQA 上的实验为例，注意力、MLP 及二者联合贡献的最高层分别为第 31、30 和 28 层，其编辑后 Average 分别为 54.674、57.842 和 58.362，均低于贡献排名较低的固定中层第 15 层（64.070），且可靠性与两类泛化指标也一致较低。在相同三层候选预算下，由高贡献区间生成的 Pre 候选 Best@3 为 58.466，低于固定中层候选的 64.938。这些结果说明，仅依据当前预测贡献及其高贡献区间选择编辑位置，不能保证获得较好的编辑效果，仍需以实际编辑结果验证定位信号的适用性。\n\n"
             "论文使用时应同步保留主实验设置与训练状态说明；不得将这些组合层面的平均结果称为逐样本编辑成功/失败案例，也不得写成完整旧回答归因。若需要展示某张图、某个问题与编辑前后具体答案，需要另取对应逐样本记录，本文未伪造此类内容。")

source_links = [
    ("真实扫层台账", "md/Location/SWeeplayers.md"),
    ("真实编辑机器可读记录", "outputs/sweep_ledger_20260928_110311/ledger.json"),
    ("MiniGPT4 新目标贡献原表", mini[0]["source"]),
    ("MiniGPT4 首预测位置贡献原表", old[0]["source"]),
    ("LLaVA 新目标贡献原表", lr["source"]),
    ("E-VQA 贡献计算程序", "VisEdit-main/scripts/run_evqa_module_contribution_pilot500_multi.py"),
    ("Pre 高贡献区间与候选计算程序", "VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py"),
    ("本次分析程序", "scripts/analyze_visedit_contribution_cases_20260929.py"),
    ("本报告生成与交叉校验程序", "scripts/write_visedit_contribution_case_report_20260929.py"),
    ("完整分析结果及原始来源哈希", "outputs/visedit_contribution_cases_20260929/analysis.json"),
    ("逐层贡献—编辑指标对齐表", "outputs/visedit_contribution_cases_20260929/layer_alignment.csv"),
    ("逐指标相关系数", "outputs/visedit_contribution_cases_20260929/correlations.csv"),
    ("完整 Pre 与 Middle 比较", "outputs/visedit_contribution_cases_20260929/pre_vs_middle.csv"),
    ("案例训练/评测证据审计", "outputs/visedit_contribution_cases_20260929/case_audit.json"),
]
parts.append("## 8. 可追溯证据与复算\n\n" + "\n".join("- " + link(label, path) for label, path in source_links)
             + "\n\n原贡献度 CSV 的 SHA-256 已逐份对照候选层汇总输入清单；现有推荐表中可比模块的完整排名与 Pre 候选也已做一致性校验。相关系数另用 pandas 平均秩重算，验证 648 个‘模块×目标×组合×指标’单元（包括常数指标无定义单元）。本报告没有查询或改变实时服务器状态。")

REPORT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
audit = {"report": REPORT.relative_to(ROOT).as_posix(), "report_sha256": sha(REPORT),
         "analysis_sha256": sha(OUT / "analysis.json"), "ledger_sha256": sha(LEDGER),
         "checked_spearman_cells": checked_rhos, "selected_case_evidence": audits,
         "config_comparison": "Within each selected model, recorded model_config_text identical except edit_layers.",
         "limitations": ["No new seed repeats or causal ablation.", "Frozen local ledger; no live server status claim.",
                         "model_pred is next-token argmax, not attribution across a complete old answer."]}
(OUT / "case_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"report": str(REPORT), "audited_layers": len(audits),
                  "checked_rhos": checked_rhos, "report_chars": len(REPORT.read_text(encoding='utf-8'))}, ensure_ascii=False))
