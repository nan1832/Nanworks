# 新会话服务器实验上下文与操作约束

> 用途：将本文件连同各阶段实验手册交给新的 AI。它必须先阅读本文件，再连接服务器核验实时状态。本文中的 Job、GPU 和进度仅是交接快照，不能替代实时查询。

## 1. 最高优先级原则

任何修改、启动、删除、重跑或本地回填之前，必须先通过 SSH 读取服务器上的真实进程、日志、结果标记和文件实体。

如果本地手册、旧聊天记录和服务器状态不一致：

1. 以服务器直接证据为准；
2. 先报告差异、可能原因和影响；
3. 未经确认不得自行猜测、补值、重跑、停止任务或删除数据。

不能只根据本地 Markdown 推测服务器实时进度。

## 2. 服务器连接方式

Windows 端应显式调用系统 OpenSSH：

```powershell
& "$env:WINDIR\System32\OpenSSH\ssh.exe" `
  -i "$HOME\.ssh\id_ed25519_bridge" `
  -o BatchMode=yes `
  -o ConnectTimeout=10 `
  bridge-server
```

`bridge-server` 连接登录节点 `login01`。登录后再连接计算节点：

```bash
ssh g07
ssh g08
```

不要假设任务仍在历史节点。每次都先查询：

```bash
squeue -j JOB_ID
scontrol show job -dd JOB_ID
sstat -j JOB_ID.batch
```

Job 到期、重排或重新申请后，Job ID、节点和 GPU 都可能改变。

## 3. 核心服务器目录

项目代码：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
```

正式共享结果根目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
```

计算节点临时目录：

```text
/tmp/ph_teacher3
```

`/tmp` 不能作为长期存储。完成评测后必须：

1. 仅保留 selected checkpoint；
2. 将正式产物同步到共享盘；
3. 对 selected checkpoint 做 SHA-256 核验；
4. 修正 `selected_checkpoint.tsv`、`train.done`、`eval_full.done` 中归档前的 `/tmp` 绝对路径；
5. 验证共享盘产物完整后，才可删除 `/tmp` 中的重复层目录与可重建 cache。

严禁直接清空整个 `/tmp/ph_teacher3`。

## 4. 三个数据集的真实路径与规模

### 4.1 EVQA-pilot500

```text
训练 JSON：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json

训练图像：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images

正式 eval JSON：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json

正式 eval 图像：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

预期数量：训练 500 条，正式 eval 2,093 条。

### 4.2 MMKE-visual

```text
训练 JSON：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json

正式 eval JSON：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_eval_evqa_compat.json

图像根目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
```

预期数量：训练 214 条，正式 eval 293 条。

### 4.3 MMKE-entity

```text
数据根目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data

训练 JSON：
vqa_mmke_entity_train_evqa_compat.json

正式 eval JSON：
vqa_mmke_entity_eval_evqa_compat.json

图像根目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
```

预期数量：训练 636 条，正式 eval 954 条。

训练成功后必须使用对应的独立 test/eval 数据评测，禁止使用训练集评测。

## 5. Python 环境与配置

普通模型常用 Python：

```text
/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
```

Qwen2.5-VL 专用环境：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
```

模型配置目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/configs/vead
```

Qwen 必须使用其专用环境，避免 processor、动态分辨率或依赖版本不一致。

部分 runner 的文件名或历史日志会出现 `blip2`，但它们可能是多模型通用 runner。不能仅凭脚本名或“loading BLIP2 train models”文字判断实际模型，必须同时核验：

- `--model-name`；
- `--config-path`；
- 完整进程命令行；
- 实际模型加载日志；
- 输出目录中的模型名。

## 6. 保持实验可比性的固定条件

未经用户明确批准，不得改变：

```text
epochs = 50
batch_size = 2
seed = 20260601
EMA alpha = 0.1
学习率
优化目标
Adapter 结构
训练集和正式 eval 集
```

checkpoint 选择规则：

```text
从 50 epoch 中选择 EMA loss 最小且数值有限的 checkpoint。
```

只改变显存调度时，例如：

- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`；
- 数据缓存在 CPU，仅将当前 batch 搬到 GPU；
- activation checkpointing；
- 同一份冻结基础模型顺序复用；

必须说明只改变显存调度，并核验样本顺序、前若干 step 的 loss 和原始实现一致。

不能未经批准直接减小 batch。减小 batch 会改变 optimizer step 次数和优化轨迹，不能自动视为与原实验完全可比。

## 7. 一个层的严格完成条件

一个层只有同时满足以下条件才算完成：

```text
train.done
selected_checkpoint.tsv
eval_full.done
非空的 eval_full/**/results.json
selected_checkpoint.tsv 指向的 checkpoint 实体真实存在
```

如果已归档到共享盘，还应有：

```text
SYNC_VERIFIED
```

只有 `train.done`、只有 checkpoint 或训练跑完 50 epoch 都不能算正式完成。

训练完成但没有 `eval_full.done` 的层，必须登记为“训练完成、尚未评测”。

## 8. 判断训练是否正常

进程存活不等于训练正常。检查时至少同时查询：

- `squeue`、`scontrol`、`sstat`；
- GPU显存、利用率和温度；
- GPU进程 PID 与完整命令行；
- launcher、训练、评测、watchdog的父子进程树；
- 最新日志更新时间；
- 当前数据集、模型和层；
- epoch/step 是否持续前进；
- 是否出现 OOM、nonfinite、NaN、Traceback、磁盘错误或无 selected checkpoint；
- `selected_checkpoint.tsv`、`eval_full.done`、结果文件和状态文件是否一致。

只有日志仍更新、epoch/step前进且GPU负载合理，才能判断训练正常。

等待显存时GPU利用率可以为0，但launcher日志必须持续输出显存探测记录；这种安全等待不能误报为卡死。

## 9. Watchdog与退出码

每层只有“代表训练或评测进度的日志连续2小时没有变化”才允许终止。

不能按以下条件停止：

- 总运行时间超过2小时；
- 进程运行时间很长；
- GPU短时间利用率为0%；
- 日志只有warning但实际epoch/step仍前进。

`rc=143` 是收到 SIGTERM 后的进程退出码，不是失败143次。

## 10. GPU进程归属与禁止操作

服务器可能多人共用同一个 Unix 账户。因此：

```text
进程用户名为 ph_teacher3，不代表一定是本项目或本人的任务。
```

判断归属必须结合：

- PID、PPID和父子进程树；
- 完整命令行；
- Slurm cgroup/step；
- 工作目录；
- 日志路径；
- launcher父进程。

严禁停止无法确认归属的 Jupyter kernel 或 GPU 进程。

未经用户确认，不得：

- `kill`、`kill -9` 或 `scancel`；
- 删除运行中目录；
- 覆盖共享盘正式结果；
- 自动重启失败任务；
- 修改候选层、训练参数或评测数据；
- 清理无法确认归属的数据。

发现问题时先报告原因、影响、可恢复checkpoint和修复建议。

## 11. Slurm GPU编号映射

`scontrol` 可能显示宿主机分配为 `GRES IDX:1`，但进入 Slurm step 后，程序因 `CUDA_VISIBLE_DEVICES` 重映射而显示为 GPU0。

每次应分别记录：

1. 宿主机物理GPU编号；
2. Slurm分配的GPU编号；
3. 进程内可见GPU编号。

不能只根据程序中的 `cuda:0` 判断宿主机物理GPU编号。

## 12. 正确启动实验

新实验应通过目标 Job 的 Slurm allocation 启动，例如：

```bash
srun --jobid=JOB_ID --overlap ...
```

不要只 SSH 到计算节点后直接后台运行，否则进程可能不属于目标 Slurm step。

启动前必须验证：

```bash
hostname
echo "$SLURM_JOB_ID"
echo "$CUDA_VISIBLE_DEVICES"
nvidia-smi
```

新任务必须使用独立结果目录和独立 lock。若已有 launcher 正在等待显存，新任务必须与其做互斥或阶段启动协调，禁止两个训练/评测进程同时抢占GPU。

不得为了启动本项目而停止其他现存任务。

## 13. checkpoint与cache清理规则

训练期间可以保留少量 Top-K 和 last checkpoint；正式评测完成后只保留 selected checkpoint。

删除前必须验证：

```bash
realpath selected_checkpoint
realpath layer_directory
```

确认selected位于当前层目录内部后，只删除同一个 `checkpoints` 目录下的非selected文件。

严禁：

- 根据文件名猜selected；
- 在没有完整评测前清理可恢复checkpoint；
- 删除尚需续训层的最近checkpoint；
- 对未经核验的拼接路径执行递归删除；
- 删除其他用户或其他项目的数据。

完成评测、共享盘同步与哈希核验后，应删除本层可重建cache和`/tmp`重复副本，保留必要日志、状态文件和正式共享归档。

## 14. 本地回填规则

本地总表：

```text
D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\md\Location\6location_7model_3datas_top_3_5_layers_outcome.md
```

Ours-Direct相关分析表：

```text
D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\md\Location\6location_formal7_OursDirect_main_correlation_analysis.md
```

每次回填前必须重新读取服务器的：

- `selected_checkpoint.tsv`；
- `eval_full.done`；
- `results.json`；
- 对应状态文件；
- selected checkpoint实体。

不得复制旧聊天内容或本地Markdown中的历史值冒充服务器结果。

回填时必须区分：

- main；
- stable；
- recovered；
- numeric anomaly；
- train-only；
- eval-complete；
- failed/nonconvergent。

PaliGemma L0等已确认不收敛的层应保留失败记录，不能填0分，也不能使用其他配置的最大值替代。

## 15. 已完成且不得重复运行的任务

截至 `2026-09-14 08:07 CST`，CMA-ModelPred 新Top-3引入的三个缺层已全部训练并完成独立正式评测：

| 数据集 × 模型 | 层 | Selected checkpoint | Eval数 | Average |
|---|---:|---|---:|---:|
| EVQA-pilot500 × SmolVLM | L5 | Epoch 42，EMA 0.428878 | 2,093 | 65.362 |
| MMKE-visual × SmolVLM | L5 | Epoch 49，EMA 0.448303 | 293 | 70.322 |
| EVQA-pilot500 × Qwen2.5-VL | L15 | Epoch 49，EMA 0.405599 | 2,093 | 62.396 |

共享归档：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_modelpred_top3_missing3_adapter_backfill_20260913_job3178423
```

三层均有：

```text
train.done
selected_checkpoint.tsv
eval_full.done
非空 results.json
SYNC_VERIFIED
共享盘 selected checkpoint 实体
```

共享盘每层只保留一个selected checkpoint，`/tmp`可重建cache已经清理。不要重复训练这三层。

21组CMA-ModelPred定位重算也已完成；除非用户明确要求，不得再次重算。

## 16. Job 3178423交接快照

以下是 `2026-09-14 08:07 CST` 的快照，操作前必须重新查询：

```text
Job：3178423
节点：g07
GPU：NVIDIA A800 80GB
GPU已用：31,913 MiB
GPU空闲：49,263 MiB
GPU利用率：0%
```

原任务：

```text
组合：MMKE-entity × LLaVA
当前层：L22
训练：已完成50 epoch
selected：Epoch 45，EMA 0.354578
正式eval：尚未开始
```

L22评测launcher要求至少 `56,320 MiB` 空闲显存，交接时还差约5.5 GiB。launcher仍在持续探测显存，属于安全等待，不是卡死。

不得从头重训L22。显存达到安全门槛后，应使用现有selected checkpoint完成正式评测。

L22完成正式评测后的原队列顺序：

```text
L24 → L1 → L9 → L7 → L0 → L2 → L13 → L11 → L12
```

## 17. 新AI每次操作前的最小核验清单

```text
[ ] 实际SSH连接服务器，而不是只读本地手册
[ ] squeue/scontrol/sstat确认Job、节点和剩余时间
[ ] nvidia-smi确认显存、利用率和GPU进程
[ ] 将GPU PID映射到完整命令行和父子进程树
[ ] 确认当前launcher、训练、评测和watchdog状态
[ ] 确认日志更新时间及epoch/step真实前进
[ ] 检查selected_checkpoint.tsv、eval_full.done和results.json
[ ] 核验训练与eval数据路径和样本数
[ ] 确认没有与其他训练/评测任务并发抢GPU
[ ] 任何kill、删除、重启、降batch或改配置前先请示
[ ] 完成层归档共享盘、核验哈希、清理非selected与可重建cache
[ ] 用服务器真实指标回填本地记录，并标注配置版本
```
