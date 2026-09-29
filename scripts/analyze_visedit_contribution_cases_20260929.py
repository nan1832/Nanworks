"""Audit contribution/editing counterexamples from existing frozen local results."""
import ast
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/visedit_contribution_cases_20260929"
VIS = ROOT / "outputs/all_methods_recommendations_20260928/visedit_full_rankings.json"
LEDGER = ROOT / "outputs/sweep_ledger_20260928_110311/ledger.json"
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
MODULES = ["attn", "mlp", "attn+mlp"]


def load(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def csvsave(name, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict,list)) else v for k,v in r.items()} for r in rows)


def rho(x,y):
    def rank(a):
        a=np.asarray(a)
        return (a[:,None]>a[None,:]).sum(axis=1)+(a[:,None]==a[None,:]).sum(axis=1)/2+.5
    x=rank(x);y=rank(y);x=x-x.mean();y=y-y.mean()
    den=np.linalg.norm(x)*np.linalg.norm(y)
    return float(np.dot(x,y)/den) if den else None


def evidence(row):
    return {k:row.get(k) for k in ["layer","recipe","epoch","raw_loss","ema_loss","samples","metrics","training","status","source","local_evidence"]}


def main():
    OUT.mkdir(exist_ok=True)
    ledger=load(LEDGER); vis=load(VIS)
    sources={ (r["dataset"],r["model"],r["target"]):r for r in vis
              if not r["historical"] and r["status"]=="done" and r.get("module")=="attn+mlp" and "paligemma" not in r["model"] }
    hashes=load(ROOT/"outputs/all_methods_recommendations_20260928/input_sha256.json")
    pool=collections.defaultdict(dict)
    for r in ledger["rows"]:
        if r["recipe"]=="main" and "paligemma" not in r["model"]:
            assert r["layer"] not in pool[r["dataset"],r["model"]]
            pool[r["dataset"],r["model"]][r["layer"]]=r
    assert len(sources)==36 and sum(map(len,pool.values()))==349
    pre_path=ROOT/"VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py"
    tree=ast.parse(pre_path.read_text(encoding="utf-8"))
    defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ["moving_average","find_high_region","pre_candidates"]]
    assert len(defs)==3
    ns={"np":np}
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(pre_path),"exec"),ns)
    all_rows=[]; aligned=[]; correlations=[]; comparisons=[]; source_manifest=[]
    for (ds,model,target),src in sources.items():
        path=ROOT/src["source"]
        assert sha(path)==hashes[src["source"]],src["source"]
        data=list(csv.DictReader(path.open(encoding="utf-8-sig")))
        data=sorted(data,key=lambda r:int(r["layer"]))
        depth=len(data);assert [int(r["layer"]) for r in data]==list(range(depth))
        existing=[r for r in vis if (r["dataset"],r["model"],r["target"])==(ds,model,target) and not r["historical"]]
        sample_count=(int(data[0]["valid_sample_count"]) if "valid_sample_count" in data[0] else None)
        if sample_count is None and (path.parent/"summary.json").is_file():
            sample_count=load(path.parent/"summary.json").get("sample_count")
        if "visedit_model_pred_mmke_20260929/results" in src["source"]:
            summary=load(path.parent/"summary.json"); verified=load(path.parent/"local_verification.json")
            assert verified["passed"] and verified["summary_sha256"]==sha(path.parent/"summary.json")
            assert sha(path)==summary["contribution_sha256"]
            assert summary["completed"]==summary["total"] and summary["failed"]==0
            sample_count=summary["completed"]
        source_manifest.append(dict(dataset=ds,model=model,target=target,attribution_scope=src["attribution_scope"],source=src["source"],sha256=sha(path),samples=sample_count))
        pp=pool[ds,model];ls=sorted(pp)
        middle=sorted(range(depth),key=lambda l:(abs(l-(depth-1)/2),l))[:3]
        oracle=min(ls,key=lambda l:(-pp[l]["metrics"]["Average"],l))
        for module in MODULES:
            signed=np.array([float(r["attn_mean"]) if module=="attn" else float(r["mlp_mean"]) if module=="mlp" else float(r["attn_mean"])+float(r["mlp_mean"]) for r in data])
            values=np.array([max(0,float(r["attn_mean"])) if module=="attn" else max(0,float(r["mlp_mean"])) if module=="mlp" else max(0,float(r["attn_mean"]))+max(0,float(r["mlp_mean"])) for r in data])
            assert np.isfinite(values).all()
            if module=="attn+mlp":
                assert np.allclose(values,[float(r["score_positive"]) for r in data],rtol=1e-7,atol=1e-12)
                order=[int(r["layer"]) for r in sorted(data,key=lambda r:(-float(r["score_positive"]),int(r["rank_positive"])))]
            else:
                order=[int(l) for l in np.argsort(-values)]
            region,threshold,_=ns["find_high_region"](ns["moving_average"](values,3),.5)
            pre=ns["pre_candidates"](region[0],3) if region else []
            match=next((r for r in existing if r.get("module")==module),None)
            if match:
                assert order==match["contribution_ranking"] and pre==match["top3"]
            peak=order[0]; top_ties=[l for l in range(depth) if values[l]==values[peak]]
            base=dict(dataset=ds,model=model,target=target,attribution_scope=src["attribution_scope"],module=module,samples=sample_count,source=src["source"])
            row=dict(**base,depth=depth,n_swept=len(ls),peak_layer=peak,peak_score=float(values[peak]),peak_ties=top_ties,
                peak_evaluated=peak in pp,peak_evidence=evidence(pp[peak]) if peak in pp else None,
                middle_layers=middle,middle_layer=middle[0],middle_evaluated=middle[0] in pp,
                middle_evidence=evidence(pp[middle[0]]) if middle[0] in pp else None,
                middle_score=float(values[middle[0]]),middle_contribution_rank=order.index(middle[0])+1,
                observed_best_average_layer=oracle,oracle_evidence=evidence(pp[oracle]),oracle_score=float(values[oracle]),oracle_rank=order.index(oracle)+1,
                pre_layers=pre,pre_missing=[l for l in pre if l not in pp],high_region=list(region),
                middle_missing=[l for l in middle if l not in pp])
            for m in METRICS:
                row["rho_"+m]=rho(values[ls],[pp[l]["metrics"][m] for l in ls])
            if peak in pp:
                row["oracle_minus_peak"]={m:pp[oracle]["metrics"][m]-pp[peak]["metrics"][m] for m in METRICS}
            if peak in pp and middle[0] in pp:
                row["middle_minus_peak"]={m:pp[middle[0]]["metrics"][m]-pp[peak]["metrics"][m] for m in METRICS}
                row["middle_strictly_lower_contribution"]=bool(values[middle[0]]<values[peak]-1e-12)
                row["both_peak_middle_50epochs"]=all(pp[l]["training"]=="50轮已核验" for l in [peak,middle[0]])
            for kind,candidate in [("contribution_top3",order[:3]),("pre",pre),("middle",middle)]:
                complete=len(candidate)==3 and all(l in pp for l in candidate)
                row[kind+"_complete"]=complete
                row[kind+"_performance"]={m:dict(top1=pp[candidate[0]]["metrics"][m],best3=max(pp[l]["metrics"][m] for l in candidate),mean3=float(np.mean([pp[l]["metrics"][m] for l in candidate]))) for m in METRICS} if complete else None
            all_rows.append(row)
            for l in range(depth):
                aligned.append(dict(**base,layer=l,positive_contribution=float(values[l]),signed_contribution=float(signed[l]),contribution_rank=order.index(l)+1,
                    evaluated=l in pp,**(pp[l]["metrics"] if l in pp else {}),training=pp[l]["training"] if l in pp else None))
            for metric in METRICS:
                correlations.append(dict(**base,metric=metric,n_layers=len(ls),rho=row["rho_"+metric]))
                if row["pre_complete"] and row["middle_complete"]:
                    comparisons.append(dict(**base,metric=metric,pre_layers=pre,middle_layers=middle,
                        **{measure+"_delta_pre_minus_middle":row["pre_performance"][metric][measure]-row["middle_performance"][metric][measure] for measure in ["top1","best3","mean3"]}))
    summary=[]
    for target in ["alt","model_pred"]:
        for module in MODULES:
            rr=[r for r in all_rows if r["target"]==target and r["module"]==module]
            peak=[r for r in rr if r["peak_evaluated"]]
            mid=[r for r in rr if "middle_minus_peak" in r and r["middle_strictly_lower_contribution"]]
            summary.append(dict(target=target,module=module,groups=len(rr),peak_evaluated=len(peak),
                peak_not_observed_average_best=sum(r["oracle_minus_peak"]["Average"]>1e-8 for r in peak),
                peak_regret_over_1pp=sum(r["oracle_minus_peak"]["Average"]>1 for r in peak),
                middle_comparable=len(mid),middle_beats_peak_all_rel_gen_avg=sum(all(r["middle_minus_peak"][m]>1e-8 for m in ["Rel","T-Gen","M-Gen","Average"]) for r in mid),
                middle_loses_to_peak_all_rel_gen_avg=sum(all(r["middle_minus_peak"][m]<-1e-8 for m in ["Rel","T-Gen","M-Gen","Average"]) for r in mid),
                pre_middle_complete=sum(r["pre_complete"] and r["middle_complete"] for r in rr)))
    result=dict(ledger_snapshot=ledger["updated_at"],n_real_edit_rows=349,groups=18,source_groups=36,module_target_groups=len(all_rows),summary=summary,rows=all_rows,
        inputs=dict(ledger_sha256=sha(LEDGER),visedit_rankings_sha256=sha(VIS),pre_implementation_sha256=sha(pre_path)),sources=source_manifest)
    save("analysis.json",result);csvsave("layer_alignment.csv",aligned);csvsave("correlations.csv",correlations);csvsave("pre_vs_middle.csv",comparisons);csvsave("coverage_summary.csv",summary)
    peak_cases=[r for r in all_rows if r.get("both_peak_middle_50epochs") and r.get("middle_strictly_lower_contribution") and all(r["middle_minus_peak"][m]>1 for m in ["Rel","T-Gen","M-Gen","Average"])]
    def concise(r):
        return {k:r[k] for k in ["dataset","model","target","module","peak_layer","peak_score","middle_layer","middle_score","middle_contribution_rank","middle_minus_peak","pre_layers","pre_missing","rho_Average"]}
    print(json.dumps(dict(summary=summary,audited_counterexamples=[concise(r) for r in sorted(peak_cases,key=lambda r:-r["middle_minus_peak"]["Average"])[:25]]),ensure_ascii=False))


if __name__=="__main__":
    main()
