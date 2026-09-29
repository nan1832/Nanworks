# Job 3178423 暂停与恢复现场

## 暂停结论

- 北京时间：2026-09-21 11:05:24--11:05:48 CST。
- 为给新的 P0 小任务释放显存，暂停 `Job 3178423 / g07 / GPU0` 上的 `MMKE-entity × LLaVA-v1.5-7B`。
- 未暂停 `Job 3178538 / g08`：其 EVQA × LLaVA L2 已接近 50 epoch 末段，应优先完成。
- 仅终止本实验的控制器进程组和训练进程组；Slurm/Jupyter Job 3178423 保持 `RUNNING`，未停止 PID 1998199 或其他未知进程。

## 暂停前状态

| 项目 | 值 |
|---|---|
| 数据集 / 模型 / 层 | MMKE-entity / LLaVA-v1.5-7B / L1 |
| 阶段 | 正式训练 |
| 最后观察进度 | Epoch 18，94/636（未完成的 Epoch 18 不作为恢复点） |
| 完整恢复点 | Epoch 17，i=5406 |
| EMA loss | 0.7862091779796281 |
| 训练完成标记 | 无 `train.done` |
| 正式评测标记 | 无 `eval_full.done` |
| 当前层分类 | 可恢复训练，不得记为已完成 |

## 可恢复 checkpoint

- 原节点文件：`/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812/mmke-entity/llava-v1.5-7b/layer_01/records/vead/llava-v1.5-7b/pilot500_blip2_visedit_L01-lr-1-t-1-v-1/checkpoints/epoch-17-i-5406-ema_loss-0.7862`
- 共享盘快照：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082/pause_snapshots/20260921_110450-before_p0/epoch-17-i-5406-ema_loss-0.7862`
- SHA-256：`18149e4dcc14c199d00eb768568d04b31637b1d4ccab574138b92e50fd6ddc37`
- 源文件与共享盘副本哈希一致。
- 同目录还保存了 `loss_history.csv`、训练日志、`queue.status.log`、`layer_status.csv`、`run_config.json`、启动脚本及 `SHA256SUMS.txt`。

## 不可改变的实验协议

- 50 epochs；batch size 2；seed 20260601；EMA alpha 0.1。
- synchronous data loading、activation checkpointing、单模型 GPU 复用。
- 仅保留最低有限 EMA loss checkpoint；完成后进行独立 MMKE-entity 正式评测。
- 不改变学习率、优化器、数据划分、Adapter结构、目标函数或评测集。

## 恢复顺序

1. 等新的 P0 小任务完全退出，核验 g07 没有该任务的 GPU 进程。
2. 核验共享盘快照哈希及节点 `/tmp` 恢复点；若节点副本丢失，从共享盘快照恢复。
3. 使用原包装器 `scripts/run_formal_top3_stage2_replacement_job_20260827.sh job3126082`，由原 launcher 自动传入 `--resume-checkpoint` 与 `--resume-layer 1`。
4. 应从 Epoch 18 开始续训，而不是从头训练；启动后核验日志出现 `loaded_epoch=17`、`next_epoch=18`。
5. L1完成50 epoch后选择全程最低有限EMA checkpoint，完成独立评测，再继续剩余队列。

剩余顺序：`L1续训及评测 → L9 → L7 → L0 → L2 → L13 → L11 → L12 → L4`。

恢复前需要重新取得用户授权，并重新检查显存、进程归属、Slurm剩余时限与共享GPU锁。

## 暂停后验证

- 实验PID 2167481以及控制器PID 3582781/3582797等均已退出。
- g07 GPU0：总显存81920 MiB，已用1221 MiB，空闲79955 MiB，利用率0%。
- 剩余GPU进程仅PID 1998199，占1210 MiB；该进程未被停止或修改。
- Job 3178423本身仍为Slurm `RUNNING`，原步骤3178423.28因本次授权暂停显示`CANCELLED 0:13`，这不是训练失败结论。

## 11:19 自动恢复链修正与 P0 执行结果

- 第一次暂停后，登录节点遗留的自动续跑链重新创建了步骤 `3178423.36`，并从 Epoch 17 checkpoint 恢复 L1；这不是用户手动恢复。
- 经用户再次明确授权，于北京时间 2026-09-21 11:19:37--11:19:42 停止本实验的自动续跑 PID `2817462`、`2323498`，并终止步骤 `3178423.36` 及其 L1 训练进程。
- 未停止其他 kernel，未修改或停止 Job 3178538；Slurm/Jupyter Job 3178423 本身继续保持 `RUNNING`。
- 保留的 P0 等待器 PID `2337336` / 步骤 `3178423.42` 随后取得共享互斥锁，完成一次 BLIP2 单样本前向探测。
- P0 结果：`status=passed`，`parameter_updates=0`，`training_started=false`；步骤 `3178423.42` 于 11:21:07 正常 `COMPLETED`。
- 最终核验时间：2026-09-21 11:21:33 CST。g07 GPU0 总显存 81920 MiB、已用 1221 MiB、空闲 79955 MiB、利用率 0%；仅保留未触碰的 PID `1998199`（1210 MiB）。
- 最终无 `run_formal_top3_stage2_replacement_job_20260827.sh`、LLaVA 训练或 P0 探测进程存活，且没有新的自动续跑步骤产生。
- 后续恢复必须等待用户再次明确下令，并严格按上文恢复点与原实验协议执行。
