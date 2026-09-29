#!/usr/bin/env bash
set -euo pipefail
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
COMMON_DATA=../../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json
BRIDGE_ROOT=../../Ten_Classes/bridge
mkdir -p ../server_results/bridge_vlm_lga_llava_train30 ../server_results/bridge_vlm_lga_blip2_train30

echo "[run] $(date '+%F %T') start llava"
$PY scripts/bridge_vlm_lga_scan.py \
  --model-name llava-v1.5-7b \
  --config-path configs/p_track/llava-v1.5-7b.yaml \
  --data-path "$COMMON_DATA" \
  --bridge-root "$BRIDGE_ROOT" \
  --old-answers-path ../../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl \
  --old-answer-key image_id \
  --layers 0-31 \
  --module-kind mlp \
  --score-mode request_only_lga \
  --main-score dot \
  --diagnostics cos,grad_norm,norm_ratio \
  --device cuda:0 \
  --layer-chunk-size 8 \
  --output-dir ../server_results/bridge_vlm_lga_llava_train30

echo "[run] $(date '+%F %T') start blip2"
$PY scripts/bridge_vlm_lga_scan.py \
  --model-name blip2-opt-2.7b \
  --config-path configs/p_track/blip2-opt-2.7b.yaml \
  --data-path "$COMMON_DATA" \
  --bridge-root "$BRIDGE_ROOT" \
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

echo "[run] $(date '+%F %T') done"
