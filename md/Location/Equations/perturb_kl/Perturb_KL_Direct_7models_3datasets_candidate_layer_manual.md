# Perturb-KL-Direct 7 模型 3 数据集候选层实验手册

## 1. 实验目标

本手册用于计算 7 个 VLM 在 3 个数据集上的 `Perturb-KL-Direct-AltSeq` 候选层。

主实验目标是：

```text
对 decoder 每一层的 visual-token hidden states 加噪声扰动，
测量完整 alt 目标序列输出分布的 KL 变化，
选择 KL 稳健分数最高的 Top-3 / Top-5 层作为候选 adapter 插入层。
```

本手册只定义候选层定位实验。真实 adapter 训练与最终编辑评测应使用统一训练手册继续执行。

## 2. 实验范围

### 2.1 模型

| Model | Short name |
|---|---|
| BLIP2-OPT-2.7B | `blip2-opt-2.7b` |
| InstructBLIP-Vicuna-7B | `instructblip-vicuna-7b` |
| MiniGPT-4-Vicuna-7B | `minigpt-4-vicuna-7b` |
| LLaVA-v1.5-7B | `llava-v1.5-7b` |
| Qwen2.5-VL-3B-Instruct | `qwen2.5-vl-3b-instruct` |
| PaliGemma-3B | `paligemma-3b` |
| SmolVLM-Instruct-1.7B | `smolvlm-1.7b` |

### 2.2 数据集

| Dataset | Task/subset | 用途 |
|---|---|---|
| EVQA-pilot500 | `pilot500` | localization 候选层定位 |
| MMKE | `visual` | localization 候选层定位 |
| MMKE | `entity` | localization 候选层定位 |

候选层定位不得使用最终 eval/test 指标反向选择层。若某数据集已有 train/localization split，优先使用 localization/train split；最终 eval/test 只用于后续真实编辑评测。

## 3. 主方法与消融边界

主扰动基线固定为：

```text
Perturb-KL-Direct-AltSeq
```

含义：

```text
target sequence = complete alt sequence
perturb scope = visual tokens only
candidate conversion = Direct
ranking metric = robust KL score
```

`Perturb-KL-Pre-AltSeq` 只作为附加/消融，用于检查“高敏感区之前是否更适合挂 adapter”。它不进入主扰动基线表，也不替代 `Perturb-KL-Direct-AltSeq` 的候选层。

本方法是本实验构造的稳健扰动基线，不应表述为某篇原论文中的固定算法。论文或记录中建议写作：

```text
Perturb-KL-Direct-AltSeq: a robust perturbation-based baseline constructed for our evaluation.
```

## 4. 层编号与 Hook 定义

候选层 `L_l` 统一表示：

```text
decoder block l 的输出之后，decoder block l+1 之前
```

Perturb-KL 的扰动 hook 必须与 adapter 候选层 hook 位置一致。

禁止以下不一致设置：

```text
候选层按 block output 定义，但扰动加在 block input
候选层按 decoder layer 定义，但扰动加在 attention 内部
候选层按语言模型层定义，但 visual span 来自错误 wrapper
visual-token 失败后 fallback 到 all prompt tokens
```

Hook 实现必须只替换 decoder block 输出中的 hidden states。若 block 输出是 tuple，只能替换第一个元素：

```python
def perturb_hook(module, inputs, output):
    if isinstance(output, tuple):
        hidden = output[0]
        perturbed_hidden = perturb_visual_tokens(hidden)
        return (perturbed_hidden,) + output[1:]

    return perturb_visual_tokens(output)
```

禁止原地修改 hidden states。visual-token 扰动必须使用 clone 或函数式替换：

```python
perturbed_hidden = hidden.clone()
perturbed_hidden[:, visual_mask, :] = (
    hidden[:, visual_mask, :] + noise
)
```

若 `visual_mask` 为空，必须报错并标记：

```text
status = unavailable
failure_reason = empty_visual_span
```

不得 fallback 到 all prompt tokens 或 text tokens。

## 5. 运行前准备

### 5.1 模型注册表

每个模型必须先写入 `model_registry.yaml`：

```text
model_name
checkpoint_or_repo_id
revision_or_commit
processor_or_tokenizer_name
decoder_module_path
num_decoder_layers
hidden_size
valid_layer_index_range
visual_token_rule
adapter_hook_position
image_size_or_visual_token_budget
dtype
quantization
torch_version
transformers_version
wrapper_commit_or_hash
```

`valid_layer_index_range` 必须用于候选层合法性检查。例如 decoder 有 `L` 层，则合法层为：

```text
0, 1, ..., L-1
```

### 5.2 样本 Manifest

每个数据集必须先写入 `sample_manifest.csv`：

```text
dataset
subset
sample_id
image_path
image_exists
question_hash
alt_answer_hash
pred_answer_hash
used_for_localization
used_for_training
used_for_eval
skip_reason
```

缺图、空 `alt`、无法 tokenize、视觉输入失败的样本不得静默丢弃，必须记录 `skip_reason`。

正式计算前必须先形成基础有效集合：

```text
D_base = samples passing all prechecks
```

预检查项目固定为：

```text
image exists
alt non-empty
tokenization valid
visual span valid
clean forward finite
target mask non-empty
```

如果扰动阶段某样本在任一层、任一 `alpha × repeat` 持续失败，应优先修复并重跑；确实无法修复时，必须从所有层统一排除该样本，形成：

\[
\mathcal D_{\mathrm{common}}
=
\bigcap_{l,\alpha,r}
\mathcal D_{l,\alpha,r}^{valid}.
\]

所有层最终使用的 `per_layer_processed_count` 必须一致。否则该 `dataset × model` 标记为：

```text
status = low_confidence
failure_reason = inconsistent_sample_coverage_across_layers
```

必须记录：

```text
manifest_sample_count
base_valid_sample_count
common_valid_sample_count
per_layer_processed_count
excluded_sample_ids
coverage_ratio
```

### 5.3 Visual-token 与 Hook 单元测试

每个 `model × dataset` 正式批量计算前必须通过：

| Test | 通过标准 |
|---|---|
| visual token count | wrapper 记录的 visual token 数等于进入 LM 的视觉 token 数 |
| visual hidden grad/activation | 指定 hook 能捕获第 `l` 层 visual-token hidden states |
| visual noise effect | 对 visual tokens 加噪声后输出 logits 或 loss 发生变化 |
| empty mask guard | visual mask 为空时必须报错，不得 fallback |
| hook consistency | Perturb hook 与 adapter hook 使用同一 block-output 位置 |

失败时该 `model × dataset` 的 Perturb-KL 状态记为：

```text
status = unavailable
failure_reason = visual_token_or_hook_test_failed
```

## 6. Perturb-KL 打分公式

### 6.1 Clean 分布

对样本 `i`，使用完整 `alt` 序列做 teacher forcing，得到 clean 输出分布：

\[
p_{i,t}^{clean}(y)
\]

teacher forcing 必须统一 shift：

```text
shift_logits = logits[..., :-1, :]
shift_labels = labels[..., 1:]
```

prompt、visual token、padding、被截断位置的 labels 必须为：

```text
-100
```

KL 只在有效 alt target positions 上计算。

同一样本的 clean 分布与候选层无关，应只计算一次并缓存：

```text
clean forward = 1
perturbed forward = L × alpha × repeat
```

缓存内容：

```text
clean_log_probs
target_mask
target_token_count
```

缓存前提：

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

### 6.2 Visual-token 扰动

对 decoder 第 `l` 层 visual-token hidden states：

\[
h_{i,l}^{v}
\]

加高斯噪声：

\[
\tilde h_{i,l}^{v}
=
h_{i,l}^{v}
+
\epsilon_{i,l}^{\alpha,r}
\]

\[
\epsilon_{i,l}^{\alpha,r}
\sim
\mathcal N
\left(
0,
(\alpha\sigma_{i,l}^{safe})^2
\right)
\]

其中标准差必须在 detached clean visual hidden 上计算：

\[
\sigma_{i,l}^{v}
=
\operatorname{Std}
\left(
\operatorname{detach}(h_{i,l}^{v,\mathrm{clean}})
\right)
\]

标准差在该样本该层全部 visual tokens 与 hidden 维度上计算：

```text
unbiased = false
```

标准差使用安全下限：

\[
\sigma_{i,l}^{safe}
=
\max
\left(
\sigma_{i,l}^{v},
\epsilon_\sigma
\right)
\]

默认：

```text
epsilon_sigma = 1e-6
```

若原始标准差低于阈值，必须记录：

```text
small_hidden_std = true
raw_hidden_std
safe_hidden_std
```

实际扰动使用：

\[
\epsilon_{i,l}^{\alpha,r}
=
\alpha
\sigma_{i,l}^{safe}
z_i^{\alpha,r}.
\]

### 6.3 噪声尺度与随机种子

主实验固定：

```text
noise_scales = [0.1, 0.5, 1, 3]
repeat = 3
base_repeats = [2026, 2027, 2028]
```

实际随机数种子必须由稳定哈希生成：

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

禁止使用 Python 内置 `hash()`，因为它会受进程、环境和 `PYTHONHASHSEED` 影响。

主实验使用 common random numbers。种子键不得包含 `layer`：

```text
seed = stable_seed(dataset, subset, model, sample_id, alpha, repeat)
```

这样不同层使用相同基础噪声方向，只比较层表示和层敏感性差异：

\[
z_i^{\alpha,r}
\sim
\mathcal N(0,I)
\]

\[
\epsilon_{i,l}^{\alpha,r}
=
\alpha
\sigma_{i,l}^{safe}
z_i^{\alpha,r}.
\]

若某模型不同层 hidden shape 不一致，可以加入 shape 信息，但仍不直接加入层号：

```text
seed = stable_seed(dataset, subset, model, sample_id, alpha, repeat, visual_token_count, hidden_size)
```

种子不得依赖 batch 顺序、GPU 数、DataLoader worker 数或运行时间。

`alpha = 0` 只作为 sanity check，不进入 robust score。应满足：

\[
D_{\mathrm{KL}}^{\alpha=0}(l)
\approx 0
\quad
\forall l.
\]

必须记录：

```text
zero_noise_max_kl
zero_noise_mean_kl
zero_noise_pass
```

`alpha = 3` 先保留在主尺度中，但必须在 `EVQA-pilot500 × BLIP2-OPT-2.7B` pilot 后冻结决策。若它造成极端 KL、输出崩坏、repeat 排序不稳定或主导最终分数，则后续主实验改为：

```text
main noise scales = [0.1, 0.5, 1]
stress-test scale = [3]
```

该决定只能在 pilot 后、其余组合运行前统一冻结，不得按模型或数据集单独调节。

### 6.4 Perturbed 分布与 KL

扰动第 `l` 层后得到：

\[
p_{i,l,t}^{\alpha,r}(y)
\]

KL 方向固定为：

```text
D_KL(clean || perturbed)
```

计算要求：

```text
logits cast to float32
softmax/log_softmax on full vocabulary
target mask excludes prompt, visual tokens, padding and truncated positions
```

推荐使用 log-space 完整词表实现：

```python
clean_log_probs = torch.log_softmax(clean_logits.float(), dim=-1)
perturbed_log_probs = torch.log_softmax(perturbed_logits.float(), dim=-1)

kl_per_position = (
    clean_log_probs.exp()
    * (clean_log_probs - perturbed_log_probs)
).sum(dim=-1)
```

只对有效 alt token positions 平均。禁止反向计算为 `D_KL(perturbed || clean)`；禁止把概率张量错误传给要求 log-prob 的 API；若使用 top-vocab 近似，必须另命名，不能混入主表。

样本级 KL：

\[
D_{i,l}^{\alpha,r}
=
\frac{1}{T_i}
\sum_{t=1}^{T_i}
D_{\mathrm{KL}}
\left(
p_{i,t}^{clean}
\Vert
p_{i,l,t}^{\alpha,r}
\right)
\]

数据集平均：

\[
S_{\mathrm{KL}}^{\alpha,r}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
D_{i,l}^{\alpha,r}
\]

### 6.5 稳健分数

对每个 `alpha × repeat` 在同一个 `dataset × model` 内做层间 MinMax 归一化：

\[
\hat S_{\mathrm{KL}}^{\alpha,r}(l)
=
\operatorname{MinMaxNorm}_{l}
S_{\mathrm{KL}}^{\alpha,r}(l)
\]

对每个 `alpha × repeat` 先计算动态范围：

\[
\Delta_{\alpha,r}
=
\max_l S_{\mathrm{KL}}^{\alpha,r}(l)
-
\min_l S_{\mathrm{KL}}^{\alpha,r}(l)
\]

中位尺度：

\[
M_{\alpha,r}
=
\left|
\operatorname{median}_l
S_{\mathrm{KL}}^{\alpha,r}(l)
\right|
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

该 `alpha × repeat` 判定为近似常数的无信息组，不参与稳健分数平均。

初始阈值：

```text
epsilon_abs = 1e-8
epsilon_rel = 1e-3
```

最终阈值必须在 `EVQA-pilot500 × BLIP2-OPT-2.7B` pilot 后冻结。

有效噪声组：

\[
\mathcal G_{\mathrm{valid}}
=
\left\{
(\alpha,r):
\text{该组动态范围有效}
\right\}
\]

最终稳健分数只对有效组平均：

\[
S_{\mathrm{KL}}^{robust}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
\hat S_{\mathrm{KL}}^{\alpha,r}(l)
\]

原始平均 KL：

\[
S_{\mathrm{KL}}^{rawmean}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
S_{\mathrm{KL}}^{\alpha,r}(l)
\]

若：

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
relative_dynamic_range
exclusion_reason
```

## 7. 候选层生成

### 7.1 Direct Top-K

主候选层：

\[
\mathcal C_{\mathrm{KL\text{-}Direct},K}
=
\operatorname{TopK}_{l}
S_{\mathrm{KL}}^{robust}(l)
\]

必须分别输出：

```text
Top-3
Top-5
full layer scores
full layer ranking
```

排序规则：

```text
primary key = robust KL score, descending
tie break 1 = raw mean KL score, descending
tie break 2 = mean_rank, ascending
tie break 3 = layer index, ascending
```

### 7.2 Raw 与 Clean 候选层

即使主方法正常情况下不会产生重复层或越界层，也必须保存两类结果：

```text
raw_candidate_layers
clean_candidate_layers
```

清洗规则：

```text
1. 保留 raw_candidate_layers 原始输出；
2. 删除重复层；
3. 删除不在 valid_layer_index_range 内的非法层；
4. 记录 dedupe_or_filter_reason；
5. 不使用其他方法 fallback 补层。
```

如果清洗后不足 Top-K，则保留不足状态：

```text
status = low_confidence
failure_reason = insufficient_valid_layers_after_cleaning
```

## 8. 输出文件

### 8.1 `perturb_kl_scores_long.csv`

每一行对应一个 `dataset × subset × model × layer × alpha × repeat` 的原始结果：

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

该长表是审计主表的依据，必须完整保存。即使某个 `alpha × repeat` 被判定为无信息组，也要保留原始 KL、动态范围和排除原因。

### 8.2 `perturb_kl_layer_scores.csv`

每一行是一个 `dataset × model × layer` 的最终层分数：

```text
dataset
subset
model
method
variant
key_mode
layer
score_kl_robust
score_kl_raw_mean
rank
raw_rank
rank_robust
mean_rank
rank_std
rank_percentile_mean
valid_group_count
invalid_group_count
localization_sample_count
manifest_sample_count
base_valid_sample_count
common_valid_sample_count
coverage_ratio
processed_sample_count
per_layer_processed_count
excluded_sample_ids
noise_scales
repeat_count
target_mask_hash
visual_token_rule
seed_method
zero_noise_max_kl
zero_noise_mean_kl
zero_noise_pass
clean_repeat_max_kl
clean_repeat_pass
spearman_between_repeats_mean
robust_top5_percentile_top5_overlap
dtype
quantization
config_hash
localization_wall_time_seconds
peak_gpu_memory_mb
forward_pass_count
status
failure_reason
score_source_file
```

固定字段值：

```text
method = Perturb-KL-Direct-AltSeq
variant = direct
key_mode = alt_sequence
perturb_scope = visual_tokens
candidate_conversion = Direct
cross_model_score_comparable = false
```

### 8.3 `perturb_kl_stability_report.csv`

每一行记录一个 `dataset × model × alpha` 的重复稳定性：

```text
dataset
subset
model
alpha
repeat_count
valid_repeat_pair_count
spearman_between_repeats_by_alpha
robust_top5
percentile_top5
top5_overlap
valid_group_count
invalid_group_count
coverage_ratio
status
failure_reason
```

排名百分位诊断分数：

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

主候选仍按 `score_kl_robust` 排序，`rank_percentile_mean` 只用于稳定性诊断。

如果以下情况之一成立，标记为 `low_confidence`：

```text
valid_group_count < 50% of total groups
mean repeat Spearman < predefined threshold
robust Top-5 与 percentile Top-5 重叠过低
coverage_ratio below threshold
```

阈值在 pilot 后冻结。

### 8.4 `perturb_kl_candidate_layers_topk.csv`

每一行是一个 Top-K 候选层：

```text
dataset
subset
model
method
variant
top_k
rank
layer
score_kl_robust
score_kl_raw_mean
raw_candidate_layers
clean_candidate_layers
dedupe_or_filter_reason
selection_source
candidate_conversion
status
failure_reason
```

### 8.5 回填到总表

完成后将 Top-3 / Top-5 回填到：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

建议单独小节：

```text
### Perturb-KL-Direct
```

表头：

```text
| Dataset | Model | Top-3 raw | Top-3 clean | Top-5 raw | Top-5 clean | Status |
```

如果另做 `Perturb-KL-Pre-AltSeq`，必须放在附加/消融小节，不得混入 Direct 主表。

## 9. 运行顺序

推荐顺序：

1. 先跑 `EVQA-pilot500 × BLIP2-OPT-2.7B` 作为 pilot；
2. 检查稳定哈希、common noise、visual-token hook、zero-noise、clean repeat、KL finite、样本覆盖一致、动态范围、repeat 稳定性、Top-K 合法；
3. 冻结 `epsilon_abs`、`epsilon_rel`、Spearman/coverage 阈值，以及 `alpha=3` 是否进入主分数；
4. 再跑剩余 6 个模型的 `EVQA-pilot500`；
5. 再跑 `MMKE-visual` 7 个模型；
6. 最后跑 `MMKE-entity` 7 个模型。

若服务器正在进行 adapter 训练，Perturb-KL 不得抢占同一张物理 GPU。必须使用空闲 GPU、单独 Slurm job，或等待训练任务完成后再运行。

## 10. 失败状态与处理

| Failure reason | 处理 |
|---|---|
| `visual_token_or_hook_test_failed` | 停止该模型该数据集，修 wrapper 后重跑 |
| `empty_visual_span` | 不允许 fallback，记录失败样本 |
| `nonfinite_kl_score` | 跳过该样本/层/alpha/repeat，记录明细；若比例过高则该组合 unavailable |
| `cuda_oom` | 降 batch size 或逐层运行，不改变公式 |
| `no_informative_alpha_repeat_group` | 无有效动态范围组，该组合 unavailable |
| `near_constant_layer_scores_for_alpha_repeat` | 该 alpha/repeat 不参与 robust score，长表记录排除原因 |
| `inconsistent_sample_coverage_across_layers` | 统一样本集合或重跑；无法一致则 low confidence |
| `zero_noise_kl_nonzero` | 检查 dropout、cache、hook、输入一致性 |
| `clean_repeat_kl_nonzero` | 检查 eval 模式、随机性和 clean cache |
| `missing_image` | 样本 manifest 记录 skip_reason，不参与 N |
| `invalid_layer_index` | raw 保留，clean 删除 |

## 11. 正式运行检查清单

- [ ] 该 `dataset × model` 的 `model_registry.yaml` 已完成。
- [ ] 该 `dataset × model` 的 `sample_manifest.csv` 已完成。
- [ ] visual-token 与 hook 单元测试通过。
- [ ] 使用完整 `alt` 序列作为 KL target。
- [ ] teacher forcing shift 与 target mask 正确。
- [ ] 扰动只加在 visual tokens。
- [ ] 扰动位置与 adapter 候选层 hook 位置一致。
- [ ] Hook 正确处理 tuple 输出，只替换第一个 hidden state。
- [ ] Hook 不做原地修改，使用 clone 或函数式替换。
- [ ] KL 方向为 `clean || perturbed`。
- [ ] KL 使用 float32 log-space 完整 vocabulary。
- [ ] 噪声尺度为 `[0.1, 0.5, 1, 3]`。
- [ ] `alpha=0` sanity check 通过且不进入 robust score。
- [ ] `alpha=3` 是否进入主分数已在 pilot 后冻结。
- [ ] 使用 SHA-256 稳定哈希种子。
- [ ] 主实验种子不包含 layer。
- [ ] 不同层使用相同基础噪声方向。
- [ ] hidden 标准差在 detached clean visual hidden 上计算。
- [ ] 设置 `unbiased=false` 与 `epsilon_sigma=1e-6` 安全下限。
- [ ] 排除近似常数的无信息噪声组。
- [ ] robust score 只对有效组平均。
- [ ] 所有层使用同一有效样本集合。
- [ ] 保存 `perturb_kl_scores_long.csv`。
- [ ] 保存 repeat 间 Spearman 与 percentile rank 诊断。
- [ ] clean 分布只计算一次并通过重复一致性测试。
- [ ] 输出 Top-3、Top-5、full layer scores、full ranking。
- [ ] raw 候选层和 clean 候选层都保留。
- [ ] 越界层、重复层、不足 Top-K 均记录原因。
- [ ] 不用其他方法候选层做 fallback。
- [ ] Direct 主表与 Pre 消融表分开。

## 12. 论文表述

可写为：

> Perturb-KL-Direct estimates layer sensitivity by injecting Gaussian noise into the visual-token hidden states at each decoder block output and measuring the KL divergence between the clean and perturbed output distributions on the complete target answer sequence. Layers are ranked by a robust KL score averaged over multiple noise scales and random seeds. The top-ranked layers are directly used as candidate adapter insertion layers.

中文表述：

> Perturb-KL-Direct 通过在每个 decoder block 输出处的 visual-token hidden states 上加入高斯扰动，测量完整目标答案序列上 clean 输出分布与 perturbed 输出分布之间的 KL 差异。每层得分由多噪声尺度、多随机种子的稳健 KL 分数组成，分数最高的 Top-K 层直接作为 adapter 候选插入层。
