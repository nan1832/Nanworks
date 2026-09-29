"""Audit existing layer-score correlations and report each evaluation component.

Reads the frozen September 28 inputs; does not train, rescore recommendations,
change candidate sets, or mix stable and main results.
"""
import collections
import csv
import hashlib
import itertools
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs/all_methods_performance_20260928"
OUT = ROOT / "outputs/component_metric_correlations_20260928"
OUT.mkdir(exist_ok=True)
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
POLICIES = ["observed_main", "main_without_flagged", "verified50_main", "stable_only"]

def read(name):
    with (SRC / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def jread(name):
    return json.loads((SRC / name).read_text(encoding="utf-8-sig"))

def write(name, rows):
    if not rows:
        return
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def rho(x, y):
    # Independent midrank implementation (pair counting rather than sorted runs).
    def rank(v):
        return [1 + sum(z < t for z in v) + (sum(z == t for z in v) - 1) / 2 for t in v]
    if len(x) < 2:
        return None
    a, b = rank(x), rank(y)
    ma, mb = st.mean(a), st.mean(b)
    denominator = math.sqrt(sum((t-ma)**2 for t in a) * sum((t-mb)**2 for t in b))
    return sum((s-ma)*(t-mb) for s,t in zip(a,b)) / denominator if denominator else None

def flagged(r):
    status = (r.get("status", "") + " " + (r.get("original_status") or "")).upper()
    return r["training"] == "恢复/诊断评测" or any(t in status for t in ["NUMERIC", "NONFINITE", "NONCONVERGENT"])

corr = read("layer_score_correlations.csv")
catalog = read("method_catalog_and_coverage.csv")
ledger = jread("inputs/ledger.json")
registry = jread("recommendation_registry.json")
reg = {(r["dataset"], r["model"], r["variant"]): r for r in registry}
scores = collections.defaultdict(dict)
for r in read("inputs/all_layer_scores.csv"):
    scores[r["dataset"],r["model"],r["method"]+"/"+r["flavor"]][int(r["layer"])] = float(r["score"])
for r in jread("inputs/visedit_full_rankings.json"):
    scores[r["dataset"],r["model"],"VisEdit-Direct-"+r["target"]+"/diagnostic"] = dict(zip(r.get("contribution_ranking",[]),r.get("contribution_scores",[])))
pools = {p: {} for p in POLICIES}
for r in ledger["rows"]:
    for p in POLICIES:
        keep = r["recipe"] == ("stable" if p == "stable_only" else "main")
        if p in ["main_without_flagged", "verified50_main"]:
            keep = keep and not flagged(r)
        if p == "verified50_main":
            keep = keep and r["training"] == "50轮已核验"
        if keep:
            key = (r["dataset"],r["model"],r["layer"])
            assert key not in pools[p]
            pools[p][key] = r

verified = 0
for r in corr:
    key = (r["dataset"],r["model"],r["variant"])
    pool = pools[r["policy"]]
    layers = [int(x[1:]) for x in r["layers"].split(",") if x]
    expected = [l for l in reg[key].get("all_ranking", []) if (*key[:2],l) in pool and l in scores[key]]
    assert layers == expected and len(layers) == int(r["n_layers"])
    rr = rho([scores[key][l] for l in layers], [pool[(*key[:2],l)]["metrics"][r["metric"]] for l in layers]) if len(layers) >= 5 else None
    assert (rr is None and not r["rho"]) or (rr is not None and r["rho"] and abs(rr-float(r["rho"])) < 1e-12), r
    verified += 1
    r["rho"] = None if rr is None else rr
    r["coverage"] = float(r["coverage"]) if r["coverage"] else None
    r["n_layers"] = int(r["n_layers"])

variants = [r["variant"] for r in catalog]
datasets = list(dict.fromkeys(r["dataset"] for r in registry))
models = list(dict.fromkeys(r["model"] for r in registry))
summary = []
for p, v, m in itertools.product(POLICIES, variants, METRICS):
    for kind, scope in [("all","all")] + [("dataset", d) for d in datasets] + [("model", x) for x in models]:
        rows = [r for r in corr if r["policy"] == p and r["variant"] == v and r["metric"] == m and r["coverage"] is not None and r["coverage"] >= .8 and (kind == "all" or r[kind] == scope)]
        valid = [r for r in rows if r["rho"] is not None]
        vals = [r["rho"] for r in valid]
        summary.append(dict(policy=p,scope_type=kind,scope=scope,variant=v,metric=m,n=len(vals),mean_rho=st.mean(vals) if vals else None,median_rho=st.median(vals) if vals else None,positive=sum(x>0 for x in vals),strong_positive=sum(x>=.7 for x in vals),strong_negative=sum(x<=-.7 for x in vals),min_rho=min(vals) if vals else None,max_rho=max(vals) if vals else None,min_layers=min((r["n_layers"] for r in valid),default=None),max_layers=max((r["n_layers"] for r in valid),default=None),groups=json.dumps([[r["dataset"],r["model"]] for r in valid],ensure_ascii=False)))
write("all_formula_metric_summary.csv", summary)
strong = [r for r in corr if r["rho"] is not None and abs(r["rho"]) >= .7 and r["coverage"] is not None and r["coverage"] >= .8]
write("strong_positive_and_negative_cases.csv", strong)
write("audited_layer_correlations.csv", corr)

S = {(r["policy"],r["scope_type"],r["scope"],r["variant"],r["metric"]):r for r in summary}
C = {(r["policy"],r["dataset"],r["model"],r["variant"],r["metric"]):r for r in corr}
main = list(pools["observed_main"].values())
constant = {m: sorted(set(r["metrics"][m] for r in main)) for m in METRICS}
assert constant["T-Loc"] == [100.0] and len(main) == 396

# Same-combination comparison for the strength-only and current joint formula.
pairs = []
for m in METRICS:
    a, b = "Ours-no-direction/raw", "Ours-main/raw"
    for d, model in itertools.product(datasets, models):
        x = C.get(("observed_main",d,model,a,m))
        y = C.get(("observed_main",d,model,b,m))
        if x and y and all(r["rho"] is not None and r["coverage"] is not None and r["coverage"] >= .8 for r in [x,y]):
            assert set(x["layers"].split(",")) == set(y["layers"].split(","))
            pairs.append(dict(dataset=d,model=model,metric=m,n_layers=x["n_layers"],strength_only_rho=x["rho"],current_joint_rho=y["rho"],delta=x["rho"]-y["rho"]))
write("strength_vs_current_same_layers.csv", pairs)

# Relations among outcome metrics explain redundancy, not additional independent tests.
cross = []
for (d, model), rr in itertools.groupby(sorted(main,key=lambda r:(r["dataset"],r["model"])), key=lambda r:(r["dataset"],r["model"])):
    rr = list(rr)
    for a,b in itertools.combinations(METRICS,2):
        cross.append(dict(dataset=d,model=model,metric_a=a,metric_b=b,n_layers=len(rr),rho=rho([r["metrics"][a] for r in rr],[r["metrics"][b] for r in rr])))
write("outcome_metric_relations.csv",cross)

def f(x):
    return "—" if x is None else f"{x:.3f}"

def table(headers, rows):
    return "| " + " | ".join(headers) + " |\n|" + "|".join(["---"]*len(headers)) + "|\n" + "".join("| " + " | ".join(map(str,r)) + " |\n" for r in rows) + "\n"

def link(path, text):
    return f"[{text}](<{path.as_posix()}>)"

proto = jread("protocol.json")
report = "# 定位公式与 Average 各组成指标的相关性\n\n"
report += f"扫层快照：{proto['sweep_updated_at']}；定位快照：{proto['recommendations_updated_at']}。使用已有结果，未启动训练、未改变公式、未依据分项成绩重排候选。\n\n"
report += "**结论：存在部分组合上的强正相关，主要来自视觉梯度强度与 Rel、T-Gen、M-Gen；当前没有发现跨组合、跨指标均保持强正相关的公式。** 将指标拆开后，梯度强度与编辑/泛化的关系比与 Average 更清楚；M-Loc 呈不同关系，不能由前面三项替代。\n\n"
report += "## 1. 计算口径\n\n"
report += "- 在每个数据集×模型组合内，用层定位分数与同层评测指标计算 Spearman ρ；只使用有实际评测的层，至少 5 层。不是把不同模型的原始梯度混合相关，也不是逐样本相关。\n- 主表要求定位有效样本覆盖率≥80%，每个组合等权平均其 ρ。表中 N 是可计算的组合数，既不是层数，也不是独立模型数；同一模型在不同数据集重复出现。不同方法 N 不同的均值仅作描述。\n- 将 ρ≥0.7 / ρ≤−0.7 作为本报告的描述性“强正/强负”标记，不代表显著性检验或独立验证。未进行多重检验后的发现声明。\n- 主口径保留 396 条 main 实测记录（含已记录的失败/未足预算结果）；去除异常训练标签的 389 条口径作为敏感性检查。stable 单列，不填补 main。全量原始结果、各数据集/模型拆分和四种口径均保存到 CSV。\n- Raw 保留有限零分末层；Tukey 用冻结输入中各公式自己的筛选集合。Tukey 与 Raw 的相关性可能基于不同层集合，均值上升不能直接解读为选层性能提升。\n\n"
report += "## 2. 全部已有逐层分数的版本\n\n"
report += "下列是组合内 ρ 的等权均值，不是 Average 成绩，也不是胜率。视觉强度四个版本与 Ours 主式使用相同的 20 个高覆盖组合；其他方法可用组合不同。T-Loc 在 main 的 396 条记录中全部为 100.0，所有公式对它的相关性均未定义，不能填成 0。\n\n"
cols = ["版本", "N", "Rel", "T-Gen", "M-Gen", "M-Loc", "Average", "强正组数 Rel/T-Gen/M-Gen"]
rows = []
for v in variants:
    ss = [S["observed_main","all","all",v,m] for m in METRICS if m != "T-Loc"]
    if not any(r["n"] for r in ss):
        continue
    assert len(set(r["n"] for r in ss)) == 1
    rows.append([v,ss[0]["n"]] + [f(r["mean_rho"]) for r in ss] + ["/".join(str(r["strong_positive"]) for r in ss[:3])])
report += table(cols,rows)
report += "记旧/新视觉隐藏状态梯度范数为 aᵢ、bᵢ，余弦为 cᵢ：Ours-no-direction=E[bᵢ]；LGA-Visual-no-direction=E[aᵢbᵢ]；Ours-main=|E[cᵢ]|E[bᵢ]；LGA-Visual=E[gᵢ旧·gᵢ新]。联合范数与纯新范数在部分组合产生相同层排序，这些结果不能计为独立的重复验证。\n\n"
report += "VisEdit-Direct 三行仅表示贡献度与同层编辑结果的诊断相关性；VisEdit-Pre 根据高贡献区域选择前置编辑层，是另一种映射规则，不能把 Direct 的负相关直接判成 Pre 方法失败。pred-field 历史目标也不等于 model_pred。CMA 两目标有噪声/seed 协议差异，参数/视觉梯度的有效样本集合也不同。\n\n"
report += "### 没有定义逐层分数相关性的登记版本\n\n"
missing = []
for c in catalog:
    if any(S["observed_main","all","all",c["variant"],m]["n"] for m in METRICS):
        continue
    v = c["variant"]
    reason = "缺严格原始消融统计，不能计算" if int(c["n_formula_ready"]) == 0 else ("区域到前置层的推荐规则，不直接视为同层贡献分数" if "VisEdit-Pre" in v else "仅有推荐名次，无可复核逐层分数")
    missing.append([v,reason])
report += table(["版本","原因"],missing)
report += "## 3. 局部强相关与反例\n\n"
cases = [
    ("mmke-entity","instructblip-vicuna-7b","Ours-no-direction/raw"),
    ("mmke-visual","smolvlm-1.7b","Ours-no-direction/raw"),
    ("mmke-entity","llava-v1.5-7b","Ours-no-direction/raw"),
    ("mmke-visual","minigpt-4-vicuna-7b","Ours-no-direction/raw"),
    ("mmke-entity","minigpt-4-vicuna-7b","Ours-no-direction/raw"),
    ("mmke-visual","minigpt-4-vicuna-7b","LGA-Visual/raw"),
    ("mmke-entity","llava-v1.5-7b","LGA-Param/tukey"),
    ("evqa-pilot500","minigpt-4-vicuna-7b","SaLEM-alt/raw"),
    ("evqa-pilot500","qwen2.5-vl-3b","Ours-no-direction/raw"),
]
case_rows = []
for d,model,v in cases:
    rr = [C["observed_main",d,model,v,m] for m in METRICS if m != "T-Loc"]
    case_rows.append([d,model,v,rr[0]["n_layers"]]+[f(r["rho"]) for r in rr])
report += table(["数据集","模型","版本","层数","Rel","T-Gen","M-Gen","M-Loc","Average"],case_rows)
report += "InstructBLIP×MMKE-entity 的纯新范数与前三项相关性约 0.93–0.95，但 M-Loc 为负。MiniGPT4×MMKE-visual 的 LGA 视觉有符号内积与前三项反而强负相关；同一组合改看纯新范数则为强正相关。不能看到 |ρ| 大就认定按原分数降序推荐有效，也不能根据已见评测结果逐组合翻转符号后当成验证过的通用公式。LLaVA×MMKE-entity 当前只有 10 个有结果的层；其强相关不等于已完成全网络确认。\n\n"
report += "## 4. 按数据集拆开：强度与方向的差异\n\n"
selected = ["Ours-no-direction/raw","LGA-Visual-no-direction/raw","Ours-main/raw","LGA-Visual/raw","LGA-Param/tukey","SaLEM-alt/raw"]
rows = []
for d,v in itertools.product(datasets,selected):
    rr = [S["observed_main","dataset",d,v,m] for m in METRICS if m != "T-Loc"]
    rows.append([d,v,rr[0]["n"]]+[f(r["mean_rho"]) for r in rr])
report += table(["数据集","版本","N","Rel","T-Gen","M-Gen","M-Loc","Average"],rows)
report += "这是任务与模型条件差异的回顾性证据，不能只由数据集名称给任务定性。若要提出任务条件定位规则，还需在不读取测试层成绩的条件下定义任务类别、选择规则，并在保留组合上确认。\n\n"
report += "## 5. 异常训练标签的敏感性检查\n\n"
rows = []
for v in selected:
    for p in ["observed_main","main_without_flagged"]:
        rr = [S[p,"all","all",v,m] for m in METRICS if m != "T-Loc"]
        rows.append([v,p,rr[0]["n"]]+[f(r["mean_rho"]) for r in rr])
report += table(["版本","口径","N","Rel","T-Gen","M-Gen","M-Loc","Average"],rows)
report += "这里的异常训练标签过滤与定位公式的 Tukey 梯度分数过滤是两件事。去除训练异常不是将不利结果从主表删除；两种口径并列。verified50_main 与 stable_only 的全部分项见输出 CSV，不能混入同一宏平均。\n\n"
report += "## 6. 对 Average 和选公式的含义\n\n"
report += "Average=(Rel+T-Gen+M-Gen+T-Loc+M-Loc)/5。前三项衡量编辑及其泛化，M-Loc 衡量图像相关局部性保留；它们可能对层选择提出不同要求。例如 Qwen×E-VQA 的纯新范数对 Rel 为正、对 M-Loc 为负，最终对 Average 接近零。**T-Loc 恒定只是不给排序提供信息；加常数和正比例缩放不会削弱 Spearman。** Average 的相关系数也不是各分项相关系数的算术平均。\n\n"
cross_rows = []
for a,b in [("Rel","T-Gen"),("Rel","M-Gen"),("T-Gen","M-Gen")]:
    vals = [r["rho"] for r in cross if r["metric_a"]==a and r["metric_b"]==b and r["rho"] is not None]
    cross_rows.append([a+" 与 "+b,len(vals),f(st.mean(vals)),f(st.median(vals))])
report += "三个编辑/泛化指标自身高度相关，不能把三个同向结果当作三份独立证据：\n\n" + table(["指标对","组合数","平均ρ","中位ρ"],cross_rows)
report += "当前最值得继续确认的假设是：视觉梯度强度有助于预测编辑与泛化，而单独依赖梯度强度未能稳定预测 M-Loc。主公式方向项是否有增益，应在同组合、同层集合比较，并用保留数据确认；不能仅凭此次事后拆指标就更换最终评价目标。分项相关性与原先 Top-1/Best@3/Mean@3 回答不同问题，最终推荐效用仍需固定预算的候选层成绩来检验。\n\n"
report += "## 7. 可复核文件\n\n"
for name,desc in [("all_formula_metric_summary.csv","全部34版本×6指标×4口径，含数据集/模型拆分、强正负计数、中位数和组合清单"),("strong_positive_and_negative_cases.csv","所有达到描述阈值的正/负案例"),("audited_layer_correlations.csv","逐组合、逐公式、逐指标的重新核验结果"),("strength_vs_current_same_layers.csv","纯新范数与当前主式的同组合、同层比较"),("outcome_metric_relations.csv","评测指标彼此的层级相关性"),("verification.json","校验结果和输入哈希")]:
    report += "- " + link(OUT/name,desc) + "\n"
report += "\n" + link(ROOT/"scripts/analyze_component_correlations_20260928.py","重现脚本") + "。每项 ρ 独立从冻结逐层分数与实际评测重新计算，并与旧表核对；缺失或常数项未填零。\n"
report_path = ROOT / "md/Location/ALL_Methods_Component_Correlations.md"
report_path.write_text(report,encoding="utf-8")
inputs = ["layer_score_correlations.csv","method_catalog_and_coverage.csv","recommendation_registry.json","inputs/ledger.json","inputs/all_layer_scores.csv","inputs/visedit_full_rankings.json","protocol.json"]
verification = dict(status="PASS",independently_verified_correlation_rows=verified,main_records=len(main),main_tloc_unique=constant["T-Loc"],summary_rows=len(summary),strong_case_rows=len(strong),registered_variants=len(variants),variants_with_computable_main_correlations=sum(any(S["observed_main","all","all",v,m]["n"] for m in METRICS) for v in variants),source_sweep_at=proto["sweep_updated_at"],source_recommendations_at=proto["recommendations_updated_at"],source_hashes={name:hashlib.sha256((SRC/name).read_bytes()).hexdigest() for name in inputs})
(OUT/"verification.json").write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(verification,ensure_ascii=False,indent=2))
print(report_path)
