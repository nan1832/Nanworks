# Ours-Direct 下一步修复报告

更新时间：2026-06-29

## 0. 阶段边界

本报告只针对 `Ours-Direct` 候选层实验的指标修复与诊断，不启动真实 adapter 训练。

本阶段只做：

1. 冻结当前 `Ours-Direct` 主结果；
2. 从已有 layer score 文件派生 Ours 系列消融候选层；
3. 诊断并修复 Qwen2.5-VL-3B 的 `model_pred` 覆盖问题；
4. 输出后续真实扫层可使用的候选层 Top-K 文件。

本阶段不做：

1. 不做真实 50 epoch adapter 训练；
2. 不做 full-layer sweep；
3. 不补跑 `Perturb-KL-Direct`；
4. 不补跑 `CMA-Direct`；
5. 不补跑 `LGA-Param-Direct`；
6. 不用 ablation 结果覆盖 `Ours-Direct` 主结果。

当前主运行目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_direct_7models_3datasets_g08_gpu0_20260626_131624
```

## 1. 当前状态

截至当前记录，21 组 `7 models × 3 datasets` 已经完成一次主流程与补跑监控。

| Status | Count | 含义 |
|---|---:|---|
| done | 8 | 主公式给出合法 Top-3/Top-5 |
| low_confidence | 3 | 有候选层，但有效样本覆盖不足 |
| failed | 10 | 未产生合法主候选层 |
| total | 21 | 7 models × 3 datasets |

当前没有看到继续运行的 `Ours-Direct` 主进程。已有主结果应先冻结，不直接覆盖。

## 2. 当前主公式与问题

### 2.1 当前主方法：Ours-Direct

当前主方法使用严格负余弦冲突门控：

```text
S_ours(l)
= max(0, -S_v_cos(l))
  * S_v_new_norm(l)
  * S_v_depth2(l)
```

其中：

```text
S_v_depth2(l) = ((l + 1) / L)^2
```

该结果是当前主实验结果，只冻结和保留，不用其他公式覆盖。

### 2.2 主要失败原因

多个组合并不是进程崩溃，而是主公式经过方向门控后没有合法层：

```text
no_valid_ours_direct_layer
```

这说明数据、hook、逐层 score 不一定失效；更可能是严格 `max(0, -S_v_cos)` 门控把正向或混合方向的层全部清零。

### 2.3 Qwen 组合存在覆盖问题

Qwen2.5-VL-3B 的问题需要分级处理，不能一刀切。

| Dataset / Model | 当前有效覆盖 | 当前状态 | 建议处理 |
|---|---:|---|---|
| EVQA-pilot500 / Qwen2.5-VL-3B | 457/500, 0.914 | failed | coverage 较高，可先从已有 score 派生 ablation 候选，同时检查 `empty_model_pred` |
| MMKE-visual / Qwen2.5-VL-3B | 96/214, 0.449 | low_confidence | 候选只作参考，需修 `model_pred` 后再重跑候选 |
| MMKE-entity / Qwen2.5-VL-3B | 5/636, 0.008 | low_confidence | 强制标记 `invalid_low_coverage`，当前不得进入主候选比较 |

## 3. 方法名与公式规范

主结果和诊断/消融结果必须分表保存，不允许用消融结果覆盖主方法。

| Method | score_variant | Formula | 是否主结果 |
|---|---|---|---|
| Ours-Direct | conflict_main | `max(0, -S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)` | 是 |
| Ours-AbsDirection-Direct | abs_cos_ablation | `abs(S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)` | 否 |
| Ours-NoDirection-Direct | new_norm_depth_ablation | `S_v_new_norm(l) * S_v_depth2(l)` | 否 |
| Ours-1MinusCos-Direct | one_minus_cos_ablation | `(1 - S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)` | 否 |

用途说明：

- `Ours-AbsDirection-Direct`：检验不区分正向/反向时，方向关系强度是否能给出更稳定候选层；
- `Ours-NoDirection-Direct`：检验只依赖新知识视觉梯度强度和深度因子能否给出候选层；
- `Ours-1MinusCos-Direct`：软化 `max(0, -S_v_cos)` 的硬负方向门控，使正向但方向差异较大的层仍有可能被排序。

## 4. 输出字段规范

### 4.1 冻结主结果字段

输出：

```text
frozen_ours_direct_main_candidates.csv
frozen_ours_direct_main_candidates.md
```

字段：

```text
dataset
model
method
score_variant
main_top3
main_top5
status
valid_samples
total_samples
coverage
failure_reason
source_run
```

要求：

1. 不覆盖 `done / low_confidence / failed`；
2. 不把消融结果写回主结果；
3. 不删除 failed 组合。

### 4.2 失败原因统计字段

每个组合需要补充失败原因统计：

```text
empty_model_pred_count
missing_image_count
empty_visual_span_count
zero_grad_layer_count
nonfinite_score_layer_count
no_negative_cos_layer_count
valid_sample_count
total_sample_count
coverage
failure_reason_major
```

`failure_reason_major` 可取：

```text
no_valid_ours_direct_layer
empty_model_pred
invalid_low_coverage
missing_required_score_columns
empty_visual_span
zero_grad_or_nonfinite
unknown
```

## 5. layer score 可派生性检查

从已有 layer score 文件派生 ablation 候选层前，必须检查必要列是否存在。

必要列：

```text
layer
S_v_cos
S_v_new_norm
S_v_depth2
S_v_zero_grad
```

建议列：

```text
S_v_dot
S_v_conflict
S_v_positive_ratio
S_v_old_norm
S_v_new_nonzero_ratio
visual_token_start
visual_token_end
```

如果缺少必要列，不得派生候选层，应标记为：

```text
cannot_derive_ablation_missing_required_columns
```

并输出缺失列：

```text
missing_required_columns
```

输出文件：

```text
ours_layer_score_derivability_report.csv
```

字段：

```text
dataset
model
score_file
can_derive
missing_required_columns
n_layers
valid_layers
invalid_layers
status
```

## 6. 消融候选层派生规则

从已有 layer score 文件派生：

```text
Ours-AbsDirection-Direct
Ours-NoDirection-Direct
Ours-1MinusCos-Direct
```

候选层清洗规则：

1. 删除 `S_v_zero_grad=true` 的层；
2. 删除 `S_v_cos / S_v_new_norm / S_v_depth2` 非有限值的层；
3. 删除 visual span 为空的层；
4. 去重并保留第一次出现；
5. 不自动用其他方法补齐；
6. 若不足 Top-K，保留实际数量并标记 `insufficient_valid_layers`。

输出：

```text
ours_direct_metric_ablation_candidates_summary.csv
ours_direct_metric_ablation_candidates_summary.md
```

字段：

```text
dataset
model
method
score_variant
formula
top3
top5
raw_top3
raw_top5
clean_top3
clean_top5
valid_samples
total_samples
coverage
status
failure_reason
source_score_file
```

## 7. coverage 与状态判定

统一状态判定：

| Coverage | Status | 说明 |
|---:|---|---|
| >= 0.80 | done | 可进入候选层比较 |
| 0.20 - 0.80 | low_confidence | 可作参考，不进入强结论 |
| < 0.20 | invalid_low_coverage | 不进入主候选比较 |

特殊规则：

```text
MMKE-entity / Qwen2.5-VL-3B 当前强制标记为 invalid_low_coverage，
直到 model_pred 覆盖修复。
```

## 8. Qwen 专项诊断与修复

Qwen 修复先生成诊断报告，不直接进入真实训练。

检查项：

```text
prompt template 是否与 Qwen-VL processor 对齐
image tensor 是否正常进入模型
max_new_tokens 是否过小
stop tokens 是否过早截断
model_pred 是否为空字符串
样本 ID 与输出文件是否错位
visual token span 是否为空
```

输出：

```text
qwen_model_pred_empty_report.csv
qwen_model_pred_mapping_report.json
qwen_ours_direct_coverage_recheck.md
```

修复后只重跑：

```text
Qwen2.5-VL-3B 的 model_pred 生成
Qwen2.5-VL-3B 的 Ours metric extraction
```

不启动真实 adapter 训练。

## 9. 执行流程

### Step 1：冻结当前 Ours-Direct 主结果

输入：

```text
ours_direct_candidates_summary.csv
ours_direct_candidates_summary.md
```

输出：

```text
frozen_ours_direct_main_candidates.csv
frozen_ours_direct_main_candidates.md
```

### Step 2：检查 layer_scores 可派生性

对每个 `dataset × model` 检查逐层 score 文件是否存在、必要列是否齐全。

输出：

```text
ours_layer_score_derivability_report.csv
```

### Step 3：派生 Ours 系列消融候选

从已有 layer score 文件派生三种消融候选，并同时保存 raw 与 clean 版本：

```text
Ours-AbsDirection-Direct
Ours-NoDirection-Direct
Ours-1MinusCos-Direct
```

输出：

```text
ours_direct_metric_ablation_candidates_summary.csv
ours_direct_metric_ablation_candidates_summary.md
```

### Step 4：重新计算 coverage 与状态

按 `done / low_confidence / invalid_low_coverage` 重新标记 ablation 表状态。

### Step 5：Qwen 专项诊断

生成 Qwen 空预测、样本映射、coverage 复查报告。修复前，`MMKE-entity / Qwen2.5-VL-3B` 不进入主候选比较。

### Step 6：输出最终候选层文件

本阶段最终输出：

```text
frozen_ours_direct_main_candidates.csv
frozen_ours_direct_main_candidates.md
ours_layer_score_derivability_report.csv
ours_direct_metric_ablation_candidates_summary.csv
ours_direct_metric_ablation_candidates_summary.md
qwen_model_pred_empty_report.csv
qwen_ours_direct_coverage_recheck.md
```

其中：

```text
frozen_ours_direct_main_candidates.*
```

只记录当前主公式结果。

```text
ours_direct_metric_ablation_candidates_summary.*
```

只记录方向消融/强度消融候选结果。

两者不得混写。

## 10. 最小可执行清单

- [ ] 冻结当前主结果，输出 `frozen_ours_direct_main_candidates.csv/md`
- [ ] 生成 `ours_layer_score_derivability_report.csv`
- [ ] 检查每组是否包含 `layer / S_v_cos / S_v_new_norm / S_v_depth2 / S_v_zero_grad`
- [ ] 派生 `Ours-AbsDirection-Direct`
- [ ] 派生 `Ours-NoDirection-Direct`
- [ ] 派生 `Ours-1MinusCos-Direct`
- [ ] 输出 raw_top3/raw_top5 与 clean_top3/clean_top5
- [ ] 补充失败原因统计字段
- [ ] 将 `MMKE-entity / Qwen2.5-VL-3B` 标为 `invalid_low_coverage`
- [ ] 生成 Qwen `empty_model_pred` 与 coverage 诊断报告
- [ ] 主结果和消融结果分别成表，禁止混写

## 11. 结论

Ours-Direct 当前的核心问题不是所有组合运行失败，而是严格负余弦方向门控与 Qwen 生成覆盖异常叠加。下一步应先冻结主结果，再基于已有 layer score 派生方向/强度消融候选，并单独诊断 Qwen 的 `model_pred` 覆盖问题。

主结果、消融结果、Qwen 修复结果必须分表记录。只有覆盖率可靠、方法名清晰、失败原因可追踪后，才进入后续真实训练评测。
