#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

GPU_ID=0
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
MAIN_SCRIPT=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
STABLE_SCRIPT=scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py
MAIN_CONFIG=configs/vead/paligemma-3b.yaml
STABLE_CONFIG=configs/vead/paligemma-3b-stable.yaml
EPOCHS=50
BATCH_SIZE=2
GPU_WAIT_MAX_USED_MIB=${GPU_WAIT_MAX_USED_MIB:-65000}
MAIN_TIMEOUT_SECONDS=${MAIN_TIMEOUT_SECONDS:-7200}
STABLE_TIMEOUT_SECONDS=${STABLE_TIMEOUT_SECONDS:-14400}
export PALIGEMMA_STABLE_MAX_EMA=${PALIGEMMA_STABLE_MAX_EMA:-100.0}
export PALIGEMMA_STABLE_GRAD_CLIP_NORM=${PALIGEMMA_STABLE_GRAD_CLIP_NORM:-1.0}
export PALIGEMMA_STABLE_SKIP_NONFINITE_STEP=${PALIGEMMA_STABLE_SKIP_NONFINITE_STEP:-1}

SERVER_RESULTS=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
VIS_ROOT=$SERVER_RESULTS/mmke_visual_top3_union_train_eval_7models_20260613_014644
ENT_ROOT=$SERVER_RESULTS/mmke_entity_top3_union_train_eval_7models_20260616_155000
PILOT_ROOT=$SERVER_RESULTS/visedit_pre_alt_pilot500_6models_20260608_092829
RUN_TAG=$(date +%Y%m%d_%H%M%S)
CONTROL_ROOT=$SERVER_RESULTS/paligemma_pending_followup_job3044208_${RUN_TAG}
STATUS=$CONTROL_ROOT/paligemma_pending_followup_status.log
CSV=$CONTROL_ROOT/paligemma_pending_followup_layer_status.csv
SUMMARY=$CONTROL_ROOT/paligemma_pending_followup_summary.md
LOCK=$SERVER_RESULTS/paligemma_pending_followup_job3044208.lock
mkdir -p "$CONTROL_ROOT"
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "PALIGEMMA_FOLLOWUP_ALREADY_RUNNING time=$(date)" | tee -a "$STATUS"
  exit 3
fi

echo "dataset,mode,layer,train_rc,eval_rc,start_time,end_time,out_root,train_log,eval_log,note" > "$CSV"
{
  echo "# PaliGemma pending follow-up job3044208"
  echo
  echo "Start: $(date '+%F %T')"
  echo
  echo "- GPU: job 3044208 / g09 / CUDA_VISIBLE_DEVICES=0"
  echo "- Main script: $MAIN_SCRIPT + $MAIN_CONFIG"
  echo "- Stable script: $STABLE_SCRIPT + $STABLE_CONFIG"
  echo "- Eval rule: always use dataset eval/test JSON, never train JSON for eval."
  echo
} > "$SUMMARY"

echo "PALIGEMMA_FOLLOWUP_START time=$(date) control_root=$CONTROL_ROOT" | tee -a "$STATUS"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS" || true

wait_gpu() {
  while true; do
    local used cuda_ok
    used=$(/usr/bin/nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')
    used=${used:-999999}
    cuda_ok=0
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" ]]; then
      if "$PY" - <<'PY' >/tmp/paligemma_followup_cuda_probe.log 2>&1
import torch
assert torch.cuda.is_available(), 'cuda unavailable'
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

layer_dir_name() { printf 'layer_%02d' "$1"; }

has_eval_done() {
  local out="$1" layer="$2"
  local d="$out/$(layer_dir_name "$layer")"
  [[ -f "$d/eval_full.done" && -f "$d/selected_checkpoint.tsv" ]]
}

archive_incomplete() {
  local out="$1" dataset="$2" mode="$3" layer="$4"
  local d="$out/$(layer_dir_name "$layer")"
  if [[ -d "$d" && ! -f "$d/eval_full.done" ]]; then
    local archive="$out/failed_or_incomplete_${dataset}_${mode}_L${layer}_${RUN_TAG}"
    echo "ARCHIVE_INCOMPLETE dataset=$dataset mode=$mode layer=$layer from=$d to=$archive time=$(date)" | tee -a "$STATUS"
    rm -rf "$archive"
    mv "$d" "$archive"
  fi
}

run_one() {
  local dataset="$1" mode="$2" layer="$3" run_root="$4" train_json="$5" train_img="$6" eval_json="$7" eval_img="$8"
  local script config overwrite_train overwrite_eval
  local out="$run_root/paligemma-3b"
  mkdir -p "$out"
  if [[ "$mode" == "main" ]]; then
    script="$MAIN_SCRIPT"; config="$MAIN_CONFIG"; overwrite_train=""; overwrite_eval=""
  else
    script="$STABLE_SCRIPT"; config="$STABLE_CONFIG"; overwrite_train="--overwrite-train"; overwrite_eval="--overwrite-eval"
  fi
  local train_log="$out/train_L${layer}_${mode}_${dataset}_${RUN_TAG}.log"
  local eval_log="$out/eval_L${layer}_${mode}_${dataset}_${RUN_TAG}.log"
  local start_time end_time train_rc eval_rc note selected
  start_time=$(date '+%F %T')
  train_rc=777; eval_rc=777; note=""
  selected="$out/$(layer_dir_name "$layer")/selected_checkpoint.tsv"

  if has_eval_done "$out" "$layer"; then
    train_rc=0; eval_rc=0; note="eval_skip_existing"
    echo "SKIP_DONE dataset=$dataset mode=$mode layer=$layer out=$out time=$(date)" | tee -a "$STATUS"
  else
    archive_incomplete "$out" "$dataset" "$mode" "$layer"
    wait_gpu
    echo "TRAIN_START dataset=$dataset mode=$mode layer=$layer config=$config time=$(date)" | tee -a "$STATUS"
    echo "ENV CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES dataset=$dataset mode=$mode layer=$layer train_json=$train_json eval_json=$eval_json host=$(hostname) time=$(date)" > "$train_log"
    local timeout_seconds
    if [[ "$mode" == "main" ]]; then timeout_seconds="$MAIN_TIMEOUT_SECONDS"; else timeout_seconds="$STABLE_TIMEOUT_SECONDS"; fi
    timeout --preserve-status --kill-after=120s "$timeout_seconds" \
      "$PY" "$script" \
        --out-root "$out" \
        --layers "$layer" \
        --epochs "$EPOCHS" \
        --batch-size "$BATCH_SIZE" \
        --model-name paligemma-3b \
        --train-data "$train_json" \
        --train-img-root "$train_img" \
        --eval-data "$eval_json" \
        --eval-img-root "$eval_img" \
        --config-path "$config" \
        --skip-eval \
        $overwrite_train \
        >> "$train_log" 2>&1
    train_rc=$?
    if [[ "$train_rc" -eq 124 || "$train_rc" -eq 137 ]]; then
      note="${note};train_timeout_${timeout_seconds}s"
      echo "TRAIN_TIMEOUT dataset=$dataset mode=$mode layer=$layer timeout_seconds=$timeout_seconds rc=$train_rc time=$(date)" | tee -a "$STATUS"
    fi
    echo "TRAIN_END dataset=$dataset mode=$mode layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"
    if [[ "$train_rc" -eq 0 && -s "$selected" ]]; then
      wait_gpu
      echo "EVAL_START dataset=$dataset mode=$mode layer=$layer eval_json=$eval_json time=$(date)" | tee -a "$STATUS"
      echo "ENV CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES dataset=$dataset mode=$mode layer=$layer train_json=$train_json eval_json=$eval_json host=$(hostname) time=$(date)" > "$eval_log"
      timeout --preserve-status --kill-after=120s "$STABLE_TIMEOUT_SECONDS" \
        "$PY" "$script" \
          --out-root "$out" \
          --layers "$layer" \
          --epochs "$EPOCHS" \
          --batch-size "$BATCH_SIZE" \
          --model-name paligemma-3b \
          --train-data "$train_json" \
          --train-img-root "$train_img" \
          --eval-data "$eval_json" \
          --eval-img-root "$eval_img" \
          --config-path "$config" \
          --skip-train \
          $overwrite_eval \
          >> "$eval_log" 2>&1
      eval_rc=$?
      if [[ "$eval_rc" -eq 124 || "$eval_rc" -eq 137 ]]; then
        note="${note};eval_timeout_${STABLE_TIMEOUT_SECONDS}s"
        echo "EVAL_TIMEOUT dataset=$dataset mode=$mode layer=$layer timeout_seconds=$STABLE_TIMEOUT_SECONDS rc=$eval_rc time=$(date)" | tee -a "$STATUS"
      fi
      echo "EVAL_END dataset=$dataset mode=$mode layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    else
      note="eval_not_run_no_checkpoint_or_train_failed"
      echo "EVAL_NOT_RUN dataset=$dataset mode=$mode layer=$layer train_rc=$train_rc selected_exists=$([[ -s "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
    fi
  fi
  end_time=$(date '+%F %T')
  echo "$dataset,$mode,$layer,$train_rc,$eval_rc,$start_time,$end_time,$out,$train_log,$eval_log,$note" >> "$CSV"
  if [[ "$train_rc" -eq 0 && "$eval_rc" -eq 0 ]]; then return 0; fi
  return 1
}

run_dataset() {
  local dataset="$1" main_root="$2" stable_root="$3" train_json="$4" train_img="$5" eval_json="$6" eval_img="$7" layers_csv="$8"
  echo "DATASET_START dataset=$dataset layers=$layers_csv main_root=$main_root stable_root=$stable_root time=$(date)" | tee -a "$STATUS"
  {
    echo "## $dataset"
    echo
    echo "Main root: $main_root"
    echo
    echo "Stable root: $stable_root"
    echo
    echo "Layers: $layers_csv"
    echo
    echo "Eval JSON: $eval_json"
    echo
  } >> "$SUMMARY"
  mkdir -p "$main_root/paligemma-3b" "$stable_root/paligemma-3b"
  IFS=',' read -ra layers <<< "$layers_csv"
  local failed_layers=()
  for layer in "${layers[@]}"; do
    if ! run_one "$dataset" main "$layer" "$main_root" "$train_json" "$train_img" "$eval_json" "$eval_img"; then
      failed_layers+=("$layer")
      echo "MAIN_LAYER_FAILED dataset=$dataset layer=$layer will_stable=1 time=$(date)" | tee -a "$STATUS"
    fi
  done
  echo "STABLE_ALL_START dataset=$dataset layers=${layers[*]} main_failed_layers=${failed_layers[*]:-none} time=$(date)" | tee -a "$STATUS"
  for layer in "${layers[@]}"; do
    run_one "$dataset" stable "$layer" "$stable_root" "$train_json" "$train_img" "$eval_json" "$eval_img" || true
  done
  echo "DATASET_END dataset=$dataset time=$(date)" | tee -a "$STATUS"
}

# Dataset definitions. Eval/test JSON is deliberately different from train JSON.
MMKE_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
PILOT_TRAIN_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
PILOT_TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
PILOT_EVAL_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
PILOT_EVAL_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images

# 1) Finish MMKE-visual pending PaliGemma layers. Main keeps existing done layers; stable must cover all 8 pending layers.
run_dataset mmke-visual "$VIS_ROOT" "$SERVER_RESULTS/paligemma_stable_mmke_visual_pending8_job3044208_${RUN_TAG}" \
  "$VIS_ROOT/data/vqa_mmke_visual_train_evqa_compat.json" "$MMKE_IMG" \
  "$VIS_ROOT/data/vqa_mmke_visual_eval_evqa_compat.json" "$MMKE_IMG" \
  "7,13,0,5,6,3,2,1"

# 2) EVQA-pilot500 PaliGemma pending layers from section 3.4.1.
run_dataset evqa-pilot500 "$PILOT_ROOT" "$SERVER_RESULTS/paligemma_stable_evqa_pilot500_pending_job3044208_${RUN_TAG}" \
  "$PILOT_TRAIN_JSON" "$PILOT_TRAIN_IMG" \
  "$PILOT_EVAL_JSON" "$PILOT_EVAL_IMG" \
  "8,7,17,0,5,6,1,4"

# 3) MMKE-entity PaliGemma pending layers from section 3.4.3.
run_dataset mmke-entity "$ENT_ROOT" "$SERVER_RESULTS/paligemma_stable_mmke_entity_pending_job3044208_${RUN_TAG}" \
  "$ENT_ROOT/data/vqa_mmke_entity_train_evqa_compat.json" "$MMKE_IMG" \
  "$ENT_ROOT/data/vqa_mmke_entity_eval_evqa_compat.json" "$MMKE_IMG" \
  "8,9,7,12,11,10,17,16,13,5,6,3,2,1,0"

echo "PALIGEMMA_FOLLOWUP_DONE time=$(date)" | tee -a "$STATUS"
{
  echo
  echo "End: $(date '+%F %T')"
  echo
  echo "Status CSV: $CSV"
} >> "$SUMMARY"
