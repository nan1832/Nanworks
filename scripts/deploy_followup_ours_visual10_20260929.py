"""Install the explicitly authorized, delayed visual10 follow-up and return its receipt."""
import base64
import json
from pathlib import Path
from manage_ours_visual10_20260929 import ssh, write

LOCAL=Path(__file__).resolve().parents[1]
REMOTE='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_visual10_20260929'
OUT=LOCAL/'outputs/ours_visual10_20260929/followup'


def main():
    payload=base64.b64encode((LOCAL/'scripts/followup_ours_visual10_20260929.py').read_bytes()).decode()
    bootstrap='''
import os,json,base64,hashlib,subprocess,time,importlib.util
from pathlib import Path
root=Path(REMOTE);target=root/'followup_20260929';code=target/'code/followup_ours_visual10_20260929.py'
assert os.uname()[1].split('.')[0]=='g08'
assert 'job_3435286' in Path('/proc/self/cgroup').read_text()
data=base64.b64decode(PAYLOAD)
if code.exists():assert code.read_bytes()==data,'Refuse to alter deployed follow-up'
else:
 code.parent.mkdir(parents=True,exist_ok=True);code.write_bytes(data)
compile(data,str(code),'exec')
spec=importlib.util.spec_from_file_location('visual10_followup',str(code));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
launch=target/'launch.json'
if launch.exists():
 result=json.loads(launch.read_text());result['live']=mod.process_identity(result['pid']);print(json.dumps(result));raise SystemExit(0)
s=json.loads((root/'control/status.json').read_text())
assert s['state']=='RUNNING_OURS_VISUAL10' and s['model']=='instructblip-vicuna-7b' and s['dataset']=='mmke-entity','Current gate changed; inspect first'
processes=[mod.process_identity(s[k]) for k in ['pid','child_pid']]
assert all(processes)
assert str(root/'code/ours_visual10_20260929.py') in processes[0]['cmd'] and ' queue' in processes[0]['cmd']
assert 'instructblip-vicuna-7b' in processes[1]['cmd'] and 'mmke-entity' in processes[1]['cmd']
pins=json.loads((root/'control/code_pins.json').read_text());pins[str(code)]=hashlib.sha256(data).hexdigest()
for name,digest in pins.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
contract=dict(time=mod.now(),authorization='User: after current group completes, diagnose these three errors and recompute where possible.',
 targets=mod.TARGETS,wait_processes=processes,pins=pins,job='3435286',node='g08',
 current_group=['mmke-entity','instructblip-vicuna-7b'],minimum_free_mib=60000,
 max_fresh_reruns_per_group=1,preserve_failed_artifacts=True,baseline_rtol=1e-3,baseline_atol=1e-8)
cp=target/'contract.json'
assert not cp.exists(),'Contract already exists without launch; inspect before duplicate launch'
mod.write(cp,contract)
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',SLURM_JOB_ID='3435286')
with (target/'controller.log').open('x') as stream:
 child=subprocess.Popen([mod.PY,'-B','-u',str(code),'queue'],cwd=str(mod.BASE/'VisEdit-main'),
  env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(time=mod.now(),pid=child.pid,job='3435286',node='g08',root=str(target),code_sha256=pins[str(code)])
mod.write(launch,receipt)
time.sleep(3)
assert child.poll() is None,'Follow-up exited on startup; inspect controller.log'
receipt['status']=json.loads((target/'status.json').read_text());receipt['live']=mod.process_identity(child.pid)
assert receipt['status']['state']=='WAITING_CURRENT_GROUP','Unexpected startup state'
print(json.dumps(receipt))
'''.replace('REMOTE',repr(REMOTE)).replace('PAYLOAD',repr(payload))
    wrapper='import subprocess\np=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=15","g08","python3 -B -"],input='+repr(bootstrap.encode())+',stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)\nprint(p.stdout.decode())\nprint(p.stderr.decode())\nraise SystemExit(p.returncode)'
    receipt=json.loads(ssh(wrapper))
    write(OUT/'launch_receipt.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
