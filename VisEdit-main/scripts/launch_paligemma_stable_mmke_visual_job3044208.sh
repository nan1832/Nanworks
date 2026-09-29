#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

GPU_ID="${GPU_ID:-0}"
PY_BASE="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
MMKE_ROOT="${MMKE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
SOURCE_ROOT="${SOURCE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/paligemma_stable_mmke_visual_top3_union_$(date +%Y%m%d_%H%M%S)}"
SCRIPT="${SCRIPT:-scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py}"
CONFIG="${CONFIG:-configs/vead/paligemma-3b-stable.yaml}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"
GPU_WAIT_MAX_USED_MIB="${GPU_WAIT_MAX_USED_MIB:-65000}"
PALIGEMMA_STABLE_MAX_EMA="${PALIGEMMA_STABLE_MAX_EMA:-100.0}"
PALIGEMMA_STABLE_GRAD_CLIP_NORM="${PALIGEMMA_STABLE_GRAD_CLIP_NORM:-1.0}"
PALIGEMMA_STABLE_SKIP_NONFINITE_STEP="${PALIGEMMA_STABLE_SKIP_NONFINITE_STEP:-1}"
export PALIGEMMA_STABLE_MAX_EMA
export PALIGEMMA_STABLE_GRAD_CLIP_NORM
export PALIGEMMA_STABLE_SKIP_NONFINITE_STEP

TRAIN_JSON="$SOURCE_ROOT/data/vqa_mmke_visual_train_evqa_compat.json"
EVAL_JSON="$SOURCE_ROOT/data/vqa_mmke_visual_eval_evqa_compat.json"
IMG_ROOT="$MMKE_ROOT/data_image"
STATUS="$RUN_ROOT/paligemma_stable_mmke_visual_status.log"
CSV="$RUN_ROOT/paligemma_stable_mmke_visual_layer_status.csv"
LOCK="$RUN_ROOT/paligemma_stable_mmke_visual.lock"
RUN_TAG="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$RUN_ROOT"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "PALIGEMMA_STABLE_ALREADY_RUNNING time=$(date) run_root=$RUN_ROOT" | tee -a "$STATUS"
  exit 3
fi

echo "model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
echo "PALIGEMMA_STABLE_MMKE_VISUAL_START time=$(date) host=$(hostname) gpu=$GPU_ID run_root=$RUN_ROOT" | tee -a "$STATUS"
echo "source_root=$SOURCE_ROOT train_json=$TRAIN_JSON eval_json=$EVAL_JSON" | tee -a "$STATUS"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS" || true

wait_gpu() {
  while true; do
    local used
    used="$(/usr/bin/nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')"
    used="${used:-999999}"
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" ]]; then
      if CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY_BASE" - <<'PY' >/tmp/paligemma_stable_cuda_probe.log 2>&1
import torch
assert torch.cuda.is_available(), "cuda unavailable"
torch.cuda.init()
PY
      then
        echo "GPU_READY used_mib=$used max_mib=$GPU_WAIT_MAX_USED_MIB time=$(date)" | tee -a "$STATUS"
        return 0
      fi
    fi
    echo "WAIT_GPU used_mib=$used max_mib=$GPU_WAIT_MAX_USED_MIB time=$(date)" | tee -a "$STATUS"
    sleep 180
  done
}

run_layer() {
  local layer="$1"
  local out="$RUN_ROOT/paligemma-3b"
  local train_log="$out/train_L${layer}_stable_${RUN_TAG}.log"
  local eval_log="$out/eval_L${layer}_stable_${RUN_TAG}.log"
  local start_time end_time train_rc eval_rc note selected

  mkdir -p "$out"
  selected="$out/layer_$(printf '%02d' "$layer")/selected_checkpoint.tsv"
  start_time="$(date '+%F %T')"
  train_rc=777
  eval_rc=777
  note=""

  wait_gpu
  echo "TRAIN_START model=paligemma-3b layer=$layer stable_config=$CONFIG time=$(date)" | tee -a "$STATUS"
  echo "ENV CUDA_VISIBLE_DEVICES=$GPU_ID host=$(hostname) time=$(date)" > "$train_log"
  CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY_BASE" "$SCRIPT" \
    --out-root "$out" \
    --layers "$layer" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --model-name paligemma-3b \
    --train-data "$TRAIN_JSON" \
    --train-img-root "$IMG_ROOT" \
    --eval-data "$EVAL_JSON" \
    --eval-img-root "$IMG_ROOT" \
    --config-path "$CONFIG" \
    --skip-eval \
    --overwrite-train \
    >> "$train_log" 2>&1
  train_rc=$?
  echo "TRAIN_END model=paligemma-3b layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"

  if [[ "$train_rc" -eq 0 && -s "$selected" ]]; then
    wait_gpu
    echo "EVAL_START model=paligemma-3b layer=$layer stable_config=$CONFIG time=$(date)" | tee -a "$STATUS"
    echo "ENV CUDA_VISIBLE_DEVICES=$GPU_ID host=$(hostname) time=$(date)" > "$eval_log"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY_BASE" "$SCRIPT" \
      --out-root "$out" \
      --layers "$layer" \
      --epochs "$EPOCHS" \
      --batch-size "$BATCH_SIZE" \
      --model-name paligemma-3b \
      --train-data "$TRAIN_JSON" \
      --train-img-root "$IMG_ROOT" \
      --eval-data "$EVAL_JSON" \
      --eval-img-root "$IMG_ROOT" \
      --config-path "$CONFIG" \
      --skip-train \
      --overwrite-eval \
      >> "$eval_log" 2>&1
    eval_rc=$?
    echo "EVAL_END model=paligemma-3b layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
  else
    note="eval_not_run_no_stable_checkpoint"
    echo "EVAL_NOT_RUN model=paligemma-3b layer=$layer train_rc=$train_rc selected_exists=$([[ -s "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
  fi

  end_time="$(date '+%F %T')"
  echo "paligemma-3b,$layer,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,$note" >> "$CSV"
}

if [[ ! -s "$TRAIN_JSON" || ! -s "$EVAL_JSON" ]]; then
  echo "DATA_MISSING train=$TRAIN_JSON eval=$EVAL_JSON time=$(date)" | tee -a "$STATUS"
  exit 2
fi

for layer in 12 11 10 14 17 9 8; do
  run_layer "$layer"
done

echo "PALIGEMMA_STABLE_MMKE_VISUAL_DONE time=$(date)" | tee -a "$STATUS"
