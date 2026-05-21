# Bridge30 Adapter-LGA Golden Layer 操作流程

## 0. 文件定位

本文件是新版操作手册，用于替代“直接对原模型 MLP 参数求梯度”的旧版 LGA 实验设计。

旧文件保留不动：

```text
md/glodenlayer/Bridge30_Golden_Layer_Operation_Manual.md
```

本文件核心修改：

```text
旧版：对原模型第 L 层参数 theta_L 求梯度。
新版：对第 L 层 adapter 的可训练参数 phi_L 求梯度。
```

原因：

```text
原始 LGA 假设直接编辑原模型参数。
当前实验实际训练的是 adapter。
因此 golden layer 应该估计“哪一层 adapter 更适合承载编辑”，而不是“哪一层原模型 MLP 更适合被直接改写”。
```

## 1. 方法定义

参考公式文件：

```text
md/glodenlayer/adapter_LGA公式_完整回答.md
```

adapter-aware LGA 主公式：

```text
G*_adapter = argmax_L S_adapter-LGA(L)
```

其中：

```text
S_adapter-LGA(L)
= sum_i dot(
    grad_phi_L L_old^{i,L},
    grad_phi_L L_new^{i,L}
  )
```

符号含义：

```text
theta   = 冻结的基础 VLM 参数
phi_L   = 插入第 L 层的 adapter 参数
x_i     = (image_i, prompt_i)
y_old_i = 未编辑基础模型 old answer
y_new_i = request.target_new
```

关键区别：

```text
不是 grad_theta_L
而是 grad_phi_L
```

## 2. 实验目标

本流程计算：

```text
bridge30 上 LLaVA 与 BLIP2 的 adapter-aware LGA candidate layers
```

本流程仍不直接决定最终编辑层。最终编辑层仍由：

```text
暴力扫层训练 adapter + 编辑指标评估
```

来确定。

本流程要验证：

```text
1. adapter-LGA 是否比原模型 MLP-LGA 更接近 adapter 暴力扫层结果。
2. LLaVA 的 adapter 候选层是否更偏浅层或中浅层。
3. BLIP2 的 adapter 候选层是否更偏中层或中后层。
4. 层选择是否与 VLM 架构和 adapter 插入机制相关。
```

## 3. 数据与 old answer

主数据：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

只使用：

```text
item.request.image
item.request.prompt
item.request.target_new
```

不参与 adapter-LGA 的字段：

```text
generality
locality
portability
```

old answer 优先读取缓存：

```text
LLaVA:
Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl

BLIP2:
Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl
```

如果 BLIP2 old answer 不存在，先生成一次并缓存。adapter-LGA 正式运行时读取缓存，不重复生成。

映射规则仍按：

```text
image_id = stem(request.image)
```

## 4. 候选层与 adapter 对象

### 4.1 LLaVA

基础模型文本层：

```text
language_model.model.layers.{0..31}
```

adapter 插入位置：

```text
language_model.model.layers.{L}
```

真实配置模板：

```text
VisEdit-main/configs/vead/llava-v1.5-7b.yaml
```

关键字段：

```text
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
```

候选层：

```text
0-31
```

### 4.2 BLIP2

基础模型文本 decoder 层：

```text
language_model.model.decoder.layers.{0..31}
```

adapter 插入位置：

```text
language_model.model.decoder.layers.{L}
```

真实配置模板：

```text
VisEdit-main/configs/vead/blip2-opt-2.7b.yaml
```

关键字段：

```text
llm_hidden_size: 2560
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.decoder.layers.{}"
```

候选层：

```text
0-31
```

本版仍不计算：

```text
BLIP2 Q-Former adapter
BLIP2 connector / language_projection adapter
BLIP2 vision encoder adapter
```

## 5. 每个候选层的模型构造

对每个候选层 `L`，构造一个临时 adapter 模型：

```text
M_{theta, phi_L}
```

其中：

```text
theta = base VLM 参数，全部 requires_grad=False
phi_L = 第 L 层 adapter 参数，requires_grad=True
```

实现要求：

```text
1. 每次只打开一个候选层 adapter。
2. 其它层不插 adapter，或插入但 requires_grad=False 且不参与统计。
3. 不加载已训练 checkpoint。
4. 不做 optimizer.step。
5. 只 forward + backward 读取 phi_L 梯度。
```

adapter 初始化：

```text
1. 使用与真实训练一致的 adapter 结构。
2. 使用固定随机种子。
3. 每个候选层使用同一初始化策略，避免随机初始化差异主导层排名。
```

建议：

```text
seed = 2026
每构造一个候选层 adapter 前重新 set_seed(seed)
```

这样不同层的 `phi_L` 初始分布一致，层分数主要来自该层 hidden state 与 adapter 交互，而不是随机初始化差异。

## 6. adapter edit signal 设置

VEAD / VisEdit adapter 不是一个裸 MLP，它依赖 edit signal。

对第 `i` 个 request：

```text
e_i = edit_signal(I_i, Q_i, y_new_i)
```

其中 `y_new_i = request.target_new`。

重要要求：

```text
old loss 和 new loss 必须使用同一个 edit signal e_i。
```

也就是说：

```text
L_old^{i,L} = CE(M_{theta,phi_L}(I_i,Q_i; e_i), y_old_i)
L_new^{i,L} = CE(M_{theta,phi_L}(I_i,Q_i; e_i), y_new_i)
```

不要这样做：

```text
old loss 使用 old answer 构造 edit signal
new loss 使用 target_new 构造 edit signal
```

原因：

```text
如果 old/new loss 使用不同 edit signal，那么梯度差异同时包含“目标答案变化”和“adapter 条件输入变化”，不再是同一个 phi_L 下的 old/new 梯度比较。
```

本实验统一：

```text
adapter edit signal always comes from request.target_new
```

## 7. 单样本 adapter-LGA 计算

对每个样本 `i`：

```text
x_i = (image_i, prompt_i)
y_old_i = cached base-model answer
y_new_i = request.target_new
e_i = edit_signal(image_i, prompt_i, y_new_i)
```

prompt 统一：

```text
原始 prompt: What is the name of this bridge?
实际 prompt: What is the name of this bridge? The answer is:
```

old loss：

```text
L_old^{i,L} = CE(M_{theta,phi_L}(x_i; e_i), y_old_i)
```

new loss：

```text
L_new^{i,L} = CE(M_{theta,phi_L}(x_i; e_i), y_new_i)
```

loss 计算要求：

```text
1. 只对 answer tokens 计算 CE。
2. image tokens 不参与 loss。
3. prompt tokens 不参与 loss。
4. prompt 部分 label 设置为 -100。
5. base VLM 不更新。
6. adapter 不更新，只读取梯度。
```

## 8. 梯度计算部分

这是本文件相对旧版最重要的修改。

旧版错误对象：

```text
theta_L = params(base_model_layer_L)
g_old_i_L = grad_theta_L L_old_i
g_new_i_L = grad_theta_L L_new_i
```

新版正确对象：

```text
phi_L = params(adapter_L)
g_old_i_L = grad_phi_L L_old^{i,L}
g_new_i_L = grad_phi_L L_new^{i,L}
```

单样本 adapter dot：

```text
s_adapter_dot_i_L = dot(g_old_i_L, g_new_i_L)
```

展开：

```text
s_adapter_dot_i_L
= sum_j g_old_{i,L,j} * g_new_{i,L,j}
```

其中：

```text
j = adapter 参数 phi_L 的维度索引
```

bridge30 聚合：

```text
S_adapter_dot_L = sum_i s_adapter_dot_i_L
```

adapter-aware golden layer：

```text
G*_adapter = argmax_L S_adapter_dot_L
```

## 9. 诊断指标

adapter cosine：

```text
s_adapter_cos_i_L
= dot(g_old_i_L, g_new_i_L)
  / (norm(g_old_i_L) * norm(g_new_i_L) + eps)

S_adapter_cos_L = mean_i s_adapter_cos_i_L
```

adapter gradient norm：

```text
adapter_old_grad_norm_L = mean_i norm(g_old_i_L)
adapter_new_grad_norm_L = mean_i norm(g_new_i_L)
adapter_joint_norm_L    = mean_i (norm(g_old_i_L) * norm(g_new_i_L))
```

adapter norm ratio：

```text
adapter_norm_ratio_L
= adapter_joint_norm_L
  / (mean_k adapter_joint_norm_k + eps)
```

主选层只使用：

```text
S_adapter_dot_L
```

诊断指标只用于解释：

```text
1. dot 是否由方向一致性贡献。
2. dot 是否被 adapter 梯度范数放大。
3. 某层 adapter 梯度是否异常。
```

## 10. conflict 分析作为补充，不作为主公式

因为 bridge 是实体替换任务，old answer 与 target_new 可能互斥，所以可以额外报告：

```text
adapter_conflict_dot_L = -S_adapter_dot_L
adapter_conflict_cos_L = -S_adapter_cos_L
```

用途：

```text
解释暴力扫层中哪些层更容易产生替换效果。
```

但必须明确：

```text
adapter_conflict_dot 不是原始 adapter-LGA 主公式。
主公式仍是 argmax S_adapter_dot_L。
```

输出时建议分两栏：

```text
Adapter-LGA top-k by dot
Adapter conflict top-k by -dot / -cos
```

## 11. 脚本设计

审核通过后建议新增脚本：

```text
VisEdit-main/scripts/bridge_vlm_adapter_lga_scan.py
```

脚本职责：

```text
1. 读取 bridge30 edit json。
2. 读取 cached old answer jsonl。
3. 每个候选层 L 构造一个单层 adapter 模型 M_{theta,phi_L}。
4. 冻结 base VLM 参数 theta。
5. 只打开 adapter_L，并设置 phi_L.requires_grad=True。
6. 对每个 request 构造 target_new edit signal e_i。
7. 用同一个 e_i 分别计算 old loss 和 new loss。
8. 对 phi_L 求梯度。
9. 输出 adapter dot、cos、norm、norm ratio、rank。
10. 输出 dot top-k 与 conflict top-k。
```

脚本不做：

```text
不训练 adapter。
不 optimizer.step。
不加载编辑 checkpoint。
不计算 generality / locality / portability。
不对 base VLM 原始 MLP 参数求梯度。
不计算 BLIP2 Q-Former / connector。
```

## 12. 输出目录

LLaVA：

```text
server_results/bridge_vlm_adapter_lga_llava_train30/
```

BLIP2：

```text
server_results/bridge_vlm_adapter_lga_blip2_train30/
```

每个目录包含：

```text
run_config.json
old_answer_mapping_report.json
sample_adapter_layer_scores.jsonl
adapter_lga_layer_scores.csv
topk_adapter_layers.json
summary.md
```

## 13. 输出字段

### 13.1 adapter_lga_layer_scores.csv

字段：

```csv
model,layer,adapter_type,adapter_path,n_request,S_adapter_dot,S_adapter_cos,adapter_old_grad_norm,adapter_new_grad_norm,adapter_joint_norm,adapter_norm_ratio,dot_rank,cos_rank,norm_rank,adapter_lga_selected_by_dot,conflict_dot_rank,conflict_cos_rank
```

示例：

```csv
llava-v1.5-7b,1,VisionEditAdaptor,language_model.model.layers.1,30,385.20,0.431,3.11,4.02,12.50,1.08,1,2,5,true,32,31
```

### 13.2 topk_adapter_layers.json

字段：

```json
{
  "model": "llava-v1.5-7b",
  "data": "bridge30",
  "main_score": "S_adapter_dot",
  "gradient_target": "adapter_parameters_phi_L",
  "base_model_trainable": false,
  "adapter_trainable": true,
  "diagnostic_scores": [
    "S_adapter_cos",
    "adapter_old_grad_norm",
    "adapter_new_grad_norm",
    "adapter_joint_norm",
    "adapter_norm_ratio"
  ],
  "top_by_adapter_dot": {
    "top1": 1,
    "top3": [1, 0, 6],
    "top5": [1, 0, 6, 4, 11]
  },
  "top_by_adapter_conflict_dot": {
    "top1": 1,
    "top3": [1, 7, 6],
    "top5": [1, 7, 6, 5, 8]
  },
  "selected_adapter_golden_layer": {
    "by": "S_adapter_dot",
    "top1": 1
  }
}
```

## 14. 拟执行命令

### 14.1 LLaVA

```bash
cd VisEdit-main
python scripts/bridge_vlm_adapter_lga_scan.py \
  --model-name llava-v1.5-7b \
  --vead-config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl \
  --layers 0-31 \
  --adapter-type vision \
  --score-mode request_only_adapter_lga \
  --main-score adapter_dot \
  --diagnostics adapter_cos,adapter_grad_norm,adapter_norm_ratio \
  --seed 2026 \
  --output-dir ../server_results/bridge_vlm_adapter_lga_llava_train30
```

### 14.2 BLIP2

```bash
cd VisEdit-main
python scripts/bridge_vlm_adapter_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --vead-config-path configs/vead/blip2-opt-2.7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl \
  --layers 0-31 \
  --adapter-type vision \
  --score-mode request_only_adapter_lga \
  --main-score adapter_dot \
  --diagnostics adapter_cos,adapter_grad_norm,adapter_norm_ratio \
  --seed 2026 \
  --output-dir ../server_results/bridge_vlm_adapter_lga_blip2_train30
```

## 15. 验收检查

每个模型运行后检查：

```text
1. adapter_lga_layer_scores.csv 有 32 行。
2. 每层 n_request = 30。
3. dot_rank 为 1-32 且不重复。
4. conflict_dot_rank 为 1-32 且不重复。
5. selected_adapter_golden_layer 等于 dot_rank = 1 的层。
6. old_answer_mapping_report.json 中 missing_cases 为空。
7. 日志中 base VLM trainable 参数数量为 0。
8. 日志中 adapter trainable 参数数量大于 0。
```

必须额外检查：

```text
确认梯度来自 adapter 参数 phi_L，而不是 base layer theta_L。
```

建议在日志中打印：

```text
gradient_target = adapter_parameters_phi_L
base_requires_grad_params = 0
adapter_requires_grad_params = <positive integer>
```

## 16. 与旧版 MLP-LGA 对比

旧版输出：

```text
server_results/bridge_vlm_lga_llava_train30/
server_results/bridge_vlm_lga_blip2_train30/
```

新版输出：

```text
server_results/bridge_vlm_adapter_lga_llava_train30/
server_results/bridge_vlm_adapter_lga_blip2_train30/
```

报告时必须分开命名：

```text
MLP-LGA:
对 frozen base model layer 参数 theta_L 求梯度。

Adapter-LGA:
对候选层 adapter 参数 phi_L 求梯度。
```

预期判断：

```text
如果 Adapter-LGA 更接近暴力扫层结果，说明旧版 MLP-LGA 与 adapter 编辑机制不匹配。
如果 Adapter-LGA 仍与暴力扫层差距大，则说明仅靠 request old/new 梯度还不足以预测 adapter 最优层，需要引入训练动态或编辑后指标。
```

## 17. 最终报告文件

运行完成后生成：

```text
md/glodenlayer/Bridge30_Adapter_LGA_Golden_Layer_Result.md
```

报告结构：

```markdown
# Bridge30 Adapter-LGA Golden Layer 结果

## 1. 实验设置

数据：
模型：
adapter 类型：
候选层：
old answer 来源：
gradient target：phi_L
main score：S_adapter_dot
diagnostics：S_adapter_cos, adapter_joint_norm, adapter_norm_ratio

## 2. LLaVA Adapter-LGA 结果

| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Rank |
|---:|---:|---:|---:|---:|---:|---:|

## 3. BLIP2 Adapter-LGA 结果

| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Rank |
|---:|---:|---:|---:|---:|---:|---:|

## 4. 与旧版 MLP-LGA 对比

| Model | MLP-LGA top-5 | Adapter-LGA top-5 | Brute-force best | 说明 |
|---|---|---|---:|---|

## 5. Adapter conflict 分析

| Model | Adapter conflict top-5 | Brute-force best | 是否更接近 |
|---|---|---:|---|

## 6. 结论

结论：
证据：
限制：
下一步：
```

## 18. 审核前不执行

审核前不做：

```text
不新增 Python 脚本。
不运行服务器实验。
不重新计算 LLaVA / BLIP2。
不覆盖旧版 Bridge30_Golden_Layer_Operation_Manual.md。
不覆盖旧版 MLP-LGA 结果。
```
