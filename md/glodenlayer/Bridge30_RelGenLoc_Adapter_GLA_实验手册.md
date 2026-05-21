# Bridge30 RelGenLoc Adapter GLA 实验手册

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this manual task-by-task after the user approves it. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用与 `bridge-only-vis` YAML 一致的三项训练目标计算 Bridge30 的 adapter GLA 候选层：`1 * Entity + 1 * Generality + 1 * Locality`。

**Architecture:** 冻结基础 VLM，只打开候选层 adapter。每个候选层都构造 request/edit signal，然后对 adapter 的层级目标求梯度，输出分层梯度分数和候选层。该实验只用于产生候选层，真正编辑层仍需后续暴力扫层结合编辑指标确认。

**Tech Stack:** VisEdit VEAD adapter, LLaVA-v1.5-7B, BLIP2-OPT-2.7B, Bridge30 train split, PyTorch autograd, JSON/JSONL, YAML, Markdown.

---

## 1. 本手册相对 request-only 版本的变化

旧的 request-only GLA 只计算：

```text
L_total = L_entity
```

新版必须计算与 only-vis YAML 对齐的三项：

```text
L_total = 1 * L_entity + 1 * L_generality + 1 * L_locality
```

对应 YAML 权重为：

```yaml
train_cfg:
  rel_lambda: 1
  gen_lambda: 1
  loc_lambda: 1
  inf_mapper_lambda: 0.1
port_lambda: 0.0
```

其中：

| 项 | 是否参与本次 GLA 梯度 | 权重 | 说明 |
|---|---:|---:|---|
| Entity / Reliability | 是 | 1 | request 图文输入写入 `target_new` |
| Generality | 是 | 1 | rephrase 图文输入写入同一实体目标 |
| Locality | 是 | 1 | KL preservation，保持无关图文样本输出分布不变 |
| Portability | 否 | 0 | only-vis YAML 中 `port_lambda = 0.0` |
| Fluency | 否 | 0 | 当前 VEAD 训练目标未显式使用 |
| Influence mapper | 默认不进入主 GLA | 0.1 | 可作为附加诊断，不作为候选层主排序 |

关键点：`locality` 不是把无关样本改成 `target_new`，而是保持编辑前后的输出分布一致。

---

## 2. 实验问题

本实验回答：

```text
当 adapter 的训练目标同时考虑 Entity、Generality、Locality 时，
LLaVA / BLIP2 哪些层的 adapter 输出或 adapter 参数最适合承载 bridge30 视觉编辑？
```

它不回答：

```text
最终训练哪个层一定最好。
```

最终编辑层仍然要用 layer sweep 训练结果判断，例如：

```text
Entity strict / loose
Generality strict / loose
Locality preservation
Open-end metric
EMA loss
```

---

## 3. 推荐梯度目标

### 3.1 主实验目标：Adapter-Output GLA

优先计算 adapter 输出的视觉修正量：

\[
\Delta h_{vis}^{i,L}
=
A_{\phi_L}(h_{vis}^{i,L}, e_i)
\]

其中：

```text
L = adapter 挂载的 VLM decoder 层
phi_L = 第 L 层 adapter 参数
h_vis^{i,L} = 第 i 个样本在第 L 层的视觉 token hidden states
e_i = 由 request.image + request.prompt + request.target_new 构造的 edit signal
```

主梯度为：

\[
g_{total,\Delta h}^{i,L}
=
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{total}^{i,L}
\]

选择该目标的原因：

```text
adapter 只训练视觉表征修正，delta_h_vis 是 adapter 真正注入模型的编辑量。
它比直接对原模型 theta_L 求梯度更符合当前 adapter 编辑设定。
```

### 3.2 辅助目标：Adapter-Parameter GLA

可选地计算：

\[
g_{total,\phi}^{i,L}
=
\nabla_{\phi_L}
\mathcal{L}_{total}^{i,L}
\]

该目标回答：

```text
第 L 层 adapter 参数本身是否容易被三项训练目标优化。
```

但它更容易受 adapter 参数规模、初始化、内部结构影响，所以本手册把 Adapter-Output GLA 作为主实验。

---

## 4. 数据使用规则

源数据：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

每个 case 使用三类监督：

### 4.1 Entity / Reliability

使用：

```json
"request": {
  "image": "...",
  "prompt": "...",
  "target_new": "..."
}
```

损失目标：

```text
request.target_new
```

### 4.2 Generality

使用：

```json
"generality": {
  "text_rephrase": [...],
  "image_rephrase": [...]
}
```

为严格贴近当前 VEAD 训练代码，默认使用每个 generality 子类的第一个样本：

```text
generality.text_rephrase[0]
generality.image_rephrase[0]
```

损失目标：

```text
generality.*[0].target
```

如果要做额外稳健性分析，可以开启 full-generality 模式，使用列表内全部样本，但主结果必须标注为：

```text
generality_mode = first_per_family
```

### 4.3 Locality

使用：

```json
"locality": {
  "text_loc": [...],
  "image_loc": [...]
}
```

为贴近 VEAD 的视觉 adapter 训练逻辑，主实验只使用：

```text
locality.image_loc[0]
```

原因：当前 `VisEdit-main/editor/vllm_editors/vead/vead.py` 中，locality 样本若 `image == None` 会被跳过，text-only locality 不参与视觉 adapter 的训练 loss。

Locality 损失不是 CE 到 `target_new`，而是 KL preservation：

```text
pre_logits  = adapter 关闭时，base model 在 locality.image_loc[0] 上的 logits
post_logits = adapter 打开并注入当前 request edit signal 后，在同一 locality 样本上的 logits
L_locality  = KL(pre_logits || post_logits)
```

### 4.4 Portability

不参与本次 GLA：

```text
portability.1hop = []
portability.2hop = []
port_lambda = 0.0
```

---

## 5. 三项总损失定义

对第 \(i\) 个 bridge case 和候选层 \(L\)，先用 request 构造 edit signal：

\[
e_i
=
\text{EditSignal}(I_{req,i}, Q_{req,i}, y_{req,i}^{new})
\]

### 5.1 Entity loss

\[
\mathcal{L}_{entity}^{i,L}
=
CE(
M_{\theta,\phi_L}(I_{req,i}, Q_{req,i}; e_i),
y_{req,i}^{new}
)
\]

### 5.2 Generality loss

设 \(G_i\) 是 `text_rephrase[0]` 和 `image_rephrase[0]` 的集合：

\[
\mathcal{L}_{generality}^{i,L}
=
\frac{1}{|G_i|}
\sum_{(I,Q,y)\in G_i}
CE(
M_{\theta,\phi_L}(I,Q; e_i),
y
)
\]

如果 text rephrase 带有 image，则照常传入 image；如果某条 generality 的 image 为 `null`，则按无图输入处理。

### 5.3 Locality loss

设 \(C_i\) 是 `image_loc[0]`：

\[
p_{base}
=
M_{\theta}(C_i)
\]

\[
p_{edit}
=
M_{\theta,\phi_L}(C_i; e_i)
\]

\[
\mathcal{L}_{locality}^{i,L}
=
KL(
p_{base}
\parallel
p_{edit}
)
\]

KL 只在目标答案 mask 覆盖的 token 位置上计算，保持与 VEAD `logit_KL_loss(pre_logits, post_logits, label_masks)` 一致。

### 5.4 总损失

\[
\mathcal{L}_{total}^{i,L}
=
1\cdot\mathcal{L}_{entity}^{i,L}
+
1\cdot\mathcal{L}_{generality}^{i,L}
+
1\cdot\mathcal{L}_{locality}^{i,L}
\]

禁止把 portability 或 fluency 加进主损失：

\[
\mathcal{L}_{main}
\neq
\mathcal{L}_{entity}
+
\mathcal{L}_{generality}
+
\mathcal{L}_{locality}
+
\mathcal{L}_{portability}
+
\mathcal{L}_{fluency}
\]

---

## 6. GLA 分数

### 6.1 主排序：三项总梯度范数

主排序使用总训练目标对 adapter-output 的梯度强度：

\[
S_{total\_norm}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
\nabla_{\Delta h_{vis}^{i,L}}
\mathcal{L}_{total}^{i,L}
\right\|_2
\]

该分数最直接对应：

```text
哪一层的 adapter 输出对 Entity + Generality + Locality 总训练目标最敏感。
```

### 6.2 保留 LGA dot 与 cosine

为了和前面 LGA 结果可比较，仍然输出 old/new 形式的 dot 和 cosine。

Entity 与 Generality 有 old/new 两个方向：

```text
old side: 使用 base model old answer
new side: 使用 target_new 或 generality target
```

Locality 是 preservation 项，没有 target_new 替换方向，因此 locality gradient 同时加入 old side 和 new side：

\[
g_{old,total}^{i,L}
=
g_{entity,old}^{i,L}
+
g_{generality,old}^{i,L}
+
g_{locality}^{i,L}
\]

\[
g_{new,total}^{i,L}
=
g_{entity,new}^{i,L}
+
g_{generality,new}^{i,L}
+
g_{locality}^{i,L}
\]

总内积：

\[
S_{total\_dot}(L)
=
\sum_{i=1}^{N}
\left(
g_{old,total}^{i,L}
\right)^\top
\left(
g_{new,total}^{i,L}
\right)
\]

总余弦：

\[
S_{total\_cos}(L)
=
\frac{1}{N}
\sum_{i=1}^{N}
\frac{
\left(
g_{old,total}^{i,L}
\right)^\top
\left(
g_{new,total}^{i,L}
\right)
}{
\left\|
g_{old,total}^{i,L}
\right\|_2
\left\|
g_{new,total}^{i,L}
\right\|_2
+
\epsilon
}
\]

注意：因为 locality gradient 在 old/new 两侧是同方向 preservation 项，`S_total_dot` 可能被 locality 拉高。因此必须同时报告分项分数。

### 6.3 分项分数

每层都要输出：

```text
S_entity_norm
S_generality_norm
S_locality_norm
S_entity_dot
S_generality_dot
S_total_dot
S_total_cos
```

额外保留 entity/generality 的替换冲突分数：

\[
S_{eg\_conflict}(L)
=
-
\sum_i
\left(
g_{entity,old}^{i,L}
+
g_{generality,old}^{i,L}
\right)^\top
\left(
g_{entity,new}^{i,L}
+
g_{generality,new}^{i,L}
\right)
\]

该分数用于解释：

```text
哪一层最像 old answer -> target_new 的替换层。
```

它不是主排序，但对解释暴力扫层结果很有用。

---

## 7. 输出文件规范

建议新建脚本：

```text
VisEdit-main/scripts/bridge_vlm_relgenloc_adapter_gla_scan.py
```

建议新建测试：

```text
VisEdit-main/tests/test_bridge_vlm_relgenloc_adapter_gla_scan.py
```

LLaVA 输出目录：

```text
server_results/bridge_vlm_relgenloc_adapter_gla_llava_train30/
```

BLIP2 输出目录：

```text
server_results/bridge_vlm_relgenloc_adapter_gla_blip2_train30/
```

每个输出目录至少包含：

```text
run_config.json
sample_component_scores.jsonl
layer_scores.csv
topk_layers.json
summary.md
```

`run_config.json` 必须记录：

```json
{
  "loss_mode": "relgenloc",
  "entity_weight": 1.0,
  "generality_weight": 1.0,
  "locality_weight": 1.0,
  "portability_weight": 0.0,
  "fluency_weight": 0.0,
  "include_influence_mapper_in_main_score": false,
  "gradient_target": "adapter_output_delta_h_vis",
  "generality_mode": "first_per_family",
  "locality_mode": "image_loc_first_only",
  "base_requires_grad_params": 0,
  "adapter_used": true
}
```

`layer_scores.csv` 至少包含：

```text
model
layer
gradient_target
n_cases
n_entity
n_generality
n_locality
S_total_norm
S_total_dot
S_total_cos
S_entity_norm
S_generality_norm
S_locality_norm
S_entity_dot
S_generality_dot
S_eg_conflict
zero_grad_flag
nan_flag
total_norm_rank
total_dot_rank
total_cos_rank
eg_conflict_rank
```

`topk_layers.json` 至少包含：

```json
{
  "primary_total_norm_topk": [],
  "total_dot_topk": [],
  "total_cos_topk": [],
  "eg_conflict_topk": [],
  "zero_grad_layers": [],
  "recommended_candidate_pool": []
}
```

推荐候选池生成规则：

```text
recommended_candidate_pool =
  top5(primary_total_norm)
  union top5(total_cos)
  union top5(eg_conflict)
  remove zero_grad_layers
```

如果第 31 层再次出现零梯度，必须保留在 `zero_grad_layers`，不能仅因 dot 为 0 就选入主候选。

---

## 8. 服务器运行模板

优先尝试 `g08`，如果因为 `pam_slurm_adopt` 无 active job 无法进入，则切换 `g07`。

本地 SSH：

```powershell
ssh -i $HOME\.ssh\id_ed25519_bridge ph_teacher3@10.68.162.201
```

进入服务器后：

```bash
ssh g08
# 如果 g08 不可用：
ssh g07
```

远端路径：

```text
repo: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
data: /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes
results: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
python: /datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
```

LLaVA 运行模板：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python \
  scripts/bridge_vlm_relgenloc_adapter_gla_scan.py \
  --model-name llava-v1.5-7b \
  --vead-config-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/llava-v1.5-7b-bridge-only-vis-l4.yaml \
  --data-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --layers 0-31 \
  --gradient-target adapter_output_delta_h_vis \
  --loss-mode relgenloc \
  --entity-weight 1.0 \
  --generality-weight 1.0 \
  --locality-weight 1.0 \
  --portability-weight 0.0 \
  --output-dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_relgenloc_adapter_gla_llava_train30
```

BLIP2 运行模板：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python \
  scripts/bridge_vlm_relgenloc_adapter_gla_scan.py \
  --model-name blip2-opt-2.7b \
  --vead-config-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/blip2-opt-2.7b-bridge-only-vis-l4.yaml \
  --data-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --layers 0-31 \
  --gradient-target adapter_output_delta_h_vis \
  --loss-mode relgenloc \
  --entity-weight 1.0 \
  --generality-weight 1.0 \
  --locality-weight 1.0 \
  --portability-weight 0.0 \
  --output-dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_relgenloc_adapter_gla_blip2_train30
```

说明：`--vead-config-path` 中的具体 layer 值只用于读取模型维度、adapter/IT 配置模板；脚本内部必须按 `--layers` 动态替换候选层。

---

## 9. 实现检查清单

- [ ] 读取 YAML，确认 `rel_lambda=1`、`gen_lambda=1`、`loc_lambda=1`、`port_lambda=0`。
- [ ] 冻结基础 VLM，确认 `base_requires_grad_params = 0`。
- [ ] 每个候选层只打开该层 adapter，确认 `adapter_used = true`。
- [ ] 每个 case 的 edit signal 只由 request 构造。
- [ ] Entity 使用 `request.target_new` 计算 CE。
- [ ] Generality 使用 `text_rephrase[0]` 与 `image_rephrase[0]` 计算 CE。
- [ ] Locality 使用 `image_loc[0]` 计算 `KL(pre_logits || post_logits)`。
- [ ] `text_loc` 不进入主 GLA loss，只能作为后续评估或附加诊断。
- [ ] Portability 不进入主 GLA loss。
- [ ] Influence mapper 不进入主 GLA 排序。
- [ ] 每层输出总分和分项分数。
- [ ] 标记 `zero_grad_flag`、`nan_flag`。
- [ ] 第 31 层如为零梯度，不能仅凭 dot 排入推荐候选。
- [ ] 不执行 optimizer step，不加载编辑后 checkpoint。
- [ ] 生成 `summary.md`，写清楚候选层和异常层。

---

## 10. 结果解释规则

如果三项 GLA 的候选层与 request-only 差异很大，不直接判定实验错误。因为：

```text
request-only 只看写入目标；
relgenloc 同时看写入、泛化和局部保持；
locality KL 会偏向不破坏无关视觉样本的层。
```

推荐解释顺序：

1. 先看 `primary_total_norm_topk`：它最接近真实训练目标的梯度敏感性。
2. 再看 `total_cos_topk`：它减少参数规模和梯度幅值差异的影响。
3. 再看 `eg_conflict_topk`：它解释 old answer 到 target_new 的替换冲突。
4. 最后和暴力扫层的编辑指标对照，不把 GLA 当作最终编辑层结论。

如果 LLaVA 候选层偏浅层或中浅层、BLIP2 候选层偏中层或中后层，需要结合模型结构解释：

```text
LLaVA: 视觉 token 直接进入 LLM decoder，浅层/中浅层可能更早承接视觉实体绑定。
BLIP2: Q-Former/OPT 接口压缩视觉信息，adapter 挂载层的最佳位置可能更依赖中层或后续语言写入层。
```

本实验的结论应写成：

```text
三项训练目标下的 GLA 候选层
```

而不是：

```text
最终最优编辑层
```
