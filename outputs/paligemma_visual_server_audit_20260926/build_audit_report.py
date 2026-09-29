"""Build evidence-linked summaries and reconcile only the audited PaliGemma visual rows."""
from pathlib import Path
import csv,json,hashlib,math,shutil,io
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DL=HERE/'downloaded_results'
records=[json.loads(x) for x in (HERE/'server_records.jsonl').read_text(encoding='utf-8').splitlines() if x.startswith('{')]
old_token='mmke_visual_top3_union_train_eval_7models_20260613_014644'
metrics=['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']
observations=[]

def add(e,recipe,source,hist=None,complete=False):
    assert e['eval_samples']==293
    assert abs(sum(e[k] for k in metrics[:5])/5-e['Average'])<1e-8
    observations.append(dict(recipe=recipe,layer=int(e['layer']),selected_epoch=int(e['ckpt_epoch']),
        raw_loss=float(e['ckpt_loss']),ema_loss=float(e['ckpt_ema_loss']),samples=e['eval_samples'],
        **{k:float(e[k]) for k in metrics},training_complete_50_epochs=complete,
        last_saved_epoch=hist.get('max_epoch','') if hist else '',
        status=e['status'],source=source,checkpoint=e['checkpoint']))

for r in records:
    if r.get('kind')!='layer' or 'eval_full.done' not in r: continue
    source=r['path']; stable='paligemma_stable_' in source
    if stable and not any(x in source for x in ['pending8_job3044208','top3_union_20260713_1120']): continue
    if not stable and old_token not in source and 'formal_top3_live_20260810' not in source: continue
    h=r.get('loss_history',{})
    add(json.loads(r['eval_full.done']['text']),'stable' if stable else 'main',source,h,
        'train.done' in r and h.get('max_epoch')==50)
for r in records:
    if r.get('kind')=='diagnostic_eval':
        e=json.loads(r['text']); stable='stable_l0' in r['path']
        add(e,'stable_l0_lr1e6' if stable else 'main',r['path'],{'max_epoch':25 if stable else 9},False)
for layer in [3,5]:
    p=DL/'main_diagnostic'/f'layer_{layer:02d}'
    e=json.loads((p/'verified_evaluation.json').read_text())
    a=json.loads((p/'selection_audit.json').read_text())
    detail=json.loads((p/'results.json').read_text())
    mean=json.loads((p/'mean_results.json').read_text())
    assert len(detail)==mean['sample_count']==293
    assert not a['nonfinite_parameter_names'] and a['parameter_tensor_count']==26
    assert not e['training_started'] and not e['training_complete_50_epochs']
    add(e,'main',str(p),{'max_epoch':a['last_saved_epoch']},False)
observations.sort(key=lambda r:(r['recipe'],r['layer']))
assert len({(r['recipe'],r['layer']) for r in observations})==len(observations)
main={r['layer']:r for r in observations if r['recipe']=='main'}
stable={r['layer']:r for r in observations if r['recipe']=='stable'}
assert len(main)==16 and sum(r['training_complete_50_epochs'] for r in main.values())==13
with (HERE/'paligemma_visual_observed_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(observations[0]));w.writeheader();w.writerows(observations)
new_layers=[1,2,3,5,6,7,13]
def row_values(r):
    return [str(r['selected_epoch']),f"{r['raw_loss']:.6f}",f"{r['ema_loss']:.6f}",str(r['samples']),
            *[f"{r[k]:.2f}" for k in metrics[:5]],f"{r['Average']:.3f}"]
def ledger_status(l):
    if l in [3,5]: return f"EVAL_DONE_INCOMPLETE_NUMERIC_INSTABILITY_MAIN_RECOVERED_20260926；已保存{main[l]['last_saved_epoch']}轮，非完整50epoch"
    return 'TRAIN_DONE_MAIN_BACKFILLED_20260926；完整50epoch，有历史非有限梯度记录'

# Back up the exact pre-edit files, preserving all unrelated user changes.
ledger=ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
direct=ROOT/'md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md'
older=ROOT/'outputs/main_formula_validation_20260925/PaliGemma主配置异常与stable可比性核验.md'
backup=HERE/'before_backfill';backup.mkdir(exist_ok=True)
for f in [ledger,direct,older]:
    if not (backup/f.name).exists(): shutil.copy2(f,backup/f.name)

t=ledger.read_text(encoding='utf-8')
start=t.index('#### MMKE-visual'); end=t.find('\n#### ',start+5)
if end<0: end=len(t)
s=t[start:end]
marker='2026-09-26 服务器复核与 main 恢复评测'
note=(f'**{marker}：** main 原运行的 L1、L2、L6、L7、L13 已有完整50轮及293条评测，本次补齐漏记；'
      'L3、L5 原训练发生非有限梯度并被停滞监控终止，现已直接评测原 checkpoint，分别为30.540、62.544。'
      '当前 main 共16层有实际评测，其中13层训练完成50轮，L0/L3/L5为训练未完成的恢复评测。'
      '“已评测”不等于“已收敛”或“完成50轮”。stable 单列保留，不再以 stable 高分替换 main 低分；'
      '先前其他章节的覆盖统计属于历史快照，不据此自动增加完整50轮可比组数。'
      '详情见 `outputs/paligemma_visual_server_audit_20260926/PaliGemma_main停训原因与直接评测结果.md`。\n\n')
if marker not in s: s=s.replace('#### MMKE-visual\n\n','#### MMKE-visual\n\n'+note,1)
s=s.replace('`paligemma-3b` 15 个唯一完成层（新增主配置L4；另有 `L0` 未收敛失败，不计入完成）',
            '`paligemma-3b` main有16个已评测层，其中13层完整50轮、L0/L3/L5为未完成训练的恢复评测；stable另列，不能混成一个完成数')
s=s.replace('PaliGemma 待补跑层验收规则：优先按主实验配置运行，若训练完整完成、loss/EMA 无极端异常、未出现 nonfinite 梯度或长时间卡死，并且 full eval 通过，则保留为主实验结果；若出现 nonfinite、极端/负 EMA、卡死或无法评测，则该层标记为主配置失败，改按 PaliGemma-stable 方案补跑，并在 `Train Status` 或备注中注明结果来源。',
'''PaliGemma 当前记录规则（2026-09-26，按用户要求更新）：保留原 main 训练轨迹与实际评测分数。出现数值异常或中断时，只要原 checkpoint 参数有限且可读取，即可按原评测协议直接评测，并明确标注训练预算完成情况；不能把低分、失败或中断静默删除，也不以 stable 分数替换。历史 stable 作为单独配方结果保留。所有定位公式必须复用同一个固定层—结果映射。完整50轮分析与包含失败/中断恢复结果的实际运行分析分别统计。''')
if 'TRAIN_DONE_MAIN_BACKFILLED_20260926' not in s:
    rows=['| '+' | '.join(['paligemma-3b',f'L{l}',*row_values(main[l]),ledger_status(l)])+' |' for l in new_layers]
    anchor='| paligemma-3b | L4 | 39 |'
    pos=s.index(anchor);s=s[:pos]+'\n'.join(rows)+'\n'+s[pos:]
t=t[:start]+s+t[end:];ledger.write_text(t,encoding='utf-8')

t=direct.read_text(encoding='utf-8')
# Locate the visual block by its existing layer-4 main result, not other datasets' heading.
anchor='| L4 | main | Top-3 | 39 | 0.332606 | 0.330234 | 293 |'
pos=t.index(anchor);start=t.rfind('#### PaliGemma-3B',0,pos);end=t.index('\n#### ',pos)
s=t[start:end]
if marker not in s:
    s=s.replace('Ours Top-1：`L5`；Top-3：`L5,L4,L3`。',
       'Ours Top-1：`L5`；Top-3：`L5,L4,L3`。\n\n'+note.strip(),1)
    rows=[]
    for l in [0,*new_layers]:
        status=ledger_status(l) if l else 'EVAL_DONE_NONCONVERGENT_MAIN_RECOVERED_20260921；非完整50epoch'
        ours='Top-1' if l==5 else 'Top-3' if l==3 else '—'
        rows.append('| '+' | '.join([f'L{l}','main',ours,*row_values(main[l]),status])+' |')
    pos=s.index('| L0 | stable |')
    s=s[:pos]+'\n'.join(rows)+'\n'+s[pos:]
s=s.replace('| L8 | main/legacy | — | 13 |','| L8 | stable | — | 13 |')
t=t[:start]+s+t[end:];direct.write_text(t,encoding='utf-8')

notice=('> **2026-09-26 服务器复核更正：** 本文原结论基于本地归档，现已找到 main L3/L5 原 checkpoint，'
        '并完成293条直接评测（30.540/62.544），另补回漏记的 main L1/L2/L6/L7/L13。'
        '本轮采用原 main 实际结果，无需为了补齐分数改跑 stable L4。L3/L5仍标注训练中断，不能计作完整50轮。'
        '下文保留为历史判断，涉及缺失层和补跑建议以 '
        '[最新服务器核验报告](../paligemma_visual_server_audit_20260926/PaliGemma_main停训原因与直接评测结果.md) 为准。\n\n')
t=older.read_text(encoding='utf-8')
if '2026-09-26 服务器复核更正' not in t:
    i=t.index('\n')+1;t=t[:i]+'\n'+notice+t[i:];older.write_text(t,encoding='utf-8')

def table(layers):
    header='| 层 | main Average | stable Average | stable − main | main 训练记录 |\n|---|---:|---:|---:|---|\n'
    return header+'\n'.join(f"| L{l} | {main[l]['Average']:.3f} | {stable[l]['Average']:.3f} | {stable[l]['Average']-main[l]['Average']:+.3f} | {'完整50轮' if main[l]['training_complete_50_epochs'] else str(main[l]['last_saved_epoch'])+'轮保存记录，随后中断'} |" for l in layers)
run=json.loads((DL/'main_diagnostic/root/status.json').read_text())
assert run['state']=='EVAL_DONE' and run['training_started'] is False
mean3=sum(main[l]['Average'] for l in [3,4,5])/3
report=f'''# MMKE-visual × PaliGemma：main 停训原因、stable 可比性与直接评测

核验日期：2026-09-26（北京时间）。本轮实际连接服务器读取原始训练/控制日志、逐轮损失、checkpoint、配置与评测文件，并对原 main L3/L5 执行评测；没有重训、续训或修改原 checkpoint。完成时间：{run['time']}。

## 1. 结论与此前判断的纠正

**无需整个组合重跑。** 原 main L3、L5 并非没有训练产物，而是训练中断后未生成自动选点文件，控制脚本因此跳过评测。本轮直接从各自原运行中选择最低有限 EMA 的现存 checkpoint，检查全部26个参数张量均为有限值后，完成每层293条独立评测。

此前“只有 stable L3/L5，因此应补 stable L4”的建议基于不完整的本地台账，现予以更正。用户要求保留原 main 实际表现，本轮按此执行。服务器另有 main L1、L2、L6、L7、L13 的完整训练与评测，本次一并补回两份本地台账。

当前 main 有16个已评测层：L0–L14及L17。其中13层有完整50轮训练记录；L0、L3、L5为未完成训练的恢复评测。完成50轮也不自动代表有效收敛。不能把这个组合不加说明地计入“全部候选均完成50轮”的组数。

## 2. main L3/L5 为什么没有正常完成

| 项目 | L3 | L5 |
|---|---|---|
| 原配置学习率 | 1e-4 | 1e-4 |
| 已保存训练轮数 | 27 | 3 |
| 最后可见训练位置 | epoch28，60/214 | epoch4，16/214 |
| `SANITIZE_NONFINITE_GRAD_BEFORE_STEP` 日志出现次数 | 49 | 7 |
| 非有限梯度证据 | `mlp_begin.weight`，2097152/2097152 | 同左 |
| 控制脚本停止原因 | `over_2h_stale_log_nonfinite_or_no_progress` | `over_2h_stale_log_nonfinite` |
| 停止时间 | 2026-07-14 17:30:30 | 2026-07-14 11:21:08 |
| 训练退出码 | 143 | 143 |
| 原自动评测情况 | `EVAL_NOT_RUN`，`selected_exists=0` | 同左 |

原始记录说明两层出现数值异常与长时间不推进，随后被停滞控制逻辑终止；退出码143与终止信号相符。`selected_exists=0` 是没有自动选定 checkpoint 的索引文件，不能解读为没有保存任何权重。所核对两份训练日志没有 CUDA OOM 记录。

这些证据支持“数值异常伴随停滞，触发停止”这一判断；尚不足以定位首次产生 NaN/Inf 的算子，也不能证明唯一原因就是学习率。main L4 已完整50轮且 Average=99.026，不能概括为整个 PaliGemma main 都跑不通。旧 L7 曾出现写盘/停滞故障，但后来已有完整50轮与评测，不能仅根据早期故障排除它。

## 3. 已直接完成的 main 评测

| 层 | 选中 epoch | EMA | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 样本数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
'''
for l in [3,4,5]:
    r=main[l]
    report+='| '+' | '.join([f'L{l}',str(r['selected_epoch']),f"{r['ema_loss']:.6f}",*[f"{r[k]:.3f}" for k in metrics],str(r['samples'])])+' |\n'
report+=f'''
L3/L5 是本轮直接评测；L4 是已存在的完整训练结果。本轮保持 main YAML、模型精度、293条评测数据和现有评测逻辑，使用 `--skip-train`。选点依据原训练 EMA，未根据测试成绩择优。两层 checkpoint 哈希在评测前后相同，依赖代码哈希在评测期间未变。

L3 的 M-Loc 只有3.07，说明该权重除编辑表现弱外，视觉局部性也受损；L5 的 M-Loc 为45.39。保留这些真实低分比用 stable 高分替换更能反映原运行表现。选中第7/第1轮只是 checkpoint 位置，训练轨迹分别已有27/3轮保存记录；二者都不能写成50轮完成。

## 4. stable 是否影响结果，能否与 main 比较

**会影响，而且现有实验已显示很大差异。** main 与普通 stable 的学习率分别为1e-4、1e-5。stable wrapper 还改变标签/KL等损失的 FP32 计算和非有限值处理、异常更新跳过、梯度裁剪（普通配置默认阈值1.0），以及 checkpoint 过滤规则。因此它不是仅改变命名，也不只是评测阶段的修补。

{table([1,2,3,5,6,7,10,13])}

表中都是同一模型、同一 MMKE-visual 293条评测口径的已观察结果。它们不是“只改变学习率”的受控重复实验，因此不能把差值全部归因于某一个配置项。L3/L5还存在训练完成预算不同的影响；main L1/L2/L13已经训练50轮仍与 stable 相差很大，所以差异不能仅用提前停训解释。L10的 stable 略低，也不能断言 stable 必然更好。

可以比较的结论层级：

1. **报告整套系统表现：可以并列表达。** 明确标注模型、训练配方、预算完成情况与同一评测集；它回答不同完整方案表现如何。
2. **比较同一模型内的定位公式：各公式应共享一套固定逐层结果。** 不能给某个公式使用 stable 分数、给另一个使用 main，不能逐层挑两种配方的高分。评测集相同不能消除训练配方影响。
3. **不同模型采用不同固定配方：可采用公开说明的模型适配协议。** 但该模型内各定位方法必须面对同一配方，结论是该编辑协议下定位表现；不能把差异只归于公式或模型架构。
4. **本次按原运行保留失败/中断：可以分析实际执行结果。** 同时报完整50轮覆盖率与数值失败/中断标志；这不是所有层严格等训练步数的受控实验。无需为了让公式显得更好而修成 stable。

目前不需要为了补齐 main 分数再跑 stable L4。如果另行研究“全部候选层使用统一 stable 配方”的效果，才需要补齐对应 stable 候选范围，那是另一项实验。

## 5. 对当前两个公式的直接含义

旧主公式 Top-3 为L5/L4/L3，纯新梯度范数 Top-3 为L4/L5/L3，集合相同。在这次保留中断结果的 main 实际运行表里，两者 Best@3均为99.026，Mean@3均为{mean3:.6f}；同一参照池下 Regret@3/Hit@3也不会因顺序不同产生差异。

Top-1 则不同：旧主公式 L5=62.544，纯新梯度范数 L4=99.026。因此这组实际结果不能作为旧主公式方向项优于纯范数的证据。该比较包含L3/L5训练中断，不将其包装成完整50轮的独立确认实验。

## 6. 证据、复现与回填

- `server_records.jsonl`：服务器原始层记录、损失历史摘要、配置、训练异常计数；`controller_records.jsonl`：停止原因与退出码。
- `download_manifest.json`：65个下载文件的服务器路径、本地路径、大小和 SHA-256；下载内容逐一通过哈希验证。
- `downloaded_results/main_diagnostic/layer_03/`、`layer_05/`：完整293条逐样本结果、均值、原配置、损失历史、选点审计和验收标记。
- `downloaded_results/main_original/`：此前漏记的L1/L2/L6/L7/L13评测与训练证据。
- `downloaded_results/main_diagnostic/root/protocol.json`：数据与代码哈希、原 checkpoint 哈希、评测命令和资源记录。输出目录中的 runner 默认 `epochs=50` 不代表训练过50轮：此次 `skip_train=true`，真实训练情况以原损失历史与选点审计为准。
- `paligemma_visual_observed_results.csv`：main、普通stable和L0特殊stable明确分开的机器可读结果，附训练完成标志、来源路径；不把配置混成一个成绩池。
- 已回填 `md/Location/6location_7model_3datas_top_3_5_layers_outcome.md`、`md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md`，并纠正后者 stable L8 被误写为main/legacy的问题。改前备份保存在 `before_backfill/`。
- 2026-09-25 的旧判断报告已加本次更正说明。此前公式筛选统计保留为原冻结快照，本轮没有把新结果静默塞入旧组数/胜率。

服务器新结果位置：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/paligemma_visual_main_nonconvergent_eval_20260926`。原 checkpoint 与原训练目录保持原样。
'''
(HERE/'PaliGemma_main停训原因与直接评测结果.md').write_text(report,encoding='utf-8')
print(json.dumps(dict(main_layers=len(main),main_full50=sum(x['training_complete_50_epochs'] for x in main.values()),
    main_diagnostic=[l for l,r in main.items() if not r['training_complete_50_epochs']],
    new_eval={l:main[l]['Average'] for l in [3,5]},best3=main[4]['Average'],mean3=mean3,observations=len(observations)),ensure_ascii=False))
