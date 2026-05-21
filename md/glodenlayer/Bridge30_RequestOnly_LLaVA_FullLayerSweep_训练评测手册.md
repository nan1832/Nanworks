# Bridge30 Request-Only LLaVA Full Layer Sweep 训练评测手册

## 1. 实验目标

本实验用于检验在 Bridge30 request-only 训练数据下，Adapter 挂载到 LLaVA 不同视觉表征层时的效果差异。

核心约束：

- 原始 `jsonl` 不改动。
- 训练数据只使用 `request`，不使用 `generality/locality` 作为训练样本。
- IT 模块保持与之前配置一致；本实验控制的是视觉表征不同位置的编辑强度。
- 所有层先完成训练并选定 checkpoint，再统一评测。

## 2. 服务器路径

```text
服务器节点：g07
项目目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
输出目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava
```

模型配置目录：

```text
LLaVA: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
BLIP2: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b
```

request-only 数据：

```text
train_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json

val_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json

val_full:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_full_metrics.json
```

LLaVA 扫层配置：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/llava/llava-v1.5-7b-bridge-request-only-l{L}.yaml
```

## 3. 训练规则

每层先训练 `100` 轮，`batch_size=1`，每轮结束保存一次 checkpoint：

```text
save_ckpt_per_i = 30
```

统一评测 checkpoint 的目标训练损失：

```text
ema_loss = 0.0003
```

选择规则：

1. 优先选择文件名中 `ema_loss-0.0003` 的 checkpoint。
2. 如果没有完全等于 `0.0003`，选择与 `0.0003` 最接近的 checkpoint。
3. 可接受范围为 `abs(ema_loss - 0.0003) <= 0.0001`，即 `0.0002-0.0004`。
4. 如果 `100` 轮内没有可接受 checkpoint，则从最新 checkpoint 继续训练 `20` 轮。
5. 之后每次仍按 `20` 轮递增，直到出现可接受 checkpoint。
6. 若单层长期不收敛，可人工设定上限并标记为 `MISS_TARGET`，选现存最接近 checkpoint 继续后续流程。

特殊记录：

- `layer30` 到 `700` epoch 仍未达到目标，标记为 `MISS_TARGET`，选中 `epoch-661-i-19830-ema_loss-0.0016`。
- `layer31` 训练到 700+ epoch 后仍未低于 `3.x`，标记为 `MISS_TARGET`，选中 `epoch-658-i-19740-ema_loss-3.2771`。

## 4. 训练命令

完整补训默认从 `layer2` 到 `layer31`：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava

nohup bash scripts/run_llava_request_only_remaining_layers_target_loss.sh \
  > "$OUT/full_layer_target0003_sweep.log" 2>&1 &
```

只补指定层：

```bash
LAYERS="30 31" FORCE_SELECT_AT_EPOCHS="30:700" \
  bash scripts/run_llava_request_only_remaining_layers_target_loss.sh
```

## 5. 统一评测

所有层都有 `selected_checkpoint.tsv` 后统一评测：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

bash scripts/eval_llava_request_only_selected_layers.sh
```

评测 split：

```text
train_request
val_request
val_full
```

评测输出：

```text
$OUT/eval/selected_eval_summary.tsv
$OUT/eval/{split}/layer_{L}/vead/llava-v1.5-7b/{split}_l{L}_target0003/single_edit/mean_results.json
```

本次评测曾因脚本末尾 CRLF 残留在完成后被 wrapper 误标为 FAILED；经核验：

```text
selected_eval_summary.tsv = 97 行
train_request manifests = 32/32
val_request manifests = 32/32
val_full manifests = 32/32
mean_results.json = 96/96
```

因此已手动修正完成标记为：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/FULL_LAYER_TARGET0003_DONE.txt
```

## 6. 监控与磁盘保护

查看训练或评测进程：

```bash
pgrep -af 'bridge_train_request_only.py|eval_bridge_request_only_ckpt.py'
```

查看训练总日志：

```bash
tail -f /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/full_layer_target0003_sweep.log
```

查看评测日志：

```bash
tail -f /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/full_layer_target0003_eval.log
```

磁盘/配额保护：

1. 每层命中 selected checkpoint 后，自动删除该层其余中间 checkpoint。
2. 如果训练因 checkpoint 写入失败、No space left on device、PytorchStreamWriter 等存储错误退出，总控脚本会清理损坏 checkpoint 和非 selected checkpoint。
3. 清理后从当前层最新可加载 checkpoint 继续训练。
4. 非存储类错误保留 FAILED 状态并等待人工检查。

## 7. 选用 checkpoint 与评测结果

<!-- REQUEST_ONLY_LLAVA_SWEEP_RESULTS_START -->

自动回填时间：`2026-05-11 19:58:10`

远端结果目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava`

完成标记：done_at=2026-05-11 19:57:37<br>note=all 96 eval manifests and mean_results exist; previous FAILED was caused by CRLF after successful summary generation<br>eval_log=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/full_layer_target0003_eval.log<br>eval_summary=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/eval/selected_eval_summary.tsv

### 7.1 Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
|---:|---|---:|---:|---:|---|
| 0 | ACCEPT | 50 | 0.0003 | 0.0000 | `epoch-50-i-1500-ema_loss-0.0003` |
| 1 | ACCEPT | 60 | 0.0003 | 0.0000 | `epoch-60-i-1800-ema_loss-0.0003` |
| 2 | ACCEPT | 50 | 0.0003 | 0.0000 | `epoch-50-i-1500-ema_loss-0.0003` |
| 3 | ACCEPT | 44 | 0.0003 | 0.0000 | `epoch-44-i-1320-ema_loss-0.0003` |
| 4 | ACCEPT | 42 | 0.0003 | 0.0000 | `epoch-42-i-1260-ema_loss-0.0003` |
| 5 | ACCEPT | 43 | 0.0003 | 0.0000 | `epoch-43-i-1290-ema_loss-0.0003` |
| 6 | ACCEPT | 43 | 0.0004 | 0.0001 | `epoch-43-i-1290-ema_loss-0.0004` |
| 7 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 8 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 9 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 10 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 11 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` |
| 12 | ACCEPT | 44 | 0.0004 | 0.0001 | `epoch-44-i-1320-ema_loss-0.0004` |
| 13 | ACCEPT | 50 | 0.0004 | 0.0001 | `epoch-50-i-1500-ema_loss-0.0004` |
| 14 | ACCEPT | 39 | 0.0004 | 0.0001 | `epoch-39-i-1170-ema_loss-0.0004` |
| 15 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 16 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` |
| 17 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` |
| 18 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` |
| 19 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` |
| 20 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 21 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 22 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 23 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 24 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 25 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 26 | ACCEPT | 55 | 0.0004 | 0.0001 | `epoch-55-i-1650-ema_loss-0.0004` |
| 27 | ACCEPT | 62 | 0.0004 | 0.0001 | `epoch-62-i-1860-ema_loss-0.0004` |
| 28 | ACCEPT | 71 | 0.0004 | 0.0001 | `epoch-71-i-2130-ema_loss-0.0004` |
| 29 | ACCEPT | 96 | 0.0004 | 0.0001 | `epoch-96-i-2880-ema_loss-0.0004` |
| 30 | MISS_TARGET | 661 | 0.0016 | 0.0013 | `epoch-661-i-19830-ema_loss-0.0016` |
| 31 | MISS_TARGET | 658 | 3.2771 | 3.2768 | `epoch-658-i-19740-ema_loss-3.2771` |

### 7.2 Evaluation Results

| Layer | Status | Epoch | EMA Loss | train_request acc | val_request acc | val_full acc |
|---:|---|---:|---:|---:|---:|---:|
| 0 | ACCEPT | 50 | 0.0003 | 1.0000 | 0.8853 | 0.8853 |
| 1 | ACCEPT | 60 | 0.0003 | 1.0000 | 0.8949 | 0.8949 |
| 2 | ACCEPT | 50 | 0.0003 | 1.0000 | 0.8860 | 0.8860 |
| 3 | ACCEPT | 44 | 0.0003 | 1.0000 | 0.8691 | 0.8691 |
| 4 | ACCEPT | 42 | 0.0003 | 1.0000 | 0.8693 | 0.8693 |
| 5 | ACCEPT | 43 | 0.0003 | 1.0000 | 0.8620 | 0.8620 |
| 6 | ACCEPT | 43 | 0.0004 | 1.0000 | 0.8600 | 0.8600 |
| 7 | ACCEPT | 42 | 0.0004 | 1.0000 | 0.9098 | 0.9098 |
| 8 | ACCEPT | 38 | 0.0004 | 1.0000 | 0.8500 | 0.8500 |
| 9 | ACCEPT | 42 | 0.0004 | 1.0000 | 0.8257 | 0.8257 |
| 10 | ACCEPT | 42 | 0.0004 | 1.0000 | 0.8354 | 0.8354 |
| 11 | ACCEPT | 37 | 0.0004 | 1.0000 | 0.8506 | 0.8506 |
| 12 | ACCEPT | 44 | 0.0004 | 1.0000 | 0.8761 | 0.8761 |
| 13 | ACCEPT | 50 | 0.0004 | 1.0000 | 0.8993 | 0.8993 |
| 14 | ACCEPT | 39 | 0.0004 | 1.0000 | 0.9034 | 0.9034 |
| 15 | ACCEPT | 38 | 0.0004 | 1.0000 | 0.8718 | 0.8718 |
| 16 | ACCEPT | 37 | 0.0004 | 1.0000 | 0.8911 | 0.8911 |
| 17 | ACCEPT | 36 | 0.0004 | 1.0000 | 0.8382 | 0.8382 |
| 18 | ACCEPT | 36 | 0.0004 | 1.0000 | 0.8395 | 0.8395 |
| 19 | ACCEPT | 36 | 0.0004 | 1.0000 | 0.8178 | 0.8178 |
| 20 | ACCEPT | 32 | 0.0004 | 1.0000 | 0.8770 | 0.8770 |
| 21 | ACCEPT | 38 | 0.0004 | 1.0000 | 0.8585 | 0.8585 |
| 22 | ACCEPT | 38 | 0.0004 | 1.0000 | 0.8505 | 0.8505 |
| 23 | ACCEPT | 42 | 0.0004 | 1.0000 | 0.8334 | 0.8334 |
| 24 | ACCEPT | 42 | 0.0004 | 1.0000 | 0.8649 | 0.8649 |
| 25 | ACCEPT | 46 | 0.0004 | 1.0000 | 0.8333 | 0.8333 |
| 26 | ACCEPT | 55 | 0.0004 | 1.0000 | 0.8555 | 0.8555 |
| 27 | ACCEPT | 62 | 0.0004 | 1.0000 | 0.8023 | 0.8023 |
| 28 | ACCEPT | 71 | 0.0004 | 1.0000 | 0.8136 | 0.8136 |
| 29 | ACCEPT | 96 | 0.0004 | 1.0000 | 0.8057 | 0.8057 |
| 30 | MISS_TARGET | 661 | 0.0016 | 1.0000 | 0.6796 | 0.6796 |
| 31 | MISS_TARGET | 658 | 3.2771 | 0.4561 | 0.5105 | 0.5105 |

样本数：`train_request=30`，`val_request=70`，`val_full=70`。这里的 acc 来自各 split 的 `single_edit/mean_results.json` 中 `reliability.acc`。

### 7.3 Same-Entity Full Metrics Evaluation Results

本节使用修正后的同实体测试集重新评测已训练好的 LLaVA adapter 全层 checkpoint，不重新训练。评测完成时间：`2026-05-14 19:43:01`。

评测数据：

`/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json`

服务器汇总结果：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv`

样本构成：`request=30`，`generality.text_rephrase=30`，`generality.image_rephrase=66`，`locality.text_loc=30`，`locality.image_loc=30`，`portability=62`。其中 request 来自训练集 request 字段；generality/locality/portability 来自原始验证集，并保证 request、generality、portability 对齐到同一实体。

| Layer | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | Port-1 | Port-2 | Status |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 1.0000 | 0.9750 | 0.9739 | 0.9755 | 0.6897 | 1.0000 | 0.3794 | 0.3029 | 0.3719 | 0.2293 | done |
| 1 | 1.0000 | 0.9753 | 0.9572 | 0.9836 | 0.6842 | 1.0000 | 0.3683 | 0.3510 | 0.3823 | 0.3177 | done |
| 2 | 1.0000 | 0.9584 | 0.9292 | 0.9717 | 0.6772 | 1.0000 | 0.3544 | 0.2726 | 0.2651 | 0.2805 | done |
| 3 | 1.0000 | 0.9725 | 0.9444 | 0.9852 | 0.6828 | 1.0000 | 0.3656 | 0.2823 | 0.2810 | 0.2837 | done |
| 4 | 1.0000 | 0.9800 | 0.9639 | 0.9874 | 0.6981 | 1.0000 | 0.3961 | 0.3052 | 0.3219 | 0.2874 | done |
| 5 | 1.0000 | 0.9718 | 0.9625 | 0.9760 | 0.6689 | 1.0000 | 0.3378 | 0.2944 | 0.2419 | 0.3504 | done |
| 6 | 1.0000 | 0.9729 | 0.9661 | 0.9760 | 0.6706 | 1.0000 | 0.3411 | 0.3146 | 0.3148 | 0.3143 | done |
| 7 | 1.0000 | 0.9808 | 0.9786 | 0.9818 | 0.6986 | 1.0000 | 0.3972 | 0.3077 | 0.3190 | 0.2956 | done |
| 8 | 1.0000 | 0.9621 | 0.9389 | 0.9726 | 0.6814 | 1.0000 | 0.3628 | 0.3011 | 0.3190 | 0.2819 | done |
| 9 | 1.0000 | 0.9526 | 0.9088 | 0.9724 | 0.7153 | 1.0000 | 0.4306 | 0.2909 | 0.2771 | 0.3056 | done |
| 10 | 1.0000 | 0.9706 | 0.9639 | 0.9737 | 0.6808 | 1.0000 | 0.3617 | 0.3199 | 0.3219 | 0.3177 | done |
| 11 | 1.0000 | 0.9753 | 0.9600 | 0.9823 | 0.7031 | 1.0000 | 0.4061 | 0.3241 | 0.3411 | 0.3059 | done |
| 12 | 1.0000 | 0.9604 | 0.9325 | 0.9731 | 0.7064 | 1.0000 | 0.4128 | 0.2881 | 0.2583 | 0.3199 | done |
| 13 | 1.0000 | 0.9592 | 0.9197 | 0.9771 | 0.7064 | 1.0000 | 0.4128 | 0.3408 | 0.3529 | 0.3279 | done |
| 14 | 1.0000 | 0.9272 | 0.8060 | 0.9823 | 0.8181 | 1.0000 | 0.6361 | 0.2803 | 0.2404 | 0.3229 | done |
| 15 | 1.0000 | 0.9408 | 0.8702 | 0.9728 | 0.7689 | 1.0000 | 0.5378 | 0.2849 | 0.2641 | 0.3071 | done |
| 16 | 1.0000 | 0.9477 | 0.8549 | 0.9899 | 0.7925 | 1.0000 | 0.5850 | 0.3497 | 0.3747 | 0.3230 | done |
| 17 | 1.0000 | 0.9278 | 0.7968 | 0.9874 | 0.8014 | 1.0000 | 0.6028 | 0.3105 | 0.3034 | 0.3181 | done |
| 18 | 1.0000 | 0.9486 | 0.8494 | 0.9937 | 0.8258 | 1.0000 | 0.6517 | 0.2715 | 0.2188 | 0.3279 | done |
| 19 | 1.0000 | 0.9323 | 0.7974 | 0.9937 | 0.8192 | 1.0000 | 0.6383 | 0.2789 | 0.2432 | 0.3170 | done |
| 20 | 1.0000 | 0.9214 | 0.7698 | 0.9903 | 0.8528 | 1.0000 | 0.7056 | 0.2466 | 0.2065 | 0.2895 | done |
| 21 | 1.0000 | 0.9291 | 0.7785 | 0.9975 | 0.8056 | 1.0000 | 0.6111 | 0.2622 | 0.2010 | 0.3274 | done |
| 22 | 1.0000 | 0.9144 | 0.7398 | 0.9937 | 0.8181 | 1.0000 | 0.6361 | 0.2436 | 0.1935 | 0.2970 | done |
| 23 | 1.0000 | 0.9205 | 0.7568 | 0.9949 | 0.8064 | 1.0000 | 0.6128 | 0.2268 | 0.1643 | 0.2935 | done |
| 24 | 1.0000 | 0.9118 | 0.7373 | 0.9912 | 0.7944 | 1.0000 | 0.5889 | 0.2469 | 0.1911 | 0.3064 | done |
| 25 | 1.0000 | 0.9196 | 0.7565 | 0.9937 | 0.8472 | 1.0000 | 0.6944 | 0.2365 | 0.1810 | 0.2957 | done |
| 26 | 1.0000 | 0.9205 | 0.7623 | 0.9924 | 0.8542 | 1.0000 | 0.7083 | 0.2032 | 0.1333 | 0.2777 | done |
| 27 | 1.0000 | 0.9144 | 0.7401 | 0.9937 | 0.8306 | 1.0000 | 0.6611 | 0.2148 | 0.1680 | 0.2647 | done |
| 28 | 1.0000 | 0.9317 | 0.7926 | 0.9949 | 0.8008 | 1.0000 | 0.6017 | 0.2149 | 0.1552 | 0.2786 | done |
| 29 | 1.0000 | 0.9255 | 0.7784 | 0.9924 | 0.8250 | 1.0000 | 0.6500 | 0.2295 | 0.1940 | 0.2673 | done |
| 30 | 1.0000 | 0.9245 | 0.7806 | 0.9899 | 0.8236 | 1.0000 | 0.6472 | 0.2608 | 0.2557 | 0.2661 | done |
| 31 | 0.4561 | 0.4562 | 0.3391 | 0.5094 | 1.0000 | 1.0000 | 1.0000 | 0.3200 | 0.3224 | 0.3173 | done |

观察：`layer 7` 的 generality 最高，为 `0.9808`；`layer 1` 的 portability 最高，为 `0.3510`；`layer 26` 的 locality 在有效编辑层中最高，为 `0.8542`。`layer 31` 的 locality 为 `1.0000` 主要来自编辑失败后的保守行为，request/generality 只有约 `0.456`，因此不作为有效最佳层。

<!-- REQUEST_ONLY_LLAVA_SWEEP_RESULTS_END -->
