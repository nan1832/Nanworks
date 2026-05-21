# Cross-Architecture Golden Layer Validation 实验计划-gpt

## 0. 实验目标

回答三个假设：

```text
H1（架构→视觉编辑层位置）：
  VLM 的最佳视觉编辑层位置具有架构依赖性：
  Q-Former / Resampler 压缩型模型更可能偏中层，
  线性投影 / MLP 型模型更可能偏浅层。

H2（视觉-文本编辑层相对距离）：
  同一模型中，最佳视觉编辑层与最佳文本编辑层的相对位置
  不是固定规律，而是具有架构依赖性。
  线性投影型可能视觉/文本层接近；Q-Former 型可能出现分离或平台化。

H3（Golden Layer 指标泛化性）：
  在 LLaVA / BLIP2 上校准出的 Virtual Δh LGA 指标
  （|cos| × new_norm / new_norm × (1-cos) 系列）
  能否在 held-out 架构上预测真实 sweep oracle。
```

约束：

```text
每个模型独立跑完全流程，不跨模型迁移 adapter
使用统一的 Bridge30 request-only 训练 / Same-Entity Full Metrics 评测口径
Virtual Δh LGA 不重新设计，只验证已有指标在新模型上的预测力
不做 dual-edit 联合层；视觉和文本各自独立扫
```

输出：

```text
每模型 × 每模态的 32 层 sweep oracle 主表
每模型 × 每模态的 Virtual Δh LGA 指标表
Spearman / Top-K 校准表（LGA 指标 vs sweep oracle）
跨架构汇总：编辑层位置 vs 架构类型的对照表
H1 / H2 / H3 的结论与证据
```

本版本相对原始计划的关键修订：

```text
1. H2 不再预设“视觉层一定不同于文本层”，因为 LLaVA 已出现 visual=7/text=7 的反例。
2. Idefics2 不再称为严格“统一 Transformer 型”，改为 Resampler / Perceiver 压缩注入型。
3. Golden layer 同时报告 gen-golden 与 balanced-golden，避免只用 generality 峰值导致解释偏窄。
4. H3 明确区分 calibration source（LLaVA/BLIP2）与 held-out validation（新增模型）。
```

## 1. 已有基线

以下两个模型已完成全 32 层 sweep + LGA 校准，作为本次实验的参照基线：

### 1.1 LLaVA-v1.5-7b（MLP 投影型）

```text
架构：Vision Encoder (CLIP ViT-L/14) → 2-layer MLP Projector → Vicuna-7b Decoder (32 layers)
视觉编辑 gen 峰值层：7（gen=0.9808）
文本编辑 gen 峰值层：7（gen=0.9840）
视觉 LGA winner：M_newn_x_1mcos（ρ=0.878, p≪0.001）
文本 LGA winner：M_new_norm（ρ=0.863, p≪0.001）
```

### 1.2 BLIP2-OPT-2.7b（Q-Former 型）

```text
架构：Vision Encoder (EVA-CLIP ViT-G/14) → Q-Former (12 layers) → OPT-2.7b Decoder (32 layers)
视觉编辑 gen 峰值层：8/9/12/15/16/21（并列 1.0 平台）
文本编辑 gen 峰值层：16/17（gen=1.0000）
视觉 LGA winner：M_abscos_x_newn（ρ=0.487, p=0.005）
文本 LGA winner：M_abscos_x_newn（ρ=0.296, p=0.106, 不显著）
```

### 1.3 已有结论摘要

```text
LLaVA（MLP 型）：视觉/文本编辑层均偏前段（层 7），LGA 预测力强
BLIP2（Q-Former 型）：视觉编辑层分布在中段平台（8-21），文本编辑层偏中后段（16-17），LGA 预测力弱
两个模型的 raw dot 均失效（被梯度模长主导），方向 × 杠杆复合指标胜出
```

## 2. 模型选择

从用户提供的 VLM 架构表中，按 3 类架构各选代表模型（含已有基线），确保：
- 覆盖 Q-Former / MLP投影 / Resampler压缩注入 三种架构
- 每类至少 1 个新模型（未做过 sweep）
- 规模在 3B-8B 范围内，可在单卡 A100/A800 上完成训练

### 2.1 Q-Former 型（视觉信息经 Q-Former 压缩后进入 LLM）

| 模型 | LLM Backbone | Decoder 层数 | 状态 |
|---|---|---|---|
| BLIP2-OPT-2.7b | OPT-2.7b | 32 | ✅ 已完成 |
| InstructBLIP-Vicuna-7b | Vicuna-7b | 32 | 🆕 新增 |

选择理由：

```text
InstructBLIP 与 BLIP2 共享 Q-Former 结构但 LLM backbone 不同（OPT vs Vicuna），
可以区分"Q-Former 架构效应"和"LLM backbone 效应"。
mPLUG-Owl2/3 需要额外的 visual abstractor 适配，工程复杂度高，不作为第一批。
MiniGPT-4 本质上也是 Q-Former + Vicuna，与 InstructBLIP 架构高度重叠，暂不纳入。
```

### 2.2 MLP / 线性投影型（视觉信息经 MLP/Linear 投影后直接拼接进 LLM）

| 模型 | LLM Backbone | Decoder 层数 | 状态 |
|---|---|---|---|
| LLaVA-v1.5-7b | Vicuna-7b | 32 | ✅ 已完成 |
| Qwen2.5-VL-7B-Instruct | Qwen2.5-7B | 28 | 🆕 新增 |

选择理由：

```text
Qwen2.5-VL 使用 ViT + 2D-RoPE + MLP projection，与 LLaVA 的 CLIP + 2-layer MLP
在投影方式上有差异（动态分辨率 vs 固定分辨率）。
PaliGemma-2 虽架构不同（SigLIP + linear），但其 decoder 是 Gemma-2，
license 与工程适配成本高，不作为第一批。
```

### 2.3 Resampler / Perceiver 压缩注入型（视觉 token 经 resampler 后进入 LLM）

| 模型 | LLM Backbone | Decoder 层数 | 状态 |
|---|---|---|---|
| Idefics2-8B | Mistral-7B | 32 | 🆕 新增 |

选择理由：

```text
Idefics2 采用 SigLIP + perceiver resampler + Mistral-7B，视觉 token 经 perceiver
压缩后进入 LLM decoder。它不是严格意义上的单一视觉-文本统一 Transformer，
但可以作为"resampler 压缩注入"类别，与 Q-Former / MLP 投影形成对比。
Mantis-Idefics2 是 Idefics2 的多图微调版，结构一致，不需要单独扫。
```

### 2.4 总览

```text
类型 A（Q-Former）：BLIP2-OPT-2.7b (已有) + InstructBLIP-Vicuna-7b (新增)
类型 B（MLP 投影）：LLaVA-v1.5-7b (已有) + Qwen2.5-VL-7B (新增)
类型 C（Resampler 压缩注入）：Idefics2-8B (新增)

共 5 个模型，其中 2 个已有全量结果，3 个需要新跑。
```

## 3. 每模型的 VEAD Adapter 适配

新增的 3 个模型需要适配 VEAD adapter 挂载。adapter 挂在 LLM decoder 的指定层，
通过 `register_forward_hook` 修改该层输出的 hidden states。

### 3.1 InstructBLIP-Vicuna-7b

```text
HuggingFace ID：Salesforce/instructblip-vicuna-7b
LLM：Vicuna-7b（与 LLaVA 相同）
Decoder 层模板：language_model.model.layers.{}
Attention 模板：language_model.model.layers.{}.self_attn
llm_hidden_size：4096
adaptor_mid_dim：1024
adaptor_cross_att_head_n：8
decoder 层数：32
视觉 token 来源：Q-Former 输出（32 query tokens）
```

### 3.2 Qwen2.5-VL-7B-Instruct

```text
HuggingFace ID：Qwen/Qwen2.5-VL-7B-Instruct
LLM：Qwen2.5-7B
Decoder 层模板：model.layers.{}
Attention 模板：model.layers.{}.self_attn
llm_hidden_size：3584
adaptor_mid_dim：1024
adaptor_cross_att_head_n：8
decoder 层数：28
视觉 token 来源：ViT + MLP 投影（动态数量，取决于图像分辨率）
```

注意：Qwen2.5-VL 只有 28 层 decoder，扫层范围为 0-27。

### 3.3 Idefics2-8B

```text
HuggingFace ID：HuggingFaceM4/idefics2-8b
LLM：Mistral-7B-v0.1
Decoder 层模板：model.layers.{}
Attention 模板：model.layers.{}.self_attn
llm_hidden_size：4096
adaptor_mid_dim：1024
adaptor_cross_att_head_n：8
decoder 层数：32
视觉 token 来源：SigLIP + perceiver resampler（64 visual tokens）
```

### 3.4 适配开发清单

每个新模型需要：

```text
1. configs/vead/{model_name}.yaml           — 基础配置
2. configs/vead/{model_name}-bridge-text-only-l16.yaml  — 文本 adapter 基础配置
3. editor/vllms_for_edit/__init__.py        — 注册模型加载入口
4. 验证 forward_hook 挂载后推理正确性（forward_equivalence_max_diff < 1e-5）
5. 验证 Bridge30 数据加载兼容性（tokenizer / image processor）
```

## 4. 实验分为 3 个阶段

```text
Phase 1：Virtual Δh LGA 扫描（零训练，仅前向 + 反向传播）
Phase 2：全层 Adapter Sweep（逐层训练 + 评测）
Phase 3：Calibration（LGA 指标 vs Sweep Oracle 的 Spearman / Top-K）
```

### 4.1 Phase 1：Virtual Δh LGA 扫描

对每个新模型，复用 `Bridge30_Virtual_DeltaH_LGA_计算手册.md` 的协议：

```text
输入数据：Bridge30 request-only 训练集 30 条
方法：
  1. 在每层挂载零初始化 virtual adapter
  2. 对每条样本计算 old_loss / new_loss 的梯度
  3. 记录 adapter 参数上的梯度向量
  4. 计算 12 个指标：dot, conflict, dot_per_dim, cos, old_norm, new_norm,
     joint_norm, positive_ratio, zero_grad + 4 个复合指标
输出：{model}/virtual_delta_h_lga_layer_scores.csv
```

每模型 × 2 模态（visual adapter + text adapter）：

```text
visual adapter：edit_layers=[L], edit_text_layers=[]
text adapter：  edit_layers=[], edit_text_layers=[L]
```

资源估计：

```text
每模型每模态：30 样本 × N 层 × 2 forward/backward ≈ 30-60 min (A100)
3 个新模型 × 2 模态 = 6 次扫描 ≈ 3-6 GPU-hours
```

### 4.2 Phase 2：全层 Adapter Sweep

对每个新模型，复用 `Bridge30_RequestOnly_*_FullLayerSweep_训练评测手册.md` 的协议：

#### 4.2.1 训练

```text
数据：Bridge30 request-only 训练集 30 条
batch_size：1
lr：1e-4
ema_alpha：0.1
目标 ema_loss：0.0003
max_epochs：100 起步，每次加 20，最多 700
selection：target0003（与已有 sweep 对齐）
```

每模型独立训练：

```text
visual sweep：edit_layers=[L], edit_text_layers=[]，L ∈ {0, ..., N_layers-1}
text sweep：  edit_layers=[], edit_text_layers=[L]，L ∈ {0, ..., N_layers-1}
```

#### 4.2.2 评测

```text
评测数据：Same-Entity Full Metrics (rephrase_split)
  edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json

主表字段（与已有 sweep 严格一致）：
  layer, request, generality, gen-T, gen-I, locality, loc-T, loc-I,
  portability, port-1, port-2, status

输出：
  {model}/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
```

资源估计：

```text
每模型每模态每层：训练 ~30 min + 评测 ~10 min ≈ 40 min (A100)
每模型每模态全层：N_layers × 40 min
3 个新模型 × 2 模态：
  InstructBLIP (32层): 32 × 2 × 40 min = ~43 GPU-hours
  Qwen2.5-VL  (28层): 28 × 2 × 40 min = ~37 GPU-hours
  Idefics2    (32层): 32 × 2 × 40 min = ~43 GPU-hours
总计：~123 GPU-hours（约 5 天单卡，或 2-3 天双卡并行）
```

### 4.3 Phase 3：Calibration

复用 `Bridge30_LGA_Metric_Calibration_实验安排.md` 的框架：

```text
脚本：scripts/bridge_vlm_lga_metric_calibration.py（已有，扩展多模型支持）

输入：
  --{model}-eval-tsv  selected_full_metrics_summary.tsv
  --{model}-lga-csv   virtual_delta_h_lga_layer_scores.csv

评估内容：
  1. 每个 LGA 指标 × 每个 oracle 轴的 Spearman / Pearson
  2. Top-K 命中率（K=1,3,5）
  3. 跨轴 agg（geomean of {generality, portability, -locality}）
  4. Zero-gradient 层过滤

输出：
  per_axis_spearman.csv / per_axis_topk_hit.csv / per_axis_winner.json
```

## 5. 假设检验设计

### 5.1 H1：架构 → 视觉编辑层位置

检验方法：

```text
对每个模型同时报告两类视觉 golden layer：

1. gen-golden layer：
   取 generality 轴 Top-3 视觉编辑层，用于检验"编辑是否可泛化"。

2. balanced-golden layer：
   先要求 request acc 达到 sanity 阈值，再综合 generality / locality / portability
   或报告 Pareto front，用于检验"泛化-局部性-可迁移性"的综合效果。

对 gen-golden Top-3 计算"归一化深度"：
  normalized_depth = layer / (total_layers - 1)

Q-Former 型（BLIP2, InstructBLIP）：
  预期 Top-3 平均 normalized_depth ∈ [0.25, 0.65]（中段）
MLP 投影型（LLaVA, Qwen2.5-VL）：
  预期 Top-3 平均 normalized_depth ∈ [0.0, 0.35]（浅段）
Resampler 压缩注入型（Idefics2）：
  无强先验预期，作为第三类探索
```

统计检验：

```text
如果样本量足够（每类 ≥ 3 个模型），用 Kruskal-Wallis 检验
  H0：三类架构的 normalized_depth 中位数无差异
  H1：至少有一类不同
当前只有 5 个模型（每类 2/2/1），不足以做正式统计检验，
改为描述性比较 + 置信区间报告。
```

判定规则：

```text
强支持 H1：Q-Former 型 Top-3 均在 [0.25, 0.65]，MLP 型 Top-3 均在 [0.0, 0.35]
弱支持 H1：两类有重叠但中心趋势不同
不支持 H1：两类分布无系统差异
```

### 5.2 H2：视觉-文本编辑层相对距离是否架构相关

检验方法：

```text
对每个模型，比较：
  visual_gen_best_layer = argmax_L gen(visual_sweep, L)
  text_gen_best_layer   = argmax_L gen(text_sweep, L)

并同时比较：
  visual_balanced_best_layer
  text_balanced_best_layer

判定规则：
  分离：|visual_best - text_best| ≥ 3 层（考虑 tie-break 噪声）
  重合：|visual_best - text_best| ≤ 2 层

这里不预设所有模型都必须分离；重点检验"分离程度是否随架构变化"。
```

已有数据：

```text
LLaVA：visual=7, text=7 → 重合
BLIP2：visual=8-21 平台, text=16-17 → 视觉编辑层范围更广，文本偏后段
```

预期解释：

```text
若 MLP 投影型更常出现 visual/text 重合或近邻，而 Q-Former 型出现平台化或更大层差，
则支持 H2 的架构依赖版本。
若所有模型均重合或均分离，则 H2 不成立，需要改为模型无关规律或数据集特异现象。
```

### 5.3 H3：Golden Layer 指标泛化

检验方法：

```text
在每个新模型上计算所有 LGA 指标 × generality 轴的 Spearman，检查：
  1. |cos| × new_norm (M_abscos_x_newn) 是否在所有模型上都进入 Top-3 指标
  2. new_norm × (1 - cos) (M_newn_x_1mcos) 是否在所有模型上都进入 Top-3 指标
  3. 纯 new_norm 或纯 cos 是否在某些模型上胜出

汇总表：
  对每个 (model, modality)，报告 winner 指标、ρ、p、top3_hit

泛化评估分组：
  calibration source：LLaVA, BLIP2
  held-out validation：InstructBLIP, Qwen2.5-VL, Idefics2

指标一致性判定：
  强泛化：同一个复合指标在 held-out 模型的大多数 setting 上胜出
  弱泛化：同族指标（|cos|×new_norm 或 new_norm×(1-cos)）在 held-out setting 中进入 Top-3
  不泛化：不同模型需要不同族的指标
```

## 6. 数据来源

### 6.1 训练数据（沿用已有）

```text
train_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json

val_request:
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json
```

### 6.2 评测数据（沿用已有）

```text
Same-Entity Full Metrics (rephrase_split):
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json
```

### 6.3 图像路径

```text
Bridge 图像：
/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge

COCO 图像：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

### 6.4 模型路径

```text
已有：
  LLaVA:       /datapool/home/.../models/llava-v1.5-7b-hf
  BLIP2:       /datapool/home/.../models/blip2-opt-2.7b

新增（需下载到同目录）：
  InstructBLIP: Salesforce/instructblip-vicuna-7b
  Qwen2.5-VL:  Qwen/Qwen2.5-VL-7B-Instruct
  Idefics2:    HuggingFaceM4/idefics2-8b
```

## 7. 服务器路径规划

```text
服务器节点：g07 / g08

输出根目录：
  /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cross_arch_golden_layer_validation/

子目录结构：
  {model_name}/
    virtual_delta_h_lga/
      visual/virtual_delta_h_lga_layer_scores.csv
      text/virtual_delta_h_lga_layer_scores.csv
    visual_sweep/
      layer_{LL}/records/...
      eval_same_entity_full_metrics_rephrase_split/
        selected_full_metrics_summary.tsv
    text_sweep/
      layer_{LL}/records/...
      eval_same_entity_full_metrics_rephrase_split/
        selected_full_metrics_summary.tsv
    calibration/
      visual/per_axis_spearman.csv, per_axis_winner.json, ...
      text/per_axis_spearman.csv, per_axis_winner.json, ...
```

## 8. 执行顺序

```text
Step 0：模型下载 + VEAD 适配开发 + 前向一致性验证
  ├─ InstructBLIP adapter 适配
  ├─ Qwen2.5-VL adapter 适配
  └─ Idefics2 adapter 适配

Step 1：Phase 1 — Virtual Δh LGA（3 模型 × 2 模态，~6 GPU-hours）
  优先级：InstructBLIP > Qwen2.5-VL > Idefics2
  理由：InstructBLIP 与 BLIP2 同架构，可第一时间验证 Q-Former 内的一致性

Step 2：快速预筛 — 根据 Phase 1 LGA 结果，检查新模型是否有 zero-grad 层
  如果某模型大量层 zero-grad（如 >50%），说明 adapter 挂载有问题，先排查

Step 3：Phase 2 — 全层 Sweep（按模型串行，每模型内可并行双模态）
  3a. InstructBLIP visual + text sweep (~43 GPU-hours)
  3b. Qwen2.5-VL visual + text sweep (~37 GPU-hours)
  3c. Idefics2 visual + text sweep (~43 GPU-hours)

Step 4：Phase 3 — Calibration（纯计算，不用 GPU，~1 hour）
  对 5 个模型统一跑 calibration 脚本

Step 5：汇总分析 — 检验 H1 / H2 / H3
```

## 9. 关键配置模板

### 9.1 InstructBLIP 视觉 adapter 基础配置

```yaml
edit_model_name: "instructblip-vicuna-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"
edit_layers: [16]
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

### 9.2 Qwen2.5-VL 视觉 adapter 基础配置

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

注意：Qwen2.5-VL 有 28 层，扫层范围为 0-27。

### 9.3 Idefics2 视觉 adapter 基础配置

```yaml
edit_model_name: "idefics2-8b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "model.layers.{}"
llm_att_tmp: "model.layers.{}.self_attn"
edit_layers: [16]
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

## 10. 分析框架

### 10.1 跨架构编辑层位置汇总表

```text
| 架构类型 | 模型 | Decoder层数 | 视觉gen峰值层 | norm_depth_v | 视觉balanced层 | 文本gen峰值层 | norm_depth_t | 文本balanced层 | |v-t|差 |
|----------|------|------------|--------------|-------------|---------------|-------------|-------------|---------------|---------|
| Q-Former | BLIP2       | 32 | 8-21 平台 | 0.25-0.68 | ? | 16-17 | 0.52-0.55 | 16/17 | — |
| Q-Former | InstructBLIP| 32 | ?   | ?      | ? | ?   | ?      | ? | ?    |
| MLP      | LLaVA       | 32 | 7   | 0.23   | ? | 7   | 0.23   | 7 | 0    |
| MLP      | Qwen2.5-VL  | 28 | ?   | ?      | ? | ?   | ?      | ? | ?    |
| Resampler| Idefics2    | 32 | ?   | ?      | ? | ?   | ?      | ? | ?    |
```

### 10.2 LGA 指标泛化性汇总表

```text
| 模型 | 模态 | Winner 指标 | ρ(gen) | p | top3_hit | top1_layer | raw_dot ρ(gen) |
|------|------|------------|--------|---|----------|------------|---------------|
| BLIP2       | vis  | M_abscos_x_newn  | 0.487 | 0.005 | 0   | 13 | -0.245 |
| BLIP2       | text | M_abscos_x_newn  | 0.296 | 0.106 | 0.33| 10 |  0.161 |
| InstructBLIP| vis  | ?                | ?     | ?     | ?   | ?  | ?      |
| InstructBLIP| text | ?                | ?     | ?     | ?   | ?  | ?      |
| LLaVA       | vis  | M_newn_x_1mcos   | 0.878 | <0.001| 0.33| 6  | -0.836 |
| LLaVA       | text | M_new_norm       | 0.863 | <0.001| 0.33| 0  | -0.861 |
| Qwen2.5-VL  | vis  | ?                | ?     | ?     | ?   | ?  | ?      |
| Qwen2.5-VL  | text | ?                | ?     | ?     | ?   | ?  | ?      |
| Idefics2    | vis  | ?                | ?     | ?     | ?   | ?  | ?      |
| Idefics2    | text | ?                | ?     | ?     | ?   | ?  | ?      |
```

### 10.3 统一指标候选评估

在所有 5 个模型上，对每个候选指标计算"跨模型平均 Spearman"和"胜出次数"。
报告时拆成 calibration source 与 held-out validation，避免把用于选指标的 LLaVA/BLIP2
再次当作泛化证据。

```text
候选指标：
  M_abscos_x_newn  = |cos| × new_norm
  M_newn_x_1mcos   = new_norm × (1 - cos)
  M_new_norm        = new_norm
  M_cos             = cos
  M_dot             = dot (baseline)

汇总：
  avg_rho(M) = mean over all (model, modality) of rho(M, gen)
  heldout_avg_rho(M) = mean over held-out (model, modality) only
  win_count(M) = number of (model, modality) where M is the winner
  heldout_win_count(M) = winner count on held-out models only
  sig_count(M) = number of (model, modality) where M is significant (p<0.05)
```

如果 `M_abscos_x_newn` 的 `heldout_win_count` ≥ 4/6 且 held-out `sig_count` ≥ 4/6，
则可以在论文中推荐它作为统一的 Golden Layer 选择指标。

## 11. Oracle 多轴定义（沿用已有并补充 balanced-golden）

```text
判别主轴（用于排序与 agg）：
  O_generality  = generality
  O_portability = portability
  O_locality    = locality（agg 时取 -ρ 转同向）

Sanity 轴（仅自检，不进 agg）：
  O_request     = request

子轴（用于 visual vs text 解释）：
  O_gen_text  = generality.text_rephrase
  O_gen_image = generality.image_rephrase
  O_loc_text  = locality.text_loc
  O_loc_image = locality.image_loc

golden layer 报告口径：
  gen-golden:
    request acc 通过 sanity 后，按 O_generality 排序。
  balanced-golden:
    request acc 通过 sanity 后，报告 Pareto front，并给出一个主表分数：
      score_balanced = mean(O_generality, O_locality, O_portability)
    若 portability 在某模型上层间几乎常数，则同时报告去 portability 的辅助分数：
      score_gen_loc = mean(O_generality, O_locality)
```

## 12. 退化层过滤（沿用已有）

```text
filter rule: M_new_norm < eps_filter
eps_filter (fp32): 1e-6

已知退化层：
  LLaVA layer 31（zero-grad）
  BLIP2 layer 31（zero-grad）
  新模型的退化层需从 Phase 1 LGA 结果中识别
```

## 13. 风险与应对

### 13.1 新模型适配失败

```text
风险：VEAD adapter 挂载后 forward 输出偏差 > 1e-5，或训练不收敛
应对：
  1. 检查 layer_tmp / att_tmp 路径是否正确
  2. 检查 hidden_size 是否匹配
  3. 检查 tokenizer 的 pad_token / eos_token 与训练脚本兼容性
  4. 如果单模型适配超过 3 天未解决，标记 BLOCKED 跳过，不阻塞其他模型
```

### 13.2 Qwen2.5-VL 动态分辨率

```text
风险：Qwen2.5-VL 的视觉 token 数量取决于输入图像分辨率，
  与 LLaVA/BLIP2 的固定 token 数（576/32）不同
应对：
  1. 训练时固定输入分辨率（如 448×448），使视觉 token 数一致
  2. 在 yaml 中记录 visual_token_count，确保 LGA 计算时 token scope 正确
  3. 如果动态分辨率引入过大噪声，降级为固定分辨率模式
```

### 13.3 BLIP2 类模型 generality 饱和

```text
风险：InstructBLIP（同 Q-Former 架构）可能也出现 generality 大面积并列 1.0
应对：
  1. 如果 >10 层 gen=1.0，Spearman 区分度受限，这是结构性问题
  2. 改用 portability 或 gen_text 作为辅助轴
  3. 在结论中如实报告"Q-Former 型模型在 Bridge30 上 generality 区分度不足"
```

### 13.4 H3 不成立（指标不泛化）

```text
风险：不同架构需要不同的 LGA 指标，没有统一的 golden layer 选择公式
应对：
  1. 这本身就是有价值的负面结论
  2. 报告"指标选择需要 architecture-aware，不能 one-size-fits-all"
  3. 分析是否存在"每个架构类型内部一致"的次级规律
```

## 14. 待开发产物清单

### 14.1 配置文件（3 个新模型 × 2 个 yaml = 6 个）

```text
configs/vead/instructblip-vicuna-7b.yaml
configs/vead/instructblip-vicuna-7b-bridge-text-only-l16.yaml
configs/vead/qwen2.5-vl-7b.yaml
configs/vead/qwen2.5-vl-7b-bridge-text-only-l14.yaml
configs/vead/idefics2-8b.yaml
configs/vead/idefics2-8b-bridge-text-only-l16.yaml
```

### 14.2 模型适配代码

```text
editor/vllms_for_edit/__init__.py  — 注册 3 个新模型
editor/vllms_for_edit/instructblip.py  — InstructBLIP 加载 / tokenize / generate
editor/vllms_for_edit/qwen2_5_vl.py   — Qwen2.5-VL 加载 / tokenize / generate
editor/vllms_for_edit/idefics2.py      — Idefics2 加载 / tokenize / generate
```

### 14.3 脚本扩展

```text
scripts/run_bridge_text_layer_sweep.py   — 扩展支持新模型的 config 派生
scripts/bridge_vlm_lga_metric_calibration.py — 扩展支持 5 模型统一校准
scripts/cross_arch_golden_layer_summary.py   — 新增：汇总 5 模型结果 + H1/H2/H3 检验
```

### 14.4 输出产物

```text
每个新模型：
  virtual_delta_h_lga_layer_scores.csv × 2 模态
  selected_full_metrics_summary.tsv × 2 模态
  per_axis_spearman.csv / per_axis_winner.json × 2 模态

汇总：
  cross_arch_visual_layer_position.tsv     — H1 检验表（gen-golden + balanced-golden）
  cross_arch_visual_vs_text_layer.tsv      — H2 检验表（gen 层差 + balanced 层差）
  cross_arch_lga_metric_generalization.tsv — H3 检验表（calibration source / held-out 分开）
  cross_arch_golden_layer_conclusion.md    — 结论文档
```

## 15. 完整性自检清单

```text
每模型每模态：
  ☐ virtual_delta_h_lga_layer_scores.csv 行数 = decoder 层数
  ☐ selected_full_metrics_summary.tsv 行数 = decoder 层数
  ☐ 退化层已标注（zero_grad / MISS_TARGET）
  ☐ forward_equivalence_max_diff < 1e-5
  ☐ per_axis_winner.json 包含完整的 spearman / topk / raw_dot baseline

跨模型：
  ☐ 5 个模型的评测口径一致（同字段、同数据、同样本数）
  ☐ H1 汇总表有 normalized_depth，且同时报告 gen-golden 与 balanced-golden
  ☐ H2 汇总表有 |visual_best - text_best|，且不把 LLaVA 重合误判为实验失败
  ☐ H3 汇总表有 win_count / sig_count / avg_rho，并拆分 held-out 统计
  ☐ raw dot baseline 在所有模型上显式报告
```

## 16. 不在本次范围（YAGNI）

```text
不做 dual-edit 联合层（visual × text 组合）
不调整 adapter_mid_dim / lr / inf_mapper_lambda
不做跨模型迁移（模型 A 的 adapter 用在模型 B 上）
不引入 IT 噪声
不替换评测集
不重新设计 LGA 指标（只验证已有指标）
不扩展到 Bridge100 或更大 proxy set
不纳入 mPLUG-Owl / MiniGPT-4 / PaliGemma（如需可后续单独开）
```

## 17. 论文写作预设口径

### 17.1 如果 H1 成立

```text
We observe an architecture-dependent pattern in the optimal visual editing layer:
Q-Former-based and resampler-compressed models tend to prefer middle decoder
layers, whereas MLP-projection models tend to prefer shallower layers. This
aligns with the information-flow difference: Q-Former/resampler architectures
compress visual information into a small set of query tokens before injection,
whereas MLP projection directly maps patch-level visual features into the LLM
input space.
```

### 17.2 如果 H2 部分成立

```text
Across models, the relative distance between the best visual and text editing
layers is architecture-dependent. In BLIP2, visual editing forms a broad
middle-layer plateau (layers 8–21) while text editing peaks later (layers
16–17), suggesting modality-specific information is distributed over different
depth ranges. In LLaVA, both modalities peak at the same layer (layer 7),
consistent with its direct MLP projection design where visual tokens are tightly
interleaved with text tokens from early decoder layers.
```

### 17.3 如果 H3 成立

```text
The composite metric |cos| × new_norm generalizes to held-out architectures as
a golden layer predictor, achieving significant positive Spearman correlation
(p < 0.05) with the generality oracle in X out of 6 held-out (model, modality)
settings. This validates our claim that gradient magnitude (new_norm) and
directional alignment (cos) jointly determine layer-wise editing effectiveness,
whereas the raw dot product is often dominated by cross-layer norm effects.
```

## 18. 状态

```text
文档状态：实验计划已完成
下一步：
  1. 下载 InstructBLIP / Qwen2.5-VL / Idefics2 模型到服务器
  2. 开发 VEAD adapter 适配代码
  3. 按 Phase 1 → 2 → 3 顺序执行
```
