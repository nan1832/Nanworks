"""Read-only metric calculation. Prints evidence and results; no ledger writes."""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / 'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
METHODS = ['Middle-Prior-Direct', 'VisEdit-Contrib-Pre-KeyToken', 'SaLEM-Alt-Direct',
           'LGA-Param-Direct-AltModelPred', 'Perturb-KL-Direct-AltSeq', 'Ours-Direct',
           'CMA-Direct-v1.3-alt', 'CMA-ModelPred-Direct-v2']
DM = {'blip2-opt-2.7b':'BLIP2-OPT-2.7B', 'instructblip-vicuna-7b':'InstructBLIP-Vicuna-7B',
      'minigpt-4-vicuna-7b':'MiniGPT-4-Vicuna-7B','llava-v1.5-7b':'LLaVA-v1.5-7B',
      'qwen2.5-vl-3b':'Qwen2.5-VL-3B','paligemma-3b':'PaliGemma-3B','smolvlm-1.7b':'SmolVLM-Instruct-1.7B'}
DS = {'evqa-pilot500':'EVQA-pilot500','mmke-visual':'MMKE-visual','mmke-entity':'MMKE-entity'}

def csvrows(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def layers(s): return [int(x) for x in re.findall(r'L(\d+)', s)]

lines = MANUAL.read_text(encoding='utf-8').splitlines()
candidates = {}
for r in csvrows(ROOT/'outputs/formal7_method_topk_performance_20260801.csv'):
    method = METHODS[-2] if r['method']=='CMA-Direct' else r['method']
    candidates[(r['dataset'],r['model'],method)] = layers(r['top3'])
header = '| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |'
for line in lines[lines.index(header)+2:]:
    if not line.startswith('|'): break
    r = [v.strip() for v in line.strip('|').split('|')]
    candidates[(r[0],r[1],METHODS[-1])] = layers(r[2])
assert len(candidates)==168
assert all(len(v)==len(set(v))==3 for v in candidates.values())

scores = {}; provenance = {}; conflicts = []
def put(key, variant, score, source, status, replace=False):
    k = (*key, variant)
    old = scores.get(k)
    if old is not None and abs(old-score)>0.011:
        conflicts.append(dict(key=k,old=old,new=score,old_source=provenance[k],new_source=source))
    if old is None or replace:
        scores[k] = score
        provenance[k] = dict(source=source,status=status)

for name in ['md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/accepted_outcome_rows.csv',
             'outputs/formal7_live_main_outcomes_20260824.csv']:
    for r in csvrows(ROOT/name):
        if r['variant']!='main': continue
        if 'FAILED' in r['status'] or 'NO_EVAL' in r['status']: continue
        put((DS[r['dataset']],DM[r['model']],int(r['layer'])),'main',float(r['average']),name,r['status'])

inside = False; ds = None
for lineno,line in enumerate(lines,1):
    if line=='### 4.0 服务器结构化结果总表': inside=True
    if line.startswith('### 4.1 '): inside=False
    if not inside: continue
    if line.startswith('#### ') and line[5:] in DS.values(): ds=line[5:]
    if not ds or not line.startswith('|'): continue
    r=[v.strip() for v in line.strip('|').split('|')]
    if len(r)!=13 or r[0] not in DM: continue
    try: score=float(r[11]); n=int(r[5]); layer=layers(r[1])[0]
    except (ValueError,IndexError): continue
    if n!={'EVQA-pilot500':2093,'MMKE-visual':293,'MMKE-entity':954}[ds]: continue
    status=r[12].upper()
    if 'FAILED' in status or 'NO_EVAL' in status: continue
    variant = 'stable' if 'STABLE' in status else 'main'
    # Section 3.5.1 explicitly identifies this ambiguous MANUAL status as stable.
    if (ds,DM[r[0]],layer,status)==('MMKE-visual','PaliGemma-3B',8,'TRAIN_DONE_MANUAL_EPOCH13'):
        assert score==96.92
        variant='stable'
    if 'DIAGNOSTIC' in status or 'NONCONVERGENT' in status: variant += '_diagnostic'
    # Preserve historical full precision when the table is merely rounded.
    put((ds,DM[r[0]],layer),variant,score,f'{MANUAL.name}:{lineno}',status)

# Cross-check candidate unions against the separately reconciled live-coverage audit.
audit=json.loads((ROOT/'outputs/localization_audit_20260922/formal8_union_status.json').read_text(encoding='utf-8'))
for r in audit['combinations']:
    assert set(r['top3'])=={l for m in METHODS for l in candidates[(r['dataset'],r['model'],m)]}

diag=ROOT/'server_results/live_backfill/pali_l0_diag_20260922/evqa-pilot500/paligemma-3b/layer_00/verified_evaluation.json'
r=json.loads(diag.read_text(encoding='utf-8'))['result']
assert r['eval_samples']==2093 and int(r['ckpt_epoch'])==2
put(('EVQA-pilot500','PaliGemma-3B',0),'main_diagnostic',float(r['Average']),str(diag),r['status'],True)

def compute(variants):
    accepted = {}
    for ds in DS.values():
        for model in DM.values():
            for layer in range(100):
                for variant in variants:
                    k=(ds,model,layer,variant)
                    if k in scores:
                        accepted[(ds,model,layer)] = (scores[k],variant)
                        break
    complete=[]; excluded=[]; details=[]; ties=[]
    for ds in DS.values():
        for model in DM.values():
            union=sorted({l for m in METHODS for l in candidates[(ds,model,m)]})
            missing=[l for l in union if (ds,model,l) not in accepted]
            if missing:
                excluded.append(dict(dataset=ds,model=model,missing=missing)); continue
            complete.append((ds,model))
            oracle=max(accepted[(ds,model,l)][0] for l in union)
            bestlayers=[l for l in union if abs(accepted[(ds,model,l)][0]-oracle)<1e-9]
            if len(bestlayers)>1: ties.append(dict(dataset=ds,model=model,layers=bestlayers))
            for method in METHODS:
                ls=candidates[(ds,model,method)]
                vals=[accepted[(ds,model,l)][0] for l in ls]
                details.append(dict(dataset=ds,model=model,method=method,layers=ls,scores=vals,
                    variants=[accepted[(ds,model,l)][1] for l in ls],
                    best=max(vals),mean=mean(vals),regret=oracle-max(vals),
                    hit=int(bool(set(ls)&set(bestlayers))),oracle=oracle,oracle_layers=bestlayers))
    summary=[]
    for method in METHODS:
        group=[r for r in details if r['method']==method]
        summary.append(dict(method=method,n=len(group),**{k:mean(r[k] for r in group) for k in ('best','mean','regret','hit')}))
    for r in summary:
        r['ranks']={k:1+sum((s[k]>r[k]+1e-10 if k!='regret' else s[k]<r[k]-1e-10) for s in summary) for k in ('best','mean','regret','hit')}
    return dict(combinations=complete,excluded=excluded,ties=ties,
                summary=sorted(summary,key=lambda r:-r['best']),details=details)

out=dict(conflicts=conflicts,primary=compute(['main']),
         diagnostic_sensitivity=compute(['main','main_diagnostic']))
for name in ('primary','diagnostic_sensitivity'):
    out[name]['n']=len(out[name]['combinations'])
assert out['primary']['n']==17
assert out['diagnostic_sensitivity']['n']==18
assert not conflicts, conflicts
# Explicitly requested sensitivity: main first (including designated diagnostic L0),
# stable only when main is unavailable. Never choose the larger score by variant.
if '--include-stable-fallback' in __import__('sys').argv:
    out['mixed19_user_requested']=compute(['main','main_diagnostic','stable'])
    out['mixed19_user_requested']['n']=len(out['mixed19_user_requested']['combinations'])
    assert out['mixed19_user_requested']['n']==19
    stable_used={(r['dataset'],r['model'],l) for r in out['mixed19_user_requested']['details']
                 for l,v in zip(r['layers'],r['variants']) if v=='stable'}
    assert stable_used=={('MMKE-visual','PaliGemma-3B',l) for l in (1,2,3,5,6,7,13)}
    out['mixed19_user_requested']['protocol']='User-requested mixed-configuration sensitivity, NOT uniform-main primary comparison'
for name in ('primary','diagnostic_sensitivity','mixed19_user_requested'):
    if name not in out: continue
    if '--detail' not in __import__('sys').argv: del out[name]['details']
print(json.dumps(out,ensure_ascii=False,indent=2))
