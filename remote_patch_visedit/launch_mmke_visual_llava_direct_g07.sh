#!/usr/bin/env bash
set -u

REPO="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
RUN_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644"
MODEL="llava-v1.5-7b"
OUT="$RUN_ROOT/$MODEL"
GPU_ID="${GPU_ID:-1}"
PY="${PY:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
SCRIPT="${SCRIPT:-scripts/run_evqa_pilot500_blip2_visedit_sweep.py}"
CONFIG="${CONFIG:-configs/vead/llava-v1.5-7b.yaml}"
TRAIN_JSON="$RUN_ROOT/data/vqa_mmke_visual_train_evqa_compat.json"
EVAL_JSON="$RUN_ROOT/data/vqa_mmke_visual_eval_evqa_compat.json"
IMG_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image"
LAYERS_CSV="${LAYERS_CSV:-27,26,30,31,29,17,18,16}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"
STATUS="$RUN_ROOT/mmke_visual_llava_direct_status.log"
CSV="$RUN_ROOT/mmke_visual_llava_direct_layer_status.csv"
LOCK="$RUN_ROOT/mmke_visual_llava_direct.lock"
RUN_TAG="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT"
cd "$REPO" || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "LLAVA_DIRECT_ALREADY_RUNNING time=$(date) run_root=$RUN_ROOT" | tee -a "$STATUS"
  exit 3
fi

if [[ ! -s "$CSV" ]]; then
  echo "model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
fi

echo "LLAVA_DIRECT_START time=$(date) host=$(hostname) gpu=$GPU_ID layers=$LAYERS_CSV tag=$RUN_TAG" | tee -a "$STATUS"

IFS=',' read -ra LAYERS <<< "$LAYERS_CSV"
for layer in "${LAYERS[@]}"; do
  layer="${layer//[[:space:]]/}"
  [[ -z "$layer" ]] && continue
  start_time="$(date '+%Y-%m-%d %H:%M:%S')"
  selected="$OUT/layer_$(printf '%02d' "$layer")/selected_checkpoint.tsv"
  train_log="$OUT/train_L${layer}_direct_${RUN_TAG}.log"
  eval_log="$OUT/eval_L${layer}_direct_${RUN_TAG}.log"

  if [[ -s "$selected" ]]; then
    echo "TRAIN_SKIP model=$MODEL layer=$layer reason=existing_selected time=$(date)" | tee -a "$STATUS"
    train_rc=0
    echo "skip existing selected=$selected" > "$train_log"
  else
    echo "TRAIN_START model=$MODEL layer=$layer direct=1 time=$(date)" | tee -a "$STATUS"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY" "$SCRIPT" \
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
      > "$train_log" 2>&1
    train_rc=$?
    echo "TRAIN_END model=$MODEL layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"
  fi

  if [[ "$train_rc" -eq 0 && -s "$selected" ]]; then
    echo "EVAL_START model=$MODEL layer=$layer direct=1 time=$(date)" | tee -a "$STATUS"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY" "$SCRIPT" \
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
      > "$eval_log" 2>&1
    eval_rc=$?
    echo "EVAL_END model=$MODEL layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
  else
    eval_rc=777
    echo "EVAL_NOT_RUN model=$MODEL layer=$layer train_rc=$train_rc selected_exists=$([[ -s "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
  fi

  end_time="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "$MODEL,$layer,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,direct_llava" >> "$CSV"
  if [[ "$train_rc" -ne 0 || "$eval_rc" -ne 0 ]]; then
    echo "LLAVA_DIRECT_STOP_AFTER_FAIL layer=$layer train_rc=$train_rc eval_rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    exit 1
  fi
done

echo "LLAVA_DIRECT_DONE time=$(date)" | tee -a "$STATUS"
