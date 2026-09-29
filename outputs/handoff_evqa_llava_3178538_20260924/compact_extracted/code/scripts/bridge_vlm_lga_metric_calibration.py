import argparse
import csv
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


try:
    from scipy import stats as scipy_stats
except Exception:  # pragma: no cover - fallback only for lean environments
    scipy_stats = None


MAIN_AXES = ["request", "generality", "portability", "locality"]
ALL_AXES = [
    "request",
    "generality",
    "portability",
    "locality",
    "gen_text",
    "gen_image",
    "loc_text",
    "loc_image",
]
AXIS_COLUMNS = {
    "request": "request_acc",
    "generality": "generality_acc",
    "portability": "portability_acc",
    "locality": "locality_acc",
    "gen_text": "generality_text_acc",
    "gen_image": "generality_image_acc",
    "loc_text": "locality_text_acc",
    "loc_image": "locality_image_acc",
}
MODALITIES = ["visual", "text"]
PREFIX = {"visual": "v", "text": "t"}


def read_table(path: str) -> List[Dict[str, str]]:
    delimiter = "\t" if path.endswith(".tsv") else ","
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def write_table(path: str, rows: List[Dict[str, Any]], fields: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def safe_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def safe_stat_pair(value: Any) -> Tuple[float, float]:
    if isinstance(value, tuple) and len(value) >= 2:
        corr, p = value[0], value[1]
    else:
        corr = getattr(value, "statistic", 0.0)
        p = getattr(value, "pvalue", 1.0)
    corr = to_float(corr, 0.0)
    p = to_float(p, 1.0)
    return corr, p


def spearman(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float]:
    if len(xs) < 3 or len(set(xs)) <= 1 or len(set(ys)) <= 1:
        return 0.0, 1.0
    if scipy_stats is None:
        return pearson(rank_desc(xs), rank_desc(ys))[0], 1.0
    return safe_stat_pair(scipy_stats.spearmanr(xs, ys))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float]:
    if len(xs) < 3 or len(set(xs)) <= 1 or len(set(ys)) <= 1:
        return 0.0, 1.0
    if scipy_stats is None:
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        vx = sum((x - mx) ** 2 for x in xs)
        vy = sum((y - my) ** 2 for y in ys)
        if vx <= 0 or vy <= 0:
            return 0.0, 1.0
        corr = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)
        return corr, 1.0
    return safe_stat_pair(scipy_stats.pearsonr(xs, ys))


def rank_desc(values: Sequence[float]) -> List[float]:
    if scipy_stats is not None:
        return [float(x) for x in scipy_stats.rankdata([-v for v in values], method="average")]
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg
        i = j
    return ranks


def topk_layers(rows: List[Dict[str, Any]], key: str, k: int) -> List[int]:
    return [
        int(row["layer"])
        for row in sorted(rows, key=lambda row: to_float(row[key]), reverse=True)[:k]
    ]


def topk_hit(metric_layers: Sequence[int], oracle_layers: Sequence[int], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(metric_layers[:k]) & set(oracle_layers[:k])) / float(k)


def geomean(values: Sequence[float]) -> float:
    vals = [max(float(v), 0.0) for v in values]
    if any(v <= 0 for v in vals):
        return 0.0
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def metric_specs(modality: str) -> List[Tuple[str, str]]:
    prefix = PREFIX[modality]
    return [
        ("M_dot", f"S_{prefix}_dot"),
        ("M_conflict", f"S_{prefix}_conflict"),
        ("M_dot_per_dim", f"S_{prefix}_dot_per_dim"),
        ("M_cos", f"S_{prefix}_cos"),
        ("M_pos_ratio", f"S_{prefix}_positive_ratio"),
        ("M_new_norm", f"S_{prefix}_new_norm"),
        ("M_old_norm", f"S_{prefix}_old_norm"),
        ("M_joint_norm", f"S_{prefix}_joint_norm"),
        ("M_newn_x_1mcos", "__compound_newn_x_1mcos__"),
        ("M_newn_x_pos", "__compound_newn_x_pos__"),
        ("M_abscos_x_newn", "__compound_abscos_x_newn__"),
        ("M_conflict_x_newn", "__compound_conflict_x_newn__"),
    ]


def add_metric_values(rows: List[Dict[str, Any]]) -> None:
    for row in rows:
        for modality in MODALITIES:
            p = PREFIX[modality]
            new_norm = to_float(row.get(f"S_{p}_new_norm"))
            cos = to_float(row.get(f"S_{p}_cos"))
            pos = to_float(row.get(f"S_{p}_positive_ratio"))
            conflict = to_float(row.get(f"S_{p}_conflict"))
            row[f"{modality}.M_newn_x_1mcos"] = new_norm * (1.0 - cos)
            row[f"{modality}.M_newn_x_pos"] = new_norm * pos
            row[f"{modality}.M_abscos_x_newn"] = abs(cos) * new_norm
            row[f"{modality}.M_conflict_x_newn"] = conflict * new_norm


def metric_key(modality: str, spec_key: str) -> str:
    if spec_key == "__compound_newn_x_1mcos__":
        return f"{modality}.M_newn_x_1mcos"
    if spec_key == "__compound_newn_x_pos__":
        return f"{modality}.M_newn_x_pos"
    if spec_key == "__compound_abscos_x_newn__":
        return f"{modality}.M_abscos_x_newn"
    if spec_key == "__compound_conflict_x_newn__":
        return f"{modality}.M_conflict_x_newn"
    return spec_key


def merge_rows(eval_path: str, lga_path: str, model: str) -> List[Dict[str, Any]]:
    eval_rows = {int(row["layer"]): row for row in read_table(eval_path)}
    lga_rows = {int(row["layer"]): row for row in read_table(lga_path)}
    layers = sorted(set(eval_rows) & set(lga_rows))
    if len(layers) != 32:
        raise RuntimeError(f"{model}: expected 32 merged layers, got {len(layers)}")
    merged = []
    for layer in layers:
        row: Dict[str, Any] = {"model": model, "layer": layer}
        row.update(eval_rows[layer])
        row.update(lga_rows[layer])
        for axis, col in AXIS_COLUMNS.items():
            row[axis] = to_float(row.get(col))
        merged.append(row)
    add_metric_values(merged)
    return merged


def filtered_rows(rows: List[Dict[str, Any]], modality: str, eps_filter: float, filtered: bool) -> Tuple[List[Dict[str, Any]], List[int]]:
    if not filtered:
        return list(rows), []
    p = PREFIX[modality]
    kept = []
    dropped = []
    for row in rows:
        new_norm = to_float(row.get(f"S_{p}_new_norm"))
        is_zero = safe_bool(row.get(f"S_{p}_zero_grad"))
        if new_norm < eps_filter or is_zero:
            dropped.append(int(row["layer"]))
        else:
            kept.append(row)
    return kept, dropped


def evaluate_view(
    rows: List[Dict[str, Any]],
    model: str,
    modality: str,
    filtered_label: str,
    eps_filter: float,
    topks: Sequence[int],
) -> Dict[str, Any]:
    use_filtered = filtered_label == "filtered"
    view_rows, dropped_layers = filtered_rows(rows, modality, eps_filter, use_filtered)
    specs = metric_specs(modality)
    spearman_rows: List[Dict[str, Any]] = []
    pearson_rows: List[Dict[str, Any]] = []
    topk_rows: List[Dict[str, Any]] = []
    rank_rows: List[Dict[str, Any]] = []
    metrics_for_summary: Dict[str, Dict[str, Any]] = {}

    for metric_name, raw_key in specs:
        key = metric_key(modality, raw_key)
        xs = [to_float(row.get(key)) for row in view_rows]
        metric_summary: Dict[str, Any] = {"metric_name": metric_name}
        axis_rhos = {}
        for axis in ALL_AXES:
            ys = [to_float(row.get(axis)) for row in view_rows]
            rho, p_s = spearman(xs, ys)
            r, p_p = pearson(xs, ys)
            axis_rhos[axis] = rho
            spearman_rows.append(
                {
                    "filtered": filtered_label,
                    "model": model,
                    "modality": modality,
                    "metric_name": metric_name,
                    "axis": axis,
                    "rho": rho,
                    "p": p_s,
                    "n": len(view_rows),
                    "is_raw_dot_baseline": metric_name == "M_dot",
                }
            )
            pearson_rows.append(
                {
                    "filtered": filtered_label,
                    "model": model,
                    "modality": modality,
                    "metric_name": metric_name,
                    "axis": axis,
                    "r": r,
                    "p": p_p,
                    "n": len(view_rows),
                    "is_raw_dot_baseline": metric_name == "M_dot",
                }
            )
            metric_rank = rank_desc(xs)
            oracle_rank = rank_desc(ys)
            rank_rows.append(
                {
                    "filtered": filtered_label,
                    "model": model,
                    "modality": modality,
                    "metric_name": metric_name,
                    "axis": axis,
                    "rank_dist": sum(abs(a - b) for a, b in zip(metric_rank, oracle_rank)) / max(len(metric_rank), 1),
                    "n": len(view_rows),
                    "is_raw_dot_baseline": metric_name == "M_dot",
                }
            )
            for k in topks:
                m_layers = topk_layers(view_rows, key, k)
                o_layers = topk_layers(view_rows, axis, k)
                topk_rows.append(
                    {
                        "filtered": filtered_label,
                        "model": model,
                        "modality": modality,
                        "metric_name": metric_name,
                        "axis": axis,
                        "k": k,
                        "hit": topk_hit(m_layers, o_layers, k),
                        "metric_topk_layers": json.dumps(m_layers, ensure_ascii=False),
                        "oracle_topk_layers": json.dumps(o_layers, ensure_ascii=False),
                        "is_raw_dot_baseline": metric_name == "M_dot",
                    }
                )
        agg = geomean(
            [
                max(axis_rhos["request"], 0.0),
                max(axis_rhos["generality"], 0.0),
                max(axis_rhos["portability"], 0.0),
                max(-axis_rhos["locality"], 0.0),
            ]
        )
        top3_hit_gen = next(
            row["hit"]
            for row in topk_rows
            if row["metric_name"] == metric_name and row["axis"] == "generality" and int(row["k"]) == 3
        )
        metric_summary.update(
            {
                "rho_request": axis_rhos["request"],
                "rho_generality": axis_rhos["generality"],
                "rho_portability": axis_rhos["portability"],
                "rho_locality": axis_rhos["locality"],
                "agg": agg,
                "top1_layer": topk_layers(view_rows, key, 1)[0] if view_rows else None,
                "top3_layers": topk_layers(view_rows, key, 3),
                "top5_layers": topk_layers(view_rows, key, 5),
                "top3_hit_generality": top3_hit_gen,
            }
        )
        metric_summary["p_generality"] = next(
            row["p"]
            for row in spearman_rows
            if row["metric_name"] == metric_name and row["axis"] == "generality"
        )
        metrics_for_summary[metric_name] = metric_summary

    ranked = sorted(
        metrics_for_summary.values(),
        key=lambda item: (
            1 if item["rho_generality"] > 0 and item["p_generality"] < 0.05 else 0,
            1 if item["rho_generality"] > 0 else 0,
            item["rho_generality"],
            item["agg"],
            item["top3_hit_generality"],
        ),
        reverse=True,
    )
    return {
        "spearman": spearman_rows,
        "pearson": pearson_rows,
        "topk": topk_rows,
        "rank_dist": rank_rows,
        "metrics": ranked,
        "winner": ranked[0],
        "raw_dot": metrics_for_summary["M_dot"],
        "dropped_layers": dropped_layers,
        "n_layers": len(view_rows),
    }


def format_float(value: float) -> str:
    return f"{float(value):.6g}"


def write_model_summary(
    path: str,
    model: str,
    filtered_results: Dict[str, Dict[str, Any]],
    unfiltered_results: Dict[str, Dict[str, Any]],
    rows: List[Dict[str, Any]],
) -> None:
    lines = [f"# {model} LGA Metric Calibration", ""]
    lines.append("Main tables use `filtered` rankings; zero-gradient layers are excluded per modality.")
    lines.append("")
    for modality in MODALITIES:
        result = filtered_results[modality]
        winner = result["winner"]
        raw = result["raw_dot"]
        dropped = result["dropped_layers"]
        lines.extend(
            [
                f"## {modality}",
                "",
                f"Dropped layers: `{dropped}`",
                "",
                "| Role | Metric | rho(generality) | p | agg | top3_hit(generality) | top1 | top3 |",
                "|---|---|---:|---:|---:|---:|---:|---|",
                f"| Winner | {winner['metric_name']} | {format_float(winner['rho_generality'])} | "
                f"{format_float(winner['p_generality'])} | {format_float(winner['agg'])} | "
                f"{format_float(winner['top3_hit_generality'])} | {winner['top1_layer']} | `{winner['top3_layers']}` |",
                f"| Raw dot | {raw['metric_name']} | {format_float(raw['rho_generality'])} | "
                f"{format_float(raw['p_generality'])} | {format_float(raw['agg'])} | "
                f"{format_float(raw['top3_hit_generality'])} | {raw['top1_layer']} | `{raw['top3_layers']}` |",
                "",
                "### Filtered Metric Ranking By Generality",
                "",
                "| Rank | Metric | rho(request) | rho(generality) | rho(portability) | rho(locality) | agg | top3_hit(generality) | top3 |",
                "|---:|---|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for idx, item in enumerate(result["metrics"], 1):
            lines.append(
                f"| {idx} | {item['metric_name']} | {format_float(item['rho_request'])} | "
                f"{format_float(item['rho_generality'])} | {format_float(item['rho_portability'])} | "
                f"{format_float(item['rho_locality'])} | {format_float(item['agg'])} | "
                f"{format_float(item['top3_hit_generality'])} | `{item['top3_layers']}` |"
            )
        lines.append("")
        unfiltered_winner = unfiltered_results[modality]["winner"]
        lines.append(
            f"Unfiltered winner: `{unfiltered_winner['metric_name']}`, "
            f"rho(generality)={format_float(unfiltered_winner['rho_generality'])}, "
            f"top3=`{unfiltered_winner['top3_layers']}`."
        )
        lines.append("")

    lines.extend(["## New Norm Magnitude Evidence", ""])
    for modality in MODALITIES:
        p = PREFIX[modality]
        key = f"S_{p}_new_norm"
        layer30 = next((row for row in rows if int(row["layer"]) == 30), None)
        max_row = max(rows, key=lambda row: to_float(row.get(key)))
        if layer30 is not None:
            ratio = to_float(max_row.get(key)) / (to_float(layer30.get(key)) + 1e-12)
            lines.append(
                f"- {modality}: layer30 {key}={format_float(to_float(layer30.get(key)))}, "
                f"max layer {max_row['layer']} {key}={format_float(to_float(max_row.get(key)))}, "
                f"ratio={format_float(ratio)}."
            )
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_outputs(
    output_dir: str,
    model: str,
    rows: List[Dict[str, Any]],
    eps_filter: float,
    topks: Sequence[int],
) -> Dict[str, Any]:
    model_dir = os.path.join(output_dir, model)
    os.makedirs(model_dir, exist_ok=True)
    all_results: Dict[str, Dict[str, Dict[str, Any]]] = {"filtered": {}, "unfiltered": {}}
    for filtered_label in ["filtered", "unfiltered"]:
        out_dir = os.path.join(model_dir, filtered_label)
        os.makedirs(out_dir, exist_ok=True)
        combined = {"spearman": [], "pearson": [], "topk": [], "rank_dist": []}
        for modality in MODALITIES:
            result = evaluate_view(rows, model, modality, filtered_label, eps_filter, topks)
            all_results[filtered_label][modality] = result
            combined["spearman"].extend(result["spearman"])
            combined["pearson"].extend(result["pearson"])
            combined["topk"].extend(result["topk"])
            combined["rank_dist"].extend(result["rank_dist"])

        write_table(
            os.path.join(out_dir, "per_axis_spearman.csv"),
            combined["spearman"],
            ["filtered", "model", "modality", "metric_name", "axis", "rho", "p", "n", "is_raw_dot_baseline"],
        )
        write_table(
            os.path.join(out_dir, "per_axis_pearson.csv"),
            combined["pearson"],
            ["filtered", "model", "modality", "metric_name", "axis", "r", "p", "n", "is_raw_dot_baseline"],
        )
        write_table(
            os.path.join(out_dir, "per_axis_topk_hit.csv"),
            combined["topk"],
            [
                "filtered",
                "model",
                "modality",
                "metric_name",
                "axis",
                "k",
                "hit",
                "metric_topk_layers",
                "oracle_topk_layers",
                "is_raw_dot_baseline",
            ],
        )
        write_table(
            os.path.join(out_dir, "per_metric_rank_dist.csv"),
            combined["rank_dist"],
            ["filtered", "model", "modality", "metric_name", "axis", "rank_dist", "n", "is_raw_dot_baseline"],
        )

    for filename in [
        "per_axis_spearman.csv",
        "per_axis_pearson.csv",
        "per_axis_topk_hit.csv",
        "per_metric_rank_dist.csv",
    ]:
        shutil.copyfile(os.path.join(model_dir, "filtered", filename), os.path.join(model_dir, filename))

    winners = {
        "model": model,
        "eps_filter": eps_filter,
        "filtered": {},
        "unfiltered": {},
    }
    for filtered_label in ["filtered", "unfiltered"]:
        for modality in MODALITIES:
            result = all_results[filtered_label][modality]
            winners[filtered_label][modality] = {
                "main_axis": "generality",
                "winner": result["winner"],
                "raw_dot_baseline": result["raw_dot"],
                "dropped_layers": result["dropped_layers"],
                "ranking_full": result["metrics"],
            }
    with open(os.path.join(model_dir, "per_axis_winner.json"), "w", encoding="utf-8") as f:
        json.dump(winners, f, ensure_ascii=False, indent=2)
    write_model_summary(os.path.join(model_dir, "summary.md"), model, all_results["filtered"], all_results["unfiltered"], rows)
    return winners


def write_cross_model_overview(output_dir: str, winners_by_model: Dict[str, Any]) -> None:
    lines = [
        "# Bridge30 LGA Metric Calibration Overview",
        "",
        "Main axis: `generality`; primary tables use `filtered` results.",
        "",
        "| Model | Modality | Winner | rho(generality) | p | agg | top3_hit | top1 | top3 | Raw-dot rho(generality) | Raw-dot top3 | Dropped |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for model, payload in winners_by_model.items():
        for modality in MODALITIES:
            item = payload["filtered"][modality]
            winner = item["winner"]
            raw = item["raw_dot_baseline"]
            lines.append(
                f"| {model} | {modality} | {winner['metric_name']} | "
                f"{format_float(winner['rho_generality'])} | {format_float(winner['p_generality'])} | "
                f"{format_float(winner['agg'])} | {format_float(winner['top3_hit_generality'])} | "
                f"{winner['top1_layer']} | `{winner['top3_layers']}` | "
                f"{format_float(raw['rho_generality'])} | `{raw['top3_layers']}` | `{item['dropped_layers']}` |"
            )
    lines.append("")
    lines.append("Locality uses the original high-is-good axis for single-axis Spearman, and `-rho(locality)` only inside `agg`.")
    lines.append("")
    with open(os.path.join(output_dir, "cross_model_overview.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def parse_topks(raw: str) -> List[int]:
    return [int(piece.strip()) for piece in raw.split(",") if piece.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge30 Virtual Delta-h LGA metric calibration.")
    parser.add_argument("--llava-eval-tsv", required=True)
    parser.add_argument("--blip2-eval-tsv", required=True)
    parser.add_argument("--llava-lga-csv", required=True)
    parser.add_argument("--blip2-lga-csv", required=True)
    parser.add_argument("--eps-filter", type=float, default=1e-6)
    parser.add_argument("--topk", default="1,3,5")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    topks = parse_topks(args.topk)
    os.makedirs(args.output_dir, exist_ok=True)
    inputs = {
        "llava-v1.5-7b": (args.llava_eval_tsv, args.llava_lga_csv),
        "blip2-opt-2.7b": (args.blip2_eval_tsv, args.blip2_lga_csv),
    }
    winners_by_model = {}
    for model, (eval_path, lga_path) in inputs.items():
        rows = merge_rows(eval_path, lga_path, model)
        winners_by_model[model] = write_outputs(args.output_dir, model, rows, args.eps_filter, topks)

    write_cross_model_overview(args.output_dir, winners_by_model)
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(json.dumps({"output_dir": args.output_dir, "models": list(winners_by_model)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
