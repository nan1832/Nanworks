# Bridge30 Request-Only Text-Only Full Layer Sweep 实验安排

## 0. 实验目标

回答一个问题：

```text
在 Bridge30 request-only 训练 + Same-Entity Full Metrics (rephrase_split) 评测
口径下，只挂载文本 adapter（scheme2，无视觉 adapter）时，
LLaVA / BLIP2 各自在 layer 0-31 中哪一层做文本表征编辑效果最好？
```

## 15. 执行版修正：训练/评测数据口径

按最新确认，本实验训练集使用纯 request 文件：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json
```

训练阶段只用 `request`，不使用 `generality`、`locality`、`portability`。

评测阶段使用 Same-Entity Full Metrics 数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

评测指标为：

```text
request acc      = 训练 request 的 sanity acc
generality acc   = val generality
locality acc     = val locality
portability acc  = val portability
```

也就是说，本实验和视觉表征 request-only sweep 使用同一训练/评测口径，只把 adapter 挂载位置改成文本表征层。

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

## 15. Text-only Full Layer Sweep Results

Source: remote `server_results/bridge_text_only_layer_sweep/{llava,blip2}`. This section uses the final `target0003/selected` rule: keep the first checkpoint that reaches `0.0003 +/- 0.0001`; if no checkpoint reaches the target by 700 epochs, mark `MISS_TARGET` and select the closest available checkpoint.

Local raw TSV backups:

- `downloads/Temp/text_only_layer_sweep_results/llava/target0003_ckpt_summary.tsv`
- `downloads/Temp/text_only_layer_sweep_results/llava/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv`
- `downloads/Temp/text_only_layer_sweep_results/blip2/target0003_ckpt_summary.tsv`
- `downloads/Temp/text_only_layer_sweep_results/blip2/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv`

### 15.1 LLaVA text adapter selected checkpoints and metrics

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | 1-hop | 2-hop |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | ACCEPT | 58 | 0.0003 | 0.0000 | `epoch-58-i-1740-ema_loss-0.0003` | 1.0000 | 0.9583 | 1.0000 | 0.9394 | 0.9833 | 1.0000 | 0.9667 | 0.3091 | 0.3042 | 0.3143 |
| 1 | ACCEPT | 58 | 0.0004 | 0.0001 | `epoch-58-i-1740-ema_loss-0.0004` | 1.0000 | 0.9687 | 1.0000 | 0.9545 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 2 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` | 1.0000 | 0.9823 | 1.0000 | 0.9742 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 3 | ACCEPT | 43 | 0.0004 | 0.0001 | `epoch-43-i-1290-ema_loss-0.0004` | 1.0000 | 0.9746 | 1.0000 | 0.9631 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 4 | ACCEPT | 39 | 0.0004 | 0.0001 | `epoch-39-i-1170-ema_loss-0.0004` | 1.0000 | 0.9770 | 1.0000 | 0.9665 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 5 | ACCEPT | 35 | 0.0004 | 0.0001 | `epoch-35-i-1050-ema_loss-0.0004` | 1.0000 | 0.9670 | 1.0000 | 0.9520 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 6 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` | 1.0000 | 0.9770 | 1.0000 | 0.9665 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 7 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` | 1.0000 | 0.9840 | 1.0000 | 0.9767 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 8 | ACCEPT | 41 | 0.0004 | 0.0001 | `epoch-41-i-1230-ema_loss-0.0004` | 1.0000 | 0.9767 | 1.0000 | 0.9661 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 9 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` | 1.0000 | 0.9694 | 0.9917 | 0.9593 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 10 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` | 1.0000 | 0.9532 | 0.9536 | 0.9530 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 11 | ACCEPT | 35 | 0.0004 | 0.0001 | `epoch-35-i-1050-ema_loss-0.0004` | 1.0000 | 0.9634 | 0.9583 | 0.9657 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 12 | ACCEPT | 37 | 0.0003 | 0.0000 | `epoch-37-i-1110-ema_loss-0.0003` | 1.0000 | 0.9390 | 0.8917 | 0.9605 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 13 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` | 1.0000 | 0.9486 | 0.9228 | 0.9603 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 14 | ACCEPT | 37 | 0.0003 | 0.0000 | `epoch-37-i-1110-ema_loss-0.0003` | 1.0000 | 0.9561 | 0.9091 | 0.9775 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 15 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` | 1.0000 | 0.9267 | 0.8269 | 0.9721 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 16 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` | 1.0000 | 0.9094 | 0.7537 | 0.9802 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 17 | ACCEPT | 37 | 0.0003 | 0.0000 | `epoch-37-i-1110-ema_loss-0.0003` | 1.0000 | 0.9133 | 0.7551 | 0.9852 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 18 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` | 1.0000 | 0.9261 | 0.7912 | 0.9874 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 19 | ACCEPT | 32 | 0.0004 | 0.0001 | `epoch-32-i-960-ema_loss-0.0004` | 1.0000 | 0.9288 | 0.7887 | 0.9924 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 20 | ACCEPT | 37 | 0.0003 | 0.0000 | `epoch-37-i-1110-ema_loss-0.0003` | 1.0000 | 0.9109 | 0.7309 | 0.9928 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 21 | ACCEPT | 36 | 0.0004 | 0.0001 | `epoch-36-i-1080-ema_loss-0.0004` | 1.0000 | 0.9034 | 0.7076 | 0.9924 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 22 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` | 1.0000 | 0.8994 | 0.6948 | 0.9924 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 23 | ACCEPT | 37 | 0.0004 | 0.0001 | `epoch-37-i-1110-ema_loss-0.0004` | 1.0000 | 0.9080 | 0.7215 | 0.9928 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 24 | ACCEPT | 38 | 0.0004 | 0.0001 | `epoch-38-i-1140-ema_loss-0.0004` | 1.0000 | 0.9081 | 0.7245 | 0.9915 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 25 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` | 1.0000 | 0.9027 | 0.7045 | 0.9928 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 26 | ACCEPT | 48 | 0.0004 | 0.0001 | `epoch-48-i-1440-ema_loss-0.0004` | 1.0000 | 0.9043 | 0.7151 | 0.9903 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 27 | ACCEPT | 46 | 0.0004 | 0.0001 | `epoch-46-i-1380-ema_loss-0.0004` | 1.0000 | 0.9097 | 0.7298 | 0.9915 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 28 | ACCEPT | 85 | 0.0004 | 0.0001 | `epoch-85-i-2550-ema_loss-0.0004` | 1.0000 | 0.8984 | 0.6935 | 0.9915 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 29 | ACCEPT | 103 | 0.0004 | 0.0001 | `epoch-103-i-3090-ema_loss-0.0004` | 1.0000 | 0.9198 | 0.7601 | 0.9924 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 30 | ACCEPT | 136 | 0.0004 | 0.0001 | `epoch-136-i-4080-ema_loss-0.0004` | 1.0000 | 0.9259 | 0.7823 | 0.9912 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |
| 31 | MISS_TARGET | 108 | 3.0962 | 3.0959 | `epoch-108-i-3240-ema_loss-3.0962` | 0.4561 | 0.4460 | 0.3258 | 0.5007 | 1.0000 | 1.0000 | 1.0000 | 0.3091 | 0.3042 | 0.3143 |

### 15.2 BLIP2 text adapter selected checkpoints and metrics

| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint | Request | Generality | Gen-T | Gen-I | Locality | Loc-T | Loc-I | Portability | 1-hop | 2-hop |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | ACCEPT | 143 | 0.0004 | 0.0001 | `epoch-143-i-4290-ema_loss-0.0004` | 1.0000 | 0.9958 | 1.0000 | 0.9939 | 0.5417 | 1.0000 | 0.0833 | 0.1008 | 0.0000 | 0.2084 |
| 1 | ACCEPT | 150 | 0.0004 | 0.0001 | `epoch-150-i-4500-ema_loss-0.0004` | 1.0000 | 0.9944 | 1.0000 | 0.9919 | 0.5333 | 1.0000 | 0.0667 | 0.1115 | 0.0000 | 0.2304 |
| 2 | ACCEPT | 130 | 0.0004 | 0.0001 | `epoch-130-i-3900-ema_loss-0.0004` | 1.0000 | 0.9968 | 1.0000 | 0.9953 | 0.5361 | 1.0000 | 0.0722 | 0.0846 | 0.0000 | 0.1749 |
| 3 | ACCEPT | 192 | 0.0004 | 0.0001 | `epoch-192-i-5760-ema_loss-0.0004` | 1.0000 | 0.9719 | 1.0000 | 0.9591 | 0.5389 | 1.0000 | 0.0778 | 0.0684 | 0.0000 | 0.1413 |
| 4 | ACCEPT | 183 | 0.0004 | 0.0001 | `epoch-183-i-5490-ema_loss-0.0004` | 1.0000 | 0.9959 | 0.9915 | 0.9978 | 0.5111 | 1.0000 | 0.0222 | 0.0502 | 0.0000 | 0.1037 |
| 5 | ACCEPT | 193 | 0.0004 | 0.0001 | `epoch-193-i-5790-ema_loss-0.0004` | 1.0000 | 0.9521 | 0.8579 | 0.9949 | 0.5250 | 1.0000 | 0.0500 | 0.0187 | 0.0000 | 0.0387 |
| 6 | ACCEPT | 133 | 0.0004 | 0.0001 | `epoch-133-i-3990-ema_loss-0.0004` | 1.0000 | 0.9979 | 1.0000 | 0.9970 | 0.5806 | 1.0000 | 0.1611 | 0.0685 | 0.0208 | 0.1194 |
| 7 | ACCEPT | 104 | 0.0004 | 0.0001 | `epoch-104-i-3120-ema_loss-0.0004` | 1.0000 | 0.9853 | 0.9603 | 0.9966 | 0.6333 | 1.0000 | 0.2667 | 0.0780 | 0.0000 | 0.1612 |
| 8 | ACCEPT | 93 | 0.0004 | 0.0001 | `epoch-93-i-2790-ema_loss-0.0004` | 1.0000 | 0.9702 | 0.9046 | 1.0000 | 0.7861 | 1.0000 | 0.5722 | 0.1096 | 0.0000 | 0.2264 |
| 9 | ACCEPT | 91 | 0.0004 | 0.0001 | `epoch-91-i-2730-ema_loss-0.0004` | 1.0000 | 0.9916 | 0.9767 | 0.9983 | 0.9111 | 1.0000 | 0.8222 | 0.1031 | 0.0000 | 0.2130 |
| 10 | ACCEPT | 91 | 0.0004 | 0.0001 | `epoch-91-i-2730-ema_loss-0.0004` | 1.0000 | 0.9882 | 0.9833 | 0.9904 | 0.9833 | 1.0000 | 0.9667 | 0.1539 | 0.0391 | 0.2763 |
| 11 | ACCEPT | 93 | 0.0004 | 0.0001 | `epoch-93-i-2790-ema_loss-0.0004` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9833 | 1.0000 | 0.9667 | 0.1700 | 0.0703 | 0.2763 |
| 12 | ACCEPT | 80 | 0.0004 | 0.0001 | `epoch-80-i-2400-ema_loss-0.0004` | 1.0000 | 0.9944 | 0.9821 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 13 | ACCEPT | 85 | 0.0004 | 0.0001 | `epoch-85-i-2550-ema_loss-0.0004` | 1.0000 | 0.9924 | 0.9822 | 0.9970 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 14 | ACCEPT | 78 | 0.0004 | 0.0001 | `epoch-78-i-2340-ema_loss-0.0004` | 1.0000 | 0.9962 | 0.9878 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 15 | ACCEPT | 85 | 0.0004 | 0.0001 | `epoch-85-i-2550-ema_loss-0.0004` | 1.0000 | 0.9927 | 1.0000 | 0.9894 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 16 | ACCEPT | 85 | 0.0004 | 0.0001 | `epoch-85-i-2550-ema_loss-0.0004` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 17 | ACCEPT | 80 | 0.0004 | 0.0001 | `epoch-80-i-2400-ema_loss-0.0004` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 18 | ACCEPT | 86 | 0.0004 | 0.0001 | `epoch-86-i-2580-ema_loss-0.0004` | 1.0000 | 0.9987 | 0.9958 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 19 | ACCEPT | 74 | 0.0004 | 0.0001 | `epoch-74-i-2220-ema_loss-0.0004` | 1.0000 | 0.9941 | 0.9810 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 20 | ACCEPT | 78 | 0.0004 | 0.0001 | `epoch-78-i-2340-ema_loss-0.0004` | 1.0000 | 0.9885 | 0.9736 | 0.9953 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 21 | ACCEPT | 78 | 0.0004 | 0.0001 | `epoch-78-i-2340-ema_loss-0.0004` | 1.0000 | 0.9916 | 0.9778 | 0.9978 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 22 | ACCEPT | 85 | 0.0004 | 0.0001 | `epoch-85-i-2550-ema_loss-0.0004` | 1.0000 | 0.9965 | 0.9889 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 23 | ACCEPT | 86 | 0.0004 | 0.0001 | `epoch-86-i-2580-ema_loss-0.0004` | 1.0000 | 0.9593 | 0.8865 | 0.9924 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 24 | ACCEPT | 86 | 0.0004 | 0.0001 | `epoch-86-i-2580-ema_loss-0.0004` | 1.0000 | 0.9756 | 0.9334 | 0.9948 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 25 | ACCEPT | 91 | 0.0004 | 0.0001 | `epoch-91-i-2730-ema_loss-0.0004` | 1.0000 | 0.9689 | 0.9072 | 0.9970 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 26 | ACCEPT | 110 | 0.0004 | 0.0001 | `epoch-110-i-3300-ema_loss-0.0004` | 1.0000 | 0.9652 | 0.8885 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 27 | ACCEPT | 130 | 0.0004 | 0.0001 | `epoch-130-i-3900-ema_loss-0.0004` | 1.0000 | 0.9679 | 0.9154 | 0.9918 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 28 | ACCEPT | 196 | 0.0004 | 0.0001 | `epoch-196-i-5880-ema_loss-0.0004` | 1.0000 | 0.9648 | 0.9320 | 0.9797 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 29 | ACCEPT | 171 | 0.0004 | 0.0001 | `epoch-171-i-5130-ema_loss-0.0004` | 1.0000 | 0.9476 | 0.9033 | 0.9677 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 30 | MISS_TARGET | 695 | 0.0009 | 0.0006 | `epoch-695-i-20850-ema_loss-0.0009` | 1.0000 | 0.9523 | 0.9279 | 0.9634 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |
| 31 | MISS_TARGET | 50 | 3.5825 | 3.5822 | `epoch-50-i-1500-ema_loss-3.5825` | 0.3546 | 0.3558 | 0.2585 | 0.4000 | 1.0000 | 1.0000 | 1.0000 | 0.1700 | 0.0703 | 0.2763 |

## 16. Text-only Result Analysis-gpt

### 16.1 Main Conclusions

1. LLaVA text-only adapter is best placed in the early text layers. Layer 7 gives the best overall result under the selected checkpoint rule: `request=1.0000`, `generality=0.9840`, `locality=1.0000`, `portability=0.3091`.
2. BLIP2 text-only adapter is best placed in the middle text layers. Layers 16 and 17 are tied on the main metrics: `request=1.0000`, `generality=1.0000`, `locality=1.0000`, `portability=0.1700`. Layer 17 is slightly preferable if using fewer epochs as a tie breaker.
3. The final layer is unstable for both models. LLaVA layer 31 is `MISS_TARGET` and drops to `request=0.4561`, `generality=0.4460`; BLIP2 layer 31 is also `MISS_TARGET` and drops to `request=0.3546`, `generality=0.3558`.
4. Portability is weak and nearly layer-insensitive in this request-only text training setup. LLaVA portability is constant at `0.3091`; BLIP2 portability plateaus at `0.1700` from the middle layers onward. This metric should not be used alone for layer selection here.
5. Request accuracy is a useful sanity check. Almost all accepted layers preserve `request=1.0000`; the severe request drop appears only in the final failed layer, which confirms that the target-loss miss corresponds to a real functional failure rather than only a logging artifact.

### 16.2 Best Layers by Metric

| Model | Metric | Best Layer(s) | Value | Note |
|---|---|---:|---:|---|
| LLaVA | Request acc | 0-30 | 1.0000 | All accepted layers pass sanity check |
| LLaVA | Generality acc | 7 | 0.9840 | Best text-only generalization layer |
| LLaVA | Locality acc | 1-31 | 1.0000 | Almost saturated; layer 0 is 0.9833 |
| LLaVA | Portability acc | 0-31 | 0.3091 | Constant across layers |
| LLaVA | Core average | 7 | 0.8233 | Average of request, generality, locality, portability |
| BLIP2 | Request acc | 0-30 | 1.0000 | Layer 31 fails request sanity |
| BLIP2 | Generality acc | 11, 16, 17 | 1.0000 | Layer 11 has lower locality than 16/17 |
| BLIP2 | Locality acc | 12-31 | 1.0000 | Early layers hurt locality strongly |
| BLIP2 | Portability acc | 11-31 | 0.1700 | Middle and late plateau |
| BLIP2 | Core average | 16, 17 | 0.7925 | Best balanced text-only placement |

### 16.3 Layer-Range Trend

| Model | Layer Range | Request Mean | Generality Mean | Locality Mean | Portability Mean | Interpretation |
|---|---|---:|---:|---:|---:|---|
| LLaVA | 0-7 | 1.0000 | 0.9736 | 0.9979 | 0.3091 | Best region; high generality and stable locality |
| LLaVA | 8-23 | 1.0000 | 0.9333 | 1.0000 | 0.3091 | Request/locality stable, generality declines |
| LLaVA | 24-31 | 0.9320 | 0.8519 | 1.0000 | 0.3091 | Tail degrades, mostly due to layer 31 failure |
| BLIP2 | 0-7 | 1.0000 | 0.9863 | 0.5500 | 0.0726 | Good generality but poor locality |
| BLIP2 | 8-23 | 1.0000 | 0.9909 | 0.9790 | 0.1610 | Best region; generality and locality both high |
| BLIP2 | 24-31 | 0.9193 | 0.8873 | 1.0000 | 0.1700 | Late layers preserve locality but tail failure hurts request/generalization |

### 16.4 Model-Specific Interpretation

LLaVA: request-only text editing works best before the middle of the language model. Layers 2-8 are all strong, with layer 7 the best overall. After layer 10, locality remains saturated but generality steadily declines. This suggests that later text-layer edits can memorize the request while becoming less helpful for rephrased or same-entity generalization.

BLIP2: early text layers can fit the request and generality, but locality is poor in layers 0-7. From layer 10 onward locality rapidly recovers, and layers 16-17 give the best balance. This is different from LLaVA: BLIP2 appears to need a deeper text-layer intervention before the edit becomes local and stable.

### 16.5 Recommended Layer Choice

| Model | Recommended Text Adapter Layer | Backup Candidates | Reason |
|---|---:|---|---|
| LLaVA | 7 | 2, 4, 6, 8 | Best generality/core average; request and locality remain saturated |
| BLIP2 | 17 | 16, 18, 22 | Best tied core average with fewer epochs than layer 16; stable request, generality, locality |

For subsequent Bridge30 request-only text editing experiments, use LLaVA layer 7 and BLIP2 layer 17 as the primary text adapter locations. Avoid the final layer for both models unless the goal is specifically to study failure modes.
