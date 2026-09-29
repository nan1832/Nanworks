# 编辑层定位方法候选层计算手册（修订版）

> 适用于：`E-VQA/pilot500`、`MMKE-Visual`、`MMKE-Entity`  
> 适用于模型：BLIP2-OPT-2.7B、InstructBLIP-Vicuna-7B、MiniGPT-4-Vicuna-7B、LLaVA-v1.5-7B、Qwen2.5-VL-3B-Instruct、PaliGemma-3B、SmolVLM-Instruct-1.7B  
> 输出目标：每种定位方法在每个“数据集 × 模型”组合上给出 `Top-3` 和 `Top-5` 候选 adapter 插入层，并通过统一的真实编辑实验验证其性能。

> 注：代码或配置中的 short name `qwen2.5-vl-3b` 与 `qwen2.5-vl-3b-instruct` 视为同一模型；结果表展示名统一写作 `Qwen2.5-VL-3B-Instruct`。

---

## 修订说明

本版本根据当前实验目标做了以下关键修改：

1. `Middle-layer Prior` 使用严格网络中点 \(\rho=0.5\)，不再使用可能偏向已知结果的 \(\rho=0.55\)。
2. `VisEdit-Contrib-Pre` 保留原文“高贡献区之前插入 adapter”的主规则；VisEdit-style 贡献度使用 key token prediction，是为了遵循原文对每层 Attention/MLP 输出到关键 token 预测贡献的定义，不把 VisEdit 主基线改成完整答案序列归因。
3. `SaLEM` 主版本严格采用参数绝对梯度的参数级、列级、矩阵级和层级聚合，并直接选择显著层。
4. `GoldenLayer/LGA` 主版本改为原论文的**层参数梯度内积**，不再将 hidden-state 梯度版本称为原始 LGA。
5. 为覆盖没有有效 `pred` 字段的 MMKE-Visual，LGA 跨数据集主版本使用模型当前输出 `model_pred` 作为旧知识；`pred` 版本作为可用数据集上的附加分析。
6. `Perturb-KL-Direct` 作为主扰动基线，直接选择 KL 敏感层；主版本在 `alt` 完整序列上计算 KL，并且只扰动 visual tokens。这里的完整序列口径是本文构造的“序列级扰动敏感性基线”，尤其适合 MMKE 这类长目标答案。
7. 本文方法的公式本身用于**直接预测适合挂载 adapter 的层**，因此主版本统一改为 `Ours-Direct`，不再对结果进行 Pre 偏移。
8. 将 `Candidate-union Oracle` 与 `Full-layer Oracle` 分开，避免把候选层并集中的最优层误称为全局最优层。
9. 明确 adapter 层编号：候选层 \(L_l\) 表示 adapter 接在 decoder block \(l\) 的输出之后、block \(l+1\) 之前。
10. 增加定位集、训练集、评测集隔离，多随机种子训练，以及 `Top1 / Mean@K / Best@K / Regret@K / Hit@K` 等评价指标。

---

# 0. 统一实验定义

## 0.1 层空间

设语言解码器共有 \(L\) 个候选 Transformer blocks，使用 0-indexed 编号：

\[
l\in\{0,1,\ldots,L-1\}.
\]

本手册主实验中的候选层均指：

```text
layer_space = text_decoder
```

对于 BLIP2、InstructBLIP、MiniGPT-4 等包含 Q-Former 的模型，主实验仍然比较文本解码器层，不把 Q-Former 层混入同一排序。若另行计算 Q-Former，必须使用：

```text
layer_space = qformer
```

并单独报告。

## 0.2 Adapter 插入位置

候选层 \(L_l\) 的统一含义为：

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
\left(\hat h_i^{\,l}\right),
\]

其中 \(A_l\) 是视觉编辑 adapter。

因此：

> `candidate layer = l` 表示 adapter 接在 decoder block \(l\) 的输出之后、block \(l+1\) 之前。

代码、日志和论文必须统一这一含义，避免 off-by-one。

## 0.2.1 Visual-token 与 Hook 单元测试

每个模型 wrapper 在批量计算 `Perturb-KL-Direct-AltSeq`、`Ours-Direct` 或 `CMA-Direct` 前，必须通过以下单元测试：

1. `visual_token_count` 与实际进入语言模型 decoder 的视觉 embedding 数一致；
2. 目标层 visual-token hidden states 对目标 loss 的梯度不为 `None`，且不是全零；
3. 对 visual tokens 加噪声后，输出 logits 或目标 token 分布发生变化；
4. 对空 visual mask 加噪声时，输出不应变化；
5. adapter hook、扰动 hook、hidden-state gradient hook、CMA restore hook 使用同一层间位置，即 block \(l\) 输出后、block \(l+1\) 前。

未通过时，该模型对应的 visual-token 方法必须标记：

```text
status = unavailable
failure_reason = visual_token_or_hook_test_failed
```

不得临时退化成 `all_prompt_tokens` 后仍写入 visual-token 主表。

## 0.3 数据集

多模态编辑数据表示为：

\[
\mathcal D
=
\left\{
(x_i^v,x_i^t,y_i^{new},y_i^{old})
\right\}_{i=1}^{N},
\]

其中：

| 符号 | 数据字段 | 含义 |
|---|---|---|
| \(x_i^v\) | `image` | 图像输入 |
| \(x_i^t\) | `src` / prompt | 文本问题 |
| \(y_i^{new}\) | `alt` / `target_new` | 希望编辑后生成的新知识 |
| \(y_i^{old}\) | `pred` 或 `model_pred` | 编辑前的旧答案或模型当前输出 |

字段规则：

- `alt`：所有目标相关主方法的统一新知识。
- `pred`：数据集提供的旧知识，仅在字段有效时使用。
- `model_pred`：冻结基础模型在当前图像与问题上的实际输出，应预先生成并缓存。
- 当 `pred` 缺失或为空时，不得静默填充。需要区分旧知识来源的方法必须在方法名或字段中显式记录，例如 LGA 主版本使用 `AltModelPred`；`Ours-Direct` 主版本默认使用 `model_pred`，`pred` 版本必须另命名为 `Ours-Direct-AltPred`。

## 0.4 数据划分

候选层定位不得使用最终 eval/test 数据。

| 数据集 | 候选层定位 | Adapter 训练 | 最终评测 |
|---|---|---|---|
| E-VQA | `pilot500 train` | `pilot500 train` | full E-VQA test/eval |
| MMKE-Visual | `visual/train.json` | `visual/train.json` | `visual/eval.json` |
| MMKE-Entity | `entity/train.json` | `entity/train.json` | `entity/eval.json` |

如果后续在训练集内部划分独立 localization proxy，可额外记录：

```text
localization_split
editing_train_split
evaluation_split
```

## 0.5 完整目标序列损失

对包含 \(T_i\) 个 token 的目标序列 \(y_i\)，使用 teacher forcing 的长度归一化自回归损失：

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

定义：

\[
\mathcal L_i^{new}
=
\mathcal L_i(y_i^{new}),
\qquad
\mathcal L_i^{old}
=
\mathcal L_i(y_i^{old}).
\]

长度归一化用于避免 MMKE-Entity 长答案仅因 token 数更多而产生更大的损失和梯度。

Teacher forcing 的标签对齐必须固定。对于 causal LM：

```text
shift_logits = logits[..., :-1, :]
shift_labels = labels[..., 1:]
prompt labels = -100
visual token labels = -100
padding labels = -100
```

只对目标答案 token 计算损失，并记录：

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

目标 token mask 必须按方法口径分别缓存并写入 manifest：VisEdit-style 使用 key token mask 以对齐原文 key token prediction 贡献；Perturb-KL-Direct、CMA-Direct 等序列级基线使用完整 `alt` token mask；`model_pred` 与 `pred` 的 token mask 也必须分别缓存，不能运行时临时重切导致 old/new 梯度不对齐。

## 0.6 主方法与候选规则

| 方法 | 主版本 | 候选层规则 |
|---|---|---|
| Middle-layer Prior | `Middle-Prior-Direct` | 网络中点附近 Top-K |
| VisEdit | `VisEdit-Contrib-Pre-KeyToken` | key token 高贡献区之前 Top-K |
| SaLEM | `SaLEM-Alt-Direct` | 参数显著性最高 Top-K |
| GoldenLayer/LGA | `LGA-Param-Direct-AltModelPred` | 新旧知识参数梯度内积最高 Top-K |
| Perturbation | `Perturb-KL-Direct-AltSeq` | KL 敏感性最高 Top-K |
| Ours | `Ours-Direct` | 本文公式得分最高 Top-K |
| Visual Causal Restoration / CMA | `CMA-Direct` | 因果恢复分数 CR 最高 Top-K |
| Oracle | `Candidate-union Oracle` / `Full-layer Oracle` | 真实编辑性能排序 |

附加实验可以报告：

```text
VisEdit-Contrib-Direct-KeyToken
SaLEM-Delta
LGA-Param-Direct-AltPred
LGA-Hidden-Visual-Direct
Perturb-KL-Direct-Prompt
Perturb-KL-Pre-AltSeq
```

但这些变体不能与主方法混用名称。

## 0.7 实施级建议采纳边界

`7models_3datasets_candidate_layer_implementation_spec.md` 中的工程建议按以下边界吸收进本手册：

| 实施级建议 | 本手册处理 | 理由 |
|---|---|---|
| 七模型注册表、visual-token 单测、teacher forcing 对齐、`model_pred` 缓存 | 采纳为正式运行前置条件 | 这些是防止 wrapper 错层、token 错位和跨模型不可复现的必要条件 |
| SaLEM 命名改为 `SaLEM-MLP-Alt-Direct` | 不改主方法名；只记录 `target_parameter_scope=mlp_ffn_weight_only` | 当前结果表和主手册已统一使用 `SaLEM-Alt-Direct`，改名会造成历史结果混乱；参数范围用字段说明即可 |
| LGA 保存 raw 与 Tukey-filtered 排名 | 采纳为诊断输出；主排序仍用 raw dot | 原始 LGA 主公式是 raw parameter-gradient dot；Tukey 过滤可能误删真实高分层，不能替代主候选层 |
| LGA 使用约 10% proxy set | 不作为主实验默认；只允许作为调试/低预算诊断 | 主实验要求所有方法使用同一 localization 样本集合；若 LGA 单独降采样，会引入样本量差异 |
| VisEdit \(\lambda\) 网格测试 | 只作为敏感性分析；主实验固定 \(\lambda=0.5\) | 不能根据候选层或编辑结果反向调阈值，否则会产生事后调参 |
| Random-Uniform-TopK | 可作为附录随机基线；不进入主定位方法，也不参与候选层主并集 | 它不是定位算法，但可帮助判断主方法是否显著优于随机选层 |
| Full-layer Oracle | 可在代表性模型/数据集上做；不强制 7×3 全量完成 | 全层逐层训练成本过高，主实验先使用 candidate-union oracle；full-layer oracle 用于校准上界 |
| checkpoint 不使用最终 eval/test 选择 | 采纳 | 防止评测集泄漏，是真实编辑评测必须遵守的约束 |

因此，本手册主表比较 7 个低成本定位方法加 oracle 评价；附加/消融/诊断建议必须单独成表，不能混入主候选方法列。

---

# 1. Middle-layer Prior

## 1.1 方法定义

中层先验不读取编辑样本的梯度或贡献度，而是根据网络深度直接选择中间层，作为低成本经验基线。

## 1.2 中点

严格使用网络几何中点：

\[
c_{\mathrm{mid}}
=
\frac{L-1}{2}.
\]

对应：

\[
\rho=0.5.
\]

## 1.3 层得分

\[
S_{\mathrm{mid}}(l)
=
-\left|
l-\frac{L-1}{2}
\right|.
\]

也可保存归一化分数：

\[
S_{\mathrm{mid}}^{norm}(l)
=
1-
\frac{
\left|l-\frac{L-1}{2}\right|
}{
L-1
}.
\]

## 1.4 候选层

\[
\mathcal C_{\mathrm{mid},K}
=
\operatorname{TopK}_l
S_{\mathrm{mid}}(l).
\]

并列层固定使用以下 tie-break：

```text
1. 与中点距离更小者优先；
2. 距离相同时，较浅层编号优先；
3. 该规则在全部模型上保持不变。
```

例如 32 层模型的中点为 15.5：

```text
Top-3: L15, L16, L14
Top-5: L15, L16, L14, L17, L13
```

不再把 `{L10,L15,L19,L20,L25}` 称为 Middle-layer Prior。若使用这种稀疏层组，应单独命名为：

```text
Equal-spaced Sparse Sweep
```

## 1.5 输出

```json
{
  "method": "Middle-Prior-Direct",
  "variant": "prior",
  "rho": 0.5,
  "layer_space": "text_decoder",
  "rank_metric": "negative_distance_to_network_midpoint",
  "top_k": 5,
  "candidate_layers": [15, 16, 14, 17, 13]
}
```

---

# 2. VisEdit-Contrib-Pre

## 2.1 方法定位

VisEdit 通过模块输出归因识别对关键输出贡献较高的层，并将视觉编辑 adapter 插入高贡献层之前。因此，VisEdit 主基线保留 `Pre` 规则。

正式名称建议使用：

```text
VisEdit-inspired Contrib-Pre
```

原因是高贡献区的自动阈值属于本实验为跨模型批量计算设计的操作化规则。

## 2.2 模块输出

对第 \(i\) 个样本、第 \(l\) 层和模块 \(b\)：

\[
b\in\{\mathrm{attn},\mathrm{mlp}\},
\]

记模块在目标预测位置的输出为：

\[
r_{i,l,b,t}.
\]

映射到词表空间：

\[
z_{i,l,b,t}
=
\operatorname{LMHead}
\left(
\operatorname{FinalNorm}(r_{i,l,b,t})
\right).
\]

目标 token 的映射概率：

\[
C^p_{i,l,b,t}
=
\operatorname{softmax}
\left(
z_{i,l,b,t}
\right)_{y^{new}_{i,t}}.
\]

归一化目标 logit：

\[
C^v_{i,l,b,t}
=
\frac{
z_{i,l,b,t,y^{new}_{i,t}}
}{
\max_{l',b'}
\left|
z_{i,l',b',t,y^{new}_{i,t}}
\right|
+\epsilon
}.
\]

signed contribution：

\[
C_{i,l,b,t}
=
\operatorname{sign}
\left(
C^v_{i,l,b,t}
\right)
\sqrt{
\left|
C^v_{i,l,b,t}
\right|
\cdot
C^p_{i,l,b,t}
}.
\]

正贡献：

\[
C^+_{i,l,b,t}
=
\max(0,C_{i,l,b,t}).
\]

## 2.3 Key token 贡献

VisEdit 原文依据是计算每层 Attention / MLP 输出对 key token prediction 的贡献，因此本手册的 VisEdit-style 主基线使用 key token，而不是完整答案序列。对每个样本从 `alt` / `target_new` 中确定一个 key token 位置 \(t_i^{key}\)，通常为目标答案在模型 tokenizer 下的第一个有效内容 token；是否带 leading space 必须固定并记录。

必须保存以下诊断字段：

```text
key_token_text
key_token_id
key_token_position
leading_space
target_answer_raw
target_answer_token_ids
```

主排序分数为：

\[
S_{\mathrm{contrib\text{-}key}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\frac{
C^+_{i,l,\mathrm{attn},t_i^{key}}
+
C^+_{i,l,\mathrm{mlp},t_i^{key}}
}{2}.
\]

如果 key token 为 `"The"`、`"A"`、`"This"` 等普通功能词，仍按 VisEdit-style 主口径保留该结果，因为这是复现 key token prediction 贡献的直接后果；同时必须在诊断字段中标记 `generic_key_token=true`，便于后续报告 MMKE 长答案场景下 key-token VisEdit 的局限性。

建议同时保存：

\[
S_{\mathrm{positive}}(l),
\qquad
S_{\mathrm{signed}}(l),
\qquad
S_{\mathrm{abs}}(l),
\qquad
S_{\mathrm{contrib\text{-}altseq}}(l)\ \text{diagnostic only},
\]

但主排序使用：

```text
rank_metric = score_positive_key_token
```

完整 `alt` 序列贡献可以作为附加诊断保存，但不得替代 VisEdit-style 主排序；需要序列级主基线时使用第 5 节 `Perturb-KL-Direct-AltSeq`。

## 2.4 高贡献区

先做 3 层移动平均：

\[
\tilde S(l)
=
\operatorname{Mean}
\left(
S(l-1),S(l),S(l+1)
\right).
\]

计算：

\[
\mu
=
\operatorname{Mean}_l
\tilde S(l),
\qquad
\sigma
=
\operatorname{Std}_l
\tilde S(l).
\]

高贡献层集合：

\[
\mathcal H
=
\left\{
l:
\tilde S(l)
\ge
\mu+\lambda\sigma
\right\},
\]

默认：

\[
\lambda=0.5.
\]

取最长连续高贡献区：

\[
[s_{\mathcal H},e_{\mathcal H}].
\]

注意：

> \(\lambda=0.5\) 是本实验的自动化阈值，不是 VisEdit 原文给出的固定阈值。

建议在附录报告：

\[
\lambda\in\{0,0.25,0.5,0.75,1.0\}.
\]

## 2.5 前置候选层

\[
\mathcal C_{\mathrm{VisEdit\text{-}Pre},K}
=
\left\{
s_{\mathcal H}-1,
s_{\mathcal H}-2,
\ldots,
s_{\mathcal H}-K
\right\}.
\]

删除越界层，不允许使用其他定位方法静默替代。候选不足时记录：

```text
status = insufficient_pre_layers
```

如必须补齐用于工程训练，补齐规则应单独标记，主分析仍保留原始不足结果。

## 2.6 输出

```json
{
  "method": "VisEdit-Contrib-Pre-KeyToken",
  "variant": "pre",
  "key_mode": "key_token",
  "rank_metric": "score_positive_key_token",
  "lambda": 0.5,
  "high_contribution_region": [20, 30],
  "top_k": 5,
  "candidate_layers": [19, 18, 17, 16, 15]
}
```

---

# 3. SaLEM-Based Salient-Layer Selection

## 3.1 方法定位

原始 SaLEM 包括：

1. 显著层选择；
2. 使用 MEND 在选中层执行参数编辑。

本实验只复用第一部分，因此正式名称使用：

```text
SaLEM-based salient-layer selection
```

而不是声称完整复现 SaLEM 编辑器。

## 3.2 参数范围

主版本统一比较每个 decoder block 的 MLP/FFN 权重：

```text
target_layer_type = mlp_ffn
```

不同架构中的典型矩阵包括：

```text
fc1 / fc2
gate_proj / up_proj / down_proj
mlp.w1 / mlp.w2 / mlp.w3
```

不将 Attention 和 MLP 混在同一主分数中。

## 3.3 参数级显著性

对第 \(i\) 个样本、第 \(l\) 层、第 \(m\) 个 MLP 权重矩阵中的参数：

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

## 3.4 列级显著性

\[
s_{i,l,m,c}^{col}
=
\frac{1}{d_{out}^{l,m}}
\sum_{r=1}^{d_{out}^{l,m}}
s_{i,l,m,r,c}.
\]

## 3.5 矩阵级显著性

\[
s_{i,l,m}^{matrix}
=
\frac{1}{d_{in}^{l,m}}
\sum_{c=1}^{d_{in}^{l,m}}
s_{i,l,m,c}^{col}.
\]

## 3.6 层级显著性

对同一层中的各 MLP 矩阵等权平均：

\[
s_{i,l}^{layer}
=
\frac{1}{M_l}
\sum_{m=1}^{M_l}
s_{i,l,m}^{matrix}.
\]

数据集级分数：

\[
S_{\mathrm{SaLEM}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
s_{i,l}^{layer}.
\]

该公式体现：

```text
参数 → 列 → 矩阵 → 层 → 数据集
```

不再同时使用 L1 总和、L2 范数等多个主公式。L2 版本只能作为附加稳定性分析。

## 3.7 候选层

SaLEM 直接选择显著层本身：

\[
\mathcal C_{\mathrm{SaLEM},K}
=
\operatorname{TopK}_{l}
S_{\mathrm{SaLEM}}(l).
\]

不执行 Pre 偏移。

## 3.8 样本规则

SaLEM 原始任务关注错误预测样本。对于本研究的反事实或知识更新任务，为确保 7 个模型使用同一批记录，主实验采用全部编辑记录：

> 只要基础模型尚未通过编辑写入 `alt`，该记录就作为编辑样本；不按各模型预测正确率重新筛选不同的样本子集。

## 3.9 输出

```json
{
  "method": "SaLEM-Alt-Direct",
  "variant": "direct",
  "key_mode": "alt_sequence",
  "score_space": "param_mlp_ffn",
  "target_layer_type": "mlp_ffn",
  "rank_metric": "column_matrix_layer_mean_abs_gradient",
  "top_k": 5,
  "candidate_layers": [16, 17, 20, 18, 19]
}
```

---

# 4. GoldenLayer / Layer Gradient Analysis

## 4.1 方法定位

LGA 的原始核心是将样本梯度归因限制到某个层的**参数权重**，并通过旧知识与新知识的层参数梯度内积估计 golden layer。

因此，本实验的原始 LGA 主基线必须使用：

```text
score_space = param_mlp_ffn
```

不能把 hidden visual-token 梯度版本直接称为原始 LGA。

## 4.2 旧知识

为了在 E-VQA、MMKE-Visual、MMKE-Entity 上使用统一定义，主版本使用冻结基础模型的实际生成结果：

\[
y_i^{old}
=
\operatorname{Generate}_{M}
(x_i^v,x_i^t).
\]

将其缓存为：

```text
model_pred
```

新知识为：

\[
y_i^{new}
=
\texttt{alt}.
\]

主方法名称：

```text
LGA-Param-Direct-AltModelPred
```

在 `pred` 字段有效的数据集上，可附加计算：

```text
LGA-Param-Direct-AltPred
```

但不得混入同一主排序。

## 4.3 层参数梯度

对第 \(l\) 层 MLP 参数集合 \(W_l\)：

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

展平为向量后，样本级层归因：

\[
\phi_{i,l}
=
\left\langle
g_{i,l}^{old},
g_{i,l}^{new}
\right\rangle.
\]

## 4.3.1 参数集合与可计算性约束

`LGA-Param-Direct-AltModelPred` 的主实验只比较每个 decoder block 的 MLP/FFN **weight 参数**，默认不包含 bias，不包含 attention，不包含 LayerNorm，不包含 adapter 参数。

```text
target_parameter_scope = mlp_ffn_weight_only
include_bias = false
include_attention = false
include_layernorm = false
include_adapter = false
```

不同模型的 MLP/FFN 命名可以不同，但必须映射到同一语义对象。例如：

| 模型族 | MLP/FFN weight 示例 |
|---|---|
| OPT / Vicuna / LLaMA-like | `mlp.fc1.weight`、`mlp.fc2.weight` 或 `mlp.gate_proj/up_proj/down_proj.weight` |
| Qwen2.5-VL | decoder block 内 `mlp.gate_proj/up_proj/down_proj.weight` |
| PaliGemma / Gemma-like | decoder block 内 `mlp.gate_proj/up_proj/down_proj.weight` |
| SmolVLM | language model decoder block 内 MLP/FFN weights |

如果某模型 wrapper 的参数命名不同，必须先在 `config` 中显式记录每一层 \(W_l\) 对应的参数名列表。不得临时把 attention 或 whole block 混入主 LGA 分数；如果需要比较，应另开方法名：

```text
LGA-Param-Direct-AltModelPred-Attn
LGA-Param-Direct-AltModelPred-BlockAll
```

该分数可以用 autograd 直接算出，但实现时不能一次性保存所有层、所有样本的完整 old/new 参数梯度，否则 7B 模型容易显存溢出。推荐逐层或逐参数块流式计算：

```text
for sample in localization_set:
  for layer in decoder_layers:
    W_l = get_mlp_ffn_weights(layer)

    grad_old = grad(L_old(sample), W_l)
    grad_new = grad(L_new(sample), W_l)

    score[layer] += dot(flatten(grad_old), flatten(grad_new))

    immediately clear grad_old / grad_new / cache
```

低显存实现可以每次只打开一个候选层的 MLP 参数梯度，其余参数保持 `requires_grad=False`；也可以按层分批计算并把中间 dot 标量累计到 CPU。必须满足：

```text
model.eval()
dropout disabled
torch.no_grad() disabled for the target forward
create_graph = false
retain_graph = false unless the implementation explicitly reuses the same graph
```

如果某层的 \(W_l\) 在当前 forward 中没有梯度，不能静默记为 0；应记录：

```text
status = unavailable
failure_reason = unused_or_unreachable_mlp_parameters
```

然后排查 wrapper / 参数路径，而不是用其它方法 fallback。

## 4.4 数据集级 LGA 分数

原始主分数使用未经维度除法的梯度内积：

\[
S_{\mathrm{LGA}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\phi_{i,l}.
\]

由于候选层只在同一模型内部排序，主版本不需要为了跨模型比较而除以参数维度。`raw dot` 的绝对值不得跨模型、跨数据集直接比较；跨模型汇总只能比较 Top-K 命中、Best@K、Regret@K 等真实编辑评价指标。

可额外保存：

\[
S_{\mathrm{LGA\text{-}cos}}(l)
=
\frac{1}{N}
\sum_i
\cos
\left(
g_{i,l}^{old},
g_{i,l}^{new}
\right),
\]

\[
S_{\mathrm{old\text{-}norm}}(l)
=
\frac{1}{N}\sum_i
\left\|
g_{i,l}^{old}
\right\|_2,
\]

\[
S_{\mathrm{new\text{-}norm}}(l)
=
\frac{1}{N}\sum_i
\left\|
g_{i,l}^{new}
\right\|_2.
\]

这些辅助量用于解释分数来源，不替代原始 dot-product 主排序。

## 4.4.1 Tukey 异常层诊断

可以额外保存 Tukey-filtered 排名作为诊断，但不能替代主排序。主候选层仍由 `raw_old_new_parameter_gradient_dot` 直接降序得到。

定义：

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

输出时记录：

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

若 filtered ranking 与 raw ranking 差异很大，只能作为稳定性说明；不得在看过真实编辑结果后选择 raw 或 filtered 中更好的一个作为主方法。

## 4.5 候选层

\[
\mathcal C_{\mathrm{LGA},K}
=
\operatorname{TopK}_{l}
S_{\mathrm{LGA}}(l).
\]

如果所有层分数为负，仍然按数值从大到小排序，不改成绝对值。

LGA 主版本不执行 Pre 偏移。

## 4.6 Hidden Visual LGA 变体

可以额外计算：

```text
LGA-Hidden-Visual-Direct
```

其梯度对象为 \(h_{i,l}^{v}\)，但必须标记为：

> 面向 VLM 的 hidden-state 适配变体，而不是原始参数空间 LGA。

它不能取代 `LGA-Param-Direct` 主基线。

## 4.7 输出

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
  "old_source": "frozen_base_model_generation",
  "rank_metric": "raw_old_new_parameter_gradient_dot",
  "dot_normalization": "none",
  "cross_model_score_comparable": false,
  "top_k": 5,
  "candidate_layers": [17, 16, 18, 19, 20]
}
```

---

# 5. Perturb-KL-Direct

## 5.1 方法定位

扰动定位直接测量对某层内部视觉表示施加干预后，模型输出分布发生多大变化。

主扰动基线使用：

```text
Perturb-KL-Direct-AltSeq
```

即直接选择 KL 最大的敏感层，不将其统一前移。

`Perturb-KL-Pre-AltSeq` 仅作为 adapter 前置插入消融。

与 VisEdit-style 不同，`Perturb-KL-Direct-AltSeq` 不是对原文 key token 贡献公式的复现，而是本文构造的“序列级扰动敏感性基线”：在完整 `alt` 序列上比较 clean 与 perturbed 输出分布的 KL。该设置尤其适合 MMKE-Visual / MMKE-Entity 中较长、语义完整的目标答案，避免只看首个 token 时忽略后续实体描述。

## 5.2 扰动对象

只扰动 decoder 第 \(l\) 层中的 visual tokens：

\[
\tilde h_{i,l}^{v}
=
h_{i,l}^{v}
+
\epsilon_{i,l}^{\alpha,r}.
\]

其中：

\[
\epsilon_{i,l}^{\alpha,r}
\sim
\mathcal N
\left(
0,
(\alpha\sigma_{i,l}^{v})^2
\right),
\]

\[
\sigma_{i,l}^{v}
=
\operatorname{Std}
(h_{i,l}^{v}).
\]

这里的标准差必须在该样本该层的全部 visual tokens 与 hidden 维度上计算，使用：

```text
unbiased = false
```

扰动位置是 decoder block \(l\) 的输出，即 adapter 候选层同一 hook 位置；不得在 attention 内部、MLP 内部或 block 输入处另设扰动点。

主结果必须使用：

```text
perturb_scope = visual_tokens
```

如果某个 wrapper 无法获得视觉 token 区间，应先修复 wrapper，或者将该配置标记为 `unavailable`。不得把 `all_prompt_tokens` 的结果混入 visual-token 主表。

## 5.3 噪声尺度

\[
\mathcal A
=
\{0.1,0.5,1,3\}.
\]

每个尺度使用固定种子重复：

\[
R=3.
\]

默认：

```text
seeds = [2026, 2027, 2028]
```

实际运行时每个样本、噪声尺度和重复编号的随机数种子应由稳定哈希生成。主实验使用 common random numbers，不把 `layer` 放入 seed key：

```text
seed = hash(dataset, subset, model, sample_id, alpha, repeat)
```

哈希种子不得依赖 batch 顺序、DataLoader worker 数、GPU 数或运行时间，也不得依赖 layer index。这样断点续跑、换卡或改变 batch size 时，已完成层和补跑层仍可复现；不同层会接收同一基础噪声方向，只比较层表示和层敏感性差异。

该多尺度、多随机种子融合是本研究构建的稳健扰动基线，不应表述为某篇论文的固定算法设置。

## 5.4 目标序列上的 KL

正常 teacher-forcing 输出分布：

\[
p_{i,t}^{clean}(y).
\]

扰动第 \(l\) 层后：

\[
p_{i,l,t}^{\alpha,r}(y).
\]

KL 方向固定为：

```text
D_KL(clean || perturbed)
```

计算 softmax、log_softmax 与 KL 时必须把 logits 转为 float32，在完整 vocabulary 上计算，并用 target mask 排除 prompt、visual token、padding 和被截断位置。

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
\right).
\]

其中：

\[
D_{\mathrm{KL}}(p\Vert q)
=
\sum_y
p(y)
\log
\frac{p(y)}{q(y)}.
\]

数据集平均：

\[
S_{\mathrm{KL}}^{\alpha,r}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
D_{i,l}^{\alpha,r}.
\]

## 5.5 稳健分数

对每个 \((\alpha,r)\) 先计算动态范围：

\[
\Delta_{\alpha,r}
=
\max_l S_{\mathrm{KL}}^{\alpha,r}(l)
-
\min_l S_{\mathrm{KL}}^{\alpha,r}(l).
\]

再计算中位尺度：

\[
M_{\alpha,r}
=
\left|
\operatorname{median}_l S_{\mathrm{KL}}^{\alpha,r}(l)
\right|.
\]

若满足：

\[
\Delta_{\alpha,r}
<
\max
\left(
\epsilon_{\mathrm{abs}},
\epsilon_{\mathrm{rel}}M_{\alpha,r}
\right),
\]

则该 \((\alpha,r)\) 判定为近似常数的无信息组，不参与稳健分数平均。长表仍必须保留该组的原始 KL、动态范围和排除原因。

初始阈值：

```text
epsilon_abs = 1e-8
epsilon_rel = 1e-3
```

最终阈值必须在 `EVQA-pilot500 × BLIP2-OPT-2.7B` pilot 后冻结。

有效噪声组定义为：

\[
\mathcal G_{\mathrm{valid}}
=
\left\{
(\alpha,r):
\text{该组动态范围有效}
\right\}.
\]

对每个有效 \((\alpha,r)\) 在同一个“数据集 × 模型”内部做层间归一化：

\[
\hat S_{\mathrm{KL}}^{\alpha,r}(l)
=
\operatorname{MinMaxNorm}_{l}
S_{\mathrm{KL}}^{\alpha,r}(l).
\]

最终稳健分数只对有效组平均：

\[
S_{\mathrm{KL}}^{robust}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
\hat S_{\mathrm{KL}}^{\alpha,r}(l).
\]

同时记录未归一化 raw mean KL：

\[
S_{\mathrm{KL}}^{rawmean}(l)
=
\frac{1}{|\mathcal G_{\mathrm{valid}}|}
\sum_{(\alpha,r)\in\mathcal G_{\mathrm{valid}}}
S_{\mathrm{KL}}^{\alpha,r}(l).
\]

若 \(|\mathcal G_{\mathrm{valid}}|=0\)，该“数据集 × 模型”组合不可用：

```text
status = unavailable
failure_reason = no_informative_alpha_repeat_group
```

不跨模型比较 KL 分数绝对值。

## 5.6 Direct 候选层

\[
\mathcal C_{\mathrm{KL\text{-}Direct},K}
=
\operatorname{TopK}_{l}
S_{\mathrm{KL}}^{robust}(l).
\]

这就是主扰动候选层。

## 5.7 Pre 消融

可根据平滑后的 robust KL 分数识别高敏感区：

\[
\mathcal H_{\mathrm{KL}}
=
\left\{
l:
\tilde S_{\mathrm{KL}}(l)
\ge
\mu_{\mathrm{KL}}
+
\lambda\sigma_{\mathrm{KL}}
\right\}.
\]

取最长连续区间：

\[
[s_{\mathrm{KL}},e_{\mathrm{KL}}],
\]

再构造：

\[
\mathcal C_{\mathrm{KL\text{-}Pre},K}
=
\{
s_{\mathrm{KL}}-1,
\ldots,
s_{\mathrm{KL}}-K
\}.
\]

该版本只用于检验“敏感区之前是否更适合挂 adapter”，不进入主扰动基线列。

## 5.8 输出

```json
{
  "method": "Perturb-KL-Direct-AltSeq",
  "variant": "direct",
  "key_mode": "alt_sequence",
  "perturb_scope": "visual_tokens",
  "noise_scales": [0.1, 0.5, 1, 3],
  "seeds": [2026, 2027, 2028],
  "rank_metric": "score_kl_robust_alt_sequence",
  "top_k": 5,
  "candidate_layers": [25, 21, 20, 18, 17]
}
```

---

# 6. Ours-Direct

## 6.1 方法定位

本文公式的目标是**直接预测适合挂载视觉编辑 adapter 的层**，而不是先定位知识贡献区或敏感区，再向前移动。

`Ours-Direct` 的具体计算和输出字段以专项手册 `md/Location/Equations/zn_visual_gradient_prediction_实验操作手册（完整规范）.md` 为执行口径；本总手册只规定主实验方法名、候选层语义和跨方法公平约束。若旧版记录中出现 `rel/gen/avg`、拐点或 raw dot 排序，它们只作为诊断/历史消融，不进入当前 `Ours-Direct` 主候选。

因此主方法固定为：

```text
Ours-Direct
```

禁止在主实验中对得分峰值额外执行 Pre 偏移。

主实验旧知识字段统一使用冻结模型确定性解码缓存的 `model_pred`。已有 `pred` 字段只可作为 `Ours-Direct-AltPred` 附加分析，必须单独成表、单独命名，不得混入 `Ours-Direct` 主排序。

## 6.2 新旧知识视觉梯度

对第 \(i\) 个样本、第 \(l\) 层 visual-token hidden states：

\[
g_{i,l}^{new}
=
\nabla_{h_{i,l}^{v}}
\mathcal L_i^{new},
\]

\[
g_{i,l}^{old}
=
\nabla_{h_{i,l}^{v}}
\mathcal L_i^{old}.
\]

在视觉 token 维度聚合：

\[
\bar g_{i,l}^{new}
=
\frac{1}{|\mathcal V_i|}
\sum_{j\in\mathcal V_i}
g_{i,l,j}^{new},
\]

\[
\bar g_{i,l}^{old}
=
\frac{1}{|\mathcal V_i|}
\sum_{j\in\mathcal V_i}
g_{i,l,j}^{old}.
\]

## 6.3 层级辅助量

新旧梯度余弦：

\[
S_{\cos}^{v}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\cos
\left(
\bar g_{i,l}^{new},
\bar g_{i,l}^{old}
\right).
\]

新知识梯度强度：

\[
S_{\mathrm{new\text{-}norm}}^{v}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
\bar g_{i,l}^{new}
\right\|_2.
\]

## 6.4 本文主分数

本手册保留当前已经确定的候选层公式：

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

其中：

- \(\max(0,-S_{\cos}^{v}(l))\)：鼓励新旧知识更新方向存在冲突，有利于替换旧答案；
- \(S_{\mathrm{new\text{-}norm}}^{v}(l)\)：保证该层对新知识具有足够强的视觉梯度；
- \(\left(\frac{l+1}{L}\right)^2\)：当前公式中的深度权重，明确用于偏向具有更强后续预测作用的较深层。

本节不再写“避免层位置过深”，因为该深度项实际上随层深增加而增大。

正式批量实验前必须确认代码实现与本公式完全一致，尤其是：

```text
cosine sign = negative cosine
depth factor = ((l + 1) / L)^2
```

不得在不同模型或数据集上临时修改符号或深度项。

## 6.5 直接候选层

候选层生成前先过滤不可用层：

```text
S_v_zero_grad = true
S_v_new_norm is nonfinite
S_v_cos is nonfinite
visual_token_start/end empty
```

若过滤后无有效层：

```text
status = unavailable
failure_reason = no_valid_ours_direct_layer
```

\[
\mathcal C_{\mathrm{ours},K}
=
\operatorname{TopK}_{l}
S_{\mathrm{ours}}(l).
\]

该 Top-K 就是本文预测的 adapter 插入层，不做平滑区间识别，不做 Pre 偏移。

## 6.6 输出

```json
{
  "method": "Ours-Direct",
  "variant": "direct",
  "new_field": "alt",
  "old_field": "model_pred",
  "score_space": "hidden_visual_tokens",
  "rank_metric": "negative_cosine_times_new_norm_times_depth2",
  "required_scores": ["S_v_cos", "S_v_neg_cos", "S_v_new_norm", "S_v_depth2", "S_ours"],
  "top_k": 5,
  "candidate_layers": [17, 19, 16, 18, 20]
}
```

为保证跨数据集一致，建议主版本统一使用：

```text
old_field = model_pred
```

`pred` 有效时可另做 `Ours-Direct-AltPred` 附加分析。

输出长表必须同时保留 raw 诊断排序所需字段，包括 `S_v_dot`、`S_v_conflict`、`S_v_dot_per_dim`、`S_v_cos`、`S_v_new_norm`、`S_v_zero_grad`、`S_v_neg_cos`、`S_v_depth2`、`S_ours`。其中只有 `S_ours` 用于主候选 Top-K。

---

# 6.5 CMA-Direct / Visual Causal Restoration

## 6.5.1 方法定位

`CMA-Direct` 参考专项手册 `md/Location/Equations/CMA-Direct.md`，使用 Visual Causal Restoration / Causal Mediation Analysis 风格的污染-恢复实验，为每个候选层估计视觉表征被恢复后对目标答案生成的挽救能力。

该方法可以进入候选层主表，但结果解释必须保持边界：

```text
CMA-Direct measures causal restoration capacity under corrupted visual input, not adapter editability itself.
```

也就是说，`CMA-Direct` 可以作为候选层定位方法，但不能被称为真实最佳编辑层或 Adapter 性能真值。

## 6.5.2 Clean / Corrupt / Restore

对每个样本 \(i\)，先执行正常输入：

\[
s_i^{clean}
=
\frac{1}{T_i}
\sum_t
\log p_{\theta}(y_{i,t}^{alt}\mid x_i^{clean}, y_{i,<t}^{alt}).
\]

然后只污染 decoder 输入端的 visual tokens，得到：

\[
s_i^{corrupt}
=
\frac{1}{T_i}
\sum_t
\log p_{\theta}(y_{i,t}^{alt}\mid x_i^{corrupt}, y_{i,<t}^{alt}).
\]

最后在污染输入下，将第 \(l\) 层 visual-token hidden states 恢复为 clean forward 缓存值：

\[
H_{i,l}^{v,corrupt}
\leftarrow
H_{i,l}^{v,clean},
\]

并计算：

\[
s_i^{restore}(l)
=
\frac{1}{T_i}
\sum_t
\log p_{\theta}(y_{i,t}^{alt}\mid x_i^{restore(l)}, y_{i,<t}^{alt}).
\]

Hook 位置仍采用本手册统一定义：decoder block \(l\) 输出之后、block \(l+1\) 之前；恢复范围只包括 visual tokens，不恢复文本 token。

## 6.5.3 有效样本过滤

只有污染确实降低目标答案支持时，样本才进入 CMA 层排序：

\[
s_i^{clean}
>
s_i^{corrupt}
+
\delta.
\]

默认：

```yaml
delta_logprob: 0.05
min_valid_samples: 30
min_valid_ratio: 0.2
```

如果有效样本不足，结果必须标记为：

```text
low_valid_coverage
```

如果没有有效样本：

```text
no_valid_cma_sample
```

这些状态不得伪装成正常 Top-K。

## 6.5.4 CMA 主分数

单样本层恢复分数：

\[
CR_i(l)
=
\frac{
s_i^{restore}(l)-s_i^{corrupt}
}{
s_i^{clean}-s_i^{corrupt}+\epsilon
}.
\]

辅助 KL 恢复分数：

\[
KCR_i(l)
=
\frac{
KL_i^{corrupt}-KL_i^{restore}(l)
}{
KL_i^{corrupt}+\epsilon
}.
\]

跨有效样本、噪声强度和随机种子聚合：

\[
S_{\mathrm{CMA}}(l)
=
\operatorname{mean}_{i,\alpha,r}
CR_i(l,\alpha,r).
\]

主排序只使用 \(S_{\mathrm{CMA}}(l)\)。`KCR` 只用于并列层的 tie-break 和诊断。

## 6.5.5 噪声与随机种子

默认配置：

```yaml
corruption_location: decoder_visual_input_embeddings
corruption_scope: visual_tokens
noise_type: gaussian
noise_alpha_list: [0.5, 1.0, 2.0]
noise_seeds: [0, 1, 2]
seed_key: dataset/model/sample_id/alpha/seed
```

`seed_key` 不包含 layer，保证同一样本在所有层上使用相同污染条件。

## 6.5.6 直接候选层

CMA 主版本直接选择恢复分数最高的层，不执行 Pre 偏移：

\[
\mathcal C_{\mathrm{CMA},K}
=
\operatorname{TopK}_{l}
S_{\mathrm{CMA}}(l).
\]

排序规则：

1. \(S_{\mathrm{CMA}}(l)\) 从大到小；
2. 并列时优先 `KCR_mean` 更大；
3. 仍并列时优先 `valid_samples(l)` 更多；
4. 仍并列时层号小的排前。

## 6.5.7 Raw 与 Clean 候选层

`CMA-Direct` 与其他方法一样，必须同时保存：

```text
raw_top3
clean_top3
raw_top5
clean_top5
removed_layers
```

清洗规则：

1. 去除重复层，保留第一次出现的位置；
2. 删除越界层；
3. 删除 hook 失败、有效样本数为 0 或分数为非有限值的层；
4. 不自动补齐被删除层，除非结果中显式记录 `fill_from_next_rank=true`。

## 6.5.8 输出

```json
{
  "method": "CMA-Direct",
  "variant": "direct",
  "score_space": "visual_hidden_restoration",
  "target_field": "alt",
  "corruption_scope": "visual_tokens",
  "rank_metric": "CR_mean",
  "aux_metric": "KCR_mean",
  "noise_alpha_list": [0.5, 1.0, 2.0],
  "noise_seeds": [0, 1, 2],
  "top_k": 5,
  "raw_candidate_layers": [17, 16, 18, 15, 19],
  "clean_candidate_layers": [17, 16, 18, 15, 19],
  "status": "done"
}
```

长表至少保留：

```text
dataset
model
sample_id
layer
alpha
seed
s_clean
s_corrupt
s_restore
clean_corrupt_gap
cr
kcr
is_valid
invalid_reason
```

---

# 7. Oracle 与真实编辑上界

## 7.1 Candidate-union Oracle

设所有主定位方法候选层并集为：

\[
\mathcal U
=
\bigcup_m
\mathcal C_{m,5}.
\]

在 \(\mathcal U\) 中训练并评测所有层：

\[
l_{\mathrm{union}}^*
=
\arg\max_{l\in\mathcal U}
A(l).
\]

该结果必须称为：

```text
Candidate-union Oracle
```

不能称为全局最优层。

## 7.2 Full-layer Oracle

只有在全部层均完成相同配置的真实编辑训练时，才可定义：

\[
l_{\mathrm{full}}^*
=
\arg\max_{l\in\{0,\ldots,L-1\}}
A(l).
\]

名称：

```text
Full-layer Oracle Sweep
```

建议至少在：

```text
pilot500 × BLIP2-OPT
```

上完成一次全层扫描，为候选定位准确性提供真实参考。

## 7.3 编辑性能

\[
A(l)
=
\frac{
Rel(l)
+
TGen(l)
+
MGen(l)
+
TLoc(l)
+
MLoc(l)
}{5}.
\]

如果某个数据集的官方 Overall 定义不同，应优先使用官方定义，并单独记录公式。

## 7.4 定位评价

### Top-1 Performance

\[
\operatorname{Top1Perf}(m)
=
A(l_{m,1}).
\]

### Mean@K

\[
\operatorname{Mean@K}(m)
=
\frac{1}{K}
\sum_{l\in\mathcal C_{m,K}}
A(l).
\]

### Best@K

\[
\operatorname{Best@K}(m)
=
\max_{l\in\mathcal C_{m,K}}
A(l).
\]

### Regret@K

相对于可用的 oracle：

\[
\operatorname{Regret@K}(m)
=
A(l^*)
-
\operatorname{Best@K}(m).
\]

必须注明 \(l^*\) 来自：

```text
Candidate-union Oracle
```

还是：

```text
Full-layer Oracle
```

### Hit@K

\[
\operatorname{Hit@K}(m)
=
\mathbb I
\left[
l^*\in\mathcal C_{m,K}
\right].
\]

### 排序相关性

只有在真实编辑覆盖足够多层时才计算：

\[
\rho_{\mathrm{Spearman}},
\qquad
\tau_{\mathrm{Kendall}},
\qquad
\operatorname{NDCG@K}.
\]

## 7.5 Random-Uniform-TopK 附录基线

`Random-Uniform-TopK` 只作为附录或 sanity-check 基线，不进入主候选方法集合，也不参与 Candidate-union Oracle 的主并集构造。

规则：

```text
candidate_pool = all legal decoder layer indices
sample_without_replacement = true
repeat = 30 or more
seed = fixed and reported
```

报告时只比较真实编辑指标：

```text
Random Mean@K
Random Best@K
Random 95% CI
```

不得用随机候选层替代任何失败方法的候选层。

---

# 8. 统一执行流程

## 8.1 阶段 A：准备基础模型输出

对每个“数据集 × 模型”组合：

1. 冻结基础模型；
2. 建立模型注册表；
3. 建立样本 manifest；
4. 对全部 localization 样本生成 `model_pred`；
5. 缓存 tokenized `alt`、`pred`、`model_pred`；
6. 记录 visual token 区间；
7. 固定图像预处理和输入分辨率。

模型注册表至少记录：

```text
model_name
checkpoint_or_repo_id
revision_or_commit
processor_or_tokenizer_name
decoder_module_path
num_decoder_layers
hidden_size
mlp_parameter_patterns
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

样本 manifest 至少记录：

```text
dataset
subset
sample_id
image_path
image_exists
question
alt_answer_raw
pred_answer_raw
split_source
used_for_localization
used_for_training
used_for_eval
skip_reason
```

`model_pred` 必须使用确定性解码生成并缓存：

```text
do_sample = false
num_beams = 1
temperature = 0 or unset
fixed max_new_tokens
fixed stop tokens
fixed prompt template
```

缓存内容至少包括 `raw_text`、`normalized_text`、`token_ids`、`effective_token_length`、`empty_or_invalid_status`。后续所有需要 `model_pred` 的定位方法只能读取缓存，不得在不同方法内部重复生成。

Qwen2.5-VL 等动态分辨率模型必须固定输入大小，例如：

```text
448 × 448
```

或固定视觉 token 预算，否则不同样本的 visual-token 范围不可直接比较。

## 8.2 阶段 B：计算候选层

主实验仅计算：

```text
Middle-Prior-Direct
VisEdit-Contrib-Pre-KeyToken
SaLEM-Alt-Direct
LGA-Param-Direct-AltModelPred
Perturb-KL-Direct-AltSeq
Ours-Direct
CMA-Direct
```

每种方法同时输出：

```text
Top-3
Top-5
full layer scores
full layer ranking
configuration
status
```

## 8.3 阶段 C：候选层并集

\[
\mathcal U_3
=
\bigcup_m
\mathcal C_{m,3},
\]

\[
\mathcal U_5
=
\bigcup_m
\mathcal C_{m,5}.
\]

先训练 \(\mathcal U_3\)，再补充 \(\mathcal U_5-\mathcal U_3\)。同一层只训练一次。

## 8.4 阶段 D：真实编辑训练

所有候选层统一：

```text
same frozen base model
same adapter architecture
same adapter parameter count
same adapter initialization rule
same localization/training data
same optimizer
same learning rate
same batch size
same epochs / steps
same checkpoint-selection rule
same evaluation data
```

同一模型内部必须使用完全一致的 adapter 结构、参数量、初始化方式和优化器配置；跨模型比较时至少保持同一设计原则，并记录 adapter rank、bottleneck hidden size、adapter 参数量以及 adapter 参数占基础模型参数的比例。

训练随机种子至少：

```text
[2026, 2027, 2028]
```

报告：

\[
\operatorname{mean}\pm\operatorname{std}.
\]

最终 eval/test 不得参与 checkpoint 选择。允许的 checkpoint 规则只有以下三类之一：

1. 固定最后一步或固定 epoch；
2. 固定 validation split 上的最低训练目标损失；
3. 预先声明的训练集 EMA loss 规则。

如果某层训练发散、出现 NaN/Inf、未生成 checkpoint 或 visual hook 失败，必须保留该层记录并标注 `status` 与 `failure_reason`，不得把失败层替换为其他方法或其他层的结果。

## 8.5 阶段 E：宏平均

跨模型、跨数据集汇总时：

1. 先在每个 `dataset × model` 组合内计算方法得分；
2. 再对组合做 macro-average。

不能把所有样本直接 micro-average，否则样本数较大的数据集会主导结论。

---

# 9. 标准输出文件

## 9.1 `model_registry.yaml`

每个模型一条记录，用于解释层编号、hook 位置和参数范围：

```text
model_name
checkpoint_or_repo_id
revision_or_commit
decoder_module_path
num_decoder_layers
valid_layer_index_range
hidden_size
mlp_parameter_patterns
visual_token_rule
adapter_hook_position
image_size_or_visual_token_budget
dtype
quantization
torch_version
transformers_version
wrapper_commit_or_hash
```

## 9.2 `sample_manifest.csv`

每个样本一条记录，用于保证所有候选方法使用同一批可用样本：

```text
dataset
subset
sample_id
image_path
image_exists
question_hash
alt_answer_hash
pred_answer_hash
model_pred_hash
used_for_localization
used_for_training
used_for_eval
skip_reason
```

## 9.3 `layer_scores.csv`

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
localization_sample_count
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
processed_sample_count
status
failure_reason
score_source_file
```

## 9.4 `candidate_layers_topk.csv`

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
dedupe_or_filter_reason
selection_source
candidate_conversion
pre_region_start
pre_region_end
```

主实验不允许用其他方法做 fallback。若方法失败：

```text
status = unavailable
```

或：

```text
status = low_confidence
```

但不得把中层先验结果伪装成该方法的候选层。

## 9.5 `candidate_union_for_edit.csv`

```text
dataset,subset,model,layer,selected_by_methods
MMKE,visual,llava-v1.5-7b,17,Ours-Direct|SaLEM-Alt-Direct
```

## 9.6 `edit_results_by_layer.csv`

```text
dataset
subset
model
layer
seed
best_checkpoint
training_steps
adapter_parameter_count
adapter_parameter_percentage
checkpoint_selection_rule
selection_metric
localization_config_hash
training_config_hash
evaluation_config_hash
Rel
T-Gen
M-Gen
T-Loc
M-Loc
Average
```

## 9.7 `localization_method_summary.csv`

```text
dataset
subset
model
method
top_k
top1_performance
mean_at_k
best_at_k
regret_at_k
hit_at_k
oracle_type
```

---

# 10. 主实验默认配置

| 方法 | 主目标/对象 | 主排序 | 候选转换 |
|---|---|---|---|
| Middle-Prior-Direct | 网络深度 | 距离中点 | Direct |
| VisEdit-Contrib-Pre-KeyToken | key token prediction 模块贡献 | positive contribution | Pre |
| SaLEM-Alt-Direct | MLP 参数 | 参数→列→矩阵→层显著性 | Direct |
| LGA-Param-Direct-AltModelPred | MLP 参数 | old/new 参数梯度 raw dot | Direct |
| Perturb-KL-Direct-AltSeq | visual tokens | 多噪声、多种子 robust KL | Direct |
| Ours-Direct | visual-token hidden gradients | 负余弦 × new norm × depth² | Direct |
| CMA-Direct | visual-token hidden restoration | 污染视觉输入下的 CR 因果恢复分数 | Direct |

默认参数：

| 参数 | 值 |
|---|---|
| Middle midpoint ratio | 0.5 |
| VisEdit smoothing window | 3 |
| VisEdit \(\lambda\) | 0.5 |
| VisEdit target position | key token prediction |
| SaLEM target parameters | MLP/FFN |
| LGA target parameters | MLP/FFN |
| Perturb noise scales | 0.1, 0.5, 1, 3 |
| Perturb seeds | 2026, 2027, 2028 |
| Perturb seed key | dataset, subset, model, sample_id, alpha, repeat |
| Perturb target positions | complete alt sequence |
| Perturb scope | visual tokens |
| Perturb invalid groups | exclude near-constant/no-informative alpha × repeat groups |
| CMA corruption location | decoder visual input embeddings |
| CMA noise scales | 0.5, 1.0, 2.0 |
| CMA seeds | 0, 1, 2 |
| CMA seed key | dataset, model, sample_id, alpha, seed |
| CMA target positions | complete alt sequence |
| CMA restore scope | visual tokens |
| CMA valid sample rule | `s_clean > s_corrupt + 0.05` |
| CMA primary score | `CR_mean` |
| CMA auxiliary score | `KCR_mean` |
| Candidate K | 3 and 5 |
| Adapter training seeds | 2026, 2027, 2028 |

数值与梯度设置：

| 项目 | 规则 |
|---|---|
| model mode | `model.eval()`，dropout disabled |
| cache during backward | `use_cache = false` |
| gradient accumulation | 每个样本或小批次后清理梯度，不跨样本残留 |
| score dtype | 分数累积使用 float32 |
| SaLEM/LGA weights | 不使用 4-bit/8-bit 量化权重计算主梯度分数 |
| nonfinite score | 记录 `status=unavailable` 与 `failure_reason`，不得改写为 0 |
| empty visual span | 记录失败样本和层，不得 fallback 到 all prompt tokens |

---

# 11. 方法公平性检查清单

正式运行每个组合前检查：

- [ ] 所有方法使用同一 localization 样本集合。
- [ ] 已建立 `model_registry.yaml`，并记录 decoder path、层数、合法层范围、visual-token rule、hook 位置和 wrapper 版本。
- [ ] 已建立 `sample_manifest.csv`，缺图、空答案、不可用样本均有 `skip_reason`。
- [ ] visual-token 与 adapter hook 单元测试已通过。
- [ ] 目标位置口径已按方法区分：VisEdit-style 使用 key token prediction；Perturb-KL-Direct / CMA-Direct 使用完整 `alt` 序列。
- [ ] `model_pred` 已由对应冻结模型用确定性解码生成并缓存，后续方法只读缓存。
- [ ] teacher-forcing 使用统一 shift 与 target mask，prompt、visual、padding 位置均为 `-100`。
- [ ] SaLEM 与 LGA 均只比较统一的 MLP/FFN 参数集合。
- [ ] LGA 主实验参数范围固定为 `mlp_ffn_weight_only`，不混入 bias、attention、LayerNorm 或 adapter 参数。
- [ ] LGA 的 `AltModelPred` 与 `AltPred` 结果分别命名、分别成表，不混入同一主排序。
- [ ] 原始 LGA 使用参数梯度，而不是 hidden-state 梯度。
- [ ] LGA 使用逐层或逐参数块流式计算，只累计 dot 标量，不保存全量 old/new 参数梯度。
- [ ] LGA 先逐样本计算 dot 再平均，不对平均梯度做 dot。
- [ ] LGA raw dot 只用于同一模型内部排序，不跨模型比较绝对分数。
- [ ] Perturb-KL 只扰动 visual tokens。
- [ ] Perturb-KL 使用 `D_KL(clean || perturbed)`、float32 logits、完整 vocabulary 和稳定哈希种子。
- [ ] Perturb-KL 主实验 seed key 不包含 layer，使用 common random numbers。
- [ ] Perturb-KL 近似常数/无信息 alpha × repeat 组从 robust score 中排除，并保留长表诊断。
- [ ] 所有模型使用一致的候选层编号定义。
- [ ] Ours 直接输出 adapter 层，不执行 Pre。
- [ ] Ours-Direct 主排序只使用 `S_ours = max(0, -S_v_cos) × S_v_new_norm × ((l+1)/L)^2`，raw dot、rel/gen/avg 和拐点只作诊断/消融。
- [ ] Ours-Direct 主实验旧知识字段使用 `model_pred`；`pred` 版本必须命名为 `Ours-Direct-AltPred` 并单独成表。
- [ ] CMA-Direct 只污染 decoder 输入端 visual tokens，恢复 decoder block output 的 visual-token hidden states。
- [ ] CMA-Direct 主实验使用完整 `alt` 序列的 teacher-forcing mean logprob 计算 `s_clean/s_corrupt/s_restore`。
- [ ] CMA-Direct 主实验 seed key 不包含 layer，同一样本所有层使用相同污染条件。
- [ ] CMA-Direct 有效样本必须满足 `s_clean > s_corrupt + delta`；低有效样本覆盖率必须标记为 `low_valid_coverage`。
- [ ] CMA-Direct 主排序只使用 `CR_mean`，`KCR_mean` 只作为辅助诊断和 tie-break。
- [ ] CMA-Direct 是因果恢复候选层方法，不写成真实最佳 Adapter 编辑层。
- [ ] 主表中没有使用其他方法做 fallback。
- [ ] 重复层和越界层同时保留 raw 候选记录与清洗后候选记录。
- [ ] Random-Uniform-TopK 只作为附录基线，不进入主候选方法并集。
- [ ] Candidate-union Oracle 与 Full-layer Oracle 名称已区分。
- [ ] 最终 eval/test 没有参与 checkpoint 选择。
- [ ] 每个真实编辑结果都记录 adapter 参数量、checkpoint 选择规则和配置 hash。
- [ ] 每个候选层使用至少 3 个训练随机种子。
- [ ] Top-3 与 Top-5 分开评价。
- [ ] 除 Best@K 外，还报告 Top1 和 Mean@K。
- [ ] 跨任务最终结果使用 macro-average。

---

# 12. 论文中的统一表述

> 本文将视觉语言模型编辑层定位建模为 Top-\(K\) 候选 adapter 插入层推荐问题。不同基线按照其原始语义生成候选层：中层先验直接选择网络中部层，VisEdit-style 基线遵循原文 key token prediction 贡献，依据每层 Attention / MLP 输出对 key token 的贡献识别高贡献区域并选择其前置层，SaLEM 直接选择参数显著性最高的层，LGA 根据旧知识与新知识的层参数梯度内积选择 golden layers，扰动基线是本文构造的序列级敏感性基线，在完整 `alt` 序列上直接选择视觉表示扰动后输出分布 KL 变化最大的敏感层，CMA-Direct 在污染视觉输入下选择恢复 clean visual hidden states 后最能挽救目标答案概率的因果恢复层。与上述方法不同，本文方法的分数被定义为对 adapter 插入适宜性的直接估计，因此直接按分数选择 Top-\(K\) 层，而不执行额外的前置偏移。随后，所有候选层均使用相同结构的视觉编辑 adapter、相同训练配置和相同评测协议进行真实编辑验证。

---

# 13. 参考方法来源说明

- `Middle-layer Prior`：依据 ROME、MEMIT 等语言模型编辑工作体现出的中层 MLP 编辑经验构造，不是独立论文提出的正式算法名。
- `VisEdit-Contrib-Pre`：依据 VisEdit 的模块贡献归因和高贡献层之前插入 VEAD 的设计；原文计算的是每层 Attention / MLP 输出对 key token prediction 的贡献，因此主版本使用 key token。完整 `alt` 序列贡献只能作为诊断/消融，不替代 VisEdit-style 主排序；本手册的高贡献区阈值是跨模型自动化规则。
- `SaLEM-based`：复用 SaLEM 的显著层选择部分，不包含原始 SaLEM 后续的 MEND 编辑器。
- `GoldenLayer/LGA`：原始方法使用旧知识与新知识的层参数梯度内积估计 golden layer。
- `Perturb-KL-Direct`：本研究基于表示扰动和输出 KL 构建的稳健定位基线，Direct 是标准主版本，Pre 是 adapter 插入消融。该方法不是 VisEdit 原文复现，而是本文构造的“序列级扰动敏感性基线”，主方法在完整 `alt` 序列上计算 KL，尤其适合 MMKE 这类长目标答案。
- `CMA-Direct`：参考 Visual Causal Restoration / Causal Mediation Analysis 的污染-恢复思想，选择视觉污染条件下恢复 clean visual hidden states 后 `CR_mean` 最高的层；该方法衡量因果恢复能力，不等价于 Adapter 编辑性能真值。
- `Ours-Direct`：本文直接预测视觉 adapter 插入层的方法。
