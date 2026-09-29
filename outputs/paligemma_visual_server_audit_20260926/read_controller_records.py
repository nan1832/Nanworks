from pathlib import Path
import json,re,datetime,hashlib
R=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
SR=R/'server_results'
matches=[]
for p in SR.iterdir():
    if 'paligemma' in p.name.lower() and ('visual' in p.name or '20260713_204917' in p.name):
        if p.is_file(): matches.append(p)
        else:
            for f in p.iterdir():
                if f.is_file() and any(t in f.name.lower() for t in ['status','controller','layer','run_config']): matches.append(f)
for f in matches:
    if f.stat().st_size>3000000: continue
    t=f.read_text(errors='replace')
    if f.name.endswith('.json'): chosen=t[:15000]
    else:
        lines=[x for x in t.splitlines() if any(xi in x for xi in ['layer=3','layer=5','L3','L5','mmke-visual,main,3','mmke-visual,main,5','STALLED','TIMEOUT'])]
        chosen='\n'.join(lines[:50])
    print(json.dumps(dict(path=str(f),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),relevant_text=chosen)),flush=True)
for root in [SR/'mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b',
             SR/'paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b',
             SR/'paligemma_visual_main_nonconvergent_eval_20260926']:
    for name in ['run_config.json','status.json','protocol.json']:
        f=root/name
        if f.exists(): print(json.dumps(dict(path=str(f),text=f.read_text())),flush=True)
