#!/usr/bin/env bash
set -u

PROJECT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
cd "$PROJECT_ROOT" || exit 1

if [ -x /datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python ]; then
  PYTHON=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
elif [ -x /datapool/home/ph_teacher3/Lwy/.lico_env/jupyter/env/bin/python ]; then
  PYTHON=/datapool/home/ph_teacher3/Lwy/.lico_env/jupyter/env/bin/python
else
  PYTHON=python
fi

TS=$(date +%Y%m%d_%H%M%S)
RUN_ROOT=${SALEM_RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/salem_candidate_layers_7models_3data_current_alloc_${TS}}
LOG_ROOT="$RUN_ROOT/logs"
mkdir -p "$LOG_ROOT"

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

echo "[SaLEM-current] start time=$(date) host=$(hostname) cuda_visible=$CUDA_VISIBLE_DEVICES"
echo "[SaLEM-current] run_root=$RUN_ROOT"
nvidia-smi || true

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

FAILED_TSV="$RUN_ROOT/failed_jobs.tsv"
printf "dataset\tmodel\texit_code\n" > "$FAILED_TSV"

for DATASET in "${DATASETS[@]}"; do
  for MODEL in "${MODELS[@]}"; do
    OUT_DIR="$RUN_ROOT/$DATASET/$MODEL"
    DATASET_LOG_DIR="$LOG_ROOT/$DATASET"
    mkdir -p "$DATASET_LOG_DIR"
    if [ -f "$OUT_DIR/summary.json" ]; then
      echo "[SaLEM-current][SKIP] $DATASET $MODEL"
      continue
    fi
    echo "[SaLEM-current][START] dataset=$DATASET model=$MODEL time=$(date)"
    "$PYTHON" scripts/run_salem_candidate_layers.py run-one \
      --dataset-name "$DATASET" \
      --model-name "$MODEL" \
      --out-dir "$OUT_DIR" \
      --device cuda:0 \
      --resume \
      > "$DATASET_LOG_DIR/${MODEL}.log" 2>&1
    RC=$?
    if [ "$RC" -ne 0 ]; then
      echo "[SaLEM-current][FAIL] dataset=$DATASET model=$MODEL rc=$RC time=$(date)"
      printf "%s\t%s\t%s\n" "$DATASET" "$MODEL" "$RC" >> "$FAILED_TSV"
    else
      echo "[SaLEM-current][DONE] dataset=$DATASET model=$MODEL time=$(date)"
    fi
    "$PYTHON" scripts/run_salem_candidate_layers.py collect --run-root "$RUN_ROOT" \
      > "$RUN_ROOT/collect_latest.log" 2>&1 || true
    nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
  done
done

"$PYTHON" scripts/run_salem_candidate_layers.py collect --run-root "$RUN_ROOT" || true
echo "[SaLEM-current] salem attempted time=$(date) run_root=$RUN_ROOT"

echo "[SaLEM-current] resume pilot500 training time=$(date)"
GPU_ID=0 PY_BASE="$PYTHON" bash scripts/resume_pilot500_top3_nonpali.sh \
  > "$RUN_ROOT/resume_pilot500_after_salem.log" 2>&1
RESUME_RC=$?
echo "[SaLEM-current] resume pilot500 finished rc=$RESUME_RC time=$(date)"
exit "$RESUME_RC"
