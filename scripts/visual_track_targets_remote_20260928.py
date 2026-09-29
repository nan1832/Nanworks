"""Stage/test three variants, update our unstarted job, or fetch completed groups."""
import argparse
import base64
import json
import sys
from pathlib import Path
from lga_ablation_remote import ssh

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'outputs/visual_track_cosine_20260928/targets_v2'
REMOTE='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visual_track_cosine_20260928'
PYTHON='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
NAMES=['run_visual_track_targets_20260928.py','test_visual_track_targets_20260928.py']

def stage():
    payload={n:base64.b64encode((ROOT/'scripts'/n).read_bytes()).decode() for n in NAMES}
    code=r'''
import base64,hashlib,json,subprocess,os
from pathlib import Path
root=Path(REMOTE)/'targets_v2';(root/'code').mkdir(parents=True,exist_ok=True)
payload=json.loads(base64.b64decode(PAYLOAD));pins={}
for name,data in payload.items():
 p=root/'code'/name;b=base64.b64decode(data)
 if p.exists() and p.read_bytes()!=b:raise RuntimeError('Immutable staged source changed: '+str(p))
 if not p.exists():p.write_bytes(b)
 pins[str(p)]=hashlib.sha256(b).hexdigest()
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run([INTERPRETER,str(root/'code/test_visual_track_targets_20260928.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=120)
x=dict(pins=pins,test_returncode=p.returncode,test_output=p.stdout)
(root/'stage_receipt.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
'''.replace('REMOTE',repr(REMOTE)).replace('INTERPRETER',repr(PYTHON)).replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
    x=json.loads(ssh(code,timeout=150));save('stage_receipt.json',x);print(json.dumps(x,ensure_ascii=False,indent=2))
    if x['test_returncode']:raise RuntimeError('CPU tests failed')

def upgrade_pending():
    code=r'''
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(REMOTE);v2=root/'targets_v2';receipt=json.loads((v2/'stage_receipt.json').read_text())
assert receipt['test_returncode']==0
for p,h in receipt['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
job=str(json.loads((root/'submission.json').read_text())['job_id']);assert job=='3463118'
def command(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=20)
 if p.returncode:raise RuntimeError(p.stdout)
 return p.stdout
state=command(['squeue','-j',job,'-h','-o','%T']).strip()
assert state=='PENDING','Never replace code for an already running job: '+state
assert not list((root/'results').glob('*/*/protocol.json')),'Unexpected v1 results'
command(['scontrol','hold',job])
try:
 assert command(['squeue','-j',job,'-h','-o','%T']).strip()=='PENDING'
 p=root/'code/run_visual_track_cosine_20260928.py';backup=root/'code/run_visual_track_cosine_20260928.v1.py'
 if not backup.exists():backup.write_bytes(p.read_bytes())
 assert hashlib.sha256(backup.read_bytes()).hexdigest()=='abbeb49979bc041d53bd1e4adefbb04c4d99572699256705850e464e83822e4a'
 wrapper="import sys\nfrom pathlib import Path\nsys.path.insert(0,"+repr(str(v2/'code'))+")\nfrom run_visual_track_targets_20260928 import main\nsys.argv[sys.argv.index('--out')+1]="+repr(str(v2/'results'))+"\nmain()\n"
 compile(wrapper,str(p),'exec');tmp=p.with_suffix('.tmp');tmp.write_text(wrapper);tmp.replace(p)
 command(['scontrol','update','JobId='+job,'TimeLimit=12:00:00'])
 x=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),job_id=job,status='pending_upgraded_to_three_variants',old_source_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),entry_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pins=receipt['pins'],results=str(v2/'results'),time_limit='12:00:00',existing_training_jobs_modified=False)
 (v2/'upgrade_receipt.json').write_text(json.dumps(x,indent=2))
finally:
 command(['scontrol','release',job])
x['queue']=command(['squeue','-j',job,'-h','-o','%i|%T|%R|%M|%L']);print(json.dumps(x))
'''.replace('REMOTE',repr(REMOTE))
    x=json.loads(ssh(code,timeout=90));save('upgrade_receipt.json',x);print(json.dumps(x,ensure_ascii=False,indent=2))

def status(fetch=False):
    code=r'''
import base64,datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(REMOTE);v2=root/'targets_v2';sub=json.loads((root/'submission.json').read_text());job=str(sub['job_id'])
x=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),job_id=job,groups=[])
p=subprocess.run(['squeue','-j',job,'-h','-o','%i|%T|%R|%M|%L'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True);x['queue']=p.stdout
priority=root/'priority_switch/status.json'
if priority.exists():
 x['priority_controller']=json.loads(priority.read_text());x['job_id']=x['priority_controller']['job']
 p=subprocess.run(['squeue','-j',str(x['job_id']),'-h','-o','%i|%T|%R|%M|%L'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True);x['queue']=p.stdout
 x['superseded_extra_job']=job
for p in sorted((v2/'results').glob('*/*')):
 r=dict(dataset=p.parent.name,model=p.name)
 for n in ['summary.json','progress.json']:
  if (p/n).exists():r[n]={k:v for k,v in json.loads((p/n).read_text()).items() if k!='sample_files'}
 if FETCH and (p/'summary.json').exists():
  s=json.loads((p/'summary.json').read_text());assert s['status']=='done'
  for n,h in s['sample_files'].items():assert hashlib.sha256((p/'samples'/n).read_bytes()).hexdigest()==h
  for n,k in [('protocol.json','protocol_sha256'),('layer_scores.json','scores_sha256'),('diagnostics.json','diagnostics_sha256')]:assert hashlib.sha256((p/n).read_bytes()).hexdigest()==s[k]
  r['files']={n:base64.b64encode((p/n).read_bytes()).decode() for n in ['summary.json','progress.json','protocol.json','layer_scores.json','layer_scores.csv','diagnostics.json'] if (p/n).exists()}
 x['groups'].append(r)
print(json.dumps(x))
'''.replace('REMOTE',repr(REMOTE)).replace('FETCH',repr(fetch))
    x=json.loads(ssh(code,timeout=120))
    for r in x['groups']:
        for n,b in r.pop('files',{}).items():
            p=LOCAL/'results'/r['dataset']/r['model']/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(b))
    save('status.json',x);print(json.dumps(x,ensure_ascii=False,indent=2))

def save(name,x):
    LOCAL.mkdir(parents=True,exist_ok=True);(LOCAL/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','upgrade-pending','status','fetch']);a=p.parse_args()
    if a.action=='stage':stage()
    elif a.action=='upgrade-pending':upgrade_pending()
    else:status(a.action=='fetch')
