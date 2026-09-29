# PaliGemma 主配置异常与 stable 可比性核验

核验日期：2026-09-25。范围：本地已归档的配置、训练脚本、损失历史和逐层结果台账；没有重新连接服务器检查实时任务，也没有启动训练。本文修正此前“MMKE-visual × PaliGemma 必须补主配置 L3/L5 才能比较”的建议，不改写既有实验结果。

## 1. 结论

**stable 可以用于比较层定位方法。** 公平性的关键是同一模型—数据集组中，各方法面对同一套固定训练协议和逐层编辑结果，而不是所有模型必须使用完全相同的学习率。采用模型适配的训练协议，需要公开说明，并对所有被比较方法一致应用。

就当前主公式与纯新梯度范数的 Top-3 配对而言，更合理的最小补全是：保留 MMKE-visual × PaliGemma 已有 stable L3/L5，补 **stable L4**。这是一项补跑建议，尚未执行；目前不能把这三个层记作完整的同配置 stable 结果。

## 2. 主配置为什么出现问题

| 证据 | 可以支持的判断 | 不能据此推断的结论 |
|---|---|---|
| 2026-07-13 异常报告记录 MMKE-visual L7 的 `mlp_begin.weight` 2,097,152/2,097,152 个梯度非有限，`influence_mapper.ln_img_reps.weight` 2,048/2,048 个梯度非有限，随后长期不推进 | adapter / influence mapper 训练链路出现数值异常；当时没有正常完成产物 | 没有逐算子追踪，不能断言第一个溢出点；也不能把所有 stall 都归因于同一个原因 |
| 同一历史报告记载 L7 当时 GPU 约剩 46 GB，日志没有 CUDA OOM | 该次异常不支持“显存耗尽”解释 | 不代表所有其他运行都没有资源问题 |
| MMKE-visual 主配置 L14 的所选 checkpoint EMA 为 −351.953961，Average 39.03 | 存在异常损失/选点记录，应隔离审查 | 负 EMA 的具体来源尚未由本轮原始逐步日志定位；不能仅凭此把原因锁定为学习率 |
| 原始 MMKE-visual 主配置 L0 的 `source_loss_history.csv` 有 9 条 epoch 记录，EMA 范围 3508.007406–3550.663258；恢复评测的 Reliability 仅 0.10、Average 38.520 | 本次 L0 在记录范围内没有有效收敛，评测可执行不等于编辑成功 | 不是完整 50 epoch 的正常收敛成绩 |
| L0 的特殊 stable 版本使用 lr=1e-6，25 条已保存 epoch 记录的 EMA 范围 3454.815660–3530.232688；台账记录 epoch 26 又出现 checkpoint 写入失败 | 降学习率和保护措施没有解决该层全部问题；写盘失败与此前持续高损失是两个问题 | 不能把这个 lr=1e-6 的 L0 特例当成普通 lr=1e-5 stable |
| MMKE-visual 主配置 L4 已有正常验收记录：所选 epoch 39、EMA 0.330234、293 条评测、Average 99.026 | 主配置并非所有层都跑不通，问题具有层依赖性 | 不能写成“PaliGemma 主配置全失败” |

当前证据最稳妥的解释是：**原训练配方在 PaliGemma 的部分层上数值不稳定或不能有效优化。** 学习率、损失精度与异常梯度处理是有代码依据的候选原因；本次没有只改变一个因素的受控实验，因此不能声称已证明“唯一原因就是 lr=1e-4”。

历史报告中的服务器补丁曾将非有限梯度替换为零后继续执行 optimizer step；这不等于跳过异常更新，也不能保证优化器内部状态健康。本地当前 `vead.py` 的原始实现是直接 backward/step，与历史服务器补丁不是完全相同的代码快照。正式复现实验应保存具体 runner、依赖源码和配置哈希。

另外，完整训练后选中较早 epoch 本身不是失败证据；应结合完整训练标记、loss 轨迹和非有限告警判断。旧问题报告把部分 early checkpoint 列为告警，不能直接据此排除所有早期选点。

## 3. stable 实际改变了什么

| 项目 | 主配置/原始实现 | 普通 stable 实现 |
|---|---|---|
| 学习率 | 1e-4 | 1e-5 |
| 标签损失与 KL 计算 | 原始函数没有显式将 logits 转成 FP32 | 显式 `.float()`，对 NaN/Inf 作替换，并保护 mask 分母 |
| influence mapper 损失 | 原始计算路径 | 预测值的 FP32 转换及非有限值处理 |
| 非有限 loss/梯度 | 历史版本存在置零后继续 step 的处理 | 跳过异常 step 并清空梯度 |
| 梯度裁剪 | 原始实现未配置 | 普通 stable 默认范数阈值 1.0 |
| checkpoint 选择 | 原主流程按 EMA 选点，曾选中负 EMA | 过滤缺失、非有限、负 EMA，以及超过阈值的记录；默认 EMA 上限 100，再选合法最小 EMA |
| adapter 尺寸、损失权重、IT 开关 | mid_dim=1024；权重 1/1/1/0.1；IT 开启 | 所核对普通 stable YAML 中相同 |

因此 stable 不是“只把结果换个名字”，也不只是学习率变化，而是另一套明确的训练/数值处理协议。`stable-l0`、后续 rollback 和 buffer1 修复也要单列具体变体，不能仅根据名称含 stable 就视为完全一致。

## 4. 当前这组三层是否足够

来源为当前逐层台账及本次公式复算 CSV；分数按台账保留精度。

| 层 | 主配置 | 普通 stable | 当前用途 |
|---|---|---|---|
| L3 | 本轮未找到可核验的主配置正式结果 | 已完成；所选 epoch 46，EMA 0.347433，293 条，Average 97.90 | 可进入 stable 配对结果池 |
| L4 | 已完成；所选 epoch 39，EMA 0.330234，293 条，Average 99.026 | 本轮检索到的台账和归档中未见正式结果 | 若采用普通 stable，需要补这一层 |
| L5 | 本轮未找到可核验的主配置正式结果 | 已完成；所选 epoch 45，EMA 0.347726，293 条，Average 98.58 | 可进入 stable 配对结果池 |

“L3/L5 没有主配置结果”不等于“已逐层证明 L3/L5 主配置失败”。本轮未找到这两个层各自的主配置失败原始日志，不将 L7/L14/L0 的故障套到它们身上。

两方法当前候选为：

- 主公式 `abs(mean cos) × mean new_norm`：L5、L4、L3。
- 纯新梯度范数：L4、L5、L3。

两者 Top-3 集合相同。因此，在同一固定结果池中，Best@3、Mean@3 必然相同；采用相同参照池时，Regret@3、Hit@3 也必然相同。Top-1 不同，需 stable L4 后才能与 stable L5 比较。补这一层的价值是统一协议、补齐覆盖并检验首选层，而不是增加一组“方向项胜出”的证据。

上述“仅需 L4”只适用于这两个公式的 Top-3。若比较全部定位方法，应检查它们候选并集；现有 stable L8 是 epoch 13 中断恢复评测，L0 是特殊配置且不收敛，仍需明确处理规则。失败层不能静默删除、记零或用其他配方最优成绩替换。Regret/Hit 的参照最优层应写成“固定已评测候选池内最优”，不能冒称全网络最优。

## 5. 如何合理纳入论文

1. **当前即可报告的内容：** 以独立 stable 表列出已有逐层结果及异常情况。原 main 口径和当前 16/15 组统计暂不变化，未完成的纯 stable 三层配对不记为完成。
2. **最小补全建议：** MMKE-visual × PaliGemma 补普通 stable L4，使用与 L3/L5 匹配的 runner、配置、训练/评测数据、随机种子规则、50 epoch 预算和 checkpoint 规则。保留完整运行记录，执行 293 条独立 full eval。所选 epoch 46/45 是最佳 checkpoint 位置，不是把新训练预算改为 46/45 epoch。
3. **正式比较：** 所有定位方法共享同一个 stable 逐层结果映射；不采用主公式用 stable、基线用 main，也不逐层取两种配方的较高分。
4. **主表或补充表：** 最稳妥的是先作为 stable 配对/敏感性分析；也可以公开修订实验协议，采用模型适配配方后重新汇总主表。应说明修订来自已观察到的数值问题、列明协议版本及覆盖范围，不能写成实验开始前已预注册。已经看过的成绩不因补跑或改名而成为独立确认集。
5. **解释界限：** 结果证明的是在给定编辑器训练协议下的候选层筛选表现。不能把 stable 的成绩提升直接归功于层定位公式，也不能由这组相同集合推导方向项优势。

建议论文表述：

> 针对 PaliGemma 部分编辑层在原训练配方下出现的非有限梯度和损失异常，本文另设稳定训练协议，通过降低学习率、提高损失计算精度、梯度裁剪和异常更新跳过改善训练稳定性。在该协议下，各定位方法共享相同的逐层编辑评测结果。原协议与稳定协议分别报告，不进行逐层择优混合。

## 6. 可追溯文件

- [历史数值异常报告](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/paligemma_training_instability_pilot500_mmke_visual.md>)：L7 梯度、显存快照、L14 异常、历史服务器处理方式。属于历史汇总证据，不代替本轮未取得的逐步原始日志。
- [逐层结果台账](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/6location_7model_3datas_top_3_5_layers_outcome.md:1558>)：MMKE-visual stable 完成范围和协议；L3/L4/L5 结果见 1664、1677、1678 行。
- [主配置](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/VisEdit-main/configs/vead/paligemma-3b.yaml>)、[普通 stable 配置](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/VisEdit-main/configs/vead/paligemma-3b-stable.yaml>)、[stable runner](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/VisEdit-main/scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py>)、[L5/L1/L0 修复启动脚本](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/VisEdit-main/scripts/run_paligemma_visual_stable_repair_5_1_0_job3044208.sh>)。
- [原始主配置 L0 损失记录](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/server_results/live_backfill/paligemma_l0_nonconvergent_eval_20260921/mmke-visual_main_l0_lr1e4/source_loss_history.csv>)、[特殊 stable L0 损失记录](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/server_results/live_backfill/paligemma_l0_nonconvergent_eval_20260921/mmke-visual_stable_l0_lr1e6/source_loss_history.csv>)。
- [主配置 L4 原始选点记录](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/server_results/live_backfill/job3117562/mmke-visual/paligemma-3b/layer_04/selected_checkpoint.tsv>)、[本轮候选排名](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/main_formula_validation_20260925/candidate_topk.csv>)。

本次没有修改原始台账、候选排名或旧配对分数，没有把后续建议当作已完成实验。
