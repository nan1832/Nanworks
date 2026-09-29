#!/usr/bin/env bash
set -u

ROOT=/tmp/ph_teacher3/mmke_visual_minigpt_llava_job3044841_20260728
MODEL_ROOT="$ROOT/minigpt-4-vicuna-7b"
LAUNCHER_PID=1145153
LAUNCHER_SCRIPT=launch_mmke_visual_minigpt_llava_job3044841_20260728.sh
LOG="$ROOT/minigpt5_only_stop_watcher.log"

log() {
  printf '%s %s\n' "$(date '+%F %T %Z')" "$*" >> "$LOG"
}

layer_complete() {
  local ll="$1" d="$MODEL_ROOT/layer_$ll"
  [[ -s "$d/train.done" ]] || return 1
  [[ -s "$d/selected_checkpoint.tsv" ]] || return 1
  [[ -s "$d/eval_full.done" ]] || return 1
  find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q .
}

log "WATCHER_START launcher_pid=$LAUNCHER_PID policy=minigpt5_only layers=L0,L1,L2,L3,L29"

while true; do
  if ! kill -0 "$LAUNCHER_PID" 2>/dev/null; then
    log "WATCHER_EXIT launcher_not_running"
    exit 0
  fi

  cmd=$(tr '\0' ' ' < "/proc/$LAUNCHER_PID/cmdline" 2>/dev/null || true)
  case "$cmd" in
    *"$LAUNCHER_SCRIPT"*) ;;
    *)
      log "WATCHER_ABORT pid_identity_mismatch cmd=$cmd"
      exit 3
      ;;
  esac

  complete=1
  for ll in 00 01 02 03 29; do
    layer_complete "$ll" || complete=0
  done

  if [[ "$complete" -eq 1 ]]; then
    # eval_full.done can appear just before the evaluator exits.  Wait until
    # the L29 runner is gone; the launcher then has a built-in 15-second gap
    # before it could start the next model.
    if ! pgrep -f "run_mmke_minigpt_llava_lowmem_sweep.py.*--out-root $MODEL_ROOT.*--layers 29" >/dev/null 2>&1; then
      log "MINIGPT5_COMPLETE all_required_artifacts_present; stopping launcher before LLaVA"
      kill -TERM "$LAUNCHER_PID"
      for _ in $(seq 1 20); do
        kill -0 "$LAUNCHER_PID" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$LAUNCHER_PID" 2>/dev/null; then
        log "LAUNCHER_TERM_PENDING no_KILL_sent"
        exit 4
      fi
      log "LAUNCHER_STOPPED job_allocation_preserved"
      touch "$ROOT/MINIGPT5_QUEUE_DONE_NO_LLAVA"
      exit 0
    fi
  fi

  sleep 1
done
