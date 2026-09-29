"""
Training script for EditBridge with VEADWithPortability.

Place this file in: VisEdit-main/bridge_train.py

----------------------------------------------------------------------
Server paths (already configured below):
  Model      : /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
  Ten_Classes: /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes
  VisEdit-main root (ROOT_PATH='VEAD'):
               /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
----------------------------------------------------------------------

Single-GPU usage:
  python bridge_train.py -dvc cuda:0 --single_gpu -bs 1 -eps 500 -sci 100 -tnp bridge_port

Dual-GPU usage:
  python bridge_train.py -dvc cuda:0 -edvc 1 -bs 2 -eps 500 -sci 100 -tnp bridge_port

Setup before running:
  1. Copy this file to:         VisEdit-main/bridge_train.py
  2. Copy edit_bridge_loader.py to: VisEdit-main/dataset/edit_bridge_loader.py
  3. Copy llava-v1.5-7b-bridge.yaml to: VisEdit-main/configs/vead/llava-v1.5-7b-bridge.yaml
  4. Copy edit_30_bridge_train.json to:  VisEdit-main/data/bridge/edit_30_bridge_train.json
  5. Make sure bridge images are accessible at:
     /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/bridge_train/bridge_images/
  6. Make sure vead_with_port.py is at:
     VisEdit-main/editor/vllm_editors/vead/vead_with_port.py
"""

import os, argparse
from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from editor.vllm_editors.vead.vead_with_port import (
    VEADWithPortability, VEADPortConfig
)

# ── Server absolute paths ──
VISEDIT_ROOT = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main'
TEN_CLASSES_ROOT = '/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes'
MODEL_PATH = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf'


def get_attr():
    def parse_lkpt(value: str):
        if value.lower() == 'none':
            return None
        return value
    parser = argparse.ArgumentParser(description='Train VEAD+Portability on EditBridge')
    parser.add_argument('-dvc', '--device', type=str, required=True,
                        help='CUDA device for editing, e.g. cuda:0')
    parser.add_argument('-edvc', '--extra_devices', type=int, nargs='+', default=[0],
                        help='Extra CUDA device for data processing')
    parser.add_argument('--single_gpu', action='store_true',
                        help='Single GPU mode: reuse the same model for data processing')
    parser.add_argument('-bs', '--batch_size', type=int, default=1,
                        help='Training batch size (use 1 for single GPU)')
    parser.add_argument('-dn', '--data_n', type=int, default=None,
                        help='Max number of training samples')
    parser.add_argument('-eps', '--epochs', type=int, default=500,
                        help='Training epochs')
    parser.add_argument('--early_stop_loss', type=float, default=None,
                        help='Stop when EMA loss falls below this threshold')
    parser.add_argument('-lkpt', '--load_ckpt_path', type=parse_lkpt, default=None,
                        help='Resume from checkpoint path')
    parser.add_argument('-tnp', '--train_name_prefix', type=str, default=None,
                        help='Prefix for the training run name')
    parser.add_argument('-sci', '--save_ckpt_per_i', type=int, default=100,
                        help='Save checkpoint every N iterations')
    parser.add_argument('-lpi', '--log_per_i', type=int, default=1,
                        help='Log every N iterations')
    parser.add_argument('-ea', '--ema_alpha', type=float, default=0.1,
                        help='EMA loss smoothing alpha')
    parser.add_argument('-rs', '--random_seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('-dbs', '--data_buffer_size', type=int, default=4,
                        help='Data generator buffer size')
    parser.add_argument('--config', type=str,
                        default=os.path.join(ROOT_PATH,
                            'configs/vead/llava-v1.5-7b-bridge.yaml'),
                        help='Path to bridge config yaml')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    cfg = get_attr()
    device = cfg.device

    # 1. Load config
    config = VEADPortConfig.from_yaml(cfg.config)
    print(f'Config loaded: port_lambda={config.port_lambda}, '
          f'port_sample_n={config.port_sample_n}')

    # 2. Load VLLM (LLaVA)
    edit_model_name = config.edit_model_name
    vllm = load_vllm_for_edit(edit_model_name, device)

    if cfg.single_gpu:
        print('=== Single GPU mode: sharing model for edit & data processing ===')
        vllm_data_proc = vllm
        data_proc_device = device
    else:
        data_proc_device = 'cuda:%s' % cfg.extra_devices[0]
        vllm_data_proc = load_vllm_for_edit(edit_model_name, data_proc_device)

    # 3. Create editor
    train_data_cache_root = os.path.join(ROOT_PATH, 'data')
    editor = VEADWithPortability(
        vllm, config, device, vllm_data_proc, data_proc_device,
        train_data_cache_root
    )

    # 4. Load dataset
    from dataset.edit_bridge_loader import EditBridge

    data_path = os.path.join(VISEDIT_ROOT, 'data/bridge/edit_30_bridge_train.json')
    bridge_img_root = os.path.join(TEN_CLASSES_ROOT, 'bridge')
    coco_img_dir = os.path.join(VISEDIT_ROOT, 'data/easy-edit-mm/images')

    train_data = EditBridge(
        data_path,
        img_root_dir=bridge_img_root,
        coco_img_dir=coco_img_dir,
        data_n=cfg.data_n,
        img_path_map={'train/images': 'bridge_train/bridge_images'},
    )
    print(f'Loaded {len(train_data.data)} training samples')

    # 5. Initialize and train
    editor.train_init(
        train_data, cfg.batch_size,
        train_name_prefix=cfg.train_name_prefix,
        load_ckpt_path=cfg.load_ckpt_path,
        save_ckpt_per_i=cfg.save_ckpt_per_i,
        log_per_i=cfg.log_per_i,
        ema_alpha=cfg.ema_alpha,
        random_seed=cfg.random_seed,
        data_buffer_size=cfg.data_buffer_size,
    )
    editor.train(cfg.epochs)
