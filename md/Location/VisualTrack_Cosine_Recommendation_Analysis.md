# 绿色曲线：视觉表征与首答案预测位置的余弦相似度

**2026-09-28 更新：**根据后续要求，补算现已扩展为 none、alt、model_pred 三版本，完整答案预测位置均值与固定前缀处理见[三版本方案及执行状态](VisualTrack_Three_Variants_20260928.md)。下文桥梁排名仍为原始不带答案版本的复算记录；最新正式补算状态以三版本报告为准。

公式：`S_l = mean_i cos(mean_visual_tokens(h_i,l), h_i,l[last_prompt_position])`。图像与提示词前向输入，不输入 alt 或 model_pred 答案；因此这条曲线不区分新目标与旧目标。测量位置为解码层输出，与现有 adapter 候选接口逐层对应。

截图已定位到 LLaVA 桥梁 4 样本归档；L20 的归一化值为 0.679654，与截图吻合。图中 min-max 归一化不改变降序排名，正仿射变换也不改变此处 Tukey 保留集合。本次直接使用原始余弦，不根据曲线形状挑区段。

## 已有桥梁曲线的实际候选

| 模型 | 桥梁样本数 | 过滤 | Top-3 | Top-5 | 剔除层 |
|---|---|---|---|---|---|
| llava-v1.5-7b | 4 | raw | L31, L20, L19 | L31, L20, L19, L29, L28 | — |
| llava-v1.5-7b | 4 | tukey | L20, L19, L29 | L20, L19, L29, L28, L21 | L31 |
| llava-v1.5-7b | 30 | raw | L31, L29, L20 | L31, L29, L20, L28, L19 | — |
| llava-v1.5-7b | 30 | tukey | L29, L20, L28 | L29, L20, L28, L19, L30 | L31 |
| blip2-opt-2.7b | 4 | raw | L3, L5, L8 | L3, L5, L8, L6, L7 | — |
| blip2-opt-2.7b | 4 | tukey | L3, L5, L8 | L3, L5, L8, L6, L7 | — |

这些是桥梁样本上的定位结果。不能配上 E-VQA/MMKE 的层成绩，冒充同任务推荐性能；当前正式扫层台账也不包含桥梁任务，故不填造它的 Best@3。

## 正式数据补算与比较

**完成时间：2026-09-29T08:37:52+0800；服务器核验时间：2026-09-29T09:18:13.102942+08:00。** 7 个模型 × 3 个数据集均已完成，每组含 none、alt、model_pred 三版，共 63 份定位统计；各自报告 Raw / Tukey，共 126 份主推荐。

正式三版本结果已经完成；本页上方桥梁候选仅作原始曲线追溯，不与 E-VQA/MMKE 编辑成绩混配。完整结果见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)，候选表见[推荐总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)。

编辑性能配对固定使用 **2026-09-28T11:10:16+08:00** 的扫层快照，396 条 main；36 条 stable 与 1 条 main-rerun 不代填或择优替换。此处未添加任何新训练结果。Top-1 是第一推荐层的 Average；Best@3、Mean@3 分别为完整三候选层的最大值、均值。缺任一候选的 main 评测就不计算完整 Best/Mean@3。以下三版汇总固定使用同一批三方 Top-3 都有评测且定位覆盖率 ≥80% 的组合；Raw 与 Tukey 的共同组合可能不同，不能直接把跨表均值差当作过滤收益。

| 版本 | 排序 | 三版共同可比组数 | Top-1 | Best@3 | Mean@3 |
|---|---|---|---|---|---|
| none | raw | 4 | 69.169 | 72.221 | 63.201 |
| alt | raw | 4 | 71.901 | 73.052 | 63.854 |
| model_pred | raw | 4 | 69.169 | 72.221 | 63.201 |
| none | tukey | 3 | 73.601 | 77.245 | 65.447 |
| alt | tukey | 3 | 77.245 | 78.300 | 66.300 |
| model_pred | tukey | 3 | 73.601 | 77.245 | 65.447 |

## 复核与文件

- [桥梁候选与 Tukey 边界](../../outputs/visual_track_cosine_20260928/bridge_candidates.csv)
- [21 组前向统计状态](../../outputs/visual_track_cosine_20260928/targets_v2/source_status.csv)
- [正式逐组推荐](../../outputs/visual_track_cosine_20260928/targets_v2/recommendations.json)
- [已有 main 上的 Top-1、Best@3、Mean@3](../../outputs/visual_track_cosine_20260928/targets_v2/performance.csv)。
- [同组合配对汇总](../../outputs/visual_track_cosine_20260928/targets_v2/paired_summary.csv)
- [各分项指标层级相关性](../../outputs/visual_track_cosine_20260928/targets_v2/correlations.csv)。
- [服务器已有文件查找证据](../../outputs/visual_track_cosine_20260928/remote_source_audit.json)
- [补算作业状态](../../outputs/visual_track_cosine_20260928/targets_v2/status.json)

当前正式三版本的复算与回填入口见[完整结果报告](VisualTrack_Three_Variants_Results_20260929.md)；原桥梁曲线程序仅用于历史结果追溯。
