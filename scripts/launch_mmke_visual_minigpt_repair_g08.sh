#!/usr/bin/env bash
set -u

# Targeted repair for MMKE-visual / MiniGPT-4 layers skipped after an rc=143.
# This script is intentionally separate from the main MMKE-visual launcher so it
# can run on an idle GPU without disturbing the ongoing MMKE-entity job.

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}

GPU_ID="${GPU_ID:-0}"
PY_BASE="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
MMKE_ROOT="${MMKE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644}"
SCRIPT="${SCRIPT:-scripts/run_evqa_pilot500_blip2_visedit_sweep.py}"
MODEL="${MODEL:-minigpt-4-vicuna-7b}"
CONFIG="${CONFIG:-configs/vead/minigpt-4-vicuna-7b.yaml}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"
LAYERS_CSV="${LAYERS_CSV:-14,5,8,0,1,3,2,29}"
GPU_WAIT_MAX_USED_MIB="${GPU_WAIT_MAX_USED_MIB:-4096}"

DATA_DIR="$RUN_ROOT/data"
TRAIN_JSON="$DATA_DIR/vqa_mmke_visual_train_evqa_compat.json"
EVAL_JSON="$DATA_DIR/vqa_mmke_visual_eval_evqa_compat.json"
IMG_ROOT="$MMKE_ROOT/data_image"
OUT="$RUN_ROOT/$MODEL"
RUN_TAG="$(date +%Y%m%d_%H%M%S)"
STATUS="$RUN_ROOT/mmke_visual_minigpt_repair_${RUN_TAG}_status.log"
CSV="$RUN_ROOT/mmke_visual_minigpt_repair_${RUN_TAG}_layer_status.csv"

mkdir -p "$OUT"
echo "model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
echo "MINIGPT_REPAIR_START time=$(date) host=$(hostname) gpu=$GPU_ID run_root=$RUN_ROOT layers=$LAYERS_CSV wait_max_mib=$GPU_WAIT_MAX_USED_MIB tag=$RUN_TAG" | tee -a "$STATUS"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS" || true

layer_dir_name() { printf "layer_%02d" "$1"; }

wait_gpu() {
  local used
  while true; do
    used="$(/usr/bin/nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')"
    used="${used:-999999}"
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" ]]; then
      echo "GPU_FREE used_mib=$used time=$(date)" | tee -a "$STATUS"
      return 0
    fi
    echo "WAIT_GPU used_mib=$used max_mib=$GPU_WAIT_MAX_USED_MIB time=$(date)" | tee -a "$STATUS"
    sleep 180
  done
}

backup_incomplete_layer() {
  local layer="$1"
  local layer_dir="$OUT/$(layer_dir_name "$layer")"
  local selected="$layer_dir/selected_checkpoint.tsv"
  local train_done="$layer_dir/train.done"
  if [[ -d "$layer_dir" && ! ( -f "$selected" && -f "$train_done" ) ]]; then
    local backup="${layer_dir}.failed_rc143_${RUN_TAG}"
    echo "BACKUP_INCOMPLETE model=$MODEL layer=$layer from=$layer_dir to=$backup time=$(date)" | tee -a "$STATUS"
    mv "$layer_dir" "$backup"
  fi
}

run_layer() {
  local layer="$1"
  local layer_dir="$OUT/$(layer_dir_name "$layer")"
  local selected="$layer_dir/selected_checkpoint.tsv"
  local train_done="$layer_dir/train.done"
  local eval_done="$layer_dir/eval_full.done"
  local train_log="$OUT/train_L${layer}_repair_${RUN_TAG}.log"
  local eval_log="$OUT/eval_L${layer}_repair_${RUN_TAG}.log"
  local train_rc=777
  local eval_rc=777
  local note=""
  local start_time end_time
  start_time="$(date '+%F %T')"

  if [[ -f "$train_done" && -f "$selected" ]]; then
    train_rc=0
    note="train_skip_existing"
    echo "TRAIN_SKIP model=$MODEL layer=$layer reason=existing_done time=$(date)" | tee -a "$STATUS"
  else
    backup_incomplete_layer "$layer"
    wait_gpu
    echo "TRAIN_START model=$MODEL layer=$layer config=$CONFIG py=$PY_BASE time=$(date)" | tee -a "$STATUS"
    echo "ENV CUDA_VISIBLE_DEVICES=$GPU_ID host=$(hostname) time=$(date)" > "$train_log"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY_BASE" "$SCRIPT" \
      --out-root "$OUT" \
      --layers "$layer" \
      --epochs "$EPOCHS" \
      --batch-size "$BATCH_SIZE" \
      --model-name "$MODEL" \
      --train-data "$TRAIN_JSON" \
      --train-img-root "$IMG_ROOT" \
      --eval-data "$EVAL_JSON" \
      --eval-img-root "$IMG_ROOT" \
      --config-path "$CONFIG" \
      --skip-eval \
      >> "$train_log" 2>&1
    train_rc=$?
    echo "TRAIN_END model=$MODEL layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"
  fi

  if [[ "$train_rc" -eq 0 && -f "$selected" ]]; then
    if [[ -f "$eval_done" ]]; then
      eval_rc=0
      note="${note};eval_skip_existing"
      echo "EVAL_SKIP model=$MODEL layer=$layer reason=existing_done time=$(date)" | tee -a "$STATUS"
    else
      wait_gpu
      echo "EVAL_START model=$MODEL layer=$layer config=$CONFIG py=$PY_BASE time=$(date)" | tee -a "$STATUS"
      echo "ENV CUDA_VISIBLE_DEVICES=$GPU_ID host=$(hostname) time=$(date)" > "$eval_log"
      CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY_BASE" "$SCRIPT" \
        --out-root "$OUT" \
        --layers "$layer" \
        --epochs "$EPOCHS" \
        --batch-size "$BATCH_SIZE" \
        --model-name "$MODEL" \
        --train-data "$TRAIN_JSON" \
        --train-img-root "$IMG_ROOT" \
        --eval-data "$EVAL_JSON" \
        --eval-img-root "$IMG_ROOT" \
        --config-path "$CONFIG" \
        --skip-train \
        >> "$eval_log" 2>&1
      eval_rc=$?
      echo "EVAL_END model=$MODEL layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    fi
  else
    echo "EVAL_NOT_RUN model=$MODEL layer=$layer train_rc=$train_rc selected_exists=$([[ -f "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
  fi

  end_time="$(date '+%F %T')"
  echo "$MODEL,$layer,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,$note" >> "$CSV"
  return 0
}

IFS=',' read -ra layers <<< "$LAYERS_CSV"
for layer in "${layers[@]}"; do
  run_layer "$layer"
done

echo "MINIGPT_REPAIR_DONE time=$(date) csv=$CSV" | tee -a "$STATUS"
