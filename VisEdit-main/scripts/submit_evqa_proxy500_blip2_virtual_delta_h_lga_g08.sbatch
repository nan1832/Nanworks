#!/bin/bash
#SBATCH --job-name=evqa-lga-b2
#SBATCH --partition=phys_hq
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --nodelist=g08
#SBATCH --time=2-00:00:00
#SBATCH --output=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy500_blip2_virtual_delta_h_lga_slurm/slurm-%j.out
#SBATCH --error=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy500_blip2_virtual_delta_h_lga_slurm/slurm-%j.err

set -euo pipefail

mkdir -p /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy500_blip2_virtual_delta_h_lga_slurm
export GPU_ID=${GPU_ID:-0}

/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/run_evqa_proxy500_blip2_virtual_delta_h_lga_g08.sh
