# Bridge30 Adapter-Output LGA 结果

## 1. 实验设置

本实验按照 `Adapter-Output_LGA_实验方案.md` 执行，用于评估：

```text
adapter 挂在模型第 L 层时，它输出的视觉修正量 delta_h_vis 是否适合驱动 old answer -> target_new 的实体替换。
```

| 项目 | 设置 |
|---|---|
| 数据 | `Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json` |
| 模型 | LLaVA-v1.5-7B, BLIP2-OPT-2.7B |
| 候选层 | 0-31 |
| Adapter | `InstrumentedVisionEditAdaptor`，结构等同 `VisionEditAdaptor`，额外捕获 `delta_h_vis` |
| 捕获对象 | `delta_h_vis` |
| 梯度对象 | `adapter_output_delta_h_vis_L` |
| 是否训练 adapter | 否 |
| 是否加载 adapter checkpoint | 否 |
| base VLM 参数 | 全部冻结 |
| edit signal | old/new loss 均使用 `target_new` 构造的同一个 edit signal |
| 主指标 | `S_out_dot` |
| 辅助指标 | `S_out_conflict=-S_out_dot`, `S_out_new_norm`, `S_out_cos` |

运行节点：

```text
g08: 无 active Slurm job，被 PAM 拒绝
g07: 成功运行，NVIDIA A800 80GB
```

完整性检查：

```text
LLaVA sample rows = 960 = 32 layers * 30 requests
BLIP2 sample rows = 960 = 32 layers * 30 requests
old answer mapped cases = 30/30 for both models
gradient_target = adapter_output_delta_h_vis_L
base_requires_grad_params = 0
adapter_used = True
```

## 2. LLaVA Adapter-Output LGA

### 2.1 按 S_out_dot 排名

| Dot Rank | Layer | S_out_dot | S_out_cos | S_out_new_norm | S_out_joint_norm | Positive Ratio | Conflict Rank | New-Norm Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 1.2650e-05 | -0.0964 | 0.0033 | 1.8582e-05 | 0.2000 | 32 | 31 |
| 2 | 31 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 31 | 32 |
| 3 | 29 | -6.3733e-05 | -0.1287 | 0.0046 | 3.4623e-05 | 0.2000 | 30 | 30 |
| 4 | 28 | -0.0002 | -0.1265 | 0.0099 | 0.0002 | 0.1333 | 29 | 29 |
| 5 | 26 | -0.0017 | -0.1510 | 0.0183 | 0.0005 | 0.1667 | 28 | 27 |

严格 dot top-k：

```text
LLaVA adapter-output dot top-5 = [30, 31, 29, 28, 26]
LLaVA adapter-output cos top-5 = [31, 30, 28, 29, 21]
```

注意：layer 31 为零梯度层，`S_out_new_norm=0`、`S_out_joint_norm=0`，但因为其它层 dot 多为负值，进入 dot/cos top-k。它应标记为 zero-gradient degenerate layer。

### 2.2 按 conflict 排名

| Conflict Rank | Layer | S_out_dot | S_out_cos | S_out_new_norm | S_out_joint_norm | Positive Ratio | Dot Rank | New-Norm Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3 | -0.9590 | -0.3236 | 0.2212 | 0.0975 | 0.0000 | 32 | 1 |
| 2 | 0 | -0.8824 | -0.3060 | 0.2173 | 0.0975 | 0.0000 | 31 | 3 |
| 3 | 4 | -0.8483 | -0.3105 | 0.2170 | 0.0941 | 0.0333 | 30 | 4 |
| 4 | 2 | -0.8288 | -0.3139 | 0.2112 | 0.0906 | 0.0000 | 29 | 8 |
| 5 | 5 | -0.7862 | -0.2874 | 0.2141 | 0.0905 | 0.0667 | 28 | 5 |

```text
LLaVA adapter-output conflict top-5 = [3, 0, 4, 2, 5]
```

### 2.3 按 new-norm 排名

| New-Norm Rank | Layer | S_out_new_norm | S_out_dot | S_out_cos | S_out_joint_norm | Positive Ratio | Dot Rank | Conflict Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 0.2212 | -0.9590 | -0.3236 | 0.0975 | 0.0000 | 32 | 1 |
| 2 | 6 | 0.2181 | -0.7017 | -0.2754 | 0.0882 | 0.0333 | 25 | 8 |
| 3 | 0 | 0.2173 | -0.8824 | -0.3060 | 0.0975 | 0.0000 | 31 | 2 |
| 4 | 4 | 0.2170 | -0.8483 | -0.3105 | 0.0941 | 0.0333 | 30 | 3 |
| 5 | 5 | 0.2141 | -0.7862 | -0.2874 | 0.0905 | 0.0667 | 28 | 5 |

```text
LLaVA adapter-output new-norm top-5 = [3, 6, 0, 4, 5]
```

解释：LLaVA 的 adapter 输出修正量在浅层最容易形成 old/new 替换冲突，并且 target_new 对浅层输出也最敏感。这比 Adapter-Parameter LGA 的严格 dot top-k 更接近“浅层 adapter 有效”的编辑直觉。

## 3. BLIP2 Adapter-Output LGA

### 3.1 按 S_out_dot 排名

| Dot Rank | Layer | S_out_dot | S_out_cos | S_out_new_norm | S_out_joint_norm | Positive Ratio | Conflict Rank | New-Norm Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 0.0078 | 0.0311 | 0.0834 | 0.0033 | 0.5333 | 32 | 31 |
| 2 | 29 | 0.0045 | 0.0169 | 0.1109 | 0.0056 | 0.6000 | 31 | 30 |
| 3 | 28 | 0.0033 | 0.0030 | 0.1319 | 0.0078 | 0.6000 | 30 | 29 |
| 4 | 31 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 29 | 32 |
| 5 | 27 | -0.0036 | -0.0107 | 0.1609 | 0.0124 | 0.4000 | 28 | 28 |

严格 dot top-k：

```text
BLIP2 adapter-output dot top-5 = [30, 29, 28, 31, 27]
BLIP2 adapter-output cos top-5 = [30, 29, 4, 8, 10]
```

### 3.2 按 conflict 排名

| Conflict Rank | Layer | S_out_dot | S_out_cos | S_out_new_norm | S_out_joint_norm | Positive Ratio | Dot Rank | New-Norm Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3 | -0.2318 | -0.0209 | 0.4503 | 0.1312 | 0.5000 | 32 | 5 |
| 2 | 14 | -0.2274 | -0.0483 | 0.4044 | 0.1039 | 0.4667 | 31 | 15 |
| 3 | 2 | -0.2265 | -0.0238 | 0.4439 | 0.1278 | 0.5000 | 30 | 9 |
| 4 | 15 | -0.2155 | -0.0514 | 0.3928 | 0.0972 | 0.4667 | 29 | 16 |
| 5 | 0 | -0.1997 | -0.0083 | 0.4652 | 0.1473 | 0.5000 | 28 | 3 |

```text
BLIP2 adapter-output conflict top-5 = [3, 14, 2, 15, 0]
```

### 3.3 按 new-norm 排名

| New-Norm Rank | Layer | S_out_new_norm | S_out_dot | S_out_cos | S_out_joint_norm | Positive Ratio | Dot Rank | Conflict Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 0.4745 | -0.0991 | 0.0101 | 0.1438 | 0.5000 | 16 | 17 |
| 2 | 5 | 0.4665 | -0.1000 | 0.0040 | 0.1409 | 0.4333 | 17 | 16 |
| 3 | 0 | 0.4652 | -0.1997 | -0.0083 | 0.1473 | 0.5000 | 28 | 5 |
| 4 | 1 | 0.4567 | -0.1985 | -0.0166 | 0.1396 | 0.4667 | 27 | 6 |
| 5 | 3 | 0.4503 | -0.2318 | -0.0209 | 0.1312 | 0.5000 | 32 | 1 |

```text
BLIP2 adapter-output new-norm top-5 = [4, 5, 0, 1, 3]
```

解释：BLIP2 的 adapter-output new-norm 仍偏浅层；但 conflict top-k 同时包含 layer 14/15，说明浅层 visual prefix 很敏感，中层可能更体现可控替换冲突。这与之前 Adapter conflict 中层候选 `[14, 15, 16, 13, 11]` 有部分一致。

## 4. 与已有实验对比

| Model | MLP-LGA top-5 | Adapter-Parameter dot top-5 | Adapter-Output dot top-5 | Adapter-Output conflict top-5 | Adapter-Output new-norm top-5 | Visual-Hidden new-norm top-5 |
|---|---|---|---|---|---|---|
| LLaVA | [26, 27, 0, 25, 24] | [31, 30, 29, 28, 26] | [30, 31, 29, 28, 26] | [3, 0, 4, 2, 5] | [3, 6, 0, 4, 5] | [6, 7, 5, 3, 4] |
| BLIP2 | [30, 29, 28, 27, 31] | [4, 0, 5, 26, 1] | [30, 29, 28, 31, 27] | [3, 14, 2, 15, 0] | [4, 5, 0, 1, 3] | [0, 1, 2, 3, 4] |

## 5. 结论

严格按照 Adapter-Output LGA 的 `S_out_dot` 主公式：

```text
LLaVA: [30, 31, 29, 28, 26]
BLIP2: [30, 29, 28, 31, 27]
```

但对实体替换编辑更有解释价值的是 conflict 和 new-norm：

```text
LLaVA adapter-output conflict: [3, 0, 4, 2, 5]
LLaVA adapter-output new-norm: [3, 6, 0, 4, 5]

BLIP2 adapter-output conflict: [3, 14, 2, 15, 0]
BLIP2 adapter-output new-norm: [4, 5, 0, 1, 3]
```

综合解释：

1. LLaVA 的 adapter 输出修正量在浅层最有替换冲突和 target_new 敏感性，支持后续重点验证浅层/中浅层。
2. BLIP2 的 target_new 输出敏感性偏浅层，但 conflict 指标出现 layer 14/15，提示 BLIP2 可能存在“浅层敏感、中层更可控替换”的结构。
3. layer 31 仍是零梯度退化层，应标注但不作为真实候选。
4. 最终编辑层仍应由暴力扫层训练 adapter 后结合编辑指标确定。

## 6. 输出文件

```text
server_results/bridge_vlm_adapter_output_lga_llava_train30/
server_results/bridge_vlm_adapter_output_lga_blip2_train30/
server_results/bridge_vlm_adapter_output_lga_train30_run/
```

关键文件：

```text
run_config.json
old_answer_mapping_report.json
sample_adapter_output_scores.jsonl
adapter_output_lga_layer_scores.csv
topk_adapter_output_layers.json
summary.md
```
