# Perturb-KL-Pre-AltSeq candidate layers

Source: derived from Perturb-KL-Direct-AltSeq full `perturb_kl_layer_scores.csv`; no model forward or perturbation rerun.

| Dataset | Model | High-sensitive region | Top-3 raw | Top-3 clean | Top-5 raw | Top-5 clean | Status |
|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L2-L15 | L1,L0,L-1 | L1,L0 | L1,L0,L-1,L-2,L-3 | L1,L0 | insufficient_pre_layers; pre_candidate_layers_out_of_range |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L0-L9 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0-L8 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| EVQA-pilot500 | PaliGemma-3B | L2-L8 | L1,L0,L-1 | L1,L0 | L1,L0,L-1,L-2,L-3 | L1,L0 | insufficient_pre_layers; pre_candidate_layers_out_of_range |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-visual | BLIP2-OPT-2.7B | L0-L6 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L3-L16 | L2,L1,L0 | L2,L1,L0 | L2,L1,L0,L-1,L-2 | L2,L1,L0 | insufficient_pre_layers; pre_candidate_layers_out_of_range |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L0-L8 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-visual | LLaVA-v1.5-7B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-visual | Qwen2.5-VL-3B | L10-L17 | L9,L8,L7 | L9,L8,L7 | L9,L8,L7,L6,L5 | L9,L8,L7,L6,L5 | done |
| MMKE-visual | PaliGemma-3B | L4-L8 | L3,L2,L1 | L3,L2,L1 | L3,L2,L1,L0,L-1 | L3,L2,L1,L0 | insufficient_pre_layers; pre_candidate_layers_out_of_range |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-entity | BLIP2-OPT-2.7B | L0-L6 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L3-L15 | L2,L1,L0 | L2,L1,L0 | L2,L1,L0,L-1,L-2 | L2,L1,L0 | insufficient_pre_layers; pre_candidate_layers_out_of_range |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L0-L9 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-entity | LLaVA-v1.5-7B | L0-L5 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-entity | Qwen2.5-VL-3B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
| MMKE-entity | PaliGemma-3B | L4-L9 | L3,L2,L1 | L3,L2,L1 | L3,L2,L1,L0,L-1 | L3,L2,L1,L0 | insufficient_pre_layers; pre_candidate_layers_out_of_range |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0-L7 | L-1,L-2,L-3 | - | L-1,L-2,L-3,L-4,L-5 | - | insufficient_pre_layers; high_sensitive_region_starts_at_L0 |
