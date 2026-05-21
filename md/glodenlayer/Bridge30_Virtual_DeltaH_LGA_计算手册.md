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

Bridge30 的 30 条样本用于 debug / pilot 是足够的；如果后续要把 Virtual Δh LGA 作为正式选层方法写入论文，建议追加更大 proxy set 稳定性实验：

```text
Bridge30
Bridge50
Bridge100
Bridge200
跨类别 proxy set：bridge + building + landmark 等
```

正式报告时应检查不同 proxy size 下 Top-K 层是否稳定。

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

old_answer 过滤与规范化规则：

```text
过滤 old_answer 为空的样本
过滤 old_answer 与 target_new 规范化后相同的样本
记录 base_correct cases
记录 old_answer 过长或包含解释性长句的样本
必要时抽取 old_answer 的实体短答案部分
```

建议同时保存：

```text
old_answer_raw
old_answer_normalized
old_answer_short
```

主实验优先使用 `old_answer_short` 计算 old loss，避免长句中无关 token 主导梯度。

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
L_old^i = mean_token_NLL(y_old_i | image_i, prompt_i)
L_new^i = mean_token_NLL(y_new_i | image_i, prompt_i)
```

注意：loss 本身不带层号，层号只体现在对第 \(l\) 层虚拟 Δ 的梯度中。`old_answer` 和 `target_new` 可能是多 token，例如 `Chikugo River Lift Bridge`，因此必须使用 answer token 上的平均 NLL：

```text
只在 answer tokens 上计算 loss
prompt tokens 不参与 loss
padding tokens 不参与 loss
使用 mean NLL，不使用 sum NLL
```

视觉梯度：

```text
g_old_v^{i,l} = ∇_{Δ_v^l} L_old^i
g_new_v^{i,l} = ∇_{Δ_v^l} L_new^i
```

文本梯度：

```text
g_old_t^{i,l} = ∇_{Δ_t^l} L_old^i
g_new_t^{i,l} = ∇_{Δ_t^l} L_new^i
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

dot 分数沿用 Golden Layer 的 old/new 梯度相似性定义，但在 hidden-state / virtual-adapter-output 场景中，其符号与最终 adapter 编辑效果不一定一一对应。若沿着 \(-g_{new}\) 降低 new loss，则 old loss 的一阶变化近似为：

```text
ΔL_old ≈ - dot(g_old, g_new)
```

因此需要同时记录冲突分数：

```text
S_v_conflict(l) = -S_v_dot(l)
S_t_conflict(l) = -S_t_dot(l)
```

解释规则：

```text
dot 大且为正：old/new 梯度方向更一致
dot 为负：降低 new loss 时可能提高 old loss，更像替换旧答案
全负 dot：不能简单取最接近 0 的层作为最佳层
```

最终候选层应同时参考 raw dot、conflict、dot_per_dim、cos、new_norm 与 joint_norm。

诊断指标定义：

```text
joint_norm_i = ||g_old_i||_2 * ||g_new_i||_2
positive_ratio = #{i | dot(g_old_i, g_new_i) > 0} / N
zero_grad = true if mean_i ||g_old_i||_2 < ε or mean_i ||g_new_i||_2 < ε
grad_nonzero_ratio = mean(|g| > ε)
```

推荐阈值：

```text
fp32: ε = 1e-12
fp16/bf16 diagnostics: ε = 1e-8 或 1e-7
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

计算 `L_old` / `L_new` 时，answer tokens 可以作为 teacher-forcing 输入的一部分，但它们不能被纳入 text Δ_t 的编辑范围；否则会对答案 token 自身表征求梯度，造成 leakage，使 text 选层结果偏向直接操纵答案 token，而不是操纵 prompt/question 表征。

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

同样地，BLIP2 的 OPT decoder 输入中如果包含 answer tokens，只允许这些 token 用于 teacher-forcing loss，不允许进入 `text_prompt` 的 Δ_t scope。

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
L_old = mean_answer_token_nll(model, image, prompt, old_answer)
g_old_v, g_old_t = torch.autograd.grad(L_old, [delta_v, delta_t])

L_new = mean_answer_token_nll(model, image, prompt, target_new)
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
s_v_conflict
s_v_dot_per_dim
s_v_cos
v_old_norm
v_new_norm
v_joint_norm
v_grad_nonzero_ratio
s_t_dot
s_t_conflict
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
S_v_conflict
S_v_dot_per_dim
S_v_cos
S_v_old_norm
S_v_new_norm
S_v_joint_norm
v_positive_ratio
v_zero_grad

S_t_dot
S_t_conflict
S_t_dot_per_dim
S_t_cos
S_t_old_norm
S_t_new_norm
S_t_joint_norm
t_positive_ratio
t_zero_grad
```

主排序保留 Golden Layer 风格的 dot 排序：

```text
Visual Top-K：按 S_v_dot 排序
Text Top-K：按 S_t_dot 排序
```

同时必须输出辅助排序：

```text
Visual conflict Top-K：按 S_v_conflict 排序
Text conflict Top-K：按 S_t_conflict 排序
Visual normalized Top-K：按 S_v_dot_per_dim 排序
Text normalized Top-K：按 S_t_dot_per_dim 排序
Visual new-norm Top-K：按 S_v_new_norm 排序
Text new-norm Top-K：按 S_t_new_norm 排序
```

如果 raw dot Top-K 与 normalized / conflict / new-norm Top-K 差异很大，不直接判定最佳层，而是把这些层都放入真实 adapter 验证候选。

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
forward_equivalence_max_diff 满足当前 precision 阈值
```

`forward_equivalence_max_diff` 用于确认：

```text
插入 Δ=0 后，模型 logits 与未插入 Δ 的 base forward 一致。
```

阈值按运行精度设置：

```text
fp32: forward_equivalence_max_diff < 1e-6 或 1e-5
fp16/bf16: forward_equivalence_max_diff < 1e-3
```

比较时必须保证：

```text
model.eval()
disable dropout
同一 batch
同一 precision
同一 tokenizer / processor 输入
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
S_v_conflict
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
S_t_conflict
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
    "visual_conflict": [],
    "visual_dot_per_dim": [],
    "visual_new_norm": [],
    "text_dot": [],
    "text_conflict": [],
    "text_dot_per_dim": [],
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
Visual conflict Top-3
Visual dot-per-dim Top-3
Visual new-norm Top-3
Text dot Top-3
Text conflict Top-3
Text dot-per-dim Top-3
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

同时插入 Δ_v 和 Δ_t 是允许的，因为二者都为 0，forward 不变；但实现必须满足：

```text
visual token indices 和 text token indices 不重叠
Δ_v 和 Δ_t 都是 leaf tensor
没有 in-place 操作破坏 autograd graph
old/new 两次梯度计算互不污染
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
6. raw dot 与 dot_per_dim / conflict / new_norm 的排序差异
7. answer-token mean NLL、text scope、forward equivalence 的实现检查
```

解释时遵守：

```text
Virtual Δh 只说明梯度敏感性
不能把 Δh 梯度高直接写成最终最佳 adapter 层
最终 adapter 层仍需真实训练和评估确认
```

## 12. 后续验证实验

Virtual Δh LGA 只生成候选层。为了验证它是否真的能预测 adapter 编辑效果，建议补充以下实验。

### 12.1 与真实 adapter 扫层效果的相关性

对每个 layer 训练对应 adapter，并记录真实指标：

```text
Request
Generality
Locality
Portability
Average score
```

计算相关性：

```text
corr(S_dot, Request)
corr(S_dot, Generality)
corr(S_dot, Average)
corr(S_conflict, Request)
corr(S_new_norm, Request)
corr(S_dot_per_dim, Average)
```

推荐使用：

```text
Spearman correlation
```

### 12.2 Top-K 命中率

定义 full sweep oracle：

```text
真实 adapter 扫层得到的最佳层 = oracle best layer
```

报告：

```text
Virtual Δh LGA Top-1 是否命中 oracle best
Top-3 是否覆盖 oracle best
Top-5 是否覆盖 oracle best
```

### 12.3 固定层、随机层和经验层对比

至少比较：

```text
Random layer
Middle layer
VisEdit-style visual layer
DualEdit fixed layer，例如 T=16, V=19
Virtual Δh LGA candidate layer
Full sweep oracle layer
```

### 12.4 LLaVA 与 BLIP2 架构差异

分别在 LLaVA 与 BLIP2 上计算：

```text
Visual Top-K
Text Top-K
```

然后做 cross-model transfer：

```text
把 BLIP2 的候选层迁移到 LLaVA
把 LLaVA 的候选层迁移到 BLIP2
```

观察性能是否下降，用于判断候选层是否具有模型架构依赖性。

### 12.5 Request-LGA 与 Balanced-LGA 消融

当前手册是 request-only 基础版。后续可以单独命名扩展实验：

```text
Request-LGA：只用 request old/new dot
Request+Gen-LGA：加入 generality 正项
Request+Gen+Port-LGA：加入 portability 正项
Balanced-LGA：request + gen + port - locality sensitivity
```

注意：locality 不作为正向 old/new 编辑目标，更适合作为敏感度惩罚项。

### 12.6 Token Scope 消融

建议比较：

```text
text_prompt
text_all_nonvisual
last_token_only
visual_all_tokens
visual_top_attention_tokens
```

如果不同 token scope 的 Top-K 差异很大，应优先把差异层放入真实 adapter 验证，而不是只采用单一 scope 的结论。

## 13. 当前待补实验

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

## 14. 实际运行结果：request-only Virtual Δh LGA

运行时间：2026-05-15 20:22:32 - 20:38:25，约 15 分 53 秒。

服务器运行目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga/request_only_20260515_202232
```

本地结果备份：

```text
downloads/Temp/bridge_virtual_delta_h_lga_request_only_20260515_202232/
```

使用脚本：

```text
VisEdit-main/scripts/bridge_vlm_virtual_delta_h_lga_scan.py
```

使用数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json
```

old answer 缓存：

```text
LLaVA: /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl
BLIP2: /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl
```

完成状态：

```text
LLaVA: DONE, 960 sample-layer records
BLIP2: DONE, 960 sample-layer records
ALL_DONE: virtual_delta_h_lga
```

### 14.1 LLaVA 结果

n_request = 30。

#### Visual Dot Top-5

| Rank | Layer | S_v_dot | S_v_conflict | S_v_dot_per_dim | S_v_cos | S_v_new_norm | S_v_positive_ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 9.25302e-07 | -9.25302e-07 | 3.92194e-13 | -0.097467 | 0.00326963 | 0.2 |
| 2 | 31 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | 29 | -1.30368e-06 | 1.30368e-06 | -5.52571e-13 | -0.124949 | 0.00448528 | 0.2 |
| 4 | 28 | -4.61219e-06 | 4.61219e-06 | -1.9549e-12 | -0.136112 | 0.00980497 | 0.133333 |
| 5 | 21 | -1.84128e-05 | 1.84128e-05 | -7.80435e-12 | -0.130758 | 0.0354784 | 0.2 |

#### Visual Conflict Top-5

| Rank | Layer | S_v_conflict | S_v_dot | S_v_dot_per_dim | S_v_new_norm |
|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 0.0366121 | -0.0366121 | -1.55182e-08 | 0.231563 |
| 2 | 3 | 0.036298 | -0.036298 | -1.53851e-08 | 0.229382 |
| 3 | 6 | 0.0362755 | -0.0362755 | -1.53756e-08 | 0.233242 |
| 4 | 0 | 0.0361575 | -0.0361575 | -1.53255e-08 | 0.227354 |
| 5 | 2 | 0.0354967 | -0.0354967 | -1.50454e-08 | 0.226757 |

#### Text Dot Top-5

| Rank | Layer | S_t_dot | S_t_conflict | S_t_dot_per_dim | S_t_cos | S_t_new_norm | S_t_positive_ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 31 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | 30 | -3.94333e-05 | 3.94333e-05 | -6.41818e-10 | -0.12321 | 0.0179594 | 0.133333 |
| 3 | 29 | -7.55421e-05 | 7.55421e-05 | -1.22953e-09 | -0.101752 | 0.0261309 | 0.133333 |
| 4 | 28 | -0.000158742 | 0.000158742 | -2.58369e-09 | -0.12972 | 0.0335077 | 0.1 |
| 5 | 27 | -0.000193585 | 0.000193585 | -3.1508e-09 | -0.105599 | 0.0416924 | 0.1 |

#### Text Conflict Top-5

| Rank | Layer | S_t_conflict | S_t_dot | S_t_dot_per_dim | S_t_new_norm |
|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 17.0037 | -17.0037 | -0.000276753 | 2.75488 |
| 2 | 1 | 12.7567 | -12.7567 | -0.000207628 | 2.16715 |
| 3 | 2 | 7.71789 | -7.71789 | -0.000125617 | 1.65476 |
| 4 | 3 | 5.35143 | -5.35143 | -8.71001e-05 | 1.37541 |
| 5 | 4 | 2.83921 | -2.83921 | -4.62112e-05 | 1.05493 |

LLaVA 的第 31 层在 visual/text 两侧均为 zero-gradient 层，`S_v_new_norm=0` 且 `S_t_new_norm=0`。因此正式选候选层时不能把第 31 层作为有效 dot Top 层；过滤 zero-gradient 后：

```text
Visual Dot Top-5: 30, 29, 28, 21, 27
Text Dot Top-5: 30, 29, 28, 27, 26
```

### 14.2 BLIP2 结果

n_request = 30。

#### Visual Dot Top-5

| Rank | Layer | S_v_dot | S_v_conflict | S_v_dot_per_dim | S_v_cos | S_v_new_norm | S_v_positive_ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 0.000326262 | -0.000326262 | 3.9827e-09 | 0.0343719 | 0.0842449 | 0.533333 |
| 2 | 29 | 0.000128479 | -0.000128479 | 1.56835e-09 | 0.0129187 | 0.11102 | 0.533333 |
| 3 | 28 | 8.89346e-05 | -8.89346e-05 | 1.08563e-09 | 0.000679928 | 0.131608 | 0.6 |
| 4 | 31 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 27 | -0.000161666 | 0.000161666 | -1.97346e-09 | -0.0144629 | 0.160031 | 0.4 |

#### Visual Conflict Top-5

| Rank | Layer | S_v_conflict | S_v_dot | S_v_dot_per_dim | S_v_new_norm |
|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 0.00856369 | -0.00856369 | -1.04537e-07 | 0.436867 |
| 2 | 9 | 0.00854854 | -0.00854854 | -1.04352e-07 | 0.437038 |
| 3 | 8 | 0.00832789 | -0.00832789 | -1.01659e-07 | 0.439813 |
| 4 | 12 | 0.00818738 | -0.00818738 | -9.99436e-08 | 0.427949 |
| 5 | 11 | 0.00816788 | -0.00816788 | -9.97055e-08 | 0.431833 |

#### Text Dot Top-5

| Rank | Layer | S_t_dot | S_t_conflict | S_t_dot_per_dim | S_t_cos | S_t_new_norm | S_t_positive_ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 24 | 7.27348e-05 | -7.27348e-05 | 2.18554e-09 | 0.00216297 | 0.0532141 | 0.5 |
| 2 | 26 | 1.32633e-05 | -1.32633e-05 | 3.98537e-10 | -0.00672028 | 0.0236486 | 0.533333 |
| 3 | 27 | 5.61173e-07 | -5.61173e-07 | 1.68622e-11 | -0.0223758 | 0.0195884 | 0.466667 |
| 4 | 31 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 30 | -4.03541e-07 | 4.03541e-07 | -1.21256e-11 | -0.0566748 | 0.00831287 | 0.433333 |

#### Text Conflict Top-5

| Rank | Layer | S_t_conflict | S_t_dot | S_t_dot_per_dim | S_t_new_norm |
|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 0.0279262 | -0.0279262 | -8.39129e-07 | 0.767477 |
| 2 | 2 | 0.0262371 | -0.0262371 | -7.88374e-07 | 0.794623 |
| 3 | 7 | 0.0260141 | -0.0260141 | -7.81673e-07 | 0.662611 |
| 4 | 0 | 0.0260098 | -0.0260098 | -7.81545e-07 | 0.851369 |
| 5 | 6 | 0.0252587 | -0.0252587 | -7.58975e-07 | 0.694616 |

BLIP2 的第 31 层同样为 zero-gradient 层，正式选候选层时应过滤。过滤 zero-gradient 后：

```text
Visual Dot Top-5: 30, 29, 28, 27, 26
Text Dot Top-5: 24, 26, 27, 30, 29
```

### 14.3 初步结论

本次 Virtual Δh LGA 的 request-only 扫层给出的有效候选层集中在高层：

```text
LLaVA visual: 30
LLaVA text: 30
BLIP2 visual: 30
BLIP2 text: 24
```

需要注意的是，dot Top 与 conflict Top 差异很大。Dot Top 更偏向 old/new 梯度方向一致的层；conflict Top 反映降低 new loss 时更可能拉高 old loss 的层。后续如果用该结果指导真实 adapter，应优先把 zero-gradient 过滤后的 dot Top 层作为主候选，同时把 conflict Top 层作为替换式编辑风险诊断层。

### 14.4 Hook 位置一致性核对

本节核对 Virtual Δh LGA 与真实 request-only adapter 扫层的挂载位置是否一致。

结论：

```text
真实 adapter 扫层位置：after layer l，也就是 layer l forward output 上挂载
Virtual Δh LGA 位置：after layer l，也就是同一个 layer l forward output 上取梯度
二者 hook 位置一致，不需要重跑
```

依据如下：

```text
真实训练：
editor/vllm_editors/vead/vead.py 使用 edit_layer.register_forward_hook(...)
adapter_hook 的输入是 outpt，并返回修改后的 outpt
因此真实 adapter 是作用在 layer l output，而不是 layer l input

Virtual Δh：
scripts/bridge_vlm_virtual_delta_h_lga_scan.py 同样使用 layer_module.register_forward_hook(...)
retain_hidden_hook 捕获的是 output hidden，并对该 output hidden retain_grad
因此 Virtual Δh 计算的也是 layer l output 梯度
```

需要额外注意：

```text
现有真实 VEAD adapter 只改视觉 token 区间：
layer_outpt[:, vt_begin:vt_end] = img_reps + delta_h

因此 visual Top-K 可以直接对齐当前真实视觉 adapter 扫层。
text Top-K 是在同一 after-layer-l 位置上对文本 prompt token 的虚拟诊断，
用于后续 text-branch adapter 或 dual-branch adapter 设计参考；
它不是当前视觉 adapter 扫层中已经训练过的真实 text adapter。
```
