#!/usr/bin/env bash
set -euo pipefail

REPO=${REPO:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
OUT=${OUT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip}
SLEEP_SECONDS=${SLEEP_SECONDS:-300}

cd "$REPO"
mkdir -p "$OUT"

echo "[$(date '+%F %T')] supervisor started on $(hostname)"
echo "waiting for GPU compute apps to clear before InstructBLIP sweep"

while true; do
  apps=$(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits 2>/dev/null | sed "/^$/d" || true)
  if [ -z "$apps" ]; then
    echo "[$(date '+%F %T')] GPU idle; starting InstructBLIP sweep"
    break
  fi
  echo "[$(date '+%F %T')] GPU busy:"
  echo "$apps"
  sleep "$SLEEP_SECONDS"
done

export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
export DEVICE=${DEVICE:-cuda:0}
export PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
export CHECK_INTERVAL_SECONDS=${CHECK_INTERVAL_SECONDS:-60}

bash scripts/watch_instructblip_request_only_train_then_eval.sh
