#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
AUDIT=/tmp/ph_teacher3/_cleanup_audit_unrelated_visedit2_20260730
CANDIDATES="$AUDIT/candidate_dirs.tsv"
PREFLIGHT="$AUDIT/preflight.tsv"
VIOLATIONS="$AUDIT/violations.tsv"
DELETE_LOG="$AUDIT/deletion.tsv"

[[ $(wc -l < "$CANDIDATES") -eq 87 ]]
[[ $(wc -l < "$PREFLIGHT") -eq 87 ]]
[[ $(wc -l < "$VIOLATIONS") -eq 1 ]]
[[ $(wc -l < "$AUDIT/active_candidate_refs.tsv") -eq 1 ]]

sha256sum "$CANDIDATES" "$PREFLIGHT" > "$AUDIT/frozen_manifest.sha256"
printf 'category\treason\tbytes\tpath\tstatus\tdeleted_at\n' > "$DELETE_LOG"

while IFS=$'\t' read -r category reason bytes path; do
  [[ "$category" == category ]] && continue
  canonical=$(readlink -f -- "$path")
  [[ -n "$canonical" ]]
  [[ ! -L "$path" ]]
  [[ "$canonical" == "$ROOT/"* ]]
  [[ "$canonical" != "$ROOT" ]]
  awk -F '\t' -v p="$canonical" 'NR>1 && $7==p {found=1} END {exit !found}' "$PREFLIGHT"
  rm -rf -- "$canonical"
  [[ ! -e "$canonical" ]]
  printf '%s\t%s\t%s\t%s\tdeleted\t%s\n' \
    "$category" "$reason" "$bytes" "$canonical" "$(date '+%F %T %z')" >> "$DELETE_LOG"
done < "$CANDIDATES"

mkdir -p \
  "$ROOT/VisEdit-main/records" \
  "$ROOT/records" \
  "$ROOT/DualEdit-main/data" \
  "$ROOT/DualEdit-main/server_results"

for dir in \
  "$ROOT/VisEdit-main/records" \
  "$ROOT/records" \
  "$ROOT/DualEdit-main/data" \
  "$ROOT/DualEdit-main/server_results"; do
  [[ -d "$dir" ]]
  [[ -z $(find "$dir" -mindepth 1 -print -quit) ]]
done

awk -F '\t' 'NR>1 {dirs++; bytes+=$3} END {
  printf "DELETE_OK dirs=%d bytes=%.0f GiB=%.3f TiB=%.3f\n", dirs, bytes, bytes/1073741824, bytes/1099511627776
}' "$DELETE_LOG"
