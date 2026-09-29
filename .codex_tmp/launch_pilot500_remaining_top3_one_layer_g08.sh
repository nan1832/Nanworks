#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}

GPU_ID="${GPU_ID:-1}"
PY_BASE="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
PY_QWEN="${PY_QWEN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_pre_alt_pilot500_6models_20260608_092829}"
SCRIPT="${SCRIPT:-scripts/run_evqa_pilot500_blip2_visedit_sweep.py}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"
TRAIN_JSON="${TRAIN_JSON:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json}"
TRAIN_IMG="${TRAIN_IMG:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images}"
EVAL_JSON="${EVAL_JSON:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json}"
EVAL_IMG="${EVAL_IMG:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images}"

RUN_TAG="$(date +%Y%m%d_%H%M%S)"
STATUS="$RUN_ROOT/pilot500_remaining_oneproc_g08_status.log"
CSV="$RUN_ROOT/pilot500_remaining_oneproc_g08_layer_status.csv"
LOCK="$RUN_ROOT/pilot500_remaining_oneproc_g08.lock"

mkdir -p "$RUN_ROOT"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "PILOT500_ONEPROC_ALREADY_RUNNING time=$(date)" | tee -a "$STATUS"
  exit 3
fi

if [[ ! -f "$CSV" ]]; then
  echo "model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
fi

echo "PILOT500_REMAINING_ONEPROC_START time=$(date) host=$(hostname) gpu=$GPU_ID run_root=$RUN_ROOT tag=$RUN_TAG" | tee -a "$STATUS"

layer_dir_name() {
  printf "layer_%02d" "$1"
}

wait_gpu() {
  local py="$1"
  while true; do
    local used cuda_ok
    used="$(env -u CUDA_VISIBLE_DEVICES /usr/bin/nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits 2>/dev/null | awk -F, -v id="$GPU_ID" '{gsub(/ /, "", $1); gsub(/ /, "", $2); if ($1 == id) {print $2; exit}}')"
    used="${used:-999999}"
    cuda_ok=0
    if [[ "$used" -lt 1024 ]]; then
      if CUDA_VISIBLE_DEVICES="$GPU_ID" "$py" - <<'PY' >/tmp/pilot500_oneproc_cuda_probe.log 2>&1
import torch
assert torch.cuda.is_available(), "cuda unavailable"
assert torch.cuda.device_count() >= 1, "no visible cuda device"
torch.cuda.init()
PY
      then
        cuda_ok=1
      fi
    fi
    if [[ "$used" -lt 1024 && "$cuda_ok" -eq 1 ]]; then
      echo "GPU${GPU_ID}_FREE used_mib=$used cuda_ok=$cuda_ok time=$(date)" | tee -a "$STATUS"
      return 0
    fi
    echo "WAIT_GPU${GPU_ID} used_mib=$used cuda_ok=$cuda_ok time=$(date)" | tee -a "$STATUS"
    sleep 300
  done
}

run_layer() {
  local py="$1"
  local model="$2"
  local layer="$3"
  local config="$4"
  local out="$RUN_ROOT/$model"
  local ldir
  ldir="$(layer_dir_name "$layer")"
  local layer_dir="$out/$ldir"
  local selected="$layer_dir/selected_checkpoint.tsv"
  local train_done="$layer_dir/train.done"
  local eval_done="$layer_dir/eval_full.done"
  local train_log="$out/train_L${layer}_oneproc_${RUN_TAG}.log"
  local eval_log="$out/eval_L${layer}_oneproc_${RUN_TAG}.log"
  local train_rc eval_rc start_time end_time note

  mkdir -p "$out"
  start_time="$(date '+%F %T')"
  train_rc=777
  eval_rc=777
  note=""

  if [[ -f "$train_done" && -f "$selected" ]]; then
    train_rc=0
    note="train_skip_existing"
    echo "TRAIN_SKIP model=$model layer=$layer reason=existing_done time=$(date)" | tee -a "$STATUS"
  else
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
      --train-img-root "$TRAIN_IMG" \
      --eval-data "$EVAL_JSON" \
      --eval-img-root "$EVAL_IMG" \
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
        --train-img-root "$TRAIN_IMG" \
        --eval-data "$EVAL_JSON" \
        --eval-img-root "$EVAL_IMG" \
        --config-path "$config" \
        --skip-train \
        >> "$eval_log" 2>&1
      eval_rc=$?
      echo "EVAL_END model=$model layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    fi
  else
    local selected_exists=0
    [[ -f "$selected" ]] && selected_exists=1
    echo "EVAL_NOT_RUN model=$model layer=$layer train_rc=$train_rc selected_exists=$selected_exists time=$(date)" | tee -a "$STATUS"
  fi

  end_time="$(date '+%F %T')"
  echo "$model,$layer,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,$note" >> "$CSV"
}

run_model() {
  local py="$1"
  local model="$2"
  local layers_csv="$3"
  local config="$4"
  if [[ ! -f "$config" ]]; then
    echo "CONFIG_MISSING model=$model config=$config time=$(date)" | tee -a "$STATUS"
    return 0
  fi
  echo "MODEL_START model=$model layers=$layers_csv config=$config py=$py time=$(date)" | tee -a "$STATUS"
  IFS=',' read -ra layers <<< "$layers_csv"
  for layer in "${layers[@]}"; do
    run_layer "$py" "$model" "$layer" "$config"
  done
  echo "MODEL_END model=$model time=$(date)" | tee -a "$STATUS"
}

# BLIP2 and InstructBLIP are already complete. Continue the remaining pilot500 Top-3 runs.
run_model "$PY_BASE" llava-v1.5-7b "28,27,26" configs/vead/llava-v1.5-7b.yaml
run_model "$PY_BASE" minigpt-4-vicuna-7b "26,25,24" configs/vead/minigpt-4-vicuna-7b.yaml
run_model "$PY_QWEN" qwen2.5-vl-3b "29,28,27" configs/vead/qwen2.5-vl-3b-instruct.yaml
run_model "$PY_BASE" paligemma-3b "12,11,10" configs/vead/paligemma-3b.yaml
run_model "$PY_BASE" smolvlm-1.7b "17,16,15" configs/vead/smolvlm-1.7b.yaml

echo "PILOT500_REMAINING_ONEPROC_DONE time=$(date)" | tee -a "$STATUS"
touch "$RUN_ROOT/PILOT500_REMAINING_ONEPROC_DONE"
