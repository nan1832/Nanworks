# 视觉表征相似度三版峰值验证：缺层清单与补跑建议

**状态更新（2026-09-29，用户决定）：本阶段不做视觉表征相似性方法，下述 9 层、15 层、75/83 层补跑建议均不执行，仅保留历史分析。当前目标改为从第七类梯度归因 V01–V10 中筛选优于前六类方法的公式，详见 [推荐层手册第 0 节](ALL_Methods_Recommends_layers.md)。**

依据 SWeeplayers.md 链接的2026-09-28 11:10:16台账；当前该本地文件与上一轮分析时的SHA-256一致。排除所有PaliGemma，仅比较main配方。本次核对本地结果，没有实时查询服务器，因此“缺层”表示此台账没有有效评测记录，不表示服务器肯定未训练。

缺的是这些层的真实adapter编辑训练/评测结果。none、alt、model_pred三版逐层相似度已有，无须为此重新计算表征。相同数据集、模型、层的一次有效main训练/评测可以服务三版，不需要每版重复训练。

## 1. 全局0.90峰值区间：共75个缺失评测单元

区间沿用前次定义：在全层曲线上min-max归一化后，取包含全局最高峰且数值不低于0.90的连续区间。它是探索性分析规则，不是已证明有效或论文强制要求的选层规则。以下为三版缺层的并集；一个单元为数据集×模型×层，层号从0开始。

| 模型 | E-VQA | MMKE-visual | MMKE-entity |
|---|---|---|---|
| BLIP2 | L6–L9、L11–L12 | L5–L12 | L5–L12 |
| InstructBLIP | L5–L10、L12–L13、L17、L20–L24、L29 | L6–L13、L21 | L6–L13、L21 |
| MiniGPT4 | L27 | L30 | L29–L30 |
| LLaVA | 无 | L31 | L29–L31 |
| Qwen2.5-VL | L33 | L31–L34 | L31–L34 |
| SmolVLM | 无 | L22 | L21–L22 |

按数据集分别缺23、24、28个；按版本分别缺75、60、66个，重叠去重后75个。三版目前均完整的共同组合仅有LLaVA×E-VQA、SmolVLM×E-VQA。BLIP2和InstructBLIP合计占55个缺层，主要由于相似度高值平台宽，部分区间接近大半个模型。

## 2. 是否必要

仅报告已有扫层上的相关性：不需要为了补齐区间而新增75次训练。可以准确报告“在已测层上缺少稳定的Rel/Gen正相关、部分组合呈强负相关”，同时保留未测峰区的不确定性。

若将选峰作为论文中的正式定位对照：值得做一个固定规则、固定评测口径的补充实验。优先考虑下一节15个峰顶缺层，可覆盖全部6模型×3数据集的三版Top-1；这比直接填满75个宽区间更贴近“相似度最高处是否编辑更好”的问题。它回答峰顶Top-1问题，不会自动证明整个峰值区间或Top-3有效。

## 3. 建议的跨模型峰顶验证：15个单元

只取每版全局相似度最高层，规则和候选层在新评测前已冻结，不按编辑结果调整。下表是尚无台账评测的峰顶并集。

| 模型 | E-VQA | MMKE-visual | MMKE-entity |
|---|---|---|---|
| BLIP2 | L8 | L5、L8 | L8 |
| InstructBLIP | L5、L22 | 无 | L8 |
| MiniGPT4 | 无 | 无 | L29 |
| LLaVA | 无 | L31 | L29、L31 |
| Qwen2.5-VL | 无 | L34 | L34 |
| SmolVLM | 无 | L22 | L22 |

共15个：E-VQA 3个、MMKE-visual 5个、MMKE-entity 7个。补齐后，三版Top-1由当前7/9/9个有结果的组合，变为同一批18/18/18个组合，可逐项比较Rel、T-Gen、M-Gen、T-Loc、M-Loc及Average。保留原有main训练配置、训练预算、checkpoint选择和独立评测口径；三版相似度复用，一层只训练/评测一次。

这一补充没有选择已知会赢的层，但仍属于基于现有探索的后续验证，不能包装成预先独立设计的确认性实验。候选分数的样本覆盖差异沿用上一轮报告；BLIP2×MMKE-entity尤其要同时报告284/636与可用全集alt结果。

## 4. 若预算只够先补全若干区间：9个单元

这套备选方案按“补齐一个组合所需缺层数”选择，与编辑分数高低无关。能够新增7个三版均完整的组合，连同已完整的2组，使三版在相同9个组合上比较0.90区间。

| 数据集 | 模型 | 补层 |
|---|---|---|
| evqa-pilot500 | MiniGPT4 | L27 |
| evqa-pilot500 | Qwen2.5-VL | L33 |
| mmke-visual | MiniGPT4 | L30 |
| mmke-visual | LLaVA | L31 |
| mmke-visual | SmolVLM | L22 |
| mmke-entity | MiniGPT4 | L29–L30 |
| mmke-entity | SmolVLM | L21–L22 |

该9层方案覆盖MiniGPT4、LLaVA、Qwen、SmolVLM四类模型，没有补齐BLIP2/InstructBLIP，因此不适合据此宣称六模型普适结论。15峰顶方案与9区间方案回答不同问题，不能混用完成率。

## 5. 内部局部峰前后各一层：42个缺失单元

以下为最高内部局部峰±1的缺层并集，不采用上面的0.90区间定义。

| 模型 | E-VQA | MMKE-visual | MMKE-entity |
|---|---|---|---|
| BLIP2 | L6–L9 | L5–L9 | L7–L9 |
| InstructBLIP | L5–L6、L21–L23 | L13 | L7–L9 |
| MiniGPT4 | 无 | L30 | L29–L30 |
| LLaVA | L29 | L29–L30 | L29–L30 |
| Qwen2.5-VL | L33 | L33–L35 | L33–L35 |
| SmolVLM | L23 | L22–L23 | L21–L23 |

若要同时补齐0.90区间和内部峰±1，合计83个单元，包含75个全局区间缺层和8个额外邻层；不是75+42次独立训练。这8个额外邻层为：E-VQA×LLaVA L29、E-VQA×SmolVLM L23；MMKE-visual×LLaVA L29/L30、Qwen L35、SmolVLM L23；MMKE-entity×Qwen L35、SmolVLM L23。

## 6. 执行前的实际缺口核对

先查上述拟补层是否已有服务器训练结果或有效selected checkpoint但未回填：已有完整评测就同步；只有有效checkpoint就按原协议评测；确无可复用结果时才补训练。当前文档是补跑建议，没有提交服务器任务。

[逐版本缺层CSV](../../outputs/visual_track_metric_audit_20260929/missing_layer_plan/missing_layers_by_variant.csv) · [机器可读清单与计数校验](../../outputs/visual_track_metric_audit_20260929/missing_layer_plan/plan.json) · [上一轮相关性与峰区分析](VisualTrackCos_三版本_分指标相关性分析_排除PaliGemma_20260929.md)
