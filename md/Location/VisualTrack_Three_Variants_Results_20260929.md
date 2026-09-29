# 视觉表征余弦三版本：完整定位结果与已有编辑效果

**完成时间：2026-09-29T08:37:52+0800；服务器核验时间：2026-09-29T09:18:13.102942+08:00。** 7 个模型 × 3 个数据集均已完成，每组含 none、alt、model_pred 三版，共 63 份定位统计；各自报告 Raw / Tukey，共 126 份主推荐。

VisualTrack-Cos-none：视觉 token 平均表征与最后提示词位置的余弦。VisualTrack-Cos-alt / VisualTrack-Cos-model_pred：固定同一图像与提示词前缀，追加对应答案，对完整答案的有效预测位置先取余弦均值，再对样本等权平均。预测 yₜ 的位置是 P−1+t；不使用读入 yₜ 后的位置代替。单个普通答案 token 时可退化为 none。model_pred 使用冻结历史缓存的全部可用文本，不补写被历史生成长度截断的内容。

这是表征余弦方法，与梯度方向余弦、LGA 梯度内积及 VisEdit 贡献度分别报告。主表复用历史视觉梯度有效样本 ID（matched_gradient）；available_train 单列于机器文件。Raw 按有符号余弦降序，Tukey 按每组每版全部有限层分数、κ=1、linear 四分位一次过滤；同分取浅层。表中首层为 Top-1 推荐层，最高层分数不等于最高编辑效果。

## 比较口径与覆盖率

编辑性能配对固定使用 **2026-09-28T11:10:16+08:00** 的扫层快照，396 条 main；36 条 stable 与 1 条 main-rerun 不代填或择优替换。此处未添加任何新训练结果。Top-1 是第一推荐层的 Average；Best@3、Mean@3 分别为完整三候选层的最大值、均值。缺任一候选的 main 评测就不计算完整 Best/Mean@3。以下三版汇总固定使用同一批三方 Top-3 都有评测且定位覆盖率 ≥80% 的组合；Raw 与 Tukey 的共同组合可能不同，不能直接把跨表均值差当作过滤收益。

BLIP2 × MMKE-entity 的主定位样本为 284/636（44.65%），逐组结果保留，≥80% 汇总中排除；全样本统计仅作独立补充。T-Loc 在冻结 main 结果中为常量，其层级相关性未定义，不记为零。

## 三版共同组合的 Top-1、Best@3、Mean@3

| 版本 | 排序 | 三版共同可比组数 | Top-1 | Best@3 | Mean@3 |
|---|---|---|---|---|---|
| none | raw | 4 | 69.169 | 72.221 | 63.201 |
| alt | raw | 4 | 71.901 | 73.052 | 63.854 |
| model_pred | raw | 4 | 69.169 | 72.221 | 63.201 |
| none | tukey | 3 | 73.601 | 77.245 | 65.447 |
| alt | tukey | 3 | 77.245 | 78.300 | 66.300 |
| model_pred | tukey | 3 | 73.601 | 77.245 | 65.447 |

共同组合清单见[固定组合 CSV](../../outputs/visual_track_cosine_20260928/targets_v2/three_variant_fixed_cohort.csv)。

## 与既有公式的同组合配对

以下按相同 Raw/Tukey 规则、相同模型×数据集及候选评测齐全的组合配对；各行组合数可能不同。参数与视觉梯度方法本身的样本协议不同，不能把这里解释为逐样本梯度对齐实验。Δ 为 VisualTrack 减参照，单位为百分点评测分数；正数表示 VisualTrack 较高。

| 版本 | 排序 | 参照 | 配对组数 | ΔTop-1 | ΔBest@3 | ΔMean@3 | Best@3 胜/平/负 |
|---|---|---|---|---|---|---|---|
| none | raw | Ours-no-direction | 7 | -12.031 | -12.934 | -9.045 | 0/0/7 |
| none | raw | Ours-main | 7 | -7.177 | -12.163 | -8.701 | 0/0/7 |
| none | raw | Ours-signed-direction | 5 | -6.564 | -13.985 | -10.055 | 0/0/5 |
| none | raw | LGA-Visual | 5 | -8.459 | -14.804 | -10.765 | 0/0/5 |
| none | raw | LGA-Param | 7 | 11.091 | -7.607 | 0.768 | 1/1/5 |
| none | tukey | Ours-no-direction | 7 | -10.249 | -12.204 | -8.696 | 0/0/7 |
| none | tukey | Ours-main | 7 | -7.001 | -11.920 | -8.481 | 0/0/7 |
| none | tukey | Ours-signed-direction | 6 | -5.937 | -11.925 | -8.701 | 0/0/6 |
| none | tukey | LGA-Visual | 5 | -10.535 | -13.446 | -11.446 | 0/0/5 |
| none | tukey | LGA-Param | 7 | -6.240 | -6.260 | -6.253 | 1/0/6 |
| alt | raw | Ours-no-direction | 4 | -7.508 | -11.007 | -7.613 | 0/1/3 |
| alt | raw | Ours-main | 4 | 1.180 | -9.466 | -6.817 | 0/1/3 |
| alt | raw | Ours-signed-direction | 3 | 6.273 | -8.400 | -6.466 | 0/1/2 |
| alt | raw | LGA-Visual | 3 | 3.115 | -9.765 | -7.650 | 0/1/2 |
| alt | raw | LGA-Param | 4 | 23.207 | -1.757 | 5.987 | 2/0/2 |
| alt | tukey | Ours-no-direction | 5 | -4.270 | -8.156 | -6.123 | 0/1/4 |
| alt | tukey | Ours-main | 5 | 0.440 | -7.604 | -5.713 | 0/1/4 |
| alt | tukey | Ours-signed-direction | 4 | 3.716 | -6.725 | -5.488 | 0/1/3 |
| alt | tukey | LGA-Visual | 4 | -1.248 | -6.052 | -7.227 | 0/0/4 |
| alt | tukey | LGA-Param | 5 | -2.272 | -3.595 | -6.614 | 1/0/4 |
| model_pred | raw | Ours-no-direction | 6 | -13.584 | -14.819 | -10.230 | 0/0/6 |
| model_pred | raw | Ours-main | 6 | -7.792 | -13.791 | -9.699 | 0/0/6 |
| model_pred | raw | Ours-signed-direction | 5 | -6.531 | -13.985 | -10.055 | 0/0/5 |
| model_pred | raw | LGA-Visual | 5 | -8.426 | -14.804 | -10.765 | 0/0/5 |
| model_pred | raw | LGA-Param | 6 | 13.391 | -8.508 | 1.250 | 1/1/4 |
| model_pred | tukey | Ours-no-direction | 7 | -10.172 | -11.412 | -8.053 | 1/0/6 |
| model_pred | tukey | Ours-main | 7 | -5.329 | -10.653 | -7.738 | 0/0/7 |
| model_pred | tukey | Ours-signed-direction | 7 | -5.329 | -10.653 | -7.738 | 0/0/7 |
| model_pred | tukey | LGA-Visual | 6 | -9.411 | -11.865 | -10.098 | 0/0/6 |
| model_pred | tukey | LGA-Param | 7 | -6.180 | -6.617 | -6.499 | 0/0/7 |

## 逐组合推荐性能与缺失评测层

“待补”表示冻结扫层快照缺少所需 main 评测，不代表零分。样本不足 80% 的行单独标记。

### evqa-pilot500

| 模型 | 版本 | 排序 | Top-1 层 | Top-1 | Best@3 | Mean@3 | 缺失 main 层 | 定位样本 |
|---|---|---|---|---|---|---|---|---|
| BLIP2 | none | raw | L8 | 待补 | 待补 | 待补 | L8, L6 | 465/500 |
| BLIP2 | none | tukey | L8 | 待补 | 待补 | 待补 | L8, L6 | 465/500 |
| BLIP2 | alt | raw | L5 | 68.890 | 待补 | 待补 | L6 | 465/500 |
| BLIP2 | alt | tukey | L5 | 68.890 | 待补 | 待补 | L6 | 465/500 |
| BLIP2 | model_pred | raw | L5 | 68.890 | 待补 | 待补 | L6 | 465/500 |
| BLIP2 | model_pred | tukey | L5 | 68.890 | 待补 | 待补 | L6 | 465/500 |
| InstructBLIP | none | raw | L22 | 待补 | 待补 | 待补 | L22, L24, L23 | 500/500 |
| InstructBLIP | none | tukey | L22 | 待补 | 待补 | 待补 | L22, L24, L23 | 500/500 |
| InstructBLIP | alt | raw | L5 | 待补 | 待补 | 待补 | L5, L6 | 500/500 |
| InstructBLIP | alt | tukey | L5 | 待补 | 待补 | 待补 | L5, L6 | 500/500 |
| InstructBLIP | model_pred | raw | L5 | 待补 | 待补 | 待补 | L5, L6 | 500/500 |
| InstructBLIP | model_pred | tukey | L5 | 待补 | 待补 | 待补 | L5, L6 | 500/500 |
| MiniGPT4 | none | raw | L29 | 58.526 | 58.526 | 58.243 | — | 499/500 |
| MiniGPT4 | none | tukey | L29 | 58.526 | 58.526 | 58.243 | — | 499/500 |
| MiniGPT4 | alt | raw | L29 | 58.526 | 58.526 | 58.243 | — | 499/500 |
| MiniGPT4 | alt | tukey | L29 | 58.526 | 58.526 | 58.243 | — | 499/500 |
| MiniGPT4 | model_pred | raw | L29 | 58.526 | 58.526 | 58.243 | — | 499/500 |
| MiniGPT4 | model_pred | tukey | L29 | 58.526 | 58.526 | 58.243 | — | 499/500 |
| LLaVA | none | raw | L31 | 58.076 | 待补 | 待补 | L29 | 500/500 |
| LLaVA | none | tukey | L31 | 58.076 | 待补 | 待补 | L29 | 500/500 |
| LLaVA | alt | raw | L31 | 58.076 | 待补 | 待补 | L29 | 500/500 |
| LLaVA | alt | tukey | L31 | 58.076 | 待补 | 待补 | L29 | 500/500 |
| LLaVA | model_pred | raw | L31 | 58.076 | 待补 | 待补 | L29 | 500/500 |
| LLaVA | model_pred | tukey | L31 | 58.076 | 待补 | 待补 | L29 | 500/500 |
| Qwen2.5-VL | none | raw | L34 | 62.770 | 待补 | 待补 | L33, L32 | 500/500 |
| Qwen2.5-VL | none | tukey | L33 | 待补 | 待补 | 待补 | L33, L32 | 500/500 |
| Qwen2.5-VL | alt | raw | L34 | 62.770 | 待补 | 待补 | L33, L32 | 500/500 |
| Qwen2.5-VL | alt | tukey | L33 | 待补 | 待补 | 待补 | L33, L32 | 500/500 |
| Qwen2.5-VL | model_pred | raw | L34 | 62.770 | 待补 | 待补 | L33, L32 | 500/500 |
| Qwen2.5-VL | model_pred | tukey | L31 | 63.052 | 63.052 | 62.647 | — | 500/500 |
| PaliGemma | none | raw | L2 | 待补 | 待补 | 待补 | L2 | 500/500 |
| PaliGemma | none | tukey | L2 | 待补 | 待补 | 待补 | L2 | 500/500 |
| PaliGemma | alt | raw | L2 | 待补 | 待补 | 待补 | L2 | 500/500 |
| PaliGemma | alt | tukey | L2 | 待补 | 待补 | 待补 | L2 | 500/500 |
| PaliGemma | model_pred | raw | L2 | 待补 | 待补 | 待补 | L2 | 500/500 |
| PaliGemma | model_pred | tukey | L2 | 待补 | 待补 | 待补 | L2 | 500/500 |
| SmolVLM | none | raw | L22 | 55.872 | 57.150 | 56.463 | — | 500/500 |
| SmolVLM | none | tukey | L20 | 57.150 | 58.848 | 57.769 | — | 500/500 |
| SmolVLM | alt | raw | L22 | 55.872 | 57.308 | 56.515 | — | 500/500 |
| SmolVLM | alt | tukey | L19 | 57.308 | 58.848 | 57.769 | — | 500/500 |
| SmolVLM | model_pred | raw | L22 | 55.872 | 57.150 | 56.463 | — | 500/500 |
| SmolVLM | model_pred | tukey | L17 | 58.848 | 待补 | 待补 | L18 | 500/500 |

### mmke-visual

| 模型 | 版本 | 排序 | Top-1 层 | Top-1 | Best@3 | Mean@3 | 缺失 main 层 | 定位样本 |
|---|---|---|---|---|---|---|---|---|
| BLIP2 | none | raw | L8 | 待补 | 待补 | 待补 | L8, L6, L7 | 175/214 |
| BLIP2 | none | tukey | L8 | 待补 | 待补 | 待补 | L8, L6, L7 | 175/214 |
| BLIP2 | alt | raw | L3 | 68.742 | 待补 | 待补 | L5 | 175/214 |
| BLIP2 | alt | tukey | L3 | 68.742 | 待补 | 待补 | L5 | 175/214 |
| BLIP2 | model_pred | raw | L5 | 待补 | 待补 | 待补 | L5, L6 | 175/214 |
| BLIP2 | model_pred | tukey | L5 | 待补 | 待补 | 待补 | L5, L6 | 175/214 |
| InstructBLIP | none | raw | L4 | 49.858 | 50.024 | 49.861 | — | 214/214 |
| InstructBLIP | none | tukey | L4 | 49.858 | 50.024 | 49.861 | — | 214/214 |
| InstructBLIP | alt | raw | L14 | 50.024 | 待补 | 待补 | L10, L8 | 214/214 |
| InstructBLIP | alt | tukey | L14 | 50.024 | 待补 | 待补 | L10, L8 | 214/214 |
| InstructBLIP | model_pred | raw | L14 | 50.024 | 50.024 | 49.861 | — | 214/214 |
| InstructBLIP | model_pred | tukey | L14 | 50.024 | 50.024 | 49.861 | — | 214/214 |
| MiniGPT4 | none | raw | L29 | 73.266 | 74.438 | 73.966 | — | 214/214 |
| MiniGPT4 | none | tukey | L29 | 73.266 | 74.438 | 73.966 | — | 214/214 |
| MiniGPT4 | alt | raw | L29 | 73.266 | 待补 | 待补 | L30 | 214/214 |
| MiniGPT4 | alt | tukey | L29 | 73.266 | 待补 | 待补 | L30 | 214/214 |
| MiniGPT4 | model_pred | raw | L29 | 73.266 | 待补 | 待补 | L30 | 214/214 |
| MiniGPT4 | model_pred | tukey | L29 | 73.266 | 待补 | 待补 | L30 | 214/214 |
| LLaVA | none | raw | L31 | 待补 | 待补 | 待补 | L31, L29 | 214/214 |
| LLaVA | none | tukey | L31 | 待补 | 待补 | 待补 | L31, L29 | 214/214 |
| LLaVA | alt | raw | L31 | 待补 | 待补 | 待补 | L31, L29, L30 | 214/214 |
| LLaVA | alt | tukey | L29 | 待补 | 待补 | 待补 | L29, L30 | 214/214 |
| LLaVA | model_pred | raw | L31 | 待补 | 待补 | 待补 | L31, L29 | 214/214 |
| LLaVA | model_pred | tukey | L31 | 待补 | 待补 | 待补 | L31, L29 | 214/214 |
| Qwen2.5-VL | none | raw | L34 | 待补 | 待补 | 待补 | L34, L33, L32 | 214/214 |
| Qwen2.5-VL | none | tukey | L34 | 待补 | 待补 | 待补 | L34, L33, L32 | 214/214 |
| Qwen2.5-VL | alt | raw | L34 | 待补 | 待补 | 待补 | L34, L33, L32 | 214/214 |
| Qwen2.5-VL | alt | tukey | L32 | 待补 | 待补 | 待补 | L32, L31 | 214/214 |
| Qwen2.5-VL | model_pred | raw | L34 | 待补 | 待补 | 待补 | L34, L33, L32 | 214/214 |
| Qwen2.5-VL | model_pred | tukey | L33 | 待补 | 待补 | 待补 | L33, L32, L31 | 214/214 |
| PaliGemma | none | raw | L2 | 80.238 | 80.238 | 50.141 | — | 214/214 |
| PaliGemma | none | tukey | L2 | 80.238 | 80.238 | 50.141 | — | 214/214 |
| PaliGemma | alt | raw | L2 | 80.238 | 80.238 | 50.276 | — | 214/214 |
| PaliGemma | alt | tukey | L2 | 80.238 | 80.238 | 50.276 | — | 214/214 |
| PaliGemma | model_pred | raw | L2 | 80.238 | 80.238 | 50.141 | — | 214/214 |
| PaliGemma | model_pred | tukey | L2 | 80.238 | 80.238 | 50.141 | — | 214/214 |
| SmolVLM | none | raw | L22 | 待补 | 待补 | 待补 | L22 | 214/214 |
| SmolVLM | none | tukey | L22 | 待补 | 待补 | 待补 | L22 | 214/214 |
| SmolVLM | alt | raw | L22 | 待补 | 待补 | 待补 | L22 | 214/214 |
| SmolVLM | alt | tukey | L20 | 67.404 | 69.660 | 68.135 | — | 214/214 |
| SmolVLM | model_pred | raw | L22 | 待补 | 待补 | 待补 | L22 | 214/214 |
| SmolVLM | model_pred | tukey | L20 | 67.404 | 67.404 | 67.330 | — | 214/214 |

### mmke-entity

| 模型 | 版本 | 排序 | Top-1 层 | Top-1 | Best@3 | Mean@3 | 缺失 main 层 | 定位样本 |
|---|---|---|---|---|---|---|---|---|
| BLIP2 | none | raw | L8 | 待补 | 待补 | 待补 | L8, L7, L6 | 284/636（低覆盖） |
| BLIP2 | none | tukey | L8 | 待补 | 待补 | 待补 | L8, L7, L6 | 284/636（低覆盖） |
| BLIP2 | alt | raw | L3 | 71.012 | 72.242 | 71.525 | — | 284/636（低覆盖） |
| BLIP2 | alt | tukey | L3 | 71.012 | 72.242 | 71.525 | — | 284/636（低覆盖） |
| BLIP2 | model_pred | raw | L3 | 71.012 | 待补 | 待补 | L5 | 284/636（低覆盖） |
| BLIP2 | model_pred | tukey | L3 | 71.012 | 待补 | 待补 | L5 | 284/636（低覆盖） |
| InstructBLIP | none | raw | L4 | 48.890 | 48.890 | 48.576 | — | 636/636 |
| InstructBLIP | none | tukey | L4 | 48.890 | 48.890 | 48.576 | — | 636/636 |
| InstructBLIP | alt | raw | L8 | 待补 | 待补 | 待补 | L8, L10 | 636/636 |
| InstructBLIP | alt | tukey | L8 | 待补 | 待补 | 待补 | L8, L10 | 636/636 |
| InstructBLIP | model_pred | raw | L4 | 48.890 | 48.890 | 48.576 | — | 636/636 |
| InstructBLIP | model_pred | tukey | L4 | 48.890 | 48.890 | 48.576 | — | 636/636 |
| MiniGPT4 | none | raw | L29 | 待补 | 待补 | 待补 | L29 | 636/636 |
| MiniGPT4 | none | tukey | L29 | 待补 | 待补 | 待补 | L29 | 636/636 |
| MiniGPT4 | alt | raw | L29 | 待补 | 待补 | 待补 | L29, L30 | 636/636 |
| MiniGPT4 | alt | tukey | L29 | 待补 | 待补 | 待补 | L29, L30 | 636/636 |
| MiniGPT4 | model_pred | raw | L29 | 待补 | 待补 | 待补 | L29, L30 | 636/636 |
| MiniGPT4 | model_pred | tukey | L29 | 待补 | 待补 | 待补 | L29, L30 | 636/636 |
| LLaVA | none | raw | L29 | 待补 | 待补 | 待补 | L29, L31 | 636/636 |
| LLaVA | none | tukey | L29 | 待补 | 待补 | 待补 | L29, L31 | 636/636 |
| LLaVA | alt | raw | L31 | 待补 | 待补 | 待补 | L31, L29, L30 | 636/636 |
| LLaVA | alt | tukey | L28 | 74.742 | 75.148 | 75.011 | — | 636/636 |
| LLaVA | model_pred | raw | L31 | 待补 | 待补 | 待补 | L31, L29 | 636/636 |
| LLaVA | model_pred | tukey | L31 | 待补 | 待补 | 待补 | L31, L29 | 636/636 |
| Qwen2.5-VL | none | raw | L34 | 待补 | 待补 | 待补 | L34, L31, L32 | 636/636 |
| Qwen2.5-VL | none | tukey | L34 | 待补 | 待补 | 待补 | L34, L31, L32 | 636/636 |
| Qwen2.5-VL | alt | raw | L34 | 待补 | 待补 | 待补 | L34, L33, L32 | 636/636 |
| Qwen2.5-VL | alt | tukey | L32 | 待补 | 待补 | 待补 | L32, L31 | 636/636 |
| Qwen2.5-VL | model_pred | raw | L34 | 待补 | 待补 | 待补 | L34, L33, L32 | 636/636 |
| Qwen2.5-VL | model_pred | tukey | L33 | 待补 | 待补 | 待补 | L33, L32, L31 | 636/636 |
| PaliGemma | none | raw | L2 | 82.040 | 92.970 | 87.957 | — | 636/636 |
| PaliGemma | none | tukey | L2 | 82.040 | 92.970 | 87.957 | — | 636/636 |
| PaliGemma | alt | raw | L3 | 92.970 | 96.136 | 90.382 | — | 636/636 |
| PaliGemma | alt | tukey | L3 | 92.970 | 96.136 | 90.382 | — | 636/636 |
| PaliGemma | model_pred | raw | L2 | 82.040 | 92.970 | 87.957 | — | 636/636 |
| PaliGemma | model_pred | tukey | L2 | 82.040 | 92.970 | 87.957 | — | 636/636 |
| SmolVLM | none | raw | L22 | 待补 | 待补 | 待补 | L22, L21, L19 | 636/636 |
| SmolVLM | none | tukey | L22 | 待补 | 待补 | 待补 | L22, L21, L19 | 636/636 |
| SmolVLM | alt | raw | L22 | 待补 | 待补 | 待补 | L22, L21, L20 | 636/636 |
| SmolVLM | alt | tukey | L21 | 待补 | 待补 | 待补 | L21, L20 | 636/636 |
| SmolVLM | model_pred | raw | L22 | 待补 | 待补 | 待补 | L22, L21, L20 | 636/636 |
| SmolVLM | model_pred | tukey | L20 | 待补 | 待补 | 待补 | L20, L19 | 636/636 |

## 核验、文件与复算

[推荐层完整表](ALL_Methods_Recommends_layers.md#visual-track-three-variants) · [全部逐组推荐](../../outputs/visual_track_cosine_20260928/targets_v2/recommendations.json) · [性能明细](../../outputs/visual_track_cosine_20260928/targets_v2/performance.csv) · [逐层相关性六项指标](../../outputs/visual_track_cosine_20260928/targets_v2/correlations.csv) · [全部同组合配对](../../outputs/visual_track_cosine_20260928/targets_v2/paired_summary.csv) · [21 组来源状态](../../outputs/visual_track_cosine_20260928/targets_v2/source_status.csv) · [完成回执](../../outputs/visual_track_cosine_20260928/targets_v2/completion_receipt.json)。

复算顺序：`python scripts/visual_track_targets_remote_20260928.py fetch` → `python scripts/analyze_visual_track_targets_20260928.py` → `python scripts/backfill_visual_track_results_20260929.py`。本次先逐样本验证服务器 SHA-256，再同步紧凑统计；回填脚本再次核对 21 份完成回执、样本数、协议与分数哈希。原始程序及 SmolVLM 修复版本均保留于协议中。
