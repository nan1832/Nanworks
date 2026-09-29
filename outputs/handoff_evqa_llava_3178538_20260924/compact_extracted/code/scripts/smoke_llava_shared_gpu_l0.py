import gc
import json
import math
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
LAYER = 0
SEED = 20260601
STEPS = 5
ROOT = Path('/tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730/validation_l0')
TRAIN_JSON = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json')
IMAGE_ROOT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image')
CONFIG = PROJECT / 'configs/vead/llava-v1.5-7b.yaml'


def log(message):
    print(f"[{time.strftime('%F %T')}] {message}", flush=True)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    editor_base.ParallelDataset = sweep.SynchronousDataset
    train_data = EVQA(str(TRAIN_JSON), str(IMAGE_ROOT), None)
    log('loading one shared LLaVA VLM')
    vllm = load_vllm_for_edit(MODEL, DEVICE)
    sweep.enable_activation_checkpointing(vllm)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats(0)
    cfg = sweep.make_config(CONFIG, LAYER)
    editor = VEAD(vllm, cfg, DEVICE, vllm, DEVICE, str(ROOT / 'cache'))
    original_organize = editor.organize_batch_data

    def shared_organize(paths):
        editor.open_adaptors(False)
        editor.vllm.model.eval()
        editor.vllm.model.requires_grad_(False)
        return original_organize(paths)

    editor.organize_batch_data = shared_organize
    editor.train_init(
        train_data,
        2,
        records_dir=str(ROOT / 'records'),
        train_name_prefix='shared_gpu_smoke_L0',
        save_ckpt_per_i=107,
        log_per_i=1,
        ema_alpha=0.1,
        random_seed=SEED,
        data_buffer_size=1,
    )
    editor.set_train(True)
    rows = []
    data_iter = iter(editor.data_generator)
    for step in range(1, STEPS + 1):
        started = time.time()
        batch, sample_n = next(data_iter)
        loss, log_dict = editor.train_a_batch(batch)
        torch.cuda.synchronize()
        free_mib, total_mib = (value / 1024**2 for value in torch.cuda.mem_get_info(0))
        peak_mib = torch.cuda.max_memory_allocated(0) / 1024**2
        params_finite = all(
            bool(torch.isfinite(param.detach()).all().item())
            for module in editor.get_modules_for_training().values()
            for param in module.parameters()
        )
        row = {
            'step': step,
            'sample_n': int(sample_n),
            'loss': float(loss),
            'seconds': time.time() - started,
            'peak_allocated_mib': peak_mib,
            'free_mib': free_mib,
            'params_finite': params_finite,
        }
        rows.append(row)
        log(f"step={step}/{STEPS} loss={loss:.9f} seconds={row['seconds']:.2f} peak={peak_mib:.1f}MiB free={free_mib:.1f}MiB finite={params_finite}")

    report = {
        'layer': LAYER,
        'seed': SEED,
        'steps': rows,
        'min_free_mib': min(row['free_mib'] for row in rows),
        'max_peak_allocated_mib': max(row['peak_allocated_mib'] for row in rows),
        'mean_step_seconds': sum(row['seconds'] for row in rows) / len(rows),
    }
    report['passed'] = bool(
        len(rows) == STEPS
        and report['min_free_mib'] >= 3072
        and all(np.isfinite(row['loss']) and row['params_finite'] for row in rows)
    )
    (ROOT / 'smoke_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (ROOT / ('L0_SMOKE_PASS' if report['passed'] else 'L0_SMOKE_FAIL')).write_text(
        time.strftime('%F %T') + '\n', encoding='utf-8'
    )
    log(f"L0 smoke passed={report['passed']} min_free={report['min_free_mib']:.1f}MiB mean_step={report['mean_step_seconds']:.2f}s")
    raise SystemExit(0 if report['passed'] else 2)


if __name__ == '__main__':
    main()
