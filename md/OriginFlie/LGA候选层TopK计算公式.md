# LGA 候选层 Top-K 计算公式整理

> 目标：用本文提出的 Layer Gradient Analysis（LGA）思想，为**不同模型**在**不同数据集**上计算候选编辑层的 Top-3 / Top-5。
>
> 适用场景：知识编辑（Knowledge Editing）中，先用 proxy set 估计候选层，再在 test set 或实际编辑任务中固定使用这些候选层。

---

## 1. 符号定义

| 符号 | 含义 |
|---|---|
| $M_{m}$ | 第 $m$ 个待分析模型，例如 GPT-2 XL、LLaMA2-7B、Gemma3-12B |
| $\hat{\theta}^{(m)}$ | 模型 $M_m$ 的参数 |
| $\mathcal{L}^{(m)}$ | 模型 $M_m$ 中可候选的编辑层集合，通常只考虑 MLP 层 |
| $L$ | 某一个候选层，$L \in \mathcal{L}^{(m)}$ |
| $\theta^{(m)}_{L}$ | 模型 $M_m$ 第 $L$ 层的参数 |
| $D_d$ | 第 $d$ 个数据集，例如 ZSRE、WikiBio、WikiCounterfact、WikiRecent、Counterfact |
| $Q^{(d)}$ | 数据集 $D_d$ 的 proxy set 查询集合 |
| $Q_i$ | proxy set 中第 $i$ 个编辑查询 |
| $K_i$ | 查询 $Q_i$ 对应的旧知识，也就是模型原始知识 |
| $K'_i$ | 查询 $Q_i$ 对应的新目标知识 |
| $\ell(\hat{\theta}; x)$ | 自回归交叉熵损失，输入为文本序列 $x$ |
| $\nabla_{\theta_L}\ell(\hat{\theta}; x)$ | 损失对第 $L$ 层参数的梯度 |

---

## 2. 单样本、单层 LGA 梯度相似度

论文先从梯度归因的内积形式出发：

$$
\phi(z, v)
=
\nabla_{\hat{\theta}} \ell(\hat{\theta}; z)^\top
\cdot
\nabla_{\hat{\theta}} \ell(\hat{\theta}; v)
$$

将它限制到某一层 $L$，得到层级梯度归因分数：

$$
\phi_L(z, v)
=
\nabla_{\theta_L} \ell(\hat{\theta}; z)^\top
\cdot
\nabla_{\theta_L} \ell(\hat{\theta}; v)
$$

在知识编辑任务中，对第 $i$ 个样本构造两段输入：

$$
x_i^{old}=Q_i \cup K_i
$$

$$
x_i^{new}=Q_i \cup K'_i
$$

于是，第 $i$ 个样本在第 $L$ 层上的 LGA 分数为：

$$
s_{i,L}
=
\phi_L(Q_i \cup K_i, Q_i \cup K'_i)
=
\nabla_{\theta_L}\ell(\hat{\theta}; Q_i \cup K_i)^\top
\cdot
\nabla_{\theta_L}\ell(\hat{\theta}; Q_i \cup K'_i)
$$

---

## 3. 单模型、单数据集的候选层总分

对一个模型 $M_m$ 和一个数据集 $D_d$，在 proxy set 上聚合所有样本的层级分数：

$$
S^{(m,d)}_L
=
\sum_{Q_i \in Q^{(d)}}
\phi_L(Q_i \cup K_i, Q_i \cup K'_i)
$$

展开为：

$$
S^{(m,d)}_L
=
\sum_{Q_i \in Q^{(d)}}
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K_i)^\top
\cdot
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K'_i)
$$

可选地，为了减少 proxy set 大小差异带来的影响，也可以使用平均分：

$$
\bar{S}^{(m,d)}_L
=
\frac{1}{|Q^{(d)}|}
\sum_{Q_i \in Q^{(d)}}
\phi_L(Q_i \cup K_i, Q_i \cup K'_i)
$$

> 对同一个数据集内部排序时，使用 $S_L$ 或 $\bar{S}_L$ 的 Top-K 结果相同。跨数据集比较数值大小时，更建议使用 $\bar{S}_L$。

---

## 4. Golden Layer 的 Top-1 计算

论文中的 LGA golden layer 估计为：

$$
G^*
=
\arg\max_{L \in \mathcal{L}}
\sum_{Q_i \in Q}
\phi_L(Q_i \cup K_i, Q_i \cup K'_i)
$$

针对不同模型、不同数据集，写成：

$$
G^{*(m,d)}
=
\arg\max_{L \in \mathcal{L}^{(m)}} S^{(m,d)}_L
$$

也就是：

$$
G^{*(m,d)}
=
\arg\max_{L \in \mathcal{L}^{(m)}}
\sum_{Q_i \in Q^{(d)}}
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K_i)^\top
\cdot
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K'_i)
$$

---

## 5. 候选层 Top-3 / Top-5 计算公式

先计算所有候选层的分数集合：

$$
\mathcal{S}^{(m,d)}
=
\left\{
(L, S^{(m,d)}_L)
\mid
L \in \mathcal{L}^{(m)}
\right\}
$$

按分数从大到小排序：

$$
\operatorname{Rank}^{(m,d)}
=
\operatorname{argsort}_{L \in \mathcal{L}^{(m)}}
\left(S^{(m,d)}_L\right)_{desc}
$$

Top-K 候选层定义为：

$$
\operatorname{TopK}^{(m,d)}(K)
=
\left\{
L_1, L_2, \dots, L_K
\right\}
$$

其中：

$$
S^{(m,d)}_{L_1}
\ge
S^{(m,d)}_{L_2}
\ge
\dots
\ge
S^{(m,d)}_{L_K}
$$

因此：

$$
\operatorname{Top3}^{(m,d)}
=
\operatorname{TopK}^{(m,d)}(3)
$$

$$
\operatorname{Top5}^{(m,d)}
=
\operatorname{TopK}^{(m,d)}(5)
$$

---

## 6. 推荐的归一化版本

如果不同层参数量差异较大，直接使用梯度内积可能偏向参数量更多的层。可以使用梯度向量维度归一化：

$$
S^{(m,d)}_{L,mean}
=
\frac{1}{|Q^{(d)}|}
\sum_{Q_i \in Q^{(d)}}
\frac{1}{|\theta^{(m)}_L|}
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K_i)^\top
\cdot
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K'_i)
$$

如果更关心方向一致性而不是梯度幅值，可以使用 cosine 版本：

$$
S^{(m,d)}_{L,cos}
=
\frac{1}{|Q^{(d)}|}
\sum_{Q_i \in Q^{(d)}}
\frac{
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K_i)^\top
\cdot
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K'_i)
}{
\left\|\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K_i)\right\|_2
\left\|\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K'_i)\right\|_2
+
\epsilon
}
$$

其中 $\epsilon$ 是防止除零的小常数。

---

## 7. Outlier Layer 过滤

论文实现细节中提到，LGA 会排除整体梯度分数异常的层，异常值检测使用 Tukey fences 和四分位距 IQR。

对所有层分数 $\{S_L\}$ 计算：

$$
Q_1 = \operatorname{Percentile}_{25}(\{S_L\})
$$

$$
Q_3 = \operatorname{Percentile}_{75}(\{S_L\})
$$

$$
IQR = Q_3 - Q_1
$$

Tukey fences：

$$
Lower = Q_1 - 1.5 \times IQR
$$

$$
Upper = Q_3 + 1.5 \times IQR
$$

保留非异常层：

$$
\mathcal{L}^{(m)}_{valid}
=
\left\{
L \in \mathcal{L}^{(m)}
\mid
Lower \le S^{(m,d)}_L \le Upper
\right\}
$$

过滤后的 Top-K：

$$
\operatorname{TopK}^{(m,d)}_{valid}(K)
=
\operatorname{TopK}_{L \in \mathcal{L}^{(m)}_{valid}}(K)
$$

---

## 8. 多模型、多数据集输出表格式

建议最终输出为以下表格，便于比较不同模型和数据集：

| Model | Dataset | Layer Scope | Score Type | Top-1 | Top-3 | Top-5 |
|---|---|---|---|---:|---|---|
| GPT-2 XL | ZSRE | MLP | raw dot product |  |  |  |
| GPT-2 XL | WikiBio | MLP | raw dot product |  |  |  |
| GPT-2 XL | WikiCounterfact | MLP | raw dot product |  |  |  |
| GPT-2 XL | WikiRecent | MLP | raw dot product |  |  |  |
| GPT-2 XL | Counterfact | MLP | raw dot product |  |  |  |
| LLaMA2-7B | ZSRE | MLP | raw dot product |  |  |  |
| LLaMA2-7B | WikiBio | MLP | raw dot product |  |  |  |
| LLaMA2-7B | WikiCounterfact | MLP | raw dot product |  |  |  |
| LLaMA2-7B | WikiRecent | MLP | raw dot product |  |  |  |
| LLaMA2-7B | Counterfact | MLP | raw dot product |  |  |  |
| Gemma3-12B | ZSRE | MLP | raw dot product |  |  |  |
| Gemma3-12B | WikiBio | MLP | raw dot product |  |  |  |
| Gemma3-12B | WikiCounterfact | MLP | raw dot product |  |  |  |
| Gemma3-12B | WikiRecent | MLP | raw dot product |  |  |  |
| Gemma3-12B | Counterfact | MLP | raw dot product |  |  |  |

---

## 9. 计算流程伪代码

```python
for model in models:
    load model
    candidate_layers = get_mlp_layers(model)

    for dataset in datasets:
        proxy_set = load_proxy_set(dataset)
        layer_scores = {L: 0.0 for L in candidate_layers}

        for sample in proxy_set:
            Q = sample["query"]
            K_old = sample["old_knowledge"]
            K_new = sample["new_knowledge"]

            x_old = concat(Q, K_old)
            x_new = concat(Q, K_new)

            # 分别计算 old / new 输入对每一层参数的梯度
            grads_old = compute_layer_grads(model, x_old, candidate_layers)
            grads_new = compute_layer_grads(model, x_new, candidate_layers)

            for L in candidate_layers:
                layer_scores[L] += dot(grads_old[L], grads_new[L])

        # 可选：按 proxy set 大小取平均
        for L in candidate_layers:
            layer_scores[L] /= len(proxy_set)

        # 可选：Tukey fences 过滤异常层
        valid_layers = tukey_filter(layer_scores)

        ranked_layers = sort_descending(valid_layers, key=lambda L: layer_scores[L])

        top1 = ranked_layers[:1]
        top3 = ranked_layers[:3]
        top5 = ranked_layers[:5]

        save_result(model, dataset, top1, top3, top5, layer_scores)
```

---

## 10. CSV / JSON 输出建议

### CSV

```csv
model,dataset,score_type,layer,score,rank
GPT-2 XL,ZSRE,raw_dot,16,0.0,1
GPT-2 XL,ZSRE,raw_dot,17,0.0,2
GPT-2 XL,ZSRE,raw_dot,15,0.0,3
```

### JSON

```json
{
  "GPT-2 XL": {
    "ZSRE": {
      "score_type": "raw_dot",
      "top1": [16],
      "top3": [16, 17, 15],
      "top5": [16, 17, 15, 19, 12]
    }
  }
}
```

---

## 11. 与论文表格结果的关系

论文附录中的表格给出了基于不同评价指标的 proxy optimal layer 与 test golden layer，例如 Rewrite Accuracy、Rephrase Accuracy、Locality、Portability、Fluency、Overall。

这些表格结果是“实际编辑后评估得到的层性能排序”，而 LGA 公式是“无需实际编辑、仅用梯度归因估计候选层”的计算方法。

因此，你要计算候选层 Top-3 / Top-5 时，应优先使用本文件第 3 到第 7 节的 LGA 分数公式；论文表格可以作为 sanity check，用来观察 LGA Top-K 是否覆盖实际编辑表现较好的层。

---

## 12. 最终推荐公式

如果只需要一个简洁可实现的版本，推荐使用以下公式计算不同模型、不同数据集的候选层 Top-3 / Top-5：

$$
S^{(m,d)}_L
=
\frac{1}{|Q^{(d)}|}
\sum_{Q_i \in Q^{(d)}}
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K_i)^\top
\cdot
\nabla_{\theta^{(m)}_L}\ell(\hat{\theta}^{(m)}; Q_i \cup K'_i)
$$

$$
\operatorname{Top3}^{(m,d)}
=
\operatorname{argsort}_{L \in \mathcal{L}^{(m)}_{valid}}
\left(S^{(m,d)}_L\right)_{desc}[1:3]
$$

$$
\operatorname{Top5}^{(m,d)}
=
\operatorname{argsort}_{L \in \mathcal{L}^{(m)}_{valid}}
\left(S^{(m,d)}_L\right)_{desc}[1:5]
$$

其中 $\mathcal{L}^{(m)}_{valid}$ 表示经过 Tukey fences 过滤后的有效 MLP 层集合。
