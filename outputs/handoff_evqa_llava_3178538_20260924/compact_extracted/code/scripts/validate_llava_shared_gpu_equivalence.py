import gc
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

PROJECT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
sys.path.insert(0, str(PROJECT))
os.chdir(PROJECT)

from dataset.vllm import EVQA
import editor.vllm_editors.base as editor_base
from editor.vllm_editors.vead.vead import VEAD
from scripts import run_mmke_llava_shared_gpu_sweep as sweep
from utils import load_vllm_for_edit

DEVICE = 'cuda:0'
MODEL = 'llava-v1.5-7b'
LAYER = 12
SEED = 20260601 + LAYER
ROOT = Path('/tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730/validation_l12')
TRAIN_JSON = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json')
IMAGE_ROOT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image')
CONFIG = PROJECT / 'configs/vead/llava-v1.5-7b.yaml'


def log(message):
    print(f"[{time.strftime('%F %T')}] {message}", flush=True)


def clone_inf_xy(batch):
    inf_inputs, targets = batch[-1]
    return {
        'targets': targets.detach().cpu().float().clone(),
        'inputs': {
            key: [tensor.detach().cpu().float().clone() for tensor in values]
            for key, values in inf_inputs.items()
        },
    }


def clone_train_state(editor):
    result = {}
    for module_name, module in editor.get_modules_for_training().items():
        for param_name, tensor in module.state_dict().items():
            result[f'{module_name}.{param_name}'] = tensor.detach().cpu().float().clone()
    return result


def cleanup(editor, vllm, data_proc):
    try:
        editor.restore_to_original_model()
    except Exception:
        pass
    try:
        for hook in editor.adaptors_hooks.values():
            hook.remove()
    except Exception:
        pass
    del editor, vllm, data_proc
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()


def run_mode(mode, train_data):
    shared = mode == 'shared'
    mode_root = ROOT / mode
    cache_root = ROOT / 'common_cache'
    mode_root.mkdir(parents=True, exist_ok=True)
    torch.cuda.empty_cache()
    log(f'{mode}: loading main VLM')
    vllm = load_vllm_for_edit(MODEL, DEVICE)
    sweep.enable_activation_checkpointing(vllm)
    if shared:
        data_proc = vllm
    else:
        log(f'{mode}: loading independent frozen data-processing VLM')
        data_proc = load_vllm_for_edit(MODEL, DEVICE)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats(0)

    cfg = sweep.make_config(CONFIG, LAYER)
    editor = VEAD(vllm, cfg, DEVICE, data_proc, DEVICE, str(cache_root))
    if shared:
        original_organize = editor.organize_batch_data

        def shared_organize(paths):
            editor.open_adaptors(False)
            editor.vllm.model.eval()
            editor.vllm.model.requires_grad_(False)
            return original_organize(paths)

        editor.organize_batch_data = shared_organize

    editor_base.ParallelDataset = sweep.SynchronousDataset
    editor.train_init(
        train_data,
        2,
        records_dir=str(mode_root / 'records'),
        train_name_prefix=f'equivalence_{mode}_L12',
        save_ckpt_per_i=107,
        log_per_i=1,
        ema_alpha=0.1,
        random_seed=SEED,
        data_buffer_size=1,
    )
    editor.set_train(True)
    log(f'{mode}: organizing identical first batch')
    batch, sample_n = next(iter(editor.data_generator))
    inf_xy = clone_inf_xy(batch)
    log(f'{mode}: training one step')
    loss, log_dict = editor.train_a_batch(batch)
    state = clone_train_state(editor)
    peak_mib = torch.cuda.max_memory_allocated(0) / 1024**2
    result = {
        'mode': mode,
        'sample_n': int(sample_n),
        'loss': float(loss),
        'log_dict': log_dict,
        'peak_allocated_mib': peak_mib,
        'free_mib_after_step': torch.cuda.mem_get_info(0)[0] / 1024**2,
        'inf_xy': inf_xy,
        'state': state,
    }
    log(f"{mode}: loss={loss:.9f} peak={peak_mib:.1f}MiB free_after={result['free_mib_after_step']:.1f}MiB")
    cleanup(editor, vllm, data_proc)
    return result


def tensor_diff(a, b):
    delta = (a - b).abs()
    return {
        'max_abs': float(delta.max()) if delta.numel() else 0.0,
        'mean_abs': float(delta.mean()) if delta.numel() else 0.0,
        'allclose': bool(torch.allclose(a, b, rtol=1e-5, atol=1e-6)),
    }


def compare(reference, shared):
    report = {
        'layer': LAYER,
        'seed': SEED,
        'sample_n_equal': reference['sample_n'] == shared['sample_n'],
        'loss_reference': reference['loss'],
        'loss_shared': shared['loss'],
        'loss_abs_diff': abs(reference['loss'] - shared['loss']),
        'reference_peak_allocated_mib': reference['peak_allocated_mib'],
        'shared_peak_allocated_mib': shared['peak_allocated_mib'],
        'shared_free_mib_after_step': shared['free_mib_after_step'],
        'target': tensor_diff(reference['inf_xy']['targets'], shared['inf_xy']['targets']),
        'influence_inputs': {},
        'train_state': {},
    }
    for key in reference['inf_xy']['inputs']:
        report['influence_inputs'][key] = [
            tensor_diff(a, b)
            for a, b in zip(reference['inf_xy']['inputs'][key], shared['inf_xy']['inputs'][key])
        ]
    for key in reference['state']:
        report['train_state'][key] = tensor_diff(reference['state'][key], shared['state'][key])

    all_inputs_close = all(
        item['allclose']
        for values in report['influence_inputs'].values()
        for item in values
    )
    all_state_close = all(item['allclose'] for item in report['train_state'].values())
    report['passed'] = bool(
        report['sample_n_equal']
        and report['loss_abs_diff'] <= 1e-5
        and report['target']['allclose']
        and all_inputs_close
        and all_state_close
        and report['shared_free_mib_after_step'] >= 3072
    )
    return report


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    log('loading MMKE-visual train data')
    train_data = EVQA(str(TRAIN_JSON), str(IMAGE_ROOT), None)
    reference = run_mode('dual_reference', train_data)
    shared = run_mode('shared', train_data)
    report = compare(reference, shared)
    report_path = ROOT / 'equivalence_report.json'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    marker = ROOT / ('VALIDATION_PASS' if report['passed'] else 'VALIDATION_FAIL')
    marker.write_text(time.strftime('%F %T') + '\n', encoding='utf-8')
    log(f"validation passed={report['passed']} report={report_path}")
    if not report['passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
