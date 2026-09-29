"""
Ablation training script: VEAD with portability loss DISABLED (port_lambda=0).

Uses VEADWithPortability (not plain VEAD) so that:
  1. The single-GPU influence mapper deferral fix is automatically inherited.
  2. The cache format (4-tuple) is consistent with the full model's cache,
     stored in a separate 'data_noport/' directory to avoid conflicts.
  3. port_lambda=0.0 in the config means the portability loss contributes
     exactly 0 gradient — portability questions are loaded but ignored.

Use saint_eval_noport.py at test time to measure portability.
The only variable vs. the full model (saint_train.py) is port_lambda: 0 vs 1.

Place this file in: VisEdit-main/saint_train_noport.py

Single-GPU usage:
  python saint_train_noport.py -dvc cuda:0 --single_gpu -bs 1 -eps 500 -sci 100 -tnp saint_noport
"""

import os, argparse
from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig


def get_attr():
    def parse_lkpt(value: str):
        if value.lower() == 'none':
            return None
        return value
    parser = argparse.ArgumentParser(
        description='Ablation: VEAD with port_lambda=0 (no portability loss) on EditSaint')
    parser.add_argument('-dvc', '--device', type=str, required=True,
                        help='CUDA device, e.g. cuda:0')
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
                            'configs/vead/llava-v1.5-7b-saint-noport.yaml'),
                        help='Ablation config yaml with port_lambda=0.0')
    return parser.parse_args()


if __name__ == '__main__':
    cfg = get_attr()
    device = cfg.device

    # 1. Load config (VEADPortConfig with port_lambda=0.0)
    config = VEADPortConfig.from_yaml(cfg.config)
    print(f'[Ablation] port_lambda={config.port_lambda}  '
          f'(should be 0.0 — portability loss disabled)')
    assert config.port_lambda == 0.0, \
        'port_lambda must be 0.0 in the noport config!'

    # 2. Load VLLM (LLaVA)
    edit_model_name = config.edit_model_name
    vllm = load_vllm_for_edit(edit_model_name, device)

    if cfg.single_gpu:
        # Single GPU: VEADWithPortability auto-detects vllm is vllm_data_proc
        # and defers influence mapper to the main thread — prevents RoPE error.
        print('=== Single GPU mode: sharing model for edit & data processing ===')
        vllm_data_proc = vllm
        data_proc_device = device
    else:
        data_proc_device = 'cuda:%s' % cfg.extra_devices[0]
        vllm_data_proc = load_vllm_for_edit(edit_model_name, data_proc_device)

    # 3. Create editor with port_lambda=0 (portability gradient = 0)
    #    Separate cache dir avoids conflict with full-model (port_lambda=1) cache.
    train_data_cache_root = os.path.join(ROOT_PATH, 'data_noport')
    editor = VEADWithPortability(
        vllm, config, device, vllm_data_proc, data_proc_device,
        train_data_cache_root
    )

    # 4. Load EditSaint dataset
    from dataset.edit_saint_loader import EditSaint
    data_path    = os.path.join(ROOT_PATH, 'data/edit_saint/edit_saint_train.json')
    img_root_dir = os.path.join(ROOT_PATH, 'data/edit_saint')
    coco_img_dir = os.path.join(ROOT_PATH, 'data/easy-edit-mm/images')
    train_data = EditSaint(data_path, img_root_dir, coco_img_dir=coco_img_dir,
                           data_n=cfg.data_n)
    print(f'Loaded {len(train_data.data)} training samples '
          f'(portability loss weight = 0 → no portability gradient)')

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
