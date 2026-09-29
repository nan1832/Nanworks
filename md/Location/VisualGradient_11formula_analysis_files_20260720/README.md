# 视觉梯度 11 公式分析文件说明

整理时间：2026-07-20

## 1. 本目录包含什么

### A. 21 组逐层原始视觉梯度分数

目录：`raw_layer_scores/`

- 数据集：`evqa-pilot500`、`mmke-visual`、`mmke-entity`
- 模型：`blip2-opt-2.7b`、`instructblip-vicuna-7b`、`minigpt-4-vicuna-7b`、`llava-v1.5-7b`、`qwen2.5-vl-3b`、`paligemma-3b`、`smolvlm-1.7b`
- 每个组合包含 `ours_direct_layer_scores.csv`
- 这些 CSV 保留了 `S_v_dot`、`S_v_conflict`、`S_v_cos`、`S_v_new_norm`、`S_v_positive_ratio`、`S_v_depth2`、`invalid_reason` 等字段，可用于派生 7 个基础视觉公式和 4 个深度加权 Ours 指标。

来源：

- 其余 6 个模型：服务器原始 21 组运行根目录 `ours_direct_7models_3datasets_g08_gpu0_20260626_131624`
- Qwen2.5-VL-3B：服务器修复版根目录 `ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304`

`ours_layer_score_derivability_report.csv` 是服务器原始运行的可派生性检查记录。

### B. 已生成的排序与候选层结果

目录：`existing_outputs/`

- `qwen_7base_4ours_candidate_topk_summary.csv`：Qwen × 3 数据集的 11 公式 Top-3/Top-5。
- `qwen_7base_4ours_full_rankings.csv`：Qwen × 3 数据集的 11 公式完整逐层排序。
- `qwen_ours_series_candidate_pool.csv`：Qwen 的 4 个 Ours 指标候选层池。
- `ours_4metrics_7models_3datasets_topk_summary.csv`：7 模型 × 3 数据集的 4 个 Ours 指标 Top-3/Top-5。
- `ours_4metrics_7models_3datasets_full_rankings.csv`：7 模型 × 3 数据集的 4 个 Ours 指标完整逐层排序。
- `ours_4metrics_7models_3datasets_pool.csv`：7 模型 × 3 数据集的 4 个 Ours 指标候选层池。

### C. 计算规范

`zn_visual_gradient_prediction_实验操作手册_7基础公式_4Ours指标_视觉版_补充诊断列_修复执行版.md`

该手册规定了 7 个基础视觉公式、4 个深度加权 Ours 指标、Top-K、失败原因和候选层池的字段与验收标准。

## 2. 当前覆盖边界

现有“完整 11 公式 Top-K/完整排序”只覆盖 Qwen2.5-VL-3B × 3 数据集。

其余 6 个模型已经具有可派生 11 公式的逐层原始分数，但当前目录中尚没有统一生成以下四个标准文件：

- `visual_gradient_layer_scores.csv`
- `visual_candidate_formula_rankings.csv`
- `visual_candidate_layers_topk.csv`
- `visual_formula_failure_reason_summary.csv`

因此，在补齐统一重算前，不能把 `ours_4metrics_7models_3datasets_*.csv` 当作 7 模型完整 11 公式结果。

## 3. 真实编辑结果

真实扫层训练与 test/eval 回填结果见同级文档：

`../6location_7model_3datas_top_3_5_layers_outcome.md`

进行公式优劣分析时，只能把具有完整 test/eval 结果的层计入有效编辑结果；失败、未评测和仅有 checkpoint 的层应单独标注，不能当作已完成结果。
