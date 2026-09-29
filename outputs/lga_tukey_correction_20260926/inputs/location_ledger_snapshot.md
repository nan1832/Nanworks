# 真实扫层实验候选编辑层清单

本文档记录后续真实扫层实验要比较的候选编辑层。正式比较以 `md/Location/6edit_layer_localization_candidate_methods_revised.md` 的主候选方法为准，保留 7 种候选定位方法，外加真实扫层 `Candidate-union Oracle` / `Full-layer Oracle` 作为上界。当前已回填的 `VisEdit-Contrib-Pre-FirstToken` 候选层来自历史 first-token 实验：使用 `md/Location/Equations/VisEdit_贡献度层排序手册firsttoken_70%靠谱.md`，计算 7 个模型在 `EVQA-pilot500`、`MMKE-visual`、`MMKE-entity` 上对目标答案 tokenizer 首个 token 的贡献度，并按“插在贡献形成之前”的 VisEdit adapter 逻辑生成候选层。该结果不是 VisEdit 原文严格的 key token prediction 贡献度，尤其在 MMKE 长答案或模板化答案上可能有误差；严格 `VisEdit-Contrib-Pre-KeyToken` 主实验需后续按 `md/Location/Equations/VisEdit_贡献度层排序手册_.keytoken全流程.md` 重算后再回填。已完成真实扫层结果回填见第 4 节。

正式方法清单：

1. `Middle-Prior-Direct`
2. `VisEdit-Contrib-Pre-KeyToken`，主实验待补；当前仅保留 `VisEdit-Contrib-Pre-FirstToken` 历史结果
3. `SaLEM-Alt-Direct`
4. `LGA-Param-Direct-AltModelPred`
5. `Perturb-KL-Direct-AltSeq`
6. `Ours-Direct`
7. `CMA-ModelPred-Direct`（当前正式版）；`CMA-Direct v1.3/alt`保留为历史版本
8. `Candidate-union Oracle` / `Full-layer Oracle`，只作为真实扫层上界，不作为预测方法。

附加 / 消融方法：`Perturb-KL-Pre-AltSeq`。该方法不计入主扰动基线，后续用于检验 “Direct 高敏感层” 与 “Pre 前置层” 两种插入规则的差异。

## 0. 目录结构

- 1. 统一规则：层编号、target 字段、统一 Top-K 语义。
- 2. 候选层方法：集中登记全部候选层定位方法与当前结果。
  - 2.1 Middle-Prior-Direct
  - 2.2 VisEdit-Contrib-Pre-KeyToken，主实验待补；当前回填为历史 `FirstToken`
  - 2.3 SaLEM-Alt-Direct
  - 2.4 LGA-Param-Direct-AltModelPred
  - 2.5 Perturb-KL-Direct-AltSeq
  - 2.6 Perturb-KL-Pre-AltSeq，附加 / 消融。
  - 2.7 Ours-Direct
  - 2.8 CMA-Direct v1.3/alt（历史原结果保留）
  - 2.8.1 CMA-ModelPred-Direct（当前正式重算版）
  - 2.9 正式候选方法说明
  - 2.10 当前可立即开跑的真实扫层并集
  - 2.11 所有候选方法综合表综合全面版
  - 2.12 所有候选方法综合表正式版
  - 2.13 本章候选层汇总
- 3. 数据集分表：历史候选范围与真实扫层状态；3.4.5保留历史CMA-alt七方法并集，3.4.6给出当前CMA-ModelPred七方法Top-3/Top-5并集、完成状态和阶段指标。
- 4. 已完成真实扫层结果回填：真实训练与评测结果。
- 5. 真实扫层实验使用方式：候选层到真实扫层的使用流程。
- 6. 注意：执行和解释注意事项。

## 1. 统一规则

- 层编号：0-indexed，例如 `L0` 到 `L31`。
- target field：`alt`，即新知识 / 目标答案；序列级方法使用完整目标序列，VisEdit-style 主基线使用从 `alt` 中抽取的 key token prediction。
- 排序指标：`score_positive = max(0, attn_mean) + max(0, mlp_mean)`。
- 高贡献区识别：对 `score_positive` 做 3 层平滑，阈值为 `mean + 0.5 * std`，取最长连续高贡献区间。
- VisEdit-Contrib-Pre-KeyToken 候选规则：若严格 key token 贡献高贡献区间起始层为 `s_H`，则 `Top-K = {s_H-1, s_H-2, ..., s_H-K}`。
- 当前已登记的 VisEdit 候选层是 historical `FirstToken` 口径，不是严格 `KeyToken` 主实验结果。
- 本文档中的 Top-3 / Top-5 是编辑插入层候选，不是贡献峰值层。

## 2. 候选层方法

本章集中放置所有候选层定位方法、候选层结果、待补登记和汇总表，避免方法定义零散分布。真实编辑扫层结果仍放在第 4 节。

### 2.1 Middle-Prior-Direct

该方法不依赖数据集，因此同一模型在三个数据集上的候选层相同。按 `6edit_layer_localization_candidate_methods_revised.md` 使用严格网络中点 `rho=0.5`；候选层按与中点 `(L-1)/2` 的距离升序排列，距离相同取较浅层。

运行问题与排查记录：该方法是纯规则基线，不依赖服务器 GPU、数据样本、hook 或模型前向，因此没有 run root 和 coverage 概念。后续若结果异常，优先检查模型总层数 `L` 是否写错、层编号是否仍为 0-indexed，以及是否误用了历史 `rho=0.55`；当前表已按 `rho=0.5` 重算。

| Model | L | Top-3 | Top-5 |
|---|---:|---|---|
| BLIP2-OPT-2.7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| InstructBLIP-Vicuna-7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| MiniGPT-4-Vicuna-7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| LLaVA-v1.5-7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| Qwen2.5-VL-3B | 36 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| PaliGemma-3B | 18 | L8,L9,L7 | L8,L9,L7,L10,L6 |
| SmolVLM-Instruct-1.7B | 24 | L11,L12,L10 | L11,L12,L10,L13,L9 |

### 2.2 VisEdit-Contrib-Pre-KeyToken（EVQA 使用原 pilot500 结果；MMKE strict KeyToken 已完成）

本方法为 VisEdit-style 主候选层方法：遵循原文 key token prediction 贡献度，先从 `alt` / `target_new` 中抽取代表编辑知识的 key token，计算每层 Attention / MLP 输出对该 key token 预测的贡献，识别高贡献区间，再按 VisEdit adapter “插在贡献形成之前”的规则取前置层。

当前本节主表把两部分结果写在一起：`EVQA-pilot500` 沿用原 pilot500 贡献度结果；`MMKE-visual` 与 `MMKE-entity` 使用 2026-07-04 严格 KeyToken 全量实验结果。MMKE keytoken 结果来源：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_keytoken_mmke_7models_job3044841_20260704_192247/visedit_keytoken_candidates_summary.csv`。

与历史 FirstToken 候选层相比，MMKE 14 组中有 8 组 Top-3/Top-5 完全相同，6 组发生变化。发生变化的组合列在下方诊断表中；正式 KeyToken 方法以本节主表和 2.11 综合表中的 KeyToken 结果为准。

| Dataset | Model | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L20,L19,L18 | L20,L19,L18,L17,L16 | original pilot500 result; used in KeyToken method table |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | original pilot500 result; used in KeyToken method table |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L26,L25,L24 | L26,L25,L24,L23,L22 | original pilot500 result; used in KeyToken method table |
| EVQA-pilot500 | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | original pilot500 result; used in KeyToken method table |
| EVQA-pilot500 | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | original pilot500 result; used in KeyToken method table |
| EVQA-pilot500 | PaliGemma-3B | L12,L11,L10 | L12,L11,L10,L9,L8 | original pilot500 result; used in KeyToken method table |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L17,L16,L15 | L17,L16,L15,L14,L13 | original pilot500 result; used in KeyToken method table |
| MMKE-visual | BLIP2-OPT-2.7B | L26,L25,L24 | L26,L25,L24,L23,L22 | strict KeyToken done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L26,L25,L24 | L26,L25,L24,L23,L22 | strict KeyToken done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=214/214 |
| MMKE-visual | PaliGemma-3B | L14,L13,L12 | L14,L13,L12,L11,L10 | strict KeyToken done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L18,L17,L16 | L18,L17,L16,L15,L14 | strict KeyToken done; n=214/214 |
| MMKE-entity | BLIP2-OPT-2.7B | L22,L21,L20 | L22,L21,L20,L19,L18 | strict KeyToken done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L25,L24,L23 | L25,L24,L23,L22,L21 | strict KeyToken done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | strict KeyToken done; n=636/636 |
| MMKE-entity | PaliGemma-3B | L12,L11,L10 | L12,L11,L10,L9,L8 | strict KeyToken done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L18,L17,L16 | L18,L17,L16,L15,L14 | strict KeyToken done; n=636/636 |

#### 2.2.1 MMKE strict KeyToken 与历史 FirstToken 差异诊断

| Dataset | Model | FirstToken Top-3 | KeyToken Top-3 | FirstToken Top-5 | KeyToken Top-5 |
|---|---|---|---|---|---|
| MMKE-entity | PaliGemma-3B | L13,L12,L11 | L12,L11,L10 | L13,L12,L11,L10,L9 | L12,L11,L10,L9,L8 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L19,L18,L17 | L18,L17,L16 | L19,L18,L17,L16,L15 | L18,L17,L16,L15,L14 |
| MMKE-visual | BLIP2-OPT-2.7B | L22,L21,L20 | L26,L25,L24 | L22,L21,L20,L19,L18 | L26,L25,L24,L23,L22 |
| MMKE-visual | PaliGemma-3B | L12,L11,L10 | L14,L13,L12 | L12,L11,L10,L9,L8 | L14,L13,L12,L11,L10 |
| MMKE-visual | Qwen2.5-VL-3B | L29,L28,L27 | L28,L27,L26 | L29,L28,L27,L26,L25 | L28,L27,L26,L25,L24 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L17,L16,L15 | L18,L17,L16 | L17,L16,L15,L14,L13 | L18,L17,L16,L15,L14 |

#### 2.2.2 VisEdit-Contrib-Pre-FirstToken 历史来源表

下表中的来源文件 `config.json` / `run.log` 记录为 `key_mode=alt` 且 `token_rule=first token of target answer`，因此这里只作为历史 FirstToken 候选层来源表保留。MMKE 严格 KeyToken 全量结果已写入本节主表和 2.11 综合全面版；EVQA-pilot500 仍沿用原 pilot500 贡献度结果。

| Dataset | Model | L | Samples | 高贡献区间 | Top-3 编辑候选层 | Top-5 编辑候选层 | 贡献峰值层 | 来源 |
|---|---|---:|---:|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | 32 | 500 | L21-L29 | L20,L19,L18 | L20,L19,L18,L17,L16 | L25 (0.124816) | `downloads/evqa_module_contribution/blip2/evqa_proxy500_blip2_module_contribution_20260602_160202/contribution_layer.csv` |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | 32 | 500 | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 | L30 (0.426551) | `downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822/instructblip-vicuna-7b/contribution_layer.csv` |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | 32 | 500 | L27-L31 | L26,L25,L24 | L26,L25,L24,L23,L22 | L28 (0.197282) | `downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822/minigpt-4-vicuna-7b/contribution_layer.csv` |
| EVQA-pilot500 | LLaVA-v1.5-7B | 32 | 500 | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 | L30 (0.471731) | `downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822/llava-v1.5-7b/contribution_layer.csv` |
| EVQA-pilot500 | Qwen2.5-VL-3B | 36 | 500 | L30-L35 | L29,L28,L27 | L29,L28,L27,L26,L25 | L31 (0.131005) | `downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822/qwen2.5-vl-3b/contribution_layer.csv` |
| EVQA-pilot500 | PaliGemma-3B | 18 | 500 | L13-L16 | L12,L11,L10 | L12,L11,L10,L9,L8 | L15 (0.043138) | `downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822/paligemma-3b/contribution_layer.csv` |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | 24 | 500 | L18-L23 | L17,L16,L15 | L17,L16,L15,L14,L13 | L22 (0.2035) | `downloads/evqa_module_contribution/crossmodel_pilot500_20260606_150822/smolvlm-1.7b/contribution_layer.csv` |
| MMKE-visual | BLIP2-OPT-2.7B | 32 | 214 | L23-L29 | L22,L21,L20 | L22,L21,L20,L19,L18 | L26 (0.0863446) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/blip2-opt-2.7b/contribution_layer.csv` |
| MMKE-visual | InstructBLIP-Vicuna-7B | 32 | 214 | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 | L30 (0.538331) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/instructblip-vicuna-7b/contribution_layer.csv` |
| MMKE-visual | MiniGPT-4-Vicuna-7B | 32 | 214 | L27-L31 | L26,L25,L24 | L26,L25,L24,L23,L22 | L28 (0.092522) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/minigpt-4-vicuna-7b/contribution_layer.csv` |
| MMKE-visual | LLaVA-v1.5-7B | 32 | 214 | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 | L30 (0.532774) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/llava-v1.5-7b/contribution_layer.csv` |
| MMKE-visual | Qwen2.5-VL-3B | 36 | 214 | L30-L32 | L29,L28,L27 | L29,L28,L27,L26,L25 | L31 (0.138793) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/qwen2.5-vl-3b/contribution_layer.csv` |
| MMKE-visual | PaliGemma-3B | 18 | 214 | L13-L15 | L12,L11,L10 | L12,L11,L10,L9,L8 | L14 (0.00061483) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/paligemma-3b/contribution_layer.csv` |
| MMKE-visual | SmolVLM-Instruct-1.7B | 24 | 214 | L18-L23 | L17,L16,L15 | L17,L16,L15,L14,L13 | L20 (0.055913) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/visual/alt/smolvlm-1.7b/contribution_layer.csv` |
| MMKE-entity | BLIP2-OPT-2.7B | 32 | 636 | L23-L30 | L22,L21,L20 | L22,L21,L20,L19,L18 | L29 (0.23269) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/blip2-opt-2.7b/contribution_layer.csv` |
| MMKE-entity | InstructBLIP-Vicuna-7B | 32 | 636 | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 | L30 (0.569705) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/instructblip-vicuna-7b/contribution_layer.csv` |
| MMKE-entity | MiniGPT-4-Vicuna-7B | 32 | 636 | L26-L31 | L25,L24,L23 | L25,L24,L23,L22,L21 | L28 (0.0929583) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/minigpt-4-vicuna-7b/contribution_layer.csv` |
| MMKE-entity | LLaVA-v1.5-7B | 32 | 636 | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 | L30 (0.460773) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/llava-v1.5-7b/contribution_layer.csv` |
| MMKE-entity | Qwen2.5-VL-3B | 36 | 636 | L30-L35 | L29,L28,L27 | L29,L28,L27,L26,L25 | L34 (0.0300386) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/qwen2.5-vl-3b/contribution_layer.csv` |
| MMKE-entity | PaliGemma-3B | 18 | 636 | L14-L16 | L13,L12,L11 | L13,L12,L11,L10,L9 | L15 (0.00035419) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/paligemma-3b/contribution_layer.csv` |
| MMKE-entity | SmolVLM-Instruct-1.7B | 24 | 636 | L20-L23 | L19,L18,L17 | L19,L18,L17,L16,L15 | L23 (0.105696) | `downloads/mmke_module_contribution/mmke_module_contribution_20260607_150600/entity/alt/smolvlm-1.7b/contribution_layer.csv` |


### 2.3 SaLEM-Alt-Direct

该方法按 `md/Location/Equations/SaLEM-based_candidate_layer_formulas.md` 的参数梯度显著性公式计算，当前已完成 21/21。`Qwen2.5-VL-3B` 三个数据集已使用 `qwen25vl` 环境补跑并回填，原 `rc=1` 由旧 transformers 环境无法导入 `Qwen2_5_VLForConditionalGeneration` 引起。

运行问题与排查记录：SaLEM 的主要历史问题集中在 Qwen2.5-VL 环境，不是数据、显存、CUDA、视觉 token 或 hook 问题。旧通用 Jupyter 环境 `/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/` 中的 `transformers` 无法导入 `Qwen2_5_VLForConditionalGeneration`，导致模型未初始化即退出，表现为 Qwen 三组 `rc=1`。排查时先运行 `from transformers import Qwen2_5_VLForConditionalGeneration`；若失败，必须切到 Qwen 专用环境再补跑。当前 Qwen 三组已用 `qwen25vl` 环境修复，样本计数均为完整数据集规模。

| Dataset | Model | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L21 | done; n=500/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L20,L17 | done; n=500/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | mean_abs_param_grad_alt | L8,L9,L10 | L8,L9,L10,L5,L6 | done; n=500/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | mean_abs_param_grad_alt | L7,L6,L5 | L7,L6,L5,L8,L9 | done; n=500/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | mean_abs_param_grad_alt | L11,L14,L12 | L11,L14,L12,L13,L15 | done; n=500/500 |
| EVQA-pilot500 | PaliGemma-3B | mean_abs_param_grad_alt | L8,L7,L9 | L8,L7,L9,L10,L6 | done; n=500/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | mean_abs_param_grad_alt | L9,L8,L7 | L9,L8,L7,L6,L10 | done; n=500/500 |
| MMKE-visual | BLIP2-OPT-2.7B | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L20 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L20,L16 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | mean_abs_param_grad_alt | L31,L5,L8 | L31,L5,L8,L6,L9 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | mean_abs_param_grad_alt | L7,L8,L9 | L7,L8,L9,L6,L10 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | mean_abs_param_grad_alt | L12,L11,L14 | L12,L11,L14,L15,L13 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | mean_abs_param_grad_alt | L10,L8,L9 | L10,L8,L9,L7,L5 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | mean_abs_param_grad_alt | L9,L8,L0 | L9,L8,L0,L10,L7 | done; n=214/214 |
| MMKE-entity | BLIP2-OPT-2.7B | mean_abs_param_grad_alt | L0,L18,L30 | L0,L18,L30,L19,L17 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L16,L20 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | mean_abs_param_grad_alt | L31,L22,L24 | L31,L22,L24,L21,L23 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | mean_abs_param_grad_alt | L23,L22,L24 | L23,L22,L24,L25,L21 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | mean_abs_param_grad_alt | L15,L14,L13 | L15,L14,L13,L16,L12 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | mean_abs_param_grad_alt | L17,L16,L13 | L17,L16,L13,L0,L10 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | mean_abs_param_grad_alt | L0,L1,L6 | L0,L1,L6,L7,L5 | done; n=636/636 |

### 2.4 LGA-Param-Direct-AltModelPred

该方法使用旧知识与新知识的层参数梯度内积排序。主版本旧知识采用冻结模型确定性输出 `model_pred`，即 `AltModelPred`；`pred` 版本只能作为附加分析单独成表。服务器 run root 为 `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900`。当前 summary 已于 `2026-07-03 23:24:44 CST` 完成补跑并 collect，`21/21` 组均为 `done`；此前 `rc=137` 与 OOM/unavailable 组已通过 low-memory 版本补算完成。

LGA 表中的 `n=a/b` 表示 `a` 条样本实际进入 old/new 参数梯度内积计分，`b` 条样本被遍历；它不是训练/评测样本截断数。按 LGA 手册规则，`model_pred` 为空、`alt` 为空，或归一化后 `model_pred == alt` 的样本不进入主 LGA 分数，只进入跳过统计。例如 `EVQA-pilot500 / BLIP2-OPT-2.7B` 的 `done; n=404/500` 来自 `processed_samples=404`、`skipped_samples=96`，其中 `old_new_same_after_norm=61`、`empty_model_pred=35`；该组 32 层分数均 finite，`status=done`。

运行问题与排查记录：LGA 早期出现过 1 组 `missing`（`EVQA-pilot500 / LLaVA-v1.5-7B`，日志 `rc=137`）和 5 组 `unavailable; valid_layer_count_lt_top3`，本质是显存/内存压力和有效层数不足叠加；后 5 组使用 low-memory LGA 版本补跑后均完成。后续若再次出现 `rc=137`，优先查 OOM、Slurm step cancel、逐层 score 文件是否完整；若出现 `valid_layer_count_lt_top3`，检查每层 finite score 数、`model_pred`/`alt` 过滤统计，而不是直接把缺失层填 0。

| Dataset | Model | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L16 | done; n=404/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | raw_old_new_parameter_gradient_dot | L2,L0,L1 | L2,L0,L1,L4,L17 | done; n=345/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | raw_old_new_parameter_gradient_dot | L29,L25,L22 | L29,L25,L22,L26,L21 | done; n=499/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | raw_old_new_parameter_gradient_dot | L24,L25,L26 | L24,L25,L26,L23,L27 | done; n=374/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L3,L10 | done; n=493/500 |
| EVQA-pilot500 | PaliGemma-3B | raw_old_new_parameter_gradient_dot | L17,L7,L0 | L17,L7,L0,L8,L13 | done; n=286/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | raw_old_new_parameter_gradient_dot | L22,L21,L20 | L22,L21,L20,L19,L18 | done; n=499/500 |
| MMKE-visual | BLIP2-OPT-2.7B | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L2 | done; n=172/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | raw_old_new_parameter_gradient_dot | L2,L0,L4 | L2,L0,L4,L28,L1 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L25 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | raw_old_new_parameter_gradient_dot | L24,L22,L27 | L24,L22,L27,L25,L23 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L3,L6 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | raw_old_new_parameter_gradient_dot | L17,L0,L7 | L17,L0,L7,L8,L10 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | raw_old_new_parameter_gradient_dot | L1,L7,L6 | L1,L7,L6,L8,L5 | done; n=214/214 |
| MMKE-entity | BLIP2-OPT-2.7B | raw_old_new_parameter_gradient_dot | L16,L13,L18 | L16,L13,L18,L17,L15 | done; n=289/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | raw_old_new_parameter_gradient_dot | L2,L28,L0 | L2,L28,L0,L4,L30 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | raw_old_new_parameter_gradient_dot | L4,L3,L6 | L4,L3,L6,L0,L1 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | raw_old_new_parameter_gradient_dot | L1,L9,L7 | L1,L9,L7,L8,L6 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L6,L3 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | raw_old_new_parameter_gradient_dot | L17,L16,L7 | L17,L16,L7,L8,L13 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | raw_old_new_parameter_gradient_dot | L1,L7,L0 | L1,L7,L0,L6,L8 | done; n=636/636 |

### 2.5 Perturb-KL-Direct-AltSeq
该方法作为主扰动基线：只扰动 visual tokens，对每一层计算完整 `alt` 序列上的输出分布 KL sensitivity，并直接选择 KL 分数最高的层作为候选编辑层。该方法不做 VisEdit-Pre 的前置层平移；即 `Top-K` 直接来自扰动敏感层排序。

来源：服务器 `perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701/perturb_kl_direct_candidates_summary.csv`；本地备份见 `md/Location/PerturbKLDirect_outputs_20260622/perturb_kl_direct_candidates_summary.csv`。21 组均完成，score source 为 `visual_token_noise_altseq_kl`。

运行问题与排查记录：Perturb-KL-Direct 早期 Qwen 组合同样受旧 transformers 环境影响，通用环境无法导入 `Qwen2_5_VLForConditionalGeneration`，导致 Qwen 组没有开始层 KL 计算、没有生成有效 summary；后续应使用能通过 Qwen import 测试的专用环境补跑。表中 `valid_groups=12` 是扰动噪声组/重复组有效计数，不是数据集样本覆盖率；若未来出现 coverage 或 sample mismatch，必须保证同一组合所有层使用一致样本集合，不能对缺失层静默补 0。该方法主口径使用完整 `alt` 序列，因此与 VisEdit FirstToken/KeyToken 的 token 口径不同。

| Dataset | Model | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | visual_token_noise_altseq_kl | L3,L4,L2 | L3,L4,L2,L1,L5 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | visual_token_noise_altseq_kl | L2,L3,L4 | L2,L3,L4,L5,L6 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | LLaVA-v1.5-7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | Qwen2.5-VL-3B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | PaliGemma-3B | visual_token_noise_altseq_kl | L5,L7,L6 | L5,L7,L6,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | visual_token_noise_altseq_kl | L1,L2,L0 | L1,L2,L0,L4,L3 | done; n=500/500; valid_groups=12 |
| MMKE-visual | BLIP2-OPT-2.7B | visual_token_noise_altseq_kl | L3,L4,L2 | L3,L4,L2,L1,L5 | done; n=214/214; valid_groups=12 |
| MMKE-visual | InstructBLIP-Vicuna-7B | visual_token_noise_altseq_kl | L2,L3,L5 | L2,L3,L5,L4,L8 | done; n=214/214; valid_groups=12 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=214/214; valid_groups=12 |
| MMKE-visual | LLaVA-v1.5-7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=214/214; valid_groups=12 |
| MMKE-visual | Qwen2.5-VL-3B | visual_token_noise_altseq_kl | L0,L13,L14 | L0,L13,L14,L12,L15 | done; n=214/214; valid_groups=12 |
| MMKE-visual | PaliGemma-3B | visual_token_noise_altseq_kl | L7,L5,L6 | L7,L5,L6,L8,L9 | done; n=214/214; valid_groups=12 |
| MMKE-visual | SmolVLM-Instruct-1.7B | visual_token_noise_altseq_kl | L1,L4,L0 | L1,L4,L0,L2,L5 | done; n=214/214; valid_groups=12 |
| MMKE-entity | BLIP2-OPT-2.7B | visual_token_noise_altseq_kl | L3,L2,L4 | L3,L2,L4,L1,L0 | done; n=636/636; valid_groups=12 |
| MMKE-entity | InstructBLIP-Vicuna-7B | visual_token_noise_altseq_kl | L5,L4,L3 | L5,L4,L3,L2,L8 | done; n=636/636; valid_groups=12 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | LLaVA-v1.5-7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | Qwen2.5-VL-3B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L14 | done; n=636/636; valid_groups=12 |
| MMKE-entity | PaliGemma-3B | visual_token_noise_altseq_kl | L7,L5,L6 | L7,L5,L6,L8,L9 | done; n=636/636; valid_groups=12 |
| MMKE-entity | SmolVLM-Instruct-1.7B | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |

### 2.6 Perturb-KL-Pre-AltSeq

该方法作为附加 / 消融实验：先用层扰动 KL sensitivity 找高敏感区，再按 “插在敏感性形成之前” 的逻辑取前置层。它不作为主扰动基线；主实验优先计算 2.5 `Perturb-KL-Direct-AltSeq`。

运行问题与排查记录：该消融已于 2026-07-04 离线派生完成，复用了 2.5 Direct 的完整 `perturb_kl_layer_scores.csv`，没有重新跑模型前向或扰动 KL。结果显示 21 组均可派生，但只有 1 组 clean Top-5 满 5 层；其余 20 组按手册标记为 `insufficient_pre_layers`，其中 14 组高敏感区从 `L0` 起步，6 组高敏感区太靠前导致 Top-5 不足。不能把 Direct Top-K、Middle-Prior 或历史 FirstToken/VisEdit-Pre 层补入本方法。

| Dataset | Model scope | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | 7 models | see 2.11 per-model rows | see 2.11 per-model rows | 0/7 done; 7 insufficient_pre_layers |
| MMKE-visual | 7 models | see 2.11 per-model rows | see 2.11 per-model rows | 1/7 done; 6 insufficient_pre_layers |
| MMKE-entity | 7 models | see 2.11 per-model rows | see 2.11 per-model rows | 0/7 done; 7 insufficient_pre_layers |

### 2.7 Ours-Direct

该方法按 `md/Location/Equations/zn_visual_gradient_prediction_实验操作手册_7基础公式_4Ours指标_视觉版_补充诊断列_修复执行版.md` 的视觉梯度候选层口径执行：不训练 adapter，不执行 Pre 偏移；从 `visual gradient layer scores` 派生候选层。当前修复版不再把严格负余弦项写成唯一主公式，而是同时保留 4 个 Ours 系列指标：

- `Ours-Direct-Conflict = max(0, -S_v_cos) * S_v_new_norm * S_v_depth2`
- `Ours-AbsDirection-Direct = abs(S_v_cos) * S_v_new_norm * S_v_depth2`
- `Ours-NoDirection-Direct = S_v_new_norm * S_v_depth2`
- `Ours-1MinusCos-Direct = (1 - S_v_cos) * S_v_new_norm * S_v_depth2`

clean Top-K 已删除 `S_v_zero_grad=true`、非有限分数、带 `invalid_reason` 的层；`Ours-Direct-Conflict` 额外要求分数大于 0。已按修复版从服务器 layer score 重新派生 `7 models × 3 datasets` 的 4 个 Ours 指标；Qwen2.5-VL-3B 三组使用 chatfix 修复版覆盖旧结果，其余 6 个模型使用 20260626 21 组 run 的最终 layer score。完整表见 `md/Location/OursDirect_repair_outputs_20260701/ours_4metrics_7models_3datasets_topk_summary.csv`。

运行问题与排查记录：Ours-Direct 的历史问题不是统一脚本失败，而是严格负余弦方向门控与 Qwen `model_pred` 覆盖异常叠加。原主公式曾产生 `no_valid_ours_direct_layer`；修复版改为同时保留 4 个 Ours 指标，并在 clean Top-K 中删除 `S_v_zero_grad=true`、非有限分数和带 `invalid_reason` 的层。当前输出中 `Ours-Direct-Conflict` 仍有 11 组 `unavailable; no_valid_negative_cosine_layer` 和 2 组 `insufficient_valid_layers; clean_topk_less_than_3`，这是严格 Conflict 门控后的诊断状态，不是运行崩溃。Qwen 三组已使用 `ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304` 覆盖旧 layer score；如后续重跑，必须同时输出 `empty_model_pred_count`、coverage、样本 ID 对齐、prompt template、stop token、max_new_tokens 与 visual span 检查。

#### 2.7.0 Ours-Direct 正式主公式 `M_abscos_x_newn`（2026-08-01重算）

七方法正式比较只使用一个 Ours 主公式：`M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm`，即视觉梯度方向余弦绝对值与新知识梯度范数的乘积，不含深度加权。下面21组Top-3/Top-5直接由 `formula_topk_all_21.csv` 中 `formula=M_abscos_x_newn` 的clean结果重算；后面的4个深度加权Ours指标继续保留作消融/敏感性分析，不再合并为正式Ours候选层。

| Dataset | Model | Top-3 | Top-5 |
|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2,L3,L4 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L11 | L1,L0,L11,L9,L10 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L18,L19,L16 | L18,L19,L16,L17,L21 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L21,L19,L17 | L21,L19,L17,L20,L18 |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L3 | L5,L4,L3,L6,L7 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 |
| MMKE-visual | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2,L4,L3 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L1,L0,L3 | L1,L0,L3,L2,L4 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L9,L10,L11 | L9,L10,L11,L15,L14 |
| MMKE-visual | LLaVA-v1.5-7B | L0,L3,L1 | L0,L3,L1,L2,L5 |
| MMKE-visual | Qwen2.5-VL-3B | L0,L1,L2 | L0,L1,L2,L3,L4 |
| MMKE-visual | PaliGemma-3B | L5,L4,L3 | L5,L4,L3,L2,L1 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 |
| MMKE-entity | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2,L3,L4 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L1,L0,L3 | L1,L0,L3,L2,L4 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L27,L28,L26 | L27,L28,L26,L25,L29 |
| MMKE-entity | LLaVA-v1.5-7B | L13,L11,L12 | L13,L11,L12,L10,L9 |
| MMKE-entity | Qwen2.5-VL-3B | L0,L1,L2 | L0,L1,L2,L3,L6 |
| MMKE-entity | PaliGemma-3B | L5,L4,L3 | L5,L4,L3,L2,L6 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 |

#### 2.7.1 7 models × 3 datasets / 4 个 Ours 指标重算结果

来源：其余 6 个模型使用服务器原始 21 组 Ours-Direct layer score；Qwen2.5-VL-3B 三组使用 `ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304` 的修复版 layer score 覆盖旧结果。clean Top-K 删除 `S_v_zero_grad=true`、非有限分数、带 `invalid_reason` 的层；`Ours-Direct-Conflict` 额外要求 score > 0。

| Dataset | Model | Ours metric | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-AbsDirection-Direct | L16,L17,L15 | L16,L17,L15,L18,L14 | done |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-NoDirection-Direct | L17,L18,L16 | L17,L18,L16,L19,L15 | done |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-1MinusCos-Direct | L25,L26,L19 | L25,L26,L19,L27,L23 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-AbsDirection-Direct | L21,L22,L20 | L21,L22,L20,L19,L23 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-NoDirection-Direct | L21,L22,L20 | L21,L22,L20,L19,L23 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-1MinusCos-Direct | L22,L21,L20 | L22,L21,L20,L23,L19 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Direct-Conflict | L29,L28,L30 | L29,L28,L30,L27,L24 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-AbsDirection-Direct | L21,L18,L22 | L21,L18,L22,L19,L20 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-NoDirection-Direct | L22,L21,L20 | L22,L21,L20,L19,L23 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-1MinusCos-Direct | L22,L21,L20 | L22,L21,L20,L23,L19 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Direct-Conflict | L17,L16,L15 | L17,L16,L15,L14,L18 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-AbsDirection-Direct | L17,L16,L15 | L17,L16,L15,L14,L18 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-NoDirection-Direct | L13,L16,L15 | L13,L16,L15,L14,L12 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-1MinusCos-Direct | L13,L16,L15 | L13,L16,L15,L17,L14 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Direct-Conflict | L34 | L34 | insufficient_valid_layers; clean_topk_less_than_3 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-AbsDirection-Direct | L24,L21,L22 | L24,L21,L22,L23,L26 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-NoDirection-Direct | L20,L18,L19 | L20,L18,L19,L21,L17 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-1MinusCos-Direct | L20,L18,L19 | L20,L18,L19,L17,L21 | done |
| EVQA-pilot500 | PaliGemma-3B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| EVQA-pilot500 | PaliGemma-3B | Ours-AbsDirection-Direct | L7,L8,L6 | L7,L8,L6,L9,L5 | done |
| EVQA-pilot500 | PaliGemma-3B | Ours-NoDirection-Direct | L7,L8,L9 | L7,L8,L9,L6,L5 | done |
| EVQA-pilot500 | PaliGemma-3B | Ours-1MinusCos-Direct | L7,L9,L8 | L7,L9,L8,L6,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Direct-Conflict | L14,L13,L12 | L14,L13,L12,L11,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-AbsDirection-Direct | L14,L13,L12 | L14,L13,L12,L11,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-NoDirection-Direct | L14,L11,L13 | L14,L11,L13,L12,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-1MinusCos-Direct | L14,L11,L13 | L14,L11,L13,L12,L10 | done |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Direct-Conflict | L30 | L30 | insufficient_valid_layers; clean_topk_less_than_3 |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-AbsDirection-Direct | L15,L17,L14 | L15,L17,L14,L16,L13 | done |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-NoDirection-Direct | L19,L20,L18 | L19,L20,L18,L21,L22 | done |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-1MinusCos-Direct | L25,L21,L22 | L25,L21,L22,L20,L26 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-AbsDirection-Direct | L27,L26,L25 | L27,L26,L25,L24,L23 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-NoDirection-Direct | L27,L26,L25 | L27,L26,L25,L24,L23 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-1MinusCos-Direct | L24,L23,L25 | L24,L23,L25,L22,L27 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Direct-Conflict | L29,L28,L27 | L29,L28,L27,L26,L30 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-AbsDirection-Direct | L29,L28,L27 | L29,L28,L27,L26,L30 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-NoDirection-Direct | L27,L26,L28 | L27,L26,L28,L29,L25 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-1MinusCos-Direct | L27,L28,L29 | L27,L28,L29,L26,L25 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Direct-Conflict | L13,L14,L15 | L13,L14,L15,L16,L12 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-AbsDirection-Direct | L13,L14,L15 | L13,L14,L15,L16,L12 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-NoDirection-Direct | L13,L12,L15 | L13,L12,L15,L14,L16 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-1MinusCos-Direct | L13,L12,L15 | L13,L12,L15,L14,L16 | done |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | Qwen2.5-VL-3B | Ours-AbsDirection-Direct | L22,L17,L18 | L22,L17,L18,L20,L21 | done |
| MMKE-visual | Qwen2.5-VL-3B | Ours-NoDirection-Direct | L20,L18,L19 | L20,L18,L19,L17,L22 | done |
| MMKE-visual | Qwen2.5-VL-3B | Ours-1MinusCos-Direct | L20,L18,L19 | L20,L18,L19,L21,L17 | done |
| MMKE-visual | PaliGemma-3B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | PaliGemma-3B | Ours-AbsDirection-Direct | L5,L7,L8 | L5,L7,L8,L6,L4 | done |
| MMKE-visual | PaliGemma-3B | Ours-NoDirection-Direct | L7,L5,L8 | L7,L5,L8,L6,L9 | done |
| MMKE-visual | PaliGemma-3B | Ours-1MinusCos-Direct | L7,L8,L5 | L7,L8,L5,L6,L9 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-AbsDirection-Direct | L10,L7,L9 | L10,L7,L9,L8,L11 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-NoDirection-Direct | L11,L10,L9 | L11,L10,L9,L14,L13 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-1MinusCos-Direct | L11,L10,L14 | L11,L10,L14,L9,L13 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Direct-Conflict | L20,L19,L18 | L20,L19,L18,L17,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-AbsDirection-Direct | L20,L19,L18 | L20,L19,L18,L17,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-NoDirection-Direct | L25,L26,L24 | L25,L26,L24,L23,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-1MinusCos-Direct | L25,L24,L23 | L25,L24,L23,L26,L22 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-AbsDirection-Direct | L27,L26,L25 | L27,L26,L25,L29,L24 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-NoDirection-Direct | L27,L26,L25 | L27,L26,L25,L24,L23 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-1MinusCos-Direct | L22,L23,L24 | L22,L23,L24,L21,L20 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Direct-Conflict | L28,L29,L27 | L28,L29,L27,L26,L25 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-AbsDirection-Direct | L28,L29,L27 | L28,L29,L27,L26,L25 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-NoDirection-Direct | L27,L26,L28 | L27,L26,L28,L25,L24 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-1MinusCos-Direct | L27,L28,L26 | L27,L28,L26,L29,L25 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Direct-Conflict | L13,L30,L12 | L13,L30,L12,L14,L15 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-AbsDirection-Direct | L13,L30,L12 | L13,L30,L12,L14,L15 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-NoDirection-Direct | L18,L15,L13 | L18,L15,L13,L19,L17 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-1MinusCos-Direct | L18,L13,L15 | L18,L13,L15,L19,L17 | done |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | Qwen2.5-VL-3B | Ours-AbsDirection-Direct | L22,L21,L20 | L22,L21,L20,L17,L18 | done |
| MMKE-entity | Qwen2.5-VL-3B | Ours-NoDirection-Direct | L22,L20,L21 | L22,L20,L21,L18,L19 | done |
| MMKE-entity | Qwen2.5-VL-3B | Ours-1MinusCos-Direct | L26,L20,L25 | L26,L20,L25,L18,L21 | done |
| MMKE-entity | PaliGemma-3B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | PaliGemma-3B | Ours-AbsDirection-Direct | L7,L5,L6 | L7,L5,L6,L8,L4 | done |
| MMKE-entity | PaliGemma-3B | Ours-NoDirection-Direct | L7,L5,L8 | L7,L5,L8,L6,L9 | done |
| MMKE-entity | PaliGemma-3B | Ours-1MinusCos-Direct | L7,L8,L9 | L7,L8,L9,L6,L10 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Direct-Conflict | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-AbsDirection-Direct | L10,L11,L9 | L10,L11,L9,L8,L7 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-NoDirection-Direct | L11,L10,L9 | L11,L10,L9,L14,L13 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-1MinusCos-Direct | L14,L13,L11 | L14,L13,L11,L12,L15 | done |

#### 2.7.2 7 models × 3 datasets / Ours 系列 Top-5 候选层池

| Dataset | Model | Top-5 pool | Source |
|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L14,L15,L16,L17,L18,L19,L23,L25,L26,L27 | union of clean Top-5 from available 4 Ours metrics |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L19,L20,L21,L22,L23 | union of clean Top-5 from available 4 Ours metrics |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L18,L19,L20,L21,L22,L23,L24,L27,L28,L29,L30 | union of clean Top-5 from available 4 Ours metrics |
| EVQA-pilot500 | LLaVA-v1.5-7B | L12,L13,L14,L15,L16,L17,L18 | union of clean Top-5 from available 4 Ours metrics |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L19,L20,L21,L22,L23,L24,L26,L34 | union of clean Top-5 from available 4 Ours metrics |
| EVQA-pilot500 | PaliGemma-3B | L5,L6,L7,L8,L9,L10 | union of clean Top-5 from available 4 Ours metrics |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L10,L11,L12,L13,L14 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | BLIP2-OPT-2.7B | L13,L14,L15,L16,L17,L18,L19,L20,L21,L22,L25,L26,L30 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | InstructBLIP-Vicuna-7B | L22,L23,L24,L25,L26,L27 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L25,L26,L27,L28,L29,L30 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | LLaVA-v1.5-7B | L12,L13,L14,L15,L16 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L19,L20,L21,L22 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | PaliGemma-3B | L4,L5,L6,L7,L8,L9 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-visual | SmolVLM-Instruct-1.7B | L7,L8,L9,L10,L11,L13,L14 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | BLIP2-OPT-2.7B | L17,L18,L19,L20,L22,L23,L24,L25,L26 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | InstructBLIP-Vicuna-7B | L20,L21,L22,L23,L24,L25,L26,L27,L29 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L24,L25,L26,L27,L28,L29 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | LLaVA-v1.5-7B | L12,L13,L14,L15,L17,L18,L19,L30 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L19,L20,L21,L22,L25,L26 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | PaliGemma-3B | L4,L5,L6,L7,L8,L9,L10 | union of clean Top-5 from available 4 Ours metrics |
| MMKE-entity | SmolVLM-Instruct-1.7B | L7,L8,L9,L10,L11,L12,L13,L14,L15 | union of clean Top-5 from available 4 Ours metrics |

### 2.8 CMA-Direct（历史 v1.3，原结果保留）

该方法参考 `md/Location/Equations/CMA-Direct_v1.3.md`，使用 Visual Causal Restoration / Causal Mediation Analysis 风格的污染-恢复实验，按 `cr_seq_mean` 直接选择因果恢复分数最高的层作为候选层。该方法只污染 decoder 输入端 visual tokens，恢复 decoder block output 的 visual-token hidden states，不执行 Pre 偏移。服务器 run root 为 `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_v13_full_g09_gpu0_20260703_134818`。Smol 三组已按原 CMA 主配置覆盖重跑并重新 collect；当前为 `20/21 done`，`MMKE-entity / Qwen2.5-VL-3B` 因有效覆盖率过低标记 `low_confidence`，不再是 missing/failed。

运行问题与排查记录：CMA 早期有 Smol 三组 failed 和若干 missing，已按原 CMA 主配置覆盖重跑并重新 collect，当前没有 missing/failed。表中 `coverage=valid_samples/total_samples`，有效样本要求 clean/corrupt/restore 三步都可比较且满足污染-恢复判定；coverage 低表示候选层可计算但置信度弱。当前唯一低置信组合是 `MMKE-entity / Qwen2.5-VL-3B`，`n=9/636; coverage=0.0142`，后续论文主表需单独标注或复核，不应与高覆盖率 done 组等价解释。

| Dataset | Model | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | cr_seq_mean | L4,L2,L5 | L4,L2,L5,L3,L1 | done; n=389/500; coverage=0.7780 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | cr_seq_mean | L1,L0,L25 | L1,L0,L25,L22,L2 | done; n=421/500; coverage=0.8420 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | cr_seq_mean | L7,L1,L0 | L7,L1,L0,L2,L8 | done; n=285/500; coverage=0.5700 |
| EVQA-pilot500 | LLaVA-v1.5-7B | cr_seq_mean | L0,L1,L4 | L0,L1,L4,L6,L10 | done; n=397/500; coverage=0.7940 |
| EVQA-pilot500 | Qwen2.5-VL-3B | cr_seq_mean | L1,L0,L3 | L1,L0,L3,L6,L4 | done; n=239/500; coverage=0.4780 |
| EVQA-pilot500 | PaliGemma-3B | cr_seq_mean | L5,L4,L0 | L5,L4,L0,L3,L2 | done; n=215/500; coverage=0.4300 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | cr_seq_mean | L0,L1,L3 | L0,L1,L3,L2,L6 | done; n=293/500; coverage=0.5860 |
| MMKE-visual | BLIP2-OPT-2.7B | cr_seq_mean | L3,L0,L1 | L3,L0,L1,L2,L4 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | InstructBLIP-Vicuna-7B | cr_seq_mean | L23,L22,L24 | L23,L22,L24,L19,L17 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=50/214; coverage=0.2336 |
| MMKE-visual | LLaVA-v1.5-7B | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=207/214; coverage=0.9673 |
| MMKE-visual | Qwen2.5-VL-3B | cr_seq_mean | L1,L0,L6 | L1,L0,L6,L7,L3 | done; n=31/214; coverage=0.1449 |
| MMKE-visual | PaliGemma-3B | cr_seq_mean | L1,L2,L0 | L1,L2,L0,L3,L5 | done; n=76/214; coverage=0.3551 |
| MMKE-visual | SmolVLM-Instruct-1.7B | cr_seq_mean | L0,L1,L15 | L0,L1,L15,L2,L7 | done; n=140/214; coverage=0.6542 |
| MMKE-entity | BLIP2-OPT-2.7B | cr_seq_mean | L3,L0,L2 | L3,L0,L2,L4,L1 | done; n=634/636; coverage=0.9969 |
| MMKE-entity | InstructBLIP-Vicuna-7B | cr_seq_mean | L23,L24,L22 | L23,L24,L22,L19,L17 | done; n=630/636; coverage=0.9906 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=97/636; coverage=0.1525 |
| MMKE-entity | LLaVA-v1.5-7B | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=632/636; coverage=0.9937 |
| MMKE-entity | Qwen2.5-VL-3B | cr_seq_mean | L1,L0,L2 | L1,L0,L2,L3,L6 | low_confidence; n=9/636; coverage=0.0142 |
| MMKE-entity | PaliGemma-3B | cr_seq_mean | L0,L2,L1 | L0,L2,L1,L3,L7 | done; n=125/636; coverage=0.1965 |
| MMKE-entity | SmolVLM-Instruct-1.7B | cr_seq_mean | L15,L18,L16 | L15,L18,L16,L19,L14 | done; n=544/636; coverage=0.8553 |

#### 2.8.1 CMA-ModelPred-Direct 正式重算（2026-09-06--2026-09-12）

本小节是新增的正式 `CMA-ModelPred-Direct` 结果，**不删除、不覆盖上方历史 `CMA-Direct v1.3` 及其低覆盖率记录**。两套结果的 target 与实验协议不同，禁止跨版本取最大值、拼接样本或把新结果冒充旧结果的原地修复：

- 历史 `CMA-Direct v1.3`：保留原 `cr_seq_mean`、原目标与原单参数/旧汇总口径；其中 `MMKE-entity / Qwen2.5-VL-3B` 的 `9/636` 继续作为 `low_confidence` 历史结果登记。
- 中间诊断版：`MMKE-entity / Qwen2.5-VL-3B` 在相同反事实 `alt` 目标上扩展到 `alpha={0.5,1.0,2.0}`、`seed={0,1,2}` 后为 `43/636`，仍属 `low_valid_coverage`；该结果保留在 `md/TODO/CMA低覆盖率修正与正式重算实验手册.md`，不覆盖本节历史表。
- 本次正式重算版：target 改为冻结基础模型确定性缓存的完整 `model_pred` 答案序列，使用 `alpha={0.5,1.0,2.0}`、`seed={0,1,2}`、`delta_logprob=0.05`，共9个参数组；所有组合按 `pair_weighted_mean_CR` 聚合，tie-break 固定为 `CR_mean`、`KCR_mean`、有效参数对数、浅层优先。

服务器最终结果根目录：

- 首个正式组合 `MMKE-entity / Qwen2.5-VL-3B`：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_modelpred_direct_formal_multinoise_multiseed_v1_20260906/formal636`
- 其余20组：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_modelpred_direct_all20_multinoise_multiseed_v1_20260906`
- 完成标记：`ALL20_COMPLETE`，最终一组于 `2026-09-12 19:23:47 CST` 完成；连同首个组合为 `21/21` 全部完成。

`CMA-ModelPred` Top-3新增候选层的Adapter补评测状态（2026-09-14 02:04 CST复核）：先前缺少真实编辑结果的3层现已全部补齐，即`EVQA-pilot500 / Qwen2.5-VL-3B L15`、`EVQA-pilot500 / SmolVLM-Instruct-1.7B L5`、`MMKE-visual / SmolVLM-Instruct-1.7B L5`。三层均完成50 epoch训练后的最小EMA checkpoint选择、对应独立eval完整评测，并同时具备非空`train.done`、`selected_checkpoint.tsv`、`eval_full.done`与`results.json`；正式产物已归档至共享盘`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_modelpred_top3_missing3_adapter_backfill_20260913_job3178423`。因此，原17个完整可比组合在切换为新版`CMA-ModelPred-Direct`候选后不再因这3层缺评测而缩减；新版七方法指标仍须基于新CMA候选重新计算，不能直接沿用下文历史`CMA-Direct v1.3`的17组合数值。

覆盖率口径必须分开解释：`ModelPred可用` 是确定性、非空且prompt匹配的 `model_pred` 样本数/数据集总样本数；`CMA有效` 是至少一个参数组通过 `gap>0.05` 且所有层恢复分数完整的唯一样本数/ModelPred可用数；`总体覆盖率` 是CMA有效唯一样本数/数据集总样本数；`有效恢复参数对` 是通过gap且所有层恢复完整的 sample-alpha-seed 参数对/实际应计算参数对。表中的“稳定”直接读取最终 `candidate_ranking_stable`，不是根据Top-3外观主观判断。

| Dataset | Model | Top-3 | Top-5 | ModelPred可用 | CMA有效 | 总体覆盖率 | 有效恢复参数对 | 排名稳定性 |
|---|---|---|---|---:|---:|---:|---:|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L2,L1,L0 | L2,L1,L0,L3,L4 | 465/500 | 465/465 | 93.00% | 3461/4185（82.70%） | stable |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L2 | L1,L0,L2,L21,L22 | 500/500 | 496/500 | 99.20% | 3644/4500（80.98%） | stable |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | 499/500 | 497/499 | 99.40% | 3058/4491（68.09%） | stable |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | 500/500 | 500/500 | 100.00% | 3984/4500（88.53%） | stable |
| EVQA-pilot500 | Qwen2.5-VL-3B | L1,L0,L15 | L1,L0,L15,L8,L5 | 500/500 | 354/500 | 70.80% | 1520/4500（33.78%） | **unstable; mean Top-3 Jaccard=0.3667** |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L7 | L5,L4,L7,L0,L6 | 500/500 | 410/500 | 82.00% | 1578/4500（35.07%） | stable |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0,L1,L5 | L0,L1,L5,L4,L8 | 500/500 | 497/500 | 99.40% | 3335/4500（74.11%） | **unstable; mean Top-3 Jaccard=0.2889** |
| MMKE-visual | BLIP2-OPT-2.7B | L2,L0,L3 | L2,L0,L3,L1,L4 | 175/214 | 175/175 | 81.78% | 1317/1575（83.62%） | stable |
| MMKE-visual | InstructBLIP-Vicuna-7B | L1,L25,L22 | L1,L25,L22,L23,L21 | 214/214 | 214/214 | 100.00% | 1394/1926（72.38%） | stable |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | 214/214 | 214/214 | 100.00% | 1418/1926（73.62%） | stable |
| MMKE-visual | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | 214/214 | 214/214 | 100.00% | 1844/1926（95.74%） | stable |
| MMKE-visual | Qwen2.5-VL-3B | L1,L0,L2 | L1,L0,L2,L3,L4 | 214/214 | 154/214 | 71.96% | 583/1926（30.27%） | stable |
| MMKE-visual | PaliGemma-3B | L7,L6,L4 | L7,L6,L4,L5,L3 | 214/214 | 166/214 | 77.57% | 570/1926（29.60%） | **unstable; mean Top-3 Jaccard=0.2556** |
| MMKE-visual | SmolVLM-Instruct-1.7B | L1,L0,L5 | L1,L0,L5,L2,L6 | 214/214 | 213/214 | 99.53% | 1457/1926（75.65%） | **unstable; mean Top-3 Jaccard=0.4333** |
| MMKE-entity | BLIP2-OPT-2.7B | L2,L3,L1 | L2,L3,L1,L7,L10 | 284/636 | 284/284 | 44.65% | 2338/2556（91.47%） | stable; ModelPred可用率低 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L26,L25,L22 | L26,L25,L22,L21,L23 | 636/636 | 627/636 | 98.58% | 3628/5724（63.38%） | stable |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | 636/636 | 636/636 | 100.00% | 4159/5724（72.66%） | stable |
| MMKE-entity | LLaVA-v1.5-7B | L0,L1,L4 | L0,L1,L4,L3,L2 | 636/636 | 636/636 | 100.00% | 5283/5724（92.30%） | stable |
| MMKE-entity | Qwen2.5-VL-3B | L1,L0,L20 | L1,L0,L20,L22,L2 | 636/636 | 360/636 | 56.60% | 1161/5724（20.28%） | stable; formal |
| MMKE-entity | PaliGemma-3B | L7,L6,L5 | L7,L6,L5,L4,L2 | 636/636 | 559/636 | 87.89% | 2385/5724（41.67%） | stable |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L9,L7 | 636/636 | 631/636 | 99.21% | 3909/5724（68.29%） | stable |

##### 2.8.1.1 与历史低覆盖结果的区别

最关键的 `MMKE-entity / Qwen2.5-VL-3B` 版本链如下。三行必须同时保留，不能只保留覆盖率最高的一行：

| 版本 | 恢复目标 | 参数配置 | 有效唯一样本 | 有效恢复参数对 | low-gap | Top-3 | Top-5 | 结论 |
|---|---|---|---:|---:|---:|---|---|---|
| 历史 CMA v1.3 | 反事实 `alt` | alpha=1.0；seed/repeat=2026 | 9/636（1.42%） | 9/636（单参数组） | 627/636 | L1,L0,L2 | L1,L0,L2,L3,L6 | `low_confidence`，原结果保留 |
| 旧目标多噪声诊断 | 反事实 `alt` | alpha=0.5,1.0,2.0；seed=0,1,2 | 43/636（6.76%） | 96/5724（1.68%） | 5628/5724 | L1,L0,L2 | L1,L0,L2,L3,L4 | 仅扩大参数网格仍低覆盖，原结果保留 |
| **CMA-ModelPred正式重算** | **基础模型完整 `model_pred`** | **alpha=0.5,1.0,2.0；seed=0,1,2** | **360/636（56.60%）** | **1161/5724（20.28%）** | **4563/5724** | **L1,L0,L20** | **L1,L0,L20,L22,L2** | **formal；candidate_ranking_stable=true** |

直接差异与解释：

1. 相对最早 `9/636`，本次有效唯一样本增加351条，覆盖率由1.42%升至56.60%；相对同样9参数组的 `43/636`，增加317条，覆盖率提高49.84个百分点。
2. 相对旧目标多噪声诊断，有效恢复参数对由96条增至1161条，参数对覆盖率由1.68%升至20.28%；`low_corruption_gap`由5628条降至4563条。`delta_logprob=0.05`没有降低，提升不是事后放宽阈值造成的。
3. Top-3前两层 `L1,L0`保持一致，说明浅层信号具有一定延续性；第三层由`L2`变为`L20`。Top-5也由`L1,L0,L2,L3,L4/6`变为`L1,L0,L20,L22,L2`，说明完整基础模型旧答案序列上的因果恢复不仅增强覆盖，还改变了中深层排序。
4. 根本区别是研究问题发生了校正：旧版问“视觉污染能否降低尚未写入模型的反事实`alt`答案”，新版问“视觉污染能否破坏基础模型当前真实输出`model_pred`，并由逐层恢复找回”。因此新旧结果不能合并平均，旧低覆盖是反事实`alt`目标与基础模型知识状态不匹配的适用性证据，不是应删除的错误数据。
5. 本次21组与历史v1.3相比，仅 `MMKE-visual/MiniGPT-4`、`MMKE-visual/LLaVA`、`MMKE-entity/MiniGPT-4` 的Top-3与Top-5完全不变；其余18组至少有一个候选层或顺序变化。这是协议/target改变后的新候选结果，不应静默覆盖既有扫层队列。
6. 本次有4组虽达到formal覆盖阈值，但最终 `candidate_ranking_stable=false`：`EVQA/Qwen2.5-VL`、`EVQA/SmolVLM`、`MMKE-visual/PaliGemma`、`MMKE-visual/SmolVLM`。这些组合可以报告主聚合Top-3/Top-5，但必须附带参数组稳定性警告。
7. `MMKE-entity/BLIP2` 的总体覆盖率只有44.65%，原因是可用`model_pred`缓存仅284/636；在这284条可用样本内CMA有效率为100%。该限制属于ModelPred输入覆盖，不应误写成CMA内部gap过滤失败。

##### 2.8.1.2 两版CMA的研究意义与正式使用结论

两版CMA回答的是不同研究问题，**新版不是对历史结果的原地修补，历史版也不能因覆盖率较低而删除**：

1. 历史`CMA-Direct v1.3`恢复反事实新答案`alt`，衡量视觉污染后目标新知识能否被逐层恢复。它反映的是模型对尚未写入答案的因果响应及该协议的适用性；低覆盖本身是有意义的限制证据。尤其`MMKE-entity/Qwen2.5-VL`仅有`9/636`条有效样本，说明反事实`alt`与基础模型当前知识状态不匹配，不能把该结果解释为“Qwen只有9条非空输出”。
2. 正式`CMA-ModelPred-Direct`恢复基础模型确定性输出的完整`model_pred`序列，衡量视觉污染破坏模型现有知识后，哪些层能恢复原知识。该定义与“原知识因果恢复”的研究目标直接一致，因此作为后续七方法正式比较中的CMA主版本。
3. 协议变化确实改变了21组预测：Top-3候选集合有18/21组发生变化，仅`MMKE-visual/MiniGPT-4`、`MMKE-visual/LLaVA`、`MMKE-entity/MiniGPT-4`三组保持完全一致；Top-5候选集合有16/21组发生变化。该变化来源于恢复target和多alpha×seed聚合口径改变，不是训练结果被任意替换。
4. `MMKE-entity/Qwen2.5-VL`在新版中的CMA有效覆盖由历史`9/636（1.42%）`提高到`360/636（56.60%）`，Top-3由`L1,L0,L2`变为`L1,L0,L20`。阈值`delta_logprob=0.05`没有降低，提升来自恢复目标校正及9个参数组的正式聚合，而非事后放宽筛选标准。
5. 新版仍需保留不确定性：`EVQA/Qwen2.5-VL`、`EVQA/SmolVLM`、`MMKE-visual/PaliGemma`、`MMKE-visual/SmolVLM`的`candidate_ranking_stable=false`，可使用正式聚合Top-3/Top-5，但论文表格和结论中必须附带参数组稳定性警告。
6. 后续七方法正式比较、候选并集重算和Adapter效果分析采用`CMA-ModelPred-Direct`；历史`CMA-Direct v1.3`继续作为另一研究问题及低覆盖现象的历史/消融证据。两版必须分栏、分版本解释，禁止跨版本混合平均、取最大值或用新版静默覆盖旧版。

**使用边界：** 本小节是当前 `CMA-ModelPred-Direct` 正式候选层结果；上方2.8、2.11与2.12中的旧 `CMA-Direct` 行继续作为历史实验口径保留。除非另行冻结“用ModelPred版替换正式七方法CMA”的分析版本并重新计算七方法Top-3/Top-5并集，否则不得据此倒改已经完成的Adapter扫层记录，也不得删除旧低覆盖候选层。

### 2.9 正式候选方法说明

正式比较只保留 7 种候选定位方法。`VisEdit-Contrib` 主版本使用 `Pre-KeyToken`，即遵循 VisEdit 原文 key token prediction 贡献度，并适配 VisEdit adapter “插在贡献形成之前”的逻辑；`FirstToken` 只作为历史/诊断结果保留，`Direct-Alt` 和 `Pre-Delta` 不再作为正式方法单列。

| Method | 候选层生成方式 | 当前状态 |
|---|---|---|
| `Middle-Prior-Direct` | 按模型总层数的中层先验给出 Top-3 / Top-5 | 已登记 |
| `VisEdit-Contrib-Pre-KeyToken` | 对严格 key token prediction 的模块贡献度做高贡献区识别，取高贡献区之前的层 | 主实验待补；当前仅有 historical FirstToken 结果 |
| `SaLEM-Alt-Direct` | 用参数梯度显著性聚合到层级后排序 | 已回填 21/21；Qwen2.5-VL-3B 三个数据集已用 qwen25vl 环境修复补跑 |
| `LGA-Param-Direct-AltModelPred` | 用旧知识与新知识的层参数梯度内积排序 | 已回填 21/21；low-memory 补跑已完成 |
| `Perturb-KL-Direct-AltSeq` | 用完整 `alt` 序列上的层扰动 KL sensitivity 直接排序，取 KL 高敏感层 | 主扰动基线；21/21 已回填 |
| `Ours-Direct` | 用视觉梯度派生的 4 个 Ours 系列指标直接预测 adapter 插入层 | 21/21 已按修复版重算；Conflict 对无负余弦组合标记 unavailable/insufficient |
| `CMA-Direct` / `CMA-ModelPred-Direct` | 用视觉污染-恢复实验直接排序；历史版恢复原`alt`口径，正式重算版恢复基础模型完整`model_pred`序列 | 历史v1.3：20/21 done、1 low_confidence，原表保留；ModelPred正式重算：21/21完成，见2.8.1；4组排名稳定性不足需标注 |

附加 / 消融方法：`Perturb-KL-Pre-AltSeq` 使用同一套扰动 KL 分数，但把候选层前移；它不计入主扰动基线，后续单独报告消融结果。

说明：`2.10 当前可立即开跑的真实扫层并集` 保留为历史/当前运行记录，其中 VisEdit-Contrib 来源为 historical FirstToken，不能直接视为严格 KeyToken 主结果；后续正式论文表格按 2.1-2.5、2.7、2.8 的 7 种主方法重新汇总，2.6 作为附加 / 消融。2.11与2.12中现有CMA行仍对应2.8历史v1.3；2026-09-12完成的ModelPred正式重算结果见2.8.1，未静默覆盖历史并集。

### 2.10 当前可立即开跑的真实扫层并集__第一版含有多余层

并集顺序按历史 `VisEdit-Contrib-Pre-FirstToken`、`VisEdit-Contrib-Direct-Alt`、`Middle-Prior-Direct` 依次加入并去重。该表用于记录已经开跑/已完成的历史扫层范围；严格 `VisEdit-Contrib-Pre-KeyToken` 版本重算后需另行更新。

| Dataset | Model | Top-3 并集 | Top-5 并集 |
|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L20,L19,L18,L25,L24,L26,L17,L16 | L20,L19,L18,L17,L16,L25,L24,L26,L29,L22,L15 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L28,L27,L26,L30,L31,L17,L18,L16 | L28,L27,L26,L25,L24,L30,L31,L22,L29,L17,L18,L16,L19,L15 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L26,L25,L24,L28,L31,L30,L17,L18,L16 | L26,L25,L24,L23,L22,L28,L31,L30,L27,L17,L18,L16,L19,L15 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L28,L27,L26,L30,L31,L29,L17,L18,L16 | L28,L27,L26,L25,L24,L30,L31,L29,L17,L18,L16,L19,L15 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L29,L28,L27,L31,L35,L26,L19,L20,L18 | L29,L28,L27,L26,L25,L31,L35,L34,L33,L19,L20,L18,L21,L17 |
| EVQA-pilot500 | PaliGemma-3B | L12,L11,L10,L15,L14,L9,L8 | L12,L11,L10,L9,L8,L15,L14,L16,L17,L7 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L17,L16,L15,L22,L19,L21,L13,L12,L14 | L17,L16,L15,L14,L13,L22,L19,L21,L18,L23,L12,L11 |
| MMKE-visual | BLIP2-OPT-2.7B | L22,L21,L20,L26,L29,L24,L17,L18,L16 | L22,L21,L20,L19,L18,L26,L29,L24,L28,L27,L17,L16,L15 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L28,L27,L26,L30,L31,L22,L17,L18,L16 | L28,L27,L26,L25,L24,L30,L31,L22,L17,L18,L16,L19,L15 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L26,L25,L24,L28,L31,L27,L17,L18,L16 | L26,L25,L24,L23,L22,L28,L31,L27,L16,L30,L17,L18,L19,L15 |
| MMKE-visual | LLaVA-v1.5-7B | L28,L27,L26,L30,L31,L29,L17,L18,L16 | L28,L27,L26,L25,L24,L30,L31,L29,L17,L18,L16,L19,L15 |
| MMKE-visual | Qwen2.5-VL-3B | L29,L28,L27,L31,L30,L19,L20,L18 | L29,L28,L27,L26,L25,L31,L30,L34,L35,L19,L20,L18,L21,L17 |
| MMKE-visual | PaliGemma-3B | L12,L11,L10,L14,L17,L9,L8 | L12,L11,L10,L9,L8,L14,L17,L15,L16,L7 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L17,L16,L15,L20,L19,L21,L13,L12,L14 | L17,L16,L15,L14,L13,L20,L19,L21,L23,L18,L12,L11 |
| MMKE-entity | BLIP2-OPT-2.7B | L22,L21,L20,L29,L24,L26,L17,L18,L16 | L22,L21,L20,L19,L18,L29,L24,L26,L4,L27,L17,L16,L15 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L28,L27,L26,L30,L31,L29,L17,L18,L16 | L28,L27,L26,L25,L24,L30,L31,L29,L10,L17,L18,L16,L19,L15 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L25,L24,L23,L28,L31,L27,L17,L18,L16 | L25,L24,L23,L22,L21,L28,L31,L27,L16,L17,L18,L19,L15 |
| MMKE-entity | LLaVA-v1.5-7B | L28,L27,L26,L30,L25,L31,L17,L18,L16 | L28,L27,L26,L25,L24,L30,L31,L29,L17,L18,L16,L19,L15 |
| MMKE-entity | Qwen2.5-VL-3B | L29,L28,L27,L34,L35,L31,L19,L20,L18 | L29,L28,L27,L26,L25,L34,L35,L31,L19,L20,L18,L21,L17 |
| MMKE-entity | PaliGemma-3B | L13,L12,L11,L15,L16,L17,L9,L10,L8 | L13,L12,L11,L10,L9,L15,L16,L17,L0,L8,L7 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L19,L18,L17,L23,L21,L20,L13,L12,L14 | L19,L18,L17,L16,L15,L23,L21,L20,L13,L12,L14,L11 |

### 2.11 8种候选方法综合表综合全面版/+1消融方法

本表汇总当前登记的全部候选层定位方法：`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Perturb-KL-Pre-AltSeq`、`Ours-Direct`、`CMA-Direct`。`Perturb-KL-Pre-AltSeq` 仍是附加 / 消融，不作为主扰动基线；`Ours-Direct` 在本综合表中展开为 4 个视觉梯度指标：`Ours-Direct-Conflict`、`Ours-AbsDirection-Direct`、`Ours-NoDirection-Direct`、`Ours-1MinusCos-Direct`；`VisEdit-Contrib-Pre-KeyToken` 当前 EVQA 记录原 pilot500 结果，MMKE 记录 strict KeyToken 结果。`CMA-Direct` 已按当前 collect 结果展开到本表；其中 `low_confidence` 表示有结果但有效覆盖率过低，后续论文主表需单独标注或复核。

> **CMA版本注释（2026-09-13）：** 本表中的`CMA-Direct`行冻结为2.8的历史v1.3结果，用于追溯既有候选并集和Adapter扫层安排；它没有被2.8.1的`CMA-ModelPred-Direct`结果覆盖。需要使用ModelPred正式重算候选层、覆盖率及稳定性时，应直接引用2.8.1，不能混用两版CMA行。

| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L20,L19,L18 | L20,L19,L18,L17,L16 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | BLIP2-OPT-2.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L21 | done; n=500/500 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L16 | done; n=404/500 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L3,L4,L2 | L3,L4,L2,L1,L5 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L16,L17,L15 | L16,L17,L15,L18,L14 | done |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L17,L18,L16 | L17,L18,L16,L19,L15 | done |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L25,L26,L19 | L25,L26,L19,L27,L23 | done |
| EVQA-pilot500 | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | L4,L2,L5 | L4,L2,L5,L3,L1 | done; n=389/500; coverage=0.7780 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L28,L27,L26 | L28,L27,L26,L25,L24 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L20,L17 | done; n=500/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L0,L1 | L2,L0,L1,L4,L17 | done; n=345/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L2,L3,L4 | L2,L3,L4,L5,L6 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L1,L0 | L1,L0 | insufficient_pre_layers; high_region=L2-L15; pre_candidate_layers_out_of_range |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L21,L22,L20 | L21,L22,L20,L19,L23 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L21,L22,L20 | L21,L22,L20,L19,L23 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L22,L21,L20 | L22,L21,L20,L23,L19 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | CMA-Direct | cr_seq_mean | L1,L0,L25 | L1,L0,L25,L22,L2 | done; n=421/500; coverage=0.8420 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L26,L25,L24 | L26,L25,L24,L23,L22 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L8,L9,L10 | L8,L9,L10,L5,L6 | done; n=500/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L29,L25,L22 | L29,L25,L22,L26,L21 | done; n=499/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L9; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L29,L28,L30 | L29,L28,L30,L27,L24 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L21,L18,L22 | L21,L18,L22,L19,L20 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L22,L21,L20 | L22,L21,L20,L19,L23 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L22,L21,L20 | L22,L21,L20,L23,L19 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | CMA-Direct | cr_seq_mean | L7,L1,L0 | L7,L1,L0,L2,L8 | done; n=285/500; coverage=0.5700 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L28,L27,L26 | L28,L27,L26,L25,L24 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | LLaVA-v1.5-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L7,L6,L5 | L7,L6,L5,L8,L9 | done; n=500/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L24,L25,L26 | L24,L25,L26,L23,L27 | done; n=374/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L8; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L17,L16,L15 | L17,L16,L15,L14,L18 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L17,L16,L15 | L17,L16,L15,L14,L18 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L13,L16,L15 | L13,L16,L15,L14,L12 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L13,L16,L15 | L13,L16,L15,L17,L14 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | CMA-Direct | cr_seq_mean | L0,L1,L4 | L0,L1,L4,L6,L10 | done; n=397/500; coverage=0.7940 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L17,L18,L16 | L17,L18,L16,L19,L15 | done; dataset-independent |
| EVQA-pilot500 | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L29,L28,L27 | L29,L28,L27,L26,L25 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | Qwen2.5-VL-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L11,L14,L12 | L11,L14,L12,L13,L15 | done; n=500/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L3,L10 | done; n=493/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L34 | L34 | insufficient_valid_layers; clean_topk_less_than_3 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L24,L21,L22 | L24,L21,L22,L23,L26 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L20,L18,L19 | L20,L18,L19,L21,L17 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L20,L18,L19 | L20,L18,L19,L17,L21 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | CMA-Direct | cr_seq_mean | L1,L0,L3 | L1,L0,L3,L6,L4 | done; n=239/500; coverage=0.4780 |
| EVQA-pilot500 | PaliGemma-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L8,L9,L7 | L8,L9,L7,L10,L6 | done; dataset-independent |
| EVQA-pilot500 | PaliGemma-3B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L12,L11,L10 | L12,L11,L10,L9,L8 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | PaliGemma-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L8,L7,L9 | L8,L7,L9,L10,L6 | done; n=500/500 |
| EVQA-pilot500 | PaliGemma-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L17,L7,L0 | L17,L7,L0,L8,L13 | done; n=286/500 |
| EVQA-pilot500 | PaliGemma-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L5,L7,L6 | L5,L7,L6,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | PaliGemma-3B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L1,L0 | L1,L0 | insufficient_pre_layers; high_region=L2-L8; pre_candidate_layers_out_of_range |
| EVQA-pilot500 | PaliGemma-3B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| EVQA-pilot500 | PaliGemma-3B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L7,L8,L6 | L7,L8,L6,L9,L5 | done |
| EVQA-pilot500 | PaliGemma-3B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L7,L8,L9 | L7,L8,L9,L6,L5 | done |
| EVQA-pilot500 | PaliGemma-3B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L7,L9,L8 | L7,L9,L8,L6,L10 | done |
| EVQA-pilot500 | PaliGemma-3B | CMA-Direct | cr_seq_mean | L5,L4,L0 | L5,L4,L0,L3,L2 | done; n=215/500; coverage=0.4300 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L11,L12,L10 | L11,L12,L10,L13,L9 | done; dataset-independent |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-KeyToken | original pilot500 contribution result; short-answer keytoken proxy | L17,L16,L15 | L17,L16,L15,L14,L13 | original pilot500 result; KeyToken table row |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L9,L8,L7 | L9,L8,L7,L6,L10 | done; n=500/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L22,L21,L20 | L22,L21,L20,L19,L18 | done; n=499/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L1,L2,L0 | L1,L2,L0,L4,L3 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L14,L13,L12 | L14,L13,L12,L11,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L14,L13,L12 | L14,L13,L12,L11,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L14,L11,L13 | L14,L11,L13,L12,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L14,L11,L13 | L14,L11,L13,L12,L10 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | CMA-Direct | cr_seq_mean | L0,L1,L3 | L0,L1,L3,L2,L6 | done; n=293/500; coverage=0.5860 |
| MMKE-visual | BLIP2-OPT-2.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L26,L25,L24 | L26,L25,L24,L23,L22 | strict KeyToken done; n=214/214 |
| MMKE-visual | BLIP2-OPT-2.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L20 | done; n=214/214 |
| MMKE-visual | BLIP2-OPT-2.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L2 | done; n=172/214 |
| MMKE-visual | BLIP2-OPT-2.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L3,L4,L2 | L3,L4,L2,L1,L5 | done; n=214/214; valid_groups=12 |
| MMKE-visual | BLIP2-OPT-2.7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L6; high_sensitive_region_starts_at_L0 |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L30 | L30 | insufficient_valid_layers; clean_topk_less_than_3 |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L15,L17,L14 | L15,L17,L14,L16,L13 | done |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L19,L20,L18 | L19,L20,L18,L21,L22 | done |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L25,L21,L22 | L25,L21,L22,L20,L26 | done |
| MMKE-visual | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | L3,L0,L1 | L3,L0,L1,L2,L4 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L20,L16 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L0,L4 | L2,L0,L4,L28,L1 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L2,L3,L5 | L2,L3,L5,L4,L8 | done; n=214/214; valid_groups=12 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L2,L1,L0 | L2,L1,L0 | insufficient_pre_layers; high_region=L3-L16; pre_candidate_layers_out_of_range |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L27,L26,L25 | L27,L26,L25,L24,L23 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L27,L26,L25 | L27,L26,L25,L24,L23 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L24,L23,L25 | L24,L23,L25,L22,L27 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | CMA-Direct | cr_seq_mean | L23,L22,L24 | L23,L22,L24,L19,L17 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L26,L25,L24 | L26,L25,L24,L23,L22 | strict KeyToken done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L31,L5,L8 | L31,L5,L8,L6,L9 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L25 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=214/214; valid_groups=12 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L8; high_sensitive_region_starts_at_L0 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L29,L28,L27 | L29,L28,L27,L26,L30 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L29,L28,L27 | L29,L28,L27,L26,L30 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L27,L26,L28 | L27,L26,L28,L29,L25 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L27,L28,L29 | L27,L28,L29,L26,L25 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=50/214; coverage=0.2336 |
| MMKE-visual | LLaVA-v1.5-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L7,L8,L9 | L7,L8,L9,L6,L10 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L24,L22,L27 | L24,L22,L27,L25,L23 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=214/214; valid_groups=12 |
| MMKE-visual | LLaVA-v1.5-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L13,L14,L15 | L13,L14,L15,L16,L12 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L13,L14,L15 | L13,L14,L15,L16,L12 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L13,L12,L15 | L13,L12,L15,L14,L16 | done |
| MMKE-visual | LLaVA-v1.5-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L13,L12,L15 | L13,L12,L15,L14,L16 | done |
| MMKE-visual | LLaVA-v1.5-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=207/214; coverage=0.9673 |
| MMKE-visual | Qwen2.5-VL-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L17,L18,L16 | L17,L18,L16,L19,L15 | done; dataset-independent |
| MMKE-visual | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L12,L11,L14 | L12,L11,L14,L15,L13 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L3,L6 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L13,L14 | L0,L13,L14,L12,L15 | done; n=214/214; valid_groups=12 |
| MMKE-visual | Qwen2.5-VL-3B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L9,L8,L7 | L9,L8,L7,L6,L5 | done; high_region=L10-L17 |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | Qwen2.5-VL-3B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L22,L17,L18 | L22,L17,L18,L20,L21 | done |
| MMKE-visual | Qwen2.5-VL-3B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L20,L18,L19 | L20,L18,L19,L17,L22 | done |
| MMKE-visual | Qwen2.5-VL-3B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L20,L18,L19 | L20,L18,L19,L21,L17 | done |
| MMKE-visual | Qwen2.5-VL-3B | CMA-Direct | cr_seq_mean | L1,L0,L6 | L1,L0,L6,L7,L3 | done; n=31/214; coverage=0.1449 |
| MMKE-visual | PaliGemma-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L8,L9,L7 | L8,L9,L7,L10,L6 | done; dataset-independent |
| MMKE-visual | PaliGemma-3B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L14,L13,L12 | L14,L13,L12,L11,L10 | strict KeyToken done; n=214/214 |
| MMKE-visual | PaliGemma-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L10,L8,L9 | L10,L8,L9,L7,L5 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L17,L0,L7 | L17,L0,L7,L8,L10 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L7,L5,L6 | L7,L5,L6,L8,L9 | done; n=214/214; valid_groups=12 |
| MMKE-visual | PaliGemma-3B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L3,L2,L1 | L3,L2,L1,L0 | insufficient_pre_layers; high_region=L4-L8; pre_candidate_layers_out_of_range |
| MMKE-visual | PaliGemma-3B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | PaliGemma-3B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L5,L7,L8 | L5,L7,L8,L6,L4 | done |
| MMKE-visual | PaliGemma-3B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L7,L5,L8 | L7,L5,L8,L6,L9 | done |
| MMKE-visual | PaliGemma-3B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L7,L8,L5 | L7,L8,L5,L6,L9 | done |
| MMKE-visual | PaliGemma-3B | CMA-Direct | cr_seq_mean | L1,L2,L0 | L1,L2,L0,L3,L5 | done; n=76/214; coverage=0.3551 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L11,L12,L10 | L11,L12,L10,L13,L9 | done; dataset-independent |
| MMKE-visual | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L18,L17,L16 | L18,L17,L16,L15,L14 | strict KeyToken done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L9,L8,L0 | L9,L8,L0,L10,L7 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L1,L7,L6 | L1,L7,L6,L8,L5 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L1,L4,L0 | L1,L4,L0,L2,L5 | done; n=214/214; valid_groups=12 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L10,L7,L9 | L10,L7,L9,L8,L11 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L11,L10,L9 | L11,L10,L9,L14,L13 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L11,L10,L14 | L11,L10,L14,L9,L13 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | CMA-Direct | cr_seq_mean | L0,L1,L15 | L0,L1,L15,L2,L7 | done; n=140/214; coverage=0.6542 |
| MMKE-entity | BLIP2-OPT-2.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L22,L21,L20 | L22,L21,L20,L19,L18 | strict KeyToken done; n=636/636 |
| MMKE-entity | BLIP2-OPT-2.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L30 | L0,L18,L30,L19,L17 | done; n=636/636 |
| MMKE-entity | BLIP2-OPT-2.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L16,L13,L18 | L16,L13,L18,L17,L15 | done; n=289/636 |
| MMKE-entity | BLIP2-OPT-2.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L3,L2,L4 | L3,L2,L4,L1,L0 | done; n=636/636; valid_groups=12 |
| MMKE-entity | BLIP2-OPT-2.7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L6; high_sensitive_region_starts_at_L0 |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L20,L19,L18 | L20,L19,L18,L17,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L20,L19,L18 | L20,L19,L18,L17,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L25,L26,L24 | L25,L26,L24,L23,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L25,L24,L23 | L25,L24,L23,L26,L22 | done |
| MMKE-entity | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | L3,L0,L2 | L3,L0,L2,L4,L1 | done; n=634/636; coverage=0.9969 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L16,L20 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L28,L0 | L2,L28,L0,L4,L30 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L5,L4,L3 | L5,L4,L3,L2,L8 | done; n=636/636; valid_groups=12 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L2,L1,L0 | L2,L1,L0 | insufficient_pre_layers; high_region=L3-L15; pre_candidate_layers_out_of_range |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L27,L26,L25 | L27,L26,L25,L29,L24 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L27,L26,L25 | L27,L26,L25,L24,L23 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L22,L23,L24 | L22,L23,L24,L21,L20 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | CMA-Direct | cr_seq_mean | L23,L24,L22 | L23,L24,L22,L19,L17 | done; n=630/636; coverage=0.9906 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L25,L24,L23 | L25,L24,L23,L22,L21 | strict KeyToken done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L31,L22,L24 | L31,L22,L24,L21,L23 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L4,L3,L6 | L4,L3,L6,L0,L1 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L9; high_sensitive_region_starts_at_L0 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L28,L29,L27 | L28,L29,L27,L26,L25 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L28,L29,L27 | L28,L29,L27,L26,L25 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L27,L26,L28 | L27,L26,L28,L25,L24 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L27,L28,L26 | L27,L28,L26,L29,L25 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=97/636; coverage=0.1525 |
| MMKE-entity | LLaVA-v1.5-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L28,L27,L26 | L28,L27,L26,L25,L24 | strict KeyToken done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L23,L22,L24 | L23,L22,L24,L25,L21 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L1,L9,L7 | L1,L9,L7,L8,L6 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | LLaVA-v1.5-7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L5; high_sensitive_region_starts_at_L0 |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | L13,L30,L12 | L13,L30,L12,L14,L15 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L13,L30,L12 | L13,L30,L12,L14,L15 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L18,L15,L13 | L18,L15,L13,L19,L17 | done |
| MMKE-entity | LLaVA-v1.5-7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L18,L13,L15 | L18,L13,L15,L19,L17 | done |
| MMKE-entity | LLaVA-v1.5-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=632/636; coverage=0.9937 |
| MMKE-entity | Qwen2.5-VL-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L17,L18,L16 | L17,L18,L16,L19,L15 | done; dataset-independent |
| MMKE-entity | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L29,L28,L27 | L29,L28,L27,L26,L25 | strict KeyToken done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L15,L14,L13 | L15,L14,L13,L16,L12 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L6,L3 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L14 | done; n=636/636; valid_groups=12 |
| MMKE-entity | Qwen2.5-VL-3B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | Qwen2.5-VL-3B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L22,L21,L20 | L22,L21,L20,L17,L18 | done |
| MMKE-entity | Qwen2.5-VL-3B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L22,L20,L21 | L22,L20,L21,L18,L19 | done |
| MMKE-entity | Qwen2.5-VL-3B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L26,L20,L25 | L26,L20,L25,L18,L21 | done |
| MMKE-entity | Qwen2.5-VL-3B | CMA-Direct | cr_seq_mean | L1,L0,L2 | L1,L0,L2,L3,L6 | low_confidence; n=9/636; coverage=0.0142 |
| MMKE-entity | PaliGemma-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L8,L9,L7 | L8,L9,L7,L10,L6 | done; dataset-independent |
| MMKE-entity | PaliGemma-3B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L12,L11,L10 | L12,L11,L10,L9,L8 | strict KeyToken done; n=636/636 |
| MMKE-entity | PaliGemma-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L17,L16,L13 | L17,L16,L13,L0,L10 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L17,L16,L7 | L17,L16,L7,L8,L13 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L7,L5,L6 | L7,L5,L6,L8,L9 | done; n=636/636; valid_groups=12 |
| MMKE-entity | PaliGemma-3B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | L3,L2,L1 | L3,L2,L1,L0 | insufficient_pre_layers; high_region=L4-L9; pre_candidate_layers_out_of_range |
| MMKE-entity | PaliGemma-3B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | PaliGemma-3B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L7,L5,L6 | L7,L5,L6,L8,L4 | done |
| MMKE-entity | PaliGemma-3B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L7,L5,L8 | L7,L5,L8,L6,L9 | done |
| MMKE-entity | PaliGemma-3B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L7,L8,L9 | L7,L8,L9,L6,L10 | done |
| MMKE-entity | PaliGemma-3B | CMA-Direct | cr_seq_mean | L0,L2,L1 | L0,L2,L1,L3,L7 | done; n=125/636; coverage=0.1965 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L11,L12,L10 | L11,L12,L10,L13,L9 | done; dataset-independent |
| MMKE-entity | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-KeyToken | strict KeyToken contribution; MMKE full train split | L18,L17,L16 | L18,L17,L16,L15,L14 | strict KeyToken done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L1,L6 | L0,L1,L6,L7,L5 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L1,L7,L0 | L1,L7,L0,L6,L8 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Perturb-KL-Pre-AltSeq | derived_from_Perturb-KL-Direct-AltSeq / score_kl_robust_alt_sequence | - | - | insufficient_pre_layers; high_region=L0-L7; high_sensitive_region_starts_at_L0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Direct-Conflict | max(0,-S_v_cos) * S_v_new_norm * S_v_depth2 | - | - | unavailable; no_valid_negative_cosine_layer |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-AbsDirection-Direct | abs(S_v_cos) * S_v_new_norm * S_v_depth2 | L10,L11,L9 | L10,L11,L9,L8,L7 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-NoDirection-Direct | S_v_new_norm * S_v_depth2 | L11,L10,L9 | L11,L10,L9,L14,L13 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-1MinusCos-Direct | (1-S_v_cos) * S_v_new_norm * S_v_depth2 | L14,L13,L11 | L14,L13,L11,L12,L15 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | CMA-Direct | cr_seq_mean | L15,L18,L16 | L15,L18,L16,L19,L14 | done; n=544/636; coverage=0.8553 |

### 2.12 所有候选方法综合表正式版

> **CMA版本注释（2026-09-13）：** 本节现有`CMA-Direct`仍为历史v1.3口径。2026-09-12完成的21组`CMA-ModelPred-Direct`正式重算结果单独登记在2.8.1；在重新冻结七方法分析版本、重算候选并集与相关性指标之前，不用新表静默替换本节旧行。

本表为正式论文/主实验版本，只保留正式候选层定位方法；`Perturb-KL-Pre-AltSeq` 作为附加/消融方法保留在 2.11 综合全面版中，正式版不纳入主实验统计。

正式版包含 7 类方法：`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct`、`CMA-Direct`。

| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L20,L19,L18 | L20,L19,L18,L17,L16 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L21 | done; n=500/500 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L16 | done; n=404/500 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L3,L4,L2 | L3,L4,L2,L1,L5 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| EVQA-pilot500 | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | L4,L2,L5 | L4,L2,L5,L3,L1 | done; n=389/500; coverage=0.7780 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L28,L27,L26 | L28,L27,L26,L25,L24 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L20,L17 | done; n=500/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L0,L1 | L2,L0,L1,L4,L17 | done; n=345/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L2,L3,L4 | L2,L3,L4,L5,L6 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L1,L0,L11 | L1,L0,L11,L9,L10 | done; main formula; no depth weighting |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | CMA-Direct | cr_seq_mean | L1,L0,L25 | L1,L0,L25,L22,L2 | done; n=421/500; coverage=0.8420 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L26,L25,L24 | L26,L25,L24,L23,L22 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L8,L9,L10 | L8,L9,L10,L5,L6 | done; n=500/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L29,L25,L22 | L29,L25,L22,L26,L21 | done; n=499/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L18,L19,L16 | L18,L19,L16,L17,L21 | done; main formula; no depth weighting |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | CMA-Direct | cr_seq_mean | L7,L1,L0 | L7,L1,L0,L2,L8 | done; n=285/500; coverage=0.5700 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| EVQA-pilot500 | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L28,L27,L26 | L28,L27,L26,L25,L24 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L7,L6,L5 | L7,L6,L5,L8,L9 | done; n=500/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L24,L25,L26 | L24,L25,L26,L23,L27 | done; n=374/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| EVQA-pilot500 | LLaVA-v1.5-7B | CMA-Direct | cr_seq_mean | L0,L1,L4 | L0,L1,L4,L6,L10 | done; n=397/500; coverage=0.7940 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L17,L18,L16 | L17,L18,L16,L19,L15 | done; dataset-independent |
| EVQA-pilot500 | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L29,L28,L27 | L29,L28,L27,L26,L25 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L11,L14,L12 | L11,L14,L12,L13,L15 | done; n=500/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L3,L10 | done; n=493/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L21,L19,L17 | L21,L19,L17,L20,L18 | done; main formula; no depth weighting |
| EVQA-pilot500 | Qwen2.5-VL-3B | CMA-Direct | cr_seq_mean | L1,L0,L3 | L1,L0,L3,L6,L4 | done; n=239/500; coverage=0.4780 |
| EVQA-pilot500 | PaliGemma-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L8,L9,L7 | L8,L9,L7,L10,L6 | done; dataset-independent |
| EVQA-pilot500 | PaliGemma-3B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L12,L11,L10 | L12,L11,L10,L9,L8 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | PaliGemma-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L8,L7,L9 | L8,L7,L9,L10,L6 | done; n=500/500 |
| EVQA-pilot500 | PaliGemma-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L17,L7,L0 | L17,L7,L0,L8,L13 | done; n=286/500 |
| EVQA-pilot500 | PaliGemma-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L5,L7,L6 | L5,L7,L6,L3,L4 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | PaliGemma-3B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L5,L4,L3 | L5,L4,L3,L6,L7 | done; main formula; no depth weighting |
| EVQA-pilot500 | PaliGemma-3B | CMA-Direct | cr_seq_mean | L5,L4,L0 | L5,L4,L0,L3,L2 | done; n=215/500; coverage=0.4300 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L11,L12,L10 | L11,L12,L10,L13,L9 | done; dataset-independent |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L17,L16,L15 | L17,L16,L15,L14,L13 | historical FirstToken; strict KeyToken pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L9,L8,L7 | L9,L8,L7,L6,L10 | done; n=500/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L22,L21,L20 | L22,L21,L20,L19,L18 | done; n=499/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L1,L2,L0 | L1,L2,L0,L4,L3 | done; n=500/500; valid_groups=12 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | CMA-Direct | cr_seq_mean | L0,L1,L3 | L0,L1,L3,L2,L6 | done; n=293/500; coverage=0.5860 |
| MMKE-visual | BLIP2-OPT-2.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L22,L21,L20 | L22,L21,L20,L19,L18 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | BLIP2-OPT-2.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L20 | done; n=214/214 |
| MMKE-visual | BLIP2-OPT-2.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L2 | done; n=172/214 |
| MMKE-visual | BLIP2-OPT-2.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L3,L4,L2 | L3,L4,L2,L1,L5 | done; n=214/214; valid_groups=12 |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L4,L3 | done; main formula; no depth weighting |
| MMKE-visual | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | L3,L0,L1 | L3,L0,L1,L2,L4 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L28,L27,L26 | L28,L27,L26,L25,L24 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L20,L16 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L0,L4 | L2,L0,L4,L28,L1 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L2,L3,L5 | L2,L3,L5,L4,L8 | done; n=214/214; valid_groups=12 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L1,L0,L3 | L1,L0,L3,L2,L4 | done; main formula; no depth weighting |
| MMKE-visual | InstructBLIP-Vicuna-7B | CMA-Direct | cr_seq_mean | L23,L22,L24 | L23,L22,L24,L19,L17 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L26,L25,L24 | L26,L25,L24,L23,L22 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L31,L5,L8 | L31,L5,L8,L6,L9 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L0,L1,L3 | L0,L1,L3,L4,L25 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=214/214; valid_groups=12 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L9,L10,L11 | L9,L10,L11,L15,L14 | done; main formula; no depth weighting |
| MMKE-visual | MiniGPT-4-Vicuna-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=50/214; coverage=0.2336 |
| MMKE-visual | LLaVA-v1.5-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-visual | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L28,L27,L26 | L28,L27,L26,L25,L24 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | LLaVA-v1.5-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L7,L8,L9 | L7,L8,L9,L6,L10 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L24,L22,L27 | L24,L22,L27,L25,L23 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=214/214; valid_groups=12 |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L3,L1 | L0,L3,L1,L2,L5 | done; main formula; no depth weighting |
| MMKE-visual | LLaVA-v1.5-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=207/214; coverage=0.9673 |
| MMKE-visual | Qwen2.5-VL-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L17,L18,L16 | L17,L18,L16,L19,L15 | done; dataset-independent |
| MMKE-visual | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L29,L28,L27 | L29,L28,L27,L26,L25 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | Qwen2.5-VL-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L12,L11,L14 | L12,L11,L14,L15,L13 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L3,L6 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L13,L14 | L0,L13,L14,L12,L15 | done; n=214/214; valid_groups=12 |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| MMKE-visual | Qwen2.5-VL-3B | CMA-Direct | cr_seq_mean | L1,L0,L6 | L1,L0,L6,L7,L3 | done; n=31/214; coverage=0.1449 |
| MMKE-visual | PaliGemma-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L8,L9,L7 | L8,L9,L7,L10,L6 | done; dataset-independent |
| MMKE-visual | PaliGemma-3B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L12,L11,L10 | L12,L11,L10,L9,L8 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | PaliGemma-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L10,L8,L9 | L10,L8,L9,L7,L5 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L17,L0,L7 | L17,L0,L7,L8,L10 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L7,L5,L6 | L7,L5,L6,L8,L9 | done; n=214/214; valid_groups=12 |
| MMKE-visual | PaliGemma-3B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L5,L4,L3 | L5,L4,L3,L2,L1 | done; main formula; no depth weighting |
| MMKE-visual | PaliGemma-3B | CMA-Direct | cr_seq_mean | L1,L2,L0 | L1,L2,L0,L3,L5 | done; n=76/214; coverage=0.3551 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L11,L12,L10 | L11,L12,L10,L13,L9 | done; dataset-independent |
| MMKE-visual | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L17,L16,L15 | L17,L16,L15,L14,L13 | historical FirstToken; strict KeyToken pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L9,L8,L0 | L9,L8,L0,L10,L7 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L1,L7,L6 | L1,L7,L6,L8,L5 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L1,L4,L0 | L1,L4,L0,L2,L5 | done; n=214/214; valid_groups=12 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| MMKE-visual | SmolVLM-Instruct-1.7B | CMA-Direct | cr_seq_mean | L0,L1,L15 | L0,L1,L15,L2,L7 | done; n=140/214; coverage=0.6542 |
| MMKE-entity | BLIP2-OPT-2.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L22,L21,L20 | L22,L21,L20,L19,L18 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | BLIP2-OPT-2.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L18,L30 | L0,L18,L30,L19,L17 | done; n=636/636 |
| MMKE-entity | BLIP2-OPT-2.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L16,L13,L18 | L16,L13,L18,L17,L15 | done; n=289/636 |
| MMKE-entity | BLIP2-OPT-2.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L3,L2,L4 | L3,L2,L4,L1,L0 | done; n=636/636; valid_groups=12 |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| MMKE-entity | BLIP2-OPT-2.7B | CMA-Direct | cr_seq_mean | L3,L0,L2 | L3,L0,L2,L4,L1 | done; n=634/636; coverage=0.9969 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L28,L27,L26 | L28,L27,L26,L25,L24 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L16,L20 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L28,L0 | L2,L28,L0,L4,L30 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L5,L4,L3 | L5,L4,L3,L2,L8 | done; n=636/636; valid_groups=12 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L1,L0,L3 | L1,L0,L3,L2,L4 | done; main formula; no depth weighting |
| MMKE-entity | InstructBLIP-Vicuna-7B | CMA-Direct | cr_seq_mean | L23,L24,L22 | L23,L24,L22,L19,L17 | done; n=630/636; coverage=0.9906 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L25,L24,L23 | L25,L24,L23,L22,L21 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L31,L22,L24 | L31,L22,L24,L21,L23 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L4,L3,L6 | L4,L3,L6,L0,L1 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L27,L28,L26 | L27,L28,L26,L25,L29 | done; main formula; no depth weighting |
| MMKE-entity | MiniGPT-4-Vicuna-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=97/636; coverage=0.1525 |
| MMKE-entity | LLaVA-v1.5-7B | Middle-Prior-Direct | rho=0.5_middle_prior | L15,L16,L14 | L15,L16,L14,L17,L13 | done; dataset-independent |
| MMKE-entity | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L28,L27,L26 | L28,L27,L26,L25,L24 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | LLaVA-v1.5-7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L23,L22,L24 | L23,L22,L24,L25,L21 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L1,L9,L7 | L1,L9,L7,L8,L6 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L13,L11,L12 | L13,L11,L12,L10,L9 | done; main formula; no depth weighting |
| MMKE-entity | LLaVA-v1.5-7B | CMA-Direct | cr_seq_mean | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=632/636; coverage=0.9937 |
| MMKE-entity | Qwen2.5-VL-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L17,L18,L16 | L17,L18,L16,L19,L15 | done; dataset-independent |
| MMKE-entity | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L29,L28,L27 | L29,L28,L27,L26,L25 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | Qwen2.5-VL-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L15,L14,L13 | L15,L14,L13,L16,L12 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L2,L30,L1 | L2,L30,L1,L6,L3 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L14 | done; n=636/636; valid_groups=12 |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L6 | done; main formula; no depth weighting |
| MMKE-entity | Qwen2.5-VL-3B | CMA-Direct | cr_seq_mean | L1,L0,L2 | L1,L0,L2,L3,L6 | low_confidence; n=9/636; coverage=0.0142 |
| MMKE-entity | PaliGemma-3B | Middle-Prior-Direct | rho=0.5_middle_prior | L8,L9,L7 | L8,L9,L7,L10,L6 | done; dataset-independent |
| MMKE-entity | PaliGemma-3B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L13,L12,L11 | L13,L12,L11,L10,L9 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | PaliGemma-3B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L17,L16,L13 | L17,L16,L13,L0,L10 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L17,L16,L7 | L17,L16,L7,L8,L13 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L7,L5,L6 | L7,L5,L6,L8,L9 | done; n=636/636; valid_groups=12 |
| MMKE-entity | PaliGemma-3B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L5,L4,L3 | L5,L4,L3,L2,L6 | done; main formula; no depth weighting |
| MMKE-entity | PaliGemma-3B | CMA-Direct | cr_seq_mean | L0,L2,L1 | L0,L2,L1,L3,L7 | done; n=125/636; coverage=0.1965 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Middle-Prior-Direct | rho=0.5_middle_prior | L11,L12,L10 | L11,L12,L10,L13,L9 | done; dataset-independent |
| MMKE-entity | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-KeyToken | historical FirstToken contribution; strict KeyToken pending | L19,L18,L17 | L19,L18,L17,L16,L15 | historical FirstToken; strict KeyToken pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | SaLEM-Alt-Direct | mean_abs_param_grad_alt | L0,L1,L6 | L0,L1,L6,L7,L5 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | LGA-Param-Direct-AltModelPred | raw_old_new_parameter_gradient_dot | L1,L7,L0 | L1,L7,L0,L6,L8 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Perturb-KL-Direct-AltSeq | visual_token_noise_altseq_kl | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=636/636; valid_groups=12 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Direct | `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` | L0,L1,L2 | L0,L1,L2,L3,L4 | done; main formula; no depth weighting |
| MMKE-entity | SmolVLM-Instruct-1.7B | CMA-Direct | cr_seq_mean | L15,L18,L16 | L15,L18,L16,L19,L14 | done; n=544/636; coverage=0.8553 |

### 2.13 本章候选层汇总

本小节集中汇总候选层定位方法的计算状态；真实扫层训练/评测结果仍放在第 4 节。

| Method | 专题小节 | 覆盖范围 | 当前状态 | 后续动作 |
|---|---|---|---|---|
| Middle-Prior-Direct | 2.1 | 7 models，不区分数据集 | done | 可直接用于真实扫层比较 |
| VisEdit-Contrib-Pre-KeyToken | 2.2 | 0/21 strict KeyToken done；21/21 historical FirstToken recorded | historical FirstToken | 严格 KeyToken 待重算；当前 FirstToken 结果只作历史对照 |
| SaLEM-Alt-Direct | 2.3 | 21/21 done | done | Qwen2.5-VL-3B 三个数据集已用 qwen25vl 环境补跑并回填 |
| LGA-Param-Direct-AltModelPred | 2.4 | 21/21 done | done | low-memory 补跑已完成并回填 |
| Perturb-KL-Direct-AltSeq | 2.5 | 21/21 done | done | 主扰动基线；已回填 Top-3 / Top-5 |
| Perturb-KL-Pre-AltSeq | 2.6 | 21/21 derived；1 done；20 insufficient_pre_layers | derived ablation | 已由 Direct full layer scores 离线派生并回填 2.11；不足层按手册不补齐 |
| Ours-Direct | 2.7 | 21/21 主公式与4个深度加权消融均已重算 | done/diagnostic | 正式主公式固定为`M_abscos_x_newn`；21组Top-3/Top-5见2.7.0；原4指标只作消融，不再贡献正式七方法并集 |
| CMA-Direct / CMA-ModelPred-Direct | 2.8 / 2.8.1 | 历史v1.3：20/21 done、1 low_confidence；ModelPred正式重算：21/21完成 | historical retained / formal rerun done | 历史`9/636`和多噪声旧目标`43/636`均保留；ModelPred版Qwen/MMKE-entity为360/636、Top-3=L1,L0,L20；4组`candidate_ranking_stable=false`需警告 |
| Candidate-union Oracle / Full-layer Oracle | 第 4 节及后续真实扫层结果 | 已完成层逐步回填 | running / partial | 作为上界，不作为预测方法 |

## 3. 数据集分表

3.1--3.4.4保留2026-08-01以前的“8方法（含Perturb-KL-Pre消融）+ 4个深度加权Ours指标并集”历史冻结口径，只用于追溯既有实验为什么被安排，**不再作为当前七方法正式比较的候选并集或待补清单**。

> **版本化权威口径：** 3.4.5保留使用历史`CMA-Direct v1.3/alt`的七方法冻结并集；3.4.6是当前使用`CMA-ModelPred-Direct`的新版七方法并集与阶段指标。两版都只包含`Middle`、`VisEdit`、`SaLEM`、`LGA`、`Perturb-KL Direct`、`Ours-Direct`、`CMA`七类方法，排除Perturb-KL Pre消融，Ours只取主公式`M_abscos_x_newn = |S_v_cos| × S_v_new_norm`；禁止跨版本混合或覆盖。

### 3.1 EVQA-pilot500

| Model | 8 方法 Top-3 并集 | 层数 | 备注 |
|---|---|---:|---|
| BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5,L17,L25,L26 | 15 | Pre 不足按现有合法层/空层处理 |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L25,L21,L22,L20 | 17 | Pre 不足按现有合法层/空层处理 |
| MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L7,L28,L30,L21,L18,L20 | 20 | Pre 不足按现有合法层/空层处理 |
| LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4,L17,L13 | 17 | Pre 不足按现有合法层/空层处理 |
| Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L3,L34,L24,L21,L22,L20,L19 | 20 | Pre 不足按现有合法层/空层处理 |
| PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L1,L4 | 12 | Pre 不足按现有合法层/空层处理 |
| SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3,L14,L13 | 18 | Pre 不足按现有合法层/空层处理 |

### 3.2 MMKE-visual

| Model | 8 方法 Top-3 并集 | 层数 | 备注 |
|---|---|---:|---|
| BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2,L30,L17,L20,L21,L22 | 18 | Pre 不足按现有合法层/空层处理 |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24,L25 | 19 | Pre 不足按现有合法层/空层处理 |
| MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L29,L28,L27 | 16 | Pre 不足按现有合法层/空层处理 |
| LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L13,L12 | 16 | Pre 不足按现有合法层/空层处理 |
| Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L9,L8,L7,L6,L22,L20,L19 | 21 | 8 方法 Top-3 去重保序 |
| PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L3,L2,L1 | 14 | Pre 不足按现有合法层/空层处理 |
| SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L15,L14 | 15 | Pre 不足按现有合法层/空层处理 |

### 3.3 MMKE-entity

| Model | 8 方法 Top-3 并集 | 层数 | 备注 |
|---|---|---:|---|
| BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L19,L25,L26,L24,L23 | 18 | Pre 不足按现有合法层/空层处理 |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22,L25 | 19 | Pre 不足按现有合法层/空层处理 |
| MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L28,L29,L27,L26 | 18 | Pre 不足按现有合法层/空层处理 |
| LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L30,L12,L18 | 18 | Pre 不足按现有合法层/空层处理 |
| Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L22,L21,L20,L26,L25 | 18 | Pre 不足按现有合法层/空层处理；CMA low_confidence 仍纳入候选 |
| PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L3,L2,L1,L0 | 15 | Pre 不足按现有合法层/空层处理 |
| SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15,L9,L14,L13 | 15 | Pre 不足按现有合法层/空层处理 |

### 3.4 待补跑层分表（第 3 节减第 4 节已完成）

本节用于继续真实扫层排队：对第 3 节每个 `dataset × model` 的 `8 方法 Top-3 并集`，扣除第 4 节已经完成 `50 epoch + minimum EMA checkpoint + eval_full.done` 的层；层序保留第 3 节并集中的去重顺序。`L18-2` 复评按 `L18` 计为已完成。

#### 3.4.1 EVQA-pilot500

| Model | 待补跑层（第 3 节减第 4 节） | 待补层数 | 第 4 节已完成命中层 | 备注 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | - | 0 | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5,L17,L25,L26 | 候选并集15/15层均已完成；2026-07-28至2026-07-29在job 3044208/GPU0补齐L14,L1,L3,L4,L2，逐层均有`train.done`、非空`selected_checkpoint.tsv`、2,093条独立正式评测的`eval_full.done`和非空`results.json`，训练与评测均`rc=0` |
| InstructBLIP-Vicuna-7B | L15,L16,L14,L0,L18,L19,L2,L1,L3,L4,L25,L21,L22,L20 | 14 | L28,L27,L26 | 继续补跑这些层 |
| MiniGPT-4-Vicuna-7B | L15,L14,L8,L9,L10,L29,L22,L0,L1,L2,L7,L21,L20 | 13 | L16,L26,L25,L24,L28,L30,L18 | 继续补跑这些层 |
| LLaVA-v1.5-7B | L15,L16,L14,L7,L6,L5,L24,L25,L0,L1,L2,L4,L17,L13 | 14 | L28,L27,L26 | 继续补跑这些层 |
| Qwen2.5-VL-3B | - | 0 | L0,L1,L2,L3,L11,L12,L14,L16,L17,L18,L19,L20,L21,L22,L24,L27,L28,L29,L30,L34 | 候选并集20/20层均已完成；原有6个命中层加上2026-07-25核验的job 3044208/GPU0补跑14层，逐层均有`train.done`、非空`selected_checkpoint.tsv`和2,093条正式评测的`eval_full.done` |
| PaliGemma-3B | L0 | 1 | L8,L9,L7,L12,L11,L10,L17,L5,L6,L1,L4 | 主配置新增 L1,L4,L5,L6,L7,L8,L17 共7层并完成2,093条完整评测；stable L6（buffer=1）与L4（optimizer-step finite保护）已于2026-07-19补跑成功并完整评测，旧失败现场仅作历史记录。候选并集仅L0未完成；L0在stable和主配置下均数值不收敛且无selected/eval |
| SmolVLM-Instruct-1.7B | - | 0 | L0,L1,L2,L3,L7,L8,L9,L10,L11,L12,L13,L14,L15,L16,L17,L20,L21,L22 | 候选并集18/18层均已完成；原有8个命中层加上2026-07-25核验的job 3044208/GPU0补跑10层，逐层均有`train.done`、非空`selected_checkpoint.tsv`和2,093条正式评测的`eval_full.done` |

##### PaliGemma stable 异常与重跑登记（更新至2026-07-19）

后续从本表筛选重跑任务时，搜索精确标记 `RETRY_REQUIRED`。该标记只表示需要重新训练并评测，不能计入已完成层。

| Dataset | Model | Config | Layer | 重跑标记 | 最后有效进度 | 异常原因与核验 | 已有文件 | 重跑提示 | 完成验收 |
|---|---|---|---:|---|---|---|---|---|---|
| EVQA-pilot500 | PaliGemma-3B | stable | L6 | `EVAL_DONE_RETRY_BUFFER1` | 旧run在Epoch 12、214/500后停滞并由watchdog终止；2026-07-18按原配置仅将`data_buffer_size=1`从头补跑，完成50 epoch | 旧异常不是OOM，最可能是`data_buffer_size=4`下后台GPU预取/数据准备卡住；串行buffer修复后日志和step持续推进，未再卡住 | 新selected为Epoch 50，raw/EMA loss `0.423632/0.468850`；非空`selected_checkpoint.tsv`与`eval_full.done`均存在 | 已使用`vqa_eval.json`完整评测2,093条，Average `79.564`；从`RETRY_REQUIRED`移出。旧rc=143和原始checkpoint保留作历史异常记录 | 验收通过：Rel 69.94、T-Gen 69.13、M-Gen 89.83、T-Loc 100.00、M-Loc 68.92 |

说明：`rc=143` 是旧run被watchdog终止后的进程退出码，不是失败143次；旧run的原始checkpoint不能替代selected checkpoint。L6现已使用buffer=1从Epoch1重训50轮并完成正式评测，计入完成的是新run及其双完成标记，不是旧checkpoint。

#### 3.4.2 MMKE-visual

| Model | 待补跑层（第 3 节减第 4 节） | 待补层数 | 第 4 节已完成命中层 | 备注 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | - | 0 | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2,L30,L17,L20,L21,L22 | 候选并集18层均已训练并完成full eval |
| InstructBLIP-Vicuna-7B | - | 0 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24,L25 | 候选并集19层均已训练并完成full eval |
| MiniGPT-4-Vicuna-7B | - | 0 | L0,L1,L2,L3,L5,L8,L14,L15,L16,L24,L25,L26,L27,L28,L29,L31 | 候选并集16/16层均已完成。原有11层之外，job 3044841/GPU1补跑L0,L1,L2,L3,L29；5层训练均完成50 epoch流程，2026-07-30修复原选点记录缺陷后按minimum EMA loss生成非空`selected_checkpoint.tsv`，并使用独立MMKE-visual eval数据完成293条正式评测，`train.done`、`eval_full.done`和非空`results.json`齐全 |
| LLaVA-v1.5-7B | L13,L14,L16,L22,L24,L26,L27 | 7 | L0,L1,L2,L7,L8,L9,L12,L15,L28 | 2026-08-11新增L15：Epoch40/EMA 0.231111，293条独立评测Average 75.752，四项完成产物齐全并已同步本地。连同既有L0、L1、L2、L7、L8、L9、L12、L28，表内已有9层完整结果，剩余7层列于左侧 |
| Qwen2.5-VL-3B | - | 0 | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L9,L8,L7,L6,L22,L20,L19 | 候选并集21层已于2026-07-20在job 3044208/GPU0全部完成；L17复用既有selected后重新完成293条独立test/eval，其余20层从头训练并评测，结果暂存g09本地`/tmp` |
| PaliGemma-3B | L0 | 1 | L1,L2,L3,L4,L5,L6,L7,L8,L9,L10,L12,L13,L14,L17 | 2026-08-11新增正式7方法Top-3主配置L4：Epoch39/EMA 0.330234，293条独立评测Average 99.026，四项完成产物齐全并已同步本地；当前共有14个相关层完整评测。L0 stable不收敛且无selected/eval，继续标记`FAILED_NONCONVERGENT` |
| SmolVLM-Instruct-1.7B | - | 0 | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L15,L14 | 候选并集15层均已训练并完成full eval；本轮10个待补层于2026-07-19在job 3044208/GPU0完成，结果暂存g09本地`/tmp` |

#### 3.4.3 MMKE-entity

| Model | 待补跑层（第 3 节减第 4 节） | 待补层数 | 第 4 节已完成命中层 | 备注 |
|---|---|---:|---|---|
| BLIP2-OPT-2.7B | - | 0 | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L19,L25,L26,L24,L23 | 候选并集18层均已训练并完成full eval |
| InstructBLIP-Vicuna-7B | - | 0 | L0,L1,L2,L3,L4,L5,L14,L15,L16,L17,L18,L19,L22,L23,L24,L25,L26,L27,L28 | 候选并集19/19层均已完成；2026-07-16补核验L2,L14,L15,L19，job 3044841/GPU1新增完成L0,L1,L3,L4,L5,L22,L23,L24,L25，逐层均有selected、954条独立eval、`eval_full.done`和嵌套完整`results.json`。L1从Epoch45 checkpoint恢复训练后完成；L25于2026-07-25 21:29完成50 epoch及正式评测，Average 47.578 |
| MiniGPT-4-Vicuna-7B | L0,L1,L3,L4,L6,L14,L16,L22,L26,L27,L29 | 11 | L2,L15,L23,L24,L25,L28,L31 | 2026-07-28服务器与备份交叉核验：L2已完成50 epoch训练流程，selected为Epoch48/step15264/EMA loss 0.280683，并使用独立MMKE-entity eval数据完整评测954条，`train.done`、非空`selected_checkpoint.tsv`、实体checkpoint、`eval_full.done`和非空`results.json`齐全，Average 75.55；原始产物已备份到login01并生成本机校验一致归档。左列11层仍待补；L16目录无完整完成标记，L27仅训练到Epoch7后暂停，均不计完成 |
| LLaVA-v1.5-7B | L0,L1,L2,L7,L9,L12,L13,L14,L15,L16,L18,L22,L23,L24,L26,L27,L28,L30 | 18 | - | 2026-07-25服务器复核：18个候选层均无完整评测；L15虽有目录但无`train.done/selected/eval_full.done/results.json`，不能计完成 |
| Qwen2.5-VL-3B | - | 0 | L0,L1,L2,L13,L14,L15,L16,L17,L18,L20,L21,L22,L25,L26,L27,L28,L29,L30 | 候选并集18层已于2026-07-23在job 3044208/GPU0全部完成；逐层均完成50 epoch训练流程并使用独立MMKE-entity eval数据完整评测954条，`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，结果暂存g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/qwen2.5-vl-3b` |
| PaliGemma-3B | - | 0 | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L3,L2,L1,L0 | stable完成14/15，主配置完成15/15；stable L12与主配置L16已于2026-07-19按稳定化方案补跑并完成954条评测。配置内仅stable L0仍不收敛；主配置L0虽完成评测但退化为Average 20.00。L16补跑训练中触发34次nonfinite梯度安全跳步，最终selected/eval完整，Average 47.044，需保留数值异常注释 |
| SmolVLM-Instruct-1.7B | - | 0 | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15,L9,L14,L13 | 候选并集15层已于2026-07-22在job 3044208/GPU0全部完成；逐层均从头训练并使用独立MMKE-entity eval数据完整评测954条，`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，结果暂存g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/smolvlm-1.7b` |

#### 3.4.4 Ours-Direct 主公式 `M_abscos_x_newn` 增量候选层

本节只登记新主公式Top-3相对第3节冻结并集新增的优先补跑层，不把这些层误记成原8方法冻结并集的历史缺层。完成验收仍要求50 epoch、minimum finite EMA selected checkpoint、对应数据集独立test/eval完整结果和`eval_full.done`；缺失结果不能按0分。

| 数据集 | 模型 | `M_abscos_x_newn` Top-3 | 原冻结并集已有完整结果 | 主公式新增待补层 | Job 3126082状态（2026-08-01） |
|---|---|---|---|---|---|
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1 | L2 | L2已于17:03完成50 epoch并使用独立293条eval完整评测；selected/eval双标记齐全 |
| MMKE-entity | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2 | - | L1已于2026-08-02 04:30完成954条独立eval，selected/eval双标记齐全，Average 72.504 |
| MMKE-entity | PaliGemma-3B | L5,L4,L3 | L5,L4,L3 | - | 主配置L4已于2026-08-02 07:40完成954条独立eval，selected/eval双标记齐全，Average 96.136；不与stable取最大值 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L9,L10,L11 | - | L9,L10,L11 | 已排在PaliGemma L4之后串行训练和独立293条eval |

说明：以上6层是为了形成新Ours主公式的真实Top-3编辑效果，不是无意义重复实验。Job 3126082上的顺序为SmolVLM L2 → BLIP2 L1 → PaliGemma L4 → MiniGPT-4 L9,L10,L11；每层完整评测后仅保留selected checkpoint并清理其他checkpoint。

### 3.4.5 正式7方法 + Ours主公式重算并集与完成状态（历史CMA-alt冻结版，原记录保留）

重算时间：2026-08-01 19:54 CST；服务器增量标记复核至2026-09-14 08:07 CST。正式方法为 `Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct(M_abscos_x_newn)`、`CMA-Direct`；不含Perturb-KL Pre消融，也不再把4个深度加权Ours指标取并集。候选层按上述方法顺序去重保序。

完成验收要求同层同时具有有效selected checkpoint、对应数据集独立test/eval完整结果和`eval_full.done`。`主:`与`stable-only:`分开登记；stable-only表示实验已经做完、无需误列为缺失，但其分数不能与主配置直接混合或取最大值。已知不收敛且无完整评测的层列入“失败”，不伪装成0分，也不自动列入原配置待补。

候选可靠性边界保持不变：EVQA的7个VisEdit组合目前仍是历史FirstToken结果而非严格KeyToken；本节正式并集冻结时使用的历史LGA有4组、历史CMA v1.3有13组为低coverage候选。它们按既有候选进入本节冻结并集，正式结论必须保留对应的`historical_firsttoken_not_strict_keytoken`或`low_candidate_coverage`标记。2026-09-12完成的21组CMA-ModelPred结果见2.8.1；在另行重算并冻结新版七方法并集前，不倒改本节已运行记录。

服务器增量已并入（更新至2026-09-13 18:02 CST）：MMKE-visual / LLaVA正式Top-3并集15层和MMKE-entity / MiniGPT-4正式Top-3并集17层均已齐全；EVQA-pilot500 / InstructBLIP正式Top-3并集15层、MiniGPT-4正式Top-3并集17层均已齐全。EVQA-pilot500 / LLaVA新增完成L5,L24,L25，现已完成L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25，共11/15层；Job 3178538当前训练L0，尚未计入完成。MMKE-entity / LLaVA新增完成L28,L27,L26,L23，现已完成L15,L16,L14,L28,L27,L26,L23，共7/17层；Job 3178423的L22已完成50 epoch并选中Epoch45 checkpoint，但尚无`eval_full.done`，因此仍列待补。以下“待补”是当前仍无完整评测且不属于已知终止失败的层。

新版CMA增量说明（2026-09-14）：Job `3178423`已补齐`EVQA/Qwen L15`、`EVQA/SmolVLM L5`、`MMKE-visual/SmolVLM L5`并完成独立eval及共享盘归档。这里的Top-3表仍冻结为历史`CMA-Direct v1.3`并集，因此不把新增CMA层倒插入下表；但三层真实结果已写入第4节，可供新版`CMA-ModelPred-Direct`七方法重算使用。其中Qwen L15和MMKE-visual SmolVLM L5同时属于下方历史Top-5并集，故Top-5完成数已据实更新。

**逐层增量回填规则：** 从本节起，不再等待整条队列结束。任一层只有在服务器同时出现非空`selected_checkpoint.tsv`、`eval_full.done`和完整独立test/eval结果后，才立即回填第4节对应模型结果行，并同步更新本节Top-3/Top-5的“已完成/待补/计数”及`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`；仅有`train.done`或仅完成训练的层不提前计为完成。异常层同步写入3.5或对应模型备注，不以0分代替缺失结果。

#### 3.4.5.1 Top-3并集：已完成、失败与待补

汇总：21组Top-3并集共317个“数据集×模型×层”实验项；已完整评测301项，已知不收敛失败2项，待补14项。该汇总按下方21行逐行求和，满足`301+2+14=317`；正式评测完成率为94.95%，计入已知终止失败后的状态覆盖率为95.58%。

| Dataset | Model | 正式7方法Top-3并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | 主:L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | - | - | 0 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | 主:L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | - | - | 0 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | 主:L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | - | - | 0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25 | 11 | - | L0,L1,L2,L4 | 4 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | 主:L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | - | - | 0 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | 主:L8,L9,L7,L12,L11,L10,L17,L5,L6,L4,L3 | 11 | L0 | - | 0 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | 主:L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | - | - | 0 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | 主:L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | - | - | 0 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | - | - | 0 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | 主:L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | - | - | 0 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | - | - | 0 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | 主:L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | - | - | 0 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3,L1,L2 | 15 | 主:L8,L9,L14,L12,L10,L17,L4；stable-only:L7,L13,L5,L6,L3,L1,L2 | 14 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | 主:L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | - | - | 0 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | 主:L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | - | - | 0 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | 主:L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | - | 0 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 17 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 10 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | 主:L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | - | - | 0 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | 主:L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | 主:L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | - | - | 0 |

##### 3.4.5.1.1 Top-3完成度汇总（2026-09-13实时核验）

| Dataset | Top-3总项 | 已完整评测 | 已知失败 | 待补 | 正式评测完成率 |
|---|---:|---:|---:|---:|---:|
| EVQA-pilot500 | 103 | 98 | 1 | 4 | 95.15% |
| MMKE-visual | 107 | 106 | 1 | 0 | 99.07% |
| MMKE-entity | 107 | 97 | 0 | 10 | 90.65% |
| **合计** | **317** | **301** | **2** | **14** | **94.95%** |

- 21个数据集×模型组合中，17组已做到正式Top-3并集每层都有完整独立评测。
- EVQA / PaliGemma与MMKE-visual / PaliGemma各有L0已知不收敛失败；它们属于终止失败，不计完整评测，也不以0分补齐。因此若按“所有候选均已有终态”统计，覆盖19/21组；若按“所有候选均有正式评测、可以做完整公平比较”统计，则为17/21组。
- 当前真正仍待完成独立评测的14项只来自两组：EVQA / LLaVA 4层（L0,L1,L2,L4）和MMKE-entity / LLaVA 10层（L22,L24,L1,L9,L7,L0,L2,L13,L11,L12）。其中EVQA / LLaVA L0正在训练；MMKE-entity / LLaVA L22已完成训练并选中checkpoint，但仍在等待显存启动正式评测，二者均未提前计为完成。

##### 3.4.5.1.2 17个完整可比组合的阶段性方法结果（2026-08-24）

计算口径：仅纳入当前17个“数据集×模型”完整可比组合；每种方法的Top-3候选层均须具有主配置的完整独立评测结果。缺失组合、stable-only结果、PaliGemma L0不收敛失败层及数值异常配置均不混入计算。四项指标定义与此前12组合版本保持一致。

| 方法 | Mean Best@3 ↑ | Mean Mean@3 ↑ | Mean Regret@3 ↓ | Hit@3 ↑ |
|---|---:|---:|---:|---:|
| **Ours-Direct** | **70.873（1）** | **68.541（1）** | **1.984（1）** | **41.2%（1）** |
| LGA-Param-Direct-AltModelPred | 69.177（2） | 65.001（6） | 3.680（2） | 11.8%（6） |
| Middle-Prior-Direct | 68.962（3） | 68.018（2） | 3.895（3） | 5.9%（7） |
| Perturb-KL-Direct-AltSeq | 68.868（4） | 67.107（3） | 3.990（4） | 17.6%（并列4） |
| CMA-Direct | 68.826（5） | 65.404（4） | 4.031（5） | 23.5%（3） |
| VisEdit-Contrib-Pre-KeyToken | 67.294（6） | 64.873（7） | 5.563（6） | 17.6%（并列4） |
| SaLEM-Alt-Direct | 67.173（7） | 65.092（5） | 5.684（7） | 35.3%（2） |

**阶段性结论：**扩展到17个完整可比组合后，**Ours-Direct仍在四项Top-3指标上全部排名第1**。相对各指标第2名，Mean Best@3高1.696分，Mean Mean@3高0.523分，Mean Regret@3低1.696分，Hit@3高5.9个百分点。

与此前12组合结果相比，Ours-Direct的四项指标由`71.365 / 68.676 / 1.703 / 50.0%`变为`70.873 / 68.541 / 1.984 / 41.2%`。新增组合提高了任务难度并使绝对值发生变化，但四项排名均保持第1。该结论属于17/21组合下的阶段性结果，剩余两组真实评测与两个PaliGemma L0终止失败不以0分填充，最终论文结论仍应在明确缺失机制与统计检验后报告。

可复核明细：`md/Location/6location_formal7_OursDirect_main_correlation_analysis.md` §5.1、`outputs/formal7_method_top3_summary_17combos_20260824.csv`、`outputs/formal7_method_top3_fair_rows_17combos_20260824.csv`、`outputs/formal7_live_main_outcomes_20260824.csv`。

#### 3.4.5.2 Top-5并集：已完成、失败与待补

汇总：21组Top-5并集共429个“数据集×模型×层”实验项；已完整评测330项，已知不收敛失败2项，待补97项。该汇总按下方21行逐行求和，满足`330+2+97=429`。Top-5待补是后续扩展比较范围，不等同于当前所有项都应立即启动。

| Dataset | Model | 正式7方法Top-5并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 | 主:L15,L16,L14,L17,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 14 | - | L13 | 1 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L22 | 24 | 主:L15,L16,L14,L28,L27,L26,L25,L0,L18,L19,L2,L1,L4,L3,L11 | 15 | - | L17,L13,L24,L20,L5,L6,L9,L10,L22 | 9 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19,L7 | 25 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L8,L9,L10,L29,L0,L1,L2,L18,L19,L7 | 18 | - | L13,L23,L5,L6,L21,L3,L4 | 7 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 22 | 主:L15,L16,L14,L28,L27,L26,L25,L24,L7,L6,L5 | 11 | - | L17,L13,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 11 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L6 | 24 | 主:L17,L18,L16,L19,L15,L29,L28,L27,L26,L11,L14,L12,L2,L30,L1,L3,L0,L21,L20 | 19 | - | L25,L13,L10,L4,L6 | 5 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4,L2 | 14 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L5,L4,L3 | 11 | L0 | L13,L2 | 2 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3 | 22 | 主:L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L22,L21,L20,L19,L1,L2,L0,L3 | 19 | - | L6,L18,L4 | 3 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L0,L18,L19,L20,L1,L3,L4,L2 | 16 | - | L13,L23,L5 | 3 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L23,L22 | 22 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L1,L3,L5,L23,L22 | 19 | - | L13,L20,L8 | 3 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 | 主:L15,L16,L14,L17,L26,L25,L24,L31,L5,L8,L9,L0,L1,L3,L2,L10,L11 | 17 | - | L13,L23,L22,L6,L4 | 5 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 | 主:L15,L16,L14,L28,L27,L26,L24,L7,L8,L9,L22,L0,L1,L2,L3 | 15 | - | L17,L13,L25,L6,L10,L23,L4,L5 | 8 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4,L7 | 22 | 主:L17,L18,L16,L19,L28,L27,L26,L12,L11,L14,L13,L2,L30,L1,L6,L0,L7 | 17 | - | L15,L25,L24,L3,L4 | 5 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 | 主:L8,L9,L10,L14,L12,L11,L17,L4；stable-only:L7,L6,L13,L5,L3,L2,L1 | 15 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2 | 18 | - | L3 | 1 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | 主:L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L23,L22 | 23 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L30,L5,L3,L1,L23,L22 | 20 | - | L13,L20,L8 | 3 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 | 主:L15,L16,L14,L25,L24,L23,L22,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | L17,L13,L21,L29 | 4 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L17,L13,L25,L24,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 18 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0 | 19 | 主:L17,L18,L16,L15,L29,L28,L27,L26,L25,L14,L13,L2,L30,L1,L0 | 15 | - | L19,L12,L6,L3 | 4 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4,L19 | 20 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L2 | 15 | - | L5,L8,L3,L4,L19 | 5 |

可复核的机器可读结果：`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`。生成逻辑：`outputs/recalculate_formal7_main_formula_unions.py`。

### 3.4.6 正式7方法 + CMA-ModelPred v2并集、完成状态与阶段指标（当前新版）

版本标识：`formal7-cma-modelpred-v2-20260914`。本节是追加的新版本，不删除、不覆盖3.4.5的历史`CMA-Direct v1.3/alt`并集及阶段指标。除CMA改为2.8.1的`CMA-ModelPred-Direct`外，其余六种方法保持原正式口径：`Middle-Prior-Direct`、`VisEdit-Contrib-Pre-KeyToken`、`SaLEM-Alt-Direct`、`LGA-Param-Direct-AltModelPred`、`Perturb-KL-Direct-AltSeq`、`Ours-Direct(M_abscos_x_newn)`。

完成验收仍要求对应层具有主配置或明确分栏的stable结果、有效selected checkpoint、独立test/eval完整结果和`eval_full.done`。缺失不记0分；PaliGemma L0不收敛失败单列。服务器只读复核至2026-09-14 10:59 CST：Job 3178538仍在训练EVQA/LLaVA L0，Job 3178423仍等待MMKE-entity/LLaVA L22正式评测，二者均未提前计为完成。

#### 3.4.6.1 CMA-ModelPred v2 Top-3并集与完成状态

汇总：21组Top-3并集共306项；已完整评测290项，已知不收敛失败2项，待补14项，满足`290+2+14=306`。

| Dataset | Model | v2 Top-3并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2 | 11 | 主:L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2 | 11 | - | - | 0 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11 | 14 | 主:L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11 | 14 | - | - | 0 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19 | 16 | 主:L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19 | 16 | - | - | 0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2 | 14 | 主:L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25 | 11 | - | L0,L1,L2 | 3 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L15 | 16 | 主:L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L15 | 16 | - | - | 0 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | 主:L8,L9,L7,L12,L11,L10,L17,L5,L6,L4,L3 | 11 | L0 | - | 0 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L5 | 16 | 主:L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L5 | 16 | - | - | 0 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | 主:L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | - | - | 0 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L25,L22 | 17 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L25,L22 | 17 | - | - | 0 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | 主:L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | - | - | 0 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | 主:L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | - | - | 0 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13 | 14 | 主:L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13 | 14 | - | - | 0 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3 | 13 | 主:L8,L9,L14,L12,L10,L17,L4；stable-only:L7,L13,L5,L6,L3 | 12 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L5 | 15 | 主:L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L5 | 15 | - | - | 0 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | 主:L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | - | - | 0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L25,L22 | 17 | 主:L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L25,L22 | 17 | - | - | 0 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | 主:L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | - | 0 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12,L4 | 18 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L22,L24,L1,L9,L7,L0,L2,L13,L11,L12,L4 | 11 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L20 | 14 | 主:L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L20 | 14 | - | - | 0 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3 | 13 | 主:L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3 | 13 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2 | 11 | 主:L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2 | 11 | - | - | 0 |

#### 3.4.6.2 17个完整可比组合上的七方法Top-3阶段指标

完整可比组合仍为17/21：EVQA除PaliGemma和LLaVA外的5组；MMKE-visual除PaliGemma外的6组；MMKE-entity除LLaVA外的6组。两组PaliGemma L0终止失败不以0分填充；两组LLaVA仍有未评测层。

| 方法 | Mean Best@3 ↑ | Mean Mean@3 ↑ | Mean Regret@3 ↓ | Hit@3 ↑ |
|---|---:|---:|---:|---:|
| **Ours-Direct** | 70.873（1） | 68.541（1） | 1.984（1） | 41.2%（1） |
| CMA-ModelPred-Direct | 69.899（2） | 67.369（3） | 2.958（2） | 29.4%（3） |
| LGA-Param-Direct-AltModelPred | 69.177（3） | 65.001（6） | 3.680（3） | 11.8%（6） |
| Middle-Prior-Direct | 68.962（4） | 68.018（2） | 3.895（4） | 5.9%（7） |
| Perturb-KL-Direct-AltSeq | 68.868（5） | 67.107（4） | 3.990（5） | 17.6%（4） |
| VisEdit-Contrib-Pre-KeyToken | 67.294（6） | 64.873（7） | 5.563（6） | 17.6%（4） |
| SaLEM-Alt-Direct | 67.173（7） | 65.092（5） | 5.684（7） | 35.3%（2） |

**阶段结论：** 替换为`CMA-ModelPred-Direct`后，Ours-Direct仍在Mean Best@3、Mean Mean@3、Mean Regret@3和Hit@3四项指标上全部排名第1。新版CMA相对历史CMA的`68.826 / 65.404 / 4.031 / 23.5%`提升为`69.899 / 67.369 / 2.958 / 29.4%`，在Best、Mean和Regret上升至第2，但仍未超过Ours-Direct。

#### 3.4.6.3 CMA-ModelPred v2 Top-5并集与完成状态

汇总：21组Top-5并集共432项；已完整评测330项，已知不收敛失败2项，待补100项，满足`330+2+100=432`。严格只使用主配置完整结果时，目前仅MMKE-entity/PaliGemma达到七方法Top-5完整可比；因此暂不把单组合Top-5方法均值作为总体结论。

| Dataset | Model | v2 Top-5并集 | 层数 | 已完成（配置分开） | 完成数 | 已知失败 | 待补 | 待补数 |
|---|---|---|---:|---|---:|---|---|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 | 主:L15,L16,L14,L17,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 14 | - | L13 | 1 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L21,L22 | 25 | 主:L15,L16,L14,L28,L27,L26,L25,L0,L18,L19,L2,L1,L4,L3,L11 | 15 | - | L17,L13,L24,L20,L5,L6,L9,L10,L21,L22 | 10 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19 | 24 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L8,L9,L10,L29,L0,L1,L2,L18,L19 | 17 | - | L13,L23,L5,L6,L21,L3,L4 | 7 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4 | 21 | 主:L15,L16,L14,L28,L27,L26,L25,L24,L7,L6,L5 | 11 | - | L17,L13,L8,L9,L23,L0,L1,L2,L3,L4 | 10 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L8,L5 | 25 | 主:L17,L18,L16,L19,L15,L29,L28,L27,L26,L11,L14,L12,L2,L30,L1,L3,L0,L21,L20 | 19 | - | L25,L13,L10,L4,L8,L5 | 6 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4 | 13 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L5,L3,L4 | 11 | L0 | L13 | 1 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3,L5 | 23 | 主:L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L22,L21,L20,L19,L1,L2,L0,L3,L5 | 20 | - | L6,L18,L4 | 3 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 | 主:L15,L16,L14,L17,L26,L25,L24,L22,L0,L18,L19,L20,L1,L3,L4,L2 | 16 | - | L13,L23,L5 | 3 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L22,L23,L21 | 23 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L1,L3,L5,L22,L23 | 19 | - | L13,L20,L8,L21 | 4 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 | 主:L15,L16,L14,L17,L26,L25,L24,L31,L5,L8,L9,L0,L1,L3,L2,L10,L11 | 17 | - | L13,L23,L22,L6,L4 | 5 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 | 主:L15,L16,L14,L28,L27,L26,L24,L7,L8,L9,L22,L0,L1,L2,L3 | 15 | - | L17,L13,L25,L6,L10,L23,L4,L5 | 8 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4 | 21 | 主:L17,L18,L16,L19,L28,L27,L26,L12,L11,L14,L13,L2,L30,L1,L6,L0 | 16 | - | L15,L25,L24,L3,L4 | 5 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 | 主:L8,L9,L10,L14,L12,L11,L17,L4；stable-only:L7,L6,L13,L5,L3,L2,L1 | 15 | L0 | - | 0 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2 | 18 | - | L3 | 1 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1,L7,L10 | 18 | 主:L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | - | L7,L10 | 2 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L22,L21,L23 | 24 | 主:L15,L16,L14,L17,L28,L27,L26,L25,L24,L18,L19,L2,L0,L4,L30,L5,L3,L1,L22,L23 | 20 | - | L13,L20,L8,L21 | 4 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 | 主:L15,L16,L14,L25,L24,L23,L22,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | - | L17,L13,L21,L29 | 4 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 | 主:L15,L16,L14,L28,L27,L26,L23 | 7 | - | L17,L13,L25,L24,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 18 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0,L20,L22 | 21 | 主:L17,L18,L16,L15,L29,L28,L27,L26,L25,L14,L13,L2,L30,L1,L0,L20,L22 | 17 | - | L19,L12,L6,L3 | 4 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2 | 15 | 主:L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2 | 15 | - | - | 0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4 | 19 | 主:L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L2 | 15 | - | L5,L8,L3,L4 | 4 |

#### 3.4.6.4 版本边界与机器可读结果

- 3.4.5及其CSV继续代表历史`CMA-Direct v1.3/alt`版本；本节代表`CMA-ModelPred-Direct v2`，两版不得混合平均、跨版本取最大值或互相覆盖。
- v2并集与状态：`outputs/formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv`。
- v2逐组合方法指标：`outputs/formal7_cma_modelpred_v2_method_fair_rows_20260914.csv`。
- v2方法汇总：`outputs/formal7_cma_modelpred_v2_method_summary_20260914.csv`。
- 可复现脚本：`outputs/recalculate_formal7_cma_modelpred_v2_20260914.py`。
+
### 3.4.7 八方法（CMA-alt与CMA-model_pred同时保留）最新完成状态：2026-09-21

本节按六种固定方法加两版CMA，共八个版本化方法行的Top-3候选层去重统计；Ours仅取主公式`M_abscos_x_newn`。历史3.4.5与3.4.6为各自日期的七方法快照，保留原文，不能直接当作当前缺层清单。八方法共324个“数据集×模型×层”项；截至2026-09-21约20:25 CST，已有完整评测311项（其中MMKE-visual/PaliGemma的L1,L2,L3,L5,L6,L7,L13共7项为stable-only，不能直接计作主配置），尚未完成11项，另有不收敛失败2项。恒等式为`311+11+2=324`；该计数是评测覆盖，不代表311项均正常收敛或具备同配置公平比较资格。

| 数据集 | 模型 | 层 | 当前状态 |
|---|---|---|---|
| EVQA-pilot500 | LLaVA-v1.5-7B | L2 | 已训练和选点，尚无`eval_full.done`，待正式评测 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L4 | 待训练与正式评测 |
| MMKE-entity | LLaVA-v1.5-7B | L1 | 用户要求暂停，Epoch17恢复点已保存；未完成正式评测 |
| MMKE-entity | LLaVA-v1.5-7B | L9,L7,L0,L2,L13,L11,L12,L4 | 待训练与正式评测，共8层 |
| EVQA-pilot500 | PaliGemma-3B | L0 | 历史不收敛；本次可访问共享盘与本地未找到checkpoint，g09临时盘因无该节点作业权限不能核验，暂未补评测，见3.5.2 |
| MMKE-visual | PaliGemma-3B | L0 | 本次已用各自run的最低有限EMA现存checkpoint补评测：主配置Average 38.520、stable配置35.442；训练仍标不收敛，见3.5.2及4.0 |

本次纠正旧待补状态：EVQA/LLaVA L0、L1与MMKE-entity/LLaVA L22、L24均已正式评测，完整指标已补入第4.0节对应数据集表。前两层各评测2,093条，后两层各评测954条；不能继续列入待补。PaliGemma补评测尚未完成前不提前计数，也不因用户允许补评测而抹去历史训练失败。

**2026-09-21补评测后更新：** MMKE-visual/PaliGemma L0已有主配置与stable两份完整独立评测，按唯一层仅新增1个已评测项。八方法Top-3并集当前为`312已有评测 + 11未完成 + 1仍缺评测失败 = 324`。其中L0是“不收敛checkpoint的诊断补评测”，不能据此声称完成正常收敛或标准50epoch训练；7个stable-only层继续单列，不自动重算既有公平比较指标。训练失败的历史事实仍为两组，而目前仍无评测的失败层只剩EVQA/PaliGemma L0。

### 3.4.8 八方法联合候选并集最新核验（2026-09-22，保留两版CMA）

口径：六个固定定位方法加历史 **CMA-alt**、新版 **CMA-model_pred**，共8个版本化方法；Ours仍只取主公式。逐一核对168个方法×组合的Top-3/Top-5推荐行，再按“数据集×模型×层”去重。这里是八方法联合覆盖，不替换前文两个七方法历史快照，也不将两版CMA分数混用或择优。

**Top-3联合并集324项：313项已有独立评测，11项仍缺独立评测。** 313项细分为304项历史主配置验收记录、7项stable-only、2项不收敛诊断补评测。后两类不能自动计入“标准50 epoch主配置完整可比”；304项中已有的历史恢复/数值异常标签也继续保留。本次没有重算方法排名。

| 数据集 | 模型 | 尚缺评测的Top-3并集层 | 数量 | 当前证据 |
|---|---|---|---:|---|
| EVQA-pilot500 | LLaVA-v1.5-7B | L2、L4 | 2 | L2已有训练完成标记和selected，但无完整eval；L4无完整评测 |
| MMKE-entity | LLaVA-v1.5-7B | L0、L1、L2、L4、L7、L9、L11、L12、L13 | 9 | L1按用户要求暂停，保留Epoch17恢复点；其余8层无完整评测 |

EVQA/LLaVA L0、L1及MMKE-entity/LLaVA L22、L24已经评测，不在缺层表。此表是集合清单，**不是新启动或恢复队列的指令**；未恢复用户暂停的MMKE-entity训练。

| 数据集 | BLIP2 | InstructBLIP | MiniGPT-4 | LLaVA | Qwen2.5-VL | PaliGemma | SmolVLM |
|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | 12/12 | 15/15 | 17/17 | 13/15 | 17/17 | 12/12（含诊断L0） | 17/17 |
| MMKE-visual | 13/13 | 19/19 | 16/16 | 15/15 | 15/15 | 15/15（含诊断L0及7项stable-only） | 16/16 |
| MMKE-entity | 14/14 | 19/19 | 17/17 | 9/18 | 14/14 | 16/16 | 12/12 |

表中分子仅表示已有评测，**19/21组合覆盖齐全不等于19个标准主配置完整可比组合**。两项诊断为EVQA/PaliGemma L0和MMKE-visual/PaliGemma L0，仍标不收敛、非完整50轮；7项stable-only为MMKE-visual/PaliGemma L1,L2,L3,L5,L6,L7,L13。严格要求标准主配置时，除11个缺评测层外，这9项也是协议例外，不能隐藏。

Top-5八方法联合并集另为439项，其中339项已有评测（含同样2项诊断和7项stable-only），100项无完整评测；不能把Top-5的100项与当前Top-3的11项混淆。

以下是Top-5附加缺口，**包含上述Top-3的11项，不是再额外增加100项**。按现有验收台账及本次活跃任务核验统计，未验收项不代表从未尝试训练，也不授权自动启动。

| 数据集 | 模型 | Top-5联合并集尚无完整评测的层 | 数量 |
|---|---|---|---:|
| EVQA-pilot500 | BLIP2 | L13 | 1 |
| EVQA-pilot500 | InstructBLIP | L5,L6,L9,L10,L13,L17,L20,L21,L22,L24 | 10 |
| EVQA-pilot500 | MiniGPT-4 | L3,L4,L5,L6,L13,L21,L23 | 7 |
| EVQA-pilot500 | LLaVA | L2,L3,L4,L8,L9,L10,L13,L17,L23 | 9 |
| EVQA-pilot500 | Qwen2.5-VL | L4,L5,L6,L8,L10,L13,L25 | 7 |
| EVQA-pilot500 | PaliGemma | L2,L13 | 2 |
| EVQA-pilot500 | SmolVLM | L4,L6,L18 | 3 |
| MMKE-visual | BLIP2 | L5,L13,L23 | 3 |
| MMKE-visual | InstructBLIP | L8,L13,L20,L21 | 4 |
| MMKE-visual | MiniGPT-4 | L4,L6,L13,L22,L23 | 5 |
| MMKE-visual | LLaVA | L4,L5,L6,L10,L13,L17,L23,L25 | 8 |
| MMKE-visual | Qwen2.5-VL | L3,L4,L15,L24,L25 | 5 |
| MMKE-visual | SmolVLM | L3 | 1 |
| MMKE-entity | BLIP2 | L7,L10 | 2 |
| MMKE-entity | InstructBLIP | L8,L13,L20,L21 | 4 |
| MMKE-entity | MiniGPT-4 | L13,L17,L21,L29 | 4 |
| MMKE-entity | LLaVA | L0,L1,L2,L3,L4,L6,L7,L8,L9,L10,L11,L12,L13,L17,L21,L25 | 16 |
| MMKE-entity | Qwen2.5-VL | L3,L6,L12,L19 | 4 |
| MMKE-entity | SmolVLM | L3,L4,L5,L8,L19 | 5 |

MMKE-visual与MMKE-entity的PaliGemma在该Top-5集合中无新增缺评测层，但前述诊断、stable-only及数值异常限制仍适用。

核验来源与范围：推荐矩阵与`Firstprash_7_location_recommend.md`全部168行交叉一致；历史验收覆盖来自已有逐层记录和两版并集CSV；当前LLaVA缺口额外核验g07/g08任务目录及共享盘的selected、train/eval标记和结果。不是对所有历史权重重新训练或全量重新评测。机器可读逐层证据：`outputs/localization_audit_20260922/formal8_union_status.json`；复算脚本：`outputs/audit_formal8_union_20260922.py`；实时产物清单为同目录`evqa_llava_tmp.json`、`evqa_llava_shared.json`、`entity_llava_tmp.json`、`entity_llava_shared.json`。最新PaliGemma诊断结果见3.5.3及4.0。

### 3.5 PaliGemma 主配置 / stable 结果、异常与重跑总登记

本节是后续 PaliGemma 失败层重跑的统一入口。最新快照来自 2026-07-19 08:38 对 Slurm job `3044208`、g09/物理GPU0的服务器结果、进程、日志与完成标记交叉检查。补跑顺序为EVQA stable L6、MMKE-entity stable L12、EVQA stable L4、MMKE-entity主配置L16，四层均已完成训练及对应test/eval完整评测，队列于2026-07-19 05:22:31自动结束，当前无PaliGemma训练或评测进程。生成重跑队列时搜索状态中包含的精确前缀 `RETRY_REQUIRED` 或 `FAILED`；`EVAL_DONE` 表示同层同时存在非空 `selected_checkpoint.tsv`、对应 test/eval 完整结果和 `eval_full.done`。

| Dataset | Config | 目标/已有范围 | 已完整评测 | 失败/未验收 | 当前与后续 |
|---|---|---|---|---|---|
| MMKE-visual | 主配置 `paligemma-3b.yaml` | 原始 run 7层：L8,L9,L10,L11,L12,L14,L17 | 7/7 | 无未评测层；L14 的负 EMA 和 L17 的高 loss 属于已评测数值异常结果 | 已结束 |
| MMKE-visual | stable | 共尝试15层 | 14/15：L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L14,L17 | L0 `FAILED_NONCONVERGENT` | 已结束；L0 不自动按原配置重跑 |
| EVQA-pilot500 | 主配置 | 既有完整评测6层：L9,L10,L11,L12,L14,L15；job 3044208追加8层 | 新增7/8：L1,L4,L5,L6,L7,L8,L17；连同既有结果共13个唯一完成层 | L9为历史stall恢复结果；L14为负EMA数值异常结果；新增L0在Epoch47后loss=nan、rc=1，无selected/eval | 阶段已结束；7个新增完成层均使用`vqa_eval.json`完整评测2,093条 |
| EVQA-pilot500 | stable | 8层：L8,L7,L17,L0,L5,L6,L1,L4 | 7/8：L1,L4,L5,L6,L7,L8,L17 | L0不收敛且无selected/eval；L4补跑虽完成但训练中触发16次nonfinite梯度安全跳步 | L6采用`data_buffer_size=1`、L4采用optimizer-step finite保护后均完成50 epoch，并使用`vqa_eval.json`完整评测2,093条；仅L0保留失败 |
| MMKE-entity | stable | 15层 | 14/15：L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L16,L17 | L0训练满50 epoch但不收敛，stable筛选后无selected/eval | L12采用`data_buffer_size=1`从头重训成功，Epoch48 selected，完成954条评测，Average 95.296；仅L0记录不收敛失败 |
| MMKE-entity | 主配置 | 15层 | 15/15：L0,L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L16,L17 | 无缺评测层；L0数值退化（Average 20.00）；L16补跑触发34次nonfinite梯度安全跳步且结果偏低（Average 47.044） | L16采用optimizer-step finite保护从头重训，Epoch49 selected，完成954条评测；双标记完整，但保留数值异常注释 |

#### 3.5.1 异常原因、现存 checkpoint 与重跑建议

| Dataset | Config | Layer | 状态标记 | 异常/结果 | 原因核验 | 现存 checkpoint | 队列结束后的处理建议 |
|---|---|---:|---|---|---|---|---|
| MMKE-visual | 主配置 | L14 | `EVAL_DONE_NUMERIC_ANOMALY` | Ckpt Epoch 1，EMA `-351.953961`，Average 39.03；已完成293条评测 | 负 EMA 不符合 stable 筛选口径，结果虽可复现但数值质量异常 | selected/eval均存在 | 不列入必重跑；比较时优先使用已完成的 stable L14（Average 58.87），主配置结果保留作异常对照 |
| MMKE-visual | stable | L8 | `EVAL_DONE_RECOVERED_EPOCH13` | 训练在 Epoch 13 后中断，使用 Epoch 13 checkpoint 手动完成293条评测，Average 96.92 | 属于中断恢复，不是完整50轮训练结束 | selected/eval均存在 | 若论文严格要求每层完整50轮，可列为可选重跑；否则保留并明确 recovered 状态 |
| MMKE-visual | stable L0专用配置 | L0 | `FAILED_NONCONVERGENT` | 训练至 Epoch 26 的212/214；EMA长期约3.4k--3.5k，整层nonfinite反复出现；保存时另有 `PytorchStreamWriter file write failed / unexpected pos` | 主要原因是数值不收敛，写盘错误是末次保存的附加故障，不是“不收敛”的根因 | 无selected、无eval | 原配置同seed直接重跑大概率重复失败；正式表记录不收敛。若必须探索，单独使用更低学习率等敏感性配置，并与主结果分栏 |
| EVQA-pilot500 | 主配置 | L9 | `EVAL_DONE_RECOVERED_FROM_STALL` | 使用恢复checkpoint完成2,093条评测，Average 36.16 | 历史训练发生stall；恢复后评测完整 | selected/eval均存在 | 不列入必重跑；若要求严格完整50轮，可在队列结束后列为可选重跑 |
| EVQA-pilot500 | 主配置 | L14 | `EVAL_DONE_NUMERIC_ANOMALY` | Ckpt Epoch 1，EMA `-1369.521638`，Average 32.06；已完整评测 | 负 EMA 明显异常，不能解释为正常收敛，但评测产物完整 | selected/eval均存在 | 该层不在当前12层候选并集内，不优先重跑；如用于附加比较，建议另补 stable 版本 |
| EVQA-pilot500 | 主配置 | L0 | `FAILED_NONFINITE_LOSS_NONCONVERGENT` | 训练至Epoch47后loss变为nan，累计284次nonfinite gradient跳步，rc=1，无评测 | 不是OOM或watchdog卡住；loss/EMA长期约2.8k--3.2k，数值未收敛，最终运行时异常退出 | 无selected、无eval | 正式记录不收敛失败；主配置与stable均失败，原配置直接重跑价值低。若必须探索，仅作为低学习率等独立敏感性实验 |
| EVQA-pilot500 | stable | L0 | `FAILED_NONCONVERGENT` | Epoch 49、约 step 12196 发生参数 nonfinite；此前整层nonfinite反复出现，loss/EMA约2.7k--3.4k | 早层反向路径数值敏感；stable保护能跳过坏梯度，但不能使该层形成有效收敛 | 有有限值原始checkpoint（最佳保留约 Epoch 47、EMA 2770.6896），无selected/eval | 不建议原配置直接重跑；记录不收敛。若必须探索，作为独立低学习率敏感性实验，不冒充当前stable结果 |
| EVQA-pilot500 | stable | L4 | `EVAL_DONE_RETRY_NUMERIC_GUARD` | 旧run在Epoch29参数nonfinite、rc=1；加入optimizer-step finite检查/保护后从头完成50 epoch，训练中有16次nonfinite梯度安全跳步 | 原异常为Adam更新后的参数数值崩溃；修复不改变epoch、batch、lr、seed、数据或优化目标，只阻止坏更新污染参数 | 新selected为Epoch50，raw/EMA loss `0.591566/0.491418`；selected/eval均存在 | 已使用`vqa_eval.json`完整评测2,093条：Rel 66.09、T-Gen 64.75、M-Gen 85.62、T-Loc 100.00、M-Loc 77.50、Average `78.792`。从必重跑列表移出，保留16次安全跳步注释 |
| EVQA-pilot500 | stable | L6 | `EVAL_DONE_RETRY_BUFFER1` | 旧run在Epoch12后停滞并由watchdog终止；`data_buffer_size=1`从头重跑完成50 epoch | 旧异常不是OOM，属于后台预取/数据准备停滞；串行buffer后未复现卡住 | 新selected为Epoch50，raw/EMA loss `0.423632/0.468850`；selected/eval均存在 | 已使用`vqa_eval.json`完整评测2,093条：Rel 69.94、T-Gen 69.13、M-Gen 89.83、T-Loc 100.00、M-Loc 68.92、Average `79.564`。从必重跑列表移出 |
| MMKE-entity | stable | L12 | `EVAL_DONE_RETRY_BUFFER1_GPU_MIGRATED` | 旧run在Epoch45后停滞；首次补跑误落GPU1并与InstructBLIP冲突，现场归档至Epoch7；随后在job3044208/物理GPU0从Epoch1重训并完成50 epoch | 原始失败是后台预取/数据准备停滞，不是不收敛；正式补跑固定正确Slurm cgroup并使用`data_buffer_size=1`，无OOM、nonfinite或Traceback | 新selected为Epoch48，raw/EMA loss `0.538605/0.830285`；selected/eval均存在。误落GPU1的Epoch2--6 checkpoints与Epoch7日志仅作冲突记录，不作为正式结果 | 已使用MMKE-entity eval数据完整评测954条：Rel 93.40、T-Gen 93.26、M-Gen 93.41、T-Loc 100.00、M-Loc 96.41、Average `95.296`。从必重跑列表移出 |
| MMKE-entity | stable | L0 | `FAILED_NONCONVERGENT` | 已训练满50 epoch；最终raw loss 2806.0613、EMA 2776.7354，累计120次整层nonfinite gradient并跳过step；stable筛选`kept=0`，rc=1，无评测 | 不是OOM，也不是2小时总运行时间限制；L0全程loss维持约2.7k--3.5k，10个保留候选checkpoint均因`too_large`被拒绝，没有合格selected checkpoint | 有10个原始候选checkpoint，但均不满足stable验收；无`selected_checkpoint.tsv`、无`eval_full.done` | 正式记录不收敛失败，不按原配置自动重跑。若必须探索，仅作为独立低学习率等敏感性实验，并与当前stable结果分栏 |
| MMKE-entity | 主配置 | L0 | `EVAL_DONE_NUMERIC_DEGENERATE` | Ckpt Epoch8，raw 2887.8733、EMA 2815.5878；完成954条评测但Rel/T-Gen/M-Gen/M-Loc均为0，仅T-Loc为100，Average 20.00 | 双完成标记齐全，因此作为真实评测结果保留；但loss极高且指标退化，不能解释为正常收敛 | selected/eval均存在 | 不列为“缺评测”；统计和论文中单独标注数值退化。若追求有效编辑结果，再以独立稳定化配置重跑 |
| MMKE-entity | 主配置 | L16 | `EVAL_DONE_RETRY_NUMERIC_GUARD` | 旧run训练至Epoch33后loss=nan、rc=1；加入optimizer-step finite保护后从头完成50 epoch，补跑中触发34次nonfinite梯度安全跳步 | 不是OOM；主配置该层仍有明显数值敏感性。保护避免坏更新污染参数，但低分结果不能解释为稳定收敛 | 新selected为Epoch49，raw/EMA loss `15.929332/18.301300`；selected/eval均存在 | 已使用MMKE-entity eval数据完整评测954条：Rel 12.43、T-Gen 12.21、M-Gen 12.41、T-Loc 100.00、M-Loc 98.17、Average `47.044`。从缺失/必重跑列表移出，但统计和论文中保留数值异常、低分与34次安全跳步注释 |

说明：`rc=143` 是旧run被watchdog终止后的进程退出码，不是失败143次。L4/L6/L12旧run的恢复候选checkpoint仍只作历史诊断；本次登记使用的是从Epoch1重新训练50轮后生成的新selected和完整test/eval结果，不是直接补评旧checkpoint。L4、L6、L12、L16均已从`RETRY_REQUIRED`/`FAILED`移出；其中L4与L16仍保留nonfinite安全跳步和数值质量注释。

#### 3.5.2 不收敛L0现存checkpoint补评测（2026-09-21，用户明确授权）

用户授权对不收敛的PaliGemma L0仍取最低checkpoint补做独立评测。此次只评测现存权重，未重训或改变历史训练配置。选点规则为**同一run内现存、可加载、EMA有限的checkpoint中取EMA最低者**；同时检查保存内容的epoch、EMA与loss_history一致及26个参数张量均为有限值。不同配置、不同重跑版本不混在一起选最低值；“不收敛”与“已有评测”分别记录。

| 数据集 | 配置/学习率 | 选中Epoch/step | raw loss | EMA loss | 独立eval数 | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 解释 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MMKE-visual | main，lr=1e-4 | 1 / 107 | 3465.718750 | 3508.007406 | 293 | 0.10 | 0.08 | 0.09 | 100.00 | 92.33 | **38.520** | 不收敛；本run现存7个checkpoint中最低有限EMA；非完整50epoch训练 |
| MMKE-visual | stable L0专用，lr=1e-6 | 25 / 2675 | 3402.662842 | 3454.815660 | 293 | 0.09 | 0.09 | 0.10 | 100.00 | 76.93 | **35.442** | 不收敛；本run现存8个checkpoint中最低有限EMA；Epoch26保存失败，仅残留lock，没有可加载权重 |
| EVQA-pilot500 | main / stable | — | — | — | 0 | — | — | — | — | — | — | 本次未找到可访问checkpoint，不能补评测；未填0分，未冒充完成 |

两份MMKE-visual评测在Job3178538/g08中串行完成，原训练队列和其他GPU进程未停止；Job3178423的LLaVA仍按用户要求暂停。输出直接写共享盘`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/paligemma_l0_nonconvergent_eval_20260921/`，没有复制大权重到服务器`/tmp`。其下`mmke-visual_main_l0_lr1e4`与`mmke-visual_stable_l0_lr1e6`各有`selection_audit.json`、原配置、原loss_history、`layer_00/selected_checkpoint.tsv`、`eval_full.done`及逐样本`results.json`、`mean_results.json`；本次没有伪造`train.done`。小型结构化结果已同步到本地同名`server_results/live_backfill/paligemma_l0_nonconvergent_eval_20260921/`目录。

原权重来源（共享盘根目录`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/`）：

- main：`mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b/layer_00/records/vead/paligemma-3b/pilot500_blip2_visedit_L00-lr-1-t-1-v-1/checkpoints/epoch-1-i-107-ema_loss-3508.0074`；SHA-256=`65f1f71b94e984cbcfa4f73d6f50498b6e3e585e488d9ed77eb9b1272282a06b`。
- stable：`paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b/layer_00/records/vead/paligemma-3b/pilot500_blip2_visedit_L00-lr-1-t-1-v-1/checkpoints/epoch-25-i-2675-ema_loss-3454.8157`；SHA-256=`0007fbf37069132da4911818ca8d0cb8ef9f33b3f0f77ac13c8b50a04eb21140`。

EVQA核验限制：已检索共享`server_results`、项目`records`、登录节点`/var/tmp/ph_teacher3`及可访问g07/g08相关临时目录；共享归档`tmp_archives_20260810/g09/paligemma_followup_job3044208_20260715_112056/`下的`paligemma_main_evqa_pilot500_job3044208_20260715_112056/paligemma-3b/layer_00`与`paligemma_stable_evqa_pilot500_pending_job3044208_20260715_112056/paligemma-3b/layer_00`只剩空目录。原g09返回`Access denied by pam_slurm_adopt: you have no active jobs on this node`，因此只能确认**当前可访问存储没有找到权重**，不能断言原节点文件已经删除。上方“stable Epoch47、EMA2770.6896仍保留”是历史记录，本次未复核到文件实体。恢复g09访问或找到备份后方可补评测，本次没有新申请作业或重训。

#### 3.5.3 EVQA/PaliGemma L0重训中断后固定Epoch 2诊断评测（2026-09-22）

在用户授权的Job3178538/g08主配置补跑中，训练保存30轮记录后停在Epoch31、100/500，未完成50轮。用户随后明确要求“不用续跑，就用这个epoch 2测试”；本次没有续训，固定使用本run现存最低有限EMA的Epoch2/step500。原配置和历史不收敛结果保留，不能覆盖成正常训练完成。

| Dataset / Model / Layer | Epoch / step | raw loss | EMA loss | eval数 | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EVQA-pilot500 / PaliGemma-3B / L0 | 2 / 500 | 3187.056885 | 3209.824510 | 2093 | 0.16 | 0.18 | 0.16 | 100.00 | 76.96 | **35.492** |

评测于**2026-09-22 08:47:15 CST**退出，rc=0；已核验2093条逐样本结果、`eval_full.done`、selected及SHA-256一致。`training_complete_50_epochs=false`，没有伪造`train.done`；通用训练完成验证仍判不完整，诊断评测单独验收。训练日志154条`SANITIZE_NONFINITE_GRAD_BEFORE_STEP`记录，不能把有限loss/EMA或有限checkpoint权重解释为收敛、没有梯度异常。极低Rel/Generality也说明编辑效果退化；Average不能替代这一质量注释。

- 共享盘原始结果：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_paligemma_l0_main_retrain_job3178538_20260921/`。
- selected：该目录`layer_00/records/vead/paligemma-3b/pilot500_blip2_visedit_L00-lr-1-t-1-v-1/checkpoints/epoch-2-i-500-ema_loss-3209.8245`；SHA-256 `9405c64d2e1d5b96f5ab96b0109a25b8dcde2697f46faec319b37727efbef260`。
- 本地轻量归档：`server_results/live_backfill/pali_l0_diag_20260922/evqa-pilot500/paligemma-3b/layer_00/`，含逐样本`results.json`、`mean_results.json`、selected、完成标记、原配置、loss_history和诊断验证记录。大checkpoint仍留共享盘，不重复拉回本地或服务器/tmp。
- `results.json` SHA-256：`05f60b78e9a874d20e8b2f84a278864aec8852325bf3a0c4645419f63a20e970`。同步清单：`outputs/localization_audit_20260922/paligemma_diagnostic_sync_manifest.json`，其中`complete=false`、`diagnostic_only=true`、`evaluation_verified=true`。

本次使八方法Top-3评测覆盖从312升至313，仍缺11个LLaVA层；两个PaliGemma不收敛L0现在都有诊断评测，但均不能冒充标准50轮训练完成。旧3.5.2“EVQA未找到checkpoint”仅描述历史run；这里使用的是新授权重训run，不是找回了旧run。

## 4. 已完成真实扫层结果回填

本节只记录已经完成真实编辑训练与 full E-VQA eval/test 评测的结果。这里的结果用于后续计算不同定位方法的 `Best@3 / Best@5 / Regret@3 / Regret@5 / Hit@3 / Hit@5`。

### 4.0 服务器结构化结果总表

**2026-09-22诊断增量：** EVQA/PaliGemma L0新增Epoch2的2093条完整诊断评测，Average35.492；状态显式包含`NONCONVERGENT_DIAGNOSTIC`及`TRAIN_INCOMPLETE`，详情见3.5.3。不能把本次新增解释为完整50轮训练验收；八方法当前缺层以3.4.8为准，历史日期快照不删除。

**2026-09-21增量回填：** 新增EVQA-pilot500/LLaVA L0、L1和MMKE-entity/LLaVA L22、L24四行，均已核验`train.done`、`selected_checkpoint.tsv`与独立完整`eval_full.done`。EVQA两行的服务器证据位于g08 `/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812/evqa-pilot500/llava-v1.5-7b/layer_00`、`layer_01`；MMKE-entity两行位于共享盘 `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082/mmke-entity/llava-v1.5-7b/layer_22`、`layer_24`。本次回填未重新训练，也未改变选点；各行Epoch为selected checkpoint轮次。EVQA/LLaVA表内唯一完整评测层由13增至15，八方法Top-3覆盖13/15；MMKE-entity/LLaVA由7增至9，八方法Top-3覆盖9/18。以下旧日期完成计数和“L22待评测”等描述保留为历史记录，以本条及3.4.7为最新状态。

来源：服务器各实验目录下的 `layer_*/eval_full.done` 与同层 `selected_checkpoint.tsv`。只回填 `EVAL_DONE` 的真实评测结果；标准 checkpoint 口径为每层训练 `50 epoch` 后按 minimum EMA loss 选择。因中断而从较早有限值 checkpoint 恢复并完成评测的例外，必须明确标记为 `TRAIN_RECOVERED_*` 或 `EVAL_DONE_RECOVERED_*`，不与标准 50 epoch 完成混淆。`EVQA-pilot500 / BLIP2-OPT-2.7B` 的历史补跑与复测表保留在 4.1，不在本总表重复列出。

完整性复核（2026-07-16 15:07）：已逐层交叉检查服务器权威结果根目录，只有同时存在非空 `selected_checkpoint.tsv` 和 `eval_full.done` 的层才进入下表。EVQA-pilot500 现有记录与服务器完成项一致、无漏行；本次补入 MMKE-visual MiniGPT-4 的4层，以及 MMKE-entity 的 BLIP2 11层、InstructBLIP 4层、MiniGPT-4 1层、PaliGemma stable 4层。正在训练、暂停、失败或仅有原始 checkpoint 的层仍不计完成。

增量复核（2026-07-17 09:49）：PaliGemma MMKE-entity stable 新增L1,L2,L3,L5,L6共5层，均同时存在非空`selected_checkpoint.tsv`、954条独立eval完整结果和`eval_full.done`，已补入下表。L0与L12没有双完成标记，分别按不收敛失败和卡住待重跑登记，不计入完成。

最终增量复核（2026-07-18 13:08）：服务器 PaliGemma 后续队列已生成`FOLLOWUP_DONE`。EVQA-pilot500主配置新增L1,L4,L5,L6,L7,L8,L17共7层，均具备非空`selected_checkpoint.tsv`、2,093条`vqa_eval.json`完整评测和`eval_full.done`；L0失败且无双标记。MMKE-entity主配置新增L0,L1,L2,L3,L5,L6,L7,L8,L9,L10,L11,L12,L13,L17共14层，均具备双标记和954条完整评测；L16失败且无双标记。以下已按配置分组、组内层号升序回填。

补跑增量复核（2026-07-19 08:38）：已按顺序完成EVQA stable L6、MMKE-entity stable L12、EVQA stable L4、MMKE-entity主配置L16。四层均从Epoch1重训至50 epoch，存在非空`selected_checkpoint.tsv`、对应test/eval完整结果及`eval_full.done`。EVQA两层各评测2,093条，MMKE-entity两层各评测954条。L4/L16分别触发16/34次nonfinite梯度安全跳步，虽验收完成但保留数值异常注释；L12首次误落GPU1的中断现场已归档，不计作正式结果。

MMKE-visual增量复核（2026-07-20 08:14）：Slurm job `3044208`在g09/GPU0完成SmolVLM待补10层与Qwen2.5-VL候选并集21层。SmolVLM 10层均从头训练并完成293条独立MMKE-visual test/eval；Qwen L17复用既有有效selected checkpoint重新评测，其余20层从头训练并评测。逐层均存在非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`，所有训练/评测阶段`rc=0`，未出现OOM、nonfinite、共享盘写入失败或watchdog超时。结构化结果暂存于g09本地`/tmp/ph_teacher3/mmke_visual_smol_qwen_job3044208_20260719_093500`，未覆盖共享结果目录。

MMKE-entity SmolVLM增量复核（2026-07-22 08:35）：Slurm job `3044208`在g09/GPU0完成候选并集15层`L0,L1,L2,L6,L7,L9,L10,L11,L12,L13,L14,L15,L16,L17,L18`。15层均从头训练至50 epoch流程结束并按minimum EMA loss选择checkpoint，随后使用独立MMKE-entity eval数据完整评测954条；逐层`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全。launcher各已结束阶段均为`rc=0`，未发现OOM、nonfinite、共享盘写入失败或watchdog超时。结构化结果暂存于g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/smolvlm-1.7b`；同队列Qwen当时仍从L17开始训练，未计入完成。

MMKE-entity Qwen增量复核（2026-07-24 11:11）：同一队列已于2026-07-23 22:38完成Qwen2.5-VL-3B候选并集18层`L0,L1,L2,L13,L14,L15,L16,L17,L18,L20,L21,L22,L25,L26,L27,L28,L29,L30`。逐层均完成50 epoch训练流程并按minimum EMA loss选择checkpoint，随后使用独立MMKE-entity eval数据完整评测954条；逐层`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，launcher训练/评测阶段均为`rc=0`，未发现OOM、nonfinite、Traceback或watchdog超时。结果暂存于g09本地`/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000/qwen2.5-vl-3b`。该runner的模型级`full_eval_results.csv`/`selected_checkpoints_all_layers.tsv`会被每层调用覆盖，当前只保留队列最后一层L25；本表完整性与数值以18个逐层目录内的`selected_checkpoint.tsv`、`eval_full.done`和`results.json`交叉核验结果为准，不能用模型级汇总文件的单行误判为仅完成1层。

MMKE-entity InstructBLIP增量复核（更新至2026-07-25 21:29）：Slurm job `3044841`在g09/GPU1新增完成候选层`L0,L1,L3,L4,L5,L22,L23,L24,L25`。9层逐层均存在非空`selected_checkpoint.tsv`、`eval_full.done`、954条独立MMKE-entity eval完整结果和嵌套非空`results.json`，已补入下表；结果位于g09本地`/tmp/ph_teacher3/mmke_entity_job3044841_20260715_121700/instructblip-vicuna-7b`。L1曾因80GB显存不足中断，后从Epoch45 checkpoint恢复，采用CPU同步数据加载与activation checkpointing完成剩余训练及正式评测；完成标记未受损。L25从Epoch1训练至Epoch50/step15900，selected EMA为10.972824，随后完整评测954条，launcher eval `rc=0`、Average 47.578。至此候选并集19/19全部完成，无待补候选层。

EVQA-pilot500 SmolVLM/Qwen增量复核（2026-07-25 20:20）：Slurm job `3044208`在g09/GPU0的后续队列已完成SmolVLM候选补跑10层`L0,L1,L2,L3,L7,L8,L9,L10,L11,L20`和Qwen候选补跑14层`L0,L1,L2,L3,L11,L12,L14,L16,L17,L21,L22,L24,L30,L34`。24层逐层均存在`train.done`、非空`selected_checkpoint.tsv`和包含2,093条独立EVQA eval完整指标的`eval_full.done`，结果位于g09本地`/tmp/ph_teacher3/evqa_pilot500_smol_qwen_job3044208_20260723_202500`，已补入下表。该runner没有另写逐层`results.json`，完整指标直接保存在非空`eval_full.done` JSON中；因此按训练完成、selected checkpoint和正式评测三项交叉验收，不因缺少冗余副本文件误判为未完成。至此SmolVLM候选并集18/18、Qwen候选并集20/20均完成。

EVQA-pilot500 BLIP2增量复核（2026-07-30）：Slurm job `3044208`在g09/GPU0于Job取消前完成待补5层`L14,L1,L3,L4,L2`。5层均从头完成50 epoch训练流程并按minimum EMA loss选择checkpoint，随后使用独立`vqa_eval.json`正式评测2,093条；逐层`train.done`、非空`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`四项齐全，训练与评测均`rc=0`。结果位于g09本地`/tmp/ph_teacher3/evqa_pilot500_blip2_missing5_job3044208_20260728`。至此BLIP2候选并集15/15层均已完整训练和评测；Job后续于2026-07-29 15:25取消不影响此前生成的完成结果。

三数据集全量增量复核（2026-07-31 08:53）：以本文件上次修改时间2026-07-30 14:10:15为界，扫描g09共享正式结果根目录及`/tmp/ph_teacher3`现存实验目录，之后新生成且同时具备非空`selected_checkpoint.tsv`、`train.done`、对应独立评测完整指标、非空`eval_full.done`和非空`results.json`的结果只有MMKE-visual / MiniGPT-4候选层`L0,L1,L2,L3,L29`共5层。5层均在job 3044841/GPU1完成50 epoch训练流程；原runner选点记录缺陷于2026-07-30 14:14修复，随后依次完成293条MMKE-visual正式评测，结果位于g09本地`/tmp/ph_teacher3/mmke_visual_minigpt_llava_job3044841_20260728/minigpt-4-vicuna-7b`。EVQA-pilot500与MMKE-entity没有发现服务器已完整评测但未回填的新层。job 3117562/GPU0的MMKE-visual LLaVA L0在本次快照时仍处于Epoch 32训练，尚无selected/eval双标记，不计入完成。

MMKE-visual LLaVA逐层增量复核（2026-08-01 20:04）：Slurm job `3117562`在g09/GPU0新增完成L0、L1。两层均完成50 epoch训练流程并按minimum finite EMA选择checkpoint，随后使用独立MMKE-visual eval数据完整评测293条；逐层`train.done`、非空`selected_checkpoint.tsv`、包含六项指标的非空`eval_full.done`和评测后清理标记齐全。L0 selected为Epoch40/step4280/EMA 0.314945，Average 75.158；L1 selected为Epoch47/step5029/EMA 0.302343，Average 75.640。评测后已分别清理51/52个非selected checkpoint及可重建cache，selected未删除；服务器结果目录为`/tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730/llava-v1.5-7b`，完成标记和结构化指标已同步到本地`server_results/live_backfill/job3117562/mmke-visual/llava-v1.5-7b`。

Ours主公式补层队列增量复核（2026-08-02 09:23）：Slurm job `3126082`已完成MMKE-visual/SmolVLM L2、MMKE-entity/BLIP2 L1和MMKE-entity/PaliGemma L4。三层分别使用对应独立eval数据完整评测293/954/954条，均有非空`selected_checkpoint.tsv`、`train.done`和`eval_full.done`。SmolVLM L2 selected为Epoch46/EMA 0.411423，Average 70.522；BLIP2 L1 selected为Epoch11/EMA 5.990400，Average 72.504；PaliGemma主配置L4 selected为Epoch2/EMA 0.882321，Average 96.136。每层评测后均删除51个非selected checkpoint并保留唯一selected；结构化结果同步到本地`server_results/live_backfill/job3126082`。同队列MiniGPT-4 L9首次尝试在加载数据处理模型时CUDA OOM，当时无selected/eval并被跳过；此后已独占GPU从头重跑成功，最终完成状态与指标以紧随其后的2026-08-10恢复复核为准。

g09节点故障后恢复复核（2026-08-10 18:03）：g09于2026-08-06 01:11发生`NODE_FAIL`，job 3117562与3126082被Slurm重排到g07后只恢复Jupyter服务，实验launcher没有自动续跑。重新将空闲的job 3126082调度回g09取得只读权限后，确认原`/tmp`结果仍完整。MMKE-visual/LLaVA新增核验完成L2、L7、L8、L9、L12，连同先前已回填的L0、L1共7层；MMKE-visual/MiniGPT-4的主公式补层L9、L10、L11也已完成。10层逐层均具备非空`train.done`、`selected_checkpoint.tsv`、293条独立eval的`eval_full.done`和非空`results.json`。MiniGPT-4 L9先前OOM记录仅属于第一次失败尝试，随后独占GPU从头重跑成功，最终selected为Epoch49/step5243/EMA 0.257039、Average 76.582；L10为Epoch36/step3852/EMA 0.260045、Average 76.630；L11为Epoch39/step4173/EMA 0.272469、Average 76.830。完整关键产物及L13中断恢复现场已从g09复制到login01 `/var/tmp/ph_teacher3/recovered_g09_nodefail_20260810`（合计5.0 GiB），checksum dry-run差异为0；本地保留完整结构化压缩原件`server_results/live_backfill/recovered_g09_nodefail_20260810/structured_results.tar.gz`及短路径分析副本`server_results/g09r`。本次仅恢复、核验和同步，未启动新训练或删除原数据。

正式Top-3逐层即时回填（2026-08-11）：新增验收MMKE-visual/LLaVA L15、MMKE-visual/PaliGemma主配置L4、EVQA-pilot500/PaliGemma主配置L3。三层均同时具备非空`train.done`、`selected_checkpoint.tsv`、独立正式评测`eval_full.done`和非空`results.json`。LLaVA L15 selected为Epoch40/step4280/EMA 0.231111，293条评测Average 75.752；MMKE-visual PaliGemma L4 selected为Epoch39/step4173/EMA 0.330234，293条评测Average 99.026；EVQA PaliGemma L3 selected为Epoch38/step9500/EMA 0.531071，2,093条评测Average 85.720。结构化产物同步到本地`server_results/live_backfill/job3126082/mmke-visual/llava-v1.5-7b/layer_15`及`server_results/live_backfill/job3117562`对应数据集目录。自本条起，每次新候选层完成正式评测后立即执行同样的服务器双标记核验、结构化产物同步和本表逐层/计数更新，不等待整队列结束。

正式Top-3 LLaVA增量回填（2026-08-31 16:39 CST）：服务器共享盘新增核验EVQA-pilot500/LLaVA L6,L7,L14,L15,L16与MMKE-entity/LLaVA L14,L15,L16共8层。各层均具有非空`train.done`、`selected_checkpoint.tsv`、对应独立正式评测`eval_full.done`、非空`results.json`和`SYNC_VERIFIED`。EVQA使用独立`vqa_eval.json`评测2,093条，MMKE-entity使用独立entity eval评测954条；没有使用训练集评测。EVQA L15,L16此前已进入完成计数但缺少第4节详细结果行，本次一并补齐；本轮相对2026-08-24快照实际新增6个Top-3完成项。当前替代Job 3178538训练EVQA L5，替代Job 3178423训练MMKE-entity L28，两层均未完成正式评测，不提前回填。

正式Top-3 LLaVA增量回填（2026-09-13 18:02 CST）：服务器新增验收7层。Job 3178538完成EVQA-pilot500/LLaVA L5,L24,L25，均使用独立`vqa_eval.json`完整评测2,093条；Average依次为70.094、62.418、60.888。Job 3178423完成MMKE-entity/LLaVA L28,L27,L26,L23，均使用独立MMKE-entity eval完整评测954条；Average依次为74.742、75.148、75.144、75.540。7层逐层均具有非空`train.done`、`selected_checkpoint.tsv`、`eval_full.done`和非空`results.json`，未使用训练集评测。L5、L24及4个MMKE-entity层已经同步共享盘；EVQA L25当前完整产物仍位于g08节点`/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812/evqa-pilot500/llava-v1.5-7b/layer_25`，本表按服务器真实完整结果回填，但保留`LOCAL_TMP_PENDING_SHARED_SYNC`标记，不能把本地节点副本误称为持久归档。当前EVQA L0仍在训练；MMKE-entity L22已训练完成但尚无`eval_full.done`，两层均不计完成。

L25共享归档与临时副本清理（2026-09-15）：EVQA-pilot500/LLaVA L25已从g08 `/tmp`归档到`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065/evqa-pilot500/llava-v1.5-7b/layer_25`。重新核验2,093条独立正式评测、selected Epoch50/step12500/EMA 0.3291842153238946及Average 60.888；checkpoint SHA-256为`1d68657620140b5c3c4ecf3cdf618b9b23d7b6d5b1a170ec902ab52554743871`。归档保留selected实体、完整结果、配置、训练/评测日志和来源记录，三个运行标记中的层目录路径已改为共享路径，并写入`SYNC_VERIFIED`。按用户明确授权，在归档与无活动引用核验后删除原L25层目录、可重建缓存和两份L25独立日志，共约23.08 GiB磁盘空间；L0正在训练的目录及缓存保留。证据见`server_results/storage_audits/20260915_l25_archive`。本次只改变归档状态，完成层数和历史指标不变。

#### EVQA-pilot500

完成层数：`blip2-opt-2.7b` 20个唯一完成层、其中候选并集15/15层（逐层结果见4.1）；`instructblip-vicuna-7b` 3 层；`minigpt-4-vicuna-7b` 9 层；`llava-v1.5-7b` 表内13个唯一完成层，其中正式Top-3并集11/15层；`qwen2.5-vl-3b` 表内24层、其中历史冻结候选并集20/20层；`paligemma-3b` 14 个唯一完成层（主配置共14层，stable完成7层且均与主配置层重合）；`smolvlm-1.7b` 表内20层、其中历史冻结候选并集18/18层。新增的Qwen L15与SmolVLM L5均为`CMA-ModelPred` Top-3补层并已正式评测、归档共享盘。LLaVA新增L5、L24、L25；L25于2026-09-15完成共享归档、SHA-256核验和对应`/tmp`副本清理，历史指标与完成层数不变。

PaliGemma stable L4/L6已于2026-07-19完成补跑并生成双标记；stable目前仅L0没有`selected_checkpoint.tsv`、`eval_full.done`或完整评测结果，且主配置和stable下均不收敛。job 3044208的stable 7层与主配置新增7层均使用`vqa_eval.json`完整评测2,093条；表内按主配置、stable分组并在组内按层号升序排列。

| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| instructblip-vicuna-7b | L26 | 50 | 0.202061 | 0.881081 | 2093 | 29.65 | 28.92 | 27.94 | 100.00 | 70.70 | 51.44 | TRAIN_DONE |
| instructblip-vicuna-7b | L27 | 36 | 0.274748 | 0.888490 | 2093 | 29.64 | 28.66 | 28.71 | 100.00 | 74.34 | 52.27 | TRAIN_DONE |
| instructblip-vicuna-7b | L28 | 49 | 1.700526 | 1.100682 | 2093 | 29.86 | 28.72 | 28.78 | 100.00 | 79.00 | 53.27 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L16 | 50 | 0.314161 | 0.297508 | 2093 | 49.34 | 46.11 | 46.47 | 100.00 | 82.77 | 64.94 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L17 | 50 | 0.351717 | 0.299282 | 2093 | 47.77 | 46.10 | 45.82 | 100.00 | 79.85 | 63.91 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L18 | 44 | 0.305323 | 0.302507 | 2093 | 40.16 | 37.37 | 38.18 | 100.00 | 82.09 | 59.56 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L24 | 45 | 0.289782 | 0.297207 | 2093 | 39.76 | 33.96 | 37.35 | 100.00 | 77.44 | 57.70 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L25 | 36 | 0.283050 | 0.298860 | 2093 | 40.09 | 37.73 | 37.59 | 100.00 | 76.92 | 58.47 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L26 | 43 | 0.306680 | 0.374355 | 2093 | 39.33 | 34.25 | 36.79 | 100.00 | 75.97 | 57.27 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L28 | 34 | 0.372540 | 0.349210 | 2093 | 39.42 | 36.54 | 37.36 | 100.00 | 78.49 | 58.36 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L30 | 48 | 0.461325 | 0.481391 | 2093 | 41.56 | 38.68 | 39.48 | 100.00 | 69.49 | 57.84 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L31 | 14 | 8.763226 | 10.222642 | 2093 | 23.88 | 24.05 | 25.44 | 100.00 | 100.00 | 54.67 | TRAIN_DONE |
| llava-v1.5-7b | L0 | 26 | 0.486695 | 0.489312 | 2093 | 45.90 | 40.34 | 41.86 | 100.00 | 74.34 | 60.488 | TRAIN_DONE_EVAL_DONE_JOB3178538_VERIFIED_20260921 |
| llava-v1.5-7b | L1 | 50 | 0.459376 | 0.478102 | 2093 | 43.28 | 37.56 | 40.29 | 100.00 | 70.75 | 58.376 | TRAIN_DONE_EVAL_DONE_JOB3178538_VERIFIED_20260921 |
| llava-v1.5-7b | L5 | 30 | 0.429168 | 0.437470 | 2093 | 60.31 | 55.48 | 56.61 | 100.00 | 78.07 | 70.094 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178538 |
| llava-v1.5-7b | L6 | 50 | 0.255764 | 0.419622 | 2093 | 58.35 | 54.30 | 57.43 | 100.00 | 72.90 | 68.596 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| llava-v1.5-7b | L7 | 31 | 0.418494 | 0.478424 | 2093 | 42.91 | 36.99 | 40.64 | 100.00 | 68.55 | 57.818 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| llava-v1.5-7b | L14 | 43 | 0.350849 | 0.365037 | 2093 | 42.87 | 37.36 | 40.65 | 100.00 | 77.10 | 59.596 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| llava-v1.5-7b | L15 | 37 | 0.309543 | 0.366532 | 2093 | 44.52 | 39.02 | 40.63 | 100.00 | 78.98 | 60.630 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| llava-v1.5-7b | L16 | 48 | 0.436350 | 0.350793 | 2093 | 50.40 | 45.63 | 47.45 | 100.00 | 81.11 | 64.918 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| llava-v1.5-7b | L24 | 41 | 0.278317 | 0.351265 | 2093 | 52.26 | 44.18 | 42.27 | 100.00 | 73.38 | 62.418 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178538 |
| llava-v1.5-7b | L25 | 50 | 0.358062 | 0.329184 | 2093 | 50.28 | 44.06 | 41.17 | 100.00 | 68.93 | 60.888 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178538_TMP_CLEANED_20260915 |
| llava-v1.5-7b | L26 | 43 | 0.269856 | 0.355572 | 2093 | 51.51 | 43.55 | 42.16 | 100.00 | 77.72 | 62.99 | TRAIN_DONE |
| llava-v1.5-7b | L27 | 50 | 0.311770 | 0.367348 | 2093 | 52.84 | 44.73 | 41.45 | 100.00 | 73.17 | 62.44 | TRAIN_DONE |
| llava-v1.5-7b | L28 | 47 | 0.462426 | 0.498747 | 2093 | 50.13 | 43.50 | 41.14 | 100.00 | 69.48 | 60.85 | TRAIN_DONE |
| llava-v1.5-7b | L30 | 46 | 0.304285 | 0.531518 | 2093 | 41.93 | 37.89 | 35.70 | 100.00 | 70.70 | 57.24 | TRAIN_DONE |
| llava-v1.5-7b | L31 | 32 | 12.569068 | 9.569223 | 2093 | 32.21 | 30.16 | 28.01 | 100.00 | 100.00 | 58.08 | TRAIN_DONE |
| qwen2.5-vl-3b | L0 | 50 | 0.388003 | 0.443953 | 2093 | 53.71 | 43.50 | 34.56 | 100.00 | 82.68 | 62.89 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L1 | 41 | 0.409356 | 0.454254 | 2093 | 53.67 | 42.77 | 34.98 | 100.00 | 75.90 | 61.46 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L2 | 42 | 0.378063 | 0.448366 | 2093 | 53.64 | 45.58 | 36.81 | 100.00 | 75.24 | 62.25 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L3 | 49 | 0.411333 | 0.434602 | 2093 | 53.03 | 43.57 | 34.87 | 100.00 | 76.49 | 61.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L11 | 41 | 0.450617 | 0.448930 | 2093 | 53.17 | 43.40 | 35.12 | 100.00 | 77.48 | 61.83 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L12 | 39 | 0.416423 | 0.436754 | 2093 | 54.69 | 44.29 | 35.21 | 100.00 | 79.14 | 62.67 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L14 | 43 | 0.435669 | 0.420537 | 2093 | 54.34 | 44.45 | 35.20 | 100.00 | 82.94 | 63.39 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L15 | 49 | 0.459994 | 0.405599 | 2093 | 52.84 | 42.30 | 35.61 | 100.00 | 81.23 | 62.396 | TRAIN_DONE_CMA_MODELPRED_TOP3_BACKFILL_SHARED_JOB3178423 |
| qwen2.5-vl-3b | L16 | 49 | 0.443011 | 0.411539 | 2093 | 52.90 | 41.96 | 36.70 | 100.00 | 82.23 | 62.76 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L17 | 45 | 0.369272 | 0.384334 | 2093 | 53.21 | 42.57 | 34.62 | 100.00 | 82.62 | 62.60 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L18 | 49 | 0.444120 | 0.399728 | 2093 | 53.09 | 44.11 | 37.70 | 100.00 | 82.87 | 63.55 | TRAIN_DONE |
| qwen2.5-vl-3b | L19 | 41 | 0.417306 | 0.385106 | 2093 | 53.54 | 43.09 | 35.50 | 100.00 | 83.90 | 63.21 | TRAIN_DONE |
| qwen2.5-vl-3b | L20 | 48 | 0.343881 | 0.375257 | 2093 | 52.62 | 41.40 | 33.99 | 100.00 | 82.55 | 62.11 | TRAIN_DONE |
| qwen2.5-vl-3b | L21 | 49 | 0.444941 | 0.365603 | 2093 | 53.83 | 43.82 | 36.61 | 100.00 | 84.45 | 63.74 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L22 | 50 | 0.413212 | 0.390550 | 2093 | 54.06 | 43.14 | 35.30 | 100.00 | 81.58 | 62.82 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L24 | 47 | 0.328337 | 0.385822 | 2093 | 52.54 | 43.06 | 35.30 | 100.00 | 83.06 | 62.79 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L26 | 48 | 0.407629 | 0.382820 | 2093 | 52.76 | 42.32 | 35.42 | 100.00 | 81.15 | 62.33 | TRAIN_DONE |
| qwen2.5-vl-3b | L27 | 35 | 0.303852 | 0.368658 | 2093 | 52.34 | 41.68 | 33.11 | 100.00 | 82.59 | 61.94 | TRAIN_DONE |
| qwen2.5-vl-3b | L28 | 50 | 0.374178 | 0.364763 | 2093 | 53.48 | 43.14 | 35.20 | 100.00 | 80.81 | 62.53 | TRAIN_DONE |
| qwen2.5-vl-3b | L29 | 49 | 0.396721 | 0.371691 | 2093 | 53.43 | 43.60 | 34.39 | 100.00 | 80.43 | 62.37 | TRAIN_DONE |
| qwen2.5-vl-3b | L30 | 49 | 0.402044 | 0.378223 | 2093 | 53.30 | 42.72 | 34.77 | 100.00 | 81.81 | 62.52 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L31 | 49 | 0.233540 | 0.360590 | 2093 | 52.68 | 42.05 | 35.47 | 100.00 | 85.06 | 63.05 | TRAIN_DONE |
| qwen2.5-vl-3b | L34 | 42 | 0.436983 | 0.584563 | 2093 | 53.15 | 42.20 | 33.65 | 100.00 | 84.86 | 62.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L35 | 49 | 8.960615 | 7.367229 | 2093 | 49.91 | 37.43 | 22.23 | 100.00 | 100.00 | 61.91 | TRAIN_DONE |
| paligemma-3b | L0 | 2 | 3187.056885 | 3209.824510 | 2093 | 0.16 | 0.18 | 0.16 | 100.00 | 76.96 | 35.492 | EVAL_DONE_NONCONVERGENT_DIAGNOSTIC_EPOCH2_TRAIN_INCOMPLETE_JOB3178538 |
| paligemma-3b | L1 | 14 | 13.376622 | 14.049339 | 2093 | 8.24 | 13.07 | 8.79 | 100.00 | 63.99 | 38.82 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L3 | 38 | 0.605178 | 0.531071 | 2093 | 85.63 | 85.86 | 89.21 | 100.00 | 67.90 | 85.720 | TRAIN_DONE_MAIN_FORMAL_TOP3_JOB3117562 |
| paligemma-3b | L4 | 38 | 7.798694 | 6.942612 | 2093 | 74.08 | 76.08 | 74.69 | 100.00 | 30.78 | 71.13 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L5 | 2 | 2.871534 | 4.631819 | 2093 | 85.30 | 83.96 | 86.80 | 100.00 | 34.78 | 78.17 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L6 | 31 | 3.886672 | 5.983205 | 2093 | 58.14 | 64.42 | 67.89 | 100.00 | 42.92 | 66.67 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L7 | 10 | 3.521098 | 4.525994 | 2093 | 82.02 | 80.30 | 84.32 | 100.00 | 31.60 | 75.65 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L8 | 3 | 4.863270 | 3.294556 | 2093 | 91.11 | 91.37 | 93.32 | 100.00 | 29.18 | 81.00 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L9 | 1 | 17.538765 | 20.548170 | 2093 | 0.54 | 0.81 | 0.45 | 100.00 | 78.98 | 36.16 | TRAIN_RECOVERED_FROM_STALL_MAIN |
| paligemma-3b | L10 | 1 | 6.230244 | 9.293444 | 2093 | 77.44 | 82.52 | 79.77 | 100.00 | 12.85 | 70.52 | TRAIN_DONE_MAIN |
| paligemma-3b | L11 | 2 | 2.080458 | 3.296938 | 2093 | 87.13 | 87.76 | 88.63 | 100.00 | 41.44 | 80.99 | TRAIN_DONE_MAIN |
| paligemma-3b | L12 | 1 | 4.603746 | 5.001783 | 2093 | 84.51 | 85.98 | 85.00 | 100.00 | 24.43 | 75.98 | TRAIN_DONE_MAIN |
| paligemma-3b | L14 | 1 | 14.575245 | -1369.521638 | 2093 | 5.59 | 9.06 | 4.75 | 100.00 | 40.89 | 32.06 | TRAIN_DONE_MAIN_NUMERIC_ANOMALY |
| paligemma-3b | L15 | 25 | 22.580488 | 31.500783 | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | TRAIN_DONE_MAIN |
| paligemma-3b | L17 | 2 | 30.357973 | 30.934000 | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L1 | 46 | 0.945888 | 1.149873 | 2093 | 77.65 | 77.27 | 93.93 | 100.00 | 56.47 | 81.06 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L4 | 50 | 0.591566 | 0.491418 | 2093 | 66.09 | 64.75 | 85.62 | 100.00 | 77.50 | 78.79 | TRAIN_DONE_STABLE_RETRY_NUMERIC_GUARD_NONFINITE_SKIP16_JOB3044208 |
| paligemma-3b | L5 | 46 | 0.596487 | 0.554996 | 2093 | 77.02 | 77.96 | 89.71 | 100.00 | 69.93 | 82.92 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L6 | 50 | 0.423632 | 0.468850 | 2093 | 69.94 | 69.13 | 89.83 | 100.00 | 68.92 | 79.56 | TRAIN_DONE_STABLE_RETRY_BUFFER1_JOB3044208 |
| paligemma-3b | L7 | 43 | 0.973857 | 0.609388 | 2093 | 82.25 | 81.34 | 91.16 | 100.00 | 67.18 | 84.39 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L8 | 38 | 0.801614 | 0.593724 | 2093 | 78.95 | 76.17 | 93.02 | 100.00 | 65.09 | 82.65 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L17 | 23 | 26.938894 | 29.851553 | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | TRAIN_DONE_STABLE_JOB3044208 |
| smolvlm-1.7b | L0 | 50 | 0.445026 | 0.452992 | 2093 | 64.02 | 59.53 | 57.19 | 100.00 | 69.10 | 69.97 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L1 | 47 | 0.449670 | 0.456147 | 2093 | 46.20 | 40.21 | 35.59 | 100.00 | 71.86 | 58.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L2 | 48 | 0.429149 | 0.437729 | 2093 | 55.62 | 51.14 | 47.70 | 100.00 | 67.59 | 64.41 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L3 | 45 | 0.445100 | 0.442415 | 2093 | 58.43 | 52.94 | 49.94 | 100.00 | 71.47 | 66.56 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L5 | 42 | 0.402913 | 0.428878 | 2093 | 56.18 | 50.60 | 45.96 | 100.00 | 74.07 | 65.362 | TRAIN_DONE_CMA_MODELPRED_TOP3_BACKFILL_SHARED_JOB3178423 |
| smolvlm-1.7b | L7 | 45 | 0.398488 | 0.419556 | 2093 | 60.39 | 55.03 | 51.65 | 100.00 | 75.17 | 68.45 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L8 | 48 | 0.401016 | 0.404693 | 2093 | 53.38 | 48.67 | 43.40 | 100.00 | 74.44 | 63.98 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L9 | 50 | 0.390892 | 0.384298 | 2093 | 58.69 | 54.30 | 50.42 | 100.00 | 76.89 | 68.06 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L10 | 48 | 0.404036 | 0.384991 | 2093 | 61.90 | 58.08 | 53.55 | 100.00 | 75.51 | 69.81 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L11 | 46 | 0.406657 | 0.396586 | 2093 | 57.70 | 52.14 | 47.72 | 100.00 | 78.63 | 67.24 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L12 | 42 | 0.376879 | 0.402297 | 2093 | 49.12 | 42.07 | 38.85 | 100.00 | 79.60 | 61.93 | TRAIN_DONE |
| smolvlm-1.7b | L13 | 50 | 0.364526 | 0.381850 | 2093 | 44.80 | 40.22 | 34.16 | 100.00 | 78.07 | 59.45 | TRAIN_DONE |
| smolvlm-1.7b | L14 | 50 | 0.405853 | 0.384188 | 2093 | 58.45 | 52.68 | 49.76 | 100.00 | 80.21 | 68.22 | TRAIN_DONE |
| smolvlm-1.7b | L15 | 46 | 0.347375 | 0.362945 | 2093 | 45.80 | 39.49 | 34.58 | 100.00 | 78.83 | 59.74 | TRAIN_DONE |
| smolvlm-1.7b | L16 | 41 | 0.373067 | 0.409362 | 2093 | 46.25 | 39.29 | 33.88 | 100.00 | 75.06 | 58.90 | TRAIN_DONE |
| smolvlm-1.7b | L17 | 46 | 0.357996 | 0.383906 | 2093 | 44.36 | 39.14 | 33.17 | 100.00 | 77.57 | 58.85 | TRAIN_DONE |
| smolvlm-1.7b | L19 | 40 | 0.380004 | 0.381024 | 2093 | 45.04 | 38.91 | 33.38 | 100.00 | 69.21 | 57.31 | TRAIN_DONE |
| smolvlm-1.7b | L20 | 48 | 0.382679 | 0.383377 | 2093 | 45.09 | 39.20 | 33.92 | 100.00 | 67.53 | 57.15 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L21 | 47 | 0.500128 | 0.415271 | 2093 | 43.91 | 37.52 | 33.37 | 100.00 | 67.03 | 56.37 | TRAIN_DONE |
| smolvlm-1.7b | L22 | 50 | 0.427672 | 0.488335 | 2093 | 42.44 | 36.70 | 31.77 | 100.00 | 68.45 | 55.87 | TRAIN_DONE |

#### MMKE-visual

**2026-09-26 服务器复核与 main 恢复评测：** main 原运行的 L1、L2、L6、L7、L13 已有完整50轮及293条评测，本次补齐漏记；L3、L5 原训练发生非有限梯度并被停滞监控终止，现已直接评测原 checkpoint，分别为30.540、62.544。当前 main 共16层有实际评测，其中13层训练完成50轮，L0/L3/L5为训练未完成的恢复评测。“已评测”不等于“已收敛”或“完成50轮”。stable 单列保留，不再以 stable 高分替换 main 低分；先前其他章节的覆盖统计属于历史快照，不据此自动增加完整50轮可比组数。详情见 `outputs/paligemma_visual_server_audit_20260926/PaliGemma_main停训原因与直接评测结果.md`。

完成层数：`blip2-opt-2.7b` 19 层；`instructblip-vicuna-7b` 21 层；`minigpt-4-vicuna-7b` 21层，其中原候选并集16/16层已完成，另有Ours主公式补层L9、L10、L11于job 3126082完成；`llava-v1.5-7b` 9层（L0、L1、L2、L7、L8、L9、L12、L15、L28），其中3.4.2原待补15层已完成8层、剩余7层；`qwen2.5-vl-3b` 21 层；`paligemma-3b` main有16个已评测层，其中13层完整50轮、L0/L3/L5为未完成训练的恢复评测；stable另列，不能混成一个完成数；`smolvlm-1.7b` 21层。SmolVLM新增L5为`CMA-ModelPred` Top-3补层，已完成293条独立MMKE-visual eval并归档共享盘。`blip2-opt-2.7b` 的 `L29`、`instructblip-vicuna-7b` 的 `L30,L31`、MiniGPT-4的`L17,L18`，以及SmolVLM已完成但不在3.2候选并集内的`L13,L19,L20,L21`，可用于oracle/full-sweep对照；做当前正式候选层统计时按3.4.5重算并集筛选。不得再沿用2026-08-01的旧快照把LLaVA L2记为训练中。

补充说明：`paligemma-3b` 原始 run 的 7 层结果保留不动；其后追加 2026-07-13 的 PaliGemma-stable 补跑结果，来源为服务器目录 `paligemma_stable_mmke_visual_top3_union_20260713_1120`。stable 补跑中 `L8` 训练到 epoch 13 后中断，已保护现场并使用 epoch 13 checkpoint 手动完成 full eval，因此状态单独标记为 `TRAIN_DONE_MANUAL_EPOCH13`。

2026-07-14 至 2026-07-15 在 Slurm job `3044208`（g09/GPU0）继续完成 PaliGemma-stable MMKE-visual 目标层 `L7,L13,L0,L5,L6,L3,L2,L1`，结果目录为 `paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b`。其中 `L7,L13,L5,L6,L3,L2,L1` 均存在非空 `selected_checkpoint.tsv` 和 `eval_full.done`，full eval 使用独立 MMKE-visual eval JSON（293 samples），计为完成。`L0` 使用 `paligemma-3b-stable-l0.yaml` 训练至 epoch 26 的 212/214 step，但 EMA loss 长期约为 3.4k--3.5k，且反复出现整层 `PALIGEMMA_STABLE_SKIP_NONFINITE_STEP`，判定为未收敛；最后一次保存又触发 `PytorchStreamWriter file write failed / unexpected pos`，未生成 selected checkpoint，未运行 eval，状态记录为 `FAILED_NONCONVERGENT_CKPT_WRITE_ERROR_NO_EVAL`。目录根部的 `ALL_DONE` 由单层 runner 写入，不能作为 8 层完成依据；本批实际为 7/8 完成。

PaliGemma 表项版本划分（按下表中的状态字段识别，不依赖易变化的文件行号）：

- `TRAIN_DONE_MAIN`：主实验配置 `configs/vead/paligemma-3b.yaml`，对应原始 run 的 `L8,L9,L10,L11,L12,L14,L17`。
- `TRAIN_DONE_MANUAL_EPOCH13` / `TRAIN_DONE_STABLE`：2026-07-13 stable 配置补跑，对应 `L8,L9,L10,L11,L12,L14,L17`；其中 L8 为 epoch 13 checkpoint 手动 full eval。
- `TRAIN_DONE_STABLE_JOB3044208`：job 3044208 stable 配置补跑，对应 `L1,L2,L3,L5,L6,L7,L13`，使用 `configs/vead/paligemma-3b-stable.yaml`。
- `FAILED_STABLE_L0_NONCONVERGENT_CKPT_WRITE_ERROR_NO_EVAL`：job 3044208 的 L0 stable 专用配置 `configs/vead/paligemma-3b-stable-l0.yaml`；未收敛且未评测，不属于主实验版本，也不计入完成结果。

PaliGemma 当前记录规则（2026-09-26，按用户要求更新）：保留原 main 训练轨迹与实际评测分数。出现数值异常或中断时，只要原 checkpoint 参数有限且可读取，即可按原评测协议直接评测，并明确标注训练预算完成情况；不能把低分、失败或中断静默删除，也不以 stable 分数替换。历史 stable 作为单独配方结果保留。所有定位公式必须复用同一个固定层—结果映射。完整50轮分析与包含失败/中断恢复结果的实际运行分析分别统计。

| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| blip2-opt-2.7b | L0 | 50 | 1.835244 | 2.004923 | 293 | 53.13 | 53.14 | 53.20 | 100.00 | 52.38 | 62.37 | TRAIN_DONE |
| blip2-opt-2.7b | L1 | 50 | 0.516416 | 0.520349 | 293 | 52.09 | 51.80 | 51.97 | 100.00 | 92.60 | 69.69 | TRAIN_DONE |
| blip2-opt-2.7b | L2 | 44 | 0.813470 | 1.107170 | 293 | 52.04 | 51.91 | 51.58 | 100.00 | 93.80 | 69.87 | TRAIN_DONE |
| blip2-opt-2.7b | L3 | 50 | 0.584310 | 0.958273 | 293 | 52.01 | 51.65 | 52.37 | 100.00 | 87.68 | 68.74 | TRAIN_DONE |
| blip2-opt-2.7b | L4 | 49 | 0.491591 | 0.601247 | 293 | 51.78 | 51.72 | 51.60 | 100.00 | 90.85 | 69.19 | TRAIN_DONE |
| blip2-opt-2.7b | L14 | 50 | 0.476014 | 0.465106 | 293 | 51.32 | 51.11 | 50.76 | 100.00 | 97.16 | 70.07 | TRAIN_DONE |
| blip2-opt-2.7b | L15 | 47 | 0.360871 | 0.334112 | 293 | 53.41 | 53.31 | 53.20 | 100.00 | 97.03 | 71.39 | TRAIN_DONE |
| blip2-opt-2.7b | L16 | 48 | 0.384157 | 0.416895 | 293 | 52.71 | 52.60 | 52.19 | 100.00 | 97.33 | 70.97 | TRAIN_DONE |
| blip2-opt-2.7b | L17 | 48 | 0.385966 | 0.438426 | 293 | 53.09 | 53.05 | 52.89 | 100.00 | 97.05 | 71.22 | TRAIN_DONE |
| blip2-opt-2.7b | L18 | 45 | 0.326844 | 0.400918 | 293 | 53.00 | 52.95 | 53.12 | 100.00 | 97.37 | 71.29 | TRAIN_DONE |
| blip2-opt-2.7b | L19 | 49 | 0.241281 | 0.346198 | 293 | 53.87 | 53.61 | 53.41 | 100.00 | 95.95 | 71.37 | TRAIN_DONE |
| blip2-opt-2.7b | L20 | 45 | 0.679693 | 0.413794 | 293 | 53.80 | 53.80 | 53.53 | 100.00 | 97.94 | 71.81 | TRAIN_DONE |
| blip2-opt-2.7b | L21 | 49 | 0.364866 | 0.352452 | 293 | 53.54 | 53.67 | 53.37 | 100.00 | 98.09 | 71.73 | TRAIN_DONE |
| blip2-opt-2.7b | L22 | 49 | 0.330121 | 0.370491 | 293 | 54.38 | 54.32 | 54.20 | 100.00 | 97.69 | 72.12 | TRAIN_DONE |
| blip2-opt-2.7b | L24 | 44 | 0.414978 | 0.417396 | 293 | 53.86 | 53.79 | 53.65 | 100.00 | 95.48 | 71.36 | TRAIN_DONE |
| blip2-opt-2.7b | L25 | 46 | 0.387067 | 0.575704 | 293 | 53.67 | 53.55 | 53.47 | 100.00 | 96.65 | 71.47 | TRAIN_DONE |
| blip2-opt-2.7b | L26 | 49 | 0.681283 | 0.788690 | 293 | 53.06 | 53.29 | 53.23 | 100.00 | 95.84 | 71.08 | TRAIN_DONE |
| blip2-opt-2.7b | L29 | 48 | 4.021954 | 2.907863 | 293 | 49.96 | 49.85 | 49.73 | 100.00 | 96.97 | 69.30 | TRAIN_DONE |
| blip2-opt-2.7b | L30 | 48 | 5.169809 | 5.331725 | 293 | 44.26 | 44.01 | 44.24 | 100.00 | 96.33 | 65.77 | TRAIN_DONE |
| instructblip-vicuna-7b | L0 | 50 | 0.171615 | 0.222510 | 293 | 52.26 | 52.42 | 52.17 | 100.00 | 99.62 | 71.29 | TRAIN_DONE |
| instructblip-vicuna-7b | L1 | 50 | 0.231107 | 0.292772 | 293 | 51.70 | 51.67 | 51.55 | 100.00 | 96.48 | 70.28 | TRAIN_DONE |
| instructblip-vicuna-7b | L2 | 46 | 6.189603 | 6.830468 | 293 | 18.67 | 16.65 | 18.50 | 100.00 | 99.57 | 50.68 | TRAIN_DONE |
| instructblip-vicuna-7b | L3 | 47 | 5.070473 | 6.227147 | 293 | 19.40 | 17.34 | 19.20 | 100.00 | 99.85 | 51.16 | TRAIN_DONE |
| instructblip-vicuna-7b | L4 | 49 | 7.357730 | 7.321517 | 293 | 17.38 | 15.28 | 17.58 | 100.00 | 99.05 | 49.86 | TRAIN_DONE |
| instructblip-vicuna-7b | L5 | 49 | 6.999227 | 7.345585 | 293 | 17.03 | 14.84 | 17.13 | 100.00 | 99.51 | 49.70 | TRAIN_DONE |
| instructblip-vicuna-7b | L14 | 50 | 5.457262 | 6.049061 | 293 | 17.34 | 15.97 | 17.24 | 100.00 | 99.57 | 50.02 | TRAIN_DONE |
| instructblip-vicuna-7b | L15 | 47 | 7.049882 | 6.446094 | 293 | 17.08 | 16.01 | 16.99 | 100.00 | 99.85 | 49.99 | TRAIN_DONE |
| instructblip-vicuna-7b | L16 | 48 | 8.969355 | 7.001298 | 293 | 18.08 | 17.11 | 17.96 | 100.00 | 99.63 | 50.56 | TRAIN_DONE |
| instructblip-vicuna-7b | L17 | 50 | 7.270292 | 6.931965 | 293 | 18.47 | 16.80 | 18.64 | 100.00 | 99.73 | 50.73 | TRAIN_DONE |
| instructblip-vicuna-7b | L18 | 50 | 6.697884 | 6.893876 | 293 | 18.08 | 16.55 | 18.22 | 100.00 | 99.60 | 50.49 | TRAIN_DONE |
| instructblip-vicuna-7b | L19 | 49 | 5.929656 | 5.769108 | 293 | 18.56 | 16.42 | 18.60 | 100.00 | 99.59 | 50.63 | TRAIN_DONE |
| instructblip-vicuna-7b | L22 | 46 | 6.008149 | 6.773030 | 293 | 17.87 | 16.80 | 17.62 | 100.00 | 100.00 | 50.46 | TRAIN_DONE |
| instructblip-vicuna-7b | L23 | 50 | 5.294744 | 6.377842 | 293 | 18.06 | 16.63 | 17.96 | 100.00 | 99.73 | 50.48 | TRAIN_DONE |
| instructblip-vicuna-7b | L24 | 47 | 6.654134 | 7.255629 | 293 | 18.21 | 16.78 | 18.19 | 100.00 | 99.76 | 50.59 | TRAIN_DONE |
| instructblip-vicuna-7b | L25 | 46 | 5.746799 | 6.995333 | 293 | 17.41 | 15.67 | 17.23 | 100.00 | 99.73 | 50.01 | TRAIN_DONE |
| instructblip-vicuna-7b | L26 | 49 | 6.737056 | 7.514501 | 293 | 17.55 | 15.30 | 17.37 | 100.00 | 99.63 | 49.97 | TRAIN_DONE |
| instructblip-vicuna-7b | L27 | 48 | 6.786605 | 7.596408 | 293 | 18.47 | 16.75 | 18.57 | 100.00 | 99.18 | 50.59 | TRAIN_DONE |
| instructblip-vicuna-7b | L28 | 49 | 5.810029 | 7.744205 | 293 | 17.32 | 15.62 | 17.06 | 100.00 | 99.83 | 49.97 | TRAIN_DONE |
| instructblip-vicuna-7b | L30 | 45 | 10.282062 | 11.521651 | 293 | 11.75 | 11.08 | 11.62 | 100.00 | 99.32 | 46.75 | TRAIN_DONE |
| instructblip-vicuna-7b | L31 | 28 | 36.477367 | 36.696703 | 293 | 0.04 | 0.04 | 0.04 | 100.00 | 100.00 | 40.02 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L0 | 50 | 0.269117 | 0.267466 | 293 | 59.95 | 60.02 | 60.14 | 100.00 | 98.95 | 75.812 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| minigpt-4-vicuna-7b | L1 | 50 | 0.272173 | 0.281973 | 293 | 60.32 | 60.32 | 60.55 | 100.00 | 97.93 | 75.824 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| minigpt-4-vicuna-7b | L2 | 41 | 0.253623 | 0.267989 | 293 | 60.35 | 60.40 | 60.64 | 100.00 | 98.93 | 76.064 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| minigpt-4-vicuna-7b | L3 | 36 | 0.254035 | 0.288644 | 293 | 61.41 | 61.60 | 61.07 | 100.00 | 99.09 | 76.634 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| minigpt-4-vicuna-7b | L5 | 35 | 0.258817 | 0.281105 | 293 | 62.09 | 62.04 | 61.86 | 100.00 | 98.73 | 76.94 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L8 | 49 | 0.265526 | 0.256176 | 293 | 61.75 | 61.62 | 61.68 | 100.00 | 97.91 | 76.59 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L9 | 49 | 0.247979 | 0.257039 | 293 | 61.34 | 61.27 | 61.41 | 100.00 | 98.89 | 76.582 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3126082 |
| minigpt-4-vicuna-7b | L10 | 36 | 0.247014 | 0.260045 | 293 | 61.51 | 61.48 | 61.42 | 100.00 | 98.74 | 76.630 | TRAIN_DONE_RECOVERED_SELECTION_G09_NODEFAIL_JOB3126082 |
| minigpt-4-vicuna-7b | L11 | 39 | 0.287227 | 0.272469 | 293 | 62.03 | 61.78 | 61.97 | 100.00 | 98.37 | 76.830 | TRAIN_DONE_RECOVERED_SELECTION_G09_NODEFAIL_JOB3126082 |
| minigpt-4-vicuna-7b | L14 | 50 | 0.234949 | 0.249512 | 293 | 61.07 | 60.94 | 60.84 | 100.00 | 98.88 | 76.35 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L15 | 50 | 0.242507 | 0.251438 | 293 | 60.39 | 60.22 | 60.11 | 100.00 | 98.64 | 75.87 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L16 | 33 | 0.238199 | 0.268302 | 293 | 61.01 | 60.87 | 60.75 | 100.00 | 97.86 | 76.10 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L17 | 49 | 0.249406 | 0.265122 | 293 | 59.81 | 59.86 | 59.90 | 100.00 | 97.14 | 75.34 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L18 | 46 | 0.269364 | 0.262238 | 293 | 59.33 | 59.18 | 59.41 | 100.00 | 98.00 | 75.18 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L24 | 49 | 0.502779 | 0.438395 | 293 | 57.99 | 57.94 | 58.05 | 100.00 | 97.30 | 74.26 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L25 | 50 | 0.759646 | 0.611862 | 293 | 57.89 | 57.73 | 57.74 | 100.00 | 98.25 | 74.32 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L26 | 49 | 0.676290 | 0.788584 | 293 | 57.32 | 56.97 | 57.30 | 100.00 | 98.06 | 73.93 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L27 | 43 | 0.908072 | 1.413074 | 293 | 57.88 | 57.60 | 57.52 | 100.00 | 97.97 | 74.19 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L28 | 45 | 1.148645 | 1.711778 | 293 | 57.96 | 57.92 | 57.85 | 100.00 | 98.46 | 74.44 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L29 | 48 | 3.022602 | 2.115868 | 293 | 56.55 | 56.18 | 56.37 | 100.00 | 97.23 | 73.266 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| minigpt-4-vicuna-7b | L31 | 43 | 6.683348 | 7.304613 | 293 | 47.21 | 46.58 | 46.99 | 100.00 | 100.00 | 68.16 | TRAIN_DONE |
| llava-v1.5-7b | L0 | 40 | 0.229806 | 0.314945 | 293 | 60.74 | 60.79 | 60.88 | 100.00 | 93.38 | 75.158 | TRAIN_DONE_LOCAL_TMP_JOB3117562 |
| llava-v1.5-7b | L1 | 47 | 0.268086 | 0.302343 | 293 | 61.27 | 61.21 | 61.56 | 100.00 | 94.16 | 75.640 | TRAIN_DONE_LOCAL_TMP_JOB3117562 |
| llava-v1.5-7b | L2 | 33 | 0.281384 | 0.305978 | 293 | 63.43 | 63.24 | 63.39 | 100.00 | 93.87 | 76.786 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| llava-v1.5-7b | L7 | 35 | 0.214817 | 0.286848 | 293 | 62.21 | 62.15 | 62.30 | 100.00 | 96.10 | 76.552 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| llava-v1.5-7b | L8 | 47 | 0.181363 | 0.260420 | 293 | 62.93 | 62.85 | 62.66 | 100.00 | 96.60 | 77.008 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| llava-v1.5-7b | L9 | 40 | 0.400646 | 0.281962 | 293 | 62.64 | 62.66 | 62.69 | 100.00 | 96.56 | 76.910 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| llava-v1.5-7b | L12 | 47 | 0.173525 | 0.243153 | 293 | 61.63 | 61.64 | 61.52 | 100.00 | 95.56 | 76.070 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| llava-v1.5-7b | L15 | 40 | 0.119042 | 0.231111 | 293 | 61.02 | 61.00 | 60.91 | 100.00 | 95.83 | 75.752 | TRAIN_DONE_FORMAL_TOP3_JOB3126082 |
| llava-v1.5-7b | L28 | 49 | 0.446779 | 0.996580 | 293 | 57.58 | 57.49 | 57.99 | 100.00 | 94.57 | 73.53 | TRAIN_DONE |
| qwen2.5-vl-3b | L0 | 45 | 0.470173 | 0.677373 | 293 | 52.74 | 52.90 | 52.28 | 100.00 | 94.20 | 70.42 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L1 | 47 | 1.164370 | 0.680025 | 293 | 51.09 | 51.08 | 51.24 | 100.00 | 94.01 | 69.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L2 | 43 | 0.670088 | 0.893235 | 293 | 51.75 | 51.64 | 51.72 | 100.00 | 94.52 | 69.93 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L6 | 45 | 0.499272 | 0.734185 | 293 | 52.38 | 52.01 | 51.85 | 100.00 | 94.51 | 70.15 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L7 | 49 | 0.474863 | 0.731563 | 293 | 52.59 | 52.39 | 52.38 | 100.00 | 94.97 | 70.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L8 | 47 | 0.389735 | 0.593588 | 293 | 52.58 | 52.64 | 52.33 | 100.00 | 96.67 | 70.84 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L9 | 50 | 0.394751 | 0.598401 | 293 | 51.68 | 51.27 | 51.61 | 100.00 | 92.83 | 69.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L11 | 48 | 0.539290 | 0.561360 | 293 | 53.34 | 53.13 | 53.01 | 100.00 | 95.51 | 71.00 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L12 | 47 | 0.458533 | 0.499579 | 293 | 52.61 | 52.22 | 52.87 | 100.00 | 97.30 | 71.00 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L13 | 48 | 0.461817 | 0.418149 | 293 | 51.51 | 51.34 | 52.22 | 100.00 | 96.89 | 70.39 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L14 | 43 | 0.517781 | 0.504366 | 293 | 52.10 | 51.90 | 51.96 | 100.00 | 93.12 | 69.82 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L16 | 49 | 0.419709 | 0.486438 | 293 | 51.80 | 51.51 | 51.76 | 100.00 | 93.99 | 69.81 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L17 | 49 | 0.335644 | 0.397961 | 293 | 51.16 | 51.10 | 51.51 | 100.00 | 94.25 | 69.60 | TRAIN_DONE_EXISTING_CKPT_EVAL_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L18 | 46 | 0.441055 | 0.438478 | 293 | 52.69 | 52.25 | 52.48 | 100.00 | 95.82 | 70.65 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L19 | 50 | 0.359075 | 0.417327 | 293 | 51.61 | 51.09 | 51.45 | 100.00 | 95.52 | 69.93 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L20 | 45 | 0.245531 | 0.482954 | 293 | 51.94 | 51.65 | 51.86 | 100.00 | 96.56 | 70.40 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L22 | 50 | 0.550950 | 0.494701 | 293 | 51.81 | 51.30 | 51.86 | 100.00 | 96.73 | 70.34 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L26 | 43 | 0.537117 | 0.583348 | 293 | 49.13 | 48.83 | 48.95 | 100.00 | 94.40 | 68.26 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L27 | 48 | 0.393821 | 0.756435 | 293 | 48.99 | 48.98 | 48.75 | 100.00 | 93.87 | 68.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L28 | 43 | 0.595793 | 1.006616 | 293 | 49.89 | 49.35 | 49.90 | 100.00 | 92.60 | 68.35 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L30 | 48 | 1.174112 | 1.430872 | 293 | 47.65 | 47.29 | 47.56 | 100.00 | 92.74 | 67.05 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| paligemma-3b | L1 | 9 | 28.518827 | 30.787377 | 293 | 0.09 | 0.08 | 0.10 | 100.00 | 97.95 | 39.644 | TRAIN_DONE_MAIN_BACKFILLED_20260926；完整50epoch，有历史非有限梯度记录 |
| paligemma-3b | L2 | 3 | 2.979825 | 1.682528 | 293 | 94.68 | 94.88 | 94.40 | 100.00 | 17.23 | 80.238 | TRAIN_DONE_MAIN_BACKFILLED_20260926；完整50epoch，有历史非有限梯度记录 |
| paligemma-3b | L3 | 7 | 21.378290 | 22.591008 | 293 | 16.41 | 16.53 | 16.69 | 100.00 | 3.07 | 30.540 | EVAL_DONE_INCOMPLETE_NUMERIC_INSTABILITY_MAIN_RECOVERED_20260926；已保存27轮，非完整50epoch |
| paligemma-3b | L5 | 1 | 8.847749 | 9.046796 | 293 | 55.51 | 55.68 | 56.14 | 100.00 | 45.39 | 62.544 | EVAL_DONE_INCOMPLETE_NUMERIC_INSTABILITY_MAIN_RECOVERED_20260926；已保存3轮，非完整50epoch |
| paligemma-3b | L6 | 2 | 0.841218 | 1.231970 | 293 | 95.38 | 95.42 | 95.31 | 100.00 | 91.33 | 95.488 | TRAIN_DONE_MAIN_BACKFILLED_20260926；完整50epoch，有历史非有限梯度记录 |
| paligemma-3b | L7 | 2 | 1.615333 | 1.543866 | 293 | 94.79 | 94.81 | 94.75 | 100.00 | 82.70 | 93.410 | TRAIN_DONE_MAIN_BACKFILLED_20260926；完整50epoch，有历史非有限梯度记录 |
| paligemma-3b | L13 | 19 | 18.990540 | 18.644390 | 293 | 0.25 | 0.25 | 0.28 | 100.00 | 99.43 | 40.042 | TRAIN_DONE_MAIN_BACKFILLED_20260926；完整50epoch，有历史非有限梯度记录 |
| paligemma-3b | L4 | 39 | 0.332606 | 0.330234 | 293 | 99.23 | 99.22 | 98.68 | 100.00 | 98.00 | 99.026 | TRAIN_DONE_MAIN_FORMAL_TOP3_JOB3117562 |
| paligemma-3b | L0 | 1 | 3465.718750 | 3508.007406 | 293 | 0.10 | 0.08 | 0.09 | 100.00 | 92.33 | 38.520 | EVAL_DONE_NONCONVERGENT_MAIN_RECOVERED_20260921；不收敛，lr=1e-4，非完整50epoch |
| paligemma-3b | L8 | 2 | 3.971717 | 2.536566 | 293 | 95.13 | 95.16 | 95.19 | 100.00 | 70.96 | 91.29 | TRAIN_DONE_MAIN |
| paligemma-3b | L9 | 6 | 0.444634 | 0.517213 | 293 | 98.79 | 98.83 | 98.69 | 100.00 | 94.16 | 98.09 | TRAIN_DONE_MAIN |
| paligemma-3b | L10 | 24 | 0.343096 | 0.348760 | 293 | 98.97 | 98.98 | 98.91 | 100.00 | 98.42 | 99.06 | TRAIN_DONE_MAIN |
| paligemma-3b | L11 | 7 | 0.579804 | 0.737678 | 293 | 96.10 | 96.05 | 95.71 | 100.00 | 97.49 | 97.07 | TRAIN_DONE_MAIN |
| paligemma-3b | L12 | 50 | 0.290716 | 0.401058 | 293 | 95.53 | 95.58 | 95.55 | 100.00 | 97.74 | 96.88 | TRAIN_DONE_MAIN |
| paligemma-3b | L14 | 1 | 17.459480 | -351.953961 | 293 | 0.90 | 1.01 | 0.88 | 100.00 | 92.34 | 39.03 | TRAIN_DONE_MAIN |
| paligemma-3b | L17 | 6 | 30.490068 | 30.831037 | 293 | 0.08 | 0.08 | 0.09 | 100.00 | 100.00 | 40.05 | TRAIN_DONE_MAIN |
| paligemma-3b | L0 | - | - | - | 0 | - | - | - | - | - | - | FAILED_STABLE_L0_NONCONVERGENT_CKPT_WRITE_ERROR_NO_EVAL |
| paligemma-3b | L0 | 25 | 3402.662842 | 3454.815660 | 293 | 0.09 | 0.09 | 0.10 | 100.00 | 76.93 | 35.442 | EVAL_DONE_NONCONVERGENT_STABLE_RECOVERED_20260921；不收敛，lr=1e-6，非完整50epoch |
| paligemma-3b | L1 | 49 | 0.334160 | 0.355574 | 293 | 97.76 | 97.70 | 96.65 | 100.00 | 98.39 | 98.10 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L2 | 44 | 0.346728 | 0.154633 | 293 | 99.34 | 99.35 | 97.65 | 100.00 | 96.00 | 98.47 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L3 | 46 | 0.342673 | 0.347433 | 293 | 97.33 | 97.26 | 96.68 | 100.00 | 98.23 | 97.90 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L5 | 45 | 0.351702 | 0.347726 | 293 | 98.91 | 98.89 | 97.91 | 100.00 | 97.20 | 98.58 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L6 | 47 | 0.334160 | 0.348006 | 293 | 97.49 | 97.56 | 96.67 | 100.00 | 98.12 | 97.97 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L7 | 49 | 0.354043 | 0.352879 | 293 | 98.54 | 98.45 | 98.17 | 100.00 | 96.84 | 98.40 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L8 | 13 | 0.498305 | 0.587410 | 293 | 96.90 | 96.93 | 96.43 | 100.00 | 94.33 | 96.92 | TRAIN_DONE_MANUAL_EPOCH13 |
| paligemma-3b | L9 | 50 | 0.351273 | 0.358913 | 293 | 98.50 | 98.47 | 98.23 | 100.00 | 96.39 | 98.32 | TRAIN_DONE_STABLE |
| paligemma-3b | L10 | 47 | 0.343897 | 0.354527 | 293 | 98.43 | 98.42 | 98.49 | 100.00 | 97.24 | 98.52 | TRAIN_DONE_STABLE |
| paligemma-3b | L11 | 50 | 0.404692 | 0.473600 | 293 | 96.34 | 96.21 | 96.33 | 100.00 | 96.85 | 97.15 | TRAIN_DONE_STABLE |
| paligemma-3b | L12 | 33 | 0.785029 | 0.381374 | 293 | 94.82 | 94.82 | 94.73 | 100.00 | 94.93 | 95.86 | TRAIN_DONE_STABLE |
| paligemma-3b | L13 | 48 | 1.357916 | 1.455967 | 293 | 87.34 | 87.26 | 87.56 | 100.00 | 95.49 | 91.53 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L14 | 50 | 10.762311 | 11.484160 | 293 | 32.64 | 32.85 | 32.57 | 100.00 | 96.28 | 58.87 | TRAIN_DONE_STABLE |
| paligemma-3b | L17 | 6 | 30.519789 | 30.862625 | 293 | 0.08 | 0.08 | 0.09 | 100.00 | 100.00 | 40.05 | TRAIN_DONE_STABLE |
| smolvlm-1.7b | L0 | 41 | 0.450055 | 0.435366 | 293 | 54.33 | 54.21 | 54.12 | 100.00 | 94.16 | 71.36 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L1 | 50 | 0.362595 | 0.523996 | 293 | 52.51 | 52.19 | 52.52 | 100.00 | 93.68 | 70.18 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L2 | 46 | 0.367433 | 0.411423 | 293 | 52.96 | 52.77 | 53.14 | 100.00 | 93.74 | 70.522 | TRAIN_DONE_LOCAL_TMP_JOB3126082 |
| smolvlm-1.7b | L4 | 44 | 0.394254 | 0.523291 | 293 | 52.73 | 52.96 | 52.59 | 100.00 | 94.39 | 70.53 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L5 | 49 | 0.532208 | 0.448303 | 293 | 52.16 | 52.31 | 52.52 | 100.00 | 94.62 | 70.322 | TRAIN_DONE_CMA_MODELPRED_TOP3_BACKFILL_SHARED_JOB3178423 |
| smolvlm-1.7b | L6 | 44 | 0.388501 | 0.489452 | 293 | 51.88 | 51.72 | 52.37 | 100.00 | 93.44 | 69.88 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L7 | 47 | 1.079098 | 0.479630 | 293 | 53.44 | 53.30 | 53.54 | 100.00 | 93.58 | 70.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L8 | 50 | 0.445105 | 0.519847 | 293 | 51.72 | 51.44 | 51.80 | 100.00 | 93.35 | 69.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L9 | 50 | 0.425834 | 0.489161 | 293 | 51.15 | 50.99 | 51.22 | 100.00 | 93.88 | 69.45 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L10 | 50 | 0.374906 | 0.415141 | 293 | 51.35 | 51.25 | 51.26 | 100.00 | 92.85 | 69.34 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L11 | 42 | 0.577633 | 0.520159 | 293 | 51.49 | 51.39 | 51.34 | 100.00 | 93.86 | 69.62 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L12 | 50 | 0.359039 | 0.477444 | 293 | 50.02 | 49.73 | 49.95 | 100.00 | 92.88 | 68.52 | TRAIN_DONE |
| smolvlm-1.7b | L13 | 50 | 0.324814 | 0.407615 | 293 | 52.18 | 51.90 | 51.81 | 100.00 | 93.27 | 69.83 | TRAIN_DONE |
| smolvlm-1.7b | L14 | 40 | 0.521079 | 0.537226 | 293 | 49.68 | 49.32 | 49.61 | 100.00 | 94.60 | 68.64 | TRAIN_DONE |
| smolvlm-1.7b | L15 | 47 | 0.543355 | 0.544850 | 293 | 49.66 | 49.27 | 49.84 | 100.00 | 93.64 | 68.48 | TRAIN_DONE |
| smolvlm-1.7b | L16 | 48 | 0.553617 | 0.595523 | 293 | 47.77 | 47.40 | 47.34 | 100.00 | 93.43 | 67.19 | TRAIN_DONE |
| smolvlm-1.7b | L17 | 48 | 0.749514 | 0.654440 | 293 | 47.84 | 47.70 | 48.11 | 100.00 | 92.58 | 67.25 | TRAIN_DONE |
| smolvlm-1.7b | L18 | 50 | 1.323157 | 1.739675 | 293 | 50.04 | 49.60 | 49.99 | 100.00 | 89.84 | 67.89 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L19 | 49 | 2.573995 | 2.826347 | 293 | 48.91 | 48.48 | 48.83 | 100.00 | 90.48 | 67.34 | TRAIN_DONE |
| smolvlm-1.7b | L20 | 49 | 6.606372 | 4.496605 | 293 | 48.57 | 48.32 | 48.73 | 100.00 | 91.40 | 67.40 | TRAIN_DONE |
| smolvlm-1.7b | L21 | 42 | 2.808244 | 3.857834 | 293 | 49.34 | 49.05 | 49.22 | 100.00 | 88.17 | 67.16 | TRAIN_DONE |

#### MMKE-entity

完成层数：`blip2-opt-2.7b` 21层；`instructblip-vicuna-7b` 表内22个完整评测层，其中候选并集19/19层；`minigpt-4-vicuna-7b` 7层；`llava-v1.5-7b` 7层，正式Top-3并集7/17层；`qwen2.5-vl-3b` 候选并集18/18层；`paligemma-3b` stable 14/15、主配置16层；`smolvlm-1.7b` 候选并集15/15层。LLaVA已有L14,L15,L16,L23,L26,L27,L28完成954条独立MMKE-entity eval并同步共享盘，Average分别为76.034、75.738、76.010、75.540、75.144、75.148、74.742；L22仅训练完成、尚无正式评测，不计入7层完成数。BLIP2 L1和PaliGemma主配置L4已由job 3126082补齐，均完成954条独立MMKE-entity eval，Average分别为72.504和96.136；当前正式七方法Top-3并集中的BLIP2 14/14、PaliGemma 16/16均已完成。InstructBLIP新增9层均已完成954条独立MMKE-entity eval评测；L1为Epoch45恢复训练后完成，L25于Epoch50/step15900完成并评测，Average 47.578。MiniGPT-4 L2已于job 3044841完成954条独立MMKE-entity eval，Average 75.55，selected checkpoint与完整评测产物已备份至login01。SmolVLM 15层与Qwen 18层均完成50 epoch训练流程及954条独立评测。PaliGemma配置内异常：stable仅L0不收敛且无完整评测；主配置L0虽完成但退化为Average 20.00；主配置L16触发34次nonfinite梯度安全跳步且Average 47.044。表内按模型、配置和层号登记。

| Model | Layer | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| blip2-opt-2.7b | L0 | 24 | 5.307720 | 6.124232 | 954 | 57.71 | 57.63 | 57.62 | 100.00 | 56.32 | 65.86 | TRAIN_DONE |
| blip2-opt-2.7b | L1 | 11 | 5.893988 | 5.990400 | 954 | 57.94 | 57.91 | 57.96 | 100.00 | 88.71 | 72.504 | TRAIN_DONE_LOCAL_TMP_JOB3126082 |
| blip2-opt-2.7b | L2 | 3 | 6.995899 | 6.229083 | 954 | 57.81 | 57.83 | 57.85 | 100.00 | 83.12 | 71.32 | TRAIN_DONE |
| blip2-opt-2.7b | L3 | 50 | 2.827587 | 3.004137 | 954 | 53.51 | 53.53 | 53.60 | 100.00 | 94.42 | 71.01 | TRAIN_DONE |
| blip2-opt-2.7b | L4 | 3 | 5.593518 | 6.027703 | 954 | 57.63 | 57.63 | 57.63 | 100.00 | 88.32 | 72.24 | TRAIN_DONE |
| blip2-opt-2.7b | L13 | 50 | 0.539618 | 0.736236 | 954 | 50.51 | 50.41 | 50.56 | 100.00 | 98.09 | 69.91 | TRAIN_DONE |
| blip2-opt-2.7b | L14 | 49 | 0.580979 | 0.732211 | 954 | 50.78 | 50.81 | 50.70 | 100.00 | 98.03 | 70.06 | TRAIN_DONE |
| blip2-opt-2.7b | L15 | 47 | 0.589422 | 0.932563 | 954 | 51.17 | 51.22 | 51.14 | 100.00 | 95.41 | 69.79 | TRAIN_DONE |
| blip2-opt-2.7b | L16 | 50 | 0.516484 | 0.527484 | 954 | 51.01 | 50.98 | 50.99 | 100.00 | 94.25 | 69.45 | TRAIN_DONE |
| blip2-opt-2.7b | L17 | 48 | 0.710702 | 0.651066 | 954 | 51.25 | 51.31 | 51.27 | 100.00 | 97.48 | 70.26 | TRAIN_DONE |
| blip2-opt-2.7b | L18 | 50 | 0.401966 | 0.597055 | 954 | 50.97 | 51.01 | 50.96 | 100.00 | 97.64 | 70.12 | TRAIN_DONE |
| blip2-opt-2.7b | L19 | 49 | 0.557689 | 0.554307 | 954 | 51.60 | 51.48 | 51.60 | 100.00 | 97.25 | 70.39 | TRAIN_DONE |
| blip2-opt-2.7b | L20 | 49 | 0.607764 | 0.626840 | 954 | 51.61 | 51.53 | 51.66 | 100.00 | 98.37 | 70.63 | TRAIN_DONE |
| blip2-opt-2.7b | L21 | 50 | 0.611507 | 0.947310 | 954 | 51.03 | 51.02 | 50.93 | 100.00 | 95.54 | 69.70 | TRAIN_DONE |
| blip2-opt-2.7b | L22 | 47 | 0.476664 | 0.634711 | 954 | 51.91 | 51.96 | 51.87 | 100.00 | 97.01 | 70.55 | TRAIN_DONE |
| blip2-opt-2.7b | L23 | 49 | 0.889130 | 1.210585 | 954 | 51.97 | 52.04 | 51.99 | 100.00 | 97.12 | 70.62 | TRAIN_DONE |
| blip2-opt-2.7b | L24 | 47 | 1.978343 | 1.652320 | 954 | 52.18 | 52.33 | 52.03 | 100.00 | 97.45 | 70.80 | TRAIN_DONE |
| blip2-opt-2.7b | L25 | 50 | 1.257574 | 1.250349 | 954 | 52.23 | 52.30 | 52.30 | 100.00 | 96.99 | 70.76 | TRAIN_DONE |
| blip2-opt-2.7b | L26 | 46 | 1.123006 | 1.444681 | 954 | 51.81 | 51.77 | 51.78 | 100.00 | 94.20 | 69.91 | TRAIN_DONE |
| blip2-opt-2.7b | L29 | 48 | 3.541405 | 3.073246 | 954 | 52.75 | 52.77 | 52.67 | 100.00 | 96.40 | 70.92 | TRAIN_DONE |
| blip2-opt-2.7b | L30 | 50 | 4.810149 | 5.183463 | 954 | 52.61 | 52.52 | 52.64 | 100.00 | 97.95 | 71.14 | TRAIN_DONE |
| instructblip-vicuna-7b | L0 | 45 | 0.791271 | 0.933128 | 954 | 48.70 | 48.77 | 48.74 | 100.00 | 95.38 | 68.32 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L1 | 43 | 0.994486 | 1.514755 | 954 | 48.72 | 48.85 | 48.71 | 100.00 | 99.61 | 69.18 | TRAIN_DONE_RESUMED_EPOCH45_CPU_SYNC_ACTIVATION_CKPT_JOB3044841 |
| instructblip-vicuna-7b | L2 | 49 | 10.099280 | 9.843736 | 954 | 16.71 | 16.24 | 16.61 | 100.00 | 99.38 | 49.79 | TRAIN_DONE |
| instructblip-vicuna-7b | L3 | 47 | 8.834968 | 9.652104 | 954 | 17.12 | 16.72 | 17.08 | 100.00 | 99.19 | 50.02 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L4 | 50 | 13.571908 | 11.388381 | 954 | 15.15 | 14.54 | 15.05 | 100.00 | 99.72 | 48.89 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L5 | 49 | 12.275386 | 11.474885 | 954 | 13.91 | 13.44 | 13.84 | 100.00 | 99.82 | 48.20 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L14 | 48 | 10.428762 | 10.631304 | 954 | 14.62 | 14.47 | 14.57 | 100.00 | 99.53 | 48.64 | TRAIN_DONE |
| instructblip-vicuna-7b | L15 | 49 | 11.955615 | 11.116361 | 954 | 14.99 | 14.60 | 14.88 | 100.00 | 99.75 | 48.84 | TRAIN_DONE |
| instructblip-vicuna-7b | L16 | 50 | 8.842422 | 10.171081 | 954 | 14.85 | 14.33 | 14.81 | 100.00 | 99.61 | 48.72 | TRAIN_DONE |
| instructblip-vicuna-7b | L17 | 50 | 11.998194 | 11.095907 | 954 | 15.27 | 14.50 | 15.24 | 100.00 | 99.63 | 48.93 | TRAIN_DONE |
| instructblip-vicuna-7b | L18 | 48 | 11.101890 | 10.146582 | 954 | 14.76 | 14.27 | 14.75 | 100.00 | 99.34 | 48.62 | TRAIN_DONE |
| instructblip-vicuna-7b | L19 | 48 | 13.396421 | 11.298227 | 954 | 14.60 | 14.37 | 14.49 | 100.00 | 99.53 | 48.60 | TRAIN_DONE |
| instructblip-vicuna-7b | L22 | 49 | 12.596491 | 11.504756 | 954 | 14.08 | 13.22 | 14.08 | 100.00 | 99.25 | 48.13 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L23 | 46 | 11.005220 | 10.972629 | 954 | 14.24 | 13.63 | 14.15 | 100.00 | 99.64 | 48.33 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L24 | 50 | 10.610746 | 10.732185 | 954 | 12.35 | 11.97 | 12.24 | 100.00 | 99.78 | 47.27 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L25 | 50 | 12.247351 | 10.972824 | 954 | 13.10 | 12.44 | 13.08 | 100.00 | 99.27 | 47.58 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| instructblip-vicuna-7b | L26 | 46 | 10.188010 | 11.535521 | 954 | 12.93 | 12.35 | 12.89 | 100.00 | 99.42 | 47.52 | TRAIN_DONE |
| instructblip-vicuna-7b | L27 | 49 | 11.816212 | 11.171924 | 954 | 12.24 | 11.65 | 12.20 | 100.00 | 98.63 | 46.94 | TRAIN_DONE |
| instructblip-vicuna-7b | L28 | 47 | 9.575759 | 11.254244 | 954 | 11.90 | 11.49 | 11.74 | 100.00 | 99.24 | 46.87 | TRAIN_DONE |
| instructblip-vicuna-7b | L29 | 48 | 12.351160 | 11.742287 | 954 | 11.66 | 10.67 | 11.61 | 100.00 | 99.58 | 46.70 | TRAIN_DONE |
| instructblip-vicuna-7b | L30 | 45 | 13.693354 | 14.488698 | 954 | 11.25 | 10.29 | 11.08 | 100.00 | 99.80 | 46.48 | TRAIN_DONE |
| instructblip-vicuna-7b | L31 | 37 | 33.016987 | 38.583624 | 954 | 0.20 | 0.20 | 0.20 | 100.00 | 100.00 | 40.12 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L2 | 48 | 0.274402 | 0.280683 | 954 | 59.89 | 59.84 | 59.78 | 100.00 | 98.24 | 75.55 | TRAIN_DONE_LOCAL_TMP_JOB3044841_BACKED_UP |
| minigpt-4-vicuna-7b | L15 | 46 | 0.303345 | 0.305240 | 954 | 60.02 | 60.06 | 60.10 | 100.00 | 98.36 | 75.71 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L23 | 50 | 0.380379 | 0.484842 | 954 | 59.08 | 59.10 | 58.97 | 100.00 | 98.00 | 75.03 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L24 | 50 | 0.425550 | 0.585518 | 954 | 59.20 | 59.28 | 59.13 | 100.00 | 97.57 | 75.04 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L25 | 49 | 0.918550 | 1.143279 | 954 | 59.21 | 59.32 | 59.25 | 100.00 | 98.13 | 75.18 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L28 | 48 | 1.072329 | 1.784545 | 954 | 60.66 | 60.69 | 60.67 | 100.00 | 98.20 | 76.04 | TRAIN_DONE |
| minigpt-4-vicuna-7b | L31 | 41 | 5.441149 | 5.627008 | 954 | 60.69 | 59.93 | 60.71 | 100.00 | 100.00 | 76.27 | TRAIN_DONE |
| llava-v1.5-7b | L14 | 49 | 0.159782 | 0.290381 | 954 | 61.31 | 61.45 | 61.29 | 100.00 | 96.12 | 76.034 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3126082 |
| llava-v1.5-7b | L15 | 45 | 0.423595 | 0.272476 | 954 | 61.07 | 61.18 | 61.01 | 100.00 | 95.43 | 75.738 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3126082 |
| llava-v1.5-7b | L16 | 41 | 0.172495 | 0.248927 | 954 | 61.13 | 61.25 | 61.10 | 100.00 | 96.57 | 76.010 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3126082 |
| llava-v1.5-7b | L22 | 45 | 0.274654 | 0.354578 | 954 | 60.32 | 60.40 | 60.34 | 100.00 | 97.03 | 75.618 | TRAIN_DONE_EVAL_DONE_SHARED_JOB3178423_VERIFIED_20260921 |
| llava-v1.5-7b | L23 | 49 | 0.284640 | 0.374458 | 954 | 60.39 | 60.41 | 60.34 | 100.00 | 96.56 | 75.540 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| llava-v1.5-7b | L24 | 41 | 0.316075 | 0.401128 | 954 | 60.05 | 60.14 | 60.04 | 100.00 | 96.74 | 75.394 | TRAIN_DONE_EVAL_DONE_SHARED_JOB3178423_VERIFIED_20260921 |
| llava-v1.5-7b | L26 | 46 | 0.452505 | 0.778010 | 954 | 59.95 | 60.07 | 59.97 | 100.00 | 95.73 | 75.144 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| llava-v1.5-7b | L27 | 50 | 0.859437 | 1.028096 | 954 | 60.03 | 60.08 | 60.00 | 100.00 | 95.63 | 75.148 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| llava-v1.5-7b | L28 | 48 | 1.354002 | 1.707617 | 954 | 59.47 | 59.54 | 59.50 | 100.00 | 95.20 | 74.742 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| qwen2.5-vl-3b | L0 | 50 | 1.760615 | 1.334659 | 954 | 54.78 | 54.49 | 54.88 | 100.00 | 96.93 | 72.22 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L1 | 50 | 1.050795 | 1.466707 | 954 | 54.69 | 54.59 | 54.85 | 100.00 | 97.25 | 72.28 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L2 | 49 | 0.828287 | 1.272041 | 954 | 54.88 | 54.78 | 54.96 | 100.00 | 95.57 | 72.04 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L13 | 49 | 1.519723 | 1.238898 | 954 | 53.29 | 53.17 | 53.31 | 100.00 | 97.43 | 71.44 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L14 | 49 | 0.686763 | 0.980262 | 954 | 53.46 | 53.41 | 53.44 | 100.00 | 97.10 | 71.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L15 | 50 | 1.871835 | 1.463023 | 954 | 52.94 | 52.85 | 52.95 | 100.00 | 96.87 | 71.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L16 | 47 | 1.531398 | 1.362743 | 954 | 53.68 | 53.56 | 53.73 | 100.00 | 96.98 | 71.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L17 | 46 | 0.521832 | 1.285736 | 954 | 53.59 | 53.47 | 53.61 | 100.00 | 96.73 | 71.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L18 | 49 | 0.705021 | 0.883009 | 954 | 53.65 | 53.56 | 53.61 | 100.00 | 95.17 | 71.20 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L20 | 49 | 0.910451 | 0.666375 | 954 | 53.24 | 53.16 | 53.35 | 100.00 | 96.30 | 71.21 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L21 | 50 | 0.532463 | 0.822907 | 954 | 52.65 | 52.37 | 52.65 | 100.00 | 95.62 | 70.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L22 | 49 | 1.156874 | 0.733265 | 954 | 53.59 | 53.36 | 53.53 | 100.00 | 96.00 | 71.30 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L25 | 44 | 0.686750 | 0.649926 | 954 | 54.00 | 53.87 | 54.03 | 100.00 | 96.58 | 71.70 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L26 | 46 | 0.741123 | 1.065371 | 954 | 52.78 | 52.53 | 52.82 | 100.00 | 95.18 | 70.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L27 | 50 | 1.188038 | 0.983534 | 954 | 53.91 | 53.67 | 54.05 | 100.00 | 95.07 | 71.34 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L28 | 50 | 0.872761 | 1.150297 | 954 | 54.69 | 54.54 | 54.83 | 100.00 | 95.01 | 71.81 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L29 | 48 | 1.635255 | 1.636492 | 954 | 55.81 | 55.61 | 55.91 | 100.00 | 95.95 | 72.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| qwen2.5-vl-3b | L30 | 50 | 1.664727 | 2.286476 | 954 | 55.97 | 55.74 | 55.92 | 100.00 | 94.42 | 72.41 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| paligemma-3b | L0 | 8 | 2887.873291 | 2815.587779 | 954 | 0.00 | 0.00 | 0.00 | 100.00 | 0.00 | 20.00 | TRAIN_DONE_MAIN_NUMERIC_DEGENERATE_JOB3044208 |
| paligemma-3b | L1 | 3 | 3.320363 | 2.964910 | 954 | 93.20 | 93.23 | 93.41 | 100.00 | 64.47 | 88.86 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L2 | 3 | 4.878585 | 6.100427 | 954 | 84.24 | 84.22 | 84.72 | 100.00 | 57.00 | 82.04 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L3 | 7 | 2.865983 | 2.230218 | 954 | 91.52 | 91.49 | 91.94 | 100.00 | 89.89 | 92.97 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L4 | 2 | 0.704963 | 0.882321 | 954 | 96.56 | 96.55 | 96.83 | 100.00 | 90.74 | 96.136 | TRAIN_DONE_MAIN_LOCAL_TMP_JOB3126082 |
| paligemma-3b | L5 | 4 | 1.668180 | 2.039312 | 954 | 88.46 | 88.47 | 88.73 | 100.00 | 88.39 | 90.81 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L6 | 2 | 1.206908 | 1.361229 | 954 | 95.85 | 95.89 | 95.96 | 100.00 | 97.22 | 96.98 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L7 | 10 | 2.394458 | 2.547924 | 954 | 84.71 | 84.65 | 84.72 | 100.00 | 96.53 | 90.12 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L8 | 3 | 0.592419 | 1.096720 | 954 | 95.94 | 95.81 | 96.00 | 100.00 | 93.73 | 96.30 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L9 | 2 | 4.133635 | 3.973418 | 954 | 78.51 | 78.36 | 78.55 | 100.00 | 91.62 | 85.41 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L10 | 1 | 18.536318 | 17.571920 | 954 | 15.04 | 15.09 | 15.00 | 100.00 | 46.26 | 38.28 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L11 | 1 | 12.053761 | 12.271097 | 954 | 21.41 | 21.14 | 21.52 | 100.00 | 59.04 | 44.62 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L12 | 2 | 2.737614 | 2.109276 | 954 | 88.78 | 88.73 | 88.85 | 100.00 | 87.00 | 90.67 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L13 | 2 | 10.599213 | 11.613107 | 954 | 17.60 | 17.58 | 17.52 | 100.00 | 90.57 | 48.65 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L16 | 49 | 15.929332 | 18.301300 | 954 | 12.43 | 12.21 | 12.41 | 100.00 | 98.17 | 47.04 | TRAIN_DONE_MAIN_RETRY_NUMERIC_GUARD_NONFINITE_SKIP34_JOB3044208 |
| paligemma-3b | L17 | 22 | 31.180017 | 31.213888 | 954 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | TRAIN_DONE_MAIN_JOB3044208 |
| paligemma-3b | L1 | 37 | 0.333475 | 0.368120 | 954 | 99.34 | 99.34 | 99.57 | 100.00 | 96.30 | 98.91 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L2 | 38 | 0.323105 | 0.361797 | 954 | 99.34 | 99.34 | 99.53 | 100.00 | 95.78 | 98.80 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L3 | 47 | 0.345626 | 0.346825 | 954 | 98.87 | 98.88 | 99.07 | 100.00 | 97.39 | 98.84 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L5 | 35 | 0.340905 | 0.359304 | 954 | 98.98 | 98.97 | 99.32 | 100.00 | 96.52 | 98.76 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L6 | 47 | 0.330504 | 0.359201 | 954 | 99.09 | 99.08 | 99.39 | 100.00 | 97.22 | 98.96 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L7 | 49 | 0.329062 | 0.344094 | 954 | 99.32 | 99.31 | 99.44 | 100.00 | 95.35 | 98.68 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L8 | 49 | 0.342368 | 0.348620 | 954 | 99.32 | 99.31 | 99.39 | 100.00 | 97.94 | 99.19 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L9 | 50 | 0.339769 | 0.346904 | 954 | 99.35 | 99.34 | 99.35 | 100.00 | 97.35 | 99.08 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L10 | 49 | 0.347619 | 0.345262 | 954 | 99.03 | 99.00 | 99.00 | 100.00 | 97.25 | 98.86 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L11 | 47 | 0.577410 | 0.686626 | 954 | 94.89 | 94.83 | 94.83 | 100.00 | 97.34 | 96.38 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L12 | 48 | 0.538605 | 0.830285 | 954 | 93.40 | 93.26 | 93.41 | 100.00 | 96.41 | 95.30 | TRAIN_DONE_STABLE_RETRY_BUFFER1_GPU0_JOB3044208 |
| paligemma-3b | L13 | 49 | 1.960766 | 2.245620 | 954 | 81.47 | 81.04 | 81.51 | 100.00 | 97.54 | 88.31 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L16 | 42 | 18.220282 | 19.640825 | 954 | 12.38 | 12.42 | 12.37 | 100.00 | 96.65 | 46.76 | TRAIN_DONE_STABLE_JOB3044208 |
| paligemma-3b | L17 | 38 | 30.471798 | 30.907994 | 954 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | TRAIN_DONE_STABLE_JOB3044208 |
| smolvlm-1.7b | L0 | 47 | 0.717729 | 0.663257 | 954 | 51.76 | 51.75 | 51.71 | 100.00 | 97.11 | 70.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L1 | 45 | 0.510274 | 0.635121 | 954 | 52.58 | 52.50 | 52.64 | 100.00 | 97.52 | 71.05 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L2 | 49 | 0.532231 | 0.734351 | 954 | 52.80 | 52.79 | 52.69 | 100.00 | 97.30 | 71.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L6 | 47 | 0.546545 | 0.688924 | 954 | 51.98 | 51.99 | 52.03 | 100.00 | 96.46 | 70.49 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L7 | 50 | 1.166944 | 0.670295 | 954 | 51.42 | 51.40 | 51.38 | 100.00 | 97.32 | 70.30 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L9 | 50 | 0.814315 | 0.769834 | 954 | 51.86 | 51.94 | 51.85 | 100.00 | 96.55 | 70.44 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L10 | 48 | 0.795752 | 0.811847 | 954 | 52.21 | 52.14 | 52.14 | 100.00 | 96.59 | 70.62 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L11 | 50 | 0.662297 | 0.798535 | 954 | 50.22 | 50.39 | 50.18 | 100.00 | 96.97 | 69.55 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L12 | 50 | 0.663954 | 0.936153 | 954 | 52.31 | 52.27 | 52.31 | 100.00 | 97.32 | 70.84 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L13 | 50 | 0.489384 | 0.820767 | 954 | 50.63 | 50.76 | 50.62 | 100.00 | 96.22 | 69.65 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L14 | 50 | 0.687138 | 0.851731 | 954 | 50.21 | 50.31 | 50.02 | 100.00 | 96.08 | 69.32 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L15 | 50 | 0.973436 | 0.839188 | 954 | 50.24 | 50.42 | 50.08 | 100.00 | 96.91 | 69.53 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L16 | 50 | 1.646834 | 1.453352 | 954 | 50.85 | 50.96 | 50.69 | 100.00 | 95.45 | 69.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L17 | 48 | 2.262018 | 2.741290 | 954 | 52.45 | 52.62 | 52.32 | 100.00 | 95.55 | 70.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| smolvlm-1.7b | L18 | 50 | 3.508034 | 3.420248 | 954 | 53.75 | 53.91 | 53.65 | 100.00 | 96.03 | 71.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

### 4.1 EVQA-pilot500 / BLIP2-OPT-2.7B

结果来源：`md/Location/blip2_pliot500_epoch50_fulltest_layer_sweep_outcome.md`；2026-07-28待补5层来自g09本地`/tmp/ph_teacher3/evqa_pilot500_blip2_missing5_job3044208_20260728`。

训练与评测设置：

- 训练数据：`vqa_train_proxy500.json`。
- 评测数据：full E-VQA eval/test，共 `2093` 个样本。
- 训练轮数：每层 `50 epoch`。
- Checkpoint 选择：每层 minimum EMA loss。
- 流程隔离：每层评测独立 Python 进程，重新加载 base model 与当前层 adapter/hook。
- 特别说明：`L0` 使用原始有效 run；`L5/L10/L15/L19/L25/L30` 使用修复 wrapper 后的 fixed rerun；`L16/L17/L18/L20/L21/L24/L26/L29` 为后续补跑/补评结果；`L1/L2/L3/L4/L14` 为job 3044208在2026-07-28至2026-07-29完成的候选并集待补结果，均具备完整训练、selected checkpoint和正式评测标记。

| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L0 | 43 | 0.375991 | 0.368115 | 44.15 | 40.43 | 40.29 | 100.00 | 65.95 | 58.16 |
| L1 | 45 | 0.521112 | 0.425138 | 46.63 | 42.52 | 44.03 | 100.00 | 59.35 | 58.506 |
| L2 | 49 | 0.347236 | 0.417455 | 32.99 | 28.69 | 30.45 | 100.00 | 58.51 | 50.128 |
| L3 | 48 | 0.326949 | 0.366410 | 51.06 | 48.13 | 49.59 | 100.00 | 63.52 | 62.460 |
| L4 | 48 | 0.376648 | 0.397449 | 43.82 | 40.43 | 40.51 | 100.00 | 61.56 | 57.264 |
| L5 | 49 | 0.300460 | 0.396571 | 62.10 | 59.42 | 59.48 | 100.00 | 63.45 | 68.89 |
| L10 | 48 | 0.253585 | 0.299741 | 64.79 | 61.72 | 62.38 | 100.00 | 76.55 | 73.09 |
| L14 | 46 | 0.206319 | 0.309126 | 69.08 | 66.40 | 67.19 | 100.00 | 73.29 | 75.192 |
| L15 | 42 | 0.238769 | 0.336919 | 66.35 | 62.89 | 63.90 | 100.00 | 72.05 | 73.04 |
| L16 | 48 | 0.342088 | 0.393885 | 65.67 | 61.31 | 63.96 | 100.00 | 78.04 | 73.80 |
| L17 | 49 | 0.377570 | 0.384648 | 66.89 | 63.79 | 65.36 | 100.00 | 81.94 | 75.60 |
| L18 | 50 | 0.346307 | 0.392374 | 61.31 | 58.54 | 59.58 | 100.00 | 81.57 | 72.20 |
| L18-2 | 50 | 0.338767 | 0.385482 | 63.29 | 59.64 | 62.24 | 100.00 | 81.51 | 73.34 |
| L19 | 41 | 0.277514 | 0.291689 | 68.80 | 65.80 | 65.01 | 100.00 | 74.65 | 74.85 |
| L20 | 49 | 0.330291 | 0.379787 | 62.38 | 58.49 | 60.65 | 100.00 | 82.90 | 72.88 |
| L21 | 44 | 0.369473 | 0.378125 | 59.31 | 55.13 | 59.29 | 100.00 | 82.94 | 71.33 |
| L24 | 43 | 0.348283 | 0.361316 | 46.55 | 42.21 | 48.30 | 100.00 | 80.82 | 63.58 |
| L25 | 45 | 0.205779 | 0.232244 | 60.27 | 56.49 | 57.02 | 100.00 | 80.14 | 70.78 |
| L26 | 49 | 0.359013 | 0.363611 | 37.61 | 34.55 | 38.48 | 100.00 | 77.07 | 57.54 |
| L29 | 48 | 0.387346 | 0.414155 | 27.57 | 25.43 | 27.64 | 100.00 | 71.54 | 50.44 |
| L30 | 48 | 0.246737 | 0.557950 | 32.60 | 30.53 | 30.22 | 100.00 | 74.86 | 53.64 |

当前已测层中 full E-VQA `Average` 最高层为 `L17`，Average `75.60`。

候选方法回填：

| Method | Top-3 | Best@3 Layer | Best@3 Average | Top-5 | Best@5 Layer | Best@5 Average | 备注 |
|---|---|---:|---:|---|---:|---:|---|
| VisEdit-Contrib-Pre-FirstToken (historical) | L20,L19,L18 | L19 | 74.85 | L20,L19,L18,L17,L16 | L17 | 75.60 | Top-5 命中当前已测最优层；严格 KeyToken 待重算 |
| Middle-Prior-Direct | L17,L18,L16 | L17 | 75.60 | L17,L18,L16,L19,L15 | L17 | 75.60 | Top-3 命中当前已测最优层 |

### 4.2 EVQA-pilot500 / InstructBLIP-Vicuna-7B

结果来源：`downloads/contribution_pre_7_models/instructblip-vicuna-7b/full_eval_results_L28_L27_L26_merged.csv`

训练与评测设置：

- 训练数据：`vqa_train_proxy500.json`。
- 评测数据：full E-VQA eval/test，共 `2093` 个样本。
- 训练轮数：每层 `50 epoch`。
- Checkpoint 选择：每层 minimum EMA loss。
- 已完成层：历史 `VisEdit-Contrib-Pre-FirstToken` 的 Top-3，即 `L28/L27/L26`。

| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L28 | 49 | 1.700526 | 1.100682 | 29.86 | 28.72 | 28.78 | 100.00 | 79.00 | 53.27 |
| L27 | 36 | 0.274748 | 0.888490 | 29.64 | 28.66 | 28.71 | 100.00 | 74.34 | 52.27 |
| L26 | 50 | 0.202061 | 0.881081 | 29.65 | 28.92 | 27.94 | 100.00 | 70.70 | 51.44 |

当前已测 Top-3 中 full E-VQA `Average` 最高层为 `L28`，Average `53.27`。

候选方法回填：

| Method | Top-3 | Best@3 Layer | Best@3 Average | Top-5 | Best@5 Layer | Best@5 Average | 备注 |
|---|---|---:|---:|---|---:|---:|---|
| VisEdit-Contrib-Pre-FirstToken (historical) | L28,L27,L26 | L28 | 53.27 | L28,L27,L26,L25,L24 | L28 | 53.27 | 目前只完成历史 Top-3；L25/L24 待测；严格 KeyToken 待重算 |
| Middle-Prior-Direct | L17,L18,L16 | - | - | L17,L18,L16,L19,L15 | - | - | 这些层尚未真实扫层 |

## 5. 真实扫层实验使用方式

1. 对每个 `dataset × model`，先取所有定位方法的 Top-3 并集做低预算真实扫层。
2. 再取所有定位方法的 Top-5 并集做完整候选层真实扫层。
3. 每个候选层使用完全相同的编辑训练配置，并记录 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average`。
4. 方法比较时按自己的 Top-K 集合回填真实扫层结果，报告 `Best@3 / Best@5 / Regret@3 / Regret@5 / Hit@3 / Hit@5`。
5. 跨数据集和跨模型汇总时使用 macro-average，避免样本量或层数不同导致结果偏置。

## 6. 注意

- PaliGemma-3B 在 MMKE 上的贡献度绝对值很小，候选层仍按相同规则给出，但真实编辑比较时建议标记为 low-confidence contribution。
- Qwen2.5-VL 做后续 visual token 梯度或编辑实验时，需要固定输入分辨率，避免视觉 token 数随图片尺寸变化。
- EVQA-pilot500 的 BLIP2 结果来自单独 BLIP2 pilot500 目录，其余 6 个模型来自 crossmodel pilot500 目录。
- 后续生成重跑队列时，以第 3.5 节为总登记，并结合第 3.4.1 节的逐层细节搜索精确标记 `RETRY_REQUIRED` 或 `FAILED_NONCONVERGENT`；只有同时具备 `selected_checkpoint.tsv`、对应 test/eval 完整评测结果及 `eval_full.done` 的层，才能从重跑登记移入已完成结果。












