# InstructBLIP 显存门槛实测接入记录

部署状态：ARMED_AFTER_L8_EVALUATION。已接入待恢复队列，显存实测尚未执行，不能把这里的配置写成实测结果。

执行顺序：MiniGPT-4 × MMKE-entity L8 训练完成 → L8 全量评测与归档校验 → InstructBLIP × EVQA-pilot500 L20 独立一轮显存测试 → L17 独立一轮显存测试 → 原协议 L20、L17 各 50 轮正式训练及评测。

原固定 77,824 MiB 门槛由新模块覆盖。两层各覆盖完整 500 条训练数据的预处理、250 个训练批次、优化器更新和第一轮检查点保存。探测进程随后退出，不生成正式 train.done、eval_full.done 或 selected_checkpoint.tsv，探测权重不用于正式训练。原训练参数只在探测中更换独立输出目录，原 epochs=50 参数保留，由包装器在完整第一轮后结束。正式训练使用原 runner、原参数和全新正式进程。

门槛计算：取两层较高的显存估计值，加 2,048 MiB 余量，向上取整到 256 MiB。每层估计值为 NVIDIA 进程显存采样峰值与 PyTorch reserved 高水位加非分配器开销估计两者的较大值；非分配器开销至少预留 1,024 MiB。因此门槛不再固定为 76 GiB，也不会强行压低实测需求以便放行。

探测启动时采集三次空闲显存，以最低值减 3,072 MiB 作为该探测进程的 PyTorch 分配器预算。该限制仅用于独立探测，不加到正式训练上。实际共享进程后续增长仍可能造成显存不足。一轮测量不是完整 50 轮最大峰值的保证。

若探测 OOM、未完成完整一轮或其他错误，记录原因并停止检查，不自动重试、不退回猜测门槛、不改变 batch 或训练协议。只管理本次创建的探测子进程。两个当前进程 2512011、2500705 未重启。原训练源码、配置、数据与其全部校验值保持有效。

验证：本地及服务器各通过 7 项针对性测试，包含 L8 评测依赖、测量先于正式训练、低于旧门槛时能放行、真实较高需求仍等待、其他模型及评测门槛保持不变、完整一轮及优化步骤计数、探测不进入正式选点。部署后已核验未来入口、全部 plan pins 和实际 Python 环境的 PyTorch 显存统计/限制接口。

服务器目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/memory_calibration_20260929

后续证据：layer_20/accepted_probe.json、layer_17/accepted_probe.json、measured_gate.json。尚未生成这些证据时，门槛数值应标为待实测。

备份：before_eligible_queue.py、before_priority_plan.json。部署凭据：deployment.json；复核凭据：verification.json。

部署时间：2026-09-29T20:07:44.483756+08:00
复核时间：2026-09-29T20:08:43.148132+08:00
复核时训练日志：Epoch 39:   0%|          | 2/636 [00:04<21:52,  2.07s/it]
