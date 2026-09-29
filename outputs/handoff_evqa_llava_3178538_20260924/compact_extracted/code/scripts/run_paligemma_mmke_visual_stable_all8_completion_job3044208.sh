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
STABLE_SCRIPT=scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py
STABLE_CONFIG=configs/vead/paligemma-3b-stable.yaml
EPOCHS=50
BATCH_SIZE=2
GPU_WAIT_MAX_USED_MIB=${GPU_WAIT_MAX_USED_MIB:-65000}
STABLE_TIMEOUT_SECONDS=${STABLE_TIMEOUT_SECONDS:-14400}
SERVER_RESULTS=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
VIS_ROOT=$SERVER_RESULTS/mmke_visual_top3_union_train_eval_7models_20260613_014644
STABLE_ROOT=$SERVER_RESULTS/paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917
RUN_TAG=$(date +%Y%m%d_%H%M%S)
CONTROL_ROOT=$SERVER_RESULTS/paligemma_visual_stable_all8_completion_job3044208_${RUN_TAG}
STATUS=$CONTROL_ROOT/status.log
CSV=$CONTROL_ROOT/layer_status.csv
LOCK=$SERVER_RESULTS/paligemma_pending_followup_job3044208.lock
MMKE_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
TRAIN_JSON=$VIS_ROOT/data/vqa_mmke_visual_train_evqa_compat.json
EVAL_JSON=$VIS_ROOT/data/vqa_mmke_visual_eval_evqa_compat.json
LAYERS=(7 13 0 5 6 3 2 1)
mkdir -p "$CONTROL_ROOT" "$STABLE_ROOT/paligemma-3b"
echo 'dataset,mode,layer,train_rc,eval_rc,start_time,end_time,out_root,train_log,eval_log,note' > "$CSV"
echo "VISUAL_STABLE_ALL8_COMPLETION_START time=$(date) control_root=$CONTROL_ROOT stable_root=$STABLE_ROOT" | tee -a "$STATUS"

exec 9>"$LOCK"
echo "WAIT_EXISTING_FOLLOWUP_LOCK time=$(date)" | tee -a "$STATUS"
flock 9
echo "LOCK_ACQUIRED time=$(date)" | tee -a "$STATUS"

layer_dir_name() { printf 'layer_%02d' "$1"; }
has_eval_done() {
  local out="$1" layer="$2" d
  d="$out/$(layer_dir_name "$layer")"
  [[ -f "$d/eval_full.done" && -f "$d/selected_checkpoint.tsv" ]]
}
wait_gpu() {
  while true; do
    local used cuda_ok
    used=$(/usr/bin/nvidia-smi -i "$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')
    used=${used:-999999}
    cuda_ok=0
    if [[ "$used" -lt "$GPU_WAIT_MAX_USED_MIB" ]]; then
      if "$PY" - <<'PY' >/tmp/paligemma_visual_stable_all8_cuda_probe.log 2>&1
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
archive_incomplete() {
  local out="$1" layer="$2" d archive
  d="$out/$(layer_dir_name "$layer")"
  if [[ -d "$d" && ! -f "$d/eval_full.done" ]]; then
    archive="$out/failed_or_incomplete_mmke-visual_stable_L${layer}_${RUN_TAG}"
    echo "ARCHIVE_INCOMPLETE layer=$layer from=$d to=$archive time=$(date)" | tee -a "$STATUS"
    rm -rf "$archive"
    mv "$d" "$archive"
  fi
}
run_stable_one() {
  local layer="$1" out="$STABLE_ROOT/paligemma-3b" selected train_log eval_log start_time end_time train_rc eval_rc note
  selected="$out/$(layer_dir_name "$layer")/selected_checkpoint.tsv"
  train_log="$out/train_L${layer}_stable_mmke-visual_all8_${RUN_TAG}.log"
  eval_log="$out/eval_L${layer}_stable_mmke-visual_all8_${RUN_TAG}.log"
  start_time=$(date '+%F %T')
  train_rc=777; eval_rc=777; note=""
  if has_eval_done "$out" "$layer"; then
    train_rc=0; eval_rc=0; note="eval_skip_existing"
    echo "SKIP_DONE layer=$layer out=$out time=$(date)" | tee -a "$STATUS"
  else
    archive_incomplete "$out" "$layer"
    wait_gpu
    echo "TRAIN_START layer=$layer config=$STABLE_CONFIG time=$(date)" | tee -a "$STATUS"
    echo "ENV CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES layer=$layer train_json=$TRAIN_JSON eval_json=$EVAL_JSON host=$(hostname) time=$(date)" > "$train_log"
    timeout --preserve-status --kill-after=120s "$STABLE_TIMEOUT_SECONDS" \
      "$PY" "$STABLE_SCRIPT" \
        --out-root "$out" \
        --layers "$layer" \
        --epochs "$EPOCHS" \
        --batch-size "$BATCH_SIZE" \
        --model-name paligemma-3b \
        --train-data "$TRAIN_JSON" \
        --train-img-root "$MMKE_IMG" \
        --eval-data "$EVAL_JSON" \
        --eval-img-root "$MMKE_IMG" \
        --config-path "$STABLE_CONFIG" \
        --skip-eval \
        --overwrite-train \
        >> "$train_log" 2>&1
    train_rc=$?
    echo "TRAIN_END layer=$layer rc=$train_rc time=$(date)" | tee -a "$STATUS"
    if [[ "$train_rc" -eq 0 && -s "$selected" ]]; then
      wait_gpu
      echo "EVAL_START layer=$layer eval_json=$EVAL_JSON time=$(date)" | tee -a "$STATUS"
      echo "ENV CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES layer=$layer train_json=$TRAIN_JSON eval_json=$EVAL_JSON host=$(hostname) time=$(date)" > "$eval_log"
      timeout --preserve-status --kill-after=120s "$STABLE_TIMEOUT_SECONDS" \
        "$PY" "$STABLE_SCRIPT" \
          --out-root "$out" \
          --layers "$layer" \
          --epochs "$EPOCHS" \
          --batch-size "$BATCH_SIZE" \
          --model-name paligemma-3b \
          --train-data "$TRAIN_JSON" \
          --train-img-root "$MMKE_IMG" \
          --eval-data "$EVAL_JSON" \
          --eval-img-root "$MMKE_IMG" \
          --config-path "$STABLE_CONFIG" \
          --skip-train \
          --overwrite-eval \
          >> "$eval_log" 2>&1
      eval_rc=$?
      echo "EVAL_END layer=$layer rc=$eval_rc time=$(date)" | tee -a "$STATUS"
    else
      note="eval_not_run_no_checkpoint_or_train_failed"
      echo "EVAL_NOT_RUN layer=$layer train_rc=$train_rc selected_exists=$([[ -s "$selected" ]] && echo 1 || echo 0) time=$(date)" | tee -a "$STATUS"
    fi
  fi
  end_time=$(date '+%F %T')
  echo "mmke-visual,stable,$layer,$train_rc,$eval_rc,$start_time,$end_time,$out,$train_log,$eval_log,$note" >> "$CSV"
}

for layer in "${LAYERS[@]}"; do
  run_stable_one "$layer" || true
done

echo "VISUAL_STABLE_ALL8_COMPLETION_DONE time=$(date)" | tee -a "$STATUS"
