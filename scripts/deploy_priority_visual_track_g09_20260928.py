"""Prepare, start, or inspect the explicitly authorized g09 priority switch."""
import argparse
import base64
import json
import sys
from pathlib import Path
from lga_ablation_remote import ssh
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'outputs/visual_track_cosine_20260928/priority_switch'
REMOTE='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visual_track_cosine_20260928/priority_switch'
PY='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'

def call_node(code,timeout=90):
    transport="import subprocess\np=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','g09','python3 -'],input="+repr(code)+",stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout="+str(timeout)+")\nprint(p.stdout)\nif p.returncode:raise RuntimeError(p.stderr)"
    return json.loads(ssh(transport,timeout=timeout+30))

def prepare():
    src=(ROOT/'scripts/priority_visual_track_g09_20260928.py').read_bytes();compile(src.decode(),'<priority>','exec')
    code=r'''
import base64,hashlib,json,os,shutil,datetime
from pathlib import Path
W=Path(REMOTE);R=W.parent;V=R/'targets_v2';B=R.parents[1];P=B/'VisEdit-main';S=B/'server_results';D=S/'tukey_top3_two_gpu_20260926'
assert os.environ.get('SLURM_JOB_ID')=='3443209' and os.uname()[1].split('.')[0]=='g09'
assert not (W/'launch.json').exists(),'Priority controller already launched'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def identity(pid):
 p=Path('/proc')/str(pid);a=(p/'stat').read_text().split(') ',1)[1].split()
 return dict(start_ticks=a[19],cmdline_sha256=sha(p/'cmdline'))
def argv(pid):return [s for s in (Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split('\0') if s]
ck=json.loads((W/'checkpoint_verified.json').read_text());assert ck['epoch']==14 and ck['i']==4452 and sha(ck['backup'])==ck['sha256']
train=argv(2287248);controller=argv(2287075)
assert train[2]==str(P/'scripts/run_mmke_minigpt_llava_lowmem_sweep.py')
assert train[train.index('--model-name')+1]=='minigpt-4-vicuna-7b' and train[train.index('--layers')+1]=='8'
out=Path(train[train.index('--out-root')+1]);assert out==S/'tukey_top3_tail_job3443209_20260926/work/mmke-entity/minigpt-4-vicuna-7b'
assert controller[2]==str(D/'control/g09/memory_eligible_20260928/eligible_queue.py')
assert '--resume-checkpoint' not in train
resume=train+['--resume-checkpoint',ck['backup'],'--resume-layer','8']
source=base64.b64decode(PAYLOAD);p=W/'priority_visual_track_g09_20260928.py'
if p.exists():assert p.read_bytes()==source
else:p.write_bytes(source)
files=[p,Path(train[2]),P/'editor/vllm_editors/base.py',P/'editor/vllm_editors/vead/vead.py',Path(train[train.index('--config-path')+1]),Path(controller[2]),D/'control/two_gpu_queue.py',S/'tukey_top3_tail_job3443209_20260926/control/top3_tail_3443209.py',V/'code/run_visual_track_targets_20260928.py']
pins={str(p):sha(p) for p in files}
stage=json.loads((V/'stage_receipt.json').read_text());assert stage['test_returncode']==0
for p,h in stage['pins'].items():assert sha(p)==h
for path in [out/'train_L8.log',out/'run_config.json',out/'layer_08/loss_history.csv']:
 dest=W/('before_pause_'+path.name)
 if not dest.exists():shutil.copy2(str(path),str(dest))
plan=dict(time=datetime.datetime.now().astimezone().isoformat(),authorization='User requested pause MMKE-entity MiniGPT4 L8, finish current three variants, then continue training.',job_id='3443209',node='g09',controller_pid=2287075,training_pid=2287248,process_identities={str(p):identity(p) for p in [2287075,2287248]},original_train_command=train,resume_command=resume,controller_command=controller,controller_cwd=str((Path('/proc/2287075')/'cwd').resolve()),layer_dir=str(out/'layer_08'),pins=pins,checkpoint=ck,source_protocol_change=False,resume_semantics='Original checkpoint resume implementation; full RNG states were not saved by original training code.')
(W/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan))
'''.replace('REMOTE',repr(REMOTE)).replace('PAYLOAD',repr(base64.b64encode(src).decode()))
    x=call_node(code);save('plan.json',x);print(json.dumps(dict(prepared=True,job=x['job_id'],resume_epoch=15,checkpoint=x['checkpoint'],pinned_files=len(x['pins'])),ensure_ascii=False,indent=2))

def launch():
    code=r'''
import csv,datetime,json,os,subprocess
from pathlib import Path
W=Path(REMOTE);plan=json.loads((W/'plan.json').read_text())
assert os.environ.get('SLURM_JOB_ID')=='3443209' and not (W/'launch.json').exists()
history=list(csv.DictReader((Path(plan['layer_dir'])/'loss_history.csv').open()))
assert [int(r['epoch']) for r in history]==list(range(1,15)),'A newer epoch completed; refresh checkpoint before pausing'
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',PYTHONUNBUFFERED='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
with (W/'controller.log').open('x') as stream:
 p=subprocess.Popen([INTERPRETER,'-u',str(W/'priority_visual_track_g09_20260928.py')],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
x=dict(time=datetime.datetime.now().astimezone().isoformat(),pid=p.pid,job='3443209',log=str(W/'controller.log'));(W/'launch.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
'''.replace('REMOTE',repr(REMOTE)).replace('INTERPRETER',repr(PY))
    x=call_node(code);save('launch.json',x);print(json.dumps(x,ensure_ascii=False,indent=2))

def status():
    code=r'''
import json,subprocess,datetime
from pathlib import Path
W=Path(REMOTE);x={'time':datetime.datetime.now().astimezone().isoformat()}
for n in ['status.json','pause_receipt.json','verified_variant_groups.json','THREE_VARIANTS_DONE.json','RESUMED_TRAINING_DONE.json','ORIGINAL_QUEUE_RESTORED.json']:
 if (W/n).exists():x[n]=json.loads((W/n).read_text())
s=x.get('status.json',{});fallback=json.loads((W/'continue_launch.json').read_text())['log'] if (W/'continue_launch.json').exists() else str(W/'controller.log');log=Path(s.get('log',fallback))
if log.exists():
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-5000));x['log_tail']=f.read().decode(errors='replace')
x['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],universal_newlines=True)
x['gpu_processes']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],universal_newlines=True)
x['jobs']=subprocess.check_output(['squeue','-j','3435286,3443209,3463118','-h','-o','%i|%T|%N|%R'],universal_newlines=True)
print(json.dumps(x))
'''.replace('REMOTE',repr(REMOTE))
    x=call_node(code);save('status_snapshot.json',x);print(json.dumps(x,ensure_ascii=False,indent=2))

def save(n,x):
    LOCAL.mkdir(parents=True,exist_ok=True);(LOCAL/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','launch','status']);a=p.parse_args();globals()[a.action]()
