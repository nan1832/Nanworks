# Perturb-KL-Direct 7 模型 3 数据集候选层实验实施建议

> 本文件是《Perturb-KL-Direct 7 模型 3 数据集候选层实验手册》的实施级补充。  
> 目标是在不改变主方法定义的前提下，补充随机性控制、样本一致性、数值稳定性、原始分数保存、Hook 实现和运行验收规则，确保 7 个模型、3 个数据集上的候选层排序可复现、可解释、可审计。

---

# 1. 总体判断

当前主方法可以保留：

```text
method = Perturb-KL-Direct-AltSeq
target = complete alt sequence
perturb_scope = visual tokens
candidate_conversion = Direct
ranking_metric = robust KL
```

其逻辑为：

\[
\text{扰动第 }l\text{ 层 visual-token hidden states}
\rightarrow
\text{测量完整 alt 序列上的输出分布变化}
\rightarrow
\text{直接选择 KL 得分最高的 Top-K 层}.
\]

正式批量运行前，建议补充以下五项关键要求：

1. 使用稳定哈希生成随机种子；
2. 不同层使用相同基础随机噪声方向；
3. 识别并排除近似常数的无信息噪声组；
4. 所有层使用同一批有效样本；
5. 保存每个 `alpha × repeat × layer` 的完整原始结果。

---

# 2. 稳定随机种子

## 2.1 禁止直接使用 Python 内置 `hash()`

以下写法不够稳定：

```python
seed = hash((dataset, subset, model, sample_id, layer, alpha, repeat))
```

Python 内置 `hash()` 可能因进程、环境和 `PYTHONHASHSEED` 不同而变化，无法保证跨机器和跨运行复现。

## 2.2 推荐稳定哈希

推荐使用 SHA-256：

```python
import hashlib

def stable_seed(*items: object) -> int:
    text = "||".join(map(str, items))
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % (2**31 - 1)
```

正式记录：

```text
seed_method = sha256_first_8_bytes_mod_2^31_minus_1
```

---

# 3. 不同层使用相同基础噪声方向

## 3.1 原因

如果随机种子包含 `layer`：

```text
L10 使用噪声 z10
L11 使用噪声 z11
```

那么层间 KL 差异同时受到：

1. 层本身敏感性；
2. 随机噪声方向；

两部分影响。

为了让层间比较更公平，建议采用 common random numbers。

## 3.2 推荐种子键

主实验建议：

```text
seed = stable_seed(
    dataset,
    subset,
    model,
    sample_id,
    alpha,
    repeat
)
```

不包含 `layer`。

生成基础标准正态噪声：

\[
z_i^{\alpha,r}
\sim
\mathcal N(0,I).
\]

对各层使用：

\[
\epsilon_{i,l}^{\alpha,r}
=
\alpha
\sigma_{i,l}^{v}
z_i^{\alpha,r}.
\]

这样不同层面对同一噪声方向，只保留层表示与层敏感性差异。

## 3.3 Hidden shape 不同的情况

如果某模型不同层 hidden shape 不一致，可以把 shape 加入种子：

```text
seed = stable_seed(
    dataset,
    subset,
    model,
    sample_id,
    alpha,
    repeat,
    visual_token_count,
    hidden_size
)
```

仍不建议直接加入层号。

---

# 4. 噪声标准差定义

## 4.1 Clean hidden 上计算

对：

\[
h_{i,l}^{v}
\in
\mathbb R^{N_{v,i}\times d},
\]

定义：

\[
\sigma_{i,l}^{v}
=
\operatorname{Std}
\left(
\operatorname{detach}(h_{i,l}^{v,\mathrm{clean}})
\right).
\]

标准差在 visual-token 维度和 hidden 维度的全部元素上计算一个标量。

固定：

```text
unbiased = false
```

## 4.2 安全下限

建议：

\[
\sigma_{i,l}^{safe}
=
\max
\left(
\sigma_{i,l}^{v},
\epsilon_\sigma
\right),
\]

默认：

```text
epsilon_sigma = 1e-6
```

如果原始标准差低于阈值，记录：

```text
small_hidden_std = true
raw_hidden_std
safe_hidden_std
```

不能静默产生几乎为零的扰动。

---

# 5. 近似常数层分数处理

## 5.1 问题

MinMax 归一化可能把极小差异放大为完整的 0–1 排序。

例如：

```text
max KL = 1.0003e-8
min KL = 1.0000e-8
```

这种情况下虽然数值不完全相同，但层间信号几乎不存在。

## 5.2 动态范围

对每个 `alpha × repeat`：

\[
\Delta_{\alpha,r}
=
\max_l S_{\mathrm{KL}}^{\alpha,r}(l)
-
\min_l S_{\mathrm{KL}}^{\alpha,r}(l).
\]

中位尺度：

\[
M_{\alpha,r}
=
\left|
\operatorname{median}_l
S_{\mathrm{KL}}^{\alpha,r}(l)
\right|.
\]

若：

\[
\Delta_{\alpha,r}
<
\max
\left(
\epsilon_{\mathrm{abs}},
\epsilon_{\mathrm{rel}}M_{\alpha,r}
\right),
\]

则该组判定为无信息组。

建议初始值：

```text
epsilon_abs = 1e-8
epsilon_rel = 1e-3
```

最终阈值应在 `pilot500 × BLIP2` 上检查后冻结。

## 5.3 无信息组处理

无信息组不参与稳健分数平均：

\[
\mathcal G_{\mathrm{valid}}
=
\left\{
(\alpha,r):
\text{该组动态范围有效}
\right\}.
\]

最终：

\[
S_{\mathrm{KL}}^{robust}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
\hat S_{\mathrm{KL}}^{\alpha,r}(l).
\]

如果：

\[
|\mathcal G_{\mathrm{valid}}|=0,
\]

该组合标记：

```text
status = unavailable
failure_reason = no_informative_alpha_repeat_group
```

必须记录：

```text
valid_alpha_repeat_count
invalid_alpha_repeat_count
dynamic_range
exclusion_reason
```

---

# 6. 统一有效样本集合

## 6.1 问题

如果某层使用 500 个样本，另一层因异常只使用 480 个样本，两层 KL 平均值不再完全可比。

## 6.2 推荐规则

先完成以下预检查：

```text
image exists
alt non-empty
tokenization valid
visual span valid
clean forward finite
target mask non-empty
```

形成基础有效集合：

\[
\mathcal D_{\mathrm{base}}.
\]

正式扰动后，如某样本在任一层、任一噪声组持续失败，应优先修复和重跑。

如果确实无法修复，应统一从所有层中排除该样本：

\[
\mathcal D_{\mathrm{common}}
=
\bigcap_{l,\alpha,r}
\mathcal D_{l,\alpha,r}^{valid}.
\]

## 6.3 输出要求

记录：

```text
manifest_sample_count
base_valid_sample_count
common_valid_sample_count
per_layer_processed_count
excluded_sample_ids
coverage_ratio
```

要求：

```text
per_layer_processed_count 相同
```

若不同，标记：

```text
status = low_confidence
failure_reason = inconsistent_sample_coverage_across_layers
```

---

# 7. 原始结果长表

## 7.1 必须新增

建议输出：

```text
perturb_kl_scores_long.csv
```

每一行对应：

```text
dataset × subset × model × layer × alpha × repeat
```

字段：

```text
dataset
subset
model
sample_scope
layer
alpha
repeat
seed_method
seed_value_or_seed_hash
raw_mean_kl
normalized_layer_score
dynamic_range
relative_dynamic_range
valid_alpha_repeat
processed_sample_count
rank_within_alpha_repeat
hidden_std_mean
hidden_std_min
hidden_std_max
status
failure_reason
config_hash
```

## 7.2 最终层表

`perturb_kl_layer_scores.csv` 建议增加：

```text
score_kl_robust
score_kl_raw_mean
rank_robust
mean_rank
rank_std
rank_percentile_mean
valid_group_count
invalid_group_count
localization_sample_count
common_valid_sample_count
coverage_ratio
status
failure_reason
```

定义原始平均 KL：

\[
S_{\mathrm{KL}}^{rawmean}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
S_{\mathrm{KL}}^{\alpha,r}(l).
\]

---

# 8. 排名稳定性

## 8.1 Repeat 间一致性

对每个噪声尺度：

\[
\rho_\alpha
=
\frac{1}{\binom{R}{2}}
\sum_{r_1<r_2}
\operatorname{Spearman}
\left(
S^{\alpha,r_1},
S^{\alpha,r_2}
\right).
\]

记录：

```text
spearman_between_repeats_by_alpha
```

## 8.2 排名百分位稳健分数

可额外保存：

\[
R_{\mathrm{percentile}}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
\frac{
L-\operatorname{rank}_{\alpha,r}(l)
}{
L-1
}.
\]

主候选仍按预注册的 robust MinMax score 排序；排名百分位用于稳定性诊断。

## 8.3 Low-confidence 标准

如果以下情况之一成立：

```text
valid_group_count < 50% of total groups
mean repeat Spearman < predefined threshold
robust Top-5 与 percentile Top-5 重叠过低
coverage_ratio below threshold
```

则标记：

```text
status = low_confidence
```

阈值在 pilot 后冻结。

---

# 9. 强噪声尺度 α=3

当前主尺度：

\[
\mathcal A
=
\{0.1,0.5,1,3\}.
\]

`alpha=3` 可以保留，但应在 pilot 中检查：

```text
是否产生极端 KL
是否使所有层输出崩坏
repeat 间排序是否稳定
是否与其他尺度排序完全相反
是否主导最终 robust score
```

如果 `alpha=3` 明显不稳定，可以预先决定：

```text
main noise scales = [0.1, 0.5, 1]
stress-test scale = [3]
```

该决定必须在完成 `pilot500 × BLIP2` 后、运行其余 20 个组合之前冻结。

不得根据不同模型分别选择最有利尺度。

---

# 10. 零扰动对照

增加：

```text
alpha = 0
```

仅作为 sanity check，不进入 robust score。

应满足：

\[
D_{\mathrm{KL}}^{\alpha=0}(l)
\approx 0
\quad
\forall l.
\]

如果明显非零，应检查：

```text
dropout 是否关闭
clean 与 perturbed forward 是否使用相同输入
hook 是否改变 tuple 或 dtype
cache 是否一致
随机性是否固定
```

建议记录：

```text
zero_noise_max_kl
zero_noise_mean_kl
zero_noise_pass
```

---

# 11. Hook 实现要求

## 11.1 Tuple 输出

部分 decoder block 返回：

```text
(hidden_states, cache, attention, ...)
```

Hook 只能替换第一个 hidden state：

```python
def perturb_hook(module, inputs, output):
    if isinstance(output, tuple):
        hidden = output[0]
        perturbed_hidden = perturb_visual_tokens(hidden)
        return (perturbed_hidden,) + output[1:]

    return perturb_visual_tokens(output)
```

禁止原地修改，推荐 clone 或函数式替换。

## 11.2 Visual mask

扰动只作用于 visual tokens：

```python
perturbed_hidden = hidden.clone()
perturbed_hidden[:, visual_mask, :] = (
    hidden[:, visual_mask, :] + noise
)
```

如果 mask 为空：

```text
raise error
status = unavailable
failure_reason = empty_visual_span
```

不允许 fallback 到 all prompt tokens。

---

# 12. Clean 分布缓存

同一样本的 clean 分布与候选层无关，应只计算一次：

```text
clean forward = 1
perturbed forward = L × alpha × repeat
```

缓存：

```text
clean_log_probs
target_mask
target_token_count
```

前提：

```text
model.eval()
dropout disabled
same prompt and image
same teacher-forcing target
same target mask
```

增加重复 clean sanity check：

\[
D_{\mathrm{KL}}
\left(
p_{\mathrm{clean}}^{(1)}
\Vert
p_{\mathrm{clean}}^{(2)}
\right)
\approx 0.
\]

---

# 13. KL 数值实现

## 13.1 推荐实现

\[
D_{\mathrm{KL}}(p\Vert q)
=
\sum_y
p(y)
\left[
\log p(y)-\log q(y)
\right].
\]

```python
clean_log_probs = torch.log_softmax(
    clean_logits.float(),
    dim=-1
)

perturbed_log_probs = torch.log_softmax(
    perturbed_logits.float(),
    dim=-1
)

kl_per_position = (
    clean_log_probs.exp()
    * (clean_log_probs - perturbed_log_probs)
).sum(dim=-1)
```

只对有效 alt token positions 平均。

## 13.2 注意事项

- 不要反向计算成 \(D_{\mathrm{KL}}(q\Vert p)\)；
- 不要把概率张量错误传给要求 log-prob 的 API；
- 主版本使用完整词表；
- 如使用 top-vocab 近似，必须另命名。

---

# 14. 候选层排序

主排序：

```text
primary key = score_kl_robust descending
tie break 1 = score_kl_raw_mean descending
tie break 2 = mean_rank ascending
tie break 3 = layer index ascending
```

输出：

```text
Top-3 raw
Top-3 clean
Top-5 raw
Top-5 clean
full layer scores
full layer ranking
```

不使用其他方法补齐候选层。

如果清洗后不足 K：

```text
status = low_confidence
failure_reason = insufficient_valid_layers_after_cleaning
```

---

# 15. 方法命名

正式论文建议写为：

```text
Perturb-KL-Direct-AltSeq
```

并说明：

> A robust perturbation-based baseline constructed for our evaluation.

原因是以下组合属于本实验实现：

```text
complete alt sequence
visual-token-only perturbation
multiple noise scales
multiple repeats
within-model layer normalization
robust score aggregation
Direct Top-K conversion
```

不应将整套组合表述为某篇原论文中的固定算法。

---

# 16. Pilot 验收

先运行：

```text
EVQA-pilot500 × BLIP2-OPT-2.7B
```

必须检查：

| 检查项 | 通过标准 |
|---|---|
| 稳定哈希 | 跨进程种子一致 |
| Common noise | 不同层使用相同基础噪声方向 |
| Visual mask | 非空且位置正确 |
| Zero noise | `alpha=0` 时 KL 近似 0 |
| Clean repeat | 两次 clean forward KL 近似 0 |
| KL finite | 无大规模 NaN/Inf |
| Sample coverage | 所有层样本数一致 |
| Dynamic range | 至少部分噪声组有有效层间差异 |
| Repeat stability | 每个尺度的重复排序有合理一致性 |
| Hook consistency | 扰动位置与 adapter 位置一致 |
| Reproducibility | 相同配置重复运行 Top-K 一致 |
| Batch invariance | 改变 batch size 后排序高度一致 |

---

# 17. 最终检查清单

- [ ] 使用 SHA-256 稳定种子。
- [ ] 主实验种子不包含 layer。
- [ ] 不同层使用相同基础噪声方向。
- [ ] hidden 标准差在 clean visual hidden 上计算。
- [ ] 设置 `unbiased=false`。
- [ ] 设置 hidden std 安全下限。
- [ ] 排除近似常数的无信息噪声组。
- [ ] robust score 只对有效组平均。
- [ ] 所有层使用同一有效样本集合。
- [ ] 保存 `alpha × repeat × layer` 原始长表。
- [ ] 保存 repeat 间 Spearman。
- [ ] `alpha=3` 是否进入主分数已在 pilot 后冻结。
- [ ] 增加 `alpha=0` sanity check。
- [ ] Hook 正确处理 tuple 输出。
- [ ] visual mask 为空时直接报错。
- [ ] clean 分布只计算一次并通过重复一致性测试。
- [ ] KL 使用 float32 log-space 完整词表计算。
- [ ] 候选层直接按 robust KL Top-K 选择。
- [ ] 不执行 Pre，不使用其他方法 fallback。
- [ ] 相同配置重复运行候选层一致。
