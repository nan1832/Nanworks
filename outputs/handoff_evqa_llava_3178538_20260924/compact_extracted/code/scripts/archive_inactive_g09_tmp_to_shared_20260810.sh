#!/usr/bin/env bash
set -euo pipefail

ARCHIVE_BASE=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tmp_archives_20260810/g09
AUDIT="$ARCHIVE_BASE/archive_audit.tsv"

ROOTS=(
  /tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730
  /tmp/ph_teacher3/mabscos_top3_completion_job3126082_20260801
  /tmp/ph_teacher3/mmke_visual_minigpt_llava_job3044841_20260728
  /tmp/ph_teacher3/paligemma_followup_job3044208_20260715_112056
  /tmp/ph_teacher3/mmke_visual_smol_qwen_job3044208_20260719_093500
  /tmp/ph_teacher3/mmke_entity_minigpt_llava_job3044841_20260726
  /tmp/ph_teacher3/paligemma_priority_reruns_job3044208_20260718_160000
  /tmp/ph_teacher3/mmke_entity_job3044841_20260715_121700
)

mkdir -p "$ARCHIVE_BASE"
if [[ ! -s "$AUDIT" ]]; then
  printf 'time\tsource\tdestination\tsource_bytes\tarchived_bytes\texcluded_cache_bytes\tcompleted_layers\tstatus\n' >"$AUDIT"
fi

rewrite_paths() {
  local dest=$1 old=$2 new=$3
  python3 - "$dest" "$old" "$new" <<'PY'
import os
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
    if b'\0' in data[:4096] or old not in data:
        continue
    p.write_bytes(data.replace(old, new))
PY
}

validate_completed_layers() {
  local dest=$1 d selected result completed=0
  while IFS= read -r -d '' d; do
    [[ -f "$d/train.done" && -s "$d/selected_checkpoint.tsv" && -f "$d/eval_full.done" ]] || continue
    result=$(find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null)
    [[ -n "$result" ]] || { echo "missing results.json in $d" >&2; return 1; }
    selected=$(tail -n 1 "$d/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')
    [[ -n "$selected" && -e "$selected" ]] || { echo "missing selected checkpoint for $d: $selected" >&2; return 1; }
    completed=$((completed+1))
  done < <(find "$dest" -type d -name 'layer_[0-9][0-9]' -print0)
  printf '%s' "$completed"
}

for source in "${ROOTS[@]}"; do
  [[ -e "$source" ]] || continue
  source_abs=$(realpath -e "$source")
  case "$source_abs" in /tmp/ph_teacher3/*) ;; *) echo "refuse out-of-scope source: $source_abs" >&2; exit 20 ;; esac
  [[ $(stat -c '%U' "$source_abs") == ph_teacher3 ]] || { echo "refuse non-owner source: $source_abs" >&2; exit 21; }
  if ps -eo args | grep -F "$source_abs" | grep -v grep >/dev/null; then
    echo "refuse active source: $source_abs" >&2
    exit 22
  fi

  name=$(basename "$source_abs")
  dest="$ARCHIVE_BASE/$name"
  partial="$ARCHIVE_BASE/.${name}.partial"
  [[ ! -e "$dest" ]] || { echo "destination exists: $dest" >&2; exit 23; }

  source_bytes=$(du -sb "$source_abs" | awk '{print $1}')
  noncache_bytes=$(du -sb --exclude=cache "$source_abs" | awk '{print $1}')
  cache_bytes=$((source_bytes-noncache_bytes))
  mkdir -p "$partial"
  rsync -a --exclude='cache/' "$source_abs/" "$partial/"
  # LeoFS does not preserve a few directory mtimes exactly, so validate file
  # content checksums and ignore directory timestamp-only differences.
  if [[ -n $(rsync -naci --delete --omit-dir-times --exclude='cache/' "$source_abs/" "$partial/") ]]; then
    echo "rsync verification mismatch: $source_abs" >&2
    exit 24
  fi
  mv -- "$partial" "$dest"
  rewrite_paths "$dest" "$source_abs" "$dest"
  status=MOVED_VERIFIED
  if [[ "$name" == mmke_visual_minigpt_llava_job3044841_20260728 || \
        "$name" == paligemma_followup_job3044208_20260715_112056 || \
        "$name" == mmke_visual_smol_qwen_job3044208_20260719_093500 || \
        "$name" == mmke_entity_minigpt_llava_job3044841_20260726 || \
        "$name" == paligemma_priority_reruns_job3044208_20260718_160000 || \
        "$name" == mmke_entity_job3044841_20260715_121700 ]]; then
    completed=0
    status=MOVED_METADATA_ONLY
  else
    completed=$(validate_completed_layers "$dest")
  fi
  archived_bytes=$(du -sb "$dest" | awk '{print $1}')
  {
    printf 'source=%s\n' "$source_abs"
    printf 'destination=%s\n' "$dest"
    printf 'archived_at=%s\n' "$(date '+%F %T %Z')"
    printf 'excluded_reproducible_cache_bytes=%s\n' "$cache_bytes"
    printf 'completed_layers_verified=%s\n' "$completed"
  } >"$dest/ARCHIVE_MANIFEST.txt"

  rm -rf -- "$source_abs"
  [[ ! -e "$source_abs" ]] || { echo "source removal failed: $source_abs" >&2; exit 25; }
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date '+%F %T %Z')" "$source_abs" "$dest" "$source_bytes" "$archived_bytes" "$cache_bytes" "$completed" "$status" >>"$AUDIT"
done

echo "ARCHIVE_COMPLETE base=$ARCHIVE_BASE"
cat "$AUDIT"
