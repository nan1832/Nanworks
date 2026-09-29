"""Derive VisEdit Pre candidates from archived scores; never run/edit a model."""
import ast
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LEDGER = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
MODELS = {
    "BLIP2-OPT-2.7B": "blip2-opt-2.7b",
    "InstructBLIP-Vicuna-7B": "instructblip-vicuna-7b",
    "MiniGPT-4-Vicuna-7B": "minigpt-4-vicuna-7b",
    "LLaVA-v1.5-7B": "llava-v1.5-7b",
    "Qwen2.5-VL-3B": "qwen2.5-vl-3b",
    "PaliGemma-3B": "paligemma-3b",
    "SmolVLM-Instruct-1.7B": "smolvlm-1.7b",
}
DATASETS = ["EVQA-pilot500", "MMKE-visual", "MMKE-entity"]
source_script = ROOT / "VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py"
tree = ast.parse(source_script.read_text(encoding="utf-8"))
names = {"moving_average", "find_high_region", "pre_candidates"}
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(functions) == 3
ns = {"np": np}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_script), "exec"), ns)

def layers(xs):
    return ",".join(f"L{x}" for x in xs)

def table_rows(text):
    return [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in text.splitlines() if line.startswith("| ")]

backup = OUT / "backups" / LEDGER.name
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    backup.write_bytes(LEDGER.read_bytes())
old = backup.read_text(encoding="utf-8-sig")
section = old.split("### 2.2 ", 1)[1].split("#### 2.2.1", 1)[0]
alt_rows = [r for r in table_rows(section) if r[0] in DATASETS]
assert len(alt_rows) == 21
history = old.split("#### 2.2.2", 1)[1].split("### 2.3", 1)[0]
history_rows = [r for r in table_rows(history) if r[0] in DATASETS]
assert len(history_rows) == 21
manifest = {}

def register(path):
    path = path.resolve()
    manifest[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path.relative_to(ROOT)).replace("\\", "/")

def derive(path, expected_mode, expected_n):
    cfg = json.loads(path.with_name("config.json").read_text(encoding="utf-8"))
    summary = json.loads(path.with_name("summary.json").read_text(encoding="utf-8"))
    assert cfg["key_mode"] == summary["key_mode"] == expected_mode
    assert cfg["sample_count"] == summary["sample_count"] == expected_n
    scores = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    assert [int(r["layer"]) for r in scores] == list(range(len(scores)))
    vals = np.array([float(r["score_positive"]) for r in scores])
    rebuilt = np.array([max(0, float(r["attn_mean"])) + max(0, float(r["mlp_mean"])) for r in scores])
    assert np.isfinite(vals).all() and np.allclose(vals, rebuilt, rtol=1e-7, atol=1e-12)
    smooth = ns["moving_average"](vals, 3)
    region, threshold, high = ns["find_high_region"](smooth, 0.5)
    assert region is not None
    for p in [path, path.with_name("config.json"), path.with_name("summary.json")]:
        register(p)
    return dict(top3=layers(ns["pre_candidates"](region[0], 3)),
                top5=layers(ns["pre_candidates"](region[0], 5)),
                high_region=f"L{region[0]}-L{region[1]}", threshold=threshold,
                sample_count=expected_n, source=register(path))

historical_checks = []
for row in history_rows:
    ds, model = row[:2]
    path = ROOT / row[8].strip("`")
    if not path.exists() and ds == "EVQA-pilot500":
        path = ROOT / "downloads/evqa_module_contribution/evqa_pilot500_module_6_contribution_model_alt" / MODELS[model] / "contribution_layer.csv"
    derived = derive(path, "alt", int(row[3]))
    assert (derived["top3"], derived["top5"]) == (row[5], row[6]), (ds, model, derived, row)
    historical_checks.append(dict(dataset=ds, model=model, **derived))

strict_path = ROOT / "md/Location/VisEditKeyToken_outputs_20260704/visedit_keytoken_candidates_summary.csv"
strict = {(r["dataset"], r["model"]): r for r in csv.DictReader(strict_path.open(encoding="utf-8-sig")) if r["phase"] == "full"}
register(strict_path)
results = []
for r in alt_rows:
    ds, model, top3, top5, status = r
    slug = MODELS[model]
    if ds == "EVQA-pilot500":
        source = next(h["source"] for h in historical_checks if h["dataset"] == ds and h["model"] == model)
        token_rule, n = "alt_first_token", 500
    else:
        s = strict[(ds.lower(), slug)]
        assert (top3, top5) == (s["top3_pre"], s["top5_pre"])
        token_rule = "alt_entity_anchor" if ds == "MMKE-entity" else "m_rel_ans_or_rel_ans_visual_semantic"
        n = int(s["valid"])
        source = register(strict_path)
    results.append(dict(dataset=ds, model=model, method="VisEdit-Contrib-Pre-alt", target_mode="alt",
                        token_rule=token_rule, top3=top3, top5=top5, status="done", sample_count=n,
                        high_region="", threshold="", source=source))
    if ds == "EVQA-pilot500":
        if slug == "blip2-opt-2.7b":
            path = ROOT / "downloads/evqa_module_contribution/blip2/evqa_proxy500_blip2_module_contribution_model_pred_20260604_100403/contribution_layer.csv"
        else:
            path = ROOT / "downloads/evqa_module_contribution/evqa_pilot500_module_6_contribution_model_pred" / slug / "contribution_layer.csv"
        d = derive(path, "model_pred", 500)
        results.append(dict(dataset=ds, model=model, method="VisEdit-Contrib-Pre-model_pred", target_mode="model_pred",
                            token_rule="base_model_next_token_argmax", status="done", **d))
    else:
        path = ROOT / "downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600" / ds.split("-")[1] / "pred" / slug / "config.json"
        cfg = json.loads(path.read_text(encoding="utf-8"))
        assert cfg["key_mode"] == "pred"
        source = register(path)
        results.append(dict(dataset=ds, model=model, method="VisEdit-Contrib-Pre-model_pred", target_mode="model_pred",
                            token_rule="base_model_next_token_argmax", status="pending_model_pred_scores",
                            sample_count="", top3="", top5="", high_region="", threshold="", source=source))

register(source_script)
register(ROOT / "VisEdit-main/scripts/run_evqa_module_contribution_pilot500_multi.py")
with (OUT / "visedit_target_candidates_21x2.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(results[0]))
    w.writeheader()
    w.writerows(results)
protocol = dict(date="2026-09-27", smoothing_window=3, lambda_value=0.5, std_ddof=0,
                boundaries="moving average uses truncated windows at endpoints",
                region_order="longest; then greatest smoothed score sum; then shallowest start",
                candidate_rule="s_H-1 ... s_H-K, stop at layer 0; do not pad",
                raw_config_caution="model_pred config token_rule is generic stale text; actual branch uses next-token argmax",
                mmke_pred_caution="pred field first token is not model_pred; never relabel existing pred scores",
                source_sha256=manifest)
(OUT / "protocol_and_sources.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "historical_alt_reproduction.json").write_text(json.dumps(historical_checks, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(dict(rows=len(results), alt_done=21, model_pred_done=7, model_pred_pending=14,
                      historical_alt_reproduced=len(historical_checks),
                      evqa_model_pred=[{k:r[k] for k in ["model", "top3", "top5", "high_region"]} for r in results if r["target_mode"] == "model_pred" and r["status"] == "done"]), ensure_ascii=False, indent=2))
