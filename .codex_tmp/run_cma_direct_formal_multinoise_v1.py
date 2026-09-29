#!/usr/bin/env python3
"""Formal CMA-Direct multi-noise/multi-seed runner.

This is intentionally a new implementation entry point.  It imports only the
model/data/scoring primitives from the historical runner and never overwrites
historical CMA outputs.  Progress is journaled at corruption-pair and
pair-by-layer grain; canonical de-duplicated CSV/JSON summaries are rebuilt
from those journals after every run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import torch
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import run_cma_direct_candidate_layers as legacy  # noqa: E402


SCHEMA_VERSION = "cma-formal-multinoise-v1"


def json_dump_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(f"invalid JSONL {path}:{n}: {exc}") from exc
    return out


def latest_by(rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
    out: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in rows:
        out[tuple(row.get(x) for x in fields)] = row
    return out


def finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def float_or_none(x: Any) -> Any:
    return float(x) if finite(x) else None


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_manifest(path: Path) -> Tuple[List[str], Dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        ids = [str(x) for x in obj]
        meta = {"sample_ids": ids}
    elif isinstance(obj, dict) and isinstance(obj.get("sample_ids"), list):
        ids = [str(x) for x in obj["sample_ids"]]
        meta = dict(obj)
    else:
        raise ValueError("manifest must be a JSON list or contain sample_ids")
    if len(ids) != len(set(ids)):
        dup = [x for x, n in Counter(ids).items() if n > 1]
        raise ValueError(f"duplicate sample IDs in manifest: {dup[:20]}")
    return ids, meta


def load_selected_mmke(data_path: Path, image_root: Path, sample_ids: Sequence[str]) -> List[Dict[str, Any]]:
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    wanted = set(sample_ids)
    rows: Dict[str, Dict[str, Any]] = {}
    duplicates: List[str] = []
    for i, item in enumerate(raw):
        sid = str(item.get("sample_id", f"mmke_{i}"))
        if sid not in wanted:
            continue
        if sid in rows:
            duplicates.append(sid)
            continue
        image_name = item.get("image") or item.get("image_path")
        if not image_name:
            raise ValueError(f"missing image for {sid}")
        image_path = Path(image_name)
        if not image_path.is_absolute():
            image_path = image_root / image_path
        if not image_path.exists():
            raise FileNotFoundError(f"missing image for {sid}: {image_path}")
        alt = str(item.get("alt", "")).strip()
        if not alt:
            raise ValueError(f"empty alt for {sid}")
        rows[sid] = {
            "sample_id": sid,
            # Match the established MMKE localization/training prompt exactly.
            "prompt": f"{item.get('src', item.get('prompt', ''))} The answer is:",
            "target": alt,
            "image_path": str(image_path.resolve()),
            "image": Image.open(image_path).convert("RGB"),
        }
    if duplicates:
        raise ValueError(f"duplicate sample IDs in dataset: {duplicates[:20]}")
    missing = [sid for sid in sample_ids if sid not in rows]
    if missing:
        raise ValueError(f"manifest IDs missing from dataset: {missing[:20]}")
    return [rows[sid] for sid in sample_ids]


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def rank_layers(layer_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(r: Dict[str, Any]) -> Tuple[Any, ...]:
        cr = r.get("cr_mean")
        kcr = r.get("kcr_mean")
        return (
            -float(cr) if finite(cr) else float("inf"),
            -float(kcr) if finite(kcr) else float("inf"),
            -int(r.get("valid_pair_count", 0)),
            int(r["layer"]),
        )
    ranked = sorted(layer_rows, key=key)
    for i, row in enumerate(ranked, 1):
        row["rank"] = i
    return ranked


def finalize(out_dir: Path, expected_layers: Sequence[int], formal_groups: Sequence[Tuple[float, int]]) -> Dict[str, Any]:
    corr_keys = ("sample_id", "alpha", "seed")
    restore_keys = ("sample_id", "alpha", "seed", "layer")
    pair_keys = ("sample_id", "alpha", "seed")
    corr = latest_by(read_jsonl(out_dir / "journals" / "corruption_pairs.jsonl"), corr_keys)
    restore = latest_by(read_jsonl(out_dir / "journals" / "restore_long.jsonl"), restore_keys)
    pair_status = latest_by(read_jsonl(out_dir / "journals" / "pair_status.jsonl"), pair_keys)

    formal_set = {(float(a), int(s)) for a, s in formal_groups}
    corr_rows = [r for k, r in sorted(corr.items()) if (float(k[1]), int(k[2])) in formal_set]
    restore_rows = [r for k, r in sorted(restore.items()) if (float(k[1]), int(k[2])) in formal_set]
    pair_rows = [r for k, r in sorted(pair_status.items()) if (float(k[1]), int(k[2])) in formal_set]
    write_csv(out_dir / "canonical" / "cma_corruption_pairs.csv", corr_rows)
    write_csv(out_dir / "canonical" / "cma_restore_long.csv", restore_rows)
    write_csv(out_dir / "canonical" / "cma_pair_status.csv", pair_rows)

    corr_by_key = {tuple(r[x] for x in corr_keys): r for r in corr_rows}
    restore_by_key = {tuple(r[x] for x in restore_keys): r for r in restore_rows}
    manifest = json.loads((out_dir / "sample_manifest.json").read_text(encoding="utf-8"))
    sample_ids = [str(x) for x in manifest["sample_ids"]]
    expected_pairs = [(sid, float(a), int(seed)) for sid in sample_ids for a, seed in formal_groups]

    valid_pairs: List[Tuple[str, float, int]] = []
    low_gap = nonfinite_score = missing_restore = runtime_error = 0
    for pkey in expected_pairs:
        c = corr_by_key.get(pkey)
        if c is None:
            runtime_error += 1
            continue
        if not finite(c.get("s_clean")) or not finite(c.get("s_corrupt")):
            nonfinite_score += 1
            continue
        if not bool(c.get("gap_valid")):
            low_gap += 1
            continue
        layer_records = [restore_by_key.get((*pkey, int(layer))) for layer in expected_layers]
        if any(x is None for x in layer_records):
            missing_restore += 1
            continue
        if any(x.get("status") != "ok" for x in layer_records):
            runtime_error += 1
            continue
        if any(not finite(x.get("s_restore")) or not finite(x.get("cr")) for x in layer_records):
            nonfinite_score += 1
            continue
        valid_pairs.append(pkey)

    valid_pair_set = set(valid_pairs)
    valid_samples = sorted({x[0] for x in valid_pairs})
    layer_rows: List[Dict[str, Any]] = []
    for layer in expected_layers:
        vals = [restore_by_key[(*p, int(layer))] for p in valid_pairs]
        crs = [float(x["cr"]) for x in vals if finite(x.get("cr"))]
        kcrs = [float(x["kcr"]) for x in vals if finite(x.get("kcr"))]
        sample_crs: Dict[str, List[float]] = defaultdict(list)
        for x in vals:
            if finite(x.get("cr")):
                sample_crs[str(x["sample_id"])].append(float(x["cr"]))
        sample_means = [float(np.mean(v)) for v in sample_crs.values() if v]
        layer_rows.append({
            "layer": int(layer),
            "valid_pair_count": len(crs),
            "valid_unique_sample_count": len(sample_crs),
            "cr_mean": float_or_none(np.mean(crs) if crs else None),
            "cr_std": float_or_none(np.std(crs) if crs else None),
            "kcr_mean": float_or_none(np.mean(kcrs) if kcrs else None),
            "sample_balanced_cr_mean": float_or_none(np.mean(sample_means) if sample_means else None),
        })
    ranked = rank_layers(layer_rows)
    write_csv(out_dir / "canonical" / "cma_layer_scores.csv", ranked)

    group_rankings: List[Dict[str, Any]] = []
    for alpha, seed in formal_groups:
        gpairs = [p for p in valid_pairs if p[1] == float(alpha) and p[2] == int(seed)]
        grows = []
        for layer in expected_layers:
            vals = [restore_by_key[(*p, int(layer))] for p in gpairs]
            crs = [float(x["cr"]) for x in vals if finite(x.get("cr"))]
            grows.append({"layer": int(layer), "cr_mean": float_or_none(np.mean(crs) if crs else None),
                          "kcr_mean": None, "valid_pair_count": len(crs)})
        granked = rank_layers(grows)
        group_rankings.append({
            "alpha": alpha,
            "seed": seed,
            "valid_pairs": len(gpairs),
            "top3": [x["layer"] for x in granked[:3] if finite(x.get("cr_mean"))],
            "top5": [x["layer"] for x in granked[:5] if finite(x.get("cr_mean"))],
            "ranking": [x["layer"] for x in granked if finite(x.get("cr_mean"))],
        })

    top3 = [x["layer"] for x in ranked[:3] if finite(x.get("cr_mean"))]
    top5 = [x["layer"] for x in ranked[:5] if finite(x.get("cr_mean"))]
    n = len(sample_ids)
    minimum_required = max(30, math.ceil(0.20 * n))
    eligible = len(valid_samples) >= minimum_required
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_unique_samples": n,
        "formal_parameter_groups": [{"alpha": a, "seed": s} for a, s in formal_groups],
        "expected_parameter_pairs": len(expected_pairs),
        "corruption_pairs_recorded": len(corr_rows),
        "finite_corruption_pairs": sum(finite(r.get("s_clean")) and finite(r.get("s_corrupt")) for r in corr_rows),
        "common_restore_pairs_all_layers": len(valid_pairs),
        "valid_unique_samples": len(valid_samples),
        "valid_unique_sample_ratio": len(valid_samples) / n if n else 0.0,
        "low_corruption_gap_pair_count": low_gap,
        "nonfinite_score_pair_count": nonfinite_score,
        "missing_restore_pair_count": missing_restore,
        "runtime_error_or_missing_pair_count": runtime_error,
        "minimum_valid_unique_samples": minimum_required,
        "eligible_for_formal_ranking": eligible,
        "coverage_tier": "formal" if eligible else ("exploratory_10_to_29" if len(valid_samples) >= 10 else "descriptive_below_10"),
        "ranking_population": "common_restore_pairs_all_layers",
        "primary_aggregation": "pair_weighted_mean_CR",
        "tie_break": ["CR_mean_desc", "KCR_mean_desc", "valid_pair_count_desc", "layer_asc"],
        "top3": top3,
        "top5": top5,
        "valid_sample_id_hash": sha256_json(valid_samples),
    }
    json_dump_atomic(out_dir / "canonical" / "summary.json", summary)
    json_dump_atomic(out_dir / "canonical" / "stability_by_alpha_seed.json", {"groups": group_rankings})
    json_dump_atomic(out_dir / "canonical" / "valid_pair_keys.json", [list(x) for x in sorted(valid_pair_set)])
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", required=True)
    p.add_argument("--data-path", required=True)
    p.add_argument("--image-root", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--noise-scales", default="0.5,1.0,2.0")
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--delta-logprob", type=float, default=0.05)
    p.add_argument("--eps", type=float, default=1e-8)
    p.add_argument("--epsilon-sigma", type=float, default=1e-6)
    p.add_argument("--run-mode", choices=["smoke", "calibration", "formal"], required=True)
    p.add_argument("--include-historical-control", action="store_true")
    p.add_argument("--resume", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(project_root)

    scales = [float(x) for x in args.noise_scales.split(",") if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    formal_groups = [(a, s) for a in scales for s in seeds]
    run_groups: List[Tuple[float, int, bool]] = [(a, s, True) for a, s in formal_groups]
    if args.include_historical_control and (1.0, 2026) not in formal_groups:
        run_groups.append((1.0, 2026, False))

    sample_ids, manifest_meta = load_manifest(Path(args.manifest))
    manifest_obj = {
        **manifest_meta,
        "sample_ids": sample_ids,
        "sample_count": len(sample_ids),
        "sample_id_hash": sha256_json(sample_ids),
    }
    manifest_path = out_dir / "sample_manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("sample_id_hash") != manifest_obj["sample_id_hash"]:
            raise RuntimeError("refusing to resume with a different sample manifest")
    else:
        json_dump_atomic(manifest_path, manifest_obj)

    frozen = {
        "schema_version": SCHEMA_VERSION,
        "run_mode": args.run_mode,
        "project_root": str(project_root),
        "data_path": str(Path(args.data_path).resolve()),
        "image_root": str(Path(args.image_root).resolve()),
        "config": str(Path(args.config).resolve()),
        "device": args.device,
        "noise_scales": scales,
        "semantic_seeds": seeds,
        "historical_control_group": args.include_historical_control,
        "delta_logprob": args.delta_logprob,
        "eps": args.eps,
        "epsilon_sigma": args.epsilon_sigma,
        "target": "alt_full_sequence_teacher_forcing",
        "noise": "alpha_times_visual_embedding_std",
        "formal_pair_seed_key": ["dataset", "model", "sample_id", "alpha", "seed"],
        "historical_control_seed_key": ["dataset", "model", "sample_id", "alpha", "seed", "visual_start", "visual_end"],
        "ranking_population": "common_restore_pairs_all_layers",
        "primary_aggregation": "pair_weighted_mean_CR",
        "runtime_python": sys.executable,
        "python_version": sys.version,
        "torch_version": getattr(torch, "__version__", "unknown"),
    }
    try:
        import transformers
        frozen["transformers_version"] = transformers.__version__
    except Exception:
        frozen["transformers_version"] = "unavailable"
    frozen["frozen_config_hash"] = sha256_json(frozen)
    frozen_path = out_dir / "frozen_config.json"
    if frozen_path.exists():
        existing = json.loads(frozen_path.read_text(encoding="utf-8"))
        if existing.get("frozen_config_hash") != frozen["frozen_config_hash"]:
            raise RuntimeError("refusing to resume with a different frozen config")
    else:
        json_dump_atomic(frozen_path, frozen)

    data = load_selected_mmke(Path(args.data_path), Path(args.image_root), sample_ids)
    from p_track.p_track import PTrackConfig
    from utils import load_vllm_for_edit
    from utils.nethook import TraceDict

    cfg = PTrackConfig.from_yaml(args.config)
    model_name = "qwen2.5-vl-3b"
    if model_name != "qwen2.5-vl-3b":
        raise RuntimeError(f"this formal run is frozen to Qwen2.5-VL-3B, got {model_name}")
    expected_layers = list(range(int(cfg.num_layers)))
    if expected_layers != list(range(36)):
        raise RuntimeError(f"expected 36 Qwen layers, got {len(expected_layers)}")
    layer_paths = [cfg.layer_module_tmp.format(i) for i in expected_layers]

    # Exactly one model load.  The historical runner accidentally loaded twice.
    vllm = load_vllm_for_edit(model_name, args.device)
    model = vllm.model
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)

    corr_path = out_dir / "journals" / "corruption_pairs.jsonl"
    restore_path = out_dir / "journals" / "restore_long.jsonl"
    status_path = out_dir / "journals" / "pair_status.jsonl"
    existing_status = latest_by(read_jsonl(status_path), ("sample_id", "alpha", "seed")) if args.resume else {}
    existing_restore = latest_by(read_jsonl(restore_path), ("sample_id", "alpha", "seed", "layer")) if args.resume else {}

    for sample_index, item in enumerate(data):
        sid = str(item["sample_id"])
        prompt = item["prompt"]
        target = item["target"]
        image = item["image"]
        unfinished = []
        for alpha, seed, formal in run_groups:
            st = existing_status.get((sid, alpha, seed))
            if st and st.get("status") in {"low_corruption_gap", "valid_restore_pair"}:
                continue
            unfinished.append((alpha, seed, formal))
        if not unfinished:
            print(f"[resume] {sid}: all parameter pairs complete", flush=True)
            continue

        try:
            (llm_input, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
                [prompt], [image], [target]
            )
            with torch.inference_mode(), TraceDict(
                model, layer_paths, retain_output=True, with_kwargs=True, clone=True, detach=True
            ) as traces:
                clean_out = vllm.get_llm_outpt(llm_input, vt_range)
                clean_logits = legacy.get_logits(clean_out).detach()
            embeds = legacy.get_inputs_embeds(llm_input)
            vt_start, vt_end = legacy.validate_visual_span(vt_range, embeds.shape[1])
            if label_masks.sum().item() <= 0:
                raise ValueError("empty target mask")
            clean_visual_by_layer = {
                layer: legacy.hidden_visual_slice(legacy.first_hidden(traces[layer_paths[layer]].output), vt_range)
                .detach().clone()
                for layer in expected_layers
            }
            s_clean = legacy.sequence_logprob(clean_logits, label_ids, label_masks)
            s_clean_first = legacy.first_token_logprob(clean_logits, label_ids, label_masks)
            visual_embeds = embeds[:, vt_start:vt_end, :]
            sigma = float(visual_embeds.float().std(unbiased=False).detach().cpu().item())
            if not finite(sigma) or sigma <= args.epsilon_sigma:
                raise RuntimeError(f"invalid visual embedding sigma={sigma}")

            for alpha, semantic_seed, is_formal in unfinished:
                pair_key = (sid, float(alpha), int(semantic_seed))
                if is_formal:
                    # Frozen formal protocol: deterministic by dataset/model/sample/alpha/seed;
                    # deliberately independent of layer and dynamic visual span.
                    rng_seed = legacy.stable_seed("mmke-entity", model_name, sid, float(alpha), int(semantic_seed))
                else:
                    # Historical positive-control only: reproduce the v1.3 key exactly.
                    rng_seed = legacy.stable_seed(
                        "mmke-entity", model_name, sid, float(alpha), int(semantic_seed), vt_start, vt_end
                    )
                actual_sigma = float(alpha) * sigma
                corrupt_inp = legacy.corrupt_llm_input(llm_input, vt_range, actual_sigma, rng_seed)
                with torch.inference_mode():
                    corrupt_out = vllm.get_llm_outpt(corrupt_inp, vt_range)
                    corrupt_logits = legacy.get_logits(corrupt_out).detach()
                s_corrupt = legacy.sequence_logprob(corrupt_logits, label_ids, label_masks)
                s_corrupt_first = legacy.first_token_logprob(corrupt_logits, label_ids, label_masks)
                gap = s_clean - s_corrupt
                gap_valid = finite(s_clean) and finite(s_corrupt) and gap > args.delta_logprob
                corr_row = {
                    "schema_version": SCHEMA_VERSION,
                    "dataset": "mmke-entity",
                    "model": model_name,
                    "sample_index": sample_index,
                    "sample_id": sid,
                    "alpha": float(alpha),
                    "seed": int(semantic_seed),
                    "rng_seed": int(rng_seed),
                    "formal_group": bool(is_formal),
                    "s_clean": float_or_none(s_clean),
                    "s_corrupt": float_or_none(s_corrupt),
                    "clean_corrupt_gap": float_or_none(gap),
                    "s_clean_first": float_or_none(s_clean_first),
                    "s_corrupt_first": float_or_none(s_corrupt_first),
                    "visual_embedding_sigma": sigma,
                    "actual_noise_sigma": actual_sigma,
                    "visual_token_start": int(vt_start),
                    "visual_token_end": int(vt_end),
                    "delta_logprob": args.delta_logprob,
                    "gap_valid": bool(gap_valid),
                    "status": "gap_valid" if gap_valid else ("low_corruption_gap" if finite(gap) else "nonfinite_score"),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }
                append_jsonl(corr_path, corr_row)
                if not gap_valid:
                    append_jsonl(status_path, {**{k: corr_row[k] for k in ("dataset", "model", "sample_id", "alpha", "seed")},
                                                     "formal_group": bool(is_formal), "status": corr_row["status"],
                                                     "completed_layer_count": 0, "expected_layer_count": len(expected_layers),
                                                     "timestamp": corr_row["timestamp"]})
                    print(f"[{sample_index+1}/{len(data)}] {sid} alpha={alpha} seed={semantic_seed} gap={gap:.6f} LOW", flush=True)
                    continue

                completed = 0
                errors = 0
                for layer, layer_path in zip(expected_layers, layer_paths):
                    old = existing_restore.get((*pair_key, int(layer)))
                    if old and old.get("status") == "ok" and finite(old.get("cr")) and finite(old.get("s_restore")):
                        completed += 1
                        continue
                    try:
                        clean_vis = clean_visual_by_layer[layer]

                        def edit_output(output: Any, layer_name: Any = None, target_layer: str = layer_path,
                                        clean: Any = clean_vis, **kwargs: Any) -> Any:
                            actual_layer = kwargs.get("layer", layer_name)
                            if actual_layer != target_layer:
                                return output
                            return legacy.restore_output_visual_slice(output, vt_range, clean)

                        with torch.inference_mode(), TraceDict(
                            model, [layer_path], with_kwargs=True, edit_output=edit_output,
                            clone=True, detach=True
                        ):
                            restored_out = vllm.get_llm_outpt(corrupt_inp, vt_range)
                            restore_logits = legacy.get_logits(restored_out).detach()
                        s_restore = legacy.sequence_logprob(restore_logits, label_ids, label_masks)
                        s_restore_first = legacy.first_token_logprob(restore_logits, label_ids, label_masks)
                        cr = legacy.restoration_score(s_restore, s_corrupt, s_clean, args.eps)
                        cr_first = legacy.restoration_score(s_restore_first, s_corrupt_first, s_clean_first, args.eps)
                        kl_corrupt = legacy.compute_kl(clean_logits, corrupt_logits, label_masks)
                        if kl_corrupt > args.eps:
                            kl_restore = legacy.compute_kl(clean_logits, restore_logits, label_masks)
                            kcr = (kl_corrupt - kl_restore) / (kl_corrupt + args.eps)
                        else:
                            kl_restore = None
                            kcr = None
                        ok = finite(s_restore) and finite(cr)
                        row = {
                            "schema_version": SCHEMA_VERSION,
                            "dataset": "mmke-entity", "model": model_name, "sample_id": sid,
                            "alpha": float(alpha), "seed": int(semantic_seed), "rng_seed": int(rng_seed),
                            "formal_group": bool(is_formal), "layer": int(layer),
                            "s_clean": float_or_none(s_clean), "s_corrupt": float_or_none(s_corrupt),
                            "s_restore": float_or_none(s_restore), "clean_corrupt_gap": float_or_none(gap),
                            "cr": float_or_none(cr), "cr_first": float_or_none(cr_first),
                            "kcr": float_or_none(kcr), "kl_corrupt": float_or_none(kl_corrupt),
                            "kl_restore": float_or_none(kl_restore),
                            "status": "ok" if ok else "nonfinite_restore_score",
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        }
                        append_jsonl(restore_path, row)
                        existing_restore[(*pair_key, int(layer))] = row
                        if ok:
                            completed += 1
                        else:
                            errors += 1
                        del restored_out, restore_logits
                    except Exception as exc:
                        errors += 1
                        row = {
                            "schema_version": SCHEMA_VERSION,
                            "dataset": "mmke-entity", "model": model_name, "sample_id": sid,
                            "alpha": float(alpha), "seed": int(semantic_seed), "rng_seed": int(rng_seed),
                            "formal_group": bool(is_formal), "layer": int(layer), "status": "runtime_error",
                            "error_type": type(exc).__name__, "error": str(exc)[:1000],
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        }
                        append_jsonl(restore_path, row)
                        existing_restore[(*pair_key, int(layer))] = row
                    finally:
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                pair_state = "valid_restore_pair" if completed == len(expected_layers) and errors == 0 else "incomplete_restore_pair"
                status_row = {
                    "schema_version": SCHEMA_VERSION,
                    "dataset": "mmke-entity", "model": model_name, "sample_id": sid,
                    "alpha": float(alpha), "seed": int(semantic_seed), "formal_group": bool(is_formal),
                    "status": pair_state, "completed_layer_count": completed,
                    "expected_layer_count": len(expected_layers), "error_layer_count": errors,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }
                append_jsonl(status_path, status_row)
                existing_status[pair_key] = status_row
                print(f"[{sample_index+1}/{len(data)}] {sid} alpha={alpha} seed={semantic_seed} gap={gap:.6f} layers={completed}/36", flush=True)
                del corrupt_out
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            del clean_out, clean_logits, traces, visual_embeds, clean_visual_by_layer
            del llm_input, label_ids, label_masks
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            append_jsonl(out_dir / "journals" / "sample_errors.jsonl", {
                "sample_id": sid, "sample_index": sample_index, "status": "runtime_error",
                "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            })
            print(f"[ERROR] {sid}: {type(exc).__name__}: {exc}", flush=True)
            if "out of memory" in str(exc).lower():
                raise
        summary = finalize(out_dir, expected_layers, formal_groups)
        print("[summary] " + json.dumps(summary, ensure_ascii=False), flush=True)

    summary = finalize(out_dir, expected_layers, formal_groups)
    json_dump_atomic(out_dir / "run_complete.json", {
        "schema_version": SCHEMA_VERSION, "run_mode": args.run_mode,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "summary": summary,
    })
    print("RUN_COMPLETE " + json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
