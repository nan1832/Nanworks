#!/usr/bin/env bash
set -uo pipefail

ROOT=${1:?usage: monitor_cleanup_completed_layers ROOT}
LOG="$ROOT/post_eval_cleanup_monitor.log"
mkdir -p "$ROOT"

cleanup_ready_layers() {
  local done layer model cache selected selected_abs layer_abs cache_abs bytes
  while IFS= read -r -d '' done; do
    layer=$(dirname "$done")
    [[ -f "$layer/train.done" && -s "$layer/selected_checkpoint.tsv" ]] || continue
    find "$layer/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q . || continue
    selected=$(tail -n 1 "$layer/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')
    [[ -n "$selected" && -e "$selected" ]] || continue
    selected_abs=$(realpath -e "$selected") || continue
    layer_abs=$(realpath -e "$layer") || continue
    case "$selected_abs" in "$layer_abs"/*) ;; *) continue ;; esac
    model=$(dirname "$layer_abs")
    cache="$model/cache/$(basename "$layer_abs")"
    [[ -e "$cache" ]] || continue
    cache_abs=$(realpath -e "$cache") || continue
    case "$cache_abs" in "$model"/cache/layer_*) ;; *) continue ;; esac
    bytes=$(du -sb "$cache_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$cache_abs"
    printf '%s CLEANED cache=%s bytes=%s layer=%s\n' "$(date '+%F %T %Z')" "$cache_abs" "${bytes:-0}" "$layer_abs" >>"$LOG"
  done < <(find "$ROOT" -type f -name eval_full.done -print0 2>/dev/null)
}

while :; do
  cleanup_ready_layers
  if [[ -f "$ROOT/QUEUE_DONE" || -f "$ROOT/QUEUE_FINISHED_WITH_FAILURES" ]]; then
    cleanup_ready_layers
    exit 0
  fi
  sleep 300
done
