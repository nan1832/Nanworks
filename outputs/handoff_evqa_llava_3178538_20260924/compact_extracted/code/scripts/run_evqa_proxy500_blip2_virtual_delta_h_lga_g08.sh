#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python}
DATA_ROOT=${DATA_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528}
TRAIN_DATA=${TRAIN_DATA:-$DATA_ROOT/data/vqa_train_proxy500.json}
IMG_ROOT=${IMG_ROOT:-$DATA_ROOT/images}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy500_blip2_virtual_delta_h_lga_$(date +%Y%m%d_%H%M%S)}
GPU_ID=${GPU_ID:-0}
MAX_GPU_MEM_MB=${MAX_GPU_MEM_MB:-2000}
MAX_GPU_UTIL=${MAX_GPU_UTIL:-20}
RUN_BACKGROUND=${RUN_BACKGROUND:-1}

cd "$REPO_ROOT"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found; refusing to start without GPU visibility check." >&2
  exit 1
fi

gpu_row=$(nvidia-smi -i "$GPU_ID" --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | head -n 1 | tr -d ' ')
gpu_mem=${gpu_row%,*}
gpu_util=${gpu_row#*,}
gpu_proc_count=$(nvidia-smi -i "$GPU_ID" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null | sed '/^$/d' | wc -l)

echo "node=$(hostname) gpu=${GPU_ID} status: memory.used=${gpu_mem}MiB utilization=${gpu_util}% compute_processes=${gpu_proc_count}"
if [ "$gpu_proc_count" -gt 0 ] || [ "$gpu_mem" -gt "$MAX_GPU_MEM_MB" ] || [ "$gpu_util" -gt "$MAX_GPU_UTIL" ]; then
  echo "GPU ${GPU_ID} on node $(hostname) is not idle enough; refusing to start. Node g07 is intentionally untouched." >&2
  exit 2
fi

mkdir -p "$OUT_ROOT/data"

"$PYTHON_BIN" scripts/prepare_evqa_proxy500_virtual_delta_h_inputs.py \
  --evqa-path "$TRAIN_DATA" \
  --out-dir "$OUT_ROOT/data" \
  --max-samples 500

export CUDA_VISIBLE_DEVICES="$GPU_ID"
export TOKENIZERS_PARALLELISM=false

log_path="$OUT_ROOT/run.log"
echo "Starting BLIP2 proxy500 virtual-delta-h LGA on node $(hostname), CUDA_VISIBLE_DEVICES=${GPU_ID}; log=${log_path}"

cmd=(
  "$PYTHON_BIN" scripts/bridge_vlm_virtual_delta_h_lga_scan.py
  --model-name blip2-opt-2.7b
  --config-path configs/vead/blip2-opt-2.7b.yaml
  --data-path "$OUT_ROOT/data/evqa_proxy500_request_only_bridge_format.json"
  --bridge-root "$IMG_ROOT"
  --old-answers-path "$OUT_ROOT/data/evqa_proxy500_old_answers_from_pred.jsonl"
  --layers 0-31
  --output-dir "$OUT_ROOT"
  --device cuda:0
  --torch-dtype float16
  --max-samples 500
)

if [ "$RUN_BACKGROUND" = "1" ]; then
  nohup "${cmd[@]}" > "$log_path" 2>&1 &
  pid=$!
  echo "$pid" > "$OUT_ROOT/run.pid"
  echo "Started PID=$pid"
else
  echo "$$" > "$OUT_ROOT/run.pid"
  "${cmd[@]}" 2>&1 | tee "$log_path"
fi
echo "Output dir: $OUT_ROOT"
echo "Follow log: tail -f $log_path"
