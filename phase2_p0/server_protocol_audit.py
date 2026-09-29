"""Read named metadata and selected checkpoint optimizer metadata; never train."""
from pathlib import Path
import csv,hashlib,inspect,json
import torch
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
parent=root.parent
out=root/'phase2_p0'
result={}
roots={
 'L0':parent/'server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/blip2-opt-2.7b/layer_00',
 'L1':parent/'server_results/tmp_archives_20260810/g09/mabscos_top3_completion_job3126082_20260801/mmke-entity/blip2-opt-2.7b/layer_01'}
for name,base in roots.items():
 record={}
 selected=list(csv.DictReader((base/'selected_checkpoint.tsv').open(),delimiter='\t'))[0]
 ckpt=Path(selected['checkpoint'])
 record['selected']=selected
 record['checkpoint_exists']=ckpt.exists()
 for f in ['train.done','eval_full.done']:
  p=base/f
  if p.exists():record[f]=json.loads(p.read_text())
 p=base/'loss_history.csv'
 if p.exists():
  rows=list(csv.DictReader(p.open()))
  record['history']={'rows':len(rows),'last_epoch':max(int(r['epoch']) for r in rows),
                     'last_step':max(int(r['i']) for r in rows),
                     'best':min(rows,key=lambda r:float(r['ema_loss']))}
 p=ckpt.parent.parent/'config.yaml'
 if p.exists(): record['saved_config_yaml']=p.read_text()
 if ckpt.exists():
  state=torch.load(str(ckpt),map_location='cpu')
  record['checkpoint_metadata']={k:state[k] for k in ['epoch','i','loss','ema_loss']}
  record['module_keys']=list(state['train_modules'])
  record['optimizer_param_groups']=[{k:(len(v) if k=='params' else v) for k,v in g.items()} for g in state['opt']['param_groups']]
  del state
 result[name]=record
 print(json.dumps({name:record}),flush=True)
raw=parent/'server_results/ours_direct_7models_3datasets_g08_gpu0_20260626_131624/mmke-entity/blip2-opt-2.7b/ours_direct_layer_scores.csv'
result['ranking_raw']={'path':str(raw),'exists':raw.exists(),'sha256':hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None}
print(json.dumps({'ranking_raw':result['ranking_raw']}),flush=True)
result['adam_signature']=str(inspect.signature(torch.optim.Adam))
(out/'server_protocol_audit.json').write_text(json.dumps(result,indent=2))
