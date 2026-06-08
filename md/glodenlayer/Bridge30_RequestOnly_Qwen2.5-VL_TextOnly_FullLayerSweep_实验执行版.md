# Bridge30 Request-Only Qwen2.5-VL Text-Only Full Layer Sweep 实验执行版

## 0. 实验目标

本实验用于验证 Qwen2.5-VL-7B-Instruct 在 Bridge30 request-only 场景下，文本 adapter 挂载到不同 Qwen2.5 decoder 层时的编辑效果差异。

核心问题：

```text
在只用 request 训练、Same-Entity Full Metrics 统一评测的口径下，
Qwen2.5-VL 的文本编辑器 golden layer 位于哪一层？
它是否更接近 LLaVA 这类线性投影型模型的浅层文本编辑层，
还是与 Qwen2.5-VL 的视觉编辑层出现明显分离？
```

本实验与 Qwen2.5-VL 视觉编辑器扫层严格成对：

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
md/glodenlayer/Bridge30_RequestOnly_InstructBLIP_TextOnly_FullLayerSweep_实验执行版.md
md/glodenlayer/Bridge30_RequestOnly_Qwen2.5-VL_FullLayerSweep_训练评测手册.md
```

已有结果：

```text
LLaVA text-only: 推荐文本层 7
BLIP2 text-only: 推荐文本层 16/17
InstructBLIP text-only: 推荐文本层 0 / core average 层 2
```

本实验新增模型：

```text
Qwen2.5-VL-7B-Instruct
架构类型：Qwen2.5-VL ViT + MLP / Merger + Qwen2.5 decoder
decoder 层数：28
扫层范围：0-27
```

解释重点：

```text
Qwen2.5-VL 与 LLaVA 都属于非 Q-Former 的视觉-语言连接方式，但 decoder backbone 不同：
LLaVA-v1.5: CLIP ViT -> MLP Projector -> Vicuna decoder
Qwen2.5-VL: Qwen2.5-VL ViT -> Merger/Projection -> Qwen2.5 decoder

如果 Qwen2.5 text golden layer 接近 LLaVA 的浅层，说明线性投影/直接视觉 token 注入结构可能主导文本编辑层位置。
如果 Qwen2.5 text golden layer 与 Qwen2.5 visual golden layer 明显分离，说明视觉表征编辑与文本表征编辑在同一架构内仍对应不同层位。
```

## 2. 服务器路径

推荐优先使用已经适配 Qwen2.5-VL 的 VisEdit-main：

```text
服务器节点：g07
项目目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

输出目录：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
```

模型路径：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/Qwen2.5-VL-7B-Instruct
```

环境路径：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl
```

说明：

```text
Qwen2.5-VL 视觉扫层已经在 VisEdit-main 中适配。
本 text-only 实验要求训练脚本支持 edit_text_layers。
如果 VisEdit-main 当前没有 text-only sweep 脚本，应从已有 DualEdit-main text-only 链路移植 run_bridge_text_layer_sweep.py / evaluator，
但模型 loader、Qwen wrapper 和环境优先沿用 VisEdit-main 的 Qwen2.5-VL 适配。
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

预期样本数应与 LLaVA / BLIP2 / InstructBLIP text-only 和 Qwen2.5 visual-only 一致：

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

VisEdit-main 当前文本编辑器链路需要支持 Qwen2.5-VL：

```text
editor/vllms_for_edit/qwen2_5_vl/qwen2_5_vl.py
editor/vllms_for_edit/qwen2_5_vl/__init__.py
editor/vllms_for_edit/__init__.py
utils/GLOBAL.py
utils/__init__.py
configs/vead/qwen2.5-vl-7b-bridge-text-only-l14.yaml
scripts/run_bridge_text_layer_sweep.py
scripts/eval_bridge_text_only_full_metrics_sweep.sh
```

必须确认：

```text
get_full_model_name("qwen2.5-vl-7b-instruct") 可返回 qwen2.5-vl-7b-instruct
load_vllm_for_edit("qwen2.5-vl-7b-instruct", "cuda:0") 可正常加载模型
模型对象包含 model.model.layers.0-27 或 wrapper 暴露 model.layers.0-27
text adapter 挂载到 Qwen2.5 decoder 层，不挂 vision encoder / visual merger 层
```

hook 位置必须与真实 text adapter 训练位置一致：

```text
文本 adapter 挂在 Qwen2.5 decoder 的 model.layers.{L}
本实验不挂视觉层，不挂 vision encoder，不挂 visual merger。
```

smoke 检查：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python - <<'PY'
from utils import load_vllm_for_edit
m = load_vllm_for_edit("qwen2.5-vl-7b-instruct", "cuda:0")
print(type(m.model))
print(len(m.model.model.layers))
print(m.model.model.layers[0].__class__)
print(m.model.model.layers[27].__class__)
PY
```

必须输出 28 层后，再进入训练。

## 5. YAML 模板

基础配置文件建议放在：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/configs/vead/qwen2.5-vl-7b-bridge-text-only-l14.yaml
```

核心内容：

```yaml
edit_model_name: "qwen2.5-vl-7b-instruct"
llm_hidden_size: 3584
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "model.layers.{}"
llm_att_tmp: "model.layers.{}.self_attn"
edit_layers: []
edit_text_layers: [14]
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

每层配置由 sweep 脚本自动从 l14 模板生成：

```text
generated_configs/qwen2.5-vl-7b-bridge-text-only-l00.yaml
...
generated_configs/qwen2.5-vl-7b-bridge-text-only-l27.yaml
```

自检条件：

```text
每个 generated yaml 中必须满足：
edit_layers == []
edit_text_layers == [当前层号]
IT.add_it == false
inf_mapper_lambda == 0.0
```

## 6. 动态分辨率控制

Qwen2.5-VL 的视觉 token 数量会随输入图像分辨率变化。为了让层间比较干净，本实验固定图像预处理口径，与 Qwen2.5 visual-only sweep 保持一致。

主实验设置：

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

不允许在同一轮 text-only sweep 中混用不同分辨率策略。

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
7. 报 No space left / PytorchStreamWriter / checkpoint 写入失败时，清理本层非 selected、非 latest checkpoint 后继续。
```

checkpoint 选择：

```text
selection=target0003
优先 exact 0.0003
否则选 abs(ema_loss - 0.0003) 最小者
```

## 8. 单层 smoke 训练命令

先跑 layer 0 的小规模 smoke：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

PY=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct

$PY scripts/run_bridge_text_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers 0 \
  --epochs 1 \
  --max_epochs 1 \
  --base_config configs/vead/qwen2.5-vl-7b-bridge-text-only-l14.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT/smoke_l0" \
  --train_name_prefix bridge_text_only_qwen25vl \
  --save_ckpt_per_i 30 \
  --data_n 1 \
  --skip_eval
```

通过标准：

```text
模型能加载
文本 adapter 能初始化到 edit_text_layers=[0]
edit_layers 为空
IT.add_it=false
能完成 1 epoch
records 目录下产生 checkpoint
```

## 9. 全层自动训练命令

正式训练 0-27 层：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

PY=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
mkdir -p "$OUT"

nohup $PY scripts/run_bridge_text_layer_sweep.py \
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
  --base_config configs/vead/qwen2.5-vl-7b-bridge-text-only-l14.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_text_only_qwen25vl \
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
LAYERS="12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27"

nohup $PY scripts/run_bridge_text_layer_sweep.py \
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
  --base_config configs/vead/qwen2.5-vl-7b-bridge-text-only-l14.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_text_only_qwen25vl \
  --selection_modes target0003 \
  --skip_eval \
  >> "$OUT/full_layer_text_only_sweep.log" 2>&1 &
```

## 10. 统一评测命令

评测使用同一个 Same-Entity Full Metrics 数据集：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
export PYTHONPATH=$PWD:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

PY=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct

nohup bash scripts/eval_bridge_text_only_full_metrics_sweep.sh \
  --out_root "$OUT" \
  --eval_data /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json \
  --selection_modes target0003 \
  --device cuda:0 \
  --layers "$(seq 0 27)" \
  --bridge_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --model_name qwen2.5-vl-7b-instruct \
  --python_bin "$PY" \
  > "$OUT/full_layer_text_only_eval.log" 2>&1 &
```

输出文件：

```text
$OUT/target0003_ckpt_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/target0003_full_metrics_summary.tsv
$OUT/eval_same_entity_full_metrics_rephrase_split/layer_{L}/target0003/eval_manifest.json
```

## 11. 进度监控

查看训练或评测进程：

```bash
pgrep -af 'run_bridge_text_layer_sweep.py|bridge_text_adapter_train.py|eval_bridge_text_only_full_metrics.py|qwen2.5|qwen25vl'
```

查看 GPU：

```bash
nvidia-smi
```

查看训练日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
tail -f "$OUT/full_layer_text_only_sweep.log"
```

查看评测日志：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
tail -f "$OUT/full_layer_text_only_eval.log"
```

统计 selected checkpoint：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
find "$OUT" -name checkpoint_inventory.json -type f | wc -l
test -f "$OUT/target0003_ckpt_summary.tsv" && wc -l "$OUT/target0003_ckpt_summary.tsv"
```

统计评测完成层数：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
find "$OUT/eval_same_entity_full_metrics_rephrase_split" -name eval_manifest.json -type f | wc -l
test -f "$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv" && \
  tail -5 "$OUT/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv"
```

检查 generated yaml：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
grep -R "edit_layers\|edit_text_layers\|add_it" "$OUT/generated_configs" | head -80
```

## 12. 磁盘保护与异常处理

自动清理原则：

```text
命中目标后，本层仅保留 selected checkpoint。
未命中目标时，仅保留 latest、best、closest-target、少量断点 checkpoint。
每层结束后清理 cache。
训练完成后清理 unselected checkpoints。
```

遇到磁盘满：

```bash
OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/qwen2_5_vl_7b_instruct
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

实验结束后，将远端结果拉回并追加到文档末尾的结果区。

需要回填三张表：

```text
Selected Checkpoints
Same-Entity Full Metrics
Quick Winners
```

结果区使用文档末尾唯一一组 `REQUEST_ONLY_QWEN25VL_TEXT_SWEEP_RESULTS` 标记。自动回填时只替换该标记之间的内容。

## 14. 分析口径

最终结论至少回答：

```text
1. Qwen2.5-VL text-only 的最佳 generality 层是哪一层？
2. Qwen2.5-VL text-only 的最佳有效 locality 层是哪一层？
3. Qwen2.5-VL text-only 的最佳 portability 层是哪一层？
4. 以 core average = mean(request, generality, locality, portability) 作为平衡指标，最佳层是哪一层？
5. Qwen2.5-VL text golden layer 与 LLaVA text golden layer 7 是否一致？
6. Qwen2.5-VL text golden layer 与 Qwen2.5-VL visual golden layer 是否分离？
7. MISS_TARGET 是否集中在末层，是否与 LLaVA/BLIP2/InstructBLIP text-only 的尾层失败现象一致？
```

建议同时报告：

```text
浅层：0-6
中层：7-20
尾层：21-27
```

若出现 generality 大面积 1.0000 平台，不能只按 generality 选层，必须结合：

```text
request sanity acc
locality acc
portability acc
训练是否 ACCEPT
所需 epoch
```

## 15. 当前状态

```text
文档状态：已创建 Qwen2.5-VL text-only 全层扫层执行手册。
下一步：
1. 确认 VisEdit-main 已支持 Qwen2.5-VL 的 text adapter 链路。
2. 创建 qwen2.5-vl-7b-bridge-text-only-l14.yaml。
3. 跑 layer 0 smoke。
4. 全层训练 0-27。
5. Same-Entity Full Metrics 统一评测。
6. 将 selected checkpoint 与评测结果回填到第 13 节结果区。
```

<!-- REQUEST_ONLY_QWEN25VL_TEXT_SWEEP_RESULTS_START -->

Update time: `2026-05-23 09:26:54`

Remote evaluation status: completed. All 28 layers have `eval_manifest.json` and `selected_full_metrics_summary.tsv`.

### Selected Checkpoints

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |
|---:|---|---:|---:|---:|---|
| 0 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 1 | ACCEPT | 60 | 0.0004 | 0.0001 | `epoch-60-i-1800-ema_loss-0.0004` |
| 2 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 3 | ACCEPT | 45 | 0.0004 | 0.0001 | `epoch-45-i-1350-ema_loss-0.0004` |
| 4 | ACCEPT | 49 | 0.0004 | 0.0001 | `epoch-49-i-1470-ema_loss-0.0004` |
| 5 | ACCEPT | 50 | 0.0004 | 0.0001 | `epoch-50-i-1500-ema_loss-0.0004` |
| 6 | ACCEPT | 39 | 0.0004 | 0.0001 | `epoch-39-i-1170-ema_loss-0.0004` |
| 7 | ACCEPT | 31 | 0.0004 | 0.0001 | `epoch-31-i-930-ema_loss-0.0004` |
| 8 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 9 | ACCEPT | 28 | 0.0004 | 0.0001 | `epoch-28-i-840-ema_loss-0.0004` |
| 10 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 11 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 12 | ACCEPT | 26 | 0.0004 | 0.0001 | `epoch-26-i-780-ema_loss-0.0004` |
| 13 | ACCEPT | 24 | 0.0004 | 0.0001 | `epoch-24-i-720-ema_loss-0.0004` |
| 14 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` |
| 15 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 16 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 17 | ACCEPT | 27 | 0.0004 | 0.0001 | `epoch-27-i-810-ema_loss-0.0004` |
| 18 | ACCEPT | 43 | 0.0004 | 0.0001 | `epoch-43-i-1290-ema_loss-0.0004` |
| 19 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` |
| 20 | ACCEPT | 33 | 0.0004 | 0.0001 | `epoch-33-i-990-ema_loss-0.0004` |
| 21 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` |
| 22 | ACCEPT | 54 | 0.0004 | 0.0001 | `epoch-54-i-1620-ema_loss-0.0004` |
| 23 | ACCEPT | 68 | 0.0004 | 0.0001 | `epoch-68-i-2040-ema_loss-0.0004` |
| 24 | ACCEPT | 81 | 0.0004 | 0.0001 | `epoch-81-i-2430-ema_loss-0.0004` |
| 25 | ACCEPT | 110 | 0.0004 | 0.0001 | `epoch-110-i-3300-ema_loss-0.0004` |
| 26 | ACCEPT | 343 | 0.0004 | 0.0001 | `epoch-343-i-10290-ema_loss-0.0004` |
| 27 | MISS_TARGET | 67 | 1.6280 | 1.6277 | `epoch-67-i-2010-ema_loss-1.6280` |

### Same-Entity Full Metrics

| Layer | Status | Epoch | EMA Loss | Request | Generality | Gen Text | Gen Image | Locality | Loc Text | Loc Image | Portability | 1-hop | 2-hop | CoreAvg4 | Checkpoint |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | ACCEPT | 38 | 0.0004 | 1.0000 | 0.9624 | 0.9331 | 0.9757 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8373 | `epoch-38-i-1140-ema_loss-0.0004` |
| 1 | ACCEPT | 60 | 0.0004 | 1.0000 | 0.9357 | 0.8472 | 0.9759 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8306 | `epoch-60-i-1800-ema_loss-0.0004` |
| 2 | ACCEPT | 46 | 0.0004 | 1.0000 | 0.9235 | 0.8183 | 0.9713 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8275 | `epoch-46-i-1380-ema_loss-0.0004` |
| 3 | ACCEPT | 45 | 0.0004 | 1.0000 | 0.9079 | 0.7608 | 0.9747 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8236 | `epoch-45-i-1350-ema_loss-0.0004` |
| 4 | ACCEPT | 49 | 0.0004 | 1.0000 | 0.9479 | 0.8833 | 0.9773 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8336 | `epoch-49-i-1470-ema_loss-0.0004` |
| 5 | ACCEPT | 50 | 0.0004 | 1.0000 | 0.9521 | 0.9083 | 0.9720 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8347 | `epoch-50-i-1500-ema_loss-0.0004` |
| 6 | ACCEPT | 39 | 0.0004 | 1.0000 | 0.9358 | 0.8544 | 0.9727 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8306 | `epoch-39-i-1170-ema_loss-0.0004` |
| 7 | ACCEPT | 31 | 0.0004 | 1.0000 | 0.8967 | 0.7336 | 0.9708 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8208 | `epoch-31-i-930-ema_loss-0.0004` |
| 8 | ACCEPT | 33 | 0.0004 | 1.0000 | 0.9331 | 0.8292 | 0.9803 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8299 | `epoch-33-i-990-ema_loss-0.0004` |
| 9 | ACCEPT | 28 | 0.0004 | 1.0000 | 0.8931 | 0.7053 | 0.9785 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8199 | `epoch-28-i-840-ema_loss-0.0004` |
| 10 | ACCEPT | 33 | 0.0004 | 1.0000 | 0.9209 | 0.8158 | 0.9687 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8269 | `epoch-33-i-990-ema_loss-0.0004` |
| 11 | ACCEPT | 27 | 0.0004 | 1.0000 | 0.9273 | 0.8428 | 0.9658 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8285 | `epoch-27-i-810-ema_loss-0.0004` |
| 12 | ACCEPT | 26 | 0.0004 | 1.0000 | 0.9289 | 0.8267 | 0.9754 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8289 | `epoch-26-i-780-ema_loss-0.0004` |
| 13 | ACCEPT | 24 | 0.0004 | 1.0000 | 0.9250 | 0.8322 | 0.9672 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8279 | `epoch-24-i-720-ema_loss-0.0004` |
| 14 | ACCEPT | 32 | 0.0004 | 1.0000 | 0.9372 | 0.8586 | 0.9729 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8309 | `epoch-32-i-960-ema_loss-0.0004` |
| 15 | ACCEPT | 33 | 0.0004 | 1.0000 | 0.9172 | 0.8089 | 0.9664 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8260 | `epoch-33-i-990-ema_loss-0.0004` |
| 16 | ACCEPT | 33 | 0.0004 | 1.0000 | 0.9550 | 0.9003 | 0.9799 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8354 | `epoch-33-i-990-ema_loss-0.0004` |
| 17 | ACCEPT | 27 | 0.0004 | 1.0000 | 0.9451 | 0.9075 | 0.9622 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8329 | `epoch-27-i-810-ema_loss-0.0004` |
| 18 | ACCEPT | 43 | 0.0004 | 1.0000 | 0.9352 | 0.8475 | 0.9751 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8305 | `epoch-43-i-1290-ema_loss-0.0004` |
| 19 | ACCEPT | 38 | 0.0004 | 1.0000 | 0.9245 | 0.8436 | 0.9612 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8278 | `epoch-38-i-1140-ema_loss-0.0004` |
| 20 | ACCEPT | 33 | 0.0004 | 1.0000 | 0.8876 | 0.7706 | 0.9408 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8185 | `epoch-33-i-990-ema_loss-0.0004` |
| 21 | ACCEPT | 46 | 0.0004 | 1.0000 | 0.9024 | 0.7711 | 0.9621 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8223 | `epoch-46-i-1380-ema_loss-0.0004` |
| 22 | ACCEPT | 54 | 0.0004 | 1.0000 | 0.9093 | 0.7544 | 0.9797 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.8240 | `epoch-54-i-1620-ema_loss-0.0004` |
| 23 | ACCEPT | 68 | 0.0004 | 1.0000 | 0.8993 | 0.7594 | 0.9628 | 1.0000 | 1.0000 | 1.0000 | 0.3862 | 0.3857 | 0.3868 | 0.8214 | `epoch-68-i-2040-ema_loss-0.0004` |
| 24 | ACCEPT | 81 | 0.0004 | 1.0000 | 0.9229 | 0.8192 | 0.9701 | 0.9800 | 1.0000 | 0.9600 | 0.3839 | 0.3857 | 0.3820 | 0.8217 | `epoch-81-i-2430-ema_loss-0.0004` |
| 25 | ACCEPT | 110 | 0.0004 | 1.0000 | 0.9428 | 0.8694 | 0.9761 | 0.9800 | 1.0000 | 0.9600 | 0.3653 | 0.3732 | 0.3569 | 0.8220 | `epoch-110-i-3300-ema_loss-0.0004` |
| 26 | ACCEPT | 343 | 0.0004 | 1.0000 | 0.9605 | 0.9178 | 0.9799 | 0.9833 | 1.0000 | 0.9667 | 0.3802 | 0.3857 | 0.3744 | 0.8310 | `epoch-343-i-10290-ema_loss-0.0004` |
| 27 | MISS_TARGET | 67 | 1.6280 | 0.6708 | 0.6843 | 0.6077 | 0.7190 | 1.0000 | 1.0000 | 1.0000 | 0.3866 | 0.3857 | 0.3876 | 0.6854 | `epoch-67-i-2010-ema_loss-1.6280` |

### Quick Winners

| Metric | Layers | Score | Criterion |
|---|---|---:|---|
| Request | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26 | 1.0000 | all layers |
| Generality | 0 | 0.9624 | effective: status!=MISS_TARGET, request>=0.9, generality>=0.8 |
| Effective Locality | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23 | 1.0000 | effective: status!=MISS_TARGET, request>=0.9, generality>=0.8 |
| Portability | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22 | 0.3866 | effective: status!=MISS_TARGET, request>=0.9, generality>=0.8 |
| CoreAvg4 | 0 | 0.8373 | mean(request,generality,locality,portability), effective first |

### Local Result Files

- `downloads/Temp/qwen25vl_text_eval_results/target0003_ckpt_summary.json`
- `downloads/Temp/qwen25vl_text_eval_results/target0003_ckpt_summary.tsv`
- `downloads/Temp/qwen25vl_text_eval_results/selected_full_metrics_summary.tsv`

<!-- REQUEST_ONLY_QWEN25VL_TEXT_SWEEP_RESULTS_END -->
