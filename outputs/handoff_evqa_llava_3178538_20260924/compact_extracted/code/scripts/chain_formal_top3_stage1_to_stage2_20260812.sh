#!/usr/bin/env bash
set -uo pipefail

ROLE=${1:?usage: chain_formal_top3_stage1_to_stage2_20260812.sh job3126082|job3150065}
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
STAGE2=$PROJ/scripts/launch_formal_top3_stage2_20260812.sh
CHAIN_ROOT=/tmp/ph_teacher3/formal_top3_stage_chains_20260812
mkdir -p "$CHAIN_ROOT"
LOG=$CHAIN_ROOT/${ROLE}.status.log

log_status() {
  printf '%s\n' "$*" | tee -a "$LOG"
}

rewrite_paths() {
  local tree=$1 old=$2 new=$3
  python3 - "$tree" "$old" "$new" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
old = sys.argv[2].encode()
new = sys.argv[3].encode()
for p in root.rglob("*"):
    if not p.is_file():
        continue
    try:
        if p.stat().st_size > 64 * 1024 * 1024:
            continue
        data = p.read_bytes()
    except OSError:
        continue
    if b"\0" not in data[:4096] and old in data:
        p.write_bytes(data.replace(old, new))
PY
}

wait_first_stage() {
  local root=$1
  while [[ ! -e "$root/QUEUE_DONE" && ! -e "$root/QUEUE_FINISHED_WITH_FAILURES" ]]; do
    log_status "WAIT_FIRST_STAGE role=$ROLE root=$root time=$(date '+%F %T %Z')"
    sleep 300
  done
  if [[ -e "$root/QUEUE_DONE" ]]; then
    log_status "FIRST_STAGE_DONE role=$ROLE root=$root time=$(date '+%F %T %Z')"
  else
    log_status "FIRST_STAGE_FINISHED_WITH_FAILURES role=$ROLE root=$root time=$(date '+%F %T %Z')"
  fi
}

case "$ROLE" in
  job3126082)
    [[ ${SLURM_JOB_ID:-unset} == 3126082 ]] || { log_status "WRONG_JOB expected=3126082 actual=${SLURM_JOB_ID:-unset}"; exit 2; }
    FIRST_ROOT=/tmp/ph_teacher3/formal_top3_highmem_llava_job3126082_20260810
    wait_first_stage "$FIRST_ROOT"
    ;;
  job3150065)
    [[ ${SLURM_JOB_ID:-unset} == 3150065 ]] || { log_status "WRONG_JOB expected=3150065 actual=${SLURM_JOB_ID:-unset}"; exit 2; }
    FIRST_ROOT=/tmp/ph_teacher3/formal_top3_minigpt_entity_job3117562_20260811
    FIRST_LAUNCHER=$PROJ/scripts/launch_top3_minigpt_entity_job3117562_20260811.sh
    SRC=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_live_20260811/job3117562_minigpt_entity/mmke-entity/minigpt-4-vicuna-7b/layer_16
    DST=$FIRST_ROOT/mmke-entity/minigpt-4-vicuna-7b/layer_16
    if [[ ! -e "$DST" ]]; then
      mkdir -p "$(dirname "$DST")"
      rsync -a "$SRC/" "$DST/"
      rewrite_paths "$DST" "$SRC" "$DST"
      log_status "FIRST_STAGE_SEEDED layer=16 source=$SRC destination=$DST time=$(date '+%F %T %Z')"
    fi
    log_status "FIRST_STAGE_LAUNCH role=$ROLE launcher=$FIRST_LAUNCHER time=$(date '+%F %T %Z')"
    bash "$FIRST_LAUNCHER"
    first_rc=$?
    log_status "FIRST_STAGE_LAUNCH_END role=$ROLE rc=$first_rc time=$(date '+%F %T %Z')"
    wait_first_stage "$FIRST_ROOT"
    ;;
  *)
    log_status "UNKNOWN_ROLE role=$ROLE"
    exit 2
    ;;
esac

log_status "SECOND_STAGE_LAUNCH role=$ROLE script=$STAGE2 time=$(date '+%F %T %Z')"
exec bash "$STAGE2" "$ROLE"
