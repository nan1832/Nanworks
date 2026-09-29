#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
PROJECT="$ROOT/VisEdit-main"
OUT="$ROOT/server_results/cma_modelpred_direct_formal_multinoise_multiseed_v1_20260906/smoke2"
CACHE="$ROOT/server_results/ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304/mmke-entity/qwen2.5-vl-3b/model_pred_cache.jsonl"
DATA="$ROOT/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json"
IMAGES="$ROOT/datasets/MMKE-Bench/data_image"
CONFIG="$PROJECT/configs/p_track/qwen2.5-vl-3b.yaml"
RUNNER="$PROJECT/scripts/run_cma_modelpred_direct_formal_multinoise_v1.py"
PY="$ROOT/envs/qwen25vl/bin/python"

cd "$PROJECT"
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1 | tr -d ' ')
echo "[$(date '+%F %T %Z')] smoke start host=$(hostname) free_mib=$free_mib"
if (( free_mib < 35000 )); then
  echo "ABORT insufficient free GPU memory: ${free_mib} MiB < 35000 MiB" >&2
  exit 75
fi

exec "$PY" "$RUNNER" \
  --project-root "$PROJECT" \
  --data-path "$DATA" \
  --image-root "$IMAGES" \
  --config "$CONFIG" \
  --manifest "$OUT/input_manifest.json" \
  --model-pred-cache "$CACHE" \
  --out-dir "$OUT" \
  --device cuda:0 \
  --noise-scales 0.5,1.0,2.0 \
  --seeds 0,1,2 \
  --delta-logprob 0.05 \
  --run-mode smoke
