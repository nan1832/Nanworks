#!/usr/bin/env bash
#SBATCH --job-name=mmkevis_llava
#SBATCH --partition=phys_hq
#SBATCH --account=phys_hq_teacher
#SBATCH --qos=gpu_xl_2
#SBATCH --nodes=1
#SBATCH --nodelist=g07
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=120G
#SBATCH --time=7-00:00:00
#SBATCH --output=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/slurm/mmkevis_llava_%j.out
#SBATCH --error=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/slurm/mmkevis_llava_%j.err

set -euo pipefail
REPO=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
RUN_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644
cd "$REPO"
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export RUN_ROOT
# In a Slurm GPU allocation, CUDA_VISIBLE_DEVICES is the authoritative visible GPU.
# Pass it through instead of hard-coding physical GPU 1.
export GPU_ID="${CUDA_VISIBLE_DEVICES:-0}"
export LAYERS_CSV="27,26,30,31,29,17,18,16"

echo "SLURM_LLAVA_VISUAL_START time=$(date) host=$(hostname) job=${SLURM_JOB_ID:-NA} CVD=${CUDA_VISIBLE_DEVICES:-unset} GPU_ID=$GPU_ID" | tee -a "$RUN_ROOT/mmke_visual_llava_slurm_status.log"
/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python -c 'import os, torch; print("CUDA_CHECK", os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NA", flush=True)'
bash scripts/launch_mmke_visual_llava_direct_g07.sh
rc=$?
echo "SLURM_LLAVA_VISUAL_END time=$(date) rc=$rc" | tee -a "$RUN_ROOT/mmke_visual_llava_slurm_status.log"
exit $rc
