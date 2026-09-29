"""Exploratory formula selection from fixed existing outcomes; no training changes."""
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean, median
from itertools import product
from datetime import datetime
import csv, json, math, hashlib, sys, warnings
import numpy as np
from scipy.stats import spearmanr

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
RAW = ROOT/'md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores'
OLD = ROOT/'md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731'
PREV = ROOT/'outputs/main_formula_validation_20260925'
MAIN, NORM = 'M_abscos_x_newn', 'M_new_norm'
sources = {}

def read(p):
    b=p.read_bytes(); sources[str(p)]=hashlib.sha256(b).hexdigest()
    return b.decode('utf-8-sig')
def rc(p): return list(csv.DictReader(read(p).splitlines()))
def wc(name, rows):
    if not rows: return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def ls(a): return ','.join('L'+str(x) for x in a)
def keystr(g): return '/'.join(g)

# This finite search space is fixed before calculating any new outcome statistics.
specs=[]
def add(name,expression,kind,complexity=1,**params):
    specs.append(dict(formula=name,expression=expression,kind=kind,complexity=complexity,**params))
for name,expr in [
 ('M_dot','dot'),('M_cos','cos'),('M_new_norm','new_norm'),
 ('M_pos_ratio','positive_ratio'),('M_conflict','-dot'),
 ('M_newn_x_1mcos','new_norm*(1-cos)'),('M_abscos_x_newn','new_norm*abs(cos)'),
 ('Ours-Direct-Conflict','new_norm*max(0,-cos)*depth^2'),
 ('Ours-AbsDirection-Direct','new_norm*abs(cos)*depth^2'),
 ('Ours-NoDirection-Direct','new_norm*depth^2'),
 ('Ours-1MinusCos-Direct','new_norm*(1-cos)*depth^2')]:
    add(name,expr,'historical11',0 if name==NORM else 1 if name==MAIN else 2)
for name,expr in [('abs_cos_only','abs(cos)'),('signed_cos_new_norm','new_norm*cos'),
                  ('negative_cos_new_norm','new_norm*max(0,-cos)'),('old_norm_only','old_norm')]:
    add(name,expr,'control',2)
for a,b,g in product([0,.25,.5,1,2],[-1,-.5,0,.5,1],[-1,0,.5,1,2]):
    add(f'power_a{a:g}_b{b:g}_g{g:g}',f'new_norm*abs(cos)^{a:g}*old_norm^{b:g}*depth^{g:g}',
        'power_grid',sum(x!=0 for x in [a,b,g])+abs(a)+abs(b)+abs(g),a=a,b=b,g=g)
for w in [.25,.5,1,2,4,8]:
    add(f'soft_direction_{w:g}',f'new_norm*(1+{w:g}*abs(cos))','soft_direction',2+w,w=w)
# Round 2 was motivated by round-1 ties/losses and is disclosed as adaptive exploration.
for w,t in product([.25,.5,1,2,4],[0,1,5]):
    add(f'rrf_w{w:g}_t{t:g}',f'1/({t}+rank_new)+{w}/({t}+rank_direction_new)',
        'rank_fusion',3+abs(math.log2(w))+t,w=w,t=t)
for w in [.5,.75,1,1.25,2]:
    add(f'rank_max_w{w:g}',f'max(1/rank_new,{w}/rank_direction_new)',
        'rank_max',3+abs(math.log2(w)),w=w)
for filename in ['search_protocol.json','discovery_summary.json']:
    existing=OUT/filename; archived=OUT/('round1_'+filename)
    if existing.exists() and not archived.exists(): archived.write_bytes(existing.read_bytes())
protocol=dict(created_at=datetime.now().astimezone().isoformat(),specs=specs,
    exploration_rounds='Round 1: 146 definitions. Round 2: 20 rank-fusion definitions after inspecting round-1 outcomes. This is not preregistration.',
    primary_metric='Best@3, equal weight per model-dataset combination',
    secondary_metrics=['Mean@3','strict wins/ties/losses','gains >= 0.5 percentage points','Top1','Spearman'],
    outcome_policy='Existing locked outcomes; clean primary; recorded historical sensitivity only; no training or checkpoint reselection',
    candidate_policy='Rank all valid gradient layers before matching outcomes; never rank only already-measured layers',
    cohort='Fixed intersection where current main and norm Top3 are complete; retain low-gradient-coverage group with separate sensitivity',
    selection='Only formulas fully observed on that entire fixed cohort may compete for its winner; missing results are not zeros',
    robustness='Leave-one-model-out and leave-one-dataset-out reselection, descriptive only: historic data already used for formula development')
(OUT/'search_protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')

groups={}; meta={}
for p in sorted(RAW.glob('*/*/ours_direct_layer_scores.csv')):
    group=tuple(p.parts[-3:-1]); rows=rc(p); n=int(float(rows[0]['n_request']))
    total={'evqa-pilot500':500,'mmke-visual':214,'mmke-entity':636}[group[0]]
    L=max(int(r['layer']) for r in rows)+1
    meta[group]=dict(coverage=n/total,valid_samples=n,total_samples=total)
    valid=[]
    for r in rows:
        if r['S_v_zero_grad'].lower()=='true' or r['invalid_reason'].strip(): continue
        if not r['visual_token_start'].strip() or not r['visual_token_end'].strip(): continue
        vals=[float(r[x]) for x in ['S_v_dot','S_v_cos','S_v_new_norm','S_v_old_norm','S_v_positive_ratio']]
        if not all(math.isfinite(x) for x in vals): continue
        valid.append(dict(layer=int(r['layer']),dot=vals[0],c=vals[1],n=vals[2],o=vals[3],p=vals[4],d=(int(r['layer'])+1)/L))
    groups[group]=valid
assert len(groups)==21

def value(s,r,group):
    c,n,o,d=r['c'],r['n'],r['o'],r['d']; name=s['formula']
    if s['kind'] in ['rank_fusion','rank_max']:
        rn=rankings[group,NORM].index(r['layer'])+1
        rm=rankings[group,MAIN].index(r['layer'])+1
        if s['kind']=='rank_max': return max(1/rn,s['w']/rm)
        return 1/(s['t']+rn)+s['w']/(s['t']+rm)
    if s['kind']=='power_grid':
        if o<=0 and s['b']<0: return None
        return n*abs(c)**s['a']*o**s['b']*d**s['g']
    if s['kind']=='soft_direction': return n*(1+s['w']*abs(c))
    return {'M_dot':r['dot'],'M_cos':c,'M_new_norm':n,'M_pos_ratio':r['p'],
       'M_conflict':-r['dot'],'M_newn_x_1mcos':n*(1-c),'M_abscos_x_newn':n*abs(c),
       'Ours-Direct-Conflict':n*max(0,-c)*d*d,'Ours-AbsDirection-Direct':n*abs(c)*d*d,
       'Ours-NoDirection-Direct':n*d*d,'Ours-1MinusCos-Direct':n*(1-c)*d*d,
       'abs_cos_only':abs(c),'signed_cos_new_norm':n*c,
       'negative_cos_new_norm':n*max(0,-c),'old_norm_only':o}[name]

rankings={}; scores={}; candidate_rows=[]
for s in specs:
    for group, rr in groups.items():
        pairs=[(r['layer'],value(s,r,group)) for r in rr]
        pairs=[(l,v) for l,v in pairs if v is not None and math.isfinite(v)]
        if s['formula'] in ['Ours-Direct-Conflict','negative_cos_new_norm']:
            pairs=[(l,v) for l,v in pairs if v>0]
        pairs.sort(key=lambda x:(-x[1],x[0]))
        rankings[group,s['formula']]=[l for l,v in pairs]
        scores[group,s['formula']]=dict(pairs)
        candidate_rows.append(dict(dataset=group[0],model=group[1],formula=s['formula'],
            expression=s['expression'],**meta[group],top1=ls([l for l,v in pairs][:1]),
            top3=ls([l for l,v in pairs][:3]),top5=ls([l for l,v in pairs][:5])))

# Validate against already audited rankings, independent of response values.
mapping={'main_abs_cos_new_norm':MAIN,'new_norm_only':NORM,'visual_lga_dot':'M_dot',
         'main_depth2':'Ours-AbsDirection-Direct','new_norm_depth2':'Ours-NoDirection-Direct',
         'one_minus_cos_new_norm':'M_newn_x_1mcos','abs_cos_only':'abs_cos_only',
         'signed_cos_new_norm':'signed_cos_new_norm','negative_cos_new_norm':'negative_cos_new_norm'}
checks=0
for r in rc(PREV/'candidate_topk.csv'):
    for k in [1,3,5]:
        assert r[f'top{k}']==ls(rankings[(r['dataset'],r['model']),mapping[r['method']]][:k]),r
        checks+=1

outcomes=rc(ROOT/'outputs/visual_lga_vs_main_20260925/verified_outcomes_with_flags.csv')
ymaps={}
for profile in ['clean','recorded']:
    for group in groups:
        rr=[r for r in outcomes if (r['dataset'],r['model'])==group and
            (not r['clean_exclusion'] if profile=='clean' else r['historical_exclusion'] in ['', 'stable_only'])]
        ymaps[profile,group]={int(r['layer']):float(r['average']) for r in rr}

# Read fixed formal baseline recommendations from the reconciled 168-row source.
names={'BLIP2-OPT-2.7B':'blip2-opt-2.7b','InstructBLIP-Vicuna-7B':'instructblip-vicuna-7b',
       'MiniGPT-4-Vicuna-7B':'minigpt-4-vicuna-7b','LLaVA-v1.5-7B':'llava-v1.5-7b',
       'Qwen2.5-VL-3B':'qwen2.5-vl-3b','PaliGemma-3B':'paligemma-3b','SmolVLM-Instruct-1.7B':'smolvlm-1.7b'}
heat=json.loads(read(ROOT/'outputs/formal8_union_heatmap_20260922/source_data.json'))
br=defaultdict(list)
for r in heat['records']:
    group=r['dataset'].lower(),names[r['model']]
    for name,rank in r['method_recommended_ranks'].items(): br[group,name].append((rank,int(r['layer'])))
assert len(br)==168
baselines=sorted({name for group,name in br if name!='Ours-Direct'})
for (group,name),rr in br.items():
    chosen=[l for rank,l in sorted(rr)]
    assert len(chosen)==3
    if name=='Ours-Direct': assert chosen==rankings[group,MAIN][:3]
    else: rankings[group,'baseline::'+name]=chosen

metric={}; metric_rows=[]; corr={}
all_names=[s['formula'] for s in specs]+['baseline::'+b for b in baselines]
for profile in ['clean','recorded']:
    for group in groups:
        y=ymaps[profile,group]; ref=max(y.values()) if y else None
        for name in all_names:
            chosen=rankings[group,name]
            for k in [1,3]:
                cc=chosen[:k]; missing=[l for l in cc if l not in y]
                complete=len(cc)==k and not missing
                vv=[y[l] for l in cc] if complete else []
                row=dict(profile=profile,dataset=group[0],model=group[1],formula=name,k=k,
                    candidates=ls(cc),complete=complete,missing_layers=ls(missing),coverage=meta[group]['coverage'],
                    best=max(vv) if vv else None,mean=mean(vv) if vv else None,
                    regret=ref-max(vv) if vv else None,hit=int(abs(ref-max(vv))<1e-9) if vv else None)
                metric[profile,group,name,k]=row; metric_rows.append(row)
            if (group,name) in scores:
                common=sorted(set(y)&set(scores[group,name])); rho=None
                if len(common)>=5:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        rho=float(spearmanr([scores[group,name][l] for l in common],[y[l] for l in common]).statistic)
                    if not math.isfinite(rho): rho=None
                corr[profile,group,name]=rho

def pair_summary(profile,name,base,k,cohort):
    gg=[g for g in cohort if metric[profile,g,name,k]['complete'] and metric[profile,g,base,k]['complete']]
    aa=[metric[profile,g,name,k] for g in gg]; bb=[metric[profile,g,base,k] for g in gg]
    dd=[a['best']-b['best'] for a,b in zip(aa,bb)]
    return dict(profile=profile,formula=name,baseline=base,k=k,n=len(gg),
        complete_on_entire_cohort=len(gg)==len(cohort),cohort_size=len(cohort),
        best=mean(a['best'] for a in aa) if aa else None,baseline_best=mean(b['best'] for b in bb) if bb else None,
        delta_best=mean(dd) if dd else None,mean=mean(a['mean'] for a in aa) if aa else None,
        delta_mean=mean(a['mean']-b['mean'] for a,b in zip(aa,bb)) if aa else None,
        wins=sum(d>1e-9 for d in dd),ties=sum(abs(d)<=1e-9 for d in dd),losses=sum(d< -1e-9 for d in dd),
        wins_ge_half=sum(d>=.5-1e-9 for d in dd),losses_ge_half=sum(d<=-.5+1e-9 for d in dd),
        median_delta=median(dd) if dd else None,worst_delta=min(dd) if dd else None,
        max_delta=max(dd) if dd else None,hit=mean(a['hit'] for a in aa) if aa else None,
        groups=';'.join(keystr(g) for g in gg))

cohorts={p:[g for g in groups if all(metric[p,g,n,3]['complete'] for n in [MAIN,NORM])] for p in ['clean','recorded']}
assert len(cohorts['clean'])==16 and len(cohorts['recorded'])==17
summaries=[]
all_pair_rows=[]
for p in cohorts:
    for s in specs:
        for base in [MAIN,NORM]:
            for k in [1,3]:
                summaries.append(pair_summary(p,s['formula'],base,k,cohorts[p]))
                all_pair_rows.append(pair_summary(p,s['formula'],base,k,list(groups)))

specmap={s['formula']:s for s in specs}
eligible={p:[s['formula'] for s in specs if all(metric[p,g,s['formula'],3]['complete'] for g in cohorts[p])] for p in cohorts}
def objective(p,name,gg,mode):
    ss=pair_summary(p,name,NORM,3,gg)
    score=(ss['best'],ss['mean']) if mode=='best' else (ss['wins']-ss['losses'],ss['best'],ss['mean'])
    return tuple(round(x,10) for x in score)+(-specmap[name]['complexity'],)

winners={}; cv=[]; folds=[]; common_rankings=[]
for p,gg in cohorts.items():
    winners[p]={}
    for mode in ['best','wins']:
        ordered=sorted(eligible[p],key=lambda n:objective(p,n,gg,mode),reverse=True)
        winners[p][mode]=ordered[0]
        if mode=='best':
            for rank,name in enumerate(ordered,1):
                common_rankings.append(dict(rank=rank,**pair_summary(p,name,NORM,3,gg)))
        for unit,idx in [('model',1),('dataset',0)]:
            for held in sorted({g[idx] for g in gg}):
                train=[g for g in gg if g[idx]!=held]; test=[g for g in gg if g[idx]==held]
                chosen=max(eligible[p],key=lambda n:objective(p,n,train,mode))
                folds.append(dict(profile=p,objective=mode,heldout_unit=unit,heldout=held,chosen=chosen,
                    expression=specmap[chosen]['expression'],train_n=len(train),test_n=len(test)))
                for g in test:
                    a=metric[p,g,chosen,3]; b=metric[p,g,NORM,3]; old=metric[p,g,MAIN,3]
                    cv.append(dict(profile=p,objective=mode,heldout_unit=unit,heldout=held,
                        dataset=g[0],model=g[1],chosen=chosen,top3=a['candidates'],best=a['best'],
                        norm_best=b['best'],main_best=old['best'],delta_norm=a['best']-b['best'],delta_main=a['best']-old['best']))

# Top-3 aliases are disclosed, not counted as independent discoveries.
aliases=defaultdict(list)
for s in specs:
    fingerprint=tuple(tuple(rankings[g,s['formula']][:3]) for g in sorted(groups))
    aliases[fingerprint].append(s['formula'])
alias_rows=[dict(alias_group=i,formulas=';'.join(nn),count=len(nn)) for i,nn in enumerate(aliases.values(),1)]

spotlight=list(dict.fromkeys([MAIN,NORM,'M_dot']+[n for ww in winners.values() for n in ww.values()]))
pair_baselines=[]; details=[]; sensitivity=[]; corr_rows=[]
for p in cohorts:
    for name in spotlight:
        for base in [MAIN,NORM]+['baseline::'+b for b in baselines]:
            if name==base: continue
            # All 21 groups are eligible here, but each row discloses its own paired N.
            pair_baselines.append(pair_summary(p,name,base,3,list(groups)))
        sub=[g for g in cohorts[p] if meta[g]['coverage']>=.8]
        sensitivity.append(pair_summary(p,name,NORM,3,sub))
        for g in groups:
            a=metric[p,g,name,3]; b=metric[p,g,NORM,3]
            details.append(dict(profile=p,dataset=g[0],model=g[1],formula=name,expression=specmap[name]['expression'],
                in_fixed_cohort=g in cohorts[p],coverage=meta[g]['coverage'],top3=a['candidates'],complete=a['complete'],
                missing_layers=a['missing_layers'],best=a['best'],mean=a['mean'],norm_top3=b['candidates'],norm_best=b['best'],
                delta_norm=a['best']-b['best'] if a['complete'] and b['complete'] else None))
    for s in specs:
        cc=[corr[p,g,s['formula']] for g in groups if corr[p,g,s['formula']] is not None]
        corr_rows.append(dict(profile=p,formula=s['formula'],n=len(cc),spearman=mean(cc) if cc else None,
                             median_spearman=median(cc) if cc else None,positive=sum(c>0 for c in cc)))

cv_summary=[]
for p,mode,unit in product(cohorts,['best','wins'],['model','dataset']):
    rr=[r for r in cv if (r['profile'],r['objective'],r['heldout_unit'])==(p,mode,unit)]
    dd=[r['delta_norm'] for r in rr]
    cv_summary.append(dict(profile=p,objective=mode,heldout_unit=unit,n=len(rr),
        best=mean(r['best'] for r in rr),norm_best=mean(r['norm_best'] for r in rr),delta_norm=mean(dd),
        wins=sum(x>1e-9 for x in dd),ties=sum(abs(x)<=1e-9 for x in dd),losses=sum(x< -1e-9 for x in dd),
        choices=json.dumps(dict(Counter(r['chosen'] for r in folds if (r['profile'],r['objective'],r['heldout_unit'])==(p,mode,unit))),ensure_ascii=False)))

# Audit whether a favorable Top3 depends on the shared lower-layer-index tie break.
tie_rows=[]
for p in cohorts:
    for name in spotlight:
        for g in groups:
            ss=scores[g,name]; order=rankings[g,name]
            if len(order)<3: continue
            cut=ss[order[2]]
            tied=[l for l,v in ss.items() if abs(v-cut)<=1e-12*max(1,abs(cut))]
            above=[l for l,v in ss.items() if v>cut+1e-12*max(1,abs(cut))]
            slots=3-len(above); y=ymaps[p,g]
            missing=[l for l in above+tied if l not in y]
            uncertain=len(tied)>slots
            worst=best=None
            if not missing and slots>0:
                yy=sorted(y[l] for l in tied); fixed=max([y[l] for l in above],default=-math.inf)
                worst=max(fixed,yy[slots-1]); best=max(fixed,yy[-1])
            desc=sorted(ss,key=lambda l:(-ss[l],-l))[:3]
            descbest=max(y[l] for l in desc) if all(l in y for l in desc) else None
            tie_rows.append(dict(profile=p,dataset=g[0],model=g[1],formula=name,
                in_fixed_cohort=g in cohorts[p],top3=ls(order[:3]),boundary_ambiguous=uncertain,
                boundary_tied_layers=ls(sorted(tied)),slots=slots,missing_tie_outcomes=ls(missing),
                worst_best3_over_ties=worst,best_best3_over_ties=best,
                reversed_index_top3=ls(desc),reversed_index_best3=descbest))

wc('candidate_topk.csv',candidate_rows); wc('all_formula_metrics.csv',metric_rows)
wc('paired_screening.csv',summaries); wc('fixed_cohort_ranking.csv',common_rankings)
wc('all_pairs_vs_anchors.csv',all_pair_rows)
wc('formula_aliases.csv',alias_rows); wc('winner_cases.csv',details)
wc('baseline_comparisons.csv',pair_baselines); wc('coverage80_sensitivity.csv',sensitivity)
wc('correlations.csv',corr_rows); wc('heldout_folds.csv',folds); wc('heldout_cases.csv',cv); wc('heldout_summary.csv',cv_summary)
wc('tie_boundary_audit.csv',tie_rows)
brief=dict(spec_count=len(specs),distinct_top3_patterns=len(aliases),ranking_crosschecks=checks,
    cohort_sizes={p:len(g) for p,g in cohorts.items()},eligible_counts={p:len(v) for p,v in eligible.items()},
    winners={p:{mode:dict(formula=n,expression=specmap[n]['expression'],
        versus_norm=pair_summary(p,n,NORM,3,cohorts[p]),versus_main=pair_summary(p,n,MAIN,3,cohorts[p]))
        for mode,n in ww.items()} for p,ww in winners.items()},heldout=cv_summary,sources=sources)
(OUT/'discovery_summary.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in brief.items() if k!='sources'},ensure_ascii=False,indent=2))
