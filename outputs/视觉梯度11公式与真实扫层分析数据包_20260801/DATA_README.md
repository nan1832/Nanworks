# 视觉梯度 11 公式与真实扫层分析数据包

生成时间：2026-08-01

## 文件

- `visual_gradient_layer_scores.csv`：21 个模型×数据集组合，逐层视觉梯度及 7 个基础公式、4 个 Ours 指标；共 618 行。
- `visual_candidate_formula_rankings.csv`：11 个公式的完整逐层排序；共 6174 行。
- `visual_candidate_layers_topk.csv`：11 个公式的 Top-3/Top-5，按候选排名展开；共 1770 行。
- `visual_formula_failure_reason_summary.csv`：每个 dataset×model×formula 一行；共 231 行。
- `formula_global_summary.csv`：公式与真实编辑结果的全局汇总，含 Spearman、Best/Mean/Regret 等。
- `real_layer_sweep_results_by_seed.csv`：本地总表中已验收的真实扫层正式评测结果；共 331 行。
- `zn_visual_gradient_prediction_实验操作手册_7基础公式_4Ours指标_视觉版_补充诊断列_修复执行版.md`：11 公式专项操作手册。
- `source_analysis_manifest.json`：原始 21 个 layer score 文件的 SHA-256 清单和分析边界。

## 重要边界

1. `real_layer_sweep_results_by_seed.csv` 保留了 `seed` 字段，但本地结果总表没有逐行登记 seed，服务器 SSH 当前也无法非交互认证，因此统一写为 `not_recorded`；不能把这些行解释为多 seed 统计。
2. `config_hash` 同样不在本地总表/已同步产物中，保持为空，并在 `config_hash_status` 明确标记。没有伪造 hash。
3. `config_profile`、`recovery_status`、`numeric_status`、`analysis_eligibility` 分列保存。main、stable、recovered、numeric anomaly 未混合，也没有跨配置取最大值。
4. PaliGemma main 是主口径；stable 只作为敏感性结果。恢复运行与数值异常结果必须单独分析。
5. `visual_formula_failure_reason_summary.csv` 的样本级 `empty_model_pred_count`、`missing_image_count`、`empty_visual_span_count` 在本地逐层原始 CSV 中不存在，因此留空；层级 zero-grad/nonfinite/negative-cos 统计已填写。
6. 所有真实扫层行来自本地台账 §4.0，台账的进入条件为非空 `selected_checkpoint.tsv`、`eval_full.done` 与对应独立 test/eval 完整结果。

## 质量检查

- 原始 layer score 文件：21 / 21。
- 逐层记录：618 / 618。
- 公式组合：231 / 231。
- 失败原因组合：231 / 231。
- 真实扫层完成记录：331 行。
- 配置分布：{'main': 296, 'stable': 35}。
- 分析口径分布：{'main_primary': 286, 'replicate_excluded_primary': 1, 'separate_recovered': 8, 'separate_numeric_anomaly': 1, 'stable_sensitivity': 31, 'separate_stable_recovered': 4}。
- eval sample count 不匹配：0 行。
- Average 五指标回算超出 0.015：0 行（通常应为 0；若非 0 请查看 `metric_consistency=review`）。
