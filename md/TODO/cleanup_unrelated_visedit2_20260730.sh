#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
AUDIT=/tmp/ph_teacher3/_cleanup_audit_unrelated_visedit2_20260730
CANDIDATES="$AUDIT/candidate_dirs.tsv"
PREFLIGHT="$AUDIT/preflight.tsv"
VIOLATIONS="$AUDIT/violations.tsv"
REFS_RAW="$AUDIT/process_refs_raw.tsv"
ACTIVE_REFS="$AUDIT/active_candidate_refs.tsv"

mkdir -p "$AUDIT"
test -s "$CANDIDATES"
printf 'category\treason\tbytes\tentries\tfiles\tforeign_owner\tcanonical_path\n' > "$PREFLIGHT"
printf 'type\tpath\tdetail\n' > "$VIOLATIONS"

mapfile -t candidate_paths < <(tail -n +2 "$CANDIDATES" | cut -f4-)

protected=(
  "$ROOT/VisEdit-main/data"
  "$ROOT/VisEdit-main/models"
  "$ROOT/datasets"
  "$ROOT/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644"
  "$ROOT/server_results/visedit_keytoken_mmke_7models_job3044841_20260704_192247"
  "$ROOT/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900"
  "$ROOT/server_results/perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701"
  "$ROOT/server_results/ours_direct_7models_3datasets_g08_gpu0_20260626_131624"
  "$ROOT/server_results/ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304"
  "$ROOT/server_results/cma_direct_v13_full_g09_gpu0_20260703_134818"
)

while IFS=$'\t' read -r category reason bytes path; do
  [[ "$category" == category ]] && continue
  if [[ ! -e "$path" ]]; then
    printf 'missing\t%s\tnot found before deletion\n' "$path" >> "$VIOLATIONS"
    continue
  fi
  if [[ -L "$path" ]]; then
    printf 'symlink\t%s\tcandidate root is a symlink\n' "$path" >> "$VIOLATIONS"
    continue
  fi
  canonical=$(readlink -f -- "$path")
  if [[ "$canonical" != "$ROOT/"* || "$canonical" == "$ROOT" ]]; then
    printf 'boundary\t%s\tresolved to %s\n' "$path" "$canonical" >> "$VIOLATIONS"
  fi
  for keep in "${protected[@]}"; do
    if [[ "$keep" == "$canonical" || "$keep" == "$canonical/"* ]]; then
      printf 'protected_overlap\t%s\twould remove %s\n' "$canonical" "$keep" >> "$VIOLATIONS"
    fi
  done
  read -r entries files foreign < <(
    find "$canonical" -xdev -printf '%u\t%y\n' |
      awk -F '\t' -v owner=ph_teacher3 '
        { entries++; if ($2 == "f") files++; if ($1 != owner) foreign++ }
        END { printf "%d %d %d\n", entries+0, files+0, foreign+0 }'
  )
  if (( foreign > 0 )); then
    printf 'foreign_owner\t%s\t%d entries not owned by ph_teacher3\n' "$canonical" "$foreign" >> "$VIOLATIONS"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$category" "$reason" "$bytes" "$entries" "$files" "$foreign" "$canonical" >> "$PREFLIGHT"
done < "$CANDIDATES"

for ((i=0; i<${#candidate_paths[@]}; i++)); do
  a=${candidate_paths[$i]}
  for ((j=i+1; j<${#candidate_paths[@]}; j++)); do
    b=${candidate_paths[$j]}
    if [[ "$a" == "$b" || "$a" == "$b/"* || "$b" == "$a/"* ]]; then
      printf 'candidate_overlap\t%s\t%s\n' "$a" "$b" >> "$VIOLATIONS"
    fi
  done
done

printf 'pid\tkind\ttarget\n' > "$REFS_RAW"
while read -r pid; do
  [[ -d "/proc/$pid" ]] || continue
  cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)
  [[ -n "$cwd" ]] && printf '%s\tcwd\t%s\n' "$pid" "$cwd" >> "$REFS_RAW"
  cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
  [[ -n "$cmd" ]] && printf '%s\tcmd\t%s\n' "$pid" "$cmd" >> "$REFS_RAW"
  for fd in "/proc/$pid"/fd/*; do
    [[ -e "$fd" || -L "$fd" ]] || continue
    target=$(readlink -f "$fd" 2>/dev/null || true)
    [[ -n "$target" ]] && printf '%s\tfd\t%s\n' "$pid" "$target" >> "$REFS_RAW"
  done
done < <(ps -u ph_teacher3 -o pid=)

printf 'category\treason\tpath\tpid\tkind\ttarget\n' > "$ACTIVE_REFS"
awk -F '\t' '
  NR==FNR && FNR>1 { cat[++n]=$1; reason[n]=$2; path[n]=$4; next }
  FNR==1 { next }
  {
    pid=$1; kind=$2; target=$3
    for (i=1; i<=n; i++) {
      if (index(target, path[i]) > 0) {
        print cat[i] "\t" reason[i] "\t" path[i] "\t" pid "\t" kind "\t" target
      }
    }
  }
' "$CANDIDATES" "$REFS_RAW" >> "$ACTIVE_REFS"

if (( $(wc -l < "$ACTIVE_REFS") > 1 )); then
  printf 'active_reference\t%s\tsee %s\n' "$ROOT" "$ACTIVE_REFS" >> "$VIOLATIONS"
fi

violation_count=$(( $(wc -l < "$VIOLATIONS") - 1 ))
if (( violation_count > 0 )); then
  echo "PREFLIGHT_FAILED violations=$violation_count"
  cat "$VIOLATIONS"
  exit 2
fi

awk -F '\t' 'NR>1 {dirs++; bytes+=$3; entries+=$4; files+=$5; foreign+=$6} END {
  printf "PREFLIGHT_OK dirs=%d bytes=%.0f GiB=%.3f entries=%.0f files=%.0f foreign=%d\n", dirs, bytes, bytes/1073741824, entries, files, foreign
}' "$PREFLIGHT"
