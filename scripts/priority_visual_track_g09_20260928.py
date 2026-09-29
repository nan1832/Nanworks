"""Authorized g09 switch: preserve L8 checkpoint, three variants, resume L8.

Only the two explicitly pinned project PIDs and our pending job are stopped.
Other GPU users and g08 are never signalled. No process-group or job-wide stop.
"""
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
import traceback
from pathlib import Path

B=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
S=B/'server_results';P=B/'VisEdit-main'
R=S/'visual_track_cosine_20260928';W=R/'priority_switch';V=R/'targets_v2'
D=S/'tukey_top3_two_gpu_20260926'
PY='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
QPY=str(B/'envs/qwen25vl/bin/python')
MODELS=['llava-v1.5-7b','blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','paligemma-3b','smolvlm-1.7b','qwen2.5-vl-3b']
DATASETS={'evqa-pilot500':500,'mmke-visual':214,'mmke-entity':636}

def load(p):return json.loads(Path(p).read_text())
def atomic(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.partial')
    q.write_text(json.dumps(x,indent=2));q.replace(p)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def command(args):return subprocess.check_output(args,universal_newlines=True,stderr=subprocess.STDOUT).strip()
def identity(pid):
    p=Path('/proc')/str(pid);fields=(p/'stat').read_text().split(') ',1)[1].split()
    return dict(start_ticks=fields[19],cmdline_sha256=sha(p/'cmdline'))
def alive(pid):
    p=Path('/proc')/str(pid)/'stat'
    return p.exists() and p.read_text().split(') ',1)[1].split()[0]!='Z'
def state(name,**kw):
    x=dict(time=time.strftime('%FT%T%z'),state=name,node='g09',job='3443209',pid=os.getpid(),**kw)
    atomic(W/'status.json',x)
    atomic(D/'control/g09/status.json',dict(x,scheduling='user_authorized_three_variants_then_resume_L8',priority_status=str(W/'status.json')))
    print(json.dumps(x),flush=True)
def verify_job():
    assert os.uname()[1].split('.')[0]=='g09' and os.environ.get('SLURM_JOB_ID')=='3443209'
    assert command(['squeue','-j','3443209','-h','-o','%T|%N'])=='RUNNING|g09'
def pincheck(plan):
    for path,digest in plan['pins'].items():assert sha(path)==digest,'Code/config drift: '+path
def stop_pinned(pid,expected):
    if not alive(pid):return  # A child may exit when its parent queue exits.
    assert identity(pid)==expected,'Process identity changed: '+str(pid)
    os.kill(pid,signal.SIGTERM)
    deadline=time.time()+30
    while alive(pid) and time.time()<deadline:time.sleep(1)
    assert not alive(pid),'Pinned process did not terminate; inspect without killing others'
def gpu_free():return int(command(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits']))
def gate(minimum,phase):
    stable=0
    while stable<3:
        verify_job();free=gpu_free();stable=stable+1 if free>=minimum else 0
        state('WAITING_GPU_MEMORY',phase=phase,free_mib=free,required_mib=minimum,stable=stable)
        if stable<3:time.sleep(20)
def run_child(args,log,phase,**info):
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONUNBUFFERED='1',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',PYTHONPATH=str(P)+':'+env.get('PYTHONPATH',''))
    with Path(log).open('x') as stream:
        child=subprocess.Popen(args,cwd=str(P),env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        state(phase,child_pid=child.pid,log=str(log),command=args,**info)
        while child.poll() is None:time.sleep(20)
    atomic(Path(str(log)+'.exit.json'),dict(returncode=child.returncode,time=time.strftime('%FT%T%z')))
    assert child.returncode==0,'Child failed, inspect '+str(log)

def verify_model(model):
    result=[]
    for ds,n in DATASETS.items():
        p=V/'results'/ds/model;s=load(p/'summary.json');assert s['status']=='done' and s['schema']==2 and s['sample_count']==n
        for name,key in [('protocol.json','protocol_sha256'),('layer_scores.json','scores_sha256'),('diagnostics.json','diagnostics_sha256')]:assert sha(p/name)==s[key]
        assert len(s['sample_files'])==n
        for name,digest in s['sample_files'].items():assert sha(p/'samples'/name)==digest
        result.append(dict(dataset=ds,model=model,n=n,summary_sha256=sha(p/'summary.json')))
    return result

def main(continue_paused=False):
    verify_job();own=(W/'controller.lock').open('a');fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=load(W/'plan.json');pincheck(plan);ck=load(W/'checkpoint_verified.json')
    assert ck['all_parameters_and_optimizer_finite'] and ck['epoch']==14 and ck['i']==4452 and sha(ck['backup'])==ck['sha256']
    if continue_paused:
        receipt=load(W/'pause_receipt.json');assert receipt['checkpoint']['sha256']==ck['sha256']
        assert not alive(plan['controller_pid']) and not alive(plan['training_pid'])
        assert not (W/'resume_minigpt_L8.log').exists(),'Training recovery needs a separate current-checkpoint audit'
    else:
        assert not (W/'pause_receipt.json').exists(),'Already switched; do not repeat stop/launch'
        assert identity(plan['controller_pid'])==plan['process_identities'][str(plan['controller_pid'])]
        assert identity(plan['training_pid'])==plan['process_identities'][str(plan['training_pid'])]
        pending=command(['squeue','-j','3463118','-h','-o','%T']).strip();assert pending=='PENDING','Extra job is no longer pending'
        state('PAUSING_VERIFIED_TRAINING',checkpoint=ck,discarded_partial_epoch=15)
        # Stop the queue first so it cannot launch a different layer after the child exits.
        stop_pinned(plan['controller_pid'],plan['process_identities'][str(plan['controller_pid'])])
        stop_pinned(plan['training_pid'],plan['process_identities'][str(plan['training_pid'])])
        subprocess.check_call(['scancel','3463118'])
        atomic(W/'pause_receipt.json',dict(time=time.strftime('%FT%T%z'),checkpoint=ck,stopped_pids=[plan['controller_pid'],plan['training_pid']],cancelled_own_pending_job='3463118',resume_command=plan['resume_command'],rng_restoration='Existing checkpoint contains weights/optimizer/epoch/step/EMA, but no full RNG states; standard frozen resume path, not bitwise identical uninterrupted training.'))
    gpu_lock=(S/'gpu_locks/g09_gpu0.lock').open('a');fcntl.flock(gpu_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipts=[]
    for model in MODELS:
        if all((V/'results'/ds/model/'summary.json').exists() for ds in DATASETS):
            receipts.extend(verify_model(model));continue
        pincheck(plan);gate(60000,'three_variants/'+model)
        args=[QPY if model.startswith('qwen') else PY,str(V/'code/run_visual_track_targets_20260928.py'),'--project',str(P),'--out',str(V/'results'),'--model',model]
        log=W/('variants_'+model+'.log')
        if log.exists():log.rename(log.with_name(log.name+'.previous_'+time.strftime('%H%M%S')))
        run_child(args,log,'RUNNING_THREE_VARIANTS',model=model,verified_groups=len(receipts),resume_checkpoint=ck['backup'])
        receipts.extend(verify_model(model));atomic(W/'verified_variant_groups.json',receipts)
    assert len(receipts)==21
    atomic(W/'THREE_VARIANTS_DONE.json',dict(time=time.strftime('%FT%T%z'),groups=receipts))
    pincheck(plan);assert sha(ck['backup'])==ck['sha256']
    gate(72166,'resume_minigpt_L8')
    # The original training script implements checkpoint loading and epoch/step advancement.
    run_child(plan['resume_command'],W/'resume_minigpt_L8.log','RESUMING_MINIGPT_L8',checkpoint=ck['backup'],resume_epoch=15,resume_i=4453)
    layer=Path(plan['layer_dir']);assert (layer/'train.done').is_file()
    atomic(W/'RESUMED_TRAINING_DONE.json',dict(time=time.strftime('%FT%T%z'),train_done=load(layer/'train.done')))
    gpu_lock.close()
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',PYTHONUNBUFFERED='1')
    with (W/'restored_original_queue.log').open('x') as stream:
        child=subprocess.Popen(plan['controller_command'],cwd=plan['controller_cwd'],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    time.sleep(5);assert child.poll() is None,'Restored original queue exited early'
    state('ORIGINAL_QUEUE_RESTORED',controller_pid=child.pid,log=str(W/'restored_original_queue.log'))
    atomic(W/'ORIGINAL_QUEUE_RESTORED.json',load(W/'status.json'))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--continue-paused',action='store_true');args=parser.parse_args()
    try:main(args.continue_paused)
    except Exception:
        state('STOPPED_REQUIRES_INSPECTION',error=traceback.format_exc(),checkpoint_preserved=True)
        raise
