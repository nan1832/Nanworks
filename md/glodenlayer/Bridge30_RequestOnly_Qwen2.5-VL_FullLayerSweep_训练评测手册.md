# Bridge30 Request-Only Qwen2.5-VL-7B-Instruct Full Layer Sweep 训练评测手册

## 1. 实验目标

本实验用于验证在 Bridge30 request-only 训练数据下，视觉 adapter 挂载到 Qwen2.5-VL-7B-Instruct 不同 decoder 层时的编辑效果差异。

核心问题：

```text
Qwen2.5-VL 作为 MLP / 线性投影型 VLM，其最佳视觉编辑层是否像 LLaVA 一样偏浅层？
```

本实验与 LLaVA 视觉扫层实验严格对齐：

```text
训练数据：只使用 request
评测数据：Same-Entity Full Metrics rephrase_split
视觉编辑：edit_layers=[L], edit_text_layers=[]
文本编辑：不参与本实验
扫层范围：0-27，共 28 层
```

约束：

- 原始 json/jsonl 不改动。
- 训练阶段只使用 `request.image`、`request.prompt`、`request.target_new`。
- `generality/locality/portability` 只用于统一评测。
- 所有层先完成训练并选定 checkpoint，再统一评测。
- 本实验不做 dual-edit，不和文本 adapter 联合训练。
- 本实验主口径不使用 IM/IT influence mapper；如果后续要比较“保留 IT 结构”，作为单独 ablation。

## 2. 服务器路径

```text
服务器节点：g07 / g08
项目目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
输出目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
```

模型目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/Qwen2.5-VL-7B-Instruct
```

已下载文件应包含：

```text
config.json
preprocessor_config.json
tokenizer.json
model.safetensors.index.json
model-00001-of-00005.safetensors
model-00002-of-00005.safetensors
model-00003-of-00005.safetensors
model-00004-of-00005.safetensors
model-00005-of-00005.safetensors
```

训练数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json
```

统一评测数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

图像根目录：

```text
Bridge 图像：/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge
COCO 图像：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

## 3. 模型与 hook 位置

Qwen2.5-VL-7B-Instruct 基本信息：

```text
HuggingFace ID：Qwen/Qwen2.5-VL-7B-Instruct
架构类型：ViT + MLP projection + Qwen2.5 decoder
LLM hidden size：3584
decoder 层数：28
扫层范围：0-27
```

预期 adapter 挂载位置：

```text
decoder layer 模板：model.layers.{}
attention 模板：model.layers.{}.self_attn
```

注意：最终以 smoke test 中打印出的真实模块路径为准。如果模型封装路径不是 `model.layers.{}`，必须先修正 `llm_layer_tmp` 和 `llm_att_tmp`，再进入正式扫层。

## 4. 环境与前置适配

当前 `visedit` 环境中的 `transformers=4.43.0` 可能无法原生加载 Qwen2.5-VL。建议新建或升级独立环境，避免污染已能稳定运行 LLaVA / BLIP2 / InstructBLIP 的环境。

推荐检查：

```bash
/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 - <<'PY'
import transformers
print(transformers.__version__)
PY
```

若不能导入 `Qwen2_5_VLForConditionalGeneration`，需要安装新版 Transformers：

```bash
pip install -U "transformers>=4.49.0" accelerate qwen-vl-utils
```

或按官方建议使用源码版 Transformers：

```bash
pip install git+https://github.com/huggingface/transformers accelerate qwen-vl-utils
```

VEAD 适配需新增或确认以下文件：

```text
editor/vllms_for_edit/qwen2_5_vl.py
editor/vllms_for_edit/__init__.py
utils/GLOBAL.py
configs/vead/qwen2.5-vl-7b-bridge-request-only-l14.yaml
```

必须通过的 smoke test：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH

python - <<'PY'
from utils import load_vllm_for_edit

m = load_vllm_for_edit("Qwen2.5-VL-7B-Instruct", "cuda:0")
print(type(m.model))
print(len(m.model.model.layers))
print(m.model.model.layers[0].__class__)
print(m.model.model.layers[27].__class__)
PY
```

通过标准：

```text
能正常加载本地模型目录
decoder 层数为 28
能定位 layer 0 和 layer 27
不挂 adapter 时 forward 输出保持一致
```

## 5. YAML 基础配置

基础配置文件建议放在：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/configs/vead/qwen2.5-vl-7b-bridge-request-only-l14.yaml
```

核心配置：

```yaml
edit_model_name: "Qwen2.5-VL-7B-Instruct"
llm_hidden_size: 3584
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "model.layers.{}"
llm_att_tmp: "model.layers.{}.self_attn"
edit_layers: [14]
edit_text_layers: []
train_cfg:
  lr: 1.0e-4
  rel_lambda: 1.0
  gen_lambda: 1.0
  loc_lambda: 1.0
  inf_mapper_lambda: 0.0
IT:
  add_it: false
  layers: []
  test_n: 1
  noise_level: 0.0
  window: 0
  vt_sample_n: 1
  mid_dim: 1024
```

每层运行时自动派生：

```text
generated_configs/qwen2.5-vl-7b-bridge-request-only-l00.yaml
...
generated_configs/qwen2.5-vl-7b-bridge-request-only-l27.yaml
```

自检条件：

```text
edit_layers == [当前层号]
edit_text_layers == []
IT.add_it == false
inf_mapper_lambda == 0.0
```

## 6. 动态分辨率控制

Qwen2.5-VL 的视觉 token 数量会随输入图像分辨率变化。为了让层间比较干净，本实验固定图像预处理口径。

建议主实验设置：

```text
min_pixels = 448 * 448
max_pixels = 448 * 448
```

如果代码中无法直接固定为 448，应在 qwen wrapper 中显式记录实际视觉 token 数，并在实验日志中写入：

```text
image_size / min_pixels / max_pixels
visual_token_count
processor 参数
```

不允许在同一轮 sweep 中混用不同分辨率策略。

## 7. 训练规则

每层独立训练：

```text
batch_size=1
random_seed=42
save_ckpt_per_i=30
log_per_i=10
ema_alpha=0.1
data_buffer_size=4
```

目标 checkpoint：

```text
target_loss = 0.0003
tolerance   = 0.0001
可接受范围：0.0002 <= ema_loss <= 0.0004
```

训练流程：

```text
1. 每层先训练 100 epoch。
2. 每轮训练结束后检查 checkpoint 文件名中的 ema_loss。
3. 若命中 0.0003 +/- 0.0001，标记 ACCEPT，保留 selected checkpoint，进入下一层。
4. 若未命中，继续补训 20 epoch。
5. 一直补训到命中目标，或达到 700 epoch。
6. 到 700 epoch 仍未命中，标记 MISS_TARGET，选择现有 checkpoint 中最接近 0.0003 的 checkpoint。
7. 如果出现 No space left / PytorchStreamWriter / checkpoint 写入失败，清理本层非 selected、非 latest checkpoint 后继续。
```

checkpoint 选择：

```text
selection=target0003
优先 exact 0.0003
否则选 abs(ema_loss - 0.0003) 最小者
```

## 8. 单层 smoke 训练

先跑 layer 0 的小规模训练，确认数据加载、图像处理、adapter 挂载和 checkpoint 保存都正常：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct

python scripts/run_bridge_visual_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers 0 \
  --epochs 1 \
  --max_epochs 1 \
  --base_config configs/vead/qwen2.5-vl-7b-bridge-request-only-l14.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT/smoke_l0" \
  --train_name_prefix bridge_request_only_qwen25vl \
  --save_ckpt_per_i 30 \
  --data_n 1 \
  --skip_eval
```

说明：如果 `scripts/run_bridge_visual_layer_sweep.py` 尚未存在，需要从 LLaVA / InstructBLIP 的 request-only sweep 脚本改造，要求支持任意 `edit_model_name`、`edit_layers=[L]` 和 `generated_configs`。

## 9. 全层自动训练

正式训练 0-27 层：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
mkdir -p "$OUT"

nohup python scripts/run_bridge_visual_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers $(seq 0 27) \
  --epochs 100 \
  --max_epochs 700 \
  --continue_increment 20 \
  --target_loss 0.0003 \
  --target_tolerance 0.0001 \
  --train_until_target \
  --prune_checkpoints_during_train \
  --cleanup_unselected_checkpoints \
  --cleanup_layer_cache \
  --retain_recent_checkpoints 1 \
  --retain_epoch_interval 100 \
  --base_config configs/vead/qwen2.5-vl-7b-bridge-request-only-l14.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_request_only_qwen25vl \
  --save_ckpt_per_i 30 \
  --log_per_i 10 \
  --ema_alpha 0.1 \
  --random_seed 42 \
  --data_buffer_size 4 \
  --selection_modes target0003 \
  --skip_eval \
  > "$OUT/full_layer_target0003_sweep.log" 2>&1 &
```

从指定层恢复：

```bash
LAYERS="12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27"

nohup python scripts/run_bridge_visual_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers $LAYERS \
  --epochs 100 \
  --max_epochs 700 \
  --continue_increment 20 \
  --target_loss 0.0003 \
  --target_tolerance 0.0001 \
  --train_until_target \
  --prune_checkpoints_during_train \
  --cleanup_unselected_checkpoints \
  --cleanup_layer_cache \
  --retain_recent_checkpoints 1 \
  --retain_epoch_interval 100 \
  --base_config configs/vead/qwen2.5-vl-7b-bridge-request-only-l14.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_request_only_qwen25vl \
  --selection_modes target0003 \
  --skip_eval \
  >> "$OUT/full_layer_target0003_sweep.log" 2>&1 &
```

## 10. 统一评测

所有层都有 selected checkpoint 后，统一运行 Same-Entity Full Metrics：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct

nohup bash scripts/eval_bridge_visual_full_metrics_sweep.sh \
  --out_root "$OUT" \
  --eval_data /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json \
  --selection_modes target0003 \
  --device cuda:0 \
  --layers "$(seq 0 27)" \
  --bridge_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --model_name Qwen2.5-VL-7B-Instruct \
  --python_bin python \
  > "$OUT/full_layer_target0003_eval.log" 2>&1 &
```

评测输出：

```text
$OUT/target0003_ckpt_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/target0003_full_metrics_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/layer_{L}/target0003/eval_manifest.json
```

预期样本数：

```text
request=30
generality.text_rephrase=30
generality.image_rephrase=66
locality.text_loc=30
locality.image_loc=30
portability=62
```

如果样本数不一致，先停止评测并检查数据集落盘。

## 11. 进度监控

查看训练或评测进程：

```bash
pgrep -af 'run_bridge_visual_layer_sweep.py|bridge_train_request_only.py|eval_bridge_visual_full_metrics|qwen'
```

查看 GPU：

```bash
nvidia-smi
```

查看训练日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
tail -f "$OUT/full_layer_target0003_sweep.log"
```

查看评测日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
tail -f "$OUT/full_layer_target0003_eval.log"
```

统计 selected checkpoint：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
find "$OUT" -name checkpoint_inventory.json -type f | wc -l
test -f "$OUT/target0003_ckpt_summary.tsv" && wc -l "$OUT/target0003_ckpt_summary.tsv"
```

统计评测完成层数：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
find "$OUT/eval_same_entity_full_metrics_rephrase_split" -name eval_manifest.json -type f | wc -l
test -f "$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv" && \
  tail -5 "$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv"
```

检查 generated yaml：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
grep -R "edit_layers\|edit_text_layers\|add_it" "$OUT/generated_configs" | head -80
```

## 12. 磁盘保护与异常处理

自动清理原则：

```text
命中目标后，本层只保留 selected checkpoint。
未命中目标时，只保留 latest、best、closest-target、少量断点 checkpoint。
每层结束后清理 cache。
训练完成后清理 unselected checkpoints。
```

遇到磁盘满：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct
du -h --max-depth=2 "$OUT" | sort -h | tail -40
find "$OUT" -path "*/checkpoints/epoch-*" -type f | wc -l
```

只允许删除：

```text
非 selected checkpoint
非 latest 断点 checkpoint
cache 目录
临时 eval 输出
损坏且无法 torch.load 的 checkpoint
```

不能删除：

```text
target0003_ckpt_summary.tsv/json
selected checkpoint
eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
最终结果 md
```

## 13. 训练与评测结果回填

评测已完成并回填。本节记录 Qwen2.5-VL-7B-Instruct 视觉编辑器逐层 sweep 的 selected checkpoint 与 Same-Entity Full Metrics 结果。

- 完成时间：`2026-05-21 16:19:53`
- 训练/评测远端目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct`
- 评测输出目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct/eval_same_entity_full_metrics_rephrase_split`
- 评测汇总 TSV：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv`
- 评测日志：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct/launch_qwen25vl_eval_20260521_153226.log`
- selected checkpoint：`28/28`
- eval manifest：`28/28`
- 评测数据：`/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json`
- 样本构成：`request=30`，`generality.text_rephrase=30`，`generality.image_rephrase=66`，`locality.text_loc=30`，`locality.image_loc=30`，`portability=62`

### 13.1 Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
| ---: | --- | ---: | ---: | ---: | --- |
| 0 | ACCEPT | 26 | 0.0004 | 0.0001 | `epoch-26-i-780-ema_loss-0.0004` |
| 1 | ACCEPT | 28 | 0.0004 | 0.0001 | `epoch-28-i-840-ema_loss-0.0004` |
| 2 | ACCEPT | 28 | 0.0004 | 0.0001 | `epoch-28-i-840-ema_loss-0.0004` |
| 3 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 4 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 5 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 6 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 7 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 8 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 9 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 10 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 11 | ACCEPT | 26 | 0.0004 | 0.0001 | `epoch-26-i-780-ema_loss-0.0004` |
| 12 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 13 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 14 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 15 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 16 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 17 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 18 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 19 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` |
| 20 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 21 | ACCEPT | 42 | 0.0004 | 0.0001 | `epoch-42-i-1260-ema_loss-0.0004` |
| 22 | ACCEPT | 50 | 0.0004 | 0.0001 | `epoch-50-i-1500-ema_loss-0.0004` |
| 23 | ACCEPT | 59 | 0.0004 | 0.0001 | `epoch-59-i-1770-ema_loss-0.0004` |
| 24 | ACCEPT | 75 | 0.0004 | 0.0001 | `epoch-75-i-2250-ema_loss-0.0004` |
| 25 | ACCEPT | 100 | 0.0004 | 0.0001 | `epoch-100-i-3000-ema_loss-0.0004` |
| 26 | ACCEPT | 291 | 0.0004 | 0.0001 | `epoch-291-i-8730-ema_loss-0.0004` |
| 27 | MISS_TARGET | 92 | 1.5717 | 1.5714 | `epoch-92-i-2760-ema_loss-1.5717` |

### 13.2 Same-Entity Full Metrics Evaluation Results

| Layer | Eval Status | Ckpt Status | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | Port-1 | Port-2 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | done | ACCEPT | 1.0000 | 0.9463 | 0.9097 | 0.9630 | 0.8419 | 1.0000 | 0.6839 | 0.3969 | 0.3865 | 0.4081 |
| 1 | done | ACCEPT | 1.0000 | 0.9617 | 0.9478 | 0.9680 | 0.7925 | 1.0000 | 0.5850 | 0.4179 | 0.4206 | 0.4149 |
| 2 | done | ACCEPT | 1.0000 | 0.9559 | 0.9381 | 0.9640 | 0.8350 | 1.0000 | 0.6700 | 0.4016 | 0.3839 | 0.4205 |
| 3 | done | ACCEPT | 1.0000 | 0.9404 | 0.8839 | 0.9660 | 0.8503 | 1.0000 | 0.7006 | 0.4090 | 0.3708 | 0.4496 |
| 4 | done | ACCEPT | 1.0000 | 0.9636 | 0.9669 | 0.9621 | 0.8503 | 1.0000 | 0.7006 | 0.3956 | 0.3896 | 0.4020 |
| 5 | done | ACCEPT | 1.0000 | 0.9441 | 0.9075 | 0.9607 | 0.8058 | 1.0000 | 0.6117 | 0.4128 | 0.3969 | 0.4297 |
| 6 | done | ACCEPT | 1.0000 | 0.9432 | 0.9047 | 0.9607 | 0.7803 | 1.0000 | 0.5606 | 0.4247 | 0.4135 | 0.4367 |
| 7 | done | ACCEPT | 1.0000 | 0.9448 | 0.9503 | 0.9423 | 0.8267 | 1.0000 | 0.6533 | 0.4034 | 0.3792 | 0.4292 |
| 8 | done | ACCEPT | 1.0000 | 0.9529 | 0.9375 | 0.9600 | 0.8808 | 1.0000 | 0.7617 | 0.3846 | 0.3602 | 0.4106 |
| 9 | done | ACCEPT | 1.0000 | 0.9478 | 0.9317 | 0.9552 | 0.8378 | 1.0000 | 0.6756 | 0.4040 | 0.3974 | 0.4111 |
| 10 | done | ACCEPT | 1.0000 | 0.9216 | 0.8631 | 0.9482 | 0.8517 | 1.0000 | 0.7033 | 0.3902 | 0.4055 | 0.3740 |
| 11 | done | ACCEPT | 1.0000 | 0.9285 | 0.8650 | 0.9573 | 0.7858 | 1.0000 | 0.5717 | 0.4357 | 0.4404 | 0.4307 |
| 12 | done | ACCEPT | 1.0000 | 0.9325 | 0.8875 | 0.9530 | 0.7864 | 1.0000 | 0.5728 | 0.3996 | 0.3810 | 0.4195 |
| 13 | done | ACCEPT | 1.0000 | 0.9433 | 0.9222 | 0.9529 | 0.7900 | 1.0000 | 0.5800 | 0.4241 | 0.4424 | 0.4046 |
| 14 | done | ACCEPT | 1.0000 | 0.9464 | 0.9308 | 0.9535 | 0.8253 | 1.0000 | 0.6506 | 0.4123 | 0.4086 | 0.4162 |
| 15 | done | ACCEPT | 1.0000 | 0.9422 | 0.9203 | 0.9521 | 0.7594 | 1.0000 | 0.5189 | 0.4140 | 0.4148 | 0.4131 |
| 16 | done | ACCEPT | 1.0000 | 0.9519 | 0.9433 | 0.9558 | 0.8261 | 1.0000 | 0.6522 | 0.3893 | 0.3784 | 0.4010 |
| 17 | done | ACCEPT | 1.0000 | 0.9510 | 0.9392 | 0.9564 | 0.7567 | 1.0000 | 0.5133 | 0.4221 | 0.4357 | 0.4076 |
| 18 | done | ACCEPT | 1.0000 | 0.9416 | 0.9297 | 0.9469 | 0.8261 | 1.0000 | 0.6522 | 0.3904 | 0.3891 | 0.3919 |
| 19 | done | ACCEPT | 1.0000 | 0.9372 | 0.8872 | 0.9600 | 0.8133 | 1.0000 | 0.6267 | 0.3945 | 0.3930 | 0.3962 |
| 20 | done | ACCEPT | 1.0000 | 0.9032 | 0.7894 | 0.9549 | 0.8239 | 1.0000 | 0.6478 | 0.3969 | 0.3706 | 0.4249 |
| 21 | done | ACCEPT | 1.0000 | 0.9035 | 0.7722 | 0.9631 | 0.8711 | 1.0000 | 0.7422 | 0.3941 | 0.3802 | 0.4090 |
| 22 | done | ACCEPT | 1.0000 | 0.8955 | 0.7422 | 0.9652 | 0.7761 | 1.0000 | 0.5522 | 0.3869 | 0.3836 | 0.3905 |
| 23 | done | ACCEPT | 1.0000 | 0.8960 | 0.7539 | 0.9606 | 0.7300 | 1.0000 | 0.4600 | 0.3915 | 0.3911 | 0.3918 |
| 24 | done | ACCEPT | 1.0000 | 0.9165 | 0.8142 | 0.9630 | 0.8989 | 1.0000 | 0.7978 | 0.3606 | 0.3576 | 0.3639 |
| 25 | done | ACCEPT | 1.0000 | 0.9292 | 0.8375 | 0.9709 | 0.8583 | 1.0000 | 0.7167 | 0.3672 | 0.3583 | 0.3766 |
| 26 | done | ACCEPT | 0.9958 | 0.9632 | 0.9186 | 0.9835 | 0.8361 | 1.0000 | 0.6722 | 0.3626 | 0.3779 | 0.3463 |
| 27 | done | MISS_TARGET | 0.6708 | 0.6843 | 0.6077 | 0.7190 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 |

### 13.3 Quick Winners

| Metric | Raw Best Layer | Raw Best Acc | Effective Best Layer | Effective Best Acc |
| --- | ---: | ---: | ---: | ---: |
| Request sanity | 0 | 1.0000 | 0 | 1.0000 |
| Generality | 4 | 0.9636 | 4 | 0.9636 |
| Locality | 27 | 1.0000 | 24 | 0.8989 |
| Portability | 11 | 0.4357 | 11 | 0.4357 |
| CoreAvg4 mean(req/gen/loc/port) | 8 | 0.8046 | 8 | 0.8046 |

### 13.4 Notes

- MISS_TARGET 层：layer 27=MISS_TARGET / epoch 92 / ema_loss 1.5717。
- 有效最佳层口径：只统计 selected checkpoint 为 ACCEPT，且 request_acc >= 0.9、generality_acc >= 0.8 的层；避免把编辑失败后的保守 locality 当作 golden layer。
- 本次 Qwen2.5-VL-7B-Instruct decoder 扫描层数为 28 层，即 layer 0-27。

## 14. 分析口径

最终结论至少回答：

```text
1. Qwen2.5-VL visual-only 的最佳 generality 层是哪一层？
2. 最佳层归一化深度 layer / 27 是多少？
3. 是否落在 MLP / 线性投影型预期浅层区间 [0.0, 0.35]？
4. Qwen2.5-VL 与 LLaVA 的视觉 golden layer 是否一致？
5. 有效 locality 最高层是哪一层？
6. portability 最高层是哪一层？
7. 末层是否出现 MISS_TARGET / zero-grad / 编辑失败，与 LLaVA/BLIP2 是否一致？
```

主轴：

```text
O_generality  = generality
O_portability = portability
O_locality    = locality
O_request     = request sanity
```

有效最佳层不要只看 locality。若某层 request/generality 很低但 locality 很高，通常代表编辑失败后的保守行为，不应作为有效 golden layer。

## 15. 当前状态

```text
文档状态：已回填 Qwen2.5-VL-7B-Instruct 视觉编辑器全层扫层结果。
模型状态：已下载到 VisEdit-main/models/Qwen2.5-VL-7B-Instruct，并完成 safetensors 完整性检查。
训练状态：layer 0-26 达到目标 loss；layer 27 未达到目标 loss，按当前最接近 checkpoint 进入评测。
评测状态：Same-Entity Full Metrics 已完成，完成时间 2026-05-21 16:19:53。
下一步：结合 LGA 指标与跨模型结构表分析 Qwen2.5-VL 的视觉 golden layer。
```

