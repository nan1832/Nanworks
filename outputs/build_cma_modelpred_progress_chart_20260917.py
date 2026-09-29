from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "md" / "Location" / "6location_7model_3datas_top_3_5_layers_outcome.md"
ACCEPTED = (
    ROOT
    / "md"
    / "Location"
    / "VisualGradient_11formula_analysis_files_20260720"
    / "analysis_outputs_20260731"
    / "accepted_outcome_rows.csv"
)
LIVE = ROOT / "outputs" / "formal7_live_main_outcomes_20260824.csv"
NEW_UNION = ROOT / "outputs" / "formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv"
OLD_UNION = ROOT / "outputs" / "formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv"
OUT_PNG = (
    ROOT
    / "md"
    / "TODO"
    / "Second_prashe"
    / "真实扫层完成度_CMA-ModelPred_v2_20260917.png"
)
OUT_CSV = ROOT / "outputs" / "cma_modelpred_v2_progress_20260917.csv"

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
MODEL_SHORT = ["BLIP2", "Instruct", "MiniGPT-4", "LLaVA", "Qwen2.5", "PaliGemma", "SmolVLM"]
DATASET_SHORT = ["EVQA", "MMKE-V", "MMKE-E"]
DISPLAY_DATASET = {
    "evqa-pilot500": "EVQA-pilot500",
    "mmke-visual": "MMKE-visual",
    "mmke-entity": "MMKE-entity",
}
DISPLAY_MODEL = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}
MODEL_FROM_MANUAL = {
    "blip2-opt-2.7b": "BLIP2-OPT-2.7B",
    "instructblip-vicuna-7b": "InstructBLIP-Vicuna-7B",
    "minigpt-4-vicuna-7b": "MiniGPT-4-Vicuna-7B",
    "llava-v1.5-7b": "LLaVA-v1.5-7B",
    "qwen2.5-vl-3b": "Qwen2.5-VL-3B",
    "paligemma-3b": "PaliGemma-3B",
    "smolvlm-1.7b": "SmolVLM-Instruct-1.7B",
}
KNOWN_FAILURES = {
    ("EVQA-pilot500", "PaliGemma-3B", "L0"),
    ("MMKE-visual", "PaliGemma-3B", "L0"),
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def layers(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip() and item.strip() != "-"]


# Main-configuration results only. Stable-only rows are deliberately excluded to
# preserve the exact protocol stated in the original figure.
main_done: set[tuple[str, str, str]] = set()
for row in rows(ACCEPTED):
    if row["variant"] != "main":
        continue
    main_done.add(
        (
            DISPLAY_DATASET[row["dataset"]],
            DISPLAY_MODEL[row["model"]],
            f"L{int(row['layer'])}",
        )
    )

for row in rows(LIVE):
    if row["variant"] != "main" or row["status"] != "EVAL_DONE":
        continue
    main_done.add(
        (
            DISPLAY_DATASET[row["dataset"]],
            DISPLAY_MODEL[row["model"]],
            f"L{int(row['layer'])}",
        )
    )

# Add the latest detailed rows from section 4.0 of the current manual.
manual_lines = MANUAL.read_text(encoding="utf-8").splitlines()
inside = False
current_dataset: str | None = None
for line in manual_lines:
    if line == "### 4.0 服务器结构化结果总表":
        inside = True
        continue
    if line == "### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B":
        break
    if not inside:
        continue
    if line == "#### EVQA-pilot500":
        current_dataset = "EVQA-pilot500"
        continue
    if line == "#### MMKE-visual":
        current_dataset = "MMKE-visual"
        continue
    if line == "#### MMKE-entity":
        current_dataset = "MMKE-entity"
        continue
    if current_dataset is None or not line.startswith("|"):
        continue
    cols = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(cols) != 13 or cols[0] not in MODEL_FROM_MANUAL:
        continue
    status = cols[12]
    if "STABLE" in status or "FAILED" in status or "NO_EVAL" in status or cols[11] == "-":
        continue
    main_done.add((current_dataset, MODEL_FROM_MANUAL[cols[0]], cols[1]))

# Read-only server verification on 2026-09-17 found these two results complete
# after the latest local manual update. Both have train.done, nonempty
# selected_checkpoint.tsv and eval_full.done on their compute node.
SERVER_VERIFIED_INCREMENT = {
    ("EVQA-pilot500", "LLaVA-v1.5-7B", "L0"),
    ("MMKE-entity", "LLaVA-v1.5-7B", "L22"),
}
main_done.update(SERVER_VERIFIED_INCREMENT)


def calculate(union_path: Path) -> list[dict[str, object]]:
    union_lookup = {(row["dataset"], row["model"]): row for row in rows(union_path)}
    if set(union_lookup) != {(dataset, model) for dataset in DATASETS for model in MODELS}:
        raise RuntimeError(f"Union coverage mismatch: {union_path}")
    result: list[dict[str, object]] = []
    for dataset in DATASETS:
        for model in MODELS:
            union = layers(union_lookup[(dataset, model)]["top3_union"])
            completed = [layer for layer in union if (dataset, model, layer) in main_done]
            failed = [layer for layer in union if (dataset, model, layer) in KNOWN_FAILURES]
            pending = [layer for layer in union if layer not in completed and layer not in failed]
            result.append(
                {
                    "dataset": dataset,
                    "model": model,
                    "done": len(completed),
                    "total": len(union),
                    "percent": 100.0 * len(completed) / len(union),
                    "completed_layers": ",".join(completed) or "-",
                    "failed_layers": ",".join(failed) or "-",
                    "pending_layers": ",".join(pending) or "-",
                }
            )
    return result


new_progress = calculate(NEW_UNION)
old_progress_now = calculate(OLD_UNION)
new_lookup = {(row["dataset"], row["model"]): row for row in new_progress}

new_done_total = sum(int(row["done"]) for row in new_progress)
new_total = sum(int(row["total"]) for row in new_progress)
new_complete_combos = sum(int(row["done"]) == int(row["total"]) for row in new_progress)
old_now_done_total = sum(int(row["done"]) for row in old_progress_now)
old_now_total = sum(int(row["total"]) for row in old_progress_now)
old_now_complete_combos = sum(int(row["done"]) == int(row["total"]) for row in old_progress_now)

if new_total != 306 or old_now_total != 317:
    raise RuntimeError(f"Unexpected union totals: modelpred={new_total}, alt={old_now_total}")

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(new_progress[0]))
    writer.writeheader()
    writer.writerows(new_progress)


def choose_font() -> str:
    preferred = ["Microsoft YaHei", "Microsoft YaHei UI", "SimHei", "Noto Sans CJK SC"]
    installed = {item.name for item in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in installed:
            return name
    return "DejaVu Sans"


font = choose_font()
plt.rcParams["font.family"] = font
plt.rcParams["axes.unicode_minus"] = False

fig = plt.figure(figsize=(16, 9), dpi=160, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")

navy = "#123E70"
blue = "#2F6FDF"
green = "#16A36B"
orange = "#F39A32"
red = "#F05A5A"
border = "#D7E4F4"

ax.text(0.32, 8.57, "真实扫层完成度", fontsize=27, fontweight="bold", color=navy, va="center")
ax.plot([0.32, 1.62], [8.26, 8.26], lw=4, color=blue, solid_capstyle="butt")
ax.text(
    1.78,
    8.25,
    "CMA-ModelPred v2｜按7种正式方法Top-3候选层并集统计｜主配置计入，stable-only不计入",
    fontsize=11.5,
    color="#55718D",
    va="center",
)

badge = FancyBboxPatch((13.55, 8.30), 1.95, 0.48, boxstyle="round,pad=0.03,rounding_size=0.11", facecolor="#EEF6FF", edgecolor="#BCD6F5", linewidth=1.5)
ax.add_patch(badge)
ax.text(14.525, 8.54, "新版实验进度", color=blue, fontsize=11, fontweight="bold", ha="center", va="center")

left = 1.95
cell_w = 1.78
cell_h = 1.12
col_gap = 0.18
row_gap = 0.18
top_y = 6.30

for col, label in enumerate(MODEL_SHORT):
    x = left + col * (cell_w + col_gap) + cell_w / 2
    ax.text(x, 7.66, label, fontsize=12, fontweight="bold", color="#102E55", ha="center", va="center")

for row_idx, dataset_label in enumerate(DATASET_SHORT):
    y = top_y - row_idx * (cell_h + row_gap)
    ax.text(1.45, y + cell_h / 2, dataset_label, fontsize=15, fontweight="bold", color="#0F315D", ha="right", va="center")
    dataset = DATASETS[row_idx]
    for col_idx, model in enumerate(MODELS):
        item = new_lookup[(dataset, model)]
        done = int(item["done"])
        total = int(item["total"])
        pct = float(item["percent"])
        if pct >= 99.999:
            fill, accent = "#E2F5E9", green
        elif pct >= 80:
            fill, accent = "#E8F2FF", blue
        elif pct >= 40:
            fill, accent = "#FFF1D9", orange
        else:
            fill, accent = "#FDE6E6", red
        x = left + col_idx * (cell_w + col_gap)
        box = FancyBboxPatch((x, y), cell_w, cell_h, boxstyle="round,pad=0.018,rounding_size=0.07", facecolor=fill, edgecolor="none")
        ax.add_patch(box)
        ax.text(x + cell_w / 2, y + 0.69, f"{done}/{total}", fontsize=18, fontweight="bold", color=accent, ha="center", va="center")
        ax.text(x + cell_w / 2, y + 0.31, f"{pct:.0f}%", fontsize=10.5, color="#55718D", ha="center", va="center")

summary_y = 0.60
summary_h = 1.45

def summary_box(x: float, width: float, accent: str, title: str, main: str, sub: str) -> None:
    box = FancyBboxPatch((x, summary_y), width, summary_h, boxstyle="round,pad=0.025,rounding_size=0.08", facecolor="white", edgecolor=border, linewidth=1.6)
    ax.add_patch(box)
    ax.add_patch(plt.Rectangle((x, summary_y), 0.09, summary_h, facecolor=accent, edgecolor="none"))
    ax.text(x + 0.36, summary_y + 1.12, title, fontsize=12.5, color="#183B66", fontweight="bold", va="center")
    ax.text(x + 0.36, summary_y + 0.68, main, fontsize=23, color=accent, fontweight="bold", va="center")
    ax.text(x + 0.36, summary_y + 0.25, sub, fontsize=9.5, color="#637D98", va="center")


summary_box(0.70, 4.05, blue, "总体完成", f"{new_done_total} / {new_total}", f"主配置已覆盖 {100 * new_done_total / new_total:.1f}% 的新版Top-3并集")
summary_box(5.20, 4.05, green, "完整组合", f"{new_complete_combos} / 21", "全部七方法Top-3推荐层均已有正式评测")

comparison = FancyBboxPatch((9.70, summary_y), 5.60, summary_h, boxstyle="round,pad=0.025,rounding_size=0.08", facecolor="white", edgecolor=border, linewidth=1.6)
ax.add_patch(comparison)
ax.add_patch(plt.Rectangle((9.70, summary_y), 0.09, summary_h, facecolor=orange, edgecolor="none"))
ax.text(10.06, summary_y + 1.12, "与历史CMA-alt口径对照", fontsize=12.5, color="#183B66", fontweight="bold", va="center")
ax.text(10.06, summary_y + 0.72, f"并集总量：317 → 306（−11）", fontsize=14.5, color="#D97916", fontweight="bold", va="center")
ax.text(10.06, summary_y + 0.39, f"按同一当前完成集：alt {old_now_done_total}/317、{old_now_complete_combos}/21组；ModelPred {new_done_total}/306、{new_complete_combos}/21组", fontsize=9.8, color="#506B86", va="center")
ax.text(10.06, summary_y + 0.15, "原图228/317、12/21是旧时间快照；新图同时反映候选并集变化与后续新增评测。", fontsize=9.2, color="#7A5A3B", va="center")

ax.text(0.72, 0.25, "注：完成须具备正式评测结果；2026-09-17只读服务器复核新增计入 EVQA×LLaVA L0、MMKE-entity×LLaVA L22。PaliGemma L0不收敛仍不按0分填充。", fontsize=8.8, color="#667A90")

OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PNG, bbox_inches="tight", pad_inches=0.08, facecolor="white")
plt.close(fig)

print(f"PNG={OUT_PNG}")
print(f"CSV={OUT_CSV}")
print(f"MODELPRED={new_done_total}/{new_total}; COMPLETE_COMBOS={new_complete_combos}/21")
print(f"ALT_SAME_CURRENT_RESULTS={old_now_done_total}/{old_now_total}; COMPLETE_COMBOS={old_now_complete_combos}/21")
for item in new_progress:
    print(f"{item['dataset']}|{item['model']}|{item['done']}/{item['total']}|pending={item['pending_layers']}|failed={item['failed_layers']}")
