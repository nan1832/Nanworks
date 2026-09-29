"""Read-only server inventory; never loads weights or starts training."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import platform
import subprocess

root = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
files = ['scripts/run_evqa_pilot500_blip2_visedit_sweep.py',
         'editor/vllm_editors/vead/vead.py', 'editor/vllm_editors/vead/adpt_model.py',
         'editor/vllm_editors/base.py', 'editor/vllms_for_edit/blip2/blip2.py',
         'editor/vllms_for_edit/base.py', 'utils/__init__.py', 'utils/GLOBAL.py',
         'utils/nethook.py', 'dataset/vllm.py', 'evaluation/vllm_editor_eval.py',
         'configs/vead/blip2-opt-2.7b.yaml']
print(json.dumps({'host':platform.node(), 'python':platform.python_version(),
                  'root':str(root), 'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES')}))
for f in files:
    p = root/f
    print(json.dumps({'file':f, 'exists':p.exists(), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}))
for f in ['models/blip2-opt-2.7b/config.json','models/blip2-opt-2.7b/preprocessor_config.json']:
    p=root/f
    print(json.dumps({'file':f, 'resolved':str(p.resolve()), 'exists':p.exists(),
                      'config':json.loads(p.read_text()) if p.exists() else None}))
parent=root.parent
data=parent/'server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data'
for split in ['train','eval']:
    p=data/f'vqa_mmke_entity_{split}_evqa_compat.json'
    if p.exists():
        rows=json.loads(p.read_text())
        sample=rows[0]
        imgs={k:str(parent/'datasets/MMKE-Bench/data_image'/sample[k]) for k in ['image','image_rephrase','m_loc']}
        print(json.dumps({'data':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'count':len(rows),'first_sample':sample,'images_exist':{k:Path(v).exists() for k,v in imgs.items()}}))
    else:print(json.dumps({'data':str(p),'exists':False}))
for name in ['torch','transformers','accelerate','PIL','yaml','fcntl']:
    print(json.dumps({'dependency':name,'available':importlib.util.find_spec(name) is not None}))
try:
    import torch, transformers
    print(json.dumps({'torch':torch.__version__,'transformers':transformers.__version__,'cuda':torch.cuda.is_available(),
                      'adam_defaults':torch.optim.Adam.__init__.__defaults__},default=str))
except Exception as e: print(json.dumps({'dependency_error':repr(e)}))
# Only named experiment/model directories. Never traverse checkpoint/cache trees.
for base in [parent/'server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/blip2-opt-2.7b',
             parent/'server_results/g09_recovered_20260810/job3126082/mmke-entity/blip2-opt-2.7b']:
    for layer in ['layer_00','layer_01','layer_02']:
        p=base/layer/'selected_checkpoint.tsv'
        if p.exists(): print(json.dumps({'selected_metadata':str(p),'content':p.read_text()[:3000]}))
