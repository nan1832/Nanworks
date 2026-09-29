# Ours 视觉表征梯度 10 式补算（2026-09-29）

范围：用户图片定义的 V01–V10；逐样本计算后等权平均；不训练 Adapter、不计算新的参数梯度、不改既有训练配置。

- 主表：[ALL_Methods_Recommends_layers.md 第 7 节](../../md/Location/ALL_Methods_Recommends_layers.md)。
- 计算与 CPU 校验：[ours_visual10_20260929.py](../../scripts/ours_visual10_20260929.py)。
- 同步与机械表格回填：[manage_ours_visual10_20260929.py](../../scripts/manage_ours_visual10_20260929.py)。
- 单元测试：[test_ours_visual10_20260929.py](../../scripts/test_ours_visual10_20260929.py)，覆盖公式、聚合顺序、Tukey、同分、有限零分、非有限拒绝。
- `sync_receipt.json` 给出当前本地不可变快照及逐文件 SHA-256；`snapshots/*/published` 保存 21 组的每层精确分数、Raw/Tukey 完整排名、Top-3/5 和剔除层。
- `watch_status.json` 与 `watch_stdout.log` 记录本地每 120 秒的自动同步；计算仍在服务器执行。同步器最长运行 24 小时；电脑休眠、断网或连续 5 次异常会影响回填，但不停止服务器任务。手动重启同步器用 `python scripts/manage_ours_visual10_20260929.py watch`；一次回填用 `sync`。

## 服务端

Job 3435286 / G08：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_visual10_20260929`。

使用现有 `server_results/gpu_locks/g08_gpu0.lock`；至少 60,000 MiB 空闲显存连续三次、每次间隔 20 秒后获取锁，再核验显存。只创建独立输出，不改旧队列或 STOP 标记，不停止任何其他进程。G09 现有训练不动。

补算模型顺序：SmolVLM → PaliGemma → Qwen2.5-VL → LLaVA → InstructBLIP；每个模型依次 EVQA-pilot500、MMKE-visual、MMKE-entity，已有完整组核验后跳过。原 9 组完整视觉逐样本量直接复用；LLaVA×MMKE-entity 保留的 40 样本可续接，最终仍需整组核验。

多 Hook 优化仅在浅/中/末层对旧、新目标的原始梯度张量核验通过后使用（rtol=1e-5、atol=1e-7）；不通过则回退原逐层函数，不放宽阈值。整组还需复现历史 dot/cos/old_norm/new_norm/joint_norm 均值（既定 rtol=1e-3、atol=1e-8），否则不发布新的交叉项候选。

原始成功样本集合与冻结 model_pred 缓存沿用；BLIP2×MMKE-entity 为 284/636，必须标注低覆盖。每式独立全层 Tukey，κ=1，NumPy linear 分位数，同分浅层优先，边界值保留，有限零梯度层按历史标记 †。

## 版本说明

V08 = E[abs(c)×b]，不等于历史 abs(E[c])×E[b]；V07 = E[c×b]，不等于 E[c]×E[b]。V09 从 c×b×a 精确重算，不拿 E[dot] 冒充（cos 分母 epsilon 使二者并非数值恒等）。

同步只更新主文档 `OURS_VISUAL10_RESULTS_BEGIN/END` 标记之间的表格，保留其他章节；旧表折叠归档。旧全表生成器已添加保护，避免后续常规更新覆盖本次 10 式段落。

技能影响：定位分析契约用于聚合/覆盖/版本边界，双卡调度契约用于显存和锁核验，结果同步契约用于哈希验证后回填。本任务是定位分数补算，训练 checkpoint/正式评测样本数的合同不适用于这些定位产物。
