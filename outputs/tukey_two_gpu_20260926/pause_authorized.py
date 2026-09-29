"""Identity-scoped pause and durable recovery capture; authorized 2026-09-26."""
import csv, hashlib, json, math, os, shutil, signal, subprocess, sys, time
from pathlib import Path

B=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
S=B/'server_results'
D=S/'tukey_top3_two_gpu_20260926'
OLD=S/'tukey_top3_tail_job3443209_20260926'
L=S/'evqa_llava_job3435286_20260924/resume_after_eval955_20260926'
EXPECTED={4045244:('259524159','resume_llava_after_eval_20260926.py',3435286),
          4079818:('260376658','run_mmke_llava_shared_gpu_sweep.py',3435286),
          1886572:('262357393','top3_tail_3443209.py follow',3443209)}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 q=p.with_name(p.name+'.partial');q.write_text(json.dumps(x,indent=2));q.replace(p)
def ident(pid):
 p=Path('/proc')/str(pid);a=(p/'stat').read_text().split(') ',1)[1].split()
 cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
 ticks,part,job=EXPECTED[pid]
 assert a[19]==ticks
 if a[0]!='Z':assert part in cmd and str(B) in cmd
 assert 'job_%d/'%job in (p/'cgroup').read_text()
 return dict(pid=pid,start_ticks=a[19],state=a[0],command=cmd)
def stop(pid):
 ident(pid);os.kill(pid,signal.SIGTERM)
 try:os.kill(pid,signal.SIGCONT)
 except ProcessLookupError:pass
 for _ in range(25):
  try:
   if ident(pid)['state']=='Z':return
  except FileNotFoundError:return
  time.sleep(1)
 raise RuntimeError('Exact PID did not exit; no broad kill: '+str(pid))
def verified_copy(src,dst):
 h=sha(src);dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists()
 shutil.copy2(str(src),str(dst));assert sha(src)==h==sha(dst)
 return dict(source=str(src),backup=str(dst),sha256=h,bytes=dst.stat().st_size)
node=os.uname()[1].split('.')[0]
if sys.argv[1]=='verify-g09':
 assert node=='g09' and not Path('/proc/1886572').exists()
 target=D/'old_tail_backup'
 for n in ['control/top3_tail_3443209.py','provenance/plan.json']:assert sha(OLD/n)==sha(target/n)
 st=json.loads((target/'control/status.json').read_text());assert st['state']=='WAITING_FOR_PRIORITY3' and st['pid']==1886572
 assert Path('/proc/1871816').exists() and Path('/proc/1896873').exists()
 data=dict(state='SUPERSEDED_STOPPED',time=time.strftime('%F %T %Z'),old_pid=1886572,old_start_ticks=EXPECTED[1886572][0],replacement=str(D),priority3_untouched=True,note='Post-signal procfs race rechecked: old waiter absent, priority3 controller and trainer remain alive.')
 dump(target/'pause.json',data);dump(OLD/'control/SUPERSEDED_BY_TWO_GPU.json',data);print(json.dumps(data))
elif sys.argv[1]=='verify-g08':
 assert node=='g08'
 for pid in [4045244,4079818]:assert not (Path('/proc')/str(pid)).exists()
 target=D/'llava_L4_pause';data=json.loads((target/'resume_manifest.json').read_text())
 assert all(sha(x['backup'])==x['sha256'] for x in data['files'])
 assert sha(data['checkpoint'])==sha(data['backup_checkpoint'])
 data.update(state='PAUSED_VERIFIED',stopped_at=time.strftime('%F %T %Z'),verification_note='Initial immediate post-signal check saw transient zombie with empty cmdline; now both exact PIDs absent and backup hashes reverified.')
 dump(target/'resume_manifest.json',data)
 dump(L/'status.json',dict(state='USER_PAUSED_FOR_NON_LLAVA_TOP3',manifest=str(target/'resume_manifest.json'),automatic_resume=False,time=time.strftime('%F %T %Z')))
 print(json.dumps({k:v for k,v in data.items() if k not in ['files','processes','resume_command']},indent=2))
elif sys.argv[1]=='g08':
 assert node=='g08'
 procs=[ident(p) for p in [4045244,4079818]]
 assert int((Path('/proc/4079818/stat').read_text().split(') ',1)[1].split())[1])==4045244
 layer=L/'run/evqa-pilot500/llava-v1.5-7b/layer_04'
 hist=list(csv.DictReader((layer/'loss_history.csv').open()))
 last=hist[-1];epoch=int(last['epoch'])
 assert [int(x['epoch']) for x in hist]==list(range(1,epoch+1)) and epoch<50
 cp=Path(last['ckpt_path']);cp.resolve().relative_to(layer.resolve())
 import torch
 c=torch.load(str(cp),map_location='cpu')
 assert c['epoch']==epoch and c['i']==epoch*250 and c['opt']['state']
 assert list(c['train_modules'])==['language_model.model.layers.4'] and math.isfinite(c['ema_loss'])
 metadata=dict(epoch=c['epoch'],step=c['i'],ema=c['ema_loss'],optimizer_states=len(c['opt']['state']))
 del c
 best=min((x for x in hist if math.isfinite(float(x['ema_loss']))),key=lambda x:float(x['ema_loss']))
 assert Path(best['ckpt_path']).is_file()
 target=D/'llava_L4_pause';target.mkdir(exist_ok=False)
 files=[verified_copy(p,target/'layer_04'/p.relative_to(layer)) for p in layer.rglob('*') if p.is_file() and not p.name.endswith('.lock') and '.partial' not in p.name and '.tmp' not in p.name]
 for n in ['prepared.json','status.json','llava_resume.log','authorization.json']:
  files.append(verified_copy(L/n,target/n)) if n!='llava_resume.log' else shutil.copy2(str(L/n),str(target/n))
 for rel in ['scripts/run_mmke_llava_shared_gpu_sweep.py','configs/vead/llava-v1.5-7b.yaml','phase2_p4/resume_llava_after_eval_20260926.py']:
  files.append(verified_copy(B/'VisEdit-main'/rel,target/'code'/rel))
 command=json.loads((L/'prepared.json').read_text())['command']
 command[command.index('--resume-checkpoint')+1]=str(cp)
 data=dict(state='BACKUP_VERIFIED_BEFORE_STOP',time=time.strftime('%F %T %Z'),processes=procs,checkpoint=str(cp),backup_checkpoint=str(target/'layer_04'/cp.relative_to(layer)),metadata=metadata,next_epoch=epoch+1,next_step=metadata['step']+1,best_epoch=int(best['epoch']),resume_command=command,files=files,automatic_resume=False,note='Partial next epoch not checkpointed. Restore from completed epoch; original RNG state availability is not assumed. Train command skips eval: formal full2093 eval must follow separately.')
 dump(target/'resume_manifest.json',data)
 (L/'CANCEL_AUTO_RESUME').write_text('USER_PAUSE_FOR_NON_LLAVA_TOP3_20260926\n')
 ident(4045244);os.kill(4045244,signal.SIGSTOP)
 stop(4045244);stop(4079818)
 data['state']='PAUSED_VERIFIED';data['stopped_at']=time.strftime('%F %T %Z')
 dump(target/'resume_manifest.json',data)
 dump(L/'status.json',dict(state='USER_PAUSED_FOR_NON_LLAVA_TOP3',manifest=str(target/'resume_manifest.json'),automatic_resume=False,time=time.strftime('%F %T %Z')))
 print(json.dumps({k:v for k,v in data.items() if k not in ['files','processes','resume_command']},indent=2))
elif sys.argv[1]=='g09':
 assert node=='g09';proc=ident(1886572)
 st=json.loads((OLD/'control/status.json').read_text());assert st['state']=='WAITING_FOR_PRIORITY3'
 children=subprocess.run(['pgrep','-P','1886572'],stdout=subprocess.PIPE,universal_newlines=True).stdout.strip();assert not children
 target=D/'old_tail_backup';target.mkdir(exist_ok=False)
 for n in ['control/status.json','control/top3_tail_3443209.py','provenance/plan.json']:
  verified_copy(OLD/n,target/n)
 stop(1886572)
 data=dict(state='SUPERSEDED_STOPPED',time=time.strftime('%F %T %Z'),process=proc,replacement=str(D),priority3_untouched=True)
 dump(target/'pause.json',data);dump(OLD/'control/SUPERSEDED_BY_TWO_GPU.json',data)
 print(json.dumps(data))
else:raise ValueError(sys.argv)
