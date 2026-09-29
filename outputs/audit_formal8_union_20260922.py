"""Rebuild dual-CMA Top-3/5 unions, preserving diagnostic and stable boundaries."""
import csv
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/localization_audit_20260922'
OUT.mkdir(exist_ok=True)
MANUAL = ROOT / 'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
RECOMMEND = ROOT / 'md/TODO/Second_prashe/Firstprash_7_location_recommend.md'
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


def layers(s):
    return [int(x) for x in re.findall(r'L(\d+)', s)]


def table(text, header):
    ls=text.splitlines(); i=ls.index(header)
    rows=[]
    for line in ls[i+2:]:
        if not line.startswith('|'): break
        rows.append([v.strip() for v in line.strip('|').split('|')])
    return rows


text=MANUAL.read_text(encoding='utf-8')
candidates={}
for r in csvrows(ROOT/'outputs/formal7_method_topk_performance_20260801.csv'):
    m='CMA-Direct-v1.3-alt' if r['method']=='CMA-Direct' else r['method']
    candidates[(r['dataset'],r['model'],m)]={k:layers(r[k]) for k in ('top3','top5')}
for r in table(text,'| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |'):
    candidates[(r[0],r[1],METHODS[-1])]={'top3':layers(r[2]),'top5':layers(r[3])}
assert len(candidates)==168
for key,v in candidates.items():
    assert len(v['top3'])==len(set(v['top3']))==3, key
    assert len(v['top5'])==len(set(v['top5']))==5, key
    assert set(v['top3'])<=set(v['top5'])
# Cross-check the standalone recommendation document, rather than trust totals.
seen=0; method=None
for line in RECOMMEND.read_text(encoding='utf-8').splitlines():
    if line.startswith('## 4.'): break
    if line.startswith('### 3.'):
        method=next((m for m in METHODS if m in line),None)
        if line.startswith('### 3.7 '): method=METHODS[-2]
        if line.startswith('### 3.8 '): method=METHODS[-1]
    if method and line.startswith('|'):
        r=[v.strip() for v in line.strip('|').split('|')]
        key=(r[0],r[1],method) if len(r)>=4 else None
        if key in candidates:
            assert candidates[key]=={'top3':layers(r[2]),'top5':layers(r[3])}, key
            seen+=1
assert seen==168, seen
known=defaultdict(list)
for filename in ('formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv','formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv'):
    for r in csvrows(ROOT/'outputs'/filename):
        # Prior verified coverage is inherited, not mislabeled as freshly inspected artifacts.
        for kind,group in re.findall(r'(主|stable-only):([^;；]+)',r['top5_done']):
            for l in layers(group):
                known[(r['dataset'],r['model'],l)].append(dict(variant='stable' if kind=='stable-only' else 'main',source=filename))
inside=False; dataset=None
for lineno,line in enumerate(text.splitlines(),1):
    if line=='### 4.0 服务器结构化结果总表': inside=True
    if line.startswith('### 4.1 '): inside=False
    if not inside: continue
    if line.startswith('#### ') and line[5:] in DS.values(): dataset=line[5:]
    if not dataset or not line.startswith('|'): continue
    r=[v.strip() for v in line.strip('|').split('|')]
    if len(r)!=13 or r[0] not in DM: continue
    try: float(r[11]); n=int(r[5]); l=layers(r[1])[0]
    except (ValueError,IndexError): continue
    if n != {'EVQA-pilot500':2093,'MMKE-visual':293,'MMKE-entity':954}[dataset]: continue
    status=r[12].upper()
    if 'FAILED' in status or 'NO_EVAL' in status: continue
    variant='diagnostic' if 'NONCONVERGENT' in status else ('stable' if 'STABLE' in status else 'main')
    known[(dataset,DM[r[0]],l)].append(dict(variant=variant,source=f'{MANUAL.name}:{lineno}',status=status))
live=defaultdict(list)
for p in OUT.glob('*llava*.json'):
    data=json.loads(p.read_text(encoding='utf-8'))
    for row in data['layers']:
        key=(DS[row['dataset']],DM[row['model']],row['layer'])
        live[key].append(row)
        if row['complete']:
            known[key].append(dict(variant='main',source=row['layer_dir'],fresh_verified=True))
diagnostic=OUT/'paligemma_diagnostic_verified.json'
if diagnostic.exists():
    d=json.loads(diagnostic.read_text(encoding='utf-8'))
    assert d['evaluation_verified'] and d['eval_samples']==2093 and d['selected_epoch']==2
    known[('EVQA-pilot500','PaliGemma-3B',0)].append(dict(variant='diagnostic',source=d['source']))

rows=[]; pending=[]
for ds in DS.values():
    for model in DM.values():
        u3=sorted({l for m in METHODS for l in candidates[(ds,model,m)]['top3']})
        u5=sorted({l for m in METHODS for l in candidates[(ds,model,m)]['top5']})
        states={}
        for l in u5:
            key=(ds,model,l); evidence=known[key]; variants={x['variant'] for x in evidence}
            if (ds,model,l) in [('EVQA-pilot500','PaliGemma-3B',0),('MMKE-visual','PaliGemma-3B',0)] and 'diagnostic' in variants: status='diagnostic_eval_only'
            elif 'main' in variants: status='evaluated_main_historical_acceptance'
            elif 'stable' in variants: status='evaluated_stable_only'
            elif any(x['selected'] and 'missing_train.done' not in x['errors'] for x in live[key]): status='evaluation_pending'
            elif ds=='MMKE-entity' and model=='LLaVA-v1.5-7B' and l==1: status='paused_incomplete_training'
            elif model=='PaliGemma-3B' and l==0: status='diagnostic_eval_in_progress'
            else: status='not_evaluated'
            states[str(l)]={'status':status,'evidence':evidence,'live':live[key]}
            if l in u3 and not status.startswith(('evaluated_','diagnostic_eval_only')):
                pending.append(dict(dataset=ds,model=model,layer=l,status=status))
        row=dict(dataset=ds,model=model,top3=u3,top5=u5,states=states)
        rows.append(row)
assert sum(len(r['top3']) for r in rows)==324
counts=Counter(r['states'][str(l)]['status'] for r in rows for l in r['top3'])
payload=dict(candidate_rows=len(candidates),recommendation_crosscheck_rows=seen,
             top3_total=sum(len(r['top3']) for r in rows),top5_total=sum(len(r['top5']) for r in rows),
             top3_counts=counts,pending_top3=pending,combinations=rows,
             scope='Historical accepted coverage plus fresh active-job artifact verification; not a claim that every inherited result is converged or full 50 epochs')
(OUT/'formal8_union_status.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in payload.items() if k!='combinations'},ensure_ascii=False,indent=2))
