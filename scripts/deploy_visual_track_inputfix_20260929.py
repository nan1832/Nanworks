"""Versioned repair; preserve all completed groups and failed-run evidence."""
import argparse
import base64
import json
from pathlib import Path
from deploy_priority_visual_track_g09_20260928 import call_node,REMOTE,PY,ROOT

LOCAL=ROOT/'outputs/visual_track_cosine_20260928/priority_switch/repair_20260929'
FILES=['run_visual_track_targets_20260929_inputfix.py','test_visual_track_targets_20260929_inputfix.py','smoke_visual_track_targets_20260929.py','priority_visual_track_g09_20260929_repair.py']


def invoke(code,timeout=90):
    return call_node(code.replace('REMOTE_ROOT',repr(REMOTE)).replace('INTERPRETER',repr(PY)),timeout)


def save(name,x):
    LOCAL.mkdir(parents=True,exist_ok=True)
    (LOCAL/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')


def stage():
    payload={n:base64.b64encode((ROOT/'scripts'/n).read_bytes()).decode() for n in FILES}
    for n in FILES:compile((ROOT/'scripts'/n).read_text(encoding='utf-8'),n,'exec')
    x=invoke(r'''
import base64,datetime,fcntl,hashlib,json,os,shutil,subprocess
from pathlib import Path
W=Path(REMOTE_ROOT);R=W/'repair_20260929';V=W.parent/'targets_v2';B=W.parents[2]
assert os.environ.get('SLURM_JOB_ID')=='3443209' and os.uname()[1].split('.')[0]=='g09'
lock=(W/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
gpu=(B/'server_results/gpu_locks/g09_gpu0.lock').open('a');fcntl.flock(gpu,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (R/'launch.json').exists(),'Already launched'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
plan=json.loads((W/'plan.json').read_text())
for path,h in plan['pins'].items():assert sha(path)==h,path
assert sha(plan['checkpoint']['backup'])==plan['checkpoint']['sha256']
assert not (W/'resume_minigpt_L8.log').exists()
assert json.loads((W/'status.json').read_text())['state']=='STOPPED_REQUIRES_INSPECTION'
verified=json.loads((W/'verified_variant_groups.json').read_text());assert len(verified)==15
for r in verified:assert sha(V/'results'/r['dataset']/r['model']/'summary.json')==r['summary_sha256']
R.mkdir(exist_ok=True)
for n,s in PAYLOAD.items():
 data=base64.b64decode(s);p=R/n;compile(data.decode(),str(p),'exec')
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']=''
p=subprocess.run([INTERPRETER,str(R/'test_visual_track_targets_20260929_inputfix.py')],cwd=str(R),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=120)
(R/'cpu_tests.log').write_text(p.stdout)
assert p.returncode==0,p.stdout
archives=[]
for ds in ['evqa-pilot500','mmke-visual','mmke-entity']:
 for model in ['smolvlm-1.7b','qwen2.5-vl-3b']:
  source=V/'results'/ds/model
  if not source.exists():continue
  assert source.resolve().parent.parent== (V/'results').resolve()
  assert not (source/'summary.json').exists()
  files=list((source/'samples').glob('*.json'))
  assert all(json.loads(f.read_text())['status']=='failed' for f in files),'Do not mix successful protocols'
  destination=R/'failed_before_fix'/ds/model
  assert not destination.exists()
  manifest={str(f.relative_to(source)):sha(f) for f in source.rglob('*') if f.is_file()}
  destination.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(destination))
  assert all(sha(destination/n)==h for n,h in manifest.items())
  archives.append(dict(source=str(source),destination=str(destination),files=manifest))
plan['repair']={'time':datetime.datetime.now().astimezone().isoformat(),'reason':'Accept only None pixel placeholders after SmolVLM pre-encodes image; unchanged scoring and completed results.','completed_groups_preserved':verified,'archives':archives,'cpu_tests_returncode':p.returncode}
for f in R.glob('*.py'):plan['pins'][str(f)]=sha(f)
(R/'plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps({'status':'staged','repair':plan['repair'],'cpu_test_log':p.stdout,'pins':plan['pins']}))
'''.replace('PAYLOAD',repr(payload)),timeout=180)
    save('stage_receipt.json',x)
    print(json.dumps({'status':x['status'],'cpu_test_log':x['cpu_test_log'],'preserved_groups':len(x['repair']['completed_groups_preserved']),'archived_failed_groups':len(x['repair']['archives'])},ensure_ascii=False,indent=2))


def launch():
    x=invoke(r'''
import datetime,fcntl,hashlib,json,os,subprocess
from pathlib import Path
W=Path(REMOTE_ROOT);R=W/'repair_20260929'
lock=(W/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (R/'launch.json').exists() and not (W/'resume_minigpt_L8.log').exists()
plan=json.loads((R/'plan.json').read_text())
for p,h in plan['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
assert plan['repair']['cpu_tests_returncode']==0
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',PYTHONUNBUFFERED='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
lock.close()
with (R/'controller.log').open('x') as stream:
 p=subprocess.Popen([INTERPRETER,'-u',str(R/'priority_visual_track_g09_20260929_repair.py'),'--continue-paused'],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
x=dict(time=datetime.datetime.now().astimezone().isoformat(),pid=p.pid,job='3443209',log=str(R/'controller.log'))
(R/'launch.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
''')
    save('launch.json',x);print(json.dumps(x,indent=2))


def status():
    x=invoke(r'''
import datetime,json,subprocess
from pathlib import Path
W=Path(REMOTE_ROOT);R=W/'repair_20260929';V=W.parent/'targets_v2/results'
x={'time':datetime.datetime.now().astimezone().isoformat(),'state':json.loads((W/'status.json').read_text()),'validation':{},'groups':[]}
for model in ['smolvlm-1.7b','qwen2.5-vl-3b']:
 p=R/('smoke_'+model+'.json')
 if p.exists():x['validation'][model]=json.loads(p.read_text())
 for ds in ['evqa-pilot500','mmke-visual','mmke-entity']:
  group=V/ds/model
  if group.exists():
   files=list((group/'samples').glob('*.json'));z={'model':model,'dataset':ds,'samples':len(files),'summary':(group/'summary.json').exists()}
   if (group/'progress.json').exists():z['progress']=json.loads((group/'progress.json').read_text())
   if files:
    first=json.loads(sorted(files)[0].read_text());z['first_sample_status']=first['status'];z['first_variants']={v:r['status'] for v,r in first['variants'].items()}
   x['groups'].append(z)
p=Path(x['state'].get('log',str(R/'controller.log')))
if p.exists():
 with p.open('rb') as f:f.seek(max(0,p.stat().st_size-3500));x['log_tail']=f.read().decode(errors='replace')
x['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],universal_newlines=True)
print(json.dumps(x))
''')
    save('status_snapshot.json',x)
    compact=dict(x)
    compact['validation']={m:{'status':v['status'],'samples':v['sample_count'],'max_first_predict_delta':max(z['first_predict_max_abs_delta'] or 0 for r in v['cases'] for z in r['variants'].values()),'longest_alt_tokens':max(r['variants']['alt']['tokens'] for r in v['cases'])} for m,v in x['validation'].items()}
    print(json.dumps(compact,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','launch','status']);args=p.parse_args();globals()[args.action]()
