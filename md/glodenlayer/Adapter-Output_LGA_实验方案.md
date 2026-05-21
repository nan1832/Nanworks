你要做的是一个**新增补充实验：Adapter-Output LGA**。

它和你现在手册里的 **Adapter-Parameter LGA** 不一样。你现有手册算的是对候选层 adapter 参数 \(\phi_L\) 的梯度，用来判断“哪一层 adapter 参数更适合承载编辑”；手册里也明确写了新版是对第 \(L\) 层 adapter 的可训练参数 \(\phi_L\) 求梯度，而不是对原模型层参数 \(\theta_L\) 求梯度。

你现在要做的 **Adapter-Output LGA**，算的是：

> **adapter 挂在模型第 \(L\) 层时，它输出的视觉表征修正量 \(\Delta h_{vis}^{L}\) 是否最适合驱动 old answer → target_new 的变化。**

---

# 1. 这个实验回答什么问题？

它回答的是：

```text
adapter 挂在 LLaVA / BLIP2 哪一层时，
adapter 输出的视觉表征修正量最适合改变实体识别结果？
```

这里的层 \(L\) 仍然是：

```text
LLaVA / BLIP2 的模型层，也就是 adapter 挂载层
```

不是 adapter 内部自己的第几层。

---

# 2. 核心思想

假设第 \(L\) 层原始视觉 hidden state 是：

\[
h_{vis}^{i,L}
\]

第 \(L\) 层 adapter 输出一个视觉修正量：

\[
\Delta h_{vis}^{i,L}
=
A_{\phi_L}(h_{vis}^{i,L}, e_i)
\]

然后修改后的视觉表征是：

\[
\tilde h_{vis}^{i,L}
=
h_{vis}^{i,L}
+
\Delta h_{vis}^{i,L}
\]

Adapter-Output LGA 不是对 \(\phi_L\) 求梯度，而是对：

\[
\Delta h_{vis}^{i,L}
\]

或者：

\[
\tilde h_{vis}^{i,L}
\]

求梯度。

我建议你第一版优先算：

\[
\Delta h_{vis}^{i,L}
\]

因为它更直接表示：

> adapter 实际注入了什么视觉修改量。

---

# 3. 主公式

对第 \(i\) 个 request：

\[
x_i=(I_i,Q_i)
\]

\[
y_i^{old}=\text{base model old answer}
\]

\[
y_i^{new}=\text{request.target\_new}
\]

adapter edit signal：

\[
e_i=edit\_signal(I_i,Q_i,y_i^{new})
\]

old loss：

\[
\mathcal{L}_{old}^{i,L}
=
CE(M_{\theta,\phi_L}(x_i;e_i),y_i^{old})
\]

new loss：

\[
\mathcal{L}_{new}^{i,L}
=
CE(M_{\theta,\phi_L}(x_i;e_i),y_i^{new})
\]

对 adapter 输出的视觉修正量求梯度：

\[
g_{old,\Delta h}^{i,L}
=
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{old}^{i,L}
\]

\[
g_{new,\Delta h}^{i,L}
=
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{new}^{i,L}
\]

单样本分数：

\[
s_{\Delta h-dot}^{i,L}
=
\left(
g_{old,\Delta h}^{i,L}
\right)^\top
g_{new,\Delta h}^{i,L}
\]

层级聚合：

\[
S_{\Delta h-dot}(L)
=
\sum_{i=1}^{N}
\left(
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{old}^{i,L}
\right)^\top
\left(
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{new}^{i,L}
\right)
\]

如果严格按照 LGA 的“最大内积”原则：

\[
G^*_{\text{Adapter-Output}}
=
\arg\max_L
S_{\Delta h-dot}(L)
\]

---

# 4. 但你的实体替换任务还要额外看两个指标

因为你的任务是：

```text
把错误实体名 old answer 改成正确实体名 target_new
```

old answer 和 target_new 经常是竞争关系，所以 dot 可能偏负。  
因此除了主 LGA dot，还要输出：

## 4.1 Adapter-output conflict score

\[
S_{\Delta h-conflict}(L)
=
-
S_{\Delta h-dot}(L)
\]

它表示：

```text
哪一层 adapter 输出更容易产生 old answer 与 target_new 的替换冲突
```

如果你发现暴力扫层最佳层更接近 conflict top-k，而不是 dot top-k，这很正常。

---

## 4.2 Adapter-output new-target sensitivity

\[
S_{\Delta h-new-norm}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{new}^{i,L}
\right\|_2
\]

它回答的是：

```text
target_new 对哪一层 adapter 输出的视觉修改量最敏感
```

这个指标对你的“视觉实体识别”尤其重要。

---

# 5. 实验流程

## Step 1：数据不变

继续用：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

只使用：

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

old answer 仍然用 before-edit cache。

---

## Step 2：候选层不变

LLaVA：

```text
language_model.model.layers.0-31
```

BLIP2：

```text
language_model.model.decoder.layers.0-31
```

这里的 \(L\) 是：

```text
adapter 挂载到基础模型的哪一层
```

---

## Step 3：每次只构造一个候选层 adapter

对每个候选层 \(L\)，构造：

\[
M_{\theta,\phi_L}
\]

要求：

```text
base VLM 参数 θ 冻结
第 L 层 adapter 存在
adapter 参数 φ_L 可以 requires_grad=True，但不更新
不加载训练好的 checkpoint
不做 optimizer.step
固定 seed
```

注意：虽然这个实验最终读的是 adapter output 的梯度，但为了让 adapter output 在计算图里，通常可以让 adapter 参数保持 `requires_grad=True`。只是你不读取 \(\phi_L\) 的梯度，也不更新它。

---

## Step 4：捕获 adapter 输出

你需要在 adapter forward 里捕获：

```text
adapter 输出的视觉修正量 Δh_vis^L
```

如果 adapter forward 返回的是 residual delta：

```text
delta_h = adapter(...)
```

就捕获：

\[
\Delta h_{vis}^{L}
\]

如果 adapter forward 返回的是修改后的 hidden：

```text
h_tilde = h + adapter(...)
```

就优先同时记录：

```text
delta_h
h_tilde
```

第一版建议主用：

```text
delta_h_vis
```

脚本里需要类似：

```python
captured = {}

def adapter_output_hook(module, inputs, output):
    out = output[0] if isinstance(output, tuple) else output
    out.retain_grad()
    captured["adapter_output"] = out
```

如果 output 是全序列 hidden，需要切视觉 token：

```python
delta_h_vis = captured["adapter_output"][:, vt_start:vt_end, :]
```

如果 output 本身已经只包含 visual tokens，就不用切。

---

## Step 5：old loss 和 new loss 必须使用同一个 edit signal

这一点和你的 Adapter-Parameter LGA 手册一致。

对每个样本：

\[
e_i=edit\_signal(I_i,Q_i,y_i^{new})
\]

old loss：

\[
\mathcal{L}_{old}^{i,L}
=
CE(M_{\theta,\phi_L}(x_i;e_i), y_i^{old})
\]

new loss：

\[
\mathcal{L}_{new}^{i,L}
=
CE(M_{\theta,\phi_L}(x_i;e_i), y_i^{new})
\]

不要用：

```text
old loss 用 old answer 构造 edit signal
new loss 用 target_new 构造 edit signal
```

否则你比较的就不是同一个 adapter 输出条件下 old/new 梯度差异。

---

## Step 6：反向传播到 adapter output

对 old loss backward 后读取：

\[
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{old}^{i,L}
\]

对 new loss backward 后读取：

\[
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{new}^{i,L}
\]

伪代码逻辑：

```python
# old
loss_old.backward()
g_old = captured["adapter_output"].grad[:, vt_start:vt_end, :].detach()

zero_grad_and_clear_capture()

# new
loss_new.backward()
g_new = captured["adapter_output"].grad[:, vt_start:vt_end, :].detach()
```

注意：

```text
old 和 new 要分别 forward + backward
不要在同一个 captured tensor 上混淆梯度
每次 backward 后清空梯度
```

---

# 6. 输出指标

每层输出这些字段：

```csv
model,
layer,
adapter_path,
n_request,
S_out_dot,
S_out_cos,
S_out_new_norm,
S_out_old_norm,
S_out_joint_norm,
out_positive_ratio,
median_out_dot,
out_dot_rank,
out_conflict_rank,
out_new_norm_rank,
out_cos_rank
```

公式如下。

## 6.1 Dot

\[
S_{out-dot}(L)
=
\sum_i
(g_{old,out}^{i,L})^\top
g_{new,out}^{i,L}
\]

## 6.2 Cosine

\[
S_{out-cos}(L)
=
\frac{1}{N}
\sum_i
\frac{
(g_{old,out}^{i,L})^\top g_{new,out}^{i,L}
}{
\|g_{old,out}^{i,L}\|_2
\|g_{new,out}^{i,L}\|_2
+\epsilon
}
\]

## 6.3 New norm

\[
S_{out-new-norm}(L)
=
\frac{1}{N}
\sum_i
\|g_{new,out}^{i,L}\|_2
\]

## 6.4 Old norm

\[
S_{out-old-norm}(L)
=
\frac{1}{N}
\sum_i
\|g_{old,out}^{i,L}\|_2
\]

## 6.5 Joint norm

\[
S_{out-joint-norm}(L)
=
\frac{1}{N}
\sum_i
\|g_{old,out}^{i,L}\|_2
\|g_{new,out}^{i,L}\|_2
\]

## 6.6 Positive ratio

\[
P_{out+}(L)
=
\frac{1}{N}
\sum_i
\mathbf{1}
[
s_{out-dot}^{i,L}>0
]
\]

## 6.7 Median dot

\[
MedianOutDot(L)
=
median_i(s_{out-dot}^{i,L})
\]

---

# 7. 排名和解释

你最后不要只看一个 top1，建议同时看三组 top-k。

## 7.1 LGA-style top-k

```text
top_by_out_dot
```

对应：

\[
\arg\max_L S_{out-dot}(L)
\]

解释：

```text
old answer 与 target_new 在 adapter 输出上的梯度方向最一致 / 最不冲突
```

---

## 7.2 Conflict top-k

```text
top_by_out_conflict_dot
```

对应：

\[
\arg\max_L -S_{out-dot}(L)
\]

解释：

```text
target_new 更新最可能压制 old answer 的层
```

这个对实体替换任务非常有用。

---

## 7.3 New-norm top-k

```text
top_by_out_new_norm
```

对应：

\[
\arg\max_L S_{out-new-norm}(L)
\]

解释：

```text
target_new 对 adapter 输出视觉修改量最敏感的层
```

---

# 8. 建议新增脚本

建议新增：

```text
VisEdit-main/scripts/bridge_vlm_adapter_output_lga_scan.py
```

它可以借鉴两个脚本：

```text
bridge_vlm_adapter_lga_scan.py
bridge_vlm_visual_hidden_lga_scan.py
```

脚本职责：

```text
1. 读取 bridge30 request 数据
2. 读取 old answer cache
3. 每次构造单层 adapter M_{theta, phi_L}
4. 冻结 base VLM
5. 不训练 adapter
6. 用 target_new 构造 edit signal
7. 捕获 adapter 输出 Δh_vis^L
8. 分别计算 old loss 和 new loss
9. 反向到 adapter output
10. 计算 dot、cos、new_norm、conflict、positive_ratio、median_dot
11. 输出每层结果和 top-k
```

---

# 9. 输出目录

LLaVA：

```text
server_results/bridge_vlm_adapter_output_lga_llava_train30/
```

BLIP2：

```text
server_results/bridge_vlm_adapter_output_lga_blip2_train30/
```

输出文件：

```text
run_config.json
old_answer_mapping_report.json
sample_adapter_output_scores.jsonl
adapter_output_lga_layer_scores.csv
topk_adapter_output_layers.json
summary.md
```

---

# 10. 拟执行命令

## LLaVA

```bash
cd VisEdit-main
python scripts/bridge_vlm_adapter_output_lga_scan.py \
  --model-name llava-v1.5-7b \
  --vead-config-path configs/vead/llava-v1.5-7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl \
  --layers 0-31 \
  --adapter-type vision \
  --capture-object delta_h_vis \
  --score-mode request_only_adapter_output_lga \
  --main-score out_dot \
  --diagnostics out_cos,out_new_norm,out_old_norm,out_joint_norm,positive_ratio,median_dot \
  --seed 2026 \
  --output-dir ../server_results/bridge_vlm_adapter_output_lga_llava_train30
```

## BLIP2

```bash
cd VisEdit-main
python scripts/bridge_vlm_adapter_output_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --vead-config-path configs/vead/blip2-opt-2.7b.yaml \
  --data-path ../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../Ten_Classes/bridge \
  --old-answers-path ../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl \
  --layers 0-31 \
  --adapter-type vision \
  --capture-object delta_h_vis \
  --score-mode request_only_adapter_output_lga \
  --main-score out_dot \
  --diagnostics out_cos,out_new_norm,out_old_norm,out_joint_norm,positive_ratio,median_dot \
  --seed 2026 \
  --output-dir ../server_results/bridge_vlm_adapter_output_lga_blip2_train30
```

---

# 11. 验收检查

每次运行后检查：

```text
1. adapter_output_lga_layer_scores.csv 有 32 行
2. 每层 n_request = 30
3. base_requires_grad_params = 0
4. adapter_used = True
5. adapter_output_grad_captured = True
6. 每层 adapter output grad 非空
7. old/new 使用同一个 edit signal
8. 没有 optimizer.step
9. 没有加载训练 checkpoint
10. vt_range / visual span 正确
```

尤其要打印：

```text
gradient_target = adapter_output_delta_h_vis_L
base_requires_grad_params = 0
adapter_requires_grad_params > 0
adapter_output_grad_nonzero_ratio = ?
```

---

# 12. 和你已有三类实验怎么放在一起？

最终对比表建议这样写：

| Model | MLP-LGA Top-5 | Adapter-Parameter Top-5 | Adapter-Output Dot Top-5 | Adapter-Output Conflict Top-5 | Visual New-Norm Top-5 | Brute-force Best |
|---|---|---|---|---|---|---|
| LLaVA | 26,27,0,25,24 | ? | ? | ? | 6,7,5,3,4 | 1 |
| BLIP2 | 30,29,28,27,31 | ? | ? | ? | 0,1,2,3,4 | 19* |

其中：

```text
Adapter-Parameter LGA：哪层 adapter 参数适合承载编辑
Adapter-Output LGA：哪层 adapter 输出的视觉修改量最关键
Visual-Hidden LGA：哪层原始视觉 hidden state 对 target_new 最敏感
Brute-force：真实训练后哪层最好
```

---

# 13. 最终解释逻辑

如果 LLaVA 出现：

```text
Adapter-Output conflict top-k = 0/1/2/3/4
Visual new-norm top-k = 3/4/5/6/7
Brute-force best = 1
```

那说明：

> LLaVA 的浅层 adapter 之所以有效，是因为浅层 adapter 输出更容易对视觉实体表征产生替换性修改。

如果 BLIP2 出现：

```text
Adapter-Output new-norm top-k = 0/1/2/3/4
但 Adapter-Output conflict top-k = 11/14/15/16
```

那说明：

> BLIP2 浅层 visual prefix 很敏感，但可控替换层可能在中层，因此浅层容易塌，中层更值得编辑。

---

# 14. 最简结论

你要做的 Adapter-Output LGA 实验就是：

```text
冻结 LLaVA / BLIP2
在候选模型层 L 插入未训练 adapter
用 target_new 构造同一个 edit signal
分别用 old answer 和 target_new 计算 loss
反向到 adapter 输出的视觉修正量 Δh_vis^L
计算两个梯度的 dot、cos、new_norm、conflict
按层排名
再和 Adapter-Parameter LGA、Visual-Hidden LGA、暴力扫层结果对比
```

它回答的是：

> **adapter 挂在哪个模型层时，它输出的视觉表征修正量最有可能实现实体替换。**
