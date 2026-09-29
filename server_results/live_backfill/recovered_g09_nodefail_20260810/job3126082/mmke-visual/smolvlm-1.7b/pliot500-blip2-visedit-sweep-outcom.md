## pliot500-blip2-visedit-sweep-outcom

### Setup

- Model: `smolvlm-1.7b`
- Train data: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json`
- Train image root: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image`
- Eval data: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_eval_evqa_compat.json`
- Eval image root: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image`
- Layers: `2`
- Epochs: `50`
- Batch size: `2`
- Adapter: visual-only VisEdit / VEAD
- Checkpoint selection: minimum checkpoint EMA loss per layer
- Official E-VQA evaluation uses the full eval/test split, not pilot500 val.

### Selected Checkpoints

| Layer | Epoch | Step | Loss | EMA Loss | Checkpoint |
|---:|---:|---:|---:|---:|---|
| 2 | 46 | 4922 | 0.367433 | 0.411423 | `epoch-46-i-4922-ema_loss-0.4114` |

### Full E-VQA Evaluation

| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Paper Avg | Delta Avg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 52.96 | 52.77 | 53.14 | 100.00 | 93.74 | 70.52 |  |  |

### Paper Full-Train Reference

| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|
| 2 |  |  |  |  |  |  |

### Loss Curves

![pilot500 BLIP2 VisEdit loss curves](/tmp/ph_teacher3/mabscos_top3_completion_job3126082_20260801/mmke-visual/smolvlm-1.7b/loss_curves_all_layers.png)

### Interpretation Template

- Best pilot500-trained layer by full E-VQA Average: Layer 2 with Average 70.52.
- Compare `Delta Avg` with the paper full-train reference to estimate the performance gap caused by training on pilot500 instead of full E-VQA train.
- If Layer 19 remains best or near-best, pilot500 preserves the paper's layer preference; if not, pilot500 is too small or biased for layer localization validation.

