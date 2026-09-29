# 实测完成，L8 已恢复

核验时间：2026-09-29T21:42:32.688920+08:00

| 层 | 完整首轮进程显存采样峰值 | 含开销与余量的门槛 |
|---|---:|---:|
| L20 | 61.94 GiB | 64.50 GiB |
| L17 | 62.40 GiB | 65.00 GiB |

两层共用启动门槛已设为 **65.00 GiB**，包含设备开销估计、2 GiB 余量和向上取整，不再固定为 76 GiB。

L8 已由完整 Epoch 41 检查点恢复。核验时 PID 3739096，实际训练进度 Epoch 42，104/636；恢复命令仅更换 checkpoint 路径，50 轮总预算及其他训练参数保持一致。

后续顺序：L8 训练完成 → L8 全量评测及归档 → L20 正式训练及评测 → L17 正式训练及评测。两个显存测试均为独立完整首轮，不用其权重继续正式训练；首轮峰值不是完整 50 轮峰值的保证。

证据：completed_reorder_verification.json、上级 measured_gate.json、两个 layer_*/accepted_probe.json 与 probe_report.json。

---

# 当前顺序：先测显存，再恢复 L8

用户最新要求：暂停 MiniGPT-4 × MMKE-entity L8，先测 InstructBLIP × EVQA-pilot500 L20、L17 的门槛，再恢复 L8；L8 训练、评测及归档完成后，才正式训练 L20、L17。

已执行：原 L8 训练 PID 2512011 与原控制器 PID 2500705 已按身份核验后退出。新控制器 PID 3415905 在原 Job 3443209 / G09 中接管原 GPU 锁，未操作其他 GPU 用户或其他项目进程。

恢复点：完整 Epoch 41，step 13038；备份 SHA256 为 9df11e5c526a43012ed3588510ae5b9f2a778b26c3d4e5b57788939198858bf3。104 个权重/优化器张量均为有限值，26 组优化器状态有效。后续从 Epoch 42、step 13039 恢复，仍训练至总计 50 轮。暂停前 Epoch 42 的少量未完成工作会重算。原 checkpoint 没有完整 RNG 状态，因此采用已有恢复机制，不声称与完全不中断逐位一致。

两个显存测试各独立执行一轮完整 500 样本、250 个 batch，包括原配置的模型加载、缓存预处理、前向、反向和优化器更新；不写正式训练完成标记，不把测试权重用于正式训练。两层测试完成后，取较高显存估计值加 2048 MiB 余量并向上取整至 256 MiB，不再固定等待 76 GiB。

控制器顺序：L20 显存测试 → L17 显存测试 → 恢复 L8 → L8 训练完成 → 原队列优先全量评测/归档 L8 → 按实测门槛正式训练/评测 L20 → L17。

测试失败会保留错误，仍优先恢复 L8；不会因显存探测失败而丢弃 L8 进度。失败测试必须检查后修复，不能编造门槛；后续队列也不会把失败测试当作完成。

验证：继承此前 7 项显存与调度测试，新增 4 项顺序/失败恢复/恢复参数测试在本地和服务器通过。恢复命令仅替换 checkpoint 路径，epochs=50、batch=2、seed、数据及其他原训练参数保持一致。

状态、日志与凭据：status.json、controller.log、checkpoint_verified.json、handoff.json、plan.json、profile_outcome.json、resume_launch.json、resume_L8_epoch41.log。实测结果位于上一级 layer_20/accepted_probe.json、layer_17/accepted_probe.json 和 measured_gate.json。

本文记录接管及自动执行顺序；是否已测完、是否已恢复，以最新 status.json 和实际日志为准。
