#!/usr/bin/env bash
set -euo pipefail

dataset=$1
model=$2
stage=$3
manifest=$4
out_dir=$5
cache=$6
data_path=$7
image_root=$8
config=$9

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
PROJECT="$ROOT/VisEdit-main"
RUNNER="$PROJECT/scripts/run_cma_modelpred_direct_formal_multinoise_all.py"
PY="$ROOT/envs/qwen25vl/bin/python"

cd "$PROJECT"
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "[$(date '+%F %T %Z')] start dataset=$dataset model=$model stage=$stage host=$(hostname)"
exec "$PY" "$RUNNER" \
  --project-root "$PROJECT" \
  --dataset-name "$dataset" \
  --model-name "$model" \
  --data-path "$data_path" \
  --image-root "$image_root" \
  --config "$config" \
  --manifest "$manifest" \
  --model-pred-cache "$cache" \
  --out-dir "$out_dir" \
  --device cuda:0 \
  --noise-scales 0.5,1.0,2.0 \
  --seeds 0,1,2 \
  --delta-logprob 0.05 \
  --run-mode "$stage"
