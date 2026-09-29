"""
VEADWithPortability: Extends VisEdit's VEAD editor with a portability loss.

Place this file in: VisEdit-main/editor/vllm_editors/vead/vead_with_port.py

Changes vs. original vead.py:
  1. VEADPortConfig adds `port_lambda` and `port_sample_n`
  2. preprocess_train_data caches portability embeddings alongside rel/gen/loc
  3. organize_batch_data randomly samples portability questions per batch
  4. train_a_batch computes NLL loss on sampled portability questions

The portability loss is structurally identical to the generality loss (NLL),
but operates on multi-hop knowledge chain questions that share the same image
as the edit request.
"""

from .vead import (
    VEAD, VEADConfig, label_loss, logit_KL_loss, get_surrounding_pixels
)
from dataset.vllm import BaseVLLMEditData
from utils.nethook import TraceDict, Trace
from utils import move_to_device
from torch.nn.utils.rnn import pad_sequence
from dataclasses import dataclass
from typing import Dict, List, Tuple
import torch, os, yaml
import numpy as np
from tqdm import tqdm


@dataclass
class VEADPortConfig(VEADConfig):
    port_lambda: float = 1.0
    port_sample_n: int = 3

    @classmethod
    def from_yaml(cls, fpath):
        with open(fpath, "r") as f:
            data = yaml.safe_load(f)
        data['train_cfg'] = cls.TrainConfig(**data['train_cfg'])
        data['IT'] = cls.InfluenceTrace(**data['IT'])
        port_lambda = data.pop('port_lambda', 1.0)
        port_sample_n = data.pop('port_sample_n', 3)
        cfg = cls(**data, port_lambda=port_lambda, port_sample_n=port_sample_n)
        return cfg


class VEADWithPortability(VEAD):
    """VEAD editor extended with portability (multi-hop knowledge) loss."""

    def __init__(self, vllm, config, device='cuda:0',
                 vllm_data_proc=None, data_proc_device=None,
                 train_data_cache_root='data'):
        super().__init__(vllm, config, device, vllm_data_proc,
                         data_proc_device, train_data_cache_root)
        self.port_cfg = self.cfg  # VEADPortConfig
        # Detect single GPU: edit model and data-proc model share the same object
        self._single_gpu = (vllm_data_proc is vllm)

    # ─────────────────────────────────────────────────────────────────────
    # Override: preprocess_train_data  —  also cache portability embeddings
    # ─────────────────────────────────────────────────────────────────────
    def preprocess_train_data(self, raw_data: BaseVLLMEditData,
                              start_i=0, end_i=None) -> List:
        if not hasattr(self, 'data_proc_device'):
            raise RuntimeError("Not set data processing model.")
        self.np_rng = np.random.default_rng(self.random_seed)
        self.pt_rng = torch.Generator(device=self.data_proc_device)
        self.pt_rng.manual_seed(self.random_seed)

        def get_llm_layer_inpt_embeds(input_embeds, vt_range):
            with torch.no_grad(), Trace(self.vllm.model, self.mid_inpt_start_layer,
                    retain_input=True, with_kwargs=False, stop=True) as t:
                self.vllm.get_llm_outpt(input_embeds, vt_range)
            return t.input[0]

        training_data_paths = []
        data_dir = os.path.join(self.train_data_cache_dir,
            self.name_of_editor_and_model()[1], raw_data.dataset_name())
        edit_signal_dir = os.path.join(data_dir, 'edit_signal')
        xym_dir = os.path.join(data_dir, 'xym')
        self.mid_inpt_start_layer_i = min(self.cfg.edit_layers + self.cfg.IT.layers)
        self.mid_inpt_start_layer = self.cfg.llm_layer_tmp.format(
            self.mid_inpt_start_layer_i)
        end_i = len(raw_data.data) if end_i is None else min(len(raw_data.data), end_i)
        self.open_adaptors(False)

        for i in tqdm(range(start_i, end_i), 'Pre-processing train data'):
            d = raw_data.data[i]

            # ── save edit_signal (same as original) ──
            edit_signal_dir_i = os.path.join(edit_signal_dir, str(i))
            flg = False
            for k in self.adaptors.keys():
                if not os.path.exists(os.path.join(edit_signal_dir_i, k)):
                    flg = True
                    break
            if flg:
                r = d['request']
                edit_reps, prompt_end = self.get_edit_signal_for_one_request(
                    r['prompt'], r['image'], r['target_new'])
                os.makedirs(edit_signal_dir_i, exist_ok=True)
                for k in edit_reps.keys():
                    save_path = os.path.join(edit_signal_dir_i, k)
                    if not os.path.exists(save_path):
                        torch.save({'edit_reps': edit_reps[k],
                                    'prompt_end': prompt_end[k]}, save_path)

            # ── save evaluation embeddings (rel + gen + loc + port) ──
            xym_dir_i = os.path.join(xym_dir, str(i))
            os.makedirs(xym_dir_i, exist_ok=True)
            save_path = os.path.join(xym_dir_i, self.mid_inpt_start_layer)
            if not os.path.exists(save_path):
                # Reliability
                prompt = [d['request']['prompt']]
                img = [d['request']['image']]
                target = [d['request']['target_new']]
                (input_embeds, vt_range), label_ids, label_masks = \
                    self.vllm.prompts_imgs_target_to_xym(prompt, img, target)
                input_embeds = get_llm_layer_inpt_embeds(input_embeds, vt_range)
                rel_data = (input_embeds, vt_range), label_ids, label_masks

                # Generality
                gen_data = {}
                for gen_name in d['generality'].keys():
                    prompt = [d['generality'][gen_name][0]['prompt']]
                    img = [d['generality'][gen_name][0]['image']]
                    img = None if img[0] is None else img
                    target = [d['generality'][gen_name][0]['target']]
                    (input_embeds, vt_range), label_ids, label_masks = \
                        self.vllm.prompts_imgs_target_to_xym(prompt, img, target)
                    input_embeds = get_llm_layer_inpt_embeds(input_embeds, vt_range)
                    gen_data[gen_name] = (input_embeds, vt_range), label_ids, label_masks

                # Locality
                loc_data = {}
                for loc_name in d['locality'].keys():
                    img = [d['locality'][loc_name][0]['image']]
                    if img[0] is None:
                        continue
                    prompt = [d['locality'][loc_name][0]['prompt']]
                    target = [d['locality'][loc_name][0]['target']]
                    (input_embeds, vt_range), label_ids, label_masks = \
                        self.vllm.prompts_imgs_target_to_xym(prompt, img, target)
                    input_embeds = get_llm_layer_inpt_embeds(input_embeds, vt_range)
                    loc_data[loc_name] = (input_embeds, vt_range), label_ids, label_masks

                # ── Portability (NEW) ──
                port_data = {}
                for hop_key in ['1hop', '2hop']:
                    port_list = d.get('portability', {}).get(hop_key, [])
                    port_data[hop_key] = []
                    for p in port_list:
                        img_p = [p['image']]
                        if img_p[0] is None:
                            continue
                        prompt_p = [p['prompt']]
                        target_p = [p['target']]
                        (input_embeds, vt_range), label_ids, label_masks = \
                            self.vllm.prompts_imgs_target_to_xym(prompt_p, img_p, target_p)
                        input_embeds = get_llm_layer_inpt_embeds(input_embeds, vt_range)
                        port_data[hop_key].append(
                            ((input_embeds, vt_range), label_ids, label_masks))

                torch.save((rel_data, gen_data, loc_data, port_data), save_path)
            training_data_paths.append((edit_signal_dir_i, xym_dir_i))
        return training_data_paths

    # ─────────────────────────────────────────────────────────────────────
    # Override: organize_batch_data  —  sample portability questions
    # ─────────────────────────────────────────────────────────────────────
    def organize_batch_data(self, a_batch_of_training_data_paths: List):
        edit_signal = {k: [] for k in self.adaptors.keys()}
        rel_data, gen_data, loc_data, port_data = [], [], [], []

        for edit_signal_dir_i, xym_dir_i in a_batch_of_training_data_paths:
            for k in edit_signal.keys():
                path = os.path.join(edit_signal_dir_i, k)
                d = torch.load(path, map_location=self.data_proc_device)
                edit_signal[k].append(d)
            path = os.path.join(xym_dir_i, self.mid_inpt_start_layer)
            loaded = torch.load(path, map_location=self.data_proc_device)
            if len(loaded) == 4:
                rd, gd, ld, pd = loaded
            else:
                rd, gd, ld = loaded
                pd = {}
            rel_data.append(rd)
            gen_data.append(gd)
            loc_data.append(ld)
            port_data.append(pd)

        # organize edit signal (same as original)
        batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end = {}, {}, {}
        for k, v in edit_signal.items():
            edit_reps = [signal['edit_reps'][0] for signal in v]
            att_mask = [torch.ones([len(r)], device=self.data_proc_device) for r in edit_reps]
            prompt_end = [signal['prompt_end'] for signal in v]
            batch_edit_reps[k] = pad_sequence(edit_reps, True)
            batch_edit_reps_att_mask[k] = pad_sequence(att_mask, True)
            batch_prompt_end[k] = torch.tensor(prompt_end, device=self.data_proc_device)

        def organize_middle_xym(embed_list):
            input_embeds_vt_range, label_ids, label_masks = zip(*embed_list)
            input_embeds, vt_range = zip(*input_embeds_vt_range)
            assert all(v == vt_range[0] for v in vt_range)
            vt_range = vt_range[0]
            max_inpt_len = max(i.shape[1] for i in input_embeds)
            min_prompt_len = min(i.shape[1] - l.shape[1]
                                for i, l in zip(input_embeds, label_ids))
            label_ids = [torch.cat([
                torch.zeros(i.shape[1] - l.shape[1] - min_prompt_len,
                            device=self.data_proc_device),
                l[0],
                torch.zeros(max_inpt_len - i.shape[1],
                            device=self.data_proc_device)
            ]).to(torch.long) for i, l in zip(input_embeds, label_ids)]
            label_ids = torch.stack(label_ids, 0)
            label_masks = [torch.cat([
                torch.zeros(i.shape[1] - m.shape[1] - min_prompt_len,
                            device=self.data_proc_device),
                m[0],
                torch.zeros(max_inpt_len - i.shape[1],
                            device=self.data_proc_device)
            ]).to(torch.long) for i, m in zip(input_embeds, label_masks)]
            label_masks = torch.stack(label_masks, 0)
            att_masks = [torch.ones(i.shape[1], device=self.data_proc_device)
                         for i in input_embeds]
            att_masks = pad_sequence(att_masks, True)
            input_embeds = pad_sequence([e[0] for e in input_embeds], True)
            mid_inpt = {'attention_mask': att_masks, 'inputs_embeds': input_embeds}
            return (mid_inpt, vt_range), label_ids, label_masks

        rel_xym = organize_middle_xym(rel_data)
        gen_xym = {}
        loc_xym = {}
        for gen_name in gen_data[0].keys():
            gen_xym[gen_name] = organize_middle_xym([d[gen_name] for d in gen_data])
        for loc_name in loc_data[0].keys():
            loc_xym[loc_name] = organize_middle_xym([d[loc_name] for d in loc_data])

        # ── Portability: pick exactly 1 question per sample per hop type ──
        # This keeps port_xym batch_size == training batch_size,
        # which must match the adaptor's edit signal batch dimension.
        port_xym = {}
        for hop_key in ['1hop', '2hop']:
            per_sample = []
            skip = False
            for pd in port_data:
                hop_list = pd.get(hop_key, [])
                if len(hop_list) == 0:
                    skip = True
                    break
                idx = int(self.np_rng.integers(0, len(hop_list)))
                per_sample.append(hop_list[idx])
            if skip or len(per_sample) == 0:
                continue
            port_xym[hop_key] = organize_middle_xym(per_sample)

        # Influence mapper xy:
        # In single GPU mode (vllm == vllm_data_proc), this background thread
        # and the main training thread would both touch the same CUDA model,
        # causing state corruption.  We DEFER the computation to train_a_batch
        # (which runs on the main thread) by passing infm_xy=None here.
        if self.cfg.IT.add_it and not self._single_gpu:
            infm_xy = self.__get_xy_for_influence_mapper__(rel_xym, gen_xym, loc_xym)
        else:
            infm_xy = None  # will be computed in train_a_batch on the main thread

        a_batch = move_to_device((
            (batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end),
            rel_xym, gen_xym, loc_xym, infm_xy, port_xym
        ), self.device)
        return a_batch

    # ─────────────────────────────────────────────────────────────────────
    # Override: train_a_batch  —  add portability NLL loss
    # ─────────────────────────────────────────────────────────────────────
    def train_a_batch(self, a_batch_of_training_data):
        ((batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end),
         rel_xym, gen_xym, loc_xym, infm_xy, port_xym) = a_batch_of_training_data
        infer_vllm = self.vllm

        # ── pre-edit phase: adaptors OFF, no edit signal ──
        with torch.no_grad():
            self.open_adaptors(False)
            # locality: capture pre-edit logits for KL divergence
            for loc_name in loc_xym.keys():
                (mid_inpt, vt_range), label_ids, label_masks = loc_xym[loc_name]
                pre_logits = self.infer_from_mid_layer(
                    infer_vllm, mid_inpt, vt_range,
                    self.mid_inpt_start_layer_i, mid_inpt['inputs_embeds']).logits
                loc_xym[loc_name] = (mid_inpt, vt_range), pre_logits, label_masks
            # influence mapper: deferred from background thread in single GPU mode
            # must run here (adaptors OFF, original model behavior) before edit signal
            if infm_xy is None and self.cfg.IT.add_it:
                infm_xy = self.__get_xy_for_influence_mapper__(
                    rel_xym, gen_xym, loc_xym)

        # activate adaptors with edit signal
        self.set_edit_signal_for_adaptors(
            batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end)
        self.open_adaptors(True)

        loss, log_dict = 0, {}

        # ── Reliability loss (NLL) ──
        (mid_inpt, vt_range), label_ids, label_masks = rel_xym
        logits = self.infer_from_mid_layer(
            infer_vllm, mid_inpt, vt_range,
            self.mid_inpt_start_layer_i, mid_inpt['inputs_embeds']).logits
        rel_loss = label_loss(logits, label_ids, label_masks) * \
            self.cfg.train_cfg.rel_lambda
        log_dict['Reliability loss'] = float(rel_loss)
        loss += rel_loss

        # ── Generality loss (NLL) ──
        log_dict['Generality loss'] = {}
        for loss_name, sp in gen_xym.items():
            (mid_inpt, vt_range), label_ids, label_masks = sp
            logits = self.infer_from_mid_layer(
                infer_vllm, mid_inpt, vt_range,
                self.mid_inpt_start_layer_i, mid_inpt['inputs_embeds']).logits
            gen_loss = label_loss(logits, label_ids, label_masks) * \
                self.cfg.train_cfg.gen_lambda
            log_dict['Generality loss'][loss_name] = float(gen_loss)
            loss += gen_loss

        # ── Locality loss (KL divergence) ──
        log_dict['Locality loss'] = {}
        for loss_name, sp in loc_xym.items():
            (mid_inpt, vt_range), pre_logits, label_masks = sp
            post_logits = self.infer_from_mid_layer(
                infer_vllm, mid_inpt, vt_range,
                self.mid_inpt_start_layer_i, mid_inpt['inputs_embeds']).logits
            loc_loss = logit_KL_loss(pre_logits, post_logits, label_masks) * \
                self.cfg.train_cfg.loc_lambda
            log_dict['Locality loss'][loss_name] = float(loc_loss)
            loss += loc_loss

        # ── Portability loss (NLL) ── NEW
        port_lambda = getattr(self.port_cfg, 'port_lambda', 1.0)
        log_dict['Portability loss'] = {}
        for hop_name, sp in port_xym.items():
            (mid_inpt, vt_range), label_ids, label_masks = sp
            logits = self.infer_from_mid_layer(
                infer_vllm, mid_inpt, vt_range,
                self.mid_inpt_start_layer_i, mid_inpt['inputs_embeds']).logits
            port_loss = label_loss(logits, label_ids, label_masks) * port_lambda
            log_dict['Portability loss'][hop_name] = float(port_loss)
            loss += port_loss

        # ── Influence mapper loss ──
        if self.cfg.IT.add_it:
            influence_mapper_inpts, rg_influences = infm_xy
            infm_lambda = self.cfg.train_cfg.inf_mapper_lambda
            for k in self.adaptors.keys():
                rg_img_reps, l_img_reps, prompt_end_reps = \
                    influence_mapper_inpts[k]
                infm_rg_pre = self.adaptors[k].influence_mapper(
                    rg_img_reps, prompt_end_reps)
                infm_l_pre = self.adaptors[k].influence_mapper(
                    l_img_reps, prompt_end_reps)
                log_dict['Influence predict sigmoid rel-gen mean-%s' % k] = \
                    float(torch.sigmoid(infm_rg_pre).mean())
                log_dict['Influence predict sigmoid loc mean-%s' % k] = \
                    float(torch.sigmoid(infm_l_pre).mean())
                rg_relative_inf_loss = -(
                    rg_influences * torch.log(
                        torch.softmax(infm_rg_pre, 1) + 1e-8)
                ).sum(1).mean(0) * infm_lambda
                rg_up_loss = -torch.log(
                    torch.sigmoid(infm_rg_pre) + 1e-8).mean() * infm_lambda
                l_down_loss = -torch.log(
                    1 - torch.sigmoid(infm_l_pre) + 1e-8).mean() * infm_lambda
                log_dict['Influence mapper rel-gen relative loss-%s' % k] = \
                    float(rg_relative_inf_loss)
                log_dict['Influence mapper rel-gen up loss-%s' % k] = \
                    float(rg_up_loss)
                log_dict['Influence mapper loc down loss-%s' % k] = \
                    float(l_down_loss)
                loss += rg_relative_inf_loss + rg_up_loss + l_down_loss

        loss.backward()
        self.opt.step()
        self.opt.zero_grad()
        return float(loss), log_dict
