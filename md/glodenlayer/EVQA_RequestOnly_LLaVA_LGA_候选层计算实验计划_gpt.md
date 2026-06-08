# EVQA Request-Only LLaVA LGA 候选层计算实验计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 只使用 E-VQA 训练集中的 request 样本，计算 LLaVA-v1.5-7B 在视觉表征与文本表征上的 Virtual Delta-h LGA 指标，并给出视觉/文本候选编辑层。

**Architecture:** 本实验不训练 adapter，不保存训练 checkpoint，只在 LLaVA 基座模型上对 request-only 样本做逐层梯度/Delta-h 统计。当前批次只执行 Stage 1：用 1000 条 request 快速计算 LGA 候选层；Stage 2 全量 E-VQA train request-only 仅在用户明确要求时再启动。

**Tech Stack:** Python, PyTorch, VisEdit/EasyEdit MMEdit 数据, LLaVA-v1.5-7B, `scripts/bridge_vlm_virtual_delta_h_lga_scan.py`, CSV/JSON/Markdown 汇总。

---

## 1. 实验边界

本实验只计算 LLaVA 在 E-VQA request-only 数据上的视觉/文本 LGA 候选层。

严格约束：

- 只计算梯度相关 LGA 指标，不做 adapter 训练。
- 只使用 request 字段参与梯度计算。
- 不使用 `generality`、`locality`、`portability`、`open_questions`、`text_rephrase`、`image_rephrase` 等非 request 样本。
- 不修改原始 E-VQA 数据集文件。
- Hook 位置沿用已有 LLaVA adapter sweep / Virtual Delta-h LGA 的层定义，保证候选层与真实编辑层定义一致。
- 当前批次只做 Stage 1 快速估计；Stage 2 full 结果等用户后续要求再补。

---

## 2. 推荐指标依据

参考文件：

```text
md/glodenlayer/CrossModel_VisualText_GoldenLayer_LGA_汇总分析_gpt.md
```

LLaVA 相关既有校准结论：

| 模型 | 模态 | 推荐主指标 | 证据强度 | 既有 LGA Top3 | 解释 |
|---|---|---|---|---|---|
| LLaVA | visual | `M_newn_x_1mcos` | strong | 6, 7, 5 | Bridge30 上强相关，Top3 命中真实 visual generality 最优层 7 |
| LLaVA | text | `M_new_norm` | trend-only | 0, 1, 2 | 有强单调趋势，但 Top3 偏最浅层，Bridge30 真实 text generality 最优层为 7 |

因此本实验输出分成两类：

- 视觉候选层：以 `M_newn_x_1mcos` Top-k 为主，同时报告 `M_new_norm`、`M_abscos_x_newn`、`M_conflict`。
- 文本候选层：以 `M_new_norm` Top-k 为主，但标记为 trend-only/弱证据，同时报告 `M_dot`、`M_conflict`、`M_cos`、`M_abscos_x_newn`。如果 E-VQA 上文本 Top-k 仍集中在 0/1/2，需要在结论中注明 LLaVA text LGA 存在浅层偏置。

---

## 3. 数据与模型路径

服务器工作目录：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
```

原始 E-VQA 训练集：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_train.json
```

图像根目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

已生成的 request-only bridge-format 数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_request_only_bridge_format.json
```

旧答案映射文件：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_old_answers.jsonl
```

数据转换报告：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_convert_report.json
```

LLaVA 模型目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
```

LLaVA 配置：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/configs/vead/llava-v1.5-7b.yaml
```

LGA 扫描脚本：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/bridge_vlm_virtual_delta_h_lga_scan.py
```

本次新输出目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
```

两阶段输出目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/pilot_1000
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/full
```

阶段划分：

| 阶段 | 数据量 | 目的 | 输出目录 | 预期样本行数 |
|---|---:|---|---|---:|
| Stage 1 | 1000 条 request | 快速估计 LLaVA 视觉/文本 LGA 候选层，检查指标是否稳定 | `pilot_1000` | `1000 * 32 = 32000` |
| Stage 2 | 6345 条 request | 在全量 E-VQA train request-only 上确认最终候选层；仅在用户明确要求时启动 | `full` | `6345 * 32 = 203040` |

执行原则：

- 当前批次只执行 Stage 1，并生成 `analysis/pilot_1000/*`。
- Stage 1 的 Top-k 只作为快速候选，不作为最终结论。
- Stage 2 full 只有在用户明确要求“跑全量 E-VQA”时才启动。
- 后续若 Stage 2 全量结果生成 `analysis/full/*`，最终候选层以 full 为准。
- 若 Stage 1 与 Stage 2 的 Top3 差异很大，需要在结论中注明数据量敏感性。

---

## 4. 指标定义

脚本原始输出字段包含 `S_v_*` 与 `S_t_*` 两组统计量：

- `v` 表示视觉表征分支。
- `t` 表示文本表征分支。

本实验统一派生以下指标：

| 指标名 | 视觉公式 | 文本公式 | 作用 |
|---|---|---|---|
| `M_dot` | `S_v_dot` | `S_t_dot` | Delta-h 与梯度的 raw dot |
| `M_conflict` | `S_v_conflict` | `S_t_conflict` | 梯度冲突程度 |
| `M_dot_per_dim` | `S_v_dot_per_dim` | `S_t_dot_per_dim` | 维度归一化 dot |
| `M_cos` | `S_v_cos` | `S_t_cos` | 方向一致性 |
| `M_new_norm` | `S_v_new_norm` | `S_t_new_norm` | 新表示改变量强度 |
| `M_old_norm` | `S_v_old_norm` | `S_t_old_norm` | 原表示强度 |
| `M_joint_norm` | `S_v_joint_norm` | `S_t_joint_norm` | 旧/新联合强度 |
| `M_pos_ratio` | `S_v_positive_ratio` | `S_t_positive_ratio` | 正向梯度比例 |
| `M_newn_x_1mcos` | `S_v_new_norm * (1 - S_v_cos)` | `S_t_new_norm * (1 - S_t_cos)` | LLaVA visual 主推荐指标 |
| `M_newn_x_pos` | `S_v_new_norm * S_v_positive_ratio` | `S_t_new_norm * S_t_positive_ratio` | 强度乘正向比例 |
| `M_abscos_x_newn` | `abs(S_v_cos) * S_v_new_norm` | `abs(S_t_cos) * S_t_new_norm` | 方向强度复合指标 |
| `M_conflict_x_newn` | `S_v_conflict * S_v_new_norm` | `S_t_conflict * S_t_new_norm` | 冲突强度复合指标 |

候选层选择规则：

- 视觉主候选：按视觉 `M_newn_x_1mcos` 从大到小排序，取 Top1/Top3/Top5。
- 视觉辅助判断：报告视觉 `M_new_norm`、`M_abscos_x_newn`、`M_conflict` 的 Top5。
- 文本主候选：按文本 `M_new_norm` 从大到小排序，取 Top1/Top3/Top5。
- 文本辅助判断：报告文本 `M_dot`、`M_conflict`、`M_cos`、`M_abscos_x_newn` 的 Top5。
- `S_v_zero_grad=1` 的层不参与视觉候选排序。
- `S_t_zero_grad=1` 的层不参与文本候选排序。

---

## 5. 执行任务

### Task 1: 检查 request-only 数据

**Files:**

- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_request_only_bridge_format.json`
- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_old_answers.jsonl`
- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_convert_report.json`

- [ ] **Step 1: 登录服务器并进入工程目录**

```bash
ssh bridge-server
ssh g07
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
```

- [ ] **Step 2: 核对 request-only 数据没有混入其他指标**

```bash
/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python - <<'PY'
import json
from pathlib import Path

data_path = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_request_only_bridge_format.json")
old_path = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_old_answers.jsonl")
report_path = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_convert_report.json")

data = json.loads(data_path.read_text(encoding="utf-8"))
non_empty = []
for item in data:
    for group in ("generality", "locality", "portability"):
        value = item.get(group, {})
        if isinstance(value, dict):
            for key, arr in value.items():
                if arr:
                    non_empty.append((item.get("case_id"), group, key, len(arr)))
        elif value:
            non_empty.append((item.get("case_id"), group, "value", 1))

old_count = sum(1 for _ in old_path.open("r", encoding="utf-8"))
report = json.loads(report_path.read_text(encoding="utf-8"))
print("request_only_items =", len(data))
print("old_answer_items =", old_count)
print("non_request_non_empty =", len(non_empty))
print("convert_report =", report)

assert len(data) == 6345
assert old_count == 6345
assert len(non_empty) == 0
PY
```

Expected:

```text
request_only_items = 6345
old_answer_items = 6345
non_request_non_empty = 0
```

### Task 2: Stage 1 启动 1000 条 request pilot LGA 扫描

**Files:**

- Read: `scripts/bridge_vlm_virtual_delta_h_lga_scan.py`
- Read: `configs/vead/llava-v1.5-7b.yaml`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/pilot_1000/*`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/run/llava_pilot1000_lga.log`

- [ ] **Step 1: 设置路径变量**

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
SRC_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
DATA=$SRC_ROOT/data/evqa_train_request_only_bridge_format.json
OLD=$SRC_ROOT/data/evqa_train_old_answers.jsonl
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images

mkdir -p "$OUT_ROOT/pilot_1000" "$OUT_ROOT/full" "$OUT_ROOT/run"
```

- [ ] **Step 2: 启动 pilot 后台扫描**

```bash
nohup "$PY" scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path "$DATA" \
  --bridge-root "$IMG_ROOT" \
  --old-answers-path "$OLD" \
  --layers 0-31 \
  --max-samples 1000 \
  --device cuda:0 \
  --torch-dtype float16 \
  --output-dir "$OUT_ROOT/pilot_1000" \
  > "$OUT_ROOT/run/llava_pilot1000_lga.log" 2>&1 &
echo $! > "$OUT_ROOT/run/pilot_pid"
cat "$OUT_ROOT/run/pilot_pid"
```

- [ ] **Step 3: 检查 pilot 进程与日志**

```bash
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
PID=$(cat "$OUT_ROOT/run/pilot_pid")
ps -fp "$PID"
tail -n 80 "$OUT_ROOT/run/llava_pilot1000_lga.log"
```

Expected:

```text
进程存在，日志持续输出 layer / sample 进度
```

### Task 3: 监控 Stage 1 pilot 运行进度

**Files:**

- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/pilot_1000/sample_virtual_delta_h_scores.jsonl`
- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/run/llava_pilot1000_lga.log`

- [ ] **Step 1: 查看已生成样本行数**

```bash
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
wc -l "$OUT_ROOT/pilot_1000/sample_virtual_delta_h_scores.jsonl"
tail -n 40 "$OUT_ROOT/run/llava_pilot1000_lga.log"
```

Expected pilot-run 行数：

```text
32000 sample_virtual_delta_h_scores.jsonl
```

说明：`32000 = 1000 request samples * 32 layers`。

- [ ] **Step 2: 确认 pilot 层级汇总文件生成**

```bash
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
ls -lh "$OUT_ROOT/pilot_1000"
wc -l "$OUT_ROOT/pilot_1000/virtual_delta_h_lga_layer_scores.csv"
```

Expected:

```text
33 virtual_delta_h_lga_layer_scores.csv
```

### Task 3B: 可选 Stage 2 全量 E-VQA request-only LGA 扫描

**Files:**

- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_request_only_bridge_format.json`
- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_old_answers.jsonl`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/full/*`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/run/llava_full_lga.log`

- [ ] **Step 1: 只在用户明确要求时启动 full**

```bash
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
test -f "$OUT_ROOT/pilot_1000/virtual_delta_h_lga_layer_scores.csv"
wc -l "$OUT_ROOT/pilot_1000/sample_virtual_delta_h_scores.jsonl"
```

Expected:

```text
32000 sample_virtual_delta_h_scores.jsonl
```

- [ ] **Step 2: 启动 full 后台扫描**

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
SRC_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
DATA=$SRC_ROOT/data/evqa_train_request_only_bridge_format.json
OLD=$SRC_ROOT/data/evqa_train_old_answers.jsonl
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images

mkdir -p "$OUT_ROOT/full" "$OUT_ROOT/run"
nohup "$PY" scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path "$DATA" \
  --bridge-root "$IMG_ROOT" \
  --old-answers-path "$OLD" \
  --layers 0-31 \
  --device cuda:0 \
  --torch-dtype float16 \
  --output-dir "$OUT_ROOT/full" \
  > "$OUT_ROOT/run/llava_full_lga.log" 2>&1 &
echo $! > "$OUT_ROOT/run/full_pid"
cat "$OUT_ROOT/run/full_pid"
```

- [ ] **Step 3: 监控 full 进度**

```bash
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525
PID=$(cat "$OUT_ROOT/run/full_pid")
ps -fp "$PID"
wc -l "$OUT_ROOT/full/sample_virtual_delta_h_scores.jsonl"
tail -n 40 "$OUT_ROOT/run/llava_full_lga.log"
```

Expected full-run 行数：

```text
203040 sample_virtual_delta_h_scores.jsonl
```

说明：`203040 = 6345 request samples * 32 layers`。

### Task 4: 生成 LLaVA 视觉/文本候选层报告

**Files:**

- Read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/pilot_1000/virtual_delta_h_lga_layer_scores.csv`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_metric_topk.csv`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_candidate_layers.json`
- Create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_candidate_summary.md`
- Optional later read: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/full/virtual_delta_h_lga_layer_scores.csv`
- Optional later create: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/analysis/full/*`

- [ ] **Step 1: 运行候选层汇总脚本**

```bash
PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
LGA_RESULT_SPLIT=pilot_1000 "$PY" - <<'PY'
import csv
import json
import math
import os
from pathlib import Path

root = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525")
result_split = os.environ.get("LGA_RESULT_SPLIT", "pilot_1000")
csv_path = root / result_split / "virtual_delta_h_lga_layer_scores.csv"
analysis_dir = root / "analysis" / result_split
analysis_dir.mkdir(parents=True, exist_ok=True)

def f(row, key):
    value = row.get(key, "")
    if value in ("", "NA", "nan", "None"):
        return float("nan")
    return float(value)

def z(row, key):
    value = str(row.get(key, "0")).strip().lower()
    if value in ("true", "1", "1.0", "yes", "y"):
        return 1
    if value in ("false", "0", "0.0", "no", "n", ""):
        return 0
    return int(float(value))

def safe_mul(a, b):
    if math.isnan(a) or math.isnan(b):
        return float("nan")
    return a * b

rows = []
with csv_path.open("r", encoding="utf-8") as fp:
    for row in csv.DictReader(fp):
        layer = int(float(row["layer"]))
        item = {"layer": layer, "raw": row}
        for branch, prefix in (("visual", "S_v"), ("text", "S_t")):
            cos = f(row, f"{prefix}_cos")
            new_norm = f(row, f"{prefix}_new_norm")
            pos_ratio = f(row, f"{prefix}_positive_ratio")
            conflict = f(row, f"{prefix}_conflict")
            item[f"{branch}_zero_grad"] = z(row, f"{prefix}_zero_grad")
            item[f"{branch}_metrics"] = {
                "M_dot": f(row, f"{prefix}_dot"),
                "M_conflict": conflict,
                "M_dot_per_dim": f(row, f"{prefix}_dot_per_dim"),
                "M_cos": cos,
                "M_new_norm": new_norm,
                "M_old_norm": f(row, f"{prefix}_old_norm"),
                "M_joint_norm": f(row, f"{prefix}_joint_norm"),
                "M_pos_ratio": pos_ratio,
                "M_newn_x_1mcos": safe_mul(new_norm, 1 - cos),
                "M_newn_x_pos": safe_mul(new_norm, pos_ratio),
                "M_abscos_x_newn": safe_mul(abs(cos), new_norm),
                "M_conflict_x_newn": safe_mul(conflict, new_norm),
            }
        rows.append(item)

if len(rows) != 32:
    raise RuntimeError(f"expected 32 layer rows, got {len(rows)}")

def topk(branch, metric, k=5):
    valid = []
    for item in rows:
        if item[f"{branch}_zero_grad"] == 1:
            continue
        score = item[f"{branch}_metrics"][metric]
        if math.isnan(score):
            continue
        valid.append((item["layer"], score))
    valid.sort(key=lambda x: x[1], reverse=True)
    return valid[:k]

metrics = [
    "M_dot", "M_conflict", "M_dot_per_dim", "M_cos", "M_new_norm", "M_old_norm",
    "M_joint_norm", "M_pos_ratio", "M_newn_x_1mcos", "M_newn_x_pos",
    "M_abscos_x_newn", "M_conflict_x_newn",
]

topk_csv = analysis_dir / "llava_evqa_lga_metric_topk.csv"
with topk_csv.open("w", encoding="utf-8", newline="") as fp:
    writer = csv.writer(fp)
    writer.writerow(["branch", "metric", "rank", "layer", "score"])
    for branch in ("visual", "text"):
        for metric in metrics:
            for rank, (layer, score) in enumerate(topk(branch, metric, 5), start=1):
                writer.writerow([branch, metric, rank, layer, f"{score:.10g}"])

visual_primary = topk("visual", "M_newn_x_1mcos", 5)
text_primary = topk("text", "M_new_norm", 5)
candidate = {
    "dataset": "E-VQA train request-only",
    "model": "llava-v1.5-7b",
    "result_split": result_split,
    "n_request": int(float(rows[0]["raw"].get("n_request", 0))) if rows else None,
    "layers": "0-31",
    "visual": {
        "primary_metric": "M_newn_x_1mcos",
        "confidence": "strong",
        "top1": visual_primary[0][0] if visual_primary else None,
        "top3": [x[0] for x in visual_primary[:3]],
        "top5": [x[0] for x in visual_primary[:5]],
        "scores_top5": [{"layer": x[0], "score": x[1]} for x in visual_primary[:5]],
        "auxiliary_top5": {
            metric: [x[0] for x in topk("visual", metric, 5)]
            for metric in ("M_new_norm", "M_abscos_x_newn", "M_conflict")
        },
    },
    "text": {
        "primary_metric": "M_new_norm",
        "confidence": "trend-only",
        "top1": text_primary[0][0] if text_primary else None,
        "top3": [x[0] for x in text_primary[:3]],
        "top5": [x[0] for x in text_primary[:5]],
        "scores_top5": [{"layer": x[0], "score": x[1]} for x in text_primary[:5]],
        "auxiliary_top5": {
            metric: [x[0] for x in topk("text", metric, 5)]
            for metric in ("M_dot", "M_conflict", "M_cos", "M_abscos_x_newn")
        },
    },
}

(analysis_dir / "llava_evqa_lga_candidate_layers.json").write_text(
    json.dumps(candidate, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

def fmt_layers(items):
    return ", ".join(f"{layer} ({score:.4g})" for layer, score in items)

summary = []
summary.append("# LLaVA E-VQA Request-Only LGA Candidate Summary")
summary.append("")
summary.append(f"Result split: `{result_split}`")
summary.append("")
summary.append("| Branch | Primary Metric | Top1 | Top3 | Top5 | Confidence |")
summary.append("|---|---|---:|---|---|---|")
summary.append(f"| visual | M_newn_x_1mcos | {candidate['visual']['top1']} | {', '.join(map(str, candidate['visual']['top3']))} | {', '.join(map(str, candidate['visual']['top5']))} | strong |")
summary.append(f"| text | M_new_norm | {candidate['text']['top1']} | {', '.join(map(str, candidate['text']['top3']))} | {', '.join(map(str, candidate['text']['top5']))} | trend-only |")
summary.append("")
summary.append("## Visual Top5 by Primary Metric")
summary.append("")
summary.append(fmt_layers(visual_primary))
summary.append("")
summary.append("## Visual Auxiliary Top5")
summary.append("")
for metric in ("M_new_norm", "M_abscos_x_newn", "M_conflict"):
    summary.append(f"- {metric}: {', '.join(map(str, candidate['visual']['auxiliary_top5'][metric]))}")
summary.append("")
summary.append("## Text Top5 by Primary Metric")
summary.append("")
summary.append(fmt_layers(text_primary))
summary.append("")
summary.append("## Text Auxiliary Top5")
summary.append("")
for metric in ("M_dot", "M_conflict", "M_cos", "M_abscos_x_newn"):
    summary.append(f"- {metric}: {', '.join(map(str, candidate['text']['auxiliary_top5'][metric]))}")
summary.append("")
summary.append("## Interpretation Rule")
summary.append("")
summary.append("Visual candidates use M_newn_x_1mcos directly. Text candidates use M_new_norm only as trend-only evidence because LLaVA text LGA is known to have a shallow-layer bias on Bridge30.")

(analysis_dir / "llava_evqa_lga_candidate_summary.md").write_text(
    "\n".join(summary) + "\n",
    encoding="utf-8",
)

print("wrote", topk_csv)
print("wrote", analysis_dir / "llava_evqa_lga_candidate_layers.json")
print("wrote", analysis_dir / "llava_evqa_lga_candidate_summary.md")
PY
```

后续用户要求 Stage 2 full 后，用同一段 here-doc 脚本再跑一次，只把命令第一行的 `LGA_RESULT_SPLIT=pilot_1000` 改成 `LGA_RESULT_SPLIT=full`；其余 Python 代码逐字保持一致。

Expected:

```text
wrote .../analysis/pilot_1000/llava_evqa_lga_metric_topk.csv
wrote .../analysis/pilot_1000/llava_evqa_lga_candidate_layers.json
wrote .../analysis/pilot_1000/llava_evqa_lga_candidate_summary.md
```

### Task 5: 拉回本地并追加到研究汇总文件

**Files:**

- Copy from remote: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525/analysis/*`
- Create local: `downloads/Temp/evqa_request_only_llava_lga_candidate_20260525/*`
- Later modify after user确认: `md/glodenlayer/CrossModel_VisualText_GoldenLayer_LGA_汇总分析_gpt.md`

- [ ] **Step 1: 拉回本地**

```powershell
$LOCAL="downloads/Temp/evqa_request_only_llava_lga_candidate_20260525"
New-Item -ItemType Directory -Force -Path $LOCAL | Out-Null
ssh bridge-server "ssh g07 'tar -C /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_request_only_llava_lga_candidate_20260525 -czf - analysis'" | tar -xzf - -C $LOCAL
```

Expected:

```text
downloads/Temp/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_candidate_summary.md
downloads/Temp/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_candidate_layers.json
downloads/Temp/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_metric_topk.csv
```

- [ ] **Step 2: 用户确认后再追加到总汇总文件**

追加目标：

```text
md/glodenlayer/CrossModel_VisualText_GoldenLayer_LGA_汇总分析_gpt.md
```

追加方式：

1. 打开 `downloads/Temp/evqa_request_only_llava_lga_candidate_20260525/analysis/pilot_1000/llava_evqa_lga_candidate_summary.md`，记录 1000 条 request 的快速候选层。
2. 将 pilot summary 表格追加到 `CrossModel_VisualText_GoldenLayer_LGA_汇总分析_gpt.md` 的 E-VQA/LGA 小节。
3. 同时注明：当前仅完成 1000 条 request 的 pilot 指标计算；full 全量 E-VQA 尚未运行；模型为 LLaVA-v1.5-7B；方法为 Virtual Delta-h LGA，全 32 层，视觉/文本分支分别统计。

---

## 6. 完成标准

实验完成时必须满足：

- request-only 检查通过：`request_only_items=6345`，`old_answer_items=6345`，`non_request_non_empty=0`。
- Stage 1 pilot 扫描完成：`pilot_1000/sample_virtual_delta_h_scores.jsonl` 有 `32000` 行。
- Stage 1 层级汇总完成：`pilot_1000/virtual_delta_h_lga_layer_scores.csv` 有 `33` 行。
- Stage 1 已生成 `analysis/pilot_1000/llava_evqa_lga_metric_topk.csv`、`analysis/pilot_1000/llava_evqa_lga_candidate_layers.json`、`analysis/pilot_1000/llava_evqa_lga_candidate_summary.md`。
- 视觉候选层报告包含 `M_newn_x_1mcos` Top1/Top3/Top5。
- 文本候选层报告包含 `M_new_norm` Top1/Top3/Top5，并包含 `M_dot`、`M_conflict`、`M_cos`、`M_abscos_x_newn` 辅助 Top5。
- Stage 2 full 的完成标准保留为后续可选项：`full/sample_virtual_delta_h_scores.jsonl` 有 `203040` 行，`full/virtual_delta_h_lga_layer_scores.csv` 有 `33` 行，并生成 `analysis/full/*`。

---

## 7. 预计耗时与风险

预计耗时：

- Stage 1 pilot：1000 条样本 × 32 层，约 1-2 小时。
- Stage 2 full：6345 条样本 × 32 层，约 6-10 小时；当前批次不启动。
- 候选层汇总脚本：1 分钟以内。
- 拉回本地与写入汇总：5 分钟以内。

风险处理：

- 这不是 adapter 训练，不会产生大量 checkpoint；磁盘主要消耗来自 `sample_virtual_delta_h_scores.jsonl`。
- 如果 SSH 中断但进程仍在服务器后台运行，pilot 用 `cat run/pilot_pid && ps -fp $(cat run/pilot_pid)` 查看，full 用 `cat run/full_pid && ps -fp $(cat run/full_pid)` 查看。
- 如果进程中断，保留已生成 jsonl；最终候选层必须等待 `virtual_delta_h_lga_layer_scores.csv` 完整生成后再判定。
- 如果显存不足，先确认服务器没有其他 Python 进程占用 GPU，再重启 LLaVA LGA 扫描。
- 如果 LLaVA text 的 Top-k 与 Bridge30 中一样偏向 0/1/2，需要在结论中明确标记为浅层偏置，不把它当成强 golden-layer 证据。

---

## 8. 结论写法

最终结论从 `llava_evqa_lga_candidate_layers.json` 读取实际层号，不手写层号。

视觉结论包含：

- 主指标：`M_newn_x_1mcos`
- 候选层：JSON 中 `visual.top1`、`visual.top3`、`visual.top5`
- 置信度：`strong`
- 解释：该指标在 Bridge30 校准中能够命中 LLaVA visual generality 最优层，因此可作为 E-VQA 上 LLaVA 视觉表征编辑的候选层依据。

文本结论包含：

- 主指标：`M_new_norm`
- 候选层：JSON 中 `text.top1`、`text.top3`、`text.top5`
- 置信度：`trend-only`
- 辅助证据：JSON 中 `text.auxiliary_top5.M_dot`、`text.auxiliary_top5.M_conflict`、`text.auxiliary_top5.M_cos`、`text.auxiliary_top5.M_abscos_x_newn`
- 解释：Bridge30 校准中 LLaVA text 的 LGA 存在浅层偏置，因此 E-VQA 文本候选层只能作为趋势参考，需要后续真实 text adapter sweep 验证。
