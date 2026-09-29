#!/usr/bin/env bash
set -uo pipefail

PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
LOCAL_ROOT="${LOCAL_ROOT:-/tmp/ph_teacher3/evqa_pilot500_smol_qwen_job3044208_20260723_202500}"
PY_SMOL=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
PY_QWEN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
GPU_ID=0
GPU_MIN_FREE_MIB=50000
STALL_SECONDS=7200
POLL_SECONDS=60
EPOCHS=50
BATCH_SIZE=2
DATA_BUFFER_SIZE=4
SEED=20260601
EMA_ALPHA=0.1
KEEP_TOP=5
KEEP_LAST=2

TRAIN_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
EVAL_JSON="$PROJ/data/easy-edit-mm/vqa/vqa_eval.json"
EVAL_IMG="$PROJ/data/easy-edit-mm/images"

# Source of truth: 6location_7model_3datas_top_3_5_layers_outcome.md
# Section 3.1 gives the 8-method Top-3 union; section 3.4.1 subtracts
# layers already carrying a selected checkpoint and eval_full.done.
SMOL_FULL_UNION="11,12,10,17,16,15,9,8,7,22,21,20,1,2,0,3,14,13"
SMOL_ALREADY_DONE="12,17,16,15,22,21,14,13"
SMOL_PENDING="11,10,9,8,7,20,1,2,0,3"
QWEN_FULL_UNION="17,18,16,29,28,27,11,14,12,2,30,1,0,3,34,24,21,22,20,19"
QWEN_ALREADY_DONE="18,29,28,27,20,19"
QWEN_PENDING="17,16,11,14,12,2,30,1,0,3,34,24,21,22"

STATUS="$LOCAL_ROOT/status.log"
CSV="$LOCAL_ROOT/layer_status.csv"
LOCK="$LOCAL_ROOT/launcher.lock"
RUN_TAG="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$LOCAL_ROOT"
cd "$PROJ" || exit 1
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"

exec 9>"$LOCK"
if ! flock -n 9; then
  printf '%s\n' "ALREADY_RUNNING time=$(date '+%F %T')" >>"$STATUS"
  exit 3
fi

if [[ ! -s "$CSV" ]]; then
  printf '%s\n' "model,layer,stage,rc,start_time,end_time,log,note" >"$CSV"
fi

log_status() {
  printf '%s\n' "$*" | tee -a "$STATUS"
}

gpu_snapshot() {
  nvidia-smi -i "$GPU_ID" \
    --query-gpu=index,name,memory.used,memory.free,memory.total,utilization.gpu \
    --format=csv,noheader,nounits 2>/dev/null || true
}

wait_gpu_free() {
  local py="$1"
  while true; do
    local free cuda_ok
    free="$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -dc '0-9')"
    free="${free:-0}"
    cuda_ok=0
    if [[ "$free" -ge "$GPU_MIN_FREE_MIB" ]]; then
      if CUDA_VISIBLE_DEVICES="$GPU_ID" "$py" - <<'PY' >"$LOCAL_ROOT/cuda_probe.log" 2>&1
import torch
assert torch.cuda.is_available()
assert torch.cuda.device_count() == 1
torch.cuda.init()
PY
      then
        cuda_ok=1
      fi
    fi
    if [[ "$free" -ge "$GPU_MIN_FREE_MIB" && "$cuda_ok" -eq 1 ]]; then
      log_status "GPU_READY free_mib=$free cuda_ok=$cuda_ok time=$(date '+%F %T')"
      return 0
    fi
    log_status "WAIT_GPU free_mib=$free min_free_mib=$GPU_MIN_FREE_MIB cuda_ok=$cuda_ok time=$(date '+%F %T')"
    sleep 180
  done
}

run_with_watchdog() {
  local log_file="$1"
  shift
  local pid now last_progress signature new_signature rc
  : >"$log_file"
  setsid env CUDA_VISIBLE_DEVICES="$GPU_ID" "$@" >>"$log_file" 2>&1 &
  pid=$!
  now="$(date +%s)"
  last_progress="$now"
  signature="$(stat -c '%s:%Y' "$log_file" 2>/dev/null || echo 0:0)"
  log_status "PROCESS_START pid=$pid pgid=$pid log=$log_file time=$(date '+%F %T')"

  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL_SECONDS"
    new_signature="$(stat -c '%s:%Y' "$log_file" 2>/dev/null || echo 0:0)"
    now="$(date +%s)"
    if [[ "$new_signature" != "$signature" ]]; then
      signature="$new_signature"
      last_progress="$now"
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

runner_args() {
  local out="$1" layer="$2" model_name="$3" config="$4"
  printf '%s\0' \
    "$RUNNER" --out-root "$out" --layers "$layer" \
    --epochs "$EPOCHS" --batch-size "$BATCH_SIZE" \
    --model-name "$model_name" --device cuda:0 \
    --train-data "$TRAIN_JSON" --train-img-root "$TRAIN_IMG" \
    --eval-data "$EVAL_JSON" --eval-img-root "$EVAL_IMG" \
    --config-path "$config" --seed "$SEED" --ema-alpha "$EMA_ALPHA" \
    --data-buffer-size "$DATA_BUFFER_SIZE" \
    --keep-top-ckpts "$KEEP_TOP" --keep-last-ckpts "$KEEP_LAST"
}

run_stage() {
  local py="$1" out="$2" layer="$3" model_name="$4" config="$5" stage="$6" model_key="$7"
  local start end rc stage_log
  local -a args
  stage_log="$out/${stage}_L${layer}_${RUN_TAG}.log"
  mapfile -d '' -t args < <(runner_args "$out" "$layer" "$model_name" "$config")
  if [[ "$stage" == train ]]; then args+=(--skip-eval); else args+=(--skip-train); fi
  wait_gpu_free "$py"
  start="$(date '+%F %T')"
  log_status "STAGE_START model=$model_key layer=$layer stage=$stage py=$py out=$out time=$start"
  run_with_watchdog "$stage_log" "$py" "${args[@]}"
  rc=$?
  end="$(date '+%F %T')"
  printf '%s\n' "$model_key,$layer,$stage,$rc,$start,$end,$stage_log," >>"$CSV"
  log_status "STAGE_END model=$model_key layer=$layer stage=$stage rc=$rc time=$end"
  return "$rc"
}

run_layer() {
  local py="$1" model_key="$2" model_name="$3" layer="$4" config="$5"
  local out="$LOCAL_ROOT/$model_key" layer_dir result_file
  layer_dir="$(printf '%s/layer_%02d' "$out" "$layer")"
  mkdir -p "$out"

  if [[ -s "$layer_dir/train.done" && -s "$layer_dir/selected_checkpoint.tsv" ]]; then
    log_status "TRAIN_SKIP model=$model_key layer=$layer reason=existing_selected time=$(date '+%F %T')"
  elif ! run_stage "$py" "$out" "$layer" "$model_name" "$config" train "$model_key"; then
    log_status "QUEUE_STOP model=$model_key layer=$layer reason=train_failed time=$(date '+%F %T')"
    return 1
  fi

  if [[ -s "$layer_dir/eval_full.done" ]]; then
    log_status "EVAL_SKIP model=$model_key layer=$layer reason=existing_eval time=$(date '+%F %T')"
  elif ! run_stage "$py" "$out" "$layer" "$model_name" "$config" eval "$model_key"; then
    log_status "QUEUE_STOP model=$model_key layer=$layer reason=eval_failed time=$(date '+%F %T')"
    return 1
  fi

  result_file="$(find "$layer_dir" -type f -name results.json -size +0c -print -quit 2>/dev/null)"
  if [[ ! -s "$layer_dir/selected_checkpoint.tsv" || ! -s "$layer_dir/eval_full.done" || -z "$result_file" ]]; then
    log_status "QUEUE_STOP model=$model_key layer=$layer reason=missing_completion_artifact time=$(date '+%F %T')"
    return 1
  fi
  log_status "LAYER_COMPLETE model=$model_key layer=$layer results=$result_file time=$(date '+%F %T')"
}

run_model_layers() {
  local py="$1" model_key="$2" model_name="$3" config="$4" layers_csv="$5" layer
  local -a layers
  IFS=',' read -ra layers <<<"$layers_csv"
  for layer in "${layers[@]}"; do
    run_layer "$py" "$model_key" "$model_name" "$layer" "$config" || return 1
  done
}

validate_layer_lists() {
  "$PY_SMOL" - "$SMOL_FULL_UNION" "$SMOL_ALREADY_DONE" "$SMOL_PENDING" \
    "$QWEN_FULL_UNION" "$QWEN_ALREADY_DONE" "$QWEN_PENDING" <<'PY'
import sys
def parse(s): return [int(x) for x in s.split(',') if x]
sf, sd, sp, qf, qd, qp = map(parse, sys.argv[1:])
assert len(sf) == len(set(sf)) == 18
assert len(qf) == len(set(qf)) == 20
assert len(sp) == len(set(sp)) == 10
assert len(qp) == len(set(qp)) == 14
assert set(sd).isdisjoint(sp) and set(sd) | set(sp) == set(sf)
assert set(qd).isdisjoint(qp) and set(qd) | set(qp) == set(qf)
assert all(0 <= x < 24 for x in sf)
assert all(0 <= x < 36 for x in qf)
print('candidate layer validation passed')
PY
}

log_status "QUEUE_START dataset=EVQA-pilot500 host=$(hostname) job=3044208 gpu=$GPU_ID local_root=$LOCAL_ROOT time=$(date '+%F %T')"
log_status "PROTECTED_GPU0_KERNELS=31810,509297,1444616,1445110,3012083,3302549 action=preserve"
log_status "CANDIDATE_SOURCE=section_3.1_union_minus_section_4_completed"
log_status "SMOL_FULL_UNION=$SMOL_FULL_UNION"
log_status "SMOL_ALREADY_DONE=$SMOL_ALREADY_DONE"
log_status "SMOL_PENDING=$SMOL_PENDING"
log_status "QWEN_FULL_UNION=$QWEN_FULL_UNION"
log_status "QWEN_ALREADY_DONE=$QWEN_ALREADY_DONE"
log_status "QWEN_PENDING=$QWEN_PENDING"
log_status "TRAIN_JSON=$TRAIN_JSON TRAIN_IMG=$TRAIN_IMG"
log_status "EVAL_JSON=$EVAL_JSON EVAL_IMG=$EVAL_IMG"
gpu_snapshot | tee -a "$STATUS"

for required in "$PY_SMOL" "$PY_QWEN" "$TRAIN_JSON" "$TRAIN_IMG" "$EVAL_JSON" "$EVAL_IMG"; do
  if [[ ! -e "$required" ]]; then
    log_status "PRECHECK_FAILED missing=$required time=$(date '+%F %T')"
    exit 2
  fi
done

if ! validate_layer_lists >>"$STATUS" 2>&1; then
  log_status "PRECHECK_FAILED reason=candidate_layer_validation time=$(date '+%F %T')"
  exit 2
fi

if ! "$PY_SMOL" - "$TRAIN_JSON" "$EVAL_JSON" <<'PY' >>"$STATUS" 2>&1
import json, sys
train = json.load(open(sys.argv[1]))
test = json.load(open(sys.argv[2]))
assert len(train) == 500, len(train)
assert len(test) == 2093, len(test)
print(f'dataset validation passed train={len(train)} eval={len(test)}')
PY
then
  log_status "PRECHECK_FAILED reason=dataset_count_validation time=$(date '+%F %T')"
  exit 2
fi

run_model_layers \
  "$PY_SMOL" smolvlm-1.7b smolvlm-1.7b configs/vead/smolvlm-1.7b.yaml \
  "$SMOL_PENDING" || exit 10

run_model_layers \
  "$PY_QWEN" qwen2.5-vl-3b qwen2.5-vl-3b-instruct \
  configs/vead/qwen2.5-vl-3b-instruct.yaml \
  "$QWEN_PENDING" || exit 20

log_status "QUEUE_COMPLETE dataset=EVQA-pilot500 time=$(date '+%F %T')"
