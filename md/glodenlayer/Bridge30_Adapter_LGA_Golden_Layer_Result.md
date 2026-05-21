# Bridge30 Adapter-LGA Golden Layer 结果

## 1. 实验设置

本次按照 `bridge3_golden_layer_operation_manual1.md` 重新计算 adapter-aware LGA。

| 项目 | 设置 |
|---|---|
| 数据 | `Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json` |
| 模型 | LLaVA-v1.5-7B, BLIP2-OPT-2.7B |
| 候选层 | 0-31 |
| Adapter | `VisionEditAdaptor` |
| 梯度对象 | 当前候选层 adapter 参数 `phi_L` |
| 冻结对象 | base VLM 全部参数 `theta` |
| 主指标 | `S_adapter_dot = sum_i dot(grad_phi_L L_old, grad_phi_L L_new)` |
| 诊断指标 | `S_adapter_cos`, adapter grad norm, joint norm, norm ratio |
| 不参与 | generality, locality, portability |

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
gradient_target = adapter_parameters_phi_L
base_requires_grad_params = 0
```

## 2. LLaVA Adapter-LGA 结果

按主公式 `S_adapter_dot` 排序：

| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Dot Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 31 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 32 |
| 2 | 30 | -0.9444 | -0.0944 | 0.5053 | 0.0027 | 31 |
| 3 | 29 | -1.3443 | -0.0878 | 0.6444 | 0.0034 | 30 |
| 4 | 28 | -4.1928 | -0.0985 | 1.7042 | 0.0090 | 29 |
| 5 | 26 | -9.1802 | -0.1048 | 2.8483 | 0.0151 | 28 |

Top-k：

```text
Adapter dot top-5 = [31, 30, 29, 28, 26]
Adapter cos top-5 = [31, 24, 22, 23, 29]
Adapter conflict dot top-5 = [1, 2, 3, 0, 4]
Adapter conflict cos top-5 = [2, 0, 1, 3, 4]
```

注意：LLaVA 的 dot top-1 layer 31 是零梯度层，`joint_norm = 0`。这是一个退化信号：因为其它层的 dot 都是负值，零值被 `argmax` 选中，但它不代表强编辑承载能力。因此后续暴力扫层不建议只看 layer 31。

更适合进入后续编辑验证的 LLaVA 候选层：

```text
主公式保留: [31, 30, 29, 28, 26]
非零梯度 dot 候选: [30, 29, 28, 26]
替换冲突候选: [1, 2, 3, 0, 4]
```

## 3. BLIP2 Adapter-LGA 结果

按主公式 `S_adapter_dot` 排序：

| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Dot Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 105.2999 | 0.0278 | 156.2911 | 1.7367 | 32 |
| 2 | 0 | 92.9082 | 0.0354 | 117.5063 | 1.3058 | 31 |
| 3 | 5 | 24.2265 | 0.0086 | 156.5969 | 1.7401 | 30 |
| 4 | 26 | 5.4182 | 0.0108 | 8.1247 | 0.0903 | 29 |
| 5 | 1 | 3.1742 | 0.0132 | 125.7861 | 1.3978 | 28 |

Top-k：

```text
Adapter dot top-5 = [4, 0, 5, 26, 1]
Adapter cos top-5 = [0, 4, 30, 29, 10]
Adapter conflict dot top-5 = [14, 15, 16, 13, 11]
Adapter conflict cos top-5 = [14, 16, 15, 17, 18]
```

更适合进入后续编辑验证的 BLIP2 候选层：

```text
主公式候选: [4, 0, 5, 26, 1]
cos 辅助候选: [0, 4, 30, 29, 10]
替换冲突候选: [14, 15, 16, 13, 11]
```

## 4. 与旧版 MLP-LGA 对比

| Model | MLP-LGA dot top-5 | Adapter-LGA dot top-5 | Adapter conflict top-5 | 观察 |
|---|---|---|---|---|
| LLaVA | [26, 27, 0, 25, 24] | [31, 30, 29, 28, 26] | [1, 2, 3, 0, 4] | 主公式偏后层且出现零梯度退化；conflict 更接近浅层编辑直觉 |
| BLIP2 | [30, 29, 28, 27, 31] | [4, 0, 5, 26, 1] | [14, 15, 16, 13, 11] | adapter 梯度后，主公式从后层转向浅层；conflict 给出中层候选 |

## 5. 结论

严格按新手册主公式，候选层为：

```text
LLaVA Adapter-LGA: [31, 30, 29, 28, 26]
BLIP2 Adapter-LGA: [4, 0, 5, 26, 1]
```

但从“后续要暴力搜索真实编辑层”的角度，更建议保留两组候选：

```text
LLaVA: [30, 29, 28, 26] + conflict [1, 2, 3, 0, 4]
BLIP2: [4, 0, 5, 26, 1] + conflict [14, 15, 16, 13, 11]
```

解释：

1. Adapter-LGA 与旧 MLP-LGA 的候选明显不同，说明不能把“直接改原模型参数”的层结论照搬到 adapter 编辑。
2. LLaVA 的主公式结果存在 layer 31 零梯度退化，需在报告和后续实验中单独标注。
3. BLIP2 的 adapter conflict 候选集中在 14-16 层，这与“BLIP2 编辑层可能在中层”的假设更接近。
4. 最终编辑层仍应由暴力扫层训练 adapter 并结合编辑指标确定；本结果只作为 candidate layer 生成。

## 6. 输出文件

```text
server_results/bridge_vlm_adapter_lga_llava_train30/
server_results/bridge_vlm_adapter_lga_blip2_train30/
server_results/bridge_vlm_adapter_lga_train30_run/
```

关键文件：

```text
adapter_lga_layer_scores.csv
topk_adapter_layers.json
summary.md
sample_adapter_layer_scores.jsonl
old_answer_mapping_report.json
run_config.json
```
