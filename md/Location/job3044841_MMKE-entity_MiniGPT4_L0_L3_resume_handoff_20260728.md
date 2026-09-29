# Job 3044841：MMKE-entity MiniGPT-4 L0/L3 续训现场

记录时间：2026-07-28 08:48 CST  
原任务：Slurm Job 3044841，g09，物理 GPU1  
模型：MiniGPT-4-Vicuna-7B  
配置：50 epochs，batch size 2，data_buffer_size 4，seed 20260601  
训练集：`vqa_mmke_entity_train_evqa_compat.json`  
评测集：`vqa_mmke_entity_eval_evqa_compat.json`（后续完成后必须用该 eval 数据正式评测）

## L0

- 状态：未完成训练、未评测，不能计为完成结果。
- 终止前日志位置：Epoch 29，138/636。
- 终止情况：原进程退出码 rc=137；该数值是进程退出码，不是失败次数。
- 最近完整可续训 checkpoint：Epoch 28，global step `i=8904`，EMA loss `1.4432`。
- checkpoint 文件约 415,895,994 bytes，包含继续训练所需状态。
- 恢复点：从 Epoch 28 checkpoint 恢复，重新执行 Epoch 29；不要从日志中的 138/636 直接接续。
- `selected_checkpoint.tsv`：无。
- `eval_full.done`：无。

## L3

- 状态：记录时仍正常训练；未完成训练、未评测，不能计为完成结果。
- 记录时实时进度：Epoch 18，180/636；日志持续更新，GPU 利用率 100%。
- 最近完整可续训 checkpoint：Epoch 17，global step `i=5406`，EMA loss `2.6138`。
- checkpoint 文件约 415,895,886 bytes，包含继续训练所需状态。
- 恢复点：从 Epoch 17 checkpoint 恢复，重新执行 Epoch 18；不要从日志中的 180/636 直接接续。
- `selected_checkpoint.tsv`：无。
- `eval_full.done`：无。

## 后续顺序（等待用户明确命令）

1. 新 Job 先做 MMKE-visual 的 MiniGPT-4 与 LLaVA 候选层训练和正式评测。
2. MMKE-visual 两个模型完成后，再恢复 MMKE-entity MiniGPT-4 L0。
3. L0 完成正式评测后，再恢复 MMKE-entity MiniGPT-4 L3。
4. 当前不关闭 Job、不停止进程、不启动新实验；所有操作等待用户命令。

## 原始结果根目录

`/tmp/ph_teacher3/mmke_entity_minigpt_llava_job3044841_20260726/minigpt-4-vicuna-7b`

注意：该目录位于 g09 节点本地 `/tmp`，关闭任务前必须使用持久化副本；不能仅依赖 `/tmp`。

## 已核验恢复副本

由于 `/datapool` 用户配额仍满，复制到共享结果目录时返回 `No space left on device`。已改为在 login01 的 `/var/tmp` 保存独立恢复副本；该目录不属于 Slurm Job 3044841 的临时目录，关闭 Job 不会随作业 cgroup 一起删除。

恢复副本根目录：

`/var/tmp/ph_teacher3/job3044841_20260728/mmke_entity_minigpt4`

- L0：`L0/epoch-28-i-8904-ema_loss-1.4432`
  - SHA-256：`25d4cac7d7c09c4ffead6e2b737673b812a1617c5c68f3640bd961fb5c5dd348`
- L3：`L3/epoch-17-i-5406-ema_loss-2.6138`
  - SHA-256：`108c6c622f5f2376c29093de30dc1dcb0176b874fb252ec9d2a7b2ef24861f98`

上述校验值已分别与 g09 原 checkpoint 重新计算并交叉核验，完全一致。新 Job 启动后应先把 checkpoint 从 login01 复制到新计算节点本地 `/tmp`，再次核验 SHA-256，然后才执行续训。
