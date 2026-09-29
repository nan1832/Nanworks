"""Compare the three target variants using frozen real-editing results."""
import collections
import csv
import hashlib
import json
import math
import statistics as st
import sys
from pathlib import Path
import numpy as np
from run_visual_track_targets_20260928 import MODELS,DATASETS,VARIANTS

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/visual_track_cosine_20260928';OUT=BASE/'targets_v2';OUT.mkdir(exist_ok=True)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def writecsv(n,rr):
    if not rr:return
    with (OUT/n).open('w',encoding='utf-8-sig',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for r in rr for k in r)));w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rr)
def ranking(values,flavor):
    assert all(math.isfinite(v) for v in values.values())
    q1,q3=map(float,np.quantile(list(values.values()),[.25,.75],method='linear'));lo,hi=q1-(q3-q1),q3+(q3-q1)
    drop=sorted(l for l,v in values.items() if flavor=='tukey' and (v<lo or v>hi))
    order=sorted((l for l in values if l not in drop),key=lambda l:(-values[l],l))
    return dict(all_ranking=order,top1=order[:1],top3=order[:3],top5=order[:5],outlier_layers=drop,lower=lo,upper=hi)
def rho(x,y):
    def ranks(a):return [sum(v<t for v in a)+(sum(v==t for v in a)+1)/2 for t in a]
    x,y=ranks(x),ranks(y);mx,my=st.mean(x),st.mean(y)
    den=math.sqrt(sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/den if den else None

ledger=load(BASE/'inputs/ledger.json');old=load(BASE/'inputs/recommendations.json')['records']
old={(r['dataset'],r['model'],r['method'],r['flavor']):r for r in old}
pool=collections.defaultdict(dict)
for r in ledger['rows']:
    if r['recipe']=='main':
        assert r['layer'] not in pool[r['dataset'],r['model']],'Duplicate main results'
        pool[r['dataset'],r['model']][r['layer']]=r['metrics']

status=[];recs=[];performance=[];correlations=[];comparisons=[]
for ds in DATASETS:
    for model in MODELS:
        p=OUT/'results'/ds/model
        if not (p/'summary.json').exists():
            status.append(dict(dataset=ds,model=model,status='pending_forward',variants=VARIANTS));continue
        s=load(p/'summary.json');assert s['status']=='done' and s['schema']==2
        for n,k in [('protocol.json','protocol_sha256'),('layer_scores.json','scores_sha256'),('diagnostics.json','diagnostics_sha256')]:assert hashlib.sha256((p/n).read_bytes()).hexdigest()==s[k]
        assert s['matched_sample_count']==old[ds,model,'Ours-main','raw']['sample_count']
        status.append(dict(dataset=ds,model=model,status='done',variants=VARIANTS,matched_samples=s['matched_sample_count'],available_counts=s['available_counts']))
        data=load(p/'layer_scores.json')['rows'];pp=pool[ds,model]
        for cohort in ['matched_gradient','available_train']:
            for variant in VARIANTS:
                rows=[r for r in data if r['variant']==variant and r['cohort']==cohort]
                assert len(rows)==MODELS[model] and len({r['n'] for r in rows})==1
                values={r['layer']:r['visual_track_cos'] for r in rows}
                for flavor in ['raw','tukey']:
                    rec=dict(dataset=ds,model=model,variant=variant,cohort=cohort,flavor=flavor,n=rows[0]['n'],coverage=rows[0]['n']/DATASETS[ds],**ranking(values,flavor));recs.append(rec)
                    cand=rec['top3'];missing=[l for l in cand if l not in pp];complete=len(cand)==3 and not missing
                    measures=dict(top1=pp[cand[0]]['Average'] if cand and cand[0] in pp else None,best3=max(pp[l]['Average'] for l in cand) if complete else None,mean3=st.mean(pp[l]['Average'] for l in cand) if complete else None)
                    perf_rec={k:v for k,v in rec.items() if k!='top1'}
                    performance.append(dict(**perf_rec,top1_layer=cand[0] if cand else None,missing_main_layers=missing,status='complete' if complete else 'missing_edit_evaluation',**measures))
                    observed=[l for l in rec['all_ranking'] if l in pp]
                    for metric in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']:
                        correlations.append(dict(dataset=ds,model=model,variant=variant,cohort=cohort,flavor=flavor,metric=metric,n_layers=len(observed),rho=rho([values[l] for l in observed],[pp[l][metric] for l in observed]) if len(observed)>=5 else None))
                    if cohort=='matched_gradient' and complete:
                        for baseline in ['Ours-no-direction','Ours-main','Ours-signed-direction','LGA-Visual','LGA-Param']:
                            for bf in ['raw','tukey']:
                                b=old[ds,model,baseline,bf];bc=b['all_ranking'][:3]
                                if len(bc)!=3 or any(l not in pp for l in bc):continue
                                br=dict(top1=pp[bc[0]]['Average'],best3=max(pp[l]['Average'] for l in bc),mean3=st.mean(pp[l]['Average'] for l in bc))
                                comparisons.append(dict(dataset=ds,model=model,variant=variant,flavor=flavor,baseline=baseline,baseline_flavor=bf,coverage=min(rec['coverage'],b['sample_count']/DATASETS[ds]),green=measures,reference=br,**{'delta_'+m:measures[m]-br[m] for m in measures}))
writecsv('source_status.csv',status);save('recommendations.json',recs);writecsv('recommendations.csv',recs)
writecsv('performance.csv',performance);writecsv('correlations.csv',correlations);writecsv('pairwise.csv',comparisons)
grouped=collections.defaultdict(list)
for r in comparisons:
    if r['coverage']>=.8:grouped[r['variant'],r['flavor'],r['baseline'],r['baseline_flavor']].append(r)
summary=[]
for (v,f,b,bf),rr in grouped.items():
    row=dict(variant=v,flavor=f,baseline=b,baseline_flavor=bf,n=len(rr),groups=[[r['dataset'],r['model']] for r in rr])
    for m in ['top1','best3','mean3']:
        row['green_'+m]=st.mean(r['green'][m] for r in rr);row['baseline_'+m]=st.mean(r['reference'][m] for r in rr);row['delta_'+m]=st.mean(r['delta_'+m] for r in rr)
        row['wins_'+m]=sum(r['delta_'+m]>1e-9 for r in rr);row['ties_'+m]=sum(abs(r['delta_'+m])<=1e-9 for r in rr);row['losses_'+m]=sum(r['delta_'+m]<-1e-9 for r in rr)
    summary.append(row)
writecsv('paired_summary.csv',summary)
# Fixed cohorts for none/alt/model_pred: every row in a comparison uses all three variants.
three=[]
for flavor in ['raw','tukey']:
    groups=[]
    for ds in DATASETS:
        for model in MODELS:
            rr=[r for r in performance if r['dataset']==ds and r['model']==model and r['cohort']=='matched_gradient' and r['flavor']==flavor and r['status']=='complete' and r['coverage']>=.8]
            if len(rr)==3:groups.append(rr)
    for variant in VARIANTS:
        rr=[next(r for r in group if r['variant']==variant) for group in groups]
        three.append(dict(variant=variant,flavor=flavor,n=len(rr),groups=[[r['dataset'],r['model']] for r in rr],**{m:st.mean(r[m] for r in rr) if rr else None for m in ['top1','best3','mean3']}))
writecsv('three_variant_fixed_cohort.csv',three)
done=sum(r['status']=='done' for r in status)
save('verification.json',dict(status='PASS',formal_groups_done=done,formal_variants_done=done*3,formal_groups_pending=21-done,main_rows=sum(len(r) for r in pool.values()),constant_metric_rho_is_null=True,performance_requires_full_top3=True))
print(json.dumps(dict(formal_done=done,formal_pending=21-done,recommendations=len(recs),output=str(OUT)),ensure_ascii=False))
