# VisEdit 不同数据集每层训练用时统计

更新时间：2026-06-12

本文统计 VisEdit/VEAD 真实扫层训练时，不同模型在不同数据集上“每一层训练每个 epoch 用时”和“单层完整训练用时”。当前已能从 `loss_history.csv` 直接读到的主要是 pilot500 结果；MMKE-Visual / MMKE-Entity 目前没有发现对应真实扫层训练日志，不能用贡献度分析文件替代训练用时。

## 统计口径

- 数据集：`pilot500`，`mmke-visual`，`mmke-entity`。
- 训练对象：每次只训练一个候选层，换层重新初始化 adapter，不加载其他层保存的 adapter。
- 用时口径：优先用相邻 epoch checkpoint 的时间差估算 `每 epoch 用时`。
- 单层训练用时：`每 epoch 用时 x epoch 数`。如果日志里有模型加载、预处理、评测时间，则单独说明。
- 当前扫层默认：pilot500 每层 50 epoch，batch size 多数为 2。

## 7 个实验模型

| 序号 | 模型 | 当前运行状态 |
|---:|---|---|
| 1 | BLIP2-OPT-2.7B | pilot500 已有实测训练日志 |
| 2 | InstructBLIP-Vicuna-7B | pilot500 top-3 已完成并拉回本地 |
| 3 | MiniGPT-4-Vicuna-7B | pilot500 排队/待完成 |
| 4 | LLaVA-v1.5-7B | pilot500 L28 正在训练，已有阶段性速度 |
| 5 | Qwen2.5-VL-3B | pilot500 排队/待完成 |
| 6 | PaliGemma-3B | wrapper/config 已补，待完整训练日志 |
| 7 | SmolVLM-Instruct-1.7B | wrapper/config 已补，待完整训练日志 |

## Pilot500 已实测/可估算用时

### 汇总表

| 数据集 | 模型 | 层 | epoch 数 | 每 epoch 用时 | 单层训练用时 | 依据 |
|---|---|---:|---:|---:|---:|---|
| pilot500 | BLIP2-OPT-2.7B | L0 | 50 | 约 3 分 10 秒 | 约 2 小时 38 分 | 原始有效 L0 run |
| pilot500 | BLIP2-OPT-2.7B | L5 | 50 | 约 3 分 32 秒 | 约 2 小时 56 分 | 修正后 fixed rerun |
| pilot500 | BLIP2-OPT-2.7B | L10 | 50 | 约 2 分 42 秒 | 约 2 小时 15 分 | 修正后 fixed rerun |
| pilot500 | BLIP2-OPT-2.7B | L15 | 50 | 约 2 分 29 秒 | 约 2 小时 04 分 | 修正后 fixed rerun |
| pilot500 | BLIP2-OPT-2.7B | L19 | 50 | 约 2 分 16 秒 | 约 1 小时 53 分 | 修正后 fixed rerun |
| pilot500 | BLIP2-OPT-2.7B | L25 | 50 | 约 2 分 07 秒 | 约 1 小时 46 分 | 修正后 fixed rerun |
| pilot500 | BLIP2-OPT-2.7B | L30 | 50 | 约 2 分 00 秒 | 约 1 小时 40 分 | 修正后 fixed rerun |
| pilot500 | InstructBLIP-Vicuna-7B | L28 | 50 | 约 2 分 23 秒 | 约 1 小时 59 分 | 本地 loss_history |
| pilot500 | InstructBLIP-Vicuna-7B | L27 | 50 | 约 2 分 34 秒 | 约 2 小时 09 分 | 本地 loss_history |
| pilot500 | InstructBLIP-Vicuna-7B | L26 | 50 | 约 2 分 45 秒 | 约 2 小时 18 分 | 本地 loss_history |
| pilot500 | LLaVA-v1.5-7B | L28 | 50 | 约 30 分 05 秒 | 约 25 小时 05 分 | 服务器运行中日志 |
| pilot500 | LLaVA-v1.5-7B | L27/L26 | 50 | 预计约 30 分钟 | 预计约 25-26 小时/层 | 按 L28 当前速度估算 |
| pilot500 | MiniGPT-4-Vicuna-7B | top-3 候选层 | 50 | 待实测 | 待实测 | 训练排队/未拉回日志 |
| pilot500 | Qwen2.5-VL-3B | top-3 候选层 | 50 | 待实测 | 待实测 | 训练排队/未拉回日志 |
| pilot500 | PaliGemma-3B | top-3 候选层 | 50 | 待实测 | 待实测 | 已做环境/配置准备，待完整训练 |
| pilot500 | SmolVLM-Instruct-1.7B | top-3 候选层 | 50 | 待实测 | 待实测 | 已做环境/配置准备，待完整训练 |

### BLIP2-OPT-2.7B 细表

日志目录：

`downloads/Location/blip2_pilot500_fixed_epoch50_loss_curves_20260602`

来源确认：本表不是来自早期错误绑定目录 `downloads/Location/blip2_pilot500_visedit_loss_curves_20260601`。根据 `md/Location/pliot500_50_testfull_outcome.md` 的记录，`L0` 使用原始有效 run；`L5/L10/L15/L19/L25/L30` 使用修复 wrapper 后的 fixed rerun，并按 layer 独立进程评测。

错误绑定 run 的用时明显偏短，例如 L5 为约 1 小时 52 分、L10 为约 1 小时 47 分、L15 为约 1 小时 39 分、L19 为约 1 小时 40 分；这些不作为后续真实扫层训练用时估计。

| 层 | epoch1 时间 | epoch50 时间 | epoch1 到 epoch50 | 平均每 epoch | 50 epoch 估算 |
|---:|---|---|---:|---:|---:|
| L0 | 2026-06-01 00:28:57 | 2026-06-01 03:04:00 | 2 小时 35 分 03 秒 | 约 3 分 10 秒 | 约 2 小时 38 分 |
| L5 | 2026-06-01 14:52:08 | 2026-06-01 17:45:17 | 2 小时 53 分 09 秒 | 约 3 分 32 秒 | 约 2 小时 56 分 |
| L10 | 2026-06-01 17:53:49 | 2026-06-01 20:05:57 | 2 小时 12 分 08 秒 | 约 2 分 42 秒 | 约 2 小时 15 分 |
| L15 | 2026-06-01 20:14:12 | 2026-06-01 22:15:41 | 2 小时 01 分 29 秒 | 约 2 分 29 秒 | 约 2 小时 04 分 |
| L19 | 2026-06-01 22:23:51 | 2026-06-02 00:14:43 | 1 小时 50 分 52 秒 | 约 2 分 16 秒 | 约 1 小时 53 分 |
| L25 | 2026-06-02 00:23:15 | 2026-06-02 02:06:45 | 1 小时 43 分 30 秒 | 约 2 分 07 秒 | 约 1 小时 46 分 |
| L30 | 2026-06-02 02:14:40 | 2026-06-02 03:52:29 | 1 小时 37 分 49 秒 | 约 2 分 00 秒 | 约 1 小时 40 分 |

说明：BLIP2 的深层候选层明显比浅层快。当前可作为 BLIP2 后续 pilot500 单层 50 epoch 的时间估计范围：约 1 小时 40 分到 3 小时。

### InstructBLIP-Vicuna-7B 细表

日志目录：

`downloads/contribution_pre_7_models/instructblip-vicuna-7b`

| 层 | epoch1 时间 | epoch50 时间 | epoch1 到 epoch50 | 平均每 epoch | 50 epoch 估算 |
|---:|---|---|---:|---:|---:|
| L28 | 2026-06-08 09:40:17 | 2026-06-08 11:37:18 | 1 小时 57 分 01 秒 | 约 2 分 23 秒 | 约 1 小时 59 分 |
| L27 | 2026-06-08 13:21:29 | 2026-06-08 15:27:37 | 2 小时 06 分 08 秒 | 约 2 分 34 秒 | 约 2 小时 09 分 |
| L26 | 2026-06-08 15:36:30 | 2026-06-08 17:51:26 | 2 小时 14 分 56 秒 | 约 2 分 45 秒 | 约 2 小时 18 分 |

### LLaVA-v1.5-7B 阶段性用时

服务器日志目录：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_pre_alt_pilot500_6models_20260608_092829/llava-v1.5-7b`

| 层 | 当前状态 | 已观测区间 | 平均每 epoch | 50 epoch 估算 | 备注 |
|---:|---|---|---:|---:|---|
| L28 | 运行中 | epoch9 到 epoch16 | 约 30 分 05 秒 | 约 25 小时 05 分 | train start 到 epoch1 还包含加载、预处理和首轮训练 |
| L27 | 未开始/待排队 | 无 | 预计约 30 分钟 | 预计约 25-26 小时 | 需等 L28 完成后更新 |
| L26 | 未开始/待排队 | 无 | 预计约 30 分钟 | 预计约 25-26 小时 | 需等 L27 完成后更新 |

当前可用结论：LLaVA-v1.5-7B 在 pilot500 上每个 epoch 约 30 分钟，50 epoch 一层训练约 25 小时。top-3 三层完整训练预计约 75-78 小时，不含最终测试集评测时间。

## BLIP2 与 LLaVA 单层训练用时差距说明

相同训练数据、相同 epoch 数下，LLaVA-v1.5-7B 一层约 25 小时，而 BLIP2-OPT-2.7B 一层约 2 小时左右，这个差距基本合理。不能只按参数量比较，真正决定训练耗时的是进入文本 decoder 的视觉 token 数、decoder hidden size、序列长度带来的 attention/activation 开销，以及训练实现中是否重复计算视觉编码。

| 对比项 | BLIP2-OPT-2.7B | LLaVA-v1.5-7B | 对训练用时的影响 |
|---|---:|---:|---|
| 总参数量 | 约 2.7B | 约 7B | LLaVA 文本 decoder 本身更重 |
| 视觉 token 数 | 约 32 个 Q-Former query token | 约 576 个 image patch token | LLaVA decoder 输入序列显著更长 |
| 视觉表征是否压缩 | 是，Q-Former 压缩后进入 OPT | 否，patch token 直接投影进 LLaMA | BLIP2 的视觉前缀计算压力小很多 |
| 文本 hidden size | OPT-2.7B 约 2560 | LLaMA-7B 约 4096 | LLaVA 单 token 的 MLP/attention 投影更贵 |
| pilot500 每 epoch step 数 | 约 250 step | 约 250 step | 数据量相同，单 step 耗时差异更能反映模型计算量 |
| 已观测每 epoch 用时 | 约 2-3.5 分钟 | 约 30 分钟 | LLaVA 约慢 9-15 倍 |
| 已观测每 step 用时 | 约 0.5-0.8 秒 | 约 7.2 秒 | 与视觉 token 和 decoder 规模差异一致 |

关键判断：

1. BLIP2 的图像信息先经过 Q-Former 压缩成约 32 个 query token，再送入 OPT decoder，所以 decoder 处理的视觉前缀很短。
2. LLaVA-v1.5-7B 通常使用 CLIP ViT-L/14-336，图像被展开为约 24 x 24 = 576 个视觉 token，再投影进 LLaMA decoder，self-attention 和激活保存开销都明显更大。
3. 即使训练时只更新 adapter，base VLM 仍然需要参与前向计算，并且为了把梯度传到 adapter，目标层附近的 activation/反向图仍有明显开销。
4. 如果视觉特征没有预缓存，每个 epoch 还会重复做图像预处理和视觉编码，LLaVA 的图像侧开销也会被放大。

因此，`BLIP2 单层约 1.7-3.0 小时` 与 `LLaVA 单层约 25 小时` 的量级差异可以接受。后续只需要额外检查 LLaVA 训练时的 GPU 利用率：如果 GPU 利用率长期很低，则优先排查 dataloader、图片 I/O、CPU 预处理或不必要的重复加载；如果 GPU 利用率较高，则该耗时主要来自正常计算成本。

## MMKE-Visual / MMKE-Entity 用时占位表

下面两张表只记录真实扫层训练的运行时间状态。已有的 MMKE module contribution/attribution 图和 CSV 不能替代 VisEdit adapter 训练用时。

### MMKE-Visual

| 数据集 | 模型 | epoch 设置 | 每 epoch 用时 | 单层训练用时 | 状态 |
|---|---|---:|---:|---:|---|
| mmke-visual | BLIP2-OPT-2.7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-visual | InstructBLIP-Vicuna-7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-visual | MiniGPT-4-Vicuna-7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-visual | LLaVA-v1.5-7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-visual | Qwen2.5-VL-3B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-visual | PaliGemma-3B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-visual | SmolVLM-Instruct-1.7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |

### MMKE-Entity

| 数据集 | 模型 | epoch 设置 | 每 epoch 用时 | 单层训练用时 | 状态 |
|---|---|---:|---:|---:|---|
| mmke-entity | BLIP2-OPT-2.7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-entity | InstructBLIP-Vicuna-7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-entity | MiniGPT-4-Vicuna-7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-entity | LLaVA-v1.5-7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-entity | Qwen2.5-VL-3B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-entity | PaliGemma-3B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |
| mmke-entity | SmolVLM-Instruct-1.7B | 待定 | 待实测 | 待实测 | 未发现真实扫层训练日志 |

## 换算公式

| 目标 | 公式 |
|---|---|
| 单层训练时间 | `T_layer = T_epoch x epoch_num` |
| top-3 训练时间 | `T_top3 = T_layer(L_a) + T_layer(L_b) + T_layer(L_c)` |
| top-5 训练时间 | `T_top5 = sum(T_layer for 5 candidate layers)` |
| 总耗时 | `T_total = T_train + T_eval + T_model_load + T_preprocess` |

示例：

| 模型 | 数据集 | 每 epoch | 50 epoch 单层 | top-3 训练估算 |
|---|---|---:|---:|---:|
| BLIP2-OPT-2.7B | pilot500 | 约 2-3.5 分钟 | 约 1.7-3.0 小时 | 约 5-9 小时 |
| InstructBLIP-Vicuna-7B | pilot500 | 约 2.4-2.8 分钟 | 约 2.0-2.3 小时 | 约 6.5 小时 |
| LLaVA-v1.5-7B | pilot500 | 约 30 分钟 | 约 25 小时 | 约 75-78 小时 |

## 后续更新规则

新模型或新数据集跑完一层后，优先从该层的 `loss_history.csv` 读取：

1. `epoch1` 的时间。
2. `epoch50` 或最后一个 epoch 的时间。
3. 用 `(最后 epoch 时间 - epoch1 时间) / (epoch_num - 1)` 估算每 epoch 用时。
4. 用 `每 epoch 用时 x epoch_num` 填入单层训练用时。

如果日志中有明确 `[train start]` 和 `[eval start]`，可以额外记录端到端耗时：

`端到端单层耗时 = eval start - train start`

这样可以把“纯训练时间”和“包含加载、预处理、保存、评测前准备的时间”分开。
