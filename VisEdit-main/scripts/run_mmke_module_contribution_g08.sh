#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${JOB_ID:-2906639}"
PYTHON_BIN="${PYTHON_BIN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
PROJECT_ROOT="${PROJECT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
DATA_ROOT="${DATA_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
OUT_ROOT="${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_module_contribution_$(date +%Y%m%d_%H%M%S)}"
DEVICE="${DEVICE:-cuda:0}"
DATA_N="${DATA_N:-999999}"

mkdir -p "${OUT_ROOT}"
echo "${OUT_ROOT}" > "${OUT_ROOT}/RUN_ROOT.txt"

cd "${PROJECT_ROOT}"

run_one() {
  local task="$1"
  local mode="$2"
  local model="$3"
  local out_dir="${OUT_ROOT}/${task}/${mode}/${model}"
  local data_path="${DATA_ROOT}/data_json/${task}_train.json"
  local img_root="${DATA_ROOT}/data_image"
  mkdir -p "${out_dir}"
  echo "[$(date '+%F %T')] start task=${task} mode=${mode} model=${model}" | tee -a "${OUT_ROOT}/run.log"

  if [[ "${model}" == "blip2-opt-2.7b" ]]; then
    srun --jobid="${JOB_ID}" --overlap "${PYTHON_BIN}" scripts/run_evqa_blip2_module_contribution_proxy500.py \
      --model-name blip2-opt-2.7b \
      --dataset-type mmke \
      --data-path "${data_path}" \
      --img-root-dir "${img_root}" \
      --out-dir "${out_dir}" \
      --data-n "${DATA_N}" \
      --key-mode "${mode}" \
      --device "${DEVICE}" \
      --config-path configs/p_track/blip2-opt-2.7b.yaml \
      > "${out_dir}/run.log" 2>&1
  else
    srun --jobid="${JOB_ID}" --overlap "${PYTHON_BIN}" scripts/run_evqa_module_contribution_pilot500_multi.py \
      --model-name "${model}" \
      --dataset-type mmke \
      --data-path "${data_path}" \
      --img-root-dir "${img_root}" \
      --out-dir "${out_dir}" \
      --data-n "${DATA_N}" \
      --key-mode "${mode}" \
      --device "${DEVICE}" \
      > "${out_dir}/run.log" 2>&1
  fi

  echo "[$(date '+%F %T')] done task=${task} mode=${mode} model=${model}" | tee -a "${OUT_ROOT}/run.log"
}

models=(
  blip2-opt-2.7b
  instructblip-vicuna-7b
  minigpt-4-vicuna-7b
  llava-v1.5-7b
  qwen2.5-vl-3b
  paligemma-3b
  smolvlm-1.7b
)

for task in entity visual; do
  for mode in alt pred; do
    for model in "${models[@]}"; do
      run_one "${task}" "${mode}" "${model}"
    done
  done
done

echo "[$(date '+%F %T')] all done" | tee -a "${OUT_ROOT}/run.log"
