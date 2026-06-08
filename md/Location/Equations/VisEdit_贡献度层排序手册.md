# VisEdit 式 Module Output Attribution 贡献度层排序手册

> 目标：参考 VisEdit 论文第 3.1 节和官方 `contribution_module.py` / `p_track.py` 的实现，计算“某个数据集在某个 VLLM 模型上的每层贡献度”，并得到层排序。本文档适用于 E-VQA、E-IC 或你自己整理的 VLM 编辑数据集。

---

## 1. 这个贡献度到底衡量什么？

VisEdit 的 3.1 节计算的是 **每一层 Attention 输出和 MLP 输出对某个 key token 的 next-token prediction 贡献度**。

也就是说，对于一个图像-文本输入：

```text
image + prompt  ->  预测下一个 token
```

我们不让模型完整生成答案，而是停在答案前一个位置，分析模型下一步要预测某个 key token 时，各层模块输出对这个 key token 的支持程度。

例如 E-VQA 样本：

```json
{
  "src": "Is it sunny?",
  "pred": "no",
  "alt": "yes",
  "image": "proxy/val2014/COCO_val2014_000000393513.jpg"
}
```

可以构造输入：

```text
Is it sunny? The answer is:
```

然后选择 key token：

```text
yes
```

计算每一层 Attention / MLP 输出对 `yes` 的贡献度。

---

## 2. key token 的几种选择方式

官方代码默认计算的是 **模型当前自己预测出来的 token**，即 `predict_word=None` 时使用模型 top-1 next token。若你要做编辑层定位，通常还需要显式指定 key token。

| 模式 | 代码设置 | 含义 | 适合用途 |
|---|---|---|---|
| `model_pred` | `predict_word=None` | 模型当前预测的 top-1 token | 复现 VisEdit 官方贡献图 |
| `alt` / `target_new` | `predict_word=r["target_new"]` | 编辑目标答案 token | 找“目标知识写入”相关层 |
| `pred` | `predict_word=d["pred"]` | 原始错误答案 token | 分析错误答案由哪些层支持 |
| `wrong_control` | `predict_word=loc_ans` 或随机错误 token | 无关错误 token | 做对照实验 |

建议你的实验至少计算三组：

```text
1. S_alt(l)：目标答案 alt 的贡献度
2. S_pred(l)：错误答案 pred 的贡献度
3. Delta(l) = S_alt(l) - S_pred(l)
```

其中 `Delta(l)` 更适合用于解释“哪些层更适合把模型从错误答案推向目标答案”。

---

## 3. 论文 3.1 节公式

### 3.1 Transformer 残差分解

对于 Transformer 中第 `l` 层、第 `n` 个 token 的隐藏表示：

```math
h_n^l = h_n^{l-1} + a_n^l + m_n^l,
\quad l \in \{1,\ldots,L\},\ n \in \{1,\ldots,N\}
```

其中：

| 符号 | 含义 |
|---|---|
| `h_n^l` | 第 `l` 层第 `n` 个 token 的 hidden state / hidden representation |
| `h_n^{l-1}` | 上一层第 `n` 个 token 的 hidden state |
| `a_n^l` | 第 `l` 层 Attention 模块在第 `n` 个 token 位置的输出 |
| `m_n^l` | 第 `l` 层 MLP / FFN 模块在第 `n` 个 token 位置的输出 |
| `l` | 层编号，范围为 `1` 到 `L`；代码里通常是 `0` 到 `L-1` |
| `L` | Transformer decoder 总层数，例如 BLIP2-OPT-2.7B 的 OPT decoder 为 32 层 |
| `n` | token 位置编号 |
| `N` | 输入序列总 token 数；这里重点使用最后一个 prompt token 位置，即 `N` |

Attention 和 MLP 输出定义为：

```math
a_n^l = \mathrm{Attn}^l(h_1^{l-1}, \ldots, h_n^{l-1})
```

```math
m_n^l = \mathrm{MLP}^l(h_n^{l-1}+a_n^l)
```

其中：

| 符号 | 含义 |
|---|---|
| `Attn^l(·)` | 第 `l` 层 Attention 子模块 |
| `MLP^l(·)` | 第 `l` 层 MLP / FFN 子模块 |

---

### 3.2 输入 embedding 与输出概率

给定一个 VLLM：

```math
f_\theta: X_v \times X_t \rightarrow O
```

其中：

| 符号 | 含义 |
|---|---|
| `f_θ` | 完整视觉语言模型 |
| `θ` | 模型参数 |
| `X_v` | 图像输入空间 |
| `X_t` | 文本 prompt 输入空间 |
| `O` | 文本输出空间 |
| `x_v` | 一个具体图像输入 |
| `x_t` | 一个具体文本问题 / prompt |
| `o` | 模型生成的文本回答 |

VisEdit 把 VLLM 内部的语言 Transformer 记为：

```math
\hat{f}_\theta: E_v \times E_t \rightarrow Y
```

其中：

| 符号 | 含义 |
|---|---|
| `\hat{f}_θ` | VLLM 中接收 image/text embeddings 并输出 next-token distribution 的 Transformer 部分 |
| `E_v` | 图像 embedding 空间 |
| `E_t` | 文本 embedding 空间 |
| `Y` | 词表概率分布空间 |

图像和文本 embedding 拼接为：

```math
\varepsilon = \varepsilon_v \oplus \varepsilon_t \in \mathbb{R}^{N \times d_h}
```

其中：

| 符号 | 含义 |
|---|---|
| `ε_v` | 图像 embedding 序列，维度为 `N_v × d_h` |
| `ε_t` | 文本 prompt embedding 序列，维度为 `N_t × d_h` |
| `ε` | 拼接后的完整 embedding 序列 |
| `⊕` | 序列拼接操作 |
| `N_v` | visual token 数量 |
| `N_t` | text token 数量 |
| `N = N_v + N_t` | 完整输入序列长度 |
| `d_h` | hidden dimension / 模型隐藏维度 |

最后一个 prompt token 的最终 hidden state 为 `h_N^L`，模型的 next-token 分布为：

```math
p = \delta(h_N^L W_V)
```

其中：

| 符号 | 含义 |
|---|---|
| `p` | next-token 概率分布 |
| `δ(·)` | softmax 函数 |
| `W_V` | LM head / vocabulary projection matrix，维度为 `d_h × |V|` |
| `V` | 词表 vocabulary |
| `|V|` | 词表大小 |
| `h_N^L W_V` | 最终 hidden state 映射到词表空间后的 logits |

---

### 3.3 模块输出对 logits 的分解

由残差结构展开：

```math
h_N^L = h_N^0 + \sum_{l=1}^{L}(a_N^l + m_N^l)
```

两边乘以 `W_V`：

```math
h_N^L W_V
=
h_N^0 W_V
+
\sum_{l=1}^{L}(a_N^l W_V + m_N^l W_V)
```

这说明最终 next-token logits 可以看成：

```text
初始 embedding 映射贡献 + 各层 Attention 输出贡献 + 各层 MLP 输出贡献
```

因此可以单独分析某一层 Attention 或 MLP 输出对目标 token 的贡献。

---

### 3.4 单个模块输出贡献度公式

对于某个模块输出：

```math
r \in \{a_N^l, m_N^l\}
```

也就是说，`r` 可以是第 `l` 层最后一个 prompt token 位置的 Attention 输出，也可以是 MLP 输出。

对 key token `o*` 的贡献度定义为：

```math
C_{o^*}(r) = \sqrt{C^p_{o^*}(r) \cdot C^v_{o^*}(r)}
```

其中 probability part 为：

```math
C^p_{o^*}(r) = \delta(rW_V)_{o^*}
```

value/logit part 为：

```math
C^v_{o^*}(r)
=
\frac{(rW_V)_{o^*}}
{\max_{l=1}^{L} \max\left(|(a_N^l W_V)_{o^*}|, |(m_N^l W_V)_{o^*}|\right)}
```

符号解释：

| 符号 | 含义 |
|---|---|
| `o*` | key token，即你要分析的目标 token；可以是模型预测 token、`alt`、`pred` 等 |
| `r` | 某一层某一模块的输出向量；可以是 `a_N^l` 或 `m_N^l` |
| `rW_V` | 将模块输出映射到词表空间得到的 logits |
| `(rW_V)_{o*}` | key token `o*` 对应位置的 logit 值 |
| `δ(rW_V)_{o*}` | key token `o*` 对应的 softmax 概率 |
| `C^p_{o*}(r)` | probability contribution，即模块输出单独映射后对 key token 的概率支持 |
| `C^v_{o*}(r)` | value contribution，即模块输出对 key token 的归一化 logit 支持 |
| `C_{o*}(r)` | 最终模块贡献度 |

注意：`C^p` 只看概率，`C^v` 看 logit 强度。论文这样设计是因为概率高但 logit 很小，不一定说明该模块对最终预测有强贡献。

---

## 4. 官方代码实现与论文公式的对应关系

官方实现主要分三步：

```python
pt.forward_and_trace(r['prompt'], r['image'])
p_dist_lists, word_lists, total_p, total_v = pt.p_tracking(save_results=False)
plot_influence(vs, ps)
```

### 4.1 forward_and_trace：hook 每层输出

`PTrack.forward_and_trace()` 会 hook 三类模块：

```text
layer outputs
attention outputs
MLP outputs
```

其中每个模型的模块路径由 `configs/p_track/{model_name}.yaml` 指定。

以 BLIP2-OPT-2.7B 为例：

```yaml
model_name: "blip2-opt-2.7b"
num_layers: 32
layer_module_tmp: "language_model.model.decoder.layers.{}"
mlp_module_tmp: "language_model.model.decoder.layers.{}.fc2"
attn_module_tmp: "language_model.model.decoder.layers.{}.self_attn"
norm_path: "language_model.model.decoder.final_layer_norm"
voc_path: "language_model.lm_head"
```

这说明 BLIP2-OPT-2.7B 的贡献度分析是在 OPT decoder 的 32 层上做的。

---

### 4.2 p_tracking：把模块输出映射到词表空间

官方代码中，模块输出 `reps` 不是直接乘 `W_V`，而是先经过 final norm，再经过 LM head：

```python
logits = self.voc(self.norm(reps))
```

这可以理解为代码版的：

```math
rW_V
```

更准确地说，代码实现是：

```math
z_r = \mathrm{LMHead}(\mathrm{FinalNorm}(r))
```

其中：

| 代码变量 | 数学含义 |
|---|---|
| `reps` | 模块输出 `r` |
| `self.norm(reps)` | final layer norm 后的模块表示 |
| `self.voc(...)` | LM head / vocabulary head |
| `logits` | `z_r`，模块输出映射到词表空间后的 logits |

然后对指定 key token 的概率和值分别记录：

```python
total_p[tm].append(float(torch.softmax(logits, 0)[predict_id]))
total_v[tm].append(float(logits[predict_id]))
```

对应：

```math
p_{s,l,t} = \delta(z_{s,l,t})_{o_s^*}
```

```math
v_{s,l,t} = (z_{s,l,t})_{o_s^*}
```

其中：

| 符号 | 含义 |
|---|---|
| `s` | 第 `s` 个样本 |
| `l` | 第 `l` 层 |
| `t` | 模块类型，`t ∈ {attn, mlp}` |
| `o_s*` | 第 `s` 个样本选择的 key token |
| `z_{s,l,t}` | 第 `s` 个样本、第 `l` 层、第 `t` 类模块输出映射后的 logits |
| `p_{s,l,t}` | key token 的 softmax 概率 |
| `v_{s,l,t}` | key token 的 logit 值 |

---

### 4.3 plot_influence：计算 signed contribution

官方 `contribution_module.py` 中的核心代码为：

```python
M = max(max(np.abs(vs['mlp'][i])), max(np.abs(vs['att'][i])))
mlp_vs = vs['mlp'][i] / M
att_vs = vs['att'][i] / M

mlp_infl = (mlp_vs / (np.abs(mlp_vs) ** prone2p)) * (mlp_ps ** prone2p)
att_infl = (att_vs / (np.abs(att_vs) ** prone2p)) * (att_ps ** prone2p)
```

默认：

```python
prone2p = 0.5
```

因此代码中的贡献度为：

```math
\tilde{v}_{s,l,t}
=
\frac{v_{s,l,t}}
{M_s}
```

```math
I_{s,l,t}
=
\frac{\tilde{v}_{s,l,t}}{|\tilde{v}_{s,l,t}|^{0.5}}
\cdot
p_{s,l,t}^{0.5}
```

等价于：

```math
I_{s,l,t}
=
\mathrm{sign}(\tilde{v}_{s,l,t})
\sqrt{|\tilde{v}_{s,l,t}|}
\sqrt{p_{s,l,t}}
```

其中：

| 符号 | 含义 |
|---|---|
| `M_s` | 第 `s` 个样本中所有层、所有 Attn/MLP 模块的 key-token logit 绝对值最大值 |
| `\tilde{v}_{s,l,t}` | 归一化后的 signed logit value |
| `I_{s,l,t}` | 代码实际计算的 signed module contribution |
| `sign(·)` | 符号函数，正 logit 保持正贡献，负 logit 保持负贡献 |

如果 `v` 为正，代码近似等价于论文公式：

```math
I_{s,l,t} \approx \sqrt{C^p_{o^*}(r) \cdot C^v_{o^*}(r)}
```

如果 `v` 为负，官方代码不会直接置零，而是保留负贡献。这一点和论文公式的简写表达相比更细。

---

## 5. 数据集准备流程

### 5.1 E-VQA 数据格式

原始 E-VQA 样本一般包含：

```json
{
  "src": "Is it sunny?",
  "pred": "no",
  "alt": "yes",
  "image": "proxy/val2014/COCO_val2014_000000393513.jpg",
  "rephrase": "Is the current weather condition clear and bright?",
  "image_rephrase": "proxy/val2014_image_rephrase/...png",
  "loc": "nq question: ...",
  "loc_ans": "...",
  "m_loc": "proxy/val2014/...jpg",
  "m_loc_q": "What does this grow from?",
  "m_loc_a": "roots"
}
```

官方 `EVQA` 类会转换成：

```python
new_d['request']['image'] = d['image']
new_d['request']['prompt'] = d['src']
new_d['request']['target_new'] = d['alt']
```

并且给 request prompt 加上：

```python
d['request']['prompt'] = '%s The answer is:' % d['request']['prompt']
```

因此实际输入模型的是：

```text
src + " The answer is:"
```

### 5.2 如果你要计算 pred 错误答案贡献度

官方 `EVQA` 类默认没有把 `pred` 存进 `request`。如果你要算 `pred`，建议修改 `dataset/vllm.py`：

```python
new_d['request']['target_pred'] = d['pred']
```

这样后面可以使用：

```python
predict_word = r['target_pred']
```

### 5.3 自定义数据集需要的最小字段

如果不是 E-VQA，你至少需要整理成：

```json
{
  "image": "图像路径",
  "prompt": "问题或描述，结尾停在答案前",
  "target_new": "目标答案",
  "target_pred": "错误答案，可选"
}
```

---

## 6. 贡献度计算完整流程

### Step 1：选择模型

确定模型名称，例如：

```python
model_name = 'blip2-opt-2.7b'
# 或：model_name = 'llava-v1.5-7b'
# 或：model_name = 'minigpt4-7b'
```

每个模型需要对应的 p_track 配置文件：

```text
configs/p_track/{model_name}.yaml
```

配置文件必须包含：

```yaml
model_name: 模型名称
num_layers: decoder 层数
layer_module_tmp: 每层整体输出路径
mlp_module_tmp: 每层 MLP 输出路径
attn_module_tmp: 每层 Attention 输出路径
norm_path: final norm 路径
voc_path: LM head 路径
```

---

### Step 2：加载数据集

如果使用 E-VQA 前 500 条：

```python
evqa = EVQA(
    data_path='data/easy-edit-mm/vqa/vqa_train.json',
    img_root_dir='data/easy-edit-mm/images',
    data_n=500
)
```

如果你已经随机抽好了 500 条：

```python
evqa = EVQA(
    data_path='data/easy-edit-mm/vqa/vqa_train_500.json',
    img_root_dir='data/easy-edit-mm/images'
)
```

建议随机抽样，而不是直接取前 500 条，以减少样本顺序偏差。

---

### Step 3：选择 key token 模式

```python
key_mode = 'alt'        # 目标答案贡献度
# key_mode = 'pred'     # 错误答案贡献度
# key_mode = 'model_pred'  # 官方默认：模型当前预测 token
```

推荐函数：

```python
def get_predict_word(r, key_mode):
    if key_mode == 'model_pred':
        return None
    elif key_mode == 'alt':
        return ' ' + r['target_new'].strip()
    elif key_mode == 'pred':
        return ' ' + r['target_pred'].strip()
    else:
        raise ValueError(key_mode)
```

为什么加前导空格？

OPT / LLaMA 类 tokenizer 往往把句中词编码为带空格 token，例如 `" yes"`。如果 prompt 是：

```text
Is it sunny? The answer is:
```

下一个 token 很可能是 `" yes"`，不是 `"yes"`。因此建议在指定答案时测试：

```python
tokenizer.decode(tokenizer(' yes', add_special_tokens=False).input_ids[0])
tokenizer.decode(tokenizer('yes', add_special_tokens=False).input_ids[0])
```

如果两者不同，应优先使用和生成位置一致的写法。

---

### Step 4：前向传播并记录每层输出

```python
pt.forward_and_trace(r['prompt'], r['image'])
```

该步骤会：

1. 将图像和 prompt 转成 LLM input embeddings；
2. 前向传播得到最终 logits；
3. hook 每层 Attention 输出、MLP 输出和 layer 输出。

---

### Step 5：计算每层模块对 key token 的 p 和 v

```python
_, _, total_p, total_v = pt.p_tracking(
    save_results=False,
    predict_word=predict_word
)
```

其中：

```python
total_p['att'][l]  # 第 l 层 Attention 输出映射后，对 key token 的 softmax 概率
total_v['att'][l]  # 第 l 层 Attention 输出映射后，对 key token 的 logit 值

total_p['mlp'][l]  # 第 l 层 MLP 输出映射后，对 key token 的 softmax 概率
total_v['mlp'][l]  # 第 l 层 MLP 输出映射后，对 key token 的 logit 值
```

---

### Step 6：对单个样本计算贡献度

对第 `s` 个样本，先计算归一化分母：

```python
M_s = max(
    max(abs(total_v['mlp'])),
    max(abs(total_v['att']))
)
```

然后对每层：

```python
v_norm = total_v[module][l] / M_s
score = sign(v_norm) * sqrt(abs(v_norm)) * sqrt(total_p[module][l])
```

对应数学式：

```math
I_{s,l,t}
=
\mathrm{sign}\left(\frac{v_{s,l,t}}{M_s}\right)
\sqrt{\left|\frac{v_{s,l,t}}{M_s}\right|}
\sqrt{p_{s,l,t}}
```

其中：

| 符号 | 含义 |
|---|---|
| `I_{s,l,t}` | 第 `s` 个样本、第 `l` 层、第 `t` 类模块的贡献度 |
| `t` | 模块类型，`attn` 或 `mlp` |
| `p_{s,l,t}` | key token 概率 |
| `v_{s,l,t}` | key token logit |
| `M_s` | 当前样本内最大 logit 绝对值，用于归一化 |

---

### Step 7：在整个数据集上平均

如果数据集有 `S` 个样本，则：

```math
\bar{I}_{l,t}
=
\frac{1}{S}\sum_{s=1}^{S} I_{s,l,t}
```

其中：

| 符号 | 含义 |
|---|---|
| `S` | 样本数量，例如 500 |
| `\bar{I}_{l,t}` | 第 `l` 层、第 `t` 类模块在整个数据集上的平均贡献度 |

代码：

```python
mean_attn = np.mean(np.stack(att_infls, 0), axis=0)
mean_mlp  = np.mean(np.stack(mlp_infls, 0), axis=0)
```

---

## 7. 层排序方法

VisEdit 原图分别画 Attention 和 MLP 的柱状图。如果你要得到单个层排序，需要把两类模块合并。

### 7.1 推荐排序公式一：正贡献求和

适合找 high-contribution layers：

```math
S_l^{+}
=
\max(0, \bar{I}_{l,attn})
+
\max(0, \bar{I}_{l,mlp})
```

优点：避免负贡献抵消正贡献，适合找对 key token 有正向支持的层。

### 7.2 推荐排序公式二：直接求和

适合严格复现 signed contribution：

```math
S_l^{signed}
=
\bar{I}_{l,attn}
+
\bar{I}_{l,mlp}
```

优点：保留正负方向。缺点：一个模块正、另一个模块负时会相互抵消。

### 7.3 推荐排序公式三：绝对贡献求和

适合分析“该层是否强烈影响 key token”，不区分正负方向：

```math
S_l^{abs}
=
|\bar{I}_{l,attn}|
+
|\bar{I}_{l,mlp}|
```

优点：能发现强抑制或强支持层。缺点：不适合直接当成“目标答案支持层”。

### 7.4 本研究建议

如果你的目标是编辑层定位，建议报告：

```text
alt_score_l  = max(0, I_alt_attn_l)  + max(0, I_alt_mlp_l)
pred_score_l = max(0, I_pred_attn_l) + max(0, I_pred_mlp_l)
delta_l = alt_score_l - pred_score_l
```

排序时优先看：

```text
1. delta_l 高
2. alt_score_l 高
3. pred_score_l 不过高
4. 该层不是过深到已经难以影响最终输出
```

---

## 8. 推荐输出文件

建议每次贡献度分析输出以下文件：

```text
results/contribution/{model_name}/{dataset_name}/{key_mode}/
├── contribution_raw.npy
├── contribution_layer.csv
├── contribution_rank.csv
├── contribution_plot.svg
└── config.json
```

### 8.1 contribution_layer.csv

建议列名：

```text
layer,attn_mean,mlp_mean,score_positive,score_signed,score_abs,rank_positive,rank_signed,rank_abs
```

### 8.2 config.json

记录实验设置：

```json
{
  "model_name": "blip2-opt-2.7b",
  "dataset": "E-VQA train proxy 500",
  "data_path": "data/easy-edit-mm/vqa/vqa_train_500.json",
  "key_mode": "alt",
  "prompt_template": "{src} The answer is:",
  "token_rule": "use first token of target answer with leading space",
  "num_layers": 32,
  "score_formula": "sign(v_norm)*sqrt(abs(v_norm))*sqrt(p)",
  "rank_formula": "max(0, attn_mean)+max(0, mlp_mean)"
}
```

---

## 9. 可直接改造的伪代码

```python
import numpy as np
from tqdm import tqdm

ks = ['layer', 'mlp', 'att']
ps = {k: [] for k in ks}
vs = {k: [] for k in ks}

key_mode = 'alt'  # alt / pred / model_pred

for r in tqdm(requests):
    pt.forward_and_trace(r['prompt'], r['image'])

    if key_mode == 'model_pred':
        predict_word = None
    elif key_mode == 'alt':
        predict_word = ' ' + r['target_new'].strip()
    elif key_mode == 'pred':
        predict_word = ' ' + r['target_pred'].strip()
    else:
        raise ValueError(key_mode)

    _, _, total_p, total_v = pt.p_tracking(
        save_results=False,
        predict_word=predict_word
    )

    for k in ks:
        ps[k].append(total_p[k])
        vs[k].append(total_v[k])

ps = {k: np.array(ps[k]) for k in ks}
vs = {k: np.array(vs[k]) for k in ks}

att_infls = []
mlp_infls = []

for i in range(len(vs['mlp'])):
    M = max(np.max(np.abs(vs['mlp'][i])), np.max(np.abs(vs['att'][i])))
    M = M + 1e-12

    mlp_v_norm = vs['mlp'][i] / M
    att_v_norm = vs['att'][i] / M

    mlp_p = ps['mlp'][i]
    att_p = ps['att'][i]

    mlp_infl = np.sign(mlp_v_norm) * np.sqrt(np.abs(mlp_v_norm)) * np.sqrt(mlp_p)
    att_infl = np.sign(att_v_norm) * np.sqrt(np.abs(att_v_norm)) * np.sqrt(att_p)

    mlp_infls.append(mlp_infl)
    att_infls.append(att_infl)

mean_mlp = np.mean(np.stack(mlp_infls, axis=0), axis=0)
mean_att = np.mean(np.stack(att_infls, axis=0), axis=0)

score_positive = np.maximum(mean_mlp, 0) + np.maximum(mean_att, 0)
score_signed = mean_mlp + mean_att
score_abs = np.abs(mean_mlp) + np.abs(mean_att)

rank_positive = np.argsort(-score_positive)
rank_signed = np.argsort(-score_signed)
rank_abs = np.argsort(-score_abs)

print('Top layers by positive contribution:', rank_positive[:10])
print('Top layers by signed contribution:', rank_signed[:10])
print('Top layers by absolute contribution:', rank_abs[:10])
```

---

## 10. 多 token 答案怎么处理？

官方 `p_tracking()` 对 `predict_word` 的处理是：

```python
predict_id = tokenizer(predict_word, add_special_tokens=False).input_ids[0]
```

也就是只取第一个 token。

因此如果答案是：

```text
Dave Sarachan
```

官方式简化计算只会分析第一个 token，例如：

```text
Dave
```

你有两种选择：

### 10.1 与 VisEdit 保持一致：只取第一个 token

优点：简单，和官方代码一致。  
缺点：不能完整表示多 token 答案。

### 10.2 更严格：逐 token teacher-forcing 后平均

对于目标答案 tokens：

```math
o^* = (o_1^*, o_2^*, \ldots, o_K^*)
```

对每个 token 单独计算贡献度：

```math
I_{s,l,t}^{(k)}
```

最后平均：

```math
I_{s,l,t}
=
\frac{1}{K}\sum_{k=1}^{K}I_{s,l,t}^{(k)}
```

这种方式更严谨，但需要每次把前面的目标 tokens 拼到 prompt 后，再重新 forward。

如果你的目标是复现 VisEdit 图，建议先使用第一种；如果你的目标是论文创新实验，可以补充第二种作为鲁棒性分析。

---

## 11. 最终报告模板

可以这样写：

> Following the module output attribution method in VisEdit, we trace the attention and MLP outputs of each decoder layer and map each module representation into the vocabulary space using the final normalization layer and LM head. For each sample, we compute the softmax probability and normalized logit value of the selected key token, and combine them into a signed contribution score. The scores are averaged over the proxy subset to obtain layer-wise contribution distributions. We further rank layers by the sum of positive attention and MLP contributions.

中文版本：

> 参考 VisEdit 的模块输出归因方法，本文对 VLLM 解码器各层 Attention 与 MLP 模块输出进行 hook，并通过最终归一化层和语言模型输出头将模块表示映射到词表空间。对于每个样本，本文计算指定 key token 在各层模块输出上的 softmax 概率与归一化 logit 值，并将二者组合为 signed contribution score。随后在代理子集上对贡献度取平均，得到层级贡献度分布，并基于 Attention 与 MLP 正贡献之和对候选编辑层进行排序。

如果你计算的是 `alt`：

> Unlike the original VisEdit implementation that uses the model-predicted token by default, we explicitly set the key token to the edited target answer `alt`, so that the resulting contribution distribution reflects the layer-wise support for target knowledge injection.

中文：

> 与 VisEdit 官方默认使用模型当前预测 token 不同，本文将 key token 显式设定为编辑目标答案 `alt`，从而使得到的贡献度分布反映各层对目标知识写入的潜在支持程度。

如果你计算的是 `pred`：

> We additionally compute the contribution distribution for the original wrong answer `pred`, which characterizes the layer-wise support for the model's erroneous prediction.

中文：

> 本文进一步计算原始错误答案 `pred` 的贡献度分布，用于刻画模型错误预测在不同层中的支持强度。

---

## 12. 注意事项

1. **不要把贡献度层排序直接等同于最终最佳编辑层。** 贡献度高说明该层对 key token 预测影响大，但编辑效果还取决于信号是否能传到后续层、是否破坏 locality、adapter 是否容易训练等。

2. **过深层贡献度高，不代表一定适合编辑。** VisEdit 也观察到过深层编辑效果可能下降，因为注入信号距离输出太近，可能难以产生足够稳定的改写影响。

3. **同一个数据集，不同模型的高贡献层可能不同。** 因为 BLIP2、LLaVA、MiniGPT-4 的视觉信息注入方式和 decoder 结构不同。

4. **同一模型，不同 key token 模式的排序也可能不同。** `model_pred`、`alt`、`pred` 分别回答不同问题，不能混用。

5. **样本数量会影响稳定性。** 500 个样本可以作为 proxy subset，但最好报告随机种子，并在条件允许时做多次抽样验证。

6. **tokenization 必须检查。** 尤其是 `yes` 和 ` yes`、`no` 和 ` no` 可能对应不同 token。

---

## 13. 推荐的实验命名

建议将实验命名为：

```text
Model-output contribution attribution on E-VQA train-500 proxy subset
```

如果使用 `alt`：

```text
Target-answer contribution attribution
```

如果使用 `pred`：

```text
Wrong-answer contribution attribution
```

如果使用差值：

```text
Target-minus-wrong contribution ranking
```

---

## 14. 一句话总结

VisEdit 3.1 的贡献度排序不是训练 adapter 得到的，而是通过一次前向传播 hook 各层 Attention/MLP 输出，将它们映射到 key token 的词表 logit 和概率上，再在数据集上平均得到的。用于你的视觉编辑层定位时，建议分别计算 `alt`、`pred` 及二者差值，而不是只复现官方默认的 model-pred token 贡献图。
