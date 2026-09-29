# 7 Models x 3 Datasets Epoch50 真实扫层训练手册

本文档用于指导 `7 models x 3 datasets` 的真实编辑扫层训练与评测。候选层由候选层定位方法给出，本手册只规定这些候选层进入真实训练后如何执行、如何选 checkpoint、如何评测、如何恢复故障，以及如何避免服务器上已经出现过的问题。

## 1. 适用范围

本手册适用于以下真实扫层任务：

1. 对 `EVQA-pilot500`、`MMKE-visual`、`MMKE-entity` 三个数据集。
2. 对 7 个模型：
   - `BLIP2-OPT-2.7B`
   - `InstructBLIP-Vicuna-7B`
   - `MiniGPT-4-Vicuna-7B`
   - `LLaVA-v1.5-7B`
   - `Qwen2.5-VL-3B`
   - `PaliGemma-3B`
   - `SmolVLM-Instruct-1.7B`
3. 对候选层并集中的每一层，训练 visual-only edit adapter / VEAD adapter `50 epoch`。
4. 每层训练完成后，按 minimum EMA loss 选择 checkpoint，再做 full eval/test 评测。

不适用范围：

- 不用于重新计算候选层分数。
- 不用于 SaLEM、LGA、Ours、CMA、Perturb-KL 等候选层公式实现。
- 不用于 no-edit baseline。

## 2. 权威输入与输出

### 2.1 候选层输入

待训练层以：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

中的以下小节为准：

- `## 3. 数据集分表`：8 方法 Top-3 并集。
- `### 3.4 待补跑层分表（第 3 节减第 4 节已完成）`：当前还需要补跑的真实训练层。

执行时优先跑 `3.4`。如果某层已经有 `train.done + selected_checkpoint.tsv + eval_full.done`，默认跳过，不重复训练。

### 2.2 真实结果回填

真实训练与评测结果回填到：

```text
md/Location/6location_7model_3datas_top_3_5_layers_outcome.md
```

中的：

```text
## 4. 已完成真实扫层结果回填
```

回填口径必须满足：

1. 同层目录存在 `train.done`。
2. 同层目录存在 `selected_checkpoint.tsv`。
3. 同层目录存在 `eval_full.done`。
4. `eval_full.done` 中 `status=EVAL_DONE`。
5. checkpoint 是该层 50 epoch 内 minimum EMA loss 的 checkpoint。

只训练未评测、只评测未写 `eval_full.done`、或训练中断的层，不能计入第 4 节已完成结果。

## 3. 数据与样本口径

| Dataset | 训练 split | 评测 split / 样本数口径 | 当前已见 eval samples | 说明 |
|---|---|---|---:|---|
| `EVQA-pilot500` | `vqa_train_proxy500.json` | full E-VQA eval/test | 2093 | 训练 500 条 proxy；评测用 full eval/test。 |
| `MMKE-visual` | `visual_train.json` | MMKE visual full eval/test | 293 | 以 `eval_full.done.eval_samples` 为准。 |
| `MMKE-entity` | `entity_train.json` | MMKE entity full eval/test | 954 | 以 `eval_full.done.eval_samples` 为准。 |

注意：

- 训练样本数和评测样本数不一定相同。
- 表格中的当前样本数来自现有服务器结果；后续若数据版本更新，以 `eval_full.done` 中实际 `eval_samples` 为准。
- 所有结果必须记录 train/eval 数据路径，避免混用 train/eval split。

## 4. 统一训练配置

| 项目 | 统一设置 |
|---|---|
| adapter | visual-only VisEdit / VEAD adapter |
| epoch | 每层 50 epoch |
| batch size | 默认沿用现有脚本，多数为 `2` |
| checkpoint 选择 | 每层 minimum EMA loss |
| 评测方式 | 选中 checkpoint 后做 full eval/test |
| 结果指标 | `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average` |
| 成功标记 | `train.done + selected_checkpoint.tsv + eval_full.done` |
| 完成后清理 | 正式评测验收通过后，仅保留 selected checkpoint 和必要结果文件；立即删除非 selected checkpoint 与可再生成 cache |

每层都必须独立记录：

- `dataset`
- `model`
- `layer`
- `run_root`
- `job_id`
- `node`
- `CUDA_VISIBLE_DEVICES`
- `train_json`
- `train_img_root`
- `eval_json`
- `eval_img_root`
- `ckpt_epoch`
- `raw_loss`
- `ema_loss`
- `eval_samples`

## 5. 推荐目录结构

每个 run root 推荐结构如下：

```text
server_results/<run_name>/
  <dataset>/
    <model>/
      layer_<L>/
        loss_history.csv
        selected_checkpoint.tsv
        train.done
        eval_full.done
        records/
        eval_full/
        logs/
```

其中：

- `loss_history.csv`：记录每个 epoch / step 的 raw loss 与 EMA loss。
- `selected_checkpoint.tsv`：训练后由脚本扫描 checkpoints，选 minimum EMA loss。
- `train.done`：训练 50 epoch 完成后写入。
- `eval_full.done`：full eval 完成后写入，必须包含 `EVAL_DONE` 和五项指标。

## 6. 启动前检查

启动任何真实训练前，先完成以下检查。

### 6.1 GPU 与 Slurm 检查

必须确认：

1. 当前 job 已经分配 GPU。
2. `CUDA_VISIBLE_DEVICES` 只暴露本任务要使用的一张卡。
3. 该卡上没有其他训练 / 候选层计算进程。
4. 不挤占正在跑的 Ours、CMA、LGA、SaLEM、epoch50 训练任务。

建议检查命令：

```bash
squeue -u $USER
scontrol show job <job_id>
nvidia-smi
ps -fu $USER | grep -E "run_evqa|visedit|resume|sweep|train|eval" | grep -v grep
```

如果 GPU util 为 0 但 Slurm job 还在，要进一步查进程是否已经退出，不能只看 job 存在就认为训练还在跑。

### 6.2 断点检查

对每个待跑层，按顺序检查：

```text
layer_<L>/train.done
layer_<L>/selected_checkpoint.tsv
layer_<L>/eval_full.done
```

处理规则：

| 状态 | 操作 |
|---|---|
| 三个文件都存在且 `EVAL_DONE` | 跳过 |
| 有 `train.done`，无 `selected_checkpoint.tsv` | 重新选 checkpoint |
| 有 `selected_checkpoint.tsv`，无 `eval_full.done` | 只补评测 |
| 训练未满 50 epoch | 从该层恢复或重跑该层 |
| 目录有 lock 但无活进程 | 人工核查后删除 stale lock |

### 6.3 全量扫层调度规则

做全量真实扫层之前，必须先完成模型可用性检查和 smoke test，不能直接把 7 模型 x 3 数据集全量队列丢到 GPU 上。

启动顺序：

1. 模型可用性检查：逐个模型确认能加载、能构造 processor/tokenizer、能读入一条对应数据集样本、能完成一次 teacher-forcing forward。
2. Hook / adapter smoke test：每个模型至少选一个轻量样本和一个合法层，确认 adapter 能挂到目标 decoder block，训练 step 能反传，loss_history 能写出。
3. Eval smoke test：用一个小样本 eval，确认 checkpoint 加载、hook 绑定、指标输出和 `eval_full.done` 写入逻辑可用。
4. 通过 smoke test 后再进入全量扫层。

全量训练调度：

| 可用 GPU 数 | 调度规则 |
|---:|---|
| 2 张卡 | 一张卡跑 `MMKE-entity` 在各模型的并集层实验；另一张卡跑 `MMKE-visual` 在各模型的并集层实验。`EVQA-pilot500` 暂不抢占，等前两者任一数据集队列完成后，接到先空出来的那张卡上继续跑。 |
| 1 张卡 | 串行跑三个数据集，不并发；推荐顺序为 `MMKE-entity -> MMKE-visual -> EVQA-pilot500`，也可以按当前论文优先级调整，但必须在日志中记录。 |
| 0 张空闲卡 | 不启动训练，只做结果整理、断点统计或脚本检查。 |

模型训练顺序：

1. 所有数据集内部的模型顺序必须把 `LLaVA-v1.5-7B` 排在最后，因为它当前观测最慢。
2. 推荐顺序：

```text
BLIP2-OPT-2.7B
InstructBLIP-Vicuna-7B
MiniGPT-4-Vicuna-7B
Qwen2.5-VL-3B
PaliGemma-3B
SmolVLM-Instruct-1.7B
LLaVA-v1.5-7B
```

3. 如果某模型存在已知环境或数值问题，可以先做该模型单层 smoke，不通过则暂停该模型，不阻塞其他模型继续。
4. 同一张物理 GPU 同时只能跑一个 epoch50 真实训练队列；不要把候选层计算任务和 epoch50 训练叠在同一卡上。

## 7. 正式训练流程

每个 `dataset x model x layer` 按以下流程执行。

### 7.1 单层训练

1. 创建 layer run 目录。
2. 启动独立 Python 进程。
3. 重新加载 base model。
4. 只初始化当前层 adapter。
5. 训练 50 epoch。
6. 写 `loss_history.csv`。
7. 写 `train.done`。

重点：每层必须是独立进程或等价的全量重新初始化流程。不要在同一个 Python 进程中复用旧 model wrapper 直接切到下一层。

### 7.2 Checkpoint 选择

训练完成后扫描该层所有 checkpoint：

```text
epoch-*-i-*-ema_loss-*
```

选择 EMA loss 最小的 checkpoint，写入：

```text
selected_checkpoint.tsv
```

字段至少包括：

```text
layer status epoch i loss ema_loss checkpoint
```

若 EMA loss 出现非有限值、负值、异常极大/极小值，需要写入 warning，不允许静默当作正常收敛。

### 7.3 Full eval

用 `selected_checkpoint.tsv` 指向的 checkpoint 做 full eval/test：

1. 启动独立 Python 进程。
2. 重新加载 base model。
3. 加载当前层 adapter checkpoint。
4. 重新注册当前层 hook/wrapper。
5. 评测 full eval/test。
6. 写 `eval_full.done`。

`eval_full.done` 必须包含：

```json
{
  "layer": 16,
  "status": "EVAL_DONE",
  "eval_samples": 2093,
  "ckpt_epoch": "50",
  "ckpt_loss": "...",
  "ckpt_ema_loss": "...",
  "Rel": 0.0,
  "T-Gen": 0.0,
  "M-Gen": 0.0,
  "T-Loc": 0.0,
  "M-Loc": 0.0,
  "Average": 0.0
}
```

## 8. 已知问题与处理规则

### 8.1 BLIP2 / VEAD wrapper stale 问题

历史问题：

- 顺序扫层时复用同一个 Python 进程和同一个 model wrapper。
- `VEAD.init_wrap_get_llm_outpt()` 只在第一次 editor 创建时 wrap。
- 后续层虽然 adapter key 正确，但 wrapper 闭包仍绑定首个 editor，导致新层 adapter 没有正确收到 `vt_range / inpt_has_img`。
- 表现为多层 loss 高位震荡，评测结果异常接近。

处理规则：

1. 每层训练使用独立 Python 进程，或强制 unwrap 后重新 bind 当前 editor。
2. `visual adapter forward` 缺少 `vt_range` 时必须直接报错。
3. 评测也必须每层独立进程，重新 load base model 和当前 checkpoint。
4. 如果多个层结果高度一致，优先排查 stale wrapper / stale checkpoint，而不是解释为模型现象。

### 8.2 Eval stale checkpoint 问题

风险：

- 评测进程复用旧 checkpoint。
- layer hook 未重新绑定。
- 评测日志显示当前层，但实际 adapter 仍是上一层。

处理规则：

1. eval 前打印 checkpoint path。
2. eval 前打印 adapter key / layer id。
3. eval 前打印 hook path。
4. 每层 eval 结束释放模型。
5. `eval_full.done` 写入完整 checkpoint path，便于复核。

### 8.3 PaliGemma 数值不稳定问题

历史现象：

- EVQA-pilot500 的 PaliGemma 多层不是“越训越好”。
- 部分层 early checkpoint 最优，例如 epoch 1 / epoch 2。
- 出现负 EMA loss、非有限梯度、CUDA stall、loss 越训越大。
- `L9` 曾出现训练卡住后用 early checkpoint 恢复评测。

处理规则：

1. PaliGemma 结果可以先按统一配置登记，但必须在 status 或备注中写 warning。
2. 如果出现负 EMA、NaN、Inf、CUDA stall，标记为 `DONE_WITH_WARNING` 或 `TRAIN_RECOVERED_FROM_STALL`。
3. 不要把 PaliGemma 的 early checkpoint 误解释为代码一定选错；先看完整 loss 曲线。
4. 后续稳定重跑建议单独成组，不混入主队列：
   - 降低 LR。
   - 加 grad clip。
   - nonfinite step 直接 skip。
   - 禁止负 EMA checkpoint 进入主结果。

### 8.4 Qwen2.5-VL 环境问题

历史问题：

- 旧通用环境无法导入 `Qwen2_5_VLForConditionalGeneration`。
- 在候选层计算中表现为 `rc=1` 或没有真正开始跑。
- Ours / SaLEM / Perturb-KL 都曾遇到 Qwen 环境或 coverage 问题。

真实训练前必须检查：

```bash
python - <<'PY'
from transformers import Qwen2_5_VLForConditionalGeneration
print("qwen25vl import ok")
PY
```

处理规则：

1. Qwen2.5-VL 必须使用能通过 import 测试的专用环境。
2. 记录实际 `python`、`transformers` 版本和环境路径。
3. 如果是 Qwen 的真实训练断掉，先排查环境，不要直接判定为数据或层问题。
4. 对 Qwen 的 prompt template、processor、image input 也要单独记录。

### 8.5 Slurm 取消 / job 过期

历史现象：

- Slurm step 被 cancel 或过期。
- job 还在，但 GPU 显示 1 MiB / 0% util，没有训练进程。
- 训练层停在中间 epoch，例如某层只跑到 epoch 7 或 epoch 29。

处理规则：

1. 每次查询进度要同时看 `squeue/sacct`、`nvidia-smi`、`ps` 和日志最后时间。
2. 如果 step 被 cancel，当前层不能计入完成。
3. 从最后未完成层恢复，而不是从队列头重跑所有层。
4. 恢复前保护现场：保留原日志、loss history、partial checkpoints。

### 8.6 Lock / skipdone 问题

历史现象：

- 后续队列因为已有 lock 跳过某些层。
- 实际该层没有 `eval_full.done`。

处理规则：

1. `skipdone` 只以 `train.done + selected_checkpoint.tsv + eval_full.done` 为完成标准。
2. 单独存在 lock 不能视为完成。
3. 若 lock 对应进程不存在，记录后再清理。
4. 清理 lock 前必须确认没有同层训练进程。

### 8.7 显存 / 内存压力

风险：

- 同卡叠加多个训练或候选层计算导致 OOM。
- 系统内存接近满时，训练进程可能被系统或 Slurm 杀掉。
- 清理缓存可能误删仍需 resume 的 checkpoint。

处理规则：

1. 同一张物理 GPU 同时只跑一个 epoch50 训练任务。
2. 清理前先列出路径、大小、用途、是否可恢复，并请示。
3. 不删除以下文件：
   - `loss_history.csv`
   - `selected_checkpoint.tsv`
   - `train.done`
   - `eval_full.done`
   - 当前层最新 checkpoint
   - minimum EMA checkpoint
4. 可考虑清理：
   - 明确废弃 run 的中间 checkpoint。
   - 已压缩备份后的旧日志。
   - 候选层计算临时缓存。

## 9. 恢复策略

### 9.1 恢复优先级

1. 已训练完但未评测：优先补 eval。
2. 已训练到中间 epoch：继续该层，或重跑该层。
3. 已完成层：跳过。
4. PaliGemma 异常层：不要混入主恢复队列，进入 stable rerun 待办。

### 9.2 恢复记录

每次恢复必须写入 run log：

```text
resume_time
job_id
node
gpu_id
run_root
dataset
model
layer
resume_from_epoch
reason
next_layers
```

### 9.3 中断后最小验收

恢复完成后，对当前层检查：

```bash
test -f layer_<L>/train.done
test -f layer_<L>/selected_checkpoint.tsv
test -f layer_<L>/eval_full.done
grep EVAL_DONE layer_<L>/eval_full.done
```

## 10. 回填格式

第 4 节主表字段：

```text
Model
Layer
Ckpt Epoch
Raw Loss
EMA Loss
Samples
Rel
T-Gen
M-Gen
T-Loc
M-Loc
Average
Train Status
```

`Train Status` 建议值：

| Status | 含义 |
|---|---|
| `TRAIN_DONE` | 50 epoch 完成，checkpoint 与 eval 正常 |
| `TRAIN_DONE_WITH_WARNING` | 训练完成但存在数值/收敛 warning |
| `TRAIN_RECOVERED_FROM_STALL` | 曾卡住或中断，使用可验证 checkpoint 恢复评测 |
| `TRAIN_PARTIAL` | 训练未满 50 epoch，不回填主表 |
| `EVAL_PENDING` | 训练完成但 eval 未完成，不回填主表 |
| `FAILED` | 明确失败，不回填主表，仅写问题记录 |

## 11. 每轮执行清单

启动前：

- [ ] 当前 job 和 GPU 已确认。
- [ ] 没有挤占其他训练任务。
- [ ] 待跑层来自 `3.4 待补跑层分表`。
- [ ] 已完成层按 `eval_full.done` 跳过。
- [ ] 已完成模型可用性检查、adapter smoke test、eval smoke test。
- [ ] 已按 2 卡 / 1 卡规则确定数据集队列；`LLaVA-v1.5-7B` 排在每个数据集模型队列最后。
- [ ] Qwen 环境 import 检查通过。
- [ ] PaliGemma 是否进入 stable rerun 已明确。

训练中：

- [ ] 每层独立进程。
- [ ] 日志持续更新。
- [ ] loss_history 正常写入。
- [ ] 无 stale wrapper / stale checkpoint。
- [ ] GPU util 和显存符合预期。

训练后：

- [ ] `train.done` 已写。
- [ ] `selected_checkpoint.tsv` 指向 minimum EMA checkpoint。
- [ ] `eval_full.done` 为 `EVAL_DONE`。
- [ ] eval samples 与该数据集口径一致。
- [ ] 结果回填第 4 节。
- [ ] selected checkpoint 实体文件存在，且与 `selected_checkpoint.tsv` 一致。
- [ ] 保留 `train.done`、`selected_checkpoint.tsv`、`eval_full.done`、完整评测结果、`loss_history.csv`、运行配置、日志和状态文件。
- [ ] 正式评测验收通过后，删除该完成层的全部非 selected checkpoint 和可重新生成的预处理 cache，并记录删除文件数与释放空间。
- [ ] 若失败，失败原因写入对应方法或训练问题记录。

### 11.1 训练完成后的强制清理规则

该规则适用于此后所有真实扫层训练任务，清理的是磁盘存储，不改变 epoch、batch size、学习率、seed、优化目标或评测口径。

1. 每层必须完成 50 epoch，再按 minimum EMA loss 选择唯一的正式 checkpoint。
2. 必须使用该数据集对应的独立 test/eval 数据完成正式评测；禁止使用训练集代替评测集。
3. 只有同时满足以下条件，才允许清理该层训练产物：
   - `train.done` 存在；
   - 非空 `selected_checkpoint.tsv` 存在；
   - TSV 指向的 selected checkpoint 实体存在；
   - `eval_full.done` 存在且状态为 `EVAL_DONE`；
   - 完整评测结果存在、非空，评测样本数与数据集口径一致。
4. 验收通过后立即删除：
   - 除 selected checkpoint 以外的所有 epoch checkpoint；
   - 可以从原始数据重新生成的训练预处理 cache；
   - 已被正式运行替代、且不再承担故障诊断用途的 smoke/速度验证 cache。
5. 必须保留：
   - selected checkpoint 实体；
   - `train.done`、`selected_checkpoint.tsv`、`eval_full.done`；
   - 完整评测结果及逐层指标；
   - `loss_history.csv`、运行配置、训练/评测日志、状态文件；
   - 清理审计清单，包括删除路径、文件数量和释放字节数。
6. 以下情况禁止按完成层清理：训练未满 50 epoch、评测未完成、没有 selected checkpoint、结果不完整、等待续训、OOM/卡住/nonfinite 调查未结束。此类层至少保留最近一个有效恢复 checkpoint、失败日志和现场状态，直至明确记录失败或完成补跑。
7. 删除前必须确认没有活跃进程引用目标路径，解析后的路径位于当前实验根目录，且所有候选文件属于本项目用户；不得删除输入训练/评测数据、基础模型权重、其他任务目录或其他用户文件。

## 12. 和候选层方法的关系

候选层方法只决定“哪些层值得训练”。真实扫层训练不因候选层方法不同而改变训练配置。

同一个层如果被多个候选方法命中，只训练一次；后续在方法比较时复用该层真实评测结果。

因此：

- `Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct`、`CMA-Direct` 的候选层进入同一个真实训练池。
- `Perturb-KL-Pre-AltSeq` 若作为消融方法，也只贡献额外候选层；训练流程不变。
- 第 4 节真实结果是所有方法共享的评测事实表。
