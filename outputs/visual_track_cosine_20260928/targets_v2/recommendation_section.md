<!-- VISUAL_TRACK_RESULTS_START -->
<a id="visual-track-three-variants"></a>

## 8. 视觉表征余弦三版本（VisualTrack-Cos；本阶段不做，仅留档）

**当前状态（2026-09-29，用户决定）：本阶段不做本方法。** none、alt、model_pred 三版的已有定位统计、候选层和历史比较保留追溯；不再为本方法补算、补训或补评测，不纳入当前公式筛选和候选补跑并集。此前 9 层、15 层峰顶及 75 层峰值区间等补跑方案不执行；后续工作集中于第七类 V01–V10 与前六类方法的比较。下方“完成时间”仅指历史定位统计完成，不表示已完成全部候选层编辑评测或仍需继续本方法。

**完成时间：2026-09-29T08:37:52+0800；服务器核验时间：2026-09-29T09:18:13.102942+08:00。** 7 个模型 × 3 个数据集均已完成，每组含 none、alt、model_pred 三版，共 63 份定位统计；各自报告 Raw / Tukey，共 126 份主推荐。

VisualTrack-Cos-none：视觉 token 平均表征与最后提示词位置的余弦。VisualTrack-Cos-alt / VisualTrack-Cos-model_pred：固定同一图像与提示词前缀，追加对应答案，对完整答案的有效预测位置先取余弦均值，再对样本等权平均。预测 yₜ 的位置是 P−1+t；不使用读入 yₜ 后的位置代替。单个普通答案 token 时可退化为 none。model_pred 使用冻结历史缓存的全部可用文本，不补写被历史生成长度截断的内容。

这是表征余弦方法，与梯度方向余弦、LGA 梯度内积及 VisEdit 贡献度分别报告。主表复用历史视觉梯度有效样本 ID（matched_gradient）；available_train 单列于机器文件。Raw 按有符号余弦降序，Tukey 按每组每版全部有限层分数、κ=1、linear 四分位一次过滤；同分取浅层。表中首层为 Top-1 推荐层，最高层分数不等于最高编辑效果。

### 8.1 evqa-pilot500

| 模型 | 版本 | 有效样本 | Raw Top-3 | Raw Top-5 | Tukey Top-3 | Tukey Top-5 | Tukey 剔除层 |
|---|---|---|---|---|---|---|---|
| BLIP2 | none | 465/500 | L8, L5, L6 | L8, L5, L6, L7, L3 | L8, L5, L6 | L8, L5, L6, L7, L3 | — |
| BLIP2 | alt | 465/500 | L5, L3, L6 | L5, L3, L6, L4, L7 | L5, L3, L6 | L5, L3, L6, L4, L7 | — |
| BLIP2 | model_pred | 465/500 | L5, L3, L6 | L5, L3, L6, L4, L7 | L5, L3, L6 | L5, L3, L6, L4, L7 | — |
| InstructBLIP | none | 500/500 | L22, L24, L23 | L22, L24, L23, L27, L26 | L22, L24, L23 | L22, L24, L23, L27, L26 | L0, L1, L2, L3, L30, L31 |
| InstructBLIP | alt | 500/500 | L5, L4, L6 | L5, L4, L6, L14, L22 | L5, L4, L6 | L5, L4, L6, L14, L22 | L0, L1, L2, L30, L31 |
| InstructBLIP | model_pred | 500/500 | L5, L4, L6 | L5, L4, L6, L22, L14 | L5, L4, L6 | L5, L4, L6, L22, L14 | L0, L1, L2, L3, L30, L31 |
| MiniGPT4 | none | 499/500 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| MiniGPT4 | alt | 499/500 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| MiniGPT4 | model_pred | 499/500 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| LLaVA | none | 500/500 | L31, L29, L28 | L31, L29, L28, L30, L27 | L31, L29, L28 | L31, L29, L28, L30, L27 | — |
| LLaVA | alt | 500/500 | L31, L29, L28 | L31, L29, L28, L30, L27 | L31, L29, L28 | L31, L29, L28, L30, L27 | — |
| LLaVA | model_pred | 500/500 | L31, L29, L28 | L31, L29, L28, L30, L27 | L31, L29, L28 | L31, L29, L28, L30, L27 | — |
| Qwen2.5-VL | none | 500/500 | L34, L33, L32 | L34, L33, L32, L31, L30 | L33, L32, L31 | L33, L32, L31, L30, L29 | L0, L34 |
| Qwen2.5-VL | alt | 500/500 | L34, L33, L32 | L34, L33, L32, L31, L30 | L33, L32, L31 | L33, L32, L31, L30, L29 | L0, L34 |
| Qwen2.5-VL | model_pred | 500/500 | L34, L33, L32 | L34, L33, L32, L31, L30 | L31, L30, L29 | L31, L30, L29, L28, L27 | L0, L32, L33, L34 |
| PaliGemma | none | 500/500 | L2, L1, L3 | L2, L1, L3, L16, L4 | L2, L1, L3 | L2, L1, L3, L16, L4 | — |
| PaliGemma | alt | 500/500 | L2, L1, L3 | L2, L1, L3, L16, L17 | L2, L1, L3 | L2, L1, L3, L16, L17 | — |
| PaliGemma | model_pred | 500/500 | L2, L1, L3 | L2, L1, L3, L16, L17 | L2, L1, L3 | L2, L1, L3, L16, L17 | — |
| SmolVLM | none | 500/500 | L22, L21, L20 | L22, L21, L20, L19, L17 | L20, L19, L17 | L20, L19, L17, L18, L3 | L21, L22 |
| SmolVLM | alt | 500/500 | L22, L21, L19 | L22, L21, L19, L20, L17 | L19, L20, L17 | L19, L20, L17, L18, L5 | L0, L21, L22 |
| SmolVLM | model_pred | 500/500 | L22, L21, L20 | L22, L21, L20, L19, L17 | L17, L18, L16 | L17, L18, L16, L5, L8 | L0, L19, L20, L21, L22 |

### 8.2 mmke-visual

| 模型 | 版本 | 有效样本 | Raw Top-3 | Raw Top-5 | Tukey Top-3 | Tukey Top-5 | Tukey 剔除层 |
|---|---|---|---|---|---|---|---|
| BLIP2 | none | 175/214 | L8, L6, L7 | L8, L6, L7, L5, L9 | L8, L6, L7 | L8, L6, L7, L5, L9 | — |
| BLIP2 | alt | 175/214 | L3, L5, L4 | L3, L5, L4, L6, L2 | L3, L5, L4 | L3, L5, L4, L6, L2 | — |
| BLIP2 | model_pred | 175/214 | L5, L3, L6 | L5, L3, L6, L4, L7 | L5, L3, L6 | L5, L3, L6, L4, L7 | — |
| InstructBLIP | none | 214/214 | L4, L14, L5 | L4, L14, L5, L6, L8 | L4, L14, L5 | L4, L14, L5, L6, L8 | L0, L1, L30, L31 |
| InstructBLIP | alt | 214/214 | L14, L10, L8 | L14, L10, L8, L13, L12 | L14, L10, L8 | L14, L10, L8, L13, L12 | L0, L1, L30, L31 |
| InstructBLIP | model_pred | 214/214 | L14, L4, L5 | L14, L4, L5, L6, L8 | L14, L4, L5 | L14, L4, L5, L6, L8 | L0, L1, L30, L31 |
| MiniGPT4 | none | 214/214 | L29, L28, L27 | L29, L28, L27, L30, L26 | L29, L28, L27 | L29, L28, L27, L30, L26 | — |
| MiniGPT4 | alt | 214/214 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| MiniGPT4 | model_pred | 214/214 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| LLaVA | none | 214/214 | L31, L29, L28 | L31, L29, L28, L26, L27 | L31, L29, L28 | L31, L29, L28, L26, L27 | — |
| LLaVA | alt | 214/214 | L31, L29, L30 | L31, L29, L30, L28, L27 | L29, L30, L28 | L29, L30, L28, L27, L26 | L31 |
| LLaVA | model_pred | 214/214 | L31, L29, L28 | L31, L29, L28, L30, L26 | L31, L29, L28 | L31, L29, L28, L30, L26 | — |
| Qwen2.5-VL | none | 214/214 | L34, L33, L32 | L34, L33, L32, L31, L30 | L34, L33, L32 | L34, L33, L32, L31, L30 | L0 |
| Qwen2.5-VL | alt | 214/214 | L34, L33, L32 | L34, L33, L32, L31, L30 | L32, L31, L30 | L32, L31, L30, L29, L28 | L0, L33, L34 |
| Qwen2.5-VL | model_pred | 214/214 | L34, L33, L32 | L34, L33, L32, L31, L30 | L33, L32, L31 | L33, L32, L31, L30, L28 | L0, L34 |
| PaliGemma | none | 214/214 | L2, L1, L3 | L2, L1, L3, L4, L5 | L2, L1, L3 | L2, L1, L3, L4, L5 | — |
| PaliGemma | alt | 214/214 | L2, L3, L17 | L2, L3, L17, L4, L1 | L2, L3, L17 | L2, L3, L17, L4, L1 | — |
| PaliGemma | model_pred | 214/214 | L2, L3, L1 | L2, L3, L1, L4, L5 | L2, L3, L1 | L2, L3, L1, L4, L5 | — |
| SmolVLM | none | 214/214 | L22, L21, L20 | L22, L21, L20, L19, L17 | L22, L21, L20 | L22, L21, L20, L19, L17 | — |
| SmolVLM | alt | 214/214 | L22, L21, L20 | L22, L21, L20, L19, L8 | L20, L19, L8 | L20, L19, L8, L5, L18 | L0, L21, L22 |
| SmolVLM | model_pred | 214/214 | L22, L21, L20 | L22, L21, L20, L19, L17 | L20, L19, L17 | L20, L19, L17, L18, L16 | L0, L21, L22 |

### 8.3 mmke-entity

| 模型 | 版本 | 有效样本 | Raw Top-3 | Raw Top-5 | Tukey Top-3 | Tukey Top-5 | Tukey 剔除层 |
|---|---|---|---|---|---|---|---|
| BLIP2 | none | 284/636（低覆盖） | L8, L7, L6 | L8, L7, L6, L5, L9 | L8, L7, L6 | L8, L7, L6, L5, L9 | — |
| BLIP2 | alt | 284/636（低覆盖） | L3, L2, L4 | L3, L2, L4, L5, L6 | L3, L2, L4 | L3, L2, L4, L5, L6 | — |
| BLIP2 | model_pred | 284/636（低覆盖） | L3, L5, L4 | L3, L5, L4, L6, L2 | L3, L5, L4 | L3, L5, L4, L6, L2 | — |
| InstructBLIP | none | 636/636 | L4, L5, L14 | L4, L5, L14, L6, L8 | L4, L5, L14 | L4, L5, L14, L6, L8 | L0, L1, L30, L31 |
| InstructBLIP | alt | 636/636 | L8, L10, L4 | L8, L10, L4, L14, L6 | L8, L10, L4 | L8, L10, L4, L14, L6 | L0, L1, L30, L31 |
| InstructBLIP | model_pred | 636/636 | L4, L5, L14 | L4, L5, L14, L6, L8 | L4, L5, L14 | L4, L5, L14, L6, L8 | L0, L1, L30, L31 |
| MiniGPT4 | none | 636/636 | L29, L28, L27 | L29, L28, L27, L30, L26 | L29, L28, L27 | L29, L28, L27, L30, L26 | — |
| MiniGPT4 | alt | 636/636 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| MiniGPT4 | model_pred | 636/636 | L29, L28, L30 | L29, L28, L30, L27, L26 | L29, L28, L30 | L29, L28, L30, L27, L26 | — |
| LLaVA | none | 636/636 | L29, L28, L31 | L29, L28, L31, L27, L26 | L29, L28, L31 | L29, L28, L31, L27, L26 | — |
| LLaVA | alt | 636/636 | L31, L29, L30 | L31, L29, L30, L28, L27 | L28, L27, L26 | L28, L27, L26, L25, L24 | L29, L30, L31 |
| LLaVA | model_pred | 636/636 | L31, L29, L28 | L31, L29, L28, L30, L27 | L31, L29, L28 | L31, L29, L28, L30, L27 | — |
| Qwen2.5-VL | none | 636/636 | L34, L31, L32 | L34, L31, L32, L33, L30 | L34, L31, L32 | L34, L31, L32, L33, L30 | L0 |
| Qwen2.5-VL | alt | 636/636 | L34, L33, L32 | L34, L33, L32, L31, L30 | L32, L31, L30 | L32, L31, L30, L29, L28 | L0, L33, L34 |
| Qwen2.5-VL | model_pred | 636/636 | L34, L33, L32 | L34, L33, L32, L31, L30 | L33, L32, L31 | L33, L32, L31, L30, L29 | L0, L34 |
| PaliGemma | none | 636/636 | L2, L1, L3 | L2, L1, L3, L4, L16 | L2, L1, L3 | L2, L1, L3, L4, L16 | — |
| PaliGemma | alt | 636/636 | L3, L2, L4 | L3, L2, L4, L5, L1 | L3, L2, L4 | L3, L2, L4, L5, L1 | L0, L15 |
| PaliGemma | model_pred | 636/636 | L2, L3, L1 | L2, L3, L1, L4, L16 | L2, L3, L1 | L2, L3, L1, L4, L16 | — |
| SmolVLM | none | 636/636 | L22, L21, L19 | L22, L21, L19, L20, L18 | L22, L21, L19 | L22, L21, L19, L20, L18 | — |
| SmolVLM | alt | 636/636 | L22, L21, L20 | L22, L21, L20, L8, L19 | L21, L20, L8 | L21, L20, L8, L19, L6 | L0, L22 |
| SmolVLM | model_pred | 636/636 | L22, L21, L20 | L22, L21, L20, L19, L18 | L20, L19, L18 | L20, L19, L18, L17, L8 | L0, L21, L22 |

### 8.4 已有真实编辑结果上的三版共同组合比较

编辑性能配对固定使用 **2026-09-28T11:10:16+08:00** 的扫层快照，396 条 main；36 条 stable 与 1 条 main-rerun 不代填或择优替换。此处未添加任何新训练结果。Top-1 是第一推荐层的 Average；Best@3、Mean@3 分别为完整三候选层的最大值、均值。缺任一候选的 main 评测就不计算完整 Best/Mean@3。以下三版汇总固定使用同一批三方 Top-3 都有评测且定位覆盖率 ≥80% 的组合；Raw 与 Tukey 的共同组合可能不同，不能直接把跨表均值差当作过滤收益。

| 版本 | 排序 | 三版共同可比组数 | Top-1 | Best@3 | Mean@3 |
|---|---|---|---|---|---|
| none | raw | 4 | 69.169 | 72.221 | 63.201 |
| alt | raw | 4 | 71.901 | 73.052 | 63.854 |
| model_pred | raw | 4 | 69.169 | 72.221 | 63.201 |
| none | tukey | 3 | 73.601 | 77.245 | 65.447 |
| alt | tukey | 3 | 77.245 | 78.300 | 66.300 |
| model_pred | tukey | 3 | 73.601 | 77.245 | 65.447 |

逐组合性能、缺失评测层及与既有公式的配对结果见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)。

[全部推荐与全层排序](../../outputs/visual_track_cosine_20260928/targets_v2/recommendations.json) · [逐组合性能](../../outputs/visual_track_cosine_20260928/targets_v2/performance.csv) · [各分项指标 Spearman](../../outputs/visual_track_cosine_20260928/targets_v2/correlations.csv) · [Tukey 阈值与剔除层](../../outputs/visual_track_cosine_20260928/targets_v2/recommendations.csv) · [完成及恢复训练回执](../../outputs/visual_track_cosine_20260928/targets_v2/completion_receipt.json)
<!-- VISUAL_TRACK_RESULTS_END -->
