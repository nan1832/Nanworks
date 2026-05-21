# Bridge30 Request-Only InstructBLIP Full Layer Sweep 训练评测手册

## 1. 实验目标

本实验用于检验在 Bridge30 request-only 训练数据下，视觉 Adapter 挂载到 InstructBLIP-Vicuna-7B 不同 Vicuna decoder 层时的编辑效果差异。

核心约束：

- 原始 `jsonl/json` 不改动。
- 训练数据只使用 `request`，不使用 `generality/locality/portability` 作为训练监督。
- `generality/locality/portability` 只用于统一评测。
- IT 模块沿用视觉编辑器口径：visual-only sweep 默认保留 IT 结构；text-only sweep 才关闭 IT。
- 所有层先完成训练并选定 checkpoint，再统一评测。
- InstructBLIP 的视觉信息先经 vision encoder + Q-Former 压缩为 query tokens，再进入 Vicuna decoder；本实验扫的是 Vicuna decoder 层，不是 Q-Former 层。

本实验用于 Cross-Architecture Golden Layer Validation：

```text
架构类型：Q-Former 型
对照模型：BLIP2-OPT-2.7B
验证问题：Q-Former 型模型的视觉编辑层是否集中在中层或中后层
```

## 2. 服务器路径

```text
服务器节点：g07 / g08
项目目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
输出目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
```

模型路径：

```text
InstructBLIP-Vicuna-7B:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/instructblip-vicuna-7b

若服务器尚未下载，来源为：
Salesforce/instructblip-vicuna-7b
```

request-only 数据：

```text
train_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json

val_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json

same_entity_full_metrics:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

图像路径：

```text
Bridge 图像：
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge

COCO 图像：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

## 3. 前置适配检查

InstructBLIP 不是当前已完成扫层的基础模型，训练前必须先完成 VEAD 模型加载与 hook 适配。

### 3.1 代码适配项

需要确认或新增：

```text
editor/vllms_for_edit/instructblip.py
editor/vllms_for_edit/__init__.py 中注册 instructblip-vicuna-7b
scripts/generate_bridge_request_only_yaml.py 支持 instructblip
scripts/eval_bridge_request_only_ckpt.py 支持 instructblip
bridge_train_request_only.py 支持 instructblip 的 processor/tokenizer/generate 流程
```

如果沿用 HuggingFace `InstructBlipForConditionalGeneration`，推荐检查以下对象路径：

```text
model.language_model.model.layers
model.language_model.model.layers.{L}.self_attn
model.language_projection
model.qformer
model.vision_model
```

### 3.2 hook 正确性验证

训练前必须通过：

```text
1. 不挂 adapter 推理正常，可以回答 Bridge request prompt。
2. 挂零初始化 adapter 后，forward 输出与原模型近似一致。
3. forward_equivalence_max_diff < 1e-5。
4. edit_layers=[L] 时，仅第 L 个 Vicuna decoder layer 被 hook。
5. edit_layers=[] 时不应挂 visual adapter。
```

建议 smoke 脚本输出：

```text
model_name
decoder_layer_count
hidden_size
hook_layer
forward_equivalence_max_diff
sample_before_answer
sample_after_zero_adapter_answer
```

## 4. YAML 配置

InstructBLIP 全层 request-only 配置目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/instructblip
```

单层配置命名：

```text
instructblip-vicuna-7b-bridge-request-only-l{L}.yaml
```

如果服务器上尚未生成全层 yaml，先扩展并执行：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

python scripts/generate_bridge_request_only_yaml.py \
  --output-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs \
  --model instructblip-vicuna-7b \
  --layers 0-31
```

InstructBLIP visual adapter yaml 核心模板：

```yaml
edit_model_name: "instructblip-vicuna-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"
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

注意：

- `edit_layers` 是视觉 adapter 扫层位置。
- 当前项目的 `VEADPortConfig` 不接受 `edit_text_layers` 字段；InstructBLIP visual sweep 只通过 `edit_layers: [L]` 控制视觉 adapter 挂载层。
- `llm_layer_tmp` 需以服务器实际模型对象为准；若 HF 模型路径不同，先以 smoke 验证为准。
- InstructBLIP 是 Q-Former + Vicuna，decoder 层数预期为 32，扫层范围为 `0-31`。

## 5. 训练规则

层位范围：

```text
InstructBLIP Vicuna decoder: language_model.model.layers.0-31
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
6. 若到 `700` epoch 仍没有命中目标，标记为 `MISS_TARGET`，选现存最接近 checkpoint 进入统一评测。

存储规则：

```text
命中目标后，仅保留 selected checkpoint。
补训过程中可保留最近 1 个 checkpoint 用于断点续训。
如果保存 checkpoint 报 No space left / PytorchStreamWriter / unexpected pos，自动清理本层非必要 checkpoint 后重试。
保存后必须 torch.load 校验，避免留下不可读 checkpoint。
```

## 6. 单层训练命令模板

先用单层 smoke 确认 InstructBLIP 训练链路无误，例如 `layer 0`：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=$PWD:$PYTHONPATH

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
L=0

/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 bridge_train_request_only.py \
  --model-name instructblip-vicuna-7b \
  --config /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/instructblip/instructblip-vicuna-7b-bridge-request-only-l${L}.yaml \
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
  --train-name-prefix "bridge_request_only_instructblip_l${L}_target0003" \
  --reset-cache
```

如果 smoke 层出现模型加载或 generate 接口错误，先回到第 3 节修 loader，不进入全层训练。

## 7. 全自动训练脚本

建议从 BLIP2 版本复制并泛化出 InstructBLIP 版本：

```text
scripts/run_blip2_request_only_remaining_layers_target_loss.sh
-> scripts/run_instructblip_request_only_remaining_layers_target_loss.sh
```

InstructBLIP 版本需要替换：

```text
MODEL_NAME=instructblip-vicuna-7b
CONFIG_DIR=/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/instructblip
CFG_PATTERN=instructblip-vicuna-7b-bridge-request-only-l{L}.yaml
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
TRAIN_NAME_PREFIX=bridge_request_only_instructblip_l{L}_target0003
LAYERS=0-31
MAX_EPOCHS=700
TARGET_LOSS=0.0003
TARGET_TOLERANCE=0.0001
```

启动全层训练：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
mkdir -p "$OUT"

nohup bash scripts/run_instructblip_request_only_remaining_layers_target_loss.sh \
  > "$OUT/full_layer_target0003_sweep.log" 2>&1 &
```

如果需要指定从某层恢复：

```bash
LAYERS="12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31" \
  bash scripts/run_instructblip_request_only_remaining_layers_target_loss.sh
```

## 8. 统一评测脚本

建议从 BLIP2 版本复制并泛化出 InstructBLIP 版本：

```text
scripts/eval_blip2_request_only_selected_layers.sh
-> scripts/eval_instructblip_request_only_selected_layers.sh
```

InstructBLIP 版本需要替换：

```text
MODEL_NAME=instructblip-vicuna-7b
CONFIG_DIR=/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/instructblip
CFG_PATTERN=instructblip-vicuna-7b-bridge-request-only-l{L}.yaml
OUT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
EVAL_NAME={split}_l{L}_target0003
```

评测前必须设置 `PYTHONPATH`：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
```

启动统一评测：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip

nohup bash scripts/eval_instructblip_request_only_selected_layers.sh \
  > "$OUT/full_layer_target0003_eval.log" 2>&1 &
```

评测输出：

```text
$OUT/eval/selected_eval_summary.tsv
$OUT/eval/{split}/layer_{L}/vead/instructblip-vicuna-7b/{split}_l{L}_target0003/single_edit/mean_results.json
```

## 9. Same-Entity Full Metrics 评测

全层训练结束后，必须使用同实体 full metrics 测试集重新评测 selected checkpoint。

评测数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

样本构成应与 LLaVA / BLIP2 已有实验一致：

```text
request=30
generality.text_rephrase=30
generality.image_rephrase=66
locality.text_loc=30
locality.image_loc=30
portability=62
```

输出：

```text
$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
```

结果表字段：

```text
layer
request
generality
gen-T
gen-I
locality
loc-T
loc-I
portability
port-1
port-2
status
```

## 10. 监控命令

查看训练/评测进程：

```bash
pgrep -af 'bridge_train_request_only.py|eval_bridge_request_only_ckpt.py|instructblip'
```

查看 GPU：

```bash
watch -n 2 -d nvidia-smi
```

查看训练日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
tail -f "$OUT/full_layer_target0003_sweep.log"
```

查看评测日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
tail -f "$OUT/full_layer_target0003_eval.log"
tail -f "$OUT/full_layer_same_entity_full_metrics_eval.log"
```

统计 selected checkpoint：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
find "$OUT" -name selected_checkpoint.tsv -type f | wc -l
```

统计评测完成数：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
for split in train_request val_request val_full; do
  echo -n "$split "
  find "$OUT/eval/$split" -name eval_manifest.json -type f | wc -l
done
```

检查 checkpoint 可读性：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip
/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 - <<'PY'
from pathlib import Path
import torch
root = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip")
bad = []
for p in root.rglob("checkpoints/epoch-*"):
    try:
        torch.load(str(p), map_location="cpu")
    except Exception as e:
        bad.append((str(p), repr(e)))
print("bad_ckpt_count", len(bad))
for item in bad[:20]:
    print(item)
PY
```

## 11. 结果回填规则

最终手册应补充三张表。

Selected checkpoint 表：

```text
layer
status: ACCEPT / MISS_TARGET
selected_epoch
selected_ema_loss
diff_to_0.0003
checkpoint
```

基础 request-only 评测结果表：

```text
layer
status
selected_epoch
selected_ema_loss
train_request reliability acc
val_request reliability acc
val_full reliability acc
```

Same-Entity Full Metrics 结果表：

```text
layer
request
generality
gen-T
gen-I
locality
loc-T
loc-I
portability
port-1
port-2
status
```

注意：

- `val_request` 与旧 `val_full` 若仍只取 `reliability.acc`，两列可能相同；最终结论必须以 Same-Entity Full Metrics 为准。
- `layer 31` 若 request/generalization 失败但 locality 很高，不应作为有效最佳层。
- 若 generality 出现大面积 `1.0000` 平台，需要同时报告 locality、portability 和 balanced-golden。

## 12. 预期观察点

InstructBLIP 与 BLIP2 同属 Q-Former 型，但 LLM backbone 不同：

- BLIP2-OPT-2.7B：Q-Former -> OPT decoder
- InstructBLIP-Vicuna-7B：Q-Former -> Vicuna decoder

因此本实验重点观察：

```text
1. InstructBLIP 的视觉 gen-golden 是否也落在中层平台。
2. 若与 BLIP2 一致，说明 Q-Former 压缩注入机制可能主导视觉编辑层位置。
3. 若更接近 LLaVA 浅层，说明 Vicuna decoder backbone 可能比 Q-Former 结构更强地影响层位。
4. LGA 指标 M_abscos_x_newn / M_newn_x_1mcos 是否能预测 InstructBLIP 的真实 sweep oracle。
```

重点候选层：

```text
浅层：0,1,2,3,4,5
中层：8,9,12,14,15,16,17,18,19,21
后层：26,28,29,30,31
```

最终结论必须以 `0-31` 全层训练与统一评测结果为准。

## 13. 当前状态

```text
文档状态：InstructBLIP 视觉编辑器全层 sweep 训练评测手册已创建。
当前状态：已完成模型下载、loader 注册、yaml 生成和 layer-0 smoke train；后台 supervisor 已在 g07 排队，等待 GPU 空闲后自动启动全层训练与 Same-Entity Full Metrics 评测。
下一步：
  1. 等待 g07 GPU 空闲
  2. 自动执行 0-31 层全层训练
  3. 自动执行 Same-Entity Full Metrics 评测
  4. 拉回远端 instructblip_results_append.md 并回填第 14 节结果
```

## 14. 选用 checkpoint 与评测结果

<!-- REQUEST_ONLY_INSTRUCTBLIP_SWEEP_RESULTS_START -->

## InstructBLIP Request-Only Full Layer Sweep Results

### Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
|---:|---|---:|---:|---:|---|
| 0 | ACCEPT | 39 | 0.0004 | 0.0001 | `epoch-39-i-1170-ema_loss-0.0004` |
| 1 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 2 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 3 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 4 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 5 | ACCEPT | 50 | 0.0004 | 0.0001 | `epoch-50-i-1500-ema_loss-0.0004` |
| 6 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 7 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 8 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 9 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 10 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 11 | ACCEPT | 41 | 0.0004 | 0.0001 | `epoch-41-i-1230-ema_loss-0.0004` |
| 12 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` |
| 13 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` |
| 14 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 15 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 16 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 17 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 18 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 19 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 20 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 21 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 22 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 23 | ACCEPT | 56 | 0.0004 | 0.0001 | `epoch-56-i-1680-ema_loss-0.0004` |
| 24 | ACCEPT | 56 | 0.0004 | 0.0001 | `epoch-56-i-1680-ema_loss-0.0004` |
| 25 | ACCEPT | 62 | 0.0004 | 0.0001 | `epoch-62-i-1860-ema_loss-0.0004` |
| 26 | ACCEPT | 62 | 0.0004 | 0.0001 | `epoch-62-i-1860-ema_loss-0.0004` |
| 27 | ACCEPT | 71 | 0.0004 | 0.0001 | `epoch-71-i-2130-ema_loss-0.0004` |
| 28 | ACCEPT | 96 | 0.0004 | 0.0001 | `epoch-96-i-2880-ema_loss-0.0004` |
| 29 | ACCEPT | 125 | 0.0004 | 0.0001 | `epoch-125-i-3750-ema_loss-0.0004` |
| 30 | ACCEPT | 428 | 0.0004 | 0.0001 | `epoch-428-i-12840-ema_loss-0.0004` |
| 31 | MISS_TARGET | 16 | 4.5116 | 4.5113 | `epoch-16-i-480-ema_loss-4.5116` |

### Same-Entity Full Metrics

| Layer | Request Acc | Generality Acc | Gen Text | Gen Image | Locality Acc | Loc Text | Loc Image | Portability Acc | Port 1hop | Port 2hop |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1.0000 | 0.9673 | 0.9094 | 0.9937 | 0.6647 | 1.0000 | 0.3294 | 0.2355 | 0.1695 | 0.3058 |
| 1 | 1.0000 | 0.9436 | 0.8747 | 0.9749 | 0.6767 | 1.0000 | 0.3533 | 0.3158 | 0.3034 | 0.3291 |
| 2 | 1.0000 | 0.9144 | 0.7921 | 0.9700 | 0.6558 | 1.0000 | 0.3117 | 0.2464 | 0.2052 | 0.2903 |
| 3 | 1.0000 | 0.9274 | 0.8043 | 0.9833 | 0.6636 | 1.0000 | 0.3272 | 0.2790 | 0.2263 | 0.3353 |
| 4 | 1.0000 | 0.9288 | 0.8276 | 0.9749 | 0.6731 | 1.0000 | 0.3461 | 0.2721 | 0.2193 | 0.3285 |
| 5 | 1.0000 | 0.9354 | 0.8515 | 0.9734 | 0.6969 | 1.0000 | 0.3939 | 0.3122 | 0.3047 | 0.3202 |
| 6 | 1.0000 | 0.9416 | 0.8652 | 0.9763 | 0.6733 | 1.0000 | 0.3467 | 0.3332 | 0.3388 | 0.3273 |
| 7 | 1.0000 | 0.9462 | 0.8696 | 0.9810 | 0.7081 | 1.0000 | 0.4161 | 0.3568 | 0.3466 | 0.3677 |
| 8 | 1.0000 | 0.9264 | 0.8343 | 0.9683 | 0.7067 | 1.0000 | 0.4133 | 0.3245 | 0.3357 | 0.3125 |
| 9 | 1.0000 | 0.9208 | 0.8210 | 0.9662 | 0.7044 | 1.0000 | 0.4089 | 0.3446 | 0.3706 | 0.3168 |
| 10 | 1.0000 | 0.9398 | 0.8443 | 0.9833 | 0.7308 | 1.0000 | 0.4617 | 0.3650 | 0.3510 | 0.3799 |
| 11 | 1.0000 | 0.9398 | 0.8212 | 0.9937 | 0.7350 | 1.0000 | 0.4700 | 0.3449 | 0.3552 | 0.3339 |
| 12 | 1.0000 | 0.9756 | 0.9386 | 0.9924 | 0.7864 | 1.0000 | 0.5728 | 0.3486 | 0.3807 | 0.3144 |
| 13 | 1.0000 | 0.9308 | 0.8038 | 0.9885 | 0.7975 | 1.0000 | 0.5950 | 0.3773 | 0.3966 | 0.3568 |
| 14 | 1.0000 | 0.9268 | 0.7656 | 1.0000 | 0.7094 | 1.0000 | 0.4189 | 0.3441 | 0.3576 | 0.3298 |
| 15 | 1.0000 | 0.9480 | 0.8488 | 0.9931 | 0.7433 | 1.0000 | 0.4867 | 0.3795 | 0.4125 | 0.3442 |
| 16 | 1.0000 | 0.9057 | 0.7310 | 0.9851 | 0.7392 | 1.0000 | 0.4783 | 0.3580 | 0.3883 | 0.3257 |
| 17 | 1.0000 | 0.9158 | 0.7501 | 0.9912 | 0.8156 | 1.0000 | 0.6311 | 0.3751 | 0.4154 | 0.3322 |
| 18 | 1.0000 | 0.9126 | 0.7260 | 0.9975 | 0.7828 | 1.0000 | 0.5656 | 0.3840 | 0.4198 | 0.3458 |
| 19 | 1.0000 | 0.9239 | 0.7620 | 0.9975 | 0.8467 | 1.0000 | 0.6933 | 0.3462 | 0.3661 | 0.3250 |
| 20 | 1.0000 | 0.9311 | 0.7851 | 0.9975 | 0.8583 | 1.0000 | 0.7167 | 0.3700 | 0.4229 | 0.3135 |
| 21 | 1.0000 | 0.9181 | 0.7381 | 1.0000 | 0.8036 | 1.0000 | 0.6072 | 0.3444 | 0.3901 | 0.2957 |
| 22 | 1.0000 | 0.9260 | 0.7687 | 0.9975 | 0.8578 | 1.0000 | 0.7156 | 0.2933 | 0.3076 | 0.2780 |
| 23 | 1.0000 | 0.9242 | 0.7576 | 1.0000 | 0.8369 | 1.0000 | 0.6739 | 0.3298 | 0.3706 | 0.2863 |
| 24 | 1.0000 | 0.9315 | 0.7809 | 1.0000 | 0.8397 | 1.0000 | 0.6794 | 0.3417 | 0.3654 | 0.3164 |
| 25 | 1.0000 | 0.9250 | 0.7600 | 1.0000 | 0.8347 | 1.0000 | 0.6694 | 0.3435 | 0.4005 | 0.2826 |
| 26 | 1.0000 | 0.9386 | 0.8034 | 1.0000 | 0.8828 | 1.0000 | 0.7656 | 0.3567 | 0.3971 | 0.3135 |
| 27 | 1.0000 | 0.9325 | 0.7840 | 1.0000 | 0.8611 | 1.0000 | 0.7222 | 0.3400 | 0.3792 | 0.2981 |
| 28 | 1.0000 | 0.9446 | 0.8226 | 1.0000 | 0.8528 | 1.0000 | 0.7056 | 0.3291 | 0.3677 | 0.2879 |
| 29 | 1.0000 | 0.9484 | 0.8350 | 1.0000 | 0.8300 | 1.0000 | 0.6600 | 0.3495 | 0.3883 | 0.3081 |
| 30 | 1.0000 | 0.9698 | 0.9033 | 1.0000 | 0.8717 | 1.0000 | 0.7433 | 0.3427 | 0.3945 | 0.2875 |
| 31 | 0.3080 | 0.3201 | 0.2685 | 0.3435 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |

Selected checkpoint TSV root: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip`
Metrics summary TSV: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv`

<!-- REQUEST_ONLY_INSTRUCTBLIP_SWEEP_RESULTS_END -->

