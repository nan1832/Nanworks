# Tukey Top-3：双卡补12层，LLaVA显式暂停

## 授权与版本边界

2026-09-26用户确认执行双卡方案：暂停g08的EVQA/LLaVA L4及其自动续跑器；g09前三层不打断；不执行MMKE-entity/LLaVA L7/L8。原14层追加队列被本12层分工取代，但原计划和历史结果保留。12层完成后不自动恢复任何LLaVA任务。

本记录不是完成结果表。部署脚本、原始只读快照、checkpoint元数据及部署清单在本地`outputs/tukey_two_gpu_20260926/`。

## 作业、队列及调度

| 卡 / 作业 | 顺序 | 新补层数 |
|---|---|---:|
| g08 / 3435286 / GPU0 | MMKE-visual × Qwen2.5-VL L3 → L10 | 2 |
| 同上 | EVQA-pilot500 × Qwen2.5-VL L10 → L6 | 2 |
| 同上 | MMKE-entity × Qwen2.5-VL L6 → L3 → L10 | 3 |
| 同上，条件执行 | EVQA-pilot500 × InstructBLIP L17 → L20 | 2 |
| 同上，队尾 | EVQA-pilot500 × PaliGemma L0，恢复Epoch30至总50轮 | 1 |
| g09 / 3443209 / GPU0 | 等前三层全部通过验收后，MMKE-entity × MiniGPT-4 L7 → L8 | 2 |

前三层指MMKE-visual/InstructBLIP L20、MMKE-entity/InstructBLIP L20、MMKE-entity/SmolVLM L8。新控制器等待它们的原GPU锁释放，并验证ALL_THREE_DONE、状态、50轮历史、最低有限EMA、正式293/954/954条eval及归档哈希，不能只看父PID消失。

### InstructBLIP显存回退

本次未取得EVQA/InstructBLIP同协议的可靠独立峰值记录，不借用其他组合的显存值保证安全。g08执行到该组合时，若空闲不足77824 MiB（76 GiB）或出现非基线进程，则**整组L17/L20委派g09**，在MiniGPT-4之后执行；g08继续PaliGemma队尾。决策写`instruct_assignment.json`。76 GiB是保守启动门槛，不是实测峰值。

因此初始分工10+2可变成8+4；组合内不拆卡，12个唯一任务不增加不遗漏。g09做完MiniGPT-4后若尚未有该决策，会不占GPU地等待。

其他模型沿用训练73728 MiB、评测56320 MiB门槛，连续3次检查。g08只允许部署时已存在的两个进程在基线内继续存在：PID3407196（1422 MiB）、4145588（5872 MiB），校验PID启动时钟和命令哈希，每个进程允许256 MiB波动；不停止这些进程。新的未知进程、显存不足会导致等待。g09默认要求没有其他GPU进程。

## LLaVA L4保存现场

- 原Job3435286、g08；原训练PID4079818、续跑器PID4045244，二者归属step37。
- 2026-09-26 22:19前保存checkpoint及配置/恢复命令等；22:20:31复核为`PAUSED_VERIFIED`。
- 最新与最低有限EMA均为Epoch38，optimizer step9500，EMA`0.48435375847355844`，optimizer包含26项状态。
- 已经开始但未保存的Epoch39部分进度不在checkpoint中；以后从Epoch39、step9501重新继续，不声称保存了中间batch或未记录的RNG状态。
- 第一次停止后立即检查遇到procfs退出竞争（状态与cmdline读取之间进程退出），后续确认两个PID均不存在，并重新核验备份哈希；不能将该检查异常误记为训练失败或未暂停。
- 旧自动续跑目录有`CANCEL_AUTO_RESUME`和明确暂停状态，原源代码未修改。

共享恢复清单：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/llava_L4_pause/resume_manifest.json
```

该文件含原checkpoint、备份checkpoint、文件SHA-256、原配置与runner快照、完整恢复命令。原训练输出在：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_llava_job3435286_20260924/resume_after_eval955_20260926/run/evqa-pilot500/llava-v1.5-7b/layer_04
```

恢复必须得到用户新指令，先检查Job、显存、互斥锁和当前12层任务。清单中的训练命令带`--skip-eval`，所以训练50轮后仍需单独进行2093条正式评测；不要误认为旧续跑器会自动完成该评测。

## 控制路径与输出路径

新双卡控制根：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926
```

- `control/two_gpu_queue.py`：双卡控制；`deployment.json`：授权、12层集合、原控制器/计划哈希、门槛。
- `control/g08/`、`control/g09/`：各自的`launch.json`、`controller.log`、`status.json`、`DONE.json`。
- 登录节点srun PID分别为2473219、2473226；节点控制器最初PID为g08的25601、g09的1903963。查询时重新核验，不盲信历史PID。
- `old_tail_backup/`保存被替换的原计划、控制器、状态和停止记录。旧等待器1886572已退出，原priority3控制器1871816及训练子进程未停止。
- 两卡使用`server_results/gpu_locks/g08_gpu0.lock`和`g09_gpu0.lock`，另有逐组合claim锁。
- `ALL_12_DONE.json`仅在两卡结束且12层逐一通过完整评测验证后产生，不仅凭进程退出。

复用原已冻结的共享工作/归档根（目录名中的3443209只是创建来源，不代表所有任务仍在g09）：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_tail_job3443209_20260926/work
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_tail_job3443209_20260926/accepted
```

训练checkpoint、正式结果和恢复点直接位于共享盘。缓存软链接指向各执行节点独立的`/tmp/ph_teacher3/tukey_top3_tail_job3443209_20260926`；同名节点路径不是共享目录。缓存可重建，不作为恢复的唯一数据源。

## 协议与自动验收

保留原冻结plan及代码/配置/数据哈希，每阶段复查。50轮、batch2、原lr1e-4、seed参数20260601及原seed+layer规则、EMA alpha0.1；各模型原Adapter/IT结构、训练目标、预处理参数、activation checkpointing等不改变。不同模型原生设置不强行统一。

选点覆盖完整历史的最低有限EMA。EVQA独立2093、MMKE-visual293、MMKE-entity954条eval。每层验证训练历史、selected文件、物理checkpoint、正式eval标记及完整results，然后共享盘归档并校验，再按精确清单清理该层非选中checkpoint。暂停的LLaVA、原Pali诊断以及其他实验不在清理范围内。

Pali沿用旧计划已核验的Epoch30恢复点及旧30轮loss历史，继续到50轮；历史Epoch2诊断不充当正式50轮结果。若OOM/nonfinite/写盘等导致阶段失败，则停该卡队列留证，不自动换stable、降学习率、改batch或从头重试。

剩余作业时间不足24小时不开始新阶段；子进程日志两小时不前进会停止该控制器自己启动的阶段并报错，不影响其他进程。

## 部署进度及两次实测

22:21:54新g09等待器等待原priority3的GPU锁；22:22:19 g08通过第2次训练门槛检查（空闲73865 MiB，门槛73728 MiB，非预期PID为空）。此时仅能称队列部署成功，不能提前称首层训练已推进。

22:22:39 g08首项MMKE-visual × Qwen L3启动，训练PID25908。完成模型加载及214条预处理后，22:26:30达到Epoch1、64/214；22:27:16达到Epoch2、36/214，证明真实训练持续推进。后一次训练进程显存26250 MiB、其他两个进程合计7294 MiB；整卡已用33566 MiB、空闲47609 MiB、利用率90%。

g09原MMKE-entity × InstructBLIP L20在22:25:51为Epoch3、254/636，22:27:16为348/636；显存71402 MiB，整卡空闲9745 MiB、利用率99%。新等待器正常等待前序GPU锁，不占GPU显存。两条活动训练的最近日志未见OOM、nonfinite、Traceback、磁盘配额/空间错误；这不是对未来运行的保证。

本次仅完成部署、暂停保存与首层启动验证，12层尚未完成。正式结果回填须在各层验收后另行核验。
