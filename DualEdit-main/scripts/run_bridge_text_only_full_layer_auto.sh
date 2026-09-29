#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
BRIDGE_ROOT=${BRIDGE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge}
COCO_ROOT=${COCO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images}
TRAIN_DATA=${TRAIN_DATA:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json}
EVAL_DATA=${EVAL_DATA:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json}
RESULT_ROOT=${RESULT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep}
DEVICE=${DEVICE:-cuda:0}
CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
LAYERS=${LAYERS:-$(seq 0 31)}
SELECTION_MODES=${SELECTION_MODES:-best matched target0003}

export CUDA_VISIBLE_DEVICES
export PYTHONUNBUFFERED=1

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

LOG_DIR="$RESULT_ROOT"
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/text_only_full_layer_auto.log"
STATUS_FILE="$LOG_DIR/text_only_full_layer_status.tsv"

log() {
  echo "[$(date '+%F %T')] $*" | tee -a "$PIPELINE_LOG"
}

write_status() {
  echo -e "$(date '+%F %T')\t$1\t$2" >> "$STATUS_FILE"
}

run_one_model() {
  local model_key=$1
  local base_config=$2
  local out_root=$3

  mkdir -p "$out_root"
  log "START train model=$model_key out_root=$out_root"
  write_status "$model_key" "TRAIN_START"

  # shellcheck disable=SC2086
  "$PYTHON_BIN" scripts/run_bridge_text_layer_sweep.py \
    --device "$DEVICE" \
    --single_gpu \
    --layers $LAYERS \
    --epochs 100 \
    --max_epochs 700 \
    --continue_increment 20 \
    --target_loss 0.0003 \
    --target_tolerance 0.0001 \
    --train_until_target \
    --cleanup_unselected_checkpoints \
    --prune_checkpoints_during_train \
    --retain_recent_checkpoints 3 \
    --retain_epoch_interval 20 \
    --cleanup_layer_cache \
    --base_config "$base_config" \
    --data_path "$TRAIN_DATA" \
    --bridge_img_root "$BRIDGE_ROOT" \
    --coco_img_root "$COCO_ROOT" \
    --out_root "$out_root" \
    --train_name_prefix bridge_text_only \
    --save_ckpt_per_i 30 \
    --log_per_i 10 \
    --data_buffer_size 4 \
    --selection_modes $SELECTION_MODES \
    --skip_eval \
    2>&1 | tee -a "$out_root/full_layer_text_only_sweep.log"

  log "END train model=$model_key"
  write_status "$model_key" "TRAIN_DONE"

  log "START eval model=$model_key"
  write_status "$model_key" "EVAL_START"
  bash scripts/eval_bridge_text_only_full_metrics_sweep.sh \
    --out_root "$out_root" \
    --eval_data "$EVAL_DATA" \
    --selection_modes "$SELECTION_MODES" \
    --device "$DEVICE" \
    --bridge_root "$BRIDGE_ROOT" \
    --coco_root "$COCO_ROOT" \
    --python_bin "$PYTHON_BIN" \
    2>&1 | tee -a "$out_root/full_layer_text_only_eval.log"

  log "END eval model=$model_key"
  write_status "$model_key" "EVAL_DONE"
}

log "PIPELINE_START"
write_status "pipeline" "START"

run_one_model \
  "llava" \
  "configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml" \
  "$RESULT_ROOT/llava"

run_one_model \
  "blip2" \
  "configs/vead/blip2-opt-2.7b-bridge-text-only-l16.yaml" \
  "$RESULT_ROOT/blip2"

log "PIPELINE_DONE"
write_status "pipeline" "DONE"
