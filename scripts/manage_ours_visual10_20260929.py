"""Deploy the authorized visual-only task; hash-checked sync and marker-only ledger rendering.

The rendered Markdown tables are a mechanical view of verified JSON artifacts.
Never restarts or signals an existing server task. Never rewrites other sections.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOCAL=Path(__file__).resolve().parents[1]
OUT=LOCAL/'outputs/ours_visual10_20260929'
DOC=LOCAL/'md/Location/ALL_Methods_Recommends_layers.md'
REMOTE='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_visual10_20260929'
PY='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
SSH='C:/Windows/System32/OpenSSH/ssh.exe'
MODELS={'blip2-opt-2.7b':'BLIP2','instructblip-vicuna-7b':'InstructBLIP','minigpt-4-vicuna-7b':'MiniGPT-4','llava-v1.5-7b':'LLaVA-1.5','qwen2.5-vl-3b':'Qwen2.5-VL','paligemma-3b':'PaliGemma','smolvlm-1.7b':'SmolVLM'}
DATASETS=['evqa-pilot500','mmke-visual','mmke-entity']
BEGIN='<!-- OURS_VISUAL10_RESULTS_BEGIN -->';END='<!-- OURS_VISUAL10_RESULTS_END -->'


def sha(b):return hashlib.sha256(b).hexdigest()


def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.partial')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(p)


def ssh(code):
    p=subprocess.run([SSH,'-o','BatchMode=yes','-o','ConnectTimeout=15','-i',str(Path.home()/'.ssh/id_ed25519_bridge'),'bridge-server','python3 -'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')+p.stdout.decode(errors='replace'))
    return p.stdout.decode('utf-8')


def deploy():
    b=(LOCAL/'scripts/ours_visual10_20260929.py').read_bytes()
    code='''
import base64,json,hashlib,subprocess
from pathlib import Path
root=Path(REMOTE); code=root/'code'; code.mkdir(parents=True,exist_ok=True)
files={'ours_visual10_20260929.py':base64.b64decode(PAYLOAD),'run_lga_two_space_ablation.py':(root.parent/'lga_two_spaces_ablation_20260928/code/run_lga_two_space_ablation.py').read_bytes()}
for name,data in files.items():
 p=code/name
 if p.exists():assert p.read_bytes()==data,'Refuse changed deployment'
 else:p.write_bytes(data)
control=root/'control';control.mkdir(exist_ok=True)
pins={str(code/name):hashlib.sha256(data).hexdigest() for name,data in files.items()}
p=control/'code_pins.json'
if p.exists():assert json.loads(p.read_text())==pins
else:p.write_text(json.dumps(pins,indent=2))
print(json.dumps(pins))
'''.replace('REMOTE',repr(REMOTE)).replace('PAYLOAD',repr(base64.b64encode(b).decode()))
    receipt=json.loads(ssh(code));write(OUT/'deployment.json',receipt);print(json.dumps(receipt))


def launch():
    bootstrap='''
import os,json,subprocess,time
from pathlib import Path
R=Path(REMOTE);P=PY
assert 'job_3435286' in Path('/proc/self/cgroup').read_text()
assert os.uname()[1].split('.')[0]=='g08'
p=R/'control/launch.json'
if p.exists():
 old=json.loads(p.read_text());print(json.dumps(old));raise SystemExit(0)
subprocess.check_call([P,str(R/'code/ours_visual10_20260929.py'),'publish'])
log=R/'control/controller.log'
with log.open('x') as f:
 child=subprocess.Popen([P,'-u',str(R/'code/ours_visual10_20260929.py'),'queue'],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=child.pid,job='3435286',node='g08',time=time.strftime('%FT%T%z'),log=str(log))
p.write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
'''.replace('REMOTE',repr(REMOTE)).replace('PY',repr(PY))
    wrapper='import subprocess\np=subprocess.run(["ssh","-o","BatchMode=yes","g08","python3 -"],input='+repr(bootstrap.encode())+',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)\nprint(p.stdout.decode())\nraise SystemExit(p.returncode)'
    print(ssh(wrapper))


def sync():
    code='''
import json,base64,hashlib,time
from pathlib import Path
r=Path(REMOTE);original=(r/'manifest.json').read_bytes();m=json.loads(original);files={};digests={};groups=[]
# Each group is published atomically after verification. The queue can update a
# group before rebuilding its global manifest; capture a fresh per-file snapshot.
for name in m['files']:
 b=(r/name).read_bytes();g=json.loads(b);assert g['status'] in ['done','pending_cross_terms']
 assert len(g['formulas'])==(10 if g['status']=='done' else 3)
 groups.append(g);digests[name]=hashlib.sha256(b).hexdigest();files[name]=base64.b64encode(b).decode()
m.update(files=digests,time=time.strftime('%FT%T%z'),complete_groups=sum(g['status']=='done' for g in groups),complete_formula_groups=sum(len(g['formulas']) for g in groups),declared_manifest_sha256=hashlib.sha256(original).hexdigest(),snapshot_kind='read_only_atomic_group_snapshot')
status=json.loads((r/'control/status.json').read_text()) if (r/'control/status.json').exists() else {}
if (r/'control/failure.json').exists():status.update(state='STOPPED_REQUIRES_INSPECTION',failure=json.loads((r/'control/failure.json').read_text()))
followup=r/'followup_20260929/status.json'
followup_evidence={}
if followup.exists():
 old_state=status.get('state');status=json.loads(followup.read_text());status.setdefault('original_queue_state',old_state)
 fr=followup.parent;followup_evidence['status']=status
 names=[fr/'outcomes.json']+list((fr/'diagnostics').glob('*/*.json'))+list((fr/'errors').glob('*/*.json'))
 for name in ['progress.json','comparison.json','numerical_probe.json']:
  names+=list((fr/'retry_raw/visual').glob('*/*/'+name))
 followup_evidence['artifacts']={str(p.relative_to(fr)):json.loads(p.read_text()) for p in names if p.is_file()}
print(json.dumps(dict(manifest=m,files=files,status=status,followup_evidence=followup_evidence)))
'''.replace('REMOTE',repr(REMOTE))
    packet=json.loads(ssh(code));m=packet['manifest']
    version=sha(json.dumps(m,sort_keys=True).encode())[:16]
    dest=OUT/'snapshots'/version
    for name,data in packet['files'].items():
        assert Path(name).parts[0]=='published' and '..' not in Path(name).parts
        b=base64.b64decode(data);assert sha(b)==m['files'][name]
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():assert p.read_bytes()==b
        else:
            tmp=p.with_name(p.name+'.partial');tmp.write_bytes(b);tmp.replace(p)
    write(dest/'manifest.json',m)
    write(OUT/'sync_receipt.json',dict(time=datetime.now().astimezone().isoformat(),server_manifest=m,
        snapshot=str(dest),hashes_verified=True,status=packet['status']))
    if packet.get('followup_evidence'):write(OUT/'followup/latest_snapshot.json',packet['followup_evidence'])
    render(dest,m,packet['status'])
    print(json.dumps(dict(complete_groups=m['complete_groups'],formula_groups=m['complete_formula_groups'],status=packet['status'].get('state')),ensure_ascii=False),flush=True)
    return m,packet['status']


def render(dest,manifest,status):
    groups={(ds,m):json.loads((dest/'published'/ds/(m+'.json')).read_text(encoding='utf-8')) for ds in DATASETS for m in MODELS}
    lines=[f"**结果核验时间：{manifest['time']}（服务器北京时间）；完整 10 式组合 {manifest['complete_groups']}/21，已发布公式×组合 {manifest['complete_formula_groups']}/210。**",
        '', 'V01–V03 可以从原始线性均值精确恢复；其余 7 式只从完整、校验通过的逐样本量计算，部分样本不发布排名。† 标记原始零视觉梯度层；各表每格为 Tukey Top-3。',
        '',f"服务器队列：`{status.get('state','尚未采集')}`；Job 3435286 / G08；当前组合 `{status.get('dataset','—')} × {status.get('model','—')}`。采用已有项目锁，空闲显存至少 60,000 MiB、连续三次检查后放行；不停止其他任务。",'']
    for ds in DATASETS:
        lines+=['#### '+ds,'']
        for title,keys in [('第一梯队：单分量',['V01','V02','V03','V04']),('第二梯队：单侧强度',['V05','V06','V07','V08']),('第三梯队：双侧强度',['V09','V10'])]:
            lines += [title,'','| 模型 | 有效/总样本 | '+' | '.join(keys)+' |','|---|---|'+'---|'*len(keys)]
            for m,label in MODELS.items():
                g=groups[ds,m];cells=[]
                for k in keys:
                    if k not in g['formulas']:cells.append('待补');continue
                    cells.append(', '.join('L'+str(l)+('†' if l in g['zero_layers'] else '') for l in g['formulas'][k]['top3']) or '无可用层')
                lines.append('| '+label+' | '+str(g['n'])+'/'+str(g['total'])+' | '+' | '.join(cells)+' |')
            lines.append('')
    relative=dest.relative_to(LOCAL).as_posix()
    lines += ['BLIP2 × MMKE-entity 仅覆盖 284/636（44.65%），保留低覆盖警示；不能冒充全量定位。',
        '',f'[本轮机器可读清单：逐层分数、Raw/Tukey Top-3/5、全部剔除层、来源证据](../../{relative}/manifest.json)',
        '', '[补算与校验代码](../../scripts/ours_visual10_20260929.py) · [同步回填脚本](../../scripts/manage_ours_visual10_20260929.py)',
        '', '历史主公式及参数空间结果保留在下方折叠存档；不计入本次 10 式完成数。']
    block='\n'.join(lines)
    old=DOC.read_text(encoding='utf-8');assert old.count(BEGIN)==old.count(END)==1,'Ledger markers changed; stop rather than overwrite'
    start=old.index(BEGIN)+len(BEGIN);end=old.index(END)
    new=old[:start]+'\n'+block+'\n'+old[end:]
    if new!=old:
        backup=OUT/'ledger_backups'/(sha(old.encode())[:16]+'.md');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_text(old,encoding='utf-8')
        assert DOC.read_text(encoding='utf-8')==old,'Concurrent ledger edit; retry'
        # Mechanical table rendering only; no model-authored changes to other sections.
        tmp=DOC.with_name(DOC.name+'.ours10.partial');tmp.write_text(new,encoding='utf-8');tmp.replace(DOC)


def watch(wait_for_existing=False):
    OUT.mkdir(parents=True,exist_ok=True)
    # Windows byte-range advisory lock prevents duplicate local watchers.
    import msvcrt
    lock=(OUT/'watch.lock').open('a+b');lock.seek(0)
    wait_deadline=time.monotonic()+48*3600
    while True:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            break
        except OSError:
            if not wait_for_existing:raise RuntimeError('Existing sync watcher owns lock')
            if time.monotonic()>=wait_deadline:raise RuntimeError('Timed out waiting for existing sync watcher')
            time.sleep(30)
    write(OUT/'watch_status.json',dict(state='RUNNING',pid=os.getpid(),started=datetime.now().astimezone().isoformat()))
    failures=0
    for _ in range(720):
        try:
            m,s=sync();failures=0
            write(OUT/'watch_status.json',dict(state='RUNNING',pid=os.getpid(),time=datetime.now().astimezone().isoformat(),complete_groups=m['complete_groups'],server_state=s.get('state')))
            if m['complete_groups']==21 or s.get('state') in ['FINISHED_WITH_PENDING','DONE','STOPPED_REQUIRES_INSPECTION']:
                write(OUT/'watch_status.json',dict(state='COMPLETE' if m['complete_groups']==21 else 'NEEDS_INSPECTION',time=datetime.now().astimezone().isoformat(),complete_groups=m['complete_groups']));return
        except Exception as exc:
            failures+=1;print(repr(exc),flush=True)
            write(OUT/'watch_status.json',dict(state='RETRYING',failures=failures,error=repr(exc),time=datetime.now().astimezone().isoformat()))
            if failures>=5:raise
        time.sleep(120)
    write(OUT/'watch_status.json',dict(state='TIME_LIMIT_24H',time=datetime.now().astimezone().isoformat()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['deploy','launch','sync','watch','watch-followup']);args=p.parse_args()
    if args.action=='watch-followup':watch(wait_for_existing=True)
    else:globals()[args.action]()
