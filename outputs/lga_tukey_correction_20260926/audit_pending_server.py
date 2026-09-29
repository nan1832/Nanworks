"""Read-only search for already existing artifacts for missing Tukey candidates."""
from pathlib import Path
import subprocess,json,csv,sys
H=Path(__file__).resolve().parent
rr=list(csv.DictReader((H/'tukey_candidate_execution_status.csv').open(encoding='utf-8-sig')))
wanted=sorted({(r['dataset'],r['model'],int(r['layer'])) for r in rr if r['main_evaluation_available']=='False'})
code='WANTED='+repr(wanted)+'\n'+r'''
from pathlib import Path
import os,json,re,subprocess,datetime
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
hits=[];errors=[];visits=0
skip={'records','checkpoints','eval_full','images','data_image','data','datasets','tokenizers','model','models','__pycache__','.git','cache','node_cache','wandb'}
for cur,dirs,files in os.walk(root,onerror=lambda e:errors.append(str(e))):
 visits+=1;p=Path(cur);rel=p.relative_to(root)
 dirs[:]=[d for d in dirs if d not in skip and not d.startswith('.') and len(rel.parts)<9]
 mt=re.fullmatch(r'layer[_-](\d+)',p.name)
 if not mt:continue
 dirs[:]=[];l=int(mt[1]);s=str(p).lower().replace('_','-')
 for ds,model,layer in WANTED:
  if l!=layer or model not in s:continue
  dmatch=(ds=='evqa-pilot500' and ('evqa' in s or 'pilot500' in s) and 'mmke' not in s) or (ds in s)
  if not dmatch:continue
  item=dict(dataset=ds,model=model,layer=l,path=str(p),stable='stable' in s,files=sorted(files))
  for name in ['eval_full.done','train.done','selected_checkpoint.tsv','run_config.json']:
   q=p/name
   if q.is_file():item[name]=q.read_text(errors='replace')[:30000]
  for a in [p.parent,p.parent.parent,p.parent.parent.parent]:
   q=a/'run_config.json'
   if q.is_file():item['ancestor_config']=dict(path=str(q),text=q.read_text(errors='replace')[:16000]);break
  hits.append(item)
queue=subprocess.run(['bash','-lc',"squeue -u ph_teacher3 -h -o '%i|%j|%T|%N|%M'"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope=str(root),node_local_tmp_scanned=False,visited_directories=visits,errors=errors,hits=hits,queue=queue.stdout)))
'''
cmd=[r'C:\Windows\System32\OpenSSH\ssh.exe','-i',str(Path.home()/'.ssh/id_ed25519_bridge'),'-o','BatchMode=yes','-o','ConnectTimeout=12','ph_teacher3@10.68.162.201','/usr/bin/python3 -']
r=subprocess.run(cmd,input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if r.returncode:
 (H/'pending_server_audit_error.log').write_bytes(r.stderr)
 print(r.stderr.decode(errors='replace'));raise SystemExit(r.returncode)
z=json.loads(r.stdout);(H/'pending_server_audit.json').write_text(json.dumps(z,ensure_ascii=False,indent=2),encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({k:v for k,v in z.items() if k!='hits'},ensure_ascii=False))
for x in z['hits']:
 print(json.dumps({k:v for k,v in x.items() if k in ['dataset','model','layer','path','stable']}|{'eval_done':'eval_full.done' in x,'selected':'selected_checkpoint.tsv' in x},ensure_ascii=False))
