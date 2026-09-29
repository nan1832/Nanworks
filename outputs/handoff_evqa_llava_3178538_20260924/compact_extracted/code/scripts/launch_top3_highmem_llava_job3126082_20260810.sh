#!/usr/bin/env bash
set -uo pipefail

PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
GENERAL_RUNNER=scripts/run_mmke_llava_shared_gpu_sweep.py
RUN_ROOT=/tmp/ph_teacher3/formal_top3_highmem_llava_job3126082_20260810
GPU_ID=0
EPOCHS=50
BATCH_SIZE=2
SEED=20260601
EMA_ALPHA=0.1
STALL_SECONDS=7200
POLL_SECONDS=60

MMKE_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench
IMG_ROOT=$MMKE_ROOT/data_image
VIS_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data
ENT_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data
VIS_TRAIN=$VIS_DATA/vqa_mmke_visual_train_evqa_compat.json
VIS_EVAL=$VIS_DATA/vqa_mmke_visual_eval_evqa_compat.json
ENT_TRAIN=$ENT_DATA/vqa_mmke_entity_train_evqa_compat.json
ENT_EVAL=$ENT_DATA/vqa_mmke_entity_eval_evqa_compat.json

STATUS=$RUN_ROOT/queue.status.log
CSV=$RUN_ROOT/layer_status.csv
LOCK=$RUN_ROOT/launcher.lock
TAG=$(date +%Y%m%d_%H%M%S)

mkdir -p "$RUN_ROOT/logs"
cd "$PROJ" || exit 1
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

exec 9>"$LOCK"
if ! flock -n 9; then
  printf '%s\n' "ALREADY_RUNNING time=$(date '+%F %T %Z') lock=$LOCK" | tee -a "$STATUS"
  exit 3
fi

if [[ ! -s "$CSV" ]]; then
  printf '%s\n' 'dataset,model,layer,stage,rc,start_time,end_time,log,note' >"$CSV"
fi

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
  local dataset=$1 model=$2 layer=$3 stage=$4 log=$5
  shift 5
  local pid rc now last_progress last_sig sig last_raw raw heartbeat
  : >"$log"
  log_status "WATCH_START dataset=$dataset model=$model layer=$layer stage=$stage idle_limit=$STALL_SECONDS log=$log time=$(date '+%F %T %Z')"
  setsid env CUDA_VISIBLE_DEVICES="$GPU_ID" PYTORCH_CUDA_ALLOC_CONF="$PYTORCH_CUDA_ALLOC_CONF" "$@" >>"$log" 2>&1 &
  pid=$!
  last_progress=$(date +%s)
  last_sig=''
  last_raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
  heartbeat=$last_progress
  log_status "PROCESS_START dataset=$dataset model=$model layer=$layer stage=$stage pid=$pid pgid=$pid"

  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL_SECONDS"
    now=$(date +%s)
    sig=$(progress_signature "$log" 2>/dev/null || true)
    raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)

    if [[ -n "$sig" && "$sig" != "$last_sig" ]]; then
      last_sig=$sig
      last_progress=$now
      log_status "WATCH_PROGRESS dataset=$dataset model=$model layer=$layer stage=$stage sig=${sig:0:320} time=$(date '+%F %T')"
    elif [[ -z "$last_sig" && "$raw" != "$last_raw" ]]; then
      # During model loading/preprocessing, changing log content is progress.
      last_progress=$now
    fi
    last_raw=$raw

    if (( now - heartbeat >= 600 )); then
      log_status "WATCH_HEARTBEAT dataset=$dataset model=$model layer=$layer stage=$stage idle_seconds=$((now-last_progress)) gpu=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -d '\n') time=$(date '+%F %T')"
      heartbeat=$now
    fi

    if (( now - last_progress >= STALL_SECONDS )); then
      log_status "WATCHDOG_STALL dataset=$dataset model=$model layer=$layer stage=$stage pid=$pid unchanged_seconds=$((now-last_progress)) time=$(date '+%F %T %Z')"
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
  log_status "PROCESS_END dataset=$dataset model=$model layer=$layer stage=$stage pid=$pid rc=$rc time=$(date '+%F %T %Z')"
  return "$rc"
}

cleanup_nonselected_checkpoints() {
  local d=$1 selected selected_abs d_abs parent item item_abs removed=0 bytes=0 item_bytes cache cache_abs model_abs
  complete_exists "$d" || return 1
  selected=$(selected_path "$d/selected_checkpoint.tsv") || return 1
  selected_abs=$(realpath -e "$selected") || return 1
  d_abs=$(realpath -e "$d") || return 1
  case "$selected_abs" in
    "$d_abs"/*) ;;
    *) log_status "CLEANUP_REFUSED reason=selected_outside_layer layer_dir=$d_abs selected=$selected_abs"; return 2 ;;
  esac
  parent=$(dirname "$selected_abs")
  case "$parent" in
    "$d_abs"/*/checkpoints) ;;
    *) log_status "CLEANUP_REFUSED reason=unexpected_checkpoint_parent parent=$parent selected=$selected_abs"; return 2 ;;
  esac

  for item in "$parent"/*; do
    [[ -e "$item" ]] || continue
    item_abs=$(realpath -e "$item") || continue
    [[ "$item_abs" == "$selected_abs" ]] && continue
    item_bytes=$(du -sb "$item_abs" 2>/dev/null | awk '{print $1}')
    item_bytes=${item_bytes:-0}
    rm -rf -- "$item_abs"
    removed=$((removed+1))
    bytes=$((bytes+item_bytes))
  done
  model_abs=$(realpath -e "$(dirname "$d_abs")") || return 1
  cache="$(dirname "$d_abs")/cache/$(basename "$d_abs")"
  if [[ -e "$cache" ]]; then
    cache_abs=$(realpath -e "$cache") || return 1
    case "$cache_abs" in
      "$model_abs"/cache/layer_*) ;;
      *) log_status "CLEANUP_REFUSED reason=unexpected_cache_path cache=$cache_abs"; return 2 ;;
    esac
    item_bytes=$(du -sb "$cache_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$cache_abs"
    removed=$((removed+1))
    bytes=$((bytes+${item_bytes:-0}))
  fi
  log_status "CHECKPOINT_CLEANUP layer_dir=$d selected=$selected_abs removed=$removed bytes=$bytes time=$(date '+%F %T %Z')"
}

run_stage() {
  local dataset=$1 model=$2 layer=$3 stage=$4 runner=$5 config=$6 train_json=$7 eval_json=$8 buffer=$9 lowmem=${10}
  local out=$RUN_ROOT/$dataset/$model log=$RUN_ROOT/logs/${dataset}_${model}_L${layer}_${stage}_${TAG}.log
  local start end rc
  local -a args
  mkdir -p "$out"
  args=(
    "$PY" "$runner"
    --out-root "$out"
    --layers "$layer"
    --epochs "$EPOCHS"
    --batch-size "$BATCH_SIZE"
    --model-name "$model"
    --device cuda:0
    --train-data "$train_json"
    --train-img-root "$IMG_ROOT"
    --eval-data "$eval_json"
    --eval-img-root "$IMG_ROOT"
    --config-path "$config"
    --seed "$SEED"
    --ema-alpha "$EMA_ALPHA"
    --data-buffer-size "$buffer"
    --keep-top-ckpts 1
    --keep-last-ckpts 0
  )
  if [[ "$lowmem" == 1 ]]; then
    args+=(--synchronous-data-loading --activation-checkpointing)
  fi
  if [[ "$model" == llava-v1.5-7b ]]; then
    # One frozen LLaVA is reused for target tracing and adapter training.
    # This only changes memory scheduling; optimization/data/config stay fixed.
    args+=(--data-proc-device cuda:0 --share-data-proc-vllm)
  fi
  if [[ "$stage" == train ]]; then args+=(--skip-eval); else args+=(--skip-train); fi

  start=$(date '+%F %T')
  log_status "STAGE_START dataset=$dataset model=$model layer=$layer stage=$stage runner=$runner config=$config train=$train_json eval=$eval_json buffer=$buffer lowmem=$lowmem time=$start"
  run_watched "$dataset" "$model" "$layer" "$stage" "$log" "${args[@]}"
  rc=$?
  end=$(date '+%F %T')
  printf '%s\n' "$dataset,$model,$layer,$stage,$rc,$start,$end,$log," >>"$CSV"
  log_status "STAGE_END dataset=$dataset model=$model layer=$layer stage=$stage rc=$rc time=$end"
  return "$rc"
}

run_layer() {
  local dataset=$1 model=$2 layer=$3 runner=$4 config=$5 train_json=$6 eval_json=$7 buffer=$8 lowmem=$9
  local out=$RUN_ROOT/$dataset/$model d ll train_rc=777 eval_rc=777 note=''
  ll=$(printf '%02d' "$layer")
  d=$out/layer_$ll
  mkdir -p "$out"

  log_status "LAYER_BEGIN dataset=$dataset model=$model layer=$layer time=$(date '+%F %T %Z')"
  if [[ -f "$d/train.done" ]] && selected_exists "$d/selected_checkpoint.tsv"; then
    train_rc=0
    note=skip_existing_train
    log_status "TRAIN_SKIP dataset=$dataset model=$model layer=$layer reason=existing_selected"
  else
    run_stage "$dataset" "$model" "$layer" train "$runner" "$config" "$train_json" "$eval_json" "$buffer" "$lowmem"
    train_rc=$?
  fi

  if [[ "$train_rc" -eq 0 ]] && selected_exists "$d/selected_checkpoint.tsv"; then
    if [[ -f "$d/eval_full.done" ]]; then
      eval_rc=0
      note=${note:+$note;}'skip_existing_eval'
      log_status "EVAL_SKIP dataset=$dataset model=$model layer=$layer reason=existing_eval"
    else
      run_stage "$dataset" "$model" "$layer" eval "$runner" "$config" "$train_json" "$eval_json" "$buffer" "$lowmem"
      eval_rc=$?
    fi
  else
    note=${note:+$note;}'train_failed_or_no_selected'
    log_status "EVAL_NOT_RUN dataset=$dataset model=$model layer=$layer train_rc=$train_rc selected=0"
  fi

  if complete_exists "$d"; then
    cleanup_nonselected_checkpoints "$d" || note=${note:+$note;}'cleanup_warning'
    log_status "LAYER_COMPLETE dataset=$dataset model=$model layer=$layer selected=$(selected_path "$d/selected_checkpoint.tsv") time=$(date '+%F %T %Z')"
  else
    note=${note:+$note;}'incomplete_artifacts'
    log_status "LAYER_INCOMPLETE dataset=$dataset model=$model layer=$layer train_rc=$train_rc eval_rc=$eval_rc note=$note time=$(date '+%F %T %Z')"
  fi
  printf '%s\n' "$dataset,$model,$layer,final,$eval_rc,$(date '+%F %T'),$(date '+%F %T'),,$note" >>"$CSV"
  sleep 15
}

log_status "QUEUE_START job=${SLURM_JOB_ID:-unset} host=$(hostname) gpu=$GPU_ID root=$RUN_ROOT time=$(date '+%F %T %Z')"
log_status "COMPARABILITY epochs=$EPOCHS batch_size=$BATCH_SIZE seed=$SEED ema_alpha=$EMA_ALPHA selection=min_finite_ema eval=independent_dataset_json"
log_status "QUEUE mmke-visual/llava-v1.5-7b/L15,L16,L14,L27,L26,L24,L22,L3 (formal Top-3 only)"
log_status "VIS_TRAIN=$VIS_TRAIN VIS_EVAL=$VIS_EVAL ENT_TRAIN=$ENT_TRAIN ENT_EVAL=$ENT_EVAL"
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS"

for required in "$PY" "$GENERAL_RUNNER" "$VIS_TRAIN" "$VIS_EVAL" "$IMG_ROOT" \
  configs/vead/llava-v1.5-7b.yaml; do
  if [[ ! -e "$required" ]]; then
    log_status "PRECHECK_FAILED missing=$required time=$(date '+%F %T %Z')"
    exit 2
  fi
done

for layer in 15 16 14 27 26 24 22 3; do
  run_layer mmke-visual llava-v1.5-7b "$layer" "$GENERAL_RUNNER" configs/vead/llava-v1.5-7b.yaml "$VIS_TRAIN" "$VIS_EVAL" 1 1
done

all_ok=1
for spec in \
  'mmke-visual/llava-v1.5-7b/layer_15' \
  'mmke-visual/llava-v1.5-7b/layer_16' \
  'mmke-visual/llava-v1.5-7b/layer_14' \
  'mmke-visual/llava-v1.5-7b/layer_27' \
  'mmke-visual/llava-v1.5-7b/layer_26' \
  'mmke-visual/llava-v1.5-7b/layer_24' \
  'mmke-visual/llava-v1.5-7b/layer_22' \
  'mmke-visual/llava-v1.5-7b/layer_03'; do
  complete_exists "$RUN_ROOT/$spec" || all_ok=0
done

if [[ "$all_ok" -eq 1 ]]; then
  touch "$RUN_ROOT/QUEUE_DONE"
  log_status "QUEUE_DONE time=$(date '+%F %T %Z')"
else
  touch "$RUN_ROOT/QUEUE_FINISHED_WITH_FAILURES"
  log_status "QUEUE_FINISHED_WITH_FAILURES time=$(date '+%F %T %Z')"
fi
