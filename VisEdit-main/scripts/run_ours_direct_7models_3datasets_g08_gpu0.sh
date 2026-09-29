#!/usr/bin/env bash
set -u

# Run Ours-Direct candidate-layer localization on the current G08 allocation.
# This script assumes it is launched inside a Slurm/Jupyter job where only one
# physical GPU is visible as CUDA_VISIBLE_DEVICES=0.

PROJECT_ROOT="${PROJECT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
SERVER_RESULTS="${SERVER_RESULTS:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results}"
PYTHON_BIN="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

DATASETS=(${DATASETS:-evqa-pilot500 mmke-visual mmke-entity})
MODELS=(${MODELS:-blip2-opt-2.7b instructblip-vicuna-7b minigpt-4-vicuna-7b llava-v1.5-7b qwen2.5-vl-3b paligemma-3b smolvlm-1.7b})

DATA_N="${DATA_N:-}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-32}"
LOG_PREFIX="${LOG_PREFIX:-ours_direct}"
TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${OURS_DIRECT_RUN_ROOT:-${SERVER_RESULTS}/ours_direct_7models_3datasets_g08_gpu0_${TS}}"

export CUDA_VISIBLE_DEVICES
export PYTORCH_CUDA_ALLOC_CONF
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

mkdir -p "${RUN_ROOT}/logs"
cd "${PROJECT_ROOT}" || exit 2

echo "========== Ours-Direct 7 models x 3 datasets =========="
echo "Run root : ${RUN_ROOT}"
echo "Host     : $(hostname)"
echo "GPU      : CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
echo "Python   : ${PYTHON_BIN}"
echo "Datasets : ${DATASETS[*]}"
echo "Models   : ${MODELS[*]}"
date

for dataset in "${DATASETS[@]}"; do
  for model in "${MODELS[@]}"; do
    out_dir="${RUN_ROOT}/${dataset}/${model}"
    log_file="${RUN_ROOT}/logs/${LOG_PREFIX}_${dataset}_${model}.log"
    mkdir -p "${out_dir}"

    if [[ -f "${out_dir}/DONE" ]]; then
      echo "[SKIP] ${dataset} / ${model}: DONE already exists"
      continue
    fi

    echo "[RUN] ${dataset} / ${model}"
    cmd=(
      "${PYTHON_BIN}" "scripts/run_ours_direct_candidate_layers.py" "run-one"
      "--dataset-name" "${dataset}"
      "--model-name" "${model}"
      "--out-dir" "${out_dir}"
      "--device" "cuda:0"
      "--max-new-tokens" "${MAX_NEW_TOKENS}"
      "--resume"
    )
    if [[ -n "${DATA_N}" ]]; then
      cmd+=("--data-n" "${DATA_N}")
    fi

    "${cmd[@]}" >"${log_file}" 2>&1
    status=$?
    "${PYTHON_BIN}" "scripts/run_ours_direct_candidate_layers.py" "collect" \
      "--run-root" "${RUN_ROOT}" >>"${RUN_ROOT}/logs/${LOG_PREFIX}_collect.log" 2>&1

    if [[ ${status} -ne 0 ]]; then
      echo "[FAIL] ${dataset} / ${model}; status=${status}; log=${log_file}"
      echo "The launcher keeps going so other model/dataset pairs can finish."
    else
      echo "[DONE] ${dataset} / ${model}"
    fi

    # Let CUDA release memory before the next model is loaded.
    sleep 5
  done
done

"${PYTHON_BIN}" "scripts/run_ours_direct_candidate_layers.py" "collect" \
  "--run-root" "${RUN_ROOT}" >>"${RUN_ROOT}/logs/${LOG_PREFIX}_collect.log" 2>&1

echo "========== Ours-Direct finished =========="
echo "Summary CSV: ${RUN_ROOT}/ours_direct_candidates_summary.csv"
echo "Summary MD : ${RUN_ROOT}/ours_direct_candidates_summary.md"
date
