#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

export CONFIG_DIR=${CONFIG_DIR:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/instructblip}
export OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/instructblip}
export MODEL_NAME=${MODEL_NAME:-instructblip-vicuna-7b}
export CONFIG_FILE_PREFIX=${CONFIG_FILE_PREFIX:-instructblip-vicuna-7b-bridge-request-only}
export EVAL_ROOT=${EVAL_ROOT:-$OUT_ROOT/eval_same_entity_full_metrics_rephrase_split}
export LAYERS=${LAYERS:-$(seq 0 31)}

exec bash "$SCRIPT_DIR/eval_blip2_same_entity_full_metrics_selected_layers.sh"
