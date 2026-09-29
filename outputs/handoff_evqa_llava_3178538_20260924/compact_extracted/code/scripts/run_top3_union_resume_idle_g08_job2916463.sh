#!/usr/bin/env bash
set -u

# Resume the 50-epoch top-3-union train/eval sweeps on the idle GPU allocated
# to Slurm/Jupyter job 2916463. Inside that allocation the idle physical card is
# exposed as CUDA_VISIBLE_DEVICES=0.

PROJECT_ROOT="${PROJECT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
SERVER_RESULTS="${SERVER_RESULTS:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results}"
GPU_ID="${GPU_ID:-0}"
MAX_USED_MIB="${MAX_USED_MIB:-4096}"
RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
LOG_DIR="${LOG_DIR:-${SERVER_RESULTS}/top3_union_resume_idle_g08_${RUN_TAG}}"

mkdir -p "$LOG_DIR"
cd "$PROJECT_ROOT" || exit 2
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

echo "TOP3_UNION_IDLE_RESUME_START time=$(date) host=$(hostname) gpu_id=$GPU_ID log_dir=$LOG_DIR"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

run_step() {
  local name="$1"
  shift
  local log="$LOG_DIR/${name}.log"
  echo "STEP_START name=$name time=$(date) cmd=$*" | tee -a "$LOG_DIR/driver.log"
  (
    set -u
    export GPU_ID="$GPU_ID"
    export MAX_USED_MIB="$MAX_USED_MIB"
    "$@"
  ) >"$log" 2>&1
  local rc=$?
  echo "STEP_END name=$name rc=$rc time=$(date) log=$log" | tee -a "$LOG_DIR/driver.log"
  return 0
}

run_step pilot500_resume_nonpali bash scripts/resume_pilot500_top3_nonpali.sh
run_step mmke_entity_resume_nonpali bash scripts/resume_mmke_entity_top3_nonpali_g07.sh
run_step mmke_visual_skipdone_atomic bash scripts/launch_mmke_visual_top3_union_skipdone_atomic_g07.sh

echo "TOP3_UNION_IDLE_RESUME_DONE time=$(date)" | tee -a "$LOG_DIR/driver.log"
