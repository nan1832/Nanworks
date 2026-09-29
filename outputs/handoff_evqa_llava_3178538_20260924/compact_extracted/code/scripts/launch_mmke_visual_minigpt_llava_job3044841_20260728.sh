#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUNNER=scripts/run_mmke_minigpt_llava_lowmem_sweep.py
RUN_ROOT=/tmp/ph_teacher3/mmke_visual_minigpt_llava_job3044841_20260728
DATA_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data
TRAIN_JSON="$DATA_ROOT/vqa_mmke_visual_train_evqa_compat.json"
EVAL_JSON="$DATA_ROOT/vqa_mmke_visual_eval_evqa_compat.json"
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
EPOCHS=50
BATCH_SIZE=2
IDLE_LIMIT=7200
RUN_TAG=$(date +%Y%m%d_%H%M%S)
STATUS="$RUN_ROOT/launcher_${RUN_TAG}.status.log"
CSV="$RUN_ROOT/launcher_${RUN_TAG}.layers.csv"

mkdir -p "$RUN_ROOT"
echo 'model,layer,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note' > "$CSV"
echo "LAUNCH_START time=$(date '+%F %T %Z') host=$(hostname) job=${SLURM_JOB_ID:-unset} step=${SLURM_STEP_ID:-unset} cuda_visible=${CUDA_VISIBLE_DEVICES:-unset}" | tee -a "$STATUS"
echo "QUEUE minigpt=L0,L1,L2,L3,L29 llava=L0,L1,L2,L7,L8,L9,L12,L13,L14,L15,L16,L22,L24,L26,L27" | tee -a "$STATUS"

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
  local phase="$1" model="$2" layer="$3" log="$4"
  shift 4
  local pid rc now last_progress last_sig sig
  echo "WATCH_START phase=$phase model=$model layer=$layer idle_limit=$IDLE_LIMIT time=$(date '+%F %T')" | tee -a "$STATUS"
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
      echo "WATCH_PROGRESS phase=$phase model=$model layer=$layer time=$(date '+%F %T') sig=${sig:0:240}" >> "$STATUS"
    fi
    if (( now - last_progress >= IDLE_LIMIT )); then
      echo "WATCH_IDLE_TIMEOUT phase=$phase model=$model layer=$layer idle_seconds=$((now-last_progress)) time=$(date '+%F %T')" | tee -a "$STATUS"
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
  echo "WATCH_END phase=$phase model=$model layer=$layer rc=$rc time=$(date '+%F %T')" | tee -a "$STATUS"
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

run_layer() {
  local model="$1" layer="$2" config="$3"
  local out="$RUN_ROOT/$model" ll d train_log eval_log start end train_rc eval_rc note
  ll=$(printf '%02d' "$layer")
  d="$out/layer_$ll"
  train_log="$out/train_L${layer}_${RUN_TAG}.log"
  eval_log="$out/eval_L${layer}_${RUN_TAG}.log"
  mkdir -p "$out"
  start=$(date '+%F %T')
  train_rc=777
  eval_rc=777
  note=''

  if complete_exists "$d"; then
    train_rc=0; eval_rc=0; note='skip_complete'
    echo "LAYER_SKIP_COMPLETE model=$model layer=$layer time=$(date '+%F %T')" | tee -a "$STATUS"
  else
    echo "TRAIN_START model=$model layer=$layer config=$config time=$(date '+%F %T')" | tee -a "$STATUS"
    : > "$train_log"
    run_watched train "$model" "$layer" "$train_log" \
      "$PY" "$RUNNER" \
      --out-root "$out" \
      --layers "$layer" \
      --epochs "$EPOCHS" \
      --batch-size "$BATCH_SIZE" \
      --model-name "$model" \
      --train-data "$TRAIN_JSON" \
      --train-img-root "$IMG_ROOT" \
      --eval-data "$EVAL_JSON" \
      --eval-img-root "$IMG_ROOT" \
      --config-path "$config" \
      --keep-top-ckpts 1 \
      --keep-last-ckpts 0 \
      --skip-eval \
      --data-buffer-size 1 \
      --synchronous-data-loading \
      --activation-checkpointing
    train_rc=$?
    echo "TRAIN_END model=$model layer=$layer rc=$train_rc time=$(date '+%F %T')" | tee -a "$STATUS"

    if [[ "$train_rc" -eq 0 ]] && selected_exists "$d/selected_checkpoint.tsv"; then
      echo "EVAL_START model=$model layer=$layer data=$EVAL_JSON time=$(date '+%F %T')" | tee -a "$STATUS"
      : > "$eval_log"
      run_watched eval "$model" "$layer" "$eval_log" \
        "$PY" "$RUNNER" \
        --out-root "$out" \
        --layers "$layer" \
        --epochs "$EPOCHS" \
        --batch-size "$BATCH_SIZE" \
        --model-name "$model" \
        --train-data "$TRAIN_JSON" \
        --train-img-root "$IMG_ROOT" \
        --eval-data "$EVAL_JSON" \
        --eval-img-root "$IMG_ROOT" \
        --config-path "$config" \
        --keep-top-ckpts 1 \
        --keep-last-ckpts 0 \
        --skip-train \
        --data-buffer-size 1 \
        --synchronous-data-loading \
        --activation-checkpointing
      eval_rc=$?
      echo "EVAL_END model=$model layer=$layer rc=$eval_rc time=$(date '+%F %T')" | tee -a "$STATUS"
    else
      note="train_failed_or_no_selected"
      echo "EVAL_NOT_RUN model=$model layer=$layer train_rc=$train_rc selected=0 time=$(date '+%F %T')" | tee -a "$STATUS"
    fi
  fi

  end=$(date '+%F %T')
  echo "$model,$layer,$train_rc,$eval_rc,$start,$end,$train_log,$eval_log,$note" >> "$CSV"
  sleep 15
}

for layer in 0 1 2 3 29; do
  run_layer minigpt-4-vicuna-7b "$layer" configs/vead/minigpt-4-vicuna-7b.yaml
done

for layer in 0 1 2 7 8 9 12 13 14 15 16 22 24 26 27; do
  run_layer llava-v1.5-7b "$layer" configs/vead/llava-v1.5-7b.yaml
done

echo "QUEUE_DONE time=$(date '+%F %T %Z')" | tee -a "$STATUS"
touch "$RUN_ROOT/QUEUE_DONE"
