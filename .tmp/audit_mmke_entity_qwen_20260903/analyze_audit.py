import csv
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def digest(ids):
    payload = "\n".join(sorted(ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def norm(s):
    return " ".join(str(s or "").casefold().split())


def canon(x):
    s = str(x)
    return s if s.startswith("mmke_") else f"mmke_{int(s)}"


data = json.loads((ROOT / "vqa_mmke_entity_train_evqa_compat.json").read_text(encoding="utf-8"))
manifest_ids = [f"mmke_{i}" for i in range(len(data))]
manifest_set = set(manifest_ids)

ours = ROOT / "ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304/qwen2.5-vl-3b"
lga = ROOT / "lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900/qwen2.5-vl-3b"
salem = ROOT / "salem_candidate_layers_7models_3data_current_alloc_20260621_203335/qwen2.5-vl-3b"
perturb = ROOT / "perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701/qwen2.5-vl-3b"
visedit = ROOT / "visedit_keytoken_mmke_7models_job3044841_20260704_192247/qwen2.5-vl-3b"
cma = ROOT / "cma_direct_v13_full_g09_gpu0_20260703_134818/qwen2.5-vl-3b"

cache_rows = jsonl(ours / "model_pred_cache.jsonl")
cache_counts = Counter(str(r.get("sample_id")) for r in cache_rows)
cache_by_id = {str(r.get("sample_id")): r for r in cache_rows}
nonempty = {sid for sid, r in cache_by_id.items() if str(r.get("answer") or "").strip()}
empty = {sid for sid, r in cache_by_id.items() if not str(r.get("answer") or "").strip()}
missing = manifest_set - set(cache_by_id)
equal_alt = set()
for sid, r in cache_by_id.items():
    i = int(sid.split("_")[-1])
    if norm(r.get("answer")) == norm(data[i].get("alt")):
        equal_alt.add(sid)

ours_rows = jsonl(ours / "ours_direct_sample_layer_scores.jsonl")
ours_valid = {str(r["sample_id"]) for r in ours_rows}
ours_input = set(cache_by_id)

lga_prog = jsonl(lga / "progress.jsonl")
lga_input = {str(r["sample_id"]) for r in lga_prog}
lga_valid = {str(r["sample_id"]) for r in lga_prog if r.get("status") == "processed" and r.get("ok_any_layer")}

salem_prog = jsonl(salem / "progress.jsonl")
salem_input = {f"mmke_{int(r['sample'])}" for r in salem_prog}
salem_valid = set(salem_input)

perturb_prog = jsonl(perturb / "progress.jsonl")
perturb_input = {str(r["sample_id"]) for r in perturb_prog}
perturb_valid = {str(r["sample_id"]) for r in perturb_prog if r.get("status") == "ok"}

with (visedit / "sample_manifest.csv").open(encoding="utf-8-sig", newline="") as f:
    vis_rows = list(csv.DictReader(f))
vis_input = {canon(r["sample_id"]) for r in vis_rows}
vis_valid = {canon(r["sample_id"]) for r in vis_rows if str(r["used_for_localization"]).lower() == "true"}

cma_prog = jsonl(cma / "progress.jsonl")
cma_input = {str(r["sample_id"]) for r in cma_prog}
cma_final = [r for r in cma_prog if "valid_noise_repeat_count" in r]
cma_valid = {str(r["sample_id"]) for r in cma_final if r.get("status") == "ok" and int(r.get("valid_noise_repeat_count", 0)) > 0}
cma_excluded = {str(r["sample_id"]) for r in cma_final if r.get("status") == "excluded"}
gap_rows = [r for r in cma_prog if r.get("status") == "low_corruption_gap"]
gap_by_group = {}
for r in gap_rows:
    gap_by_group.setdefault((float(r["noise_scale"]), int(r["repeat"])), []).append(r)

methods = {
    "Ours-Direct": (ours_input, ours_valid, "direct"),
    "LGA-Param-Direct-AltModelPred": (lga_input, lga_valid, "direct"),
    "SaLEM-Alt-Direct": (salem_input, salem_valid, "reconstructed_by_order"),
    "Perturb-KL-Direct-AltSeq": (perturb_input, perturb_valid, "direct"),
    "VisEdit-Contrib-Pre-KeyToken": (vis_input, vis_valid, "direct_numeric_id_canonicalized"),
    "CMA-Direct": (cma_input, cma_valid, "direct"),
}
common = set.intersection(*(v[0] for v in methods.values()))

pairs = []
names = list(methods)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        A, B = methods[a][0], methods[b][0]
        pairs.append({"a": a, "b": b, "intersection": len(A & B), "only_a": len(A - B), "only_b": len(B - A), "jaccard": len(A & B) / len(A | B)})

def percentile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    pos = (len(vals) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)

gap_stats = {}
for key, rows in gap_by_group.items():
    vals = [float(r["gap"]) for r in rows if math.isfinite(float(r["gap"]))]
    gap_stats[f"alpha={key[0]},seed={key[1]}"] = {
        "count": len(rows), "finite": len(vals), "min": min(vals), "p25": percentile(vals, .25),
        "median": percentile(vals, .5), "p75": percentile(vals, .75), "p90": percentile(vals, .9),
        "p95": percentile(vals, .95), "max": max(vals),
        "closest_below": sorted(({"sample_id": r["sample_id"], "gap": r["gap"]} for r in rows), key=lambda x: abs(float(x["gap"]) - .05))[:20],
    }

rng = random.Random(20260903)
nonempty_sample = rng.sample(sorted(nonempty), min(20, len(nonempty)))

def sample_detail(sid):
    i = int(sid.split("_")[-1])
    row = cache_by_id.get(sid, {})
    return {
        "sample_id": sid, "src": data[i].get("src"), "alt": data[i].get("alt"), "model_pred": row.get("answer", ""),
        "first_token": None, "first_token_is_eos": None, "effective_token_length": None,
        "generated_token_ids_present": "generated_token_ids" in row,
    }

summary = json.loads((cma / "summary.json").read_text(encoding="utf-8"))
out = {
    "base": {
        "total_samples": len(manifest_set), "generated_model_pred_samples": len(cache_by_id),
        "nonempty_model_pred_samples": len(nonempty), "empty_model_pred_samples": len(empty),
        "model_pred_equal_alt_samples": len(equal_alt), "model_pred_not_equal_alt_samples": len(set(cache_by_id) - equal_alt),
        "missing_model_pred_samples": len(missing), "duplicate_sample_ids": sum(c - 1 for c in cache_counts.values() if c > 1),
        "cache_ids_hash": digest(set(cache_by_id)), "missing_generated_token_ids": sum("generated_token_ids" not in r for r in cache_rows),
    },
    "empty_examples": [sample_detail(s) for s in sorted(empty)[:20]],
    "nonempty_examples": [sample_detail(s) for s in nonempty_sample],
    "methods": {name: {"input": len(inp), "valid": len(valid), "excluded": len(inp-valid), "hash": digest(valid), "evidence": ev,
                       "missing_manifest_ids": len(manifest_set-inp), "extra_ids": len(inp-manifest_set)} for name, (inp, valid, ev) in methods.items()},
    "common": {"count": len(common), "hash": digest(common)},
    "pairs": pairs,
    "cma": {
        "input": len(cma_input), "final_records": len(cma_final), "valid": len(cma_valid), "valid_ids": sorted(cma_valid),
        "excluded": len(cma_excluded), "low_gap_unique": len({str(r['sample_id']) for r in gap_rows}),
        "low_gap_records": len(gap_rows), "runtime_errors": sum(1 for r in cma_final if r.get("error")),
        "nonfinite_gap_records": sum(1 for r in gap_rows if not math.isfinite(float(r["gap"]))),
        "gap_stats": gap_stats, "summary_excluded_sample_count": summary.get("excluded_sample_count"),
        "valid_gap_values_retained": False, "s_clean_corrupt_restore_retained": False,
    },
}
print(json.dumps(out, ensure_ascii=False, indent=2))
