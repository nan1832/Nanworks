"""Read-only progress snapshot for the two existing allocations."""
import json
import sys
from pathlib import Path
from lga_ablation_remote import ssh
sys.stdout.reconfigure(encoding='utf-8')
code=r'''
import datetime,json,re,subprocess,concurrent.futures
from pathlib import Path
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
specs=[('3435286','g08','E-VQA','LLaVA',4,'evqa_llava_job3435286_20260924/resume_L4_wait_memory_20260928/train_L4.log'),('3443209','g09','MMKE-entity','MiniGPT4',8,'tukey_top3_tail_job3443209_20260926/work/mmke-entity/minigpt-4-vicuna-7b/train_L8.log')]
out={'timestamp':datetime.datetime.now().astimezone().isoformat(),'jobs':[]}
for job,node,ds,model,layer,rel in specs:
 p=root/rel;stat=p.stat()
 with p.open('rb') as stream:stream.seek(max(0,stat.st_size-25000));text=stream.read().decode(errors='replace').replace('\r','\n')
 lines=text.splitlines();progress=[line for line in lines if re.search(r'Epoch\s+\d+:.*\d+/\d+\s*\[',line)]
 matches=re.findall(r'Epoch\s+(\d+):.*?(\d+)/(\d+)\s*\[',text)
 r=dict(job=job,node=node,dataset=ds,model=model,layer=layer,log=str(p),log_mtime=datetime.datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),recent_progress=progress[-3:],latest_checkpoint=[line for line in lines if '[ckpt]' in line][-1:],recent_errors=[line for line in lines if any(w in line for w in ['Traceback','CUDA out of memory','FloatingPointError','RuntimeError:'])][-3:])
 if matches:
  epoch,current,total=map(int,matches[-1]);r.update(epoch=epoch,current=current,total=total,total_epochs=50,training_fraction=((epoch-1)+current/total)/50)
 out['jobs'].append(r)
def gpu(node):
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',node,'nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=25)
 return node,dict(returncode=p.returncode,output=p.stdout)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:out['gpus']=dict(pool.map(gpu,['g08','g09']))
out['squeue']=subprocess.check_output(['squeue','-j','3435286,3443209,3463118','-h','-o','%i|%T|%R|%N|%M|%L'],universal_newlines=True)
out['lga_waiters']={node:json.loads((root/'lga_two_spaces_ablation_20260928/control'/(node+'_status.json')).read_text()) for node in ['g08','g09']}
priority=root/'visual_track_cosine_20260928/priority_switch/status.json'
if priority.exists():
 out['g09_priority_controller']=json.loads(priority.read_text())
 out['jobs'][1]['historical_training_log_only']=True
 out['jobs'][1]['current_phase']=out['g09_priority_controller']['state']
 out['jobs'][1]['note']='L8 log is a historical snapshot during the authorized pause; use priority controller for current GPU work.'
print(json.dumps(out))
'''
x=json.loads(ssh(code,timeout=90))
p=Path(__file__).resolve().parents[1]/'outputs/visual_track_cosine_20260928/targets_v2/current_training_progress.json'
p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(x,ensure_ascii=False,indent=2))
