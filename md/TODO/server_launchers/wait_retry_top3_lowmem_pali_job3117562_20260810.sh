#!/usr/bin/env bash
set -uo pipefail

OLD_SRUN_PID=1003673
REPO=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
LOG=/var/tmp/ph_teacher3_top3_lowmem_job3117562_20260810_retry.srun.log
PID_FILE=/var/tmp/ph_teacher3_top3_lowmem_job3117562_20260810.srun.pid

while kill -0 "$OLD_SRUN_PID" 2>/dev/null; do
  sleep 60
done

nohup srun --overlap --jobid=3117562 \
  bash "$REPO/scripts/launch_top3_lowmem_pali_job3117562_20260810.sh" \
  >"$LOG" 2>&1 &
printf '%s\n' "$!" >"$PID_FILE"
