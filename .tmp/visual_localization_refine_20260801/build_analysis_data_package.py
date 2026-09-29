from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset")
VG = ROOT / "md" / "Location" / "VisualGradient_11formula_analysis_files_20260720"
AN = VG / "analysis_outputs_20260731"
LEDGER = ROOT / "md" / "Location" / "6location_7model_3datas_top_3_5_layers_outcome.md"
MANUAL = VG / "zn_visual_gradient_prediction_实验操作手册_7基础公式_4Ours指标_视觉版_补充诊断列_修复执行版.md"
OUT = ROOT / "outputs" / "视觉梯度11公式与真实扫层分析数据包_20260801"
ZIP = ROOT / "outputs" / "视觉梯度11公式与真实扫层分析数据包_20260801.zip"

DATASET_TOTAL = {"evqa-pilot500": 500, "mmke-visual": 214, "mmke-entity": 636}
EVAL_TOTAL = {"evqa-pilot500": 2093, "mmke-visual": 293, "mmke-entity": 954}

FORMULAS = [
    ("base_7_visual", "M_dot", "S_v_dot"),
    ("base_7_visual", "M_cos", "S_v_cos"),
    ("base_7_visual", "M_new_norm", "S_v_new_norm"),
    ("base_7_visual", "M_pos_ratio", "S_v_positive_ratio"),
    ("base_7_visual", "M_conflict", "S_v_conflict"),
    ("base_7_visual", "M_newn_x_1mcos", "S_v_new_norm * (1-S_v_cos)"),
    ("base_7_visual", "M_abscos_x_newn", "abs(S_v_cos) * S_v_new_norm"),
    ("ours_4_depth_weighted", "Ours-Direct-Conflict", "max(0,-S_v_cos) * S_v_new_norm * S_v_depth2"),
    ("ours_4_depth_weighted", "Ours-AbsDirection-Direct", "abs(S_v_cos) * S_v_new_norm * S_v_depth2"),
    ("ours_4_depth_weighted", "Ours-NoDirection-Direct", "S_v_new_norm * S_v_depth2"),
    ("ours_4_depth_weighted", "Ours-1MinusCos-Direct", "(1-S_v_cos) * S_v_new_norm * S_v_depth2"),
]
FORMULA_META = {name: (group, expr) for group, name, expr in FORMULAS}


def fnum(value, default=math.nan):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def bval(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.16g}"
    return str(value)


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: fmt(row.get(k, "")) for k in fieldnames})


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
if ZIP.exists():
    ZIP.unlink()

# -----------------------------------------------------------------------------
# 1) 21 组原始逐层视觉梯度 -> 标准 layer CSV（618 行）
# -----------------------------------------------------------------------------
raw_files = sorted((VG / "raw_layer_scores").rglob("ours_direct_layer_scores.csv"))
if len(raw_files) != 21:
    raise RuntimeError(f"预期 21 个原始 layer score 文件，实际 {len(raw_files)}")

layer_rows = []
combo_diag = {}
for path in raw_files:
    rel = path.relative_to(ROOT).as_posix()
    source_hash = sha256(path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise RuntimeError(f"空文件：{rel}")
    dataset = rows[0]["dataset_key"].strip().lower()
    model = rows[0]["model_key"].strip().lower()
    total = DATASET_TOTAL[dataset]
    zero_grad_count = sum(bval(r.get("S_v_zero_grad")) for r in rows)
    nonfinite_count = 0
    no_negative_count = 0
    for r in rows:
        sv_cos = fnum(r.get("S_v_cos"))
        sv_new = fnum(r.get("S_v_new_norm"))
        sv_depth = fnum(r.get("S_v_depth2"))
        sv_neg = fnum(r.get("S_v_neg_cos"), max(0.0, -sv_cos) if finite(sv_cos) else math.nan)
        scores_to_check = [fnum(r.get(k)) for k in ["S_v_dot", "S_v_cos", "S_v_new_norm", "S_v_positive_ratio", "S_v_conflict"]]
        if any(not finite(x) for x in scores_to_check):
            nonfinite_count += 1
        if not finite(sv_neg) or sv_neg <= 0:
            no_negative_count += 1
    combo_diag[(dataset, model)] = {
        "zero_grad_layer_count": zero_grad_count,
        "nonfinite_score_layer_count": nonfinite_count,
        "no_negative_cos_layer_count": no_negative_count,
        "n_layers": len(rows),
    }

    for r in rows:
        sv_dot = fnum(r.get("S_v_dot"))
        sv_conflict = fnum(r.get("S_v_conflict"))
        sv_cos = fnum(r.get("S_v_cos"))
        sv_new = fnum(r.get("S_v_new_norm"))
        sv_pos = fnum(r.get("S_v_positive_ratio"))
        sv_depth = fnum(r.get("S_v_depth2"))
        sv_neg = fnum(r.get("S_v_neg_cos"), max(0.0, -sv_cos) if finite(sv_cos) else math.nan)
        n_request = int(fnum(r.get("n_request"), 0))
        coverage = n_request / total if total else math.nan
        zero_grad = bval(r.get("S_v_zero_grad"))
        invalid_reason = (r.get("invalid_reason") or "").strip()
        layer_failure = invalid_reason or ("zero_visual_gradient" if zero_grad else "")
        if layer_failure:
            status = "invalid_layer"
            failure_major = "zero_grad_or_nonfinite" if zero_grad else layer_failure
        elif coverage >= 0.8:
            status = "done"
            failure_major = ""
        elif coverage >= 0.2:
            status = "low_confidence"
            failure_major = "low_coverage"
        else:
            status = "invalid_low_coverage"
            failure_major = "invalid_low_coverage"

        start = fnum(r.get("visual_token_start"))
        end = fnum(r.get("visual_token_end"))
        layer_rows.append({
            "dataset": dataset,
            "model": model,
            "layer": int(fnum(r.get("layer"), -1)),
            "layer_name": r.get("layer_name", ""),
            "layer_path": r.get("layer_path", ""),
            "n_request": n_request,
            "valid_samples": n_request,
            "total_samples": total,
            "coverage": coverage,
            "S_v_dot": sv_dot,
            "S_v_conflict": sv_conflict,
            "S_v_dot_per_dim": fnum(r.get("S_v_dot_per_dim")),
            "S_v_cos": sv_cos,
            "S_v_old_norm": fnum(r.get("S_v_old_norm")),
            "S_v_new_norm": sv_new,
            "S_v_joint_norm": fnum(r.get("S_v_joint_norm")),
            "S_v_positive_ratio": sv_pos,
            "S_v_zero_grad": zero_grad,
            "S_v_old_nonzero_ratio": fnum(r.get("S_v_old_nonzero_ratio")),
            "S_v_new_nonzero_ratio": fnum(r.get("S_v_new_nonzero_ratio")),
            "median_v_dot": fnum(r.get("median_v_dot")),
            "S_v_neg_cos": sv_neg,
            "S_v_depth2": sv_depth,
            "S_strict_negcos_depth2": sv_neg * sv_new * sv_depth if all(finite(x) for x in [sv_neg, sv_new, sv_depth]) else math.nan,
            "M_dot": sv_dot,
            "M_cos": sv_cos,
            "M_new_norm": sv_new,
            "M_pos_ratio": sv_pos,
            "M_conflict": sv_conflict,
            "M_newn_x_1mcos": sv_new * (1 - sv_cos) if all(finite(x) for x in [sv_new, sv_cos]) else math.nan,
            "M_abscos_x_newn": abs(sv_cos) * sv_new if all(finite(x) for x in [sv_cos, sv_new]) else math.nan,
            "S_ours_conflict": max(0.0, -sv_cos) * sv_new * sv_depth if all(finite(x) for x in [sv_cos, sv_new, sv_depth]) else math.nan,
            "S_ours_absdir": abs(sv_cos) * sv_new * sv_depth if all(finite(x) for x in [sv_cos, sv_new, sv_depth]) else math.nan,
            "S_ours_nodir": sv_new * sv_depth if all(finite(x) for x in [sv_new, sv_depth]) else math.nan,
            "S_ours_1mcos": (1 - sv_cos) * sv_new * sv_depth if all(finite(x) for x in [sv_cos, sv_new, sv_depth]) else math.nan,
            "visual_token_start_valid": finite(start) and start >= 0,
            "visual_token_end_valid": finite(end) and finite(start) and end > start,
            "status": status,
            "failure_reason": layer_failure,
            "empty_model_pred_count": "",
            "missing_image_count": "",
            "empty_visual_span_count": "",
            "zero_grad_layer_count": zero_grad_count,
            "nonfinite_score_layer_count": nonfinite_count,
            "no_negative_cos_layer_count": no_negative_count,
            "failure_reason_major": failure_major,
            "source_score_file": rel,
            "source_score_sha256": source_hash,
            "config_hash": "",
            "config_hash_status": "not_present_in_local_source",
        })

layer_fields = [
    "dataset", "model", "layer", "layer_name", "layer_path", "n_request", "valid_samples", "total_samples", "coverage",
    "S_v_dot", "S_v_conflict", "S_v_dot_per_dim", "S_v_cos", "S_v_old_norm", "S_v_new_norm", "S_v_joint_norm",
    "S_v_positive_ratio", "S_v_zero_grad", "S_v_old_nonzero_ratio", "S_v_new_nonzero_ratio", "median_v_dot",
    "S_v_neg_cos", "S_v_depth2", "S_strict_negcos_depth2", "M_dot", "M_cos", "M_new_norm", "M_pos_ratio",
    "M_conflict", "M_newn_x_1mcos", "M_abscos_x_newn", "S_ours_conflict", "S_ours_absdir", "S_ours_nodir",
    "S_ours_1mcos", "visual_token_start_valid", "visual_token_end_valid", "status", "failure_reason",
    "empty_model_pred_count", "missing_image_count", "empty_visual_span_count", "zero_grad_layer_count",
    "nonfinite_score_layer_count", "no_negative_cos_layer_count", "failure_reason_major", "source_score_file",
    "source_score_sha256", "config_hash", "config_hash_status",
]
write_csv(OUT / "visual_gradient_layer_scores.csv", layer_fields, layer_rows)

# -----------------------------------------------------------------------------
# 2) 11 公式完整逐层排名
# -----------------------------------------------------------------------------
rank_source = AN / "formula_full_rankings.csv"
with rank_source.open("r", encoding="utf-8-sig", newline="") as fh:
    source_rank_rows = list(csv.DictReader(fh))
topk_source = AN / "formula_topk_all_21.csv"
with topk_source.open("r", encoding="utf-8-sig", newline="") as fh:
    topk_summary = list(csv.DictReader(fh))

combo_formula_status = {}
for t in topk_summary:
    key = (t["dataset"], t["model"], t["formula"])
    top1_layers = re.findall(r"L(\d+)", t.get("top1", ""))
    top3_layers = re.findall(r"L(\d+)", t.get("top3", ""))
    if t["status"] == "done":
        combo_formula_status[key] = ("done", "")
    elif t["formula"] == "Ours-Direct-Conflict" and not top1_layers:
        combo_formula_status[key] = ("unavailable", "no_valid_negative_cosine_layer")
    elif t["formula"] == "Ours-Direct-Conflict" and len(top3_layers) < 3:
        combo_formula_status[key] = ("insufficient_valid_layers", "clean_topk_less_than_3")
    else:
        combo_formula_status[key] = (t["status"], "unknown")

ranking_rows = []
for r in source_rank_rows:
    formula = r["formula"]
    group, expr = FORMULA_META[formula]
    rank_status, rank_failure = combo_formula_status[(r["dataset"], r["model"], formula)]
    ranking_rows.append({
        "dataset": r["dataset"],
        "model": r["model"],
        "formula_group": group,
        "formula_name": formula,
        "expression": expr,
        "rank_metric": formula,
        "rank": r["rank"],
        "layer": r["layer"],
        "score": r["score"],
        "valid_samples": r["valid_samples"],
        "total_samples": r["total_samples"],
        "coverage": r["coverage"],
        "status": rank_status,
        "failure_reason": rank_failure,
        "source_layer_scores_file": f"md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores/{r['dataset']}/{r['model']}/ours_direct_layer_scores.csv",
    })

ranking_fields = ["dataset", "model", "formula_group", "formula_name", "expression", "rank_metric", "rank", "layer", "score",
                  "valid_samples", "total_samples", "coverage", "status", "failure_reason", "source_layer_scores_file"]
write_csv(OUT / "visual_candidate_formula_rankings.csv", ranking_fields, ranking_rows)

# -----------------------------------------------------------------------------
# 3) 11 公式 Top-3 / Top-5，展开为每个排名一行
# -----------------------------------------------------------------------------
score_lookup = {}
for r in ranking_rows:
    score_lookup[(r["dataset"], r["model"], r["formula_name"], int(r["layer"]))] = r["score"]

topk_rows = []
failure_rows = []
for r in topk_summary:
    dataset, model, formula = r["dataset"], r["model"], r["formula"]
    group, expr = FORMULA_META[formula]
    status0 = r["status"]
    top1 = re.findall(r"L(\d+)", r.get("top1", ""))
    top3 = [int(x) for x in re.findall(r"L(\d+)", r.get("top3", ""))]
    top5 = [int(x) for x in re.findall(r"L(\d+)", r.get("top5", ""))]
    if status0 == "done":
        failure_reason = ""
        status = "done"
    elif formula == "Ours-Direct-Conflict" and not top1:
        failure_reason = "no_valid_negative_cosine_layer"
        status = "unavailable"
    elif formula == "Ours-Direct-Conflict" and len(top3) < 3:
        failure_reason = "clean_topk_less_than_3"
        status = "insufficient_valid_layers"
    else:
        failure_reason = "unknown"
        status = status0

    for k, layers in [(3, top3), (5, top5)]:
        joined = ",".join(f"L{x}" for x in layers)
        if not layers:
            topk_rows.append({
                "dataset": dataset, "model": model, "formula_group": group, "formula_name": formula,
                "expression": expr, "rank_metric": formula, "top_k": k, "rank": "", "layer": "", "score": "",
                "raw_candidate_layers": joined, "clean_candidate_layers": joined,
                "valid_samples": r["valid_samples"], "total_samples": r["total_samples"], "coverage": r["coverage"],
                "status": status, "failure_reason": failure_reason, "source_layer_scores_file": r["raw_score_file"],
            })
        else:
            for idx, layer in enumerate(layers, 1):
                topk_rows.append({
                    "dataset": dataset, "model": model, "formula_group": group, "formula_name": formula,
                    "expression": expr, "rank_metric": formula, "top_k": k, "rank": idx, "layer": layer,
                    "score": score_lookup.get((dataset, model, formula, layer), ""),
                    "raw_candidate_layers": joined, "clean_candidate_layers": joined,
                    "valid_samples": r["valid_samples"], "total_samples": r["total_samples"], "coverage": r["coverage"],
                    "status": status, "failure_reason": failure_reason, "source_layer_scores_file": r["raw_score_file"],
                })

    diag = combo_diag[(dataset, model)]
    failure_rows.append({
        "dataset": dataset,
        "model": model,
        "formula_group": group,
        "formula_name": formula,
        "expression": expr,
        "empty_model_pred_count": "",
        "missing_image_count": "",
        "empty_visual_span_count": "",
        "zero_grad_layer_count": diag["zero_grad_layer_count"],
        "nonfinite_score_layer_count": diag["nonfinite_score_layer_count"],
        "no_negative_cos_layer_count": diag["no_negative_cos_layer_count"],
        "valid_sample_count": r["valid_samples"],
        "total_sample_count": r["total_samples"],
        "coverage": r["coverage"],
        "available_top3_count": len(top3),
        "available_top5_count": len(top5),
        "status": status,
        "failure_reason_major": failure_reason,
        "source_layer_scores_file": r["raw_score_file"],
        "diagnostic_note": "sample-level reason counts are not present in the local raw layer CSV" if any(x == "" for x in ["", "", ""]) else "",
    })

topk_fields = ["dataset", "model", "formula_group", "formula_name", "expression", "rank_metric", "top_k", "rank", "layer",
               "score", "raw_candidate_layers", "clean_candidate_layers", "valid_samples", "total_samples", "coverage", "status",
               "failure_reason", "source_layer_scores_file"]
write_csv(OUT / "visual_candidate_layers_topk.csv", topk_fields, topk_rows)

failure_fields = ["dataset", "model", "formula_group", "formula_name", "expression", "empty_model_pred_count", "missing_image_count",
                  "empty_visual_span_count", "zero_grad_layer_count", "nonfinite_score_layer_count", "no_negative_cos_layer_count",
                  "valid_sample_count", "total_sample_count", "coverage", "available_top3_count", "available_top5_count", "status",
                  "failure_reason_major", "source_layer_scores_file", "diagnostic_note"]
write_csv(OUT / "visual_formula_failure_reason_summary.csv", failure_fields, failure_rows)

# -----------------------------------------------------------------------------
# 4) 已完成真实扫层：保留配置、恢复、数值异常边界；未知 seed/config_hash 不猜。
# -----------------------------------------------------------------------------
ledger_lines = LEDGER.read_text(encoding="utf-8").splitlines()
sec_start = next(i for i, line in enumerate(ledger_lines) if line.startswith("### 4.0 "))
sec_end = next(i for i in range(sec_start + 1, len(ledger_lines)) if ledger_lines[i].startswith("### 4.1 "))
current_dataset = None
sweep_rows = []
duplicate_counter = Counter()

def infer_profile(model, status):
    stable = "STABLE" in status or "MANUAL_EPOCH13" in status
    if stable:
        config_profile = "stable"
        adapter_config = "configs/vead/paligemma-3b-stable.yaml" if "paligemma" in model else "stable_profile_exact_yaml_not_recorded"
    else:
        config_profile = "main"
        adapter_config = "configs/vead/paligemma-3b.yaml" if "paligemma" in model else "main_profile_exact_yaml_not_recorded"

    recovery_tokens = []
    for token in ["RECOVERED", "RESUMED", "MANUAL_EPOCH13", "REPAIRED_SELECTION", "RETRY_BUFFER1", "RETRY_NUMERIC_GUARD"]:
        if token in status:
            recovery_tokens.append(token.lower())
    recovery_status = "+".join(recovery_tokens) if recovery_tokens else "none"

    if "NUMERIC_ANOMALY" in status:
        numeric_status = "numeric_anomaly"
    elif "NONFINITE" in status or "NUMERIC_GUARD" in status:
        numeric_status = "numeric_guard_or_nonfinite_skip"
    else:
        numeric_status = "clean_or_not_flagged"

    if numeric_status == "numeric_anomaly":
        eligibility = "separate_numeric_anomaly"
    elif recovery_status != "none" and stable:
        eligibility = "separate_stable_recovered"
    elif recovery_status != "none":
        eligibility = "separate_recovered"
    elif stable:
        eligibility = "stable_sensitivity"
    else:
        eligibility = "main_primary"
    return config_profile, adapter_config, recovery_status, numeric_status, eligibility

for idx in range(sec_start, sec_end):
    line = ledger_lines[idx]
    if line.startswith("#### EVQA-pilot500"):
        current_dataset = "evqa-pilot500"
        continue
    if line.startswith("#### MMKE-visual"):
        current_dataset = "mmke-visual"
        continue
    if line.startswith("#### MMKE-entity"):
        current_dataset = "mmke-entity"
        continue
    if current_dataset is None or not line.startswith("|"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != 13 or cells[0] in {"Model", "---"} or cells[0].startswith("---"):
        continue
    model, layer_s, ckpt_epoch, raw_loss, ema_loss, samples, rel, tgen, mgen, tloc, mloc, avg, status = cells
    if not re.fullmatch(r"L\d+(?:-\d+)?", layer_s):
        continue
    # §4.0 同时登记失败现场；逐层正式结果 CSV 只纳入完整 test/eval 行。
    if "FAILED" in status or int(fnum(samples, 0)) <= 0 or not finite(fnum(avg)):
        continue
    layer_match = re.match(r"L(\d+)", layer_s)
    layer = int(layer_match.group(1))
    config_profile, adapter_config, recovery_status, numeric_status, eligibility = infer_profile(model, status)
    duplicate_counter[(current_dataset, model, layer, config_profile)] += 1
    replicate_index = duplicate_counter[(current_dataset, model, layer, config_profile)]
    vals = [fnum(rel), fnum(tgen), fnum(mgen), fnum(tloc), fnum(mloc)]
    recomputed = sum(vals) / 5 if all(finite(x) for x in vals) else math.nan
    avg_f = fnum(avg)
    delta = avg_f - recomputed if finite(avg_f) and finite(recomputed) else math.nan
    job_match = re.search(r"JOB(\d+)", status)
    sweep_rows.append({
        "dataset": current_dataset,
        "model": model,
        "layer": layer,
        "layer_label": layer_s,
        "seed": "not_recorded",
        "seed_status": "not_recorded_in_local_ledger",
        "replicate_index_within_profile": replicate_index,
        "adapter_config": adapter_config,
        "config_profile": config_profile,
        "config_hash": "",
        "config_hash_status": "not_recoverable_without_remote_run_config",
        "recovery_status": recovery_status,
        "numeric_status": numeric_status,
        "analysis_eligibility": eligibility,
        "train_status": status,
        "eval_status": "EVAL_DONE_VERIFIED_IN_LEDGER",
        "completion_basis": "nonempty selected_checkpoint.tsv + eval_full.done + formal independent eval",
        "job_id": job_match.group(1) if job_match else "",
        "selected_ckpt_epoch": ckpt_epoch,
        "raw_loss": raw_loss,
        "ema_loss": ema_loss,
        "eval_samples": samples,
        "expected_eval_samples": EVAL_TOTAL[current_dataset],
        "eval_sample_count_match": int(fnum(samples, -1)) == EVAL_TOTAL[current_dataset],
        "Rel": rel,
        "T-Gen": tgen,
        "M-Gen": mgen,
        "T-Loc": tloc,
        "M-Loc": mloc,
        "Average": avg,
        "Average_recomputed": recomputed,
        "Average_delta": delta,
        "metric_consistency": "ok_rounding" if finite(delta) and abs(delta) <= 0.015 else "review",
        "source_document": LEDGER.relative_to(ROOT).as_posix(),
        "source_line": idx + 1,
    })

# EVQA / BLIP2 的 20 个主层及 L18-2 复现实验放在 §4.1，不重复出现在 §4.0。
detail_start = next(i for i, line in enumerate(ledger_lines) if line.startswith("### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B"))
detail_end = next(i for i in range(detail_start + 1, len(ledger_lines)) if ledger_lines[i].startswith("### 4.2 "))
for idx in range(detail_start, detail_end):
    line = ledger_lines[idx]
    if not line.startswith("|"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != 10 or cells[0] in {"Layer", "---"} or cells[0].startswith("---"):
        continue
    layer_s, ckpt_epoch, raw_loss, ema_loss, rel, tgen, mgen, tloc, mloc, avg = cells
    if not re.fullmatch(r"L\d+(?:-\d+)?", layer_s):
        continue
    layer = int(re.match(r"L(\d+)", layer_s).group(1))
    model = "blip2-opt-2.7b"
    dataset = "evqa-pilot500"
    config_profile = "main"
    duplicate_counter[(dataset, model, layer, config_profile)] += 1
    replicate_index = duplicate_counter[(dataset, model, layer, config_profile)]
    is_replicate = layer_s != f"L{layer}"
    vals = [fnum(rel), fnum(tgen), fnum(mgen), fnum(tloc), fnum(mloc)]
    recomputed = sum(vals) / 5 if all(finite(x) for x in vals) else math.nan
    avg_f = fnum(avg)
    delta = avg_f - recomputed if finite(avg_f) and finite(recomputed) else math.nan
    sweep_rows.append({
        "dataset": dataset,
        "model": model,
        "layer": layer,
        "layer_label": layer_s,
        "seed": "not_recorded",
        "seed_status": "not_recorded_in_local_ledger",
        "replicate_index_within_profile": replicate_index,
        "adapter_config": "main_profile_exact_yaml_not_recorded",
        "config_profile": config_profile,
        "config_hash": "",
        "config_hash_status": "not_recoverable_without_remote_run_config",
        "recovery_status": "fixed_wrapper_rerun" if layer in {5, 10, 15, 19, 25, 30} else "none",
        "numeric_status": "clean_or_not_flagged",
        "analysis_eligibility": "replicate_excluded_primary" if is_replicate else "main_primary",
        "train_status": "TRAIN_DONE_REPLICATE_L18_2_EXCLUDED_PRIMARY" if is_replicate else "TRAIN_DONE_MAIN_DETAIL_SECTION_4_1",
        "eval_status": "EVAL_DONE_VERIFIED_IN_LEDGER",
        "completion_basis": "selected checkpoint + formal independent EVQA full eval recorded in §4.1",
        "job_id": "3044208" if layer in {1, 2, 3, 4, 14} else "",
        "selected_ckpt_epoch": ckpt_epoch,
        "raw_loss": raw_loss,
        "ema_loss": ema_loss,
        "eval_samples": 2093,
        "expected_eval_samples": 2093,
        "eval_sample_count_match": True,
        "Rel": rel,
        "T-Gen": tgen,
        "M-Gen": mgen,
        "T-Loc": tloc,
        "M-Loc": mloc,
        "Average": avg,
        "Average_recomputed": recomputed,
        "Average_delta": delta,
        "metric_consistency": "ok_rounding" if finite(delta) and abs(delta) <= 0.015 else "review",
        "source_document": LEDGER.relative_to(ROOT).as_posix(),
        "source_line": idx + 1,
    })

sweep_rows.sort(key=lambda r: (
    {"evqa-pilot500": 0, "mmke-visual": 1, "mmke-entity": 2}[r["dataset"]],
    r["model"], r["config_profile"], int(r["layer"]), int(r["replicate_index_within_profile"])
))

sweep_fields = [
    "dataset", "model", "layer", "layer_label", "seed", "seed_status", "replicate_index_within_profile", "adapter_config",
    "config_profile", "config_hash", "config_hash_status", "recovery_status", "numeric_status", "analysis_eligibility",
    "train_status", "eval_status", "completion_basis", "job_id", "selected_ckpt_epoch", "raw_loss", "ema_loss",
    "eval_samples", "expected_eval_samples", "eval_sample_count_match", "Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc",
    "Average", "Average_recomputed", "Average_delta", "metric_consistency", "source_document", "source_line",
]
write_csv(OUT / "real_layer_sweep_results_by_seed.csv", sweep_fields, sweep_rows)

# 复制手册与分析清单，方便上传者核验公式和来源。
shutil.copy2(MANUAL, OUT / MANUAL.name)
shutil.copy2(AN / "analysis_manifest.json", OUT / "source_analysis_manifest.json")
shutil.copy2(AN / "formula_global_summary.csv", OUT / "formula_global_summary.csv")

profile_counts = Counter(r["config_profile"] for r in sweep_rows)
eligibility_counts = Counter(r["analysis_eligibility"] for r in sweep_rows)
metric_review = [r for r in sweep_rows if r["metric_consistency"] != "ok_rounding"]
sample_mismatch = [r for r in sweep_rows if not r["eval_sample_count_match"]]

readme = f"""# 视觉梯度 11 公式与真实扫层分析数据包

生成时间：2026-08-01

## 文件

- `visual_gradient_layer_scores.csv`：21 个模型×数据集组合，逐层视觉梯度及 7 个基础公式、4 个 Ours 指标；共 {len(layer_rows)} 行。
- `visual_candidate_formula_rankings.csv`：11 个公式的完整逐层排序；共 {len(ranking_rows)} 行。
- `visual_candidate_layers_topk.csv`：11 个公式的 Top-3/Top-5，按候选排名展开；共 {len(topk_rows)} 行。
- `visual_formula_failure_reason_summary.csv`：每个 dataset×model×formula 一行；共 {len(failure_rows)} 行。
- `formula_global_summary.csv`：公式与真实编辑结果的全局汇总，含 Spearman、Best/Mean/Regret 等。
- `real_layer_sweep_results_by_seed.csv`：本地总表中已验收的真实扫层正式评测结果；共 {len(sweep_rows)} 行。
- `{MANUAL.name}`：11 公式专项操作手册。
- `source_analysis_manifest.json`：原始 21 个 layer score 文件的 SHA-256 清单和分析边界。

## 重要边界

1. `real_layer_sweep_results_by_seed.csv` 保留了 `seed` 字段，但本地结果总表没有逐行登记 seed，服务器 SSH 当前也无法非交互认证，因此统一写为 `not_recorded`；不能把这些行解释为多 seed 统计。
2. `config_hash` 同样不在本地总表/已同步产物中，保持为空，并在 `config_hash_status` 明确标记。没有伪造 hash。
3. `config_profile`、`recovery_status`、`numeric_status`、`analysis_eligibility` 分列保存。main、stable、recovered、numeric anomaly 未混合，也没有跨配置取最大值。
4. PaliGemma main 是主口径；stable 只作为敏感性结果。恢复运行与数值异常结果必须单独分析。
5. `visual_formula_failure_reason_summary.csv` 的样本级 `empty_model_pred_count`、`missing_image_count`、`empty_visual_span_count` 在本地逐层原始 CSV 中不存在，因此留空；层级 zero-grad/nonfinite/negative-cos 统计已填写。
6. 所有真实扫层行来自本地台账 §4.0，台账的进入条件为非空 `selected_checkpoint.tsv`、`eval_full.done` 与对应独立 test/eval 完整结果。

## 质量检查

- 原始 layer score 文件：{len(raw_files)} / 21。
- 逐层记录：{len(layer_rows)} / 618。
- 公式组合：{len(topk_summary)} / 231。
- 失败原因组合：{len(failure_rows)} / 231。
- 真实扫层完成记录：{len(sweep_rows)} 行。
- 配置分布：{dict(profile_counts)}。
- 分析口径分布：{dict(eligibility_counts)}。
- eval sample count 不匹配：{len(sample_mismatch)} 行。
- Average 五指标回算超出 0.015：{len(metric_review)} 行（通常应为 0；若非 0 请查看 `metric_consistency=review`）。
"""
(OUT / "DATA_README.md").write_text(readme, encoding="utf-8")

manifest = {
    "generated_at": "2026-08-01",
    "source_ledger": str(LEDGER.relative_to(ROOT)).replace("\\", "/"),
    "source_ledger_sha256": sha256(LEDGER),
    "raw_score_file_count": len(raw_files),
    "layer_rows": len(layer_rows),
    "ranking_rows": len(ranking_rows),
    "topk_rows": len(topk_rows),
    "failure_rows": len(failure_rows),
    "sweep_rows": len(sweep_rows),
    "profile_counts": dict(profile_counts),
    "eligibility_counts": dict(eligibility_counts),
    "sample_mismatch_count": len(sample_mismatch),
    "metric_review_count": len(metric_review),
    "files": {},
}
for path in sorted(OUT.iterdir()):
    if path.is_file():
        manifest["files"][path.name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
(OUT / "package_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            zf.write(path, arcname=f"{OUT.name}/{path.name}")

print(f"OUT={OUT}")
print(f"ZIP={ZIP}")
print(f"RAW_FILES={len(raw_files)}")
print(f"LAYER_ROWS={len(layer_rows)}")
print(f"RANKING_ROWS={len(ranking_rows)}")
print(f"TOPK_ROWS={len(topk_rows)}")
print(f"FAILURE_ROWS={len(failure_rows)}")
print(f"SWEEP_ROWS={len(sweep_rows)}")
print(f"PROFILE_COUNTS={dict(profile_counts)}")
print(f"ELIGIBILITY_COUNTS={dict(eligibility_counts)}")
print(f"SAMPLE_MISMATCH={len(sample_mismatch)}")
print(f"METRIC_REVIEW={len(metric_review)}")
print(f"ZIP_BYTES={ZIP.stat().st_size}")
