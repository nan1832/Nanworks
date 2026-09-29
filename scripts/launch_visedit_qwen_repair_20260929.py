"""Deploy the isolated, authorized Qwen repair and hold its SSH session open."""
import base64
import hashlib
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
from lga_ablation_remote import ssh, BASE, QWEN_PYTHON

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'outputs/visedit_model_pred_mmke_20260929/qwen_repair'
REMOTE=BASE+'/server_results/visedit_model_pred_mmke_20260929/qwen_repair_bf16_v2'
names=['repair_visedit_qwen_bf16_20260929.py','run_visedit_model_pred_mmke_20260929.py']
files={}
for name in names:
    p=ROOT/'scripts'/name
    py_compile.compile(str(p),doraise=True)
    files[name]=base64.b64encode(p.read_bytes()).decode()
deploy='''
import base64,hashlib,json
from pathlib import Path
root=Path(%r);files=%r
(root/'code').mkdir(parents=True,exist_ok=True)
(root/'control').mkdir(exist_ok=True)
receipt=[]
for name,data in files.items():
 p=root/'code'/name;b=base64.b64decode(data)
 if p.exists():assert p.read_bytes()==b,'Existing repair code differs'
 else:p.write_bytes(b)
 receipt.append(dict(path=str(p),sha256=hashlib.sha256(b).hexdigest()))
print(json.dumps(receipt))
'''%(REMOTE,files)
receipt=json.loads(ssh(deploy))
LOCAL.mkdir(parents=True,exist_ok=True)
(LOCAL/'deployment.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(dict(deployed=receipt)),flush=True)
node='''
import subprocess,sys
from pathlib import Path
root=Path(%r)
with (root/'control/runner.log').open('a',buffering=1) as log:
 p=subprocess.Popen([%r,'-u',str(root/'code/repair_visedit_qwen_bf16_20260929.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,cwd=%r)
 for line in p.stdout:
  log.write(line);print(line,end='',flush=True)
 rc=p.wait()
raise SystemExit(rc)
'''%(REMOTE,QWEN_PYTHON,BASE+'/VisEdit-main')
bridge='''
import subprocess
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','g08','python3 -'],input=%r,universal_newlines=True)
raise SystemExit(p.returncode)
'''%node
cmd=['ssh.exe','-i',str(Path(os.environ['USERPROFILE'])/'.ssh/id_ed25519_bridge'),'-o','BatchMode=yes','-o','ConnectTimeout=15','bridge-server','python3 -']
result=subprocess.run(cmd,input=bridge.encode('utf-8'))
raise SystemExit(result.returncode)
