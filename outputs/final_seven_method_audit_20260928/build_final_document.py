"""Consolidate verified final-method snapshots into the user-designated document."""
from pathlib import Path
from collections import Counter
from datetime import datetime
import csv
import hashlib
import json
import math
import statistics
import sys

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
TARGET = ROOT / 'md/Location/Final-candidate-methods-recommends-top3-layer.md'
MARKER = '<!-- FINAL_SEVEN_METHODS_VERIFIED_SNAPSHOT -->'
MODELS = {
    'blip2-opt-2.7b': ('BLIP2', 32),
    'instructblip-vicuna-7b': ('InstructBLIP', 32),
    'minigpt-4-vicuna-7b': ('MiniGPT-4', 32),
    'llava-v1.5-7b': ('LLaVA-1.5', 32),
    'qwen2.5-vl-3b': ('Qwen2.5-VL', 36),
    'paligemma-3b': ('PaliGemma', 18),
    'smolvlm-1.7b': ('SmolVLM', 24),
}
DATASETS = {'evqa-pilot500': ('EVQA', 500), 'mmke-visual': ('MMKE-Visual', 214), 'mmke-entity': ('MMKE-Entity', 636)}
GROUPS = [(ds,m) for ds in DATASETS for m in MODELS]
PROVENANCE = {}

def load(path):
    b=path.read_bytes(); PROVENANCE[path.relative_to(ROOT).as_posix()]=hashlib.sha256(b).hexdigest()
    return json.loads(b.decode('utf-8-sig'))

def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def link(label,path):
    return f'[{label}](../../{path.relative_to(ROOT).as_posix()})'

def table(head, data):
    data=[list(r) for r in data]
    assert all(len(r)==len(head) for r in data)
    def cell(x):return str(x).replace('|','\\|').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(cell(x) for x in r)+' |' for r in data])

def ls(items,zero=()):
    return ', '.join(f'L{l}'+('†' if l in zero else '') for l in items) or '—'

def number(value):return '未齐' if value is None else f'{value:.3f}'

registry_path=ROOT/'outputs/all_methods_recommendations_20260928/recommendations.json'
registry=load(registry_path)
reg={(r['method'],r['flavor'],r['dataset'],r['model']):r for r in registry['records']}
grad=load(OUT/'gradient_available_top3.json')
gr={(r['formula_id'],r['dataset'],r['model']):r for r in grad}
vis=load(OUT/'visedit_model_pred_components.json')
vr={(r['component'],r['dataset'],r['model']):r for r in vis}
similarity=load(OUT/'similarity_verified.json')
sr={(r['variant'],r['flavor'],r['dataset'],r['model']):r for r in similarity['recommendations']}
remote=load(OUT/'remote_status.json')
previous_verification=load(OUT/'verification.json')
outcome_path=ROOT/'outputs/all_methods_performance_20260928/outcomes_used.csv'
PROVENANCE[outcome_path.relative_to(ROOT).as_posix()]=hashlib.sha256(outcome_path.read_bytes()).hexdigest()
with outcome_path.open(encoding='utf-8-sig',newline='') as f:
    outcome_rows=list(csv.DictReader(f))
pool={(r['dataset'],r['model'],int(r['layer'])):float(r['Average']) for r in outcome_rows if r['recipe']=='main'}
assert len(pool)==396
assert len(gr)==147 and len(vr)==21
assert all(r['source_hashes_verified'] for r in similarity['verified'])

def perf(ds,m,top):
    assert len(top)==len(set(top)) and all(0<=l<MODELS[m][1] for l in top)
    missing=[l for l in top if (ds,m,l) not in pool]
    complete=len(top)==3 and not missing
    return dict(complete=complete,missing=missing,mean3=statistics.mean(pool[ds,m,l] for l in top) if complete else None,
                layer_average=[dict(layer=l,Average=pool.get((ds,m,l))) for l in top])

records=[]
def register(section,key,ds,m,top=None,reason='',**extra):
    if top is None:
        r=dict(section=section,version=key,dataset=ds,model=m,status='pending',top3=[],reason=reason,**extra)
    else:
        r=dict(section=section,version=key,dataset=ds,model=m,status='ready' if len(top)==3 else 'insufficient_layers',top3=top,**perf(ds,m,top),**extra)
    records.append(r)
    return r

BASELINES=[(1,'中层先验','Middle-Prior','raw'),(2,'CMA-model_pred','CMA-model_pred','raw'),(4,'SaLEM-alt','SaLEM-alt','raw'),(5,'LGA 参数梯度：Tukey','LGA-Param','tukey'),(6,'Perturb-KL-alt','Perturb-KL-alt','raw')]
baseline={}
for sec,title,method,flavor in BASELINES:
    baseline[sec]=[]
    for ds,m in GROUPS:
        original=reg[method,flavor,ds,m]
        assert original['status']=='done'
        baseline[sec].append(register(sec,method+'/'+flavor,ds,m,original['top3'],source=original['source'],sample_count=original.get('sample_count'),notes=original.get('notes',''),source_status=original.get('source_status','done')))

formula_definitions={
 1:('有符号方向×旧强度×新强度','E[c×a×b]','保留方向和两侧强度，对应视觉梯度内积。'),
 2:('绝对方向×旧强度×新强度','E[abs(c)×a×b]','强调方向关系强度，同时接受同向和反向，保留旧、新两侧强度。'),
 3:('有符号方向×新强度','E[c×b]','去掉旧梯度强度，对应新梯度沿旧梯度单位方向的有符号投影。'),
 4:('绝对方向×新强度','E[abs(c)×b]','去掉旧强度并忽略方向正负，对应新梯度在旧梯度方向轴上的投影长度。'),
 5:('仅新梯度强度','E[b]','只看新目标敏感性，对逐样本新梯度范数取平均。'),
}
pending_reasons={'F2':'缺逐样本 abs(c)×a×b 交叉统计。','F3':'严格逐样本补算尚在等待前序实验，未有完整可核验组合。','F4':'缺逐样本 abs(c)×b 交叉统计。'}
gradient_records={}
product_first_sources=[]
for f in range(1,6):
    key=f'F{f}'
    for ds,m in GROUPS:
        source=gr.get((f'F{f}-B',ds,m))
        if source:
            r=register(7,key,ds,m,source['top3'],source=source['source'],zero_gradient_layers=source['zero_gradient_layers'],excluded=source['excluded'])
            assert r['missing']==source['missing'] and r['complete']==source['complete']
            if r['mean3'] is not None:assert math.isclose(r['mean3'],source['mean3'],rel_tol=1e-12)
            product_first_sources.append({**source,'formula_id':key,'formula':formula_definitions[f][1],'source_formula_id':source['formula_id']})
        else:r=register(7,key,ds,m,reason=pending_reasons[key])
        gradient_records[key,ds,m]=r

vis_records={}
for component in ['attn','mlp','attn+mlp']:
    for ds,m in GROUPS:
        v=vr.get((component,ds,m))
        for mode in ['contribution','pre']:
            if v:
                top=v['contribution_top3'] if mode=='contribution' else v['pre_top3']
                r=register(3,component+'/'+mode,ds,m,top,source=v['source'])
            else:r=register(3,component+'/'+mode,ds,m,reason='尚无可核验的 MMKE model_pred 贡献原始结果；历史 pred 字段或 alt 不能替代。')
            vis_records[component,mode,ds,m]=r

sim_records={}
for variant in ['none','alt','model_pred']:
    for flavor in ['raw','tukey']:
        for ds,m in GROUPS:
            s=sr.get((variant,flavor,ds,m))
            if s:
                r=register(7,'similarity/'+variant+'/'+flavor,ds,m,s['top3'],sample_count=s['n'])
                assert r['missing']==s['missing_main']
                if r['mean3'] is not None:assert math.isclose(r['mean3'],s['mean3'],rel_tol=1e-12)
            else:r=register(7,'similarity/'+variant+'/'+flavor,ds,m,reason='当前已核验快照尚无该组合完整前向统计。')
            sim_records[variant,flavor,ds,m]=r
for ds,m in GROUPS:register(7,'similarity/none/peak-region-middle',ds,m,reason='尚未实现极大值区间、中层和 Top-3 邻层的确定规则；不是已有 Raw/Tukey 排序。')

def coverage(rr):return sum(r['status']=='ready' for r in rr),sum(r.get('complete',False) for r in rr)
stamp=datetime.now().astimezone().isoformat(timespec='seconds')
lines=['# 最终七类定位方法：已有 Top-3 推荐层与缺项', '',MARKER,'',
 f'**整理时间：{stamp}（本机北京时间）。** 本表依据已核验快照回填，方法顺序遵从最终截图：中层、CMA-model_pred、VisEdit-model_pred、SaLEM-alt、参数 LGA、Perturb-KL-alt、第七类猜想。', '',
 f"定位基线来源快照：{registry['updated_at']}；梯度/VisEdit 本地派生快照：{previous_verification['local_time']}；服务器梯度等待状态：{remote['checked_at']}；绿色相似度完成产物采集：{similarity['checked_at']}。本表不将这些有时间戳的状态称为持续实时进度。", '',
 '## 0. 统一口径与完成概览','',
 '- 层号从 L0 开始；候选 L_l 表示 adapter 接在 decoder block l 输出之后。Top-3 保留推荐顺序。',
 '- alt 为新目标；model_pred 为模型响应；数据集 pred 字段单独区分。此表没有用 VisEdit-alt 或历史 pred 来填充最终要求的 model_pred。',
 '- 第七类梯度猜想统一采用逐样本先计算乘积、再跨样本平均的五个公式 F1–F5，尚未确定唯一最优公式。',
 '- 参数 LGA 与五类视觉梯度公式按全层 Tukey 排名：Q1−IQR 至 Q3+IQR，κ=1，linear 四分位数，一次过滤，边界保留，同分取浅层，不按真实编辑效果决定剔除层。',
 '- † 表示已有原始记录标记的零视觉梯度层。当前全层协议保留有限零分；零分排在负分之前不代表存在有效方向证据。',
 '- Mean@3 为三个推荐层各自真实编辑后 Average 的算术平均；三层缺任一层则记“未齐”，不取已完成层的均值、不用 Best@3 替代。Average 延用热力图的五项指标均值。',
 '- 实测覆盖冻结为已同步的 396 条 main 记录；包含已记录的未收敛/恢复等运行标签，不按表现筛除。stable 和独立复测不择优补 main；“实测齐”也不等于所有训练预算已一致验收。', '',]
overview=[]
for sec,title,_,_ in BASELINES:
    a,b=coverage(baseline[sec]);overview.append((sec,[str(sec)+'. '+title,f'{a}/21',f'{b}/21']))
for c in ['attn','mlp','attn+mlp']:
    direct=[vis_records[c,'contribution',ds,m] for ds,m in GROUPS];pre=[vis_records[c,'pre',ds,m] for ds,m in GROUPS]
    a,b=coverage(pre);overview.append((3,[f'3. VisEdit-model_pred / {c}',f'{a}/21',f'贡献 Top-3 {coverage(direct)[1]}/21；Pre {b}/21']))
for f in range(1,6):
    k=f'F{f}';a,b=coverage([gradient_records[k,ds,m] for ds,m in GROUPS]);overview.append((7,[f'7. 梯度 {k}',f'{a}/21',f'{b}/21']))
for v in ['none','alt','model_pred']:
    a,b=coverage([sim_records[v,'raw',ds,m] for ds,m in GROUPS]);bt=coverage([sim_records[v,'tukey',ds,m] for ds,m in GROUPS])[1]
    overview.append((7,[f'7. 相似度 {v}',f'{a}/21',f'降序 Raw {b}/21；Tukey {bt}/21']))
overview.append((7,['7. 不分新旧相似度：极大值区间中层','0/21','选层规则尚未实现']))
lines += [table(['最终方法 / 版本','已有 Top-3','三个推荐层 main 实测已齐'],[x[1] for x in sorted(overview,key=lambda x:x[0])]),'',
 '目录：[1 中层](#1-中层先验) · [2 CMA](#2-cma-model_pred) · [3 VisEdit](#3-visedit-model_pred三类贡献及前置候选) · [4 SaLEM](#4-salem-alt) · [5 LGA](#5-lga模型参数梯度tukey) · [6 Perturb-KL](#6-perturb-kl-alt) · [7 猜想](#7-我们的猜想视觉梯度与表征相似度)','']

def base_section(sec,heading,description):
    lines.extend([f'## {sec}. {heading}','',description,'',table(['数据集','模型','Top-3','定位有效样本','Mean@3 (%)','缺 main 层'],[[DATASETS[r['dataset']][0],MODELS[r['model']][0],ls(r['top3']),'结构先验' if r['sample_count'] is None else f"{r['sample_count']}/{DATASETS[r['dataset']][1]}",number(r['mean3']),ls(r['missing'])] for r in baseline[sec]]),''])

base_section(1,'中层先验','中心为 (L−1)/2；按距离升序，同距离取较浅层。同模型三个数据集推荐相同；下表分别对接各数据集实测。')
base_section(2,'CMA-model_pred','在视觉污染输入中逐层恢复正常视觉状态，按对完整 model_pred 答案平均对数概率的相对恢复量排序。目标是模型当前响应，不是 alt。当前采用 α={0.5,1,2}×seed={0,1,2}。有推荐不代表全样本都通过内部恢复有效性过滤。')
unstable=[r for r in baseline[2] if r['source_status']!='done']
lines+=['排名稳定性提示：'+ '；'.join(f"{DATASETS[r['dataset']][0]} / {MODELS[r['model']][0]}：{r['source_status']}" for r in unstable)+'。','']

lines+=['## 3. VisEdit-model_pred：三类贡献及前置候选','',
 '原始模块贡献分别保存 attention、MLP，以及合并曲线。贡献度排序是归因依据；Pre 是仿照 VisEdit 在高贡献区之前插入 adapter 的基线。两种列表分列，不把贡献最高层直接称为原文选定编辑层。', '',
 '已有 EVQA 七组的 model_pred 是模型下一 token argmax 目标。MMKE 两个数据集共十四组尚缺真正 model_pred 原始贡献；alt、历史数据集 pred 不换名填充。', '',
 '当前用于推荐的正贡献：attn=max(0,attn_mean)，mlp=max(0,mlp_mean)，合并为二者之和。Pre 对各自曲线使用三层滑动均值，阈值 mean+0.5×std，选择最长高贡献连续区；等长取贡献和更大者，再取更浅者。区间从 s 开始时取 s−1、s−2、s−3，不足三层不回填。此自动规则为项目基线。', '',
 '### 3.1 三类贡献 Top-3 与 Pre Top-3','']
for ds in DATASETS:
    rr=[]
    for m in MODELS:
        cells=[MODELS[m][0]]
        for c in ['attn','mlp','attn+mlp']:
            v=vr.get((c,ds,m));cells += [ls(v['contribution_top3']) if v else '待补',ls(v['pre_top3']) if v else '待补']
        rr.append(cells)
    lines += [f'**{DATASETS[ds][0]}**','',table(['模型','attn 贡献','attn Pre','mlp 贡献','mlp Pre','attn+mlp 贡献','attn+mlp Pre'],rr),'']
lines+=['### 3.2 已有 EVQA 推荐的实测覆盖','',table(['模型','贡献对象','贡献 Top-3 Mean@3','贡献 Top-3 缺层','Pre Mean@3','Pre 缺层'],[[MODELS[m][0],c,number(vis_records[c,'contribution','evqa-pilot500',m]['mean3']),ls(vis_records[c,'contribution','evqa-pilot500',m]['missing']),number(vis_records[c,'pre','evqa-pilot500',m]['mean3']),ls(vis_records[c,'pre','evqa-pilot500',m]['missing'])] for m in MODELS for c in ['attn','mlp','attn+mlp']]),'',
 '### 3.3 全层贡献度排序：高到低','',
 '下列各行均为 EVQA-model_pred，保留原始有符号排序和用于当前 Pre 的正贡献排序。合并的有符号分数为 attn_mean+mlp_mean；正贡献合并则分别取正部后相加。同分取浅层。MMKE 无原始结果，不能输出全层排序。','']
for m in MODELS:
    lines += [f'**{MODELS[m][0]}**','']
    for c in ['attn','mlp','attn+mlp']:
        v=vr[c,'evqa-pilot500',m]
        lines += [f"- **{c}**：有符号排序 {ls(v['signed_full_ranking'])}。",'',f"  正贡献排序 {ls(v['positive_full_ranking'])}。高贡献区 {ls(v['high_region'])}（区间端点），Pre 为 {ls(v['pre_top3'])}。",'']

base_section(4,'SaLEM-alt','对新目标 alt 损失计算配置指定 MLP/FFN 模块的参数绝对梯度，按参数总数归一化，再跨样本平均。保留现有参数空间定位器，最终在推荐位置训练视觉 adapter。该定位计算本身不更新基础模型参数。')
base_section(5,'LGA：模型参数梯度，Tukey','old=model_pred，new=alt；先逐样本计算 MLP/FFN 权重梯度有符号内积，再取平均。按最终方案使用 Tukey 后 Top-3；Raw 保留于来源归档，不以其替换此主列。参数空间与视觉空间有效样本集合可能不同。')
base_section(6,'Perturb-KL-alt','扰动层间视觉 token 隐状态，在完整 alt teacher-forcing 答案位置比较干净/扰动的全词表输出分布 KL。现有 score_kl_robust 使用四噪声强度×三重复，在各配置内层间归一化后聚合；直接选敏感层，不做 Pre。')

lines+=['## 7. 我们的猜想：视觉梯度与表征相似度','',
 '### 7.1 梯度对象与五个逐样本公式','',
 '定位时在冻结基础模型的 decoder 层输出视觉隐状态 Hᵥ 上计算梯度，等价于在 ΔHᵥ=0 处对虚拟视觉增量求梯度；不是先训练 adapter 后再归因，也不是 adapter 权重梯度。', '',
 'aᵢ=旧目标视觉梯度 L2 范数，bᵢ=新目标视觉梯度 L2 范数，cᵢ=二者余弦；E 为同一组合有效样本的等权平均。每个样本先计算对应公式，再跨样本平均；F2、F4 在样本内对 cᵢ 取绝对值，F5 直接平均逐样本新梯度范数。', '',
 table(['公式','归因含义','逐样本计算后平均'],[[f'F{f}：{x[0]}',x[2],x[1]] for f,x in formula_definitions.items()]),'',
 'F1 按原 epsilon=1e-12 约定使用 E[dot]−epsilon×E[c]，21 组 Tukey Top-3 与既有视觉 LGA 一致。F5 为逐样本新梯度范数的均值。五个公式统一应用于七模型×三数据集，每个公式独立过滤异常层并推荐 Top-3。', '',
 '缺失 F2、F3、F4 的原因是旧逐样本日志未保存所需 cos/范数交叉统计。严格补算会保存逐样本基础量，完成后可以生成这些公式；当前已核验快照仍为等待前序实验。', '',
 'BLIP2 × MMKE-Entity 视觉梯度沿用 284/636 条有效样本（44.65%），属于低覆盖；这不等于在全部 636 条上定位。其他组合有效样本数可追溯原层分数 n_request。','']
for f,(name,formula,description) in formula_definitions.items():
    lines += [f'### 7.1.{f} F{f}：{name}','',f'**公式：`{formula}`。** {description}','']
    rr=[]
    for ds,m in GROUPS:
        cells=[DATASETS[ds][0],MODELS[m][0]]
        r=gradient_records[f'F{f}',ds,m]
        cells += [ls(r['top3'],r.get('zero_gradient_layers',[])) if r['status']=='ready' else '待补',number(r.get('mean3')) if r['status']=='ready' else '—',ls(r['missing']) if r['status']=='ready' else '待定位']
        rr.append(cells)
    lines += [table(['数据集','模型','Top-3','Mean@3','缺 main 层'],rr),'']

lines += ['### 7.2 绿色点划线：视觉表征相似度','',
 '相似度比较视觉 token 隐状态均值与文本预测位置的隐状态，不是新旧梯度余弦。不分新旧 none 使用固定图像+问题的首答案预测位置；alt/model_pred 在相应答案各普通 token 的预测位置计算，先样本内平均，再跨样本平均。图像/Q-Former 编码不混入答案。', '',
 '主对比使用 matched_gradient，与既有视觉梯度有效样本 ID 对齐。BLIP2 等组合虽然 none/alt 可处理更多样本，不能把不同覆盖率直接混进公式比较。', '',
 f"截至服务器快照 {similarity['checked_at']}，完成 {similarity['completed_groups']}/21 个组合，三种目标共 {similarity['completed_target_variants']}/63 个组合×目标；分数、协议、诊断文件哈希已核对。当时控制器在 g09 运行 MiniGPT-4。", '',
 '截图中的“极大值区间中层”仍未实现；需要独立定义区间阈值、多峰选择、中心和 Top-3 邻层。以下 Raw 表示直接按相似度高到低，Tukey 是另列的过滤版本，两者都不能替代区间中层规则。','']
for variant,title in [('none','不分新旧'),('alt','仅新目标 alt'),('model_pred','仅旧目标 model_pred')]:
    lines += [f'#### {title}：已有推荐','']
    rr=[]
    for ds,m in GROUPS:
        cells=[DATASETS[ds][0],MODELS[m][0]]
        raw=sim_records[variant,'raw',ds,m]
        cells.append(str(raw['sample_count']) if raw['status']=='ready' else '待补')
        for flavor in ['raw','tukey']:
            r=sim_records[variant,flavor,ds,m]
            cells += [ls(r['top3']) if r['status']=='ready' else '待补',number(r.get('mean3')) if r['status']=='ready' else '—',ls(r['missing']) if r['status']=='ready' else '待定位']
        rr.append(cells)
    lines += [table(['数据集','模型','匹配样本数','降序 Raw Top-3','Raw Mean@3','Raw 缺 main 层','Tukey Top-3','Tukey Mean@3','Tukey 缺 main 层'],rr),'']

lines += ['## 8. 尚缺的数据与来源','',
 '- VisEdit：MMKE-Visual、MMKE-Entity 共十四组 model_pred 原始贡献。三条贡献分支均受此缺项影响。',
 '- 视觉梯度：F2、F3、F4 各二十一组，缺严格逐样本交叉统计；服务器等待状态不等于已算完。',
 f"- 绿色相似度：当前快照尚缺 {21-similarity['completed_groups']} 个组合的完整前向结果；另有不分新旧的极大值区间中层选层规则尚未实现。",
 '- 已有定位的候选层仍存在 main 编辑评测缺项，逐行列在各表“缺 main 层”。不将缺分记为零，不替换为 stable，不以部分 Top-3 平均值宣称完整 Mean@3。', '',
 '本表用于记录候选和已有实测；尚不能判定某一第七类公式在全部七模型×三数据集上超过前六类方法。公式须统一应用于二十一组，宏均值更高与逐组全部胜出分别报告。','',
 '### 数据文件','',
 '- '+link('最终方法全量登记 JSON（含待补、逐候选层 Average、Mean@3）',OUT/'final_methods_registry.json'),
 '- '+link('本表生成核验与来源哈希',OUT/'final_document_verification.json'),
 '- '+link('原始定位总登记',registry_path),
 '- '+link('视觉梯度已完成逐样本公式、逐层分数及 Tukey 剔除层',OUT/'gradient_product_first_top3.json'),
 '- '+link('VisEdit 三分支完整分数、排序与高贡献区',OUT/'visedit_model_pred_components.json'),
 '- '+link('绿色相似度已核验产物及完整排序',OUT/'similarity_verified.json'),
 '- '+link('main/stable 原始评测汇总',outcome_path),
 '- '+link('独立核验附表',OUT/'核验附表.md'),
 '- '+link('服务器只读状态快照',OUT/'remote_status.json'),
 '- '+link('可重建脚本',Path(__file__)), '',
 '### 可复现与版本边界','',
 '本次只读取此前核验快照并回填指定 Markdown，未启动或更改服务器实验。后续补算完成后，应先更新已核验输入再重建此表；不能只改完成数量而不补原始分数及推荐层。历史方法并集结论不约束本次最终方法方案。','']

assert len(records)==483
counts=Counter(r['status'] for r in records)
assert counts=={'ready':243,'pending':240}, counts
assert len({(r['version'],r['dataset'],r['model']) for r in records})==len(records)
assert len(gradient_records)==105 and len(product_first_sources)==42
assert all(r['top3']==gr['F5-B',r['dataset'],r['model']]['top3'] for r in records if r['version']=='F5')
content='\n'.join(lines)+'\n'
before=TARGET.read_text(encoding='utf-8-sig') if TARGET.exists() else ''
if before and MARKER not in before:
    raise RuntimeError('Target has new non-generated content; preserve it and merge explicitly.')
if before:
    (OUT/'final_document.previous.md').write_text(before,encoding='utf-8')
save(OUT/'gradient_product_first_top3.json',product_first_sources)
save(OUT/'final_methods_registry.json',dict(written_at=stamp,snapshot_sources=PROVENANCE,records=records))
TARGET.write_text(content,encoding='utf-8')
verified=dict(status='PASS',written_at=stamp,target=TARGET.relative_to(ROOT).as_posix(),document_sha256=hashlib.sha256(TARGET.read_bytes()).hexdigest(),line_count=len(content.splitlines()),registered_rows=len(records),ready_rows=counts['ready'],pending_rows=counts['pending'],baseline_rows=105,visedit_rows=126,gradient_rows=105,similarity_raw_tukey_rows=126,similarity_peak_region_rows=21,available_gradient_rows=42,available_visedit_rows=42,available_similarity_rows=len(similarity['recommendations']),main_outcome_rows=len(pool),sample_mean_only_when_three_evaluations=True,gradient_aggregation='product_within_sample_then_mean',source_sha256=PROVENANCE)
save(OUT/'final_document_verification.json',verified)
appendix=OUT/'核验附表.md'
text=appendix.read_text(encoding='utf-8')
notice='> **完整最终方法主表：** [Final-candidate-methods-recommends-top3-layer.md](../../md/Location/Final-candidate-methods-recommends-top3-layer.md)。该主表已逐组汇集前六类基线、VisEdit 三分支、五个逐样本梯度公式、绿色相似度及待补状态；本附表保留独立审计快照。\n\n'
if notice not in text:
    text='\n'.join(line for line in text.split('\n') if not line.startswith('> **完整最终方法主表：**'))
    title,remaining=text.split('\n',1)
    appendix.write_text(title+'\n\n'+notice+remaining.lstrip('\n'),encoding='utf-8')
print(json.dumps(verified,ensure_ascii=False,indent=2))
