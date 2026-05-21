# Bridge30 Virtual Δh LGA 计算手册

## 0. 实验目标

本手册用于计算：

```text
Virtual Δh LGA：在不训练 adapter 的情况下，用零扰动 Δ 探针估计 LLaVA / BLIP2 的视觉与文本候选编辑层。
```

它回答的问题是：

```text
如果未来把 adapter 挂到第 l 层，视觉 token 位置和文本 token 位置分别有多适合承载 request-only 编辑信号？
```

本实验只计算层级梯度分数，不做参数更新：

```text
不训练 adapter
不加载 adapter checkpoint
不更新 base model
不更新 Δ
只计算 old/new loss 对虚拟 Δ 的梯度
```

最终编辑层仍必须由：

```text
真实 adapter 扫层训练 + request / generality / locality / portability 评测
```

来确认。Virtual Δh LGA 只用于生成候选层与诊断梯度信号。

## 1. 计算范围

本手册只参考：

```text
md/glodenlayer/virtual_adapter_delta_h_scheme_updated.md
```

本次要计算的是：

```text
同一候选层同时插入 Δ_v 和 Δ_t
分别得到视觉分数 S_v(l) 与文本分数 S_t(l)
输出 Visual Top-K 与 Text Top-K
```

重点输出：

```text
visual tokens 的 Δ_v 梯度分数
text tokens 的 Δ_t 梯度分数
visual/text 分支同一次实验中的可比诊断信息
```

注意：visual 和 text 的 token 数、维度、梯度尺度不同，原始 dot 不应直接跨模态比较。视觉层和文本层应分别排序。

## 2. 数据与模型

### 2.1 Proxy Set

使用 Bridge30 训练集 request 字段：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

服务器 request-only 版本：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json
```

参与计算的字段：

```text
request.image
request.prompt
request.target_new
old_answer
```

不参与 Virtual Δh LGA 选层计算的字段：

```text
generality
locality
portability
```

这些字段只用于后续真实 adapter 评估。

### 2.2 old_answer 来源

优先读取 base model 的未编辑生成结果：

```text
LLaVA: Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl
BLIP2: Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl
```

如果缓存不存在，则用 base model 对每条 request 生成 old_answer，并保存：

```text
old_answer_mapping_report.json
old_answer_cache.jsonl
```

要求：

```text
old answer mapped cases = 30/30
```

### 2.3 模型路径

服务器模型路径：

```text
LLaVA: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
BLIP2: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b
```

配置文件路径：

```text
LLaVA: /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/llava/llava-v1.5-7b-bridge-request-only-l{L}.yaml
BLIP2: /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2/blip2-opt-2.7b-bridge-request-only-l{L}.yaml
```

配置中的 adapter 层位置只用于对齐 hook / intervention point，不加载真实 adapter 权重。

## 3. 核心公式

第 \(i\) 个样本：

```text
x_i = image_i + prompt_i
y_old_i = base model old answer
y_new_i = request.target_new
```

第 \(l\) 层 hidden states 拆成：

```text
h_l = [h_v^l; h_t^l]
```

其中：

```text
h_v^l：视觉 token 表征
h_t^l：文本 prompt token 表征
```

在第 \(l\) 层插入零扰动：

```text
h_v^l -> h_v^l + Δ_v^l
h_t^l -> h_t^l + Δ_t^l
```

约束：

```text
Δ_v^l = 0
Δ_t^l = 0
requires_grad = True
```

因此：

```text
forward 行为等于原始 base model
backward 可以得到 loss 对 Δ 的梯度
```

old/new loss：

```text
L_old^{i,l} = -log P(y_old_i | image_i, prompt_i)
L_new^{i,l} = -log P(y_new_i | image_i, prompt_i)
```

视觉梯度：

```text
g_old_v^{i,l} = ∇_{Δ_v^l} L_old^{i,l}
g_new_v^{i,l} = ∇_{Δ_v^l} L_new^{i,l}
```

文本梯度：

```text
g_old_t^{i,l} = ∇_{Δ_t^l} L_old^{i,l}
g_new_t^{i,l} = ∇_{Δ_t^l} L_new^{i,l}
```

主分数：

```text
S_v_dot(l) = mean_i dot(flat(g_old_v^{i,l}), flat(g_new_v^{i,l}))
S_t_dot(l) = mean_i dot(flat(g_old_t^{i,l}), flat(g_new_t^{i,l}))
```

诊断分数：

```text
S_v_cos(l) = mean_i cos(g_old_v^{i,l}, g_new_v^{i,l})
S_t_cos(l) = mean_i cos(g_old_t^{i,l}, g_new_t^{i,l})

S_v_old_norm(l) = mean_i ||g_old_v^{i,l}||_2
S_v_new_norm(l) = mean_i ||g_new_v^{i,l}||_2
S_t_old_norm(l) = mean_i ||g_old_t^{i,l}||_2
S_t_new_norm(l) = mean_i ||g_new_t^{i,l}||_2
```

为了避免 token 数量差异误导，还需要记录归一化 dot：

```text
S_v_dot_per_dim(l) = mean_i dot(g_old_v, g_new_v) / numel(g_old_v)
S_t_dot_per_dim(l) = mean_i dot(g_old_t, g_new_t) / numel(g_old_t)
```

## 4. Token Scope 定义

### 4.1 LLaVA

LLaVA 的视觉 token 是 projector 输出后插入 LLM 序列的 image tokens。

默认视觉范围：

```text
visual_token_start
visual_token_end
```

从模型实际输入映射中读取，不手写固定值。

文本范围：

```text
text prompt tokens
```

要求：

```text
排除 visual tokens
排除 padding tokens
排除答案 label tokens
优先只保留 prompt/question tokens
```

如果实现上难以精确区分 prompt token 与 answer token，则同时输出两个 scope：

```text
text_prompt
text_all_nonvisual
```

最终主表使用 `text_prompt`。

### 4.2 BLIP2

BLIP2 的视觉 token 是 Q-Former 输出投影到 OPT decoder 的 visual prefix / query tokens。

默认视觉范围：

```text
visual_prefix tokens
```

文本范围：

```text
OPT decoder prompt tokens
```

要求同 LLaVA：

```text
排除 visual prefix
排除 padding tokens
排除答案 label tokens
优先只保留 prompt/question tokens
```

## 5. 计算流程

### Step 1：加载模型并冻结参数

```python
for p in model.parameters():
    p.requires_grad_(False)
model.eval()
```

检查：

```text
base_requires_grad_params = 0
adapter_used = false
optimizer_used = false
```

### Step 2：遍历候选层

候选层：

```text
0-31
```

每次只在一个候选层插入虚拟 Δ。

### Step 3：在 hook 点插入零扰动

伪代码：

```python
h = hidden_states
h_v = h[:, visual_start:visual_end, :]
h_t = h[:, text_indices, :]

delta_v = torch.zeros_like(h_v, requires_grad=True)
delta_t = torch.zeros_like(h_t, requires_grad=True)

h[:, visual_start:visual_end, :] = h_v + delta_v
h[:, text_indices, :] = h_t + delta_t
```

实现时不要原地破坏 autograd graph，优先用 clone / index_copy 或项目已有 hook 写法。

### Step 4：分别计算 old/new 梯度

推荐 old 和 new 各跑一次 forward，避免 retain_graph 混乱：

```python
L_old = nll_loss(model, image, prompt, old_answer)
g_old_v, g_old_t = torch.autograd.grad(L_old, [delta_v, delta_t])

L_new = nll_loss(model, image, prompt, target_new)
g_new_v, g_new_t = torch.autograd.grad(L_new, [delta_v, delta_t])
```

注意：

```text
不调用 optimizer.step()
不保存任何 adapter checkpoint
不改变模型权重
```

### Step 5：记录单样本分数

每个样本、每层输出一行：

```text
case_id
image_id
layer
model
old_answer
target_new
old_loss
new_loss
visual_token_start
visual_token_end
text_token_count
s_v_dot
s_v_dot_per_dim
s_v_cos
v_old_norm
v_new_norm
v_joint_norm
v_grad_nonzero_ratio
s_t_dot
s_t_dot_per_dim
s_t_cos
t_old_norm
t_new_norm
t_joint_norm
t_grad_nonzero_ratio
```

### Step 6：聚合层分数

每层聚合：

```text
S_v_dot
S_v_dot_per_dim
S_v_cos
S_v_old_norm
S_v_new_norm
S_v_joint_norm
v_positive_ratio
v_zero_grad

S_t_dot
S_t_dot_per_dim
S_t_cos
S_t_old_norm
S_t_new_norm
S_t_joint_norm
t_positive_ratio
t_zero_grad
```

主排序：

```text
Visual Top-K：按 S_v_dot 排序
Text Top-K：按 S_t_dot 排序
```

辅助排序：

```text
Visual new-norm Top-K：按 S_v_new_norm 排序
Text new-norm Top-K：按 S_t_new_norm 排序
```

遇到全负 dot 或零梯度退化层时，必须同时报告：

```text
cos
new_norm
joint_norm
positive_ratio
zero_grad
```

## 6. 输出目录与文件

建议输出目录：

```text
server_results/bridge_vlm_virtual_delta_h_lga_llava_train30/
server_results/bridge_vlm_virtual_delta_h_lga_blip2_train30/
```

关键文件：

```text
run_config.json
old_answer_cache.jsonl
old_answer_mapping_report.json
sample_virtual_delta_h_scores.jsonl
virtual_delta_h_layer_scores.csv
topk_virtual_delta_h_layers.json
summary.md
full_run.log
```

完整性检查：

```text
sample rows = 960 = 32 layers * 30 requests
old answer mapped cases = 30/30
base_requires_grad_params = 0
adapter_used = false
optimizer_used = false
forward_equivalence_max_diff < 1e-5
```

`forward_equivalence_max_diff` 用于确认：

```text
插入 Δ=0 后，模型 logits 与未插入 Δ 的 base forward 一致。
```

## 7. 服务器运行命令模板

进入项目：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0
```

LLaVA：

```bash
/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 \
  scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name llava-v1.5-7b \
  --data-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --config-dir /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/llava \
  --config-prefix llava-v1.5-7b-bridge-request-only \
  --bridge-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --layers 0-31 \
  --token-scopes visual,text_prompt \
  --output-dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga_llava_train30 \
  --device cuda:0
```

BLIP2：

```bash
/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 \
  scripts/bridge_vlm_virtual_delta_h_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --data-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --config-dir /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2 \
  --config-prefix blip2-opt-2.7b-bridge-request-only \
  --bridge-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --layers 0-31 \
  --token-scopes visual,text_prompt \
  --output-dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga_blip2_train30 \
  --device cuda:0
```

后台运行示例：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga_llava_train30
mkdir -p "$OUT"
nohup bash scripts/run_bridge_virtual_delta_h_lga_llava.sh > "$OUT/full_run.log" 2>&1 &
```

注意：上述 `bridge_vlm_virtual_delta_h_lga_scan.py` 是本实验建议实现的脚本名。如果代码尚未实现，应以已有 `bridge_vlm_visual_hidden_lga_scan.py` 为基础扩展 text token Δ_t 逻辑。

## 8. 结果表格式

`virtual_delta_h_layer_scores.csv` 至少包含：

```text
model
layer
n_request
visual_token_scope
text_token_scope
S_v_dot
S_v_dot_per_dim
S_v_cos
S_v_old_norm
S_v_new_norm
S_v_joint_norm
v_positive_ratio
v_zero_grad
v_dot_rank
v_new_norm_rank
S_t_dot
S_t_dot_per_dim
S_t_cos
S_t_old_norm
S_t_new_norm
S_t_joint_norm
t_positive_ratio
t_zero_grad
t_dot_rank
t_new_norm_rank
```

`topk_virtual_delta_h_layers.json` 建议包含：

```json
{
  "model": "llava-v1.5-7b",
  "main_score": {
    "visual": "S_v_dot",
    "text": "S_t_dot"
  },
  "topk": {
    "visual_dot": [],
    "visual_new_norm": [],
    "text_dot": [],
    "text_new_norm": []
  },
  "degenerate_layers": {
    "visual_zero_grad": [],
    "text_zero_grad": []
  }
}
```

## 9. 候选层选择规则

不要只选一个层，至少保留：

```text
Visual dot Top-3
Visual new-norm Top-3
Text dot Top-3
Text new-norm Top-3
```

筛选时排除：

```text
zero_grad = true
joint_norm 接近 0
new_norm 接近 0
```

如果 dot 全负：

```text
不能简单取最接近 0 的层当最佳层
需要同时看 new_norm、joint_norm、positive_ratio
```

推荐最终输出：

```text
Visual候选层：3-5 个
Text候选层：3-5 个
需要真实 adapter 验证的组合：不超过 6 组
```

组合策略：

```text
1. visual best + text best
2. visual best + text new-norm best
3. visual new-norm best + text best
4. 当前 full-layer sweep 最佳视觉层 + text best
5. 当前 full-layer sweep 最佳视觉层 + text new-norm best
```

## 10. 与真实 adapter 训练衔接

Virtual Δh LGA 完成后，才进行真实 adapter 训练：

```text
固定 visual layer
固定 text layer
挂真实 adapter
训练 adapter 参数
```

训练目标可以扩展为：

```text
request loss
generality loss
locality loss
portability loss
```

但要和选层阶段区分：

```text
选层阶段：只用 request，计算 Δ 梯度，不训练参数
训练阶段：使用真实 adapter，可以引入 full metrics 训练目标
评估阶段：冻结 adapter，测试 request / generality / locality / portability
```

## 11. 报告规则

结果报告文件建议命名：

```text
md/glodenlayer/Bridge30_Virtual_DeltaH_LGA_Result.md
```

必须报告：

```text
1. LLaVA Visual Top-3 / Text Top-3
2. BLIP2 Visual Top-3 / Text Top-3
3. dot 与 new_norm 是否一致
4. 是否存在 zero-gradient 退化层
5. Visual Top-K 与 Text Top-K 的候选层交集和差异
```

解释时遵守：

```text
Virtual Δh 只说明梯度敏感性
不能把 Δh 梯度高直接写成最终最佳 adapter 层
最终 adapter 层仍需真实训练和评估确认
```

## 12. 当前待补实验

截至本手册编写时：

```text
Virtual Δ_v 指标尚未按本手册统一重算
Virtual Δ_t 指标尚未按本手册统一计算
Virtual Δ_v + Δ_t 同实验表尚未生成
```

因此下一步是：

```text
实现 bridge_vlm_virtual_delta_h_lga_scan.py
在 g07 上分别跑 LLaVA 与 BLIP2
生成 visual/text Top-K
再决定是否训练双分支或文本分支 adapter ablation
```

---

## 13. 实验手册审查与补充建议

整体看，这个实验手册**方向是对的，主公式没有原则性错误**：你现在定义的是 **request-only Virtual Δh LGA**，即在不训练 adapter 的情况下，对候选层插入零扰动 \(Δ_v^l,Δ_t^l\)，分别计算 old/new request loss 对视觉 token 和文本 token 虚拟输出的梯度，然后用梯度内积给视觉层、文本层分别排序。这个设计和“分模态 adapter 插入层候选选择”是匹配的。

手册中也已经明确：

```text
选层阶段不训练 adapter
不更新 base model
不更新 Δ
generality / locality / portability 只用于后续真实 adapter 训练与评估
```

这点是合理的。

但有几处需要补充或修正，尤其是：

```text
loss 归一化
dot 分数解释
token scope
真实 adapter 验证实验
```

---

### 13.1 公式总体正确，但建议改两个细节

#### 13.1.1 \(L_{old}^{i,l}\)、\(L_{new}^{i,l}\) 建议写成 \(L_{old}^{i}\)、\(L_{new}^{i}\)

手册里目前写的是：

```text
L_old^{i,l} = -log P(y_old_i | image_i, prompt_i)
L_new^{i,l} = -log P(y_new_i | image_i, prompt_i)
```

严格来说，loss 本身不是第 \(l\) 层特有的，特有的是它对第 \(l\) 层 \(Δ\) 的梯度。

更严谨写法是：

```text
L_old^i = -log P(y_old_i | image_i, prompt_i)
L_new^i = -log P(y_new_i | image_i, prompt_i)
```

然后：

```text
g_old_v^{i,l} = ∇_{Δ_v^l} L_old^i
g_new_v^{i,l} = ∇_{Δ_v^l} L_new^i
```

这不是大错误，但论文或手册里建议改得更严谨。

---

#### 13.1.2 target 是多 token 时，loss 必须明确是 mean NLL

现在手册中写的是：

```text
L_old = -log P(old_answer | image, prompt)
L_new = -log P(target_new | image, prompt)
```

如果 `old_answer` 或 `target_new` 是多 token，比如：

```text
Chikugo River Lift Bridge
```

建议明确：

```text
L_old = mean_token_NLL(old_answer | image, prompt)
L_new = mean_token_NLL(target_new | image, prompt)
```

不要用 sum NLL 作为主 loss，否则长答案会产生更大的梯度范数，影响不同样本的层分数。

推荐补充：

```text
所有 old/new answer loss 均采用 answer token 上的平均 NLL；
prompt token 不参与 loss；
padding token 不参与 loss。
```

---

### 13.2 主分数 dot 没错，但要谨慎解释

当前主分数是：

```text
S_v_dot(l) = mean_i dot(g_old_v^{i,l}, g_new_v^{i,l})
S_t_dot(l) = mean_i dot(g_old_t^{i,l}, g_new_t^{i,l})
```

这个和 Golden Layer 原文的 old/new loss gradient dot 思路是一致的，可以作为基础版 LGA。

但要注意：**在 adapter-output / hidden-state 场景下，dot 的符号解释不一定和参数编辑完全一样**。

从优化直觉看，如果我们沿着 \(-g_{new}\) 的方向降低 new loss，那么 old loss 的一阶变化是：

```text
ΔL_old ≈ - dot(g_old, g_new)
```

所以：

```text
dot 很大且为正：降低 new loss 的同时可能也降低 old loss；
dot 为负：降低 new loss 时可能提高 old loss，也就是更像“替换旧答案”。
```

Golden Layer 原文选择正向内积最大，但这里是 hidden-state / adapter-output 探针，不一定完全等价。因此手册里最好加一句：

```text
S_dot 作为主分数沿用 Golden Layer 的梯度相似性定义，但其符号与最终 adapter 编辑效果之间的关系需要通过真实 adapter 扫层实验验证。若出现全负 dot 或 dot 与真实编辑效果不一致，应同时比较 -dot、cos、new_norm 和 balanced score。
```

这个非常重要，避免后面实验结果出现“dot 最高但不是最好层”时无法解释。

---

### 13.3 主排序建议不要只用 raw dot

手册里目前主排序是：

```text
Visual Top-K：按 S_v_dot 排序
Text Top-K：按 S_t_dot 排序
```

可以保留，但建议把主排序改成“双排序”：

```text
主排序 A：S_dot
主排序 B：S_dot_per_dim 或 S_cos × S_new_norm
```

原因是不同层梯度范数可能差异很大，raw dot 容易被梯度尺度主导。

目前手册已经记录了：

```text
S_dot_per_dim
S_cos
old_norm
new_norm
joint_norm
positive_ratio
zero_grad
```

这很好，但需要明确最终候选层不能只看 raw dot。建议补充：

```text
最终候选层由 S_dot Top-K 与 S_dot_per_dim / S_cos / S_new_norm Top-K 共同确定；
若 raw dot Top-K 与 normalized score Top-K 差异很大，需要优先进入真实 adapter 验证，而不是直接判定最佳层。
```

---

### 13.4 几个诊断指标需要定义清楚

手册里出现了：

```text
v_joint_norm
t_joint_norm
v_positive_ratio
t_positive_ratio
v_zero_grad
t_zero_grad
v_grad_nonzero_ratio
t_grad_nonzero_ratio
```

但没有明确公式。建议补充：

```text
joint_norm_i = ||g_old_i||_2 × ||g_new_i||_2

positive_ratio = # {i | dot(g_old_i, g_new_i) > 0} / N

zero_grad = true if mean_i ||g_new_i||_2 < ε or mean_i ||g_old_i||_2 < ε

grad_nonzero_ratio = mean( |g| > ε )
```

其中：

```text
ε = 1e-12 for fp32
ε = 1e-8 or 1e-7 for fp16/bf16 diagnostics
```

---

### 13.5 forward_equivalence 阈值要按精度调整

手册中写的是：

```text
forward_equivalence_max_diff < 1e-5
```

如果用 fp32，这个可以。

但 LLaVA / BLIP2 很可能用 fp16 或 bf16 跑，`1e-5` 可能过严。

建议改成：

```text
fp32: forward_equivalence_max_diff < 1e-6 或 1e-5
fp16/bf16: forward_equivalence_max_diff < 1e-3
```

同时要求：

```text
model.eval()
disable dropout
同一 batch、同一 precision 下比较
```

---

### 13.6 Token scope 部分基本对，但需要再强调 answer tokens 不能进 text scope

手册已经写了：

```text
排除 visual tokens
排除 padding tokens
排除答案 label tokens
优先只保留 prompt/question tokens
```

这是对的。

这里建议再补一句：

```text
计算 L_old / L_new 时，answer tokens 可以作为 teacher-forcing 输入的一部分，但它们不能被纳入 text Δ_t 的编辑范围；否则会出现对答案 token 自身表征求梯度的 leakage，使选层结果偏向直接操纵答案 token，而不是操纵 prompt/question 表征。
```

这点很关键。尤其是 decoder-only 模型，训练时通常输入 prompt + answer，如果 text scope 不小心包含 answer token，梯度会虚高。

---

### 13.7 old_answer 来源需要加过滤规则

目前要求是：

```text
old answer mapped cases = 30/30
```

还不够。建议补充：

```text
过滤 old_answer 为空的样本；
过滤 old_answer 与 target_new 规范化后相同的样本；
记录 base_correct cases；
记录 old_answer 过长或包含解释性长句的样本；
必要时只取 old_answer 的实体短答案部分。
```

例如 base model 可能输出：

```text
The bridge appears to be the Liberty Bridge.
```

这种答案如果直接作为 old_answer，会导致 old loss 包含大量无关 token。

可以保留原始生成，但最好额外保存：

```text
old_answer_raw
old_answer_normalized
old_answer_short
```

主实验用 `old_answer_short` 更干净。

---

### 13.8 Bridge30 样本太少，只能作为 pilot

30 条样本用于手册测试可以，但如果要把结果写进论文，建议至少补：

```text
Bridge30：debug / pilot
Bridge100 或 Bridge200：正式 proxy set
跨类别 proxy：bridge + building + landmark 等
```

Golden layer 选层本质是 dataset-level 估计，30 条样本可能偶然性较大。

可以报告：

```text
不同 proxy size 下 Top-K 稳定性：
N=30, 50, 100, 200
```

如果 Top-K 层稳定，方法可信度会更高。

---

### 13.9 还需要补充的关键实验

#### 13.9.1 LGA 分数与真实 adapter 扫层效果的相关性实验

这是最重要的。

不能只输出 Top-K，还要证明 Virtual Δh LGA 的分数能预测真实编辑效果。

建议做：

```text
对每个 layer 训练 visual-only adapter；
记录真实 Request / Gen / Loc / Port；
计算 S_v_dot 与真实指标的 Spearman correlation。

对每个 layer 训练 text-only adapter；
记录真实 Request / Gen / Loc / Port；
计算 S_t_dot 与真实指标的 Spearman correlation。
```

至少报告：

```text
corr(S_dot, Request)
corr(S_dot, Generality)
corr(S_dot, Average)
corr(S_new_norm, Request)
corr(S_dot_per_dim, Average)
```

如果相关性高，选层方法才站得住。

---

#### 13.9.2 Top-K 命中率实验

定义 full sweep oracle：

```text
真实 adapter 扫层得到的最佳层 = oracle best layer
```

然后看：

```text
Virtual Δh LGA Top-1 是否命中 oracle best；
Top-3 是否覆盖 oracle best；
Top-5 是否覆盖 oracle best。
```

这个比只报 Top-K 更有说服力。

---

#### 13.9.3 和固定层 / 经验层 / 随机层比较

至少比较：

```text
Random layer
Middle layer
VisEdit-style visual layer
DualEdit fixed layer, e.g. T=16, V=19
Your Virtual Δh LGA layer
Full sweep oracle layer
```

要证明：

```text
Your LGA layer 接近 oracle；
优于 random / fixed / cross-model transferred layer。
```

---

#### 13.9.4 BLIP2 与 LLaVA 的架构差异实验

这是论文第二个创新点的关键支撑。

建议做：

```text
BLIP2 上计算 Visual/Text Top-K；
LLaVA 上计算 Visual/Text Top-K；
比较两者是否位于不同层段；
再用真实 adapter 扫层验证。
```

并且做一个 cross-model transfer：

```text
把 BLIP2 的最佳层迁移到 LLaVA；
把 LLaVA 的最佳层迁移到 BLIP2；
观察性能下降。
```

这样可以支撑：

```text
VLM 编辑层与模型架构相关，不能直接跨模型迁移。
```

---

#### 13.9.5 Request-LGA vs Balanced-LGA 消融

当前手册是 request-only，这是合理的基础版。

但因为真实 adapter 训练包含：

```text
request
generality
locality
portability
```

建议补一个扩展实验：

```text
Request-LGA：只用 request old/new dot
Request+Gen-LGA：加入 generality 正项
Request+Gen+Port-LGA：加入 portability 正项
Balanced-LGA：request + gen + port - locality sensitivity
```

然后比较最终 adapter 效果。

注意：locality 不能作为正向 old/new 编辑目标，而应该作为敏感度惩罚项。

---

#### 13.9.6 token scope 消融

建议至少做：

```text
text_prompt
text_all_nonvisual
last_token_only
visual_all_tokens
visual_top_attention_tokens
```

原因是 DualEdit 用 last-token representation 做 gating，VisEdit 更关注 prompt-relevant visual regions。这里如果只用全部 text prompt tokens，可能不如 last-token 或 question tokens 稳定。

---

### 13.10 手册里“同一候选层同时插入 Δ_v 和 Δ_t”是可以的

手册中写的是：

```text
同一候选层同时插入 Δ_v 和 Δ_t
分别得到视觉分数 S_v(l) 与文本分数 S_t(l)
```

这是可以的，因为 \(Δ_v=Δ_t=0\)，forward 不变。

同时求：

```text
∇_{Δ_v} L
∇_{Δ_t} L
```

相当于在同一次计算图里拿到两个偏导。

但要确保：

```text
visual token indices 和 text token indices 不重叠；
Δ_v 和 Δ_t 都是 leaf tensor；
没有 in-place 操作破坏 autograd graph。
```

---

### 13.11 当前手册可以保留的核心结论

这份手册最适合作为：

```text
Request-only Virtual Δh LGA candidate-layer computation protocol
```

它的定位要写清楚：

```text
它不是最终编辑实验；
它不是 adapter 训练；
它不是直接证明最佳层；
它是用于生成 visual/text candidate layers 的梯度诊断实验。
```

这一点手册里已经写了，是正确的。

---

### 13.12 总体判断

**可以用，但建议修改后再跑正式实验。**

最需要改的地方是：

```text
1. loss 改成 answer-token mean NLL；
2. L_old^{i,l} 改成 L_old^i，梯度才带 layer l；
3. 明确 answer tokens 不能进入 text Δ_t scope；
4. 定义 joint_norm / positive_ratio / zero_grad；
5. forward_equivalence 阈值按 fp32/fp16 调整；
6. 不要只按 raw dot 排序，增加 normalized score 与相关性验证；
7. 增加真实 adapter sweep 相关性、Top-K 命中率、固定层对比实验。
```

最关键的一句话是：

```text
这份手册的公式可以作为 request-only 分模态虚拟 Δh 选层的基础版，但必须通过真实 adapter 扫层验证它和最终编辑效果的相关性；否则它只能说明梯度敏感性，不能直接宣称选出了最佳编辑层。
```

