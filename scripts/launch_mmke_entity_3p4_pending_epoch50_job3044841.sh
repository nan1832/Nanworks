#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}

GPU_ID="${GPU_ID:-0}"
PY_BASE="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
PY_QWEN="${PY_QWEN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
MMKE_ROOT="${MMKE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000}"
SCRIPT="${SCRIPT:-scripts/run_evqa_pilot500_blip2_visedit_sweep.py}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"

DATA_DIR="$RUN_ROOT/data"
TRAIN_JSON="$DATA_DIR/vqa_mmke_entity_train_evqa_compat.json"
EVAL_JSON="$DATA_DIR/vqa_mmke_entity_eval_evqa_compat.json"
IMG_ROOT="$MMKE_ROOT/data_image"
STATUS="$RUN_ROOT/mmke_entity_3p4_pending_job3044841_status.log"
CSV="$RUN_ROOT/mmke_entity_3p4_pending_job3044841_layer_status.csv"
LOCK="$RUN_ROOT/mmke_entity_3p4_pending_job3044841.lock"
RUN_TAG="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$RUN_ROOT" "$DATA_DIR"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "MMKE_ENTITY_3P4_ALREADY_RUNNING time=$(date) run_root=$RUN_ROOT" | tee -a "$STATUS"
  exit 3
fi

if [[ ! -s "$CSV" ]]; then
  echo "model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
fi

echo "MMKE_ENTITY_3P4_START time=$(date) host=$(hostname) gpu=$GPU_ID run_root=$RUN_ROOT tag=$RUN_TAG" | tee -a "$STATUS"
echo "VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}" | tee -a "$STATUS"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS" || true

layer_dir_name() { printf "layer_%02d" "$1"; }

wait_gpu() {
  local py="$1"
  while true; do
    local used cuda_ok
    used="$(/usr/bin/nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')"
    used="${used:-999999}"
    cuda_ok=0
    if [[ "$used" -lt 4096 ]]; then
      if CUDA_VISIBLE_DEVICES="$GPU_ID" "$py" - <<'PY' >/tmp/mmke_entity_3p4_cuda_probe.log 2>&1
import torch
assert torch.cuda.is_available(), "cuda unavailable"
assert torch.cuda.device_count() >= 1, "no visible cuda device"
torch.cuda.init()
PY
      then
        cuda_ok=1
      fi
    fi
    if [[ "$used" -lt 4096 && "$cuda_ok" -eq 1 ]]; then
      echo "GPU_FREE used_mib=$used cuda_ok=$cuda_ok time=$(date)" | tee -a "$STATUS"
      return 0
    fi
    echo "WAIT_GPU used_mib=$used cuda_ok=$cuda_ok time=$(date)" | tee -a "$STATUS"
    sleep 180
  done
}

prepare_data() {
  if [[ -s "$TRAIN_JSON" && -s "$EVAL_JSON" ]]; then
    echo "DATA_PREP_SKIP existing train=$TRAIN_JSON eval=$EVAL_JSON time=$(date)" | tee -a "$STATUS"
  else
    "$PY_BASE" scripts/prepare_mmke_evqa_compat.py \
      --mmke-root "$MMKE_ROOT" \
      --task entity \
      --split train \
      --out-json "$TRAIN_JSON" | tee "$DATA_DIR/prepare_entity_train_3p4.log"
    local rc1=${PIPESTATUS[0]}
    "$PY_BASE" scripts/prepare_mmke_evqa_compat.py \
      --mmke-root "$MMKE_ROOT" \
      --task entity \
      --split eval \
      --out-json "$EVAL_JSON" | tee "$DATA_DIR/prepare_entity_eval_3p4.log"
    local rc2=${PIPESTATUS[0]}
    if [[ "$rc1" -ne 0 || "$rc2" -ne 0 ]]; then
      echo "DATA_PREP_FAILED train_rc=$rc1 eval_rc=$rc2 time=$(date)" | tee -a "$STATUS"
      exit 2
    fi
  fi
}

run_layer() {
  local py="$1"
  local model="$2"
  local layer="$3"
  local config="$4"
  local out="$RUN_ROOT/$model"
  local ldir layer_dir selected train_done eval_done train_log eval_log
  local train_rc eval_rc start_time end_time note selected_exists

  ldir="$(layer_dir_name "$layer")"
  layer_dir="$out/$ldir"
  selected="$layer_dir/selected_checkpoint.tsv"
  train_done="$layer_dir/train.done"
  eval_done="$layer_dir/eval_full.done"
  train_log="$out/train_L${layer}_3p4_${RUN_TAG}.log"
  eval_log="$out/eval_L${layer}_3p4_${RUN_TAG}.log"
  train_rc=777
  eval_rc=777
  note=""

  mkdir -p "$out"
  start_time="$(date '+%F %T')"

  if [[ -f "$train_done" && -f "$selected" ]]; then
    train_rc=0
    note="train_skip_existing"
    echo "TRAIN_SKIP model=$model layer=$layer reason=existing_done time=$(date)" | tee -a "$STATUS"
  else
    if [[ -d "$layer_dir" ]]; then
      echo "CLEAN_INCOMPLETE_LAYER model=$model layer=$layer dir=$layer_dir time=$(date)" | tee -a "$STATUS"
      rm -rf "$layer_dir"
    fi
    wait_gpu "$py"
    echo "TRAIN_START model=$model layer=$layer config=$config py=$py time=$(date)" | tee -a "$STATUS"
    echo "ENV CUDA_VISIBLE_DEVICES=$GPU_ID host=$(hostname) time=$(date)" > "$train_log"
    CUDA_VISIBLE_DEVICES="$GPU_ID" "$py" "$SCRIPT" \
      --out-root "$out" \
      --layers "$layer" \
      --epochs "$EPOCHS" \
      --batch-size "$BATCH_SIZE" \
      --model-name "$model" \
      --train-data "$TRAIN_JSON" \
      --train-img-root "$IMG_ROOT" \
      --eval-data "$EVAL_JSON" \
      --eval-img-root "$IMG_ROOT" \
      --config-path "$config" \
      --skip-eval \
      >> "$train_log" 2>&1
    train_rc=$?
    echo "TRAIN_END model=$model layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"
  fi

  if [[ "$train_rc" -eq 0 && -f "$selected" ]]; then
    if [[ -f "$eval_done" ]]; then
      eval_rc=0
      note="${note};eval_skip_existing"
      echo "EVAL_SKIP model=$model layer=$layer reason=existing_done time=$(date)" | tee -a "$STATUS"
    else
      wait_gpu "$py"
      echo "EVAL_START model=$model layer=$layer config=$config py=$py time=$(date)" | tee -a "$STATUS"
      echo "ENV CUDA_VISIBLE_DEVICES=$GPU_ID host=$(hostname) time=$(date)" > "$eval_log"
      CUDA_VISIBLE_DEVICES="$GPU_ID" "$py" "$SCRIPT" \
        --out-root "$out" \
        --layers "$layer" \
        --epochs "$EPOCHS" \
        --batch-size "$BATCH_SIZE" \
        --model-name "$model" \
        --train-data "$TRAIN_JSON" \
        --train-img-root "$IMG_ROOT" \
        --eval-data "$EVAL_JSON" \
        --eval-img-root "$IMG_ROOT" \
        --config-path "$config" \
        --skip-train \
        >> "$eval_log" 2>&1
      eval_rc=$?
      echo "EVAL_END model=$model layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    fi
  else
    selected_exists=0
    [[ -f "$selected" ]] && selected_exists=1
    echo "EVAL_NOT_RUN model=$model layer=$layer train_rc=$train_rc selected_exists=$selected_exists time=$(date)" | tee -a "$STATUS"
  fi

  end_time="$(date '+%F %T')"
  echo "$model,$layer,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,$note" >> "$CSV"
  return "$train_rc"
}

run_model() {
  local py="$1"
  local model="$2"
  local layers_csv="$3"
  local config="$4"
  if [[ ! -f "$config" ]]; then
    echo "MODEL_CONFIG_MISSING model=$model config=$config time=$(date)" | tee -a "$STATUS"
    return 0
  fi
  echo "MODEL_START model=$model layers=$layers_csv config=$config py=$py time=$(date)" | tee -a "$STATUS"
  IFS=',' read -ra layers <<< "$layers_csv"
  for layer in "${layers[@]}"; do
    if ! run_layer "$py" "$model" "$layer" "$config"; then
      echo "MODEL_STOP_AFTER_TRAIN_FAIL model=$model layer=$layer time=$(date)" | tee -a "$STATUS"
      break
    fi
  done
  echo "MODEL_END model=$model time=$(date)" | tee -a "$STATUS"
}

prepare_data

# MMKE-entity pending layers from md/Location/6location_7model_3datas_top_3_5_layers_outcome.md section 3.4.3.
# LLaVA is intentionally last because it is the slowest model.
run_model "$PY_BASE" blip2-opt-2.7b "15,14,0,30,13,3,2,4,19,25,23" configs/vead/blip2-opt-2.7b.yaml
run_model "$PY_BASE" instructblip-vicuna-7b "15,14,19,2,0,5,4,3,1,23,24,22,25" configs/vead/instructblip-vicuna-7b.yaml
run_model "$PY_BASE" minigpt-4-vicuna-7b "15,16,14,22,4,3,6,0,1,2,29,27,26" configs/vead/minigpt-4-vicuna-7b.yaml
run_model "$PY_QWEN" qwen2.5-vl-3b "17,18,16,29,28,27,15,14,13,2,30,1,0,22,21,20,26,25" configs/vead/qwen2.5-vl-3b-instruct.yaml
run_model "$PY_BASE" paligemma-3b "8,9,7,12,11,10,17,16,13,5,6,3,2,1,0" configs/vead/paligemma-3b.yaml
run_model "$PY_BASE" smolvlm-1.7b "11,12,10,18,17,16,0,1,6,7,2,15,9,14,13" configs/vead/smolvlm-1.7b.yaml
run_model "$PY_BASE" llava-v1.5-7b "15,16,14,28,27,26,23,22,24,1,9,7,0,2,13,30,12,18" configs/vead/llava-v1.5-7b.yaml

echo "MMKE_ENTITY_3P4_DONE time=$(date)" | tee -a "$STATUS"
touch "$RUN_ROOT/MMKE_ENTITY_3P4_PENDING_JOB3044841_DONE"
