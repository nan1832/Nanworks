# PaliGemma-3B 训练不稳定问题记录

记录时间：2026-07-13

## 涉及范围

本文只记录当前已确认的两个数据集：

| Dataset | Model | 实验类型 |
|---|---|---|
| EVQA-pilot500 | PaliGemma-3B | top-3 并集层 epoch50 训练 + 最小 EMA checkpoint 评测 |
| MMKE-visual | PaliGemma-3B | top-3 并集层 epoch50 训练 + 最小 EMA checkpoint 评测 |

MMKE-entity 的 PaliGemma 后续如出现同类现象，按本文同一规则追加记录。

## 现象概述

PaliGemma-3B 在当前统一 VEAD/VisEdit 训练配置下不是稳定收敛型训练。它在 EVQA-pilot500 和 MMKE-visual 上均出现：

- 训练早期 checkpoint 被选中，后续 epoch 的 EMA loss 变大。
- 多层日志出现大量 `SANITIZE_NONFINITE_GRAD_BEFORE_STEP`。
- 个别层出现负 EMA loss 或极端 EMA loss。
- 个别层训练进程长时间占用 GPU 但无有效日志推进、无 `train.done`、无 `selected_checkpoint.tsv`。
- 评测结果层间波动极大，同一模型不同层从高分到接近无效都有。

这不是单个数据集偶发问题，而是 PaliGemma 与当前训练 recipe 的系统性不稳定。

## EVQA-pilot500 证据

已记录结果中 PaliGemma-3B 表现如下：

| Layer | Ckpt Epoch | EMA Loss | Average | 状态判断 |
|---|---:|---:|---:|---|
| L9 | 1 | 20.548170 | 36.16 | `TRAIN_RECOVERED_FROM_STALL`，非正常完整训练 |
| L10 | 1 | 9.293444 | 70.52 | early checkpoint 最优，后续不稳定 |
| L11 | 2 | 3.296938 | 80.99 | early checkpoint 最优，后续不稳定 |
| L12 | 1 | 5.001783 | 75.98 | early checkpoint 最优，后续不稳定 |
| L14 | 1 | -1369.521638 | 32.06 | 负 EMA，结果不可信 |
| L15 | 25 | 31.500783 | 40.11 | 完成但弱，仍有数值警告 |

服务器日志证据：

- pilot500 PaliGemma 多层日志中 `SANITIZE_NONFINITE_GRAD_BEFORE_STEP` 达到上千次级别。
- L14 出现负 EMA checkpoint：`ema_loss=-1369.521638`。
- L9 曾出现 stall/recovered 记录，不是标准 50 epoch 正常完成路径。

## MMKE-visual 证据

已完成部分 PaliGemma-3B 结果如下：

| Layer | Ckpt Epoch | EMA Loss | Average | 状态判断 |
|---|---:|---:|---:|---|
| L8 | 2 | 2.536566 | 91.29 | early checkpoint 最优，但评测高 |
| L9 | 6 | 0.517213 | 98.09 | 相对可用 |
| L10 | 24 | 0.348760 | 99.06 | 相对稳定 |
| L11 | 7 | 0.737678 | 97.07 | early checkpoint 最优，但评测高 |
| L12 | 50 | 0.401058 | 96.88 | 较正常 |
| L14 | 1 | -351.953961 | 39.03 | 负 EMA，结果不可信 |
| L17 | 6 | 30.831037 | 40.05 | 基本未学到有效编辑 |

当前补跑中 `MMKE-visual / PaliGemma-3B / L7` 的异常：

- 进程仍占用 GPU，但训练日志最后停在 `2026-07-12 13:01` 左右。
- 没有 `train.done`。
- 没有 `selected_checkpoint.tsv`。
- 没有进入评测。
- GPU0 当时仍有约 46GB 空闲，PaliGemma 进程约占 19GB，因此不是 CUDA OOM。
- 日志中多次出现 `SANITIZE_NONFINITE_GRAD_BEFORE_STEP`。

典型坏梯度位置：

```text
language_model.model.layers.7.mlp_begin.weight grad_bad=2097152/2097152
language_model.model.layers.7.influence_mapper.ln_img_reps.weight grad_bad=2048/2048
```

## 已排除原因

### 不是显存不足

异常发生时：

- GPU0 总显存约 80GB。
- 已用约 34GB。
- 空闲约 46GB。
- PaliGemma L7 进程约占 19GB。
- 日志无 `CUDA out of memory`。

因此不能解释为“跑 20 小时后才显存不够”。更准确地说是：训练进程仍在占卡，但没有有效产出。

### 不是单个数据集坏样本

EVQA-pilot500 和 MMKE-visual 均出现非有限梯度、早期 checkpoint、负 EMA 或弱结果。因此不是某个数据集单独导致。

### 存储问题是独立问题

MMKE-visual 和 MMKE-entity 曾出现 `/datapool` 写入失败、checkpoint 写入失败。该问题会导致 `PytorchStreamWriter failed writing file` 或 `No space left on device`。

但当前 PaliGemma 数值不稳定问题不等同于存储问题：

- 多个 PaliGemma 层在无写入错误时也出现大量非有限梯度。
- 当前 L7 卡住前没有新的 `No space left on device` 证据。

## 代码层面原因

当前 `editor/vllm_editors/vead/vead.py` 中，训练遇到非有限梯度时逻辑为：

```python
loss.backward()
...
if bad_grad_reasons:
    print('[SANITIZE_NONFINITE_GRAD_BEFORE_STEP]', ...)
    for module in self.adaptors.values():
        for param in module.parameters():
            if param.grad is not None:
                torch.nan_to_num_(param.grad, nan=0.0, posinf=0.0, neginf=0.0)
self.opt.step()
self.opt.zero_grad()
```

也就是说，当前逻辑只是把 NaN/Inf 梯度替换成 0，但仍继续执行 `optimizer.step()`。

这会导致：

- 异常 step 后 adapter 状态继续累积。
- PaliGemma 的 loss/EMA 可能持续发散。
- 可能出现负 EMA 或极端 EMA。
- 可能出现长时间占 GPU 但没有有效训练产物。

## 配置层面原因

当前 PaliGemma 配置为：

```yaml
edit_model_name: "paligemma-3b"
llm_hidden_size: 2048
adaptor_mid_dim: 1024
llm_layer_tmp: "language_model.model.layers.{}"
train_cfg:
  lr: 1.e-4
  rel_lambda: 1
  gen_lambda: 1
  loc_lambda: 1
  inf_mapper_lambda: 0.1
IT:
  add_it: true
  layers: [13,14,15,16]
  noise_level: 0.7
  vt_sample_n: 24
```

在该配置下，PaliGemma 对 IT / influence mapper 训练非常敏感。当前没有：

- grad clip。
- nonfinite step 直接 skip。
- 负 EMA / 极端 EMA checkpoint 过滤。
- PaliGemma 专用低学习率。

因此判断为：当前统一 recipe 对 PaliGemma 不稳定。

## 当前结果使用建议

主表中 PaliGemma 的这些结果不应简单视为与其他模型同等稳定的正常结果。

建议标记：

| 状态 | 使用规则 |
|---|---|
| `TRAIN_DONE` 且无负 EMA、评测高 | 可保留，但注明 PaliGemma 存在数值不稳定风险 |
| early checkpoint 最优 | `done_with_warning` |
| 大量非有限梯度但完成评测 | `unstable` |
| 负 EMA | `failed / unreliable` |
| 长时间无日志推进、无 selected checkpoint | `stalled / failed` |

EVQA-pilot500 的 L14、MMKE-visual 的 L14 不建议作为正常结果使用。

当前 MMKE-visual L7 应保护现场后停掉，标记为 `stalled / failed`，后续单独重跑。

## 后续修复方案

### A. baseline-retry

目的：验证同一配置重跑是否复现异常。

要求：

- 继续使用 `configs/vead/paligemma-3b.yaml`。
- 输出到独立目录，不能覆盖主实验。
- 每层独立 Python 进程。
- 每层重新初始化 adapter。
- 记录所有 `SANITIZE_NONFINITE_GRAD_BEFORE_STEP` 次数、负 EMA、stall 情况。

### B. PaliGemma-stable

目的：验证是否通过稳定训练 recipe 解决。

建议配置：

| 项目 | 建议 |
|---|---|
| LR | 从 `1e-4` 降到 `1e-5`，必要时 `5e-6` |
| grad clip | `clip_grad_norm_(trainable_params, 1.0)` |
| nonfinite grad | 出现 NaN/Inf 梯度时直接 skip step，不执行 optimizer step |
| checkpoint filter | 禁止选择负 EMA、NaN/Inf EMA、极端 EMA |
| save policy | 保持每 epoch 保存，仍按合法 EMA loss 选 best |
| IT | 初始保持开启；若仍不稳定，再做降低 `noise_level` 或 `inf_mapper_lambda` 的 ablation |

## 后续待办

- [ ] 停掉当前 `MMKE-visual / PaliGemma-3B / L7` stalled 进程并保护现场。
- [ ] 把 L7 标为 `stalled / failed`。
- [ ] 不在当前主 launcher 中继续硬跑 PaliGemma 异常层。
- [ ] 后续单独执行 `PaliGemma-baseline-retry`。
- [ ] 后续单独执行 `PaliGemma-stable`。
- [ ] 将 baseline-retry 与 stable 结果写入独立报告。
- [ ] 主实验表中保留原结果，但给 PaliGemma 异常层加注释，不与正常收敛模型直接等价比较。

