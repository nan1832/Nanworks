# VLM-LGA：多模态大语言模型 Golden Layer 估计实验操作方案

## 1. 实验目标

本实验目标是将 **Layer Gradient Analysis（LGA）** 从纯文本大语言模型知识编辑扩展到多模态视觉语言模型（VLM）编辑中，用于估计不同模型架构下的 **Golden Layer**。

你的核心假设是：

> 编辑层位置与模型架构相关。LLaVA 的最佳编辑层可能偏浅层，而 BLIP2 的最佳编辑层可能偏中层或中后层。

实验要回答三个问题：

1. LGA 思路是否可以用于 VLM 的编辑层选择？
2. LLaVA 和 BLIP2 的 Golden Layer 是否位于不同深度？
3. LGA 估计出的层是否能预测真实扫层实验中的最佳层？

---

## 2. 基本思想

原始 LGA 用于文本 LLM，核心是比较同一层参数在“旧知识”和“新知识”上的梯度关系：

\[
G^* = \arg\max_L \sum_i \nabla_{\theta_L} \mathcal{L}(Q_i, K_i) \cdot \nabla_{\theta_L} \mathcal{L}(Q_i, K'_i)
\]

在 VLM 编辑中，将文本输入扩展为图文对：

\[
Q_i \rightarrow (I_i, Q_i)
\]

其中：

- \(I_i\)：图像
- \(Q_i\)：问题
- \(y_i^{old}\)：基础模型原始输出
- \(y_i^{new}\)：希望编辑成的新答案

因此，VLM-LGA 的基本形式为：

\[
G^* = \arg\max_L \sum_i sim\left(
\nabla_{\theta_L}\mathcal{L}(I_i,Q_i,y_i^{old}),
\nabla_{\theta_L}\mathcal{L}(I_i,Q_i,y_i^{new})
\right)
\]

其中 \(sim(\cdot)\) 可以使用 dot product，也可以使用 cosine similarity。考虑到 VLM 中不同模块参数规模差异较大，建议优先使用 cosine similarity。

---

## 3. 数据准备

每个编辑样本建议包含以下字段：

```json
{
  "case_id": "train_0",
  "entity_id": "Q1056242",
  "entity_name": "Chikugo River Lift Bridge",
  "request": {
    "image": "train/images/GLDv2_084bb592a552d066.jpg",
    "prompt": "What is the name of this bridge?",
    "target_new": "Chikugo River Lift Bridge"
  },
  "generality": {
    "text_rephrase": [...],
    "image_rephrase": [...]
  },
  "locality": {
    "text_loc": [...],
    "image_loc": [...]
  },
  "portability": {
    "1hop": [],
    "2hop": [],
    "3hop": []
  }
}
```

建议划分：

```text
proxy set：用于计算 VLM-LGA 分数，例如 10% 或 50–200 个样本
test set：用于验证 LGA 选出的层是否真实有效
```

如果数据量较小，可以采用：

```text
proxy set：30–50 个实体
test set：剩余实体
```

注意：尽量按 entity_id 划分，避免同一实体同时出现在 proxy 和 test 中。

---

## 4. 候选层设置

### 4.1 LLaVA 候选层

LLaVA 典型结构：

```text
Vision Encoder → Projector → LLM Decoder
```

如果你的 adapter 插入在 LLM decoder 层，可以先扫：

```text
0, 1, 2, 4, 6, 8, 11, 14, 16, 18, 20, 24, 28, 30
```

如果资源允许，建议全层扫描。

也可以分模块统计：

```text
visual encoder layers
projector layer
LLM decoder layers
adapter insertion layers
```

### 4.2 BLIP2 候选层

BLIP2 典型结构：

```text
Vision Encoder → Q-Former → LLM Decoder
```

建议不要只扫 2、4、15、19，而是补充更多层，例如：

```text
0, 2, 4, 6, 8, 10, 12, 15, 18, 19, 21, 24, 27, 30
```

如果 BLIP2 的 adapter 插在 Q-Former 或 LLM decoder，需要分别记录：

```text
Q-Former golden layer
LLM decoder golden layer
cross-modal connector golden layer
```

---

## 5. Step-by-step 实验流程

## Step 1：获取基础模型的 old answer

对每个 request 输入：

\[
(I_i, Q_i)
\]

使用未编辑基础模型进行 greedy decoding，得到原始输出：

\[
y_i^{old} = M_{base}(I_i,Q_i)
\]

新答案来自数据集：

\[
y_i^{new} = target\_new
\]

保存为：

```json
{
  "case_id": "train_0",
  "old_answer": "...",
  "new_answer": "Chikugo River Lift Bridge"
}
```

注意：

- 如果 old answer 为空、乱码或与问题无关，建议单独标记。
- 如果 old answer 已经等于 target_new，可以标记为 already_correct，后续可以单独分析。
- 对实体识别任务，old answer 最好使用短答案，不要保留过长解释。

---

## Step 2：构造 old loss 与 new loss

对每个样本构造两个监督目标。

### 旧答案 loss

\[
\mathcal{L}_{old}^{i} = CE(M(I_i,Q_i), y_i^{old})
\]

### 新答案 loss

\[
\mathcal{L}_{new}^{i} = CE(M(I_i,Q_i), y_i^{new})
\]

实现时注意：

- 只对 answer tokens 计算 loss。
- image tokens 和 question tokens 不参与 CE loss。
- 对于 autoregressive LLM，需要将 prompt 部分 label 设置为 `-100`。

---

## Step 3：计算每个候选层的梯度

对每个候选层 \(l\)：

\[
g_{old}^{i,l}=\nabla_{\theta_l}\mathcal{L}_{old}^{i}
\]

\[
g_{new}^{i,l}=\nabla_{\theta_l}\mathcal{L}_{new}^{i}
\]

其中 \(\theta_l\) 可以是：

```text
LLaVA decoder layer l 的 MLP / attention / adapter 参数
BLIP2 Q-Former layer l 参数
BLIP2 LLM decoder layer l 参数
Projector / connector 参数
```

建议优先对以下参数计算：

```text
adapter 参数
MLP 参数
cross-attention 参数
projector 参数
```

不建议一开始直接对全模型所有参数计算，因为显存开销较大。

---

## Step 4：计算编辑相关 LGA 分数

对每个样本、每个层计算梯度相似度：

\[
s_{edit}^{i,l}=cos(g_{old}^{i,l}, g_{new}^{i,l})
\]

然后对 proxy set 求平均：

\[
S_{edit}(l)=\frac{1}{N}\sum_i s_{edit}^{i,l}
\]

如果使用 dot product，则为：

\[
s_{edit}^{i,l}=g_{old}^{i,l}\cdot g_{new}^{i,l}
\]

建议同时保存两种分数：

```text
edit_dot_score
edit_cos_score
```

最终主分析优先用 cosine score。

---

## Step 5：加入 generality 分数

generality 包括：

```text
text_rephrase
image_rephrase
```

对每个 generality 样本 \(r\)：

\[
x_r=(I_r,Q_r)
\]

计算：

\[
g_{old}^{r,l}=\nabla_{\theta_l}\mathcal{L}(x_r,y_r^{old})
\]

\[
g_{new}^{r,l}=\nabla_{\theta_l}\mathcal{L}(x_r,y_r^{new})
\]

\[
s_{gen}^{r,l}=cos(g_{old}^{r,l},g_{new}^{r,l})
\]

聚合：

\[
S_{gen}(l)=\frac{1}{|G|}\sum_{r\in G}s_{gen}^{r,l}
\]

其中 \(G\) 是所有 rephrase 样本集合。

如果暂时不想复杂化，可以第一版只用 request 计算 LGA，第二版再加入 generality。

---

## Step 6：加入 locality 惩罚项

locality 的目标是保持无关样本输出不变。

对每个 locality 样本 \(u\)：

\[
x_u=(I_u,Q_u)
\]

\[
g_{loc}^{u,l}=\nabla_{\theta_l}\mathcal{L}(x_u,y_u)
\]

其中 \(y_u\) 是 locality 样本原本应该保持的答案。

计算编辑目标梯度和 locality 梯度的干扰程度：

\[
s_{loc}^{u,l}=\left|cos(g_{new}^{i,l},g_{loc}^{u,l})\right|
\]

聚合：

\[
S_{loc}(l)=\frac{1}{|U|}\sum_{u\in U}s_{loc}^{u,l}
\]

这里 \(S_{loc}(l)\) 越大，说明编辑该层越可能影响无关知识，因此它应该作为惩罚项。

---

## Step 7：构造 VLM-LGA 总分

建议使用：

\[
S_{VLM-LGA}(l)=\alpha S_{edit}(l)+\beta S_{gen}(l)-\gamma S_{loc}(l)
\]

推荐初始权重：

```text
alpha = 0.5
beta  = 0.3
gamma = 0.2
```

如果当前没有 generality 或 locality 的梯度统计，可以先用简化版：

\[
S_{VLM-LGA}(l)=S_{edit}(l)
\]

如果后续加入 portability / open-ended multi-hop：

\[
S_{VLM-LGA}(l)=\alpha S_{edit}(l)+\beta S_{gen}(l)+\delta S_{port}(l)-\gamma S_{loc}(l)
\]

---

## Step 8：选出 top-k 候选 Golden Layers

分别对 LLaVA 和 BLIP2 计算：

\[
\hat{g}_{LLaVA}=\arg\max_l S_{VLM-LGA}^{LLaVA}(l)
\]

\[
\hat{g}_{BLIP2}=\arg\max_l S_{VLM-LGA}^{BLIP2}(l)
\]

实际操作中不要只取 top-1，建议保存 top-k：

```text
top-1 layer
top-3 layers
top-5 layers
```

输出文件：

```text
llava_lga_scores.csv
blip2_lga_scores.csv
llava_topk_layers.json
blip2_topk_layers.json
```

CSV 推荐格式：

```csv
model,layer,S_edit,S_gen,S_loc,S_total,rank
LLaVA,1,0.431,0.388,0.102,0.375,1
LLaVA,11,0.397,0.401,0.133,0.348,2
BLIP2,19,0.281,0.220,0.090,0.207,1
```

---

## Step 9：训练 adapter 验证 LGA 选层是否有效

对每个模型选取：

```text
LGA top-1 层
LGA top-3 层
当前经验最佳层
VisEdit 推荐中层
随机层
浅层 baseline
深层 baseline
```

分别训练 adapter，并在 test set 上评估：

```text
Entity Strict
Entity Loose
Open-end Strict
Open-end Loose
Generality
Locality
Portability
Overall Score
```

关键比较：

```text
LLaVA: LGA top 层是否落在浅层，并且 test 表现最好？
BLIP2: LGA top 层是否避开浅层，落在中层/中后层，并且 test 表现更好？
```

---

## Step 10：与 brute-force golden layer 对比

为了证明 LGA 有效，需要做一个小规模 brute-force 扫层作为 ground truth。

对小 proxy set 或 validation set：

1. 每个候选层都训练 adapter。
2. 每层在同一个 test subset 上评估。
3. 得到真实最佳层：

\[
g_{true}=\arg\max_l Score_{eval}(l)
\]

然后比较：

```text
LGA predicted golden layer vs brute-force true golden layer
```

可以报告：

```text
Top-1 hit: LGA top-1 是否等于真实最佳层
Top-3 hit: 真实最佳层是否在 LGA top-3 中
Rank correlation: LGA 层排序与真实扫层排序的 Spearman 相关
Performance gap: LGA top-1 与真实最佳层的性能差距
```

---

## 6. 推荐整体指标设计

建议定义一个综合分数：

\[
Score(l)=w_1E_{strict}+w_2E_{loose}+w_3O_{strict}+w_4O_{loose}+w_5G+w_6L
\]

其中：

- \(E_{strict}\)：Entity strict
- \(E_{loose}\)：Entity loose
- \(O_{strict}\)：Open-end strict
- \(O_{loose}\)：Open-end loose
- \(G\)：Generality
- \(L\)：Locality

如果你当前只统计四个指标，可以先用：

\[
Score(l)=0.35E_{strict}+0.25E_{loose}+0.20O_{strict}+0.20O_{loose}
\]

如果更重视实体编辑：

\[
Score(l)=0.45E_{strict}+0.25E_{loose}+0.15O_{strict}+0.15O_{loose}
\]

如果更重视开放问答泛化：

\[
Score(l)=0.30E_{strict}+0.20E_{loose}+0.25O_{strict}+0.25O_{loose}
\]

---

## 7. PyTorch 风格伪代码

```python
for model_name in ["llava", "blip2"]:
    model = load_model(model_name)
    candidate_layers = get_candidate_layers(model_name)

    layer_scores = {l: {"edit": [], "gen": [], "loc": []} for l in candidate_layers}

    for sample in proxy_set:
        image = load_image(sample["request"]["image"])
        question = sample["request"]["prompt"]
        y_new = sample["request"]["target_new"]

        # Step 1: get old answer from base model
        y_old = greedy_decode(model, image, question)

        for l in candidate_layers:
            params_l = get_layer_params(model, l)

            # old loss gradient
            model.zero_grad()
            loss_old = compute_answer_ce_loss(model, image, question, y_old)
            grad_old = get_grad_vector(loss_old, params_l)

            # new loss gradient
            model.zero_grad()
            loss_new = compute_answer_ce_loss(model, image, question, y_new)
            grad_new = get_grad_vector(loss_new, params_l)

            # edit score
            s_edit = cosine_similarity(grad_old, grad_new)
            layer_scores[l]["edit"].append(s_edit)

            # optional: generality score
            for r in get_generality_samples(sample):
                image_r, question_r, y_r_new = parse_rephrase(r)
                y_r_old = greedy_decode(model, image_r, question_r)

                model.zero_grad()
                loss_r_old = compute_answer_ce_loss(model, image_r, question_r, y_r_old)
                grad_r_old = get_grad_vector(loss_r_old, params_l)

                model.zero_grad()
                loss_r_new = compute_answer_ce_loss(model, image_r, question_r, y_r_new)
                grad_r_new = get_grad_vector(loss_r_new, params_l)

                s_gen = cosine_similarity(grad_r_old, grad_r_new)
                layer_scores[l]["gen"].append(s_gen)

            # optional: locality penalty
            for u in get_locality_samples(sample):
                image_u, question_u, y_u = parse_locality(u)

                model.zero_grad()
                loss_u = compute_answer_ce_loss(model, image_u, question_u, y_u)
                grad_loc = get_grad_vector(loss_u, params_l)

                s_loc = abs(cosine_similarity(grad_new, grad_loc))
                layer_scores[l]["loc"].append(s_loc)

    final_scores = []
    for l in candidate_layers:
        S_edit = mean(layer_scores[l]["edit"])
        S_gen = mean(layer_scores[l]["gen"]) if layer_scores[l]["gen"] else 0.0
        S_loc = mean(layer_scores[l]["loc"]) if layer_scores[l]["loc"] else 0.0

        S_total = 0.5 * S_edit + 0.3 * S_gen - 0.2 * S_loc
        final_scores.append((l, S_edit, S_gen, S_loc, S_total))

    final_scores = sorted(final_scores, key=lambda x: x[-1], reverse=True)
    save_scores(model_name, final_scores)
```

---

## 8. 实验结果表格模板

### 8.1 LGA 分数表

| Model | Layer | S_edit | S_gen | S_loc | S_total | Rank |
|---|---:|---:|---:|---:|---:|---:|
| LLaVA | 1 | - | - | - | - | 1 |
| LLaVA | 11 | - | - | - | - | 2 |
| BLIP2 | 19 | - | - | - | - | 1 |

### 8.2 LGA 预测层训练验证表

| Model | Layer Source | Layer | Entity Strict | Entity Loose | Open-end Strict | Open-end Loose | Locality | Overall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LLaVA | LGA top-1 | 1 | - | - | - | - | - | - |
| LLaVA | VisEdit middle | 15 | - | - | - | - | - | - |
| BLIP2 | LGA top-1 | 19 | - | - | - | - | - | - |
| BLIP2 | shallow baseline | 2 | - | - | - | - | - | - |

### 8.3 LGA 与 brute-force 对齐表

| Model | LGA Top-1 | Brute-force Best | Top-1 Hit | Brute-force Best in LGA Top-3 | Performance Gap |
|---|---:|---:|---|---|---:|
| LLaVA | - | - | - | - | - |
| BLIP2 | - | - | - | - | - |

---

## 9. 预期结论判断标准

### 支持你的假设的结果

如果出现以下现象，可以支持“编辑层与模型架构相关”：

```text
1. LLaVA 的 LGA top 层集中在浅层，例如 layer 0–4 或 0–6。
2. BLIP2 的 LGA top 层避开浅层，集中在中层或中后层，例如 Q-Former / LLM 的中间层。
3. LGA top 层训练 adapter 后，在 test set 上接近或超过 brute-force 最优层。
4. VisEdit 的 BLIP2 中层结论不能直接迁移到 LLaVA；LLaVA 浅层反而更优。
```

### 不支持你的假设的结果

如果出现以下现象，需要修改假设：

```text
1. LLaVA 和 BLIP2 的 LGA top 层都集中在同一区域。
2. LGA top 层与真实扫层最佳层完全不一致。
3. BLIP2 所有层都塌陷，说明问题可能来自训练设置，而不是层位置。
4. 不同随机种子下最佳层波动很大，说明结果不稳定。
```

---

## 10. 关键控制变量

为了避免把训练问题误判为架构问题，必须控制以下变量：

```text
1. 相同训练集 / proxy set / test set 划分
2. 相同 batch size
3. 相同 learning rate 搜索范围
4. 相同训练步数或相同 early stopping 规则
5. 相同 adapter 参数量
6. 相同 decoding 设置
7. 相同 evaluation script
8. 至少 3 个 random seeds
9. BLIP2 与 LLaVA 分别调好基础训练稳定性后再比较层位置
```

特别注意：

> 不同层使用不同 checkpoint 时，不能直接证明层位置差异，因为 checkpoint 差异会引入收敛速度混杂因素。

建议使用：

```text
方案 A：所有层固定训练相同步数
方案 B：所有层使用同一 early stopping 规则
```

---

## 11. 常见问题与处理

### 问题 1：old answer 本身就是正确答案

处理方式：

```text
单独标记 already_correct
主分析可以剔除
附录中报告包含 already_correct 的结果
```

### 问题 2：某些层梯度为 0 或极小

处理方式：

```text
检查该层是否被冻结
检查 adapter 是否接入计算图
检查 loss 是否只对 answer tokens 生效
检查是否用了 no_grad
```

### 问题 3：dot product 偏向参数量大的层

处理方式：

```text
主结果使用 cosine similarity
附录报告 dot product
也可以使用 normalized dot product
```

### 问题 4：BLIP2 全层效果都很低

处理方式：

```text
先检查 adapter 插入位置是否合理
检查 Q-Former 是否需要单独编辑
检查学习率是否过大导致输出塌陷
检查训练目标是否只适合 LLaVA 不适合 BLIP2
增加中层和 Q-Former 层扫描
```

### 问题 5：open-end 问答下降明显

解释方向：

```text
训练只包含实体识别，没有加入多跳知识监督
adapter 学到的是实体名称绑定，而不是知识链路推理
可作为 generality / portability limitation 讨论
```

---

## 12. 论文写法建议

可以将该方法命名为：

```text
VLM-LGA: Vision-Language Layer Gradient Analysis
```

或：

```text
Modality-aware Layer Gradient Analysis
```

可写成如下方法描述：

> Although LGA was originally proposed for text-only LLM knowledge editing, its core mechanism relies on first-order layer-wise gradient attribution and is not inherently restricted to unimodal language models. We extend this idea to vision-language model editing by replacing the textual query with an image-question pair and computing layer-wise gradient alignment between the original model answer and the edited target answer. This enables architecture-aware golden layer estimation for VLMs.

中文表述：

> 虽然 LGA 最初用于纯文本大语言模型知识编辑，但其核心机制是一阶层级梯度归因，并不天然局限于文本模型。本文将文本查询扩展为图文对输入，通过计算基础模型原始答案与编辑目标答案在不同层上的梯度对齐程度，估计视觉语言模型中的架构感知 Golden Layer。

---

## 13. 最终实验结论模板

如果实验支持你的假设，可以这样总结：

> The results suggest that golden editing layers in VLMs are architecture-dependent. For LLaVA, the optimal editing layers tend to appear in shallow decoder layers, possibly because visual tokens are directly projected into the language model and early layers are responsible for visual-textual binding. In contrast, BLIP2 shows poor performance when editing shallow layers, while middle or later layers are more favorable, likely due to the Q-Former bottleneck that pre-compresses visual information before it reaches the language decoder. These findings indicate that layer selection strategies derived from BLIP2 cannot be directly transferred to LLaVA.

中文总结：

> 实验结果表明，VLM 中的最佳编辑层具有明显的架构相关性。LLaVA 的最佳编辑层更偏浅层，这可能与其视觉特征通过 projector 直接进入语言模型、浅层承担视觉-文本绑定有关；而 BLIP2 的浅层编辑容易导致输出退化，中层或中后层更可能适合编辑，这可能与 Q-Former 对视觉信息的预压缩和重组有关。因此，基于 BLIP2 得到的中层最优结论不能直接迁移到 LLaVA。
