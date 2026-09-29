#!/usr/bin/env bash
set -uo pipefail

ROLE=${1:?usage: launch_formal_top3_stage2_20260812.sh job3126082|job3150065}
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
SHARED_RUNNER=scripts/run_mmke_llava_shared_gpu_sweep.py
INSTRUCT_RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep_resume.py
GPU_ID=0
EPOCHS=50
BATCH_SIZE=2
SEED=20260601
EMA_ALPHA=0.1
STALL_SECONDS=7200
POLL_SECONDS=60
GPU_IDLE_MAX_MIB=512

EVQA_TRAIN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
EVQA_TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
EVQA_EVAL=$PROJ/data/easy-edit-mm/vqa/vqa_eval.json
EVQA_EVAL_IMG=$PROJ/data/easy-edit-mm/images
ENT_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data
ENT_TRAIN=$ENT_DATA/vqa_mmke_entity_train_evqa_compat.json
ENT_EVAL=$ENT_DATA/vqa_mmke_entity_eval_evqa_compat.json
MMKE_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image

case "$ROLE" in
  job3126082)
    EXPECTED_JOB=3126082
    RUN_ROOT=/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812
    SHARED_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082
    ;;
  job3150065)
    EXPECTED_JOB=3150065
    RUN_ROOT=/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812
    SHARED_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065
    ;;
  *)
    printf 'unknown role: %s\n' "$ROLE" >&2
    exit 2
    ;;
esac

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
  [[ -s "$d/train.done" && -s "$d/selected_checkpoint.tsv" && -s "$d/eval_full.done" ]] || return 1
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

wait_gpu_clean() {
  local stable=0 used
  while (( stable < 3 )); do
    used=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -dc '0-9')
    used=${used:-999999}
    if (( used <= GPU_IDLE_MAX_MIB )); then
      stable=$((stable+1))
    else
      stable=0
    fi
    log_status "GPU_CLEAN_PROBE used_mib=$used stable=$stable/3 time=$(date '+%F %T %Z')"
    (( stable >= 3 )) || sleep 20
  done
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
  local d=$1 selected selected_abs d_abs parent item item_abs removed=0 bytes=0 item_bytes
  complete_exists "$d" || return 1
  selected=$(selected_path "$d/selected_checkpoint.tsv") || return 1
  selected_abs=$(realpath -e "$selected") || return 1
  d_abs=$(realpath -e "$d") || return 1
  case "$selected_abs" in "$d_abs"/*) ;; *) log_status "CLEANUP_REFUSED reason=selected_outside_layer layer_dir=$d_abs selected=$selected_abs"; return 2 ;; esac
  parent=$(dirname "$selected_abs")
  case "$parent" in "$d_abs"/*/checkpoints) ;; *) log_status "CLEANUP_REFUSED reason=unexpected_checkpoint_parent parent=$parent selected=$selected_abs"; return 2 ;; esac
  for item in "$parent"/*; do
    [[ -e "$item" ]] || continue
    item_abs=$(realpath -e "$item") || continue
    [[ "$item_abs" == "$selected_abs" ]] && continue
    item_bytes=$(du -sb "$item_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$item_abs"
    removed=$((removed+1))
    bytes=$((bytes+${item_bytes:-0}))
  done
  log_status "CHECKPOINT_CLEANUP layer_dir=$d selected=$selected_abs removed=$removed bytes=$bytes time=$(date '+%F %T %Z')"
}

latest_resume_checkpoint() {
  local layer_dir=$1
  "$PY" - "$layer_dir/loss_history.csv" <<'PY'
import csv
import math
import sys
from pathlib import Path

p = Path(sys.argv[1])
best = None
if p.is_file():
    for row in csv.DictReader(p.open(encoding="utf-8")):
        try:
            ckpt = Path(row["ckpt_path"])
            i = int(row["i"])
            if ckpt.is_file() and math.isfinite(float(row["ema_loss"])):
                if best is None or i > best[0]:
                    best = (i, ckpt)
        except Exception:
            pass
if best:
    print(best[1])
PY
}

run_stage() {
  local dataset=$1 model=$2 layer=$3 stage=$4 runner=$5 config=$6 train_json=$7 train_img=$8 eval_json=$9 eval_img=${10} lowmem=${11} shared_model=${12}
  local out=$RUN_ROOT/$dataset/$model log=$RUN_ROOT/logs/${dataset}_${model}_L${layer}_${stage}_${TAG}.log
  local start end rc layer_dir resume_ckpt
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
    --train-img-root "$train_img"
    --eval-data "$eval_json"
    --eval-img-root "$eval_img"
    --config-path "$config"
    --seed "$SEED"
    --ema-alpha "$EMA_ALPHA"
    --data-buffer-size 1
    --keep-top-ckpts 1
    --keep-last-ckpts 0
  )
  if [[ "$lowmem" == 1 ]]; then
    args+=(--synchronous-data-loading --activation-checkpointing)
  fi
  if [[ "$shared_model" == 1 ]]; then
    args+=(--data-proc-device cuda:0 --share-data-proc-vllm)
  fi
  if [[ "$stage" == train ]]; then
    layer_dir=$out/layer_$(printf '%02d' "$layer")
    resume_ckpt=$(latest_resume_checkpoint "$layer_dir" 2>/dev/null || true)
    if [[ -n "$resume_ckpt" ]]; then
      args+=(--resume-checkpoint "$resume_ckpt" --resume-layer "$layer")
      log_status "RESUME_SELECTED dataset=$dataset model=$model layer=$layer checkpoint=$resume_ckpt"
    fi
    args+=(--skip-eval)
  else
    args+=(--skip-train)
  fi

  wait_gpu_clean
  start=$(date '+%F %T')
  log_status "STAGE_START dataset=$dataset model=$model layer=$layer stage=$stage runner=$runner config=$config train=$train_json eval=$eval_json lowmem=$lowmem shared_model=$shared_model time=$start"
  run_watched "$dataset" "$model" "$layer" "$stage" "$log" "${args[@]}"
  rc=$?
  end=$(date '+%F %T')
  printf '%s\n' "$dataset,$model,$layer,$stage,$rc,$start,$end,$log," >>"$CSV"
  log_status "STAGE_END dataset=$dataset model=$model layer=$layer stage=$stage rc=$rc time=$end"
  return "$rc"
}

run_layer() {
  local dataset=$1 model=$2 layer=$3 runner=$4 config=$5 train_json=$6 train_img=$7 eval_json=$8 eval_img=$9 lowmem=${10} shared_model=${11}
  local out=$RUN_ROOT/$dataset/$model d ll train_rc=777 eval_rc=777 note=''
  ll=$(printf '%02d' "$layer")
  d=$out/layer_$ll
  mkdir -p "$out"

  log_status "LAYER_BEGIN dataset=$dataset model=$model layer=$layer time=$(date '+%F %T %Z')"
  if [[ -s "$d/train.done" ]] && selected_exists "$d/selected_checkpoint.tsv"; then
    train_rc=0
    note=skip_existing_train
    log_status "TRAIN_SKIP dataset=$dataset model=$model layer=$layer reason=existing_selected"
  else
    run_stage "$dataset" "$model" "$layer" train "$runner" "$config" "$train_json" "$train_img" "$eval_json" "$eval_img" "$lowmem" "$shared_model"
    train_rc=$?
  fi

  if [[ "$train_rc" -eq 0 ]] && selected_exists "$d/selected_checkpoint.tsv"; then
    if [[ -s "$d/eval_full.done" ]] && find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null | grep -q .; then
      eval_rc=0
      note=${note:+$note;}'skip_existing_eval'
      log_status "EVAL_SKIP dataset=$dataset model=$model layer=$layer reason=existing_eval"
    else
      run_stage "$dataset" "$model" "$layer" eval "$runner" "$config" "$train_json" "$train_img" "$eval_json" "$eval_img" "$lowmem" "$shared_model"
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

combo_complete() {
  local dataset=$1 model=$2 layers_csv=$3 layer
  IFS=',' read -r -a layers <<<"$layers_csv"
  for layer in "${layers[@]}"; do
    complete_exists "$RUN_ROOT/$dataset/$model/layer_$(printf '%02d' "$layer")" || return 1
  done
}

run_combo() {
  local dataset=$1 model=$2 layers_csv=$3 runner=$4 config=$5 train_json=$6 train_img=$7 eval_json=$8 eval_img=$9 lowmem=${10} shared_model=${11}
  local layer
  log_status "COMBO_START dataset=$dataset model=$model layers=$layers_csv time=$(date '+%F %T %Z')"
  IFS=',' read -r -a layers <<<"$layers_csv"
  for layer in "${layers[@]}"; do
    run_layer "$dataset" "$model" "$layer" "$runner" "$config" "$train_json" "$train_img" "$eval_json" "$eval_img" "$lowmem" "$shared_model"
  done
  if combo_complete "$dataset" "$model" "$layers_csv"; then
    touch "$RUN_ROOT/$dataset/$model/COMBO_DONE"
    log_status "COMBO_DONE dataset=$dataset model=$model time=$(date '+%F %T %Z')"
  else
    touch "$RUN_ROOT/$dataset/$model/COMBO_FINISHED_WITH_FAILURES"
    log_status "COMBO_FINISHED_WITH_FAILURES dataset=$dataset model=$model time=$(date '+%F %T %Z')"
  fi
}

if [[ ${SLURM_JOB_ID:-unset} != "$EXPECTED_JOB" ]]; then
  if [[ ${ALLOW_REPLACEMENT_JOB:-0} == 1 && ${SLURM_JOB_ID:-unset} != unset ]]; then
    log_status "REPLACEMENT_JOB_ACCEPTED original_job=$EXPECTED_JOB actual_job=$SLURM_JOB_ID reason=resume_after_allocation_loss time=$(date '+%F %T %Z')"
  else
    log_status "PRECHECK_FAILED expected_job=$EXPECTED_JOB actual_job=${SLURM_JOB_ID:-unset} allow_replacement=${ALLOW_REPLACEMENT_JOB:-0}"
    exit 2
  fi
fi

for required in "$PY" "$PROJ/$SHARED_RUNNER" "$PROJ/$INSTRUCT_RUNNER" "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" "$ENT_TRAIN" "$ENT_EVAL" "$MMKE_IMG" \
  configs/vead/minigpt-4-vicuna-7b.yaml configs/vead/llava-v1.5-7b.yaml configs/vead/instructblip-vicuna-7b.yaml; do
  if [[ ! -e "$required" ]]; then
    log_status "PRECHECK_FAILED missing=$required time=$(date '+%F %T %Z')"
    exit 2
  fi
done

log_status "QUEUE_START role=$ROLE job=${SLURM_JOB_ID:-unset} host=$(hostname) gpu=$GPU_ID root=$RUN_ROOT shared=$SHARED_ROOT time=$(date '+%F %T %Z')"
log_status "COMPARABILITY epochs=$EPOCHS batch_size=$BATCH_SIZE seed=$SEED ema_alpha=$EMA_ALPHA selection=min_finite_ema eval=independent_test_or_eval data_buffer=1"
log_status "RETENTION keep_selected=1 keep_last=0 cleanup_after_verified_eval=1"
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS"

case "$ROLE" in
  job3126082)
    run_combo evqa-pilot500 minigpt-4-vicuna-7b '15,14,8,9,10,29,22,0,1,2,19,7' "$SHARED_RUNNER" configs/vead/minigpt-4-vicuna-7b.yaml "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 1 1
    run_combo mmke-entity llava-v1.5-7b '15,16,14,28,27,26,23,22,24,1,9,7,0,2,13,11,12' "$SHARED_RUNNER" configs/vead/llava-v1.5-7b.yaml "$ENT_TRAIN" "$MMKE_IMG" "$ENT_EVAL" "$MMKE_IMG" 1 1
    ;;
  job3150065)
    run_combo evqa-pilot500 instructblip-vicuna-7b '15,16,14,0,18,19,2,1,3,4,11,25' "$INSTRUCT_RUNNER" configs/vead/instructblip-vicuna-7b.yaml "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 1 0
    run_combo evqa-pilot500 llava-v1.5-7b '15,16,14,7,6,5,24,25,0,1,2,4' "$SHARED_RUNNER" configs/vead/llava-v1.5-7b.yaml "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 1 1
    ;;
esac

all_ok=1
case "$ROLE" in
  job3126082)
    combo_complete evqa-pilot500 minigpt-4-vicuna-7b '15,14,8,9,10,29,22,0,1,2,19,7' || all_ok=0
    combo_complete mmke-entity llava-v1.5-7b '15,16,14,28,27,26,23,22,24,1,9,7,0,2,13,11,12' || all_ok=0
    ;;
  job3150065)
    combo_complete evqa-pilot500 instructblip-vicuna-7b '15,16,14,0,18,19,2,1,3,4,11,25' || all_ok=0
    combo_complete evqa-pilot500 llava-v1.5-7b '15,16,14,7,6,5,24,25,0,1,2,4' || all_ok=0
    ;;
esac

if [[ "$all_ok" -eq 1 ]]; then
  touch "$RUN_ROOT/QUEUE_DONE"
  log_status "QUEUE_DONE time=$(date '+%F %T %Z')"
else
  touch "$RUN_ROOT/QUEUE_FINISHED_WITH_FAILURES"
  log_status "QUEUE_FINISHED_WITH_FAILURES time=$(date '+%F %T %Z')"
fi
