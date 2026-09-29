#!/usr/bin/env python3
import argparse
import csv
import gc
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from p_track.p_track import PTrackConfig  # noqa: E402
from utils import find_module, load_vllm_for_edit  # noqa: E402

from run_ours_direct_candidate_layers_qwen_chatfix import (  # noqa: E402
    CONFIG_PATHS,
    DATASET_DISPLAY,
    DATASET_ORDER,
    DEFAULT_DATASETS,
    MODEL_DISPLAY,
    MODEL_ORDER,
    clean_generated_text,
    ensure_model_pred_cache,
    get_sample_id,
    load_edit_data,
    normalize_model_name,
)


METHOD_NAME = "LGA-Param-Direct-AltModelPred"
SCORE_SOURCE = "raw_old_new_parameter_gradient_dot"
EPS = 1e-12


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def normalize_answer(text: Any) -> str:
    return " ".join(str(text or "").strip().lower().split())


def get_logits(output: Any) -> Any:
    if hasattr(output, "logits"):
        return output.logits
    if isinstance(output, (tuple, list)):
        return output[0]
    raise TypeError(f"Cannot read logits from output type: {type(output)}")


def model_pred_cache_row_ok(row: Dict[str, Any]) -> bool:
    return str(row.get("status", "")) == "ok" and bool(str(row.get("answer", "")).strip())


def prepare_mlp_weight_modules(vllm: Any, cfg: Any, model_name: str, include_bias: bool = False) -> List[Dict[str, Any]]:
    for param in vllm.model.parameters():
        param.requires_grad_(False)

    modules: List[Dict[str, Any]] = []
    for layer in range(int(cfg.num_layers)):
        if model_name == "blip2-opt-2.7b" and hasattr(cfg, "layer_module_tmp"):
            module_path = cfg.layer_module_tmp.format(layer)
        else:
            module_path = cfg.mlp_module_tmp.format(layer)
        module = find_module(vllm.model, module_path)
        named_params: List[Tuple[str, Any]] = []
        for name, param in module.named_parameters(recurse=True):
            if model_name == "blip2-opt-2.7b" and not (name.startswith("fc1.") or name.startswith("fc2.")):
                continue
            if not include_bias and not name.endswith("weight"):
                continue
            named_params.append((name, param))
        param_count = int(sum(param.numel() for _, param in named_params))
        modules.append(
            {
                "layer": layer,
                "layer_name": f"L{layer}",
                "module_path": module_path,
                "param_names": [name for name, _ in named_params],
                "params": [param for _, param in named_params],
                "param_count": param_count,
            }
        )
    return modules


def set_params_trainable(params: Sequence[Any], trainable: bool) -> None:
    for param in params:
        param.requires_grad_(trainable)


def set_all_mlp_params_trainable(modules: Sequence[Dict[str, Any]], trainable: bool) -> None:
    for item in modules:
        set_params_trainable(item["params"], trainable)


def compute_target_loss(vllm: Any, prompt: str, image: Any, target: str) -> Any:
    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [prompt],
        [image],
        [target],
    )
    if label_masks.sum().item() <= 0:
        raise ValueError("empty target mask")
    output = vllm.get_llm_outpt(llm_inpt, vt_range)
    logits = get_logits(output)
    loss = vllm.label_loss(logits, label_ids, label_masks, average=True)
    if not torch.isfinite(loss):
        raise FloatingPointError("non-finite target loss")
    return loss


def compute_grads_for_target(vllm: Any, prompt: str, image: Any, target: str, params: Sequence[Any]) -> Tuple[float, List[Any]]:
    vllm.model.zero_grad(set_to_none=True)
    loss = compute_target_loss(vllm, prompt, image, target)
    grads = torch.autograd.grad(
        loss,
        list(params),
        retain_graph=False,
        create_graph=False,
        allow_unused=True,
    )
    detached = []
    for grad in grads:
        detached.append(None if grad is None else grad.detach().float().cpu().contiguous())
    loss_value = float(loss.detach().float().cpu().item())
    del loss, grads
    vllm.model.zero_grad(set_to_none=True)
    return loss_value, detached


def compute_all_layer_grads_for_target(
    vllm: Any,
    modules: Sequence[Dict[str, Any]],
    prompt: str,
    image: Any,
    target: str,
) -> Tuple[float, Dict[int, List[Any]]]:
    vllm.model.zero_grad(set_to_none=True)
    loss = compute_target_loss(vllm, prompt, image, target)
    loss.backward()
    out: Dict[int, List[Any]] = {}
    for item in modules:
        grads = []
        for param in item["params"]:
            grad = param.grad
            grads.append(None if grad is None else grad.detach().float().cpu().contiguous())
        out[int(item["layer"])] = grads
    loss_value = float(loss.detach().float().cpu().item())
    del loss
    vllm.model.zero_grad(set_to_none=True)
    return loss_value, out


def grad_pair_stats(old_grads: Sequence[Any], new_grads: Sequence[Any]) -> Dict[str, float]:
    dot = 0.0
    old_sq = 0.0
    new_sq = 0.0
    used = 0
    for old_grad, new_grad in zip(old_grads, new_grads):
        if old_grad is None or new_grad is None:
            raise RuntimeError("unused_or_unreachable_mlp_parameters")
        dot += float(torch.sum(old_grad * new_grad).item())
        old_sq += float(torch.sum(old_grad * old_grad).item())
        new_sq += float(torch.sum(new_grad * new_grad).item())
        used += int(old_grad.numel())
    old_norm = math.sqrt(max(old_sq, 0.0))
    new_norm = math.sqrt(max(new_sq, 0.0))
    if old_norm <= EPS:
        raise RuntimeError("all_zero_old_gradient")
    if new_norm <= EPS:
        raise RuntimeError("all_zero_new_gradient")
    if not math.isfinite(dot):
        raise FloatingPointError("nonfinite_lga_dot")
    return {
        "dot": dot,
        "old_norm": old_norm,
        "new_norm": new_norm,
        "cos": dot / (old_norm * new_norm + EPS),
        "grad_param_count": float(used),
    }


def init_accum(layer: int) -> Dict[str, Any]:
    return {
        "layer": layer,
        "layer_name": f"L{layer}",
        "score_sum": 0.0,
        "old_norm_sum": 0.0,
        "new_norm_sum": 0.0,
        "cos_sum": 0.0,
        "valid_sample_count": 0,
        "failure_count": 0,
        "failure_reasons": {},
    }


def add_failure(accum: Dict[str, Any], reason: str) -> None:
    accum["failure_count"] += 1
    accum["failure_reasons"][reason] = accum["failure_reasons"].get(reason, 0) + 1


def rank_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    valid = [row for row in rows if row["status"] == "ok" and math.isfinite(float(row["score"]))]
    valid.sort(key=lambda row: (-float(row["score"]), int(row["layer"])))
    for rank, row in enumerate(valid, 1):
        row["rank"] = rank
    invalid = [row for row in rows if row["status"] != "ok" or not math.isfinite(float(row["score"]))]
    for row in invalid:
        row["rank"] = ""
    return valid + invalid


def write_csv_atomic(path: Path, rows: List[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def build_candidate_rows(dataset_name: str, model_name: str, ranked: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    clean = [row for row in ranked if row["status"] == "ok"]
    top3 = [row["layer_name"] for row in clean[:3]]
    top5 = [row["layer_name"] for row in clean[:5]]
    candidate_rows: List[Dict[str, Any]] = []
    for top_k, top_layers in [(3, top3), (5, top5)]:
        for rank, layer_name in enumerate(top_layers, 1):
            layer_row = next(row for row in clean if row["layer_name"] == layer_name)
            candidate_rows.append(
                {
                    "dataset": DATASET_DISPLAY[dataset_name],
                    "model": MODEL_DISPLAY[model_name],
                    "method": METHOD_NAME,
                    "variant": "direct",
                    "top_k": top_k,
                    "rank": rank,
                    "layer": layer_name,
                    "score": layer_row["score"],
                    "raw_rank": layer_row["rank"],
                    "filtered_rank": "",
                    "raw_candidate_layers": ",".join(top_layers),
                    "clean_candidate_layers": ",".join(top_layers),
                    "selection_source": SCORE_SOURCE,
                    "candidate_conversion": "direct",
                    "status": "done" if top_layers else "unavailable",
                    "failure_reason": "" if top_layers else "no_valid_lga_layer",
                }
            )
    return top3, top5, candidate_rows


def run_one(args: Any) -> None:
    model_name = normalize_model_name(args.model_name)
    dataset_name = args.dataset_name
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.json"
    if args.resume and summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as f:
            summary = json.load(f)
        if summary.get("status") == "done":
            print(f"[SKIP] Existing done summary: {summary_path}")
            return

    ds = DEFAULT_DATASETS[dataset_name]
    data_path = args.data_path or ds["data_path"]
    img_root = args.img_root or ds["img_root"]
    data = load_edit_data(dataset_name, data_path, img_root, args.data_n)

    cfg = PTrackConfig.from_yaml(str(resolve_path(CONFIG_PATHS[model_name])))
    torch.set_grad_enabled(True)
    vllm = load_vllm_for_edit(model_name, args.device)
    vllm.model.eval()
    if hasattr(vllm.model, "config"):
        try:
            vllm.model.config.use_cache = False
        except Exception:
            pass

    modules = prepare_mlp_weight_modules(vllm, cfg, model_name, include_bias=args.include_bias)
    missing_layers = [item["layer"] for item in modules if not item["params"]]
    set_all_mlp_params_trainable(modules, True)
    model_pred_cache = ensure_model_pred_cache(
        vllm,
        model_name,
        data,
        out_dir / "model_pred_cache.jsonl",
        args.max_new_tokens,
    )

    accum = {item["layer"]: init_accum(item["layer"]) for item in modules}
    skipped_samples: List[Dict[str, Any]] = []
    layer_failures: List[Dict[str, Any]] = []
    ok_samples = 0
    started = time.time()

    progress_path = out_dir / "progress.jsonl"
    with progress_path.open("a", encoding="utf-8") as pf:
        for sample_i, row in enumerate(data):
            sample_id = get_sample_id(row, sample_i)
            req = row["request"]
            prompt = req["prompt"]
            image = req["image"]
            target_new = str(req["target_new"] or "").strip()
            cache_row = model_pred_cache.get(sample_id, {})
            target_old = str(cache_row.get("answer") or "").strip()

            sample_skip_reason = ""
            if not target_new:
                sample_skip_reason = "invalid_alt"
            elif not model_pred_cache_row_ok(cache_row):
                sample_skip_reason = str(cache_row.get("status") or "invalid_model_pred")
            elif not args.include_old_new_same and normalize_answer(target_old) == normalize_answer(target_new):
                sample_skip_reason = "old_new_same_after_norm"

            if sample_skip_reason:
                skipped_samples.append(
                    {
                        "dataset": dataset_name,
                        "model": model_name,
                        "sample_i": sample_i,
                        "sample_id": sample_id,
                        "skip_reason": sample_skip_reason,
                        "old_text": target_old,
                        "new_text": target_new,
                    }
                )
                pf.write(json.dumps({"sample_i": sample_i, "sample_id": sample_id, "status": "skipped", "reason": sample_skip_reason}, ensure_ascii=False) + "\n")
                pf.flush()
                continue

            sample_ok_any_layer = False
            try:
                old_loss, old_grads_by_layer = compute_all_layer_grads_for_target(
                    vllm, modules, prompt, image, target_old
                )
                new_loss, new_grads_by_layer = compute_all_layer_grads_for_target(
                    vllm, modules, prompt, image, target_new
                )
            except Exception as exc:
                reason = str(exc) or exc.__class__.__name__
                skipped_samples.append(
                    {
                        "dataset": dataset_name,
                        "model": model_name,
                        "sample_i": sample_i,
                        "sample_id": sample_id,
                        "skip_reason": reason,
                        "old_text": target_old,
                        "new_text": target_new,
                    }
                )
                pf.write(json.dumps({"sample_i": sample_i, "sample_id": sample_id, "status": "skipped", "reason": reason}, ensure_ascii=False) + "\n")
                pf.flush()
                if torch.cuda.is_available() and args.empty_cache_each_layer:
                    torch.cuda.empty_cache()
                gc.collect()
                continue

            for item in modules:
                layer = item["layer"]
                if not item["params"]:
                    add_failure(accum[layer], "missing_mlp_ffn_weight_params")
                    continue
                try:
                    stats = grad_pair_stats(old_grads_by_layer[layer], new_grads_by_layer[layer])
                    accum[layer]["score_sum"] += stats["dot"]
                    accum[layer]["old_norm_sum"] += stats["old_norm"]
                    accum[layer]["new_norm_sum"] += stats["new_norm"]
                    accum[layer]["cos_sum"] += stats["cos"]
                    accum[layer]["valid_sample_count"] += 1
                    sample_ok_any_layer = True
                except Exception as exc:
                    reason = str(exc) or exc.__class__.__name__
                    add_failure(accum[layer], reason)
                    if len(layer_failures) < args.max_logged_failures:
                        layer_failures.append(
                            {
                                "dataset": dataset_name,
                                "model": model_name,
                                "sample_i": sample_i,
                                "sample_id": sample_id,
                                "layer": layer,
                                "failure_reason": reason,
                                "traceback": traceback.format_exc(limit=3),
                            }
                        )
            del old_grads_by_layer, new_grads_by_layer
            vllm.model.zero_grad(set_to_none=True)
            if torch.cuda.is_available() and args.empty_cache_each_layer:
                torch.cuda.empty_cache()
            gc.collect()
            if sample_ok_any_layer:
                ok_samples += 1
            pf.write(json.dumps({"sample_i": sample_i, "sample_id": sample_id, "status": "processed", "ok_any_layer": sample_ok_any_layer}, ensure_ascii=False) + "\n")
            pf.flush()

    rows: List[Dict[str, Any]] = []
    for item in modules:
        layer = item["layer"]
        a = accum[layer]
        n = int(a["valid_sample_count"])
        status = "ok" if n > 0 and item["params"] else "unavailable"
        failure_reason = "" if status == "ok" else ("missing_mlp_ffn_weight_params" if not item["params"] else "no_valid_lga_sample")
        rows.append(
            {
                "dataset": DATASET_DISPLAY[dataset_name],
                "model": MODEL_DISPLAY[model_name],
                "method": METHOD_NAME,
                "variant": "direct",
                "new_field": "alt",
                "old_field": "model_pred",
                "layer_space": "text_decoder",
                "score_space": "param_mlp_ffn",
                "target_parameter_scope": "mlp_ffn_weight_only" if not args.include_bias else "mlp_ffn_weight_and_bias",
                "include_bias": bool(args.include_bias),
                "layer": layer,
                "layer_name": f"L{layer}",
                "module_path": item["module_path"],
                "param_names": ";".join(item["param_names"]),
                "param_count": item["param_count"],
                "score": a["score_sum"] / n if n else float("nan"),
                "score_raw": a["score_sum"] / n if n else float("nan"),
                "score_lga_cos": a["cos_sum"] / n if n else float("nan"),
                "score_old_grad_norm": a["old_norm_sum"] / n if n else float("nan"),
                "score_new_grad_norm": a["new_norm_sum"] / n if n else float("nan"),
                "rank": "",
                "localization_sample_count": len(data),
                "processed_sample_count": ok_samples,
                "valid_sample_count": n,
                "skipped_sample_count": len(skipped_samples),
                "failure_count": a["failure_count"],
                "failure_reasons": json.dumps(a["failure_reasons"], ensure_ascii=False, sort_keys=True),
                "rank_metric": SCORE_SOURCE,
                "dot_normalization": "none",
                "candidate_conversion": "direct",
                "status": status,
                "failure_reason": failure_reason,
            }
        )
    ranked = rank_rows(rows)
    top3, top5, candidate_rows = build_candidate_rows(dataset_name, model_name, ranked)

    total_samples = len(data)
    valid_layers = sum(1 for row in ranked if row["status"] == "ok")
    if valid_layers < 3:
        status = "unavailable"
        failure_reason = "valid_layer_count_lt_top3"
    elif ok_samples < args.min_valid_samples or (total_samples and ok_samples / total_samples < args.min_valid_ratio):
        status = "low_valid_coverage"
        failure_reason = f"valid_samples={ok_samples}/{total_samples}"
    elif valid_layers / max(len(modules), 1) < args.min_valid_layer_ratio:
        status = "unreliable"
        failure_reason = f"valid_layers={valid_layers}/{len(modules)}"
    else:
        status = "done"
        failure_reason = ""

    layer_fields = list(ranked[0].keys()) if ranked else []
    write_csv_atomic(out_dir / "layer_scores.csv", ranked, layer_fields)
    candidate_fields = list(candidate_rows[0].keys()) if candidate_rows else [
        "dataset",
        "model",
        "method",
        "variant",
        "top_k",
        "rank",
        "layer",
        "score",
        "status",
        "failure_reason",
    ]
    write_csv_atomic(out_dir / "candidate_layers_topk.csv", candidate_rows, candidate_fields)

    with (out_dir / "skipped_samples.jsonl").open("w", encoding="utf-8") as f:
        for item in skipped_samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    with (out_dir / "layer_failure_log.jsonl").open("w", encoding="utf-8") as f:
        for item in layer_failures:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    sanity_failure = ""
    finite_scores = [float(row["score"]) for row in ranked if row["status"] == "ok" and math.isfinite(float(row["score"]))]
    if finite_scores and len(set(finite_scores)) == 1:
        sanity_failure = "all_layer_scores_identical"
    elif finite_scores and all(abs(x) <= EPS for x in finite_scores):
        sanity_failure = "all_layer_scores_zero"
    sanity = {
        "sanity_status": "failed" if sanity_failure else "ok",
        "sanity_failure_reason": sanity_failure,
        "finite_score_count": len(finite_scores),
        "valid_layers": valid_layers,
        "missing_layers": missing_layers,
    }
    with (out_dir / "sanity_check.json").open("w", encoding="utf-8") as f:
        json.dump(sanity, f, ensure_ascii=False, indent=2)
    if sanity_failure and status == "done":
        status = "unreliable"
        failure_reason = sanity_failure

    summary = {
        "dataset_key": dataset_name,
        "dataset": DATASET_DISPLAY[dataset_name],
        "model_key": model_name,
        "model": MODEL_DISPLAY[model_name],
        "method": METHOD_NAME,
        "score_source": SCORE_SOURCE,
        "new_field": "alt",
        "old_field": "model_pred",
        "target_parameter_scope": "mlp_ffn_weight_only" if not args.include_bias else "mlp_ffn_weight_and_bias",
        "num_decoder_layers": int(cfg.num_layers),
        "total_samples": total_samples,
        "processed_samples": ok_samples,
        "skipped_samples": len(skipped_samples),
        "valid_layers": valid_layers,
        "top3_layers": top3,
        "top5_layers": top5,
        "duration_sec": time.time() - started,
        "status": status,
        "failure_reason": failure_reason,
        "sanity": sanity,
        "scores_csv": str(out_dir / "layer_scores.csv"),
        "candidates_csv": str(out_dir / "candidate_layers_topk.csv"),
    }
    tmp_summary = summary_path.with_suffix(".json.tmp")
    with tmp_summary.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    tmp_summary.replace(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def collect(args: Any) -> None:
    run_root = Path(args.run_root).resolve()
    rows = []
    for dataset_name in DATASET_ORDER:
        for model_name in MODEL_ORDER:
            summary_path = run_root / dataset_name / model_name / "summary.json"
            if summary_path.exists():
                with summary_path.open("r", encoding="utf-8") as f:
                    summary = json.load(f)
                status = summary.get("status", "unknown")
                if summary.get("failure_reason"):
                    status = f"{status}; {summary.get('failure_reason')}"
                status = f"{status}; n={summary.get('processed_samples')}/{summary.get('total_samples')}"
                top3 = ",".join(summary.get("top3_layers", []))
                top5 = ",".join(summary.get("top5_layers", []))
            else:
                status = "missing"
                top3 = "-"
                top5 = "-"
            rows.append(
                {
                    "Dataset": DATASET_DISPLAY[dataset_name],
                    "Model": MODEL_DISPLAY[model_name],
                    "Method": METHOD_NAME,
                    "Score source": SCORE_SOURCE,
                    "Top-3": top3,
                    "Top-5": top5,
                    "Status": status,
                }
            )

    csv_path = run_root / "lga_param_direct_altmodelpred_candidates_summary.csv"
    write_csv_atomic(csv_path, rows, list(rows[0].keys()))
    md_path = run_root / "lga_param_direct_altmodelpred_candidates_summary.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for row in rows:
            f.write(
                f"| {row['Dataset']} | {row['Model']} | {row['Method']} | {row['Score source']} "
                f"| {row['Top-3']} | {row['Top-5']} | {row['Status']} |\n"
            )
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute LGA-Param-Direct-AltModelPred layer candidates.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-one")
    run.add_argument("--model-name", required=True)
    run.add_argument("--dataset-name", required=True, choices=DATASET_ORDER)
    run.add_argument("--out-dir", required=True)
    run.add_argument("--device", default="cuda:0")
    run.add_argument("--data-path", default=None)
    run.add_argument("--img-root", default=None)
    run.add_argument("--data-n", type=int, default=None)
    run.add_argument("--max-new-tokens", type=int, default=32)
    run.add_argument("--include-bias", action="store_true")
    run.add_argument("--include-old-new-same", action="store_true")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--empty-cache-each-layer", action="store_true", default=True)
    run.add_argument("--min-valid-samples", type=int, default=50)
    run.add_argument("--min-valid-ratio", type=float, default=0.20)
    run.add_argument("--min-valid-layer-ratio", type=float, default=0.80)
    run.add_argument("--max-logged-failures", type=int, default=200)
    run.set_defaults(func=run_one)

    col = sub.add_parser("collect")
    col.add_argument("--run-root", required=True)
    col.set_defaults(func=collect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
