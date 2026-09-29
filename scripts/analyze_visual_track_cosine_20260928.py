"""Rank representation cosine and compare only matched dataset/model sweeps.

May run before GPU completion: formal missing scores remain explicitly pending.
Bridge pilot curves are never relabeled as EVQA/MMKE localization scores.
"""
import collections
import csv
import hashlib
import json
import math
import statistics as st
import sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/visual_track_cosine_20260928'
OUT.mkdir(exist_ok=True)
SRC=ROOT/'outputs/all_methods_recommendations_20260928'
DATASETS={'evqa-pilot500':500,'mmke-visual':214,'mmke-entity':636}
MODELS=['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b','qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']
METRICS=['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def csvwrite(name,rows):
    if not rows:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def rank(values,flavor):
    assert values and all(math.isfinite(x) for x in values.values())
    q1,q3=[float(x) for x in np.quantile(list(values.values()),[.25,.75],method='linear')]
    low,high=q1-(q3-q1),q3+(q3-q1)
    excluded=sorted(l for l,x in values.items() if flavor=='tukey' and (x<low or x>high))
    ranked=sorted((l for l in values if l not in excluded),key=lambda l:(-values[l],l))
    return dict(top1=ranked[:1],top3=ranked[:3],top5=ranked[:5],all_ranking=ranked,outlier_layers=excluded,q1=q1,q3=q3,lower=low,upper=high)
def rho(x,y):
    def ranks(a):return [1+sum(v<t for v in a)+(sum(v==t for v in a)-1)/2 for t in a]
    a,b=ranks(x),ranks(y);ma,mb=st.mean(a),st.mean(b)
    den=math.sqrt(sum((t-ma)**2 for t in a)*sum((t-mb)**2 for t in b))
    return sum((s-ma)*(t-mb) for s,t in zip(a,b))/den if den else None
def ls(x):return ', '.join('L'+str(l) for l in x) or '—'
def f(x):return '—' if x is None else '%.3f'%x
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(str(x).replace('|','\\|') for x in r)+' |\n' for r in rows)+'\n'

legacy=[]
for name,model in [('bridge_attr_localize_pred_pilot4_v2','llava-v1.5-7b'),('bridge_attr_localize_train30','llava-v1.5-7b'),('bridge_attr_localize_blip2_pilot4','blip2-opt-2.7b')]:
    p=ROOT/'server_results'/name
    rr=rcsv(p/'layer_metrics.csv')
    records=[load(s) for s in sorted((p/'samples').glob('*.json'))]
    sample_n=load(p/'summary.json')['sample_count']
    assert len(records)==sample_n
    values={int(r['layer']):float(r['visual_track_cos']) for r in rr}
    for l,score in values.items():
        original=[next(v['visual_track_cos'] for v in r['layers'] if v['layer']==l) for r in records]
        assert abs(st.mean(original)-score)<1e-12
    low,high=min(values.values()),max(values.values())
    normalized={l:(x-low)/(high-low) for l,x in values.items()}
    for flavor in ['raw','tukey']:
        ranked=rank(values,flavor)
        normalized_ranking=rank(normalized,flavor)
        assert ranked['all_ranking']==normalized_ranking['all_ranking']
        legacy.append(dict(source=name,dataset='bridge_train30_pilot'+str(sample_n),model=model,samples=sample_n,flavor=flavor,**ranked,source_sha256=hashlib.sha256((p/'layer_metrics.csv').read_bytes()).hexdigest()))
csvwrite('bridge_candidates.csv',legacy)

ledger_path=ROOT/'outputs/sweep_ledger_20260928_110311/ledger.json'
inputs=OUT/'inputs';inputs.mkdir(exist_ok=True)
for src,name in [(ledger_path,'ledger.json'),(SRC/'recommendations.json','recommendations.json')]:
    if not (inputs/name).exists():(inputs/name).write_bytes(src.read_bytes())
all_old=load(inputs/'recommendations.json')['records']
old={(r['dataset'],r['model'],r['method'],r['flavor']):r for r in all_old}
ledger=load(inputs/'ledger.json')
pool=collections.defaultdict(dict)
for r in ledger['rows']:
    if r['recipe']=='main':pool[r['dataset'],r['model']][r['layer']]=r
protocol_variants=[('matched_gradient','visual_track_cos','VisualTrack-Cos-matched'),('all_train','visual_track_cos','VisualTrack-Cos-all'),('matched_gradient','visual_track_cos_fp32','VisualTrack-Cos-matched-fp32')]
recommendations=[];scores={};source_status=[]
for ds in DATASETS:
    for model in MODELS:
        folder=OUT/'results'/ds/model
        if not (folder/'summary.json').exists():
            source_status.append(dict(dataset=ds,model=model,status='pending_forward_statistics'));continue
        s=load(folder/'summary.json');pr=load(folder/'protocol.json');data=load(folder/'layer_scores.json')
        assert s['status']=='done' and s['sample_count']==DATASETS[ds]
        assert hashlib.sha256((folder/'layer_scores.json').read_bytes()).hexdigest()==s['scores_sha256']
        assert hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()==s['protocol_sha256']
        assert s['matched_sample_count']==old[ds,model,'Ours-main','raw']['sample_count']
        source_status.append(dict(dataset=ds,model=model,status='done',n=s['sample_count'],matched_n=s['matched_sample_count']))
        for cohort,metric,method in protocol_variants:
            rows=[r for r in data['rows'] if r['cohort']==cohort]
            values={r['layer']:r[metric] for r in rows}
            assert len(values)==old[ds,model,'Ours-main','raw']['total_layers']
            scores[ds,model,method]=values
            for flavor in ['raw','tukey']:
                recommendations.append(dict(dataset=ds,model=model,method=method,flavor=flavor,cohort=cohort,score_field=metric,n=rows[0]['n'],coverage=rows[0]['n']/DATASETS[ds],**rank(values,flavor)))
csvwrite('recommendations.csv',recommendations);save('recommendations.json',recommendations);csvwrite('formal_source_status.csv',source_status)

measurements=[];correlations=[];comparisons=[]
for r in recommendations:
    ds,model=r['dataset'],r['model'];pp=pool[ds,model]
    for k in [1,3,5]:
        cand=r['all_ranking'][:k];missing=[l for l in cand if l not in pp]
        complete=len(cand)==k and not missing
        x=dict(dataset=ds,model=model,method=r['method'],flavor=r['flavor'],k=k,coverage=r['coverage'],candidates=cand,missing_layers=missing,status='complete' if complete else 'missing_evaluations',top1=pp[cand[0]]['metrics']['Average'] if cand and cand[0] in pp else None,best=max(pp[l]['metrics']['Average'] for l in cand) if complete else None,mean=st.mean(pp[l]['metrics']['Average'] for l in cand) if complete else None)
        measurements.append(x)
        for baseline in ['Ours-no-direction','Ours-main','Ours-signed-direction','LGA-Visual','LGA-Param']:
            for bf in ['raw','tukey']:
                br=old[ds,model,baseline,bf];bc=br['all_ranking'][:k]
                if complete and len(bc)==k and all(l in pp for l in bc):
                    y=dict(dataset=ds,model=model,method=r['method'],flavor=r['flavor'],k=k,baseline=baseline,baseline_flavor=bf,coverage=min(r['coverage'],br['sample_count']/DATASETS[ds]),green_top1=x['top1'],baseline_top1=pp[bc[0]]['metrics']['Average'],green_best=x['best'],baseline_best=max(pp[l]['metrics']['Average'] for l in bc),green_mean=x['mean'],baseline_mean=st.mean(pp[l]['metrics']['Average'] for l in bc),same_candidate_set=set(cand)==set(bc))
                    for m in ['top1','best','mean']:y['delta_'+m]=y['green_'+m]-y['baseline_'+m]
                    comparisons.append(y)
    layers=[l for l in r['all_ranking'] if l in pp]
    for metric in METRICS:
        value=rho([scores[ds,model,r['method']][l] for l in layers],[pp[l]['metrics'][metric] for l in layers]) if len(layers)>=5 else None
        correlations.append(dict(dataset=ds,model=model,method=r['method'],flavor=r['flavor'],metric=metric,n_layers=len(layers),coverage=r['coverage'],rho=value,layers=layers))
csvwrite('performance.csv',measurements);csvwrite('pairwise_by_combination.csv',comparisons);csvwrite('correlations.csv',correlations)
summary=[]
for method in [v[2] for v in protocol_variants]:
    for flavor in ['raw','tukey']:
        for baseline,bf in [('Ours-no-direction','raw'),('Ours-no-direction','tukey'),('Ours-main','raw'),('Ours-main','tukey')]:
            rr=[r for r in comparisons if r['method']==method and r['flavor']==flavor and r['baseline']==baseline and r['baseline_flavor']==bf and r['k']==3 and r['coverage']>=.8]
            x=dict(method=method,flavor=flavor,baseline=baseline,baseline_flavor=bf,n=len(rr),groups=[[r['dataset'],r['model']] for r in rr])
            for m in ['top1','best','mean']:
                x['green_'+m]=st.mean(r['green_'+m] for r in rr) if rr else None
                x['baseline_'+m]=st.mean(r['baseline_'+m] for r in rr) if rr else None
                x['delta_'+m]=st.mean(r['delta_'+m] for r in rr) if rr else None
                x['wins_'+m]=sum(r['delta_'+m]>1e-9 for r in rr);x['ties_'+m]=sum(abs(r['delta_'+m])<=1e-9 for r in rr);x['losses_'+m]=sum(r['delta_'+m]<-1e-9 for r in rr)
            summary.append(x)
csvwrite('paired_summary.csv',summary)

done=sum(r['status']=='done' for r in source_status)
report='# 绿色曲线：视觉表征与首答案预测位置的余弦相似度\n\n'
if (ROOT/'md/Location/VisualTrack_Three_Variants_20260928.md').exists():
    report+='**2026-09-28 更新：**补算已扩展为 none、alt、model_pred 三版本，完整答案预测位置均值与固定前缀处理见[三版本方案及执行状态](VisualTrack_Three_Variants_20260928.md)。下文桥梁排名仍为原始不带答案版本的复算记录；最新正式补算状态以三版本报告为准。\n\n'
report+='公式：`S_l = mean_i cos(mean_visual_tokens(h_i,l), h_i,l[last_prompt_position])`。图像与提示词前向输入，不输入 alt 或 model_pred 答案；因此这条曲线不区分新目标与旧目标。测量位置为解码层输出，与现有 adapter 候选接口逐层对应。\n\n'
report+='截图已定位到 LLaVA 桥梁 4 样本归档；L20 的归一化值为 0.679654，与截图吻合。图中 min-max 归一化不改变降序排名，正仿射变换也不改变此处 Tukey 保留集合。本次直接使用原始余弦，不根据曲线形状挑区段。\n\n'
report+='## 已有桥梁曲线的实际候选\n\n'
report+=table(['模型','桥梁样本数','过滤','Top-3','Top-5','剔除层'],[[r['model'],r['samples'],r['flavor'],ls(r['top3']),ls(r['top5']),ls(r['outlier_layers'])] for r in legacy])
report+='这些是桥梁样本上的定位结果。不能配上 E-VQA/MMKE 的层成绩，冒充同任务推荐性能；当前正式扫层台账也不包含桥梁任务，故不填造它的 Best@3。\n\n'
report+='## 正式数据补算与比较\n\n'
report+=f'当前完成 **{done}/21** 个正式数据集×模型组合。缺失前向统计的组合在 formal_source_status.csv 标为 pending，不给零分。已测编辑成绩沿用 '+ledger['updated_at']+' 的 main 配置快照；缺候选层评测就不计算完整 Best/Mean@3。\n\n'
report+='主比较使用 matched_gradient，即与原视觉梯度方法完全相同的样本 ID；all_train 单列，避免把覆盖率变化混成公式改进。native 精度复现原图的计算定义，另保存 float32 重算作数值敏感性检查。Raw 保留全部有限层；Tukey 在全层分数上用 κ=1、linear 四分位数一次过滤，再降序推荐，同分取浅层。没有按编辑结果修改排序、翻转符号或删除末层。\n\n'
if done:
    rr=[r for r in summary if r['method']=='VisualTrack-Cos-matched']
    report+=table(['绿线过滤','参照','共同组数','绿线Top-1','参照Top-1','绿线Best@3','参照Best@3','绿线Mean@3','参照Mean@3','Best胜/平/负'],[[r['flavor'],r['baseline']+'/'+r['baseline_flavor'],r['n'],f(r['green_top1']),f(r['baseline_top1']),f(r['green_best']),f(r['baseline_best']),f(r['green_mean']),f(r['baseline_mean']),f"{r['wins_best']}/{r['ties_best']}/{r['losses_best']}"] for r in rr])
    report+='表中每一行只使用双方 Top-3 都完整且定位覆盖率均≥80%的同一批组合；不同的行可能包含不同组合。逐组合推荐与 Rel/T-Gen/M-Gen/T-Loc/M-Loc/Average 相关性另存 CSV。\n\n'
else:report+='**尚无正式三数据集的绿线分数，当前不能判断它是否优于新梯度范数。桥梁曲线的峰值高低不是编辑性能的证据。**\n\n'
if (OUT/'status.json').exists():
    state=load(OUT/'status.json')
    report+='最近调度状态：`'+state.get('squeue','').strip()+'`；采集时间 '+state['timestamp']+'。\n\n'
report+='## 复核与文件\n\n'
for name,desc in [('bridge_candidates.csv','桥梁候选与 Tukey 边界'),('formal_source_status.csv','21 组前向统计状态'),('recommendations.json','正式逐组推荐'),('performance.csv','已有 main 上的 Top-1/3/5'),('paired_summary.csv','同组合配对汇总'),('correlations.csv','各分项指标的层级相关性'),('remote_source_audit.json','服务器已有文件查找证据'),('status.json','补算作业状态')]:
    if (OUT/name).exists():
        report+=f'- [{desc}](../../outputs/visual_track_cosine_20260928/{name})\n'
    else:
        report+=f'- {desc}：待正式前向统计完成后生成。\n'
report+='\n运行 `python scripts/visual_track_remote_20260928.py fetch` 同步完成组合，再运行 `python scripts/analyze_visual_track_cosine_20260928.py` 更新本报告。\n'
doc=ROOT/'md/Location/VisualTrack_Cosine_Recommendation_Analysis.md';doc.write_text(report,encoding='utf-8')
save('verification.json',dict(status='PASS',bridge_source_cohorts=3,bridge_aggregate_reproduced=True,normalized_ranking_and_tukey_equivalent=True,formal_groups_done=done,formal_groups_pending=21-done,bridge_not_mixed_with_formal_evaluation=True,main_rows=sum(len(v) for v in pool.values())))
print(json.dumps(dict(report=str(doc),formal_done=done,formal_pending=21-done,legacy_candidates=legacy),ensure_ascii=False,indent=2))
