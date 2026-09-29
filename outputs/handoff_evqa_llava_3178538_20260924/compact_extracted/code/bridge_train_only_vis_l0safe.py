import os
import argparse
import shutil

from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from utils.nethook import TraceDict
from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig


VISEDIT_ROOT = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main'
TEN_CLASSES_ROOT = '/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes'


class VEADWithPortabilityL0Safe(VEADWithPortability):
    def infer_from_mid_layer(self, infer_vllm, llm_inpt, vt_range, mid_inpt_layer_i, mid_inpt_reps):
        if mid_inpt_layer_i != 0:
            return super().infer_from_mid_layer(
                infer_vllm, llm_inpt, vt_range, mid_inpt_layer_i, mid_inpt_reps
            )

        layer0 = self.cfg.llm_layer_tmp.format(0)

        def mid_inpt_embeds(inpt, layer):
            args, kargs = inpt
            args = (mid_inpt_reps,)
            return args, kargs

        with TraceDict(infer_vllm.model, [layer0], edit_input=mid_inpt_embeds):
            outpt = infer_vllm.get_llm_outpt(llm_inpt, vt_range)
        return outpt


def get_attr():
    def parse_lkpt(value: str):
        if value.lower() == 'none':
            return None
        return value

    parser = argparse.ArgumentParser(description='Train VEAD on EditBridge only-vis data with l0-safe mid-layer injection')
    parser.add_argument('-dvc', '--device', type=str, required=True)
    parser.add_argument('-edvc', '--extra_devices', type=int, nargs='+', default=[0])
    parser.add_argument('--single_gpu', action='store_true')
    parser.add_argument('-bs', '--batch_size', type=int, default=1)
    parser.add_argument('-dn', '--data_n', type=int, default=None)
    parser.add_argument('-eps', '--epochs', type=int, default=500)
    parser.add_argument('--early_stop_loss', type=float, default=None)
    parser.add_argument('-lkpt', '--load_ckpt_path', type=parse_lkpt, default=None)
    parser.add_argument('-tnp', '--train_name_prefix', type=str, default='bridge_noport_only_vis_l0')
    parser.add_argument('-sci', '--save_ckpt_per_i', type=int, default=100)
    parser.add_argument('-lpi', '--log_per_i', type=int, default=1)
    parser.add_argument('-ea', '--ema_alpha', type=float, default=0.1)
    parser.add_argument('-rs', '--random_seed', type=int, default=42)
    parser.add_argument('-dbs', '--data_buffer_size', type=int, default=4)
    parser.add_argument('--config', type=str,
                        default=os.path.join(ROOT_PATH, 'configs/vead/llava-v1.5-7b-bridge-only-vis-l0.yaml'))
    parser.add_argument('--data_path', type=str,
                        default=os.path.join(VISEDIT_ROOT, 'data/bridge/edit_30_bridge_train_only_vis.json'))
    parser.add_argument('--cache_root', type=str,
                        default=os.path.join(ROOT_PATH, 'data_bridge_noport_onlyvis_l0'))
    parser.add_argument('--reset_cache', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    cfg = get_attr()
    device = cfg.device

    config = VEADPortConfig.from_yaml(cfg.config)
    assert config.port_lambda == 0.0
    vllm = load_vllm_for_edit(config.edit_model_name, device)

    if cfg.single_gpu:
        vllm_data_proc = vllm
        data_proc_device = device
    else:
        data_proc_device = f'cuda:{cfg.extra_devices[0]}'
        vllm_data_proc = load_vllm_for_edit(config.edit_model_name, data_proc_device)

    train_data_cache_root = cfg.cache_root
    cache_dir = os.path.join(train_data_cache_root, 'vead_train_cache')
    if cfg.reset_cache and os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(train_data_cache_root, exist_ok=True)
    editor = VEADWithPortabilityL0Safe(
        vllm, config, device, vllm_data_proc, data_proc_device, train_data_cache_root
    )

    from dataset.edit_bridge_loader import EditBridge
    bridge_img_root = os.path.join(TEN_CLASSES_ROOT, 'bridge')
    coco_img_dir = os.path.join(VISEDIT_ROOT, 'data/easy-edit-mm/images')

    train_data = EditBridge(
        cfg.data_path,
        img_root_dir=bridge_img_root,
        coco_img_dir=coco_img_dir,
        data_n=cfg.data_n,
        img_path_map={'train/images': 'bridge_train/bridge_images'},
    )

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
