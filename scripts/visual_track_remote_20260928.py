"""Deploy a separate forward-only Slurm job, inspect, and fetch its scores."""
import argparse
import base64
import json
import sys
from pathlib import Path
from lga_ablation_remote import ssh

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'outputs/visual_track_cosine_20260928'
BASE='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2'
REMOTE=BASE+'/server_results/visual_track_cosine_20260928'
PROJECT=BASE+'/VisEdit-main'
OLDPY='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
QPY=BASE+'/envs/qwen25vl/bin/python'

def launch():
    if (LOCAL/'submission.json').exists():raise RuntimeError('Submission receipt exists; inspect before considering a new job')
    script=(ROOT/'scripts/run_visual_track_cosine_20260928.py').read_bytes()
    compile(script.decode(),'<runner>','exec')
    job='''#!/bin/bash
#SBATCH --job-name=visual-track-cos
#SBATCH --partition=phys_hq
#SBATCH --account=phys_hq_teacher
#SBATCH --qos=gpu_xl_2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=REMOTE/slurm-%j.log
set -u
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
cd PROJECT
status=0
for model in llava-v1.5-7b blip2-opt-2.7b instructblip-vicuna-7b minigpt-4-vicuna-7b paligemma-3b smolvlm-1.7b qwen2.5-vl-3b; do
    interpreter=OLDPY
    if [[ "$model" == qwen* ]]; then interpreter=QPY; fi
    "$interpreter" REMOTE/code/run_visual_track_cosine_20260928.py --project PROJECT --out REMOTE/results --model "$model" || status=1
done
exit "$status"
'''.replace('REMOTE',REMOTE).replace('PROJECT',PROJECT).replace('OLDPY',OLDPY).replace('QPY',QPY)
    code='''
import base64,json,subprocess,hashlib,datetime
from pathlib import Path
root=Path(REMOTE);(root/'code').mkdir(parents=True,exist_ok=True)
payload=json.loads(base64.b64decode(PAYLOAD))
for name,data in payload.items():
 p=root/name;b=base64.b64decode(data)
 if p.exists() and p.read_bytes()!=b:raise RuntimeError('Existing isolated source differs: '+str(p))
 if not p.exists():p.write_bytes(b)
if (root/'submission.json').exists():raise RuntimeError('Server receipt exists; do not duplicate')
test=subprocess.run(['sbatch','--test-only',str(root/'job.sbatch')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
result=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),test_returncode=test.returncode,test_output=test.stdout)
if test.returncode==0:
 p=subprocess.run(['sbatch','--parsable',str(root/'job.sbatch')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 result.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0]
  assert job.isdigit();result['job_id']=job
  (root/'submission.json').write_text(json.dumps(result,indent=2))
result['runner_sha256']=hashlib.sha256((root/'code/run_visual_track_cosine_20260928.py').read_bytes()).hexdigest()
print(json.dumps(result))
'''.replace('REMOTE',repr(REMOTE)).replace('PAYLOAD',repr(base64.b64encode(json.dumps({'code/run_visual_track_cosine_20260928.py':base64.b64encode(script).decode(),'job.sbatch':base64.b64encode(job.encode()).decode()}).encode()).decode()))
    result=json.loads(ssh(code,timeout=90))
    LOCAL.mkdir(exist_ok=True)
    (LOCAL/('submission.json' if result.get('job_id') else 'submission_attempt.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

def status(fetch):
    code='''
import base64,datetime,json,subprocess,hashlib
from pathlib import Path
root=Path(REMOTE)
sub=json.loads((root/'submission.json').read_text()) if (root/'submission.json').exists() else {}
job=sub.get('job_id','')
res=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),submission=sub)
if job:
 for key,cmd in [('squeue',['squeue','-j',job,'-h','-o','%i|%T|%R|%N|%M|%L']),('sacct',['sacct','-j',job,'--format=JobID,State,ExitCode,Elapsed,AllocTRES','-P','-n'])]:
  p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True);res[key]=p.stdout
 log=root/('slurm-'+job+'.log')
 if log.exists():res['log_tail']=log.read_text(errors='replace')[-9000:]
res['groups']=[]
for p in sorted((root/'results').glob('*/*')):
 if not p.is_dir():continue
 r=dict(dataset=p.parent.name,model=p.name)
 for n in ['summary.json','progress.json']:
  if (p/n).exists():
   obj=json.loads((p/n).read_text());r[n]={k:v for k,v in obj.items() if k!='sample_files'}
 if FETCH and (p/'summary.json').exists():
  s=json.loads((p/'summary.json').read_text())
  if s['status']=='done':
   for name,h in s['sample_files'].items():assert hashlib.sha256((p/'samples'/name).read_bytes()).hexdigest()==h
   assert hashlib.sha256((p/'layer_scores.json').read_bytes()).hexdigest()==s['scores_sha256']
   r['files']={n:base64.b64encode((p/n).read_bytes()).decode() for n in ['summary.json','protocol.json','layer_scores.json','layer_scores.csv']}
 res['groups'].append(r)
print(json.dumps(res))
'''.replace('REMOTE',repr(REMOTE)).replace('FETCH',repr(fetch))
    result=json.loads(ssh(code,timeout=120))
    for r in result['groups']:
        for name,b in r.pop('files',{}).items():
            p=LOCAL/'results'/r['dataset']/r['model']/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(b))
    (LOCAL/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','status','fetch']);a=p.parse_args()
    if a.action=='launch':launch()
    else:status(a.action=='fetch')
