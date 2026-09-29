#!/usr/bin/env python3
"""PaliGemma-stable wrapper for the existing VEAD sweep runner.

This file intentionally does not edit ``editor/vllm_editors/vead/vead.py``.
It patches only the current Python process so ongoing jobs that use the
standard runner keep their original behavior.
"""

import importlib.util
import math
import os
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

BASE_SCRIPT = PROJECT_ROOT / "scripts" / "run_evqa_pilot500_blip2_visedit_sweep.py"
spec = importlib.util.spec_from_file_location("_base_visedit_sweep", BASE_SCRIPT)
base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["_base_visedit_sweep"] = base
spec.loader.exec_module(base)


def _to_float(value, default=None):
    try:
        out = float(value)
    except Exception:
        return default
    if not math.isfinite(out):
        return default
    return out


def _cfg_get(obj, name, default=None):
    return getattr(obj, name, default)


def _stable_label_loss(logits, label_ids, masks, average=True):
    logits = logits[:, -label_ids.shape[1]:].float()
    logits = torch.nan_to_num(logits, nan=0.0, posinf=30.0, neginf=-30.0)
    log_pre_p = torch.log_softmax(logits, -1)
    log_pre_p = log_pre_p.gather(-1, label_ids.unsqueeze(-1)).squeeze(-1)
    loss = -(log_pre_p * masks).sum()
    if average:
        loss = loss / masks.sum().clamp_min(1)
    return loss


def _stable_logit_kl_loss(logits1, logits2, masks, average=True):
    logits1 = logits1[:, -masks.shape[1]:].float()
    logits2 = logits2[:, -masks.shape[1]:].float()
    logits1 = torch.nan_to_num(logits1, nan=0.0, posinf=30.0, neginf=-30.0)
    logits2 = torch.nan_to_num(logits2, nan=0.0, posinf=30.0, neginf=-30.0)
    log_p1 = torch.log_softmax(logits1, -1)
    log_p2 = torch.log_softmax(logits2, -1)
    p1 = torch.softmax(logits1, 2)
    kl_loss = (p1 * (log_p1 - log_p2)).sum(2)
    loss = (kl_loss * masks).sum()
    if average:
        loss = loss / masks.sum().clamp_min(1)
    return loss


def _finite_loss_value(loss):
    try:
        detached = loss.detach().float()
        if torch.isfinite(detached).all().item():
            return float(detached.cpu())
    except Exception:
        pass
    return 1.0e12


def _all_trainable_params(self):
    params = []
    for module in self.adaptors.values():
        params.extend([p for p in module.parameters() if p.requires_grad])
    return params


def stable_train_a_batch(self, a_batch_of_training_data):
    ((batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end),
     rel_xym, gen_xym, loc_xym, infm_xy) = a_batch_of_training_data
    infer_vllm = self.vllm

    with torch.no_grad():
        self.open_adaptors(False)
        for loc_name in loc_xym.keys():
            (mid_inpt, vt_range), label_ids, label_masks = loc_xym[loc_name]
            pre_logits = self.infer_from_mid_layer(
                infer_vllm, mid_inpt, vt_range,
                self.mid_inpt_start_layer_i, mid_inpt["inputs_embeds"]
            ).logits
            loc_xym[loc_name] = (mid_inpt, vt_range), pre_logits, label_masks

    self.set_edit_signal_for_adaptors(
        batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end
    )
    loss, log_dict = 0, {}
    self.open_adaptors(True)

    (mid_inpt, vt_range), label_ids, label_masks = rel_xym
    logits = self.infer_from_mid_layer(
        infer_vllm, mid_inpt, vt_range,
        self.mid_inpt_start_layer_i, mid_inpt["inputs_embeds"]
    ).logits
    rel_loss = _stable_label_loss(logits, label_ids, label_masks) * self.cfg.train_cfg.rel_lambda
    log_dict["Reliability loss"] = _finite_loss_value(rel_loss)
    loss += rel_loss

    log_dict["Generality loss"] = {}
    for loss_name, sp in gen_xym.items():
        (mid_inpt, vt_range), label_ids, label_masks = sp
        logits = self.infer_from_mid_layer(
            infer_vllm, mid_inpt, vt_range,
            self.mid_inpt_start_layer_i, mid_inpt["inputs_embeds"]
        ).logits
        gen_loss = _stable_label_loss(logits, label_ids, label_masks) * self.cfg.train_cfg.gen_lambda
        log_dict["Generality loss"][loss_name] = _finite_loss_value(gen_loss)
        loss += gen_loss

    log_dict["Locality loss"] = {}
    for loss_name, sp in loc_xym.items():
        (mid_inpt, vt_range), pre_logits, label_masks = sp
        post_logits = self.infer_from_mid_layer(
            infer_vllm, mid_inpt, vt_range,
            self.mid_inpt_start_layer_i, mid_inpt["inputs_embeds"]
        ).logits
        loc_loss = _stable_logit_kl_loss(pre_logits, post_logits, label_masks) * self.cfg.train_cfg.loc_lambda
        log_dict["Locality loss"][loss_name] = _finite_loss_value(loc_loss)
        loss += loc_loss

    if self.cfg.IT.add_it:
        influence_mapper_inpts, rg_influences = infm_xy
        infm_lambda = self.cfg.train_cfg.inf_mapper_lambda
        for k in self.adaptors.keys():
            rg_img_reps, l_img_reps, prompt_end_reps = influence_mapper_inpts[k]
            infm_rg_pre = self.adaptors[k].influence_mapper(rg_img_reps, prompt_end_reps)
            infm_l_pre = self.adaptors[k].influence_mapper(l_img_reps, prompt_end_reps)
            infm_rg_pre = torch.nan_to_num(infm_rg_pre.float(), nan=0.0, posinf=30.0, neginf=-30.0)
            infm_l_pre = torch.nan_to_num(infm_l_pre.float(), nan=0.0, posinf=30.0, neginf=-30.0)
            log_dict["Influence predict sigmoid rel-gen mean-%s" % k] = float(torch.sigmoid(infm_rg_pre).mean())
            log_dict["Influence predict sigmoid loc mean-%s" % k] = float(torch.sigmoid(infm_l_pre).mean())
            rg_relative_inf_loss = -(
                rg_influences * torch.log(torch.softmax(infm_rg_pre, 1) + 1e-8)
            ).sum(1).mean(0) * infm_lambda
            rg_up_loss = -torch.log(torch.sigmoid(infm_rg_pre) + 1e-8).mean() * infm_lambda
            l_down_loss = -torch.log(1 - torch.sigmoid(infm_l_pre) + 1e-8).mean() * infm_lambda
            log_dict["Influence mapper rel-gen relative loss-%s" % k] = _finite_loss_value(rg_relative_inf_loss)
            log_dict["Influence mapper rel-gen up loss-%s" % k] = _finite_loss_value(rg_up_loss)
            log_dict["Influence mapper loc down loss-%s" % k] = _finite_loss_value(l_down_loss)
            loss += rg_relative_inf_loss + rg_up_loss + l_down_loss

    loss_value = _finite_loss_value(loss)
    if loss_value >= 1.0e12:
        print("[PALIGEMMA_STABLE_SKIP_NONFINITE_LOSS] skip optimizer step", flush=True)
        self.opt.zero_grad()
        return loss_value, log_dict

    loss.backward()

    bad_grad_reasons = []
    for module_name, module in self.adaptors.items():
        for param_name, param in module.named_parameters():
            if param.grad is None:
                continue
            finite = torch.isfinite(param.grad)
            if not bool(finite.all().item()):
                bad_n = int((~finite).sum().item())
                bad_grad_reasons.append(
                    "%s.%s grad_bad=%d/%d" % (
                        module_name, param_name, bad_n, param.grad.numel()
                    )
                )
                break
        if bad_grad_reasons:
            break

    skip_nonfinite_step = bool(_cfg_get(self.cfg.train_cfg, "skip_nonfinite_step", False))
    skip_nonfinite_step = skip_nonfinite_step or os.environ.get(
        "PALIGEMMA_STABLE_SKIP_NONFINITE_STEP", "1"
    ).lower() in {"1", "true", "yes", "y"}
    if bad_grad_reasons and skip_nonfinite_step:
        print(
            "[PALIGEMMA_STABLE_SKIP_NONFINITE_STEP] "
            + ";".join(bad_grad_reasons),
            flush=True,
        )
        self.opt.zero_grad()
        return loss_value, log_dict

    if bad_grad_reasons:
        print(
            "[PALIGEMMA_STABLE_SANITIZE_NONFINITE_GRAD_BEFORE_STEP] "
            + ";".join(bad_grad_reasons),
            flush=True,
        )
        for module in self.adaptors.values():
            for param in module.parameters():
                if param.grad is not None:
                    torch.nan_to_num_(param.grad, nan=0.0, posinf=0.0, neginf=0.0)

    grad_clip_norm = _cfg_get(
        self.cfg.train_cfg,
        "grad_clip_norm",
        os.environ.get("PALIGEMMA_STABLE_GRAD_CLIP_NORM", "1.0"),
    )
    if grad_clip_norm is not None:
        try:
            grad_clip_norm = float(grad_clip_norm)
        except Exception:
            grad_clip_norm = 0.0
        if grad_clip_norm > 0:
            torch.nn.utils.clip_grad_norm_(_all_trainable_params(self), grad_clip_norm)

    self.opt.step()
    self.opt.zero_grad()
    return loss_value, log_dict


def stable_select_best_checkpoint(layer_dir, history_path):
    max_ema = _to_float(os.environ.get("PALIGEMMA_STABLE_MAX_EMA"), 100.0)
    rows = []
    skipped = {"missing": 0, "nonfinite": 0, "negative": 0, "too_large": 0}
    for r in base.read_history(history_path):
        p = Path(r["ckpt_path"])
        if not p.exists():
            skipped["missing"] += 1
            continue
        ema = _to_float(r.get("ema_loss"))
        loss = _to_float(r.get("loss"))
        if ema is None or loss is None:
            skipped["nonfinite"] += 1
            continue
        if ema < 0:
            skipped["negative"] += 1
            continue
        if max_ema is not None and ema > max_ema:
            skipped["too_large"] += 1
            continue
        rows.append(r)
    print(
        "[PALIGEMMA_STABLE_SELECT] kept=%d skipped=%s layer_dir=%s"
        % (len(rows), skipped, layer_dir),
        flush=True,
    )
    if not rows:
        raise RuntimeError(
            "No stable checkpoint exists for %s after filtering: %s"
            % (layer_dir, skipped)
        )
    return min(rows, key=lambda r: float(r["ema_loss"]))


base.VEAD.train_a_batch = stable_train_a_batch
base.select_best_checkpoint = stable_select_best_checkpoint


if __name__ == "__main__":
    print("[PALIGEMMA_STABLE_WRAPPER] active", flush=True)
    base.main()
