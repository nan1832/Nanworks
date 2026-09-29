## 最新完成记录：Qwen BF16 全量修复

服务器完成时间：2026-09-29T12:17:16+0800。本地复算与回填已通过，14/14 组、42 个模块版本全部完成。

- 本次补算 Qwen × MMKE-visual：214/214，失败 0；Qwen × MMKE-entity：636/636，失败 0。
- 根因验证：原 auto 加载器固定使用 FP16；8 个诊断样本中，6 个历史失败样本均复现非有限输出。模型原生 BF16 下 8/8 通过。
- 权重文件头核验：Qwen 两个 safetensors 分片的 824 个权重张量均为 BF16（含视觉编码器 390 个张量），与模型配置一致。
- 两组均按 BF16 全量重算，没有混用原 FP16 的部分成功样本；精度可能改变预测与贡献度数值，表格已单独标注。
- 数据、提示词、贡献度公式和 Pre 候选规则沿用原版。完整输出的哈希、逐样本 p/v、三种排名和 Pre 已本地复算核验。
- 当前结果是 model_pred-NextTokenArgmax 首预测位置对照；完整 model_pred 回答逐 token 贡献度尚未执行。
- 修复诊断第一版因检查超大词表张量触发 INT_MAX 索引限制而退出；第二版只检查实际计分预测位置的 logits，保留原始诊断日志。
- 原始 FP16 部分结果和诊断第一版均保留于服务器；正式修复来源为 qwen_repair_bf16_v2/results。
- g09 MiniGPT4 L8 及已停止的 LGA 队列未改动；GPU 通过共享项目锁使用，结束后自动释放。

本地 Qwen 逐样本文件以 samples.json.gz 保存（gzip JSON：文件名到原始 JSON 字节的 base64 映射），summary.json 记录压缩包及每条原始记录的哈希。
证据：completion_receipt.json、qwen_repair/completion_audit.json、qwen_repair_bf16_v2/diagnosis.json 和各组 local_verification.json。


以下为历史执行记录，进度、进程号与等待安排以本节和最新状态文件为准。

---

# VisEdit-model_pred：MMKE 两数据集补算

> **用户后续纠正（优先于以下早期计划）：** model_pred 是基础模型对原始图文对的完整输出。此前把它定义为下一 token 的表述错误。代码核查确认，当前队列只计算下一 token logits argmax 的贡献度，没有生成/冻结完整回答，没有逐答案 token 聚合。总表和生成器已明确改名显示 `model_pred-NextTokenArgmax（首预测位置对照）`，机器可读文件另加 `attribution_scope=next_token_argmax`。此任务队列的 DONE 仅代表首预测位置对照完成，不能宣称用户的完整 model_pred 回答归因已经完成。当前等待用户确认归因范围：全部答案 token 作为正式版，还是保留首预测位置口径。用户尚未要求停止首预测位置对照，因此现有队列保持运行、已有产物保留。

> 完整回答版如确认执行，应另立版本，优先核查与原始图文样本绑定的冻结 model_pred 回答、输入模板一致性和有效预测位置，不能直接把这里的单 token 结果换名，也不能因为使用同一个 target 名称就认定模型原始输出一致。已有 VisualTrack-Cos 全回答版是另一方法，不等于 VisEdit 全回答贡献度。

用户 2026-09-29 明确要求补算两个 MMKE 数据集缺少的 VisEdit-model_pred，并回填 `md/Location/ALL_Methods_Recommends_layers.md` 对应位置。任务覆盖 7 模型 × 2 数据集 = 14 组，输出 attn、MLP、attn+MLP 三版，共 42 组模块排名/Pre 候选。不是 VisualTrack-Cos 三版本任务；后者已完成，不能混淆。

## 已完成的准备和首批结果

- 检查本地与服务器归档：历史 MMKE `pred` 是数据集字段，不是 model_pred。真实缺项为 14 组。
- 使用原贡献度脚本和模型输入流程，冻结代码于 `source_snapshot/`。目标为输入末位置模型下一 token argmax，沿用已有 E-VQA model_pred 口径，不是完整生成答案。
- 原始数据：MMKE-Bench/data_json/visual_train.json（214）和 entity_train.json（636）；原始图像目录 data_image。逐样本保存预测 token ID/文本、各层 p/v、图像与协议哈希。所有原始样本均须成功；不把失败值置零。
- 贡献度公式精确复用原脚本（含 epsilon）；先平均有符号贡献，再对模块均值取非负部分。attn、MLP 分别使用正贡献，联合版为二者之和。保留原始有符号均值和单模块有符号排名以便追溯。
- Pre：3 层滑动均值，mean+0.5×总体标准差；取最长高贡献连续区，等长取和更大、再取更浅；推荐区间起点前最多 3 层，不足不补。
- 首组 MMKE-visual × BLIP2 已全量完成、下载并独立复算。其余状态以服务器及 sync_status.json 的实时内容为准。
- 已扩展 `scripts/build_all_method_recommendations.py`：第 6.2.2、6.3.2 各自生成 attn/MLP/联合三个表，只有完整且本地复算通过的组合才替换待补；同时更新机器可读推荐、逐层分数、VisEdit 排名和主总账方法目录。
- 新文件全保存在本目录；修改前两份文档备份于 `backups/`。其他方法内容（忽略一个空行）、VisualTrack 三版本保留；主总账第 3 节起的真实编辑与历史记录字节一致，见 implementation_verification.json。

## 服务器执行和限制

- 连接：`scripts/lga_ablation_remote.py` 的 ssh helper，bridge-server 密钥为用户 `.ssh/id_ed25519_bridge`，再 SSH g08。
- 基目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2`。
- 本任务服务器目录：`server_results/visedit_model_pred_mmke_20260929`。
- Job3435286 / g08，项目 GPU 锁为 `server_results/gpu_locks/g08_gpu0.lock`。队列串行加载各模型，每模型先 visual 后 entity。
- 09:55:31 实际队列 controller PID3538983，首个子进程3539055；需实时查 control/status.json 验证，不能只靠旧 PID。
- 09:54 首次 detached 启动 PID3538450 已退出且没有计算。control/launch.json 是这次无效旧记录；真正运行由 status.json 和实际进程判定。
- 第二次通过保持 SSH 会话运行，当前本地 unified exec session ID63169。不要终止该会话；它等待完整队列退出。可用进度文件独立查询，无需轮询这个会话。
- 已启动一次性计算收尾进程：本地隐藏 Python PID31600，`scripts/finalize_visedit_model_pred_mmke_20260929.py`。它依赖当前服务器 controller 退出（GNU tail --pid），随后自动执行本地同步/独立复算/回填；不启动新 GPU 任务。查看 finalizer_status.json、finalizer.log、finalizer.stderr.log。若队列没有 14 个完整组，状态为 NEEDS_REPAIR，不能称完成。该收尾步骤是本次计算流水线的一部分，不是新的周期训练任务。
- 桌面 heartbeat 创建调用长时间没有返回确认，已终止等待（functions cell86）；不能仅据调用认定自动跟进已创建，且未重复创建。已有一次性收尾程序负责正常队列结束后的本地回填。如之后发现原调用实际创建了同名 heartbeat，全部完成后暂停它。
- 队列脚本 `code/queue_visedit_model_pred_mmke_20260929.py`，runner 为 `code/run_visedit_model_pred_mmke_20260929.py`，Qwen 环境 Python 执行全部模型，沿用旧贡献度启动器设置。
- `control/status.json` 含当前模型、PID、log、outcomes；各组 results/<dataset>/<model>/progress.json、samples/、failures/、summary.json。
- 仅完整组生成 summary.json。连续累计 3 个异常会中止该组并继续下一组，队列终态可能 NEEDS_REPAIR。必须查错误并修复后才能称全部完成。
- **g08 的 LGA 队列已经用户要求停止（STOPPED_BY_USER），禁止恢复。g09 的 MiniGPT4 L8 正在继续原训练，禁止干扰或改动其他任务。**

## 同步和完成核验

本地 Python：`C:/Users/zhoun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`。

运行 `scripts/sync_visedit_model_pred_mmke_20260929.py`。它只读服务器，检查完整组全部样本哈希，下载新的完整组，在本地重新计算原始贡献度与三个模块版本的排名和 Pre，然后回填两份 Markdown 及相关 JSON/CSV。未完成样本不会进入正式表。脚本耗时数十秒；不要同时运行多个实例。

完成标准：14 个模型×数据集全部全量成功，42 个模块变体都完成；local_verification 全部通过；总表第 6.2.2、6.3.2 的 42 行均为实际结果；原有其他方法、E-VQA、alt、历史 pred 和真实编辑明细保留。完成后暂停本任务的自动跟进，向用户提供文件链接。没有新进展时不重复打扰。

若需修复，保留已完成产物并检查协议哈希约束。不要直接覆盖既有原始记录或把新代码结果混进旧协议；必要时使用独立 repair 版本并说明差异。用户已授权完成本次缺项补算，但未授权恢复其他停止的任务或修改训练配置。
