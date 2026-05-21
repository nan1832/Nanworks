# Bridge30 Golden Layer 结果

## 1. 实验设置

数据：

```text
Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
```

模型：

```text
LLaVA-v1.5-7B
BLIP2-OPT-2.7B
```

候选层：

```text
0-31
```

模块：

```text
LLaVA: language_model.model.layers.{l}.mlp
BLIP2: language_model.model.decoder.layers.{l}.fc2
```

LGA 主指标：

```text
S_lga_dot = sum_i dot(g_old_i_l, g_new_i_l)
```

诊断指标：

```text
S_lga_cos
old_grad_norm
new_grad_norm
joint_grad_norm
norm_ratio
```

old answer 来源：

```text
LLaVA: 已有 before-edit entity recognition 缓存
BLIP2: 本次使用未编辑 BLIP2 基础模型生成并缓存
```

## 2. LLaVA LGA 结果

LLaVA 的 request-only LGA dot top-5：

| Dot Rank | Layer | S_lga_dot | S_lga_cos | Joint Norm | Norm Ratio | Cos Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 26 | -250.9878 | -0.0440 | 220.3764 | 0.2948 | 1 |
| 2 | 27 | -259.8126 | -0.0487 | 201.5588 | 0.2696 | 4 |
| 3 | 0 | -259.8184 | -0.2549 | 50.9730 | 0.0682 | 24 |
| 4 | 25 | -279.0532 | -0.0480 | 225.1402 | 0.3012 | 2 |
| 5 | 24 | -279.7886 | -0.0485 | 218.9976 | 0.2930 | 3 |

LGA predicted golden layer：

```text
LLaVA: layer 26
```

候选层：

```text
LLaVA candidate layers by dot top-5 = [26, 27, 0, 25, 24]
```

注意：

```text
LLaVA 的 S_lga_dot top 层仍为负值。
因此这里的 layer 26 是 argmax，即“最不负”的层，而不是强正向梯度对齐层。
cosine top-1 也为 layer 26，但 cosine 仍为负，说明 old/new 梯度方向整体不一致。
```

## 3. BLIP2 LGA 结果

BLIP2 的 request-only LGA dot top-5：

| Dot Rank | Layer | S_lga_dot | S_lga_cos | Joint Norm | Norm Ratio | Cos Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 12.8838 | 0.0017 | 37.4923 | 1.1536 | 1 |
| 2 | 29 | 6.9970 | -0.0003 | 36.3550 | 1.1186 | 2 |
| 3 | 28 | 0.8074 | -0.0029 | 36.5562 | 1.1248 | 3 |
| 4 | 27 | -5.3313 | -0.0090 | 33.8248 | 1.0408 | 4 |
| 5 | 31 | -5.6501 | -0.0179 | 30.3043 | 0.9325 | 7 |

LGA predicted golden layer：

```text
BLIP2: layer 30
```

候选层：

```text
BLIP2 candidate layers by dot top-5 = [30, 29, 28, 27, 31]
```

注意：

```text
BLIP2 的 dot top-3 集中在后层，且 top-1 的 dot 为正。
cosine top-3 与 dot top-3 一致，为 [30, 29, 28]。
这说明 BLIP2 在 decoder-only MLP LGA 设置下更偏后层。
```

## 4. LGA 与暴力扫层对比

| Model | LGA Dot Top-5 | Brute-force 当前较优层 | 对齐情况 |
|---|---|---:|---|
| LLaVA | [26, 27, 0, 25, 24] | 1 | 未直接命中 layer 1；layer 0 进入 top-3 |
| BLIP2 | [30, 29, 28, 27, 31] | 19* | 未命中 layer 19，LGA 更偏后层 |

*BLIP2 layer 19 是当前 loose exploratory best，strict true edit layer 尚未确定。

## 5. 结论

本次 request-only LGA 的候选层为：

```text
LLaVA: [26, 27, 0, 25, 24]
BLIP2: [30, 29, 28, 27, 31]
```

解释：

```text
1. 这次只计算文本解码器 MLP / fc2 的 request-only LGA。
2. LGA predicted golden layer 不等于最终编辑层，最终编辑层仍需要暴力扫层和编辑指标确定。
3. 当前 LLaVA LGA 结果没有直接支持“编辑层必在 layer 1”，但 layer 0 进入 dot top-3。
4. 当前 BLIP2 LGA 结果明显偏后层，而不是直接落在已测 loose best layer 19。
5. 这说明“LGA 梯度候选层”和“adapter 暴力扫层最优层”需要分开报告，不能互相替代。
```

## 6. 差距分析

当前 `argmax(S_lga_dot)` 与暴力扫层差距较大：

```text
LLaVA: LGA dot top1 = 26，但暴力扫层当前最优 = 1。
BLIP2: LGA dot top1 = 30，但暴力扫层当前 loose 较优 = 19。
```

但如果观察 old/new 梯度的冲突方向，即：

```text
conflict_score = -S_lga_dot
```

也就是选择 `S_lga_dot` 最负的层，结果与暴力扫层明显更接近。

### 6.1 LLaVA conflict ranking

| Conflict Rank | Layer | S_lga_dot | S_lga_cos | Norm Ratio |
|---:|---:|---:|---:|---:|
| 1 | 1 | -122077.2897 | -0.2573 | 20.8971 |
| 2 | 7 | -4142.5706 | -0.3172 | 0.5412 |
| 3 | 5 | -3743.2956 | -0.3036 | 0.5327 |
| 4 | 6 | -3630.1079 | -0.3030 | 0.5057 |
| 5 | 8 | -3529.4991 | -0.3037 | 0.4836 |

LLaVA 的暴力扫层最优 `layer 1` 正好是 conflict top-1。

不过 `layer 1` 的 norm ratio = 20.8971，说明 raw dot 受到梯度范数强烈放大，因此它不能简单作为论文 LGA 主指标替代项。

### 6.2 BLIP2 conflict ranking

| Conflict Rank | Layer | S_lga_dot | S_lga_cos | Norm Ratio |
|---:|---:|---:|---:|---:|
| 1 | 18 | -165.1584 | -0.0733 | 1.7674 |
| 2 | 19 | -162.4611 | -0.0752 | 1.6930 |
| 3 | 21 | -134.3231 | -0.0653 | 1.6318 |
| 4 | 20 | -130.1578 | -0.0690 | 1.4995 |
| 5 | 17 | -124.0662 | -0.0666 | 1.4961 |

BLIP2 的暴力扫层 loose 较优 `layer 19` 是 conflict top-2。

如果按 negative cosine，即方向冲突而不受梯度范数大小影响，BLIP2 的 `layer 19` 是 top-1：

```text
BLIP2 negative cosine top-5 = [19, 18, 20, 17, 21]
```

### 6.3 解释

这说明当前实验里有两个不同问题：

```text
1. 原始 LGA dot argmax：找 old loss 与 new loss 梯度方向最一致或最不冲突的层。
2. 替换式编辑 conflict score：找 old answer 与 new target 梯度方向最冲突的层。
```

对于 bridge 实体替换任务，old answer 与 target_new 往往是互斥答案。此时有效编辑层可能不是 `dot` 最大的层，而是 old/new 梯度冲突最强的层。

从这个角度看，结果反而支持当前暴力扫层现象：

```text
LLaVA: conflict signal 指向浅层，尤其 layer 1。
BLIP2: conflict signal 指向中层/中后层，尤其 layer 18/19/20/21。
```

### 6.4 后续命名建议

论文复现主结果仍保留：

```text
VLM-LGA-request-only-dot
```

替换式编辑层分析单独命名：

```text
VLM-LGA-request-conflict
```

其中：

```text
conflict_dot = -S_lga_dot
conflict_cos = -S_lga_cos
```

不能把 conflict ranking 写成原始 LGA 主公式结果，但可以作为解释 adapter 暴力扫层结果的补充证据。

## 7. 结果文件

LLaVA：

```text
server_results/bridge_vlm_lga_llava_train30/
```

BLIP2：

```text
server_results/bridge_vlm_lga_blip2_train30/
```

运行日志：

```text
server_results/bridge_vlm_lga_train30_run/
server_results/bridge_vlm_lga_blip2_rerun/
```
