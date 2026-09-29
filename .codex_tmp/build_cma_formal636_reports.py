#!/usr/bin/env python3
"""Build the formal CMA-Direct 636-sample deliverables from immutable journals."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

BASE = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_formal_multinoise_multiseed_v1_20260906")
RUN = BASE / "formal636"
PROJECT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
OLD = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_v13_full_g09_gpu0_20260703_134818/mmke-entity/qwen2.5-vl-3b")
SCHEMA = "cma-formal-multinoise-v1"
LAYERS = list(range(36))


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def num(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def finite(value: Any) -> bool:
    return math.isfinite(num(value))


def qstats(values: Sequence[float]) -> Dict[str, Any]:
    arr = np.asarray([x for x in values if math.isfinite(x)], dtype=float)
    names = ("gap_min", "gap_p25", "gap_median", "gap_p75", "gap_p90", "gap_p95", "gap_max")
    if not len(arr):
        return {name: "" for name in names}
    return dict(zip(names, [float(x) for x in np.percentile(arr, [0, 25, 50, 75, 90, 95, 100])]))


def spearman(order_a: Sequence[int], order_b: Sequence[int]) -> float:
    if len(order_a) != len(order_b) or len(order_a) < 2:
        return float("nan")
    pa = {x: i for i, x in enumerate(order_a)}
    pb = {x: i for i, x in enumerate(order_b)}
    common = sorted(set(pa) & set(pb))
    n = len(common)
    if n < 2:
        return float("nan")
    d2 = sum((pa[x] - pb[x]) ** 2 for x in common)
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def kendall(order_a: Sequence[int], order_b: Sequence[int]) -> float:
    pa = {x: i for i, x in enumerate(order_a)}
    pb = {x: i for i, x in enumerate(order_b)}
    common = sorted(set(pa) & set(pb))
    concordant = discordant = 0
    for i, x in enumerate(common):
        for y in common[i + 1:]:
            sign = (pa[x] - pa[y]) * (pb[x] - pb[y])
            concordant += sign > 0
            discordant += sign < 0
    total = concordant + discordant
    return (concordant - discordant) / total if total else float("nan")


def layer_scores(restores: Sequence[Dict[str, str]], pair_set: set, group_label: str) -> List[Dict[str, Any]]:
    vals: Dict[int, List[Dict[str, str]]] = defaultdict(list)
    for row in restores:
        key = (row["sample_id"], num(row["alpha"]), int(row["seed"]))
        if key in pair_set and row.get("status") == "ok" and finite(row.get("cr")):
            vals[int(row["layer"])].append(row)
    rows = []
    for layer in LAYERS:
        rv = vals.get(layer, [])
        crs = [num(x["cr"]) for x in rv]
        kcrs = [num(x["kcr"]) for x in rv if finite(x.get("kcr"))]
        by_sample: Dict[str, List[float]] = defaultdict(list)
        for x in rv:
            by_sample[x["sample_id"]].append(num(x["cr"]))
        sample_means = [float(np.mean(v)) for v in by_sample.values()]
        rows.append({
            "schema_version": SCHEMA, "group": group_label, "layer": layer,
            "valid_pair_count": len(crs), "valid_unique_sample_count": len(by_sample),
            "CR_mean": float(np.mean(crs)) if crs else "",
            "CR_std": float(np.std(crs)) if crs else "",
            "KCR_mean": float(np.mean(kcrs)) if kcrs else "",
            "sample_balanced_CR_mean": float(np.mean(sample_means)) if sample_means else "",
            "restore_forward_count": len(rv),
        })
    ranked = sorted(rows, key=lambda r: (-(num(r["CR_mean"]) if finite(r["CR_mean"]) else -1e99),
                                         -(num(r["KCR_mean"]) if finite(r["KCR_mean"]) else -1e99),
                                         -int(r["valid_pair_count"]), int(r["layer"])))
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
    return ranked


def main() -> None:
    corr = read_csv(RUN / "canonical/cma_corruption_pairs.csv")
    pair_rows = read_csv(RUN / "canonical/cma_pair_status.csv")
    restores_raw = read_csv(RUN / "canonical/cma_restore_long.csv")
    raw_summary_path = RUN / "canonical/summary.json"
    raw_summary = json.loads(raw_summary_path.read_text(encoding="utf-8"))
    (RUN / "runner_summary_raw.json").write_text(json.dumps(raw_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    valid_pairs = {
        (r["sample_id"], num(r["alpha"]), int(r["seed"]))
        for r in pair_rows if r.get("status") == "valid_restore_pair" and int(r.get("completed_layer_count", 0)) == 36
    }
    input_ids = sorted({r["sample_id"] for r in corr})
    valid_ids = sorted({x[0] for x in valid_pairs})
    if len(corr) != 5724 or len(input_ids) != 636:
        raise RuntimeError(f"invalid formal input counts: pairs={len(corr)} unique={len(input_ids)}")
    if len(restores_raw) != len(valid_pairs) * 36:
        raise RuntimeError(f"restore count mismatch: {len(restores_raw)} != {len(valid_pairs)}*36")

    pair_long = []
    for r in corr:
        key = (r["sample_id"], num(r["alpha"]), int(r["seed"]))
        valid = key in valid_pairs
        pair_long.append({
            **r, "restore_pair_valid": valid, "included_in_formal_aggregate": valid,
            "invalid_reason": "" if valid else ("low_corruption_gap" if str(r.get("gap_valid", "")).lower() != "true" else "missing_or_nonfinite_restore"),
        })
    write_csv(RUN / "cma_sample_alpha_seed_long.csv", pair_long)
    write_csv(RUN / "cma_corruption_pairs.csv", corr)

    restores = []
    for r in restores_raw:
        key = (r["sample_id"], num(r["alpha"]), int(r["seed"]))
        valid = key in valid_pairs and r.get("status") == "ok" and finite(r.get("s_restore")) and finite(r.get("cr"))
        restores.append({
            **r, "gap_valid": True, "restore_valid": valid,
            "included_in_formal_aggregate": valid,
            "invalid_reason": "" if valid else (r.get("status") or "invalid_restore"),
            "restore_status": r.get("status"),
        })
    write_csv(RUN / "cma_restore_long.csv", restores)

    specs: List[Tuple[str, Any, Any, str]] = []
    for alpha in (0.5, 1.0, 2.0):
        for seed in (0, 1, 2):
            specs.append(("alpha_seed", alpha, seed, f"alpha={alpha},seed={seed}"))
    specs += [("alpha", alpha, None, f"alpha={alpha},all_seeds") for alpha in (0.5, 1.0, 2.0)]
    specs += [("seed", None, seed, f"all_alpha,seed={seed}") for seed in (0, 1, 2)]
    specs.append(("formal_all", None, None, "formal_all_3x3"))

    group_summary = []
    all_layer_rows = []
    rankings: Dict[str, List[int]] = {}
    group_pair_sets: Dict[str, set] = {}
    for kind, alpha, seed, label in specs:
        crows = [r for r in corr if (alpha is None or num(r["alpha"]) == alpha) and (seed is None or int(r["seed"]) == seed)]
        keys = {(r["sample_id"], num(r["alpha"]), int(r["seed"])) for r in crows}
        vpairs = keys & valid_pairs
        group_pair_sets[label] = vpairs
        scores = layer_scores(restores, vpairs, label)
        all_layer_rows.extend(scores)
        ranking = [int(r["layer"]) for r in scores if finite(r["CR_mean"])]
        rankings[label] = ranking
        gaps = [num(r["clean_corrupt_gap"]) for r in crows if finite(r.get("clean_corrupt_gap"))]
        group_summary.append({
            "schema_version": SCHEMA, "group_type": kind, "group": label,
            "alpha": "" if alpha is None else alpha, "seed": "" if seed is None else seed,
            "input_unique_samples": len({r["sample_id"] for r in crows}), "input_parameter_pairs": len(crows),
            "valid_unique_samples": len({x[0] for x in vpairs}), "valid_restore_pairs": len(vpairs),
            "valid_pair_ratio": len(vpairs) / len(crows) if crows else 0.0,
            "low_corruption_gap_pairs": len(crows) - len(vpairs),
            **qstats(gaps),
            "top3": ",".join(f"L{x}" for x in ranking[:3]),
            "top5": ",".join(f"L{x}" for x in ranking[:5]),
            "support_status": "no_valid_group" if not vpairs else ("low_support_group" if len({x[0] for x in vpairs}) < 30 else "supported_group"),
        })
    write_csv(RUN / "cma_alpha_seed_coverage_summary.csv", group_summary)
    write_csv(RUN / "cma_layer_alpha_seed_scores.csv", all_layer_rows)

    formal_order = rankings["formal_all_3x3"]
    formal_top3, formal_top5 = formal_order[:3], formal_order[:5]
    stability = []
    frequency3, frequency5 = Counter(), Counter()
    for row in group_summary:
        if row["group_type"] != "alpha_seed":
            continue
        label = row["group"]
        order = rankings[label]
        top3, top5 = set(order[:3]), set(order[:5])
        frequency3.update(top3)
        frequency5.update(top5)
        ft3, ft5 = set(formal_top3), set(formal_top5)
        stability.append({
            "schema_version": SCHEMA, "group": label,
            "valid_unique_samples": row["valid_unique_samples"], "valid_restore_pairs": row["valid_restore_pairs"],
            "support_status": row["support_status"],
            "top1_agreement": bool(order and formal_order and order[0] == formal_order[0]),
            "top3_overlap": len(top3 & ft3), "top3_jaccard": len(top3 & ft3) / len(top3 | ft3) if top3 | ft3 else "",
            "top5_overlap": len(top5 & ft5), "top5_jaccard": len(top5 & ft5) / len(top5 | ft5) if top5 | ft5 else "",
            "spearman_vs_formal": spearman(order, formal_order) if order else "",
            "kendall_vs_formal": kendall(order, formal_order) if order else "",
            "top3": ",".join(f"L{x}" for x in order[:3]), "top5": ",".join(f"L{x}" for x in order[:5]),
        })
    write_csv(RUN / "cma_candidate_stability.csv", stability)
    write_csv(RUN / "cma_candidate_frequency.csv", [
        {"schema_version": SCHEMA, "layer": layer, "top3_frequency_9_groups": frequency3[layer],
         "top5_frequency_9_groups": frequency5[layer]} for layer in LAYERS
    ])

    full_pair_scores = next(layer_scores(restores, valid_pairs, "formal_all_pair_weighted") for _ in [0])
    sample_ranked = sorted(full_pair_scores, key=lambda r: (-(num(r["sample_balanced_CR_mean"]) if finite(r["sample_balanced_CR_mean"]) else -1e99), int(r["layer"])))
    sample_order = [int(r["layer"]) for r in sample_ranked if finite(r["sample_balanced_CR_mean"])]
    rank_agreement = {
        "pair_weighted_top3": formal_top3, "sample_balanced_top3": sample_order[:3],
        "pair_weighted_top5": formal_top5, "sample_balanced_top5": sample_order[:5],
        "spearman": spearman(formal_order, sample_order), "kendall": kendall(formal_order, sample_order),
    }

    low_gap = len(corr) - len(valid_pairs)
    coverage_status = "eligible" if len(valid_ids) >= 128 else ("low_valid_coverage" if len(valid_ids) >= 30 else ("low_valid_coverage_severe" if valid_ids else "no_valid_cma_sample"))
    coverage = {
        "schema_version": SCHEMA, "method": "CMA-Direct", "variant": "direct",
        "dataset": "MMKE-entity", "model": "Qwen2.5-VL-3B", "run_stage": "formal636",
        "total_samples": 636, "input_unique_samples": 636, "nonempty_target_samples": 636,
        "valid_unique_samples": len(valid_ids), "fully_excluded_unique_samples": 636 - len(valid_ids),
        "total_sample_alpha_seed_pairs": 5724, "valid_corruption_pairs": len(valid_pairs),
        "valid_restore_pairs": len(valid_pairs), "low_corruption_gap_pair_count": low_gap,
        "nonfinite_gap_pair_count": 0, "runtime_error_pair_count": 0,
        "missing_restore_pair_count": 0, "nonfinite_restore_pair_count": 0,
        "excluded_pair_count": low_gap, "common_restore_pairs_all_layers": len(valid_pairs),
        "nonfinite_restore_records": 0, "missing_restore_records": 0,
        "valid_ratio_unique": len(valid_ids) / 636, "valid_ratio_pairs": len(valid_pairs) / 5724,
        "minimum_valid_unique_samples": 128, "status": coverage_status,
        "rank_metric": "CR_mean", "aux_metric": "KCR_mean",
        "top3": formal_top3, "top5": formal_top5,
        "valid_sample_id_hash": hashlib.sha256(json.dumps(valid_ids, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "pair_weighted_vs_sample_balanced_rank_agreement": rank_agreement,
    }
    (RUN / "cma_coverage_summary.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    formal_candidates = {
        "schema_version": SCHEMA, "method": "CMA-Direct", "variant": "direct",
        "dataset": "MMKE-entity", "model": "Qwen2.5-VL-3B",
        "target_field": "alt", "target_scope": "complete_alt_sequence",
        "corruption_scope": "visual_tokens", "noise_alpha_list": [0.5, 1.0, 2.0],
        "noise_seeds": [0, 1, 2], "delta_logprob": 0.05,
        "input_unique_samples": 636, "total_sample_alpha_seed_pairs": 5724,
        "valid_unique_samples": len(valid_ids), "valid_ratio_unique": len(valid_ids) / 636,
        "valid_restore_pairs": len(valid_pairs), "common_restore_pairs_all_layers": len(valid_pairs),
        "valid_ratio_pairs": len(valid_pairs) / 5724, "rank_metric": "CR_mean", "aux_metric": "KCR_mean",
        "top3": [f"L{x}" for x in formal_top3], "top5": [f"L{x}" for x in formal_top5],
        "raw_rank_all_layers": [f"L{x}" for x in formal_order], "clean_rank_all_layers": [f"L{x}" for x in formal_order],
        "status": coverage_status, "confidence_note": "below 128 valid unique samples; retain as low-coverage CMA result",
    }
    (RUN / "cma_formal_top3_top5.json").write_text(json.dumps(formal_candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # Correct the runner's provisional tier label while preserving it verbatim above.
    corrected_summary = dict(raw_summary)
    corrected_summary["status"] = coverage_status
    corrected_summary["coverage_tier"] = coverage_status
    corrected_summary["valid_ratio_pairs"] = len(valid_pairs) / 5724
    corrected_summary["fully_excluded_unique_samples"] = 636 - len(valid_ids)
    corrected_summary["top3"] = formal_top3
    corrected_summary["top5"] = formal_top5
    raw_summary_path.write_text(json.dumps(corrected_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = RUN / "sample_manifest.json"
    (RUN / "sample_manifest.sha256").write_text(f"{sha256(manifest_path)}  sample_manifest.json\n", encoding="utf-8")
    frozen = json.loads((RUN / "frozen_config.json").read_text(encoding="utf-8"))
    (RUN / "config_frozen.yaml").write_text("\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in frozen.items()) + "\n", encoding="utf-8")
    runner_snapshot = BASE / "code/run_cma_direct_formal_multinoise_v1.py"
    aggregator = BASE / "code/build_cma_formal636_reports.py"
    code_version = (
        f"schema_version={SCHEMA}\nrunner_snapshot={runner_snapshot}\nrunner_sha256={sha256(runner_snapshot)}\n"
        f"aggregator={aggregator}\naggregator_sha256={sha256(aggregator)}\n"
        f"historical_runner_sha256={sha256(PROJECT / 'scripts/run_cma_direct_candidate_layers.py')}\n"
        f"manifest_sha256={sha256(manifest_path)}\n"
        f"dataset_sha256={sha256(Path(frozen['data_path']))}\nconfig_sha256={sha256(Path(frozen['config']))}\n"
        f"python={frozen['runtime_python']}\ntorch={frozen['torch_version']}\ntransformers={frozen['transformers_version']}\n"
    )
    (RUN / "code_version.txt").write_text(code_version, encoding="utf-8")

    old_top3 = [1, 0, 2]
    old_top5 = [1, 0, 2, 3, 6]
    t3i, t3u = set(old_top3) & set(formal_top3), set(old_top3) | set(formal_top3)
    t5i, t5u = set(old_top5) & set(formal_top5), set(old_top5) | set(formal_top5)
    comparison = f"""# CMA v0 vs formal multi-noise/multi-seed comparison

| Item | Historical v0 | Formal v1 |
|---|---:|---:|
| Input unique samples | 636 | 636 |
| Valid unique samples | 9 | {len(valid_ids)} |
| Valid unique ratio | 1.42% | {len(valid_ids)/636:.2%} |
| Valid restore pairs | 9/636 | {len(valid_pairs)}/5724 |
| Alpha | 1.0 | 0.5, 1.0, 2.0 |
| Seed | 2026 | 0, 1, 2 |
| Low-gap pairs | 627 | {low_gap} |
| Top-3 | L1,L0,L2 | {','.join('L'+str(x) for x in formal_top3)} |
| Top-5 | L1,L0,L2,L3,L6 | {','.join('L'+str(x) for x in formal_top5)} |
| Coverage status | low_valid_coverage_severe | {coverage_status} |

- Top-3 overlap: {len(t3i)}/3; Jaccard={len(t3i)/len(t3u):.4f}.
- Top-5 overlap: {len(t5i)}/5; Jaccard={len(t5i)/len(t5u):.4f}.
- New formal-only Top-5 layer: {','.join('L'+str(x) for x in sorted(set(formal_top5)-set(old_top5))) or 'none'}.
- Historical-only Top-5 layer: {','.join('L'+str(x) for x in sorted(set(old_top5)-set(formal_top5))) or 'none'}.
- The new protocol improves unique coverage from 9 to {len(valid_ids)} but remains below the predeclared eligibility threshold of 128; it must not be interpreted at equal confidence to adequately covered methods.
- No Adapter training was launched from these candidates.
"""
    (RUN / "cma_v0_vs_formal_comparison.md").write_text(comparison, encoding="utf-8")

    supported = [r for r in stability if int(r["valid_restore_pairs"]) > 0]
    avg_j3 = float(np.mean([num(r["top3_jaccard"]) for r in supported])) if supported else float("nan")
    report = f"""# CMA formal 636-sample report

## Result

- Protocol: alpha `[0.5,1.0,2.0]` × seed `[0,1,2]`, `delta_logprob=0.05`.
- Corruption pairs: 5724/5724; common complete 36-layer restore pairs: {len(valid_pairs)}.
- Valid unique samples: {len(valid_ids)}/636 ({len(valid_ids)/636:.2%}); fully excluded: {636-len(valid_ids)}.
- Low-gap pairs: {low_gap}; nonfinite/runtime/missing restore errors: 0/0/0.
- Top-3: `{','.join('L'+str(x) for x in formal_top3)}`.
- Top-5: `{','.join('L'+str(x) for x in formal_top5)}`.
- Status: **{coverage_status}** because valid unique samples are below 128.

## Stability

- Supported alpha×seed groups: {len(supported)}/9; unsupported groups remain explicitly recorded.
- Mean Top-3 Jaccard versus pooled ranking across supported groups: {avg_j3:.4f}.
- Pair-weighted versus sample-balanced Top-3: `{','.join('L'+str(x) for x in formal_top3)}` vs `{','.join('L'+str(x) for x in sample_order[:3])}`.
- Pair-weighted versus sample-balanced Spearman: {rank_agreement['spearman']:.4f}; Kendall: {rank_agreement['kendall']:.4f}.

## Interpretation

The multi-parameter protocol raised valid unique coverage from 9 to {len(valid_ids)}, but coverage remains below the predeclared 128-sample eligibility line. The Top-3 is unchanged from history; Top-5 replaces historical L6 with L4. Retain this as a low-coverage CMA result, do not lower the threshold post hoc, and do not automatically enqueue Adapter training.
"""
    (RUN / "cma_formal_report.md").write_text(report, encoding="utf-8")

    artifacts = [
        "config_frozen.yaml", "code_version.txt", "sample_manifest.json", "sample_manifest.sha256",
        "cma_corruption_pairs.csv", "cma_restore_long.csv", "cma_sample_alpha_seed_long.csv",
        "cma_alpha_seed_coverage_summary.csv", "cma_layer_alpha_seed_scores.csv",
        "cma_candidate_stability.csv", "cma_candidate_frequency.csv", "cma_formal_top3_top5.json",
        "cma_coverage_summary.json", "cma_v0_vs_formal_comparison.md", "cma_formal_report.md",
        "runner_summary_raw.json", "canonical/summary.json",
    ]
    manifest = {"schema_version": SCHEMA, "stage": "formal636_complete", "files": []}
    for rel in artifacts:
        path = RUN / rel
        manifest["files"].append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    (RUN / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
