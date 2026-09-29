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

当前完成 **0/21** 个正式数据集×模型组合。缺失前向统计的组合在 formal_source_status.csv 标为 pending，不给零分。已测编辑成绩沿用 2026-09-28T11:10:16+08:00 的 main 配置快照；缺候选层评测就不计算完整 Best/Mean@3。

主比较使用 matched_gradient，即与原视觉梯度方法完全相同的样本 ID；all_train 单列，避免把覆盖率变化混成公式改进。native 精度复现原图的计算定义，另保存 float32 重算作数值敏感性检查。Raw 保留全部有限层；Tukey 在全层分数上用 κ=1、linear 四分位数一次过滤，再降序推荐，同分取浅层。没有按编辑结果修改排序、翻转符号或删除末层。

**尚无正式三数据集的绿线分数，当前不能判断它是否优于新梯度范数。桥梁曲线的峰值高低不是编辑性能的证据。**

最近调度状态：`3463118|PENDING|(QOSMaxGRESPerUser)||0:00|2:00:00`；采集时间 2026-09-28T16:45:29.426359+08:00。

## 复核与文件

- [桥梁候选与 Tukey 边界](../../outputs/visual_track_cosine_20260928/bridge_candidates.csv)
- [21 组前向统计状态](../../outputs/visual_track_cosine_20260928/formal_source_status.csv)
- [正式逐组推荐](../../outputs/visual_track_cosine_20260928/recommendations.json)
- 已有 main 上的 Top-1/3/5：待正式前向统计完成后生成。
- [同组合配对汇总](../../outputs/visual_track_cosine_20260928/paired_summary.csv)
- 各分项指标的层级相关性：待正式前向统计完成后生成。
- [服务器已有文件查找证据](../../outputs/visual_track_cosine_20260928/remote_source_audit.json)
- [补算作业状态](../../outputs/visual_track_cosine_20260928/status.json)

运行 `python scripts/visual_track_remote_20260928.py fetch` 同步完成组合，再运行 `python scripts/analyze_visual_track_cosine_20260928.py` 更新本报告。
