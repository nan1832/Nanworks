"""Independent checks against frozen CSV results and explicit subset enumeration."""
import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/all_methods_performance_20260928"
def jr(p):return json.loads(p.read_text(encoding="utf-8"))
def cr(p):return list(csv.DictReader(p.open(encoding="utf-8-sig")))
protocol=jr(OUT/"protocol.json")
for name,item in protocol['input_manifest'].items():
    assert hashlib.sha256((OUT/'inputs'/name).read_bytes()).hexdigest()==item['sha256']
original=jr(OUT/'inputs/recommendations.json')['records']
registry=jr(OUT/'recommendation_registry.json')
reg={(r['dataset'],r['model'],r['method'],r['flavor']):r for r in registry}
for r in original:
    x=reg[r['dataset'],r['model'],r['method'],r['flavor']]
    assert x['top3']==r['top3'] and x['formula_status']==r['status']
data=jr(OUT/'inputs/ledger.json')['rows']
csvdata=cr(OUT/'inputs/sweep_results.csv')
direct_csv={(r['dataset'],r['model'],int(r['layer']),r['recipe']):r for r in csvdata}
assert len(direct_csv)==433
for r in data:
    c=direct_csv[r['dataset'],r['model'],r['layer'],r['recipe']]
    for m in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']:assert abs(float(c[m])-r['metrics'][m])<1e-8
metrics=jr(OUT/'method_performance_all.json')
complete_main=0;pending=0
bykey={(r['policy'],r['dataset'],r['model'],r['variant'],r['k']):r for r in metrics}
for r in metrics:
    if r['status']!='complete':
        assert r['best'] is None and r['mean'] is None and r['hit'] is None
        pending+=1;continue
    assert r['mean']<=r['best']+1e-8 and r['regret']>=-1e-8
    assert abs(r['delta_best_random']-(r['best']-r['random_expected_best']))<1e-8
    one=bykey[r['policy'],r['dataset'],r['model'],r['variant'],1]
    assert one['status']=='complete' and one['best']<=r['best']+1e-8
    if r['policy']=='observed_main':
        ls=[int(l[1:]) for l in r['candidates'].split(',')]
        vals=[float(direct_csv[r['dataset'],r['model'],l,'main']['Average']) for l in ls]
        assert len(vals)==r['k']==r['evaluated_count']
        assert abs(max(vals)-r['best'])<1e-8
        assert abs(statistics.mean(vals)-r['mean'])<1e-8
        assert abs(vals[0]-r['rank1_score'])<1e-8
        complete_main+=1
refs=cr(OUT/'observed_pool_and_random_reference.csv')
random_checks=0
for ref in refs:
    if ref['policy']!='observed_main' or ref['k'] not in ['1','3']:continue
    vals=[float(r['Average']) for r in csvdata if r['dataset']==ref['dataset'] and r['model']==ref['model'] and r['recipe']=='main']
    k=int(ref['k']);subsets=list(itertools.combinations(vals,k))
    actual=statistics.mean(max(x) for x in subsets)
    assert abs(actual-float(ref['random_expected_best']))<1e-8
    random_checks+=1
pairs=cr(OUT/'all_pairwise_comparisons.csv')
pairchecks=0
for r in pairs:
    n=int(r['n'])
    for f in ['best','mean']:
        assert sum(int(r[f+'_'+w]) for w in ['wins','ties','losses'])==n
        if n:assert abs(float(r['a_'+f])-float(r['b_'+f])-float(r['delta_'+f]))<1e-8
    if r['policy']=='observed_main' and r['k']=='3' and r['coverage_filter']=='all' and r['scope']=='all' and n:
        groups=[g.split('/') for g in json.loads(r['groups'])]
        assert len(groups)==n
        for metric in ['best','mean']:
            values=[bykey['observed_main',d,m,r['a'],3][metric]-bykey['observed_main',d,m,r['b'],3][metric] for d,m in groups]
            assert abs(statistics.mean(values)-float(r['delta_'+metric]))<1e-8
        pairchecks+=1
cohorts=cr(OUT/'fixed_cohort_comparisons.csv')
core=[r for r in cohorts if r['cohort']=='core7_current' and r['policy']=='observed_main' and r['k']=='3' and r['coverage_filter']=='all' and r['scope']=='all']
assert len(core)==7 and all(r['n']=='18' for r in core)
assert len({r['groups'] for r in core})==1
for name in ['SWeeplayers.md','ALL_Methods_Recommends_layers.md']:
    p=ROOT/'md/Location'/name
    if (OUT/'manual_backups'/name).exists():
        old=(OUT/'manual_backups'/name).read_text(encoding='utf-8-sig').rstrip()
        new=p.read_text(encoding='utf-8-sig').split('<!-- ALL_METHODS_PERFORMANCE_20260928 -->')[0].rstrip()
        assert old==new
result=dict(status='PASS',input_hashes_verified=len(protocol['input_manifest']),registered_top3_unchanged=len(original),
            ledger_csv_json_agree=433,complete_main_performance_checked=complete_main,missing_metrics_kept_null=pending,
            random_expectations_checked_by_enumeration=random_checks,paired_rows_checked=len(pairs),main_top3_pairwise_recomputed=pairchecks,
            core7_shared_groups=18,original_markdown_tables_unchanged=True)
(OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
