# 视觉梯度 11 公式与定位基线的当前证据分析

生成日期：2026-07-31

## 1. 结论先行

基于当前**已完成独立 test/eval 的 measured-layer 结果**，`M_abscos_x_newn = abs(S_v_cos) × S_v_new_norm` 与 `M_new_norm` 构成明显领先组；若必须冻结一个下一阶段主公式，当前证据可把 `M_abscos_x_newn` 作为略占优的首选，但现有数据还不足以声称它已经被证明为全局唯一最优或统计显著优于所有基线。准确表述应是：

> 在当前已测候选层范围内，`M_abscos_x_newn` 的平均跨组合排序相关性略高，且在与基础公式的 Top-3 两两 regret 比较中未观察到劣势，因此暂选为下一阶段主公式；它与 `M_new_norm` 实质上仍接近并列，结论属于 measured-layer evidence。

## 2. 数据与防止选择性报告的规则

- 公式候选由 21 份逐层原始 CSV 统一重算，不使用只覆盖 Qwen 的现成 11 公式表替代其他模型。
- Qwen 3 数据集 × 11 公式共 33 行、以及全 21 组 × 4 个深度指标共 84 行 Top-5，均与既有标准结果逐行一致，作为重算实现校验。
- 只使用主表中有完整正式评测的层；失败、无 eval、仅 checkpoint 的层不进入性能值。
- PaliGemma 主配置用于主分析，stable 配置只做敏感性分析，不把两种配置逐层挑高值混合。
- EVQA/BLIP2 使用 4.1 的主结果，`L18-2` 是重复结果，不用“择优复评”替换主 L18。
- 梯度候选 coverage < 0.8 的组合不进入强汇总；当前主要是 MMKE-entity/BLIP2（284/636）。
- Oracle 仅为已测层中的最高 Average，即 measured-layer oracle，不声称是全层 oracle。

输入哈希：

- `6edit_layer_localization_candidate_methods_简洁说明版.md`: `da40d47db7a3e73b85ab9295071c5b636c7520b28e42c91b06fa4c38f9989e71`
- `6location_7model_3datas_top_3_5_layers_outcome.md`: `bce3f4105d06d5dfb23ba265f75de9315d4afe5dcef953b0f0859f1a0f7441ef`

## 3. 11 公式主配置汇总

| Formula | Top3完整组合 | Best@3均值 | Mean@3均值 | Regret@3均值↓ | Spearman均值↑ | Spearman中位数 | 正相关组合 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `M_dot` | 8 | 67.477 | 65.135 | 4.184 | 0.068 | 0.159 | 12/18 |
| `M_cos` | 4 | 59.665 | 58.667 | 13.258 | 0.072 | 0.104 | 12/18 |
| `M_new_norm` | 10 | 69.159 | 66.514 | 2.238 | 0.320 | 0.419 | 13/18 |
| `M_pos_ratio` | 5 | 73.997 | 67.339 | 2.875 | 0.145 | 0.346 | 12/18 |
| `M_conflict` | 3 | 62.177 | 59.003 | 8.247 | -0.068 | -0.159 | 6/18 |
| `M_newn_x_1mcos` | 10 | 65.230 | 63.800 | 6.167 | 0.308 | 0.370 | 13/18 |
| `M_abscos_x_newn` | 9 | 68.486 | 65.581 | 2.295 | 0.323 | 0.395 | 15/18 |
| `Ours-Direct-Conflict` | 2 | 71.330 | 68.583 | 2.125 | 0.088 | 0.143 | 3/5 |
| `Ours-AbsDirection-Direct` | 13 | 70.222 | 68.557 | 3.879 | 0.090 | 0.317 | 12/18 |
| `Ours-NoDirection-Direct` | 13 | 70.098 | 67.903 | 4.002 | 0.032 | 0.095 | 10/18 |
| `Ours-1MinusCos-Direct` | 13 | 70.078 | 67.289 | 4.022 | 0.016 | 0.084 | 10/18 |

注意：上表每个公式的 Top-3 完整组合数不同，不能仅按 Best@3 均值横向宣布胜负；下节使用共同组合和两两配对。

## 4. 为什么当前首选 M_abscos_x_newn

### 4.1 跨已测层排序相关性

按每个 dataset×model 内公式分数与真实 Average 的 Spearman 相关，再跨组合平均：

| Rank | Formula | Mean Spearman | Median | Positive/Total |
|---:|---|---:|---:|---:|
| 1 | `M_abscos_x_newn` | 0.323 | 0.395 | 15/18 |
| 2 | `M_new_norm` | 0.320 | 0.419 | 13/18 |
| 3 | `M_newn_x_1mcos` | 0.308 | 0.370 | 13/18 |
| 4 | `M_pos_ratio` | 0.145 | 0.346 | 12/18 |
| 5 | `Ours-AbsDirection-Direct` | 0.090 | 0.317 | 12/18 |
| 6 | `Ours-Direct-Conflict` | 0.088 | 0.143 | 3/5 |
| 7 | `M_cos` | 0.072 | 0.104 | 12/18 |
| 8 | `M_dot` | 0.068 | 0.159 | 12/18 |
| 9 | `Ours-NoDirection-Direct` | 0.032 | 0.095 | 10/18 |
| 10 | `Ours-1MinusCos-Direct` | 0.016 | 0.084 | 10/18 |
| 11 | `M_conflict` | -0.068 | -0.159 | 6/18 |

`M_abscos_x_newn` 的平均 Spearman 最高；但只比 `M_new_norm` 高约 0.003，因此该差异必须视为描述性排序，而非统计显著优势。

敏感性分析没有改变平均 Spearman 的第一名：

| Outcome profile | Rank 1 | Mean Spearman | Rank 2 | Mean Spearman | Rank 3 | Mean Spearman |
|---|---|---:|---|---:|---|---:|
| `main` | `M_abscos_x_newn` | 0.323 | `M_new_norm` | 0.320 | `M_newn_x_1mcos` | 0.308 |
| `main_clean` | `M_abscos_x_newn` | 0.313 | `M_new_norm` | 0.310 | `M_newn_x_1mcos` | 0.298 |
| `pali_stable_sensitivity` | `M_abscos_x_newn` | 0.315 | `M_new_norm` | 0.311 | `M_newn_x_1mcos` | 0.288 |

### 4.2 七个基础公式的完全共同 Top-3 组合

| Formula | Common N | Best@3 | Mean@3 | Regret@3↓ | Hit@3 |
|---|---:|---:|---:|---:|---:|
| `M_dot` | 2 | 63.165 | 59.485 | 6.410 | 0.500 |
| `M_cos` | 2 | 52.045 | 51.585 | 17.530 | 0.000 |
| `M_new_norm` | 2 | 69.575 | 63.445 | 0.000 | 1.000 |
| `M_pos_ratio` | 2 | 63.165 | 59.447 | 6.410 | 0.500 |
| `M_conflict` | 2 | 58.420 | 55.533 | 11.155 | 0.500 |
| `M_newn_x_1mcos` | 2 | 59.995 | 56.710 | 9.580 | 0.500 |
| `M_abscos_x_newn` | 2 | 69.575 | 63.445 | 0.000 | 1.000 |

共同组合数很小，因此本表只能说明这些组合内的相对次序，不能外推到 21 组。

### 4.3 M_abscos_x_newn 与其他公式的配对 Top-3 regret

Regret improvement = comparison regret − M_abscos regret；正数表示 `M_abscos_x_newn` 更好。

| Comparison | Paired N | Regret improvement | 95% bootstrap CI | W/T/L | Sign-test p |
|---|---:|---:|---:|---:|---:|
| `M_dot` | 8 | 1.603 | [0.000, 4.808] | 1/7/0 | 1.000 |
| `M_cos` | 3 | 11.687 | [0.000, 22.240] | 2/1/0 | 0.500 |
| `M_new_norm` | 9 | 0.094 | [0.000, 0.283] | 1/8/0 | 1.000 |
| `M_pos_ratio` | 3 | 4.273 | [0.000, 12.820] | 1/2/0 | 1.000 |
| `M_conflict` | 3 | 7.497 | [0.000, 22.310] | 2/1/0 | 0.500 |
| `M_newn_x_1mcos` | 9 | 4.460 | [0.000, 10.860] | 3/6/0 | 0.250 |
| `Ours-Direct-Conflict` | 1 | 1.750 | [1.750, 1.750] | 1/0/0 | 1.000 |
| `Ours-AbsDirection-Direct` | 9 | 2.965 | [-3.773, 9.968] | 5/1/3 | 0.727 |
| `Ours-NoDirection-Direct` | 9 | 2.940 | [-3.871, 10.062] | 6/0/3 | 0.508 |
| `Ours-1MinusCos-Direct` | 9 | 2.968 | [-3.632, 9.983] | 6/0/3 | 0.508 |

目前对基础 7 公式的共同完整组合，`M_abscos_x_newn` 的 regret 没有观察到更差；但大量平局与小样本使双侧 sign test 不能提供 p<0.05 的显著性证据。

### 4.4 与 M_new_norm 的可辨识性

21 组中两者 Top-3 有序列表完全相同 12 组（57.1%），平均 Top-3 Jaccard 为 0.676。18 个可算相关性的组合中，`M_abscos_x_newn - M_new_norm` 的平均 Spearman 差为 0.005，W/T/L=6/9/4；Top-3 regret 配对 W/T/L=1/8/0。现有结果只能支持“`M_abscos_x_newn` 不弱且平均相关性略高”，不能充分证明 `abs(cos)` 因子本身带来稳定增益。

## 5. 与六个正式定位基线的配对比较

只比较双方 Top-3 都有完整正式评测的相同 dataset×model；正 improvement 表示 `M_abscos_x_newn` 更好。`strict` 另排除候选生成 coverage<0.8 以及 EVQA 历史 FirstToken 未严格统一项。`Perturb-KL-Pre-AltSeq` 按主文档 §2.12 属于消融方法，不列入六个正式基线。

| Baseline | All N | Best@3 diff | Mean@3 diff | Regret W/T/L | Sign p | Strict N | Strict regret improvement |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Middle-Prior-Direct` | 9 | 2.662 | 0.601 | 6/0/3 | 0.508 | 9 | 2.662 |
| `VisEdit-Contrib-Pre-KeyToken` | 9 | 4.133 | 1.795 | 5/0/4 | 1.000 | 6 | 7.017 |
| `SaLEM-Alt-Direct` | 9 | 2.792 | 1.341 | 6/0/3 | 0.508 | 9 | 2.792 |
| `LGA-Param-Direct-AltModelPred` | 9 | 1.284 | 2.345 | 6/1/2 | 0.289 | 9 | 1.284 |
| `Perturb-KL-Direct-AltSeq` | 9 | 4.021 | 2.771 | 3/5/1 | 0.625 | 9 | 4.021 |
| `CMA-Direct` | 9 | 3.538 | 2.960 | 4/3/2 | 0.688 | 4 | 10.345 |

这些配对的平均差当前总体有利于 `M_abscos_x_newn`，但 paired N 很小，且任一基线比较都不能据此声称统计显著全面胜出。

## 6. 当前覆盖缺口

`M_abscos_x_newn` 主配置 Top-3 尚未全部正式评测的组合：

| Dataset | Model | Predicted Top-3 | Missing eval layers |
|---|---|---|---|
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L11 | L1,L0,L11 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L18,L19,L16 | L19 |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L3 | L3 |
| MMKE-entity | BLIP2-OPT-2.7B | L0,L1,L2 | L1 |
| MMKE-entity | LLaVA-v1.5-7B | L13,L11,L12 | L13,L11,L12 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L27,L28,L26 | L27,L26 |
| MMKE-entity | PaliGemma-3B | L5,L4,L3 | L4 |
| MMKE-visual | LLaVA-v1.5-7B | L0,L3,L1 | L0,L3,L1 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L9,L10,L11 | L9,L10,L11 |
| MMKE-visual | PaliGemma-3B | L5,L4,L3 | L5,L4,L3 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L2 | L2 |

`M_abscos_x_newn` 在 coverage≥0.8 且已有该模型正式结果的 19 个可评组合中，Top-3 完整覆盖 9/19，Top-5 完整覆盖 5/19。特别是 MMKE-entity/LLaVA 尚无正式层结果，MMKE-visual/LLaVA 当前结果不足，且若干基础公式候选层未包含在原先只汇总 4 个 Ours 指标的扫层并集中。这是现有证据缺失，不应按失败或零分处理。

## 7. 可以写进论文与暂时不能写的结论

可以写：

- 当前 measured-layer 描述性证据可把 `M_abscos_x_newn` 排为视觉梯度框架的首选公式，同时明确它与 `M_new_norm` 接近并列。
- 它在平均跨层排序相关性上领先，并在现有基础公式 Top-3 配对中没有观察到 regret 劣势。
- 与六个正式定位基线的共同完整 Top-3 组合上，描述性均值总体有利于该公式。

暂时不能写：

- 已证明它是 21 个组合、所有层的全局最优定位公式。
- 已统计显著优于每个基线。
- `abs(cos)` 因子已被独立证明优于单独的 `S_v_new_norm`；二者当前重合度和配对平局都很高。
- Top-5 已充分验证；当前完整 Top-5 组合更少。

## 8. 最小补实验方案

1. 先补 `M_abscos_x_newn` Top-3 缺失层，保持现有统一训练和独立 test/eval 协议。
2. 对 `M_abscos_x_newn` 与 `M_new_norm` Top-3 不同的组合，优先成对补双方独有层；这是验证 `abs(cos)` 是否真正有增益的判别性实验。
3. 再补与最佳深度加权指标候选不同的层，区分视觉梯度关系与深层先验。
4. 完成后按同一冻结脚本重新计算 Best/Mean/Regret/Hit、Spearman/Kendall/NDCG，并报告置信区间，不按结果更换主指标。

## 9. 可复核输出

- `formula_topk_all_21.csv`: 21 组 × 11 公式统一 Top-K。
- `formula_full_rankings.csv`: 所有合法层的完整公式排序。
- `formula_combo_metrics.csv`: 每个公式在每个组合上的覆盖与真实表现。
- `formula_global_summary.csv`: 主配置、数值异常剔除及 Pali stable 敏感性汇总。
- `formula_pairwise_vs_M_abscos.csv`: 公式两两配对、bootstrap CI 与 sign test。
- `baseline_pairwise_vs_M_abscos.csv`: 与正式定位基线的配对比较。
- `analysis_manifest.json`: 输入文件哈希与验收计数。
