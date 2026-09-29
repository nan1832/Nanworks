#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

export CONFIG_DIR=${CONFIG_DIR:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/blip2}
export OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2}
export MODEL_NAME=${MODEL_NAME:-blip2-opt-2.7b}
export CONFIG_FILE_PREFIX=${CONFIG_FILE_PREFIX:-blip2-opt-2.7b-bridge-request-only}
export LAYERS=${LAYERS:-$(seq 0 31)}

exec bash "$SCRIPT_DIR/eval_llava_request_only_selected_layers.sh"
