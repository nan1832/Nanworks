"""Independent audit: stdlib quantiles, original source files, and recomputed metrics."""
from pathlib import Path
from statistics import quantiles,mean
import csv,json,hashlib,math,re,sys
H=Path(__file__).resolve().parent
def rows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-9),(a,b)
def ls(s):return [int(x.removeprefix('L')) for x in s.split(',') if x not in ['—','-','']]
manifest=load(H/'source_manifest.json')
for x in manifest['files']:assert hashlib.sha256((H/x['relative']).read_bytes()).hexdigest()==x['sha256']
audit={(r['dataset'],r['model']):r for r in rows(H/'tukey_audit_21groups.csv')}
cand={(r['dataset'],r['model'],r['method']):r for r in rows(H/'candidate_topk_21x8.csv')}
checked_ranks=0;excluded=0
for p in (H/'raw').glob('*/*/layer_scores.csv'):
    d,m=p.parts[-3:-1];z=audit[d,m];rr=rows(p);valid=[r for r in rr if r['status']=='ok' and math.isfinite(float(r['score']))]
    vv=[float(r['score']) for r in valid];q1,_,q3=quantiles(vv,n=4,method='inclusive');lo=q1-(q3-q1);hi=q3+(q3-q1)
    for key,val in [('q1',q1),('q3',q3),('lower',lo),('upper',hi)]:close(z[key],val)
    ordered=sorted(valid,key=lambda r:(-float(r['score']),int(r['layer'])))
    kept=[int(r['layer']) for r in ordered if lo<=float(r['score'])<=hi]
    ex=[int(r['layer']) for r in ordered if float(r['score'])<lo or float(r['score'])>hi]
    assert ex==ls(z['excluded_layers']);excluded+=len(ex)
    for k in [1,3,5]:
        assert kept[:k]==ls(cand[d,m,'LGA-Param-Tukey']['top'+str(k)]);checked_ranks+=1
        assert [int(r['layer']) for r in ordered[:k]]==ls(cand[d,m,'LGA-Param-Raw']['top'+str(k)]);checked_ranks+=1
assert len(audit)==21 and excluded==76
out={(r['dataset'],r['model'],int(r['layer'])):r for r in rows(H/'outcomes_main_used.csv')}
checked_metrics=0
for r in rows(H/'method_metrics.csv'):
    d,m,k=r['dataset'],r['model'],int(r['k']);cc=ls(r['candidates']);valid={}
    for (dd,mm,l),o in out.items():
        if (dd,mm)!=(d,m):continue
        if r['profile']=='clean' and (o['config']=='main/recovered-early' or re.search('FAILED|NO_EVAL|NONCONVERGENT|DIAGNOSTIC|NUMERIC|NONFINITE|STALL',o['status'],re.I)):continue
        assert o['config']!='stable';valid[l]=float(o['Average'])
    missing=[l for l in cc if l not in valid]
    assert missing==ls(r['missing_or_excluded'])
    complete=len(cc)==k and not missing;assert complete==(r['complete']=='True')
    if complete:
        yy=[valid[l] for l in cc];ref=max(valid.values())
        for name,val in [('best',max(yy)),('mean',mean(yy)),('regret',ref-max(yy)),('hit',int(abs(max(yy)-ref)<1e-9))]:close(r[name],val)
        checked_metrics+=1
    else:assert not r['best'] and not r['mean'] and not r['regret'] and not r['hit']
paired=rows(H/'paired_comparisons.csv');summ=rows(H/'paired_summary.csv')
for r in summ:
    keys=['profile','coverage_policy','scope','k','method_a','method_b'];zz=[x for x in paired if all(x[k]==r[k] for k in keys)];assert len(zz)==int(r['n'])
    for k in ['a_best','b_best','a_mean','b_mean','delta_best','delta_mean','a_regret','b_regret','a_hit','b_hit']:close(r[k],mean(float(x[k]) for x in zz))
    assert int(r['a_wins'])+int(r['ties'])+int(r['a_losses'])==len(zz)
fair=rows(H/'same_cohort_method_summary.csv');counts={}
for r in fair:
    group=r['profile'],r['comparison'],r['k'];g=r['groups'];assert group not in counts or counts[group]==g;counts[group]=g
missing=rows(H/'tukey_candidate_execution_status.csv');s=load(H/'calculation_summary.json')
for k in [3,5]:assert sum(r['main_evaluation_available']=='False' and r['k']==str(k) for r in missing)==s['top'+str(k)+'_missing_unique']
assert s['top3_missing_unique']==17 and s['top5_missing_unique']==35
root=H.parents[1]
ledger=(root/'md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md').read_text(encoding='utf-8');start=ledger.index('### 4.3 MMKE-entity');start=ledger.index('#### LLaVA-v1.5-7B',start);end=ledger.find('\n#### ',start+5)
assert '| L9 | main | — | 48 | 0.293750 | 0.323795 | 954 | 60.96 | 60.99 | 60.95 | 100.00 | 95.23 | 75.626 |' in ledger[start:end]
result=dict(status='PASS',source_hashes_verified=len(manifest['files']),groups=21,independent_quantiles='statistics.quantiles inclusive (type 7)',rank_lists_verified=checked_ranks,excluded_layers=excluded,complete_metric_rows_verified=checked_metrics,paired_summary_rows_verified=len(summ),same_cohort_tables_verified=len(counts),missing_top3=17,missing_top5=35,l9_full_evaluation_verified=load(H/'supplemental_evaluation_verification.json'),server_mutations=0,new_gpu_training_launched=False)
(H/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
