#!/usr/bin/env bash
set -euo pipefail

REPO="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
OUT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/llava-v1.5-7b"
LOG="$OUT/train_L27_once_direct_20260617.log"

cd "$REPO"
setsid -f bash -lc "cd '$REPO' && CUDA_VISIBLE_DEVICES=1 /datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python scripts/run_evqa_pilot500_blip2_visedit_sweep.py --out-root '$OUT' --layers 27 --epochs 50 --batch-size 2 --model-name llava-v1.5-7b --train-data /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json --train-img-root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image --eval-data /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_eval_evqa_compat.json --eval-img-root /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image --config-path configs/vead/llava-v1.5-7b.yaml --skip-eval > '$LOG' 2>&1"
sleep 1
pgrep -af "run_evqa_pilot500_blip2_visedit_sweep.py --out-root $OUT --layers 27" || true
