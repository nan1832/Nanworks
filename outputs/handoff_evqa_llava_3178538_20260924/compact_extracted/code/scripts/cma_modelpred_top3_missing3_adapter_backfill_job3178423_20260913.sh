#!/usr/bin/env bash
set -Eeuo pipefail

# CMA-ModelPred Top-3 newly introduced layers that lack real Adapter eval.
# Run inside Slurm job 3178423 on g07.  The original MMKE-entity/LLaVA
# launcher is only SIGSTOP'ed while a new stage wins the GPU-start race and
# is SIGCONT'ed immediately after the stage process starts.

EXPECTED_JOB=3178423
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY_SMOL=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
PY_QWEN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
RUNNER=scripts/run_evqa_pilot500_blip2_visedit_sweep.py
GPU_ID=0
EPOCHS=50
BATCH_SIZE=2
SEED=20260601
EMA_ALPHA=0.1
DATA_BUFFER_SIZE=4
STALL_SECONDS=7200
POLL_SECONDS=60

RUN_ROOT=/tmp/ph_teacher3/cma_modelpred_top3_missing3_job3178423_20260913
SHARED_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_modelpred_top3_missing3_adapter_backfill_20260913_job3178423
STATUS=$RUN_ROOT/queue.status.log
CSV=$RUN_ROOT/layer_status.csv
LOCK=$RUN_ROOT/launcher.lock

EVQA_TRAIN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
EVQA_TRAIN_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
EVQA_EVAL=$PROJ/data/easy-edit-mm/vqa/vqa_eval.json
EVQA_EVAL_IMG=$PROJ/data/easy-edit-mm/images

MMKE_VIS_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644
MMKE_VIS_TRAIN=$MMKE_VIS_ROOT/data/vqa_mmke_visual_train_evqa_compat.json
MMKE_VIS_EVAL=$MMKE_VIS_ROOT/data/vqa_mmke_visual_eval_evqa_compat.json
MMKE_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image

SMOL_CONFIG=configs/vead/smolvlm-1.7b.yaml
QWEN_CONFIG=configs/vead/qwen2.5-vl-3b-instruct.yaml
LLAVA_LAUNCH_PATTERN='launch_formal_top3_stage2_20260812.sh job3126082'

mkdir -p "$RUN_ROOT/logs" "$SHARED_ROOT"
cd "$PROJ"
export PYTHONPATH="$PROJ:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

exec 9>"$LOCK"
if ! flock -n 9; then
  printf '%s\n' "ALREADY_RUNNING lock=$LOCK time=$(date '+%F %T %Z')" | tee -a "$STATUS"
  exit 3
fi

if [[ ! -s "$CSV" ]]; then
  printf '%s\n' 'dataset,model,layer,stage,rc,start_time,end_time,log,note' >"$CSV"
fi

log_status() {
  printf '%s\n' "$*" | tee -a "$STATUS"
}

LLAVA_PIDS=()
llava_launcher_pids() {
  pgrep -f "$LLAVA_LAUNCH_PATTERN" 2>/dev/null | while read -r pid; do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    cmd=$(tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null || true)
    [[ "$cmd" == *"$LLAVA_LAUNCH_PATTERN"* ]] && printf '%s\n' "$pid"
  done
}

suspend_llava_launcher() {
  LLAVA_PIDS=()
  while read -r pid; do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    kill -STOP "$pid" 2>/dev/null || continue
    LLAVA_PIDS+=("$pid")
    log_status "LLAVA_LAUNCHER_PAUSE pid=$pid reason=atomic_filler_stage_start time=$(date '+%F %T %Z')"
  done < <(llava_launcher_pids)
}

resume_llava_launcher() {
  local pid
  for pid in "${LLAVA_PIDS[@]:-}"; do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    kill -CONT "$pid" 2>/dev/null || true
    log_status "LLAVA_LAUNCHER_RESUME pid=$pid time=$(date '+%F %T %Z')"
  done
  LLAVA_PIDS=()
}
trap 'resume_llava_launcher' EXIT INT TERM HUP

gpu_non_kernel_count() {
  local pid cmd count=0
  while read -r pid; do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    cmd=$(tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null || true)
    [[ "$cmd" == *ipykernel_launcher* ]] || count=$((count+1))
  done < <(nvidia-smi -i "$GPU_ID" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null)
  printf '%s\n' "$count"
}

wait_gpu_ready() {
  local min_free=$1 stable=0 free non_kernel
  while (( stable < 3 )); do
    free=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -dc '0-9')
    free=${free:-0}
    non_kernel=$(gpu_non_kernel_count)
    if (( free >= min_free && non_kernel == 0 )); then
      stable=$((stable+1))
    else
      stable=0
    fi
    log_status "GPU_READY_PROBE free_mib=$free min_free_mib=$min_free non_kernel=$non_kernel stable=$stable/3 time=$(date '+%F %T %Z')"
    (( stable >= 3 )) || sleep 10
  done
}

progress_signature() {
  "$PY_SMOL" - "$1" <<'PY'
import re
import sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.exists():
    raise SystemExit(0)
with p.open('rb') as h:
    try:
        h.seek(-8 * 1024 * 1024, 2)
    except OSError:
        h.seek(0)
    text = h.read().decode('utf-8', errors='ignore').replace('\r', '\n')
last = ''
for line in text.splitlines():
    if re.search(r'\b\d+\s*/\s*\d+\b', line) and re.search(
        r'Epoch|Pre-process|Evaluat|eval|train|Waiting data|it/s|step', line, re.I
    ):
        last = line[-600:]
if last:
    print(last)
PY
}

run_watched() {
  local dataset=$1 model=$2 layer=$3 stage=$4 log=$5 py=$6
  shift 6
  local pid rc now last_progress last_sig='' sig last_raw raw heartbeat
  : >"$log"
  setsid env CUDA_VISIBLE_DEVICES="$GPU_ID" PYTORCH_CUDA_ALLOC_CONF="$PYTORCH_CUDA_ALLOC_CONF" "$py" "$@" >>"$log" 2>&1 &
  pid=$!
  last_progress=$(date +%s)
  heartbeat=$last_progress
  last_raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
  log_status "PROCESS_START dataset=$dataset model=$model layer=$layer stage=$stage pid=$pid pgid=$pid log=$log"
  resume_llava_launcher

  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL_SECONDS"
    now=$(date +%s)
    sig=$(progress_signature "$log" 2>/dev/null || true)
    raw=$(stat -c '%s:%Y' "$log" 2>/dev/null || echo 0:0)
    if [[ -n "$sig" && "$sig" != "$last_sig" ]]; then
      last_sig=$sig
      last_progress=$now
      log_status "WATCH_PROGRESS dataset=$dataset model=$model layer=$layer stage=$stage sig=${sig:0:320} time=$(date '+%F %T %Z')"
    elif [[ -z "$last_sig" && "$raw" != "$last_raw" ]]; then
      last_progress=$now
    fi
    last_raw=$raw
    if (( now - heartbeat >= 600 )); then
      log_status "WATCH_HEARTBEAT dataset=$dataset model=$model layer=$layer stage=$stage idle_seconds=$((now-last_progress)) gpu=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -d '\n') time=$(date '+%F %T %Z')"
      heartbeat=$now
    fi
    if (( now - last_progress >= STALL_SECONDS )); then
      log_status "WATCHDOG_STALL dataset=$dataset model=$model layer=$layer stage=$stage unchanged_seconds=$((now-last_progress)) time=$(date '+%F %T %Z')"
      kill -TERM -- "-$pid" 2>/dev/null || true
      for _ in $(seq 1 60); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      kill -0 "$pid" 2>/dev/null && kill -KILL -- "-$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
  done
  wait "$pid"
  rc=$?
  log_status "PROCESS_END dataset=$dataset model=$model layer=$layer stage=$stage pid=$pid rc=$rc time=$(date '+%F %T %Z')"
  return "$rc"
}

selected_path() {
  tail -n1 "$1" | awk -F '\t' '{print $NF}' | tr -d '\r'
}

complete_exists() {
  local d=$1 selected result
  [[ -s "$d/train.done" && -s "$d/selected_checkpoint.tsv" && -s "$d/eval_full.done" ]] || return 1
  selected=$(selected_path "$d/selected_checkpoint.tsv")
  [[ -n "$selected" && -e "$selected" ]] || return 1
  result=$(find "$d/eval_full" -type f -name results.json -size +0c -print -quit 2>/dev/null)
  [[ -n "$result" ]]
}

cleanup_and_sync() {
  local d=$1 dataset=$2 model=$3 layer=$4 selected selected_abs d_abs parent item item_abs removed=0 bytes=0 item_bytes
  local dest rel shared_selected local_hash shared_hash tmp_tsv marker marker_tmp
  complete_exists "$d"
  selected=$(selected_path "$d/selected_checkpoint.tsv")
  selected_abs=$(realpath -e "$selected")
  d_abs=$(realpath -e "$d")
  case "$selected_abs" in "$d_abs"/*) ;; *) log_status "CLEANUP_REFUSED selected_outside_layer=$selected_abs"; return 2 ;; esac
  parent=$(dirname "$selected_abs")
  case "$parent" in "$d_abs"/*/checkpoints) ;; *) log_status "CLEANUP_REFUSED unexpected_parent=$parent"; return 2 ;; esac
  for item in "$parent"/*; do
    [[ -e "$item" ]] || continue
    item_abs=$(realpath -e "$item")
    [[ "$item_abs" == "$selected_abs" ]] && continue
    item_bytes=$(du -sb "$item_abs" 2>/dev/null | awk '{print $1}')
    rm -rf -- "$item_abs"
    removed=$((removed+1))
    bytes=$((bytes+${item_bytes:-0}))
  done
  [[ -e "$selected_abs" ]]
  dest="$SHARED_ROOT/$dataset/$model/layer_$(printf '%02d' "$layer")"
  mkdir -p "$(dirname "$dest")" "$dest"
  rsync -a "$d/" "$dest/"
  rel=${selected_abs#"$d_abs"/}
  shared_selected="$dest/$rel"
  tmp_tsv="$dest/selected_checkpoint.tsv.tmp.$$"
  awk -F '\t' -v OFS='\t' -v p="$shared_selected" 'NR==2{$NF=p} {print}' "$dest/selected_checkpoint.tsv" >"$tmp_tsv"
  mv -f "$tmp_tsv" "$dest/selected_checkpoint.tsv"
  # The runner records absolute paths in its status markers.  Rewrite only
  # these copied marker files so the durable archive does not point back to
  # the layer directory that will be removed from /tmp.
  for marker in train.done eval_full.done; do
    [[ -f "$dest/$marker" ]] || continue
    marker_tmp="$dest/$marker.tmp.$$"
    sed "s|$d_abs|$dest|g" "$dest/$marker" >"$marker_tmp"
    mv -f "$marker_tmp" "$dest/$marker"
  done
  [[ -s "$dest/train.done" && -s "$dest/eval_full.done" && -s "$dest/selected_checkpoint.tsv" && -e "$shared_selected" ]]
  find "$dest/eval_full" -type f -name results.json -size +0c -print -quit | grep -q .
  local_hash=$(sha256sum "$selected_abs" | awk '{print $1}')
  shared_hash=$(sha256sum "$shared_selected" | awk '{print $1}')
  [[ "$local_hash" == "$shared_hash" ]]
  printf 'verified_at\t%s\nselected_sha256\t%s\nsource\t%s\n' "$(date '+%F %T %Z')" "$shared_hash" "$d_abs" >"$dest/SYNC_VERIFIED"
  log_status "LAYER_SYNC_VERIFIED dataset=$dataset model=$model layer=$layer dest=$dest selected_sha256=$shared_hash cleanup_removed=$removed cleanup_bytes=$bytes time=$(date '+%F %T %Z')"
  case "$d_abs" in "$RUN_ROOT"/*) rm -rf -- "$d_abs" ;; *) log_status "TMP_DELETE_REFUSED path=$d_abs"; return 2 ;; esac
  log_status "TMP_DUPLICATE_REMOVED dataset=$dataset model=$model layer=$layer path=$d_abs time=$(date '+%F %T %Z')"
}

run_stage() {
  local dataset=$1 model=$2 layer=$3 stage=$4 py=$5 config=$6 train_json=$7 train_img=$8 eval_json=$9 eval_img=${10} min_free=${11}
  local out="$RUN_ROOT/$dataset/$model" log="$RUN_ROOT/logs/${dataset}_${model}_L${layer}_${stage}_$(date +%Y%m%d_%H%M%S).log"
  local -a args
  mkdir -p "$out"
  args=(
    "$RUNNER" --out-root "$out" --layers "$layer" --epochs "$EPOCHS" --batch-size "$BATCH_SIZE"
    --model-name "$model" --device cuda:0
    --train-data "$train_json" --train-img-root "$train_img"
    --eval-data "$eval_json" --eval-img-root "$eval_img"
    --config-path "$config" --seed "$SEED" --ema-alpha "$EMA_ALPHA"
    --data-buffer-size "$DATA_BUFFER_SIZE" --keep-top-ckpts 5 --keep-last-ckpts 2
  )
  [[ "$stage" == train ]] && args+=(--skip-eval) || args+=(--skip-train)
  suspend_llava_launcher
  wait_gpu_ready "$min_free"
  log_status "STAGE_START dataset=$dataset model=$model layer=$layer stage=$stage config=$config train=$train_json eval=$eval_json time=$(date '+%F %T %Z')"
  run_watched "$dataset" "$model" "$layer" "$stage" "$log" "$py" "${args[@]}"
}

run_layer() {
  local dataset=$1 model=$2 layer=$3 py=$4 config=$5 train_json=$6 train_img=$7 eval_json=$8 eval_img=$9 min_free=${10}
  local out="$RUN_ROOT/$dataset/$model" d="$RUN_ROOT/$dataset/$model/layer_$(printf '%02d' "$layer")"
  local shared_d="$SHARED_ROOT/$dataset/$model/layer_$(printf '%02d' "$layer")"
  if [[ -s "$shared_d/SYNC_VERIFIED" && -s "$shared_d/eval_full.done" ]]; then
    log_status "LAYER_SKIP dataset=$dataset model=$model layer=$layer reason=verified_shared_archive"
    return 0
  fi
  if [[ ! -s "$d/train.done" || ! -s "$d/selected_checkpoint.tsv" ]]; then
    run_stage "$dataset" "$model" "$layer" train "$py" "$config" "$train_json" "$train_img" "$eval_json" "$eval_img" "$min_free"
  else
    log_status "TRAIN_SKIP dataset=$dataset model=$model layer=$layer reason=existing_selected"
  fi
  [[ -s "$d/selected_checkpoint.tsv" ]]
  if [[ ! -s "$d/eval_full.done" ]]; then
    run_stage "$dataset" "$model" "$layer" eval "$py" "$config" "$train_json" "$train_img" "$eval_json" "$eval_img" "$min_free"
  else
    log_status "EVAL_SKIP dataset=$dataset model=$model layer=$layer reason=existing_eval"
  fi
  complete_exists "$d"
  cleanup_and_sync "$d" "$dataset" "$model" "$layer"
  printf '%s\n' "$dataset,$model,$layer,complete,0,$(date '+%F %T'),$(date '+%F %T'),,shared_verified_tmp_removed" >>"$CSV"
}

qwen_smoke() {
  local out="$RUN_ROOT/smoke/evqa-pilot500/qwen2.5-vl-3b" log="$RUN_ROOT/logs/qwen_L15_smoke_$(date +%Y%m%d_%H%M%S).log" rc=0
  if [[ -s "$RUN_ROOT/qwen_L15_smoke.done" ]]; then
    log_status "SMOKE_SKIP model=qwen2.5-vl-3b layer=15 reason=existing_success"
    return 0
  fi
  rm -rf -- "$out"
  mkdir -p "$out"
  suspend_llava_launcher
  wait_gpu_ready 48000
  log_status "SMOKE_START model=qwen2.5-vl-3b layer=15 epochs=1 time=$(date '+%F %T %Z')"
  run_watched evqa-pilot500 qwen2.5-vl-3b 15 smoke "$log" "$PY_QWEN" \
    "$RUNNER" --out-root "$out" --layers 15 --epochs 1 --batch-size "$BATCH_SIZE" \
    --model-name qwen2.5-vl-3b --device cuda:0 \
    --train-data "$EVQA_TRAIN" --train-img-root "$EVQA_TRAIN_IMG" \
    --eval-data "$EVQA_EVAL" --eval-img-root "$EVQA_EVAL_IMG" \
    --config-path "$QWEN_CONFIG" --seed "$SEED" --ema-alpha "$EMA_ALPHA" \
    --data-buffer-size "$DATA_BUFFER_SIZE" --keep-top-ckpts 1 --keep-last-ckpts 0 --skip-eval || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    log_status "SMOKE_FAILED model=qwen2.5-vl-3b layer=15 rc=$rc time=$(date '+%F %T %Z')"
    return "$rc"
  fi
  touch "$RUN_ROOT/qwen_L15_smoke.done"
  rm -rf -- "$out"
  log_status "SMOKE_COMPLETE model=qwen2.5-vl-3b layer=15 scratch_removed=1 time=$(date '+%F %T %Z')"
}

if [[ ${SLURM_JOB_ID:-unset} != "$EXPECTED_JOB" ]]; then
  log_status "PRECHECK_FAILED expected_job=$EXPECTED_JOB actual_job=${SLURM_JOB_ID:-unset}"
  exit 2
fi

for required in "$PY_SMOL" "$PY_QWEN" "$PROJ/$RUNNER" "$PROJ/$SMOL_CONFIG" "$PROJ/$QWEN_CONFIG" \
  "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" \
  "$MMKE_VIS_TRAIN" "$MMKE_VIS_EVAL" "$MMKE_IMG"; do
  [[ -e "$required" ]] || { log_status "PRECHECK_FAILED missing=$required"; exit 2; }
done

"$PY_SMOL" - "$EVQA_TRAIN" "$EVQA_EVAL" "$MMKE_VIS_TRAIN" "$MMKE_VIS_EVAL" <<'PY'
import json, sys
counts = [len(json.load(open(p))) for p in sys.argv[1:]]
assert counts == [500, 2093, 214, 293], counts
print('DATASET_COUNTS_OK', counts)
PY

log_status "QUEUE_START job=$SLURM_JOB_ID host=$(hostname) gpu=$GPU_ID order=evqa_smol_L5,mmke_visual_smol_L5,evqa_qwen_L15 time=$(date '+%F %T %Z')"
log_status "COMPARABILITY epochs=$EPOCHS batch_size=$BATCH_SIZE seed=$SEED ema_alpha=$EMA_ALPHA data_buffer=$DATA_BUFFER_SIZE selection=min_finite_ema eval=independent"
log_status "RETENTION keep_during_train=top5_plus_last2 after_eval=selected_only shared_sync=sha256_verified tmp_duplicate=remove"
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits | tee -a "$STATUS"

run_layer evqa-pilot500 smolvlm-1.7b 5 "$PY_SMOL" "$SMOL_CONFIG" "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 40000
run_layer mmke-visual smolvlm-1.7b 5 "$PY_SMOL" "$SMOL_CONFIG" "$MMKE_VIS_TRAIN" "$MMKE_IMG" "$MMKE_VIS_EVAL" "$MMKE_IMG" 40000
qwen_smoke
run_layer evqa-pilot500 qwen2.5-vl-3b 15 "$PY_QWEN" "$QWEN_CONFIG" "$EVQA_TRAIN" "$EVQA_TRAIN_IMG" "$EVQA_EVAL" "$EVQA_EVAL_IMG" 48000

# Layer directories have already been archived and removed.  The remaining
# per-model cache is reproducible and is not needed for evaluation recovery.
for cache in \
  "$RUN_ROOT/evqa-pilot500/smolvlm-1.7b/cache" \
  "$RUN_ROOT/mmke-visual/smolvlm-1.7b/cache" \
  "$RUN_ROOT/evqa-pilot500/qwen2.5-vl-3b/cache" \
  "$RUN_ROOT/smoke"; do
  cache_abs=$(realpath -m "$cache")
  case "$cache_abs" in
    "$RUN_ROOT"/*) rm -rf -- "$cache_abs" ;;
    *) log_status "CACHE_DELETE_REFUSED path=$cache_abs"; exit 4 ;;
  esac
done

touch "$SHARED_ROOT/QUEUE_DONE"
log_status "QUEUE_DONE shared_root=$SHARED_ROOT time=$(date '+%F %T %Z')"
resume_llava_launcher
