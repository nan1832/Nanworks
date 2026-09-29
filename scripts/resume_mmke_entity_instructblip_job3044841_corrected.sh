#!/usr/bin/env bash
set -uo pipefail

ROOT=/tmp/ph_teacher3/mmke_entity_job3044841_20260715_121700
OUT="$ROOT/instructblip-vicuna-7b"
PROJECT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
RUNNER="$PROJECT/scripts/run_evqa_pilot500_blip2_visedit_sweep.py"
TRAIN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json
EVAL=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_eval_evqa_compat.json
IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image
CONFIG=configs/vead/instructblip-vicuna-7b.yaml
STATUS="$ROOT/instructblip_resume_buffer_fallback_status.log"
CSV="$ROOT/instructblip_resume_buffer_fallback_layers.csv"
LOCK="$ROOT/instructblip_resume_buffer_fallback.lock"
NO_PROGRESS_LIMIT=7200
TARGET_GPU_UUID=GPU-eb6299da-bc55-564d-9cc5-cbfa5530d590
GPU_READY_MAX_MIB=1024

export CUDA_VISIBLE_DEVICES=0
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

mkdir -p "$OUT"
exec 9>"$LOCK"
if ! flock -n 9; then
    printf '%s launcher_already_running\n' "$(date '+%F %T')" >> "$STATUS"
    exit 75
fi

if [[ ! -f "$CSV" ]]; then
    printf 'layer,attempt,buffer_size,rc,start_time,end_time,log,note\n' > "$CSV"
fi

status() {
    printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$STATUS"
}

wait_for_target_gpu() {
    local used stable=0
    while (( stable < 3 )); do
        used=$(nvidia-smi -i "$TARGET_GPU_UUID" \
            --query-gpu=memory.used --format=csv,noheader,nounits \
            | tr -d ' ')
        if [[ "$used" =~ ^[0-9]+$ ]] && (( used <= GPU_READY_MAX_MIB )); then
            stable=$((stable + 1))
            status "GPU_READY_PROBE physical_uuid=$TARGET_GPU_UUID used_mib=$used stable=$stable/3"
            sleep 20
        else
            stable=0
            status "GPU_WAIT physical_uuid=$TARGET_GPU_UUID used_mib=${used:-unknown} threshold_mib=$GPU_READY_MAX_MIB"
            sleep 60
        fi
    done
    status "GPU_READY_CONFIRMED physical_uuid=$TARGET_GPU_UUID"
}

stop_owned_child() {
    local pid=$1
    kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 30); do
        kill -0 "$pid" 2>/dev/null || return 0
        sleep 1
    done
    kill -KILL "$pid" 2>/dev/null || true
}

run_attempt() {
    local layer=$1
    local buffer_size=$2
    local attempt=$3
    local stamp log start_epoch now_epoch last_progress progress last_progress_hash
    stamp=$(date '+%Y%m%d_%H%M%S')
    log="$OUT/train_eval_L${layer}_buffer${buffer_size}_${stamp}.log"
    start_epoch=$(date +%s)
    last_progress=$start_epoch
    last_progress_hash=""

    status "ATTEMPT_START layer=$layer attempt=$attempt buffer_size=$buffer_size log=$log gpu=$(nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ' ')"
    cd "$PROJECT" || return 70
    "$PY" "$RUNNER" \
        --out-root "$OUT" \
        --layers "$layer" \
        --epochs 50 \
        --batch-size 2 \
        --model-name instructblip-vicuna-7b \
        --device cuda:0 \
        --train-data "$TRAIN" \
        --train-img-root "$IMG" \
        --eval-data "$EVAL" \
        --eval-img-root "$IMG" \
        --config-path "$CONFIG" \
        --seed 20260601 \
        --ema-alpha 0.1 \
        --data-buffer-size "$buffer_size" \
        --keep-top-ckpts 5 \
        --keep-last-ckpts 2 \
        > "$log" 2>&1 &
    local pid=$!

    while kill -0 "$pid" 2>/dev/null; do
        sleep 60
        if grep -aqE 'CUDA out of memory|OutOfMemoryError' "$log"; then
            status "OOM_DETECTED layer=$layer attempt=$attempt buffer_size=$buffer_size pid=$pid"
            stop_owned_child "$pid"
            wait "$pid" 2>/dev/null || true
            printf '%s,%s,%s,42,%s,%s,%s,oom\n' "$layer" "$attempt" "$buffer_size" "$(date -d "@$start_epoch" '+%F %T')" "$(date '+%F %T')" "$log" >> "$CSV"
            return 42
        fi

        progress=$(tr '\r' '\n' < "$log" | grep -av 'Waiting data:' | tail -n 1 | sha256sum | awk '{print $1}')
        if [[ -n "$progress" && "$progress" != "${last_progress_hash:-}" ]]; then
            last_progress_hash=$progress
            last_progress=$(date +%s)
        fi
        now_epoch=$(date +%s)
        if (( now_epoch - last_progress >= NO_PROGRESS_LIMIT )); then
            status "NO_PROGRESS_2H layer=$layer attempt=$attempt buffer_size=$buffer_size pid=$pid"
            stop_owned_child "$pid"
            wait "$pid" 2>/dev/null || true
            printf '%s,%s,%s,43,%s,%s,%s,no_progress_2h\n' "$layer" "$attempt" "$buffer_size" "$(date -d "@$start_epoch" '+%F %T')" "$(date '+%F %T')" "$log" >> "$CSV"
            return 43
        fi
    done

    wait "$pid"
    local rc=$?
    if [[ $rc -eq 0 ]] \
        && [[ -s "$OUT/layer_$(printf '%02d' "$layer")/selected_checkpoint.tsv" ]] \
        && [[ -s "$OUT/layer_$(printf '%02d' "$layer")/eval_full.done" ]] \
        && grep -q '"eval_samples": 954' "$OUT/layer_$(printf '%02d' "$layer")/eval_full.done"; then
        status "LAYER_DONE layer=$layer attempt=$attempt buffer_size=$buffer_size eval_samples=954"
        printf '%s,%s,%s,0,%s,%s,%s,train_and_eval_done\n' "$layer" "$attempt" "$buffer_size" "$(date -d "@$start_epoch" '+%F %T')" "$(date '+%F %T')" "$log" >> "$CSV"
        return 0
    fi

    status "ATTEMPT_FAILED layer=$layer attempt=$attempt buffer_size=$buffer_size rc=$rc markers_incomplete=1"
    printf '%s,%s,%s,%s,%s,%s,%s,failed_or_incomplete_markers\n' "$layer" "$attempt" "$buffer_size" "$rc" "$(date -d "@$start_epoch" '+%F %T')" "$(date '+%F %T')" "$log" >> "$CSV"
    if [[ $rc -eq 0 ]]; then
        return 44
    fi
    return "$rc"
}

run_layer() {
    local layer=$1
    local initial_buffer=$2
    run_attempt "$layer" "$initial_buffer" 1
    local rc=$?
    if [[ $rc -eq 0 ]]; then
        return 0
    fi
    if [[ $rc -eq 42 && $initial_buffer -gt 1 ]]; then
        status "SERIAL_FALLBACK layer=$layer from_buffer=$initial_buffer to_buffer=1"
        run_attempt "$layer" 1 2
        return $?
    fi
    return "$rc"
}

status "LAUNCHER_START host=$(hostname) job=3044841 model=instructblip-vicuna-7b reason=retry_after_paligemma_gpu_collision config_unchanged=1 batch_size=2 epochs=50 seed=20260601 queue=1,23,24,22,25"
wait_for_target_gpu

# L1 already exhausted buffer=4 before the collision, so restart it directly
# with serialized data preparation. The later layers retain buffer=4 and only
# fall back to buffer=1 after an OOM from their own process on an otherwise
# idle physical GPU1.
run_layer 1 1
rc=$?
if [[ $rc -ne 0 ]]; then
    status "LAYER_FAILED_CONTINUE layer=1 rc=$rc"
fi
for layer in 23 24 22 25; do
    run_layer "$layer" 4
    rc=$?
    if [[ $rc -ne 0 ]]; then
        status "LAYER_FAILED_CONTINUE layer=$layer rc=$rc"
    fi
done

status "LAUNCHER_END"
