"""Recompute rankings and extract small, traceable evidence. No model loading."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'phase2_p0'
B = next((ROOT/'md/TODO/Second_prashe').glob('*_BLIP2_MMKE-Entity'))
P = ROOT/'md/Location/VisualGradient_11formula_analysis_files_20260720'
def read_csv(p, delimiter=','):
    return list(csv.DictReader(p.open(encoding='utf-8-sig', newline=''), delimiter=delimiter))
def save(name, value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raw = P/'raw_layer_scores/mmke-entity/blip2-opt-2.7b/ours_direct_layer_scores.csv'
ranked=[]
for r in read_csv(raw):
    if r['S_v_zero_grad'].strip().lower()=='true' or r['invalid_reason'].strip():continue
    if not r['visual_token_start'].strip() or not r['visual_token_end'].strip():continue
    cos,norm=float(r['S_v_cos']),float(r['S_v_new_norm'])
    if not all(map(math.isfinite,[cos,norm])):continue
    score=abs(cos)*norm
    if not math.isfinite(score):continue
    ranked.append({'layer':int(r['layer']),'score':score,'cos':cos,'new_norm':norm,
                   'module_path':r['layer_path'],'valid_samples':int(r['n_request']),
                   'visual_span':[int(r['visual_token_start']),int(r['visual_token_end'])]})
ranked.sort(key=lambda r:(-r['score'],r['layer']))
reference=next(r for r in read_csv(P/'analysis_outputs_20260731/formula_topk_all_21.csv')
               if r['dataset']=='mmke-entity' and r['model']=='blip2-opt-2.7b' and r['formula']=='M_abscos_x_newn')
assert ','.join('L'+str(r['layer']) for r in ranked[:3])==reference['top3']
save('ranking_recomputed.json',{'formula':'abs(S_v_cos) * S_v_new_norm','reference':reference,'ranking':ranked})
checks=[]
for line in (B/'SHA256SUMS.txt').read_text().splitlines():
    expected,f=line.split(maxsplit=1)
    p=B/f.strip()
    actual=hashlib.sha256(p.read_bytes()).hexdigest()
    checks.append({'path':str(p.relative_to(ROOT)),'expected':expected,'actual':actual,'match':actual==expected})
assert all(r['match'] for r in checks)
save('bundle_integrity.json',checks)
history=ROOT/'server_results/live_backfill/recovered_g09_nodefail_20260810/job3126082/mmke-entity/blip2-opt-2.7b/layer_01/loss_history.csv'
rows=read_csv(history)
best=min(rows,key=lambda r:float(r['ema_loss']))
selected=read_csv(B/'evidence/selected_checkpoint_L1.tsv','\t')[0]
assert int(best['epoch'])==int(selected['epoch']) and float(best['ema_loss'])==float(selected['ema_loss'])
save('checkpoint_selection_recomputed.json',{'source':str(history.relative_to(ROOT)), 'checkpoint_rows':len(rows),
    'epoch_min':min(int(r['epoch']) for r in rows),'epoch_max':max(int(r['epoch']) for r in rows),
    'final_step':max(int(r['i']) for r in rows),'minimum_ema':best,'selected_record':selected})
evidence=[]
for p in (ROOT/'server_results/g09r/job3126082/logs').glob('*blip2*'):
    for i,l in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        if re.search(r'Random seed|reinitialized|train samples=|eval samples=|train start|train done|eval start|eval done|\[ckpt\].*epoch=(11|50)\b|Loading blip2|NONFINITE|SANITIZE|Traceback',l):
            # Remove progress bars, retain the original informative text.
            evidence.append({'source':str(p.relative_to(ROOT)),'logical_line_after_splitlines':i,'text':l})
save('runtime_log_excerpts.json',evidence)
paths=[raw,history,B/'SHA256SUMS.txt',*B.glob('config/*'),*B.glob('evidence/*'),
       *B.glob('launcher/*'),P/'analysis_outputs_20260731/formula_topk_all_21.csv',
       ROOT/'scripts/analyze_visual_gradient_formula_evidence.py',
       ROOT/'VisEdit-main/scripts/run_ours_direct_candidate_layers.py',
       ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md',
       next((ROOT/'md/TODO/Second_prashe').glob('*_v2.1.md')),
       *(ROOT/'server_results/g09r/job3126082/logs').glob('*blip2*')]
save('evidence_manifest.json',[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,
      'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths])
print(json.dumps({'bundle_hash_matches':len(checks),'ours_top3':[r['layer'] for r in ranked[:3]],
                 'coverage':284/636,'training_epochs_recorded':len(rows),'selected_epoch':int(best['epoch'])}))
