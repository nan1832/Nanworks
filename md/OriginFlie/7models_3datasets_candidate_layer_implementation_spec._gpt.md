# 7 Models × 3 Datasets 候选层实验实施级补充规范

> 本文件是《编辑层定位方法候选层计算手册（修订版）》的工程实施补充。  
> 目标是让 7 个视觉语言模型在 E-VQA/pilot500、MMKE-Visual、MMKE-Entity 上使用同一套可复现协议计算 Top-3、Top-5 候选 adapter 插入层。

---

## 1. 启动全部实验前必须完成的事项

在启动 `7 models × 3 datasets = 21` 个组合前，必须先完成：

1. 七模型精确注册表；
2. 每个模型的 visual-token 区间提取与单元测试；
3. teacher forcing 目标 token 对齐；
4. `model_pred` 的确定性生成与缓存；
5. SaLEM、LGA、Perturb-KL、Ours 的实现细节冻结；
6. `pilot500 × BLIP2-OPT` 单配置验收。

通过验收后再扩展到其余组合。

---

# 2. 七模型注册表

每个模型建立固定注册记录：

```yaml
model_name:
checkpoint_id:
revision:
processor_id:
tokenizer_id:
language_model_path:
decoder_layer_path:
num_decoder_layers:
hidden_size:
mlp_parameter_patterns:
attention_parameter_patterns:
vision_encoder_path:
projector_or_qformer_path:
visual_token_rule:
adapter_hook_position:
chat_template:
image_size_or_visual_budget:
dtype:
quantization:
transformers_version:
torch_version:
```

建议同时记录归一化层深：

\[
d_l=\frac{l+0.5}{L}.
\]

跨模型分析优先比较 \(d_l\)，不要只比较绝对层号。

---

# 3. Adapter 层号统一定义

候选层 \(L_l\) 的统一含义：

\[
\hat h_i^{\,l}
=
h_i^{\,l}
+
A_l(h_i^{\,l}),
\]

\[
h_i^{\,l+1}
=
\operatorname{Block}_{l+1}
\left(\hat h_i^{\,l}\right).
\]

即：

> `candidate layer = l` 表示 adapter 位于 decoder block \(l\) 输出之后、block \(l+1\) 之前。

扰动、hidden-state 梯度和 adapter hook 必须使用同一张量位置，避免 off-by-one。

---

# 4. Visual-token 区间

## 4.1 必须记录

```text
sample_id
visual_token_start
visual_token_end
visual_token_count
visual_token_mask
visual_token_source
sequence_length
prompt_token_count
target_token_count
```

## 4.2 模型类型

- BLIP2、InstructBLIP、MiniGPT-4：visual tokens 指进入文本解码器后的视觉查询/投影 token，不是 vision encoder patch token。
- LLaVA：visual tokens 指图像占位符展开后的视觉 embedding。
- Qwen2.5-VL：固定分辨率或固定视觉 token 预算。
- PaliGemma、SmolVLM：按其 processor 和输入拼接规则确定视觉前缀/视觉 token。

## 4.3 单元测试

每个模型 wrapper 必须通过：

1. `visual_token_count` 与实际进入语言模型的视觉 embedding 数一致；
2. \(\nabla_{h_{i,l}^{v}}\mathcal L_i\) 不为 `None` 且非全零；
3. 对 visual tokens 加噪声后输出发生变化；
4. 对空 visual mask 扰动时输出不变；
5. adapter 与扰动 hook 位于同一层间位置。

未通过时不得启动 Perturb-KL 或 Ours 的批量实验。

---

# 5. Teacher Forcing 与目标 Token 对齐

## 5.1 目标损失

\[
\mathcal L_i(y_i)
=
-\frac{1}{T_i}
\sum_{t=1}^{T_i}
\log
P_\theta
\left(
y_{i,t}
\mid
x_i^v,x_i^t,y_{i,<t}
\right).
\]

## 5.2 对齐规则

对于 causal LM：

```text
shift_logits = logits[..., :-1, :]
shift_labels = labels[..., 1:]
```

只对目标答案 token 计算损失：

```text
prompt labels = -100
visual token labels = -100
padding labels = -100
```

## 5.3 必须固定

```text
include_bos_in_loss
include_eos_in_loss
padding_side
max_target_tokens
truncation_side
```

并记录：

```text
original_target_length
effective_target_length
truncated
truncation_reason
```

## 5.4 主方法统一目标范围

以下方法必须使用同一 `alt` token mask：

```text
VisEdit-Contrib-Pre-AltSeq
SaLEM-Alt-Direct
LGA-Param-Direct-AltModelPred（new side）
Perturb-KL-Direct-AltSeq
Ours-Direct（new side）
```

---

# 6. `model_pred` 生成协议

## 6.1 确定性生成

```yaml
do_sample: false
num_beams: 1
temperature: null
top_p: null
top_k: null
max_new_tokens: fixed
use_cache: true
repetition_penalty: 1.0
stop_tokens: model-specific fixed list
```

## 6.2 缓存字段

```text
sample_id
model
raw_model_pred
normalized_model_pred
model_pred_token_ids
model_pred_length
generation_config_hash
already_matches_alt
empty_model_pred
invalid_model_pred
```

## 6.3 特殊情况

- 空输出：标记 `invalid_model_pred`，不得自动替换为 `pred`。
- 已等于 `alt`：保留样本并记录。
- 超长输出：按预设上限截断并记录。
- 不同模型必须使用同一批样本 ID。

建议汇总：

```text
total_samples
valid_model_pred_count
empty_model_pred_count
already_matches_alt_count
truncated_model_pred_count
```

---

# 7. SaLEM 实施规范

## 7.1 方法命名

只比较 MLP 参数时使用：

```text
SaLEM-MLP-Alt-Direct
```

如比较完整 block，另命名：

```text
SaLEM-Block-Alt-Direct
```

## 7.2 主参数范围

```text
include_mlp_weights = true
include_attention_weights = false
include_bias = false
include_layernorm = false
include_embedding = false
include_lm_head = false
include_adapter = false
```

## 7.3 显著性聚合

参数级：

\[
s_{i,l,m,r,c}
=
\left|
\frac{
\partial\mathcal L_i^{new}
}{
\partial W_{l,m}[r,c]
}
\right|.
\]

列级：

\[
s_{i,l,m,c}^{col}
=
\frac{1}{d_{out}^{l,m}}
\sum_{r=1}^{d_{out}^{l,m}}
s_{i,l,m,r,c}.
\]

层级主公式采用所有列等权：

\[
s_{i,l}^{layer}
=
\frac{
\sum_m\sum_{c=1}^{C_{l,m}}
s_{i,l,m,c}^{col}
}{
\sum_m C_{l,m}
}.
\]

数据集级：

\[
S_{\mathrm{SaLEM}}(l)
=
\frac1N\sum_i s_{i,l}^{layer}.
\]

候选层：

\[
\mathcal C_{\mathrm{SaLEM},K}
=
\operatorname{TopK}_l S_{\mathrm{SaLEM}}(l).
\]

SaLEM 主版本不做 Pre。

## 7.4 梯度实现

```text
model.eval()
target MLP weights requires_grad = true
optimizer does not include base weights
no optimizer.step()
create_graph = false
score accumulation = float32
clear gradients after every sample
```

---

# 8. LGA 实施规范

## 8.1 主方法

```text
LGA-Param-Direct-AltModelPred
score_space = param_mlp_ffn
target_parameter_scope = mlp_ffn_weight_only
```

## 8.2 每样本梯度

\[
g_{i,l}^{old}
=
\nabla_{W_l}
\mathcal L_i^{old},
\qquad
g_{i,l}^{new}
=
\nabla_{W_l}
\mathcal L_i^{new}.
\]

每样本内积：

\[
\phi_{i,l}
=
\left\langle
g_{i,l}^{old},
g_{i,l}^{new}
\right\rangle.
\]

数据集级：

\[
S_{\mathrm{LGA}}(l)
=
\frac1N\sum_i\phi_{i,l}.
\]

必须先对每个样本求 dot，再跨样本平均。禁止计算：

\[
\left\langle
\frac1N\sum_i g_{i,l}^{old},
\frac1N\sum_i g_{i,l}^{new}
\right\rangle.
\]

## 8.3 Raw Dot

```text
dot_normalization = none
```

不除以参数维度，不取绝对值。若全层为负，仍按从大到小排序。

## 8.4 Tukey 异常层处理

同时保存：

```text
score_lga_raw
score_lga_tukey_filtered
```

\[
IQR=Q_3-Q_1,
\]

\[
\mathrm{Lower}=Q_1-\kappa IQR,
\qquad
\mathrm{Upper}=Q_3+\kappa IQR.
\]

默认：

\[
\kappa=1.
\]

记录：

```text
tukey_constant
q1
q3
iqr
lower_fence
upper_fence
excluded_layers
raw_rank
filtered_rank
```

## 8.5 Proxy Set

如采用约 10% proxy，必须预先固定：

```text
proxy_sample_ids
proxy_seed
proxy_ratio
```

若其他方法使用完整 localization set，论文中必须明确样本量差异。

## 8.6 低显存实现

```text
for sample:
    for layer:
        compute grad_old for W_l
        compute grad_new for W_l
        compute dot scalar
        accumulate scalar on CPU
        delete temporary gradients
```

异常梯度不得记为 0：

```text
status = unavailable
failure_reason = unused_or_unreachable_mlp_parameters
```

---

# 9. Perturb-KL 实施规范

## 9.1 主方法

```text
Perturb-KL-Direct-AltSeq
```

Direct 是主版本，Pre 仅作消融。

## 9.2 扰动位置

噪声加入 block \(l\) 输出后、block \(l+1\) 前，与 adapter 位置一致。

## 9.3 噪声尺度

对：

\[
h_{i,l}^{v}
\in\mathbb R^{N_{v,i}\times d},
\]

计算单样本、单层标量标准差：

\[
\sigma_{i,l}^{v}
=
\operatorname{Std}
\left(
h_{i,l}^{v}
\text{ over all }N_{v,i}\times d\text{ elements}
\right),
\]

固定：

```text
unbiased = false
```

噪声：

\[
\epsilon_{i,l}^{\alpha,r}
\sim
\mathcal N
\left(
0,
(\alpha\sigma_{i,l}^{v})^2
\right).
\]

默认：

\[
\alpha\in\{0.1,0.5,1,3\},
\qquad R=3.
\]

## 9.4 可复现种子

```text
noise_seed = hash(dataset, subset, model, sample_id, layer, alpha, repeat)
```

种子不得依赖 batch 顺序。

## 9.5 KL 方向与精度

固定：

\[
D_{\mathrm{KL}}
\left(
p_{\mathrm{clean}}
\Vert
p_{\mathrm{perturbed}}
\right).
\]

实现：

```text
logits -> float32
softmax/log_softmax -> float32
padding positions masked
complete vocabulary used
```

## 9.6 聚合顺序

先 token 平均：

\[
D_{i,l}^{\alpha,r}
=
\frac1{T_i}
\sum_t
D_{\mathrm{KL}}
\left(
p_{i,t}^{clean}
\Vert
p_{i,l,t}^{\alpha,r}
\right).
\]

再样本平均：

\[
S_{\mathrm{KL}}^{\alpha,r}(l)
=
\frac1N\sum_i D_{i,l}^{\alpha,r}.
\]

最后在每个 \((\alpha,r)\) 内做层间归一化并平均。

## 9.7 无 fallback

主表只允许：

```text
perturb_scope = visual_tokens
```

visual-token 区间不可用时：

```text
status = unavailable
```

不得改为 `all_prompt_tokens` 后仍标成同一方法。

---

# 10. VisEdit-Contrib 实施补充

必须确认现有结果属于：

```text
VisEdit-Contrib-Pre-AltKeyToken
```

还是：

```text
VisEdit-Contrib-Pre-AltSeq
```

若只使用首 token/key token，不能标成 AltSeq。

两种方案：

1. 重新计算完整 `alt` 序列，统一使用 AltSeq；
2. 保留已有 key-token 结果，并将方法名写清楚。

高贡献阈值：

\[
\tilde S(l)\ge\mu+\lambda\sigma,
\qquad \lambda=0.5.
\]

建议在一个代表性配置上测试：

\[
\lambda\in\{0,0.25,0.5,0.75,1.0\}.
\]

如 Pre 候选不足，保留：

```text
raw_candidate_layers
clean_candidate_layers
fill_rule
status = insufficient_pre_layers
```

---

# 11. Ours-Direct 实施规范

## 11.1 主方法

```text
method = Ours-Direct
variant = direct
```

本文公式直接预测适合挂 adapter 的层，不做 Pre。

## 11.2 梯度

\[
g_{i,l}^{new}
=
\nabla_{h_{i,l}^{v}}
\mathcal L_i^{new},
\qquad
g_{i,l}^{old}
=
\nabla_{h_{i,l}^{v}}
\mathcal L_i^{old}.
\]

## 11.3 公式冻结

\[
S_{\mathrm{ours}}(l)
=
\max
\left(
0,
-
S_{\cos}^{v}(l)
\right)
\cdot
S_{\mathrm{new\text{-}norm}}^{v}(l)
\cdot
\left(
\frac{l+1}{L}
\right)^2.
\]

正式批量运行前固定：

```text
cosine sign = negative
depth exponent = 2
new norm = L2
visual token aggregation = mean
dataset aggregation = mean
candidate conversion = direct Top-K
old_field = model_pred
```

不得在查看结果后调整。

## 11.4 诊断量

保存：

```text
score_cosine
score_negative_cosine
score_new_norm
score_depth_weight
score_ours
```

---

# 12. 梯度与数值设置

```text
model.eval()
dropout disabled
no optimizer step during localization
use_cache = false during teacher-forcing backward
forward dtype = bf16 or fp16
score accumulation = float32
```

SaLEM 和 LGA 主实验不建议使用 4-bit/8-bit 量化权重。

遇到 `NaN/Inf/None gradient/empty visual span` 时，必须记录：

```text
status
failure_reason
sample_id
layer
method
```

不得默认为 0 后继续排序。

---

# 13. Adapter 公平性

## 13.1 同一模型内部

所有候选层使用：

```text
same adapter architecture
same bottleneck/rank
same parameter count
same initialization
same optimizer
same training schedule
```

## 13.2 跨模型

跨模型统一设计原则和 bottleneck ratio，而非强行统一绝对参数量。

记录：

```text
adapter_rank
adapter_bottleneck_ratio
adapter_parameter_count
adapter_parameter_percentage
```

同一层只训练一次，结果回填给所有推荐该层的方法。

---

# 14. Checkpoint 选择

最终 test/eval 不得用于 checkpoint 选择。

可选：

1. 固定 adapter validation；
2. 固定步数并使用最后 checkpoint；
3. 使用预先定义的训练/验证损失。

记录：

```text
checkpoint_selection_rule
best_checkpoint
selection_metric
selection_split
```

---

# 15. 随机层基线

建议增加：

```text
Random-Uniform-TopK
```

从合法 decoder 层均匀无放回采样，重复至少 30 次，报告：

\[
\operatorname{Mean@K}_{random}
\pm95\%\mathrm{CI}.
\]

---

# 16. 定位成本

每种方法记录：

```text
localization_wall_time_seconds
peak_gpu_memory_mb
forward_pass_count
backward_pass_count
processed_sample_count
samples_per_second
disk_output_size_mb
```

---

# 17. 输出文件补充

## 17.1 `model_registry.yaml`

包含所有模型注册字段。

## 17.2 `sample_manifest.csv`

```text
dataset
subset
sample_id
image_path
prompt
alt
pred
model_pred
valid_model_pred
already_matches_alt
visual_token_start
visual_token_end
visual_token_count
target_token_count
```

## 17.3 `layer_scores.csv`

增加：

```text
localization_sample_count
proxy_ratio
proxy_seed
dtype
quantization
visual_token_rule
target_mask_hash
config_hash
score_raw
score_filtered
excluded_by_tukey
status
failure_reason
```

## 17.4 `candidate_layers_topk.csv`

增加：

```text
raw_rank
filtered_rank
selection_source
candidate_conversion
pre_region_start
pre_region_end
```

## 17.5 `edit_results_by_layer.csv`

增加：

```text
adapter_parameter_count
adapter_parameter_percentage
checkpoint_selection_rule
selection_metric
localization_config_hash
training_config_hash
evaluation_config_hash
```

---

# 18. 统计分析

每个候选层至少使用 3 个训练 seed：

\[
A(l)
=
\operatorname{mean}_r A_r(l)
\pm
\operatorname{std}_r A_r(l).
\]

方法级指标：

```text
Top1Perf
Mean@3
Mean@5
Best@3
Best@5
Regret@3
Regret@5
Hit@3
Hit@5
```

跨组合汇总：

1. 每个 `dataset × model` 单独计算；
2. 再做 macro-average；
3. 报告 bootstrap 95% CI；
4. Ours 与每个 baseline 做 paired bootstrap 或 Wilcoxon signed-rank test。

---

# 19. Pilot 验收

在：

```text
E-VQA/pilot500 × BLIP2-OPT-2.7B
```

上完成：

| 检查项 | 通过标准 |
|---|---|
| 模型注册 | checkpoint、revision、模块路径完整 |
| 层编号 | adapter、扰动、hidden hook 无 off-by-one |
| visual-token mask | 数量正确，梯度非空 |
| teacher forcing | target mask 与有效 token 一致 |
| model_pred | 重复生成一致 |
| VisEdit | AltKeyToken/AltSeq 命名正确 |
| SaLEM | 所有合法层分数有限 |
| LGA | per-sample dot 正确，raw/Tukey 均保存 |
| Perturb-KL | 各尺度无 NaN/Inf，batch size 不影响噪声 |
| Ours | 公式、符号、深度项、Direct 规则一致 |
| Adapter | 同一模型各层参数量一致 |
| Checkpoint | 未使用 test/eval 选择 |
| 输出追踪 | 可由结果反查全部配置 |
| 复现 | 相同 seed 重跑候选层一致 |

---

# 20. 推荐运行顺序

1. 模型注册、数据 manifest、`model_pred` 缓存；
2. visual-token 和 teacher-forcing 单元测试；
3. `pilot500 × BLIP2` 六种主方法定位；
4. 训练 Top-3 并集；
5. 补充 Top-5 并集；
6. 完成一次 Full-layer Oracle；
7. 扩展到 7 模型；
8. 扩展到 3 数据集；
9. 运行消融；
10. 统计分析与论文图表。

---

# 21. 最终检查清单

## 数据与模型

- [ ] 七模型 checkpoint/revision 已冻结。
- [ ] 三数据集 split 已冻结。
- [ ] `model_pred` 已缓存。
- [ ] visual-token mask 已通过测试。
- [ ] teacher-forcing 对齐已通过测试。

## 方法

- [ ] VisEdit 的 AltKeyToken/AltSeq 名称准确。
- [ ] SaLEM 参数范围与方法名一致。
- [ ] SaLEM 使用所有列等权聚合。
- [ ] LGA 按样本先 dot、再平均。
- [ ] LGA 保存 raw 和 Tukey-filtered 排名。
- [ ] Perturb-KL 标准差轴和种子规则已固定。
- [ ] Perturb-KL 使用 clean-to-perturbed KL。
- [ ] Ours 使用负余弦、new norm、depth²。
- [ ] Ours 直接输出 adapter 层，不做 Pre。

## 真实编辑

- [ ] 同一模型各层 adapter 参数量一致。
- [ ] 每层至少 3 个训练 seed。
- [ ] checkpoint 不由 test/eval 选择。
- [ ] Candidate-union Oracle 与 Full-layer Oracle 已区分。

## 结果

- [ ] 报告 Top1、Mean@K、Best@K。
- [ ] 报告 Regret@K、Hit@K。
- [ ] 跨组合使用 macro-average。
- [ ] 报告 95% CI。
- [ ] 记录定位时间和峰值显存。
- [ ] 添加 Random-Uniform-TopK 基线。
