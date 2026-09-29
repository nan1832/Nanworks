import argparse
import json
import os
import shutil

import torch
from torch.nn.utils.rnn import pad_sequence
from tqdm import tqdm

from dataset.edit_bridge_loader import EditBridge
from editor.vllm_editors.vead.vead import label_loss
from editor.vllm_editors.vead.vead_with_port import VEADPortConfig, VEADWithPortability
from utils import load_vllm_for_edit, move_to_device
from utils.GLOBAL import ROOT_PATH
from utils.nethook import Trace, TraceDict


VISEDIT_ROOT = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
TEN_CLASSES_ROOT = "/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes"


class RequestOnlyVEAD(VEADWithPortability):
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
            return infer_vllm.get_llm_outpt(llm_inpt, vt_range)

    def preprocess_train_data(self, raw_data, start_i=0, end_i=None):
        if not hasattr(self, "data_proc_device"):
            raise RuntimeError("Not set data processing model.")

        def get_llm_layer_inpt_embeds(input_embeds, vt_range):
            with torch.no_grad(), Trace(
                self.vllm.model,
                self.mid_inpt_start_layer,
                retain_input=True,
                with_kwargs=False,
                stop=True,
            ) as t:
                self.vllm.get_llm_outpt(input_embeds, vt_range)
            return t.input[0]

        data_dir = os.path.join(
            self.train_data_cache_dir,
            self.name_of_editor_and_model()[1],
            raw_data.dataset_name() + "_request_only",
        )
        edit_signal_dir = os.path.join(data_dir, "edit_signal")
        xym_dir = os.path.join(data_dir, "xym")
        self.mid_inpt_start_layer_i = min(self.cfg.edit_layers + self.cfg.IT.layers)
        self.mid_inpt_start_layer = self.cfg.llm_layer_tmp.format(self.mid_inpt_start_layer_i)

        end_i = len(raw_data.data) if end_i is None else min(len(raw_data.data), end_i)
        training_data_paths = []
        self.open_adaptors(False)

        for i in tqdm(range(start_i, end_i), "Pre-processing request-only train data"):
            d = raw_data.data[i]

            edit_signal_dir_i = os.path.join(edit_signal_dir, str(i))
            need_edit_signal = any(
                not os.path.exists(os.path.join(edit_signal_dir_i, k))
                for k in self.adaptors.keys()
            )
            if need_edit_signal:
                r = d["request"]
                edit_reps, prompt_end = self.get_edit_signal_for_one_request(
                    r["prompt"], r["image"], r["target_new"]
                )
                os.makedirs(edit_signal_dir_i, exist_ok=True)
                for k in edit_reps.keys():
                    torch.save(
                        {"edit_reps": edit_reps[k], "prompt_end": prompt_end[k]},
                        os.path.join(edit_signal_dir_i, k),
                    )

            xym_dir_i = os.path.join(xym_dir, str(i))
            os.makedirs(xym_dir_i, exist_ok=True)
            save_path = os.path.join(xym_dir_i, self.mid_inpt_start_layer)
            if not os.path.exists(save_path):
                r = d["request"]
                (input_embeds, vt_range), label_ids, label_masks = self.vllm.prompts_imgs_target_to_xym(
                    [r["prompt"]], [r["image"]], [r["target_new"]]
                )
                input_embeds = get_llm_layer_inpt_embeds(input_embeds, vt_range)
                rel_data = (input_embeds, vt_range), label_ids, label_masks
                torch.save(rel_data, save_path)

            training_data_paths.append((edit_signal_dir_i, xym_dir_i))

        return training_data_paths

    def organize_batch_data(self, a_batch_of_training_data_paths):
        edit_signal = {k: [] for k in self.adaptors.keys()}
        rel_data = []

        for edit_signal_dir_i, xym_dir_i in a_batch_of_training_data_paths:
            for k in edit_signal.keys():
                edit_signal[k].append(torch.load(os.path.join(edit_signal_dir_i, k), map_location=self.data_proc_device))
            rel_data.append(torch.load(os.path.join(xym_dir_i, self.mid_inpt_start_layer), map_location=self.data_proc_device))

        batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end = {}, {}, {}
        for k, v in edit_signal.items():
            edit_reps = [signal["edit_reps"][0] for signal in v]
            att_mask = [torch.ones([len(r)], device=self.data_proc_device) for r in edit_reps]
            prompt_end = [signal["prompt_end"] for signal in v]
            batch_edit_reps[k] = pad_sequence(edit_reps, True)
            batch_edit_reps_att_mask[k] = pad_sequence(att_mask, True)
            batch_prompt_end[k] = torch.tensor(prompt_end, device=self.data_proc_device)

        def organize_middle_xym(embed_list):
            input_embeds_vt_range, label_ids, label_masks = zip(*embed_list)
            input_embeds, vt_range = zip(*input_embeds_vt_range)
            assert all(v == vt_range[0] for v in vt_range)
            vt_range = vt_range[0]
            max_inpt_len = max(i.shape[1] for i in input_embeds)
            min_prompt_len = min(i.shape[1] - l.shape[1] for i, l in zip(input_embeds, label_ids))
            label_ids = [
                torch.cat(
                    [
                        torch.zeros(i.shape[1] - l.shape[1] - min_prompt_len, device=self.data_proc_device),
                        l[0],
                        torch.zeros(max_inpt_len - i.shape[1], device=self.data_proc_device),
                    ]
                ).to(torch.long)
                for i, l in zip(input_embeds, label_ids)
            ]
            label_masks = [
                torch.cat(
                    [
                        torch.zeros(i.shape[1] - m.shape[1] - min_prompt_len, device=self.data_proc_device),
                        m[0],
                        torch.zeros(max_inpt_len - i.shape[1], device=self.data_proc_device),
                    ]
                ).to(torch.long)
                for i, m in zip(input_embeds, label_masks)
            ]
            att_masks = [torch.ones(i.shape[1], device=self.data_proc_device) for i in input_embeds]
            mid_inpt = {
                "attention_mask": pad_sequence(att_masks, True),
                "inputs_embeds": pad_sequence([e[0] for e in input_embeds], True),
            }
            return (mid_inpt, vt_range), torch.stack(label_ids, 0), torch.stack(label_masks, 0)

        batch = ((batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end), organize_middle_xym(rel_data))
        return move_to_device(batch, self.device)

    def train_a_batch(self, a_batch_of_training_data):
        (batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end), rel_xym = a_batch_of_training_data
        self.set_edit_signal_for_adaptors(batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end)
        self.open_adaptors(True)

        (mid_inpt, vt_range), label_ids, label_masks = rel_xym
        logits = self.infer_from_mid_layer(
            self.vllm,
            mid_inpt,
            vt_range,
            self.mid_inpt_start_layer_i,
            mid_inpt["inputs_embeds"],
        ).logits
        rel_loss = label_loss(logits, label_ids, label_masks) * self.cfg.train_cfg.rel_lambda
        rel_loss.backward()
        self.opt.step()
        self.opt.zero_grad()
        return float(rel_loss), {
            "Reliability loss": float(rel_loss),
            "Generality train sample count": 0,
            "Locality train sample count": 0,
            "Portability train sample count": 0,
        }


def parse_args():
    parser = argparse.ArgumentParser(description="Train VEAD on Bridge request-only data")
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", default=os.path.join(TEN_CLASSES_ROOT, "bridge"))
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--run-config-path", default=None)
    parser.add_argument("--device", "-dvc", required=True)
    parser.add_argument("--extra-devices", "-edvc", type=int, nargs="+", default=[0])
    parser.add_argument("--single-gpu", action="store_true")
    parser.add_argument("--batch-size", "-bs", type=int, default=1)
    parser.add_argument("--data-n", "-dn", type=int, default=None)
    parser.add_argument("--epochs", "-eps", type=int, default=200)
    parser.add_argument("--load-ckpt-path", "-lkpt", default=None)
    parser.add_argument(
        "--resume-next-epoch",
        action="store_true",
        help="When loading an end-of-epoch checkpoint, continue from the next epoch/step.",
    )
    parser.add_argument("--train-name-prefix", "-tnp", default="bridge_request_only")
    parser.add_argument("--save-ckpt-per-i", "-sci", type=int, default=300)
    parser.add_argument("--log-per-i", "-lpi", type=int, default=1)
    parser.add_argument("--ema-alpha", "-ea", type=float, default=0.1)
    parser.add_argument("--random-seed", "-rs", type=int, default=2026)
    parser.add_argument("--data-buffer-size", "-dbs", type=int, default=4)
    parser.add_argument("--reset-cache", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    config = VEADPortConfig.from_yaml(args.config)
    assert config.port_lambda == 0.0
    assert config.train_cfg.gen_lambda == 0.0
    assert config.train_cfg.loc_lambda == 0.0
    assert config.IT.add_it is True

    model_name = args.model_name or config.edit_model_name
    vllm = load_vllm_for_edit(model_name, args.device)

    if args.single_gpu:
        vllm_data_proc = vllm
        data_proc_device = args.device
    else:
        data_proc_device = f"cuda:{args.extra_devices[0]}"
        vllm_data_proc = load_vllm_for_edit(model_name, data_proc_device)

    cache_dir = os.path.join(args.cache_root, "vead_train_cache")
    if args.reset_cache and os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(args.cache_root, exist_ok=True)
    os.makedirs(args.records_dir, exist_ok=True)

    editor = RequestOnlyVEAD(vllm, config, args.device, vllm_data_proc, data_proc_device, args.cache_root)

    train_data = EditBridge(
        args.data_path,
        img_root_dir=args.bridge_root,
        coco_img_dir=os.path.join(VISEDIT_ROOT, "data/easy-edit-mm/images"),
        data_n=args.data_n,
        img_path_map={"train/images": "bridge_train/bridge_images", "val/images": "bridge_val/bridge_images"},
    )

    run_config = {
        "train_loss_mode": "request_only",
        "model_name": model_name,
        "config": args.config,
        "data_path": args.data_path,
        "bridge_root": args.bridge_root,
        "cache_root": args.cache_root,
        "records_dir": args.records_dir,
        "device": args.device,
        "single_gpu": args.single_gpu,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "random_seed": args.random_seed,
        "used_request_samples": len(train_data.data),
        "used_generality_samples_for_train": 0,
        "used_locality_samples_for_train": 0,
        "used_portability_samples_for_train": 0,
        "IT.add_it": config.IT.add_it,
        "IT.layers": config.IT.layers,
        "IT.test_n": config.IT.test_n,
        "IT.noise_level": config.IT.noise_level,
        "IT.vt_sample_n": config.IT.vt_sample_n,
        "gen_lambda": config.train_cfg.gen_lambda,
        "loc_lambda": config.train_cfg.loc_lambda,
        "inf_mapper_lambda": config.train_cfg.inf_mapper_lambda,
    }
    run_config_path = args.run_config_path or os.path.join(args.records_dir, "run_config.json")
    os.makedirs(os.path.dirname(run_config_path), exist_ok=True)
    with open(run_config_path, "w", encoding="utf-8") as f:
        json.dump(run_config, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(run_config, ensure_ascii=False, indent=2))

    editor.train_init(
        train_data,
        args.batch_size,
        records_dir=args.records_dir,
        train_name_prefix=args.train_name_prefix,
        load_ckpt_path=args.load_ckpt_path,
        save_ckpt_per_i=args.save_ckpt_per_i,
        log_per_i=args.log_per_i,
        ema_alpha=args.ema_alpha,
        random_seed=args.random_seed,
        data_buffer_size=args.data_buffer_size,
    )
    if args.load_ckpt_path and args.resume_next_epoch:
        editor.train_epoch += 1
        editor.train_i += 1
    editor.train(args.epochs)


if __name__ == "__main__":
    main()
