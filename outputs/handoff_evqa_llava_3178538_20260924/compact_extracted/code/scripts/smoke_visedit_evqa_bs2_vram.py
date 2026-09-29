import os
import sys
import time
import gc
import traceback
import subprocess
from pathlib import Path

ROOT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
OUT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_evqa_bs4_smoke_20260531')
CACHE = OUT / 'cache'
RECORDS = OUT / 'records'
DATA_PATH = ROOT / 'data/easy-edit-mm/vqa/vqa_train.json'
IMG_ROOT = ROOT / 'data/easy-edit-mm/images'

os.environ.setdefault('PYTHONPATH', str(ROOT))
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import torch
from utils import load_vllm_editor
from dataset.vllm import EVQA


def smi_used():
    try:
        out = subprocess.check_output([
            'nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'
        ], text=True).strip().splitlines()[0]
        return int(out.strip())
    except Exception:
        return -1


def report(stage):
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        allocated = torch.cuda.memory_allocated(0) / 1024**2
        reserved = torch.cuda.memory_reserved(0) / 1024**2
        max_allocated = torch.cuda.max_memory_allocated(0) / 1024**2
        max_reserved = torch.cuda.max_memory_reserved(0) / 1024**2
        print(f'SMOKE_STAGE={stage} allocated_mib={allocated:.1f} reserved_mib={reserved:.1f} max_allocated_mib={max_allocated:.1f} max_reserved_mib={max_reserved:.1f} nvidia_smi_used_mib={smi_used()}', flush=True)
    else:
        print(f'SMOKE_STAGE={stage} cuda_unavailable', flush=True)


def main():
    print(f'SMOKE_START time={time.strftime("%F %T")}', flush=True)
    print(f'ROOT={ROOT}', flush=True)
    print(f'DATA_PATH={DATA_PATH}', flush=True)
    print(f'IMG_ROOT={IMG_ROOT}', flush=True)
    print(f'torch={torch.__version__} cuda={torch.cuda.is_available()}', flush=True)
    if torch.cuda.is_available():
        print(f'gpu={torch.cuda.get_device_name(0)}', flush=True)
        torch.cuda.reset_peak_memory_stats(0)
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)

    report('before_editor_load')
    editor = load_vllm_editor('vead', 'llava-v1.5-7b', 'cuda:0', [0], None, True)
    editor.train_data_cache_dir = str(CACHE)
    # Current repo has VisionEditAdaptor.forward referring to ln_text_reps,
    # while visual-only adaptor initializes ln_edit_reps. Alias only for this smoke test.
    for _adpt in editor.adaptors.values():
        if not hasattr(_adpt, 'ln_text_reps') and hasattr(_adpt, 'ln_edit_reps'):
            _adpt.ln_text_reps = _adpt.ln_edit_reps
    report('after_editor_load')

    train_data = EVQA(str(DATA_PATH), str(IMG_ROOT), data_n=4)
    report('after_data_load')

    editor.train_init(
        train_data,
        batch_size=2,
        records_dir=str(RECORDS),
        train_name_prefix='smoke_visedit_full_evqa_bs2',
        save_ckpt_per_i=999999999,
        log_per_i=1,
        ema_alpha=0.1,
        random_seed=20260531,
        data_buffer_size=1,
    )
    report('after_train_init')

    torch.cuda.reset_peak_memory_stats(0)
    editor.set_train(True)
    it = iter(editor.data_generator)
    a_batch_samples, samp_n = next(it)
    print(f'SMOKE_BATCH_BS2 sample_n={samp_n}', flush=True)
    loss, log_dict = editor.train_a_batch(a_batch_samples)
    editor.set_train(False)
    report('after_one_train_batch')
    print(f'SMOKE_RESULT=SUCCESS loss={float(loss):.6f} log_dict={log_dict}', flush=True)

    del a_batch_samples, train_data, editor
    gc.collect()
    torch.cuda.empty_cache()
    report('after_cleanup')


if __name__ == '__main__':
    try:
        main()
    except torch.cuda.OutOfMemoryError as e:
        report('oom_caught')
        print('SMOKE_RESULT=OOM', flush=True)
        traceback.print_exc()
        raise SystemExit(100)
    except Exception:
        report('exception_caught')
        print('SMOKE_RESULT=ERROR', flush=True)
        traceback.print_exc()
        raise
