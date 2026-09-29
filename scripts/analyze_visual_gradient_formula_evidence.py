#!/usr/bin/env python3
"""Recompute and evaluate the 11 visual-gradient layer formulas.

The script uses only the checked-in raw layer scores and accepted full-eval rows
from the project ledger.  It deliberately distinguishes measured-layer evidence
from a full-layer oracle and keeps PaliGemma main/stable configurations separate.
"""

import csv
import hashlib
import json
import math
import random
import re
import statistics
from collections import OrderedDict, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
METHOD_DOC = ROOT / "md/Location/6edit_layer_localization_candidate_methods_简洁说明版.md"
PACKAGE = ROOT / "md/Location/VisualGradient_11formula_analysis_files_20260720"
RAW_ROOT = PACKAGE / "raw_layer_scores"
QWEN_REFERENCE = PACKAGE / "existing_outputs/qwen_7base_4ours_candidate_topk_summary.csv"
OURS4_REFERENCE = PACKAGE / "existing_outputs/ours_4metrics_7models_3datasets_topk_summary.csv"
OUTPUT = PACKAGE / "analysis_outputs_20260731"

DATASET_DISPLAY = {
    "evqa-pilot500": "EVQA-pilot500",
    "mmke-visual": "MMKE-visual",
    "mmke-entity": "MMKE-entity",
}
MODEL_DISPLAY = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}
MODEL_KEY = {value: key for key, value in MODEL_DISPLAY.items()}
EXPECTED_GRADIENT_SAMPLES = {"evqa-pilot500": 500, "mmke-visual": 214, "mmke-entity": 636}


def number(row, field):
    return float(row[field])


FORMULAS = OrderedDict(
    [
        ("M_dot", ("base7", "S_v_dot", lambda r: number(r, "S_v_dot"))),
        ("M_cos", ("base7", "S_v_cos", lambda r: number(r, "S_v_cos"))),
        ("M_new_norm", ("base7", "S_v_new_norm", lambda r: number(r, "S_v_new_norm"))),
        ("M_pos_ratio", ("base7", "S_v_positive_ratio", lambda r: number(r, "S_v_positive_ratio"))),
        ("M_conflict", ("base7", "S_v_conflict", lambda r: number(r, "S_v_conflict"))),
        (
            "M_newn_x_1mcos",
            ("base7", "S_v_new_norm * (1-S_v_cos)", lambda r: number(r, "S_v_new_norm") * (1 - number(r, "S_v_cos"))),
        ),
        (
            "M_abscos_x_newn",
            ("base7", "abs(S_v_cos) * S_v_new_norm", lambda r: abs(number(r, "S_v_cos")) * number(r, "S_v_new_norm")),
        ),
        (
            "Ours-Direct-Conflict",
            (
                "ours4",
                "max(0,-S_v_cos) * S_v_new_norm * S_v_depth2",
                lambda r: max(0.0, -number(r, "S_v_cos")) * number(r, "S_v_new_norm") * number(r, "S_v_depth2"),
            ),
        ),
        (
            "Ours-AbsDirection-Direct",
            (
                "ours4",
                "abs(S_v_cos) * S_v_new_norm * S_v_depth2",
                lambda r: abs(number(r, "S_v_cos")) * number(r, "S_v_new_norm") * number(r, "S_v_depth2"),
            ),
        ),
        (
            "Ours-NoDirection-Direct",
            ("ours4", "S_v_new_norm * S_v_depth2", lambda r: number(r, "S_v_new_norm") * number(r, "S_v_depth2")),
        ),
        (
            "Ours-1MinusCos-Direct",
            (
                "ours4",
                "(1-S_v_cos) * S_v_new_norm * S_v_depth2",
                lambda r: (1 - number(r, "S_v_cos")) * number(r, "S_v_new_norm") * number(r, "S_v_depth2"),
            ),
        ),
    ]
)
BASE7 = list(FORMULAS)[:7]
NON_STRICT10 = [name for name in FORMULAS if name != "Ours-Direct-Conflict"]
BASELINES = [
    "Middle-Prior-Direct",
    "VisEdit-Contrib-Pre-KeyToken",
    "SaLEM-Alt-Direct",
    "LGA-Param-Direct-AltModelPred",
    "Perturb-KL-Direct-AltSeq",
    "CMA-Direct",
]
TARGET = "M_abscos_x_newn"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_layers(value):
    return [int(item[1:]) for item in value.split(",") if re.fullmatch(r"L\d+", item.strip())]


def split_table(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_outcomes():
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    rows = []
    in_total = False
    dataset = None
    pali_stable = False
    for line_no, line in enumerate(lines, 1):
        if line.startswith("### 4.0 "):
            in_total = True
            continue
        if line.startswith("### 4.1 "):
            break
        if not in_total:
            continue
        if line.startswith("#### "):
            heading = line[5:].strip()
            if heading in DATASET_DISPLAY.values():
                dataset = heading.lower()
                pali_stable = False
        if not dataset or not line.startswith("| "):
            continue
        cells = split_table(line)
        if len(cells) != 13 or cells[0] == "Model":
            continue
        model, status = cells[0], cells[12]
        if model == "paligemma-3b" and ("STABLE" in status or "FAILED_STABLE" in status):
            pali_stable = True
        try:
            layer = int(cells[1][1:])
            average = float(cells[11])
        except (ValueError, IndexError):
            continue
        variant = "stable" if model == "paligemma-3b" and pali_stable else "main"
        rows.append(
            {
                "dataset": dataset,
                "model": model,
                "layer": layer,
                "average": average,
                "status": status,
                "variant": variant,
                "source_line": line_no,
            }
        )

    # Section 4.0 intentionally omits the historical EVQA/BLIP2 table.  Add its
    # accepted primary L0..L30 rows from section 4.1; L18-2 is a replicate and
    # is kept out of the primary layer map to avoid selecting the better repeat.
    in_blip = False
    in_blip_table = False
    for line_no, line in enumerate(lines, 1):
        if line.startswith("### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B"):
            in_blip = True
            continue
        if in_blip and line.startswith("### 4.2 "):
            break
        if not in_blip:
            continue
        if line.startswith("| Layer | Ckpt Epoch"):
            in_blip_table = True
            continue
        if in_blip_table and not line.startswith("|"):
            if rows:
                in_blip_table = False
            continue
        if not in_blip_table or line.startswith("|---"):
            continue
        cells = split_table(line)
        if len(cells) != 10 or cells[0] == "L18-2":
            continue
        try:
            layer = int(cells[0][1:])
            average = float(cells[9])
        except (ValueError, IndexError):
            continue
        rows.append(
            {
                "dataset": "evqa-pilot500",
                "model": "blip2-opt-2.7b",
                "layer": layer,
                "average": average,
                "status": "TRAIN_DONE_SECTION_4_1",
                "variant": "main",
                "source_line": line_no,
            }
        )

    seen = set()
    for row in rows:
        key = (row["dataset"], row["model"], row["variant"], row["layer"])
        if key in seen:
            raise RuntimeError("duplicate outcome row: %r" % (key,))
        seen.add(key)
    return rows


def outcome_profiles(rows):
    profiles = {"main": {}, "main_clean": {}, "pali_stable_sensitivity": {}}
    for row in rows:
        key = (row["dataset"], row["model"], row["layer"])
        is_pali = row["model"] == "paligemma-3b"
        if not is_pali or row["variant"] == "main":
            profiles["main"][key] = row
            if not re.search(r"NUMERIC|NONFINITE", row["status"]):
                profiles["main_clean"][key] = row
        if not is_pali or row["variant"] == "stable":
            profiles["pali_stable_sensitivity"][key] = row
    return profiles


def raw_row_is_valid(row):
    try:
        return (
            row["S_v_zero_grad"].strip().lower() != "true"
            and not row["invalid_reason"].strip()
            and bool(row["visual_token_start"].strip())
            and bool(row["visual_token_end"].strip())
            and math.isfinite(number(row, "S_v_new_norm"))
            and math.isfinite(number(row, "S_v_cos"))
        )
    except (KeyError, ValueError):
        return False


def derive_formula_rankings():
    topk = {}
    ranking_rows = []
    source_meta = {}
    paths = sorted(RAW_ROOT.glob("*/*/ours_direct_layer_scores.csv"))
    if len(paths) != 21:
        raise RuntimeError("expected 21 raw score files, found %d" % len(paths))
    for path in paths:
        dataset, model = path.parts[-3], path.parts[-2]
        raw = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
        valid_samples = int(float(raw[0]["n_request"]))
        total_samples = EXPECTED_GRADIENT_SAMPLES[dataset]
        source_meta[(dataset, model)] = {
            "valid_samples": valid_samples,
            "total_samples": total_samples,
            "coverage": valid_samples / total_samples,
            "raw_score_file": str(path.relative_to(ROOT)).replace("\\", "/"),
        }
        for formula, (family, expression, scorer) in FORMULAS.items():
            scored = []
            for row in raw:
                if not raw_row_is_valid(row):
                    continue
                try:
                    score = scorer(row)
                    layer = int(row["layer"])
                except (KeyError, ValueError):
                    continue
                if not math.isfinite(score):
                    continue
                if formula == "Ours-Direct-Conflict" and score <= 0:
                    continue
                scored.append((score, layer))
            scored.sort(key=lambda item: (-item[0], item[1]))
            layers = [layer for _score, layer in scored]
            topk[(dataset, model, formula)] = layers
            for rank, (score, layer) in enumerate(scored, 1):
                ranking_rows.append(
                    {
                        "dataset": dataset,
                        "model": model,
                        "family": family,
                        "formula": formula,
                        "expression": expression,
                        "layer": layer,
                        "score": score,
                        "rank": rank,
                        "valid_samples": valid_samples,
                        "total_samples": total_samples,
                        "coverage": valid_samples / total_samples,
                    }
                )
    return topk, ranking_rows, source_meta


def verify_existing_references(topk):
    qwen_checked = 0
    with QWEN_REFERENCE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            dataset = row["dataset"].lower()
            key = (dataset, "qwen2.5-vl-3b", row["method"])
            expected = parse_layers(row["clean_top5"])
            actual = topk[key][:5]
            if actual != expected:
                raise RuntimeError("Qwen Top-5 mismatch %r: %r != %r" % (key, actual, expected))
            qwen_checked += 1
    if qwen_checked != 33:
        raise RuntimeError("expected 33 Qwen reference rows, found %d" % qwen_checked)

    ours4_checked = 0
    with OURS4_REFERENCE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            dataset = row["Dataset"].lower()
            key = (dataset, MODEL_KEY[row["Model"]], row["Metric"])
            expected = parse_layers(row["Top-5"])
            actual = topk[key][:5]
            if actual != expected:
                raise RuntimeError("Ours4 Top-5 mismatch %r: %r != %r" % (key, actual, expected))
            ours4_checked += 1
    if ours4_checked != 84:
        raise RuntimeError("expected 84 Ours4 reference rows, found %d" % ours4_checked)


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + end - 1) / 2.0 + 1.0
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def pearson(left, right):
    if len(left) < 2:
        return None
    left_mean, right_mean = statistics.mean(left), statistics.mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - left_mean) ** 2 for x in left) * sum((y - right_mean) ** 2 for y in right)
    )
    return numerator / denominator if denominator else None


def spearman(left, right):
    return pearson(average_ranks(left), average_ranks(right))


def kendall_tau_b(left, right):
    concordant = discordant = ties_left = ties_right = 0
    for first in range(len(left)):
        for second in range(first + 1, len(left)):
            dx, dy = left[first] - left[second], right[first] - right[second]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_left += 1
            elif dy == 0:
                ties_right += 1
            elif dx * dy > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt(
        (concordant + discordant + ties_left) * (concordant + discordant + ties_right)
    )
    return (concordant - discordant) / denominator if denominator else None


def ndcg(predicted_layers, outcomes, k):
    if len(predicted_layers) != k or len(outcomes) < k or any(layer not in outcomes for layer in predicted_layers):
        return None
    values = list(outcomes.values())
    low, high = min(values), max(values)
    if high == low:
        return 1.0

    def relevance(value):
        return (value - low) / (high - low)

    def dcg(seq):
        return sum(relevance(value) / math.log2(index + 2) for index, value in enumerate(seq))

    predicted = [outcomes[layer] for layer in predicted_layers]
    ideal = sorted(values, reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    return dcg(predicted) / ideal_dcg if ideal_dcg else 1.0


def evaluate_candidates(profile, profile_rows, topk, rankings, source_meta):
    outcome_by_combo = defaultdict(dict)
    for (dataset, model, layer), row in profile_rows.items():
        outcome_by_combo[(dataset, model)][layer] = row["average"]
    score_by_formula = defaultdict(dict)
    for row in rankings:
        score_by_formula[(row["dataset"], row["model"], row["formula"])][row["layer"]] = row["score"]

    metrics = []
    for dataset, model in sorted(source_meta):
        outcomes = outcome_by_combo.get((dataset, model), {})
        oracle = max(outcomes.values()) if outcomes else None
        oracle_layers = [layer for layer, value in outcomes.items() if value == oracle] if outcomes else []
        for formula in FORMULAS:
            candidates = topk[(dataset, model, formula)]
            row = {
                "profile": profile,
                "dataset": dataset,
                "model": model,
                "formula": formula,
                "gradient_coverage": source_meta[(dataset, model)]["coverage"],
                "measured_layer_count": len(outcomes),
                "measured_oracle": oracle,
                "measured_oracle_layers": ",".join("L%d" % layer for layer in oracle_layers),
                "top1": "L%d" % candidates[0] if candidates else "",
                "top3": ",".join("L%d" % layer for layer in candidates[:3]),
                "top5": ",".join("L%d" % layer for layer in candidates[:5]),
            }
            for k in (1, 3, 5):
                selected = candidates[:k]
                measured = [outcomes[layer] for layer in selected if layer in outcomes]
                full = len(selected) == k and len(measured) == k
                row["candidate_count_%d" % k] = len(selected)
                row["measured_count_%d" % k] = len(measured)
                row["full_%d" % k] = full
                row["partial_best_%d" % k] = max(measured) if measured else None
                row["partial_mean_%d" % k] = statistics.mean(measured) if measured else None
                row["best_%d" % k] = max(measured) if full else None
                row["mean_%d" % k] = statistics.mean(measured) if full else None
                row["regret_%d" % k] = oracle - max(measured) if full and oracle is not None else None
                row["hit_%d" % k] = bool(set(selected) & set(oracle_layers)) if full else None
                row["ndcg_%d" % k] = ndcg(selected, outcomes, k) if full else None
            scores = score_by_formula[(dataset, model, formula)]
            common_layers = sorted(set(scores) & set(outcomes))
            if len(common_layers) >= 3:
                score_values = [scores[layer] for layer in common_layers]
                outcome_values = [outcomes[layer] for layer in common_layers]
                row["correlation_n"] = len(common_layers)
                row["spearman"] = spearman(score_values, outcome_values)
                row["kendall"] = kendall_tau_b(score_values, outcome_values)
            else:
                row["correlation_n"] = len(common_layers)
                row["spearman"] = None
                row["kendall"] = None
            metrics.append(row)
    return metrics


def mean_or_none(values):
    values = [value for value in values if value is not None]
    return statistics.mean(values) if values else None


def median_or_none(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def summarize_formulas(metrics):
    grouped = defaultdict(list)
    for row in metrics:
        grouped[(row["profile"], row["formula"])].append(row)
    summary = []
    for (profile, formula), rows in sorted(grouped.items()):
        eligible = [row for row in rows if row["gradient_coverage"] >= 0.8 and row["measured_layer_count"] > 0]
        item = {
            "profile": profile,
            "formula": formula,
            "family": FORMULAS[formula][0],
            "eligible_combo_n": len(eligible),
            "available_combo_n": sum(bool(row["candidate_count_1"]) for row in eligible),
            "top1_measured_n": sum(row["full_1"] for row in eligible),
            "top1_perf_mean": mean_or_none([row["best_1"] for row in eligible]),
            "correlation_combo_n": sum(row["spearman"] is not None for row in eligible),
            "spearman_mean": mean_or_none([row["spearman"] for row in eligible]),
            "spearman_median": median_or_none([row["spearman"] for row in eligible]),
            "spearman_positive_n": sum(row["spearman"] is not None and row["spearman"] > 0 for row in eligible),
            "kendall_mean": mean_or_none([row["kendall"] for row in eligible]),
        }
        for k in (3, 5):
            full = [row for row in eligible if row["full_%d" % k]]
            item["top%d_full_n" % k] = len(full)
            item["top%d_full_rate" % k] = len(full) / len(eligible) if eligible else None
            item["top%d_layer_coverage" % k] = (
                sum(row["measured_count_%d" % k] for row in eligible) / (k * len(eligible)) if eligible else None
            )
            item["best_%d_mean" % k] = mean_or_none([row["best_%d" % k] for row in full])
            item["mean_%d_mean" % k] = mean_or_none([row["mean_%d" % k] for row in full])
            item["regret_%d_mean" % k] = mean_or_none([row["regret_%d" % k] for row in full])
            item["hit_%d_rate" % k] = mean_or_none([1.0 if row["hit_%d" % k] else 0.0 for row in full])
            item["ndcg_%d_mean" % k] = mean_or_none([row["ndcg_%d" % k] for row in full])
        summary.append(item)
    return summary


def exact_sign_p(wins, losses):
    n = wins + losses
    if n == 0:
        return None
    tail = sum(math.comb(n, index) for index in range(0, min(wins, losses) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_ci(values, seed, iterations=10000):
    if not values:
        return None, None
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        means.append(statistics.mean(values[rng.randrange(len(values))] for _index in range(len(values))))
    means.sort()
    return means[int(0.025 * iterations)], means[int(0.975 * iterations) - 1]


def paired_summary(left_rows, right_rows, k, seed, require_right_coverage=True):
    shared = []
    right_by_combo = {(row["dataset"], row["model"]): row for row in right_rows}
    for left in left_rows:
        key = (left["dataset"], left["model"])
        right = right_by_combo.get(key)
        if (
            right
            and left["gradient_coverage"] >= 0.8
            and (not require_right_coverage or right.get("gradient_coverage", 1.0) >= 0.8)
            and left["full_%d" % k]
            and right["full_%d" % k]
        ):
            shared.append((left, right))
    regret_improvement = [right["regret_%d" % k] - left["regret_%d" % k] for left, right in shared]
    mean_improvement = [left["mean_%d" % k] - right["mean_%d" % k] for left, right in shared]
    best_improvement = [left["best_%d" % k] - right["best_%d" % k] for left, right in shared]
    wins = sum(value > 1e-12 for value in regret_improvement)
    ties = sum(abs(value) <= 1e-12 for value in regret_improvement)
    losses = sum(value < -1e-12 for value in regret_improvement)
    regret_low, regret_high = bootstrap_ci(regret_improvement, seed)
    mean_low, mean_high = bootstrap_ci(mean_improvement, seed + 1)
    return {
        "paired_n": len(shared),
        "regret_improvement_mean": mean_or_none(regret_improvement),
        "regret_improvement_ci95_low": regret_low,
        "regret_improvement_ci95_high": regret_high,
        "mean_perf_improvement": mean_or_none(mean_improvement),
        "mean_perf_improvement_ci95_low": mean_low,
        "mean_perf_improvement_ci95_high": mean_high,
        "best_perf_improvement": mean_or_none(best_improvement),
        "regret_wins": wins,
        "regret_ties": ties,
        "regret_losses": losses,
        "sign_test_p_two_sided": exact_sign_p(wins, losses),
        "shared_combos": ";".join("%s/%s" % (left["dataset"], left["model"]) for left, _right in shared),
    }


def formula_pairwise(metrics):
    main = [row for row in metrics if row["profile"] == "main"]
    by_formula = defaultdict(list)
    for row in main:
        by_formula[row["formula"]].append(row)
    result = []
    for k in (3, 5):
        for index, formula in enumerate(FORMULAS):
            if formula == TARGET:
                continue
            item = {"k": k, "target": TARGET, "comparison": formula}
            item.update(paired_summary(by_formula[TARGET], by_formula[formula], k, 20260731 + 100 * k + index))
            result.append(item)
    return result


def common_set_summary(metrics):
    by_key = {(row["profile"], row["dataset"], row["model"], row["formula"]): row for row in metrics}
    combos = sorted(set((row["profile"], row["dataset"], row["model"]) for row in metrics))
    groups = {"base7": BASE7, "non_strict10": NON_STRICT10, "all11": list(FORMULAS)}
    output = []
    for profile in sorted(set(row["profile"] for row in metrics)):
        profile_combos = [(d, m) for p, d, m in combos if p == profile]
        for k in (3, 5):
            for group_name, formulas in groups.items():
                common = []
                for dataset, model in profile_combos:
                    rows = [by_key[(profile, dataset, model, formula)] for formula in formulas]
                    if all(row["gradient_coverage"] >= 0.8 and row["full_%d" % k] for row in rows):
                        common.append((dataset, model))
                for formula in formulas:
                    rows = [by_key[(profile, dataset, model, formula)] for dataset, model in common]
                    output.append(
                        {
                            "profile": profile,
                            "k": k,
                            "comparison_set": group_name,
                            "formula": formula,
                            "common_combo_n": len(common),
                            "best_mean": mean_or_none([row["best_%d" % k] for row in rows]),
                            "mean_perf": mean_or_none([row["mean_%d" % k] for row in rows]),
                            "regret_mean": mean_or_none([row["regret_%d" % k] for row in rows]),
                            "hit_rate": mean_or_none([1.0 if row["hit_%d" % k] else 0.0 for row in rows]),
                            "ndcg_mean": mean_or_none([row["ndcg_%d" % k] for row in rows]),
                            "common_combos": ";".join("%s/%s" % key for key in common),
                        }
                    )
    return output


def parse_baselines():
    rows = []
    in_section = False
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.startswith("### 2.11 "):
            in_section = True
            continue
        if line.startswith("### 2.12 "):
            break
        if not in_section or not line.startswith("| "):
            continue
        cells = split_table(line)
        if len(cells) != 7 or cells[0] == "Dataset" or cells[2] not in BASELINES:
            continue
        status = cells[6]
        coverage = None
        match = re.search(r"coverage=([0-9.]+)", status)
        if match:
            coverage = float(match.group(1))
        else:
            match = re.search(r"n=(\d+)/(\d+)", status)
            if match:
                coverage = int(match.group(1)) / int(match.group(2))
        reliability = "eligible"
        if coverage is not None and coverage < 0.8:
            reliability = "low_candidate_coverage"
        if cells[2] == "VisEdit-Contrib-Pre-KeyToken" and cells[0] == "EVQA-pilot500":
            reliability = "historical_firsttoken_not_strict_keytoken"
        rows.append(
            {
                "dataset": cells[0].lower(),
                "model": MODEL_KEY[cells[1]],
                "method": cells[2],
                "top3": parse_layers(cells[4]),
                "top5": parse_layers(cells[5]),
                "candidate_coverage": coverage,
                "reliability": reliability,
                "status": status,
            }
        )
    if len(rows) != 21 * len(BASELINES):
        raise RuntimeError("expected %d baseline rows, found %d" % (21 * len(BASELINES), len(rows)))
    return rows


def evaluate_baselines(baselines, main_profile):
    outcome_by_combo = defaultdict(dict)
    for (dataset, model, layer), row in main_profile.items():
        outcome_by_combo[(dataset, model)][layer] = row["average"]
    metrics = []
    for base in baselines:
        outcomes = outcome_by_combo.get((base["dataset"], base["model"]), {})
        oracle = max(outcomes.values()) if outcomes else None
        item = dict(base)
        item["gradient_coverage"] = base["candidate_coverage"] if base["candidate_coverage"] is not None else 1.0
        item["measured_layer_count"] = len(outcomes)
        for k in (3, 5):
            selected = base["top%d" % k]
            measured = [outcomes[layer] for layer in selected if layer in outcomes]
            full = len(selected) == k and len(measured) == k
            item["full_%d" % k] = full
            item["best_%d" % k] = max(measured) if full else None
            item["mean_%d" % k] = statistics.mean(measured) if full else None
            item["regret_%d" % k] = oracle - max(measured) if full and oracle is not None else None
        metrics.append(item)
    return metrics


def baseline_pairwise(formula_metrics, baseline_metrics):
    target_rows = [row for row in formula_metrics if row["profile"] == "main" and row["formula"] == TARGET]
    result = []
    for k in (3, 5):
        for index, method in enumerate(BASELINES):
            comparison = [row for row in baseline_metrics if row["method"] == method]
            all_stats = paired_summary(
                target_rows,
                comparison,
                k,
                20260731 + 1000 + 100 * k + index,
                require_right_coverage=False,
            )
            reliable = [row for row in comparison if row["reliability"] == "eligible"]
            strict_stats = paired_summary(target_rows, reliable, k, 20260731 + 2000 + 100 * k + index)
            item = {"k": k, "target": TARGET, "comparison": method}
            item.update({"all_" + key: value for key, value in all_stats.items()})
            item.update({"strict_" + key: value for key, value in strict_stats.items()})
            result.append(item)
    return result


def formula_overlap(topk):
    output = []
    combos = sorted(set((dataset, model) for dataset, model, _formula in topk))
    for other in FORMULAS:
        if other == TARGET:
            continue
        for k in (1, 3, 5):
            identical = 0
            jaccards = []
            for dataset, model in combos:
                left = topk[(dataset, model, TARGET)][:k]
                right = topk[(dataset, model, other)][:k]
                identical += left == right
                union = set(left) | set(right)
                jaccards.append(len(set(left) & set(right)) / len(union) if union else 1.0)
            output.append(
                {
                    "comparison": other,
                    "k": k,
                    "combo_n": len(combos),
                    "identical_ordered_n": identical,
                    "identical_ordered_rate": identical / len(combos),
                    "jaccard_mean": statistics.mean(jaccards),
                }
            )
    return output


def write_csv(path, rows):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value, digits=3):
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return ("%%.%df" % digits) % value if isinstance(value, float) else str(value)


def make_report(outcomes, profiles, formula_summary, common_summary, pairwise, baseline_pairs, overlap, metrics, topk, source_meta):
    main_summary = {row["formula"]: row for row in formula_summary if row["profile"] == "main"}
    main_pair3 = [row for row in pairwise if row["k"] == 3]
    base_common3 = [
        row
        for row in common_summary
        if row["profile"] == "main" and row["k"] == 3 and row["comparison_set"] == "base7"
    ]
    corr_order = sorted((main_summary[name] for name in FORMULAS), key=lambda row: (-(row["spearman_mean"] or -999), row["formula"]))
    sensitivity_top = {}
    for profile in ("main", "main_clean", "pali_stable_sensitivity"):
        candidates = [row for row in formula_summary if row["profile"] == profile]
        candidates.sort(key=lambda row: (-(row["spearman_mean"] or -999), row["formula"]))
        sensitivity_top[profile] = candidates[:3]
    target_summary = main_summary[TARGET]
    new_norm_overlap = next(row for row in overlap if row["comparison"] == "M_new_norm" and row["k"] == 3)
    target_vs_new = next(row for row in main_pair3 if row["comparison"] == "M_new_norm")
    target_metrics = [row for row in metrics if row["profile"] == "main" and row["formula"] == TARGET]
    target_corr = {(row["dataset"], row["model"]): row["spearman"] for row in target_metrics}
    new_corr = {
        (row["dataset"], row["model"]): row["spearman"]
        for row in metrics
        if row["profile"] == "main" and row["formula"] == "M_new_norm"
    }
    corr_differences = [
        target_corr[key] - new_corr[key]
        for key in target_corr
        if target_corr[key] is not None and new_corr.get(key) is not None
    ]
    corr_wins = sum(value > 1e-12 for value in corr_differences)
    corr_ties = sum(abs(value) <= 1e-12 for value in corr_differences)
    corr_losses = sum(value < -1e-12 for value in corr_differences)
    missing = []
    for row in target_metrics:
        candidates = topk[(row["dataset"], row["model"], TARGET)][:3]
        measured = set()
        for (dataset, model, layer), _outcome in profiles["main"].items():
            if (dataset, model) == (row["dataset"], row["model"]):
                measured.add(layer)
        absent = [layer for layer in candidates if layer not in measured]
        if absent:
            missing.append((row["dataset"], row["model"], candidates, absent))

    lines = [
        "# 视觉梯度 11 公式与定位基线的当前证据分析",
        "",
        "生成日期：2026-07-31",
        "",
        "## 1. 结论先行",
        "",
        "基于当前**已完成独立 test/eval 的 measured-layer 结果**，`M_abscos_x_newn = abs(S_v_cos) × S_v_new_norm` 与 `M_new_norm` 构成明显领先组；若必须冻结一个下一阶段主公式，当前证据可把 `M_abscos_x_newn` 作为略占优的首选，但现有数据还不足以声称它已经被证明为全局唯一最优或统计显著优于所有基线。准确表述应是：",
        "",
        "> 在当前已测候选层范围内，`M_abscos_x_newn` 的平均跨组合排序相关性略高，且在与基础公式的 Top-3 两两 regret 比较中未观察到劣势，因此暂选为下一阶段主公式；它与 `M_new_norm` 实质上仍接近并列，结论属于 measured-layer evidence。",
        "",
        "## 2. 数据与防止选择性报告的规则",
        "",
        "- 公式候选由 21 份逐层原始 CSV 统一重算，不使用只覆盖 Qwen 的现成 11 公式表替代其他模型。",
        "- Qwen 3 数据集 × 11 公式共 33 行、以及全 21 组 × 4 个深度指标共 84 行 Top-5，均与既有标准结果逐行一致，作为重算实现校验。",
        "- 只使用主表中有完整正式评测的层；失败、无 eval、仅 checkpoint 的层不进入性能值。",
        "- PaliGemma 主配置用于主分析，stable 配置只做敏感性分析，不把两种配置逐层挑高值混合。",
        "- EVQA/BLIP2 使用 4.1 的主结果，`L18-2` 是重复结果，不用“择优复评”替换主 L18。",
        "- 梯度候选 coverage < 0.8 的组合不进入强汇总；当前主要是 MMKE-entity/BLIP2（284/636）。",
        "- Oracle 仅为已测层中的最高 Average，即 measured-layer oracle，不声称是全层 oracle。",
        "",
        "输入哈希：",
        "",
        "- `6edit_layer_localization_candidate_methods_简洁说明版.md`: `%s`" % sha256(METHOD_DOC),
        "- `6location_7model_3datas_top_3_5_layers_outcome.md`: `%s`" % sha256(LEDGER),
        "",
        "## 3. 11 公式主配置汇总",
        "",
        "| Formula | Top3完整组合 | Best@3均值 | Mean@3均值 | Regret@3均值↓ | Spearman均值↑ | Spearman中位数 | 正相关组合 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for formula in FORMULAS:
        row = main_summary[formula]
        lines.append(
            "| `%s` | %s | %s | %s | %s | %s | %s | %s/%s |"
            % (
                formula,
                row["top3_full_n"],
                fmt(row["best_3_mean"]),
                fmt(row["mean_3_mean"]),
                fmt(row["regret_3_mean"]),
                fmt(row["spearman_mean"]),
                fmt(row["spearman_median"]),
                row["spearman_positive_n"],
                row["correlation_combo_n"],
            )
        )
    lines.extend(
        [
            "",
            "注意：上表每个公式的 Top-3 完整组合数不同，不能仅按 Best@3 均值横向宣布胜负；下节使用共同组合和两两配对。",
            "",
            "## 4. 为什么当前首选 M_abscos_x_newn",
            "",
            "### 4.1 跨已测层排序相关性",
            "",
            "按每个 dataset×model 内公式分数与真实 Average 的 Spearman 相关，再跨组合平均：",
            "",
            "| Rank | Formula | Mean Spearman | Median | Positive/Total |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for index, row in enumerate(corr_order, 1):
        lines.append(
            "| %d | `%s` | %s | %s | %s/%s |"
            % (index, row["formula"], fmt(row["spearman_mean"]), fmt(row["spearman_median"]), row["spearman_positive_n"], row["correlation_combo_n"])
        )
    lines.extend(
        [
            "",
            "`M_abscos_x_newn` 的平均 Spearman 最高；但只比 `M_new_norm` 高约 0.003，因此该差异必须视为描述性排序，而非统计显著优势。",
            "",
            "敏感性分析没有改变平均 Spearman 的第一名：",
            "",
            "| Outcome profile | Rank 1 | Mean Spearman | Rank 2 | Mean Spearman | Rank 3 | Mean Spearman |",
            "|---|---|---:|---|---:|---|---:|",
        ]
    )
    for profile in ("main", "main_clean", "pali_stable_sensitivity"):
        first, second, third = sensitivity_top[profile]
        lines.append(
            "| `%s` | `%s` | %s | `%s` | %s | `%s` | %s |"
            % (
                profile,
                first["formula"],
                fmt(first["spearman_mean"]),
                second["formula"],
                fmt(second["spearman_mean"]),
                third["formula"],
                fmt(third["spearman_mean"]),
            )
        )
    lines.extend(
        [
            "",
            "### 4.2 七个基础公式的完全共同 Top-3 组合",
            "",
            "| Formula | Common N | Best@3 | Mean@3 | Regret@3↓ | Hit@3 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in base_common3:
        lines.append(
            "| `%s` | %s | %s | %s | %s | %s |"
            % (row["formula"], row["common_combo_n"], fmt(row["best_mean"]), fmt(row["mean_perf"]), fmt(row["regret_mean"]), fmt(row["hit_rate"]))
        )
    lines.extend(
        [
            "",
            "共同组合数很小，因此本表只能说明这些组合内的相对次序，不能外推到 21 组。",
            "",
            "### 4.3 M_abscos_x_newn 与其他公式的配对 Top-3 regret",
            "",
            "Regret improvement = comparison regret − M_abscos regret；正数表示 `M_abscos_x_newn` 更好。",
            "",
            "| Comparison | Paired N | Regret improvement | 95% bootstrap CI | W/T/L | Sign-test p |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in main_pair3:
        lines.append(
            "| `%s` | %s | %s | [%s, %s] | %s/%s/%s | %s |"
            % (
                row["comparison"],
                row["paired_n"],
                fmt(row["regret_improvement_mean"]),
                fmt(row["regret_improvement_ci95_low"]),
                fmt(row["regret_improvement_ci95_high"]),
                row["regret_wins"],
                row["regret_ties"],
                row["regret_losses"],
                fmt(row["sign_test_p_two_sided"]),
            )
        )
    lines.extend(
        [
            "",
            "目前对基础 7 公式的共同完整组合，`M_abscos_x_newn` 的 regret 没有观察到更差；但大量平局与小样本使双侧 sign test 不能提供 p<0.05 的显著性证据。",
            "",
            "### 4.4 与 M_new_norm 的可辨识性",
            "",
            "21 组中两者 Top-3 有序列表完全相同 %d 组（%.1f%%），平均 Top-3 Jaccard 为 %.3f。18 个可算相关性的组合中，`M_abscos_x_newn - M_new_norm` 的平均 Spearman 差为 %.3f，W/T/L=%d/%d/%d；Top-3 regret 配对 W/T/L=%d/%d/%d。现有结果只能支持“`M_abscos_x_newn` 不弱且平均相关性略高”，不能充分证明 `abs(cos)` 因子本身带来稳定增益。"
            % (
                new_norm_overlap["identical_ordered_n"],
                100 * new_norm_overlap["identical_ordered_rate"],
                new_norm_overlap["jaccard_mean"],
                statistics.mean(corr_differences),
                corr_wins,
                corr_ties,
                corr_losses,
                target_vs_new["regret_wins"],
                target_vs_new["regret_ties"],
                target_vs_new["regret_losses"],
            ),
            "",
            "## 5. 与六个正式定位基线的配对比较",
            "",
            "只比较双方 Top-3 都有完整正式评测的相同 dataset×model；正 improvement 表示 `M_abscos_x_newn` 更好。`strict` 另排除候选生成 coverage<0.8 以及 EVQA 历史 FirstToken 未严格统一项。`Perturb-KL-Pre-AltSeq` 按主文档 §2.12 属于消融方法，不列入六个正式基线。",
            "",
            "| Baseline | All N | Best@3 diff | Mean@3 diff | Regret W/T/L | Sign p | Strict N | Strict regret improvement |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in [item for item in baseline_pairs if item["k"] == 3]:
        lines.append(
            "| `%s` | %s | %s | %s | %s/%s/%s | %s | %s | %s |"
            % (
                row["comparison"],
                row["all_paired_n"],
                fmt(row["all_best_perf_improvement"]),
                fmt(row["all_mean_perf_improvement"]),
                row["all_regret_wins"],
                row["all_regret_ties"],
                row["all_regret_losses"],
                fmt(row["all_sign_test_p_two_sided"]),
                row["strict_paired_n"],
                fmt(row["strict_regret_improvement_mean"]),
            )
        )
    lines.extend(
        [
            "",
            "这些配对的平均差当前总体有利于 `M_abscos_x_newn`，但 paired N 很小，且任一基线比较都不能据此声称统计显著全面胜出。",
            "",
            "## 6. 当前覆盖缺口",
            "",
            "`M_abscos_x_newn` 主配置 Top-3 尚未全部正式评测的组合：",
            "",
            "| Dataset | Model | Predicted Top-3 | Missing eval layers |",
            "|---|---|---|---|",
        ]
    )
    for dataset, model, candidates, absent in missing:
        lines.append(
            "| %s | %s | %s | %s |"
            % (
                DATASET_DISPLAY[dataset],
                MODEL_DISPLAY[model],
                ",".join("L%d" % layer for layer in candidates),
                ",".join("L%d" % layer for layer in absent),
            )
        )
    lines.extend(
        [
            "",
            "`M_abscos_x_newn` 在 coverage≥0.8 且已有该模型正式结果的 19 个可评组合中，Top-3 完整覆盖 %d/19，Top-5 完整覆盖 %d/19。特别是 MMKE-entity/LLaVA 尚无正式层结果，MMKE-visual/LLaVA 当前结果不足，且若干基础公式候选层未包含在原先只汇总 4 个 Ours 指标的扫层并集中。这是现有证据缺失，不应按失败或零分处理。"
            % (target_summary["top3_full_n"], target_summary["top5_full_n"]),
            "",
            "## 7. 可以写进论文与暂时不能写的结论",
            "",
            "可以写：",
            "",
            "- 当前 measured-layer 描述性证据可把 `M_abscos_x_newn` 排为视觉梯度框架的首选公式，同时明确它与 `M_new_norm` 接近并列。",
            "- 它在平均跨层排序相关性上领先，并在现有基础公式 Top-3 配对中没有观察到 regret 劣势。",
            "- 与六个正式定位基线的共同完整 Top-3 组合上，描述性均值总体有利于该公式。",
            "",
            "暂时不能写：",
            "",
            "- 已证明它是 21 个组合、所有层的全局最优定位公式。",
            "- 已统计显著优于每个基线。",
            "- `abs(cos)` 因子已被独立证明优于单独的 `S_v_new_norm`；二者当前重合度和配对平局都很高。",
            "- Top-5 已充分验证；当前完整 Top-5 组合更少。",
            "",
            "## 8. 最小补实验方案",
            "",
            "1. 先补 `M_abscos_x_newn` Top-3 缺失层，保持现有统一训练和独立 test/eval 协议。",
            "2. 对 `M_abscos_x_newn` 与 `M_new_norm` Top-3 不同的组合，优先成对补双方独有层；这是验证 `abs(cos)` 是否真正有增益的判别性实验。",
            "3. 再补与最佳深度加权指标候选不同的层，区分视觉梯度关系与深层先验。",
            "4. 完成后按同一冻结脚本重新计算 Best/Mean/Regret/Hit、Spearman/Kendall/NDCG，并报告置信区间，不按结果更换主指标。",
            "",
            "## 9. 可复核输出",
            "",
            "- `formula_topk_all_21.csv`: 21 组 × 11 公式统一 Top-K。",
            "- `formula_full_rankings.csv`: 所有合法层的完整公式排序。",
            "- `formula_combo_metrics.csv`: 每个公式在每个组合上的覆盖与真实表现。",
            "- `formula_global_summary.csv`: 主配置、数值异常剔除及 Pali stable 敏感性汇总。",
            "- `formula_pairwise_vs_M_abscos.csv`: 公式两两配对、bootstrap CI 与 sign test。",
            "- `baseline_pairwise_vs_M_abscos.csv`: 与正式定位基线的配对比较。",
            "- `analysis_manifest.json`: 输入文件哈希与验收计数。",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    outcomes = parse_outcomes()
    profiles = outcome_profiles(outcomes)
    topk, rankings, source_meta = derive_formula_rankings()
    verify_existing_references(topk)
    metrics = []
    for profile, rows in profiles.items():
        metrics.extend(evaluate_candidates(profile, rows, topk, rankings, source_meta))
    formula_summary = summarize_formulas(metrics)
    common_summary = common_set_summary(metrics)
    pairwise = formula_pairwise(metrics)
    baselines = parse_baselines()
    baseline_metrics = evaluate_baselines(baselines, profiles["main"])
    baseline_pairs = baseline_pairwise(metrics, baseline_metrics)
    overlap = formula_overlap(topk)

    topk_rows = []
    for dataset, model in sorted(source_meta):
        for formula, (family, expression, _scorer) in FORMULAS.items():
            layers = topk[(dataset, model, formula)]
            meta = source_meta[(dataset, model)]
            topk_rows.append(
                {
                    "dataset": dataset,
                    "model": model,
                    "family": family,
                    "formula": formula,
                    "expression": expression,
                    "valid_samples": meta["valid_samples"],
                    "total_samples": meta["total_samples"],
                    "coverage": meta["coverage"],
                    "status": "done" if len(layers) >= 3 else "insufficient_or_unavailable",
                    "top1": ",".join("L%d" % layer for layer in layers[:1]),
                    "top3": ",".join("L%d" % layer for layer in layers[:3]),
                    "top5": ",".join("L%d" % layer for layer in layers[:5]),
                    "raw_score_file": meta["raw_score_file"],
                }
            )

    write_csv(OUTPUT / "accepted_outcome_rows.csv", outcomes)
    write_csv(OUTPUT / "formula_topk_all_21.csv", topk_rows)
    write_csv(OUTPUT / "formula_full_rankings.csv", rankings)
    write_csv(OUTPUT / "formula_combo_metrics.csv", metrics)
    write_csv(OUTPUT / "formula_global_summary.csv", formula_summary)
    write_csv(OUTPUT / "formula_common_set_summary.csv", common_summary)
    write_csv(OUTPUT / "formula_pairwise_vs_M_abscos.csv", pairwise)
    write_csv(OUTPUT / "formula_topk_overlap_vs_M_abscos.csv", overlap)
    write_csv(OUTPUT / "baseline_candidates.csv", baselines)
    write_csv(OUTPUT / "baseline_combo_metrics.csv", baseline_metrics)
    write_csv(OUTPUT / "baseline_pairwise_vs_M_abscos.csv", baseline_pairs)

    report = make_report(
        outcomes,
        profiles,
        formula_summary,
        common_summary,
        pairwise,
        baseline_pairs,
        overlap,
        metrics,
        topk,
        source_meta,
    )
    (OUTPUT / "visual_gradient_formula_evidence_report.md").write_text(report, encoding="utf-8")
    manifest = {
        "generated_at": "2026-07-31",
        "method_doc": {"path": str(METHOD_DOC.relative_to(ROOT)), "sha256": sha256(METHOD_DOC)},
        "ledger": {"path": str(LEDGER.relative_to(ROOT)), "sha256": sha256(LEDGER)},
        "raw_score_file_count": len(list(RAW_ROOT.glob("*/*/ours_direct_layer_scores.csv"))),
        "formula_count": len(FORMULAS),
        "formula_topk_rows": len(topk_rows),
        "qwen_reference_rows_verified": 33,
        "ours4_reference_rows_verified": 84,
        "raw_score_files": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in sorted(RAW_ROOT.glob("*/*/ours_direct_layer_scores.csv"))
        },
        "accepted_outcome_rows": len(outcomes),
        "profile_layer_counts": {name: len(rows) for name, rows in profiles.items()},
        "notes": [
            "PaliGemma main is primary; stable is sensitivity only.",
            "EVQA BLIP2 L18-2 replicate is excluded from the primary layer map.",
            "All oracle quantities are measured-layer oracle quantities.",
        ],
    }
    (OUTPUT / "analysis_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("output=%s" % OUTPUT)
    print("raw_score_files=21 formulas=11 topk_rows=%d qwen_reference_verified=33 ours4_reference_verified=84" % len(topk_rows))
    print("accepted_outcome_rows=%d main_layers=%d" % (len(outcomes), len(profiles["main"])))


if __name__ == "__main__":
    main()
