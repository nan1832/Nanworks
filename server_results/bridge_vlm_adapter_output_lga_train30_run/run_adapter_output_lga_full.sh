#!/usr/bin/env bash
set -euo pipefail
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
RUN_ROOT=../server_results/bridge_vlm_adapter_output_lga_train30_run
mkdir -p "$RUN_ROOT"
{
  echo "started_at=$(date '+%F %T')"
  echo "host=$(hostname)"
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader || true
  echo "===== LLaVA adapter-output LGA full scan ====="
  $PY scripts/bridge_vlm_adapter_output_lga_scan.py \
    --model-name llava-v1.5-7b \
    --vead-config-path configs/vead/llava-v1.5-7b.yaml \
    --data-path ../../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
    --bridge-root ../../Ten_Classes/bridge \
    --old-answers-path ../../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_llava.jsonl \
    --layers 0-31 \
    --adapter-type vision \
    --capture-object delta_h_vis \
    --score-mode request_only_adapter_output_lga \
    --main-score out_dot \
    --diagnostics out_cos,out_new_norm,out_old_norm,out_joint_norm,positive_ratio,median_dot \
    --device cuda:0 \
    --torch-dtype float16 \
    --seed 2026 \
    --output-dir ../server_results/bridge_vlm_adapter_output_lga_llava_train30
  echo "llava_finished_at=$(date '+%F %T')"
  echo "===== BLIP2 adapter-output LGA full scan ====="
  $PY scripts/bridge_vlm_adapter_output_lga_scan.py \
    --model-name blip2-opt-2.7b \
    --vead-config-path configs/vead/blip2-opt-2.7b.yaml \
    --data-path ../../Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json \
    --bridge-root ../../Ten_Classes/bridge \
    --old-answers-path ../../Ten_Classes/bridge/bridge_train/beforeedit/open_end/bridge_train_entity_recognition_blip2.jsonl \
    --layers 0-31 \
    --adapter-type vision \
    --capture-object delta_h_vis \
    --score-mode request_only_adapter_output_lga \
    --main-score out_dot \
    --diagnostics out_cos,out_new_norm,out_old_norm,out_joint_norm,positive_ratio,median_dot \
    --device cuda:0 \
    --torch-dtype float16 \
    --seed 2026 \
    --output-dir ../server_results/bridge_vlm_adapter_output_lga_blip2_train30
  echo "finished_at=$(date '+%F %T')"
} > "$RUN_ROOT/full_run.log" 2>&1
