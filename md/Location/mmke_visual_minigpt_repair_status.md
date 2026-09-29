# MMKE-visual / MiniGPT-4-Vicuna-7B 补跑状态

更新时间：2026-07-12 09:53 CST

## 1. 补跑范围

本次记录的是 `MMKE-visual / MiniGPT-4-Vicuna-7B` 的补跑任务。

原始补跑队列共 8 层：

```text
L14,L5,L8,L0,L1,L3,L2,L29
```

当前等待重跑队列共 5 层：

```text
L0,L1,L3,L2,L29
```

## 2. 当前运行状态

当前补跑脚本已挂在 `job 3044208 / g09 GPU0`，但尚未启动新的训练，正在等待显存足够空闲。

等待条件：

```text
GPU_WAIT_MAX_USED_MIB=4096
```

当前 GPU0 状态：

```text
total = 81920 MiB
used  = 15185 MiB
free  = 65972 MiB
util  = 0%
```

虽然当前空闲显存约 64GB，但 MiniGPT 训练本身峰值约 64GB；GPU0 上仍有两个 Jupyter kernel 占用约 15GB，因此脚本会继续等待，避免再次 OOM。

当前等待日志：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/mmke_visual_minigpt_repair_20260711_162809_status.log
```

当前等待 CSV：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/mmke_visual_minigpt_repair_20260711_162809_layer_status.csv
```

## 3. 已完成并可用结果

已完成可用结果共 3 层：`L14,L5,L8`。

这些层均满足：

```text
train.done = 1
selected_checkpoint.tsv = 1
eval_full.done = 1
```

| Layer | 状态 | Ckpt Epoch | EMA Loss | 结果目录 |
|---|---|---:|---:|---|
| L14 | 已完成，已有结果并跳过重训 | 50 | 0.249512 | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/minigpt-4-vicuna-7b/layer_14` |
| L5 | 已完成，补跑训练和评测完成 | 35 | 0.281105 | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/minigpt-4-vicuna-7b/layer_05` |
| L8 | 已完成，补跑训练和评测完成 | 49 | 0.256176 | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/minigpt-4-vicuna-7b/layer_08` |

已完成层的 selected checkpoint 信息保存在各自目录下：

```text
layer_14/selected_checkpoint.tsv
layer_05/selected_checkpoint.tsv
layer_08/selected_checkpoint.tsv
```

已完成层的评测结果保存在各自目录下：

```text
layer_14/eval_full/
layer_05/eval_full/
layer_08/eval_full/
```

上一轮补跑状态 CSV：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/mmke_visual_minigpt_repair_20260710_135648_layer_status.csv
```

## 4. 未完成层与原因

未完成共 5 层：`L0,L1,L3,L2,L29`。

| Layer | 当前状态 | 是否有可用 selected checkpoint | 是否评测 | 未完成原因 |
|---|---|---:|---:|---|
| L0 | 训练失败，等待重跑 | 否 | 否 | 训练阶段 CUDA OOM，`train_rc=1`，未生成 `selected_checkpoint.tsv` |
| L1 | 训练失败，等待重跑 | 否 | 否 | 训练阶段 CUDA OOM，`train_rc=1`，未生成 `selected_checkpoint.tsv` |
| L3 | 训练失败，等待重跑 | 否 | 否 | 有中间 ckpt，但未完成 50 epoch；训练阶段 CUDA OOM，不能作为正式结果 |
| L2 | 训练失败/被保护性停止，等待重跑 | 否 | 否 | 训练阶段出现 CUDA OOM；随后已切换为显存等待模式，未生成正式结果 |
| L29 | 尚未开始本轮补跑 | 否 | 否 | 排在 L0/L1/L3/L2 之后；当前脚本仍在等待 GPU0 显存低于 4096 MiB |

注意：`L3` 虽然曾写过中间 checkpoint，例如到 epoch 7 左右，但由于未完成 50 epoch，也没有进入“从 50 epoch 中挑最小 EMA checkpoint”的流程，因此不能回填为正式结果。

## 5. 失败原因归纳

失败发生在训练阶段，不是评测阶段。

典型日志表现：

```text
CUDA out of memory
EVAL_NOT_RUN ... train_rc=1 selected_exists=0
```

根因是 GPU0 上存在额外 Jupyter kernel 占用显存，MiniGPT 训练峰值接近整卡容量，导致训练中分配几十 MiB 额外显存时 OOM。

当前 GPU0 仍被两个 Jupyter kernel 占用：

```text
PID 31810 约 10582 MiB
PID 509297 约 4582 MiB
```

## 6. 后续动作

当前脚本已设置为等待模式：

```text
LAYERS_CSV=0,1,3,2,29
GPU_WAIT_MAX_USED_MIB=4096
```

当 GPU0 已用显存低于 4096 MiB 后，会自动开始补跑：

```text
L0 -> L1 -> L3 -> L2 -> L29
```

如果需要立即补跑，应先确认并清理 GPU0 上两个非训练 Jupyter kernel；否则保持等待模式，避免继续产生 OOM 失败记录。

## 7. MiniGPT repair 启动命令

该命令用于在已分配的 `job 3044208 / g09 GPU0` 内启动 `MMKE-visual / MiniGPT-4-Vicuna-7B` 的补跑任务。它不会接续主 launcher 的后续模型，只负责 MiniGPT 剩余层。

补跑层：

```text
L0,L1,L3,L2,L29
```

推荐使用保守显存阈值，等 GPU0 已用显存低于 4096 MiB 后再启动训练：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

RUN_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644
LAUNCH_LOG="$RUN_ROOT/mmke_visual_minigpt_repair_wait4096_srun_$(date +%Y%m%d_%H%M%S).log"

nohup srun --jobid=3044208 --overlap --nodes=1 --ntasks=1 bash -lc \
'cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main && \
 env CUDA_VISIBLE_DEVICES=0 \
     GPU_ID=0 \
     GPU_WAIT_MAX_USED_MIB=4096 \
     LAYERS_CSV=0,1,3,2,29 \
     PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
     bash /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/launch_mmke_visual_minigpt_repair_g08.sh' \
> "$LAUNCH_LOG" 2>&1 &
```

当前实际已启动的等待任务：

```text
srun PID: 544957
status: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/mmke_visual_minigpt_repair_20260711_162809_status.log
csv:    /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/mmke_visual_minigpt_repair_20260711_162809_layer_status.csv
```

如果未来要重启，应先确认没有旧的 `launch_mmke_visual_minigpt_repair_g08.sh` / `srun --jobid=3044208` repair 进程仍在等待，避免重复补跑。

## 8. 主 launcher 后续模型判断

原始 `MMKE-visual` 主 launcher 是：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/launch_mmke_visual_3p4_pending_epoch50_job3044208.sh
```

主 launcher 原计划顺序：

```text
BLIP2 -> InstructBLIP -> MiniGPT -> Qwen2.5-VL -> PaliGemma -> SmolVLM -> LLaVA
```

当前已确认：

```text
BLIP2-OPT-2.7B: 10/10 done
InstructBLIP-Vicuna-7B: 12/12 done
MiniGPT-4-Vicuna-7B: 4/9 done，剩余 L0,L1,L3,L2,L29 等待 repair
Qwen2.5-VL-3B: 0/21 done
PaliGemma-3B: 0/8 done
SmolVLM-Instruct-1.7B: 0/10 done
LLaVA-v1.5-7B: 0/15 done
```

当前 GPU0 约有 65GB 空闲，但 MiniGPT 训练峰值接近 64GB，叠加两个 Jupyter kernel 后不稳定，因此 MiniGPT 不应在当前显存状态下继续硬跑。

在当前约 65GB 可用显存下，主 launcher 后续更适合先跑显存压力较低的模型：

```text
PaliGemma-3B
SmolVLM-Instruct-1.7B
Qwen2.5-VL-3B
```

`LLaVA-v1.5-7B` 也可能可跑，但按实验手册和原计划应排最后，因为它最慢；如果继续主队列，建议仍保持 `LLaVA-v1.5-7B` 最后。
