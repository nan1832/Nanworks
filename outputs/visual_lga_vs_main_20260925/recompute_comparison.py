"""Read-only source analysis: visual-hidden-state LGA dot vs the fixed main formula."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from statistics import mean
import csv
import hashlib
import json
import math
import re
import sys
import warnings
from scipy.stats import spearmanr, kendalltau

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
RAW = ROOT / "md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores"
OLD = ROOT / "md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/formula_topk_all_21.csv"
SOURCE = ROOT / "md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md"
MANUAL = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
MODELS = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}
REV = {v: k for k, v in MODELS.items()}
DATASETS = {"evqa-pilot500": (500, 2093), "mmke-visual": (214, 293), "mmke-entity": (636, 954)}
FORMULAS = ("M_dot", "M_abscos_x_newn")
NAMES = {"M_dot": "视觉LGA（M_dot）", "M_abscos_x_newn": "当前主公式"}
sources = {}

def read_text(path):
    sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path.read_text(encoding="utf-8-sig")

def read_csv(path):
    return list(csv.DictReader(read_text(path).splitlines()))

def write_csv(name, rows):
    if not rows:
        return
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def fmt_layers(values):
    return ",".join("L" + str(v) for v in values)

def fnum(value):
    return "—" if value is None else f"{value:.3f}"

def signed(value):
    return "—" if value is None else f"{value:+.3f}"

archived = {(r["dataset"], r["model"], r["formula"]): r for r in read_csv(OLD) if r["formula"] in FORMULAS}
rankings, meta, score_maps = {}, {}, {}
ranking_rows, candidate_rows = [], []
raw_files = sorted(RAW.glob("*/*/ours_direct_layer_scores.csv"))
assert len(raw_files) == 21
verified_rank_lists = 0
for path in raw_files:
    ds, model = path.parts[-3:-1]
    rows = read_csv(path)
    counts = {int(float(r["n_request"])) for r in rows}
    assert len(counts) == 1, (path, counts)
    count = counts.pop()
    meta[(ds, model)] = {"valid_samples": count, "total_samples": DATASETS[ds][0], "coverage": count / DATASETS[ds][0]}
    valid = []
    for r in rows:
        if r["S_v_zero_grad"].strip().lower() == "true" or r["invalid_reason"].strip():
            continue
        if not r["visual_token_start"].strip() or not r["visual_token_end"].strip():
            continue
        dot, cos, norm = [float(r[c]) for c in ("S_v_dot", "S_v_cos", "S_v_new_norm")]
        if not all(math.isfinite(v) for v in (dot, cos, norm)):
            continue
        valid.append((int(r["layer"]), dot, cos, norm))
    for formula in FORMULAS:
        scored = [(layer, dot if formula == "M_dot" else abs(cos) * norm)
                  for layer, dot, cos, norm in valid]
        scored.sort(key=lambda x: (-x[1], x[0]))
        layers = [x[0] for x in scored]
        key = ds, model, formula
        rankings[key] = layers
        score_maps[key] = dict(scored)
        old = archived[key]
        assert int(old["valid_samples"]) == count
        for k in (3, 5):
            assert fmt_layers(layers[:k]) == old[f"top{k}"], (key, k)
            verified_rank_lists += 1
        candidate_rows.append({"dataset": ds, "model": model, "formula": formula,
                               **meta[(ds, model)], "top1": fmt_layers(layers[:1]),
                               "top3": fmt_layers(layers[:3]), "top5": fmt_layers(layers[:5]),
                               "raw_score_file": str(path)})
        for rank, (layer, score) in enumerate(scored, 1):
            ranking_rows.append({"dataset": ds, "model": model, "formula": formula,
                                 "layer": layer, "score": score, "rank": rank,
                                 "LGA_sum_equivalent": score * count if formula == "M_dot" else "",
                                 **meta[(ds, model)]})

# Read the current detailed evaluation table, preserving profile/replicate identity.
records = []
active = False
ds = model = None
for lineno, line in enumerate(read_text(SOURCE).splitlines(), 1):
    if line.startswith("## 4. "):
        active = True
    elif active and line.startswith("## "):
        break
    if not active:
        continue
    if line.startswith("### 4."):
        ds = line.split(" ", 2)[2].lower()
    elif line.startswith("#### "):
        model = REV[line[5:]]
    elif line.startswith("| L"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        assert len(c) == 14
        match = re.fullmatch(r"L(\d+)(-\d+)?", c[0])
        assert match
        if c[12] in ("", "-", "—"):
            continue
        average = float(c[12])
        assert 0 <= average <= 100
        records.append({"dataset": ds, "model": model, "layer": int(match[1]),
                        "replicate": bool(match[2]), "config": c[1], "average": average,
                        "eval_samples": int(c[6]), "status": c[13],
                        "source": str(SOURCE), "source_line": lineno})

groups = defaultdict(list)
for r in records:
    if not r["replicate"]:
        groups[(r["dataset"], r["model"], r["layer"])].append(r)
priority = {"main": 3, "main/legacy": 2, "main/recovered-early": 1, "stable": 0}
selected = {}
for key, group in groups.items():
    group.sort(key=lambda x: priority.get(x["config"], -1), reverse=True)
    assert len(group) == 1 or priority.get(group[0]["config"], -1) != priority.get(group[1]["config"], -1), key
    selected[key] = group[0]

# Add only independently verified local archival results; never pick a larger score.
verification_paths = [
    ROOT / "outputs/localization_audit_20260922/evqa_llava_tmp.json",
    ROOT / "outputs/localization_audit_20260922/evqa_llava_shared.json",
    ROOT / "outputs/localization_audit_20260922/entity_llava_tmp.json",
    ROOT / "outputs/localization_audit_20260922/entity_llava_shared.json",
    ROOT / "outputs/handoff_evqa_llava_3178538_20260924/verify_tmp.json",
    ROOT / "outputs/handoff_evqa_llava_3178538_20260924/verify_shared.json",
]
overlap_checks, supplements = 0, []
for path in verification_paths:
    if not path.exists():
        continue
    content = json.loads(read_text(path))
    for r in content.get("layers", []):
        e = r.get("evaluation") or {}
        if not r.get("complete") or r.get("errors") or e.get("status") != "EVAL_DONE":
            continue
        ds = r["dataset"].lower()
        assert e["eval_samples"] == DATASETS[ds][1]
        key = ds, r["model"], int(r["layer"])
        average = float(e["Average"])
        if key in selected:
            assert abs(selected[key]["average"] - average) < 0.011, (path, key, selected[key]["average"], average)
            overlap_checks += 1
        else:
            new = {"dataset": ds, "model": r["model"], "layer": int(r["layer"]),
                   "replicate": False, "config": "main", "average": average,
                   "eval_samples": e["eval_samples"],
                   "status": "EVAL_DONE_LOCAL_ARCHIVE_VERIFIED",
                   "source": str(path), "source_line": ""}
            selected[key] = new
            supplements.append(new)

def exclusions(r, profile):
    reasons = []
    if r["config"] == "stable":
        reasons.append("stable_only")
    if r["config"] not in priority:
        reasons.append("nonstandard_config")
    if re.search("FAILED|NO_EVAL|NONCONVERGENT|DIAGNOSTIC", r["status"], re.I):
        reasons.append("diagnostic_or_incomplete")
    if r["eval_samples"] != DATASETS[r["dataset"]][1]:
        reasons.append("evaluation_protocol_size")
    if profile == "clean":
        if r["config"] == "main/recovered-early":
            reasons.append("early_training")
        if re.search("NUMERIC|NONFINITE|STALL", r["status"], re.I):
            reasons.append("numeric_or_stall_flag")
    return reasons

outcome_rows = []
for key, r in sorted(selected.items()):
    outcome_rows.append({**r, "clean_exclusion": ";".join(exclusions(r, "clean")),
                         "historical_exclusion": ";".join(exclusions(r, "historical"))})

metrics = {}
correlations = []
for profile in ("clean", "historical"):
    pool = {key: r for key, r in selected.items() if not exclusions(r, profile)}
    for ds, model in sorted(meta):
        measured = {layer: r["average"] for (d, m, layer), r in pool.items() if (d, m) == (ds, model)}
        reference = max(measured.values()) if measured else None
        for formula in FORMULAS:
            key = ds, model, formula
            ranks, scores = rankings[key], score_maps[key]
            common = sorted(set(measured) & set(scores))
            corr = {"profile": profile, "dataset": ds, "model": model, "formula": formula,
                    "coverage": meta[(ds, model)]["coverage"], "layer_count": len(common),
                    "spearman": None, "kendall": None}
            if len(common) >= 5:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    rho = float(spearmanr([scores[l] for l in common], [measured[l] for l in common]).statistic)
                    tau = float(kendalltau([scores[l] for l in common], [measured[l] for l in common]).statistic)
                corr["spearman"] = rho if math.isfinite(rho) else None
                corr["kendall"] = tau if math.isfinite(tau) else None
            correlations.append(corr)
            for k in (1, 3, 5):
                chosen = ranks[:k]
                missing = [l for l in chosen if l not in measured]
                complete = len(chosen) == k and not missing
                values = [measured[l] for l in chosen if l in measured]
                best = max(values) if complete else None
                row = {"profile": profile, "dataset": ds, "model": model, "formula": formula, "k": k,
                       "coverage": meta[(ds, model)]["coverage"], "candidates": fmt_layers(chosen),
                       "evaluated_count": len(values), "complete": complete,
                       "missing_or_excluded": fmt_layers(missing), "best": best,
                       "mean": mean(values) if complete else None,
                       "best_layer": fmt_layers([l for l in chosen if complete and abs(measured[l] - best) < 1e-9]),
                       "measured_reference": reference,
                       "regret": reference - best if complete else None,
                       "hit": int(abs(reference - best) < 1e-9) if complete else None,
                       "measured_layers": len(measured)}
                metrics[(profile, ds, model, formula, k)] = row

paired_rows, summaries, missing_rows = [], [], []
for profile in ("clean", "historical"):
    for k in (1, 3, 5):
        paired = []
        for ds, model in sorted(meta):
            dot = metrics[(profile, ds, model, "M_dot", k)]
            ours = metrics[(profile, ds, model, "M_abscos_x_newn", k)]
            eligible = dot["complete"] and ours["complete"] and meta[(ds, model)]["coverage"] >= 0.8
            row = {"profile": profile, "dataset": ds, "model": model, "k": k,
                   "coverage": meta[(ds, model)]["coverage"], "paired_eligible": eligible,
                   "dot_candidates": dot["candidates"], "ours_candidates": ours["candidates"],
                   "dot_best": dot["best"], "ours_best": ours["best"],
                   "dot_mean": dot["mean"], "ours_mean": ours["mean"],
                   "dot_regret": dot["regret"], "ours_regret": ours["regret"],
                   "dot_hit": dot["hit"], "ours_hit": ours["hit"],
                   "dot_missing": dot["missing_or_excluded"], "ours_missing": ours["missing_or_excluded"],
                   "delta_best_ours_minus_dot": ours["best"] - dot["best"] if eligible else None,
                   "delta_mean_ours_minus_dot": ours["mean"] - dot["mean"] if eligible else None}
            paired_rows.append(row)
            if eligible:
                paired.append(row)
            if profile == "clean" and k == 3:
                for formula, item in (("M_dot", dot), ("M_abscos_x_newn", ours)):
                    for l in rankings[(ds, model, formula)][:k]:
                        record = selected.get((ds, model, l))
                        reasons = ["not_in_local_verified_outcomes"] if record is None else exclusions(record, "clean")
                        if reasons:
                            missing_rows.append({"dataset": ds, "model": model, "formula": formula, "layer": l,
                                                 "reason": ";".join(reasons), "source": record["source"] if record else ""})
        summary = {"profile": profile, "k": k, "paired_combinations": len(paired)}
        for label in ("dot", "ours"):
            for field in ("best", "mean", "regret", "hit"):
                summary[f"{label}_{field}"] = mean(r[f"{label}_{field}"] for r in paired) if paired else None
        delta = [r["delta_best_ours_minus_dot"] for r in paired]
        summary.update({"ours_best_wins": sum(x > 1e-9 for x in delta),
                        "best_ties": sum(abs(x) <= 1e-9 for x in delta),
                        "ours_best_losses": sum(x < -1e-9 for x in delta),
                        "mean_delta_best": mean(delta) if paired else None,
                        "mean_delta_candidate_average": mean(r["delta_mean_ours_minus_dot"] for r in paired) if paired else None})
        summaries.append(summary)

corr_summaries = []
for profile in ("clean", "historical"):
    dot = {(r["dataset"], r["model"]): r for r in correlations if r["profile"] == profile and r["formula"] == "M_dot"}
    ours = {(r["dataset"], r["model"]): r for r in correlations if r["profile"] == profile and r["formula"] == "M_abscos_x_newn"}
    keys = [key for key in dot if dot[key]["coverage"] >= 0.8 and dot[key]["spearman"] is not None and ours[key]["spearman"] is not None]
    assert all(dot[key]["layer_count"] == ours[key]["layer_count"] for key in keys)
    corr_summaries.append({"profile": profile, "paired_combinations": len(keys),
                           "dot_spearman": mean(dot[key]["spearman"] for key in keys),
                           "ours_spearman": mean(ours[key]["spearman"] for key in keys),
                           "dot_kendall": mean(dot[key]["kendall"] for key in keys),
                           "ours_kendall": mean(ours[key]["kendall"] for key in keys),
                           "dot_positive_spearman": sum(dot[key]["spearman"] > 0 for key in keys),
                           "ours_positive_spearman": sum(ours[key]["spearman"] > 0 for key in keys)})

# Verify fixed main-formula candidates and scores against the frozen comparison.
fair = read_csv(ROOT / "outputs/formal7_cma_modelpred_v2_method_fair_rows_20260914.csv")
frozen_checks = []
for row in fair:
    if row["method"] != "Ours-Direct" or row["topk"] != "3":
        continue
    ds, model = row["dataset"].lower(), REV[row["model"]]
    r = metrics[("historical", ds, model, "M_abscos_x_newn", 3)]
    assert r["candidates"] == row["layers"]
    if r["complete"]:
        assert abs(r["best"] - float(row["best"])) < 0.011
        assert abs(r["mean"] - float(row["mean"])) < 0.011
    frozen_checks.append({"dataset": ds, "model": model, "complete": r["complete"]})

write_csv("candidate_topk_21x2.csv", candidate_rows)
write_csv("layer_scores_and_ranks.csv", ranking_rows)
write_csv("verified_outcomes_with_flags.csv", outcome_rows)
write_csv("method_metrics.csv", list(metrics.values()))
write_csv("paired_comparison.csv", paired_rows)
write_csv("paired_summary.csv", summaries)
write_csv("layerwise_correlations.csv", correlations)
write_csv("correlation_summary.csv", corr_summaries)
write_csv("top3_missing_or_excluded.csv", missing_rows)

for path, digest in sources.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
same3 = sum(rankings[(d,m,"M_dot")][:3] == rankings[(d,m,"M_abscos_x_newn")][:3] for d,m in meta)
same3set = sum(set(rankings[(d,m,"M_dot")][:3]) == set(rankings[(d,m,"M_abscos_x_newn")][:3]) for d,m in meta)
manifest = {"generated_at": datetime.now().astimezone().isoformat(),
            "scope": "Existing gradients and locally verified outcomes only; no new model inference or training.",
            "formula_dot": "mean_i <grad_H L_old, grad_H L_new>; sum differs by layer-constant n_request only",
            "formula_main": "abs(mean_i cos_i) * mean_i new_norm_i",
            "verified_archived_topk_lists": verified_rank_lists,
            "frozen_main_checks": frozen_checks,
            "same_ordered_top3": same3, "same_top3_set": same3set,
            "verified_outcome_overlaps": overlap_checks, "added_archival_outcomes": supplements,
            "coverage_threshold": 0.8, "clean_exclusion_policy": "stable, early training, diagnostic/nonconvergent, numeric/nonfinite/stall flagged, mismatched evaluation size",
            "sources": [{"path": p, "sha256": h} for p,h in sources.items()],
            "summaries": summaries, "correlation_summaries": corr_summaries}
(OUT/"verification.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

main3 = next(r for r in summaries if r["profile"] == "clean" and r["k"] == 3)
lines = [
    "# 视觉隐藏状态版Golden Layers与当前主公式：实际重算结果",
    "",
    "计算日期：2026-09-25。本次复用21份原始视觉梯度CSV，重新生成候选并匹配本地已核验编辑结果，没有重新训练或运行模型推理。",
    "",
    f'**结果：在{main3["paired_combinations"]}个双方Top-3均可比的组合上，视觉LGA的Best@3为{main3["dot_best"]:.3f}，当前主公式为{main3["ours_best"]:.3f}，主公式平均高{main3["mean_delta_best"]:.3f}分。现有结果未显示直接改用视觉LGA内积可以整体优于当前主公式。**',
    "",
    f'但主公式的Best@3胜/平/负为{main3["ours_best_wins"]}/{main3["best_ties"]}/{main3["ours_best_losses"]}，大部分组合没有差异；该均值优势主要由少数差异组合贡献，不能解释为稳定全面胜出。',
    "",
    "视觉LGA为 M_dot = mean_i <g_old_visual, g_new_visual>；原文求和式在同组有效样本数固定时产生相同排序。当前主公式为 M_abscos_x_newn = abs(mean_i cos_i) × mean_i new_norm_i。两者均直接推荐post-block适配器位置，不做Pre偏移。",
    "",
    f"重新计算的两公式Top-3/Top-5共{verified_rank_lists}份有序列表全部匹配原归档。21组中{same3}组Top-3有序列表相同，{same3set}组Top-3集合相同。",
    "",
    "## 1. 同组合、同预算的主比较",
    "",
    "主汇总要求：定位样本覆盖≥80%，两公式各自Top-K全部具备可比编辑结果；排除stable-only、提前结束训练、诊断/不收敛、数值异常或stall标记。保留这些记录的历史敏感性结果另存CSV。未评测或被排除的结果不按0分，不把部分候选最佳分数当成完整Best@K。",
    "",
    "| K | 共同完整组合 | 视觉LGA Best@K | 主公式 Best@K | 主公式增量 | 视觉LGA Mean@K | 主公式 Mean@K | 主公式Best胜/平/负 |",
    "|---:|---:|---:|---:|---:|---:|---:|---|",
]
for r in summaries:
    if r["profile"] == "clean":
        lines.append(f'| {r["k"]} | {r["paired_combinations"]} | {fnum(r["dot_best"])} | {fnum(r["ours_best"])} | {signed(r["mean_delta_best"])} | {fnum(r["dot_mean"])} | {fnum(r["ours_mean"])} | {r["ours_best_wins"]}/{r["best_ties"]}/{r["ours_best_losses"]} |')
lines += ["", "不同K对应的共同完整组合可能不同，不能直接把跨行分数变化解释为增加预算的收益。Best@K衡量候选集合潜力；Top-1直接使用评分首位层。以上均为已有单次运行的描述性比较，未据此宣布统计显著或全局最优。", "", "## 2. 全部21组Top-3", "",
          "分数为五项Average；差值=主公式Best@3−视觉LGA Best@3。单边完整结果可展示，但只有双方完整且覆盖达标才进入配对汇总。", "",
          "| 数据 | 模型 | 视觉LGA Top-3 | 主公式Top-3 | 视觉LGA最佳 | 主公式最佳 | 配对差值 | 状态 |",
          "|---|---|---|---|---:|---:|---:|---|"]
for r in paired_rows:
    if r["profile"] != "clean" or r["k"] != 3:
        continue
    state = "可比" if r["paired_eligible"] else (
        f'低覆盖{r["coverage"]:.1%}' if r["coverage"] < .8 else
        f'视觉LGA缺/排除：{r["dot_missing"] or "无"}；主公式缺/排除：{r["ours_missing"] or "无"}')
    lines.append(f'| {r["dataset"]} | {r["model"]} | {r["dot_candidates"]} | {r["ours_candidates"]} | {fnum(r["dot_best"])} | {fnum(r["ours_best"])} | {signed(r["delta_best_ours_minus_dot"])} | {state} |')
lines += ["", "## 3. 全部共同已测层的排序预测质量", "",
          "在每个模型—数据集内，使用两公式共同有效、且有可比实际评测的全部层计算相关性，不仅使用Top-3。每组至少5个层，随后对组合等权平均；它仍是已测范围内相关性，不能代表尚未测量的所有层。", "",
          "| 口径 | 共同组合 | 视觉LGA平均Spearman | 主公式平均Spearman | 视觉LGA平均Kendall | 主公式平均Kendall |",
          "|---|---:|---:|---:|---:|---:|"]
for r in corr_summaries:
    lines.append(f'| {r["profile"]} | {r["paired_combinations"]} | {fnum(r["dot_spearman"])} | {fnum(r["ours_spearman"])} | {fnum(r["dot_kendall"])} | {fnum(r["ours_kendall"])} |')
lines += ["", "## 4. 版本与可复核文件", "",
          "- 梯度来源为21组已保存的视觉梯度长表，Qwen使用其中已归档的修复版本。不是将层均值梯度相乘，也不是对旧/新范数均值与余弦均值作乘积来替代M_dot。",
          "- MMKE实体／BLIP2的当前梯度文件只有284/636样本（44.65%），保留候选但排除主汇总。该覆盖属于本次读取的具体梯度文件。",
          "- 评测采用现有第一阶段口径：E-VQA 2093、MMKE视觉293、MMKE实体954。未混用实体955版本。",
          "- 来源包括当前详细评测表及2026-09-22/24的本地验收归档；新增归档只补缺失项，重叠记录检查一致，不按较高分挑选运行。原始L18-2重复结果不替换L18。",
          "- 本次参照为同组合、同口径全部已测位置。它不同于旧七方法Top-3并集参照，故本报告Regret/Hit不能与旧汇总直接拼接；Best/Mean仍使用同一层的实际分数。",
          "- 本次Top-3双方完整集合为13组，不是此前七方法表的17组；不能拿本报告某方法的13组平均与旧表17组平均作对照。",
          "- Top-5仅5组双方完整，且这些已覆盖条件的结果相同；不能外推其余16组。",
          "- 现有梯度和编辑结果曾参与方法探索，本报告属于事后对照分析，不是冻结公式后的独立确认实验。",
          "- 历史配置与低覆盖敏感性限制保留在明细中。当前结果不补造未完成层，也未恢复暂停的实验。",
          "",
          "输出文件：candidate_topk_21x2.csv（21组两公式Top-1/3/5）；layer_scores_and_ranks.csv（逐层得分与排名）；paired_comparison.csv（逐组合配对）；paired_summary.csv（同集合汇总）；layerwise_correlations.csv及correlation_summary.csv（相关性）；top3_missing_or_excluded.csv（缺项与排除原因）；verified_outcomes_with_flags.csv（编辑结果来源）；verification.json（哈希与校验）；recompute_comparison.py（复算脚本）。",
          ""]
(OUT/"视觉LGA与主公式_重算报告.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"top3":main3,"correlations":corr_summaries,"same_top3":same3,
                  "added_outcomes":len(supplements),"all_summaries":summaries,
                  "different_complete_top3":[r for r in paired_rows if r["profile"]=="clean" and r["k"]==3 and r["paired_eligible"] and r["dot_candidates"]!=r["ours_candidates"]]},
                 ensure_ascii=False,indent=2))
