"""Render the completed local audit; no mutation of the sweep ledger."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/visual_track_metric_audit_20260929"
REPORT = ROOT / "md/Location/VisualTrackCos_三版本_分指标相关性分析_排除PaliGemma_20260929.md"
DATA = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
DS = ["evqa-pilot500", "mmke-visual", "mmke-entity"]
MODELS = ["blip2-opt-2.7b", "instructblip-vicuna-7b", "minigpt-4-vicuna-7b", "llava-v1.5-7b", "qwen2.5-vl-3b", "smolvlm-1.7b"]
SHORT = dict(zip(MODELS, ["BLIP2", "InstructBLIP", "MiniGPT4", "LLaVA", "Qwen2.5-VL", "SmolVLM"]))
VARIANTS = ["none", "alt", "model_pred"]
METRICS = ["Rel", "T-Gen", "M-Gen", "M-Loc", "Average"]
PRIMARY = DATA["primary"]


def readcsv(name):
    return list(csv.DictReader((OUT / name).open(encoding="utf-8-sig")))


def pick(rows, **kw):
    rr = [r for r in rows if all(r[k] == v for k, v in kw.items())]
    assert len(rr) == 1, (kw, len(rr))
    return rr[0]


def fmt(x, digits=3, signed=False):
    if x is None or x == "":
        return "—"
    return format(float(x), ("+" if signed else "") + f".{digits}f")


def lset(x):
    ll = json.loads(x) if isinstance(x, str) else x
    if not ll:
        return "无"
    chunks = []
    lo = hi = ll[0]
    for l in ll[1:] + [None]:
        if l is not None and l == hi + 1:
            hi = l
            continue
        chunks.append(f"L{lo}" if lo == hi else f"L{lo}–L{hi}")
        lo = hi = l
    return "、".join(chunks)


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|"+"---|"*len(headers)] +
                     ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def metric_row(ds, model, variant, metric):
    return pick(PRIMARY, dataset=ds, model=model, variant=variant, metric=metric)


def figures():
    # Optional runtime dependency lives outside the repository.
    sys.path.insert(0, "C:/Users/zhoun/AppData/Local/Temp/codex-vtrack-mpl-20260929")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10})
    groups = [(ds, m) for ds in DS for m in MODELS]
    fig, axes = plt.subplots(1, 3, figsize=(17, 9.4), sharey=True, layout="constrained")
    for ax, variant in zip(axes, VARIANTS):
        matrix = np.array([[metric_row(ds,m,variant,metric)["rho"] for metric in METRICS] for ds,m in groups])
        im = ax.imshow(matrix, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
        ax.set_title(variant, fontweight="bold", pad=10)
        ax.set_xticks(range(5), METRICS)
        ax.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)
        ax.set_yticks(range(18), [f"{ds.replace('evqa-pilot500','E-VQA')} / {SHORT[m]}" for ds,m in groups])
        for i, (ds,m) in enumerate(groups):
            for j, metric in enumerate(METRICS):
                r = metric_row(ds,m,variant,metric)
                star = "*" if r["q_bh"] < .05 else ""
                ax.text(j,i,f"{r['rho']:.2f}{star}",ha="center",va="center",fontsize=9,
                        color="white" if abs(r["rho"])>.6 else "#18212a")
        for boundary in [5.5,11.5]:
            ax.axhline(boundary,color="white",linewidth=2)
    fig.colorbar(im,ax=axes,shrink=.6,label="Within-group Spearman rho")
    fig.suptitle("VisualTrack cosine vs editing outcomes | PaliGemma excluded\n18 groups, 349 main-recipe layer results; raw cosine, matched sample cohort", fontsize=15)
    fig.supxlabel("* Exploratory permutation p adjusted by BH < 0.05 (270 tests). T-Loc is constant in every group.", fontsize=10)
    fig.savefig(OUT / "correlation_heatmap.png",dpi=170)
    fig.savefig(OUT / "correlation_heatmap.pdf")
    plt.close(fig)


def main():
    peaks = readcsv("peak_regions.csv")
    coverage = readcsv("coverage.csv")
    tops = readcsv("top3_per_metric.csv")
    sensitivity = readcsv("correlations.csv")
    pieces = ["# 三版视觉表征相似度与真实编辑效果的分指标分析（排除 PaliGemma）\n",
        "本分析使用 [SWeeplayers.md](SWeeplayers.md) 当前链接的 **2026-09-28T11:10:16+08:00** 扫层快照，完成日期为 2026-09-29。所有 PaliGemma 记录均排除；只比较 main 配方。共 **18 个模型×数据集组合、349 条逐层实测结果**。结果反映这份冻结台账，不代表此后服务器新增的扫层结果。\n",
        "**主要发现：有相关性，但当前最明确的是若干组合中的负相关，而非相似度越高、Rel/Gen 越好。** 三版的组内 Rel/T-Gen/M-Gen 相关系数跨组合均值约为 −0.29 至 −0.33；没有经本次多重比较校正后显著的 Rel/Gen 正相关。内部峰附近存在一个局部正例，但样本覆盖不足，尚不支持通用选峰规则。\n",
        "## 1. 比较的对象与统计口径\n",
        "- none：图文提示结束处的预测位置，与同层视觉 token 平均表征求余弦。\n- alt：新答案全部有效预测位置的余弦在样本内平均，再对样本等权平均。\n- model_pred：原始图文输入对应的模型历史完整输出缓存，按全部可用答案预测位置同样聚合。缓存若曾截断，不补造后续文本。\n- alt/model_pred 不是仅首 token，也不是读完答案 token 之后的状态；预测 y_t 使用位置 P−1+t。这里比较的是表征相似度，不是新旧梯度之间的方向余弦。\n- 主分析用 `matched_gradient`，三版使用同一组可比样本；只有 BLIP2×MMKE-entity 为 284/636（44.65%），其余组合的样本覆盖率均不低于80%（例如BLIP2×E-VQA为465/500），并非全部100%。另做 `available_train` 敏感性分析，该口径下 BLIP2×MMKE-entity 的 none/alt 为 636，model_pred 仍为 284，不能称为三版同样本比较。\n- 在每个模型×数据集内，将完整相似度曲线与实测层交集对齐，计算 Spearman ρ。没有把不同模型的原始分数混在一起算单个相关系数。下文“平均ρ”是18个组内ρ的等权算术均值，不是合并样本的ρ。\n- 主分析保留 raw 有符号余弦；未因编辑分数高低删除层。另报告余弦分数的 Tukey κ=1 敏感性分析，与 LGA 梯度分数的异常层过滤不是同一对象。\n- 按层进行 19,999 次双侧随机置换，固定种子 20260929；270 个可计算的主检验统一做 BH 校正。层之间存在结构依赖，且扫层集合并非随机抽样，因此 p/q 仅为探索性指标，不能当成独立留出验证或因果证据。\n- 对两变量的秩分别回归层号秩，再计算残差相关，作为控制层深的一阶诊断；不等于排除所有非线性架构因素。若相似度秩与层号秩完全重合，残差方差为零，偏相关记“—”。\n- Rel 是编辑可靠性，T-Gen 是文本改写泛化，M-Gen 是图像改写泛化，T-Loc/M-Loc 是文本/图像局部性。Average 沿用五项均值，保留台账历史舍入值。相关性分析的观测单位是“层”，不是349个独立训练种子，也不是逐样本编辑成功率。\n",
        "## 2. 三版与各项指标的总体关系\n"]
    rows=[]
    for metric in METRICS+["T-Loc"]:
        rr=[pick(DATA["summary"],scope="all18",variant=v,metric=metric) for v in VARIANTS]
        rows.append([metric]+[fmt(r["mean_rho"]) for r in rr]+[" / ".join(str(r["positive"]) for r in rr)," / ".join(str(r["q05_positive"]) for r in rr)])
    pieces += [table(["指标","none 平均ρ","alt 平均ρ","model_pred 平均ρ","正相关组数 none/alt/model_pred","q<.05 正相关组数"],rows),
        "\nT-Loc 在全部349条主分析记录里均为100，故54个对应检验的ρ未定义，不能解释为ρ=0。Rel/Gen 的均值呈弱负相关，部分单组则很强；负相关意味着相似度高的实测层通常编辑分数更低。本文仅用 |ρ|≥0.6 标识较强关联，用于描述而非普适显著性阈值。\n",
        "![各组合、版本与指标的相关系数](../../outputs/visual_track_metric_audit_20260929/correlation_heatmap.png)\n",
        "## 3. 相关性具体出现在哪里\n"]
    casekeys=[("mmke-visual","minigpt-4-vicuna-7b","none"),
              ("evqa-pilot500","instructblip-vicuna-7b","alt"),
              ("mmke-entity","llava-v1.5-7b","model_pred"),
              ("evqa-pilot500","smolvlm-1.7b","model_pred"),
              ("mmke-entity","instructblip-vicuna-7b","alt")]
    rows=[]
    for ds,m,v in casekeys:
        rr=[metric_row(ds,m,v,metric) for metric in ["Rel","T-Gen","M-Gen"]]
        rows.append([ds,SHORT[m],v,rr[0]["n_layers"]]+[fmt(r["rho"]) for r in rr]+[" / ".join(fmt(r["rho_partial_depth"]) for r in rr)])
    pieces += [table(["数据集","模型","版本","层数","Rel ρ","T-Gen ρ","M-Gen ρ","控制层深后 Rel/T-Gen/M-Gen"],rows),
        "\n这些案例在结果计算后选取，用于展示正负方向与控制层深的差别，并非独立确认集。完整54组结果见后文。\n",
        "**强负相关且控制层深后仍保留的例子**：MiniGPT4×MMKE-visual 的 none，与 T-Gen/M-Gen 均约 −0.873，控制层深后仍约 −0.63；InstructBLIP×E-VQA 的 alt 与 T-Gen 为 −0.861，控制层深后为 −0.851。这些关系不能简单归结为一个共同的单调深度趋势。\n",
        "**强相关但与层深混在一起的例子**：LLaVA×MMKE-entity 的 none/model_pred 在已测10层上，相似度排序恰与层深排序一致（ρ=1），与 Rel/T-Gen 约 −0.891、M-Gen 约 −0.900；无法凭这些层区分“相似度解释力”和“层深解释力”。\n",
        "**正相关存在，但未形成可靠的编辑/泛化预测规则**：InstructBLIP×MMKE-entity 的 alt 与 Rel/T-Gen/M-Gen 分别约 +0.394/+0.423/+0.402，校正后 q 分别约0.139/0.112/0.133；控制层深后均转为轻微负值。\n",
        "**唯一达到 |ρ|≥0.6 且 q<.05 的正相关**是 InstructBLIP×E-VQA、none 与 M-Loc：ρ=+0.696，q≈0.021；它对应的是图像局部性，而非编辑可靠性或泛化。相似度和 M-Loc 都随层深增长，控制层深后ρ=−0.105，故不能说找到了独立有效的 M-Loc 预测因子。\n",
        "## 4. 是否被三个数据集混合掩盖\n"]
    rows=[]
    for ds in DS:
        for v in VARIANTS:
            rows.append([ds,v]+[fmt(pick(DATA["summary"],scope=ds,variant=v,metric=m)["mean_rho"]) for m in ["Rel","T-Gen","M-Gen","M-Loc","Average"]])
    pieces += [table(["数据集","版本","平均 Rel ρ","平均 T-Gen ρ","平均 M-Gen ρ","平均 M-Loc ρ","平均 Average ρ"],rows),
        "\nMMKE-visual 的六个模型，在三版中与 Rel/T-Gen/M-Gen 均为负相关；MMKE-entity 则模型差异明显，既有 LLaVA 的强负相关，也有 InstructBLIP、SmolVLM 等的轻微或中等正相关。**数据集差异确实会影响合并均值，但拆开后仍未发现“高相似度普遍意味着高 Rel/Gen”的模式。** 这些现象也不足以直接决定整类任务都改用相反排序。\n",
        "## 5. 峰值区间能否选到更好的编辑层\n",
        "本次在读取编辑效果前固定两个定义，均在完整相似度曲线上选择，不能先删掉未扫层再找峰：\n\n1. **全局峰高值区间**：令 z_l=(c_l−min c)/(max c−min c)，取包含全局最大值的 z_l≥0.90 连续区间。并检查0.80/0.95阈值。极值相同取较浅层。\n2. **最高内部局部峰 ±1**：排除两端，找高于两侧的局部峰，取相似度最高者及前后各一层；平顶峰取中点。选择只依据相似度，不依据编辑分数。\n\n区间效果定义为“区间内实测指标均值 − 同组合区间外已测层均值”，单位是百分点。它不是相对未编辑模型的提升，也不是保证与最优层相等。完整性要求区间内每层都已有评测；其余只保留局部覆盖诊断，不能报成完整区间结果。0.90是探索性规则而非已验证最优阈值。\n"]
    rows=[]
    for rule in ["global_90","interior_pm1"]:
        for v in VARIANTS:
            rr=[pick(DATA["peak_summary"],rule=rule,variant=v,metric=m) for m in ["Rel","T-Gen","M-Gen","M-Loc","Average"]]
            rows.append([rule,v,f"{rr[0]['n_complete']}/18"]+[fmt(r["mean_delta_pp"],2,True) for r in rr]+[f"{rr[0]['wins']}/{rr[0]['n_complete']}"])
    pieces += [table(["区间规则","版本","完整组数","ΔRel","ΔT-Gen","ΔM-Gen","ΔM-Loc","ΔAverage","Rel 高于区间外组数"],rows),
        "\n各版完整组合不同，不能用上表均值直接给三个版本排优劣。全局0.90区间在可完整核验的2/3/3组里，Rel、T-Gen、M-Gen、Average 均低于区间外；内部峰±1也没有一致优势。未完整区间太多，因此结论是“当前没有普遍选峰优势的证据”，不是断言所有未测峰值都无效。\n",
        "### 5.1 具体反例：LLaVA×E-VQA 的相似度最高层 L31\n",
        "三版全局相似度峰均落在 L31，0.90区间均仅含 L31，评测完整。以下对比 L31 与其余15个已测层的均值：\n"]
    rows=[]
    for metric in METRICS:
        r=pick(peaks,dataset="evqa-pilot500",model="llava-v1.5-7b",cohort="matched_gradient",variant="none",rule="global_90",metric=metric)
        rows.append([metric,fmt(r["mean_inside"],2),fmt(r["mean_outside"],2),fmt(r["delta_pp"],2,True)])
    pieces += [table(["指标","峰层 L31","其余实测层均值","差值（百分点）"],rows),
        "\n这个例子中，相似度最高处的 **M-Loc 更高，但 Rel 和两种 Gen 明显更低**。高局部性说明图像局部性评测中的原有响应保持得更多，不能据此声称新知识编辑成功。仅看一条曲线或一个综合 Average 会掩盖这种指标差异。\n",
        "### 5.2 局部正例：BLIP2×MMKE-entity 的 alt/model_pred 内部峰 L3\n",
        "两版最高内部峰均为 L3，窗口 L2–L4 的三层均已有实测：\n"]
    rows=[]
    for metric in METRICS:
        r=pick(peaks,dataset="mmke-entity",model="blip2-opt-2.7b",cohort="matched_gradient",variant="alt",rule="interior_pm1",metric=metric)
        rows.append([metric,fmt(r["mean_inside"],2),fmt(r["mean_outside"],2),fmt(r["delta_pp"],2,True)])
    pieces += [table(["指标","L2–L4 均值","其余18层均值","差值（百分点）"],rows),
        "\n此处的局部优势确实出现在 **Rel、T-Gen、M-Gen**，均约+4个百分点；M-Loc 约−5.50个百分点，Average 约+1.34个百分点。主口径相似度仅覆盖284/636个样本；将 alt 扩大至全部636个可用样本后，最高内部峰仍为L3，窗口仍为L2–L4，因此该窗口选择对这次样本扩展稳定。model_pred 的可用缓存仍只有284个。整个组合并不呈强单调正相关（主口径 alt：Rel ρ≈+0.092；model_pred≈+0.073）。这支持“这一局部窗口值得独立确认”，尚不能把这个正例推广成普遍规律；样本扩展检验仍复用了同一批编辑评测，并非独立效果验证。完整样本的 alt 敏感性与区间数据保存在附件中。\n",
        "还有一个关键区别：**窗口均值较高，不代表峰顶最佳。** 相似度峰顶L3的Rel为53.51，低于邻层L2的57.81和L4的57.63；已测层的Rel/T-Gen/M-Gen最佳均在L1，分别为57.94/57.91/57.96。L2–L4的窗口优势主要来自邻层，当前证据不支持“越靠近峰顶越好”，也没有命中这些指标的已测最优层。\n",
        "## 6. 稳健性检查与解释\n"]
    rows=[]
    for scope in ["all18","coverage_ge_80pct","available_train_raw","matched_gradient_tukey_k1"]:
        for v in VARIANTS:
            rr=[pick(DATA["summary"],scope=scope,variant=v,metric=m) for m in ["Rel","T-Gen","M-Gen","Average"]]
            rows.append([scope,v,rr[0]["n_groups"]]+[fmt(r["mean_rho"]) for r in rr])
    pieces += [table(["口径","版本","组合数","平均 Rel ρ","平均 T-Gen ρ","平均 M-Gen ρ","平均 Average ρ"],rows),
        "\n移除低覆盖的 BLIP2×MMKE-entity、扩大可用相似度样本、或对相似度施加 Tukey κ=1 后，平均 Rel/Gen 相关性的方向均保持为负，没有逆转成明显正相关。Tukey 会改变层集合，因此与 raw 的强度差不能只归因于公式优劣。\n",
        "三版完整层曲线之间的组内 Spearman 相关性均值：none–alt 为0.918，none–model_pred 为0.923，alt–model_pred 为0.970。它们多数时候给出相近的层排序，这解释了为什么更换答案版本未明显改变总体结论；个别组合（如 InstructBLIP×E-VQA）仍有显著差异。\n",
        "从现有证据可以提出一个机制假设：视觉表征与预测位置表征相近，可能反映层深和跨模态信息融合状态；adapter 的可编辑性还取决于可改变的特征、剩余传播路径与训练优化。相似度本身没有测量这些因素。部分末层能保持局部性，却对新知识注入和泛化不利。**这是对观察结果的解释假设，不是本次相关性分析证明的机制。**\n",
        "因此，暂不建议把“相似度越高”或“选峰”写成通用主公式。可以保留三版作诊断/对照；若要从这些结果进一步找规则，优先检验已经出现、且控制层深后仍保留的组合内负相关，再用未参与选规则的样本或层确认。不能在这批数据上发现负号后就将倒序结果当成独立成功。\n",
        "## 7. 所有模型×数据集×版本的相关系数\n",
        "星号表示本次主检验BH校正q<0.05，仅作探索性标记；完整 p、q、控制层深结果与两种敏感性口径见CSV。T-Loc全部未定义，不重复列出。\n"]
    for ds in DS:
        rows=[]
        for m in MODELS:
            for v in VARIANTS:
                rr=[metric_row(ds,m,v,metric) for metric in METRICS]
                rows.append([SHORT[m],v,rr[0]["n_layers"],str(rr[0]["similarity_samples"])]+[fmt(r["rho"])+("*" if r["q_bh"] < .05 else "") for r in rr])
        pieces += [f"### {ds}\n",table(["模型","版本","已测层数","相似度样本数"]+METRICS,rows),"\n"]
    pieces += ["## 8. 峰值区间及缺失层清单\n",
        "下面的缺失是“该冻结台账里没有该层main评测”，不等同于实时服务器未运行。暂不启动补训。完整区间的判定严格使用所有窗口层，不用少数已测层代替。\n"]
    for ds in DS:
        rows=[]
        for m in MODELS:
            for v in VARIANTS:
                common=dict(dataset=ds,model=m,variant=v,cohort="matched_gradient",metric="Rel")
                r=pick(peaks,**common,rule="global_90")
                s=pick(peaks,**common,rule="interior_pm1")
                rows.append([SHORT[m],v,"L"+r["global_peak"],lset(r["region"]),lset(r["missing_inside"]),lset(s["region"]),lset(s["missing_inside"])])
        pieces += [f"### {ds}\n",table(["模型","版本","全局峰","0.90高值区间","区间缺层","内部峰±1","内部峰窗口缺层"],rows),"\n"]
    pieces += ["## 9. 数据与复现\n",
        "- [完整结果与参数 JSON](../../outputs/visual_track_metric_audit_20260929/analysis.json)\n- [逐层相似度与六项实测指标](../../outputs/visual_track_metric_audit_20260929/aligned_layers.csv)\n- [全部相关性、置换p、BH校正q、控制层深与敏感性结果](../../outputs/visual_track_metric_audit_20260929/correlations.csv)\n- [全部峰值区间及各项指标差值](../../outputs/visual_track_metric_audit_20260929/peak_regions.csv)\n- [三版Top-1/Best@3/Mean@3分指标结果及缺失层](../../outputs/visual_track_metric_audit_20260929/top3_per_metric.csv)\n- [来源和SHA-256清单](../../outputs/visual_track_metric_audit_20260929/source_manifest.json)\n- [分析脚本](../../scripts/audit_visual_track_metric_correlations_20260929.py)\n- [报告与图表脚本](../../scripts/report_visual_track_metric_audit_20260929.py)\n",
        "相似度来源为 `outputs/visual_track_cosine_20260928/targets_v2/results/`；18组 summary 状态均为done，各 protocol/layer_scores/diagnostics 文件通过所登记SHA-256核对。评测来源为台账链接的 `outputs/sweep_ledger_20260928_110311/ledger.json`；同模型、数据集、层、main配方没有重复记录。349条记录中233条为50轮已核验、108条历史验收、8条完成标记但历史未全留存。没有把历史验收说成本次重新训练或重新全量评测。\n",
        "相关系数已与此前存档的同口径结果交叉检查，并用独立的pandas秩相关实现重新计算核对。读取CSV进行精度复核时使用 `float_precision='round_trip'`，避免默认浮点解析改变极近值的并列秩。机器可读结果保留原精度，本文表格做显示舍入。峰值区间0.80/0.95的敏感性结果也在CSV内，无根据结果改阈值。\n"]
    REPORT.write_text("\n".join(pieces),encoding="utf-8")
    if "--no-figures" not in sys.argv:
        figures()
    print(str(REPORT))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
