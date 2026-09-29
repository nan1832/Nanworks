# 七类定位方法：Top-3 推荐层、VisEdit 全层贡献度与消融

**整理时间：2026-09-28T13:17:07+08:00（北京时间）。服务器原始定位产物核对时间：2026-09-28T13:14:07.052060+08:00。**

本文件按本次指定的七类方法重新组织；每行对应一个模型与数据集。层号从 L0 开始，Top-3 保留推荐顺序。这里的定位分数不等于训练后的编辑性能；不计算或宣称当前 Top-3 并集总层数。真实训练评测见 [扫层结果总账](6location_7model_3datas_top_3_5_layers_outcome.md) 与 [SWeeplayers](SWeeplayers.md)。

## 0. 目标与排序口径

- `alt` 是新知识目标；`model_pred` 是基础模型自己的响应；数据集字段 `pred` 单独标明，不能更名为 `model_pred`。
- `Pre` 是 VisEdit 高贡献区域之前的候选层规则，不是目标字段 `pred`。贡献度最高的层与 Pre 推荐编辑层分别报告。
- 正式 Ours 主公式为 `abs(S_v_cos) * S_v_new_norm`，**不含深度权重**。早期 Conflict、AbsDirection×depth² 等保存在原文备份，不能混充当前主公式。
- 第七类消融按用户确认仅针对视觉表征 LGA；分别去旧强度、去新强度、去方向。缺少必要统计的版本在每个组合明确写待补。
- 定位样本总量：EVQA-pilot500 为 500，MMKE-visual 为 214，MMKE-entity 为 636；各方法有效样本数另列，不能把不同覆盖率当作完全相同实验。

### 全层 Tukey 协议

对每一个模型×数据集×公式，先取**全部层**的该公式有限分数计算 Q1、Q3，令 IQR=Q3−Q1；一次性剔除低于 `Q1−1.0×IQR` 或高于 `Q3+1.0×IQR` 的所有层，再对保留层降序排序取 Top-3。同分取较浅层；边界值保留；不足三层不回填异常层；不迭代重新估计四分位数。

Tukey 系数 1.0 依据 [LGA 论文附录 A](https://arxiv.org/html/2602.20207v3#A1)。四分位数采用 NumPy `method=linear`，这是明确的实现约定。对 Ours 和消融公式应用相同流程是本次扩展，不称为论文原有实验。每个公式按自身分数过滤，不共享由其他公式确定的异常层掩码。

Raw 不做 Tukey，不裁剪、不截尾、不丢弃有限的大梯度层。本次全层口径还保留原始记录中每组最后一层的有限零分及 `S_v_zero_grad` 标记；余弦按原脚本 epsilon 约定为 0，这些层通常因因果结构没有视觉梯度，不能把 0 解读为已测得有效梯度方向。Tukey 的四分位数也包含这些有限零分；这与历史先删零梯度层的 clean 口径不同。NaN/Inf 不转换成 0；当前所用视觉与参数原始层表全部为有限数。

**† 表示原始记录标记为零视觉梯度的层。** 视觉 LGA 使用有符号内积，七个组合的其他层内积为负，因此零分末层在全层 Raw 中排在它们之前；这是本次不预先删层的直接结果，不能据此声称该层有有效梯度证据。具体与旧 clean 排名的变化见 [差异核对表](../../outputs/all_methods_recommendations_20260928/raw_vs_previous_clean.csv)。

## 1. 中层先验

中心为 `(L−1)/2`（ρ=0.5）；按到中心的距离升序，同距离取较浅层。三个数据集使用同一组推荐。

| 模型 | 模型标识 | 层数 | Top-3（适用于三个数据集） |
|---|---|---|---|
| BLIP2 | blip2-opt-2.7b | 32 | L15, L16, L14 |
| InstructBLIP | instructblip-vicuna-7b | 32 | L15, L16, L14 |
| MiniGPT-4 | minigpt-4-vicuna-7b | 32 | L15, L16, L14 |
| LLaVA-1.5 | llava-v1.5-7b | 32 | L15, L16, L14 |
| Qwen2.5-VL | qwen2.5-vl-3b | 36 | L17, L18, L16 |
| PaliGemma | paligemma-3b | 18 | L8, L9, L7 |
| SmolVLM | smolvlm-1.7b | 24 | L11, L12, L10 |

## 2. CMA 因果恢复：model_pred 与 alt

两版都保留。CMA-alt v1.3 使用完整 alt 序列、α=1.0/seed=2026；model_pred 使用完整模型响应、α={0.5,1,2}×seed={0,1,2}，按有效恢复对的 CR 均值排序。因此当前两版同时改变了目标与扰动协议，不能将差异只归因于目标类型。CMA 的稳定/不稳定指定位排名，不是 adapter 训练的 main/stable。

| 数据集 | 模型 | CMA-model_pred Top-3 | 有效样本/总量；排名 | CMA-alt v1.3 Top-3 | 有效样本/总量 |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2 | L2, L1, L0 | 465/500；model_pred 可用 465/500；排序稳定 | L4, L2, L5 | 389/500 |
| EVQA-pilot500 | InstructBLIP | L1, L0, L2 | 496/500；model_pred 可用 500/500；排序稳定 | L1, L0, L25 | 421/500 |
| EVQA-pilot500 | MiniGPT-4 | L0, L1, L2 | 497/500；model_pred 可用 499/500；排序稳定 | L7, L1, L0 | 285/500 |
| EVQA-pilot500 | LLaVA-1.5 | L0, L1, L2 | 500/500；model_pred 可用 500/500；排序稳定 | L0, L1, L4 | 397/500 |
| EVQA-pilot500 | Qwen2.5-VL | L1, L0, L15 | 354/500；model_pred 可用 500/500；排序不稳定 | L1, L0, L3 | 239/500 |
| EVQA-pilot500 | PaliGemma | L5, L4, L7 | 410/500；model_pred 可用 500/500；排序稳定 | L5, L4, L0 | 215/500 |
| EVQA-pilot500 | SmolVLM | L0, L1, L5 | 497/500；model_pred 可用 500/500；排序不稳定 | L0, L1, L3 | 293/500 |
| MMKE-visual | BLIP2 | L2, L0, L3 | 175/214；model_pred 可用 175/214；排序稳定 | L3, L0, L1 | 212/214 |
| MMKE-visual | InstructBLIP | L1, L25, L22 | 214/214；model_pred 可用 214/214；排序稳定 | L23, L22, L24 | 212/214 |
| MMKE-visual | MiniGPT-4 | L0, L1, L2 | 214/214；model_pred 可用 214/214；排序稳定 | L0, L1, L2 | 50/214 |
| MMKE-visual | LLaVA-1.5 | L0, L1, L2 | 214/214；model_pred 可用 214/214；排序稳定 | L0, L1, L2 | 207/214 |
| MMKE-visual | Qwen2.5-VL | L1, L0, L2 | 154/214；model_pred 可用 214/214；排序稳定 | L1, L0, L6 | 31/214 |
| MMKE-visual | PaliGemma | L7, L6, L4 | 166/214；model_pred 可用 214/214；排序不稳定 | L1, L2, L0 | 76/214 |
| MMKE-visual | SmolVLM | L1, L0, L5 | 213/214；model_pred 可用 214/214；排序不稳定 | L0, L1, L15 | 140/214 |
| MMKE-entity | BLIP2 | L2, L3, L1 | 284/636；model_pred 可用 284/636；排序稳定 | L3, L0, L2 | 634/636 |
| MMKE-entity | InstructBLIP | L26, L25, L22 | 627/636；model_pred 可用 636/636；排序稳定 | L23, L24, L22 | 630/636 |
| MMKE-entity | MiniGPT-4 | L0, L1, L2 | 636/636；model_pred 可用 636/636；排序稳定 | L0, L1, L2 | 97/636 |
| MMKE-entity | LLaVA-1.5 | L0, L1, L4 | 636/636；model_pred 可用 636/636；排序稳定 | L0, L1, L2 | 632/636 |
| MMKE-entity | Qwen2.5-VL | L1, L0, L20 | 360/636；model_pred 可用 636/636；排序稳定 | L1, L0, L2 | 9/636；low_confidence |
| MMKE-entity | PaliGemma | L7, L6, L5 | 559/636；model_pred 可用 636/636；排序稳定 | L0, L2, L1 | 125/636 |
| MMKE-entity | SmolVLM | L0, L1, L2 | 631/636；model_pred 可用 636/636；排序稳定 | L15, L18, L16 | 544/636 |

另有 **MMKE-entity / Qwen2.5-VL 的 alt 多噪声多种子补算**：Top-3 为 L1, L0, L2，有效样本 43/636，状态 `low_valid_coverage`。这不是 21 组完整新版，单独保留，不覆盖上表的同版本序列。

## 3. Perturb-KL：当前为 alt 序列条件版

现有定位归档和脚本仅核实到 alt 版，没有 model_pred 版。实际扰动的是各层视觉 token 隐状态；在完整 alt 序列的 teacher-forcing 上下文及答案位置比较干净/扰动输出的全词表分布 KL，**不是直接扰动 alt 文本，也不是仅计算 alt token 的概率差**。当前按 `score_kl_robust` 排名（四种噪声强度×三次重复），直接选择该层，不做 Pre 偏移。

| 数据集 | 模型 | Perturb-KL-alt Top-3 | 有效样本/总量 |
|---|---|---|---|
| EVQA-pilot500 | BLIP2 | L3, L4, L2 | 500/500 |
| EVQA-pilot500 | InstructBLIP | L2, L3, L4 | 500/500 |
| EVQA-pilot500 | MiniGPT-4 | L0, L1, L2 | 500/500 |
| EVQA-pilot500 | LLaVA-1.5 | L0, L1, L2 | 500/500 |
| EVQA-pilot500 | Qwen2.5-VL | L0, L1, L2 | 500/500 |
| EVQA-pilot500 | PaliGemma | L5, L7, L6 | 500/500 |
| EVQA-pilot500 | SmolVLM | L1, L2, L0 | 500/500 |
| MMKE-visual | BLIP2 | L3, L4, L2 | 214/214 |
| MMKE-visual | InstructBLIP | L2, L3, L5 | 214/214 |
| MMKE-visual | MiniGPT-4 | L0, L1, L2 | 214/214 |
| MMKE-visual | LLaVA-1.5 | L0, L1, L2 | 214/214 |
| MMKE-visual | Qwen2.5-VL | L0, L13, L14 | 214/214 |
| MMKE-visual | PaliGemma | L7, L5, L6 | 214/214 |
| MMKE-visual | SmolVLM | L1, L4, L0 | 214/214 |
| MMKE-entity | BLIP2 | L3, L2, L4 | 636/636 |
| MMKE-entity | InstructBLIP | L5, L4, L3 | 636/636 |
| MMKE-entity | MiniGPT-4 | L0, L1, L2 | 636/636 |
| MMKE-entity | LLaVA-1.5 | L0, L1, L2 | 636/636 |
| MMKE-entity | Qwen2.5-VL | L0, L1, L2 | 636/636 |
| MMKE-entity | PaliGemma | L7, L5, L6 | 636/636 |
| MMKE-entity | SmolVLM | L0, L1, L2 | 636/636 |

## 4. SaLEM：当前为新知识 alt 版

现有归档和执行脚本只核实到 `target_new/alt` 版，没有旧知识 `model_pred` 版。按样本计算目标损失对配置指定 MLP/FFN 模块参数的梯度绝对值均值，再跨样本平均；对应字段 `layer_score`。参数模块范围遵从该实验的 p_track 配置，不等同于假定所有方法都对同一参数集合求梯度。

| 数据集 | 模型 | SaLEM-alt Top-3 | 有效样本/总量 |
|---|---|---|---|
| EVQA-pilot500 | BLIP2 | L0, L18, L19 | 500/500 |
| EVQA-pilot500 | InstructBLIP | L0, L18, L19 | 500/500 |
| EVQA-pilot500 | MiniGPT-4 | L8, L9, L10 | 500/500 |
| EVQA-pilot500 | LLaVA-1.5 | L7, L6, L5 | 500/500 |
| EVQA-pilot500 | Qwen2.5-VL | L11, L14, L12 | 500/500 |
| EVQA-pilot500 | PaliGemma | L8, L7, L9 | 500/500 |
| EVQA-pilot500 | SmolVLM | L9, L8, L7 | 500/500 |
| MMKE-visual | BLIP2 | L0, L18, L19 | 214/214 |
| MMKE-visual | InstructBLIP | L18, L17, L19 | 214/214 |
| MMKE-visual | MiniGPT-4 | L31, L5, L8 | 214/214 |
| MMKE-visual | LLaVA-1.5 | L7, L8, L9 | 214/214 |
| MMKE-visual | Qwen2.5-VL | L12, L11, L14 | 214/214 |
| MMKE-visual | PaliGemma | L10, L8, L9 | 214/214 |
| MMKE-visual | SmolVLM | L9, L8, L0 | 214/214 |
| MMKE-entity | BLIP2 | L0, L18, L30 | 636/636 |
| MMKE-entity | InstructBLIP | L18, L17, L19 | 636/636 |
| MMKE-entity | MiniGPT-4 | L31, L22, L24 | 636/636 |
| MMKE-entity | LLaVA-1.5 | L23, L22, L24 | 636/636 |
| MMKE-entity | Qwen2.5-VL | L15, L14, L13 | 636/636 |
| MMKE-entity | PaliGemma | L17, L16, L13 | 636/636 |
| MMKE-entity | SmolVLM | L0, L1, L6 | 636/636 |

## 5. LGA：模型参数梯度与视觉表征梯度

两版均使用 old=model_pred、new=alt 的有符号梯度内积。参数版在 MLP/FFN 权重参数空间计算；视觉版在候选插入接口的视觉隐状态/虚拟增量 ΔHᵥ 上计算，**不是对 adapter 权重求梯度，也没有预训练 adapter**。同组各层样本数一致时，内积均值与论文求和的排名及 Tukey 保留集合相同。

视觉主公式直接读取 `S_v_dot = E[g_old·g_new]`。不能用 `E[cos]×E[旧范数]×E[新范数]` 代替。

| 数据集 | 模型 | 参数 Raw Top-3 | 参数 Tukey Top-3 | 视觉 Raw Top-3 | 视觉 Tukey Top-3 | 参数/视觉有效样本 |
|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2 | L0, L1, L3 | L4, L16, L18 | L0, L1, L2 | L5, L6, L7 | 404 / 465 |
| EVQA-pilot500 | InstructBLIP | L2, L0, L1 | L17, L18, L20 | L1, L0, L11 | L11, L9, L10 | 345 / 500 |
| EVQA-pilot500 | MiniGPT-4 | L29, L25, L22 | L29, L25, L22 | L8, L18, L16 | L18, L16, L17 | 499 / 499 |
| EVQA-pilot500 | LLaVA-1.5 | L24, L25, L26 | L24, L25, L26 | L31†, L30, L29 | L31†, L30, L29 | 374 / 500 |
| EVQA-pilot500 | Qwen2.5-VL | L2, L30, L1 | L3, L10, L6 | L6, L5, L7 | L6, L5, L7 | 493 / 500 |
| EVQA-pilot500 | PaliGemma | L17, L7, L0 | L7, L0, L8 | L5, L4, L3 | L5, L4, L3 | 286 / 500 |
| EVQA-pilot500 | SmolVLM | L22, L21, L20 | L22, L21, L20 | L23†, L22, L21 | L23†, L22, L21 | 499 / 500 |
| MMKE-visual | BLIP2 | L0, L1, L3 | L18, L16, L17 | L4, L3, L2 | L7, L8, L9 | 172 / 175 |
| MMKE-visual | InstructBLIP | L2, L0, L4 | L17, L20, L18 | L1, L0, L3 | L1, L0, L3 | 214 / 214 |
| MMKE-visual | MiniGPT-4 | L0, L1, L3 | L0, L1, L3 | L31†, L30, L29 | L30, L29, L28 | 214 / 214 |
| MMKE-visual | LLaVA-1.5 | L24, L22, L27 | L24, L22, L27 | L31†, L30, L29 | L31†, L30, L29 | 214 / 214 |
| MMKE-visual | Qwen2.5-VL | L2, L30, L1 | L3, L6, L10 | L0, L1, L2 | L2, L3, L4 | 214 / 214 |
| MMKE-visual | PaliGemma | L17, L0, L7 | L7, L8, L10 | L5, L4, L3 | L2, L1, L6 | 214 / 214 |
| MMKE-visual | SmolVLM | L1, L7, L6 | L6, L8, L5 | L0, L1, L2 | L0, L1, L2 | 214 / 214 |
| MMKE-entity | BLIP2 | L16, L13, L18 | L16, L13, L18 | L31†, L29, L30 | L31†, L29, L30 | 289 / 284 |
| MMKE-entity | InstructBLIP | L2, L28, L0 | L1, L17, L20 | L1, L0, L3 | L1, L0, L3 | 636 / 636 |
| MMKE-entity | MiniGPT-4 | L4, L3, L6 | L7, L8, L14 | L31†, L30, L29 | L29, L28, L25 | 636 / 636 |
| MMKE-entity | LLaVA-1.5 | L1, L9, L7 | L9, L7, L8 | L31†, L29, L21 | L31†, L29, L21 | 636 / 636 |
| MMKE-entity | Qwen2.5-VL | L2, L30, L1 | L6, L3, L10 | L0, L1, L2 | L0, L1, L2 | 636 / 636 |
| MMKE-entity | PaliGemma | L17, L16, L7 | L7, L8, L13 | L5, L4, L3 | L3, L2, L6 | 636 / 636 |
| MMKE-entity | SmolVLM | L1, L7, L0 | L0, L6, L8 | L0, L1, L2 | L2, L3, L4 | 636 / 636 |

MMKE-entity / BLIP2 的视觉梯度仅覆盖 284/636（44.65%），原归档标记 low_coverage；该组的 Ours 和视觉 LGA 消融也使用同一批样本，保留推荐但须注明低覆盖，不能当作全量定位。参数 LGA 另有自己的有效样本集合。

## 6. VisEdit：两种目标的全层贡献度与 Pre Top-3

贡献度取未经平滑的 `max(0, attn_mean)+max(0, mlp_mean)`，按高→低列出所有层，同分沿用原始 `rank_positive`。Pre 候选按三层滑动均值，阈值 mean+0.5×std（ddof=0），选最长高贡献连续区；等长选贡献和更大者，再取更浅者。若该区始于 s，则推荐 s−1、s−2、s−3，到 L0 为止。

alt：EVQA 为新答案首 token；MMKE-entity 为 alt 实体锚点；MMKE-visual 为新目标相关的视觉语义 KeyToken。model_pred：当前只存在 EVQA 的模型下一 token argmax 版，**不是完整旧答案序列**。MMKE 的 model_pred 两表共十四组仍待补；现存数据集 pred 字段版另列附录 A，不能冒充 model_pred。

### 6.1.1 EVQA-pilot500 / alt

| 模型 | Pre Top-3 | 全部层贡献度排序（高→低） | 目标 token 口径 |
|---|---|---|---|
| BLIP2 | L20, L19, L18 | L25, L24, L26, L29, L22, L27, L23, L28, L20, L30, L15, L21, L17, L16, L18, L5, L11, L8, L9, L13, L12, L31, L19, L14, L10, L6, L4, L7, L0, L2, L3, L1 | alt_first_token |
| InstructBLIP | L28, L27, L26 | L30, L31, L28, L22, L29, L27, L2, L17, L26, L5, L16, L23, L12, L6, L10, L9, L24, L4, L21, L19, L25, L0, L1, L13, L14, L20, L18, L11, L15, L7, L3, L8 | alt_first_token |
| MiniGPT-4 | L26, L25, L24 | L28, L31, L30, L27, L25, L12, L26, L29, L2, L22, L16, L4, L5, L10, L20, L0, L13, L1, L15, L19, L23, L24, L21, L14, L9, L6, L3, L18, L17, L7, L8, L11 | alt_first_token |
| LLaVA-1.5 | L28, L27, L26 | L30, L31, L29, L28, L27, L25, L26, L6, L7, L10, L16, L1, L11, L2, L13, L18, L3, L24, L5, L17, L12, L14, L22, L21, L4, L9, L15, L20, L19, L0, L8, L23 | alt_first_token |
| Qwen2.5-VL | L29, L28, L27 | L31, L35, L26, L34, L33, L30, L32, L28, L16, L29, L10, L27, L6, L24, L1, L8, L18, L22, L11, L12, L17, L14, L25, L19, L5, L23, L9, L13, L3, L21, L2, L15, L20, L4, L7, L0 | alt_first_token |
| PaliGemma | L12, L11, L10 | L15, L14, L12, L16, L17, L13, L8, L10, L11, L9, L6, L7, L1, L0, L4, L5, L3, L2 | alt_first_token |
| SmolVLM | L17, L16, L15 | L22, L19, L21, L18, L23, L20, L17, L16, L15, L8, L10, L14, L1, L12, L13, L11, L4, L9, L2, L3, L6, L5, L7, L0 | alt_first_token |

### 6.1.2 EVQA-pilot500 / model_pred

| 模型 | Pre Top-3 | 全部层贡献度排序（高→低） | 目标 token 口径 |
|---|---|---|---|
| BLIP2 | L21, L20, L19 | L26, L25, L27, L22, L24, L29, L23, L28, L20, L15, L17, L16, L10, L8, L30, L18, L12, L5, L21, L11, L7, L14, L9, L0, L6, L13, L19, L2, L4, L31, L1, L3 | base_model_next_token_argmax |
| InstructBLIP | L17, L16, L15 | L30, L20, L23, L21, L18, L26, L28, L19, L27, L24, L25, L16, L22, L17, L14, L31, L29, L15, L3, L13, L12, L4, L10, L2, L5, L9, L11, L1, L7, L0, L6, L8 | base_model_next_token_argmax |
| MiniGPT-4 | L24, L23, L22 | L26, L30, L25, L20, L31, L19, L22, L28, L29, L18, L21, L23, L27, L13, L15, L14, L17, L12, L16, L24, L4, L0, L3, L10, L1, L2, L6, L8, L9, L5, L11, L7 | base_model_next_token_argmax |
| LLaVA-1.5 | L26, L25, L24 | L28, L30, L27, L31, L29, L24, L26, L20, L22, L19, L21, L17, L16, L25, L18, L23, L15, L13, L9, L7, L14, L6, L10, L4, L12, L1, L8, L11, L2, L3, L5, L0 | base_model_next_token_argmax |
| Qwen2.5-VL | L28, L27, L26 | L31, L30, L34, L32, L33, L29, L26, L35, L27, L28, L25, L10, L24, L23, L16, L19, L5, L8, L6, L11, L2, L22, L17, L14, L3, L15, L21, L12, L9, L13, L4, L18, L20, L7, L1, L0 | base_model_next_token_argmax |
| PaliGemma | L11, L10, L9 | L13, L15, L16, L14, L12, L17, L10, L11, L9, L8, L7, L6, L3, L2, L5, L4, L0, L1 | base_model_next_token_argmax |
| SmolVLM | L18, L17, L16 | L22, L21, L23, L20, L16, L18, L19, L17, L15, L8, L10, L14, L1, L13, L12, L11, L4, L9, L6, L2, L7, L5, L3, L0 | base_model_next_token_argmax |

### 6.2.1 MMKE-visual / alt

| 模型 | Pre Top-3 | 全部层贡献度排序（高→低） | 目标 token 口径 |
|---|---|---|---|
| BLIP2 | L26, L25, L24 | L28, L30, L27, L29, L31, L21, L14, L18, L5, L4, L15, L24, L17, L20, L25, L22, L23, L19, L11, L8, L16, L6, L10, L9, L12, L7, L26, L2, L13, L1, L3, L0 | m_rel_ans_or_rel_ans_visual_semantic |
| InstructBLIP | L28, L27, L26 | L30, L31, L22, L25, L27, L28, L29, L9, L10, L12, L2, L17, L11, L26, L5, L6, L0, L4, L16, L19, L1, L14, L23, L24, L15, L20, L13, L8, L21, L18, L3, L7 | m_rel_ans_or_rel_ans_visual_semantic |
| MiniGPT-4 | L26, L25, L24 | L28, L31, L27, L16, L30, L25, L22, L20, L29, L10, L4, L15, L5, L0, L2, L12, L24, L9, L13, L19, L14, L26, L21, L7, L1, L18, L23, L11, L6, L17, L3, L8 | m_rel_ans_or_rel_ans_visual_semantic |
| LLaVA-1.5 | L28, L27, L26 | L30, L31, L29, L25, L28, L6, L27, L26, L1, L10, L2, L3, L7, L24, L16, L15, L18, L8, L0, L21, L4, L11, L13, L17, L22, L12, L20, L19, L14, L9, L5, L23 | m_rel_ans_or_rel_ans_visual_semantic |
| Qwen2.5-VL | L28, L27, L26 | L35, L34, L30, L33, L32, L31, L10, L3, L6, L13, L16, L5, L28, L24, L1, L22, L21, L12, L17, L11, L19, L9, L26, L4, L7, L14, L15, L25, L27, L8, L20, L18, L23, L29, L2, L0 | m_rel_ans_or_rel_ans_visual_semantic |
| PaliGemma | L14, L13, L12 | L17, L16, L15, L6, L14, L13, L9, L0, L7, L5, L4, L3, L11, L10, L2, L1, L12, L8 | m_rel_ans_or_rel_ans_visual_semantic |
| SmolVLM | L18, L17, L16 | L23, L19, L22, L20, L21, L8, L18, L16, L13, L12, L11, L14, L6, L10, L17, L4, L15, L7, L1, L2, L9, L5, L3, L0 | m_rel_ans_or_rel_ans_visual_semantic |

### 6.2.2 MMKE-visual / model_pred

| 模型 | Pre Top-3 | 全部层贡献度排序（高→低） | 目标 token 口径 |
|---|---|---|---|
| BLIP2 | 待补 | 待补 | 无该目标的原始贡献度 |
| InstructBLIP | 待补 | 待补 | 无该目标的原始贡献度 |
| MiniGPT-4 | 待补 | 待补 | 无该目标的原始贡献度 |
| LLaVA-1.5 | 待补 | 待补 | 无该目标的原始贡献度 |
| Qwen2.5-VL | 待补 | 待补 | 无该目标的原始贡献度 |
| PaliGemma | 待补 | 待补 | 无该目标的原始贡献度 |
| SmolVLM | 待补 | 待补 | 无该目标的原始贡献度 |

### 6.3.1 MMKE-entity / alt

| 模型 | Pre Top-3 | 全部层贡献度排序（高→低） | 目标 token 口径 |
|---|---|---|---|
| BLIP2 | L22, L21, L20 | L26, L24, L28, L23, L27, L25, L30, L29, L22, L20, L19, L31, L8, L17, L14, L21, L6, L15, L16, L12, L9, L10, L7, L11, L4, L18, L2, L5, L13, L3, L0, L1 | alt_entity_anchor |
| InstructBLIP | L28, L27, L26 | L30, L31, L29, L10, L28, L25, L27, L16, L17, L9, L2, L22, L12, L26, L14, L5, L19, L20, L6, L24, L0, L11, L1, L13, L21, L15, L23, L4, L18, L7, L8, L3 | alt_entity_anchor |
| MiniGPT-4 | L25, L24, L23 | L28, L31, L27, L16, L25, L30, L20, L26, L19, L22, L13, L23, L29, L2, L15, L5, L24, L9, L10, L21, L14, L6, L0, L12, L17, L4, L18, L1, L7, L11, L3, L8 | alt_entity_anchor |
| LLaVA-1.5 | L28, L27, L26 | L30, L25, L31, L29, L27, L28, L6, L10, L7, L26, L1, L3, L12, L2, L8, L0, L18, L13, L21, L24, L4, L15, L20, L22, L14, L11, L9, L5, L23, L16, L17, L19 | alt_entity_anchor |
| Qwen2.5-VL | L29, L28, L27 | L31, L33, L32, L34, L30, L28, L22, L6, L35, L10, L12, L3, L1, L9, L27, L17, L16, L18, L19, L14, L20, L13, L5, L8, L26, L2, L11, L24, L29, L21, L4, L7, L25, L15, L23, L0 | alt_entity_anchor |
| PaliGemma | L12, L11, L10 | L14, L15, L12, L16, L17, L13, L0, L1, L7, L6, L5, L4, L11, L10, L2, L3, L8, L9 | alt_entity_anchor |
| SmolVLM | L18, L17, L16 | L20, L21, L19, L22, L23, L18, L14, L17, L8, L4, L2, L1, L15, L11, L10, L16, L13, L5, L6, L12, L0, L9, L3, L7 | alt_entity_anchor |

### 6.3.2 MMKE-entity / model_pred

| 模型 | Pre Top-3 | 全部层贡献度排序（高→低） | 目标 token 口径 |
|---|---|---|---|
| BLIP2 | 待补 | 待补 | 无该目标的原始贡献度 |
| InstructBLIP | 待补 | 待补 | 无该目标的原始贡献度 |
| MiniGPT-4 | 待补 | 待补 | 无该目标的原始贡献度 |
| LLaVA-1.5 | 待补 | 待补 | 无该目标的原始贡献度 |
| Qwen2.5-VL | 待补 | 待补 | 无该目标的原始贡献度 |
| PaliGemma | 待补 | 待补 | 无该目标的原始贡献度 |
| SmolVLM | 待补 | 待补 | 无该目标的原始贡献度 |

## 7. Ours 主公式及视觉 LGA 消融：Raw / Tukey

记每个样本的旧、新梯度范数为 aᵢ、bᵢ，方向余弦为 cᵢ；E 表示先在样本内计算后取均值。C=`S_v_cos`=E[cᵢ]，N=`S_v_new_norm`=E[bᵢ]，J=`S_v_joint_norm`=E[aᵢbᵢ]。

| 版本 | 精确定义 | 现有数据可否计算 |
|---|---|---|
| Ours 主公式 | abs(C) × N（无深度） | 可计算；保持既定层级聚合公式 |
| Ours 去方向 | N | 可计算 |
| Ours 去强度 | abs(C) | 可计算 |
| 视觉 LGA 主公式 | E[g_old·g_new] ≈ E[aᵢbᵢcᵢ] | 可计算；直接用原始 S_v_dot，≈ 仅因余弦分母 epsilon |
| 视觉 LGA 去旧强度 | E[bᵢcᵢ] | 待补：未保存该交叉统计 |
| 视觉 LGA 去新强度 | E[aᵢcᵢ] | 待补：未保存该交叉统计 |
| 视觉 LGA 去方向 | E[aᵢbᵢ] = J | 可计算；不是 E[aᵢ]×E[bᵢ] |

Ours 主公式中的 `abs(E[c])×E[b]` 不能改写成 `E[abs(c)×b]`。LGA 去单侧强度也不能用 C×N、C×旧范数均值替代；这些是不同的统计量。已审计服务器二十一组逐样本日志，均只保存样本标识、目标、loss 和视觉范围，没有范数/余弦交叉项。因此下方待补是缺少可识别的数据，不是计算得到空 Top-3，也不是 0 分。

### 7.1. EVQA-pilot500

Ours 三版：

| 模型 | 主公式 Raw | 主公式 Tukey | 去方向 Raw | 去方向 Tukey | 去强度 Raw | 去强度 Tukey |
|---|---|---|---|---|---|---|
| BLIP2 | L0, L1, L2 | L1, L2, L3 | L0, L1, L2 | L1, L2, L3 | L0, L1, L2 | L0, L1, L2 |
| InstructBLIP | L1, L0, L11 | L1, L0, L11 | L1, L0, L9 | L1, L0, L9 | L1, L0, L17 | L17, L18, L15 |
| MiniGPT-4 | L18, L19, L16 | L18, L19, L16 | L0, L1, L2 | L0, L1, L2 | L30, L29, L18 | L30, L29, L18 |
| LLaVA-1.5 | L0, L1, L2 | L0, L1, L2 | L0, L1, L3 | L0, L1, L3 | L30, L26, L27 | L25, L28, L24 |
| Qwen2.5-VL | L21, L19, L17 | L21, L19, L17 | L0, L1, L2 | L0, L1, L2 | L24, L23, L27 | L24, L23, L27 |
| PaliGemma | L5, L4, L3 | L5, L4, L3 | L5, L4, L3 | L5, L4, L3 | L16, L5, L4 | L16, L5, L4 |
| SmolVLM | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L1, L2, L3 | L14, L12, L13 | L14, L12, L13 |

视觉 LGA 四版：

| 模型 | LGA Raw | LGA Tukey | 去方向 Raw | 去方向 Tukey | 去旧强度 Raw / Tukey | 去新强度 Raw / Tukey |
|---|---|---|---|---|---|---|
| BLIP2 | L0, L1, L2 | L5, L6, L7 | L0, L1, L2 | L5, L6, L7 | 待补 / 待补 | 待补 / 待补 |
| InstructBLIP | L1, L0, L11 | L11, L9, L10 | L1, L0, L11 | L11, L9, L10 | 待补 / 待补 | 待补 / 待补 |
| MiniGPT-4 | L8, L18, L16 | L18, L16, L17 | L0, L1, L2 | L0, L1, L2 | 待补 / 待补 | 待补 / 待补 |
| LLaVA-1.5 | L31†, L30, L29 | L31†, L30, L29 | L6, L5, L7 | L6, L5, L7 | 待补 / 待补 | 待补 / 待补 |
| Qwen2.5-VL | L6, L5, L7 | L6, L5, L7 | L0, L1, L2 | L0, L1, L2 | 待补 / 待补 | 待补 / 待补 |
| PaliGemma | L5, L4, L3 | L5, L4, L3 | L4, L5, L3 | L4, L5, L3 | 待补 / 待补 | 待补 / 待补 |
| SmolVLM | L23†, L22, L21 | L23†, L22, L21 | L0, L1, L2 | L3, L4, L5 | 待补 / 待补 | 待补 / 待补 |

### 7.2. MMKE-visual

Ours 三版：

| 模型 | 主公式 Raw | 主公式 Tukey | 去方向 Raw | 去方向 Tukey | 去强度 Raw | 去强度 Tukey |
|---|---|---|---|---|---|---|
| BLIP2 | L0, L1, L2 | L5, L6, L7 | L0, L1, L2 | L6, L7, L8 | L11, L5, L4 | L11, L5, L4 |
| InstructBLIP | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | L30, L29, L27 | L25, L24, L1 |
| MiniGPT-4 | L9, L10, L11 | L10, L11, L15 | L0, L1, L2 | L0, L1, L2 | L29, L28, L30 | L30, L27, L26 |
| LLaVA-1.5 | L0, L3, L1 | L0, L3, L1 | L5, L0, L6 | L5, L0, L6 | L30, L29, L28 | L23, L24, L22 |
| Qwen2.5-VL | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L12, L10, L11 | L12, L10, L11 |
| PaliGemma | L5, L4, L3 | L5, L4, L3 | L4, L5, L3 | L4, L5, L3 | L5, L4, L16 | L5, L4, L16 |
| SmolVLM | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L7, L6, L5 | L7, L6, L5 |

视觉 LGA 四版：

| 模型 | LGA Raw | LGA Tukey | 去方向 Raw | 去方向 Tukey | 去旧强度 Raw / Tukey | 去新强度 Raw / Tukey |
|---|---|---|---|---|---|---|
| BLIP2 | L4, L3, L2 | L7, L8, L9 | L0, L1, L2 | L7, L8, L9 | 待补 / 待补 | 待补 / 待补 |
| InstructBLIP | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | 待补 / 待补 | 待补 / 待补 |
| MiniGPT-4 | L31†, L30, L29 | L30, L29, L28 | L0, L1, L2 | L0, L1, L2 | 待补 / 待补 | 待补 / 待补 |
| LLaVA-1.5 | L31†, L30, L29 | L31†, L30, L29 | L5, L6, L4 | L5, L6, L4 | 待补 / 待补 | 待补 / 待补 |
| Qwen2.5-VL | L0, L1, L2 | L2, L3, L4 | L0, L1, L2 | L1, L2, L3 | 待补 / 待补 | 待补 / 待补 |
| PaliGemma | L5, L4, L3 | L2, L1, L6 | L4, L5, L3 | L3, L2, L6 | 待补 / 待补 | 待补 / 待补 |
| SmolVLM | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L3, L4, L5 | 待补 / 待补 | 待补 / 待补 |

### 7.3. MMKE-entity

Ours 三版：

| 模型 | 主公式 Raw | 主公式 Tukey | 去方向 Raw | 去方向 Tukey | 去强度 Raw | 去强度 Tukey |
|---|---|---|---|---|---|---|
| BLIP2 | L0, L1, L2 | L16, L17, L18 | L0, L1, L2 | L7, L8, L9 | L0, L1, L2 | L2, L3, L4 |
| InstructBLIP | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | L29, L30, L27 | L25, L24, L23 |
| MiniGPT-4 | L27, L28, L26 | L27, L28, L26 | L0, L1, L2 | L0, L1, L2 | L29, L28, L30 | L30, L27, L26 |
| LLaVA-1.5 | L13, L11, L12 | L14, L15, L0 | L0, L1, L6 | L0, L1, L6 | L30, L29, L13 | L13, L28, L12 |
| Qwen2.5-VL | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L12, L11, L10 | L12, L11, L10 |
| PaliGemma | L5, L4, L3 | L5, L4, L3 | L5, L4, L3 | L5, L4, L3 | L5, L4, L16 | L5, L4, L16 |
| SmolVLM | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L1, L2, L3 | L6, L7, L5 | L6, L7, L5 |

视觉 LGA 四版：

| 模型 | LGA Raw | LGA Tukey | 去方向 Raw | 去方向 Tukey | 去旧强度 Raw / Tukey | 去新强度 Raw / Tukey |
|---|---|---|---|---|---|---|
| BLIP2 | L31†, L29, L30 | L31†, L29, L30 | L0, L1, L2 | L7, L8, L9 | 待补 / 待补 | 待补 / 待补 |
| InstructBLIP | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | L1, L0, L3 | 待补 / 待补 | 待补 / 待补 |
| MiniGPT-4 | L31†, L30, L29 | L29, L28, L25 | L0, L1, L2 | L0, L1, L2 | 待补 / 待补 | 待补 / 待补 |
| LLaVA-1.5 | L31†, L29, L21 | L31†, L29, L21 | L6, L5, L0 | L6, L5, L0 | 待补 / 待补 | 待补 / 待补 |
| Qwen2.5-VL | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | L0, L1, L2 | 待补 / 待补 | 待补 / 待补 |
| PaliGemma | L5, L4, L3 | L3, L2, L6 | L5, L4, L3 | L5, L4, L3 | 待补 / 待补 | 待补 / 待补 |
| SmolVLM | L0, L1, L2 | L2, L3, L4 | L0, L1, L2 | L3, L4, L5 | 待补 / 待补 | 待补 / 待补 |

### 7.4 每组、每公式的剔除层

以下列出全部 Tukey 剔除层，不只列原 Top-3 中被替换的层；Q1/Q3、上下界、保留层及完整精度分数见附录 B 的可机读文件。

| 数据集 | 模型 | 参数 LGA | 视觉 LGA | Ours 主公式 | Ours 去方向 | Ours 去强度 | 视觉 LGA 去方向 |
|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2 | L0, L1, L3 | L0, L1, L2, L3, L4 | L0 | L0 | L31 | L0, L1, L2, L3, L4 |
| EVQA-pilot500 | InstructBLIP | L0, L1, L2, L4 | L0, L1 | — | — | L0, L1, L25, L26, L27, L28, L29, L30, L31 | L0, L1 |
| EVQA-pilot500 | MiniGPT-4 | L2, L31 | L8, L24 | — | — | — | — |
| EVQA-pilot500 | LLaVA-1.5 | L1 | — | — | — | L26, L27, L30, L31 | — |
| EVQA-pilot500 | Qwen2.5-VL | L1, L2, L30 | — | — | — | — | — |
| EVQA-pilot500 | PaliGemma | L17 | — | — | — | L17 | — |
| EVQA-pilot500 | SmolVLM | L1, L7 | L0, L1 | — | L0 | — | L0, L1, L2 |
| MMKE-visual | BLIP2 | L0, L1, L2, L3, L4, L5, L6, L7 | L0, L1, L2, L3, L4, L5 | L0, L1, L2, L3, L4 | L0, L1, L2, L3, L4, L5 | — | L0, L1, L2, L3, L4, L5, L6 |
| MMKE-visual | InstructBLIP | L0, L1, L2, L4, L28, L30, L31 | — | L31 | L31 | L26, L27, L28, L29, L30, L31 | — |
| MMKE-visual | MiniGPT-4 | L2, L30, L31 | L31 | L9, L30, L31 | — | L28, L29, L31 | — |
| MMKE-visual | LLaVA-1.5 | L1, L31 | — | — | — | L25, L26, L27, L28, L29, L30, L31 | — |
| MMKE-visual | Qwen2.5-VL | L1, L2, L30 | L0, L1 | — | — | L32, L34, L35 | L0 |
| MMKE-visual | PaliGemma | L0, L17 | L3, L4, L5 | — | — | L17 | L4, L5 |
| MMKE-visual | SmolVLM | L1, L7, L23 | — | — | — | — | L0, L1, L2 |
| MMKE-entity | BLIP2 | L0, L1, L2, L3, L4, L5, L6 | L0, L1, L2, L3, L4, L5, L6 | L0, L1, L2, L3, L4, L5 | L0, L1, L2, L3, L4, L5, L6 | L0, L1 | L0, L1, L2, L3, L4, L5, L6 |
| MMKE-entity | InstructBLIP | L0, L2, L4, L28, L30, L31 | — | L30, L31 | L31 | L26, L27, L28, L29, L30, L31 | — |
| MMKE-entity | MiniGPT-4 | L0, L1, L2, L3, L4, L5, L6, L28, L29, L30, L31 | L30, L31 | L31 | L31 | L28, L29 | — |
| MMKE-entity | LLaVA-1.5 | L1 | — | L9, L10, L11, L12, L13 | — | L29, L30 | — |
| MMKE-entity | Qwen2.5-VL | L1, L2, L30 | — | — | — | L35 | — |
| MMKE-entity | PaliGemma | L16, L17 | L4, L5 | — | — | L17 | — |
| MMKE-entity | SmolVLM | L1, L7 | L0, L1 | — | L0 | — | L0, L1, L2 |

## 附录 A. 已存在的 VisEdit 数据集 pred 字段版（历史补充）

这是当前 MMKE 旧侧归档实际保存的版本：`key_mode=pred`、数据集 pred 首 token。它既不是新知识 alt，也不是模型实际 model_pred；与主表的 MMKE 新侧 KeyToken 还存在 token 规则差异。仅供完整追溯，单独报告，不代填主表的 model_pred 缺项。

| 数据集 | 模型 | Pre Top-3 | 全部层贡献度排序（高→低） |
|---|---|---|---|
| MMKE-visual | BLIP2 | L23, L22, L21 | L25, L10, L29, L16, L27, L7, L30, L28, L24, L8, L17, L9, L6, L31, L19, L21, L18, L20, L14, L5, L4, L11, L13, L26, L15, L12, L2, L0, L23, L22, L3, L1 |
| MMKE-visual | InstructBLIP | L2, L1, L0 | L25, L6, L17, L2, L5, L31, L4, L26, L12, L27, L9, L30, L10, L7, L19, L28, L29, L21, L13, L24, L15, L23, L22, L14, L8, L20, L0, L1, L11, L3, L16, L18 |
| MMKE-visual | MiniGPT-4 | L26, L25, L24 | L28, L31, L29, L5, L25, L30, L16, L2, L10, L23, L22, L12, L27, L24, L19, L21, L26, L15, L4, L14, L7, L6, L11, L18, L17, L13, L9, L1, L3, L8, L0, L20 |
| MMKE-visual | LLaVA-1.5 | L28, L27, L26 | L30, L31, L29, L12, L18, L5, L3, L6, L16, L25, L7, L26, L28, L2, L14, L0, L4, L17, L24, L10, L9, L15, L27, L21, L1, L13, L11, L22, L20, L8, L23, L19 |
| MMKE-visual | Qwen2.5-VL | L32, L31, L30 | L35, L34, L30, L16, L13, L33, L6, L31, L32, L11, L10, L1, L28, L18, L8, L22, L24, L19, L21, L5, L17, L27, L3, L9, L29, L26, L12, L20, L25, L2, L14, L23, L15, L7, L4, L0 |
| MMKE-visual | PaliGemma | L14, L13, L12 | L16, L17, L15, L14, L6, L12, L3, L0, L7, L5, L4, L8, L11, L10, L2, L1, L13, L9 |
| MMKE-visual | SmolVLM | L21, L20, L19 | L23, L22, L19, L16, L8, L21, L20, L17, L1, L18, L10, L12, L15, L14, L4, L11, L9, L13, L6, L3, L5, L2, L7, L0 |
| MMKE-entity | BLIP2 | L22, L21, L20 | L29, L24, L4, L27, L26, L8, L28, L23, L10, L25, L22, L20, L30, L14, L18, L31, L5, L17, L3, L19, L15, L12, L21, L16, L9, L2, L11, L6, L7, L13, L1, L0 |
| MMKE-entity | InstructBLIP | L28, L27, L26 | L30, L31, L29, L10, L28, L25, L27, L16, L17, L9, L2, L22, L12, L26, L14, L5, L19, L20, L6, L24, L0, L11, L1, L13, L21, L15, L23, L4, L18, L7, L8, L3 |
| MMKE-entity | MiniGPT-4 | L25, L24, L23 | L28, L31, L27, L16, L25, L30, L20, L26, L19, L22, L13, L23, L29, L2, L15, L5, L24, L9, L10, L21, L14, L6, L0, L12, L17, L4, L18, L1, L7, L11, L3, L8 |
| MMKE-entity | LLaVA-1.5 | L28, L27, L26 | L30, L25, L31, L29, L27, L28, L6, L10, L7, L26, L1, L3, L12, L2, L8, L0, L18, L13, L21, L24, L4, L15, L20, L22, L14, L11, L9, L5, L23, L16, L17, L19 |
| MMKE-entity | Qwen2.5-VL | L29, L28, L27 | L34, L35, L31, L33, L27, L6, L18, L25, L29, L30, L13, L5, L10, L16, L3, L17, L11, L19, L32, L12, L9, L1, L14, L20, L24, L28, L26, L7, L2, L22, L4, L8, L15, L21, L23, L0 |
| MMKE-entity | PaliGemma | L13, L12, L11 | L17, L15, L16, L10, L11, L14, L0, L1, L7, L6, L5, L4, L8, L9, L2, L3, L12, L13 |
| MMKE-entity | SmolVLM | L19, L18, L17 | L23, L21, L16, L20, L15, L19, L22, L18, L17, L8, L14, L6, L11, L12, L4, L1, L10, L13, L2, L9, L0, L7, L5, L3 |

## 附录 B. 来源、待补与复算

- VisEdit-model_pred：MMKE-visual 与 MMKE-entity 的十四个组合缺原始贡献度。
- 视觉 LGA 去旧强度、去新强度：两个版本各二十一组均缺必要交叉统计，Raw 与 Tukey 均待补；应在同一数据、目标、hook 和精度协议下补算梯度统计，不需要为定位重新训练 adapter。
- Perturb-KL、SaLEM 当前仅报告已存在的 alt 版，不虚构 model_pred 结果。
- 旧的深度加权 Ours、Perturb-KL-Pre、VisEdit FirstToken 历史表保存在原始总账备份；不混入本次指定的七类主表。

[全部推荐层 JSON](../../outputs/all_methods_recommendations_20260928/recommendations.json) · [推荐层 CSV](../../outputs/all_methods_recommendations_20260928/recommendations.csv) · [逐层分数与排名](../../outputs/all_methods_recommendations_20260928/all_layer_scores.csv) · [Tukey 阈值与剔除层](../../outputs/all_methods_recommendations_20260928/tukey_audit.csv) · [VisEdit 完整排序](../../outputs/all_methods_recommendations_20260928/visedit_full_rankings.json)

[服务器产物来源与 SHA-256](../../outputs/all_methods_recommendations_20260928/server_source_manifest.json) · [本次输入文件 SHA-256](../../outputs/all_methods_recommendations_20260928/input_sha256.json) · [逐样本日志字段核验](../../outputs/all_methods_recommendations_20260928/sample_schema_audit.json) · [复算验证](../../outputs/all_methods_recommendations_20260928/verification.json) · [原始总账备份](../../outputs/all_methods_recommendations_20260928/backups/6location_7model_3datas_top_3_5_layers_outcome.md)

在项目根目录运行 `python scripts/build_all_method_recommendations.py` 可从本次已核验的本地原始分数重建本文件及总账方法目录。需要重新读取服务器产物时，先运行 `python scripts/collect_recommendation_sources_20260928.py`；它只读服务器、写本地产物，不启动训练或修改服务器结果。
