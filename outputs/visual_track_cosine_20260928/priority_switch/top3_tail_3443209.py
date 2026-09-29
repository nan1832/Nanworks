"""Authorized Top-3-only continuation, gated on all three priority results."""
import csv, fcntl, hashlib, importlib.util, json, math, os, shutil, signal, subprocess, sys, time
from pathlib import Path

B = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
P = B / 'VisEdit-main'
S = B / 'server_results'
R = S / 'tukey_top3_tail_job3443209_20260926'
PRIOR = S / 'priority3_main_protocol_job3443209_20260926'
TMP = Path('/tmp/ph_teacher3/tukey_top3_tail_job3443209_20260926')
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
QPY = str(B / 'envs/qwen25vl/bin/python')
MAIN = 'scripts/run_evqa_pilot500_blip2_visedit_sweep.py'
RESUME = 'scripts/run_evqa_pilot500_blip2_visedit_sweep_resume.py'
LOWMEM = 'scripts/run_mmke_minigpt_llava_lowmem_sweep.py'
SHARED = 'scripts/run_mmke_llava_shared_gpu_sweep.py'
PALI = S / 'evqa_paligemma_l0_main_retrain_job3178538_20260921'
ROOTS = {'mmke-visual': S / 'mmke_visual_top3_union_train_eval_7models_20260613_014644',
         'mmke-entity': S / 'mmke_entity_top3_union_train_eval_7models_20260616_155000'}
METRICS = ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']
PARENT_PID = 1871816
PARENT_START = '261884209'
PARENT_SHA = 'cebe6f035ae5e978fdfd92054cad7cf9ebac0c5850ad98253cfb131a5c599903'
GROUPS = [('evqa-pilot500','instructblip-vicuna-7b',[17,20]),
          ('evqa-pilot500','qwen2.5-vl-3b',[10,6]),
          ('mmke-entity','qwen2.5-vl-3b',[6,3,10]),
          ('mmke-visual','qwen2.5-vl-3b',[3,10]),
          ('mmke-entity','minigpt-4-vicuna-7b',[7,8]),
          ('mmke-entity','llava-v1.5-7b',[7,8]),
          ('evqa-pilot500','paligemma-3b',[0])]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for a in iter(lambda:f.read(8*1024*1024),b''): h.update(a)
    return h.hexdigest()

def read(p):
    for i in range(6):
        try: return json.loads(Path(p).read_text())
        except (ValueError,FileNotFoundError):
            if i==5: raise
            time.sleep(2)

def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_name(p.name+'.partial');q.write_text(json.dumps(data,indent=2));q.replace(p)

def copy(a,b):
    b.parent.mkdir(parents=True,exist_ok=True)
    assert not b.exists(),str(b)
    h=sha(a);shutil.copy2(str(a),str(b));assert sha(a)==sha(b)==h
    return h

def state(s,**kw):
    d=dict(time=time.strftime('%F %T %Z'),state=s,job=3443209,node='g09',pid=os.getpid(),**kw)
    write(R/'control/status.json',d);print(json.dumps(d),flush=True)

def spec(ds,m,l):
    ev=ds=='evqa-pilot500'
    if ev:
        td=S/'evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json'
        ed=P/'data/easy-edit-mm/vqa/vqa_eval.json'
        ti=S/'evqa_proxy_train500_eval500_20260528/images';ei=P/'data/easy-edit-mm/images'
        nt,ne=500,2093
    else:
        key=ds.split('-')[1]
        td=ROOTS[ds]/'data'/('vqa_mmke_%s_train_evqa_compat.json'%key)
        ed=ROOTS[ds]/'data'/('vqa_mmke_%s_eval_evqa_compat.json'%key)
        ti=ei=B/'datasets/MMKE-Bench/data_image';nt,ne=(214,293) if key=='visual' else (636,954)
    model=m+'-instruct' if m=='qwen2.5-vl-3b' else m
    runner=MAIN;extra=[];buf=4;top,last=5,2
    if m=='instructblip-vicuna-7b':
        runner=RESUME;extra=['--synchronous-data-loading','--activation-checkpointing'];buf=1;top,last=1,0
    elif m=='minigpt-4-vicuna-7b':
        runner=LOWMEM;extra=['--synchronous-data-loading','--activation-checkpointing'];buf=1;top,last=1,0
    elif m=='llava-v1.5-7b':
        runner=SHARED;extra=['--synchronous-data-loading','--activation-checkpointing','--data-proc-device','cuda:0','--share-data-proc-vllm'];buf=1;top,last=1,0
    elif m=='paligemma-3b':runner=RESUME
    return dict(dataset=ds,model=m,layer=l,model_arg=model,train_count=nt,eval_count=ne,
                train_data=str(td),eval_data=str(ed),train_images=str(ti),eval_images=str(ei),
                python=QPY if m.startswith('qwen') else PY,runner=runner,extra=extra,
                buffer=buf,keep_top=top,keep_last=last,config='configs/vead/'+model+'.yaml')

def specs():return [spec(ds,m,l) for ds,m,ls in GROUPS for l in ls]
def out(j):return R/'work'/j['dataset']/j['model']
def layer(j):return out(j)/('layer_%02d'%j['layer'])

def prepare():
    import yaml
    assert not (R/'provenance/plan.json').exists(),'Already prepared'
    assert sha(PRIOR/'control/priority3_main_protocol_3443209.py')==PARENT_SHA
    st=(Path('/proc')/str(PARENT_PID)/'stat').read_text().split(') ',1)[1].split()
    assert st[19]==PARENT_START
    copy(PRIOR/'control/priority3_main_protocol_3443209.py',R/'control/priority3_snapshot.py')
    pins={};refs=[]
    old_pins=read(PRIOR/'provenance/protocol.json')['files']
    for p,h in old_pins.items():
        assert sha(p)==h,'Source changed since priority3: '+p
        if str(p).startswith(str(P)):
            pins[p]=copy(Path(p),R/'provenance/code'/Path(p).relative_to(P))
    for n in [MAIN,RESUME,LOWMEM,SHARED]:
        p=P/n
        if str(p) not in pins:pins[str(p)]=copy(p,R/'provenance/code'/n)
    launchers=['launch_formal_top3_stage2_20260812.sh','launch_evqa_pilot500_smol_qwen_job3044208.sh',
               'launch_mmke_entity_smol_qwen_job3044208.sh','launch_mmke_visual_pali_smol_qwen_job3044208.sh',
               'launch_mmke_minigpt_llava_pending_job.sh']
    for n in launchers:copy(P/'scripts'/n,R/'provenance/launchers'/n)
    seen=set()
    for j in specs():
        ds,m=j['dataset'],j['model'];combo=(ds,m)
        if combo in seen:continue
        seen.add(combo)
        cfg=P/j['config']
        if m=='instructblip-vicuna-7b':
            ref=next((S/'formal_top3_stage2_20260812/job3150065/evqa-pilot500/instructblip-vicuna-7b/layer_25').glob('records/**/config.yaml'))
        elif m=='qwen2.5-vl-3b':
            ref=next((ROOTS['mmke-visual']/m/'layer_17').glob('records/**/config.yaml'))
        elif m=='minigpt-4-vicuna-7b':
            ref=next((ROOTS[ds]/m/'layer_16').glob('records/**/config.yaml'))
        elif m=='llava-v1.5-7b':
            ref=S/'mmke_entity_llava_job3443209_20260926/provenance/code/configs/vead/llava-v1.5-7b.yaml'
        else:ref=PALI/'original_main_config.yaml'
        a,b=yaml.safe_load(ref.read_text()),yaml.safe_load(cfg.read_text())
        a.pop('edit_layers');b.pop('edit_layers');assert a==b,(ds,m,'main config mismatch')
        assert float(b['train_cfg']['lr'])==1e-4 and b['IT']['add_it'] is True
        copy(ref,R/'provenance/references'/ds/m/'baseline_main.yaml')
        refs.append(dict(dataset=ds,model=m,config_reference=str(ref),match_excluding_layer=True))
        if str(cfg) not in pins:pins[str(cfg)]=copy(cfg,R/'provenance/code'/j['config'])
        assert Path(j['python']).is_file()
        for phase in ['train','eval']:
            p=Path(j[phase+'_data']);rows=read(p);assert len(rows)==j[phase+'_count']
            pins[str(p)]=sha(p)
            for r in rows:
                for k in ['image','image_rephrase','m_loc']:
                    assert (Path(j[phase+'_images'])/r[k]).is_file(),(ds,k,r[k])
        out(j).mkdir(parents=True,exist_ok=True)
        for k in ['cache','eval_cache']:
            dest=TMP/ds/m/k;dest.mkdir(parents=True,exist_ok=True)
            (out(j)/k).symlink_to(dest,target_is_directory=True)
    # Preserve the existing incomplete Pali run in a new work tree; never change original diagnosis.
    import torch
    pj=specs()[-1];old=PALI/'layer_00';cp=next(old.glob('records/**/epoch-30-i-7500-ema_loss-3418.7548'))
    c=torch.load(str(cp),map_location='cpu')
    assert c['epoch']==30 and c['i']==7500 and c['opt']['state']
    assert list(c['train_modules'])==['language_model.model.layers.0'] and math.isfinite(c['ema_loss'])
    del c
    cps=[]
    for src in old.glob('records/**/checkpoints/epoch-*'):
        if src.is_file() and src.stat().st_size>0:
            dst=layer(pj)/src.relative_to(old);h=copy(src,dst);cps.append(dict(source=str(src),copy=str(dst),sha256=h))
    hist=list(csv.DictReader((old/'loss_history.csv').open()));assert [int(x['epoch']) for x in hist]==list(range(1,31))
    copy(old/'loss_history.csv',R/'provenance/pali_original_loss_history.csv')
    new_cp_dir=(layer(pj)/cp.relative_to(old)).parent
    for row in hist:row['ckpt_path']=str(new_cp_dir/Path(row['ckpt_path']).name)
    with (layer(pj)/'loss_history.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(hist[0]));w.writeheader();w.writerows(hist)
    best=min(hist,key=lambda x:float(x['ema_loss']))
    assert Path(best['ckpt_path']).is_file(),'Original minimum EMA checkpoint must remain available'
    for n in ['safe_cleanup_manifest.py','verify_result_tree.py']:
        copy(PRIOR/'control'/n,R/'control'/n)
    plan=dict(created_epoch=time.time(),created=time.strftime('%F %T %Z'),jobs=specs(),pins=pins,
              references=refs,parent_pid=PARENT_PID,parent_start=PARENT_START,parent_sha256=PARENT_SHA,
              pali_resume=str(layer(pj)/cp.relative_to(old)),pali_copies=cps,
              protocol=dict(epochs=50,batch=2,seed_parameter=20260601,ema_alpha=.1,selection='minimum finite EMA across complete history',main_only=True),
              note='Only Top-3 missing entries. Pali resumes epoch31; LLaVA L7 restarts by explicit prior authorization. Other paused LLaVA layers stay paused.')
    write(R/'provenance/plan.json',plan);state('PREPARED',pending_layers=14)

def pincheck():
    for p,h in read(R/'provenance/plan.json')['pins'].items():assert sha(p)==h,'Source/input changed: '+p

def parent_alive():
    try:
        a=(Path('/proc')/str(PARENT_PID)/'stat').read_text().split(') ',1)[1].split()
        return a[19]==PARENT_START and a[0]!='Z'
    except FileNotFoundError:return False

def validate(j,d=None):
    d=layer(j) if d is None else d
    hist=list(csv.DictReader((d/'loss_history.csv').open()))
    assert [int(x['epoch']) for x in hist]==list(range(1,51)),'Incomplete 50 epoch history: '+str(d)
    assert int(hist[-1]['i'])==50*math.ceil(j['train_count']/2)
    assert read(d/'train.done')['status']=='TRAIN_DONE'
    rows=list(csv.DictReader((d/'selected_checkpoint.tsv').open(),delimiter='\t'));assert len(rows)==1
    sel=rows[0];cp=Path(sel['checkpoint']);cp.resolve().relative_to(d.resolve());assert cp.stat().st_size>0
    valid=[x for x in hist if all(math.isfinite(float(x[k])) for k in ['loss','ema_loss'])]
    assert abs(min(float(x['ema_loss']) for x in valid)-float(sel['ema_loss']))<1e-8
    return cp

def validate_eval(j,d):
    cp=validate(j,d);ev=read(d/'eval_full.done')
    assert ev['status']=='EVAL_DONE' and int(ev['eval_samples'])==j['eval_count']
    assert all(math.isfinite(float(ev[k])) for k in METRICS)
    assert Path(ev['checkpoint']).resolve()==cp.resolve()
    results=list(d.glob('eval_full/**/results.json'))
    assert results and len(read(results[0]))==j['eval_count']
    return cp,ev

def wait_parent():
    while parent_alive():
        state('WAITING_FOR_PRIORITY3',parent_pid=PARENT_PID,parent_start=PARENT_START,gpu_memory_mib=0)
        time.sleep(30)
    assert (PRIOR/'control/ALL_THREE_DONE').is_file(),'Priority3 exited without completion; do not bypass'
    assert read(PRIOR/'control/status.json')['state']=='ALL_THREE_DONE_LLAVA_STAYS_PAUSED'
    for ds,m,l,nt,ne in [('mmke-visual','instructblip-vicuna-7b',20,214,293),('mmke-entity','instructblip-vicuna-7b',20,636,954),('mmke-entity','smolvlm-1.7b',8,636,954)]:
        j=dict(dataset=ds,model=m,layer=l,train_count=nt,eval_count=ne)
        d=PRIOR/'accepted'/ds/m/('layer_%02d'%l)
        cp,ev=validate_eval(j,d)
        assert (d/'SYNC_VERIFIED').is_file()
        mf=read(d/'ARCHIVE_MANIFEST.json')
        assert all(sha(d/x['file'])==x['archive_sha256'] for x in mf)
    state('PRIORITY3_VERIFIED')

def gate(phase):
    good=0;minimum=73728 if phase=='train' else 56320
    while good<3:
        free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True))
        pids=subprocess.check_output(['nvidia-smi','-i','0','--query-compute-apps=pid','--format=csv,noheader,nounits'],universal_newlines=True).strip()
        good=good+1 if free>=minimum and not pids else 0
        state('GPU_GATE',phase=phase,free_mib=free,required_mib=minimum,stable=good,other_gpu_pids=pids)
        if good<3:time.sleep(20)

def command(j,phase):
    a=[j['python'],'-u',str(P/j['runner']),'--out-root',str(out(j)),'--layers',str(j['layer']),
       '--epochs','50','--batch-size','2','--model-name',j['model_arg'],'--device','cuda:0',
       '--train-data',j['train_data'],'--eval-data',j['eval_data'],'--train-img-root',j['train_images'],
       '--eval-img-root',j['eval_images'],'--config-path',str(R/'provenance/code'/j['config']),
       '--seed','20260601','--ema-alpha','0.1','--data-buffer-size',str(j['buffer']),
       '--keep-top-ckpts',str(j['keep_top']),'--keep-last-ckpts',str(j['keep_last']),
       '--skip-eval' if phase=='train' else '--skip-train']
    a+=j['extra']
    if phase=='train' and j['model']=='paligemma-3b':a+=['--resume-checkpoint',read(R/'provenance/plan.json')['pali_resume'],'--resume-layer','0']
    return a

def run_stage(j,phase):
    pincheck();gate(phase)
    remaining=subprocess.check_output(['squeue','-j','3443209','-h','-o','%L'],universal_newlines=True).strip()
    if remaining!='UNLIMITED':
        days,clock=(remaining.split('-',1) if '-' in remaining else ('0',remaining))
        parts=[int(x) for x in clock.split(':')]
        seconds=int(days)*86400+sum(v*(60**i) for i,v in enumerate(reversed(parts)))
        assert seconds>= (72*3600 if phase=='train' and j['model']=='llava-v1.5-7b' else 24*3600), 'Insufficient remaining job time; migrate safely'
    logfile=out(j)/('%s_L%d.log'%(phase,j['layer']));assert not logfile.exists(),'Inspect existing attempt; no silent retry'
    env=os.environ.copy();env['PYTHONPATH']=str(P)+':'+env.get('PYTHONPATH','');env['CUDA_VISIBLE_DEVICES']='0'
    env['PYTORCH_CUDA_ALLOC_CONF']='expandable_segments:True'
    args=command(j,phase)
    with logfile.open('x') as f:
        c=subprocess.Popen(args,cwd=str(P),env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        state('RUNNING',dataset=j['dataset'],model=j['model'],layer=j['layer'],phase=phase,child_pid=c.pid,log=str(logfile),command=args)
        size=-1;last=time.time()
        while c.poll() is None:
            n=logfile.stat().st_size
            if n!=size:size=n;last=time.time()
            if time.time()-last>7200:
                os.killpg(c.pid,signal.SIGTERM)
                try:c.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(c.pid,signal.SIGKILL);c.wait()
                raise RuntimeError('Own stage stopped after 2h without progress: '+str(logfile))
            time.sleep(15)
        assert c.returncode==0,(j,phase,c.returncode)
    copy(out(j)/'run_config.json',layer(j)/(phase+'_run_config.json'))

def archive(j):
    d=layer(j);cp,ev=validate_eval(j,d)
    dest=R/'accepted'/j['dataset']/j['model']/d.name
    if (dest/'SYNC_VERIFIED').is_file():
        validate_eval(j,dest);assert sha(cp)==sha(dest/cp.relative_to(d));return
    st=Path(str(dest)+'.partial');st.mkdir(parents=True,exist_ok=False)
    files=[cp]+[d/x for x in ['train.done','selected_checkpoint.tsv','eval_full.done','loss_history.csv','train_run_config.json','eval_run_config.json'] if (d/x).is_file()]
    files += [p for p in (d/'eval_full').rglob('*') if p.is_file()]
    files += list(d.glob('records/**/config.yaml'))
    mf=[]
    for src in files:mf.append(dict(file=str(src.relative_to(d)),source_sha256=copy(src,st/src.relative_to(d)),bytes=src.stat().st_size))
    for n in ['train.done','selected_checkpoint.tsv','eval_full.done','loss_history.csv']:
        p=st/n;p.write_text(p.read_text().replace(str(d),str(dest)))
    for x in mf:x['archive_sha256']=sha(st/x['file'])
    write(st/'ARCHIVE_MANIFEST.json',mf);st.rename(dest)
    validate_eval(j,dest)
    assert all(sha(dest/x['file'])==x['archive_sha256'] for x in mf)
    subprocess.run([PY,str(R/'control/verify_result_tree.py'),'--root',str(dest),'--dataset',j['dataset'],'--strict','--output',str(dest/'verification.json')],check=True)
    (dest/'SYNC_VERIFIED').write_text(time.strftime('%F %T %Z'))
    clean=[p for p in cp.parent.iterdir() if p.is_file() and not p.is_symlink() and p.name.startswith('epoch-') and not p.name.endswith('.lock') and p.resolve()!=cp.resolve()]
    if clean:
        a=R/'cleanup_audits'/j['dataset']/j['model']/d.name;a.mkdir(parents=True)
        manifest=a/'manifest.tsv';manifest.write_text('path\treason\n'+''.join(str(p.resolve())+'\taccepted_independent_eval_and_verified_shared_selected_checkpoint\n' for p in clean))
        cmd=[PY,str(R/'control/safe_cleanup_manifest.py'),'--root',str(d),'--manifest',str(manifest)]
        subprocess.run(cmd+['--mode','audit','--audit-output',str(a/'audit.json')],check=True)
        subprocess.run(cmd+['--mode','delete','--audit-report',str(a/'audit.json'),'--confirm-sha256',sha(manifest),'--confirm-text','DELETE-EXACT-VALIDATED-MANIFEST','--delete-log',str(a/'deleted.json')],check=True)
    state('LAYER_COMPLETE',dataset=j['dataset'],model=j['model'],layer=j['layer'],metrics=ev,archive=str(dest))

def follow():
    assert os.environ.get('SLURM_JOB_ID')=='3443209' and os.uname()[1].split('.')[0]=='g09'
    f=(R/'control/waiter.lock').open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=read(R/'provenance/plan.json');assert plan['jobs']==specs()
    wait_parent();pincheck()
    gpu=(S/'gpu_locks/g09_gpu0.lock').open('a')
    while True:
        try:fcntl.flock(gpu,fcntl.LOCK_EX|fcntl.LOCK_NB);break
        except BlockingIOError:state('WAITING_FOR_GPU_PROJECT_LOCK');time.sleep(30)
    for j in plan['jobs']:
        done=R/'accepted'/j['dataset']/j['model']/('layer_%02d'%j['layer'])
        if (done/'SYNC_VERIFIED').is_file():
            validate_eval(j,done);state('SKIP_VERIFIED_COMPLETE',dataset=j['dataset'],model=j['model'],layer=j['layer']);continue
        # If another authorized run produced this layer while we waited, stop for reconciliation.
        spec_a=importlib.util.spec_from_file_location('tail_audit',str(R/'control/audit_top3_tail.py'))
        module=importlib.util.module_from_spec(spec_a);spec_a.loader.exec_module(module)
        hits=module.scan()['hits']
        external=[x for x in hits if (x['dataset'],x['model'],x['layer'])==(j['dataset'],j['model'],j['layer']) and not x['stable'] and not str(x['path']).startswith(str(R)+'/') and ('eval_full.done' in x or 'train.done' in x)]
        assert not external,'New external result/selected state found; reconcile instead of duplicating: '+repr([x['path'] for x in external])
        if (layer(j)/'train.done').exists():validate(j)
        else:run_stage(j,'train');validate(j)
        if (layer(j)/'eval_full.done').exists():validate_eval(j,layer(j))
        else:run_stage(j,'eval')
        archive(j)
    (R/'control/ALL_14_DONE').write_text(time.strftime('%F %T %Z'))
    state('TOP3_TAIL_DONE_OTHER_LLAVA_STAYS_PAUSED',count=14)

if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':prepare()
        elif sys.argv[1]=='follow':follow()
        else:raise ValueError(sys.argv[1])
    except Exception as e:
        state('STOPPED_ERROR_NO_CONFIG_FALLBACK',error=repr(e));raise

