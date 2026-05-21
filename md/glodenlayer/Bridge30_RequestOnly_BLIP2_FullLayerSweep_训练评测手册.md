# Bridge30 Request-Only BLIP2 Full Layer Sweep 训练评测手册

## 1. 实验目标

本实验用于检验在 Bridge30 request-only 训练数据下，Adapter 挂载到 BLIP2-OPT-2.7B 不同 OPT decoder 层时的编辑效果差异。

核心约束：

- 原始 `jsonl/json` 不改动。
- 训练数据只使用 `request`，不使用 `generality/locality/portability` 作为训练监督。
- IT 模块保持和之前 `bridge-only-vis` BLIP2 yaml 一致；本实验控制的是视觉表征进入 OPT decoder 后不同层位置的编辑强度。
- 所有层先完成训练并选定 checkpoint，再统一评测。
- BLIP2 的视觉信息先经 Q-Former 压缩成 query/prefix，再进入 OPT decoder；本实验扫的是 `language_model.model.decoder.layers.0-31`，不是 Q-Former 层。

## 2. 服务器路径

```text
服务器节点：g07
项目目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
输出目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
```

模型路径：

```text
BLIP2-OPT-2.7B:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b
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

注意：当前 `val_request` 与 `val_full` 的 request/reliability 样本一致，且 `generality/locality` 为空列表。因此若只读取 `reliability.acc`，两列结果会完全一致；`val_full acc` 应理解为 `val_full reliability acc`，不是 full-metric 总分。

## 3. YAML 配置

BLIP2 全层 request-only 配置目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2
```

单层配置命名：

```text
blip2-opt-2.7b-bridge-request-only-l{L}.yaml
```

如果服务器上尚未生成全层 yaml，先执行：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

python scripts/generate_bridge_request_only_yaml.py \
  --output-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs \
  --layers 0-31
```

BLIP2 yaml 核心模板：

```yaml
edit_model_name: "blip2-opt-2.7b"
llm_hidden_size: 2560
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.decoder.layers.{}"
llm_att_tmp: "language_model.model.decoder.layers.{}.self_attn"
edit_layers: [L]
train_cfg:
  lr: 1.e-4
  rel_lambda: 1.0
  gen_lambda: 0.0
  loc_lambda: 0.0
  inf_mapper_lambda: 0.1
port_lambda: 0.0
port_sample_n: 1
IT:
  add_it: true
  layers: [20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
```

## 4. 训练规则

层位范围：

```text
BLIP2 OPT decoder: language_model.model.decoder.layers.0-31
```

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
5. 后续仍按 `20` 轮递增，直到出现可接受 checkpoint。
6. 若某层长期不收敛，可人工设定 epoch 上限并标记为 `MISS_TARGET`，选现存最接近 checkpoint 继续后续流程。

建议 BLIP2 额外设置最大上限，避免后层不收敛时无限补训：

```text
默认上限建议：700 epoch
状态标记：MISS_TARGET
选点规则：现存 checkpoint 中与 0.0003 最接近者
```

## 5. 单层训练命令模板

先用单层 smoke 确认 BLIP2 训练链路无误，例如 `layer 0`：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=$PWD:$PYTHONPATH

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
L=0

/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 bridge_train_request_only.py \
  --model-name blip2-opt-2.7b \
  --config /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2/blip2-opt-2.7b-bridge-request-only-l${L}.yaml \
  --data-path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --cache-root "$OUT/layer_${L}_target0003/cache" \
  --records-dir "$OUT/layer_${L}_target0003/records" \
  --run-config-path "$OUT/layer_${L}_target0003/run_config.json" \
  --epochs 100 \
  --batch-size 1 \
  --save-ckpt-per-i 30 \
  --random-seed 2026 \
  --data-buffer-size 1 \
  --device cuda:0 \
  --single-gpu \
  --train-name-prefix "bridge_request_only_blip2_l${L}_target0003" \
  --reset-cache
```

## 6. 全自动训练脚本

建议从 LLaVA 版本复制并泛化出 BLIP2 版本：

```text
scripts/run_llava_request_only_remaining_layers_target_loss.sh
-> scripts/run_blip2_request_only_remaining_layers_target_loss.sh
```

BLIP2 版本需要替换：

```text
MODEL_NAME=blip2-opt-2.7b
CONFIG_DIR=/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2
CFG_PATTERN=blip2-opt-2.7b-bridge-request-only-l{L}.yaml
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
TRAIN_NAME_PREFIX=bridge_request_only_blip2_l{L}_target0003
LAYERS=0-31
```

启动全层训练：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2

nohup bash scripts/run_blip2_request_only_remaining_layers_target_loss.sh \
  > "$OUT/full_layer_target0003_sweep.log" 2>&1 &
```

如果需要设置强制上限：

```bash
LAYERS="$(seq 0 31)" FORCE_SELECT_AT_EPOCHS="30:700 31:700" \
  bash scripts/run_blip2_request_only_remaining_layers_target_loss.sh
```

## 7. 统一评测脚本

建议从 LLaVA 版本复制并泛化出 BLIP2 版本：

```text
scripts/eval_llava_request_only_selected_layers.sh
-> scripts/eval_blip2_request_only_selected_layers.sh
```

BLIP2 版本需要替换：

```text
MODEL_NAME=blip2-opt-2.7b
CONFIG_DIR=/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2
CFG_PATTERN=blip2-opt-2.7b-bridge-request-only-l{L}.yaml
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
EVAL_NAME={split}_l{L}_target0003
```

评测前必须设置 `PYTHONPATH`，避免直接执行 `scripts/eval_bridge_request_only_ckpt.py` 时找不到仓库本地包：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
```

启动统一评测：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2

nohup bash scripts/eval_blip2_request_only_selected_layers.sh \
  > "$OUT/full_layer_target0003_eval.log" 2>&1 &
```

评测输出：

```text
$OUT/eval/selected_eval_summary.tsv
$OUT/eval/{split}/layer_{L}/vead/blip2-opt-2.7b/{split}_l{L}_target0003/single_edit/mean_results.json
```

## 8. 监控命令

查看训练/评测进程：

```bash
pgrep -af 'bridge_train_request_only.py|eval_bridge_request_only_ckpt.py'
```

查看 GPU：

```bash
watch -n 2 -d nvidia-smi
```

查看训练日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
tail -f "$OUT/full_layer_target0003_sweep.log"
```

查看评测日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
tail -f "$OUT/full_layer_target0003_eval.log"
```

统计 selected checkpoint：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
find "$OUT" -name selected_checkpoint.tsv -type f | wc -l
```

统计评测完成数：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2
for split in train_request val_request val_full; do
  echo -n "$split "
  find "$OUT/eval/$split" -name eval_manifest.json -type f | wc -l
done
```

## 9. 结果回填规则

最终手册应补充两张表。

Selected checkpoint 表：

```text
layer
status: ACCEPT / MISS_TARGET
selected_epoch
selected_ema_loss
diff_to_0.0003
checkpoint
```

评测结果表：

```text
layer
status
selected_epoch
selected_ema_loss
train_request reliability acc
val_request reliability acc
val_full reliability acc
```

注意：

- 当前 `val_request` 与 `val_full` 文件内容相同，因此如果仍只取 `reliability.acc`，两列预期会相同。
- 若后续重新构造包含非空 `generality/locality` 的 `val_full`，需要额外记录 generality/locality 指标，不能再把 `val_full acc` 当作 full-metric 总分。

## 10. 预期观察点

BLIP2 与 LLaVA 的结构不同：

- LLaVA 的视觉 token 经过 projector 直接进入语言模型，浅层可能更强地承担视觉-文本绑定。
- BLIP2 的视觉信息先经 Q-Former 压缩，再作为 query/prefix 输入 OPT decoder。
- 因此 BLIP2 浅层可能对 visual prefix 很敏感，但不一定是最稳定的可控编辑层；中层或中后层可能更值得关注。

结合已有 LGA 结果，BLIP2 重点观察：

```text
浅层候选：0,1,2,3,4,5
中层候选：14,15,16,19
后层候选：26,28,29,30,31
```

最终结论必须以 0-31 全层训练与统一评测结果为准。

## 11. 当前状态

```text
文档状态：BLIP2 0-31 层训练已完成，32 层均已有 selected_checkpoint.tsv。
下一步：启动统一评测，评测结束后自动回填 selected checkpoint 表和 train_request/val_request/val_full 结果表。
```

## 12. 选用 checkpoint 与评测结果

<!-- REQUEST_ONLY_BLIP2_SWEEP_RESULTS_START -->

自动回填时间：`2026-05-14 08:35:14`

远端结果目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2`

完成标记：DONE at 2026-05-13 22:30:07<br>selected_checkpoints=32<br>train_log=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2/full_layer_target0003_sweep.log<br>eval_log=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2/full_layer_target0003_eval.log<br>eval_summary=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2/eval/selected_eval_summary.tsv

### 12.1 Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
|---:|---|---:|---:|---:|---|
| 0 | ACCEPT | 100 | 0.0004 | 0.0001 | `epoch-100-i-3000-ema_loss-0.0004` |
| 1 | ACCEPT | 114 | 0.0004 | 0.0001 | `epoch-114-i-3420-ema_loss-0.0004` |
| 2 | ACCEPT | 108 | 0.0004 | 0.0001 | `epoch-108-i-3240-ema_loss-0.0004` |
| 3 | ACCEPT | 100 | 0.0004 | 0.0001 | `epoch-100-i-3000-ema_loss-0.0004` |
| 4 | ACCEPT | 91 | 0.0004 | 0.0001 | `epoch-91-i-2730-ema_loss-0.0004` |
| 5 | ACCEPT | 87 | 0.0004 | 0.0001 | `epoch-87-i-2610-ema_loss-0.0004` |
| 6 | ACCEPT | 91 | 0.0004 | 0.0001 | `epoch-91-i-2730-ema_loss-0.0004` |
| 7 | ACCEPT | 87 | 0.0004 | 0.0001 | `epoch-87-i-2610-ema_loss-0.0004` |
| 8 | ACCEPT | 84 | 0.0004 | 0.0001 | `epoch-84-i-2520-ema_loss-0.0004` |
| 9 | ACCEPT | 75 | 0.0004 | 0.0001 | `epoch-75-i-2250-ema_loss-0.0004` |
| 10 | ACCEPT | 69 | 0.0004 | 0.0001 | `epoch-69-i-2070-ema_loss-0.0004` |
| 11 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` |
| 12 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` |
| 13 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` |
| 14 | ACCEPT | 71 | 0.0004 | 0.0001 | `epoch-71-i-2130-ema_loss-0.0004` |
| 15 | ACCEPT | 71 | 0.0004 | 0.0001 | `epoch-71-i-2130-ema_loss-0.0004` |
| 16 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` |
| 17 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` |
| 18 | ACCEPT | 69 | 0.0004 | 0.0001 | `epoch-69-i-2070-ema_loss-0.0004` |
| 19 | ACCEPT | 71 | 0.0004 | 0.0001 | `epoch-71-i-2130-ema_loss-0.0004` |
| 20 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` |
| 21 | ACCEPT | 71 | 0.0004 | 0.0001 | `epoch-71-i-2130-ema_loss-0.0004` |
| 22 | ACCEPT | 75 | 0.0004 | 0.0001 | `epoch-75-i-2250-ema_loss-0.0004` |
| 23 | ACCEPT | 77 | 0.0004 | 0.0001 | `epoch-77-i-2310-ema_loss-0.0004` |
| 24 | ACCEPT | 75 | 0.0004 | 0.0001 | `epoch-75-i-2250-ema_loss-0.0004` |
| 25 | ACCEPT | 84 | 0.0004 | 0.0001 | `epoch-84-i-2520-ema_loss-0.0004` |
| 26 | ACCEPT | 87 | 0.0004 | 0.0001 | `epoch-87-i-2610-ema_loss-0.0004` |
| 27 | ACCEPT | 108 | 0.0004 | 0.0001 | `epoch-108-i-3240-ema_loss-0.0004` |
| 28 | ACCEPT | 134 | 0.0004 | 0.0001 | `epoch-134-i-4020-ema_loss-0.0004` |
| 29 | ACCEPT | 166 | 0.0004 | 0.0001 | `epoch-166-i-4980-ema_loss-0.0004` |
| 30 | MISS_TARGET | 617 | 0.0008 | 0.0005 | `epoch-617-i-18510-ema_loss-0.0008` |
| 31 | MISS_TARGET | 513 | 3.4272 | 3.4269 | `epoch-513-i-15390-ema_loss-3.4272` |

### 12.2 Evaluation Results

| Layer | Status | Epoch | EMA Loss | train_request acc | val_request acc | val_full acc |
|---:|---|---:|---:|---:|---:|---:|
| 0 | ACCEPT | 100 | 0.0004 | 1.0000 | 0.7648 | 0.7648 |
| 1 | ACCEPT | 114 | 0.0004 | 1.0000 | 0.7738 | 0.7738 |
| 2 | ACCEPT | 108 | 0.0004 | 1.0000 | 0.8040 | 0.8040 |
| 3 | ACCEPT | 100 | 0.0004 | 1.0000 | 0.7677 | 0.7677 |
| 4 | ACCEPT | 91 | 0.0004 | 1.0000 | 0.8151 | 0.8151 |
| 5 | ACCEPT | 87 | 0.0004 | 1.0000 | 0.8327 | 0.8327 |
| 6 | ACCEPT | 91 | 0.0004 | 1.0000 | 0.8084 | 0.8084 |
| 7 | ACCEPT | 87 | 0.0004 | 1.0000 | 0.8803 | 0.8803 |
| 8 | ACCEPT | 84 | 0.0004 | 1.0000 | 0.8906 | 0.8906 |
| 9 | ACCEPT | 75 | 0.0004 | 1.0000 | 0.9224 | 0.9224 |
| 10 | ACCEPT | 69 | 0.0004 | 1.0000 | 0.9376 | 0.9376 |
| 11 | ACCEPT | 74 | 0.0004 | 1.0000 | 0.8768 | 0.8768 |
| 12 | ACCEPT | 74 | 0.0004 | 1.0000 | 0.8983 | 0.8983 |
| 13 | ACCEPT | 74 | 0.0004 | 1.0000 | 0.9431 | 0.9431 |
| 14 | ACCEPT | 71 | 0.0004 | 1.0000 | 0.9219 | 0.9219 |
| 15 | ACCEPT | 71 | 0.0004 | 1.0000 | 0.9835 | 0.9835 |
| 16 | ACCEPT | 74 | 0.0004 | 1.0000 | 0.9590 | 0.9590 |
| 17 | ACCEPT | 74 | 0.0004 | 1.0000 | 0.9705 | 0.9705 |
| 18 | ACCEPT | 69 | 0.0004 | 1.0000 | 0.9550 | 0.9550 |
| 19 | ACCEPT | 71 | 0.0004 | 1.0000 | 0.9812 | 0.9812 |
| 20 | ACCEPT | 74 | 0.0004 | 1.0000 | 0.8964 | 0.8964 |
| 21 | ACCEPT | 71 | 0.0004 | 1.0000 | 0.9736 | 0.9736 |
| 22 | ACCEPT | 75 | 0.0004 | 1.0000 | 0.9428 | 0.9428 |
| 23 | ACCEPT | 77 | 0.0004 | 1.0000 | 0.9034 | 0.9034 |
| 24 | ACCEPT | 75 | 0.0004 | 1.0000 | 0.8824 | 0.8824 |
| 25 | ACCEPT | 84 | 0.0004 | 1.0000 | 0.8534 | 0.8534 |
| 26 | ACCEPT | 87 | 0.0004 | 1.0000 | 0.8963 | 0.8963 |
| 27 | ACCEPT | 108 | 0.0004 | 1.0000 | 0.8578 | 0.8578 |
| 28 | ACCEPT | 134 | 0.0004 | 1.0000 | 0.8527 | 0.8527 |
| 29 | ACCEPT | 166 | 0.0004 | 1.0000 | 0.9186 | 0.9186 |
| 30 | MISS_TARGET | 617 | 0.0008 | 1.0000 | 0.9008 | 0.9008 |
| 31 | MISS_TARGET | 513 | 3.4272 | 0.3546 | 0.3988 | 0.3988 |

样本数：`train_request=30`，`val_request=70`，`val_full=70`。这里的 acc 来自各 split 的 `single_edit/mean_results.json` 中 `reliability.acc`。

注意：当前 `val_request` 与 `val_full` 的 request/reliability 样本一致，且 generality/locality 为空，因此两列 reliability acc 预期相同。

### 12.3 Same-Entity Full Metrics Evaluation Results

本节使用修正后的同实体测试集重新评测已训练好的 BLIP2 adapter 全层 checkpoint，不重新训练。评测完成时间：`2026-05-14 12:40:09`。

评测数据：

`/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json`

服务器汇总结果：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv`

样本构成：`request=30`，`generality.text_rephrase=30`，`generality.image_rephrase=66`，`locality.text_loc=30`，`locality.image_loc=30`，`portability=62`。其中 request 来自训练集 request 字段；generality/locality/portability 来自原始验证集，并保证 request、generality、portability 对齐到同一实体。

| Layer | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | Port-1 | Port-2 | Status |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 1.0000 | 0.9746 | 0.9799 | 0.9722 | 0.6000 | 1.0000 | 0.2000 | 0.1595 | 0.0417 | 0.2851 | done |
| 1 | 1.0000 | 0.9754 | 0.9750 | 0.9756 | 0.5750 | 1.0000 | 0.1500 | 0.1610 | 0.0521 | 0.2772 | done |
| 2 | 1.0000 | 0.9686 | 0.9777 | 0.9644 | 0.5972 | 1.0000 | 0.1944 | 0.1491 | 0.0495 | 0.2553 | done |
| 3 | 1.0000 | 0.9847 | 0.9889 | 0.9828 | 0.6444 | 1.0000 | 0.2889 | 0.1559 | 0.0573 | 0.2611 | done |
| 4 | 1.0000 | 0.9740 | 0.9561 | 0.9822 | 0.6000 | 1.0000 | 0.2000 | 0.1596 | 0.0703 | 0.2549 | done |
| 5 | 1.0000 | 0.9901 | 0.9833 | 0.9932 | 0.6611 | 1.0000 | 0.3222 | 0.1367 | 0.0495 | 0.2297 | done |
| 6 | 1.0000 | 0.9933 | 0.9833 | 0.9978 | 0.6528 | 1.0000 | 0.3056 | 0.1659 | 0.0703 | 0.2678 | done |
| 7 | 1.0000 | 0.9839 | 0.9833 | 0.9842 | 0.6250 | 1.0000 | 0.2500 | 0.1469 | 0.0703 | 0.2287 | done |
| 8 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.6194 | 1.0000 | 0.2389 | 0.1382 | 0.0495 | 0.2329 | done |
| 9 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.6194 | 1.0000 | 0.2389 | 0.1387 | 0.0495 | 0.2338 | done |
| 10 | 1.0000 | 0.9979 | 1.0000 | 0.9970 | 0.5889 | 1.0000 | 0.1778 | 0.1462 | 0.0417 | 0.2576 | done |
| 11 | 1.0000 | 0.9921 | 0.9852 | 0.9953 | 0.6306 | 1.0000 | 0.2611 | 0.1414 | 0.0495 | 0.2396 | done |
| 12 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.6250 | 1.0000 | 0.2500 | 0.1488 | 0.0521 | 0.2519 | done |
| 13 | 1.0000 | 0.9887 | 0.9722 | 0.9962 | 0.6083 | 1.0000 | 0.2167 | 0.1595 | 0.0703 | 0.2547 | done |
| 14 | 1.0000 | 0.9983 | 0.9944 | 1.0000 | 0.5889 | 1.0000 | 0.1778 | 0.1435 | 0.0495 | 0.2439 | done |
| 15 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.5889 | 1.0000 | 0.1778 | 0.1515 | 0.0417 | 0.2686 | done |
| 16 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.6111 | 1.0000 | 0.2222 | 0.1562 | 0.0417 | 0.2784 | done |
| 17 | 1.0000 | 0.9974 | 1.0000 | 0.9962 | 0.5722 | 1.0000 | 0.1444 | 0.1435 | 0.0417 | 0.2521 | done |
| 18 | 1.0000 | 0.9911 | 0.9847 | 0.9939 | 0.6528 | 1.0000 | 0.3056 | 0.1499 | 0.0417 | 0.2653 | done |
| 19 | 1.0000 | 0.9965 | 0.9889 | 1.0000 | 0.6611 | 1.0000 | 0.3222 | 0.1556 | 0.0599 | 0.2576 | done |
| 20 | 1.0000 | 0.9924 | 0.9889 | 0.9939 | 0.6361 | 1.0000 | 0.2722 | 0.1282 | 0.0417 | 0.2206 | done |
| 21 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 1.0000 | 0.3333 | 0.1428 | 0.0286 | 0.2646 | done |
| 22 | 1.0000 | 0.9954 | 0.9852 | 1.0000 | 0.7194 | 1.0000 | 0.4389 | 0.1442 | 0.0313 | 0.2647 | done |
| 23 | 1.0000 | 0.9861 | 0.9554 | 1.0000 | 0.6750 | 1.0000 | 0.3500 | 0.1540 | 0.0313 | 0.2848 | done |
| 24 | 1.0000 | 0.9962 | 0.9926 | 0.9978 | 0.6750 | 1.0000 | 0.3500 | 0.1460 | 0.0208 | 0.2796 | done |
| 25 | 1.0000 | 0.9892 | 0.9787 | 0.9939 | 0.7306 | 1.0000 | 0.4611 | 0.1491 | 0.0495 | 0.2553 | done |
| 26 | 1.0000 | 0.9935 | 0.9793 | 1.0000 | 0.7056 | 1.0000 | 0.4111 | 0.1451 | 0.0495 | 0.2470 | done |
| 27 | 1.0000 | 0.9962 | 0.9944 | 0.9970 | 0.7139 | 1.0000 | 0.4278 | 0.1328 | 0.0495 | 0.2216 | done |
| 28 | 1.0000 | 0.9915 | 0.9841 | 0.9948 | 0.7694 | 1.0000 | 0.5389 | 0.1181 | 0.0521 | 0.1885 | done |
| 29 | 1.0000 | 0.9862 | 0.9757 | 0.9909 | 0.8056 | 1.0000 | 0.6111 | 0.0918 | 0.0313 | 0.1563 | done |
| 30 | 1.0000 | 0.9644 | 0.9521 | 0.9699 | 0.7500 | 1.0000 | 0.5000 | 0.0670 | 0.0417 | 0.0941 | done |
| 31 | 0.3546 | 0.3558 | 0.2585 | 0.4000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 | done |

观察：`layer 8/9/12/15/16/21` 在 request 与 generality 上均达到 `1.0000`；`layer 29/30` 的 locality 更高但 portability 明显下降；`layer 31` 的 locality 为 `1.0000` 主要是因为编辑未有效写入，request/generality 明显失败，因此不应作为有效最佳层。

<!-- REQUEST_ONLY_BLIP2_SWEEP_RESULTS_END -->
