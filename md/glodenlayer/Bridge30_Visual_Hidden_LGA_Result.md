# Bridge30 Visual-Hidden LGA 补充实验结果

## 1. 实验设置

本实验按照 `Visual-Hidden_LGA_补充实验安排.md` 执行，用于补充解释视觉 token hidden state 在不同层对实体识别目标的敏感性。

| 项目 | 设置 |
|---|---|
| 数据 | `Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json` |
| 模型 | LLaVA-v1.5-7B, BLIP2-OPT-2.7B |
| 候选层 | 0-31 |
| capture point | `adapter_hook`，与 adapter 插入点对齐 |
| LLaVA token scope | `visual` |
| BLIP2 token scope | `visual_prefix` |
| 梯度对象 | 每层视觉 token hidden state `h_vis^L` |
| 是否使用 adapter | 否 |
| base VLM 参数 | 全部冻结 |
| 主指标 | `S_vis_dot` |
| 重点解释指标 | `S_vis_new_norm` |

完整性检查：

```text
LLaVA sample rows = 960 = 32 layers * 30 requests
BLIP2 sample rows = 960 = 32 layers * 30 requests
old answer mapped cases = 30/30 for both models
gradient_target = visual_token_hidden_state_h_vis_L
base_requires_grad_params = 0
adapter_used = False
```

运行节点：

```text
g08: 无 active Slurm job，被 PAM 拒绝
g07: 成功运行，NVIDIA A800 80GB
```

## 2. LLaVA Visual-Hidden LGA

### 2.1 按 S_vis_dot 排名

| Dot Rank | Layer | S_vis_dot | S_vis_cos | S_vis_new_norm | S_vis_joint_norm | Positive Ratio | New-Norm Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 2.7759e-05 | -0.0975 | 0.0033 | 1.9211e-05 | 0.2000 | 31 |
| 2 | 31 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 32 |
| 3 | 29 | -3.9112e-05 | -0.1249 | 0.0045 | 3.3088e-05 | 0.2000 | 30 |
| 4 | 28 | -0.0001 | -0.1361 | 0.0098 | 0.0002 | 0.1333 | 29 |
| 5 | 21 | -0.0006 | -0.1307 | 0.0355 | 0.0025 | 0.2000 | 22 |

严格 dot top-k：

```text
LLaVA visual dot top-5 = [30, 31, 29, 28, 21]
LLaVA visual cos top-5 = [31, 30, 29, 21, 28]
```

注意：layer 31 的 hidden 梯度全为 0，却因为多数层 dot 为负而进入 dot/cos top-k。这与之前 Adapter-LGA 中 layer 31 的零梯度退化类似，不能单独解释为强视觉编辑层。

### 2.2 按 S_vis_new_norm 排名

| New-Norm Rank | Layer | S_vis_new_norm | S_vis_dot | S_vis_cos | S_vis_joint_norm | Positive Ratio | Dot Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 0.2333 | -1.0867 | -0.3040 | 0.1087 | 0.0333 | 30 |
| 2 | 7 | 0.2331 | -1.0423 | -0.2968 | 0.1070 | 0.0333 | 25 |
| 3 | 5 | 0.2316 | -1.0973 | -0.3045 | 0.1086 | 0.0333 | 32 |
| 4 | 3 | 0.2293 | -1.0886 | -0.2996 | 0.1086 | 0.0333 | 31 |
| 5 | 4 | 0.2292 | -1.0614 | -0.3015 | 0.1059 | 0.0333 | 27 |

视觉目标敏感层：

```text
LLaVA visual new-norm top-5 = [6, 7, 5, 3, 4]
LLaVA visual joint-norm top-5 = [6, 3, 5, 0, 7]
```

解释：LLaVA 的 old-new dot 更偏后层，但 target_new 对视觉 token hidden state 的敏感度集中在浅层到中浅层，尤其是 layer 5-7。这更适合解释“视觉实体识别/visual grounding”相关的编辑候选。

## 3. BLIP2 Visual-Hidden LGA

### 3.1 按 S_vis_dot 排名

| Dot Rank | Layer | S_vis_dot | S_vis_cos | S_vis_new_norm | S_vis_joint_norm | Positive Ratio | New-Norm Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 0.0098 | 0.0344 | 0.0842 | 0.0035 | 0.5333 | 31 |
| 2 | 29 | 0.0039 | 0.0129 | 0.1110 | 0.0056 | 0.5333 | 30 |
| 3 | 28 | 0.0027 | 0.0007 | 0.1316 | 0.0078 | 0.6000 | 29 |
| 4 | 31 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 32 |
| 5 | 27 | -0.0048 | -0.0145 | 0.1600 | 0.0123 | 0.4000 | 28 |

严格 dot top-k：

```text
BLIP2 visual dot top-5 = [30, 29, 28, 31, 27]
BLIP2 visual cos top-5 = [30, 29, 28, 31, 0]
```

### 3.2 按 S_vis_new_norm 排名

| New-Norm Rank | Layer | S_vis_new_norm | S_vis_dot | S_vis_cos | S_vis_joint_norm | Positive Ratio | Dot Rank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0.4648 | -0.2010 | -0.0118 | 0.1474 | 0.5000 | 16 |
| 2 | 1 | 0.4621 | -0.2157 | -0.0166 | 0.1448 | 0.5000 | 18 |
| 3 | 2 | 0.4565 | -0.2298 | -0.0219 | 0.1403 | 0.4667 | 20 |
| 4 | 3 | 0.4559 | -0.2321 | -0.0234 | 0.1392 | 0.4667 | 21 |
| 5 | 4 | 0.4517 | -0.2328 | -0.0258 | 0.1362 | 0.4333 | 22 |

视觉目标敏感层：

```text
BLIP2 visual new-norm top-5 = [0, 1, 2, 3, 4]
BLIP2 visual joint-norm top-5 = [0, 1, 2, 3, 4]
```

解释：BLIP2 的 visual-prefix 对 target_new 的敏感度集中在 decoder 浅层，但 old-new dot 仍然偏后层。这说明“目标视觉敏感层”和“old/new 梯度方向一致层”不是同一个问题。

## 4. 与已有结果对比

| Model | MLP-LGA dot top-5 | Adapter-LGA dot top-5 | Adapter conflict top-5 | Visual-Hidden dot top-5 | Visual new-norm top-5 | Brute-force 参考 |
|---|---|---|---|---|---|---|
| LLaVA | [26, 27, 0, 25, 24] | [31, 30, 29, 28, 26] | [1, 2, 3, 0, 4] | [30, 31, 29, 28, 21] | [6, 7, 5, 3, 4] | 浅层/中浅层更值得验证 |
| BLIP2 | [30, 29, 28, 27, 31] | [4, 0, 5, 26, 1] | [14, 15, 16, 13, 11] | [30, 29, 28, 31, 27] | [0, 1, 2, 3, 4] | 中层候选仍需靠暴力扫层确认 |

## 5. 结论

本补充实验不替代 Adapter-LGA，也不直接给最终编辑层。它回答的是：

```text
视觉 token hidden state 在哪一层最受 target_new 监督信号影响？
```

结论：

1. LLaVA 的 `S_vis_dot` 偏后层，但 `S_vis_new_norm` 集中在 layer 5-7，说明 target_new 对视觉表征的强敏感区在浅层到中浅层。
2. BLIP2 的 `S_vis_dot` 偏后层，而 `S_vis_new_norm` 集中在 layer 0-4，说明 visual prefix 在 decoder 浅层最敏感，但这不等价于最终 adapter 编辑层。
3. 两个模型都出现 layer 31 零梯度进入 dot/cos top-k 的现象，报告时应标注为退化排序信号。
4. 后续真实编辑层仍应由 adapter 暴力扫层训练和编辑指标决定；本实验主要用于解释 visual hidden sensitivity。

建议后续暴力验证时保留：

```text
LLaVA: visual new-norm [6, 7, 5, 3, 4]，并结合 adapter conflict [1, 2, 3, 0, 4]
BLIP2: visual new-norm [0, 1, 2, 3, 4]，并结合 adapter conflict [14, 15, 16, 13, 11]
```

## 6. 输出文件

```text
server_results/bridge_vlm_visual_hidden_lga_llava_train30/
server_results/bridge_vlm_visual_hidden_lga_blip2_train30/
server_results/bridge_vlm_visual_hidden_lga_train30_run/
```

关键文件：

```text
run_config.json
old_answer_mapping_report.json
sample_visual_hidden_scores.jsonl
visual_hidden_lga_layer_scores.csv
topk_visual_hidden_layers.json
summary.md
```
