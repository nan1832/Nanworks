# 虚拟 Adapter 输出 Δh 梯度选层方案：第 2、3、7 和第 8 部分

## 2. 视觉表征和文本表征分别怎么做？

假设第 \(l\) 层 hidden states 是：

```text
h_l = [h_v^l; h_t^l]
```

其中：

```text
h_v^l：视觉 token 表征
h_t^l：文本 token 表征
```

你在第 \(l\) 层分别加入两个虚拟输出：

```text
h_v^l → h_v^l + Δ_v^l
h_t^l → h_t^l + Δ_t^l
```

其中：

```text
Δ_v^l = 0
Δ_t^l = 0
requires_grad = True
```

也就是：

```text
visual tokens: h_v^l + Δ_v^l
text tokens:   h_t^l + Δ_t^l
```

这里的 \(Δ_v^l\) 和 \(Δ_t^l\) 不是一个真实 adapter 的输出，而是“虚拟 adapter 输出探针”。它们用于模拟：如果未来把 adapter 挂在这一层，它的 residual editing signal 会从哪个位置注入模型。

因为 \(Δ_v^l = 0\)、\(Δ_t^l = 0\)，所以 forward 时模型行为完全等于原始模型，不会受到随机 adapter 初始化的影响；但是 backward 时可以计算 loss 对这些虚拟输出变量的梯度，从而判断该层视觉/文本表征对编辑目标的敏感性。

对于第 \(i\) 个 request 样本：

```text
image_i + prompt_i
old_i：原模型旧答案
new_i：目标新答案 target_new
```

构造两个 loss：

```text
L_old^{req,i} = -log P(old_i | image_i, prompt_i)

L_new^{req,i} = -log P(new_i | image_i, prompt_i)
```

然后对第 \(l\) 层的虚拟视觉 adapter 输出求梯度：

```text
g_old_v^{i,l} = ∇_{Δ_v^l} L_old^{req,i}

g_new_v^{i,l} = ∇_{Δ_v^l} L_new^{req,i}
```

对应视觉层分数：

```text
S_req^v(l) = Σ_i <g_old_v^{i,l}, g_new_v^{i,l}>
```

文本同理：

```text
g_old_t^{i,l} = ∇_{Δ_t^l} L_old^{req,i}

g_new_t^{i,l} = ∇_{Δ_t^l} L_new^{req,i}
```

对应文本层分数：

```text
S_req^t(l) = Σ_i <g_old_t^{i,l}, g_new_t^{i,l}>
```

所以更准确地说：

```text
S_req^v(l)：第 l 层视觉 adapter 输出位置的梯度内积分数
S_req^t(l)：第 l 层文本 adapter 输出位置的梯度内积分数
```

它们不是对真实 adapter 参数求梯度，而是对虚拟 adapter 输出 \(Δ_v^l\)、\(Δ_t^l\) 求梯度。

如果直接写成：

```text
∇_{h_v^l} L_old, ∇_{h_v^l} L_new
∇_{h_t^l} L_old, ∇_{h_t^l} L_new
```

也是可以的。因为在 residual 形式下：

```text
h_l' = h_l + Δ_h^l
```

且 \(Δ_h^l = 0\)，所以：

```text
∇_{Δ_h^l} L = ∇_{h_l'} L
```

因此，对虚拟 adapter 输出求梯度和对该层 hidden states 求梯度在数学上是一致的；区别在于，前者更贴近“adapter 应该挂在哪一层”的研究叙事。

---

## 3. 这样做时，需要训练 adapter 吗？

不需要。

选层阶段流程是：

```text
冻结原始 VLM；
不挂真实 adapter；
在候选层插入零扰动变量 Δ；
计算 old loss 和 new loss；
反向传播得到 Δ 的梯度；
记录梯度相似度；
不更新任何参数。
```

所以：

```text
不会训练 adapter；
不会改变 base model；
不会改变 Δ；
只是用梯度做层敏感性分析。
```

你可以把 \(Δ\) 理解成“未来 adapter 输出的位置探针”。

反向传播本身只是计算梯度：

```python
loss.backward()
```

或者更推荐使用：

```python
torch.autograd.grad(loss, delta)
```

参数真正改变发生在：

```python
optimizer.step()
```

所以选层阶段不要创建 optimizer，也不要执行 `optimizer.step()`。

同时建议把模型参数全部冻结：

```python
for p in model.parameters():
    p.requires_grad_(False)
```

这样就不会有任何模型参数被更新。

需要注意的是：选层阶段不要挂随机初始化的真实 adapter。因为随机 adapter 会改变 forward hidden states：

```text
h_l' = h_l + Adapter_random(h_l)
```

这时模型输出已经不是原模型输出，计算出来的 old/new 梯度相似度会受到随机初始化、adapter 结构和输出尺度影响。

正确做法是：

```text
h_l' = h_l + Δ_h^l,  Δ_h^l = 0
```

这样：

```text
forward 不变；
backward 可测；
不更新参数；
不受 adapter 初始化影响。
```

选层完成后，才真正挂载并训练 adapter 参数。

---

## 7. 推荐你采用的实验方案

### Step 1：选 proxy set

使用训练集的 edit request：

只包括 reliability/request 数据

```text
image + prompt + old_answer + target_new
```

old_answer 可以用 base model 生成。

---

### Step 2：对每个候选层插入零扰动

对第 \(l\) 层：

```text
visual tokens: h_v^l + Δ_v^l
text tokens:   h_t^l + Δ_t^l
```

其中：

```text
Δ_v^l = 0
Δ_t^l = 0
requires_grad = True
```

---

### Step 3：计算 old/new loss

```text
L_old = -log P(old_answer | image, prompt)

L_new = -log P(target_new | image, prompt)
```

---

### Step 4：分别计算视觉和文本梯度

```text
g_old_v, g_new_v
g_old_t, g_new_t
```

---

### Step 5：得到每层分数

主分数可以先用 Golden Layer 原文的 dot product：

```text
S_v(l) = mean(dot(g_old_v, g_new_v))
S_t(l) = mean(dot(g_old_t, g_new_t))
```

同时建议记录：

```text
cosine similarity
old gradient norm
new gradient norm
dot score
```

因为你之前已经遇到过全负 dot 的情况，单独看 dot 可能不够稳定。

---

### Step 6：选 Top-K 层

不要只选一个层，先选：

```text
Visual Top-3 layers
Text Top-3 layers
```

然后再训练 adapter 验证。

---

## 8. 和真实 adapter 训练怎么衔接？

选层阶段结束后，才真正挂 adapter。

例如选出来：

```text
visual layer = 8
text layer = 12
```

然后训练：

```text
Visual adapter 挂在 layer 8，编辑 h_v^8
Text adapter 挂在 layer 12，编辑 h_t^12
```

训练时再用：

```text
request loss
generality loss
locality loss
portability loss
```

这个阶段才更新 adapter 参数。

所以完整流程是：

```text
梯度选层阶段：
不训练 adapter，只用 Δ 探针算梯度。

adapter 训练阶段：
固定选出的层，挂真实 adapter，训练 adapter 参数。

评估阶段：
冻结 adapter，测试 reliability / generality / locality / portability。
```
