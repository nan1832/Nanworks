"""Recompute fixed formula ablations from archived gradients and audited outcomes.

No training, inference, source-ledger writes, or selection of a new main formula.
Run from any directory. Outputs are restricted to this script's directory.
"""
from pathlib import Path
from collections import defaultdict
from statistics import mean
from datetime import datetime
import csv
import hashlib
import json
import math
import sys
import warnings
from scipy.stats import spearmanr, kendalltau

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PREV = ROOT / "outputs/visual_lga_vs_main_20260925"
RAW = ROOT / "md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores"
TOTAL = {"evqa-pilot500": 500, "mmke-visual": 214, "mmke-entity": 636}
MAIN = "main_abs_cos_new_norm"
NORMS = "new_norm_only"
NAMES = {
    MAIN: "主公式：绝对余弦×新梯度范数",
    NORMS: "去方向项：仅新梯度范数",
    "abs_cos_only": "去幅度项：仅绝对余弦",
    "signed_cos_new_norm": "保留方向符号：余弦×新梯度范数",
    "negative_cos_new_norm": "仅负方向：max(0,−余弦)×新梯度范数",
    "one_minus_cos_new_norm": "方向替代：(1−余弦)×新梯度范数",
    "main_depth2": "主公式增加深度平方",
    "new_norm_depth2": "新梯度范数×深度平方",
    "visual_lga_dot": "视觉LGA：样本梯度内积均值",
}
sources = {}


def read(path):
    b = path.read_bytes()
    sources[str(path)] = hashlib.sha256(b).hexdigest()
    return b.decode("utf-8-sig")


def rcsv(path):
    return list(csv.DictReader(read(path).splitlines()))


def writecsv(name, rows):
    if not rows:
        return
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def layers(seq):
    return ",".join(f"L{x}" for x in seq)


def safe_corr(x, y, fn):
    if len(x) < 5:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        v = float(fn(x, y).statistic)
    return v if math.isfinite(v) else None


rankings, scores, meta = {}, {}, {}
candidate_rows, score_rows = [], []
raw_paths = sorted(RAW.glob("*/*/ours_direct_layer_scores.csv"))
assert len(raw_paths) == 21
for path in raw_paths:
    ds, model = path.parts[-3:-1]
    rows = rcsv(path)
    counts = {int(float(r["n_request"])) for r in rows}
    assert len(counts) == 1
    count = counts.pop()
    length = max(int(r["layer"]) for r in rows) + 1
    meta[ds, model] = dict(valid_samples=count, total_samples=TOTAL[ds], coverage=count / TOTAL[ds])
    group = defaultdict(dict)
    for r in rows:
        if r["S_v_zero_grad"].lower() == "true" or r["invalid_reason"].strip():
            continue
        if not r["visual_token_start"].strip() or not r["visual_token_end"].strip():
            continue
        dot, cos, norm = [float(r[c]) for c in ("S_v_dot", "S_v_cos", "S_v_new_norm")]
        if not all(math.isfinite(x) for x in (dot, cos, norm)):
            continue
        layer = int(r["layer"])
        depth2 = ((layer + 1) / length) ** 2
        assert abs(float(r["S_v_depth2"]) - depth2) < 1e-8
        values = {
            MAIN: abs(cos) * norm,
            NORMS: norm,
            "abs_cos_only": abs(cos),
            "signed_cos_new_norm": cos * norm,
            "negative_cos_new_norm": max(0.0, -cos) * norm,
            "one_minus_cos_new_norm": (1.0 - cos) * norm,
            "main_depth2": abs(cos) * norm * depth2,
            "new_norm_depth2": norm * depth2,
            "visual_lga_dot": dot,
        }
        for method, value in values.items():
            # Zero is not a qualifying negative-direction candidate. Keep its
            # mathematical value for correlations on identical measured layers.
            group[method][layer] = value
    for method in NAMES:
        key = ds, model, method
        scores[key] = group[method]
        eligible = [(l, s) for l, s in group[method].items()
                    if method != "negative_cos_new_norm" or s > 0]
        ranking = sorted(eligible, key=lambda x: (-x[1], x[0]))
        rankings[key] = [l for l, _ in ranking]
        rankmap = {l: i for i, (l, _) in enumerate(ranking, 1)}
        candidate_rows.append(dict(dataset=ds, model=model, method=method, **meta[ds, model],
                                   qualifying_layers=len(ranking), top1=layers(rankings[key][:1]),
                                   top3=layers(rankings[key][:3]), top5=layers(rankings[key][:5])))
        for l, value in sorted(group[method].items()):
            score_rows.append(dict(dataset=ds, model=model, method=method, layer=l,
                                   score=value, rank=rankmap.get(l, "")))

# Locked local audit from the immediately preceding calculation. Do not reselect
# checkpoints or reinterpret an unfinished/diagnostic layer as a successful run.
outcomes = rcsv(PREV / "verified_outcomes_with_flags.csv")
assert len({(r["dataset"], r["model"], r["layer"]) for r in outcomes}) == len(outcomes)
previous_candidates = rcsv(PREV / "candidate_topk_21x2.csv")
for r in previous_candidates:
    method = MAIN if r["formula"] == "M_abscos_x_newn" else "visual_lga_dot"
    for k in (1, 3, 5):
        assert r[f"top{k}"] == layers(rankings[r["dataset"], r["model"], method][:k])

metric_rows, metric_map, corrs = [], {}, []
for profile in ("clean", "historical"):
    for ds, model in sorted(meta):
        measured = {int(r["layer"]): float(r["average"]) for r in outcomes
                    if (r["dataset"], r["model"]) == (ds, model) and not r[f"{profile}_exclusion"]}
        reference = max(measured.values()) if measured else None
        for method in NAMES:
            key = ds, model, method
            common = sorted(set(measured) & set(scores[key]))
            xs, ys = [scores[key][l] for l in common], [measured[l] for l in common]
            corrs.append(dict(profile=profile, dataset=ds, model=model, method=method,
                              coverage=meta[ds, model]["coverage"], measured_layer_count=len(common),
                              spearman=safe_corr(xs, ys, spearmanr), kendall=safe_corr(xs, ys, kendalltau)))
            for k in (1, 3, 5):
                chosen = rankings[key][:k]
                missing = [l for l in chosen if l not in measured]
                complete = len(chosen) == k and not missing
                vals = [measured[l] for l in chosen if l in measured]
                best = max(vals) if complete else None
                row = dict(profile=profile, dataset=ds, model=model, method=method, k=k,
                           coverage=meta[ds, model]["coverage"], candidates=layers(chosen),
                           complete=complete, missing_or_excluded=layers(missing),
                           best=best, mean=mean(vals) if complete else None,
                           regret=reference-best if complete else None,
                           hit=int(abs(reference-best) < 1e-9) if complete else None,
                           measured_reference=reference, measured_layer_count=len(measured))
                metric_rows.append(row)
                metric_map[profile, ds, model, method, k] = row

pairs, summaries, missing = [], [], []
for profile in ("clean", "historical"):
    for k in (1, 3, 5):
        for method in NAMES:
            if method == MAIN:
                continue
            included = []
            for ds, model in sorted(meta):
                a = metric_map[profile, ds, model, MAIN, k]
                b = metric_map[profile, ds, model, method, k]
                eligible = a["complete"] and b["complete"] and a["coverage"] >= .8
                ar, br = rankings[ds, model, MAIN][:k], rankings[ds, model, method][:k]
                row = dict(profile=profile, dataset=ds, model=model, comparator=method, k=k,
                           eligible=eligible, coverage=a["coverage"], main_candidates=layers(ar),
                           comparator_candidates=layers(br), same_order=ar == br,
                           same_set=set(ar) == set(br), main_missing=a["missing_or_excluded"],
                           comparator_missing=b["missing_or_excluded"])
                for field in ("best", "mean", "regret", "hit"):
                    row[f"main_{field}"] = a[field] if eligible else None
                    row[f"comparator_{field}"] = b[field] if eligible else None
                    row[f"delta_{field}"] = a[field]-b[field] if eligible else None
                pairs.append(row)
                if eligible:
                    included.append(row)
                if profile == "clean" and k == 3 and method == NORMS and not eligible:
                    required = sorted(set(ar) | set(br))
                    good = {int(r["layer"]) for r in outcomes if (r["dataset"], r["model"]) == (ds, model)
                            and not r["clean_exclusion"]}
                    for l in required:
                        if l in good:
                            continue
                        record = next((r for r in outcomes if (r["dataset"], r["model"], int(r["layer"])) == (ds, model, l)), None)
                        missing.append(dict(dataset=ds, model=model, layer=l,
                                            required_by=";".join(m for m, ls in ((MAIN, ar), (NORMS, br)) if l in ls),
                                            same_candidate_set=set(ar) == set(br), coverage=a["coverage"],
                                            reason=record["clean_exclusion"] if record else "not_in_locked_local_verified_outcomes"))
            s = dict(profile=profile, k=k, comparator=method, n=len(included),
                     main_wins=sum(r["delta_best"] > 1e-9 for r in included),
                     ties=sum(abs(r["delta_best"]) <= 1e-9 for r in included),
                     main_losses=sum(r["delta_best"] < -1e-9 for r in included),
                     different_candidate_sets=sum(not r["same_set"] for r in included))
            for field in ("best", "mean", "regret", "hit"):
                for side in ("main", "comparator", "delta"):
                    s[f"{side}_{field}"] = mean(r[f"{side}_{field}"] for r in included) if included else None
            summaries.append(s)

# Correlation comparison is also paired, including only combinations with finite
# statistics for both methods on exactly the same eligible measured layer pool.
cmap = {(r["profile"], r["dataset"], r["model"], r["method"]): r for r in corrs}
corr_summary = []
for profile in ("clean", "historical"):
    for method in NAMES:
        if method == MAIN:
            continue
        rows = []
        for ds, model in meta:
            a, b = cmap[profile, ds, model, MAIN], cmap[profile, ds, model, method]
            if a["coverage"] >= .8 and a["spearman"] is not None and b["spearman"] is not None:
                assert a["measured_layer_count"] == b["measured_layer_count"]
                rows.append((a, b))
        corr_summary.append(dict(profile=profile, comparator=method, n=len(rows),
                                 main_spearman=mean(a["spearman"] for a, b in rows) if rows else None,
                                 comparator_spearman=mean(b["spearman"] for a, b in rows) if rows else None,
                                 main_kendall=mean(a["kendall"] for a, b in rows) if rows else None,
                                 comparator_kendall=mean(b["kendall"] for a, b in rows) if rows else None))

# A common-cohort table for the requested directional controls; report empty or
# tiny cohorts honestly rather than comparing averages from different groups.
core = [MAIN, NORMS, "abs_cos_only", "signed_cos_new_norm", "visual_lga_dot"]
core_groups = [(ds, m) for ds, m in meta if meta[ds, m]["coverage"] >= .8 and
               all(metric_map["clean", ds, m, method, 3]["complete"] for method in core)]
common = []
for method in core:
    rr = [metric_map["clean", ds, m, method, 3] for ds, m in core_groups]
    common.append(dict(method=method, n=len(rr), combinations=";".join(f"{d}/{m}" for d, m in core_groups),
                       best=mean(r["best"] for r in rr) if rr else None,
                       mean=mean(r["mean"] for r in rr) if rr else None))

# Independent recalculation checks against the prior two-formula evidence.
previous_pairs = rcsv(PREV / "paired_summary.csv")
checks = []
for r in previous_pairs:
    profile = r.get("profile")
    k = int(r["k"])
    new = next(x for x in summaries if x["profile"] == profile and x["k"] == k and x["comparator"] == "visual_lga_dot")
    # Previous output uses n_pairs (inspect fallback names for compatibility).
    old_n = int(r.get("n_pairs", r.get("paired_combinations", r.get("n", -1))))
    if old_n >= 0:
        assert old_n == new["n"]
    for old_field, new_field in (("ours_best", "main_best"), ("dot_best", "comparator_best"),
                                  ("ours_mean", "main_mean"), ("dot_mean", "comparator_mean"),
                                  ("mean_delta_best", "delta_best")):
        assert abs(float(r[old_field])-new[new_field]) < 1e-10
    checks.append(dict(profile=profile, k=k, recomputed_n=new["n"]))

prior_manifest = json.loads(read(PREV / "verification.json"))
prior_source_checks = []
for r in prior_manifest["sources"]:
    p = Path(r["path"])
    assert p.is_file(), p
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest == r["sha256"], f"Source changed since locked audit: {p}"
    sources[str(p)] = digest
    prior_source_checks.append(str(p))

norm15 = {(r["dataset"], r["model"]) for r in pairs if r["profile"] == "clean" and r["k"] == 3
          and r["comparator"] == NORMS and r["eligible"]}
top1_same15 = [r for r in pairs if r["profile"] == "clean" and r["k"] == 1
               and r["comparator"] == NORMS and r["eligible"] and (r["dataset"], r["model"]) in norm15]
matched_budget_check = dict(n=len(top1_same15),
                            main_top1=mean(r["main_best"] for r in top1_same15),
                            norm_top1=mean(r["comparator_best"] for r in top1_same15),
                            delta_top1=mean(r["delta_best"] for r in top1_same15))

for name, rows in (("candidate_topk.csv", candidate_rows), ("layer_scores.csv", score_rows),
                   ("method_metrics.csv", metric_rows), ("paired_comparisons.csv", pairs),
                   ("paired_summary.csv", summaries), ("layerwise_correlations.csv", corrs),
                   ("correlation_summary.csv", corr_summary), ("common_cohort_top3.csv", common),
                   ("direction_top3_missing_layers.csv", missing)):
    writecsv(name, rows)
summary = dict(generated_at=datetime.now().astimezone().isoformat(), method_names=NAMES,
               primary_top3=[r for r in summaries if r["profile"] == "clean" and r["k"] == 3],
               norm_top1=next(r for r in summaries if r["profile"] == "clean" and r["k"] == 1 and r["comparator"] == NORMS),
               norm_top5=next(r for r in summaries if r["profile"] == "clean" and r["k"] == 5 and r["comparator"] == NORMS),
               norm_different_complete=[r for r in pairs if r["profile"] == "clean" and r["k"] == 3 and r["comparator"] == NORMS and r["eligible"] and not r["same_set"]],
               norm_all_same_set=sum(set(rankings[d, m, MAIN][:3]) == set(rankings[d, m, NORMS][:3]) for d, m in meta),
               norm_all_same_order=sum(rankings[d, m, MAIN][:3] == rankings[d, m, NORMS][:3] for d, m in meta),
               common_cohort=common, primary_correlations=[r for r in corr_summary if r["profile"] == "clean"],
               prior_comparison_checks=checks,
               unchanged_prior_source_count=len(prior_source_checks),
               top1_on_norm_top3_cohort=matched_budget_check,
               evidence_status="Exploratory post-hoc ablation; already-used evaluation results are not independent confirmation.",
               source_sha256=sources)
(OUT / "analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k not in ("source_sha256", "method_names")}, ensure_ascii=False, indent=2))
