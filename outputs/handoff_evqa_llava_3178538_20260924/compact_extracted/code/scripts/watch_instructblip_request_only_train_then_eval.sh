#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
DEVICE=${DEVICE:-cuda:0}

export CUDA_VISIBLE_DEVICES DEVICE PYTHON_BIN OUT_ROOT

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$OUT_ROOT"

echo "[$(date '+%F %T')] InstructBLIP request-only sweep start"
echo "OUT_ROOT=$OUT_ROOT"
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES DEVICE=$DEVICE"

"$PYTHON_BIN" scripts/generate_bridge_request_only_yaml.py \
  --output-root /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs \
  --layers 0-31

bash scripts/run_instructblip_request_only_remaining_layers_target_loss.sh \
  2>&1 | tee "$OUT_ROOT/full_layer_target0003_sweep.log"

bash scripts/eval_instructblip_same_entity_full_metrics_selected_layers.sh \
  2>&1 | tee "$OUT_ROOT/full_layer_same_entity_full_metrics_eval.log"

"$PYTHON_BIN" scripts/render_instructblip_request_only_results_md.py \
  --out-root "$OUT_ROOT" \
  --output-md "$OUT_ROOT/instructblip_results_append.md"

echo "[$(date '+%F %T')] InstructBLIP request-only sweep and eval finished"
echo "append_md=$OUT_ROOT/instructblip_results_append.md"
