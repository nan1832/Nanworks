# LGA Tukey 补正：21 组候选、真实编辑比较与待补层

版本：`lga-tukey-k1-20260926`。参数分数只读同步于 2026-09-26T11:05:15.551972+00:00；原始 88 份文件已逐一核对 SHA-256。

已完成全部 21 组候选重算：618 条参数层记录中排除 76 条，15 组 Top-3 与 Top-5 改变。保留历史 Raw 排名作为消融，不将旧结果改写成 Tukey 结果。

## 1. 补正内容与固定规则

原论文 v2 附录 A 已要求按 Tukey fences 排除整体梯度分数异常的层；v3 指定默认常数为 1。来源：[Golden Layers v3 附录 A](https://arxiv.org/html/2602.20207v3#A1)。此前项目手册将 Tukey 降为可选诊断，导致现有第一阶段缺少这个选择步骤。

每个数据集 × 模型独立计算全部有效 MLP/FFN 参数层的 Q1、Q3，IQR = Q3 − Q1；保留 Q1 − IQR ≤ score ≤ Q3 + IQR 的层，然后按带符号 raw dot 降序取候选。上下界上的层保留。不取绝对值，不做对数变换，不删掉所有负分层，不依据真实编辑效果调整 kappa。

21 组内部有效样本数在各层完全相同，因此历史均值分数与论文求和分数相差一个正的常数：Tukey 剔除集合与排序一致，已逐组验证。参数版所有 618 层原本均为 finite/ok；本次排除的 76 层属于统计异常层，不是视觉版的末层零梯度过滤。

论文没有说明四分位数插值细节。本次预先固定 NumPy `method="linear"`，并报告 midpoint/lower/higher/nearest 的敏感性，不根据编辑结果选择实现。其中 midpoint 会改变 BLIP2 的 E-VQA 与 MMKE-visual 两组候选；因此这是按公开论文规则补齐 Tukey 的可复算实现，不宣称与未核得的作者源代码逐位一致。

本次只补正参数版 LGA；视觉隐藏状态 M_dot、当前主公式及训练配置没有改变。参数版沿用原有样本过滤，仍不同于视觉版；二者的比较是现有完整流程的比较，不能据此单独归因于梯度空间。

## 2. 全部候选层

| 数据集 | 模型 | Raw Top-3 | Tukey Top-3 | Tukey Top-5 | 剔除层 |
|---|---|---|---|---|---|
| evqa-pilot500 | blip2-opt-2.7b | L0,L1,L3 | L4,L16,L18 | L4,L16,L18,L17,L15 | L0,L1,L3 |
| evqa-pilot500 | instructblip-vicuna-7b | L2,L0,L1 | L17,L18,L20 | L17,L18,L20,L19,L21 | L2,L0,L1,L4 |
| evqa-pilot500 | llava-v1.5-7b | L24,L25,L26 | L24,L25,L26 | L24,L25,L26,L23,L27 | L1 |
| evqa-pilot500 | minigpt-4-vicuna-7b | L29,L25,L22 | L29,L25,L22 | L29,L25,L22,L26,L21 | L31,L2 |
| evqa-pilot500 | paligemma-3b | L17,L7,L0 | L7,L0,L8 | L7,L0,L8,L13,L16 | L17 |
| evqa-pilot500 | qwen2.5-vl-3b | L2,L30,L1 | L3,L10,L6 | L3,L10,L6,L12,L9 | L2,L30,L1 |
| evqa-pilot500 | smolvlm-1.7b | L22,L21,L20 | L22,L21,L20 | L22,L21,L20,L19,L18 | L7,L1 |
| mmke-entity | blip2-opt-2.7b | L16,L13,L18 | L16,L13,L18 | L16,L13,L18,L17,L15 | L6,L5,L4,L1,L3,L2,L0 |
| mmke-entity | instructblip-vicuna-7b | L2,L28,L0 | L1,L17,L20 | L1,L17,L20,L18,L16 | L2,L28,L0,L4,L30,L31 |
| mmke-entity | llava-v1.5-7b | L1,L9,L7 | L9,L7,L8 | L9,L7,L8,L6,L5 | L1 |
| mmke-entity | minigpt-4-vicuna-7b | L4,L3,L6 | L7,L8,L14 | L7,L8,L14,L17,L13 | L4,L3,L6,L0,L1,L5,L29,L28,L30,L31,L2 |
| mmke-entity | paligemma-3b | L17,L16,L7 | L7,L8,L13 | L7,L8,L13,L10,L0 | L17,L16 |
| mmke-entity | qwen2.5-vl-3b | L2,L30,L1 | L6,L3,L10 | L6,L3,L10,L12,L11 | L2,L30,L1 |
| mmke-entity | smolvlm-1.7b | L1,L7,L0 | L0,L6,L8 | L0,L6,L8,L9,L5 | L1,L7 |
| mmke-visual | blip2-opt-2.7b | L0,L1,L3 | L18,L16,L17 | L18,L16,L17,L19,L15 | L0,L1,L3,L4,L2,L5,L6,L7 |
| mmke-visual | instructblip-vicuna-7b | L2,L0,L4 | L17,L20,L18 | L17,L20,L18,L16,L19 | L2,L0,L4,L28,L1,L31,L30 |
| mmke-visual | llava-v1.5-7b | L24,L22,L27 | L24,L22,L27 | L24,L22,L27,L25,L23 | L31,L1 |
| mmke-visual | minigpt-4-vicuna-7b | L0,L1,L3 | L0,L1,L3 | L0,L1,L3,L4,L25 | L30,L31,L2 |
| mmke-visual | paligemma-3b | L17,L0,L7 | L7,L8,L10 | L7,L8,L10,L16,L13 | L17,L0 |
| mmke-visual | qwen2.5-vl-3b | L2,L30,L1 | L3,L6,L10 | L3,L6,L10,L9,L8 | L2,L30,L1 |
| mmke-visual | smolvlm-1.7b | L1,L7,L6 | L6,L8,L5 | L6,L8,L5,L4,L9 | L1,L7,L23 |

## 3. 使用相同组合比较 Raw、Tukey 与当前主公式

主表采用已有 main 配置的真实评测，包括已直接评测的不收敛运行，并保留训练状态。stable 不混入。只有一个方法的全部 Top-K 都已评测，才计算其 Best@K、Mean@K。Regret/Hit 的参考是该组合已测 main 层中的最好结果，并非全层 oracle。以下三行严格使用相同的 10 组；该批包含低定位覆盖组，下面另报覆盖与训练状态敏感性。

| 方法 | 同一批组合数 | Best@3 | Mean@3 | 已测层 Regret@3 | 已测层 Hit@3 |
|---|---:|---:|---:|---:|---:|
| LGA-Param-Raw | 10 | 72.349 | 64.858 | 6.511 | 0.0% |
| LGA-Param-Tukey | 10 | 74.781 | 71.698 | 4.080 | 10.0% |
| Ours-Direct | 10 | 75.533 | 69.852 | 3.328 | 30.0% |

在这批相同组合上，Tukey 相比 Raw 的 Best@3 提高约 2.432，Mean@3 提高约 6.840。当前主公式相比 Tukey 的 Best@3 高约 0.752，但 Mean@3 低约 1.846，Best@3 为 6 胜、0 平、4 负。不能继续将“优于未过滤 Raw”写成“全面优于原论文 LGA”。

所有当前可配对的 Raw/Tukey 共有 11 组，Tukey 为 4 胜、6 平、1 负，Best@3 增量约 2.211、Mean@3 增量约 6.218。它与上述三方共同 10 组的平均值不能直接混用。

### 3.1 训练状态与定位覆盖敏感性

`clean` 排除提前恢复、数值异常、停滞、不收敛/诊断记录；它与主表不是同一批组合。不同口径会改变 Mean@3 的符号，不能只选择有利口径。定位覆盖≥80%时同时要求被比较两方法达标。

| 口径 | 覆盖限制 | 主公式/Tukey 共同组数 | ΔBest@3（主公式−Tukey） | ΔMean@3 | 主公式胜/平/负 |
|---|---|---:|---:|---:|---|
| observed_main | all_coverage | 10 | +0.752 | -1.846 | 6/0/4 |
| observed_main | coverage_ge_80pct | 9 | +0.570 | -2.059 | 5/0/4 |
| clean | all_coverage | 9 | +0.838 | +1.343 | 6/0/3 |
| clean | coverage_ge_80pct | 8 | +0.645 | +1.502 | 5/0/3 |

### 3.2 按数据集分开（observed_main、双方覆盖≥80%）

| 数据集 | 共同组数 | 主公式 ΔBest@3 | 主公式 ΔMean@3 | 胜/平/负 |
|---|---:|---:|---:|---|
| evqa-pilot500 | 3 | +1.304 | -0.598 | 2/0/1 |
| mmke-visual | 5 | +0.277 | -6.337 | 3/0/2 |
| mmke-entity | 1 | -0.164 | +14.949 | 0/0/1 |

MMKE-entity 在该覆盖限制下只有 1 组可比，不能据此宣布该任务适合某个公式。七方法在共同组上的完整表见 `same_cohort_method_summary.csv`；该表仍保留其他方法的历史版本边界，例如 EVQA 的 VisEdit 仍为历史 FirstToken 结果。

## 4. 真实案例与可核对的变化

| 数据集 × 模型 | Raw 候选 | Tukey 候选 | Raw Best@3 | Tukey Best@3 | 说明 |
|---|---|---|---:|---:|---|
| E-VQA × BLIP2 | L0,L1,L3 | L4,L16,L18 | 62.460 | 73.800 | 补齐过滤后提高 11.340；候选由浅层转向更深层 |
| MMKE-visual × BLIP2 | L0,L1,L3 | L18,L16,L17 | 69.690 | 71.290 | Best@3 提高 1.600 |
| MMKE-visual × SmolVLM | L1,L7,L6 | L6,L8,L5 | 70.770 | 70.322 | 下降 0.448，说明 Tukey 并非每组都会改善 |

MMKE-visual × PaliGemma 的 Raw 集合含 main L0 的不收敛实测值；换为 Tukey 后 Mean@3 大幅提高，不能将这个增幅当作正常收敛条件下的普遍提升。该组合的 clean 分析单列，不用 stable 成绩替换失败 main。

## 5. 尚缺的真实编辑结果

补记并验证 LLaVA × MMKE-entity L9 后，Tukey Top-3 的 63 个组合—层位置中已有 46 个 main 评测，还缺 17 个；Top-5 的 105 个位置中已有 70 个，还缺 35 个。这里按“数据集 × 模型 × 层”计数，不是缺 17/35 个组合。

Top-3 缺项中，15 个是本次相对旧七方法 Top-3 并集新增的层；另外 2 个是历史缺项：E-VQA × PaliGemma L0、MMKE-entity × LLaVA L7。

| 数据集 | 模型 | Top-3 尚缺 main 评测 | 其中新增于旧七方法 Top-3 并集 | 扩至 Top-5 额外缺项 |
|---|---|---|---|---|
| evqa-pilot500 | instructblip-vicuna-7b | L17,L20 | L17,L20 | L21 |
| evqa-pilot500 | llava-v1.5-7b | — | — | L23 |
| evqa-pilot500 | minigpt-4-vicuna-7b | — | — | L21 |
| evqa-pilot500 | paligemma-3b | L0 | — | L13,L16 |
| evqa-pilot500 | qwen2.5-vl-3b | L10,L6 | L10,L6 | L9 |
| evqa-pilot500 | smolvlm-1.7b | — | — | L18 |
| mmke-entity | instructblip-vicuna-7b | L20 | L20 | — |
| mmke-entity | llava-v1.5-7b | L7,L8 | L8 | L6,L5 |
| mmke-entity | minigpt-4-vicuna-7b | L7,L8 | L7,L8 | L17,L13 |
| mmke-entity | qwen2.5-vl-3b | L6,L3,L10 | L6,L3,L10 | L12,L11 |
| mmke-entity | smolvlm-1.7b | L8 | L8 | L5 |
| mmke-visual | instructblip-vicuna-7b | L20 | L20 | — |
| mmke-visual | llava-v1.5-7b | — | — | L25,L23 |
| mmke-visual | minigpt-4-vicuna-7b | — | — | L4 |
| mmke-visual | paligemma-3b | — | — | L16 |
| mmke-visual | qwen2.5-vl-3b | L3,L10 | L3,L10 | — |

LLaVA × MMKE-entity L9 已找到共享盘正式结果：训练完成 50 epoch，选中 epoch 48，954 条逐样本评测，Average=75.626；已下载 7 个证据文件、核验哈希并重新聚合五项指标，无须重复训练。

服务器只读核对范围与时间见 `pending_server_audit.json`：扫描项目共享 server_results，未扫描所有计算节点的 /tmp。缺项表示当前没有取得可验收的 main 评测；不一概认定从未启动训练。E-VQA × PaliGemma L0 找到历史失败目录；E-VQA × InstructBLIP L17 找到归因目录，但没有对应真实编辑完成标记。

执行顺序：先补 Top-3 新增的 15 个位置；历史 LLaVA L7 随已有恢复队列核对；PaliGemma L0 优先检查已有 checkpoint 能否按原 main 直接评测，再决定是否需重训；最后处理 Top-5 额外的 18 个缺项。保持各组合原训练配置、训练预算和选点规则，不为 Tukey 调训练参数。当前 g08/g09 已有训练任务，本次没有改动正在运行的队列，也没有启动新增 GPU 训练。

## 6. 文件与复现

- `raw/`、`source_manifest.json`：21 组原始参数分数、summary、候选和 sanity；历史 Raw 保留。
- `protocol.json`、`recompute.py`：固定 Tukey 与比较规则、完整复算脚本。
- `tukey_audit_21groups.csv`、`parameter_layer_scores_raw_and_tukey.csv`：阈值、76 个异常层、原/新排名。
- `candidate_topk_21x8.csv`、`corrected_seven_method_union.csv`：修正后的候选与并集，Raw 单列消融。
- `method_metrics.csv`、`paired_comparisons.csv`、`paired_summary.csv`、`same_cohort_method_summary.csv`：完整指标、逐组合配对与相同组合汇总。
- `tukey_candidate_execution_status.csv`、`pending_server_audit.json`：每个候选的 main 评测与共享盘核对状态。
- `quartile_sensitivity.csv`：固定 kappa=1 下五种分位数实现的敏感性；主结果始终用 linear。
- `supplemental_evidence/`、`supplemental_evaluation_verification.json`：新增找到的 L9 真实结果证据。
- `verification.json`：独立分位数、排序、指标和源文件哈希复核。

复算顺序：在本目录运行 `recompute.py`，再运行 `verify.py`。输入 snapshot 固定，若需要纳入未来新结果，应建立新版本，不静默替换现有快照。
