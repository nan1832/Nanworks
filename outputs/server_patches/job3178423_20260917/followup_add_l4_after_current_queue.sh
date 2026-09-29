#!/usr/bin/env bash
set -euo pipefail

JOB_ID=3178423
CURRENT_SRUN_PID=2810670
PROJECT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
WRAPPER="$PROJECT/scripts/run_formal_top3_stage2_replacement_job_20260827.sh"
RESULT_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082

printf 'FOLLOWUP_WAIT_START job=%s watched_srun_pid=%s time=%s\n' \
  "$JOB_ID" "$CURRENT_SRUN_PID" "$(date '+%F %T %Z')"

while kill -0 "$CURRENT_SRUN_PID" 2>/dev/null; do
  sleep 60
done

if ! squeue -h -j "$JOB_ID" 2>/dev/null | grep -q .; then
  printf 'FOLLOWUP_NOT_STARTED reason=allocation_not_active job=%s time=%s\n' \
    "$JOB_ID" "$(date '+%F %T %Z')"
  exit 0
fi

mkdir -p "$RESULT_ROOT/recovery_logs"
run_log="$RESULT_ROOT/recovery_logs/srun_followup_add_l4_job${JOB_ID}_$(date +%Y%m%d_%H%M%S).log"
printf 'FOLLOWUP_START job=%s log=%s time=%s\n' \
  "$JOB_ID" "$run_log" "$(date '+%F %T %Z')"

exec srun --jobid="$JOB_ID" --overlap --nodes=1 --ntasks=1 \
  --cpus-per-task=1 --mem=125G --gres=gpu:1 \
  bash "$WRAPPER" job3126082 >"$run_log" 2>&1
