#!/bin/bash
#SBATCH --job-name=bridge-sweep
#SBATCH --partition=phys_hq
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --nodelist=g08
#SBATCH --time=3-00:00:00
#SBATCH --output=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main/server_results/text-adapter-location/scheme2-layer-sweep-e80/slurm-%j.out
#SBATCH --error=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main/server_results/text-adapter-location/scheme2-layer-sweep-e80/slurm-%j.err

set -euo pipefail

PROJECT_DIR=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
OUT_ROOT=server_results/text-adapter-location/scheme2-layer-sweep-e80
PYTHON_BIN=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python

cd "$PROJECT_DIR"
mkdir -p "$OUT_ROOT"
export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}"

"$PYTHON_BIN" scripts/run_bridge_text_layer_sweep.py \
  --device cuda:0 \
  --single_gpu \
  --layers 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 \
  --epochs 80 \
  --train_name_prefix bridge_text_scheme2 \
  --out_root "$OUT_ROOT"
