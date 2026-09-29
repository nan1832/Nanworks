#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
AUDIT=/tmp/ph_teacher3/_cleanup_audit_unrelated_visedit2_20260730
CANDIDATES="$AUDIT/candidate_dirs.tsv"
REPORT="$AUDIT/post_cleanup_verification.txt"

recreated=(
  "$ROOT/VisEdit-main/records"
  "$ROOT/records"
  "$ROOT/DualEdit-main/data"
  "$ROOT/DualEdit-main/server_results"
)

is_recreated() {
  local p=$1 x
  for x in "${recreated[@]}"; do
    [[ "$p" == "$x" ]] && return 0
  done
  return 1
}

missing=0
empty_recreated=0
errors=0
while IFS=$'\t' read -r category reason bytes path; do
  [[ "$category" == category ]] && continue
  if is_recreated "$path"; then
    if [[ -d "$path" && -z $(find "$path" -mindepth 1 -print -quit) ]]; then
      ((empty_recreated+=1))
    else
      echo "ERROR recreated_not_empty_or_missing $path"
      ((errors+=1))
    fi
  elif [[ ! -e "$path" ]]; then
    ((missing+=1))
  else
    echo "ERROR candidate_still_exists $path"
    ((errors+=1))
  fi
done < "$CANDIDATES"

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

protected_ok=0
for path in "${protected[@]}"; do
  if [[ -e "$path" ]]; then
    ((protected_ok+=1))
  else
    echo "ERROR protected_missing $path"
    ((errors+=1))
  fi
done

formal_root="$ROOT/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644"
read -r selected eval_done train_done < <(
  find "$formal_root" -type d -name cache -prune -o -type f \
    \( -name selected_checkpoint.tsv -o -name eval_full.done -o -name train.done \) \
    -printf '%f\n' |
    awk '
      $0=="selected_checkpoint.tsv" {selected++}
      $0=="eval_full.done" {eval_done++}
      $0=="train.done" {train_done++}
      END {printf "%d %d %d\n", selected+0, eval_done+0, train_done+0}'
)

{
  printf 'verification_time=%s\n' "$(date '+%F %T %z')"
  printf 'deleted_absent=%d\n' "$missing"
  printf 'recreated_empty=%d\n' "$empty_recreated"
  printf 'protected_ok=%d\n' "$protected_ok"
  printf 'errors=%d\n' "$errors"
  printf 'mmke_visual_formal_selected=%d\n' "$selected"
  printf 'mmke_visual_formal_eval_done=%d\n' "$eval_done"
  printf 'mmke_visual_formal_train_done=%d\n' "$train_done"
} | tee "$REPORT"

(( errors == 0 ))
[[ "$missing" -eq 82 ]]
[[ "$empty_recreated" -eq 4 ]]
