#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:?usage: cleanup_tmp_duplicate_selected_checkpoints_20260827.sh TMP_ROOT SHARED_ROOT AUDIT_DIR}
SHARED=${2:?usage: cleanup_tmp_duplicate_selected_checkpoints_20260827.sh TMP_ROOT SHARED_ROOT AUDIT_DIR}
AUDIT_DIR=${3:?usage: cleanup_tmp_duplicate_selected_checkpoints_20260827.sh TMP_ROOT SHARED_ROOT AUDIT_DIR}

ROOT=$(realpath -e "$ROOT")
SHARED=$(realpath -e "$SHARED")

case "$ROOT" in
  /tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812|/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812) ;;
  *) printf 'REFUSED unexpected_tmp_root=%s\n' "$ROOT" >&2; exit 20 ;;
esac
case "$SHARED" in
  /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082|/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065) ;;
  *) printf 'REFUSED unexpected_shared_root=%s\n' "$SHARED" >&2; exit 21 ;;
esac

mkdir -p "$AUDIT_DIR"
MANIFEST="$AUDIT_DIR/manifest.tsv"
SUMMARY="$AUDIT_DIR/summary.txt"
printf 'status\tbytes\tlocal_checkpoint\tshared_selected\tsha256\n' > "$MANIFEST"

deleted=0
deleted_bytes=0
skipped_incomplete=0
refused=0

while IFS= read -r -d '' checkpoint; do
  layer_dir=${checkpoint%%/records/*}

  # Incomplete/current layers are resumable state and must never be cleaned here.
  if [[ ! -s "$layer_dir/train.done" || ! -s "$layer_dir/selected_checkpoint.tsv" || ! -s "$layer_dir/eval_full.done" ]]; then
    skipped_incomplete=$((skipped_incomplete + 1))
    continue
  fi
  if ! find "$layer_dir/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q .; then
    printf 'REFUSED_NO_EVAL\t0\t%s\t\t\n' "$checkpoint" >> "$MANIFEST"
    refused=$((refused + 1))
    continue
  fi

  selected=$(tail -n 1 "$layer_dir/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')
  local_abs=$(realpath -e "$checkpoint")
  selected_abs=$(realpath -e "$selected")

  case "$local_abs" in "$ROOT"/*) ;; *)
    printf 'REFUSED_LOCAL_SCOPE\t0\t%s\t%s\t\n' "$local_abs" "$selected_abs" >> "$MANIFEST"
    refused=$((refused + 1)); continue ;;
  esac
  case "$selected_abs" in "$SHARED"/*) ;; *)
    printf 'REFUSED_SHARED_SCOPE\t0\t%s\t%s\t\n' "$local_abs" "$selected_abs" >> "$MANIFEST"
    refused=$((refused + 1)); continue ;;
  esac
  if [[ $(basename "$local_abs") != $(basename "$selected_abs") ]]; then
    printf 'REFUSED_BASENAME\t0\t%s\t%s\t\n' "$local_abs" "$selected_abs" >> "$MANIFEST"
    refused=$((refused + 1)); continue
  fi

  local_sha=$(sha256sum "$local_abs" | awk '{print $1}')
  shared_sha=$(sha256sum "$selected_abs" | awk '{print $1}')
  if [[ "$local_sha" != "$shared_sha" ]]; then
    printf 'REFUSED_SHA256\t0\t%s\t%s\t%s!=%s\n' "$local_abs" "$selected_abs" "$local_sha" "$shared_sha" >> "$MANIFEST"
    refused=$((refused + 1)); continue
  fi

  bytes=$(stat -c %s "$local_abs")
  rm -f -- "$local_abs"
  printf 'DELETED_VERIFIED_DUPLICATE\t%s\t%s\t%s\t%s\n' "$bytes" "$local_abs" "$selected_abs" "$local_sha" >> "$MANIFEST"
  deleted=$((deleted + 1))
  deleted_bytes=$((deleted_bytes + bytes))
done < <(find "$ROOT" -type f -path '*/checkpoints/epoch-*' ! -name '*.lock' -print0)

{
  printf 'time=%s\n' "$(date '+%F %T %Z')"
  printf 'tmp_root=%s\n' "$ROOT"
  printf 'shared_root=%s\n' "$SHARED"
  printf 'deleted=%s\n' "$deleted"
  printf 'deleted_bytes=%s\n' "$deleted_bytes"
  printf 'skipped_incomplete_resume_checkpoints=%s\n' "$skipped_incomplete"
  printf 'refused=%s\n' "$refused"
} | tee "$SUMMARY"

[[ "$refused" -eq 0 ]]
