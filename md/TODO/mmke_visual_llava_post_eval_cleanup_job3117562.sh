#!/usr/bin/env bash
set -u

ROOT=/tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730
OUT=$ROOT/llava-v1.5-7b
AUDIT=$ROOT/cleanup_audit
LOG=$ROOT/logs/post_eval_cleanup_watcher.log
LAYERS=(0 1 2 7 8 9 12 13 14 15 16 22 24 26 27)
EXPECTED_EVAL_SAMPLES=293
POLL_SECONDS=30

mkdir -p "$AUDIT" "$ROOT/logs"

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" >> "$LOG"
}

cleanup_layer() {
  local layer=$1 tag layer_dir done_marker eval_marker selected_tsv selected resolved
  local checkpoint_list deleted_list checkpoint_bytes=0 cache_bytes=0 total_bytes=0
  local deleted_count=0 f size cache_dir cache_resolved result_file

  tag=$(printf '%02d' "$layer")
  layer_dir=$OUT/layer_$tag
  done_marker=$layer_dir/post_eval_cleanup.done
  eval_marker=$layer_dir/eval_full.done
  selected_tsv=$layer_dir/selected_checkpoint.tsv

  [[ -f "$done_marker" ]] && return 0
  [[ -f "$layer_dir/train.done" ]] || return 0
  [[ -s "$selected_tsv" ]] || return 0
  [[ -s "$eval_marker" ]] || return 0
  grep -Eq '"status"[[:space:]]*:[[:space:]]*"EVAL_DONE"' "$eval_marker" || return 0
  grep -Eq '"eval_samples"[[:space:]]*:[[:space:]]*293([,[:space:]]|$)' "$eval_marker" || return 0

  # Do not clean while this layer still has an active train/eval process.
  if pgrep -af -- "--out-root $OUT.*--layers $layer([[:space:]]|$)" >/dev/null; then
    return 0
  fi

  selected=$(awk -F '\t' 'NR==2 {gsub(/\r/, "", $7); print $7}' "$selected_tsv")
  [[ -n "$selected" && -f "$selected" ]] || {
    log "L$tag skip: selected checkpoint missing"
    return 0
  }
  resolved=$(readlink -f -- "$selected")
  case "$resolved" in
    "$layer_dir"/records/*/checkpoints/epoch-*) ;;
    *) log "L$tag safety stop: selected path escaped layer: $resolved"; return 0 ;;
  esac

  result_file=$(find "$layer_dir/eval_full" -type f -size +0c \
    \( -name results.json -o -name mean_results.json \) -print -quit 2>/dev/null)
  [[ -n "$result_file" ]] || {
    log "L$tag skip: non-empty formal eval result missing"
    return 0
  }

  checkpoint_list=$AUDIT/L${tag}_checkpoint_files_before.tsv
  deleted_list=$AUDIT/L${tag}_deleted_nonselected_checkpoints.tsv
  : > "$checkpoint_list"
  : > "$deleted_list"
  while IFS= read -r -d '' f; do
    size=$(stat -c '%s' "$f")
    printf '%s\t%s\n' "$size" "$f" >> "$checkpoint_list"
  done < <(find "$layer_dir" -type f -path '*/checkpoints/*' -print0)

  sha256sum "$selected" > "$AUDIT/L${tag}_selected_sha256_before.txt"
  while IFS=$'\t' read -r size f; do
    [[ -n "$f" ]] || continue
    if [[ "$f" != "$selected" ]]; then
      [[ "$(stat -c '%U' "$f")" == ph_teacher3 ]] || {
        log "L$tag safety stop: foreign owner: $f"
        return 0
      }
      printf '%s\t%s\n' "$size" "$f" >> "$deleted_list"
      rm -f -- "$f"
      checkpoint_bytes=$((checkpoint_bytes + size))
      deleted_count=$((deleted_count + 1))
    fi
  done < "$checkpoint_list"

  cache_dir=$OUT/cache/layer_$tag
  if [[ -d "$cache_dir" ]]; then
    cache_resolved=$(readlink -f -- "$cache_dir")
    if [[ "$cache_resolved" == "$OUT/cache/layer_$tag" ]] && \
       [[ -z "$(find "$cache_dir" -xdev ! -user ph_teacher3 -print -quit)" ]]; then
      cache_bytes=$(du -sb "$cache_dir" | cut -f1)
      printf '%s\t%s\n' "$cache_bytes" "$cache_dir" > "$AUDIT/L${tag}_deleted_cache.tsv"
      rm -rf -- "$cache_dir"
    else
      log "L$tag safety stop: cache path/owner validation failed"
      return 0
    fi
  fi

  sha256sum -c "$AUDIT/L${tag}_selected_sha256_before.txt" \
    > "$AUDIT/L${tag}_selected_sha256_verify.txt" || {
      log "L$tag ERROR: selected checksum verification failed"
      return 0
    }
  [[ -f "$selected" && -s "$selected_tsv" && -s "$eval_marker" && -n "$result_file" ]] || {
    log "L$tag ERROR: post-cleanup invariant failed"
    return 0
  }

  total_bytes=$((checkpoint_bytes + cache_bytes))
  {
    printf 'status\tPOST_EVAL_CLEANUP_DONE\n'
    printf 'layer\t%s\n' "$layer"
    printf 'selected_checkpoint\t%s\n' "$selected"
    printf 'deleted_nonselected_checkpoint_files\t%s\n' "$deleted_count"
    printf 'deleted_nonselected_checkpoint_bytes\t%s\n' "$checkpoint_bytes"
    printf 'deleted_cache_bytes\t%s\n' "$cache_bytes"
    printf 'total_freed_bytes\t%s\n' "$total_bytes"
    printf 'completed_at\t%s\n' "$(date '+%F %T %Z')"
  } > "$done_marker"
  log "L$tag cleanup done: checkpoints=$deleted_count checkpoint_bytes=$checkpoint_bytes cache_bytes=$cache_bytes total=$total_bytes"
}

log "watcher start pid=$$ layers=${LAYERS[*]}"
while true; do
  for layer in "${LAYERS[@]}"; do
    cleanup_layer "$layer"
  done

  if [[ -f "$ROOT/QUEUE_FINISHED" ]]; then
    log "QUEUE_FINISHED observed; final cleanup pass complete"
    break
  fi
  sleep "$POLL_SECONDS"
done
log "watcher exit"
