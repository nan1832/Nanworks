"""Read-only export of compact evaluation evidence; never exports checkpoints or caches."""
from pathlib import Path
import json, base64, hashlib

ROOT=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
SR=ROOT/'server_results'
OLD=SR/'mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b'
NEW=SR/'paligemma_visual_main_nonconvergent_eval_20260926'
paths=set()
for layer in [1,2,6,7,13]:
    p=OLD/f'layer_{layer:02d}'
    for n in ['eval_full.done','train.done','selected_checkpoint.tsv','loss_history.csv']:
        if (p/n).is_file(): paths.add(p/n)
    paths.update(p.glob('records/vead/paligemma-3b/*/config.yaml'))
    if (p/'eval_full.done').is_file():
        d=Path(json.loads((p/'eval_full.done').read_text())['result_dir'])
        paths.update(d.glob('*.json'))
for p in NEW.rglob('*'):
    if p.is_file() and (p.suffix in ['.json','.csv','.tsv','.yaml','.done'] or p.name=='ALL_DONE'):
        paths.add(p)
controller=SR/'paligemma_pending_followup_job3044208_20260713_204917'
for n in ['paligemma_pending_followup_layer_status.csv','paligemma_pending_followup_status.log']:
    paths.add(controller/n)
for n in ['scripts/run_evqa_pilot500_blip2_visedit_sweep.py',
          'scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py',
          'configs/vead/paligemma-3b.yaml','configs/vead/paligemma-3b-stable.yaml',
          'editor/vllm_editors/vead/vead.py','evaluation/vllm_editor_eval.py']:
    paths.add(ROOT/'VisEdit-main'/n)
for p in sorted(paths):
    if not p.is_file(): continue
    if p.stat().st_size>20_000_000:
        print(json.dumps(dict(skipped=str(p),reason='size limit'))); continue
    data=p.read_bytes()
    print(json.dumps(dict(path=str(p),relative=str(p.relative_to(ROOT)),bytes=len(data),
                         sha256=hashlib.sha256(data).hexdigest(),base64=base64.b64encode(data).decode())),flush=True)
