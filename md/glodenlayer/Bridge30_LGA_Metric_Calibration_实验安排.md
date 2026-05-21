# Bridge30 LGA Metric Calibration 实验安排

## 0. 实验目标

回答一个问题：

```text
在 Bridge30 request-only 视觉 adapter 32 层全扫场景下，Virtual Δh LGA 应该选用哪个指标，才能最好地预测扫层 oracle？
```

约束：

```text
不重新训练 adapter
不重新跑 Virtual Δh
不跨模型迁移
只在已有结果上做指标级校准
```

输出：

```text
LLaVA 与 BLIP2 各自的 visual / text 模态推荐主指标
配套 Spearman / Top-K 命中表
退化层过滤策略
最终在 Result.md 中给出可写入论文的指标选择依据
```

## 1. 动机与现有问题

已有 32 层 request-only sweep 训练评测结果（见 `Bridge30_RequestOnly_LLaVA_FullLayerSweep_训练评测手册.md` §7.3 与 `Bridge30_RequestOnly_BLIP2_FullLayerSweep_训练评测手册.md` §12.3）显示：

```text
LLaVA generality 峰值层：7
LLaVA portability 峰值层：1, 16, 13
LLaVA locality 峰值层（去除编辑失败层 31）：26
BLIP2 generality=1.0 平台：8, 9, 12, 15, 16, 21
BLIP2 portability 峰值层：1, 0, 16
BLIP2 locality 峰值层（去除编辑失败层 31）：29, 28, 25, 26
```

而 Virtual Δh LGA（`Bridge30_Virtual_DeltaH_LGA_计算手册.md` §14）按 raw dot 选出的 Top-K：

```text
LLaVA visual dot Top-5: 30, 29, 28, 21, 27
LLaVA text   dot Top-5: 30, 29, 28, 27, 26
BLIP2 visual dot Top-5: 30, 29, 28, 27, 26
BLIP2 text   dot Top-5: 24, 26, 27, 30, 29
```

两套排序在 visual / text 上几乎都集中在 27-31 的尾段层，与扫层 oracle 的中段层不重合。直接证据：

```text
LLaVA visual S_v_new_norm: layer 30 = 0.0033, layer 5 = 0.232 (差 ~70 倍)
BLIP2 visual S_v_new_norm: layer 30 = 0.084,  layer 10 = 0.437 (差 ~5 倍)
```

即 raw dot 在跨层比较时被梯度模长主导，无法表征"old/new 梯度方向是否一致"这一原始物理含义。因此需要校准指标。

## 2. 数据来源

### 2.1 Oracle（扫层真值）

直接读取已有评测产物：

```text
LLaVA:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv

BLIP2:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2/eval_same_entity_full_metrics_rephrase_split/selected_full_metrics_summary.tsv
```

每个文件含 32 行 × 至少以下列：

```text
layer
request
generality, generality.text_rephrase, generality.image_rephrase
locality,  locality.text_loc,        locality.image_loc
portability, portability.port_1,     portability.port_2
status
```

### 2.2 LGA 指标（候选预测量）

直接读取已有产物：

```text
LLaVA:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga/request_only_20260515_202232/llava-v1.5-7b/virtual_delta_h_layer_scores.csv
sample_virtual_delta_h_scores.jsonl

BLIP2:
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga/request_only_20260515_202232/blip2-opt-2.7b/virtual_delta_h_layer_scores.csv
sample_virtual_delta_h_scores.jsonl
```

`virtual_delta_h_layer_scores.csv` 至少含：

```text
model, layer, n_request, visual_token_scope, text_token_scope
S_v_dot, S_v_conflict, S_v_dot_per_dim, S_v_cos
S_v_old_norm, S_v_new_norm, S_v_joint_norm
v_positive_ratio, v_zero_grad, v_dot_rank, v_new_norm_rank
S_t_dot, S_t_conflict, S_t_dot_per_dim, S_t_cos
S_t_old_norm, S_t_new_norm, S_t_joint_norm
t_positive_ratio, t_zero_grad, t_dot_rank, t_new_norm_rank
```

若个别字段缺失（例如 `positive_ratio`），从 `sample_virtual_delta_h_scores.jsonl` 重新聚合，不重跑 forward。

## 3. 候选 LGA 指标清单

每个模态分支（visual / text）分别评估，命名上 visual 加 `_v` 后缀，text 加 `_t` 后缀，下表以 visual 为例：

### 3.1 方向类（去模长）

```text
M_cos        = S_v_cos
M_pos_ratio  = v_positive_ratio
```

### 3.2 幅度类（去方向）

```text
M_new_norm   = S_v_new_norm
M_old_norm   = S_v_old_norm
M_joint_norm = S_v_joint_norm
```

### 3.3 原始类（保留 Golden Layer 风格，作对照基线）

```text
M_dot         = S_v_dot
M_conflict    = S_v_conflict = -S_v_dot
M_dot_per_dim = S_v_dot_per_dim
```

### 3.4 复合类（候选主指标）

```text
M_newn_x_1mcos   = S_v_new_norm * (1 - S_v_cos)
M_newn_x_pos     = S_v_new_norm * v_positive_ratio
M_abscos_x_newn  = abs(S_v_cos) * S_v_new_norm
M_conflict_x_newn= S_v_conflict * S_v_new_norm
```

text 分支同构，把 `_v` 换成 `_t`。

## 4. 退化层过滤

zero-gradient 层不进入主排序（避免 raw dot 把"无梯度"误判为"方向一致"）：

```text
filter rule: M_new_norm < eps_filter
eps_filter (fp32): 1e-6
```

具体到现有数据：

```text
LLaVA visual: layer 31 (new_norm=0)，layer 30 边界 (new_norm=0.0033) 不过滤
LLaVA text:   layer 31
BLIP2 visual: layer 31
BLIP2 text:   layer 31
```

输出两套结果：

```text
filtered:   过滤 zero-grad 后的排序
unfiltered: 保留全部 32 层
```

主表用 filtered，附录给 unfiltered，明确指标对退化层的鲁棒性。

## 5. Oracle 多轴定义

不加权，分轴评估。共 3 个判别主轴 + 1 个 sanity 轴 + 4 个子轴：

```text
判别主轴（用于排序与 agg）：
  O_generality  = generality                    # 泛化
  O_portability = portability                   # 编辑迁移
  O_locality    = locality                      # 保留性（与编辑反向）

Sanity 轴（仅用于自检，不进 agg、不参与排序）：
  O_request     = request                       # 训练数据上的编辑目标达成度

子轴（用于解释 visual vs text 分布）：
  O_gen_text  = generality.text_rephrase
  O_gen_image = generality.image_rephrase
  O_loc_text  = locality.text_loc
  O_loc_image = locality.image_loc
```

约定：

```text
locality 在排序与 Spearman 单轴计算时按"高=好"原样使用，不取反；
跨轴汇总 agg(M) 时，对 locality 轴使用 -rho(M, O_locality) 转同向（见 §6.3）；
原因：编辑越彻底 locality 越低，预测编辑性的指标天然与 O_locality 负相关。

为什么把 request 从判别主轴里剥离：
Bridge30 测试集与训练集同源，训练以 EMA loss = 0.0003 收敛，
按设计就要在 request 列上接近 1.0，这是"编辑目标是否达成"的 sanity check，
而不是层间区分度的来源。把 request 当判别轴会让 agg 被无信息轴拉为 0。
```

## 6. 评估方法

### 6.1 Spearman / Pearson（主）

每个候选指标 M × 每个 oracle 轴 O：

```text
rho_spearman(M, O), p_spearman
r_pearson(M, O),    p_pearson
```

主表只展示 Spearman；Pearson 进附录。

### 6.2 Top-K 命中率（辅）

```text
topk_hit(M, O, K) = |Top-K(M) ∩ Top-K(O)| / K
K ∈ {1, 3, 5}
```

并行报告：

```text
top1_layer(M)   vs  top1_layer(O)
top3_layers(M)  vs  top3_layers(O)
top5_layers(M)  vs  top5_layers(O)
```

### 6.3 跨轴汇总（每模态的主指标提名）

对每个候选指标 M，在 3 个判别主轴上做几何均值（locality 取负号转同向），request 仅作 sanity，不入 agg：

```text
agg(M) = geomean( max(rho(M, O_generality),  0),
                  max(rho(M, O_portability), 0),
                  max(-rho(M, O_locality),   0) )
```

说明：

```text
locality 与编辑方向相反，rho 越负越好，因此 -rho 转正同向
负值剪到 0：保证 geomean 不出现复数；负相关的指标在该轴被判为"无预测力"
仅作"提名"用，论文写作时仍以单轴 Spearman + Top-K 为主证据
request 不进 agg：Bridge30 测试集 = 训练集，request 已被 EMA loss 训练目标
  压到接近 1.0 的常数，本身不带层间判别信号，纳入会无谓地把 geomean 拉为 0
```

### 6.4 平均秩差（辅）

```text
rank_dist(M, O) = mean_l |rank_M(l) - rank_O(l)|
```

用于补充看尾部偏差。

## 7. 报告内容

每个模型 × 每个模态分支输出一张主表，列：

```text
metric_name
rho(O_request),    p
rho(O_generality), p
rho(O_portability),p
rho(O_locality),   p
agg
top1_hit(O_main_axis)
top3_hit(O_main_axis)
top5_hit(O_main_axis)
top1_layer(M)
top3_layers(M)
```

`O_main_axis` 设为：

```text
visual 分支主轴：O_generality
text   分支主轴：O_generality
locality / portability 单独成表作交叉证据
```

理由：generality 是拟合 + 泛化的核心目标，且在两套扫层结果上区分度最大；portability 数值范围较小、波动大，做主轴会引入噪声；locality 与 oracle 关系反向，更适合作"代价侧"对照。

## 8. 决策规则（写入 Result.md 的口径）

胜出顺位：

```text
1. 在 visual / text 各自的 O_generality 轴上 Spearman 最高，且 p < 0.05；
2. 若并列，看 4 轴 agg；
3. 若仍并列，看 Top-3 命中率；
4. 若 raw dot 进入前 3，仍保留它作 baseline 对照，但不作主指标。
```

明确：

```text
"raw dot 不胜出" 必须给出 §1 中的梯度模长跨层差的数值证据，并附 §6.1 的负 / 弱 Spearman 数值。
```

## 9. 产物清单

本次实验安排只写规则与脚本接口，不强制执行。后续若执行，应有：

```text
脚本：
  scripts/bridge_vlm_lga_metric_calibration.py

输入：
  --llava-eval-tsv  selected_full_metrics_summary.tsv (llava)
  --blip2-eval-tsv  selected_full_metrics_summary.tsv (blip2)
  --llava-lga-csv   virtual_delta_h_layer_scores.csv  (llava)
  --blip2-lga-csv   virtual_delta_h_layer_scores.csv  (blip2)
  --eps-filter      1e-6
  --topk            1,3,5
  --output-dir      server_results/bridge_vlm_virtual_delta_h_lga/request_only_20260515_202232/metric_calibration

输出：
  {output-dir}/{model}/per_axis_spearman.csv
  {output-dir}/{model}/per_axis_pearson.csv
  {output-dir}/{model}/per_axis_topk_hit.csv
  {output-dir}/{model}/per_metric_rank_dist.csv
  {output-dir}/{model}/per_axis_winner.json
  {output-dir}/{model}/summary.md
  {output-dir}/cross_model_overview.md
```

`per_axis_winner.json` 形如：

```json
{
  "model": "llava-v1.5-7b",
  "modality": "visual",
  "main_axis": "generality",
  "winner": {
    "name": "M_newn_x_1mcos",
    "spearman": 0.xx,
    "p": 0.xx,
    "top3_hit_generality": 0.xx,
    "top3_layers": [..]
  },
  "raw_dot_baseline": {
    "spearman": 0.xx,
    "p": 0.xx,
    "top3_hit_generality": 0.xx,
    "top3_layers": [30, 29, 28]
  },
  "ranking_full": [{"name": "...", "spearman": 0.xx}, ...]
}
```

## 10. 不在本次范围（YAGNI）

```text
不新训 visual / text adapter
不扫文本分支 adapter
不做 visual × text 组合层联合实验
不做跨模型迁移
不重算 Virtual Δh
不引入 generality / portability 加权复合 oracle
```

以上每一项都可在本次结论得出后单独开新实验安排。

## 11. 完整性自检清单

执行脚本完成后，需通过以下检查：

```text
oracle 行数 = 32 (LLaVA) + 32 (BLIP2)
lga 行数  = 32 (LLaVA) + 32 (BLIP2)
metric 数 = visual 12 + text 12
spearman 表非空，无 NaN（zero-grad 行除外）
filtered / unfiltered 各出一份
raw dot baseline 在所有表中显式标注
summary.md 含：
  - 每模态推荐主指标
  - 与 raw dot 的对比
  - 模长跨层差证据
  - locality 反向同向化口径
```

## 12. 状态

```text
文档状态：实验安排已对齐，等待编写 scripts/bridge_vlm_lga_metric_calibration.py
下一步：编写实施计划（writing-plans），随后才进入脚本实现
```

## 13. 实际执行结果

执行时间：`2026-05-16 19:05:05 +08:00`

本次实验没有重新训练 adapter，也没有重跑 Virtual Δh，只读取已有 oracle 与 LGA 指标表做 calibration。

### 13.1 执行产物

新增脚本：

```text
VisEdit-main/scripts/bridge_vlm_lga_metric_calibration.py
```

远端输出目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_vlm_virtual_delta_h_lga/request_only_20260515_202232/metric_calibration
```

本地结果备份：

```text
downloads/Temp/bridge_lga_metric_calibration_request_only_20260516/
```

实际读取的 LGA 文件与第 2.2 节计划路径略有不同。第 2.2 节写的是：

```text
llava-v1.5-7b/virtual_delta_h_layer_scores.csv
blip2-opt-2.7b/virtual_delta_h_layer_scores.csv
```

实际 Virtual Δh 实验产物路径是：

```text
llava/virtual_delta_h_lga_layer_scores.csv
blip2/virtual_delta_h_lga_layer_scores.csv
```

本次 calibration 按实际产物执行。

### 13.2 Cross-Model Overview

主轴：`generality`。主表使用 `filtered` 结果，即按模态过滤 `new_norm < 1e-6` 或 zero-gradient 层。

| Model | Modality | Winner | rho(generality) | p | agg | top3_hit | top1 | top3 | Raw-dot rho(generality) | Raw-dot top3 | Dropped |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---|
| llava-v1.5-7b | visual | M_newn_x_1mcos | 0.877685 | 9.02747e-11 | 0 | 0.333333 | 6 | `[6, 7, 5]` | -0.836342 | `[30, 29, 28]` | `[31]` |
| llava-v1.5-7b | text | M_new_norm | 0.862761 | 4.33629e-10 | 0 | 0.333333 | 0 | `[0, 1, 2]` | -0.860946 | `[30, 29, 28]` | `[31]` |
| blip2-opt-2.7b | visual | M_abscos_x_newn | 0.487458 | 0.00541185 | 0 | 0 | 13 | `[13, 15, 14]` | -0.245246 | `[30, 29, 28]` | `[31]` |
| blip2-opt-2.7b | text | M_abscos_x_newn | 0.296238 | 0.105628 | 0 | 0.333333 | 10 | `[10, 8, 7]` | 0.160867 | `[24, 26, 27]` | `[31]` |

说明：

```text
locality 在单轴 Spearman 中仍按 high-is-good 原样计算；
只在 agg 中使用 -rho(locality) 转成编辑同向。
```

`agg` 本次全部为 0，主要原因是 request 轴几乎/完全饱和，`rho(request)` 被判为 0；因此本次主结论以 `generality` 单轴 Spearman 与 Top-K 为准，`agg` 只保留为兼容字段。

### 13.3 推荐主指标

按第 8 节决策规则，并额外避免把负相关显著指标作为 winner，得到如下建议：

```text
LLaVA visual: M_newn_x_1mcos
LLaVA text:   M_new_norm
BLIP2 visual: M_abscos_x_newn
BLIP2 text:   M_abscos_x_newn
```

BLIP2 text 需要谨慎解释：

```text
M_abscos_x_newn 是正相关最高指标，但 p=0.105628，未达到 p<0.05。
因此 BLIP2 text 分支只能写作“弱证据候选指标”，不能写作显著胜出指标。
```

### 13.4 Raw Dot Baseline 结论

raw dot 不适合作为本次 Virtual Δh LGA 的主指标，原因是它在 LLaVA 上与 generality oracle 强负相关：

```text
LLaVA visual raw dot: rho(generality) = -0.836342
LLaVA text raw dot:   rho(generality) = -0.860946
BLIP2 visual raw dot: rho(generality) = -0.245246
BLIP2 text raw dot:   rho(generality) =  0.160867
```

其 Top-K 也明显偏向尾段层：

```text
LLaVA visual raw dot Top-3: [30, 29, 28]
LLaVA text raw dot Top-3:   [30, 29, 28]
BLIP2 visual raw dot Top-3: [30, 29, 28]
BLIP2 text raw dot Top-3:   [24, 26, 27]
```

这与真实 adapter 全层 sweep 的 generality 峰值层不一致。尤其在 LLaVA 上，raw dot 实际把高层低模长区域排在前面，和泛化效果呈反向关系。

### 13.5 模长证据

校准脚本自动记录了 `new_norm` 跨层差异：

```text
LLaVA visual: layer30 S_v_new_norm = 0.00326963，max layer6 = 0.233242，ratio = 71.3358
LLaVA text:   layer30 S_t_new_norm = 0.0179594，max layer0 = 2.75488，ratio = 153.395
BLIP2 visual: layer30 S_v_new_norm = 0.0842449，max layer0 = 0.464769，ratio = 5.51688
BLIP2 text:   layer30 S_t_new_norm = 0.00831287，max layer0 = 0.851369，ratio = 102.416
```

这支持第 1 节判断：raw dot 的跨层排序会被梯度模长与退化层共同影响，不能直接作为最终主指标。

### 13.6 完整性自检

```text
oracle 行数：LLaVA 32 + BLIP2 32
lga 行数：LLaVA 32 + BLIP2 32
metric 数：visual 12 + text 12
filtered / unfiltered 均已输出
zero-gradient 过滤层：LLaVA visual/text layer31；BLIP2 visual/text layer31
raw dot baseline 已显式保留
summary.md、per_axis_winner.json、per_axis_spearman.csv、per_axis_topk_hit.csv 已生成
```

本地备份已补齐。第一次备份时 g07 出现短暂 SSH 超时，随后已重新连接并补拉 BLIP2 明细 CSV：

```text
blip2-opt-2.7b_per_axis_spearman.csv
blip2-opt-2.7b_per_axis_topk_hit.csv
```

## 14. 结果分析

### 14.1 Winner Top-3 与扫层 oracle 峰值的对照

把 §13.2 的 winner Top-3 直接和 `Bridge30_RequestOnly_*_FullLayerSweep_训练评测手册.md` §7.3 / §12.3 的 generality 列对照（取同源 Same-Entity Full Metrics）：

| Model | Modality | Winner Top-3 | Top-3 各层 gen | Sweep gen Top-3（按值排序）| 是否覆盖峰值 |
|---|---|---|---|---|---|
| LLaVA | visual | `[6, 7, 5]` | 0.9729 / **0.9808** / 0.9718 | `[7, 4, 1]` (0.9808 / 0.9800 / 0.9753) | 命中峰值层 7 |
| LLaVA | text | `[0, 1, 2]` | 0.9750 / 0.9753 / 0.9584 | `[7, 4, 1]` | 仅命中第 3 名层 1 |
| BLIP2 | visual | `[13, 15, 14]` | 0.9887 / **1.0000** / 0.9983 | `[8, 9, 12]` (并列 1.0) | 命中并列峰值层 15 |
| BLIP2 | text | `[10, 8, 7]` | 0.9979 / **1.0000** / 0.9839 | `[8, 9, 12]` (并列 1.0) | 命中并列峰值层 8 |

结论：

```text
LLaVA visual 与 BLIP2 visual / text winner 都至少命中 1 个 oracle generality 峰值层；
LLaVA text 没有命中绝对峰值（层 7），但 Top-3 都是 gen ≥ 0.958 的高分层，绝对值损失不大；
Top-3 命中率被 oracle 内部并列与 tie-break 顺序压低（BLIP2 visual 报为 0 是 tie-break 错位，
真实情况是命中了 1.0 并列峰），后续报告需区分 "tie-aware hit rate" 与原始 hit rate。
```

### 14.2 raw dot 在 LLaVA 上的强负相关解读

LLaVA 上 raw dot 与 O_generality 的 Spearman 达到 −0.84 / −0.86，且 p ≪ 0.05，是本次校准最强的反向证据。机制可拆成两层：

```text
1. 跨层模长断崖：layer30 / max_layer 比例 = 71.3 (visual) / 153.4 (text)。
   raw dot ≈ ||g_old||·||g_new||·cos，模长项把"几乎无梯度的高层"误顶到 Top；
2. cos 主导方向：高层 cos 接近 0，dot 接近 0；中段 cos 显著负 ⇒ dot 显著负；
   两者叠加后，dot 的层间排序几乎与 layer 深度成反向单调，正好与 sweep 的"中段
   gen 高、尾段 gen 低" 反过来对齐。
```

这解释了为什么对 LLaVA 沿用 Golden Layer 风格的 raw dot 会把人引到错的层。BLIP2 上 raw dot 不显著（visual rho=−0.25, text rho=+0.16），不是因为它正确，而是因为 BLIP2 自身 new_norm 跨层比 (5.5 / 102.4) 比 LLaVA 平缓，模长偏倚被稀释，但也没有真正反映方向。

### 14.3 各 (model, modality) winner 不一致的解读

四个分支 winner 不同：

```text
LLaVA visual: M_newn_x_1mcos    复合（杠杆 × 方向冲突度）
LLaVA text:   M_new_norm        纯杠杆
BLIP2 visual: M_abscos_x_newn   复合（|方向| × 杠杆）
BLIP2 text:   M_abscos_x_newn   同上，但 p=0.106 不显著
```

可读出的两条规律：

```text
A. 杠杆项 new_norm 在四个分支都进入 winner 的乘积里，是必要因子；
B. 单纯 cos 在所有分支都没能单独胜出，方向项必须乘以杠杆才有效。
```

LLaVA text winner 是纯 `M_new_norm`，需要给一段额外的"单调共因"风险声明：

```text
LLaVA text 的 new_norm 在 0-31 层近似单调下降；
LLaVA text 的 generality 在同一区间也呈"前段高、后段低"的近似单调；
两者的高 Spearman 可能部分来自共同的深度趋势，而不是"new_norm 高 ⇒ 编辑成功"的因果链。
后续若把 M_new_norm 写入论文，应补做控制 layer 的偏相关 (partial Spearman | layer)。
```

### 14.4 BLIP2 信号普遍偏弱的原因

BLIP2 winner 的 Spearman 范围是 0.30-0.49，远低于 LLaVA 的 0.86-0.88。三条候选解释：

```text
1. Oracle 饱和：BLIP2 same-entity generality 在 6 个层并列 1.0，oracle 内部秩本身有噪音；
2. 杠杆动态范围窄：BLIP2 visual new_norm ratio 仅 5.5×，方向 / 杠杆区分度被压扁；
3. Q-Former 结构：视觉信息经 Q-Former 压缩为少量 query，token 级 Δh 在 layer 间扩散
   模式与 LLaVA 直接 patchify 投影不同，单层 LGA 的预测力受限。
```

任意一条单独都不致命，但叠加后导致 BLIP2 text 没有任何指标越过 p<0.05。这一点要在 Result.md 里如实写明。

### 14.5 agg=0 的成因与处理

`agg(M)` 在初版执行里全为 0，根因不是数据问题，而是 §5 / §6.3 初稿把 `O_request` 当成了判别主轴：

```text
Bridge30 测试集与训练集同源，训练的设计目标就是把 request 列的 EMA loss
压到 ≈ 0.0003，让模型在训练样本上输出新目标。也就是说 request ≈ 1.0
在收敛后是被设计强制出来的 sanity check，而不是层间的判别信号。
把这样一个近常数轴塞进 geomean，只要它的 rho 被剪到 0，整个 agg 就归零，
和其他三个轴的真实判别力无关。
```

修正口径（已在 §5 / §6.3 落地）：

```text
1. 把 O_request 从判别主轴中移除，标注为 sanity 轴；
2. agg(M) 改为在 {generality, portability, -locality} 三轴上做几何均值；
3. 把 request 作为独立的"目标达成度"指标在 summary.md 里单独报告，
   只用来验证编辑确实生效，不用来排序层。
```

修正后预期：agg 不再被无信息轴拉零，但 §13.2 的四个 winner 应该不会换人——它们是从单轴 `rho(generality)` 的最大者里选出的，与 agg 无关；agg 只是从一个误导性的 0 变成一个有意义的提名分。脚本侧另需加一道防御性 `auto-drop` 策略，防止未来其他轴出现 std → 0 的退化情况时再把 agg 拖崩：

```text
auto-drop policy: 若 oracle 轴的 std < 1e-6 或唯一值数 < 3，
  该轴在 agg 中被跳过；
  agg(M) 改为 "在生效轴上的几何均值"，并记录 effective_axes 字段。
```

### 14.6 结论写入 Result.md 的口径建议

可以直接落到论文里的话术：

```text
1. 在 Bridge30 request-only 视觉 adapter 32 层扫层 oracle 上，Virtual Δh LGA 的
   原始 dot 指标在 LLaVA 上与 generality 强负相关 (ρ=−0.84/−0.86, p≪0.001)，
   在 BLIP2 上无显著正相关；不能直接作为层选指标。
2. 推荐主指标：
     LLaVA visual: new_norm × (1 − cos)，ρ=0.88，命中扫层 gen 峰值层 7；
     BLIP2 visual: |cos| × new_norm，ρ=0.49，命中扫层 gen 并列峰值层 15；
     LLaVA text:   new_norm（带单调共因风险声明）；
     BLIP2 text:   无任何指标显著（p>0.05），暂不推荐。
3. 不同模态、不同模型上 winner 不一致，但共同点是 "杠杆 (new_norm) 必须参与"，
   方向项 (cos) 单独不胜出；这与"raw dot 受模长断崖污染"的物理解释一致。
```

### 14.7 紧接的待办

```text
1. 修 calibration 脚本的 agg 退化轴策略（§14.5）；
2. 给 LLaVA text 加 partial Spearman(M_new_norm, gen | layer) 的偏相关检验（§14.3）；
3. 给 Top-K 命中率加 tie-aware 版本（§14.1），用于汇报 BLIP2；
4. 视野外但建议预留：把 proxy set 从 Bridge30 扩到 Bridge100，看 BLIP2 信号是否走出噪声。
```

