# 真实扫层实验候选编辑层清单

本文档记录后续真实扫层实验要比较的候选编辑层。当前已计算完成的是 `VisEdit-Contrib-Pre-Alt`：使用我们已经完成的 7 个模型在 `EVQA-pilot500`、`MMKE-visual`、`MMKE-entity` 上对关键 token `alt` 的贡献度分析结果。

## 1. 统一规则

- 层编号：0-indexed，例如 `L0` 到 `L31`。
- key token：`alt_first_token`，即新知识 / 目标答案的首个 token。
- 排序指标：`score_positive = max(0, attn_mean) + max(0, mlp_mean)`。
- 高贡献区识别：对 `score_positive` 做 3 层平滑，阈值为 `mean + 0.5 * std`，取最长连续高贡献区间。
- VisEdit-Pre 候选规则：若高贡献区间起始层为 `s_H`，则 `Top-K = {s_H-1, s_H-2, ..., s_H-K}`。
- 本文档中的 Top-3 / Top-5 是编辑插入层候选，不是贡献峰值层。

## 2. VisEdit-Contrib-Pre-Alt 候选层

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

该方法不依赖数据集，因此同一模型在三个数据集上的候选层相同。默认 `rho=0.55`。

| Model | L | Top-3 | Top-5 |
|---|---:|---|---|
| BLIP2-OPT-2.7B | 32 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| InstructBLIP-Vicuna-7B | 32 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| MiniGPT-4-Vicuna-7B | 32 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| LLaVA-v1.5-7B | 32 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| Qwen2.5-VL-3B | 36 | L19,L20,L18 | L19,L20,L18,L21,L17 |
| PaliGemma-3B | 18 | L9,L10,L8 | L9,L10,L8,L11,L7 |
| SmolVLM-Instruct-1.7B | 24 | L13,L12,L14 | L13,L12,L14,L11,L15 |

### 4.2 VisEdit-Contrib-Direct-Alt

该方法直接按 `score_positive` 从高到低取贡献峰值层，作为和 Pre 规则对比的消融。

| Dataset | Model | Top-3 | Top-5 |
|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L25,L24,L26 | L25,L24,L26,L29,L22 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L30,L31,L28 | L30,L31,L28,L22,L29 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L28,L31,L30 | L28,L31,L30,L27,L25 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L30,L31,L29 | L30,L31,L29,L28,L27 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L31,L35,L26 | L31,L35,L26,L34,L33 |
| EVQA-pilot500 | PaliGemma-3B | L15,L14,L12 | L15,L14,L12,L16,L17 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L22,L19,L21 | L22,L19,L21,L18,L23 |
| MMKE-visual | BLIP2-OPT-2.7B | L26,L29,L24 | L26,L29,L24,L28,L27 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L30,L31,L22 | L30,L31,L22,L25,L27 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L28,L31,L27 | L28,L31,L27,L16,L30 |
| MMKE-visual | LLaVA-v1.5-7B | L30,L31,L29 | L30,L31,L29,L25,L28 |
| MMKE-visual | Qwen2.5-VL-3B | L31,L29,L30 | L31,L29,L30,L34,L35 |
| MMKE-visual | PaliGemma-3B | L14,L11,L17 | L14,L11,L17,L15,L16 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L20,L19,L21 | L20,L19,L21,L23,L18 |
| MMKE-entity | BLIP2-OPT-2.7B | L29,L24,L26 | L29,L24,L26,L4,L27 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L30,L31,L29 | L30,L31,L29,L10,L28 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L28,L31,L27 | L28,L31,L27,L16,L25 |
| MMKE-entity | LLaVA-v1.5-7B | L30,L25,L31 | L30,L25,L31,L29,L27 |
| MMKE-entity | Qwen2.5-VL-3B | L34,L35,L31 | L34,L35,L31,L27,L25 |
| MMKE-entity | PaliGemma-3B | L15,L16,L17 | L15,L16,L17,L11,L0 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L23,L21,L20 | L23,L21,L20,L16,L15 |

### 4.3 当前可立即开跑的真实扫层并集

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

### 4.4 待补候选方法

| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status |
|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | PaliGemma-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | SaLEM | parameter gradient saliency | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | PaliGemma-3B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | PaliGemma-3B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | PaliGemma-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | PaliGemma-3B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | PaliGemma-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | PaliGemma-3B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | PaliGemma-3B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | PaliGemma-3B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | PaliGemma-3B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | PaliGemma-3B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | VisEdit-Contrib-Pre-Delta | alt-pred contribution delta | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | SaLEM | parameter gradient saliency | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | GoldenLayer/LGA | hidden-state gradient attribution | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | Perturb-KL-Pre | layer perturbation KL sensitivity | - | - | pending |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Pre | request-only visual gradient delta-LGA | - | - | pending |

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
