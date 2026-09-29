# Visual Causal Restoration（视觉因果恢复）实验手册

> 版本：v1.3（回填术语统一：主排序字段 `cr_seq_mean`；辅助字段 `cr_first_token_mean` / `kcr_seq_mean`）  
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

补充说明：

- 当前主排序指标为 `CR_seq`，即完整目标答案序列恢复分数；
- 为兼容传统 Causal Tracing / CMA 的目标 object token 评分口径，本手册同时计算 `CR_first_token`；
- `CR_seq`、`CR_first_token` 和 `KCR_seq` 均由同一次 clean / corrupt / restore 前向结果计算，不额外执行恢复前向传播；
- 最终候选层主排名使用 `CR_seq`，`CR_first_token` 仅作为传统 CMA 兼容性辅助分析；
- 回填到候选层总表时，主排序字段统一写作 `cr_seq_mean`，不再使用容易混淆的 `CR_mean`。

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

同时计算 clean 状态下目标答案序列平均 log probability，记为 `s_clean_seq`：

```math
s_clean_seq = (1/T) * sum_t log p_clean(y_t | x_v, x_t, y_<t)
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

执行污染前向，计算目标答案序列平均 log probability，记为 `s_corrupt_seq`：

```math
s_corrupt_seq = (1/T) * sum_t log p_corrupt(y_t | x_v_corrupt, x_t, y_<t)
```

---

## 8. 样本过滤规则

为了保证污染确实破坏了模型对目标答案的支持，需要过滤样本。

保留满足以下条件的样本：

```math
s_clean_seq > s_corrupt_seq + delta
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

然后继续执行后续 decoder layers，得到恢复状态下的目标答案序列平均 log probability，记为 `s_restore_seq(l)`：

```math
s_restore_seq(l) = (1/T) * sum_t log p_restore(l)(y_t | x_v_corrupt, x_t, y_<t)
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

## 10. 主指标：Seq-CR 与传统 CMA 兼容指标

本手册采用 **一个 CMA-Direct 实验流程，同时计算多个 scoring 口径**：

| 指标 | 名称 | 用途 | 是否主排序 |
|---|---|---|---|
| `CR_seq` | 完整答案序列恢复分数 | 衡量完整目标答案序列的平均 log probability 恢复程度 | 是 |
| `CR_first_token` | 首个目标答案 token 恢复分数 | 兼容传统 Causal Tracing / CMA 的 next-token factual recall 口径 | 否 |
| `KCR_seq` | 完整答案序列 KL 恢复率 | 衡量恢复后输出分布是否接近 clean 分布 | 否 |

重要原则：

```text
做两个 scoring，不做两个实验。
```

也就是说，`CR_seq` 与 `CR_first_token` 使用同一次 clean / corrupt / restore 前向结果计算，不额外执行恢复前向传播。额外时间开销通常只来自多取一个 token 的 log probability、多保存字段和多生成辅助排名，预计约 `1%-3%`。

---

### 10.1 主指标：完整答案序列恢复分数 `CR_seq`

给定目标答案序列：

```math
y=(y_1,\ldots,y_T)
```

clean 状态下完整答案序列平均 log probability 为：

```math
s_{\mathrm{clean}}^{\mathrm{seq}}
=
\frac{1}{T}
\sum_{t=1}^{T}
\log p_{\mathrm{clean}}(y_t \mid x_v,x_t,y_{<t})
```

corrupt 状态下：

```math
s_{\mathrm{corrupt}}^{\mathrm{seq}}
=
\frac{1}{T}
\sum_{t=1}^{T}
\log p_{\mathrm{corrupt}}(y_t \mid \tilde{x}_v,x_t,y_{<t})
```

恢复第 `l` 层视觉 hidden states 后：

```math
s_{\mathrm{restore}}^{\mathrm{seq}}(l)
=
\frac{1}{T}
\sum_{t=1}^{T}
\log p_{\mathrm{restore}(l)}(y_t \mid \tilde{x}_v,x_t,y_{<t})
```

第 `l` 层的完整序列因果恢复分数定义为：

```math
CR_{\mathrm{seq}}(l)
=
\frac{
s_{\mathrm{restore}}^{\mathrm{seq}}(l)
-
s_{\mathrm{corrupt}}^{\mathrm{seq}}
}{
s_{\mathrm{clean}}^{\mathrm{seq}}
-
s_{\mathrm{corrupt}}^{\mathrm{seq}}
+
\epsilon
}
```

其中：

```yaml
epsilon: 1.0e-8
```

`CR_seq` 是本文 `CMA-Direct / Visual Causal Restoration` 的主排序指标，用于生成正式 `Top-3 / Top-5` 候选层。

---

### 10.2 传统 CMA 兼容指标：首 token 恢复分数 `CR_first_token`

传统 Causal Tracing / CMA 通常用于 factual recall 场景，关注的是目标 object token 的 next-token probability 恢复。为兼容该口径，本实验额外计算目标答案首 token 的恢复分数。

设目标答案第一个 token 为：

```math
y_1
```

clean 状态下：

```math
s_{\mathrm{clean}}^{\mathrm{ft}}
=
\log p_{\mathrm{clean}}(y_1 \mid x_v,x_t)
```

corrupt 状态下：

```math
s_{\mathrm{corrupt}}^{\mathrm{ft}}
=
\log p_{\mathrm{corrupt}}(y_1 \mid \tilde{x}_v,x_t)
```

恢复第 `l` 层视觉 hidden states 后：

```math
s_{\mathrm{restore}}^{\mathrm{ft}}(l)
=
\log p_{\mathrm{restore}(l)}(y_1 \mid \tilde{x}_v,x_t)
```

首 token 恢复分数定义为：

```math
CR_{\mathrm{first\_token}}(l)
=
\frac{
s_{\mathrm{restore}}^{\mathrm{ft}}(l)
-
s_{\mathrm{corrupt}}^{\mathrm{ft}}
}{
s_{\mathrm{clean}}^{\mathrm{ft}}
-
s_{\mathrm{corrupt}}^{\mathrm{ft}}
+
\epsilon
}
```

`CR_first_token` 仅作为传统 CMA 兼容性分析，不作为主候选层排序标准。

---

### 10.3 指标解释

| 分数范围 | 含义 |
|---|---|
| `≈ 0` | 恢复该层几乎不能挽救输出 |
| `0 - 1` | 部分恢复 |
| `≈ 1` | 基本恢复到 clean 状态 |
| `> 1` | 恢复后比 clean 更支持目标答案，可能是过恢复或噪声现象 |
| `< 0` | 恢复该层反而进一步降低目标答案支持 |

如果答案只有一个 token，`CR_seq` 与 `CR_first_token` 通常接近；如果答案包含多个 token，则以 `CR_seq` 为主，因为它更能反映完整目标答案的恢复情况。

---


## 11. 辅助指标：完整答案序列 KL Restoration Score（KCR_seq）

除了 log probability 恢复，也可以使用 KL 恢复率作为辅助诊断指标。`KCR_seq` 在完整 target answer token positions 上计算。

首先计算 clean 与 corrupt 输出分布之间的 KL：

```math
KL_{\mathrm{corrupt}}^{\mathrm{seq}}
=
D_{\mathrm{KL}}
(
p_{\mathrm{clean}}^{\mathrm{seq}}
\Vert
p_{\mathrm{corrupt}}^{\mathrm{seq}}
)
```

再计算 clean 与 restore 输出分布之间的 KL：

```math
KL_{\mathrm{restore}}^{\mathrm{seq}}(l)
=
D_{\mathrm{KL}}
(
p_{\mathrm{clean}}^{\mathrm{seq}}
\Vert
p_{\mathrm{restore}(l)}^{\mathrm{seq}}
)
```

定义 KL 恢复率：

```math
KCR_{\mathrm{seq}}(l)
=
\frac{
KL_{\mathrm{corrupt}}^{\mathrm{seq}}
-
KL_{\mathrm{restore}}^{\mathrm{seq}}(l)
}{
KL_{\mathrm{corrupt}}^{\mathrm{seq}}
+
\epsilon
}
```

### 指标解释

| KCR_seq 值 | 含义 |
|---|---|
| 越接近 1 | 恢复后输出分布越接近 clean |
| 接近 0 | 恢复几乎没有作用 |
| 小于 0 | 恢复后输出分布比 corrupt 更偏离 clean |

### 建议

主结果使用 `CR_seq`，`KCR_seq` 只作为辅助分析。

原因：

- `CR_seq` 更直接对应完整目标答案概率是否恢复；
- `KCR_seq` 更关注完整答案位置上的分布形状，可能受到非目标 token 概率变化影响；
- `CR_first_token` 用于兼容传统 CMA，但不替代 `CR_seq`。

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
CR_seq_bar(l) = (1/S) * sum_s CR_seq_s(l)
```

---

## 14. 聚合方式

对每个模型、每个数据集、每个层 `l`，聚合所有有效样本。主聚合分数使用 `CR_seq`：

```math
Score_seq(l) = mean_{i in D_valid} CR_seq_i(l)
```

同时报告：

- mean；
- standard deviation；
- standard error；
- bootstrap 95% confidence interval；
- valid sample count。

---

## 15. 层排名与候选层输出

根据聚合后的主分数 `CR_seq` 进行排序：

```text
Rank = argsort_l(Score_seq(l), descending=True)
```

输出：

```yaml
top_k:
  - 3
  - 5
```

保存：

- Top-3 causal restoration layers by `CR_seq`；
- Top-5 causal restoration layers by `CR_seq`；
- 每层平均 `CR_seq`；
- 每层平均 `KCR_seq`；
- 每层有效样本数；
- 每层 `CR_seq` 标准误；
- 每层 `CR_seq` 置信区间。

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
│   ├── cr_seq_curve.png
│   ├── cr_first_token_curve.png
│   ├── kcr_seq_curve.png
│   └── summary.md
```

### layer_scores.csv 字段

```csv
model,dataset,layer,noise_alpha,num_samples,valid_samples,valid_ratio,cr_seq_mean,cr_seq_clip01_mean,cr_seq_std,cr_seq_se,cr_seq_ci_low,cr_seq_ci_high,cr_seq_gt1_ratio,cr_seq_lt0_ratio,cr_first_token_mean,cr_first_token_std,cr_first_token_se,cr_first_token_ci_low,cr_first_token_ci_high,kcr_seq_mean,kcr_seq_std,kcr_seq_se,kcr_seq_ci_low,kcr_seq_ci_high,rank_by_cr_seq,rank_by_cr_first_token,shallow_middle_deep_group,status
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
first_answer_token_id
first_answer_token_text
target_mask_hash
s_clean_seq
s_corrupt_seq
s_restore_seq
clean_corrupt_gap_seq
cr_seq
cr_seq_clip01
s_clean_first_token
s_corrupt_first_token
s_restore_first_token
clean_corrupt_gap_first_token
cr_first_token
kl_corrupt_seq
kl_restore_seq
kcr_seq
is_valid
invalid_reason
```

### top_layers.json 示例

```json
{
  "model": "llava-v1.5-7b",
  "dataset": "E-VQA",
  "method": "CMA-Direct",
  "primary_metric": "CR_seq",
  "top3_by_cr_seq": [0, 1, 2],
  "top5_by_cr_seq": [0, 1, 2, 3, 4],
  "auxiliary_metrics": {
    "CR_first_token": {
      "top3": [0, 1, 2],
      "top5": [0, 1, 2, 3, 4]
    },
    "KCR_seq": {
      "top3": [0, 1, 2],
      "top5": [0, 1, 2, 3, 4]
    }
  },
  "note": "CR_first_token is computed from the same forward passes as CR_seq and is reported only for compatibility with classical Causal Tracing."
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
  primary: CR_seq
  auxiliary:
    - CR_first_token
    - KCR_seq

answer_scoring:
  mode: teacher_forcing
  token_mask: target_answer_tokens
  reduction: mean_logprob
  first_token_score: true
  first_token_position: first_target_answer_token

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
  primary_score: cr_seq_mean
  diagnostic_scores:
    - cr_seq_clip01_mean
    - cr_first_token_mean
    - kcr_seq_mean
    - cr_seq_gt1_ratio
    - cr_seq_lt0_ratio
  auxiliary_ranking:
    - rank_by_cr_first_token
    - rank_by_kcr_seq
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

            target_answer = sample.alt or sample.target_new or sample.answer

            # 0. Build teacher-forcing inputs and answer token positions
            inputs = build_teacher_forcing_inputs(
                sample=sample,
                target_answer=target_answer
            )
            answer_positions = get_answer_token_positions(inputs)
            first_answer_pos = answer_positions[0]

            # 1. Clean forward
            clean_outputs = forward_with_cache(
                model=model,
                inputs=inputs,
                corrupt_visual=False,
                cache_visual_hidden=True
            )

            clean_visual_cache = clean_outputs.visual_hidden_by_layer

            # 同一次 clean logits 同时计算 seq 与 first-token 分数
            s_clean_seq = mean_logprob(
                clean_outputs.logits,
                inputs.target_ids,
                answer_positions
            )
            s_clean_first_token = token_logprob(
                clean_outputs.logits,
                inputs.target_ids,
                first_answer_pos
            )

            for alpha in noise_alpha_list:
                for seed in noise_seeds:

                    # 2. Corrupt forward
                    noise = make_visual_noise(sample, alpha=alpha, seed=seed)
                    corrupt_outputs = forward_with_cache(
                        model=model,
                        inputs=inputs,
                        visual_noise=noise,
                        cache_visual_hidden=False
                    )

                    # 同一次 corrupt logits 同时计算 seq 与 first-token 分数
                    s_corrupt_seq = mean_logprob(
                        corrupt_outputs.logits,
                        inputs.target_ids,
                        answer_positions
                    )
                    s_corrupt_first_token = token_logprob(
                        corrupt_outputs.logits,
                        inputs.target_ids,
                        first_answer_pos
                    )

                    # 3. Filter sample using primary seq gap
                    is_valid = (s_clean_seq > s_corrupt_seq + delta_logprob)
                    if not is_valid:
                        continue

                    for layer in decoder_layers:

                        # 4. Restore layer
                        restore_outputs = forward_with_restore(
                            model=model,
                            inputs=inputs,
                            visual_noise=noise,
                            restore_layer=layer,
                            restore_visual_hidden=clean_visual_cache[layer]
                        )

                        # 5. Same restore logits, two `CR_seq` scores
                        s_restore_seq = mean_logprob(
                            restore_outputs.logits,
                            inputs.target_ids,
                            answer_positions
                        )
                        s_restore_first_token = token_logprob(
                            restore_outputs.logits,
                            inputs.target_ids,
                            first_answer_pos
                        )

                        cr_seq = (s_restore_seq - s_corrupt_seq) / (
                            s_clean_seq - s_corrupt_seq + eps
                        )

                        cr_first_token = (
                            s_restore_first_token - s_corrupt_first_token
                        ) / (
                            s_clean_first_token - s_corrupt_first_token + eps
                        )

                        # 6. Optional `KCR_seq` over complete target answer positions
                        kl_corrupt_seq = sequence_kl(
                            clean_outputs.logits,
                            corrupt_outputs.logits,
                            answer_positions
                        )
                        kl_restore_seq = sequence_kl(
                            clean_outputs.logits,
                            restore_outputs.logits,
                            answer_positions
                        )
                        kcr_seq = (kl_corrupt_seq - kl_restore_seq) / (
                            kl_corrupt_seq + eps
                        )

                        save_sample_score(
                            cr_seq=cr_seq,
                            cr_first_token=cr_first_token,
                            kcr_seq=kcr_seq,
                            s_clean_seq=s_clean_seq,
                            s_corrupt_seq=s_corrupt_seq,
                            s_restore_seq=s_restore_seq,
                            s_clean_first_token=s_clean_first_token,
                            s_corrupt_first_token=s_corrupt_first_token,
                            s_restore_first_token=s_restore_first_token,
                        )
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

> `CR_seq` / `KCR_seq` measure causal restoration capacity under visual corruption, not adapter editability itself.

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

### 如果浅层 `CR_seq` 最高

> 浅层视觉表征恢复后，干净视觉信息仍可通过更多后续 attention 和 MLP 模块传播至目标答案 token，因此具有更强的恢复能力。这说明浅层视觉状态在污染条件下对答案恢复具有较强因果作用，但该结果也可能受到剩余传播深度的影响，并不直接表明浅层是最佳 Adapter 编辑层。

### 如果中层 `CR_seq` 最高

> 中层视觉表征恢复带来最大的答案概率恢复，说明视觉信息可能在该阶段与文本查询语义发生关键融合。相比浅层，中层恢复可能更接近已经语义化的视觉表征；相比深层，中层仍保留足够的下游传播路径，因此表现出较强的因果恢复作用。

### 如果深层 `CR_seq` 很低

> 深层视觉表征恢复后，后续可用于将视觉信息混合至目标答案 token 的 attention 层数较少，因此恢复作用有限。这与 decoder-only VLM 中视觉 token 需要通过后续自注意力影响文本 token 的传播机制一致。

---

## 22. 论文英文描述

```text
We further conduct a visual causal restoration analysis to examine whether visual representations at a given decoder layer causally support target answer generation under corrupted visual inputs. For each sample, we first run a clean forward pass and cache the visual hidden states at every decoder layer. We then corrupt the visual input embeddings with Gaussian noise and measure the degradation in the target answer log-likelihood. During the restoration pass, the model still receives the corrupted visual input, but the visual hidden states at a selected layer are replaced with their clean counterparts. Our primary causal restoration score, CR_seq, is defined as the fraction of the corrupted-to-clean log-likelihood gap recovered over the complete target answer sequence under teacher forcing. To maintain compatibility with classical Causal Tracing, we additionally compute CR_first_token on the first target token from the same forward passes. The first-token score is reported only as an auxiliary compatibility analysis, while CR_seq is used for candidate-layer ranking. Since restoring earlier layers leaves more downstream computation for the restored signal to propagate, we use this analysis as a causal restoration diagnostic rather than as a ground-truth measure of adapter editability.
```

---

## 23. 中文论文描述

```text
为分析不同decoder层视觉表征对目标答案生成的因果作用，本文进一步设计视觉因果恢复实验。具体而言，首先在正常输入下执行干净前向传播，并缓存各decoder层视觉token对应的hidden states。随后在decoder输入端对视觉embeddings加入高斯噪声，构造污染前向传播，并测量目标答案序列对数概率的下降。在恢复阶段，模型仍接收污染后的视觉输入，但在指定decoder层处，将该层视觉hidden states替换为干净前向中缓存的对应状态，并继续执行后续层计算。本文将完整目标答案序列上恢复后对数概率相对于污染状态的提升，占污染状态到干净状态差距的比例，定义为主因果恢复分数 CR_seq。为兼容经典 Causal Tracing 的目标 object token 评分口径，本文同时从同一批前向结果中计算目标答案首 token 的 CR_first_token，但该指标仅作为辅助兼容性分析，不作为主候选层排序标准。需要注意的是，较浅层恢复后仍具有更长的下游传播路径，因此该指标可能受到剩余传播深度影响。本文将其作为视觉表征因果恢复诊断，而不将其视为Adapter编辑适宜性的真实标准。
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
  primary: CR_seq
  auxiliary:
    - CR_first_token
    - KCR_seq
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
- CR_seq 是否大量大于 1；
- CR_seq 是否全部集中在 L0/L1；
- CR_first_token 与 CR_seq 的排名是否大体一致；
- KCR_seq 与 CR_seq 趋势是否一致；
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

本节补充的是把 `Visual Causal Restoration / CMA` 真正用于 `7 models x 3 datasets` 候选层定位时还缺少的实验口径。前文已经定义了 clean / corrupt / restore 和 `CR_seq` / `CR_first_token` / `KCR_seq`，但还需要把数据、层空间、排序、清洗、失败状态和回填格式固定下来，否则结果很难和其他候选层方法对齐。

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
  primary: cr_seq_mean
  auxiliary:
    - cr_first_token_mean
    - kcr_seq_mean
  teacher_forcing: true
  answer_score: mean_logprob_over_target_answer_tokens
  first_token_score: true
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
Score(l) = mean_{i in D_valid, alpha, seed} CR_seq_i(l, alpha, seed)
```

在 `layer_scores.csv`、`top_layers.json` 和候选层总表中，该聚合后的主排序分数字段统一记为：

```text
cr_seq_mean
```

不得再写成泛化的 `CR_mean`，因为 `CR_mean` 容易与 `cr_first_token_mean` 或 `kcr_seq_mean` 混淆。

辅助分数：

```math
KCRScore(l) = mean_{i in D_valid, alpha, seed} KCR_seq_i(l, alpha, seed)
```

排序规则：

1. `Score(l)` 从大到小排序。
2. 如果 `Score(l)` 并列，优先 `KCRScore(l)` 更大的层。
3. 如果仍并列，优先 `valid_samples(l)` 更多的层。
4. 如果仍并列，层号小的排前。

候选层输出：

```text
Top-3 = cr_seq_mean rank 前 3
Top-5 = cr_seq_mean rank 前 5
```

对应总表写法：

```text
score_source = cr_seq_mean
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
dataset,model,layer,valid_samples,total_samples,valid_ratio,cr_seq_mean,cr_seq_std,cr_seq_se,cr_first_token_mean,cr_first_token_std,cr_first_token_se,kcr_seq_mean,kcr_seq_std,kcr_seq_se,score,rank_by_cr_seq,rank_by_cr_first_token,status
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

### 29.10 回填到当前候选层总表

回填到：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

当前总表不是把 CMA 写入真实扫层结果第 4 节，而是先作为候选层定位方法登记在第 2 章。因此正式回填采用以下三处：

1. 更新 `### 2.8 CMA-Direct` 的方法说明与状态。
2. 在 `### 2.11 待补候选方法` 按 `dataset/model` 展开 21 行。
3. 更新 `### 2.12 本章候选层汇总` 的完成度。

`### 2.11 待补候选方法` 的主表头保持为：

```markdown
| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|---|
```

每个 `dataset/model` 回填一行：

```markdown
| EVQA-pilot500 | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | Lx,Ly,Lz | Lx,Ly,Lz,La,Lb | done; valid=.../...; alpha=...; seeds=... |
```

字段规则：

- `Method` 固定写作 `CMA-Direct`；
- `Score source` 固定写作 `cr_seq_mean`；
- `Top-3` / `Top-5` 使用清洗后的候选层，即去重、删除越界层、删除 hook 失败或非有限分数层后的结果；
- 如果清洗前后不同，必须在该组合的 `candidates_raw.json`、`candidates_clean.json` 和 `summary.md` 中保留差异原因；
- `Status` 至少写明 `done` / `low_valid_coverage` / `hook_failed` / `visual_span_failed` / `no_valid_cma_sample`，并附带 `valid=有效样本/总样本`；
- `low_valid_coverage` 可以回填诊断 Top-K，但不得和正常 `done` 混写。

如果需要在文档中保留 raw/clean 差异，可在 `### 2.8 CMA-Direct` 下另开诊断表：

```markdown
| Dataset | Model | Raw Top-3 | Clean Top-3 | Raw Top-5 | Clean Top-5 | Valid Samples | Total Samples | Status |
|---|---|---|---|---|---|---:|---:|---|
```

该诊断表用于记录异常处理，不替代 `### 2.11` 的统一候选方法登记表。

### 29.11 最小运行清单

正式跑 `7 models x 3 datasets` 前，先检查：

- 是否只占用空闲 GPU，不影响正在进行的训练任务；
- 是否启用 resume/skip done；
- 是否完成模型适配实测表，且每个模型的 `decoder_block_path`、`layer_id -> module_name`、hook output shape 已登记；
- 是否完成 visual span probe，且每个模型都能稳定得到 `visual_token_indices`；
- 是否完成每个 `model/dataset` 的 noise calibration，并保存 `noise_calibration.json`；
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

### 30.1 模型适配实测登记表

正式全量运行前，必须先用 probe 脚本把下表补齐。下表中的 `待实测` 不能作为全量运行依据；只有 `probe_status=passed` 的模型才允许进入 Stage 3。

| Model | Legal layers | Decoder block path | Hook output object | Hook output hidden shape | Visual span source | Visual span status | Probe status | Probe log |
|---|---|---|---|---|---|---|---|---|
| `blip2-opt-2.7b` | `L0-L31` | 待实测 | 待实测 | 待实测 | Q-Former 输出后进入 OPT 的视觉 query token | 待实测 | pending | - |
| `instructblip-vicuna-7b` | `L0-L31` | 待实测 | 待实测 | 待实测 | Q-Former 输出后的视觉 query token | 待实测 | pending | - |
| `minigpt-4-vicuna-7b` | `L0-L31` | 待实测 | 待实测 | 待实测 | projected visual tokens 在 prompt 中的位置 | 待实测 | pending | - |
| `llava-v1.5-7b` | `L0-L31` | 待实测 | 待实测 | 待实测 | `<image>` 展开后的 image token span / projector output | 待实测 | pending | - |
| `qwen2.5-vl-3b-instruct` | `L0-L35` | 待实测 | 待实测 | 待实测 | processor/chat template 展开后的 image token span | 待实测 | pending | - |
| `paligemma-3b` | `L0-L17` | 待实测 | 待实测 | 待实测 | processor 序列中的 image token positions | 待实测 | pending | - |
| `smolvlm-1.7b` | `L0-L23` | 待实测 | 待实测 | 待实测 | processor 返回或可反推的 image token positions | 待实测 | pending | - |

每个模型的 probe 结果至少保存为：

```text
cma_direct_probe/
  {model}/
    model_probe.json
    visual_span_probe.jsonl
    hook_probe.log
```

`model_probe.json` 必须包含：

```json
{
  "model": "llava-v1.5-7b",
  "config_path": "configs/vead/llava-v1.5-7b.yaml",
  "num_decoder_layers": 32,
  "legal_layers": ["L0", "L1", "..."],
  "decoder_block_path": "实际模块路径模板，例如 ...layers.{layer}",
  "layer_id_to_module_name": {"L0": "...", "L1": "..."},
  "hook_position": "decoder_block_output",
  "hook_output_object": "tensor|tuple|dataclass",
  "hook_output_hidden_shape_example": [1, 1234, 4096],
  "visual_span_source": "processor|chat_template|wrapper_prepare_inputs|manual_verified",
  "visual_span_status": "passed",
  "restore_hook_status": "passed",
  "probe_status": "passed",
  "failure_reason": ""
}
```

通过标准：

1. `num_decoder_layers` 与合法层空间一致。
2. 每一层 `layer_id -> module_name` 可解析，且 hook 能捕获 decoder block output。
3. hook 返回结构可被安全替换；如果输出是 tuple/dataclass，只替换 hidden tensor，不破坏其余字段。
4. 至少 5 条样本能稳定得到非空 `visual_token_indices`。
5. `visual_token_indices` 不得与 teacher-forcing answer token 区间重叠。
6. restore hook dry-run 后，只有 visual token slice 被替换，文本 token 和答案 token hidden states 不变。

任一条件不满足时，该模型不得进入全量 CMA-Direct，状态写为 `hook_failed`、`visual_span_failed` 或更具体的失败原因。

### 30.2 Visual Span Probe 流程

每个模型必须先执行 visual span probe，再执行 noise calibration。probe 不做候选层排序，只验证“哪些 token 是进入 decoder 后的视觉 token”。

对每条 probe 样本保存：

```json
{
  "sample_id": "...",
  "model": "llava-v1.5-7b",
  "dataset": "EVQA-pilot500",
  "input_ids_shape": [1, 1234],
  "inputs_embeds_shape": [1, 1234, 4096],
  "visual_token_indices": [35, 36, 37],
  "visual_start": 35,
  "visual_end": 610,
  "num_visual_tokens": 576,
  "answer_start": 900,
  "answer_end": 905,
  "overlap_with_answer": false,
  "span_source": "wrapper_prepare_inputs",
  "status": "passed",
  "failure_reason": ""
}
```

模型级建议：

- `BLIP2-OPT-2.7B` / `InstructBLIP-Vicuna-7B`：视觉 span 指进入语言模型 decoder 的 Q-Former query / prefix tokens，不是原始图像 patch。
- `MiniGPT-4-Vicuna-7B`：视觉 span 指 projected visual tokens 被拼入 Vicuna prompt 后的位置，必须由 wrapper 实际拼接结果确定。
- `LLaVA-v1.5-7B`：视觉 span 指 `<image>` 占位符经 projector 展开后的 image token 区间，不默认在序列开头。
- `Qwen2.5-VL-3B`：必须使用同一 chat template / processor 生成输入后定位 image span；不能用裸文本 tokenizer 的位置替代。
- `PaliGemma-3B`：视觉 token positions 通常由 processor 序列显式给出，但仍需验证 answer token mask 不重叠。
- `SmolVLM-Instruct-1.7B`：优先使用 processor 返回的 image token positions；如果 processor 不返回，必须从 multimodal input construction 中反推并记录依据。

禁止 fallback：

```text
visual_token_indices = all_prompt_tokens
visual_token_indices = all_non_answer_tokens
visual_token_indices = full_sequence
visual_token_indices = first_N_tokens_without_verification
```

如果无法确定视觉 token span，该组合状态写为 `visual_span_failed`，不得产出正常 Top-3 / Top-5。

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

### 31.1 Noise Calibration 输出规范

每个 `model/dataset` 必须先产生：

```text
cma_direct_noise_calibration/
  {dataset}/
    {model}/
      noise_calibration.json
      noise_calibration_samples.jsonl
      noise_calibration_summary.md
```

`noise_calibration.json` 字段：

```json
{
  "dataset": "EVQA-pilot500",
  "model": "llava-v1.5-7b",
  "pilot_samples": 50,
  "delta_logprob": 0.05,
  "candidate_alpha_list": [0.1, 0.3, 0.5, 1.0, 2.0],
  "noise_seeds": [0, 1, 2],
  "selected_alpha_list": [0.5],
  "selected_seed_list": [0],
  "selection_rule": "valid_ratio_in_0.3_0.8_then_closest_to_0.5",
  "alpha_stats": [
    {
      "alpha": 0.1,
      "valid_samples": 8,
      "total_samples": 50,
      "valid_ratio": 0.16,
      "mean_clean_logprob": -1.23,
      "mean_corrupt_logprob": -1.25,
      "mean_gap": 0.02,
      "status": "too_weak"
    }
  ],
  "status": "passed",
  "failure_reason": ""
}
```

`noise_calibration_samples.jsonl` 每行至少保存：

```json
{
  "sample_id": "...",
  "alpha": 0.5,
  "seed": 0,
  "s_clean_seq": -1.23,
  "s_corrupt_seq": -1.74,
  "gap": 0.51,
  "is_valid": true,
  "invalid_reason": ""
}
```

alpha 选择规则固定为：

1. 先过滤 `valid_ratio < 0.3` 的 alpha，标记为 `too_weak` 或 `low_valid_coverage`。
2. 再过滤 `valid_ratio > 0.8` 且 `mean_corrupt_logprob` 极低的 alpha，标记为 `too_strong`。
3. 在剩余 alpha 中，优先选择 `valid_ratio` 最接近 `0.5` 的 alpha。
4. 如果多个 alpha 接近，选择较小 alpha，避免过强污染导致浅层恢复偏置。
5. 如果没有 alpha 通过，允许进入诊断状态，但该组合不得写为正常 `done`，状态写 `noise_calibration_failed` 或 `low_valid_coverage`。

全量运行建议：

- 默认使用校准出的 `selected_alpha_list`。
- 如果时间预算紧张，主实验可先用 `1` 个 alpha 和 `seed=0` 跑全量，再对异常组合补多 seed。
- 如果论文需要报告稳健性，再对最终 Top-5 附近层补跑 `seeds=[0,1,2]`。
- 不允许根据真实编辑扫层结果反向选择 alpha。

### 31.2 Calibration 通过标准

进入全量 CMA-Direct 前，`noise_calibration.json` 必须满足：

```yaml
status: passed
selected_alpha_list_nonempty: true
min_valid_ratio: 0.3
max_valid_ratio_without_too_strong: 0.8
visual_span_probe_status: passed
hook_probe_status: passed
```

如果某个模型 / 数据集无法满足上述条件，可以继续保存诊断文件，但总表状态必须写成：

```text
low_valid_coverage
noise_calibration_failed
```

不得把这类结果与正常 `done` 混在一起。

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

如果答案 token mask 错误，`CR_seq` / `CR_first_token` / `KCR_seq` 就不再是目标答案恢复分数，而可能混入 prompt、padding 或其他特殊 token。

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

## 34. CR_seq 异常值与浅层偏置诊断

主排序默认使用 `CR_seq` 的 raw 均值：

```text
cr_seq_mean
```

但必须同时报告：

```text
cr_seq_clip01_mean
cr_seq_gt1_ratio
cr_seq_lt0_ratio
nonfinite_count
```

定义：

```math
`CR_seq`^{seq}_{clip01}(l)=clip(CR_{seq}(l),0,1).
```

不建议只保存 clipped 结果，因为 `CR_seq>1` 和 `CR_seq<0` 本身是重要诊断信息。

如果某个 `model/dataset` 出现大量 `CR_seq>1`、`CR_seq<0` 或 NaN/Inf，需要在 `summary.md` 标记：

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
shallow_mean_cr_seq
middle_mean_cr_seq
deep_mean_cr_seq
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
- `CR_seq` 是否大量异常；
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
- 增加 `CR_seq` 异常值与浅层偏置诊断；
- 增加分阶段运行计划；
- 增加传统 CMA 兼容评分 `CR_first_token`，与 `CR_seq` 同一次前向计算；
- 明确主排序使用 `CR_seq`，`CR_first_token` 仅作为辅助兼容性分析；
- 将候选层总表中的主排序字段统一为 `cr_seq_mean`，不再使用 `CR_mean`；

暂不放入主实验口径，只保留为可选变体或后续消融：

- 目标区域视觉 token 恢复：需要 bbox 或可靠 region-token 映射，当前三数据集未统一具备；
- 单视觉 token 恢复：计算成本过高，不适合作为 7 models x 3 datasets 主实验；
- full-state restoration：会恢复文本和答案 token，不再专门衡量视觉表征恢复能力，只能作为诊断消融；
- clipped `CR_seq` 排名：可作为稳健性分析，但主排序保留 raw `CR_seq`，以免掩盖 `CR_seq>1` 或 `CR_seq<0` 的异常信息。

---

## 37. 传统 CMA 兼容评分：同一次前向同时计算 Seq-CR 与 First-Token CR

### 37.1 实验动机

经典 Causal Tracing / CMA 通常用于文本事实回忆场景，关注的是目标 object token 的 next-token probability 恢复。也就是说，传统口径更接近：

```text
prompt -> first target object token
```

而当前 VLM 编辑任务中的目标答案通常可能包含多个 token。因此，本文保留完整目标答案序列恢复分数作为主指标，同时额外计算 first-token 恢复分数，以兼容传统 CMA 的评分口径。

### 37.2 指标角色

| 指标 | 角色 | 是否进入主排名 |
|---|---|---|
| `CR_seq` | 完整答案序列恢复分数，适配 VLM 多 token 目标 | 是 |
| `CR_first_token` | 首个目标 token 恢复分数，兼容传统 CMA | 否 |
| `KCR_seq` | 完整答案序列 KL 恢复率，辅助诊断分布恢复 | 否 |

最终 `Top-3 / Top-5` 主结果使用：

```text
rank_by_cr_seq
```

同时保存：

```text
rank_by_cr_first_token
rank_by_kcr_seq
```

用于附录、诊断或与传统 CMA 口径对齐。

### 37.3 计算成本说明

`CR_first_token` 必须从同一次 clean / corrupt / restore forward 的 logits 中计算，不允许为了 first-token 版本重新跑一遍实验。

推荐实现：

```text
clean forward -> 同时计算 s_clean_seq 与 s_clean_first_token
corrupt forward -> 同时计算 s_corrupt_seq 与 s_corrupt_first_token
restore forward -> 同时计算 s_restore_seq 与 s_restore_first_token
```

预计额外开销：

```text
1% - 3%
```

主要来自字段保存、额外 logprob 提取和辅助排名生成。

错误实现：

```text
CMA-Direct-Seq 跑一遍
CMA-Direct-FirstToken 再跑一遍
```

这种做法会使 clean / corrupt / restore forward 重复执行，整体耗时接近 `2x`，不推荐。

### 37.4 目标 token 记录要求

为了便于排查 tokenizer 差异，必须在 sample-level 输出中保存：

```text
answer_token_count
first_answer_token_id
first_answer_token_text
answer_start
answer_end
target_mask_hash
```

如果答案只有一个 token，`CR_seq` 与 `CR_first_token` 通常接近。  
如果答案包含多个 token，二者可能不同，此时以 `CR_seq` 为主。

### 37.5 多 token 答案统计

每个 `model / dataset` 的 `summary.md` 中应统计：

```text
single_token_answer_ratio
multi_token_answer_ratio
topk_overlap_cr_seq_vs_first_token
spearman_corr_cr_seq_vs_first_token
```

其中：

- `topk_overlap_cr_seq_vs_first_token` 用于观察传统 CMA 口径与完整序列口径的候选层一致性；
- `spearman_corr_cr_seq_vs_first_token` 用于观察两种评分在全层排序上的相关性。

### 37.6 论文表述

英文：

```text
To maintain compatibility with classical Causal Tracing, we additionally compute a first-target-token restoration score. However, since multimodal editing targets often consist of multiple tokens, our primary CMA-Direct score is computed over the complete target answer sequence under teacher forcing. Both scores are computed from the same clean, corrupted, and restored forward passes; no additional restoration forward pass is performed for the first-token score. We therefore report the first-token score only as a compatibility analysis with traditional factual-recall localization, while using the sequence-level score for candidate-layer ranking.
```

中文：

```text
为兼容经典 Causal Tracing 在事实回忆场景中常用的目标 object token 评分口径，本文额外计算目标答案首 token 的恢复分数。然而，由于多模态编辑目标通常包含多个 token，本文将 teacher-forcing 下完整目标答案序列的恢复分数作为 CMA-Direct 的主指标。首 token 恢复分数与完整序列恢复分数由同一批 clean、corrupt 和 restore 前向结果计算，不额外执行恢复前向传播。因此，本文仅将首 token 分数作为与传统事实回忆定位设置对齐的兼容性分析，而使用序列级分数进行候选层排序。
```

### 37.7 最终实施要求

最终实现必须满足：

```yaml
score_metrics:
  primary: CR_seq
  auxiliary:
    - CR_first_token
    - KCR_seq

ranking:
  primary_rank: rank_by_cr_seq
  auxiliary_ranks:
    - rank_by_cr_first_token
    - rank_by_kcr_seq

forward_reuse:
  cr_first_token_from_same_forward: true
  extra_restore_forward_for_first_token: false
```

一句话总结：

> 当前 CMA-Direct 主实验保持完整答案序列 `CR_seq`；为了兼容传统 CMA，新增 `CR_first_token` 作为辅助评分。二者由同一次前向结果同时计算，几乎不增加时间开销。



---

## 38. v1.3 相对 v1.2 的唯一术语修订

本版本只做命名与回填字段统一，不改变 `CMA-Direct / Visual Causal Restoration` 的实验流程、恢复范围和主排序逻辑。

### 38.1 修订内容

将候选层总表与输出文件中的主排序字段统一为：

```text
cr_seq_mean
```

不再使用：

```text
CR_mean
```

原因是 `CR_mean` 语义过宽，可能被误解为 `CR_seq`、`CR_first_token` 或 `KCR_seq` 的任意均值。正式候选层排序应明确表示为完整目标答案序列恢复分数的均值，即 `cr_seq_mean`。

### 38.2 保持不变的内容

以下内容相对 v1.2 不变：

- 主实验仍计算完整目标答案序列恢复分数 `CR_seq`；
- 主排序仍使用 `rank_by_cr_seq`；
- `CR_first_token` 仍仅作为传统 Causal Tracing / CMA 兼容性辅助指标；
- `KCR_seq` 仍仅作为完整答案序列 KL 恢复率辅助诊断；
- clean / corrupt / restore 三类前向流程不变；
- 主实验仍恢复指定 decoder 层输出后的全部 visual-token hidden states；
- 单视觉 token 恢复仍只作为可选变体，不进入 7 models × 3 datasets 主实验；
- CMA-Direct 仍采用 Direct 口径，不做 Pre-shift。

### 38.3 总表推荐写法

在 `6location_7model_3datas_top_3_5_layers_outcome.md` 的 `CMA-Direct` 部分，推荐写作：

```text
该方法参考 `md/Location/Equations/CMA-Direct_v1.3.md`，使用 Visual Causal Restoration / Causal Mediation Analysis 风格的污染-恢复实验，按 `cr_seq_mean` 直接选择完整目标答案序列因果恢复分数最高的层作为候选层；`cr_first_token_mean` 和 `kcr_seq_mean` 仅作为辅助诊断。该方法只污染 decoder 输入端 visual tokens，恢复 decoder block output 的 visual-token hidden states，不执行 Pre 偏移。当前尚未回填候选层；逐模型待补登记后续可并入 2.11。
```

一句话总结：

> v1.3 只把候选层回填字段从 `CR_mean` 统一为 `cr_seq_mean`，以明确主排序基于完整目标答案序列恢复分数；实验算法本身不变。
