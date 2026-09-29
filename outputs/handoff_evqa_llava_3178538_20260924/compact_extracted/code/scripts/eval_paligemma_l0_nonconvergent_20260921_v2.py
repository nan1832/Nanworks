"""Evaluate an existing failed-run checkpoint without retraining or altering the run."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJECT = ROOT / 'VisEdit-main'
SOURCE = ROOT / 'server_results/paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b/layer_00'
OUT = ROOT / 'server_results/paligemma_l0_nonconvergent_eval_20260921/mmke-visual_stable_l0_lr1e6'
DATA = ROOT / 'server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data'

def main():
    global SOURCE, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', choices=['stable', 'main'], default='stable')
    args = ap.parse_args()
    variant = args.variant
    if variant == 'main':
        SOURCE = ROOT / 'server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b/layer_00'
        OUT = ROOT / 'server_results/paligemma_l0_nonconvergent_eval_20260921/mmke-visual_main_l0_lr1e4'
    import torch
    torch.set_num_threads(2)
    assert os.environ.get('SLURM_JOB_ID') == '3178538', 'Expected allocation 3178538'
    OUT.mkdir(parents=True, exist_ok=True)
    layer_out = OUT / 'layer_00'
    layer_out.mkdir(exist_ok=True)
    if (layer_out / 'eval_full.done').exists():
        print('Already evaluated; preserving existing result', flush=True)
        return
    with (SOURCE / 'loss_history.csv').open() as f:
        history = list(csv.DictReader(f))
    candidates = []
    for row in history:
        path = Path(row['ckpt_path'])
        if math.isfinite(float(row['ema_loss'])) and path.is_file() and path.stat().st_size:
            candidates.append((float(row['ema_loss']), path, row))
    candidates.sort(key=lambda item: item[0])
    if not candidates:
        raise RuntimeError('No surviving checkpoint with finite EMA; no evaluation started')
    ema, checkpoint, row = candidates[0]
    saved = torch.load(str(checkpoint), map_location='cpu')
    assert int(saved['epoch']) == int(row['epoch'])
    assert abs(float(saved['ema_loss']) - ema) < 1e-6
    bad = []
    tensor_count = 0
    for module, state in saved['train_modules'].items():
        for name, tensor in state.items():
            if torch.is_tensor(tensor):
                tensor_count += 1
                if not torch.isfinite(tensor).all():
                    bad.append(module + '.' + name)
    metadata = {k: v for k, v in saved.items() if not isinstance(v, (dict, list, tuple)) and not torch.is_tensor(v)}
    report = dict(source_layer=str(SOURCE), source_checkpoint=str(checkpoint),
                  selection='minimum finite EMA among surviving checkpoints in this exact run',
                  checkpoint_ema=ema, history_row=row, saved_metadata=metadata,
                  surviving_checkpoint_count=len(candidates), parameter_tensor_count=tensor_count,
                  nonfinite_parameter_names=bad, converged=False, training_complete_50_epochs=False,
                  variant=('stable L0-specific lr=1e-6' if variant == 'stable' else 'main lr=1e-4'), expected_eval_samples=293,
                  training_started=False, checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())
    (OUT / 'selection_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)
    if bad:
        raise RuntimeError('Lowest surviving checkpoint has nonfinite adapter parameters; cannot produce trustworthy evaluation')
    del saved
    config = next(SOURCE.glob('records/vead/paligemma-3b/*/config.yaml'))
    target_config = OUT / 'original_config.yaml'
    shutil.copy2(config, target_config)
    shutil.copy2(SOURCE / 'loss_history.csv', OUT / 'source_loss_history.csv')
    selected = dict(layer=0, status='TRAIN_NONCONVERGENT_RECOVERED_' + variant.upper(), epoch=row['epoch'],
                    i=row['i'], loss=row['loss'], ema_loss=row['ema_loss'], checkpoint=str(checkpoint))
    with (layer_out / 'selected_checkpoint.tsv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(selected), delimiter='\t')
        writer.writeheader()
        writer.writerow(selected)
    free = int(subprocess.check_output(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True).splitlines()[0])
    if free < 24576:
        raise RuntimeError('Insufficient free GPU memory: {} MiB; no model loaded'.format(free))
    cmd = [sys.executable, '-u', str(PROJECT / 'scripts/run_evqa_pilot500_blip2_visedit_sweep.py'),
           '--model-name', 'paligemma-3b', '--layers', '0', '--skip-train', '--out-root', str(OUT),
           '--device', 'cuda:0', '--config-path', str(target_config),
           '--train-data', str(DATA / 'vqa_mmke_visual_train_evqa_compat.json'),
           '--eval-data', str(DATA / 'vqa_mmke_visual_eval_evqa_compat.json'),
           '--train-img-root', str(ROOT / 'datasets/MMKE-Bench/data_image'),
           '--eval-img-root', str(ROOT / 'datasets/MMKE-Bench/data_image')]
    print('EVAL_ONLY_COMMAND ' + json.dumps(cmd), flush=True)
    subprocess.run(cmd, cwd=str(PROJECT), check=True)
    result_file = layer_out / 'eval_full.done'
    result = json.loads(result_file.read_text())
    assert int(result['eval_samples']) == 293
    assert all(math.isfinite(float(result[k])) for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average'])
    result.update(status='EVAL_DONE_NONCONVERGENT_' + variant.upper() + '_RECOVERED', converged=False,
                  training_complete_50_epochs=False, selection_audit=str(OUT / 'selection_audit.json'))
    result_file.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('NONCONVERGENT_EVAL_COMPLETE ' + json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
