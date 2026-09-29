# ZN Visual Gradient Prediction 实验手册（7 基础公式 + 4 个 Ours 系列指标｜视觉候选层计算修复版）

本手册用于指导后续 **不同模型、不同数据集** 的视觉梯度层定位实验。核心目标是：在不训练 adapter、不改模型权重的前提下，通过 Virtual Delta-H 视觉梯度计算每个候选层的 old/new answer 梯度关系，并基于 **视觉 token hidden-state gradients** 生成候选 adapter 插入层。

本版本的关键修改是：

1. 不再把严格负方向公式 `max(0, -cos) × new_norm × depth²` 固定为唯一主公式；
2. 保留 7 个基础视觉梯度候选公式，用于完整比较与相关性分析；
3. 额外加入 4 个 Ours 系列深度加权指标，用于当前 Ours-Direct 修复实验；
4. 后续根据真实 adapter 扫层结果，在 7 个基础公式与 4 个 Ours 系列指标中选择效果最好的候选层定位公式；
5. 如果这些公式都不能稳定预测真实编辑层，再基于真实扫层结果与视觉梯度长表重新做相关性分析，归纳新的视觉候选公式；
6. 本手册只做 **视觉表征编辑候选层定位**，不做文本表征候选层定位，不输出文本 token hidden-state 候选层排序；
7. 在 `layer CSV` 中额外保留 `S_v_neg_cos`、`S_v_depth2`、`S_strict_negcos_depth2` 三个历史对照字段，并统一标记为 `diagnostic only`，用于排查和论文对照，不作为唯一主公式；
8. 吸收 `OursDirect_next_repair_report.md` 与补充版中的修复经验：严格负余弦门控可能导致 `no_valid_ours_direct_layer`，因此本手册要求同时输出 7 个基础公式与 4 个 Ours 系列指标，禁止用任一公式覆盖其他公式；
9. 增加 layer score 可派生性检查、coverage 状态判定、Qwen2.5-VL `model_pred` 覆盖诊断、失败原因统计与候选层池输出规范；
10. 本阶段只用于视觉表征候选层计算与候选层池整理，不启动真实 adapter 训练，不补跑 Perturb-KL、CMA 或 LGA。

当前公式集合分为两组：

```text
A. 7 个基础视觉梯度候选公式：
   M_dot
   M_cos
   M_new_norm
   M_pos_ratio
   M_conflict
   M_newn_x_1mcos
   M_abscos_x_newn

B. 4 个 Ours 系列深度加权候选指标：
   Ours-Direct-Conflict
   Ours-AbsDirection-Direct
   Ours-NoDirection-Direct
   Ours-1MinusCos-Direct
```

其中 `Ours-Direct-Conflict` 等价于旧版严格负方向公式，但在本手册中它只是 **Ours 系列候选指标之一**，不再被写成唯一主方法。

---

## 1. 任务定义

给定一个 VLM、一个编辑数据集和一组候选层，计算每层视觉 token hidden state 上的旧知识梯度与新知识梯度。

对第 `i` 个样本、第 `l` 层：

```text
L_old^i = mean_token_NLL(y_old_i | image_i, prompt_i)
L_new^i = mean_token_NLL(y_new_i | image_i, prompt_i)

g_old_v^{i,l} = ∇_{Δ_v^l} L_old^i
g_new_v^{i,l} = ∇_{Δ_v^l} L_new^i
```

其中：

- `Δ_v^l` 是插入在第 `l` 层视觉 token hidden state 上的零扰动；
- 只对 `Δ_v^l` 求梯度，不更新模型参数；
- `L_old` 和 `L_new` 都只在 answer token 上算平均 NLL；
- prompt token、visual token、padding token 不参与 loss；
- 每层只根据 visual token hidden-state gradients 计算候选指标；
- 本手册不计算文本 token hidden-state 候选层排序。

---

## 2. 字段映射规范

每个数据集必须先明确旧知识和新知识字段，不能让脚本自动猜。

| 数据集/任务 | prompt 字段 | image 字段 | 旧知识字段 | 新知识字段 |
|---|---|---|---|---|
| E-VQA proxy500/pilot500 | `src` | `image` | `model_pred` | `alt` |
| E-VQA full | `src` | `image` | `model_pred` | `alt` |
| Bridge request-only | `request.prompt` | `request.image` | old answers file | `request.target_new` |
| MMKE-visual | 按 manifest 显式记录 | 按 manifest 显式记录 | `model_pred` | `alt` / target |
| MMKE-entity | 按 manifest 显式记录 | 按 manifest 显式记录 | `model_pred` | `alt` / target |
| 其他数据集 | 必须显式记录 | 必须显式记录 | 必须显式记录 | 必须显式记录 |

旧知识字段默认使用当前冻结模型确定性解码得到的 `model_pred`。如果某数据集已有 `pred` 字段，且确认它来自同一个冻结模型、同一输入模板和同一解码配置，可另做 `AltPred` 附加分析，但必须单独命名、单独成表，不得混入 `model_pred` 主口径。

硬性检查：

```text
total_cases == selected_cases
mapped_cases == selected_cases
missing_cases == []
```

如果同一 `image_id` 对应多个问题，`old_answers.jsonl` 必须保留 `question` 字段，让 loader 按 question 匹配，而不是只按 image_id 取第一条。

---

## 3. 模型与层范围

不同模型的视觉 token scope 和候选层路径不同，必须在实验配置里写清楚。

| 模型 | 候选层示例 | 视觉 token scope | hook 位置 |
|---|---|---|---|
| BLIP2-OPT | OPT decoder `0-31` | Q-Former 输出投影后的 visual prefix/query tokens | `language_model.model.decoder.layers.{l}` |
| LLaVA | LLM decoder `0-31` 或实际层数 | projector 输出后插入 LLM 的 image tokens | LLM decoder block |
| InstructBLIP | LLM decoder 层 | Q-Former/visual prefix tokens | LLM decoder block |
| Qwen2.5-VL | LLM decoder 或 merger 后层 | image/video tokens 或 visual prefix | 以模型 tokenizer/processor 映射为准 |
| PaliGemma | Gemma decoder 层 | image tokens / visual prefix | language decoder block |
| SmolVLM | language decoder 层 | image tokens / visual prefix | language decoder block |

原则：

- `visual_token_start`、`visual_token_end` 必须由模型实际输入映射读取，不手写固定值；
- candidate layer `l` 统一表示 adapter 接在 decoder block `l` 输出之后、block `l+1` 之前；
- 不允许在视觉 token 失败时 fallback 到 all prompt tokens 后仍写入视觉主表；
- 不输出文本表征候选层排序。

---

## 4. 计算流程

### Step 1：加载模型并冻结

```python
model.eval()
for p in model.parameters():
    p.requires_grad_(False)
```

必须记录：

```text
base_requires_grad_params = 0
adapter_used = false
optimizer_used = false
gradient_target = virtual_delta_h_at_layer_visual_hidden_state
```

### Step 2：遍历候选层

每次只在一个候选层 `l` 插入零扰动：

```text
layers = 0-31  # 示例，按模型实际层数调整
```

### Step 3：插入视觉零扰动

伪代码：

```python
h = hidden_states
h_v = h[:, visual_start:visual_end, :]
delta_v = torch.zeros_like(h_v, requires_grad=True)
h[:, visual_start:visual_end, :] = h_v + delta_v
```

实现要求：

- 不要原地破坏 autograd graph；
- 优先使用项目已有 hook 写法；
- 每个 old/new loss 推荐各跑一次 forward，避免 `retain_graph` 引起混乱；
- 每层每个样本必须记录 visual token 区间是否有效。

### Step 4：分别计算 old/new 梯度

```python
L_old = answer_mean_nll(model, image, prompt, old_answer)
g_old_v = autograd.grad(L_old, delta_v)

L_new = answer_mean_nll(model, image, prompt, target_new)
g_new_v = autograd.grad(L_new, delta_v)
```

禁止事项：

```text
不调用 optimizer.step()
不保存 adapter checkpoint
不改变模型权重
不把 old/new 拼在一次 loss 里混算
不输出文本候选层排序
```

---

## 5. 视觉梯度原始指标定义

每层聚合输出视觉原始指标。设：

```text
old = flat(g_old_v^{i,l})
new = flat(g_new_v^{i,l})
dot_i = sum(old * new)
old_norm_i = ||old||_2
new_norm_i = ||new||_2
joint_i = old_norm_i * new_norm_i
numel_i = number_of_elements(old)
eps = 1e-8
```

每个样本的余弦：

```text
cos_i = dot_i / (joint_i + eps)
```

层级聚合指标：

| 指标 | 公式/定义 | 用途 |
|---|---|---|
| `S_v_dot` | `mean_i dot_i` | old/new 视觉梯度点积 |
| `S_v_conflict` | `mean_i (-dot_i)` | dot 反向冲突强度 |
| `S_v_dot_per_dim` | `mean_i dot_i / numel_i` | 维度归一化点积 |
| `S_v_cos` | `mean_i cos_i` | old/new 视觉梯度方向相似度 |
| `S_v_old_norm` | `mean_i old_norm_i` | 旧知识视觉梯度强度 |
| `S_v_new_norm` | `mean_i new_norm_i` | 新知识视觉梯度强度 |
| `S_v_joint_norm` | `mean_i joint_i` | old/new 共同梯度强度 |
| `S_v_positive_ratio` | `count(dot_i > 0) / n` | 方向一致样本比例 |
| `S_v_zero_grad` | `S_v_old_norm < eps or S_v_new_norm < eps` | 是否近似零梯度层 |
| `S_v_old_nonzero_ratio` | `mean_i mean(abs(old) > eps)` | 旧知识梯度非零元素比例 |
| `S_v_new_nonzero_ratio` | `mean_i mean(abs(new) > eps)` | 新知识梯度非零元素比例 |
| `median_v_dot` | `median_i dot_i` | 样本级 dot 中位数，抗异常样本 |

这些原始指标必须全部保留，因为 7 个基础候选公式和 4 个 Ours 系列指标都由它们派生。

### 5.1 历史对照诊断列（diagnostic only）

为保留旧版严格负方向公式的可追溯性，并方便后续论文写作、失败排查和与旧实验结果对齐，`layer CSV` 必须额外保留以下 3 个诊断列：

| 字段 | 公式 | 标记 | 用途 |
|---|---|---|---|
| `S_v_neg_cos` | `max(0, -S_v_cos)` | diagnostic only | 旧版严格负余弦门控项，记录该层是否存在 old/new 方向冲突信号 |
| `S_v_depth2` | `((l + 1) / L)^2` | diagnostic only | 旧版深度加权项，也被 4 个 Ours 系列候选指标复用 |
| `S_strict_negcos_depth2` | `S_v_neg_cos * S_v_new_norm * S_v_depth2` | diagnostic only | 旧版严格负方向深度加权得分的历史对照列 |

说明：

```text
S_strict_negcos_depth2(l)
= max(0, -S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)
```

它与 `Ours-Direct-Conflict` 的数值等价，但二者在表中的含义不同：

```text
S_strict_negcos_depth2 = 历史对照 / diagnostic only 字段
Ours-Direct-Conflict = 4 个 Ours 系列候选指标之一
```

因此，`S_strict_negcos_depth2` 不单独作为主公式，也不得被写成唯一主方法；如果需要按严格负方向公式生成候选层，应使用 `Ours-Direct-Conflict` 这一显式方法名。

---

## 6. 七个基础视觉表征候选公式

本节公式来自历史 CrossModel LGA 视觉指标分析。它们不加入深度因子，主要用于基础比较、跨模型相关性分析和候选层诊断。

设：

```text
M_dot(l) = S_v_dot(l)
M_cos(l) = S_v_cos(l)
M_new_norm(l) = S_v_new_norm(l)
M_pos_ratio(l) = S_v_positive_ratio(l)
```

### 6.1 `M_dot`

```text
M_dot(l) = mean_i <g_old_v^{i,l}, g_new_v^{i,l}>
```

候选层：

```text
candidate_layers = TopK_l M_dot(l)
```

含义：选择 old/new 视觉梯度点积较大的层。该指标强调方向一致与共同梯度强度。

### 6.2 `M_cos`

```text
M_cos(l) = mean_i cos(g_old_v^{i,l}, g_new_v^{i,l})
```

候选层：

```text
candidate_layers = TopK_l M_cos(l)
```

含义：选择 old/new 视觉梯度方向相似度较高的层。该指标不直接考虑梯度范数大小。

### 6.3 `M_new_norm`

```text
M_new_norm(l) = mean_i ||g_new_v^{i,l}||_2
```

候选层：

```text
candidate_layers = TopK_l M_new_norm(l)
```

含义：选择新知识视觉梯度强度较大的层，用于检验“仅新知识写入强度是否足以预测编辑层”。

### 6.4 `M_pos_ratio`

```text
M_pos_ratio(l) = count_i(dot_i > 0) / n
```

候选层：

```text
candidate_layers = TopK_l M_pos_ratio(l)
```

含义：选择 old/new 视觉梯度方向一致样本比例较高的层。

### 6.5 `M_conflict`

```text
M_conflict(l) = -M_dot(l)
```

候选层：

```text
candidate_layers = TopK_l M_conflict(l)
```

含义：选择 old/new 视觉梯度点积更负的层，用于检验反向冲突是否更适合替换旧答案。

### 6.6 `M_newn_x_1mcos`

```text
M_newn_x_1mcos(l) = M_new_norm(l) * (1 - M_cos(l))
```

候选层：

```text
candidate_layers = TopK_l M_newn_x_1mcos(l)
```

含义：同时考虑新知识视觉梯度强度与 old/new 方向差异。相比严格负余弦门控，该公式不会因为 `cos >= 0` 直接清零。

### 6.7 `M_abscos_x_newn`

```text
M_abscos_x_newn(l) = abs(M_cos(l)) * M_new_norm(l)
```

候选层：

```text
candidate_layers = TopK_l M_abscos_x_newn(l)
```

含义：同时考虑方向关系强度与新知识视觉梯度强度，但不区分同向或反向。

---

## 7. 四个 Ours 系列深度加权候选指标

本节把当前修复实验需要的 4 个 Ours 系列指标加入手册。它们都基于 `S_v_cos`、`S_v_new_norm` 和深度因子构造。

定义深度因子：

```text
S_v_depth2(l) = ((l + 1) / L)^2
```

这里的 `L` 表示合法候选层数量；若层编号为 `0,...,L-1`，则使用 `(l+1)/L`，避免第 0 层深度因子为 0。

同时保存诊断门控项：

```text
S_v_neg_cos(l) = max(0, -S_v_cos(l))
S_strict_negcos_depth2(l) = S_v_neg_cos(l) * S_v_new_norm(l) * S_v_depth2(l)
```

这两个诊断字段仅用于历史对照和排查；候选层排序仍通过下列 4 个显式 `Ours-*` 方法名分别输出。

### 7.1 `Ours-Direct-Conflict`

公式：

```text
S_ours_conflict(l)
= max(0, -S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)
```

候选层：

```text
candidate_layers = TopK_l S_ours_conflict(l)
```

作用：保留旧版严格负方向冲突思想，只选择 old/new 视觉梯度方向存在负余弦冲突的层。

注意：在本手册中，它不再是唯一主方法，只是 4 个 Ours 系列候选指标之一。

### 7.2 `Ours-AbsDirection-Direct`

公式：

```text
S_ours_absdir(l)
= abs(S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)
```

候选层：

```text
candidate_layers = TopK_l S_ours_absdir(l)
```

作用：不区分 old/new 梯度同向还是反向，只看方向关系强度与新知识梯度强度。

该指标可以看作 `M_abscos_x_newn` 加入深度因子的 Ours 版本。

### 7.3 `Ours-NoDirection-Direct`

公式：

```text
S_ours_nodir(l)
= S_v_new_norm(l) * S_v_depth2(l)
```

候选层：

```text
candidate_layers = TopK_l S_ours_nodir(l)
```

作用：完全不考虑方向关系，只看新知识视觉梯度强度与深度因子。

该指标可以看作 `M_new_norm` 加入深度因子的 Ours 版本。

### 7.4 `Ours-1MinusCos-Direct`

公式：

```text
S_ours_1mcos(l)
= (1 - S_v_cos(l)) * S_v_new_norm(l) * S_v_depth2(l)
```

候选层：

```text
candidate_layers = TopK_l S_ours_1mcos(l)
```

作用：软化负方向约束，不要求 `S_v_cos(l)` 必须小于 0。只要 old/new 方向差异较大，该层就可以获得较高分数。

该指标可以看作 `M_newn_x_1mcos` 加入深度因子的 Ours 版本。

### 7.5 四个 Ours 指标的实验地位

当前阶段不能预设 4 个 Ours 指标中哪个最好，也不能把 `Ours-Direct-Conflict` 写成唯一主公式。必须全部输出 Top-3 / Top-5，并在真实扫层完成后比较：

```text
Top1Perf
Mean@K
Best@K
Regret@K
Hit@K
Spearman / Kendall / NDCG@K（真实扫层覆盖足够时）
```

---

## 8. 输出文件规范

每次实验必须输出以下文件：

```text
sample_virtual_delta_h_scores.jsonl
visual_gradient_layer_scores.csv
visual_candidate_formula_rankings.csv
visual_candidate_layers_topk.csv
visual_candidate_layers_topk.md
visual_candidate_layers_topk.json
old_answer_mapping_report.json
run_config.json
summary.md

# 修复/诊断阶段额外输出
visual_layer_score_derivability_report.csv
visual_formula_failure_reason_summary.csv
qwen_model_pred_empty_report.csv
qwen_model_pred_mapping_report.json
qwen_visual_gradient_coverage_recheck.md
visual_candidate_pool_union.csv
visual_candidate_pool_union.md
```

### 8.1 sample JSONL

每个样本、每层一行，必须包含：

```text
case_id
image_id
layer
layer_path
old_answer
target_new
old_loss
new_loss
visual_token_start
visual_token_end
answer_loss_position_count
s_v_dot
s_v_conflict
s_v_dot_per_dim
s_v_cos
v_old_norm
v_new_norm
v_joint_norm
v_old_nonzero_ratio
v_new_nonzero_ratio
```

### 8.2 layer CSV

每层一行，必须包含视觉聚合指标、7 个基础候选公式得分、4 个 Ours 系列指标得分，以及 3 个 `diagnostic only` 历史对照字段：

```text
dataset
model
layer
n_request
valid_samples
total_samples
coverage
S_v_dot
S_v_conflict
S_v_dot_per_dim
S_v_cos
S_v_old_norm
S_v_new_norm
S_v_joint_norm
S_v_positive_ratio
S_v_zero_grad
S_v_old_nonzero_ratio
S_v_new_nonzero_ratio
median_v_dot
S_v_neg_cos                  # diagnostic only
S_v_depth2                   # diagnostic only / reused by Ours metrics
S_strict_negcos_depth2        # diagnostic only
M_dot
M_cos
M_new_norm
M_pos_ratio
M_conflict
M_newn_x_1mcos
M_abscos_x_newn
S_ours_conflict
S_ours_absdir
S_ours_nodir
S_ours_1mcos
visual_token_start_valid
visual_token_end_valid
status
failure_reason
empty_model_pred_count
missing_image_count
empty_visual_span_count
zero_grad_layer_count
nonfinite_score_layer_count
no_negative_cos_layer_count
failure_reason_major
source_score_file
config_hash
```

其中：

```text
S_v_neg_cos
S_v_depth2
S_strict_negcos_depth2
```

必须在 `layer CSV` 中保留并标记为 `diagnostic only`。这三列用于历史对照和排查，不单独作为主候选公式；严格负方向候选层应通过 `Ours-Direct-Conflict` 方法列输出。

不得输出 `S_t_*` 文本表征候选层字段。

### 8.3 Top-K CSV / JSON

每个基础公式和 Ours 系列指标都必须输出 Top-3 与 Top-5：

```text
dataset
model
formula_group          # base_7_visual 或 ours_4_depth_weighted
formula_name
rank_metric
top_k
rank
layer
score
raw_candidate_layers
clean_candidate_layers
valid_samples
total_samples
coverage
status
failure_reason
source_layer_scores_file
```

推荐同时保存：

```text
visual_candidate_formula_rankings.csv
visual_candidate_layers_topk.csv
visual_candidate_layers_topk.md
visual_candidate_layers_topk.json
```

### 8.4 mapping report

必须检查：

```text
total_cases
mapped_cases
missing_cases
duplicate_image_ids
old_answer_source
empty_model_pred_count
```

合格条件：

```text
mapped_cases == total_cases
missing_cases == []
```

---

## 9. 候选层排序规则

### 9.1 并行排序

对每个 `dataset × model` 组合，必须同时计算以下 11 个视觉候选得分的完整层排序：

```text
# 7 个基础视觉候选公式
M_dot
M_cos
M_new_norm
M_pos_ratio
M_conflict
M_newn_x_1mcos
M_abscos_x_newn

# 4 个 Ours 系列深度加权指标
Ours-Direct-Conflict
Ours-AbsDirection-Direct
Ours-NoDirection-Direct
Ours-1MinusCos-Direct
```

每个公式分别输出：

```text
Top-1
Top-3
Top-5
full layer ranking
full layer scores
```

当前阶段不得预先声明某个公式为唯一主公式。真实扫层完成前，只能称为“候选公式”或“候选指标”。

### 9.2 有效层过滤

以下层不得进入任何候选公式的 clean Top-K：

```text
S_v_zero_grad = true
S_v_new_norm is nonfinite
S_v_cos is nonfinite
visual_token_start/end empty
layer index out of range
```

如果某个公式清洗后无有效层，该“数据集 × 模型 × 公式”组合标记为：

```text
status = unavailable
failure_reason = no_valid_visual_gradient_layer
```

对于 `Ours-Direct-Conflict`，如果所有有效层的 `max(0, -S_v_cos)` 都为 0，则标记：

```text
status = failed
failure_reason = no_valid_negative_cosine_layer
```

但这不影响其他 10 个公式继续输出候选层。

### 9.3 排序方向与 tie-break

所有候选公式默认按分数从大到小排序：

```text
rank = descending(score)
```

并列时使用：

```text
1. S_v_new_norm 更大者优先；
2. coverage 更高者优先；
3. 仍并列时层号小者优先。
```

### 9.4 raw 与 clean 候选层

每个公式都必须保存：

```text
raw_top3
raw_top5
clean_top3
clean_top5
removed_layers
remove_reason
```

清洗只删除无效层，不允许用其他公式或其他方法补齐。

---

## 10. 真实扫层后的公式选择规则

本手册的核心不是预设哪个公式最好，而是通过真实编辑扫层确定哪个公式最能预测视觉编辑层。

### 10.1 真实编辑性能

对每个已完成真实 adapter 训练和评测的层，使用：

```text
Average = (Rel + T-Gen + M-Gen + T-Loc + M-Loc) / 5
```

如果某个数据集官方 Overall 定义不同，应记录官方公式并单独说明。

### 10.2 每个公式的定位评价

对每个公式 `m` 和每个 `dataset × model`：

```text
Top1Perf(m) = Average(layer ranked 1 by m)
Mean@K(m) = mean Average(layers in TopK by m)
Best@K(m) = max Average(layers in TopK by m)
Regret@K(m) = OracleAverage - Best@K(m)
Hit@K(m) = 1[oracle layer in TopK by m]
```

其中 Oracle 必须注明来源：

```text
Candidate-union Oracle
Full-layer Oracle
Measured-layer Oracle
```

当前如果只完成部分候选层扫层，只能使用 `Measured-layer Oracle`，不能称为全局最优层。

### 10.3 排序相关性

当真实扫层覆盖足够多层时，计算：

```text
Spearman rho
Kendall tau
NDCG@K
```

建议条件：

```text
measured_layers >= 8
且覆盖低层 / 中层 / 高层至少两个区间
```

否则只报告 Top-K 性能，不强行解释排序相关性。

### 10.4 选择最终视觉候选公式

选择规则：

1. 优先看跨 `dataset × model` macro-average 的 `Best@3 / Best@5`；
2. 同时报告 `Mean@K`，避免某公式只靠单个偶然高层取胜；
3. 用 `Hit@K` 判断是否命中当前 oracle；
4. 若覆盖层足够，用 Spearman / Kendall 验证排序趋势；
5. 若 7 个基础公式和 4 个 Ours 系列指标都表现不稳定，则基于真实扫层结果和视觉梯度长表重新做相关性分析，设计新公式，并另起方法名，不能事后覆盖原始公式。

可能的新公式命名示例：

```text
Ours-VisualCorr-Direct-v1
Ours-VisualNormCalibrated-Direct
Ours-VisualDepthAdjusted-Direct
```

---

## 11. 候选层池构建规则

本阶段只构建视觉公式候选层池，不做真实扫层。

每个 `dataset × model` 的视觉候选层池：

```text
U_visual = union(
  Top5(M_dot),
  Top5(M_cos),
  Top5(M_new_norm),
  Top5(M_pos_ratio),
  Top5(M_conflict),
  Top5(M_newn_x_1mcos),
  Top5(M_abscos_x_newn),
  Top5(Ours-Direct-Conflict),
  Top5(Ours-AbsDirection-Direct),
  Top5(Ours-NoDirection-Direct),
  Top5(Ours-1MinusCos-Direct)
)
```

若候选层池过大，可先输出完整 union，再按以下优先级生成精简候选池：

```text
1. Ours-1MinusCos-Direct Top5
2. Ours-NoDirection-Direct Top5
3. Ours-AbsDirection-Direct Top3
4. M_abscos_x_newn Top3
5. M_newn_x_1mcos Top3
6. M_new_norm Top3
7. 其他公式补充未覆盖层
```

该优先级只是工程执行建议，不等于论文最终结论。最终仍以真实扫层结果比较为准。

输出：

```text
visual_candidate_pool_union.csv
visual_candidate_pool_union.md
```

字段：

```text
dataset
model
layer
selected_by_formulas
selected_by_ours_variants
selected_by_base_formulas
coverage
status
note
```

---

## 12. 结果解释规则

### 12.1 raw dot 不是最终编辑层

若 `M_dot` Top-K 集中在浅层，例如 `0,1,2,3,4`，通常说明浅层视觉表示对 old/new answer 梯度都很强，但不一定是最适合编辑的层。必须通过真实 adapter 扫层验证。

### 12.2 零梯度层不能作为候选层

若：

```text
S_v_zero_grad = true
```

则该层不进入 clean Top-K，即使某些反排公式把它排到前面，也只能作为诊断信息。

### 12.3 严格负方向公式不能被单独称为主公式

`Ours-Direct-Conflict` 只是四个 Ours 系列指标之一。若它失败，不能将整个 Ours 视觉梯度方法判为失败，而应同时报告其他公式：

```text
Ours-AbsDirection-Direct
Ours-NoDirection-Direct
Ours-1MinusCos-Direct
```

### 12.4 方向指标可能存在模型差异

`M_cos`、`M_pos_ratio`、`M_conflict`、`M_newn_x_1mcos`、`M_abscos_x_newn` 以及 4 个 Ours 方向相关指标都可能出现模型差异、符号翻转或层段偏移。因此，不得只凭一个模型的相关性结论在所有模型上固定公式。

---

## 13. 跨模型实验模板

每次新模型/新数据集必须填写：

```text
model_name:
dataset_name:
data_path:
image_root:
sample_count:
prompt_field:
image_field:
old_answer_field:
new_answer_field:
layer_range:
layer_path_template:
visual_token_scope_rule:
answer_loss_rule: mean_token_NLL
zero_grad_eps: 1e-8
output_dir:
base_visual_candidate_formulas:
  - M_dot
  - M_cos
  - M_new_norm
  - M_pos_ratio
  - M_conflict
  - M_newn_x_1mcos
  - M_abscos_x_newn
ours_visual_candidate_formulas:
  - Ours-Direct-Conflict
  - Ours-AbsDirection-Direct
  - Ours-NoDirection-Direct
  - Ours-1MinusCos-Direct
old_field_policy: model_pred_main_pred_only_ablation
```

必须记录：

```text
CUDA_VISIBLE_DEVICES / Slurm job id
node name
model checkpoint path
script commit or local script path
run_config.json
```

---

## 14. 服务器执行建议

优先使用 Slurm 或已有 allocation，不要直接打断正在训练的节点。

示例：E-VQA proxy500 / BLIP2 / g08

```text
train json:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json

image root:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images

output:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy500_blip2_visual_gradient_7base_4ours_YYYYMMDD_HHMMSS
```

如果节点名是 `g08`，作业内部通常使用：

```text
CUDA_VISIBLE_DEVICES=0
--device cuda:0
```

不要把节点名 `g08` 误解成物理 GPU id `8`。

---

## 15. 报告模板

每次实验结束后写一份 Markdown 报告，至少包含：

```text
1. 数据与字段映射
   - old = ?
   - new = ?
   - prompt = ?
   - image = ?

2. 运行配置
   - model
   - layers
   - n_request
   - visual token scope
   - answer loss rule

3. 映射检查
   - total_cases
   - mapped_cases
   - missing_cases
   - empty_model_pred_count
   - duplicate_image_ids 是否可解释

4. 视觉梯度核心原始指标表
   - S_v_dot
   - S_v_cos
   - S_v_new_norm
   - S_v_positive_ratio
   - S_v_zero_grad
   - S_v_neg_cos（diagnostic only）
   - S_v_depth2（diagnostic only）
   - S_strict_negcos_depth2（diagnostic only）

5. 七个基础候选公式排序
   - M_dot Top-3 / Top-5
   - M_cos Top-3 / Top-5
   - M_new_norm Top-3 / Top-5
   - M_pos_ratio Top-3 / Top-5
   - M_conflict Top-3 / Top-5
   - M_newn_x_1mcos Top-3 / Top-5
   - M_abscos_x_newn Top-3 / Top-5

6. 四个 Ours 系列指标排序
   - Ours-Direct-Conflict Top-3 / Top-5
   - Ours-AbsDirection-Direct Top-3 / Top-5
   - Ours-NoDirection-Direct Top-3 / Top-5
   - Ours-1MinusCos-Direct Top-3 / Top-5

7. 候选层交集与并集
   - 每个公式 Top-K
   - 11 公式 Top-K union
   - 多公式共同命中的层

8. 结论
   - 当前只给出候选层，不声明最佳公式
   - 哪些层建议进入后续真实 adapter sweep
   - 哪些公式需要真实扫层后再判断
```

---

## 16. 最小验收清单

实验完成前必须逐项检查：

```text
[ ] old/new 字段映射明确，且写入报告
[ ] answer loss 是 mean token NLL
[ ] base model 参数冻结，base_requires_grad_params=0
[ ] adapter_used=false
[ ] mapped_cases == total_cases
[ ] missing_cases == []
[ ] visual_token_start/end 非空或可解释 mixed
[ ] 每层 n_request 一致
[ ] zero_grad 层未进入 clean Top-K
[ ] 输出 sample JSONL、layer CSV、Top-K JSON/CSV、run_config
[ ] 7 个基础视觉候选公式全部输出 Top-3 / Top-5
[ ] 4 个 Ours 系列指标全部输出 Top-3 / Top-5
[ ] layer CSV 额外保留 `S_v_neg_cos`、`S_v_depth2`、`S_strict_negcos_depth2`，并标记为 diagnostic only
[ ] 没有把 `S_strict_negcos_depth2` 单独写成主公式或唯一主方法
[ ] 没有输出文本候选层排序
[ ] 没有把 Ours-Direct-Conflict 当作唯一主公式
[ ] 没有执行 Pre 偏移
[ ] 最终结论写成“候选层”，不写成“已证明最佳层”
[ ] 后续用真实扫层结果比较全部公式，再决定最终采用哪个公式
```

---

## 17. 推荐结论表述

正确表述：

```text
本实验基于 Virtual Delta-H 视觉梯度，分别计算 7 个基础视觉候选公式和 4 个 Ours 系列深度加权候选指标。每个公式独立产生 Top-K 候选 adapter 插入层。当前阶段不预设唯一主公式，后续将通过真实 adapter sweep 的 Average、Best@K、Mean@K、Regret@K、Hit@K 以及排序相关性分析，确定哪一类视觉梯度公式最能预测有效编辑层。
```

避免表述：

```text
严格负余弦公式就是最终主公式。
S_strict_negcos_depth2 是唯一主候选公式。
Ours-Direct-Conflict 失败就说明视觉梯度方法失败。
梯度最高层就是最终最佳编辑层。
raw S_v_dot Top1 就是 visual golden layer。
某个公式只凭 proxy500 train 梯度就证明 full E-VQA 最优层。
文本表征候选层与视觉表征候选层可以混在同一主表。
```


---

## 18. 已遇到问题与本手册修复执行规范

本节用于把前期按照旧版 Ours-Direct 手册运行 7 models × 3 datasets 时遇到的问题，以及 `OursDirect_next_repair_report.md` / `OursDirect_next_repair_report_supplemented.md` 中的解决办法，正式并入本视觉候选层计算手册。后续视觉表征候选层计算任务应以本节作为执行约束。

### 18.1 已遇到的核心问题

前期 Ours-Direct 21 组运行结果显示，严格负余弦冲突公式在部分组合上不能稳定产生候选层。典型状态包括：

```text
done = 8 / 21
low_confidence = 3 / 21
failed = 10 / 21
```

主要失败原因不是进程崩溃，而是严格负方向门控后没有合法层：

```text
failure_reason = no_valid_ours_direct_layer
```

这说明：

```text
1. visual gradient hook 与 layer score 不一定完全失效；
2. 问题主要来自 max(0, -S_v_cos) 过硬；
3. 某些模型/数据集的 old/new 视觉梯度可能表现为正向或混合方向；
4. 因此不能把 Ours-Direct-Conflict 失败解释为整个视觉梯度候选层方法失败。
```

### 18.2 当前阶段边界

本阶段只做视觉表征候选层计算与候选层池整理。

本阶段允许执行：

```text
1. 生成或读取 visual gradient layer scores；
2. 计算 7 个基础视觉候选公式；
3. 计算 4 个 Ours 系列深度加权指标；
4. 检查 layer score 是否可派生；
5. 统计 coverage、empty_model_pred、zero_grad、nonfinite、empty_visual_span；
6. 对 Qwen2.5-VL 执行 model_pred 与 coverage 诊断；
7. 输出 visual_candidate_pool_union.csv/md，作为后续真实扫层输入。
```

本阶段不执行：

```text
1. 不启动真实 50 epoch adapter training；
2. 不做 full-layer sweep；
3. 不补跑 Perturb-KL-Direct；
4. 不补跑 CMA-Direct；
5. 不补跑 LGA-Param-Direct；
6. 不用任何消融公式覆盖其他公式；
7. 不把 Ours-Direct-Conflict 单独写成主公式。
```

### 18.3 layer score 可派生性检查

从已有 layer score 文件派生 7 个基础公式和 4 个 Ours 指标前，必须检查必要列是否存在。

必要列：

```text
layer
S_v_dot
S_v_cos
S_v_new_norm
S_v_positive_ratio
S_v_zero_grad
S_v_neg_cos
S_v_depth2
S_strict_negcos_depth2
```

建议列：

```text
S_v_conflict
S_v_dot_per_dim
S_v_old_norm
S_v_joint_norm
S_v_old_nonzero_ratio
S_v_new_nonzero_ratio
median_v_dot
visual_token_start
visual_token_end
visual_token_start_valid
visual_token_end_valid
valid_samples
total_samples
coverage
```

若缺少必要列，不得直接派生候选层，应标记：

```text
status = cannot_derive
failure_reason = missing_required_score_columns
```

并输出：

```text
visual_layer_score_derivability_report.csv
```

字段建议：

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
failure_reason
```

### 18.4 coverage 与状态判定

所有公式在每个 `dataset × model` 组合上都必须记录 coverage：

```text
coverage = valid_samples / total_samples
```

统一状态判定：

| Coverage | Status | 说明 |
|---:|---|---|
| `>= 0.80` | `done` | 可进入候选层比较 |
| `0.20 - 0.80` | `low_confidence` | 仅作参考，不进入强结论 |
| `< 0.20` | `invalid_low_coverage` | 不进入主候选比较 |

特殊规则：

```text
MMKE-entity / Qwen2.5-VL-3B 若仍接近 5/636，应强制标记为 invalid_low_coverage。
```

注意：

```text
coverage 低不是公式失败本身，而是数据映射、model_pred、visual span 或有效梯度覆盖问题；
coverage 修复前，不应把该组合纳入公式优劣判断。
```

### 18.5 失败原因统计

每个 `dataset × model × formula` 都必须输出失败原因统计，避免只看到 failed 而不知道原因。

建议统计字段：

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
no_valid_visual_gradient_layer
no_valid_negative_cosine_layer
empty_model_pred
invalid_low_coverage
missing_required_score_columns
empty_visual_span
zero_grad_or_nonfinite
unknown
```

对于 `Ours-Direct-Conflict`，若有效层存在但所有层：

```text
max(0, -S_v_cos) = 0
```

则标记：

```text
status = failed
failure_reason = no_valid_negative_cosine_layer
```

但其他 10 个公式仍应继续正常输出候选层。

### 18.6 Qwen2.5-VL 专项诊断与修复

Qwen2.5-VL 的问题不能和普通公式失败混在一起。若出现大量 `empty_model_pred` 或 coverage 过低，应先做生成与映射诊断。

必须检查：

```text
prompt template 是否与 Qwen-VL processor 对齐
image tensor 是否正常进入模型
图像路径是否存在
max_new_tokens 是否过小
stop tokens 是否过早截断
model_pred 是否为空字符串
样本 ID 与输出文件是否错位
visual token span 是否为空
```

必须输出：

```text
qwen_model_pred_empty_report.csv
qwen_model_pred_mapping_report.json
qwen_visual_gradient_coverage_recheck.md
```

建议报告字段：

```text
dataset
model
sample_id
image_path
image_exists
prompt_hash
model_pred_raw
model_pred_is_empty
generation_error
visual_span_valid
skip_reason
```

修复后只重跑：

```text
1. Qwen2.5-VL 的 deterministic model_pred generation；
2. Qwen2.5-VL 的 visual gradient metric extraction；
3. 11 个视觉候选公式的 Top-K 生成。
```

不得在 Qwen coverage 修复前启动真实 adapter 训练。

### 18.7 公式输出与候选层清洗规则

每个公式都必须保存 raw 与 clean 版本：

```text
raw_top3
raw_top5
clean_top3
clean_top5
removed_layers
remove_reason
```

clean Top-K 删除规则：

```text
1. 删除 S_v_zero_grad = true 的层；
2. 删除 S_v_cos / S_v_new_norm / S_v_depth2 非有限值的层；
3. 删除 visual_token_start/end 为空或 visual span 无效的层；
4. 删除越界层；
5. 同一公式内去重，保留第一次出现；
6. 不自动用其他公式或其他方法补齐。
```

如果 clean Top-K 不足 K 个：

```text
status = insufficient_valid_layers
```

如果 clean Top-K 为空：

```text
status = unavailable
failure_reason = no_valid_visual_gradient_layer
```

### 18.8 主结果、消融结果与诊断列不得混写

本手册中有三类内容，必须分清：

| 类型 | 示例 | 是否产生候选层 | 是否可作为最终公式 |
|---|---|---:|---:|
| 原始视觉梯度指标 | `S_v_dot`, `S_v_cos`, `S_v_new_norm` | 否，作为公式输入 | 否 |
| diagnostic only 历史对照列 | `S_v_neg_cos`, `S_v_depth2`, `S_strict_negcos_depth2` | 否，单独不作为方法 | 否 |
| 显式候选公式/方法名 | `M_newn_x_1mcos`, `Ours-1MinusCos-Direct` 等 | 是 | 后续真实扫层后决定 |

因此：

```text
S_strict_negcos_depth2 只能作为 diagnostic only 字段；
严格负方向候选层必须通过 Ours-Direct-Conflict 方法名输出；
Ours-Direct-Conflict 不能覆盖其他 10 个公式；
任一公式失败不能代表全部视觉梯度候选层方法失败。
```

### 18.9 Ours 系列候选层池构建规则

除第 11 节的 11 公式整体候选池外，本手册还要求输出一个 Ours 系列候选层池，用于复现实验修复阶段的结果。

对每个 `dataset × model`：

```text
U_ours = union(
  Top5(Ours-Direct-Conflict),
  Top5(Ours-AbsDirection-Direct),
  Top5(Ours-NoDirection-Direct),
  Top5(Ours-1MinusCos-Direct)
)
```

输出文件：

```text
ours_series_candidate_pool.csv
ours_series_candidate_pool.md
```

字段建议：

```text
dataset
model
layer
selected_by_ours_variants
source_methods
source_topk_type
coverage
pool_status
note
```

规则：

```text
1. 只汇总 Ours 系列 4 个指标；
2. 不用 Middle-Prior、VisEdit、SaLEM、Perturb-KL、CMA、LGA 补齐；
3. 若某 Ours 变体 invalid_low_coverage，则该变体候选层不进入 pool；
4. 同一层被多个 Ours 变体选中，只保留一行，并记录全部来源；
5. 如果所有 Ours 变体均不可用，pool_status = unavailable。
```

### 18.10 InstructBLIP 中层保护层边界

历史分析提示 InstructBLIP visual 可能存在 instruction-aware Q-Former 的浅层预对齐问题，导致视觉梯度指标在浅层出峰，而真实编辑效果可能需要中层固化。

可选保护层：

```text
L12,L13,L14
```

但本手册当前任务是视觉梯度公式候选层计算，因此：

```text
1. InstructBLIP-MidProtect-Direct 不写入 11 个视觉梯度公式主表；
2. 不写入 U_ours；
3. 若后续真实扫层需要，必须另开 optional_architecture_protection_candidates.csv/md；
4. 必须标记 not_ours_metric = true。
```

### 18.11 本修复版最终交付物

一次完整视觉表征候选层计算任务，至少输出：

```text
sample_virtual_delta_h_scores.jsonl
visual_gradient_layer_scores.csv
visual_candidate_formula_rankings.csv
visual_candidate_layers_topk.csv
visual_candidate_layers_topk.md
visual_candidate_layers_topk.json
visual_layer_score_derivability_report.csv
visual_formula_failure_reason_summary.csv
visual_candidate_pool_union.csv
visual_candidate_pool_union.md
ours_series_candidate_pool.csv
ours_series_candidate_pool.md
old_answer_mapping_report.json
run_config.json
summary.md
```

若包含 Qwen2.5-VL，还必须额外输出：

```text
qwen_model_pred_empty_report.csv
qwen_model_pred_mapping_report.json
qwen_visual_gradient_coverage_recheck.md
```

---

## 19. 修复版最小执行清单

```text
[ ] 明确本阶段只做视觉表征候选层计算，不启动真实 adapter training
[ ] 每个模型/数据集均使用 model_pred 作为默认旧知识字段
[ ] 对所有样本完成 old/new mean token NLL 的 teacher forcing 对齐
[ ] visual_token_start/end 由模型实际输入映射得到
[ ] base model frozen，adapter_used=false，optimizer_used=false
[ ] 输出全部视觉原始指标
[ ] layer CSV 保留 S_v_neg_cos / S_v_depth2 / S_strict_negcos_depth2，并标记 diagnostic only
[ ] 同时计算 7 个基础视觉公式
[ ] 同时计算 4 个 Ours 系列指标
[ ] 每个公式输出 Top-1 / Top-3 / Top-5 / full ranking
[ ] 每个公式保存 raw_topK 与 clean_topK
[ ] 每个公式记录 coverage / status / failure_reason
[ ] 生成 visual_layer_score_derivability_report.csv
[ ] 生成 visual_formula_failure_reason_summary.csv
[ ] Qwen2.5-VL 单独检查 empty_model_pred 与 coverage
[ ] MMKE-entity / Qwen2.5-VL 在 coverage < 0.2 时标记 invalid_low_coverage
[ ] 生成 visual_candidate_pool_union.csv/md
[ ] 生成 ours_series_candidate_pool.csv/md
[ ] 不用任何公式覆盖其他公式
[ ] 不把 Ours-Direct-Conflict 或 S_strict_negcos_depth2 写成唯一主公式
[ ] 不输出文本表征候选层排序
[ ] 不补跑 Perturb-KL / CMA / LGA
[ ] 最终结论只写“候选层”，不写“已证明最佳层”
```
