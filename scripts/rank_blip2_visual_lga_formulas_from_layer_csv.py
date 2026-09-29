import argparse
import csv
import json
import math
from pathlib import Path


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["layer"] = int(row["layer"])
        for key in ["S_v_dot", "S_v_cos", "S_v_new_norm", "S_v_positive_ratio"]:
            row[key] = float(row[key])
        row["S_v_zero_grad"] = str(row.get("S_v_zero_grad", "")).lower() in {"true", "1", "yes"}
    return rows


def score_rows(rows):
    valid = [r for r in rows if not r["S_v_zero_grad"]]
    max_nn = max(r["S_v_new_norm"] for r in valid)
    by_layer = {r["layer"]: r for r in valid}

    def base(r):
        return max(0.0, r["S_v_cos"]) * r["S_v_new_norm"]

    def elbow(r, k=2):
        nxt = by_layer.get(r["layer"] + k)
        if nxt is None:
            return None
        if r["S_v_cos"] <= 0.08 or r["S_v_new_norm"] <= 0.30:
            return None
        return r["S_v_cos"] - nxt["S_v_cos"]

    def in_v2(r):
        return r["layer"] <= 22 and r["S_v_cos"] > 0.08 and r["S_v_new_norm"] > 0.25

    def in_v3(r):
        return r["S_v_cos"] > 0

    def in_universal(r):
        return r["S_v_cos"] > 0 and r["S_v_new_norm"] > 0.10 * max_nn

    specs = [
        ("V1", "visual-sensitivity", "S_v_dot", "S_v_dot 降序", lambda r: r["S_v_dot"], False),
        ("V2", "visual-direction", "S_v_cos", "S_v_cos 降序", lambda r: r["S_v_cos"], False),
        ("V3", "visual-new-norm", "S_v_new_norm", "S_v_new_norm 降序", lambda r: r["S_v_new_norm"], False),
        ("B1", "gen", "|S_v_cos| * S_v_new_norm", "降序", lambda r: abs(r["S_v_cos"]) * r["S_v_new_norm"], False),
        ("B2", "loc", "S_v_new_norm 反排", "S_v_new_norm 升序", lambda r: r["S_v_new_norm"], True),
        ("B3", "avg", "S_v_new_norm 反排", "S_v_new_norm 升序", lambda r: r["S_v_new_norm"], True),
        ("B4", "portability", "S_v_new_norm * (1 - S_v_cos)", "降序", lambda r: r["S_v_new_norm"] * (1.0 - r["S_v_cos"]), False),
        ("B5", "gen-alt", "S_v_positive_ratio 反排", "S_v_positive_ratio 升序", lambda r: r["S_v_positive_ratio"], True),
    ]
    for target in ["rel", "gen", "avg"]:
        specs.append(("C1", target, "M_edit_sweet = S_v_cos(l) - S_v_cos(l+2), with cos>0.08 and nn>0.30", "降序", elbow, False))

    for prefix, domain_label, domain_fn in [
        ("E-v2", "v2 F: l<=22, cos>0.08, nn>0.25", in_v2),
        ("E-v3", "v3 F': cos>0", in_v3),
        ("U", "universal F: cos>0 and nn>0.1*max(nn)", in_universal),
    ]:
        specs.extend(
            [
                (prefix, "rel", f"max(0,cos)*nn*(l/30)^1.8, {domain_label}", "降序", lambda r, d=domain_fn: base(r) * (r["layer"] / 30.0) ** 1.8 if d(r) else None, False),
                (prefix, "gen", f"max(0,cos)*nn*(l/30)^2.5, {domain_label}", "降序", lambda r, d=domain_fn: base(r) * (r["layer"] / 30.0) ** 2.5 if d(r) else None, False),
                (prefix, "avg", f"max(0,cos)*nn*(l/30)^2.0, {domain_label}", "降序", lambda r, d=domain_fn: base(r) * (r["layer"] / 30.0) ** 2.0 if d(r) else None, False),
                (prefix, "loc", f"max(0,cos)*sqrt(nn)*(l/30)^2.0, {domain_label}", "降序", lambda r, d=domain_fn: max(0.0, r["S_v_cos"]) * math.sqrt(r["S_v_new_norm"]) * (r["layer"] / 30.0) ** 2.0 if d(r) else None, False),
            ]
        )

    scored = []
    for fid, target, formula, sort_label, fn, ascending in specs:
        items = []
        for row in valid:
            score = fn(row)
            if score is None or (isinstance(score, float) and math.isnan(score)):
                continue
            items.append(
                {
                    "formula_id": fid,
                    "target": target,
                    "formula": formula,
                    "sort": sort_label,
                    "layer": row["layer"],
                    "score": score,
                    "S_v_cos": row["S_v_cos"],
                    "S_v_new_norm": row["S_v_new_norm"],
                    "S_v_dot": row["S_v_dot"],
                    "S_v_positive_ratio": row["S_v_positive_ratio"],
                }
            )
        items.sort(key=lambda x: x["score"], reverse=not ascending)
        for rank, item in enumerate(items, 1):
            item["rank"] = rank
            scored.append(item)
    return scored


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
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
        for row in rows:
            writer.writerow(row)


def top(scored, fid, target, k=10):
    rows = [r for r in scored if r["formula_id"] == fid and r["target"] == target and r["rank"] <= k]
    return sorted(rows, key=lambda r: r["rank"])


def write_report(path: Path, layer_csv: Path, scored):
    summary = [
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
        ("E-v3", "rel", "E-VQA v3：Rel 深度加权"),
        ("E-v3", "gen", "E-VQA v3：Gen 深度加权"),
        ("E-v3", "avg", "E-VQA v3：Avg 深度加权"),
        ("U", "rel", "通用公式：Rel"),
        ("U", "gen", "通用公式：Gen"),
        ("U", "avg", "通用公式：Avg"),
    ]
    lines = [
        "# BLIP2 proxy500 视觉 LGA 候选层公式排序",
        "",
        f"数据来源：`{layer_csv}`。",
        "",
        "旧知识字段：`pred`；新知识字段：`alt`。本报告只读取该真实 proxy500/pilot500 的 `virtual_delta_h_lga_layer_scores.csv`。",
        "",
        "## Top10 总览",
        "",
        "| Formula | Target | Sort | Top10 Layers |",
        "|---|---|---|---|",
    ]
    for fid, target, label in summary:
        rows = top(scored, fid, target)
        if rows:
            lines.append(f"| `{label}` | {target} | {rows[0]['sort']} | {', '.join(str(r['layer']) for r in rows)} |")
    lines.extend(["", "## 排序明细", ""])
    for fid, target, label in summary:
        rows = top(scored, fid, target)
        if not rows:
            continue
        lines.extend(
            [
                f"### {label}",
                "",
                f"- 排序目标：`{target}`",
                f"- 排序公式：`{rows[0]['formula']}`",
                f"- 排序方向：{rows[0]['sort']}",
                "",
                "| Rank | Layer | Score | S_v_cos | S_v_new_norm | S_v_dot |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for r in rows:
            lines.append(f"| {r['rank']} | {r['layer']} | {r['score']:.8g} | {r['S_v_cos']:.6g} | {r['S_v_new_norm']:.6g} | {r['S_v_dot']:.6g} |")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer-csv", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    layer_csv = Path(args.layer_csv)
    scored = score_rows(read_rows(layer_csv))
    write_csv(Path(args.out_csv), scored)
    write_report(Path(args.report), layer_csv, scored)
    print(json.dumps({"rank_csv": args.out_csv, "report": args.report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
