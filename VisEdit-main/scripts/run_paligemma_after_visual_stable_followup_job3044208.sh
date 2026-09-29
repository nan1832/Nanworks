#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PALIGEMMA_STABLE_MAX_EMA=${PALIGEMMA_STABLE_MAX_EMA:-100.0}
export PALIGEMMA_STABLE_GRAD_CLIP_NORM=${PALIGEMMA_STABLE_GRAD_CLIP_NORM:-1.0}
export PALIGEMMA_STABLE_SKIP_NONFINITE_STEP=${PALIGEMMA_STABLE_SKIP_NONFINITE_STEP:-1}

GPU_ID=0
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
MAIN_SCRIPT=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
STABLE_SCRIPT=scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py
MAIN_CONFIG=configs/vead/paligemma-3b.yaml
STABLE_CONFIG=configs/vead/paligemma-3b-stable.yaml
EPOCHS=50
BATCH_SIZE=2
STALL_TIMEOUT_SECONDS=7200
GPU_WAIT_MAX_USED_MIB=${GPU_WAIT_MAX_USED_MIB:-65000}

SERVER_RESULTS=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
OUTPUT_BASE=${PALIGEMMA_FOLLOWUP_OUTPUT_BASE:-$SERVER_RESULTS}
CURRENT_VISUAL_CONTROL=$SERVER_RESULTS/paligemma_visual_stable_all8_completion_job3044208_20260714_210005
CURRENT_VISUAL_STATUS=$CURRENT_VISUAL_CONTROL/status.log
CURRENT_VISUAL_REPAIR_STATUS=$SERVER_RESULTS/paligemma_visual_stable_repair_5_1_0_job3044208_20260715_090123/status.log
CURRENT_VISUAL_MODEL_ROOT=$SERVER_RESULTS/paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b
ENTITY_DATA_ROOT=$SERVER_RESULTS/mmke_entity_top3_union_train_eval_7models_20260616_155000
RUN_TAG=$(date +%Y%m%d_%H%M%S)
PILOT_MAIN_ROOT=${PALIGEMMA_PILOT_MAIN_ROOT:-$OUTPUT_BASE/paligemma_main_evqa_pilot500_job3044208_$RUN_TAG}
ENTITY_MAIN_ROOT=${PALIGEMMA_ENTITY_MAIN_ROOT:-$OUTPUT_BASE/paligemma_main_mmke_entity_job3044208_$RUN_TAG}
PILOT_STABLE_ROOT=$OUTPUT_BASE/paligemma_stable_evqa_pilot500_pending_job3044208_$RUN_TAG
ENTITY_STABLE_ROOT=$OUTPUT_BASE/paligemma_stable_mmke_entity_pending_job3044208_$RUN_TAG
CONTROL_ROOT=$OUTPUT_BASE/paligemma_after_visual_stable_followup_job3044208_$RUN_TAG
STATUS=$CONTROL_ROOT/status.log
CSV=$CONTROL_ROOT/layer_status.csv
SUMMARY=$CONTROL_ROOT/summary.md
LOCK=$OUTPUT_BASE/paligemma_after_visual_stable_followup_job3044208.lock
mkdir -p "$OUTPUT_BASE" "$CONTROL_ROOT"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "FOLLOWUP_ALREADY_RUNNING time=$(date)" | tee -a "$STATUS"
  exit 3
fi

echo "dataset,mode,layer,train_rc,eval_rc,start_time,end_time,out_root,train_log,eval_log,note" > "$CSV"
{
  echo "# PaliGemma follow-up after MMKE-visual stable terminal states"
  echo
  echo "- Start: $(date '+%F %T')"
  echo "- GPU: job 3044208 / g09 / CUDA_VISIBLE_DEVICES=0"
  echo "- Output base: $OUTPUT_BASE"
  echo "- Phase order: pilot stable -> entity stable -> pilot main -> entity main"
  echo "- MMKE-visual gate: 7 evaluated layers plus recorded nonconvergent L0 failure"
  echo "- Stop rule: terminate only after ${STALL_TIMEOUT_SECONDS}s without log progress"
  echo "- Evaluation always uses the dataset eval/test JSON."
} > "$SUMMARY"
echo "FOLLOWUP_WAIT_START time=$(date) visual_control=$CURRENT_VISUAL_CONTROL" | tee -a "$STATUS"

layer_dir_name() { printf 'layer_%02d' "$1"; }

verify_visual_stable_all8() {
  local required_layers=(7 13 5 6 3 2 1)
  local done_count=0 l0_failed=0 layer dir
  for layer in "${required_layers[@]}"; do
    dir="$CURRENT_VISUAL_MODEL_ROOT/$(layer_dir_name "$layer")"
    if [[ -s "$dir/selected_checkpoint.tsv" && -f "$dir/eval_full.done" ]]; then
      done_count=$((done_count + 1))
    fi
  done
  if grep -q "TRAIN_END layer=0 rc=1" "$CURRENT_VISUAL_REPAIR_STATUS" 2>/dev/null \
    && grep -q "EVAL_NOT_RUN layer=0 train_rc=1 selected_exists=0" "$CURRENT_VISUAL_REPAIR_STATUS" 2>/dev/null; then
    l0_failed=1
  fi
  echo "VISUAL_STABLE_TERMINAL_VERIFY evaluated_count=$done_count required_evaluated=7 l0_failed=$l0_failed required_l0_failed=1 time=$(date)" | tee -a "$STATUS"
  [[ "$done_count" -eq 7 && "$l0_failed" -eq 1 ]]
}

wait_for_visual_stable_all8() {
  while true; do
    if grep -q "VISUAL_STABLE_ALL8_COMPLETION_DONE" "$CURRENT_VISUAL_STATUS" 2>/dev/null; then
      if verify_visual_stable_all8; then
        echo "VISUAL_STABLE_TERMINAL_STATES_CONFIRMED evaluated_layers=7 failed_layers=L0 time=$(date)" | tee -a "$STATUS"
        return 0
      fi
      echo "WAIT_VISUAL_TERMINAL_STATES evaluated_or_failure_record_missing time=$(date)" | tee -a "$STATUS"
    else
      echo "WAIT_VISUAL_STABLE_ALL8 marker=missing time=$(date)" | tee -a "$STATUS"
    fi
    sleep 180
  done
}

wait_gpu() {
  while true; do
    local used cuda_ok
    used=$(/usr/bin/nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')
    used=${used:-999999}
    cuda_ok=0
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" ]]; then
      if "$PY" - <<'PY' >/tmp/paligemma_after_visual_cuda_probe.log 2>&1
import torch
assert torch.cuda.is_available(), "cuda unavailable"
torch.cuda.init()
PY
      then
        cuda_ok=1
      fi
    fi
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" && "$cuda_ok" -eq 1 ]]; then
      echo "GPU_READY used_mib=$used max_mib=$GPU_WAIT_MAX_USED_MIB time=$(date)" | tee -a "$STATUS"
      return 0
    fi
    echo "WAIT_GPU used_mib=$used cuda_ok=$cuda_ok max_mib=$GPU_WAIT_MAX_USED_MIB time=$(date)" | tee -a "$STATUS"
    sleep 180
  done
}

has_eval_done() {
  local out="$1" layer="$2" dir
  dir="$out/$(layer_dir_name "$layer")"
  [[ -s "$dir/selected_checkpoint.tsv" && -f "$dir/eval_full.done" ]]
}

archive_incomplete() {
  local out="$1" dataset="$2" mode="$3" layer="$4" dir archive
  dir="$out/$(layer_dir_name "$layer")"
  if [[ -d "$dir" && ! -f "$dir/eval_full.done" ]]; then
    archive="$out/failed_or_incomplete_${dataset}_${mode}_L${layer}_$RUN_TAG"
    echo "ARCHIVE_INCOMPLETE dataset=$dataset mode=$mode layer=$layer from=$dir to=$archive time=$(date)" | tee -a "$STATUS"
    rm -rf -- "$archive"
    mv -- "$dir" "$archive"
  fi
}

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
      if [[ "$event" == "train" ]]; then
        echo "TRAIN_STALLED pid=$pid stale_seconds=$stale_seconds limit=$STALL_TIMEOUT_SECONDS time=$(date)" | tee -a "$STATUS"
      else
        echo "EVAL_STALLED pid=$pid stale_seconds=$stale_seconds limit=$STALL_TIMEOUT_SECONDS time=$(date)" | tee -a "$STATUS"
      fi
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

resolve_dataset() {
  local dataset="$1" mode="$2"
  local mmke_img=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
  case "$dataset" in
    evqa-pilot500)
      train_json=$SERVER_RESULTS/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
      train_img=$SERVER_RESULTS/evqa_proxy_train500_eval500_20260528/images
      eval_json=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
      eval_img=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
      if [[ "$mode" == "stable" ]]; then run_root="$PILOT_STABLE_ROOT"; else run_root="$PILOT_MAIN_ROOT"; fi
      ;;
    mmke-entity)
      train_json=$ENTITY_DATA_ROOT/data/vqa_mmke_entity_train_evqa_compat.json
      train_img=$mmke_img
      eval_json=$ENTITY_DATA_ROOT/data/vqa_mmke_entity_eval_evqa_compat.json
      eval_img=$mmke_img
      if [[ "$mode" == "stable" ]]; then run_root="$ENTITY_STABLE_ROOT"; else run_root="$ENTITY_MAIN_ROOT"; fi
      ;;
    *)
      echo "UNKNOWN_DATASET dataset=$dataset time=$(date)" | tee -a "$STATUS"
      return 2
      ;;
  esac
  [[ -s "$train_json" && -s "$eval_json" ]] || {
    echo "DATA_FILE_MISSING dataset=$dataset train_json=$train_json eval_json=$eval_json time=$(date)" | tee -a "$STATUS"
    return 2
  }
  [[ "$train_json" != "$eval_json" ]] || {
    echo "REFUSE_TRAIN_JSON_FOR_EVAL dataset=$dataset json=$train_json time=$(date)" | tee -a "$STATUS"
    return 2
  }
}

run_one() {
  local dataset="$1" mode="$2" layer="$3"
  local script config out selected train_log eval_log start_time end_time train_rc eval_rc note
  resolve_dataset "$dataset" "$mode" || return 2
  if [[ "$mode" == "stable" ]]; then
    script="$STABLE_SCRIPT"; config="$STABLE_CONFIG"
  else
    script="$MAIN_SCRIPT"; config="$MAIN_CONFIG"
  fi
  out="$run_root/paligemma-3b"
  mkdir -p "$out"
  selected="$out/$(layer_dir_name "$layer")/selected_checkpoint.tsv"
  train_log="$out/train_L${layer}_${mode}_${dataset}_$RUN_TAG.log"
  eval_log="$out/eval_L${layer}_${mode}_${dataset}_$RUN_TAG.log"
  start_time=$(date '+%F %T')
  train_rc=777; eval_rc=777; note=""

  if has_eval_done "$out" "$layer"; then
    train_rc=0; eval_rc=0; note="skip_existing_complete_eval"
    echo "SKIP_DONE dataset=$dataset mode=$mode layer=$layer time=$(date)" | tee -a "$STATUS"
  else
    archive_incomplete "$out" "$dataset" "$mode" "$layer"
    wait_gpu
    echo "TRAIN_START dataset=$dataset mode=$mode layer=$layer stall_timeout=$STALL_TIMEOUT_SECONDS config=$config time=$(date)" | tee -a "$STATUS"
    echo "ENV dataset=$dataset mode=$mode layer=$layer train_json=$train_json eval_json=$eval_json config=$config time=$(date)" > "$train_log"
    run_with_stall_timeout "$train_log" train \
      "$PY" "$script" \
        --out-root "$out" --layers "$layer" --epochs "$EPOCHS" --batch-size "$BATCH_SIZE" \
        --model-name paligemma-3b \
        --train-data "$train_json" --train-img-root "$train_img" \
        --eval-data "$eval_json" --eval-img-root "$eval_img" \
        --config-path "$config" --skip-eval --overwrite-train \
        >> "$train_log" 2>&1
    train_rc=$?
    if [[ "$LAST_RUN_STALLED" -eq 1 ]]; then
      note="train_stalled_${STALL_TIMEOUT_SECONDS}s"
    fi
    echo "TRAIN_END dataset=$dataset mode=$mode layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"

    if [[ "$train_rc" -eq 0 && -s "$selected" ]]; then
      wait_gpu
      echo "EVAL_START dataset=$dataset mode=$mode layer=$layer eval_json=$eval_json stall_timeout=$STALL_TIMEOUT_SECONDS time=$(date)" | tee -a "$STATUS"
      echo "ENV dataset=$dataset mode=$mode layer=$layer train_json=$train_json eval_json=$eval_json config=$config time=$(date)" > "$eval_log"
      run_with_stall_timeout "$eval_log" eval \
        "$PY" "$script" \
          --out-root "$out" --layers "$layer" --epochs "$EPOCHS" --batch-size "$BATCH_SIZE" \
          --model-name paligemma-3b \
          --train-data "$train_json" --train-img-root "$train_img" \
          --eval-data "$eval_json" --eval-img-root "$eval_img" \
          --config-path "$config" --skip-train --overwrite-eval \
          >> "$eval_log" 2>&1
      eval_rc=$?
      if [[ "$LAST_RUN_STALLED" -eq 1 ]]; then
        note="$note;eval_stalled_${STALL_TIMEOUT_SECONDS}s"
      fi
      if [[ "$eval_rc" -eq 0 && ! -f "$out/$(layer_dir_name "$layer")/eval_full.done" ]]; then
        eval_rc=98
        note="$note;eval_marker_missing"
      fi
      echo "EVAL_END dataset=$dataset mode=$mode layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    else
      note="$note;eval_not_run_no_checkpoint_or_train_failed"
      echo "EVAL_NOT_RUN dataset=$dataset mode=$mode layer=$layer train_rc=$train_rc selected_exists=$([[ -s "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
    fi
  fi

  end_time=$(date '+%F %T')
  echo "$dataset,$mode,$layer,$train_rc,$eval_rc,$start_time,$end_time,$out,$train_log,$eval_log,$note" >> "$CSV"
  [[ "$train_rc" -eq 0 && "$eval_rc" -eq 0 ]]
}

run_phase() {
  local dataset="$1" mode="$2" layers_csv="$3" layer
  echo "PHASE_START dataset=$dataset mode=$mode layers=$layers_csv time=$(date)" | tee -a "$STATUS"
  IFS=',' read -ra phase_layers <<< "$layers_csv"
  for layer in "${phase_layers[@]}"; do
    run_one "$dataset" "$mode" "$layer" || true
  done
  echo "PHASE_END dataset=$dataset mode=$mode time=$(date)" | tee -a "$STATUS"
}

wait_for_visual_stable_all8
echo "FOLLOWUP_RUN_START time=$(date)" | tee -a "$STATUS"
run_phase "evqa-pilot500" "stable" "8,7,17,0,5,6,1,4"
run_phase "mmke-entity" "stable" "8,9,7,12,11,10,17,16,13,5,6,3,2,1,0"
run_phase "evqa-pilot500" "main" "8,7,17,0,5,6,1,4"
run_phase "mmke-entity" "main" "8,9,7,12,11,10,17,16,13,5,6,3,2,1,0"
echo "FOLLOWUP_DONE time=$(date)" | tee -a "$STATUS"
echo "- End: $(date '+%F %T')" >> "$SUMMARY"
echo "- Status CSV: $CSV" >> "$SUMMARY"
