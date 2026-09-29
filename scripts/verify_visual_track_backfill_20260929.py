"""Check numeric rankings/performance and preservation of existing ledger text."""
import ast
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/visual_track_cosine_20260928/targets_v2'
DOC=ROOT/'md/Location';BACKUP=OUT/'backfill_20260929/backups'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def key(r):return tuple(r[k] for k in ['dataset','model','variant','cohort','flavor'])

recs=load(OUT/'recommendations.json');lookup={key(r):r for r in recs}
assert len(lookup)==252
for r in recs:
    data=load(OUT/'results'/r['dataset']/r['model']/'layer_scores.json')['rows']
    values={z['layer']:z['visual_track_cos'] for z in data if z['variant']==r['variant'] and z['cohort']==r['cohort']}
    a=sorted(values.values())
    def quant(q):
        i=(len(a)-1)*q;j=int(i)
        return a[j]+(a[min(j+1,len(a)-1)]-a[j])*(i-j)
    q1,q3=quant(.25),quant(.75);lo,hi=q1-(q3-q1),q3+(q3-q1)
    drop=sorted(l for l,v in values.items() if r['flavor']=='tukey' and (v<lo or v>hi))
    order=sorted((l for l in values if l not in drop),key=lambda l:(-values[l],l))
    assert order==r['all_ranking'] and order[:3]==r['top3'] and order[:5]==r['top5'] and drop==r['outlier_layers'],key(r)
ledger=load(OUT.parent/'inputs/ledger.json')
main={(r['dataset'],r['model'],r['layer']):r['metrics']['Average'] for r in ledger['rows'] if r['recipe']=='main'}
performance=list(csv.DictReader((OUT/'performance.csv').open(encoding='utf-8-sig')))
for p in performance:
    r=lookup[key(p)];cand=r['top3'];missing=[l for l in cand if (r['dataset'],r['model'],l) not in main]
    assert missing==json.loads(p['missing_main_layers']) and int(p['top1_layer'])==cand[0],key(p)
    n=main.get((r['dataset'],r['model'],cand[0]))
    assert p['top1']=='' if n is None else abs(float(p['top1'])-n)<1e-8
    if missing:assert p['best3']==p['mean3']==''
    else:
        vals=[main[r['dataset'],r['model'],l] for l in cand]
        assert abs(float(p['best3'])-max(vals))<1e-8 and abs(float(p['mean3'])-statistics.mean(vals))<1e-8
for name in ['SWeeplayers.md','6location_7model_3datas_top_3_5_layers_outcome.md','ALL_Methods_Recommends_layers.md']:
    old=(BACKUP/name).read_bytes().decode('utf-8');new=(DOC/name).read_bytes().decode('utf-8')
    if name=='SWeeplayers.md':old=old.rstrip();new=new.split('<!-- VISUAL_TRACK_PERFORMANCE_START -->')[0].rstrip()
    elif name.startswith('6location'):old=old.split('## 3. 数据集分表',1)[1];new=new.split('## 3. 数据集分表',1)[1]
    else:new=re.sub(r'<!-- VISUAL_TRACK_RESULTS_START -->.*?<!-- VISUAL_TRACK_RESULTS_END -->\s*','',new,flags=re.S)
    assert old==new,name
source=(ROOT/'scripts/build_all_method_recommendations.py').read_text(encoding='utf-8');tree=ast.parse(source)
func=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='make_main')
ns={'ROOT':ROOT,'read':lambda p:p.read_text(encoding='utf-8'),'hashlib':hashlib}
exec(compile(ast.Module(body=[func],type_ignores=[]),'<make_main>','exec'),ns)
new,digest=ns['make_main']((DOC/'6location_7model_3datas_top_3_5_layers_outcome.md').read_text(encoding='utf-8'),'verification-only')
assert new.count('<!-- VISUAL_TRACK_INDEX_START -->')==1 and '### 2.9' in new
result={'status':'PASS','recommendations_recomputed':len(recs),'performance_rows_recomputed':len(performance),'existing_recommendation_sections_preserved':True,'existing_real_editing_rows_preserved':True,'rebuild_retains_visual_track_index':True}
(OUT/'backfill_20260929/independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
