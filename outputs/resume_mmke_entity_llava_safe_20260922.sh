#!/usr/bin/env bash
# Scoped recovery: same training/evaluation protocol, stricter GPU admission only.
set -euo pipefail
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
ROOT=/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812
DEST=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082
LAUNCHER=$PROJ/scripts/launch_formal_top3_stage2_20260812.sh
MONITOR=$PROJ/scripts/sync_completed_layers_to_shared_monitor_20260810.sh
[[ ${SLURM_JOB_ID:-} == 3178423 && $(hostname -s) == g07 ]] || exit 20
[[ -d "$ROOT" && -f "$LAUNCHER" && -f "$MONITOR" ]] || exit 21
grep -qx 'GPU_TRAIN_FREE_MIN_MIB=61440' "$LAUNCHER" || exit 22
export ALLOW_REPLACEMENT_JOB=1
export GPU_TRAIN_ALLOW_NON_KERNEL=0
printf 'SAFE_RESUME time=%s job=%s node=%s train_min_free_mib=73728 allow_non_kernel=0 eval_min_free_mib=56320\n' "$(date '+%F %T %Z')" "$SLURM_JOB_ID" "$(hostname)"
sha256sum "$LAUNCHER" "$MONITOR"
# Keep the original durable-archive/retention monitor; do not touch other jobs.
bash "$MONITOR" "$ROOT" "$DEST" &
monitor_pid=$!
cleanup() { kill -TERM "$monitor_pid" 2>/dev/null || true; wait "$monitor_pid" 2>/dev/null || true; }
trap cleanup EXIT
# Change only admission memory in this process; the shared launcher is not edited.
set +e
sed 's/^GPU_TRAIN_FREE_MIN_MIB=61440$/GPU_TRAIN_FREE_MIN_MIB=73728/' "$LAUNCHER" |
  bash -s -- job3126082
rc=${PIPESTATUS[1]}
set -e
printf 'SAFE_RESUME_EXIT rc=%s time=%s\n' "$rc" "$(date '+%F %T %Z')"
if [[ $rc == 0 && -f "$ROOT/QUEUE_DONE" ]]; then
  for ((i=0; i<180; i++)); do
    kill -0 "$monitor_pid" 2>/dev/null || break
    sleep 10
  done
fi
exit "$rc"
