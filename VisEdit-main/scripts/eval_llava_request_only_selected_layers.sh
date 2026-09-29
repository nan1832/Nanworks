#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
CONFIG_DIR=${CONFIG_DIR:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/llava}
BRIDGE_ROOT=${BRIDGE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava}
MODEL_NAME=${MODEL_NAME:-llava-v1.5-7b}
CONFIG_FILE_PREFIX=${CONFIG_FILE_PREFIX:-llava-v1.5-7b-bridge-request-only}
DEVICE=${DEVICE:-cuda:0}
CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
LAYERS=${LAYERS:-$(seq 0 31)}
EVAL_SPLITS=${EVAL_SPLITS:-"train_request val_request val_full"}

TRAIN_REQUEST_DATA=${TRAIN_REQUEST_DATA:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json}
VAL_REQUEST_DATA=${VAL_REQUEST_DATA:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_request_only.json}
VAL_FULL_DATA=${VAL_FULL_DATA:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/val/edit_30_bridge_val_full_metrics.json}

export CUDA_VISIBLE_DEVICES

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

selected_file_for_layer() {
  local layer=$1
  local candidates=(
    "$OUT_ROOT/layer_${layer}_target0003/selected_checkpoint.tsv"
    "$OUT_ROOT/layer_${layer}_ep200/selected_checkpoint.tsv"
  )
  local file
  for file in "${candidates[@]}"; do
    if [[ -f "$file" ]]; then
      echo "$file"
      return 0
    fi
  done
  return 1
}

data_path_for_split() {
  local split=$1
  case "$split" in
    train_request) echo "$TRAIN_REQUEST_DATA" ;;
    val_request) echo "$VAL_REQUEST_DATA" ;;
    val_full) echo "$VAL_FULL_DATA" ;;
    *) return 1 ;;
  esac
}

summary="$OUT_ROOT/eval/selected_eval_summary.tsv"
mkdir -p "$(dirname "$summary")"
echo -e "layer\tsplit\tcheckpoint\toutput_root\tstatus" > "$summary.tmp"

for layer in $LAYERS; do
  selected=$(selected_file_for_layer "$layer")
  ckpt=$(tail -n 1 "$selected" | awk -F '\t' '{print $9}')
  cfg="$CONFIG_DIR/${CONFIG_FILE_PREFIX}-l${layer}.yaml"

  if [[ -z "$ckpt" || ! -f "$ckpt" ]]; then
    echo "Selected checkpoint missing for layer=$layer: $ckpt" >&2
    exit 1
  fi
  if [[ ! -f "$cfg" ]]; then
    echo "Missing config for layer=$layer: $cfg" >&2
    exit 1
  fi

  for split in $EVAL_SPLITS; do
    data_path=$(data_path_for_split "$split")
    output_root="$OUT_ROOT/eval/${split}/layer_${layer}"
    manifest="$output_root/eval_manifest.json"
    mkdir -p "$output_root"

    if [[ -f "$manifest" ]]; then
      echo "[$(date '+%F %T')] skip existing eval layer=$layer split=$split"
      echo -e "${layer}\t${split}\t${ckpt}\t${output_root}\tskipped_existing" >> "$summary.tmp"
      continue
    fi

    echo "[$(date '+%F %T')] eval layer=$layer split=$split ckpt=$(basename "$ckpt")"
    "$PYTHON_BIN" scripts/eval_bridge_request_only_ckpt.py \
      --model-name "$MODEL_NAME" \
      --config "$cfg" \
      --ckpt-path "$ckpt" \
      --data-path "$data_path" \
      --eval-name "${split}_l${layer}_target0003" \
      --bridge-root "$BRIDGE_ROOT" \
      --output-root "$output_root" \
      --device "$DEVICE"

    echo -e "${layer}\t${split}\t${ckpt}\t${output_root}\tdone" >> "$summary.tmp"
  done
done

mv "$summary.tmp" "$summary"
echo "[$(date '+%F %T')] all selected checkpoint evaluations finished: $summary"
