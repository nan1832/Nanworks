### 3.4.6 正式7方法 + CMA-ModelPred v2并集、完成状态与阶段指标

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
