from pathlib import Path
import hashlib,json,subprocess
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
for name in ['scripts/run_evqa_pilot500_blip2_visedit_sweep.py','editor/vllm_editors/vead/vead.py','editor/vllm_editors/vead/adpt_model.py','editor/vllms_for_edit/blip2.py','configs/vead/blip2-opt-2.7b.yaml']:
 p=root/name
 print(json.dumps({'file':name,'exists':p.exists(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}),flush=True)
print(subprocess.check_output(['ps','-u','ph_teacher3','-o','pid,ppid,etime,comm'],universal_newlines=True),flush=True)
print('BLIP2_FILES',[str(p) for p in (root/'editor/vllms_for_edit').glob('**/*blip2*.py')],flush=True)
for name in ['recovered_g09_nodefail_20260810','live_backfill','mmke_entity_top3_union_train_eval_7models_20260616_155000']:
 p=root.parent/'server_results'/name
 print('PATH',str(p),p.exists(),flush=True)
 if p.exists(): print([x.name for x in p.iterdir()][:35],flush=True)
