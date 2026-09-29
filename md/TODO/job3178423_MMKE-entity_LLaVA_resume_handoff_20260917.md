# Job 3178423 / MMKE-entity × LLaVA 续跑现场

更新时间：2026-09-17 22:17 CST

## 当前状态

- Slurm Job：`3178423`
- 节点 / GPU：`g07 / GPU0`，NVIDIA A800 80GB
- 当前层：`MMKE-entity × LLaVA-v1.5-7B / L24`
- L24 于 `2026-09-17 22:12:43 CST` 启动训练；模型已完整加载，训练预处理持续前进。
- 启动后实测整卡显存：约 `33,270 MiB` 已用、`47,906 MiB` 空闲，GPU 利用率 `100%`。
- 未发现 CUDA OOM、Traceback、nonfinite 或磁盘写入错误。

## 完成与后续层

已完成正式训练、最低有限 EMA checkpoint 选择、独立 954 条评测并归档的层：

`L15、L16、L14、L28、L27、L26、L23、L22`

当前及后续正式 Top-3 并集顺序：

`L24 → L1 → L9 → L7 → L0 → L2 → L13 → L11 → L12 → L4`

其中 `L4` 来自 `CMA-ModelPred v2` 后的七方法 Top-3 并集。旧启动器漏列 L4，已于 2026-09-17 补入启动器的 `run_combo` 与 `combo_complete`，并部署后继控制器，保证当前队列结束后自动补跑而不打断 L24。

## 可比性配置

- 每层 `50 epoch`
- `batch_size=2`
- 基础 seed：`20260601`，沿用原逐层派生 seed 规则
- EMA alpha：`0.1`
- checkpoint：选择 minimum finite EMA loss
- 独立 MMKE-entity eval：954 条
- 低显存策略：同步数据加载、activation checkpointing、单个冻结 LLaVA 在未编辑 influence trace 与 Adapter 训练之间复用
- 未改变学习率、数据、优化目标、Adapter 配置或评测口径

## 显存启动修复

原启动器即使有约 `75.7 GiB` 空闲显存，也因检测到一个其他非-kernel GPU进程而永久等待。现仅对 `job3126082` 替代角色启用：

- 训练开始前要求空闲显存不少于 `61,440 MiB`
- 允许保留低占用的其他非-kernel进程
- 连续3次探测通过后启动
- 其他角色仍保持原独占策略

未停止、未抢占、未修改卡上其他人的进程。

## 存储与清理策略

- 服务器临时工作目录：`/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812`
- 共享盘正式归档：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082`
- 每层流程：训练 → minimum finite EMA选点 → 独立eval → 共享盘归档核验 → 删除非selected checkpoints与可重建cache。
- `/tmp/ph_teacher3` 是服务器节点本地临时盘，不是Windows本地电脑。仅当前层的活动数据留在该目录；完成层的selected checkpoint与正式结果以共享盘为准，临时实体替换为共享盘链接或清理。

## 日志与控制器

- 当前队列日志：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082/recovery_logs/srun_replacement_job3178423_20260917_221058.log`
- L24训练日志：`/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812/logs/mmke-entity_llava-v1.5-7b_L24_train_20260917_221059.log`
- L4后继控制器日志：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082/recovery_logs/followup_add_l4_controller_20260917.log`
- 启动器：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/launch_formal_top3_stage2_20260812.sh`
- 启动器 SHA-256：`71caef0de33bd7d2d7aa1b8ea9f27b03ef2b0489fbbedfbf391e5fd396d04194`

## 验收约束

任何层只有同时满足以下条件才计为完成：

1. 非空 `train.done`
2. 非空 `selected_checkpoint.tsv`
3. selected checkpoint 实体在共享盘存在并可读
4. 非空 `eval_full.done`
5. 非空 `results.json`，且为954条独立 MMKE-entity eval
6. `SYNC_VERIFIED` 与 checkpoint retention 核验通过

