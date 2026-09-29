#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}
export CUDA_VISIBLE_DEVICES=0

PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUN_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_pre_alt_pilot500_6models_20260608_092829
TRAIN_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
EVAL_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
EVAL_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
SCRIPT=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
STATUS="$RUN_ROOT/pali_smol_launcher_status.log"
MAIN_PID_FILE="$RUN_ROOT/top3_launcher.pid"

echo "PALI_SMOL_WAIT_START $(date) host=$(hostname)" | tee -a "$STATUS"
if [[ -f "$MAIN_PID_FILE" ]]; then
  main_pid=$(cat "$MAIN_PID_FILE" 2>/dev/null || true)
  while [[ -n "${main_pid:-}" ]] && kill -0 "$main_pid" 2>/dev/null; do
    echo "WAITING_FOR_TOP3 pid=$main_pid time=$(date)" | tee -a "$STATUS"
    sleep 300
  done
fi

echo "PALI_SMOL_RUN_START $(date) host=$(hostname)" | tee -a "$STATUS"
nvidia-smi >> "$RUN_ROOT/pali_smol_launcher_nvidia_smi_start.log" 2>&1 || true

run_train() {
  local model="$1" layers="$2" config="$3" out="$RUN_ROOT/$1"
  mkdir -p "$out"
  echo "TRAIN_START model=$model layers=$layers time=$(date)" | tee -a "$STATUS"
  "$PY" "$SCRIPT" \
    --out-root "$out" \
    --layers "$layers" \
    --epochs 50 \
    --batch-size 2 \
    --model-name "$model" \
    --train-data "$TRAIN_JSON" \
    --train-img-root "$TRAIN_IMG" \
    --eval-data "$EVAL_JSON" \
    --eval-img-root "$EVAL_IMG" \
    --config-path "$config" \
    --skip-eval \
    > "$out/train_top3.log" 2>&1
  local rc=$?
  echo "TRAIN_END model=$model rc=$rc time=$(date)" | tee -a "$STATUS"
  return $rc
}

run_eval_one() {
  local model="$1" layer="$2" config="$3" out="$RUN_ROOT/$1"
  echo "EVAL_START model=$model layer=$layer time=$(date)" | tee -a "$STATUS"
  "$PY" "$SCRIPT" \
    --out-root "$out" \
    --layers "$layer" \
    --epochs 50 \
    --batch-size 2 \
    --model-name "$model" \
    --train-data "$TRAIN_JSON" \
    --train-img-root "$TRAIN_IMG" \
    --eval-data "$EVAL_JSON" \
    --eval-img-root "$EVAL_IMG" \
    --config-path "$config" \
    --skip-train \
    > "$out/eval_L${layer}.log" 2>&1
  local rc=$?
  echo "EVAL_END model=$model layer=$layer rc=$rc time=$(date)" | tee -a "$STATUS"
  return $rc
}

run_model_top3() {
  local model="$1" layers_csv="$2" config="$3"
  run_train "$model" "$layers_csv" "$config" || return 0
  IFS=',' read -ra LAYERS <<< "$layers_csv"
  for layer in "${LAYERS[@]}"; do
    run_eval_one "$model" "$layer" "$config" || true
  done
}

run_model_top3 paligemma-3b "12,11,10" configs/vead/paligemma-3b.yaml
run_model_top3 smolvlm-1.7b "17,16,15" configs/vead/smolvlm-1.7b.yaml

echo "PALI_SMOL_ALL_FINISHED $(date)" | tee -a "$STATUS"
