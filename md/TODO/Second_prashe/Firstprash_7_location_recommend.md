# 第一阶段七种定位方法：21组 Top-3 / Top-5 候选层与两版 CMA 并集

> 生成日期：2026-09-17。本文是候选层的完整提取表，不以层是否已完成Adapter评测为筛选条件，避免漏掉待补、失败或低覆盖候选。

## 1. 口径与版本边界

每套正式比较都只有七种方法：前六种方法固定，第七种CMA按版本二选一。本文同时保留两版CMA，因此展示时共有8个“版本化方法行”，但不得把两版CMA同时并入同一个七方法并集。

固定的六种方法：

1. `Middle-Prior-Direct`
2. `VisEdit-Contrib-Pre-KeyToken`
3. `SaLEM-Alt-Direct`
4. `LGA-Param-Direct-AltModelPred`
5. `Perturb-KL-Direct-AltSeq`
6. `Ours-Direct`：只采用正式主公式 `M_abscos_x_newn`

CMA二选一版本：

- `CMA-Direct-v1.3-alt`：历史协议，恢复目标为反事实新答案 `alt`；历史低覆盖结果原样保留。
- `CMA-ModelPred-Direct-v2`：当前正式协议，恢复目标为冻结基础模型确定性输出的完整 `model_pred`；用于新版七方法比较。

禁止跨CMA版本取最大值、拼接候选层或混合计算指标。旧版与新版分别形成一套七方法Top-3/Top-5并集。

## 2. 数据来源与实验交叉核验

- 主手册：`md/Location/6location_7model_3datas_top_3_5_layers_outcome.md`。
- 历史七方法逐方法表：`outputs/formal7_method_topk_performance_20260801.csv`，147行 = 7方法 × 21组合。
- 历史CMA-alt并集：`outputs/formal7_M_abscos_x_newn_top3_top5_union_status_20260801.csv`。
- 新版CMA-ModelPred并集：`outputs/formal7_cma_modelpred_v2_top3_top5_union_status_20260914.csv`。
- 五种基线与Ours主公式的实验候选源：`md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/baseline_candidates.csv`、`formula_topk_all_21.csv`。
- CMA-ModelPred服务器实验已于2026-09-12完成21/21组合；本文直接读取主手册2.8.1中由正式实验回填的21行Top-3、Top-5、覆盖率和稳定性。
- 历史CMA候选逐行与主手册2.8历史表核对；两版七方法并集均由逐方法候选重新计算，并与对应机器可读并集CSV逐字段核对。

## 3. 各方法在21组上的Top-3与Top-5

### 3.1 Middle-Prior-Direct

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16 | L17,L18,L16,L19,L15 | - |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7 | L8,L9,L7,L10,L6 | - |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10 | L11,L12,L10,L13,L9 | - |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16 | L17,L18,L16,L19,L15 | - |
| MMKE-visual | PaliGemma-3B | L8,L9,L7 | L8,L9,L7,L10,L6 | - |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10 | L11,L12,L10,L13,L9 | - |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14 | L15,L16,L14,L17,L13 | - |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16 | L17,L18,L16,L19,L15 | - |
| MMKE-entity | PaliGemma-3B | L8,L9,L7 | L8,L9,L7,L10,L6 | - |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10 | L11,L12,L10,L13,L9 | - |

### 3.2 VisEdit-Contrib-Pre-KeyToken

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L20,L19,L18 | L20,L19,L18,L17,L16 | - |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L26,L25,L24 | L26,L25,L24,L23,L22 | - |
| EVQA-pilot500 | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| EVQA-pilot500 | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | - |
| EVQA-pilot500 | PaliGemma-3B | L12,L11,L10 | L12,L11,L10,L9,L8 | - |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L17,L16,L15 | L17,L16,L15,L14,L13 | - |
| MMKE-visual | BLIP2-OPT-2.7B | L26,L25,L24 | L26,L25,L24,L23,L22 | - |
| MMKE-visual | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L26,L25,L24 | L26,L25,L24,L23,L22 | - |
| MMKE-visual | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| MMKE-visual | Qwen2.5-VL-3B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| MMKE-visual | PaliGemma-3B | L14,L13,L12 | L14,L13,L12,L11,L10 | - |
| MMKE-visual | SmolVLM-Instruct-1.7B | L18,L17,L16 | L18,L17,L16,L15,L14 | - |
| MMKE-entity | BLIP2-OPT-2.7B | L22,L21,L20 | L22,L21,L20,L19,L18 | - |
| MMKE-entity | InstructBLIP-Vicuna-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L25,L24,L23 | L25,L24,L23,L22,L21 | - |
| MMKE-entity | LLaVA-v1.5-7B | L28,L27,L26 | L28,L27,L26,L25,L24 | - |
| MMKE-entity | Qwen2.5-VL-3B | L29,L28,L27 | L29,L28,L27,L26,L25 | - |
| MMKE-entity | PaliGemma-3B | L12,L11,L10 | L12,L11,L10,L9,L8 | - |
| MMKE-entity | SmolVLM-Instruct-1.7B | L18,L17,L16 | L18,L17,L16,L15,L14 | - |

### 3.3 SaLEM-Alt-Direct

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L0,L18,L19 | L0,L18,L19,L17,L21 | - |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L0,L18,L19 | L0,L18,L19,L20,L17 | - |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L8,L9,L10 | L8,L9,L10,L5,L6 | - |
| EVQA-pilot500 | LLaVA-v1.5-7B | L7,L6,L5 | L7,L6,L5,L8,L9 | - |
| EVQA-pilot500 | Qwen2.5-VL-3B | L11,L14,L12 | L11,L14,L12,L13,L15 | - |
| EVQA-pilot500 | PaliGemma-3B | L8,L7,L9 | L8,L7,L9,L10,L6 | - |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L9,L8,L7 | L9,L8,L7,L6,L10 | - |
| MMKE-visual | BLIP2-OPT-2.7B | L0,L18,L19 | L0,L18,L19,L17,L20 | - |
| MMKE-visual | InstructBLIP-Vicuna-7B | L18,L17,L19 | L18,L17,L19,L20,L16 | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L31,L5,L8 | L31,L5,L8,L6,L9 | - |
| MMKE-visual | LLaVA-v1.5-7B | L7,L8,L9 | L7,L8,L9,L6,L10 | - |
| MMKE-visual | Qwen2.5-VL-3B | L12,L11,L14 | L12,L11,L14,L15,L13 | - |
| MMKE-visual | PaliGemma-3B | L10,L8,L9 | L10,L8,L9,L7,L5 | - |
| MMKE-visual | SmolVLM-Instruct-1.7B | L9,L8,L0 | L9,L8,L0,L10,L7 | - |
| MMKE-entity | BLIP2-OPT-2.7B | L0,L18,L30 | L0,L18,L30,L19,L17 | - |
| MMKE-entity | InstructBLIP-Vicuna-7B | L18,L17,L19 | L18,L17,L19,L16,L20 | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L31,L22,L24 | L31,L22,L24,L21,L23 | - |
| MMKE-entity | LLaVA-v1.5-7B | L23,L22,L24 | L23,L22,L24,L25,L21 | - |
| MMKE-entity | Qwen2.5-VL-3B | L15,L14,L13 | L15,L14,L13,L16,L12 | - |
| MMKE-entity | PaliGemma-3B | L17,L16,L13 | L17,L16,L13,L0,L10 | - |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0,L1,L6 | L0,L1,L6,L7,L5 | - |

### 3.4 LGA-Param-Direct-AltModelPred

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L0,L1,L3 | L0,L1,L3,L4,L16 | - |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L2,L0,L1 | L2,L0,L1,L4,L17 | - |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L29,L25,L22 | L29,L25,L22,L26,L21 | - |
| EVQA-pilot500 | LLaVA-v1.5-7B | L24,L25,L26 | L24,L25,L26,L23,L27 | - |
| EVQA-pilot500 | Qwen2.5-VL-3B | L2,L30,L1 | L2,L30,L1,L3,L10 | - |
| EVQA-pilot500 | PaliGemma-3B | L17,L7,L0 | L17,L7,L0,L8,L13 | - |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L22,L21,L20 | L22,L21,L20,L19,L18 | - |
| MMKE-visual | BLIP2-OPT-2.7B | L0,L1,L3 | L0,L1,L3,L4,L2 | - |
| MMKE-visual | InstructBLIP-Vicuna-7B | L2,L0,L4 | L2,L0,L4,L28,L1 | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0,L1,L3 | L0,L1,L3,L4,L25 | - |
| MMKE-visual | LLaVA-v1.5-7B | L24,L22,L27 | L24,L22,L27,L25,L23 | - |
| MMKE-visual | Qwen2.5-VL-3B | L2,L30,L1 | L2,L30,L1,L3,L6 | - |
| MMKE-visual | PaliGemma-3B | L17,L0,L7 | L17,L0,L7,L8,L10 | - |
| MMKE-visual | SmolVLM-Instruct-1.7B | L1,L7,L6 | L1,L7,L6,L8,L5 | - |
| MMKE-entity | BLIP2-OPT-2.7B | L16,L13,L18 | L16,L13,L18,L17,L15 | - |
| MMKE-entity | InstructBLIP-Vicuna-7B | L2,L28,L0 | L2,L28,L0,L4,L30 | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L4,L3,L6 | L4,L3,L6,L0,L1 | - |
| MMKE-entity | LLaVA-v1.5-7B | L1,L9,L7 | L1,L9,L7,L8,L6 | - |
| MMKE-entity | Qwen2.5-VL-3B | L2,L30,L1 | L2,L30,L1,L6,L3 | - |
| MMKE-entity | PaliGemma-3B | L17,L16,L7 | L17,L16,L7,L8,L13 | - |
| MMKE-entity | SmolVLM-Instruct-1.7B | L1,L7,L0 | L1,L7,L0,L6,L8 | - |

### 3.5 Perturb-KL-Direct-AltSeq

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L3,L4,L2 | L3,L4,L2,L1,L5 | - |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L2,L3,L4 | L2,L3,L4,L5,L6 | - |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| EVQA-pilot500 | Qwen2.5-VL-3B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| EVQA-pilot500 | PaliGemma-3B | L5,L7,L6 | L5,L7,L6,L3,L4 | - |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L1,L2,L0 | L1,L2,L0,L4,L3 | - |
| MMKE-visual | BLIP2-OPT-2.7B | L3,L4,L2 | L3,L4,L2,L1,L5 | - |
| MMKE-visual | InstructBLIP-Vicuna-7B | L2,L3,L5 | L2,L3,L5,L4,L8 | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-visual | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-visual | Qwen2.5-VL-3B | L0,L13,L14 | L0,L13,L14,L12,L15 | - |
| MMKE-visual | PaliGemma-3B | L7,L5,L6 | L7,L5,L6,L8,L9 | - |
| MMKE-visual | SmolVLM-Instruct-1.7B | L1,L4,L0 | L1,L4,L0,L2,L5 | - |
| MMKE-entity | BLIP2-OPT-2.7B | L3,L2,L4 | L3,L2,L4,L1,L0 | - |
| MMKE-entity | InstructBLIP-Vicuna-7B | L5,L4,L3 | L5,L4,L3,L2,L8 | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-entity | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-entity | Qwen2.5-VL-3B | L0,L1,L2 | L0,L1,L2,L3,L14 | - |
| MMKE-entity | PaliGemma-3B | L7,L5,L6 | L7,L5,L6,L8,L9 | - |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |

### 3.6 Ours-Direct（M_abscos_x_newn）

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L11 | L1,L0,L11,L9,L10 | - |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L18,L19,L16 | L18,L19,L16,L17,L21 | - |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| EVQA-pilot500 | Qwen2.5-VL-3B | L21,L19,L17 | L21,L19,L17,L20,L18 | - |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L3 | L5,L4,L3,L6,L7 | - |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-visual | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2,L4,L3 | - |
| MMKE-visual | InstructBLIP-Vicuna-7B | L1,L0,L3 | L1,L0,L3,L2,L4 | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L9,L10,L11 | L9,L10,L11,L15,L14 | - |
| MMKE-visual | LLaVA-v1.5-7B | L0,L3,L1 | L0,L3,L1,L2,L5 | - |
| MMKE-visual | Qwen2.5-VL-3B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-visual | PaliGemma-3B | L5,L4,L3 | L5,L4,L3,L2,L1 | - |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-entity | BLIP2-OPT-2.7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |
| MMKE-entity | InstructBLIP-Vicuna-7B | L1,L0,L3 | L1,L0,L3,L2,L4 | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L27,L28,L26 | L27,L28,L26,L25,L29 | - |
| MMKE-entity | LLaVA-v1.5-7B | L13,L11,L12 | L13,L11,L12,L10,L9 | - |
| MMKE-entity | Qwen2.5-VL-3B | L0,L1,L2 | L0,L1,L2,L3,L6 | - |
| MMKE-entity | PaliGemma-3B | L5,L4,L3 | L5,L4,L3,L2,L6 | - |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L3,L4 | - |

### 3.7 CMA-Direct v1.3（历史alt目标）

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L4,L2,L5 | L4,L2,L5,L3,L1 | done; n=389/500; coverage=0.7780 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L25 | L1,L0,L25,L22,L2 | done; n=421/500; coverage=0.8420 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L7,L1,L0 | L7,L1,L0,L2,L8 | done; n=285/500; coverage=0.5700 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L4 | L0,L1,L4,L6,L10 | done; n=397/500; coverage=0.7940 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L1,L0,L3 | L1,L0,L3,L6,L4 | done; n=239/500; coverage=0.4780 |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L0 | L5,L4,L0,L3,L2 | done; n=215/500; coverage=0.4300 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0,L1,L3 | L0,L1,L3,L2,L6 | done; n=293/500; coverage=0.5860 |
| MMKE-visual | BLIP2-OPT-2.7B | L3,L0,L1 | L3,L0,L1,L2,L4 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L23,L22,L24 | L23,L22,L24,L19,L17 | done; n=212/214; coverage=0.9907 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=50/214; coverage=0.2336 |
| MMKE-visual | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=207/214; coverage=0.9673 |
| MMKE-visual | Qwen2.5-VL-3B | L1,L0,L6 | L1,L0,L6,L7,L3 | done; n=31/214; coverage=0.1449 |
| MMKE-visual | PaliGemma-3B | L1,L2,L0 | L1,L2,L0,L3,L5 | done; n=76/214; coverage=0.3551 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L15 | L0,L1,L15,L2,L7 | done; n=140/214; coverage=0.6542 |
| MMKE-entity | BLIP2-OPT-2.7B | L3,L0,L2 | L3,L0,L2,L4,L1 | done; n=634/636; coverage=0.9969 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L23,L24,L22 | L23,L24,L22,L19,L17 | done; n=630/636; coverage=0.9906 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=97/636; coverage=0.1525 |
| MMKE-entity | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | done; n=632/636; coverage=0.9937 |
| MMKE-entity | Qwen2.5-VL-3B | L1,L0,L2 | L1,L0,L2,L3,L6 | low_confidence; n=9/636; coverage=0.0142 |
| MMKE-entity | PaliGemma-3B | L0,L2,L1 | L0,L2,L1,L3,L7 | done; n=125/636; coverage=0.1965 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L15,L18,L16 | L15,L18,L16,L19,L14 | done; n=544/636; coverage=0.8553 |

### 3.8 CMA-ModelPred-Direct v2（正式model_pred目标）

| 数据集 | 模型 | Top-3 | Top-5 | 覆盖/状态注释 |
|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L2,L1,L0 | L2,L1,L0,L3,L4 | ModelPred可用=465/500；CMA有效=465/465；总体覆盖率=93.00%；有效参数对=3461/4185（82.70%）；stable |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L2 | L1,L0,L2,L21,L22 | ModelPred可用=500/500；CMA有效=496/500；总体覆盖率=99.20%；有效参数对=3644/4500（80.98%）；stable |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | ModelPred可用=499/500；CMA有效=497/499；总体覆盖率=99.40%；有效参数对=3058/4491（68.09%）；stable |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | ModelPred可用=500/500；CMA有效=500/500；总体覆盖率=100.00%；有效参数对=3984/4500（88.53%）；stable |
| EVQA-pilot500 | Qwen2.5-VL-3B | L1,L0,L15 | L1,L0,L15,L8,L5 | ModelPred可用=500/500；CMA有效=354/500；总体覆盖率=70.80%；有效参数对=1520/4500（33.78%）；unstable; mean Top-3 Jaccard=0.3667 |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L7 | L5,L4,L7,L0,L6 | ModelPred可用=500/500；CMA有效=410/500；总体覆盖率=82.00%；有效参数对=1578/4500（35.07%）；stable |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0,L1,L5 | L0,L1,L5,L4,L8 | ModelPred可用=500/500；CMA有效=497/500；总体覆盖率=99.40%；有效参数对=3335/4500（74.11%）；unstable; mean Top-3 Jaccard=0.2889 |
| MMKE-visual | BLIP2-OPT-2.7B | L2,L0,L3 | L2,L0,L3,L1,L4 | ModelPred可用=175/214；CMA有效=175/175；总体覆盖率=81.78%；有效参数对=1317/1575（83.62%）；stable |
| MMKE-visual | InstructBLIP-Vicuna-7B | L1,L25,L22 | L1,L25,L22,L23,L21 | ModelPred可用=214/214；CMA有效=214/214；总体覆盖率=100.00%；有效参数对=1394/1926（72.38%）；stable |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | ModelPred可用=214/214；CMA有效=214/214；总体覆盖率=100.00%；有效参数对=1418/1926（73.62%）；stable |
| MMKE-visual | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | ModelPred可用=214/214；CMA有效=214/214；总体覆盖率=100.00%；有效参数对=1844/1926（95.74%）；stable |
| MMKE-visual | Qwen2.5-VL-3B | L1,L0,L2 | L1,L0,L2,L3,L4 | ModelPred可用=214/214；CMA有效=154/214；总体覆盖率=71.96%；有效参数对=583/1926（30.27%）；stable |
| MMKE-visual | PaliGemma-3B | L7,L6,L4 | L7,L6,L4,L5,L3 | ModelPred可用=214/214；CMA有效=166/214；总体覆盖率=77.57%；有效参数对=570/1926（29.60%）；unstable; mean Top-3 Jaccard=0.2556 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L1,L0,L5 | L1,L0,L5,L2,L6 | ModelPred可用=214/214；CMA有效=213/214；总体覆盖率=99.53%；有效参数对=1457/1926（75.65%）；unstable; mean Top-3 Jaccard=0.4333 |
| MMKE-entity | BLIP2-OPT-2.7B | L2,L3,L1 | L2,L3,L1,L7,L10 | ModelPred可用=284/636；CMA有效=284/284；总体覆盖率=44.65%；有效参数对=2338/2556（91.47%）；stable; ModelPred可用率低 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L26,L25,L22 | L26,L25,L22,L21,L23 | ModelPred可用=636/636；CMA有效=627/636；总体覆盖率=98.58%；有效参数对=3628/5724（63.38%）；stable |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2,L3,L4 | ModelPred可用=636/636；CMA有效=636/636；总体覆盖率=100.00%；有效参数对=4159/5724（72.66%）；stable |
| MMKE-entity | LLaVA-v1.5-7B | L0,L1,L4 | L0,L1,L4,L3,L2 | ModelPred可用=636/636；CMA有效=636/636；总体覆盖率=100.00%；有效参数对=5283/5724（92.30%）；stable |
| MMKE-entity | Qwen2.5-VL-3B | L1,L0,L20 | L1,L0,L20,L22,L2 | ModelPred可用=636/636；CMA有效=360/636；总体覆盖率=56.60%；有效参数对=1161/5724（20.28%）；stable; formal |
| MMKE-entity | PaliGemma-3B | L7,L6,L5 | L7,L6,L5,L4,L2 | ModelPred可用=636/636；CMA有效=559/636；总体覆盖率=87.89%；有效参数对=2385/5724（41.67%）；stable |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0,L1,L2 | L0,L1,L2,L9,L7 | ModelPred可用=636/636；CMA有效=631/636；总体覆盖率=99.21%；有效参数对=3909/5724（68.29%）；stable |

## 4. 21组数据集×模型：七方法候选层与两版并集

每个组合先列固定六方法，再分别列历史CMA-alt和正式CMA-ModelPred。其后两行并集分别对应两套七方法版本。

### 4.1 EVQA-pilot500 × BLIP2-OPT-2.7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L20,L19,L18 | L20,L19,L18,L17,L16 |
| SaLEM-Alt-Direct | 固定方法 | L0,L18,L19 | L0,L18,L19,L17,L21 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L0,L1,L3 | L0,L1,L3,L4,L16 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L3,L4,L2 | L3,L4,L2,L1,L5 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L4,L2,L5 | L4,L2,L5,L3,L1 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L2,L1,L0 | L2,L1,L0,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2 | 11 | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 |

### 4.2 EVQA-pilot500 × InstructBLIP-Vicuna-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L0,L18,L19 | L0,L18,L19,L20,L17 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L2,L0,L1 | L2,L0,L1,L4,L17 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L2,L3,L4 | L2,L3,L4,L5,L6 |
| Ours-Direct | 固定方法 | L1,L0,L11 | L1,L0,L11,L9,L10 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L1,L0,L25 | L1,L0,L25,L22,L2 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L1,L0,L2 | L1,L0,L2,L21,L22 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L22 | 24 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11 | 14 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L21,L22 | 25 |

### 4.3 EVQA-pilot500 × MiniGPT-4-Vicuna-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L26,L25,L24 | L26,L25,L24,L23,L22 |
| SaLEM-Alt-Direct | 固定方法 | L8,L9,L10 | L8,L9,L10,L5,L6 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L29,L25,L22 | L29,L25,L22,L26,L21 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L18,L19,L16 | L18,L19,L16,L17,L21 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L7,L1,L0 | L7,L1,L0,L2,L8 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L2 | L0,L1,L2,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19,L7 | 25 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19 | 16 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19 | 24 |

### 4.4 EVQA-pilot500 × LLaVA-v1.5-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L7,L6,L5 | L7,L6,L5,L8,L9 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L24,L25,L26 | L24,L25,L26,L23,L27 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L4 | L0,L1,L4,L6,L10 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L2 | L0,L1,L2,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4 | 15 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 22 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2 | 14 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4 | 21 |

### 4.5 EVQA-pilot500 × Qwen2.5-VL-3B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L29,L28,L27 | L29,L28,L27,L26,L25 |
| SaLEM-Alt-Direct | 固定方法 | L11,L14,L12 | L11,L14,L12,L13,L15 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L2,L30,L1 | L2,L30,L1,L3,L10 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L21,L19,L17 | L21,L19,L17,L20,L18 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L1,L0,L3 | L1,L0,L3,L6,L4 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L1,L0,L15 | L1,L0,L15,L8,L5 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L6 | 24 |
| 正式 CMA-ModelPred v2 | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L15 | 16 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L8,L5 | 25 |

### 4.6 EVQA-pilot500 × PaliGemma-3B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L8,L9,L7 | L8,L9,L7,L10,L6 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L12,L11,L10 | L12,L11,L10,L9,L8 |
| SaLEM-Alt-Direct | 固定方法 | L8,L7,L9 | L8,L7,L9,L10,L6 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L17,L7,L0 | L17,L7,L0,L8,L13 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L5,L7,L6 | L5,L7,L6,L3,L4 |
| Ours-Direct | 固定方法 | L5,L4,L3 | L5,L4,L3,L6,L7 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L5,L4,L0 | L5,L4,L0,L3,L2 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L5,L4,L7 | L5,L4,L7,L0,L6 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4,L2 | 14 |
| 正式 CMA-ModelPred v2 | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4 | 13 |

### 4.7 EVQA-pilot500 × SmolVLM-Instruct-1.7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L11,L12,L10 | L11,L12,L10,L13,L9 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L17,L16,L15 | L17,L16,L15,L14,L13 |
| SaLEM-Alt-Direct | 固定方法 | L9,L8,L7 | L9,L8,L7,L6,L10 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L22,L21,L20 | L22,L21,L20,L19,L18 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L1,L2,L0 | L1,L2,L0,L4,L3 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L3 | L0,L1,L3,L2,L6 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L5 | L0,L1,L5,L4,L8 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3 | 22 |
| 正式 CMA-ModelPred v2 | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L5 | 16 | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3,L5 | 23 |

### 4.8 MMKE-visual × BLIP2-OPT-2.7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L26,L25,L24 | L26,L25,L24,L23,L22 |
| SaLEM-Alt-Direct | 固定方法 | L0,L18,L19 | L0,L18,L19,L17,L20 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L0,L1,L3 | L0,L1,L3,L4,L2 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L3,L4,L2 | L3,L4,L2,L1,L5 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L4,L3 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L3,L0,L1 | L3,L0,L1,L2,L4 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L2,L0,L3 | L2,L0,L3,L1,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 |

### 4.9 MMKE-visual × InstructBLIP-Vicuna-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L18,L17,L19 | L18,L17,L19,L20,L16 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L2,L0,L4 | L2,L0,L4,L28,L1 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L2,L3,L5 | L2,L3,L5,L4,L8 |
| Ours-Direct | 固定方法 | L1,L0,L3 | L1,L0,L3,L2,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L23,L22,L24 | L23,L22,L24,L19,L17 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L1,L25,L22 | L1,L25,L22,L23,L21 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L23,L22 | 22 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L25,L22 | 17 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L22,L23,L21 | 23 |

### 4.10 MMKE-visual × MiniGPT-4-Vicuna-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L26,L25,L24 | L26,L25,L24,L23,L22 |
| SaLEM-Alt-Direct | 固定方法 | L31,L5,L8 | L31,L5,L8,L6,L9 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L0,L1,L3 | L0,L1,L3,L4,L25 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L9,L10,L11 | L9,L10,L11,L15,L14 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L2 | L0,L1,L2,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 |

### 4.11 MMKE-visual × LLaVA-v1.5-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L7,L8,L9 | L7,L8,L9,L6,L10 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L24,L22,L27 | L24,L22,L27,L25,L23 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L0,L3,L1 | L0,L3,L1,L2,L5 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L2 | L0,L1,L2,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 |

### 4.12 MMKE-visual × Qwen2.5-VL-3B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L12,L11,L14 | L12,L11,L14,L15,L13 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L2,L30,L1 | L2,L30,L1,L3,L6 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L13,L14 | L0,L13,L14,L12,L15 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L1,L0,L6 | L1,L0,L6,L7,L3 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L1,L0,L2 | L1,L0,L2,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4,L7 | 22 |
| 正式 CMA-ModelPred v2 | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13 | 14 | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4 | 21 |

### 4.13 MMKE-visual × PaliGemma-3B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L8,L9,L7 | L8,L9,L7,L10,L6 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L14,L13,L12 | L14,L13,L12,L11,L10 |
| SaLEM-Alt-Direct | 固定方法 | L10,L8,L9 | L10,L8,L9,L7,L5 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L17,L0,L7 | L17,L0,L7,L8,L10 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L7,L5,L6 | L7,L5,L6,L8,L9 |
| Ours-Direct | 固定方法 | L5,L4,L3 | L5,L4,L3,L2,L1 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L1,L2,L0 | L1,L2,L0,L3,L5 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L7,L6,L4 | L7,L6,L4,L5,L3 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3,L1,L2 | 15 | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 |
| 正式 CMA-ModelPred v2 | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3 | 13 | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 |

### 4.14 MMKE-visual × SmolVLM-Instruct-1.7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L11,L12,L10 | L11,L12,L10,L13,L9 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L18,L17,L16 | L18,L17,L16,L15,L14 |
| SaLEM-Alt-Direct | 固定方法 | L9,L8,L0 | L9,L8,L0,L10,L7 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L1,L7,L6 | L1,L7,L6,L8,L5 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L1,L4,L0 | L1,L4,L0,L2,L5 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L15 | L0,L1,L15,L2,L7 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L1,L0,L5 | L1,L0,L5,L2,L6 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 |
| 正式 CMA-ModelPred v2 | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L5 | 15 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 |

### 4.15 MMKE-entity × BLIP2-OPT-2.7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L22,L21,L20 | L22,L21,L20,L19,L18 |
| SaLEM-Alt-Direct | 固定方法 | L0,L18,L30 | L0,L18,L30,L19,L17 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L16,L13,L18 | L16,L13,L18,L17,L15 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L3,L2,L4 | L3,L2,L4,L1,L0 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L3,L0,L2 | L3,L0,L2,L4,L1 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L2,L3,L1 | L2,L3,L1,L7,L10 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1,L7,L10 | 18 |

### 4.16 MMKE-entity × InstructBLIP-Vicuna-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L18,L17,L19 | L18,L17,L19,L16,L20 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L2,L28,L0 | L2,L28,L0,L4,L30 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L5,L4,L3 | L5,L4,L3,L2,L8 |
| Ours-Direct | 固定方法 | L1,L0,L3 | L1,L0,L3,L2,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L23,L24,L22 | L23,L24,L22,L19,L17 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L26,L25,L22 | L26,L25,L22,L21,L23 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L23,L22 | 23 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L25,L22 | 17 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L22,L21,L23 | 24 |

### 4.17 MMKE-entity × MiniGPT-4-Vicuna-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L25,L24,L23 | L25,L24,L23,L22,L21 |
| SaLEM-Alt-Direct | 固定方法 | L31,L22,L24 | L31,L22,L24,L21,L23 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L4,L3,L6 | L4,L3,L6,L0,L1 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L27,L28,L26 | L27,L28,L26,L25,L29 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L2 | L0,L1,L2,L3,L4 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 |

### 4.18 MMKE-entity × LLaVA-v1.5-7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L15,L16,L14 | L15,L16,L14,L17,L13 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| SaLEM-Alt-Direct | 固定方法 | L23,L22,L24 | L23,L22,L24,L25,L21 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L1,L9,L7 | L1,L9,L7,L8,L6 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L13,L11,L12 | L13,L11,L12,L10,L9 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L4 | L0,L1,L4,L3,L2 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 17 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 |
| 正式 CMA-ModelPred v2 | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12,L4 | 18 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 |

### 4.19 MMKE-entity × Qwen2.5-VL-3B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L17,L18,L16 | L17,L18,L16,L19,L15 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L29,L28,L27 | L29,L28,L27,L26,L25 |
| SaLEM-Alt-Direct | 固定方法 | L15,L14,L13 | L15,L14,L13,L16,L12 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L2,L30,L1 | L2,L30,L1,L6,L3 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L14 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L6 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L1,L0,L2 | L1,L0,L2,L3,L6 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L1,L0,L20 | L1,L0,L20,L22,L2 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0 | 19 |
| 正式 CMA-ModelPred v2 | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L20 | 14 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0,L20,L22 | 21 |

### 4.20 MMKE-entity × PaliGemma-3B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L8,L9,L7 | L8,L9,L7,L10,L6 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L12,L11,L10 | L12,L11,L10,L9,L8 |
| SaLEM-Alt-Direct | 固定方法 | L17,L16,L13 | L17,L16,L13,L0,L10 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L17,L16,L7 | L17,L16,L7,L8,L13 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L7,L5,L6 | L7,L5,L6,L8,L9 |
| Ours-Direct | 固定方法 | L5,L4,L3 | L5,L4,L3,L2,L6 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L0,L2,L1 | L0,L2,L1,L3,L7 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L7,L6,L5 | L7,L6,L5,L4,L2 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 |
| 正式 CMA-ModelPred v2 | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3 | 13 | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2 | 15 |

### 4.21 MMKE-entity × SmolVLM-Instruct-1.7B

| 方法 | 版本角色 | Top-3 | Top-5 |
|---|---|---|---|
| Middle-Prior-Direct | 固定方法 | L11,L12,L10 | L11,L12,L10,L13,L9 |
| VisEdit-Contrib-Pre-KeyToken | 固定方法 | L18,L17,L16 | L18,L17,L16,L15,L14 |
| SaLEM-Alt-Direct | 固定方法 | L0,L1,L6 | L0,L1,L6,L7,L5 |
| LGA-Param-Direct-AltModelPred | 固定方法 | L1,L7,L0 | L1,L7,L0,L6,L8 |
| Perturb-KL-Direct-AltSeq | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| Ours-Direct | 固定方法 | L0,L1,L2 | L0,L1,L2,L3,L4 |
| CMA-Direct-v1.3-alt | 历史CMA（alt） | L15,L18,L16 | L15,L18,L16,L19,L14 |
| CMA-ModelPred-Direct-v2 | 正式CMA（model_pred） | L0,L1,L2 | L0,L1,L2,L9,L7 |

| 七方法版本 | Top-3并集 | 层数 | Top-5并集 | 层数 |
|---|---|---|---|---|
| 历史 CMA-alt v1.3 | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4,L19 | 20 |
| 正式 CMA-ModelPred v2 | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2 | 11 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4 | 19 |

## 5. 21组两版七方法并集总表

| 数据集 | 模型 | 历史alt Top-3并集 | 数 | ModelPred Top-3并集 | 数 | 历史alt Top-5并集 | 数 | ModelPred Top-5并集 | 数 |
|---|---|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2,L5 | 12 | L15,L16,L14,L20,L19,L18,L0,L1,L3,L4,L2 | 11 | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 | L15,L16,L14,L17,L13,L20,L19,L18,L0,L21,L1,L3,L4,L2,L5 | 15 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11,L25 | 15 | L15,L16,L14,L28,L27,L26,L0,L18,L19,L2,L1,L3,L4,L11 | 14 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L22 | 24 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L0,L18,L19,L20,L2,L1,L4,L3,L5,L6,L11,L9,L10,L21,L22 | 25 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19,L7 | 17 | L15,L16,L14,L26,L25,L24,L8,L9,L10,L29,L22,L0,L1,L2,L18,L19 | 16 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19,L7 | 25 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L8,L9,L10,L5,L6,L29,L21,L0,L1,L2,L3,L4,L18,L19 | 24 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2,L4 | 15 | L15,L16,L14,L28,L27,L26,L7,L6,L5,L24,L25,L0,L1,L2 | 14 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4,L10 | 22 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L6,L5,L8,L9,L23,L0,L1,L2,L3,L4 | 21 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L3 | 16 | L17,L18,L16,L29,L28,L27,L11,L14,L12,L2,L30,L1,L0,L21,L19,L15 | 16 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L6 | 24 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L11,L14,L12,L13,L2,L30,L1,L3,L10,L0,L4,L21,L20,L8,L5 | 25 |
| EVQA-pilot500 | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | L8,L9,L7,L12,L11,L10,L17,L0,L5,L6,L4,L3 | 12 | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4,L2 | 14 | L8,L9,L7,L10,L6,L12,L11,L17,L0,L13,L5,L3,L4 | 13 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L3 | 16 | L11,L12,L10,L17,L16,L15,L9,L8,L7,L22,L21,L20,L1,L2,L0,L5 | 16 | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3 | 22 | L11,L12,L10,L13,L9,L17,L16,L15,L14,L8,L7,L6,L22,L21,L20,L19,L18,L1,L2,L0,L4,L3,L5 | 23 |
| MMKE-visual | BLIP2-OPT-2.7B | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | L15,L16,L14,L26,L25,L24,L0,L18,L19,L1,L3,L4,L2 | 13 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L0,L18,L19,L20,L1,L3,L4,L2,L5 | 19 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L23,L22,L24 | 18 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L4,L3,L5,L1,L25,L22 | 17 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L23,L22 | 22 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L1,L3,L5,L8,L22,L23,L21 | 23 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | L15,L16,L14,L26,L25,L24,L31,L5,L8,L0,L1,L3,L2,L9,L10,L11 | 16 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 | L15,L16,L14,L17,L13,L26,L25,L24,L23,L22,L31,L5,L8,L6,L9,L0,L1,L3,L4,L2,L10,L11 | 22 |
| MMKE-visual | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | L15,L16,L14,L28,L27,L26,L7,L8,L9,L24,L22,L0,L1,L2,L3 | 15 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L7,L8,L9,L6,L10,L22,L23,L0,L1,L2,L3,L4,L5 | 23 |
| MMKE-visual | Qwen2.5-VL-3B | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13,L6 | 15 | L17,L18,L16,L28,L27,L26,L12,L11,L14,L2,L30,L1,L0,L13 | 14 | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4,L7 | 22 | L17,L18,L16,L19,L15,L28,L27,L26,L25,L24,L12,L11,L14,L13,L2,L30,L1,L3,L6,L0,L4 | 21 |
| MMKE-visual | PaliGemma-3B | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3,L1,L2 | 15 | L8,L9,L7,L14,L13,L12,L10,L17,L0,L5,L6,L4,L3 | 13 | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 | L8,L9,L7,L10,L6,L14,L13,L12,L11,L5,L17,L0,L4,L3,L2,L1 | 16 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L15 | 15 | L11,L12,L10,L18,L17,L16,L9,L8,L0,L1,L7,L6,L4,L2,L5 | 15 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L8,L0,L7,L1,L6,L5,L4,L2,L3 | 19 |
| MMKE-entity | BLIP2-OPT-2.7B | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | L15,L16,L14,L22,L21,L20,L0,L18,L30,L13,L3,L2,L4,L1 | 14 | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1 | 16 | L15,L16,L14,L17,L13,L22,L21,L20,L19,L18,L0,L30,L3,L2,L4,L1,L7,L10 | 18 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L23,L24,L22 | 18 | L15,L16,L14,L28,L27,L26,L18,L17,L19,L2,L0,L5,L4,L3,L1,L25,L22 | 17 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L23,L22 | 23 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L18,L19,L20,L2,L0,L4,L30,L5,L3,L8,L1,L22,L21,L23 | 24 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | L15,L16,L14,L25,L24,L23,L31,L22,L4,L3,L6,L0,L1,L2,L27,L28,L26 | 17 | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 | L15,L16,L14,L17,L13,L25,L24,L23,L22,L21,L31,L4,L3,L6,L0,L1,L2,L27,L28,L26,L29 | 21 |
| MMKE-entity | LLaVA-v1.5-7B | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12 | 17 | L15,L16,L14,L28,L27,L26,L23,L22,L24,L1,L9,L7,L0,L2,L13,L11,L12,L4 | 18 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 | L15,L16,L14,L17,L13,L28,L27,L26,L25,L24,L23,L22,L21,L1,L9,L7,L8,L6,L0,L2,L3,L4,L11,L12,L10 | 25 |
| MMKE-entity | Qwen2.5-VL-3B | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0 | 13 | L17,L18,L16,L29,L28,L27,L15,L14,L13,L2,L30,L1,L0,L20 | 14 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0 | 19 | L17,L18,L16,L19,L15,L29,L28,L27,L26,L25,L14,L13,L12,L2,L30,L1,L6,L3,L0,L20,L22 | 21 |
| MMKE-entity | PaliGemma-3B | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3,L0,L2,L1 | 16 | L8,L9,L7,L12,L11,L10,L17,L16,L13,L5,L6,L4,L3 | 13 | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2,L1 | 16 | L8,L9,L7,L10,L6,L12,L11,L17,L16,L13,L0,L5,L4,L3,L2 | 15 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2,L15 | 12 | L11,L12,L10,L18,L17,L16,L0,L1,L6,L7,L2 | 11 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4,L19 | 20 | L11,L12,L10,L13,L9,L18,L17,L16,L15,L14,L0,L1,L6,L7,L5,L8,L2,L3,L4 | 19 |

## 6. 两版CMA逐组合变化

| 数据集 | 模型 | CMA-alt Top-3 | CMA-ModelPred Top-3 | 集合 | CMA-alt Top-5 | CMA-ModelPred Top-5 | 集合 |
|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L4,L2,L5 | L2,L1,L0 | 变化 | L4,L2,L5,L3,L1 | L2,L1,L0,L3,L4 | 变化 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1,L0,L25 | L1,L0,L2 | 变化 | L1,L0,L25,L22,L2 | L1,L0,L2,L21,L22 | 变化 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L7,L1,L0 | L0,L1,L2 | 变化 | L7,L1,L0,L2,L8 | L0,L1,L2,L3,L4 | 变化 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L4 | L0,L1,L2 | 变化 | L0,L1,L4,L6,L10 | L0,L1,L2,L3,L4 | 变化 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L1,L0,L3 | L1,L0,L15 | 变化 | L1,L0,L3,L6,L4 | L1,L0,L15,L8,L5 | 变化 |
| EVQA-pilot500 | PaliGemma-3B | L5,L4,L0 | L5,L4,L7 | 变化 | L5,L4,L0,L3,L2 | L5,L4,L7,L0,L6 | 变化 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0,L1,L3 | L0,L1,L5 | 变化 | L0,L1,L3,L2,L6 | L0,L1,L5,L4,L8 | 变化 |
| MMKE-visual | BLIP2-OPT-2.7B | L3,L0,L1 | L2,L0,L3 | 变化 | L3,L0,L1,L2,L4 | L2,L0,L3,L1,L4 | 不变 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L23,L22,L24 | L1,L25,L22 | 变化 | L23,L22,L24,L19,L17 | L1,L25,L22,L23,L21 | 变化 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2 | 不变 | L0,L1,L2,L3,L4 | L0,L1,L2,L3,L4 | 不变 |
| MMKE-visual | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L2 | 不变 | L0,L1,L2,L3,L4 | L0,L1,L2,L3,L4 | 不变 |
| MMKE-visual | Qwen2.5-VL-3B | L1,L0,L6 | L1,L0,L2 | 变化 | L1,L0,L6,L7,L3 | L1,L0,L2,L3,L4 | 变化 |
| MMKE-visual | PaliGemma-3B | L1,L2,L0 | L7,L6,L4 | 变化 | L1,L2,L0,L3,L5 | L7,L6,L4,L5,L3 | 变化 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0,L1,L15 | L1,L0,L5 | 变化 | L0,L1,L15,L2,L7 | L1,L0,L5,L2,L6 | 变化 |
| MMKE-entity | BLIP2-OPT-2.7B | L3,L0,L2 | L2,L3,L1 | 变化 | L3,L0,L2,L4,L1 | L2,L3,L1,L7,L10 | 变化 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L23,L24,L22 | L26,L25,L22 | 变化 | L23,L24,L22,L19,L17 | L26,L25,L22,L21,L23 | 变化 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L0,L1,L2 | L0,L1,L2 | 不变 | L0,L1,L2,L3,L4 | L0,L1,L2,L3,L4 | 不变 |
| MMKE-entity | LLaVA-v1.5-7B | L0,L1,L2 | L0,L1,L4 | 变化 | L0,L1,L2,L3,L4 | L0,L1,L4,L3,L2 | 不变 |
| MMKE-entity | Qwen2.5-VL-3B | L1,L0,L2 | L1,L0,L20 | 变化 | L1,L0,L2,L3,L6 | L1,L0,L20,L22,L2 | 变化 |
| MMKE-entity | PaliGemma-3B | L0,L2,L1 | L7,L6,L5 | 变化 | L0,L2,L1,L3,L7 | L7,L6,L5,L4,L2 | 变化 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L15,L18,L16 | L0,L1,L2 | 变化 | L15,L18,L16,L19,L14 | L0,L1,L2,L9,L7 | 变化 |

CMA候选集合变化统计：Top-3为18/21组，Top-5为16/21组。顺序变化但集合相同不计入该数字；完整排序仍以上表为准。

## 7. 完整性校验与使用说明

- 组合覆盖：21/21（3个数据集 × 7个模型）。
- 候选矩阵：168/168个版本化方法行（固定六方法126行 + CMA-alt 21行 + CMA-ModelPred 21行）。
- 每一行均通过：Top-3恰好3个唯一层、Top-5恰好5个唯一层、Top-3是Top-5子集。
- 历史CMA-alt七方法并集总量：Top-3共317项，Top-5共429项。
- 正式CMA-ModelPred七方法并集总量：Top-3共306项，Top-5共432项。
- 替换CMA版本后，21组中Top-3并集集合有15组变化，Top-5并集集合有13组变化。
- CMA方法自身的候选集合变化：Top-3有18/21组，Top-5有16/21组。
- 两版并集均与现有机器可读并集CSV逐组合、逐字段一致；若后续候选公式或CMA协议改变，应新建版本，不能原地覆盖本表。
- 本文只冻结推荐候选层及并集。真实Adapter训练/评测数值、失败层与待补层仍以主手册第4章及服务器完成标记为准；不得把未评测层当0分。

## 8. 八方法联合并集评测覆盖补注（2026-09-22）

六个固定方法与CMA-alt、CMA-model_pred作为8个独立版本化方法同时计入，Top-3联合去重共324项，Top-5共439项。这里只合并待测层集合，**不修改任何单方法排名，也不混合两版CMA分数**；前文两个七方法并集及历史记录全部保留。

Top-3已有评测313项，尚缺11项：

| 数据集 / 模型 | 仍缺独立评测的层 | 状态 |
|---|---|---|
| EVQA-pilot500 / LLaVA-v1.5-7B | L2、L4 | L2已训练选点，待评测；L4未完成 |
| MMKE-entity / LLaVA-v1.5-7B | L0、L1、L2、L4、L7、L9、L11、L12、L13 | L1用户暂停，保留恢复点；其余无完整评测 |

313项包含304项历史主配置验收记录、7项MMKE-visual/PaliGemma stable-only（L1,L2,L3,L5,L6,L7,L13）及2项PaliGemma L0不收敛诊断评测（EVQA、MMKE-visual）。**评测覆盖不等于标准50轮主配置完成或收敛**；历史恢复/数值异常标签不变。EVQA/PaliGemma L0本次固定Epoch2评测2093条，Average35.492，没有续训。

完整说明和21组覆盖表见主手册3.4.8、诊断详情见3.5.3和4.0；逐层证据见`outputs/localization_audit_20260922/formal8_union_status.json`。Top-5已有评测339项、缺100项，是另一统计口径，不等于当前Top-3补层队列。
