"""Read-only remote inventory of representation-cosine and matched sweep sources."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root=Path(__file__).resolve().parents[1]
out=root/"outputs/visual_track_cosine_20260928"
out.mkdir(exist_ok=True)
code=r'''
import os,json,datetime,hashlib
from pathlib import Path
base=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
roots=[base/'server_results',base/'VisEdit-main/server_results',base/'VisEdit-main/records',base/'records']
runs=[];files=[];examined=0
for root in roots:
    if not root.is_dir():continue
    for run in sorted(root.iterdir()):
        if not run.is_dir():continue
        name=run.name.lower()
        if not any(x in name for x in ['attr','contribution','representation','bridge','visual_track','hidden_cos']):continue
        runs.append(str(run))
        for folder,dirs,names in os.walk(str(run)):
            depth=len(Path(folder).relative_to(run).parts)
            dirs[:]=[d for d in dirs if depth<6 and d not in ['checkpoints','cache','.git','visual_reps','samples','sample_gradients','wandb','node_modules','data'] and not d.startswith('epoch-')]
            for n in names:
                p=Path(folder)/n
                if not (n.endswith('.csv') or n in ['config.json','summary.json','eval_full.done','results.json','metrics.json']):continue
                if n.endswith('.csv'):
                    try:
                        with p.open(errors='replace') as f:head=f.readline(4096)
                    except OSError:continue
                    examined+=1
                    relevant='visual_track_cos' in head
                else:relevant=False
                bridge_result=('bridge' in name and n in ['eval_full.done','summary.json','results.json','metrics.json','config.json'])
                if not (relevant or bridge_result):continue
                size=p.stat().st_size
                if size>1000000:continue
                b=p.read_bytes()
                files.append(dict(path=str(p),size=size,sha256=hashlib.sha256(b).hexdigest(),visual_track=relevant,content=b.decode('utf-8','replace')))
print(json.dumps(dict(timestamp=datetime.datetime.now().astimezone().isoformat(),roots=[str(p) for p in roots],runs=runs,csv_headers_examined=examined,files=files)))
'''
cmd=["C:/Windows/System32/OpenSSH/ssh.exe","-i",str(Path(os.environ['USERPROFILE'])/'.ssh/id_ed25519_bridge'),"-o","BatchMode=yes","-o","ConnectTimeout=12","ph_teacher3@10.68.162.201","python3 -"]
p=subprocess.run(cmd,input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
result=json.loads(p.stdout)
(out/'remote_source_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(timestamp=result['timestamp'],run_count=len(result['runs']),csv_headers_examined=result['csv_headers_examined'],matches=[{k:f[k] for k in ['path','size','visual_track']} for f in result['files'] if f['visual_track']],bridge_summary_paths=[f['path'] for f in result['files'] if not f['visual_track']]),ensure_ascii=False,indent=2))
