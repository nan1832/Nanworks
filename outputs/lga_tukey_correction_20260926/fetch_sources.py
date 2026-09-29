"""Read-only SSH export of the historical parameter-LGA run. No server writes."""
from pathlib import Path
import subprocess, json, hashlib, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REMOTE = r'''
from pathlib import Path
import json,hashlib,datetime
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
run=root/'server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900'
files=[]
for p in sorted(run.glob('*/*/summary.json')):
 for name in ['summary.json','layer_scores.csv','candidate_layers_topk.csv','sanity_check.json']:
  q=p.parent/name
  if q.exists():files.append((q,'raw/'+str(q.relative_to(run))))
for name in ['run_lga_param_direct_altmodelpred_candidate_layers.py','run_lga_param_direct_altmodelpred_lowmem_candidate_layers.py']:
 files.append((root/'VisEdit-main/scripts'/name,'server_code/'+name))
for name in ['lga_param_direct_altmodelpred_candidates_summary.csv','lga_param_direct_altmodelpred_candidates_summary.md']:
 files.append((run/name,'raw/'+name))
out=[]
for p,rel in files:
 b=p.read_bytes();out.append(dict(source=str(p),relative=rel,sha256=hashlib.sha256(b).hexdigest(),text=b.decode('utf-8')))
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),run_root=str(run),files=out)))
'''
cmd=[r'C:\Windows\System32\OpenSSH\ssh.exe','-i',str(Path.home()/'.ssh/id_ed25519_bridge'),'-o','BatchMode=yes','-o','ConnectTimeout=12','ph_teacher3@10.68.162.201','/usr/bin/python3 -']
r=subprocess.run(cmd,input=REMOTE.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
bundle=json.loads(r.stdout)
for item in bundle['files']:
    p=HERE/item['relative'];p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(item['text'].encode('utf-8'))
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
manifest={k:v for k,v in bundle.items() if k!='files'}
manifest['files']=[{k:v for k,v in x.items() if k!='text'} for x in bundle['files']]
(HERE/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(manifest['files']),'groups':len(list((HERE/'raw').glob('*/*/summary.json'))),'captured_utc':bundle['captured_utc']}))
