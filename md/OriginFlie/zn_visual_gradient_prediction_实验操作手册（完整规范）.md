# ZN Visual Gradient Prediction 实验手册

本手册用于指导后续 **不同模型、不同数据集** 的视觉梯度层定位实验。核心目标是：在不训练 adapter、不改模型权重的前提下，通过 Virtual Delta-H 视觉梯度计算每个候选层的 old/new answer 梯度关系，并按 `Ours-Direct` 主公式得到视觉候选层排序，再把候选层交给真实编辑实验验证。

本手册是 `Ours-Direct` 的专项执行手册；总手册 `md/Location/6edit_layer_localization_candidate_methods_revised.md` 中的 Ours 定义必须与本手册保持一致。主实验不执行 Pre 偏移，不使用 raw dot 直接选层，也不使用 rel/gen/avg 多公式作为主候选。

参考来源：

- `md/glodenlayer/Bridge30_Virtual_DeltaH_LGA_计算手册_补充版.md`
- `downloads/Temp/evqa_proxy500_blip2_virtual_delta_h_lga_20260604_140903/virtual_delta_h_lga_layer_scores.csv`
- `md/glodenlayer/BLIP2_Proxy500_Visual_LGA_FormulaRankings.md`

## 1. 任务定义

给定一个 VLM、一个编辑数据集和一组候选层，计算每层视觉 token hidden state 上的旧知识梯度与新知识梯度。

对第 `i` 个样本、第 `l` 层：

```text
L_old^i = mean_token_NLL(y_old_i | image_i, prompt_i)
L_new^i = mean_token_NLL(y_new_i | image_i, prompt_i)

g_old_v^{i,l} = ∇_{Δ_v^l} L_old^i
g_new_v^{i,l} = ∇_{Δ_v^l} L_new^i
```

其中：

- `Δ_v^l` 是插入在第 `l` 层视觉 token hidden state 上的零扰动。
- 只对 `Δ_v^l` 求梯度，不更新模型参数。
- `L_old` 和 `L_new` 都只在 answer token 上算平均 NLL，prompt token 和 padding token 不参与 loss。

## 2. 字段映射规范

每个数据集必须先明确旧知识和新知识字段，不能让脚本自动猜。

| 数据集/任务 | prompt 字段 | image 字段 | 旧知识字段（主实验） | 新知识字段 |
|---|---|---|---|---|
| E-VQA proxy500/pilot500 | `src` | `image` | `model_pred` | `alt` |
| E-VQA full | `src` | `image` | `model_pred` | `alt` |
| Bridge request-only | `request.prompt` | `request.image` | old answers file | `request.target_new` |
| 其他数据集 | 必须显式记录 | 必须显式记录 | 必须显式记录 | 必须显式记录 |

主实验的旧知识字段统一使用当前冻结模型确定性解码得到的 `model_pred`。如果某数据集已有 `pred` 字段，且确认它来自同一个冻结模型、同一输入模板和同一解码配置，可另做 `Ours-Direct-AltPred` 附加分析；不得把 `pred` 结果混入 `Ours-Direct` 主排序。

E-VQA 转换规则：

```text
request.prompt = src
request.image = image
request.target_new = alt
old_answers.jsonl.answer = model_pred
old_answers.jsonl.question = src
old_answers.jsonl.image_id = Path(image).stem
```

若运行 `Ours-Direct-AltPred` 附加分析，可将 `old_answers.jsonl.answer` 替换为数据集已有 `pred`，但输出目录、方法名和结果表必须显式带 `AltPred`。

硬性检查：

```text
total_cases == selected_cases
mapped_cases == selected_cases
missing_cases == []
```

如果同一 `image_id` 对应多个问题，`old_answers.jsonl` 必须保留 `question` 字段，让 loader 按 question 匹配，而不是只按 image_id 取第一条。

## 3. 模型与层范围

不同模型的视觉 token scope 和候选层路径不同，必须在实验配置里写清楚。

| 模型 | 候选层示例 | 视觉 token scope | hook 位置 |
|---|---|---|---|
| BLIP2-OPT | OPT decoder `0-31` | Q-Former 输出投影后的 visual prefix/query tokens | `language_model.model.decoder.layers.{l}` |
| LLaVA | LLM decoder `0-31` 或实际层数 | projector 输出后插入 LLM 的 image tokens | LLM decoder block |
| InstructBLIP | LLM decoder 层 | Q-Former/visual prefix tokens | LLM decoder block |
| Qwen2.5-VL | LLM decoder 或 merger 后层 | image/video tokens 或 visual prefix | 以模型 tokenizer/processor 映射为准 |

原则：

- `visual_token_start`、`visual_token_end` 必须由模型实际输入映射读取，不手写固定值。
- 文本 scope 必须排除 visual tokens、padding tokens、answer loss tokens。
- 本手册主任务是视觉候选层定位；文本指标可同时输出，但视觉排序以 `S_v_*` 为主。

## 4. 计算流程

### Step 1：加载模型并冻结

```python
model.eval()
for p in model.parameters():
    p.requires_grad_(False)
```

必须记录：

```text
base_requires_grad_params = 0
adapter_used = false
optimizer_used = false
gradient_target = virtual_delta_h_at_layer_hidden_state
```

### Step 2：遍历候选层

每次只在一个候选层 `l` 插入零扰动：

```text
layers = 0-31  # 示例，按模型实际层数调整
```

### Step 3：插入视觉零扰动

伪代码：

```python
h = hidden_states
h_v = h[:, visual_start:visual_end, :]
delta_v = torch.zeros_like(h_v, requires_grad=True)
h[:, visual_start:visual_end, :] = h_v + delta_v
```

实现要求：

- 不要原地破坏 autograd graph。
- 优先使用项目已有 hook 写法。
- 每个 old/new loss 推荐各跑一次 forward，避免 `retain_graph` 引起混乱。

### Step 4：分别计算 old/new 梯度

```python
L_old = answer_mean_nll(model, image, prompt, old_answer)
g_old_v = autograd.grad(L_old, delta_v)

L_new = answer_mean_nll(model, image, prompt, target_new)
g_new_v = autograd.grad(L_new, delta_v)
```

禁止事项：

```text
不调用 optimizer.step()
不保存 adapter checkpoint
不改变模型权重
不把 old/new 拼在一次 loss 里混算
```

## 5. 视觉梯度指标定义

每层聚合输出 12 个视觉原始指标。设：

```text
old = flat(g_old_v^{i,l})
new = flat(g_new_v^{i,l})
dot_i = sum(old * new)
old_norm_i = ||old||_2
new_norm_i = ||new||_2
joint_i = old_norm_i * new_norm_i
numel_i = number_of_elements(old)
eps = 1e-8
```

| 指标 | 公式/定义 | 含义 |
|---|---|---|
| `S_v_dot` | `mean_i dot_i` | 旧/新知识视觉梯度点积；raw LGA 诊断分数，不作为 Ours 主排序。 |
| `S_v_conflict` | `mean_i (-dot_i)` | dot 反向冲突诊断；越大表示 old/new 点积越负。 |
| `S_v_dot_per_dim` | `mean_i dot_i / numel_i` | 维度归一化点积，缓解 token 数/维度差异。 |
| `S_v_cos` | `mean_i dot_i / (joint_i + eps)` | 梯度方向相似度，不直接看梯度大小。 |
| `S_v_old_norm` | `mean_i old_norm_i` | 旧知识对该层视觉 hidden state 的敏感度。 |
| `S_v_new_norm` | `mean_i new_norm_i` | 新知识写入该层视觉 hidden state 的梯度强度。 |
| `S_v_joint_norm` | `mean_i joint_i` | old/new 共同梯度强度。 |
| `S_v_positive_ratio` | `count(dot_i > 0) / n` | 方向一致样本比例。 |
| `S_v_zero_grad` | `S_v_old_norm < eps or S_v_new_norm < eps` | 是否近似零梯度层。 |
| `S_v_old_nonzero_ratio` | `mean_i mean(abs(old) > eps)` | 旧知识梯度非零元素比例。 |
| `S_v_new_nonzero_ratio` | `mean_i mean(abs(new) > eps)` | 新知识梯度非零元素比例。 |
| `median_v_dot` | `median_i dot_i` | 样本级 dot 中位数，抗异常样本。 |
| `S_v_neg_cos` | `max(0, -S_v_cos)` | Ours 主公式中的方向冲突项。 |
| `S_v_depth2` | `((l + 1) / L)^2` | Ours 主公式中的深度权重。 |
| `S_ours` | `S_v_neg_cos * S_v_new_norm * S_v_depth2` | Ours-Direct 主排序分数。 |

对应文本指标用 `S_t_*` 命名，定义完全相同，只是 token scope 换成 prompt text tokens。

这里的 \(L\) 表示合法候选层数量；若层编号为 \(0,\ldots,L-1\)，则深度项使用 \((l+1)/L\)，避免第 0 层深度因子为 0。

## 6. 输出文件规范

每次实验必须输出以下文件：

```text
sample_virtual_delta_h_scores.jsonl
virtual_delta_h_lga_layer_scores.csv
topk_virtual_delta_h_layers.json
old_answer_mapping_report.json
run_config.json
summary.md
```

### 6.1 sample JSONL

每个样本、每层一行，必须包含：

```text
case_id
image_id
layer
layer_path
old_answer
target_new
old_loss
new_loss
visual_token_start
visual_token_end
text_token_count
answer_loss_position_count
s_v_dot
s_v_conflict
s_v_dot_per_dim
s_v_cos
v_old_norm
v_new_norm
v_joint_norm
v_old_nonzero_ratio
v_new_nonzero_ratio
```

### 6.2 layer CSV

每层一行，必须包含视觉与文本聚合指标：

```text
model
layer
n_request
S_v_dot
S_v_conflict
S_v_dot_per_dim
S_v_cos
S_v_old_norm
S_v_new_norm
S_v_joint_norm
S_v_positive_ratio
S_v_zero_grad
S_v_old_nonzero_ratio
S_v_new_nonzero_ratio
median_v_dot
S_v_neg_cos
S_v_depth2
S_ours
S_t_dot
S_t_conflict
S_t_dot_per_dim
S_t_cos
S_t_old_norm
S_t_new_norm
S_t_joint_norm
S_t_positive_ratio
S_t_zero_grad
```

### 6.3 mapping report

必须检查：

```text
total_cases
mapped_cases
missing_cases
duplicate_image_ids
old_answer_source
```

合格条件：

```text
mapped_cases == total_cases
missing_cases == []
```

`duplicate_image_ids` 不一定是错误，但必须确认 loader 使用 question 匹配旧答案。

## 7. 候选层排序规则

### 7.1 Ours-Direct 主排序

不要只按 raw `S_v_dot` 下结论。raw dot 很容易被浅层梯度范数主导，因此 Ours 主实验只按下式直接选 adapter 插入层：

```text
S_v_neg_cos(l) = max(0, -S_v_cos(l))
S_v_depth2(l) = ((l + 1) / L)^2
S_ours(l) = S_v_neg_cos(l) * S_v_new_norm(l) * S_v_depth2(l)
candidate_layers = TopK_l S_ours(l)
```

该 Top-K 就是主实验候选层，不做平滑区间识别，不做拐点扩展，不做 Pre 偏移。

### 7.2 有效层过滤

以下层不得进入主候选：

```text
S_v_zero_grad = true
S_v_new_norm is nonfinite
S_v_cos is nonfinite
visual_token_start/end empty
```

如果有效层为空，该“数据集 × 模型”组合标记为：

```text
status = unavailable
failure_reason = no_valid_ours_direct_layer
```

### 7.3 诊断排序

以下排序必须输出用于解释和排错，但不作为 Ours-Direct 主候选：

| 排序 | 公式 | 用途 |
|---|---|---|
| raw visual dot | `S_v_dot` 降序 | 检查是否被浅层范数主导。 |
| dot conflict | `S_v_conflict` 降序 | 观察 old/new 点积反向层。 |
| normalized dot | `S_v_dot_per_dim` 降序 | 消除维度规模差异。 |
| cosine | `S_v_cos` 升序和降序都报告 | 升序用于查看方向冲突；降序只作方向一致性诊断。 |
| new strength | `S_v_new_norm` 降序 | 查看新知识写入强度。 |

历史版本中的 `M_rel/M_gen/M_avg` 和 `M_elbow` 只能作为附加诊断或消融，不进入当前 Ours-Direct 主表。

## 8. 结果解释规则

### 8.1 raw dot 不是最终编辑层

若 raw `S_v_dot` Top-K 集中在浅层，例如 `0,1,2,3,4`，通常说明浅层视觉 hidden state 对 old/new answer 都敏感，但不一定是最适合编辑的层。

必须同时查看：

```text
S_v_cos
S_v_neg_cos
S_v_new_norm
S_v_positive_ratio
S_v_zero_grad
S_v_depth2
S_ours
```

### 8.2 zero grad 层不能作为候选层

若：

```text
S_v_zero_grad = true
```

则该层不进入候选层排序，即使某些反排公式把它排到前面，也只能作为诊断信息。

### 8.3 负 cos 深层要谨慎

如果深层出现：

```text
S_v_cos < 0
S_v_dot < 0
```

说明 old/new 方向冲突。它可能对替换旧答案有意义，也是 Ours 主公式中的有效信号之一；但单独的负 cos 不应直接解释为最佳编辑层，必须结合 `S_v_new_norm` 与深度项，并进入真实 adapter 验证。

## 9. 跨模型实验模板

每次新模型/新数据集必须填写：

```text
model_name:
dataset_name:
data_path:
image_root:
sample_count:
prompt_field:
image_field:
old_answer_field:
new_answer_field:
layer_range:
layer_path_template:
visual_token_scope_rule:
text_token_scope_rule:
answer_loss_rule: mean_token_NLL
zero_grad_eps: 1e-8
output_dir:
ours_rank_metric: negative_cosine_times_new_norm_times_depth2
old_field_policy: model_pred_main_pred_only_ablation
```

必须记录：

```text
CUDA_VISIBLE_DEVICES / Slurm job id
node name
model checkpoint path
script commit or local script path
run_config.json
```

## 10. 服务器执行建议

优先使用 Slurm 或已有 allocation，不要直接打断正在训练的节点。

示例：E-VQA proxy500 / BLIP2 / g08

```text
train json:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json

image root:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images

output:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy500_blip2_virtual_delta_h_lga_YYYYMMDD_HHMMSS
```

如果节点名是 `g08`，作业内部通常使用：

```text
CUDA_VISIBLE_DEVICES=0
--device cuda:0
```

不要把节点名 `g08` 误解成物理 GPU id `8`。

## 11. 报告模板

每次实验结束后写一份 Markdown 报告，至少包含：

```text
1. 数据与字段映射
   - old = ?
   - new = ?
   - prompt = ?
   - image = ?

2. 运行配置
   - model
   - layers
   - n_request
   - visual token scope
   - answer loss rule

3. 映射检查
   - total_cases
   - mapped_cases
   - missing_cases
   - duplicate_image_ids 是否可解释

4. 核心指标表
   - S_v_dot
   - S_v_cos
   - S_v_neg_cos
   - S_v_new_norm
   - S_v_depth2
   - S_ours
   - S_v_positive_ratio
   - S_v_zero_grad

5. 候选层排序
   - Ours-Direct Top-K by S_ours
   - raw dot / conflict / cosine / new_norm 诊断排序

6. 结论
   - 推荐验证层 Top-K
   - 不推荐层及原因
   - 需要真实 adapter 验证的问题
```

## 12. BLIP2 proxy500 参考输出

本节作为 sanity check，不作为其他模型的固定结论。

实验：

```text
model = blip2-opt-2.7b
dataset = E-VQA proxy500/pilot500
old = pred
new = alt
n_request = 500
layers = 0-31
```

原始 visual top：

```text
top_by_dot = 0, 1, 3, 2, 4
top_by_conflict = 28, 29, 30, 31, 27
top_by_new_norm = 0, 1, 2, 3, 4
```

历史深度加权公式排序（旧版本 sanity check，不作为当前 Ours-Direct 主排序）：

| 目标 | Top10 |
|---|---|
| `rel` | 17, 18, 16, 15, 19, 14, 13, 20, 21, 22 |
| `gen` | 18, 17, 19, 16, 21, 22, 20, 15, 14, 13 |
| `avg` | 18, 17, 16, 19, 15, 14, 21, 20, 22, 13 |

解释：

- raw dot 选择浅层，说明浅层视觉表示对 old/new answer 梯度都很强，但不能直接作为编辑层。
- 当前 Ours-Direct 应重新输出 `S_ours` 与 `TopK_l S_ours(l)`；不得直接把旧版 `rel/gen/avg` 排序写成主结果。
- 这些层仍然只是候选层，最终要用真实编辑训练和 full/proxy eval 验证。

## 13. 最小验收清单

实验完成前必须逐项检查：

```text
[ ] old/new 字段映射明确，且写入报告
[ ] answer loss 是 mean token NLL
[ ] base model 参数冻结，base_requires_grad_params=0
[ ] adapter_used=false
[ ] mapped_cases == total_cases
[ ] missing_cases == []
[ ] visual_token_start/end 非空或可解释 mixed
[ ] 每层 n_request 一致
[ ] zero_grad 层未进入最终候选
[ ] 输出 sample JSONL、layer CSV、topk JSON、run_config
[ ] 主候选只按 S_ours 排序，不执行 Pre 偏移
[ ] 同时报告 raw dot、cos、neg_cos、new_norm、positive_ratio、S_ours 和诊断排序
[ ] 最终结论写成“候选层”，不写成“已证明最佳层”
```

## 14. 推荐结论表述

正确表述：

```text
根据 Ours-Direct 的 Virtual Delta-H 视觉梯度主分数 `S_ours = max(0, -S_v_cos) × S_v_new_norm × ((l+1)/L)^2`，模型在该数据集上的视觉候选层集中于 Lx/Ly/Lz。该结论表示这些层在 old/new answer 的视觉 hidden-state 梯度关系上更符合候选层公式，需要进一步通过真实 adapter sweep 验证。
```

避免表述：

```text
梯度最高层就是最终最佳编辑层。
raw S_v_dot Top1 就是 visual golden layer。
旧版 rel/gen/avg 排序就是当前 Ours-Direct 主结果。
只凭 proxy500 train 梯度证明 full E-VQA 最优层。
```
