from pathlib import Path
from collections import defaultdict
import csv,json,shutil,re,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
def rows(n):return list(csv.DictReader((H/n).open(encoding='utf-8-sig')))
def load(n):return json.loads((H/n).read_text(encoding='utf-8'))
def f(x):return f'{float(x):.3f}'
def fmt(xs):return ','.join('L'+str(x) for x in xs) or '—'
def link(p,label):return f'[{label}](<{str(p.resolve()).replace(chr(92),"/")}>)'
S=load('calculation_summary.json');A=rows('tukey_audit_21groups.csv');P=rows('paired_summary.csv');F=rows('same_cohort_method_summary.csv');E=rows('tukey_candidate_execution_status.csv');Q=rows('quartile_sensitivity.csv');O=rows('outcomes_main_used.csv')
O={(r['dataset'],r['model'],int(r['layer'])):r for r in O}
missing=defaultdict(lambda:{3:[],5:[]});newmissing=defaultdict(list)
for r in E:
    if r['main_evaluation_available']=='False':
        g=r['dataset'],r['model'];missing[g][int(r['k'])].append(int(r['layer']))
        if r['k']=='3' and r['new_vs_old_seven_union']=='True':newmissing[g].append(int(r['layer']))
new_n=sum(map(len,newmissing.values()))
table=['| 数据集 | 模型 | Raw Top-3 | Tukey Top-3 | Tukey Top-5 | 剔除层 |','|---|---|---|---|---|---|']
for r in A:table.append('| '+' | '.join(r[k] for k in ['dataset','model','raw_top3','tukey_top3','tukey_top5','excluded_layers'])+' |')
cohort=['| 方法 | 同一批组合数 | Best@3 | Mean@3 | 已测层 Regret@3 | 已测层 Hit@3 |','|---|---:|---:|---:|---:|---:|']
for r in F:
    if r['profile']=='observed_main' and r['comparison']=='raw_tukey_ours_same_groups' and r['k']=='3':cohort.append(f"| {r['method']} | {r['n']} | {f(r['best'])} | {f(r['mean'])} | {f(r['regret'])} | {float(r['hit'])*100:.1f}% |")
pending=['| 数据集 | 模型 | Top-3 尚缺 main 评测 | 其中新增于旧七方法 Top-3 并集 | 扩至 Top-5 额外缺项 |','|---|---|---|---|---|']
for (d,m),rr in sorted(missing.items()):pending.append(f'| {d} | {m} | {fmt(rr[3])} | {fmt(newmissing[d,m])} | {fmt([x for x in rr[5] if x not in rr[3]])} |')
report=[
'# LGA Tukey 补正：21 组候选、真实编辑比较与待补层',
'',f"版本：`{S['version']}`。参数分数只读同步于 {S['source_manifest_captured_utc']}；原始 88 份文件已逐一核对 SHA-256。",
'',f"已完成全部 21 组候选重算：618 条参数层记录中排除 {S['excluded_layers']} 条，15 组 Top-3 与 Top-5 改变。保留历史 Raw 排名作为消融，不将旧结果改写成 Tukey 结果。",
'','## 1. 补正内容与固定规则','',
'原论文 v2 附录 A 已要求按 Tukey fences 排除整体梯度分数异常的层；v3 指定默认常数为 1。来源：[Golden Layers v3 附录 A](https://arxiv.org/html/2602.20207v3#A1)。此前项目手册将 Tukey 降为可选诊断，导致现有第一阶段缺少这个选择步骤。',
'',
'每个数据集 × 模型独立计算全部有效 MLP/FFN 参数层的 Q1、Q3，IQR = Q3 − Q1；保留 Q1 − IQR ≤ score ≤ Q3 + IQR 的层，然后按带符号 raw dot 降序取候选。上下界上的层保留。不取绝对值，不做对数变换，不删掉所有负分层，不依据真实编辑效果调整 kappa。',
'',
'21 组内部有效样本数在各层完全相同，因此历史均值分数与论文求和分数相差一个正的常数：Tukey 剔除集合与排序一致，已逐组验证。参数版所有 618 层原本均为 finite/ok；本次排除的 76 层属于统计异常层，不是视觉版的末层零梯度过滤。',
'',
'论文没有说明四分位数插值细节。本次预先固定 NumPy `method="linear"`，并报告 midpoint/lower/higher/nearest 的敏感性，不根据编辑结果选择实现。其中 midpoint 会改变 BLIP2 的 E-VQA 与 MMKE-visual 两组候选；因此这是按公开论文规则补齐 Tukey 的可复算实现，不宣称与未核得的作者源代码逐位一致。',
'',
'本次只补正参数版 LGA；视觉隐藏状态 M_dot、当前主公式及训练配置没有改变。参数版沿用原有样本过滤，仍不同于视觉版；二者的比较是现有完整流程的比较，不能据此单独归因于梯度空间。',
'','## 2. 全部候选层','',*table,
'','## 3. 使用相同组合比较 Raw、Tukey 与当前主公式','',
'主表采用已有 main 配置的真实评测，包括已直接评测的不收敛运行，并保留训练状态。stable 不混入。只有一个方法的全部 Top-K 都已评测，才计算其 Best@K、Mean@K。Regret/Hit 的参考是该组合已测 main 层中的最好结果，并非全层 oracle。以下三行严格使用相同的 10 组；该批包含低定位覆盖组，下面另报覆盖与训练状态敏感性。','',*cohort,
'',
'在这批相同组合上，Tukey 相比 Raw 的 Best@3 提高约 2.432，Mean@3 提高约 6.840。当前主公式相比 Tukey 的 Best@3 高约 0.752，但 Mean@3 低约 1.846，Best@3 为 6 胜、0 平、4 负。不能继续将“优于未过滤 Raw”写成“全面优于原论文 LGA”。',
'',
'所有当前可配对的 Raw/Tukey 共有 11 组，Tukey 为 4 胜、6 平、1 负，Best@3 增量约 2.211、Mean@3 增量约 6.218。它与上述三方共同 10 组的平均值不能直接混用。',
'','### 3.1 训练状态与定位覆盖敏感性','',
'`clean` 排除提前恢复、数值异常、停滞、不收敛/诊断记录；它与主表不是同一批组合。不同口径会改变 Mean@3 的符号，不能只选择有利口径。定位覆盖≥80%时同时要求被比较两方法达标。','',
'| 口径 | 覆盖限制 | 主公式/Tukey 共同组数 | ΔBest@3（主公式−Tukey） | ΔMean@3 | 主公式胜/平/负 |','|---|---|---:|---:|---:|---|']
for r in P:
    if r['k']=='3' and r['scope']=='all' and r['method_a']=='Ours-Direct' and r['method_b']=='LGA-Param-Tukey':report.append(f"| {r['profile']} | {r['coverage_policy']} | {r['n']} | {float(r['delta_best']):+.3f} | {float(r['delta_mean']):+.3f} | {r['a_wins']}/{r['ties']}/{r['a_losses']} |")
report+=['','### 3.2 按数据集分开（observed_main、双方覆盖≥80%）','','| 数据集 | 共同组数 | 主公式 ΔBest@3 | 主公式 ΔMean@3 | 胜/平/负 |','|---|---:|---:|---:|---|']
for r in P:
    if r['k']=='3' and r['scope']!='all' and r['profile']=='observed_main' and r['coverage_policy']=='coverage_ge_80pct' and r['method_a']=='Ours-Direct' and r['method_b']=='LGA-Param-Tukey':report.append(f"| {r['scope']} | {r['n']} | {float(r['delta_best']):+.3f} | {float(r['delta_mean']):+.3f} | {r['a_wins']}/{r['ties']}/{r['a_losses']} |")
report+=['','MMKE-entity 在该覆盖限制下只有 1 组可比，不能据此宣布该任务适合某个公式。七方法在共同组上的完整表见 `same_cohort_method_summary.csv`；该表仍保留其他方法的历史版本边界，例如 EVQA 的 VisEdit 仍为历史 FirstToken 结果。','',
'## 4. 真实案例与可核对的变化','',
'| 数据集 × 模型 | Raw 候选 | Tukey 候选 | Raw Best@3 | Tukey Best@3 | 说明 |','|---|---|---|---:|---:|---|',
'| E-VQA × BLIP2 | L0,L1,L3 | L4,L16,L18 | 62.460 | 73.800 | 补齐过滤后提高 11.340；候选由浅层转向更深层 |',
'| MMKE-visual × BLIP2 | L0,L1,L3 | L18,L16,L17 | 69.690 | 71.290 | Best@3 提高 1.600 |',
'| MMKE-visual × SmolVLM | L1,L7,L6 | L6,L8,L5 | 70.770 | 70.322 | 下降 0.448，说明 Tukey 并非每组都会改善 |',
'',
'MMKE-visual × PaliGemma 的 Raw 集合含 main L0 的不收敛实测值；换为 Tukey 后 Mean@3 大幅提高，不能将这个增幅当作正常收敛条件下的普遍提升。该组合的 clean 分析单列，不用 stable 成绩替换失败 main。',
'','## 5. 尚缺的真实编辑结果','',
f"补记并验证 LLaVA × MMKE-entity L9 后，Tukey Top-3 的 63 个组合—层位置中已有 46 个 main 评测，还缺 {S['top3_missing_unique']} 个；Top-5 的 105 个位置中已有 70 个，还缺 {S['top5_missing_unique']} 个。这里按“数据集 × 模型 × 层”计数，不是缺 17/35 个组合。",
'',f"Top-3 缺项中，{new_n} 个是本次相对旧七方法 Top-3 并集新增的层；另外 2 个是历史缺项：E-VQA × PaliGemma L0、MMKE-entity × LLaVA L7。",'',*pending,
'',
'LLaVA × MMKE-entity L9 已找到共享盘正式结果：训练完成 50 epoch，选中 epoch 48，954 条逐样本评测，Average=75.626；已下载 7 个证据文件、核验哈希并重新聚合五项指标，无须重复训练。',
'',
'服务器只读核对范围与时间见 `pending_server_audit.json`：扫描项目共享 server_results，未扫描所有计算节点的 /tmp。缺项表示当前没有取得可验收的 main 评测；不一概认定从未启动训练。E-VQA × PaliGemma L0 找到历史失败目录；E-VQA × InstructBLIP L17 找到归因目录，但没有对应真实编辑完成标记。',
'',
'执行顺序：先补 Top-3 新增的 15 个位置；历史 LLaVA L7 随已有恢复队列核对；PaliGemma L0 优先检查已有 checkpoint 能否按原 main 直接评测，再决定是否需重训；最后处理 Top-5 额外的 18 个缺项。保持各组合原训练配置、训练预算和选点规则，不为 Tukey 调训练参数。当前 g08/g09 已有训练任务，本次没有改动正在运行的队列，也没有启动新增 GPU 训练。',
'','## 6. 文件与复现','',
'- `raw/`、`source_manifest.json`：21 组原始参数分数、summary、候选和 sanity；历史 Raw 保留。',
'- `protocol.json`、`recompute.py`：固定 Tukey 与比较规则、完整复算脚本。',
'- `tukey_audit_21groups.csv`、`parameter_layer_scores_raw_and_tukey.csv`：阈值、76 个异常层、原/新排名。',
'- `candidate_topk_21x8.csv`、`corrected_seven_method_union.csv`：修正后的候选与并集，Raw 单列消融。',
'- `method_metrics.csv`、`paired_comparisons.csv`、`paired_summary.csv`、`same_cohort_method_summary.csv`：完整指标、逐组合配对与相同组合汇总。',
'- `tukey_candidate_execution_status.csv`、`pending_server_audit.json`：每个候选的 main 评测与共享盘核对状态。',
'- `quartile_sensitivity.csv`：固定 kappa=1 下五种分位数实现的敏感性；主结果始终用 linear。',
'- `supplemental_evidence/`、`supplemental_evaluation_verification.json`：新增找到的 L9 真实结果证据。',
'- `verification.json`：独立分位数、排序、指标和源文件哈希复核。',
'',
'复算顺序：在本目录运行 `recompute.py`，再运行 `verify.py`。输入 snapshot 固定，若需要纳入未来新结果，应建立新版本，不静默替换现有快照。']
(H/'LGA_Tukey补正报告.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
plan=['# LGA Tukey 候选待补清单','',f'Top-3 待取得 main 评测：17 个，其中新增 15 个、历史缺项 2 个。Top-5 共缺 35 个（含这 17 个）。', '',*pending,'','注：本次为候选补正与结果复算，未启动 GPU 补跑。不能用 stable 替换 main 缺项。已验证的 MMKE-entity × LLaVA L9 不再列入待补。']
(H/'待补层清单.md').write_text('\n'.join(plan)+'\n',encoding='utf-8')

# Correct documentation without rewriting historical candidate/result tables.
back=H/'manual_backups';back.mkdir(exist_ok=True)
def save(p,s):
    before=p.read_bytes();b=back/p.name
    if not b.exists():b.write_bytes(before)
    p.write_text(s,encoding='utf-8')
def prepend(p,note):
    s=p.read_text(encoding='utf-8-sig')
    if '<!-- LGA_TUKEY_CORRECTION_20260926 -->' in s:return
    first,rest=s.split('\n',1);save(p,first+'\n\n<!-- LGA_TUKEY_CORRECTION_20260926 -->\n'+note+'\n\n'+rest)
newmanual=ROOT/'md/Location/Equations/LGA-Param-Tukey_候选层补正手册_20260926.md'
newmanual.write_text('\n'.join([
'# LGA 参数版：Tukey 候选层补正手册（2026-09-26）','',
'本文件取代历史 LGA 手册中“未经 Tukey 的 raw 排序代表原始 LGA”“Tukey 只作诊断”的规定。旧分数与旧候选保留为 LGA-Param-Raw 消融；补齐过滤后的版本记为 LGA-Param-Tukey（完整名：LGA-Param-Tukey-Direct-AltModelPred）。',
'','## 固定执行规则','',
'1. 沿用历史冻结模型、model_pred/alt、MLP/FFN weight 范围与输入过滤，不重抽样，不更改训练配置。',
'2. 每个模型与数据集内，对全部 finite/ok 层的带符号原始内积分数计算 Q1、Q3；本次固定 linear 分位数，kappa=1。',
'3. IQR=Q3−Q1，剔除 score<Q1−IQR 或 score>Q3+IQR 的层，边界保留。',
'4. 对保留层按分数降序、并列层号升序取 Top-1/3/5，不做 Pre 偏移，不按编辑结果挑选 Raw/Tukey 或阈值。',
'5. 保存 raw_rank、tukey_rank、Q1/Q3/IQR、上下界、异常层及排除原因、样本覆盖、所有原始文件哈希。',
'6. 21 组内部每层样本数相同，均值分数与论文求和分数的筛选与排序等价，已验证。',
'7. 缺少真实编辑评测不填 0；Top-K 全部可比才计算完整指标。main 不收敛实测和 clean 敏感性分别报告；stable 单列。',
'','## 当前执行结果','',
'21/21 定位重算完成，618 条层记录中剔除 76 条；15 组 Top-3/5 改变。Tukey Top-3 尚缺 17 个 main 评测位置，Top-5 尚缺 35 个。这不等于第一阶段真实编辑验证已经全部完成。','',
link(H/'LGA_Tukey补正报告.md','完整报告、候选表和新比较指标')+'；'+link(H/'待补层清单.md','待补层清单')+'。',
'','## 原论文依据与复现范围','',
'[Golden Layers v3 附录 A](https://arxiv.org/html/2602.20207v3#A1) 要求 Tukey 剔除并给出默认常数 1。论文未说明分位插值方式；本次显式固定 linear，另存敏感性结果。本次补齐该步骤，不宣称项目的 VLM adapter 编辑设置与原论文 LLM 参数编辑设置完全相同。',
'','## 执行入口','',
link(H/'recompute.py','复算脚本')+'；'+link(H/'verify.py','独立核验脚本')+'。输入和输出均在本地补正目录；不覆盖原始服务器结果。',
])+'\n',encoding='utf-8')
ref=link(newmanual,'2026-09-26 Tukey 补正手册');rep=link(H/'LGA_Tukey补正报告.md','21 组补正结果')
note='> **LGA 版本更正（2026-09-26）：** 本文件历史 LGA 候选及比较采用未做 Tukey 的 Raw 版本，不能作为完整 LGA 复现。论文要求的 Tukey 过滤已单独补算，当前规则以 '+ref+' 为准，结果见 '+rep+'。旧表保留用于追溯和 Raw 消融；旧的 LGA 优劣结论须按新候选重算。'
guide=ROOT/'md/Location/6edit_layer_localization_candidate_methods_简洁说明版.md';prepend(guide,note)
old=ROOT/'md/Location/Equations/LGA-Param-Direct-AltModelPred_候选层TopK实验手册_修订版.md';prepend(old,note+' **下文未经 Tukey 的执行规定已废止为正式 LGA 规则，仅描述历史 Raw 实验。**')
outcome=ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md';prepend(outcome,note)
s=outcome.read_text(encoding='utf-8')
if '#### 2.4.1 LGA-Param-Tukey 补正' not in s:
    sec='\n#### 2.4.1 LGA-Param-Tukey 补正（2026-09-26）\n\n上方 2.4 为历史 Raw 表。当前 Tukey 版本已完成 21/21 组定位重算；618 条层记录剔除 76 条，15 组候选改变。训练与评测缺项保留，不将定位完成误报为编辑验证完成。\n\n'+'\n'.join(table)+'\n\n同一批 10 组 main 实测（含已评测的不收敛记录，stable 不混入）：\n\n'+'\n'.join(cohort)+'\n\nTukey Top-3 尚缺 17 个 main 评测位置、Top-5 尚缺 35 个。MMKE-entity × LLaVA L9 已核验 954 条评测，Average=75.626，训练 50 epoch、选中 epoch 48，已纳入本次复算。详细训练状态敏感性、定位覆盖、逐组配对和待补清单见 '+rep+'。此前 3.4/3.5 的冻结并集和历史汇总保留原版本；新版并集见补正报告所附 `corrected_seven_method_union.csv`。\n\n'
    assert '### 2.5 Perturb-KL-Direct-AltSeq' in s
    save(outcome,s.replace('### 2.5 Perturb-KL-Direct-AltSeq',sec+'### 2.5 Perturb-KL-Direct-AltSeq',1))
detail=ROOT/'md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md';prepend(detail,note)
s=detail.read_text(encoding='utf-8');a=s.index('### 4.3 MMKE-entity');a=s.index('#### LLaVA-v1.5-7B',a);b=s.find('\n#### ',a+5);b=len(s) if b<0 else b;block=s[a:b]
row='| L9 | main | — | 48 | 0.293750 | 0.323795 | 954 | 60.96 | 60.99 | 60.95 | 100.00 | 95.23 | 75.626 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_VERIFIED_20260926 |'
if not re.search(r'^\| L9 \|',block,re.M):
    ls=block.splitlines();idx=next((i for i,x in enumerate(ls) if re.match(r'^\| L(\d+) \|',x) and int(re.match(r'^\| L(\d+) \|',x)[1])>9),None)
    if idx is None:idx=max(i for i,x in enumerate(ls) if x.startswith('| L'))+1
    ls.insert(idx,row);block='\n'.join(ls)+'\n';save(detail,s[:a]+block+s[b:])
print(json.dumps({'report':str(H/'LGA_Tukey补正报告.md'),'new_manual':str(newmanual),'historical_manuals_annotated':4,'l9_backfilled':True},ensure_ascii=False))
