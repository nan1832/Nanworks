"""Plot documented editing outcomes and versioned CMA recommendations.

Run from any directory with Python + matplotlib + numpy. Source markdown is
parsed as data; no source document is rewritten. All displayed scores retain
their source line, configuration and original precision in the JSON audit.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors, font_manager
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md"
CANDIDATES = ROOT / "md/TODO/Second_prashe/Firstprash_7_location_recommend.md"
MANUAL = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
OUT = ROOT / "outputs/cma_heatmap_20260921"
DATASETS = ["EVQA-pilot500", "MMKE-visual", "MMKE-entity"]
MODELS = ["BLIP2-OPT-2.7B", "InstructBLIP-Vicuna-7B", "MiniGPT-4-Vicuna-7B",
          "LLaVA-v1.5-7B", "Qwen2.5-VL-3B", "PaliGemma-3B", "SmolVLM-Instruct-1.7B"]
SHORT = ["BLIP2", "InstructBLIP", "MiniGPT-4", "LLaVA-1.5", "Qwen2.5-VL", "PaliGemma", "SmolVLM"]
NAVY, MUTED, GRID = "#183754", "#63778a", "#d0dbe4"
RED, ORANGE = "#d44834", "#dc9218"


def cells(line):
    return [s.strip() for s in line.strip().strip("|").split("|")]


def read_candidates(section="3.7"):
    """Read exactly one versioned method table; preserve its ranking and notes."""
    candidates = {}
    active = False
    for number, line in enumerate(CANDIDATES.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith(f"### {section} "):
            active = True
        elif active and line.startswith("##"):
            break
        if active and line.startswith("| "):
            c = cells(line)
            if c[0] not in DATASETS:
                continue
            top3, top5 = [[int(x[1:]) for x in col.split(",")] for col in c[2:4]]
            assert len(top3) == len(set(top3)) == 3
            assert len(top5) == len(set(top5)) == 5 and top3 == top5[:3]
            candidates[(c[0], c[1])] = dict(top3=top3, top5=top5, note=c[4], source_line=number)
    assert set(candidates) == {(d, m) for d in DATASETS for m in MODELS}
    return candidates


def read_data():
    records = []
    active = False
    dataset = model = None
    for number, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## 4. "):
            active = True
        elif active and line.startswith("## "):
            break
        if not active:
            continue
        if line.startswith("### 4."):
            dataset = line.split(" ", 2)[2]
        elif line.startswith("#### "):
            model = line[5:]
        elif line.startswith("| L"):
            c = cells(line)
            assert len(c) == 14, (number, c)
            match = re.fullmatch(r"L(\d+)(-\d+)?", c[0])
            assert match and dataset in DATASETS and model in MODELS
            score = None if c[12] in ("-", "—", "") else float(c[12])
            record = dict(dataset=dataset, model=model, layer=int(match[1]),
                          source_layer=c[0], replicate=bool(match[2]), config=c[1],
                          checkpoint_epoch=c[3], samples=int(c[6]), average=score,
                          average_source=c[12], status=c[13], source_line=number,
                          metrics=dict(zip(["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc"], c[7:12])))
            if score is not None:
                assert 0 <= score <= 100 and record["samples"] > 0
                assert "NO_EVAL" not in record["status"] and "FAILED" not in record["status"]
                avg = sum(map(float, c[7:12])) / 5
                record["average_recomputed_from_rounded_metrics"] = avg
                record["average_rounding_difference"] = score - avg
            records.append(record)
    candidates = read_candidates()

    depths = {}
    for line in MANUAL.read_text(encoding="utf-8").splitlines():
        if line.startswith("| "):
            c = cells(line)
            if len(c) == 4 and c[0] in MODELS and c[1].isdigit():
                depths[c[0]] = int(c[1])
    assert set(depths) == set(MODELS)
    grouped = defaultdict(list)
    for r in records:
        assert r["layer"] < depths[r["model"]]
        grouped[(r["dataset"], r["model"], r["layer"])].append(r)
    selected = {}
    for key, group in grouped.items():
        # Use the original run, not the L18-2 replicate; never select by score.
        usable = [r for r in group if r["average"] is not None and not r["replicate"]]
        if usable:
            priority = lambda r: {"main": 3, "main/legacy": 2, "main/recovered-early": 1, "stable": 0}[r["config"]]
            usable.sort(key=priority, reverse=True)
            assert len(usable) == 1 or priority(usable[0]) != priority(usable[1]), key
            selected[key] = usable[0]
    for (d, m), rec in candidates.items():
        assert all(0 <= layer < depths[m] for layer in rec["top5"])
    assert len({(r["dataset"], r["model"]) for r in records}) == 21
    return records, candidates, depths, selected


def tags(record):
    t = ""
    if record["config"] == "stable":
        t += "s"
    if record["config"] == "main/recovered-early":
        t += "e"
    if any(s in record["status"] for s in ("NUMERIC", "NONFINITE", "STALL")):
        t += "!"
    return t


def configure_fonts():
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        plt.rcParams["font.family"] = [font_manager.FontProperties(fname=str(font_path)).get_name(), "DejaVu Sans"]
    plt.rcParams.update({"axes.unicode_minus": False, "svg.fonttype": "path", "pdf.fonttype": 42})


def render(candidates, depths, selected, relative=False, *, method=None, output_dir=None):
    method = method or dict(short="CMA", label="CMA-Direct v1.3 / alt（与原图一致）",
                            section="3.7", stem="cma_alt_v13_editing_heatmap", legend="CMA",
                            caveat="† Qwen × MMKE-entity 的 CMA-alt 定位仅 9/636 样本有效（1.42%）。")
    output_dir = Path(output_dir) if output_dir is not None else OUT
    flagged = {key for key, rec in candidates.items()
               if any(token in rec["note"] for token in ("low_confidence", "unstable", "可用率低"))}
    fig = plt.figure(figsize=(28, 15), facecolor="white")
    # A large, flat matrix preserves the model/dataset order of the user's image.
    ax = fig.add_axes([.137, .219, .802, .643])
    ax.set_xlim(0, 36)
    ax.set_ylim(21, 0)
    ax.axis("off")
    cmap = colors.LinearSegmentedColormap.from_list("editing_blue", ["#f3f7fb", "#b9d7ea", "#64a5ce", "#246998", "#083558"])
    norm = colors.Normalize(0, 1 if relative else 100)
    rows = [(d, m) for m in MODELS for d in DATASETS]
    for row, (dataset, model) in enumerate(rows):
        rec = candidates[(dataset, model)]
        measured = [v for (d, m, _), v in selected.items() if (d, m) == (dataset, model)]
        values = [v["average"] for v in measured]
        lo, hi = min(values), max(values)
        comparable = [v for v in measured if v["config"] not in ("stable", "main/recovered-early")]
        best = max(v["average"] for v in comparable)
        for layer in range(36):
            record = selected.get((dataset, model, layer))
            if layer >= depths[model]:
                ax.add_patch(Rectangle((layer, row), 1, 1, facecolor="#dfe4e9", edgecolor=GRID, linewidth=.45))
                continue
            if record:
                score = record["average"]
                intensity = ((score-lo)/(hi-lo) if hi > lo else .5) if relative else score
                fill = cmap(norm(intensity))
            else:
                fill = "white"
            ax.add_patch(Rectangle((layer, row), 1, 1, facecolor=fill, edgecolor=GRID, linewidth=.5))
            rank = rec["top5"].index(layer) + 1 if layer in rec["top5"] else None
            if record:
                luminance = .2126*fill[0]+.7152*fill[1]+.0722*fill[2]
                ink = "white" if luminance < .53 else NAVY
                ax.text(layer+.5, row+.57, f'{record["average"]:.2f}', ha="center", va="center", color=ink, fontsize=8.5)
                if tags(record):
                    ax.text(layer+.85, row+.13, tags(record), ha="right", va="top", color=ink, fontsize=6.6, weight="bold")
                if record["config"] not in ("stable", "main/recovered-early") and abs(record["average"]-best) < 1e-9:
                    ax.text(layer+.5, row+.90, "★", ha="center", va="center", color=ink, fontsize=7.2)
            else:
                ax.text(layer+.5, row+.56, "—", ha="center", va="center", color="#a0adb8", fontsize=9)
            if rank:
                border = RED if rank <= 3 else ORANGE
                ax.add_patch(Rectangle((layer+.055, row+.065), .89, .87, facecolor="none", edgecolor="white", linewidth=3.2))
                ax.add_patch(Rectangle((layer+.055, row+.065), .89, .87, facecolor="none", edgecolor=border,
                                       linewidth=1.75, linestyle="-" if rank <= 3 else (0, (3, 1.5))))
                ax.text(layer+.12, row+.19, str(rank), color="white", va="center", ha="center", fontsize=6.2,
                        weight="bold", bbox=dict(boxstyle="square,pad=.12", fc=border, ec="none"))
        label = ["E", "V", "N"][DATASETS.index(dataset)]
        if (dataset, model) in flagged:
            label += "†"
        ax.text(-.23, row+.5, label, ha="right", va="center", color=RED if "†" in label else NAVY,
                fontsize=10.2, fontweight="bold", clip_on=False)
    for i, (model, short) in enumerate(zip(MODELS, SHORT)):
        y = i*3
        ax.add_patch(Rectangle((-5.1, y), 4.15, 3, fc="#f0f4f8" if i % 2 == 0 else "#f8fafc", ec="none", clip_on=False))
        ax.text(-1.22, y+1.30, short, ha="right", va="center", fontsize=12, fontweight="bold", color=NAVY, clip_on=False)
        ax.text(-1.22, y+1.90, f'{depths[model]} layers', ha="right", va="center", fontsize=8, color=MUTED, clip_on=False)
    for x in range(5, 36, 5):
        ax.plot([x, x], [0, 21], color="#8b9eaf", lw=.9, zorder=5)
    for y in range(0, 22, 3):
        ax.plot([-.75, 36], [y, y], color="#879eb2", lw=1.05, clip_on=False, zorder=5)
    ax.add_patch(Rectangle((0, 0), 36, 21, fc="none", ec="#849caf", lw=1.0, zorder=5))
    # Individual indices and five-layer header bands.
    for layer in range(36):
        ax.text(layer+.5, -.38, str(layer), ha="center", va="center", fontsize=9, color=NAVY, clip_on=False)
    for start in range(0, 36, 5):
        width = min(5, 36-start)
        ax.add_patch(Rectangle((start, -1.50), width, .68, fc=NAVY if (start//5)%2 == 0 else "#295071", ec="white", lw=.6, clip_on=False))
        ax.text(start+width/2, -1.16, f"{start}–{start+width-1}" if width > 1 else str(start), color="white", ha="center", va="center", fontsize=10, clip_on=False)
    ax.text(-1.15, -1.10, "模型 / 数据集", ha="right", va="center", color=NAVY, fontsize=11, weight="bold", clip_on=False)
    ax.text(36.42, -1.1, "行内\n相对值" if relative else "真实\nAverage", ha="center", va="center", color=NAVY, fontsize=9, clip_on=False)
    title = f'{method["short"]} 推荐层 × 真实编辑性能'
    fig.text(.026, .970, title, fontsize=27, color=NAVY, weight="bold", va="top")
    mode = "行内相对配色 · 格内仍为真实分数" if relative else "全图统一 0–100 分色标"
    fig.text(.026, .929, f'{method["label"]}    |    7 模型 × 3 数据集    |    {mode}', fontsize=12, color=MUTED)
    cbax = fig.add_axes([.955, .370, .010, .39])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbax)
    cb.set_ticks([0, .25, .5, .75, 1] if relative else [0, 20, 40, 60, 80, 100])
    cb.ax.tick_params(labelsize=9, colors=NAVY, length=3)
    cb.outline.set_edgecolor(GRID)
    fig.text(.960, .787, "越深\n越好", fontsize=10, ha="center", color=NAVY)
    if relative:
        fig.text(.960, .348, "行内归一化", fontsize=8, ha="center", color=MUTED)

    # Legend, with independent visual channels for scores and recommendations.
    legend_y = .169
    def key(x, text, edge, style="-", fill="white"):
        fig.add_artist(Rectangle((x, legend_y), .014, .018, transform=fig.transFigure, fc=fill, ec=edge, lw=1.8, linestyle=style))
        fig.text(x+.020, legend_y+.009, text, fontsize=10.2, color=NAVY, va="center")
    legend = method.get("legend", "本方法")
    key(.028, f"红色实框：{legend} Top-3", RED)
    key(.210, f"橙色虚框：{legend} 第 4–5 名", ORANGE, "--")
    fig.text(.425, legend_y+.009, "角标 1–5：推荐次序     ★：本行已测主配置最高分", fontsize=10.2, color=NAVY, va="center")
    key(.768, "—：文档无评测值", GRID)
    key(.903, "无此层", GRID, fill="#dfe4e9")
    fig.text(.028, .130, "E = EVQA-pilot500    V = MMKE-visual    N = MMKE-entity    |    Average = (Rel + T-Gen + M-Gen + T-Loc + M-Loc) / 5", fontsize=11, color=NAVY)
    fig.text(.028, .101, "配置：优先 main；s = 仅有 stable，e = 提前结束训练，! = 数值异常或恢复记录。★ 排除 stable 与 recovered-early；原始低分如实保留。", fontsize=10, color=MUTED)
    caveat = method.get("caveat", "† 表示源文档标记的定位排名不稳定或低覆盖。" if flagged else "")
    fig.text(.028, .073, caveat + "未评测不填 0；BLIP2-E 的 L18 使用原始记录，重复实验 L18-2 单列于数据文件。", fontsize=10, color=MUTED)
    footer = "颜色=(本行分数−本行最小值)/(本行最大值−本行最小值)，用于观察同组层间差异；不同组的深浅不可直接比较。" if relative else f'来源：用户指定评测表第 4 节 + 推荐表第 {method["section"]} 节。数字保留两位小数，颜色按原精度计算；已测最高分仅代表当前文档覆盖的层。'
    fig.text(.028, .043, footer, fontsize=9.6, color=MUTED)
    stem = method["stem"] + ("_row_relative" if relative else "")
    for ext in ("png", "svg", "pdf"):
        fig.savefig(output_dir / f"{stem}.{ext}", dpi=220, facecolor="white")
    plt.close(fig)
    return stem


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records, candidates, depths, selected = read_data()
    configure_fonts()
    stems = [render(candidates, depths, selected, relative=r) for r in (False, True)]
    audit_cells = []
    for model in MODELS:
        for dataset in DATASETS:
            rec = candidates[(dataset, model)]
            for layer in range(36):
                r = selected.get((dataset, model, layer))
                audit_cells.append(dict(dataset=dataset, model=model, layer=layer,
                    state="no_such_layer" if layer >= depths[model] else "evaluated" if r else "no_score_in_source",
                    cma_rank=rec["top5"].index(layer)+1 if layer in rec["top5"] else None,
                    candidate_source_line=rec["source_line"],
                    evaluation=r, marks=tags(r) if r else ""))
    counts = Counter(c["state"] for c in audit_cells)
    summary = dict(cells=dict(counts), configs=dict(Counter(r["config"] for r in selected.values())),
        top3_evaluated=sum(c["state"] == "evaluated" and c["cma_rank"] is not None and c["cma_rank"] <= 3 for c in audit_cells),
        top5_evaluated=sum(c["state"] == "evaluated" and c["cma_rank"] is not None for c in audit_cells),
        average_discrepancies=[r for r in records if r["average"] is not None and abs(r["average_rounding_difference"]) > .03])
    assert sum(counts.values()) == 21*36
    assert sum(c["cma_rank"] is not None for c in audit_cells) == 105
    audit = dict(generated_at=datetime.now().isoformat(timespec="seconds"), method="CMA-Direct-v1.3-alt",
        sources=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (SOURCE, CANDIDATES, MANUAL)],
        selection_policy="Original run, main > main/legacy > main/recovered-early > stable; never pick by maximum score. Exclude replicate L18-2 from matrix.",
        summary=summary, cells=audit_cells, all_source_records=records)
    (OUT / "cma_heatmap_data.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ["# CMA 候选层与真实编辑性能热力图", "",
              "本次按用户截图使用 **CMA-Direct v1.3 / alt**。候选取自推荐文档第 3.7 节，未与 ModelPred v2 混合。", "",
              f"![统一色标主图]({stems[0]}.png)", "",
              "- 蓝色越深，真实 Average 越高；全图共享 0–100 分色标。格内显示两位小数，颜色使用原始精度。",
              "- 红色实框为 Top-3，橙色虚框为第 4–5 名；角标数字为方法推荐次序。所有已有评测的层均着色，不限于 CMA 候选。",
              "- 白格的横线表示指定文档没有评测分数；灰格表示模型没有此层。二者都不按 0 分处理。",
              "- ★ 标出同一模型与数据集组合已测 main/main-legacy 中的最高值，只作为观察参照，不代表全层最优。",
              "- 优先 main；没有 main 时保留 stable 并标 s。e 表示 recovered-early，! 表示源状态含数值异常、nonfinite 或 stall 恢复。各配置不混作公平比较。",
              "- BLIP2-EVQA 的 L18 原始结果为 72.20；L18-2 为重复实验 73.34，保留在数据文件中，不通过取最大值覆盖原始层。",
              "- Qwen2.5-VL × MMKE-entity 的历史 CMA 只有 9/636 个有效定位样本（1.42%），行标签以 † 提示。",
              f"- 共展示 {counts['evaluated']} 个层的真实分数；Top-3 候选有 {summary['top3_evaluated']}/63 个具有评测值，Top-5 为 {summary['top5_evaluated']}/105（包含明确标记的 stable-only）。", "",
              "## 同组层间差异放大版", "",
              f"![行内相对配色]({stems[1]}.png)", "",
              "此图保留所有真实数字，但颜色按每行已显示分数的最小/最大值归一化：同组越高越深，不同组的颜色不能直接比较。", "",
              "## 可复核文件", "",
              "- `cma_heatmap_data.json`：全部原始记录、每格使用的分数与配置、源文档行号、候选排名、源文件 SHA-256。",
              "- 同名 PNG 为高清图，SVG/PDF 为矢量图。",
              "- 生成脚本：`../build_cma_eval_heatmap_20260921.py`。", "",
              "本图严格反映用户指定文档的当前内容，未把其他进度记录中的“完成”状态当作缺失的评测数值，也未查询服务器。", ""]
    (OUT / "README.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(str(OUT))


if __name__ == "__main__":
    main()
