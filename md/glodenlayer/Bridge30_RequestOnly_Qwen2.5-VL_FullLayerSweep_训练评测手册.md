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

## 13. 结果回填格式

实验结束后，将远端结果追加到本节：

```text
<!-- REQUEST_ONLY_QWEN25VL_VISUAL_SWEEP_RESULTS_START -->
...
<!-- REQUEST_ONLY_QWEN25VL_VISUAL_SWEEP_RESULTS_END -->
```

需要回填两张主表。

### 13.1 Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
|---:|---|---:|---:|---:|---|
| 0 | TODO | TODO | TODO | TODO | TODO |

### 13.2 Same-Entity Full Metrics

| Layer | Status | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | 1-hop | 2-hop |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |

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
文档状态：已创建 Qwen2.5-VL-7B-Instruct 视觉编辑器全层扫层手册。
模型状态：已下载到 VisEdit-main/models/Qwen2.5-VL-7B-Instruct，并完成 safetensors 完整性检查。
下一步：
1. 准备支持 Qwen2.5-VL 的 transformers/qwen-vl-utils 环境。
2. 适配 editor/vllms_for_edit/qwen2_5_vl.py。
3. 创建 qwen2.5-vl-7b-bridge-request-only-l14.yaml。
4. 跑 layer 0 smoke。
5. 全层训练 0-27。
6. Same-Entity Full Metrics 统一评测。
7. 将 selected checkpoint 与评测结果回填到第 13 节。
```

<!-- REQUEST_ONLY_QWEN25VL_VISUAL_SWEEP_RESULTS_START -->

待实验完成后回填。

<!-- REQUEST_ONLY_QWEN25VL_VISUAL_SWEEP_RESULTS_END -->
