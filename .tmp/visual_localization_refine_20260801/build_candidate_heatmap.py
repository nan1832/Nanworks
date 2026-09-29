from pathlib import Path
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

ROOT = Path(r"D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset")
SOURCE = ROOT / "md" / "Location" / "6location_7model_3datas_top_3_5_layers_outcome.md"
OUT = ROOT / "outputs" / "三个数据集_七模型_候选定位方法_Top5热力图.png"

DATASETS = ["EVQA-pilot500", "MMKE-visual", "MMKE-entity"]
MODELS = [
    "BLIP2-OPT-2.7B",
    "InstructBLIP-Vicuna-7B",
    "MiniGPT-4-Vicuna-7B",
    "LLaVA-v1.5-7B",
    "Qwen2.5-VL-3B",
    "PaliGemma-3B",
    "SmolVLM-Instruct-1.7B",
]
MODEL_SHORT = {
    "BLIP2-OPT-2.7B": "BLIP2",
    "InstructBLIP-Vicuna-7B": "InstructBLIP",
    "MiniGPT-4-Vicuna-7B": "MiniGPT-4",
    "LLaVA-v1.5-7B": "LLaVA",
    "Qwen2.5-VL-3B": "Qwen2.5-VL",
    "PaliGemma-3B": "PaliGemma",
    "SmolVLM-Instruct-1.7B": "SmolVLM",
}
MODEL_LAYERS = {
    "BLIP2-OPT-2.7B": 32,
    "InstructBLIP-Vicuna-7B": 32,
    "MiniGPT-4-Vicuna-7B": 32,
    "LLaVA-v1.5-7B": 32,
    "Qwen2.5-VL-3B": 36,
    "PaliGemma-3B": 18,
    "SmolVLM-Instruct-1.7B": 24,
}

BASE_METHODS = {
    "Middle-Prior-Direct": "Middle",
    "VisEdit-Contrib-Pre-KeyToken": "VisEdit",
    "SaLEM-Alt-Direct": "SaLEM",
    "LGA-Param-Direct-AltModelPred": "LGA",
    "Perturb-KL-Direct-AltSeq": "Perturb-KL",
    "CMA-Direct": "CMA",
}
OURS_METHODS = {
    "Ours-Direct-Conflict": "Ours-Conflict",
    "Ours-AbsDirection-Direct": "Ours-AbsDir",
    "Ours-NoDirection-Direct": "Ours-NoDir",
    "Ours-1MinusCos-Direct": "Ours-1−Cos",
}
METHODS = list(BASE_METHODS.values()) + list(OURS_METHODS.values())
MAX_LAYERS = 36

def table_cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def parse_layers(value: str):
    return [int(x) for x in re.findall(r"L(\d+)", value)]

text = SOURCE.read_text(encoding="utf-8")
lines = text.splitlines()

records = {}

# 正式表 2.12：六个基线方法；Ours 总类在这里指向 2.7.1，故单独展开四个指标。
start = next(i for i, line in enumerate(lines) if line.startswith("### 2.12 "))
end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("### 2.13 ")), len(lines))
for line in lines[start:end]:
    if not line.startswith("|"):
        continue
    cells = table_cells(line)
    if len(cells) < 7 or cells[0] not in DATASETS:
        continue
    dataset, model, method, _, top3, top5, status = cells[:7]
    if model in MODELS and method in BASE_METHODS:
        records[(dataset, model, BASE_METHODS[method])] = {
            "top3": parse_layers(top3),
            "top5": parse_layers(top5),
            "status": status,
        }

# 2.7.1 以及后续完整表中的 Ours 四指标。重复条目数值一致，后出现者覆盖不影响结果。
for line in lines:
    if not line.startswith("|"):
        continue
    cells = table_cells(line)
    if len(cells) < 6 or cells[0] not in DATASETS:
        continue
    dataset, model, method = cells[0], cells[1], cells[2]
    if model not in MODELS or method not in OURS_METHODS:
        continue
    top3, top5 = cells[3], cells[4]
    status = cells[5] if len(cells) > 5 else ""
    records[(dataset, model, OURS_METHODS[method])] = {
        "top3": parse_layers(top3),
        "top5": parse_layers(top5),
        "status": status,
    }

expected = len(DATASETS) * len(MODELS) * len(METHODS)
missing = [(d, m, h) for d in DATASETS for m in MODELS for h in METHODS if (d, m, h) not in records]
if missing:
    raise RuntimeError(f"缺少 {len(missing)} 条记录，示例：{missing[:5]}")
if len(records) < expected:
    raise RuntimeError(f"记录数不足：{len(records)} / {expected}")

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
})

rows = [(m, method) for m in MODELS for method in METHODS]
nrows = len(rows)

# -1: 超出模型层数；0: 有效但未入选；1-5: Top-5 排名。
colors = ["#D5DAE2", "#F6F8FB", "#064E3B", "#0F766E", "#14B8A6", "#99F6E4", "#CCFBF1"]
cmap = ListedColormap(colors)
norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5], cmap.N)

fig, axes = plt.subplots(1, 3, figsize=(22, 18.5), dpi=240, sharey=True)
fig.subplots_adjust(left=0.185, right=0.985, top=0.89, bottom=0.115, wspace=0.035)

for ax, dataset in zip(axes, DATASETS):
    mat = np.zeros((nrows, MAX_LAYERS), dtype=float)
    empty_rows = []
    partial_rows = []
    for ri, (model, method) in enumerate(rows):
        layer_count = MODEL_LAYERS[model]
        mat[ri, layer_count:] = -1
        rec = records[(dataset, model, method)]
        ranked = rec["top5"]
        if not ranked:
            empty_rows.append(ri)
        elif len(ranked) < 5:
            partial_rows.append(ri)
        for rank, layer in enumerate(ranked[:5], start=1):
            if 0 <= layer < layer_count:
                mat[ri, layer] = rank

    ax.imshow(mat, cmap=cmap, norm=norm, aspect="auto", interpolation="none")
    ax.set_title(dataset, fontsize=18, fontweight="bold", pad=18, color="#16324F")
    ax.set_xlim(-0.5, MAX_LAYERS - 0.5)
    ax.set_xticks(np.arange(0, MAX_LAYERS, 2))
    ax.set_xticklabels([f"L{i}" for i in range(0, MAX_LAYERS, 2)], fontsize=8)
    ax.set_xlabel("编辑插入层（0-indexed）", fontsize=11, labelpad=10)
    ax.set_xticks(np.arange(-0.5, MAX_LAYERS, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, nrows, 1), minor=True)
    ax.grid(which="minor", color="#FFFFFF", linewidth=0.55)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="x", length=0, pad=5)
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_color("#C7CFDA")
        spine.set_linewidth(0.8)

    # 每个候选格标注其 Top-5 排名。
    for ri in range(nrows):
        for layer in np.where(mat[ri] > 0)[0]:
            rank = int(mat[ri, layer])
            text_color = "white" if rank <= 3 else "#134E4A"
            ax.text(layer, ri, str(rank), ha="center", va="center", fontsize=6.2,
                    color=text_color, fontweight="bold")

    # 空候选与不足 Top-5 用右侧符号标记，避免与普通未选层混淆。
    for ri in empty_rows:
        ax.text(MAX_LAYERS - 0.05, ri, "×", ha="left", va="center", fontsize=9,
                color="#DC2626", fontweight="bold", clip_on=False)
    for ri in partial_rows:
        ax.text(MAX_LAYERS - 0.05, ri, "△", ha="left", va="center", fontsize=7.5,
                color="#D97706", fontweight="bold", clip_on=False)

    for boundary in range(len(METHODS), nrows, len(METHODS)):
        ax.axhline(boundary - 0.5, color="#52606D", linewidth=1.35)

yticklabels = [f"{MODEL_SHORT[m]} · {method}" for m, method in rows]
axes[0].set_yticks(np.arange(nrows))
axes[0].set_yticklabels(yticklabels, fontsize=7.2)
for tick, (_, method) in zip(axes[0].get_yticklabels(), rows):
    if method.startswith("Ours"):
        tick.set_color("#047857")
        tick.set_fontweight("bold")

for ax in axes[1:]:
    ax.tick_params(labelleft=False)

fig.suptitle("三个数据集 × 7 个模型 × 候选定位方法：Top-5 层热力图",
             fontsize=26, fontweight="bold", x=0.5, y=0.965, color="#172B4D")
fig.text(0.5, 0.925,
         "每行对应一个模型与方法；色块数字为候选排名。Ours 展开为文档中登记的 4 个正式指标。",
         ha="center", fontsize=12, color="#52606D")

legend_handles = [
    Patch(facecolor="#064E3B", edgecolor="none", label="Top-1"),
    Patch(facecolor="#0F766E", edgecolor="none", label="Top-2"),
    Patch(facecolor="#14B8A6", edgecolor="none", label="Top-3"),
    Patch(facecolor="#99F6E4", edgecolor="none", label="Top-4"),
    Patch(facecolor="#CCFBF1", edgecolor="none", label="Top-5"),
    Patch(facecolor="#D5DAE2", edgecolor="none", label="超出该模型层数"),
]
fig.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, 0.066),
           ncol=6, frameon=False, fontsize=10, handlelength=1.5, columnspacing=1.6)
fig.text(0.5, 0.035,
         "注：EVQA-pilot500 的 VisEdit 当前仍为历史 FirstToken 口径；MMKE 两个数据集为 strict KeyToken。"
         "CMA 低覆盖组合仍按文档候选层展示；本图表示候选排名，不代表真实编辑性能或置信度。"
         " × = 无有效候选，△ = 候选不足 Top-5。",
         ha="center", fontsize=9.5, color="#5F6B7A")
fig.text(0.985, 0.012,
         "数据来源：6location_7model_3datas_top_3_5_layers_outcome.md（§2.7.1、§2.12）",
         ha="right", fontsize=8.5, color="#7A869A")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
plt.close(fig)

print(f"OUT={OUT}")
print(f"RECORDS={len(records)} EXPECTED={expected}")
print(f"BYTES={OUT.stat().st_size}")
