# OursDirect_next_repair_report 修改意见整理

更新时间：2026-06-29

## 1. 总体判断

`OursDirect_next_repair_report.md` 的总体方向是可执行的：先冻结当前 `Ours-Direct` 主结果，再从已有逐层 score 文件派生方向相关/方向无关的消融候选，同时单独处理 Qwen2.5-VL-3B 的 `model_pred` 覆盖问题。

但该报告不能原封不动执行。当前主要问题不是流程方向错误，而是：

1. 公式表达不够严格；
2. 方法名和输出字段需要进一步规范；
3. Qwen 三个数据集组合不能一刀切处理；
4. coverage 阈值之外还缺少失败原因统计；
5. 从已有 score 派生候选前缺少必要列检查；
6. 本阶段边界需要写清楚：只修 Ours-Direct 不同指标出候选层，不做真实扫层训练，也不做 Perturb-KL / CMA / LGA。

---

## 2. 需要保留的内容

报告中以下原则是正确的，建议保留：

1. 当前 21 组 `Ours-Direct` 主结果先冻结，不直接覆盖；
2. `done / low_confidence / failed` 状态需要全部保留；
3. 不把 `Ours-AbsDirection-Direct` 改名为 `Ours-Direct`；
4. 对高覆盖但主公式 failed 的组合，优先从已有逐层 score 派生消融候选，不盲目重复跑同一个主公式；
5. Qwen2.5-VL-3B 需要单独检查 `empty_model_pred` 和有效样本覆盖率；
6. `MMKE-entity / Qwen2.5-VL-3B` 当前有效样本过少，不能进入可靠主结论。

---

## 3. 主要缺点与修改建议

### 3.1 缺点一：公式写法过于模糊

原报告中写法类似：

```text
score_main(l) = max(0, -cos_l) * stability_or_delta_factor
score_abs(l) = abs(cos_l) * stability_or_delta_factor
```

问题是 `stability_or_delta_factor` 没有严格定义，容易与当前正式手册不一致。

应改为明确使用：

```text
S_v_new_norm(l) * S_v_depth2(l)
```

其中：

```text
S_v_depth2(l) = ((l + 1) / L)^2
```

### 修改后公式

#### 1. 当前主方法：`Ours-Direct`

```text
S_ours(l)
= max(0, -S_v_cos(l))
  * S_v_new_norm(l)
  * S_v_depth2(l)
```

该结果是当前主实验结果，只冻结和保留，不用其他公式覆盖。

#### 2. 方向绝对值消融：`Ours-AbsDirection-Direct`

```text
S_absdir(l)
= abs(S_v_cos(l))
  * S_v_new_norm(l)
  * S_v_depth2(l)
```

用途：检验不区分正向/反向时，方向关系强度是否能给出更稳定候选层。

#### 3. 不考虑方向消融：`Ours-NoDirection-Direct`

```text
S_nodir(l)
= S_v_new_norm(l)
  * S_v_depth2(l)
```

用途：检验只依赖新知识视觉梯度强度和深度因子能否给出候选层。

#### 4. 软方向差异消融：`Ours-1MinusCos-Direct`

```text
S_1mcos(l)
= (1 - S_v_cos(l))
  * S_v_new_norm(l)
  * S_v_depth2(l)
```

用途：软化 `max(0, -cos)` 的硬负方向门控，使正向但方向差异较大的层仍有可能被排序。

---

### 3.2 缺点二：方法名还不够防混淆

原报告已经区分了 `Ours-Direct` 与 `Ours-AbsDirection-Direct`，这是正确的。但为了后续汇总时不混淆，建议输出表中新增字段：

```text
score_variant
```

推荐命名如下：

| Method | score_variant | 说明 |
|---|---|---|
| `Ours-Direct` | `conflict_main` | 当前严格负余弦冲突主公式 |
| `Ours-AbsDirection-Direct` | `abs_cos_ablation` | 方向绝对值消融 |
| `Ours-NoDirection-Direct` | `new_norm_depth_ablation` | 不考虑方向消融 |
| `Ours-1MinusCos-Direct` | `one_minus_cos_ablation` | 软方向差异消融 |

---

### 3.3 缺点三：Qwen 三组不能一刀切处理

原报告将 Qwen 三组都列为需要修复 `model_pred`，方向是对的，但优先级应分开。

| Dataset | 当前有效覆盖 | 建议处理 |
|---|---:|---|
| `EVQA-pilot500 / Qwen2.5-VL-3B` | 457/500，约 0.914 | coverage 较高，可先从已有 score 派生 ablation 候选，同时检查 empty_model_pred |
| `MMKE-visual / Qwen2.5-VL-3B` | 96/214，约 0.449 | 标记为 `low_confidence`，候选只作参考，需修 `model_pred` |
| `MMKE-entity / Qwen2.5-VL-3B` | 5/636，约 0.008 | 标记为 `invalid_low_coverage`，不进入主候选比较，必须先修 `model_pred` |

因此报告中 “Qwen 三组修复后补跑” 应改成：

1. EVQA/Qwen：可先派生消融候选，同时生成 empty report；
2. MMKE-visual/Qwen：低置信，修复后再重跑候选；
3. MMKE-entity/Qwen：当前无效，必须先解决 `model_pred` 覆盖问题。

---

### 3.4 缺点四：coverage 阈值不够，还要输出失败原因统计

报告建议 coverage 阈值：

```text
>= 0.80     可进入候选层比较
0.20-0.80   low_confidence
< 0.20      invalid
```

这个规则可以保留，但每个组合还应输出失败原因统计，否则无法判断是公式失败还是数据/模型 wrapper 失败。

建议新增以下字段：

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

其中 `failure_reason_major` 可取：

```text
no_valid_ours_direct_layer
empty_model_pred
invalid_low_coverage
missing_required_score_columns
empty_visual_span
zero_grad_or_nonfinite
unknown
```

---

### 3.5 缺点五：从已有 layer_scores 派生前缺少验收检查

原报告建议从已有 score 文件直接派生 `AbsDirection / NoDirection / 1MinusCos`，这是节省时间的正确做法，但必须先检查必要列是否存在。

每个组合的 layer score 文件必须至少包含：

```text
layer
S_v_cos
S_v_new_norm
S_v_depth2
S_v_zero_grad
S_v_new_nonzero_ratio
visual_token_start
visual_token_end
```

若缺少必要列，则不得派生候选层，应标记为：

```text
cannot_derive_ablation_missing_required_columns
```

同时输出缺失列列表：

```text
missing_required_columns
```

---

### 3.6 缺点六：阶段边界需要重新写清楚

原报告里提到“是否把方向无关版本纳入后续真实 50 epoch 训练评测”，这可以作为远期说明，但当前阶段不应安排真实训练。

当前阶段只做：

```text
1. 冻结 Ours-Direct 主结果；
2. 从已有 layer_scores 派生 Ours 系列不同指标候选层；
3. 修复或诊断 Qwen model_pred 覆盖问题；
4. 输出后续真实扫层可使用的候选层 top-k 文件。
```

当前阶段不做：

```text
1. 不做真实 50 epoch adapter 训练；
2. 不做 full-layer sweep；
3. 不补跑 Perturb-KL-Direct；
4. 不补跑 CMA-Direct；
5. 不补跑 LGA-Param-Direct；
6. 不把 ablation 结果覆盖 Ours-Direct 主结果。
```

---

## 4. 建议改成的执行流程

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

保留字段：

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

```text
不覆盖 done / low_confidence / failed
不把消融结果写回主结果
不删除 failed 组合
```

---

### Step 2：检查 layer_scores 可派生性

对每个 `dataset × model` 检查是否存在逐层 score 文件，且必要列齐全。

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

输出：

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

---

### Step 3：派生 Ours 系列消融候选

从已有 layer score 文件派生：

```text
Ours-AbsDirection-Direct
Ours-NoDirection-Direct
Ours-1MinusCos-Direct
```

候选层清洗规则：

```text
1. 删除 S_v_zero_grad=true 的层；
2. 删除 S_v_cos / S_v_new_norm / S_v_depth2 非有限值的层；
3. 删除 visual span 为空的层；
4. 去重并保留第一次出现；
5. 不自动用其他方法补齐；
6. 若不足 Top-K，保留实际数量并标记 insufficient_valid_layers。
```

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

---

### Step 4：重新计算 coverage 与状态

状态判定：

| Coverage | Status | 说明 |
|---:|---|---|
| `>= 0.80` | `done` | 可进入候选层比较 |
| `0.20 - 0.80` | `low_confidence` | 可作参考，不进入强结论 |
| `< 0.20` | `invalid_low_coverage` | 不进入主候选比较 |

特殊规则：

```text
MMKE-entity / Qwen2.5-VL-3B 当前强制标记为 invalid_low_coverage，直到 model_pred 覆盖修复。
```

---

### Step 5：Qwen 专项诊断与修复

先生成诊断报告，不直接进入真实训练。

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

---

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

---

## 5. 建议替换原报告中的关键文字

### 原报告中不建议保留的说法

```text
score_main(l) = max(0, -cos_l) * stability_or_delta_factor
score_abs(l) = abs(cos_l) * stability_or_delta_factor
```

### 建议替换为

```text
score_main(l)
= max(0, -S_v_cos(l)) * S_v_new_norm(l) * ((l + 1) / L)^2

score_abs(l)
= abs(S_v_cos(l)) * S_v_new_norm(l) * ((l + 1) / L)^2

score_nodir(l)
= S_v_new_norm(l) * ((l + 1) / L)^2

score_1mcos(l)
= (1 - S_v_cos(l)) * S_v_new_norm(l) * ((l + 1) / L)^2
```

---

## 6. 给 Codex 的简化执行指令

```text
请基于当前 Ours-Direct 结果目录执行修复，但只做 Ours 系列候选指标修复，不启动真实 adapter 训练，不运行 Perturb-KL、CMA 或 LGA。

具体要求：

1. 冻结当前 Ours-Direct 主结果，输出 frozen_ours_direct_main_candidates.csv/md。
2. 对每个 dataset × model 检查 layer_scores 是否可派生 ablation，必要列为 layer、S_v_cos、S_v_new_norm、S_v_depth2、S_v_zero_grad。
3. 从已有 layer_scores 派生三个消融方法：
   - Ours-AbsDirection-Direct: abs(S_v_cos) * S_v_new_norm * S_v_depth2
   - Ours-NoDirection-Direct: S_v_new_norm * S_v_depth2
   - Ours-1MinusCos-Direct: (1 - S_v_cos) * S_v_new_norm * S_v_depth2
4. 每个方法输出 raw_top3/raw_top5 和 clean_top3/clean_top5；clean 版本需删除 zero-grad、nonfinite、empty visual span 层。
5. coverage >=0.80 标记 done，0.20-0.80 标记 low_confidence，<0.20 标记 invalid_low_coverage。
6. MMKE-entity / Qwen2.5-VL-3B 当前不得进入主候选比较，标记 invalid_low_coverage。
7. 单独输出 Qwen model_pred 诊断报告，包括 empty_model_pred_count、coverage、样本 ID 对齐、prompt template、stop token、max_new_tokens 和 visual span 检查。
8. 主结果和消融结果必须分别成表，不允许用 ablation 覆盖 Ours-Direct 主结果。
```

---

## 7. 最终结论

`OursDirect_next_repair_report.md` 可以作为修复实验的基础，但必须先修改后执行。

最核心的改正意见是：

1. 将模糊的 `stability_or_delta_factor` 改成明确的 `S_v_new_norm × S_v_depth2`；
2. 将当前阶段限定为 `Ours-Direct` 不同指标出候选层的修复，不做真实扫层、不做 Perturb-KL、不做 CMA、不做 LGA；
3. 新增 `score_variant`、失败原因统计和 layer score 可派生性检查；
4. Qwen 三组分级处理，尤其 `MMKE-entity / Qwen2.5-VL-3B` 当前只能标记为无效低覆盖，不能进入可靠候选比较；
5. 主结果和消融结果必须严格分表，不能用方向无关结果覆盖 `Ours-Direct` 主结果。
