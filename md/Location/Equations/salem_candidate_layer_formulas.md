# 候选层计算公式：Saliency-based Layer Selection（SaLEM）

本文档用于计算不同模型在不同数据集上的候选层 `top-3`、`top-5`。核心思想来自 SaLEM：用编辑数据集上的损失梯度构造参数显著性，再逐级聚合到列显著性、层显著性，最后按层显著性排序选出候选层。

---

## 1. 符号定义

给定基础模型：

$$
f_{\theta_W}(X)=Y
$$

其中：

| 符号 | 含义 |
|---|---|
| $f_{\theta_W}$ | 待编辑的基础模型 |
| $\theta_W$ | 模型已训练参数 |
| $D_{edit}$ | 编辑数据集 |
| $(X,Y)$ | 编辑样本及目标输出 |
| $L_{\theta_W}(X,Y)$ | 当前模型在样本上的损失 |
| $l$ | 第 $l$ 层 |
| $p$ | 第 $l$ 层中的某一列、通道、神经元或可聚合参数组 |
| $i$ | 参数索引 |
| $s_i$ | 参数级显著性 |
| $s_p$ | 列级显著性 |
| $s_l$ | 层级显著性 |
| $K$ | 候选层数量，例如 3 或 5 |

---

## 2. 参数级显著性

对每个编辑样本 $(X,Y)\in D_{edit}$，计算损失对模型参数的梯度绝对值：

$$
s_i(X,Y)=\left|\nabla_{\theta_W}L_{\theta_W}(X,Y)\right|_i
$$

解释：

梯度绝对值越大，说明该参数对当前错误预测或待编辑目标越敏感。该参数越可能是需要编辑的参数。

---

## 3. 列级显著性

对某一层中的一个参数列、通道或可聚合参数组 $p$，将其中所有参数级显著性取平均：

$$
s_p(X,Y)=\frac{1}{|p|}\sum_{i=1}^{|p|}s_i(X,Y)
$$

其中 $|p|$ 表示该列或参数组中的参数数量。

如果参数矩阵为：

$$
W_l\in\mathbb{R}^{d_{out}\times d_{in}}
$$

则可以按列计算：

$$
s_{l,j}(X,Y)=\frac{1}{d_{out}}\sum_{r=1}^{d_{out}}
\left|\frac{\partial L_{\theta_W}(X,Y)}{\partial W_l[r,j]}\right|
$$

其中 $j$ 是第 $l$ 层参数矩阵的第 $j$ 列。

---

## 4. 层级显著性

对第 $l$ 层中所有列级显著性取平均，得到该层显著性：

$$
s_l(X,Y)=\frac{1}{|l|}\sum_{p=1}^{|l|}s_p(X,Y)
$$

若第 $l$ 层权重矩阵为 $W_l\in\mathbb{R}^{d_{out}\times d_{in}}$，则等价写法为：

$$
s_l(X,Y)=
\frac{1}{d_{out}d_{in}}
\sum_{r=1}^{d_{out}}\sum_{j=1}^{d_{in}}
\left|\frac{\partial L_{\theta_W}(X,Y)}{\partial W_l[r,j]}\right|
$$

也就是该层所有参数梯度绝对值的平均值。

---

## 5. 数据集级层显著性

为了计算某个模型在某个数据集上的候选层，需要对整个编辑数据集 $D_{edit}$ 聚合：

$$
S_l(D_{edit})=
\frac{1}{|D_{edit}|}
\sum_{(X,Y)\in D_{edit}}s_l(X,Y)
$$

展开后：

$$
S_l(D_{edit})=
\frac{1}{|D_{edit}|}
\sum_{(X,Y)\in D_{edit}}
\frac{1}{|W_l|}
\sum_{i\in W_l}
\left|\frac{\partial L_{\theta_W}(X,Y)}{\partial W_l[i]}\right|
$$

其中：

$$
|W_l|=d_{out}d_{in}
$$

---

## 6. Top-K 候选层选择公式

将所有层的显著性分数排序，选择分数最高的 $K$ 层：

$$
E_L^{topK}=
\operatorname{TopK}_{l}
\left(S_l(D_{edit})\right)
$$

也可以写为：

$$
E_L^{topK}
=
\underset{l}{\operatorname{arg\,topK}}
\ S_l(D_{edit})
$$

用于 `top-3`：

$$
E_L^{top3}
=
\underset{l}{\operatorname{arg\,top3}}
\ S_l(D_{edit})
$$

用于 `top-5`：

$$
E_L^{top5}
=
\underset{l}{\operatorname{arg\,top5}}
\ S_l(D_{edit})
$$

---

## 7. 实际计算流程

### 输入

| 输入 | 说明 |
|---|---|
| 模型 $f_{\theta_W}$ | 例如 BERT、T5、BART、GPT-Neo、Distil-GPT2 |
| 编辑数据集 $D_{edit}$ | 通常包含错误样本 $X_{fail}$ 及其目标标签 |
| 目标层集合 $\mathcal{L}$ | 需要比较的候选层，例如所有 MLP 层 |
| 候选层数量 $K$ | 例如 3 或 5 |

### 输出

| 输出 | 说明 |
|---|---|
| `layer_score` | 每一层的显著性分数 $S_l$ |
| `top3_layers` | 显著性最高的 3 层 |
| `top5_layers` | 显著性最高的 5 层 |

---

## 8. 伪代码

```python
layer_scores = {l: 0.0 for l in target_layers}

for X, Y in D_edit:
    loss = model_loss(model, X, Y)
    loss.backward()

    for l in target_layers:
        grad = model.layers[l].weight.grad
        sample_layer_score = mean(abs(grad))
        layer_scores[l] += sample_layer_score

    model.zero_grad()

for l in target_layers:
    layer_scores[l] /= len(D_edit)

top3_layers = sorted(layer_scores, key=layer_scores.get, reverse=True)[:3]
top5_layers = sorted(layer_scores, key=layer_scores.get, reverse=True)[:5]
```

---

## 9. 针对不同模型的数据记录模板

你可以按下面格式记录每个模型在每个数据集上的候选层结果。

| Model | Dataset | Layer Count | Target Layer Type | Top-3 Layers | Top-5 Layers | Notes |
|---|---:|---:|---|---|---|---|
| BERT-large | MULTINLI | 12 | MLP / FFN |  |  |  |
| BERT-large | DIALOGUENLI | 12 | MLP / FFN |  |  |  |
| BERT-large | EMPATHETICDIALOGUES | 12 | MLP / FFN |  |  |  |
| BERT-large | PERSUASIONFORGOOD | 12 | MLP / FFN |  |  |  |
| BART-large | ZSRe | 24 | MLP / FFN |  |  |  |
| T5-XL | ZSRe | 24 | MLP / FFN |  |  |  |
| GPT-Neo 2.7B | WIKITEXT | 24 | MLP / FFN |  |  |  |
| Distil-GPT2 | WIKITEXT | 6 | MLP / FFN |  |  |  |

---

## 10. 计算注意事项

1. **必须保持同一套计算标准。**  
   不同模型、不同数据集之间比较候选层时，必须统一使用同一种层显著性定义。推荐使用每层梯度绝对值均值：

   $$
   S_l=\operatorname{mean}\left(|\nabla_{W_l}L|\right)
   $$

2. **不要直接用梯度总和比较不同大小的层。**  
   大层参数更多，梯度总和天然更大，会导致候选层偏向大参数层。应使用平均值归一化。

3. **建议只比较 MLP / FFN 层。**  
   SaLEM 的实验主要关注 MLP 层，因为前人工作中 MLP 层编辑效果更好。

4. **同一数据集应使用同一批编辑样本。**  
   推荐使用 $X_{fail}$ 或完整 $D_{edit}$。如果不同模型使用不同样本，top-k 层不可直接横向比较。

5. **top-3 和 top-5 只改变 $K$，不改变分数公式。**

---

## 11. 最终推荐公式

实际实验中建议直接使用下面这个版本：

$$
S_l(D_{edit})=
\frac{1}{|D_{edit}|}
\sum_{(X,Y)\in D_{edit}}
\operatorname{mean}
\left(
\left|
\nabla_{W_l}L_{\theta_W}(X,Y)
\right|
\right)
$$

然后：

$$
Top3=
\underset{l}{\operatorname{arg\,top3}}\ S_l(D_{edit})
$$

$$
Top5=
\underset{l}{\operatorname{arg\,top5}}\ S_l(D_{edit})
$$

这个公式最适合直接写进代码，用于批量计算不同模型、不同数据集的候选层。
