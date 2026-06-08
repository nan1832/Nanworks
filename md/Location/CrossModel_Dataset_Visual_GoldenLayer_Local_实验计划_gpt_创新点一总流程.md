# Cross-Model Cross-Dataset Visual Golden Layer Localization 实验计划

## 1. 实验目标

本实验用于验证：在不同多模态模型架构、不同 E-VQA 数据规模上，**request-only 视觉梯度定位方法**能否比现有的 **因果定位** 与 **高贡献层定位** 更准确地预测视觉模态高性能编辑层。

核心问题：
- 视觉梯度定位得到的候选层，是否更接近真实 visual adapter 高性能层。
- 该结论是否跨模型架构成立：压缩型视觉桥接结构（Q-Former，约 32 个视觉 token）与非压缩型视觉投影结构（MLP / projector，多视觉 token）。
- 该结论是否跨数据规模成立：`E-VQA-pilot500` 与 full `E-VQA`。

硬件约束：
- 单卡训练优先使用 A800 80G。
- 统一训练 `batch_size=2`。
- 每个候选层训练 `50 epochs`。
- 若模型在 `bs=2` 下 OOM，则该模型只保留定位指标计算，不进入 adapter 训练验证，除非另开降配实验。

> 已验证：LLaVA-v1.5-7B + VisEdit visual adapter 在 E-VQA 上 `bs=4` 会 OOM，`bs=2` 可跑通单 batch，峰值约 71.7GB。因此本实验统一使用 `bs=2`。

---

## 2. 实验假设

### H1：视觉梯度定位优于因果定位

只使用 request 样本计算视觉表征梯度，能够直接反映编辑目标对视觉 token 表征的层敏感性。相较于逐层 activation corruption / restoration 的因果定位，梯度定位计算成本更低，且候选层更贴近真实 visual adapter 的最优层。

### H2：视觉梯度定位优于高贡献层定位

高贡献层定位通常衡量模型原始推理时哪些层对当前答案贡献大，但编辑层需要的是“可被 adapter 有效改写且能泛化”的位置。视觉梯度定位更接近编辑目标本身，因此应比 activation norm、attention mass、gradient x activation 等贡献指标更能预测高性能编辑层。

### H3：不同架构的视觉高性能层分布不同

预期趋势：
- 压缩型（Q-Former，32 tok）：视觉信息先被压缩成少量 query token，视觉编辑层更可能落在 LLM 中层或中后层。
- 非压缩型（MLP / projector，多 tok）：视觉 token 数量更多，视觉编辑层可能更受浅层视觉-文本融合与中层语义整理共同影响。
- 统一 Transformer 型：视觉与文本 token 早期深度融合，候选层可能更分散，需要单独分析。

---

## 3. 数据集

| Dataset | 用途 | 规模 | 说明 |
|---|---:|---:|---|
| `E-VQA-pilot500` | 快速验证与全层扫描 | train 500 / val 500 | 从 E-VQA train/eval 随机抽取，图片也复制到 proxy 子目录，降低 IO 与调试成本 |

抽取的 pilot500/proxy500 训练集 JSON 在服务器这里：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
对应的 eval500 是：
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json
图片根目录是：/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images

| full `E-VQA` | 最终验证 | train 6345 / eval 2093 | 使用官方 E-VQA 数据与图片路径 |

数据原则：
- 定位阶段只使用 `request`，不使用 generality/locality 的目标信号。
- visual adapter 训练阶段按 VisEdit / E-VQA 视觉编辑设置执行，可使用 Rel / Gen / Loc 训练损失。
- 评测阶段统一报告 E-VQA 六项指标：`Rel`, `T-Gen`, `M-Gen`, `T-Loc`, `M-Loc`, `Avg`。
- 所有标记为 E-VQA 正式评测的结果，必须使用完整 test/eval 集；pilot500 只用于快速调试、候选层筛选和资源预估，不能作为最终 E-VQA 指标。
- 不修改原始 E-VQA 文件；所有 proxy 数据和图片复制到新目录。

---

## 4. 对比方法

### 4.1 Ours：Request-Only Visual Gradient LGA

对每个 request 样本，在每一层视觉表征位置计算编辑目标 loss 对视觉 token 表征的梯度，汇总逐层 LGA 指标。

主指标：
- `M_abscos_x_newn`

辅助指标：
- `M_dot`
- `M_cos`
- `M_new_norm`
- `M_joint_norm`
- `M_conflict`
- `M_dot_per_dim`

输出：
- 每层逐样本指标 JSONL / CSV。
- 每模型、每数据集的 visual Top1 / Top3 / Top5 候选层。

### 4.2 Baseline A：Causal Localization

对每层视觉 token 表征做 causal intervention：
- corruption：扰动或替换该层视觉 token 表征。
- restoration：恢复某层视觉 token 表征，观察目标答案概率或 loss 恢复程度。

层分数：
- `causal_effect = clean_score - corrupted_score` 或 `restoration_gain`。

输出：
- 每层 causal score。
- causal Top1 / Top3 / Top5 候选层。

### 4.3 Baseline B：High-Contribution Layer Localization

不直接优化编辑目标，而是根据原模型推理贡献定位高贡献层。

主基线：
- `grad_x_activation = mean(|h_l * grad_l|)` over visual tokens。

可选辅助基线：
- visual token activation norm。
- answer-token attention to visual tokens。
- integrated gradient 或 saliency score。

输出：
- contribution Top1 / Top3 / Top5 候选层。

---

## 5. 实验模型清单

本实验模型以图中 6 个主模型为核心，并新增 `SmolVLM-Instruct / 1.7B` 作为轻量扩展 sanity check。后续 cross-model 表格、脚本命名和报告默认覆盖这 7 个模型；其中 SmolVLM 单独标注为轻量扩展，不与 3B/7B 主模型等权解释。`mPLUG-Owl`、`LLaVA-OV`、`Mantis`、`Idefics2` 等旧候选不再混入本轮实验。

### 5.0 模型结构细节总表

下表的层数优先来自服务器已下载模型的 `config.json`；BLIP2 / InstructBLIP / MiniGPT-4 的视觉编码器按其 BLIP-2 系列常用 EVA/CLIP ViT-g 配置记录，正式 smoke test 时必须以实际加载对象再次确认。`视觉 token 数` 指进入文本解码器或跨模态解码路径的视觉 token 数，不是原始 ViT patch 数。

| 模型 | 实验版本/目录 | 总参数量 | LLM / text decoder | text decoder 层数 | 视觉编码器 | Vision encoder 层数 | 视觉 token 数 | 视觉到文本是否压缩 | 连接/投影方式 | 备注 |
|---|---|---:|---|---:|---|---:|---:|---|---|---|
| BLIP2-OPT-2.7B | `models/blip2-opt-2.7b` | 约 3.7B | OPT-2.7B | 32 | EVA/CLIP ViT-g 系列 | 约 39 | 32 | 是 | Q-Former 32 query token -> OPT prefix | 已有 BLIP2 梯度/排序结果；主压缩型 anchor |
| InstructBLIP-Vicuna-7B | `models/instructblip-vicuna-7b` | 约 8B | Vicuna-7B / LLaMA | 32 | EVA/CLIP ViT-g 系列 | 约 39 | 32 | 是 | instruction-aware Q-Former 32 query token -> Vicuna prefix | 指令型 Q-Former anchor |
| MiniGPT-4-Vicuna-7B ★ | 待确认/下载 | 约 7B+ | Vicuna-7B / LLaMA | 32 | EVA/CLIP ViT-g 系列 | 约 39 | 32 | 是 | BLIP-2 Q-Former -> linear projection -> Vicuna | 压缩型扩展重点；目录和具体 checkpoint 待确认 |
| LLaVA-v1.5-7B | `models/llava-v1.5-7b-hf` | 约 7.3B | Vicuna-7B / LLaMA | 32 | CLIP ViT-L/14-336 | 24 | 576 | 否 | CLIP patch features -> MLP projector -> Vicuna | `336/14=24`，默认去 CLS 后 `24*24=576` |
| Qwen2.5-VL-3B | `models/Qwen2.5-VL-3B-Instruct` | 约 3B | Qwen2.5 VL decoder | 36 | Qwen2.5-VL ViT | 32 | 动态；固定 `448x448` 时约 256 | 否；动态 token，经 merger 降采样 | ViT patch -> spatial merge -> Qwen2.5 decoder | 必须固定输入分辨率；否则 token scope 随样本变化 |
| PaliGemma-3B ★ | `models/paligemma-3b-mix-224-modelscope` | 约 3B；ModelScope 权重约 11G | Gemma decoder | 18 | SigLIP vision model | 27 | 256 | 否 | SigLIP visual tokens -> projection dim 2048 -> Gemma decoder | 来自 ModelScope `AI-ModelScope/paligemma-3b-mix-224`；config 确认 `num_image_tokens=256`、`patch_size=14`、预处理 `224x224` |
| SmolVLM-Instruct / 1.7B | `models/SmolVLM-Instruct` | 约 1.7B；本地 PyTorch 文件 4.2G | SmolLM/VLlama3-style LLaMA decoder | 24 | Idefics3 / SigLIP-style vision encoder | 27 | 81 | 是；非 Q-Former 压缩 | pixel shuffle / connector -> 81 image tokens -> text decoder | 新下载轻量扩展模型，只作 sanity check / 低成本对照 |

### 5.1 压缩型：Q-Former / 少量视觉 token

这类模型先把图像压缩成少量 query/visual prefix token，再送入 LLM。默认按 **32 tok** 记作压缩型视觉接口。

| 模型 | 实验版本 | 视觉接口 | 视觉 token 数 | 本实验角色 | 模型目录 |
|---|---|---|---:|---|---|
| BLIP2-OPT-2.7B | `blip2-opt-2.7b` | Q-Former -> OPT visual prefix | 32 | 压缩型 anchor，已有 BLIP2 结果 | `models/blip2-opt-2.7b` |
| InstructBLIP-Vicuna-7B | `instructblip-vicuna-7b` | Q-Former -> Vicuna visual prefix | 32 | 指令型 Q-Former anchor | `models/instructblip-vicuna-7b` |
| MiniGPT-4-Vicuna-7B ★ | `MiniGPT-4-Vicuna-7B` | Q-Former / projection bridge -> Vicuna | 32 | 压缩型扩展重点模型 | 待确认/下载 |

### 5.2 非压缩型：MLP / projector / 多视觉 token

这类模型保留较多视觉 token，经 MLP/projector/merger 接入 LLM。视觉 token 数随模型和分辨率而变，不统一压缩到 32。

| 模型 | 实验版本 | 视觉接口 | 视觉 token 数 | 本实验角色 | 模型目录 |
|---|---|---|---:|---|---|
| LLaVA-v1.5-7B | `llava-v1.5-7b-hf` | CLIP/SigLIP visual features -> MLP projector -> Vicuna | 576 | 非压缩型 anchor，已有 LLaVA 基础结果 | `models/llava-v1.5-7b-hf` |
| Qwen2.5-VL-3B | `Qwen2.5-VL-3B-Instruct` | ViT/merger -> Qwen2.5 LLM | 动态；实验中固定输入分辨率 | 替换原 Qwen2.5-VL-7B，降低显存和训练成本 | `models/Qwen2.5-VL-3B-Instruct` |
| PaliGemma-3B ★ | `AI-ModelScope/paligemma-3b-mix-224` | SigLIP visual tokens -> Gemma | 256 | 非压缩型扩展重点模型 | `models/paligemma-3b-mix-224-modelscope` |

### 5.3 轻量扩展：SmolVLM

SmolVLM 不纳入主 3B/7B 统计结论的等权比较，只用于检查轻量模型上视觉梯度定位曲线是否仍能形成稳定候选层。

| 模型 | 实验版本 | 视觉接口 | 视觉 token 数 | 本实验角色 | 模型目录 |
|---|---|---|---:|---|---|
| SmolVLM-Instruct / 1.7B | `HuggingFaceTB/SmolVLM-Instruct` | Idefics3/SigLIP-style vision encoder -> pixel shuffle / connector -> LLaMA-style decoder | 81 | 轻量 sanity check；2B 以下扩展对照 | `models/SmolVLM-Instruct` |

Qwen2.5-VL 额外约束：动态分辨率会导致视觉 token 数量随图片尺寸变化。做 LGA 和编辑实验时必须固定输入分辨率，例如统一 `448×448`，确保跨样本的视觉 token 数一致；否则 `visual_token_start/end` 可能随样本变化，层间指标和 adapter 训练结果会混入 token scope 差异。

PaliGemma-3B 结构记录：当前使用 ModelScope 版本 `AI-ModelScope/paligemma-3b-mix-224`，服务器目录为 `models/paligemma-3b-mix-224-modelscope`。`config.json` 显示 `model_type=paligemma`，架构为 `PaliGemmaForConditionalGeneration`；text decoder 为 `gemma`，`hidden_size=2048`，`num_hidden_layers=18`，`num_attention_heads=8`，`num_key_value_heads=1`；vision encoder 为 `siglip_vision_model`，`hidden_size=1152`，`num_hidden_layers=27`，`num_attention_heads=16`，`patch_size=14`，`projection_dim=2048`；`text_config` 和 `vision_config` 均记录 `num_image_tokens=256`。`preprocessor_config.json` 显示固定输入尺寸为 `224×224`，`image_seq_length=256`。

执行优先级：
1. 已具备模型或结果的 anchor：BLIP2-OPT-2.7B、LLaVA-v1.5-7B、InstructBLIP-Vicuna-7B、Qwen2.5-VL-3B。
2. 图中重点扩展：MiniGPT-4-Vicuna-7B ★、PaliGemma-3B ★。
3. 轻量扩展：SmolVLM-Instruct / 1.7B，优先做 smoke test 和 LGA 指标；adapter 训练视显存与 hook 适配情况决定。
4. 若某个扩展模型因显存或 hook 适配暂时不可用，先完成其余模型闭环，并在报告中单独标注阻塞原因。

---

## 6. 实验流程

### Stage 0：模型接入检查

每个模型先做最小 smoke test：
- 能否加载模型。
- 能否拿到视觉 token 表征。
- 能否在目标 hook 位置注册 forward hook / backward hook。
- `bs=2` 下能否完成一个 visual adapter train batch。
- 对 Qwen2.5-VL，必须确认图像预处理固定分辨率，例如 `448×448`，并检查所有样本的 `visual_token_start/end` 与视觉 token 数一致。
- 对 SmolVLM-Instruct / 1.7B，必须确认进入 text decoder 的 image token 数为 `image_seq_len=81`，并记录 hook 到的是 Idefics3 connector 之后的 81 个 image token，还是 vision encoder 内部 patch token。

若失败：
- 记录失败原因。
- 不进入正式训练。
- 如果只是不支持 adapter 训练，但能计算梯度，则保留定位指标计算。

### Stage 1：E-VQA-pilot500 定位指标计算

对每个模型计算三类定位方法：
- request-only visual gradient LGA。
- causal localization。
- high-contribution localization。

输出：
- `layer_scores.csv`
- `sample_layer_scores.jsonl`
- `metric_topk.csv`
- `locator_topk_summary.md`

### Stage 2：E-VQA-pilot500 候选层训练验证

构造候选层集合：

```text
- ours Top3
- causal Top3
- contribution Top3
- architecture prior layer, if available
```

对候选层逐层训练 visual adapter：
- visual adapter only。
- `batch_size=2`。
- `epochs=50`。
- 保存 checkpoint 时只保留 `best_train_loss`、`last`，避免磁盘占满。
- 每层训练结束后立即评测 pilot500 val，但评测必须按 layer 单独进程执行。

评测隔离要求：
- 每个 layer 单独启动 eval 进程。
- 每个 eval 进程重新加载 base model。
- 每个 eval 进程只加载当前 layer 的 selected checkpoint。
- 每个 eval 进程重新注册当前 layer 的 adapter hook / `get_llm_outpt` wrapper。
- 当前 layer 评测结束后释放模型、adapter、hook 和 CUDA cache。
- 禁止在同一个 Python 进程里顺序评测多个 layer，除非已经有明确的 wrapper rebind 与 hook 清理验证。

异常判定：
- 如果多个 layer 的 `Rel/T-Gen/M-Gen/T-Loc/M-Loc/Average` 完全一致，优先怀疑 stale checkpoint、stale hook 或 stale wrapper。
- 此时先检查 eval 加载路径、checkpoint key、hook layer path、wrapper owner，再考虑模型层现象解释。

如果候选集合超过 8 层：
- 优先保留各方法 Top1。
- 再加入 ours Top2/Top3。
- 最多训练 8 个候选层。

### Stage 3：full E-VQA 定位指标计算

只在 pilot500 结果稳定后启动。

计算 full E-VQA 上三类定位方法的层分数：
- 不训练 adapter。
- 输出 full data 的层排名。
- 检查 full Top3 是否与 pilot500 Top3 一致。

### Stage 4：full E-VQA 候选层训练验证

full E-VQA 不默认全层扫描，只训练候选层：
- pilot500 中表现最好的 ours 候选层。
- full E-VQA LGA Top3 中未被 pilot 覆盖的层。
- causal / contribution 各 Top1。

每个候选层：
- `bs=2`。
- `50 epochs`。
- 选择 EMA loss 最小 checkpoint 做统一评测。
- 报告 E-VQA eval 六项指标。
- 最终论文/汇总表中的 E-VQA 指标必须来自完整 test/eval 集，不能只用 pilot500 val 集。

正式评测执行规范：
- 每个候选层使用独立 eval 进程。
- 每次评测从干净 base model 开始，重新加载该层 adapter checkpoint。
- 评测日志必须记录：layer id、checkpoint path、checkpoint 内部 train module key、hook module path、wrapper owner / rebind 状态。
- 评测结束后显式释放模型与 hook，避免下一层复用 stale wrapper。
- 若发现多个层结果完全相同，先暂停汇总，按 stale eval 事故排查，不直接把它解释为真实模型性能。

---

## 7. 真实高性能层定义

在 pilot500 上：
- 若做了全层 visual sweep，则真实最佳层定义为 `Avg` 最高层。
- 同时保留单指标最佳层：`Rel`, `T-Gen`, `M-Gen`, `T-Loc`, `M-Loc`。

在 full E-VQA 上：
- 如果只训练候选层，则称为“候选集合内最佳层”，不声称全局最佳。
- 若后续资源允许全层扫描，再升级为“full E-VQA 真实最佳层”。

---

## 8. 对齐分析指标

对每个模型、每个数据集、每个定位方法计算：

| 指标 | 含义 |
|---|---|
| `Hit@1` | 预测 Top1 是否命中真实最佳层 |
| `Hit@3` | 预测 Top3 是否包含真实最佳层 |
| `RankOfBest` | 真实最佳层在该定位方法排名中的位置 |
| `Regret@1` | 真实最佳 Avg - 预测 Top1 层 Avg |
| `Regret@3` | 真实最佳 Avg - 预测 Top3 中最佳 Avg |
| `Spearman` | 定位层分数与真实逐层 Avg 的秩相关 |
| `KendallTau` | 定位层分数与真实逐层 Avg 的 Kendall 相关 |

判定标准：
- 视觉梯度定位在多数模型/数据集上 `Regret@3` 低于 causal 与 contribution。
- 视觉梯度定位 `Hit@3` 高于 causal 与 contribution。
- 若某模型上 causal 更强，需要分析是否由视觉 token 融合方式、hook 位置或 adapter 容量导致。

---

## 9. 结果表模板

### 9.1 定位候选层汇总

| Dataset | Model | Architecture | Ours Top3 | Causal Top3 | Contribution Top3 | Notes |
|---|---|---|---|---|---|---|
| E-VQA-pilot500 | BLIP2-OPT-2.7B | Q-Former |  |  |  |  |
| E-VQA-pilot500 | InstructBLIP-Vicuna-7B | Q-Former |  |  |  |  |
| E-VQA-pilot500 | MiniGPT-4-Vicuna-7B | Q-Former / bridge |  |  |  |  |
| E-VQA-pilot500 | LLaVA-v1.5-7B | MLP projector, 576 tok |  |  |  |  |
| E-VQA-pilot500 | Qwen2.5-VL-3B | MLP / Merger, dynamic tok |  |  |  |  |
| E-VQA-pilot500 | PaliGemma-3B | SigLIP projector, 256 tok |  |  |  |  |
| E-VQA-pilot500 | SmolVLM-Instruct / 1.7B | Idefics3 connector, 81 tok |  |  |  |  |
| full E-VQA | BLIP2-OPT-2.7B | Q-Former |  |  |  |  |
| full E-VQA | InstructBLIP-Vicuna-7B | Q-Former |  |  |  |  |
| full E-VQA | MiniGPT-4-Vicuna-7B | Q-Former / bridge |  |  |  |  |
| full E-VQA | LLaVA-v1.5-7B | MLP projector, 576 tok |  |  |  |  |
| full E-VQA | Qwen2.5-VL-3B | MLP / Merger, dynamic tok |  |  |  |  |
| full E-VQA | PaliGemma-3B | SigLIP projector, 256 tok |  |  |  |  |
| full E-VQA | SmolVLM-Instruct / 1.7B | Idefics3 connector, 81 tok |  |  |  |  |

### 9.2 候选层 visual adapter 评测

| Dataset | Model | Method | Layer | Epochs | BS | Checkpoint | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Avg |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| E-VQA-pilot500 |  | ours |  | 50 | 2 |  |  |  |  |  |  |  |
| E-VQA-pilot500 |  | causal |  | 50 | 2 |  |  |  |  |  |  |  |
| E-VQA-pilot500 |  | contribution |  | 50 | 2 |  |  |  |  |  |  |  |

### 9.3 方法对齐分析

| Dataset | Model | Method | Hit@1 | Hit@3 | RankOfBest | Regret@1 | Regret@3 | Spearman | KendallTau |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| E-VQA-pilot500 |  | ours |  |  |  |  |  |  |  |
| E-VQA-pilot500 |  | causal |  |  |  |  |  |  |  |
| E-VQA-pilot500 |  | contribution |  |  |  |  |  |  |  |

---

## 10. Hook 位置约束

所有定位方法的 hook 位置必须与后续 visual adapter 训练挂载位置完全一致：

```text
如果 adapter 是 before layer l，则梯度定位、因果定位、贡献定位都必须 hook before layer l。
如果 adapter 是 after layer l，则三种定位方法都必须 hook after layer l。
```

禁止出现：

```text
真实 adapter sweep 用 before layer l，
但 LGA / causal / contribution 用 after layer l。
```

每个模型接入时必须记录：
- 视觉 token 起止位置。
- 视觉 token 是否进入 LLM decoder。
- adapter 挂载模块路径。
- hook 是 before 还是 after。
- 层编号是 0-based 还是论文中的 1-based。

---

## 11. 存储与失败恢复

训练 checkpoint 策略：
- 每层最多保留 `best_train_loss` 和 `last`。
- 若保存多个 checkpoint 导致磁盘压力，自动删除非 selected checkpoint。
- 每个模型单独输出 `selected_checkpoint.tsv`。
- selected checkpoint 默认按 EMA loss 最小选择；raw loss 只作为辅助诊断字段。

运行失败记录：
- OOM：记录 batch size、峰值显存、失败阶段。
- hook failure：记录模块路径和报错。
- evaluation failure：保留 checkpoint，先跳过该层，后续补评。

输出目录建议：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cross_dataset_visual_layer_localization/
```

本地备份建议：

```text
downloads/cross_dataset_visual_layer_localization/
```

---

## 12. 第一轮执行建议

第一轮不直接跑全量全模型，先用 pilot 模型集合完成闭环：

1. `E-VQA-pilot500`
2. BLIP2-OPT-2.7B、InstructBLIP-Vicuna-7B、MiniGPT-4-Vicuna-7B、LLaVA-v1.5-7B、Qwen2.5-VL-3B、PaliGemma-3B、SmolVLM-Instruct / 1.7B
3. 三种定位方法全部计算
4. 每种方法 Top3 的候选层训练 visual adapter，`bs=2`，`50 epochs`
5. 汇总 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Avg`
6. 做 `Hit@3`、`Regret@3`、`Spearman` 对齐分析

第一轮通过后，再扩展：
- full E-VQA。
- SmolVLM-Instruct / 1.7B 若 pilot500 曲线噪声较大，只保留为轻量 sanity check，不纳入主结论统计。
- 若某个模型因下载、gated 权限、显存或 hook 适配暂时阻塞，先完成其余模型；阻塞模型只保留 smoke test 与定位脚本适配记录。

---
