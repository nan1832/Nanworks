import argparse
import csv
import json
import os
import re
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

from p_track.p_track import PTrackConfig
from scripts.run_evqa_module_contribution_pilot500_multi import (
    build_runner,
    plot_bars,
    signed_contribution,
    write_csv,
)


MODEL_SPECS = {
    "blip2-opt-2.7b": {
        "loader": "visedit",
        "model_path": "models/blip2-opt-2.7b",
        "config_path": "configs/p_track/blip2-opt-2.7b.yaml",
        "title": "BLIP2-OPT-2.7B",
    },
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
        "title": "SmolVLM-Instruct-1.7B",
    },
}

MODEL_ALIASES = {
    "blip2": "blip2-opt-2.7b",
    "instructblip": "instructblip-vicuna-7b",
    "minigpt4": "minigpt-4-vicuna-7b",
    "minigpt-4": "minigpt-4-vicuna-7b",
    "llava": "llava-v1.5-7b",
    "qwen": "qwen2.5-vl-3b",
    "qwen2.5-vl-3b-instruct": "qwen2.5-vl-3b",
    "paligemma": "paligemma-3b",
    "smolvlm": "smolvlm-1.7b",
    "smolvlm-instruct": "smolvlm-1.7b",
}

GENERIC_WORDS = {
    "the",
    "a",
    "an",
    "this",
    "that",
    "these",
    "those",
    "it",
    "there",
    "human",
    "person",
    "people",
    "man",
    "woman",
    "image",
    "picture",
    "photo",
    "depicted",
    "shown",
    "corresponds",
    "correspond",
    "called",
    "named",
    "is",
    "are",
    "was",
    "were",
    "in",
    "on",
    "of",
    "to",
    "with",
    "and",
    "or",
    "as",
    "for",
    "about",
    "usually",
    "commonly",
    "gesture",
    "life",
    "visual",
    "object",
    "thing",
    "yes",
    "no",
}

TEMPLATE_PHRASES_ENTITY = [
    "the human in the image corresponds to",
    "the person in the image corresponds to",
    "the human in the picture corresponds to",
    "the person in the picture corresponds to",
    "the image shows",
    "the picture shows",
]

TEMPLATE_PHRASES_VISUAL = [
    "this is the",
    "this is a",
    "this is an",
    "the image shows",
    "the picture shows",
    "it usually signifies",
    "it means",
]


def normalize_model_name(raw):
    key = raw.lower().replace("_", "-").replace("/", "-")
    if key in MODEL_SPECS:
        return key
    if key in MODEL_ALIASES:
        return MODEL_ALIASES[key]
    for name in MODEL_SPECS:
        if name in key:
            return name
    raise ValueError(f"Unknown model name: {raw}")


def normalize_word(word):
    return re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", word or "").lower()


def basic_word_tokenize(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9._'/-]*", text or "")


def strip_template(text, templates):
    stripped = (text or "").strip()
    low = stripped.lower()
    for template in templates:
        if low.startswith(template):
            return stripped[len(template) :].strip(" :,.\n\t")
    return stripped


def first_content_word(text, allow_generic=False):
    words = basic_word_tokenize(text)
    first_any = None
    for word in words:
        norm = normalize_word(word)
        if not norm:
            continue
        if first_any is None:
            first_any = word
        if norm not in GENERIC_WORDS:
            return word
    return first_any if allow_generic else None


def extract_key_token(row, dataset_name):
    alt = row.get("alt", "")
    if dataset_name == "mmke-entity":
        token = first_content_word(strip_template(alt, TEMPLATE_PHRASES_ENTITY))
        if token:
            return token, "alt_entity_anchor", False
        for field in ["rel_ans_1", "rel_ans_2", "m_rel_ans_1", "m_rel_ans_2"]:
            token = first_content_word(row.get(field, ""))
            if token:
                return token, f"{field}_fallback", True
        generic = first_content_word(alt, allow_generic=True)
        return generic, "excluded_no_entity_anchor", True

    if dataset_name == "mmke-visual":
        for field, source in [
            ("m_rel_ans", "m_rel_ans_visual_semantic"),
            ("rel_ans", "rel_ans_visual_semantic"),
        ]:
            token = first_content_word(row.get(field, ""))
            if token:
                return token, source, False
        token = first_content_word(strip_template(alt, TEMPLATE_PHRASES_VISUAL))
        if token:
            return token, "alt_visual_semantic_anchor", False
        generic = first_content_word(alt, allow_generic=True)
        return generic, "excluded_no_visual_semantic_anchor", True

    raise ValueError(f"Unsupported dataset: {dataset_name}")


def make_predict_word(text, leading_space=True):
    text = (text or "").strip()
    return (" " + text) if leading_space else text


def tokenizer_encode(tokenizer, predict_word):
    try:
        ids = tokenizer(predict_word, add_special_tokens=False).input_ids
    except TypeError:
        ids = tokenizer(predict_word, add_special_tokens=False)["input_ids"]
    if ids and isinstance(ids[0], list):
        ids = ids[0]
    return [int(x) for x in ids]


def tokenizer_decode(tokenizer, token_id):
    try:
        return tokenizer.decode([int(token_id)])
    except Exception:
        return tokenizer.decode(int(token_id))


def get_runner_tokenizer(runner):
    if hasattr(runner, "tokenizer"):
        return runner.tokenizer
    if hasattr(runner, "pt") and hasattr(runner.pt, "tokenizer"):
        return runner.pt.tokenizer
    if hasattr(runner, "vllm") and hasattr(runner.vllm, "get_llm_tokenizer"):
        return runner.vllm.get_llm_tokenizer()
    raise AttributeError("Cannot find tokenizer on runner")


def resolve_image(row, img_root_dir):
    image_path = Path(row["image"])
    if not image_path.is_absolute():
        image_path = Path(img_root_dir) / image_path
    return image_path


def build_prompt(row, prompt_suffix):
    prompt = row.get("src", "")
    if prompt_suffix:
        prompt = f"{prompt}{prompt_suffix}"
    return prompt


def moving_average(values, window=3):
    values = np.asarray(values, dtype=np.float64)
    radius = window // 2
    out = []
    for idx in range(len(values)):
        lo = max(0, idx - radius)
        hi = min(len(values), idx + radius + 1)
        out.append(float(np.mean(values[lo:hi])))
    return np.asarray(out, dtype=np.float64)


def find_high_region(smoothed, lambda_value=0.5):
    smoothed = np.asarray(smoothed, dtype=np.float64)
    threshold = float(np.mean(smoothed) + lambda_value * np.std(smoothed))
    mask = smoothed >= threshold
    best = None
    start = None
    for idx, flag in enumerate(mask.tolist() + [False]):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            end = idx - 1
            score_sum = float(np.sum(smoothed[start : end + 1]))
            cand = (end - start + 1, score_sum, -start, start, end)
            if best is None or cand > best:
                best = cand
            start = None
    if best is None:
        return None, threshold, []
    _, _, _, s_h, e_h = best
    return (int(s_h), int(e_h)), threshold, [int(i) for i in np.where(mask)[0]]


def pre_candidates(start_layer, top_k):
    layers = []
    layer = start_layer - 1
    while len(layers) < top_k and layer >= 0:
        layers.append(int(layer))
        layer -= 1
    return layers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--dataset-name", required=True, choices=["mmke-visual", "mmke-entity"])
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--img-root-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-n", type=int, default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config-path", default=None)
    parser.add_argument("--prompt-suffix", default=" The answer is:")
    parser.add_argument("--leading-space", action="store_true", default=True)
    parser.add_argument("--no-leading-space", dest="leading_space", action="store_false")
    parser.add_argument("--min-valid-ratio", type=float, default=0.70)
    parser.add_argument("--min-valid-samples", type=int, default=100)
    parser.add_argument("--smoothing-window", type=int, default=3)
    parser.add_argument("--lambda-value", type=float, default=0.5)
    parser.add_argument("--torch-dtype", default="auto", choices=["auto", "float16", "bfloat16", "float32"])
    parser.add_argument("--attn-implementation", default=None)
    args = parser.parse_args()

    model_name = normalize_model_name(args.model_name)
    spec = MODEL_SPECS[model_name]
    cfg = PTrackConfig.from_yaml(args.config_path or spec["config_path"])
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    sample_count = min(len(raw_data), args.data_n or len(raw_data))
    raw_data = raw_data[:sample_count]

    runner = build_runner(model_name, spec, cfg, args.device, args.torch_dtype, args.attn_implementation)
    tokenizer = get_runner_tokenizer(runner)

    config_payload = {
        "method": "VisEdit-Contrib-Pre-KeyToken",
        "dataset_name": args.dataset_name,
        "model_name": model_name,
        "sample_count": sample_count,
        "data_path": args.data_path,
        "img_root_dir": args.img_root_dir,
        "prompt_suffix": args.prompt_suffix,
        "key_mode": "dataset_key_token",
        "rank_metric": "score_positive_key_token",
        "candidate_conversion": "pre_before_high_contribution_region",
        "smoothing_window": args.smoothing_window,
        "lambda_value": args.lambda_value,
        "min_valid_ratio": args.min_valid_ratio,
        "min_valid_samples": args.min_valid_samples,
        "config_path": args.config_path or spec["config_path"],
    }
    (out_dir / "config.json").write_text(json.dumps(config_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    sample_manifest_rows = []
    key_manifest_rows = []
    run_items = []
    total = 0
    valid_key = 0
    generic_count = 0
    fallback_count = 0
    image_missing_count = 0

    for sample_idx, row in enumerate(raw_data):
        total += 1
        image_path = resolve_image(row, args.img_root_dir)
        image_exists = image_path.exists()
        if not image_exists:
            image_missing_count += 1
        token_text, token_source, fallback = extract_key_token(row, args.dataset_name)
        generic = normalize_word(token_text) in GENERIC_WORDS if token_text else True
        predict_word = make_predict_word(token_text, args.leading_space) if token_text else ""
        token_ids = tokenizer_encode(tokenizer, predict_word) if predict_word else []
        key_token_id = token_ids[0] if token_ids else None
        decoded = tokenizer_decode(tokenizer, key_token_id) if key_token_id is not None else ""
        used = image_exists and key_token_id is not None and not generic and not fallback
        if key_token_id is not None and not generic:
            valid_key += 1
        if generic:
            generic_count += 1
        if fallback:
            fallback_count += 1

        skip_reason = ""
        if not image_exists:
            skip_reason = "image_missing"
        elif key_token_id is None:
            skip_reason = "key_token_id_missing"
        elif generic:
            skip_reason = "generic_key_token"
        elif fallback:
            skip_reason = "fallback_excluded_from_main"

        sample_manifest_rows.append(
            {
                "dataset": args.dataset_name,
                "subset": "train",
                "sample_id": sample_idx,
                "image_path": str(image_path),
                "image_exists": image_exists,
                "src_hash": hash(row.get("src", "")),
                "alt_hash": hash(row.get("alt", "")),
                "pred_hash": hash(row.get("pred", "")),
                "used_for_localization": used,
                "skip_reason": skip_reason,
            }
        )
        key_manifest_rows.append(
            {
                "dataset": args.dataset_name,
                "subset": "train",
                "model": model_name,
                "sample_id": sample_idx,
                "alt_raw": row.get("alt", ""),
                "pred_raw": row.get("pred", ""),
                "key_phrase_text": token_text or "",
                "key_phrase_source": token_source,
                "key_phrase_token_ids": json.dumps(token_ids, ensure_ascii=False),
                "key_phrase_token_count": len(token_ids),
                "key_token_text": token_text or "",
                "predict_word": predict_word,
                "key_token_source": token_source,
                "key_token_id": key_token_id if key_token_id is not None else "",
                "key_token_position": 0 if key_token_id is not None else "",
                "key_token_subtoken_ids": json.dumps(token_ids, ensure_ascii=False),
                "used_subtoken_index": 0 if key_token_id is not None else "",
                "leading_space": args.leading_space,
                "tokenizer_decoded_key_token": decoded,
                "tokenizer_family": type(tokenizer).__name__,
                "key_token_is_first_subtoken_of_phrase": bool(key_token_id is not None),
                "generic_key_token": generic,
                "used_in_main_score": used,
                "skip_reason": skip_reason,
            }
        )
        if used:
            run_items.append((sample_idx, row, image_path, predict_word, token_text, key_token_id))

    write_csv(
        out_dir / "sample_manifest.csv",
        [
            "dataset",
            "subset",
            "sample_id",
            "image_path",
            "image_exists",
            "src_hash",
            "alt_hash",
            "pred_hash",
            "used_for_localization",
            "skip_reason",
        ],
        sample_manifest_rows,
    )
    write_csv(
        out_dir / "key_token_manifest.csv",
        list(key_manifest_rows[0].keys()) if key_manifest_rows else [],
        key_manifest_rows,
    )

    min_valid_samples = min(args.min_valid_samples, int(np.ceil(args.min_valid_ratio * total)))
    used_ratio = len(run_items) / max(total, 1)
    pre_status = "pass"
    pre_failure = ""
    if len(run_items) < min_valid_samples or used_ratio < args.min_valid_ratio:
        pre_status = "low_valid_key_token_coverage"
        pre_failure = f"used={len(run_items)}/{total}, min_valid_samples={min_valid_samples}, min_valid_ratio={args.min_valid_ratio}"

    coverage = {
        "dataset": args.dataset_name,
        "model": model_name,
        "total_sample_count": total,
        "valid_key_token_count": valid_key,
        "generic_key_token_count": generic_count,
        "generic_key_token_ratio": generic_count / max(total, 1),
        "used_in_main_score_count": len(run_items),
        "used_in_main_score_ratio": used_ratio,
        "fallback_key_token_count": fallback_count,
        "fallback_key_token_ratio": fallback_count / max(total, 1),
        "image_missing_count": image_missing_count,
        "manual_checked_count": 0,
        "manual_error_count": 0,
        "manual_error_ratio": 0.0,
        "status": pre_status,
        "failure_reason": pre_failure,
    }
    (out_dir / "key_token_coverage_report.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    keys = ["layer", "att", "mlp"]
    ps = {key: [] for key in keys}
    vs = {key: [] for key in keys}
    sample_rows = []

    for sample_idx, row, image_path, predict_word, token_text, key_token_id in tqdm(
        run_items, desc=f"{args.dataset_name}/{model_name} key-token contribution"
    ):
        with Image.open(image_path) as image:
            pil_image = image.convert("RGB").copy()
        prompt = build_prompt(row, args.prompt_suffix)
        total_p, total_v = runner.trace_one(prompt, pil_image, predict_word)
        for key in keys:
            ps[key].append(total_p[key])
            vs[key].append(total_v[key])
        for layer in range(cfg.num_layers):
            sample_rows.append(
                {
                    "dataset": args.dataset_name,
                    "subset": "train",
                    "model": model_name,
                    "sample_id": sample_idx,
                    "layer": layer,
                    "module_type": "att",
                    "key_token_text": token_text,
                    "key_token_id": key_token_id,
                    "p_value": total_p["att"][layer],
                    "v_logit": total_v["att"][layer],
                    "v_norm": "",
                    "contribution_signed": "",
                    "used_in_main_score": True,
                }
            )
            sample_rows.append(
                {
                    "dataset": args.dataset_name,
                    "subset": "train",
                    "model": model_name,
                    "sample_id": sample_idx,
                    "layer": layer,
                    "module_type": "mlp",
                    "key_token_text": token_text,
                    "key_token_id": key_token_id,
                    "p_value": total_p["mlp"][layer],
                    "v_logit": total_v["mlp"][layer],
                    "v_norm": "",
                    "contribution_signed": "",
                    "used_in_main_score": True,
                }
            )
        if torch.cuda.is_available() and (len(ps["att"]) % 10 == 0):
            torch.cuda.empty_cache()

    if not run_items:
        summary = {
            "dataset": args.dataset_name,
            "model": model_name,
            "method": "VisEdit-Contrib-Pre-KeyToken",
            "status": pre_status,
            "failure_reason": pre_failure or "no_valid_key_token_samples",
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    ps = {key: np.asarray(value, dtype=np.float64) for key, value in ps.items()}
    vs = {key: np.asarray(value, dtype=np.float64) for key, value in vs.items()}
    att_infl, mlp_infl = signed_contribution(vs, ps)
    mean_att = att_infl.mean(axis=0)
    mean_mlp = mlp_infl.mean(axis=0)
    score_positive = np.maximum(mean_att, 0.0) + np.maximum(mean_mlp, 0.0)
    score_signed = mean_att + mean_mlp
    score_abs = np.abs(mean_att) + np.abs(mean_mlp)
    smoothed = moving_average(score_positive, args.smoothing_window)
    region, threshold, high_layers = find_high_region(smoothed, args.lambda_value)

    if region is None:
        status = "no_high_contribution_region"
        failure_reason = "no layer above threshold"
        top3_pre, top5_pre = [], []
        region_start = region_end = ""
    else:
        region_start, region_end = region
        top3_pre = pre_candidates(region_start, 3)
        top5_pre = pre_candidates(region_start, 5)
        if len(top3_pre) < 3:
            status = "insufficient_pre_layers"
            failure_reason = f"region_start={region_start}"
        else:
            status = "done" if pre_status == "pass" else pre_status
            failure_reason = pre_failure

    order_positive = np.argsort(-score_positive)
    order_signed = np.argsort(-score_signed)
    order_abs = np.argsort(-score_abs)
    rank_positive = np.empty_like(order_positive)
    rank_signed = np.empty_like(order_signed)
    rank_abs = np.empty_like(order_abs)
    rank_positive[order_positive] = np.arange(1, len(order_positive) + 1)
    rank_signed[order_signed] = np.arange(1, len(order_signed) + 1)
    rank_abs[order_abs] = np.arange(1, len(order_abs) + 1)

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
    for layer in range(cfg.num_layers):
        layer_rows.append(
            {
                "dataset": args.dataset_name,
                "subset": "train",
                "model": model_name,
                "method": "VisEdit-Contrib-Pre-KeyToken",
                "key_mode": "dataset_key_token",
                "key_token_rule": "dataset_specific_key_token",
                "layer": layer,
                "attn_mean": mean_att[layer],
                "mlp_mean": mean_mlp[layer],
                "score_positive": score_positive[layer],
                "score_signed": score_signed[layer],
                "score_abs": score_abs[layer],
                "score_positive_smoothed": smoothed[layer],
                "rank_positive": int(rank_positive[layer]),
                "rank_signed": int(rank_signed[layer]),
                "rank_abs": int(rank_abs[layer]),
                "total_sample_count": total,
                "valid_sample_count": len(run_items),
                "generic_key_token_count": generic_count,
                "generic_key_token_ratio": generic_count / max(total, 1),
                "status": status,
                "failure_reason": failure_reason,
            }
        )
    write_csv(out_dir / "layer_scores.csv", list(layer_rows[0].keys()), layer_rows)
    write_csv(out_dir / "contribution_layer.csv", list(layer_rows[0].keys()), layer_rows)
    write_csv(out_dir / "sample_layer_contribution.csv", list(sample_rows[0].keys()) if sample_rows else [], sample_rows)

    high_region_payload = {
        "dataset": args.dataset_name,
        "model": model_name,
        "method": "VisEdit-Contrib-Pre-KeyToken",
        "rank_metric": "score_positive_key_token",
        "smoothing_window": args.smoothing_window,
        "lambda": args.lambda_value,
        "threshold_rule": "mean + lambda * std",
        "threshold": threshold,
        "high_layers": high_layers,
        "selected_region": [region_start, region_end] if region is not None else [],
        "status": status,
        "failure_reason": failure_reason,
    }
    (out_dir / "high_contribution_region.json").write_text(
        json.dumps(high_region_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    candidate_rows = []
    for top_k, layers in [(3, top3_pre), (5, top5_pre)]:
        for rank, layer in enumerate(layers, start=1):
            candidate_rows.append(
                {
                    "dataset": args.dataset_name,
                    "subset": "train",
                    "model": model_name,
                    "method": "VisEdit-Contrib-Pre-KeyToken",
                    "variant": "pre",
                    "top_k": top_k,
                    "rank": rank,
                    "layer": layer,
                    "score_positive": score_positive[layer],
                    "score_positive_smoothed": smoothed[layer],
                    "high_contribution_region_start": region_start,
                    "high_contribution_region_end": region_end,
                    "candidate_conversion": "pre_before_high_contribution_region",
                    "status": status,
                    "failure_reason": failure_reason,
                }
            )
    if candidate_rows:
        write_csv(out_dir / "candidate_layers_topk.csv", list(candidate_rows[0].keys()), candidate_rows)
    else:
        write_csv(
            out_dir / "candidate_layers_topk.csv",
            [
                "dataset",
                "subset",
                "model",
                "method",
                "variant",
                "top_k",
                "rank",
                "layer",
                "score_positive",
                "score_positive_smoothed",
                "high_contribution_region_start",
                "high_contribution_region_end",
                "candidate_conversion",
                "status",
                "failure_reason",
            ],
            [],
        )

    plot_bars(out_dir, list(range(cfg.num_layers)), mean_att, mean_mlp, spec["title"])
    plot_bars(out_dir, list(range(cfg.num_layers)), mean_att, mean_mlp, spec["title"], suffix="_positive", positive=True)

    summary = {
        "dataset": args.dataset_name,
        "model": model_name,
        "method": "VisEdit-Contrib-Pre-KeyToken",
        "key_mode": "dataset_key_token",
        "valid_sample_count": len(run_items),
        "total_sample_count": total,
        "generic_key_token_ratio": generic_count / max(total, 1),
        "fallback_key_token_ratio": fallback_count / max(total, 1),
        "top3_direct_layers": [int(x) for x in order_positive[:3]],
        "top5_direct_layers": [int(x) for x in order_positive[:5]],
        "high_contribution_region": [region_start, region_end] if region is not None else [],
        "top3_pre_layers": top3_pre,
        "top5_pre_layers": top5_pre,
        "status": status,
        "failure_reason": failure_reason,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(out_dir / "contribution_summary.csv", list(summary.keys()), [summary])
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
