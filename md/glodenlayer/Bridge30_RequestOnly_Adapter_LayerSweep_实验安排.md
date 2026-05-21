# Bridge30 Request-Only Adapter Layer Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after the user approves it. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构造只使用 `request` 监督信号的 Bridge30 训练/验证实验，比较 adapter 挂载到 LLaVA 与 BLIP2 不同层时的实际编辑效果。

**Architecture:** 原始 `jsonl/json` 数据只读，不直接修改；所有 request-only 训练集、验证集、yaml、缓存和结果都写入新的派生目录。训练阶段只计算 request/reliability loss，不读取 `generality`、`locality`、`portability` 作为训练监督；验证阶段保留 request-only 验证与 full-metric 验证两条读数。

**Tech Stack:** VisEdit VEAD adapter、LLaVA-v1.5-7B、BLIP2-OPT-2.7B、Bridge30 数据、PyTorch、JSON/JSONL、YAML、Markdown 汇总。

---

## 0. 服务器模型路径

本实验在服务器上运行时，基础 VLM 模型配置与权重目录固定为：

| Model | Server path |
|---|---|
| LLaVA-v1.5-7B | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf` |
| BLIP2-OPT-2.7B | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b` |

运行训练/评估脚本前必须确认 `utils.load_vllm_for_edit()` 或对应模型加载配置实际指向上述目录。

---

## 1. 实验问题

当前 VEAD 训练默认同时使用：

```text
request / reliability
generality
locality
```

yaml 中也通常是：

```yaml
train_cfg:
  rel_lambda: 1
  gen_lambda: 1
  loc_lambda: 1
```

这次新增实验只回答一个问题：

> 当 adapter 的训练监督只来自 `request.image + request.prompt + request.target_new` 时，adapter 挂到 LLaVA / BLIP2 的哪一层效果最好？

因此本实验是一个 request-only ablation，不再把 `generality` 和 `locality` 混入训练 loss。

---

## 2. 严格约束

1. 不修改任何原始 `jsonl`：

```text
Ten_Classes/bridge/bridge_train/30_bridge_train.jsonl
Ten_Classes/bridge/bridge_val/30_bridge_val.jsonl
```

2. 不覆盖现有编辑数据：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
Ten_Classes/bridge/bridge_val/edit_30_bridge_val_eval_only_vis.json
```

3. 所有新数据放到派生目录：

```text
Ten_Classes/bridge/request_only/
```

4. 训练脚本必须能打印并保存以下断言：

```text
train_loss_mode = request_only
used_request_samples = 30
used_generality_samples_for_train = 0
used_locality_samples_for_train = 0
used_portability_samples_for_train = 0
IT.add_it = true
IT block = same_as_previous_bridge_only_vis_yaml
gen_lambda = 0.0
loc_lambda = 0.0
inf_mapper_lambda = 0.1
```

5. 验证可以读取 full-metric 数据，但只能在训练完成后用于评估，不参与 optimizer step。

---

## 3. 数据设计

### 3.1 源数据

| Split | Source | Count | 用途 |
|---|---|---:|---|
| train | `Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json` | 30 | 派生 request-only 训练集 |
| val | `Ten_Classes/bridge/bridge_val/edit_30_bridge_val_eval_only_vis.json` | 70 | 派生 request-only 验证集与 full-metric 验证集 |

### 3.2 新增派生文件

```text
Ten_Classes/bridge/request_only/
  train/
    edit_30_bridge_train_request_only.json
    manifest.json
  val/
    edit_30_bridge_val_request_only.json
    edit_30_bridge_val_full_metrics.json
    manifest.json
```

### 3.3 request-only 训练格式

为了兼容现有 loader，仍保留同样的顶层 schema，但训练文件里只保留 `request` 有效内容，其他指标清空：

```json
{
  "case_id": "train_0",
  "entity_id": "Q1056242",
  "entity_name": "Chikugo River Lift Bridge",
  "request": {
    "image": "train/images/GLDv2_084bb592a552d066.jpg",
    "prompt": "What is the name of this bridge?",
    "target_new": "Chikugo River Lift Bridge"
  },
  "generality": {
    "text_rephrase": [],
    "image_rephrase": []
  },
  "locality": {
    "text_loc": [],
    "image_loc": []
  },
  "portability": {
    "1hop": [],
    "2hop": []
  }
}
```

### 3.4 验证集两套视图

`edit_30_bridge_val_request_only.json` 用于判断 request-only 泛化到未见 bridge 实体时的可靠性。

`edit_30_bridge_val_full_metrics.json` 保留 `generality/locality`，但只用于最终评估：

```text
request accuracy      -> 是否成功写入新实体
generality accuracy   -> 改写是否能迁移到改写问法/图像
locality accuracy     -> 是否破坏无关知识
```

这份 full-metric 验证不参与训练，也不参与 early optimizer update。

---

## 4. 训练目标

request-only 训练 loss 定义为：

\[
\mathcal{L}_{request}
= CE(M_{\theta,\phi_L}(I_i,Q_i), y_i^{new})
\]

其中：

```text
I_i = request.image
Q_i = request.prompt
y_i^{new} = request.target_new
theta = frozen base VLM
phi_L = 第 L 层 adapter 参数
```

总 loss：

\[
\mathcal{L}_{total} = \mathcal{L}_{request}
\]

不计算：

```text
generality CE loss
locality KL loss
portability loss
```

保留：

```text
IT visual-strength modulation
```

说明：这里的 request-only 指“训练监督样本只来自 request”，不是关闭 IT。IT 模块控制视觉表征不同位置的编辑强度，应保持和之前 `bridge-only-vis` yaml 一样。旧训练代码里依赖 `generality/locality` 的 influence auxiliary 构造不能照搬；如果实现辅助 IT loss，它也只能从 request 样本派生。

---

## 5. YAML 规则

这次不沿用等比例三项 loss，但 `IT` 模块保持和之前 `bridge-only-vis` yaml 一样。每个候选层生成一个 request-only yaml：

```yaml
edit_model_name: "llava-v1.5-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"
edit_layers: [L]
train_cfg:
  lr: 1.e-4
  rel_lambda: 1.0
  gen_lambda: 0.0
  loc_lambda: 0.0
  inf_mapper_lambda: 0.1
port_lambda: 0.0
port_sample_n: 1
IT:
  add_it: true
  layers: [19,20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
```

BLIP2 只替换模型名、hidden size 和层模板：

```yaml
edit_model_name: "blip2-opt-2.7b"
llm_hidden_size: 2560
llm_layer_tmp: "language_model.model.decoder.layers.{}"
llm_att_tmp: "language_model.model.decoder.layers.{}.self_attn"
IT:
  add_it: true
  layers: [20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
```

说明：`IT` 不是一个额外数据指标，而是 adapter 内部对视觉 token/视觉表征位置的强度控制。request-only 实验应保留该结构，只把训练监督限制为 `request`，并禁止旧的 `generality/locality` loss 进入优化。

---

## 6. 层位扫描范围

正式实验建议两模型都跑全层：

```text
LLaVA:  language_model.model.layers.0-31
BLIP2:  language_model.model.decoder.layers.0-31
```

如果资源不足，可以先跑 smoke/候选层，但最终结论必须来自完整 0-31 扫描。

候选层 smoke 建议：

| Model | Smoke layers | 来源 |
|---|---|---|
| LLaVA | `0,1,2,3,4,5,6,11,14,16,18,20,30` | Adapter-Output conflict/new-norm、Visual-Hidden、已有浅层经验 |
| BLIP2 | `0,1,2,3,4,5,14,15,16,19,26,28,29,30` | Adapter-Output conflict/new-norm、已有 BLIP2 层试验 |

---

## 7. 后续需要新增/修改的文件

### Task 1: 构造派生数据

**Files:**

- Create: `VisEdit-main/scripts/build_bridge_request_only_splits.py`
- Create: `Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json`
- Create: `Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json`
- Create: `Ten_Classes/bridge/request_only/val/edit_30_bridge_val_full_metrics.json`
- Create: `Ten_Classes/bridge/request_only/train/manifest.json`
- Create: `Ten_Classes/bridge/request_only/val/manifest.json`

- [ ] 从源 JSON 读取 30 train / 70 val 样本。
- [ ] 写出 request-only train JSON，清空 `generality/locality/portability`。
- [ ] 写出 request-only val JSON，清空 `generality/locality/portability`。
- [ ] 写出 full-metric val JSON，保留验证指标但归档到 request-only 实验目录。
- [ ] manifest 中记录源路径、输出路径、样本数、sha256、生成时间。
- [ ] 校验原始 `30_bridge_train.jsonl` 和 `30_bridge_val.jsonl` 未变化。

### Task 2: 生成 request-only yaml

**Files:**

- Create: `VisEdit-main/scripts/generate_bridge_request_only_yaml.py`
- Create: `Ten_Classes/bridge/request_only/configs/llava/llava-v1.5-7b-bridge-request-only-l{L}.yaml`
- Create: `Ten_Classes/bridge/request_only/configs/blip2/blip2-opt-2.7b-bridge-request-only-l{L}.yaml`

- [ ] 为 LLaVA 生成 32 个 yaml，`edit_layers: [0]` 到 `[31]`。
- [ ] 为 BLIP2 生成 32 个 yaml，`edit_layers: [0]` 到 `[31]`。
- [ ] 所有 yaml 固定 `rel_lambda=1.0`，`gen_lambda=0.0`，`loc_lambda=0.0`，`inf_mapper_lambda=0.1`。
- [ ] LLaVA yaml 的 `IT` 模块保持 `[19,20,21,22,23,24,25,26,27,28,29,30]`、`test_n=1`、`noise_level=0.7`、`vt_sample_n=24`。
- [ ] BLIP2 yaml 的 `IT` 模块保持 `[20,21,22,23,24,25,26,27,28,29,30]`、`test_n=1`、`noise_level=0.7`、`vt_sample_n=24`。
- [ ] 生成后抽查 layer 0、layer 1、layer 31。

### Task 3: 新增 request-only 训练入口

**Files:**

- Create: `VisEdit-main/bridge_train_request_only.py`
- Modify only if needed: `VisEdit-main/editor/vllm_editors/vead/vead.py`

- [ ] 新训练入口读取 `edit_30_bridge_train_request_only.json`。
- [ ] 训练 batch 只组织 request/reliability xym。
- [ ] `train_a_batch` 只计算 request CE loss。
- [ ] 不调用依赖 `generality/locality` 的旧版 `__get_xy_for_influence_mapper__`。
- [ ] 保留 adapter forward 中的 IT visual-strength modulation，使 influence mapper 可以通过 request CE 梯度被训练。
- [ ] 不遍历 `generality`、`locality` 作为训练 loss。
- [ ] 每次 run 保存 `run_config.json`，包含 layer、model、data path、loss mode、seed、epochs。

### Task 4: 新增评估与汇总

**Files:**

- Create: `VisEdit-main/scripts/eval_bridge_request_only_ckpt.py`
- Create: `VisEdit-main/scripts/summarize_bridge_request_only_layer_sweep.py`

- [ ] 对每个 checkpoint 跑 train request eval。
- [ ] 对每个 checkpoint 跑 val request-only eval。
- [ ] 对每个 checkpoint 跑 val full-metric eval。
- [ ] 输出每层最佳 checkpoint 与最终指标。
- [ ] 汇总 LLaVA / BLIP2 的 top-5 层位表。

---

## 8. 运行计划

### 8.1 数据与 yaml 生成

```bash
cd VisEdit-main
python scripts/build_bridge_request_only_splits.py \
  --train-source ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --val-source ../Ten_Classes/bridge/bridge_val/edit_30_bridge_val_eval_only_vis.json \
  --output-root ../Ten_Classes/bridge/request_only

python scripts/generate_bridge_request_only_yaml.py \
  --output-root ../Ten_Classes/bridge/request_only/configs \
  --layers 0-31
```

### 8.2 LLaVA 层扫描

```bash
cd VisEdit-main
python bridge_train_request_only.py \
  --model-name llava-v1.5-7b \
  --config ../Ten_Classes/bridge/request_only/configs/llava/llava-v1.5-7b-bridge-request-only-l{L}.yaml \
  --data-path ../Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge-root ../Ten_Classes/bridge \
  --cache-root ../server_results/bridge_request_only_layer_sweep/llava/layer_{L}/cache \
  --output-dir ../server_results/bridge_request_only_layer_sweep/llava/layer_{L} \
  --epochs 500 \
  --batch-size 1 \
  --save-ckpt-per-i 100 \
  --random-seed 2026 \
  --device cuda:0
```

### 8.3 BLIP2 层扫描

```bash
cd VisEdit-main
python bridge_train_request_only.py \
  --model-name blip2-opt-2.7b \
  --config ../Ten_Classes/bridge/request_only/configs/blip2/blip2-opt-2.7b-bridge-request-only-l{L}.yaml \
  --data-path ../Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge-root ../Ten_Classes/bridge \
  --cache-root ../server_results/bridge_request_only_layer_sweep/blip2/layer_{L}/cache \
  --output-dir ../server_results/bridge_request_only_layer_sweep/blip2/layer_{L} \
  --epochs 500 \
  --batch-size 1 \
  --save-ckpt-per-i 100 \
  --random-seed 2026 \
  --device cuda:0
```

### 8.4 每层 checkpoint 验证

```bash
cd VisEdit-main
python scripts/eval_bridge_request_only_ckpt.py \
  --model-name {llava-v1.5-7b|blip2-opt-2.7b} \
  --config <layer-yaml> \
  --ckpt-path <checkpoint> \
  --train-request-data ../Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --val-request-data ../Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json \
  --val-full-data ../Ten_Classes/bridge/request_only/val/edit_30_bridge_val_full_metrics.json \
  --bridge-root ../Ten_Classes/bridge \
  --output-dir <layer-eval-output-dir>
```

---

## 9. 选层标准

每层保存一个 `layer_summary.json`，至少包含：

```json
{
  "model": "llava-v1.5-7b",
  "layer": 1,
  "best_checkpoint": "epoch-xxx-i-xxxx-ema_loss-xxxx",
  "train_request_acc": 0.0,
  "val_request_acc": 0.0,
  "val_request_loose_acc": 0.0,
  "val_generality_text_acc": 0.0,
  "val_generality_image_acc": 0.0,
  "val_locality_text_acc": 0.0,
  "val_locality_image_acc": 0.0,
  "selection_score": 0.0
}
```

主排序：

```text
1. val_request_loose_acc
2. val_request_acc
3. val_generality_image_acc
4. val_locality_image_acc
5. train_request_acc 不能明显低于同组其他层
```

不建议只按训练 loss 选层，因为 request-only 很容易记住 30 个 train 样本。

---

## 10. 结果目录

```text
server_results/bridge_request_only_layer_sweep/
  llava/
    layer_0/
    layer_1/
    ...
    layer_31/
    llava_request_only_layer_sweep_summary.md
    llava_request_only_layer_sweep_scores.csv
  blip2/
    layer_0/
    layer_1/
    ...
    layer_31/
    blip2_request_only_layer_sweep_summary.md
    blip2_request_only_layer_sweep_scores.csv
  Bridge30_RequestOnly_Adapter_LayerSweep_Result.md
```

最终总表：

| Model | Best Layer | Val Request Loose | Val Request Strict | Generality Image | Locality Image | Top-5 Layers |
|---|---:|---:|---:|---:|---:|---|
| LLaVA | 待实验 | 待实验 | 待实验 | 待实验 | 待实验 | 待实验 |
| BLIP2 | 待实验 | 待实验 | 待实验 | 待实验 | 待实验 | 待实验 |

并和已有 LGA 结果对照：

| Model | Adapter-Output Conflict Top-5 | Adapter-Output New-Norm Top-5 | Visual-Hidden New-Norm Top-5 | Request-Only Brute Best |
|---|---|---|---|---|
| LLaVA | `[3, 0, 4, 2, 5]` | `[3, 6, 0, 4, 5]` | `[6, 7, 5, 3, 4]` | 待实验 |
| BLIP2 | `[3, 14, 2, 15, 0]` | `[4, 5, 0, 1, 3]` | `[0, 1, 2, 3, 4]` | 待实验 |

---

## 11. 验收检查

- [ ] 原始 `30_bridge_train.jsonl` hash 未变化。
- [ ] 原始 `30_bridge_val.jsonl` hash 未变化。
- [ ] 派生 train request-only count = 30。
- [ ] 派生 val request-only count = 70。
- [ ] 服务器存在 LLaVA 模型目录 `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf`。
- [ ] 服务器存在 BLIP2 模型目录 `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b`。
- [ ] 训练日志显示 `used_generality_samples_for_train = 0`。
- [ ] 训练日志显示 `used_locality_samples_for_train = 0`。
- [ ] 训练日志显示 `IT.add_it = true`。
- [ ] 训练日志显示 `IT block = same_as_previous_bridge_only_vis_yaml`。
- [ ] LLaVA 每层都有至少一个 checkpoint 和 eval summary。
- [ ] BLIP2 每层都有至少一个 checkpoint 和 eval summary。
- [ ] 汇总表能给出 LLaVA top-5、BLIP2 top-5 和 best layer。
- [ ] 最终结果明确区分 request-only 训练效果与 full-metric 验证效果。

---

## 12. 预期解释

如果 LLaVA 最佳层落在浅层，例如 layer 0-6，且与 Adapter-Output conflict/new-norm 接近，可以说明：

> LLaVA 的 request-only 实体编辑主要依赖浅层视觉 token 表征修正，generality/locality loss 不是浅层有效性的唯一来源。

如果 BLIP2 最佳层落在中层，例如 layer 14-19，可以说明：

> BLIP2 虽然浅层 visual prefix 对 target_new 敏感，但真正可控的实体替换可能更依赖 OPT decoder 中层。

如果 request-only 的最佳层和三指标等比例训练的最佳层不同，则说明：

> `generality/locality` 不只是正则项，也改变了 adapter 的最优挂载层。
