#!/usr/bin/env bash
#SBATCH -J lga_repair6_g07
#SBATCH -p phys_hq
#SBATCH --nodelist=g07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=125G
#SBATCH --gres=gpu:1
#SBATCH --time=3-00:00:00
#SBATCH -o /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900/logs/lga_repair6_g07_%j.out
#SBATCH -e /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900/logs/lga_repair6_g07_%j.err

set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python

cd "$PROJ"
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

mkdir -p "$ROOT/logs"
echo "LGA_REPAIR6_G07_START time=$(date) host=$(hostname) root=$ROOT"
nvidia-smi --query-gpu=index,uuid,name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits || true

backup_outputs() {
  local dataset="$1"
  local model="$2"
  local out_dir="$ROOT/$dataset/$model"
  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$out_dir"
  for f in progress.jsonl skipped_samples.jsonl layer_failure_log.jsonl layer_scores.csv candidate_layers_topk.csv summary.json sanity_check.json; do
    if [ -f "$out_dir/$f" ]; then
      mv "$out_dir/$f" "$out_dir/${f}.before_g07_repair_${ts}"
    fi
  done
}

collect_summary() {
  "$PY" scripts/run_lga_param_direct_altmodelpred_candidate_layers.py collect --run-root "$ROOT" >>"$ROOT/collect.log" 2>&1 || true
}

run_normal() {
  local dataset="$1"
  local model="$2"
  local out_dir="$ROOT/$dataset/$model"
  local log="$ROOT/logs/${dataset}__${model}_g07_repair_normal.log"
  backup_outputs "$dataset" "$model"
  echo "RUN_NORMAL_START time=$(date) dataset=$dataset model=$model"
  "$PY" scripts/run_lga_param_direct_altmodelpred_candidate_layers.py run-one \
    --dataset-name "$dataset" \
    --model-name "$model" \
    --out-dir "$out_dir" \
    --device cuda:0 \
    --max-new-tokens 32 \
    --resume >"$log" 2>&1
  echo "RUN_NORMAL_END time=$(date) dataset=$dataset model=$model"
  collect_summary
}

run_lowmem() {
  local dataset="$1"
  local model="$2"
  local out_dir="$ROOT/$dataset/$model"
  local log="$ROOT/logs/${dataset}__${model}_g07_repair_lowmem.log"
  backup_outputs "$dataset" "$model"
  echo "RUN_LOWMEM_START time=$(date) dataset=$dataset model=$model"
  "$PY" scripts/run_lga_param_direct_altmodelpred_lowmem_candidate_layers.py \
    --dataset-name "$dataset" \
    --model-name "$model" \
    --out-dir "$out_dir" \
    --device cuda:0 \
    --max-new-tokens 32 \
    --layer-batch-size 4 \
    --resume >"$log" 2>&1
  echo "RUN_LOWMEM_END time=$(date) dataset=$dataset model=$model"
  collect_summary
}

# Missing group: previous rc=137 was Slurm step cancellation / killed run, not a formula failure.
run_normal evqa-pilot500 llava-v1.5-7b

# Unavailable groups: previous runs skipped all samples due CUDA OOM.
run_lowmem mmke-visual instructblip-vicuna-7b
run_lowmem mmke-visual minigpt-4-vicuna-7b
run_lowmem mmke-visual llava-v1.5-7b
run_lowmem mmke-entity instructblip-vicuna-7b
run_lowmem mmke-entity minigpt-4-vicuna-7b

collect_summary
echo "LGA_REPAIR6_G07_DONE time=$(date) root=$ROOT"
