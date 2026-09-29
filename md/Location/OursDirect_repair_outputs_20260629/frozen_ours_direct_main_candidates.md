| dataset | model | method | score_variant | main_top3 | main_top5 | status | valid_samples | total_samples | coverage | failure_reason_major |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Direct | conflict_main |  |  | failed | 465 | 500 | 0.93 | no_valid_ours_direct_layer |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Direct | conflict_main |  |  | failed | 500 | 500 | 1.0 | no_valid_ours_direct_layer |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Direct | conflict_main | L17,L16,L15 | L17,L16,L15,L14,L18 | done | 500 | 500 | 1.0 |  |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Direct | conflict_main | L29,L28,L30 | L29,L28,L30,L27,L24 | done | 499 | 500 | 0.998 | empty_model_pred |
| EVQA-pilot500 | PaliGemma-3B | Ours-Direct | conflict_main |  |  | failed | 500 | 500 | 1.0 | no_valid_ours_direct_layer |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Direct | conflict_main |  |  | failed | 457 | 500 | 0.914 | no_valid_ours_direct_layer |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Direct | conflict_main | L14,L13,L12 | L14,L13,L12,L11,L10 | done | 500 | 500 | 1.0 |  |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Direct | conflict_main | L20,L19,L18 | L20,L19,L18,L17,L22 | low_confidence | 284 | 636 | 0.446541 | low_coverage |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Direct | conflict_main |  |  | failed | 636 | 636 | 1.0 | no_valid_ours_direct_layer |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Direct | conflict_main | L13,L30,L12 | L13,L30,L12,L14,L15 | done | 636 | 636 | 1.0 |  |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Direct | conflict_main | L28,L29,L27 | L28,L29,L27,L26,L25 | done | 636 | 636 | 1.0 |  |
| MMKE-entity | PaliGemma-3B | Ours-Direct | conflict_main |  |  | failed | 636 | 636 | 1.0 | no_valid_ours_direct_layer |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Direct | conflict_main | L8,L7,L6 | L8,L7,L6,L5,L9 | invalid_low_coverage | 5 | 636 | 0.007862 | invalid_low_coverage |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Direct | conflict_main |  |  | failed | 636 | 636 | 1.0 | no_valid_ours_direct_layer |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Direct | conflict_main | L30 | L30 | done | 175 | 214 | 0.817757 | empty_model_pred |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Direct | conflict_main |  |  | failed | 214 | 214 | 1.0 | no_valid_ours_direct_layer |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Direct | conflict_main | L13,L14,L15 | L13,L14,L15,L16,L12 | done | 214 | 214 | 1.0 |  |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Direct | conflict_main | L29,L28,L27 | L29,L28,L27,L26,L30 | done | 214 | 214 | 1.0 |  |
| MMKE-visual | PaliGemma-3B | Ours-Direct | conflict_main |  |  | failed | 214 | 214 | 1.0 | no_valid_ours_direct_layer |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Direct | conflict_main | L18,L19,L20 | L18,L19,L20,L16,L17 | low_confidence | 96 | 214 | 0.448598 | low_coverage |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Direct | conflict_main |  |  | failed | 214 | 214 | 1.0 | no_valid_ours_direct_layer |
