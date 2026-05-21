对，这里建议你记录 **4 类指标**：  
**主指标 = LGA 内积分数**；  
**辅助诊断 = cosine、gradient norm、norm-dominance ratio**。

下面给你完整公式。

---

# 1. 基础符号定义

对第 \(i\) 个样本：

\[
x_i=(I_i,Q_i)
\]

其中：

\[
I_i=\text{image}, \quad Q_i=\text{request prompt}
\]

旧答案：

\[
y_i^{old}
\]

新目标答案：

\[
y_i^{new}
\]

第 \(L\) 层参数：

\[
\theta_L
\]

old loss：

\[
\mathcal{L}_{old}^{i}
=
CE(M(x_i),y_i^{old})
\]

new loss：

\[
\mathcal{L}_{new}^{i}
=
CE(M(x_i),y_i^{new})
\]

第 \(L\) 层 old 梯度：

\[
g_{old}^{i,L}
=
\nabla_{\theta_L}\mathcal{L}_{old}^{i}
\]

第 \(L\) 层 new 梯度：

\[
g_{new}^{i,L}
=
\nabla_{\theta_L}\mathcal{L}_{new}^{i}
\]

原文 LGA 就是基于这种**层级梯度内积**来估计 golden layer：对 proxy set 中 old knowledge 和 new target knowledge 的层梯度内积求和，然后取最高层。fileciteturn8file0

---

# 2. 主指标：LGA Dot Product Score

这是你的**主实验指标**。

单个样本、单层：

\[
s_{\text{dot}}^{i,L}
=
(g_{old}^{i,L})^\top g_{new}^{i,L}
\]

展开理解就是：

\[
s_{\text{dot}}^{i,L}
=
\sum_{j=1}^{d_L}
g_{old,j}^{i,L}
g_{new,j}^{i,L}
\]

其中 \(d_L\) 是第 \(L\) 层参数量。

proxy set 聚合：

\[
S_{\text{dot}}(L)
=
\sum_{i=1}^{N}
(g_{old}^{i,L})^\top g_{new}^{i,L}
\]

最终 golden layer：

\[
G^*
=
\arg\max_{L}
S_{\text{dot}}(L)
\]

你的 LLaVA / BLIP2 分别计算：

\[
G^*_{\text{LLaVA}}
=
\arg\max_L S_{\text{dot}}^{\text{LLaVA}}(L)
\]

\[
G^*_{\text{BLIP2}}
=
\arg\max_L S_{\text{dot}}^{\text{BLIP2}}(L)
\]

**解释：**

\[
g_{old}\cdot g_{new}
=
\|g_{old}\|
\|g_{new}\|
\cos(\theta)
\]

所以 dot product 同时包含：

```text id="m5gqjp"
1. 梯度方向是否一致
2. 这一层梯度响应强不强
```

因此它更接近原文想衡量的“该层对 old → new 知识替换的影响力”。

---

# 3. 辅助指标一：Cosine Similarity Score

这是诊断指标，不作为主选层依据。

单个样本、单层：

\[
s_{\text{cos}}^{i,L}
=
\frac{
(g_{old}^{i,L})^\top g_{new}^{i,L}
}{
\|g_{old}^{i,L}\|_2
\|g_{new}^{i,L}\|_2
+\epsilon
}
\]

其中 \(\epsilon\) 是防止除零的小数，例如：

\[
\epsilon=10^{-8}
\]

proxy set 聚合可以用平均：

\[
S_{\text{cos}}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
s_{\text{cos}}^{i,L}
\]

也可以用加权平均，但建议第一版用普通平均。

**解释：**

- \(S_{\text{cos}}(L)\) 高：old 和 new 的梯度方向相似；
- \(S_{\text{cos}}(L)\) 低或负：old 和 new 的更新方向不一致；
- 如果 dot 很高但 cosine 不高，说明这一层可能是被梯度范数放大，而不是真正方向对齐。

---

# 4. 辅助指标二：Gradient Norm

这个用来判断某层是不是出现异常大梯度。

old gradient norm：

\[
n_{old}^{i,L}
=
\|g_{old}^{i,L}\|_2
\]

new gradient norm：

\[
n_{new}^{i,L}
=
\|g_{new}^{i,L}\|_2
\]

合并 norm：

\[
n_{\text{joint}}^{i,L}
=
\|g_{old}^{i,L}\|_2
\|g_{new}^{i,L}\|_2
\]

proxy set 平均：

\[
N_{old}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\|g_{old}^{i,L}\|_2
\]

\[
N_{new}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\|g_{new}^{i,L}\|_2
\]

\[
N_{\text{joint}}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\|g_{old}^{i,L}\|_2
\|g_{new}^{i,L}\|_2
\]

**解释：**

- norm 高：该层对 loss 变化敏感；
- norm 极端高：可能是异常梯度；
- dot 高 + norm 高 + cosine 低：需要警惕；
- dot 高 + norm 中等 + cosine 高：比较可信。

---

# 5. 辅助指标三：Norm-Dominance Ratio

这个指标用来判断：

> LGA dot 分数高，到底是因为方向真的对齐，还是因为梯度范数太大？

因为：

\[
s_{\text{dot}}^{i,L}
=
\|g_{old}^{i,L}\|_2
\|g_{new}^{i,L}\|_2
s_{\text{cos}}^{i,L}
\]

所以可以定义：

\[
R_{\text{norm-dom}}(L)
=
\frac{
S_{\text{dot}}(L)
}{
N_{\text{joint}}(L)+\epsilon
}
\]

但注意，严格来说这个值近似反映方向因素，和 cosine 有关系。

更直观的诊断可以这样写：

\[
D(L)
=
\frac{
N_{\text{joint}}(L)
}{
\frac{1}{|\mathcal{L}|}
\sum_{k\in \mathcal{L}}N_{\text{joint}}(k)
+\epsilon
}
\]

其中 \(|\mathcal{L}|\) 是候选层数量。

**解释：**

- \(D(L)\approx 1\)：该层梯度范数正常；
- \(D(L)\gg 1\)：该层梯度范数远高于平均，可能主导 dot；
- \(D(L)\ll 1\)：该层梯度响应很弱。

如果某一层：

\[
S_{\text{dot}}(L)\text{ rank}=1
\]

但：

\[
S_{\text{cos}}(L)\text{ 很低},\quad D(L)\gg 1
\]

那说明这个层可能不是理想 golden layer，而是“梯度范数异常大”。

---

# 6. 辅助指标四：Rank Consistency

这个不是原文指标，但很适合你分析 LLaVA / BLIP2。

分别计算三个排名：

\[
r_{\text{dot}}(L)
\]

\[
r_{\text{cos}}(L)
\]

\[
r_{\text{norm}}(L)
\]

其中 rank 越小表示越靠前。

可以定义一致性：

\[
C_{\text{rank}}(L)
=
\frac{
r_{\text{dot}}(L)+r_{\text{cos}}(L)
}{2}
\]

或者更简单地报告：

```text id="e71bg9"
Dot Rank
Cosine Rank
Norm Rank
Adapter Rank
```

你真正希望看到的是：

```text id="fo638u"
Dot Rank 高
Cosine Rank 也较高
Norm Rank 不异常
Adapter Rank 也高
```

这说明 LGA 选层可靠。

---

# 7. 你最终表格可以这样设计

| Model | Layer | Dot Score ↑ | Dot Rank | Cosine ↑ | Cos Rank | Joint Norm | Norm Ratio | LGA Selected |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| LLaVA | 0 |  |  |  |  |  |  |  |
| LLaVA | 1 |  |  |  |  |  |  | ✅ |
| LLaVA | 2 |  |  |  |  |  |  |  |
| BLIP2 | 15 |  |  |  |  |  |  |  |
| BLIP2 | 19 |  |  |  |  |  |  | ✅ |

---

# 8. 你的主实验最终采用哪个公式？

主实验只用这个：

\[
S_{\text{LGA}}(L)
=
S_{\text{dot}}(L)
=
\sum_{i=1}^{N}
(g_{old}^{i,L})^\top g_{new}^{i,L}
\]

golden layer：

\[
G^*
=
\arg\max_L S_{\text{LGA}}(L)
\]

辅助分析报告：

\[
S_{\text{cos}}(L)
\]

\[
N_{\text{joint}}(L)
\]

\[
D(L)
\]

一句话总结：

> **Dot product 是主指标；cosine、gradient norm、norm ratio 是诊断指标，用来解释 dot product 选出的层是否可靠。**
