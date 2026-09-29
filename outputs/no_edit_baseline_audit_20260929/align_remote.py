"""CPU audit: exact evaluation inputs, saved scores, and common-cohort aggregation."""
import collections,datetime,hashlib,json,math,os
from pathlib import Path
B=Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2")
P=B/"VisEdit-main"; S=B/"server_results"; ROOT=S/"no_edit_baseline_audit_20260929/aligned_v2"
ROOT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=True,indent=2))
def normmodel(m):return "qwen2.5-vl-3b-instruct" if m.startswith("qwen") else m
def read(p):return json.loads(Path(p).read_text())
def img(x,root):
    if x is None:return None
    return os.path.normpath(os.path.join(str(root),x))
def prompt_old(s):
    s=(s or "").strip()
    return s if s.endswith(":") else s+" The answer is:"
def items(d,root):
    def q(p,i,t):return dict(prompt=p,image=img(i,root),target=t)
    return {
        "Rel":q(d["src"]+" The answer is:",d["image"],d["alt"]),
        "T-Gen":q(d["rephrase"]+" The answer is:",d["image"],d["alt"]),
        "M-Gen":q(d["src"]+" The answer is:",d["image_rephrase"],d["alt"]),
        "T-Loc":q(d["loc"]+"?",None,d["loc_ans"]),
        "M-Loc":q(d["m_loc_q"]+" The answer is:",d["m_loc"],d["m_loc_a"])}
def olditems(d,root,mmke):
    def one(x):
        if isinstance(x,list):assert len(x)==1;x=x[0]
        return dict(prompt=prompt_old(x["prompt"]) if mmke else x["prompt"],
                    image=img(x.get("image"),root),target=x["target"],acc=x["acc"],
                    predict=x.get("predict_no_edit"))
    return {"Rel":one(d["reliability"]),
            "T-Gen":one(d["generality"]["text_rephrase"]),
            "M-Gen":one(d["generality"]["image_rephrase"]),
            "T-Loc":one(d["locality"]["text_loc"]),
            "M-Loc":one(d["locality"]["image_loc"])}
def key(d):
    return tuple((d[m]["prompt"],d[m]["image"],d[m]["target"]) for m in ["Rel","T-Gen","M-Gen"])
requests=read(ROOT/"requests.json")
groups=[];cache={};canonical={}
for req in requests:
    ds=req["dataset"];model=normmodel(req["model"])
    cfgpath=None;cfg=None;chosen=None
    for source in req["sources"]:
        p=Path(source)
        for c in [p/"eval_run_config.json",p/"run_config.json",p.parent/"run_config.json"]:
            if c.is_file():
                v=read(c)
                if v.get("eval_data") and Path(v["eval_data"]).is_file():
                    cfgpath=c;cfg=v;chosen=p;break
        if cfg is not None:break
    protocol_kind="run_config"
    if cfg is None and ds in canonical:
        reference=canonical[ds]
        expected_keys=[key(items(d,reference["eval_img_root"])) for d in read(reference["eval_data"])]
        for source in req["sources"]:
            for recorded in Path(source).rglob("results.json"):
                rows=read(recorded)
                if not isinstance(rows,list) or len(rows)!=len(expected_keys):continue
                try:recorded_keys=[key(olditems(r,reference["eval_img_root"],False)) for r in rows]
                except (KeyError,TypeError):continue
                if recorded_keys==expected_keys:
                    cfg=dict(reference);cfgpath=recorded;chosen=Path(source)
                    protocol_kind="all_recorded_edited_evaluation_inputs_match";break
            if cfg is not None:break
    if cfg is None:
        groups.append(dict(dataset=ds,model=model,status="NO_EDITED_PROTOCOL"));continue
    canonical[ds]=dict(eval_data=cfg["eval_data"],eval_img_root=cfg["eval_img_root"])
    datafile=Path(cfg["eval_data"]);imgroot=cfg["eval_img_root"]
    raw=read(datafile); expected={"evqa-pilot500":2093,"mmke-visual":293,"mmke-entity":954}[ds]
    assert len(raw)==expected,(ds,len(raw))
    current=[items(d,imgroot) for d in raw]
    if ds=="evqa-pilot500":
        oldroot=S/"no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148"/model
    else:
        oldroot=S/"no_edit_mmke_alt_eval_7models_20260612_161034"/ds.replace("mmke-","")/"alt"/model
    oldfile=oldroot/"no_edit_results.json";oldcfg=read(oldroot/"run_config.json")
    oldraw=read(oldfile)
    oldimgroot=oldcfg.get("eval_img_root") or str(Path(oldcfg["data_root"])/"data_image")
    previous=[olditems(d,oldimgroot,ds!="evqa-pilot500") for d in oldraw]
    lookup=collections.defaultdict(list)
    for i,d in enumerate(previous):lookup[key(d)].append(i)
    mapped=[];missing=[];used=set();loc_differences=collections.Counter()
    for i,d in enumerate(current):
        candidates=lookup.get(key(d),[])
        j=next((j for j in candidates if j not in used),None)
        if j is None:
            missing.append(i);mapped.append(None);continue
        used.add(j);before=previous[j]
        for m in ["T-Loc","M-Loc"]:
            for field in ["prompt","image","target"]:
                if before[m][field]!=d[m][field]:loc_differences[m+"."+field]+=1
        scores={m:before[m]["acc"] for m in ["Rel","T-Gen","M-Gen"]}
        assert all(isinstance(v,(float,int)) and math.isfinite(v) and 0<=v<=1 for v in scores.values())
        # No-edit locality is identity, independent of the old locality prompt.
        scores.update({"T-Loc":1.0,"M-Loc":1.0})
        mapped.append(dict(old_index=j,scores=scores))
    metrics=None
    if not missing:
        metrics={m:100*sum(r["scores"][m] for r in mapped)/len(mapped)
                 for m in ["Rel","T-Gen","M-Gen","T-Loc","M-Loc"]}
        metrics["Average"]=sum(metrics.values())/5
    exclusions=[dict(old_index=j,sample_id=oldraw[j].get("sample_id"),
                     image=previous[j]["Rel"]["image"],prompt=previous[j]["Rel"]["prompt"],
                     target_sha256=hashlib.sha256(previous[j]["Rel"]["target"].encode()).hexdigest())
                for j in range(len(oldraw)) if j not in used]
    out=ROOT/"groups"/ds/model;out.mkdir(parents=True,exist_ok=True)
    cohort=[dict(index=i,inputs=d,historical=mapped[i]) for i,d in enumerate(current)]
    write(out/"cohort.json",cohort)
    sample_indices=sorted(set(round(t*(len(raw)-1)/11) for t in range(12)))
    manifest=dict(dataset=ds,model=model,status="INPUTS_ALIGNED_PENDING_GPU_CHECK" if not missing else "NEEDS_CURRENT_PROTOCOL_REEVALUATION",
        sample_count=len(raw),historical_sample_count=len(oldraw),matched=len(used),missing_indices=missing,
        excluded=exclusions,historical_results=str(oldfile),historical_results_sha256=sha(oldfile),
        eval_data=str(datafile),eval_data_sha256=sha(datafile),eval_img_root=imgroot,
        edited_protocol_file=str(cfgpath),edited_protocol_sha256=sha(cfgpath),
        edited_protocol_kind=protocol_kind,edited_source=str(chosen),
        cohort_path=str(out/"cohort.json"),cohort_sha256=sha(out/"cohort.json"),
        locality_input_differences=dict(loc_differences),
        locality_baseline="identity agreement = 100; this is not reference-answer accuracy",
        historical_metrics_reaggregated=metrics,check_indices=sample_indices,
        time=datetime.datetime.now().astimezone().isoformat())
    write(out/"alignment.json",manifest);groups.append(manifest)
write(ROOT/"alignment.json",groups)
print(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),root=str(ROOT),groups=groups)))
