import argparse
import csv
import gc
import json
import math
import os
import re
import shutil
import sys
import time
import traceback
from copy import deepcopy
from pathlib import Path

import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dataset.vllm import BaseVLLMEditData, EVQA
from editor.vllm_editors.vead.adpt_model import VisionEditAdaptor
from editor.vllm_editors.vead.vead import VEAD, VEADConfig
from evaluation.vllm_editor_eval import VLLMEditorEvaluation
from utils import get_full_model_name, load_vllm_for_edit
from utils.GLOBAL import ROOT_PATH

METRIC_COLUMNS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
PAPER_BLIP2_EVQA = {
    0: {"Rel": 95.10, "T-Gen": 93.70, "M-Gen": 94.43, "T-Loc": 100.00, "M-Loc": 84.51, "Average": 93.55},
    5: {"Rel": 95.16, "T-Gen": 94.63, "M-Gen": 94.49, "T-Loc": 100.00, "M-Loc": 86.51, "Average": 94.16},
    10: {"Rel": 96.36, "T-Gen": 95.79, "M-Gen": 95.60, "T-Loc": 100.00, "M-Loc": 85.83, "Average": 94.72},
    15: {"Rel": 97.69, "T-Gen": 97.48, "M-Gen": 97.08, "T-Loc": 100.00, "M-Loc": 92.20, "Average": 96.89},
    19: {"Rel": 98.83, "T-Gen": 98.63, "M-Gen": 97.90, "T-Loc": 100.00, "M-Loc": 92.30, "Average": 97.53},
    25: {"Rel": 97.54, "T-Gen": 96.97, "M-Gen": 95.87, "T-Loc": 100.00, "M-Loc": 88.83, "Average": 95.80},
    30: {"Rel": 86.22, "T-Gen": 84.18, "M-Gen": 83.62, "T-Loc": 100.00, "M-Loc": 85.98, "Average": 88.00},
}


def now():
    return time.strftime("%F %T")


def log(msg):
    print(f"[{now()}] {msg}", flush=True)


def official_visual_forward(self, layer_outpt):
    """Pin visual-only VisEdit adapter forward to avoid local text/gating branch bugs."""
    if not self.is_open or layer_outpt.shape[1] == 1:
        return layer_outpt
    if not hasattr(self, "inpt_has_img"):
        raise RuntimeError(
            "Visual adapter is open but set_input_info() was never called; "
            "VEAD get_llm_outpt wrapper is not bound to the active editor."
        )
    if not self.inpt_has_img:
        return layer_outpt
    vt_begin = getattr(self, "inpt_vt_begin", None)
    vt_end = getattr(self, "inpt_vt_end", None)
    if vt_begin is None or vt_end is None:
        raise RuntimeError("Visual adapter is open but vision token range is missing.")
    img_reps = layer_outpt[:, vt_begin:vt_end].clone()
    b1, l1, _ = img_reps.shape
    b2, l2, _ = self.edit_reps.shape
    if l1 != self.img_tok_n:
        raise BaseException("Number of selected vision tokens error.")
    if b1 != b2:
        raise BaseException("Batch size of input and editing signal are not matched.")
    adapter_dtype = next(self.parameters()).dtype
    img_reps_in = img_reps.to(dtype=adapter_dtype)
    edit_reps = self.edit_reps.to(dtype=adapter_dtype)
    if self.add_it:
        prompt_last_token_of_edit_reps = edit_reps[range(len(self.prompt_end)), self.prompt_end]
        inf_map = self.influence_mapper(img_reps_in, prompt_last_token_of_edit_reps)
        inf_map = torch.sigmoid(inf_map).unsqueeze(-1)
    else:
        inf_map = 1
    norm_img_reps = self.ln_img_reps(img_reps_in)
    norm_edit_reps = self.ln_edit_reps(edit_reps)
    x = self.mlp_begin(norm_img_reps)
    q = self.cross_att_q_mlp(x).reshape(b1, l1, self.cross_att_head_n, self.mid_dim // self.cross_att_head_n)
    k = self.cross_att_k_mlp(norm_edit_reps).reshape(b1, l2, self.cross_att_head_n, self.mid_dim // self.cross_att_head_n)
    v = self.cross_att_v_mlp(norm_edit_reps).reshape(b1, l2, self.cross_att_head_n, self.mid_dim // self.cross_att_head_n)
    s = torch.einsum("blhm,buhm->bhlu", q, k)
    s = s / (self.mid_dim // self.cross_att_head_n) ** 0.5
    edit_reps_att_mask = self.edit_reps_att_mask.to(dtype=s.dtype)
    s = s + (edit_reps_att_mask.reshape(b1, 1, 1, l2) - 1) * 9999999999
    s = torch.softmax(s, 3)
    x = torch.einsum("bhlu,buhm->blhm", s, v).reshape(b1, l1, self.mid_dim)
    x = self.mlp_end(x) * inf_map
    layer_outpt[:, vt_begin:vt_end] = img_reps + x.to(dtype=img_reps.dtype)
    return layer_outpt


def load_imgs_with_closed_files(self, data):
    if isinstance(data, dict):
        for key in data.keys():
            if key == "image":
                if data[key] is not None:
                    with Image.open(data[key]) as image:
                        data[key] = image.convert("RGB").copy()
            else:
                load_imgs_with_closed_files(self, data[key])
    elif isinstance(data, list):
        for item in data:
            load_imgs_with_closed_files(self, item)
    elif isinstance(data, str):
        return
    else:
        raise TypeError(f"Unsupported data type while loading images: {type(data)}")


VisionEditAdaptor.forward = official_visual_forward
BaseVLLMEditData.__load_imgs_for_data_with_img_path__ = load_imgs_with_closed_files


def parse_layers(text):
    out = []
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def gpu_report():
    if not torch.cuda.is_available():
        return "cuda_unavailable"
    torch.cuda.synchronize()
    return (
        f"allocated={torch.cuda.memory_allocated(0)/1024**2:.1f}MiB "
        f"reserved={torch.cuda.memory_reserved(0)/1024**2:.1f}MiB "
        f"max_allocated={torch.cuda.max_memory_allocated(0)/1024**2:.1f}MiB"
    )


def metric_from_mean(mean_results):
    rel = mean_results["reliability"]["acc"] * 100.0
    t_gen = mean_results["generality"]["text_rephrase"]["acc"] * 100.0
    m_gen = mean_results["generality"]["image_rephrase"]["acc"] * 100.0
    t_loc = mean_results["locality"]["text_loc"]["acc"] * 100.0
    m_loc = mean_results["locality"]["image_loc"]["acc"] * 100.0
    avg = (rel + t_gen + m_gen + t_loc + m_loc) / 5.0
    return {"Rel": rel, "T-Gen": t_gen, "M-Gen": m_gen, "T-Loc": t_loc, "M-Loc": m_loc, "Average": avg}


def write_rows_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def append_history(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = ["time", "layer", "epoch", "i", "loss", "ema_loss", "ckpt_path", "kept"]
    with path.open('a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow(row)


def read_history(path):
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def cleanup_checkpoints(layer_dir, history_path, keep_top=5, keep_last=2):
    rows = read_history(history_path)
    valid = []
    for r in rows:
        p = Path(r["ckpt_path"])
        if p.exists():
            try:
                valid.append((float(r["ema_loss"]), float(r["loss"]), int(r["epoch"]), int(r["i"]), p))
            except Exception:
                pass
    keep = set()
    for item in sorted(valid, key=lambda x: x[0])[:keep_top]:
        keep.add(item[-1])
    for item in sorted(valid, key=lambda x: x[1])[:keep_top]:
        keep.add(item[-1])
    for item in sorted(valid, key=lambda x: x[3], reverse=True)[:keep_last]:
        keep.add(item[-1])
    removed = 0
    for _, _, _, _, p in valid:
        if p not in keep:
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    return removed, len(keep)


def select_best_checkpoint(layer_dir, history_path):
    rows = []
    for r in read_history(history_path):
        p = Path(r["ckpt_path"])
        if p.exists():
            rows.append(r)
    if not rows:
        raise RuntimeError(f"No checkpoint exists for {layer_dir}")
    best = min(rows, key=lambda r: float(r["ema_loss"]))
    return best


def write_selected_tsv(path, rows):
    fields = ["layer", "status", "epoch", "i", "loss", "ema_loss", "checkpoint"]
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter='\t')
        w.writeheader()
        for r in rows:
            w.writerow(r)


def plot_loss_curves(out_root, layers):
    history_rows = []
    for layer in layers:
        hp = out_root / f"layer_{layer:02d}" / "loss_history.csv"
        for r in read_history(hp):
            history_rows.append(r)
    if not history_rows:
        return None
    all_csv = out_root / "loss_history_all_layers.csv"
    write_rows_csv(all_csv, ["time", "layer", "epoch", "i", "loss", "ema_loss", "ckpt_path", "kept"], history_rows)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6), dpi=160)
        for layer in layers:
            rows = [r for r in history_rows if int(r["layer"]) == layer]
            if not rows:
                continue
            xs = [int(r["epoch"]) for r in rows]
            ys = [float(r["ema_loss"]) for r in rows]
            plt.plot(xs, ys, marker='o', linewidth=1.4, markersize=2.5, label=f"L{layer}")
        plt.xlabel("Epoch")
        plt.ylabel("EMA loss")
        plt.title("BLIP2 VisEdit E-VQA pilot500 training loss")
        plt.grid(True, alpha=0.25)
        plt.legend(ncol=2, fontsize=8)
        plt.tight_layout()
        fig_path = out_root / "loss_curves_all_layers.png"
        plt.savefig(fig_path)
        plt.close()
        return fig_path
    except Exception as e:
        (out_root / "plot_loss_error.txt").write_text(str(e), encoding='utf-8')
        return None


def make_config(base_config_path, layer):
    cfg = VEADConfig.from_yaml(str(base_config_path))
    cfg.edit_layers = [int(layer)]
    return cfg


def assert_current_editor_binding(editor, layer):
    get_llm_outpt = editor.vllm.get_llm_outpt
    owner_id = getattr(get_llm_outpt, "vead_owner_id", None)
    owner_layers = getattr(get_llm_outpt, "vead_owner_layers", None)
    expected_layers = tuple(editor.cfg.edit_layers)
    if owner_id != id(editor) or owner_layers != expected_layers:
        raise RuntimeError(
            "VEAD get_llm_outpt wrapper is not bound to the current layer editor: "
            f"layer={layer}, expected_layers={expected_layers}, owner_layers={owner_layers}. "
            "Each layer must create and bind a fresh adapter/editor."
        )


def train_one_layer(args, layer, train_data, base_config_path, vllm, vllm_data_proc):
    layer_dir = args.out_root / f"layer_{layer:02d}"
    done_file = layer_dir / "train.done"
    selected_file = layer_dir / "selected_checkpoint.tsv"
    if done_file.exists() and selected_file.exists() and not args.overwrite_train:
        log(f"[train skip] layer={layer} already done")
        return
    layer_dir.mkdir(parents=True, exist_ok=True)
    cfg = make_config(base_config_path, layer)
    editor = VEAD(vllm, cfg, args.device, vllm_data_proc, args.device, str(args.out_root / "cache" / f"layer_{layer:02d}"))
    assert_current_editor_binding(editor, layer)
    steps_per_epoch = math.ceil(len(train_data.data) / args.batch_size)
    history_path = layer_dir / "loss_history.csv"

    def after_save(ckpt_path, train_i, train_epoch, loss, ema_loss):
        append_history(history_path, {
            "time": now(), "layer": layer, "epoch": int(train_epoch), "i": int(train_i),
            "loss": float(loss), "ema_loss": float(ema_loss), "ckpt_path": ckpt_path, "kept": 1,
        })
        removed, kept = cleanup_checkpoints(layer_dir, history_path, args.keep_top_ckpts, args.keep_last_ckpts)
        log(f"[ckpt] layer={layer} epoch={train_epoch} i={train_i} loss={loss:.6f} ema={ema_loss:.6f} removed={removed} kept~={kept}")
        return False

    editor.after_save_ckpt_callback = after_save
    log(f"[train start] layer={layer} epochs={args.epochs} bs={args.batch_size} save_per_i={steps_per_epoch} {gpu_report()}")
    editor.train_init(
        train_data,
        args.batch_size,
        records_dir=str(layer_dir / "records"),
        train_name_prefix=f"pilot500_blip2_visedit_L{layer:02d}",
        save_ckpt_per_i=steps_per_epoch,
        log_per_i=max(1, steps_per_epoch // 5),
        ema_alpha=args.ema_alpha,
        random_seed=args.seed + layer,
        data_buffer_size=args.data_buffer_size,
    )
    editor.train(args.epochs)
    best = select_best_checkpoint(layer_dir, history_path)
    selected = {
        "layer": layer,
        "status": "TRAIN_DONE",
        "epoch": int(best["epoch"]),
        "i": int(best["i"]),
        "loss": float(best["loss"]),
        "ema_loss": float(best["ema_loss"]),
        "checkpoint": best["ckpt_path"],
    }
    write_selected_tsv(selected_file, [selected])
    done_file.write_text(json.dumps(selected, indent=2), encoding='utf-8')
    log(f"[train done] layer={layer} selected={best['ckpt_path']} ema={float(best['ema_loss']):.6f}")
    try:
        editor.restore_to_original_model()
        for hook in editor.adaptors_hooks.values():
            hook.remove()
    except Exception:
        pass
    del editor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def eval_one_layer(args, layer, eval_data, base_config_path, vllm):
    layer_dir = args.out_root / f"layer_{layer:02d}"
    eval_done = layer_dir / "eval_full.done"
    if eval_done.exists() and not args.overwrite_eval:
        log(f"[eval skip] layer={layer} already done")
        return json.loads(eval_done.read_text(encoding='utf-8'))
    selected_rows = list(csv.DictReader((layer_dir / "selected_checkpoint.tsv").open('r', encoding='utf-8'), delimiter='\t'))
    if not selected_rows:
        raise RuntimeError(f"missing selected checkpoint for layer {layer}")
    selected = selected_rows[0]
    ckpt_path = selected["checkpoint"]
    cfg = make_config(base_config_path, layer)
    editor = VEAD(vllm, cfg, args.device, None, None, str(args.out_root / "eval_cache"))
    assert_current_editor_binding(editor, layer)
    editor.opt = editor.get_a_new_optimizer()
    editor.load_ckpt(ckpt_path, True, False)
    eval_name = f"EVQA_full_test_pilot500_blip2_visedit_L{layer:02d}"
    result_root = layer_dir / "eval_full"
    log(f"[eval start] layer={layer} ckpt={ckpt_path} samples={len(eval_data.data)} {gpu_report()}")
    evaluator = VLLMEditorEvaluation(editor, eval_data, eval_name, str(result_root))
    evaluator.evaluate_single_edit()
    mean_path = result_root / "vead" / args.model_name / eval_name / "single_edit" / "mean_results.json"
    mean_results = json.loads(mean_path.read_text(encoding='utf-8'))
    metrics = metric_from_mean(mean_results)
    row = {
        "layer": layer,
        "status": "EVAL_DONE",
        "eval_samples": mean_results.get("sample_count", len(eval_data.data)),
        "checkpoint": ckpt_path,
        "ckpt_epoch": selected["epoch"],
        "ckpt_i": selected["i"],
        "ckpt_loss": selected["loss"],
        "ckpt_ema_loss": selected["ema_loss"],
        "result_dir": str(mean_path.parent),
    }
    row.update(metrics)
    eval_done.write_text(json.dumps(row, indent=2), encoding='utf-8')
    log(f"[eval done] layer={layer} avg={metrics['Average']:.2f}")
    try:
        editor.restore_to_original_model()
        for hook in editor.adaptors_hooks.values():
            hook.remove()
    except Exception:
        pass
    del editor, evaluator
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return row


def fmt(x):
    if x is None or x == "":
        return ""
    return f"{float(x):.2f}"


def render_outcome_md(args, layers, selected_rows, eval_rows, loss_fig):
    lines = []
    lines.append("## pliot500-blip2-visedit-sweep-outcom")
    lines.append("")
    lines.append("### Setup")
    lines.append("")
    lines.append(f"- Model: `{args.model_name}`")
    lines.append(f"- Train data: `{args.train_data}`")
    lines.append(f"- Train image root: `{args.train_img_root}`")
    lines.append(f"- Eval data: `{args.eval_data}`")
    lines.append(f"- Eval image root: `{args.eval_img_root}`")
    lines.append(f"- Layers: `{','.join(map(str, layers))}`")
    lines.append(f"- Epochs: `{args.epochs}`")
    lines.append(f"- Batch size: `{args.batch_size}`")
    lines.append("- Adapter: visual-only VisEdit / VEAD")
    lines.append("- Checkpoint selection: minimum checkpoint EMA loss per layer")
    lines.append("- Official E-VQA evaluation uses the full eval/test split, not pilot500 val.")
    lines.append("")
    lines.append("### Selected Checkpoints")
    lines.append("")
    lines.append("| Layer | Epoch | Step | Loss | EMA Loss | Checkpoint |")
    lines.append("|---:|---:|---:|---:|---:|---|")
    for r in selected_rows:
        lines.append(f"| {r['layer']} | {r['epoch']} | {r['i']} | {float(r['loss']):.6f} | {float(r['ema_loss']):.6f} | `{Path(r['checkpoint']).name}` |")
    lines.append("")
    lines.append("### Full E-VQA Evaluation")
    lines.append("")
    lines.append("| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Paper Avg | Delta Avg |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in sorted(eval_rows, key=lambda x: int(x['layer'])):
        layer = int(r['layer'])
        p = PAPER_BLIP2_EVQA.get(layer, {})
        paper_avg = p.get('Average')
        delta = float(r['Average']) - paper_avg if paper_avg is not None else None
        lines.append(
            f"| {layer} | {fmt(r['Rel'])} | {fmt(r['T-Gen'])} | {fmt(r['M-Gen'])} | {fmt(r['T-Loc'])} | {fmt(r['M-Loc'])} | {fmt(r['Average'])} | {fmt(paper_avg) if paper_avg is not None else ''} | {fmt(delta) if delta is not None else ''} |"
        )
    lines.append("")
    lines.append("### Paper Full-Train Reference")
    lines.append("")
    lines.append("| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for layer in layers:
        p = PAPER_BLIP2_EVQA.get(layer, {})
        lines.append(f"| {layer} | {fmt(p.get('Rel'))} | {fmt(p.get('T-Gen'))} | {fmt(p.get('M-Gen'))} | {fmt(p.get('T-Loc'))} | {fmt(p.get('M-Loc'))} | {fmt(p.get('Average'))} |")
    lines.append("")
    lines.append("### Loss Curves")
    lines.append("")
    if loss_fig:
        lines.append(f"![pilot500 BLIP2 VisEdit loss curves]({loss_fig})")
    else:
        lines.append("Loss curve PNG was not generated; see `loss_history_all_layers.csv`.")
    lines.append("")
    lines.append("### Interpretation Template")
    lines.append("")
    if eval_rows:
        best = max(eval_rows, key=lambda x: float(x['Average']))
        lines.append(f"- Best pilot500-trained layer by full E-VQA Average: Layer {best['layer']} with Average {float(best['Average']):.2f}.")
    lines.append("- Compare `Delta Avg` with the paper full-train reference to estimate the performance gap caused by training on pilot500 instead of full E-VQA train.")
    lines.append("- If Layer 19 remains best or near-best, pilot500 preserves the paper's layer preference; if not, pilot500 is too small or biased for layer localization validation.")
    lines.append("")
    md = "\n".join(lines) + "\n"
    out_md = args.out_root / "pliot500-blip2-visedit-sweep-outcom.md"
    out_md.write_text(md, encoding='utf-8')
    return out_md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-root', type=Path, required=True)
    ap.add_argument('--layers', default='0,5,10,15,19,25,30')
    ap.add_argument('--epochs', type=int, default=50)
    ap.add_argument('--batch-size', type=int, default=2)
    ap.add_argument('--model-name', default='blip2-opt-2.7b')
    ap.add_argument('--device', default='cuda:0')
    ap.add_argument('--train-data', type=Path, required=True)
    ap.add_argument('--train-img-root', type=Path, required=True)
    ap.add_argument('--eval-data', type=Path, required=True)
    ap.add_argument('--eval-img-root', type=Path, required=True)
    ap.add_argument('--config-path', type=Path, default=PROJECT_ROOT / 'configs/vead/blip2-opt-2.7b.yaml')
    ap.add_argument('--train-sample-n', type=int, default=None)
    ap.add_argument('--eval-sample-n', type=int, default=None)
    ap.add_argument('--seed', type=int, default=20260601)
    ap.add_argument('--ema-alpha', type=float, default=0.1)
    ap.add_argument('--data-buffer-size', type=int, default=4)
    ap.add_argument('--keep-top-ckpts', type=int, default=5)
    ap.add_argument('--keep-last-ckpts', type=int, default=2)
    ap.add_argument('--skip-train', action='store_true')
    ap.add_argument('--skip-eval', action='store_true')
    ap.add_argument('--overwrite-train', action='store_true')
    ap.add_argument('--overwrite-eval', action='store_true')
    args = ap.parse_args()

    args.model_name = get_full_model_name(args.model_name)
    args.out_root.mkdir(parents=True, exist_ok=True)
    (args.out_root / 'run_config.json').write_text(json.dumps({k: str(v) for k, v in vars(args).items()}, indent=2), encoding='utf-8')
    layers = parse_layers(args.layers)
    log(f"start layers={layers} out={args.out_root}")

    selected_rows = []
    if not args.skip_train:
        log("loading training data")
        train_data = EVQA(str(args.train_data), str(args.train_img_root), args.train_sample_n)
        log(f"train samples={len(train_data.data)}")
        log("loading BLIP2 train models")
        vllm = load_vllm_for_edit(args.model_name, args.device)
        vllm_data_proc = load_vllm_for_edit(args.model_name, args.device)
        for layer in layers:
            train_one_layer(args, layer, train_data, args.config_path, vllm, vllm_data_proc)
        del vllm, vllm_data_proc, train_data
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    for layer in layers:
        sf = args.out_root / f"layer_{layer:02d}" / "selected_checkpoint.tsv"
        if sf.exists():
            selected_rows.extend(list(csv.DictReader(sf.open('r', encoding='utf-8'), delimiter='\t')))
    write_selected_tsv(args.out_root / 'selected_checkpoints_all_layers.tsv', selected_rows)
    loss_fig = plot_loss_curves(args.out_root, layers)

    eval_rows = []
    if not args.skip_eval:
        log("loading full E-VQA eval data")
        eval_data = EVQA(str(args.eval_data), str(args.eval_img_root), args.eval_sample_n)
        log(f"eval samples={len(eval_data.data)}")
        log("loading BLIP2 eval model")
        vllm = load_vllm_for_edit(args.model_name, args.device)
        for layer in layers:
            row = eval_one_layer(args, layer, eval_data, args.config_path, vllm)
            eval_rows.append(row)
            fields = ["layer", "status", "eval_samples", "checkpoint", "ckpt_epoch", "ckpt_i", "ckpt_loss", "ckpt_ema_loss", *METRIC_COLUMNS, "result_dir"]
            write_rows_csv(args.out_root / 'full_eval_results.csv', fields, sorted(eval_rows, key=lambda x: int(x['layer'])))
        del vllm, eval_data
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    else:
        for layer in layers:
            p = args.out_root / f"layer_{layer:02d}" / "eval_full.done"
            if p.exists():
                eval_rows.append(json.loads(p.read_text(encoding='utf-8')))

    out_md = render_outcome_md(args, layers, selected_rows, eval_rows, loss_fig)
    (args.out_root / 'ALL_DONE').write_text(now() + '\n', encoding='utf-8')
    log(f"ALL_DONE md={out_md}")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
