"""Append six audited cross-model/dataset cases to the user's related-work copy."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/visedit_contribution_cases_20260929"
REPORT = ROOT / "md/Location/related_work.md/贡献度归因与编辑效果不一致_案例分析_20260929.md"
load = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
A = load(OUT / "analysis.json")
ledger_path = ROOT / "outputs/sweep_ledger_20260928_110311/ledger.json"
assert sha(ledger_path) == A["inputs"]["ledger_sha256"]
ledger = load(ledger_path)
pool = {(r["dataset"], r["model"], r["layer"]): r for r in ledger["rows"] if r["recipe"] == "main"}
analyses = {(r["dataset"], r["model"], r["target"], r["module"]): r for r in A["rows"]}
with (OUT / "layer_alignment.csv").open(encoding="utf-8-sig", newline="") as f:
    aligned = {(r["dataset"], r["model"], r["target"], r["module"], int(r["layer"])): r for r in csv.DictReader(f)}
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
MEASURES = ["top1", "best3", "mean3"]
BEGIN, END = "<!-- ADDITIONAL_CONTRIBUTION_CASES_BEGIN -->", "<!-- ADDITIONAL_CONTRIBUTION_CASES_END -->"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
                      + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def link(label, p):
    return f"[{label}](<{(ROOT/p).as_posix()}>)"


def fmt(x, n=3):
    return f"{x:.{n}f}"


def target_label(target):
    return "alt" if target == "alt" else "首预测位置对照"


CASES = [
    dict(name="MiniGPT4 × MMKE-visual：新目标与首预测位置均有峰值反例", ds="mmke-visual", model="minigpt-4-vicuna-7b", ref=15,
         selections=[("alt", "attn", 31), ("alt", "mlp", 28), ("alt", "attn+mlp", 28), ("model_pred", "attn", 26)],
         reason="参照仍为固定中层首选 L15。alt 在此数据集是视觉语义 KeyToken，不是整段新答案归因。",
         comment="alt-attn 的峰值 L31 比 L15 的 Rel、T-Gen、M-Gen 分别低 13.18、13.64、13.12 个百分点，Average 低 7.716。不过 L31 的 EMA loss=7.304613，包含明显的优化困难。更适合作为补充支撑的是首预测位置 attn：其峰值 L26 的 EMA loss=0.788584，L15 为 0.251438；L15 的 Rel、两种 Gen 仍分别高 3.07、3.25、2.81 个百分点，Average 高 1.942。alt 的 MLP/联合峰值 L28 也落后于 L15，Average 差 1.434。",
         pre_note="alt-MLP/联合 Pre 的 Best@3 比 Middle 低 2.024，Mean@3 低 1.936 个百分点，说明反例扩展到了 MMKE-visual 的实际候选规则。首预测位置 MLP/联合的 Pre 与 Middle 候选集合相同、顺序不同，Best@3 与 Mean@3 必须持平，不能把这两行解释为 Pre 失败。"),
    dict(name="LLaVA × MMKE-visual：高贡献层与实际 Pre 候选均落后", ds="mmke-visual", model="llava-v1.5-7b", ref=15,
         selections=[("alt", "mlp", 28), ("alt", "attn+mlp", 28), ("model_pred", "attn", 28), ("model_pred", "attn+mlp", 28)],
         reason="参照为固定中层首选 L15。这里比较的是高贡献层 L28，不是全局峰值：L28 的 alt-MLP/联合排名为第 4/5，首预测位置 attn/联合排名均为第 2。",
         comment="L28 的贡献高于 L15，但 L15 的 Rel、T-Gen、M-Gen 分别高 3.44、3.51、2.92 个百分点，Average 高 2.226；M-Loc 也高 1.26。L28 的 EMA loss=0.996580，L15 为 0.231111。这个案例支持‘高贡献排名不足以保证更好的编辑收益’，不能写成‘最高贡献层被中层击败’。",
         pre_note="alt-MLP 和联合贡献推荐 [28,27,26]，已完整评测；其 Best@3 和 Mean@3 比 Middle 分别低 2.118、2.220 个百分点。这是另一模型在 MMKE-visual 上的 Pre 反例。首预测位置三种 Pre 均缺 L25，不能给它们填入完整三候选成绩。"),
    dict(name="LLaVA × MMKE-entity：存在排序反例，但效应较小", ds="mmke-entity", model="llava-v1.5-7b", ref=15,
         selections=[("model_pred", "attn", 24), ("alt", "mlp", 27), ("alt", "attn+mlp", 27)],
         reason="参照为固定中层首选 L15。首预测位置 attn 的 L24 确为全局峰值；alt 的 L27 分别是 MLP 第 4、联合贡献第 5，二者证据性质不同。",
         comment="L15 相对 attn 峰值 L24，Rel、T-Gen、M-Gen 分别高 1.02、1.04、0.97 个百分点，但 M-Loc 低 1.31，因此 Average 仅高 0.344。相对 alt 高贡献层 L27，三项分别高 1.04、1.10、1.01，Average 高 0.590。L24、L27、L15 的 EMA loss 分别为 0.401128、1.028096、0.272476。它能说明顺序并非严格单调，但差距较小，没有重复种子结果时不宜写成‘显著优于’。",
         pre_note="alt 与首预测位置的 MLP/联合 Pre 都为 [28,27,26]，其 Best@3 比 Middle 低 0.886，Mean@3 低 0.916 个百分点。首预测位置 attn 的 Pre 尚缺 L21、L20，所以峰值反例与该 attn-Pre 的有效性必须分开表述。"),
    dict(name="InstructBLIP × MMKE-entity：三种峰值同层，但整体训练效果受限", ds="mmke-entity", model="instructblip-vicuna-7b", ref=15,
         selections=[("alt", "attn", 30), ("alt", "mlp", 30), ("alt", "attn+mlp", 30)],
         reason="参照为固定中层首选 L15。alt 使用实体 KeyToken；三种模块贡献的全局峰值都落在 L30，因此只对应同一对编辑结果，不能算三次独立实验。",
         comment="L15 的 Rel、T-Gen、M-Gen 比 L30 分别高 3.74、4.31、3.80 个百分点，Average 高 2.360，且贡献排名明显较低。但两层 EMA loss 均高（L30=14.488698，L15=11.116361），Rel 也仅为 11.25 和 14.99。这个组合适合作为‘当前既定配方下贡献峰值并未指出较好位置’的补充现象，不能作为脱离优化状态的主要机制证据，也不能称两层均已收敛。",
         pre_note="alt 三种 Pre 相同，其 Best@3、Mean@3 分别比 Middle 低 1.326、1.622。与此同时，首预测位置 attn-Pre 的 Average Top-1/Best@3/Mean@3 为 48.928/48.928/48.831，略高于 Middle 的 48.844/48.844/48.734；应保留这个相反结果，不能说该组合的所有目标、所有 Pre 规则均失败。"),
    dict(name="BLIP2 × E-VQA：低损失条件下仍有较大差距", ds="evqa-pilot500", model="blip2-opt-2.7b", ref=15,
         selections=[("model_pred", "attn", 29), ("model_pred", "mlp", 25), ("model_pred", "attn+mlp", 26), ("alt", "mlp", 25), ("alt", "attn+mlp", 25)],
         reason="参照为固定中层首选 L15。首预测位置三种贡献度均使用其全局峰值；alt 在本例只展示 MLP/联合峰值，不声称 alt-attn 峰值也失败。",
         comment="首预测位置 attn 的峰值 L29，Rel/T-Gen/M-Gen 为 27.57/25.43/27.64，固定中层 L15 为 66.35/62.89/63.90，差距达到 38.78/37.46/36.26 个百分点；Average 差 22.602。两层 EMA loss 为 0.414155 与 0.336919，并非只依靠极高损失末层构造反例。联合贡献峰值 L26 的 Average 也低 15.496；MLP 峰值 L25 低 2.254，但它的 M-Loc 更高，应保留编辑与局部性的取舍。这个组合特别适合与 MiniGPT4 主案例一起展示。",
         pre_note="Pre 会避开部分较差峰值层，其分差远小于直接选择峰值的分差：两个实际 Pre 集合的 Best@3 均为 74.852，Middle 为 75.192，仅差 0.340；Mean@3 分别低 0.697 和 0.985。不能把直接选峰的 22.602 个百分点差距写成 VisEdit-Pre 的损失。"),
    dict(name="SmolVLM × E-VQA：三种 alt 峰值均弱于另一个固定中层候选", ds="evqa-pilot500", model="smolvlm-1.7b", ref=12,
         selections=[("alt", "attn", 22), ("alt", "mlp", 19), ("alt", "attn+mlp", 22)],
         reason="SmolVLM 有 24 层，固定中层三候选是 [11,12,10]。本例用其中第二候选 L12 展示已完整核验训练历史的成对比较；L12 不是 Middle Top-1，也不是扫层最优层。Top-3 方法比较仍使用原集合 [11,12,10]，不替换 L11。",
         comment="alt-attn/联合峰值 L22 的 Average 为 55.872，MLP 峰值 L19 为 57.308，均低于 L12 的 61.928，分别差 6.056、4.620 个百分点。Rel 与两种 Gen 也全部较低。L22、L19、L12 的 EMA loss 分别为 0.488335、0.381024、0.402297，L19 的训练损失甚至低于 L12，而评测更差。这能排除‘所有反例都只由极端高损失造成’的解释，但不单独证明训练损失与评测脱节的因果机制。",
         pre_note="alt-MLP/联合 Pre 的 Mean@3 分别比 Middle 低 4.041、7.165 个百分点；alt-attn 的 Pre 缺 L18，不能报告完整结果。首预测位置 MLP-Pre 的 Top-1 为 68.220，高于 Middle 的 67.240，但 Best@3、Mean@3 更低，故也不能将结果概括成全部指标一致失败。"),
]

before_bytes = REPORT.read_bytes()
text = before_bytes.decode("utf-8-sig").replace("\r\r\n", "\n").replace("\r\n", "\n")
backup = OUT / "related_work_report_before_extension.md"
if not backup.exists():
    backup.write_bytes(before_bytes)
sections = [BEGIN, "## 6. 新增六组跨模型、跨数据集案例",
            "本节在前述冻结结果上新增六个模型×数据集组合，覆盖 MMKE-visual、MMKE-entity 和 E-VQA。所有成对案例层都重新检查了本地保存的服务器核验记录：main 配方、完整 50 轮历史、选中 checkpoint 与最小 EMA 记录一致、评测样本数一致；同一组合的成对模型配置除 `edit_layers` 外一致。仍排除 PaliGemma，没有补跑训练。\n\n"
            "这些是事后选出的反例，用来否定‘高贡献必然带来好编辑’这一充分条件，不用于估计总体失败率。未将未测全局峰值替换成已测层最大值；排名前几但不是第一的层会明确标注。`首预测位置对照` 始终指现有 `model_pred-NextTokenArgmax`，不是完整旧答案归因。每组归因样本数与编辑评测样本数分别列出，不能混为同一批逐样本配对。"]
audited = {}
case_records = []
summary_rows = []
for i, case in enumerate(CASES, 1):
    ds, model, ref = case["ds"], case["model"], case["ref"]
    ar = [analyses[ds, model, target, module] for target, module, _ in case["selections"]]
    layers = sorted({ref, *(l for _, _, l in case["selections"])})
    norms = set()
    rounding_notes = []
    for layer in layers:
        r = pool[ds, model, layer]
        v = r["verification"]
        assert r["training"] == "50轮已核验" and v["all_50_epochs_present"]
        assert v["evaluation_verified"] and v["minimum_ema_matches"] and not v["errors"]
        assert r["samples"] == v["results_count"] == {"evqa-pilot500": 2093, "mmke-visual": 293, "mmke-entity": 954}[ds]
        norm, n = re.subn(r"(?m)^edit_layers:\n- \d+\n", "edit_layers:\n- LAYER\n", v["model_config_text"])
        assert n == 1
        norms.add(norm)
        mean_paths = {"Rel": ("reliability", "acc"), "T-Gen": ("generality", "text_rephrase", "acc"),
                      "M-Gen": ("generality", "image_rephrase", "acc"), "T-Loc": ("locality", "text_loc", "acc"),
                      "M-Loc": ("locality", "image_loc", "acc")}
        for m in METRICS[:-1]:
            raw_mean = v["mean_results"]
            for field in mean_paths[m]:
                raw_mean = raw_mean[field]
            assert abs(r["metrics"][m]-100*raw_mean) < 1e-8
            diff = abs(r["metrics"][m]-v["recomputed_metrics"][m])
            assert diff <= 0.010000001, (ds, model, layer, m, diff)
            if diff > 1e-8:
                rounding_notes.append(f"L{layer} 的 {m} 在原汇总/台账中为 {r['metrics'][m]:.2f}，逐样本复核汇总为 {v['recomputed_metrics'][m]:.2f}，相差 {diff:.2f} 个百分点")
        assert abs(r["metrics"]["Average"]-sum(r["metrics"][m] for m in METRICS[:-1])/5) < 1e-8
        audited[ds, model, layer] = r
    assert len(norms) == 1
    scoring_rows, comparisons = [], []
    for target, module, high in case["selections"]:
        ah, al = aligned[ds, model, target, module, high], aligned[ds, model, target, module, ref]
        assert float(ah["positive_contribution"]) > float(al["positive_contribution"])
        rank = int(ah["contribution_rank"])
        assert rank <= 5
        delta = {m: pool[ds, model, ref]["metrics"][m]-pool[ds, model, high]["metrics"][m] for m in METRICS}
        assert all(delta[m] > 0 for m in ["Rel", "T-Gen", "M-Gen", "Average"])
        scoring_rows.append([target_label(target), module, f"L{high}（第 {rank}）", fmt(float(ah["positive_contribution"]), 9),
                             fmt(float(al["positive_contribution"]), 9), al["contribution_rank"], f"{delta['Average']:+.3f}"])
        comparisons.append(dict(target=target, module=module, higher_contribution_layer=high, higher_contribution_rank=rank,
                                lower_contribution_layer=ref, delta_lower_minus_higher=delta))
    sample_count = sorted({r["samples"] for r in ar})
    sections += [f"### 6.{i} {case['name']}",
                 f"归因有效样本数：{' / '.join(map(str,sample_count))}；编辑评测样本数：{pool[ds,model,ref]['samples']}。{case['reason']}",
                 table(["目标", "模块", "高贡献层及全局排名", "高层贡献值", f"L{ref} 贡献值", f"L{ref} 排名", f"L{ref} 的 Average 优势"], scoring_rows),
                 table(["层", *METRICS, "选中 EMA loss"],
                       [[f"L{l}" + ("（低贡献参照）" if l==ref else "")]
                        + [fmt(pool[ds,model,l]["metrics"][m]) for m in METRICS]
                        + [fmt(pool[ds,model,l]["ema_loss"],6)] for l in layers]), case["comment"]]
    if rounding_notes:
        sections.append("数值核对说明："+"；".join(rounding_notes)+"。本节统一沿用冻结台账与原 mean_results 的数值，没有择优替换；这一末位精度差异不改变比较方向。")
    # Display every complete Pre rule for this group, including ties and wins;
    # merge identical ordered candidate sets to avoid counting duplicate results.
    aa = [r for r in A["rows"] if r["dataset"] == ds and r["model"] == model]
    by_pre, missing = {}, []
    for r in aa:
        label = target_label(r["target"]) + "-" + r["module"]
        if r["pre_complete"] and r["middle_complete"]:
            key = tuple(r["pre_layers"])
            if key not in by_pre:
                by_pre[key] = [[], r]
            by_pre[key][0].append(label)
        else:
            missing.append(label + " 缺 " + ",".join(f"L{l}" for l in r["pre_missing"]))
    pre_rows = []
    all_pre_layers = set(aa[0]["middle_layers"])
    for key, (labels, r) in by_pre.items():
        pre_rows.append(["；".join(labels), ",".join(map(str,key))] + [fmt(r["pre_performance"]["Average"][k]) for k in MEASURES])
        all_pre_layers.update(key)
        for m in METRICS:
            actual = [pool[ds,model,l]["metrics"][m] for l in key]
            for k, value in zip(MEASURES, [actual[0], max(actual), sum(actual)/3]):
                assert abs(value-r["pre_performance"][m][k]) < 1e-8
    rr = aa[0]
    pre_rows.append(["Middle（固定中层）", ",".join(map(str,rr["middle_layers"]))]
                    + [fmt(rr["middle_performance"]["Average"][k]) for k in MEASURES])
    sections += ["实际候选规则的 Average 比较（相同三层预算；同一候选集合合并展示）：",
                 table(["方法", "有序候选层", "Top-1", "Best@3", "Mean@3"], pre_rows), case["pre_note"]]
    if missing:
        sections.append("未完成的 Pre 覆盖：" + "；".join(missing) + "。这些规则不进入上表。")
    history = [(l, pool[ds,model,l]["training"]) for l in sorted(all_pre_layers) if pool[ds,model,l]["training"] != "50轮已核验"]
    if history:
        sections.append("训练证据层级：上述成对反例层全部通过完整 50 轮核验；Top-3 表还使用了 "
                        + "、".join(f"L{l}（{status}）" for l,status in history)
                        + "，因此该表是完整评测覆盖比较，不代表所有候选训练历史都重新核验。")
    else:
        # Check all candidate layers used for the stronger coverage statement.
        for l in all_pre_layers:
            v = pool[ds,model,l]["verification"]
            assert v["all_50_epochs_present"] and v["evaluation_verified"] and v["minimum_ema_matches"]
        sections.append("训练证据层级：成对反例层和上表使用的全部候选层均有完整 50 轮核验记录。")
    srcs = list(dict.fromkeys(r["source"] for r in aa))
    for src in srcs:
        recorded = next(s["sha256"] for s in A["sources"] if s["source"] == src)
        assert sha(ROOT/src) == recorded
    sections.append("贡献度来源：" + "；".join(link("alt 原始贡献" if "/model_pred/" not in s and "model_pred" not in s else "首预测位置原始贡献",s) for s in srcs) + "。")
    case_records.append(dict(case=case, comparisons=comparisons, pre_results=aa, primary_layers=layers, pre_history_only_layers=history, rounding_notes=rounding_notes))
    delta_values=[c["delta_lower_minus_higher"]["Average"] for c in comparisons]
    summary_rows.append([case["name"].split("：")[0], ",".join("L"+str(l) for l in layers if l!=ref), f"L{ref}",
                         f"{min(delta_values):.3f}–{max(delta_values):.3f}" if min(delta_values)!=max(delta_values) else fmt(delta_values[0])])

sections += ["### 6.7 新增案例如何取舍", table(["组合", "本节比较的高贡献层", "低贡献参照", "参照的 Average 优势（百分点）"], summary_rows),
             "正文建议优先选 **BLIP2 × E-VQA、SmolVLM × E-VQA、MiniGPT4 × MMKE-visual 和 LLaVA × MMKE-visual**，与原 MiniGPT4 × E-VQA 案例共同展示跨模型、跨数据集现象。MMKE-entity 可加入 LLaVA 的小幅反例说明数据集差异；InstructBLIP × MMKE-entity 放入补充分析，并明确其整体训练效果受限。\n\n"
             "比较表支持三个层次的结论：贡献最高层未必最好；即使不是最高层，较高贡献排名也不保证较高 Rel/Gen；高贡献区间之前的 Pre 规则在部分组合上同样落后于固定中层。部分目标下 Pre 持平或有收益、MMKE-entity 部分差距较小，这些事实同时保留。新增案例没有改变总体胜率的统计分母，不能把多个模块/目标复用的同一层评测当成独立重复实验。",
             "新增证据：" + link("六组案例与训练/评测核验记录", "outputs/visedit_contribution_cases_20260929/additional_cases_audit.json")
             + "；" + link("本节复算与写入程序", "scripts/extend_visedit_contribution_cases_20260929.py") + "。", END]
block = "\n\n".join(sections) + "\n\n"
if BEGIN in text:
    start, end = text.index(BEGIN), text.index(END)+len(END)
    text = text[:start]+block.rstrip()+text[end:]
else:
    anchor = "## 6. 全部已存结果的覆盖检查"
    assert text.count(anchor) == 1
    text = text.replace("## 8. 可追溯证据与复算", "## 9. 可追溯证据与复算")
    text = text.replace("## 7. 对论文论证的作用", "## 8. 对论文论证的作用")
    text = text.replace(anchor, block + "## 7. 全部已存结果的覆盖检查")
intro = "**扩充说明：本文件第 6 节已新增 6 个组合案例，涉及 BLIP2、SmolVLM、InstructBLIP、MiniGPT4、LLaVA，以及 E-VQA、MMKE-visual、MMKE-entity；原有案例保留。**\n\n"
text = text.replace(intro, "")
pos = text.index("\n\n")+2
text = text[:pos]+intro+text[pos:]
assert REPORT.read_bytes() == before_bytes, "Report changed during analysis; preserve concurrent edits."
REPORT.write_text(text,encoding="utf-8",newline="\n")
audit = dict(report=REPORT.relative_to(ROOT).as_posix(), report_sha256=sha(REPORT),
             ledger_sha256=sha(ledger_path), analysis_sha256=sha(OUT/"analysis.json"),
             added_case_count=len(CASES), primary_audited_layer_count=len(audited),
             cases=case_records, primary_layer_evidence=list(audited.values()))
(OUT/"additional_cases_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(dict(report=str(REPORT),added_cases=len(CASES),primary_audited_layers=len(audited),summary=summary_rows),ensure_ascii=False))
