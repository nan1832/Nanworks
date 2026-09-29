#!/usr/bin/env bash
set -euo pipefail
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
echo "[run] $(date '+%F %T') start blip2 rerun"
$PY scripts/bridge_vlm_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --config-path configs/p_track/blip2-opt-2.7b.yaml \
  --data-path ../../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
  --bridge-root ../../Ten_Classes/bridge \
  --old-answers-path ../../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl \
  --old-answer-key image_id \
  --layers 0-31 \
  --module-kind mlp \
  --score-mode request_only_lga \
  --main-score dot \
  --diagnostics cos,grad_norm,norm_ratio \
  --device cuda:0 \
  --layer-chunk-size 8 \
  --generate-old-answers-if-missing \
  --output-dir ../server_results/bridge_vlm_lga_blip2_train30
echo "[run] $(date '+%F %T') done blip2 rerun"
