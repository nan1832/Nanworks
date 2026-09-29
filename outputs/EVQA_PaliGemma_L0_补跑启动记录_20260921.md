# EVQA × PaliGemma L0 主配置重训启动记录

- 用户授权：在 3178538 先重训 PaliGemma L0；结束后让原 EVQA × LLaVA 启动器按显存门槛自动继续。
- 启动时间：2026-09-21 22:21:51 CST。
- Slurm：Job 3178538，step 108，g08 / GPU0；没有新建 allocation，没有使用 g09。
- 登录节点 srun PID：3712897；g08 控制器 PID：660581；训练 PID：660670。PID 仅代表本次启动，后续操作必须复核身份和启动时间。
- 配置：50 epoch，batch=2，lr=1e-4，seed=20260601，EMA alpha=0.1，data_buffer_size=4。训练 500 条，独立评测 2093 条。
- 原脚本未修改，使用字节一致的新名称快照；SHA-256：`7c26d9f37d0d0aca4e6f70a7e730d7edbe1dbdb03954ca7766689b4ce91656b3`。
- 配置文件 SHA-256：`408ea59cf079c7eb7b1e70aee64603812d8f81dfa9e3e02e2ef5c871edcac3b6`。

## 路径

共享输出根目录：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_paligemma_l0_main_retrain_job3178538_20260921`

该目录包含 `controller.log`、`training.log`、`protocol.json`、`status.json`、`training_process.json`。评测后预期生成 `eval.log`、`selection_audit.json`、`verified_evaluation.json`、`layer_00/selected_checkpoint.tsv`、`layer_00/eval_full.done` 和逐样本结果。

控制器：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/retrain_evqa_paligemma_l0_20260921.py`

本地同名源代码位于本记录同目录。

## 队列互斥和恢复

- g08 原 LLaVA 等待器 PID 2905258（start_ticks=`86448536`）在确认仅有 sleep 子进程后收到 SIGSTOP；不是终止训练，也未删除现场。
- 旧等待器仍引用已经删除的旧 lock inode。新控制器另持当前路径 `launcher.lock`，防止其他遵守此锁的启动器重复进入。
- 控制器完成/普通异常退出时，先确保自己的训练或评测子进程已退出，再释放当前路径锁；复核原等待器 PID、启动时间和命令后发送 SIGCONT。
- 原等待器恢复后按原门槛等待，目前为 71680 MiB（70 GiB）。未降低门槛，未重启/改写其脚本。
- 若控制器被 SIGKILL 或 allocation 终止，finally 无法执行。届时需读取 `launcher_hold.json`、`launcher_released.json` 并复核进程身份后决定恢复；不可盲目按旧 PID 发信号。
- 3178423 的原 LLaVA 保持暂停，第二阶段 G1 评测不动；其他 kernel 不动。

## 选点、归档与异常

- 只在本次主配置运行内部选择最低有限 EMA checkpoint，并核验 adapter 参数有限；不与历史 main/stable 结果混合挑最大值。
- 若训练异常退出但存在有限 checkpoint，可做诊断评测，并记录训练未完成，不能冒充完整 50 epoch。
- 历史不收敛标签保留。当前重训是否收敛需依据新 loss 曲线判断，不能因有评测分数就改成收敛。
- 输出、cache、TMPDIR 均在上述共享目录。不会向服务器 `/tmp` 写入大量 checkpoint；`/tmp` 仅保留队列小锁文件。
- 完成 50 epoch 且独立 2093 条评测和选中权重哈希核验通过后，对本次目录的非 selected checkpoint 建精确清单、审计后清理；失败/未完成时保留恢复资料。
- 本记录是启动记录，不是完成记录。结果尚未回填正式手册，也未部署自动修改本地手册的任务。

## 启动后核验（2026-09-21 22:28:48 CST）

- 两次观察已从 Epoch 1 的 448/500 推进到 Epoch 2 的 158/500。
- Epoch 1 checkpoint 已保存：step 250，loss=3203.417724609375，EMA=3297.1371699174942。数值有限但较高，不能据此宣称收敛。
- 训练 PID 660670 使用 19076 MiB；整卡使用 36501 MiB、空闲 44675 MiB、利用率 100%。原 5 个 kernel 的 PID 和显存占用均保留。
- 原 LLaVA 等待器 PID 2905258 为 T（临时挂起）；控制器保持运行，补跑结束后按记录中的 finally 恢复机制释放。

## 2026-09-22 改为仅评测 Epoch 2（用户明确授权）

- 08:29 复核：日志自 09-21 23:25:56 起停止在 Epoch 31、100/500；已有 30 个 epoch 的 loss 记录，未完成 50 epoch。日志含 154 条 `SANITIZE_NONFINITE_GRAD_BEFORE_STEP` 记录，不能将有限 EMA 理解为没有非有限梯度异常。
- 用户要求“不用续跑，就用这个 epoch 2 测试”。没有重启或续训 PaliGemma。
- 在 CPU 上核验 Epoch 2 / step 500 / EMA=3209.824509720526，Adapter 参数全部有限；checkpoint SHA-256：`9405c64d2e1d5b96f5ab96b0109a25b8dcde2697f46faec319b37727efbef260`。
- 08:33:05，仅向身份核验通过的训练 PID 660670 发送 SIGTERM；其正常退出，未使用 SIGKILL。控制器和 LLaVA 等待器保留。
- 08:33:21，原控制器以 `--skip-train` 启动评测 PID 1438611，固定读取 Epoch 2 selected 记录；评测集是独立 EVQA 2093 条，不是训练 500 条。
- 选点记录状态为 `TRAIN_INCOMPLETE_FINITE_RECOVERED`，`training_complete_50_epochs=false`，历史不收敛标注保留。`nonfinite_history=false` 只指 checkpoint loss/EMA 数值有限，不代表梯度没有异常。
- 共享目录新增 `diagnostic_epoch2_request.json`、`selection_audit.json`、`eval_process.json`；尚未取得评测完成结果。本次不会自动清理未完成训练的恢复 checkpoint。
- 评测结束/控制器普通异常退出后仍会释放 g08 原 LLaVA 等待器，由它按原显存门槛自动继续；g07 不动。

## 2026-09-22 诊断评测完成及本地归档

- 08:47:15 CST评测退出rc=0，2093条全部完成；Epoch2/step500，raw3187.056884765625、EMA3209.824509720526。
- Rel0.16、T-Gen0.18、M-Gen0.16、T-Loc100.00、M-Loc76.96、Average35.492；不收敛及训练未完成50轮的标签保留。
- 08:47:16原控制器记录已向LLaVA等待器2905258发送SIGCONT；没有恢复g07用户暂停的训练。
- 12个轻量证据文件（合计4900044字节）按大小和SHA-256逐一拉回`server_results/live_backfill/pali_l0_diag_20260922/evqa-pilot500/paligemma-3b/layer_00/`。checkpoint本体仍在共享盘。
- 主手册新增3.4.8八方法联合并集核验、3.5.3诊断说明及4.0结果行。没有清理未完成训练的恢复checkpoint，也未启动新的补层训练。
- 同步后的桥接中转文件清理遇到SSH连接超时；本地最终目录已生成，随后独立复验12个文件的大小/SHA-256全部通过，逐样本数2093。可能残留少量桥接中转文件（本次总量约4.7MiB），不能声称中转清理全部完成。末次实时进程查询亦超时，因此不报告新的GPU/等待器实时状态；前述08:47:16释放记录来自已取得的控制器产物。
