#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

TASK="${TASK:?TASK must be visual or entity}"
EXPECTED_JOB="${EXPECTED_JOB:?EXPECTED_JOB is required}"
PY="${PY:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
RUNNER="${RUNNER:-scripts/run_mmke_minigpt_llava_lowmem_sweep.py}"
MMKE_ROOT="${MMKE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
EPOCHS="${EPOCHS:-50}"
BATCH_SIZE="${BATCH_SIZE:-2}"
GPU_WAIT_MAX_USED_MIB="${GPU_WAIT_MAX_USED_MIB:-20000}"
STALL_SECONDS="${STALL_SECONDS:-7200}"
RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
OUT_ROOT="${OUT_ROOT:-/tmp/ph_teacher3/mmke_${TASK}_minigpt_llava_job${EXPECTED_JOB}_${RUN_TAG}}"
SKIP_MINI="${SKIP_MINI:-0}"
SKIP_LLAVA="${SKIP_LLAVA:-0}"

if [[ "${SLURM_JOB_ID:-}" != "$EXPECTED_JOB" ]]; then
  echo "WRONG_SLURM_JOB expected=$EXPECTED_JOB actual=${SLURM_JOB_ID:-unset}" >&2
  exit 90
fi
if [[ "$(hostname)" != "g09" ]]; then
  echo "WRONG_HOST expected=g09 actual=$(hostname)" >&2
  exit 91
fi

case "$TASK" in
  visual)
    DATA_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/data"
    TRAIN_JSON="$DATA_ROOT/vqa_mmke_visual_train_evqa_compat.json"
    EVAL_JSON="$DATA_ROOT/vqa_mmke_visual_eval_evqa_compat.json"
    MINI_LAYERS="0,1,2,3,29"
    LLAVA_LAYERS="0,1,2,7,8,9,12,13,14,15,16,22,24,26,27"
    INITIAL_MODE="${INITIAL_MODE:-lowmem}"
    ;;
  entity)
    DATA_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data"
    TRAIN_JSON="$DATA_ROOT/vqa_mmke_entity_train_evqa_compat.json"
    EVAL_JSON="$DATA_ROOT/vqa_mmke_entity_eval_evqa_compat.json"
    MINI_LAYERS="0,1,2,3,4,6,14,16,22,26,27,29"
    LLAVA_LAYERS="0,1,2,7,9,12,13,14,15,16,18,22,23,24,26,27,28,30"
    INITIAL_MODE="${INITIAL_MODE:-normal}"
    ;;
  *)
    echo "Unknown TASK=$TASK" >&2
    exit 92
    ;;
esac

IMG_ROOT="$MMKE_ROOT/data_image"
STATUS="$OUT_ROOT/queue_status.log"
CSV="$OUT_ROOT/layer_status.csv"
LOCK="$OUT_ROOT/queue.lock"
mkdir -p "$OUT_ROOT"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "QUEUE_ALREADY_RUNNING task=$TASK job=$EXPECTED_JOB out=$OUT_ROOT time=$(date)" | tee -a "$STATUS"
  exit 3
fi

for required in "$RUNNER" "$TRAIN_JSON" "$EVAL_JSON"; do
  if [[ ! -s "$required" ]]; then
    echo "REQUIRED_FILE_MISSING path=$required time=$(date)" | tee -a "$STATUS"
    exit 93
  fi
done

if [[ ! -s "$CSV" ]]; then
  echo "task,model,layer,mode,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
fi

log_status() {
  echo "$* time=$(date '+%F %T')" | tee -a "$STATUS"
}

gpu_used_mib() {
  nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9'
}

wait_gpu() {
  while true; do
    local used
    used="$(gpu_used_mib)"
    used="${used:-999999}"
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" ]]; then
      log_status "GPU_READY task=$TASK logical_gpu=0 used_mib=$used threshold=$GPU_WAIT_MAX_USED_MIB"
      return 0
    fi
    log_status "WAIT_GPU task=$TASK logical_gpu=0 used_mib=$used threshold=$GPU_WAIT_MAX_USED_MIB"
    sleep 180
  done
}

run_with_stall_watchdog() {
  local log_file="$1"
  shift
  local pid rc timed_out now_ts mtime idle
  mkdir -p "$(dirname "$log_file")"
  : > "$log_file"
  setsid "$@" >> "$log_file" 2>&1 &
  pid=$!
  timed_out=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 300
    now_ts=$(date +%s)
    mtime=$(stat -c %Y "$log_file" 2>/dev/null || echo "$now_ts")
    idle=$((now_ts - mtime))
    log_status "WATCHDOG task=$TASK pid=$pid log=$log_file idle_seconds=$idle limit=$STALL_SECONDS"
    if (( idle >= STALL_SECONDS )); then
      timed_out=1
      log_status "WATCHDOG_STALL task=$TASK pid=$pid idle_seconds=$idle action=TERM_process_group"
      kill -TERM -- "-$pid" 2>/dev/null || true
      sleep 30
      kill -KILL -- "-$pid" 2>/dev/null || true
      break
    fi
  done
  wait "$pid"
  rc=$?
  if [[ "$timed_out" -eq 1 ]]; then
    return 124
  fi
  return "$rc"
}

verify_eval() {
  local layer_dir="$1"
  "$PY" - "$layer_dir" <<'PY'
import json
import pathlib
import sys

layer = pathlib.Path(sys.argv[1])
required = [layer / "train.done", layer / "selected_checkpoint.tsv", layer / "eval_full.done"]
missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
if missing:
    raise SystemExit("missing completion files: " + ", ".join(missing))
row = json.loads((layer / "eval_full.done").read_text(encoding="utf-8"))
if int(row.get("eval_samples", 0)) <= 0:
    raise SystemExit("eval_samples is not positive")
result_dir = pathlib.Path(row.get("result_dir", ""))
result_file = result_dir / "results.json"
if not result_file.is_file() or result_file.stat().st_size == 0:
    raise SystemExit(f"missing complete evaluation result: {result_file}")
PY
}

run_train_attempt() {
  local model="$1" layer="$2" config="$3" out="$4" mode="$5" log_file="$6"
  local -a extra
  extra=()
  if [[ "$mode" == "lowmem" ]]; then
    extra=(--data-buffer-size 1 --synchronous-data-loading --activation-checkpointing)
  else
    extra=(--data-buffer-size 4)
  fi
  run_with_stall_watchdog "$log_file" "$PY" "$RUNNER" \
    --out-root "$out" --layers "$layer" --epochs "$EPOCHS" --batch-size "$BATCH_SIZE" \
    --model-name "$model" --train-data "$TRAIN_JSON" --train-img-root "$IMG_ROOT" \
    --eval-data "$EVAL_JSON" --eval-img-root "$IMG_ROOT" --config-path "$config" \
    --keep-top-ckpts 1 --keep-last-ckpts 0 --skip-eval "${extra[@]}"
}

run_eval_attempt() {
  local model="$1" layer="$2" config="$3" out="$4" log_file="$5"
  run_with_stall_watchdog "$log_file" "$PY" "$RUNNER" \
    --out-root "$out" --layers "$layer" --epochs "$EPOCHS" --batch-size "$BATCH_SIZE" \
    --model-name "$model" --train-data "$TRAIN_JSON" --train-img-root "$IMG_ROOT" \
    --eval-data "$EVAL_JSON" --eval-img-root "$IMG_ROOT" --config-path "$config" \
    --keep-top-ckpts 1 --keep-last-ckpts 0 --skip-train
}

run_layer() {
  local model="$1" layer="$2" config="$3"
  local model_out="$OUT_ROOT/$model" layer_dir="$OUT_ROOT/$model/layer_$(printf '%02d' "$layer")"
  local start_time end_time mode train_rc eval_rc train_log eval_log note archive
  mkdir -p "$model_out"
  start_time="$(date '+%F %T')"
  mode="$INITIAL_MODE"
  train_rc=777
  eval_rc=777
  note=""
  train_log="$model_out/train_L${layer}_${mode}_${RUN_TAG}.log"
  eval_log="$model_out/eval_L${layer}_${RUN_TAG}.log"

  if [[ -s "$layer_dir/train.done" && -s "$layer_dir/selected_checkpoint.tsv" ]]; then
    train_rc=0
    note="train_skip_existing"
    log_status "TRAIN_SKIP task=$TASK model=$model layer=$layer reason=existing_complete"
  else
    wait_gpu
    log_status "TRAIN_START task=$TASK model=$model layer=$layer mode=$mode epochs=$EPOCHS batch=$BATCH_SIZE"
    run_train_attempt "$model" "$layer" "$config" "$model_out" "$mode" "$train_log"
    train_rc=$?
    log_status "TRAIN_END task=$TASK model=$model layer=$layer mode=$mode rc=$train_rc"

    if [[ "$train_rc" -ne 0 && "$mode" == "normal" ]] && grep -Eqi 'CUDA out of memory|OutOfMemoryError' "$train_log"; then
      archive="$OUT_ROOT/failed_attempts/${model}_L${layer}_normal_${RUN_TAG}"
      mkdir -p "$archive"
      if [[ -d "$layer_dir" ]]; then
        mv "$layer_dir" "$archive/"
      fi
      note="normal_oom_preserved_and_retried_lowmem"
      mode="lowmem"
      train_log="$model_out/train_L${layer}_${mode}_${RUN_TAG}.log"
      wait_gpu
      log_status "TRAIN_RETRY task=$TASK model=$model layer=$layer reason=normal_oom mode=lowmem archive=$archive"
      run_train_attempt "$model" "$layer" "$config" "$model_out" "$mode" "$train_log"
      train_rc=$?
      log_status "TRAIN_RETRY_END task=$TASK model=$model layer=$layer mode=$mode rc=$train_rc"
    fi
  fi

  if [[ "$train_rc" -eq 0 && -s "$layer_dir/train.done" && -s "$layer_dir/selected_checkpoint.tsv" ]]; then
    if [[ -s "$layer_dir/eval_full.done" ]] && verify_eval "$layer_dir" >> "$eval_log" 2>&1; then
      eval_rc=0
      note="${note};eval_skip_existing"
      log_status "EVAL_SKIP task=$TASK model=$model layer=$layer reason=existing_complete"
    else
      wait_gpu
      log_status "EVAL_START task=$TASK model=$model layer=$layer data=$EVAL_JSON"
      run_eval_attempt "$model" "$layer" "$config" "$model_out" "$eval_log"
      eval_rc=$?
      if [[ "$eval_rc" -eq 0 ]]; then
        verify_eval "$layer_dir" >> "$eval_log" 2>&1
        eval_rc=$?
      fi
      log_status "EVAL_END task=$TASK model=$model layer=$layer rc=$eval_rc"
    fi
  else
    note="${note};no_selected_checkpoint"
    log_status "EVAL_NOT_RUN task=$TASK model=$model layer=$layer train_rc=$train_rc reason=no_selected_checkpoint"
  fi

  end_time="$(date '+%F %T')"
  echo "$TASK,$model,$layer,$mode,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,$note" >> "$CSV"
}

run_model() {
  local model="$1" layers_csv="$2" config="$3" layer free_kib
  IFS=',' read -ra layers <<< "$layers_csv"
  log_status "MODEL_QUEUE_START task=$TASK model=$model layers=$layers_csv"
  for layer in "${layers[@]}"; do
    free_kib=$(df -Pk /tmp | awk 'NR==2 {print $4}')
    if (( free_kib < 15 * 1024 * 1024 )); then
      log_status "QUEUE_PAUSE_DISK_LOW task=$TASK model=$model next_layer=$layer free_kib=$free_kib minimum_kib=$((15*1024*1024))"
      return 95
    fi
    run_layer "$model" "$layer" "$config"
  done
  log_status "MODEL_QUEUE_END task=$TASK model=$model"
}

log_status "QUEUE_START task=$TASK job=$EXPECTED_JOB host=$(hostname) logical_gpu=${CUDA_VISIBLE_DEVICES:-unset} out=$OUT_ROOT initial_mode=$INITIAL_MODE stall_seconds=$STALL_SECONDS"
nvidia-smi --query-gpu=index,uuid,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS"
log_status "DATA_BINDING task=$TASK train=$TRAIN_JSON eval=$EVAL_JSON images=$IMG_ROOT"
log_status "CANDIDATES task=$TASK minigpt=$MINI_LAYERS llava=$LLAVA_LAYERS"

if [[ "$SKIP_MINI" -eq 1 ]]; then
  mini_rc=0
  log_status "MODEL_QUEUE_SKIP task=$TASK model=minigpt-4-vicuna-7b reason=explicit_skip"
else
  run_model "minigpt-4-vicuna-7b" "$MINI_LAYERS" "configs/vead/minigpt-4-vicuna-7b.yaml"
  mini_rc=$?
fi
if [[ "$SKIP_LLAVA" -eq 1 ]]; then
  llava_rc=0
  log_status "MODEL_QUEUE_SKIP task=$TASK model=llava-v1.5-7b reason=explicit_skip"
else
  run_model "llava-v1.5-7b" "$LLAVA_LAYERS" "configs/vead/llava-v1.5-7b.yaml"
  llava_rc=$?
fi

if [[ "$mini_rc" -eq 0 && "$llava_rc" -eq 0 ]]; then
  date '+%F %T' > "$OUT_ROOT/QUEUE_ALL_LAYERS_ATTEMPTED"
fi
log_status "QUEUE_END task=$TASK minigpt_queue_rc=$mini_rc llava_queue_rc=$llava_rc"
