#!/usr/bin/env bash
set -uo pipefail

PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUN_ROOT=/tmp/ph_teacher3/mabscos_top3_completion_job3126082_20260801
OUT_ROOT=$RUN_ROOT/mmke-visual/minigpt-4-vicuna-7b
RUNNER=scripts/run_mmke_minigpt_llava_lowmem_sweep.py
L9_RETRY=scripts/retry_mmke_visual_minigpt_l9_after_queue_job3126082.sh
CONFIG=configs/vead/minigpt-4-vicuna-7b.yaml
DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data
TRAIN_JSON=$DATA/vqa_mmke_visual_train_evqa_compat.json
EVAL_JSON=$DATA/vqa_mmke_visual_eval_evqa_compat.json
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
STATUS=$RUN_ROOT/l10_l11_repair_eval.status.log
CSV=$RUN_ROOT/l10_l11_repair_eval_status.csv
LOCK=$RUN_ROOT/l10_l11_repair_eval.lock
GPU_ID=0
STALL_SECONDS=7200
POLL_SECONDS=60

mkdir -p "$RUN_ROOT/logs"
cd "$PROJ" || exit 1
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

log_status() { printf '%s\n' "$*" | tee -a "$STATUS"; }

selected_path() {
  [[ -s "$1" ]] || return 1
  tail -n 1 "$1" | awk -F '\t' '{print $NF}' | tr -d '\r'
}

selected_exists() {
  local p
  p=$(selected_path "$1") || return 1
  [[ -n "$p" && -e "$p" ]]
}

complete_exists() {
  local d=$1 result
  [[ -f "$d/train.done" && -s "$d/selected_checkpoint.tsv" && -f "$d/eval_full.done" ]] || return 1
  selected_exists "$d/selected_checkpoint.tsv" || return 1
  result=$(find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null)
  [[ -n "$result" ]]
}

run_watched() {
  local label=$1 log=$2
  shift 2
  local pid rc last_progress now old_sig='' sig raw old_raw heartbeat
  : >"$log"
  setsid env CUDA_VISIBLE_DEVICES="$GPU_ID" PYTORCH_CUDA_ALLOC_CONF="$PYTORCH_CUDA_ALLOC_CONF" "$@" >>"$log" 2>&1 &
  pid=$!
  last_progress=$(date +%s)
  heartbeat=$last_progress
  old_raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
  log_status "PROCESS_START label=$label pid=$pid log=$log time=$(date '+%F %T %Z')"
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL_SECONDS"
    now=$(date +%s)
    raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
    sig=$(tail -c 8388608 "$log" 2>/dev/null | tr '\r' '\n' | grep -Ei 'Evaluat|eval|[0-9]+/[0-9]+|it/s' | tail -1 || true)
    if [[ -n "$sig" && "$sig" != "$old_sig" ]]; then
      old_sig=$sig
      last_progress=$now
      log_status "WATCH_PROGRESS label=$label sig=${sig:0:320} time=$(date '+%F %T')"
    elif [[ -z "$old_sig" && "$raw" != "$old_raw" ]]; then
      last_progress=$now
    fi
    old_raw=$raw
    if (( now - heartbeat >= 600 )); then
      log_status "WATCH_HEARTBEAT label=$label idle_seconds=$((now-last_progress)) gpu=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -d '\n')"
      heartbeat=$now
    fi
    if (( now - last_progress >= STALL_SECONDS )); then
      log_status "WATCHDOG_STALL label=$label unchanged_seconds=$((now-last_progress))"
      kill -TERM -- "-$pid" 2>/dev/null || true
      for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      kill -0 "$pid" 2>/dev/null && kill -KILL -- "-$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
  done
  wait "$pid"
  rc=$?
  log_status "PROCESS_END label=$label pid=$pid rc=$rc time=$(date '+%F %T %Z')"
  return "$rc"
}

cleanup_layer() {
  local layer=$1 d selected selected_abs d_abs parent item item_abs item_bytes bytes=0 removed=0 cache
  d=$(printf "$OUT_ROOT/layer_%02d" "$layer")
  complete_exists "$d" || return 1
  selected=$(selected_path "$d/selected_checkpoint.tsv") || return 1
  selected_abs=$(realpath -e "$selected") || return 1
  d_abs=$(realpath -e "$d") || return 1
  case "$selected_abs" in "$d_abs"/*) ;; *) log_status "CLEANUP_REFUSED L$layer selected_outside_layer"; return 2 ;; esac
  parent=$(dirname "$selected_abs")
  case "$parent" in "$d_abs"/*/checkpoints) ;; *) log_status "CLEANUP_REFUSED L$layer unexpected_parent=$parent"; return 2 ;; esac
  for item in "$parent"/*; do
    [[ -e "$item" ]] || continue
    item_abs=$(realpath -e "$item") || continue
    [[ "$item_abs" == "$selected_abs" ]] && continue
    item_bytes=$(du -sb "$item_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$item_abs"
    bytes=$((bytes+${item_bytes:-0}))
    removed=$((removed+1))
  done
  cache=$(printf "$OUT_ROOT/cache/layer_%02d" "$layer")
  if [[ -e "$cache" ]]; then
    item_bytes=$(du -sb "$cache" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$cache"
    bytes=$((bytes+${item_bytes:-0}))
    removed=$((removed+1))
  fi
  log_status "POST_EVAL_CLEANUP layer=L$layer selected=$selected_abs removed=$removed bytes=$bytes"
}

exec 9>"$LOCK"
if ! flock -n 9; then log_status "ALREADY_RUNNING lock=$LOCK"; exit 3; fi

log_status "CHAIN_START job=${SLURM_JOB_ID:-unset} host=$(hostname) plan=L10_eval,L11_eval,L9_retry time=$(date '+%F %T %Z')"
printf '%s\n' 'layer,stage,rc,start_time,end_time,log,note' >"$CSV"

# Require an actually idle allocated GPU for five consecutive checks.
streak=0
while (( streak < 5 )); do
  pids=$(nvidia-smi -i "$GPU_ID" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null | sed '/^[[:space:]]*$/d' || true)
  used=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d '[:space:]')
  used=${used:-999999}
  if [[ -z "$pids" && "$used" =~ ^[0-9]+$ ]] && (( used < 2048 )); then streak=$((streak+1)); else streak=0; fi
  log_status "WAIT_GPU_EXCLUSIVE used_mib=$used compute_pids=${pids//$'\n'/,} streak=$streak/5"
  (( streak < 5 )) && sleep 60
done

common=(
  "$PY" "$RUNNER" --out-root "$OUT_ROOT" --epochs 50 --batch-size 2
  --model-name minigpt-4-vicuna-7b --device cuda:0
  --train-data "$TRAIN_JSON" --train-img-root "$IMG_ROOT"
  --eval-data "$EVAL_JSON" --eval-img-root "$IMG_ROOT"
  --config-path "$CONFIG" --seed 20260601 --ema-alpha 0.1
  --data-buffer-size 1 --synchronous-data-loading --activation-checkpointing
  --keep-top-ckpts 1 --keep-last-ckpts 0 --skip-train
)

for layer in 10 11; do
  d=$(printf "$OUT_ROOT/layer_%02d" "$layer")
  if complete_exists "$d"; then
    log_status "EVAL_SKIP layer=L$layer reason=already_complete"
    cleanup_layer "$layer" || true
    continue
  fi
  if ! selected_exists "$d/selected_checkpoint.tsv"; then
    log_status "CHAIN_BLOCKED layer=L$layer reason=no_valid_selected_checkpoint"
    exit 20
  fi
  log=$RUN_ROOT/logs/mmke-visual_minigpt-4-vicuna-7b_L${layer}_recovered_eval_$(date +%Y%m%d_%H%M%S).log
  start=$(date '+%F %T')
  run_watched "L${layer}_recovered_eval" "$log" "${common[@]}" --layers "$layer"
  rc=$?
  printf '%s\n' "$layer,eval,$rc,$start,$(date '+%F %T'),$log,recovered_selection" >>"$CSV"
  if [[ "$rc" -ne 0 ]] || ! complete_exists "$d"; then
    log_status "CHAIN_BLOCKED layer=L$layer reason=eval_failed_or_incomplete rc=$rc"
    exit "${rc:-1}"
  fi
  cleanup_layer "$layer" || { log_status "CLEANUP_WARNING layer=L$layer"; exit 21; }
  log_status "RECOVERED_LAYER_COMPLETE layer=L$layer selected=$(selected_path "$d/selected_checkpoint.tsv")"
done

touch "$RUN_ROOT/L10_L11_RECOVERED_EVAL_DONE"
log_status "L10_L11_EVAL_COMPLETE handoff=L9_retry time=$(date '+%F %T %Z')"
exec bash "$L9_RETRY"
