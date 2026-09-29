"""Retrospective task/model heterogeneity analysis on frozen, evidence-backed inputs."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,io,math,re,hashlib,warnings
import numpy as np
from scipy.stats import spearmanr
H=Path(__file__).resolve().parent;I=H/'inputs';ROOT=H.parents[1]
DS=['evqa-pilot500','mmke-visual','mmke-entity']
MODELS=['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b','qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']
DISPLAY=['BLIP2-OPT-2.7B','InstructBLIP-Vicuna-7B','MiniGPT-4-Vicuna-7B','LLaVA-v1.5-7B','Qwen2.5-VL-3B','PaliGemma-3B','SmolVLM-Instruct-1.7B']
TOTAL=dict(zip(DS,[500,214,636]));EVAL=dict(zip(DS,[2093,293,954]))
METRICS=['Average','Rel','T-Gen','M-Gen','T-Loc','M-Loc']
CORE=['norm','abs_cos_norm','one_minus_cos_norm']
EXPANDED=CORE+['signed_cos_norm','cos','dot','depth2_norm']
ALL=EXPANDED+['negative_cos_norm']
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def readcsv(p):return list(csv.DictReader(Path(p).read_text(encoding='utf-8-sig').splitlines()))
def write(name,rows):
    if not rows:return
    with (H/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def corr(a,b):
    if len(a)<5 or len(set(a))<2 or len(set(b))<2:return None
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');r=float(spearmanr(a,b).statistic)
    return r if math.isfinite(r) else None
def normtext(x):return ' '.join(re.findall(r'\w+',str(x).casefold()))
def overlap(a,b):
    a=Counter(normtext(a).split());b=Counter(normtext(b).split())
    return 2*sum((a&b).values())/(sum(a.values())+sum(b.values())) if a and b else 0
def mean(x):return float(np.mean(list(x)))

datasets={d:load(I/(d+'_data.json'))['records'] for d in DS}
dataset_summary=[]
for d,rr in datasets.items():
    words=[len(normtext(r['alt']).split()) for r in rr]
    dataset_summary.append(dict(dataset=d,n=len(rr),median_target_words=float(np.median(words)),
        mean_target_words=mean(words),target_words_min=min(words),target_words_max=max(words),
        blank_dataset_old=sum(not r.get('pred','').strip() for r in rr),
        dataset_old_exact_new=sum(r.get('pred','').strip()==r['alt'].strip() for r in rr),
        subtype_counts=json.dumps(dict(Counter(r.get('_type_self','unspecified') for r in rr)),ensure_ascii=False)))
write('dataset_semantics_summary.csv',dataset_summary)

layers=[];summaries=[];sample_rows=[];examples=[];sources={};groups={};stats={};sensitivity=[]
for d in DS:
    for model in MODELS:
        g=(d,model);z=load(I/(d+'__'+model+'.json'))
        assert z['duplicates']==0 and z['answer_mismatch_across_layers']==0 and z['identical_sample_ids_all_layers']
        assert not any('cos' in k or 'norm' in k or 'dot' in k for k in z['sample_schema'])
        rr=list(csv.DictReader(io.StringIO(z['files']['ours_direct_layer_scores.csv']['text'])))
        saved=readcsv(ROOT/'md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores'/d/model/'ours_direct_layer_scores.csv')
        assert len(rr)==len(saved)
        for a,b in zip(rr,saved):
            assert a['layer']==b['layer'] and a['n_request']==b['n_request']
            for key in ['S_v_cos','S_v_dot','S_v_old_norm','S_v_new_norm','S_v_positive_ratio']:
                av,bv=float(a[key]),float(b[key]);assert av==bv or (math.isnan(av) and math.isnan(bv))
        valid=[];num_layers=max(int(r['layer']) for r in rr)+1
        for r in rr:
            l=int(r['layer']);n=int(r['n_request']);c=float(r['S_v_cos']);p=float(r['S_v_positive_ratio']);new=float(r['S_v_new_norm']);old=float(r['S_v_old_norm'])
            ok=(r['S_v_zero_grad'].lower()!='true' and not r.get('invalid_reason','') and all(math.isfinite(x) for x in [c,p,new,old]))
            row=dict(dataset=d,model=model,layer=l,depth=(l+1)/num_layers,valid=ok,n=n,coverage=n/TOTAL[d],
                     mean_cos=c,positive_fraction=p,nonpositive_fraction=1-p,new_norm=new,old_norm=old,
                     dot=float(r['S_v_dot']),median_dot=float(r['median_v_dot']),
                     mean_old_answer_loss_positions=float(r['answer_loss_position_count_mean']),
                     visual_tokens=str(r['visual_token_start'])+':'+str(r['visual_token_end']),invalid_reason=r.get('invalid_reason',''))
            layers.append(row)
            if ok:valid.append(row)
        valid.sort(key=lambda r:r['layer'])
        groups[g]=valid
        ss=[]
        for r in z['samples']:
            raw=datasets[d][r['sample_i']];assert str(raw['alt'])==str(r['target_new'])
            old,new=str(r['old_answer']),str(r['target_new'])
            sr=dict(dataset=d,model=model,sample_i=r['sample_i'],sample_id=r['sample_id'],
                    exact_old_new=old.strip()==new.strip(),normalized_old_new=normtext(old)==normtext(new),
                    lexical_f1=overlap(old,new),old_words=len(normtext(old).split()),new_words=len(normtext(new).split()),
                    old_loss=r['old_loss'],new_loss=r['new_loss'],category=raw.get('_type_self','unspecified'),
                    prompt=raw['src'],old_answer=old,target_new=new,dataset_old=raw.get('pred',''))
            ss.append(sr);sample_rows.append(sr)
        n=len(ss);cs=[r['mean_cos'] for r in valid];ps=[r['positive_fraction'] for r in valid]
        same=sum(r['exact_old_new'] for r in ss)/n
        # Exact identical target sequences contribute cos>=0 and ideally cos=1 when nonzero.
        # Removing at most +1 per identical example gives a conservative lower bound on
        # mean cosine among unequal strings; this is not a recomputed subgroup estimate.
        lower=[(c-same)/(1-same) if same<1 else float('nan') for c in cs]
        nonident_pos_lb=[max(0.,(p-same)/(1-same)) if same<1 else float('nan') for p in ps]
        sr=dict(dataset=d,model=model,total=TOTAL[d],valid_samples=n,coverage=n/TOTAL[d],valid_layers=len(valid),
                invalid_layers=','.join('L'+str(r['layer']) for r in layers if (r['dataset'],r['model'])==g and not r['valid']),
                negative_mean_layers=sum(c<0 for c in cs),positive_mean_layers=sum(c>0 for c in cs),
                mean_cos=mean(cs),min_cos=min(cs),max_cos=max(cs),mean_positive_fraction=mean(ps),min_positive_fraction=min(ps),
                exact_old_new_count=sum(r['exact_old_new'] for r in ss),exact_old_new_fraction=same,
                normalized_old_new_fraction=mean(r['normalized_old_new'] for r in ss),
                mean_lexical_f1=mean(r['lexical_f1'] for r in ss),mean_old_words=mean(r['old_words'] for r in ss),
                mean_new_words=mean(r['new_words'] for r in ss),mean_old_loss=mean(r['old_loss'] for r in ss),mean_new_loss=mean(r['new_loss'] for r in ss),
                unequal_string_cos_lower_bound=mean(lower),unequal_string_positive_fraction_lower_bound=mean(nonident_pos_lb),
                sign_changes=sum(cs[i]*cs[i-1]<0 for i in range(1,len(cs))))
        for name,a,b in [('early',0,1/3),('middle',1/3,2/3),('late',2/3,1.01)]:
            sr[name+'_cos']=mean(r['mean_cos'] for r in valid if a<r['depth']<=b)
        summaries.append(sr);stats[g]=sr
        examples.extend([dict(selection='fixed_first_valid_sample',**ss[0])])
        sources[d+'__'+model]=dict(source_root=z['source_root'],sample_source_sha256=z['sample_source_sha256'],layer_csv_sha256=z['files']['ours_direct_layer_scores.csv']['sha256'])
write('layer_direction.csv',layers);write('group_direction_summary.csv',summaries);write('sample_target_audit.csv',sample_rows)
(H/'fixed_examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2),encoding='utf-8')

# Balanced two-way decomposition of 21 group mean cosines: descriptive, not causal ANOVA.
A=np.array([[stats[d,m]['mean_cos'] for m in MODELS] for d in DS]);grand=A.mean()
ss_total=((A-grand)**2).sum();ss_d=7*((A.mean(axis=1)-grand)**2).sum();ss_m=3*((A.mean(axis=0)-grand)**2).sum()
decomp=dict(total_ss=float(ss_total),dataset_share=float(ss_d/ss_total),model_share=float(ss_m/ss_total),
            interaction_residual_share=float((ss_total-ss_d-ss_m)/ss_total),interpretation='descriptive variance of 21 equally weighted group means; no causal attribution')

# Parse exact frozen ledger metrics; no source ledger edits.
parsed=[];active=False;ds=model=None
for lineno,line in enumerate((I/'outcome_ledger_snapshot.md').read_text(encoding='utf-8').splitlines(),1):
    if line.startswith('## 4. '):active=True
    elif active and line.startswith('## '):break
    if not active:continue
    if line.startswith('### 4.'):ds=line.split(' ',2)[2].lower()
    elif line.startswith('#### '):model=dict(zip(DISPLAY,MODELS))[line[5:]]
    elif line.startswith('| L'):
        c=[v.strip() for v in line.strip().strip('|').split('|')];assert len(c)==14
        mat=re.fullmatch(r'L(\d+)(-\d+)?',c[0]);assert mat
        if mat[2] or c[12] in ['','-','—'] or c[1]=='stable':continue
        r=dict(dataset=ds,model=model,layer=int(mat[1]),config=c[1],samples=int(c[6]),status=c[13],source_line=lineno,
               **dict(zip(['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average'],map(float,c[7:13]))))
        if r['samples']!=EVAL[ds]:continue
        parsed.append(r)
priority={'main':3,'main/legacy':2,'main/recovered-early':1}
out={}
for r in parsed:
    key=r['dataset'],r['model'],r['layer']
    if key not in out or priority.get(r['config'],-1)>priority.get(out[key]['config'],-1):out[key]=r
prev=readcsv(I/'previous_outcomes.csv');prevc={(r['dataset'],r['model'],int(r['layer'])):r for r in prev}
for key,r in prevc.items():
    if r['config']=='stable' or int(r['eval_samples'])!=EVAL[r['dataset']]:continue
    if key not in out:
        rr=dict(dataset=r['dataset'],model=r['model'],layer=int(r['layer']),config=r['config'],samples=int(r['eval_samples']),status=r['status'],source_line='',
                **{m:None for m in METRICS});rr['Average']=float(r['average'])
        src=Path(r['source'])
        if src.exists() and src.suffix=='.json':
            for x in load(src).get('layers',[]):
                if (x.get('dataset','').lower(),x.get('model'),int(x.get('layer',-1)))==key:
                    e=x.get('evaluation') or {}
                    if e.get('status')=='EVAL_DONE':
                        for m in METRICS:rr[m]=float(e[m])
        out[key]=rr
for r in readcsv(I/'pali_main_stable_snapshot.csv'):
    if r['recipe']!='main':continue
    key='mmke-visual','paligemma-3b',int(r['layer'])
    out[key]=dict(dataset=key[0],model=key[1],layer=key[2],config='main',samples=293,status=r['status'],source_line='',
                 **{m:float(r[m]) for m in METRICS})
write('observed_main_outcomes.csv',list(out.values()))

profiles={p:defaultdict(dict) for p in ['observed_main','frozen_clean']}
for key,r in out.items():
    profiles['observed_main'][key[:2]][key[2]]=r
    if key in prevc and not prevc[key]['clean_exclusion'] and prevc[key]['config']!='stable':
        # Preserve the earlier frozen clean numerical values for the sensitivity panel.
        q=dict(r);q['Average']=float(prevc[key]['average']);profiles['frozen_clean'][key[:2]][key[2]]=q

scores={};rankings={};tops=[]
for g,rr in groups.items():
    for f in ALL:
        values={}
        for r in rr:
            n,c,d=r['new_norm'],r['mean_cos'],r['depth']
            value={'norm':n,'abs_cos_norm':abs(c)*n,'one_minus_cos_norm':(1-c)*n,
                   'signed_cos_norm':c*n,'cos':c,'dot':r['dot'],'depth2_norm':n*d*d,'negative_cos_norm':max(0,-c)*n}[f]
            values[r['layer']]=value
        scores[g,f]=values
        ranking=sorted([l for l,v in values.items() if f!='negative_cos_norm' or v>0],key=lambda l:(-values[l],l))
        rankings[g,f]=ranking
        tops.append(dict(dataset=g[0],model=g[1],formula=f,top1=','.join(map(str,ranking[:1])),top3=','.join(map(str,ranking[:3])),qualifying_layers=len(ranking)))
write('candidate_topk.csv',tops)
correlations=[];mr=[];mm={}
for profile,bygroup in profiles.items():
    for g,rr in groups.items():
        yy=bygroup[g]
        for f in ALL:
            for metric in METRICS:
                common=[l for l in scores[g,f] if l in yy and yy[l][metric] is not None]
                correlations.append(dict(profile=profile,dataset=g[0],model=g[1],formula=f,metric=metric,n_layers=len(common),coverage=stats[g]['coverage'],
                    spearman=corr([scores[g,f][l] for l in common],[yy[l][metric] for l in common])))
            for k in [1,3]:
                cc=rankings[g,f][:k];missing=[l for l in cc if l not in yy];complete=len(cc)==k and not missing
                row=dict(profile=profile,dataset=g[0],model=g[1],formula=f,k=k,coverage=stats[g]['coverage'],complete=complete,
                    candidates=','.join(map(str,cc)),missing=','.join(map(str,missing)),n_measured=len(yy))
                for metric in METRICS:
                    vv=[yy[l][metric] for l in cc] if complete else []
                    row[metric+'_best']=max(vv) if vv and all(v is not None for v in vv) else None
                    row[metric+'_mean']=mean(vv) if vv and all(v is not None for v in vv) else None
                # Per-metric best may refer to different layers; never present as one checkpoint.
                best_layer=max(cc,key=lambda l:yy[l]['Average']) if complete else None
                row['best_average_layer']=best_layer
                for metric in METRICS:row['at_best_average_'+metric]=yy[best_layer][metric] if complete else None
                mr.append(row);mm[profile,g,f,k]=row
write('layerwise_correlations.csv',correlations);write('formula_metrics.csv',mr)

paired=[];agg=[]
for p in profiles:
    for d in DS+['ALL']:
        for k in [1,3]:
            cohort=[g for g in groups if (d=='ALL' or g[0]==d) and stats[g]['coverage']>=.8 and all(mm[p,g,f,k]['complete'] for f in CORE)]
            for f in ALL:
                # Core comparisons share exactly the same cohort; noncore report availability.
                gg=[g for g in cohort if mm[p,g,f,k]['complete']]
                if not gg:continue
                for metric in ['Average_best','Average_mean','Rel_mean','M-Gen_mean','M-Loc_mean']:
                    a=[mm[p,g,f,k][metric] for g in gg];b=[mm[p,g,'norm',k][metric] for g in gg]
                    if any(v is None for v in a+b):continue
                    delta=np.array(a)-np.array(b)
                    agg.append(dict(profile=p,dataset=d,k=k,formula=f,metric=metric,n=len(gg),fixed_core_n=len(cohort),
                        mean=mean(a),norm_mean=mean(b),delta=mean(delta),wins=int(sum(delta>1e-8)),ties=int(sum(abs(delta)<=1e-8)),losses=int(sum(delta< -1e-8)),
                        min_delta=float(min(delta)),max_delta=float(max(delta)),groups=';'.join(g[1] for g in gg)))
                if d!='ALL':
                    for g in gg:
                        a=mm[p,g,f,k];b=mm[p,g,'norm',k]
                        paired.append(dict(profile=p,dataset=g[0],model=g[1],k=k,formula=f,same_set=set(rankings[g,f][:k])==set(rankings[g,'norm'][:k]),
                            delta_best=a['Average_best']-b['Average_best'],delta_mean=a['Average_mean']-b['Average_mean'],formula_candidates=a['candidates'],norm_candidates=b['candidates']))
write('dataset_formula_summary.csv',agg);write('paired_by_group.csv',paired)

# Leave-one-model-out: exclude all three datasets of the held model from learning.
cv=[];cvsummary=[]
for p in profiles:
    for family,ff in [('core3',CORE),('expanded7',EXPANDED)]:
        for k in [1,3]:
            cohort=[g for g in groups if stats[g]['coverage']>=.8 and all(mm[p,g,f,k]['complete'] for f in ff)]
            for objective in (['Average_best'] if k==1 else ['Average_best','Average_mean']):
                def choose(gg):
                    # Tie preference is norm, then simpler earlier formula; no held-out outcomes.
                    return max(ff,key=lambda f:(round(mean(mm[p,g,f,k][objective] for g in gg),9),-ff.index(f)))
                local=[]
                for g in cohort:
                    global_train=[x for x in cohort if x[1]!=g[1]]
                    task_train=[x for x in global_train if x[0]==g[0]]
                    if len(task_train)<3:continue
                    a,b=choose(global_train),choose(task_train)
                    ar,br,nr=[mm[p,g,f,k] for f in [a,b,'norm']]
                    r=dict(profile=p,family=family,k=k,objective=objective,dataset=g[0],model=g[1],
                        n_global_train=len(global_train),n_task_train=len(task_train),unified_formula=a,task_formula=b,
                        unified_score=ar[objective],task_score=br[objective],norm_score=nr[objective],
                        task_minus_unified=br[objective]-ar[objective],task_minus_norm=br[objective]-nr[objective])
                    cv.append(r);local.append(r)
                for d in DS+['ALL']:
                    rr=[r for r in local if d=='ALL' or r['dataset']==d]
                    if not rr:continue
                    dd=[r['task_minus_unified'] for r in rr]
                    # Cluster bootstrap by model because each model contributes multiple tasks.
                    rng=np.random.default_rng(20260926);models=sorted({r['model'] for r in rr});boot=[]
                    for _ in range(2000):
                        draw=rng.choice(models,len(models));vals=[r['task_minus_unified'] for m in draw for r in rr if r['model']==m]
                        boot.append(mean(vals))
                    cvsummary.append(dict(profile=p,family=family,k=k,objective=objective,dataset=d,n=len(rr),models=len(models),
                        delta_task_unified=mean(dd),delta_task_norm=mean(r['task_minus_norm'] for r in rr),
                        ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),
                        wins=sum(x>1e-8 for x in dd),ties=sum(abs(x)<=1e-8 for x in dd),losses=sum(x< -1e-8 for x in dd),
                        task_selections=json.dumps(dict(Counter(r['task_formula'] for r in rr)))))
write('leave_model_out_cases.csv',cv);write('leave_model_out_summary.csv',cvsummary)

summary=dict(group_count=len(groups),valid_layer_count=sum(len(x) for x in groups.values()),
    negative_mean_layer_count=sum(r['valid'] and r['mean_cos']<0 for r in layers),
    missing_per_sample_direction=True,source_csv_matches_local_archive=True,variance_decomposition=decomp,
    dataset_summaries=dataset_summary,group_summaries=summaries,
    cv_core_observed=[r for r in cvsummary if r['family']=='core3' and r['profile']=='observed_main'],
    outcome_group_counts={p:{d:sum(len(bygroup[g]) for g in groups if g[0]==d) for d in DS} for p,bygroup in profiles.items()},
    source_hashes=sources)
(H/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(variance=decomp,datasets=dataset_summary,core_cv=summary['cv_core_observed']),ensure_ascii=False,indent=2))
