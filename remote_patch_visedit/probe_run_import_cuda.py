import os
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

print("after_torch_import", os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count(), flush=True)

from dataset.vllm import BaseVLLMEditData, EVQA
from editor.vllm_editors.vead.adpt_model import VisionEditAdaptor
from editor.vllm_editors.vead.vead import VEAD, VEADConfig
from evaluation.vllm_editor_eval import VLLMEditorEvaluation
from utils import get_full_model_name, load_vllm_for_edit
from utils.GLOBAL import ROOT_PATH

print("after_project_imports", os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count(), flush=True)
if torch.cuda.is_available():
    torch.cuda.init()
    print("name0", torch.cuda.get_device_name(0), flush=True)
