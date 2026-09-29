## pliot500-blip2-visedit-sweep-outcom

### Setup

- Model: `blip2-opt-2.7b`
- Train data: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json`
- Train image root: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image`
- Eval data: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_eval_evqa_compat.json`
- Eval image root: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image`
- Layers: `1`
- Epochs: `50`
- Batch size: `2`
- Adapter: visual-only VisEdit / VEAD
- Checkpoint selection: minimum checkpoint EMA loss per layer
- Official E-VQA evaluation uses the full eval/test split, not pilot500 val.

### Selected Checkpoints

| Layer | Epoch | Step | Loss | EMA Loss | Checkpoint |
|---:|---:|---:|---:|---:|---|
| 1 | 11 | 3498 | 5.893988 | 5.990400 | `epoch-11-i-3498-ema_loss-5.9904` |

### Full E-VQA Evaluation

| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Paper Avg | Delta Avg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 57.94 | 57.91 | 57.96 | 100.00 | 88.71 | 72.50 |  |  |

### Paper Full-Train Reference

| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|
| 1 |  |  |  |  |  |  |

### Loss Curves

![pilot500 BLIP2 VisEdit loss curves](/tmp/ph_teacher3/mabscos_top3_completion_job3126082_20260801/mmke-entity/blip2-opt-2.7b/loss_curves_all_layers.png)

### Interpretation Template

- Best pilot500-trained layer by full E-VQA Average: Layer 1 with Average 72.50.
- Compare `Delta Avg` with the paper full-train reference to estimate the performance gap caused by training on pilot500 instead of full E-VQA train.
- If Layer 19 remains best or near-best, pilot500 preserves the paper's layer preference; if not, pilot500 is too small or biased for layer localization validation.

