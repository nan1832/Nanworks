"""Frozen-ledger, layer-level VisualTrack cosine audit; never changes source results.

Primary: matched_gradient cohort, all main sweep rows, no PaliGemma.
Peak rules are fixed before inspecting editing outcomes: global peak connected
90%-range region (80/95% sensitivity), and highest interior local peak +/- 1.
Permutation p-values are exploratory: exchangeability across layers is imperfect.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/visual_track_metric_audit_20260929"
SOURCE = ROOT / "outputs/visual_track_cosine_20260928/targets_v2/results"
LEDGER = ROOT / "outputs/sweep_ledger_20260928_110311/ledger.json"
METRICS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]
VARIANTS = ["none", "alt", "model_pred"]
DATASETS = ["evqa-pilot500", "mmke-visual", "mmke-entity"]
MODELS = {"blip2-opt-2.7b": 32, "instructblip-vicuna-7b": 32,
          "minigpt-4-vicuna-7b": 32, "llava-v1.5-7b": 32,
          "qwen2.5-vl-3b": 36, "smolvlm-1.7b": 24}
N_SAMPLES = {"evqa-pilot500": 500, "mmke-visual": 214, "mmke-entity": 636}
SEED, N_PERM = 20260929, 19999


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                      allow_nan=False), encoding="utf-8")


def csvsave(name, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                         for k, v in r.items()} for r in rows)


def rank(a):
    a = np.asarray(a, dtype=float)
    return (a[:, None] > a[None, :]).sum(axis=1) + (a[:, None] == a[None, :]).sum(axis=1) / 2 + .5


def unit(a):
    a = np.asarray(a, dtype=float)
    a = a - a.mean(axis=0)
    norm = np.sqrt((a * a).sum(axis=0))
    return np.divide(a, norm, out=np.zeros_like(a), where=norm > 1e-12), norm > 1e-12


def rho(x, y):
    if len(x) < 3:
        return None
    x, okx = unit(rank(x)); y, oky = unit(rank(y))
    return float(np.clip(x @ y, -1, 1)) if okx and oky else None


def depth_partial(x, y, layers):
    z, _ = unit(rank(layers))
    x = rank(x); y = rank(y)
    x = x - x.mean(); y = y - y.mean()
    x = x - z * (z @ x); y = y - z * (z @ y)
    x, okx = unit(x); y, oky = unit(y)
    return float(np.clip(x @ y, -1, 1)) if okx and oky else None


def bh(rows, pkey="p_perm", qkey="q_bh"):
    valid = sorted((r for r in rows if r[pkey] is not None), key=lambda r: r[pkey])
    previous = 1.
    for i in range(len(valid) - 1, -1, -1):
        previous = min(previous, valid[i][pkey] * len(valid) / (i + 1))
        valid[i][qkey] = previous
    for r in rows:
        r.setdefault(qkey, None)
    return len(valid)


def peak_sets(values):
    x = np.asarray(values)
    top = int(np.argmax(x))
    span = float(np.ptp(x))
    if span <= 1e-12:
        return {}, top, []
    sets = {}
    for threshold in (.80, .90, .95):
        limit = float(x.min() + threshold * span)
        lo = hi = top
        while lo > 0 and x[lo - 1] >= limit:
            lo -= 1
        while hi < len(x) - 1 and x[hi + 1] >= limit:
            hi += 1
        sets[f"global_{round(100*threshold)}"] = list(range(lo, hi + 1))
    # Find interior plateaus strictly above both adjacent outside values.
    peaks = []
    i = 1
    while i < len(x) - 1:
        j = i
        while j + 1 < len(x) and x[j + 1] == x[i]:
            j += 1
        if j < len(x) - 1 and x[i] > x[i - 1] and x[j] > x[j + 1]:
            peaks.append((i + j) // 2)
        i = j + 1
    if peaks:
        interior = sorted(peaks, key=lambda l: (-x[l], l))[0]
        sets["interior_pm1"] = list(range(interior - 1, interior + 2))
    return sets, top, peaks


def summaries(rows, scope):
    result = []
    for v in VARIANTS:
        for metric in METRICS:
            rr = [r for r in rows if r["variant"] == v and r["metric"] == metric and r["rho"] is not None]
            vals = [r["rho"] for r in rr]
            partials = [r["rho_partial_depth"] for r in rr if r["rho_partial_depth"] is not None]
            result.append(dict(scope=scope, variant=v, metric=metric, n_groups=len(rr),
                mean_rho=float(np.mean(vals)) if vals else None,
                median_rho=float(np.median(vals)) if vals else None,
                positive=sum(x > 0 for x in vals), negative=sum(x < 0 for x in vals),
                strong_positive=sum(x >= .6 for x in vals), strong_negative=sum(x <= -.6 for x in vals),
                q05_positive=sum(r.get("q_bh") is not None and r["q_bh"] < .05 and r["rho"] > 0 for r in rr),
                q05_negative=sum(r.get("q_bh") is not None and r["q_bh"] < .05 and r["rho"] < 0 for r in rr),
                mean_partial_depth=float(np.mean(partials)) if partials else None))
    return result


def main():
    OUT.mkdir(exist_ok=True)
    ledger = load(LEDGER)
    assert LEDGER.read_bytes() == (ROOT / "outputs/visual_track_cosine_20260928/inputs/ledger.json").read_bytes()
    pools = collections.defaultdict(dict)
    for r in ledger["rows"]:
        if r["recipe"] == "main" and r["model"] in MODELS:
            assert r["layer"] not in pools[r["dataset"], r["model"]]
            assert np.isfinite(list(r["metrics"].values())).all()
            # Some historical Average fields were rounded to 2 decimals; retain
            # the published result, allowing only that rounding discrepancy.
            assert abs(r["metrics"]["Average"] - np.mean([r["metrics"][m] for m in METRICS[:-1]])) < .0051
            pools[r["dataset"], r["model"]][r["layer"]] = r
    assert len(pools) == 18 and sum(map(len, pools.values())) == 349
    manifest = dict(ledger=str(LEDGER.relative_to(ROOT)), ledger_sha256=sha(LEDGER),
        ledger_updated_at=ledger["updated_at"], script_sha256=sha(Path(__file__)),
        excluded_model="paligemma-3b", recipe="main", permutation_seed=SEED,
        permutations=N_PERM, primary_cohort="matched_gradient", primary_flavor="raw",
        peak_primary="global maximum contiguous component above min+0.90*(max-min)",
        peak_sensitivity=["global_80", "global_95", "highest interior local peak +/-1"], sources=[])
    correlations, aligned, peaks, tops, coverage, variant_pairs = [], [], [], [], [], []
    rng = np.random.default_rng(SEED)
    for ds in DATASETS:
        for model, depth in MODELS.items():
            directory = SOURCE / ds / model
            summary = load(directory / "summary.json")
            assert summary["status"] == "done" and summary["schema"] == 2
            for fname, key in [("protocol.json", "protocol_sha256"), ("layer_scores.json", "scores_sha256"), ("diagnostics.json", "diagnostics_sha256")]:
                assert sha(directory / fname) == summary[key], str(directory / fname)
            protocol = load(directory / "protocol.json")
            manifest["sources"].append(dict(dataset=ds, model=model,
                summary_sha256=sha(directory / "summary.json"), scores_sha256=summary["scores_sha256"],
                protocol_sha256=summary["protocol_sha256"], diagnostics_sha256=summary["diagnostics_sha256"]))
            data = load(directory / "layer_scores.json")["rows"]
            pool = pools[ds, model]; layers = sorted(pool)
            metrics = np.array([[pool[l]["metrics"][m] for m in METRICS] for l in layers])
            ys = np.column_stack([rank(metrics[:, i]) for i in range(len(METRICS))])
            yu, yok = unit(ys)
            perms = rng.permuted(np.broadcast_to(np.arange(len(layers)), (N_PERM, len(layers))), axis=1)
            for cohort in ["matched_gradient", "available_train"]:
                values_by_variant = {}
                for variant in VARIANTS:
                    rows = sorted([r for r in data if r["cohort"] == cohort and r["variant"] == variant], key=lambda r:r["layer"])
                    assert [r["layer"] for r in rows] == list(range(depth))
                    assert len({r["n"] for r in rows}) == 1
                    values = np.array([r["visual_track_cos"] for r in rows])
                    assert np.isfinite(values).all()
                    values_by_variant[variant] = values
                    base = dict(dataset=ds, model=model, cohort=cohort, variant=variant,
                                similarity_samples=rows[0]["n"], sample_coverage=rows[0]["n"]/N_SAMPLES[ds])
                    if cohort == "matched_gradient":
                        assert rows[0]["n"] == len(protocol["matched_sample_ids"])
                    coverage.append(dict(**base, depth=depth, n_swept=len(layers), swept_layers=layers,
                                         missing_sweep_layers=[l for l in range(depth) if l not in pool]))
                    for l in range(depth):
                        aligned.append(dict(**base, layer=l, cosine=float(values[l]), evaluated=l in pool,
                            **({m:pool[l]["metrics"][m] for m in METRICS} if l in pool else {}),
                            training=pool[l]["training"] if l in pool else None,
                            eval_source=pool[l]["source"] if l in pool else None))
                    q1, q3 = np.quantile(values, [.25, .75], method="linear")
                    keep = [l for l in layers if q1 - (q3-q1) <= values[l] <= q3 + (q3-q1)]
                    x = values[layers]; xu, xok = unit(rank(x))
                    if cohort == "matched_gradient":
                        perm_rhos = np.einsum("n,bnm->bm", xu, yu[perms], optimize=True)
                    for flavor, ll in [("raw", layers), ("tukey_k1", keep)]:
                        for k, metric in enumerate(METRICS):
                            y = [pool[l]["metrics"][metric] for l in ll]
                            xx = values[ll]; r = rho(xx, y)
                            p = (int(np.sum(np.abs(perm_rhos[:, k]) >= abs(r)-1e-12)) + 1)/(N_PERM+1) if cohort == "matched_gradient" and flavor == "raw" and r is not None else None
                            correlations.append(dict(**base, flavor=flavor, metric=metric, n_layers=len(ll),
                                rho=r, rho_partial_depth=depth_partial(xx,y,ll) if len(ll)>=4 else None,
                                rho_cos_depth=rho(xx,ll), rho_metric_depth=rho(y,ll), p_perm=p))
                    sets, top, local_peaks = peak_sets(values)
                    order = sorted(range(depth), key=lambda l:(-values[l],l))
                    candidate = order[:3]; missing = [l for l in candidate if l not in pool]
                    for metric in METRICS:
                        yall = [pool[l]["metrics"][metric] for l in layers]
                        tops.append(dict(**base, metric=metric, top1_layer=top, top3_layers=candidate,
                            missing_top3=missing, top3_complete=not missing,
                            top1=pool[top]["metrics"][metric] if top in pool else None,
                            top1_gap_from_observed_mean=pool[top]["metrics"][metric]-float(np.mean(yall)) if top in pool else None,
                            top1_regret_vs_observed_best=max(yall)-pool[top]["metrics"][metric] if top in pool else None,
                            mean3=float(np.mean([pool[l]["metrics"][metric] for l in candidate])) if not missing else None,
                            best3=max(pool[l]["metrics"][metric] for l in candidate) if not missing else None,
                            observed_mean=float(np.mean(yall)), observed_best=max(yall)))
                    for rule, region in sets.items():
                        inside = [l for l in region if l in pool]
                        outside = [l for l in layers if l not in region]
                        absent = [l for l in region if l not in pool]
                        for metric in METRICS:
                            yi = [pool[l]["metrics"][metric] for l in inside]
                            yo = [pool[l]["metrics"][metric] for l in outside]
                            peaks.append(dict(**base, rule=rule, metric=metric, global_peak=top,
                                global_peak_endpoint=top in [0,depth-1], local_peak_centers=local_peaks,
                                region=region, observed_inside=inside, missing_inside=absent,
                                n_outside=len(outside), complete=not absent and bool(yi) and bool(yo),
                                mean_inside=float(np.mean(yi)) if yi else None,
                                mean_outside=float(np.mean(yo)) if yo else None,
                                delta_pp=float(np.mean(yi)-np.mean(yo)) if yi and yo else None,
                                region_contains_observed_best=any(pool[l]["metrics"][metric] == max(pool[k]["metrics"][metric] for k in layers) for l in inside)))
                for i, va in enumerate(VARIANTS):
                    for vb in VARIANTS[i+1:]:
                        variant_pairs.append(dict(dataset=ds,model=model,cohort=cohort,variant_a=va,variant_b=vb,
                            rho_full_curve=rho(values_by_variant[va],values_by_variant[vb])))
    primary = [r for r in correlations if r["cohort"] == "matched_gradient" and r["flavor"] == "raw"]
    n_tests = bh(primary)
    aggregate = summaries(primary, "all18")
    for ds in DATASETS:
        aggregate += summaries([r for r in primary if r["dataset"] == ds], ds)
    for model in MODELS:
        aggregate += summaries([r for r in primary if r["model"] == model], model)
    aggregate += summaries([r for r in primary if r["sample_coverage"] >= .8], "coverage_ge_80pct")
    for cohort, flavor in [("available_train", "raw"), ("matched_gradient", "tukey_k1")]:
        aggregate += summaries([r for r in correlations if r["cohort"] == cohort and r["flavor"] == flavor], cohort+"_"+flavor)
    peak_summary = []
    for rule in ["global_80", "global_90", "global_95", "interior_pm1"]:
        for v in VARIANTS:
            for metric in METRICS:
                all_rr = [r for r in peaks if r["cohort"]=="matched_gradient" and r["rule"]==rule and r["variant"]==v and r["metric"]==metric]
                rr = [r for r in all_rr if r["complete"]]
                vals = [r["delta_pp"] for r in rr]
                peak_summary.append(dict(rule=rule,variant=v,metric=metric,n_regions=len(all_rr),n_complete=len(rr),
                    mean_delta_pp=float(np.mean(vals)) if vals else None, median_delta_pp=float(np.median(vals)) if vals else None,
                    wins=sum(x>1e-9 for x in vals),ties=sum(abs(x)<=1e-9 for x in vals),losses=sum(x< -1e-9 for x in vals),
                    groups=[(r["dataset"],r["model"]) for r in rr]))
    result = dict(manifest=manifest, counts=dict(main_layers=349,groups=18,primary_tests=n_tests,
        primary_constant_tests=sum(r["rho"] is None for r in primary)), primary=primary,
        summary=aggregate, peak_summary=peak_summary)
    save("analysis.json",result)
    save("source_manifest.json",manifest)
    for name, rows in [("correlations",correlations),("aligned_layers",aligned),("peak_regions",peaks),
        ("top3_per_metric",tops),("coverage",coverage),("curve_similarity_between_variants",variant_pairs),
        ("correlation_summary",aggregate),("peak_summary",peak_summary)]:
        csvsave(name+".csv",rows)
    print(json.dumps(dict(counts=result["counts"], summary=aggregate[:18],
        peak90=[r for r in peak_summary if r["rule"]=="global_90" and r["metric"]!="T-Loc"],
        strongest=sorted([r for r in primary if r["rho"] is not None],key=lambda r:-abs(r["rho"]))[:12]),ensure_ascii=False))


if __name__ == "__main__":
    main()
