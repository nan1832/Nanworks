#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
CONFIG_DIR=${CONFIG_DIR:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/llava}
BRIDGE_ROOT=${BRIDGE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava}
MODEL_NAME=${MODEL_NAME:-llava-v1.5-7b}
CONFIG_FILE_PREFIX=${CONFIG_FILE_PREFIX:-llava-v1.5-7b-bridge-request-only}
DATA_PATH=${DATA_PATH:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json}
EVAL_ROOT=${EVAL_ROOT:-$OUT_ROOT/eval_same_entity_full_metrics_rephrase_split}
DEVICE=${DEVICE:-cuda:0}
CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
LAYERS=${LAYERS:-$(seq 0 31)}

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

result_json_for_layer() {
  local layer=$1
  echo "$EVAL_ROOT/layer_${layer}/vead/${MODEL_NAME}/same_entity_full_metrics_l${layer}/single_edit/mean_results.json"
}

summary="$EVAL_ROOT/selected_full_metrics_summary.tsv"
mkdir -p "$EVAL_ROOT"
echo -e "layer\tcheckpoint\toutput_root\trequest_acc\tgenerality_acc\tgenerality_text_acc\tgenerality_image_acc\tlocality_acc\tlocality_text_acc\tlocality_image_acc\tportability_acc\tportability_1hop_acc\tportability_2hop_acc\tstatus" > "$summary.tmp"

for layer in $LAYERS; do
  selected=$(selected_file_for_layer "$layer")
  ckpt=$(tail -n 1 "$selected" | awk -F '\t' '{print $9}')
  cfg="$CONFIG_DIR/${CONFIG_FILE_PREFIX}-l${layer}.yaml"
  output_root="$EVAL_ROOT/layer_${layer}"
  manifest="$output_root/eval_manifest.json"
  result_json=$(result_json_for_layer "$layer")

  if [[ -z "$ckpt" || ! -f "$ckpt" ]]; then
    echo "Selected checkpoint missing for layer=$layer: $ckpt" >&2
    exit 1
  fi
  if [[ ! -f "$cfg" ]]; then
    echo "Missing config for layer=$layer: $cfg" >&2
    exit 1
  fi
  if [[ ! -f "$DATA_PATH" ]]; then
    echo "Missing data path: $DATA_PATH" >&2
    exit 1
  fi

  if [[ ! -f "$manifest" ]]; then
    echo "[$(date '+%F %T')] eval same-entity full metrics layer=$layer ckpt=$(basename "$ckpt")"
    "$PYTHON_BIN" scripts/eval_bridge_full_metrics_ckpt.py \
      --model-name "$MODEL_NAME" \
      --config "$cfg" \
      --ckpt-path "$ckpt" \
      --data-path "$DATA_PATH" \
      --eval-name "same_entity_full_metrics_l${layer}" \
      --bridge-root "$BRIDGE_ROOT" \
      --output-root "$output_root" \
      --device "$DEVICE"
  else
    echo "[$(date '+%F %T')] skip existing same-entity full metrics eval layer=$layer"
  fi

  "$PYTHON_BIN" - "$layer" "$ckpt" "$output_root" "$result_json" <<'PY' >> "$summary.tmp"
import json
import pathlib
import sys

layer, ckpt, output_root, result_json = sys.argv[1:5]
path = pathlib.Path(result_json)
if not path.exists():
    raise SystemExit(f"missing mean_results: {path}")
data = json.loads(path.read_text(encoding="utf-8"))

def fmt(value):
    if value is None or value == "":
        return ""
    return f"{float(value):.4f}"

row = [
    layer,
    ckpt,
    output_root,
    fmt(data.get("reliability", {}).get("acc")),
    fmt(data.get("generality", {}).get("overall", {}).get("acc")),
    fmt(data.get("generality", {}).get("text_rephrase", {}).get("acc")),
    fmt(data.get("generality", {}).get("image_rephrase", {}).get("acc")),
    fmt(data.get("locality", {}).get("overall", {}).get("acc")),
    fmt(data.get("locality", {}).get("text_loc", {}).get("acc")),
    fmt(data.get("locality", {}).get("image_loc", {}).get("acc")),
    fmt(data.get("portability", {}).get("overall", {}).get("acc")),
    fmt(data.get("portability", {}).get("1hop", {}).get("acc")),
    fmt(data.get("portability", {}).get("2hop", {}).get("acc")),
    "done",
]
print("\t".join(row))
PY
done

mv "$summary.tmp" "$summary"
echo "[$(date '+%F %T')] all same-entity full metrics evaluations finished: $summary"
