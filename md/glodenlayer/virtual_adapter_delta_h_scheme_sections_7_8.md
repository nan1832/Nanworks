# 虚拟 Adapter 输出 Δh 梯度选层方案：第 7 和第 8 部分

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
