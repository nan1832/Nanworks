"""Read-only source audit; writes only this isolated local audit directory."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import ast
import csv
import hashlib
import json
import math
import sys
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REG = ROOT / 'outputs/all_methods_recommendations_20260928'
sys.path.insert(0, str(ROOT / 'scripts'))

def js(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def table(headers, data):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] + ['| '+' | '.join(map(str,r))+' |' for r in data])

def layers(xs):
    return ', '.join('L'+str(x) for x in xs) or '—'

def rank(values, tukey=True):
    finite={l:v for l,v in values.items() if math.isfinite(v)}
    q1,q3=np.quantile(list(finite.values()), [.25,.75], method='linear')
    lo,hi=q1-(q3-q1),q3+(q3-q1)
    removed=[l for l,v in finite.items() if tukey and (v<lo or v>hi)]
    order=sorted((l for l in finite if l not in removed), key=lambda l:(-finite[l],l))
    return dict(top3=order[:3], all_ranking=order, excluded=removed, lower=float(lo), upper=float(hi))

registry=js(REG/'recommendations.json')['records']
outcome_path=ROOT/'outputs/all_methods_performance_20260928/outcomes_used.csv'
outcomes=rows(outcome_path)
pool={(r['dataset'],r['model'],int(r['layer'])):float(r['Average']) for r in outcomes if r['recipe']=='main'}
assert len(pool)==sum(r['recipe']=='main' for r in outcomes)

def performance(ds,model,top):
    missing=[l for l in top if (ds,model,l) not in pool]
    complete=len(top)==3 and not missing
    return dict(complete=complete, missing=missing,
                mean3=sum(pool[ds,model,l] for l in top)/3 if complete else None,
                best3=max(pool[ds,model,l] for l in top) if complete else None)

remote_code=r'''
import json,datetime
from pathlib import Path
r=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
o={'checked_at':datetime.datetime.now().astimezone().isoformat()}
for name,rel in [('visual_priority','visual_track_cosine_20260928/priority_switch/status.json'),('lga_g08','lga_two_spaces_ablation_20260928/control/g08_status.json'),('lga_g09','lga_two_spaces_ablation_20260928/control/g09_status.json')]:
 p=r/rel
 o[name]=json.loads(p.read_text()) if p.exists() else None
for name,rel in [('visual_groups','visual_track_cosine_20260928/targets_v2/results'),('lga_groups','lga_two_spaces_ablation_20260928/results')]:
 groups=[]
 for folder in (r/rel).glob('*/*'):
  if name=='lga_groups': candidates=list(folder.glob('*'))
  else: candidates=[folder]
  for d in candidates:
   if not d.is_dir(): continue
   g={'path':str(d),'sample_files':len(list((d/'samples').glob('*.json')))}
   for fn in ['summary.json','progress.json']:
    p=d/fn
    if p.exists():
     obj=json.loads(p.read_text());obj.pop('sample_files',None);g[fn]=obj
   groups.append(g)
 o[name]=groups
print(json.dumps(o,ensure_ascii=False))
'''
try:
    from lga_ablation_remote import ssh
    remote=js(OUT/'remote_status.json') if '--offline' in sys.argv and (OUT/'remote_status.json').exists() else json.loads(ssh(remote_code,timeout=60))
except Exception as e:
    remote=dict(error=str(e), checked_at=datetime.now().astimezone().isoformat())
save('remote_status.json',remote)

source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [REG/'recommendations.json',outcome_path]}
visual=[]
new_formulas={
 'F1-A': ('E[c] E[a] E[b]', lambda c,a,b,d:c*a*b),
 'F2-A': ('abs(E[c]) E[a] E[b]', lambda c,a,b,d:abs(c)*a*b),
 'F3-A': ('E[c] E[b]', lambda c,a,b,d:c*b),
 'F4-A': ('abs(E[c]) E[b]', lambda c,a,b,d:abs(c)*b),
 'F5-A': ('E[b]', lambda c,a,b,d:b),
 'F1-B': ('E[c*a*b] = E[dot] - 1e-12 E[c]', lambda c,a,b,d:d-1e-12*c),
 'F5-B': ('E[b]; identical to F5-A', lambda c,a,b,d:b),
}
epsilon_ranking_checks=0
for p in sorted((REG/'raw/visual').glob('*/*/ours_direct_layer_scores.csv')):
    ds,model=p.parent.parent.name,p.parent.name
    rr=rows(p);source_hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    vals={key:{} for key in new_formulas}
    for r in rr:
        l=int(r['layer']); c,a,b,d=[float(r[k]) for k in ['S_v_cos','S_v_old_norm','S_v_new_norm','S_v_dot']]
        for key,(_,fn) in new_formulas.items(): vals[key][l]=fn(c,a,b,d)
    for key,(formula,_) in new_formulas.items():
        rec=dict(dataset=ds,model=model,formula_id=key,formula=formula,source=str(p.relative_to(ROOT)),**rank(vals[key]))
        rec['scores']=vals[key]
        rec['zero_gradient_layers']=[int(r['layer']) for r in rr if r['S_v_zero_grad'].lower()=='true']
        rec.update(performance(ds,model,rec['top3']))
        visual.append(rec)
        alias={'F1-B':'LGA-Visual','F3-A':'Ours-signed-direction','F4-A':'Ours-main','F5-A':'Ours-no-direction','F5-B':'Ours-no-direction'}.get(key)
        if alias:
            old=next(r for r in registry if (r['method'],r['dataset'],r['model'],r['flavor'])==(alias,ds,model,'tukey'))
            assert rec['top3']==old['top3'],(key,ds,model)
            if key=='F1-B':epsilon_ranking_checks+=1
    assert vals['F5-A']==vals['F5-B']
save('gradient_available_top3.json',visual)

src=ROOT/'VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py'
tree=ast.parse(src.read_text(encoding='utf-8'))
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'moving_average','find_high_region','pre_candidates'}]
ns={'np':np};exec(compile(ast.Module(body=funcs,type_ignores=[]),str(src),'exec'),ns)
vis=[]
for r in registry:
    if r['method']!='VisEdit-Pre-model_pred' or r['status']!='done':continue
    p=ROOT/r['source'];rr=rows(p)
    source_hashes[r['source']]=hashlib.sha256(p.read_bytes()).hexdigest()
    for component in ['attn','mlp','attn+mlp']:
        signed={int(x['layer']):float(x['attn_mean']) if component=='attn' else float(x['mlp_mean']) if component=='mlp' else float(x['attn_mean'])+float(x['mlp_mean']) for x in rr}
        positive={int(x['layer']):max(0,float(x['attn_mean'])) if component=='attn' else max(0,float(x['mlp_mean'])) if component=='mlp' else max(0,float(x['attn_mean']))+max(0,float(x['mlp_mean'])) for x in rr}
        order=sorted(positive,key=lambda l:(-positive[l],l))
        signed_order=sorted(signed,key=lambda l:(-signed[l],l))
        smooth=ns['moving_average']([positive[l] for l in range(len(rr))],3)
        region,threshold,_=ns['find_high_region'](smooth,.5)
        pre=ns['pre_candidates'](region[0],3) if region else []
        if component=='attn+mlp':assert pre==r['top3']
        v=dict(dataset=r['dataset'],model=r['model'],component=component,source=r['source'],signed_scores=signed,signed_full_ranking=signed_order,positive_scores=positive,positive_full_ranking=order,contribution_top3=order[:3],high_region=region,threshold=float(threshold),pre_top3=pre,pre_status='done' if len(pre)==3 else 'insufficient_layers',direct_performance=performance(r['dataset'],r['model'],order[:3]),pre_performance=performance(r['dataset'],r['model'],pre))
        vis.append(v)
save('visedit_model_pred_components.json',vis)
save('source_sha256.json',source_hashes)

baseline=[]
for method,flavor in [('Middle-Prior','raw'),('CMA-model_pred','raw'),('VisEdit-Pre-model_pred','current'),('SaLEM-alt','raw'),('LGA-Param','tukey'),('Perturb-KL-alt','raw')]:
    rr=[r for r in registry if r['method']==method and r['flavor']==flavor]
    ready=[r for r in rr if r['status']=='done']
    missing=[]
    for r in ready:
        perf=performance(r['dataset'],r['model'],r['top3'])
        if not perf['complete']:missing.append(dict(dataset=r['dataset'],model=r['model'],top3=r['top3'],**perf))
    baseline.append(dict(method=method,flavor=flavor,registered=len(rr),ready=len(ready),full_main=len(ready)-len(missing),missing=missing))
save('baseline_coverage.json',baseline)

summary=dict(local_time=datetime.now().astimezone().isoformat(),outcome_source=str(outcome_path.relative_to(ROOT)),main_rows=len(pool),gradient_ids={k:dict(groups=sum(r['formula_id']==k for r in visual),full_main=sum(r['formula_id']==k and r['complete'] for r in visual)) for k in new_formulas},visedit={c:dict(groups=sum(r['component']==c for r in vis),full_main_direct=sum(r['component']==c and r['direct_performance']['complete'] for r in vis),full_main_pre=sum(r['component']==c and r['pre_performance']['complete'] for r in vis),insufficient_pre=sum(r['component']==c and len(r['pre_top3'])<3 for r in vis)) for c in ['attn','mlp','attn+mlp']},epsilon_rank_matches=epsilon_ranking_checks)
save('verification.json',summary)

doc=['# 最终七类方法核验：独立审计附表','',f"本地核验时间：{summary['local_time']}；服务器只读核验时间：{remote.get('checked_at','未取得')}。",'',
     '按用户本次截图重新核验。旧文档的“唯一主公式已定”不约束本次公式比较。本次只在本目录保存核验及可直接派生的结果，没有更改原三份手册或服务器任务。','',
     'A=分别求样本均值后相乘；B=每个样本内部相乘后平均。a=旧视觉梯度范数，b=新视觉梯度范数，c=新旧视觉梯度余弦。F2/F4 的 A 版取 abs(E[c])；B 版取 E[abs(c)×…]。','',
     '## 定位结果与真实编辑评测覆盖','',
     '实测口径固定为热力图对应汇总中的 396 条 main 记录（包含已有失败/恢复标签）；stable、独立复测不择优填补 main。这里统计是否三个推荐层都有实测，不宣称全部已经同预算训练合格。','',
     table(['方法','已有定位组/21','三个推荐层均有 main 实测组/21'],[[r['method']+'/'+r['flavor'],r['ready'],r['full_main']] for r in baseline]),'',
     '## 视觉梯度五公式×两种聚合','',
     table(['编号','公式','定位状态','完整 main 组/21'],[[k,v[0],'21/21；本次从既有统计派生' if k in ['F1-A','F2-A'] else '21/21；复核既有统计',summary['gradient_ids'][k]['full_main']] for k,v in new_formulas.items()]+[['F2-B','E[abs(c)*a*b]','缺逐样本交叉统计','—'],['F3-B','E[c*b]','严格逐样本补算尚未导入，详见实时状态','—'],['F4-B','E[abs(c)*b]','缺逐样本交叉统计','—']]),'',
     'F5-A 与 F5-B 数学上相同。F1-A/F2-A 明确定义为三个均值相乘，不能用 E[c]×E[a*b] 或 abs(E[c])×E[a*b] 替代。F1-B 按原 epsilon=1e-12 约定由 E[dot]−epsilon E[c] 得到，与既有 LGA-Visual 的 21 组 Tukey Top-3 均相同。','',
     '每个公式在全体有限层分数上独立做一次 Tukey：Q1−IQR 至 Q3+IQR，linear 四分位数，边界保留，同分取浅层。不使用真实编辑结果决定剔除层。沿用目前全层口径保留有限零梯度层，并在 JSON 单列；这些层不能解释为有效梯度方向。','',
     '### 可用公式的全部 Top-3','',
     table(['数据集','模型','公式','Tukey Top-3','缺 main 层','Mean@3'],[[r['dataset'],r['model'],r['formula_id'],layers(r['top3']),layers(r['missing']),f"{r['mean3']:.4f}" if r['mean3'] is not None else '未齐'] for r in visual]),'',
     '## VisEdit-model_pred 三种贡献','',
     'EVQA 7 组原始文件均含 attn_mean 和 mlp_mean。本次从原始列派生独立 attn、mlp、attn+mlp 排序及 Pre。两个 MMKE 数据集的 14 组仍缺真正 model_pred 原始贡献；历史 pred 字段归档不能替代。','',
     '为明确处理负贡献，JSON 同时保存原始有符号全排序与正贡献全排序。下表按现有总表协议：先求模块贡献均值，再取正部；attn+mlp=positive(attn_mean)+positive(mlp_mean)。Pre 用同一分数经三层滑动均值，阈值 mean+0.5std，选最长连续高贡献区（等长取贡献和更高者，再取浅者），区域从 s 开始时取 s−1,s−2,s−3，不足不回填。该自动规则是项目基线，并非原文给出的唯一算法。','',
     table(['模型','贡献对象','原始有符号 Top-3','正贡献 Top-3','高贡献区','Pre Top-3','缺 main 层'],[[r['model'],r['component'],layers(r['signed_full_ranking'][:3]),layers(r['contribution_top3']),str(r['high_region']),layers(r['pre_top3']),layers(r['pre_performance']['missing'])] for r in vis]),'',
     '### 全层贡献排序（高→低）','']
for r in vis:
    doc += [f"**{r['model']} / {r['component']}**",'',f"原始有符号：{layers(r['signed_full_ranking'])}",'',f"正贡献：{layers(r['positive_full_ranking'])}",'']
doc += ['## 来源与实时状态','', '[实时状态 JSON](remote_status.json) · [基线缺层](baseline_coverage.json) · [十版中可计算的七版](gradient_available_top3.json) · [VisEdit 三分支完整排序](visedit_model_pred_components.json) · [来源 SHA-256](source_sha256.json) · [核验统计](verification.json)','',
        '原文件中的“正式 Ours 已定”“VisEdit 单合并版”“LGA Raw 主版本”等描述属于历史口径。本次按用户最终列表核验，不能将这些历史表述当作新的执行指令。']
(OUT/'核验附表.md').write_text('\n'.join(doc)+'\n',encoding='utf-8')
print(json.dumps({'verification':summary,'baseline':baseline,'remote':remote},ensure_ascii=False,indent=2))
