# PaliGemma 双版本重跑实验 TODO

## 目标

后续单独做两组 PaliGemma 补充实验，用来判断 PaliGemma 在当前 VisEdit/VEAD 训练配置下出现的 loss 不收敛、负 EMA、CUDA stall，到底是偶发运行问题、当前 recipe 不适配，还是模型/wrapper/data 路径本身存在问题。

两组实验都只作为补充表/敏感性分析，不和 7 模型统一配置主实验混表。主实验仍保留统一配置口径，PaliGemma 异常层需要明确标注。

## 双版本重跑策略

| 版本 | 名称 | 配置口径 | 目的 | 是否进入主排名 |
|---|---|---|---|---|
| A | `PaliGemma-baseline-retry` | 完全沿用当前主实验 PaliGemma 配置、学习率、IT 路径和 checkpoint 选择规则 | 验证当前异常是否可复现，排除偶发进程中断、日志混入、单次 CUDA stall 等运行问题 | 不进入；只作为主实验异常复核 |
| B | `PaliGemma-stable` | 保持编辑目标、IT 路径、候选层不变，只降低 LR、加 grad clip、nonfinite step skip、过滤异常 checkpoint | 验证 PaliGemma 是否需要独立稳定训练 recipe 才能正常收敛 | 不进入；只作为稳定性/敏感性分析 |

判断逻辑：

- A 版仍不收敛、B 版收敛：说明主要是当前训练 recipe 对 PaliGemma 不稳定，主实验应保留原配置结果并给 PaliGemma 加异常注释。
- A 版收敛、B 版也收敛：说明之前更可能是单次运行/日志混入/进程中断问题，可回看原主实验对应层是否需要替换为 A 版复跑结果；替换前必须单独标注。
- A 版和 B 版都不收敛：优先排查 PaliGemma wrapper、adapter 挂载位置、IT loss 路径、token 对齐或数据格式。
- A 版不收敛、B 版也只改善不明显：保留 PaliGemma 作为“不适配当前 VisEdit/VEAD 训练 recipe”的特殊模型，不和其他模型直接比较收敛质量。

## 当前问题记录

### EVQA-pilot500

| Layer | 当前状态 | 问题 |
|---:|---|---|
| L9 | abnormal/recovered | 训练卡在 CUDA 同步，使用 early checkpoint 恢复评测，不是标准 50 epoch 完整结果 |
| L10 | unstable | 50 epoch 完成，但 early checkpoint 最优，后期 EMA 变大，存在大量非有限梯度告警 |
| L11 | unstable | 50 epoch 完成，但 early checkpoint 最优，后期 EMA 变大，存在非有限梯度告警 |
| L12 | unstable | 50 epoch 完成，但 early checkpoint 最优，后期 EMA 变大，存在非有限梯度告警 |
| L14 | failed | loss_history 混入多次运行，出现负 EMA，不可作为正常结果 |
| L15 | done_with_warning | 50 epoch 完成，选中 epoch25，但仍有数值告警 |

### MMKE-visual

| Layer | 当前状态 | 问题 |
|---:|---|---|
| L8 | done_with_note | early checkpoint 最优，后期 EMA 变大，但评测结果高 |
| L9 | done_with_note | early checkpoint 最优，后期 EMA 变大，但评测结果高 |
| L10 | done | 结果较稳定，可保留 |
| L11 | done_with_note | early checkpoint 最优，后期 EMA 变大，但评测结果高 |
| L12 | done | epoch50 最优，较正常 |
| L14 | failed | 出现负 EMA，评测差，不可作为正常结果 |
| L17 | weak/unstable | 基本学不动，评测接近 no-edit 底线 |

### MMKE-entity

截至本 TODO 创建时，MMKE-entity 还没有跑到 PaliGemma 层。后续如果出现同类现象，按同一规则标记。

## A 版：baseline-retry 配置要求

保持和当前主实验完全一致：

- 使用现有 `configs/vead/paligemma-3b.yaml`。
- 不改 LR、不改 loss 权重、不关 IT、不改候选层。
- 每层独立 Python 进程，每层重新初始化 adapter。
- 输出目录必须和主实验分开，不能覆盖或接续当前主实验 checkpoint。
- 目的不是追求更好结果，而是验证“同一配置重跑是否仍然失败/不收敛”。

## B 版：stable 配置要求

保持和主实验相同的编辑目标与 IT 口径：不关闭 IT，不改变候选层集合，不混用 adapter。

需要新增一个 PaliGemma 专用稳定配置，例如 `configs/vead/paligemma-3b-stable.yaml`：

| 项目 | 建议 |
|---|---|
| lr | 从 `1e-4` 降到 `1e-5`，必要时试 `5e-6` |
| grad clip | 添加 `clip_grad_norm_(trainable_params, 1.0)` |
| nonfinite grad | 出现 NaN/Inf 梯度时跳过该 step，清空梯度，不做 optimizer step |
| checkpoint filter | 禁止选择负 EMA、NaN/Inf EMA、异常极端 EMA checkpoint |
| save policy | 每 epoch 保存，仍按 EMA loss 选 best checkpoint |
| IT | 保持开启；如仍不稳定，再记录一版降低 `noise_level` 或 `inf_mapper_lambda` 的 ablation |

## 重跑范围

只重跑 PaliGemma，不重跑其他模型。

### EVQA-pilot500 PaliGemma top-3 并集

候选层：`L12, L11, L10, L15, L14, L9, L8`

要求：

- 每层独立 Python 进程。
- 每层重新初始化 adapter。
- 不加载上一层 adapter。
- 训练 50 epoch。
- A 版和 B 版都要使用独立输出目录，不能互相覆盖。
- A 版输出目录示例：

```text
server_results/paligemma_baseline_retry_pilot500_top3_union_YYYYMMDD_HHMMSS/
```

- B 版输出目录示例：

```text
server_results/paligemma_stable_pilot500_top3_union_YYYYMMDD_HHMMSS/
```

### MMKE-visual PaliGemma top-3 并集

候选层：`L12, L11, L10, L14, L17, L9, L8`

输出目录必须和主实验分开，例如：

```text
server_results/paligemma_baseline_retry_mmke_visual_top3_union_YYYYMMDD_HHMMSS/
```

```text
server_results/paligemma_stable_mmke_visual_top3_union_YYYYMMDD_HHMMSS/
```

### MMKE-entity PaliGemma top-3 并集

候选层：`L13, L12, L11, L15, L16, L17, L9, L10, L8`

输出目录必须和主实验分开，例如：

```text
server_results/paligemma_baseline_retry_mmke_entity_top3_union_YYYYMMDD_HHMMSS/
```

```text
server_results/paligemma_stable_mmke_entity_top3_union_YYYYMMDD_HHMMSS/
```

## 结果判定规则

| 状态 | 判定 |
|---|---|
| DONE | 50 epoch 完成，eval 完成，无负 EMA，无 NaN/Inf，无 CUDA stall |
| DONE_WITH_NOTE | 50 epoch 完成，early checkpoint 最优，但无负 EMA/NaN/Inf，eval 正常 |
| UNSTABLE | 出现非有限梯度告警或 loss 明显发散，但 eval 可完成 |
| FAILED | 负 EMA、NaN/Inf EMA、CUDA stall、训练中断、缺 checkpoint、eval 失败 |

## 汇总要求

双版本重跑结果单独写入新表，不覆盖主实验：

```text
md/Location/paligemma_baseline_vs_stable_top3_union_rerun_outcome.md
```

表格至少包含：

| Dataset | Model | Layer | Config | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Status | Note |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|

其中 `Config` 必须明确写 `baseline-retry` 或 `stable`。主实验总结中只引用双版本重跑作为补充分析，不能把 baseline-retry/stable 结果和统一配置主实验结果直接混在同一个排名表里。

## 待办清单

- [ ] 写 PaliGemma-baseline-retry launcher，复用当前 `paligemma-3b.yaml`，但输出到独立目录。
- [ ] 跑 EVQA-pilot500 PaliGemma baseline-retry top-3 并集。
- [ ] 跑 MMKE-visual PaliGemma baseline-retry top-3 并集。
- [ ] 跑 MMKE-entity PaliGemma baseline-retry top-3 并集。
- [ ] 新增 PaliGemma stable config。
- [ ] 修改训练循环：加 grad clip。
- [ ] 修改训练循环：nonfinite grad 直接 skip step。
- [ ] 修改 checkpoint 选择：过滤负 EMA、NaN/Inf、极端异常 EMA。
- [ ] 写 PaliGemma-stable launcher，保证每层独立进程。
- [ ] 跑 EVQA-pilot500 PaliGemma stable top-3 并集。
- [ ] 跑 MMKE-visual PaliGemma stable top-3 并集。
- [ ] 跑 MMKE-entity PaliGemma stable top-3 并集。
- [ ] 汇总 baseline-retry 与 stable 结果到 `paligemma_baseline_vs_stable_top3_union_rerun_outcome.md`。
- [ ] 在主实验结果表里给原 PaliGemma 异常层加注释，不直接删除。
- [ ] 对比主实验原结果 vs baseline-retry vs stable，判断 PaliGemma 异常是否来自训练 recipe 不适配、运行偶发问题或 wrapper/data 路径问题。
