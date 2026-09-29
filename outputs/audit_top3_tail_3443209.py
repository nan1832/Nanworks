"""Read-only discovery of existing main/checkpoint artifacts for authorized tail."""
from pathlib import Path
import os,json,re,time,csv
WANTED = [('evqa-pilot500','instructblip-vicuna-7b',17),('evqa-pilot500','instructblip-vicuna-7b',20),
 ('evqa-pilot500','qwen2.5-vl-3b',10),('evqa-pilot500','qwen2.5-vl-3b',6),
 ('mmke-entity','qwen2.5-vl-3b',6),('mmke-entity','qwen2.5-vl-3b',3),('mmke-entity','qwen2.5-vl-3b',10),
 ('mmke-visual','qwen2.5-vl-3b',3),('mmke-visual','qwen2.5-vl-3b',10),
 ('mmke-entity','minigpt-4-vicuna-7b',7),('mmke-entity','minigpt-4-vicuna-7b',8),
 ('mmke-entity','llava-v1.5-7b',7),('mmke-entity','llava-v1.5-7b',8),('evqa-pilot500','paligemma-3b',0)]
ROOTS = [Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results'),Path('/tmp/ph_teacher3')]
SKIP={'records','checkpoints','eval_full','images','data_image','data','datasets','tokenizers','model','models','__pycache__','.git','cache','eval_cache','node_cache','wandb','provenance'}

def scan():
 hits=[];errors=[]
 for root in ROOTS:
  for cur,dirs,files in os.walk(str(root),onerror=lambda e:errors.append(str(e))):
   p=Path(cur);dirs[:]=[d for d in dirs if d not in SKIP and not d.startswith('.') and len(p.relative_to(root).parts)<10]
   m=re.fullmatch(r'layer[_-](\d+)',p.name)
   if not m:continue
   dirs[:]=[];s=str(p).lower().replace('_','-')
   for ds,model,l in WANTED:
    if l!=int(m[1]):continue
    if model not in s:continue
    if not ((ds=='evqa-pilot500' and ('evqa' in s or 'pilot500' in s) and 'mmke' not in s) or ds in s):continue
    if not files and not any(p.glob('records/**/epoch-*')):continue
    row=dict(dataset=ds,model=model,layer=l,path=str(p),stable='stable' in s,files=files)
    for name in ['train.done','eval_full.done','selected_checkpoint.tsv']:
     q=p/name
     if q.is_file():row[name]=q.read_text(errors='replace')[:5000]
    q=p/'loss_history.csv'
    if q.is_file():
     hist=list(csv.DictReader(q.open()));row['history_epochs']=[int(x['epoch']) for x in hist]
    row['checkpoints']=[{'path':str(q),'bytes':q.stat().st_size} for q in p.glob('records/**/checkpoints/epoch-*') if q.is_file() and q.stat().st_size>0]
    hits.append(row)
 return dict(time=time.strftime('%F %T %Z'),roots=[str(r) for r in ROOTS],wanted=WANTED,hits=hits,errors=errors)
if __name__=='__main__':print(json.dumps(scan(),indent=2))
