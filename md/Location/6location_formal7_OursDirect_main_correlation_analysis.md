# 7模型 × 3数据集：正式七方法与Ours-Direct主公式相关性分析数据表

生成日期：2026-08-24。本文档是从原综合记录中抽离出的当前正式分析口径，只服务于七方法公平比较；旧4个Ours深度加权指标、Perturb-KL Pre消融及历史冻结并集均不进入本文件。

## 1. 正式比较口径

- 正式方法固定为7类：`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct`、`CMA-Direct`。
- Ours唯一主公式：`M_abscos_x_newn = |S_v_cos| × S_v_new_norm`，不含深度加权。
- 真实编辑效果比较只使用主配置结果；stable、真正改变训练配置的recovered run和numeric anomaly必须保留标签，禁止跨配置取最大值。本次`RECOVERED_G09_NODEFAIL`仅表示从节点故障现场恢复原主配置产物，训练配置未改变，因此仍登记为`variant=main`。
- 缺失层不按0分；只有候选Top-K全部具有`selected_checkpoint.tsv + eval_full.done + 完整独立test/eval`时，才计算该方法在该组合上的正式Best@K和Mean@K。
- 当前服务器增量已计入：截至2026-08-24，新增的EVQA/InstructBLIP 12层、EVQA/MiniGPT-4 12层、MMKE-visual/LLaVA 8层和MMKE-entity/MiniGPT-4 10层均已用非空`selected_checkpoint.tsv + eval_full.done`及对应独立test/eval交叉验收；连同历史结果，正式Top-3完整可比组合达到17/21。

## 2. 七种方法的定位原理

| 方法 | 类型 | 定位原理 |
|---|---|---|
| `Middle-Prior-Direct` | 结构先验 | 按模型深度中点附近排序；不使用数据集梯度。 |
| `VisEdit-Contrib-Pre-KeyToken` | 贡献度 | 比较关键token路径上的层贡献，按贡献分数选择Top-K。 |
| `SaLEM-Alt-Direct` | 参数梯度 | 以替代目标下的参数梯度绝对值聚合衡量层敏感性。 |
| `LGA-Param-Direct-AltModelPred` | 新旧知识梯度交互 | 使用新旧目标参数梯度的点积衡量层级更新一致性。 |
| `Perturb-KL-Direct-AltSeq` | 扰动敏感度 | 扰动视觉token后计算输出KL变化，选择对视觉扰动最敏感的层。 |
| `Ours-Direct` | 视觉梯度方向×幅值 | 主公式 `M_abscos_x_newn = |S_v_cos| × S_v_new_norm`；不使用深度权重。 |
| `CMA-Direct` | 因果中介恢复 | 污染视觉输入并逐层恢复hidden state，以因果恢复增益选择层。 |

可靠性提示：EVQA的7个VisEdit组合仍为历史FirstToken结果而非严格KeyToken；LGA有4组、CMA有13组为低coverage。候选层仍列出，但论文结论必须保留这些限制。

## 3. 21组各方法Top-3/Top-5及当前主配置评测覆盖

`n/3`或`n/5`表示对应候选层中已有多少层具备主配置完整评测。Best/Mean只在候选全部完成时给出；部分完成不计算正式值，避免幸存者偏差。

### 3.1 EVQA-pilot500

| Model | Method | Top-3 | 完成 | Best@3 | Mean@3 | Top-5 | 完成 | Best@5 | Mean@5 | 可靠性 |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---|
| BLIP2-OPT-2.7B | Middle | L15,L16,L14 | 3/3 | 75.192 | 74.011 | L15,L16,L14,L17,L13 | 4/5 | - | - | eligible |
| BLIP2-OPT-2.7B | VisEdit | L20,L19,L18 | 3/3 | 74.850 | 73.310 | L20,L19,L18,L17,L16 | 5/5 | 75.600 | 73.866 | historical_firsttoken_not_strict_keytoken |
| BLIP2-OPT-2.7B | SaLEM | L0,L18,L19 | 3/3 | 74.850 | 68.403 | L0,L18,L19,L17,L21 | 5/5 | 75.600 | 70.428 | eligible |
| BLIP2-OPT-2.7B | LGA | L0,L1,L3 | 3/3 | 62.460 | 59.709 | L0,L1,L3,L4,L16 | 5/5 | 73.800 | 62.038 | eligible |
| BLIP2-OPT-2.7B | Perturb-KL | L3,L4,L2 | 3/3 | 62.460 | 56.617 | L3,L4,L2,L1,L5 | 5/5 | 68.890 | 59.450 | eligible |
| BLIP2-OPT-2.7B | Ours-Direct | L0,L1,L2 | 3/3 | 58.506 | 55.598 | L0,L1,L2,L3,L4 | 5/5 | 62.460 | 57.304 | eligible |
| BLIP2-OPT-2.7B | CMA | L4,L2,L5 | 3/3 | 68.890 | 58.761 | L4,L2,L5,L3,L1 | 5/5 | 68.890 | 59.450 | low_candidate_coverage |
| InstructBLIP-Vicuna-7B | Middle | L15,L16,L14 | 3/3 | 49.910 | 49.757 | L15,L16,L14,L17,L13 | 3/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | VisEdit | L28,L27,L26 | 3/3 | 53.270 | 52.327 | L28,L27,L26,L25,L24 | 4/5 | - | - | historical_firsttoken_not_strict_keytoken |
| InstructBLIP-Vicuna-7B | SaLEM | L0,L18,L19 | 3/3 | 52.254 | 49.110 | L0,L18,L19,L20,L17 | 3/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | LGA | L2,L0,L1 | 3/3 | 54.470 | 52.225 | L2,L0,L1,L4,L17 | 4/5 | - | - | low_candidate_coverage |
| InstructBLIP-Vicuna-7B | Perturb-KL | L2,L3,L4 | 3/3 | 50.474 | 49.436 | L2,L3,L4,L5,L6 | 3/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | Ours-Direct | L1,L0,L11 | 3/3 | 54.470 | 51.987 | L1,L0,L11,L9,L10 | 3/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | CMA | L1,L0,L25 | 3/3 | 54.470 | 52.807 | L1,L0,L25,L22,L2 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | Middle | L15,L16,L14 | 3/3 | 64.940 | 64.147 | L15,L16,L14,L17,L13 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | VisEdit | L26,L25,L24 | 3/3 | 58.470 | 57.813 | L26,L25,L24,L23,L22 | 4/5 | - | - | historical_firsttoken_not_strict_keytoken |
| MiniGPT-4-Vicuna-7B | SaLEM | L8,L9,L10 | 3/3 | 77.070 | 68.597 | L8,L9,L10,L5,L6 | 3/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | LGA | L29,L25,L22 | 3/3 | 58.554 | 58.517 | L29,L25,L22,L26,L21 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | Perturb-KL | L0,L1,L2 | 3/3 | 71.104 | 64.143 | L0,L1,L2,L3,L4 | 3/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | Ours-Direct | L18,L19,L16 | 3/3 | 64.940 | 60.959 | L18,L19,L16,L17,L21 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | CMA | L7,L1,L0 | 3/3 | 71.104 | 65.333 | L7,L1,L0,L2,L8 | 5/5 | 71.104 | 65.706 | low_candidate_coverage |
| LLaVA-v1.5-7B | Middle | L15,L16,L14 | 0/3 | - | - | L15,L16,L14,L17,L13 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | VisEdit | L28,L27,L26 | 3/3 | 62.990 | 62.093 | L28,L27,L26,L25,L24 | 3/5 | - | - | historical_firsttoken_not_strict_keytoken |
| LLaVA-v1.5-7B | SaLEM | L7,L6,L5 | 0/3 | - | - | L7,L6,L5,L8,L9 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | LGA | L24,L25,L26 | 1/3 | - | - | L24,L25,L26,L23,L27 | 2/5 | - | - | low_candidate_coverage |
| LLaVA-v1.5-7B | Perturb-KL | L0,L1,L2 | 0/3 | - | - | L0,L1,L2,L3,L4 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | Ours-Direct | L0,L1,L2 | 0/3 | - | - | L0,L1,L2,L3,L4 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | CMA | L0,L1,L4 | 0/3 | - | - | L0,L1,L4,L6,L10 | 0/5 | - | - | low_candidate_coverage |
| Qwen2.5-VL-3B | Middle | L17,L18,L16 | 3/3 | 63.550 | 62.970 | L17,L18,L16,L19,L15 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | VisEdit | L29,L28,L27 | 3/3 | 62.530 | 62.280 | L29,L28,L27,L26,L25 | 4/5 | - | - | historical_firsttoken_not_strict_keytoken |
| Qwen2.5-VL-3B | SaLEM | L11,L14,L12 | 3/3 | 63.390 | 62.630 | L11,L14,L12,L13,L15 | 3/5 | - | - | eligible |
| Qwen2.5-VL-3B | LGA | L2,L30,L1 | 3/3 | 62.520 | 62.077 | L2,L30,L1,L3,L10 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | Perturb-KL | L0,L1,L2 | 3/3 | 62.890 | 62.200 | L0,L1,L2,L3,L4 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | Ours-Direct | L21,L19,L17 | 3/3 | 63.740 | 63.183 | L21,L19,L17,L20,L18 | 5/5 | 63.740 | 63.042 | eligible |
| Qwen2.5-VL-3B | CMA | L1,L0,L3 | 3/3 | 62.890 | 61.980 | L1,L0,L3,L6,L4 | 3/5 | - | - | low_candidate_coverage |
| PaliGemma-3B | Middle | L8,L9,L7 | 3/3 | 81.000 | 64.270 | L8,L9,L7,L10,L6 | 5/5 | 81.000 | 66.000 | eligible |
| PaliGemma-3B | VisEdit | L12,L11,L10 | 3/3 | 80.990 | 75.830 | L12,L11,L10,L9,L8 | 5/5 | 81.000 | 68.930 | historical_firsttoken_not_strict_keytoken |
| PaliGemma-3B | SaLEM | L8,L7,L9 | 3/3 | 81.000 | 64.270 | L8,L7,L9,L10,L6 | 5/5 | 81.000 | 66.000 | eligible |
| PaliGemma-3B | LGA | L17,L7,L0 | 2/3 | - | - | L17,L7,L0,L8,L13 | 3/5 | - | - | low_candidate_coverage |
| PaliGemma-3B | Perturb-KL | L5,L7,L6 | 3/3 | 78.170 | 73.497 | L5,L7,L6,L3,L4 | 4/5 | - | - | eligible |
| PaliGemma-3B | Ours-Direct | L5,L4,L3 | 2/3 | - | - | L5,L4,L3,L6,L7 | 4/5 | - | - | eligible |
| PaliGemma-3B | CMA | L5,L4,L0 | 2/3 | - | - | L5,L4,L0,L3,L2 | 2/5 | - | - | low_candidate_coverage |
| SmolVLM-Instruct-1.7B | Middle | L11,L12,L10 | 3/3 | 69.810 | 66.327 | L11,L12,L10,L13,L9 | 5/5 | 69.810 | 65.298 | eligible |
| SmolVLM-Instruct-1.7B | VisEdit | L17,L16,L15 | 3/3 | 59.740 | 59.163 | L17,L16,L15,L14,L13 | 5/5 | 68.220 | 61.032 | historical_firsttoken_not_strict_keytoken |
| SmolVLM-Instruct-1.7B | SaLEM | L9,L8,L7 | 3/3 | 68.450 | 66.830 | L9,L8,L7,L6,L10 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | LGA | L22,L21,L20 | 3/3 | 57.150 | 56.463 | L22,L21,L20,L19,L18 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | Perturb-KL | L1,L2,L0 | 3/3 | 69.970 | 64.383 | L1,L2,L0,L4,L3 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | Ours-Direct | L0,L1,L2 | 3/3 | 69.970 | 64.383 | L0,L1,L2,L3,L4 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | CMA | L0,L1,L3 | 3/3 | 69.970 | 65.100 | L0,L1,L3,L2,L6 | 4/5 | - | - | low_candidate_coverage |

### 3.2 MMKE-visual

| Model | Method | Top-3 | 完成 | Best@3 | Mean@3 | Top-5 | 完成 | Best@5 | Mean@5 | 可靠性 |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---|
| BLIP2-OPT-2.7B | Middle | L15,L16,L14 | 3/3 | 71.390 | 70.810 | L15,L16,L14,L17,L13 | 4/5 | - | - | eligible |
| BLIP2-OPT-2.7B | VisEdit | L26,L25,L24 | 3/3 | 71.470 | 71.303 | L26,L25,L24,L23,L22 | 4/5 | - | - | eligible |
| BLIP2-OPT-2.7B | SaLEM | L0,L18,L19 | 3/3 | 71.370 | 68.343 | L0,L18,L19,L17,L20 | 5/5 | 71.810 | 69.612 | eligible |
| BLIP2-OPT-2.7B | LGA | L0,L1,L3 | 3/3 | 69.690 | 66.933 | L0,L1,L3,L4,L2 | 5/5 | 69.870 | 67.972 | eligible |
| BLIP2-OPT-2.7B | Perturb-KL | L3,L4,L2 | 3/3 | 69.870 | 69.267 | L3,L4,L2,L1,L5 | 4/5 | - | - | eligible |
| BLIP2-OPT-2.7B | Ours-Direct | L0,L1,L2 | 3/3 | 69.870 | 67.310 | L0,L1,L2,L4,L3 | 5/5 | 69.870 | 67.972 | eligible |
| BLIP2-OPT-2.7B | CMA | L3,L0,L1 | 3/3 | 69.690 | 66.933 | L3,L0,L1,L2,L4 | 5/5 | 69.870 | 67.972 | eligible |
| InstructBLIP-Vicuna-7B | Middle | L15,L16,L14 | 3/3 | 50.560 | 50.190 | L15,L16,L14,L17,L13 | 4/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | VisEdit | L28,L27,L26 | 3/3 | 50.590 | 50.177 | L28,L27,L26,L25,L24 | 5/5 | 50.590 | 50.226 | eligible |
| InstructBLIP-Vicuna-7B | SaLEM | L18,L17,L19 | 3/3 | 50.730 | 50.617 | L18,L17,L19,L20,L16 | 4/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | LGA | L2,L0,L4 | 3/3 | 71.290 | 57.277 | L2,L0,L4,L28,L1 | 5/5 | 71.290 | 58.416 | eligible |
| InstructBLIP-Vicuna-7B | Perturb-KL | L2,L3,L5 | 3/3 | 51.160 | 50.513 | L2,L3,L5,L4,L8 | 4/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | Ours-Direct | L1,L0,L3 | 3/3 | 71.290 | 64.243 | L1,L0,L3,L2,L4 | 5/5 | 71.290 | 58.654 | eligible |
| InstructBLIP-Vicuna-7B | CMA | L23,L22,L24 | 3/3 | 50.590 | 50.510 | L23,L22,L24,L19,L17 | 5/5 | 50.730 | 50.578 | eligible |
| MiniGPT-4-Vicuna-7B | Middle | L15,L16,L14 | 3/3 | 76.350 | 76.107 | L15,L16,L14,L17,L13 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | VisEdit | L26,L25,L24 | 3/3 | 74.320 | 74.170 | L26,L25,L24,L23,L22 | 3/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | SaLEM | L31,L5,L8 | 3/3 | 76.940 | 73.897 | L31,L5,L8,L6,L9 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | LGA | L0,L1,L3 | 3/3 | 76.634 | 76.090 | L0,L1,L3,L4,L25 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | Perturb-KL | L0,L1,L2 | 3/3 | 76.064 | 75.900 | L0,L1,L2,L3,L4 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | Ours-Direct | L9,L10,L11 | 3/3 | 76.830 | 76.681 | L9,L10,L11,L15,L14 | 5/5 | 76.830 | 76.452 | eligible |
| MiniGPT-4-Vicuna-7B | CMA | L0,L1,L2 | 3/3 | 76.064 | 75.900 | L0,L1,L2,L3,L4 | 4/5 | - | - | low_candidate_coverage |
| LLaVA-v1.5-7B | Middle | L15,L16,L14 | 3/3 | 76.514 | 76.002 | L15,L16,L14,L17,L13 | 3/5 | - | - | eligible |
| LLaVA-v1.5-7B | VisEdit | L28,L27,L26 | 3/3 | 74.396 | 73.783 | L28,L27,L26,L25,L24 | 4/5 | - | - | eligible |
| LLaVA-v1.5-7B | SaLEM | L7,L8,L9 | 3/3 | 77.008 | 76.823 | L7,L8,L9,L6,L10 | 3/5 | - | - | eligible |
| LLaVA-v1.5-7B | LGA | L24,L22,L27 | 3/3 | 74.586 | 74.274 | L24,L22,L27,L25,L23 | 3/5 | - | - | eligible |
| LLaVA-v1.5-7B | Perturb-KL | L0,L1,L2 | 3/3 | 76.786 | 75.861 | L0,L1,L2,L3,L4 | 4/5 | - | - | eligible |
| LLaVA-v1.5-7B | Ours-Direct | L0,L3,L1 | 3/3 | 76.186 | 75.661 | L0,L3,L1,L2,L5 | 4/5 | - | - | eligible |
| LLaVA-v1.5-7B | CMA | L0,L1,L2 | 3/3 | 76.786 | 75.861 | L0,L1,L2,L3,L4 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | Middle | L17,L18,L16 | 3/3 | 70.650 | 70.020 | L17,L18,L16,L19,L15 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | VisEdit | L28,L27,L26 | 3/3 | 68.350 | 68.243 | L28,L27,L26,L25,L24 | 3/5 | - | - | eligible |
| Qwen2.5-VL-3B | SaLEM | L12,L11,L14 | 3/3 | 71.000 | 70.607 | L12,L11,L14,L15,L13 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | LGA | L2,L30,L1 | 3/3 | 69.930 | 68.820 | L2,L30,L1,L3,L6 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | Perturb-KL | L0,L13,L14 | 3/3 | 70.420 | 70.210 | L0,L13,L14,L12,L15 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | Ours-Direct | L0,L1,L2 | 3/3 | 70.420 | 69.943 | L0,L1,L2,L3,L4 | 3/5 | - | - | eligible |
| Qwen2.5-VL-3B | CMA | L1,L0,L6 | 3/3 | 70.420 | 70.017 | L1,L0,L6,L7,L3 | 4/5 | - | - | low_candidate_coverage |
| PaliGemma-3B | Middle | L8,L9,L7 | 2/3 | - | - | L8,L9,L7,L10,L6 | 3/5 | - | - | eligible |
| PaliGemma-3B | VisEdit | L14,L13,L12 | 2/3 | - | - | L14,L13,L12,L11,L10 | 4/5 | - | - | eligible |
| PaliGemma-3B | SaLEM | L10,L8,L9 | 3/3 | 99.060 | 96.147 | L10,L8,L9,L7,L5 | 3/5 | - | - | eligible |
| PaliGemma-3B | LGA | L17,L0,L7 | 1/3 | - | - | L17,L0,L7,L8,L10 | 3/5 | - | - | eligible |
| PaliGemma-3B | Perturb-KL | L7,L5,L6 | 0/3 | - | - | L7,L5,L6,L8,L9 | 2/5 | - | - | eligible |
| PaliGemma-3B | Ours-Direct | L5,L4,L3 | 0/3 | - | - | L5,L4,L3,L2,L1 | 0/5 | - | - | eligible |
| PaliGemma-3B | CMA | L1,L2,L0 | 0/3 | - | - | L1,L2,L0,L3,L5 | 0/5 | - | - | low_candidate_coverage |
| SmolVLM-Instruct-1.7B | Middle | L11,L12,L10 | 3/3 | 69.620 | 69.160 | L11,L12,L10,L13,L9 | 5/5 | 69.830 | 69.352 | eligible |
| SmolVLM-Instruct-1.7B | VisEdit | L18,L17,L16 | 3/3 | 67.890 | 67.443 | L18,L17,L16,L15,L14 | 5/5 | 68.640 | 67.890 | eligible |
| SmolVLM-Instruct-1.7B | SaLEM | L9,L8,L0 | 3/3 | 71.360 | 70.157 | L9,L8,L0,L10,L7 | 5/5 | 71.360 | 70.116 | eligible |
| SmolVLM-Instruct-1.7B | LGA | L1,L7,L6 | 3/3 | 70.770 | 70.277 | L1,L7,L6,L8,L5 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | Perturb-KL | L1,L4,L0 | 3/3 | 71.360 | 70.690 | L1,L4,L0,L2,L5 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | Ours-Direct | L0,L1,L2 | 3/3 | 71.360 | 70.687 | L0,L1,L2,L3,L4 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | CMA | L0,L1,L15 | 3/3 | 71.360 | 70.007 | L0,L1,L15,L2,L7 | 5/5 | 71.360 | 70.262 | low_candidate_coverage |

### 3.3 MMKE-entity

| Model | Method | Top-3 | 完成 | Best@3 | Mean@3 | Top-5 | 完成 | Best@5 | Mean@5 | 可靠性 |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---|
| BLIP2-OPT-2.7B | Middle | L15,L16,L14 | 3/3 | 70.060 | 69.767 | L15,L16,L14,L17,L13 | 5/5 | 70.260 | 69.894 | eligible |
| BLIP2-OPT-2.7B | VisEdit | L22,L21,L20 | 3/3 | 70.630 | 70.293 | L22,L21,L20,L19,L18 | 5/5 | 70.630 | 70.278 | eligible |
| BLIP2-OPT-2.7B | SaLEM | L0,L18,L30 | 3/3 | 71.140 | 69.040 | L0,L18,L30,L19,L17 | 5/5 | 71.140 | 69.554 | eligible |
| BLIP2-OPT-2.7B | LGA | L16,L13,L18 | 3/3 | 70.120 | 69.827 | L16,L13,L18,L17,L15 | 5/5 | 70.260 | 69.906 | low_candidate_coverage |
| BLIP2-OPT-2.7B | Perturb-KL | L3,L2,L4 | 3/3 | 72.240 | 71.523 | L3,L2,L4,L1,L0 | 5/5 | 72.504 | 70.587 | eligible |
| BLIP2-OPT-2.7B | Ours-Direct | L0,L1,L2 | 3/3 | 72.504 | 69.895 | L0,L1,L2,L3,L4 | 5/5 | 72.504 | 70.587 | eligible |
| BLIP2-OPT-2.7B | CMA | L3,L0,L2 | 3/3 | 71.320 | 69.397 | L3,L0,L2,L4,L1 | 5/5 | 72.504 | 70.587 | eligible |
| InstructBLIP-Vicuna-7B | Middle | L15,L16,L14 | 3/3 | 48.840 | 48.733 | L15,L16,L14,L17,L13 | 4/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | VisEdit | L28,L27,L26 | 3/3 | 47.520 | 47.110 | L28,L27,L26,L25,L24 | 5/5 | 47.580 | 47.236 | eligible |
| InstructBLIP-Vicuna-7B | SaLEM | L18,L17,L19 | 3/3 | 48.930 | 48.717 | L18,L17,L19,L16,L20 | 4/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | LGA | L2,L28,L0 | 3/3 | 68.320 | 54.993 | L2,L28,L0,L4,L30 | 5/5 | 68.320 | 52.070 | eligible |
| InstructBLIP-Vicuna-7B | Perturb-KL | L5,L4,L3 | 3/3 | 50.020 | 49.037 | L5,L4,L3,L2,L8 | 4/5 | - | - | eligible |
| InstructBLIP-Vicuna-7B | Ours-Direct | L1,L0,L3 | 3/3 | 69.180 | 62.507 | L1,L0,L3,L2,L4 | 5/5 | 69.180 | 57.240 | eligible |
| InstructBLIP-Vicuna-7B | CMA | L23,L24,L22 | 3/3 | 48.330 | 47.910 | L23,L24,L22,L19,L17 | 5/5 | 48.930 | 48.252 | eligible |
| MiniGPT-4-Vicuna-7B | Middle | L15,L16,L14 | 3/3 | 76.236 | 75.933 | L15,L16,L14,L17,L13 | 3/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | VisEdit | L25,L24,L23 | 3/3 | 75.180 | 75.083 | L25,L24,L23,L22,L21 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | SaLEM | L31,L22,L24 | 3/3 | 76.270 | 75.430 | L31,L22,L24,L21,L23 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | LGA | L4,L3,L6 | 3/3 | 75.938 | 75.527 | L4,L3,L6,L0,L1 | 5/5 | 75.938 | 75.416 | eligible |
| MiniGPT-4-Vicuna-7B | Perturb-KL | L0,L1,L2 | 3/3 | 75.550 | 75.349 | L0,L1,L2,L3,L4 | 5/5 | 75.938 | 75.480 | eligible |
| MiniGPT-4-Vicuna-7B | Ours-Direct | L27,L28,L26 | 3/3 | 76.040 | 75.795 | L27,L28,L26,L25,L29 | 4/5 | - | - | eligible |
| MiniGPT-4-Vicuna-7B | CMA | L0,L1,L2 | 3/3 | 75.550 | 75.349 | L0,L1,L2,L3,L4 | 5/5 | 75.938 | 75.480 | low_candidate_coverage |
| LLaVA-v1.5-7B | Middle | L15,L16,L14 | 0/3 | - | - | L15,L16,L14,L17,L13 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | VisEdit | L28,L27,L26 | 0/3 | - | - | L28,L27,L26,L25,L24 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | SaLEM | L23,L22,L24 | 0/3 | - | - | L23,L22,L24,L25,L21 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | LGA | L1,L9,L7 | 0/3 | - | - | L1,L9,L7,L8,L6 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | Perturb-KL | L0,L1,L2 | 0/3 | - | - | L0,L1,L2,L3,L4 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | Ours-Direct | L13,L11,L12 | 0/3 | - | - | L13,L11,L12,L10,L9 | 0/5 | - | - | eligible |
| LLaVA-v1.5-7B | CMA | L0,L1,L2 | 0/3 | - | - | L0,L1,L2,L3,L4 | 0/5 | - | - | eligible |
| Qwen2.5-VL-3B | Middle | L17,L18,L16 | 3/3 | 71.590 | 71.423 | L17,L18,L16,L19,L15 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | VisEdit | L29,L28,L27 | 3/3 | 72.660 | 71.937 | L29,L28,L27,L26,L25 | 5/5 | 72.660 | 71.634 | eligible |
| Qwen2.5-VL-3B | SaLEM | L15,L14,L13 | 3/3 | 71.480 | 71.347 | L15,L14,L13,L16,L12 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | LGA | L2,L30,L1 | 3/3 | 72.410 | 72.243 | L2,L30,L1,L6,L3 | 3/5 | - | - | eligible |
| Qwen2.5-VL-3B | Perturb-KL | L0,L1,L2 | 3/3 | 72.280 | 72.180 | L0,L1,L2,L3,L14 | 4/5 | - | - | eligible |
| Qwen2.5-VL-3B | Ours-Direct | L0,L1,L2 | 3/3 | 72.280 | 72.180 | L0,L1,L2,L3,L6 | 3/5 | - | - | eligible |
| Qwen2.5-VL-3B | CMA | L1,L0,L2 | 3/3 | 72.280 | 72.180 | L1,L0,L2,L3,L6 | 3/5 | - | - | low_candidate_coverage |
| PaliGemma-3B | Middle | L8,L9,L7 | 3/3 | 96.300 | 90.610 | L8,L9,L7,L10,L6 | 5/5 | 96.980 | 81.418 | eligible |
| PaliGemma-3B | VisEdit | L12,L11,L10 | 3/3 | 90.670 | 57.857 | L12,L11,L10,L9,L8 | 5/5 | 96.300 | 71.056 | eligible |
| PaliGemma-3B | SaLEM | L17,L16,L13 | 3/3 | 48.650 | 45.340 | L17,L16,L13,L0,L10 | 5/5 | 48.650 | 38.860 | eligible |
| PaliGemma-3B | LGA | L17,L16,L7 | 3/3 | 90.120 | 59.163 | L17,L16,L7,L8,L13 | 5/5 | 96.300 | 64.488 | eligible |
| PaliGemma-3B | Perturb-KL | L7,L5,L6 | 3/3 | 96.980 | 92.637 | L7,L5,L6,L8,L9 | 5/5 | 96.980 | 91.924 | eligible |
| PaliGemma-3B | Ours-Direct | L5,L4,L3 | 3/3 | 96.136 | 93.305 | L5,L4,L3,L2,L6 | 5/5 | 96.980 | 91.787 | eligible |
| PaliGemma-3B | CMA | L0,L2,L1 | 3/3 | 88.860 | 63.633 | L0,L2,L1,L3,L7 | 5/5 | 92.970 | 74.798 | low_candidate_coverage |
| SmolVLM-Instruct-1.7B | Middle | L11,L12,L10 | 3/3 | 70.840 | 70.337 | L11,L12,L10,L13,L9 | 5/5 | 70.840 | 70.220 | eligible |
| SmolVLM-Instruct-1.7B | VisEdit | L18,L17,L16 | 3/3 | 71.470 | 70.550 | L18,L17,L16,L15,L14 | 5/5 | 71.470 | 70.100 | eligible |
| SmolVLM-Instruct-1.7B | SaLEM | L0,L1,L6 | 3/3 | 71.050 | 70.670 | L0,L1,L6,L7,L5 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | LGA | L1,L7,L0 | 3/3 | 71.050 | 70.607 | L1,L7,L0,L6,L8 | 4/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | Perturb-KL | L0,L1,L2 | 3/3 | 71.120 | 70.880 | L0,L1,L2,L3,L4 | 3/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | Ours-Direct | L0,L1,L2 | 3/3 | 71.120 | 70.880 | L0,L1,L2,L3,L4 | 3/5 | - | - | eligible |
| SmolVLM-Instruct-1.7B | CMA | L15,L18,L16 | 3/3 | 71.470 | 70.197 | L15,L18,L16,L19,L14 | 4/5 | - | - | eligible |

## 4. 正式七方法Top-3/Top-5并集与待补状态

`已完成`按主配置与stable-only分开；stable-only表示层已经做过，但不进入本文件的主配置性能均值。已知不收敛失败单列，不当作0分。

### 4.1 Top-3并集

| Dataset | Model | Top-3并集 | 层数 | 已完成（配置分开） | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | 主:L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | - | - | 0 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | 主:L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | - | - | 0 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | 主:L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | - | - | 0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4 | 15 | 主:L15,L16,L28,L27,L26 | - | L14,L7,L6,L5,L24,L25,L0,L1,L2,L4 | 10 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | 主:L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | - | - | 0 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | 主:L8,L9,L7,L12,L11,L10,L17,L5,L6,L4,L3 | L0 | - | 0 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | 主:L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | - | - | 0 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | 主:L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | - | - | 0 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | - | - | 0 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | 主:L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | - | - | 0 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | - | - | 0 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | 主:L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | - | - | 0 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3,L1,L2 | 15 | 主:L8,L9,L14,L12,L10,L17,L4；stable-only:L7,L13,L5,L6,L3,L1,L2 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | 主:L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | - | - | 0 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | 主:L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | - | - | 0 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | 主:L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | - | - | 0 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 17 | - | - | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 17 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | 主:L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | - | - | 0 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | 主:L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | 主:L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | - | - | 0 |

### 4.2 Top-5并集

| Dataset | Model | Top-5并集 | 层数 | 已完成（配置分开） | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 | 主:L15,L16,L14,L17,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | - | L13 | 1 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L22 | 24 | 主:L15,L16,L14,L28,L27,L26,L25,L0,L18,L19,L2,L1,L4,L3,L11 | - | L17,L13,L24,L20,L5,L6,L9,L10,L22 | 9 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19,L7 | 25 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L8,L9,L10,L29,L0,L1,L2,L18,L19,L7 | - | L13,L23,L5,L6,L21,L3,L4 | 7 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 22 | 主:L15,L16,L28,L27,L26 | - | L14,L17,L13,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 17 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L6 | 24 | 主:L17,L18,L16,L19,L29,L28,L27,L26,L11,L14,L12,L2,L30,L1,L3,L0,L21,L20 | - | L15,L25,L13,L10,L4,L6 | 6 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4,L2 | 14 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L5,L3,L4 | L0 | L13,L2 | 2 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3 | 22 | 主:L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L22,L21,L20,L19,L1,L2,L0,L3 | - | L6,L18,L4 | 3 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L0,L18,L19,L20,L1,L3,L4,L2 | - | L13,L23,L5 | 3 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L23,L22 | 22 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L1,L3,L5,L23,L22 | - | L13,L20,L8 | 3 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 | 主:L15,L16,L14,L17,L26,L25,L24,L31,L5,L8,L9,L0,L1,L3,L2,L10,L11 | - | L13,L23,L22,L6,L4 | 5 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 | 主:L15,L16,L14,L28,L27,L26,L24,L7,L8,L9,L22,L0,L1,L2,L3 | - | L17,L13,L25,L6,L10,L23,L4,L5 | 8 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4,L7 | 22 | 主:L17,L18,L16,L19,L28,L27,L26,L12,L11,L14,L13,L2,L30,L1,L6,L0,L7 | - | L15,L25,L24,L3,L4 | 5 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 | 主:L8,L9,L10,L14,L12,L11,L17,L4；stable-only:L7,L6,L13,L5,L3,L2,L1 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L4,L2 | - | L5,L3 | 2 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | 主:L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L23,L22 | 23 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L30,L5,L3,L1,L23,L22 | - | L13,L20,L8 | 3 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 | 主:L15,L16,L14,L25,L24,L23,L22,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26 | - | L17,L13,L21,L29 | 4 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 | - | - | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0 | 19 | 主:L17,L18,L16,L15,L29,L28,L27,L26,L25,L14,L13,L2,L30,L1,L0 | - | L19,L12,L6,L3 | 4 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4,L19 | 20 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L2 | - | L5,L8,L3,L4,L19 | 5 |

## 5. 当前可公平比较组合与阶段性结果

公平组合要求同一`dataset × model`下七种方法的Top-K候选全部已有主配置完整评测。以下结果用于阶段性核验，不把不完整组合混入平均值。

### 5.1 Top-3

完整可比组合：**17/21**。

组合：EVQA-pilot500 × BLIP2-OPT-2.7B；EVQA-pilot500 × InstructBLIP-Vicuna-7B；EVQA-pilot500 × MiniGPT-4-Vicuna-7B；EVQA-pilot500 × Qwen2.5-VL-3B；EVQA-pilot500 × SmolVLM-Instruct-1.7B；MMKE-visual × BLIP2-OPT-2.7B；MMKE-visual × InstructBLIP-Vicuna-7B；MMKE-visual × MiniGPT-4-Vicuna-7B；MMKE-visual × LLaVA-v1.5-7B；MMKE-visual × Qwen2.5-VL-3B；MMKE-visual × SmolVLM-Instruct-1.7B；MMKE-entity × BLIP2-OPT-2.7B；MMKE-entity × InstructBLIP-Vicuna-7B；MMKE-entity × MiniGPT-4-Vicuna-7B；MMKE-entity × Qwen2.5-VL-3B；MMKE-entity × PaliGemma-3B；MMKE-entity × SmolVLM-Instruct-1.7B。

| Method | 可比组合数 | Mean Best@3 | Mean Mean@3 | Mean Regret@3↓ | Hit@3 |
|---|---:|---:|---:|---:|---:|
| Ours-Direct | 17 | 70.873（1） | 68.541（1） | 1.984（1） | 41.2%（1） |
| LGA | 17 | 69.177（2） | 65.001（6） | 3.680（2） | 11.8%（6） |
| Middle | 17 | 68.962（3） | 68.018（2） | 3.895（3） | 5.9%（7） |
| Perturb-KL | 17 | 68.868（4） | 67.107（3） | 3.990（4） | 17.6%（4） |
| CMA | 17 | 68.826（5） | 65.404（4） | 4.031（5） | 23.5%（3） |
| VisEdit | 17 | 67.294（6） | 64.873（7） | 5.563（6） | 17.6%（4） |
| SaLEM | 17 | 67.173（7） | 65.092（5） | 5.684（7） | 35.3%（2） |

阶段性结论：扩展到17个完整可比组合后，Ours-Direct的Mean Best@3、Mean Mean@3和Hit@3仍为七方法最高，Mean Regret@3仍为最低，四项指标均排名第1。

Ours相对其他方法的配对Best@3差值（同一完整组合，正值表示Ours更高）：

| 对比方法 | Ours平均差值 | 胜/平/负 |
|---|---:|---:|
| Middle | +1.911 | 10/1/6 |
| VisEdit | +3.579 | 13/0/4 |
| SaLEM | +3.700 | 9/1/7 |
| LGA | +1.696 | 13/2/2 |
| Perturb-KL | +2.006 | 7/6/4 |
| CMA | +2.047 | 8/5/4 |

### 5.2 Top-5

完整可比组合：**2/21**。

组合：MMKE-entity × BLIP2-OPT-2.7B；MMKE-entity × PaliGemma-3B。

| Method | 可比组合数 | Mean Best@5 | Mean Mean@5 | Mean Regret@5↓ | Hit@5 |
|---|---:|---:|---:|---:|---:|
| Perturb-KL | 2 | 84.742 | 81.255 | 0.000 | 100.0% |
| Ours-Direct | 2 | 84.742 | 81.187 | 0.000 | 100.0% |
| Middle | 2 | 83.620 | 75.656 | 1.122 | 50.0% |
| VisEdit | 2 | 83.465 | 70.667 | 1.277 | 0.0% |
| LGA | 2 | 83.280 | 67.197 | 1.462 | 0.0% |
| CMA | 2 | 82.737 | 72.692 | 2.005 | 50.0% |
| SaLEM | 2 | 59.895 | 54.207 | 24.847 | 0.0% |

Ours相对其他方法的配对Best@5差值（同一完整组合，正值表示Ours更高）：

| 对比方法 | Ours平均差值 | 胜/平/负 |
|---|---:|---:|
| Middle | +1.122 | 1/1/0 |
| VisEdit | +1.277 | 2/0/0 |
| SaLEM | +24.847 | 2/0/0 |
| LGA | +1.462 | 2/0/0 |
| Perturb-KL | +0.000 | 0/2/0 |
| CMA | +2.005 | 1/1/0 |

## 6. 用于验证Ours优势的相关性与显著性分析方案

1. **主要指标**：每个完整组合分别计算Best@3、Best@5、Mean@3、Mean@5、Regret@3/5和Hit@3/5；优先报告Regret更低、Hit更高，而不是只挑单个最高分案例。
2. **排序相关性**：在每种方法自己的Top-K内部，用预测顺序与真实Average顺序计算Spearman ρ或Kendall τ；Top-3样本很小，应跨21组合报告分布和置信区间，不只报告单点。
3. **配对检验**：在相同完整组合上比较Ours与每个基线的Best@K/Regret@K差值，使用配对bootstrap置信区间或Wilcoxon signed-rank；七方法多重比较采用Holm校正。
4. **候选重合分析**：计算Ours与每个基线Top-3/Top-5的Jaccard重合度，并结合性能差值判断Ours是找到不同高性能层，还是仅复现共同候选。
5. **分层报告**：分别按数据集、模型规模和层深归一化位置汇报，避免某一数据集或某类模型主导总体均值。
6. **异常处理**：stable、recovered、nonfinite、numeric anomaly单独做敏感性分析；不得与主配置直接取最大值，PaliGemma L0不收敛不得记0分。

只有当Ours在预先定义的完整组合上表现为更高Best/Mean、更低Regret、更高Hit，且配对置信区间或检验支持时，才能表述为“Ours优于其他定位方法”；若证据不支持，应如实报告模型或数据集上的边界。

## 7. 数据来源与可复现文件

- 七基线候选：`md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/baseline_candidates.csv`
- Ours主公式候选：同目录`formula_topk_all_21.csv`，筛选`formula=M_abscos_x_newn`
- 已验收逐层结果：同目录`accepted_outcome_rows.csv`，正式比较筛选`variant=main`
- 2026-08-24服务器增量：`outputs/formal7_live_main_outcomes_20260824.csv`
- 正式并集状态：`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`
- 方法级分析表：`outputs/formal7_method_topk_performance_20260801.csv`
- 17组合Top-3逐组合明细：`outputs/formal7_method_top3_fair_rows_17combos_20260824.csv`
- 17组合Top-3汇总排名：`outputs/formal7_method_top3_summary_17combos_20260824.csv`
- 生成脚本：`outputs/build_formal7_oursdirect_analysis_md.py`
- 文件名中的`20260801`为首次生成批次标识；上述并集与方法级CSV已于2026-08-10根据g09恢复结果重新生成，内容以文件内当前数据为准。
