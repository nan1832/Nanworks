"""Evaluation only of existing incomplete main checkpoints, with an isolated output directory."""
from pathlib import Path
import csv, json, math, hashlib, datetime, os, sys, shutil, subprocess, traceback, runpy

ROOT=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJECT=ROOT/'VisEdit-main'
SOURCE=ROOT/'server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b'
DATA=SOURCE.parent/'data'
OUT=ROOT/'server_results/paligemma_visual_main_nonconvergent_eval_20260926'
RUNNER=PROJECT/'scripts/run_evqa_pilot500_blip2_visedit_sweep.py'
LAYERS=[3,5]

def now(): return datetime.datetime.now().astimezone().isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):
    p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def status(state,**kwargs):
    obj=dict(time=now(),state=state,job=os.environ.get('SLURM_JOB_ID'),node=os.environ.get('SLURMD_NODENAME'),
             training_started=False,source=str(SOURCE),**kwargs)
    save('status.json',obj); print(json.dumps(obj,ensure_ascii=False),flush=True)

def main():
    assert os.environ.get('SLURM_JOB_ID')=='3435286', 'Expected existing allocation 3435286'
    assert os.environ.get('SLURMD_NODENAME')=='g08'
    OUT.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(OUT/'evaluation.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if all((OUT/f'layer_{l:02d}/verified_evaluation.json').exists() for l in LAYERS):
        print('Both diagnostics already verified; no duplicate evaluation',flush=True); return
    import torch, yaml
    torch.set_num_threads(2)
    status('VALIDATING_EXISTING_CHECKPOINTS')
    audits=[]; configs=[]
    for layer in LAYERS:
        sd=SOURCE/f'layer_{layer:02d}'
        hist=list(csv.DictReader((sd/'loss_history.csv').read_text().splitlines()))
        candidates=[r for r in hist if math.isfinite(float(r['ema_loss'])) and Path(r['ckpt_path']).is_file()]
        selected=min(candidates,key=lambda r:float(r['ema_loss']))
        cp=Path(selected['ckpt_path']); digest=sha(cp)
        data=torch.load(str(cp),map_location='cpu',weights_only=False)
        assert int(data['epoch'])==int(selected['epoch'])
        assert abs(float(data['ema_loss'])-float(selected['ema_loss']))<1e-6
        bad=[]; tensors=0
        for module,weights in data['train_modules'].items():
            for name,t in weights.items():
                if torch.is_tensor(t):
                    tensors+=1
                    if not bool(torch.isfinite(t).all()): bad.append(module+'.'+name)
        cfg=next(sd.glob('records/vead/paligemma-3b/*/config.yaml'))
        config=yaml.safe_load(cfg.read_text()); assert config['train_cfg']['lr']==1e-4
        config.pop('edit_layers'); configs.append(config)
        audit=dict(layer=layer,source_checkpoint=str(cp),checkpoint_sha256=digest,
                   selection='minimum finite EMA among surviving checkpoints in the same original main run',
                   selected_record=selected,saved_epoch=data['epoch'],saved_ema=data['ema_loss'],
                   recorded_epochs=len(hist),last_saved_epoch=max(int(r['epoch']) for r in hist),
                   parameter_tensor_count=tensors,nonfinite_parameter_names=bad,training_complete_50_epochs=False,
                   training_started=False,numerical_instability_in_training=True,config_sha256=sha(cfg))
        save(f'layer_{layer:02d}/selection_audit.json',audit)
        print(json.dumps(dict(layer=layer,selected_epoch=data['epoch'],ema=data['ema_loss'],bad_parameters=bad,sha256=digest)),flush=True)
        if bad: raise RuntimeError(f'L{layer}: selected checkpoint has nonfinite parameters; no evaluation started')
        dest=OUT/f'layer_{layer:02d}'; dest.mkdir(exist_ok=True)
        shutil.copy2(cfg,dest/'original_config.yaml')
        shutil.copy2(sd/'loss_history.csv',dest/'source_loss_history.csv')
        row=dict(layer=layer,status='TRAIN_INCOMPLETE_NUMERIC_INSTABILITY_MAIN_RECOVERED',
                 epoch=selected['epoch'],i=selected['i'],loss=selected['loss'],ema_loss=selected['ema_loss'],checkpoint=str(cp))
        with (dest/'selected_checkpoint.tsv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(row),delimiter='\t'); w.writeheader(); w.writerow(row)
        audits.append(audit); del data
    assert configs[0]==configs[1], 'Layer configs differ beyond their edit layer'
    train=DATA/'vqa_mmke_visual_train_evqa_compat.json'
    evaluate=DATA/'vqa_mmke_visual_eval_evqa_compat.json'
    assert len(json.loads(evaluate.read_text()))==293
    dependency_paths=[RUNNER,PROJECT/'editor/vllm_editors/vead/vead.py',
        PROJECT/'editor/vllm_editors/vead/adpt_model.py',PROJECT/'editor/vllms_for_edit/paligemma/paligemma.py',
        PROJECT/'evaluation/vllm_editor_eval.py',PROJECT/'dataset/vllm.py']
    deps={str(p):sha(p) for p in dependency_paths if p.is_file()}
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
    if free<13824:
        status('READY_WAITING_FOR_GPU_HEADROOM',free_mib=free,required_mib=13824)
        return
    total=torch.cuda.get_device_properties(0).total_memory
    # Resource ceiling only: preserve model precision, batches, sequence lengths and all metrics.
    cap_bytes=9*1024**3
    torch.cuda.set_per_process_memory_fraction(cap_bytes/total,0)
    cmd=[str(RUNNER),'--model-name','paligemma-3b','--layers','3,5','--skip-train',
         '--out-root',str(OUT),'--device','cuda:0','--config-path',str(OUT/'layer_03/original_config.yaml'),
         '--train-data',str(train),'--eval-data',str(evaluate),
         '--train-img-root',str(ROOT/'datasets/MMKE-Bench/data_image'),
         '--eval-img-root',str(ROOT/'datasets/MMKE-Bench/data_image'),'--seed','20260601']
    save('protocol.json',dict(time=now(),mode='evaluation_only',training_started=False,command=cmd,
        expected_eval_samples=293,train_data_sha256=sha(train),eval_data_sha256=sha(evaluate),dependencies=deps,
        allocator_limit_bytes=cap_bytes,initial_free_mib=free,model_precision_unchanged=True,
        layers=audits,original_runs_untouched=True))
    status('EVALUATING_EXISTING_MAIN_L3_L5',allocator_limit_gib=9,initial_free_mib=free)
    os.chdir(PROJECT); sys.path.insert(0,str(PROJECT)); sys.argv=cmd
    runpy.run_path(str(RUNNER),run_name='__main__')
    results=[]
    for audit in audits:
        l=audit['layer']; p=OUT/f'layer_{l:02d}/eval_full.done'; r=json.loads(p.read_text())
        assert int(r['eval_samples'])==293
        assert all(math.isfinite(float(r[k])) for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average'])
        assert sha(Path(audit['source_checkpoint']))==audit['checkpoint_sha256']
        detail=Path(r['result_dir'])/'results.json'
        r.update(status='EVAL_DONE_INCOMPLETE_NUMERIC_INSTABILITY_MAIN_RECOVERED',training_complete_50_epochs=False,
                 training_started=False,numerical_instability_in_training=True,checkpoint_sha256=audit['checkpoint_sha256'],
                 evaluation_protocol_sha256=sha(OUT/'protocol.json'))
        p.write_text(json.dumps(r,ensure_ascii=False,indent=2))
        save(f'layer_{l:02d}/verified_evaluation.json',r); results.append(r)
    assert all(sha(Path(p))==h for p,h in deps.items()), 'Dependencies changed during evaluation'
    status('EVAL_DONE',results=results,max_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
           max_reserved_mib=torch.cuda.max_memory_reserved()/2**20)

try:
    main()
except Exception as e:
    if OUT.exists(): status('FAILED',error=str(e),traceback=traceback.format_exc())
    raise
