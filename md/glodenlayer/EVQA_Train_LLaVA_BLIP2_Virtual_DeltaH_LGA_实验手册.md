# E-VQA Train LLaVA / BLIP2 Virtual Delta-h LGA 实验手册

## 0. 实验目标

本实验用于在 EasyEdit MMEdit 的 E-VQA 训练集上计算 LLaVA 与 BLIP2 的 Virtual Delta-h LGA 指标，得到每个模型在 visual / text 两个模态分支上的候选编辑层。

这里的 `lag` 按本文档统一写作 `LGA`。

核心问题：

```text
在 E-VQA train request 上，不训练 adapter，只用零扰动 Delta-h 梯度信号，
分别估计 LLaVA / BLIP2 的 visual token 与 text prompt token 最敏感层。
```

最终输出：

```text
LLaVA visual LGA top-k
LLaVA text LGA top-k
BLIP2 visual LGA top-k
BLIP2 text LGA top-k
每层完整 LGA 指标表
```

## 1. 数据集位置

服务器上 E-VQA 数据集位置：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_train.json
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
```

图片根目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

已核对的样本规模：

```text
vqa_train.json: 6345 cases
vqa_eval.json:  2093 cases
```

本实验只使用 `vqa_train.json` 作为 LGA proxy set，不使用 eval。

## 2. 字段映射

E-VQA 原始字段示例：

```text
src              原始问题
pred             base / old answer
alt              edited / new target answer
rephrase         同图改写问题
image            原始图片
image_rephrase   同语义改写图片
loc              text locality 问题
loc_ans          text locality 答案
m_loc            multimodal locality 图片
m_loc_q          multimodal locality 问题
m_loc_a          multimodal locality 答案
```

Virtual Delta-h LGA 的 request-only 映射：

| E-VQA 字段 | LGA 使用字段 | 说明 |
| --- | --- | --- |
| `image` | `request.image` | 原始 request 图片 |
| `src` | `request.prompt` | 原始 request 问题 |
| `alt` | `request.target_new` | new target |
| `pred` | `old_answer` | old target / base answer |

本实验不把 `rephrase / image_rephrase / loc / m_loc` 加入 LGA 计算。它们后续用于真实 adapter 评测或 balanced-LGA 消融。

## 3. Hook 位置

必须和后续真实 adapter 挂载位置保持一致：

```text
after layer l
```

也就是在 LLM decoder layer `l` 的 forward output 上挂 hook，取该层输出 hidden state 对 old/new answer loss 的梯度。

LLaVA：

```text
language_model.model.layers.{l}
```

BLIP2：

```text
language_model.model.decoder.layers.{l}
```

对应配置文件：

```text
configs/vead/llava-v1.5-7b.yaml
configs/vead/blip2-opt-2.7b.yaml
```

## 4. 数据预处理

现有 `scripts/bridge_vlm_virtual_delta_h_lga_scan.py` 读取 Bridge 风格 request JSON，因此先把 E-VQA train 转成兼容格式。

不修改原始文件，只生成派生文件：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_request_only_bridge_format.json
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_old_answers.jsonl
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data/evqa_train_convert_report.json
```

生成命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
EVQA_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
mkdir -p "$OUT_ROOT/data"

$PY - <<'PY'
import json
from pathlib import Path

evqa_root = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm")
src_path = evqa_root / "vqa" / "vqa_train.json"
out_dir = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga/data")
out_dir.mkdir(parents=True, exist_ok=True)

items = json.load(open(src_path, "r", encoding="utf-8"))
converted = []
old_rows = []
missing_image = []

for idx, item in enumerate(items):
    rel_image = str(item["image"])
    image_path = evqa_root / "images" / rel_image
    image_id = Path(rel_image).stem
    case_id = f"evqa_train_{idx}"

    if not image_path.exists():
        missing_image.append({"case_id": case_id, "image": rel_image})

    prompt = str(item["src"]).strip()
    old_answer = str(item["pred"]).strip()
    target_new = str(item["alt"]).strip()

    converted.append({
        "case_id": case_id,
        "entity_id": image_id,
        "entity_name": target_new,
        "request": {
            "image": rel_image,
            "prompt": prompt,
            "target_new": target_new,
        },
        "generality": {
            "text_rephrase": [],
            "image_rephrase": [],
        },
        "locality": {
            "text_loc": [],
            "image_loc": [],
        },
        "portability": {
            "1hop": [],
            "2hop": [],
        },
        "source_dataset": "EasyEdit-MMEdit-EVQA",
        "source_index": idx,
    })

    old_rows.append({
        "image_id": image_id,
        "question": prompt,
        "answer": old_answer,
        "case_id": case_id,
        "image": rel_image,
    })

json.dump(converted, open(out_dir / "evqa_train_request_only_bridge_format.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
with open(out_dir / "evqa_train_old_answers.jsonl", "w", encoding="utf-8") as f:
    for row in old_rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

report = {
    "source": str(src_path),
    "n_cases": len(items),
    "n_converted": len(converted),
    "n_old_answers": len(old_rows),
    "n_missing_image": len(missing_image),
    "missing_image_preview": missing_image[:20],
}
json.dump(report, open(out_dir / "evqa_train_convert_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
```

预期：

```text
n_cases = 6345
n_converted = 6345
n_old_answers = 6345
n_missing_image = 0
```

## 5. 计算命令

### 5.1 小规模检查

先跑 100 条样本确认脚本、图片路径、old answer 映射和显存都正常。

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
DATA=$OUT_ROOT/data/evqa_train_request_only_bridge_format.json
OLD=$OUT_ROOT/data/evqa_train_old_answers.jsonl
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images

mkdir -p "$OUT_ROOT/pilot_llava_100" "$OUT_ROOT/pilot_blip2_100"

$PY scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path "$DATA" \
  --bridge-root "$IMG_ROOT" \
  --old-answers-path "$OLD" \
  --layers 0-31 \
  --device cuda:0 \
  --torch-dtype float16 \
  --max-samples 100 \
  --output-dir "$OUT_ROOT/pilot_llava_100"

$PY scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --config-path configs/vead/blip2-opt-2.7b.yaml \
  --data-path "$DATA" \
  --bridge-root "$IMG_ROOT" \
  --old-answers-path "$OLD" \
  --layers 0-31 \
  --device cuda:0 \
  --torch-dtype float16 \
  --max-samples 100 \
  --output-dir "$OUT_ROOT/pilot_blip2_100"
```

检查：

```bash
cat "$OUT_ROOT/pilot_llava_100/old_answer_mapping_report.json"
cat "$OUT_ROOT/pilot_blip2_100/old_answer_mapping_report.json"
head -5 "$OUT_ROOT/pilot_llava_100/virtual_delta_h_lga_layer_scores.csv"
head -5 "$OUT_ROOT/pilot_blip2_100/virtual_delta_h_lga_layer_scores.csv"
```

必须满足：

```text
missing_cases = []
mapped_cases = max_samples
virtual_delta_h_lga_layer_scores.csv 有 32 行
topk_virtual_delta_h_layers.json 已生成
summary.md 已生成
```

### 5.2 正式全量运行

E-VQA train 有 6345 条，计算量明显大于 Bridge30。建议后台运行，并保留日志。

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
DATA=$OUT_ROOT/data/evqa_train_request_only_bridge_format.json
OLD=$OUT_ROOT/data/evqa_train_old_answers.jsonl
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
RUN_ROOT=$OUT_ROOT/run
mkdir -p "$RUN_ROOT" "$OUT_ROOT/llava_full" "$OUT_ROOT/blip2_full"

cat > "$RUN_ROOT/run_evqa_train_llava_blip2_virtual_delta_h_lga.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
DATA=$OUT_ROOT/data/evqa_train_request_only_bridge_format.json
OLD=$OUT_ROOT/data/evqa_train_old_answers.jsonl
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images

echo "[start] $(date '+%F %T') host=$(hostname)"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader || true

echo "[llava] $(date '+%F %T')"
$PY scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path "$DATA" \
  --bridge-root "$IMG_ROOT" \
  --old-answers-path "$OLD" \
  --layers 0-31 \
  --device cuda:0 \
  --torch-dtype float16 \
  --output-dir "$OUT_ROOT/llava_full"

echo "[blip2] $(date '+%F %T')"
$PY scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --config-path configs/vead/blip2-opt-2.7b.yaml \
  --data-path "$DATA" \
  --bridge-root "$IMG_ROOT" \
  --old-answers-path "$OLD" \
  --layers 0-31 \
  --device cuda:0 \
  --torch-dtype float16 \
  --output-dir "$OUT_ROOT/blip2_full"

echo "[done] $(date '+%F %T')"
SH

chmod +x "$RUN_ROOT/run_evqa_train_llava_blip2_virtual_delta_h_lga.sh"
nohup "$RUN_ROOT/run_evqa_train_llava_blip2_virtual_delta_h_lga.sh" \
  > "$RUN_ROOT/full_run.log" 2>&1 &
echo $! > "$RUN_ROOT/pid"
cat "$RUN_ROOT/pid"
```

## 6. 进度检查

```bash
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_train_virtual_delta_h_lga
RUN_ROOT=$OUT_ROOT/run

ps -fp "$(cat "$RUN_ROOT/pid")" || true
tail -80 "$RUN_ROOT/full_run.log"
nvidia-smi
```

检查已完成层：

```bash
for d in "$OUT_ROOT/llava_full" "$OUT_ROOT/blip2_full"; do
  echo "===== $d ====="
  [ -f "$d/virtual_delta_h_lga_layer_scores.csv" ] && wc -l "$d/virtual_delta_h_lga_layer_scores.csv" || true
  [ -f "$d/summary.md" ] && tail -80 "$d/summary.md" || true
done
```

注意：当前脚本按层写 `sample_virtual_delta_h_scores.jsonl`，最终才写 layer summary。如果运行中断，可先检查 jsonl 里最后完成到哪一层。

```bash
tail -20 "$OUT_ROOT/llava_full/sample_virtual_delta_h_scores.jsonl" | cut -c 1-240
tail -20 "$OUT_ROOT/blip2_full/sample_virtual_delta_h_scores.jsonl" | cut -c 1-240
```

## 7. 输出文件

每个模型输出目录应包含：

```text
old_answer_mapping_report.json
sample_virtual_delta_h_scores.jsonl
virtual_delta_h_lga_layer_scores.csv
topk_virtual_delta_h_layers.json
summary.md
run_config.json
```

最重要的是：

```text
virtual_delta_h_lga_layer_scores.csv
topk_virtual_delta_h_layers.json
summary.md
```

`virtual_delta_h_lga_layer_scores.csv` 至少检查以下字段：

```text
S_v_dot
S_v_conflict
S_v_dot_per_dim
S_v_cos
S_v_old_norm
S_v_new_norm
S_v_joint_norm
S_v_positive_ratio
S_v_zero_grad
S_t_dot
S_t_conflict
S_t_dot_per_dim
S_t_cos
S_t_old_norm
S_t_new_norm
S_t_joint_norm
S_t_positive_ratio
S_t_zero_grad
```

## 8. 层选择与解释规则

不要只看 raw dot。至少同时报告：

```text
visual dot Top-5
visual conflict Top-5
visual dot_per_dim Top-5
visual new_norm Top-5
visual cos Top-5
text dot Top-5
text conflict Top-5
text dot_per_dim Top-5
text new_norm Top-5
text cos Top-5
zero_grad layers
```

结合 Bridge30 校准经验，优先关注：

```text
LLaVA visual: M_newn_x_1mcos = S_v_new_norm * (1 - S_v_cos)
BLIP2 visual: M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm
text 分支: M_dot / M_new_norm / M_conflict 都要同时看
```

其中：

```text
M_dot = S_dot
M_conflict = -S_dot
M_new_norm = S_new_norm
M_newn_x_1mcos = S_new_norm * (1 - S_cos)
M_abscos_x_newn = abs(S_cos) * S_new_norm
```

E-VQA 上是否沿用 Bridge30 的最佳指标，必须后续用真实 adapter sweep 验证。LGA 只能给候选层和梯度诊断，不能直接等同于真实最佳编辑层。

### 8.1 待检验假设：DualEdit 分模态最佳层是否跨模型一致

本节只作为检验设计，不预设结论。手册实际算出的 LGA 指标必须完整保留并做分析，不能用外部图片中的层号替代 `virtual_delta_h_lga_layer_scores.csv` 与 `topk_virtual_delta_h_layers.json` 的结果。

附加参考信息：

| Backbone | 文本模态参考层 | 视觉模态参考层 | 可信度 | 使用方式 |
| --- | ---: | ---: | --- | --- |
| BLIP2-OPT-2.7B | Layer 16 | Layer 19 | 可信 | 作为 BLIP2 的外部参考标签，用来检验 E-VQA LGA 是否能恢复 text=16、visual=19 |
| LLaVA-V1.5-7B | Layer 16 | Layer 19 | 不可信 | 只作为附加对照信息，不能作为 LLaVA 的判定标签；LLaVA 以本实验 LGA 指标和后续真实 adapter sweep 为准 |

检验时分别读取 LLaVA / BLIP2 的 `topk_virtual_delta_h_layers.json` 和 `virtual_delta_h_lga_layer_scores.csv`，按 visual / text 两个分支独立分析。

BLIP2 的外部参考目标：

```text
BLIP2 text 分支参考目标：Layer 16
BLIP2 visual 分支参考目标：Layer 19
```

LLaVA 的分析方式：

```text
LLaVA 不使用图片中的 Layer 16 / Layer 19 作为准确标签。
LLaVA 需要保留所有 LGA 指标，并报告每个指标给出的 text / visual top-k。
如果 LLaVA 的 LGA top-k 自发接近 Layer 16 / Layer 19，只能写为“与附加参考一致”，不能写为“命中真实标签”。
```

判定标准：

| 结论 | 判定条件 |
| --- | --- |
| BLIP2_SUPPORT | BLIP2 的 text 分支候选最佳层为 Layer 16，且 visual 分支候选最佳层为 Layer 19 |
| BLIP2_PARTIAL_SUPPORT | BLIP2 的 Layer 16 / Layer 19 没有全部成为 top-1，但分别出现在对应分支 Top-3 或 Top-5 内，或最佳层与参考层相差不超过 1 层 |
| BLIP2_NOT_SUPPORT | BLIP2 的 text 分支稳定偏离 Layer 16，或 visual 分支稳定偏离 Layer 19，且参考层不在主要指标 Top-5 内 |
| LLAVA_METRIC_ONLY | LLaVA 只报告 LGA 指标排序与候选层，不用图片层号判断 SUPPORT / NOT_SUPPORT |

优先用于分析的指标：

| Model | visual 主分析指标 | text 主分析指标 |
| --- | --- | --- |
| LLaVA-V1.5-7B | `M_newn_x_1mcos = S_v_new_norm * (1 - S_v_cos)`，同时保留 `S_v_dot`、`S_v_conflict`、`S_v_new_norm`、`S_v_cos` | `S_t_new_norm`、`S_t_dot`、`S_t_conflict` 综合判断，并保留所有 `S_t_*` 指标 |
| BLIP2-OPT-2.7B | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm`，同时保留 `S_v_dot`、`S_v_conflict`、`S_v_new_norm`、`S_v_cos` | `S_t_new_norm`、`S_t_dot`、`S_t_conflict` 综合判断，并保留所有 `S_t_*` 指标 |

结果回填时必须保留三类信息：

1. 每个模型、每个模态、每个 LGA 指标的 top-k 层。
2. BLIP2 的 `Layer 16 / Layer 19` 是否命中对应分支的 top-1；如果没有命中 top-1，记录参考层在对应分支 Top-k 中的排名。
3. LLaVA 只记录 LGA 指标产生的候选层，以及这些候选层是否“附加对照上接近 Layer 16 / Layer 19”；不得把图片中的 LLaVA 层号写成准确标签。

回填模板：

| Model | Branch | Reference Layer | Best Layer | Reference Rank | Verdict | Main Metric | Notes |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| LLaVA-V1.5-7B | text | 16 |  |  | LLAVA_METRIC_ONLY |  | 图片参考不可信，只作附加对照 |
| LLaVA-V1.5-7B | visual | 19 |  |  | LLAVA_METRIC_ONLY |  | 图片参考不可信，只作附加对照 |
| BLIP2-OPT-2.7B | text | 16 |  |  |  |  | BLIP2 参考层可信 |
| BLIP2-OPT-2.7B | visual | 19 |  |  |  |  | BLIP2 参考层可信 |

## 9. 结果回填格式

建议新建结果文档：

```text
md/glodenlayer/EVQA_Train_LLaVA_BLIP2_Virtual_DeltaH_LGA_Result.md
```

结果表模板：

```markdown
## LLaVA

| Branch | Metric | Top-5 Layers | Notes |
| --- | --- | --- | --- |
| visual | S_v_dot |  |  |
| visual | S_v_conflict |  |  |
| visual | S_v_new_norm |  |  |
| visual | M_newn_x_1mcos |  |  |
| text | S_t_dot |  |  |
| text | S_t_conflict |  |  |
| text | S_t_new_norm |  |  |

## BLIP2

| Branch | Metric | Top-5 Layers | Notes |
| --- | --- | --- | --- |
| visual | S_v_dot |  |  |
| visual | S_v_conflict |  |  |
| visual | S_v_new_norm |  |  |
| visual | M_abscos_x_newn |  |  |
| text | S_t_dot |  |  |
| text | S_t_conflict |  |  |
| text | S_t_new_norm |  |  |
```

## 10. 风险与注意事项

1. E-VQA train 是 6345 条，计算量约为 Bridge30 的 211 倍；全量运行可能需要很久。
2. 先跑 `--max-samples 100`，确认输出格式和显存正常后再跑全量。
3. `pred` 直接作为 old answer，不需要重新生成 old answer；但要保留 `old_answer_mapping_report.json` 检查映射是否完整。
4. 如果全量太慢，可先用固定随机子集，例如 500 / 1000 条，比较 top-k 稳定性后再决定是否跑完整 train。
5. 不要改原始 `vqa_train.json` / `vqa_eval.json`。
6. 如果脚本中断，先保存已有输出目录，再决定是否按层重跑；不要直接覆盖未备份结果。
