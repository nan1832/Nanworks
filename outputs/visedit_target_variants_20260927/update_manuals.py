"""Update candidate registries without changing archived experiment results."""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LEDGER = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
HANDBOOK = ROOT / "md/Location/6edit_layer_localization_candidate_methods_简洁说明版.md"
rows = list(csv.DictReader((OUT / "visedit_target_candidates_21x2.csv").open(encoding="utf-8-sig")))
by_key = {(r["dataset"], r["model"], r["target_mode"]): r for r in rows}
ALT = "VisEdit-Contrib-Pre-alt"
PRED = "VisEdit-Contrib-Pre-model_pred"

def link(label, path):
    return f"[{label}](<{path.as_posix()}>)"

def replace_once(text, old, new):
    assert text.count(old) == 1, (old[:100], text.count(old))
    return text.replace(old, new, 1)

def replace_section(text, start, end, body):
    a, tail = text.split(start, 1)
    _, b = tail.split(end, 1)
    return a + body.rstrip() + "\n\n" + end + b

def status(r):
    if r["status"] != "done":
        return "待计算；已有 pred 字段归因，不能替代 model_pred"
    if r["target_mode"] == "model_pred":
        return "归因已完成；本次派生 Pre 候选；n=500"
    return ("FirstToken；n=500" if r["dataset"] == "EVQA-pilot500" else
            f"dataset-specific KeyToken；n={r['sample_count']}")

def full_row(r):
    source = r["token_rule"] if r["status"] == "done" else "model_pred_scores_missing; existing pred != model_pred"
    return "| " + " | ".join([r["dataset"], r["model"], r["method"], source,
                                r["top3"] or "待计算", r["top5"] or "待计算", status(r)]) + " |"

original = (OUT / "backups" / LEDGER.name).read_text(encoding="utf-8-sig")
assert LEDGER.read_text(encoding="utf-8-sig") == original, "Ledger changed since snapshot; inspect before overwriting"
text = original
intro_start = "本文档记录后续真实扫层实验要比较的候选编辑层。"
intro_end = "## 0. 目录结构"
intro = f"""本文档登记候选编辑层及真实扫层结果。VisEdit 统一按目标来源区分为 `{ALT}`（新目标）与 `{PRED}`（模型当前预测，即旧响应侧），二者属于同一 VisEdit 方法族，共用模块贡献度与 Pre 选层规则。当前登记 7 个方法族、8 个方法版本；Oracle 另列为上界，消融单独报告。方法定义见 {link('候选层计算手册', HANDBOOK)}。

> **VisEdit 更新（2026-09-27）：** `alt` 已有 21/21 组候选；`model_pred` 从现有 EVQA 七组逐层分数补算得到，MMKE 十四组待计算。原表只列了 `alt`；2.12 中六组过期 MMKE FirstToken 候选已与 2.2、2.11 的 KeyToken 结果对齐。`pred` 字段归因不能改名为 `model_pred`。本次更正不代表已经完成新增候选层的真实编辑评测。

登记的方法版本：

1. `Middle-Prior-Direct`
2. `{ALT}`
3. `{PRED}`
4. `SaLEM-Alt-Direct`
5. `LGA-Param-Tukey`（当前补正版）；`LGA-Param-Direct-AltModelPred` 是保留的 Raw 历史/消融版。
6. `Perturb-KL-Direct-AltSeq`
7. `Ours-Direct`
8. `CMA-ModelPred-Direct`（当前版）；`CMA-Direct v1.3/alt` 保留为历史版。

`Candidate-union Oracle` / `Full-layer Oracle` 只作为真实扫层上界。附加/消融包括 `Perturb-KL-Pre-AltSeq`、Ours 其他指标、VisEdit 历史 FirstToken 和 LGA Raw。

第 3 节的既有并集与阶段指标是冻结记录，尚未纳入本次新增的 VisEdit `model_pred`；不能据此称八个方法版本已经全部可比。LGA Tukey 补正另见 2.4.1。
"""
text = replace_section(text, intro_start, intro_end, intro)
text = replace_once(text, "  - 2.2 VisEdit-Contrib-Pre-KeyToken，主实验待补；当前回填为历史 `FirstToken`", "  - 2.2 VisEdit-Contrib-Pre-alt / model_pred：两版候选、目标定义与覆盖状态")
text = replace_once(text, "  - 2.10 当前可立即开跑的真实扫层并集", "  - 2.10 第一版真实扫层并集（历史冻结）")
text = replace_once(text, "- 3. 数据集分表：历史候选范围与真实扫层状态；3.4.5保留历史CMA-alt七方法并集，3.4.6给出当前CMA-ModelPred七方法Top-3/Top-5并集、完成状态和阶段指标。", "- 3. 数据集分表：保留既有候选并集、完成状态和阶段指标；这些冻结版本仅包含 VisEdit-alt，未纳入本次新增 model_pred。")
rules = f"""## 1. 统一规则

- 层编号为 0-indexed，例如 `L0` 到 `L31`；候选层仍表示同一 adapter 插入接口。
- **VisEdit 目标来源与 token 选择分开登记。** `{ALT}` 表示新目标侧：EVQA 沿用 `alt` 首个 tokenizer token；MMKE-entity 使用 `alt_entity_anchor`；MMKE-visual 使用 `m_rel_ans` / `rel_ans` 中的视觉语义 token。MMKE 这套结果的历史名称为 strict KeyToken，不等于逐样本都选中了新旧事实差异词。
- `{PRED}` 表示未编辑基础模型在原问题与图像上的**下一 token 概率最高项**，即当前响应侧；不是数据集 `pred` 字段，也不是完整旧答案序列。它与 CMA/LGA 中完整 `model_pred` 序列的目标粒度不同。
- 两版都在未编辑基础模型上计算模块贡献，区别在归因目标。`score_positive = max(0, attn_mean) + max(0, mlp_mean)`。
- 同用 3 层滑动平均，边界截短窗口；阈值为平滑分数的 `mean + 0.5 * std`（`ddof=0`），取最长连续高贡献区；长度相同取平滑分数和较大者，再取起始较浅者。
- 若高贡献区起始为 `s_H`，Pre Top-K 为 `s_H-1, s_H-2, ..., s_H-K`；遇到 L0 截止，不补齐。Top-K 是**编辑候选层**，不是贡献峰值层。
- 缺少 `model_pred` 分数的组合记“待计算”，不能填零、复制 alt 或用 `pred` 归因代替。两版方法比较须采用双方候选及真实编辑评测均完整的共同组合，并注明 token 规则差异。
"""
text = replace_section(text, "## 1. 统一规则", "## 2. 候选层方法", rules)

old22 = original.split("### 2.2 ", 1)[1].split("### 2.3", 1)[0]
history = "#### 2.2.1" + old22.split("#### 2.2.1", 1)[1]
history = history.replace("正式 KeyToken 方法", "VisEdit-alt 的 MMKE KeyToken 版本")
history = history.replace("#### 2.2.2 VisEdit-Contrib-Pre-FirstToken 历史来源表", "#### 2.2.2 VisEdit-alt 历史 FirstToken 来源表")
history = history.replace("MMKE 严格 KeyToken 全量结果已写入本节主表和 2.11 综合全面版", "MMKE dataset-specific KeyToken 全量结果已写入本节主表及 2.11、2.12 综合表")
section22 = f"""### 2.2 VisEdit-Contrib-Pre-alt 与 VisEdit-Contrib-Pre-model_pred

两版采用相同的 VisEdit-style 模块输出贡献度与高贡献区前置规则，仅按目标来源命名。高贡献区自动阈值是本实验的统一操作规则；名称不表示两版均为 VisEdit 原文的逐项严格复现。

`alt` 现有 21 组：EVQA 七组为原 pilot500 FirstToken，MMKE 十四组为 2026-07-04 的 dataset-specific KeyToken 全量结果。`model_pred` 已核实 EVQA 七组 `key_mode=model_pred` 的原始贡献度，按同一规则离线生成候选，未重新运行模型。MMKE 共享归档与本地记录中的旧侧结果均为 `key_mode=pred`，不能作为这十四组的 model_pred 结果。

| Dataset | Model | Method | Top-3 | Top-5 | 状态/目标粒度 |
|---|---|---|---|---|---|
"""
for r in rows:
    section22 += "| " + " | ".join([r["dataset"], r["model"], r["method"], r["top3"] or "待计算", r["top5"] or "待计算", status(r)]) + " |\n"
section22 += "\n" + history.rstrip() + "\n\n"
section22 += f"""#### 2.2.3 model_pred 候选的原始来源与复算

`model_pred` 的代码分支将 `predict_word=None` 传入追踪器，追踪器取基础模型下一 token 的 argmax。历史 `config.json` 中的通用 `token_rule=first token of target answer` 文本没有随模式更新，实际解释以 `key_mode` 和执行分支为准。MMKE `pred` 分支读取 `row['pred']` 后取 tokenizer 首 token，不存在自动等同 model_pred 的规则。

EVQA 七组原始分数及配置已核对，样本数均为 500。采用已有脚本中的平滑、区间识别及 Pre 函数；先复算历史 alt 的全部 21 组，Top-3/Top-5 均与历史表一致，再对 model_pred 派生候选。

| Model | 高贡献区间 | Top-3 | Top-5 | 原始逐层分数 |
|---|---|---|---|---|
"""
for r in rows:
    if r["target_mode"] == "model_pred" and r["status"] == "done":
        section22 += f"| {r['model']} | {r['high_region']} | {r['top3']} | {r['top5']} | {link('contribution_layer.csv', ROOT / r['source'])} |\n"
section22 += f"\n完整登记见 {link('42 行机器可读候选表', OUT / 'visedit_target_candidates_21x2.csv')}；来源哈希与规则见 {link('复算协议', OUT / 'protocol_and_sources.json')}；MMKE 归档核对范围见 {link('服务器只读核对记录', OUT / 'server_archive_audit.json')}。\n\n"
section22 += "#### 2.2.4 两版候选差异与后续并集使用\n\nEVQA 七组的 Top-3、Top-5 均因目标改变而发生变化。下表只计算两版 VisEdit 的候选差集，不表示这些层尚未训练；训练/评测状态须另查实际结果。MMKE 缺 model_pred，暂不能形成完整双目标并集。\n\n| Dataset | Model | model_pred Top-3 相对 alt 新增 | model_pred Top-5 相对 alt 新增 |\n|---|---|---|---|\n"
for r in rows:
    if r["target_mode"] == "model_pred" and r["status"] == "done":
        a = by_key[(r["dataset"], r["model"], "alt")]
        diffs = [",".join(v for v in r[k].split(",") if v not in a[k].split(",")) or "无" for k in ["top3", "top5"]]
        section22 += f"| {r['dataset']} | {r['model']} | {diffs[0]} | {diffs[1]} |\n"
text = replace_section(text, "### 2.2 ", "### 2.3", section22)

section29 = f"""### 2.9 正式候选方法说明

当前按 7 个方法族、8 个目标/方法版本登记。VisEdit 的 `{ALT}` 与 `{PRED}` 同属贡献度 Pre 方法，分别报告，不能把二者合并成一项后取较好结果。

| Method | 候选层生成方式 | 当前状态 |
|---|---|---|
| `Middle-Prior-Direct` | 网络中点先验 | 已登记 |
| `{ALT}` | 新目标 token 模块贡献，高贡献区前置 | 21/21；EVQA FirstToken 7 组，MMKE KeyToken 14 组 |
| `{PRED}` | 当前下一 token 预测的模块贡献，高贡献区前置 | EVQA 7/21 已派生候选；MMKE 14/21 待计算 |
| `SaLEM-Alt-Direct` | 参数梯度显著性 | 21/21 |
| `LGA-Param-Tukey` | 参数梯度内积经 Tukey 过滤后排序 | 21/21，见 2.4.1；2.4 与综合表 Raw 行为历史/消融 |
| `Perturb-KL-Direct-AltSeq` | 完整 alt 序列的视觉扰动 KL | 21/21 |
| `Ours-Direct` | 当前登记主公式 `abs(S_v_cos) * S_v_new_norm` | 21/21；其他公式单列消融 |
| `CMA-ModelPred-Direct` | 基础模型完整当前响应的视觉污染-恢复 | 21/21，见 2.8.1；综合表 CMA-Direct 行为历史 v1.3 |

候选已完成不等于真实编辑评测已完成。2.10 和第 3 节既有并集/阶段比较继续作为冻结记录；其中没有本次新增的 VisEdit-model_pred。2.11、2.12 的 VisEdit 两版已同步，其余历史 LGA Raw、CMA-alt 行保留并标明版本；不能把混合登记表直接视作完整八版本性能比较。
"""
text = replace_section(text, "### 2.9 正式候选方法说明", "### 2.10", section29)
text = text.replace("### 2.10 当前可立即开跑的真实扫层并集__第一版含有多余层", "### 2.10 第一版真实扫层并集（历史冻结，含多余层）")
text = replace_once(text, "该表用于记录已经开跑/已完成的历史扫层范围；严格 `VisEdit-Contrib-Pre-KeyToken` 版本重算后需另行更新。", "该表只追溯当时的 alt/FirstToken 扫层范围；未纳入后续 MMKE KeyToken 更正及本次 VisEdit-model_pred，不作为当前待补层清单。")

def update_comprehensive(section, title, intro):
    lines = section.splitlines()
    table_start = next(i for i,l in enumerate(lines) if l.startswith("| Dataset | Model | Method |"))
    body = []
    count = 0
    for line in lines[table_start:]:
        if line.startswith("| "):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 7 and cells[2] == "VisEdit-Contrib-Pre-KeyToken":
                body.extend(full_row(by_key[(cells[0], cells[1], mode)]) for mode in ["alt", "model_pred"])
                count += 1
                continue
        body.append(line)
    assert count == 21
    return title + "\n\n" + intro + "\n\n" + "\n".join(body).rstrip() + "\n\n"

for start,end,title,intro in [
    ("### 2.11", "### 2.12", "### 2.11 候选方法综合全面表（VisEdit 分 alt / model_pred）",
     "VisEdit 两个版本分别列行，候选与 2.2 一致；Ours 展开四个历史视觉梯度消融，Perturb-KL-Pre 单列消融。本表 LGA-Param-Direct-AltModelPred 为 Raw，CMA-Direct 为历史 v1.3/alt；当前 LGA Tukey 与 CMA-ModelPred 分别见 2.4.1、2.8.1。待计算行不计作已完成方法。"),
    ("### 2.12", "### 2.13", "### 2.12 主候选方法登记表（VisEdit 双版本；其余历史基线行保留）",
     "本表登记 7 个方法族、8 个方法版本，其中 VisEdit 的 alt 与 model_pred 分别列行；Ours 只列当前登记主公式。VisEdit-alt 的 MMKE 候选已同步 2.2，修正旧表六组 FirstToken 残留。LGA Raw 与 CMA-alt 行仍保留作追溯，正式补正版分别见 2.4.1、2.8.1；本表不能直接作为已完成的八版本论文性能比较表。"),
]:
    section = start + text.split(start,1)[1].split(end,1)[0]
    text = replace_section(text, start, end, update_comprehensive(section,title,intro))
old_status = "| VisEdit-Contrib-Pre-KeyToken | 2.2 | 0/21 strict KeyToken done；21/21 historical FirstToken recorded | historical FirstToken | 严格 KeyToken 待重算；当前 FirstToken 结果只作历史对照 |"
new_status = f"| {ALT} | 2.2 | 21/21；EVQA FirstToken 7、MMKE KeyToken 14 | 候选已完成 | 目标粒度按数据集注明；历史 FirstToken 留作诊断 |\n| {PRED} | 2.2.3 | EVQA 7/21；MMKE 14/21 待计算 | 已有七组候选，十四组缺归因分数 | MMKE 需真正 model_pred 归因，不能复用 pred 字段归因冒充 |"
text = replace_once(text, old_status, new_status)
text = replace_once(text, "## 3. 数据集分表\n", "## 3. 数据集分表\n\n> **2026-09-27 适用范围补注：** 本节现存七方法并集、完成数及 Best/Mean/Hit 指标保留原冻结值，其中 VisEdit 仅为 alt 版本（原名 Pre-KeyToken 或历史 Pre-FirstToken）。下文“当前/新版”是当时相对 CMA 旧版的表述，不包括本次新增 VisEdit-model_pred，也不自动包括 9 月 26 日 LGA Tukey 补正。新增版本的完整并集与性能统计需基于对应候选和实际评测另行生成。\n")
text = replace_once(text, "1. 对每个 `dataset × model`，先取所有定位方法的 Top-3 并集做低预算真实扫层。", "1. 对每个 `dataset × model`，先冻结方法及目标版本，再取 Top-3 并集。VisEdit-alt 与 VisEdit-model_pred 分别纳入；MMKE model_pred 尚缺候选，必须标记并集不完整。既有第 3 节并集不能直接改名为八版本并集。")
text = replace_once(text, "4. 方法比较时按自己的 Top-K 集合回填真实扫层结果，报告 `Best@3 / Best@5 / Regret@3 / Regret@5 / Hit@3 / Hit@5`。", "4. 方法比较时按各自 Top-K 集合回填真实编辑结果；VisEdit-alt 与 VisEdit-model_pred 分别报告 `Best@3 / Best@5 / Mean@K / Regret@K / Hit@K`，只在共同候选评测完整的组合上配对，附覆盖数，不把待计算当作零分。")

# Preserve all real-edit results and the already audited LGA correction byte-for-byte as text.
def block(s, start, end):
    return s.split(start, 1)[1].split(end, 1)[0]
assert block(text,"## 4.","## 5.") == block(original,"## 4.","## 5.")
assert block(text,"### 2.4", "### 2.5") == block(original,"### 2.4", "### 2.5")
for sec,end in [("### 2.11","### 2.12"),("### 2.12","### 2.13")]:
    def other_rows(s):
        return [l for l in block(s,sec,end).splitlines() if l.startswith("| ") and "VisEdit-Contrib-Pre-" not in l]
    assert other_rows(text) == other_rows(original)

LEDGER.write_text(text, encoding="utf-8")

# Keep the companion method handbook consistent with the renamed targets.
hbackup = OUT / "backups" / HANDBOOK.name
if not hbackup.exists():
    hbackup.write_bytes(HANDBOOK.read_bytes())
oldh = hbackup.read_text(encoding="utf-8-sig")
assert HANDBOOK.read_text(encoding="utf-8-sig") == oldh
h = oldh.replace("VisEdit-Contrib-Pre-KeyToken", ALT)
notice = f"\n> **VisEdit 双目标登记更新（2026-09-27）：** 同一方法族拆为 `{ALT}` 与 `{PRED}` 两个版本；target mode 与 token rule 分开记录。alt 候选 21/21（EVQA FirstToken 7 组、MMKE KeyToken 14 组）；model_pred 候选 7/21（EVQA），MMKE 14 组待计算。既有七方法性能分析均为冻结的单 VisEdit-alt 版本，不能自动外推至新增版本。候选与证据以 {link('结果手册 2.2', LEDGER)} 为准。\n"
h = h.replace("\n", "\n" + notice, 1)
h = replace_once(h, f"| VisEdit | `{ALT}` | key token 高贡献区之前 Top-K |", f"| VisEdit-alt | `{ALT}` | 新目标 token 高贡献区之前 Top-K；token 规则单列 |\n| VisEdit-model_pred | `{PRED}` | 基础模型当前下一 token 预测的高贡献区之前 Top-K |")
new211 = f"""### 2.1.1 alt / model_pred 目标版本与已有结果

两版均属于 VisEdit-inspired Contrib-Pre，共用贡献计算、3 层平滑、`mean + 0.5 * std` 阈值和 Pre 规则，按目标来源命名：

| 方法名 | 归因目标 | 已有候选 |
|---|---|---|
| `{ALT}` | 新目标侧 token；EVQA 为 alt 首 token，MMKE-entity 为 alt 实体锚点，MMKE-visual 为 m_rel_ans/rel_ans 视觉语义 token | 21/21 |
| `{PRED}` | 未编辑模型在原问题和图像上的下一 token argmax | EVQA 7/21；MMKE 14/21 待计算 |

`model_pred` 在本方法中是单个当前预测 token，不是完整旧答案序列，也不是数据集 `pred` 字段。不能把现有 MMKE `key_mode=pred` 归因换名使用。历史配置中的通用 `token_rule` 文本可能未随模式更新，须同时核对实际代码分支。

旧名称 `VisEdit-Contrib-Pre-KeyToken` 归入 alt 版本，并额外登记 token_rule；历史 `VisEdit-Contrib-Pre-FirstToken` 仍作为 alt 的历史目标粒度保留。MMKE 14 组 dataset-specific KeyToken 已完成，2026-07-04 结果替换当前 alt 主表的旧 FirstToken 候选；六组发生改变。实体锚点或视觉语义词不保证都是新旧答案之间唯一变化的事实词。

历史 alt 21 组已用相同 Pre 函数全部复算一致，EVQA 七组 model_pred 从原始逐层贡献分数派生；本次未重新运行模型。两版候选、来源和缺失状态见结果手册 2.2。比较时分别报告方法，采用候选真实编辑评测完整的共同组合；不要把两版候选合并后只报告较好的成绩。

结果记录必须同时包含 `method`、`key_mode`、`token_rule`、样本数及来源。缺归因分数写 pending；缺合法 Pre 层写 insufficient；二者不能混淆。完整答案序列归因可另作消融，不替代上述单 token 版本。
"""
h = replace_section(h, "### 2.1.1", "## 2.2 模块输出", new211)
h = h.replace('"key_mode": "key_token",', '"key_mode": "alt",\n  "token_rule": "dataset_specific_key_token",')
h = replace_once(h, "## 2.7 完整执行流程", f"上述为 MMKE alt/KeyToken 输出示例。EVQA alt 应记录 `token_rule=alt_first_token`；当前响应版本使用 `method={PRED}`、`key_mode=model_pred`、`token_rule=base_model_next_token_argmax`。候选值必须从各自分数实际计算，不能复用示例。\n\n## 2.7 完整执行流程")
h = replace_once(h, f"严格 `{ALT}` 主实验按以下流程执行：", "VisEdit 两个目标版本分别执行以下流程；MMKE-alt 的 KeyToken 协议与 EVQA-alt 的历史 FirstToken 协议须分别记录：")
h = replace_once(h, "2. 抽取 key token：按数据集规则从 `alt` 中抽取代表编辑知识的 key token，写出 `key_token_manifest.csv`。该文件必须包含 `key_token_text`、`key_token_id`、`key_token_position`、`target_answer_token_ids`、`extraction_rule`、`generic_key_token`、`confidence`、`failure_reason`。", "2. 确定归因目标：alt 按其数据集 token 规则选取目标；model_pred 在基础模型原输入上取下一 token argmax。写入 manifest 的 `key_mode`、`token_rule`、`token_text`、`token_id` 与样本 ID；alt/KeyToken 另存抽取规则、generic 标记及失败原因。")
h = replace_once(h, "3. 过滤无效样本：图像缺失、tokenizer 失败、无法构造 prompt、无法抽取可靠 key token 的样本不进入主聚合；数量写入 `summary.json`。", "3. 过滤该目标版本的无效样本：图像缺失、无法构造 prompt、tokenizer 或目标选择失败的样本不进入主聚合；alt 的 key-token 抽取失败另记原因。有效/总样本数写入 summary，不能把 pred 替代 model_pred。")
h = replace_once(h, f"9. 回填候选表：严格 KeyToken 结果写入 `6location_7model_3datas_top_3_5_layers_outcome.md` 的 `{ALT}` 表；历史 FirstToken 结果保留为 historical / diagnostic。", f"9. 回填候选表：按 `{ALT}` / `{PRED}` 分别写入结果手册 2.2、2.11、2.12，保留 token_rule 与覆盖状态。历史 MMKE-alt FirstToken 另留诊断；EVQA-alt 当前仍用原 FirstToken 结果。")
h = replace_once(h, f"Middle-Prior-Direct\n{ALT}\nSaLEM-Alt-Direct", f"Middle-Prior-Direct\n{ALT}\n{PRED}\nSaLEM-Alt-Direct")
h = replace_once(h, f"| {ALT} | key token prediction 模块贡献 | positive contribution | Pre |", f"| {ALT} | 新目标侧单 token 模块贡献（规则分数据集登记） | positive contribution | Pre |\n| {PRED} | 模型当前下一 token argmax 的模块贡献 | positive contribution | Pre |")
h = replace_once(h, "| VisEdit target position | key token prediction |", "| VisEdit target | alt：各数据集既定目标 token；model_pred：当前下一 token argmax |")
h = replace_once(h, f"- [ ] VisEdit 的历史 `FirstToken` 结果已标记为 historical / diagnostic；严格主表只使用 `{ALT}` 重算结果，且不得在 key token 抽取失败时静默 fallback 到 first token。", "- [ ] VisEdit-alt 与 VisEdit-model_pred 分别登记；EVQA-alt FirstToken 与 MMKE-alt KeyToken 明确区分；model_pred 不能由 pred 字段归因代替；缺失十四组标记待计算。")
# Limit target-specific theoretical prose to the alt branch, leaving equations intact.
h = h.replace("对每个样本从 `alt` / `target_new` 中确定一个 key token 位置", "以下抽取说明适用于 alt 分支；model_pred 分支改取基础模型当前下一 token argmax，之后贡献聚合与 Pre 选层相同。对每个 alt 样本确定一个 key token 位置")
HANDBOOK.write_text(h, encoding="utf-8")

verification = {"candidate_rows": len(rows), "alt_done": 21, "model_pred_done": 7, "model_pred_pending": 14,
                "main_tables_synced": [], "historical_alt_reproduced": 21,
                "real_edit_section_unchanged": True, "lga_correction_unchanged": True,
                "other_method_candidate_rows_unchanged": True}
for sec, end in [("### 2.2 ","#### 2.2.1"),("### 2.11","### 2.12"),("### 2.12","### 2.13")]:
    found = [l for l in block(text,sec,end).splitlines() if l.startswith("| ") and (f"| {ALT} |" in l or f"| {PRED} |" in l)]
    assert len(found) == 42, (sec,len(found))
    for r in rows:
        matches = [l for l in found if l.startswith(f"| {r['dataset']} | {r['model']} | {r['method']} |")]
        assert len(matches) == 1
        assert f"| {r['top3'] or '待计算'} | {r['top5'] or '待计算'} |" in matches[0]
    verification["main_tables_synced"].append(sec)
assert "0/21 strict KeyToken" not in text
assert "strict KeyToken pending" not in text.split("## 3.")[0]
verification["updated_sha256"] = {str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in [LEDGER,HANDBOOK]}
(OUT / "verification.json").write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(verification,ensure_ascii=False,indent=2))
