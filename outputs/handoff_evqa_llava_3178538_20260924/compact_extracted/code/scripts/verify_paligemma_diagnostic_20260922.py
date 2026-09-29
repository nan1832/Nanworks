"""Read-only artifact validation; writes only separate audit manifests."""
import csv
import hashlib
import json
import math
from pathlib import Path
import time

ROOT=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
OUT=ROOT/'server_results/evqa_paligemma_l0_main_retrain_job3178538_20260921'
AUDIT=ROOT/'server_results/localization_audit_20260922'


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''): h.update(c)
    return h.hexdigest()


def load(p): return json.loads(p.read_text())


layer=OUT/'layer_00'
result=load(layer/'eval_full.done')
verified=load(OUT/'verified_evaluation.json')
assert verified['training_complete_50_epochs'] is False
assert result==verified['result']
assert result['status']=='EVAL_DONE' and int(result['eval_samples'])==2093
selected=list(csv.DictReader((layer/'selected_checkpoint.tsv').open(),delimiter='\t'))[0]
assert int(selected['epoch'])==2 and selected['status']=='TRAIN_INCOMPLETE_FINITE_RECOVERED'
assert not (layer/'train.done').exists(), 'Do not reinterpret a completed run as the diagnostic run'
checkpoint=Path(selected['checkpoint'])
assert checkpoint.is_file() and checkpoint.stat().st_size>0
assert checkpoint==Path(result['checkpoint'])
assert sha(checkpoint)=='9405c64d2e1d5b96f5ab96b0109a25b8dcde2697f46faec319b37727efbef260'
metrics={k:float(result[k]) for k in ('Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average')}
assert all(math.isfinite(v) for v in metrics.values())
assert abs(sum(metrics[k] for k in ('Rel','T-Gen','M-Gen','T-Loc','M-Loc'))/5-metrics['Average'])<0.03
results=Path(result['result_dir'])/'results.json'
assert len(load(results))==2093
assert sha(results)==verified['results_sha256']
history=list(csv.DictReader((layer/'loss_history.csv').open()))
assert max(int(r['epoch']) for r in history)==30
counts={'saved_epochs':30,'nonfinite_gradient_records':(OUT/'training.log').read_text(errors='replace').count('SANITIZE_NONFINITE_GRAD_BEFORE_STEP')}
summary=dict(time=time.strftime('%F %T %Z'),source=str(OUT),evaluation_verified=True,diagnostic_only=True,
             eval_samples=2093,selected_epoch=2,selected_step=int(selected['i']),raw_loss=float(selected['loss']),
             ema_loss=float(selected['ema_loss']),training_complete_50_epochs=False,
             nonconvergent=True,checkpoint=str(checkpoint),checkpoint_sha256=sha(checkpoint),metrics=metrics,**counts)
(AUDIT/'paligemma_diagnostic_verified.json').write_text(json.dumps(summary,indent=2))
files={
 'selected_checkpoint.tsv':layer/'selected_checkpoint.tsv',
 'eval_full.done':layer/'eval_full.done',
 'results.json':results,
 'mean_results.json':results.parent/'mean_results.json',
 'selection_audit.json':OUT/'selection_audit.json',
 'diagnostic_epoch2_request.json':OUT/'diagnostic_epoch2_request.json',
 'original_main_config.yaml':OUT/'original_main_config.yaml',
 'loss_history.csv':layer/'loss_history.csv',
 'verified_evaluation.json':OUT/'verified_evaluation.json',
 'paligemma_diagnostic_verified.json':AUDIT/'paligemma_diagnostic_verified.json',
 'standard_training_verifier.json':AUDIT/'paligemma_standard_verifier.json',
 'protocol.json':OUT/'protocol.json',
}
artifacts=[dict(path=str(p),relative_path=name,size=p.stat().st_size,sha256=sha(p)) for name,p in files.items()]
manifest=dict(dataset='evqa-pilot500',layers=[dict(layer=0,model='paligemma-3b',complete=False,
              diagnostic_only=True,evaluation_verified=True,training_complete_50_epochs=False,
              artifacts=artifacts)],bytes=sum(r['size'] for r in artifacts))
(AUDIT/'paligemma_diagnostic_sync_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(summary,indent=2))
print('SYNC_BYTES',manifest['bytes'])
