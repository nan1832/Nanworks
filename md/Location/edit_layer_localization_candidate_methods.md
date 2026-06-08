# 编辑层定位方法候选层计算手册

本手册用于指导后续在不同数据集、不同视觉语言模型上的**编辑候选层计算**。目标不是直接证明“知识一定存储在哪一层”，而是让每种定位方法都输出一组候选编辑层 `Top-K`，再通过真实编辑训练与评测验证这些候选层的效果。

适用对象：

- 语言模型编辑：修改某一层参数、MLP/FFN、Attention 或挂载 adapter。
- 视觉语言模型编辑：修改文本解码器层、视觉相关 hidden states、visual tokens，或在指定层挂载 visual adapter。
- 多模型比较：同一方法应在 7 个模型上使用同一套公式和同一套超参数。

---

## 0. 统一符号

设模型共有 \(L\) 个候选层，层编号为：

\[
l \in \{0,1,\dots,L-1\}
\]

数据集为：

\[
\mathcal{D}=\{(x_i^v,x_i^t,y_i^*)\}_{i=1}^{N}
\]

其中：

| 符号 | 含义 |
|---|---|
| \(x_i^v\) | 第 \(i\) 个样本的图像输入 |
| \(x_i^t\) | 第 \(i\) 个样本的文本 prompt / question |
| \(y_i^*\) | 第 \(i\) 个样本的编辑目标答案，通常为数据集中的 `alt` / `target_new` |
| \(o_i^*\) | \(y_i^*\) 的 key token，默认取目标答案的第一个生成 token |
| \(h_{i,l}\) | 第 \(i\) 个样本在第 \(l\) 层的 hidden states |
| \(h_{i,l}^{v}\) | 第 \(i\) 个样本在第 \(l\) 层的 visual token hidden states |
| \(h_{i,l}^{t}\) | 第 \(i\) 个样本在第 \(l\) 层的 text token hidden states |
| \(\theta_l\) | 第 \(l\) 层的可编辑参数，例如 MLP/FFN、Attention、decoder block 或 adapter 所在层参数 |
| \(p_i(y)\) | 正常 forward 时模型在输出位置的概率分布 |
| \(p_{i,l}^{\alpha}(y)\) | 扰动第 \(l\) 层、噪声强度为 \(\alpha\) 后的输出概率分布 |
| \(K\) | 每种方法输出的候选层数量，建议 \(K=3\) 或 \(K=5\) |
| \(\operatorname{TopK}(\cdot)\) | 按得分从高到低取前 \(K\) 个层 |
| \(\operatorname{Rank}(\cdot)\) | 层排序，排名越靠前表示越推荐 |
| \(\operatorname{Norm}(\cdot)\) | 对层得分做 min-max 或 z-score 归一化 |

默认训练/评测原则：

1. 每种定位方法只负责输出候选层。
2. 所有候选层必须使用相同训练集、训练轮数、学习率、batch size、checkpoint 选择规则和评测集。
3. 最终比较以真实编辑指标为准，例如 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average`。
4. 不把“知识存储层”“贡献最高层”“最佳 adapter 插入层”直接等同，最终以真实编辑效果验证。

## 0.1 结合当前实验后的补充原则

为了比较不同编辑层候选方法的性能，每种方法必须同时输出 `Top-3` 和 `Top-5`，并明确记录候选层来自哪个分数、哪个字段和哪个层空间。

必须区分三类层：

| 类型 | 含义 | 是否可直接作为编辑层 |
|---|---|---|
| 贡献峰值层 | 某层对 key token 的贡献度最高 | 不一定 |
| 梯度敏感层 | 某层 hidden state 或参数对目标 loss 梯度最大 | 不一定 |
| 编辑插入层 | adapter / 可编辑模块真正挂载的位置 | 是 |

如果一个方法输出的是“贡献峰值层”或“敏感区间”，需要同时给出两个版本：

1. `Direct`：直接取峰值层 Top-K，作为消融或诊断。
2. `Pre`：取峰值区间之前的 Top-K 层，作为 visual adapter 插入的主版本。

候选层文件必须记录：

```text
dataset
subset / task
model
method
variant: direct / pre / delta / prior / oracle
key_mode: alt / pred / model_pred
rank_metric: score_positive / score_signed / score_abs / average / custom
layer_space: text_decoder / qformer / vision_encoder / adapter_insert
top_k: 3 or 5
rank
layer
score
score_source_file
```

其中 `alt` 表示新知识或目标答案，`pred` 表示旧知识或数据集给定的旧答案，`model_pred` 表示模型当前实际输出。正式编辑层定位应优先比较 `alt` 与 `alt-pred`，`pred` 和 `model_pred` 主要用于分析旧答案支持强度或模型自身输出路径。

---

# 1. Middle-layer Prior

## 1.1 方法名称

**Middle-layer Prior**  
中文可写作：中层先验定位法。

## 1.2 方法思想

许多语言模型编辑工作观察到事实关联和可编辑计算常集中在 Transformer 的中间层，尤其是中层 MLP/FFN 模块。因此，中层先验不计算梯度或贡献度，而是直接把中间层作为候选编辑层。

该方法适合作为最基础的编辑层定位 baseline。

## 1.3 层得分公式

设中层中心位置为：

\[
c_{\text{mid}}=\rho (L-1)
\]

其中 \(\rho\) 是中层比例，默认：

\[
\rho=0.55
\]

对每一层定义中层接近度得分：

\[
S_{\text{mid}}(l)=-\left|l-c_{\text{mid}}\right|
\]

得分越大，表示越接近中层中心。

也可以使用归一化形式：

\[
S_{\text{mid}}(l)=1-\frac{|l-c_{\text{mid}}|}{L-1}
\]

## 1.4 候选层计算

\[
\mathcal{C}_{\text{mid}}=\operatorname{TopK}_{l}\left(S_{\text{mid}}(l)\right)
\]

即取最接近 \(c_{\text{mid}}\) 的 \(K\) 个层。

## 1.5 推荐设置

对于 32 层模型，如果 \(K=5\)，通常会得到类似：

\[
\{L17,L18,L16,L19,L15\}
\]

如果只想和稀疏扫描对齐，也可以使用固定中层组：

\[
\{L10,L15,L19,L20,L25\}
\]

但建议正式实验使用公式化版本，避免人工选择。

## 1.6 输出格式

```json
{
  "method": "Middle-layer Prior",
  "L": 32,
  "rho": 0.55,
  "top_k": 5,
  "candidate_layers": [17, 18, 16, 19, 15]
}
```

---

# 2. VisEdit-Contrib-Pre

## 2.1 方法名称

**VisEdit-Contrib-Pre**  
中文可写作：VisEdit 贡献度引导的高贡献区前置插入法。

## 2.2 方法思想

该方法先计算每层 Attention/MLP 输出对 key token 的贡献度，找到高贡献层区域；但并不直接把 adapter 插在贡献最高层，而是把编辑模块插在高贡献区域之前，使编辑信号能够进入后续高贡献层。

该方法特别适合视觉语言模型中的 visual adapter 插入层选择。

## 2.3 Key token 设定

有两个版本。

### 版本 A：目标答案贡献度

\[
o_i^*=\operatorname{FirstToken}(y_i^*)
\]

其中 \(y_i^*\) 是数据集中的 `alt` / `target_new`。该版本衡量每层对目标编辑答案的支持强度，适合编辑目标层定位。

### 版本 B：模型预测贡献度

\[
o_i^*=\arg\max_{o}p_i(o)
\]

该版本衡量模型当前预测 token 的贡献，适合复现默认贡献度图。

正式编辑层定位建议使用版本 A。

## 2.4 模块贡献度公式

对第 \(i\) 个样本、第 \(l\) 层、第 \(b\) 个模块：

\[
b\in\{\text{attn},\text{mlp}\}
\]

记该模块在追踪 token 位置的输出为：

\[
r_{i,l,b}
\]

将其映射到词表空间：

\[
z_{i,l,b}=\operatorname{LMHead}(\operatorname{FinalNorm}(r_{i,l,b}))
\]

目标 token 的映射概率为：

\[
C^p_{i,l,b}=\operatorname{softmax}(z_{i,l,b})_{o_i^*}
\]

目标 token 的归一化 logit 为：

\[
C^v_{i,l,b}=
\frac{z_{i,l,b,o_i^*}}
{\max\limits_{l',b'} |z_{i,l',b',o_i^*}|+\epsilon}
\]

其中 \(\epsilon\) 是防止除零的小常数，例如：

\[
\epsilon=10^{-8}
\]

使用 signed sqrt 形式计算模块贡献度：

\[
C_{i,l,b}=\operatorname{sign}(C^v_{i,l,b})\sqrt{|C^v_{i,l,b}| \cdot C^p_{i,l,b}}
\]

如果只想保留正贡献，可以使用：

\[
C^{+}_{i,l,b}=\max(0,C_{i,l,b})
\]

## 2.5 层贡献度聚合

默认聚合 Attention 和 MLP：

\[
S_{\text{contrib}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{C^{+}_{i,l,\text{attn}}+C^{+}_{i,l,\text{mlp}}}{2}
\]

如果需要保留符号，可以将 \(C^+\) 替换为 \(C\)。

结合当前 `pilot500` 与 `MMKE` 贡献度实验，实际落表时建议同时保存三种层分数：

| 分数名 | 计算方式 | 含义 |
|---|---|---|
| `score_positive` | \(\max(0,I_{\text{attn}}(l))+\max(0,I_{\text{mlp}}(l))\) | 只看 Attention/MLP 对 key token 的正向支持 |
| `score_signed` | \(I_{\text{attn}}(l)+I_{\text{mlp}}(l)\) | 保留正负方向，适合分析促进或抑制 |
| `score_abs` | \(|I_{\text{attn}}(l)|+|I_{\text{mlp}}(l)|\) | 只看影响强度，不区分方向 |

其中 \(I_{\text{attn}}(l)\)、\(I_{\text{mlp}}(l)\) 是样本平均后的模块贡献度。当前跨模型柱状图主结果使用 `score_positive`。

若中间概率或 logit 出现 `NaN/Inf`，该样本该模块的贡献记为 0，同时在日志中记录非有限值数量；不要让单个异常值改变全层排序。

## 2.5.1 `alt`、`pred` 与 `alt-pred` 候选分数

对同一个模型、同一个数据集，应尽量分别计算：

\[
S_{\text{alt}}(l)=S_{\text{contrib}}(l;\ key=\texttt{alt})
\]

\[
S_{\text{pred}}(l)=S_{\text{contrib}}(l;\ key=\texttt{pred})
\]

\[
S_{\text{model-pred}}(l)=S_{\text{contrib}}(l;\ key=\texttt{model\_pred})
\]

其中：

- `alt`：数据集中的新知识或目标答案，是编辑后希望增强的答案。
- `pred`：数据集中的旧知识或原答案，是编辑时通常希望替换或压低的答案。
- `model_pred`：模型当前自己生成的答案，用来分析模型实际输出路径。

推荐加入目标-旧答案差分分数：

\[
S_{\Delta}(l)=S_{\text{alt}}(l)-\gamma S_{\text{pred}}(l)
\]

默认：

\[
\gamma=1.0
\]

该分数表示“增强新知识同时避开旧知识强支持层”。如果真实编辑实验显示 `pred` 支持层反而适合做抑制编辑，可以把 `S_pred` 作为单独消融，不要和 `S_alt` 混在同一个主结论里。

因此，贡献度方法至少应输出以下候选方法名：

| 方法名 | 排序分数 | 候选层含义 | 推荐用途 |
|---|---|---|---|
| `VisEdit-Contrib-Direct-Alt` | \(S_{\text{alt}}(l)\) | 目标答案贡献峰值层 | 诊断 / 消融 |
| `VisEdit-Contrib-Pre-Alt` | \(S_{\text{alt}}(l)\) 的高贡献区前置层 | 目标答案高贡献区之前的编辑插入层 | 主比较 |
| `VisEdit-Contrib-Direct-Pred` | \(S_{\text{pred}}(l)\) | 旧答案贡献峰值层 | 旧知识路径分析 |
| `VisEdit-Contrib-Pre-Pred` | \(S_{\text{pred}}(l)\) 的高贡献区前置层 | 旧答案路径前置层 | 抑制编辑消融 |
| `VisEdit-Contrib-Direct-Delta` | \(S_{\Delta}(l)\) | 新旧贡献差分峰值层 | 诊断 / 消融 |
| `VisEdit-Contrib-Pre-Delta` | \(S_{\Delta}(l)\) 的高贡献区前置层 | 避开旧答案支持的新知识插入层 | 推荐重点比较 |
| `VisEdit-Contrib-Direct-ModelPred` | \(S_{\text{model-pred}}(l)\) | 模型自身输出贡献峰值层 | 模型行为解释 |

## 2.6 高贡献区间识别

先对层贡献度做三层平滑：

\[
\tilde{S}_{\text{contrib}}(l)=
\frac{S_{\text{contrib}}(l-1)+S_{\text{contrib}}(l)+S_{\text{contrib}}(l+1)}{3}
\]

边界层使用可用邻居平均。

计算均值和标准差：

\[
\mu=\operatorname{Mean}_{l}(\tilde{S}_{\text{contrib}}(l))
\]

\[
\sigma=\operatorname{Std}_{l}(\tilde{S}_{\text{contrib}}(l))
\]

定义高贡献层集合：

\[
\mathcal{H}=\{l \mid \tilde{S}_{\text{contrib}}(l) \ge \mu+\lambda\sigma\}
\]

默认：

\[
\lambda=0.5
\]

然后选择最长的连续高贡献区间：

\[
[s_{\mathcal{H}},e_{\mathcal{H}}]
\]

其中 \(s_{\mathcal{H}}\) 是高贡献区间起始层，\(e_{\mathcal{H}}\) 是终止层。

如果该规则未形成连续区间，则使用贡献度最高的 \(q\) 个层构成近似高贡献区，并取其中最小层作为起点：

\[
s_{\mathcal{H}}=\min \operatorname{TopQ}_{l}(S_{\text{contrib}}(l))
\]

默认：

\[
q=\max(3,\lceil0.2L\rceil)
\]

## 2.7 前置候选层计算

VisEdit-Contrib-Pre 不直接选择高贡献层，而选择高贡献区之前的层：

\[
\mathcal{C}_{\text{contrib-pre}}=
\{s_{\mathcal{H}}-1,\ s_{\mathcal{H}}-2,\ \dots,\ s_{\mathcal{H}}-K\}
\]

删除越界层：

\[
0 \le l < L
\]

并按距离高贡献区起点从近到远排序。

## 2.8 例子

如果模型有 32 层，贡献度曲线显示高贡献区间为：

\[
[L20,L30]
\]

且 \(K=3\)，则：

\[
\mathcal{C}_{\text{contrib-pre}}=\{L19,L18,L17\}
\]

如果 \(K=5\)，则：

\[
\mathcal{C}_{\text{contrib-pre}}=\{L19,L18,L17,L16,L15\}
\]

## 2.8.1 原文 VisEdit 在 E-VQA 全集上的固定候选层

如果直接复现原文 VisEdit 对 E-VQA 全集的贡献度结论，高贡献层区间与候选编辑层按如下规则确定。层编号使用 0-indexed 的 `L0` 到 `L31`。

统一规则：

\[
\text{TopK}=\{s_{\mathcal{H}}-1,\ s_{\mathcal{H}}-2,\ \dots,\ s_{\mathcal{H}}-K\}
\]

其中 \(s_{\mathcal{H}}\) 是原文标出的高贡献层起始层。

| 模型 | 原文高贡献层区间 | Top-1 插入层 | Top-3 候选层 | Top-5 候选层 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | L20-L31 | L19 | L19,L18,L17 | L19,L18,L17,L16,L15 |
| MiniGPT-4-Vicuna-7B | L18-L31 | L17 | L17,L16,L15 | L17,L16,L15,L14,L13 |
| LLaVA-v1.5-7B | L19-L31 | L18 | L18,L17,L16 | L18,L17,L16,L15,L14 |

这组候选层属于 `VisEdit-Contrib-Pre` 的原文复现版本：不是重新按当前 pilot500 或 MMKE 贡献度曲线估计高贡献区，而是直接使用原文在完整 E-VQA 上给出的高贡献区间。

## 2.9 输出格式

```json
{
  "method": "VisEdit-Contrib-Pre",
  "key_token": "alt_first_token",
  "lambda": 0.5,
  "high_contribution_region": [20, 30],
  "top_k": 5,
  "candidate_layers": [19, 18, 17, 16, 15]
}
```

---

# 3. SaLEM

## 3.1 方法名称

**SaLEM: Salient Layers Editing Model**  
中文可写作：显著层编辑模型。

## 3.2 方法思想

SaLEM 使用数据驱动的层级显著性分布来选择编辑层。核心思想是：如果某一层参数对目标编辑 loss 的梯度更大，则该层对当前编辑任务更敏感，更可能适合作为编辑层。

## 3.3 编辑目标 loss

对于第 \(i\) 个样本，使用目标答案 \(y_i^*\) 计算交叉熵损失：

\[
\mathcal{L}_i=-\log P_{\theta}(y_i^* \mid x_i^v,x_i^t)
\]

如果 \(y_i^*\) 是多 token 答案，则使用平均 token loss：

\[
\mathcal{L}_i=-\frac{1}{T_i}\sum_{t=1}^{T_i}\log P_{\theta}(y_{i,t}^* \mid x_i^v,x_i^t,y_{i,<t}^*)
\]

其中：

| 符号 | 含义 |
|---|---|
| \(T_i\) | 第 \(i\) 个目标答案的 token 数 |
| \(y_{i,t}^*\) | 目标答案的第 \(t\) 个 token |
| \(y_{i,<t}^*\) | 目标答案第 \(t\) 个 token 之前的 token |

## 3.4 参数梯度显著性

对每一层参数 \(\theta_l\) 计算梯度：

\[
g_{i,l}=\nabla_{\theta_l}\mathcal{L}_i
\]

为了避免不同层参数量不同造成偏差，使用参数量归一化梯度范数：

\[
S_{\text{SaLEM}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{\|g_{i,l}\|_1}{|\theta_l|}
\]

也可以使用 L2 形式：

\[
S_{\text{SaLEM}}^{(2)}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{\|g_{i,l}\|_2}{\sqrt{|\theta_l|}}
\]

默认推荐使用 L2 形式：

\[
S_{\text{SaLEM}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{\|\nabla_{\theta_l}\mathcal{L}_i\|_2}{\sqrt{|\theta_l|}}
\]

## 3.5 候选层计算

\[
\mathcal{C}_{\text{SaLEM}}=\operatorname{TopK}_{l}(S_{\text{SaLEM}}(l))
\]

## 3.6 实现注意事项

1. 对所有模型统一使用相同的目标 loss。
2. 如果比较 decoder 层，则 \(\theta_l\) 应对应第 \(l\) 个语言解码器 block。
3. 如果比较 visual adapter 插入层，也可以将 \(\theta_l\) 替换为第 \(l\) 层可挂载 adapter 的虚拟参数或 block 参数。
4. 为避免梯度显存过高，可以每次只保留每层梯度范数，不保存完整梯度。
5. 对多数据集比较时，每个数据集独立计算 \(S_{\text{SaLEM}}(l)\)。

## 3.7 输出格式

```json
{
  "method": "SaLEM",
  "score_type": "parameter_gradient_l2_normalized",
  "target": "full_alt_sequence_loss",
  "top_k": 5,
  "candidate_layers": [16, 17, 20, 18, 19]
}
```

---

# 4. GoldenLayer / LGA

## 4.1 方法名称

**GoldenLayer / Layer Gradient Analysis (LGA)**  
中文可写作：黄金层 / 层梯度分析。

## 4.2 方法思想

GoldenLayer / LGA 的思想是：不对所有层逐一进行完整编辑训练，而是在代理数据集上通过梯度归因估计一组能够泛化到未见样本的“黄金编辑层”。

与 SaLEM 更偏参数梯度显著性不同，LGA 更适合用 hidden states 的梯度归因来计算每层的编辑潜力。

## 4.3 编辑目标 loss

同 SaLEM：

\[
\mathcal{L}_i=-\log P_{\theta}(y_i^* \mid x_i^v,x_i^t)
\]

多 token 答案使用平均 token loss：

\[
\mathcal{L}_i=-\frac{1}{T_i}\sum_{t=1}^{T_i}\log P_{\theta}(y_{i,t}^* \mid x_i^v,x_i^t,y_{i,<t}^*)
\]

## 4.4 Hidden-state 梯度归因

对第 \(l\) 层 hidden states \(h_{i,l}\) 计算梯度：

\[
g_{i,l}^{h}=\nabla_{h_{i,l}}\mathcal{L}_i
\]

使用 gradient × activation 得分：

\[
A_{i,l}=
\frac{1}{|\Omega_{i,l}|}
\sum_{j\in \Omega_{i,l}}
\left|
h_{i,l,j}\odot g_{i,l,j}^{h}
\right|_1
\]

其中：

| 符号 | 含义 |
|---|---|
| \(\Omega_{i,l}\) | 需要聚合的 token 集合 |
| \(j\) | token index |
| \(\odot\) | 逐元素乘法 |
| \(|\cdot|_1\) | L1 求和 |

## 4.5 Token 集合选择

根据任务选择 \(\Omega_{i,l}\)。

### 语言模型编辑

通常选择 subject token、最后一个 subject token 或最后一个 prompt token：

\[
\Omega_{i,l}=\{\text{subject-final token}\}
\]

或：

\[
\Omega_{i,l}=\{\text{last prompt token}\}
\]

### 视觉语言模型编辑

如果目标是视觉 adapter 插入层，推荐选择 visual tokens：

\[
\Omega_{i,l}=\{\text{visual tokens}\}
\]

如果目标是文本 decoder 层编辑，可以选择最后一个 prompt token：

\[
\Omega_{i,l}=\{\text{last prompt token}\}
\]

## 4.6 层得分聚合

\[
S_{\text{LGA}}(l)=\frac{1}{N}\sum_{i=1}^{N}A_{i,l}
\]

也可以使用梯度范数版本：

\[
S_{\text{LGA-grad}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{1}{|\Omega_{i,l}|}
\sum_{j\in \Omega_{i,l}}
\left\|\nabla_{h_{i,l,j}}\mathcal{L}_i\right\|_2
\]

默认推荐使用 gradient × activation：

\[
S_{\text{LGA}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{1}{|\Omega_{i,l}|}
\sum_{j\in \Omega_{i,l}}
\left|
h_{i,l,j}\odot\nabla_{h_{i,l,j}}\mathcal{L}_i
\right|_1
\]

## 4.7 候选层计算

\[
\mathcal{C}_{\text{LGA}}=\operatorname{TopK}_{l}(S_{\text{LGA}}(l))
\]

## 4.8 输出格式

```json
{
  "method": "GoldenLayer-LGA",
  "score_type": "hidden_gradient_times_activation",
  "token_scope": "visual_tokens",
  "target": "full_alt_sequence_loss",
  "top_k": 5,
  "candidate_layers": [17, 16, 18, 19, 20]
}
```

---

# 5. Perturb-KL-Pre

## 5.1 方法名称

**Perturb-KL-Pre**  
中文可写作：KL 扰动敏感区前置插入法。

## 5.2 方法思想

该方法通过对不同层的 hidden states 加噪声，观察输出分布变化。如果扰动某层导致输出分布变化大，说明该层对最终预测敏感。对于 adapter 插入任务，不直接选择敏感峰值层，而是选择敏感区域之前的层，使编辑信号能进入后续敏感层。

## 5.3 原始输出分布

对第 \(i\) 个样本正常 forward，得到原始输出分布：

\[
p_i(y)=P_{\theta}(y \mid x_i^v,x_i^t)
\]

默认取最后一个 prompt token 后的 next-token 分布。  
如果目标答案很长，也可使用目标答案 token 序列上的平均 KL。

## 5.4 扰动方式

对第 \(l\) 层 hidden states 加高斯噪声：

\[
\tilde{h}_{i,l}=h_{i,l}+\epsilon_{i,l}^{\alpha}
\]

其中：

\[
\epsilon_{i,l}^{\alpha}\sim
\mathcal{N}\left(0,(\alpha \cdot \sigma_{i,l})^2\right)
\]

\[
\sigma_{i,l}=\operatorname{Std}(h_{i,l})
\]

对于视觉语言模型，若定位 visual adapter 插入层，推荐只扰动 visual tokens：

\[
\tilde{h}_{i,l}^{v}=h_{i,l}^{v}+\epsilon_{i,l}^{\alpha}
\]

## 5.5 噪声强度

不要只使用单一噪声。默认使用：

\[
\mathcal{A}=\{0.1,0.5,1,3\}
\]

其中：

| \(\alpha\) | 含义 |
|---|---|
| 0.1 | 轻微扰动 |
| 0.5 | 中等偏小扰动 |
| 1 | 标准尺度扰动 |
| 3 | 强扰动，接近 VisEdit 噪声设定思想 |

## 5.6 KL 层敏感性得分

扰动第 \(l\) 层后，得到输出分布：

\[
p_{i,l}^{\alpha}(y)=P_{\theta}(y \mid \tilde{h}_{i,l},x_i^v,x_i^t)
\]

计算 KL 散度：

\[
D_{i,l}^{\alpha}=D_{\mathrm{KL}}\left(p_i(y)\Vert p_{i,l}^{\alpha}(y)\right)
\]

其中：

\[
D_{\mathrm{KL}}(p\Vert q)=\sum_{y}p(y)\log\frac{p(y)}{q(y)}
\]

数据集平均得分：

\[
S_{\text{KL}}^{\alpha}(l)=\frac{1}{N}\sum_{i=1}^{N}D_{i,l}^{\alpha}
\]

多噪声强度稳健得分：

\[
S_{\text{KL}}^{\text{robust}}(l)=
\frac{1}{|\mathcal{A}|}
\sum_{\alpha\in\mathcal{A}}
\operatorname{Norm}\left(S_{\text{KL}}^{\alpha}(l)\right)
\]

## 5.7 敏感区识别

对 \(S_{\text{KL}}^{\text{robust}}(l)\) 做三层平滑：

\[
\tilde{S}_{\text{KL}}(l)=
\frac{S_{\text{KL}}^{\text{robust}}(l-1)+S_{\text{KL}}^{\text{robust}}(l)+S_{\text{KL}}^{\text{robust}}(l+1)}{3}
\]

计算：

\[
\mu_{\text{KL}}=\operatorname{Mean}_{l}(\tilde{S}_{\text{KL}}(l))
\]

\[
\sigma_{\text{KL}}=\operatorname{Std}_{l}(\tilde{S}_{\text{KL}}(l))
\]

定义敏感层集合：

\[
\mathcal{H}_{\text{KL}}=\{l \mid \tilde{S}_{\text{KL}}(l)\ge \mu_{\text{KL}}+\lambda\sigma_{\text{KL}}\}
\]

默认：

\[
\lambda=0.5
\]

取最长连续敏感区：

\[
[s_{\text{KL}},e_{\text{KL}}]
\]

## 5.8 前置候选层计算

Perturb-KL-Pre 选择敏感区之前的层：

\[
\mathcal{C}_{\text{KL-pre}}=
\{s_{\text{KL}}-1,\ s_{\text{KL}}-2,\ \dots,\ s_{\text{KL}}-K\}
\]

删除越界层：

\[
0 \le l < L
\]

并按距离敏感区起点从近到远排序。

## 5.9 Direct 版本，作为消融

如果需要对比“敏感层本身是否适合编辑”，可以额外定义：

\[
\mathcal{C}_{\text{KL-direct}}=\operatorname{TopK}_{l}\left(S_{\text{KL}}^{\text{robust}}(l)\right)
\]

正式主方法建议使用 `Perturb-KL-Pre`，Direct 只作为消融。

## 5.10 输出格式

```json
{
  "method": "Perturb-KL-Pre",
  "noise_scales": [0.1, 0.5, 1, 3],
  "perturb_scope": "visual_tokens",
  "lambda": 0.5,
  "sensitive_region": [20, 30],
  "top_k": 5,
  "candidate_layers": [19, 18, 17, 16, 15]
}
```

---

# 6. Ours

## 6.1 方法名称

**Ours: Request-only Visual Gradient Delta-LGA**  
中文可写作：请求侧视觉梯度差分层定位法。

## 6.2 方法思想

该方法面向视觉语言模型编辑，重点分析“输入图像视觉 token 在各个文本解码层中对新旧知识答案的梯度作用”。与贡献度柱状图不同，本方法直接围绕编辑目标计算 hidden-state 梯度，并在视觉 token 区间聚合层级分数。

核心判断是：适合编辑的层应该同时满足：

1. 对新知识 `alt` 有较强可编辑梯度。
2. 与旧知识 `pred` 的梯度方向存在差异，便于替换旧答案。
3. 视觉 token 的梯度信号足够强，说明该层仍保留可利用的视觉证据。
4. 层位置不过度靠后，避免只在最终输出附近做表面修正。

## 6.3 公式

对第 \(i\) 个样本、第 \(l\) 层视觉 token hidden states \(h^v_{i,l}\)，分别计算新知识和旧知识 loss：

\[
\mathcal{L}^{alt}_i=-\log p_i(y_i^{alt})
\]

\[
\mathcal{L}^{pred}_i=-\log p_i(y_i^{pred})
\]

对应视觉 token 梯度为：

\[
g^{alt}_{i,l}=\nabla_{h^v_{i,l}}\mathcal{L}^{alt}_i
\]

\[
g^{pred}_{i,l}=\nabla_{h^v_{i,l}}\mathcal{L}^{pred}_i
\]

视觉 token 区间聚合后计算：

\[
S^v_{\text{dot}}(l)=
\frac{1}{N}\sum_i
\left\langle
\bar{g}^{alt}_{i,l},
\bar{g}^{pred}_{i,l}
\right\rangle
\]

\[
S^v_{\text{cos}}(l)=
\frac{1}{N}\sum_i
\cos\left(
\bar{g}^{alt}_{i,l},
\bar{g}^{pred}_{i,l}
\right)
\]

\[
S^v_{\text{new-norm}}(l)=
\frac{1}{N}\sum_i
\left\Vert
\bar{g}^{alt}_{i,l}
\right\Vert_2
\]

其中 \(\bar{g}\) 表示对视觉 token 区间求平均后的梯度向量。

主排序分数使用视觉相关编辑潜力：

\[
S_{\text{ours}}(l)=
\max(0,-S^v_{\text{cos}}(l))
\cdot
S^v_{\text{new-norm}}(l)
\cdot
\left(\frac{l+1}{L}\right)^2
\]

其中 \(\max(0,-S^v_{\text{cos}}(l))\) 鼓励新旧知识梯度方向冲突，\(S^v_{\text{new-norm}}(l)\) 保证新知识梯度强度，\(\left(\frac{l+1}{L}\right)^2\) 是深度权重。若实验目标是 visual adapter 前置插入，不直接使用峰值层，而是先识别高分区间再取前置层。

## 6.4 候选层计算

Direct 版本：

\[
\mathcal{C}_{\text{ours}}=\operatorname{TopK}_{l}\left(S_{\text{ours}}(l)\right)
\]

Pre 版本：

\[
\mathcal{C}_{\text{ours-pre}}=\{s_{\text{ours}}-1,\dots,s_{\text{ours}}-K\}
\]

其中 \(s_{\text{ours}}\) 是 \(S_{\text{ours}}(l)\) 平滑后高分区间的起始层。主实验建议报告：

```text
Ours-Direct
Ours-Pre
```

如果真实编辑模块挂载在 decoder block 前，使用 `Ours-Pre` 作为主结果；如果编辑方法本身直接修改目标层参数，可以同时报告 `Ours-Direct`。

## 6.5 输出格式

```json
{
  "method": "Ours-Pre",
  "score_type": "visual_gradient_delta_lga",
  "target": "alt_vs_pred",
  "token_scope": "visual_tokens",
  "rank_metric": "negative_cosine_times_new_norm_depth2",
  "top_k": 5,
  "candidate_layers": [19, 18, 17, 16, 15]
}
```

---

# 7. Oracle Sweep

## 7.1 方法名称

**Oracle Sweep**  
中文可写作：真实编辑性能逐层扫描上界。

## 7.2 方法思想

Oracle Sweep 不是一种无需训练的定位方法，而是用来评价其他定位方法是否准确的真实上界。它对候选层逐层训练 adapter 或执行编辑，然后根据真实编辑指标排序。

## 7.3 候选层集合

为了节省成本，可以只训练所有方法推荐层的并集：

\[
\mathcal{U}=\bigcup_{m}\mathcal{C}_{m}
\]

其中 \(m\) 表示不同定位方法。

如果资源允许，也可以训练所有层：

\[
\mathcal{U}=\{0,1,\dots,L-1\}
\]

## 7.4 真实编辑性能

对每个层 \(l\in\mathcal{U}\)，使用完全相同配置训练并评测，得到：

\[
R(l)=\operatorname{Rel}(l)
\]

\[
G_T(l)=\operatorname{TGen}(l)
\]

\[
G_M(l)=\operatorname{MGen}(l)
\]

\[
Loc_T(l)=\operatorname{TLoc}(l)
\]

\[
Loc_M(l)=\operatorname{MLoc}(l)
\]

综合指标：

\[
A(l)=\frac{R(l)+G_T(l)+G_M(l)+Loc_T(l)+Loc_M(l)}{5}
\]

其中 \(A(l)\) 即 `Average`。

## 7.5 Oracle 最优层

\[
l^*=\arg\max_{l\in\mathcal{U}}A(l)
\]

Oracle Top-K：

\[
\mathcal{C}_{\text{oracle}}=\operatorname{TopK}_{l\in\mathcal{U}}\left(A(l)\right)
\]

## 7.6 定位方法准确性评价

对于某个定位方法 \(m\)，其候选层为：

\[
\mathcal{C}_{m}
\]

### Best-of-TopK

\[
\operatorname{BestTopK}(m)=\max_{l\in \mathcal{C}_{m}}A(l)
\]

越大越好。

### Regret

\[
\operatorname{Regret}(m)=A(l^*)-\max_{l\in \mathcal{C}_{m}}A(l)
\]

越小越好。

### Hit@K

\[
\operatorname{Hit@K}(m)=\mathbb{I}\left[l^*\in \mathcal{C}_{m}\right]
\]

其中 \(\mathbb{I}[\cdot]\) 是指示函数，条件成立为 1，否则为 0。

### Rank Correlation

如果方法 \(m\) 可以给所有层输出得分 \(S_m(l)\)，可计算其排序与真实编辑性能 \(A(l)\) 排序之间的相关性：

\[
\rho_{\text{Spearman}}=\operatorname{SpearmanRankCorr}\left(S_m(l), A(l)\right)
\]

或：

\[
\tau_{\text{Kendall}}=\operatorname{KendallTau}\left(S_m(l), A(l)\right)
\]

## 7.7 输出格式

```json
{
  "method": "Oracle Sweep",
  "trained_layers": [15, 16, 17, 18, 19, 20, 21],
  "metric": "Average",
  "oracle_best_layer": 17,
  "oracle_top_k": [17, 19, 16, 10, 15]
}
```

---

# 8. 推荐统一实验流程

## 8.1 阶段一：计算候选层

对每个数据集、每个模型分别计算：

```text
Middle-layer Prior
VisEdit-Contrib-Pre-Alt
VisEdit-Contrib-Pre-Delta
VisEdit-Contrib-Direct-Alt, as ablation
VisEdit-Contrib-Direct-Pred / ModelPred, as analysis
SaLEM
GoldenLayer / LGA
Perturb-KL-Pre
Ours-Pre
Ours-Direct, as ablation
```

每种方法输出：

```text
Top-K candidate layers
Layer scores
Ranking
Method hyperparameters
```

## 8.2 阶段二：合并候选层

\[
\mathcal{U}=
\mathcal{C}_{\text{mid}}
\cup
\mathcal{C}_{\text{contrib-pre}}
\cup
\mathcal{C}_{\text{SaLEM}}
\cup
\mathcal{C}_{\text{LGA}}
\cup
\mathcal{C}_{\text{KL-pre}}
\cup
\mathcal{C}_{\text{ours}}
\]

去重后得到需要真实训练的层集合。

## 8.3 阶段三：真实编辑训练

对每个 \(l\in\mathcal{U}\)，使用相同配置训练：

```text
same dataset
same model
same adapter structure
same learning rate
same batch size
same epoch / iteration
same checkpoint selection rule
same evaluation set
```

## 8.4 阶段四：真实编辑评测

记录每个层：

```text
Rel
T-Gen
M-Gen
T-Loc
M-Loc
Average
```

## 8.5 阶段五：比较定位准确性

对每种定位方法报告：

```text
Candidate Layers
Best-of-TopK Average
Regret
Hit@K
Spearman / Kendall, if full ranking exists
```

Top-3 和 Top-5 必须分开报告：

\[
\operatorname{Best@3}(m)=\max_{l\in \mathcal{C}_{m,3}}A(l)
\]

\[
\operatorname{Best@5}(m)=\max_{l\in \mathcal{C}_{m,5}}A(l)
\]

\[
\operatorname{Regret@K}(m)=A(l^*)-\operatorname{Best@K}(m)
\]

\[
\operatorname{Hit@K}(m)=\mathbb{I}\left[l^*\in \mathcal{C}_{m,K}\right]
\]

如果真实编辑只训练候选层并集 \(\mathcal{U}\)，则 \(l^*\) 是该并集中的 oracle 最优层；如果训练了所有层，则 \(l^*\) 是全层 oracle 最优层。论文主表需要明确写清楚是哪一种 oracle。

## 8.6 当前已有实验结果如何接入

当前已经完成的贡献度实验可以直接作为 `VisEdit-Contrib-*` 方法的输入。

EVQA / pilot500：

```text
downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822
downloads/evqa_module_contribution/evqa_pilot500_module_contribution_model_pred_20260606_193500
downloads/evqa_module_contribution/blip2
```

MMKE visual/entity：

```text
downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt
downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/pred
downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt
downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/pred
```

每个模型目录中的核心输入文件是：

```text
contribution_layer.csv
contribution_rank.csv
summary.json
config.json
```

从贡献度结果生成候选层时，默认读取 `contribution_layer.csv` 的 `score_positive`：

```text
Direct-Alt:
  sort visual/alt/{model}/contribution_layer.csv by score_positive desc

Direct-Pred:
  sort visual/pred/{model}/contribution_layer.csv by score_positive desc

Direct-Delta:
  join alt and pred by layer
  score_delta = score_positive_alt - score_positive_pred
  sort by score_delta desc

Pre-Alt / Pre-Pred / Pre-Delta:
  first identify high-score region from the corresponding score curve
  then return K valid layers before the region start
```

`entity` 子任务同理，只把路径中的 `visual` 改为 `entity`。

## 8.7 候选层标准输出文件

每次候选层计算建议输出三个文件。

`candidate_layers_topk.csv`：

| column | 含义 |
|---|---|
| `dataset` | 数据集名，例如 `EVQA` / `MMKE` |
| `subset` | 子任务或 split，例如 `pilot500` / `visual` / `entity` |
| `model` | 模型名 |
| `method` | 定位方法名 |
| `variant` | `direct` / `pre` / `delta` / `prior` / `oracle` |
| `key_mode` | `alt` / `pred` / `model_pred` / `alt-pred` |
| `rank_metric` | 排序指标 |
| `top_k` | 3 或 5 |
| `rank` | Top-K 内排序 |
| `layer` | 候选编辑层 |
| `score` | 该层定位分数 |
| `score_source_file` | 分数来源文件 |

`candidate_layers_summary.json`：

```json
{
  "dataset": "MMKE",
  "subset": "entity",
  "model": "llava-v1.5-7b",
  "methods": ["Middle-layer Prior", "VisEdit-Contrib-Pre-Alt", "VisEdit-Contrib-Pre-Delta"],
  "top_k_values": [3, 5],
  "layer_space": "text_decoder",
  "notes": "candidate layers are adapter insertion layers"
}
```

`candidate_union_for_edit.csv`：

```text
dataset,subset,model,layer,selected_by_methods
MMKE,entity,llava-v1.5-7b,18,VisEdit-Contrib-Pre-Alt|Ours-Pre
```

真实编辑训练只读取 `candidate_union_for_edit.csv`，避免每种方法重复训练同一个层。

## 8.8 真实编辑验证协议

真实编辑验证分两步：

1. 对所有方法的 Top-3 并集训练一次，得到低预算比较。
2. 对所有方法的 Top-5 并集训练一次，得到较高预算比较。

如果 Top-3 并集已经包含某个 Top-5 层，不重复训练；最终评价时按方法自己的 Top-K 集合回填真实编辑结果。

每个候选层必须记录：

```text
Rel
T-Gen
M-Gen
T-Loc
M-Loc
Average
best_checkpoint
training_steps
random_seed
```

跨模型、跨数据集汇总时，主结果使用 macro-average，即先对每个 `dataset × model` 得到一个方法得分，再对这些得分平均。不要用所有样本或所有层直接 micro-average，否则层数多的模型或样本多的数据集会主导结论。

---

# 9. 建议表格模板

## 9.1 候选层表

| Dataset | Model | Method | Top-1 | Top-3 | Top-5 |
|---|---|---|---:|---|---|
| E-VQA | BLIP2-OPT | Middle-layer Prior | 17 | 17,18,16 | 17,18,16,19,15 |
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Pre-Alt | 19 | 19,18,17 | 19,18,17,16,15 |
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Pre-Delta | - | - | - |
| E-VQA | BLIP2-OPT | SaLEM | - | - | - |
| E-VQA | BLIP2-OPT | GoldenLayer/LGA | - | - | - |
| E-VQA | BLIP2-OPT | Perturb-KL-Pre | - | - | - |
| E-VQA | BLIP2-OPT | Ours-Pre | - | - | - |

## 9.2 定位准确性表

| Dataset | Model | Method | Candidate Layers | Best-of-TopK | Regret | Hit@K |
|---|---|---|---|---:|---:|---:|
| E-VQA | BLIP2-OPT | Middle-layer Prior | L17,L18,L16 | - | - | - |
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Pre-Alt | L19,L18,L17 | - | - | - |
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Pre-Delta | - | - | - | - |
| E-VQA | BLIP2-OPT | SaLEM | - | - | - | - |
| E-VQA | BLIP2-OPT | GoldenLayer/LGA | - | - | - | - |
| E-VQA | BLIP2-OPT | Perturb-KL-Pre | - | - | - | - |
| E-VQA | BLIP2-OPT | Ours-Pre | - | - | - | - |
| E-VQA | BLIP2-OPT | Oracle Sweep | - | - | 0 | 1 |

---

# 10. 默认超参数汇总

| 方法 | 超参数 | 默认值 |
|---|---|---|
| Middle-layer Prior | \(\rho\) | 0.55 |
| VisEdit-Contrib-Pre | \(\lambda\) | 0.5 |
| VisEdit-Contrib-Pre | smoothing window | 3 |
| VisEdit-Contrib-Pre | key token | `alt_first_token` / `pred_first_token` / `model_pred_first_token` |
| VisEdit-Contrib-Delta | \(\gamma\) | 1.0 |
| VisEdit-Contrib-* | primary rank metric | `score_positive` |
| SaLEM | gradient norm | L2 / sqrt(parameter count) |
| GoldenLayer/LGA | attribution | gradient × activation |
| GoldenLayer/LGA | token scope for VLM | visual tokens |
| Perturb-KL-Pre | noise scales | 0.1, 0.5, 1, 3 |
| Perturb-KL-Pre | perturb scope for VLM | visual tokens |
| Perturb-KL-Pre | \(\lambda\) | 0.5 |
| Ours | target contrast | `alt` vs `pred` |
| Ours | token scope | visual tokens |
| Ours | rank metric | negative cosine × new norm × depth weight |
| Oracle Sweep | metric | Average |

---

# 11. 注意事项

1. 对于 VLM，不同模型的 visual token 插入位置不同，需要先确认 hook 到的是哪一层、哪个 token 范围。
2. 对于 BLIP2-OPT、MiniGPT-4 这类 Q-Former 架构，要区分 Q-Former 层和语言解码器层。
3. 对于 LLaVA/Qwen2.5-VL/PaliGemma 等 decoder-only 风格模型，要统一候选层编号。
4. 如果目标是 visual adapter 插入层，建议所有方法都输出“插入层候选”，不要混合“贡献峰值层”和“插入层”。
5. 对于 VisEdit-Contrib-Pre 和 Perturb-KL-Pre，主结果使用 Pre 版本；Direct 版本可作为消融。
6. 如果某方法输出的是高贡献区或敏感区，而不是单个层，统一转换为该区间之前的 \(K\) 个层。
7. 如果某方法输出的候选层重复或越界，需要去重并删除非法层。
8. 所有方法必须在同一数据集、同一模型、同一 tokenization 设置下计算候选层。
9. 最终结论必须基于 Oracle Sweep 或候选层真实编辑评测，而不是只基于定位分数。
10. Qwen2.5-VL 使用动态分辨率，做 LGA、visual token 梯度或 adapter 编辑实验时必须固定输入分辨率，例如统一 448×448，保证跨样本视觉 token 数和 `visual_token_start/end` 一致。
11. 如果某个模型的贡献度总量极低，例如 `score_positive` 全层接近 0，需要把该方法标记为 low-confidence，并使用中层先验或梯度方法作为 fallback 对照。
12. `alt`、`pred`、`model_pred` 不能混用在同一个主排序里。论文图表必须写清楚每个排序是按新知识贡献、旧知识贡献、模型自身输出贡献，还是新旧差分贡献排序。
13. BLIP2、InstructBLIP、MiniGPT-4 等压缩型模型需要说明候选层是 Q-Former 层还是文本解码器层；LLaVA、Qwen2.5-VL、PaliGemma、SmolVLM 等非压缩或轻压缩模型需要说明候选层对应 decoder block 的编号。

---

# 12. 推荐最终结论写法

可以在论文中使用如下逻辑：

> 本文将编辑层定位视为候选层推荐问题，而不是直接假设知识存储层或预测贡献层等同于最优编辑层。对于每种定位方法，首先计算其 Top-K 候选编辑层；随后在相同训练配置下对这些候选层进行真实编辑训练，并以 Reliability、Generality、Locality 和 Average 指标评价候选层的实际编辑效果。该设计能够更公平地比较不同定位方法的有效性，并避免仅凭归因分数或梯度分数直接判断编辑层优劣。

---

# 13. 参考文献标注建议

正式论文中可将方法来源写为：

- ROME / MEMIT 系列：中层 MLP 编辑先验与 causal tracing 思路。
- VisEdit：贡献度归因、噪声扰动和高贡献区前置插入策略。
- SaLEM：基于 layer-wise saliency map 的自动层选择。
- GoldenLayer / LGA：基于 proxy dataset 和 gradient attribution 的 golden layer 估计。
- Does Localization Inform Editing?：说明知识定位结果不必然等同于最佳编辑层。
