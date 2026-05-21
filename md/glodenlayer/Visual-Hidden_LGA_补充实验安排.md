可以。这个补充实验建议命名为：

```text
Visual-Hidden LGA / Visual-Token Gradient LGA
```

它和你现在操作手册里的 **Adapter-LGA** 不同。你当前手册主要是对候选层 adapter 参数 \(\phi_L\) 求梯度，用来判断“哪一层 adapter 最适合承载编辑”；补充实验则对每层的**视觉 token hidden state** 求梯度，用来判断“视觉表征在哪一层对实体识别最敏感”。你手册里的 Adapter-LGA 已经明确是冻结基础 VLM，只对候选层 adapter 参数求梯度。

# 1. 实验目的

这个补充实验回答的问题是：

> **在 LLaVA / BLIP2 中，视觉实体识别所依赖的视觉表征在哪一层最容易被 old answer / target_new 的监督信号影响？**

它不是直接找最终编辑层，而是解释：

```text
为什么 LLaVA 浅层 adapter 可能更有效？
为什么 BLIP2 浅层可能容易塌陷？
视觉 token 的敏感层是否和 adapter 暴力扫层结果一致？
```

最终你要比较三类结果：

```text
1. Adapter-LGA top layers
2. Visual-Hidden LGA top layers
3. Brute-force adapter best layer
```

如果 LLaVA 的 Visual-Hidden LGA 也偏浅层，而暴力扫层最佳也是 layer 1，那么你就有更强证据说明：

> **LLaVA 的实体识别编辑优势来自浅层视觉-语言绑定 / visual grounding。**

---

# 2. 核心公式

对第 \(i\) 个样本：

\[
x_i=(I_i,Q_i)
\]

其中：

\[
I_i=\text{image}, \quad Q_i=\text{entity recognition prompt}
\]

旧答案：

\[
y_i^{old}
\]

新目标答案：

\[
y_i^{new}
\]

第 \(L\) 层视觉 token hidden state：

\[
h_{vis}^{i,L}
\]

old loss：

\[
\mathcal{L}_{old}^{i}
=
CE(M_{\theta}(I_i,Q_i),y_i^{old})
\]

new loss：

\[
\mathcal{L}_{new}^{i}
=
CE(M_{\theta}(I_i,Q_i),y_i^{new})
\]

其中基础模型参数 \(\theta\) 全部冻结，不训练 adapter。

对视觉 hidden state 求梯度：

\[
g_{old,vis}^{i,L}
=
\nabla_{h_{vis}^{i,L}}
\mathcal{L}_{old}^{i}
\]

\[
g_{new,vis}^{i,L}
=
\nabla_{h_{vis}^{i,L}}
\mathcal{L}_{new}^{i}
\]

单样本分数：

\[
s_{vis-dot}^{i,L}
=
\left(
g_{old,vis}^{i,L}
\right)^\top
g_{new,vis}^{i,L}
\]

聚合分数：

\[
S_{vis-dot}(L)
=
\sum_{i=1}^{N}
\left(
\nabla_{h_{vis}^{i,L}}\mathcal{L}_{old}^{i}
\right)^\top
\left(
\nabla_{h_{vis}^{i,L}}\mathcal{L}_{new}^{i}
\right)
\]

Visual-Hidden LGA 候选层：

\[
G^*_{vis-hidden}
=
\arg\max_L S_{vis-dot}(L)
\]

---

# 3. 还要额外记录一个视觉敏感度指标

因为你的任务是实体识别，old answer 和 target_new 可能冲突，dot 可能全负。因此除了 old-new dot，还建议记录 **new-target visual sensitivity**：

\[
S_{vis-new-norm}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
\nabla_{h_{vis}^{i,L}}
\mathcal{L}_{new}^{i}
\right\|_2
\]

这个指标回答：

> **target_new 的监督信号最强地作用在哪一层视觉 token 表征上？**

所以你最终可以同时报告：

```text
S_vis_dot：old-new 梯度关系，保持和 LGA 思路一致
S_vis_new_norm：新目标对视觉表征的敏感度
S_vis_cos：old-new 梯度方向一致性
```

如果出现：

```text
LLaVA layer 1 的 S_vis_new_norm 很高
但 S_vis_dot 不一定最高
```

这仍然可以解释：

> **layer 1 对目标实体识别很敏感，但 old/new 答案之间存在梯度冲突。**

---

# 4. 视觉 token 怎么定义？

## 4.1 LLaVA

LLaVA 结构大致是：

```text
vision encoder → projector → LLM decoder
```

图像经过 projector 后变成视觉 token，插入 LLM 输入序列中。

所以 LLaVA 的：

\[
h_{vis}^{i,L}
\]

就是第 \(L\) 层 LLM hidden states 中对应 image tokens 的部分。

实现上要记录：

```text
visual_token_start
visual_token_end
```

然后取：

```python
h_vis_L = hidden_states_L[:, visual_token_start:visual_token_end, :]
```

注意：LLaVA 里输入的 `<image>` token 往往会被展开成很多视觉 token，不是只看一个 `<image>` token 位置。

---

## 4.2 BLIP2

BLIP2 结构大致是：

```text
vision encoder → Q-Former → language projection → OPT decoder
```

进入 OPT decoder 的不是原始 patch token，而是 Q-Former 输出后的视觉 query / prefix 表征。

因此 BLIP2 的：

\[
h_{vis}^{i,L}
\]

建议定义为 OPT decoder 中对应视觉 prefix / query tokens 的 hidden states。

通常可以取 decoder 输入序列前面的 visual query token span，例如：

```text
0 : num_query_tokens
```

但你需要根据你当前 BLIP2 实现确认实际拼接顺序。

如果 BLIP2 的 OPT decoder 中无法方便分离 visual prefix tokens，就至少记录：

```text
visual_prefix_start
visual_prefix_end
num_query_tokens
```

---

# 5. 实验流程

## Step 1：数据保持不变

使用和 Adapter-LGA 一样的 bridge30 数据：

```text
edit_30_bridge_train_only_vis.json
```

只用：

```text
request.image
request.prompt
request.target_new
```

不使用：

```text
generality
locality
portability
```

old answer 仍然读取缓存：

```text
LLaVA old answer cache
BLIP2 old answer cache
```

---

## Step 2：不插 adapter，加载基础模型

这个补充实验建议第一版不插 adapter：

```text
M_theta = base LLaVA / base BLIP2
theta.requires_grad = False
```

但是 hidden states 需要：

```python
hidden_states.retain_grad()
```

这里的重点不是训练模型，而是读取：

\[
\nabla_{h_{vis}^{L}} \mathcal{L}
\]

---

## Step 3：确定候选层

和你 Adapter-LGA 保持一致：

```text
LLaVA: language_model.model.layers.0-31
BLIP2: language_model.model.decoder.layers.0-31
```

每层捕获的 hidden state 应该尽量和 adapter 插入点对齐。

如果你的 adapter 是挂在 layer \(L\) 的输入端，则捕获：

\[
h_{vis,in}^{L}
\]

如果 adapter 是挂在 layer \(L\) 的输出端，则捕获：

\[
h_{vis,out}^{L}
\]

建议手册里写清楚：

```text
Visual-hidden capture point must match adapter insertion point.
```

---

## Step 4：计算 old loss 和 new loss

对每个样本分别计算：

\[
\mathcal{L}_{old}^{i}
=
CE(M_{\theta}(I_i,Q_i),y_i^{old})
\]

\[
\mathcal{L}_{new}^{i}
=
CE(M_{\theta}(I_i,Q_i),y_i^{new})
\]

要求仍然是：

```text
1. 只对 answer tokens 计算 CE
2. image tokens 不参与 loss
3. prompt tokens 不参与 loss
4. prompt 部分 label = -100
```

---

## Step 5：对视觉 hidden states 求梯度

对每个候选层 \(L\)，取视觉 token hidden state：

\[
h_{vis}^{i,L}
\]

然后分别得到：

\[
g_{old,vis}^{i,L}
=
\nabla_{h_{vis}^{i,L}}
\mathcal{L}_{old}^{i}
\]

\[
g_{new,vis}^{i,L}
=
\nabla_{h_{vis}^{i,L}}
\mathcal{L}_{new}^{i}
\]

注意：这里不是对模型参数求梯度。

不是：

```text
grad theta_L
```

也不是：

```text
grad phi_L
```

而是：

```text
grad h_vis^L
```

---

# 6. 输出指标

建议输出下面这些字段。

## 6.1 主 LGA 风格指标

\[
S_{vis-dot}(L)
=
\sum_i
(g_{old,vis}^{i,L})^\top
g_{new,vis}^{i,L}
\]

对应字段：

```text
S_vis_dot
```

---

## 6.2 cosine 诊断

\[
S_{vis-cos}(L)
=
\frac{1}{N}
\sum_i
\frac{
(g_{old,vis}^{i,L})^\top g_{new,vis}^{i,L}
}{
\|g_{old,vis}^{i,L}\|_2
\|g_{new,vis}^{i,L}\|_2
+
\epsilon
}
\]

对应字段：

```text
S_vis_cos
```

---

## 6.3 new-target visual sensitivity

\[
S_{vis-new-norm}(L)
=
\frac{1}{N}
\sum_i
\left\|
g_{new,vis}^{i,L}
\right\|_2
\]

对应字段：

```text
S_vis_new_norm
```

这个指标在你的实体识别任务中很重要。

---

## 6.4 old-target visual sensitivity

\[
S_{vis-old-norm}(L)
=
\frac{1}{N}
\sum_i
\left\|
g_{old,vis}^{i,L}
\right\|_2
\]

对应字段：

```text
S_vis_old_norm
```

---

## 6.5 joint norm

\[
S_{vis-joint-norm}(L)
=
\frac{1}{N}
\sum_i
\|g_{old,vis}^{i,L}\|_2
\|g_{new,vis}^{i,L}\|_2
\]

对应字段：

```text
S_vis_joint_norm
```

---

## 6.6 positive ratio

\[
P_{vis+}(L)
=
\frac{1}{N}
\sum_i
\mathbf{1}
[
s_{vis-dot}^{i,L}>0
]
\]

对应字段：

```text
vis_positive_ratio
```

这个可以判断某层 dot 是不是大部分样本都正向，还是只是少数样本拉高。

---

## 6.7 median dot

\[
MedianVisDot(L)
=
median_i(s_{vis-dot}^{i,L})
\]

对应字段：

```text
median_vis_dot
```

---

# 7. 排名方式

建议不要只给一个 ranking，而是给三种 ranking：

```text
1. vis_dot_rank
2. vis_new_norm_rank
3. vis_cos_rank
```

解释方式：

```text
vis_dot_rank:
保持和 LGA 原始思想一致，衡量 old/new 梯度关系。

vis_new_norm_rank:
衡量 target_new 对视觉表征的影响强度，更适合解释实体识别。

vis_cos_rank:
衡量 old/new 梯度方向是否一致，用于诊断。
```

如果你的目标是“解释视觉实体识别”，我建议重点看：

```text
vis_new_norm_rank + brute-force best layer
```

如果你的目标是“复刻 LGA 思路”，则主报告：

```text
vis_dot_rank
```

---

# 8. 输出文件设计

建议新增目录：

```text
server_results/bridge_vlm_visual_hidden_lga_llava_train30/
server_results/bridge_vlm_visual_hidden_lga_blip2_train30/
```

每个目录包含：

```text
run_config.json
old_answer_mapping_report.json
sample_visual_hidden_scores.jsonl
visual_hidden_lga_layer_scores.csv
topk_visual_hidden_layers.json
summary.md
```

CSV 字段建议：

```csv
model,layer,capture_point,visual_token_start,visual_token_end,n_request,S_vis_dot,S_vis_cos,S_vis_new_norm,S_vis_old_norm,S_vis_joint_norm,vis_positive_ratio,median_vis_dot,vis_dot_rank,vis_new_norm_rank,vis_cos_rank
```

---

# 9. 建议执行命令

## LLaVA

```bash
cd VisEdit-main
python scripts/bridge_vlm_visual_hidden_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl \
  --layers 0-31 \
  --capture-point adapter_hook \
  --token-scope visual \
  --score-mode request_only_visual_hidden_lga \
  --main-score vis_dot \
  --diagnostics vis_cos,vis_new_norm,vis_old_norm,vis_joint_norm,positive_ratio,median_dot \
  --output-dir ../server_results/bridge_vlm_visual_hidden_lga_llava_train30
```

## BLIP2

```bash
cd VisEdit-main
python scripts/bridge_vlm_visual_hidden_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --config-path configs/vead/blip2-opt-2.7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl \
  --layers 0-31 \
  --capture-point adapter_hook \
  --token-scope visual_prefix \
  --score-mode request_only_visual_hidden_lga \
  --main-score vis_dot \
  --diagnostics vis_cos,vis_new_norm,vis_old_norm,vis_joint_norm,positive_ratio,median_dot \
  --output-dir ../server_results/bridge_vlm_visual_hidden_lga_blip2_train30
```

---

# 10. 和 Adapter-LGA 怎么对比？

最终报告里放这张表：

| Model | MLP-LGA Top-5 | Adapter-LGA Top-5 | Visual-Hidden Dot Top-5 | Visual New-Norm Top-5 | Brute-force Best |
|---|---|---|---|---|---:|
| LLaVA | 26,27,0,25,24 | ? | ? | ? | 1 |
| BLIP2 | ? | ? | ? | ? | 19* |

其中 BLIP2 的 19 现在只能标注为：

```text
loose exploratory best, strict best not confirmed
```

---

# 11. 结果解释逻辑

## 如果 LLaVA 出现：

```text
Visual-Hidden new-norm top-k = 0/1/2/6
Adapter-LGA top-k = 0/1/6/11
Brute-force best = 1
```

可以解释为：

> LLaVA 的视觉实体识别编辑主要依赖浅层视觉 token 表征，浅层 adapter 更容易调控视觉-语言绑定。

---

## 如果 LLaVA 出现：

```text
Visual-Hidden dot top-k 偏深层
但 new-norm top-k 偏浅层
```

可以解释为：

> old-new 梯度关系受到答案竞争影响，dot 偏向语言输出层；但 target_new 对视觉表征的敏感度仍显示浅层更关键。

---

## 如果 BLIP2 出现：

```text
Visual-Hidden top-k 偏中层/中后层
Adapter-LGA 也偏中层/中后层
```

可以解释为：

> BLIP2 的视觉信息经过 Q-Former 压缩后进入语言模型，浅层 decoder 不一定是最佳编辑位置，中层/中后层可能更适合承载实体编辑。

---

## 如果 BLIP2 结果仍然混乱

则说明：

```text
只看 OPT decoder visual prefix hidden states 不足以解释 BLIP2。
下一步应计算 Q-Former hidden states 或 language_projection / connector 的梯度敏感性。
```

---

# 12. 你应该把它写成补充实验，不要替代 Adapter-LGA

最终实验体系建议是：

```text
主实验：
Adapter-LGA
回答：哪一层 adapter 更适合承载编辑？

补充实验：
Visual-Hidden LGA
回答：视觉 token 表征在哪一层对实体识别目标更敏感？

最终验证：
Brute-force adapter scan
回答：实际训练后哪一层编辑效果最好？
```

一句话：

> **Adapter-LGA 负责选 adapter 候选层；Visual-Hidden LGA 负责解释视觉表征敏感层；最终 true edit layer 仍由暴力扫层验证。**
