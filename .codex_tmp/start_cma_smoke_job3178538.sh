#!/usr/bin/env bash
set -euo pipefail

PROJECT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
BASE=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_formal_multinoise_multiseed_v1_20260906
PYTHON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python

export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8

cd "$PROJECT"
exec "$PYTHON" -u scripts/run_cma_direct_formal_multinoise_v1.py \
  --project-root "$PROJECT" \
  --data-path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json \
  --image-root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image \
  --config "$PROJECT/configs/p_track/qwen2.5-vl-3b.yaml" \
  --manifest "$BASE/manifests/smoke2.json" \
  --out-dir "$BASE/smoke2_v3" \
  --device cuda:0 \
  --noise-scales 0.5,1.0,2.0 \
  --seeds 0,1,2 \
  --delta-logprob 0.05 \
  --eps 1e-8 \
  --epsilon-sigma 1e-6 \
  --run-mode smoke \
  --include-historical-control \
  --resume
