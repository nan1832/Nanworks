#!/usr/bin/env bash
set -uo pipefail

ROOT=/tmp/ph_teacher3/paligemma_priority_reruns_job3044208_20260718_160000
STATUS="$ROOT/status.log"
OLD_LAUNCHER=3253754
RESUME_SCRIPT=/tmp/run_paligemma_priority_reruns_job3044208_20260718.sh
L12_PATTERN="$ROOT/2_mmke-entity_stable-buffer1_L12"

echo "HANDOFF_WATCH_START old_launcher=$OLD_LAUNCHER time=$(date '+%F %T')" >> "$STATUS"

while pgrep -af 'run_evqa_pilot500_blip2_visedit_sweep_pali_retry_rollback.py' | grep -Fq "$L12_PATTERN"; do
  sleep 30
done

sleep 10

if pgrep -af 'run_evqa_pilot500_blip2_visedit_sweep_pali_retry_rollback.py' | grep -Fq "$ROOT/3_"; then
  echo "HANDOFF_NOT_NEEDED reason=order3_already_started time=$(date '+%F %T')" >> "$STATUS"
  exit 0
fi

if kill -0 "$OLD_LAUNCHER" 2>/dev/null; then
  for child in $(pgrep -P "$OLD_LAUNCHER" 2>/dev/null || true); do
    child_cmd=$(ps -p "$child" -o cmd= 2>/dev/null || true)
    if [[ "$child_cmd" == sleep* ]]; then
      kill -TERM "$child" 2>/dev/null || true
    elif [[ -n "$child_cmd" ]]; then
      echo "HANDOFF_ABORT active_unexpected_child=$child cmd=$child_cmd time=$(date '+%F %T')" >> "$STATUS"
      exit 3
    fi
  done
  kill -TERM "$OLD_LAUNCHER" 2>/dev/null || true
  for _ in $(seq 1 20); do
    kill -0 "$OLD_LAUNCHER" 2>/dev/null || break
    sleep 1
  done
fi

rmdir "$ROOT/launcher.lock" 2>/dev/null || true
echo "HANDOFF_START_RESUME order=3 time=$(date '+%F %T')" >> "$STATUS"
START_ORDER=3 nohup bash "$RESUME_SCRIPT" \
  >/tmp/paligemma_priority_reruns_job3044208_20260718_resume3.nohup 2>&1 &
echo "HANDOFF_NEW_LAUNCHER pid=$! time=$(date '+%F %T')" >> "$STATUS"
