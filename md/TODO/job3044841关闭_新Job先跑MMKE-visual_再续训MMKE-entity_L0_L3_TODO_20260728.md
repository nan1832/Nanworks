# 2026-07-28 09:42 计划变更（当前执行版）

## 2026-07-28 14:01 再次变更：仅完成 MiniGPT-4 五层

- 不打断当前 MMKE-visual MiniGPT-4 L0 训练。
- 只完成 MiniGPT-4 `L0,L1,L2,L3,L29`；每层继续按“训练→独立 MMKE-visual eval 正式评测”执行。
- 五层必须同时具备 `train.done`、有效 `selected_checkpoint.tsv`、`eval_full.done` 和非空 `results.json` 才算完成。
- 五层完成后停止本轮 launcher，保留 Job 3044841，不启动任何 LLaVA 层。
- 已部署独立收尾监控 `stop_mmke_visual_launcher_after_minigpt5_job3044841.sh`；它仅在 L29 评测进程退出且五层产物齐全后停止 launcher，不会中断当前训练或评测。
- 下文关于“随后自动运行 LLaVA 十五层”的安排全部取消；LLaVA 留待重新安排。

- **不关闭 Job 3044841**，让它在 `2026-08-02 10:30:24 CST` 到期后自行停止。
- 已保存 MMKE-entity MiniGPT-4 L3 最新可恢复 checkpoint：Epoch 19、`i=6042`、EMA loss `2.4269`。
- 加固副本：`login01:/var/tmp/ph_teacher3/job3044841_20260728/mmke_entity_minigpt4/L3_epoch19_switch_20260728_0940/epoch-19-i-6042-ema_loss-2.4269`。
- 源文件与副本 SHA-256 均为 `7f9ce08c4ee6b9d820f094fae6acaf63690645a221fc80a8314a305a9a53c42c`。
- 已停止旧的 MMKE-entity L3 launcher/训练进程，但保留 Job 3044841。
- 已于 `2026-07-28 09:42:11 CST` 在 Job 3044841 / g09 / GPU1 启动 MMKE-visual 队列。
- 本轮实际补跑顺序：MiniGPT-4 `L0,L1,L2,L3,L29`；随后 LLaVA `L0,L1,L2,L7,L8,L9,L12,L13,L14,L15,L16,L22,L24,L26,L27`。
- 两个 MMKE-visual 模型完成后，再按原计划恢复 MMKE-entity MiniGPT-4 L0、L3；若 Job 到期，则在新 Job 中从已备份 checkpoint 恢复。

下文“关闭当前 Job、申请新 Job 后再开始”的旧计划已由以上变更替代，仅保留作历史交接依据。

# Job 3044841 关闭、新 Job 实验与 MMKE-entity 续训 TODO

记录日期：2026-07-28  
执行状态：**等待用户明确命令，当前不得关闭 Job、停止训练或启动新实验。**  
当前 Job：`3044841`，节点 `g09`，物理 GPU1。服务器 `scontrol` 显示到期时间为 `2026-08-02 10:30:24 CST`。

## 一、固定执行顺序

- [ ] 1. 收到用户明确命令后，关闭 Job 3044841 前最后核验并记录 MMKE-entity MiniGPT-4 L0、L3 现场。
- [ ] 2. 确认恢复 checkpoint 已脱离 g09 Job 本地 `/tmp`，并再次核验 SHA-256。
- [ ] 3. 关闭 Job 3044841，申请/使用新 Job。
- [ ] 4. 新 Job **先完成 MMKE-visual MiniGPT-4 候选层**训练及正式 eval 评测。
- [ ] 5. 接着完成 **MMKE-visual LLaVA 候选层**训练及正式 eval 评测。
- [ ] 6. 两个 MMKE-visual 模型全部完成后，恢复 **MMKE-entity MiniGPT-4 L0**。
- [ ] 7. L0 完成训练和正式 eval 评测后，恢复 **MMKE-entity MiniGPT-4 L3**。
- [ ] 8. 回填本地总表并更新完成、失败、重跑和异常标记。

不得改变上述顺序。任何启动、停止、删除、覆盖或重跑操作均需先获得用户明确命令。

## 二、关闭 Job 3044841 前的保护检查

### 2.1 已有可恢复现场

| 数据集/模型/层 | 状态 | 可恢复 checkpoint | 恢复方式 |
|---|---|---|---|
| MMKE-entity / MiniGPT-4 / L0 | 未完成、未评测 | Epoch 28，`i=8904`，EMA loss `1.4432` | 从 Epoch 28 恢复，重新执行 Epoch 29 |
| MMKE-entity / MiniGPT-4 / L3 | 未完成、未评测 | Epoch 17，`i=5406`，EMA loss `2.6138` | 从 Epoch 17 恢复，重新执行 Epoch 18 |

已核验恢复副本：

`/var/tmp/ph_teacher3/job3044841_20260728/mmke_entity_minigpt4`

| 层 | 文件 | SHA-256 |
|---|---|---|
| L0 | `L0/epoch-28-i-8904-ema_loss-1.4432` | `25d4cac7d7c09c4ffead6e2b737673b812a1617c5c68f3640bd961fb5c5dd348` |
| L3 | `L3/epoch-17-i-5406-ema_loss-2.6138` | `108c6c622f5f2376c29093de30dc1dcb0176b874fb252ec9d2a7b2ef24861f98` |

该目录还保存 `HANDOFF.md`、`run_config.json`、训练日志和 `loss_history.csv`。两个 checkpoint 的 SHA-256 已与 g09 原文件交叉核验一致。

### 2.2 关闭前必须再做一次

- [ ] 查询 `squeue`、`scontrol`、GPU 进程和父子进程树，确认待关闭的是 Job 3044841/GPU1，不影响 Job 3044208/GPU0。
- [ ] 检查 L3 是否生成了比 Epoch 17 更新且完整的 checkpoint；若有，先另存并校验，再更新本 TODO。
- [ ] 检查 checkpoint 文件大小不为 0，排除仅有 `.lock` 文件的情况。
- [ ] 保存 L0、L3 最新日志、loss history、run config 和异常退出记录。
- [ ] 确认新 Job 能从 login01 的 `/var/tmp` 复制恢复文件。
- [ ] 用户明确下达“关闭”命令后才关闭 Job。

说明：关闭 Job 会终止训练、launcher 和 Jupyter kernel。`/datapool` 数据不受影响；g09 的 `/tmp` 不保证长期保留，新 Job 若分配到其他节点也无法直接访问。因此不能把 g09 `/tmp` 当成持久归档。

## 三、新 Job 启动前检查

- [ ] 记录新 Job ID、节点、物理 GPU 编号、到期时间和结果根目录。
- [ ] 确认 GPU 上没有其他训练任务；记录显存总量、已用、空闲、利用率及 GPU PID。
- [ ] 确认 MiniGPT-4/LLaVA 原始模型、代码、YAML、训练数据、eval 数据均可只读访问。
- [ ] 新结果优先写新计算节点本地 `/tmp/ph_teacher3/...`，避免共享盘配额错误。
- [ ] 建立 launcher、训练、正式评测和 watchdog 的独立日志。
- [ ] watchdog 只能在“同一日志连续 2 小时没有训练/评测进展”时停止；禁止按总运行时间 2 小时停止。
- [ ] 严禁用训练集评测；训练成功后必须使用对应的 test/eval 数据。

## 四、第一阶段：MMKE-visual MiniGPT-4

### 4.1 候选层依据

候选层只允许来自：

`md/Location/6location_7model_3datas_top_3_5_layers_outcome.md` 的 `### 3.2 MMKE-visual`。

当前文档快照中的 8 方法 Top-3 并集为：

`L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L29,L28,L27`（16 层）

启动前必须把这 16 层与服务器现有真实结果交叉核验：只有同时存在 `selected_checkpoint.tsv`、`eval_full.done` 和完整正式评测结果的层才算完成；本轮只运行缺失层，不重复覆盖已经完成的有效结果。

### 4.2 固定数据和配置

- 模型：`minigpt-4-vicuna-7b`
- Epoch：50
- Batch size：2
- Seed：20260601
- 训练数据：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json`
- 正式评测数据：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_eval_evqa_compat.json`
- 图片根目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image`
- YAML：`configs/vead/minigpt-4-vicuna-7b.yaml`
- 80 GB 显存不足时允许使用既有低显存调度：`data_buffer_size=1`、同步 CPU 数据加载、activation checkpointing；不得改变 batch size、学习率、epoch 或优化目标。

### 4.3 每层验收

- [ ] 训练日志到 Epoch 50 或按全程 checkpoint 中 EMA loss 选择有效 checkpoint。
- [ ] `train.done` 存在。
- [ ] `selected_checkpoint.tsv` 存在且指向实体 checkpoint。
- [ ] 使用 MMKE-visual eval JSON 完整评测。
- [ ] `eval_full.done` 存在且评测结果文件完整。
- [ ] 无 OOM、nonfinite、Traceback、磁盘错误、无 selected checkpoint 或假完成标记。

## 五、第二阶段：MMKE-visual LLaVA

### 5.1 候选层依据

同样只允许来自总表 `### 3.2 MMKE-visual`。

当前文档快照中的 8 方法 Top-3 并集为：

`L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L13,L12`（16 层）

启动前与真实结果交叉核验，只运行缺失层。

### 5.2 固定数据和配置

- 模型：`llava-v1.5-7b`
- Epoch：50
- Batch size：2
- Seed：20260601
- 训练数据：与 MiniGPT-4 相同的 MMKE-visual train JSON。
- 正式评测数据：与 MiniGPT-4 相同的 MMKE-visual eval JSON。
- YAML：`configs/vead/llava-v1.5-7b.yaml`
- 低显存规则与 MiniGPT-4 相同，不改变可比性参数。

验收条件与第四节完全一致。

## 六、第三阶段：恢复 MMKE-entity MiniGPT-4 L0

- [ ] 从 login01 `/var/tmp` 把 L0 checkpoint 复制到新计算节点本地 `/tmp`。
- [ ] 重新计算 SHA-256，必须等于 `25d4cac7d7c09c4ffead6e2b737673b812a1617c5c68f3640bd961fb5c5dd348`。
- [ ] 使用原模型、原 YAML、原 optimizer state、batch size 2、epoch 50 和原数据恢复。
- [ ] 从 Epoch 28 checkpoint 恢复，Epoch 29 从头重新执行；不能把旧日志中的 Epoch 29 局部 step 当作已保存状态。
- [ ] 完成训练后使用 `vqa_mmke_entity_eval_evqa_compat.json` 正式评测。
- [ ] `selected_checkpoint.tsv`、实体 checkpoint、完整评测结果和 `eval_full.done` 齐全后才算完成。

## 七、第四阶段：恢复 MMKE-entity MiniGPT-4 L3

- [ ] 仅在 L0 正式评测完成后开始。
- [ ] 从 login01 `/var/tmp` 把 L3 checkpoint 复制到新计算节点本地 `/tmp`。
- [ ] 重新计算 SHA-256，必须等于 `108c6c622f5f2376c29093de30dc1dcb0176b874fb252ec9d2a7b2ef24861f98`。
- [ ] 使用原模型、原 YAML、原 optimizer state、batch size 2、epoch 50 和原数据恢复。
- [ ] 从 Epoch 17 checkpoint 恢复，Epoch 18 从头重新执行。
- [ ] 完成训练后使用 `vqa_mmke_entity_eval_evqa_compat.json` 正式评测。
- [ ] `selected_checkpoint.tsv`、实体 checkpoint、完整评测结果和 `eval_full.done` 齐全后才算完成。

## 八、异常处理规则

- 进程活着不代表正常：必须同时确认日志更新时间、Epoch/Step 前进和合理 GPU 利用率。
- `rc=143`、`rc=137` 是进程退出码，不是失败次数。
- OOM、nonfinite、无 selected checkpoint、评测缺失、磁盘配额错误、日志连续 2 小时无进展均单独记录。
- 发现异常先记录原因和建议，未经用户确认不得自动 kill、删除、覆盖或重启。
- 没有 `eval_full.done` 或没有完整评测结果的层不得登记为完成。

## 九、最终回填

每完成一层，需同步更新：

`D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\md\Location\6location_7model_3datas_top_3_5_layers_outcome.md`

回填内容至少包括：模型、数据集、层、selected checkpoint、评测样本数、各指标、Average、异常、重跑方式、完成状态和服务器结果路径。

原始 L0/L3 交接记录：

`md/Location/job3044841_MMKE-entity_MiniGPT4_L0_L3_resume_handoff_20260728.md`
