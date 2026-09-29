# Visual Causal Restoration（视觉因果恢复）实验手册

> 版本：v1.0  
> 目的：指导在 VLM decoder 侧测量“某一层视觉表征对目标答案生成的因果恢复作用”。  
> 定位：这是一个 **causal restoration analysis / 因果恢复分析实验**，不是最终 Adapter 编辑层真值。

---

## 0. 前置执行结论

本手册可以指导 `7 models x 3 datasets` 的 `CMA-Direct / Visual Causal Restoration` 候选层实验，但有一个硬性前提：

> 先完成每个模型的 decoder block path、visual token span 和 restore hook 验证，再按 `pilot -> 跨架构验证 -> 全量运行` 三步执行。

未完成 hook path、visual span 或 restore hook 验证的模型，不得写入正常 `done`，必须标记为 `hook_failed`、`visual_span_failed` 或对应失败状态。

执行顺序固定为：

1. `pilot`：先跑 `llava-v1.5-7b + EVQA-pilot500` 小样本，验证基本流程。
2. `跨架构验证`：再跑 `llava-v1.5-7b / blip2-opt-2.7b / paligemma-3b`，确认 projector、Q-Former、image-token 架构都能稳定定位 visual span。
3. `全量运行`：最后扩展到 7 个模型和 3 个数据集。

---

## 1. 实验目标

本实验用于回答：

> 在视觉信息被污染的情况下，如果恢复某一层的干净视觉 hidden states，模型的目标答案分布能否从污染状态恢复？

换句话说，本实验测量第 `l` 层视觉表征是否对目标答案生成具有因果恢复作用。

需要注意：

- 该实验不是直接寻找最佳 Adapter 编辑层；
- 它测量的是“恢复干净视觉表征后能否挽救输出”；
- 浅层恢复通常拥有更长的下游传播路径，因此恢复分数可能偏向浅层；
- 实验结果应作为 **因果恢复型表征干预基线** 或分析实验，而不是编辑适宜性的最终判断标准。

---

## 2. 与 Perturb-KL 的区别

| 方法 | 起点 | 操作 | 衡量内容 |
|---|---|---|---|
| Perturb-KL | 干净状态 | 在某一层视觉 hidden states 加噪 | 该层被破坏后输出变化多大 |
| Visual Causal Restoration | 污染状态 | 在某一层恢复干净视觉 hidden states | 该层恢复后输出能否被挽救 |

可以理解为：

```text
Perturb-KL: Clean -> Damage
Causal Restoration: Corrupt -> Rescue
```

---

## 3. 核心实验流程

对每个样本 `(x_v, x_t, y)`，其中：

- `x_v`：图像输入；
- `x_t`：文本问题或 prompt；
- `y=(y_1,...,y_T)`：目标答案序列。

执行三类前向计算：

1. **Clean forward**：正常输入，缓存干净 hidden states；
2. **Corrupt forward**：污染视觉输入，得到污染输出；
3. **Restore forward**：仍使用污染输入，但在指定层恢复 clean hidden states，观察输出恢复程度。

---

## 4. Hook 位置定义

建议统一 hook 在：

> decoder block `l` 输出之后、decoder block `l+1` 之前。

即：

```math
H^l = Block_l(H^{l-1})
```

然后在 `H^l` 上进行缓存、恢复或评分。

### 为什么这样定义？

因为你的视觉编辑 Adapter 候选层也是作用在某层 decoder 输出后的视觉 hidden states 上。这样因果恢复实验与 Adapter 候选层实验使用相同的层空间和 hook 位置，便于对比。

---

## 5. 视觉 token 范围

不同 VLM 的视觉 token 不一定出现在 decoder 序列最前面，因此主实验不得默认视觉 token 范围为 `1:N_v`。

设进入语言 decoder 后的 hidden states 为：

```math
H^l \in R^{B \times T \times d}
```

设视觉 token 位置集合为：

```math
V_i \subseteq \{0,\ldots,T_i-1\}
```

则第 `l` 层视觉 hidden states 定义为：

```math
H_{i,v}^l = H_i^l[:, V_i, :]
```

其中 `V_i` 必须由各模型的 processor、chat template 或 input embedding 拼接逻辑显式确定，不默认等于 `1:N_v`。

每条样本必须保存：

```text
visual_start
visual_end
num_visual_tokens
visual_token_indices
```

如果无法确定视觉 token 位置，样本或模型状态标记为：

```text
visual_span_failed
```

不得 fallback 到全部 prompt token、文本 token 或整层 hidden states。主实验只恢复 `visual_token_indices` 对应位置，不恢复文本 token、prompt token 或 teacher-forcing answer token。

---

## 6. Step 1：Clean Forward

正常输入 `(x_v, x_t)`，执行一次完整前向传播。

缓存每一层的视觉 hidden states：

```math
H_{i,v}^{l,clean} = H_i^{l,clean}[:, V_i, :]
```

同时计算 clean 状态下目标答案序列平均 log probability：

```math
s_clean = (1/T) * sum_t log p_clean(y_t | x_v, x_t, y_<t)
```

### 实现注意

建议使用 teacher-forcing 方式计算完整目标答案序列的 log probability。若样本有 `alt` / `target_new` 字段，主实验优先使用它作为目标答案：

- 输入 prompt + target answer；
- 对 answer token 位置取 logits；
- 计算每个目标 token 的 log probability；
- 对 answer token 求平均。

不建议只看第一个答案 token，因为多 token 答案会被低估或不稳定。

---

## 7. Step 2：Corrupt Forward

构造污染视觉输入。

推荐污染位置为 **decoder 输入端的视觉 embeddings**，而不是每一层分别加噪。

```math
E_v_corrupt = E_v + epsilon
epsilon ~ N(0, sigma^2 I)
```

污染后的 decoder 输入为：

```math
[E_v_corrupt; E_t]
```

执行污染前向，计算目标答案平均 log probability：

```math
s_corrupt = (1/T) * sum_t log p_corrupt(y_t | x_v_corrupt, x_t, y_<t)
```

---

## 8. 样本过滤规则

为了保证污染确实破坏了模型对目标答案的支持，需要过滤样本。

保留满足以下条件的样本：

```math
s_clean > s_corrupt + delta
```

建议初始设置：

```yaml
delta_logprob: 0.05
```

如果过滤后样本太少，可以降低为：

```yaml
delta_logprob: 0.01
```

如果污染太弱，很多样本无法被破坏，应增大噪声强度。

---

## 9. Step 3：Restore Forward

对于每一层 `l`，仍然使用污染视觉输入：

```math
[E_v_corrupt; E_t]
```

但在 decoder block `l` 输出后，将污染状态下该层视觉 hidden states 替换为 clean forward 中缓存的视觉 hidden states：

```math
H_v^{l,corrupt} <- H_v^{l,clean}
```

然后继续执行后续 decoder layers，得到恢复状态下的目标答案平均 log probability：

```math
s_restore(l) = (1/T) * sum_t log p_restore(l)(y_t | x_v_corrupt, x_t, y_<t)
```

### 9.1 主实验恢复范围说明

主实验只恢复指定 decoder 层输出后的视觉 token hidden states，而不是恢复整层 hidden states。

设第 `l` 层输出 hidden states 为：

```math
H^{l,corrupt} = [H_v^{l,corrupt}; H_t^{l,corrupt}]
```

其中 `H_v` 表示视觉 token hidden states，`H_t` 表示文本 token、prompt token 和 teacher-forcing answer token 的 hidden states。

恢复操作定义为：

```math
H_v^{l,corrupt} \leftarrow H_v^{l,clean}
```

而非：

```math
H^{l,corrupt} \leftarrow H^{l,clean}
```

恢复后的状态为：

```math
H^{l,restore} = [H_v^{l,clean}; H_t^{l,corrupt}]
```

本文不恢复整层 hidden states，因为整层恢复会同时恢复文本和答案 token 表征，使实验不再专门衡量视觉表征的因果恢复作用。

---

## 10. 主指标：Causal Restoration Score

第 `l` 层视觉表征的因果恢复分数定义为：

```math
CR(l) = (s_restore(l) - s_corrupt) / (s_clean - s_corrupt + eps)
```

建议：

```yaml
epsilon: 1.0e-8
```

### 指标解释

| CR 值 | 含义 |
|---|---|
| `CR(l) ≈ 0` | 恢复该层几乎不能挽救输出 |
| `0 < CR(l) < 1` | 部分恢复 |
| `CR(l) ≈ 1` | 基本恢复到 clean 状态 |
| `CR(l) > 1` | 恢复后比 clean 更支持目标答案，可能是过恢复或噪声现象 |
| `CR(l) < 0` | 恢复该层反而进一步降低目标答案支持 |

---

## 11. 辅助指标：KL Restoration Score

除了 log probability 恢复，也可以使用 KL 恢复率。

首先计算 clean 与 corrupt 输出分布之间的 KL：

```math
KL_corrupt = D_KL(p_clean || p_corrupt)
```

再计算 clean 与 restore 输出分布之间的 KL：

```math
KL_restore(l) = D_KL(p_clean || p_restore(l))
```

定义 KL 恢复率：

```math
KCR(l) = (KL_corrupt - KL_restore(l)) / (KL_corrupt + eps)
```

### 指标解释

| KCR 值 | 含义 |
|---|---|
| 越接近 1 | 恢复后输出分布越接近 clean |
| 接近 0 | 恢复几乎没有作用 |
| 小于 0 | 恢复后输出分布比 corrupt 更偏离 clean |

### 建议

主结果建议使用 `CR`，`KCR` 作为辅助分析。

原因：

- `CR` 更直接对应目标答案概率是否恢复；
- `KCR` 更关注整体分布形状，可能受到非目标 token 概率变化影响。

---

## 12. 噪声设置

推荐从以下相对噪声强度开始：

```yaml
relative_noise_alpha_list:
  - 0.5
  - 1.0
  - 2.0
```

使用视觉 embedding 标准差进行尺度归一：

```python
noise = alpha * visual_embeds.std() * torch.randn_like(visual_embeds)
visual_embeds_corrupt = visual_embeds + noise
```

正式全量运行前应先执行第 31 节的 noise calibration。`[0.5, 1.0, 2.0]` 是默认候选范围，不是所有模型/数据集必须固定使用的唯一强度。不同模型视觉表征尺度差异较大，如果不做预校准，可能出现污染过弱导致有效样本过少，或污染过强导致恢复分数几乎只偏向浅层。

---

## 13. 多随机种子

由于噪声实验存在随机性，建议每个样本每个噪声强度重复多个 seed：

```yaml
noise_seeds:
  - 0
  - 1
  - 2
```

最终对 seed 求平均：

```math
CR_bar(l) = (1/S) * sum_s CR_s(l)
```

---

## 14. 聚合方式

对每个模型、每个数据集、每个层 `l`，聚合所有有效样本：

```math
Score(l) = mean_{i in D_valid} CR_i(l)
```

同时报告：

- mean；
- standard deviation；
- standard error；
- bootstrap 95% confidence interval；
- valid sample count。

---

## 15. 层排名与候选层输出

根据聚合后的分数进行排序：

```text
Rank = argsort_l(Score(l), descending=True)
```

输出：

```yaml
top_k:
  - 3
  - 5
```

保存：

- Top-3 causal restoration layers；
- Top-5 causal restoration layers；
- 每层平均 CR；
- 每层平均 KCR；
- 每层有效样本数；
- 每层标准误；
- 每层置信区间。

---

## 16. 推荐输出文件

建议每个模型、每个数据集输出以下文件：

```text
visual_causal_restoration/
├── {model_name}/{dataset_name}/
│   ├── layer_scores.csv
│   ├── sample_scores.parquet
│   ├── top_layers.json
│   ├── config.yaml
│   ├── cr_curve.png
│   ├── kcr_curve.png
│   └── summary.md
```

### layer_scores.csv 字段

```csv
model,dataset,layer,noise_alpha,num_samples,valid_samples,valid_ratio,cr_raw_mean,cr_clip01_mean,cr_std,cr_se,cr_ci_low,cr_ci_high,cr_gt1_ratio,cr_lt0_ratio,nonfinite_count,kcr_mean,kcr_std,kcr_se,kcr_ci_low,kcr_ci_high,shallow_middle_deep_group,status
```

### sample_scores.parquet 字段

```text
sample_id
model
dataset
layer
noise_alpha
seed
visual_start
visual_end
num_visual_tokens
visual_token_indices_hash
answer_start
answer_end
answer_token_count
s_clean
s_corrupt
s_restore
clean_corrupt_gap
cr
cr_clip01
kl_corrupt
kl_restore
kcr
is_valid
invalid_reason
```

### top_layers.json 示例

```json
{
  "model": "llava-v1.5-7b",
  "dataset": "E-VQA",
  "metric": "CR",
  "top3": [0, 1, 2],
  "top5": [0, 1, 2, 3, 4],
  "note": "Causal restoration score may favor shallow layers due to longer downstream propagation."
}
```

---

## 17. 推荐配置文件

```yaml
experiment_name: visual_causal_restoration

hook_position: block_output
restore_target: visual_tokens_only

runtime:
  model_eval: true
  torch_no_grad: true
  use_cache: false
  deterministic: true
  do_sample: false
  use_generate: false

score_metrics:
  primary: CR
  auxiliary:
    - KCR

answer_scoring:
  mode: teacher_forcing
  token_mask: target_answer_tokens
  reduction: mean_logprob

corruption:
  location: decoder_visual_input_embeddings
  type: gaussian
  relative_to_visual_std: true
  seed_key: dataset/model/sample_id/alpha/seed
  alpha_list:
    - 0.5
    - 1.0
    - 2.0
  seeds:
    - 0
    - 1
    - 2

sample_filter:
  min_clean_corrupt_gap: 0.05
  min_valid_samples: 30
  min_valid_ratio: 0.2

noise_calibration:
  enabled: true
  pilot_samples: 50
  candidate_alpha_list: [0.1, 0.3, 0.5, 1.0, 2.0]
  target_valid_ratio_range: [0.3, 0.8]
  delta_logprob: 0.05

restore:
  layers: all_decoder_layers
  token_scope: visual_tokens_only
  operation: replace_corrupt_visual_slice_with_clean_visual_slice

aggregation:
  sample_average: mean
  seed_average: mean
  bootstrap_ci: true
  bootstrap_samples: 1000
  primary_score: cr_raw_mean
  diagnostic_scores:
    - cr_clip01_mean
    - kcr_mean
    - cr_gt1_ratio
    - cr_lt0_ratio
  top_k:
    - 3
    - 5

diagnostics:
  shallow_bias_check: true
  shallow_layers: first_20_percent
  middle_layers: middle_40_percent
  deep_layers: last_20_percent

outputs:
  save_layer_scores: true
  save_sample_scores: true
  save_curves: true
  save_summary: true
  save_visual_span_log: true
  save_hook_mapping: true
```

---

## 18. 伪代码

```python
for model in models:
    for dataset in datasets:
        for sample in dataset:

            # 1. Clean forward
            clean_outputs = forward_with_cache(
                model=model,
                sample=sample,
                corrupt_visual=False,
                cache_visual_hidden=True
            )
            target_answer = sample.alt or sample.target_new or sample.answer
            s_clean = compute_answer_mean_logprob(clean_outputs, target_answer)
            clean_visual_cache = clean_outputs.visual_hidden_by_layer

            for alpha in noise_alpha_list:
                for seed in noise_seeds:

                    # 2. Corrupt forward
                    noise = make_visual_noise(sample, alpha=alpha, seed=seed)
                    corrupt_outputs = forward_with_cache(
                        model=model,
                        sample=sample,
                        visual_noise=noise,
                        cache_visual_hidden=False
                    )
                    s_corrupt = compute_answer_mean_logprob(corrupt_outputs, target_answer)

                    # 3. Filter sample
                    is_valid = (s_clean > s_corrupt + delta_logprob)
                    if not is_valid:
                        continue

                    for layer in decoder_layers:

                        # 4. Restore layer
                        restore_outputs = forward_with_restore(
                            model=model,
                            sample=sample,
                            visual_noise=noise,
                            restore_layer=layer,
                            restore_visual_hidden=clean_visual_cache[layer]
                        )
                        s_restore = compute_answer_mean_logprob(
                            restore_outputs,
                            target_answer
                        )

                        # 5. Compute CR
                        cr = (s_restore - s_corrupt) / (
                            s_clean - s_corrupt + eps
                        )

                        # 6. Optional KCR
                        kl_corrupt = compute_kl(clean_outputs, corrupt_outputs)
                        kl_restore = compute_kl(clean_outputs, restore_outputs)
                        kcr = (kl_corrupt - kl_restore) / (kl_corrupt + eps)

                        save_sample_score(...)
```

---

## 19. 关键实现细节

### 19.1 Clean cache 必须与 corrupt restore 使用同一 token 对齐

恢复时必须确保：

```text
H_v^{l,clean}
```

和

```text
H_v^{l,corrupt}
```

具有完全相同的 shape 和视觉 token 顺序。

如果模型使用 Q-Former 或视觉压缩模块，应在进入 decoder 后的视觉 token 维度上做恢复，而不是在原始图像 patch 上做恢复。

---

### 19.2 不建议污染文本 token

本实验关注视觉表征的因果恢复作用，所以污染范围应限制在视觉侧。

不建议污染视觉 + 文本全部 token，否则无法判断恢复视觉 hidden states 的效果来自视觉修复还是文本侧扰动残留。

---

### 19.3 不建议每层分别加噪再恢复

本实验采用统一的上游污染输入：

```math
E_v_corrupt = E_v + epsilon
```

然后测试恢复不同层的 clean hidden states。

不建议采用：

```text
在第0层加噪，恢复第0层；
在第1层加噪，恢复第1层；
...
```

因为这样每层污染条件不同，层间分数不可比，而且会退化成类似 Perturb-KL 的逐层扰动实验。

---

### 19.4 恢复全部视觉 token 会产生浅层偏置

如果恢复范围是全部视觉 token，那么浅层恢复通常有更多后续层重新利用干净视觉信息，因此分数可能偏高。

结果解释时必须写明：

> CR/KCR measures causal restoration capacity under visual corruption, not adapter editability itself.

---

## 20. 可选变体

### 20.1 目标区域视觉 token 恢复

如果有目标物体 bbox 或 attention-based region，可以只恢复目标区域视觉 token：

```math
H_{v,R}^{l,corrupt} <- H_{v,R}^{l,clean}
```

优点：

- 更接近视觉对象级因果定位；
- 浅层恢复全部视觉信息的问题较弱。

缺点：

- 需要区域标注或可靠的区域映射；
- 不同模型视觉 token 对齐更复杂。

---

### 20.2 单视觉 token 恢复

逐个视觉 token 恢复：

```math
h_j^{l,corrupt} <- h_j^{l,clean}
```

得到 token × layer 因果恢复图。

优点：

- 更接近经典 Causal Tracing；
- 可以分析具体视觉 patch 的因果作用。

缺点：

- 计算成本高；
- 需要将 token-level 分数聚合为 layer-level 分数；
- 对不同 VLM 架构不容易统一。

---

### 20.3 Attention output 或 MLP output 恢复

可以恢复：

- block output；
- attention output；
- MLP output。

但为了与你的 Adapter 插入实验一致，主实验建议使用：

```yaml
restore_target: block_output_visual_hidden
```

---

## 21. 结果解释模板

### 如果浅层 CR 最高

> 浅层视觉表征恢复后，干净视觉信息仍可通过更多后续 attention 和 MLP 模块传播至目标答案 token，因此具有更强的恢复能力。这说明浅层视觉状态在污染条件下对答案恢复具有较强因果作用，但该结果也可能受到剩余传播深度的影响，并不直接表明浅层是最佳 Adapter 编辑层。

### 如果中层 CR 最高

> 中层视觉表征恢复带来最大的答案概率恢复，说明视觉信息可能在该阶段与文本查询语义发生关键融合。相比浅层，中层恢复可能更接近已经语义化的视觉表征；相比深层，中层仍保留足够的下游传播路径，因此表现出较强的因果恢复作用。

### 如果深层 CR 很低

> 深层视觉表征恢复后，后续可用于将视觉信息混合至目标答案 token 的 attention 层数较少，因此恢复作用有限。这与 decoder-only VLM 中视觉 token 需要通过后续自注意力影响文本 token 的传播机制一致。

---

## 22. 论文英文描述

```text
We further conduct a visual causal restoration analysis to examine whether visual representations at a given decoder layer causally support target answer generation under corrupted visual inputs. For each sample, we first run a clean forward pass and cache the visual hidden states at every decoder layer. We then corrupt the visual input embeddings with Gaussian noise and measure the degradation in the target answer log-likelihood. During the restoration pass, the model still receives the corrupted visual input, but the visual hidden states at a selected layer are replaced with their clean counterparts. The causal restoration score is defined as the fraction of the corrupted-to-clean log-likelihood gap recovered by this layer-wise intervention. Higher scores indicate that restoring the visual representations at that layer more strongly rescues the target answer distribution. Since restoring earlier layers leaves more downstream computation for the restored signal to propagate, we use this analysis as a causal restoration diagnostic rather than as a ground-truth measure of adapter editability.
```

---

## 23. 中文论文描述

```text
为分析不同decoder层视觉表征对目标答案生成的因果作用，本文进一步设计视觉因果恢复实验。具体而言，首先在正常输入下执行干净前向传播，并缓存各decoder层视觉token对应的hidden states。随后在decoder输入端对视觉embeddings加入高斯噪声，构造污染前向传播，并测量目标答案序列对数概率的下降。在恢复阶段，模型仍接收污染后的视觉输入，但在指定decoder层处，将该层视觉hidden states替换为干净前向中缓存的对应状态，并继续执行后续层计算。本文将恢复后目标答案对数概率相对于污染状态的提升，占污染状态到干净状态差距的比例，定义为该层的因果恢复分数。分数越高，说明恢复该层视觉表征越能挽救目标答案分布。需要注意的是，较浅层恢复后仍具有更长的下游传播路径，因此该指标可能受到剩余传播深度影响。本文将其作为视觉表征因果恢复诊断，而不将其视为Adapter编辑适宜性的真实标准。
```

---

## 24. 常见问题

### Q1：这个实验是不是 CMA/Causal Tracing？

它是受 Causal Tracing 启发的视觉因果恢复实验，但不是经典文本 Causal Tracing 的严格复现。

经典 Causal Tracing 通常在文本主体词上构造污染，并恢复 token × layer 状态。这里是面向 VLM 视觉 token 和 Adapter 插入位置设计的恢复实验。

建议名称：

```text
Visual Causal Restoration
```

不要直接命名为：

```text
CMA
```

除非你完整实现了经典污染—恢复流程并与原方法保持一致。

---

### Q2：能不能用这个实验直接选 Adapter 层？

不建议直接作为最终层选择标准。

它可以作为：

- 因果恢复分析；
- 表征干预基线；
- 解释浅层/中层视觉表征作用的辅助实验。

真正判断 Adapter 层优劣，仍应以真实 Adapter 训练后的 Reliability、Generality、Locality 为准。

---

### Q3：如果结果总是第一层最高怎么办？

这不是实验失败，而是说明恢复较浅层具有更长的下游传播路径。

需要在结果中明确：

> 该实验测量恢复能力，不直接测量编辑适宜性。

如果想减轻浅层偏置，可以尝试：

- 只恢复目标区域视觉 token；
- 对恢复分数加入深度校正；
- 比较同一层恢复后立即输出影响与最终输出影响；
- 将其作为分析实验，而非主定位方法。

---

### Q4：为什么不直接污染某一层再恢复某一层？

因为那样每一层的污染条件都不同，不再是统一因果恢复实验。

更重要的是，这会退化为逐层扰动敏感性分析，和 Perturb-KL 高度重合。

本实验应保持统一污染源，只改变恢复层。

---

## 25. 最小可行实验（Pilot）

为控制成本，建议先做最小可行版本：

```yaml
models:
  - llava-v1.5-7b

datasets:
  - E-VQA

sample_size: 100

noise_alpha_list:
  - 1.0

noise_seeds:
  - 0

restore_layers: all_decoder_layers

metric:
  primary: CR
  auxiliary: KCR
```

如果 pilot 能跑通，再扩展到：

```yaml
sample_size: 500
noise_alpha_list: [0.5, 1.0, 2.0]
noise_seeds: [0, 1, 2]
models: selected_vlms
datasets: selected_datasets
```

---

## 26. 实验完成后检查清单

完成后重点检查：

- clean log probability 是否合理；
- corrupt log probability 是否明显下降；
- 有效样本比例是否过低；
- CR 是否大量大于 1；
- CR 是否全部集中在 L0/L1；
- KCR 与 CR 趋势是否一致；
- 不同噪声强度下排名是否稳定；
- 不同 seed 下排名是否稳定；
- 是否存在某些模型视觉 token hook 位置错误。

---

## 27. 作为论文附录实验的建议标题

```text
Appendix X. Visual Causal Restoration Analysis
```

建议核心结论写法：

```text
This analysis is used to examine the causal recoverability of visual representations under corrupted visual inputs. It is not used as the primary edit-layer selector because restoration scores may be confounded by the remaining downstream propagation depth.
```

中文：

```text
该实验用于分析污染视觉输入下不同层视觉表征的因果恢复能力。由于恢复分数可能受到后续剩余传播深度的影响，本文不将其作为主要编辑层选择方法，而将其作为候选层机理分析的补充实验。
```

---

## 28. 最终推荐表述

本实验最终应定位为：

> Visual Causal Restoration measures how much restoring clean visual hidden states at a given decoder layer can rescue target answer generation from a corrupted visual input.

中文：

> 视觉因果恢复实验衡量的是，在视觉输入被污染的条件下，恢复某一decoder层的干净视觉 hidden states，能够在多大程度上挽救目标答案生成。

不要写成：

> 该实验直接找到最佳视觉编辑层。

应该写成：

> 该实验提供关于视觉表征因果恢复能力的辅助证据，并与真实 Adapter 编辑实验共同分析候选层选择的合理性。

---

## 29. 用于 CMA 候选层实验的补充规范

本节补充的是把 `Visual Causal Restoration / CMA` 真正用于 `7 models x 3 datasets` 候选层定位时还缺少的实验口径。前文已经定义了 clean / corrupt / restore 和 `CR/KCR`，但还需要把数据、层空间、排序、清洗、失败状态和回填格式固定下来，否则结果很难和其他候选层方法对齐。

### 29.1 实验定位

`CMA-Direct` 或 `Visual-Causal-Restoration-Direct` 可以作为候选层定位方法之一，但必须在结果表中与 `Middle-layer Prior`、`SaLEM`、`Perturb-KL-Direct`、`Ours-Direct` 等方法分开登记。

建议名称：

```text
CMA-Direct
```

不建议写成：

```text
best edit layer found by causal restoration
```

原因是 CMA 衡量的是污染视觉输入后恢复某层 clean visual hidden states 的输出挽救能力，不等价于 Adapter 训练后的编辑性能。

### 29.2 数据集与 split

候选层计算统一使用训练侧数据，不使用 eval/test：

| Dataset name | Split / source | 备注 |
|---|---|---|
| `EVQA-pilot500` | pilot500 train | 与 pilot500 top-3 并集训练口径一致 |
| `MMKE-visual` | visual train | 使用 visual 子集训练样本 |
| `MMKE-entity` | entity train | 使用 entity 子集训练样本 |

每条样本必须记录：

- `sample_id`
- `dataset`
- `model`
- `image_path`
- `prompt/question`
- `target_answer`
- `alt/target_new`，如果当前任务使用改写目标答案，则优先用它作为 `target_answer`
- `is_valid`
- `invalid_reason`

如果图片缺失、prompt 为空、目标答案为空、tokenizer 无法产生 answer token，样本不得进入有效样本统计。

### 29.3 模型与合法层空间

层号必须落在各模型文本 decoder block 的合法范围内，hook 位置统一为 decoder block `l` 输出之后、block `l+1` 之前。

| Model | Legal layers |
|---|---|
| `blip2-opt-2.7b` | `L0-L31` |
| `instructblip-vicuna-7b` | `L0-L31` |
| `minigpt-4-vicuna-7b` | `L0-L31` |
| `llava-v1.5-7b` | `L0-L31` |
| `qwen2.5-vl-3b-instruct` | `L0-L35` |
| `paligemma-3b` | `L0-L17` |
| `smolvlm-1.7b` | `L0-L23` |

如果某模型实现中的模块命名与表中层号不一致，必须在运行日志中保存 `layer_id -> module_name` 映射。

### 29.4 统一腐蚀与恢复配置

同一个样本的 clean / corrupt / restore 必须共享同一套视觉 token 对齐和噪声配置。为了保证层间可比性，噪声 seed 不允许随层号变化。

推荐默认配置：

```yaml
corruption:
  location: decoder_visual_input_embeddings
  token_scope: visual_tokens_only
  noise_type: gaussian
  noise_alpha_list: [0.5, 1.0, 2.0]
  noise_seeds: [0, 1, 2]
  seed_key: dataset/model/sample_id/alpha/seed

restore:
  hook_position: decoder_block_output
  token_scope: visual_tokens_only
  operation: replace_corrupt_visual_hidden_with_clean_visual_hidden
  layers: all_legal_decoder_layers

scoring:
  primary: CR_mean
  auxiliary: KCR_mean
  teacher_forcing: true
  answer_score: mean_logprob_over_target_answer_tokens
```

### 29.5 有效样本过滤

每个样本先计算：

```math
gap = s_clean - s_corrupt
```

保留条件：

```math
gap > delta
```

默认：

```yaml
delta_logprob: 0.05
min_valid_samples: 30
min_valid_ratio: 0.2
```

如果有效样本少于阈值，不直接输出正常 top-k，状态标记为：

```text
low_valid_coverage
```

如果没有任何有效样本，状态标记为：

```text
no_valid_cma_sample
```

### 29.6 层分数聚合与候选层排序

主排序分数：

```math
Score(l) = mean_{i in D_valid, alpha, seed} CR_i(l, alpha, seed)
```

辅助分数：

```math
KCRScore(l) = mean_{i in D_valid, alpha, seed} KCR_i(l, alpha, seed)
```

排序规则：

1. `Score(l)` 从大到小排序。
2. 如果 `Score(l)` 并列，优先 `KCRScore(l)` 更大的层。
3. 如果仍并列，优先 `valid_samples(l)` 更多的层。
4. 如果仍并列，层号小的排前。

候选层输出：

```text
Top-3 = Score rank 前 3
Top-5 = Score rank 前 5
```

这里使用 `Direct` 口径，不做 pre-shift，不把 `Lk` 改成 `L(k-1)` 或 `L(k-2)`。

### 29.7 原始候选层与清洗后候选层

必须同时保存原始候选层和清洗后候选层。

清洗规则：

1. 去除重复层，保留第一次出现的位置。
2. 删除越界层。
3. 删除 hook 失败、有效样本数为 0 或分数为非有限值的层。
4. 不用其他层补齐被删除的位置，除非另行声明 `fill_from_next_rank=true`。

输出字段示例：

```json
{
  "method": "CMA-Direct",
  "model": "blip2-opt-2.7b",
  "dataset": "EVQA-pilot500",
  "raw_top3": ["L17", "L17", "L99"],
  "clean_top3": ["L17"],
  "raw_top5": ["L17", "L17", "L99", "L16", "L15"],
  "clean_top5": ["L17", "L16", "L15"],
  "removed_layers": [
    {"layer": "L17", "reason": "duplicate"},
    {"layer": "L99", "reason": "out_of_range"}
  ]
}
```

### 29.8 输出文件规范

每个 `dataset/model` 至少输出以下文件：

```text
cma_direct/
  {dataset}/
    {model}/
      config.yaml
      layer_scores.csv
      sample_layer_scores.jsonl
      candidates_raw.json
      candidates_clean.json
      status.json
      run.log
```

`layer_scores.csv` 字段：

```csv
dataset,model,layer,valid_samples,total_samples,valid_ratio,cr_mean,cr_std,cr_se,kcr_mean,kcr_std,kcr_se,score,rank,status
```

`status.json` 字段：

```json
{
  "dataset": "MMKE-visual",
  "model": "llava-v1.5-7b",
  "method": "CMA-Direct",
  "status": "done",
  "total_samples": 293,
  "valid_samples": 211,
  "top3_raw": ["L17", "L16", "L18"],
  "top3_clean": ["L17", "L16", "L18"],
  "top5_raw": ["L17", "L16", "L18", "L15", "L19"],
  "top5_clean": ["L17", "L16", "L18", "L15", "L19"],
  "failure_reason": ""
}
```

### 29.9 失败状态

统一使用以下状态，方便后续批量补跑：

| Status | 含义 |
|---|---|
| `done` | 候选层计算完成且有效样本数达标 |
| `low_valid_coverage` | 有效样本过少，结果只能作为诊断 |
| `no_valid_cma_sample` | 没有满足 clean-corrupt gap 的样本 |
| `missing_image` | 图像缺失导致样本不足 |
| `empty_target_answer` | 目标答案为空 |
| `hook_failed` | 指定层 hook 或 restore 失败 |
| `visual_span_failed` | 无法定位视觉 token span |
| `nonfinite_score` | 出现 NaN/Inf 分数 |
| `oom` | CUDA OOM |
| `env_error` | 模型环境或依赖错误 |
| `failed` | 其他未归类失败，需要查看日志 |

### 29.10 回填到总结果表

回填到：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

建议新增或更新独立小节：

```text
### 4.x CMA-Direct / Visual Causal Restoration
```

表头：

```markdown
| Dataset | Model | Raw Top-3 | Clean Top-3 | Raw Top-5 | Clean Top-5 | Valid Samples | Total Samples | Status |
|---|---|---|---|---|---|---:|---:|---|
```

如果 `raw_topk` 与 `clean_topk` 一致，也仍然保留两列，保证和其他方法的异常处理口径一致。

### 29.11 最小运行清单

正式跑 `7 models x 3 datasets` 前，先检查：

- 是否只占用空闲 GPU，不影响正在进行的训练任务；
- 是否启用 resume/skip done；
- 是否保存 `layer_id -> module_name`；
- 是否保存每个样本的 clean/corrupt gap；
- 是否保存 raw candidate 和 clean candidate；
- 是否把 `low_valid_coverage` 与 `done` 分开；
- 是否在结果表中注明 CMA 是辅助/候选层定位方法，而不是编辑性能真值。

---

## 30. 模型适配表：Hook 路径与 Visual Span 获取

正式实现前，每个模型必须在 `model_registry.yaml` 或运行日志中记录 decoder block path、visual span source 和 hook 输出 shape。下表中的 `待代码确认` 不是允许省略，而是表示必须由当前仓库 wrapper 实测后填入。

| Model | Decoder block path | Visual span source | 注意事项 |
|---|---|---|---|
| `blip2-opt-2.7b` | 待代码确认 | Q-Former 输出后进入 OPT 的视觉 query token | 不在原始 patch 上恢复 |
| `instructblip-vicuna-7b` | 待代码确认 | Q-Former 输出后的视觉 query token | 注意 Vicuna decoder 层路径 |
| `minigpt-4-vicuna-7b` | 待代码确认 | projected visual tokens | 需要确认视觉 token 在 prompt 中的位置 |
| `llava-v1.5-7b` | 待代码确认 | image token span / projector output | 不默认视觉 token 位于开头 |
| `qwen2.5-vl-3b-instruct` | 待代码确认 | processor/chat template 生成的 image token span | chat template 会影响 token 位置 |
| `paligemma-3b` | 待代码确认 | image token positions | 架构特殊，需单独验证 |
| `smolvlm-1.7b` | 待代码确认 | processor 返回的 image token positions | 需保存 token span 日志 |

每次运行必须保存：

```text
layer_id -> module_name
visual_token_indices
input_embeds.shape
hidden_states[layer].shape
clean_cache[layer].shape
restore_hidden.shape
```

如果 hook 路径或 visual span 不能确定，该组合不得写入正常 `done`，应标记为 `hook_failed` 或 `visual_span_failed`。

---

## 31. Noise Calibration：噪声强度预校准

正式运行前，每个 `model / dataset` 先用 50 个样本进行噪声校准。

候选 alpha：

```yaml
candidate_alpha_list: [0.1, 0.3, 0.5, 1.0, 2.0]
pilot_samples: 50
delta_logprob: 0.05
target_valid_ratio_range: [0.3, 0.8]
```

选择规则：

1. 计算每个 alpha 下满足 `gap = s_clean - s_corrupt > delta` 的有效样本比例；
2. 优先选择有效样本比例位于 `30%-80%` 的 alpha；
3. 如果所有 alpha 有效比例都低于 `30%`，说明污染太弱，应增大 alpha 或检查 visual span；
4. 如果所有 alpha 有效比例都高于 `80%` 且 `s_corrupt` 极低，说明污染可能太强，应降低 alpha；
5. 正式实验可使用 1-3 个稳定 alpha，并把选择过程写入 `noise_calibration.json`。

不要为了让某个模型得到更好候选层而事后挑 alpha。alpha 选择只依据 clean-corrupt gap 覆盖率，不依据最终编辑评测结果。

---

## 32. Teacher-forcing 答案 Token 对齐规则

目标答案评分必须使用 teacher-forcing，不使用 `generate()`。

输入形式：

```text
[prompt tokens] + [target answer tokens]
```

规则：

- prompt 部分 label 全部设为 `-100`；
- 只对 target answer token 计算 log probability；
- 如果当前任务有 `target_new` / `alt` answer，优先使用编辑目标答案作为 `target_answer`；
- 如果 target answer 为空，样本无效；
- 如果 tokenizer 后 answer token 长度为 0，样本无效；
- 如果 answer 被截断，样本无效；
- 不同模型保持各自 chat template 的合法格式；
- 必须记录 `answer_start`、`answer_end`、`answer_token_count`、`target_mask_hash`。

如果答案 token mask 错误，`CR/KCR` 就不再是目标答案恢复分数，而可能混入 prompt、padding 或其他特殊 token。

---

## 33. Restore Hook 实现规范

主实验 restore hook 只能替换 visual token slice。推荐伪代码：

```python
def restore_hook(module, inputs, outputs):
    hidden = outputs[0] if isinstance(outputs, tuple) else outputs
    hidden_new = hidden.clone()

    # visual_token_indices: per-sample visual token positions after decoder input construction
    hidden_new[:, visual_token_indices, :] = clean_cache[layer][:, visual_token_indices, :]

    if isinstance(outputs, tuple):
        return (hidden_new,) + outputs[1:]
    return hidden_new
```

必须满足：

- 只替换视觉 token slice；
- 不替换文本 token；
- 不替换 teacher-forcing answer token；
- 不 inplace 修改原 tensor；
- clean cache 与当前 batch 样本顺序一致；
- hidden shape 与 clean cache shape 一致；
- `model.eval()`；
- `torch.no_grad()`；
- `use_cache=False`；
- batch 内不同样本 visual span 不一致时，必须按样本分别索引，不能假设统一连续区间。

如果 `outputs` 是 tuple、dataclass 或模型自定义对象，必须保持原返回结构，只替换其中 hidden states。

---

## 34. CR 异常值与浅层偏置诊断

主排序默认使用 raw CR 均值：

```text
cr_raw_mean
```

但必须同时报告：

```text
cr_clip01_mean
cr_gt1_ratio
cr_lt0_ratio
nonfinite_count
```

定义：

```math
CR_{clip01}(l)=clip(CR(l),0,1).
```

不建议只保存 clipped 结果，因为 `CR>1` 和 `CR<0` 本身是重要诊断信息。

如果某个 `model/dataset` 出现大量 `CR>1`、`CR<0` 或 NaN/Inf，需要在 `summary.md` 标记：

```text
unstable_restoration
```

浅层偏置也必须自动诊断：

```yaml
diagnostics:
  shallow_bias_check: true
  shallow_layers: first_20_percent
  middle_layers: middle_40_percent
  deep_layers: last_20_percent
```

建议输出：

```text
shallow_mean_cr
middle_mean_cr
deep_mean_cr
top_layer_depth_ratio
```

如果 Top-3 全部集中在最前 20% 层，summary 中写入：

```text
The restoration scores are strongly concentrated in shallow layers, indicating that the result may be dominated by remaining downstream propagation depth rather than adapter editability.
```

中文说明：

```text
因果恢复分数明显集中在浅层，说明结果可能主要受到恢复后剩余传播深度影响，而不应直接解释为浅层具有最高 Adapter 编辑适宜性。
```

---

## 35. 分阶段运行计划

不要直接全量跑 `7 models x 3 datasets`。按以下阶段推进。

### Stage 1：最小可行 pilot

```yaml
models:
  - llava-v1.5-7b
datasets:
  - EVQA-pilot500
sample_size: 50
alpha_list: [0.5, 1.0]
seeds: [0]
```

检查：

- visual span 是否正确；
- clean/corrupt gap 是否合理；
- 有效样本比例是否在 `30%-80%`；
- CR 是否大量异常；
- Top 层是否全部集中在 `L0/L1`。

### Stage 2：跨架构验证

```yaml
models:
  - llava-v1.5-7b
  - blip2-opt-2.7b
  - paligemma-3b
datasets:
  - EVQA-pilot500
sample_size: 50
```

目的：

- 验证不同视觉接入方式下 hook 是否稳定；
- 验证 visual span 是否能够统一定位；
- 验证 Q-Former、projector、image token 模型都能跑通。

### Stage 3：全量运行

```yaml
models:
  - blip2-opt-2.7b
  - instructblip-vicuna-7b
  - minigpt-4-vicuna-7b
  - llava-v1.5-7b
  - qwen2.5-vl-3b-instruct
  - paligemma-3b
  - smolvlm-1.7b
datasets:
  - EVQA-pilot500
  - MMKE-visual
  - MMKE-entity
```

只有前两阶段通过后，再进入全量运行。全量运行必须启用 `resume/skip done`，并确保不会影响正在进行的训练任务。

---

## 36. 本次修订采纳与未采纳说明

采纳并写入主实验口径：

- 恢复视觉 token slice，不恢复整层 hidden states；
- 将 `H_v^l = H^l_{1:N_v}` 改为 `H_v^l = H^l[:, V, :]`；
- 增加模型级 hook path 与 visual span 适配表；
- 增加 noise calibration；
- 增加 teacher-forcing answer token mask 规则；
- 增加 restore hook 伪代码；
- 增加 runtime 设置；
- 增加 CR 异常值与浅层偏置诊断；
- 增加分阶段运行计划。

暂不放入主实验口径，只保留为可选变体或后续消融：

- 目标区域视觉 token 恢复：需要 bbox 或可靠 region-token 映射，当前三数据集未统一具备；
- 单视觉 token 恢复：计算成本过高，不适合作为 7 models x 3 datasets 主实验；
- full-state restoration：会恢复文本和答案 token，不再专门衡量视觉表征恢复能力，只能作为诊断消融；
- clipped CR 排名：可作为稳健性分析，但主排序保留 raw CR，以免掩盖 `CR>1` 或 `CR<0` 的异常信息。
