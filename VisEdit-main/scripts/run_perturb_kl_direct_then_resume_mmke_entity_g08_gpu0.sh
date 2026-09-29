#!/usr/bin/env bash
set -u

PROJECT_ROOT="${PROJECT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
SERVER_RESULTS="${SERVER_RESULTS:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results}"
PYTHON_BIN="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

TS="$(date +%Y%m%d_%H%M%S)"
RUN_ROOT="${PERTURB_KL_RUN_ROOT:-${SERVER_RESULTS}/perturb_kl_direct_7models_3datasets_g08_gpu0_${TS}}"
LOG_ROOT="${RUN_ROOT}/logs"
mkdir -p "$LOG_ROOT"

cd "$PROJECT_ROOT" || exit 2
export PATH="/usr/bin:/usr/local/cuda/bin:${PATH:-}"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

MODELS=(
  blip2-opt-2.7b
  instructblip-vicuna-7b
  minigpt-4-vicuna-7b
  llava-v1.5-7b
  qwen2.5-vl-3b
  paligemma-3b
  smolvlm-1.7b
)

DATASETS=(
  evqa-pilot500
  mmke-visual
  mmke-entity
)

FAILED_TSV="${RUN_ROOT}/failed_jobs.tsv"
echo -e "dataset\tmodel\trc\tlog" > "$FAILED_TSV"

echo "[START] $(date)"
echo "[INFO] host=$(hostname) CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
echo "[INFO] run_root=${RUN_ROOT}"
echo "[INFO] python=${PYTHON_BIN}"
nvidia-smi || true

for dataset in "${DATASETS[@]}"; do
  for model in "${MODELS[@]}"; do
    out_dir="${RUN_ROOT}/${dataset}/${model}"
    log_file="${LOG_ROOT}/${dataset}__${model}.log"
    mkdir -p "$out_dir"
    echo "[RUN] $(date) dataset=${dataset} model=${model} log=${log_file}"

    set +e
    "$PYTHON_BIN" scripts/run_perturb_kl_direct_candidate_layers.py run-one \
      --dataset-name "$dataset" \
      --model-name "$model" \
      --out-dir "$out_dir" \
      --device cuda:0 \
      --noise-scales "${NOISE_SCALES:-0.1,0.5,1,3}" \
      --repeats "${PERTURB_REPEATS:-2026,2027,2028}" \
      --resume \
      > "$log_file" 2>&1
    rc=$?
    set -e

    if [[ "$rc" -ne 0 ]]; then
      echo "[FAIL] dataset=${dataset} model=${model} rc=${rc}; see ${log_file}"
      echo -e "${dataset}\t${model}\t${rc}\t${log_file}" >> "$FAILED_TSV"
    else
      echo "[DONE] dataset=${dataset} model=${model}"
    fi

    "$PYTHON_BIN" scripts/run_perturb_kl_direct_candidate_layers.py collect \
      --run-root "$RUN_ROOT" \
      > "${LOG_ROOT}/collect_latest.log" 2>&1 || true

    nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu \
      --format=csv,noheader,nounits || true
  done
done

"$PYTHON_BIN" scripts/run_perturb_kl_direct_candidate_layers.py collect \
  --run-root "$RUN_ROOT" \
  > "${LOG_ROOT}/collect_final.log" 2>&1 || true

echo "[PERTURB_KL_FINISHED] $(date)"
cat "$FAILED_TSV" || true

echo "[RESUME_MMKE_ENTITY] $(date)"
if [[ -x scripts/resume_mmke_entity_top3_nonpali_g07.sh ]]; then
  GPU_ID=0 MAX_USED_MIB="${MAX_USED_MIB:-4096}" PY_BASE="$PYTHON_BIN" \
    bash scripts/resume_mmke_entity_top3_nonpali_g07.sh \
    > "${RUN_ROOT}/resume_mmke_entity_after_perturb.log" 2>&1
  resume_rc=$?
  echo "[RESUME_MMKE_ENTITY_DONE] rc=${resume_rc} $(date)"
  exit "$resume_rc"
else
  echo "[RESUME_MMKE_ENTITY_MISSING] scripts/resume_mmke_entity_top3_nonpali_g07.sh"
  exit 3
fi
