import argparse
import csv
import gc
import json
import os
import sys
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


def official_visual_forward(self, layer_outpt):
    """Original VisEdit visual-only adapter forward pass.

    Some local experiment branches add gating or text-adapter fields to
    VisionEditAdaptor.forward. The official E-VQA checkpoint is visual-only, so
    the layer sweep pins the forward logic to the original visual adapter.
    """
    if (
        not self.is_open
        or layer_outpt.shape[1] == 1
        or not getattr(self, "inpt_has_img", False)
    ):
        return layer_outpt
    vt_begin = getattr(self, "inpt_vt_begin", None)
    vt_end = getattr(self, "inpt_vt_end", None)
    if vt_begin is None or vt_end is None:
        raise BaseException("Have not set vision token range.")
    img_reps = layer_outpt[:, vt_begin:vt_end].clone()
    b1, l1, _ = img_reps.shape
    b2, l2, _ = self.edit_reps.shape
    if l1 != self.img_tok_n:
        raise BaseException("Number of selected vision tokens error.")
    if b1 != b2:
        raise BaseException("Batch size of input and editing signal are not matched.")
    if self.add_it:
        prompt_last_token_of_edit_reps = self.edit_reps[range(len(self.prompt_end)), self.prompt_end]
        inf_map = self.influence_mapper(img_reps, prompt_last_token_of_edit_reps)
        inf_map = torch.sigmoid(inf_map).unsqueeze(-1)
    else:
        inf_map = 1
    norm_img_reps = self.ln_img_reps(img_reps)
    norm_edit_reps = self.ln_edit_reps(self.edit_reps)
    x = self.mlp_begin(norm_img_reps)
    q = self.cross_att_q_mlp(x).reshape(
        b1, l1, self.cross_att_head_n, self.mid_dim // self.cross_att_head_n
    )
    k = self.cross_att_k_mlp(norm_edit_reps).reshape(
        b1, l2, self.cross_att_head_n, self.mid_dim // self.cross_att_head_n
    )
    v = self.cross_att_v_mlp(norm_edit_reps).reshape(
        b1, l2, self.cross_att_head_n, self.mid_dim // self.cross_att_head_n
    )
    s = torch.einsum("blhm,buhm->bhlu", q, k)
    s = s / (self.mid_dim // self.cross_att_head_n) ** 0.5
    s = s + (self.edit_reps_att_mask.reshape(b1, 1, 1, l2) - 1) * 9999999999
    s = torch.softmax(s, 3)
    x = torch.einsum("bhlu,buhm->blhm", s, v).reshape(b1, l1, self.mid_dim)
    x = self.mlp_end(x) * inf_map
    layer_outpt[:, vt_begin:vt_end] = img_reps + x
    return layer_outpt


VisionEditAdaptor.forward = official_visual_forward


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


BaseVLLMEditData.__load_imgs_for_data_with_img_path__ = load_imgs_with_closed_files


def parse_layers(text):
    layers = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            layers.extend(range(int(start), int(end) + 1))
        else:
            layers.append(int(part))
    return layers


def load_visual_adapter_state(ckpt_path):
    def to_jsonable(value):
        if isinstance(value, torch.Tensor):
            if value.numel() == 1:
                return value.item()
            return value.detach().cpu().tolist()
        return value

    ckpt = torch.load(ckpt_path, map_location="cpu")
    train_modules = ckpt.get("train_modules", ckpt)
    if not isinstance(train_modules, dict) or not train_modules:
        raise RuntimeError(f"No train_modules found in checkpoint: {ckpt_path}")
    source_key = next(iter(train_modules.keys()))
    source_state = train_modules[source_key]
    if not isinstance(source_state, dict):
        raise RuntimeError(f"Unexpected adapter state type for {source_key}: {type(source_state)}")
    meta = {k: to_jsonable(ckpt.get(k)) for k in ("i", "epoch", "loss", "ema_loss") if k in ckpt}
    return source_key, source_state, meta


def metric_from_mean(mean_results):
    rel = mean_results["reliability"]["acc"] * 100.0
    t_gen = mean_results["generality"]["text_rephrase"]["acc"] * 100.0
    m_gen = mean_results["generality"]["image_rephrase"]["acc"] * 100.0
    t_loc = mean_results["locality"]["text_loc"]["acc"] * 100.0
    m_loc = mean_results["locality"]["image_loc"]["acc"] * 100.0
    avg = (rel + t_gen + m_gen + t_loc + m_loc) / 5.0
    return {
        "Rel": rel,
        "T-Gen": t_gen,
        "M-Gen": m_gen,
        "T-Loc": t_loc,
        "M-Loc": m_loc,
        "Average": avg,
    }


def write_csv(csv_path, rows):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "layer",
        "status",
        "sample_count",
        "source_ckpt_layer_key",
        "ckpt_epoch",
        "ckpt_i",
        "ckpt_ema_loss",
        *METRIC_COLUMNS,
        "result_dir",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_value(row, key):
    value = row.get(key)
    if value == "" or value is None:
        return ""
    return f"{float(value):.2f}"


def write_md(md_path, rows, args, ckpt_meta, source_key):
    md_path.parent.mkdir(parents=True, exist_ok=True)
    completed = [r for r in rows if r.get("status") == "done"]
    best_avg = max(completed, key=lambda r: float(r["Average"])) if completed else None
    lines = [
        "# E-VQA Official VisEdit LLaVA Visual Adapter Layer Sweep",
        "",
        "This experiment reproduces the VisEdit LLaVA-V1.5 E-VQA visual-only editing setup. It does not train a new adapter and does not use a text editor. The official visual adapter checkpoint is attached to different LLaVA decoder layers and evaluated on the full E-VQA test split.",
        "",
        "## Setup",
        "",
        f"- Model: `{args.model_name}`",
        f"- Dataset: `{args.data_path}`",
        f"- Image root: `{args.img_root_dir}`",
        f"- Checkpoint: `{args.ckpt_path}`",
        f"- Checkpoint source train module: `{source_key}`",
        f"- Checkpoint meta: `{json.dumps(ckpt_meta, ensure_ascii=False)}`",
        f"- Layers: `{args.layers}`",
        f"- Data sample n: `{args.data_sample_n if args.data_sample_n is not None else 'full'}`",
        "",
        "## Metrics",
        "",
        "`Rel` = reliability, `T-Gen` = text generality, `M-Gen` = modal/image generality, `T-Loc` = text locality, `M-Loc` = modal/image locality. `Average` is the mean of the five metrics, matching the VisEdit paper table.",
        "",
    ]
    if best_avg:
        lines.extend(
            [
                "## Current Best",
                "",
                f"| Best by Average | Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
                f"| Official visual adapter sweep | {best_avg['layer']} | {fmt_value(best_avg, 'Rel')} | {fmt_value(best_avg, 'T-Gen')} | {fmt_value(best_avg, 'M-Gen')} | {fmt_value(best_avg, 'T-Loc')} | {fmt_value(best_avg, 'M-Loc')} | {fmt_value(best_avg, 'Average')} |",
                "",
            ]
        )
    lines.extend(
        [
            "## Layer Results",
            "",
            "| Layer | Status | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(rows, key=lambda r: int(r["layer"])):
        lines.append(
            f"| {row['layer']} | {row.get('status', '')} | {row.get('sample_count', '')} | "
            f"{fmt_value(row, 'Rel')} | {fmt_value(row, 'T-Gen')} | {fmt_value(row, 'M-Gen')} | "
            f"{fmt_value(row, 'T-Loc')} | {fmt_value(row, 'M-Loc')} | {fmt_value(row, 'Average')} |"
        )
    lines.extend(["", "## Notes", "", "- This is a visual-only adapter layer sweep. It does not include text-only or dual-modality adapters."])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_existing_rows(csv_path):
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default="llava-v1.5-7b")
    parser.add_argument("--config-path", default=None)
    parser.add_argument("--data-path", default=None)
    parser.add_argument("--img-root-dir", default=None)
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--data-sample-n", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    args.model_name = get_full_model_name(args.model_name)
    args.config_path = args.config_path or str(PROJECT_ROOT / "configs" / "vead" / f"{args.model_name}.yaml")
    args.data_path = args.data_path or os.path.join(ROOT_PATH, "data/easy-edit-mm/vqa/vqa_eval.json")
    args.img_root_dir = args.img_root_dir or os.path.join(ROOT_PATH, "data/easy-edit-mm/images")

    output_dir = Path(args.output_dir)
    csv_path = output_dir / "official_visedit_llava_evqa_visual_layer_sweep.csv"
    md_path = output_dir / "official_visedit_llava_evqa_visual_layer_sweep.md"

    source_key, source_state, ckpt_meta = load_visual_adapter_state(args.ckpt_path)
    layers = parse_layers(args.layers)
    rows = [] if args.overwrite else load_existing_rows(csv_path)
    done_layers = {int(r["layer"]) for r in rows if r.get("status") == "done"}

    print(f"[setup] project_root={PROJECT_ROOT}")
    print(f"[setup] model={args.model_name}")
    print(f"[setup] data={args.data_path}")
    print(f"[setup] image_root={args.img_root_dir}")
    print(f"[setup] ckpt={args.ckpt_path}")
    print(f"[setup] source_key={source_key}")
    print(f"[setup] layers={layers}")

    eval_data = EVQA(args.data_path, args.img_root_dir, args.data_sample_n)
    sample_count = len(eval_data.data_with_img)

    vllm = load_vllm_for_edit(args.model_name, args.device)
    base_get_llm_outpt = vllm.get_llm_outpt
    base_config = VEADConfig.from_yaml(args.config_path)

    for layer in layers:
        if layer in done_layers:
            print(f"[skip] layer={layer} already done")
            continue
        print(f"[layer {layer}] start")
        config = deepcopy(base_config)
        config.edit_layers = [layer]
        vllm.get_llm_outpt = base_get_llm_outpt
        editor = VEAD(vllm, config, args.device, None, None, os.path.join(ROOT_PATH, "data"))
        if len(editor.adaptors) != 1:
            raise RuntimeError(f"Expected one visual adaptor, got {list(editor.adaptors.keys())}")
        target_key, adaptor = next(iter(editor.adaptors.items()))
        adaptor.load_state_dict(source_state, strict=True)

        layer_dir = output_dir / f"layer_{layer:02d}"
        eval_name = f"EVQA_official_visedit_visual_layer_{layer:02d}"
        evaluator = VLLMEditorEvaluation(editor, eval_data, eval_name, str(layer_dir))
        evaluator.evaluate_single_edit()
        mean_path = layer_dir / "vead" / args.model_name / eval_name / "single_edit" / "mean_results.json"
        mean_results = json.loads(mean_path.read_text(encoding="utf-8"))
        metrics = metric_from_mean(mean_results)

        row = {
            "layer": layer,
            "status": "done",
            "sample_count": sample_count,
            "source_ckpt_layer_key": source_key,
            "ckpt_epoch": ckpt_meta.get("epoch", ""),
            "ckpt_i": ckpt_meta.get("i", ""),
            "ckpt_ema_loss": ckpt_meta.get("ema_loss", ""),
            "result_dir": str(mean_path.parent),
        }
        row.update(metrics)
        rows = [r for r in rows if int(r["layer"]) != layer]
        rows.append(row)
        write_csv(csv_path, sorted(rows, key=lambda r: int(r["layer"])))
        write_md(md_path, sorted(rows, key=lambda r: int(r["layer"])), args, ckpt_meta, source_key)
        print(f"[layer {layer}] done average={metrics['Average']:.2f}")

        editor.restore_to_original_model()
        for hook in editor.adaptors_hooks.values():
            hook.remove()
        vllm.get_llm_outpt = base_get_llm_outpt
        del editor, evaluator
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    write_csv(csv_path, sorted(rows, key=lambda r: int(r["layer"])))
    write_md(md_path, sorted(rows, key=lambda r: int(r["layer"])), args, ckpt_meta, source_key)
    print(f"[done] csv={csv_path}")
    print(f"[done] md={md_path}")


if __name__ == "__main__":
    main()

