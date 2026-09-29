"""Diagnose FP16 nonfinite outputs and recompute both Qwen groups uniformly in BF16.

The original failed FP16 run remains immutable. Uses the existing per-group GPU lock.
"""
import base64
import csv
import fcntl
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from run_visedit_model_pred_mmke_20260929 import aggregate, reference, sha, write, now

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
ORIGINAL = BASE/'server_results/visedit_model_pred_mmke_20260929'
ROOT = ORIGINAL/'qwen_repair_bf16_v2'
PROJECT = BASE/'VisEdit-main'
MODEL = 'qwen2.5-vl-3b'
DATA = BASE/'datasets/MMKE-Bench'
SOURCE = ORIGINAL/'source_snapshot'


def state(name, **kwargs):
    value = dict(state=name,time=now(),job='3435286',node='g08',pid=os.getpid(),**kwargs)
    write(ROOT/'control/status.json',value)
    print(json.dumps(value),flush=True)


def admission():
    assert os.uname().nodename.split('.')[0] == 'g08'
    assert 'job_3435286' in Path('/proc/self/cgroup').read_text(), 'Wrong allocation'
    own=(ROOT/'control/runner.lock').open('a')
    fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
    lockpath=BASE/'server_results/gpu_locks/g08_gpu0.lock'
    while True:
        if (ROOT/'control/STOP').exists():
            raise RuntimeError('Repair STOP marker found')
        assert subprocess.check_output(['squeue','-j','3435286','-h','-o','%T %N'],universal_newlines=True).strip()=='RUNNING g08'
        lock=lockpath.open('a')
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close();state('WAITING_PROJECT_GPU_LOCK');time.sleep(10);continue
        free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True).strip())
        if free >= 45000:
            state('GPU_ADMITTED',free_mib=free);return own,lock
        lock.close();state('WAITING_GPU_MEMORY',free_mib=free);time.sleep(10)


def tensor_summary(value):
    import torch
    if isinstance(value,(list,tuple)): value=value[0]
    if not torch.is_tensor(value):return None
    finite=torch.isfinite(value)
    return dict(shape=list(value.shape),dtype=str(value.dtype),finite=bool(finite.all()),
                nan=int(torch.isnan(value).sum()),inf=int(torch.isinf(value).sum()),
                max_finite_abs=float(value[finite].abs().max()) if bool(finite.any()) else None)


def make_runner(ref,cfg,dtype):
    import torch
    runner=ref.build_runner(MODEL,ref.MODEL_SPECS[MODEL],cfg,'cuda:0',dtype,None)
    original=runner.predict_id
    def predict(word,logits):
        runner.last_logits_summary=tensor_summary(logits[0,-1])
        if not runner.last_logits_summary['finite']:
            raise FloatingPointError('Nonfinite next-token logits')
        result=original(word,logits)
        runner.last_target_id=int(result)
        return result
    runner.predict_id=predict
    return runner


def sample_input(dataset,i):
    from PIL import Image
    raw=json.loads((DATA/'data_json'/(dataset+'_train.json')).read_text())
    row=raw[i]
    path=Path(row['image'])
    if not path.is_absolute():path=DATA/'data_image'/path
    with Image.open(path) as img:image=img.convert('RGB').copy()
    return row,str(row['src'])+' The answer is:',path,image


def diagnose(runner,dtype):
    import torch
    import numpy as np
    cases=[('visual',0,False),('visual',137,True),('visual',181,True),('visual',207,True),
           ('entity',0,False),('entity',1,True),('entity',16,True),('entity',22,True)]
    records=[]
    for ds,i,failed in cases:
        row,prompt,path,image=sample_input(ds,i)
        activations={};handles=[]
        def hook(name):
            def capture(module,args,output):
                if name in activations:return
                # The complete vocabulary tensor may exceed INT_MAX. Inspect the
                # actual scored prediction position; keep decoder/vision outputs whole.
                value=output[0,-1] if name=='lm_head' and output.ndim==3 else output
                activations[name]=tensor_summary(value)
                if name=='lm_head':activations[name]['scope']='final prompt position'
            return capture
        for name,module in runner.model.named_modules():
            # Whole vision stack plus each decoder layer identifies where failure first appears.
            if name=='visual' or (name.startswith('model.layers.') and name.count('.')==2) or name in ['model.norm','lm_head']:
                handles.append(module.register_forward_hook(hook(name)))
        result=dict(dataset='mmke-'+ds,sample_idx=i,previously_failed=failed,dtype=dtype,image_sha256=sha(path),prompt=prompt)
        try:
            with torch.no_grad():p,v=runner.trace_one(prompt,image,None)
            assert all(np.isfinite(x).all() for x in list(p.values())+list(v.values()))
            result.update(finite=True,target_id=runner.last_target_id,target_token=runner.tokenizer.decode([runner.last_target_id]))
            old=ORIGINAL/'results'/('mmke-'+ds)/MODEL/'samples'/('%06d.json'%i)
            if old.exists():
                previous=json.loads(old.read_text())
                result['old_target_id']=previous['target_id']
                result['target_matches_old_fp16']=previous['target_id']==runner.last_target_id
                result['max_abs_p_delta_from_old_fp16']=max(float(np.max(np.abs(np.asarray(p[k])-np.asarray(previous['p'][k])))) for k in p)
                result['max_abs_v_delta_from_old_fp16']=max(float(np.max(np.abs(np.asarray(v[k])-np.asarray(previous['v'][k])))) for k in v)
        except (FloatingPointError,AssertionError):
            result.update(finite=False,error=traceback.format_exc())
        finally:
            for handle in handles:handle.remove()
        result['activations']=activations
        result['next_token_logits']=getattr(runner,'last_logits_summary',None)
        records.append(result)
        write(ROOT/'diagnostics'/('%s_%s_%06d.json'%(dtype,ds,i)),result)
        state('DIAGNOSING',dtype=dtype,dataset=ds,sample_idx=i,finite=result['finite'])
        torch.cuda.empty_cache()
    return records


def run_dataset(runner,ref,cfg,ds,expected,diagnosis):
    import torch
    import numpy as np
    out=ROOT/'results'/('mmke-'+ds)/MODEL
    datafile=DATA/'data_json'/(ds+'_train.json')
    raw=json.loads(datafile.read_text());assert len(raw)==expected
    old_protocol=ORIGINAL/'results'/('mmke-'+ds)/MODEL/'protocol.json'
    cfgpath=PROJECT/'configs/p_track/qwen2.5-vl-3b.yaml'
    protocol=dict(dataset='mmke-'+ds,model=MODEL,key_mode='model_pred',attribution_scope='next_token_argmax',
                  sample_count=expected,num_layers=cfg.num_layers,dataset_path=str(datafile),dataset_sha256=sha(datafile),
                  cfg_path=str(cfgpath),cfg_sha256=sha(cfgpath),source_sha256={p.name:sha(p) for p in SOURCE.iterdir() if p.is_file()},
                  runner_sha256=sha(__file__),original_runner_sha256=sha(ORIGINAL/'code/run_visedit_model_pred_mmke_20260929.py'),
                  original_fp16_protocol_sha256=sha(old_protocol),torch_dtype='bfloat16',
                  torch_version=torch.__version__,numpy_version=np.__version__,
                  target_rule='next-token argmax at final prompt position; no answer teacher forcing',
                  prompt_rule="row['src'] + ' The answer is:'",loader='qwen25vl',
                  precision_change='Original auto hard-coded float16; recompute all samples in config-native bfloat16, never mix precisions',
                  diagnosis_sha256=sha(diagnosis),model_config_sha256=sha(PROJECT/'models/Qwen2.5-VL-3B-Instruct/config.json'),
                  contribution_rule='sign(v/M)*sqrt(abs(v/M)+1e-12)*sqrt(max(p,0)); M=max_abs_attn_mlp_per_sample',
                  aggregate_rule='mean signed contribution first; clip each module mean to nonnegative; sum for attn+mlp',
                  pre_rule='window=3; mean+0.5 population std; longest high region; precede by up to 3 layers',
                  tie_rule='numpy argsort(-scores), matching original contribution rank_positive',server_result_path=str(out))
    old=json.loads(old_protocol.read_text())
    assert protocol['dataset_sha256']==old['dataset_sha256'] and protocol['cfg_sha256']==old['cfg_sha256']
    if (out/'protocol.json').exists():assert json.loads((out/'protocol.json').read_text())==protocol
    else:write(out/'protocol.json',protocol)
    ph=sha(out/'protocol.json');records=[];errors=[];start=time.time()
    for i,row in enumerate(raw):
        sample=out/'samples'/('%06d.json'%i)
        try:
            if sample.exists():
                result=json.loads(sample.read_text());assert result['protocol_sha256']==ph and result['sample_idx']==i
            else:
                row,prompt,path,image=sample_input(ds,i)
                with torch.no_grad():p,v=runner.trace_one(prompt,image,None)
                assert all(len(x)==cfg.num_layers and np.isfinite(x).all() for x in list(p.values())+list(v.values()))
                result=dict(sample_idx=i,sample_id=row.get('case_id',row.get('id',i)),prompt=prompt,image=str(path),image_sha256=sha(path),
                            protocol_sha256=ph,target_id=runner.last_target_id,target_token=runner.tokenizer.decode([runner.last_target_id]),p=p,v=v)
                write(sample,result)
            records.append(result)
        except Exception:
            err=dict(sample_idx=i,time=now(),error=traceback.format_exc());write(out/'failures'/('%06d.json'%i),err);errors.append(err)
            torch.cuda.empty_cache()
            if len(errors)>=3:break
        if (i+1)%25==0 or i+1==expected:
            progress=dict(state='RUNNING',time=now(),dataset='mmke-'+ds,model=MODEL,completed=len(records),total=expected,failed=len(errors),elapsed_seconds=time.time()-start)
            write(out/'progress.json',progress);print(json.dumps(progress),flush=True)
    if len(records)!=expected:
        write(out/'progress.json',dict(state='INCOMPLETE',completed=len(records),total=expected,failed=len(errors),time=now()))
        raise RuntimeError('BF16 run still incomplete: '+ds)
    rows,variants=aggregate(records,cfg.num_layers,SOURCE)
    ps={k:np.array([r['p'][k] for r in records]) for k in ['layer','att','mlp']}
    vs={k:np.array([r['v'][k] for r in records]) for k in ps}
    a,m=ref.signed_contribution(vs,ps)
    assert np.allclose(a.mean(0),[r['attn_mean'] for r in rows],rtol=0,atol=1e-15)
    assert np.allclose(m.mean(0),[r['mlp_mean'] for r in rows],rtol=0,atol=1e-15)
    with (out/'contribution_layer.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write(out/'recommendations.json',variants)
    files={p.name:p.read_bytes() for p in sorted((out/'samples').glob('*.json'))}
    bundle=gzip.compress(json.dumps({n:base64.b64encode(b).decode() for n,b in files.items()}).encode(),mtime=0)
    (out/'samples.json.gz').write_bytes(bundle)
    write(out/'summary.json',dict(state='DONE',time=now(),dataset='mmke-'+ds,model=MODEL,completed=expected,total=expected,failed=0,
                                  torch_dtype='bfloat16',attribution_scope='next_token_argmax',server_result_path=str(out),
                                  protocol_sha256=ph,contribution_sha256=sha(out/'contribution_layer.csv'),recommendation_sha256=sha(out/'recommendations.json'),
                                  original_formula_parity=True,elapsed_seconds=time.time()-start,sample_bundle_sha256=sha(out/'samples.json.gz'),
                                  sample_files={n:hashlib.sha256(b).hexdigest() for n,b in files.items()}))
    state('DATASET_DONE',dataset='mmke-'+ds,completed=expected)


def main():
    (ROOT/'control').mkdir(parents=True,exist_ok=True)
    own,lock=admission()
    try:
        os.environ.update(CUDA_VISIBLE_DEVICES='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
        ref=reference(SOURCE,PROJECT)
        import torch
        cfg=ref.PTrackConfig.from_yaml(str(PROJECT/'configs/p_track/qwen2.5-vl-3b.yaml'))
        config=json.loads((PROJECT/'models/Qwen2.5-VL-3B-Instruct/config.json').read_text());assert config['torch_dtype']=='bfloat16'
        state('LOADING_FP16_DIAGNOSTIC')
        runner=make_runner(ref,cfg,'float16')
        fp16=diagnose(runner,'float16')
        del runner;gc.collect();torch.cuda.empty_cache()
        state('LOADING_BF16_REPAIR')
        runner=make_runner(ref,cfg,'bfloat16')
        bf16=diagnose(runner,'bfloat16')
        diagnosis=ROOT/'diagnosis.json'
        write(diagnosis,dict(model=MODEL,time=now(),model_config_dtype='bfloat16',original_auto_resolves_to='float16',
                             fp16=fp16,bf16=bf16,fp16_nonfinite=sum(not r['finite'] for r in fp16),bf16_nonfinite=sum(not r['finite'] for r in bf16)))
        assert sum(not r['finite'] for r in fp16)>=1, 'Original issue not reproduced; inspect before changing precision'
        assert all(r['finite'] for r in bf16), 'BF16 did not solve all diagnosed cases'
        for ds,n in [('visual',214),('entity',636)]:run_dataset(runner,ref,cfg,ds,n,diagnosis)
        state('DONE',completed_groups=2,completed_samples=850,attribution_scope='next_token_argmax',torch_dtype='bfloat16')
    finally:
        lock.close();own.close()


if __name__=='__main__':
    try:main()
    except Exception:
        state('NEEDS_REPAIR',error=traceback.format_exc());raise
