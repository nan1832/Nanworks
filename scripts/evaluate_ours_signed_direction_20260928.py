"""Evaluate signed Ours layer recommendations against frozen existing sweeps.

Run build_all_method_recommendations.py first. No training or server mutation.
After this script, rebuild the catalog to include its generated section 7.5.
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
SRC = ROOT / "outputs/all_methods_recommendations_20260928"
OUT = ROOT / "outputs/ours_signed_direction_20260928"
INPUTS = OUT / "inputs"
INPUTS.mkdir(parents=True, exist_ok=True)
NEW = "Ours-signed-direction"
METHODS = [NEW, "Ours-main", "Ours-no-direction", "LGA-Visual", "LGA-Param"]
POLICIES = ["observed_main", "main_without_flagged", "verified50_main", "stable_only"]
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
TOTAL = {"evqa-pilot500":500,"mmke-visual":214,"mmke-entity":636}
DISPLAY = {"blip2-opt-2.7b":"BLIP2","instructblip-vicuna-7b":"InstructBLIP","minigpt-4-vicuna-7b":"MiniGPT-4","llava-v1.5-7b":"LLaVA-1.5","qwen2.5-vl-3b":"Qwen2.5-VL","paligemma-3b":"PaliGemma","smolvlm-1.7b":"SmolVLM"}

def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def csvread(p):
    with p.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def csvwrite(name, rows):
    if not rows: return
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        for r in rows: w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def save(name, obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
def group(r): return r["dataset"],r["model"]
def variant(r): return r["method"]+"/"+r["flavor"]
def avg(x): return st.mean(x) if x else None
def fmt(x): return "—" if x is None else f"{x:.3f}"
def layers(x): return ", ".join("L"+str(l) for l in x) or "—"
def table(headers, rows):
    def cell(x): return str(x).replace("|","\\|")
    return "| " + " | ".join(headers) + " |\n|"+"|".join(["---"]*len(headers))+"|\n"+"".join("| "+" | ".join(cell(x) for x in r)+" |\n" for r in rows)+"\n"

catalog=load(SRC/"recommendations.json")
recs=catalog["records"]
old=load(OUT/"backups/recommendations.json")["records"]
R={(group(r),variant(r)):r for r in recs}
assert len(R)==len(recs)
old_unchanged=0
for r in old:
    if r["method"] != NEW:
        assert R[group(r),variant(r)]==r, (group(r),variant(r))
        old_unchanged+=1
assert old_unchanged==624
new=[r for r in recs if r["method"]==NEW]
assert len(new)==42 and len(recs)==666
# Freeze this task's inputs; never rewrite the previous performance snapshot.
(INPUTS/"recommendations.json").write_bytes((SRC/"recommendations.json").read_bytes())
ledger_path=ROOT/"outputs/sweep_ledger_20260928_110311/ledger.json"
if not (INPUTS/"ledger.json").exists(): (INPUTS/"ledger.json").write_bytes(ledger_path.read_bytes())
ledger=load(INPUTS/"ledger.json")

raw_sources={}; score_rows=[]; independently_verified=0
for ds,model in itertools.product(TOTAL,DISPLAY):
    p=SRC/"raw/visual"/ds/model/"ours_direct_layer_scores.csv"
    rr=csvread(p); raw_sources[p.relative_to(ROOT).as_posix()]=digest(p)
    values={int(r["layer"]):float(r["S_v_cos"])*float(r["S_v_new_norm"]) for r in rr}
    assert all(math.isfinite(x) for x in values.values())
    # Independent linear quantile implementation, separate from NumPy in builder.
    ordered=sorted(values.values())
    def quantile(q):
        h=(len(ordered)-1)*q; lo=math.floor(h); hi=math.ceil(h)
        return ordered[lo]+(h-lo)*(ordered[hi]-ordered[lo])
    q1,q3=quantile(.25),quantile(.75)
    low,high=q1-(q3-q1),q3+(q3-q1)
    for flavor in ["raw","tukey"]:
        r=R[(ds,model),NEW+"/"+flavor]
        excluded=sorted(l for l,s in values.items() if s<low or s>high) if flavor=="tukey" else []
        rank=sorted((l for l in values if l not in excluded),key=lambda l:(-values[l],l))
        assert r["all_ranking"]==rank and r["outlier_layers"]==excluded
        assert r["top3_scores"]==[values[l] for l in rank[:3]]
        if flavor=="tukey":
            assert all(math.isclose(r[k],v,rel_tol=1e-12,abs_tol=1e-15) for k,v in [("q1",q1),("q3",q3),("lower",low),("upper",high)])
        assert all(l in values and values[l]==0 for l in r["zero_gradient_layers"])
        independently_verified+=1
    for r in rr:
        l=int(r["layer"])
        score_rows.append(dict(dataset=ds,model=model,layer=l,mean_cos=float(r["S_v_cos"]),mean_new_l2=float(r["S_v_new_norm"]),signed_score=values[l],absolute_score=abs(float(r["S_v_cos"]))*float(r["S_v_new_norm"]),zero_gradient=r["S_v_zero_grad"],n_request=int(r["n_request"])))
csvwrite("signed_layer_scores.csv",score_rows)
csvwrite("recommendations.csv",new)
save("recommendations.json",new)

def flagged(r):
    status=(r["status"]+" "+(r.get("original_status") or "")).upper()
    return r["training"]=="恢复/诊断评测" or any(s in status for s in ["NUMERIC","NONFINITE","NONCONVERGENT"])
pools={p:collections.defaultdict(dict) for p in POLICIES}
for r in ledger["rows"]:
    for p in POLICIES:
        keep=r["recipe"]==("stable" if p=="stable_only" else "main")
        if p in ["main_without_flagged","verified50_main"]: keep=keep and not flagged(r)
        if p=="verified50_main": keep=keep and r["training"]=="50轮已核验"
        if keep:
            assert r["layer"] not in pools[p][group(r)]
            pools[p][group(r)][r["layer"]]=r

measurements=[]; M={}
for p,r,k in itertools.product(POLICIES,[r for r in recs if r["method"] in METHODS],[1,3,5]):
    pool=pools[p][group(r)]; cand=r["all_ranking"][:k]
    missing=[l for l in cand if l not in pool]
    status="complete" if len(cand)==k and not missing else "missing_evaluations" if missing else "insufficient_candidates"
    x=dict(policy=p,dataset=r["dataset"],model=r["model"],variant=variant(r),k=k,status=status,coverage=r["sample_count"]/TOTAL[r["dataset"]],candidates=cand,missing_layers=missing,zero_gradient_candidates=[l for l in cand if l in r.get("zero_gradient_layers",[])],flagged_candidates=[l for l in cand if l in pool and flagged(pool[l])],top1=pool[cand[0]]["metrics"]["Average"] if cand and cand[0] in pool else None,best=None,mean=None,regret=None,hit=None)
    if status=="complete":
        best_l=max(cand,key=lambda l:pool[l]["metrics"]["Average"])
        best=pool[best_l]["metrics"]["Average"]
        observed_best=max(v["metrics"]["Average"] for v in pool.values())
        x.update(best=best,mean=avg([pool[l]["metrics"]["Average"] for l in cand]),best_layer=best_l,regret=observed_best-best,hit=int(abs(observed_best-best)<1e-9),best_checkpoint_source=pool[best_l]["source"])
        for metric in METRICS:
            x["top1_"+metric]=pool[cand[0]]["metrics"][metric]
            x["best_selected_"+metric]=pool[best_l]["metrics"][metric]
            x["mean_"+metric]=avg([pool[l]["metrics"][metric] for l in cand])
    measurements.append(x); M[p,group(r),variant(r),k]=x
csvwrite("recommendation_performance.csv",measurements)
save("recommendation_performance.json",measurements)
variants=[m+"/"+f for m in METHODS for f in ["raw","tukey"]]
groups=list(itertools.product(TOTAL,DISPLAY))
def usable(r,cf): return r["status"]=="complete" and (cf=="all" or r["coverage"]>=.8)
summaries=[]
for p,v,k,cf in itertools.product(POLICIES,variants,[1,3,5],["all","coverage80"]):
    rr=[M[p,g,v,k] for g in groups if usable(M[p,g,v,k],cf)]
    summaries.append(dict(policy=p,variant=v,k=k,coverage_filter=cf,n=len(rr),top1=avg([r["top1"] for r in rr]),best=avg([r["best"] for r in rr]),mean=avg([r["mean"] for r in rr]),groups=[group(r) for r in rr]))
csvwrite("method_summary.csv",summaries)
pairs=[]
for p,k,cf,a,b,scope in itertools.product(POLICIES,[1,3,5],["all","coverage80"],[NEW+"/raw",NEW+"/tukey"],variants,["all"]+list(TOTAL)):
    if a==b: continue
    gg=[g for g in groups if (scope=="all" or g[0]==scope) and usable(M[p,g,a,k],cf) and usable(M[p,g,b,k],cf)]
    row=dict(policy=p,k=k,coverage_filter=cf,a=a,b=b,scope=scope,n=len(gg),groups=gg)
    for metric in ["top1","best","mean"]:
        av=[M[p,g,a,k][metric] for g in gg]; bv=[M[p,g,b,k][metric] for g in gg]
        dd=[x-y for x,y in zip(av,bv)]
        row.update({"a_"+metric:avg(av),"b_"+metric:avg(bv),"delta_"+metric:avg(dd),"wins_"+metric:sum(d>1e-9 for d in dd),"ties_"+metric:sum(abs(d)<=1e-9 for d in dd),"losses_"+metric:sum(d< -1e-9 for d in dd)})
    pairs.append(row)
csvwrite("paired_comparisons.csv",pairs)
P={(r["policy"],r["k"],r["coverage_filter"],r["a"],r["b"],r["scope"]):r for r in pairs}
missing=[r for r in measurements if r["variant"].startswith(NEW+"/") and r["status"]!="complete"]
csvwrite("missing_evaluations.csv",missing)

# Independently check shared comparator performance against the earlier audited snapshot.
previous=load(ROOT/"outputs/all_methods_performance_20260928/method_performance_all.json")
oldM={(r["policy"],group(r),r["variant"],r["k"]):r for r in previous}
verified_baseline=0
for key,x in M.items():
    if key[2].startswith(NEW+"/"): continue
    oldrow=oldM[key]
    assert x["status"]==oldrow["status"]
    for met in ["best","mean","regret","hit"]:
        assert x[met]==oldrow[met] or (x[met] is not None and oldrow[met] is not None and abs(x[met]-oldrow[met])<1e-9)
    verified_baseline+=1

section="### 7.5 Ours 带符号方向 × 新范数：补算与真实推荐效果\n\n"
section+="新增 `Ours-signed-direction`：`S_l = S_v_cos × S_v_new_norm = E[c_i] × E[b_i]`。仅去掉主公式的绝对值；梯度对象、样本、目标、聚合顺序保持一致，无深度权重。**不等于 LGA 去旧强度的 E[c_i b_i]；后者仍按原严格补算进度登记。** 原始 LGA 使用梯度内积，包含旧范数、新范数和带符号余弦。[论文 §5.1 与附录 A](https://arxiv.org/html/2602.20207v3)。\n\n"
section+="已补算 21 组、618 个层分数，各生成 Raw/Tukey Top-3、Top-5 与完整排序。Tukey 使用每组全部有限分数、κ=1、linear 四分位数、一次过滤、降序排序，同分取浅层。保留原始有限零分层，未因新公式而修改异常层协议。\n\n"
section+=f"真实编辑效果使用 SWeeplayers 的 **{ledger['updated_at']}** 快照；396 条 main、36 条 stable 分开，1 条 main-rerun 不择优替换原记录。候选缺一层就不计算完整 Best/Mean@3，不用零分、部分均值或 stable 代填 main。Top-1 是原推荐第一层的 Average；Best@3、Mean@3 为三层 Average 的最大值、均值。\n\n"
new_t=[M["observed_main",g,NEW+"/tukey",3] for g in groups]
complete=sum(r["status"]=="complete" for r in new_t)
zero=sum(bool(r["zero_gradient_candidates"]) for r in new_t)
missing_unique=sorted({(*group(r),l) for r in new_t for l in r["missing_layers"]})
section+=f"**Tukey 推荐已生成 21/21 组；已有 main 能完整评估 {complete}/21 组。{21-complete} 组缺候选层结果，共 {len(missing_unique)} 个不同的数据集×模型×层。{zero} 组 Top-3 含已标记零视觉梯度层。** 负方向组中 0 分可能高于所有负分而排在第一；这不表示该层有有效梯度证据。只看已有结果的宏平均会受可评组合构成影响，因此下表采用相同组合配对。\n\n"
section+="#### 7.5.1 同组合配对效果（新版本减参照）\n\n"
rows=[]
for cf in ["all","coverage80"]:
    for b in ["Ours-main/tukey","Ours-main/raw","Ours-no-direction/tukey","LGA-Visual/tukey","LGA-Param/tukey",NEW+"/raw"]:
        r=P["observed_main",3,cf,NEW+"/tukey",b,"all"]
        rows.append([cf,b,r["n"],fmt(r["a_top1"])+" / "+fmt(r["b_top1"]),fmt(r["a_best"])+" / "+fmt(r["b_best"]),fmt(r["a_mean"])+" / "+fmt(r["b_mean"]),fmt(r["delta_best"]),f"{r['wins_best']}/{r['ties_best']}/{r['losses_best']}"])
section+=table(["覆盖口径","参照版本","共同组数","Top-1 新/参照","Best@3 新/参照","Mean@3 新/参照","ΔBest@3","Best 胜/平/负"],rows)
matched=P["observed_main",3,"all",NEW+"/tukey","Ours-main/tukey","all"]
same_candidates=sum(R[g,NEW+"/tukey"]["top3"]==R[g,"Ours-main/tukey"]["top3"] for g in matched["groups"])
section+=f"**对最直接的绝对值消融：同做 Tukey 的 {matched['n']} 个完整共同组中，{same_candidates} 组 Top-3 顺序完全相同；Best@3 为 {matched['wins_best']} 胜、{matched['ties_best']} 平、{matched['losses_best']} 负，均值差 {matched['delta_best']:+.3f} 个百分点。现有可评结果未显示去掉绝对值有收益。** 不能把相对未过滤主公式的改善单独归因于符号，因为那个比较同时改变了过滤。\n\n"
section+="每一行内三个指标都使用该行相同的 Top-3 完整共同组，行与行的组合可以不同。coverage80 要求双方有效定位样本比例≥80%；BLIP2×MMKE-entity 的视觉定位 284/636，完整推荐保留并标记低覆盖。参数 LGA 的样本集合另有差异。\n\n"
section+="#### 7.5.2 带符号 Tukey 逐组合结果\n\n"
rows=[]
for x in new_t:
    r=R[group(x),NEW+"/tukey"]; z=set(r["zero_gradient_layers"])
    c=", ".join("L"+str(l)+( "†" if l in z else "") for l in x["candidates"])
    rows.append([x["dataset"],DISPLAY[x["model"]],c,fmt(x["top1"]),fmt(x["best"]),fmt(x["mean"]),layers(x["missing_layers"]),f"{r['sample_count']}/{TOTAL[x['dataset']]}"])
section+=table(["数据集","模型","带符号 Tukey Top-3","Top-1","Best@3","Mean@3","缺 main 层","定位样本"],rows)
section+="† 为原始日志的有限零视觉梯度层。这里的缺层不是推荐公式未算出；Top-1 在第一层已有评测时可单独报告，Best/Mean@3 仍必须三层齐全。Top-5、逐层分数和各公式的全部剔除层见机器可读文件及第 7.4 节。\n\n"
section+="#### 7.5.3 去除已标记训练异常后的配对检查\n\n"
rows=[]
for p,cf in itertools.product(["observed_main","main_without_flagged"],["all","coverage80"]):
    r=P[p,3,cf,NEW+"/tukey","Ours-main/tukey","all"]
    rows.append([p,cf,r["n"],fmt(r["delta_top1"]),fmt(r["delta_best"]),fmt(r["delta_mean"]),f"{r['wins_best']}/{r['ties_best']}/{r['losses_best']}"])
section+=table(["评测口径","覆盖口径","共同组数","ΔTop-1","ΔBest@3","ΔMean@3","Best 胜/平/负"],rows)
section+="主表保留所有 main 实测结果；main_without_flagged 排除恢复/诊断训练、数值异常/保护、不收敛标签，与 Tukey 的层定位分数过滤不同。verified50_main 和 stable_only 单独存入 CSV。相关缺层使部分负方向组尚不能进入完整比较，不能从现有可比子集外推 21 组整体胜率。\n\n"
prefix="../../outputs/ours_signed_direction_20260928/"
section+="[新增推荐含完整排序]("+prefix+"recommendations.json) · [逐层 C、N 与带符号分数]("+prefix+"signed_layer_scores.csv) · [Top-1/3/5 及分项成绩]("+prefix+"recommendation_performance.csv) · [同组合配对比较]("+prefix+"paired_comparisons.csv) · [缺失候选层]("+prefix+"missing_evaluations.csv) · [独立核验]("+prefix+"verification.json)\n\n"
section+="复现顺序：`python scripts/build_all_method_recommendations.py` → `python scripts/evaluate_ours_signed_direction_20260928.py` → `python scripts/build_all_method_recommendations.py`。最后一步将本节回填到总表，后续同步不会丢失新增公式。这里是已有实验的回顾性比较，没有新训练或测试集独立确认。\n"
(OUT/"recommendation_section.md").write_text(section,encoding="utf-8")
verification=dict(status="PASS",formula="mean_cos * mean_new_l2; no abs, no depth; NOT mean(cos*new_l2)",independently_verified_recommendation_groups=independently_verified,existing_recommendations_unchanged=old_unchanged,existing_baseline_evaluation_rows_reproduced=verified_baseline,new_layer_scores=len(score_rows),performance_rows=len(measurements),paired_rows=len(pairs),tukey_main_top3_complete=complete,tukey_main_top3_missing_groups=21-complete,tukey_main_missing_distinct_layers=len(missing_unique),tukey_top3_zero_gradient_groups=zero,paired_with_abs_same_ordered_top3=same_candidates,missing_tukey_main_layer_keys=missing_unique,sweep_snapshot=ledger["updated_at"],ledger_sha256=digest(INPUTS/"ledger.json"),recommendations_sha256=digest(INPUTS/"recommendations.json"),raw_sources=raw_sources,no_server_mutation=True,no_training=True)
save("verification.json",verification)
print(json.dumps({k:v for k,v in verification.items() if k!="raw_sources"},ensure_ascii=False,indent=2))
print(json.dumps(P["observed_main",3,"all",NEW+"/tukey","Ours-main/tukey","all"],ensure_ascii=False,indent=2))
