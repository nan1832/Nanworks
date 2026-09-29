"""Compare frozen recommendations with existing sweeps; no training or server writes.

All scoring decisions precede outcome inspection. Missing candidates/evaluations are
explicit states, never zero scores. A method's first recommendation is not reordered
using evaluation outcomes. Run with the bundled Python from the dataset root.
"""
import collections
import copy
import csv
import datetime
import hashlib
import itertools
import json
import math
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/all_methods_performance_20260928"
OUT.mkdir(parents=True, exist_ok=True)
INPUTS = OUT / "inputs"
INPUTS.mkdir(exist_ok=True)
SRC = ROOT / "outputs/all_methods_recommendations_20260928"
SWEEP = ROOT / "outputs/sweep_ledger_20260928_110311"
TOTAL = {"evqa-pilot500":500, "mmke-visual":214, "mmke-entity":636}
EVAL_N = {"evqa-pilot500":2093, "mmke-visual":293, "mmke-entity":954}
MODELS = ["blip2-opt-2.7b", "instructblip-vicuna-7b", "minigpt-4-vicuna-7b", "llava-v1.5-7b", "qwen2.5-vl-3b", "paligemma-3b", "smolvlm-1.7b"]
GROUPS = list(itertools.product(TOTAL, MODELS))
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
POLICIES = ["observed_main", "main_without_flagged", "verified50_main", "stable_only"]
KS = [1,3,5]
TOL = 1e-9
manifest = {}

def sha(data): return hashlib.sha256(data).hexdigest()
def snapshot(p, name=None):
    q = INPUTS / (name or p.name)
    if not q.exists(): q.write_bytes(p.read_bytes())
    manifest[q.name] = {"original":p.relative_to(ROOT).as_posix(), "sha256":sha(q.read_bytes()), "original_current_sha256":sha(p.read_bytes())}
    return q
def jread(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def jwrite(name, x): (OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
def cwrite(name, rr):
    if not rr: return
    fields = list(dict.fromkeys(k for r in rr for k in r))
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rr:
            w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()})
def fmt(xs): return ",".join(f"L{x}" for x in xs)
def avg(xs): return statistics.mean(xs) if xs else None
def variant(r): return r["method"]+"/"+r["flavor"]
def key(r): return r["dataset"],r["model"]
def eligible_coverage(r): return r["coverage"] is not None and r["coverage"] >= .8

for name in ["recommendations.json", "recommendations.csv", "all_layer_scores.csv", "visedit_full_rankings.json", "verification.json"]:
    snapshot(SRC/name, "recommendations_verification.json" if name=="verification.json" else name)
snapshot(SWEEP/"ledger.json");snapshot(SWEEP/"sweep_results.csv");snapshot(SWEEP/"audit_issues.json")
snapshot(ROOT/"md/Location/ALL_Methods_Recommends_layers.md")
snapshot(ROOT/"md/Location/SWeeplayers.md")
snapshot(ROOT/"outputs/lga_two_spaces_ablation_20260928/sync_status.json", "strict_ablation_sync_status.json")
recs_source=jread(INPUTS/"recommendations.json")
ledger=jread(INPUTS/"ledger.json")
recs=copy.deepcopy(recs_source["records"])
assert len(recs)==624
vis=jread(INPUTS/"visedit_full_rankings.json")
vis_lookup={(r["dataset"],r["model"],r["target"]):r for r in vis}
score_rows=list(csv.DictReader((INPUTS/"all_layer_scores.csv").open(encoding="utf-8-sig")))
score_lookup=collections.defaultdict(dict)
for r in score_rows:
    score_lookup[(r["dataset"],r["model"],r["method"],r["flavor"])][int(r["layer"])]=float(r["score"])

# Resolve VisEdit's Pre ranking separately from the contribution ranking. Derive
# additional Direct diagnostics for all three recorded targets, without relabeling Pre.
direct=[]
for r in recs:
    r["variant"]=variant(r);r["diagnostic_direct"]=False
    r["formula_status"]=r["status"]
    r["coverage"]=None if r.get("sample_count") is None else r["sample_count"]/TOTAL[r["dataset"]]
    if r["method"]=="Middle-Prior":r["coverage"]=1.
    if r["method"].startswith("VisEdit-Pre-"):
        v=vis_lookup[(r["dataset"],r["model"],r["target"])]
        if r["status"]=="done":
            assert r["top3"]==v["top3"]
            start=v["high_region"][0]
            r["all_ranking"]=list(range(start-1,-1,-1))
            assert r["all_ranking"][:3]==r["top3"]
            cfg_path=ROOT/r["source"]
            cfg=jread(cfg_path.with_name("config.json"))
            # VisEdit cohorts in these archives are complete; verify, don't infer.
            summary=jread(cfg_path.with_name("summary.json"))
            n=summary.get("valid_sample_count",summary.get("sample_count"))
            assert n==TOTAL[r["dataset"]] and cfg["sample_count"]==n
            r["sample_count"]=n;r["coverage"]=n/TOTAL[r["dataset"]]
        d=copy.deepcopy(r)
        d["method"]=r["method"].replace("VisEdit-Pre-","VisEdit-Direct-")
        d["flavor"]="diagnostic";d["variant"]=variant(d);d["diagnostic_direct"]=True
        d["all_ranking"]=v.get("contribution_ranking",[])
        d["top3"]=d["all_ranking"][:3]
        if d["status"]=="done":
            score_lookup[(d["dataset"],d["model"],d["method"],d["flavor"])]=dict(zip(v["contribution_ranking"],v["contribution_scores"]))
        direct.append(d)
    if r["status"]=="done":
        assert r["all_ranking"][:3]==r["top3"]
        assert len(set(r["all_ranking"]))==len(r["all_ranking"])
    else: assert not r["top3"]
recs+=direct
assert len(recs)==680
VARIANTS=list(dict.fromkeys(r["variant"] for r in recs))
assert len(VARIANTS)==34
R={(key(r),r["variant"]):r for r in recs}
assert len(R)==len(recs)
cwrite("recommendation_registry.csv",recs)
jwrite("recommendation_registry.json",recs)

# Adopt each recorded recipe exactly. Keep the BLIP2 rerun as a separate record.
outcome_rows=ledger["rows"]
assert len(outcome_rows)==433
outcome_keys=set();avg_rounding=[];flags=[]
def reasons(r):
    why=[];st=(r.get("status","")+" "+(r.get("original_status") or "")).upper()
    if r["training"]=="恢复/诊断评测":why.append("recovered_or_incomplete_training")
    if "NUMERIC" in st or "NONFINITE" in st:why.append("numeric_anomaly_or_guard")
    if "NONCONVERGENT" in st:why.append("nonconvergent")
    # Existing-checkpoint/repaired-selection/resume are retained; they do not by
    # themselves prove a changed training recipe or an incomplete run.
    return sorted(set(why))
for r in outcome_rows:
    ident=(*key(r),r["layer"],r["recipe"]);assert ident not in outcome_keys;outcome_keys.add(ident)
    assert r["samples"]==EVAL_N[r["dataset"]]
    assert all(math.isfinite(r["metrics"][m]) and 0<=r["metrics"][m]<=100.00001 for m in METRICS)
    delta=r["metrics"]["Average"]-statistics.mean(r["metrics"][m] for m in METRICS[:-1])
    assert abs(delta)<.011,(ident,delta)
    if abs(delta)>1e-8:avg_rounding.append(dict(dataset=r["dataset"],model=r["model"],layer=r["layer"],recipe=r["recipe"],stored_average=r["metrics"]["Average"],delta_from_rounded_components=delta))
    if reasons(r):flags.append(dict(dataset=r["dataset"],model=r["model"],layer=r["layer"],recipe=r["recipe"],reason=reasons(r),status=r["status"],original_status=r.get("original_status"),Average=r["metrics"]["Average"]))
pools={p:collections.defaultdict(dict) for p in POLICIES}
for r in outcome_rows:
    for p in POLICIES:
        keep=(r["recipe"]=="stable") if p=="stable_only" else r["recipe"]=="main"
        if p in ["main_without_flagged","verified50_main"]:keep=keep and not reasons(r)
        if p=="verified50_main":keep=keep and r["training"]=="50轮已核验"
        if keep:pools[p][key(r)][r["layer"]]=r
cwrite("flagged_outcomes.csv",flags);cwrite("stored_average_rounding_audit.csv",avg_rounding)
cwrite("outcomes_used.csv",[dict(dataset=r["dataset"],model=r["model"],layer=r["layer"],recipe=r["recipe"],training=r["training"],status=r["status"],original_status=r.get("original_status"),evidence=r["evidence"],source=r["source"],**r["metrics"]) for r in outcome_rows])

# Random reference is an exact expectation over the observed pool, NOT a claim
# about uniform sampling of all architecture layers (many have no outcomes).
references={};refrows=[]
for p in POLICIES:
    for g,pool in pools[p].items():
        values=sorted(r["metrics"]["Average"] for r in pool.values());n=len(values)
        oracle=values[-1];ties=sum(abs(v-oracle)<=TOL for v in values)
        for k in KS:
            if n<k:continue
            denominator=math.comb(n,k)
            expected_best=sum(values[i]*math.comb(i,k-1)/denominator for i in range(k-1,n))
            ref=dict(policy=p,dataset=g[0],model=g[1],k=k,n_observed_layers=n,
                     observed_best=oracle,observed_best_layers=fmt(sorted(l for l,r in pool.items() if abs(r["metrics"]["Average"]-oracle)<=TOL)),
                     random_expected_best=expected_best,random_expected_mean=statistics.mean(values),
                     random_hit_probability=1-(math.comb(n-ties,k) if n-ties>=k else 0)/denominator)
            references[p,g,k]=ref;refrows.append(ref)
cwrite("observed_pool_and_random_reference.csv",refrows)

measurements=[];M={};missing=[]
for p in POLICIES:
    for r in recs:
        g=key(r);pool=pools[p].get(g,{})
        for k in KS:
            candidates=r.get("all_ranking",[])[:k]
            known=[l for l in candidates if l in pool]
            miss=[l for l in candidates if l not in pool]
            if r["status"]!="done":state="pending_formula"
            elif len(candidates)<k:state="insufficient_candidates"
            elif miss:state="missing_evaluations"
            else:state="complete"
            ref=references.get((p,g,k),{})
            row=dict(policy=p,dataset=g[0],model=g[1],variant=r["variant"],family=r["family"],method=r["method"],flavor=r["flavor"],target=r["target"],diagnostic_direct=r["diagnostic_direct"],coverage=r["coverage"],k=k,
                     status=state,candidates=fmt(candidates),evaluated_count=len(known),missing_layers=fmt(miss),
                     candidate_zero_gradient_layers=fmt([l for l in candidates if l in r.get("zero_gradient_layers",[])]),
                     candidate_flagged_layers=fmt([l for l in known if reasons(pool[l])]),
                     n_observed_layers=len(pool),best=None,mean=None,regret=None,hit=None,
                     best_layer=None,rank1_score=pool[candidates[0]]["metrics"]["Average"] if candidates and candidates[0] in pool else None,
                     random_expected_best=ref.get("random_expected_best"),random_expected_mean=ref.get("random_expected_mean"),
                     delta_best_random=None,delta_mean_random=None,source=r.get("source",""),notes=r.get("notes",""))
            if state=="complete":
                # Ties in evaluation choose earlier recommendation; never splice
                # the best submetric from a different checkpoint into this result.
                best_layer=max(candidates,key=lambda l:pool[l]["metrics"]["Average"])
                best=pool[best_layer]["metrics"]["Average"]
                row.update(best=best,mean=avg([pool[l]["metrics"]["Average"] for l in candidates]),best_layer=best_layer,
                           regret=ref["observed_best"]-best,hit=int(abs(best-ref["observed_best"])<=TOL),
                           best_checkpoint_status=pool[best_layer]["status"],best_checkpoint_training=pool[best_layer]["training"],
                           best_checkpoint_source=pool[best_layer]["source"])
                for metric in METRICS[:-1]:
                    row["best_selected_"+metric]=pool[best_layer]["metrics"][metric]
                    row["mean_"+metric]=avg([pool[l]["metrics"][metric] for l in candidates])
                row["delta_best_random"]=best-ref["random_expected_best"]
                row["delta_mean_random"]=row["mean"]-ref["random_expected_mean"]
            if state!="complete":missing.append({k2:row[k2] for k2 in ["policy","dataset","model","variant","k","status","candidates","evaluated_count","missing_layers"]})
            assert state=="complete" or row["best"] is None
            measurements.append(row);M[p,g,r["variant"],k]=row
cwrite("method_performance_all.csv",measurements);jwrite("method_performance_all.json",measurements)
cwrite("missing_candidates_or_evaluations.csv",missing)

SCOPES=[("all","all")]+[("dataset",d) for d in TOTAL]+[("model",m) for m in MODELS]
def in_scope(g,t,s):return t=="all" or (g[0] if t=="dataset" else g[1])==s
def ok(m,coverage_filter):return m and m["status"]=="complete" and (coverage_filter=="all" or eligible_coverage(m))
SUMMARY_FIELDS=["best","mean","regret","hit","delta_best_random","delta_mean_random"]
summaries=[]
for p,k,cf,(stype,scope),v in itertools.product(POLICIES,KS,["all","coverage80"],SCOPES,VARIANTS):
    allrows=[M[p,g,v,k] for g in GROUPS if (p,g,v,k) in M and in_scope(g,stype,scope)]
    complete=[x for x in allrows if ok(x,cf)]
    s=dict(policy=p,k=k,coverage_filter=cf,scope_type=stype,scope=scope,variant=v,n_registered=len(allrows),n_complete=len(complete),
           n_pending_formula=sum(x["status"]=="pending_formula" for x in allrows),
           groups=[x["dataset"]+"/"+x["model"] for x in complete])
    for f in SUMMARY_FIELDS:s[f]=avg([x[f] for x in complete])
    summaries.append(s)
cwrite("method_summary_by_scope.csv",summaries)

# All pairs are computed on precisely the same dataset-model combinations. The
# scope breakdown prevents a pooled win count from hiding model/task differences.
pairs=[]
for p,k,cf,(stype,scope) in itertools.product(POLICIES,KS,["all","coverage80"],SCOPES):
    gs=[g for g in GROUPS if in_scope(g,stype,scope)]
    for a,b in itertools.combinations(VARIANTS,2):
        common=[g for g in gs if ok(M.get((p,g,a,k)),cf) and ok(M.get((p,g,b,k)),cf)]
        # Preserve n=0 for overall coverage; detailed empty slices add no evidence.
        if not common and stype!="all":continue
        rr=dict(policy=p,k=k,coverage_filter=cf,scope_type=stype,scope=scope,a=a,b=b,n=len(common),
                groups=["/".join(g) for g in common],same_candidate_set=sum(set(M[p,g,a,k]["candidates"].split(","))==set(M[p,g,b,k]["candidates"].split(",")) for g in common))
        for f in ["best","mean"]:
            ds=[M[p,g,a,k][f]-M[p,g,b,k][f] for g in common]
            rr.update({"a_"+f:avg([M[p,g,a,k][f] for g in common]),"b_"+f:avg([M[p,g,b,k][f] for g in common]),
                       "delta_"+f:avg(ds),"median_delta_"+f:statistics.median(ds) if ds else None,
                       f+"_wins":sum(d>TOL for d in ds),f+"_ties":sum(abs(d)<=TOL for d in ds),f+"_losses":sum(d<-TOL for d in ds)})
        pairs.append(rr)
cwrite("all_pairwise_comparisons.csv",pairs)

# Fixed cohorts for readable multi-method comparisons (without mixing denominators).
cohorts={
    "core7_current":["Middle-Prior/raw","CMA-model_pred/raw","Perturb-KL-alt/raw","SaLEM-alt/raw","LGA-Param/tukey","VisEdit-Pre-alt/current","Ours-main/raw"],
    "all_complete21_variants":[v for v in VARIANTS if sum(r["variant"]==v and r["status"]=="done" for r in recs)==21],
    "visual_formulas":[v for v in VARIANTS if v.startswith(("Ours-","LGA-Visual")) and sum(r["variant"]==v and r["status"]=="done" for r in recs)==21],
}
cohort_rows=[]
for name,vs in cohorts.items():
    for p,k,cf,(stype,scope) in itertools.product(POLICIES,KS,["all","coverage80"],SCOPES[:4]):
        gs=[g for g in GROUPS if in_scope(g,stype,scope) and all(ok(M.get((p,g,v,k)),cf) for v in vs)]
        for v in vs:
            cc=dict(cohort=name,policy=p,k=k,coverage_filter=cf,scope_type=stype,scope=scope,variant=v,n=len(gs),groups=["/".join(g) for g in gs])
            for f in SUMMARY_FIELDS:cc[f]=avg([M[p,g,v,k][f] for g in gs])
            cohort_rows.append(cc)
cwrite("fixed_cohort_comparisons.csv",cohort_rows)

# Spearman on observed, eligible layers. Pre is a region-to-candidate rule and is
# NOT assigned the contribution score of the same numbered layer as its own score.
def ranks(values):
    out=[0.]*len(values);order=sorted(range(len(values)),key=lambda i:values[i]);i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]:j+=1
        rank=(i+j-1)/2+1
        for t in range(i,j):out[order[t]]=rank
        i=j
    return out
def spearman(x,y):
    a,b=ranks(x),ranks(y);ma,mb=statistics.mean(a),statistics.mean(b)
    den=math.sqrt(sum((t-ma)**2 for t in a)*sum((t-mb)**2 for t in b))
    return sum((u-ma)*(v-mb) for u,v in zip(a,b))/den if den else None
correlations=[]
for p in POLICIES:
    for r in recs:
        if r["status"]!="done":continue
        scores=score_lookup.get((r["dataset"],r["model"],r["method"],r["flavor"]),{})
        pool=pools[p].get(key(r),{})
        ls=[l for l in r["all_ranking"] if l in pool and l in scores]
        for met in METRICS:
            rho=spearman([scores[l] for l in ls],[pool[l]["metrics"][met] for l in ls]) if len(ls)>=5 else None
            correlations.append(dict(policy=p,dataset=r["dataset"],model=r["model"],variant=r["variant"],metric=met,n_layers=len(ls),rho=rho,
                                     coverage=r["coverage"],layers=fmt(ls),status="ok" if rho is not None else "no_score_or_insufficient_layers_or_constant"))
cwrite("layer_score_correlations.csv",correlations)

# Unweighted counts for missing layers are diagnostic, not a queue priority:
# correlated variants recommending the same layer are not independent votes.
needs=collections.defaultdict(set)
for r in missing:
    if r["policy"]=="observed_main" and r["status"]=="missing_evaluations":
        for l in r["missing_layers"].split(","):
            needs[r["dataset"],r["model"],l,r["k"]].add(r["variant"])
cwrite("missing_layer_coverage.csv",[dict(dataset=d,model=m,layer=l,k=k,affected_variant_count=len(vs),affected_variants=sorted(vs)) for (d,m,l,k),vs in sorted(needs.items())])
catalog=[]
for v in VARIANTS:
    rr=[r for r in recs if r["variant"]==v]
    cc=dict(variant=v,family=rr[0]["family"],target=rr[0]["target"],diagnostic_direct=rr[0]["diagnostic_direct"],n_registered=len(rr),n_formula_ready=sum(r["status"]=="done" for r in rr),n_formula_pending=sum(r["status"]!="done" for r in rr),
            top1_complete=sum(ok(M["observed_main",key(r),v,1],"all") for r in rr),top3_complete=sum(ok(M["observed_main",key(r),v,3],"all") for r in rr),top5_complete=sum(ok(M["observed_main",key(r),v,5],"all") for r in rr))
    catalog.append(cc)
cwrite("method_catalog_and_coverage.csv",catalog)
protocol=dict(created_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
              recommendations_updated_at=recs_source["updated_at"],sweep_updated_at=ledger["updated_at"],
              scope="31 registered method/target/formula/filter variants plus 3 explicitly diagnostic VisEdit Direct variants; no historical depth-weighted formulas added",
              metrics="Top1 uses first candidate. Best@K=max stored Average; Mean@K=mean stored Average. Require K candidates and all K outcomes. Regret/Hit use observed pool best, NOT full-layer oracle.",
              top5="Deterministically extend recorded all_ranking or VisEdit high-region Pre rule; preserve recorded Top3 exactly; never extend by observed editing performance.",
              policies={"observed_main":"all main records including evaluated failed/numeric/incomplete runs", "main_without_flagged":"main excluding recovered/diagnostic training, numeric/NaN-guard and nonconvergent labels; other resumed or repaired selection records retained", "verified50_main":"main_without_flagged with training=50轮已核验", "stable_only":"stable rows only, retain own failure flags; never fill main with stable"},
              main_rerun="preserved in outcomes_used.csv, excluded from primary pools; no best-of-run selection",
              random="exact expected Best/Mean/Hit of uniform K-subsets within recorded observed pool; conditional diagnostic, not full-network random experiment",
              pooling="dataset-model macro; method-only averages are descriptive, not a shared-cohort leaderboard. All pairwise comparisons use matched groups. coverage80 requires each compared localization coverage>=80%.",
              source_version_cautions="CMA alt/model_pred also differ noise/seed protocol; parameter/visual LGA differ sample cohorts; VisEdit pred-field not model_pred; zero-gradient finite terminal layers kept per source rules.",
              incomplete_formula="210 original LGA ablation group-variant rows lack strict cross-statistics; never replace E[ab] by E[a]E[b]. MMKE model_pred contribution missing in 14 original rows, plus 14 diagnostic Direct rows.",
              input_manifest=manifest)
jwrite("protocol.json",protocol)
verification=dict(original_variants=31,total_variants=34,original_recommendation_rows=624,total_recommendation_rows=len(recs),
                  formula_ready=sum(r["status"]=="done" for r in recs),formula_pending=sum(r["status"]!="done" for r in recs),
                  outcome_rows=len(outcome_rows),recipe_counts=dict(collections.Counter(r["recipe"] for r in outcome_rows)),
                  policy_outcome_counts={p:sum(len(x) for x in pools[p].values()) for p in POLICIES},
                  performance_rows=len(measurements),pairwise_rows=len(pairs),correlation_rows=len(correlations),
                  all_registered_top3_preserved=True,no_missing_outcome_imputed=True,no_recipe_mixing=True)
jwrite("verification.json",verification)
print(json.dumps(verification,ensure_ascii=False,indent=2))
print("CATALOG",json.dumps(catalog,ensure_ascii=False))
