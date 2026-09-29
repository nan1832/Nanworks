#!/usr/bin/env bash
set -u

PROJECT="${PROJECT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
PY="${PY:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_$(date +%Y%m%d_%H%M%S)}"
LOG_ROOT="$RUN_ROOT/logs"

mkdir -p "$LOG_ROOT"
cd "$PROJECT" || exit 2
export PYTHONPATH="$PROJECT:${PYTHONPATH:-}"

echo "LGA_PARAM_DIRECT_ALTMODELPRED_START time=$(date) host=$(hostname) run_root=$RUN_ROOT" | tee -a "$RUN_ROOT/driver.log"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}" | tee -a "$RUN_ROOT/driver.log"

DATASETS=(
  evqa-pilot500
  mmke-visual
  mmke-entity
)

MODELS=(
  blip2-opt-2.7b
  instructblip-vicuna-7b
  minigpt-4-vicuna-7b
  llava-v1.5-7b
  qwen2.5-vl-3b
  paligemma-3b
  smolvlm-1.7b
)

for dataset in "${DATASETS[@]}"; do
  for model in "${MODELS[@]}"; do
    out_dir="$RUN_ROOT/$dataset/$model"
    log_file="$LOG_ROOT/${dataset}__${model}.log"
    echo "RUN_ONE_START time=$(date) dataset=$dataset model=$model out_dir=$out_dir" | tee -a "$RUN_ROOT/driver.log"
    "$PY" scripts/run_lga_param_direct_altmodelpred_candidate_layers.py run-one \
      --dataset-name "$dataset" \
      --model-name "$model" \
      --out-dir "$out_dir" \
      --device cuda:0 \
      --max-new-tokens 32 \
      --resume >"$log_file" 2>&1
    rc=$?
    echo "RUN_ONE_END time=$(date) dataset=$dataset model=$model rc=$rc log=$log_file" | tee -a "$RUN_ROOT/driver.log"
    "$PY" scripts/run_lga_param_direct_altmodelpred_candidate_layers.py collect --run-root "$RUN_ROOT" >>"$RUN_ROOT/collect.log" 2>&1 || true
    if [ "$rc" -ne 0 ]; then
      echo "RUN_ONE_FAILED_CONTINUE dataset=$dataset model=$model rc=$rc" | tee -a "$RUN_ROOT/driver.log"
    fi
  done
done

"$PY" scripts/run_lga_param_direct_altmodelpred_candidate_layers.py collect --run-root "$RUN_ROOT" >>"$RUN_ROOT/collect.log" 2>&1 || true
echo "LGA_PARAM_DIRECT_ALTMODELPRED_DONE time=$(date) run_root=$RUN_ROOT" | tee -a "$RUN_ROOT/driver.log"
