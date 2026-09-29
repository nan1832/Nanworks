#!/usr/bin/env bash
set -uo pipefail

export CUDA_VISIBLE_DEVICES=0
export TOKENIZERS_PARALLELISM=false
export PALIGEMMA_STABLE_MAX_EMA=100.0
export PALIGEMMA_STABLE_GRAD_CLIP_NORM=1.0
export PALIGEMMA_STABLE_SKIP_NONFINITE_STEP=1
export PALIGEMMA_STABLE_ROLLBACK_NONFINITE_STEP=1

PROJECT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUNNER="$PROJECT/scripts/run_evqa_pilot500_blip2_visedit_sweep_pali_retry_rollback.py"
RUN_TAG=20260718_160000
RUN_ROOT=/tmp/ph_teacher3/paligemma_priority_reruns_job3044208_${RUN_TAG}
STATUS="$RUN_ROOT/status.log"
CSV="$RUN_ROOT/layer_status.csv"
LOCK="$RUN_ROOT/launcher.lock"
START_ORDER="${START_ORDER:-1}"

EVQA_TRAIN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
EVQA_TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
EVQA_EVAL="$PROJECT/data/easy-edit-mm/vqa/vqa_eval.json"
EVQA_EVAL_IMG="$PROJECT/data/easy-edit-mm/images"

ENTITY_TRAIN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json
ENTITY_EVAL=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_eval_evqa_compat.json
ENTITY_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image

mkdir -p "$RUN_ROOT"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "ALREADY_RUNNING lock=$LOCK time=$(date '+%F %T')" | tee -a "$STATUS"
  exit 2
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

if (( START_ORDER <= 1 )); then
  echo 'order,dataset,config,layer,buffer,rc,selected,eval_done,start_time,end_time,out_root,log' > "$CSV"
  echo "RERUN_QUEUE_START job=3044208 host=$(hostname) gpu=0 time=$(date '+%F %T') root=$RUN_ROOT" | tee -a "$STATUS"
  echo "L0_POLICY skip_all_L0 reason=current_config_nonconvergent" | tee -a "$STATUS"
else
  echo "RERUN_QUEUE_RESUME job=3044208 start_order=$START_ORDER host=$(hostname) gpu=0 time=$(date '+%F %T') root=$RUN_ROOT" | tee -a "$STATUS"
fi

wait_for_gpu() {
  # The adopted Slurm shell can expose a logical GPU index that differs from
  # the host's physical nvidia-smi index. The queue is serial, so after the
  # previous Python process exits we only pause briefly for CUDA cleanup.
  sleep 20
  echo "GPU_SERIAL_CLEANUP_WAIT_DONE time=$(date '+%F %T')" | tee -a "$STATUS"
}

run_one() {
  local order=$1 dataset=$2 config_label=$3 layer=$4 buffer=$5 config_path=$6
  local train_data=$7 train_img=$8 eval_data=$9 eval_img=${10} rollback=${11}
  local out="$RUN_ROOT/${order}_${dataset}_${config_label}_L${layer}/paligemma-3b"
  local log="$RUN_ROOT/${order}_${dataset}_${config_label}_L${layer}.log"
  local start end pid rc selected eval_done age now mtime

  mkdir -p "$out"
  wait_for_gpu
  start=$(date '+%F %T')
  echo "RUN_START order=$order dataset=$dataset config=$config_label layer=$layer buffer=$buffer time=$start" | tee -a "$STATUS"

  (
    cd "$PROJECT" || exit 90
    export PALIGEMMA_STABLE_ROLLBACK_NONFINITE_STEP="$rollback"
    exec "$PY" "$RUNNER" \
      --out-root "$out" \
      --layers "$layer" \
      --epochs 50 \
      --batch-size 2 \
      --model-name paligemma-3b \
      --device cuda:0 \
      --train-data "$train_data" \
      --train-img-root "$train_img" \
      --eval-data "$eval_data" \
      --eval-img-root "$eval_img" \
      --config-path "$config_path" \
      --seed 20260601 \
      --ema-alpha 0.1 \
      --data-buffer-size "$buffer" \
      --keep-top-ckpts 5 \
      --keep-last-ckpts 2 \
      --overwrite-train \
      --overwrite-eval
  ) > "$log" 2>&1 &
  pid=$!

  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
    now=$(date +%s)
    mtime=$(stat -c %Y "$log" 2>/dev/null || echo "$now")
    age=$((now - mtime))
    if (( age > 7200 )); then
      echo "WATCHDOG_STALE_LOG order=$order dataset=$dataset layer=$layer pid=$pid age_seconds=$age action=TERM time=$(date '+%F %T')" | tee -a "$STATUS"
      kill -TERM "$pid" 2>/dev/null || true
      sleep 20
      kill -KILL "$pid" 2>/dev/null || true
      break
    fi
  done

  wait "$pid"
  rc=$?
  end=$(date '+%F %T')
  selected=0
  eval_done=0
  [[ -s "$out/layer_$(printf '%02d' "$layer")/selected_checkpoint.tsv" ]] && selected=1
  [[ -s "$out/layer_$(printf '%02d' "$layer")/eval_full.done" ]] && eval_done=1
  echo "$order,$dataset,$config_label,$layer,$buffer,$rc,$selected,$eval_done,$start,$end,$out,$log" >> "$CSV"
  echo "RUN_END order=$order dataset=$dataset config=$config_label layer=$layer rc=$rc selected=$selected eval_done=$eval_done time=$end" | tee -a "$STATUS"
}

if (( START_ORDER <= 1 )); then
  run_one 1 evqa-pilot500 stable-buffer1 6 1 configs/vead/paligemma-3b-stable.yaml \
    "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 0
fi

if (( START_ORDER <= 2 )); then
  run_one 2 mmke-entity stable-buffer1 12 1 configs/vead/paligemma-3b-stable.yaml \
    "$ENTITY_TRAIN" "$ENTITY_IMG" "$ENTITY_EVAL" "$ENTITY_IMG" 0
fi

if (( START_ORDER <= 3 )); then
  run_one 3 evqa-pilot500 stable-rollback 4 4 configs/vead/paligemma-3b-stable.yaml \
    "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 1
fi

if (( START_ORDER <= 4 )); then
  run_one 4 mmke-entity main-rollback 16 4 configs/vead/paligemma-3b.yaml \
    "$ENTITY_TRAIN" "$ENTITY_IMG" "$ENTITY_EVAL" "$ENTITY_IMG" 1
fi

touch "$RUN_ROOT/QUEUE_DONE"
echo "RERUN_QUEUE_DONE job=3044208 time=$(date '+%F %T')" | tee -a "$STATUS"
