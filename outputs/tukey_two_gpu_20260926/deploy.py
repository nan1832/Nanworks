"""Login-node launcher: approved two-card queue, no changes to training protocol."""
import ast, hashlib, importlib.util,json,os,subprocess,sys,time
from pathlib import Path
B=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2');S=B/'server_results'
D=S/'tukey_top3_two_gpu_20260926';OLD=S/'tukey_top3_tail_job3443209_20260926'
PY='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2))
assert load(D/'llava_L4_pause/resume_manifest.json')['state']=='PAUSED_VERIFIED'
assert load(D/'old_tail_backup/pause.json')['state']=='SUPERSEDED_STOPPED'
spec=importlib.util.spec_from_file_location('tail',str(OLD/'control/top3_tail_3443209.py'));t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
t.pincheck()
tree=ast.parse((D/'control/two_gpu_queue.py').read_text())
groups=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='GROUPS' for v in n.targets))
planned={(d,m,l) for gs in groups.values() for d,m,ls in gs for l in ls}
original={(j['dataset'],j['model'],j['layer']) for j in load(OLD/'provenance/plan.json')['jobs'] if j['model']!='llava-v1.5-7b'}
assert planned==original and len(planned)==12
for x in load(OLD/'provenance/plan.json')['pali_copies']:assert sha(x['copy'])==x['sha256']
baseline_code="""
import hashlib,json,subprocess
from pathlib import Path
lines=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],universal_newlines=True).strip().splitlines()
d={}
for line in lines:
 pid,mem=map(int,line.split(','));assert pid in [3407196,4145588],('Unexpected process; inspect',pid)
 p=Path('/proc')/str(pid);a=(p/'stat').read_text().split(') ',1)[1].split()
 d[str(pid)]=dict(identity=dict(start_ticks=a[19],cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()),max_memory_mib=mem+256,observed_memory_mib=mem)
print(json.dumps(d))
"""
r=subprocess.run(['ssh','g08','python3 -'],input=baseline_code,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,check=True)
dump(D/'control/g08/gpu_baseline.json',json.loads(r.stdout))
deployment=dict(time=time.strftime('%F %T %Z'),authorized=True,groups=groups,count=12,frozen_controller_sha256=sha(OLD/'control/top3_tail_3443209.py'),queue_sha256=sha(D/'control/two_gpu_queue.py'),source_plan_sha256=sha(OLD/'provenance/plan.json'),instruct_fallback='Require76GiB g08 free or delegate entire EVQA InstructBLIP combination to g09 after MiniGPT. No optimization change.',train_gate_mib=73728,eval_gate_mib=56320,auto_resume_llava=False,output_root=str(OLD),note='Original shared output root reused; its job3443209 name denotes provenance, not execution placement.')
assert not (D/'deployment.json').exists();dump(D/'deployment.json',deployment)
for node,job in [('g08','3435286'),('g09','3443209')]:
 mapping=subprocess.check_output(['squeue','-j',job,'-h','-o','%T %N'],universal_newlines=True).strip();assert mapping=='RUNNING '+node,mapping
 dest=D/'control'/node;dest.mkdir(parents=True,exist_ok=True)
 cmd=['srun','--jobid='+job,'--overlap','--nodes=1','--ntasks=1','--cpus-per-task=8','--nodelist='+node,PY,'-u',str(D/'control/two_gpu_queue.py')]
 with (dest/'controller.log').open('xb') as log:p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 dump(dest/'launch.json',dict(pid=p.pid,command=cmd,time=time.strftime('%F %T %Z')))
 print(node,job,p.pid,flush=True)
