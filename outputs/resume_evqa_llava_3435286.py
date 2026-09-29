"""Scoped replacement-job preparation, launcher and durable archive helper."""
import csv
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJ = BASE / 'VisEdit-main'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
OLD = Path('/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812')
ROOT = Path('/tmp/ph_teacher3/evqa_llava_job3435286_20260924')
SHARED = BASE / 'server_results/evqa_llava_job3435286_20260924'
BACKUP = BASE / 'server_results/resume_handoffs/evqa_llava_job3178538_20260924_1340'
COMBO = Path('evqa-pilot500/llava-v1.5-7b')
CP_HASH = '71c8db9bea7a27ddaf2414d5f135801ba564707e78a0856b84de5d1f43a8c13f'
PINNED = {
    'scripts/launch_formal_top3_stage2_20260812.sh': '71caef0de33bd7d2d7aa1b8ea9f27b03ef2b0489fbbedfbf391e5fd396d04194',
    'scripts/run_mmke_llava_shared_gpu_sweep.py': '936ccf7e4b13365b3fe8f3d8d7d07573448342507c7a75572b63a75d9e06cd56',
    'configs/vead/llava-v1.5-7b.yaml': 'b6a5f7cd5c29012cee2e84de580acdcc7aef460f7238c156759e69072f992b52',
}

def sha(p):
    h=hashlib.sha256()
    with open(str(p),'rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def log(s):
    print(time.strftime('%F %T %Z')+' '+s,flush=True)

def checked_copy(src,dst):
    src,dst=Path(src),Path(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    assert not dst.exists(),str(dst)
    expected=sha(src)
    shutil.copy2(str(src),str(dst))
    assert sha(src)==sha(dst)==expected

def original_code():
    for p,h in PINNED.items():assert sha(PROJ/p)==h,'source changed: '+p
    return (PROJ/'scripts/launch_formal_top3_stage2_20260812.sh').read_text()

def generate():
    text=original_code()
    text=text.replace('RUN_ROOT='+str(OLD),'RUN_ROOT='+str(ROOT))
    text=text.replace('SHARED_ROOT='+str(BASE/'server_results/formal_top3_stage2_20260812/job3150065'),'SHARED_ROOT='+str(SHARED))
    text=text.replace('EXPECTED_JOB=3150065','EXPECTED_JOB=3435286')
    text=text.replace('GPU_TRAIN_FREE_MIN_MIB=61440','GPU_TRAIN_FREE_MIN_MIB=71680')
    full="'15,16,14,7,6,5,24,25,0,1,2,4'"
    assert text.count(full)==2
    text=text.replace(full,"'2,4'")
    # Only the two requested LLaVA layers; no InstructBLIP or other combo launches.
    text='\n'.join(l for l in text.splitlines() if not l.strip().startswith(('run_combo evqa-pilot500 instructblip','combo_complete evqa-pilot500 instructblip')))+'\n'
    old='    cleanup_nonselected_checkpoints "$d" || note=${note:+$note;}\'cleanup_warning\''
    assert text.count(old)==1
    helper=SHARED/'control/resume_evqa_llava_3435286.py'
    replacement='    if ! "$PY" "'+str(helper)+'" archive "$d"; then\n      log_status "ARCHIVE_FAILED_STOP_QUEUE layer=$layer"\n      exit 75\n    fi'
    text=text.replace(old,replacement)
    # GPU evaluation remains >=55GiB; no unrelated non-kernel workload admitted.
    text=text.replace('wait_gpu_clean "$GPU_EVAL_FREE_MIN_MIB" 1','wait_gpu_clean "$GPU_EVAL_FREE_MIN_MIB" 0')
    text=text.replace('eval_allow_non_kernel=1','eval_allow_non_kernel=0')
    subprocess.run(['bash','-n'],input=text,universal_newlines=True,check=True)
    return text

def prepare():
    assert subprocess.check_output(['hostname'],universal_newlines=True).strip()=='g08'
    text=generate()
    assert not ROOT.exists(), 'new root already exists; inspect before restart'
    ROOT.mkdir(parents=True)
    (SHARED/'control').mkdir(parents=True,exist_ok=True)
    m=json.load((BACKUP/'manifest.json').open())
    row=next(x for x in m['layers'] if x['layer']==2)
    cp=Path(row['durable_checkpoint']);assert sha(cp)==CP_HASH
    source=BACKUP/'layers'/COMBO/'layer_02'
    layer=ROOT/COMBO/'layer_02'
    for name in ['selected_checkpoint.tsv','train.done','loss_history.csv']:
        checked_copy(source/name,layer/name)
    newcp=layer/cp.relative_to(source)
    checked_copy(cp,newcp)
    # Rewrite only the new work copy, retaining original evidence in BACKUP.
    for name in ['selected_checkpoint.tsv','train.done','loss_history.csv']:
        p=layer/name;p.write_text(p.read_text().replace(str(OLD),str(ROOT)))
    sel=list(csv.DictReader((layer/'selected_checkpoint.tsv').open(),delimiter='\t'))[0]
    assert Path(sel['checkpoint'])==newcp and sha(newcp)==CP_HASH
    assert not (layer/'eval_full.done').exists()
    # Keep an extra durable training-ready copy under this new run's provenance.
    for name in ['selected_checkpoint.tsv','train.done','loss_history.csv']:
        checked_copy(layer/name,SHARED/'provenance/layer_02'/name)
    for p in ['queue.status.log','layer_status.csv']:
        if (OLD/p).is_file():checked_copy(OLD/p,SHARED/'provenance/old_job_final'/p)
    oldlog=OLD/'logs/evqa-pilot500_llava-v1.5-7b_L2_eval_20260906_121304.log'
    if oldlog.is_file():checked_copy(oldlog,SHARED/'provenance/old_job_final'/oldlog.name)
    for p in PINNED:checked_copy(PROJ/p,SHARED/'provenance/code'/p)
    (SHARED/'control/launcher_scoped.sh').write_text(text)
    (SHARED/'provenance/recovery.json').write_text(json.dumps({
        'job':3435286,'old_job':3178538,'old_state':'CANCELLED','node':'g08',
        'sequence':['L2_eval_only','L4_train_50_epochs','L4_eval'],
        'l2_checkpoint':str(newcp),'l2_sha256':CP_HASH,'source_backup':str(BACKUP),
        'training_config_changed':False,'train_gate_MiB':71680,'eval_gate_MiB':56320,
        'scope':'two-layer continuation, not all historical candidates',
        'created_beijing':time.strftime('%F %T %Z')},indent=2))
    log('PREPARED root='+str(ROOT)+' L2 selected hash verified; original source/config unchanged')

def archive(d):
    d=Path(d).resolve();relative=d.relative_to(ROOT)
    assert relative in [COMBO/'layer_02',COMBO/'layer_04']
    assert (d/'train.done').is_file()
    sel=list(csv.DictReader((d/'selected_checkpoint.tsv').open(),delimiter='\t'))[0]
    cp=Path(sel['checkpoint']).resolve();cp.relative_to(d)
    assert cp.is_file() and cp.stat().st_size>0
    ev=json.load((d/'eval_full.done').open())
    assert ev['status']=='EVAL_DONE' and ev['eval_samples']==2093
    assert all(math.isfinite(float(ev[k])) for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average'])
    results=list(d.glob('eval_full/**/results.json'))
    assert results and len(json.load(results[0].open()))==2093
    hist=list(csv.DictReader((d/'loss_history.csv').open()))
    valid=[r for r in hist if math.isfinite(float(r['ema_loss'])) and math.isfinite(float(r['loss']))]
    assert abs(min(float(r['ema_loss']) for r in valid)-float(sel['ema_loss']))<1e-8
    dest=SHARED/relative
    if not dest.exists():
        stage=Path(str(dest)+'.partial');stage.mkdir(parents=True,exist_ok=False)
        files=[cp]+[d/n for n in ['train.done','selected_checkpoint.tsv','eval_full.done','loss_history.csv']]
        files += [f for f in (d/'eval_full').rglob('*') if f.is_file()]
        hashes=[]
        for f in files:
            rel=f.relative_to(d);target=stage/rel;checked_copy(f,target)
            hashes.append({'relative_path':str(rel),'source_sha256':sha(f),'size':f.stat().st_size})
        for n in ['train.done','selected_checkpoint.tsv','eval_full.done','loss_history.csv']:
            p=stage/n;p.write_text(p.read_text().replace(str(d),str(dest)))
        for entry in hashes:entry['archive_sha256']=sha(stage/entry['relative_path'])
        (stage/'ARCHIVE_MANIFEST.json').write_text(json.dumps(hashes,indent=2))
        (stage/'SYNC_VERIFIED').write_text(time.strftime('%F %T %Z')+' all copied artifacts hash checked\n')
        stage.rename(dest)
    cp_dest=dest/cp.relative_to(d)
    assert sha(cp_dest)==sha(cp)
    assert len(json.load(next(dest.glob('eval_full/**/results.json')).open()))==2093
    for f in (ROOT/'logs').glob('*L'+str(int(d.name.split('_')[1]))+'_*'):
        target=SHARED/'logs'/f.name
        if not target.exists():checked_copy(f,target)
    # Exact-file cleanup, no cache/tree deletion. Prior user retention authorization applies.
    candidates=[p.resolve() for p in cp.parent.iterdir() if p.is_file() and not p.is_symlink()
                and p.name.startswith('epoch-') and not p.name.endswith('.lock') and p.resolve()!=cp]
    if candidates:
        auditroot=SHARED/'cleanup_audits'/(d.name+'_'+time.strftime('%Y%m%d_%H%M%S'))
        auditroot.mkdir(parents=True,exist_ok=False)
        manifest=auditroot/'manifest.tsv'
        with manifest.open('w') as f:
            f.write('path\treason\n')
            for p in candidates:f.write(str(p)+'\tnonselected_after_2093_eval_and_verified_archive\n')
        tool=SHARED/'control/safe_cleanup_manifest.py'
        args=[PY,str(tool),'--root',str(d),'--manifest',str(manifest)]
        report=auditroot/'audit.json'
        subprocess.run(args+['--mode','audit','--audit-output',str(report)],check=True)
        log('CLEANUP_AUDITED count=%d bytes=%d sha256=%s'%(len(candidates),sum(p.stat().st_size for p in candidates),sha(manifest)))
        subprocess.run(args+['--mode','delete','--audit-report',str(report),
            '--confirm-sha256',sha(manifest),'--confirm-text','DELETE-EXACT-VALIDATED-MANIFEST',
            '--delete-log',str(auditroot/'deleted.json')],check=True)
    assert cp.is_file() and sha(cp)==sha(cp_dest)
    log('ARCHIVE_VERIFIED '+str(dest)+' selected='+str(cp_dest))

def launch():
    assert os.environ.get('SLURM_JOB_ID')=='3435286'
    assert subprocess.check_output(['hostname'],universal_newlines=True).strip()=='g08'
    original_code()
    oldlock=(OLD/'launcher.lock').open('a')
    fcntl.flock(oldlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    lock=(SHARED/'control/controller.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    text=generate();script=SHARED/'control/launcher_scoped.sh'
    assert script.read_text()==text
    log('LAUNCH job3435286 layers=2_eval_then_4_train_eval old/new queue locks acquired')
    env=os.environ.copy();env['GPU_TRAIN_ALLOW_NON_KERNEL']='0'
    rc=subprocess.call(['bash',str(script),'job3150065'],env=env)
    # Capture final queue state after exit; never mislabel it as all historical layers complete.
    for n in ['queue.status.log','layer_status.csv','QUEUE_DONE','QUEUE_FINISHED_WITH_FAILURES']:
        p=ROOT/n
        if p.is_file():
            dst=SHARED/'runtime_final'/n;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(str(p),str(dst))
    sys.exit(rc)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='prepare':prepare()
    elif mode=='launch':launch()
    elif mode=='archive':archive(sys.argv[2])
    elif mode=='validate':generate();log('VALIDATION_OK')
    else:raise ValueError(mode)
