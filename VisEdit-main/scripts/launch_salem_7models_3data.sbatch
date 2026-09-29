#!/usr/bin/env bash
#SBATCH --job-name=salem7x3
#SBATCH --partition=phys_hq
#SBATCH --account=phys_hq_teacher
#SBATCH --qos=gpu_xl_2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=80G
#SBATCH --time=7-00:00:00
#SBATCH --chdir=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
#SBATCH --output=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/salem_candidate_layers_logs/slurm-%j.out
#SBATCH --error=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/salem_candidate_layers_logs/slurm-%j.err

set -u

PROJECT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
cd "$PROJECT_ROOT"

mkdir -p /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/salem_candidate_layers_logs

if [ -x /datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python ]; then
  PYTHON=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
elif [ -x /datapool/home/ph_teacher3/Lwy/.lico_env/jupyter/env/bin/python ]; then
  PYTHON=/datapool/home/ph_teacher3/Lwy/.lico_env/jupyter/env/bin/python
else
  PYTHON=python
fi

TS=$(date +%Y%m%d_%H%M%S)
RUN_ROOT=${SALEM_RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/salem_candidate_layers_7models_3data_${TS}_${SLURM_JOB_ID}}
mkdir -p "$RUN_ROOT"

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

echo "[SaLEM] job=$SLURM_JOB_ID node=$(hostname) cuda_visible=${CUDA_VISIBLE_DEVICES:-unset}"
echo "[SaLEM] python=$PYTHON"
echo "[SaLEM] run_root=$RUN_ROOT"
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
    LOG_DIR="$RUN_ROOT/logs/$DATASET"
    mkdir -p "$LOG_DIR"
    if [ -f "$OUT_DIR/summary.json" ]; then
      echo "[SaLEM][SKIP] $DATASET $MODEL already done"
      continue
    fi
    echo "[SaLEM][START] dataset=$DATASET model=$MODEL"
    "$PYTHON" scripts/run_salem_candidate_layers.py run-one \
      --dataset-name "$DATASET" \
      --model-name "$MODEL" \
      --out-dir "$OUT_DIR" \
      --device cuda:0 \
      --resume \
      > "$LOG_DIR/${MODEL}.log" 2>&1
    RC=$?
    if [ "$RC" -ne 0 ]; then
      echo "[SaLEM][FAIL] dataset=$DATASET model=$MODEL rc=$RC"
      printf "%s\t%s\t%s\n" "$DATASET" "$MODEL" "$RC" >> "$FAILED_TSV"
    else
      echo "[SaLEM][DONE] dataset=$DATASET model=$MODEL"
    fi
    "$PYTHON" scripts/run_salem_candidate_layers.py collect --run-root "$RUN_ROOT" \
      > "$RUN_ROOT/collect_latest.log" 2>&1 || true
    nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
  done
done

"$PYTHON" scripts/run_salem_candidate_layers.py collect --run-root "$RUN_ROOT"
echo "[SaLEM] all done or attempted; run_root=$RUN_ROOT"
