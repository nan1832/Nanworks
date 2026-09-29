#!/usr/bin/env bash
set -euo pipefail

SCRATCH_ROOT="${SCRATCH_ROOT:?SCRATCH_ROOT is required}"
PARENT_STEP="${PARENT_STEP:-3044841.92}"
POLL_SECONDS="${POLL_SECONDS:-300}"
LOG="$SCRATCH_ROOT/post_eval_cleanup.log"

case "$SCRATCH_ROOT" in
  /tmp/ph_teacher3/mmke_entity_job3044841_*) ;;
  *) echo "Refusing unsafe scratch root: $SCRATCH_ROOT" >&2; exit 2 ;;
esac

cleanup_completed_layers() {
  local eval_done layer_dir model layer_name cache_dir selected f bytes

  while IFS= read -r -d '' eval_done; do
    layer_dir="$(dirname "$eval_done")"
    [[ ! -L "$layer_dir" ]] || continue
    [[ -f "$layer_dir/train.done" ]] || continue
    [[ -s "$layer_dir/selected_checkpoint.tsv" ]] || continue
    [[ ! -f "$layer_dir/.scratch_cleanup.done" ]] || continue

    selected="$(tail -n 1 "$layer_dir/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')"
    [[ -f "$selected" ]] || continue
    case "$selected" in "$layer_dir"/*/checkpoints/epoch-*) ;; *) continue ;; esac

    model="$(basename "$(dirname "$layer_dir")")"
    layer_name="$(basename "$layer_dir")"
    cache_dir="$SCRATCH_ROOT/$model/cache/$layer_name"
    case "$cache_dir" in "$SCRATCH_ROOT"/*/cache/layer_*) ;; *) continue ;; esac

    bytes=0
    if [[ -d "$cache_dir" ]]; then
      bytes="$(du -sb "$cache_dir" 2>/dev/null | awk '{print $1}')"
      rm -rf -- "$cache_dir"
    fi

    while IFS= read -r -d '' f; do
      [[ "$f" == "$selected" ]] || rm -f -- "$f"
    done < <(find "$layer_dir" -type f -path '*/checkpoints/epoch-*' -print0)

    touch "$layer_dir/.scratch_cleanup.done"
    printf '%s model=%s layer=%s cache_bytes=%s selected_kept=%s\n' \
      "$(date '+%F %T %z')" "$model" "$layer_name" "${bytes:-0}" "$selected" >> "$LOG"
  done < <(find "$SCRATCH_ROOT" -mindepth 3 -maxdepth 3 -type f -name eval_full.done -print0)
}

printf '%s cleanup_watch_start parent_step=%s root=%s poll=%s\n' \
  "$(date '+%F %T %z')" "$PARENT_STEP" "$SCRATCH_ROOT" "$POLL_SECONDS" >> "$LOG"

while scontrol show step "$PARENT_STEP" 2>/dev/null | grep -q 'State=RUNNING'; do
  cleanup_completed_layers
  sleep "$POLL_SECONDS"
done

cleanup_completed_layers
printf '%s cleanup_watch_end parent_step=%s\n' "$(date '+%F %T %z')" "$PARENT_STEP" >> "$LOG"
