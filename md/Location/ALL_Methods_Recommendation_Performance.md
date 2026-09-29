# 所有定位方法的推荐性能比较（2026-09-28 现有结果快照）

输入为 [SWeeplayers.md](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/SWeeplayers.md>) 与 [ALL_Methods_Recommends_layers.md](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/ALL_Methods_Recommends_layers.md>) 所链接的机器可读原件。扫层快照：**2026-09-28T11:10:16+08:00**；推荐快照：**2026-09-28T14:35:59+08:00**。本次未重新训练、未改变推荐公式、未依据编辑成绩重排候选。

## 1. 这次算到了什么

原推荐表的 **31 个方法/目标/公式/过滤版本全部登记**；另对 VisEdit 三种目标增加贡献度直接选层的诊断对照，共 34 个版本。原推荐记录 624 行中，400 行有可用推荐、224 行缺原始定位统计；新增 Direct 诊断后共 680 行。缺失不等于低分。

主比较用 **396 条 main**，36 条 stable 单独计算，1 条 BLIP2 L18 复测保留但不择优替换原 main。分别计算 Top-1、Best/Mean/Regret/Hit@3 与 @5；所有方法两两比较还按数据集和模型拆分。结果是回顾性分析，不是新独立确认实验。

当前 Ours 与参数 LGA-Tukey 的共同 **18 组**中，ΔBest@3=+2.153、ΔMean@3=+0.971，Best@3 胜/平/负=11/1/6。但是，相对纯新梯度范数，共同 **17 组**的 ΔBest@3=-0.239、ΔMean@3=-0.057，说明不能仅凭胜过参数 LGA 宣称方向项已获得支持。

参数 LGA 的 Tukey−Raw 在共同 **18 组**中，ΔBest@3=+0.652、ΔMean@3=+4.325。是否过滤、在哪个梯度空间过滤，需要逐版比较；不能套用一条统一结论。

## 2. 指标与可比边界

- **Top-1**：原推荐顺序的第一层，不按编辑分数重选。**Best@K**：事后在 K 个候选中取得的最高 Average，表示候选集合的最好潜力；**Mean@K**：这 K 层的平均 Average。Best@K 不等于无需试验就能部署的单层成绩。
- 必须有 K 个合法候选且 K 个评测全部存在，才计算 Best/Mean@K。部分结果仅报告已评测数和缺失层，不计算部分均值冒充完整结果。Top-5 按现有全部排名/Pre 规则延长，没有按编辑效果补层。
- Regret@K=同组合、同分析口径的已测最好 Average−Best@K；Hit@K 为是否包含该已测最优表现。它们不是全网络 oracle 的 Regret/Hit；同分容差为 1e-9 个百分点。
- 每个组合等权。各方法自己可用组合的均值仅作描述；方法优劣用相同组合的配对表或固定共同组表。coverage80 要求比较双方定位有效样本比例≥80%。
- 同时给出已测候选池内均匀随机选择 K 层的精确期望。候选池由既有实验选择形成，这只是条件随机参照，不能当作全网络随机实验。
- 参数与视觉 LGA 沿用不同有效样本集合；CMA 两个目标版本也改变了噪声/seed 协议；这些比较衡量完整流程，不能只归因于梯度空间或目标。视觉有限零分末层按输入规则保留，候选含零梯度层时单独标记。

| 分析口径 | 层结果数 | 用途 |
|---|---|---|
| observed_main | 396 | 所有已登记 main，包括有实测值的失败/未足训练预算；主描述 |
| main_without_flagged | 389 | 排除恢复/诊断训练、数值异常/数值保护、不收敛标签；不证明所有层都收敛 |
| verified50_main | 252 | 再要求本次明确核验了完整 50 轮历史 |
| stable_only | 36 | 只用 stable，不填补 main 缺项；保留自身异常标签 |

恢复原训练继续运行、修复 checkpoint 选择、已有 checkpoint 评测，不单凭名称认定改变配方。历史验收记录在主分析保留，在 verified50 中自然排除；排除清单见 flagged_outcomes.csv。Average 沿用台账，部分历史记录因分项四舍五入有 ≤0.010 的差异，未擅自重写。

## 3. 全部对象、公式与覆盖

记 aᵢ、bᵢ 分别为旧/新梯度范数，cᵢ 为余弦；E 为逐样本聚合。每行是独立比较版本，编号贯穿后续明细。

| 编号 | 方法版本 | 对象 | 公式/规则 | 推荐可用/登记组 | Top1可评 | Top3完整 | Top5完整 |
|---|---|---|---|---|---|---|---|
| M01 | Middle-Prior/raw | 层深先验 | 距离 (L−1)/2 最近 | 21/21 | 21 | 21 | 8 |
| M02 | CMA-alt-v1.3/raw | 视觉污染恢复 | CR；版本的噪声/seed 协议不同 | 21/21 | 20 | 19 | 12 |
| M03 | CMA-model_pred/raw | 视觉污染恢复 | CR；版本的噪声/seed 协议不同 | 21/21 | 20 | 20 | 9 |
| M04 | Perturb-KL-alt/raw | 视觉扰动 KL | robust KL；alt 全序列 | 21/21 | 20 | 20 | 8 |
| M05 | SaLEM-alt/raw | 参数梯度 | 参数梯度绝对值聚合 | 21/21 | 21 | 21 | 9 |
| M06 | LGA-Param/raw | 参数梯度 | E[g_old·g_new] | 21/21 | 20 | 20 | 13 |
| M07 | LGA-Param/tukey | 参数梯度 | E[g_old·g_new] | 21/21 | 20 | 18 | 8 |
| M08 | CMA-alt-formal/supplement | 视觉污染恢复 | CR；版本的噪声/seed 协议不同 | 1/1 | 1 | 1 | 0 |
| M09 | Ours-main/raw | 视觉隐状态梯度 | abs(E[cᵢ]) × E[bᵢ] | 21/21 | 20 | 20 | 11 |
| M10 | Ours-main/tukey | 视觉隐状态梯度 | abs(E[cᵢ]) × E[bᵢ] | 21/21 | 20 | 19 | 10 |
| M11 | Ours-no-direction/raw | 视觉隐状态梯度 | E[bᵢ] | 21/21 | 19 | 17 | 9 |
| M12 | Ours-no-direction/tukey | 视觉隐状态梯度 | E[bᵢ] | 21/21 | 17 | 14 | 7 |
| M13 | Ours-no-strength/raw | 视觉隐状态梯度 | abs(E[cᵢ]) | 21/21 | 15 | 9 | 6 |
| M14 | Ours-no-strength/tukey | 视觉隐状态梯度 | abs(E[cᵢ]) | 21/21 | 13 | 10 | 5 |
| M15 | LGA-Visual/raw | 视觉隐状态梯度 | E[g_old·g_new] | 21/21 | 17 | 13 | 7 |
| M16 | LGA-Visual/tukey | 视觉隐状态梯度 | E[g_old·g_new] | 21/21 | 14 | 8 | 6 |
| M17 | LGA-Visual-no-direction/raw | 视觉隐状态梯度 | E[aᵢbᵢ] | 21/21 | 19 | 19 | 9 |
| M18 | LGA-Visual-no-direction/tukey | 视觉隐状态梯度 | E[aᵢbᵢ] | 21/21 | 15 | 12 | 6 |
| M19 | LGA-Param-no-old-strength/raw | 参数梯度 | E[bᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M20 | LGA-Param-no-old-strength/tukey | 参数梯度 | E[bᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M21 | LGA-Param-no-new-strength/raw | 参数梯度 | E[aᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M22 | LGA-Param-no-new-strength/tukey | 参数梯度 | E[aᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M23 | LGA-Param-no-direction/raw | 参数梯度 | E[aᵢbᵢ] | 0/21 | 0 | 0 | 0 |
| M24 | LGA-Param-no-direction/tukey | 参数梯度 | E[aᵢbᵢ] | 0/21 | 0 | 0 | 0 |
| M25 | LGA-Visual-no-old-strength/raw | 视觉隐状态梯度 | E[bᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M26 | LGA-Visual-no-old-strength/tukey | 视觉隐状态梯度 | E[bᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M27 | LGA-Visual-no-new-strength/raw | 视觉隐状态梯度 | E[aᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M28 | LGA-Visual-no-new-strength/tukey | 视觉隐状态梯度 | E[aᵢcᵢ] | 0/21 | 0 | 0 | 0 |
| M29 | VisEdit-Pre-alt/current | 模块输出贡献度 | 高贡献区起点前置层 | 21/21 | 21 | 21 | 12 |
| M30 | VisEdit-Pre-model_pred/current | 模块输出贡献度 | 高贡献区起点前置层 | 7/21 | 5 | 4 | 2 |
| M31 | VisEdit-Pre-pred-field/historical | 模块输出贡献度 | 高贡献区起点前置层 | 14/14 | 11 | 11 | 6 |
| M32 | VisEdit-Direct-alt/diagnostic | 模块输出贡献度 | 贡献分数直接降序（诊断） | 21/21 | 12 | 9 | 2 |
| M33 | VisEdit-Direct-model_pred/diagnostic | 模块输出贡献度 | 贡献分数直接降序（诊断） | 7/21 | 5 | 3 | 0 |
| M34 | VisEdit-Direct-pred-field/diagnostic | 模块输出贡献度 | 贡献分数直接降序（诊断） | 14/14 | 7 | 4 | 2 |

原 31 版本中有 10 个 LGA 严格消融版本（参数去旧/去新/去方向，视觉去旧/去新，各分 Raw/Tukey）尚缺逐样本交叉统计，共 210 行；VisEdit-model_pred 的 MMKE 还缺 14 行。它们已进入登记和缺项清单，不能用层均值相乘伪造 E[ab]、E[bc]、E[ac]。VisEdit Direct 是本次附加诊断，不替换原 Pre。

## 4. 固定共同组合上的七类当前版本

### 4.1 全部定位覆盖：相同 18 组

共同组合：evqa-pilot500/blip2-opt-2.7b；evqa-pilot500/minigpt-4-vicuna-7b；evqa-pilot500/llava-v1.5-7b；evqa-pilot500/qwen2.5-vl-3b；evqa-pilot500/paligemma-3b；evqa-pilot500/smolvlm-1.7b；mmke-visual/blip2-opt-2.7b；mmke-visual/instructblip-vicuna-7b；mmke-visual/minigpt-4-vicuna-7b；mmke-visual/llava-v1.5-7b；mmke-visual/qwen2.5-vl-3b；mmke-visual/paligemma-3b；mmke-visual/smolvlm-1.7b；mmke-entity/blip2-opt-2.7b；mmke-entity/instructblip-vicuna-7b；mmke-entity/qwen2.5-vl-3b；mmke-entity/paligemma-3b；mmke-entity/smolvlm-1.7b。

| 编号 | 方法 | 同组Top1 | Best@3 | Mean@3 | 已测Regret@3 | 已测Hit@3 | ΔBest−池内随机 |
|---|---|---|---|---|---|---|---|
| M09 | Ours-main/raw | 69.297 | 73.785 | 69.024 | 1.983 | 38.9% | +2.239 |
| M03 | CMA-model_pred/raw | 69.663 | 72.473 | 69.517 | 3.295 | 22.2% | +0.927 |
| M01 | Middle-Prior/raw | 70.447 | 71.679 | 69.492 | 4.089 | 0.0% | +0.133 |
| M07 | LGA-Param/tukey | 69.372 | 71.632 | 68.053 | 4.135 | 22.2% | +0.086 |
| M04 | Perturb-KL-alt/raw | 68.724 | 71.524 | 68.666 | 4.244 | 16.7% | -0.022 |
| M05 | SaLEM-alt/raw | 66.077 | 70.198 | 67.107 | 5.569 | 33.3% | -1.348 |
| M29 | VisEdit-Pre-alt/current | 65.789 | 69.801 | 65.111 | 5.967 | 5.6% | -1.745 |

### 4.2 各方法定位覆盖均≥80%：相同 11 组

共同组合：evqa-pilot500/blip2-opt-2.7b；evqa-pilot500/minigpt-4-vicuna-7b；evqa-pilot500/smolvlm-1.7b；mmke-visual/blip2-opt-2.7b；mmke-visual/instructblip-vicuna-7b；mmke-visual/minigpt-4-vicuna-7b；mmke-visual/llava-v1.5-7b；mmke-visual/smolvlm-1.7b；mmke-entity/instructblip-vicuna-7b；mmke-entity/paligemma-3b；mmke-entity/smolvlm-1.7b。

| 编号 | 方法 | 同组Top1 | Best@3 | Mean@3 | 已测Regret@3 | 已测Hit@3 | ΔBest−池内随机 |
|---|---|---|---|---|---|---|---|
| M09 | Ours-main/raw | 70.355 | 72.308 | 69.292 | 3.055 | 36.4% | +1.956 |
| M03 | CMA-model_pred/raw | 67.939 | 70.924 | 67.454 | 4.439 | 27.3% | +0.572 |
| M01 | Middle-Prior/raw | 69.242 | 70.032 | 68.766 | 5.331 | 0.0% | -0.320 |
| M07 | LGA-Param/tukey | 67.611 | 69.943 | 66.308 | 5.419 | 9.1% | -0.409 |
| M04 | Perturb-KL-alt/raw | 66.220 | 69.717 | 67.266 | 5.646 | 27.3% | -0.635 |
| M29 | VisEdit-Pre-alt/current | 66.765 | 67.399 | 63.880 | 7.964 | 9.1% | -2.954 |
| M05 | SaLEM-alt/raw | 61.973 | 66.946 | 64.400 | 8.417 | 36.4% | -3.406 |

这里的排序只针对上述七个明确版本及共同组合，不代表所有公式的总体排名。所有可产生 21 组推荐的版本一起取 Top-3 完整交集，只剩 **2 组**；若要求全部 34 个版本完成，则没有共同完整组。因此必须看下面的配对和分组结果。

## 5. 所有版本的可用范围描述（不可直接跨行排总名次）

每列均值只使用该方法自己的完整组合，分母不同。先看覆盖，再看第 6 节共同组差值。

| 编号 | 方法 | N1 | Top1 | N3 | Best@3 | Mean@3 | N5 | Best@5 | Mean@5 |
|---|---|---|---|---|---|---|---|---|---|
| M01 | Middle-Prior/raw | 21 | 69.950 | 21 | 71.067 | 69.165 | 8 | 77.667 | 72.569 |
| M02 | CMA-alt-v1.3/raw | 20 | 62.802 | 19 | 69.919 | 64.541 | 12 | 70.472 | 64.640 |
| M03 | CMA-model_pred/raw | 20 | 69.187 | 20 | 71.727 | 68.944 | 9 | 77.467 | 71.837 |
| M04 | Perturb-KL-alt/raw | 20 | 68.116 | 20 | 70.673 | 68.039 | 8 | 80.221 | 75.458 |
| M05 | SaLEM-alt/raw | 21 | 66.354 | 21 | 69.891 | 67.047 | 9 | 68.714 | 63.645 |
| M06 | LGA-Param/raw | 20 | 60.474 | 20 | 70.403 | 63.743 | 13 | 74.803 | 66.711 |
| M07 | LGA-Param/tukey | 20 | 69.983 | 18 | 71.632 | 68.053 | 8 | 71.898 | 64.238 |
| M08 | CMA-alt-formal/supplement | 1 | 72.280 | 1 | 72.280 | 72.180 | 0 | — | — |
| M09 | Ours-main/raw | 20 | 68.882 | 20 | 72.933 | 68.511 | 11 | 76.388 | 68.468 |
| M10 | Ours-main/tukey | 20 | 69.764 | 19 | 73.184 | 68.639 | 10 | 77.497 | 68.679 |
| M11 | Ours-no-direction/raw | 19 | 70.270 | 17 | 74.294 | 69.465 | 9 | 78.108 | 69.784 |
| M12 | Ours-no-direction/tukey | 17 | 70.389 | 14 | 75.003 | 69.508 | 7 | 81.004 | 70.235 |
| M13 | Ours-no-strength/raw | 15 | 63.795 | 9 | 67.408 | 63.808 | 6 | 69.988 | 65.467 |
| M14 | Ours-no-strength/tukey | 13 | 64.802 | 10 | 67.751 | 63.437 | 5 | 76.090 | 68.811 |
| M15 | LGA-Visual/raw | 17 | 68.938 | 13 | 73.724 | 68.268 | 7 | 79.099 | 66.822 |
| M16 | LGA-Visual/tukey | 14 | 69.597 | 8 | 78.405 | 71.652 | 6 | 80.954 | 68.964 |
| M17 | LGA-Visual-no-direction/raw | 19 | 70.326 | 19 | 73.029 | 68.336 | 9 | 78.108 | 69.784 |
| M18 | LGA-Visual-no-direction/tukey | 15 | 66.586 | 12 | 76.311 | 71.013 | 6 | 82.433 | 71.082 |
| M19 | LGA-Param-no-old-strength/raw | 0 | — | 0 | — | — | 0 | — | — |
| M20 | LGA-Param-no-old-strength/tukey | 0 | — | 0 | — | — | 0 | — | — |
| M21 | LGA-Param-no-new-strength/raw | 0 | — | 0 | — | — | 0 | — | — |
| M22 | LGA-Param-no-new-strength/tukey | 0 | — | 0 | — | — | 0 | — | — |
| M23 | LGA-Param-no-direction/raw | 0 | — | 0 | — | — | 0 | — | — |
| M24 | LGA-Param-no-direction/tukey | 0 | — | 0 | — | — | 0 | — | — |
| M25 | LGA-Visual-no-old-strength/raw | 0 | — | 0 | — | — | 0 | — | — |
| M26 | LGA-Visual-no-old-strength/tukey | 0 | — | 0 | — | — | 0 | — | — |
| M27 | LGA-Visual-no-new-strength/raw | 0 | — | 0 | — | — | 0 | — | — |
| M28 | LGA-Visual-no-new-strength/tukey | 0 | — | 0 | — | — | 0 | — | — |
| M29 | VisEdit-Pre-alt/current | 21 | 66.066 | 21 | 69.525 | 65.449 | 12 | 72.062 | 65.715 |
| M30 | VisEdit-Pre-model_pred/current | 5 | 67.108 | 4 | 70.340 | 64.986 | 2 | 78.298 | 71.118 |
| M31 | VisEdit-Pre-pred-field/historical | 11 | 62.998 | 11 | 74.192 | 67.158 | 6 | 74.748 | 65.416 |
| M32 | VisEdit-Direct-alt/diagnostic | 12 | 58.259 | 9 | 63.706 | 58.639 | 2 | 63.430 | 61.701 |
| M33 | VisEdit-Direct-model_pred/diagnostic | 5 | 58.917 | 3 | 61.319 | 60.272 | 0 | — | — |
| M34 | VisEdit-Direct-pred-field/diagnostic | 7 | 61.384 | 4 | 67.412 | 65.938 | 2 | 76.605 | 74.629 |

## 6. 目标、梯度对象、公式及过滤的配对比较

差值均为 **A−B**；正值表示 A 较高。胜/平/负按 Best@3，集合相同数为双方三个候选忽略顺序后相同。每行都有自己的共同组合，不把不同行的差值当作同一批实验。

| 比较 | A−B | 共同N | ΔBest@3 | ΔMean@3 | Best胜/平/负 | 集合相同 |
|---|---|---|---|---|---|---|
| LGA-Param：Tukey−Raw | M07−M06 | 18 | +0.652 | +4.325 | 9/6/3 | 6 |
| LGA-Visual：Tukey−Raw | M16−M15 | 8 | -0.849 | +0.425 | 1/5/2 | 5 |
| LGA-Visual-no-direction：Tukey−Raw | M18−M17 | 12 | -0.336 | +0.376 | 0/10/2 | 10 |
| Ours-main：Tukey−Raw | M10−M09 | 19 | +0.090 | +0.065 | 1/17/1 | 16 |
| Ours-no-direction：Tukey−Raw | M12−M11 | 14 | +0.039 | +0.021 | 1/12/1 | 12 |
| Ours-no-strength：Tukey−Raw | M14−M13 | 9 | +0.062 | +0.349 | 1/6/2 | 6 |
| Ours 方向项增量（raw） | M09−M11 | 17 | -0.239 | -0.057 | 3/13/1 | 13 |
| Ours 强度项增量（raw） | M09−M13 | 9 | +3.933 | +3.961 | 5/3/1 | 2 |
| LGA 视觉−参数（raw） | M15−M06 | 13 | +2.329 | +6.844 | 9/2/2 | 0 |
| 视觉 LGA 方向项增量（raw） | M15−M17 | 13 | -0.159 | +0.179 | 0/12/1 | 11 |
| Ours 方向项增量（tukey） | M10−M12 | 14 | -0.046 | -0.005 | 4/9/1 | 9 |
| Ours 强度项增量（tukey） | M10−M14 | 10 | +3.757 | +4.127 | 7/1/2 | 0 |
| LGA 视觉−参数（tukey） | M16−M07 | 8 | +3.660 | +3.669 | 5/1/2 | 0 |
| 视觉 LGA 方向项增量（tukey） | M16−M18 | 7 | -0.760 | -0.136 | 1/5/1 | 4 |
| CMA model_pred−alt（含协议差异） | M03−M02 | 19 | +1.949 | +4.735 | 5/11/3 | 3 |
| VisEdit Pre model_pred−alt | M30−M29 | 4 | -0.000 | -3.393 | 0/4/0 | 0 |
| VisEdit Pre pred-field−alt（历史诊断） | M31−M29 | 11 | +1.838 | +1.566 | 1/9/1 | 8 |
| VisEdit Pre−Direct / alt | M29−M32 | 9 | +1.204 | +5.243 | 6/0/3 | 0 |
| VisEdit Pre−Direct / model_pred | M30−M33 | 2 | +0.012 | +0.703 | 1/0/1 | 0 |
| VisEdit Pre−Direct / pred-field | M31−M34 | 4 | -0.498 | +0.727 | 1/0/3 | 0 |
| 当前 Ours−中层 | M09−M01 | 20 | +2.114 | -0.316 | 13/1/6 | 0 |
| 当前 Ours−参数 LGA Tukey | M09−M07 | 18 | +2.153 | +0.971 | 11/1/6 | 0 |
| 纯新范数−中层 | M11−M01 | 17 | +2.233 | -0.480 | 10/0/7 | 0 |
| 当前 Ours−CMA model_pred | M09−M03 | 20 | +1.206 | -0.433 | 6/11/3 | 4 |

### 6.1 按任务拆分关键比较

| 比较 | 数据集 | 共同N | ΔBest@3 | ΔMean@3 | Best胜/平/负 |
|---|---|---|---|---|---|
| LGA-Param：Tukey−Raw | evqa-pilot500 | 6 | +2.883 | +3.693 | 3/3/0 |
| LGA-Param：Tukey−Raw | mmke-visual | 7 | -1.787 | +5.155 | 3/2/2 |
| LGA-Param：Tukey−Raw | mmke-entity | 5 | +1.388 | +3.921 | 3/1/1 |
| Ours 方向项增量（raw） | evqa-pilot500 | 5 | -1.063 | -0.441 | 1/3/1 |
| Ours 方向项增量（raw） | mmke-visual | 6 | +0.128 | +0.130 | 1/5/0 |
| Ours 方向项增量（raw） | mmke-entity | 6 | +0.082 | +0.074 | 1/5/0 |
| LGA 视觉−参数（raw） | evqa-pilot500 | 4 | +4.149 | +7.392 | 2/1/1 |
| LGA 视觉−参数（raw） | mmke-visual | 5 | +1.374 | +3.509 | 4/1/0 |
| LGA 视觉−参数（raw） | mmke-entity | 4 | +1.704 | +10.466 | 3/0/1 |
| CMA model_pred−alt（含协议差异） | evqa-pilot500 | 6 | -1.731 | +1.387 | 0/5/1 |
| CMA model_pred−alt（含协议差异） | mmke-visual | 7 | +5.522 | +7.169 | 3/4/0 |
| CMA model_pred−alt（含协议差异） | mmke-entity | 6 | +1.459 | +5.243 | 2/2/2 |
| VisEdit Pre model_pred−alt | evqa-pilot500 | 4 | -0.000 | -3.393 | 0/4/0 |
| VisEdit Pre model_pred−alt | mmke-visual | 0 | — | — | 0/0/0 |
| VisEdit Pre model_pred−alt | mmke-entity | 0 | — | — | 0/0/0 |
| 当前 Ours−参数 LGA Tukey | evqa-pilot500 | 6 | +2.553 | +2.278 | 5/0/1 |
| 当前 Ours−参数 LGA Tukey | mmke-visual | 7 | +3.025 | -2.646 | 4/0/3 |
| 当前 Ours−参数 LGA Tukey | mmke-entity | 5 | +0.453 | +4.466 | 2/1/2 |

### 6.2 按模型拆分方向项与过滤

| 比较 | 模型 | 共同N | ΔBest@3 | ΔMean@3 | Best胜/平/负 |
|---|---|---|---|---|---|
| LGA-Param：Tukey−Raw | blip2-opt-2.7b | 3 | +4.311 | +4.088 | 2/1/0 |
| LGA-Param：Tukey−Raw | instructblip-vicuna-7b | 2 | -9.778 | -2.997 | 1/0/1 |
| LGA-Param：Tukey−Raw | minigpt-4-vicuna-7b | 2 | -0.000 | -0.000 | 0/2/0 |
| LGA-Param：Tukey−Raw | llava-v1.5-7b | 2 | -0.000 | -0.000 | 0/2/0 |
| LGA-Param：Tukey−Raw | qwen2.5-vl-3b | 3 | +0.663 | +0.624 | 3/0/0 |
| LGA-Param：Tukey−Raw | paligemma-3b | 3 | +5.725 | +23.360 | 3/0/0 |
| LGA-Param：Tukey−Raw | smolvlm-1.7b | 3 | -0.270 | -0.127 | 0/1/2 |
| Ours 方向项增量（raw） | blip2-opt-2.7b | 3 | +0.000 | +0.000 | 0/3/0 |
| Ours 方向项增量（raw） | instructblip-vicuna-7b | 2 | +0.000 | +0.000 | 0/2/0 |
| Ours 方向项增量（raw） | minigpt-4-vicuna-7b | 3 | -1.635 | -0.652 | 2/0/1 |
| Ours 方向项增量（raw） | llava-v1.5-7b | 0 | — | — | 0/0/0 |
| Ours 方向项增量（raw） | qwen2.5-vl-3b | 3 | +0.283 | +0.327 | 1/2/0 |
| Ours 方向项增量（raw） | paligemma-3b | 3 | +0.000 | +0.000 | 0/3/0 |
| Ours 方向项增量（raw） | smolvlm-1.7b | 3 | +0.000 | +0.000 | 0/3/0 |

## 7. 训练状态、定位覆盖与 stable 敏感性

以下不挑选最有利的过滤结果；切换口径后共同组合会变化，因而变化不能只归因于排除异常。两种梯度空间的样本定义差异也不会被 coverage80 自动消除。

| 比较 | 训练/证据口径 | 定位覆盖限制 | 共同N | ΔBest@3 | ΔMean@3 |
|---|---|---|---|---|---|
| LGA-Param：Tukey−Raw | observed_main | all | 18 | +0.652 | +4.325 |
| LGA-Param：Tukey−Raw | observed_main | coverage80 | 15 | +0.425 | +4.281 |
| LGA-Param：Tukey−Raw | main_without_flagged | all | 15 | -0.363 | +0.518 |
| LGA-Param：Tukey−Raw | main_without_flagged | coverage80 | 13 | -0.419 | +0.597 |
| LGA-Param：Tukey−Raw | verified50_main | all | 6 | -3.137 | -0.393 |
| LGA-Param：Tukey−Raw | verified50_main | coverage80 | 4 | -4.705 | -0.589 |
| LGA-Param：Tukey−Raw | stable_only | all | 2 | +0.313 | +36.725 |
| LGA-Param：Tukey−Raw | stable_only | coverage80 | 2 | +0.313 | +36.725 |
| Ours 方向项增量（raw） | observed_main | all | 17 | -0.239 | -0.057 |
| Ours 方向项增量（raw） | observed_main | coverage80 | 16 | -0.254 | -0.061 |
| Ours 方向项增量（raw） | main_without_flagged | all | 16 | -0.254 | -0.061 |
| Ours 方向项增量（raw） | main_without_flagged | coverage80 | 15 | -0.270 | -0.065 |
| Ours 方向项增量（raw） | verified50_main | all | 4 | -1.542 | -0.796 |
| Ours 方向项增量（raw） | verified50_main | coverage80 | 3 | -2.055 | -1.062 |
| Ours 方向项增量（raw） | stable_only | all | 0 | — | — |
| Ours 方向项增量（raw） | stable_only | coverage80 | 0 | — | — |
| 当前 Ours−参数 LGA Tukey | observed_main | all | 18 | +2.153 | +0.971 |
| 当前 Ours−参数 LGA Tukey | observed_main | coverage80 | 15 | +1.705 | +0.171 |
| 当前 Ours−参数 LGA Tukey | main_without_flagged | all | 16 | +2.129 | +2.108 |
| 当前 Ours−参数 LGA Tukey | main_without_flagged | coverage80 | 14 | +1.829 | +2.366 |
| 当前 Ours−参数 LGA Tukey | verified50_main | all | 6 | +5.906 | +2.357 |
| 当前 Ours−参数 LGA Tukey | verified50_main | coverage80 | 4 | +6.745 | +3.382 |
| 当前 Ours−参数 LGA Tukey | stable_only | all | 0 | — | — |
| 当前 Ours−参数 LGA Tukey | stable_only | coverage80 | 0 | — | — |

stable 的逐组合成绩与 main 单列保存在 method_performance_all.csv；本报告没有让别的模型使用 main、PaliGemma 自动改用 stable 后再混成一个主均值。

## 8. 分数与实际成绩的关联

对同一组合已测且在当前排序中保留的层计算 Spearman，至少五层、分数和指标非恒定才给值。这里不保证覆盖全部网络层。Raw/Tukey 的参与层集合可能不同；Pre 是区间到候选层的转换，未把同层贡献分数冒充 Pre 自身分数；贡献度关联看 VisEdit Direct 诊断。下表为覆盖≥80%的模型相关系数等权均值，不是将所有层拼接回归，也不是显著性证明。

| 方法 | 任务 | N模型 | ρ Average | ρ Rel | ρ M-Gen | ρ M-Loc |
|---|---|---|---|---|---|---|
| M06 LGA-Param/raw | evqa-pilot500 | 4 | -0.300 | -0.152 | -0.208 | -0.454 |
| M06 LGA-Param/raw | mmke-visual | 7 | -0.073 | -0.078 | -0.090 | 0.001 |
| M06 LGA-Param/raw | mmke-entity | 6 | 0.192 | 0.149 | 0.149 | 0.219 |
| M07 LGA-Param/tukey | evqa-pilot500 | 4 | -0.277 | -0.166 | -0.205 | -0.407 |
| M07 LGA-Param/tukey | mmke-visual | 7 | 0.079 | 0.030 | 0.026 | 0.208 |
| M07 LGA-Param/tukey | mmke-entity | 6 | 0.298 | 0.229 | 0.225 | 0.277 |
| M09 Ours-main/raw | evqa-pilot500 | 7 | 0.297 | 0.332 | 0.400 | -0.160 |
| M09 Ours-main/raw | mmke-visual | 7 | 0.345 | 0.420 | 0.392 | -0.170 |
| M09 Ours-main/raw | mmke-entity | 6 | 0.350 | 0.312 | 0.313 | -0.030 |
| M11 Ours-no-direction/raw | evqa-pilot500 | 7 | 0.252 | 0.447 | 0.426 | -0.321 |
| M11 Ours-no-direction/raw | mmke-visual | 7 | 0.410 | 0.477 | 0.456 | -0.089 |
| M11 Ours-no-direction/raw | mmke-entity | 6 | 0.453 | 0.418 | 0.416 | 0.184 |
| M15 LGA-Visual/raw | evqa-pilot500 | 7 | -0.006 | 0.117 | 0.057 | -0.215 |
| M15 LGA-Visual/raw | mmke-visual | 7 | 0.042 | 0.018 | 0.002 | 0.033 |
| M15 LGA-Visual/raw | mmke-entity | 6 | 0.234 | 0.193 | 0.183 | 0.214 |
| M32 VisEdit-Direct-alt/diagnostic | evqa-pilot500 | 7 | -0.184 | -0.266 | -0.283 | 0.070 |
| M32 VisEdit-Direct-alt/diagnostic | mmke-visual | 7 | -0.317 | -0.367 | -0.366 | -0.047 |
| M32 VisEdit-Direct-alt/diagnostic | mmke-entity | 7 | -0.117 | -0.156 | -0.157 | 0.012 |

## 9. 全量明细、缺项与复算

逐个模型×数据集查看全部 34 个版本的实际推荐层、Top1、Best/Mean@3、缺失层与 Top5 结果：[21 组完整明细](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/ALL_Methods_Performance_Per_Combination.md>)。

- [全部方法、配方口径与 K 的逐组性能](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/method_performance_all.csv>)
- [所有方法两两配对（含分数据集、分模型）](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/all_pairwise_comparisons.csv>)
- [固定共同组比较](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/fixed_cohort_comparisons.csv>)
- [各方法分任务/模型汇总](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/method_summary_by_scope.csv>)
- [定位未完成与评测缺失](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/missing_candidates_or_evaluations.csv>)
- [缺失层涉及哪些方法](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/missing_layer_coverage.csv>)
- [所有逐层分数相关性](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/layer_score_correlations.csv>)
- [已测池最优与条件随机参照](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/observed_pool_and_random_reference.csv>)
- [统计口径与输入哈希](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/protocol.json>)
- [计算检查](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/all_methods_performance_20260928/verification.json>)

复算脚本：[compare_all_method_recommendations_20260928.py](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/scripts/compare_all_method_recommendations_20260928.py>)；报告脚本：[report_all_method_performance_20260928.py](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/scripts/report_all_method_performance_20260928.py>)。脚本默认复用本目录冻结输入，确保这版结果可重现；新数据应另建快照，不能与这版共同组数混用。
