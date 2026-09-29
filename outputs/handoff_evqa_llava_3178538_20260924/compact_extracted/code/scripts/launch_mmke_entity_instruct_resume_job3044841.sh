#!/usr/bin/env bash
set -uo pipefail

PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
DATA_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000
ROOT=/tmp/ph_teacher3/mmke_entity_job3044841_20260715_121700
OUT=$ROOT/instructblip-vicuna-7b
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
RESUME_RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep_resume.py
CONFIG=configs/vead/instructblip-vicuna-7b.yaml
TRAIN_JSON=$DATA_ROOT/data/vqa_mmke_entity_train_evqa_compat.json
EVAL_JSON=$DATA_ROOT/data/vqa_mmke_entity_eval_evqa_compat.json
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
RESUME_CKPT=$OUT/layer_01/records/vead/instructblip-vicuna-7b/pilot500_blip2_visedit_L01-lr-1-t-1-v-1/checkpoints/epoch-45-i-14310-ema_loss-1.5520
STATUS=$ROOT/instruct_resume_job3044841_status.log
CSV=$ROOT/instruct_resume_job3044841_layers.csv
LOCK=$ROOT/instruct_resume_job3044841.lock
# Slurm exposes physical GPU1 as logical GPU0 inside job 3044841 steps.
PHYSICAL_GPU_ID=1
GPU_ID=0
GPU_MAX_IDLE_USED_MIB=512
STALL_SECONDS=7200
POLL_SECONDS=60
RUN_TAG=$(date +%Y%m%d_%H%M%S)

mkdir -p "$ROOT" "$OUT"
cd "$PROJ" || exit 1
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

exec 9>"$LOCK"
if ! flock -n 9; then
  printf '%s\n' "ALREADY_RUNNING time=$(date '+%F %T')" >>"$STATUS"
  exit 3
fi

if [[ ! -s "$CSV" ]]; then
  printf '%s\n' "model,layer,stage,buffer_size,rc,start_time,end_time,log,note" >"$CSV"
fi

log_status() {
  printf '%s\n' "$*" | tee -a "$STATUS"
}

wait_gpu_clean() {
  local stable=0 used cuda_ok
  while (( stable < 3 )); do
    used=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -dc '0-9')
    used=${used:-999999}
    cuda_ok=0
    if (( used <= GPU_MAX_IDLE_USED_MIB )); then
      if CUDA_VISIBLE_DEVICES="$GPU_ID" "$PY" - <<'PY' >/tmp/ph_teacher3/instruct_resume_cuda_probe.log 2>&1
import torch
assert torch.cuda.is_available()
assert torch.cuda.device_count() == 1
torch.cuda.init()
PY
      then
        cuda_ok=1
      fi
    fi
    if (( used <= GPU_MAX_IDLE_USED_MIB && cuda_ok == 1 )); then
      stable=$((stable + 1))
    else
      stable=0
    fi
    log_status "GPU1_CLEAN_PROBE used_mib=$used cuda_ok=$cuda_ok stable=$stable/3 time=$(date '+%F %T')"
    (( stable >= 3 )) || sleep 20
  done
}

run_with_watchdog() {
  local log_file="$1"
  shift
  local pid now last_progress signature new_signature rc
  : >"$log_file"
  setsid env CUDA_VISIBLE_DEVICES="$GPU_ID" "$@" >>"$log_file" 2>&1 &
  pid=$!
  now=$(date +%s)
  last_progress=$now
  signature=$(stat -c '%s:%Y' "$log_file" 2>/dev/null || echo 0:0)
  log_status "PROCESS_START pid=$pid pgid=$pid log=$log_file time=$(date '+%F %T')"
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL_SECONDS"
    new_signature=$(stat -c '%s:%Y' "$log_file" 2>/dev/null || echo 0:0)
    now=$(date +%s)
    if [[ "$new_signature" != "$signature" ]]; then
      signature=$new_signature
      last_progress=$now
    elif (( now - last_progress >= STALL_SECONDS )); then
      log_status "WATCHDOG_STALL pid=$pid unchanged_seconds=$((now-last_progress)) log=$log_file time=$(date '+%F %T')"
      kill -TERM -- "-$pid" 2>/dev/null || true
      for _ in $(seq 1 30); do
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
  log_status "PROCESS_END pid=$pid rc=$rc log=$log_file time=$(date '+%F %T')"
  return "$rc"
}

common_args() {
  local runner="$1" layer="$2" buffer="$3"
  printf '%s\0' "$runner" \
    --out-root "$OUT" --layers "$layer" --epochs 50 --batch-size 2 \
    --model-name instructblip-vicuna-7b --device cuda:0 \
    --train-data "$TRAIN_JSON" --train-img-root "$IMG_ROOT" \
    --eval-data "$EVAL_JSON" --eval-img-root "$IMG_ROOT" \
    --config-path "$CONFIG" --seed 20260601 --ema-alpha 0.1 \
    --data-buffer-size "$buffer" --keep-top-ckpts 5 --keep-last-ckpts 2
}

run_stage() {
  local layer="$1" stage="$2" buffer="$3" runner="$4" note="$5"
  shift 5
  local start end rc log_file
  local -a args extra
  extra=("$@")
  mapfile -d '' -t args < <(common_args "$runner" "$layer" "$buffer")
  if [[ "$stage" == train ]]; then args+=(--skip-eval); else args+=(--skip-train); fi
  args+=("${extra[@]}")
  wait_gpu_clean
  log_file=$OUT/${stage}_L${layer}_${note}_${RUN_TAG}.log
  start=$(date '+%F %T')
  log_status "STAGE_START layer=$layer stage=$stage buffer=$buffer runner=$runner note=$note time=$start"
  run_with_watchdog "$log_file" "$PY" "${args[@]}"
  rc=$?
  end=$(date '+%F %T')
  printf '%s\n' "instructblip-vicuna-7b,$layer,$stage,$buffer,$rc,$start,$end,$log_file,$note" >>"$CSV"
  log_status "STAGE_END layer=$layer stage=$stage buffer=$buffer rc=$rc note=$note time=$end"
  return "$rc"
}

validate_layer_complete() {
  local layer="$1" layer_dir result_file eval_samples
  layer_dir=$(printf '%s/layer_%02d' "$OUT" "$layer")
  result_file=$(find "$layer_dir" -type f -name results.json -size +0c -print -quit 2>/dev/null)
  eval_samples=$("$PY" - "$layer_dir/eval_full.done" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        print(json.load(f).get('eval_samples', -1))
except Exception:
    print(-1)
PY
)
  [[ -s "$layer_dir/train.done" && -s "$layer_dir/selected_checkpoint.tsv" && \
     -s "$layer_dir/eval_full.done" && -n "$result_file" && "$eval_samples" == 954 ]]
}

run_fresh_layer() {
  local layer="$1" layer_dir archive
  layer_dir=$(printf '%s/layer_%02d' "$OUT" "$layer")
  if validate_layer_complete "$layer"; then
    log_status "LAYER_SKIP layer=$layer reason=already_complete time=$(date '+%F %T')"
    return 0
  fi
  if ! run_stage "$layer" train 4 "$RUNNER" fresh_buffer4; then
    if grep -Eqi 'CUDA out of memory|torch\.cuda\.OutOfMemoryError' "$OUT"/train_L${layer}_fresh_buffer4_${RUN_TAG}.log; then
      archive=${layer_dir}_failed_buffer4_$(date +%Y%m%d_%H%M%S)
      if [[ -d "$layer_dir" ]]; then mv "$layer_dir" "$archive"; fi
      log_status "BUFFER_FALLBACK layer=$layer archive=$archive from=4 to=1 time=$(date '+%F %T')"
      run_stage "$layer" train 1 "$RUNNER" retry_buffer1 || return 1
    else
      return 1
    fi
  fi
  run_stage "$layer" eval 1 "$RUNNER" full_eval || return 1
  validate_layer_complete "$layer"
}

log_status "QUEUE_START job=3044841 host=$(hostname) physical_gpu=$PHYSICAL_GPU_ID logical_gpu=$GPU_ID time=$(date '+%F %T')"
log_status "RESUME_LAYER=1 RESUME_CKPT=$RESUME_CKPT next_epoch=46 next_i=14311 buffer=1"
log_status "MEMORY_FIX=expandable_segments+synchronous_no_prefetch+post_resume_empty_cache+activation_checkpointing"
log_status "FOLLOWUP_QUEUE=23,24,22,25"
log_status "TRAIN_JSON=$TRAIN_JSON"
log_status "EVAL_JSON=$EVAL_JSON expected_eval_samples=954"

for required in "$PY" "$PROJ/$RUNNER" "$PROJ/$RESUME_RUNNER" "$CONFIG" "$TRAIN_JSON" "$EVAL_JSON" "$IMG_ROOT" "$RESUME_CKPT"; do
  if [[ ! -e "$required" ]]; then
    log_status "PRECHECK_FAILED missing=$required time=$(date '+%F %T')"
    exit 2
  fi
done

run_stage 1 train 1 "$RESUME_RUNNER" resume_epoch45 \
  --resume-checkpoint "$RESUME_CKPT" --resume-layer 1 \
  --synchronous-data-loading --activation-checkpointing || exit 11
run_stage 1 eval 1 "$RUNNER" full_eval || exit 12
if ! validate_layer_complete 1; then
  log_status "QUEUE_STOP layer=1 reason=missing_or_incomplete_eval_artifacts time=$(date '+%F %T')"
  exit 13
fi
log_status "LAYER_COMPLETE layer=1 mode=resume eval_samples=954 time=$(date '+%F %T')"

for layer in 23 24 22 25; do
  if ! run_fresh_layer "$layer"; then
    log_status "QUEUE_STOP layer=$layer reason=train_or_eval_failed time=$(date '+%F %T')"
    exit 20
  fi
  log_status "LAYER_COMPLETE layer=$layer mode=fresh eval_samples=954 time=$(date '+%F %T')"
done

log_status "QUEUE_COMPLETE time=$(date '+%F %T')"
