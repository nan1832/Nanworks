#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PALIGEMMA_STABLE_MAX_EMA=${PALIGEMMA_STABLE_MAX_EMA:-100.0}
export PALIGEMMA_STABLE_SKIP_NONFINITE_STEP=1

PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py
STABLE_CONFIG=configs/vead/paligemma-3b-stable.yaml
L0_STABLE_CONFIG=configs/vead/paligemma-3b-stable-l0.yaml
STALL_TIMEOUT_SECONDS=7200
SERVER_RESULTS=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
VIS_ROOT=$SERVER_RESULTS/mmke_visual_top3_union_train_eval_7models_20260613_014644
MODEL_ROOT=$SERVER_RESULTS/paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b
MMKE_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
TRAIN_JSON=$VIS_ROOT/data/vqa_mmke_visual_train_evqa_compat.json
EVAL_JSON=$VIS_ROOT/data/vqa_mmke_visual_eval_evqa_compat.json
RUN_TAG=$(date +%Y%m%d_%H%M%S)
CONTROL=$SERVER_RESULTS/paligemma_visual_stable_repair_5_1_0_job3044208_$RUN_TAG
STATUS=$CONTROL/status.log
CSV=$CONTROL/layer_status.csv
mkdir -p "$CONTROL" "$MODEL_ROOT"
echo "layer,config,train_rc,eval_rc,start_time,end_time,train_log,eval_log,note" > "$CSV"
echo "REPAIR_START layers=5,1,0 stall_timeout=$STALL_TIMEOUT_SECONDS time=$(date)" | tee -a "$STATUS"

run_with_stall_timeout() {
  local log_file="$1" event="$2"
  shift 2
  local pid now mtime stale_seconds rc
  LAST_RUN_STALLED=0
  "$@" >> "$log_file" 2>&1 &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
    now=$(date +%s)
    mtime=$(stat -c %Y "$log_file" 2>/dev/null || echo "$now")
    stale_seconds=$((now - mtime))
    if [[ "$stale_seconds" -ge "$STALL_TIMEOUT_SECONDS" ]]; then
      LAST_RUN_STALLED=1
      echo "${event^^}_STALLED pid=$pid stale_seconds=$stale_seconds layer=$CURRENT_LAYER time=$(date)" | tee -a "$STATUS"
      kill -TERM "$pid" 2>/dev/null || true
      sleep 20
      kill -KILL "$pid" 2>/dev/null || true
      break
    fi
  done
  wait "$pid"
  rc=$?
  return "$rc"
}

archive_incomplete() {
  local layer="$1" dir archive
  dir="$MODEL_ROOT/layer_$(printf '%02d' "$layer")"
  if [[ -d "$dir" && ! -f "$dir/eval_full.done" ]]; then
    archive="$MODEL_ROOT/failed_or_incomplete_mmke-visual_stable_L${layer}_$RUN_TAG"
    rm -rf -- "$archive"
    mv -- "$dir" "$archive"
    echo "ARCHIVE_INCOMPLETE layer=$layer to=$archive time=$(date)" | tee -a "$STATUS"
  fi
}

run_repair_layer() {
  local layer="$1" config="$2"
  local train_log eval_log selected start_time end_time train_rc eval_rc note
  CURRENT_LAYER=$layer
  if [[ "$layer" -eq 0 ]]; then
    export PALIGEMMA_STABLE_GRAD_CLIP_NORM=0.5
  else
    export PALIGEMMA_STABLE_GRAD_CLIP_NORM=1.0
  fi
  archive_incomplete "$layer"
  train_log="$MODEL_ROOT/train_L${layer}_stable_repair_$RUN_TAG.log"
  eval_log="$MODEL_ROOT/eval_L${layer}_stable_repair_$RUN_TAG.log"
  selected="$MODEL_ROOT/layer_$(printf '%02d' "$layer")/selected_checkpoint.tsv"
  start_time=$(date '+%F %T')
  train_rc=777; eval_rc=777; note=""
  echo "TRAIN_START layer=$layer config=$config stall_timeout=$STALL_TIMEOUT_SECONDS time=$(date)" | tee -a "$STATUS"
  echo "ENV layer=$layer config=$config train_json=$TRAIN_JSON eval_json=$EVAL_JSON time=$(date)" > "$train_log"
  run_with_stall_timeout "$train_log" train \
    "$PY" "$RUNNER" \
      --out-root "$MODEL_ROOT" --layers "$layer" --epochs 50 --batch-size 2 \
      --model-name paligemma-3b \
      --train-data "$TRAIN_JSON" --train-img-root "$MMKE_IMG" \
      --eval-data "$EVAL_JSON" --eval-img-root "$MMKE_IMG" \
      --config-path "$config" --skip-eval --overwrite-train
  train_rc=$?
  [[ "$LAST_RUN_STALLED" -eq 0 ]] || note="train_stalled_${STALL_TIMEOUT_SECONDS}s"
  echo "TRAIN_END layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"
  if [[ "$train_rc" -eq 0 && -s "$selected" ]]; then
    echo "EVAL_START layer=$layer eval_json=$EVAL_JSON time=$(date)" | tee -a "$STATUS"
    echo "ENV layer=$layer config=$config train_json=$TRAIN_JSON eval_json=$EVAL_JSON time=$(date)" > "$eval_log"
    run_with_stall_timeout "$eval_log" eval \
      "$PY" "$RUNNER" \
        --out-root "$MODEL_ROOT" --layers "$layer" --epochs 50 --batch-size 2 \
        --model-name paligemma-3b \
        --train-data "$TRAIN_JSON" --train-img-root "$MMKE_IMG" \
        --eval-data "$EVAL_JSON" --eval-img-root "$MMKE_IMG" \
        --config-path "$config" --skip-train --overwrite-eval
    eval_rc=$?
    [[ "$LAST_RUN_STALLED" -eq 0 ]] || note="$note;eval_stalled_${STALL_TIMEOUT_SECONDS}s"
    echo "EVAL_END layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
  else
    note="$note;eval_not_run_no_checkpoint_or_train_failed"
    echo "EVAL_NOT_RUN layer=$layer train_rc=$train_rc selected_exists=$([[ -s "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
  fi
  end_time=$(date '+%F %T')
  echo "$layer,$config,$train_rc,$eval_rc,$start_time,$end_time,$train_log,$eval_log,$note" >> "$CSV"
}

run_repair_layer 5 "$STABLE_CONFIG"
run_repair_layer 1 "$STABLE_CONFIG"
run_repair_layer 0 "$L0_STABLE_CONFIG"
echo "REPAIR_DONE time=$(date)" | tee -a "$STATUS"
