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

本轮主实验不再统一规定“Pre 一定是主版本、Direct 一定是消融”。不同定位方法按其原始方法语义选择主候选层：

| 方法 | 主候选规则 | 原因 |
|---|---|---|
| Middle-layer Prior | 中层直接 Top-K | 中层经验先验 |
| VisEdit-Contrib-Pre | 高贡献区之前 Top-K | 原文明确采用前置插入 |
| SaLEM-based | 显著性最高 Top-K | 原方法直接选显著层 |
| LGA | 梯度内积最高 Top-K | 原方法直接选黄金层 |
| Perturb-KL-Direct | KL 最大 Top-K | 标准扰动敏感层定位 |
| Ours | 按本文公式输出 Top-K | 主方法 |
| Oracle Sweep | 逐层真实训练排序 | 评价上界 |

附加/消融/诊断变体单独报告，不与主方法混在同一列：

| 附加/消融/诊断变体 | 作用 |
|---|---|
| VisEdit-Contrib-Pre-Delta | 检验新旧贡献差分的前置层是否比 `VisEdit-Contrib-Pre-Alt` 更适合编辑 |
| VisEdit-Contrib-Direct-Pred / ModelPred | 分析旧答案路径或模型自身输出路径的贡献峰值，不作为新知识主候选 |
| GoldenLayer-LGA-Pre-AltPred | 检验 LGA 高分区前置层是否更适合 adapter 插入 |
| SaLEM-Delta | 检验新旧参数梯度显著性差分是否比 `SaLEM-Alt` 更稳定 |
| Perturb-KL-Pre | 检验 KL 敏感区之前是否更适合挂 adapter |
| Ours-Direct | 检验本文分数峰值层本身是否适合直接编辑 |

如果某个方法输出的是“区间”而不是单层排序，只有在方法名明确带 `Pre` 时才转换为该区间之前的 \(K\) 个层；否则按该方法的主分数直接 Top-K。

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
raw_rank
raw_layer
raw_candidate_layers
clean_rank
clean_layer
clean_candidate_layers
dedupe_or_filter_reason
```

其中 `raw_*` 字段保留方法原始输出，不做去重、不删越界层；`clean_*` 字段保留用于真实训练和并集汇总的处理后结果。若原始候选层重复、越界或被 fallback 补齐，必须在 `dedupe_or_filter_reason` 中说明，不能只保留处理后结果。

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

贡献度方法的主结果与附加/消融/诊断结果按下表区分；主实验只使用 `VisEdit-Contrib-Pre-Alt`，其余变体单独成表：

| 方法名 | 排序分数 | 候选层含义 | 推荐用途 |
|---|---|---|---|
| `VisEdit-Contrib-Direct-Alt` | \(S_{\text{alt}}(l)\) | 目标答案贡献峰值层 | 诊断 / 消融 |
| `VisEdit-Contrib-Pre-Alt` | \(S_{\text{alt}}(l)\) 的高贡献区前置层 | 目标答案高贡献区之前的编辑插入层 | 主比较 |
| `VisEdit-Contrib-Direct-Pred` | \(S_{\text{pred}}(l)\) | 旧答案贡献峰值层 | 旧知识路径分析 |
| `VisEdit-Contrib-Pre-Pred` | \(S_{\text{pred}}(l)\) 的高贡献区前置层 | 旧答案路径前置层 | 抑制编辑消融 |
| `VisEdit-Contrib-Direct-Delta` | \(S_{\Delta}(l)\) | 新旧贡献差分峰值层 | 诊断 / 消融 |
| `VisEdit-Contrib-Pre-Delta` | \(S_{\Delta}(l)\) 的高贡献区前置层 | 避开旧答案支持的新知识插入层 | 附加 / 消融 |
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

## 2.10 后续 SaLEM / LGA / Perturb-KL 的统一计算范围

后续第 3、4、5 节的三个定位方法，都按同一套任务矩阵计算候选层：

| 维度 | 取值 |
|---|---|
| 数据集 / 子任务 | `EVQA / pilot500`、`MMKE / visual`、`MMKE / entity` |
| 模型 | `BLIP2-OPT-2.7B`、`InstructBLIP-Vicuna-7B`、`MiniGPT-4-Vicuna-7B`、`LLaVA-v1.5-7B`、`Qwen2.5-VL-3B`、`PaliGemma-3B`、`SmolVLM-Instruct-1.7B` |
| 层空间 | 默认使用 `text_decoder` 层，层编号为 0-indexed |
| 输出 K | 必须同时输出 `Top-3` 和 `Top-5` |
| 主目标字段 | `alt`，表示新知识 / 目标答案 |
| 旧知识字段 | `pred`，表示旧知识 / 原答案 |

对 BLIP2、InstructBLIP、MiniGPT-4 这类压缩视觉输入模型，默认候选层仍然指文本解码器层，不指 Q-Former 层；如果额外计算 Q-Former 层，必须把 `layer_space` 写成 `qformer`，不要和 decoder 层混在同一个排序里。

对 LLaVA、Qwen2.5-VL、PaliGemma、SmolVLM 这类非压缩或轻压缩模型，默认候选层对应 decoder block。若方法需要 visual tokens，必须记录 `visual_token_start`、`visual_token_end`、`visual_token_count`；Qwen2.5-VL 必须固定输入分辨率后再计算，否则 visual token 数会随图片尺寸变化。

每种方法最终都要落成同一张候选层表：

```text
dataset,subset,model,method,variant,key_mode,layer_space,score_space,target_layer_type,rank_metric,top_k,rank,layer,score,score_source_file,fallback_reason
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

L2 形式可以作为辅助分数保存，但本轮候选层主排序使用 SaLEM 公式文件中推荐的“每层参数梯度绝对值均值”，即 `mean(abs(grad))`，避免大参数层仅因为参数量大而占优。

\[
S_{\text{SaLEM-L2}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{\|\nabla_{\theta_l}\mathcal{L}_i\|_2}{\sqrt{|\theta_l|}}
\]

## 3.4.1 本实验采用的 SaLEM 主公式

令 \(W_l\) 表示第 \(l\) 个 decoder block 中用于编辑层比较的参数集合。默认取 MLP / FFN 参数；如果某个模型的编辑方法明确作用于 attention 或 whole block，必须额外记录 `target_layer_type=attn` 或 `target_layer_type=block_all`，不能和 MLP 排序混用。

对新知识 `alt`：

\[
\mathcal{L}^{alt}_i=
-\frac{1}{T^{alt}_i}\sum_{t=1}^{T^{alt}_i}
\log P_{\theta}(y^{alt}_{i,t}\mid x_i^v,x_i^t,y^{alt}_{i,<t})
\]

SaLEM 层显著性主分数为：

\[
S_{\text{SaLEM-Alt}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\operatorname{mean}_{w\in W_l}
\left|
\frac{\partial \mathcal{L}^{alt}_i}{\partial w}
\right|
\]

也就是：

\[
S_{\text{SaLEM-Alt}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{1}{|W_l|}
\sum_{w\in W_l}
\left|
\nabla_{w}\mathcal{L}^{alt}_i
\right|
\]

如果要分析旧知识路径，可同样计算：

\[
S_{\text{SaLEM-Pred}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\operatorname{mean}_{w\in W_l}
\left|
\frac{\partial \mathcal{L}^{pred}_i}{\partial w}
\right|
\]

其中 `pred` 是旧知识字段。正式候选层主结果使用 `SaLEM-Alt`；`SaLEM-Pred` 只用于旧知识敏感层分析。

## 3.5 候选层计算

\[
\mathcal{C}_{\text{SaLEM}}=\operatorname{TopK}_{l}(S_{\text{SaLEM}}(l))
\]

本轮实验中具体写成：

\[
\mathcal{C}_{\text{SaLEM-Alt},K}
=
\operatorname{TopK}_{l}
\left(S_{\text{SaLEM-Alt}}(l)\right)
\]

用于 `Top-3`：

\[
\mathcal{C}_{\text{SaLEM-Alt},3}
=
\operatorname{Top3}_{l}
\left(S_{\text{SaLEM-Alt}}(l)\right)
\]

用于 `Top-5`：

\[
\mathcal{C}_{\text{SaLEM-Alt},5}
=
\operatorname{Top5}_{l}
\left(S_{\text{SaLEM-Alt}}(l)\right)
\]

SaLEM 是直接显著层选择方法，主版本不做 Pre 转换。也就是说，SaLEM 的候选层就是显著性分数最高的层本身，而不是显著区间之前的层。

如果需要补充一个“新旧差分”消融，可在同一模型、同一数据集内先对 `alt` 和 `pred` 分数做 min-max 归一化，再计算：

\[
S_{\text{SaLEM-Delta}}(l)
=
\operatorname{Norm}(S_{\text{SaLEM-Alt}}(l))
-
\operatorname{Norm}(S_{\text{SaLEM-Pred}}(l))
\]

然后：

\[
\mathcal{C}_{\text{SaLEM-Delta},K}
=
\operatorname{TopK}_{l}
\left(S_{\text{SaLEM-Delta}}(l)\right)
\]

`SaLEM-Delta` 只作为消融或补充分析，不能替代论文公式主结果。

## 3.6 实现注意事项

1. 对所有模型统一使用相同的目标 loss。
2. 如果比较 decoder 层，则 \(\theta_l\) 应对应第 \(l\) 个语言解码器 block。
3. 如果比较 visual adapter 插入层，也可以将 \(\theta_l\) 替换为第 \(l\) 层可挂载 adapter 的虚拟参数或 block 参数。
4. 为避免梯度显存过高，可以每次只保留每层梯度范数，不保存完整梯度。
5. 对多数据集比较时，每个数据集独立计算 \(S_{\text{SaLEM}}(l)\)。
6. 每个样本 backward 后必须立即读取每层分数并 `zero_grad`，不要跨样本累积完整梯度张量。
7. 分数只在同一 `dataset × subset × model × target_layer_type` 内排序，不做跨模型绝对值比较。

## 3.7 输出格式

```json
{
  "method": "SaLEM-Alt",
  "variant": "direct",
  "score_type": "mean_abs_parameter_gradient",
  "target_layer_type": "mlp_ffn",
  "key_mode": "alt",
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

本轮实验的 LGA 主公式使用 `原始LGA公式整理表.md` 中的 old/new 梯度内积形式：

\[
S_{\mathrm{LGA}}(l)
=
\sum_i
\left\langle
g^{l}_{old,i},
g^{l}_{new,i}
\right\rangle
\]

其中：

| LGA 符号 | 本实验字段 |
|---|---|
| \(g^{l}_{new,i}\) | `alt` 新知识 / 目标答案 loss 对第 \(l\) 层对象的梯度 |
| \(g^{l}_{old,i}\) | `pred` 旧知识 / 原答案 loss 对第 \(l\) 层对象的梯度 |

向量分解形式为：

\[
S_{\mathrm{LGA}}(l)
=
\sum_i
\left\|g^{l}_{old,i}\right\|
\cdot
\left\|g^{l}_{new,i}\right\|
\cdot
\cos\left(g^{l}_{old,i},g^{l}_{new,i}\right)
\]

因此 LGA 分数同时刻画三件事：旧知识梯度强度、新知识写入强度、以及新旧知识更新方向是否一致。

## 4.3 编辑目标 loss

同 SaLEM：

\[
\mathcal{L}_i=-\log P_{\theta}(y_i^* \mid x_i^v,x_i^t)
\]

多 token 答案使用平均 token loss：

\[
\mathcal{L}_i=-\frac{1}{T_i}\sum_{t=1}^{T_i}\log P_{\theta}(y_{i,t}^* \mid x_i^v,x_i^t,y_{i,<t}^*)
\]

在本轮 `pilot500 / MMKE-visual / MMKE-entity` 上，原始 LGA 必须同时计算新旧两个 loss：

\[
\mathcal{L}^{new}_i=\mathcal{L}^{alt}_i
=
-\frac{1}{T^{alt}_i}
\sum_{t=1}^{T^{alt}_i}
\log P_{\theta}(y^{alt}_{i,t}\mid x_i^v,x_i^t,y^{alt}_{i,<t})
\]

\[
\mathcal{L}^{old}_i=\mathcal{L}^{pred}_i
=
-\frac{1}{T^{pred}_i}
\sum_{t=1}^{T^{pred}_i}
\log P_{\theta}(y^{pred}_{i,t}\mid x_i^v,x_i^t,y^{pred}_{i,<t})
\]

如果某条样本缺少 `pred`，则该样本不能参与原始 `LGA-AltPred` 分数；不要用 `model_pred` 自动替代 `pred`，除非方法名明确写成 `LGA-AltModelPred`。

## 4.3.1 LGA 梯度对象与 score_space

令 \(z_{i,l}\) 表示第 \(i\) 个样本在第 \(l\) 层用于求梯度的对象。不同实现必须在输出里记录 `score_space`：

| `score_space` | \(z_{i,l}\) | 用途 |
|---|---|---|
| `hidden_visual_tokens` | decoder 第 \(l\) 层 visual token hidden states \(h^v_{i,l}\) | 本轮 VLM visual adapter 候选层主版本 |
| `hidden_last_prompt_token` | decoder 第 \(l\) 层最后一个 prompt token hidden state | 文本路径消融 |
| `param_mlp_ffn` | decoder 第 \(l\) 层 MLP / FFN 参数 \(W_l\) | 更贴近参数编辑的消融 |
| `param_block_all` | decoder 第 \(l\) 层整个 block 参数 | 高成本消融，不作默认 |

本轮七模型主结果推荐使用：

```text
method = GoldenLayer-LGA-Direct-AltPred
score_space = hidden_visual_tokens
key_mode = alt-pred
layer_space = text_decoder
```

对压缩型模型，`hidden_visual_tokens` 指进入文本解码器后的视觉查询 / 图像 token 表征，不指原始 vision encoder patch token。必须记录实际聚合的 token 数。

对每个样本、每个层分别计算：

\[
g^{l}_{new,i}
=
\nabla_{z_{i,l}}\mathcal{L}^{new}_i
\]

\[
g^{l}_{old,i}
=
\nabla_{z_{i,l}}\mathcal{L}^{old}_i
\]

如果 \(z_{i,l}\) 是 visual token hidden states，则先在 visual token 区间聚合为一个向量：

\[
\bar{g}^{l}_{new,i}
=
\frac{1}{|\mathcal{V}_i|}
\sum_{j\in \mathcal{V}_i}
g^{l}_{new,i,j}
\]

\[
\bar{g}^{l}_{old,i}
=
\frac{1}{|\mathcal{V}_i|}
\sum_{j\in \mathcal{V}_i}
g^{l}_{old,i,j}
\]

其中 \(\mathcal{V}_i\) 是样本 \(i\) 的 visual token index 集合。

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

先给出单目标 gradient × activation 辅助分数。注意：这一组不是本轮 `GoldenLayer / LGA` 主排序，只用于和单目标归因方法做消融。

\[
S_{\text{GxA-Alt}}(l)=\frac{1}{N}\sum_{i=1}^{N}A_{i,l}
\]

也可以使用梯度范数版本：

\[
S_{\text{GxA-grad}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{1}{|\Omega_{i,l}|}
\sum_{j\in \Omega_{i,l}}
\left\|\nabla_{h_{i,l,j}}\mathcal{L}_i\right\|_2
\]

如果只计算单目标归因，可以保存 gradient × activation 作为辅助分数：

\[
S_{\text{GxA-Alt}}(l)=
\frac{1}{N}\sum_{i=1}^{N}
\frac{1}{|\Omega_{i,l}|}
\sum_{j\in \Omega_{i,l}}
\left|
h_{i,l,j}\odot\nabla_{h_{i,l,j}}\mathcal{L}_i
\right|_1
\]

但本轮 `GoldenLayer / LGA` 主排序必须使用 old/new 梯度内积，而不是单目标 gradient × activation。

对 `hidden_visual_tokens` 主版本：

\[
D^{l}_{i}
=
\frac{
\left\langle
\bar{g}^{l}_{old,i},
\bar{g}^{l}_{new,i}
\right\rangle
}{
d_l
}
\]

其中 \(d_l\) 是梯度向量维度，用于避免不同 hidden size 或不同参数规模下的内积绝对值不可比。数据集级 LGA 分数为：

\[
S_{\text{LGA-dot}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
D^{l}_{i}
\]

同时建议保存以下辅助指标，方便解释排序来自强度还是方向：

\[
S_{\text{LGA-pos-dot}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\max(0,D^{l}_{i})
\]

\[
S_{\text{LGA-cos}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\cos\left(
\bar{g}^{l}_{old,i},
\bar{g}^{l}_{new,i}
\right)
\]

\[
S_{\text{LGA-new-norm}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
\bar{g}^{l}_{new,i}
\right\|_2
\]

\[
S_{\text{LGA-old-norm}}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
\bar{g}^{l}_{old,i}
\right\|_2
\]

主候选层排序使用 `score_lga_dot`，即 \(S_{\text{LGA-dot}}(l)\)。若某个模型的全层 `score_lga_dot` 几乎全为负，也仍然按从大到小排序；不要临时改用绝对值，否则会把“新旧知识方向冲突强”的层误当成 LGA 黄金层。

## 4.7 候选层计算

\[
\mathcal{C}_{\text{LGA}}=\operatorname{TopK}_{l}(S_{\text{LGA}}(l))
\]

本轮主结果写成：

\[
\mathcal{C}_{\text{LGA-Direct},K}
=
\operatorname{TopK}_{l}
\left(S_{\text{LGA-dot}}(l)\right)
\]

用于 `Top-3`：

\[
\mathcal{C}_{\text{LGA-Direct},3}
=
\operatorname{Top3}_{l}
\left(S_{\text{LGA-dot}}(l)\right)
\]

用于 `Top-5`：

\[
\mathcal{C}_{\text{LGA-Direct},5}
=
\operatorname{Top5}_{l}
\left(S_{\text{LGA-dot}}(l)\right)
\]

如果真实编辑模块是“插在高分区域之前”的 visual adapter，也可以额外输出 `GoldenLayer-LGA-Pre-AltPred`。Pre 版本不改变 LGA 分数，只改变候选层转换规则：

\[
\mathcal{H}_{\text{LGA}}
=
\{l\mid \tilde{S}_{\text{LGA-dot}}(l)\ge \mu+\lambda\sigma\}
\]

取最长连续高分区间 \([s_{\text{LGA}},e_{\text{LGA}}]\)，再取：

\[
\mathcal{C}_{\text{LGA-Pre},K}
=
\{s_{\text{LGA}}-1,\ s_{\text{LGA}}-2,\dots,s_{\text{LGA}}-K\}
\]

`GoldenLayer-LGA-Direct-AltPred` 是论文公式主结果；`GoldenLayer-LGA-Pre-AltPred` 只用于和 VisEdit-style adapter 前置插入规则对齐。

## 4.8 输出格式

```json
{
  "method": "GoldenLayer-LGA-Direct-AltPred",
  "variant": "direct",
  "score_type": "old_new_gradient_dot",
  "rank_metric": "score_lga_dot",
  "token_scope": "visual_tokens",
  "score_space": "hidden_visual_tokens",
  "key_mode": "alt-pred",
  "new_field": "alt",
  "old_field": "pred",
  "top_k": 5,
  "candidate_layers": [17, 16, 18, 19, 20]
}
```

---

# 5. Perturb-KL-Direct

## 5.1 方法名称

**Perturb-KL-Direct**  
中文可写作：KL 扰动敏感层直接定位法。

## 5.2 方法思想

该方法通过对不同层的 hidden states 加噪声，观察输出分布变化。如果扰动某层导致输出分布变化大，说明该层对当前输入输出分布更敏感，也更可能是有效编辑层。

本轮主扰动基线使用 `Perturb-KL-Direct`：直接按 robust KL 得分从高到低取 Top-K。`Perturb-KL-Pre` 只作为附加/消融，用来检验“敏感区之前是否更适合挂 adapter”，不作为主扰动基线。

## 5.3 原始输出分布

对第 \(i\) 个样本正常 forward，得到原始输出分布：

\[
p_i(y)=P_{\theta}(y \mid x_i^v,x_i^t)
\]

默认取最后一个 prompt token 后的 next-token 分布。  
如果目标答案很长，也可使用目标答案 token 序列上的平均 KL。

本轮实验建议同时支持两种 `key_mode`，但主表只选一种作为主结果：

| `key_mode` | KL 位置 | 含义 | 推荐用途 |
|---|---|---|---|
| `prompt_distribution` | 只使用 prompt 后 next-token 分布 | 不依赖 `alt/pred`，测层对当前输入输出分布的敏感性 | `Perturb-KL-Direct` 主版本 |
| `alt_sequence` | teacher forcing 下 `alt` token 位置的平均分布 | 测层对目标答案路径的分布敏感性 | 目标相关消融 |
| `pred_sequence` | teacher forcing 下 `pred` token 位置的平均分布 | 测层对旧答案路径的分布敏感性 | 旧知识路径分析 |

如果论文主表只放一个 Perturb-KL 方法，使用：

```text
method = Perturb-KL-Direct
key_mode = prompt_distribution
rank_metric = score_kl_robust
```

`alt_sequence` 和 `pred_sequence` 可以在附录或消融表中报告。

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

本轮 VLM 主版本使用：

```text
perturb_scope = visual_tokens
layer_space = text_decoder
```

如果某个 wrapper 暂时不能稳定拿到 visual token 区间，可以退化为：

```text
perturb_scope = all_prompt_tokens
fallback_reason = missing_visual_token_span
```

但退化结果必须单独标注，不能和 `visual_tokens` 主结果混为同一方法。

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

为了降低随机噪声造成的排序抖动，每个 \(\alpha\) 建议使用固定随机种子重复 \(R\) 次，默认：

\[
R=3
\]

例如：

```text
seeds = [2026, 2027, 2028]
```

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

带随机种子的完整版本为：

\[
D_{i,l}^{\alpha,r}
=
\frac{1}{|\mathcal{P}_i|}
\sum_{t\in \mathcal{P}_i}
D_{\mathrm{KL}}
\left(
p_{i,t}(y)
\Vert
p_{i,l,t}^{\alpha,r}(y)
\right)
\]

其中 \(\mathcal{P}_i\) 是 KL 计算位置集合：`prompt_distribution` 时只有 prompt 后第一个输出位置；`alt_sequence` / `pred_sequence` 时为对应答案 token 位置。

\[
S_{\text{KL}}^{\alpha,r}(l)
=
\frac{1}{N}
\sum_{i=1}^{N}
D_{i,l}^{\alpha,r}
\]

最终稳健分数：

\[
S_{\text{KL}}^{\text{robust}}(l)
=
\frac{1}{|\mathcal{A}|R}
\sum_{\alpha\in\mathcal{A}}
\sum_{r=1}^{R}
\operatorname{Norm}_{l}
\left(
S_{\text{KL}}^{\alpha,r}(l)
\right)
\]

其中 \(\operatorname{Norm}_{l}\) 表示在同一个 `dataset × subset × model × key_mode × perturb_scope` 内对所有层做 min-max 归一化。不要跨模型归一化。

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

如果 \(\mathcal{H}_{\text{KL}}\) 为空，使用 robust KL 得分最高的 \(q\) 个层构成近似敏感区，并取其中最小层作为起点：

\[
s_{\text{KL}}
=
\min
\operatorname{TopQ}_{l}
\left(S_{\text{KL}}^{\text{robust}}(l)\right)
\]

\[
q=\max(3,\lceil0.2L\rceil)
\]

敏感区只用于诊断和 `Perturb-KL-Pre` 消融。主扰动基线 `Perturb-KL-Direct` 不需要先识别敏感区，直接使用 robust KL 分数排序。

## 5.8 Direct 主候选层计算

`Perturb-KL-Direct` 直接选择 KL 扰动敏感性最高的层：

\[
\mathcal{C}_{\text{KL-direct},K}
=
\operatorname{TopK}_{l}
\left(S_{\text{KL}}^{\text{robust}}(l)\right)
\]

即：

\[
\mathcal{C}_{\text{KL-direct},3}
=
\operatorname{Top3}_{l}
\left(S_{\text{KL}}^{\text{robust}}(l)\right)
\]

\[
\mathcal{C}_{\text{KL-direct},5}
=
\operatorname{Top5}_{l}
\left(S_{\text{KL}}^{\text{robust}}(l)\right)
\]

该结果是本轮主扰动基线，写入主候选层表。

## 5.9 Pre 版本，作为附加/消融

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

如果因为 \(s_{\text{KL}}\) 太靠前导致前置候选层不足 \(K\) 个，按以下规则补齐：

1. 先保留所有合法前置层。
2. 再从 `Perturb-KL-Direct` 的得分排序中，选择尚未出现的最高分层补齐到 \(K\) 个。
3. 在输出中记录 `fallback_reason=pre_boundary_fill_with_direct`。

这样可以保证每个 `dataset × model × method` 都有完整的 Top-3 和 Top-5，同时不会静默丢层。

`Perturb-KL-Pre` 不作为本轮主扰动基线，只用于回答：如果真实编辑模块挂在敏感区之前，是否比直接扰动敏感层更适合 adapter 编辑。

## 5.10 输出格式

```json
{
  "method": "Perturb-KL-Direct",
  "variant": "direct",
  "key_mode": "prompt_distribution",
  "noise_scales": [0.1, 0.5, 1, 3],
  "seeds": [2026, 2027, 2028],
  "perturb_scope": "visual_tokens",
  "rank_metric": "score_kl_robust",
  "top_k": 5,
  "candidate_layers": [30, 25, 21, 20, 18],
  "sensitive_region_for_diagnosis": [20, 30],
  "ablation_pre_candidate_layers": [19, 18, 17, 16, 15]
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

其中 \(s_{\text{ours}}\) 是 \(S_{\text{ours}}(l)\) 平滑后高分区间的起始层。主实验使用：

```text
Ours-Pre
```

`Ours-Direct` 只作为附加/消融，用来检验本文分数峰值层本身是否适合直接编辑。

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

对每个数据集、每个模型分别计算。主实验候选层只使用以下方法：

```text
Middle-layer Prior
VisEdit-Contrib-Pre-Alt
SaLEM-Alt
GoldenLayer-LGA-Direct-AltPred
Perturb-KL-Direct
Ours-Pre
Oracle Sweep
```

附加/消融/诊断方法单独计算、单独成表，不进入主候选方法列：

```text
VisEdit-Contrib-Pre-Delta, as optional analysis
VisEdit-Contrib-Direct-Pred / ModelPred, as analysis
GoldenLayer-LGA-Pre-AltPred, as adapter-insertion alignment
SaLEM-Delta, as ablation
Perturb-KL-Pre, as ablation
Ours-Direct, as ablation
```

每种方法输出：

```text
Top-K candidate layers
Layer scores
Ranking
Method hyperparameters
```

## 8.2 阶段二：合并主实验候选层

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
\mathcal{C}_{\text{KL-direct}}
\cup
\mathcal{C}_{\text{ours}}
\]

去重后得到主实验需要真实训练的层集合。附加/消融/诊断方法若需要训练，另行生成：

\[
\mathcal{U}_{\text{ablation}}
=
\bigcup_m
\mathcal{C}_{m}^{\text{ablation}}
\]

其中 \(m\) 只包括 `VisEdit-Contrib-Pre-Delta`、`VisEdit-Contrib-Direct-Pred / ModelPred`、`GoldenLayer-LGA-Pre-AltPred`、`SaLEM-Delta`、`Perturb-KL-Pre`、`Ours-Direct` 等附加方法。不要把 \(\mathcal{U}_{\text{ablation}}\) 与主实验 \(\mathcal{U}\) 混成同一个主表结论。

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

每次候选层计算建议输出四类文件，原始候选层和处理后候选层都要保留。

`candidate_layers_raw.csv`：

| column | 含义 |
|---|---|
| `dataset` | 数据集名，例如 `EVQA` / `MMKE` |
| `subset` | 子任务或 split，例如 `pilot500` / `visual` / `entity` |
| `model` | 模型名 |
| `method` | 定位方法名 |
| `variant` | `direct` / `pre` / `delta` / `prior` / `oracle` |
| `top_k` | 3 或 5 |
| `raw_rank` | 原始 Top-K 内排序 |
| `raw_layer` | 方法原始输出层，允许重复或越界 |
| `raw_score` | 原始层定位分数 |
| `score_source_file` | 分数来源文件 |
| `raw_status` | `valid` / `duplicate` / `out_of_range` / `fallback_source` |

`candidate_layers_topk.csv`（清洗后，用于真实训练并集）：

| column | 含义 |
|---|---|
| `dataset` | 数据集名，例如 `EVQA` / `MMKE` |
| `subset` | 子任务或 split，例如 `pilot500` / `visual` / `entity` |
| `model` | 模型名 |
| `method` | 定位方法名 |
| `variant` | `direct` / `pre` / `delta` / `prior` / `oracle` |
| `key_mode` | `alt` / `pred` / `model_pred` / `alt-pred` / `prompt_distribution` |
| `layer_space` | `text_decoder` / `qformer` / `vision_encoder` / `adapter_insert` |
| `score_space` | `param_mlp_ffn` / `hidden_visual_tokens` / `hidden_last_prompt_token` / `visual_tokens_perturb` 等 |
| `target_layer_type` | `mlp_ffn` / `attn` / `block_all` / `hidden_state` |
| `rank_metric` | 排序指标 |
| `top_k` | 3 或 5 |
| `rank` | Top-K 内排序 |
| `layer` | 候选编辑层 |
| `score` | 该层定位分数 |
| `raw_candidate_layers` | 原始候选层列表，例如 `31,31,35,-1` |
| `clean_candidate_layers` | 去重和删除越界后的候选层列表 |
| `dedupe_or_filter_reason` | 处理说明，例如 `drop_duplicate_L31;drop_out_of_range_-1` |
| `score_source_file` | 分数来源文件 |
| `fallback_reason` | 无 fallback 时为空；例如 `pre_boundary_fill_with_direct` |

`candidate_layers_summary.json`：

```json
{
  "dataset": "MMKE",
  "subset": "entity",
  "model": "llava-v1.5-7b",
  "methods": ["Middle-layer Prior", "VisEdit-Contrib-Pre-Alt", "SaLEM-Alt", "GoldenLayer-LGA-Direct-AltPred", "Perturb-KL-Direct", "Ours-Pre"],
  "top_k_values": [3, 5],
  "layer_space": "text_decoder",
  "raw_candidate_layers_kept": true,
  "clean_candidate_layers_used_for_training": true,
  "notes": "Main methods follow their original candidate rules; Perturb-KL-Direct is the main perturbation baseline, while Perturb-KL-Pre is an ablation."
}
```

`candidate_union_for_edit.csv`：

```text
dataset,subset,model,layer,selected_by_methods
MMKE,entity,llava-v1.5-7b,18,VisEdit-Contrib-Pre-Alt|Ours-Pre
```

真实编辑训练只读取基于 `clean_candidate_layers` 生成的 `candidate_union_for_edit.csv`，避免每种方法重复训练同一个层；但排查定位方法时必须回看 `candidate_layers_raw.csv`，不能用清洗后结果反推方法原始输出。

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
| E-VQA | BLIP2-OPT | SaLEM-Alt | - | - | - |
| E-VQA | BLIP2-OPT | GoldenLayer-LGA-Direct-AltPred | - | - | - |
| E-VQA | BLIP2-OPT | Perturb-KL-Direct | - | - | - |
| E-VQA | BLIP2-OPT | Ours-Pre | - | - | - |

## 9.2 定位准确性表

| Dataset | Model | Method | Candidate Layers | Best-of-TopK | Regret | Hit@K |
|---|---|---|---|---:|---:|---:|
| E-VQA | BLIP2-OPT | Middle-layer Prior | L17,L18,L16 | - | - | - |
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Pre-Alt | L19,L18,L17 | - | - | - |
| E-VQA | BLIP2-OPT | SaLEM-Alt | - | - | - | - |
| E-VQA | BLIP2-OPT | GoldenLayer-LGA-Direct-AltPred | - | - | - | - |
| E-VQA | BLIP2-OPT | Perturb-KL-Direct | - | - | - | - |
| E-VQA | BLIP2-OPT | Ours-Pre | - | - | - | - |
| E-VQA | BLIP2-OPT | Oracle Sweep | - | - | 0 | 1 |

## 9.3 附加/消融/诊断候选层表

这些方法不进入主实验候选方法列。若要报告，单独放入附加/消融/诊断表：

| Dataset | Model | Method | Purpose | Top-1 | Top-3 | Top-5 |
|---|---|---|---|---:|---|---|
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Pre-Delta | 新旧贡献差分前置层消融 | - | - | - |
| E-VQA | BLIP2-OPT | VisEdit-Contrib-Direct-Pred / ModelPred | 旧答案/模型输出路径诊断 | - | - | - |
| E-VQA | BLIP2-OPT | GoldenLayer-LGA-Pre-AltPred | LGA 前置插入消融 | - | - | - |
| E-VQA | BLIP2-OPT | SaLEM-Delta | 新旧显著性差分消融 | - | - | - |
| E-VQA | BLIP2-OPT | Perturb-KL-Pre | KL 敏感区前置插入消融 | - | - | - |
| E-VQA | BLIP2-OPT | Ours-Direct | 本文分数峰值层直接编辑消融 | - | - | - |

---

# 10. 默认超参数汇总

## 10.1 主实验方法超参数

| 方法 | 超参数 | 默认值 |
|---|---|---|
| Middle-layer Prior | \(\rho\) | 0.55 |
| VisEdit-Contrib-Pre | \(\lambda\) | 0.5 |
| VisEdit-Contrib-Pre | smoothing window | 3 |
| VisEdit-Contrib-Pre | key token | `alt_first_token` / `pred_first_token` / `model_pred_first_token` |
| VisEdit-Contrib-* | primary rank metric | `score_positive` |
| SaLEM-Alt | primary rank metric | `mean_abs_parameter_gradient` |
| SaLEM-Alt | target_layer_type | `mlp_ffn` |
| GoldenLayer-LGA-Direct-AltPred | primary rank metric | `score_lga_dot` |
| GoldenLayer-LGA-Direct-AltPred | score_space | `hidden_visual_tokens` |
| GoldenLayer-LGA-* | old/new fields | `pred` / `alt` |
| Perturb-KL-Direct | noise scales | 0.1, 0.5, 1, 3 |
| Perturb-KL-Direct | seeds | 2026, 2027, 2028 |
| Perturb-KL-Direct | key_mode | `prompt_distribution` |
| Perturb-KL-Direct | perturb scope for VLM | visual tokens |
| Perturb-KL-Direct | primary rank metric | `score_kl_robust` |
| Ours | target contrast | `alt` vs `pred` |
| Ours | token scope | visual tokens |
| Ours | rank metric | negative cosine × new norm × depth weight |
| Oracle Sweep | metric | Average |

## 10.2 附加/消融/诊断方法超参数

| 方法 | 超参数 | 默认值 / 说明 |
|---|---|---|
| VisEdit-Contrib-Pre-Delta | \(\gamma\) | 1.0；仅用于新旧贡献差分前置层消融 |
| VisEdit-Contrib-Direct-Pred / ModelPred | key token | `pred_first_token` / `model_pred_first_token`；仅用于旧答案或模型输出路径诊断 |
| GoldenLayer-LGA-Pre-AltPred | \(\lambda\) | 0.5；仅用于 LGA 高分区前置插入消融 |
| SaLEM-Delta | normalization | min-max within same dataset × model；仅用于新旧显著性差分消融 |
| Perturb-KL-Pre | \(\lambda\) | 0.5；仅用于 KL 敏感区前置插入消融 |
| Ours-Direct | rank metric | negative cosine × new norm × depth weight；不做 Pre 转换 |

---

# 11. 注意事项

1. 对于 VLM，不同模型的 visual token 插入位置不同，需要先确认 hook 到的是哪一层、哪个 token 范围。
2. 对于 BLIP2-OPT、MiniGPT-4 这类 Q-Former 架构，要区分 Q-Former 层和语言解码器层。
3. 对于 LLaVA/Qwen2.5-VL/PaliGemma 等 decoder-only 风格模型，要统一候选层编号。
4. 如果目标是 visual adapter 插入层，必须区分 `Direct` 候选层和 `Pre` 插入层候选；不要把“贡献峰值层 / 显著层 / 敏感层”和“前置插入层”混在同一个方法名里。
5. 主实验按方法原始定义选层：VisEdit-Contrib-Pre 使用高贡献区前置层；SaLEM-Alt、GoldenLayer-LGA-Direct-AltPred 和 Perturb-KL-Direct 使用分数最高层；Ours 按本文公式输出候选层。
6. 如果某方法输出的是高贡献区或敏感区，而不是单个层，只有在方法名明确带 `Pre` 时才转换为该区间之前的 \(K\) 个层。
7. 如果某方法输出的候选层重复或越界，需要生成清洗后候选层用于训练并集，但原始候选层结果与处理后的候选层结果都必须保留；原始结果用于追踪方法行为，处理后结果用于训练与评测。
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
