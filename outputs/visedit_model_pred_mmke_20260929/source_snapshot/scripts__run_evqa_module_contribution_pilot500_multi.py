import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dataset.vllm import BaseVLLMEditData, EVQA
from p_track.p_track import PTrack, PTrackConfig, get_module
from utils.nethook import TraceDict


MODEL_SPECS = {
    "instructblip-vicuna-7b": {
        "loader": "instructblip",
        "model_path": "models/instructblip-vicuna-7b",
        "config_path": "configs/p_track/instructblip-vicuna-7b.yaml",
        "title": "InstructBLIP-Vicuna-7B",
    },
    "minigpt-4-vicuna-7b": {
        "loader": "visedit",
        "model_path": "models/minigpt-4-vicuna-7b",
        "config_path": "configs/p_track/minigpt-4-vicuna-7b.yaml",
        "title": "MiniGPT-4-Vicuna-7B",
    },
    "llava-v1.5-7b": {
        "loader": "llava",
        "model_path": "models/llava-v1.5-7b-hf",
        "config_path": "configs/p_track/llava-v1.5-7b.yaml",
        "title": "LLaVA-v1.5-7B",
    },
    "qwen2.5-vl-3b": {
        "loader": "qwen25vl",
        "model_path": "models/Qwen2.5-VL-3B-Instruct",
        "config_path": "configs/p_track/qwen2.5-vl-3b.yaml",
        "title": "Qwen2.5-VL-3B",
    },
    "paligemma-3b": {
        "loader": "paligemma",
        "model_path": "models/paligemma-3b-mix-224-modelscope",
        "config_path": "configs/p_track/paligemma-3b.yaml",
        "title": "PaliGemma-3B",
    },
    "smolvlm-1.7b": {
        "loader": "smolvlm",
        "model_path": "models/SmolVLM-Instruct",
        "config_path": "configs/p_track/smolvlm-1.7b.yaml",
        "title": "SmolVLM-Instruct 1.7B",
    },
}


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


def resolve_path(path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str((PROJECT_ROOT / p).resolve())


def normalize_model_name(raw: str) -> str:
    key = raw.lower().replace("_", "-").replace("/", "-")
    aliases = {
        "instructblip": "instructblip-vicuna-7b",
        "instructblip-vicuna": "instructblip-vicuna-7b",
        "minigpt4": "minigpt-4-vicuna-7b",
        "minigpt-4": "minigpt-4-vicuna-7b",
        "llava": "llava-v1.5-7b",
        "llava-v1.5-7b-hf": "llava-v1.5-7b",
        "qwen": "qwen2.5-vl-3b",
        "qwen2.5-vl-3b-instruct": "qwen2.5-vl-3b",
        "paligemma": "paligemma-3b",
        "paligemma-3b-mix-224": "paligemma-3b",
        "smolvlm": "smolvlm-1.7b",
        "smolvlm-instruct": "smolvlm-1.7b",
    }
    if key in MODEL_SPECS:
        return key
    if key in aliases:
        return aliases[key]
    for name in MODEL_SPECS:
        if name in key:
            return name
    raise ValueError(f"Unknown model name: {raw}")


def make_predict_word(text: str, leading_space: bool = True) -> str:
    text = (text or "").strip()
    return (" " + text) if leading_space else text


def build_mmke_data(data_path: str, img_root_dir: str, data_n=None):
    if data_n is None:
        data_n = 99999999
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    data_n = min(len(raw_data), data_n)
    data = []
    for i in tqdm(range(data_n), "Loading MMKE data"):
        row = raw_data[i]
        image_path = Path(row["image"])
        if not image_path.is_absolute():
            image_path = Path(img_root_dir) / image_path
        with Image.open(image_path) as image:
            pil_image = image.convert("RGB").copy()
        data.append(
            {
                "request": {
                    "image": pil_image,
                    "prompt": f"{row['src']} The answer is:",
                    "target_new": row.get("alt", ""),
                }
            }
        )
    return data


def load_contribution_data(dataset_type: str, data_path: str, img_root_dir: str, data_n=None):
    if dataset_type == "evqa":
        return EVQA(data_path, img_root_dir, data_n).data
    if dataset_type == "mmke":
        return build_mmke_data(data_path, img_root_dir, data_n)
    raise ValueError(f"Unsupported dataset_type: {dataset_type}")


def rank_desc(values):
    order = np.argsort(-values)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(values) + 1)
    return ranks, order


def signed_contribution(vs, ps, eps=1e-12):
    infl_att, infl_mlp = [], []
    for i in range(vs["att"].shape[0]):
        finite_abs = np.concatenate(
            [
                np.abs(vs["att"][i][np.isfinite(vs["att"][i])]),
                np.abs(vs["mlp"][i][np.isfinite(vs["mlp"][i])]),
            ]
        )
        denom = max(float(np.max(finite_abs)) if finite_abs.size else 0.0, eps)
        att_v = np.nan_to_num(vs["att"][i] / denom, nan=0.0, posinf=0.0, neginf=0.0)
        mlp_v = np.nan_to_num(vs["mlp"][i] / denom, nan=0.0, posinf=0.0, neginf=0.0)
        att_p = np.nan_to_num(ps["att"][i], nan=0.0, posinf=0.0, neginf=0.0)
        mlp_p = np.nan_to_num(ps["mlp"][i], nan=0.0, posinf=0.0, neginf=0.0)
        att = np.sign(att_v) * np.sqrt(np.abs(att_v) + eps) * np.sqrt(np.maximum(att_p, 0.0))
        mlp = np.sign(mlp_v) * np.sqrt(np.abs(mlp_v) + eps) * np.sqrt(np.maximum(mlp_p, 0.0))
        infl_att.append(att)
        infl_mlp.append(mlp)
    return np.stack(infl_att, axis=0), np.stack(infl_mlp, axis=0)


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_bars(out_dir, layers, attn, mlp, title, suffix="", positive=False):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 14,
            "axes.labelsize": 18,
            "axes.titlesize": 21,
            "legend.fontsize": 17,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
        }
    )
    if positive:
        attn = np.maximum(attn, 0.0)
        mlp = np.maximum(mlp, 0.0)
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    width = 0.35
    x = np.asarray(layers)
    ax.bar(x - width / 2, attn, width=width, color="green", label="Attn")
    ax.bar(x + width / 2, mlp, width=width, color="red", label="MLP")
    ax.set_xlim(-1, max(layers) + 1.5)
    ymin = min(0.0, float(np.min(attn)), float(np.min(mlp)))
    ymax = max(float(np.max(attn)), float(np.max(mlp)), 1e-4)
    pad = max((ymax - ymin) * 0.12, 1e-4)
    ax.set_ylim(ymin - pad * 0.2, ymax + pad)
    ax.set_xlabel("Layer")
    ax.set_ylabel("Module Output Contribution")
    title_suffix = " (positive)" if positive else ""
    ax.set_title(f"Module Contribution of {title}{title_suffix}", pad=14)
    xtick_step = 5 if len(layers) > 24 else 2
    ax.set_xticks(np.arange(0, max(layers) + 1, xtick_step))
    ax.legend(loc="lower left", frameon=False)
    ax.annotate(
        "",
        xy=(1.02, 0),
        xytext=(0, 0),
        xycoords=("axes fraction", "axes fraction"),
        textcoords=("axes fraction", "axes fraction"),
        arrowprops=dict(arrowstyle="->", color="black", linewidth=1.6),
    )
    ax.annotate(
        "",
        xy=(0, 1.03),
        xytext=(0, 0),
        xycoords=("axes fraction", "axes fraction"),
        textcoords=("axes fraction", "axes fraction"),
        arrowprops=dict(arrowstyle="->", color="black", linewidth=1.6),
    )
    fig.tight_layout()
    base = out_dir / f"module_contribution_bar{suffix}"
    fig.savefig(base.with_suffix(".png"))
    fig.savefig(base.with_suffix(".pdf"))
    fig.savefig(base.with_suffix(".svg"))
    plt.close(fig)
    return base.with_suffix(".png")


def module_output_tensor(output):
    h = output[0] if isinstance(output, (list, tuple)) else output
    if not torch.is_tensor(h):
        raise TypeError(f"Hooked module output is not a tensor: {type(h)}")
    return h


class HFContributionRunner:
    def __init__(self, model_name, spec, cfg, device, torch_dtype="auto", attn_implementation=None):
        self.model_name = model_name
        self.spec = spec
        self.cfg = cfg
        self.device = device
        self.model_path = resolve_path(spec["model_path"])
        self.loader = spec["loader"]
        self.torch_dtype = torch_dtype
        self.attn_implementation = attn_implementation
        self.model, self.processor = self.load_model()
        self.tokenizer = getattr(self.processor, "tokenizer", self.processor)
        self.norm = get_module(self.model, cfg.norm_path)
        self.voc = get_module(self.model, cfg.voc_path)

    def load_model(self):
        kwargs = {"device_map": self.device}
        if self.torch_dtype and self.torch_dtype != "auto":
            kwargs["torch_dtype"] = getattr(torch, self.torch_dtype)
        else:
            kwargs["torch_dtype"] = torch.float16
        if self.attn_implementation:
            kwargs["attn_implementation"] = self.attn_implementation
        if self.loader == "instructblip":
            from transformers import InstructBlipForConditionalGeneration, InstructBlipProcessor

            processor = InstructBlipProcessor.from_pretrained(self.model_path)
            model = InstructBlipForConditionalGeneration.from_pretrained(self.model_path, **kwargs)
        elif self.loader == "llava":
            from transformers import LlavaForConditionalGeneration, LlavaProcessor

            processor = LlavaProcessor.from_pretrained(self.model_path)
            model = LlavaForConditionalGeneration.from_pretrained(self.model_path, **kwargs)
        elif self.loader == "qwen25vl":
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

            processor = AutoProcessor.from_pretrained(self.model_path)
            model = Qwen2_5_VLForConditionalGeneration.from_pretrained(self.model_path, **kwargs)
        elif self.loader == "paligemma":
            from transformers import AutoProcessor, PaliGemmaForConditionalGeneration

            processor = AutoProcessor.from_pretrained(self.model_path)
            model = PaliGemmaForConditionalGeneration.from_pretrained(self.model_path, **kwargs)
        elif self.loader == "smolvlm":
            from transformers import AutoProcessor, Idefics3ForConditionalGeneration

            processor = AutoProcessor.from_pretrained(self.model_path)
            model = Idefics3ForConditionalGeneration.from_pretrained(self.model_path, **kwargs)
        else:
            raise ValueError(f"Unsupported HF loader: {self.loader}")
        return model.eval().requires_grad_(False), processor

    def build_inputs(self, prompt, image):
        if self.loader == "qwen25vl":
            from qwen_vl_utils import process_vision_info

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
        elif self.loader == "paligemma":
            inputs = self.processor(text=[prompt], images=[image], padding=True, return_tensors="pt")
        elif self.loader == "smolvlm":
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            if hasattr(self.processor, "apply_chat_template"):
                text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
                inputs = self.processor(text=[text], images=[image], padding=True, return_tensors="pt")
            else:
                inputs = self.processor(text=[prompt], images=[image], padding=True, return_tensors="pt")
        elif self.loader == "llava":
            text = prompt if "<image>" in prompt else "<image>\n" + prompt
            inputs = self.processor(images=image, text=text, return_tensors="pt")
        elif self.loader == "instructblip":
            inputs = self.processor(images=image, text=prompt, return_tensors="pt")
        else:
            inputs = self.processor(text=[prompt], images=[image], padding=True, return_tensors="pt")
        return {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inputs.items()}

    def predict_id(self, predict_word, logits):
        if predict_word is None:
            return int(torch.softmax(logits[0, -1], dim=-1).argmax())
        return int(self.tokenizer(predict_word, add_special_tokens=False).input_ids[0])

    def reps_to_word_predict(self, reps):
        return self.voc(self.norm(reps))

    def trace_one(self, prompt, image, predict_word):
        layers = [self.cfg.layer_module_tmp.format(i) for i in range(self.cfg.num_layers)]
        atts = [self.cfg.attn_module_tmp.format(i) for i in range(self.cfg.num_layers)]
        mlps = [self.cfg.mlp_module_tmp.format(i) for i in range(self.cfg.num_layers)]
        trace_layers = layers + atts + mlps
        with torch.no_grad(), TraceDict(self.model, trace_layers, retain_output=True) as td:
            inputs = self.build_inputs(prompt, image)
            output = self.model(**inputs, use_cache=False, return_dict=True)
        logits = output.logits
        pred_id = self.predict_id(predict_word, logits)
        total_p, total_v = {}, {}
        for name, tmp in [("layer", self.cfg.layer_module_tmp), ("att", self.cfg.attn_module_tmp), ("mlp", self.cfg.mlp_module_tmp)]:
            total_p[name], total_v[name] = [], []
            for layer in range(self.cfg.num_layers):
                h = module_output_tensor(td[tmp.format(layer)].output)
                h = h[0, -1] if h.dim() == 3 else h[-1]
                vocab_logits = self.reps_to_word_predict(h)
                total_p[name].append(float(torch.softmax(vocab_logits, dim=-1)[pred_id]))
                total_v[name].append(float(vocab_logits[pred_id]))
        return total_p, total_v


class VisEditContributionRunner:
    def __init__(self, model_name, spec, cfg, device):
        from utils import load_vllm_for_edit

        self.model_name = model_name
        self.spec = spec
        self.cfg = cfg
        self.vllm = load_vllm_for_edit(model_name, device)
        self.pt = PTrack(self.vllm, cfg)

    def trace_one(self, prompt, image, predict_word):
        self.pt.forward_and_trace(prompt, image)
        _, _, total_p, total_v = self.pt.p_tracking(save_results=False, predict_word=predict_word)
        if hasattr(self.pt, "td"):
            del self.pt.td
        return total_p, total_v


def build_runner(model_name, spec, cfg, device, torch_dtype, attn_implementation):
    if spec["loader"] == "visedit":
        return VisEditContributionRunner(model_name, spec, cfg, device)
    return HFContributionRunner(model_name, spec, cfg, device, torch_dtype, attn_implementation)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True, choices=sorted(MODEL_SPECS))
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--img-root-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-n", type=int, default=500)
    parser.add_argument("--dataset-type", choices=["evqa", "mmke"], default="evqa")
    parser.add_argument("--key-mode", choices=["alt", "pred", "model_pred"], default="alt")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config-path", default=None)
    parser.add_argument("--leading-space", action="store_true", default=True)
    parser.add_argument("--no-leading-space", dest="leading_space", action="store_false")
    parser.add_argument("--torch-dtype", default="auto", choices=["auto", "float16", "bfloat16", "float32"])
    parser.add_argument("--attn-implementation", default=None)
    args = parser.parse_args()
    args.device = args.device.strip()
    args.data_path = args.data_path.strip()
    args.img_root_dir = args.img_root_dir.strip()
    args.out_dir = args.out_dir.strip()
    if args.config_path is not None:
        args.config_path = args.config_path.strip()

    model_name = normalize_model_name(args.model_name)
    spec = MODEL_SPECS[model_name]
    config_path = args.config_path or spec["config_path"]
    cfg = PTrackConfig.from_yaml(config_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    sample_count = min(len(raw_data), args.data_n or len(raw_data))

    config_payload = {
        "model_name": model_name,
        "loader": spec["loader"],
        "model_path": spec["model_path"],
        "data_path": args.data_path,
        "img_root_dir": args.img_root_dir,
        "sample_count": sample_count,
        "dataset_type": args.dataset_type,
        "key_mode": args.key_mode,
        "device": args.device,
        "config_path": config_path,
        "score_formula": "sign(v/M)*sqrt(abs(v/M))*sqrt(p)",
        "rank_formula": "max(0, attn_mean)+max(0, mlp_mean)",
        "token_rule": "first token of target answer; leading space enabled unless --no-leading-space",
        "output_format_reference": "downloads/evqa_module_contribution/blip2/evqa_fullevqa_blip2_module_contribution_20260602_161102",
    }
    (out_dir / "config.json").write_text(json.dumps(config_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    data = load_contribution_data(args.dataset_type, args.data_path, args.img_root_dir, args.data_n)
    runner = build_runner(model_name, spec, cfg, args.device, args.torch_dtype, args.attn_implementation)

    keys = ["layer", "att", "mlp"]
    ps = {key: [] for key in keys}
    vs = {key: [] for key in keys}
    sample_rows = []

    for sample_idx, item in enumerate(tqdm(data, desc=f"{model_name} module contribution")):
        request = item["request"]
        if args.key_mode == "model_pred":
            predict_word = None
        elif args.key_mode == "pred":
            predict_word = make_predict_word(raw_data[sample_idx].get("pred", ""), args.leading_space)
        else:
            predict_word = make_predict_word(request["target_new"], args.leading_space)
        total_p, total_v = runner.trace_one(request["prompt"], request["image"], predict_word)
        for key in keys:
            ps[key].append(total_p[key])
            vs[key].append(total_v[key])
        for layer in range(cfg.num_layers):
            sample_rows.append(
                {
                    "sample_idx": sample_idx,
                    "layer": layer,
                    "att_p": total_p["att"][layer],
                    "att_v": total_v["att"][layer],
                    "mlp_p": total_p["mlp"][layer],
                    "mlp_v": total_v["mlp"][layer],
                    "layer_p": total_p["layer"][layer],
                    "layer_v": total_v["layer"][layer],
                }
            )
        if torch.cuda.is_available() and (sample_idx + 1) % 10 == 0:
            torch.cuda.empty_cache()

    ps = {key: np.asarray(value, dtype=np.float64) for key, value in ps.items()}
    vs = {key: np.asarray(value, dtype=np.float64) for key, value in vs.items()}
    att_infl, mlp_infl = signed_contribution(vs, ps)
    mean_att = att_infl.mean(axis=0)
    mean_mlp = mlp_infl.mean(axis=0)
    score_positive = np.maximum(mean_att, 0.0) + np.maximum(mean_mlp, 0.0)
    score_signed = mean_att + mean_mlp
    score_abs = np.abs(mean_att) + np.abs(mean_mlp)
    rank_positive, order_positive = rank_desc(score_positive)
    rank_signed, order_signed = rank_desc(score_signed)
    rank_abs, order_abs = rank_desc(score_abs)
    layers = list(range(cfg.num_layers))

    np.savez_compressed(
        out_dir / "contribution_raw.npz",
        ps_layer=ps["layer"],
        ps_att=ps["att"],
        ps_mlp=ps["mlp"],
        vs_layer=vs["layer"],
        vs_att=vs["att"],
        vs_mlp=vs["mlp"],
        att_infl=att_infl,
        mlp_infl=mlp_infl,
    )

    layer_rows = []
    for layer in layers:
        layer_rows.append(
            {
                "layer": layer,
                "attn_mean": mean_att[layer],
                "mlp_mean": mean_mlp[layer],
                "score_positive": score_positive[layer],
                "score_signed": score_signed[layer],
                "score_abs": score_abs[layer],
                "rank_positive": int(rank_positive[layer]),
                "rank_signed": int(rank_signed[layer]),
                "rank_abs": int(rank_abs[layer]),
            }
        )
    write_csv(
        out_dir / "contribution_layer.csv",
        [
            "layer",
            "attn_mean",
            "mlp_mean",
            "score_positive",
            "score_signed",
            "score_abs",
            "rank_positive",
            "rank_signed",
            "rank_abs",
        ],
        layer_rows,
    )
    write_csv(
        out_dir / "contribution_sample_layer.csv",
        ["sample_idx", "layer", "att_p", "att_v", "mlp_p", "mlp_v", "layer_p", "layer_v"],
        sample_rows,
    )

    rank_rows = []
    for pos, layer in enumerate(order_positive[: cfg.num_layers], start=1):
        rank_rows.append({"rank_type": "positive", "rank": pos, "layer": int(layer), "score": score_positive[layer]})
    for pos, layer in enumerate(order_signed[: cfg.num_layers], start=1):
        rank_rows.append({"rank_type": "signed", "rank": pos, "layer": int(layer), "score": score_signed[layer]})
    for pos, layer in enumerate(order_abs[: cfg.num_layers], start=1):
        rank_rows.append({"rank_type": "abs", "rank": pos, "layer": int(layer), "score": score_abs[layer]})
    write_csv(out_dir / "contribution_rank.csv", ["rank_type", "rank", "layer", "score"], rank_rows)

    plot_bars(out_dir, layers, mean_att, mean_mlp, spec["title"])
    plot_bars(out_dir, layers, mean_att, mean_mlp, spec["title"], suffix="_positive", positive=True)

    summary = {
        "sample_count": sample_count,
        "key_mode": args.key_mode,
        "top10_positive": [int(x) for x in order_positive[:10]],
        "top10_signed": [int(x) for x in order_signed[:10]],
        "top10_abs": [int(x) for x in order_abs[:10]],
        "outputs": {
            "layer_csv": str(out_dir / "contribution_layer.csv"),
            "rank_csv": str(out_dir / "contribution_rank.csv"),
            "sample_csv": str(out_dir / "contribution_sample_layer.csv"),
            "plot_png": str(out_dir / "module_contribution_bar.png"),
            "plot_positive_png": str(out_dir / "module_contribution_bar_positive.png"),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
