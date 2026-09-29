"""Independent checks against original cached scores and frozen outcomes."""
from pathlib import Path
import json,csv,hashlib,math,io
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
def rc(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
groups={}
for p in (H/'inputs').glob('*__*.json'):
    x=json.loads(p.read_text(encoding='utf-8'));g=x['dataset'],x['model'];groups[g]=x
    n=len(x['samples']);assert all(v==n for v in x['layer_sample_counts'].values())
    for r in csv.DictReader(io.StringIO(x['files']['ours_direct_layer_scores.csv']['text'])):
        assert int(r['n_request'])==n
        pos=float(r['S_v_positive_ratio'])*n
        assert abs(pos-round(pos))<1e-7
    for name,v in x['files'].items():assert hashlib.sha256(v['text'].encode()).hexdigest()==v['sha256']
assert len(groups)==21
tops={(r['dataset'],r['model'],r['formula']):r for r in rc(H/'candidate_topk.csv')}
old=rc(ROOT/'outputs/main_formula_validation_20260925/candidate_topk.csv')
matches=0
for r in old:
    if r['method'] not in ['main_abs_cos_new_norm','new_norm_only','one_minus_cos_new_norm']:continue
    name={'main_abs_cos_new_norm':'abs_cos_norm','new_norm_only':'norm','one_minus_cos_new_norm':'one_minus_cos_norm'}[r['method']]
    for k in [1,3]:
        assert r['top'+str(k)].replace('L','')==tops[r['dataset'],r['model'],name]['top'+str(k)];matches+=1
y={(r['dataset'],r['model'],int(r['layer'])):float(r['Average']) for r in rc(H/'observed_main_outcomes.csv')}
metric_checks=0
for r in rc(H/'formula_metrics.csv'):
    if r['profile']!='observed_main' or r['complete']!='True':continue
    vals=[y[r['dataset'],r['model'],int(l)] for l in r['candidates'].split(',')]
    assert len(vals)==int(r['k'])
    assert abs(max(vals)-float(r['Average_best']))<1e-9
    assert abs(sum(vals)/len(vals)-float(r['Average_mean']))<1e-9
    metric_checks+=1
hashes={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'inputs').glob('*') if p.is_file()}
summary=dict(groups=21,integer_positive_count_checks=True,source_hash_checks=True,
             previous_topk_matches=matches,observed_metric_checks=metric_checks,
             per_sample_gradient_not_present=True,source_input_sha256=hashes)
(H/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='source_input_sha256'}))
