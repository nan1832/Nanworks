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
