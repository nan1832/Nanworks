"""Prepare isolated server code, inspect progress, or fetch verified LGA results.

Default actions do not launch GPU work. Existing source runs are never modified.
"""
import argparse
import base64
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "outputs/lga_two_spaces_ablation_20260928"
BASE = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2"
REMOTE = BASE + "/server_results/lga_two_spaces_ablation_20260928"
PROJECT = BASE + "/VisEdit-main"
PYTHON = "/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python"
QWEN_PYTHON = BASE + "/envs/qwen25vl/bin/python"


def ssh(code, timeout=180):
    command = ["ssh.exe", "-i", str(Path(os.environ["USERPROFILE"]) / ".ssh/id_ed25519_bridge"),
               "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "bridge-server", "python3 -"]
    process = subprocess.run(command, input=code.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if process.returncode:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace") + process.stdout.decode("utf-8", errors="replace"))
    return process.stdout.decode("utf-8")


def prepare():
    files = {}
    for name in ["run_lga_two_space_ablation.py", "test_lga_two_space_ablation.py", "test_lga_two_space_autograd.py", "queue_lga_two_space_ablation.py"]:
        files[name] = base64.b64encode((ROOT / "scripts" / name).read_bytes()).decode()
    code = """
import base64,hashlib,json
from pathlib import Path
root=Path(REMOTE)/'code'
root.mkdir(parents=True,exist_ok=True)
files=json.loads(base64.b64decode(FILES))
out=[]
for name,content in files.items():
 p=root/name;b=base64.b64decode(content)
 if p.exists() and p.read_bytes()!=b: raise RuntimeError('Existing isolated code changed: '+str(p))
 if not p.exists():p.write_bytes(b)
 out.append(dict(path=str(p),sha256=hashlib.sha256(b).hexdigest()))
print(json.dumps(out))
""".replace("REMOTE", repr(REMOTE)).replace("FILES", repr(base64.b64encode(json.dumps(files).encode()).decode()))
    receipt = json.loads(ssh(code))
    LOCAL.mkdir(parents=True, exist_ok=True)
    (LOCAL / "deployment.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt))


def preflight(args):
    envpython = QWEN_PYTHON if args.space == "parameter" or args.model.startswith("qwen") else PYTHON
    command = [envpython, REMOTE + "/code/run_lga_two_space_ablation.py", "--project-dir", PROJECT,
               "--source-root", BASE + "/server_results", "--out-root", REMOTE + "/results",
               "--space", args.space, "--dataset", args.dataset, "--model", args.model, "--preflight"]
    remote_command = "env CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 " + " ".join(map(shlex.quote, command))
    code = """
import subprocess
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',NODE,COMMAND],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
print(p.stdout)
raise SystemExit(p.returncode)
""".replace("NODE", repr(args.node)).replace("COMMAND", repr(remote_command))
    print(ssh(code, timeout=600))


def sync():
    code = """
import base64,datetime,hashlib,importlib.util,json
from pathlib import Path
root=Path(REMOTE)
spec=importlib.util.spec_from_file_location('cross',str(root/'code/run_lga_two_space_ablation.py'))
cross=importlib.util.module_from_spec(spec);spec.loader.exec_module(cross)
result=[]
for space in ['parameter','visual']:
 for ds in cross.DATASETS:
  for model in cross.MODELS:
   p=root/'results'/space/ds/model
   entry=dict(space=space,dataset=ds,model=model,status='not_started')
   if (p/'summary.json').exists():entry.update(json.loads((p/'summary.json').read_text()))
   elif (p/'progress.json').exists():entry.update(json.loads((p/'progress.json').read_text()))
   elif (p/'protocol.json').exists():entry['status']='preflight_ready'
   entry['completed_sample_files']=len(list((p/'samples').glob('*.json')))
   if entry['status']=='done':
    protocol=json.loads((p/'protocol.json').read_text())
    assert cross.sha(p/'protocol.json')==entry['protocol_sha256']
    assert cross.sha(p/'layer_scores.json')==entry['score_sha256']
    assert cross.sha(p/'historical_reproduction.json')==entry['reproduction_sha256']
    assert all(x['passed'] for x in json.loads((p/'historical_reproduction.json').read_text()))
    records=[]
    for name,sha in entry['sample_files'].items():
     assert Path(name).name==name
     assert cross.sha(p/'samples'/name)==sha
     records.append(json.loads((p/'samples'/name).read_text()))
    scores=cross.aggregate(sorted(records,key=lambda r:r['sample_i']),[x['sample_id'] for x in protocol['cohort']],cross.MODELS[model])
    assert scores==json.loads((p/'layer_scores.json').read_text())['rows']
    entry['files']={name:base64.b64encode((p/name).read_bytes()).decode() for name in ['summary.json','protocol.json','layer_scores.json','historical_reproduction.json']}
    entry['remote_sample_reaggregation_verified']=True
   result.append(entry)
status={}
for node in ['g08','g09']:
 p=root/'control'/(node+'_status.json')
 if p.exists():status[node]=json.loads(p.read_text())
print(json.dumps(dict(records=result,workers=status,server_collected_at=datetime.datetime.now().astimezone().isoformat())))
""".replace("REMOTE", repr(REMOTE))
    payload = json.loads(ssh(code, timeout=600))
    LOCAL.mkdir(parents=True, exist_ok=True)
    for entry in payload["records"]:
        for name, content in entry.pop("files", {}).items():
            p = LOCAL / "results" / entry["space"] / entry["dataset"] / entry["model"] / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(base64.b64decode(content))
    from datetime import datetime
    payload["synced_at"] = datetime.now().astimezone().isoformat()
    (LOCAL / "sync_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    print(json.dumps(dict(status_counts=dict(Counter(x["status"] for x in payload["records"])), workers=payload["workers"]), ensure_ascii=False))
    subprocess.run([sys.executable, str(ROOT / "scripts/build_all_method_recommendations.py")], cwd=str(ROOT), check=True)


def launch():
    """Start CPU-only waiters; GPU admission is gated inside the worker."""
    code = r'''
import hashlib,json,subprocess
from pathlib import Path
root=Path(REMOTE)
control=root/'control';control.mkdir(exist_ok=True)
env_python=__ENV_PYTHON__
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'code').glob('*.py')}
p=control/'code_pins.json'
if p.exists():assert json.loads(p.read_text())==pins
else:p.write_text(json.dumps(pins,indent=2))
receipts=[]
for node,job in [('g08','3435286'),('g09','3443209')]:
 nodecode="""
import json,os,subprocess,time
from pathlib import Path
root=Path(__ROOT__)
control=root/'control'
node=__NODE__
job=__JOB__
receipt=control/(node+'_launch.json')
if receipt.exists():
 r=json.loads(receipt.read_text());pid=r['pid']
 command=Path('/proc')/str(pid)/'cmdline'
 if command.exists() and b'queue_lga_two_space_ablation.py' in command.read_bytes():
  print(json.dumps(dict(r,already_running=True)));raise SystemExit(0)
 raise RuntimeError('Previous waiter exited: inspect status before restarting')
assert subprocess.check_output(['squeue','-j',job,'-h','-o','%T %N'],universal_newlines=True).strip()=='RUNNING '+node
env=os.environ.copy();env.update(SLURM_JOB_ID=job,CUDA_VISIBLE_DEVICES='0',PYTHONUNBUFFERED='1')
log=control/(node+'_controller.log')
with log.open('xb') as output:
 child=subprocess.Popen([__PYTHON__,str(root/'code/queue_lga_two_space_ablation.py'),'--node',node],env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
r=dict(node=node,job=job,pid=child.pid,time=time.strftime('%Y-%m-%dT%H:%M:%S%z'),log=str(log))
receipt.write_text(json.dumps(r,indent=2));print(json.dumps(r))
""".replace('__ROOT__',repr(str(root))).replace('__NODE__',repr(node)).replace('__JOB__',repr(job)).replace('__PYTHON__',repr(env_python))
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',node,'python3 -'],input=nodecode,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 if p.returncode:raise RuntimeError(p.stderr+p.stdout)
 receipts.append(json.loads(p.stdout))
print(json.dumps(receipts))
'''.replace('REMOTE', repr(REMOTE)).replace('__ENV_PYTHON__', repr(PYTHON))
    receipts = json.loads(ssh(code))
    (LOCAL / 'launch_receipts.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(receipts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "preflight", "sync", "launch"])
    parser.add_argument("--node", choices=["g08", "g09"], default="g08")
    parser.add_argument("--space", choices=["parameter", "visual"], default="visual")
    parser.add_argument("--dataset", default="evqa-pilot500")
    parser.add_argument("--model", default="blip2-opt-2.7b")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "preflight":
        preflight(args)
    elif args.action == "launch":
        launch()
    else:
        sync()


if __name__ == "__main__":
    main()
