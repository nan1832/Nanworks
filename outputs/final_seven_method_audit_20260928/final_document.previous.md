# 最终七类定位方法：已有 Top-3 推荐层与缺项

<!-- FINAL_SEVEN_METHODS_VERIFIED_SNAPSHOT -->

**整理时间：2026-09-28T22:07:59+08:00（本机北京时间）。** 本表依据已核验快照回填，方法顺序遵从最终截图：中层、CMA-model_pred、VisEdit-model_pred、SaLEM-alt、参数 LGA、Perturb-KL-alt、第七类猜想。

定位基线来源快照：2026-09-28T16:00:41+08:00；梯度/VisEdit 本地派生快照：2026-09-28T21:52:30.105901+08:00；服务器梯度等待状态：2026-09-28T21:56:58.400094+08:00；绿色相似度完成产物采集：2026-09-28T21:58:41.648858+08:00。本表不将这些有时间戳的状态称为持续实时进度。

## 0. 统一口径与完成概览

- 层号从 L0 开始；候选 L_l 表示 adapter 接在 decoder block l 输出之后。Top-3 保留推荐顺序。
- alt 为新目标；model_pred 为模型响应；数据集 pred 字段单独区分。此表没有用 VisEdit-alt 或历史 pred 来填充最终要求的 model_pred。
- 第七类仍在比较候选公式，没有预先确定唯一最优公式。A=先分别平均再相乘，B=逐样本计算后平均。
- 参数 LGA 与五类视觉梯度公式按全层 Tukey 排名：Q1−IQR 至 Q3+IQR，κ=1，linear 四分位数，一次过滤，边界保留，同分取浅层，不按真实编辑效果决定剔除层。
- † 表示已有原始记录标记的零视觉梯度层。当前全层协议保留有限零分；零分排在负分之前不代表存在有效方向证据。
- Mean@3 为三个推荐层各自真实编辑后 Average 的算术平均；三层缺任一层则记“未齐”，不取已完成层的均值、不用 Best@3 替代。Average 延用热力图的五项指标均值。
- 实测覆盖冻结为已同步的 396 条 main 记录；包含已记录的未收敛/恢复等运行标签，不按表现筛除。stable 和独立复测不择优补 main；“实测齐”也不等于所有训练预算已一致验收。

| 最终方法 / 版本 | 已有 Top-3 | 三个推荐层 main 实测已齐 |
| --- | --- | --- |
| 1. 中层先验 | 21/21 | 21/21 |
| 2. CMA-model_pred | 21/21 | 20/21 |
| 3. VisEdit-model_pred / attn | 7/21 | 贡献 Top-3 4/21；Pre 4/21 |
| 3. VisEdit-model_pred / mlp | 7/21 | 贡献 Top-3 2/21；Pre 5/21 |
| 3. VisEdit-model_pred / attn+mlp | 7/21 | 贡献 Top-3 3/21；Pre 4/21 |
| 4. SaLEM-alt | 21/21 | 21/21 |
| 5. LGA 参数梯度：Tukey | 21/21 | 18/21 |
| 6. Perturb-KL-alt | 21/21 | 20/21 |
| 7. 梯度 F1-A | 21/21 | 9/21 |
| 7. 梯度 F1-B | 21/21 | 8/21 |
| 7. 梯度 F2-A | 21/21 | 11/21 |
| 7. 梯度 F2-B | 0/21 | 0/21 |
| 7. 梯度 F3-A | 21/21 | 14/21 |
| 7. 梯度 F3-B | 0/21 | 0/21 |
| 7. 梯度 F4-A | 21/21 | 19/21 |
| 7. 梯度 F4-B | 0/21 | 0/21 |
| 7. 梯度 F5-A | 21/21 | 14/21 |
| 7. 梯度 F5-B | 21/21 | 14/21 |
| 7. 相似度 none | 9/21 | 降序 Raw 2/21；Tukey 2/21 |
| 7. 相似度 alt | 9/21 | 降序 Raw 1/21；Tukey 2/21 |
| 7. 相似度 model_pred | 9/21 | 降序 Raw 2/21；Tukey 2/21 |
| 7. 不分新旧相似度：极大值区间中层 | 0/21 | 选层规则尚未实现 |

目录：[1 中层](#1-中层先验) · [2 CMA](#2-cma-model_pred) · [3 VisEdit](#3-visedit-model_pred三类贡献及前置候选) · [4 SaLEM](#4-salem-alt) · [5 LGA](#5-lga模型参数梯度tukey) · [6 Perturb-KL](#6-perturb-kl-alt) · [7 猜想](#7-我们的猜想视觉梯度与表征相似度)

## 1. 中层先验

中心为 (L−1)/2；按距离升序，同距离取较浅层。同模型三个数据集推荐相同；下表分别对接各数据集实测。

| 数据集 | 模型 | Top-3 | 定位有效样本 | Mean@3 (%) | 缺 main 层 |
| --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L15, L16, L14 | 结构先验 | 74.009 | — |
| EVQA | InstructBLIP | L15, L16, L14 | 结构先验 | 49.757 | — |
| EVQA | MiniGPT-4 | L15, L16, L14 | 结构先验 | 64.147 | — |
| EVQA | LLaVA-1.5 | L15, L16, L14 | 结构先验 | 61.715 | — |
| EVQA | Qwen2.5-VL | L17, L18, L16 | 结构先验 | 62.971 | — |
| EVQA | PaliGemma | L8, L9, L7 | 结构先验 | 64.269 | — |
| EVQA | SmolVLM | L11, L12, L10 | 结构先验 | 66.326 | — |
| MMKE-Visual | BLIP2 | L15, L16, L14 | 结构先验 | 70.809 | — |
| MMKE-Visual | InstructBLIP | L15, L16, L14 | 结构先验 | 50.189 | — |
| MMKE-Visual | MiniGPT-4 | L15, L16, L14 | 结构先验 | 76.105 | — |
| MMKE-Visual | LLaVA-1.5 | L15, L16, L14 | 结构先验 | 76.002 | — |
| MMKE-Visual | Qwen2.5-VL | L17, L18, L16 | 结构先验 | 70.020 | — |
| MMKE-Visual | PaliGemma | L8, L9, L7 | 结构先验 | 94.264 | — |
| MMKE-Visual | SmolVLM | L11, L12, L10 | 结构先验 | 69.159 | — |
| MMKE-Entity | BLIP2 | L15, L16, L14 | 结构先验 | 69.766 | — |
| MMKE-Entity | InstructBLIP | L15, L16, L14 | 结构先验 | 48.734 | — |
| MMKE-Entity | MiniGPT-4 | L15, L16, L14 | 结构先验 | 75.932 | — |
| MMKE-Entity | LLaVA-1.5 | L15, L16, L14 | 结构先验 | 75.927 | — |
| MMKE-Entity | Qwen2.5-VL | L17, L18, L16 | 结构先验 | 71.423 | — |
| MMKE-Entity | PaliGemma | L8, L9, L7 | 结构先验 | 90.610 | — |
| MMKE-Entity | SmolVLM | L11, L12, L10 | 结构先验 | 70.337 | — |

## 2. CMA-model_pred

在视觉污染输入中逐层恢复正常视觉状态，按对完整 model_pred 答案平均对数概率的相对恢复量排序。目标是模型当前响应，不是 alt。当前采用 α={0.5,1,2}×seed={0,1,2}。有推荐不代表全样本都通过内部恢复有效性过滤。

| 数据集 | 模型 | Top-3 | 定位有效样本 | Mean@3 (%) | 缺 main 层 |
| --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L2, L1, L0 | 465/500 | 55.599 | — |
| EVQA | InstructBLIP | L1, L0, L2 | 496/500 | 52.225 | — |
| EVQA | MiniGPT-4 | L0, L1, L2 | 497/500 | 64.143 | — |
| EVQA | LLaVA-1.5 | L0, L1, L2 | 500/500 | 62.641 | — |
| EVQA | Qwen2.5-VL | L1, L0, L15 | 354/500 | 62.249 | — |
| EVQA | PaliGemma | L5, L4, L7 | 410/500 | 74.983 | — |
| EVQA | SmolVLM | L0, L1, L5 | 497/500 | 64.701 | — |
| MMKE-Visual | BLIP2 | L2, L0, L3 | 175/214 | 66.993 | — |
| MMKE-Visual | InstructBLIP | L1, L25, L22 | 214/214 | 56.915 | — |
| MMKE-Visual | MiniGPT-4 | L0, L1, L2 | 214/214 | 75.900 | — |
| MMKE-Visual | LLaVA-1.5 | L0, L1, L2 | 214/214 | 75.861 | — |
| MMKE-Visual | Qwen2.5-VL | L1, L0, L2 | 154/214 | 69.943 | — |
| MMKE-Visual | PaliGemma | L7, L6, L4 | 166/214 | 95.975 | — |
| MMKE-Visual | SmolVLM | L1, L0, L5 | 213/214 | 70.621 | — |
| MMKE-Entity | BLIP2 | L2, L3, L1 | 284/636 | 71.613 | — |
| MMKE-Entity | InstructBLIP | L26, L25, L22 | 627/636 | 47.743 | — |
| MMKE-Entity | MiniGPT-4 | L0, L1, L2 | 636/636 | 75.349 | — |
| MMKE-Entity | LLaVA-1.5 | L0, L1, L4 | 636/636 | 未齐 | L0, L1, L4 |
| MMKE-Entity | Qwen2.5-VL | L1, L0, L20 | 360/636 | 71.903 | — |
| MMKE-Entity | PaliGemma | L7, L6, L5 | 559/636 | 92.637 | — |
| MMKE-Entity | SmolVLM | L0, L1, L2 | 631/636 | 70.880 | — |

排名稳定性提示：EVQA / Qwen2.5-VL：candidate_ranking_unstable；EVQA / SmolVLM：candidate_ranking_unstable；MMKE-Visual / PaliGemma：candidate_ranking_unstable；MMKE-Visual / SmolVLM：candidate_ranking_unstable。

## 3. VisEdit-model_pred：三类贡献及前置候选

原始模块贡献分别保存 attention、MLP，以及合并曲线。贡献度排序是归因依据；Pre 是仿照 VisEdit 在高贡献区之前插入 adapter 的基线。两种列表分列，不把贡献最高层直接称为原文选定编辑层。

已有 EVQA 七组的 model_pred 是模型下一 token argmax 目标。MMKE 两个数据集共十四组尚缺真正 model_pred 原始贡献；alt、历史数据集 pred 不换名填充。

当前用于推荐的正贡献：attn=max(0,attn_mean)，mlp=max(0,mlp_mean)，合并为二者之和。Pre 对各自曲线使用三层滑动均值，阈值 mean+0.5×std，选择最长高贡献连续区；等长取贡献和更大者，再取更浅者。区间从 s 开始时取 s−1、s−2、s−3，不足三层不回填。此自动规则为项目基线。

### 3.1 三类贡献 Top-3 与 Pre Top-3

**EVQA**

| 模型 | attn 贡献 | attn Pre | mlp 贡献 | mlp Pre | attn+mlp 贡献 | attn+mlp Pre |
| --- | --- | --- | --- | --- | --- | --- |
| BLIP2 | L29, L22, L26 | L20, L19, L18 | L25, L26, L24 | L21, L20, L19 | L26, L25, L27 | L21, L20, L19 |
| InstructBLIP | L18, L23, L20 | L16, L15, L14 | L30, L20, L23 | L18, L17, L16 | L30, L20, L23 | L17, L16, L15 |
| MiniGPT-4 | L26, L25, L31 | L24, L23, L22 | L30, L20, L27 | L27, L26, L25 | L26, L30, L25 | L24, L23, L22 |
| LLaVA-1.5 | L28, L30, L24 | L26, L25, L24 | L30, L28, L29 | L26, L25, L24 | L28, L30, L27 | L26, L25, L24 |
| Qwen2.5-VL | L34, L26, L35 | L32, L31, L30 | L31, L30, L34 | L28, L27, L26 | L31, L30, L34 | L28, L27, L26 |
| PaliGemma | L15, L12, L14 | L12, L11, L10 | L13, L16, L17 | L11, L10, L9 | L13, L15, L16 | L11, L10, L9 |
| SmolVLM | L22, L21, L23 | L19, L18, L17 | L16, L18, L17 | L14, L13, L12 | L22, L21, L23 | L18, L17, L16 |

**MMKE-Visual**

| 模型 | attn 贡献 | attn Pre | mlp 贡献 | mlp Pre | attn+mlp 贡献 | attn+mlp Pre |
| --- | --- | --- | --- | --- | --- | --- |
| BLIP2 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| InstructBLIP | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| MiniGPT-4 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| LLaVA-1.5 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| Qwen2.5-VL | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| PaliGemma | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| SmolVLM | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |

**MMKE-Entity**

| 模型 | attn 贡献 | attn Pre | mlp 贡献 | mlp Pre | attn+mlp 贡献 | attn+mlp Pre |
| --- | --- | --- | --- | --- | --- | --- |
| BLIP2 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| InstructBLIP | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| MiniGPT-4 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| LLaVA-1.5 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| Qwen2.5-VL | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| PaliGemma | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| SmolVLM | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |

### 3.2 已有 EVQA 推荐的实测覆盖

| 模型 | 贡献对象 | 贡献 Top-3 Mean@3 | 贡献 Top-3 缺层 | Pre Mean@3 | Pre 缺层 |
| --- | --- | --- | --- | --- | --- |
| BLIP2 | attn | 未齐 | L22 | 73.312 | — |
| BLIP2 | mlp | 63.967 | — | 73.023 | — |
| BLIP2 | attn+mlp | 未齐 | L27 | 73.023 | — |
| InstructBLIP | attn | 未齐 | L23, L20 | 49.757 | — |
| InstructBLIP | mlp | 未齐 | L30, L20, L23 | 未齐 | L17 |
| InstructBLIP | attn+mlp | 未齐 | L30, L20, L23 | 未齐 | L17 |
| MiniGPT-4 | attn | 56.803 | — | 未齐 | L23 |
| MiniGPT-4 | mlp | 未齐 | L20, L27 | 未齐 | L27 |
| MiniGPT-4 | attn+mlp | 57.859 | — | 未齐 | L23 |
| LLaVA-1.5 | attn | 60.171 | — | 62.098 | — |
| LLaVA-1.5 | mlp | 未齐 | L29 | 62.098 | — |
| LLaVA-1.5 | attn+mlp | 60.177 | — | 62.098 | — |
| Qwen2.5-VL | attn | 62.338 | — | 未齐 | L32 |
| Qwen2.5-VL | mlp | 62.781 | — | 62.267 | — |
| Qwen2.5-VL | attn+mlp | 62.781 | — | 62.267 | — |
| PaliGemma | attn | 49.384 | — | 75.831 | — |
| PaliGemma | mlp | 未齐 | L13, L16 | 62.555 | — |
| PaliGemma | attn+mlp | 未齐 | L13, L16 | 62.555 | — |
| SmolVLM | attn | 未齐 | L23 | 未齐 | L18 |
| SmolVLM | mlp | 未齐 | L18 | 63.199 | — |
| SmolVLM | attn+mlp | 未齐 | L23 | 未齐 | L18 |

### 3.3 全层贡献度排序：高到低

下列各行均为 EVQA-model_pred，保留原始有符号排序和用于当前 Pre 的正贡献排序。合并的有符号分数为 attn_mean+mlp_mean；正贡献合并则分别取正部后相加。同分取浅层。MMKE 无原始结果，不能输出全层排序。

**BLIP2**

- **attn**：有符号排序 L29, L22, L26, L27, L25, L15, L28, L30, L20, L24, L23, L16, L11, L8, L5, L18, L31, L21, L0, L9, L12, L14, L10, L13, L19, L17, L2, L6, L4, L7, L1, L3。

  正贡献排序 L29, L22, L26, L27, L25, L15, L28, L30, L20, L24, L23, L16, L11, L8, L5, L18, L31, L21, L0, L9, L12, L14, L10, L13, L19, L17, L2, L6, L4, L7, L1, L3。高贡献区 L21, L30（区间端点），Pre 为 L20, L19, L18。

- **mlp**：有符号排序 L25, L26, L24, L27, L23, L28, L22, L29, L20, L17, L10, L16, L8, L18, L12, L21, L15, L7, L5, L14, L6, L11, L4, L13, L19, L9, L2, L0, L30, L3, L1, L31。

  正贡献排序 L25, L26, L24, L27, L23, L28, L22, L29, L20, L17, L10, L16, L8, L18, L12, L21, L15, L7, L5, L14, L6, L11, L4, L13, L19, L9, L2, L0, L30, L3, L1, L31。高贡献区 L22, L28（区间端点），Pre 为 L21, L20, L19。

- **attn+mlp**：有符号排序 L26, L25, L27, L22, L24, L29, L23, L28, L20, L15, L17, L16, L10, L8, L30, L18, L12, L5, L21, L11, L7, L14, L9, L0, L6, L13, L19, L2, L4, L31, L1, L3。

  正贡献排序 L26, L25, L27, L22, L24, L29, L23, L28, L20, L15, L17, L16, L10, L8, L30, L18, L12, L5, L21, L11, L7, L14, L9, L0, L6, L13, L19, L2, L4, L31, L1, L3。高贡献区 L22, L29（区间端点），Pre 为 L21, L20, L19。

**InstructBLIP**

- **attn**：有符号排序 L18, L23, L20, L28, L21, L19, L26, L24, L30, L25, L17, L16, L15, L14, L3, L13, L22, L12, L4, L2, L10, L31, L29, L5, L9, L11, L27, L7, L1, L8, L0, L6。

  正贡献排序 L18, L23, L20, L28, L21, L19, L26, L24, L30, L25, L17, L16, L15, L14, L3, L13, L22, L12, L4, L2, L10, L31, L29, L5, L9, L11, L27, L7, L1, L8, L0, L6。高贡献区 L17, L25（区间端点），Pre 为 L16, L15, L14。

- **mlp**：有符号排序 L30, L20, L23, L27, L21, L26, L28, L31, L22, L19, L25, L16, L14, L29, L18, L24, L17, L15, L12, L10, L13, L0, L1, L6, L11, L9, L7, L4, L2, L5, L3, L8。

  正贡献排序 L30, L20, L23, L27, L21, L26, L28, L31, L22, L19, L25, L16, L14, L29, L18, L24, L17, L15, L12, L10, L13, L0, L1, L6, L11, L9, L7, L4, L2, L5, L3, L8。高贡献区 L19, L22（区间端点），Pre 为 L18, L17, L16。

- **attn+mlp**：有符号排序 L30, L20, L23, L21, L18, L26, L28, L19, L27, L24, L25, L16, L22, L17, L14, L31, L29, L15, L3, L13, L12, L4, L10, L2, L5, L9, L11, L1, L7, L0, L6, L8。

  正贡献排序 L30, L20, L23, L21, L18, L26, L28, L19, L27, L24, L25, L16, L22, L17, L14, L31, L29, L15, L3, L13, L12, L4, L10, L2, L5, L9, L11, L1, L7, L0, L6, L8。高贡献区 L18, L24（区间端点），Pre 为 L17, L16, L15。

**MiniGPT-4**

- **attn**：有符号排序 L26, L25, L31, L19, L30, L22, L20, L28, L13, L23, L21, L18, L29, L17, L15, L14, L16, L12, L24, L3, L0, L10, L4, L8, L6, L9, L2, L1, L5, L11, L7, L27。

  正贡献排序 L26, L25, L31, L19, L30, L22, L20, L28, L13, L23, L21, L18, L29, L17, L15, L14, L16, L12, L24, L3, L0, L10, L4, L8, L6, L9, L2, L1, L5, L11, L7, L27。高贡献区 L25, L27（区间端点），Pre 为 L24, L23, L22。

- **mlp**：有符号排序 L30, L20, L27, L29, L25, L18, L28, L21, L22, L23, L14, L15, L31, L19, L12, L4, L24, L16, L26, L17, L0, L1, L2, L10, L6, L13, L11, L5, L3, L7, L9, L8。

  正贡献排序 L30, L20, L27, L29, L25, L18, L28, L21, L22, L23, L14, L15, L31, L19, L12, L4, L24, L16, L26, L17, L0, L1, L2, L10, L6, L13, L11, L5, L3, L7, L9, L8。高贡献区 L28, L31（区间端点），Pre 为 L27, L26, L25。

- **attn+mlp**：有符号排序 L26, L30, L25, L20, L31, L19, L22, L28, L29, L18, L21, L23, L27, L13, L15, L14, L17, L12, L16, L24, L4, L0, L3, L10, L1, L2, L6, L8, L9, L5, L11, L7。

  正贡献排序 L26, L30, L25, L20, L31, L19, L22, L28, L29, L18, L21, L23, L27, L13, L15, L14, L17, L12, L16, L24, L4, L0, L3, L10, L1, L2, L6, L8, L9, L5, L11, L7。高贡献区 L25, L27（区间端点），Pre 为 L24, L23, L22。

**LLaVA-1.5**

- **attn**：有符号排序 L28, L30, L24, L31, L27, L19, L22, L16, L20, L26, L21, L25, L29, L18, L23, L17, L9, L13, L14, L15, L6, L1, L7, L12, L11, L10, L3, L8, L4, L0, L2, L5。

  正贡献排序 L28, L30, L24, L31, L27, L19, L22, L16, L20, L26, L21, L25, L29, L18, L23, L17, L9, L13, L14, L15, L6, L1, L7, L12, L11, L10, L3, L8, L4, L0, L2, L5。高贡献区 L27, L31（区间端点），Pre 为 L26, L25, L24。

- **mlp**：有符号排序 L30, L28, L29, L27, L31, L26, L17, L20, L22, L18, L24, L21, L23, L25, L15, L19, L16, L7, L10, L13, L4, L2, L14, L6, L12, L8, L5, L9, L1, L3, L11, L0。

  正贡献排序 L30, L28, L29, L27, L31, L26, L17, L20, L22, L18, L24, L21, L23, L25, L15, L19, L16, L7, L10, L13, L4, L2, L14, L6, L12, L8, L5, L9, L1, L3, L11, L0。高贡献区 L27, L31（区间端点），Pre 为 L26, L25, L24。

- **attn+mlp**：有符号排序 L28, L30, L27, L31, L29, L24, L26, L20, L22, L19, L21, L17, L16, L25, L18, L23, L15, L13, L9, L7, L14, L6, L10, L4, L12, L1, L8, L11, L2, L3, L5, L0。

  正贡献排序 L28, L30, L27, L31, L29, L24, L26, L20, L22, L19, L21, L17, L16, L25, L18, L23, L15, L13, L9, L7, L14, L6, L10, L4, L12, L1, L8, L11, L2, L3, L5, L0。高贡献区 L27, L31（区间端点），Pre 为 L26, L25, L24。

**Qwen2.5-VL**

- **attn**：有符号排序 L34, L26, L35, L29, L30, L33, L32, L31, L10, L28, L19, L24, L8, L6, L27, L16, L2, L5, L15, L22, L14, L21, L9, L13, L25, L18, L3, L20, L17, L7, L23, L1, L4, L0, L12, L11。

  正贡献排序 L34, L26, L35, L29, L30, L33, L32, L31, L10, L28, L19, L24, L8, L6, L27, L16, L2, L5, L15, L22, L14, L21, L9, L13, L25, L18, L3, L20, L17, L7, L23, L1, L4, L0, L11, L12。高贡献区 L33, L35（区间端点），Pre 为 L32, L31, L30。

- **mlp**：有符号排序 L31, L30, L34, L32, L33, L29, L27, L26, L28, L25, L35, L23, L16, L11, L5, L24, L17, L12, L3, L4, L14, L10, L8, L22, L9, L21, L18, L6, L7, L1, L2, L13, L19, L20, L15, L0。

  正贡献排序 L31, L30, L34, L32, L33, L29, L27, L26, L28, L25, L35, L23, L16, L11, L5, L24, L17, L12, L3, L4, L14, L10, L8, L22, L9, L21, L18, L6, L7, L1, L2, L13, L19, L20, L15, L0。高贡献区 L29, L33（区间端点），Pre 为 L28, L27, L26。

- **attn+mlp**：有符号排序 L31, L30, L34, L32, L33, L29, L26, L35, L27, L28, L25, L10, L24, L23, L16, L19, L5, L8, L6, L11, L2, L22, L17, L14, L3, L15, L21, L9, L12, L13, L4, L18, L20, L7, L1, L0。

  正贡献排序 L31, L30, L34, L32, L33, L29, L26, L35, L27, L28, L25, L10, L24, L23, L16, L19, L5, L8, L6, L11, L2, L22, L17, L14, L3, L15, L21, L12, L9, L13, L4, L18, L20, L7, L1, L0。高贡献区 L29, L35（区间端点），Pre 为 L28, L27, L26。

**PaliGemma**

- **attn**：有符号排序 L15, L12, L14, L16, L17, L13, L10, L8, L9, L0, L1, L2, L3, L4, L5, L11, L7, L6。

  正贡献排序 L15, L12, L14, L16, L17, L13, L10, L8, L9, L0, L1, L2, L3, L4, L5, L6, L7, L11。高贡献区 L13, L17（区间端点），Pre 为 L12, L11, L10。

- **mlp**：有符号排序 L13, L16, L17, L14, L11, L12, L10, L9, L8, L0, L1, L2, L3, L4, L7, L15, L6, L5。

  正贡献排序 L13, L16, L17, L14, L11, L12, L10, L9, L8, L0, L1, L2, L3, L4, L5, L6, L7, L15。高贡献区 L12, L14（区间端点），Pre 为 L11, L10, L9。

- **attn+mlp**：有符号排序 L13, L15, L16, L14, L12, L17, L10, L11, L9, L8, L0, L1, L2, L3, L4, L7, L5, L6。

  正贡献排序 L13, L15, L16, L14, L12, L17, L10, L11, L9, L8, L0, L1, L2, L3, L4, L5, L6, L7。高贡献区 L12, L16（区间端点），Pre 为 L11, L10, L9。

**SmolVLM**

- **attn**：有符号排序 L22, L21, L23, L20, L19, L18, L16, L15, L17, L13, L12, L11, L8, L4, L14, L9, L10, L6, L5, L2, L7, L0, L1, L3。

  正贡献排序 L22, L21, L23, L20, L19, L18, L16, L15, L17, L13, L12, L11, L8, L4, L14, L9, L10, L6, L5, L2, L7, L0, L1, L3。高贡献区 L20, L23（区间端点），Pre 为 L19, L18, L17。

- **mlp**：有符号排序 L16, L18, L17, L19, L15, L23, L22, L21, L20, L8, L10, L14, L1, L12, L13, L4, L9, L11, L6, L2, L7, L5, L3, L0。

  正贡献排序 L16, L18, L17, L19, L15, L23, L22, L21, L20, L8, L10, L14, L1, L12, L13, L4, L9, L11, L6, L2, L7, L5, L3, L0。高贡献区 L15, L19（区间端点），Pre 为 L14, L13, L12。

- **attn+mlp**：有符号排序 L22, L21, L23, L20, L16, L18, L19, L17, L15, L8, L10, L14, L1, L13, L12, L11, L4, L9, L6, L2, L7, L5, L3, L0。

  正贡献排序 L22, L21, L23, L20, L16, L18, L19, L17, L15, L8, L10, L14, L1, L13, L12, L11, L4, L9, L6, L2, L7, L5, L3, L0。高贡献区 L19, L23（区间端点），Pre 为 L18, L17, L16。

## 4. SaLEM-alt

对新目标 alt 损失计算配置指定 MLP/FFN 模块的参数绝对梯度，按参数总数归一化，再跨样本平均。保留现有参数空间定位器，最终在推荐位置训练视觉 adapter。该定位计算本身不更新基础模型参数。

| 数据集 | 模型 | Top-3 | 定位有效样本 | Mean@3 (%) | 缺 main 层 |
| --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L0, L18, L19 | 500/500 | 68.405 | — |
| EVQA | InstructBLIP | L0, L18, L19 | 500/500 | 49.110 | — |
| EVQA | MiniGPT-4 | L8, L9, L10 | 500/500 | 68.597 | — |
| EVQA | LLaVA-1.5 | L7, L6, L5 | 500/500 | 65.503 | — |
| EVQA | Qwen2.5-VL | L11, L14, L12 | 500/500 | 62.630 | — |
| EVQA | PaliGemma | L8, L7, L9 | 500/500 | 64.269 | — |
| EVQA | SmolVLM | L9, L8, L7 | 500/500 | 66.830 | — |
| MMKE-Visual | BLIP2 | L0, L18, L19 | 214/214 | 68.342 | — |
| MMKE-Visual | InstructBLIP | L18, L17, L19 | 214/214 | 50.617 | — |
| MMKE-Visual | MiniGPT-4 | L31, L5, L8 | 214/214 | 73.897 | — |
| MMKE-Visual | LLaVA-1.5 | L7, L8, L9 | 214/214 | 76.823 | — |
| MMKE-Visual | Qwen2.5-VL | L12, L11, L14 | 214/214 | 70.607 | — |
| MMKE-Visual | PaliGemma | L10, L8, L9 | 214/214 | 96.146 | — |
| MMKE-Visual | SmolVLM | L9, L8, L0 | 214/214 | 70.157 | — |
| MMKE-Entity | BLIP2 | L0, L18, L30 | 636/636 | 69.039 | — |
| MMKE-Entity | InstructBLIP | L18, L17, L19 | 636/636 | 48.717 | — |
| MMKE-Entity | MiniGPT-4 | L31, L22, L24 | 636/636 | 75.427 | — |
| MMKE-Entity | LLaVA-1.5 | L23, L22, L24 | 636/636 | 75.517 | — |
| MMKE-Entity | Qwen2.5-VL | L15, L14, L13 | 636/636 | 71.347 | — |
| MMKE-Entity | PaliGemma | L17, L16, L13 | 636/636 | 45.340 | — |
| MMKE-Entity | SmolVLM | L0, L1, L6 | 636/636 | 70.670 | — |

## 5. LGA：模型参数梯度，Tukey

old=model_pred，new=alt；先逐样本计算 MLP/FFN 权重梯度有符号内积，再取平均。按最终方案使用 Tukey 后 Top-3；Raw 保留于来源归档，不以其替换此主列。参数空间与视觉空间有效样本集合可能不同。

| 数据集 | 模型 | Top-3 | 定位有效样本 | Mean@3 (%) | 缺 main 层 |
| --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L4, L16, L18 | 404/500 | 67.753 | — |
| EVQA | InstructBLIP | L17, L18, L20 | 345/500 | 未齐 | L17, L20 |
| EVQA | MiniGPT-4 | L29, L25, L22 | 499/500 | 58.515 | — |
| EVQA | LLaVA-1.5 | L24, L25, L26 | 374/500 | 62.098 | — |
| EVQA | Qwen2.5-VL | L3, L10, L6 | 493/500 | 62.561 | — |
| EVQA | PaliGemma | L7, L0, L8 | 286/500 | 64.047 | — |
| EVQA | SmolVLM | L22, L21, L20 | 499/500 | 56.463 | — |
| MMKE-Visual | BLIP2 | L18, L16, L17 | 172/214 | 71.157 | — |
| MMKE-Visual | InstructBLIP | L17, L20, L18 | 214/214 | 50.699 | — |
| MMKE-Visual | MiniGPT-4 | L0, L1, L3 | 214/214 | 76.090 | — |
| MMKE-Visual | LLaVA-1.5 | L24, L22, L27 | 214/214 | 74.274 | — |
| MMKE-Visual | Qwen2.5-VL | L3, L6, L10 | 214/214 | 70.326 | — |
| MMKE-Visual | PaliGemma | L7, L8, L10 | 214/214 | 94.585 | — |
| MMKE-Visual | SmolVLM | L6, L8, L5 | 214/214 | 69.954 | — |
| MMKE-Entity | BLIP2 | L16, L13, L18 | 289/636 | 69.825 | — |
| MMKE-Entity | InstructBLIP | L1, L17, L20 | 636/636 | 55.578 | — |
| MMKE-Entity | MiniGPT-4 | L7, L8, L14 | 636/636 | 未齐 | L8 |
| MMKE-Entity | LLaVA-1.5 | L9, L7, L8 | 636/636 | 未齐 | L7, L8 |
| MMKE-Entity | Qwen2.5-VL | L6, L3, L10 | 636/636 | 72.126 | — |
| MMKE-Entity | PaliGemma | L7, L8, L13 | 636/636 | 78.357 | — |
| MMKE-Entity | SmolVLM | L0, L6, L8 | 636/636 | 70.549 | — |

## 6. Perturb-KL-alt

扰动层间视觉 token 隐状态，在完整 alt teacher-forcing 答案位置比较干净/扰动的全词表输出分布 KL。现有 score_kl_robust 使用四噪声强度×三重复，在各配置内层间归一化后聚合；直接选敏感层，不做 Pre。

| 数据集 | 模型 | Top-3 | 定位有效样本 | Mean@3 (%) | 缺 main 层 |
| --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L3, L4, L2 | 500/500 | 56.617 | — |
| EVQA | InstructBLIP | L2, L3, L4 | 500/500 | 49.436 | — |
| EVQA | MiniGPT-4 | L0, L1, L2 | 500/500 | 64.143 | — |
| EVQA | LLaVA-1.5 | L0, L1, L2 | 500/500 | 62.641 | — |
| EVQA | Qwen2.5-VL | L0, L1, L2 | 500/500 | 62.200 | — |
| EVQA | PaliGemma | L5, L7, L6 | 500/500 | 73.497 | — |
| EVQA | SmolVLM | L1, L2, L0 | 500/500 | 64.383 | — |
| MMKE-Visual | BLIP2 | L3, L4, L2 | 214/214 | 69.266 | — |
| MMKE-Visual | InstructBLIP | L2, L3, L5 | 214/214 | 50.513 | — |
| MMKE-Visual | MiniGPT-4 | L0, L1, L2 | 214/214 | 75.900 | — |
| MMKE-Visual | LLaVA-1.5 | L0, L1, L2 | 214/214 | 75.861 | — |
| MMKE-Visual | Qwen2.5-VL | L0, L13, L14 | 214/214 | 70.210 | — |
| MMKE-Visual | PaliGemma | L7, L5, L6 | 214/214 | 83.814 | — |
| MMKE-Visual | SmolVLM | L1, L4, L0 | 214/214 | 70.690 | — |
| MMKE-Entity | BLIP2 | L3, L2, L4 | 636/636 | 71.525 | — |
| MMKE-Entity | InstructBLIP | L5, L4, L3 | 636/636 | 49.037 | — |
| MMKE-Entity | MiniGPT-4 | L0, L1, L2 | 636/636 | 75.349 | — |
| MMKE-Entity | LLaVA-1.5 | L0, L1, L2 | 636/636 | 未齐 | L0, L1, L2 |
| MMKE-Entity | Qwen2.5-VL | L0, L1, L2 | 636/636 | 72.180 | — |
| MMKE-Entity | PaliGemma | L7, L5, L6 | 636/636 | 92.637 | — |
| MMKE-Entity | SmolVLM | L0, L1, L2 | 636/636 | 70.880 | — |

## 7. 我们的猜想：视觉梯度与表征相似度

### 7.1 梯度对象与十个版本

定位时在冻结基础模型的 decoder 层输出视觉隐状态 Hᵥ 上计算梯度，等价于在 ΔHᵥ=0 处对虚拟视觉增量求梯度；不是先训练 adapter 后再归因，也不是 adapter 权重梯度。

aᵢ=旧目标视觉梯度 L2 范数，bᵢ=新目标视觉梯度 L2 范数，cᵢ=二者余弦；E 为同一组合有效样本的等权平均。A 版取 abs(E[c])，B 版取样本内 abs(c) 后再聚合；两者不能互换。

| 公式 | 归因含义 | A：分别平均再相乘 | B：逐样本算后平均 |
| --- | --- | --- | --- |
| F1：有符号方向×旧强度×新强度 | 保留方向和两侧强度；B 为视觉梯度内积对应版本。 | E[c]×E[a]×E[b] | E[c×a×b] |
| F2：绝对方向×旧强度×新强度 | 强调方向关系强度，同时接受同向和反向，保留旧、新两侧强度。 | abs(E[c])×E[a]×E[b] | E[abs(c)×a×b] |
| F3：有符号方向×新强度 | 去掉旧梯度强度，B 对应新梯度沿旧梯度单位方向的有符号投影。 | E[c]×E[b] | E[c×b] |
| F4：绝对方向×新强度 | 去掉旧强度并忽略方向正负；B 对应投影长度。历史 Ours 仅对应 A。 | abs(E[c])×E[b] | E[abs(c)×b] |
| F5：仅新梯度强度 | 只看新目标敏感性；A、B 数学上相同，保留两个编号以对应最终方案。 | E[b] | E[b] |

F5-A=F5-B：十个编号包含九种不同数学统计。F1-A/F2-A 本次由已有三种层均值直接派生；F1-B 按原 epsilon=1e-12 约定使用 E[dot]−epsilon×E[c]，21 组 Tukey Top-3 与既有视觉 LGA 一致。F4-A 是历史 abs(S_v_cos)×S_v_new_norm，但当前仍作为待比较公式之一，不预设胜出。

缺失 F2-B、F3-B、F4-B 的原因是旧逐样本日志未保存所需 cos/范数交叉统计。严格补算会保存逐样本基础量，完成后可以生成这些版本；当前已核验状态仍在等待前序实验。不能用层均值相乘伪造样本内乘积均值。

BLIP2 × MMKE-Entity 视觉梯度沿用 284/636 条有效样本（44.65%），属于低覆盖；这不等于在全部 636 条上定位。其他组合有效样本数可追溯原层分数 n_request。

### 7.1.1 F1：有符号方向×旧强度×新强度

**A：`E[c]×E[a]×E[b]`；B：`E[c×a×b]`。** 保留方向和两侧强度；B 为视觉梯度内积对应版本。

| 数据集 | 模型 | A Top-3 | A Mean@3 | A 缺 main 层 | B Top-3 | B Mean@3 | B 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L4, L5, L6 | 未齐 | L6 | L5, L6, L7 | 未齐 | L6, L7 |
| EVQA | InstructBLIP | L11, L9, L10 | 未齐 | L9, L10 | L11, L9, L10 | 未齐 | L9, L10 |
| EVQA | MiniGPT-4 | L18, L8, L7 | 65.219 | — | L18, L16, L17 | 62.802 | — |
| EVQA | LLaVA-1.5 | L31†, L30, L29 | 未齐 | L29 | L31†, L30, L29 | 未齐 | L29 |
| EVQA | Qwen2.5-VL | L17, L18, L14 | 63.181 | — | L6, L5, L7 | 未齐 | L5, L7 |
| EVQA | PaliGemma | L5, L4, L3 | 78.340 | — | L5, L4, L3 | 78.340 | — |
| EVQA | SmolVLM | L23†, L22, L21 | 未齐 | L23 | L23†, L22, L21 | 未齐 | L23 |
| MMKE-Visual | BLIP2 | L6, L7, L8 | 未齐 | L6, L7, L8 | L7, L8, L9 | 未齐 | L7, L8, L9 |
| MMKE-Visual | InstructBLIP | L1, L0, L3 | 64.244 | — | L1, L0, L3 | 64.244 | — |
| MMKE-Visual | MiniGPT-4 | L31†, L30, L29 | 未齐 | L30 | L30, L29, L28 | 未齐 | L30 |
| MMKE-Visual | LLaVA-1.5 | L31†, L30, L29 | 未齐 | L31, L30, L29 | L31†, L30, L29 | 未齐 | L31, L30, L29 |
| MMKE-Visual | Qwen2.5-VL | L0, L1, L2 | 69.943 | — | L2, L3, L4 | 未齐 | L4 |
| MMKE-Visual | PaliGemma | L3, L2, L6 | 68.755 | — | L2, L1, L6 | 71.790 | — |
| MMKE-Visual | SmolVLM | L2, L3, L4 | 未齐 | L3 | L0, L1, L2 | 70.687 | — |
| MMKE-Entity | BLIP2 | L6, L8, L31† | 未齐 | L6, L8, L31 | L31†, L29, L30 | 未齐 | L31 |
| MMKE-Entity | InstructBLIP | L1, L0, L3 | 62.507 | — | L1, L0, L3 | 62.507 | — |
| MMKE-Entity | MiniGPT-4 | L29, L28, L25 | 未齐 | L29 | L29, L28, L25 | 未齐 | L29 |
| MMKE-Entity | LLaVA-1.5 | L2, L20, L21 | 未齐 | L2, L20, L21 | L31†, L29, L21 | 未齐 | L31, L29, L21 |
| MMKE-Entity | Qwen2.5-VL | L0, L1, L2 | 72.180 | — | L0, L1, L2 | 72.180 | — |
| MMKE-Entity | PaliGemma | L4, L3, L2 | 90.382 | — | L3, L2, L6 | 90.663 | — |
| MMKE-Entity | SmolVLM | L3, L4, L5 | 未齐 | L3, L4, L5 | L2, L3, L4 | 未齐 | L3, L4 |

### 7.1.2 F2：绝对方向×旧强度×新强度

**A：`abs(E[c])×E[a]×E[b]`；B：`E[abs(c)×a×b]`。** 强调方向关系强度，同时接受同向和反向，保留旧、新两侧强度。

| 数据集 | 模型 | A Top-3 | A Mean@3 | A 缺 main 层 | B Top-3 | B Mean@3 | B 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L4, L5, L6 | 未齐 | L6 | 待补 | — | 待定位 |
| EVQA | InstructBLIP | L11, L9, L10 | 未齐 | L9, L10 | 待补 | — | 待定位 |
| EVQA | MiniGPT-4 | L18, L8, L7 | 65.219 | — | 待补 | — | 待定位 |
| EVQA | LLaVA-1.5 | L0, L1, L2 | 62.641 | — | 待补 | — | 待定位 |
| EVQA | Qwen2.5-VL | L17, L18, L14 | 63.181 | — | 待补 | — | 待定位 |
| EVQA | PaliGemma | L5, L4, L3 | 78.340 | — | 待补 | — | 待定位 |
| EVQA | SmolVLM | L2, L3, L4 | 未齐 | L4 | 待补 | — | 待定位 |
| MMKE-Visual | BLIP2 | L6, L7, L8 | 未齐 | L6, L7, L8 | 待补 | — | 待定位 |
| MMKE-Visual | InstructBLIP | L1, L0, L3 | 64.244 | — | 待补 | — | 待定位 |
| MMKE-Visual | MiniGPT-4 | L9, L8, L6 | 未齐 | L6 | 待补 | — | 待定位 |
| MMKE-Visual | LLaVA-1.5 | L0, L3, L5 | 未齐 | L5 | 待补 | — | 待定位 |
| MMKE-Visual | Qwen2.5-VL | L0, L1, L2 | 69.943 | — | 待补 | — | 待定位 |
| MMKE-Visual | PaliGemma | L3, L2, L6 | 68.755 | — | 待补 | — | 待定位 |
| MMKE-Visual | SmolVLM | L2, L3, L4 | 未齐 | L3 | 待补 | — | 待定位 |
| MMKE-Entity | BLIP2 | L16, L15, L17 | 69.832 | — | 待补 | — | 待定位 |
| MMKE-Entity | InstructBLIP | L1, L0, L3 | 62.507 | — | 待补 | — | 待定位 |
| MMKE-Entity | MiniGPT-4 | L9, L7, L8 | 未齐 | L9, L8 | 待补 | — | 待定位 |
| MMKE-Entity | LLaVA-1.5 | L13, L12, L0 | 未齐 | L13, L12, L0 | 待补 | — | 待定位 |
| MMKE-Entity | Qwen2.5-VL | L0, L1, L2 | 72.180 | — | 待补 | — | 待定位 |
| MMKE-Entity | PaliGemma | L4, L3, L2 | 90.382 | — | 待补 | — | 待定位 |
| MMKE-Entity | SmolVLM | L3, L4, L5 | 未齐 | L3, L4, L5 | 待补 | — | 待定位 |

### 7.1.3 F3：有符号方向×新强度

**A：`E[c]×E[b]`；B：`E[c×b]`。** 去掉旧梯度强度，B 对应新梯度沿旧梯度单位方向的有符号投影。

| 数据集 | 模型 | A Top-3 | A Mean@3 | A 缺 main 层 | B Top-3 | B Mean@3 | B 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L1, L2, L3 | 57.031 | — | 待补 | — | 待定位 |
| EVQA | InstructBLIP | L1, L0, L11 | 51.987 | — | 待补 | — | 待定位 |
| EVQA | MiniGPT-4 | L18, L19, L16 | 60.959 | — | 待补 | — | 待定位 |
| EVQA | LLaVA-1.5 | L31†, L30, L29 | 未齐 | L29 | 待补 | — | 待定位 |
| EVQA | Qwen2.5-VL | L21, L19, L17 | 63.182 | — | 待补 | — | 待定位 |
| EVQA | PaliGemma | L5, L4, L3 | 78.340 | — | 待补 | — | 待定位 |
| EVQA | SmolVLM | L23†, L22, L21 | 未齐 | L23 | 待补 | — | 待定位 |
| MMKE-Visual | BLIP2 | L5, L6, L7 | 未齐 | L5, L6, L7 | 待补 | — | 待定位 |
| MMKE-Visual | InstructBLIP | L1, L0, L3 | 64.244 | — | 待补 | — | 待定位 |
| MMKE-Visual | MiniGPT-4 | L2, L0, L1 | 75.900 | — | 待补 | — | 待定位 |
| MMKE-Visual | LLaVA-1.5 | L31†, L29, L28 | 未齐 | L31, L29 | 待补 | — | 待定位 |
| MMKE-Visual | Qwen2.5-VL | L0, L1, L2 | 69.943 | — | 待补 | — | 待定位 |
| MMKE-Visual | PaliGemma | L5, L4, L3 | 64.037 | — | 待补 | — | 待定位 |
| MMKE-Visual | SmolVLM | L0, L1, L2 | 70.687 | — | 待补 | — | 待定位 |
| MMKE-Entity | BLIP2 | L6, L8, L31† | 未齐 | L6, L8, L31 | 待补 | — | 待定位 |
| MMKE-Entity | InstructBLIP | L1, L0, L3 | 62.507 | — | 待补 | — | 待定位 |
| MMKE-Entity | MiniGPT-4 | L0, L1, L30 | 未齐 | L30 | 待补 | — | 待定位 |
| MMKE-Entity | LLaVA-1.5 | L20, L21, L2 | 未齐 | L20, L21, L2 | 待补 | — | 待定位 |
| MMKE-Entity | Qwen2.5-VL | L0, L1, L2 | 72.180 | — | 待补 | — | 待定位 |
| MMKE-Entity | PaliGemma | L5, L4, L3 | 93.305 | — | 待补 | — | 待定位 |
| MMKE-Entity | SmolVLM | L0, L1, L2 | 70.880 | — | 待补 | — | 待定位 |

### 7.1.4 F4：绝对方向×新强度

**A：`abs(E[c])×E[b]`；B：`E[abs(c)×b]`。** 去掉旧强度并忽略方向正负；B 对应投影长度。历史 Ours 仅对应 A。

| 数据集 | 模型 | A Top-3 | A Mean@3 | A 缺 main 层 | B Top-3 | B Mean@3 | B 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L1, L2, L3 | 57.031 | — | 待补 | — | 待定位 |
| EVQA | InstructBLIP | L1, L0, L11 | 51.987 | — | 待补 | — | 待定位 |
| EVQA | MiniGPT-4 | L18, L19, L16 | 60.959 | — | 待补 | — | 待定位 |
| EVQA | LLaVA-1.5 | L0, L1, L2 | 62.641 | — | 待补 | — | 待定位 |
| EVQA | Qwen2.5-VL | L21, L19, L17 | 63.182 | — | 待补 | — | 待定位 |
| EVQA | PaliGemma | L5, L4, L3 | 78.340 | — | 待补 | — | 待定位 |
| EVQA | SmolVLM | L0, L1, L2 | 64.383 | — | 待补 | — | 待定位 |
| MMKE-Visual | BLIP2 | L5, L6, L7 | 未齐 | L5, L6, L7 | 待补 | — | 待定位 |
| MMKE-Visual | InstructBLIP | L1, L0, L3 | 64.244 | — | 待补 | — | 待定位 |
| MMKE-Visual | MiniGPT-4 | L10, L11, L15 | 76.444 | — | 待补 | — | 待定位 |
| MMKE-Visual | LLaVA-1.5 | L0, L3, L1 | 75.661 | — | 待补 | — | 待定位 |
| MMKE-Visual | Qwen2.5-VL | L0, L1, L2 | 69.943 | — | 待补 | — | 待定位 |
| MMKE-Visual | PaliGemma | L5, L4, L3 | 64.037 | — | 待补 | — | 待定位 |
| MMKE-Visual | SmolVLM | L0, L1, L2 | 70.687 | — | 待补 | — | 待定位 |
| MMKE-Entity | BLIP2 | L16, L17, L18 | 69.941 | — | 待补 | — | 待定位 |
| MMKE-Entity | InstructBLIP | L1, L0, L3 | 62.507 | — | 待补 | — | 待定位 |
| MMKE-Entity | MiniGPT-4 | L27, L28, L26 | 75.796 | — | 待补 | — | 待定位 |
| MMKE-Entity | LLaVA-1.5 | L14, L15, L0 | 未齐 | L0 | 待补 | — | 待定位 |
| MMKE-Entity | Qwen2.5-VL | L0, L1, L2 | 72.180 | — | 待补 | — | 待定位 |
| MMKE-Entity | PaliGemma | L5, L4, L3 | 93.305 | — | 待补 | — | 待定位 |
| MMKE-Entity | SmolVLM | L0, L1, L2 | 70.880 | — | 待补 | — | 待定位 |

### 7.1.5 F5：仅新梯度强度

**A：`E[b]`；B：`E[b]`。** 只看新目标敏感性；A、B 数学上相同，保留两个编号以对应最终方案。

| 数据集 | 模型 | A Top-3 | A Mean@3 | A 缺 main 层 | B Top-3 | B Mean@3 | B 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | L1, L2, L3 | 57.031 | — | L1, L2, L3 | 57.031 | — |
| EVQA | InstructBLIP | L1, L0, L9 | 未齐 | L9 | L1, L0, L9 | 未齐 | L9 |
| EVQA | MiniGPT-4 | L0, L1, L2 | 64.143 | — | L0, L1, L2 | 64.143 | — |
| EVQA | LLaVA-1.5 | L0, L1, L3 | 未齐 | L3 | L0, L1, L3 | 未齐 | L3 |
| EVQA | Qwen2.5-VL | L0, L1, L2 | 62.200 | — | L0, L1, L2 | 62.200 | — |
| EVQA | PaliGemma | L5, L4, L3 | 78.340 | — | L5, L4, L3 | 78.340 | — |
| EVQA | SmolVLM | L1, L2, L3 | 63.247 | — | L1, L2, L3 | 63.247 | — |
| MMKE-Visual | BLIP2 | L6, L7, L8 | 未齐 | L6, L7, L8 | L6, L7, L8 | 未齐 | L6, L7, L8 |
| MMKE-Visual | InstructBLIP | L1, L0, L3 | 64.244 | — | L1, L0, L3 | 64.244 | — |
| MMKE-Visual | MiniGPT-4 | L0, L1, L2 | 75.900 | — | L0, L1, L2 | 75.900 | — |
| MMKE-Visual | LLaVA-1.5 | L5, L0, L6 | 未齐 | L5, L6 | L5, L0, L6 | 未齐 | L5, L6 |
| MMKE-Visual | Qwen2.5-VL | L0, L1, L2 | 69.943 | — | L0, L1, L2 | 69.943 | — |
| MMKE-Visual | PaliGemma | L4, L5, L3 | 64.037 | — | L4, L5, L3 | 64.037 | — |
| MMKE-Visual | SmolVLM | L0, L1, L2 | 70.687 | — | L0, L1, L2 | 70.687 | — |
| MMKE-Entity | BLIP2 | L7, L8, L9 | 未齐 | L7, L8, L9 | L7, L8, L9 | 未齐 | L7, L8, L9 |
| MMKE-Entity | InstructBLIP | L1, L0, L3 | 62.507 | — | L1, L0, L3 | 62.507 | — |
| MMKE-Entity | MiniGPT-4 | L0, L1, L2 | 75.349 | — | L0, L1, L2 | 75.349 | — |
| MMKE-Entity | LLaVA-1.5 | L0, L1, L6 | 未齐 | L0, L1, L6 | L0, L1, L6 | 未齐 | L0, L1, L6 |
| MMKE-Entity | Qwen2.5-VL | L0, L1, L2 | 72.180 | — | L0, L1, L2 | 72.180 | — |
| MMKE-Entity | PaliGemma | L5, L4, L3 | 93.305 | — | L5, L4, L3 | 93.305 | — |
| MMKE-Entity | SmolVLM | L1, L2, L3 | 未齐 | L3 | L1, L2, L3 | 未齐 | L3 |

### 7.2 绿色点划线：视觉表征相似度

相似度比较视觉 token 隐状态均值与文本预测位置的隐状态，不是新旧梯度余弦。不分新旧 none 使用固定图像+问题的首答案预测位置；alt/model_pred 在相应答案各普通 token 的预测位置计算，先样本内平均，再跨样本平均。图像/Q-Former 编码不混入答案。

主对比使用 matched_gradient，与既有视觉梯度有效样本 ID 对齐。BLIP2 等组合虽然 none/alt 可处理更多样本，不能把不同覆盖率直接混进公式比较。

截至服务器快照 2026-09-28T21:58:41.648858+08:00，完成 9/21 个组合，三种目标共 27/63 个组合×目标；分数、协议、诊断文件哈希已核对。当时控制器在 g09 运行 MiniGPT-4。

截图中的“极大值区间中层”仍未实现；需要独立定义区间阈值、多峰选择、中心和 Top-3 邻层。以下 Raw 表示直接按相似度高到低，Tukey 是另列的过滤版本，两者都不能替代区间中层规则。

#### 不分新旧：已有推荐

| 数据集 | 模型 | 匹配样本数 | 降序 Raw Top-3 | Raw Mean@3 | Raw 缺 main 层 | Tukey Top-3 | Tukey Mean@3 | Tukey 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | 465 | L8, L5, L6 | 未齐 | L8, L6 | L8, L5, L6 | 未齐 | L8, L6 |
| EVQA | InstructBLIP | 500 | L22, L24, L23 | 未齐 | L22, L24, L23 | L22, L24, L23 | 未齐 | L22, L24, L23 |
| EVQA | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | LLaVA-1.5 | 500 | L31, L29, L28 | 未齐 | L29 | L31, L29, L28 | 未齐 | L29 |
| EVQA | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | BLIP2 | 175 | L8, L6, L7 | 未齐 | L8, L6, L7 | L8, L6, L7 | 未齐 | L8, L6, L7 |
| MMKE-Visual | InstructBLIP | 214 | L4, L14, L5 | 49.861 | — | L4, L14, L5 | 49.861 | — |
| MMKE-Visual | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | LLaVA-1.5 | 214 | L31, L29, L28 | 未齐 | L31, L29 | L31, L29, L28 | 未齐 | L31, L29 |
| MMKE-Visual | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | BLIP2 | 284 | L8, L7, L6 | 未齐 | L8, L7, L6 | L8, L7, L6 | 未齐 | L8, L7, L6 |
| MMKE-Entity | InstructBLIP | 636 | L4, L5, L14 | 48.576 | — | L4, L5, L14 | 48.576 | — |
| MMKE-Entity | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | LLaVA-1.5 | 636 | L29, L28, L31 | 未齐 | L29, L31 | L29, L28, L31 | 未齐 | L29, L31 |
| MMKE-Entity | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |

#### 仅新目标 alt：已有推荐

| 数据集 | 模型 | 匹配样本数 | 降序 Raw Top-3 | Raw Mean@3 | Raw 缺 main 层 | Tukey Top-3 | Tukey Mean@3 | Tukey 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | 465 | L5, L3, L6 | 未齐 | L6 | L5, L3, L6 | 未齐 | L6 |
| EVQA | InstructBLIP | 500 | L5, L4, L6 | 未齐 | L5, L6 | L5, L4, L6 | 未齐 | L5, L6 |
| EVQA | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | LLaVA-1.5 | 500 | L31, L29, L28 | 未齐 | L29 | L31, L29, L28 | 未齐 | L29 |
| EVQA | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | BLIP2 | 175 | L3, L5, L4 | 未齐 | L5 | L3, L5, L4 | 未齐 | L5 |
| MMKE-Visual | InstructBLIP | 214 | L14, L10, L8 | 未齐 | L10, L8 | L14, L10, L8 | 未齐 | L10, L8 |
| MMKE-Visual | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | LLaVA-1.5 | 214 | L31, L29, L30 | 未齐 | L31, L29, L30 | L29, L30, L28 | 未齐 | L29, L30 |
| MMKE-Visual | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | BLIP2 | 284 | L3, L2, L4 | 71.525 | — | L3, L2, L4 | 71.525 | — |
| MMKE-Entity | InstructBLIP | 636 | L8, L10, L4 | 未齐 | L8, L10 | L8, L10, L4 | 未齐 | L8, L10 |
| MMKE-Entity | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | LLaVA-1.5 | 636 | L31, L29, L30 | 未齐 | L31, L29, L30 | L28, L27, L26 | 75.011 | — |
| MMKE-Entity | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |

#### 仅旧目标 model_pred：已有推荐

| 数据集 | 模型 | 匹配样本数 | 降序 Raw Top-3 | Raw Mean@3 | Raw 缺 main 层 | Tukey Top-3 | Tukey Mean@3 | Tukey 缺 main 层 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA | BLIP2 | 465 | L5, L3, L6 | 未齐 | L6 | L5, L3, L6 | 未齐 | L6 |
| EVQA | InstructBLIP | 500 | L5, L4, L6 | 未齐 | L5, L6 | L5, L4, L6 | 未齐 | L5, L6 |
| EVQA | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | LLaVA-1.5 | 500 | L31, L29, L28 | 未齐 | L29 | L31, L29, L28 | 未齐 | L29 |
| EVQA | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| EVQA | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | BLIP2 | 175 | L5, L3, L6 | 未齐 | L5, L6 | L5, L3, L6 | 未齐 | L5, L6 |
| MMKE-Visual | InstructBLIP | 214 | L14, L4, L5 | 49.861 | — | L14, L4, L5 | 49.861 | — |
| MMKE-Visual | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | LLaVA-1.5 | 214 | L31, L29, L28 | 未齐 | L31, L29 | L31, L29, L28 | 未齐 | L31, L29 |
| MMKE-Visual | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Visual | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | BLIP2 | 284 | L3, L5, L4 | 未齐 | L5 | L3, L5, L4 | 未齐 | L5 |
| MMKE-Entity | InstructBLIP | 636 | L4, L5, L14 | 48.576 | — | L4, L5, L14 | 48.576 | — |
| MMKE-Entity | MiniGPT-4 | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | LLaVA-1.5 | 636 | L31, L29, L28 | 未齐 | L31, L29 | L31, L29, L28 | 未齐 | L31, L29 |
| MMKE-Entity | Qwen2.5-VL | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | PaliGemma | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |
| MMKE-Entity | SmolVLM | 待补 | 待补 | — | 待定位 | 待补 | — | 待定位 |

## 8. 尚缺的数据与来源

- VisEdit：MMKE-Visual、MMKE-Entity 共十四组 model_pred 原始贡献。三条贡献分支均受此缺项影响。
- 视觉梯度：F2-B、F3-B、F4-B 各二十一组，缺严格逐样本交叉统计；服务器等待状态不等于已算完。
- 绿色相似度：当前快照尚缺 12 个组合的完整前向结果；另有不分新旧的极大值区间中层选层规则尚未实现。
- 已有定位的候选层仍存在 main 编辑评测缺项，逐行列在各表“缺 main 层”。不将缺分记为零，不替换为 stable，不以部分 Top-3 平均值宣称完整 Mean@3。

本表用于记录候选和已有实测；尚不能判定某一第七类公式在全部七模型×三数据集上超过前六类方法。公式须统一应用于二十一组，宏均值更高与逐组全部胜出分别报告。

### 数据文件

- [最终方法全量登记 JSON（含待补、逐候选层 Average、Mean@3）](../../outputs/final_seven_method_audit_20260928/final_methods_registry.json)
- [本表生成核验与来源哈希](../../outputs/final_seven_method_audit_20260928/final_document_verification.json)
- [原始定位总登记](../../outputs/all_methods_recommendations_20260928/recommendations.json)
- [视觉梯度可用七编号、逐层分数及 Tukey 剔除层](../../outputs/final_seven_method_audit_20260928/gradient_available_top3.json)
- [VisEdit 三分支完整分数、排序与高贡献区](../../outputs/final_seven_method_audit_20260928/visedit_model_pred_components.json)
- [绿色相似度已核验产物及完整排序](../../outputs/final_seven_method_audit_20260928/similarity_verified.json)
- [main/stable 原始评测汇总](../../outputs/all_methods_performance_20260928/outcomes_used.csv)
- [独立核验附表](../../outputs/final_seven_method_audit_20260928/核验附表.md)
- [服务器只读状态快照](../../outputs/final_seven_method_audit_20260928/remote_status.json)
- [可重建脚本](../../outputs/final_seven_method_audit_20260928/build_final_document.py)

### 可复现与版本边界

本次只读取此前核验快照并回填指定 Markdown，未启动或更改服务器实验。后续补算完成后，应先更新已核验输入再重建此表；不能只改完成数量而不补原始分数及推荐层。旧总表中的唯一 Ours 公式与历史方法并集结论不约束本次最终方法方案。

