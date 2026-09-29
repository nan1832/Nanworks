"""Approved 12 non-LLaVA layers. Reuse frozen protocol and validated archive routines."""
import csv, fcntl, hashlib, importlib.util, json, os, signal, subprocess, sys, time
from pathlib import Path

B=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2');S=B/'server_results';P=B/'VisEdit-main'
D=S/'tukey_top3_two_gpu_20260926';OLD=S/'tukey_top3_tail_job3443209_20260926'
PY='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
JOB={'g08':'3435286','g09':'3443209'}
GROUPS={'g08':[('mmke-visual','qwen2.5-vl-3b',[3,10]),('evqa-pilot500','qwen2.5-vl-3b',[10,6]),('mmke-entity','qwen2.5-vl-3b',[6,3,10]),('evqa-pilot500','instructblip-vicuna-7b',[17,20]),('evqa-pilot500','paligemma-3b',[0])],
        'g09':[('mmke-entity','minigpt-4-vicuna-7b',[7,8])]}
def load(path):return json.loads(Path(path).read_text())
def dump(path,x):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_name(path.name+'.partial');tmp.write_text(json.dumps(x,indent=2));tmp.replace(path)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def module(path,name):
 s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=module(OLD/'control/top3_tail_3443209.py','frozen_tail')
NODE=os.uname()[1].split('.')[0]
def state(s,**kw):
 d=dict(time=time.strftime('%F %T %Z'),state=s,node=NODE,job=JOB[NODE],pid=os.getpid(),llava_auto_resume=False,**kw)
 dump(D/'control'/NODE/'status.json',d);print(json.dumps(d),flush=True)
def apps():
 data=subprocess.check_output(['nvidia-smi','-i','0','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],universal_newlines=True)
 return {int(a):int(b) for a,b in (line.split(',') for line in data.strip().splitlines())}
def signature(pid):
 p=Path('/proc')/str(pid);a=(p/'stat').read_text().split(') ',1)[1].split()
 return dict(start_ticks=a[19],cmdline_sha256=sha(p/'cmdline'))
def gpu(phase,instruct=False):
 free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True))
 current=apps();baseline=load(D/'control/g08/gpu_baseline.json') if NODE=='g08' else {}
 unexpected=[]
 for pid,mem in current.items():
  b=baseline.get(str(pid))
  try:ok=b and signature(pid)==b['identity'] and mem<=b['max_memory_mib']
  except (OSError,ValueError):ok=False
  if not ok:unexpected.append(dict(pid=pid,memory=mem))
 # InstructBLIP has no measured same-protocol peak in this audit: require an almost empty card.
 minimum=(77824 if instruct else 73728) if phase=='train' else 56320
 return free>=minimum and not unexpected,dict(free_mib=free,required_mib=minimum,unexpected=unexpected,other_gpu=current)
def gate(phase):
 good=0
 while good<3:
  ready,evidence=gpu(phase,instruct=CURRENT['model']=='instructblip-vicuna-7b')
  good=good+1 if ready else 0;state('GPU_GATE',phase=phase,stable=good,**evidence)
  if good<3:time.sleep(20)
def check_time():
 remain=subprocess.check_output(['squeue','-j',JOB[NODE],'-h','-o','%L'],universal_newlines=True).strip()
 if remain=='UNLIMITED':return
 days,clock=remain.split('-',1) if '-' in remain else ('0',remain)
 seconds=int(days)*86400+sum(int(v)*60**i for i,v in enumerate(reversed(clock.split(':'))))
 assert seconds>=86400,'Less than24h remains: stop for migration'
def run_stage(j,phase):
 global CURRENT
 CURRENT=j;t.pincheck();check_time();gate(phase)
 log=t.out(j)/('%s_L%d.log'%(phase,j['layer']));assert not log.exists(),'Existing attempt requires inspection'
 args=t.command(j,phase)
 env=os.environ.copy();env.update(PYTHONPATH=str(P)+':'+env.get('PYTHONPATH',''),CUDA_VISIBLE_DEVICES='0',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
 with log.open('x') as f:
  c=subprocess.Popen(args,cwd=str(P),env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  state('RUNNING',dataset=j['dataset'],model=j['model'],layer=j['layer'],phase=phase,child_pid=c.pid,log=str(log),command=args)
  size=-1;last=time.time();last_report=0
  while c.poll() is None:
   n=log.stat().st_size
   if n!=size:size=n;last=time.time()
   if time.time()-last>7200:
    os.killpg(c.pid,signal.SIGTERM)
    try:c.wait(timeout=30)
    except subprocess.TimeoutExpired:os.killpg(c.pid,signal.SIGKILL);c.wait()
    raise RuntimeError('Own child2h no progress; stopped, no automatic retry')
   if time.time()-last_report>60:
    state('RUNNING',dataset=j['dataset'],model=j['model'],layer=j['layer'],phase=phase,child_pid=c.pid,log=str(log),bytes=n,idle_seconds=time.time()-last,gpu_process_memory=apps());last_report=time.time()
   time.sleep(15)
  assert c.returncode==0,(j,phase,c.returncode)
 t.copy(t.out(j)/'run_config.json',t.layer(j)/(phase+'_run_config.json'))
def external_check(j):
 audit=module(OLD/'control/audit_top3_tail.py','external_audit')
 hits=audit.scan()['hits'];bad=[]
 for x in hits:
  if (x['dataset'],x['model'],x['layer'])!=(j['dataset'],j['model'],j['layer']) or x['stable'] or x['path'].startswith(str(OLD)+'/'):continue
  # The explicitly approved Pali epoch30 continuation supersedes only its known incomplete diagnosis.
  if j['model']=='paligemma-3b' and len(x.get('history_epochs',[]))<50 and x['path'].startswith(str(t.PALI)+'/'):continue
  if 'train.done' in x or 'eval_full.done' in x:bad.append(x['path'])
 assert not bad,'External result discovered; reconcile first: '+repr(bad)
def do_job(j):
 assert j['model']!='llava-v1.5-7b'
 done=OLD/'accepted'/j['dataset']/j['model']/('layer_%02d'%j['layer'])
 if (done/'SYNC_VERIFIED').is_file():t.validate_eval(j,done);state('SKIP_VERIFIED_COMPLETE',task=j);return
 external_check(j)
 for name in ['cache','eval_cache']:
  q=t.out(j)/name
  assert q.is_symlink() and str(q.resolve()).startswith('/tmp/ph_teacher3/tukey_top3_tail_job3443209_20260926/')
  q.resolve().mkdir(parents=True,exist_ok=True)
 if (t.layer(j)/'train.done').exists():t.validate(j)
 else:run_stage(j,'train');t.validate(j)
 if (t.layer(j)/'eval_full.done').exists():t.validate_eval(j,t.layer(j))
 else:run_stage(j,'eval')
 t.archive(j)
def execute_group(ds,m,layers):
 lock_path=D/'claims'/('%s_%s.lock'%(ds,m));lock_path.parent.mkdir(exist_ok=True)
 with lock_path.open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for layer in layers:do_job(t.spec(ds,m,layer))
def follow():
 assert NODE in JOB and os.environ.get('SLURM_JOB_ID')==JOB[NODE]
 assert load(D/'llava_L4_pause/resume_manifest.json')['state']=='PAUSED_VERIFIED'
 assert load(D/'old_tail_backup/pause.json')['state']=='SUPERSEDED_STOPPED'
 assert sha(OLD/'control/top3_tail_3443209.py')==load(D/'deployment.json')['frozen_controller_sha256']
 assert len([l for g in GROUPS.values() for _,_,ls in g for l in ls])==12
 t.state=state;t.run_stage=run_stage
 held=[]
 for p in [D/'control'/NODE/'controller.lock',S/'gpu_locks'/('%s_gpu0.lock'%NODE)]:
  p.parent.mkdir(parents=True,exist_ok=True);f=p.open('a');held.append(f)
  while True:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:
    # On g09 wait for the priority3 holder, without GPU allocation.
    state('WAITING_FOR_PRIORITY3_OR_GPU_LOCK',lock=str(p));time.sleep(30)
 if NODE=='g09':t.wait_parent()
 t.pincheck()
 for ds,m,layers in GROUPS[NODE]:
  if NODE=='g08' and m=='instructblip-vicuna-7b':
   ready,evidence=gpu('train',instruct=True)
   decision=dict(owner='g08' if ready else 'g09',reason='same_protocol_peak_not_verified_require76GiB',evidence=evidence,time=time.strftime('%F %T %Z'))
   dump(D/'instruct_assignment.json',decision)
   if not ready:state('INSTRUCT_DEFERRED_TO_G09',decision=decision);continue
  execute_group(ds,m,layers)
 if NODE=='g09':
  while not (D/'instruct_assignment.json').is_file():state('WAITING_G08_INSTRUCT_ASSIGNMENT');time.sleep(60)
  if load(D/'instruct_assignment.json')['owner']=='g09':execute_group('evqa-pilot500','instructblip-vicuna-7b',[17,20])
 dump(D/'control'/NODE/'DONE.json',dict(time=time.strftime('%F %T %Z'),state='CARD_QUEUE_DONE_LLAVA_STAYS_PAUSED'))
 state('CARD_QUEUE_DONE_LLAVA_STAYS_PAUSED')
 if all((D/'control'/n/'DONE.json').is_file() for n in JOB):
  verified=[]
  for groups in GROUPS.values():
   for ds,m,layers in groups:
    for l in layers:
     j=t.spec(ds,m,l);d=OLD/'accepted'/ds/m/('layer_%02d'%l)
     assert (d/'SYNC_VERIFIED').is_file();cp,ev=t.validate_eval(j,d)
     verified.append(dict(dataset=ds,model=m,layer=l,archive=str(d),checkpoint_sha256=sha(cp)))
  assert len(verified)==12
  dump(D/'ALL_12_DONE.json',dict(time=time.strftime('%F %T %Z'),layers=verified,llava_auto_resume=False))
if __name__=='__main__':
 try:follow()
 except Exception as e:
  if NODE in JOB:state('STOPPED_ERROR_NO_CONFIG_FALLBACK',error=repr(e))
  raise

