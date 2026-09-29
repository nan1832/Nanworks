import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'no_edit_baseline_audit_20260929'))
from remote import ssh,node
LOCAL=Path(__file__).resolve().parent
BASE='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results'
REMOTE=BASE+'/tukey_top3_two_gpu_20260926/control/g09/memory_calibration_20260929'
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
old=(LOCAL/'before_eligible_queue.py').read_text(encoding='utf-8')
cal=(LOCAL/'calibration.py').read_text(encoding='utf-8')
probe=(LOCAL/'probe.py').read_text(encoding='utf-8')
injection=r"""
    calibration_path = D / 'control/g09/memory_calibration_20260929/calibration.py'
    probe_path = calibration_path.with_name('probe.py')
    assert hashlib.sha256(calibration_path.read_bytes()).hexdigest() == '__CAL_SHA__'
    assert hashlib.sha256(probe_path.read_bytes()).hexdigest() == '__PROBE_SHA__'
    calibration_spec = importlib.util.spec_from_file_location('measured_instruct_gate', str(calibration_path))
    calibration = importlib.util.module_from_spec(calibration_spec)
    calibration_spec.loader.exec_module(calibration)
    calibration.install(q)
""".replace('__CAL_SHA__',digest(cal)).replace('__PROBE_SHA__',digest(probe))
assert old.count('    install(q)\n')==1
new=old.replace('    install(q)\n','    install(q)\n'+injection)
compile(new,'eligible_queue.py','exec')
(LOCAL/'eligible_queue.py').write_text(new,encoding='utf-8')
files={name:(LOCAL/name).read_text(encoding='utf-8') for name in ['calibration.py','probe.py','test_calibration.py','before_eligible_queue.py']}
expected_plan=digest((LOCAL/'before_priority_plan.json').read_text(encoding='utf-8'))
expected_controller=json.loads((LOCAL/'before_priority_plan.json').read_text(encoding='utf-8'))['pins'][BASE+'/visual_track_cosine_20260928/priority_switch/repair_20260929/priority_visual_track_g09_20260929_repair.py']
if sys.argv[1]=='prepare':
    code="""from pathlib import Path
import json,subprocess,hashlib
root=Path(%r)
root.mkdir(exist_ok=True)
files=%r
for name,content in files.items():
 p=root/name
 if p.exists():assert p.read_text()==content,'Existing different file: '+str(p)
 else:p.write_text(content)
 compile(content,str(p),'exec')
p=subprocess.run(['python3','-B',str(root/'test_calibration.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
(root/'cpu_tests.log').write_text(p.stdout)
print(p.stdout)
assert p.returncode==0
print(json.dumps({'prepared':str(root),'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files}}))
"""%(REMOTE,files)
    output=ssh(code)
    (LOCAL/'prepare_receipt.log').write_text(output,encoding='utf-8')
    print(output)
elif sys.argv[1]=='activate':
    code="""from pathlib import Path
import json,os,hashlib,subprocess,datetime,fcntl,re
root=Path(%r);base=Path(%r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,content):
 p=Path(p);temp=p.with_name(p.name+'.calibration.partial');temp.write_text(content);temp.replace(p)
assert os.uname()[1].split('.')[0]=='g09'
assert subprocess.check_output(['squeue','-j','3443209','-h','-o','%%T|%%N'],universal_newlines=True).strip()=='RUNNING|g09'
lock=(root/'deployment.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (root/'deployment.json').exists(),'Already activated'
eligible=base/'tukey_top3_two_gpu_20260926/control/g09/memory_eligible_20260928/eligible_queue.py'
plan_path=base/'visual_track_cosine_20260928/priority_switch/repair_20260929/plan.json'
controller_path=plan_path.with_name('priority_visual_track_g09_20260929_repair.py')
assert sha(eligible)==%r
assert sha(plan_path)==%r
assert sha(controller_path)==%r
plan=json.loads(plan_path.read_text())
for name,digest in plan['pins'].items():assert sha(name)==digest,'Existing protocol pin drift: '+name
proc=Path('/proc/2512011');fields=(proc/'stat').read_text().split(') ',1)[1].split()
assert fields[19]=='283915048' and fields[1]=='2500705'
assert 'run_mmke_minigpt_llava_lowmem_sweep.py' in (proc/'cmdline').read_bytes().decode()
assert 'job_3443209' in (proc/'cgroup').read_text()
assert str(controller_path) in Path('/proc/2500705/cmdline').read_bytes().decode()
for d in Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:args=(d/'cmdline').read_bytes().split(b'\\0')
 except (OSError,PermissionError):continue
 assert str(eligible).encode() not in args,'Original queue already active; re-audit required'
for name,digest in %r.items():assert sha(root/name)==digest
assert 'OK' in (root/'cpu_tests.log').read_text()
assert 'self.train_i = self.train_epoch = self.ema_loss = 1' in (base.parent/'VisEdit-main/editor/vllm_editors/base.py').read_text()
(root/'before_priority_plan.json').write_text(plan_path.read_text())
(root/'before_eligible_queue.py').write_text(eligible.read_text())
new=%r
compile(new,str(eligible),'exec')
new_sha=hashlib.sha256(new.encode()).hexdigest()
plan['pins'][str(eligible)]=new_sha
for name in ['calibration.py','probe.py']:plan['pins'][str(root/name)]=sha(root/name)
plan['memory_gate_amendment_20260929']={'reason':'User confirmed measuring original L20/L17 configuration after L8 evaluation instead of waiting on a fixed 76 GiB gate','directory':str(root),'original_eligible_sha256':%r,'updated_eligible_sha256':new_sha}
atomic(eligible,new)
atomic(plan_path,json.dumps(plan,indent=2))
receipt={'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'state':'ARMED_AFTER_L8_EVALUATION','active_training_pid':2512011,'active_controller_pid':2500705,'active_processes_not_restarted':True,'pending_entrypoint':str(eligible),'entrypoint_sha256':sha(eligible),'plan_sha256':sha(plan_path),'old_76g_gate_overridden_at_runtime':True,'measured_gate_available':False,'sequence':['L8 train to 50 epochs','L8 full evaluation and verified archive','isolated L20 one-epoch memory probe','isolated L17 one-epoch memory probe','L20 formal 50-epoch train/eval','L17 formal 50-epoch train/eval'],'margin_mib':2048,'calibration_only_allocator_headroom_mib':3072,'probe_failure':'record and stop; no automatic retry or guessed threshold','formal_training_parameters_unchanged':True}
atomic(root/'deployment.json',json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
"""%(REMOTE,BASE,digest(old),expected_plan,expected_controller,{n:digest(files[n]) for n in files},new,digest(old))
    output=node(code,'g09')
    (LOCAL/'deployment.json').write_text(output,encoding='utf-8')
    print(output)
else:raise SystemExit('Use prepare or activate')
