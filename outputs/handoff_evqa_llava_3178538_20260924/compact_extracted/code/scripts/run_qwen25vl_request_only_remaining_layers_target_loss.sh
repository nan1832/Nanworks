#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

export PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}
export CONFIG_DIR=${CONFIG_DIR:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/qwen2_5_vl}
export OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/qwen2_5_vl_7b_instruct}
export MODEL_NAME=${MODEL_NAME:-qwen2.5-vl-7b-instruct}
export CONFIG_FILE_PREFIX=${CONFIG_FILE_PREFIX:-qwen2.5-vl-7b-instruct-bridge-request-only}
export TRAIN_NAME_MODEL_TAG=${TRAIN_NAME_MODEL_TAG:-qwen25vl}
export LAYERS=${LAYERS:-$(seq 0 27)}
export FORCE_SELECT_AT_EPOCHS=${FORCE_SELECT_AT_EPOCHS:-$(for l in $(seq 0 27); do printf "%s:700 " "$l"; done)}
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}

exec bash "$SCRIPT_DIR/run_llava_request_only_remaining_layers_target_loss.sh"
