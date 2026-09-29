"""Reproducible post-hoc LGA Tukey correction. No training, no outcome-based tuning."""
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean
import ast, csv, json, math, re, hashlib, shutil, sys
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
H=Path(__file__).resolve().parent; ROOT=H.parents[1]; I=H/'inputs'; I.mkdir(exist_ok=True)
VERSION='lga-tukey-k1-20260926'
RAW='LGA-Param-Raw'; TUKEY='LGA-Param-Tukey'; OURS='Ours-Direct'
DS=['evqa-pilot500','mmke-visual','mmke-entity']; TOTAL=dict(zip(DS,[500,214,636])); EVAL=dict(zip(DS,[2093,293,954]))
MODELS=['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b','qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']
DISPLAY=['BLIP2-OPT-2.7B','InstructBLIP-Vicuna-7B','MiniGPT-4-Vicuna-7B','LLaVA-v1.5-7B','Qwen2.5-VL-3B','PaliGemma-3B','SmolVLM-Instruct-1.7B']; REV=dict(zip(DISPLAY,MODELS))
BASE=ROOT/'md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731'
SEVEN=['Middle-Prior-Direct','VisEdit-Contrib-Pre-KeyToken','SaLEM-Alt-Direct',TUKEY,'Perturb-KL-Direct-AltSeq',OURS,'CMA-ModelPred-Direct']
METRICS=['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']
sources={}
def read(p):
    p=Path(p); sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return p.read_text(encoding='utf-8-sig')
def rows(p):return list(csv.DictReader(read(p).splitlines()))
def load(p):return json.loads(read(p))
def write(name,rr):
    if not rr:return
    with (H/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
def jwrite(name,z):(H/name).write_text(json.dumps(z,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def layers(s):return list(map(int,ast.literal_eval(s))) if s.startswith('[') else [int(x.strip().removeprefix('L')) for x in s.split(',') if x.strip() not in ['', '-', '—']]
def fmt(v):return ','.join('L'+str(x) for x in v) or '—'
def snapshot(src,name):
    dst=I/name
    if not dst.exists():shutil.copyfile(src,dst)
    return dst
protocol=dict(version=VERSION,paper='https://arxiv.org/html/2602.20207v3#A1',kappa=1.0,quartile_method='numpy.quantile(method=linear)',
    fences='Q1 - 1*IQR <= signed_raw_dot <= Q3 + 1*IQR',filter_scope='all finite ok MLP/FFN parameter-layer scores within each dataset-model',
    rank='descending signed raw dot, ascending layer for ties',normalization='none; existing mean and paper sum equivalent because n identical across layers',
    original_filtered_rank='empty, not actually Tukey-filtered',ranking_budget=[1,3,5],
    outcome_protocol='existing main configuration; observed_main includes evaluated nonconvergent runs; clean sensitivity excludes early/numeric/diagnostic runs; never mix stable',
    metric_reference='best among observed comparable layers, not all-layer oracle',
    limitations='paper does not specify quantile interpolation; linear interpolation is an explicit implementation convention. This corrects Tukey on existing VLM parameter scores; not a new full replication of all original paper settings.')
jwrite('protocol.json',protocol)
manifest=load(H/'source_manifest.json')
for x in manifest['files']:assert hashlib.sha256((H/x['relative']).read_bytes()).hexdigest()==x['sha256']

# Freeze ranking before consulting outcomes.
candidates={}; coverage={}; audit=[]; layer_rows=[]; changes=[]; qsens=[]
for p in sorted((H/'raw').glob('*/*/layer_scores.csv')):
    d,m=p.parts[-3:-1];g=d,m;rr=rows(p);su=load(p.parent/'summary.json')
    valid=[r for r in rr if r['status']=='ok' and math.isfinite(float(r['score']))]
    ns={int(r['valid_sample_count']) for r in valid};assert len(ns)==1,(g,ns);n=ns.pop()
    coverage[g,RAW]=coverage[g,TUKEY]=n/TOTAL[d]
    vals=np.array([float(r['score']) for r in valid]);q1,q3=np.quantile(vals,[.25,.75],method='linear');iqr=q3-q1;lo=q1-iqr;hi=q3+iqr
    ordered=sorted(valid,key=lambda r:(-float(r['score']),int(r['layer'])))
    raw=[int(r['layer']) for r in ordered];kept=[int(r['layer']) for r in ordered if lo<=float(r['score'])<=hi]
    excluded=[int(r['layer']) for r in ordered if int(r['layer']) not in kept]
    assert fmt(raw[:3])==','.join(su['top3_layers']) and fmt(raw[:5])==','.join(su['top5_layers'])
    # A positive common scale must preserve fences and rankings.
    a,b=np.quantile(vals*n,[.25,.75],method='linear');assert [int(r['layer']) for r in ordered if a-(b-a)<=float(r['score'])*n<=b+(b-a)]==kept
    candidates[g,RAW]={k:raw[:k] for k in [1,3,5]};candidates[g,TUKEY]={k:kept[:k] for k in [1,3,5]}
    for method in ['linear','midpoint','lower','higher','nearest']:
        a,b=np.quantile(vals,[.25,.75],method=method);ks=[int(r['layer']) for r in ordered if a-(b-a)<=float(r['score'])<=b+(b-a)]
        qsens.append(dict(dataset=d,model=m,quantile_method=method,top3=fmt(ks[:3]),top5=fmt(ks[:5]),top3_same_primary=ks[:3]==kept[:3],top5_same_primary=ks[:5]==kept[:5]))
    audit.append(dict(dataset=d,model=m,layers=len(rr),valid_layers=len(valid),valid_samples=n,total_samples=TOTAL[d],coverage=n/TOTAL[d],q1=float(q1),q3=float(q3),iqr=float(iqr),lower=float(lo),upper=float(hi),excluded_layers=fmt(excluded),excluded_count=len(excluded),retained_count=len(kept),raw_top3=fmt(raw[:3]),tukey_top3=fmt(kept[:3]),raw_top5=fmt(raw[:5]),tukey_top5=fmt(kept[:5]),top3_changed=raw[:3]!=kept[:3],top5_changed=raw[:5]!=kept[:5],new_top3=fmt([x for x in kept[:3] if x not in raw[:3]]),new_top5=fmt([x for x in kept[:5] if x not in raw[:5]])))
    for r in ordered:
        l=int(r['layer']);v=float(r['score']);layer_rows.append(dict(dataset=d,model=m,layer=l,score=v,sum_equivalent=v*n,valid_samples=n,raw_rank=raw.index(l)+1,tukey_rank=kept.index(l)+1 if l in kept else '',excluded=l not in kept,exclusion_side='below_lower' if v<lo else 'above_upper' if v>hi else '',lower=float(lo),upper=float(hi)))
assert len(audit)==21
write('tukey_audit_21groups.csv',audit);write('parameter_layer_scores_raw_and_tukey.csv',layer_rows);write('quartile_sensitivity.csv',qsens)

for r in rows(snapshot(BASE/'baseline_candidates.csv','baseline_candidates.csv')):
    d,m,f=r['dataset'],r['model'],r['method']
    if f=='LGA-Param-Direct-AltModelPred':continue
    if f not in SEVEN:continue
    candidates[(d,m),f]={k:layers(r['top'+str(max(k,3))])[:k] for k in [1,3,5]}
    coverage[(d,m),f]=float(r['candidate_coverage']) if r['candidate_coverage'] else None
for r in rows(snapshot(BASE/'formula_topk_all_21.csv','formula_topk_all_21.csv')):
    if r['formula']!='M_abscos_x_newn':continue
    g=r['dataset'],r['model'];candidates[g,OURS]={k:layers(r['top'+str(k)]) for k in [1,3,5]};coverage[g,OURS]=float(r['coverage'])
manual=read(snapshot(ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md','location_ledger_snapshot.md')).splitlines()
header='| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |'
start=manual.index(header)
for line in manual[start+2:]:
    if not line.startswith('|'):break
    c=[x.strip() for x in line.strip().strip('|').split('|')];g=c[0].lower(),REV[c[1]]
    candidates[g,'CMA-ModelPred-Direct']={k:layers(c[2 if k<=3 else 3])[:k] for k in [1,3,5]}
    coverage[g,'CMA-ModelPred-Direct']=float(c[6].strip('%'))/100
assert len(candidates)==21*8,len(candidates)
write('candidate_topk_21x8.csv',[dict(dataset=g[0],model=g[1],method=f,coverage=coverage[g,f],top1=fmt(cs[1]),top3=fmt(cs[3]),top5=fmt(cs[5])) for (g,f),cs in candidates.items()])

# Existing main outcomes, with fresh ledger rows taking priority over previous snapshots.
out={};stable={};priority={'main':3,'main/legacy':2,'main/recovered-early':1}
previous=snapshot(ROOT/'outputs/task_direction_analysis_20260926/observed_main_outcomes.csv','previous_main_outcomes.csv')
for r in rows(previous):
    r['layer']=int(r['layer']);r['samples']=int(r['samples'])
    for x in METRICS:r[x]=float(r[x]) if r[x] else None
    r['source']=str(previous);out[(r['dataset'],r['model'],r['layer'])]=r
ledger=snapshot(ROOT/'md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md','outcome_ledger_snapshot.md')
active=False;d=m=None
for no,line in enumerate(read(ledger).splitlines(),1):
    if line.startswith('## 4. '):active=True
    elif active and line.startswith('## '):break
    if not active:continue
    if line.startswith('### 4.'):d=line.split(' ',2)[2].lower()
    elif line.startswith('#### '):m=REV[line[5:]]
    elif line.startswith('| L'):
        c=[x.strip() for x in line.strip().strip('|').split('|')];assert len(c)==14
        match=re.fullmatch(r'L(\d+)(-\d+)?',c[0]);assert match
        if match[2] or c[12] in ['', '-', '—']:continue
        key=d,m,int(match[1]);r=dict(dataset=d,model=m,layer=key[2],config=c[1],samples=int(c[6]),status=c[13],source_line=no,source=str(ledger),**dict(zip(METRICS,map(float,c[7:13]))))
        if r['config']=='stable':stable[key]=r;continue
        if r['config'] not in priority or r['samples']!=EVAL[d]:continue
        if key in out:
            assert abs(out[key]['Average']-r['Average'])<.011,(key,out[key],r)
            if priority[r['config']]<priority.get(out[key]['config'],-1):continue
            # Preserve the already verified machine-readable precision when the
            # fresh ledger agrees up to its display rounding; never choose max.
            if priority[r['config']]==priority.get(out[key]['config'],-1):
                r['Average']=out[key]['Average']
        out[key]=r
supplement=H/'supplemental_evidence/mmke-entity/llava-v1.5-7b/layer_09'
if supplement.exists():
    sm=load(supplement/'manifest.json');assert sm['checkpoint_exists']
    for x in sm['files']:assert hashlib.sha256((supplement/x['relative']).read_bytes()).hexdigest()==x['sha256']
    ev=load(supplement/'eval_full.done');detail=load(next(supplement.glob('eval_full/**/results.json')))
    saved_mean=load(next(supplement.glob('eval_full/**/mean_results.json')))
    assert ev['status']=='EVAL_DONE' and len(detail)==ev['eval_samples']==954
    history=rows(supplement/'loss_history.csv');assert max(int(x['epoch']) for x in history)==50
    selected=list(csv.DictReader(read(supplement/'selected_checkpoint.tsv').splitlines(),delimiter='\t'))[0]
    assert selected['checkpoint']==ev['checkpoint'] and int(selected['epoch'])==48
    acc={'Rel':mean(x['reliability']['acc'] for x in detail)}
    for metric,family,kind in [('T-Gen','generality','text_rephrase'),('M-Gen','generality','image_rephrase'),('T-Loc','locality','text_loc'),('M-Loc','locality','image_loc')]:
        assert all(len(x[family][kind])==1 for x in detail)
        acc[metric]=mean(x[family][kind][0]['acc'] for x in detail)
    for metric,value in acc.items():assert abs(round(value,4)*100-ev[metric])<1e-8,(metric,value,ev[metric])
    assert abs(mean(ev[m] for m in METRICS[:-1])-ev['Average'])<1e-9
    r=dict(dataset='mmke-entity',model='llava-v1.5-7b',layer=9,config='main',samples=954,status='EVAL_DONE_SERVER_VERIFIED_50_EPOCHS',source_line='',source=str(supplement/'eval_full.done'),**{m:ev[m] for m in METRICS})
    out[('mmke-entity','llava-v1.5-7b',9)]=r
    jwrite('supplemental_evaluation_verification.json',dict(dataset=r['dataset'],model=r['model'],layer=9,samples=954,training_epochs=50,selected_epoch=48,average=ev['Average'],metric_mean_from_sample_records=acc,files_sha256_verified=len(sm['files'])))
write('outcomes_main_used.csv',list(out.values()))
profiles={p:defaultdict(dict) for p in ['observed_main','clean']}
for key,r in out.items():
    if r['samples']!=EVAL[key[0]] or r['Average'] is None:continue
    assert 0<=r['Average']<=100
    profiles['observed_main'][key[:2]][key[2]]=r
    if r['config']=='main/recovered-early' or re.search('FAILED|NO_EVAL|NONCONVERGENT|DIAGNOSTIC|NUMERIC|NONFINITE|STALL',r['status'],re.I):continue
    profiles['clean'][key[:2]][key[2]]=r

metrics=[];mm={};pending=[];union=[]
for p,pool in profiles.items():
    for (g,f),cs in candidates.items():
        vals={l:r['Average'] for l,r in pool[g].items()};ref=max(vals.values()) if vals else None
        for k,cc in cs.items():
            missing=[l for l in cc if l not in vals];complete=len(cc)==k and not missing
            yy=[vals[l] for l in cc if l in vals]
            row=dict(profile=p,dataset=g[0],model=g[1],method=f,k=k,candidates=fmt(cc),coverage=coverage[g,f],complete=complete,missing_or_excluded=fmt(missing),observed_candidate_count=len(yy),best=max(yy) if complete else None,mean=mean(yy) if complete else None,observed_reference=ref,regret=ref-max(yy) if complete else None,hit=int(abs(max(yy)-ref)<1e-9) if complete else None)
            metrics.append(row);mm[p,g,f,k]=row
for a in audit:
    g=a['dataset'],a['model']
    for k in [3,5]:
        raw=candidates[g,RAW][k];tuk=candidates[g,TUKEY][k]
        old_union=sorted(set(l for f in SEVEN for l in candidates[g,RAW if f==TUKEY else f][k]))
        new_union=sorted(set(l for f in SEVEN for l in candidates[g,f][k]))
        for l in tuk:
            key=(*g,l);r=out.get(key);clean=mm['clean',g,TUKEY,k]
            status='main_evaluated' if r else 'stable_only' if key in stable else 'no_local_main_evaluation'
            if r and l not in profiles['clean'][g]:status='main_evaluated_with_training_flags'
            pending.append(dict(dataset=g[0],model=g[1],k=k,layer=l,new_vs_raw_topk=l not in raw,new_vs_old_seven_union=l not in old_union,status=status,average=r['Average'] if r else '',training_status=r['status'] if r else '',source=r['source'] if r else '',main_evaluation_available=bool(r)))
        missing=[l for l in new_union if l not in profiles['observed_main'][g]]
        union.append(dict(version=VERSION,dataset=g[0],model=g[1],k=k,old_union=fmt(old_union),new_union=fmt(new_union),added=fmt(sorted(set(new_union)-set(old_union))),removed=fmt(sorted(set(old_union)-set(new_union))),new_union_count=len(new_union),main_evaluated_count=len(new_union)-len(missing),pending_main=fmt(missing)))
write('method_metrics.csv',metrics);write('tukey_candidate_execution_status.csv',pending);write('corrected_seven_method_union.csv',union)

paired=[];summaries=[];fair=[];pairnames=[(TUKEY,RAW),(OURS,TUKEY),(OURS,RAW)]
for profile in profiles:
    for k in [1,3,5]:
        for policy in ['all_coverage','coverage_ge_80pct']:
            for scope in ['all']+DS:
                for fa,fb in pairnames:
                    zz=[]
                    for g in [(d,m) for d in DS for m in MODELS if scope=='all' or d==scope]:
                        a,b=mm[profile,g,fa,k],mm[profile,g,fb,k]
                        if not(a['complete'] and b['complete']):continue
                        if policy=='coverage_ge_80pct' and min(coverage[g,fa],coverage[g,fb])<.8:continue
                        rr=dict(profile=profile,coverage_policy=policy,scope=scope,k=k,dataset=g[0],model=g[1],method_a=fa,method_b=fb,a_candidates=a['candidates'],b_candidates=b['candidates'],a_best=a['best'],b_best=b['best'],a_mean=a['mean'],b_mean=b['mean'],delta_best=a['best']-b['best'],delta_mean=a['mean']-b['mean'],a_regret=a['regret'],b_regret=b['regret'],a_hit=a['hit'],b_hit=b['hit'])
                        zz.append(rr);paired.append(rr)
                    if zz:summaries.append(dict(profile=profile,coverage_policy=policy,scope=scope,k=k,method_a=fa,method_b=fb,n=len(zz),a_best=mean(r['a_best'] for r in zz),b_best=mean(r['b_best'] for r in zz),delta_best=mean(r['delta_best'] for r in zz),a_mean=mean(r['a_mean'] for r in zz),b_mean=mean(r['b_mean'] for r in zz),delta_mean=mean(r['delta_mean'] for r in zz),a_wins=sum(r['delta_best']>1e-9 for r in zz),ties=sum(abs(r['delta_best'])<=1e-9 for r in zz),a_losses=sum(r['delta_best']< -1e-9 for r in zz),a_regret=mean(r['a_regret'] for r in zz),b_regret=mean(r['b_regret'] for r in zz),a_hit=mean(r['a_hit'] for r in zz),b_hit=mean(r['b_hit'] for r in zz)))
        # Paired three-way cohort fixes membership before contrasting old/new conclusions.
        trio=[g for g in [(d,m) for d in DS for m in MODELS] if all(mm[profile,g,f,k]['complete'] for f in [RAW,TUKEY,OURS])]
        for label,fs in [('raw_tukey_ours_same_groups',[RAW,TUKEY,OURS]),('corrected_seven_plus_raw_same_groups',SEVEN+[RAW])]:
            gs=trio if len(fs)==3 else [g for g in [(d,m) for d in DS for m in MODELS] if all(mm[profile,g,f,k]['complete'] for f in fs)]
            if not gs:continue
            for f in fs:
                rr=[mm[profile,g,f,k] for g in gs]
                fair.append(dict(profile=profile,comparison=label,k=k,method=f,n=len(gs),best=mean(r['best'] for r in rr),mean=mean(r['mean'] for r in rr),regret=mean(r['regret'] for r in rr),hit=mean(r['hit'] for r in rr),groups=';'.join('/'.join(g) for g in gs)))
write('paired_comparisons.csv',paired);write('paired_summary.csv',summaries);write('same_cohort_method_summary.csv',fair)
summary=dict(version=VERSION,groups=len(audit),parameter_layers=len(layer_rows),excluded_layers=sum(a['excluded_count'] for a in audit),changed_top3=sum(a['top3_changed'] for a in audit),changed_top5=sum(a['top5_changed'] for a in audit),
    top3_missing_unique=len({(r['dataset'],r['model'],r['layer']) for r in pending if r['k']==3 and not r['main_evaluation_available']}),top5_missing_unique=len({(r['dataset'],r['model'],r['layer']) for r in pending if r['k']==5 and not r['main_evaluation_available']}),
    interpolation_top3_changed=sum(not r['top3_same_primary'] for r in qsens if r['quantile_method']=='midpoint'),interpolation_top5_changed=sum(not r['top5_same_primary'] for r in qsens if r['quantile_method']=='midpoint'),
    observed_main_outcomes=len(out),source_manifest_captured_utc=manifest['captured_utc'])
jwrite('calculation_summary.json',summary);jwrite('local_source_hashes.json',sources)
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('MAIN_TOP3_SUMMARIES',json.dumps([r for r in summaries if r['profile']=='observed_main' and r['scope']=='all' and r['coverage_policy']=='all_coverage' and r['k']==3],ensure_ascii=False))
print('MISSING_TOP3',json.dumps([r for r in pending if r['k']==3 and not r['main_evaluation_available']],ensure_ascii=False))
