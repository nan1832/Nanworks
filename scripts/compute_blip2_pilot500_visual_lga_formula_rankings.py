import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
SRC_SAMPLE = ROOT / "downloads/Temp/evqa_request_only_blip2_lga_candidate_20260525/pilot_1000/sample_virtual_delta_h_scores.jsonl"
OUT_DIR = ROOT / "downloads/Temp/evqa_request_only_blip2_lga_candidate_20260525/pilot_500_from_pilot1000"
REPORT = ROOT / "md/glodenlayer/BLIP2_Pilot500_Visual_LGA_FormulaRankings.md"


METRIC_KEYS = [
    "s_v_dot",
    "s_v_conflict",
    "s_v_dot_per_dim",
    "s_v_cos",
    "v_old_norm",
    "v_new_norm",
    "v_joint_norm",
    "v_old_nonzero_ratio",
    "v_new_nonzero_ratio",
]


def load_first_n_per_layer(path: Path, n: int = 500):
    buckets = defaultdict(list)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            layer = int(row["layer"])
            if len(buckets[layer]) < n:
                buckets[layer].append(row)
    return buckets


def rank_values(rows, key, descending=True):
    ordered = sorted(rows, key=lambda r: (r[key] is None, r[key]), reverse=descending)
    if not descending:
        ordered = sorted(rows, key=lambda r: (r[key] is None, r[key]))
    for rank, row in enumerate(ordered, 1):
        row[f"{key}_rank"] = rank


def aggregate_layer_rows(buckets):
    rows = []
    for layer in sorted(buckets):
        samples = buckets[layer]
        n = len(samples)
        if n == 0:
            continue
        row = {
            "model": "blip2-opt-2.7b",
            "layer": layer,
            "layer_path": samples[0].get("layer_path", ""),
            "n_request": n,
            "visual_token_start": samples[0].get("visual_token_start", ""),
            "visual_token_end": samples[0].get("visual_token_end", ""),
            "text_token_count_mean": sum(float(s["text_token_count"]) for s in samples) / n,
            "answer_loss_position_count_mean": sum(float(s["answer_loss_position_count"]) for s in samples) / n,
        }
        for key in METRIC_KEYS:
            row[key] = sum(float(s[key]) for s in samples) / n
        row["S_v_dot"] = row.pop("s_v_dot")
        row["S_v_conflict"] = row.pop("s_v_conflict")
        row["S_v_dot_per_dim"] = row.pop("s_v_dot_per_dim")
        row["S_v_cos"] = row.pop("s_v_cos")
        row["S_v_old_norm"] = row.pop("v_old_norm")
        row["S_v_new_norm"] = row.pop("v_new_norm")
        row["S_v_joint_norm"] = row.pop("v_joint_norm")
        row["S_v_old_nonzero_ratio"] = row.pop("v_old_nonzero_ratio")
        row["S_v_new_nonzero_ratio"] = row.pop("v_new_nonzero_ratio")
        row["S_v_positive_ratio"] = sum(1 for s in samples if float(s["s_v_dot"]) > 0) / n
        row["S_v_zero_grad"] = row["S_v_old_norm"] < 1e-8 or row["S_v_new_norm"] < 1e-8
        row["median_v_dot"] = median(float(s["s_v_dot"]) for s in samples)
        rows.append(row)

    for key, desc in [
        ("S_v_dot", True),
        ("S_v_conflict", True),
        ("S_v_dot_per_dim", True),
        ("S_v_cos", True),
        ("S_v_new_norm", True),
        ("S_v_joint_norm", True),
    ]:
        rank_values(rows, key, desc)
    return rows


def write_layer_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "model",
        "layer",
        "layer_path",
        "n_request",
        "visual_token_start",
        "visual_token_end",
        "text_token_count_mean",
        "answer_loss_position_count_mean",
        "S_v_dot",
        "S_v_conflict",
        "S_v_dot_per_dim",
        "S_v_cos",
        "S_v_old_norm",
        "S_v_new_norm",
        "S_v_joint_norm",
        "S_v_positive_ratio",
        "S_v_zero_grad",
        "S_v_old_nonzero_ratio",
        "S_v_new_nonzero_ratio",
        "median_v_dot",
        "S_v_dot_rank",
        "S_v_conflict_rank",
        "S_v_dot_per_dim_rank",
        "S_v_cos_rank",
        "S_v_new_norm_rank",
        "S_v_joint_norm_rank",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def score_formulas(rows):
    by_layer = {int(r["layer"]): r for r in rows}
    valid_nonzero = [r for r in rows if not r["S_v_zero_grad"]]
    max_nn = max(float(r["S_v_new_norm"]) for r in valid_nonzero)

    def base(r):
        return max(0.0, float(r["S_v_cos"])) * float(r["S_v_new_norm"])

    formula_specs = []

    formula_specs.extend(
        [
            {
                "id": "V1",
                "target": "visual-sensitivity",
                "formula": "S_v_dot",
                "sort": "S_v_dot 降序",
                "score": lambda r: float(r["S_v_dot"]),
            },
            {
                "id": "V2",
                "target": "visual-direction",
                "formula": "S_v_cos",
                "sort": "S_v_cos 降序",
                "score": lambda r: float(r["S_v_cos"]),
            },
            {
                "id": "V3",
                "target": "visual-new-norm",
                "formula": "S_v_new_norm",
                "sort": "S_v_new_norm 降序",
                "score": lambda r: float(r["S_v_new_norm"]),
            },
        ]
    )

    formula_specs.extend(
        [
            {
                "id": "B1",
                "target": "gen",
                "formula": "|S_v_cos| * S_v_new_norm",
                "sort": "降序",
                "score": lambda r: abs(float(r["S_v_cos"])) * float(r["S_v_new_norm"]),
            },
            {
                "id": "B2",
                "target": "loc",
                "formula": "S_v_new_norm 反排",
                "sort": "S_v_new_norm 升序",
                "score": lambda r: float(r["S_v_new_norm"]),
                "ascending": True,
            },
            {
                "id": "B3",
                "target": "avg",
                "formula": "S_v_new_norm 反排",
                "sort": "S_v_new_norm 升序",
                "score": lambda r: float(r["S_v_new_norm"]),
                "ascending": True,
            },
            {
                "id": "B4",
                "target": "portability",
                "formula": "S_v_new_norm * (1 - S_v_cos)",
                "sort": "降序",
                "score": lambda r: float(r["S_v_new_norm"]) * (1.0 - float(r["S_v_cos"])),
            },
            {
                "id": "B5",
                "target": "gen-alt",
                "formula": "S_v_positive_ratio 反排",
                "sort": "S_v_positive_ratio 升序",
                "score": lambda r: float(r["S_v_positive_ratio"]),
                "ascending": True,
            },
        ]
    )

    def elbow_score(r, k=2):
        layer = int(r["layer"])
        future = by_layer.get(layer + k)
        if future is None:
            return None
        if float(r["S_v_cos"]) <= 0.08 or float(r["S_v_new_norm"]) <= 0.30:
            return None
        return float(r["S_v_cos"]) - float(future["S_v_cos"])

    for target in ["rel", "gen", "avg"]:
        formula_specs.append(
            {
                "id": "C1",
                "target": target,
                "formula": "M_edit_sweet = S_v_cos(l) - S_v_cos(l+2), with cos>0.08 and nn>0.30",
                "sort": "降序",
                "score": elbow_score,
            }
        )

    def in_v2(r):
        layer = int(r["layer"])
        return layer <= 22 and float(r["S_v_cos"]) > 0.08 and float(r["S_v_new_norm"]) > 0.25

    def in_v3(r):
        return float(r["S_v_cos"]) > 0

    def in_universal(r):
        return float(r["S_v_cos"]) > 0 and float(r["S_v_new_norm"]) > 0.10 * max_nn

    for domain_name, domain_fn in [
        ("v2 F: l<=22, cos>0.08, nn>0.25", in_v2),
        ("v3 F': cos>0", in_v3),
        ("universal F: cos>0 and nn>0.1*max(nn)", in_universal),
    ]:
        prefix = {"v2 F: l<=22, cos>0.08, nn>0.25": "E-v2", "v3 F': cos>0": "E-v3"}.get(domain_name, "U")
        formula_specs.extend(
            [
                {
                    "id": prefix,
                    "target": "rel",
                    "formula": f"max(0,cos)*nn*(l/30)^1.8, {domain_name}",
                    "sort": "降序",
                    "score": lambda r, d=domain_fn: base(r) * (int(r["layer"]) / 30.0) ** 1.8 if d(r) else None,
                },
                {
                    "id": prefix,
                    "target": "gen",
                    "formula": f"max(0,cos)*nn*(l/30)^2.5, {domain_name}",
                    "sort": "降序",
                    "score": lambda r, d=domain_fn: base(r) * (int(r["layer"]) / 30.0) ** 2.5 if d(r) else None,
                },
                {
                    "id": prefix,
                    "target": "avg",
                    "formula": f"max(0,cos)*nn*(l/30)^2, {domain_name}",
                    "sort": "降序",
                    "score": lambda r, d=domain_fn: base(r) * (int(r["layer"]) / 30.0) ** 2.0 if d(r) else None,
                },
                {
                    "id": prefix,
                    "target": "loc",
                    "formula": f"max(0,cos)*sqrt(nn)*(l/30)^2, {domain_name}",
                    "sort": "降序",
                    "score": lambda r, d=domain_fn: max(0.0, float(r["S_v_cos"])) * math.sqrt(float(r["S_v_new_norm"])) * (int(r["layer"]) / 30.0) ** 2.0
                    if d(r)
                    else None,
                },
            ]
        )

    scored = []
    for spec in formula_specs:
        items = []
        for row in rows:
            if row["S_v_zero_grad"]:
                continue
            value = spec["score"](row)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            items.append(
                {
                    "formula_id": spec["id"],
                    "target": spec["target"],
                    "formula": spec["formula"],
                    "sort": spec["sort"],
                    "layer": int(row["layer"]),
                    "score": value,
                    "S_v_cos": float(row["S_v_cos"]),
                    "S_v_new_norm": float(row["S_v_new_norm"]),
                    "S_v_dot": float(row["S_v_dot"]),
                    "S_v_positive_ratio": float(row["S_v_positive_ratio"]),
                }
            )
        reverse = not spec.get("ascending", False)
        items.sort(key=lambda x: x["score"], reverse=reverse)
        for rank, item in enumerate(items, 1):
            item["rank"] = rank
            scored.append(item)
    return scored


def write_formula_csv(scored, path):
    fields = [
        "formula_id",
        "target",
        "formula",
        "sort",
        "rank",
        "layer",
        "score",
        "S_v_cos",
        "S_v_new_norm",
        "S_v_dot",
        "S_v_positive_ratio",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in scored:
            writer.writerow({field: row[field] for field in fields})


def top_layers(scored, formula_id, target, k=10):
    rows = [r for r in scored if r["formula_id"] == formula_id and r["target"] == target and r["rank"] <= k]
    rows.sort(key=lambda r: r["rank"])
    return rows


def md_table(rows, include_formula=False):
    lines = []
    header = "| Rank | Layer | Score | S_v_cos | S_v_new_norm | S_v_dot |"
    sep = "|---:|---:|---:|---:|---:|---:|"
    if include_formula:
        header = "| Formula | Target | Sort | Top10 Layers |"
        sep = "|---|---|---|---|"
    lines.extend([header, sep])
    for row in rows:
        if include_formula:
            layers = ", ".join(str(x["layer"]) for x in row["top"])
            lines.append(f"| `{row['formula']}` | {row['target']} | {row['sort']} | {layers} |")
        else:
            lines.append(
                f"| {row['rank']} | {row['layer']} | {row['score']:.8g} | {row['S_v_cos']:.6g} | {row['S_v_new_norm']:.6g} | {row['S_v_dot']:.6g} |"
            )
    return "\n".join(lines)


def write_report(rows, scored):
    summary_specs = [
        ("V1", "visual-sensitivity", "基础指标：按 S_v_dot 排视觉 raw LGA"),
        ("B1", "gen", "Bridge30旧公式：Generality = |cos|*nn"),
        ("B2", "loc", "Bridge30旧公式：Locality = nn 反排"),
        ("B3", "avg", "Bridge30旧公式：Average = nn 反排"),
        ("C1", "rel", "拐点公式：Rel = cos(l)-cos(l+2)"),
        ("C1", "gen", "拐点公式：Gen = cos(l)-cos(l+2)"),
        ("C1", "avg", "拐点公式：Avg = cos(l)-cos(l+2)"),
        ("E-v2", "rel", "E-VQA v2：Rel 深度加权"),
        ("E-v2", "gen", "E-VQA v2：Gen 深度加权"),
        ("E-v2", "avg", "E-VQA v2：Avg 深度加权"),
        ("E-v2", "loc", "E-VQA v2：Loc 深度加权"),
        ("E-v3", "rel", "E-VQA v3：Rel 深度加权"),
        ("E-v3", "gen", "E-VQA v3：Gen 深度加权"),
        ("E-v3", "avg", "E-VQA v3：Avg 深度加权"),
        ("E-v3", "loc", "E-VQA v3：Loc 深度加权"),
        ("U", "rel", "通用公式：Rel"),
        ("U", "gen", "通用公式：Gen"),
        ("U", "avg", "通用公式：Avg"),
        ("U", "loc", "通用公式：Loc"),
    ]
    summary_rows = []
    for formula_id, target, label in summary_specs:
        top = top_layers(scored, formula_id, target, 10)
        if not top:
            continue
        summary_rows.append(
            {
                "formula": label,
                "target": target,
                "sort": top[0]["sort"],
                "top": top,
            }
        )

    lines = [
        "# BLIP2 pilot500 视觉 LGA 候选层公式排序",
        "",
        "数据来源：`downloads/Temp/evqa_request_only_blip2_lga_candidate_20260525/pilot_1000/sample_virtual_delta_h_scores.jsonl`。",
        "",
        "处理方式：按每个 layer 取前 500 条逐样本梯度记录重新聚合，因此这是从 pilot1000 原始 sample 记录派生的 pilot500，不是直接复用 pilot1000 的层均值。",
        "",
        "只使用视觉指标：`S_v_dot`、`S_v_cos`、`S_v_new_norm`、`S_v_positive_ratio`。",
        "",
        f"层数：{len(rows)}；每层样本数：{rows[0]['n_request'] if rows else 0}。",
        "",
        "## 1. 总览：不同公式 Top10",
        "",
        md_table(summary_rows, include_formula=True),
        "",
        "## 2. 各公式排序明细",
        "",
    ]
    for formula_id, target, label in summary_specs:
        top = top_layers(scored, formula_id, target, 10)
        if not top:
            continue
        lines.extend(
            [
                f"### {label}",
                "",
                f"- 排序目标：`{target}`",
                f"- 排序公式：`{top[0]['formula']}`",
                f"- 排序方向：{top[0]['sort']}",
                "",
                md_table(top),
                "",
            ]
        )
    lines.extend(
        [
            "## 3. 读数说明",
            "",
            "- `rel` 对应 Request/Rel 推荐层排序。",
            "- `gen` 对应 Generality 推荐层排序。",
            "- `avg` 对应 Average/Combined 推荐层排序。",
            "- `loc` 是手册中同时给出的 Locality/M-Loc 排序，虽然你重点问 rel/gen/avg，这里一并保留便于排查 Average 是否被 Loc 牵引。",
            "- Bridge30 旧公式属于对照组；若 Top 层落在 0 或 30，要特别警惕浅层词法重叠或深层写不进去的问题。",
        ]
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    buckets = load_first_n_per_layer(SRC_SAMPLE, 500)
    rows = aggregate_layer_rows(buckets)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_layer_csv(rows, OUT_DIR / "virtual_delta_h_lga_layer_scores_pilot500.csv")
    scored = score_formulas(rows)
    write_formula_csv(scored, OUT_DIR / "visual_formula_rankings_pilot500.csv")
    write_report(rows, scored)
    print(json.dumps({"layer_csv": str(OUT_DIR / "virtual_delta_h_lga_layer_scores_pilot500.csv"), "rankings_csv": str(OUT_DIR / "visual_formula_rankings_pilot500.csv"), "report": str(REPORT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
