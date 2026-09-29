#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1

PY=/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python
RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
OUT=/tmp/ph_teacher3/evqa_pilot500_blip2_missing5_job3044208_20260728
TRAIN_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
EVAL_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
EVAL_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
LAYERS=(14 1 3 4 2)
IDLE_LIMIT=7200
TAG=$(date +%Y%m%d_%H%M%S)
STATUS="$OUT/launcher_${TAG}.status.log"
CSV="$OUT/launcher_${TAG}.layers.csv"

mkdir -p "$OUT/logs"
echo 'phase,layer,rc,start_time,end_time,log,note' > "$CSV"
echo "LAUNCH_START time=$(date '+%F %T %Z') host=$(hostname) job=${SLURM_JOB_ID:-unset} step=${SLURM_STEP_ID:-unset} cuda_visible=${CUDA_VISIBLE_DEVICES:-unset}" | tee -a "$STATUS"
echo "COMPARABILITY epochs=50 batch_size=2 seed=20260601 ema_alpha=0.1 data_buffer_size=4 keep_top_ckpts=5 keep_last_ckpts=2" | tee -a "$STATUS"
echo "TRAIN_DATA=$TRAIN_DATA" | tee -a "$STATUS"
echo "EVAL_DATA=$EVAL_DATA" | tee -a "$STATUS"
echo "QUEUE layers=L14,L1,L3,L4,L2 policy=train_all_then_eval_all" | tee -a "$STATUS"

progress_signature() {
  "$PY" - "$1" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.exists():
    raise SystemExit(0)
with p.open('rb') as f:
    try:
        f.seek(-4 * 1024 * 1024, 2)
    except OSError:
        f.seek(0)
    text = f.read().decode('utf-8', errors='ignore').replace('\r', '\n')
last = ''
for line in text.splitlines():
    if re.search(r'\b\d+\s*/\s*\d+\b', line) and re.search(
        r'Epoch|Pre-process|Evaluat|eval|train|it/s|Waiting data', line, re.I
    ):
        last = line[-500:]
if last:
    print(last)
PY
}

run_watched() {
  local phase="$1" layer="$2" log="$3"
  shift 3
  local pid rc now last_progress last_sig sig
  echo "WATCH_START phase=$phase layer=$layer idle_limit=$IDLE_LIMIT time=$(date '+%F %T')" | tee -a "$STATUS"
  setsid "$@" >> "$log" 2>&1 &
  pid=$!
  last_progress=$(date +%s)
  last_sig=''
  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
    sig=$(progress_signature "$log" 2>/dev/null || true)
    now=$(date +%s)
    if [[ -n "$sig" && "$sig" != "$last_sig" ]]; then
      last_sig="$sig"
      last_progress=$now
      echo "WATCH_PROGRESS phase=$phase layer=$layer time=$(date '+%F %T') sig=${sig:0:260}" >> "$STATUS"
    fi
    if (( now - last_progress >= IDLE_LIMIT )); then
      echo "WATCH_IDLE_TIMEOUT phase=$phase layer=$layer idle_seconds=$((now-last_progress)) time=$(date '+%F %T')" | tee -a "$STATUS"
      kill -TERM -- "-$pid" 2>/dev/null || true
      for _ in $(seq 1 60); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$pid" 2>/dev/null; then
        kill -KILL -- "-$pid" 2>/dev/null || true
      fi
      wait "$pid" 2>/dev/null || true
      return 124
    fi
  done
  wait "$pid"
  rc=$?
  echo "WATCH_END phase=$phase layer=$layer rc=$rc time=$(date '+%F %T')" | tee -a "$STATUS"
  return "$rc"
}

selected_exists() {
  local selected="$1" p
  [[ -s "$selected" ]] || return 1
  p=$(tail -n 1 "$selected" | awk -F '\t' '{print $NF}' | tr -d '\r')
  [[ -n "$p" && -f "$p" ]]
}

complete_exists() {
  local d="$1"
  [[ -s "$d/train.done" && -s "$d/selected_checkpoint.tsv" && -s "$d/eval_full.done" ]] || return 1
  selected_exists "$d/selected_checkpoint.tsv" || return 1
  find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q .
}

for L in "${LAYERS[@]}"; do
  LL=$(printf '%02d' "$L")
  D="$OUT/layer_$LL"
  LOG="$OUT/logs/train_L${LL}_${TAG}.log"
  START=$(date '+%F %T')
  RC=777
  NOTE=''
  if [[ -s "$D/train.done" ]] && selected_exists "$D/selected_checkpoint.tsv"; then
    RC=0
    NOTE='skip_train_complete'
    echo "TRAIN_SKIP layer=$L time=$(date '+%F %T')" | tee -a "$STATUS"
  else
    : > "$LOG"
    echo "TRAIN_START layer=$L time=$(date '+%F %T')" | tee -a "$STATUS"
    run_watched train "$L" "$LOG" \
      "$PY" "$RUNNER" \
      --out-root "$OUT" \
      --layers "$L" \
      --epochs 50 \
      --batch-size 2 \
      --train-data "$TRAIN_DATA" \
      --train-img-root "$TRAIN_IMG" \
      --eval-data "$EVAL_DATA" \
      --eval-img-root "$EVAL_IMG" \
      --skip-eval \
      --keep-top-ckpts 5 \
      --keep-last-ckpts 2 \
      --overwrite-train
    RC=$?
    echo "TRAIN_END layer=$L rc=$RC time=$(date '+%F %T')" | tee -a "$STATUS"
    if [[ "$RC" -ne 0 ]] || ! selected_exists "$D/selected_checkpoint.tsv"; then
      NOTE='train_failed_or_no_selected'
    fi
  fi
  echo "train,$L,$RC,$START,$(date '+%F %T'),$LOG,$NOTE" >> "$CSV"
  sleep 15
done

for L in "${LAYERS[@]}"; do
  LL=$(printf '%02d' "$L")
  D="$OUT/layer_$LL"
  LOG="$OUT/logs/eval_L${LL}_${TAG}.log"
  START=$(date '+%F %T')
  RC=777
  NOTE=''
  if complete_exists "$D"; then
    RC=0
    NOTE='skip_eval_complete'
    echo "EVAL_SKIP layer=$L time=$(date '+%F %T')" | tee -a "$STATUS"
  elif selected_exists "$D/selected_checkpoint.tsv"; then
    : > "$LOG"
    echo "EVAL_START layer=$L data=$EVAL_DATA time=$(date '+%F %T')" | tee -a "$STATUS"
    run_watched eval "$L" "$LOG" \
      "$PY" "$RUNNER" \
      --out-root "$OUT" \
      --layers "$L" \
      --epochs 50 \
      --batch-size 2 \
      --train-data "$TRAIN_DATA" \
      --train-img-root "$TRAIN_IMG" \
      --eval-data "$EVAL_DATA" \
      --eval-img-root "$EVAL_IMG" \
      --skip-train \
      --overwrite-eval
    RC=$?
    echo "EVAL_END layer=$L rc=$RC time=$(date '+%F %T')" | tee -a "$STATUS"
    complete_exists "$D" || NOTE='eval_failed_or_incomplete_artifacts'
  else
    NOTE='no_selected_checkpoint'
    echo "EVAL_NOT_RUN layer=$L selected=0 time=$(date '+%F %T')" | tee -a "$STATUS"
  fi
  echo "eval,$L,$RC,$START,$(date '+%F %T'),$LOG,$NOTE" >> "$CSV"
  sleep 15
done

ALL_OK=1
for L in "${LAYERS[@]}"; do
  LL=$(printf '%02d' "$L")
  complete_exists "$OUT/layer_$LL" || ALL_OK=0
done
if [[ "$ALL_OK" -eq 1 ]]; then
  touch "$OUT/QUEUE_DONE"
  echo "QUEUE_DONE time=$(date '+%F %T %Z')" | tee -a "$STATUS"
else
  touch "$OUT/QUEUE_FINISHED_WITH_FAILURES"
  echo "QUEUE_FINISHED_WITH_FAILURES time=$(date '+%F %T %Z')" | tee -a "$STATUS"
fi
