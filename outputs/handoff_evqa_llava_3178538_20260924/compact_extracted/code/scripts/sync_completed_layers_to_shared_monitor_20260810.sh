#!/usr/bin/env bash
set -uo pipefail

ROOT=${1:?usage: sync_completed_layers_to_shared_monitor ROOT DEST}
DEST=${2:?usage: sync_completed_layers_to_shared_monitor ROOT DEST}
LOG="$DEST/sync_monitor.log"
MIN_AGE_SECONDS=600
POLL_SECONDS=300

mkdir -p "$DEST"

rewrite_dest_paths() {
  local tree=$1 old=$2 new=$3
  python3 - "$tree" "$old" "$new" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
old = sys.argv[2].encode()
new = sys.argv[3].encode()
for p in root.rglob('*'):
    if not p.is_file():
        continue
    try:
        if p.stat().st_size > 64 * 1024 * 1024:
            continue
        data = p.read_bytes()
    except OSError:
        continue
    if b'\0' not in data[:4096] and old in data:
        p.write_bytes(data.replace(old, new))
PY
}

prune_checkpoint_siblings() {
  local tree=$1 selected=$2 scope=$3
  local tree_abs selected_abs parent item item_abs item_bytes
  local removed=0 bytes=0 remaining
  tree_abs=$(realpath -e "$tree") || return 20
  selected_abs=$(realpath -e "$selected") || return 21
  case "$selected_abs" in "$tree_abs"/*) ;; *) return 22 ;; esac
  parent=$(dirname "$selected_abs")
  case "$parent" in "$tree_abs"/*/checkpoints) ;; *) return 23 ;; esac

  for item in "$parent"/*; do
    [[ -e "$item" ]] || continue
    item_abs=$(realpath -e "$item") || return 24
    case "$item_abs" in "$parent"/*) ;; *) return 25 ;; esac
    [[ "$item_abs" == "$selected_abs" ]] && continue
    item_bytes=$(du -sb "$item_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$item_abs"
    removed=$((removed+1))
    bytes=$((bytes+${item_bytes:-0}))
  done

  [[ -e "$selected_abs" ]] || return 26
  remaining=$(find "$parent" -mindepth 1 -maxdepth 1 -print | wc -l)
  [[ "$remaining" -eq 1 ]] || return 27
  if (( removed > 0 )); then
    printf '%s CHECKPOINT_RETENTION scope=%s removed=%s bytes=%s selected=%s\n' \
      "$(date '+%F %T %Z')" "$scope" "$removed" "$bytes" "$selected_abs" >>"$LOG"
  fi
}

cleanup_verified_destination() {
  local dest_layer=$1 rel=$2 dest_selected
  [[ -f "$dest_layer/SYNC_VERIFIED" && -s "$dest_layer/selected_checkpoint.tsv" && -s "$dest_layer/eval_full.done" ]] || return 30
  find "$dest_layer/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q . || return 31
  dest_selected=$(tail -n 1 "$dest_layer/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')
  [[ -n "$dest_selected" && -e "$dest_selected" ]] || return 32
  prune_checkpoint_siblings "$dest_layer" "$dest_selected" "destination:$rel" || return 33
  if [[ ! -f "$dest_layer/CHECKPOINT_RETENTION_VERIFIED" ]]; then
    printf 'verified_at=%s\nselected=%s\npolicy=selected_only\n' \
      "$(date '+%F %T %Z')" "$dest_selected" >"$dest_layer/CHECKPOINT_RETENTION_VERIFIED"
  fi
}

sync_one() {
  local layer=$1 rel dest_layer partial selected dest_selected selected_abs layer_abs cache cache_abs bytes partial_selected selected_rel
  layer_abs=$(realpath -e "$layer") || return 1
  case "$layer_abs" in "$ROOT"/*) ;; *) return 2 ;; esac
  [[ $(stat -c '%U' "$layer_abs") == ph_teacher3 ]] || return 3
  [[ -f "$layer/train.done" && -s "$layer/selected_checkpoint.tsv" && -f "$layer/eval_full.done" ]] || return 4
  find "$layer/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q . || return 5
  if (( $(date +%s) - $(stat -c %Y "$layer/eval_full.done") < MIN_AGE_SECONDS )); then return 6; fi

  selected=$(tail -n 1 "$layer/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')
  [[ -n "$selected" && -e "$selected" ]] || return 7
  selected_abs=$(realpath -e "$selected") || return 7
  case "$selected_abs" in "$layer_abs"/*) ;; *) return 8 ;; esac

  rel=${layer_abs#"$ROOT"/}
  dest_layer="$DEST/$rel"
  if [[ -f "$dest_layer/SYNC_VERIFIED" ]]; then
    cleanup_verified_destination "$dest_layer" "$rel"
    return $?
  fi
  partial="$DEST/.partial/${rel}"
  rm -rf -- "$partial"
  mkdir -p "$partial"
  rsync -a "$layer_abs/" "$partial/"
  [[ -z $(rsync -naci --delete --omit-dir-times "$layer_abs/" "$partial/") ]] || return 9
  selected_rel=${selected_abs#"$layer_abs"/}
  partial_selected="$partial/$selected_rel"
  [[ -e "$partial_selected" ]] || return 15
  prune_checkpoint_siblings "$partial" "$partial_selected" "partial:$rel" || return 16
  mkdir -p "$(dirname "$dest_layer")"
  [[ ! -e "$dest_layer" ]] || return 10
  mv -- "$partial" "$dest_layer"
  rewrite_dest_paths "$dest_layer" "$layer_abs" "$dest_layer"
  dest_selected=$(tail -n 1 "$dest_layer/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')
  [[ -n "$dest_selected" && -e "$dest_selected" ]] || return 11
  find "$dest_layer/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q . || return 12
  printf 'source=%s\ndestination=%s\nsynced_at=%s\nselected=%s\n' \
    "$layer_abs" "$dest_layer" "$(date '+%F %T %Z')" "$dest_selected" >"$dest_layer/SYNC_VERIFIED"
  cleanup_verified_destination "$dest_layer" "$rel" || return 17

  prune_checkpoint_siblings "$layer_abs" "$selected_abs" "source:$rel" || return 18
  bytes=$(du -sb "$selected_abs" 2>/dev/null | awk '{print $1}')
  rm -rf -- "$selected_abs"
  ln -s "$dest_selected" "$selected_abs"
  cache="$(dirname "$layer_abs")/cache/$(basename "$layer_abs")"
  if [[ -e "$cache" ]]; then
    cache_abs=$(realpath -e "$cache") || return 13
    case "$cache_abs" in "$(dirname "$layer_abs")"/cache/layer_*) rm -rf -- "$cache_abs" ;; *) return 14 ;; esac
  fi
  printf '%s SYNCED rel=%s selected_bytes_released=%s destination=%s\n' \
    "$(date '+%F %T %Z')" "$rel" "${bytes:-0}" "$dest_layer" >>"$LOG"
}

while :; do
  pending=0
  while IFS= read -r -d '' done; do
    layer=$(dirname "$done")
    [[ -f "$layer/train.done" && -s "$layer/selected_checkpoint.tsv" ]] || continue
    find "$layer/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q . || continue
    rel=${layer#"$ROOT"/}
    if [[ -f "$DEST/$rel/SYNC_VERIFIED" ]]; then
      cleanup_verified_destination "$DEST/$rel" "$rel" || \
        printf '%s RETENTION_WARNING rel=%s destination=%s\n' "$(date '+%F %T %Z')" "$rel" "$DEST/$rel" >>"$LOG"
      continue
    fi
    pending=$((pending+1))
    sync_one "$layer" || true
  done < <(find "$ROOT" -type f -name eval_full.done -print0 2>/dev/null)

  if [[ -f "$ROOT/QUEUE_DONE" && "$pending" -eq 0 ]]; then
    rsync -a --exclude='*/layer_[0-9][0-9]/***' --exclude='*/cache/***' "$ROOT/" "$DEST/root_metadata/" || true
    printf '%s QUEUE_SYNC_COMPLETE root=%s\n' "$(date '+%F %T %Z')" "$ROOT" >>"$LOG"
    exit 0
  fi
  sleep "$POLL_SECONDS"
done
