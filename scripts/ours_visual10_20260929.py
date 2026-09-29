"""User-approved ten visual-gradient ablations. No parameter training or generation.

Immutable historical inputs; isolated outputs; per-sample nonlinear aggregation.
CPU publication validates full cohorts/hashes/reproduction before exposing scores.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
SERVER = BASE / 'server_results'
ROOT = SERVER / 'ours_visual10_20260929'
LEGACY = SERVER / 'lga_two_spaces_ablation_20260928'
MODELS = {'blip2-opt-2.7b':32, 'instructblip-vicuna-7b':32,
          'minigpt-4-vicuna-7b':32, 'llava-v1.5-7b':32,
          'qwen2.5-vl-3b':36, 'paligemma-3b':18, 'smolvlm-1.7b':24}
DATASETS = {'evqa-pilot500':500, 'mmke-visual':214, 'mmke-entity':636}
FORMULAS = {'V01':'E[a]', 'V02':'E[b]', 'V03':'E[c]', 'V04':'E[abs(c)]',
            'V05':'E[c*a]', 'V06':'E[abs(c)*a]', 'V07':'E[c*b]',
            'V08':'E[abs(c)*b]', 'V09':'E[c*b*a]', 'V10':'E[abs(c)*b*a]'}
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
QPY = str(BASE / 'envs/qwen25vl/bin/python')


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def write(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.partial')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    tmp.replace(p)


def source(ds, model):
    run = 'ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304' if model.startswith('qwen') else 'ours_direct_7models_3datasets_g08_gpu0_20260626_131624'
    return SERVER/run/ds/model


def baseline(ds, model):
    p = source(ds, model)/'ours_direct_layer_scores.csv'
    with p.open(encoding='utf-8-sig') as f:
        rows = sorted(csv.DictReader(f), key=lambda r:int(r['layer']))
    assert [int(r['layer']) for r in rows] == list(range(MODELS[model]))
    assert len({int(r['n_request']) for r in rows}) == 1
    return rows


def formula_values(s):
    a,b,c,d = (float(s[k]) for k in ['old_norm','new_norm','cos','dot'])
    assert all(math.isfinite(v) for v in [a,b,c,d]) and min(a,b)>=0
    assert math.isclose(c, d/(a*b+1e-12), rel_tol=1e-10, abs_tol=1e-12)
    values = [a,b,c,abs(c),c*a,abs(c)*a,c*b,abs(c)*b,c*b*a,abs(c)*b*a]
    assert all(math.isfinite(v) for v in values)
    return dict(zip(FORMULAS, values))


def quantile(values, q):
    import numpy as np
    try:return float(np.quantile(values,q,method='linear'))
    except TypeError:return float(np.quantile(values,q,interpolation='linear'))


def rank(values):
    assert values and all(math.isfinite(v) for v in values)
    q1,q3=quantile(values,.25),quantile(values,.75)
    low,high=q1-(q3-q1),q3+(q3-q1)
    raw=sorted(range(len(values)),key=lambda l:(-values[l],l))
    clean=[l for l in raw if low<=values[l]<=high]
    return dict(raw_top3=raw[:3],raw_top5=raw[:5],raw_ranking=raw,
                top3=clean[:3],top5=clean[:5],ranking=clean,
                excluded=[l for l,v in enumerate(values) if not low<=v<=high],
                q1=q1,q3=q3,lower=low,upper=high,scores=values)


def verify_full(p, ds, model, historical):
    s=read(p/'summary.json'); assert s['status']=='done'
    n=int(historical[0]['n_request']); assert s['sample_count']==n
    for name,key in [('protocol.json','protocol_sha256'),('layer_scores.json','score_sha256'),('historical_reproduction.json','reproduction_sha256')]:
        assert sha(p/name)==s[key], str(p/name)
    protocol=read(p/'protocol.json')
    for name in ['ours_direct_layer_scores.csv','ours_direct_sample_layer_scores.jsonl','model_pred_cache.jsonl']:
        src=source(ds,model)/name
        assert protocol['files'][str(src)]==sha(src), 'Historical source changed: '+str(src)
    records=[]
    for name,digest in s['sample_files'].items():
        f=p/'samples'/name; assert sha(f)==digest
        records.append(read(f))
    assert len(records)==n==len({r['sample_id'] for r in records})
    cohort={r['sample_id']:r for r in protocol['cohort']}
    assert set(cohort)=={r['sample_id'] for r in records}
    for r in records:
        assert all(r[k]==cohort[r['sample_id']][k] for k in ['sample_i','old','new'])
        assert set(r['layers'])=={str(l) for l in range(MODELS[model])}
    score_rows=[]; checks=[]
    for l,h in enumerate(historical):
        pairs=[r['layers'][str(l)] for r in records]
        vals=[formula_values(pair) for pair in pairs]
        row={k:math.fsum(v[k] for v in vals)/n for k in FORMULAS}
        score_rows.append(row)
        for field,col in [('dot','S_v_dot'),('cos','S_v_cos'),('old_norm','S_v_old_norm'),('new_norm','S_v_new_norm')]:
            actual=math.fsum(float(v[field]) for v in pairs)/n
            checks.append(math.isclose(actual,float(h[col]),rel_tol=1e-3,abs_tol=1e-8))
        joint=math.fsum(float(v['old_norm'])*float(v['new_norm']) for v in pairs)/n
        checks.append(math.isclose(joint,float(h['S_v_joint_norm']),rel_tol=1e-3,abs_tol=1e-8))
    assert all(checks), 'Historical reproduction failed'
    return score_rows, dict(path=str(p),summary_sha256=sha(p/'summary.json'),verified_samples=n,
                            baseline_checks=len(checks),all_passed=True)


def publish_group(ds, model):
    h=baseline(ds,model); n=int(h[0]['n_request'])
    result=dict(dataset=ds,model=model,n=n,total=DATASETS[ds],time=now(),formulas={},
                zero_layers=[int(r['layer']) for r in h if str(r['S_v_zero_grad']).lower()=='true'],
                historical_source=str(source(ds,model)),baseline_sha256=sha(source(ds,model)/'ours_direct_layer_scores.csv'))
    full=None
    for p in [ROOT/'raw/visual'/ds/model,LEGACY/'results/visual'/ds/model]:
        if (p/'summary.json').exists() and read(p/'summary.json').get('status')=='done':
            full,evidence=verify_full(p,ds,model,h); result['evidence']=evidence;break
    if full is not None:
        for k in FORMULAS:result['formulas'][k]=dict(rank([r[k] for r in full]),source_kind='verified_sample_products')
    else:
        for k,col in [('V01','S_v_old_norm'),('V02','S_v_new_norm'),('V03','S_v_cos')]:
            result['formulas'][k]=dict(rank([float(r[col]) for r in h]),source_kind='historical_linear_mean')
    result['status']='done' if len(result['formulas'])==10 else 'pending_cross_terms'
    write(ROOT/'published'/ds/(model+'.json'),result)
    return result


def publish():
    results=[publish_group(ds,m) for ds in DATASETS for m in MODELS]
    manifest=dict(time=now(),formula_definitions=FORMULAS,
                  complete_groups=sum(r['status']=='done' for r in results),
                  complete_formula_groups=sum(len(r['formulas']) for r in results),expected_formula_groups=210,
                  files={str((Path('published')/r['dataset']/(r['model']+'.json'))):sha(ROOT/'published'/r['dataset']/(r['model']+'.json')) for r in results})
    write(ROOT/'manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'}),flush=True)


def run_group(ds, model):
    # Frozen helper copied from the audited collector. Only its visual functions are used.
    import run_lga_two_space_ablation as original
    import torch
    args=argparse.Namespace(project_dir=str(BASE/'VisEdit-main'),source_root=str(SERVER),
        out_root=str(ROOT/'raw'),space='visual',dataset=ds,model=model,device='cuda:0',
        layer_batch_size=4,stop_after=0,preflight=False)
    helper,_,cfg,h,cohort,out,vllm=original.prepare(args)
    modules={l:helper.find_module(vllm.model,cfg.layer_module_tmp.format(l)) for l in range(MODELS[model])}
    validation=out/'gradient_execution.json'
    mode=read(validation)['mode'] if validation.exists() else None
    start=time.time()
    for i,item in enumerate(cohort):
        p=out/'samples'/('%06d.json'%item['sample_i'])
        oldp=LEGACY/'results/visual'/ds/model/'samples'/p.name
        if p.exists():rec=read(p)
        elif oldp.exists():
            rec=read(oldp)
            assert all(rec[k]==item[k] for k in ['sample_id','sample_i','old','new'])
            if len(rec['layers'])==MODELS[model]:
                for s in rec['layers'].values():formula_values(s)
                write(p,rec)
        else:rec=dict(sample_i=item['sample_i'],sample_id=item['sample_id'],old=item['old'],new=item['new'],layers={})
        assert all(rec[k]==item[k] for k in ['sample_id','sample_i','old','new'])
        if len(rec['layers'])==MODELS[model]:continue
        req=item['row']['request']; prompt,image=req['prompt'],req['image']
        use_single=mode=='original_single_layer'
        old=new=None;ol=nl=None;span=None
        if not use_single:
            ol,old,span=original.visual_all_grads(helper,vllm,modules,prompt,image,item['old'])
            nl,new,span2=original.visual_all_grads(helper,vllm,modules,prompt,image,item['new']);assert span==span2
            if mode is None:
                checks=[]
                try:
                    for l in sorted({0,MODELS[model]//2,MODELS[model]-1}):
                        for target,grads in [(item['old'],old),(item['new'],new)]:
                            single=helper.compute_virtual_delta_target_grad(vllm,modules[l],prompt,image,target,1e-8)
                            torch.testing.assert_close(grads[l],single['visual_grad'],rtol=1e-5,atol=1e-7)
                            checks.append(dict(layer=l,max_abs_error=float((grads[l]-single['visual_grad']).abs().max())))
                    mode='validated_multihook'
                    write(validation,dict(mode=mode,checks=checks,rtol=1e-5,atol=1e-7))
                except AssertionError as exc:
                    mode='original_single_layer';use_single=True;old=new=None
                    write(validation,dict(mode=mode,reason=str(exc),tolerance_not_relaxed=True))
        for l in modules:
            if use_single:
                a=helper.compute_virtual_delta_target_grad(vllm,modules[l],prompt,image,item['old'],1e-8)
                b=helper.compute_virtual_delta_target_grad(vllm,modules[l],prompt,image,item['new'],1e-8)
                stats=helper.grad_stats(a['visual_grad'],b['visual_grad'],1e-8)
            else:stats=helper.grad_stats(old[l],new[l],1e-8)
            rec['layers'][str(l)]=original.cross_stats(stats)
        write(p,rec);old=new=None;vllm.model.zero_grad(set_to_none=True);torch.cuda.empty_cache()
        progress=dict(time=now(),dataset=ds,model=model,processed=i+1,total=len(cohort),mode=mode,elapsed_seconds=time.time()-start)
        write(out/'progress.json',progress);print(json.dumps(progress),flush=True)
    records=[read(out/'samples'/('%06d.json'%i['sample_i'])) for i in cohort]
    rows=original.aggregate(records,[i['sample_id'] for i in cohort],MODELS[model])
    checks=[dict(layer=r['layer'],field=k,passed=math.isclose(r[k],float(prev[col]),rel_tol=1e-3,abs_tol=1e-8))
        for r,prev in zip(rows,h) for k,col in [('dot','S_v_dot'),('cos','S_v_cos'),('old_norm','S_v_old_norm'),('new_norm','S_v_new_norm'),('no_direction','S_v_joint_norm')]]
    write(out/'historical_reproduction.json',checks)
    write(out/'layer_scores.json',dict(rows=rows))
    summary=dict(status='done' if all(c['passed'] for c in checks) else 'needs_reproduction_review',time=now(),
        sample_count=len(cohort),collector_sha256=sha(Path(__file__)),score_sha256=sha(out/'layer_scores.json'),protocol_sha256=sha(out/'protocol.json'),
        reproduction_sha256=sha(out/'historical_reproduction.json'),baseline_failures=sum(not c['passed'] for c in checks),
        sample_files={p.name:sha(p) for p in (out/'samples').glob('*.json')})
    write(out/'summary.json',summary);assert summary['status']=='done','Historical reproduction failed'
    publish_group(ds,model)


def queue():
    import fcntl
    assert os.uname()[1].split('.')[0]=='g08'
    assert 'job_3435286' in Path('/proc/self/cgroup').read_text(), 'Not in approved allocation'
    os.environ['SLURM_JOB_ID']='3435286'
    control=ROOT/'control';control.mkdir(parents=True,exist_ok=True)
    own=(control/'controller.lock').open('a');fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
    pins=read(control/'code_pins.json')
    def state(name,**kw):
        d=dict(state=name,time=now(),job='3435286',node='g08',pid=os.getpid(),**kw)
        write(control/'status.json',d);print(json.dumps(d),flush=True)
    def check():
        for name,digest in pins.items():assert sha(name)==digest,'Code changed'
        assert subprocess.check_output(['squeue','-j','3435286','-h','-o','%T %N'],universal_newlines=True).strip()=='RUNNING g08'
        if (control/'STOP').exists():raise RuntimeError('New queue STOP requested')
    outcomes=[]
    order=['smolvlm-1.7b','paligemma-3b','qwen2.5-vl-3b','llava-v1.5-7b','instructblip-vicuna-7b','blip2-opt-2.7b','minigpt-4-vicuna-7b']
    for m in order:
        for ds in DATASETS:
            if publish_group(ds,m)['status']=='done':continue
            stable=0;lock=None
            while lock is None:
                check()
                free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True).strip())
                stable=stable+1 if free>=60000 else 0
                state('WAITING_GPU_MEMORY_OR_LOCK',model=m,dataset=ds,free_mib=free,required_mib=60000,stable=stable)
                if stable>=3:
                    f=(SERVER/'gpu_locks/g08_gpu0.lock').open('a')
                    try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError:f.close();stable=0
                    else:lock=f
                if lock is None:time.sleep(20)
            try:
                check()
                # Guard the allocation again after acquiring the project lock.
                free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True).strip())
                assert free>=60000,'VRAM changed while obtaining lock'
                log=control/(m+'_'+ds+'_'+time.strftime('%H%M%S')+'.log')
                env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONUNBUFFERED='1')
                command=[QPY if m.startswith('qwen') else PY,'-u',str(Path(__file__).resolve()),'run','--dataset',ds,'--model',m]
                with log.open('x') as f:
                    child=subprocess.Popen(command,env=env,cwd=str(BASE/'VisEdit-main'),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
                    state('RUNNING_OURS_VISUAL10',model=m,dataset=ds,child_pid=child.pid,log=str(log),outcomes=outcomes)
                    rc=child.wait()
                outcomes.append(dict(model=m,dataset=ds,returncode=rc,log=str(log)))
                write(control/'outcomes.json',outcomes)
                publish()
                if rc:state('GROUP_FAILED_PRESERVED',outcomes=outcomes)
            finally:lock.close()
    publish();manifest=read(ROOT/'manifest.json')
    state('DONE' if manifest['complete_groups']==21 else 'FINISHED_WITH_PENDING',outcomes=outcomes,complete_groups=manifest['complete_groups'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','run','queue']);p.add_argument('--dataset',choices=list(DATASETS));p.add_argument('--model',choices=list(MODELS));a=p.parse_args()
    if a.action=='publish':publish()
    elif a.action=='run':run_group(a.dataset,a.model)
    else:
        try:queue()
        except Exception:
            write(ROOT/'control/failure.json',dict(time=now(),error=traceback.format_exc()));raise
