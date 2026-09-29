#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava}
TRAIN_LOG=${TRAIN_LOG:-$OUT_ROOT/full_layer_target0003_sweep.log}
EVAL_LOG=${EVAL_LOG:-$OUT_ROOT/full_layer_target0003_eval.log}
DONE_FILE=${DONE_FILE:-$OUT_ROOT/FULL_LAYER_TARGET0003_DONE.txt}
FAIL_FILE=${FAIL_FILE:-$OUT_ROOT/FULL_LAYER_TARGET0003_FAILED.txt}
CHECK_INTERVAL_SECONDS=${CHECK_INTERVAL_SECONDS:-1800}
EXPECTED_SELECTED=${EXPECTED_SELECTED:-32}

mkdir -p "$OUT_ROOT"
rm -f "$DONE_FILE" "$FAIL_FILE"

log() {
  echo "[$(date '+%F %T')] $*"
}

selected_count() {
  find "$OUT_ROOT" -name selected_checkpoint.tsv -type f 2>/dev/null | wc -l
}

training_running() {
  pgrep -f 'run_llava_request_only_remaining_layers_target_loss.sh|bridge_train_request_only.py' >/dev/null 2>&1
}

cd "$REPO_ROOT"

{
  log "watcher started"
  while true; do
    count=$(selected_count)
    if (( count >= EXPECTED_SELECTED )); then
      log "all selected checkpoints are ready count=$count"
      break
    fi

    if training_running; then
      log "training still running selected=$count/$EXPECTED_SELECTED"
      sleep "$CHECK_INTERVAL_SECONDS"
      continue
    fi

    log "training is not running but selected checkpoints are incomplete selected=$count/$EXPECTED_SELECTED"
    {
      echo "FAILED at $(date '+%F %T')"
      echo "selected=$count/$EXPECTED_SELECTED"
      echo "train_log=$TRAIN_LOG"
    } > "$FAIL_FILE"
    exit 1
  done

  log "starting unified evaluation"
  if bash scripts/eval_llava_request_only_selected_layers.sh > "$EVAL_LOG" 2>&1; then
    {
      echo "DONE at $(date '+%F %T')"
      echo "selected_checkpoints=$EXPECTED_SELECTED"
      echo "train_log=$TRAIN_LOG"
      echo "eval_log=$EVAL_LOG"
      echo "eval_summary=$OUT_ROOT/eval/selected_eval_summary.tsv"
    } > "$DONE_FILE"
    log "unified evaluation finished"
    if command -v wall >/dev/null 2>&1; then
      echo "Bridge30 LLaVA request-only layer sweep and evaluation finished: $DONE_FILE" | wall || true
    fi
  else
    {
      echo "FAILED during eval at $(date '+%F %T')"
      echo "selected_checkpoints=$EXPECTED_SELECTED"
      echo "eval_log=$EVAL_LOG"
    } > "$FAIL_FILE"
    log "evaluation failed"
    exit 1
  fi
} >> "$OUT_ROOT/full_layer_target0003_watch_eval.log" 2>&1
