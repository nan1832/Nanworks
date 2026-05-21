# Bridge30 Golden Layer 计算操作流程

## 0. 实验定位

本流程严格遵循原始 Golden Layer / LGA 论文的计算思想，只用编辑请求本身计算层级梯度分数。

本流程计算：

```text
bridge30 上 LLaVA 与 BLIP2 的 LGA predicted golden layer
```

本流程不直接决定最终编辑层。最终编辑层仍由：

```text
暴力扫层训练 adapter + 编辑指标评估
```

来确定。

固定术语：

```text
LGA predicted golden layer：用 LGA 梯度方法预测出的候选层。
true edit layer：暴力扫层后由编辑指标确定的实际最优编辑层。
```

实验要验证：

```text
1. BLIP2 的有效编辑层更可能位于中层或中后层。
2. LLaVA 的有效编辑层可能位于浅层，也可能存在中层候选。
3. 层选择与模型架构相关。
4. 不能把 BLIP2 的扫层结论直接迁移到 LLaVA。
```

## 1. 方法来源

Golden Layer 方法来源：

```text
pdf/2026-golden-layer选择原文.pdf
```

原文方法为 Layer Gradient Analysis, 简称 LGA。

本操作手册的公式识别优先级：

```text
1. md/glodenlayer/LGA指标计算公式_完整回答.md
2. md/glodenlayer/LGA指标计算公式.pdf
```

原因：

```text
Markdown 版本中的 LaTeX 公式结构更完整，适合作为实现依据。
PDF 版本作为同内容排版参考，不用 PDF 文本抽取结果覆盖 Markdown 公式。
```

原始文本 LLM 形式：

```text
G* = argmax_L sum_i grad_theta_L loss(Q_i, K_i) dot grad_theta_L loss(Q_i, K'_i)
```

其中：

```text
Q_i  = query
K_i  = old knowledge / old answer
K'_i = new target knowledge / new answer
L    = candidate layer
```

迁移到 VLM 后：

```text
Q_i  -> (I_i, Q_i)
K_i  -> base VLM old answer
K'_i -> request.target_new
```

直观解释：

```text
如果某一层在 old answer loss 和 new target loss 上的梯度内积更大，
说明该层对从旧答案迁移到新目标答案更关键，因此更可能是 golden layer。
```

本实验按公式文件采用 4 类指标：

```text
1. 主指标：gradient inner product / dot，用于最终 LGA 选层。
2. 诊断指标：cosine similarity / cos，用于检查梯度方向一致性。
3. 诊断指标：gradient norm，用于检查层梯度响应强度。
4. 诊断指标：norm-dominance ratio，用于检查 dot 是否被异常梯度范数主导。
```

最终 predicted golden layer 只由 `S_lga_dot` 决定：

```text
G* = argmax_L S_lga_dot(L)
```

`S_lga_cos`、gradient norm、norm ratio 必须一起输出，但只用于解释和诊断，不作为主选层依据。

## 2. 只使用 request 计算 LGA

本版 LGA 只使用：

```text
item.request
```

参与 LGA 的字段：

```text
request.image
request.prompt
request.target_new
```

不参与 LGA 计算的字段：

```text
generality.text_rephrase
generality.image_rephrase
locality.text_loc
locality.image_loc
portability
```

原因：

```text
1. 原始 LGA 论文用 query 的 old knowledge 与 new target knowledge 梯度计算层分数。
2. generality / locality / portability 是编辑效果评估维度，不是原始 LGA 层分数的必要输入。
3. 如果把 generality / locality / portability 混入 LGA，会变成自定义扩展方法，不再是严格复现原始 LGA。
4. 本实验当前目标是验证 LGA predicted layer 与 brute-force true edit layer 的关系，因此先保持 LGA 定义纯净。
```

后续可以做扩展实验，但必须单独命名，例如：

```text
VLM-LGA-request-only
VLM-LGA-request-plus-generality
VLM-LGA-with-locality-penalty
```

当前主实验只做：

```text
VLM-LGA-request-only
```

## 3. 数据来源

GLDv2 数据来源论文：

```text
pdf/gldv2_CVPR_2020原文.pdf
```

bridge30 编辑数据：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

辅助参考文件：

```text

Ten_Classes/bridge/bridge_train/30_bridge_train.jsonl
```

主实验使用：

```text
edit_30_bridge_train_only_vis.json
```

原因：

```text
1. 每个样本都有 request.image、request.prompt、request.target_new。
2. target_new 是桥实体名，适合做实体识别型编辑层估计。
3. 与当前 only-vis 暴力扫层实验的数据形式一致。
```

## 4. old answer 来源

### 4.1 LLaVA

LLaVA 的未编辑基础模型实体识别结果已经存在：

```text
Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl
```

文件格式示例：

```json
{"image_id": "GLDv2_0173d637a2257753", "question": "What is this bridge called?", "answer": "Golden gate"}
```

因此 LLaVA LGA 不重复生成 old answer，而是读取已有结果：

```text
y_old_i = cached answer matched by image_id
```

### 4.2 BLIP2

BLIP2 也应优先读取已有未编辑基础模型生成结果。

默认约定路径：

```text
Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl
```

如果该文件不存在：

```text
先单独生成一次 BLIP2 before-edit entity recognition，并缓存为该文件。
LGA 主流程复跑时读取缓存，不重复生成。
```

### 4.3 old answer 映射规则

因为已有结果没有 `case_id`，需要按图像 ID 映射。

从 request image 提取：

```text
request.image = train/images/GLDv2_084bb592a552d066.jpg
image_id      = GLDv2_084bb592a552d066
```

映射 key：

```text
image_id
```

如果同一个 `image_id` 有多条实体识别问题：

```text
1. 优先选择 question 与 request.prompt 最接近的记录。
2. 如果仍有多条，选择第一条。
3. 在 old_answer_mapping_report.json 中记录 duplicate_image_ids。
```

如果某个 request 找不到 old answer：

```text
1. 记录 missing_cases。
2. 不静默跳过。
3. 若 missing_cases 非空，先补齐 old answer 后再正式运行 LGA。
```

## 5. 候选层设置

本实验只计算文本解码器部分的梯度。

### 5.1 LLaVA

配置文件：

```text
VisEdit-main/configs/p_track/llava-v1.5-7b.yaml
```

候选层：

```text
language_model.model.layers.{0..31}
```

主计算模块：

```text
language_model.model.layers.{l}.mlp
```

可选补充模块：

```text
language_model.model.layers.{l}.self_attn
language_model.model.layers.{l}
```

默认候选层：

```text
0-31
```

### 5.2 BLIP2

配置文件：

```text
VisEdit-main/configs/p_track/blip2-opt-2.7b.yaml
```

候选层：

```text
language_model.model.decoder.layers.{0..31}
```

主计算模块：

```text
language_model.model.decoder.layers.{l}.fc2
```

可选补充模块：

```text
language_model.model.decoder.layers.{l}.self_attn
language_model.model.decoder.layers.{l}
```

默认候选层：

```text
0-31
```

本版明确不计算：

```text
BLIP2 Q-Former
BLIP2 language_projection / connector
BLIP2 vision encoder
```

原因：

```text
1. 当前暴力扫层实验主要对应语言解码器层。
2. LLaVA 与 BLIP2 都先限制在文本解码器，便于比较层位差异。
3. 如果 BLIP2 decoder-only LGA 无法解释结果，再单独设计 Q-Former / connector 实验。
```

## 6. 单样本 LGA 计算

对每个 bridge30 request 样本：

```text
x_i = (image_i, prompt_i)
y_old_i = cached base-model answer
y_new_i = request.target_new
```

prompt 统一为：

```text
原始 prompt: What is the name of this bridge?
实际 prompt: What is the name of this bridge? The answer is:
```

如果 prompt 已经包含 `The answer is:`，不重复追加。

old loss：

```text
L_old_i = CE(model(image_i, prompt_i), y_old_i)
```

new loss：

```text
L_new_i = CE(model(image_i, prompt_i), y_new_i)
```

关键要求：

```text
1. 只对 answer tokens 计算 CE。
2. image tokens 不参与 loss。
3. prompt tokens 不参与 loss。
4. prompt 部分 label 设置为 -100。
5. 模型不做参数更新，只做梯度读取。
```

## 7. 层梯度与 LGA 分数

对每个候选层 `l`：

```text
theta_l = params(module_l)
g_old_i_l = grad_theta_l L_old_i
g_new_i_l = grad_theta_l L_new_i
```

主指标：gradient inner product / dot。

```text
s_lga_dot_i_l = dot(g_old_i_l, g_new_i_l)
              = transpose(g_old_i_l) * g_new_i_l
```

bridge30 聚合：

```text
S_lga_dot_l = sum_i s_lga_dot_i_l
```

如果实现中同时输出 mean dot，只能作为辅助阅读字段；主排名使用 sum dot。由于 bridge30 每层样本数相同，sum 和 mean 的排序一致，但公式记录以 sum 为准。

LGA predicted golden layer：

```text
G* = argmax_l S_lga_dot_l
```

诊断指标一：cosine similarity / cos。

```text
s_lga_cos_i_l = dot(g_old_i_l, g_new_i_l) / (norm(g_old_i_l) * norm(g_new_i_l) + eps)
S_lga_cos_l = mean_i s_lga_cos_i_l
```

cosine 不单独产生 golden layer。它用于判断 dot 高分层是否真的方向一致：

```text
dot 高 + cosine 高：该层更可信。
dot 高 + cosine 低：该层可能主要被梯度范数放大。
```

诊断指标二：gradient norm。

```text
old_grad_norm_l   = mean_i norm(g_old_i_l)
new_grad_norm_l   = mean_i norm(g_new_i_l)
joint_grad_norm_l = mean_i (norm(g_old_i_l) * norm(g_new_i_l))
```

诊断指标三：norm-dominance ratio。

```text
norm_ratio_l = joint_grad_norm_l / (mean_k joint_grad_norm_k + eps)
```

其中 `k` 遍历所有候选层。解释：

```text
norm_ratio_l ≈ 1：该层梯度范数正常。
norm_ratio_l >> 1：该层梯度范数明显偏大，可能主导 dot。
norm_ratio_l << 1：该层梯度响应较弱。
```

本实验排序：

```text
dot_rank = rank by S_lga_dot descending
cos_rank = rank by S_lga_cos descending
norm_rank = rank by joint_grad_norm descending
```

如果 dot rank 与 cos rank 差异很大：

```text
1. 仍以 dot rank 作为 LGA 主结果。
2. 报告 cosine、joint_grad_norm、norm_ratio。
3. 分析 dot 高分是否来自方向一致，还是来自梯度范数放大。
```

## 8. 脚本设计

审核通过后新增：

```text
VisEdit-main/scripts/bridge_vlm_lga_scan.py
```

脚本职责：

```text
1. 读取 bridge30 edit json。
2. 读取已有 before-edit old answer jsonl。
3. 建立 image_id -> old_answer 映射。
4. 只构造 request LGA 样本。
5. 加载 LLaVA 或 BLIP2 基础模型。
6. 只对文本解码器候选层计算梯度。
7. 输出 S_lga_dot、S_lga_cos、梯度范数、norm_ratio、dot_rank、cos_rank、norm_rank。
8. 以 top-k by dot 作为 LGA predicted layers，同时输出 top-k by cos 作为诊断参考。
```

脚本不做：

```text
不训练 adapter。
不加载编辑 checkpoint。
不计算编辑后指标。
不使用 generality。
不使用 locality。
不使用 portability。
不计算 BLIP2 Q-Former / connector。
不重复生成已有 old answer。
```

## 9. 输出目录

LLaVA：

```text
server_results/bridge_vlm_lga_llava_train30/
```

BLIP2：

```text
server_results/bridge_vlm_lga_blip2_train30/
```

每个目录包含：

```text
run_config.json
old_answer_mapping_report.json
sample_layer_scores.jsonl
lga_layer_scores.csv
topk_layers.json
summary.md
```

## 10. 输出字段

### 10.1 lga_layer_scores.csv

字段：

```csv
model,layer,module_kind,module_path,n_request,S_lga_dot,S_lga_cos,old_grad_norm,new_grad_norm,joint_grad_norm,norm_ratio,dot_rank,cos_rank,norm_rank,lga_selected_by_dot
```

示例：

```csv
llava-v1.5-7b,1,mlp,language_model.model.layers.1.mlp,30,385.20,0.431,3.11,4.02,12.50,1.08,1,2,5,true
```

### 10.2 topk_layers.json

字段：

```json
{
  "model": "llava-v1.5-7b",
  "data": "bridge30",
  "module_kind": "mlp",
  "main_score": "S_lga_dot",
  "diagnostic_scores": ["S_lga_cos", "old_grad_norm", "new_grad_norm", "joint_grad_norm", "norm_ratio"],
  "top_by_dot": {
    "top1": 1,
    "top3": [1, 0, 6],
    "top5": [1, 0, 6, 4, 11]
  },
  "top_by_cos": {
    "top1": 1,
    "top3": [1, 6, 0],
    "top5": [1, 6, 0, 11, 4]
  },
  "selected_golden_layer": {
    "by": "S_lga_dot",
    "top1": 1
  }
}
```

### 10.3 old_answer_mapping_report.json

字段：

```json
{
  "old_answer_source": "Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl",
  "total_cases": 30,
  "mapped_cases": 30,
  "missing_cases": [],
  "duplicate_image_ids": []
}
```

## 11. 执行前检查

检查 bridge 数据：

```powershell
Get-ChildItem Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

检查 LLaVA old answer：

```powershell
Get-ChildItem Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl
```

检查 BLIP2 old answer：

```powershell
Get-ChildItem Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl
```

如果 BLIP2 old answer 文件不存在：

```text
先补一次 BLIP2 before-edit entity recognition，再运行 BLIP2 LGA。
```

检查配置：

```powershell
Get-ChildItem VisEdit-main/configs/p_track/llava-v1.5-7b.yaml
Get-ChildItem VisEdit-main/configs/p_track/blip2-opt-2.7b.yaml
```

服务器检查：

```bash
nvidia-smi
ls models/llava-v1.5-7b-hf
ls models/blip2-opt-2.7b
```

## 12. 拟执行命令

### 12.1 LLaVA

```bash
cd VisEdit-main
python scripts/bridge_vlm_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/p_track/llava-v1.5-7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl \
  --old-answer-key image_id \
  --layers 0-31 \
  --module-kind mlp \
  --score-mode request_only_lga \
  --main-score dot \
  --diagnostics cos,grad_norm,norm_ratio \
  --output-dir ../server_results/bridge_vlm_lga_llava_train30
```

### 12.2 BLIP2

```bash
cd VisEdit-main
python scripts/bridge_vlm_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --config-path configs/p_track/blip2-opt-2.7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl \
  --old-answer-key image_id \
  --layers 0-31 \
  --module-kind mlp \
  --score-mode request_only_lga \
  --main-score dot \
  --diagnostics cos,grad_norm,norm_ratio \
  --output-dir ../server_results/bridge_vlm_lga_blip2_train30
```

## 13. 验收检查

每个模型运行后检查：

```bash
test -f ../server_results/bridge_vlm_lga_llava_train30/lga_layer_scores.csv
test -f ../server_results/bridge_vlm_lga_llava_train30/topk_layers.json
test -f ../server_results/bridge_vlm_lga_llava_train30/summary.md
```

CSV 检查：

```text
1. 应有 32 行候选层。
2. n_request 应为 30。
3. dot_rank 应从 1 到 32 不重复。
4. cos_rank 应从 1 到 32 不重复。
5. norm_rank 应从 1 到 32 不重复。
6. `lga_selected_by_dot=true` 只能出现在 dot_rank = 1 的层。
7. topk_layers.json 的 selected_golden_layer 必须等于 CSV 中 dot_rank = 1 的层。
```

old answer 映射检查：

```text
missing_cases 必须为空，或者在 summary.md 中解释。
duplicate_image_ids 必须有处理策略。
```

## 14. 与暴力扫层结果对比

LGA 运行后，不直接说 LGA top1 就是最终编辑层。

必须和暴力扫层编辑指标对比。

### 14.1 LLaVA 当前扫层结果

当前表格中最强层：

```text
layer 1
Entity strict = 54.29%
Entity loose = 62.86%
Open-end strict = 16.71%
Open-end loose = 25.58%
```

其它候选：

```text
layer 0:  Entity strict = 35.71%, Open-end strict = 15.30%
layer 6:  Entity strict = 40.00%, Open-end strict = 14.65%
layer 11: Entity strict = 52.86%, Open-end strict = 7.20%
```

对比方式：

```text
看 LLaVA dot top-k 是否命中 layer 1。
看 LLaVA cosine、joint_grad_norm、norm_ratio 是否支持 dot top-k 的可靠性。
如果 dot top-k 命中 layer 1，说明 request-only LGA 能解释当前 LLaVA 暴力扫层结果。
如果 dot 与 cos 排名不同，仍以 dot 为 LGA 主结果，并分析差异是否来自梯度范数。
```

### 14.2 BLIP2 当前扫层结果

已测：

```text
layer 2, 4, 15, 19
```

strict：

```text
Entity strict 全部为 0
Open-end strict 全部为 0
```

loose exploratory best：

```text
layer 19
Entity loose = 4/70 = 5.71%
Open-end loose = 13/778 = 1.67%
```

解释：

```text
BLIP2 当前不能严格确定 true edit layer。
如果 BLIP2 LGA dot top-k 偏向 15/19 或中后层，可作为“架构相关层位差异”的支持证据。
cosine、joint_grad_norm、norm_ratio 只用于解释该 dot top-k 是否可信。
如果 BLIP2 LGA top-k 偏浅层，需要重新检查 decoder-only LGA 是否遗漏 Q-Former / connector 信息。
```

## 15. 架构相关性判断

支持假设的结果：

```text
1. LLaVA dot top-k 覆盖浅层/中浅层，尤其 0/1/6/11。
2. LLaVA 暴力扫层最强为 layer 1。
3. BLIP2 dot top-k 偏中层/中后层。
4. BLIP2 与 LLaVA 的 LGA top-k 深度分布明显不同。
```

不支持假设的结果：

```text
1. LLaVA 和 BLIP2 LGA top-k 都集中同一深度区间。
2. LLaVA LGA top-k 完全集中深层，无法解释 layer 1 的暴力扫层优势。
3. BLIP2 LGA top-k 完全集中浅层，且后续 BLIP2 strict 扫层也支持浅层。
```

深度区间：

```text
shallow = 0-7
middle  = 8-19
late    = 20-31
```

## 16. 最终报告文件

运行完成后生成：

```text
md/glodenlayer/Bridge30_Golden_Layer_Result.md
```

报告结构：

```markdown
# Bridge30 Golden Layer 结果

## 1. 实验设置

数据：
模型：
候选层：
模块：
old answer 来源：
main score：S_lga_dot
diagnostics：S_lga_cos, old_grad_norm, new_grad_norm, joint_grad_norm, norm_ratio

## 2. LLaVA LGA 结果

| Dot Rank | Layer | S_lga_dot | S_lga_cos | Joint Norm | Norm Ratio | n_request |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | - | - | - | - | - | 30 |
| 2 | - | - | - | - | - | 30 |
| 3 | - | - | - | - | - | 30 |

## 3. BLIP2 LGA 结果

| Dot Rank | Layer | S_lga_dot | S_lga_cos | Joint Norm | Norm Ratio | n_request |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | - | - | - | - | - | 30 |
| 2 | - | - | - | - | - | 30 |
| 3 | - | - | - | - | - | 30 |

## 4. Dot 主结果可靠性诊断

| Model | Dot Top-1 | Cos Rank of Dot Top-1 | Norm Ratio | 诊断 |
|---|---:|---:|---:|---|
| LLaVA | - | - | - | - |
| BLIP2 | - | - | - | - |

## 5. LGA 与暴力扫层对比

| Model | LGA Dot Top-3 | Diagnostic Notes | Brute-force best | 结论 |
|---|---|---|---:|---|
| LLaVA | - | - | 1 | - |
| BLIP2 | - | - | 19* | - |

*BLIP2 layer 19 目前只是 loose exploratory best，strict true edit layer 尚未确定。

## 6. 架构相关性分析

结论：
证据：
限制：
下一步：
```

## 17. 审核前不执行

审核前不做：

```text
不新增 Python 脚本。
不运行 LLaVA。
不运行 BLIP2。
不训练 adapter。
不修改 bridge 数据。
不重复生成已有 LLaVA old answer。
不使用 generality / locality / portability 计算 LGA。
不计算 BLIP2 Q-Former / connector。
```
