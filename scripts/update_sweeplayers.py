"""Refresh the local sweep ledger from read-only SSH evidence (Python stdlib only).

Run from any directory: python scripts/update_sweeplayers.py
Replay a saved audit:  python scripts/update_sweeplayers.py --from-snapshot outputs/sweep_ledger_20260928
No remote file writes, training, evaluations, cleanup, or scheduled tasks are performed.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
TARGET = ROOT/'md/Location/SWeeplayers.md'
STATE = ROOT/'outputs/sweep_ledger/latest.json'
SHARED = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results'
DS = {'evqa-pilot500': 'EVQA-pilot500', 'mmke-visual': 'MMKE-visual', 'mmke-entity': 'MMKE-entity'}
MODELS = ['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b',
          'qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']
EXPECTED = dict(zip(DS, [2093,293,954]))
METRICS = ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']
TZ = dt.timezone(dt.timedelta(hours=8))


def now():
    return dt.datetime.now(TZ).isoformat(timespec='seconds')


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def key(r):
    return (r['dataset'], r['model'], int(r['layer']), r['recipe'])


def priority(x):
    return ('/accepted/' in x['path'], x['host']=='login01', '/resume_handoffs/' not in x['path'],
            x.get('artifacts',{}).get('eval_full.done',{}).get('mtime',''))


def baseline():
    rows = {}
    dataset = None
    section = None
    for lineno, line in enumerate(MANUAL.read_text(encoding='utf-8').splitlines(),1):
        if line.startswith('### 4.0 '): section='main'
        if line.startswith('### 4.1 '): section='blip2'
        if line.startswith('### 4.2 '): break
        if line.startswith('#### ') and line[5:].lower() in DS:
            dataset=line[5:].lower()
        if not line.startswith('|'):
            continue
        c=[s.strip() for s in line.strip('|').split('|')]
        if section=='main' and dataset and len(c)==13 and c[0] in MODELS and re.fullmatch(r'L\d+',c[1]):
            try:
                metrics={m:float(v) for m,v in zip(METRICS,c[6:12])}
                r=dict(dataset=dataset,model=c[0],layer=int(c[1][1:]),recipe='stable' if 'STABLE' in c[12] else 'main',
                       epoch=int(c[2]),raw_loss=float(c[3]),ema_loss=float(c[4]),samples=int(c[5]),metrics=metrics,
                       status=c[12],evidence='历史登记',training='历史验收',source=f'{MANUAL.name}:{lineno}',original_status=c[12])
            except ValueError:
                continue
            # This row sits in the stable block but its old status omitted STABLE.
            # The server stable run independently matches Epoch13 and all metrics.
            if (dataset,c[0],c[1],c[12])==('mmke-visual','paligemma-3b','L8','TRAIN_DONE_MANUAL_EPOCH13'):
                r['recipe']='stable'
            if any(w in c[12] for w in ['INCOMPLETE','RECOVERED','DIAGNOSTIC','NONCONVERGENT']):
                r['training']='恢复/诊断评测'
            if 'MAIN50' in c[12] or 'STABLE50' in c[12]:
                r['training']='50轮已核验'
            elif 'HISTORY_PARTIAL' in c[12]:
                r['training']='完成标记；历史未全留存'
            if not all(math.isfinite(v) for v in metrics.values()):
                continue
            if key(r) in rows:
                raise ValueError('Duplicate baseline key: '+str(key(r)))
            rows[key(r)]=r
        elif section=='blip2' and len(c)==10 and re.fullmatch(r'L\d+(?:-\d+)?',c[0]):
            layer=int(re.findall(r'\d+',c[0])[0])
            r=dict(dataset='evqa-pilot500',model=MODELS[0],layer=layer,recipe='main' if '-' not in c[0] else 'main-rerun',
                   epoch=int(c[1]),raw_loss=float(c[2]),ema_loss=float(c[3]),samples=2093,
                   metrics={m:float(v) for m,v in zip(METRICS,c[4:])},status='HISTORICAL_BLIP2',
                   evidence='历史登记',training='历史验收',source=f'{MANUAL.name}:{lineno}',original_status='HISTORICAL_BLIP2')
            rows[key(r)]=r
    if len(rows)<300:
        raise ValueError('Baseline parser found too few rows; refusing to rewrite ledger')
    return rows


def ssh_run(code, host, host_alias, key_file, timeout=600):
    cmd=['ssh.exe' if os.name=='nt' else 'ssh','-i',str(key_file),'-o','BatchMode=yes','-o','ConnectTimeout=15',host_alias]
    if host!='login01':cmd+=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12',host]
    cmd+=['python3','-']
    r=subprocess.run(cmd,input=code.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,
                     **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
    if r.returncode:raise RuntimeError(host+': '+r.stderr.decode('utf-8','replace'))
    return r.stdout, r.stderr


def collect(out,args):
    source=(ROOT/'scripts/audit_sweep_results_remote.py').read_text(encoding='utf-8')
    def scan(h,roots):
        stdout,stderr=ssh_run('AUDIT_ROOTS='+repr(roots)+'\n'+source,h,args.host,args.key)
        z=json.loads(stdout)
        save(out/(h+'_inventory.json'),z)
        (out/(h+'.stderr.txt')).write_bytes(stderr)
        if z['errors']:raise RuntimeError('Incomplete inventory: '+str(z['errors']))
        print(h+': inventoried '+str(len(z['layers']))+' layer directories',flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(scan,'login01',[SHARED,'/var/tmp/ph_teacher3']),pool.submit(scan,'g08',['/tmp/ph_teacher3']),pool.submit(scan,'g09',['/tmp/ph_teacher3'])]
        for job in jobs:job.result()
    allrows=[x for h in ['login01','g08','g09'] for x in json.loads((out/(h+'_inventory.json')).read_text(encoding='utf-8'))['layers']]
    choices={}
    for x in allrows:
        e=x.get('evaluation')
        if not e or x['dataset'] not in DS or x['model'] not in MODELS or not x.get('selected'):continue
        if int(e.get('eval_samples',0))!=EXPECTED[x['dataset']]:continue
        sig=key(x)+(str(e.get('ckpt_epoch')),str(e.get('ckpt_i')),tuple(round(float(e.get(m,-999)),3) for m in METRICS[:5]))
        if sig not in choices or priority(x)>priority(choices[sig]):choices[sig]=x
    selected=list(choices.values())
    save(out/'verification_inputs.json',selected)
    code=(ROOT/'scripts/verify_sweep_results_remote.py').read_text(encoding='utf-8')
    def verify(h):
        items=[{k:x[k] for k in ['path','dataset','model','layer']} for x in selected if x['host']==h]
        if not items:return
        stdout,stderr=ssh_run('VERIFY_ITEMS='+repr(items)+'\n'+code,h,args.host,args.key)
        (out/(h+'_verified.jsonl')).write_bytes(stdout)
        (out/(h+'_verified.stderr.txt')).write_bytes(stderr)
        parsed=[json.loads(l) for l in stdout.splitlines()]
        if len(parsed)!=len(items):raise RuntimeError('Truncated verification output')
        print(h+': verified '+str(len(items))+' result sets',flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for j in [pool.submit(verify,h) for h in sorted({x['host'] for x in selected})]:j.result()
    clock_code="import datetime,json; print(json.dumps({'server_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')}))"
    stdout,_=ssh_run(clock_code,'login01',args.host,args.key)
    save(out/'collection_completed.json',dict(json.loads(stdout),local_time=now()))


def metrics_match(a,b):
    # Historical tables often display Average at only two decimals.
    return all(abs(float(a[m])-float(b[m]))<=.011 for m in METRICS)


def build(out):
    original=baseline()
    baseline_copy=out/'source_manual_before_update.md'
    if not baseline_copy.exists():baseline_copy.write_bytes(MANUAL.read_bytes())
    rows={k:dict(v) for k,v in original.items()}
    previous=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else None
    if previous:
        for r in previous['rows']:
            rows[key(r)]=dict(r, evidence='前次核验留存')
    inputs=json.loads((out/'verification_inputs.json').read_text(encoding='utf-8'))
    checks={}
    for p in sorted(out.glob('*_verified.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            v=json.loads(line);checks[(v['host'],v['path'])]=v
    if len(checks)!=len(inputs):
        raise ValueError('Verification incomplete: '+str((len(checks),len(inputs))))
    candidates=defaultdict(list)
    issues=[]
    for x in inputs:
        v=checks[(x['host'],x['path'])]
        if any(token in x['path'].lower() for token in ['fullevqa', 'fulltrain']):
            continue
        if 'blip2_pilot500_visedit_sweep_L18_2_' in x['path'] and x['layer']==18:
            x['recipe']='main-rerun'
        candidates[key(x)].append((x,v))
        if v['errors'] or v['warnings']:
            issues.append(dict(dataset=x['dataset'],model=x['model'],layer=x['layer'],recipe=x['recipe'],
                               path=x['path'],errors=v['errors'],warnings=v['warnings']))
    added=[];conflicts=[]
    for k, possibilities in candidates.items():
        valid=[(x,v) for x,v in possibilities if v['evaluation_verified'] and v.get('checkpoint',{}).get('size',0)>0]
        if not valid:continue
        prior=rows.get(k)
        matching=[(x,v) for x,v in valid if prior and metrics_match(prior['metrics'],v['evaluation'])]
        pool=matching if matching else valid
        if prior and not matching:
            conflicts.append(dict(key=list(k),historical_metrics=prior['metrics'],alternatives=[dict(path=x['path'],metrics={m:v['evaluation'][m] for m in METRICS}) for x,v in valid]))
            continue
        # Keep divergent reruns visible, never choose a layer by its highest score.
        if not prior and any(not metrics_match(valid[0][1]['evaluation'],v['evaluation']) for _,v in valid[1:]):
            conflicts.append(dict(key=list(k),alternatives=[dict(path=x['path'],metrics={m:v['evaluation'][m] for m in METRICS}) for x,v in valid]))
            continue
        x,v=max(pool,key=lambda pair:priority(pair[0]))
        e=v['evaluation'];s=v['selected']
        full50=v.get('train_done') and v.get('all_50_epochs_present')
        training='50轮已核验' if full50 else ('完成标记；历史未全留存' if v.get('train_done') else '恢复/诊断评测')
        notes=[]
        if v.get('minimum_ema_matches') is False:
            notes.append('选点非现存history最低EMA')
        if k[:3]==('evqa-pilot500','paligemma-3b',0):
            notes.append('高损失未收敛；旧Epoch2诊断记录保留在原手册')
        if prior and prior.get('original_status'):
            old_status=prior['original_status']
        else:old_status=''
        r=dict(dataset=k[0],model=k[1],layer=k[2],recipe=k[3],epoch=int(s['epoch']),raw_loss=float(s['loss']),
               ema_loss=float(s['ema_loss']),samples=int(e['eval_samples']),metrics={m:float(e[m]) for m in METRICS},
               status='TRAIN_DONE_EVAL_DONE' if v.get('train_done') else 'RECOVERED_EVAL_DONE',evidence='本次服务器复核',
               training=training,source=x['path'],host=x['host'],original_status=old_status,notes='；'.join(notes),
               verified_at=now(),eval_modified=x['artifacts']['eval_full.done']['mtime'],verification=v,
               baseline_source=prior.get('baseline_source',prior.get('source','')) if prior else '')
        rows[k]=r
        if k not in original:added.append(r)
        # The input JSON preserves exact metadata text and source SHA-256. Avoid
        # producing thousands of redundant local files on every refresh.
        for name,a in x['artifacts'].items():
            if Path(name).name!=name:raise ValueError('Unsafe artifact name')
            data=a['text'].encode('utf-8')
            if hashlib.sha256(data).hexdigest()!=a['sha256']:raise ValueError('Metadata hash mismatch')
        r['local_evidence']=(out/'verification_inputs.json').relative_to(ROOT).as_posix()
    inventories=[json.loads((out/(h+'_inventory.json')).read_text(encoding='utf-8')) for h in ['login01','g08','g09']]
    pending={}
    for inv in inventories:
        for x in inv['layers']:
            if x['dataset'] not in DS or x['model'] not in MODELS or x.get('evaluation'):continue
            k=key(x)
            if k in rows:continue
            mtime=x['artifacts'].get('loss_history.csv',{}).get('mtime','')
            if not mtime or mtime<pending.get(k,{}).get('mtime',''):continue
            epochs=x.get('history',{}).get('epochs',[])
            pending[k]=dict(dataset=k[0],model=k[1],layer=k[2],recipe=k[3],max_epoch=max(epochs,default=0),
                            mtime=mtime,source=x['path'],status='有训练产物，未发现完整评测；不推断当前是否运行')
    clockfile=out/'collection_completed.json'
    clockinfo=json.loads(clockfile.read_text(encoding='utf-8')) if clockfile.exists() else {}
    server_time=clockinfo.get('server_time',max(i['finished'] for i in inventories))
    result=dict(updated_at=server_time,local_written_at=now(),clock_source='login01 server UTC+08:00',audit_started=min(i['started'] for i in inventories),audit_finished=max(i['finished'] for i in inventories),
                snapshot=out.relative_to(ROOT).as_posix(),baseline_sha256=hashlib.sha256(MANUAL.read_bytes()).hexdigest(),
                baseline_rows=len(original),rows=sorted(rows.values(),key=lambda r:(list(DS).index(r['dataset']),MODELS.index(r['model']),r['recipe'],r['layer'])),
                added_vs_original=[list(k) for k in rows if k not in original],issues=issues,conflicts=conflicts,pending=list(pending.values()),
                queue=inventories[0].get('queue',''),previous_snapshot=previous.get('snapshot') if previous else None)
    if previous:
        prev_keys={key(r) for r in previous['rows']}
        result['added_vs_previous']=[list(key(r)) for r in result['rows'] if key(r) not in prev_keys]
    else:result['added_vs_previous']=result['added_vs_original']
    return result


def layerlist(rows):
    return ','.join('L'+str(x) for x in sorted({int(r['layer']) for r in rows})) or '—'


def fmt(v, digits=3):
    return f'{float(v):.{digits}f}'


def render(z):
    rs=z['rows'];addkeys={tuple(k) for k in z['added_vs_original']}
    added=[r for r in rs if key(r) in addkeys]
    fresh=[r for r in rs if r['evidence']=='本次服务器复核']
    full=[r for r in fresh if r['training']=='50轮已核验']
    snapshot='../../'+z['snapshot']
    lines=['# 服务器真实扫层结果台账','',
           f"**更新时间：{z['updated_at']}（北京时间，UTC+08:00；以服务器时钟为准）**",'',
           f"服务器目录扫描时间：{z['audit_started']} 至 {z['audit_finished']}。随后逐层复核独立评测原件，完成后写入本文件。",'',
           f"本地文件生成时间：{z['local_written_at']}（本机时钟）。本机与服务器时钟可能有偏差，服务器结果时间以上述服务器记录为准。",'',
           f'核对基线为本次更新前的总手册第 4.0、4.1 节；[更新前快照]({snapshot}/source_manual_before_update.md)保留原行号。[总手册](6location_7model_3datas_top_3_5_layers_outcome.md)的当前结果表随后与本台账同步，候选方法、冻结并集及历史排名保持原样。', '',
           f"本台账共 **{len(rs)} 条结果记录**（按数据集 × 模型 × 层 × 配方区分，含 stable 与一次 BLIP2 L18 复测）。相对本次核对前的总手册逐层表补入 **{len(added)} 条漏记结果**。本次服务器原件复核通过并找到实体 checkpoint 的登记记录 **{len(fresh)} 条**，其中 **{len(full)} 条**同时具备 1–50 轮历史；其余 **{len(rs)-len(fresh)} 条**保留历史/前次登记，未冒充本次全量验收。",'',
           '## 1. 记录口径','',
           '- 层号为 0-indexed。EVQA-pilot500 / MMKE-visual / MMKE-entity 的独立评测样本数分别为 2093 / 293 / 954。',
           '- 本次新增条目要求：非空 selected_checkpoint.tsv、eval_full.done、完整逐样本 results.json、可定位的实体 checkpoint；交叉核对选点、样本数、五项指标与 Average。训练完成状态单独记录。',
           '- “50轮已核验”要求 train.done 存在且 loss_history.csv 覆盖 1–50 轮；“完成标记；历史未全留存”表示训练完成标记存在，但保留的历史不足以重新证明全部 50 轮；“恢复/诊断评测”不算完整训练验收。表中 Epoch 是选中 checkpoint 轮次。',
           '- main、stable 与复测分开登记；训练预算完成不表示收敛。不同运行分数不按高低择优替换。未评测层不记零分，重复归档不重复计数。',
           '- Average 沿用原评测定义，为 Rel、T-Gen、M-Gen、T-Loc、M-Loc 五项均值；Markdown 保留三位小数，CSV/JSON 保留服务器精度。',
           '- 本次仅只读扫描服务器共享结果根、login01 的 /var/tmp/ph_teacher3、G08/G09 的 /tmp/ph_teacher3；不解包历史压缩档案，不启动训练/评测，不改动服务器文件。', '',
           f"[本次机器可读台账]({snapshot}/ledger.json) · [逐层 CSV]({snapshot}/sweep_results.csv) · [核验问题清单]({snapshot}/audit_issues.json)", '',
           '## 2. 相对原手册新增的逐层结果','',
           '以下是原手册逐层明细缺少、此次从服务器原件补入的记录。既有条目的状态变化另见第 4 节。','']
    def table(rows, extra=True):
        h='| 数据集 | 模型 | 层 | 配方 | Epoch | Raw loss | EMA loss | N | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 训练核对 | 证据 |'
        if not extra:h='| 模型 | 层 | 配方 | Epoch | Raw loss | EMA loss | N | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 训练核对 | 证据 |'
        result=[h,'|'+'---|'*(16 if extra else 15)]
        for r in rows:
            evidence='本次' if r['evidence']=='本次服务器复核' else '历史/前次'
            sid=source_ids[r['source']]
            cells=([DS[r['dataset']]] if extra else [])+[r['model'],'L'+str(r['layer']),r['recipe'],str(r['epoch']),fmt(r['raw_loss'],6),fmt(r['ema_loss'],6),str(r['samples'])]+[fmt(r['metrics'][m]) for m in METRICS]+[r['training'],f'{evidence} [S{sid}](#source-{sid})']
            result.append('| '+' | '.join(cells)+' |')
        return result
    source_ids={s:i+1 for i,s in enumerate(sorted({r['source'] for r in rs}))}
    lines+=table(added)+['','## 3. 21 组组合的实际记录数','',
            '这里统计已登记的真实层结果，不使用过期的候选并集分母；main 包括明确标注的恢复/诊断评测。stable 与 main 重合的层分别列出，不合并为正式 main 完成数。', '',
            '| 数据集 | 模型 | main 已登记 | 本次 main 复核通过 | 本次 main 50轮历史齐全 | stable 已登记 | main 已登记层 |',
            '|---|---|---:|---:|---:|---:|---|']
    for ds in DS:
        for model in MODELS:
            main=[r for r in rs if r['dataset']==ds and r['model']==model and r['recipe']=='main']
            stable=[r for r in rs if r['dataset']==ds and r['model']==model and r['recipe']=='stable']
            verified=[r for r in main if r['evidence']=='本次服务器复核']
            lines.append(f"| {DS[ds]} | {model} | {len(main)} | {len(verified)} | {sum(r['training']=='50轮已核验' for r in verified)} | {len(stable)} | {layerlist(main)} |")
    lines+=['','## 4. 状态变化与核验边界','']
    pali=next(r for r in rs if key(r)==('evqa-pilot500','paligemma-3b',0,'main'))
    if pali['evidence']=='本次服务器复核' and pali['training']=='50轮已核验':
        lines+=[f"- **EVQA / PaliGemma L0：** 最新归档具备 1–50 轮历史、train.done 与完整 2093 条评测；selected 仍为 Epoch {pali['epoch']}，EMA {fmt(pali['ema_loss'],6)}，Average {fmt(pali['metrics']['Average'])}。原手册的“训练未完成、Epoch2 诊断”是此前快照；本次更新预算完成状态，同时保留高损失、未收敛事实。分数相同不代表训练状态未变化。"]
    lines+=['- 原手册 EVQA/InstructBLIP、EVQA/MiniGPT-4、MMKE-entity/MiniGPT-4、MMKE-visual/LLaVA 的旧完成计数与服务器结果存在漏记；本台账按唯一键重建。',
            '- 最近 G09 三个优先补层（MMKE-visual/InstructBLIP L20、MMKE-entity/InstructBLIP L20、MMKE-entity/SmolVLM L8）已在原手册，不重复计为此次新增。',
            '- 只保留 train.done 的历史记录与完整 50 轮历史记录分别显示；PaliGemma 低分、异常和恢复评测没有被 stable 高分覆盖。',
            '- 个别归档的 selected 不是现存 history 的最低 EMA，或当前路径下缺少 checkpoint/逐样本文件；详见下表与 JSON。本次不改选 checkpoint，不删除旧结果。','',
            '| 数据集 / 模型 / 层 / 配方 | 核验发现 |', '|---|---|']
    translations={'checkpoint_binary_not_at_recorded_path':'实体 checkpoint 不在记录/归档路径',
                  'selected_not_minimum_of_available_history':'selected 不是现存 history 的最低 EMA',
                  'result_file_count:0':'当前归档缺少 results.json'}
    for issue in z['issues']:
        msg='；'.join(translations.get(w,w) for w in issue['errors']+issue['warnings'])
        lines.append(f"| {DS[issue['dataset']]} / {issue['model']} / L{issue['layer']} / {issue['recipe']} | {msg}；路径见核验问题 JSON |")
    if z['conflicts']:
        lines+=['',f"发现 **{len(z['conflicts'])} 个不同运行的数值冲突**，已保留既有映射，未自动选最高分；所有备选指标和路径见 audit_issues.json。"]
    lines+=['','## 5. 尚无完整评测的训练产物','',
            '以下仅列扫描到的未评测训练产物，不代表完整待跑队列，也不据静态文件推断正在训练、暂停或失败。Max epoch 是该副本保留历史的最大轮次；没有完整评测就不增加完成数。','',
            '| 数据集 | 模型 | 层 | 配方 | Max epoch | 历史文件修改时间（北京） |', '|---|---|---:|---|---:|---|']
    for r in sorted(z['pending'],key=key):
        lines.append(f"| {DS[r['dataset']]} | {r['model']} | L{r['layer']} | {r['recipe']} | {r['max_epoch']} | {r['mtime']} |")
    lines+=['','## 6. 全部已登记逐层结果','']
    for ds in DS:
        lines+=['### '+DS[ds],'']+table([r for r in rs if r['dataset']==ds],False)+['']
    lines+=['## 7. 后续按需增量更新','',
            '在项目根目录运行（Python 标准库 + 系统 OpenSSH；使用现有 bridge-server 与 SSH key）：','',
            '```powershell','python scripts/update_sweeplayers.py','```','',
            '脚本会扫描当前服务器结果、复核独立评测、按数据集/模型/层/配方去重、保留历史结果和冲突，同步更新本文件、总手册第4节和时间戳。每次快照保存到 outputs/sweep_ledger_日期_时间/；两份 Markdown 自动备份。连接失败、扫描错误或校验输出不完整时中止，不覆盖现有台账。','',
            '本次按用户选择不安装定时任务。每次需要最新结果时运行一次。若计算节点改变，可修改脚本 collect() 中的节点列表后再执行。不要手改脚本生成的表格；人工补注放在下面的保留区域。','',
            '<!-- SWEEP_USER_NOTES_START -->','<!-- SWEEP_USER_NOTES_END -->','',
            '## 8. 逐层来源索引','',
            'S 编号对应服务器目录或原手册行号；各层的 metadata 原文、SHA-256、样本数复核和完整服务器路径在 ledger.json / verification_inputs.json 中。results.json 与权重保留在服务器，本地保存其校验摘要；这不表示已下载全部原件。','']
    for source,sid in source_ids.items():
        lines+=[f'<a id="source-{sid}"></a>',f'- **S{sid}**：`{source}`']
    return '\n'.join(lines)+'\n'


def write_result(out,z,dry_run=False):
    if dry_run:
        out=out/'previews'/dt.datetime.now(TZ).strftime('%Y%m%d_%H%M%S')
        out.mkdir(parents=True,exist_ok=False)
    rs=z['rows']
    assert len({key(r) for r in rs})==len(rs)
    assert all(r['samples']==EXPECTED[r['dataset']] for r in rs)
    assert all(all(math.isfinite(float(v)) for v in r['metrics'].values()) for r in rs)
    assert all(abs(sum(r['metrics'][m] for m in METRICS[:5])/5-r['metrics']['Average'])<.02 for r in rs)
    save(out/'ledger.json',z)
    save(out/'audit_issues.json',dict(issues=z['issues'],conflicts=z['conflicts']))
    cols=['dataset','model','layer','recipe','epoch','raw_loss','ema_loss','samples']+METRICS+['training','evidence','status','source','notes']
    with (out/'sweep_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        for r in rs:
            writer.writerow({k:r['metrics'][k] if k in METRICS else r.get(k,'') for k in cols})
    new=render(z)
    old=TARGET.read_text(encoding='utf-8') if TARGET.exists() else ''
    pattern=r'(<!-- SWEEP_USER_NOTES_START -->).*?(<!-- SWEEP_USER_NOTES_END -->)'
    m=re.search(pattern,old,re.S)
    if m:new=re.sub(pattern,lambda _:m.group(0),new,flags=re.S)
    (out/'SWeeplayers.generated.md').write_text(new,encoding='utf-8')
    if not dry_run:
        if TARGET.exists():
            backup=out/'SWeeplayers.before.md'
            if not backup.exists():shutil.copy2(TARGET,backup)
        temp=TARGET.with_suffix('.md.tmp')
        temp.write_text(new,encoding='utf-8');os.replace(temp,TARGET)
        STATE.parent.mkdir(parents=True,exist_ok=True)
        temp_state=STATE.with_suffix('.json.tmp');save(temp_state,z);os.replace(temp_state,STATE)
    print(json.dumps(dict(target=str(TARGET),dry_run=dry_run,rows=len(rs),baseline_rows=z['baseline_rows'],
                          added_vs_original=len(z['added_vs_original']),added_vs_previous=len(z['added_vs_previous']),
                          fresh_verified=sum(r['evidence']=='本次服务器复核' for r in rs),conflicts=len(z['conflicts']),
                          evidence=str(out)),ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-snapshot',type=Path,help='Replay saved evidence without connecting to server')
    parser.add_argument('--dry-run',action='store_true',help='Generate review files without replacing the ledger')
    parser.add_argument('--host',default='bridge-server')
    parser.add_argument('--key',type=Path,default=Path.home()/'.ssh/id_ed25519_bridge')
    args=parser.parse_args()
    out=args.from_snapshot or ROOT/'outputs'/('sweep_ledger_'+dt.datetime.now(TZ).strftime('%Y%m%d_%H%M%S'))
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    if not args.from_snapshot:collect(out,args)
    z=build(out);write_result(out,z,args.dry_run)
    if not args.dry_run:
        from sync_main_sweep_manual import synchronize
        print(json.dumps({'main_manual_sync':synchronize(STATE)},ensure_ascii=False))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    main()
