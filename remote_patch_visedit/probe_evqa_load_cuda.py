import os
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dataset.vllm import EVQA

print("before_evqa", os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count(), flush=True)
data = EVQA(
    "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json",
    "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image",
    None,
)
print("after_evqa", len(data.data), os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count(), flush=True)
if torch.cuda.is_available():
    torch.cuda.init()
    print("name0", torch.cuda.get_device_name(0), flush=True)
