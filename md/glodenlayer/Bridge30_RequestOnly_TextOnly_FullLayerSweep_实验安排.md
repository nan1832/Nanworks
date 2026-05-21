# Bridge30 Request-Only Text-Only Full Layer Sweep 实验安排

## 0. 实验目标

回答一个问题：

```text
在 Bridge30 request-only 训练 + Same-Entity Full Metrics (rephrase_split) 评测
口径下，只挂载文本 adapter（scheme2，无视觉 adapter）时，
LLaVA / BLIP2 各自在 layer 0-31 中哪一层做文本表征编辑效果最好？
```

约束：

```text
adapter 只挂在文本侧（edit_layers=[]，edit_text_layers=[L]）
不联挂视觉 adapter（与已有 visual sweep 严格成对比）
训练 / 评测口径必须能直接和已有 visual sweep §7.3 对照（同评测集、同主表字段）
不引入新的 oracle 轴、不复合 oracle
```

输出：

```text
LLaVA / BLIP2 各自 32 层的文本 adapter checkpoint 与评测结果
3 套 ckpt 选择方案：best-loss / matched-loss / target0003
与 visual sweep §7.3 同样字段的 selected_full_metrics_summary.tsv
最佳文本编辑层的推荐与证据
```

## 1. 与 Visual Sweep 的对位

已有 visual sweep（仅挂 visual adapter，文本 adapter 不挂）：

```text
Bridge30_RequestOnly_LLaVA_FullLayerSweep_训练评测手册.md  §7.3
Bridge30_RequestOnly_BLIP2_FullLayerSweep_训练评测手册.md  §12.3
```

本次（仅挂 text adapter）和 visual sweep 配对的关系：

```text
visual sweep: edit_layers=[L], edit_text_layers=[]   →  视觉表征单独编辑的"层热力图"
text-only:    edit_layers=[],  edit_text_layers=[L]  →  文本表征单独编辑的"层热力图"
两套独立基线，留给后续 dual-edit 联合实验作交叉对照（不在本次范围）
```

由于评测集、采样口径、单边编辑结构都对齐 visual sweep，本次结果可以直接与 §7.3/§12.3 的同列做层级对位比较。

## 2. 服务器路径

```text
服务器节点：g07（与 visual sweep 一致；如改 g08 走 sbatch 同样模板）
项目目录：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
输出根目录：
  LLaVA: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/llava
  BLIP2: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/blip2
```

模型路径（沿用 visual sweep）：

```text
LLaVA: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
BLIP2: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b
```

request-only 训练数据（沿用 visual sweep）：

```text
train_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json

val_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json

val_full:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_full_metrics.json
```

Same-Entity Full Metrics (rephrase_split) 评测数据（与 visual sweep §7.3 同源）：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

## 3. 配置文件

每个 (model, layer) 一份 yaml；扫层时由 `scripts/run_bridge_text_layer_sweep.py` 自动从 base config 派生。base 模板：

```text
LLaVA base：DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml （已有）
BLIP2 base：DualEdit-main/configs/vead/blip2-opt-2.7b-bridge-text-only-l16.yaml（本次新增）
```

派生规则：

```text
edit_layers       = []          # 视觉 adapter 不挂
edit_text_layers  = [L]         # 单层文本 adapter
其他字段（llm_hidden_size, adaptor_mid_dim, train_cfg 等）保持 base 一致
IT.add_it         = false       # 不引入 IT 噪声，保持与 visual sweep 同口径
```

BLIP2 base 关键字段（新增 yaml 必须包含）：

```yaml
edit_model_name: "blip2-opt-2.7b"
llm_hidden_size: 2560
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.decoder.layers.{}"
llm_att_tmp:   "language_model.model.decoder.layers.{}.self_attn"
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

注：BLIP2 默认 yaml 的 `inf_mapper_lambda=0.1` 与 visual sweep 不一致；本次 text-only base 强制 `0.0` 与 LLaVA 对齐，避免影响损失收敛。

## 4. 训练规则

每层独立训练，batch_size=1，random_seed=42，沿用 visual sweep 的训练超参：

```text
batch_size:      1
ema_alpha:       0.1
log_per_i:       10
save_ckpt_per_i: 30
data_buffer_size:4
```

最大 epoch：

```text
LLaVA: 100 起步，达不到目标按 visual sweep 规则每次加 20，最多 700
BLIP2: 同上
```

目标训练损失（沿用 visual sweep §3）：

```text
ema_loss = 0.0003
```

选择规则（沿用 visual sweep §3）：

```text
1. 命中 ema_loss == 0.0003 的 checkpoint
2. 否则取最接近 0.0003 的
3. 可接受 |ema_loss - 0.0003| <= 0.0001
4. 100 epoch 未达到则每 20 epoch 续训
5. 超过 700 epoch 仍未达到，标记 MISS_TARGET，选最接近的 ckpt 继续后续流程
```

## 5. 训练命令

LLaVA 全 32 层：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/llava

nohup python scripts/run_bridge_text_layer_sweep.py \
  --device cuda:0 --extra_devices 1 \
  --layers $(seq 0 31) \
  --epochs 100 \
  --base_config configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root   /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_text_only \
  --selection_modes best matched \
  > "$OUT/full_layer_text_only_sweep.log" 2>&1 &
```

BLIP2 全 32 层：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/blip2

nohup python scripts/run_bridge_text_layer_sweep.py \
  --device cuda:0 --extra_devices 1 \
  --layers $(seq 0 31) \
  --epochs 100 \
  --base_config configs/vead/blip2-opt-2.7b-bridge-text-only-l16.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json \
  --bridge_img_root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge \
  --coco_img_root   /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images \
  --out_root "$OUT" \
  --train_name_prefix bridge_text_only \
  --selection_modes best matched \
  > "$OUT/full_layer_text_only_sweep.log" 2>&1 &
```

注：当前 `run_bridge_text_layer_sweep.py` 内置 `best-loss` / `matched-loss` 两种 selection，本次额外需要 `target0003`，见 §6。

## 6. Checkpoint 选择：3 套并行

本次扫层每层都跑到 100+ epoch，然后从所有保存下来的 ckpt 中按 3 种规则各选一份评测，共产 3 套结果：

```text
best     : 损失最小的 ckpt
matched  : 所有层一起对齐到 "全层 best_loss 的最大值"，保证横向可比
target0003: 复刻 visual sweep §3 的目标损失 + MISS_TARGET 兜底
```

`run_bridge_text_layer_sweep.py` 需要扩展（不重训）：

```text
1. --selection_modes 增加 "target0003"
2. 实现 select_checkpoint_for_target_loss(checkpoints, 0.0003) 复用
3. 当所有 ckpt 都 |loss - 0.0003| > 0.0001 时，记录 status="MISS_TARGET"
4. target0003 单独输出 target0003_eval_report.json 与 selected_target0003_summary.tsv
```

如所有层均能在 700 epoch 内命中，target0003 应与 visual sweep 的 §7.1 列等价。

## 7. 评测口径：完全沿用 Same-Entity Full Metrics (rephrase_split)

本次评测必须输出和 visual sweep §7.3 完全同字段的主表，便于直接对位比较。

评测数据：

```text
edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

主表字段（与 visual sweep §7.3 严格一致）：

```text
Layer
Request
Generality
Generality.text_rephrase   (Gen-T)
Generality.image_rephrase  (Gen-I)
Locality
Locality.text_loc          (Loc-T)
Locality.image_loc         (Loc-I)
Portability
Portability.port_1         (Port-1)
Portability.port_2         (Port-2)
Status
```

输出文件：

```text
{out_root}/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
{out_root}/eval_same_entity_full_metrics_rephrase_split/{best,matched,target0003}_full_metrics_summary.tsv
{out_root}/eval_same_entity_full_metrics_rephrase_split/layer_{LL}/{selection}/single_edit/mean_results.json
```

评测脚本：

```text
当前 scripts/eval_bridge_text_adapter_ckpt.py 输出的是 strict/loose acc 简表，
需新增 scripts/eval_bridge_text_only_full_metrics.py：
  1. 加载已选 ckpt + edit_layers=[] + edit_text_layers=[L]
  2. 在 Same-Entity Full Metrics (rephrase_split) 数据上跑单编辑
  3. 输出 single_edit/mean_results.json 字段集与 visual sweep 一致
  4. 汇总成 selected_full_metrics_summary.tsv
```

样本数量预期（沿用 visual sweep §7.3）：

```text
request=30
generality.text_rephrase=30
generality.image_rephrase=66
locality.text_loc=30
locality.image_loc=30
portability=62
```

如任一 split 实际样本数与上述不符，说明评测数据落盘异常，需先排查再跑评测。

## 8. 评测命令

LLaVA 同 entity 评测：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/llava

bash scripts/eval_bridge_text_only_full_metrics_sweep.sh \
  --out_root "$OUT" \
  --eval_data /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json \
  --selection_modes best matched target0003 \
  > "$OUT/full_layer_text_only_eval.log" 2>&1
```

BLIP2 同 entity 评测：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/blip2

bash scripts/eval_bridge_text_only_full_metrics_sweep.sh \
  --out_root "$OUT" \
  --eval_data /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json \
  --selection_modes best matched target0003 \
  > "$OUT/full_layer_text_only_eval.log" 2>&1
```

`eval_bridge_text_only_full_metrics_sweep.sh` 是新脚本，内部 for layer in 0..31，复用单层 evaluator。

## 9. 监控与磁盘保护

复用 visual sweep §6 的同套做法：

```bash
pgrep -af 'bridge_text_adapter_train.py|eval_bridge_text_only_full_metrics.py'

tail -f /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/{llava,blip2}/full_layer_text_only_sweep.log
tail -f /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/{llava,blip2}/full_layer_text_only_eval.log
```

磁盘 / 阶段保护：

```text
1. 每层 selected ckpt 命中后自动清理同层中间 ckpt
2. checkpoint 保存失败 / No space left / PytorchStreamWriter 异常 → 清理该层最早 ckpt 后续训
3. 非存储类异常保留 FAILED 状态，等待人工排查
4. 训练完成后归档 generated_configs/ 与 records/，evaluator 之外只保留 selected ckpt
```

## 10. 完整性自检清单

执行完成后必须通过以下自检：

```text
每模型每选择模式 32 行 ckpt 与 32 行评测结果
selected_full_metrics_summary.tsv 字段集 = visual sweep §7.3
样本数 (request/gen-T/gen-I/loc-T/loc-I/port) 与 §7 一致
任何 MISS_TARGET 行有显式标注且 ema_loss 已记录
3 种选择模式（best / matched / target0003）各出一份 summary
评测日志中无 "FAILED" 或 "out of memory" 残留
generated_configs/ 中每层 yaml 的 edit_layers=[] 且 edit_text_layers=[L]
```

## 11. 不在本次范围（YAGNI）

```text
不挂 visual adapter（不做 dual-edit）
不做 visual × text 联合扫层
不调整 adapter_mid_dim / lr / inf_mapper_lambda
不引入 IT 噪声
不跨模型迁移
不替换评测集，不做加权复合 oracle
不重做 Virtual Δh LGA（已有 calibration 结果直接复用）
```

每一项都可在本次结论得出后单独开新实验安排。

## 12. 结果分析的预设口径

跑完后，下一份手册（`Bridge30_RequestOnly_TextOnly_FullLayerSweep_训练评测手册.md`）需要回答以下问题：

```text
1. text-only 单层最佳层是哪一层？generality / portability / locality 峰值分别落在哪？
2. 与 visual sweep 的对位：同层位次是否一致？谁更靠前段、谁更靠后段？
3. MISS_TARGET 层（如有）是否集中在末尾（30/31）和视觉 sweep 一致？
4. text-only 的 locality 是否系统性低于 visual-only？（文本编辑通常波及面更广，需用数据说话）
5. 给后续 Bridge30_LGA_Metric_Calibration §13.3 推荐的 text 主指标补充独立验证：
     LLaVA text: M_new_norm 推荐层 [0,1,2] 是否真在 text-only sweep 主表里靠前？
     BLIP2 text: M_abscos_x_newn 推荐层 [10,8,7] 是否真在 text-only sweep 主表里靠前？
```

## 13. 待开发产物清单

实施阶段需要新增的文件：

```text
configs/vead/blip2-opt-2.7b-bridge-text-only-l16.yaml   (BLIP2 base)
scripts/run_bridge_text_layer_sweep.py                   (扩展 target0003 选择模式)
scripts/eval_bridge_text_only_full_metrics.py            (单层 Same-Entity Full Metrics evaluator)
scripts/eval_bridge_text_only_full_metrics_sweep.sh      (扫层批跑壳脚本)
```

输出物：

```text
server_results/bridge_text_only_layer_sweep/llava/
  generated_configs/llava-v1.5-7b-bridge-text-only-l{LL}.yaml × 32
  layer_{LL}/records/...                                       × 32
  layer_{LL}/checkpoint_inventory.json                         × 32
  best_ckpt_summary.json
  matched_ckpt_summary.json
  target0003_ckpt_summary.json
  best_eval_report.json
  matched_eval_report.json
  target0003_eval_report.json
  eval_same_entity_full_metrics_rephrase_split/
    selected_full_metrics_summary.tsv
    {best,matched,target0003}_full_metrics_summary.tsv
    layer_{LL}/{selection}/single_edit/mean_results.json

server_results/bridge_text_only_layer_sweep/blip2/
  ...                                                          (镜像结构)
```

## 14. 状态

```text
文档状态：实验安排已对齐用户口径（text-only scheme2 + 双模型 + 全 32 层 + best/matched/target0003 + Same-Entity Full Metrics rephrase_split）
下一步：写实施计划（writing-plans），随后才进入 BLIP2 base yaml、selection 扩展、evaluator 与扫层壳脚本的实现
```
