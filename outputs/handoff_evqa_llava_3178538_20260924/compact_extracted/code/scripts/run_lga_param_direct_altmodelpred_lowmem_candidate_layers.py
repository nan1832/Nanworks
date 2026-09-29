#!/usr/bin/env python3
import argparse
import gc
import json
import math
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Sequence

import torch

from run_lga_param_direct_altmodelpred_candidate_layers import (
    CONFIG_PATHS,
    DATASET_DISPLAY,
    DATASET_ORDER,
    DEFAULT_DATASETS,
    EPS,
    METHOD_NAME,
    MODEL_DISPLAY,
    MODEL_ORDER,
    SCORE_SOURCE,
    add_failure,
    build_candidate_rows,
    compute_all_layer_grads_for_target,
    grad_pair_stats,
    init_accum,
    load_edit_data,
    load_vllm_for_edit,
    model_pred_cache_row_ok,
    normalize_answer,
    normalize_model_name,
    prepare_mlp_weight_modules,
    rank_rows,
    resolve_path,
    set_params_trainable,
    write_csv_atomic,
    ensure_model_pred_cache,
    get_sample_id,
)
from p_track.p_track import PTrackConfig


def chunked(seq: Sequence[Dict[str, Any]], size: int) -> Sequence[Sequence[Dict[str, Any]]]:
    for start in range(0, len(seq), size):
        yield seq[start : start + size]


def set_module_batch_trainable(modules: Sequence[Dict[str, Any]], trainable: bool) -> None:
    for item in modules:
        set_params_trainable(item["params"], trainable)


def run_one_lowmem(args: Any) -> None:
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
    # Keep all MLP params frozen by default; only a small layer batch is enabled.
    for item in modules:
        set_params_trainable(item["params"], False)

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

    layer_batch_size = max(int(args.layer_batch_size), 1)
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
            sample_skipped_whole = False
            for batch in chunked(modules, layer_batch_size):
                batch = [item for item in batch if item["params"]]
                if not batch:
                    continue
                try:
                    set_module_batch_trainable(batch, True)
                    _, old_grads_by_layer = compute_all_layer_grads_for_target(
                        vllm, batch, prompt, image, target_old
                    )
                    _, new_grads_by_layer = compute_all_layer_grads_for_target(
                        vllm, batch, prompt, image, target_new
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
                    sample_skipped_whole = True
                    try:
                        del old_grads_by_layer, new_grads_by_layer
                    except Exception:
                        pass
                    vllm.model.zero_grad(set_to_none=True)
                    set_module_batch_trainable(batch, False)
                    if torch.cuda.is_available() and args.empty_cache_each_batch:
                        torch.cuda.empty_cache()
                    gc.collect()
                    break

                for item in batch:
                    layer = int(item["layer"])
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
                set_module_batch_trainable(batch, False)
                if torch.cuda.is_available() and args.empty_cache_each_batch:
                    torch.cuda.empty_cache()
                gc.collect()

            if sample_skipped_whole:
                continue
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

    write_csv_atomic(out_dir / "layer_scores.csv", ranked, list(ranked[0].keys()) if ranked else [])
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

    finite_scores = [float(row["score"]) for row in ranked if row["status"] == "ok" and math.isfinite(float(row["score"]))]
    sanity_failure = ""
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
        "execution_mode": "layerwise_lowmem",
        "layer_batch_size": layer_batch_size,
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
        "execution_mode": "layerwise_lowmem",
        "layer_batch_size": layer_batch_size,
    }
    tmp_summary = summary_path.with_suffix(".json.tmp")
    with tmp_summary.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    tmp_summary.replace(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Low-memory LGA-Param-Direct-AltModelPred runner.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--dataset-name", required=True, choices=DATASET_ORDER)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--data-path", default=None)
    parser.add_argument("--img-root", default=None)
    parser.add_argument("--data-n", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--include-bias", action="store_true")
    parser.add_argument("--include-old-new-same", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--empty-cache-each-batch", action="store_true", default=True)
    parser.add_argument("--layer-batch-size", type=int, default=4)
    parser.add_argument("--min-valid-samples", type=int, default=50)
    parser.add_argument("--min-valid-ratio", type=float, default=0.20)
    parser.add_argument("--min-valid-layer-ratio", type=float, default=0.80)
    parser.add_argument("--max-logged-failures", type=int, default=200)
    args = parser.parse_args()
    if args.layer_batch_size < 1:
        raise ValueError("--layer-batch-size must be >= 1")
    run_one_lowmem(args)


if __name__ == "__main__":
    main()
