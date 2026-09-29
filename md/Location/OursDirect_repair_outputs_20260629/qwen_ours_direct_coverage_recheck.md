# Qwen Ours-Direct coverage recheck

Computed at: 2026-06-29 21:19:23

| dataset | model | valid_samples | total_samples | coverage | status | empty_model_pred_count | failure_reason_major |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVQA-pilot500 | Qwen2.5-VL-3B | 457 | 500 | 0.914 | failed | 43 | no_valid_ours_direct_layer |
| MMKE-entity | Qwen2.5-VL-3B | 5 | 636 | 0.007862 | invalid_low_coverage | 631 | invalid_low_coverage |
| MMKE-visual | Qwen2.5-VL-3B | 96 | 214 | 0.448598 | low_confidence | 118 | low_coverage |

## Notes

- EVQA-pilot500 / Qwen2.5-VL-3B: coverage high enough for ablation derivation, but main formula failed.
- MMKE-visual / Qwen2.5-VL-3B: low confidence; repair model_pred before strong conclusion.
- MMKE-entity / Qwen2.5-VL-3B: forced invalid_low_coverage until model_pred coverage is fixed.
