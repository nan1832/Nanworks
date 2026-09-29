#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}

GPU_ID="${GPU_ID:-1}"
PY_BASE="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
PY_QWEN="${PY_QWEN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
MMKE_ROOT="${MMKE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_$(date +%Y%m%d_%H%M%S)}"
SCRIPT="${SCRIPT:-scripts/run_evqa_pilot500_blip2_visedit_sweep.py}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"

DATA_DIR="$RUN_ROOT/data"
TRAIN_JSON="$DATA_DIR/vqa_mmke_visual_train_evqa_compat.json"
EVAL_JSON="$DATA_DIR/vqa_mmke_visual_eval_evqa_compat.json"
IMG_ROOT="$MMKE_ROOT/data_image"
STATUS="$RUN_ROOT/mmke_visual_top3_union_status.log"
CSV="$RUN_ROOT/mmke_visual_top3_union_layer_status.csv"

mkdir -p "$RUN_ROOT" "$DATA_DIR"

echo "MMKE_VISUAL_TOP3_UNION_START time=$(date) host=$(hostname) gpu=$GPU_ID run_root=$RUN_ROOT" | tee -a "$STATUS"
if [[ ! -s "$CSV" ]]; then echo "model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log" > "$CSV"; fi

wait_gpu() {
  used="$(/usr/bin/nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc '0-9')"
  used="${used:-unknown}"
  echo "GPU${GPU_ID}_FORCE_FREE used_mib=$used time=$(date)" | tee -a "$STATUS"
  return 0
}

prepare_data() {
  "$PY_BASE" scripts/prepare_mmke_evqa_compat.py \
    --mmke-root "$MMKE_ROOT" \
    --task visual \
    --split train \
    --out-json "$TRAIN_JSON" | tee "$DATA_DIR/prepare_visual_train.log"
  local rc1=${PIPESTATUS[0]}
  "$PY_BASE" scripts/prepare_mmke_evqa_compat.py \
    --mmke-root "$MMKE_ROOT" \
    --task visual \
    --split eval \
    --out-json "$EVAL_JSON" | tee "$DATA_DIR/prepare_visual_eval.log"
  local rc2=${PIPESTATUS[0]}
  if [[ "$rc1" -ne 0 || "$rc2" -ne 0 ]]; then
    echo "DATA_PREP_FAILED train_rc=$rc1 eval_rc=$rc2 time=$(date)" | tee -a "$STATUS"
    exit 2
  fi
  "$PY_BASE" - <<PY
from dataset.vllm import EVQA
train = EVQA("$TRAIN_JSON", "$IMG_ROOT", 2)
eval_data = EVQA("$EVAL_JSON", "$IMG_ROOT", 2)
print("EVQA_COMPAT_OK", len(train.data), len(eval_data.data))
PY
}

run_layer() {
  local py="$1"
  local model="$2"
  local layer="$3"
  local config="$4"
  local out="$RUN_ROOT/$model"
  local start_time end_time train_rc eval_rc train_log eval_log

  mkdir -p "$out"
  train_log="$out/train_L${layer}.log"
  eval_log="$out/eval_L${layer}.log"
  start_time="$(date '+%F %T')"

  wait_gpu
  echo "TRAIN_START model=$model layer=$layer config=$config py=$py time=$(date)" | tee -a "$STATUS"
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
    > "$train_log" 2>&1
  train_rc=$?
  echo "TRAIN_END model=$model layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"

  eval_rc=999
  if [[ "$train_rc" -eq 0 ]]; then
    wait_gpu
    echo "EVAL_START model=$model layer=$layer time=$(date)" | tee -a "$STATUS"
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
      > "$eval_log" 2>&1
    eval_rc=$?
    echo "EVAL_END model=$model layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
  fi

  end_time="$(date '+%F %T')"
  echo "$model,$layer,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log" >> "$CSV"
  return "$train_rc"
}

run_model() {
  local model="$1"
  local layers_csv="$2"
  local config="$3"
  local py="$4"

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

# Resume after completed BLIP2 + InstructBLIP + MiniGPT4.
# Keep LLaVA last, per experiment scheduling requirement.
run_model paligemma-3b "12,11,10,14,17,9,8" configs/vead/paligemma-3b.yaml "$PY_BASE"
run_model smolvlm-1.7b "17,16,15,20,19,21,13,12,14" configs/vead/smolvlm-1.7b.yaml "$PY_BASE"
run_model llava-v1.5-7b "28,27,26,30,31,29,17,18,16" configs/vead/llava-v1.5-7b.yaml "$PY_BASE"

echo "MMKE_VISUAL_TOP3_UNION_RESUME_DONE time=$(date)" | tee -a "$STATUS"
touch "$RUN_ROOT/ALL_DONE"
