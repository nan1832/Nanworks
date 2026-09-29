#!/usr/bin/env bash
set -uo pipefail

ROLE=${1:?usage: run_formal_top3_stage2_replacement_job_20260827.sh job3126082|job3150065}
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
LAUNCHER=$PROJ/scripts/launch_formal_top3_stage2_20260812.sh
MONITOR=$PROJ/scripts/sync_completed_layers_to_shared_monitor_20260810.sh

case "$ROLE" in
  job3126082)
    ROOT=/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812
    DEST=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082
    TRAIN_ALLOW_NON_KERNEL=1
    ;;
  job3150065)
    ROOT=/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812
    DEST=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065
    TRAIN_ALLOW_NON_KERNEL=0
    ;;
  *)
    printf 'unknown role: %s\n' "$ROLE" >&2
    exit 2
    ;;
esac

mkdir -p "$DEST/recovery_logs"
LOG="$DEST/recovery_logs/replacement_job_${SLURM_JOB_ID:-unset}_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

printf 'RECOVERY_START role=%s original_root=%s actual_job=%s host=%s time=%s\n' \
  "$ROLE" "$ROOT" "${SLURM_JOB_ID:-unset}" "$(hostname)" "$(date '+%F %T %Z')"
printf 'RECOVERY_GPU_POLICY role=%s train_allow_non_kernel=%s train_min_free_mib=61440\n' \
  "$ROLE" "$TRAIN_ALLOW_NON_KERNEL"

[[ -d "$ROOT" ]] || { printf 'RECOVERY_REFUSED missing_root=%s\n' "$ROOT"; exit 20; }
[[ -x "$LAUNCHER" && -x "$MONITOR" ]] || { printf 'RECOVERY_REFUSED missing_script\n'; exit 21; }

monitor_pid=''
cleanup() {
  if [[ -n "$monitor_pid" ]] && kill -0 "$monitor_pid" 2>/dev/null; then
    kill -TERM "$monitor_pid" 2>/dev/null || true
    wait "$monitor_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT TERM INT

bash "$MONITOR" "$ROOT" "$DEST" &
monitor_pid=$!

export ALLOW_REPLACEMENT_JOB=1
export GPU_TRAIN_ALLOW_NON_KERNEL="$TRAIN_ALLOW_NON_KERNEL"
bash "$LAUNCHER" "$ROLE"
launcher_rc=$?
printf 'RECOVERY_LAUNCHER_END role=%s rc=%s time=%s\n' "$ROLE" "$launcher_rc" "$(date '+%F %T %Z')"

if [[ "$launcher_rc" -eq 0 && -f "$ROOT/QUEUE_DONE" ]]; then
  for _ in $(seq 1 180); do
    kill -0 "$monitor_pid" 2>/dev/null || break
    sleep 10
  done
fi

exit "$launcher_rc"
