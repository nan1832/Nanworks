import base64,hashlib,json,py_compile,sys
from remote import LOCAL,REMOTE,BASE,ssh
sys.stdout.reconfigure(encoding="utf-8")
alignment=json.loads((LOCAL/"alignment.json").read_text())
assert len(alignment["groups"])==21
assert all(g["status"]=="INPUTS_ALIGNED_PENDING_GPU_CHECK" for g in alignment["groups"])
files={}
for name in ["evaluate.py","queue.py"]:
    py_compile.compile(str(LOCAL/name),doraise=True)
    files[name]=base64.b64encode((LOCAL/name).read_bytes()).decode()
code="""import base64,datetime,hashlib,json,subprocess
from pathlib import Path
root=Path(%r);base=Path(%r)
groups=json.loads((root/'alignment.json').read_text())
assert len(groups)==21 and all(g['status']=='INPUTS_ALIGNED_PENDING_GPU_CHECK' for g in groups)
assert subprocess.check_output(['squeue','-j','3435286','-h','-o','%%T %%N'],universal_newlines=True).strip()=='RUNNING g08'
(root/'code').mkdir(exist_ok=True);(root/'control').mkdir(exist_ok=True)
pins={}
for name,data in %r.items():
    p=root/'code'/name;body=base64.b64decode(data)
    if p.exists():assert p.read_bytes()==body,'Isolated code changed'
    else:p.write_bytes(body)
    pins[str(p)]=hashlib.sha256(body).hexdigest()
launch=root/'control/launch.json'
assert not launch.exists(),'Existing launch requires inspection'
command=['srun','--jobid=3435286','--overlap','--nodes=1','--ntasks=1','--nodelist=g08',
         '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python','-u',str(root/'code/queue.py')]
with (root/'control/controller.log').open('xb') as log:
    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=str(base/'VisEdit-main'))
receipt=dict(time=datetime.datetime.now().astimezone().isoformat(),login_pid=child.pid,
             job='3435286',node='g08',command=command,code_pins=pins,root=str(root))
launch.write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
"""%(REMOTE,BASE,files)
result=json.loads(ssh(code))
(LOCAL/"launch.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
