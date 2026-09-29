"""Generate the remaining six localization methods and CMA-ModelPred v2.

Uses the same renderer and documented evaluation matrix as the approved CMA-alt
figure. Each method is checked against both recommendation tables before output.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import build_cma_eval_heatmap_20260921 as base

OUT = base.ROOT / "outputs/localization_heatmaps_20260921"
METHODS = [
    dict(id="Middle-Prior-Direct", short="Middle-Prior", label="Middle-Prior-Direct",
         section="3.1", stem="01_middle_prior_editing_heatmap"),
    dict(id="VisEdit-Contrib-Pre-KeyToken", short="VisEdit", label="VisEdit-Contrib-Pre-KeyToken",
         section="3.2", stem="02_visedit_keytoken_editing_heatmap"),
    dict(id="SaLEM-Alt-Direct", short="SaLEM", label="SaLEM-Alt-Direct",
         section="3.3", stem="03_salem_alt_editing_heatmap"),
    dict(id="LGA-Param-Direct-AltModelPred", short="LGA", label="LGA-Param-Direct-AltModelPred",
         section="3.4", stem="04_lga_altmodelpred_editing_heatmap"),
    dict(id="Perturb-KL-Direct-AltSeq", short="Perturb-KL", label="Perturb-KL-Direct-AltSeq",
         section="3.5", stem="05_perturb_kl_altseq_editing_heatmap"),
    dict(id="Ours-Direct", short="Ours-Direct", label="Ours-Direct · M_abscos_x_newn = abs(S_v_cos) × S_v_new_norm",
         section="3.6", stem="06_ours_direct_editing_heatmap"),
    dict(id="CMA-ModelPred-Direct-v2", short="CMA-ModelPred v2", label="CMA-ModelPred-Direct v2 · 正式 model_pred 目标",
         section="3.8", stem="07_cma_modelpred_v2_editing_heatmap"),
]


def validate_candidate_tables(candidate_maps, depths):
    """Cross-check the per-method table against the separate per-combo table."""
    checked = set()
    combo = None
    for line in base.CANDIDATES.read_text(encoding="utf-8").splitlines():
        if line.startswith("### 4."):
            dataset, model = line.split(" ", 2)[2].split(" × ")
            combo = (dataset, model)
        elif line.startswith("## 5."):
            break
        elif combo and line.startswith("| "):
            c = base.cells(line)
            if len(c) == 4 and c[0] in candidate_maps:
                rec = candidate_maps[c[0]][combo]
                assert c[2] == ",".join(f"L{x}" for x in rec["top3"]), (c[0], combo)
                assert c[3] == ",".join(f"L{x}" for x in rec["top5"]), (c[0], combo)
                assert all(0 <= x < depths[combo[1]] for x in rec["top5"])
                checked.add((c[0], *combo))
    assert len(checked) == 147, len(checked)
    return len(checked)


def render_method(method, candidates, depths, selected):
    base.configure_fonts()
    for relative in (False, True):
        stem = base.render(candidates, depths, selected, relative=relative,
                           method=method, output_dir=OUT)
        print(f"Rendered {stem}", flush=True)
    return method["id"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records, _, depths, selected = base.read_data()
    previous = json.loads((base.OUT / "cma_heatmap_data.json").read_text(encoding="utf-8"))
    previous_selected = {(c["dataset"], c["model"], c["layer"]): c["evaluation"]
                         for c in previous["cells"] if c["evaluation"] is not None}
    assert selected == previous_selected, "Evaluation data changed since the approved CMA-alt figure."
    assert not [r for r in records if r["average"] is not None and abs(r["average_rounding_difference"]) > .03]
    candidate_maps = {m["id"]: base.read_candidates(m["section"]) for m in METHODS}
    checked = validate_candidate_tables(candidate_maps, depths)
    scores = []
    for model in base.MODELS:
        for dataset in base.DATASETS:
            for layer in range(36):
                r = selected.get((dataset, model, layer))
                scores.append(dict(dataset=dataset, model=model, layer=layer,
                    state="no_such_layer" if layer >= depths[model] else "evaluated" if r else "no_score_in_source",
                    evaluation=r, marks=base.tags(r) if r else ""))
    score_bytes = json.dumps(scores, ensure_ascii=False, sort_keys=True).encode("utf-8")
    score_hash = hashlib.sha256(score_bytes).hexdigest()
    sources = [dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
               for p in (base.SOURCE, base.CANDIDATES, base.MANUAL)]
    common = dict(generated_at=datetime.now().isoformat(timespec="seconds"), sources=sources,
                  evaluation_matrix_sha256=score_hash, same_as_previous_cma_alt=True,
                  summary=dict(Counter(c["state"] for c in scores)),
                  cells=scores, all_source_records=records,
                  selection_policy=previous["selection_policy"])
    (OUT / "shared_evaluation_data.json").write_text(json.dumps(common, ensure_ascii=False, indent=2), encoding="utf-8")
    summaries = []
    for method in METHODS:
        candidates = candidate_maps[method["id"]]
        candidate_cells = []
        for (dataset, model), rec in candidates.items():
            for rank, layer in enumerate(rec["top5"], 1):
                result = selected.get((dataset, model, layer))
                candidate_cells.append(dict(dataset=dataset, model=model, layer=layer, rank=rank,
                    average=result["average"] if result else None, config=result["config"] if result else None,
                    evaluation_source_line=result["source_line"] if result else None,
                    recommendation_source_line=rec["source_line"], recommendation_note=rec["note"]))
        summary = dict(method=method["id"], top3_evaluated=sum(c["average"] is not None and c["rank"] <= 3 for c in candidate_cells),
                       top5_evaluated=sum(c["average"] is not None for c in candidate_cells),
                       candidate_cells=len(candidate_cells))
        assert summary["candidate_cells"] == 105
        summaries.append(summary)
        payload = dict(method=method, evaluation_matrix_sha256=score_hash,
                       summary=summary, candidates=candidate_cells)
        (OUT / f'{method["stem"]}_data.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validated {checked} recommendation rows; all methods share {len(selected)} unchanged scores.", flush=True)
    # Workers only write method-specific files, and share no pyplot state.
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(render_method, m, candidate_maps[m["id"]], depths, selected) for m in METHODS]
        for future in as_completed(futures):
            print(f"Completed {future.result()}", flush=True)

    from PIL import Image
    files = []
    for method in METHODS:
        for relative in (False, True):
            stem = method["stem"] + ("_row_relative" if relative else "")
            for ext in ("png", "svg", "pdf"):
                path = OUT / f"{stem}.{ext}"
                assert path.stat().st_size > 10_000, path
                files.append(path)
            with Image.open(OUT / f"{stem}.png") as im:
                assert im.size == (6160, 3300), (stem, im.size)
                im.verify()
    assert len(files) == 42
    manifest = dict(method_count=7, variants_per_method=2, files=len(files),
                    candidate_tables_cross_checked=checked, same_scores_as_previous_cma_alt=True,
                    evaluation_matrix_sha256=score_hash, summaries=summaries,
                    artifacts=[dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size) for p in files])
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_readme(summaries)
    source_dir = OUT / "source"
    source_dir.mkdir(exist_ok=True)
    for path in (Path(__file__), Path(base.__file__)):
        shutil.copy2(path, source_dir / path.name)
    archive = OUT.parent / "localization_heatmaps_20260921.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                z.write(path, arcname=Path(OUT.name) / path.relative_to(OUT))
    print(json.dumps(manifest["summaries"], ensure_ascii=False, indent=2), flush=True)
    print(f"Created 14 figures in 42 image/vector files. ZIP: {archive.name}", flush=True)


def write_readme(summaries):
    lines = ["# 各定位方法推荐层 × 真实编辑性能", "",
        "沿用已确认的 CMA-alt 热力图版式，新增其余六种定位方法及正式 CMA-ModelPred v2，共 7 种方法、14 张图。", "",
        "所有图使用同一份真实评测矩阵：21 个模型×数据集组合、377 个已评测层；逐条核对，与此前 CMA-alt 图的分数及配置完全一致。", "",
        "## 下载与浏览", "",
        "| 方法 | 统一色标 PNG | 行内差异增强 PNG | SVG | PDF |", "|---|---|---|---|---|"]
    for m in METHODS:
        s = m["stem"]
        lines.append(f'| {m["id"]} | [查看]({s}.png) | [查看]({s}_row_relative.png) | [矢量图]({s}.svg) | [矢量图]({s}.pdf) |')
    lines += ["", "行内差异增强版同样提供同名 SVG/PDF。所有 PNG 均为 6160 × 3300 像素。", "",
        "## 读图口径", "",
        "- 蓝色越深，真实 Average 越高；统一色标图始终采用 0–100 分，相同格子在所有方法图中的底色一致。",
        "- 红色实框标记当前方法 Top-3，橙色虚框标记第 4–5 名，角标数字是推荐次序。",
        "- 格内数字保留两位小数，着色使用原始精度；★ 是该组合已测主配置中的最高分，仅代表当前文档覆盖的层。",
        "- — 表示源文档无评测值；灰格表示无此层。缺失结果不填 0。",
        "- 优先 main；s 为 stable-only，e 为 recovered-early，! 为数值异常/nonfinite/stall 恢复记录。★ 排除 stable 和 recovered-early。",
        "- BLIP2-E 的 L18 使用原始实验 72.20，L18-2 重复实验 73.34 单独保存在原始数据中，不以取最大值覆盖。",
        "- 行内差异增强版按每行已显示分数的 min/max 归一化；数字仍是真实分数，但不同组合的深浅不能直接比较。",
        "- Ours 采用 M_abscos_x_newn = abs(S_v_cos) × S_v_new_norm。CMA-ModelPred v2 单独展示，未与历史 CMA-alt 混合。",
        "- CMA-ModelPred v2 的 † 保留源文档标记的排名不稳定或低覆盖；具体说明见对应数据 JSON。其他方法不继承 CMA-alt 的低覆盖标记。", "",
        "## 候选层评测覆盖", "",
        "以下仅统计有分数的候选数量，包含已标 s 的 stable-only；不是各方法的性能排名。", "",
        "| 方法 | Top-3 已评测 | Top-5 已评测 |", "|---|---:|---:|"]
    for s in summaries:
        lines.append(f'| {s["method"]} | {s["top3_evaluated"]}/63 | {s["top5_evaluated"]}/105 |')
    lines += ["", "## 可复核数据", "",
        "`shared_evaluation_data.json` 保存所有单元格状态、评测值、配置、源文档行号及完整原始记录。每个方法的 `_data.json` 保存 105 个候选的次序、分数和来源行号。", "",
        "`manifest.json` 保存输出文件哈希、共用评测矩阵哈希及核验结果；147 组方法×组合候选已同时对照推荐文档的第 3 节与第 4 节。", "",
        "生成脚本在 `source/` 留档；项目中的可直接执行版本为 `outputs/build_other_localization_heatmaps_20260921.py`。", "",
        "## 全部统一色标图", ""]
    for m in METHODS:
        lines += [f'### {m["id"]}', "", f'![{m["id"]}]({m["stem"]}.png)', ""]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
