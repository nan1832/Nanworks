### 7.5 Ours 带符号方向 × 新范数：补算与真实推荐效果

新增 `Ours-signed-direction`：`S_l = S_v_cos × S_v_new_norm = E[c_i] × E[b_i]`。仅去掉主公式的绝对值；梯度对象、样本、目标、聚合顺序保持一致，无深度权重。**不等于 LGA 去旧强度的 E[c_i b_i]；后者仍按原严格补算进度登记。** 原始 LGA 使用梯度内积，包含旧范数、新范数和带符号余弦。[论文 §5.1 与附录 A](https://arxiv.org/html/2602.20207v3)。

已补算 21 组、618 个层分数，各生成 Raw/Tukey Top-3、Top-5 与完整排序。Tukey 使用每组全部有限分数、κ=1、linear 四分位数、一次过滤、降序排序，同分取浅层。保留原始有限零分层，未因新公式而修改异常层协议。

真实编辑效果使用 SWeeplayers 的 **2026-09-28T11:10:16+08:00** 快照；396 条 main、36 条 stable 分开，1 条 main-rerun 不择优替换原记录。候选缺一层就不计算完整 Best/Mean@3，不用零分、部分均值或 stable 代填 main。Top-1 是原推荐第一层的 Average；Best@3、Mean@3 为三层 Average 的最大值、均值。

**Tukey 推荐已生成 21/21 组；已有 main 能完整评估 14/21 组。7 组缺候选层结果，共 14 个不同的数据集×模型×层。4 组 Top-3 含已标记零视觉梯度层。** 负方向组中 0 分可能高于所有负分而排在第一；这不表示该层有有效梯度证据。只看已有结果的宏平均会受可评组合构成影响，因此下表采用相同组合配对。

#### 7.5.1 同组合配对效果（新版本减参照）

| 覆盖口径 | 参照版本 | 共同组数 | Top-1 新/参照 | Best@3 新/参照 | Mean@3 新/参照 | ΔBest@3 | Best 胜/平/负 |
|---|---|---|---|---|---|---|---|
| all | Ours-main/tukey | 14 | 69.128 / 69.169 | 73.443 / 73.498 | 68.227 / 68.266 | -0.055 | 0/13/1 |
| all | Ours-main/raw | 14 | 69.128 / 69.141 | 73.443 / 73.216 | 68.227 / 68.181 | 0.228 | 1/12/1 |
| all | Ours-no-direction/tukey | 12 | 70.238 / 73.042 | 75.218 / 75.661 | 69.360 / 69.543 | -0.443 | 1/10/1 |
| all | LGA-Visual/tukey | 8 | 71.766 / 74.247 | 78.742 / 78.405 | 70.782 / 71.652 | 0.337 | 1/6/1 |
| all | LGA-Param/tukey | 13 | 70.256 / 70.391 | 74.903 / 73.327 | 69.477 / 68.549 | 1.576 | 6/1/6 |
| all | Ours-signed-direction/raw | 13 | 68.595 / 68.568 | 73.242 / 72.938 | 67.637 / 67.527 | 0.304 | 1/12/0 |
| coverage80 | Ours-main/tukey | 14 | 69.128 / 69.169 | 73.443 / 73.498 | 68.227 / 68.266 | -0.055 | 0/13/1 |
| coverage80 | Ours-main/raw | 14 | 69.128 / 69.141 | 73.443 / 73.216 | 68.227 / 68.181 | 0.228 | 1/12/1 |
| coverage80 | Ours-no-direction/tukey | 12 | 70.238 / 73.042 | 75.218 / 75.661 | 69.360 / 69.543 | -0.443 | 1/10/1 |
| coverage80 | LGA-Visual/tukey | 8 | 71.766 / 74.247 | 78.742 / 78.405 | 70.782 / 71.652 | 0.337 | 1/6/1 |
| coverage80 | LGA-Param/tukey | 12 | 69.596 / 69.953 | 74.002 / 72.688 | 68.738 / 68.924 | 1.313 | 5/1/6 |
| coverage80 | Ours-signed-direction/raw | 13 | 68.595 / 68.568 | 73.242 / 72.938 | 67.637 / 67.527 | 0.304 | 1/12/0 |

**对最直接的绝对值消融：同做 Tukey 的 14 个完整共同组中，13 组 Top-3 顺序完全相同；Best@3 为 0 胜、13 平、1 负，均值差 -0.055 个百分点。现有可评结果未显示去掉绝对值有收益。** 不能把相对未过滤主公式的改善单独归因于符号，因为那个比较同时改变了过滤。

每一行内三个指标都使用该行相同的 Top-3 完整共同组，行与行的组合可以不同。coverage80 要求双方有效定位样本比例≥80%；BLIP2×MMKE-entity 的视觉定位 284/636，完整推荐保留并标记低覆盖。参数 LGA 的样本集合另有差异。

#### 7.5.2 带符号 Tukey 逐组合结果

| 数据集 | 模型 | 带符号 Tukey Top-3 | Top-1 | Best@3 | Mean@3 | 缺 main 层 | 定位样本 |
|---|---|---|---|---|---|---|---|
| evqa-pilot500 | BLIP2 | L1, L2, L3 | 58.506 | 62.460 | 57.031 | — | 465/500 |
| evqa-pilot500 | InstructBLIP | L1, L0, L11 | 54.470 | 54.470 | 51.987 | — | 500/500 |
| evqa-pilot500 | MiniGPT-4 | L18, L19, L16 | 59.560 | 64.938 | 60.959 | — | 499/500 |
| evqa-pilot500 | LLaVA-1.5 | L31†, L30, L29 | 58.076 | — | — | L29 | 500/500 |
| evqa-pilot500 | Qwen2.5-VL | L21, L19, L17 | 63.740 | 63.740 | 63.182 | — | 500/500 |
| evqa-pilot500 | PaliGemma | L5, L4, L3 | 78.170 | 85.720 | 78.340 | — | 500/500 |
| evqa-pilot500 | SmolVLM | L23†, L22, L21 | — | — | — | L23 | 500/500 |
| mmke-visual | BLIP2 | L5, L6, L7 | — | — | — | L5, L6, L7 | 175/214 |
| mmke-visual | InstructBLIP | L1, L0, L3 | 70.280 | 71.294 | 64.244 | — | 214/214 |
| mmke-visual | MiniGPT-4 | L2, L0, L1 | 76.064 | 76.064 | 75.900 | — | 214/214 |
| mmke-visual | LLaVA-1.5 | L31†, L29, L28 | — | — | — | L31, L29 | 214/214 |
| mmke-visual | Qwen2.5-VL | L0, L1, L2 | 70.420 | 70.420 | 69.943 | — | 214/214 |
| mmke-visual | PaliGemma | L5, L4, L3 | 62.544 | 99.026 | 64.037 | — | 214/214 |
| mmke-visual | SmolVLM | L0, L1, L2 | 71.360 | 71.360 | 70.687 | — | 214/214 |
| mmke-entity | BLIP2 | L6, L8, L31† | — | — | — | L6, L8, L31 | 284/636 |
| mmke-entity | InstructBLIP | L1, L0, L3 | 69.180 | 69.180 | 62.507 | — | 636/636 |
| mmke-entity | MiniGPT-4 | L0, L1, L30 | 75.336 | — | — | L30 | 636/636 |
| mmke-entity | LLaVA-1.5 | L20, L21, L2 | — | — | — | L20, L21, L2 | 636/636 |
| mmke-entity | Qwen2.5-VL | L0, L1, L2 | 72.220 | 72.280 | 72.180 | — | 636/636 |
| mmke-entity | PaliGemma | L5, L4, L3 | 90.810 | 96.136 | 93.305 | — | 636/636 |
| mmke-entity | SmolVLM | L0, L1, L2 | 70.470 | 71.120 | 70.880 | — | 636/636 |

† 为原始日志的有限零视觉梯度层。这里的缺层不是推荐公式未算出；Top-1 在第一层已有评测时可单独报告，Best/Mean@3 仍必须三层齐全。Top-5、逐层分数和各公式的全部剔除层见机器可读文件及第 7.4 节。

#### 7.5.3 去除已标记训练异常后的配对检查

| 评测口径 | 覆盖口径 | 共同组数 | ΔTop-1 | ΔBest@3 | ΔMean@3 | Best 胜/平/负 |
|---|---|---|---|---|---|---|
| observed_main | all | 14 | -0.040 | -0.055 | -0.039 | 0/13/1 |
| observed_main | coverage80 | 14 | -0.040 | -0.055 | -0.039 | 0/13/1 |
| main_without_flagged | all | 13 | -0.044 | -0.059 | -0.042 | 0/12/1 |
| main_without_flagged | coverage80 | 13 | -0.044 | -0.059 | -0.042 | 0/12/1 |

主表保留所有 main 实测结果；main_without_flagged 排除恢复/诊断训练、数值异常/保护、不收敛标签，与 Tukey 的层定位分数过滤不同。verified50_main 和 stable_only 单独存入 CSV。相关缺层使部分负方向组尚不能进入完整比较，不能从现有可比子集外推 21 组整体胜率。

[新增推荐含完整排序](../../outputs/ours_signed_direction_20260928/recommendations.json) · [逐层 C、N 与带符号分数](../../outputs/ours_signed_direction_20260928/signed_layer_scores.csv) · [Top-1/3/5 及分项成绩](../../outputs/ours_signed_direction_20260928/recommendation_performance.csv) · [同组合配对比较](../../outputs/ours_signed_direction_20260928/paired_comparisons.csv) · [缺失候选层](../../outputs/ours_signed_direction_20260928/missing_evaluations.csv) · [独立核验](../../outputs/ours_signed_direction_20260928/verification.json)

复现顺序：`python scripts/build_all_method_recommendations.py` → `python scripts/evaluate_ours_signed_direction_20260928.py` → `python scripts/build_all_method_recommendations.py`。最后一步将本节回填到总表，后续同步不会丢失新增公式。这里是已有实验的回顾性比较，没有新训练或测试集独立确认。
