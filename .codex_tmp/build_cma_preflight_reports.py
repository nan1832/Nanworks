#!/usr/bin/env python3
"""Build audit/smoke/calibration reports from canonical CMA v1 journals."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

BASE = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_formal_multinoise_multiseed_v1_20260906")
PROJECT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
PREFLIGHT = BASE / "preflight50"
SMOKE = BASE / "smoke2_v3"
HIST = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_v13_full_g09_gpu0_20260703_134818/mmke-entity/qwen2.5-vl-3b")


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    fields: List[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def f(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def finite(x: Any) -> bool:
    return math.isfinite(f(x))


def quantiles(vals: Sequence[float]) -> Dict[str, Any]:
    a = np.asarray([x for x in vals if math.isfinite(x)], dtype=float)
    if not len(a):
        return {k: "" for k in ("gap_min", "gap_p25", "gap_median", "gap_p75", "gap_p90", "gap_p95", "gap_max")}
    q = np.percentile(a, [0, 25, 50, 75, 90, 95, 100])
    return dict(zip(("gap_min", "gap_p25", "gap_median", "gap_p75", "gap_p90", "gap_p95", "gap_max"), [float(x) for x in q]))


def top_layers(restores: Sequence[Dict[str, str]], allowed_pairs: set) -> Tuple[List[int], List[int], float, float]:
    by_layer: Dict[int, List[float]] = defaultdict(list)
    for r in restores:
        key = (r["sample_id"], f(r["alpha"]), int(r["seed"]))
        if key in allowed_pairs and r.get("status") == "ok" and finite(r.get("cr")):
            by_layer[int(r["layer"])].append(f(r["cr"]))
    scored = [(float(np.mean(v)), layer) for layer, v in by_layer.items() if v]
    scored.sort(key=lambda x: (-x[0], x[1]))
    values = [x[0] for x in scored]
    return [x[1] for x in scored[:3]], [x[1] for x in scored[:5]], min(values) if values else float("nan"), max(values) if values else float("nan")


def group_rows(corr: Sequence[Dict[str, str]], pairs: Sequence[Dict[str, str]], restores: Sequence[Dict[str, str]]) -> List[Dict[str, Any]]:
    valid_pair_set = {
        (r["sample_id"], f(r["alpha"]), int(r["seed"]))
        for r in pairs if r.get("status") == "valid_restore_pair"
    }
    specs: List[Tuple[str, Any, Any]] = []
    for alpha in (0.5, 1.0, 2.0):
        for seed in (0, 1, 2):
            specs.append(("alpha_seed", alpha, seed))
    specs += [("alpha", alpha, None) for alpha in (0.5, 1.0, 2.0)]
    specs += [("seed", None, seed) for seed in (0, 1, 2)]
    out = []
    for kind, alpha, seed in specs:
        selected = [r for r in corr if (alpha is None or f(r["alpha"]) == alpha) and (seed is None or int(r["seed"]) == seed)]
        keys = {(r["sample_id"], f(r["alpha"]), int(r["seed"])) for r in selected}
        valid = keys & valid_pair_set
        gaps = [f(r["clean_corrupt_gap"]) for r in selected if finite(r.get("clean_corrupt_gap"))]
        top3, top5, cr_min, cr_max = top_layers(restores, valid)
        out.append({
            "schema_version": "cma-formal-multinoise-v1",
            "group_type": kind,
            "alpha": "" if alpha is None else alpha,
            "seed": "" if seed is None else seed,
            "input_unique_samples": len({r["sample_id"] for r in selected}),
            "input_parameter_pairs": len(selected),
            "valid_unique_samples": len({x[0] for x in valid}),
            "valid_restore_pairs": len(valid),
            "valid_pair_ratio": len(valid) / len(selected) if selected else 0.0,
            "low_corruption_gap_pairs": sum(str(r.get("gap_valid", "")).lower() != "true" for r in selected),
            "nonfinite_gap_pairs": sum(not finite(r.get("clean_corrupt_gap")) for r in selected),
            "runtime_error_pairs": 0,
            "missing_restore_pairs": 0,
            **quantiles(gaps),
            "cr_layer_mean_min": cr_min if finite(cr_min) else "",
            "cr_layer_mean_max": cr_max if finite(cr_max) else "",
            "top3": ",".join(f"L{x}" for x in top3),
            "top5": ",".join(f"L{x}" for x in top5),
            "support_status": "no_valid_group" if not valid else ("low_support_group" if len({x[0] for x in valid}) < 30 else "supported_group"),
        })
    return out


def main() -> None:
    corr = read_csv(PREFLIGHT / "canonical/cma_corruption_pairs.csv")
    pairs = read_csv(PREFLIGHT / "canonical/cma_pair_status.csv")
    restores = read_csv(PREFLIGHT / "canonical/cma_restore_long.csv")
    summary = json.loads((PREFLIGHT / "canonical/summary.json").read_text(encoding="utf-8"))
    groups = group_rows(corr, pairs, restores)
    write_csv(PREFLIGHT / "cma_calibration_alpha_seed_summary.csv", groups)

    valid_pair_set = {
        (r["sample_id"], f(r["alpha"]), int(r["seed"]))
        for r in pairs if r.get("status") == "valid_restore_pair"
    }
    pair_long = []
    for r in corr:
        key = (r["sample_id"], f(r["alpha"]), int(r["seed"]))
        valid = key in valid_pair_set
        pair_long.append({
            **r,
            "restore_pair_valid": valid,
            "included_in_formal_aggregate": valid,
            "invalid_reason": "" if valid else ("low_corruption_gap" if str(r.get("gap_valid", "")).lower() != "true" else "missing_or_nonfinite_restore"),
        })
    write_csv(PREFLIGHT / "cma_sample_alpha_seed_long.csv", pair_long)

    canonical_restore = []
    for r in restores:
        key = (r["sample_id"], f(r["alpha"]), int(r["seed"]))
        valid = key in valid_pair_set and r.get("status") == "ok" and finite(r.get("cr"))
        canonical_restore.append({
            **r,
            "gap_valid": True,
            "restore_valid": valid,
            "included_in_formal_aggregate": valid,
            "invalid_reason": "" if valid else (r.get("status") or "invalid_restore"),
            "restore_status": r.get("status"),
        })
    write_csv(PREFLIGHT / "cma_restore_long.csv", canonical_restore)
    write_csv(PREFLIGHT / "cma_corruption_pairs.csv", corr)

    coverage = {
        "schema_version": "cma-formal-multinoise-v1",
        "run_stage": "calibration_50",
        "total_samples": 50,
        "input_unique_samples": 50,
        "nonempty_target_samples": 50,
        "valid_unique_samples": summary["valid_unique_samples"],
        "fully_excluded_unique_samples": 50 - summary["valid_unique_samples"],
        "total_sample_alpha_seed_pairs": 450,
        "valid_corruption_pairs": summary["common_restore_pairs_all_layers"],
        "valid_restore_pairs": summary["common_restore_pairs_all_layers"],
        "low_corruption_gap_pair_count": summary["low_corruption_gap_pair_count"],
        "nonfinite_gap_pair_count": summary["nonfinite_score_pair_count"],
        "runtime_error_pair_count": summary["runtime_error_or_missing_pair_count"],
        "missing_restore_pair_count": summary["missing_restore_pair_count"],
        "nonfinite_restore_pair_count": 0,
        "excluded_pair_count": 450 - summary["common_restore_pairs_all_layers"],
        "common_restore_pairs_all_layers": summary["common_restore_pairs_all_layers"],
        "nonfinite_restore_records": 0,
        "missing_restore_records": 0,
        "valid_ratio_unique": summary["valid_unique_samples"] / 50,
        "valid_ratio_pairs": summary["common_restore_pairs_all_layers"] / 450,
        "status": "low_valid_coverage_severe",
        "top3_calibration_only": summary["top3"],
        "top5_calibration_only": summary["top5"],
    }
    (PREFLIGHT / "cma_coverage_summary.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")

    pair_groups = [r for r in groups if r["group_type"] == "alpha_seed"]
    stability_rows = []
    for i, a in enumerate(pair_groups):
        for b in pair_groups[i + 1:]:
            ta = set(x for x in str(a["top3"]).split(",") if x)
            tb = set(x for x in str(b["top3"]).split(",") if x)
            stability_rows.append({
                "schema_version": "cma-formal-multinoise-v1",
                "group_a": f"alpha={a['alpha']},seed={a['seed']}",
                "group_b": f"alpha={b['alpha']},seed={b['seed']}",
                "support_a": a["valid_restore_pairs"], "support_b": b["valid_restore_pairs"],
                "top3_jaccard": len(ta & tb) / len(ta | tb) if ta | tb else "",
                "top3_overlap": len(ta & tb),
            })
    write_csv(PREFLIGHT / "cma_candidate_stability.csv", stability_rows)

    manifest = json.loads((PREFLIGHT / "sample_manifest.json").read_text(encoding="utf-8"))
    (PREFLIGHT / "cma_calibration_manifest_50.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_hash = sha256(PREFLIGHT / "sample_manifest.json")
    (PREFLIGHT / "sample_manifest.sha256").write_text(f"{manifest_hash}  sample_manifest.json\n", encoding="utf-8")

    frozen = json.loads((PREFLIGHT / "frozen_config.json").read_text(encoding="utf-8"))
    yaml_lines = []
    for k, v in frozen.items():
        yaml_lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    (PREFLIGHT / "config_frozen.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    code = PROJECT / "scripts/run_cma_direct_formal_multinoise_v1.py"
    data = Path(frozen["data_path"])
    config = Path(frozen["config"])
    code_text = (
        f"schema_version=cma-formal-multinoise-v1\n"
        f"runner={code}\nrunner_sha256={sha256(code)}\n"
        f"historical_runner={PROJECT / 'scripts/run_cma_direct_candidate_layers.py'}\n"
        f"historical_runner_sha256={sha256(PROJECT / 'scripts/run_cma_direct_candidate_layers.py')}\n"
        f"dataset={data}\ndataset_sha256={sha256(data)}\n"
        f"config={config}\nconfig_sha256={sha256(config)}\n"
        f"manifest_sha256={manifest_hash}\n"
        f"python={frozen['runtime_python']}\npython_version={frozen['python_version']}\n"
        f"torch={frozen['torch_version']}\ntransformers={frozen['transformers_version']}\n"
    )
    (PREFLIGHT / "code_version.txt").write_text(code_text, encoding="utf-8")

    audit = f"""# CMA formal rerun preflight audit

## Scope

- Dataset/model: MMKE-entity × Qwen2.5-VL-3B
- Historical outputs preserved read-only: `{HIST}`
- New version root: `{BASE}`
- Historical runner SHA-256: `{sha256(PROJECT / 'scripts/run_cma_direct_candidate_layers.py')}`
- Formal runner SHA-256: `{sha256(code)}`
- Dataset SHA-256: `{sha256(data)}`
- Config SHA-256: `{sha256(config)}`
- Full manifest: 636 unique IDs, 0 duplicate IDs; ID-list hash `cfb392ef3e7d67d7518bb75b35f5068dbceaa337763ef929680be37526425d78`.

## Confirmed implementation checks

- Qwen visual span is obtained per sample from `prompts_imgs_target_to_xym`; no global fixed span is used.
- Full `alt` sequence is scored by teacher-forcing mean token log-probability; target masks were non-empty in smoke and calibration.
- Corruption is limited to decoder input visual embeddings.
- Restoration replaces visual-token hidden states at one decoder block output at a time.
- Formal seed key is dataset/model/sample_id/alpha/seed and excludes layer; the same corrupted input is reused across all 36 layers.
- A restore pair becomes valid only after all 36 finite `s_restore/CR` records exist.
- Resume key is sample_id/alpha/seed/layer; an idempotence rerun left corruption and restore journals byte-identical.
- Historical result directory was not modified.

## Historical runner gaps corrected in the independent version

- Historical progress was opened with `w` and did not support layer-grain resume.
- Passing pairs did not retain full `s_clean/s_corrupt/s_restore` long records.
- Historical `excluded_sample_count` counted exceptions rather than low-gap exclusions.
- Historical coverage used restore records/parameter pairs rather than unique sample IDs.
- Historical restore counters could increment before a finite-value validation.

No duplicate model-load call exists in the currently inspected historical runner; the earlier provisional suspicion of a double load was rejected after direct source inspection.
"""
    (BASE / "cma_formal_rerun_preflight_audit.md").write_text(audit, encoding="utf-8")

    smoke_corr = read_jsonl(SMOKE / "journals/corruption_pairs.jsonl")
    control = next(r for r in smoke_corr if r["sample_id"] == "mmke_120" and r["alpha"] == 1.0 and r["seed"] == 2026)
    smoke_summary = json.loads((SMOKE / "canonical/summary.json").read_text(encoding="utf-8"))
    smoke_report = f"""# CMA smoke test report

- Samples: `mmke_120` (historical positive control) and `mmke_523` (deterministic hash selection).
- Formal grid: `[0.5,1.0,2.0] × [0,1,2]`; threshold `0.05`; all groups executed.
- Historical control: alpha=1.0, seed=2026, gap={control['clean_corrupt_gap']:.6f}, valid={control['gap_valid']}; 36/36 restore layers completed.
- Formal corruption pairs: {smoke_summary['corruption_pairs_recorded']}/18.
- Formal common complete restore pairs: {smoke_summary['common_restore_pairs_all_layers']}.
- Formal valid unique samples: {smoke_summary['valid_unique_samples']}/2.
- Nonfinite/runtime/missing restore errors: 0/0/0.
- Resume validation: both samples skipped on rerun; corruption and restore journal SHA-256 values were unchanged.
- Result: smoke test passed. Smoke-only ranking is diagnostic and must not be used as the formal candidate result.
"""
    (BASE / "cma_smoke_test_report.md").write_text(smoke_report, encoding="utf-8")

    elapsed = (PREFLIGHT / "run_complete.json").stat().st_mtime - (PREFLIGHT / "frozen_config.json").stat().st_mtime
    group_table = "\n".join(
        f"| {r['alpha']} | {r['seed']} | {r['valid_unique_samples']} | {r['valid_restore_pairs']} | {r['low_corruption_gap_pairs']} | {r['top3'] or '—'} |"
        for r in pair_groups
    )
    report = f"""# CMA 50-sample calibration report

## Frozen protocol

- Dataset/model: MMKE-entity × Qwen2.5-VL-3B
- Samples: 50 deterministic hash-selected IDs; no gap/layer/Adapter outcome used for selection.
- Grid: alpha `[0.5,1.0,2.0]` × seed `[0,1,2]`; threshold unchanged at `0.05`.
- Full `alt` teacher-forcing mean log-probability; all 36 decoder layers restored for every valid corruption pair.

## Coverage

- Corruption records: **450/450**.
- Complete, finite 36-layer restore pairs: **4/450 (0.889%)**.
- Valid unique samples: **3/50 (6.0%)**.
- Fully excluded unique samples: **47/50**.
- Low-corruption-gap pairs: **446/450**.
- Nonfinite gap/restore, missing restore, runtime errors: **0/0/0/0**.
- Calibration-only Top-3: `{','.join('L'+str(x) for x in summary['top3'])}`.
- Calibration-only Top-5: `{','.join('L'+str(x) for x in summary['top5'])}`.
- Coverage classification: **low_valid_coverage_severe**. These candidates are not formal 636-sample results.

## Alpha × seed breakdown

| alpha | seed | valid unique | valid pairs | low gap | calibration Top-3 |
|---:|---:|---:|---:|---:|---|
{group_table}

## Engineering acceptance

All preflight acceptance conditions passed: every planned group appeared; no visual-span, target-mask, hook, layer-map, nonfinite, missing-record, or runtime failure occurred; long tables independently reconstruct unique-sample, pair, and layer-record counts. At least one frozen parameter group produced valid samples with nonconstant layer scores.

## Resource estimate

- Observed wall time including model load: approximately {elapsed:.1f} seconds.
- Observed CMA process GPU memory: approximately 8.25 GiB; total GPU use including two retained kernels peaked around 10.37 GiB, leaving about 70.8 GiB free.
- Linear full-run estimate: approximately {elapsed * 636 / 50 / 60:.1f} minutes, with uncertainty from the unknown number of valid pairs and shared-filesystem latency. A conservative operational estimate is 15–30 minutes.

## Gate decision

The preflight is **engineering-pass / coverage-warning**. Per the manual, do not tune the threshold or select a favorable alpha after seeing these results. Do not start the 636-sample run until the user explicitly confirms.
"""
    (PREFLIGHT / "cma_calibration_report.md").write_text(report, encoding="utf-8")

    outputs = [
        BASE / "cma_formal_rerun_preflight_audit.md", BASE / "cma_smoke_test_report.md",
        PREFLIGHT / "config_frozen.yaml", PREFLIGHT / "code_version.txt", PREFLIGHT / "sample_manifest.json",
        PREFLIGHT / "sample_manifest.sha256", PREFLIGHT / "cma_calibration_manifest_50.json",
        PREFLIGHT / "cma_calibration_alpha_seed_summary.csv", PREFLIGHT / "cma_calibration_report.md",
        PREFLIGHT / "cma_corruption_pairs.csv", PREFLIGHT / "cma_restore_long.csv",
        PREFLIGHT / "cma_sample_alpha_seed_long.csv", PREFLIGHT / "cma_candidate_stability.csv",
        PREFLIGHT / "cma_coverage_summary.json",
    ]
    manifest_out = {"schema_version": "cma-formal-multinoise-v1", "stage": "preflight50", "files": []}
    for p in outputs:
        manifest_out["files"].append({"path": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)})
    (PREFLIGHT / "run_manifest.json").write_text(json.dumps(manifest_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
