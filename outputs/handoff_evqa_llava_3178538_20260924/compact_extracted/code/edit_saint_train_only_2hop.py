import os
import argparse
from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig


def get_attr():
    def parse_lkpt(value: str):
        if value.lower() == "none":
            return None
        return value
    parser = argparse.ArgumentParser(description="Train VEAD+Portability with only 2hop portability")
    parser.add_argument("-dvc", "--device", type=str, required=True)
    parser.add_argument("-edvc", "--extra_devices", type=int, nargs="+", default=[0])
    parser.add_argument("--single_gpu", action="store_true")
    parser.add_argument("-bs", "--batch_size", type=int, default=1)
    parser.add_argument("-dn", "--data_n", type=int, default=None)
    parser.add_argument("-eps", "--epochs", type=int, default=500)
    parser.add_argument("--early_stop_loss", type=float, default=None)
    parser.add_argument("-lkpt", "--load_ckpt_path", type=parse_lkpt, default=None)
    parser.add_argument("-tnp", "--train_name_prefix", type=str, default=None)
    parser.add_argument("-sci", "--save_ckpt_per_i", type=int, default=100)
    parser.add_argument("-lpi", "--log_per_i", type=int, default=1)
    parser.add_argument("-ea", "--ema_alpha", type=float, default=0.1)
    parser.add_argument("-rs", "--random_seed", type=int, default=42)
    parser.add_argument("-dbs", "--data_buffer_size", type=int, default=4)
    parser.add_argument("--config", type=str, default=os.path.join(ROOT_PATH, "configs/vead/llava-v1.5-7b-saint.yaml"))
    parser.add_argument("--source_data", type=str, default=os.path.join(ROOT_PATH, "data/edit_saint/edit_saint_train_only2hop.json"))
    return parser.parse_args()



if __name__ == "__main__":
    cfg = get_attr()

    config = VEADPortConfig.from_yaml(cfg.config)
    print(f"Config loaded: port_lambda={config.port_lambda}, port_sample_n={config.port_sample_n}")

    edit_model_name = config.edit_model_name
    vllm = load_vllm_for_edit(edit_model_name, cfg.device)

    if cfg.single_gpu:
        vllm_data_proc = vllm
        data_proc_device = cfg.device
    else:
        data_proc_device = f"cuda:{cfg.extra_devices[0]}"
        vllm_data_proc = load_vllm_for_edit(edit_model_name, data_proc_device)

    editor = VEADWithPortability(
        vllm, config, cfg.device, vllm_data_proc, data_proc_device,
        os.path.join(ROOT_PATH, "data")
    )

    from dataset.edit_saint_loader import EditSaint
    img_root_dir = os.path.join(ROOT_PATH, "data/edit_saint")
    coco_img_dir = os.path.join(ROOT_PATH, "data/easy-edit-mm/images")
    train_data = EditSaint(cfg.source_data, img_root_dir, coco_img_dir=coco_img_dir, data_n=cfg.data_n)
    print(f"Loaded {len(train_data.data)} training samples")

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
