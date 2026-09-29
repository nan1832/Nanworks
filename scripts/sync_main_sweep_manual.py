"""Synchronize verified sweep ledger results into the main localization manual.

Preserve candidate definitions and frozen method comparisons. Never infer a
current candidate-union denominator. Back up the manual before replacing it.
"""
import argparse
from collections import Counter, defaultdict
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
MANUAL=ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
LEDGER=ROOT/'outputs/sweep_ledger/latest.json'
SWEEP=ROOT/'md/Location/SWeeplayers.md'
DS={'evqa-pilot500':'EVQA-pilot500','mmke-visual':'MMKE-visual','mmke-entity':'MMKE-entity'}
MODELS=['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b','qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']
METRICS=['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']
TZ=dt.timezone(dt.timedelta(hours=8))


def key(r):return (r['dataset'],r['model'],r['layer'],r['recipe'])


def parse(text):
    result={};section=None;ds=None
    for line in text.splitlines():
        if line.startswith('### 4.0 '):section='all'
        if line.startswith('### 4.1 '):section='blip2'
        if line.startswith('### 4.2 '):break
        if line.startswith('#### ') and line[5:].lower() in DS:ds=line[5:].lower()
        if not line.startswith('|'):continue
        c=[x.strip() for x in line.strip('|').split('|')]
        if section=='all' and len(c)==13 and c[0] in MODELS and re.fullmatch(r'L\d+',c[1]):
            if c[2]=='-' or c[11]=='-':continue
            recipe='stable' if 'STABLE' in c[12] else 'main'
            if (ds,c[0],c[1],c[12])==('mmke-visual','paligemma-3b','L8','TRAIN_DONE_MANUAL_EPOCH13'):recipe='stable'
            k=(ds,c[0],int(c[1][1:]),recipe)
            v=dict(epoch=int(c[2]),raw_loss=float(c[3]),ema_loss=float(c[4]),samples=int(c[5]),metrics=dict(zip(METRICS,map(float,c[6:12]))))
        elif section=='blip2' and len(c)==10 and re.fullmatch(r'L\d+(?:-\d+)?',c[0]):
            k=('evqa-pilot500',MODELS[0],int(re.search(r'\d+',c[0])[0]),'main-rerun' if '-' in c[0] else 'main')
            v=dict(epoch=int(c[1]),raw_loss=float(c[2]),ema_loss=float(c[3]),samples=2093,metrics=dict(zip(METRICS,map(float,c[4:]))))
        else:continue
        if k in result:raise ValueError('Duplicate result key: '+str(k))
        result[k]=v
    return result


def verify(text,rows):
    got=parse(text);expected={key(r):r for r in rows}
    assert set(got)==set(expected),(set(expected)-set(got),set(got)-set(expected))
    for k,r in expected.items():
        a=got[k]
        assert a['epoch']==r['epoch'] and a['samples']==r['samples'],k
        assert abs(a['raw_loss']-r['raw_loss'])<1e-6 and abs(a['ema_loss']-r['ema_loss'])<1e-6,k
        assert all(abs(a['metrics'][m]-r['metrics'][m])<.00051 for m in METRICS),k
    return len(got)


def tagged(text,name,body,anchor):
    start='<!-- '+name+'_START -->';end='<!-- '+name+'_END -->'
    block=start+'\n'+body+'\n'+end
    if start in text:
        return re.sub(re.escape(start)+r'.*?'+re.escape(end),lambda _:block,text,count=1,flags=re.S)
    assert anchor in text,anchor
    return text.replace(anchor,anchor+'\n\n'+block,1)


def status(r):
    recipe='STABLE' if r['recipe']=='stable' else 'MAIN'
    old=r.get('original_status') or r['status']
    if r['training']=='50轮已核验':s='TRAIN_DONE_'+recipe+'50_EVAL_DONE'
    elif r['training']=='完成标记；历史未全留存':s='TRAIN_DONE_'+recipe+'_EVAL_DONE_HISTORY_PARTIAL'
    elif r['training']=='恢复/诊断评测':s='EVAL_DONE_'+recipe+'_RECOVERED_TRAIN_BUDGET_NOT_VERIFIED'
    else:return old+'；'+recipe+'_HISTORICAL_ACCEPTANCE'
    if key(r)==('evqa-pilot500','paligemma-3b',0,'main') or 'NONCONVERGENT' in old:s+='_NONCONVERGENT'
    if 'NUMERIC' in old:s+='_NUMERIC_INSTABILITY'
    if 'MANUAL_EPOCH13' in old:s+='_MANUAL_EPOCH13'
    if '选点非现存history最低EMA' in r.get('notes',''):s+='_SELECTION_HISTORY_MISMATCH'
    verified_date=r.get('verified_at','')[:10].replace('-','') or 'DATE_IN_LEDGER'
    return s+'_VERIFIED_'+verified_date


def result_table(rows,model_column=True,status_column=True):
    cols=(['Model'] if model_column else [])+['Layer','Ckpt Epoch','Raw Loss','EMA Loss']+(['Samples'] if model_column else [])+METRICS+(['Train Status'] if status_column else [])
    ls=['| '+' | '.join(cols)+' |','|'+'---|'*len(cols)]
    for r in rows:
        layer='L'+str(r['layer'])+('-2' if r['recipe']=='main-rerun' else '')
        c=([r['model']] if model_column else [])+[layer,str(r['epoch']),f"{r['raw_loss']:.6f}",f"{r['ema_loss']:.6f}"]+([str(r['samples'])] if model_column else [])+[f"{r['metrics'][m]:.3f}" for m in METRICS]+([status(r)] if status_column else [])
        ls.append('| '+' | '.join(c)+' |')
    return '\n'.join(ls)


def replace_table(block,header,replacement):
    lines=block.splitlines();i=next(i for i,l in enumerate(lines) if l==header);j=i
    while j<len(lines) and lines[j].startswith('|'):j+=1
    return '\n'.join(lines[:i]+replacement.splitlines()+lines[j:])+'\n'


def synchronize(ledger_path=LEDGER):
    payload=ledger_path.read_bytes();z=json.loads(payload);rows=z['rows']
    digest=hashlib.sha256(payload).hexdigest();old=MANUAL.read_text(encoding='utf-8');existing=parse(old)
    if '<!-- SWEEP_LEDGER_SHA256:'+digest+' -->' in old:
        verify(old,rows)
        return dict(changed=False,records=len(rows),reason='Already synchronized with the same ledger')
    stamp=dt.datetime.now(TZ).strftime('%Y%m%d_%H%M%S')
    out=ROOT/'outputs'/('main_manual_sweep_sync_'+stamp);out.mkdir(parents=True,exist_ok=False)
    backup=out/'6location_7model_3datas_top_3_5_layers_outcome.before.md'
    backup.write_bytes(MANUAL.read_bytes())
    (out/'SWeeplayers.before.md').write_bytes(SWEEP.read_bytes())
    backup_link='../../'+backup.relative_to(ROOT).as_posix()
    missing=[r for r in rows if key(r) not in existing]
    data_time=z['updated_at'].replace('T',' ')
    head=f"**真实扫层结果已同步：{data_time}（服务器北京时间）。** 本次将核对前遗漏的 {len(missing)} 条补入第 4 节，逐层表现有 {len(rows)} 条记录（main/stable 分开，含独立复测）。当前结果、训练核验状态及逐层来源与 [SWeeplayers.md](SWeeplayers.md) 对齐。第 3 节候选并集及方法统计仍为有日期的历史快照；不据此宣称当前 Top-3 并集总量已确定。"
    text=tagged(old,'SWEEP_MAIN_SYNC_HEADER',head,old.splitlines()[0])
    section4='## 4. 已完成真实扫层结果回填'
    a=text.index(section4);b=text.index('### 4.0 ',a)
    text=text[:a]+section4+'\n\n本节登记各数据集独立完整 eval 的真实层评测，包含 main、stable 和明确标识的恢复/诊断评测。训练是否完成 50 轮、是否收敛与评测是否完成分别判断；不因为未收敛或低分而删除已有评测。方法比较须再固定候选版本及训练口径。\n\n'+text[b:]
    additions=defaultdict(list)
    for r in missing:additions[(r['dataset'],r['model'])].append(r['layer'])
    fresh=sum(r['evidence']=='本次服务器复核' for r in rows)
    block=[f'**最新同步：{data_time}，数据来自最近一次服务器只读核验。**',
           f'<!-- SWEEP_LEDGER_SHA256:{digest} -->','',
           f'核对前逐层表 {len(existing)} 条，本次补入 {len(missing)} 条，现 {len(rows)} 条。main/stable 独立保留，不跨配置挑最高分。台账中 {fresh} 条在该次核验通过并找到实体 checkpoint，其余保留历史证据；不能把全部记录统称为本次重新验收的完整 50 轮。','',
           '当前已登记数量只按真实结果计数，不提供尚未冻结的候选并集分母。','',
           '| Dataset | Model | main 已评测 | stable 已评测 | main 独立复测 |','|---|---|---:|---:|---:|']
    for ds in DS:
        for model in MODELS:
            c=Counter(r['recipe'] for r in rows if r['dataset']==ds and r['model']==model)
            block.append(f"| {DS[ds]} | {model} | {c['main']} | {c['stable']} | {c['main-rerun']} |")
    if missing:
        block+=['','本次漏记层：','', '| Dataset | Model | 新补入逐层记录 |','|---|---|---|']
        for (ds,model),layers in additions.items():block.append(f"| {DS[ds]} | {model} | {','.join('L'+str(l) for l in sorted(layers))} |")
    block+=['',
        '- EVQA/PaliGemma main L0 最新产物覆盖 1–50 轮；仍选 Epoch2（EMA 3209.824510），Average 35.492，仍为高损失未收敛。此前“训练未完成”属于旧快照。',
        '- MMKE-visual/PaliGemma main L0/L3/L5、stable L0 保留恢复评测；stable L8 保留手工 Epoch13 选点的历史身份。',
        '- `MAIN50` / `STABLE50` 表示该次核验覆盖 1–50 轮；`HISTORY_PARTIAL` 表示有训练完成标记但历史未全留存；`RECOVERED` 不冒称预算完整；`HISTORICAL_ACCEPTANCE` 表示继承原登记。',
        '- 最低 EMA 是常规选点规则；EVQA/PaliGemma main L14、MMKE-visual/PaliGemma stable L2/L13 的 selected 与现存 history 最低值不一致，原分数与选点均保留并标注 `SELECTION_HISTORY_MISMATCH`。',
        f'- [逐层来源及核验证据](../../{z["snapshot"]}/ledger.json)；[本次更新前原手册]({backup_link})。台账引用的旧手册行号对应更新前文件，不对应本次移动后的行号。',
        '- [结果图 PNG](../../outputs/completed_layer_results_20260928/completed_layers_average_main_stable.png) / [SVG](../../outputs/completed_layer_results_20260928/completed_layers_average_main_stable.svg)：main/stable 分行，逐格标注版本；图的数据时间以图内标注为准，重画命令为 `python scripts/plot_completed_sweep_results.py`。','',
        '**以下带旧日期的增量说明为历史审计记录；当前逐层状态和数量以上面的汇总及下方更新后的结果表为准。**']
    text=tagged(text,'SWEEP_MAIN_CURRENT_RESULTS','\n'.join(block),'### 4.0 服务器结构化结果总表')
    header='| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |'
    for ds in DS:
        a=text.index('#### '+DS[ds],text.index('### 4.0 '));end=text.find('\n#### ',a+1)
        cap=text.index('\n### 4.1 ',a)
        b=min(end,cap) if end!=-1 else cap
        chunk=text[a:b]
        relevant=[r for r in rows if r['dataset']==ds and not(ds=='evqa-pilot500' and r['model']==MODELS[0])]
        relevant.sort(key=lambda r:(MODELS.index(r['model']),r['recipe'],r['layer']))
        chunk=replace_table(chunk,header,result_table(relevant))
        items=[]
        for model in MODELS:
            c=Counter(r['recipe'] for r in rows if r['dataset']==ds and r['model']==model)
            items.append('`'+model+'` main '+str(c['main'])+' 层'+('、stable '+str(c['stable'])+' 层' if c['stable'] else '')+('、独立复测 '+str(c['main-rerun'])+' 条（见 4.1）' if c['main-rerun'] else ''))
        summary='已登记完整评测（'+z['updated_at'][:10]+'同步）：'+'；'.join(items)+'。这里的“已评测”包括明确列出的恢复/诊断结果，不等同于全部训练收敛或全部完整50轮。'
        chunk=re.sub(r'^(?:完成层数：|已登记完整评测（).*$',lambda _:summary,chunk,count=1,flags=re.M)
        if ds=='evqa-pilot500':
            chunk=re.sub(r'^PaliGemma stable L4/L6.*$',
                'PaliGemma main 与 stable 分别登记。main L0 已有完整50轮历史，但仍未收敛，最低 EMA checkpoint 为 Epoch2，完整2093条评测 Average 35.492。stable L0 当前未登记有效完整评测；其他已登记 stable 层保留其真实分数。',chunk,count=1,flags=re.M)
        text=text[:a]+chunk.rstrip()+'\n'+text[b:]
    a=text.index('### 4.1 ');b=text.index('### 4.2 ',a)
    blip=[r for r in rows if r['dataset']=='evqa-pilot500' and r['model']==MODELS[0]]
    blip.sort(key=lambda r:(r['layer'],r['recipe']))
    small_header='| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |'
    part=replace_table(text[a:b],small_header,result_table(blip,False,False))
    part=part.replace('候选方法回填：','历史候选方法回填示例（保留当时的候选定义与统计，不表示当前方法版本）：')
    text=text[:a]+part.rstrip()+'\n\n'+text[b:]
    a=text.index('### 4.2 ');b=text.index('## 5. ',a)
    instruct=sorted([r for r in rows if r['dataset']=='evqa-pilot500' and r['model']==MODELS[1]],key=lambda r:r['layer'])
    best=max(instruct,key=lambda r:r['metrics']['Average'])
    partial=[r for r in instruct if r['training']=='完成标记；历史未全留存']
    new42=['### 4.2 EVQA-pilot500 / InstructBLIP-Vicuna-7B','',
           '本节已与 4.0 及 SWeeplayers.md 同步，包含全部已登记 main 层，不再只列历史 L26/L27/L28。逐层服务器路径、checkpoint 和核验证据见本次台账；更新前的三层表和旧候选方法示例保存在上方原手册备份。','',
           '- 训练数据：`vqa_train_proxy500.json`；独立评测：`vqa_eval.json`，2093 条。',
           '- 目标训练预算为50轮、按运行选点记录评测；有训练完成标记但历史仅部分留存的层为 '+','.join('L'+str(r['layer']) for r in partial)+'，不将它们写成此次重新验证了完整50轮。',
           '- 当前已登记 main 层：'+','.join('L'+str(r['layer']) for r in instruct)+'。','',
           result_table(instruct,False,True),'',
           f"当前这些已登记层中最高 Average 为 **L{best['layer']} / {best['metrics']['Average']:.3f}**；这不是未完成候选层的上界。",'',
           '方法 Top-K 比较须使用第2节相应版本的真实候选，并对照本节逐层结果检查是否齐全；本次不重新计算未冻结的候选并集或沿用原历史方法示例作为最新结论。','']
    text=text[:a]+'\n'.join(new42)+'\n'+text[b:]
    text=tagged(text,'SWEEP_HISTORICAL_SCOPE',
        '> 当前扫层结果已于 '+z['updated_at'][:10]+' 同步至第4节。本节以下并集完成数、待补状态和方法比较属于原日期冻结记录，不作为当前实时进度；未确定的现行 Top-3 并集不在此次更新中给出总量。',
        '## 3. 数据集分表')
    text=re.sub(r'^- 后续生成重跑队列时.*$',
        '- 后续生成重跑队列时，先以第4.0节当前逐层结果及 SWeeplayers.md 核对已有评测，再参考第3.5节有日期的失败/中断记录；不能直接把历史待补清单作为当前队列。完整训练、恢复评测和 stable 配方须分别判断，避免重复执行已完成层。',text,count=1,flags=re.M)
    count=verify(text,rows)
    # Candidate definition sections must remain byte-for-byte identical in text form.
    assert old[old.index('## 1.'):old.index('## 3.')] == text[text.index('## 1.'):text.index('## 3.')]
    (out/'update.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='before',tofile='after')),encoding='utf-8')
    tmp=MANUAL.with_suffix('.md.sync.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,MANUAL)
    # The preserved notes area survives future sweep-ledger regeneration.
    sweep_text=SWEEP.read_text(encoding='utf-8')
    note='总手册同步状态：第4节已与本台账同步。本文“相对原手册新增”指核对前版本；旧手册行号证据见[更新前备份]('+backup_link+')。后续 `python scripts/update_sweeplayers.py` 会同步更新两份文件。'
    sweep_text=tagged(sweep_text,'SWEEP_MAIN_SYNC_NOTE',note,'<!-- SWEEP_USER_NOTES_START -->')
    temp=SWEEP.with_suffix('.md.sync.tmp');temp.write_text(sweep_text,encoding='utf-8');os.replace(temp,SWEEP)
    report=dict(changed=True,records=count,added=len(missing),updated_at=z['updated_at'],ledger_sha256=digest,
                original_manual_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),updated_manual_sha256=hashlib.sha256(MANUAL.read_bytes()).hexdigest(),
                backup=str(backup),manual=str(MANUAL),added_keys=[list(key(r)) for r in missing])
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ledger',type=Path,default=LEDGER)
    print(json.dumps(synchronize(parser.parse_args().ledger),ensure_ascii=False,indent=2))
