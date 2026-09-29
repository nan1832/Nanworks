#!/usr/bin/env bash
set -uo pipefail

PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUN_ROOT=/tmp/ph_teacher3/mabscos_top3_completion_job3126082_20260801
OUT_ROOT=$RUN_ROOT/mmke-visual/minigpt-4-vicuna-7b
MAIN_LOCK=$RUN_ROOT/launcher.lock
RETRY_LOCK=$RUN_ROOT/l9_retry.lock
STATUS=$RUN_ROOT/l9_retry.status.log
CSV=$RUN_ROOT/l9_retry_status.csv
LOWMEM_RUNNER=scripts/run_mmke_minigpt_llava_lowmem_sweep.py
SHARED_RUNNER=scripts/run_mmke_llava_shared_gpu_sweep.py
CONFIG=configs/vead/minigpt-4-vicuna-7b.yaml
VIS_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data
TRAIN_JSON=$VIS_DATA/vqa_mmke_visual_train_evqa_compat.json
EVAL_JSON=$VIS_DATA/vqa_mmke_visual_eval_evqa_compat.json
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
GPU_ID=0
STALL_SECONDS=7200
POLL_SECONDS=60
EMPTY_STREAK_REQUIRED=5

mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/failed_attempts"
cd "$PROJ" || exit 1
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

log_status() {
  printf '%s\n' "$*" | tee -a "$STATUS"
}

selected_path() {
  local selected=$1
  [[ -s "$selected" ]] || return 1
  tail -n 1 "$selected" | awk -F '\t' '{print $NF}' | tr -d '\r'
}

selected_exists() {
  local selected=$1 p
  p=$(selected_path "$selected") || return 1
  [[ -n "$p" && -e "$p" ]]
}

complete_exists() {
  local d=$1 result
  [[ -f "$d/train.done" && -s "$d/selected_checkpoint.tsv" && -f "$d/eval_full.done" ]] || return 1
  selected_exists "$d/selected_checkpoint.tsv" || return 1
  result=$(find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null)
  [[ -n "$result" ]]
}

progress_signature() {
  "$PY" - "$1" <<'PY'
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
if not p.exists():
    raise SystemExit(0)
with p.open("rb") as handle:
    try:
        handle.seek(-8 * 1024 * 1024, 2)
    except OSError:
        handle.seek(0)
    text = handle.read().decode("utf-8", errors="ignore").replace("\r", "\n")
last = ""
for line in text.splitlines():
    if re.search(r"\b\d+\s*/\s*\d+\b", line) and re.search(
        r"Epoch|Pre-process|Evaluat|eval|train|Waiting data|it/s|step", line, re.I
    ):
        last = line[-600:]
if last:
    print(last)
PY
}

run_watched() {
  local label=$1 log=$2
  shift 2
  local pid rc now last_progress last_sig sig last_raw raw heartbeat
  : >"$log"
  log_status "WATCH_START label=$label idle_limit=$STALL_SECONDS log=$log time=$(date '+%F %T %Z')"
  setsid env CUDA_VISIBLE_DEVICES="$GPU_ID" PYTORCH_CUDA_ALLOC_CONF="$PYTORCH_CUDA_ALLOC_CONF" "$@" >>"$log" 2>&1 &
  pid=$!
  last_progress=$(date +%s)
  last_sig=''
  last_raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
  heartbeat=$last_progress
  log_status "PROCESS_START label=$label pid=$pid pgid=$pid"
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL_SECONDS"
    now=$(date +%s)
    sig=$(progress_signature "$log" 2>/dev/null || true)
    raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
    if [[ -n "$sig" && "$sig" != "$last_sig" ]]; then
      last_sig=$sig
      last_progress=$now
      log_status "WATCH_PROGRESS label=$label sig=${sig:0:320} time=$(date '+%F %T')"
    elif [[ -z "$last_sig" && "$raw" != "$last_raw" ]]; then
      last_progress=$now
    fi
    last_raw=$raw
    if (( now - heartbeat >= 600 )); then
      log_status "WATCH_HEARTBEAT label=$label idle_seconds=$((now-last_progress)) gpu=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -d '\n') time=$(date '+%F %T')"
      heartbeat=$now
    fi
    if (( now - last_progress >= STALL_SECONDS )); then
      log_status "WATCHDOG_STALL label=$label unchanged_seconds=$((now-last_progress)) time=$(date '+%F %T %Z')"
      kill -TERM -- "-$pid" 2>/dev/null || true
      for _ in $(seq 1 60); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
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

archive_incomplete_l9() {
  local layer=$OUT_ROOT/layer_09 cache=$OUT_ROOT/cache/layer_09 tag bytes
  tag=$(date +%Y%m%d_%H%M%S)
  if [[ -e "$layer" ]] && ! complete_exists "$layer"; then
    mv -- "$layer" "$RUN_ROOT/failed_attempts/layer_09_$tag"
    log_status "ARCHIVE_INCOMPLETE path=$layer dest=$RUN_ROOT/failed_attempts/layer_09_$tag"
  fi
  if [[ -e "$cache" ]]; then
    bytes=$(du -sb "$cache" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$cache"
    log_status "REMOVE_REPRODUCIBLE_FAILED_CACHE path=$cache bytes=${bytes:-0}"
  fi
}

cleanup_after_success() {
  local d=$OUT_ROOT/layer_09 selected selected_abs d_abs parent item item_abs bytes=0 item_bytes removed=0 cache
  complete_exists "$d" || return 1
  selected=$(selected_path "$d/selected_checkpoint.tsv") || return 1
  selected_abs=$(realpath -e "$selected") || return 1
  d_abs=$(realpath -e "$d") || return 1
  case "$selected_abs" in "$d_abs"/*) ;; *) return 2 ;; esac
  parent=$(dirname "$selected_abs")
  case "$parent" in "$d_abs"/*/checkpoints) ;; *) return 2 ;; esac
  for item in "$parent"/*; do
    [[ -e "$item" ]] || continue
    item_abs=$(realpath -e "$item") || continue
    [[ "$item_abs" == "$selected_abs" ]] && continue
    item_bytes=$(du -sb "$item_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$item_abs"
    bytes=$((bytes+${item_bytes:-0}))
    removed=$((removed+1))
  done
  cache=$OUT_ROOT/cache/layer_09
  if [[ -e "$cache" ]]; then
    item_bytes=$(du -sb "$cache" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$cache"
    bytes=$((bytes+${item_bytes:-0}))
    removed=$((removed+1))
  fi
  log_status "POST_EVAL_CLEANUP selected=$selected_abs removed=$removed bytes=$bytes"
}

common_args=(
  --out-root "$OUT_ROOT" --layers 9 --epochs 50 --batch-size 2
  --model-name minigpt-4-vicuna-7b --device cuda:0
  --train-data "$TRAIN_JSON" --train-img-root "$IMG_ROOT"
  --eval-data "$EVAL_JSON" --eval-img-root "$IMG_ROOT"
  --config-path "$CONFIG" --seed 20260601 --ema-alpha 0.1
  --data-buffer-size 1 --keep-top-ckpts 1 --keep-last-ckpts 0
  --synchronous-data-loading --activation-checkpointing
)

run_train_attempt() {
  local mode=$1 log=$2 rc
  if [[ "$mode" == two_model_gpu ]]; then
    run_watched "L9_train_two_model_gpu" "$log" "$PY" "$LOWMEM_RUNNER" "${common_args[@]}" --skip-eval --overwrite-train
  elif [[ "$mode" == one_model_gpu ]]; then
    run_watched "L9_train_one_model_gpu" "$log" "$PY" "$SHARED_RUNNER" "${common_args[@]}" --data-proc-device cuda:0 --share-data-proc-vllm --skip-eval --overwrite-train
  else
    run_watched "L9_train_cpu_data_proc" "$log" "$PY" "$SHARED_RUNNER" "${common_args[@]}" --data-proc-device cpu --skip-eval --overwrite-train
  fi
  rc=$?
  if [[ "$rc" -eq 0 ]] && selected_exists "$OUT_ROOT/layer_09/selected_checkpoint.tsv"; then
    return 0
  fi
  [[ "$rc" -eq 0 ]] && rc=88
  return "$rc"
}

run_eval() {
  local runner=$1 mode=$2 log=$3
  if [[ "$runner" == "$SHARED_RUNNER" && "$mode" == one_model_gpu ]]; then
    run_watched "L9_eval" "$log" "$PY" "$runner" "${common_args[@]}" --data-proc-device cuda:0 --share-data-proc-vllm --skip-train
  elif [[ "$runner" == "$SHARED_RUNNER" ]]; then
    run_watched "L9_eval" "$log" "$PY" "$runner" "${common_args[@]}" --data-proc-device cpu --skip-train
  else
    run_watched "L9_eval" "$log" "$PY" "$runner" "${common_args[@]}" --skip-train
  fi
}

exec 8>"$MAIN_LOCK"
exec 9>"$RETRY_LOCK"
if ! flock -n 9; then
  log_status "ALREADY_RUNNING lock=$RETRY_LOCK time=$(date '+%F %T %Z')"
  exit 3
fi

log_status "RETRY_WAITER_START job=${SLURM_JOB_ID:-unset} host=$(hostname) time=$(date '+%F %T %Z')"
log_status "WAIT_CURRENT_QUEUE condition=launcher_lock_released_then_L10_L11_complete"
while ! flock -n 8; do
  sleep 60
done
log_status "CURRENT_QUEUE_LOCK_RELEASED time=$(date '+%F %T %Z')"

for layer in 10 11; do
  ll=$(printf '%02d' "$layer")
  if ! complete_exists "$OUT_ROOT/layer_$ll"; then
    log_status "BLOCKED prerequisite=L$layer reason=no_complete_train_selected_eval time=$(date '+%F %T %Z')"
    exit 20
  fi
done
log_status "PREREQUISITES_OK L10=complete L11=complete"

streak=0
while (( streak < EMPTY_STREAK_REQUIRED )); do
  pids=$(nvidia-smi -i "$GPU_ID" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null | sed '/^[[:space:]]*$/d' || true)
  used=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d '[:space:]')
  used=${used:-999999}
  if [[ -z "$pids" && "$used" =~ ^[0-9]+$ ]] && (( used < 2048 )); then
    streak=$((streak+1))
  else
    streak=0
  fi
  log_status "WAIT_GPU_EXCLUSIVE used_mib=$used compute_pids=${pids//$'\n'/,} empty_streak=$streak/$EMPTY_STREAK_REQUIRED time=$(date '+%F %T')"
  (( streak < EMPTY_STREAK_REQUIRED )) && sleep 60
done

archive_incomplete_l9
tag=$(date +%Y%m%d_%H%M%S)
printf '%s\n' 'attempt,mode,stage,rc,start_time,end_time,log,note' >"$CSV"

mode=two_model_gpu
runner=$LOWMEM_RUNNER
train_log=$RUN_ROOT/logs/mmke-visual_minigpt-4-vicuna-7b_L9_retry_two_model_$tag.log
start=$(date '+%F %T')
run_train_attempt "$mode" "$train_log"
rc=$?
printf '%s\n' "1,$mode,train,$rc,$start,$(date '+%F %T'),$train_log," >>"$CSV"

if [[ "$rc" -ne 0 ]]; then
  if grep -Eqi 'CUDA out of memory|CUDA OOM|OutOfMemoryError' "$train_log"; then
    log_status "FALLBACK reason=cuda_oom from=two_model_gpu to=one_model_gpu"
    archive_incomplete_l9
    mode=one_model_gpu
    runner=$SHARED_RUNNER
    train_log=$RUN_ROOT/logs/mmke-visual_minigpt-4-vicuna-7b_L9_retry_one_model_$tag.log
    start=$(date '+%F %T')
    run_train_attempt "$mode" "$train_log"
    rc=$?
    printf '%s\n' "2,$mode,train,$rc,$start,$(date '+%F %T'),$train_log," >>"$CSV"
  else
    log_status "RETRY_STOP reason=non_oom_training_failure rc=$rc log=$train_log"
    exit "$rc"
  fi
fi

if [[ "$rc" -ne 0 ]]; then
  if grep -Eqi 'CUDA out of memory|CUDA OOM|OutOfMemoryError' "$train_log"; then
    log_status "FALLBACK reason=cuda_oom from=one_model_gpu to=cpu_data_proc"
    archive_incomplete_l9
    mode=cpu_data_proc
    runner=$SHARED_RUNNER
    train_log=$RUN_ROOT/logs/mmke-visual_minigpt-4-vicuna-7b_L9_retry_cpu_data_proc_$tag.log
    start=$(date '+%F %T')
    run_train_attempt "$mode" "$train_log"
    rc=$?
    printf '%s\n' "3,$mode,train,$rc,$start,$(date '+%F %T'),$train_log," >>"$CSV"
  fi
fi

if [[ "$rc" -ne 0 ]]; then
  log_status "RETRY_FAILED stage=train mode=$mode rc=$rc log=$train_log"
  exit "$rc"
fi

eval_log=$RUN_ROOT/logs/mmke-visual_minigpt-4-vicuna-7b_L9_retry_eval_$tag.log
start=$(date '+%F %T')
run_eval "$runner" "$mode" "$eval_log"
eval_rc=$?
printf '%s\n' "final,$mode,eval,$eval_rc,$start,$(date '+%F %T'),$eval_log," >>"$CSV"
if [[ "$eval_rc" -ne 0 ]] || ! complete_exists "$OUT_ROOT/layer_09"; then
  log_status "RETRY_FAILED stage=eval mode=$mode rc=$eval_rc complete=0 log=$eval_log"
  exit "${eval_rc:-1}"
fi

cleanup_after_success || log_status "CLEANUP_WARNING layer=L9"
touch "$RUN_ROOT/L9_RETRY_DONE"
touch "$RUN_ROOT/QUEUE_DONE_RECOVERED"
log_status "L9_RETRY_COMPLETE mode=$mode selected=$(selected_path "$OUT_ROOT/layer_09/selected_checkpoint.tsv") time=$(date '+%F %T %Z')"
