# 真实扫层实验候选编辑层清单

本文档记录后续真实扫层实验要比较的候选编辑层。正式比较只保留 6 种候选定位方法，外加真实扫层 `Oracle Sweep` 作为上界。当前已计算完成的是 `VisEdit-Contrib-Pre` 主版本：使用我们已经完成的 7 个模型在 `EVQA-pilot500`、`MMKE-visual`、`MMKE-entity` 上对关键 token `alt` 的贡献度分析结果，并按“插在贡献形成之前”的 VisEdit adapter 逻辑生成候选层。已完成真实扫层结果回填见第 5 节。

正式方法清单：

1. `Middle-layer Prior`
2. `VisEdit-Contrib-Pre`
3. `SaLEM`
4. `GoldenLayer / LGA`
5. `Perturb-KL-Direct`
6. `Ours-Pre`
7. `Oracle Sweep`，只作为真实扫层上界，不作为预测方法。

附加 / 消融方法：`Perturb-KL-Pre`。该方法不计入主扰动基线，后续用于检验 “Direct 高敏感层” 与 “Pre 前置层” 两种插入规则的差异。

## 1. 统一规则

- 层编号：0-indexed，例如 `L0` 到 `L31`。
- key token：`alt_first_token`，即新知识 / 目标答案的首个 token。
- 排序指标：`score_positive = max(0, attn_mean) + max(0, mlp_mean)`。
- 高贡献区识别：对 `score_positive` 做 3 层平滑，阈值为 `mean + 0.5 * std`，取最长连续高贡献区间。
- VisEdit-Contrib-Pre 候选规则：若高贡献区间起始层为 `s_H`，则 `Top-K = {s_H-1, s_H-2, ..., s_H-K}`。
- 本文档中的 Top-3 / Top-5 是编辑插入层候选，不是贡献峰值层。

## 2. VisEdit-Contrib-Pre 候选层

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

## 3. 数据集分表

### 3.1 EVQA-pilot500

| Model | 高贡献区间 | Top-3 | Top-5 |
|---|---|---|---|
| BLIP2-OPT-2.7B | L21-L29 | L20,L19,L18 | L20,L19,L18,L17,L16 |
| InstructBLIP-Vicuna-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| MiniGPT-4-Vicuna-7B | L27-L31 | L26,L25,L24 | L26,L25,L24,L23,L22 |
| LLaVA-v1.5-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| Qwen2.5-VL-3B | L30-L35 | L29,L28,L27 | L29,L28,L27,L26,L25 |
| PaliGemma-3B | L13-L16 | L12,L11,L10 | L12,L11,L10,L9,L8 |
| SmolVLM-Instruct-1.7B | L18-L23 | L17,L16,L15 | L17,L16,L15,L14,L13 |

### 3.2 MMKE-visual

| Model | 高贡献区间 | Top-3 | Top-5 |
|---|---|---|---|
| BLIP2-OPT-2.7B | L23-L29 | L22,L21,L20 | L22,L21,L20,L19,L18 |
| InstructBLIP-Vicuna-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| MiniGPT-4-Vicuna-7B | L27-L31 | L26,L25,L24 | L26,L25,L24,L23,L22 |
| LLaVA-v1.5-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| Qwen2.5-VL-3B | L30-L32 | L29,L28,L27 | L29,L28,L27,L26,L25 |
| PaliGemma-3B | L13-L15 | L12,L11,L10 | L12,L11,L10,L9,L8 |
| SmolVLM-Instruct-1.7B | L18-L23 | L17,L16,L15 | L17,L16,L15,L14,L13 |

### 3.3 MMKE-entity

| Model | 高贡献区间 | Top-3 | Top-5 |
|---|---|---|---|
| BLIP2-OPT-2.7B | L23-L30 | L22,L21,L20 | L22,L21,L20,L19,L18 |
| InstructBLIP-Vicuna-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| MiniGPT-4-Vicuna-7B | L26-L31 | L25,L24,L23 | L25,L24,L23,L22,L21 |
| LLaVA-v1.5-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| Qwen2.5-VL-3B | L30-L35 | L29,L28,L27 | L29,L28,L27,L26,L25 |
| PaliGemma-3B | L14-L16 | L13,L12,L11 | L13,L12,L11,L10,L9 |
| SmolVLM-Instruct-1.7B | L20-L23 | L19,L18,L17 | L19,L18,L17,L16,L15 |

## 4. 其他定位方法候选层登记区

下面这些方法使用同一套 Top-3 / Top-5 格式登记，方便后续把真实编辑扫层结果回填到同一张比较表。

### 4.1 Middle-layer Prior

该方法不依赖数据集，因此同一模型在三个数据集上的候选层相同。按 `6edit_layer_localization_candidate_methods_revised.md` 使用严格网络中点 `rho=0.5`；候选层按与中点 `(L-1)/2` 的距离升序排列，距离相同取较浅层。
| Model | L | Top-3 | Top-5 |
|---|---:|---|---|
| BLIP2-OPT-2.7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| InstructBLIP-Vicuna-7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| MiniGPT-4-Vicuna-7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| LLaVA-v1.5-7B | 32 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| Qwen2.5-VL-3B | 36 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| PaliGemma-3B | 18 | L8,L9,L7 | L8,L9,L7,L10,L6 |
| SmolVLM-Instruct-1.7B | 24 | L11,L12,L10 | L11,L12,L10,L13,L9 |

### 4.2 VisEdit-Contrib-Pre

该方法使用第 2 节的 `alt_first_token` 模块贡献度结果，先识别高贡献区间，再按 VisEdit adapter “插在贡献形成之前”的规则取前置层。完整贡献度来源见第 2 节。

| Dataset | Model | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L20,L19,L18 | L20,L19,L18,L17,L16 | done |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | done |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L26,L25,L24 | L26,L25,L24,L23,L22 | done |
| EVQA-pilot500 | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | done |
| EVQA-pilot500 | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | done |
| EVQA-pilot500 | PaliGemma-3B | L12,L11,L10 | L12,L11,L10,L9,L8 | done |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L17,L16,L15 | L17,L16,L15,L14,L13 | done |
| MMKE-visual | BLIP2-OPT-2.7B | L22,L21,L20 | L22,L21,L20,L19,L18 | done |
| MMKE-visual | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | done |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L26,L25,L24 | L26,L25,L24,L23,L22 | done |
| MMKE-visual | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | done |
| MMKE-visual | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | done |
| MMKE-visual | PaliGemma-3B | L12,L11,L10 | L12,L11,L10,L9,L8 | done |
| MMKE-visual | SmolVLM-Instruct-1.7B | L17,L16,L15 | L17,L16,L15,L14,L13 | done |
| MMKE-entity | BLIP2-OPT-2.7B | L22,L21,L20 | L22,L21,L20,L19,L18 | done |
| MMKE-entity | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | done |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L25,L24,L23 | L25,L24,L23,L22,L21 | done |
| MMKE-entity | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | done |
| MMKE-entity | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | done |
| MMKE-entity | PaliGemma-3B | L13,L12,L11 | L13,L12,L11,L10,L9 | done |
| MMKE-entity | SmolVLM-Instruct-1.7B | L19,L18,L17 | L19,L18,L17,L16,L15 | done |

### 4.3 SaLEM

该方法按 `md/Location/Equations/salem_candidate_layer_formulas.md` 的参数梯度显著性公式计算，当前已完成 18/21；`Qwen2.5-VL-3B` 三个数据集均为 `rc=1`，待修复后重算。

| Dataset | Model | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L21 | done; n=500/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L20,L17 | done; n=500/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | mean_abs_param_grad_alt | L8,L9,L10 | L8,L9,L10,L5,L6 | done; n=500/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | mean_abs_param_grad_alt | L7,L6,L5 | L7,L6,L5,L8,L9 | done; n=500/500 |
| EVQA-pilot500 | Qwen2.5-VL-3B | mean_abs_param_grad_alt | - | - | failed; rc=1 |
| EVQA-pilot500 | PaliGemma-3B | mean_abs_param_grad_alt | L8,L7,L9 | L8,L7,L9,L10,L6 | done; n=500/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | mean_abs_param_grad_alt | L9,L8,L7 | L9,L8,L7,L6,L10 | done; n=500/500 |
| MMKE-visual | BLIP2-OPT-2.7B | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L20 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L20,L16 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | mean_abs_param_grad_alt | L31,L5,L8 | L31,L5,L8,L6,L9 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | mean_abs_param_grad_alt | L7,L8,L9 | L7,L8,L9,L6,L10 | done; n=214/214 |
| MMKE-visual | Qwen2.5-VL-3B | mean_abs_param_grad_alt | - | - | failed; rc=1 |
| MMKE-visual | PaliGemma-3B | mean_abs_param_grad_alt | L10,L8,L9 | L10,L8,L9,L7,L5 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | mean_abs_param_grad_alt | L9,L8,L0 | L9,L8,L0,L10,L7 | done; n=214/214 |
| MMKE-entity | BLIP2-OPT-2.7B | mean_abs_param_grad_alt | L0,L18,L30 | L0,L18,L30,L19,L17 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L16,L20 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | mean_abs_param_grad_alt | L31,L22,L24 | L31,L22,L24,L21,L23 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | mean_abs_param_grad_alt | L23,L22,L24 | L23,L22,L24,L25,L21 | done; n=636/636 |
| MMKE-entity | Qwen2.5-VL-3B | mean_abs_param_grad_alt | - | - | failed; rc=1 |
| MMKE-entity | PaliGemma-3B | mean_abs_param_grad_alt | L17,L16,L13 | L17,L16,L13,L0,L10 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | mean_abs_param_grad_alt | L0,L1,L6 | L0,L1,L6,L7,L5 | done; n=636/636 |

### 4.4 GoldenLayer / LGA

该方法使用 hidden-state gradient attribution 排序。当前尚未回填候选层；逐模型待补登记保留在 4.9。

| Dataset | Model scope | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | 7 models | - | - | pending |
| MMKE-visual | 7 models | - | - | pending |
| MMKE-entity | 7 models | - | - | pending |

### 4.5 Perturb-KL-Direct

该方法作为主扰动基线：对每一层做扰动，计算输出分布 KL sensitivity，并直接选择 KL 分数最高的层作为候选编辑层。该方法不做 VisEdit-Pre 的前置层平移；即 `Top-K` 直接来自扰动敏感层排序。当前尚未回填候选层；逐模型待补登记保留在 4.10。

| Dataset | Model scope | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | 7 models | - | - | pending |
| MMKE-visual | 7 models | - | - | pending |
| MMKE-entity | 7 models | - | - | pending |

### 4.6 Perturb-KL-Pre

该方法作为附加 / 消融实验：先用层扰动 KL sensitivity 找高敏感区，再按 “插在敏感性形成之前” 的逻辑取前置层。它不作为主扰动基线；主实验优先计算 4.5 `Perturb-KL-Direct`。

| Dataset | Model scope | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | 7 models | - | - | pending; ablation |
| MMKE-visual | 7 models | - | - | pending; ablation |
| MMKE-entity | 7 models | - | - | pending; ablation |

### 4.7 Ours-Pre

该方法用 request-only visual gradient delta-LGA 找高分区，并按前置层规则生成编辑候选。当前尚未回填候选层；逐模型待补登记保留在 4.10。

| Dataset | Model scope | Top-3 | Top-5 | Status |
|---|---|---|---|---|
| EVQA-pilot500 | 7 models | - | - | pending |
| MMKE-visual | 7 models | - | - | pending |
| MMKE-entity | 7 models | - | - | pending |

### 4.8 正式候选方法说明

正式比较只保留 6 种候选定位方法。`VisEdit-Contrib` 只使用 `Pre` 主版本，即适配 VisEdit adapter “插在贡献形成之前”的逻辑；`Direct-Alt` 和 `Pre-Delta` 不再作为正式方法单列。

| Method | 候选层生成方式 | 当前状态 |
|---|---|---|
| `Middle-layer Prior` | 按模型总层数的中层先验给出 Top-3 / Top-5 | 已登记 |
| `VisEdit-Contrib-Pre` | 对 `alt_first_token` 的模块贡献度做高贡献区识别，取高贡献区之前的层 | 已登记 |
| `SaLEM` | 用参数梯度显著性聚合到层级后排序 | 已回填 18/21；Qwen2.5-VL-3B 三个数据集 rc=1，待修复后重算 |
| `GoldenLayer / LGA` | 用 hidden-state gradient attribution 排序 | 待补 |
| `Perturb-KL-Direct` | 用层扰动 KL sensitivity 直接排序，取 KL 高敏感层 | 主扰动基线；待补 |
| `Ours-Pre` | 用 request-only visual gradient delta-LGA 找高分区，并取前置层 | 待补 |

附加 / 消融方法：`Perturb-KL-Pre` 使用同一套扰动 KL 分数，但把候选层前移；它不计入主扰动基线，后续单独报告消融结果。

说明：`4.9 当前可立即开跑的真实扫层并集` 保留为历史/当前运行记录；后续正式论文表格按 4.1-4.5 与 4.7 的 6 种主方法重新汇总，4.6 作为附加 / 消融。

### 4.9 当前可立即开跑的真实扫层并集

并集顺序按 `VisEdit-Contrib-Pre-Alt`、`VisEdit-Contrib-Direct-Alt`、`Middle-layer Prior` 依次加入并去重。

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

### 4.10 待补候选方法

本表保留为综合登记表：已算出的 SaLEM 结果仍保留在这里，未计算的 GoldenLayer / LGA、Perturb-KL-Direct、Ours-Pre 继续用 `pending` 占位，方便后续逐项回填。`Perturb-KL-Pre` 作为附加 / 消融方法也保留在本表中，但不作为主扰动基线。

| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | SaLEM | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L21 | done; n=500/500 |
| EVQA-pilot500 | BLIP2-OPT-2.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | SaLEM | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L20,L17 | done; n=500/500 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | SaLEM | mean_abs_param_grad_alt | L8,L9,L10 | L8,L9,L10,L5,L6 | done; n=500/500 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | SaLEM | mean_abs_param_grad_alt | L7,L6,L5 | L7,L6,L5,L8,L9 | done; n=500/500 |
| EVQA-pilot500 | LLaVA-v1.5-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | SaLEM | mean_abs_param_grad_alt | - | - | failed; rc=1 |
| EVQA-pilot500 | Qwen2.5-VL-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | SaLEM | mean_abs_param_grad_alt | L8,L7,L9 | L8,L7,L9,L10,L6 | done; n=500/500 |
| EVQA-pilot500 | PaliGemma-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | PaliGemma-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | SaLEM | mean_abs_param_grad_alt | L9,L8,L7 | L9,L8,L7,L6,L10 | done; n=500/500 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | SaLEM | mean_abs_param_grad_alt | L0,L18,L19 | L0,L18,L19,L17,L20 | done; n=214/214 |
| MMKE-visual | BLIP2-OPT-2.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | SaLEM | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L20,L16 | done; n=214/214 |
| MMKE-visual | InstructBLIP-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | SaLEM | mean_abs_param_grad_alt | L31,L5,L8 | L31,L5,L8,L6,L9 | done; n=214/214 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | SaLEM | mean_abs_param_grad_alt | L7,L8,L9 | L7,L8,L9,L6,L10 | done; n=214/214 |
| MMKE-visual | LLaVA-v1.5-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | SaLEM | mean_abs_param_grad_alt | - | - | failed; rc=1 |
| MMKE-visual | Qwen2.5-VL-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | PaliGemma-3B | SaLEM | mean_abs_param_grad_alt | L10,L8,L9 | L10,L8,L9,L7,L5 | done; n=214/214 |
| MMKE-visual | PaliGemma-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | PaliGemma-3B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | PaliGemma-3B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | PaliGemma-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | SaLEM | mean_abs_param_grad_alt | L9,L8,L0 | L9,L8,L0,L10,L7 | done; n=214/214 |
| MMKE-visual | SmolVLM-Instruct-1.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | SaLEM | mean_abs_param_grad_alt | L0,L18,L30 | L0,L18,L30,L19,L17 | done; n=636/636 |
| MMKE-entity | BLIP2-OPT-2.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | SaLEM | mean_abs_param_grad_alt | L18,L17,L19 | L18,L17,L19,L16,L20 | done; n=636/636 |
| MMKE-entity | InstructBLIP-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | SaLEM | mean_abs_param_grad_alt | L31,L22,L24 | L31,L22,L24,L21,L23 | done; n=636/636 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | SaLEM | mean_abs_param_grad_alt | L23,L22,L24 | L23,L22,L24,L25,L21 | done; n=636/636 |
| MMKE-entity | LLaVA-v1.5-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | SaLEM | mean_abs_param_grad_alt | - | - | failed; rc=1 |
| MMKE-entity | Qwen2.5-VL-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | PaliGemma-3B | SaLEM | mean_abs_param_grad_alt | L17,L16,L13 | L17,L16,L13,L0,L10 | done; n=636/636 |
| MMKE-entity | PaliGemma-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | PaliGemma-3B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | PaliGemma-3B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | PaliGemma-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | SaLEM | mean_abs_param_grad_alt | L0,L1,L6 | L0,L1,L6,L7,L5 | done; n=636/636 |
| MMKE-entity | SmolVLM-Instruct-1.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | Perturb-KL-Direct | layer perturbation KL sensitivity direct | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | Perturb-KL-Pre | layer perturbation KL sensitivity pre-shift ablation | - | - | pending; ablation |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |

### 4.11 本节候选层汇总

本小节只汇总候选层定位方法的计算状态；真实扫层训练/评测结果仍放在第 5 节。

| Method | 专题小节 | 覆盖范围 | 当前状态 | 后续动作 |
|---|---|---|---|---|
| Middle-layer Prior | 4.1 | 7 models，不区分数据集 | done | 可直接用于真实扫层比较 |
| VisEdit-Contrib-Pre | 4.2 | 7 models × 3 datasets | done | 可直接用于真实扫层比较 |
| SaLEM | 4.3 | 18/21 done | Qwen2.5-VL-3B 三个数据集 failed; rc=1 | 修复 Qwen 后重算 3 个失败项 |
| GoldenLayer / LGA | 4.4 | 0/21 done | pending | 按 LGA 手册计算并回填 |
| Perturb-KL-Direct | 4.5 | 0/21 done | pending | 主扰动基线；优先计算并回填 |
| Perturb-KL-Pre | 4.6 | 0/21 done | pending; ablation | 附加 / 消融；Direct 完成后再算 |
| Ours-Pre | 4.7 | 0/21 done | pending | 跑 request-only visual gradient delta-LGA 后回填 |
| Oracle Sweep | 第 5 节及后续真实扫层结果 | 已完成层逐步回填 | running / partial | 作为上界，不作为预测方法 |

## 5. 已完成真实扫层结果回填

本节只记录已经完成真实编辑训练与 full E-VQA eval/test 评测的结果。这里的结果用于后续计算不同定位方法的 `Best@3 / Best@5 / Regret@3 / Regret@5 / Hit@3 / Hit@5`。

### 5.1 EVQA-pilot500 / BLIP2-OPT-2.7B

结果来源：`md/Location/blip2_pliot500_epoch50_fulltest_layer_sweep_outcome.md`

训练与评测设置：

- 训练数据：`vqa_train_proxy500.json`。
- 评测数据：full E-VQA eval/test，共 `2093` 个样本。
- 训练轮数：每层 `50 epoch`。
- Checkpoint 选择：每层 minimum EMA loss。
- 流程隔离：每层评测独立 Python 进程，重新加载 base model 与当前层 adapter/hook。
- 特别说明：`L0` 使用原始有效 run；`L5/L10/L15/L19/L25/L30` 使用修复 wrapper 后的 fixed rerun；`L16/L17/L18/L20/L21/L24/L26/L29` 为后续补跑/补评结果。

| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L0 | 43 | 0.375991 | 0.368115 | 44.15 | 40.43 | 40.29 | 100.00 | 65.95 | 58.16 |
| L5 | 49 | 0.300460 | 0.396571 | 62.10 | 59.42 | 59.48 | 100.00 | 63.45 | 68.89 |
| L10 | 48 | 0.253585 | 0.299741 | 64.79 | 61.72 | 62.38 | 100.00 | 76.55 | 73.09 |
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
| VisEdit-Contrib-Pre | L20,L19,L18 | L19 | 74.85 | L20,L19,L18,L17,L16 | L17 | 75.60 | Top-5 命中当前已测最优层 |
| Middle-layer Prior | L17,L18,L16 | L17 | 75.60 | L17,L18,L16,L19,L15 | L17 | 75.60 | Top-3 命中当前已测最优层 |

### 5.2 EVQA-pilot500 / InstructBLIP-Vicuna-7B

结果来源：`downloads/contribution_pre_7_models/instructblip-vicuna-7b/full_eval_results_L28_L27_L26_merged.csv`

训练与评测设置：

- 训练数据：`vqa_train_proxy500.json`。
- 评测数据：full E-VQA eval/test，共 `2093` 个样本。
- 训练轮数：每层 `50 epoch`。
- Checkpoint 选择：每层 minimum EMA loss。
- 已完成层：`VisEdit-Contrib-Pre` 的 Top-3，即 `L28/L27/L26`。

| Layer | Ckpt Epoch | Raw Loss | EMA Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L28 | 49 | 1.700526 | 1.100682 | 29.86 | 28.72 | 28.78 | 100.00 | 79.00 | 53.27 |
| L27 | 36 | 0.274748 | 0.888490 | 29.64 | 28.66 | 28.71 | 100.00 | 74.34 | 52.27 |
| L26 | 50 | 0.202061 | 0.881081 | 29.65 | 28.92 | 27.94 | 100.00 | 70.70 | 51.44 |

当前已测 Top-3 中 full E-VQA `Average` 最高层为 `L28`，Average `53.27`。

候选方法回填：

| Method | Top-3 | Best@3 Layer | Best@3 Average | Top-5 | Best@5 Layer | Best@5 Average | 备注 |
|---|---|---:|---:|---|---:|---:|---|
| VisEdit-Contrib-Pre | L28,L27,L26 | L28 | 53.27 | L28,L27,L26,L25,L24 | L28 | 53.27 | 目前只完成 Top-3；L25/L24 待测 |
| Middle-layer Prior | L17,L18,L16 | - | - | L17,L18,L16,L19,L15 | - | - | 这些层尚未真实扫层 |

## 6. 真实扫层实验使用方式

1. 对每个 `dataset × model`，先取所有定位方法的 Top-3 并集做低预算真实扫层。
2. 再取所有定位方法的 Top-5 并集做完整候选层真实扫层。
3. 每个候选层使用完全相同的编辑训练配置，并记录 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average`。
4. 方法比较时按自己的 Top-K 集合回填真实扫层结果，报告 `Best@3 / Best@5 / Regret@3 / Regret@5 / Hit@3 / Hit@5`。
5. 跨数据集和跨模型汇总时使用 macro-average，避免样本量或层数不同导致结果偏置。

## 7. 注意

- PaliGemma-3B 在 MMKE 上的贡献度绝对值很小，候选层仍按相同规则给出，但真实编辑比较时建议标记为 low-confidence contribution。
- Qwen2.5-VL 做后续 visual token 梯度或编辑实验时，需要固定输入分辨率，避免视觉 token 数随图片尺寸变化。
- EVQA-pilot500 的 BLIP2 结果来自单独 BLIP2 pilot500 目录，其余 6 个模型来自 crossmodel pilot500 目录。



