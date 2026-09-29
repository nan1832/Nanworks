# 定位公式与 Average 各组成指标的相关性

扫层快照：2026-09-28T11:10:16+08:00；定位快照：2026-09-28T14:35:59+08:00。使用已有结果，未启动训练、未改变公式、未依据分项成绩重排候选。

**结论：存在部分组合上的强正相关，主要来自视觉梯度强度与 Rel、T-Gen、M-Gen；当前没有发现跨组合、跨指标均保持强正相关的公式。** 将指标拆开后，梯度强度与编辑/泛化的关系比与 Average 更清楚；M-Loc 呈不同关系，不能由前面三项替代。

## 1. 计算口径

- 在每个数据集×模型组合内，用层定位分数与同层评测指标计算 Spearman ρ；只使用有实际评测的层，至少 5 层。不是把不同模型的原始梯度混合相关，也不是逐样本相关。
- 主表要求定位有效样本覆盖率≥80%，每个组合等权平均其 ρ。表中 N 是可计算的组合数，既不是层数，也不是独立模型数；同一模型在不同数据集重复出现。不同方法 N 不同的均值仅作描述。
- 将 ρ≥0.7 / ρ≤−0.7 作为本报告的描述性“强正/强负”标记，不代表显著性检验或独立验证。未进行多重检验后的发现声明。
- 主口径保留 396 条 main 实测记录（含已记录的失败/未足预算结果）；去除异常训练标签的 389 条口径作为敏感性检查。stable 单列，不填补 main。全量原始结果、各数据集/模型拆分和四种口径均保存到 CSV。
- Raw 保留有限零分末层；Tukey 用冻结输入中各公式自己的筛选集合。Tukey 与 Raw 的相关性可能基于不同层集合，均值上升不能直接解读为选层性能提升。

## 2. 全部已有逐层分数的版本

下列是组合内 ρ 的等权均值，不是 Average 成绩，也不是胜率。视觉强度四个版本与 Ours 主式使用相同的 20 个高覆盖组合；其他方法可用组合不同。T-Loc 在 main 的 396 条记录中全部为 100.0，所有公式对它的相关性均未定义，不能填成 0。

| 版本 | N | Rel | T-Gen | M-Gen | M-Loc | Average | 强正组数 Rel/T-Gen/M-Gen |
|---|---|---|---|---|---|---|---|
| Middle-Prior/raw | 21 | 0.088 | 0.103 | 0.120 | 0.216 | 0.180 | 3/3/3 |
| CMA-alt-v1.3/raw | 8 | 0.272 | 0.281 | 0.257 | -0.269 | 0.167 | 1/1/1 |
| CMA-model_pred/raw | 16 | 0.401 | 0.376 | 0.400 | -0.049 | 0.338 | 5/5/5 |
| Perturb-KL-alt/raw | 21 | 0.386 | 0.367 | 0.376 | -0.086 | 0.310 | 5/5/7 |
| SaLEM-alt/raw | 21 | 0.182 | 0.176 | 0.198 | 0.264 | 0.217 | 2/2/2 |
| LGA-Param/raw | 17 | -0.015 | -0.021 | -0.034 | -0.029 | -0.033 | 1/1/1 |
| LGA-Param/tukey | 17 | 0.054 | 0.062 | 0.042 | 0.088 | 0.072 | 1/1/1 |
| Ours-main/raw | 20 | 0.357 | 0.365 | 0.371 | -0.124 | 0.330 | 4/4/4 |
| Ours-main/tukey | 20 | 0.360 | 0.363 | 0.371 | -0.055 | 0.346 | 4/4/4 |
| Ours-no-direction/raw | 20 | 0.449 | 0.434 | 0.434 | -0.088 | 0.368 | 7/6/7 |
| Ours-no-direction/tukey | 20 | 0.466 | 0.447 | 0.449 | -0.021 | 0.398 | 6/6/7 |
| Ours-no-strength/raw | 20 | 0.046 | 0.059 | 0.054 | -0.096 | 0.052 | 1/1/2 |
| Ours-no-strength/tukey | 20 | 0.003 | 0.014 | 0.018 | 0.023 | 0.045 | 1/1/2 |
| LGA-Visual/raw | 20 | 0.105 | 0.110 | 0.075 | 0.000 | 0.083 | 2/2/2 |
| LGA-Visual/tukey | 20 | 0.107 | 0.117 | 0.072 | 0.013 | 0.076 | 3/3/3 |
| LGA-Visual-no-direction/raw | 20 | 0.460 | 0.445 | 0.441 | -0.091 | 0.377 | 7/6/7 |
| LGA-Visual-no-direction/tukey | 20 | 0.466 | 0.456 | 0.446 | -0.024 | 0.398 | 8/7/8 |
| VisEdit-Direct-alt/diagnostic | 21 | -0.263 | -0.253 | -0.269 | 0.012 | -0.206 | 0/0/0 |
| VisEdit-Direct-model_pred/diagnostic | 7 | -0.395 | -0.372 | -0.396 | 0.139 | -0.271 | 0/0/0 |
| VisEdit-Direct-pred-field/diagnostic | 14 | -0.238 | -0.244 | -0.239 | -0.057 | -0.205 | 0/0/0 |

记旧/新视觉隐藏状态梯度范数为 aᵢ、bᵢ，余弦为 cᵢ：Ours-no-direction=E[bᵢ]；LGA-Visual-no-direction=E[aᵢbᵢ]；Ours-main=|E[cᵢ]|E[bᵢ]；LGA-Visual=E[gᵢ旧·gᵢ新]。联合范数与纯新范数在部分组合产生相同层排序，这些结果不能计为独立的重复验证。

VisEdit-Direct 三行仅表示贡献度与同层编辑结果的诊断相关性；VisEdit-Pre 根据高贡献区域选择前置编辑层，是另一种映射规则，不能把 Direct 的负相关直接判成 Pre 方法失败。pred-field 历史目标也不等于 model_pred。CMA 两目标有噪声/seed 协议差异，参数/视觉梯度的有效样本集合也不同。

### 没有定义逐层分数相关性的登记版本

| 版本 | 原因 |
|---|---|
| CMA-alt-formal/supplement | 仅有推荐名次，无可复核逐层分数 |
| LGA-Param-no-old-strength/raw | 缺严格原始消融统计，不能计算 |
| LGA-Param-no-old-strength/tukey | 缺严格原始消融统计，不能计算 |
| LGA-Param-no-new-strength/raw | 缺严格原始消融统计，不能计算 |
| LGA-Param-no-new-strength/tukey | 缺严格原始消融统计，不能计算 |
| LGA-Param-no-direction/raw | 缺严格原始消融统计，不能计算 |
| LGA-Param-no-direction/tukey | 缺严格原始消融统计，不能计算 |
| LGA-Visual-no-old-strength/raw | 缺严格原始消融统计，不能计算 |
| LGA-Visual-no-old-strength/tukey | 缺严格原始消融统计，不能计算 |
| LGA-Visual-no-new-strength/raw | 缺严格原始消融统计，不能计算 |
| LGA-Visual-no-new-strength/tukey | 缺严格原始消融统计，不能计算 |
| VisEdit-Pre-alt/current | 区域到前置层的推荐规则，不直接视为同层贡献分数 |
| VisEdit-Pre-model_pred/current | 区域到前置层的推荐规则，不直接视为同层贡献分数 |
| VisEdit-Pre-pred-field/historical | 区域到前置层的推荐规则，不直接视为同层贡献分数 |

## 3. 局部强相关与反例

| 数据集 | 模型 | 版本 | 层数 | Rel | T-Gen | M-Gen | M-Loc | Average |
|---|---|---|---|---|---|---|---|---|
| mmke-entity | instructblip-vicuna-7b | Ours-no-direction/raw | 23 | 0.927 | 0.948 | 0.932 | -0.149 | 0.943 |
| mmke-visual | smolvlm-1.7b | Ours-no-direction/raw | 21 | 0.879 | 0.892 | 0.896 | 0.722 | 0.923 |
| mmke-entity | llava-v1.5-7b | Ours-no-direction/raw | 10 | 0.891 | 0.891 | 0.900 | 0.079 | 0.903 |
| mmke-visual | minigpt-4-vicuna-7b | Ours-no-direction/raw | 21 | 0.749 | 0.777 | 0.775 | 0.349 | 0.758 |
| mmke-entity | minigpt-4-vicuna-7b | Ours-no-direction/raw | 18 | -0.185 | -0.294 | -0.199 | -0.004 | -0.224 |
| mmke-visual | minigpt-4-vicuna-7b | LGA-Visual/raw | 21 | -0.921 | -0.925 | -0.938 | -0.270 | -0.905 |
| mmke-entity | llava-v1.5-7b | LGA-Param/tukey | 10 | 0.867 | 0.867 | 0.863 | -0.042 | 0.855 |
| evqa-pilot500 | minigpt-4-vicuna-7b | SaLEM-alt/raw | 21 | 0.508 | 0.560 | 0.542 | 0.714 | 0.606 |
| evqa-pilot500 | qwen2.5-vl-3b | Ours-no-direction/raw | 26 | 0.486 | 0.513 | 0.302 | -0.510 | -0.015 |

InstructBLIP×MMKE-entity 的纯新范数与前三项相关性约 0.93–0.95，但 M-Loc 为负。MiniGPT4×MMKE-visual 的 LGA 视觉有符号内积与前三项反而强负相关；同一组合改看纯新范数则为强正相关。不能看到 |ρ| 大就认定按原分数降序推荐有效，也不能根据已见评测结果逐组合翻转符号后当成验证过的通用公式。LLaVA×MMKE-entity 当前只有 10 个有结果的层；其强相关不等于已完成全网络确认。

## 4. 按数据集拆开：强度与方向的差异

| 数据集 | 版本 | N | Rel | T-Gen | M-Gen | M-Loc | Average |
|---|---|---|---|---|---|---|---|
| evqa-pilot500 | Ours-no-direction/raw | 7 | 0.447 | 0.415 | 0.426 | -0.321 | 0.252 |
| evqa-pilot500 | LGA-Visual-no-direction/raw | 7 | 0.470 | 0.436 | 0.439 | -0.329 | 0.269 |
| evqa-pilot500 | Ours-main/raw | 7 | 0.332 | 0.318 | 0.400 | -0.160 | 0.297 |
| evqa-pilot500 | LGA-Visual/raw | 7 | 0.117 | 0.113 | 0.057 | -0.215 | -0.006 |
| evqa-pilot500 | LGA-Param/tukey | 4 | -0.166 | -0.150 | -0.205 | -0.407 | -0.277 |
| evqa-pilot500 | SaLEM-alt/raw | 7 | 0.288 | 0.283 | 0.331 | 0.157 | 0.361 |
| mmke-visual | Ours-no-direction/raw | 7 | 0.477 | 0.484 | 0.456 | -0.089 | 0.410 |
| mmke-visual | LGA-Visual-no-direction/raw | 7 | 0.487 | 0.493 | 0.464 | -0.090 | 0.420 |
| mmke-visual | Ours-main/raw | 7 | 0.420 | 0.415 | 0.392 | -0.170 | 0.345 |
| mmke-visual | LGA-Visual/raw | 7 | 0.018 | 0.030 | 0.002 | 0.033 | 0.042 |
| mmke-visual | LGA-Param/tukey | 7 | 0.030 | 0.055 | 0.026 | 0.208 | 0.079 |
| mmke-visual | SaLEM-alt/raw | 7 | 0.502 | 0.492 | 0.507 | 0.341 | 0.519 |
| mmke-entity | Ours-no-direction/raw | 6 | 0.418 | 0.398 | 0.416 | 0.184 | 0.453 |
| mmke-entity | LGA-Visual-no-direction/raw | 6 | 0.418 | 0.398 | 0.416 | 0.184 | 0.453 |
| mmke-entity | Ours-main/raw | 6 | 0.312 | 0.361 | 0.313 | -0.030 | 0.350 |
| mmke-entity | LGA-Visual/raw | 6 | 0.193 | 0.200 | 0.183 | 0.214 | 0.234 |
| mmke-entity | LGA-Param/tukey | 6 | 0.229 | 0.212 | 0.225 | 0.277 | 0.298 |
| mmke-entity | SaLEM-alt/raw | 7 | -0.243 | -0.247 | -0.245 | 0.296 | -0.229 |

这是任务与模型条件差异的回顾性证据，不能只由数据集名称给任务定性。若要提出任务条件定位规则，还需在不读取测试层成绩的条件下定义任务类别、选择规则，并在保留组合上确认。

## 5. 异常训练标签的敏感性检查

| 版本 | 口径 | N | Rel | T-Gen | M-Gen | M-Loc | Average |
|---|---|---|---|---|---|---|---|
| Ours-no-direction/raw | observed_main | 20 | 0.449 | 0.434 | 0.434 | -0.088 | 0.368 |
| Ours-no-direction/raw | main_without_flagged | 20 | 0.456 | 0.440 | 0.438 | -0.074 | 0.381 |
| LGA-Visual-no-direction/raw | observed_main | 20 | 0.460 | 0.445 | 0.441 | -0.091 | 0.377 |
| LGA-Visual-no-direction/raw | main_without_flagged | 20 | 0.465 | 0.448 | 0.443 | -0.076 | 0.389 |
| Ours-main/raw | observed_main | 20 | 0.357 | 0.365 | 0.371 | -0.124 | 0.330 |
| Ours-main/raw | main_without_flagged | 20 | 0.365 | 0.371 | 0.376 | -0.108 | 0.344 |
| LGA-Visual/raw | observed_main | 20 | 0.105 | 0.110 | 0.075 | 0.000 | 0.083 |
| LGA-Visual/raw | main_without_flagged | 20 | 0.110 | 0.114 | 0.078 | 0.018 | 0.095 |
| LGA-Param/tukey | observed_main | 17 | 0.054 | 0.062 | 0.042 | 0.088 | 0.072 |
| LGA-Param/tukey | main_without_flagged | 17 | 0.055 | 0.063 | 0.044 | 0.087 | 0.073 |
| SaLEM-alt/raw | observed_main | 21 | 0.182 | 0.176 | 0.198 | 0.264 | 0.217 |
| SaLEM-alt/raw | main_without_flagged | 21 | 0.178 | 0.171 | 0.194 | 0.262 | 0.210 |

这里的异常训练标签过滤与定位公式的 Tukey 梯度分数过滤是两件事。去除训练异常不是将不利结果从主表删除；两种口径并列。verified50_main 与 stable_only 的全部分项见输出 CSV，不能混入同一宏平均。

## 6. 对 Average 和选公式的含义

Average=(Rel+T-Gen+M-Gen+T-Loc+M-Loc)/5。前三项衡量编辑及其泛化，M-Loc 衡量图像相关局部性保留；它们可能对层选择提出不同要求。例如 Qwen×E-VQA 的纯新范数对 Rel 为正、对 M-Loc 为负，最终对 Average 接近零。**T-Loc 恒定只是不给排序提供信息；加常数和正比例缩放不会削弱 Spearman。** Average 的相关系数也不是各分项相关系数的算术平均。

三个编辑/泛化指标自身高度相关，不能把三个同向结果当作三份独立证据：

| 指标对 | 组合数 | 平均ρ | 中位ρ |
|---|---|---|---|
| Rel 与 T-Gen | 21 | 0.965 | 0.985 |
| Rel 与 M-Gen | 21 | 0.942 | 0.989 |
| T-Gen 与 M-Gen | 21 | 0.937 | 0.983 |

当前最值得继续确认的假设是：视觉梯度强度有助于预测编辑与泛化，而单独依赖梯度强度未能稳定预测 M-Loc。主公式方向项是否有增益，应在同组合、同层集合比较，并用保留数据确认；不能仅凭此次事后拆指标就更换最终评价目标。分项相关性与原先 Top-1/Best@3/Mean@3 回答不同问题，最终推荐效用仍需固定预算的候选层成绩来检验。

## 7. 可复核文件

- [全部34版本×6指标×4口径，含数据集/模型拆分、强正负计数、中位数和组合清单](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/component_metric_correlations_20260928/all_formula_metric_summary.csv>)
- [所有达到描述阈值的正/负案例](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/component_metric_correlations_20260928/strong_positive_and_negative_cases.csv>)
- [逐组合、逐公式、逐指标的重新核验结果](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/component_metric_correlations_20260928/audited_layer_correlations.csv>)
- [纯新范数与当前主式的同组合、同层比较](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/component_metric_correlations_20260928/strength_vs_current_same_layers.csv>)
- [评测指标彼此的层级相关性](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/component_metric_correlations_20260928/outcome_metric_relations.csv>)
- [校验结果和输入哈希](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/component_metric_correlations_20260928/verification.json>)

[重现脚本](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/scripts/analyze_component_correlations_20260928.py>)。每项 ρ 独立从冻结逐层分数与实际评测重新计算，并与旧表核对；缺失或常数项未填零。
