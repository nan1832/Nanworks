"""Rebuild the seven-family localization catalog from audited score artifacts.

No model execution, training, checkpoint selection, or editing-performance ranking.
All numerical filtering is performed before Top-3 selection, across all layers.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/all_methods_recommendations_20260928"
RAW = OUT / "raw"
DOC = ROOT / "md/Location/ALL_Methods_Recommends_layers.md"
MAIN = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
MODELS = {
    "blip2-opt-2.7b": ("BLIP2", 32),
    "instructblip-vicuna-7b": ("InstructBLIP", 32),
    "minigpt-4-vicuna-7b": ("MiniGPT-4", 32),
    "llava-v1.5-7b": ("LLaVA-1.5", 32),
    "qwen2.5-vl-3b": ("Qwen2.5-VL", 36),
    "paligemma-3b": ("PaliGemma", 18),
    "smolvlm-1.7b": ("SmolVLM", 24),
}
DISPLAY_TO_SLUG = dict(zip([
    "BLIP2-OPT-2.7B", "InstructBLIP-Vicuna-7B", "MiniGPT-4-Vicuna-7B",
    "LLaVA-v1.5-7B", "Qwen2.5-VL-3B", "PaliGemma-3B", "SmolVLM-Instruct-1.7B"], MODELS))
DATASETS = {"evqa-pilot500": ("EVQA-pilot500", 500), "mmke-visual": ("MMKE-visual", 214), "mmke-entity": ("MMKE-entity", 636)}
FAMILIES = {1: "中层先验", 2: "CMA 因果恢复", 3: "Perturb-KL", 4: "SaLEM", 5: "LGA 两种梯度空间", 6: "VisEdit 贡献度", 7: "Ours 与两种梯度空间 LGA 消融"}
ABLATION = ROOT / "outputs/lga_two_spaces_ablation_20260928"
ABLATION_GROUPS = []
SOURCES: dict[str, str] = {}
RECS: list[dict] = []
SCORES: list[dict] = []
AUDITS: list[dict] = []
VIS: list[dict] = []
VISEDIT_MMKE = ROOT / 'outputs/visedit_model_pred_mmke_20260929'
RAW_CHANGES: list[dict] = []
CHECKS: Counter = Counter()


def read(path):
    path = Path(path)
    b = path.read_bytes()
    SOURCES[path.relative_to(ROOT).as_posix()] = hashlib.sha256(b).hexdigest()
    return b.decode("utf-8-sig")


def rcsv(path):
    return list(csv.DictReader(io.StringIO(read(path))))


def rjson(path):
    return json.loads(read(path))


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def writejson(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def writecsv(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def ls(seq):
    return ", ".join(f"L{int(x)}" for x in seq) if seq else "—"


def parse_layers(seq):
    return [int(str(x).lstrip("L")) for x in seq]


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|", *["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]]) + "\n"


def add_rank(family, method, ds, model, values, source, *, target="", n=None, flavor="raw", ordered=None, notes="", source_status="done", flags=None):
    assert len(values) == len(set(values)), (method, ds, model)
    assert all(0 <= l < MODELS[model][1] for l in values)
    finite = {l: s for l, s in values.items() if math.isfinite(s)}
    nonfinite = sorted(set(values) - set(finite))
    excluded, q1, q3, lower, upper = [], None, None, None, None
    population = finite
    if flavor == "tukey":
        q1, q3 = [float(x) for x in np.quantile(list(finite.values()), [.25, .75], method="linear")]
        iqr = q3 - q1
        lower, upper = q1 - iqr, q3 + iqr
        excluded = sorted(l for l, s in finite.items() if s < lower or s > upper)
        population = {l: s for l, s in finite.items() if lower <= s <= upper}
        assert set(population) | set(excluded) == set(finite)
        assert not set(population) & set(excluded)
        AUDITS.append(dict(method=method, dataset=ds, model=model, total_layers=MODELS[model][1], finite_layers=len(finite), q1=q1, q3=q3, iqr=iqr, kappa=1.0, lower=lower, upper=upper, excluded_layers=excluded, retained_layers=sorted(population), source=source))
    ranked = sorted(population, key=lambda l: (-population[l], l)) if ordered is None else [l for l in ordered if l in population]
    assert len(ranked) == len(population) and set(ranked) == set(population)
    assert all(population[a] >= population[b] for a, b in zip(ranked, ranked[1:]))
    item = dict(family=family, method=method, dataset=ds, model=model, target=target, flavor=flavor,
                top3=ranked[:3], top3_scores=[population[l] for l in ranked[:3]], all_ranking=ranked,
                total_layers=MODELS[model][1], finite_layers=len(finite), eligible_layers=len(population),
                outlier_layers=excluded, nonfinite_layers=nonfinite, q1=q1, q3=q3, lower=lower, upper=upper,
                sample_count=n, status="done" if len(ranked) >= 3 else "insufficient_layers",
                source_status=source_status, notes=notes, source=source,
                zero_gradient_layers=sorted(l for l,f in (flags or {}).items() if f == 'S_v_zero_grad'))
    RECS.append(item)
    rankmap = {l: i for i, l in enumerate(ranked, 1)}
    for l, score in values.items():
        SCORES.append(dict(family=family, method=method, dataset=ds, model=model, target=target, flavor=flavor,
                           layer=l, score=score if math.isfinite(score) else None, rank=rankmap.get(l),
                           tukey_outlier=l in excluded, nonfinite=l in nonfinite, source_flags=(flags or {}).get(l, ""), source=source))
    return item


def missing(family, method, ds, model, flavor, reason, target="model_pred+alt"):
    RECS.append(dict(family=family, method=method, dataset=ds, model=model, target=target, flavor=flavor,
                     top3=[], top3_scores=[], all_ranking=[], status="pending_source_data", notes=reason, source=""))


def get(method, ds, model, flavor="raw"):
    matches = [r for r in RECS if (r["method"], r["dataset"], r["model"], r["flavor"]) == (method, ds, model, flavor)]
    assert len(matches) == 1, (method, ds, model, flavor, len(matches))
    return matches[0]


def top(method, ds, model, flavor="raw"):
    r = get(method, ds, model, flavor)
    if r["status"] == "pending_source_data":
        return "待补"
    zero=set(r.get('zero_gradient_layers',[]))
    return ", ".join(f"L{l}"+('†' if l in zero else '') for l in r['top3']) or '—'


def baseline_sources():
    for ds in DATASETS:
        for model, (_, count) in MODELS.items():
            center = (count - 1) / 2
            add_rank(1, "Middle-Prior", ds, model, {l: -abs(l-center) for l in range(count)}, "analytic:rho=0.5;tie=layer_asc", target="none")
            for family, folder, name, scorecol, method in [
                (2, "cma_alt", "cma_direct_layer_scores.csv", "cr_seq_mean", "CMA-alt-v1.3"),
                (2, "cma_model_pred", "cma_layer_scores.csv", "cr_mean", "CMA-model_pred"),
                (3, "perturb", "perturb_kl_layer_scores.csv", "score_kl_robust", "Perturb-KL-alt"),
                (4, "salem", "salem_layer_scores.csv", "layer_score", "SaLEM-alt"),
            ]:
                p = RAW / folder / ds / model / name
                rows, summary = rcsv(p), rjson(p.with_name("summary.json"))
                assert len(rows) == count and {int(r["layer"]) for r in rows} == set(range(count))
                values = {int(r["layer"]): float(r[scorecol]) for r in rows}
                ordered = [int(r["layer"]) for r in sorted(rows, key=lambda r: int(r["rank"]))]
                if folder == "cma_model_pred":
                    assert summary["target_field"] == "model_pred"
                    expected = summary["top3"]
                    n = summary["valid_unique_samples"]
                    note = f"{n}/{DATASETS[ds][1]}；model_pred 可用 {summary['total_unique_samples']}/{DATASETS[ds][1]}；排序{'稳定' if summary['candidate_ranking_stable'] else '不稳定'}"
                else:
                    expected = parse_layers(summary["top3_layers"])
                    if folder == "cma_alt":
                        assert summary["target_sequence"] == "complete alt sequence"
                        n = summary["max_layer_valid_restore_count"]
                    elif folder == "salem":
                        assert "alt" in summary["target_field"]
                        n = summary["ok_samples"]
                    else:
                        assert summary["target_sequence"] == "complete alt sequence"
                        n = summary["common_valid_sample_count"]
                    note = f"{n}/{DATASETS[ds][1]}"
                    if summary.get('status','done')!='done':
                        note += '；'+summary['status']
                r = add_rank(family, method, ds, model, values, rel(p), ordered=ordered, target="model_pred" if folder == "cma_model_pred" else "alt", n=n, notes=note, source_status=summary.get("status", summary.get("coverage_status", "done")))
                assert r["top3"] == expected, (method, ds, model, r["top3"], expected)
                CHECKS["baseline_top3_matches_server_summary"] += 1
            p = RAW / "lga_param" / ds / model / "layer_scores.csv"
            rows = rcsv(p)
            assert len(rows) == count and all(r["status"] == "ok" for r in rows)
            values = {int(r["layer"]): float(r["score_raw"]) for r in rows}
            nset = {int(r["valid_sample_count"]) for r in rows}
            assert len(nset) == 1
            for flavor in ("raw", "tukey"):
                add_rank(5, "LGA-Param", ds, model, values, rel(p), flavor=flavor, target="model_pred+alt", n=next(iter(nset)))
    old = rcsv(ROOT / "outputs/lga_tukey_correction_20260926/tukey_audit_21groups.csv")
    for row in old:
        current=get('LGA-Param',row['dataset'],row['model'],'tukey')
        assert ls(current['top3']).replace(' ','')==row['tukey_top3']
        assert set(current['outlier_layers'])==set(parse_layers([x for x in row['excluded_layers'].split(',') if x.strip()]))
        assert all(math.isclose(current[k],float(row[k]),rel_tol=1e-12,abs_tol=1e-12) for k in ['q1','q3','lower','upper'])
        CHECKS["previous_tukey_groups_loaded"] += 1
    p=RAW / "cma_alt_formal_qwen_entity/cma_formal_top3_top5.json"
    formal=rjson(p)
    assert parse_layers(formal['raw_rank_all_layers'])[:3]==parse_layers(formal['top3'])
    RECS.append(dict(family=2,method='CMA-alt-formal',dataset='mmke-entity',model='qwen2.5-vl-3b',target='alt',flavor='supplement',top3=parse_layers(formal['top3']),all_ranking=parse_layers(formal['raw_rank_all_layers']),sample_count=formal['valid_unique_samples'],status='done',source_status=formal['status'],notes='独立多噪声多种子补算，43/636，low_valid_coverage；不是21组完整替换版',source=rel(p)))


def visual_sources():
    for ds in DATASETS:
        for model, (_, count) in MODELS.items():
            p = RAW / "visual" / ds / model / "ours_direct_layer_scores.csv"
            rows = rcsv(p)
            summary=rjson(p.with_name('summary.json'))
            original = ROOT / "md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores" / ds / model / p.name
            assert p.read_bytes() == original.read_bytes(), p
            read(original)
            assert len(rows) == count and {int(r["layer"]) for r in rows} == set(range(count))
            counts = {int(r["n_request"]) for r in rows}
            assert len(counts) == 1
            values = {k: {} for k in ["Ours-main", "Ours-signed-direction", "Ours-no-direction", "Ours-no-strength", "LGA-Visual", "LGA-Visual-no-direction"]}
            flags = {}
            for row in rows:
                l = int(row["layer"])
                dot, cos, norm, joint = [float(row[k]) for k in ["S_v_dot", "S_v_cos", "S_v_new_norm", "S_v_joint_norm"]]
                assert all(math.isfinite(x) for x in [dot, cos, norm, joint])
                values["Ours-main"][l] = abs(cos) * norm
                values["Ours-signed-direction"][l] = cos * norm
                values["Ours-no-direction"][l] = norm
                values["Ours-no-strength"][l] = abs(cos)
                values["LGA-Visual"][l] = dot
                values["LGA-Visual-no-direction"][l] = joint
                flags[l] = row["invalid_reason"]
                if row["S_v_zero_grad"].lower() == "true":
                    assert all(v[l] == 0 for v in values.values())
                    CHECKS["zero_gradient_layers_explicitly_retained_in_raw"] += 1
            for method, mapping in values.items():
                for flavor in ["raw", "tukey"]:
                    add_rank(7 if method != "LGA-Visual" else 5, method, ds, model, mapping, rel(p), flavor=flavor, target="model_pred+alt", n=next(iter(counts)), flags=flags,source_status='low_coverage' if summary['coverage_ratio']<.8 else 'done',
                             notes="全层分数；保留原始有限零分及 S_v_zero_grad 标记；不套用历史 clean 预筛选")
    schema = rjson(OUT / "sample_schema_audit.json")
    assert len(schema["samples"]) == 21
    assert all(not any("norm" in k or "cos" in k or "grad" in k or "dot" in k for k in r["keys"]) for r in schema["samples"])
    CHECKS["sample_logs_confirmed_missing_cross_moments"] = 21
    previous = rcsv(ROOT / "outputs/main_formula_validation_20260925/candidate_topk.csv")
    aliases = {"main_abs_cos_new_norm": "Ours-main", "new_norm_only": "Ours-no-direction", "abs_cos_only": "Ours-no-strength", "visual_lga_dot": "LGA-Visual"}
    for r in previous:
        if r["method"] in aliases:
            expected = [int(x.strip().lstrip("L")) for x in r["top3"].split(",")]
            current=get(aliases[r["method"]], r["dataset"], r["model"])
            if current['top3'] == expected:
                CHECKS["raw_top3_matches_previous_formula_analysis"] += 1
            else:
                assert aliases[r['method']]=='LGA-Visual'
                assert [l for l in current['all_ranking'] if l not in current['zero_gradient_layers']][:3]==expected
                RAW_CHANGES.append(dict(dataset=r['dataset'],model=r['model'],method='LGA-Visual',previous_clean_top3=expected,all_layer_raw_top3=current['top3'],reason='raw now includes the recorded finite zero-gradient last layer; zero exceeds negative signed dot'))
                CHECKS['raw_top3_change_explained_by_explicit_zero_layer_policy']+=1


def cross_strength_sources():
    """Only admit complete, hash-verified, historically reproduced GPU results."""
    sync = rjson(ABLATION / "sync_status.json") if (ABLATION / "sync_status.json").exists() else {"records": []}
    for space, prefix in [("parameter", "LGA-Param"), ("visual", "LGA-Visual")]:
        versions = {"no-old-strength": "no_old_strength", "no-new-strength": "no_new_strength"}
        if space == "parameter":
            versions["no-direction"] = "no_direction"
        for ds in DATASETS:
            for model, (_, count) in MODELS.items():
                folder = ABLATION / "results" / space / ds / model
                entry = next((r for r in sync["records"] if (r['space'], r['dataset'], r['model']) == (space, ds, model)), {})
                status = entry.get('status', 'not_started')
                ABLATION_GROUPS.append(dict(space=space, dataset=ds, model=model, status=status, completed_sample_files=entry.get('completed_sample_files', 0)))
                if status != "done":
                    for version in versions:
                        for flavor in ["raw", "tukey"]:
                            missing(7, prefix + "-" + version, ds, model, flavor, "严格逐样本补算状态：" + status + "；不能用层均值恢复交叉统计")
                    continue
                assert entry.get("remote_sample_reaggregation_verified") is True
                summary = rjson(folder / "summary.json")
                assert summary["status"] == "done" and summary["baseline_failures"] == 0
                for name, key in [('layer_scores.json', 'score_sha256'), ('protocol.json', 'protocol_sha256'), ('historical_reproduction.json', 'reproduction_sha256')]:
                    assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == summary[key]
                checks = rjson(folder / "historical_reproduction.json")
                assert len(checks) == count * (4 if space == 'parameter' else 5) and all(c['passed'] for c in checks)
                protocol = rjson(folder / "protocol.json")
                source_name = 'layer_scores.csv' if space == 'parameter' else 'ours_direct_layer_scores.csv'
                original = RAW / ('lga_param' if space == 'parameter' else 'visual') / ds / model / source_name
                assert hashlib.sha256(original.read_bytes()).hexdigest() == protocol['files'][protocol['source'] + '/' + source_name]
                artifact = rjson(folder / "layer_scores.json")
                assert (artifact['space'], artifact['dataset'], artifact['model']) == (space, ds, model)
                rows = artifact['rows']
                assert len(rows) == count and {r['layer'] for r in rows} == set(range(count))
                n = get(prefix, ds, model)['sample_count']
                assert summary['sample_count'] == len(protocol['cohort']) == n and all(r['n'] == n for r in rows)
                flags = {r['layer']: 'S_v_zero_grad' for r in rows if space == 'visual' and r['old_norm'] == r['new_norm'] == 0}
                for version, column in versions.items():
                    for flavor in ['raw', 'tukey']:
                        add_rank(7, prefix + '-' + version, ds, model, {r['layer']: r[column] for r in rows}, rel(folder / 'layer_scores.json'),
                                 target='model_pred+alt', n=n, flavor=flavor, flags=flags,
                                 notes='逐样本求交叉项再取均值；原始样本与梯度对象复核通过；' + summary['updated_at'])
                CHECKS['strict_ablation_groups_imported'] += 1


def visedit_sources():
    src = ROOT / "VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py"
    tree = ast.parse(read(src))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"moving_average", "find_high_region", "pre_candidates"}]
    assert len(funcs) == 3
    ns = {"np": np}
    exec(compile(ast.Module(body=funcs, type_ignores=[]), str(src), "exec"), ns)

    def derive(ds, model, mode, path, token, expected=None, historical=False, module='attn+mlp'):
        rows = rcsv(path)
        assert len(rows) == MODELS[model][1]
        vals = {int(r["layer"]): (float(r["score_positive"]) if module == 'attn+mlp' else max(0., float(r['attn_mean' if module == 'attn' else 'mlp_mean']))) for r in rows}
        assert set(vals) == set(range(len(rows)))
        for r in rows:
            assert math.isclose(float(r["score_positive"]), max(0., float(r["attn_mean"])) + max(0., float(r["mlp_mean"])), rel_tol=1e-7, abs_tol=1e-12)
        smooth = ns["moving_average"](np.array([vals[l] for l in range(len(vals))]), 3)
        region, threshold, high = ns["find_high_region"](smooth, .5)
        assert region is not None
        pre = ns["pre_candidates"](region[0], 3)
        ranking = ([int(r["layer"]) for r in sorted(rows, key=lambda r: (-float(r["score_positive"]), int(r["rank_positive"])))]
                   if module == 'attn+mlp' else [int(x) for x in np.argsort(-np.array([vals[i] for i in range(len(vals))]))])
        if expected is not None:
            assert ls(pre).replace(" ", "") == expected.replace(" ", ""), (ds, model, mode, pre, expected)
            CHECKS["visedit_pre_matches_previous_ledger"] += 1
        suffix = '' if module == 'attn+mlp' else '-' + module
        scope = 'next_token_argmax' if mode == 'model_pred' else token
        VIS.append(dict(dataset=ds, model=model, target=mode, attribution_scope=scope, module=module, token_rule=token, top3=pre, high_region=list(region), contribution_ranking=ranking, contribution_scores=[vals[l] for l in ranking], threshold=float(threshold), source=rel(path), historical=historical, status="done"))
        for rank, l in enumerate(ranking, 1):
            SCORES.append(dict(family=6, method="VisEdit-contribution-"+mode+suffix, dataset=ds, model=model, target=mode, attribution_scope=scope, module=module, flavor="historical" if historical else "current", layer=l, score=vals[l], rank=rank, source=rel(path)))
        RECS.append(dict(family=6, method="VisEdit-Pre-"+mode+suffix, dataset=ds, model=model, target=mode, attribution_scope=scope, module=module, flavor="historical" if historical else "current", top3=pre, status="done" if len(pre)==3 else "insufficient_layers", notes=token, source=rel(path)))

    existing = rcsv(ROOT / "outputs/visedit_contribution_rankings_20260927/visedit_candidates_and_contribution_top5.csv")
    for r in existing:
        ds, model = r["dataset"].lower(), DISPLAY_TO_SLUG[r["model"]]
        if not r["contribution_score_source"]:
            assert ds != "evqa-pilot500" and r["target_mode"] == "model_pred"
            folder = VISEDIT_MMKE / 'results' / ds / model
            if (folder / 'summary.json').exists():
                summary, protocol = rjson(folder / 'summary.json'), rjson(folder / 'protocol.json')
                assert summary['state'] == 'DONE' and summary['completed'] == summary['total'] == DATASETS[ds][1] and summary['failed'] == 0
                assert protocol['key_mode'] == 'model_pred'
                assert hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest() == summary['protocol_sha256']
                assert hashlib.sha256((folder/'contribution_layer.csv').read_bytes()).hexdigest() == summary['contribution_sha256']
                assert hashlib.sha256((folder/'recommendations.json').read_bytes()).hexdigest() == summary['recommendation_sha256']
                verified = rjson(folder/'local_verification.json')
                assert verified['passed'] and verified['summary_sha256'] == hashlib.sha256((folder/'summary.json').read_bytes()).hexdigest()
                variants = rjson(folder/'recommendations.json')
                for module in ['attn+mlp', 'attn', 'mlp']:
                    precision = protocol.get('torch_dtype', 'auto')
                    derive(ds, model, 'model_pred', folder/'contribution_layer.csv', f"模型下一 token argmax；{summary['completed']}/{summary['total']}；{module}；dtype={precision}", module=module)
                    VIS[-1]['torch_dtype'] = precision
                    assert VIS[-1]['contribution_ranking'] == variants[module]['ranking']
                    assert VIS[-1]['top3'] == variants[module]['pre_top3']
                CHECKS['visedit_mmke_model_pred_completed'] += 1
                continue
            missing(6, "VisEdit-Pre-model_pred", ds, model, "current", "现有 MMKE 旧侧归档为数据集 pred 字段，不是模型 model_pred；尚无该目标的贡献度", target="model_pred")
            VIS.append(dict(dataset=ds, model=model, target="model_pred", status="pending_source_data", top3=[], contribution_ranking=[], historical=False))
            continue
        path = ROOT / r["contribution_score_source"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == r["contribution_score_sha256"]
        derive(ds, model, r["target_mode"], path, r["token_rule"], r["top3"])
        if ds == 'evqa-pilot500' and r['target_mode'] == 'model_pred':
            config, summary = rjson(path.with_name('config.json')), rjson(path.with_name('summary.json'))
            assert config['key_mode'] == summary['key_mode'] == 'model_pred'
            assert config['sample_count'] == summary['sample_count'] == DATASETS[ds][1]
            for module in ['attn', 'mlp']:
                derive(ds, model, 'model_pred', path, r['token_rule'], module=module)
            CHECKS['visedit_evqa_model_pred_completed'] += 1
    for ds, folder in [("mmke-visual", "visual"), ("mmke-entity", "entity")]:
        for model in MODELS:
            p = ROOT / "downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600" / folder / "pred" / model / "contribution_layer.csv"
            cfg = rjson(p.with_name("config.json"))
            assert cfg["key_mode"] == "pred"
            derive(ds, model, "pred-field", p, "dataset_pred_first_token", historical=True)


def validate():
    keys = [(r["method"], r["dataset"], r["model"], r["flavor"]) for r in RECS]
    assert len(keys) == len(set(keys))
    for r in RECS:
        assert len(r["top3"]) == len(set(r["top3"])) <= 3
        if r["status"] == "pending_source_data":
            assert r["top3"] == []
        elif r.get("flavor") == "tukey":
            assert not set(r["top3"]) & set(r["outlier_layers"])
            assert r["top3"] == r["all_ranking"][:3]
    done_param = sum(r['space'] == 'parameter' and r['status'] == 'done' for r in ABLATION_GROUPS)
    done_visual = sum(r['space'] == 'visual' and r['status'] == 'done' for r in ABLATION_GROUPS)
    assert len(ABLATION_GROUPS) == 42
    assert len(AUDITS) == 147 + 3 * done_param + 2 * done_visual
    assert sum(r["status"] == "pending_source_data" for r in RECS) == 14 - CHECKS['visedit_mmke_model_pred_completed'] + 6 * (21 - done_param) + 4 * (21 - done_visual)
    assert CHECKS['visedit_evqa_model_pred_completed'] == 7
    assert sum(not v["historical"] and v["status"] == "done" for v in VIS) == 42 + 3 * CHECKS['visedit_mmke_model_pred_completed']
    assert sum(v["historical"] for v in VIS) == 14
    assert CHECKS["baseline_top3_matches_server_summary"] == 84
    assert CHECKS["raw_top3_matches_previous_formula_analysis"] == 77
    assert CHECKS['raw_top3_change_explained_by_explicit_zero_layer_policy']==7


def make_document(stamp, server_stamp):
    lines = ["# 七类定位方法：Top-3 推荐层、VisEdit 全层贡献度与消融", "",
             f"**整理时间：{stamp}（北京时间）。服务器原始定位产物核对时间：{server_stamp}。**", "",
             "本文件按本次指定的七类方法重新组织；每行对应一个模型与数据集。层号从 L0 开始，Top-3 保留推荐顺序。这里的定位分数不等于训练后的编辑性能；不计算或宣称当前 Top-3 并集总层数。真实训练评测见 [扫层结果总账](6location_7model_3datas_top_3_5_layers_outcome.md) 与 [SWeeplayers](SWeeplayers.md)。", "",
             "## 0. 目标与排序口径", "",
             "**当前研究决策（2026-09-29，按用户要求）：本阶段不做第八类视觉表征相似性方法（VisualTrack-Cos）。** none、alt、model_pred 三版已有结果仅作历史留档，不进入当前公式筛选、候选层补跑并集或新增实验计划；此前针对该方法的 9/15/75 层补跑建议均不执行。", "",
             "**当前核心目标：从第七类视觉表征梯度归因的 V01–V10 十个公式中，寻找在真实编辑效果上优于前六类方法的公式。** 前六类按本手册顺序为：中层先验、CMA、Perturb-KL、SaLEM、LGA、VisEdit；各目标、梯度对象和候选规则的已有版本分别比较。最终主公式由实验结果确定，暂不预设 V08 或历史主公式为胜者。", "",
             "比较采用相同候选预算、相同模型×数据集组合及可比训练评测配置，报告 Top-1、Best@3、Mean@3，同时分解 Rel、T-Gen、M-Gen、T-Loc、M-Loc 和 Average，结合提升幅度、胜/平/负及分数据集、分模型的一致性判断优势，不只看汇总胜率。缺失候选评测单列；沿用用户要求，PaliGemma 暂不进入编辑效果比较，其定位表保留。后续补算需求围绕前六类与第七类十式之间的实际比较缺口确定。", "",
              "- `alt` 是新知识目标；`model_pred` 是基础模型对原始图文对生成的完整输出。选择首 token、关键 token 或全部答案 token 属于归因范围，必须另行标明，不能改变 model_pred 的定义。数据集字段 `pred` 另列，不能直接更名为 `model_pred`。", 
             "- `Pre` 是 VisEdit 高贡献区域之前的候选层规则，不是目标字段 `pred`。贡献度最高的层与 Pre 推荐编辑层分别报告。",
             "- 历史 Ours 主公式为 `abs(S_v_cos) * S_v_new_norm`，不含深度权重；当前只作历史参照，不再预定为最终主公式。第七类 V01–V10 按逐样本公式计算后平均，与历史聚合公式严格区分；早期 Conflict、AbsDirection×depth² 仍仅留档。",
             "- 第七类 LGA 消融现按最新任务扩展为参数梯度、视觉表征两套；各自报告去旧强度、去新强度、去方向及 Raw / Tukey。只导入已完成且通过样本、来源哈希与历史统计复核的严格逐样本补算结果。",
             "- 定位样本总量：EVQA-pilot500 为 500，MMKE-visual 为 214，MMKE-entity 为 636；各方法有效样本数另列，不能把不同覆盖率当作完全相同实验。", "",
             "### 全层 Tukey 协议", "",
             "对每一个模型×数据集×公式，先取**全部层**的该公式有限分数计算 Q1、Q3，令 IQR=Q3−Q1；一次性剔除低于 `Q1−1.0×IQR` 或高于 `Q3+1.0×IQR` 的所有层，再对保留层降序排序取 Top-3。同分取较浅层；边界值保留；不足三层不回填异常层；不迭代重新估计四分位数。", "",
             "Tukey 系数 1.0 依据 [LGA 论文附录 A](https://arxiv.org/html/2602.20207v3#A1)。四分位数采用 NumPy `method=linear`，这是明确的实现约定。对 Ours 和消融公式应用相同流程是本次扩展，不称为论文原有实验。每个公式按自身分数过滤，不共享由其他公式确定的异常层掩码。", "",
             "Raw 不做 Tukey，不裁剪、不截尾、不丢弃有限的大梯度层。本次全层口径还保留原始记录中每组最后一层的有限零分及 `S_v_zero_grad` 标记；余弦按原脚本 epsilon 约定为 0，这些层通常因因果结构没有视觉梯度，不能把 0 解读为已测得有效梯度方向。Tukey 的四分位数也包含这些有限零分；这与历史先删零梯度层的 clean 口径不同。NaN/Inf 不转换成 0；当前所用视觉与参数原始层表全部为有限数。", "",
             "**† 表示原始记录标记为零视觉梯度的层。** 视觉 LGA 使用有符号内积，七个组合的其他层内积为负，因此零分末层在全层 Raw 中排在它们之前；这是本次不预先删层的直接结果，不能据此声称该层有有效梯度证据。具体与旧 clean 排名的变化见 [差异核对表](../../outputs/all_methods_recommendations_20260928/raw_vs_previous_clean.csv)。", "",
             "## 1. 中层先验", "", "中心为 `(L−1)/2`（ρ=0.5）；按到中心的距离升序，同距离取较浅层。三个数据集使用同一组推荐。", ""]
    lines.append(table(["模型", "模型标识", "层数", "Top-3（适用于三个数据集）"], [[label, m, n, top("Middle-Prior", "evqa-pilot500", m)] for m,(label,n) in MODELS.items()]))
    lines += ["## 2. CMA 因果恢复：model_pred 与 alt", "", "两版都保留。CMA-alt v1.3 使用完整 alt 序列、α=1.0/seed=2026；model_pred 使用完整模型响应、α={0.5,1,2}×seed={0,1,2}，按有效恢复对的 CR 均值排序。因此当前两版同时改变了目标与扰动协议，不能将差异只归因于目标类型。CMA 的稳定/不稳定指定位排名，不是 adapter 训练的 main/stable。", ""]
    lines.append(table(["数据集", "模型", "CMA-model_pred Top-3", "有效样本/总量；排名", "CMA-alt v1.3 Top-3", "有效样本/总量"], [[DATASETS[d][0],MODELS[m][0],top("CMA-model_pred",d,m),get("CMA-model_pred",d,m)["notes"],top("CMA-alt-v1.3",d,m),get("CMA-alt-v1.3",d,m)["notes"]] for d in DATASETS for m in MODELS]))
    fa = rjson(RAW / "cma_alt_formal_qwen_entity/cma_formal_top3_top5.json")
    lines += [f"另有 **MMKE-entity / Qwen2.5-VL 的 alt 多噪声多种子补算**：Top-3 为 {ls(parse_layers(fa['top3']))}，有效样本 {fa['valid_unique_samples']}/{fa['input_unique_samples']}，状态 `{fa['status']}`。这不是 21 组完整新版，单独保留，不覆盖上表的同版本序列。", "",
              "## 3. Perturb-KL：当前为 alt 序列条件版", "", "现有定位归档和脚本仅核实到 alt 版，没有 model_pred 版。实际扰动的是各层视觉 token 隐状态；在完整 alt 序列的 teacher-forcing 上下文及答案位置比较干净/扰动输出的全词表分布 KL，**不是直接扰动 alt 文本，也不是仅计算 alt token 的概率差**。当前按 `score_kl_robust` 排名（四种噪声强度×三次重复），直接选择该层，不做 Pre 偏移。", ""]
    lines.append(table(["数据集", "模型", "Perturb-KL-alt Top-3", "有效样本/总量"], [[DATASETS[d][0],MODELS[m][0],top("Perturb-KL-alt",d,m),get("Perturb-KL-alt",d,m)["notes"]] for d in DATASETS for m in MODELS]))
    lines += ["## 4. SaLEM：当前为新知识 alt 版", "", "现有归档和执行脚本只核实到 `target_new/alt` 版，没有旧知识 `model_pred` 版。按样本计算目标损失对配置指定 MLP/FFN 模块参数的梯度绝对值均值，再跨样本平均；对应字段 `layer_score`。参数模块范围遵从该实验的 p_track 配置，不等同于假定所有方法都对同一参数集合求梯度。", ""]
    lines.append(table(["数据集", "模型", "SaLEM-alt Top-3", "有效样本/总量"], [[DATASETS[d][0],MODELS[m][0],top("SaLEM-alt",d,m),get("SaLEM-alt",d,m)["notes"]] for d in DATASETS for m in MODELS]))
    lines += ["## 5. LGA：模型参数梯度与视觉表征梯度", "", "两版均使用 old=model_pred、new=alt 的有符号梯度内积。参数版在 MLP/FFN 权重参数空间计算；视觉版在候选插入接口的视觉隐状态/虚拟增量 ΔHᵥ 上计算，**不是对 adapter 权重求梯度，也没有预训练 adapter**。同组各层样本数一致时，内积均值与论文求和的排名及 Tukey 保留集合相同。", "", "视觉主公式直接读取 `S_v_dot = E[g_old·g_new]`。不能用 `E[cos]×E[旧范数]×E[新范数]` 代替。", ""]
    lines.append(table(["数据集", "模型", "参数 Raw Top-3", "参数 Tukey Top-3", "视觉 Raw Top-3", "视觉 Tukey Top-3", "参数/视觉有效样本"], [[DATASETS[d][0],MODELS[m][0],top("LGA-Param",d,m),top("LGA-Param",d,m,"tukey"),top("LGA-Visual",d,m),top("LGA-Visual",d,m,"tukey"),f"{get('LGA-Param',d,m)['sample_count']} / {get('LGA-Visual',d,m)['sample_count']}"] for d in DATASETS for m in MODELS]))
    lines += ["MMKE-entity / BLIP2 的视觉梯度仅覆盖 284/636（44.65%），原归档标记 low_coverage；该组的 Ours 和视觉 LGA 消融也使用同一批样本，保留推荐但须注明低覆盖，不能当作全量定位。参数 LGA 另有自己的有效样本集合。", ""]
    vis_done = CHECKS['visedit_mmke_model_pred_completed']
    lines += ["## 6. VisEdit：model_pred-NextTokenArgmax 关键 token 贡献度与 Pre Top-3", "", "贡献度取未经平滑的 `max(0, attn_mean)+max(0, mlp_mean)`，按高→低列出所有层，同分沿用原始 `rank_positive`。Pre 候选按三层滑动均值，阈值 mean+0.5×std（ddof=0），选最长高贡献连续区；等长选贡献和更大者，再取更浅者。若该区始于 s，则推荐 s−1、s−2、s−3，到 L0 为止。", "", "**当前 VisEdit 口径（2026-09-29，按用户确认）：以关键 token 计算贡献度，归因目标采用 `model_pred-NextTokenArgmax`。** 基础模型在原始图文输入末位置取下一 token logits 的 argmax，并在该预测位置归因；本节以这一口径核验和比较，不要求整段回答逐 token 归因。CMA/LGA 的完整回答目标与 VisEdit 的关键 token 归因范围分别注明。", "",
              "本节按三个数据集组织，每个数据集分别展示 attn、MLP、attn+MLP 三个分支。已有十四组 MMKE 数据集 `pred` 字段版保存在 [附录 A](#visedit-pred-archive)，独立留档。", "",
              f"**2026-09-29 关键 token 归因（NextTokenArgmax）：EVQA 已回填 7/7 组，MMKE 已回填 {vis_done}/14 组，合计 {7+vis_done}/21 组。** 每组分别列 attn、MLP、attn+MLP 的最高贡献层、贡献度 Top-5、全层排序及 Pre Top-3，已完成记录合计 {3*(7+vis_done)} 行。EVQA 的 attn、MLP 分支由已有完整层分数整理，无需重新运行模型。未完成组不使用部分样本替代全量。", "",
              "单模块排名与 Pre 使用 `max(0, attn_mean)` 或 `max(0, mlp_mean)`；联合版使用两者之和。先在样本间平均有符号贡献，再截取非负部分，沿用既有正贡献排序口径。逐层原始有符号均值仍保存在 CSV，MMKE 单模块有符号完整排名另存在 recommendations.json 的 signed_ranking；零贡献同分按原 NumPy argsort 规则列出，不能据此解释细微优劣。最高贡献层与高贡献区前置编辑候选是两种输出，分别报告。", ""]
    status_file = VISEDIT_MMKE / 'sync_status.json'
    repair_diagnosis = VISEDIT_MMKE / 'qwen_repair_bf16_v2/diagnosis.json'
    if repair_diagnosis.exists() and any(v.get('torch_dtype')=='bfloat16' and v['model']=='qwen2.5-vl-3b' for v in VIS):
        diagnosis = rjson(repair_diagnosis)
        lines += [f"**Qwen 数值修复：** 原加载器 `auto` 固定使用 FP16，失败为非有限输出。8 个诊断样本（含 6 个历史失败样本）中，FP16 非有限 {diagnosis['fp16_nonfinite']} 个，模型配置原生 BF16 非有限 {diagnosis['bf16_nonfinite']} 个。Qwen 的 MMKE 结果按 BF16 独立全量重算，仅全量完成且核验通过的组合回填下表；原 FP16 部分结果独立保留，不混入新均值。数据、提示词、贡献度与 Pre 规则沿用原版，精度变更单独记录，不宣称与 FP16 数值等价。见 [逐层诊断](../../outputs/visedit_model_pred_mmke_20260929/qwen_repair_bf16_v2/diagnosis.json)。", ""]
    if status_file.exists():
        status = rjson(status_file)
        worker = status.get('worker', {})
        lines += [f"服务器核验时间：{status['server_collected_at']}；队列状态：`{worker.get('state','unknown')}`。来源及逐样本复算：[同步核验](../../outputs/visedit_model_pred_mmke_20260929/sync_status.json)。", ""]
        incomplete = [g for g in status.get('groups', []) if g.get('state') == 'INCOMPLETE']
        if incomplete:
            lines += ['以下组合尚未全量完成，不生成正式排名，也不把缺失样本记为零分：', '']
            lines.append(table(['数据集','模型','已保存/总样本','记录失败数','状态'],
                               [[DATASETS[g['dataset']][0], MODELS[g['model']][0], f"{g['saved_samples']}/{g['total']}",g.get('failed','未记录'),'未完成，需排查'] for g in incomplete]))
    presence_path = ROOT / 'outputs/visedit_presence_recheck_20260928/server_audit.json'
    if presence_path.exists():
        presence = rjson(presence_path)
        dataset_audit = rjson(presence_path.with_name('dataset_pred_field_audit.json'))
        assert not presence['errors']
        mmke_pred = [r for r in presence['configs'] if '/mmke_module_contribution_20260607_150600/' in r['path'] and '/pred/' in r['path'] and r['path'].endswith('/config.json')]
        assert len(mmke_pred) == 14 and all(r['config']['key_mode'] == 'pred' for r in mmke_pred)
        assert not any(r['config'].get('key_mode') == 'model_pred' and ('mmke' in r['path'].lower() or 'mmke' in str(r['config']).lower()) for r in presence['configs'])
        assert next(r for r in dataset_audit if r['task']=='visual')['pred_empty'] == 214
        lines += [f"**历史存在性复核：{presence['time']}（服务器时钟）。** 当时检查了 {len(presence['folders'])} 个相关归档，MMKE 当时已有的旧侧归档采用数据集 `pred` 字段，尚缺模型下一 token 预测目标的贡献度。2026-09-29 的补算状态以上述新记录为准。详见 [历史复核证据](../../outputs/visedit_presence_recheck_20260928/README.md)。", ""]
    for ds in DATASETS:
        target = 'model_pred'
        section = list(DATASETS).index(ds) + 1
        lines += [f"### 6.{section} {DATASETS[ds][0]}", ""]
        for module_index, module in enumerate(['attn', 'mlp', 'attn+mlp'], 1):
            lines += [f"#### 6.{section}.{module_index} {module} 贡献度与高贡献区前置候选", ""]
            rr = []
            for model in MODELS:
                matches = [v for v in VIS if v['dataset']==ds and v['model']==model and v['target']==target and not v['historical'] and v.get('module','attn+mlp')==module and v['status']=='done']
                if not matches:
                    rr.append([MODELS[model][0], '待补', '待补', '待补', '待补', '待补', '待补'])
                    continue
                v = matches[0]
                label=MODELS[model][0]+('（BF16）' if v.get('torch_dtype')=='bfloat16' else '')
                rr.append([label, f"L{v['contribution_ranking'][0]}（{v['contribution_scores'][0]:.6g}）", ls(v['contribution_ranking'][:5]), ls(v['high_region']), ls(v['top3']), ls(v['contribution_ranking']), DATASETS[ds][1]])
            lines.append(table(['模型', '最高贡献层（分数）', '贡献度 Top-5', '高贡献区起止', 'Pre Top-3', '全层排序（高→低）', '有效样本'], rr))
    lines += ["## 7. Ours 主公式及两种梯度空间 LGA 消融：Raw / Tukey", "", "记每个样本的旧、新梯度范数为 aᵢ、bᵢ，方向余弦为 cᵢ；E 表示先在样本内计算后取均值。参数版的梯度对象是该层 MLP/FFN 权重（不含 bias；BLIP2 为 fc1/fc2 权重），与原参数 LGA 一致；视觉版为该层输出的视觉 token 隐状态/虚拟 ΔHᵥ。下面 LGA 四个公式分别在这两个空间独立计算。视觉侧 C=`S_v_cos`=E[cᵢ]，N=`S_v_new_norm`=E[bᵢ]，J=`S_v_joint_norm`=E[aᵢbᵢ]。", ""]
    lines.append(table(["版本","精确定义","现有数据可否计算"],[
        ["Ours 主公式","abs(C) × N（无深度）","可计算；保持既定层级聚合公式"],
        ["Ours 带符号方向（Ours-signed-direction）","C × N（无绝对值、无深度）","21 组已由原始层统计补算；独立 Raw / Tukey"],
        ["Ours 去方向","N","可计算"],["Ours 去强度","abs(C)","可计算"],
        ["LGA 主公式（两空间）","E[g_old·g_new] ≈ E[aᵢbᵢcᵢ]","原始内积均值已存在；≈ 仅因余弦分母 epsilon"],
        ["LGA 去旧强度（两空间）","E[bᵢcᵢ]","严格补算：逐样本 cos×新范数 后求均值"],
        ["LGA 去新强度（两空间）","E[aᵢcᵢ]","严格补算：逐样本 cos×旧范数 后求均值"],
        ["LGA 去方向（两空间）","E[aᵢbᵢ]","视觉已有 J；参数版随本次补算保存，不能用均值相乘"]]))
    lines += ["新增 Ours 带符号方向版仅将主公式的 abs(C) 替换成 C，按有符号分数降序推荐。它是 `E[c]×E[b]`，**不是**严格逐样本的 `E[c×b]`（LGA 去旧强度），不填补后者的待补状态。原始 LGA 是范数与带符号余弦共同形成的梯度内积，不是单独 cos。", "", "Ours 主公式中的 `abs(E[c])×E[b]` 不能改写成 `E[abs(c)×b]`。LGA 去单侧强度也不能用 C×N、C×旧范数均值替代；这些是不同的统计量。旧视觉日志没有保存必要交叉项，参数层均值同样不能识别它们，本次需复用原数据及冻结 model_pred 答案做前向、反向补算，无需训练 adapter。两个空间沿用各自原始有效样本集合；参数版原先排除归一化后 old=new 的样本，视觉版沿用原成功样本日志，不能声称两空间是完全相同样本的配对比较。", ""]
    completed = sum(g['status'] == 'done' for g in ABLATION_GROUPS)
    lines += [f"**严格补算导入进度：{completed}/42 个模型×数据集×梯度空间组合。** 只有整组完成、所有层样本数匹配、原始统计复现通过且逐样本重新聚合通过，才替换下表的待补。`待补` 不是零分或空排名。", ""]
    if (ABLATION / 'sync_status.json').exists():
        status = rjson(ABLATION / 'sync_status.json')
        lines += [f"本地同步时间：{status['synced_at']}；服务器采集时间：{status.get('server_collected_at', '本次未记录')}。两端分别记录自身时钟。", ""]
        labels = {'WAITING_PREVIOUS_EXPERIMENTS': '已排队，等待原扫层实验完成', 'WAITING_GPU_MEMORY': '等待足够空闲显存',
                  'WAITING_PROJECT_GPU_LOCK': '等待项目 GPU 锁', 'RUNNING_ABLATION': '正在补算', 'ALL_ASSIGNED_GROUPS_DONE': '所分配组合已全部完成',
                  'STOPPED_REQUIRES_INSPECTION': '已停止，需检查', 'FINISHED_WITH_FAILURES': '队列结束，部分组需检查'}
        for node, worker in status.get('workers', {}).items():
            state = worker.get('state', worker.get('status', 'unknown'))
            lines += [f"- {node}：{labels.get(state, state)}（`{state}`）。"]
        lines += [""]
    if (ABLATION / 'cohort_audit.json').exists():
        cohort = rjson(ABLATION / 'cohort_audit.json')
        assert cohort['passed'] == 42
        lines += ["[四十二组样本与原始层数核验](../../outputs/lga_two_spaces_ablation_20260928/cohort_audit.json)已通过；这是输入核验，不代表梯度补算已完成。", ""]
    for ds in DATASETS:
        lines += [f"### 7.{list(DATASETS).index(ds)+1}. {DATASETS[ds][0]}", "", "Ours 四版（每格为 Top-3；带符号方向版去掉主公式的绝对值）：", ""]
        lines.append(table(["模型","主公式 Raw","主公式 Tukey","带符号方向 Raw","带符号方向 Tukey","去方向 Raw","去方向 Tukey","去强度 Raw","去强度 Tukey"],[[MODELS[m][0],*[top(method,ds,m,flavor) for method in ['Ours-main','Ours-signed-direction','Ours-no-direction','Ours-no-strength'] for flavor in ['raw','tukey']]] for m in MODELS]))
        for space, prefix in [('参数梯度', 'LGA-Param'), ('视觉表征梯度', 'LGA-Visual')]:
            lines += [space + " LGA 四版：", ""]
            lines.append(table(["模型","LGA Raw","LGA Tukey","去方向 Raw","去方向 Tukey","去旧强度 Raw / Tukey","去新强度 Raw / Tukey"],
                [[MODELS[m][0], top(prefix,ds,m), top(prefix,ds,m,'tukey'), top(prefix+'-no-direction',ds,m), top(prefix+'-no-direction',ds,m,'tukey'),
                  top(prefix+'-no-old-strength',ds,m) + ' / ' + top(prefix+'-no-old-strength',ds,m,'tukey'),
                  top(prefix+'-no-new-strength',ds,m) + ' / ' + top(prefix+'-no-new-strength',ds,m,'tukey')] for m in MODELS]))
    lines += ["### 7.4 每组、每公式的剔除层", "", "以下列出全部 Tukey 剔除层，不只列原 Top-3 中被替换的层；Q1/Q3、上下界、保留层及完整精度分数见附录 B 的可机读文件。", ""]
    lines.append(table(["数据集","模型","参数 LGA","视觉 LGA","Ours 主公式","Ours 带符号方向","Ours 去方向","Ours 去强度","视觉 LGA 去方向"],[[DATASETS[d][0],MODELS[m][0],*[ls(get(method,d,m,'tukey')['outlier_layers']) for method in ['LGA-Param','LGA-Visual','Ours-main','Ours-signed-direction','Ours-no-direction','Ours-no-strength','LGA-Visual-no-direction']]] for d in DATASETS for m in MODELS]))
    lines += ["新增严格消融的全层 Tukey 剔除层（未完成组不生成过滤结论）：", ""]
    lines.append(table(['数据集', '模型', '参数去旧', '参数去新', '参数去方向', '视觉去旧', '视觉去新'], [
        [DATASETS[d][0], MODELS[m][0], *['待补' if get(method,d,m,'tukey')['status'] == 'pending_source_data' else ls(get(method,d,m,'tukey')['outlier_layers'])
          for method in ['LGA-Param-no-old-strength','LGA-Param-no-new-strength','LGA-Param-no-direction','LGA-Visual-no-old-strength','LGA-Visual-no-new-strength']]] for d in DATASETS for m in MODELS]))
    signed_performance = ROOT / "outputs/ours_signed_direction_20260928/recommendation_section.md"
    if signed_performance.exists():
        lines += [read(signed_performance), ""]
    visual_track_section = ROOT / "outputs/visual_track_cosine_20260928/targets_v2/recommendation_section.md"
    if visual_track_section.exists():
        lines += [read(visual_track_section), ""]
    lines += ["<a id=\"visedit-pred-archive\"></a>", "", "## 附录 A. 已存在的 VisEdit 数据集 pred 字段版（历史补充）", "", "以下十四组历史文件和推荐层确实存在：`key_mode=pred`，目标来自数据集 pred 字段，经 tokenizer 取首 token。它们与第 6 节 `model_pred-NextTokenArgmax` 采用不同目标，保留历史追溯；当前模型预测目标的推荐见第 6 节。", "",
              "**目标有效性补注（2026-09-28）：** 当前服务器原始 `visual_train.json` 的 214/214 条 pred 均为空；`entity_train.json` 的 636/636 条 pred 非空。历史脚本会把空 pred 加前导空格后送入 tokenizer，并不会进入 model_pred 的 argmax 分支。因此 MMKE-visual 的 pred 归档不能据此解释为有效旧知识或当前模型预测归因。此处只保留历史数值；本次核验的是当前数据文件，历史数据当时的字节内容未单独保存哈希。见 [字段核验](../../outputs/visedit_presence_recheck_20260928/dataset_pred_field_audit.json)。", ""]
    lines.append(table(["数据集","模型","Pre Top-3","全部层贡献度排序（高→低）"],[[DATASETS[v['dataset']][0],MODELS[v['model']][0],ls(v['top3']),ls(v['contribution_ranking'])] for v in VIS if v['historical']]))
    prefix = "../../outputs/all_methods_recommendations_20260928/"
    lines += ["## 附录 B. 来源、待补与复算", "", "- 当前优先事项是第七类 V01–V10 与前六类方法的真实编辑效果比较。第八类 VisualTrack-Cos 已退出本阶段实验计划，其历史缺层不再列为当前待补任务。", f"- VisEdit-model_pred-NextTokenArgmax：按关键 token 口径，EVQA 已回填 7/7 组，MMKE 已回填 {vis_done}/14 组；attn、MLP、attn+MLP 各覆盖 {7+vis_done}/21 个模型×数据集组合。余 {14-vis_done} 组待补；整段回答归因不列为本方法的缺项。", f"- 参数/视觉 LGA 去旧强度、去新强度：严格补算已导入 {completed}/42 组；参数去方向同时补存。未完成组合保持待补，完整状态见第 7 节。", "- Perturb-KL、SaLEM 当前仅报告已存在的 alt 版，不虚构 model_pred 结果。", "- 旧的深度加权 Ours、Perturb-KL-Pre、VisEdit FirstToken 历史表保存在原始总账备份；不混入本次指定的七类主表。", "",
              f"[全部推荐层 JSON]({prefix}recommendations.json) · [推荐层 CSV]({prefix}recommendations.csv) · [逐层分数与排名]({prefix}all_layer_scores.csv) · [Tukey 阈值与剔除层]({prefix}tukey_audit.csv) · [VisEdit 完整排序]({prefix}visedit_full_rankings.json)", "",
              f"[服务器产物来源与 SHA-256]({prefix}server_source_manifest.json) · [本次输入文件 SHA-256]({prefix}input_sha256.json) · [逐样本日志字段核验]({prefix}sample_schema_audit.json) · [复算验证]({prefix}verification.json) · [原始总账备份]({prefix}backups/6location_7model_3datas_top_3_5_layers_outcome.md)", "",
              "在项目根目录运行 `python scripts/build_all_method_recommendations.py` 可从本次已核验的本地原始分数重建本文件及总账方法目录。需要重新读取服务器原定位产物时，先运行 `python scripts/collect_recommendation_sources_20260928.py`。严格 LGA 补算完成后运行 `python scripts/lga_ablation_remote.py sync`：只读核验服务器逐样本结果、同步完整组合并重建本表，不启动 GPU 任务。", "",
              "[严格补算脚本](../../scripts/run_lga_two_space_ablation.py) · [服务器补算状态与同步证据](../../outputs/lga_two_spaces_ablation_20260928/sync_status.json)", ""]
    return "\n".join(lines)


def make_main(original, stamp):
    boundary = "## 3. 数据集分表"
    assert original.count(boundary) == 1
    tail = original[original.index(boundary):]
    sync = original.split("<!-- SWEEP_MAIN_SYNC_HEADER_START -->",1)[1].split("<!-- SWEEP_MAIN_SYNC_HEADER_END -->",1)[0]
    lines = ["# 定位方法目录与真实扫层结果", "", "<!-- SWEEP_MAIN_SYNC_HEADER_START -->"+sync+"<!-- SWEEP_MAIN_SYNC_HEADER_END -->", "",
             f"**方法目录整理时间：{stamp}（北京时间）。** 本次按七类重新组织方法与目标版本。全部 Top-3、VisEdit 全层贡献度排序、Ours/LGA 消融与全层 Tukey 结果统一见 [ALL_Methods_Recommends_layers.md](ALL_Methods_Recommends_layers.md)。定位统计与训练评测分别维护。", "",
             "## 0. 目录结构", "", "- 1. 统一口径与版本区别", "- 2. 本次指定的七类定位方法", "- 3. 历史数据集分表：冻结留档，不代表此次新候选并集或新方法比较", "- 4. 已完成真实扫层结果：保留逐层 main/stable、训练预算及评测来源", "- 5–6. 扫层使用方式与注意事项", "",
             "## 1. 统一口径与版本区别", "", "- 所有层号为 0-indexed。Top-3 保留分数/规则给出的先后次序，不将层号重新从小到大排列。", "- alt、新旧模型响应 model_pred、数据集 pred 字段严格区分。VisEdit 的 Pre 表示高贡献区域前置候选层，不是 pred 字段。", "- 历史 Ours 主公式 abs(S_v_cos)×S_v_new_norm 仅作参照；当前从第七类 V01–V10 十式中根据与前六类方法的真实编辑效果比较确定最终主公式，不预设胜者。第八类视觉表征相似性方法本阶段不做。", "- Raw 保留全部有限层分数，包括极端大值和已有有限零分；全层 Tukey 为每个组合、每个公式独立计算 Q1/Q3，剔除区间 [Q1−IQR,Q3+IQR] 外全部层后排序取 Top-3。κ=1.0，四分位数 linear，边界保留，不迭代、不回填异常层。", "- 方法未计算、数据不足和排名不足三层分别标记；不以 alt 替代 model_pred，不用层均值相乘假造未保存的逐样本交叉统计。", "- 本次不更新候选并集总层数和方法真实性能排名；main/stable 编辑结果继续分开，不按某层分数取较高版本。", "",
             "## 2. 本次指定的七类定位方法", ""]
    descriptions = [
        ("中层先验", "Middle-Prior；中心 (L−1)/2，按距离升序，同距取浅层；三个数据集共用。"),
        ("CMA 因果恢复", "分别报告 CMA-model_pred 与 CMA-alt v1.3，目标均为完整答案序列。两者目前噪声/种子协议也不同；Qwen/MMKE-entity 的 alt 多噪声补算独立列出，不混进旧二十一组版本。"),
        ("Perturb-KL", "当前仅核实 alt 序列条件版：扰动视觉隐状态，在 alt teacher-forcing 的答案位置计算输出分布 KL，按 score_kl_robust 选层；未找到 model_pred 版。"),
        ("SaLEM", "当前仅核实新知识 alt 版：样本目标损失对配置指定 MLP/FFN 参数的梯度绝对值均值，再跨样本平均；未找到旧知识 model_pred 版。"),
        ("LGA 两版", "模型参数 LGA：MLP/FFN 权重梯度内积；视觉表征 LGA：候选插入位置视觉隐状态/虚拟 ΔHᵥ 梯度内积，不是 adapter 参数梯度。两版均报告 Raw/Tukey Top-3，视觉内积直接读取 E[g_old·g_new]。"),
        ("VisEdit 关键 token 贡献度", f"按用户确认，VisEdit 对关键 token 归因，目标采用 model_pred-NextTokenArgmax。EVQA 已回填 7/7 组，MMKE 已回填 {CHECKS['visedit_mmke_model_pred_completed']}/14 组；每组分别提供 attn、MLP、attn+MLP 的 Top-5、最高贡献层、全层排序及 Pre Top-3，见推荐总表 6.1、6.2、6.3。整段回答归因不列为该方法的缺项。历史十四组数据集 pred 字段版独立留档，见 [附录 A](ALL_Methods_Recommends_layers.md#visedit-pred-archive)。"),
        ("Ours 主公式及两种梯度空间 LGA 消融", "Ours：abs(E[cos])×E[新范数]；新增带符号方向版 Ours-signed-direction=E[cos]×E[新范数]；去方向为 E[新范数]，去强度为 abs(E[cos])。新增版的 21 组 Raw/Tukey 推荐与已有编辑效果见推荐总表第 7 节。LGA 消融按最新任务同时做 MLP/FFN 权重参数版与视觉表征版：去方向为 E[旧范数×新范数]；去旧/去新分别为 E[cos×新范数] / E[cos×旧范数]，不能由层均值相乘替代。沿用各空间原数据、冻结 model_pred 答案与梯度对象严格逐样本补算，完成并通过复核后回填推荐层总表；未完成明确待补。每个版本分别列 Raw 与全层 Tukey。"),
    ]
    for i,(name,desc) in enumerate(descriptions,1):
        lines += [f"### 2.{i} {name}", "", desc, "", f"Top-3、来源和版本细节见 [推荐层总表第 {i} 节](ALL_Methods_Recommends_layers.md)。", ""]
    lines += ["### 2.8 数据来源与历史保留", "", "本次基于服务器原始层分数和本地已核验贡献度重新生成，附可重复脚本、逐层分数、过滤边界及 SHA-256。详见 [生成与验证产物](../../outputs/all_methods_recommendations_20260928/verification.json)。原第 1–2 节的历史 Top-5、Pre 消融、早期 Ours 等完整保存在 [整理前备份](../../outputs/all_methods_recommendations_20260928/backups/6location_7model_3datas_top_3_5_layers_outcome.md)。", "", 
             "> **以下第 3 节是历史冻结比较，版本和候选集合未随本次方法重排重算；其中的并集数字、完成率与方法优劣不能作为本次新表结论。第 4 节真实扫层明细原样保留。**", ""]
    visual_track_index = ROOT / "outputs/visual_track_cosine_20260928/targets_v2/main_index_section.md"
    if visual_track_index.exists():
        note = next(i for i,s in enumerate(lines) if s.startswith("> **以下第 3 节是历史冻结比较"))
        lines[note:note] = [read(visual_track_index), ""]
    return "\n".join(lines) + "\n" + tail, hashlib.sha256(tail.encode()).hexdigest()


def preserve_user_visual10_section(generated, current):
    """The user-approved 10-formula section is maintained by its own verified renderer."""
    if '<!-- OURS_VISUAL10_RESULTS_BEGIN -->' not in current:
        return generated
    import re
    pattern = r'(?ms)^## 7\..*?(?=^## (?:8\.|附录)|\Z)'
    old = re.search(pattern, current)
    assert old and '<!-- OURS_VISUAL10_RESULTS_END -->' in old.group(), 'Incomplete protected section'
    assert re.search(pattern, generated), 'Generated section 7 missing'
    generated = re.sub(pattern, lambda _: old.group(), generated, count=1)
    new_bullet = next(line for line in current.splitlines() if line.startswith('- 第七类现以用户'))
    generated = re.sub(r'(?m)^- 第七类 LGA 消融.*$', lambda _: new_bullet, generated)
    return generated


def main():
    OUT.mkdir(exist_ok=True)
    manifest = rjson(OUT / "server_source_manifest.json")
    for r in manifest['records']:
        assert r['status']=='ok'
        assert hashlib.sha256((OUT/r['local']).read_bytes()).hexdigest()==r['sha256']
    baseline_sources()
    visual_sources()
    cross_strength_sources()
    visedit_sources()
    validate()
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    backups = OUT / "backups"
    backups.mkdir(exist_ok=True)
    for p in [MAIN,DOC]:
        backup=backups/p.name
        if not backup.exists():backup.write_bytes(p.read_bytes())
    original = MAIN.read_bytes().decode('utf-8')
    document = make_document(stamp, manifest['collected_at'])
    new_main, tail_sha = make_main(original, stamp)
    writejson(OUT/'recommendations.json',dict(updated_at=stamp, records=RECS))
    writecsv(OUT/'recommendations.csv', RECS)
    writecsv(OUT/'all_layer_scores.csv', SCORES)
    writecsv(OUT/'tukey_audit.csv', AUDITS)
    writecsv(OUT/'raw_vs_previous_clean.csv', RAW_CHANGES)
    writejson(OUT/'visedit_full_rankings.json', VIS)
    writejson(OUT/'input_sha256.json', SOURCES)
    document = preserve_user_visual10_section(document, DOC.read_text(encoding='utf-8'))
    DOC.write_bytes(document.encode('utf-8'))
    MAIN.write_bytes(new_main.encode('utf-8'))
    actual_tail=MAIN.read_bytes().decode('utf-8').split('## 3. 数据集分表',1)[1]
    assert hashlib.sha256(('## 3. 数据集分表'+actual_tail).encode()).hexdigest()==tail_sha
    verification=dict(updated_at=stamp,checks=dict(CHECKS),recommendation_rows=len(RECS),tukey_groups=len(AUDITS),source_files=len(SOURCES),
                      status_counts=dict(Counter(r['status'] for r in RECS)), all_visual_raw_layers=618,
                      main_sections_3_through_6_unchanged_sha256=tail_sha,
                      no_model_execution=True,no_server_mutation=True,
                      strict_ablation_groups=ABLATION_GROUPS,
                      pending=dict(Counter(r['method'] for r in RECS if r['status']=='pending_source_data')))
    writejson(OUT/'verification.json', verification)
    print(json.dumps(verification,ensure_ascii=False))


if __name__ == '__main__':
    main()
