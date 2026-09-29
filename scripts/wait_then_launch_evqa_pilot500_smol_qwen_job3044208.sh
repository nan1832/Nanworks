#!/usr/bin/env bash
set -uo pipefail

CURRENT_LAUNCHER_PID="${CURRENT_LAUNCHER_PID:-2067100}"
CURRENT_LAUNCHER_NAME=launch_mmke_entity_smol_qwen_job3044208.sh
CURRENT_ROOT=/tmp/ph_teacher3/mmke_entity_smol_qwen_job3044208_20260721_105000
NEW_ROOT=/tmp/ph_teacher3/evqa_pilot500_smol_qwen_job3044208_20260723_202500
NEW_LAUNCHER=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/launch_evqa_pilot500_smol_qwen_job3044208.sh
HANDOFF_LOG="$NEW_ROOT/handoff.log"

mkdir -p "$NEW_ROOT"

log_handoff() {
  printf '%s\n' "$*" | tee -a "$HANDOFF_LOG"
}

old_launcher_alive() {
  [[ -r "/proc/$CURRENT_LAUNCHER_PID/cmdline" ]] || return 1
  tr '\0' ' ' <"/proc/$CURRENT_LAUNCHER_PID/cmdline" | grep -Fq "$CURRENT_LAUNCHER_NAME"
}

count_done() {
  local model="$1"
  find "$CURRENT_ROOT/$model" -mindepth 2 -maxdepth 2 -type f -name eval_full.done -size +0c 2>/dev/null | wc -l
}

log_handoff "HANDOFF_ARMED current_pid=$CURRENT_LAUNCHER_PID current_root=$CURRENT_ROOT new_launcher=$NEW_LAUNCHER time=$(date '+%F %T')"

while old_launcher_alive; do
  log_handoff "HANDOFF_WAIT current_pid=$CURRENT_LAUNCHER_PID time=$(date '+%F %T')"
  sleep 60
done

smol_done="$(count_done smolvlm-1.7b)"
qwen_done="$(count_done qwen2.5-vl-3b)"
if ! grep -q 'QUEUE_COMPLETE' "$CURRENT_ROOT/status.log" 2>/dev/null; then
  log_handoff "HANDOFF_BLOCKED reason=old_queue_missing_QUEUE_COMPLETE smol_done=$smol_done qwen_done=$qwen_done time=$(date '+%F %T')"
  exit 4
fi
if [[ "$smol_done" -ne 15 || "$qwen_done" -ne 18 ]]; then
  log_handoff "HANDOFF_BLOCKED reason=old_queue_incomplete smol_done=$smol_done expected_smol=15 qwen_done=$qwen_done expected_qwen=18 time=$(date '+%F %T')"
  exit 5
fi
if pgrep -af 'run_evqa_pilot500_blip2_visedit_sweep.py.*mmke_entity_smol_qwen_job3044208' >>"$HANDOFF_LOG" 2>&1; then
  log_handoff "HANDOFF_BLOCKED reason=old_runner_still_alive time=$(date '+%F %T')"
  exit 6
fi
if [[ ! -x "$NEW_LAUNCHER" ]]; then
  log_handoff "HANDOFF_BLOCKED reason=new_launcher_not_executable path=$NEW_LAUNCHER time=$(date '+%F %T')"
  exit 7
fi

log_handoff "HANDOFF_START smol_done=$smol_done qwen_done=$qwen_done time=$(date '+%F %T')"
exec "$NEW_LAUNCHER"
