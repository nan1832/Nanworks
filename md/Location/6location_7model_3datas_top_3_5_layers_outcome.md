# 定位方法目录与真实扫层结果

<!-- SWEEP_MAIN_SYNC_HEADER_START -->
**真实扫层结果已同步：2026-09-28 11:10:16+08:00（服务器北京时间）。** 本次将核对前遗漏的 51 条补入第 4 节，逐层表现有 433 条记录（main/stable 分开，含独立复测）。当前结果、训练核验状态及逐层来源与 [SWeeplayers.md](SWeeplayers.md) 对齐。第 3 节候选并集及方法统计仍为有日期的历史快照；不据此宣称当前 Top-3 并集总量已确定。
<!-- SWEEP_MAIN_SYNC_HEADER_END -->

**方法目录整理时间：2026-09-29T12:13:29+08:00（北京时间）。** 本次按七类重新组织方法与目标版本。全部 Top-3、VisEdit 全层贡献度排序、Ours/LGA 消融与全层 Tukey 结果统一见 [ALL_Methods_Recommends_layers.md](ALL_Methods_Recommends_layers.md)。定位统计与训练评测分别维护。

## 0. 目录结构

- 1. 统一口径与版本区别
- 2. 本次指定的七类定位方法
- 3. 历史数据集分表：冻结留档，不代表此次新候选并集或新方法比较
- 4. 已完成真实扫层结果：保留逐层 main/stable、训练预算及评测来源
- 5–6. 扫层使用方式与注意事项

## 1. 统一口径与版本区别

- 所有层号为 0-indexed。Top-3 保留分数/规则给出的先后次序，不将层号重新从小到大排列。
- alt、新旧模型响应 model_pred、数据集 pred 字段严格区分。VisEdit 的 Pre 表示高贡献区域前置候选层，不是 pred 字段。
- 正式 Ours 主公式固定为 abs(S_v_cos)×S_v_new_norm，不带深度权重；历史 Conflict/深度公式不能冒充该主公式。
- Raw 保留全部有限层分数，包括极端大值和已有有限零分；全层 Tukey 为每个组合、每个公式独立计算 Q1/Q3，剔除区间 [Q1−IQR,Q3+IQR] 外全部层后排序取 Top-3。κ=1.0，四分位数 linear，边界保留，不迭代、不回填异常层。
- 方法未计算、数据不足和排名不足三层分别标记；不以 alt 替代 model_pred，不用层均值相乘假造未保存的逐样本交叉统计。
- 本次不更新候选并集总层数和方法真实性能排名；main/stable 编辑结果继续分开，不按某层分数取较高版本。

## 2. 本次指定的七类定位方法

### 2.1 中层先验

Middle-Prior；中心 (L−1)/2，按距离升序，同距取浅层；三个数据集共用。

Top-3、来源和版本细节见 [推荐层总表第 1 节](ALL_Methods_Recommends_layers.md)。

### 2.2 CMA 因果恢复

分别报告 CMA-model_pred 与 CMA-alt v1.3，目标均为完整答案序列。两者目前噪声/种子协议也不同；Qwen/MMKE-entity 的 alt 多噪声补算独立列出，不混进旧二十一组版本。

Top-3、来源和版本细节见 [推荐层总表第 2 节](ALL_Methods_Recommends_layers.md)。

### 2.3 Perturb-KL

当前仅核实 alt 序列条件版：扰动视觉隐状态，在 alt teacher-forcing 的答案位置计算输出分布 KL，按 score_kl_robust 选层；未找到 model_pred 版。

Top-3、来源和版本细节见 [推荐层总表第 3 节](ALL_Methods_Recommends_layers.md)。

### 2.4 SaLEM

当前仅核实新知识 alt 版：样本目标损失对配置指定 MLP/FFN 参数的梯度绝对值均值，再跨样本平均；未找到旧知识 model_pred 版。

Top-3、来源和版本细节见 [推荐层总表第 4 节](ALL_Methods_Recommends_layers.md)。

### 2.5 LGA 两版

模型参数 LGA：MLP/FFN 权重梯度内积；视觉表征 LGA：候选插入位置视觉隐状态/虚拟 ΔHᵥ 梯度内积，不是 adapter 参数梯度。两版均报告 Raw/Tukey Top-3，视觉内积直接读取 E[g_old·g_new]。

Top-3、来源和版本细节见 [推荐层总表第 5 节](ALL_Methods_Recommends_layers.md)。

### 2.6 VisEdit 贡献度两版

model_pred 是基础模型对原始图文对生成的完整回答。当前 VisEdit 旧侧归因实现为 model_pred-NextTokenArgmax（首预测位置对照），不代表完整回答归因：EVQA 已有七组，MMKE 对照已核验回填 14/14 组。MMKE 每组分别提供 attn、MLP、attn+MLP 的 Top-5、最高贡献层、全层排序及 Pre Top-3，见推荐总表 6.2.2、6.3.2。VisEdit 完整回答归因尚未执行。alt 二十一组及历史十四组数据集 pred 字段版保持独立；后者见 [附录 A](ALL_Methods_Recommends_layers.md#visedit-pred-archive)。

Top-3、来源和版本细节见 [推荐层总表第 6 节](ALL_Methods_Recommends_layers.md)。

### 2.7 Ours 主公式及两种梯度空间 LGA 消融

Ours：abs(E[cos])×E[新范数]；新增带符号方向版 Ours-signed-direction=E[cos]×E[新范数]；去方向为 E[新范数]，去强度为 abs(E[cos])。新增版的 21 组 Raw/Tukey 推荐与已有编辑效果见推荐总表第 7 节。LGA 消融按最新任务同时做 MLP/FFN 权重参数版与视觉表征版：去方向为 E[旧范数×新范数]；去旧/去新分别为 E[cos×新范数] / E[cos×旧范数]，不能由层均值相乘替代。沿用各空间原数据、冻结 model_pred 答案与梯度对象严格逐样本补算，完成并通过复核后回填推荐层总表；未完成明确待补。每个版本分别列 Raw 与全层 Tukey。

Top-3、来源和版本细节见 [推荐层总表第 7 节](ALL_Methods_Recommends_layers.md)。

### 2.8 数据来源与历史保留

本次基于服务器原始层分数和本地已核验贡献度重新生成，附可重复脚本、逐层分数、过滤边界及 SHA-256。详见 [生成与验证产物](../../outputs/all_methods_recommendations_20260928/verification.json)。原第 1–2 节的历史 Top-5、Pre 消融、早期 Ours 等完整保存在 [整理前备份](../../outputs/all_methods_recommendations_20260928/backups/6location_7model_3datas_top_3_5_layers_outcome.md)。

<!-- VISUAL_TRACK_INDEX_START -->
### 2.9 补充：视觉表征余弦三版本

21/21 组已于 2026-09-29T08:37:52+0800 完成。分别报告 VisualTrack-Cos-none、-alt、-model_pred 的 Raw/Tukey Top-3、Top-5、异常层和有效样本数。推荐层见[推荐总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)，真实编辑表现及缺失候选评测见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)。沿用既定扫层快照比较；本次不重写历史候选并集或把定位补算视为新训练评测。
<!-- VISUAL_TRACK_INDEX_END -->


> **以下第 3 节是历史冻结比较，版本和候选集合未随本次方法重排重算；其中的并集数字、完成率与方法优劣不能作为本次新表结论。第 4 节真实扫层明细原样保留。**

## 3. 数据集分表

<!-- SWEEP_HISTORICAL_SCOPE_START -->
> 当前扫层结果已于 2026-09-28 同步至第4节。本节以下并集完成数、待补状态和方法比较属于原日期冻结记录，不作为当前实时进度；未确定的现行 Top-3 并集不在此次更新中给出总量。
<!-- SWEEP_HISTORICAL_SCOPE_END -->

> **2026-09-27 适用范围补注：** 本节现存七方法并集、完成数及 Best/Mean/Hit 指标保留原冻结值，其中 VisEdit 仅为 alt 版本（原名 Pre-KeyToken 或历史 Pre-FirstToken）。下文“当前/新版”是当时相对 CMA 旧版的表述，不包括本次新增 VisEdit-model_pred，也不自动包括 9 月 26 日 LGA Tukey 补正。新增版本的完整并集与性能统计需基于对应候选和实际评测另行生成。

3.1--3.4.4保留2026-08-01以前的“8方法（含Perturb-KL-Pre消融）+ 4个深度加权Ours指标并集”历史冻结口径，只用于追溯既有实验为什么被安排，**不再作为当前七方法正式比较的候选并集或待补清单**。

> **版本化权威口径：** 3.4.5保留使用历史`CMA-Direct v1.3/alt`的七方法冻结并集；3.4.6是当前使用`CMA-ModelPred-Direct`的新版七方法并集与阶段指标。两版都只包含`Middle`、`VisEdit`、`SaLEM`、`LGA`、`Perturb-KL Direct`、`Ours-Direct`、`CMA`七类方法，排除Perturb-KL Pre消融，Ours只取主公式`M_abscos_x_newn = |S_v_cos| × S_v_new_norm`；禁止跨版本混合或覆盖。

### 3.1 EVQA-pilot500

| Model | 8 方法 Top-3 并集 | 层数 | 备注 |
|---|---|---:|---|
| BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5,L17,L25,L26 | 15 | Pre 不足按现有合法层/空层处理 |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L25,L21,L22,L20 | 17 | Pre 不足按现有合法层/空层处理 |
| MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L7,L28,L30,L21,L18,L20 | 20 | Pre 不足按现有合法层/空层处理 |
| LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4,L17,L13 | 17 | Pre 不足按现有合法层/空层处理 |
| Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L3,L34,L24,L21,L22,L20,L19 | 20 | Pre 不足按现有合法层/空层处理 |
| PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L1,L4 | 12 | Pre 不足按现有合法层/空层处理 |
| SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3,L14,L13 | 18 | Pre 不足按现有合法层/空层处理 |

### 3.2 MMKE-visual

| Model | 8 方法 Top-3 并集 | 层数 | 备注 |
|---|---|---:|---|
| BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2,L30,L17,L20,L21,L22 | 18 | Pre 不足按现有合法层/空层处理 |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24,L25 | 19 | Pre 不足按现有合法层/空层处理 |
| MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L29,L28,L27 | 16 | Pre 不足按现有合法层/空层处理 |
| LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L13,L12 | 16 | Pre 不足按现有合法层/空层处理 |
| Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L9,L8,L7,L6,L22,L20,L19 | 21 | 8 方法 Top-3 去重保序 |
| PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L3,L2,L1 | 14 | Pre 不足按现有合法层/空层处理 |
| SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L15,L14 | 15 | Pre 不足按现有合法层/空层处理 |

### 3.3 MMKE-entity

| Model | 8 方法 Top-3 并集 | 层数 | 备注 |
|---|---|---:|---|
| BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L19,L25,L26,L24,L23 | 18 | Pre 不足按现有合法层/空层处理 |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22,L25 | 19 | Pre 不足按现有合法层/空层处理 |
| MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L28,L29,L27,L26 | 18 | Pre 不足按现有合法层/空层处理 |
| LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L30,L12,L18 | 18 | Pre 不足按现有合法层/空层处理 |
| Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L22,L21,L20,L26,L25 | 18 | Pre 不足按现有合法层/空层处理；CMA low_confidence 仍纳入候选 |
| PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L3,L2,L1,L0 | 15 | Pre 不足按现有合法层/空层处理 |
| SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15,L9,L14,L13 | 15 | Pre 不足按现有合法层/空层处理 |

### 3.4 待补跑层分表（第 3 节减第 4 节已完成）

本节用于继续真实扫层排队：对第 3 节每个 `dataset × model` 的 `8 方法 Top-3 并集`，扣除第 4 节已经完成 `50 epoch + minimum EMA checkpoint + eval_full.done` 的层；层序保留第 3 节并集中的去重顺序。`L18-2` 复评按 `L18` 计为已完成。

#### 3.4.1 EVQA-pilot500

| Model | 待补跑层（第 3 节减第 4 节） | 待补层数 | 第 4 节已完成命中层 | 备注 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | - | 0 | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5,L17,L25,L26 | 候选并集15/15层均已完成；2026-07-28至2026-07-29在job 3044208/GPU0补齐L14,L1,L3,L4,L2，逐层均有`train.done`、非空`selected_checkpoint.tsv`、2,093条独立正式评测的`eval_full.done`和非空`results.json`，训练与评测均`rc=0` |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L0,L18,L19,L2,L1,L3,L4,L25,L21,L22,L20 | 14 | L28,L27,L26 | 继续补跑这些层 |
| MiniGPT-4-Vicuna-7B | L15,L14,L8,L9,L10,L29,L22,L0,L1,L2,L7,L21,L20 | 13 | L16,L26,L25,L24,L28,L30,L18 | 继续补跑这些层 |
| LLaVA-v1.5-7B | L15,L16,L14,L7,L6,L5,L24,L25,L0,L1,L2,L4,L17,L13 | 14 | L28,L27,L26 | 继续补跑这些层 |
| Qwen2.5-VL-3B | - | 0 | L0,L1,L2,L3,L11,L12,L14,L16,L17,L18,L19,L20,L21,L22,L24,L27,L28,L29,L30,L34 | 候选并集20/20层均已完成；原有6个命中层加上2026-07-25核验的job 3044208/GPU0补跑14层，逐层均有`train.done`、非空`selected_checkpoint.tsv`和2,093条正式评测的`eval_full.done` |
| PaliGemma-3B | L0 | 1 | L8,L9,L7,L12,L11,L10,L17,L5,L6,L1,L4 | 主配置新增 L1,L4,L5,L6,L7,L8,L17 共7层并完成2,093条完整评测；stable L6（buffer=1）与L4（optimizer-step finite保护）已于2026-07-19补跑成功并完整评测，旧失败现场仅作历史记录。候选并集仅L0未完成；L0在stable和主配置下均数值不收敛且无selected/eval |
| SmolVLM-Instruct-1.7B | - | 0 | L0,L1,L2,L3,L7,L8,L9,L10,L11,L12,L13,L14,L15,L16,L17,L20,L21,L22 | 候选并集18/18层均已完成；原有8个命中层加上2026-07-25核验的job 3044208/GPU0补跑10层，逐层均有`train.done`、非空`selected_checkpoint.tsv`和2,093条正式评测的`eval_full.done` |

##### PaliGemma stable 异常与重跑登记（更新至2026-07-19）

后续从本表筛选重跑任务时，搜索精确标记 `RETRY_REQUIRED`。该标记只表示需要重新训练并评测，不能计入已完成层。

| Dataset | Model | Config | Layer | 重跑标记 | 最后有效进度 | 异常原因与核验 | 已有文件 | 重跑提示 | 完成验收 |
|---|---|---|---:|---|---|---|---|---|---|
| EVQA-pilot500 | PaliGemma-3B | stable | L6 | `EVAL_DONE_RETRY_BUFFER1` | 旧run在Epoch 12、214/500后停滞并由watchdog终止；2026-07-18按原配置仅将`data_buffer_size=1`从头补跑，完成50 epoch | 旧异常不是OOM，最可能是`data_buffer_size=4`下后台GPU预取/数据准备卡住；串行buffer修复后日志和step持续推进，未再卡住 | 新selected为Epoch 50，raw/EMA loss `0.423632/0.468850`；非空`selected_checkpoint.tsv`与`eval_full.done`均存在 | 已使用`vqa_eval.json`完整评测2,093条，Average `79.564`；从`RETRY_REQUIRED`移出。旧rc=143和原始checkpoint保留作历史异常记录 | 验收通过：Rel 69.94、T-Gen 69.13、M-Gen 89.83、T-Loc 100.00、M-Loc 68.92 |

说明：`rc=143` 是旧run被watchdog终止后的进程退出码，不是失败143次；旧run的原始checkpoint不能替代selected checkpoint。L6现已使用buffer=1从Epoch1重训50轮并完成正式评测，计入完成的是新run及其双完成标记，不是旧checkpoint。

#### 3.4.2 MMKE-visual

| Model | 待补跑层（第 3 节减第 4 节） | 待补层数 | 第 4 节已完成命中层 | 备注 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | - | 0 | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2,L30,L17,L20,L21,L22 | 候选并集18层均已训练并完成full eval |
| InstructBLIP-Vicuna-7B | - | 0 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24,L25 | 候选并集19层均已训练并完成full eval |
| MiniGPT-4-Vicuna-7B | - | 0 | L0,L1,L2,L3,L5,L8,L14,L15,L16,L24,L25,L26,L27,L28,L29,L31 | 候选并集16/16层均已完成。原有11层之外，job 3044841/GPU1补跑L0,L1,L2,L3,L29；5层训练均完成50 epoch流程，2026-07-30修复原选点记录缺陷后按minimum EMA loss生成非空`selected_checkpoint.tsv`，并使用独立MMKE-visual eval数据完成293条正式评测，`train.done`、`eval_full.done`和非空`results.json`齐全 |
| LLaVA-v1.5-7B | L13,L14,L16,L22,L24,L26,L27 | 7 | L0,L1,L2,L7,L8,L9,L12,L15,L28 | 2026-08-11新增L15：Epoch40/EMA 0.231111，293条独立评测Average 75.752，四项完成产物齐全并已同步本地。连同既有L0、L1、L2、L7、L8、L9、L12、L28，表内已有9层完整结果，剩余7层列于左侧 |
| Qwen2.5-VL-3B | - | 0 | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L9,L8,L7,L6,L22,L20,L19 | 候选并集21层已于2026-07-20在job 3044208/GPU0全部完成；L17复用既有selected后重新完成293条独立test/eval，其余20层从头训练并评测，结果暂存g09本地`/tmp` |
| PaliGemma-3B | L0 | 1 | L1,L2,L3,L4,L5,L6,L7,L8,L9,L10,L12,L13,L14,L17 | 2026-08-11新增正式7方法Top-3主配置L4：Epoch39/EMA 0.330234，293条独立评测Average 99.026，四项完成产物齐全并已同步本地；当前共有14个相关层完整评测。L0 stable不收敛且无selected/eval，继续标记`FAILED_NONCONVERGENT` |
| SmolVLM-Instruct-1.7B | - | 0 | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L15,L14 | 候选并集15层均已训练并完成full eval；本轮10个待补层于2026-07-19在job 3044208/GPU0完成，结果暂存g09本地`/tmp` |

#### 3.4.3 MMKE-entity

| Model | 待补跑层（第 3 节减第 4 节） | 待补层数 | 第 4 节已完成命中层 | 备注 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | - | 0 | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L19,L25,L26,L24,L23 | 候选并集18层均已训练并完成full eval |
| InstructBLIP-Vicuna-7B | - | 0 | L0,L1,L2,L3,L4,L5,L14,L15,L16,L17,L18,L19,L22,L23,L24,L25,L26,L27,L28 | 候选并集19/19层均已完成；2026-07-16补核验L2,L14,L15,L19，job 3044841/GPU1新增完成L0,L1,L3,L4,L5,L22,L23,L24,L25，逐层均有selected、954条独立eval、`eval_full.done`和嵌套完整`results.json`。L1从Epoch45 checkpoint恢复训练后完成；L25于2026-07-25 21:29完成50 epoch及正式评测，Average 47.578 |
| MiniGPT-4-Vicuna-7B | L0,L1,L3,L4,L6,L14,L16,L22,L26,L27,L29 | 11 | L2,L15,L23,L24,L25,L28,L31 | 2026-07-28服务器与备份交叉核验：L2已完成50 epoch训练流程，selected为Epoch48/step15264/EMA loss 0.280683，并使用独立MMKE-entity eval数据完整评测954条，`train.done`、非空`selected_checkpoint.tsv`、实体checkpoint、`eval_full.done`和非空`results.json`齐全，Average 75.55；原始产物已备份到login01并生成本机校验一致归档。左列11层仍待补；L16目录无完整完成标记，L27仅训练到Epoch7后暂停，均不计完成 |
| LLaVA-v1.5-7B | L0,L1,L2,L7,L9,L12,L13,L14,L15,L16,L18,L22,L23,L24,L26,L27,L28,L30 | 18 | - | 2026-07-25服务器复核：18个候选层均无完整评测；L15虽有目录但无`train.done/selected/eval_full.done/results.json`，不能计完成 |
| Qwen2.5-VL-3B | - | 0 | L0,L1,L2,L13,L14,L15,L16,L17,L18,L20,L21,L22,L25,L26,L27,L28,L29,L30 | 候选并集18层已于2026-07-23在job 3044208/GPU0全部完成；逐层均完成50 epoch训练流程并使用独立MMKE-entity eval数据完整评测954条，`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，结果暂存g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/qwen2.5-vl-3b` |
| PaliGemma-3B | - | 0 | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L3,L2,L1,L0 | stable完成14/15，主配置完成15/15；stable L12与主配置L16已于2026-07-19按稳定化方案补跑并完成954条评测。配置内仅stable L0仍不收敛；主配置L0虽完成评测但退化为Average 20.00。L16补跑训练中触发34次nonfinite梯度安全跳步，最终selected/eval完整，Average 47.044，需保留数值异常注释 |
| SmolVLM-Instruct-1.7B | - | 0 | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15,L9,L14,L13 | 候选并集15层已于2026-07-22在job 3044208/GPU0全部完成；逐层均从头训练并使用独立MMKE-entity eval数据完整评测954条，`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，结果暂存g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/smolvlm-1.7b` |

#### 3.4.4 Ours-Direct 主公式 `M_abscos_x_newn` 增量候选层

本节只登记新主公式Top-3相对第3节冻结并集新增的优先补跑层，不把这些层误记成原8方法冻结并集的历史缺层。完成验收仍要求50 epoch、minimum finite EMA selected checkpoint、对应数据集独立test/eval完整结果和`eval_full.done`；缺失结果不能按0分。

| 数据集 | 模型 | `M_abscos_x_newn` Top-3 | 原冻结并集已有完整结果 | 主公式新增待补层 | Job 3126082状态（2026-08-01） |
|---|---|---|---|---|---|
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1 | L2 | L2已于17:03完成50 epoch并使用独立293条eval完整评测；selected/eval双标记齐全 |
| MMKE-entity | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2 | - | L1已于2026-08-02 04:30完成954条独立eval，selected/eval双标记齐全，Average 72.504 |
| MMKE-entity | PaliGemma-3B | L5,L4,L3 | L5,L4,L3 | - | 主配置L4已于2026-08-02 07:40完成954条独立eval，selected/eval双标记齐全，Average 96.136；不与stable取最大值 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L9,L10,L11 | - | L9,L10,L11 | 已排在PaliGemma L4之后串行训练和独立293条eval |

说明：以上6层是为了形成新Ours主公式的真实Top-3编辑效果，不是无意义重复实验。Job 3126082上的顺序为SmolVLM L2 → BLIP2 L1 → PaliGemma L4 → MiniGPT-4 L9,L10,L11；每层完整评测后仅保留selected checkpoint并清理其他checkpoint。

### 3.4.5 正式7方法 + Ours主公式重算并集与完成状态（历史CMA-alt冻结版，原记录保留）

重算时间：2026-08-01 19:54 CST；服务器增量标记复核至2026-09-14 08:07 CST。正式方法为 `Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct(M_abscos_x_newn)`、`CMA-Direct`；不含Perturb-KL Pre消融，也不再把4个深度加权Ours指标取并集。候选层按上述方法顺序去重保序。

完成验收要求同层同时具有有效selected checkpoint、对应数据集独立test/eval完整结果和`eval_full.done`。`主:`与`stable-only:`分开登记；stable-only表示实验已经做完、无需误列为缺失，但其分数不能与主配置直接混合或取最大值。已知不收敛且无完整评测的层列入“失败”，不伪装成0分，也不自动列入原配置待补。

候选可靠性边界保持不变：EVQA的7个VisEdit组合目前仍是历史FirstToken结果而非严格KeyToken；本节正式并集冻结时使用的历史LGA有4组、历史CMA v1.3有13组为低coverage候选。它们按既有候选进入本节冻结并集，正式结论必须保留对应的`historical_firsttoken_not_strict_keytoken`或`low_candidate_coverage`标记。2026-09-12完成的21组CMA-ModelPred结果见2.8.1；在另行重算并冻结新版七方法并集前，不倒改本节已运行记录。

服务器增量已并入（更新至2026-09-13 18:02 CST）：MMKE-visual / LLaVA正式Top-3并集15层和MMKE-entity / MiniGPT-4正式Top-3并集17层均已齐全；EVQA-pilot500 / InstructBLIP正式Top-3并集15层、MiniGPT-4正式Top-3并集17层均已齐全。EVQA-pilot500 / LLaVA新增完成L5,L24,L25，现已完成L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25，共11/15层；Job 3178538当前训练L0，尚未计入完成。MMKE-entity / LLaVA新增完成L28,L27,L26,L23，现已完成L15,L16,L14,L28,L27,L26,L23，共7/17层；Job 3178423的L22已完成50 epoch并选中Epoch45 checkpoint，但尚无`eval_full.done`，因此仍列待补。以下“待补”是当前仍无完整评测且不属于已知终止失败的层。

新版CMA增量说明（2026-09-14）：Job `3178423`已补齐`EVQA/Qwen L15`、`EVQA/SmolVLM L5`、`MMKE-visual/SmolVLM L5`并完成独立eval及共享盘归档。这里的Top-3表仍冻结为历史`CMA-Direct v1.3`并集，因此不把新增CMA层倒插入下表；但三层真实结果已写入第4节，可供新版`CMA-ModelPred-Direct`七方法重算使用。其中Qwen L15和MMKE-visual SmolVLM L5同时属于下方历史Top-5并集，故Top-5完成数已据实更新。

**逐层增量回填规则：** 从本节起，不再等待整条队列结束。任一层只有在服务器同时出现非空`selected_checkpoint.tsv`、`eval_full.done`和完整独立test/eval结果后，才立即回填第4节对应模型结果行，并同步更新本节Top-3/Top-5的“已完成/待补/计数”及`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`；仅有`train.done`或仅完成训练的层不提前计为完成。异常层同步写入3.5或对应模型备注，不以0分代替缺失结果。

#### 3.4.5.1 Top-3并集：已完成、失败与待补

汇总：21组Top-3并集共317个“数据集×模型×层”实验项；已完整评测301项，已知不收敛失败2项，待补14项。该汇总按下方21行逐行求和，满足`301+2+14=317`；正式评测完成率为94.95%，计入已知终止失败后的状态覆盖率为95.58%。

| Dataset | Model | 正式7方法Top-3并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | 主:L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | - | - | 0 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | 主:L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | - | - | 0 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | 主:L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | - | - | 0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25 | 11 | - | L0,L1,L2,L4 | 4 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | 主:L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | - | - | 0 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | 主:L8,L9,L7,L12,L11,L10,L17,L5,L6,L4,L3 | 11 | L0 | - | 0 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | 主:L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | - | - | 0 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | 主:L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | - | - | 0 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | - | - | 0 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | 主:L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | - | - | 0 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | - | - | 0 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | 主:L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | - | - | 0 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3,L1,L2 | 15 | 主:L8,L9,L14,L12,L10,L17,L4；stable-only:L7,L13,L5,L6,L3,L1,L2 | 14 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | 主:L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | - | - | 0 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | 主:L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | - | - | 0 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | 主:L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | - | 0 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 17 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 10 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | 主:L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | - | - | 0 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | 主:L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | 主:L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | - | - | 0 |

##### 3.4.5.1.1 Top-3完成度汇总（2026-09-13实时核验）

| Dataset | Top-3总项 | 已完整评测 | 已知失败 | 待补 | 正式评测完成率 |
|---|---:|---:|---:|---:|---:|
| EVQA-pilot500 | 103 | 98 | 1 | 4 | 95.15% |
| MMKE-visual | 107 | 106 | 1 | 0 | 99.07% |
| MMKE-entity | 107 | 97 | 0 | 10 | 90.65% |
| **合计** | **317** | **301** | **2** | **14** | **94.95%** |

- 21个数据集×模型组合中，17组已做到正式Top-3并集每层都有完整独立评测。
- EVQA / PaliGemma与MMKE-visual / PaliGemma各有L0已知不收敛失败；它们属于终止失败，不计完整评测，也不以0分补齐。因此若按“所有候选均已有终态”统计，覆盖19/21组；若按“所有候选均有正式评测、可以做完整公平比较”统计，则为17/21组。
- 当前真正仍待完成独立评测的14项只来自两组：EVQA / LLaVA 4层（L0,L1,L2,L4）和MMKE-entity / LLaVA 10层（L22,L24,L1,L9,L7,L0,L2,L13,L11,L12）。其中EVQA / LLaVA L0正在训练；MMKE-entity / LLaVA L22已完成训练并选中checkpoint，但仍在等待显存启动正式评测，二者均未提前计为完成。

##### 3.4.5.1.2 17个完整可比组合的阶段性方法结果（2026-08-24）

计算口径：仅纳入当前17个“数据集×模型”完整可比组合；每种方法的Top-3候选层均须具有主配置的完整独立评测结果。缺失组合、stable-only结果、PaliGemma L0不收敛失败层及数值异常配置均不混入计算。四项指标定义与此前12组合版本保持一致。

| 方法 | Mean Best@3 ↑ | Mean Mean@3 ↑ | Mean Regret@3 ↓ | Hit@3 ↑ |
|---|---:|---:|---:|---:|
| **Ours-Direct** | **70.873（1）** | **68.541（1）** | **1.984（1）** | **41.2%（1）** |
| LGA-Param-Direct-AltModelPred | 69.177（2） | 65.001（6） | 3.680（2） | 11.8%（6） |
| Middle-Prior-Direct | 68.962（3） | 68.018（2） | 3.895（3） | 5.9%（7） |
| Perturb-KL-Direct-AltSeq | 68.868（4） | 67.107（3） | 3.990（4） | 17.6%（并列4） |
| CMA-Direct | 68.826（5） | 65.404（4） | 4.031（5） | 23.5%（3） |
| VisEdit-Contrib-Pre-KeyToken | 67.294（6） | 64.873（7） | 5.563（6） | 17.6%（并列4） |
| SaLEM-Alt-Direct | 67.173（7） | 65.092（5） | 5.684（7） | 35.3%（2） |

**阶段性结论：**扩展到17个完整可比组合后，**Ours-Direct仍在四项Top-3指标上全部排名第1**。相对各指标第2名，Mean Best@3高1.696分，Mean Mean@3高0.523分，Mean Regret@3低1.696分，Hit@3高5.9个百分点。

与此前12组合结果相比，Ours-Direct的四项指标由`71.365 / 68.676 / 1.703 / 50.0%`变为`70.873 / 68.541 / 1.984 / 41.2%`。新增组合提高了任务难度并使绝对值发生变化，但四项排名均保持第1。该结论属于17/21组合下的阶段性结果，剩余两组真实评测与两个PaliGemma L0终止失败不以0分填充，最终论文结论仍应在明确缺失机制与统计检验后报告。

可复核明细：`md/Location/6location_formal7_OursDirect_main_correlation_analysis.md` §5.1、`outputs/formal7_method_top3_summary_17combos_20260824.csv`、`outputs/formal7_method_top3_fair_rows_17combos_20260824.csv`、`outputs/formal7_live_main_outcomes_20260824.csv`。

#### 3.4.5.2 Top-5并集：已完成、失败与待补

汇总：21组Top-5并集共429个“数据集×模型×层”实验项；已完整评测330项，已知不收敛失败2项，待补97项。该汇总按下方21行逐行求和，满足`330+2+97=429`。Top-5待补是后续扩展比较范围，不等同于当前所有项都应立即启动。

| Dataset | Model | 正式7方法Top-5并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 | 主:L15,L16,L14,L17,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 14 | - | L13 | 1 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L22 | 24 | 主:L15,L16,L14,L28,L27,L26,L25,L0,L18,L19,L2,L1,L4,L3,L11 | 15 | - | L17,L13,L24,L20,L5,L6,L9,L10,L22 | 9 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19,L7 | 25 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L8,L9,L10,L29,L0,L1,L2,L18,L19,L7 | 18 | - | L13,L23,L5,L6,L21,L3,L4 | 7 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 22 | 主:L15,L16,L14,L28,L27,L26,L25,L24,L7,L6,L5 | 11 | - | L17,L13,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 11 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L6 | 24 | 主:L17,L18,L16,L19,L15,L29,L28,L27,L26,L11,L14,L12,L2,L30,L1,L3,L0,L21,L20 | 19 | - | L25,L13,L10,L4,L6 | 5 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4,L2 | 14 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L5,L4,L3 | 11 | L0 | L13,L2 | 2 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3 | 22 | 主:L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L22,L21,L20,L19,L1,L2,L0,L3 | 19 | - | L6,L18,L4 | 3 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L0,L18,L19,L20,L1,L3,L4,L2 | 16 | - | L13,L23,L5 | 3 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L23,L22 | 22 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L1,L3,L5,L23,L22 | 19 | - | L13,L20,L8 | 3 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 | 主:L15,L16,L14,L17,L26,L25,L24,L31,L5,L8,L9,L0,L1,L3,L2,L10,L11 | 17 | - | L13,L23,L22,L6,L4 | 5 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 | 主:L15,L16,L14,L28,L27,L26,L24,L7,L8,L9,L22,L0,L1,L2,L3 | 15 | - | L17,L13,L25,L6,L10,L23,L4,L5 | 8 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4,L7 | 22 | 主:L17,L18,L16,L19,L28,L27,L26,L12,L11,L14,L13,L2,L30,L1,L6,L0,L7 | 17 | - | L15,L25,L24,L3,L4 | 5 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 | 主:L8,L9,L10,L14,L12,L11,L17,L4；stable-only:L7,L6,L13,L5,L3,L2,L1 | 15 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2 | 18 | - | L3 | 1 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | 主:L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L23,L22 | 23 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L30,L5,L3,L1,L23,L22 | 20 | - | L13,L20,L8 | 3 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 | 主:L15,L16,L14,L25,L24,L23,L22,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | L17,L13,L21,L29 | 4 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L17,L13,L25,L24,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 18 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0 | 19 | 主:L17,L18,L16,L15,L29,L28,L27,L26,L25,L14,L13,L2,L30,L1,L0 | 15 | - | L19,L12,L6,L3 | 4 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4,L19 | 20 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L2 | 15 | - | L5,L8,L3,L4,L19 | 5 |

可复核的机器可读结果：`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`。生成逻辑：`outputs/recalculate_formal7_main_formula_unions.py`。

### 3.4.6 正式7方法 + CMA-ModelPred v2并集、完成状态与阶段指标（当前新版）

版本标识：`formal7-cma-modelpred-v2-20260914`。本节是追加的新版本，不删除、不覆盖3.4.5的历史`CMA-Direct v1.3/alt`并集及阶段指标。除CMA改为2.8.1的`CMA-ModelPred-Direct`外，其余六种方法保持原正式口径：`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct(M_abscos_x_newn)`。

完成验收仍要求对应层具有主配置或明确分栏的stable结果、有效selected checkpoint、独立test/eval完整结果和`eval_full.done`。缺失不记0分；PaliGemma L0不收敛失败单列。服务器只读复核至2026-09-14 10:59 CST：Job 3178538仍在训练EVQA/LLaVA L0，Job 3178423仍等待MMKE-entity/LLaVA L22正式评测，二者均未提前计为完成。

#### 3.4.6.1 CMA-ModelPred v2 Top-3并集与完成状态

汇总：21组Top-3并集共306项；已完整评测290项，已知不收敛失败2项，待补14项，满足`290+2+14=306`。

| Dataset | Model | v2 Top-3并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2 | 11 | 主:L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2 | 11 | - | - | 0 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11 | 14 | 主:L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11 | 14 | - | - | 0 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19 | 16 | 主:L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19 | 16 | - | - | 0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2 | 14 | 主:L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25 | 11 | - | L0,L1,L2 | 3 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L15 | 16 | 主:L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L15 | 16 | - | - | 0 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | 主:L8,L9,L7,L12,L11,L10,L17,L5,L6,L4,L3 | 11 | L0 | - | 0 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L5 | 16 | 主:L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L5 | 16 | - | - | 0 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | 主:L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | - | - | 0 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L25,L22 | 17 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L25,L22 | 17 | - | - | 0 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | 主:L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | - | - | 0 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | - | - | 0 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13 | 14 | 主:L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13 | 14 | - | - | 0 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3 | 13 | 主:L8,L9,L14,L12,L10,L17,L4；stable-only:L7,L13,L5,L6,L3 | 12 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L5 | 15 | 主:L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L5 | 15 | - | - | 0 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | 主:L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L25,L22 | 17 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L25,L22 | 17 | - | - | 0 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | 主:L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | - | 0 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12,L4 | 18 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L22,L24,L1,L9,L7,L0,L2,L13,L11,L12,L4 | 11 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L20 | 14 | 主:L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L20 | 14 | - | - | 0 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3 | 13 | 主:L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3 | 13 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2 | 11 | 主:L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2 | 11 | - | - | 0 |

#### 3.4.6.2 17个完整可比组合上的七方法Top-3阶段指标

完整可比组合仍为17/21：EVQA除PaliGemma和LLaVA外的5组；MMKE-visual除PaliGemma外的6组；MMKE-entity除LLaVA外的6组。两组PaliGemma L0终止失败不以0分填充；两组LLaVA仍有未评测层。

| 方法 | Mean Best@3 ↑ | Mean Mean@3 ↑ | Mean Regret@3 ↓ | Hit@3 ↑ |
|---|---:|---:|---:|---:|
| **Ours-Direct** | 70.873（1） | 68.541（1） | 1.984（1） | 41.2%（1） |
| CMA-ModelPred-Direct | 69.899（2） | 67.369（3） | 2.958（2） | 29.4%（3） |
| LGA-Param-Direct-AltModelPred | 69.177（3） | 65.001（6） | 3.680（3） | 11.8%（6） |
| Middle-Prior-Direct | 68.962（4） | 68.018（2） | 3.895（4） | 5.9%（7） |
| Perturb-KL-Direct-AltSeq | 68.868（5） | 67.107（4） | 3.990（5） | 17.6%（4） |
| VisEdit-Contrib-Pre-KeyToken | 67.294（6） | 64.873（7） | 5.563（6） | 17.6%（4） |
| SaLEM-Alt-Direct | 67.173（7） | 65.092（5） | 5.684（7） | 35.3%（2） |

**阶段结论：** 替换为`CMA-ModelPred-Direct`后，Ours-Direct仍在Mean Best@3、Mean Mean@3、Mean Regret@3和Hit@3四项指标上全部排名第1。新版CMA相对历史CMA的`68.826 / 65.404 / 4.031 / 23.5%`提升为`69.899 / 67.369 / 2.958 / 29.4%`，在Best、Mean和Regret上升至第2，但仍未超过Ours-Direct。

#### 3.4.6.3 CMA-ModelPred v2 Top-5并集与完成状态

汇总：21组Top-5并集共432项；已完整评测330项，已知不收敛失败2项，待补100项，满足`330+2+100=432`。严格只使用主配置完整结果时，目前仅MMKE-entity/PaliGemma达到七方法Top-5完整可比；因此暂不把单组合Top-5方法均值作为总体结论。

| Dataset | Model | v2 Top-5并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 | 主:L15,L16,L14,L17,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 14 | - | L13 | 1 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L21,L22 | 25 | 主:L15,L16,L14,L28,L27,L26,L25,L0,L18,L19,L2,L1,L4,L3,L11 | 15 | - | L17,L13,L24,L20,L5,L6,L9,L10,L21,L22 | 10 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19 | 24 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L8,L9,L10,L29,L0,L1,L2,L18,L19 | 17 | - | L13,L23,L5,L6,L21,L3,L4 | 7 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4 | 21 | 主:L15,L16,L14,L28,L27,L26,L25,L24,L7,L6,L5 | 11 | - | L17,L13,L8,L9,L23,L0,L1,L2,L3,L4 | 10 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L8,L5 | 25 | 主:L17,L18,L16,L19,L15,L29,L28,L27,L26,L11,L14,L12,L2,L30,L1,L3,L0,L21,L20 | 19 | - | L25,L13,L10,L4,L8,L5 | 6 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4 | 13 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L5,L3,L4 | 11 | L0 | L13 | 1 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3,L5 | 23 | 主:L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L22,L21,L20,L19,L1,L2,L0,L3,L5 | 20 | - | L6,L18,L4 | 3 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L0,L18,L19,L20,L1,L3,L4,L2 | 16 | - | L13,L23,L5 | 3 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L22,L23,L21 | 23 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L1,L3,L5,L22,L23 | 19 | - | L13,L20,L8,L21 | 4 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 | 主:L15,L16,L14,L17,L26,L25,L24,L31,L5,L8,L9,L0,L1,L3,L2,L10,L11 | 17 | - | L13,L23,L22,L6,L4 | 5 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 | 主:L15,L16,L14,L28,L27,L26,L24,L7,L8,L9,L22,L0,L1,L2,L3 | 15 | - | L17,L13,L25,L6,L10,L23,L4,L5 | 8 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4 | 21 | 主:L17,L18,L16,L19,L28,L27,L26,L12,L11,L14,L13,L2,L30,L1,L6,L0 | 16 | - | L15,L25,L24,L3,L4 | 5 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 | 主:L8,L9,L10,L14,L12,L11,L17,L4；stable-only:L7,L6,L13,L5,L3,L2,L1 | 15 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2 | 18 | - | L3 | 1 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1,L7,L10 | 18 | 主:L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | - | L7,L10 | 2 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L22,L21,L23 | 24 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L30,L5,L3,L1,L22,L23 | 20 | - | L13,L20,L8,L21 | 4 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 | 主:L15,L16,L14,L25,L24,L23,L22,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | L17,L13,L21,L29 | 4 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L17,L13,L25,L24,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 18 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0,L20,L22 | 21 | 主:L17,L18,L16,L15,L29,L28,L27,L26,L25,L14,L13,L2,L30,L1,L0,L20,L22 | 17 | - | L19,L12,L6,L3 | 4 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2 | 15 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2 | 15 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L2 | 15 | - | L5,L8,L3,L4 | 4 |

#### 3.4.6.4 版本边界与机器可读结果

- 3.4.5及其CSV继续代表历史`CMA-Direct v1.3/alt`版本；本节代表`CMA-ModelPred-Direct v2`，两版不得混合平均、跨版本取最大值或互相覆盖。
- v2并集与状态：`outputs/formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv`。
- v2逐组合方法指标：`outputs/formal7_cma_modelpred_v2_method_fair_rows_20260914.csv`。
- v2方法汇总：`outputs/formal7_cma_modelpred_v2_method_summary_20260914.csv`。
- 可复现脚本：`outputs/recalculate_formal7_cma_modelpred_v2_20260914.py`。
+
### 3.4.7 八方法（CMA-alt与CMA-model_pred同时保留）最新完成状态：2026-09-21

本节按六种固定方法加两版CMA，共八个版本化方法行的Top-3候选层去重统计；Ours仅取主公式`M_abscos_x_newn`。历史3.4.5与3.4.6为各自日期的七方法快照，保留原文，不能直接当作当前缺层清单。八方法共324个“数据集×模型×层”项；截至2026-09-21约20:25 CST，已有完整评测311项（其中MMKE-visual/PaliGemma的L1,L2,L3,L5,L6,L7,L13共7项为stable-only，不能直接计作主配置），尚未完成11项，另有不收敛失败2项。恒等式为`311+11+2=324`；该计数是评测覆盖，不代表311项均正常收敛或具备同配置公平比较资格。

| 数据集 | 模型 | 层 | 当前状态 |
|---|---|---|---|
| EVQA-pilot500 | LLaVA-v1.5-7B | L2 | 已训练和选点，尚无`eval_full.done`，待正式评测 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L4 | 待训练与正式评测 |
| MMKE-entity | LLaVA-v1.5-7B | L1 | 用户要求暂停，Epoch17恢复点已保存；未完成正式评测 |
| MMKE-entity | LLaVA-v1.5-7B | L9,L7,L0,L2,L13,L11,L12,L4 | 待训练与正式评测，共8层 |
| EVQA-pilot500 | PaliGemma-3B | L0 | 历史不收敛；本次可访问共享盘与本地未找到checkpoint，g09临时盘因无该节点作业权限不能核验，暂未补评测，见3.5.2 |
| MMKE-visual | PaliGemma-3B | L0 | 本次已用各自run的最低有限EMA现存checkpoint补评测：主配置Average 38.520、stable配置35.442；训练仍标不收敛，见3.5.2及4.0 |

本次纠正旧待补状态：EVQA/LLaVA L0、L1与MMKE-entity/LLaVA L22、L24均已正式评测，完整指标已补入第4.0节对应数据集表。前两层各评测2,093条，后两层各评测954条；不能继续列入待补。PaliGemma补评测尚未完成前不提前计数，也不因用户允许补评测而抹去历史训练失败。

**2026-09-21补评测后更新：** MMKE-visual/PaliGemma L0已有主配置与stable两份完整独立评测，按唯一层仅新增1个已评测项。八方法Top-3并集当前为`312已有评测 + 11未完成 + 1仍缺评测失败 = 324`。其中L0是“不收敛checkpoint的诊断补评测”，不能据此声称完成正常收敛或标准50epoch训练；7个stable-only层继续单列，不自动重算既有公平比较指标。训练失败的历史事实仍为两组，而目前仍无评测的失败层只剩EVQA/PaliGemma L0。

### 3.4.8 八方法联合候选并集最新核验（2026-09-22，保留两版CMA）

口径：六个固定定位方法加历史 **CMA-alt**、新版 **CMA-model_pred**，共8个版本化方法；Ours仍只取主公式。逐一核对168个方法×组合的Top-3/Top-5推荐行，再按“数据集×模型×层”去重。这里是八方法联合覆盖，不替换前文两个七方法历史快照，也不将两版CMA分数混用或择优。

**Top-3联合并集324项：313项已有独立评测，11项仍缺独立评测。** 313项细分为304项历史主配置验收记录、7项stable-only、2项不收敛诊断补评测。后两类不能自动计入“标准50 epoch主配置完整可比”；304项中已有的历史恢复/数值异常标签也继续保留。本次没有重算方法排名。

| 数据集 | 模型 | 尚缺评测的Top-3并集层 | 数量 | 当前证据 |
|---|---|---|---:|---|
| EVQA-pilot500 | LLaVA-v1.5-7B | L2、L4 | 2 | L2已有训练完成标记和selected，但无完整eval；L4无完整评测 |
| MMKE-entity | LLaVA-v1.5-7B | L0、L1、L2、L4、L7、L9、L11、L12、L13 | 9 | L1按用户要求暂停，保留Epoch17恢复点；其余8层无完整评测 |

EVQA/LLaVA L0、L1及MMKE-entity/LLaVA L22、L24已经评测，不在缺层表。此表是集合清单，**不是新启动或恢复队列的指令**；未恢复用户暂停的MMKE-entity训练。

| 数据集 | BLIP2 | InstructBLIP | MiniGPT-4 | LLaVA | Qwen2.5-VL | PaliGemma | SmolVLM |
|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | 12/12 | 15/15 | 17/17 | 13/15 | 17/17 | 12/12（含诊断L0） | 17/17 |
| MMKE-visual | 13/13 | 19/19 | 16/16 | 15/15 | 15/15 | 15/15（含诊断L0及7项stable-only） | 16/16 |
| MMKE-entity | 14/14 | 19/19 | 17/17 | 9/18 | 14/14 | 16/16 | 12/12 |

表中分子仅表示已有评测，**19/21组合覆盖齐全不等于19个标准主配置完整可比组合**。两项诊断为EVQA/PaliGemma L0和MMKE-visual/PaliGemma L0，仍标不收敛、非完整50轮；7项stable-only为MMKE-visual/PaliGemma L1,L2,L3,L5,L6,L7,L13。严格要求标准主配置时，除11个缺评测层外，这9项也是协议例外，不能隐藏。

Top-5八方法联合并集另为439项，其中339项已有评测（含同样2项诊断和7项stable-only），100项无完整评测；不能把Top-5的100项与当前Top-3的11项混淆。

以下是Top-5附加缺口，**包含上述Top-3的11项，不是再额外增加100项**。按现有验收台账及本次活跃任务核验统计，未验收项不代表从未尝试训练，也不授权自动启动。

| 数据集 | 模型 | Top-5联合并集尚无完整评测的层 | 数量 |
|---|---|---|---:|
| EVQA-pilot500 | BLIP2 | L13 | 1 |
| EVQA-pilot500 | InstructBLIP | L5,L6,L9,L10,L13,L17,L20,L21,L22,L24 | 10 |
| EVQA-pilot500 | MiniGPT-4 | L3,L4,L5,L6,L13,L21,L23 | 7 |
| EVQA-pilot500 | LLaVA | L2,L3,L4,L8,L9,L10,L13,L17,L23 | 9 |
| EVQA-pilot500 | Qwen2.5-VL | L4,L5,L6,L8,L10,L13,L25 | 7 |
| EVQA-pilot500 | PaliGemma | L2,L13 | 2 |
| EVQA-pilot500 | SmolVLM | L4,L6,L18 | 3 |
| MMKE-visual | BLIP2 | L5,L13,L23 | 3 |
| MMKE-visual | InstructBLIP | L8,L13,L20,L21 | 4 |
| MMKE-visual | MiniGPT-4 | L4,L6,L13,L22,L23 | 5 |
| MMKE-visual | LLaVA | L4,L5,L6,L10,L13,L17,L23,L25 | 8 |
| MMKE-visual | Qwen2.5-VL | L3,L4,L15,L24,L25 | 5 |
| MMKE-visual | SmolVLM | L3 | 1 |
| MMKE-entity | BLIP2 | L7,L10 | 2 |
| MMKE-entity | InstructBLIP | L8,L13,L20,L21 | 4 |
| MMKE-entity | MiniGPT-4 | L13,L17,L21,L29 | 4 |
| MMKE-entity | LLaVA | L0,L1,L2,L3,L4,L6,L7,L8,L9,L10,L11,L12,L13,L17,L21,L25 | 16 |
| MMKE-entity | Qwen2.5-VL | L3,L6,L12,L19 | 4 |
| MMKE-entity | SmolVLM | L3,L4,L5,L8,L19 | 5 |

MMKE-visual与MMKE-entity的PaliGemma在该Top-5集合中无新增缺评测层，但前述诊断、stable-only及数值异常限制仍适用。

核验来源与范围：推荐矩阵与`Firstprash_7_location_recommend.md`全部168行交叉一致；历史验收覆盖来自已有逐层记录和两版并集CSV；当前LLaVA缺口额外核验g07/g08任务目录及共享盘的selected、train/eval标记和结果。不是对所有历史权重重新训练或全量重新评测。机器可读逐层证据：`outputs/localization_audit_20260922/formal8_union_status.json`；复算脚本：`outputs/audit_formal8_union_20260922.py`；实时产物清单为同目录`evqa_llava_tmp.json`、`evqa_llava_shared.json`、`entity_llava_tmp.json`、`entity_llava_shared.json`。最新PaliGemma诊断结果见3.5.3及4.0。

### 3.5 PaliGemma 主配置 / stable 结果、异常与重跑总登记

本节是后续 PaliGemma 失败层重跑的统一入口。最新快照来自 2026-07-19 08:38 对 Slurm job `3044208`、g09/物理GPU0的服务器结果、进程、日志与完成标记交叉检查。补跑顺序为EVQA stable L6、MMKE-entity stable L12、EVQA stable L4、MMKE-entity主配置L16，四层均已完成训练及对应test/eval完整评测，队列于2026-07-19 05:22:31自动结束，当前无PaliGemma训练或评测进程。生成重跑队列时搜索状态中包含的精确前缀 `RETRY_REQUIRED` 或 `FAILED`；`EVAL_DONE` 表示同层同时存在非空 `selected_checkpoint.tsv`、对应 test/eval 完整结果和 `eval_full.done`。

| Dataset | Config | 目标/已有范围 | 已完整评测 | 失败/未验收 | 当前与后续 |
|---|---|---|---|---|---|
| MMKE-visual | 主配置 `paligemma-3b.yaml` | 原始 run 7层：L8,L9,L10,L11,L12,L14,L17 | 7/7 | 无未评测层；L14 的负 EMA 和 L17 的高 loss 属于已评测数值异常结果 | 已结束 |
| MMKE-visual | stable | 共尝试15层 | 14/15：L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L14,L17 | L0 `FAILED_NONCONVERGENT` | 已结束；L0 不自动按原配置重跑 |
| EVQA-pilot500 | 主配置 | 既有完整评测6层：L9,L10,L11,L12,L14,L15；job 3044208追加8层 | 新增7/8：L1,L4,L5,L6,L7,L8,L17；连同既有结果共13个唯一完成层 | L9为历史stall恢复结果；L14为负EMA数值异常结果；新增L0在Epoch47后loss=nan、rc=1，无selected/eval | 阶段已结束；7个新增完成层均使用`vqa_eval.json`完整评测2,093条 |
| EVQA-pilot500 | stable | 8层：L8,L7,L17,L0,L5,L6,L1,L4 | 7/8：L1,L4,L5,L6,L7,L8,L17 | L0不收敛且无selected/eval；L4补跑虽完成但训练中触发16次nonfinite梯度安全跳步 | L6采用`data_buffer_size=1`、L4采用optimizer-step finite保护后均完成50 epoch，并使用`vqa_eval.json`完整评测2,093条；仅L0保留失败 |
| MMKE-entity | stable | 15层 | 14/15：L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L16,L17 | L0训练满50 epoch但不收敛，stable筛选后无selected/eval | L12采用`data_buffer_size=1`从头重训成功，Epoch48 selected，完成954条评测，Average 95.296；仅L0记录不收敛失败 |
| MMKE-entity | 主配置 | 15层 | 15/15：L0,L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L16,L17 | 无缺评测层；L0数值退化（Average 20.00）；L16补跑触发34次nonfinite梯度安全跳步且结果偏低（Average 47.044） | L16采用optimizer-step finite保护从头重训，Epoch49 selected，完成954条评测；双标记完整，但保留数值异常注释 |

#### 3.5.1 异常原因、现存 checkpoint 与重跑建议

| Dataset | Config | Layer | 状态标记 | 异常/结果 | 原因核验 | 现存 checkpoint | 队列结束后的处理建议 |
|---|---|---:|---|---|---|---|---|
| MMKE-visual | 主配置 | L14 | `EVAL_DONE_NUMERIC_ANOMALY` | Ckpt Epoch 1，EMA `-351.953961`，Average 39.03；已完成293条评测 | 负 EMA 不符合 stable 筛选口径，结果虽可复现但数值质量异常 | selected/eval均存在 | 不列入必重跑；比较时优先使用已完成的 stable L14（Average 58.87），主配置结果保留作异常对照 |
| MMKE-visual | stable | L8 | `EVAL_DONE_RECOVERED_EPOCH13` | 训练在 Epoch 13 后中断，使用 Epoch 13 checkpoint 手动完成293条评测，Average 96.92 | 属于中断恢复，不是完整50轮训练结束 | selected/eval均存在 | 若论文严格要求每层完整50轮，可列为可选重跑；否则保留并明确 recovered 状态 |
| MMKE-visual | stable L0专用配置 | L0 | `FAILED_NONCONVERGENT` | 训练至 Epoch 26 的212/214；EMA长期约3.4k--3.5k，整层nonfinite反复出现；保存时另有 `PytorchStreamWriter file write failed / unexpected pos` | 主要原因是数值不收敛，写盘错误是末次保存的附加故障，不是“不收敛”的根因 | 无selected、无eval | 原配置同seed直接重跑大概率重复失败；正式表记录不收敛。若必须探索，单独使用更低学习率等敏感性配置，并与主结果分栏 |
| EVQA-pilot500 | 主配置 | L9 | `EVAL_DONE_RECOVERED_FROM_STALL` | 使用恢复checkpoint完成2,093条评测，Average 36.16 | 历史训练发生stall；恢复后评测完整 | selected/eval均存在 | 不列入必重跑；若要求严格完整50轮，可在队列结束后列为可选重跑 |
| EVQA-pilot500 | 主配置 | L14 | `EVAL_DONE_NUMERIC_ANOMALY` | Ckpt Epoch 1，EMA `-1369.521638`，Average 32.06；已完整评测 | 负 EMA 明显异常，不能解释为正常收敛，但评测产物完整 | selected/eval均存在 | 该层不在当前12层候选并集内，不优先重跑；如用于附加比较，建议另补 stable 版本 |
| EVQA-pilot500 | 主配置 | L0 | `FAILED_NONFINITE_LOSS_NONCONVERGENT` | 训练至Epoch47后loss变为nan，累计284次nonfinite gradient跳步，rc=1，无评测 | 不是OOM或watchdog卡住；loss/EMA长期约2.8k--3.2k，数值未收敛，最终运行时异常退出 | 无selected、无eval | 正式记录不收敛失败；主配置与stable均失败，原配置直接重跑价值低。若必须探索，仅作为低学习率等独立敏感性实验 |
| EVQA-pilot500 | stable | L0 | `FAILED_NONCONVERGENT` | Epoch 49、约 step 12196 发生参数 nonfinite；此前整层nonfinite反复出现，loss/EMA约2.7k--3.4k | 早层反向路径数值敏感；stable保护能跳过坏梯度，但不能使该层形成有效收敛 | 有有限值原始checkpoint（最佳保留约 Epoch 47、EMA 2770.6896），无selected/eval | 不建议原配置直接重跑；记录不收敛。若必须探索，作为独立低学习率敏感性实验，不冒充当前stable结果 |
| EVQA-pilot500 | stable | L4 | `EVAL_DONE_RETRY_NUMERIC_GUARD` | 旧run在Epoch29参数nonfinite、rc=1；加入optimizer-step finite检查/保护后从头完成50 epoch，训练中有16次nonfinite梯度安全跳步 | 原异常为Adam更新后的参数数值崩溃；修复不改变epoch、batch、lr、seed、数据或优化目标，只阻止坏更新污染参数 | 新selected为Epoch50，raw/EMA loss `0.591566/0.491418`；selected/eval均存在 | 已使用`vqa_eval.json`完整评测2,093条：Rel 66.09、T-Gen 64.75、M-Gen 85.62、T-Loc 100.00、M-Loc 77.50、Average `78.792`。从必重跑列表移出，保留16次安全跳步注释 |
| EVQA-pilot500 | stable | L6 | `EVAL_DONE_RETRY_BUFFER1` | 旧run在Epoch12后停滞并由watchdog终止；`data_buffer_size=1`从头重跑完成50 epoch | 旧异常不是OOM，属于后台预取/数据准备停滞；串行buffer后未复现卡住 | 新selected为Epoch50，raw/EMA loss `0.423632/0.468850`；selected/eval均存在 | 已使用`vqa_eval.json`完整评测2,093条：Rel 69.94、T-Gen 69.13、M-Gen 89.83、T-Loc 100.00、M-Loc 68.92、Average `79.564`。从必重跑列表移出 |
| MMKE-entity | stable | L12 | `EVAL_DONE_RETRY_BUFFER1_GPU_MIGRATED` | 旧run在Epoch45后停滞；首次补跑误落GPU1并与InstructBLIP冲突，现场归档至Epoch7；随后在job3044208/物理GPU0从Epoch1重训并完成50 epoch | 原始失败是后台预取/数据准备停滞，不是不收敛；正式补跑固定正确Slurm cgroup并使用`data_buffer_size=1`，无OOM、nonfinite或Traceback | 新selected为Epoch48，raw/EMA loss `0.538605/0.830285`；selected/eval均存在。误落GPU1的Epoch2--6 checkpoints与Epoch7日志仅作冲突记录，不作为正式结果 | 已使用MMKE-entity eval数据完整评测954条：Rel 93.40、T-Gen 93.26、M-Gen 93.41、T-Loc 100.00、M-Loc 96.41、Average `95.296`。从必重跑列表移出 |
| MMKE-entity | stable | L0 | `FAILED_NONCONVERGENT` | 已训练满50 epoch；最终raw loss 2806.0613、EMA 2776.7354，累计120次整层nonfinite gradient并跳过step；stable筛选`kept=0`，rc=1，无评测 | 不是OOM，也不是2小时总运行时间限制；L0全程loss维持约2.7k--3.5k，10个保留候选checkpoint均因`too_large`被拒绝，没有合格selected checkpoint | 有10个原始候选checkpoint，但均不满足stable验收；无`selected_checkpoint.tsv`、无`eval_full.done` | 正式记录不收敛失败，不按原配置自动重跑。若必须探索，仅作为独立低学习率等敏感性实验，并与当前stable结果分栏 |
| MMKE-entity | 主配置 | L0 | `EVAL_DONE_NUMERIC_DEGENERATE` | Ckpt Epoch8，raw 2887.8733、EMA 2815.5878；完成954条评测但Rel/T-Gen/M-Gen/M-Loc均为0，仅T-Loc为100，Average 20.00 | 双完成标记齐全，因此作为真实评测结果保留；但loss极高且指标退化，不能解释为正常收敛 | selected/eval均存在 | 不列为“缺评测”；统计和论文中单独标注数值退化。若追求有效编辑结果，再以独立稳定化配置重跑 |
| MMKE-entity | 主配置 | L16 | `EVAL_DONE_RETRY_NUMERIC_GUARD` | 旧run训练至Epoch33后loss=nan、rc=1；加入optimizer-step finite保护后从头完成50 epoch，补跑中触发34次nonfinite梯度安全跳步 | 不是OOM；主配置该层仍有明显数值敏感性。保护避免坏更新污染参数，但低分结果不能解释为稳定收敛 | 新selected为Epoch49，raw/EMA loss `15.929332/18.301300`；selected/eval均存在 | 已使用MMKE-entity eval数据完整评测954条：Rel 12.43、T-Gen 12.21、M-Gen 12.41、T-Loc 100.00、M-Loc 98.17、Average `47.044`。从缺失/必重跑列表移出，但统计和论文中保留数值异常、低分与34次安全跳步注释 |

说明：`rc=143` 是旧run被watchdog终止后的进程退出码，不是失败143次。L4/L6/L12旧run的恢复候选checkpoint仍只作历史诊断；本次登记使用的是从Epoch1重新训练50轮后生成的新selected和完整test/eval结果，不是直接补评旧checkpoint。L4、L6、L12、L16均已从`RETRY_REQUIRED`/`FAILED`移出；其中L4与L16仍保留nonfinite安全跳步和数值质量注释。

#### 3.5.2 不收敛L0现存checkpoint补评测（2026-09-21，用户明确授权）

用户授权对不收敛的PaliGemma L0仍取最低checkpoint补做独立评测。此次只评测现存权重，未重训或改变历史训练配置。选点规则为**同一run内现存、可加载、EMA有限的checkpoint中取EMA最低者**；同时检查保存内容的epoch、EMA与loss_history一致及26个参数张量均为有限值。不同配置、不同重跑版本不混在一起选最低值；“不收敛”与“已有评测”分别记录。

| 数据集 | 配置/学习率 | 选中Epoch/step | raw loss | EMA loss | 独立eval数 | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 解释 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MMKE-visual | main，lr=1e-4 | 1 / 107 | 3465.718750 | 3508.007406 | 293 | 0.10 | 0.08 | 0.09 | 100.00 | 92.33 | **38.520** | 不收敛；本run现存7个checkpoint中最低有限EMA；非完整50epoch训练 |
| MMKE-visual | stable L0专用，lr=1e-6 | 25 / 2675 | 3402.662842 | 3454.815660 | 293 | 0.09 | 0.09 | 0.10 | 100.00 | 76.93 | **35.442** | 不收敛；本run现存8个checkpoint中最低有限EMA；Epoch26保存失败，仅残留lock，没有可加载权重 |
| EVQA-pilot500 | main / stable | — | — | — | 0 | — | — | — | — | — | — | 本次未找到可访问checkpoint，不能补评测；未填0分，未冒充完成 |

两份MMKE-visual评测在Job3178538/g08中串行完成，原训练队列和其他GPU进程未停止；Job3178423的LLaVA仍按用户要求暂停。输出直接写共享盘`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/paligemma_l0_nonconvergent_eval_20260921/`，没有复制大权重到服务器`/tmp`。其下`mmke-visual_main_l0_lr1e4`与`mmke-visual_stable_l0_lr1e6`各有`selection_audit.json`、原配置、原loss_history、`layer_00/selected_checkpoint.tsv`、`eval_full.done`及逐样本`results.json`、`mean_results.json`；本次没有伪造`train.done`。小型结构化结果已同步到本地同名`server_results/live_backfill/paligemma_l0_nonconvergent_eval_20260921/`目录。

原权重来源（共享盘根目录`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/`）：

- main：`mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b/layer_00/records/vead/paligemma-3b/pilot500_blip2_visedit_L00-lr-1-t-1-v-1/checkpoints/epoch-1-i-107-ema_loss-3508.0074`；SHA-256=`65f1f71b94e984cbcfa4f73d6f50498b6e3e585e488d9ed77eb9b1272282a06b`。
- stable：`paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b/layer_00/records/vead/paligemma-3b/pilot500_blip2_visedit_L00-lr-1-t-1-v-1/checkpoints/epoch-25-i-2675-ema_loss-3454.8157`；SHA-256=`0007fbf37069132da4911818ca8d0cb8ef9f33b3f0f77ac13c8b50a04eb21140`。

EVQA核验限制：已检索共享`server_results`、项目`records`、登录节点`/var/tmp/ph_teacher3`及可访问g07/g08相关临时目录；共享归档`tmp_archives_20260810/g09/paligemma_followup_job3044208_20260715_112056/`下的`paligemma_main_evqa_pilot500_job3044208_20260715_112056/paligemma-3b/layer_00`与`paligemma_stable_evqa_pilot500_pending_job3044208_20260715_112056/paligemma-3b/layer_00`只剩空目录。原g09返回`Access denied by pam_slurm_adopt: you have no active jobs on this node`，因此只能确认**当前可访问存储没有找到权重**，不能断言原节点文件已经删除。上方“stable Epoch47、EMA2770.6896仍保留”是历史记录，本次未复核到文件实体。恢复g09访问或找到备份后方可补评测，本次没有新申请作业或重训。

#### 3.5.3 EVQA/PaliGemma L0重训中断后固定Epoch 2诊断评测（2026-09-22）

在用户授权的Job3178538/g08主配置补跑中，训练保存30轮记录后停在Epoch31、100/500，未完成50轮。用户随后明确要求“不用续跑，就用这个epoch 2测试”；本次没有续训，固定使用本run现存最低有限EMA的Epoch2/step500。原配置和历史不收敛结果保留，不能覆盖成正常训练完成。

| Dataset / Model / Layer | Epoch / step | raw loss | EMA loss | eval数 | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EVQA-pilot500 / PaliGemma-3B / L0 | 2 / 500 | 3187.056885 | 3209.824510 | 2093 | 0.16 | 0.18 | 0.16 | 100.00 | 76.96 | **35.492** |

评测于**2026-09-22 08:47:15 CST**退出，rc=0；已核验2093条逐样本结果、`eval_full.done`、selected及SHA-256一致。`training_complete_50_epochs=false`，没有伪造`train.done`；通用训练完成验证仍判不完整，诊断评测单独验收。训练日志154条`SANITIZE_NONFINITE_GRAD_BEFORE_STEP`记录，不能把有限loss/EMA或有限checkpoint权重解释为收敛、没有梯度异常。极低Rel/Generality也说明编辑效果退化；Average不能替代这一质量注释。

- 共享盘原始结果：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_paligemma_l0_main_retrain_job3178538_20260921/`。
- selected：该目录`layer_00/records/vead/paligemma-3b/pilot500_blip2_visedit_L00-lr-1-t-1-v-1/checkpoints/epoch-2-i-500-ema_loss-3209.8245`；SHA-256 `9405c64d2e1d5b96f5ab96b0109a25b8dcde2697f46faec319b37727efbef260`。
- 本地轻量归档：`server_results/live_backfill/pali_l0_diag_20260922/evqa-pilot500/paligemma-3b/layer_00/`，含逐样本`results.json`、`mean_results.json`、selected、完成标记、原配置、loss_history和诊断验证记录。大checkpoint仍留共享盘，不重复拉回本地或服务器/tmp。
- `results.json` SHA-256：`05f60b78e9a874d20e8b2f84a278864aec8852325bf3a0c4645419f63a20e970`。同步清单：`outputs/localization_audit_20260922/paligemma_diagnostic_sync_manifest.json`，其中`complete=false`、`diagnostic_only=true`、`evaluation_verified=true`。

本次使八方法Top-3评测覆盖从312升至313，仍缺11个LLaVA层；两个PaliGemma不收敛L0现在都有诊断评测，但均不能冒充标准50轮训练完成。旧3.5.2“EVQA未找到checkpoint”仅描述历史run；这里使用的是新授权重训run，不是找回了旧run。

## 4. 已完成真实扫层结果回填

本节登记各数据集独立完整 eval 的真实层评测，包含 main、stable 和明确标识的恢复/诊断评测。训练是否完成 50 轮、是否收敛与评测是否完成分别判断；不因为未收敛或低分而删除已有评测。方法比较须再固定候选版本及训练口径。

### 4.0 服务器结构化结果总表

<!-- SWEEP_MAIN_CURRENT_RESULTS_START -->
**最新同步：2026-09-28 11:10:16+08:00，数据来自最近一次服务器只读核验。**
<!-- SWEEP_LEDGER_SHA256:1fca9b575451ac101dccab12ff44c3cb59dba93d94dedeb429d7f297e340c71a -->

核对前逐层表 382 条，本次补入 51 条，现 433 条。main/stable 独立保留，不跨配置挑最高分。台账中 282 条在该次核验通过并找到实体 checkpoint，其余保留历史证据；不能把全部记录统称为本次重新验收的完整 50 轮。

当前已登记数量只按真实结果计数，不提供尚未冻结的候选并集分母。

| Dataset | Model | main 已评测 | stable 已评测 | main 独立复测 |
|---|---|---:|---:|---:|
| EVQA-pilot500 | blip2-opt-2.7b | 20 | 0 | 1 |
| EVQA-pilot500 | instructblip-vicuna-7b | 15 | 0 | 0 |
| EVQA-pilot500 | minigpt-4-vicuna-7b | 21 | 0 | 0 |
| EVQA-pilot500 | llava-v1.5-7b | 16 | 0 | 0 |
| EVQA-pilot500 | qwen2.5-vl-3b | 26 | 0 | 0 |
| EVQA-pilot500 | paligemma-3b | 15 | 7 | 0 |
| EVQA-pilot500 | smolvlm-1.7b | 20 | 0 | 0 |
| MMKE-visual | blip2-opt-2.7b | 19 | 0 | 0 |
| MMKE-visual | instructblip-vicuna-7b | 22 | 0 | 0 |
| MMKE-visual | minigpt-4-vicuna-7b | 21 | 0 | 0 |
| MMKE-visual | llava-v1.5-7b | 16 | 0 | 0 |
| MMKE-visual | qwen2.5-vl-3b | 23 | 0 | 0 |
| MMKE-visual | paligemma-3b | 16 | 15 | 0 |
| MMKE-visual | smolvlm-1.7b | 21 | 0 | 0 |
| MMKE-entity | blip2-opt-2.7b | 21 | 0 | 0 |
| MMKE-entity | instructblip-vicuna-7b | 23 | 0 | 0 |
| MMKE-entity | minigpt-4-vicuna-7b | 18 | 0 | 0 |
| MMKE-entity | llava-v1.5-7b | 10 | 0 | 0 |
| MMKE-entity | qwen2.5-vl-3b | 21 | 0 | 0 |
| MMKE-entity | paligemma-3b | 16 | 14 | 0 |
| MMKE-entity | smolvlm-1.7b | 16 | 0 | 0 |

本次漏记层：

| Dataset | Model | 新补入逐层记录 |
|---|---|---|
| EVQA-pilot500 | instructblip-vicuna-7b | L0,L1,L2,L3,L4,L11,L14,L15,L16,L18,L19,L25 |
| EVQA-pilot500 | minigpt-4-vicuna-7b | L0,L1,L2,L7,L8,L9,L10,L14,L15,L19,L22,L29 |
| EVQA-pilot500 | llava-v1.5-7b | L2 |
| EVQA-pilot500 | qwen2.5-vl-3b | L6,L10 |
| MMKE-visual | llava-v1.5-7b | L3,L14,L16,L22,L24,L26,L27 |
| MMKE-visual | qwen2.5-vl-3b | L3,L10 |
| MMKE-entity | minigpt-4-vicuna-7b | L0,L1,L3,L4,L6,L7,L14,L16,L22,L26,L27 |
| MMKE-entity | llava-v1.5-7b | L9 |
| MMKE-entity | qwen2.5-vl-3b | L3,L6,L10 |

- EVQA/PaliGemma main L0 最新产物覆盖 1–50 轮；仍选 Epoch2（EMA 3209.824510），Average 35.492，仍为高损失未收敛。此前“训练未完成”属于旧快照。
- MMKE-visual/PaliGemma main L0/L3/L5、stable L0 保留恢复评测；stable L8 保留手工 Epoch13 选点的历史身份。
- `MAIN50` / `STABLE50` 表示该次核验覆盖 1–50 轮；`HISTORY_PARTIAL` 表示有训练完成标记但历史未全留存；`RECOVERED` 不冒称预算完整；`HISTORICAL_ACCEPTANCE` 表示继承原登记。
- 最低 EMA 是常规选点规则；EVQA/PaliGemma main L14、MMKE-visual/PaliGemma stable L2/L13 的 selected 与现存 history 最低值不一致，原分数与选点均保留并标注 `SELECTION_HISTORY_MISMATCH`。
- [逐层来源及核验证据](../../outputs/sweep_ledger_20260928_110311/ledger.json)；[本次更新前原手册](../../outputs/main_manual_sweep_sync_20260928_115326/6location_7model_3datas_top_3_5_layers_outcome.before.md)。台账引用的旧手册行号对应更新前文件，不对应本次移动后的行号。
- [结果图 PNG](../../outputs/completed_layer_results_20260928/completed_layers_average_main_stable.png) / [SVG](../../outputs/completed_layer_results_20260928/completed_layers_average_main_stable.svg)：main/stable 分行，逐格标注版本；图的数据时间以图内标注为准，重画命令为 `python scripts/plot_completed_sweep_results.py`。

**以下带旧日期的增量说明为历史审计记录；当前逐层状态和数量以上面的汇总及下方更新后的结果表为准。**
<!-- SWEEP_MAIN_CURRENT_RESULTS_END -->

**2026-09-27 22:09 CST，G09/Job3443209 本次优先补层回填：** 已完整训练并正式评测3层：MMKE-visual/InstructBLIP L20、MMKE-entity/InstructBLIP L20、MMKE-entity/SmolVLM L8。三层均核验50条连续epoch历史、最低有限EMA选点、非空实体checkpoint及SHA-256、`train.done`、`eval_full.done`与完整`results.json`；独立评测样本数分别为293、954、954，Average分别为50.878、48.626、70.688。原main协议为50轮、batch=2、lr=1e-4、EMA alpha=0.1，未改为stable。已在下方对应数据集表各补1行；MMKE-visual/InstructBLIP表内完成数21→22，MMKE-entity/InstructBLIP 22→23，MMKE-entity/SmolVLM 15→16。本次只回填G09三层，其他历史计数及第3节冻结候选并集/方法指标不在本次重算。

G09现有安排共7层（含由G08转来的EVQA/InstructBLIP L17、L20），完成3层、未完成4层。当前MMKE-entity/MiniGPT-4 L7在Epoch43/50，22:07:46为348/636、22:09:55为418/636；后续依次L7正式评测→同组合L8训练评测→EVQA/InstructBLIP L17→L20。LLaVA仍按既有指令暂停，未在本次恢复。本条为带时间戳快照，不以排入队列代替完成。

逐层共享来源根：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/priority3_main_protocol_job3443209_20260926/accepted/`；相对目录分别为`mmke-visual/instructblip-vicuna-7b/layer_20`、`mmke-entity/instructblip-vicuna-7b/layer_20`、`mmke-entity/smolvlm-1.7b/layer_08`。完整精度、checkpoint/配置哈希及本地原件下载状态见[本次核验记录](../../outputs/g09_results_sync_20260927_2210/核验与回填记录.md)。服务器验收与本地下载是两项状态，不能因共享归档完成便声称全部原件已拉回本地。


**2026-09-22诊断增量：** EVQA/PaliGemma L0新增Epoch2的2093条完整诊断评测，Average35.492；状态显式包含`NONCONVERGENT_DIAGNOSTIC`及`TRAIN_INCOMPLETE`，详情见3.5.3。不能把本次新增解释为完整50轮训练验收；八方法当前缺层以3.4.8为准，历史日期快照不删除。

**2026-09-21增量回填：** 新增EVQA-pilot500/LLaVA L0、L1和MMKE-entity/LLaVA L22、L24四行，均已核验`train.done`、`selected_checkpoint.tsv`与独立完整`eval_full.done`。EVQA两行的服务器证据位于g08 `/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812/evqa-pilot500/llava-v1.5-7b/layer_00`、`layer_01`；MMKE-entity两行位于共享盘 `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082/mmke-entity/llava-v1.5-7b/layer_22`、`layer_24`。本次回填未重新训练，也未改变选点；各行Epoch为selected checkpoint轮次。EVQA/LLaVA表内唯一完整评测层由13增至15，八方法Top-3覆盖13/15；MMKE-entity/LLaVA由7增至9，八方法Top-3覆盖9/18。以下旧日期完成计数和“L22待评测”等描述保留为历史记录，以本条及3.4.7为最新状态。

来源：服务器各实验目录下的 `layer_*/eval_full.done` 与同层 `selected_checkpoint.tsv`。只回填 `EVAL_DONE` 的真实评测结果；标准 checkpoint 口径为每层训练 `50 epoch` 后按 minimum EMA loss 选择。因中断而从较早有限值 checkpoint 恢复并完成评测的例外，必须明确标记为 `TRAIN_RECOVERED_*` 或 `EVAL_DONE_RECOVERED_*`，不与标准 50 epoch 完成混淆。`EVQA-pilot500 / BLIP2-OPT-2.7B` 的历史补跑与复测表保留在 4.1，不在本总表重复列出。

完整性复核（2026-07-16 15:07）：已逐层交叉检查服务器权威结果根目录，只有同时存在非空 `selected_checkpoint.tsv` 和 `eval_full.done` 的层才进入下表。EVQA-pilot500 现有记录与服务器完成项一致、无漏行；本次补入 MMKE-visual MiniGPT-4 的4层，以及 MMKE-entity 的 BLIP2 11层、InstructBLIP 4层、MiniGPT-4 1层、PaliGemma stable 4层。正在训练、暂停、失败或仅有原始 checkpoint 的层仍不计完成。

增量复核（2026-07-17 09:49）：PaliGemma MMKE-entity stable 新增L1,L2,L3,L5,L6共5层，均同时存在非空`selected_checkpoint.tsv`、954条独立eval完整结果和`eval_full.done`，已补入下表。L0与L12没有双完成标记，分别按不收敛失败和卡住待重跑登记，不计入完成。

最终增量复核（2026-07-18 13:08）：服务器 PaliGemma 后续队列已生成`FOLLOWUP_DONE`。EVQA-pilot500主配置新增L1,L4,L5,L6,L7,L8,L17共7层，均具备非空`selected_checkpoint.tsv`、2,093条`vqa_eval.json`完整评测和`eval_full.done`；L0失败且无双标记。MMKE-entity主配置新增L0,L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L17共14层，均具备双标记和954条完整评测；L16失败且无双标记。以下已按配置分组、组内层号升序回填。

补跑增量复核（2026-07-19 08:38）：已按顺序完成EVQA stable L6、MMKE-entity stable L12、EVQA stable L4、MMKE-entity主配置L16。四层均从Epoch1重训至50 epoch，存在非空`selected_checkpoint.tsv`、对应test/eval完整结果及`eval_full.done`。EVQA两层各评测2,093条，MMKE-entity两层各评测954条。L4/L16分别触发16/34次nonfinite梯度安全跳步，虽验收完成但保留数值异常注释；L12首次误落GPU1的中断现场已归档，不计作正式结果。

MMKE-visual增量复核（2026-07-20 08:14）：Slurm job `3044208`在g09/GPU0完成SmolVLM待补10层与Qwen2.5-VL候选并集21层。SmolVLM 10层均从头训练并完成293条独立MMKE-visual test/eval；Qwen L17复用既有有效selected checkpoint重新评测，其余20层从头训练并评测。逐层均存在非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`，所有训练/评测阶段`rc=0`，未出现OOM、nonfinite、共享盘写入失败或watchdog超时。结构化结果暂存于g09本地`/tmp/ph_teacher3/mmke_visual_smol_qwen_job3044208_20260719_093500`，未覆盖共享结果目录。

MMKE-entity SmolVLM增量复核（2026-07-22 08:35）：Slurm job `3044208`在g09/GPU0完成候选并集15层`L0,L1,L2,L6,L7,L9,L10,L11,L12,L13,L14,L15,L16,L17,L18`。15层均从头训练至50 epoch流程结束并按minimum EMA loss选择checkpoint，随后使用独立MMKE-entity eval数据完整评测954条；逐层`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全。launcher各已结束阶段均为`rc=0`，未发现OOM、nonfinite、共享盘写入失败或watchdog超时。结构化结果暂存于g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/smolvlm-1.7b`；同队列Qwen当时仍从L17开始训练，未计入完成。

MMKE-entity Qwen增量复核（2026-07-24 11:11）：同一队列已于2026-07-23 22:38完成Qwen2.5-VL-3B候选并集18层`L0,L1,L2,L13,L14,L15,L16,L17,L18,L20,L21,L22,L25,L26,L27,L28,L29,L30`。逐层均完成50 epoch训练流程并按minimum EMA loss选择checkpoint，随后使用独立MMKE-entity eval数据完整评测954条；逐层`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，launcher训练/评测阶段均为`rc=0`，未发现OOM、nonfinite、Traceback或watchdog超时。结果暂存于g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/qwen2.5-vl-3b`。该runner的模型级`full_eval_results.csv`/`selected_checkpoints_all_layers.tsv`会被每层调用覆盖，当前只保留队列最后一层L25；本表完整性与数值以18个逐层目录内的`selected_checkpoint.tsv`、`eval_full.done`和`results.json`交叉核验结果为准，不能用模型级汇总文件的单行误判为仅完成1层。

MMKE-entity InstructBLIP增量复核（更新至2026-07-25 21:29）：Slurm job `3044841`在g09/GPU1新增完成候选层`L0,L1,L3,L4,L5,L22,L23,L24,L25`。9层逐层均存在非空`selected_checkpoint.tsv`、`eval_full.done`、954条独立MMKE-entity eval完整结果和嵌套非空`results.json`，已补入下表；结果位于g09本地`/tmp/ph_teacher3/mmke_entity_job3044841_20260715_121700/instructblip-vicuna-7b`。L1曾因80GB显存不足中断，后从Epoch45 checkpoint恢复，采用CPU同步数据加载与activation checkpointing完成剩余训练及正式评测；完成标记未受损。L25从Epoch1训练至Epoch50/step15900，selected EMA为10.972824，随后完整评测954条，launcher eval `rc=0`、Average 47.578。至此候选并集19/19全部完成，无待补候选层。

EVQA-pilot500 SmolVLM/Qwen增量复核（2026-07-25 20:20）：Slurm job `3044208`在g09/GPU0的后续队列已完成SmolVLM候选补跑10层`L0,L1,L2,L3,L7,L8,L9,L10,L11,L20`和Qwen候选补跑14层`L0,L1,L2,L3,L11,L12,L14,L16,L17,L21,L22,L24,L30,L34`。24层逐层均存在`train.done`、非空`selected_checkpoint.tsv`和包含2,093条独立EVQA eval完整指标的`eval_full.done`，结果位于g09本地`/tmp/ph_teacher3/evqa_pilot500_smol_qwen_job3044208_20260723_202500`，已补入下表。该runner没有另写逐层`results.json`，完整指标直接保存在非空`eval_full.done` JSON中；因此按训练完成、selected checkpoint和正式评测三项交叉验收，不因缺少冗余副本文件误判为未完成。至此SmolVLM候选并集18/18、Qwen候选并集20/20均完成。

EVQA-pilot500 BLIP2增量复核（2026-07-30）：Slurm job `3044208`在g09/GPU0于Job取消前完成待补5层`L14,L1,L3,L4,L2`。5层均从头完成50 epoch训练流程并按minimum EMA loss选择checkpoint，随后使用独立`vqa_eval.json`正式评测2,093条；逐层`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，训练与评测均`rc=0`。结果位于g09本地`/tmp/ph_teacher3/evqa_pilot500_blip2_missing5_job3044208_20260728`。至此BLIP2候选并集15/15层均已完整训练和评测；Job后续于2026-07-29 15:25取消不影响此前生成的完成结果。

三数据集全量增量复核（2026-07-31 08:53）：以本文件上次修改时间2026-07-30 14:10:15为界，扫描g09共享正式结果根目录及`/tmp/ph_teacher3`现存实验目录，之后新生成且同时具备非空`selected_checkpoint.tsv`、`train.done`、对应独立评测完整指标、非空`eval_full.done`和非空`results.json`的结果只有MMKE-visual / MiniGPT-4候选层`L0,L1,L2,L3,L29`共5层。5层均在job 3044841/GPU1完成50 epoch训练流程；原runner选点记录缺陷于2026-07-30 14:14修复，随后依次完成293条MMKE-visual正式评测，结果位于g09本地`/tmp/ph_teacher3/mmke_visual_minigpt_llava_job3044841_20260728/minigpt-4-vicuna-7b`。EVQA-pilot500与MMKE-entity没有发现服务器已完整评测但未回填的新层。job 3117562/GPU0的MMKE-visual LLaVA L0在本次快照时仍处于Epoch 32训练，尚无selected/eval双标记，不计入完成。

MMKE-visual LLaVA逐层增量复核（2026-08-01 20:04）：Slurm job `3117562`在g09/GPU0新增完成L0、L1。两层均完成50 epoch训练流程并按minimum finite EMA选择checkpoint，随后使用独立MMKE-visual eval数据完整评测293条；逐层`train.done`、非空`selected_checkpoint.tsv`、包含六项指标的非空`eval_full.done`和评测后清理标记齐全。L0 selected为Epoch40/step4280/EMA 0.314945，Average 75.158；L1 selected为Epoch47/step5029/EMA 0.302343，Average 75.640。评测后已分别清理51/52个非selected checkpoint及可重建cache，selected未删除；服务器结果目录为`/tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730/llava-v1.5-7b`，完成标记和结构化指标已同步到本地`server_results/live_backfill/job3117562/mmke-visual/llava-v1.5-7b`。

Ours主公式补层队列增量复核（2026-08-02 09:23）：Slurm job `3126082`已完成MMKE-visual/SmolVLM L2、MMKE-entity/BLIP2 L1和MMKE-entity/PaliGemma L4。三层分别使用对应独立eval数据完整评测293/954/954条，均有非空`selected_checkpoint.tsv`、`train.done`和`eval_full.done`。SmolVLM L2 selected为Epoch46/EMA 0.411423，Average 70.522；BLIP2 L1 selected为Epoch11/EMA 5.990400，Average 72.504；PaliGemma主配置L4 selected为Epoch2/EMA 0.882321，Average 96.136。每层评测后均删除51个非selected checkpoint并保留唯一selected；结构化结果同步到本地`server_results/live_backfill/job3126082`。同队列MiniGPT-4 L9首次尝试在加载数据处理模型时CUDA OOM，当时无selected/eval并被跳过；此后已独占GPU从头重跑成功，最终完成状态与指标以紧随其后的2026-08-10恢复复核为准。

g09节点故障后恢复复核（2026-08-10 18:03）：g09于2026-08-06 01:11发生`NODE_FAIL`，job 3117562与3126082被Slurm重排到g07后只恢复Jupyter服务，实验launcher没有自动续跑。重新将空闲的job 3126082调度回g09取得只读权限后，确认原`/tmp`结果仍完整。MMKE-visual/LLaVA新增核验完成L2、L7、L8、L9、L12，连同先前已回填的L0、L1共7层；MMKE-visual/MiniGPT-4的主公式补层L9、L10、L11也已完成。10层逐层均具备非空`train.done`、`selected_checkpoint.tsv`、293条独立eval的`eval_full.done`和非空`results.json`。MiniGPT-4 L9先前OOM记录仅属于第一次失败尝试，随后独占GPU从头重跑成功，最终selected为Epoch49/step5243/EMA 0.257039、Average 76.582；L10为Epoch36/step3852/EMA 0.260045、Average 76.630；L11为Epoch39/step4173/EMA 0.272469、Average 76.830。完整关键产物及L13中断恢复现场已从g09复制到login01 `/var/tmp/ph_teacher3/recovered_g09_nodefail_20260810`（合计5.0 GiB），checksum dry-run差异为0；本地保留完整结构化压缩原件`server_results/live_backfill/recovered_g09_nodefail_20260810/structured_results.tar.gz`及短路径分析副本`server_results/g09r`。本次仅恢复、核验和同步，未启动新训练或删除原数据。

正式Top-3逐层即时回填（2026-08-11）：新增验收MMKE-visual/LLaVA L15、MMKE-visual/PaliGemma主配置L4、EVQA-pilot500/PaliGemma主配置L3。三层均同时具备非空`train.done`、`selected_checkpoint.tsv`、独立正式评测`eval_full.done`和非空`results.json`。LLaVA L15 selected为Epoch40/step4280/EMA 0.231111，293条评测Average 75.752；MMKE-visual PaliGemma L4 selected为Epoch39/step4173/EMA 0.330234，293条评测Average 99.026；EVQA PaliGemma L3 selected为Epoch38/step9500/EMA 0.531071，2,093条评测Average 85.720。结构化产物同步到本地`server_results/live_backfill/job3126082/mmke-visual/llava-v1.5-7b/layer_15`及`server_results/live_backfill/job3117562`对应数据集目录。自本条起，每次新候选层完成正式评测后立即执行同样的服务器双标记核验、结构化产物同步和本表逐层/计数更新，不等待整队列结束。

正式Top-3 LLaVA增量回填（2026-08-31 16:39 CST）：服务器共享盘新增核验EVQA-pilot500/LLaVA L6,L7,L14,L15,L16与MMKE-entity/LLaVA L14,L15,L16共8层。各层均具有非空`train.done`、`selected_checkpoint.tsv`、对应独立正式评测`eval_full.done`、非空`results.json`和`SYNC_VERIFIED`。EVQA使用独立`vqa_eval.json`评测2,093条，MMKE-entity使用独立entity eval评测954条；没有使用训练集评测。EVQA L15,L16此前已进入完成计数但缺少第4节详细结果行，本次一并补齐；本轮相对2026-08-24快照实际新增6个Top-3完成项。当前替代Job 3178538训练EVQA L5，替代Job 3178423训练MMKE-entity L28，两层均未完成正式评测，不提前回填。

正式Top-3 LLaVA增量回填（2026-09-13 18:02 CST）：服务器新增验收7层。Job 3178538完成EVQA-pilot500/LLaVA L5,L24,L25，均使用独立`vqa_eval.json`完整评测2,093条；Average依次为70.094、62.418、60.888。Job 3178423完成MMKE-entity/LLaVA L28,L27,L26,L23，均使用独立MMKE-entity eval完整评测954条；Average依次为74.742、75.148、75.144、75.540。7层逐层均具有非空`train.done`、`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`，未使用训练集评测。L5、L24及4个MMKE-entity层已经同步共享盘；EVQA L25当前完整产物仍位于g08节点`/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812/evqa-pilot500/llava-v1.5-7b/layer_25`，本表按服务器真实完整结果回填，但保留`LOCAL_TMP_PENDING_SHARED_SYNC`标记，不能把本地节点副本误称为持久归档。当前EVQA L0仍在训练；MMKE-entity L22已训练完成但尚无`eval_full.done`，两层均不计完成。

L25共享归档与临时副本清理（2026-09-15）：EVQA-pilot500/LLaVA L25已从g08 `/tmp`归档到`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065/evqa-pilot500/llava-v1.5-7b/layer_25`。重新核验2,093条独立正式评测、selected Epoch50/step12500/EMA 0.3291842153238946及Average 60.888；checkpoint SHA-256为`1d68657620140b5c3c4ecf3cdf618b9b23d7b6d5b1a170ec902ab52554743871`。归档保留selected实体、完整结果、配置、训练/评测日志和来源记录，三个运行标记中的层目录路径已改为共享路径，并写入`SYNC_VERIFIED`。按用户明确授权，在归档与无活动引用核验后删除原L25层目录、可重建缓存和两份L25独立日志，共约23.08 GiB磁盘空间；L0正在训练的目录及缓存保留。证据见`server_results/storage_audits/20260915_l25_archive`。本次只改变归档状态，完成层数和历史指标不变。

#### EVQA-pilot500

已登记完整评测（2026-09-28同步）：`blip2-opt-2.7b` main 20 层、独立复测 1 条（见 4.1）；`instructblip-vicuna-7b` main 15 层；`minigpt-4-vicuna-7b` main 21 层；`llava-v1.5-7b` main 16 层；`qwen2.5-vl-3b` main 26 层；`paligemma-3b` main 15 层、stable 7 层；`smolvlm-1.7b` main 20 层。这里的“已评测”包括明确列出的恢复/诊断结果，不等同于全部训练收敛或全部完整50轮。

PaliGemma main 与 stable 分别登记。main L0 已有完整50轮历史，但仍未收敛，最低 EMA checkpoint 为 Epoch2，完整2093条评测 Average 35.492。stable L0 当前未登记有效完整评测；其他已登记 stable 层保留其真实分数。

| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| instructblip-vicuna-7b | L0 | 49 | 0.599338 | 0.568572 | 2093 | 37.990 | 36.920 | 33.840 | 100.000 | 52.520 | 52.254 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| instructblip-vicuna-7b | L1 | 43 | 0.711665 | 0.678210 | 2093 | 42.000 | 40.440 | 37.890 | 100.000 | 52.020 | 54.470 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L2 | 37 | 3.260540 | 1.270162 | 2093 | 30.810 | 29.740 | 27.730 | 100.000 | 61.480 | 49.952 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L3 | 47 | 0.504032 | 0.941844 | 2093 | 32.540 | 31.380 | 30.530 | 100.000 | 57.920 | 50.474 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L4 | 37 | 0.620709 | 1.438048 | 2093 | 28.720 | 27.310 | 27.500 | 100.000 | 55.880 | 47.882 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L11 | 46 | 1.284068 | 1.214271 | 2093 | 28.720 | 28.180 | 27.180 | 100.000 | 62.100 | 49.236 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L14 | 40 | 0.440674 | 0.989394 | 2093 | 29.790 | 27.440 | 28.180 | 100.000 | 64.140 | 49.910 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| instructblip-vicuna-7b | L15 | 38 | 0.579282 | 1.232926 | 2093 | 27.750 | 26.460 | 26.740 | 100.000 | 66.350 | 49.460 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| instructblip-vicuna-7b | L16 | 37 | 0.312248 | 1.197859 | 2093 | 27.570 | 26.550 | 26.170 | 100.000 | 69.220 | 49.902 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| instructblip-vicuna-7b | L18 | 50 | 0.409738 | 1.225163 | 2093 | 23.540 | 22.450 | 22.630 | 100.000 | 55.670 | 44.858 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| instructblip-vicuna-7b | L19 | 41 | 2.461512 | 1.400177 | 2093 | 27.690 | 26.050 | 26.680 | 100.000 | 70.670 | 50.218 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| instructblip-vicuna-7b | L25 | 50 | 3.241802 | 0.924779 | 2093 | 28.930 | 28.260 | 28.230 | 100.000 | 73.060 | 51.696 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L26 | 50 | 0.202061 | 0.881081 | 2093 | 29.650 | 28.920 | 27.940 | 100.000 | 70.700 | 51.442 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L27 | 36 | 0.274748 | 0.888490 | 2093 | 29.640 | 28.660 | 28.710 | 100.000 | 74.340 | 52.270 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L28 | 49 | 1.700526 | 1.100682 | 2093 | 29.860 | 28.720 | 28.780 | 100.000 | 79.000 | 53.272 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L0 | 50 | 0.481247 | 0.429186 | 2093 | 41.060 | 36.900 | 38.310 | 100.000 | 72.880 | 57.830 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L1 | 48 | 0.386813 | 0.384318 | 2093 | 61.310 | 58.270 | 59.270 | 100.000 | 76.670 | 71.104 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L2 | 50 | 0.479588 | 0.420997 | 2093 | 49.220 | 45.300 | 46.130 | 100.000 | 76.830 | 63.496 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L7 | 47 | 0.352282 | 0.320426 | 2093 | 51.980 | 49.540 | 49.790 | 100.000 | 84.010 | 67.064 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L8 | 50 | 0.370879 | 0.330787 | 2093 | 55.690 | 53.420 | 53.670 | 100.000 | 82.390 | 69.034 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L9 | 48 | 0.370514 | 0.374562 | 2093 | 40.320 | 38.080 | 38.410 | 100.000 | 81.620 | 59.686 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L10 | 50 | 0.311659 | 0.304353 | 2093 | 68.300 | 65.630 | 65.890 | 100.000 | 85.530 | 77.070 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L14 | 43 | 0.376951 | 0.329464 | 2093 | 46.890 | 43.630 | 44.990 | 100.000 | 81.650 | 63.432 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L15 | 50 | 0.266809 | 0.307395 | 2093 | 49.540 | 46.310 | 46.960 | 100.000 | 77.540 | 64.070 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L16 | 50 | 0.314161 | 0.297508 | 2093 | 49.340 | 46.110 | 46.470 | 100.000 | 82.770 | 64.938 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L17 | 50 | 0.351717 | 0.299282 | 2093 | 47.770 | 46.100 | 45.820 | 100.000 | 79.850 | 63.908 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L18 | 44 | 0.305323 | 0.302507 | 2093 | 40.160 | 37.370 | 38.180 | 100.000 | 82.090 | 59.560 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L19 | 49 | 0.293260 | 0.293898 | 2093 | 38.470 | 36.520 | 37.190 | 100.000 | 79.710 | 58.378 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L22 | 49 | 0.243635 | 0.275690 | 2093 | 40.110 | 37.700 | 37.850 | 100.000 | 77.110 | 58.554 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L24 | 45 | 0.289782 | 0.297207 | 2093 | 39.760 | 33.960 | 37.350 | 100.000 | 77.440 | 57.702 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L25 | 36 | 0.283050 | 0.298860 | 2093 | 40.090 | 37.730 | 37.590 | 100.000 | 76.920 | 58.466 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L26 | 43 | 0.306680 | 0.374355 | 2093 | 39.330 | 34.250 | 36.790 | 100.000 | 75.970 | 57.268 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L28 | 34 | 0.372540 | 0.349210 | 2093 | 39.420 | 36.540 | 37.360 | 100.000 | 78.490 | 58.362 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L29 | 43 | 0.359531 | 0.372103 | 2093 | 39.520 | 37.330 | 37.850 | 100.000 | 77.930 | 58.526 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L30 | 48 | 0.461325 | 0.481391 | 2093 | 41.560 | 38.680 | 39.480 | 100.000 | 69.490 | 57.842 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L31 | 14 | 8.763226 | 10.222642 | 2093 | 23.880 | 24.050 | 25.440 | 100.000 | 100.000 | 54.674 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L0 | 26 | 0.486695 | 0.489312 | 2093 | 45.900 | 40.340 | 41.860 | 100.000 | 74.340 | 60.488 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L1 | 50 | 0.459376 | 0.478102 | 2093 | 43.280 | 37.560 | 40.290 | 100.000 | 70.750 | 58.376 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L2 | 41 | 0.399019 | 0.462631 | 2093 | 59.550 | 56.910 | 57.100 | 100.000 | 71.740 | 69.060 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L5 | 30 | 0.429168 | 0.437470 | 2093 | 60.310 | 55.480 | 56.610 | 100.000 | 78.070 | 70.094 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L6 | 50 | 0.255764 | 0.419622 | 2093 | 58.350 | 54.300 | 57.430 | 100.000 | 72.900 | 68.596 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L7 | 31 | 0.418494 | 0.478424 | 2093 | 42.910 | 36.990 | 40.640 | 100.000 | 68.550 | 57.818 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L14 | 43 | 0.350849 | 0.365037 | 2093 | 42.870 | 37.360 | 40.650 | 100.000 | 77.100 | 59.596 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L15 | 37 | 0.309543 | 0.366532 | 2093 | 44.520 | 39.020 | 40.630 | 100.000 | 78.980 | 60.630 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L16 | 48 | 0.436350 | 0.350793 | 2093 | 50.400 | 45.630 | 47.450 | 100.000 | 81.110 | 64.918 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L24 | 41 | 0.278317 | 0.351265 | 2093 | 52.260 | 44.180 | 42.270 | 100.000 | 73.380 | 62.418 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L25 | 50 | 0.358062 | 0.329184 | 2093 | 50.280 | 44.060 | 41.170 | 100.000 | 68.930 | 60.888 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L26 | 43 | 0.269856 | 0.355572 | 2093 | 51.510 | 43.550 | 42.160 | 100.000 | 77.720 | 62.988 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L27 | 50 | 0.311770 | 0.367348 | 2093 | 52.840 | 44.730 | 41.450 | 100.000 | 73.170 | 62.438 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L28 | 47 | 0.462426 | 0.498747 | 2093 | 50.130 | 43.500 | 41.140 | 100.000 | 69.480 | 60.850 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L30 | 46 | 0.304285 | 0.531518 | 2093 | 41.930 | 37.890 | 35.700 | 100.000 | 70.700 | 57.244 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L31 | 32 | 12.569068 | 9.569223 | 2093 | 32.210 | 30.160 | 28.010 | 100.000 | 100.000 | 58.076 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L0 | 50 | 0.388003 | 0.443953 | 2093 | 53.710 | 43.500 | 34.560 | 100.000 | 82.680 | 62.890 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L1 | 41 | 0.409356 | 0.454254 | 2093 | 53.670 | 42.770 | 34.980 | 100.000 | 75.900 | 61.460 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L2 | 42 | 0.378063 | 0.448366 | 2093 | 53.640 | 45.580 | 36.810 | 100.000 | 75.240 | 62.250 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L3 | 49 | 0.411333 | 0.434602 | 2093 | 53.030 | 43.570 | 34.870 | 100.000 | 76.490 | 61.590 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L6 | 49 | 0.452782 | 0.437895 | 2093 | 55.060 | 43.800 | 35.850 | 100.000 | 80.940 | 63.130 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L10 | 48 | 0.394701 | 0.412794 | 2093 | 54.090 | 44.240 | 34.200 | 100.000 | 82.290 | 62.964 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L11 | 41 | 0.450617 | 0.448930 | 2093 | 53.170 | 43.400 | 35.120 | 100.000 | 77.480 | 61.830 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L12 | 39 | 0.416423 | 0.436754 | 2093 | 54.690 | 44.290 | 35.210 | 100.000 | 79.140 | 62.670 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L14 | 43 | 0.435669 | 0.420537 | 2093 | 54.340 | 44.450 | 35.200 | 100.000 | 82.940 | 63.390 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L15 | 49 | 0.459994 | 0.405599 | 2093 | 52.840 | 42.300 | 35.610 | 100.000 | 81.230 | 62.396 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L16 | 49 | 0.443011 | 0.411539 | 2093 | 52.900 | 41.960 | 36.700 | 100.000 | 82.230 | 62.760 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L17 | 45 | 0.369272 | 0.384334 | 2093 | 53.210 | 42.570 | 34.620 | 100.000 | 82.620 | 62.600 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L18 | 49 | 0.444120 | 0.399728 | 2093 | 53.090 | 44.110 | 37.700 | 100.000 | 82.870 | 63.554 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L19 | 41 | 0.417306 | 0.385106 | 2093 | 53.540 | 43.090 | 35.500 | 100.000 | 83.900 | 63.206 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L20 | 48 | 0.343881 | 0.375257 | 2093 | 52.620 | 41.400 | 33.990 | 100.000 | 82.550 | 62.112 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L21 | 49 | 0.444941 | 0.365603 | 2093 | 53.830 | 43.820 | 36.610 | 100.000 | 84.450 | 63.740 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L22 | 50 | 0.413212 | 0.390550 | 2093 | 54.060 | 43.140 | 35.300 | 100.000 | 81.580 | 62.820 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L24 | 47 | 0.328337 | 0.385822 | 2093 | 52.540 | 43.060 | 35.300 | 100.000 | 83.060 | 62.790 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L26 | 48 | 0.407629 | 0.382820 | 2093 | 52.760 | 42.320 | 35.420 | 100.000 | 81.150 | 62.330 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L27 | 35 | 0.303852 | 0.368658 | 2093 | 52.340 | 41.680 | 33.110 | 100.000 | 82.590 | 61.944 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L28 | 50 | 0.374178 | 0.364763 | 2093 | 53.480 | 43.140 | 35.200 | 100.000 | 80.810 | 62.526 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L29 | 49 | 0.396721 | 0.371691 | 2093 | 53.430 | 43.600 | 34.390 | 100.000 | 80.430 | 62.370 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L30 | 49 | 0.402044 | 0.378223 | 2093 | 53.300 | 42.720 | 34.770 | 100.000 | 81.810 | 62.520 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L31 | 49 | 0.233540 | 0.360590 | 2093 | 52.680 | 42.050 | 35.470 | 100.000 | 85.060 | 63.052 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L34 | 42 | 0.436983 | 0.584563 | 2093 | 53.150 | 42.200 | 33.650 | 100.000 | 84.860 | 62.770 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L35 | 49 | 8.960615 | 7.367229 | 2093 | 49.910 | 37.430 | 22.230 | 100.000 | 100.000 | 61.914 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L0 | 2 | 3187.056885 | 3209.824510 | 2093 | 0.160 | 0.180 | 0.160 | 100.000 | 76.960 | 35.492 | TRAIN_DONE_MAIN50_EVAL_DONE_NONCONVERGENT_VERIFIED_20260928 |
| paligemma-3b | L1 | 14 | 13.376622 | 14.049339 | 2093 | 8.240 | 13.070 | 8.790 | 100.000 | 63.990 | 38.820 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L3 | 38 | 0.605178 | 0.531071 | 2093 | 85.630 | 85.860 | 89.210 | 100.000 | 67.900 | 85.720 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L4 | 38 | 7.798694 | 6.942612 | 2093 | 74.080 | 76.080 | 74.690 | 100.000 | 30.780 | 71.130 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L5 | 2 | 2.871534 | 4.631819 | 2093 | 85.300 | 83.960 | 86.800 | 100.000 | 34.780 | 78.170 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L6 | 31 | 3.886672 | 5.983205 | 2093 | 58.140 | 64.420 | 67.890 | 100.000 | 42.920 | 66.670 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L7 | 10 | 3.521098 | 4.525994 | 2093 | 82.020 | 80.300 | 84.320 | 100.000 | 31.600 | 75.650 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L8 | 3 | 4.863270 | 3.294556 | 2093 | 91.110 | 91.370 | 93.320 | 100.000 | 29.180 | 81.000 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L9 | 1 | 17.538765 | 20.548170 | 2093 | 0.540 | 0.810 | 0.450 | 100.000 | 78.980 | 36.156 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| paligemma-3b | L10 | 1 | 6.230244 | 9.293444 | 2093 | 77.440 | 82.520 | 79.770 | 100.000 | 12.850 | 70.516 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L11 | 2 | 2.080458 | 3.296938 | 2093 | 87.130 | 87.760 | 88.630 | 100.000 | 41.440 | 80.992 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L12 | 1 | 4.603746 | 5.001783 | 2093 | 84.510 | 85.980 | 85.000 | 100.000 | 24.430 | 75.984 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L14 | 1 | 14.575245 | -1369.521638 | 2093 | 5.590 | 9.060 | 4.750 | 100.000 | 40.890 | 32.058 | TRAIN_DONE_MAIN50_EVAL_DONE_NUMERIC_INSTABILITY_SELECTION_HISTORY_MISMATCH_VERIFIED_20260928 |
| paligemma-3b | L15 | 25 | 22.580488 | 31.500783 | 2093 | 0.180 | 0.230 | 0.140 | 100.000 | 100.000 | 40.110 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L17 | 2 | 30.357973 | 30.934000 | 2093 | 0.180 | 0.230 | 0.140 | 100.000 | 100.000 | 40.110 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L1 | 46 | 0.945888 | 1.149873 | 2093 | 77.650 | 77.270 | 93.930 | 100.000 | 56.470 | 81.060 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L4 | 50 | 0.591566 | 0.491418 | 2093 | 66.090 | 64.750 | 85.620 | 100.000 | 77.500 | 78.790 | TRAIN_DONE_STABLE_RETRY_NUMERIC_GUARD_NONFINITE_SKIP16_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L5 | 46 | 0.596487 | 0.554996 | 2093 | 77.020 | 77.960 | 89.710 | 100.000 | 69.930 | 82.920 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L6 | 50 | 0.423632 | 0.468850 | 2093 | 69.940 | 69.130 | 89.830 | 100.000 | 68.920 | 79.560 | TRAIN_DONE_STABLE_RETRY_BUFFER1_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L7 | 43 | 0.973857 | 0.609388 | 2093 | 82.250 | 81.340 | 91.160 | 100.000 | 67.180 | 84.390 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L8 | 38 | 0.801614 | 0.593724 | 2093 | 78.950 | 76.170 | 93.020 | 100.000 | 65.090 | 82.650 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L17 | 23 | 26.938894 | 29.851553 | 2093 | 0.180 | 0.230 | 0.140 | 100.000 | 100.000 | 40.110 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L0 | 50 | 0.445026 | 0.452992 | 2093 | 64.020 | 59.530 | 57.190 | 100.000 | 69.100 | 69.970 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L1 | 47 | 0.449670 | 0.456147 | 2093 | 46.200 | 40.210 | 35.590 | 100.000 | 71.860 | 58.770 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L2 | 48 | 0.429149 | 0.437729 | 2093 | 55.620 | 51.140 | 47.700 | 100.000 | 67.590 | 64.410 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L3 | 45 | 0.445100 | 0.442415 | 2093 | 58.430 | 52.940 | 49.940 | 100.000 | 71.470 | 66.560 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L5 | 42 | 0.402913 | 0.428878 | 2093 | 56.180 | 50.600 | 45.960 | 100.000 | 74.070 | 65.362 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L7 | 45 | 0.398488 | 0.419556 | 2093 | 60.390 | 55.030 | 51.650 | 100.000 | 75.170 | 68.450 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L8 | 48 | 0.401016 | 0.404693 | 2093 | 53.380 | 48.670 | 43.400 | 100.000 | 74.440 | 63.980 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L9 | 50 | 0.390892 | 0.384298 | 2093 | 58.690 | 54.300 | 50.420 | 100.000 | 76.890 | 68.060 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L10 | 48 | 0.404036 | 0.384991 | 2093 | 61.900 | 58.080 | 53.550 | 100.000 | 75.510 | 69.810 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L11 | 46 | 0.406657 | 0.396586 | 2093 | 57.700 | 52.140 | 47.720 | 100.000 | 78.630 | 67.240 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L12 | 42 | 0.376879 | 0.402297 | 2093 | 49.120 | 42.070 | 38.850 | 100.000 | 79.600 | 61.928 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L13 | 50 | 0.364526 | 0.381850 | 2093 | 44.800 | 40.220 | 34.160 | 100.000 | 78.070 | 59.450 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L14 | 50 | 0.405853 | 0.384188 | 2093 | 58.450 | 52.680 | 49.760 | 100.000 | 80.210 | 68.220 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L15 | 46 | 0.347375 | 0.362945 | 2093 | 45.800 | 39.490 | 34.580 | 100.000 | 78.830 | 59.740 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L16 | 41 | 0.373067 | 0.409362 | 2093 | 46.250 | 39.290 | 33.880 | 100.000 | 75.060 | 58.896 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L17 | 46 | 0.357996 | 0.383906 | 2093 | 44.360 | 39.140 | 33.170 | 100.000 | 77.570 | 58.848 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L19 | 40 | 0.380004 | 0.381024 | 2093 | 45.040 | 38.910 | 33.380 | 100.000 | 69.210 | 57.308 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L20 | 48 | 0.382679 | 0.383377 | 2093 | 45.090 | 39.200 | 33.920 | 100.000 | 67.530 | 57.150 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L21 | 47 | 0.500128 | 0.415271 | 2093 | 43.910 | 37.520 | 33.370 | 100.000 | 67.030 | 56.366 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L22 | 50 | 0.427672 | 0.488335 | 2093 | 42.440 | 36.700 | 31.770 | 100.000 | 68.450 | 55.872 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |

#### MMKE-visual

**2026-09-26 服务器复核与 main 恢复评测：** main 原运行的 L1、L2、L6、L7、L13 已有完整50轮及293条评测，本次补齐漏记；L3、L5 原训练发生非有限梯度并被停滞监控终止，现已直接评测原 checkpoint，分别为30.540、62.544。当前 main 共16层有实际评测，其中13层训练完成50轮，L0/L3/L5为训练未完成的恢复评测。“已评测”不等于“已收敛”或“完成50轮”。stable 单列保留，不再以 stable 高分替换 main 低分；先前其他章节的覆盖统计属于历史快照，不据此自动增加完整50轮可比组数。详情见 `outputs/paligemma_visual_server_audit_20260926/PaliGemma_main停训原因与直接评测结果.md`。

已登记完整评测（2026-09-28同步）：`blip2-opt-2.7b` main 19 层；`instructblip-vicuna-7b` main 22 层；`minigpt-4-vicuna-7b` main 21 层；`llava-v1.5-7b` main 16 层；`qwen2.5-vl-3b` main 23 层；`paligemma-3b` main 16 层、stable 15 层；`smolvlm-1.7b` main 21 层。这里的“已评测”包括明确列出的恢复/诊断结果，不等同于全部训练收敛或全部完整50轮。

补充说明：`paligemma-3b` 原始 run 的 7 层结果保留不动；其后追加 2026-07-13 的 PaliGemma-stable 补跑结果，来源为服务器目录 `paligemma_stable_mmke_visual_top3_union_20260713_1120`。stable 补跑中 `L8` 训练到 epoch 13 后中断，已保护现场并使用 epoch 13 checkpoint 手动完成 full eval，因此状态单独标记为 `TRAIN_DONE_MANUAL_EPOCH13`。

2026-07-14 至 2026-07-15 在 Slurm job `3044208`（g09/GPU0）继续完成 PaliGemma-stable MMKE-visual 目标层 `L7,L13,L0,L5,L6,L3,L2,L1`，结果目录为 `paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b`。其中 `L7,L13,L5,L6,L3,L2,L1` 均存在非空 `selected_checkpoint.tsv` 和 `eval_full.done`，full eval 使用独立 MMKE-visual eval JSON（293 samples），计为完成。`L0` 使用 `paligemma-3b-stable-l0.yaml` 训练至 epoch 26 的 212/214 step，但 EMA loss 长期约为 3.4k--3.5k，且反复出现整层 `PALIGEMMA_STABLE_SKIP_NONFINITE_STEP`，判定为未收敛；最后一次保存又触发 `PytorchStreamWriter file write failed / unexpected pos`，未生成 selected checkpoint，未运行 eval，状态记录为 `FAILED_NONCONVERGENT_CKPT_WRITE_ERROR_NO_EVAL`。目录根部的 `ALL_DONE` 由单层 runner 写入，不能作为 8 层完成依据；本批实际为 7/8 完成。

PaliGemma 表项版本划分（按下表中的状态字段识别，不依赖易变化的文件行号）：

- `TRAIN_DONE_MAIN`：主实验配置 `configs/vead/paligemma-3b.yaml`，对应原始 run 的 `L8,L9,L10,L11,L12,L14,L17`。
- `TRAIN_DONE_MANUAL_EPOCH13` / `TRAIN_DONE_STABLE`：2026-07-13 stable 配置补跑，对应 `L8,L9,L10,L11,L12,L14,L17`；其中 L8 为 epoch 13 checkpoint 手动 full eval。
- `TRAIN_DONE_STABLE_JOB3044208`：job 3044208 stable 配置补跑，对应 `L1,L2,L3,L5,L6,L7,L13`，使用 `configs/vead/paligemma-3b-stable.yaml`。
- `FAILED_STABLE_L0_NONCONVERGENT_CKPT_WRITE_ERROR_NO_EVAL`：job 3044208 的 L0 stable 专用配置 `configs/vead/paligemma-3b-stable-l0.yaml`；未收敛且未评测，不属于主实验版本，也不计入完成结果。

PaliGemma 当前记录规则（2026-09-26，按用户要求更新）：保留原 main 训练轨迹与实际评测分数。出现数值异常或中断时，只要原 checkpoint 参数有限且可读取，即可按原评测协议直接评测，并明确标注训练预算完成情况；不能把低分、失败或中断静默删除，也不以 stable 分数替换。历史 stable 作为单独配方结果保留。所有定位公式必须复用同一个固定层—结果映射。完整50轮分析与包含失败/中断恢复结果的实际运行分析分别统计。

| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| blip2-opt-2.7b | L0 | 50 | 1.835244 | 2.004923 | 293 | 53.130 | 53.140 | 53.200 | 100.000 | 52.380 | 62.370 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L1 | 50 | 0.516416 | 0.520349 | 293 | 52.090 | 51.800 | 51.970 | 100.000 | 92.600 | 69.692 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L2 | 44 | 0.813470 | 1.107170 | 293 | 52.040 | 51.910 | 51.580 | 100.000 | 93.800 | 69.866 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L3 | 50 | 0.584310 | 0.958273 | 293 | 52.010 | 51.650 | 52.370 | 100.000 | 87.680 | 68.742 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L4 | 49 | 0.491591 | 0.601247 | 293 | 51.780 | 51.720 | 51.600 | 100.000 | 90.850 | 69.190 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L14 | 50 | 0.476014 | 0.465106 | 293 | 51.320 | 51.110 | 50.760 | 100.000 | 97.160 | 70.070 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L15 | 47 | 0.360871 | 0.334112 | 293 | 53.410 | 53.310 | 53.200 | 100.000 | 97.030 | 71.390 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L16 | 48 | 0.384157 | 0.416895 | 293 | 52.710 | 52.600 | 52.190 | 100.000 | 97.330 | 70.966 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L17 | 48 | 0.385966 | 0.438426 | 293 | 53.090 | 53.050 | 52.890 | 100.000 | 97.050 | 71.216 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L18 | 45 | 0.326844 | 0.400918 | 293 | 53.000 | 52.950 | 53.120 | 100.000 | 97.370 | 71.288 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L19 | 49 | 0.241281 | 0.346198 | 293 | 53.870 | 53.610 | 53.410 | 100.000 | 95.950 | 71.368 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L20 | 45 | 0.679693 | 0.413794 | 293 | 53.800 | 53.800 | 53.530 | 100.000 | 97.940 | 71.814 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L21 | 49 | 0.364866 | 0.352452 | 293 | 53.540 | 53.670 | 53.370 | 100.000 | 98.090 | 71.734 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L22 | 49 | 0.330121 | 0.370491 | 293 | 54.380 | 54.320 | 54.200 | 100.000 | 97.690 | 72.118 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L24 | 44 | 0.414978 | 0.417396 | 293 | 53.860 | 53.790 | 53.650 | 100.000 | 95.480 | 71.356 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L25 | 46 | 0.387067 | 0.575704 | 293 | 53.670 | 53.550 | 53.470 | 100.000 | 96.650 | 71.468 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L26 | 49 | 0.681283 | 0.788690 | 293 | 53.060 | 53.290 | 53.230 | 100.000 | 95.840 | 71.084 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L29 | 48 | 4.021954 | 2.907863 | 293 | 49.960 | 49.850 | 49.730 | 100.000 | 96.970 | 69.302 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L30 | 48 | 5.169809 | 5.331725 | 293 | 44.260 | 44.010 | 44.240 | 100.000 | 96.330 | 65.768 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L0 | 50 | 0.171615 | 0.222510 | 293 | 52.260 | 52.420 | 52.170 | 100.000 | 99.620 | 71.294 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L1 | 50 | 0.231107 | 0.292772 | 293 | 51.700 | 51.670 | 51.550 | 100.000 | 96.480 | 70.280 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L2 | 46 | 6.189603 | 6.830468 | 293 | 18.670 | 16.650 | 18.500 | 100.000 | 99.570 | 50.678 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L3 | 47 | 5.070473 | 6.227147 | 293 | 19.400 | 17.340 | 19.200 | 100.000 | 99.850 | 51.158 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L4 | 49 | 7.357730 | 7.321517 | 293 | 17.380 | 15.280 | 17.580 | 100.000 | 99.050 | 49.858 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L5 | 49 | 6.999227 | 7.345585 | 293 | 17.030 | 14.840 | 17.130 | 100.000 | 99.510 | 49.702 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L14 | 50 | 5.457262 | 6.049061 | 293 | 17.340 | 15.970 | 17.240 | 100.000 | 99.570 | 50.024 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L15 | 47 | 7.049882 | 6.446094 | 293 | 17.080 | 16.010 | 16.990 | 100.000 | 99.850 | 49.986 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L16 | 48 | 8.969355 | 7.001298 | 293 | 18.080 | 17.110 | 17.960 | 100.000 | 99.630 | 50.556 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L17 | 50 | 7.270292 | 6.931965 | 293 | 18.470 | 16.800 | 18.640 | 100.000 | 99.730 | 50.728 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L18 | 50 | 6.697884 | 6.893876 | 293 | 18.080 | 16.550 | 18.220 | 100.000 | 99.600 | 50.490 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L19 | 49 | 5.929656 | 5.769108 | 293 | 18.560 | 16.420 | 18.600 | 100.000 | 99.590 | 50.634 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L20 | 50 | 5.900426 | 6.889282 | 293 | 18.520 | 17.290 | 18.680 | 100.000 | 99.900 | 50.878 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L22 | 46 | 6.008149 | 6.773030 | 293 | 17.870 | 16.800 | 17.620 | 100.000 | 100.000 | 50.458 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L23 | 50 | 5.294744 | 6.377842 | 293 | 18.060 | 16.630 | 17.960 | 100.000 | 99.730 | 50.476 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L24 | 47 | 6.654134 | 7.255629 | 293 | 18.210 | 16.780 | 18.190 | 100.000 | 99.760 | 50.588 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L25 | 46 | 5.746799 | 6.995333 | 293 | 17.410 | 15.670 | 17.230 | 100.000 | 99.730 | 50.008 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L26 | 49 | 6.737056 | 7.514501 | 293 | 17.550 | 15.300 | 17.370 | 100.000 | 99.630 | 49.970 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L27 | 48 | 6.786605 | 7.596408 | 293 | 18.470 | 16.750 | 18.570 | 100.000 | 99.180 | 50.594 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L28 | 49 | 5.810029 | 7.744205 | 293 | 17.320 | 15.620 | 17.060 | 100.000 | 99.830 | 49.966 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L30 | 45 | 10.282062 | 11.521651 | 293 | 11.750 | 11.080 | 11.620 | 100.000 | 99.320 | 46.754 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L31 | 28 | 36.477367 | 36.696703 | 293 | 0.040 | 0.040 | 0.040 | 100.000 | 100.000 | 40.024 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L0 | 50 | 0.269117 | 0.267466 | 293 | 59.950 | 60.020 | 60.140 | 100.000 | 98.950 | 75.812 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| minigpt-4-vicuna-7b | L1 | 50 | 0.272173 | 0.281973 | 293 | 60.320 | 60.320 | 60.550 | 100.000 | 97.930 | 75.824 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| minigpt-4-vicuna-7b | L2 | 41 | 0.253623 | 0.267989 | 293 | 60.350 | 60.400 | 60.640 | 100.000 | 98.930 | 76.064 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| minigpt-4-vicuna-7b | L3 | 36 | 0.254035 | 0.288644 | 293 | 61.410 | 61.600 | 61.070 | 100.000 | 99.090 | 76.634 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| minigpt-4-vicuna-7b | L5 | 35 | 0.258817 | 0.281105 | 293 | 62.090 | 62.040 | 61.860 | 100.000 | 98.730 | 76.944 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L8 | 49 | 0.265526 | 0.256176 | 293 | 61.750 | 61.620 | 61.680 | 100.000 | 97.910 | 76.592 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L9 | 49 | 0.247979 | 0.257039 | 293 | 61.340 | 61.270 | 61.410 | 100.000 | 98.890 | 76.582 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L10 | 36 | 0.247014 | 0.260045 | 293 | 61.510 | 61.480 | 61.420 | 100.000 | 98.740 | 76.630 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L11 | 39 | 0.287227 | 0.272469 | 293 | 62.030 | 61.780 | 61.970 | 100.000 | 98.370 | 76.830 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L14 | 50 | 0.234949 | 0.249512 | 293 | 61.070 | 60.940 | 60.840 | 100.000 | 98.880 | 76.346 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L15 | 50 | 0.242507 | 0.251438 | 293 | 60.390 | 60.220 | 60.110 | 100.000 | 98.640 | 75.872 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L16 | 33 | 0.238199 | 0.268302 | 293 | 61.010 | 60.870 | 60.750 | 100.000 | 97.860 | 76.098 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L17 | 49 | 0.249406 | 0.265122 | 293 | 59.810 | 59.860 | 59.900 | 100.000 | 97.140 | 75.342 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L18 | 46 | 0.269364 | 0.262238 | 293 | 59.330 | 59.180 | 59.410 | 100.000 | 98.000 | 75.184 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L24 | 49 | 0.502779 | 0.438395 | 293 | 57.990 | 57.940 | 58.050 | 100.000 | 97.300 | 74.256 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L25 | 50 | 0.759646 | 0.611862 | 293 | 57.890 | 57.730 | 57.740 | 100.000 | 98.250 | 74.322 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L26 | 49 | 0.676290 | 0.788584 | 293 | 57.320 | 56.970 | 57.300 | 100.000 | 98.060 | 73.930 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L27 | 43 | 0.908072 | 1.413074 | 293 | 57.880 | 57.600 | 57.520 | 100.000 | 97.970 | 74.194 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L28 | 45 | 1.148645 | 1.711778 | 293 | 57.960 | 57.920 | 57.850 | 100.000 | 98.460 | 74.438 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L29 | 48 | 3.022602 | 2.115868 | 293 | 56.550 | 56.180 | 56.370 | 100.000 | 97.230 | 73.266 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| minigpt-4-vicuna-7b | L31 | 43 | 6.683348 | 7.304613 | 293 | 47.210 | 46.580 | 46.990 | 100.000 | 100.000 | 68.156 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L0 | 40 | 0.229806 | 0.314945 | 293 | 60.740 | 60.790 | 60.880 | 100.000 | 93.380 | 75.158 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L1 | 47 | 0.268086 | 0.302343 | 293 | 61.270 | 61.210 | 61.560 | 100.000 | 94.160 | 75.640 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L2 | 33 | 0.281384 | 0.305978 | 293 | 63.430 | 63.240 | 63.390 | 100.000 | 93.870 | 76.786 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L3 | 22 | 0.185736 | 0.301791 | 293 | 62.320 | 62.230 | 62.340 | 100.000 | 94.040 | 76.186 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L7 | 35 | 0.214817 | 0.286848 | 293 | 62.210 | 62.150 | 62.300 | 100.000 | 96.100 | 76.552 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L8 | 47 | 0.181363 | 0.260420 | 293 | 62.930 | 62.850 | 62.660 | 100.000 | 96.600 | 77.008 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L9 | 40 | 0.400646 | 0.281962 | 293 | 62.640 | 62.660 | 62.690 | 100.000 | 96.560 | 76.910 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L12 | 47 | 0.173525 | 0.243153 | 293 | 61.630 | 61.640 | 61.520 | 100.000 | 95.560 | 76.070 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L14 | 47 | 0.146300 | 0.248103 | 293 | 62.030 | 62.070 | 62.330 | 100.000 | 96.140 | 76.514 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L15 | 40 | 0.119042 | 0.231111 | 293 | 61.020 | 61.000 | 60.910 | 100.000 | 95.830 | 75.752 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L16 | 21 | 0.202061 | 0.291990 | 293 | 60.640 | 60.330 | 60.580 | 100.000 | 97.150 | 75.740 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L22 | 50 | 0.280591 | 0.381777 | 293 | 57.520 | 57.340 | 57.480 | 100.000 | 96.860 | 73.840 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L24 | 48 | 0.199074 | 0.292995 | 293 | 58.400 | 58.070 | 58.420 | 100.000 | 98.040 | 74.586 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L26 | 49 | 0.432336 | 0.546802 | 293 | 57.410 | 57.080 | 57.270 | 100.000 | 95.360 | 73.424 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L27 | 48 | 0.281177 | 0.556985 | 293 | 58.830 | 58.380 | 58.660 | 100.000 | 96.110 | 74.396 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L28 | 49 | 0.446779 | 0.996580 | 293 | 57.580 | 57.490 | 57.990 | 100.000 | 94.570 | 73.526 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L0 | 45 | 0.470173 | 0.677373 | 293 | 52.740 | 52.900 | 52.280 | 100.000 | 94.200 | 70.420 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L1 | 47 | 1.164370 | 0.680025 | 293 | 51.090 | 51.080 | 51.240 | 100.000 | 94.010 | 69.480 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L2 | 43 | 0.670088 | 0.893235 | 293 | 51.750 | 51.640 | 51.720 | 100.000 | 94.520 | 69.930 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L3 | 47 | 0.423464 | 0.665823 | 293 | 51.450 | 51.290 | 51.340 | 100.000 | 94.830 | 69.782 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L6 | 45 | 0.499272 | 0.734185 | 293 | 52.380 | 52.010 | 51.850 | 100.000 | 94.510 | 70.150 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L7 | 49 | 0.474863 | 0.731563 | 293 | 52.590 | 52.390 | 52.380 | 100.000 | 94.970 | 70.470 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L8 | 47 | 0.389735 | 0.593588 | 293 | 52.580 | 52.640 | 52.330 | 100.000 | 96.670 | 70.840 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L9 | 50 | 0.394751 | 0.598401 | 293 | 51.680 | 51.270 | 51.610 | 100.000 | 92.830 | 69.480 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L10 | 47 | 0.332733 | 0.533539 | 293 | 53.240 | 53.230 | 53.600 | 100.000 | 95.160 | 71.046 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L11 | 48 | 0.539290 | 0.561360 | 293 | 53.340 | 53.130 | 53.010 | 100.000 | 95.510 | 71.000 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L12 | 47 | 0.458533 | 0.499579 | 293 | 52.610 | 52.220 | 52.870 | 100.000 | 97.300 | 71.000 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L13 | 48 | 0.461817 | 0.418149 | 293 | 51.510 | 51.340 | 52.220 | 100.000 | 96.890 | 70.390 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L14 | 43 | 0.517781 | 0.504366 | 293 | 52.100 | 51.900 | 51.960 | 100.000 | 93.120 | 69.820 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L16 | 49 | 0.419709 | 0.486438 | 293 | 51.800 | 51.510 | 51.760 | 100.000 | 93.990 | 69.810 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L17 | 49 | 0.335644 | 0.397961 | 293 | 51.160 | 51.100 | 51.510 | 100.000 | 94.250 | 69.600 | TRAIN_DONE_EXISTING_CKPT_EVAL_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L18 | 46 | 0.441055 | 0.438478 | 293 | 52.690 | 52.250 | 52.480 | 100.000 | 95.820 | 70.650 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L19 | 50 | 0.359075 | 0.417327 | 293 | 51.610 | 51.090 | 51.450 | 100.000 | 95.520 | 69.930 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L20 | 45 | 0.245531 | 0.482954 | 293 | 51.940 | 51.650 | 51.860 | 100.000 | 96.560 | 70.400 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L22 | 50 | 0.550950 | 0.494701 | 293 | 51.810 | 51.300 | 51.860 | 100.000 | 96.730 | 70.340 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L26 | 43 | 0.537117 | 0.583348 | 293 | 49.130 | 48.830 | 48.950 | 100.000 | 94.400 | 68.260 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L27 | 48 | 0.393821 | 0.756435 | 293 | 48.990 | 48.980 | 48.750 | 100.000 | 93.870 | 68.120 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L28 | 43 | 0.595793 | 1.006616 | 293 | 49.890 | 49.350 | 49.900 | 100.000 | 92.600 | 68.350 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L30 | 48 | 1.174112 | 1.430872 | 293 | 47.650 | 47.290 | 47.560 | 100.000 | 92.740 | 67.050 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L0 | 1 | 3465.718750 | 3508.007406 | 293 | 0.100 | 0.080 | 0.090 | 100.000 | 92.330 | 38.520 | EVAL_DONE_MAIN_RECOVERED_TRAIN_BUDGET_NOT_VERIFIED_NONCONVERGENT_VERIFIED_20260928 |
| paligemma-3b | L1 | 9 | 28.518827 | 30.787377 | 293 | 0.090 | 0.080 | 0.100 | 100.000 | 97.950 | 39.644 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L2 | 3 | 2.979825 | 1.682528 | 293 | 94.680 | 94.880 | 94.400 | 100.000 | 17.230 | 80.238 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L3 | 7 | 21.378290 | 22.591008 | 293 | 16.410 | 16.530 | 16.690 | 100.000 | 3.070 | 30.540 | EVAL_DONE_MAIN_RECOVERED_TRAIN_BUDGET_NOT_VERIFIED_NUMERIC_INSTABILITY_VERIFIED_20260928 |
| paligemma-3b | L4 | 39 | 0.332606 | 0.330234 | 293 | 99.230 | 99.220 | 98.680 | 100.000 | 98.000 | 99.026 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L5 | 1 | 8.847749 | 9.046796 | 293 | 55.510 | 55.680 | 56.140 | 100.000 | 45.390 | 62.544 | EVAL_DONE_MAIN_RECOVERED_TRAIN_BUDGET_NOT_VERIFIED_NUMERIC_INSTABILITY_VERIFIED_20260928 |
| paligemma-3b | L6 | 2 | 0.841218 | 1.231970 | 293 | 95.380 | 95.420 | 95.310 | 100.000 | 91.330 | 95.488 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L7 | 2 | 1.615333 | 1.543866 | 293 | 94.790 | 94.810 | 94.750 | 100.000 | 82.700 | 93.410 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L8 | 2 | 3.971717 | 2.536566 | 293 | 95.130 | 95.160 | 95.190 | 100.000 | 70.960 | 91.288 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L9 | 6 | 0.444634 | 0.517213 | 293 | 98.790 | 98.830 | 98.690 | 100.000 | 94.160 | 98.094 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L10 | 24 | 0.343096 | 0.348760 | 293 | 98.970 | 98.980 | 98.910 | 100.000 | 98.420 | 99.056 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L11 | 7 | 0.579804 | 0.737678 | 293 | 96.100 | 96.050 | 95.710 | 100.000 | 97.490 | 97.070 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L12 | 50 | 0.290716 | 0.401058 | 293 | 95.530 | 95.580 | 95.550 | 100.000 | 97.740 | 96.880 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L13 | 19 | 18.990540 | 18.644390 | 293 | 0.250 | 0.250 | 0.280 | 100.000 | 99.430 | 40.042 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L14 | 1 | 17.459480 | -351.953961 | 293 | 0.900 | 1.010 | 0.880 | 100.000 | 92.340 | 39.026 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L17 | 6 | 30.490068 | 30.831037 | 293 | 0.080 | 0.080 | 0.090 | 100.000 | 100.000 | 40.050 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L0 | 25 | 3402.662842 | 3454.815660 | 293 | 0.090 | 0.090 | 0.100 | 100.000 | 76.930 | 35.442 | EVAL_DONE_STABLE_RECOVERED_TRAIN_BUDGET_NOT_VERIFIED_NONCONVERGENT_VERIFIED_20260928 |
| paligemma-3b | L1 | 49 | 0.334160 | 0.355574 | 293 | 97.760 | 97.700 | 96.650 | 100.000 | 98.390 | 98.100 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L2 | 44 | 0.346728 | 0.154634 | 293 | 99.340 | 99.350 | 97.650 | 100.000 | 96.000 | 98.468 | TRAIN_DONE_STABLE50_EVAL_DONE_SELECTION_HISTORY_MISMATCH_VERIFIED_20260928 |
| paligemma-3b | L3 | 46 | 0.342673 | 0.347433 | 293 | 97.330 | 97.260 | 96.680 | 100.000 | 98.230 | 97.900 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L5 | 45 | 0.351702 | 0.347726 | 293 | 98.910 | 98.890 | 97.910 | 100.000 | 97.200 | 98.582 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L6 | 47 | 0.334160 | 0.348006 | 293 | 97.490 | 97.560 | 96.670 | 100.000 | 98.120 | 97.968 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L7 | 49 | 0.354043 | 0.352879 | 293 | 98.540 | 98.450 | 98.170 | 100.000 | 96.840 | 98.400 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L8 | 13 | 0.498305 | 0.587410 | 293 | 96.900 | 96.930 | 96.430 | 100.000 | 94.330 | 96.918 | EVAL_DONE_STABLE_RECOVERED_TRAIN_BUDGET_NOT_VERIFIED_MANUAL_EPOCH13_VERIFIED_20260928 |
| paligemma-3b | L9 | 50 | 0.351273 | 0.358913 | 293 | 98.500 | 98.470 | 98.230 | 100.000 | 96.390 | 98.318 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L10 | 47 | 0.343897 | 0.354527 | 293 | 98.430 | 98.420 | 98.490 | 100.000 | 97.240 | 98.516 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L11 | 50 | 0.404692 | 0.473600 | 293 | 96.340 | 96.210 | 96.330 | 100.000 | 96.850 | 97.146 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L12 | 33 | 0.785029 | 0.381374 | 293 | 94.820 | 94.820 | 94.730 | 100.000 | 94.930 | 95.860 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L13 | 48 | 1.357916 | 1.455967 | 293 | 87.340 | 87.260 | 87.560 | 100.000 | 95.490 | 91.530 | TRAIN_DONE_STABLE50_EVAL_DONE_SELECTION_HISTORY_MISMATCH_VERIFIED_20260928 |
| paligemma-3b | L14 | 50 | 10.762311 | 11.484160 | 293 | 32.640 | 32.850 | 32.570 | 100.000 | 96.280 | 58.868 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L17 | 6 | 30.519789 | 30.862625 | 293 | 0.080 | 0.080 | 0.090 | 100.000 | 100.000 | 40.050 | TRAIN_DONE_STABLE50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L0 | 41 | 0.450055 | 0.435366 | 293 | 54.330 | 54.210 | 54.120 | 100.000 | 94.160 | 71.360 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L1 | 50 | 0.362595 | 0.523996 | 293 | 52.510 | 52.190 | 52.520 | 100.000 | 93.680 | 70.180 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L2 | 46 | 0.367433 | 0.411423 | 293 | 52.960 | 52.770 | 53.140 | 100.000 | 93.740 | 70.522 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L4 | 44 | 0.394254 | 0.523291 | 293 | 52.730 | 52.960 | 52.590 | 100.000 | 94.390 | 70.530 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L5 | 49 | 0.532208 | 0.448303 | 293 | 52.160 | 52.310 | 52.520 | 100.000 | 94.620 | 70.322 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L6 | 44 | 0.388501 | 0.489452 | 293 | 51.880 | 51.720 | 52.370 | 100.000 | 93.440 | 69.880 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L7 | 47 | 1.079098 | 0.479630 | 293 | 53.440 | 53.300 | 53.540 | 100.000 | 93.580 | 70.770 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L8 | 50 | 0.445105 | 0.519847 | 293 | 51.720 | 51.440 | 51.800 | 100.000 | 93.350 | 69.660 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L9 | 50 | 0.425834 | 0.489161 | 293 | 51.150 | 50.990 | 51.220 | 100.000 | 93.880 | 69.450 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L10 | 50 | 0.374906 | 0.415141 | 293 | 51.350 | 51.250 | 51.260 | 100.000 | 92.850 | 69.340 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L11 | 42 | 0.577633 | 0.520159 | 293 | 51.490 | 51.390 | 51.340 | 100.000 | 93.860 | 69.620 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L12 | 50 | 0.359039 | 0.477444 | 293 | 50.020 | 49.730 | 49.950 | 100.000 | 92.880 | 68.516 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L13 | 50 | 0.324814 | 0.407615 | 293 | 52.180 | 51.900 | 51.810 | 100.000 | 93.270 | 69.832 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L14 | 40 | 0.521079 | 0.537226 | 293 | 49.680 | 49.320 | 49.610 | 100.000 | 94.600 | 68.642 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L15 | 47 | 0.543355 | 0.544850 | 293 | 49.660 | 49.270 | 49.840 | 100.000 | 93.640 | 68.482 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L16 | 48 | 0.553617 | 0.595523 | 293 | 47.770 | 47.400 | 47.340 | 100.000 | 93.430 | 67.188 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L17 | 48 | 0.749514 | 0.654440 | 293 | 47.840 | 47.700 | 48.110 | 100.000 | 92.580 | 67.246 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L18 | 50 | 1.323157 | 1.739675 | 293 | 50.040 | 49.600 | 49.990 | 100.000 | 89.840 | 67.890 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L19 | 49 | 2.573995 | 2.826347 | 293 | 48.910 | 48.480 | 48.830 | 100.000 | 90.480 | 67.340 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L20 | 49 | 6.606372 | 4.496605 | 293 | 48.570 | 48.320 | 48.730 | 100.000 | 91.400 | 67.404 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L21 | 42 | 2.808244 | 3.857834 | 293 | 49.340 | 49.050 | 49.220 | 100.000 | 88.170 | 67.156 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |

#### MMKE-entity

已登记完整评测（2026-09-28同步）：`blip2-opt-2.7b` main 21 层；`instructblip-vicuna-7b` main 23 层；`minigpt-4-vicuna-7b` main 18 层；`llava-v1.5-7b` main 10 层；`qwen2.5-vl-3b` main 21 层；`paligemma-3b` main 16 层、stable 14 层；`smolvlm-1.7b` main 16 层。这里的“已评测”包括明确列出的恢复/诊断结果，不等同于全部训练收敛或全部完整50轮。

| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| blip2-opt-2.7b | L0 | 24 | 5.307720 | 6.124232 | 954 | 57.710 | 57.630 | 57.620 | 100.000 | 56.320 | 65.856 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L1 | 11 | 5.893988 | 5.990400 | 954 | 57.940 | 57.910 | 57.960 | 100.000 | 88.710 | 72.504 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L2 | 3 | 6.995899 | 6.229083 | 954 | 57.810 | 57.830 | 57.850 | 100.000 | 83.120 | 71.322 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L3 | 50 | 2.827587 | 3.004137 | 954 | 53.510 | 53.530 | 53.600 | 100.000 | 94.420 | 71.012 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L4 | 3 | 5.593518 | 6.027703 | 954 | 57.630 | 57.630 | 57.630 | 100.000 | 88.320 | 72.242 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L13 | 50 | 0.539618 | 0.736236 | 954 | 50.510 | 50.410 | 50.560 | 100.000 | 98.090 | 69.914 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L14 | 49 | 0.580979 | 0.732211 | 954 | 50.780 | 50.810 | 50.700 | 100.000 | 98.030 | 70.064 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L15 | 47 | 0.589422 | 0.932563 | 954 | 51.170 | 51.220 | 51.140 | 100.000 | 95.410 | 69.788 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L16 | 50 | 0.516484 | 0.527484 | 954 | 51.010 | 50.980 | 50.990 | 100.000 | 94.250 | 69.446 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L17 | 48 | 0.710702 | 0.651066 | 954 | 51.250 | 51.310 | 51.270 | 100.000 | 97.480 | 70.262 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L18 | 50 | 0.401966 | 0.597055 | 954 | 50.970 | 51.010 | 50.960 | 100.000 | 97.640 | 70.116 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L19 | 49 | 0.557689 | 0.554307 | 954 | 51.600 | 51.480 | 51.600 | 100.000 | 97.250 | 70.386 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L20 | 49 | 0.607764 | 0.626840 | 954 | 51.610 | 51.530 | 51.660 | 100.000 | 98.370 | 70.634 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L21 | 50 | 0.611507 | 0.947310 | 954 | 51.030 | 51.020 | 50.930 | 100.000 | 95.540 | 69.704 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L22 | 47 | 0.476664 | 0.634711 | 954 | 51.910 | 51.960 | 51.870 | 100.000 | 97.010 | 70.550 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L23 | 49 | 0.889130 | 1.210585 | 954 | 51.970 | 52.040 | 51.990 | 100.000 | 97.120 | 70.624 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L24 | 47 | 1.978343 | 1.652320 | 954 | 52.180 | 52.330 | 52.030 | 100.000 | 97.450 | 70.798 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L25 | 50 | 1.257574 | 1.250349 | 954 | 52.230 | 52.300 | 52.300 | 100.000 | 96.990 | 70.764 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L26 | 46 | 1.123006 | 1.444681 | 954 | 51.810 | 51.770 | 51.780 | 100.000 | 94.200 | 69.912 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L29 | 48 | 3.541405 | 3.073246 | 954 | 52.750 | 52.770 | 52.670 | 100.000 | 96.400 | 70.918 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| blip2-opt-2.7b | L30 | 50 | 4.810149 | 5.183463 | 954 | 52.610 | 52.520 | 52.640 | 100.000 | 97.950 | 71.144 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L0 | 45 | 0.791271 | 0.933128 | 954 | 48.700 | 48.770 | 48.740 | 100.000 | 95.380 | 68.320 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L1 | 43 | 0.994486 | 1.514755 | 954 | 48.720 | 48.850 | 48.710 | 100.000 | 99.610 | 69.180 | TRAIN_DONE_RESUMED_EPOCH45_CPU_SYNC_ACTIVATION_CKPT_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L2 | 49 | 10.099280 | 9.843736 | 954 | 16.710 | 16.240 | 16.610 | 100.000 | 99.380 | 49.788 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L3 | 47 | 8.834968 | 9.652104 | 954 | 17.120 | 16.720 | 17.080 | 100.000 | 99.190 | 50.020 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L4 | 50 | 13.571908 | 11.388381 | 954 | 15.150 | 14.540 | 15.050 | 100.000 | 99.720 | 48.890 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L5 | 49 | 12.275386 | 11.474885 | 954 | 13.910 | 13.440 | 13.840 | 100.000 | 99.820 | 48.200 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L14 | 48 | 10.428762 | 10.631304 | 954 | 14.620 | 14.470 | 14.570 | 100.000 | 99.530 | 48.638 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L15 | 49 | 11.955615 | 11.116361 | 954 | 14.990 | 14.600 | 14.880 | 100.000 | 99.750 | 48.844 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L16 | 50 | 8.842422 | 10.171081 | 954 | 14.850 | 14.330 | 14.810 | 100.000 | 99.610 | 48.720 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L17 | 50 | 11.998194 | 11.095907 | 954 | 15.270 | 14.500 | 15.240 | 100.000 | 99.630 | 48.928 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L18 | 48 | 11.101890 | 10.146582 | 954 | 14.760 | 14.270 | 14.750 | 100.000 | 99.340 | 48.624 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L19 | 48 | 13.396421 | 11.298227 | 954 | 14.600 | 14.370 | 14.490 | 100.000 | 99.530 | 48.598 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L20 | 50 | 7.502770 | 10.103081 | 954 | 14.630 | 14.110 | 14.520 | 100.000 | 99.870 | 48.626 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L22 | 49 | 12.596491 | 11.504756 | 954 | 14.080 | 13.220 | 14.080 | 100.000 | 99.250 | 48.130 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L23 | 46 | 11.005220 | 10.972629 | 954 | 14.240 | 13.630 | 14.150 | 100.000 | 99.640 | 48.330 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L24 | 50 | 10.610746 | 10.732185 | 954 | 12.350 | 11.970 | 12.240 | 100.000 | 99.780 | 47.270 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L25 | 50 | 12.247351 | 10.972824 | 954 | 13.100 | 12.440 | 13.080 | 100.000 | 99.270 | 47.580 | TRAIN_DONE_LOCAL_TMP_JOB3044841；MAIN_HISTORICAL_ACCEPTANCE |
| instructblip-vicuna-7b | L26 | 46 | 10.188010 | 11.535521 | 954 | 12.930 | 12.350 | 12.890 | 100.000 | 99.420 | 47.518 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L27 | 49 | 11.816212 | 11.171924 | 954 | 12.240 | 11.650 | 12.200 | 100.000 | 98.630 | 46.944 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L28 | 47 | 9.575759 | 11.254244 | 954 | 11.900 | 11.490 | 11.740 | 100.000 | 99.240 | 46.874 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L29 | 48 | 12.351160 | 11.742287 | 954 | 11.660 | 10.670 | 11.610 | 100.000 | 99.580 | 46.704 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L30 | 45 | 13.693354 | 14.488698 | 954 | 11.250 | 10.290 | 11.080 | 100.000 | 99.800 | 46.484 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| instructblip-vicuna-7b | L31 | 37 | 33.016987 | 38.583624 | 954 | 0.200 | 0.200 | 0.200 | 100.000 | 100.000 | 40.120 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L0 | 50 | 0.296119 | 0.316450 | 954 | 59.300 | 59.230 | 59.190 | 100.000 | 98.960 | 75.336 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L1 | 44 | 0.401454 | 0.342019 | 954 | 59.310 | 59.250 | 59.260 | 100.000 | 97.990 | 75.162 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L2 | 48 | 0.274402 | 0.280683 | 954 | 59.890 | 59.840 | 59.780 | 100.000 | 98.240 | 75.550 | TRAIN_DONE_LOCAL_TMP_JOB3044841_BACKED_UP；MAIN_HISTORICAL_ACCEPTANCE |
| minigpt-4-vicuna-7b | L3 | 47 | 0.311317 | 0.324533 | 954 | 59.670 | 59.710 | 59.640 | 100.000 | 98.040 | 75.412 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L4 | 44 | 0.315207 | 0.294066 | 954 | 60.510 | 60.480 | 60.570 | 100.000 | 98.130 | 75.938 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L6 | 47 | 0.292086 | 0.298080 | 954 | 59.290 | 59.210 | 59.300 | 100.000 | 98.350 | 75.230 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L7 | 50 | 0.301146 | 0.294014 | 954 | 59.590 | 59.570 | 59.600 | 100.000 | 97.950 | 75.342 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L14 | 45 | 0.318980 | 0.312375 | 954 | 60.860 | 60.830 | 60.840 | 100.000 | 98.650 | 76.236 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L15 | 46 | 0.303345 | 0.305240 | 954 | 60.020 | 60.060 | 60.100 | 100.000 | 98.360 | 75.708 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L16 | 44 | 0.338442 | 0.331353 | 954 | 60.270 | 60.330 | 60.240 | 100.000 | 98.420 | 75.852 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L22 | 47 | 0.416511 | 0.552444 | 954 | 58.820 | 58.820 | 58.760 | 100.000 | 98.500 | 74.980 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L23 | 50 | 0.380379 | 0.484842 | 954 | 59.080 | 59.100 | 58.970 | 100.000 | 98.000 | 75.030 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L24 | 50 | 0.425550 | 0.585518 | 954 | 59.200 | 59.280 | 59.130 | 100.000 | 97.570 | 75.036 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L25 | 49 | 0.918550 | 1.143279 | 954 | 59.210 | 59.320 | 59.250 | 100.000 | 98.130 | 75.182 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L26 | 46 | 0.877820 | 1.221248 | 954 | 59.710 | 59.890 | 59.600 | 100.000 | 98.400 | 75.520 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L27 | 44 | 0.747977 | 1.406714 | 954 | 60.480 | 60.610 | 60.440 | 100.000 | 97.590 | 75.824 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L28 | 48 | 1.072329 | 1.784545 | 954 | 60.660 | 60.690 | 60.670 | 100.000 | 98.200 | 76.044 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| minigpt-4-vicuna-7b | L31 | 41 | 5.441149 | 5.627008 | 954 | 60.690 | 59.930 | 60.710 | 100.000 | 100.000 | 76.266 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L9 | 48 | 0.293750 | 0.323795 | 954 | 60.960 | 60.990 | 60.950 | 100.000 | 95.230 | 75.626 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L14 | 49 | 0.159782 | 0.290381 | 954 | 61.310 | 61.450 | 61.290 | 100.000 | 96.120 | 76.034 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L15 | 45 | 0.423595 | 0.272476 | 954 | 61.070 | 61.180 | 61.010 | 100.000 | 95.430 | 75.738 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L16 | 41 | 0.172495 | 0.248927 | 954 | 61.130 | 61.250 | 61.100 | 100.000 | 96.570 | 76.010 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L22 | 45 | 0.274654 | 0.354578 | 954 | 60.320 | 60.400 | 60.340 | 100.000 | 97.030 | 75.618 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L23 | 49 | 0.284640 | 0.374458 | 954 | 60.390 | 60.410 | 60.340 | 100.000 | 96.560 | 75.540 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L24 | 41 | 0.316075 | 0.401128 | 954 | 60.050 | 60.140 | 60.040 | 100.000 | 96.740 | 75.394 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L26 | 46 | 0.452505 | 0.778010 | 954 | 59.950 | 60.070 | 59.970 | 100.000 | 95.730 | 75.144 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L27 | 50 | 0.859437 | 1.028096 | 954 | 60.030 | 60.080 | 60.000 | 100.000 | 95.630 | 75.148 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| llava-v1.5-7b | L28 | 48 | 1.354002 | 1.707617 | 954 | 59.470 | 59.540 | 59.500 | 100.000 | 95.200 | 74.742 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L0 | 50 | 1.760615 | 1.334659 | 954 | 54.780 | 54.490 | 54.880 | 100.000 | 96.930 | 72.220 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L1 | 50 | 1.050795 | 1.466707 | 954 | 54.690 | 54.590 | 54.850 | 100.000 | 97.250 | 72.280 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L2 | 49 | 0.828287 | 1.272041 | 954 | 54.880 | 54.780 | 54.960 | 100.000 | 95.570 | 72.040 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L3 | 50 | 0.892876 | 1.445015 | 954 | 54.450 | 54.320 | 54.430 | 100.000 | 96.830 | 72.006 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L6 | 50 | 1.694816 | 1.488007 | 954 | 55.640 | 55.600 | 55.610 | 100.000 | 96.510 | 72.672 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L10 | 50 | 2.474420 | 1.383637 | 954 | 54.050 | 53.930 | 54.000 | 100.000 | 96.520 | 71.700 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| qwen2.5-vl-3b | L13 | 49 | 1.519723 | 1.238898 | 954 | 53.290 | 53.170 | 53.310 | 100.000 | 97.430 | 71.440 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L14 | 49 | 0.686763 | 0.980262 | 954 | 53.460 | 53.410 | 53.440 | 100.000 | 97.100 | 71.480 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L15 | 50 | 1.871835 | 1.463023 | 954 | 52.940 | 52.850 | 52.950 | 100.000 | 96.870 | 71.120 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L16 | 47 | 1.531398 | 1.362743 | 954 | 53.680 | 53.560 | 53.730 | 100.000 | 96.980 | 71.590 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L17 | 46 | 0.521832 | 1.285736 | 954 | 53.590 | 53.470 | 53.610 | 100.000 | 96.730 | 71.480 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L18 | 49 | 0.705021 | 0.883009 | 954 | 53.650 | 53.560 | 53.610 | 100.000 | 95.170 | 71.200 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L20 | 49 | 0.910451 | 0.666375 | 954 | 53.240 | 53.160 | 53.350 | 100.000 | 96.300 | 71.210 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L21 | 50 | 0.532463 | 0.822907 | 954 | 52.650 | 52.370 | 52.650 | 100.000 | 95.620 | 70.660 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L22 | 49 | 1.156874 | 0.733265 | 954 | 53.590 | 53.360 | 53.530 | 100.000 | 96.000 | 71.300 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L25 | 44 | 0.686750 | 0.649926 | 954 | 54.000 | 53.870 | 54.030 | 100.000 | 96.580 | 71.700 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L26 | 46 | 0.741123 | 1.065371 | 954 | 52.780 | 52.530 | 52.820 | 100.000 | 95.180 | 70.660 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L27 | 50 | 1.188038 | 0.983534 | 954 | 53.910 | 53.670 | 54.050 | 100.000 | 95.070 | 71.340 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L28 | 50 | 0.872761 | 1.150297 | 954 | 54.690 | 54.540 | 54.830 | 100.000 | 95.010 | 71.810 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L29 | 48 | 1.635255 | 1.636492 | 954 | 55.810 | 55.610 | 55.910 | 100.000 | 95.950 | 72.660 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| qwen2.5-vl-3b | L30 | 50 | 1.664727 | 2.286476 | 954 | 55.970 | 55.740 | 55.920 | 100.000 | 94.420 | 72.410 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L0 | 8 | 2887.873291 | 2815.587779 | 954 | 0.000 | 0.000 | 0.000 | 100.000 | 0.000 | 20.000 | TRAIN_DONE_MAIN_NUMERIC_DEGENERATE_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L1 | 3 | 3.320363 | 2.964910 | 954 | 93.200 | 93.230 | 93.410 | 100.000 | 64.470 | 88.860 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L2 | 3 | 4.878585 | 6.100427 | 954 | 84.240 | 84.220 | 84.720 | 100.000 | 57.000 | 82.040 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L3 | 7 | 2.865983 | 2.230218 | 954 | 91.520 | 91.490 | 91.940 | 100.000 | 89.890 | 92.970 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L4 | 2 | 0.704963 | 0.882321 | 954 | 96.560 | 96.550 | 96.830 | 100.000 | 90.740 | 96.136 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| paligemma-3b | L5 | 4 | 1.668180 | 2.039312 | 954 | 88.460 | 88.470 | 88.730 | 100.000 | 88.390 | 90.810 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L6 | 2 | 1.206908 | 1.361229 | 954 | 95.850 | 95.890 | 95.960 | 100.000 | 97.220 | 96.980 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L7 | 10 | 2.394458 | 2.547924 | 954 | 84.710 | 84.650 | 84.720 | 100.000 | 96.530 | 90.120 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L8 | 3 | 0.592419 | 1.096720 | 954 | 95.940 | 95.810 | 96.000 | 100.000 | 93.730 | 96.300 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L9 | 2 | 4.133635 | 3.973418 | 954 | 78.510 | 78.360 | 78.550 | 100.000 | 91.620 | 85.410 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L10 | 1 | 18.536318 | 17.571920 | 954 | 15.040 | 15.090 | 15.000 | 100.000 | 46.260 | 38.280 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L11 | 1 | 12.053761 | 12.271097 | 954 | 21.410 | 21.140 | 21.520 | 100.000 | 59.040 | 44.620 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L12 | 2 | 2.737614 | 2.109276 | 954 | 88.780 | 88.730 | 88.850 | 100.000 | 87.000 | 90.670 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L13 | 2 | 10.599213 | 11.613107 | 954 | 17.600 | 17.580 | 17.520 | 100.000 | 90.570 | 48.650 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L16 | 49 | 15.929332 | 18.301300 | 954 | 12.430 | 12.210 | 12.410 | 100.000 | 98.170 | 47.040 | TRAIN_DONE_MAIN_RETRY_NUMERIC_GUARD_NONFINITE_SKIP34_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L17 | 22 | 31.180017 | 31.213888 | 954 | 0.560 | 0.550 | 0.550 | 100.000 | 100.000 | 40.330 | TRAIN_DONE_MAIN_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L1 | 37 | 0.333475 | 0.368120 | 954 | 99.340 | 99.340 | 99.570 | 100.000 | 96.300 | 98.910 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L2 | 38 | 0.323105 | 0.361797 | 954 | 99.340 | 99.340 | 99.530 | 100.000 | 95.780 | 98.800 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L3 | 47 | 0.345626 | 0.346825 | 954 | 98.870 | 98.880 | 99.070 | 100.000 | 97.390 | 98.840 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L5 | 35 | 0.340905 | 0.359304 | 954 | 98.980 | 98.970 | 99.320 | 100.000 | 96.520 | 98.760 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L6 | 47 | 0.330504 | 0.359201 | 954 | 99.090 | 99.080 | 99.390 | 100.000 | 97.220 | 98.960 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L7 | 49 | 0.329062 | 0.344094 | 954 | 99.320 | 99.310 | 99.440 | 100.000 | 95.350 | 98.680 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L8 | 49 | 0.342368 | 0.348620 | 954 | 99.320 | 99.310 | 99.390 | 100.000 | 97.940 | 99.190 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L9 | 50 | 0.339769 | 0.346904 | 954 | 99.350 | 99.340 | 99.350 | 100.000 | 97.350 | 99.080 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L10 | 49 | 0.347619 | 0.345262 | 954 | 99.030 | 99.000 | 99.000 | 100.000 | 97.250 | 98.860 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L11 | 47 | 0.577410 | 0.686626 | 954 | 94.890 | 94.830 | 94.830 | 100.000 | 97.340 | 96.380 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L12 | 48 | 0.538605 | 0.830285 | 954 | 93.400 | 93.260 | 93.410 | 100.000 | 96.410 | 95.300 | TRAIN_DONE_STABLE_RETRY_BUFFER1_GPU0_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L13 | 49 | 1.960766 | 2.245620 | 954 | 81.470 | 81.040 | 81.510 | 100.000 | 97.540 | 88.310 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L16 | 42 | 18.220282 | 19.640825 | 954 | 12.380 | 12.420 | 12.370 | 100.000 | 96.650 | 46.760 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| paligemma-3b | L17 | 38 | 30.471798 | 30.907994 | 954 | 0.560 | 0.550 | 0.550 | 100.000 | 100.000 | 40.330 | TRAIN_DONE_STABLE_JOB3044208；STABLE_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L0 | 47 | 0.717729 | 0.663257 | 954 | 51.760 | 51.750 | 51.710 | 100.000 | 97.110 | 70.470 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L1 | 45 | 0.510274 | 0.635121 | 954 | 52.580 | 52.500 | 52.640 | 100.000 | 97.520 | 71.050 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L2 | 49 | 0.532231 | 0.734351 | 954 | 52.800 | 52.790 | 52.690 | 100.000 | 97.300 | 71.120 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L6 | 47 | 0.546545 | 0.688924 | 954 | 51.980 | 51.990 | 52.030 | 100.000 | 96.460 | 70.490 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L7 | 50 | 1.166944 | 0.670295 | 954 | 51.420 | 51.400 | 51.380 | 100.000 | 97.320 | 70.300 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L8 | 50 | 0.998911 | 0.787083 | 954 | 52.220 | 52.250 | 52.220 | 100.000 | 96.750 | 70.688 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| smolvlm-1.7b | L9 | 50 | 0.814315 | 0.769834 | 954 | 51.860 | 51.940 | 51.850 | 100.000 | 96.550 | 70.440 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L10 | 48 | 0.795752 | 0.811847 | 954 | 52.210 | 52.140 | 52.140 | 100.000 | 96.590 | 70.620 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L11 | 50 | 0.662297 | 0.798535 | 954 | 50.220 | 50.390 | 50.180 | 100.000 | 96.970 | 69.550 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L12 | 50 | 0.663954 | 0.936153 | 954 | 52.310 | 52.270 | 52.310 | 100.000 | 97.320 | 70.840 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L13 | 50 | 0.489384 | 0.820767 | 954 | 50.630 | 50.760 | 50.620 | 100.000 | 96.220 | 69.650 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L14 | 50 | 0.687138 | 0.851731 | 954 | 50.210 | 50.310 | 50.020 | 100.000 | 96.080 | 69.320 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L15 | 50 | 0.973436 | 0.839188 | 954 | 50.240 | 50.420 | 50.080 | 100.000 | 96.910 | 69.530 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L16 | 50 | 1.646834 | 1.453352 | 954 | 50.850 | 50.960 | 50.690 | 100.000 | 95.450 | 69.590 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L17 | 48 | 2.262018 | 2.741290 | 954 | 52.450 | 52.620 | 52.320 | 100.000 | 95.550 | 70.590 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |
| smolvlm-1.7b | L18 | 50 | 3.508034 | 3.420248 | 954 | 53.750 | 53.910 | 53.650 | 100.000 | 96.030 | 71.470 | TRAIN_DONE_LOCAL_TMP_JOB3044208；MAIN_HISTORICAL_ACCEPTANCE |

### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B

结果来源：`md/Location/blip2_pliot500_epoch50_fulltest_layer_sweep_outcome.md`；2026-07-28待补5层来自g09本地`/tmp/ph_teacher3/evqa_pilot500_blip2_missing5_job3044208_20260728`。

训练与评测设置：

- 训练数据：`vqa_train_proxy500.json`。
- 评测数据：full E-VQA eval/test，共 `2093` 个样本。
- 训练轮数：每层 `50 epoch`。
- Checkpoint 选择：每层 minimum EMA loss。
- 流程隔离：每层评测独立 Python 进程，重新加载 base model 与当前层 adapter/hook。
- 特别说明：`L0` 使用原始有效 run；`L5/L10/L15/L19/L25/L30` 使用修复 wrapper 后的 fixed rerun；`L16/L17/L18/L20/L21/L24/L26/L29` 为后续补跑/补评结果；`L1/L2/L3/L4/L14` 为job 3044208在2026-07-28至2026-07-29完成的候选并集待补结果，均具备完整训练、selected checkpoint和正式评测标记。

| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---|---|---|---|---|---|---|---|---|---|
| L0 | 43 | 0.375991 | 0.368115 | 44.150 | 40.430 | 40.290 | 100.000 | 65.950 | 58.164 |
| L1 | 45 | 0.521112 | 0.425138 | 46.630 | 42.520 | 44.030 | 100.000 | 59.350 | 58.506 |
| L2 | 49 | 0.347236 | 0.417455 | 32.990 | 28.690 | 30.450 | 100.000 | 58.510 | 50.128 |
| L3 | 48 | 0.326949 | 0.366410 | 51.060 | 48.130 | 49.590 | 100.000 | 63.520 | 62.460 |
| L4 | 48 | 0.376648 | 0.397449 | 43.820 | 40.430 | 40.510 | 100.000 | 61.560 | 57.264 |
| L5 | 49 | 0.300460 | 0.396571 | 62.100 | 59.420 | 59.480 | 100.000 | 63.450 | 68.890 |
| L10 | 48 | 0.253585 | 0.299741 | 64.790 | 61.720 | 62.380 | 100.000 | 76.550 | 73.088 |
| L14 | 46 | 0.206319 | 0.309126 | 69.080 | 66.400 | 67.190 | 100.000 | 73.290 | 75.192 |
| L15 | 42 | 0.238769 | 0.336919 | 66.350 | 62.890 | 63.900 | 100.000 | 72.050 | 73.038 |
| L16 | 48 | 0.342088 | 0.393885 | 65.670 | 61.310 | 63.960 | 100.000 | 78.040 | 73.796 |
| L17 | 49 | 0.377570 | 0.384648 | 66.890 | 63.790 | 65.360 | 100.000 | 81.940 | 75.596 |
| L18 | 50 | 0.346307 | 0.392374 | 61.310 | 58.540 | 59.580 | 100.000 | 81.570 | 72.200 |
| L18-2 | 50 | 0.338767 | 0.385482 | 63.290 | 59.640 | 62.240 | 100.000 | 81.510 | 73.336 |
| L19 | 41 | 0.277514 | 0.291689 | 68.800 | 65.800 | 65.010 | 100.000 | 74.650 | 74.852 |
| L20 | 49 | 0.330291 | 0.379787 | 62.380 | 58.490 | 60.650 | 100.000 | 82.900 | 72.884 |
| L21 | 44 | 0.369473 | 0.378125 | 59.310 | 55.130 | 59.290 | 100.000 | 82.940 | 71.334 |
| L24 | 43 | 0.348283 | 0.361316 | 46.550 | 42.210 | 48.300 | 100.000 | 80.820 | 63.576 |
| L25 | 45 | 0.205779 | 0.232244 | 60.270 | 56.490 | 57.020 | 100.000 | 80.140 | 70.784 |
| L26 | 49 | 0.359013 | 0.363611 | 37.610 | 34.550 | 38.480 | 100.000 | 77.070 | 57.542 |
| L29 | 48 | 0.387346 | 0.414155 | 27.570 | 25.430 | 27.640 | 100.000 | 71.540 | 50.436 |
| L30 | 48 | 0.246737 | 0.557950 | 32.600 | 30.530 | 30.220 | 100.000 | 74.860 | 53.642 |

当前已测层中 full E-VQA `Average` 最高层为 `L17`，Average `75.60`。

历史候选方法回填示例（保留当时的候选定义与统计，不表示当前方法版本）：

| Method | Top-3 | Best@3 Layer | Best@3 Average | Top-5 | Best@5 Layer | Best@5 Average | 备注 |
|---|---|---:|---:|---|---:|---:|---|
| VisEdit-Contrib-Pre-FirstToken (historical) | L20,L19,L18 | L19 | 74.85 | L20,L19,L18,L17,L16 | L17 | 75.60 | Top-5 命中当前已测最优层；严格 KeyToken 待重算 |
| Middle-Prior-Direct | L17,L18,L16 | L17 | 75.60 | L17,L18,L16,L19,L15 | L17 | 75.60 | Top-3 命中当前已测最优层 |

### 4.2 EVQA-pilot500 / InstructBLIP-Vicuna-7B

本节已与 4.0 及 SWeeplayers.md 同步，包含全部已登记 main 层，不再只列历史 L26/L27/L28。逐层服务器路径、checkpoint 和核验证据见本次台账；更新前的三层表和旧候选方法示例保存在上方原手册备份。

- 训练数据：`vqa_train_proxy500.json`；独立评测：`vqa_eval.json`，2093 条。
- 目标训练预算为50轮、按运行选点记录评测；有训练完成标记但历史仅部分留存的层为 L0,L14,L15,L16,L18,L19，不将它们写成此次重新验证了完整50轮。
- 当前已登记 main 层：L0,L1,L2,L3,L4,L11,L14,L15,L16,L18,L19,L25,L26,L27,L28。

| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 49 | 0.599338 | 0.568572 | 37.990 | 36.920 | 33.840 | 100.000 | 52.520 | 52.254 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| L1 | 43 | 0.711665 | 0.678210 | 42.000 | 40.440 | 37.890 | 100.000 | 52.020 | 54.470 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L2 | 37 | 3.260540 | 1.270162 | 30.810 | 29.740 | 27.730 | 100.000 | 61.480 | 49.952 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L3 | 47 | 0.504032 | 0.941844 | 32.540 | 31.380 | 30.530 | 100.000 | 57.920 | 50.474 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L4 | 37 | 0.620709 | 1.438048 | 28.720 | 27.310 | 27.500 | 100.000 | 55.880 | 47.882 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L11 | 46 | 1.284068 | 1.214271 | 28.720 | 28.180 | 27.180 | 100.000 | 62.100 | 49.236 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L14 | 40 | 0.440674 | 0.989394 | 29.790 | 27.440 | 28.180 | 100.000 | 64.140 | 49.910 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| L15 | 38 | 0.579282 | 1.232926 | 27.750 | 26.460 | 26.740 | 100.000 | 66.350 | 49.460 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| L16 | 37 | 0.312248 | 1.197859 | 27.570 | 26.550 | 26.170 | 100.000 | 69.220 | 49.902 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| L18 | 50 | 0.409738 | 1.225163 | 23.540 | 22.450 | 22.630 | 100.000 | 55.670 | 44.858 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| L19 | 41 | 2.461512 | 1.400177 | 27.690 | 26.050 | 26.680 | 100.000 | 70.670 | 50.218 | TRAIN_DONE_MAIN_EVAL_DONE_HISTORY_PARTIAL_VERIFIED_20260928 |
| L25 | 50 | 3.241802 | 0.924779 | 28.930 | 28.260 | 28.230 | 100.000 | 73.060 | 51.696 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L26 | 50 | 0.202061 | 0.881081 | 29.650 | 28.920 | 27.940 | 100.000 | 70.700 | 51.442 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L27 | 36 | 0.274748 | 0.888490 | 29.640 | 28.660 | 28.710 | 100.000 | 74.340 | 52.270 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |
| L28 | 49 | 1.700526 | 1.100682 | 29.860 | 28.720 | 28.780 | 100.000 | 79.000 | 53.272 | TRAIN_DONE_MAIN50_EVAL_DONE_VERIFIED_20260928 |

当前这些已登记层中最高 Average 为 **L1 / 54.470**；这不是未完成候选层的上界。

方法 Top-K 比较须使用第2节相应版本的真实候选，并对照本节逐层结果检查是否齐全；本次不重新计算未冻结的候选并集或沿用原历史方法示例作为最新结论。

## 5. 真实扫层实验使用方式

1. 对每个 `dataset × model`，先冻结方法及目标版本，再取 Top-3 并集。VisEdit-alt 与 VisEdit-model_pred 分别纳入；MMKE model_pred 尚缺候选，必须标记并集不完整。既有第 3 节并集不能直接改名为八版本并集。
2. 再取所有定位方法的 Top-5 并集做完整候选层真实扫层。
3. 每个候选层使用完全相同的编辑训练配置，并记录 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average`。
4. 方法比较时按各自 Top-K 集合回填真实编辑结果；VisEdit-alt 与 VisEdit-model_pred 分别报告 `Best@3 / Best@5 / Mean@K / Regret@K / Hit@K`，只在共同候选评测完整的组合上配对，附覆盖数，不把待计算当作零分。
5. 跨数据集和跨模型汇总时使用 macro-average，避免样本量或层数不同导致结果偏置。

## 6. 注意

- PaliGemma-3B 在 MMKE 上的贡献度绝对值很小，候选层仍按相同规则给出，但真实编辑比较时建议标记为 low-confidence contribution。
- Qwen2.5-VL 做后续 visual token 梯度或编辑实验时，需要固定输入分辨率，避免视觉 token 数随图片尺寸变化。
- EVQA-pilot500 的 BLIP2 结果来自单独 BLIP2 pilot500 目录，其余 6 个模型来自 crossmodel pilot500 目录。
- 后续生成重跑队列时，先以第4.0节当前逐层结果及 SWeeplayers.md 核对已有评测，再参考第3.5节有日期的失败/中断记录；不能直接把历史待补清单作为当前队列。完整训练、恢复评测和 stable 配方须分别判断，避免重复执行已完成层。












