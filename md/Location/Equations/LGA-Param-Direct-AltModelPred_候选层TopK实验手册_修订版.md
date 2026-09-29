# LGA-Param-Direct-AltModelPred 候选层 Top-K 实验手册（修订版）

<!-- LGA_TUKEY_CORRECTION_20260926 -->
> **LGA 版本更正（2026-09-26）：** 本文件历史 LGA 候选及比较采用未做 Tukey 的 Raw 版本，不能作为完整 LGA 复现。论文要求的 Tukey 过滤已单独补算，当前规则以 [2026-09-26 Tukey 补正手册](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/Equations/LGA-Param-Tukey_候选层补正手册_20260926.md>) 为准，结果见 [21 组补正结果](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/lga_tukey_correction_20260926/LGA_Tukey补正报告.md>)。旧表保留用于追溯和 Raw 消融；旧的 LGA 优劣结论须按新候选重算。 **下文未经 Tukey 的执行规定已废止为正式 LGA 规则，仅描述历史 Raw 实验。**


> 适用于：`E-VQA / pilot500`、`MMKE-Visual`、`MMKE-Entity`  
> 适用于模型：BLIP2-OPT-2.7B、InstructBLIP-Vicuna-7B、MiniGPT-4-Vicuna-7B、LLaVA-v1.5-7B、Qwen2.5-VL-3B-Instruct、PaliGemma-3B、SmolVLM-Instruct-1.7B  
> 输出目标：为每个 `dataset × model` 组合计算原始 LGA 参数空间候选编辑层 `Top-3 / Top-5`，作为视觉表征 adapter 编辑层定位的参数空间强基线。

---

## 0. 本手册修订目的

本手册用于将原始 `LGA候选层TopK计算公式.md` 修订为与总手册 `6edit_layer_localization_candidate_methods_简洁说明版.md` 完全一致的实验执行版。

核心修订原则如下：

1. 原始 LGA 主基线必须是 **参数空间 LGA**，即层参数梯度内积；不能把 hidden-state 梯度版本称为原始 LGA。
2. 主实验名称统一为：

```text
LGA-Param-Direct-AltModelPred
```

3. 新知识统一使用 `alt`，旧知识统一使用冻结基础模型确定性生成并缓存的 `model_pred`。
4. LGA 的梯度对象是 decoder block 的 MLP/FFN weight 参数，不是 visual-token hidden states。
5. 主排序使用未经维度归一化、未经 Tukey 过滤的 old/new 参数梯度 raw dot。
6. cosine、old/new norm、维度归一化 dot、Tukey-filtered ranking 只作为诊断输出，不替代主排序。
7. LGA 候选层直接用于 adapter 插入层，不执行 Pre 偏移。

本设置用于公平回答以下问题：

> 原始 LGA 的参数空间梯度内积，是否能够准确预测视觉表征 adapter 的最佳插入层？

如果该基线在真实编辑扫层后无法稳定覆盖 oracle 层，则可支持论文中的 `intervention-space mismatch` 论点：原始 LGA 的归因空间是参数空间，而本文真实编辑发生在视觉表征空间。

---

## 1. 方法定位

### 1.1 原始 LGA 的核心思想

原始 Layer Gradient Analysis（LGA）通过比较旧知识和新知识在某一层参数上的梯度相似性来估计 golden layer。其基本形式为：

\[
S_L
=
\sum_i
\left\langle
\nabla_{\theta_L}\mathcal L_i^{old},
\nabla_{\theta_L}\mathcal L_i^{new}
\right\rangle.
\]

分数越高，表示该层参数同时受到旧知识与新知识的强关联影响，因此被认为更适合进行参数编辑。

### 1.2 本实验中的 LGA 角色

本文不是直接使用 ROME / MEMIT 等参数编辑，而是在视觉语言模型的 decoder 层间插入视觉编辑 adapter。因此，原始 LGA 在本文中作为 **参数空间层定位基线**：

```text
method = LGA-Param-Direct-AltModelPred
score_space = param_mlp_ffn
target_parameter_scope = mlp_ffn_weight_only
candidate_conversion = direct
```

它不代表本文的视觉表征方法，也不应与 `Ours-VisualGradient-Direct` 混淆。

### 1.3 与 Ours-VisualGradient-Direct 的边界

| 项目 | LGA-Param-Direct-AltModelPred | Ours-VisualGradient-Direct |
|---|---|---|
| 梯度对象 | MLP/FFN 参数 \(W_l\) | visual-token hidden states \(h_l^v\) |
| 分数空间 | 参数空间 | 视觉表征空间 |
| 旧知识 | `model_pred` | `model_pred` |
| 新知识 | `alt` | `alt` |
| 主信号 | old/new 参数梯度 raw dot | 视觉梯度方向、强度、深度等 |
| 候选层转换 | Direct | Direct |
| 论文角色 | 原始 LGA 强基线 | 本文视觉表征定位方法 |

---

## 2. 实验范围

### 2.1 数据集

主实验覆盖三个数据集：

```text
E-VQA / pilot500
MMKE-Visual
MMKE-Entity
```

每个数据集统一抽象为：

\[
\mathcal D
=
\{(x_i^v,x_i^t,y_i^{new},y_i^{old})\}_{i=1}^{N}.
\]

| 符号 | 字段 | 含义 |
|---|---|---|
| \(x_i^v\) | `image` | 图像输入 |
| \(x_i^t\) | `src` | 编辑问题 / prompt |
| \(y_i^{new}\) | `alt` | 新知识目标 |
| \(y_i^{old}\) | `model_pred` | 冻结基础模型当前输出 |

### 2.2 模型

主实验覆盖七个 VLM：

```text
BLIP2-OPT-2.7B
InstructBLIP-Vicuna-7B
MiniGPT-4-Vicuna-7B
LLaVA-v1.5-7B
Qwen2.5-VL-3B-Instruct
PaliGemma-3B
SmolVLM-Instruct-1.7B
```

所有模型只比较语言解码器层：

```text
layer_space = text_decoder
```

若模型包含 Q-Former，例如 BLIP2、InstructBLIP、MiniGPT-4，主实验仍只比较 text decoder 层；Q-Former 层若另算，必须单独报告为：

```text
layer_space = qformer
```

---

## 3. 层编号与 adapter 插入位置

设语言解码器共有 \(L\) 个 Transformer blocks，候选层编号为 0-indexed：

\[
l\in\{0,1,\ldots,L-1\}.
\]

本实验中：

```text
candidate layer = l
```

统一表示 adapter 接在 decoder block \(l\) 的输出之后、decoder block \(l+1\) 之前。

形式化表示为：

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
\operatorname{Block}_{l+1}(\hat h_i^{\,l}).
\]

虽然 LGA 本身计算的是参数梯度，但它输出的候选层必须与最终 adapter 插入层编号一致，避免 off-by-one。

---

## 4. 数据字段规则

### 4.1 新知识字段

LGA 主实验的新知识统一使用：

```text
new_field = alt
```

即：

\[
y_i^{new}=\texttt{alt}_i.
\]

### 4.2 旧知识字段

LGA 主实验旧知识统一使用冻结基础模型确定性生成并缓存的：

```text
old_field = model_pred
```

即：

\[
y_i^{old}=\texttt{model\_pred}_i.
\]

`model_pred` 必须在候选层定位前统一生成，不允许在不同方法内部重复生成。

推荐确定性解码设置：

```yaml
do_sample: false
num_beams: 1
temperature: 0 or unset
fixed_max_new_tokens: true
fixed_stop_tokens: true
fixed_prompt_template: true
```

缓存字段至少包括：

```text
sample_id
raw_text
normalized_text
token_ids
effective_token_length
empty_or_invalid_status
prompt_template_hash
generation_config_hash
```

### 4.3 `pred` 字段的处理

数据集自带 `pred` 不能等同于当前实验模型的实时输出。主实验不得默认使用 `pred`。

在 `pred` 非空且语义有效的数据集上，可以额外计算：

```text
LGA-Param-Direct-AltPred
```

但必须单独成表、单独命名、不得混入主排序。

尤其是 `MMKE-Visual` 中，`pred` 经常为空或无效。不得将空字符串作为旧知识，也不得静默填充为 `alt`。

---

## 5. Teacher-forcing 损失定义

### 5.1 VLM 输入形式

LGA 在本文中不是纯文本输入 `Q ∪ K`，而是 VLM 输入：

```text
image + src + target answer
```

旧知识损失：

\[
\mathcal L_i^{old}
=
\mathcal L
\left(
M(x_i^v,x_i^t)\rightarrow y_i^{old}
\right).
\]

新知识损失：

\[
\mathcal L_i^{new}
=
\mathcal L
\left(
M(x_i^v,x_i^t)\rightarrow y_i^{new}
\right).
\]

### 5.2 完整答案序列损失

对目标序列 \(y_i=(y_{i,1},\ldots,y_{i,T_i})\)，使用长度归一化 teacher-forcing 自回归负对数似然：

\[
\mathcal L_i(y_i)
=
-
\frac{1}{T_i}
\sum_{t=1}^{T_i}
\log P_\theta
\left(
y_{i,t}\mid x_i^v,x_i^t,y_{i,<t}
\right).
\]

长度归一化用于避免 MMKE-Entity 等长答案样本因 token 数更多而产生更大梯度。

### 5.3 标签 mask 规则

对于 causal LM：

```python
shift_logits = logits[..., :-1, :]
shift_labels = labels[..., 1:]
```

标签必须满足：

```text
prompt labels = -100
visual token labels = -100
padding labels = -100
answer token labels = target token id
```

只对答案 token 计算 loss。

必须记录以下字段：

```text
include_bos_in_loss
include_eos_in_loss
padding_side
max_target_tokens
truncation_side
original_target_length
effective_target_length
truncated
truncation_reason
target_mask_hash
```

`alt`、`model_pred`、`pred` 的 token mask 必须分别缓存，不能运行时临时重切导致 old/new 梯度不对齐。

---

## 6. 参数范围

### 6.1 主实验参数集合

LGA 主实验只比较每个 decoder block 的 MLP/FFN weight 参数：

```text
score_space = param_mlp_ffn
target_layer_type = mlp_ffn
target_parameter_scope = mlp_ffn_weight_only
include_bias = false
include_attention = false
include_layernorm = false
include_adapter = false
```

即第 \(l\) 层参数集合写为：

\[
W_l=\{W_{l,1},W_{l,2},\ldots,W_{l,M_l}\}.
\]

### 6.2 各模型 MLP/FFN 参数映射

不同模型的参数名不同，但必须映射到同一语义对象。

| 模型 / 模型族 | MLP/FFN weight 示例 |
|---|---|
| BLIP2-OPT | `fc1.weight`, `fc2.weight` |
| InstructBLIP-Vicuna | `gate_proj.weight`, `up_proj.weight`, `down_proj.weight` |
| MiniGPT-4-Vicuna | `gate_proj.weight`, `up_proj.weight`, `down_proj.weight` |
| LLaVA-v1.5 | `gate_proj.weight`, `up_proj.weight`, `down_proj.weight` |
| Qwen2.5-VL | decoder block 内 `mlp.gate_proj/up_proj/down_proj.weight` |
| PaliGemma / Gemma-like | decoder block 内 `mlp.gate_proj/up_proj/down_proj.weight` |
| SmolVLM | language decoder block 内 MLP/FFN weights |

每个模型必须在 `model_registry.yaml` 中显式记录：

```text
model_name
decoder_module_path
num_decoder_layers
valid_layer_index_range
mlp_parameter_patterns
mlp_parameter_names_by_layer
hidden_size
dtype
quantization
wrapper_commit_or_hash
```

若某模型参数命名特殊，必须先补 wrapper，不得临时把 attention 或 whole block 混入主 LGA 分数。

若需要比较 attention 或 whole block，必须另开方法名：

```text
LGA-Param-Direct-AltModelPred-Attn
LGA-Param-Direct-AltModelPred-BlockAll
```

它们不得进入原始 LGA 主基线。

---

## 7. LGA 主公式

### 7.1 单样本、单层参数梯度

对第 \(i\) 个样本、第 \(l\) 层 MLP/FFN 参数集合 \(W_l\)：

\[
g_{i,l}^{old}
=
\nabla_{W_l}
\mathcal L_i^{old},
\]

\[
g_{i,l}^{new}
=
\nabla_{W_l}
\mathcal L_i^{new}.
\]

展平后，单样本层分数为：

\[
\phi_{i,l}
=
\left\langle
\operatorname{vec}(g_{i,l}^{old}),
\operatorname{vec}(g_{i,l}^{new})
\right\rangle.
\]

### 7.2 数据集级主分数

主实验使用逐样本 dot 后再平均：

\[
S_{\mathrm{LGA}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\phi_{i,l}.
\]

即：

\[
S_{\mathrm{LGA}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\langle
\nabla_{W_l}\mathcal L_i^{old},
\nabla_{W_l}\mathcal L_i^{new}
\right\rangle.
\]

主排序字段为：

```text
rank_metric = raw_old_new_parameter_gradient_dot
dot_normalization = none
cross_model_score_comparable = false
```

注意：必须先对每个样本算 dot，再对样本平均；不得先平均 old 梯度和 new 梯度后再做 dot。

### 7.3 候选层

按照主分数从大到小排序：

\[
\operatorname{Rank}_{\mathrm{LGA}}
=
\operatorname{argsort}_l
\left(S_{\mathrm{LGA}}(l)\right)_{desc}.
\]

Top-K 候选层为：

\[
\mathcal C_{\mathrm{LGA},K}
=
\{L_1,L_2,\ldots,L_K\},
\]

其中：

\[
S_{\mathrm{LGA}}(L_1)
\ge
S_{\mathrm{LGA}}(L_2)
\ge
\cdots
\ge
S_{\mathrm{LGA}}(L_K).
\]

实际代码必须使用：

```python
top3 = ranked_layers[:3]
top5 = ranked_layers[:5]
```

不得写成：

```python
top3 = ranked_layers[1:3]
top5 = ranked_layers[1:5]
```

否则会错误排除 Top-1。

### 7.4 负分数处理

如果所有层分数均为负，仍按数值从大到小排序。

例如：

```text
-0.1 > -0.5 > -2.0
```

不得改成绝对值排序。

### 7.5 候选层转换

LGA 主版本直接选择高分层：

```text
candidate_conversion = direct
```

不执行 Pre 偏移。

---

## 8. 辅助诊断指标

以下指标可以保存，但不得替代主排序。

### 8.1 参数梯度 cosine

\[
S_{\mathrm{LGA\text{-}cos}}(l)
=
\frac{1}{N}
\sum_i
\frac{
\left\langle g_{i,l}^{old},g_{i,l}^{new}\right\rangle
}{
\left\|g_{i,l}^{old}\right\|_2
\left\|g_{i,l}^{new}\right\|_2
+
\epsilon
}.
\]

用途：解释 old/new 参数梯度方向关系。

### 8.2 old/new 梯度范数

\[
S_{old\text{-}norm}(l)
=
\frac{1}{N}
\sum_i
\left\|g_{i,l}^{old}\right\|_2,
\]

\[
S_{new\text{-}norm}(l)
=
\frac{1}{N}
\sum_i
\left\|g_{i,l}^{new}\right\|_2.
\]

用途：判断 raw dot 高分是否主要来自梯度幅值。

### 8.3 维度归一化 dot

\[
S_{dim\text{-}norm}(l)
=
\frac{1}{N}
\sum_i
\frac{1}{|W_l|}
\left\langle g_{i,l}^{old},g_{i,l}^{new}\right\rangle.
\]

用途：诊断不同层参数量差异的影响。

### 8.4 Tukey-filtered ranking

可以保存 Tukey-filtered ranking 作为诊断，但主候选层仍由 raw dot 直接降序得到。

计算：

\[
IQR=Q_3-Q_1,
\]

\[
Lower=Q_1-\kappa IQR,
\qquad
Upper=Q_3+\kappa IQR.
\]

默认：

```text
tukey_constant = 1.0
```

输出记录：

```text
score_lga_raw
score_lga_tukey_filtered
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

严格要求：

```text
主表只使用 raw_top3 / raw_top5。
filtered_top3 / filtered_top5 只作诊断。
不得在看过真实编辑结果后选择 raw 或 filtered 中更好的一个作为主方法。
```

---

## 9. Proxy / localization set 规则

原始 LGA 使用 proxy set 估计 golden layer。本文为了公平比较所有候选层方法，主实验中 LGA 使用与其他方法完全一致的 localization 样本集合。

主实验：

```text
proxy_ratio = 1.0
localization_set = same as other candidate methods
```

低预算诊断可以额外使用：

```text
proxy_ratio = 0.1
proxy_seed = fixed
```

但低预算结果必须单独标记：

```text
experiment_type = low_budget_diagnostic
```

不得混入主候选层表。

---

## 10. 低显存流式实现

### 10.1 基本原则

7B 级 VLM 不能一次性保存所有层、所有样本的 old/new 参数梯度。推荐逐层或逐参数块流式计算，只累计 dot 标量到 CPU。

必须满足：

```text
model.eval()
use_cache = false
dropout disabled
torch.no_grad() disabled for target forward
create_graph = false
retain_graph = false unless explicitly reused
score accumulation dtype = float32 or float64 on CPU
```

主实验不使用 4-bit / 8-bit 量化权重计算 LGA 参数梯度：

```text
SaLEM/LGA weights: no 4-bit/8-bit quantized weights for main gradient scores
```

### 10.2 推荐伪代码

```python
for model in models:
    model.eval()
    model.config.use_cache = False
    registry = load_model_registry(model)
    decoder_layers = registry.valid_layer_index_range

    for dataset in datasets:
        localization_set = load_localization_set(dataset)
        layer_scores = {l: 0.0 for l in decoder_layers}
        layer_counts = {l: 0 for l in decoder_layers}

        for sample in localization_set:
            image = sample["image"]
            src = sample["src"]
            y_old = sample["model_pred"]
            y_new = sample["alt"]

            if invalid(y_old) or invalid(y_new):
                log_skip(sample, reason="empty_old_or_new_target")
                continue

            for l in decoder_layers:
                params = get_mlp_ffn_weight_params(model, layer=l)

                if len(params) == 0:
                    log_layer_failure(l, "missing_mlp_ffn_weight_params")
                    continue

                # old loss: answer-only teacher forcing
                L_old = compute_vlm_teacher_forcing_loss(
                    model=model,
                    image=image,
                    prompt=src,
                    target=y_old,
                    answer_only_mask=True,
                    length_normalized=True,
                )

                grad_old = torch.autograd.grad(
                    L_old,
                    params,
                    retain_graph=False,
                    create_graph=False,
                    allow_unused=True,
                )

                clear_forward_cache_but_keep_model()

                # new loss: answer-only teacher forcing
                L_new = compute_vlm_teacher_forcing_loss(
                    model=model,
                    image=image,
                    prompt=src,
                    target=y_new,
                    answer_only_mask=True,
                    length_normalized=True,
                )

                grad_new = torch.autograd.grad(
                    L_new,
                    params,
                    retain_graph=False,
                    create_graph=False,
                    allow_unused=True,
                )

                if any(g is None for g in grad_old) or any(g is None for g in grad_new):
                    log_layer_failure(l, "unused_or_unreachable_mlp_parameters")
                    continue

                dot = 0.0
                for go, gn in zip(grad_old, grad_new):
                    dot += torch.sum(go.float() * gn.float()).item()

                if not math.isfinite(dot):
                    log_layer_failure(l, "nonfinite_lga_dot")
                    continue

                layer_scores[l] += dot
                layer_counts[l] += 1

                del L_old, L_new, grad_old, grad_new
                torch.cuda.empty_cache()

        for l in decoder_layers:
            if layer_counts[l] > 0:
                layer_scores[l] /= layer_counts[l]
            else:
                mark_unavailable(l, "no_valid_lga_sample")

        ranked = sort_descending_valid_layers(layer_scores)
        top3 = ranked[:3]
        top5 = ranked[:5]

        save_layer_scores(...)
        save_candidates(top3, top5, ...)
```

### 10.3 更高效的实现建议

上面的伪代码清晰但会重复 forward。实际实现可按以下方式优化：

1. 每次只打开一个候选层的 MLP 参数 `requires_grad=True`，其他参数冻结。
2. 以小 batch 计算 old/new loss，然后只对当前层参数求梯度。
3. 将 dot 标量立即累计到 CPU。
4. 完成当前层后释放 graph 和梯度，再进入下一层。
5. 不保存完整梯度张量到磁盘。

无论采用哪种实现，必须保证分数语义仍是：

```text
mean_i dot(grad_Wl L_old_i, grad_Wl L_new_i)
```

而不是：

```text
dot(mean_i grad_Wl L_old_i, mean_i grad_Wl L_new_i)
```

---

## 11. 异常处理

### 11.1 样本级跳过

以下样本不进入 LGA 主分数：

```text
image missing
src empty
alt empty
model_pred empty or invalid
tokenization failed
target token length = 0
teacher-forcing mask empty
```

记录到：

```text
skipped_samples.jsonl
```

字段：

```text
dataset
model
sample_id
skip_reason
old_field
new_field
old_text
new_text
```

### 11.2 层级失败

如果某层出现以下情况，不得静默记为 0：

```text
missing_mlp_ffn_weight_params
unused_or_unreachable_mlp_parameters
grad_old_none
grad_new_none
all_zero_old_gradient
all_zero_new_gradient
nonfinite_lga_dot
```

记录到：

```text
layer_failure_log.jsonl
```

并在 `layer_scores.csv` 中标记：

```text
status = unavailable
failure_reason = ...
```

### 11.3 不允许 fallback

LGA 失败时不得使用以下方式补结果：

```text
Middle-layer Prior fallback
Random fallback
all_prompt_tokens fallback
hidden-state LGA fallback
attention parameter fallback
whole-block parameter fallback
```

如果方法失败，主表必须如实记录：

```text
status = unavailable
```

---

## 12. 输出文件规范

每个 `dataset × model` 组合建议输出到：

```text
server_results/lga_param_direct_altmodelpred/{model}/{dataset}/
```

至少包含：

```text
run_config.yaml
model_registry.yaml
sample_manifest.csv
model_pred_cache.jsonl
layer_scores.csv
candidate_layers_topk.csv
candidates.json
lga_diagnostics.csv
skipped_samples.jsonl
layer_failure_log.jsonl
summary.json
```

### 12.1 `layer_scores.csv`

建议字段：

```text
dataset
subset
model
method
variant
key_mode
new_field
old_field
layer_space
score_space
target_layer_type
target_parameter_scope
include_bias
include_attention
include_layernorm
include_adapter
old_source
rank_metric
dot_normalization
cross_model_score_comparable
layer
score
rank
raw_rank
filtered_rank
score_raw
score_filtered
excluded_by_diagnostic_filter
score_lga_cos
score_old_grad_norm
score_new_grad_norm
score_dim_normalized_dot
localization_sample_count
processed_sample_count
valid_sample_count
skipped_sample_count
proxy_ratio
proxy_seed
target_mask_hash
visual_token_rule
dtype
quantization
config_hash
localization_wall_time_seconds
peak_gpu_memory_mb
forward_pass_count
backward_pass_count
status
failure_reason
score_source_file
```

### 12.2 `candidate_layers_topk.csv`

建议字段：

```text
dataset
subset
model
method
variant
top_k
rank
layer
score
raw_rank
filtered_rank
raw_candidate_layers
clean_candidate_layers
filtered_candidate_layers
dedupe_or_filter_reason
selection_source
candidate_conversion
status
failure_reason
```

### 12.3 `candidates.json`

示例：

```json
{
  "method": "LGA-Param-Direct-AltModelPred",
  "variant": "direct",
  "new_field": "alt",
  "old_field": "model_pred",
  "score_space": "param_mlp_ffn",
  "target_layer_type": "mlp_ffn",
  "target_parameter_scope": "mlp_ffn_weight_only",
  "include_bias": false,
  "include_attention": false,
  "include_layernorm": false,
  "include_adapter": false,
  "old_source": "frozen_base_model_generation",
  "rank_metric": "raw_old_new_parameter_gradient_dot",
  "dot_normalization": "none",
  "cross_model_score_comparable": false,
  "candidate_conversion": "direct",
  "top3": [17, 16, 18],
  "top5": [17, 16, 18, 19, 20],
  "status": "done"
}
```

### 12.4 `summary.json`

建议字段：

```json
{
  "dataset": "MMKE-Visual",
  "model": "LLaVA-v1.5-7B",
  "method": "LGA-Param-Direct-AltModelPred",
  "total_samples": 0,
  "valid_samples": 0,
  "skipped_samples": 0,
  "num_decoder_layers": 0,
  "valid_layers": 0,
  "failed_layers": 0,
  "top3": [],
  "top5": [],
  "config_hash": "",
  "status": "done"
}
```

---

## 13. 回填总表规则

LGA 主结果回填到：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

对应方法名必须写成：

```text
LGA-Param-Direct-AltModelPred
```

不得简写成：

```text
LGA
GoldenLayer
LGA-Hidden
```

如果同时报告 `AltPred` 附加版本，必须另起行或另起表：

```text
LGA-Param-Direct-AltPred
```

如果报告 hidden visual 变体，必须另起行或另起表：

```text
LGA-Hidden-Visual-Direct
```

并标记：

```text
diagnostic only
not original LGA
```

---

## 14. 真实编辑验证后的评价

LGA 只是候选层定位方法。候选层是否好，必须通过统一 adapter 训练与最终评测判断。

对每个 `dataset × model × method`，记录：

```text
Top1Perf
Mean@3
Best@3
Regret@3
Hit@3
Mean@5
Best@5
Regret@5
Hit@5
```

其中真实编辑性能：

\[
A(l)
=
\frac{Rel(l)+TGen(l)+MGen(l)+TLoc(l)+MLoc(l)}{5}.
\]

如果使用官方 Overall，应记录官方公式。

Regret 相对于可用 oracle：

```text
Candidate-union Oracle
```

或：

```text
Full-layer Oracle
```

不得把 candidate-union oracle 误称为 full-layer oracle。

---

## 15. 附加变体

### 15.1 LGA-Param-Direct-AltPred

当数据集 `pred` 非空且语义有效时，可额外计算：

```text
method = LGA-Param-Direct-AltPred
old_field = pred
new_field = alt
```

它的公式与主版本相同，只是旧知识字段不同。

该版本只能作为附加分析，不得混入主 LGA 表。

### 15.2 LGA-Hidden-Visual-Direct

可以额外计算视觉 hidden-state 适配变体：

\[
S_{hidden}(l)
=
\frac{1}{N}
\sum_i
\left\langle
\nabla_{h_{i,l}^{v}}\mathcal L_i^{old},
\nabla_{h_{i,l}^{v}}\mathcal L_i^{new}
\right\rangle.
\]

但必须标记为：

```text
method = LGA-Hidden-Visual-Direct
score_space = hidden_visual_tokens
status = diagnostic_only
not_original_lga = true
```

它不能取代：

```text
LGA-Param-Direct-AltModelPred
```

该变体的作用是检验：仅仅把 LGA 的归因对象从参数换成视觉 hidden states，是否足以预测最佳 adapter 层。它可以作为 OurDirect 的消融对照。

---

## 16. 实验前检查清单

正式运行每个 `dataset × model` 组合前，必须检查：

- [ ] 已生成并缓存 `model_pred`。
- [ ] `model_pred` 非空且 token 长度 > 0。
- [ ] `alt` 非空且 token 长度 > 0。
- [ ] `pred` 不参与主版本，除非运行 `AltPred` 附加分析。
- [ ] `model_registry.yaml` 已记录 decoder path、层数、合法层范围和 MLP 参数名。
- [ ] 只启用 MLP/FFN weight 参数，不包含 bias、attention、LayerNorm、adapter。
- [ ] 使用完整答案序列 teacher-forcing loss。
- [ ] loss mask 只覆盖答案 token，prompt / visual / padding 标签为 `-100`。
- [ ] `use_cache = false`。
- [ ] `model.eval()`，dropout disabled。
- [ ] 未使用 `torch.no_grad()` 包住目标 forward。
- [ ] 主排序使用 raw old/new parameter gradient dot。
- [ ] cosine、norm、dim-normalized dot 仅保存为诊断。
- [ ] Tukey-filtered ranking 仅保存为诊断，不替代 raw Top-K。
- [ ] TopK 使用 `ranked[:3]` 和 `ranked[:5]`。
- [ ] 所有失败样本与失败层均有 `failure_reason`。
- [ ] 不使用任何 fallback 替代 LGA 失败结果。
- [ ] 输出 `layer_scores.csv`、`candidate_layers_topk.csv`、`candidates.json`、`summary.json`。

---

## 16.1 全量执行级补充规则

本节用于把 `LGA-Param-Direct-AltModelPred` 从公式手册落实为 7 模型 × 3 数据集可恢复、可审计的全量实验流程。以下规则不改变主公式，只约束运行、失败处理和结果回填。

### 16.1.1 `model_pred` 生成与有效性

每个 `dataset × model` 组合必须先生成并固定独立的：

```text
model_pred_cache.jsonl
```

后续 LGA 计算只能读取缓存，不得在 LGA 进程内部临时生成 `model_pred`。

`model_pred_cache.jsonl` 至少记录：

```text
dataset
model
sample_id
raw_text
normalized_text
token_ids
effective_token_length
empty_or_invalid_status
generation_config_hash
prompt_template_hash
processor_hash
```

有效性规则：

1. `model_pred` 为空、token 长度为 0、tokenization 失败时，该样本跳过，原因写为 `invalid_model_pred`。
2. `alt` 为空、token 长度为 0、tokenization 失败时，该样本跳过，原因写为 `invalid_alt`。
3. 如果归一化后 `model_pred == alt`，记录为 `old_new_same_after_norm`。该样本默认不进入主 LGA 分数，可单独进入诊断统计。
4. 不允许把空 `model_pred` 填充为 `pred`、`alt`、中层先验或任意默认字符串。
5. 不同方法共享同一份 `model_pred` 缓存；若重新生成，必须改变 `generation_config_hash` 并另开 run root。

### 16.1.2 模型 wrapper 与参数路径验收

正式全量运行前，每个模型必须先完成 wrapper smoke test。验收对象包括：

```text
decoder_module_path
num_decoder_layers
valid_layer_index_range
mlp_parameter_names_by_layer
nonzero_old_gradient
nonzero_new_gradient
```

每个模型至少抽取 3 条样本做 smoke test，并输出：

```text
wrapper_smoke_test.json
```

建议字段：

```text
model
dataset
sample_id
num_layers
layer
mlp_weight_param_count
mlp_weight_numel
old_loss
new_loss
old_grad_norm
new_grad_norm
dot
status
failure_reason
```

验收要求：

1. 每层必须能找到 MLP/FFN weight 参数。
2. 至少一个测试样本在每层产生非零 old/new 梯度。
3. `Qwen2.5-VL-3B`、`PaliGemma-3B`、`SmolVLM-Instruct-1.7B` 必须单独通过 smoke test 后再进入全量运行。
4. 未通过 smoke test 的模型不得进入主 LGA 表，必须标记 `status=unavailable`。

### 16.1.3 失败比例阈值

样本级失败和层级失败必须可见，不得静默归零。

组合级状态规则：

```text
valid_sample_count < 50                         -> status = low_valid_coverage
valid_sample_count / total_sample_count < 0.20  -> status = low_valid_coverage
valid_layer_count / total_layer_count < 0.80    -> status = unreliable
valid_layer_count < top_k                       -> status = unavailable
```

若组合被标记为 `low_valid_coverage` 或 `unreliable`，仍可保存诊断结果，但不得作为主论文表中的可信候选层。主表应写明：

```text
status
failure_reason
valid_sample_count
valid_layer_count
```

### 16.1.4 断点续跑与原子写入

全量运行必须支持：

```text
--resume
--skip-done
--run-root
```

组合完成判定以 `summary.json` 为准：

```json
{
  "status": "done",
  "method": "LGA-Param-Direct-AltModelPred"
}
```

写文件时必须使用临时文件再原子替换：

```text
layer_scores.csv.tmp -> layer_scores.csv
candidate_layers_topk.csv.tmp -> candidate_layers_topk.csv
summary.json.tmp -> summary.json
```

每完成一个 layer，应保存中间结果：

```text
layer_scores.partial.csv
layer_progress.json
```

中断后续跑时：

1. 已完成且 `status=done` 的 `dataset × model` 组合直接跳过。
2. 已完成的 layer 不重复计算，除非显式指定 `--force-layer`。
3. 发现 `.tmp` 文件时，先检查是否有完整目标文件；若无完整目标文件，则从最近完整 layer 继续。

### 16.1.5 低显存运行默认配置

正式运行默认采用低显存流式策略：

```yaml
batch_size: 1
model_eval: true
use_cache: false
requires_grad_scope: one_layer_mlp_ffn_weight_only
old_new_backward: separated
score_accumulation_device: cpu
score_accumulation_dtype: float64
torch_empty_cache_each_layer: true
```

每层计算结束后必须执行等价清理：

```python
model.zero_grad(set_to_none=True)
del loss, grads
gc.collect()
torch.cuda.empty_cache()
```

资源调度规则：

1. 不得与正在进行的 epoch50 adapter 训练抢同一张 GPU。
2. 如果需要占用正在训练的 Slurm job，必须先保护训练现场并记录恢复命令。
3. 主实验不得使用 4-bit / 8-bit 量化权重计算参数梯度。

### 16.1.6 分数 sanity check

每个 `dataset × model` 组合完成后必须检查：

1. 是否所有层分数完全相同。
2. 是否所有层分数均为 0。
3. 是否存在 NaN / Inf。
4. 是否 Top-K 包含越界层。
5. 是否 Top-K 包含重复层。
6. 是否 `raw_top3/raw_top5` 和 `clean_top3/clean_top5` 都已保存。
7. 是否有分数来自 fallback。

若出现异常，写入：

```text
sanity_check.json
```

并在 `summary.json` 中记录：

```text
sanity_status
sanity_failure_reason
```

异常组合不得直接回填为主结果。

### 16.1.7 Raw 与 Clean 候选层

所有候选层必须同时保存原始结果与清洗结果：

```text
raw_top3
raw_top5
clean_top3
clean_top5
removed_layers
cleaning_reason
```

清洗规则：

1. 去除重复层，保留首次出现的位置。
2. 删除越界层。
3. 删除 `status=unavailable`、`score=NaN/Inf` 或有效样本数为 0 的层。
4. 不自动用下一名补齐，除非显式记录 `fill_from_next_rank=true`。

主表默认使用 `clean_top3/clean_top5`，但必须能追溯到 `raw_top3/raw_top5`。

### 16.1.8 结果回填格式

回填到：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

建议主表字段：

```text
Dataset | Model | Method | Top-3 | Top-5 | Status | Score Source
```

方法名必须固定为：

```text
LGA-Param-Direct-AltModelPred
```

`Score Source` 建议写：

```text
server_results/lga_param_direct_altmodelpred/.../candidate_layers_topk.csv
```

失败组合不得留空，应写：

```text
unavailable: failure_reason
low_valid_coverage: valid_sample_count / total_sample_count
unreliable: valid_layer_count / total_layer_count
```

### 16.1.9 推荐执行顺序

全量运行按以下顺序执行：

1. `pilot500 × BLIP2-OPT-2.7B` 跑通端到端流程。
2. 使用 `Qwen2.5-VL-3B`、`PaliGemma-3B`、`SmolVLM-Instruct-1.7B` 做跨架构 wrapper 验证。
3. 确认 `model_pred` 缓存、teacher-forcing mask、MLP 参数路径、sanity check 均通过。
4. 运行 7 模型 × 3 数据集全量候选层计算。
5. 汇总 `candidate_layers_topk.csv`，回填总表。
6. 将失败组合单独列入 rerun 清单，不使用其他方法结果替代。

---

## 17. 论文表述建议

可以在论文中这样描述该基线：

> We include a faithful parameter-space LGA baseline, denoted as `LGA-Param-Direct-AltModelPred`. Following the original LGA principle, we compute the inner product between old-knowledge and new-knowledge gradients restricted to the MLP/FFN weights of each decoder layer. The old knowledge is instantiated by the frozen VLM's deterministic prediction, while the new knowledge is the target edit answer. The resulting layer scores are used to directly rank candidate adapter insertion layers. This baseline allows us to test whether parameter-space gradient similarity can serve as a reliable proxy for visual-representation adapter editability.

中文表述：

> 本文将原始 LGA 作为参数空间强基线，记为 `LGA-Param-Direct-AltModelPred`。具体而言，我们在每个 decoder 层的 MLP/FFN 权重参数上，计算旧知识损失与新知识损失的梯度内积，并据此直接排序候选 adapter 插入层。旧知识由冻结基础 VLM 在当前图像与问题上的确定性输出 `model_pred` 表示，新知识为编辑目标 `alt`。该基线用于检验参数空间梯度相似性是否能够可靠预测视觉表征 adapter 的可编辑层。

如果结果显示 LGA 候选层无法覆盖真实最佳层，可以写：

> The gap between `LGA-Param-Direct` and visual-gradient-based methods suggests an intervention-space mismatch: LGA measures attribution in the parameter space, whereas the actual edit is applied to visual-token hidden representations.

---

## 18. 最终主公式摘要

主实验只使用以下公式生成 Top-3 / Top-5：

\[
S_{\mathrm{LGA}}^{(m,d)}(l)
=
\frac{1}{|\mathcal D_d|}
\sum_{i\in\mathcal D_d}
\left\langle
\nabla_{W_l^{(m)}}
\mathcal L
\left(M_m(x_i^v,x_i^t)\rightarrow \texttt{model\_pred}_i\right),
\nabla_{W_l^{(m)}}
\mathcal L
\left(M_m(x_i^v,x_i^t)\rightarrow \texttt{alt}_i\right)
\right\rangle.
\]

候选层：

\[
\operatorname{Top3}^{(m,d)}
=
\operatorname{argsort}_{l}
\left(S_{\mathrm{LGA}}^{(m,d)}(l)\right)_{desc}[:3],
\]

\[
\operatorname{Top5}^{(m,d)}
=
\operatorname{argsort}_{l}
\left(S_{\mathrm{LGA}}^{(m,d)}(l)\right)_{desc}[:5].
\]

主配置固定为：

```json
{
  "method": "LGA-Param-Direct-AltModelPred",
  "new_field": "alt",
  "old_field": "model_pred",
  "score_space": "param_mlp_ffn",
  "target_parameter_scope": "mlp_ffn_weight_only",
  "rank_metric": "raw_old_new_parameter_gradient_dot",
  "dot_normalization": "none",
  "candidate_conversion": "direct"
}
```
