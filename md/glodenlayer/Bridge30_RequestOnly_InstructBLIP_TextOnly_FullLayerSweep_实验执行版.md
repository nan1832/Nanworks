# Bridge30 Request-Only InstructBLIP Text-Only Full Layer Sweep 实验执行版

## 0. 实验目标

本实验用于验证 InstructBLIP-Vicuna-7B 在 Bridge30 request-only 场景下，文本 adapter 挂载到不同 Vicuna decoder 层时的编辑效果差异。

核心问题：

```text
在只用 request 训练、Same-Entity Full Metrics 统一评测的口径下，
InstructBLIP 的文本编辑器 golden layer 位于哪一层？
它是否像 BLIP2 一样偏中后层，还是更接近 LLaVA/Vicuna 的浅中层？
```

本实验与已有视觉编辑器扫层严格成对：

```text
visual-only: edit_layers=[L], edit_text_layers=[]   -> 视觉表征编辑层
text-only:   edit_layers=[],  edit_text_layers=[L]  -> 文本表征编辑层
```

约束：

```text
原始 json/jsonl 不更改。
训练集只用纯 request 文件。
generality/locality/portability 只用于评测。
评测额外保留 request acc，作为 sanity acc。
文本编辑器不打开 IM/IT 模块，不引入 influence mapper / IT 噪声。
每层命中目标 loss 后只保留 selected checkpoint；未命中则补训，最多到 700 epoch。
```

## 1. 与已有实验的对应关系

参考实验：

```text
md/glodenlayer/Bridge30_RequestOnly_TextOnly_FullLayerSweep_实验执行版.md
```

已有结果：

```text
LLaVA text-only: 推荐文本层 7
BLIP2 text-only: 推荐文本层 16/17
```

本实验新增模型：

```text
InstructBLIP-Vicuna-7B
架构类型：Q-Former + Vicuna decoder
decoder 层数：32
扫层范围：0-31
```

解释重点：

```text
BLIP2 与 InstructBLIP 都有 Q-Former，但文本 decoder 不同：
BLIP2:        Q-Former -> OPT decoder
InstructBLIP: Q-Former -> Vicuna decoder

如果 InstructBLIP text golden layer 接近 BLIP2，说明 Q-Former 桥接机制可能主导文本编辑层位置。
如果更接近 LLaVA，说明 Vicuna decoder backbone 可能主导文本编辑层位置。
```

## 2. 服务器路径

推荐沿用已有文本编辑器代码路径：

```text
服务器节点：g07
项目目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main

输出目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
```

模型路径：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/instructblip-vicuna-7b
```

说明：

```text
InstructBLIP 视觉扫层代码已经在 VisEdit-main 适配。
但已有 text-only sweep 使用 DualEdit-main，因为 DualEdit-main 的 VEAD 已支持 edit_text_layers。
因此本实验优先方案是：把 InstructBLIP loader/model map 从 VisEdit-main 移植到 DualEdit-main。
不要直接使用视觉扫层 yaml 运行文本编辑器，因为视觉 yaml 只控制 edit_layers。
```

## 3. 数据口径

训练集使用纯 request 文件：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json
```

训练阶段只使用：

```text
request.image
request.prompt
request.target_new
```

训练阶段不使用：

```text
generality
locality
portability
```

统一评测集使用 Same-Entity Full Metrics rephrase_split：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

评测指标：

```text
request acc      = 训练 request sanity acc
generality acc   = val generality，同实体泛化
locality acc     = val locality，局部性
portability acc  = val portability，可迁移性
```

预期样本数应与 LLaVA/BLIP2 text-only 和 visual-only 一致：

```text
request=30
generality.text_rephrase=30
generality.image_rephrase=66
locality.text_loc=30
locality.image_loc=30
portability=62
```

如果评测日志中的样本数不一致，先停止评测并检查数据落盘。

## 4. 前置代码适配检查

DualEdit-main 当前文本编辑器链路需要支持 InstructBLIP：

```text
editor/vllms_for_edit/instructblip/instructblip.py
editor/vllms_for_edit/instructblip/__init__.py
editor/vllms_for_edit/__init__.py
utils/GLOBAL.py
utils/__init__.py
configs/vead/instructblip-vicuna-7b-bridge-text-only-l16.yaml
```

可从已经适配过的 VisEdit-main 复制 InstructBLIP wrapper，并确认 DualEdit-main 中：

```text
get_full_model_name("instructblip-vicuna-7b") 可返回 instructblip-vicuna-7b
load_vllm_for_edit("instructblip-vicuna-7b", "cuda:0") 可正常加载模型
模型对象包含 language_model.model.layers.0-31
```

hook 位置必须与真实文本 adapter 训练位置一致：

```text
文本 adapter 挂在 Vicuna decoder 的 language_model.model.layers.{L}
本实验不挂 Q-Former 层，不挂 vision encoder 层。
```

smoke 检查：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH

/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 - <<'PY'
from utils import load_vllm_for_edit
m = load_vllm_for_edit("instructblip-vicuna-7b", "cuda:0")
print(type(m.model))
print(len(m.model.language_model.model.layers))
print(m.model.language_model.model.layers[0].__class__)
print(m.model.language_model.model.layers[31].__class__)
PY
```

必须输出 32 层后，再进入训练。

## 5. YAML 模板

基础配置文件：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main/configs/vead/instructblip-vicuna-7b-bridge-text-only-l16.yaml
```

核心内容：

```yaml
edit_model_name: "instructblip-vicuna-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"
edit_layers: []
edit_text_layers: [16]
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

说明：

```text
edit_layers=[]：不挂视觉 adapter。
edit_text_layers=[L]：只挂单层文本 adapter。
IT.add_it=false：文本编辑器不打开 IM/IT 模块。
inf_mapper_lambda=0.0：不使用 influence mapper 信号。
gen_lambda/loc_lambda 虽保留为 1.0，但训练数据是纯 request 文件，实际没有 generality/locality 训练样本进入监督。
```

每层配置由 sweep 脚本自动从 l16 模板生成：

```text
generated_configs/instructblip-vicuna-7b-bridge-text-only-l00.yaml
...
generated_configs/instructblip-vicuna-7b-bridge-text-only-l31.yaml
```

自检条件：

```text
每个 generated yaml 中必须满足：
edit_layers == []
edit_text_layers == [当前层号]
IT.add_it == false
```

## 6. 训练规则

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
7. 报 No space left / PytorchStreamWriter / checkpoint 写入失败时，清理本层非 selected、非 latest checkpoint 后继续。
```

checkpoint 选择：

```text
selection=target0003
优先 exact 0.0003
否则选 abs(ema_loss - 0.0003) 最小者
```

## 7. 单层 smoke 训练命令

先跑 layer 0 的小规模 smoke：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip

/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 scripts/run_bridge_text_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers 0 \
  --epochs 1 \
  --max_epochs 1 \
  --base_config configs/vead/instructblip-vicuna-7b-bridge-text-only-l16.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT/smoke_l0" \
  --train_name_prefix bridge_text_only_instructblip \
  --save_ckpt_per_i 30 \
  --data_n 1 \
  --skip_eval
```

通过标准：

```text
模型能加载
文本 adapter 能初始化到 edit_text_layers=[0]
能完成 1 epoch
records 目录下产生 checkpoint
```

## 8. 全层自动训练命令

正式训练 0-31 层：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
mkdir -p "$OUT"

nohup /datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 scripts/run_bridge_text_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers $(seq 0 31) \
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
  --base_config configs/vead/instructblip-vicuna-7b-bridge-text-only-l16.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_text_only_instructblip \
  --save_ckpt_per_i 30 \
  --log_per_i 10 \
  --ema_alpha 0.1 \
  --random_seed 42 \
  --data_buffer_size 4 \
  --selection_modes target0003 \
  --skip_eval \
  > "$OUT/full_layer_text_only_sweep.log" 2>&1 &
```

说明：

```text
这里训练阶段 skip_eval，只做训练和 checkpoint 选择。
所有层 selected checkpoint 准备好后，再统一做 Same-Entity Full Metrics 评测。
```

如果从某一层恢复：

```bash
LAYERS="12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31"

nohup /datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 scripts/run_bridge_text_layer_sweep.py \
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
  --base_config configs/vead/instructblip-vicuna-7b-bridge-text-only-l16.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_text_only_instructblip \
  --selection_modes target0003 \
  --skip_eval \
  >> "$OUT/full_layer_text_only_sweep.log" 2>&1 &
```

## 9. 统一评测命令

评测使用同一个 Same-Entity Full Metrics 数据集：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip

nohup bash scripts/eval_bridge_text_only_full_metrics_sweep.sh \
  --out_root "$OUT" \
  --eval_data /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json \
  --selection_modes target0003 \
  --device cuda:0 \
  --layers "$(seq 0 31)" \
  --bridge_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --model_name instructblip-vicuna-7b \
  --python_bin /datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11 \
  > "$OUT/full_layer_text_only_eval.log" 2>&1 &
```

输出文件：

```text
$OUT/target0003_ckpt_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/target0003_full_metrics_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/layer_{L}/target0003/eval_manifest.json
```

## 10. 进度监控

查看训练或评测进程：

```bash
pgrep -af 'run_bridge_text_layer_sweep.py|bridge_text_adapter_train.py|eval_bridge_text_only_full_metrics.py|instructblip'
```

查看 GPU：

```bash
nvidia-smi
```

查看训练日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
tail -f "$OUT/full_layer_text_only_sweep.log"
```

查看评测日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
tail -f "$OUT/full_layer_text_only_eval.log"
```

统计 selected checkpoint：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
find "$OUT" -name checkpoint_inventory.json -type f | wc -l
test -f "$OUT/target0003_ckpt_summary.tsv" && wc -l "$OUT/target0003_ckpt_summary.tsv"
```

统计评测完成层数：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
find "$OUT/eval_same_entity_full_metrics_rephrase_split" -name eval_manifest.json -type f | wc -l
test -f "$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv" && \
  tail -5 "$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv"
```

检查 generated yaml：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
grep -R "edit_layers\\|edit_text_layers\\|add_it" "$OUT/generated_configs" | head -80
```

## 11. 磁盘保护与异常处理

自动清理原则：

```text
命中目标后，本层仅保留 selected checkpoint。
未命中目标时，仅保留 latest、best、closest-target、少量断点 checkpoint。
每层结束后清理 cache。
训练完成后清理 unselected checkpoints。
```

遇到磁盘满：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/instructblip
du -h --max-depth=2 "$OUT" | sort -h | tail -40
find "$OUT" -path "*/checkpoints/epoch-*" -type f | wc -l
```

只允许删除：

```text
非 selected checkpoint
非 latest 断点 checkpoint
cache 目录
临时 eval 输出
```

不能删除：

```text
target0003_ckpt_summary.tsv/json
selected checkpoint
eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
最终结果 md
```

## 12. 结果回填格式

实验结束后，将远端结果拉回并追加到文档末尾的结果区。当前 InstructBLIP text-only 结果已完成回填，见 `REQUEST_ONLY_INSTRUCTBLIP_TEXT_SWEEP_RESULTS` 标记之间的内容。

需要回填两张表：

- `Selected Checkpoints`
- `Same-Entity Full Metrics`
## 13. 分析口径

最终结论至少回答：

```text
1. InstructBLIP text-only 的最佳 generality 层是哪一层？
2. InstructBLIP text-only 的最佳有效 locality 层是哪一层？
3. InstructBLIP text-only 的最佳 portability 层是哪一层？
4. 以 core average = mean(request, generality, locality, portability) 作为平衡指标，最佳层是哪一层？
5. InstructBLIP text golden layer 与 BLIP2 text golden layer 16/17 是否一致？
6. InstructBLIP text golden layer 与 InstructBLIP visual golden layer 是否分离？
7. MISS_TARGET 是否集中在末层，是否与 LLaVA/BLIP2 text-only 的 layer 31 失败现象一致？
```

建议同时报告：

```text
浅层：0-7
中层：8-23
尾层：24-31
```

若出现 generality 大面积 1.0000 平台，不能只按 generality 选层，必须结合：

```text
request sanity acc
locality acc
portability acc
训练是否 ACCEPT
所需 epoch
```

## 14. 当前状态

```text
文档状态：已创建 InstructBLIP text-only 全层扫层执行手册。
下一步：
1. 确认 DualEdit-main 已支持 InstructBLIP loader。
2. 创建 instructblip-vicuna-7b-bridge-text-only-l16.yaml。
3. 跑 layer 0 smoke。
4. 全层训练 0-31。
5. Same-Entity Full Metrics 统一评测。
6. 将 selected checkpoint 与评测结果回填到第 12 节。
```

<!-- REQUEST_ONLY_INSTRUCTBLIP_TEXT_SWEEP_RESULTS_START -->

### 12.1 Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
|---:|---|---:|---:|---:|---|
| 0 | ACCEPT | 58 | 0.0003 | 0.0000 | `epoch-58-i-1740-ema_loss-0.0003` |
| 1 | ACCEPT | 44 | 0.0004 | 0.0001 | `epoch-44-i-1320-ema_loss-0.0004` |
| 2 | ACCEPT | 58 | 0.0003 | 0.0000 | `epoch-58-i-1740-ema_loss-0.0003` |
| 3 | ACCEPT | 41 | 0.0004 | 0.0001 | `epoch-41-i-1230-ema_loss-0.0004` |
| 4 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 5 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 6 | ACCEPT | 44 | 0.0004 | 0.0001 | `epoch-44-i-1320-ema_loss-0.0004` |
| 7 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 8 | ACCEPT | 41 | 0.0004 | 0.0001 | `epoch-41-i-1230-ema_loss-0.0004` |
| 9 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 10 | ACCEPT | 58 | 0.0004 | 0.0001 | `epoch-58-i-1740-ema_loss-0.0004` |
| 11 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 12 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 13 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 14 | ACCEPT | 43 | 0.0004 | 0.0001 | `epoch-43-i-1290-ema_loss-0.0004` |
| 15 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` |
| 16 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 17 | ACCEPT | 43 | 0.0004 | 0.0001 | `epoch-43-i-1290-ema_loss-0.0004` |
| 18 | ACCEPT | 56 | 0.0004 | 0.0001 | `epoch-56-i-1680-ema_loss-0.0004` |
| 19 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 20 | ACCEPT | 58 | 0.0004 | 0.0001 | `epoch-58-i-1740-ema_loss-0.0004` |
| 21 | ACCEPT | 56 | 0.0004 | 0.0001 | `epoch-56-i-1680-ema_loss-0.0004` |
| 22 | ACCEPT | 58 | 0.0004 | 0.0001 | `epoch-58-i-1740-ema_loss-0.0004` |
| 23 | ACCEPT | 68 | 0.0004 | 0.0001 | `epoch-68-i-2040-ema_loss-0.0004` |
| 24 | ACCEPT | 78 | 0.0004 | 0.0001 | `epoch-78-i-2340-ema_loss-0.0004` |
| 25 | ACCEPT | 80 | 0.0004 | 0.0001 | `epoch-80-i-2400-ema_loss-0.0004` |
| 26 | ACCEPT | 100 | 0.0004 | 0.0001 | `epoch-100-i-3000-ema_loss-0.0004` |
| 27 | ACCEPT | 103 | 0.0004 | 0.0001 | `epoch-103-i-3090-ema_loss-0.0004` |
| 28 | ACCEPT | 115 | 0.0004 | 0.0001 | `epoch-115-i-3450-ema_loss-0.0004` |
| 29 | ACCEPT | 273 | 0.0004 | 0.0001 | `epoch-273-i-8190-ema_loss-0.0004` |
| 30 | MISS_TARGET | 656 | 0.0016 | 0.0013 | `epoch-656-i-19680-ema_loss-0.0016` |
| 31 | MISS_TARGET | 108 | 4.5286 | 4.5283 | `epoch-108-i-3240-ema_loss-4.5286` |

### 12.2 Same-Entity Full Metrics

| Layer | Status | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | 1-hop | 2-hop |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | ACCEPT | 1.0000 | 0.9965 | 1.0000 | 0.9949 | 0.9833 | 1.0000 | 0.9667 | 0.3524 | 0.3922 | 0.3100 |
| 1 | ACCEPT | 1.0000 | 0.9620 | 0.9708 | 0.9579 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 2 | ACCEPT | 1.0000 | 0.9924 | 1.0000 | 0.9890 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 3 | ACCEPT | 1.0000 | 0.9890 | 0.9786 | 0.9937 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 4 | ACCEPT | 1.0000 | 0.9896 | 1.0000 | 0.9848 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 5 | ACCEPT | 1.0000 | 0.9832 | 0.9917 | 0.9793 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 6 | ACCEPT | 1.0000 | 0.9906 | 1.0000 | 0.9864 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 7 | ACCEPT | 1.0000 | 0.9558 | 0.9261 | 0.9693 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 8 | ACCEPT | 1.0000 | 0.9689 | 0.9650 | 0.9707 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 9 | ACCEPT | 1.0000 | 0.9677 | 0.9667 | 0.9681 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 10 | ACCEPT | 1.0000 | 0.9612 | 0.9483 | 0.9671 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 11 | ACCEPT | 1.0000 | 0.9752 | 0.9692 | 0.9780 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 12 | ACCEPT | 1.0000 | 0.9705 | 0.9519 | 0.9789 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 13 | ACCEPT | 1.0000 | 0.9683 | 0.9274 | 0.9869 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 14 | ACCEPT | 1.0000 | 0.9121 | 0.7846 | 0.9701 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 15 | ACCEPT | 1.0000 | 0.9162 | 0.7868 | 0.9750 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 16 | ACCEPT | 1.0000 | 0.9043 | 0.7304 | 0.9833 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 17 | ACCEPT | 1.0000 | 0.9074 | 0.7203 | 0.9924 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 18 | ACCEPT | 1.0000 | 0.8822 | 0.6564 | 0.9848 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 19 | ACCEPT | 1.0000 | 0.9125 | 0.7200 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 20 | ACCEPT | 1.0000 | 0.9104 | 0.7134 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 21 | ACCEPT | 1.0000 | 0.9094 | 0.7100 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 22 | ACCEPT | 1.0000 | 0.9088 | 0.7137 | 0.9975 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 23 | ACCEPT | 1.0000 | 0.9138 | 0.7240 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 24 | ACCEPT | 1.0000 | 0.9124 | 0.7197 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 25 | ACCEPT | 1.0000 | 0.9112 | 0.7158 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 26 | ACCEPT | 1.0000 | 0.9061 | 0.6995 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 27 | ACCEPT | 1.0000 | 0.9056 | 0.6981 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 28 | ACCEPT | 1.0000 | 0.9138 | 0.7242 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 29 | ACCEPT | 1.0000 | 0.9621 | 0.8788 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 30 | MISS_TARGET | 1.0000 | 0.9545 | 0.8544 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |
| 31 | MISS_TARGET | 0.3080 | 0.3201 | 0.2685 | 0.3435 | 1.0000 | 1.0000 | 1.0000 | 0.3524 | 0.3922 | 0.3100 |

### 12.3 Quick Winners

| Metric | Layer | Score |
|---|---:|---:|
| Best Generality | 0 | 0.9965 |
| Best Locality | 1 | 1.0000 |
| Best Portability | 0 | 0.3524 |
| Best Core Average | 2 | 0.8362 |

<!-- REQUEST_ONLY_INSTRUCTBLIP_TEXT_SWEEP_RESULTS_END -->
