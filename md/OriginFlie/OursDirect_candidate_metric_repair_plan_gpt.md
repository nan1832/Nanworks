# Ours-Direct 不同指标候选层修复计划

> 适用范围：当前阶段只处理 `Ours-Direct` 视觉梯度指标产生候选层的问题。  
> 不在本阶段执行：`Perturb-KL-Direct`、`CMA-Direct`、新的真实 adapter 扫层训练。  
> 后续真实扫层实验：待 Ours 系列候选层稳定产出后，再统一并入候选层真实编辑验证流程。

---

## 1. 当前问题概述

根据已完成的 `Ours-Direct 21 组候选层实验`，当前主公式运行已经结束，整体状态为：

```text
Done: 8 / 21
Low-confidence: 3 / 21
Failed: 10 / 21
```

当前主公式为严格方向冲突版本：

\[
S_{ours}(l)
=
\max(0,-S_v^{cos}(l))
\cdot
S_v^{new\_norm}(l)
\cdot
\left(\frac{l+1}{L}\right)^2
\]

其中：

- \(S_v^{cos}(l)\)：old / `model_pred` 梯度与 new / `alt` 梯度在视觉 hidden states 上的余弦相似度；
- \(\max(0,-S_v^{cos}(l))\)：只保留 old/new 梯度方向冲突的层；
- \(S_v^{new\_norm}(l)\)：new / `alt` 对该层视觉表征的梯度强度；
- \(\left(\frac{l+1}{L}\right)^2\)：深度因子。

当前失败的主要原因不是训练或进程崩溃，而是：

```text
no_valid_ours_direct_layer
```

即经过严格负余弦方向约束与有效层清洗后，部分 `dataset × model` 组合没有合法候选层。

因此，当前问题应理解为：

> 严格负方向冲突约束在部分 VLM / 数据集组合中过于保守，导致无法稳定给出 Top-3 / Top-5 候选层。

---

## 2. 本阶段目标

本阶段只解决一个问题：

> 在不重新训练 adapter、不开展真实扫层的前提下，基于已有或重跑得到的 visual-gradient layer scores，为每个 `dataset × model` 组合稳定输出 Ours 系列候选层。

具体目标：

1. 保留当前严格方向版 `Ours-Direct` 主结果，不用其他公式覆盖；
2. 新增若干 Ours 消融指标，用于处理主公式失败或低置信问题；
3. 对 failed / low-confidence 组合给出可追踪、可复现、单独命名的候选层；
4. 修复 Qwen2.5-VL 的 `model_pred` / coverage 问题；
5. 形成统一的 `Ours` 系列候选层表，供后续真实 adapter sweep 使用。

本阶段不做：

```text
Perturb-KL-Direct
CMA-Direct
LGA-Param-Direct
新的 adapter training
真实扫层评价 Best@K / Regret@K / Hit@K
```

---

## 3. 方法命名原则

当前主方法名称保持不变：

```text
Ours-Direct
```

它只对应严格方向冲突版本：

\[
\max(0,-cos) \times new\_norm \times depth^2
\]

新增指标必须单独命名，不能覆盖或伪装为 `Ours-Direct`。

建议统一命名如下：

| 方法名 | 公式 | 定位 |
|---|---|---|
| `Ours-Direct` | \(\max(0,-cos) \times new\_norm \times depth^2\) | 当前主方法 |
| `Ours-AbsDirection-Direct` | \(|cos| \times new\_norm \times depth^2\) | 不区分同向/反向，只看方向关系强度 |
| `Ours-NoDirection-Direct` | \(new\_norm \times depth^2\) | 不考虑方向，只看新知识视觉梯度强度 |
| `Ours-1MinusCos-Direct` | \((1-cos) \times new\_norm \times depth^2\) | 软化负方向约束，不要求 cos 必须小于 0 |

其中：

- `Ours-Direct` 是主方法；
- 其余三个是消融 / 修复候选指标；
- 后续论文或实验表格中必须分列报告，不能混入主方法结果。

---

## 4. 新增候选指标公式

设第 \(l\) 层已有如下聚合指标：

\[
S_v^{cos}(l)
\]

\[
S_v^{new\_norm}(l)
\]

\[
D(l)
=
\left(\frac{l+1}{L}\right)^2
\]

### 4.1 当前主方法：`Ours-Direct`

\[
S_{conflict}(l)
=
\max(0,-S_v^{cos}(l))
\cdot
S_v^{new\_norm}(l)
\cdot
D(l)
\]

候选层：

\[
\mathcal C_{conflict,K}
=
TopK_l S_{conflict}(l)
\]

该方法只接受 old/new 视觉梯度方向冲突的层。

---

### 4.2 不区分方向正负：`Ours-AbsDirection-Direct`

\[
S_{absdir}(l)
=
|S_v^{cos}(l)|
\cdot
S_v^{new\_norm}(l)
\cdot
D(l)
\]

候选层：

\[
\mathcal C_{absdir,K}
=
TopK_l S_{absdir}(l)
\]

含义：

- 不要求 old/new 梯度必须反向；
- 只要求该层 old/new 梯度方向关系明显；
- 适合排查 `Ours-Direct` 因没有负 cos 层而失败的问题。

该指标对应文件 4 中视觉模态较稳定的 `M_abscos_x_newn` 思路，但保留当前 Ours 方法的深度因子。

---

### 4.3 不考虑方向：`Ours-NoDirection-Direct`

\[
S_{nodir}(l)
=
S_v^{new\_norm}(l)
\cdot
D(l)
\]

候选层：

\[
\mathcal C_{nodir,K}
=
TopK_l S_{nodir}(l)
\]

含义：

- 完全不使用 old/new 方向关系；
- 只判断该层是否对 new / `alt` 有足够强的视觉梯度；
- 用于回答：“即使没有方向冲突，仅新知识梯度强度是否足以预测候选编辑层？”

这是当前最稳健的 fallback 消融，但不能替代主方法。

---

### 4.4 软化冲突方向：`Ours-1MinusCos-Direct`

\[
S_{1-cos}(l)
=
(1-S_v^{cos}(l))
\cdot
S_v^{new\_norm}(l)
\cdot
D(l)
\]

候选层：

\[
\mathcal C_{1-cos,K}
=
TopK_l S_{1-cos}(l)
\]

含义：

- 当 cos 越小，分数越大；
- 不要求 cos 必须为负；
- 相比 `max(0,-cos)` 更连续、更不容易产生空候选；
- 可视为 `Ours-Direct` 的软门控版本。

---

## 5. 状态分类与处理规则

### 5.1 `done` 组合

对于当前 `Ours-Direct` 已经完成且 coverage 正常的组合：

```text
status = done
coverage >= 0.8
Top-3 / Top-5 非空
```

处理方式：

1. 保留 `Ours-Direct` 主候选层；
2. 同时计算三个消融指标；
3. 不用消融结果覆盖主结果；
4. 后续只在分析中比较这些指标的候选层差异。

---

### 5.2 `failed` 但 coverage 高的组合

例如：

```text
coverage >= 0.8
status = failed
failure_reason = no_valid_ours_direct_layer
```

这类组合说明样本和梯度本身多数可用，但严格负方向约束无法产出候选。

处理方式：

1. 不重复跑同一个 `Ours-Direct` 主公式；
2. 从已有 layer scores 直接派生：
   - `Ours-AbsDirection-Direct`
   - `Ours-NoDirection-Direct`
   - `Ours-1MinusCos-Direct`
3. 将这些结果标记为：

```text
ablation_candidate = true
main_ours_status = failed
```

4. 进入后续候选层池时必须保留方法名，不能写成 `Ours-Direct repaired`。

---

### 5.3 `low_confidence` 组合

例如：

```text
0.2 <= coverage < 0.8
```

处理方式：

1. 保留已有 `Ours-Direct` 候选，但标记低置信；
2. 同时计算三个消融指标；
3. 后续报告时单独列出 low-confidence，不进入主结论平均；
4. 如果 coverage 过低，应优先检查数据映射或 `model_pred`。

---

### 5.4 coverage 极低组合

例如：

```text
coverage < 0.2
```

特别是：

```text
MMKE-entity × Qwen2.5-VL
valid = 5 / 636
```

处理方式：

1. 不生成正式候选层；
2. 不使用消融公式强行补候选；
3. 标记为：

```text
status = invalid_due_to_low_coverage
```

4. 必须先修复 `model_pred` / 样本映射 / 解码配置。

---

## 6. Qwen2.5-VL 专项修复计划

Qwen2.5-VL 当前主要问题是 `empty_model_pred` 和 coverage 过低。

### 6.1 修复目标

```text
EVQA-pilot500: coverage 尽量恢复到 >= 0.8
MMKE-visual: coverage 尽量恢复到 >= 0.8
MMKE-entity: 先从 5/636 修复到可分析水平
```

### 6.2 处理步骤

1. 单独重跑 Qwen2.5-VL 的 `model_pred` 生成；
2. 固定图像分辨率或视觉 token budget；
3. 检查 prompt template 是否与模型 processor 匹配；
4. 放宽 `max_new_tokens`，避免空输出；
5. 检查 stop tokens 是否过早截断；
6. 输出诊断文件：

```text
qwen_model_pred_empty_report.csv
qwen_model_pred_mapping_report.json
```

7. 重新统计：

```text
total_cases
nonempty_model_pred_cases
mapped_cases
missing_cases
empty_model_pred_cases
coverage
```

8. 只有 coverage 达到最低阈值后，才重跑 Ours 系列视觉梯度指标。

### 6.3 Qwen 暂停纳入规则

在修复前，以下组合不进入主结论：

```text
MMKE-entity × Qwen2.5-VL
```

若 EVQA / MMKE-visual 的 Qwen coverage 仍低于 0.8，也应标记为 low-confidence 或 invalid，不参与宏平均主结论。

---

## 7. 候选层生成流程

### Step 1：检查已有 layer scores

每个组合检查是否存在：

```text
S_v_cos
S_v_new_norm
S_v_depth2
S_v_zero_grad
visual_token_start/end
n_valid
n_total
```

若这些字段齐全，则无需重新跑模型，可直接派生新增指标。

---

### Step 2：计算四类 Ours 分数

对每层计算：

```text
S_conflict = max(0, -S_v_cos) * S_v_new_norm * S_v_depth2
S_absdir   = abs(S_v_cos) * S_v_new_norm * S_v_depth2
S_nodir    = S_v_new_norm * S_v_depth2
S_1mcos    = (1 - S_v_cos) * S_v_new_norm * S_v_depth2
```

---

### Step 3：有效层过滤

以下层不得进入候选：

```text
S_v_zero_grad = true
S_v_new_norm is nonfinite
S_v_cos is nonfinite
visual_token_start/end empty
layer index out of range
```

对于 `S_conflict`，如果全部层分数为 0，则：

```text
Ours-Direct status = failed
failure_reason = no_valid_negative_cosine_layer
```

对于其他消融指标，只要有效层存在即可排序。

---

### Step 4：输出 Top-K

每个方法输出：

```text
Top-3
Top-5
full layer ranking
full layer scores
status
failure_reason
coverage
```

Top-K 排序规则：

1. 分数从大到小；
2. 分数相同则优先 `S_v_new_norm` 更大；
3. 仍相同则优先层号小；
4. 不自动补齐失败方法的候选层。

---

## 8. 输出文件规范

建议新增汇总文件：

```text
ours_direct_metric_ablation_candidates_summary.csv
ours_direct_metric_ablation_candidates_summary.md
```

### 8.1 CSV 字段

```text
dataset
model
method
formula
layer
score
rank
in_top3
in_top5
S_v_cos
S_v_new_norm
S_v_depth2
S_v_zero_grad
valid_samples
total_samples
coverage
main_ours_status
ablation_candidate
status
failure_reason
source_layer_scores_file
config_hash
```

### 8.2 Markdown 汇总表字段

```text
Dataset
Model
Method
Top-3
Top-5
Status
Valid
Total
Coverage
Note
```

### 8.3 推荐状态枚举

```text
done
failed
low_confidence
invalid_due_to_low_coverage
invalid_due_to_empty_model_pred
computed_from_existing_layer_scores
requires_qwen_model_pred_repair
```

---

## 9. 后续候选层池构建规则

本阶段只构建 Ours 系列候选层池，不做真实扫层。

每个 `dataset × model` 的 Ours 系列候选层池：

\[
\mathcal U_{ours}
=
\mathcal C_{conflict,5}
\cup
\mathcal C_{absdir,5}
\cup
\mathcal C_{nodir,5}
\cup
\mathcal C_{1-cos,5}
\]

若层数过多，按以下优先级保留：

1. `Ours-Direct` 主方法 Top-5；
2. `Ours-AbsDirection-Direct` Top-3；
3. `Ours-NoDirection-Direct` Top-3；
4. `Ours-1MinusCos-Direct` Top-3；
5. 对 InstructBLIP 可额外保留中层保护层。

当前阶段只输出候选池，不启动训练。

---

## 10. InstructBLIP 特别处理

文件 4 的历史相关性分析提示：InstructBLIP visual 是系统性困难案例。可能原因是 instruction-aware Q-Former 让 visual token 在浅层已经高度对齐编辑方向，但真实编辑效果可能需要 decoder 处理中层后才稳定。

因此，InstructBLIP 不建议只依赖严格冲突方向指标。

建议额外输出：

```text
InstructBLIP-MidProtect-Direct
```

保护层建议：

```text
L12,L13,L14
```

该保护层不是 Ours 主公式结果，只作为后续真实扫层的风险控制候选层。

输出时标记：

```text
method = InstructBLIP-MidProtect-Direct
source = architecture_specific_protection
ablation_candidate = true
```

---

## 11. 当前阶段不做的事项

以下内容放到后续真实扫层阶段，不在本阶段执行：

```text
1. 不补跑 Perturb-KL-Direct。
2. 不补跑 CMA-Direct。
3. 不补跑 LGA-Param-Direct。
4. 不训练新的 adapter。
5. 不计算 Best@K / Regret@K / Hit@K。
6. 不把 abs-direction 候选直接写成 Ours-Direct 主结果。
7. 不用消融指标覆盖 failed 的主方法状态。
```

本阶段的边界是：

> 只修复 Ours-Direct 不同视觉梯度指标能否稳定产生候选层的问题。

---

## 12. 最小验收清单

完成本阶段前必须检查：

```text
[ ] 当前 Ours-Direct 主结果已冻结，不被覆盖。
[ ] 新增 Ours-AbsDirection-Direct 候选层。
[ ] 新增 Ours-NoDirection-Direct 候选层。
[ ] 新增 Ours-1MinusCos-Direct 候选层。
[ ] 每个新增方法都有独立 method name。
[ ] 每个方法均输出 Top-3 / Top-5 / full ranking。
[ ] failed 主结果仍保留 failed，不被消融结果替代。
[ ] low-confidence 结果单独标记，不进入主结论平均。
[ ] Qwen2.5-VL 的 empty_model_pred 已单独统计。
[ ] MMKE-entity × Qwen2.5-VL 在 coverage 修复前不进入主结论。
[ ] 所有候选层使用同一层编号语义：adapter 接在 decoder block l 输出后。
[ ] 本阶段没有启动 Perturb-KL、CMA 或真实 adapter sweep。
```

---

## 13. 建议报告表述

可以在实验报告中这样写：

```text
当前 Ours-Direct 主公式采用严格 old/new 视觉梯度负余弦冲突约束，即 max(0, -cos) × new_norm × depth²。该设置能够在部分模型与数据集组合上给出候选层，但在若干组合中由于没有满足负方向约束的有效层而无法产生 Top-K。为判断失败是否来自视觉梯度信号缺失，还是来自方向约束过强，我们保留原始 Ours-Direct 主结果，并新增 AbsDirection、NoDirection 和 1MinusCos 三个消融指标。三者仅用于候选层修复与后续验证，不覆盖主方法状态，也不与主方法混名。
```

---

## 14. 执行优先级

建议按以下顺序推进：

```text
P0: 冻结当前 Ours-Direct 主结果和失败状态。
P1: 从已有 layer_scores 派生 AbsDirection / NoDirection / 1MinusCos 候选。
P2: 生成 ours_direct_metric_ablation_candidates_summary.csv/md。
P3: 单独修复 Qwen2.5-VL model_pred 与 coverage。
P4: 对修复后的 Qwen 重新生成 Ours 系列候选。
P5: 汇总 Ours 系列候选层池，等待后续真实扫层实验统一验证。
```

