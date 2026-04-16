import os
import csv
import json
import math
import argparse
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
import torch
import yaml
from PIL import Image
from tqdm import tqdm

from utils import load_vllm_for_edit
from utils.nethook import TraceDict


@dataclass
class Sample:
    image: Image.Image
    prompt: str
    sample_id: str


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", type=str, default="llava-v1.5-7b")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--config-path", type=str, default="configs/p_track/llava-v1.5-7b.yaml")
    parser.add_argument("--dataset-type", type=str, choices=["evqa", "eic", "jsonl"], default="evqa")
    parser.add_argument("--jsonl-path", type=str, default=None)
    parser.add_argument("--image-root", type=str, default="")
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--noise-level", type=float, default=0.30)
    parser.add_argument("--layer-start", type=int, default=0)
    parser.add_argument("--layer-end", type=int, default=-1)
    parser.add_argument("--topk-layers", type=int, default=5)
    parser.add_argument("--run-token-scan", action="store_true")
    parser.add_argument("--token-scan-samples", type=int, default=2)
    parser.add_argument("--token-scan-stride", type=int, default=4)
    parser.add_argument("--pair-scan-topk", type=int, default=4)
    parser.add_argument("--output-dir", type=str, default="records/attr_localize")
    return parser.parse_args()


def read_config(config_path: str) -> Dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_samples(args) -> List[Sample]:
    if args.dataset_type in ["evqa", "eic"]:
        if args.dataset_type == "evqa":
            from dataset.vllm import EVQA
            ds = EVQA(data_n=args.max_samples)
        else:
            from dataset.vllm import EIC
            ds = EIC(data_n=args.max_samples)
        samples = []
        for i, d in enumerate(ds.data[:args.max_samples]):
            req = d["request"]
            samples.append(Sample(image=req["image"], prompt=req["prompt"], sample_id=f"{args.dataset_type}_{i}"))
        return samples
    if args.jsonl_path is None:
        raise ValueError("dataset-type=jsonl 时必须提供 --jsonl-path")
    samples = []
    with open(args.jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= args.max_samples:
                break
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            img_path = d.get("image", d.get("img"))
            prompt = d.get("prompt", d.get("src", ""))
            if img_path is None or prompt == "":
                continue
            if not os.path.isabs(img_path):
                img_path = os.path.join(args.image_root, img_path)
            image = Image.open(img_path).convert("RGB")
            sid = str(d.get("id", i))
            samples.append(Sample(image=image, prompt=prompt, sample_id=sid))
    return samples


def safe_softmax_last(logits: torch.Tensor) -> torch.Tensor:
    p = torch.softmax(logits[0, -1], dim=-1)
    return torch.clamp(p, min=1e-12)


def kl_p0_p1(p0: torch.Tensor, p1: torch.Tensor) -> float:
    v = torch.sum(p0 * (torch.log(p0) - torch.log(p1))).item()
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return float(v)


def get_text_indices(seq_len: int, vt_range: Tuple[int, int]) -> List[int]:
    b, e = int(vt_range[0]), int(vt_range[1])
    return [i for i in range(seq_len) if i < b or i >= e]


def apply_noise_to_hidden(hs: torch.Tensor, token_ids: List[int], noise_level: float) -> torch.Tensor:
    if len(token_ids) == 0:
        return hs
    h = hs.clone()
    dev = h.device
    idx = torch.tensor(token_ids, device=dev, dtype=torch.long)
    noise = torch.randn((len(token_ids), h.shape[-1]), device=dev, dtype=h.dtype) * noise_level
    h[0, idx] = h[0, idx] + noise
    return h


def perturb_one_layer(vllm, llm_inpt, layer_name: str, token_ids: List[int], noise_level: float) -> torch.Tensor:
    def edit_output(output, layer=None):
        if layer != layer_name:
            return output
        if isinstance(output, tuple):
            hs = output[0]
            hs = apply_noise_to_hidden(hs, token_ids, noise_level)
            return (hs,) + output[1:]
        if isinstance(output, list):
            hs = output[0]
            hs = apply_noise_to_hidden(hs, token_ids, noise_level)
            out = list(output)
            out[0] = hs
            return out
        return apply_noise_to_hidden(output, token_ids, noise_level)

    with torch.no_grad(), TraceDict(
        vllm.model,
        [layer_name],
        with_kwargs=True,
        edit_output=edit_output,
        clone=True,
        detach=True
    ):
        out = vllm.get_llm_outpt(llm_inpt, None).logits
    return out


def perturb_two_layers(vllm, llm_inpt, layer_name_v: str, token_ids_v: List[int], layer_name_t: str, token_ids_t: List[int], noise_level: float) -> torch.Tensor:
    layers = [layer_name_v, layer_name_t]

    def edit_output(output, layer=None):
        if layer == layer_name_v:
            ids = token_ids_v
        elif layer == layer_name_t:
            ids = token_ids_t
        else:
            return output
        if isinstance(output, tuple):
            hs = output[0]
            hs = apply_noise_to_hidden(hs, ids, noise_level)
            return (hs,) + output[1:]
        if isinstance(output, list):
            hs = output[0]
            hs = apply_noise_to_hidden(hs, ids, noise_level)
            out = list(output)
            out[0] = hs
            return out
        return apply_noise_to_hidden(output, ids, noise_level)

    with torch.no_grad(), TraceDict(
        vllm.model,
        layers,
        with_kwargs=True,
        edit_output=edit_output,
        clone=True,
        detach=True
    ):
        out = vllm.get_llm_outpt(llm_inpt, None).logits
    return out


def mean_hidden_norm_from_attn_input(attn_input, vis_ids: List[int], txt_ids: List[int]) -> Tuple[float, float]:
    args, kargs = attn_input
    hs = kargs["hidden_states"]
    if hs.dim() == 2:
        hs = hs.unsqueeze(0)
    vis_norm = torch.norm(hs[0, vis_ids], dim=-1).mean().item() if len(vis_ids) > 0 else 0.0
    txt_norm = torch.norm(hs[0, txt_ids], dim=-1).mean().item() if len(txt_ids) > 0 else 0.0
    return float(vis_norm), float(txt_norm)


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    cfg = read_config(args.config_path)
    num_layers = int(cfg["num_layers"])
    layer_tmp = cfg["layer_module_tmp"]
    attn_tmp = cfg["attn_module_tmp"]

    layer_start = max(0, args.layer_start)
    layer_end = num_layers if args.layer_end < 0 else min(num_layers, args.layer_end)
    layers = list(range(layer_start, layer_end))
    layer_names = [layer_tmp.format(i) for i in layers]
    attn_names = [attn_tmp.format(i) for i in layers]

    samples = load_samples(args)
    if len(samples) == 0:
        raise RuntimeError("没有可用样本")

    vllm = load_vllm_for_edit(args.model_name, args.device)

    kl_visual = {i: [] for i in layers}
    kl_text = {i: [] for i in layers}
    kl_joint = {i: [] for i in layers}
    attn_visual = {i: [] for i in layers}
    attn_text = {i: [] for i in layers}

    for sample in tqdm(samples, desc="Phase A scan"):
        llm_inpt, vt_range = vllm.get_llm_input_embeds([sample.prompt], [sample.image])
        seq_len = int(llm_inpt["inputs_embeds"].shape[1])
        vis_ids = list(range(int(vt_range[0]), int(vt_range[1])))
        txt_ids = get_text_indices(seq_len, vt_range)

        with torch.no_grad(), TraceDict(
            vllm.model,
            attn_names,
            retain_input=True,
            with_kwargs=True,
            clone=True,
            detach=True
        ) as td_att:
            out_base = vllm.get_llm_outpt(llm_inpt, vt_range).logits
        p0 = safe_softmax_last(out_base)

        for li, ln, an in zip(layers, layer_names, attn_names):
            v_norm, t_norm = mean_hidden_norm_from_attn_input(td_att[an].input, vis_ids, txt_ids)
            attn_visual[li].append(v_norm)
            attn_text[li].append(t_norm)

            p_vis = safe_softmax_last(perturb_one_layer(vllm, llm_inpt, ln, vis_ids, args.noise_level))
            p_txt = safe_softmax_last(perturb_one_layer(vllm, llm_inpt, ln, txt_ids, args.noise_level))
            p_jnt = safe_softmax_last(perturb_one_layer(vllm, llm_inpt, ln, vis_ids + txt_ids, args.noise_level))

            kl_visual[li].append(kl_p0_p1(p0, p_vis))
            kl_text[li].append(kl_p0_p1(p0, p_txt))
            kl_joint[li].append(kl_p0_p1(p0, p_jnt))

    rows = []
    for li in layers:
        row = {
            "layer": li,
            "attn_visual": float(np.mean(attn_visual[li])) if attn_visual[li] else 0.0,
            "attn_text": float(np.mean(attn_text[li])) if attn_text[li] else 0.0,
            "kl_visual": float(np.mean(kl_visual[li])) if kl_visual[li] else 0.0,
            "kl_text": float(np.mean(kl_text[li])) if kl_text[li] else 0.0,
            "kl_joint": float(np.mean(kl_joint[li])) if kl_joint[li] else 0.0,
        }
        row["score_visual"] = row["kl_visual"]
        row["score_text"] = row["kl_text"]
        row["score_joint"] = row["kl_joint"]
        rows.append(row)

    rows_sorted_v = sorted(rows, key=lambda x: x["score_visual"], reverse=True)
    rows_sorted_t = sorted(rows, key=lambda x: x["score_text"], reverse=True)
    top_v = [r["layer"] for r in rows_sorted_v[: args.topk_layers]]
    top_t = [r["layer"] for r in rows_sorted_t[: args.topk_layers]]

    write_csv(
        os.path.join(args.output_dir, "phaseA_layer_scores.csv"),
        rows,
        ["layer", "attn_visual", "attn_text", "kl_visual", "kl_text", "kl_joint", "score_visual", "score_text", "score_joint"],
    )

    pair_rows = []
    pair_v = top_v[: args.pair_scan_topk]
    pair_t = top_t[: args.pair_scan_topk]
    pair_samples = samples[: min(8, len(samples))]
    for lv in tqdm(pair_v, desc="Phase C pair scan"):
        for lt in pair_t:
            scores = []
            ln_v = layer_tmp.format(lv)
            ln_t = layer_tmp.format(lt)
            for sample in pair_samples:
                llm_inpt, vt_range = vllm.get_llm_input_embeds([sample.prompt], [sample.image])
                seq_len = int(llm_inpt["inputs_embeds"].shape[1])
                vis_ids = list(range(int(vt_range[0]), int(vt_range[1])))
                txt_ids = get_text_indices(seq_len, vt_range)
                out_base = vllm.get_llm_outpt(llm_inpt, vt_range).logits
                p0 = safe_softmax_last(out_base)
                out_pair = perturb_two_layers(vllm, llm_inpt, ln_v, vis_ids, ln_t, txt_ids, args.noise_level)
                p1 = safe_softmax_last(out_pair)
                scores.append(kl_p0_p1(p0, p1))
            pair_rows.append(
                {
                    "visual_layer": lv,
                    "text_layer": lt,
                    "pair_kl": float(np.mean(scores)) if scores else 0.0,
                }
            )
    pair_rows = sorted(pair_rows, key=lambda x: x["pair_kl"], reverse=True)
    write_csv(os.path.join(args.output_dir, "phaseC_pair_scores.csv"), pair_rows, ["visual_layer", "text_layer", "pair_kl"])

    token_rows = []
    if args.run_token_scan and len(top_v) > 0:
        token_layers = top_v[: min(3, len(top_v))]
        token_samples = samples[: min(args.token_scan_samples, len(samples))]
        for li in tqdm(token_layers, desc="Phase B token scan"):
            ln = layer_tmp.format(li)
            tok_scores: Dict[int, List[float]] = {}
            for sample in token_samples:
                llm_inpt, vt_range = vllm.get_llm_input_embeds([sample.prompt], [sample.image])
                vis_ids = list(range(int(vt_range[0]), int(vt_range[1]), max(1, args.token_scan_stride)))
                out_base = vllm.get_llm_outpt(llm_inpt, vt_range).logits
                p0 = safe_softmax_last(out_base)
                for tid in vis_ids:
                    p1 = safe_softmax_last(perturb_one_layer(vllm, llm_inpt, ln, [tid], args.noise_level))
                    tok_scores.setdefault(tid, []).append(kl_p0_p1(p0, p1))
            for tid, vals in tok_scores.items():
                token_rows.append(
                    {
                        "layer": li,
                        "token_id": tid,
                        "token_kl": float(np.mean(vals)) if vals else 0.0,
                    }
                )
        token_rows = sorted(token_rows, key=lambda x: x["token_kl"], reverse=True)
        write_csv(os.path.join(args.output_dir, "phaseB_token_scores.csv"), token_rows, ["layer", "token_id", "token_kl"])

    summary = {
        "top_visual_layers": top_v,
        "top_text_layers": top_t,
        "best_pair": pair_rows[0] if pair_rows else None,
        "output_dir": args.output_dir,
        "sample_count": len(samples),
    }
    with open(os.path.join(args.output_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
