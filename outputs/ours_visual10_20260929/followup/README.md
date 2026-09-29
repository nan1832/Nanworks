# 十式补算：当前组结束后的三组排查与重算

授权：用户要求“当前组完成后排查这三个错误原因，能重算这三个就重算”。

服务端：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_visual10_20260929/followup_20260929`。
运行位置：Job `3435286` / G08；启动及进程信息见 [launch_receipt.json](launch_receipt.json)。当前是等待阶段，尚未排查或重算。

## 执行顺序

1. 等待 InstructBLIP × MMKE-entity 完成全部 636 个样本，且原控制器和计算进程均退出。当前组即使在最终复现校验中未通过，也不会被擅自加入本次重算范围。
2. 只处理 PaliGemma × MMKE-entity、Qwen2.5-VL × EVQA-pilot500、Qwen2.5-VL × MMKE-visual。
3. 核对原文件哈希、全部样本与冻结 old/new 目标，从逐样本记录重新聚合，输出每一层每项指标的实际值、历史值、误差与原容差。数据或实现漂移时记录原因并保留结果，不自动适配新的协议。
4. 对仍可复现的统计误差，每组至多进行一次全量、独立输出的重算。采用历史单层梯度函数及层优先遍历顺序，附加代表样本的重复梯度/历史 loss 对比。执行顺序是排查变量，不预先宣称其为错误根因。
5. 重算必须取得 `gpu_locks/g08_gpu0.lock`，并满足连续三次空闲显存至少 60,000 MiB，间隔 20 秒，取得锁后再次核验。现有任务的锁与进程不变。
6. 使用原 `rtol=1e-3, atol=1e-8` 完整校验，保持原样本、目标、公式、模型精度。通过后使用原验证器生成并发布十式排名；旧失败目录原样保留。仍失败则保存诊断和重算证据，不放宽阈值、不无限重试。

## 结果与同步

- 服务端 `status.json`、`diagnostics/`、`retry_raw/`、`outcomes.json` 保存状态与证据。
- 本地 [latest_snapshot.json](latest_snapshot.json) 保存同步到的状态、诊断、重复梯度探针、重算进度和比较结果。
- 后继同步进程等待原同步器释放锁后接手，每 120 秒同步一次；启动信息见 [successor_launch.json](successor_launch.json)。只更新主文档的 `OURS_VISUAL10_RESULTS_BEGIN/END` 区域。
- 服务器后续任务不依赖本地电脑保持在线；本地休眠或断网会延后文档回填。
- 服务端正式 `published/` 中修复成功组的 `evidence.path` 指向本次重算，主 manifest 记录 followup。原始队列已经退出，不应再运行旧 `publish` 命令覆盖这些修复结果。

实现：[后续控制器](../../../scripts/followup_ours_visual10_20260929.py)、[同步器](../../../scripts/manage_ours_visual10_20260929.py)。验证：7 项自动检查通过，服务器已核实 `WAITING_CURRENT_GROUP` 状态。
