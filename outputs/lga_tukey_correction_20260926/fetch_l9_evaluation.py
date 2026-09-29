from pathlib import Path
import subprocess,json,hashlib,base64
H=Path(__file__).resolve().parent
remote=r'''
from pathlib import Path
import json,hashlib,base64
p=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082/mmke-entity/llava-v1.5-7b/layer_09')
paths=[p/x for x in ['eval_full.done','train.done','selected_checkpoint.tsv','loss_history.csv']]
paths+=list(p.glob('eval_full/**/results.json'))+list(p.glob('eval_full/**/mean_results.json'))+list(p.glob('records/**/config.yaml'))
out=[]
for q in paths:
 b=q.read_bytes();out.append(dict(relative=str(q.relative_to(p)),source=str(q),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
e=json.loads((p/'eval_full.done').read_text());cp=Path(e['checkpoint'])
print(json.dumps(dict(files=out,checkpoint_exists=cp.is_file(),checkpoint_bytes=cp.stat().st_size if cp.exists() else None)))
'''
cmd=[r'C:\Windows\System32\OpenSSH\ssh.exe','-i',str(Path.home()/'.ssh/id_ed25519_bridge'),'-o','BatchMode=yes','-o','ConnectTimeout=12','ph_teacher3@10.68.162.201','/usr/bin/python3 -']
r=subprocess.run(cmd,input=remote.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);z=json.loads(r.stdout)
dest=H/'supplemental_evidence/mmke-entity/llava-v1.5-7b/layer_09'
for x in z['files']:
 p=dest/x['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(x.pop('data')));assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256']
(dest/'manifest.json').write_text(json.dumps(z,indent=2),encoding='utf-8')
print(json.dumps({'files':len(z['files']),'checkpoint_exists':z['checkpoint_exists'],'checkpoint_bytes':z['checkpoint_bytes']}))
for p in dest.glob('eval_full/**/mean_results.json'):print('MEAN',p.read_text()[:4000])
for p in dest.glob('eval_full/**/results.json'):
 zz=json.loads(p.read_text());print('RESULT_SCHEMA',len(zz),json.dumps(zz[0] if isinstance(zz,list) else next(iter(zz.items())))[:2200])
