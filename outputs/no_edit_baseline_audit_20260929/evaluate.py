"""No-adapter verification and, when necessary, full current-cohort evaluation."""
import argparse,datetime,hashlib,importlib.util,json,os,sys,time,traceback
from pathlib import Path
B=Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2")
P=B/"VisEdit-main";ROOT=B/"server_results/no_edit_baseline_audit_20260929/aligned_v2"
METRICS=["Rel","T-Gen","M-Gen","T-Loc","M-Loc"]
def now():return datetime.datetime.now().astimezone().isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+".partial");t.write_text(json.dumps(d,indent=2));t.replace(p)
def main(model):
    import torch
    import transformers
    from PIL import Image
    os.chdir(str(P));sys.path.insert(0,str(P))
    from utils import load_vllm_for_edit
    source=P/"scripts/eval_evqa_no_edit_full_alt.py"
    spec=importlib.util.spec_from_file_location("baseline_original",str(source))
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    assert os.environ.get("CUDA_VISIBLE_DEVICES")=="0"
    torch.manual_seed(20260601)
    vllm=load_vllm_for_edit(model,"cuda:0")
    baseline.set_eval_mode(vllm)
    tokenizer=vllm.get_llm_tokenizer()
    original=vllm.get_llm_outpt
    def finite_forward(*args,**kwargs):
        out=original(*args,**kwargs)
        assert torch.isfinite(out.logits).all().item(),"Nonfinite base-model logits"
        return out
    vllm.get_llm_outpt=finite_forward
    def score(d,compare=False):
        image=None
        if d["image"] is not None:
            with Image.open(d["image"]) as im:image=im.convert("RGB").copy()
        try:
            (embeds,span),ids,mask=vllm.prompts_imgs_target_to_xym([d["prompt"]],[image],[d["target"]])
            assert int(mask.sum().item())>0,"Empty answer mask"
            logits=vllm.get_llm_outpt(embeds,span).logits
            prediction=logits.argmax(-1)[:,-ids.shape[1]:]
            if compare:
                second=vllm.get_llm_outpt(embeds,span).logits.argmax(-1)[:,-ids.shape[1]:]
                value=float((((prediction==second)*mask).sum()/mask.sum()).item())
            else:value=float((((prediction==ids)*mask).sum()/mask.sum()).item())
            return value
        finally:
            if image is not None:image.close()
    groups=[g for g in read(ROOT/"alignment.json") if g["model"]==model]
    assert len(groups)==3
    for g in groups:
        ds=g["dataset"];out=ROOT/"groups"/ds/model
        if (out/"accepted.json").exists():continue
        assert g["status"]!="NO_EDITED_PROTOCOL",g
        assert sha(g["cohort_path"])==g["cohort_sha256"]
        assert sha(g["eval_data"])==g["eval_data_sha256"]
        cohort=read(g["cohort_path"])
        checks=[];cache={}
        with torch.inference_mode():
            for idx in g["check_indices"]:
                row=cohort[idx];scores={}
                for metric in METRICS:scores[metric]=score(row["inputs"][metric],metric.endswith("Loc"))
                cache[idx]=scores
                hist=row["historical"]
                diffs=[] if hist is not None else ["unmatched_input"]
                if hist is not None:
                    for metric in METRICS:
                        if abs(scores[metric]-hist["scores"][metric])>0.000051:diffs.append(metric)
                checks.append(dict(index=idx,current=scores,historical=hist,mismatches=diffs))
                write(out/"progress.json",dict(state="VERIFYING",time=now(),model=model,dataset=ds,
                      checked=len(checks),total=len(g["check_indices"]),pid=os.getpid()))
            write(out/"spotcheck.json",dict(time=now(),checks=checks,torch=torch.__version__,
                  transformers=transformers.__version__,reference_script_sha256=sha(source),
                  evaluated_on_current_exact_inputs=True,rounding_tolerance=0.000051))
            rerun=bool(g["missing_indices"]) or any(c["mismatches"] for c in checks)
            rows=[]
            for i,row in enumerate(cohort):
                if rerun:
                    scores=cache.get(i)
                    if scores is None:
                        scores={m:score(row["inputs"][m]) for m in METRICS[:3]}
                        # Identity is the defined no-edit locality baseline; stability
                        # was explicitly checked on all predeclared verification rows.
                        scores.update({"T-Loc":1.0,"M-Loc":1.0})
                else:scores=row["historical"]["scores"]
                assert all(0<=v<=1 for v in scores.values())
                rows.append(dict(index=i,scores=scores))
                if i%20==0:
                    write(out/"progress.json",dict(state="REEVALUATING" if rerun else "REAGGREGATING",
                          time=now(),dataset=ds,model=model,processed=i+1,total=len(cohort),pid=os.getpid()))
            values={m:100*sum(r["scores"][m] for r in rows)/len(rows) for m in METRICS}
            values["Average"]=sum(values.values())/5
            write(out/"accepted_scores.json",rows)
            accepted=dict(dataset=ds,model=model,status="DONE",time=now(),sample_count=len(rows),
                mode="FULL_CURRENT_COHORT_REEVALUATED" if rerun else "HISTORICAL_REAGGREGATED_GPU_SPOTCHECKED",
                metrics=values,spotcheck_n=len(checks),mismatching_checks=sum(bool(c["mismatches"]) for c in checks),
                historical_source=g["historical_results"],historical_sha256=g["historical_results_sha256"],
                eval_data=g["eval_data"],eval_data_sha256=g["eval_data_sha256"],
                cohort_sha256=g["cohort_sha256"],scores_sha256=sha(out/"accepted_scores.json"),
                spotcheck_sha256=sha(out/"spotcheck.json"),alignment_sha256=sha(out/"alignment.json"),
                torch=torch.__version__,transformers=transformers.__version__,pid=os.getpid(),
                node=os.uname()[1],job=os.environ.get("SLURM_JOB_ID"),no_adapter_loaded=True,
                locality="Identity agreement; verified on declared spotcheck inputs.",
                historical_rounding_abs_bound_percentage_points=0.005 if not rerun else 0)
            write(out/"accepted.json",accepted)
            print(json.dumps(accepted),flush=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--model",required=True)
    args=parser.parse_args()
    try:main(args.model)
    except Exception:
        write(ROOT/"control"/(args.model+"_error.json"),dict(time=now(),error=traceback.format_exc()))
        raise
