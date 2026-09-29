#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
BRIDGE_ROOT=${BRIDGE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge}
COCO_ROOT=${COCO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_text_only_layer_sweep/llava}
DATA_PATH=${DATA_PATH:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/full_metrics_same_entity/edit_30_bridge_train_request_val_metrics_same_entity_rephrase_split.json}
EVAL_ROOT=${EVAL_ROOT:-}
DEVICE=${DEVICE:-cuda:0}
CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
LAYERS=${LAYERS:-$(seq 0 31)}
SELECTION_MODES=${SELECTION_MODES:-target0003}
MODEL_NAME=${MODEL_NAME:-}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out_root) OUT_ROOT="$2"; shift 2 ;;
    --eval_data) DATA_PATH="$2"; shift 2 ;;
    --eval_root) EVAL_ROOT="$2"; shift 2 ;;
    --selection_modes) SELECTION_MODES="$2"; shift 2 ;;
    --device) DEVICE="$2"; shift 2 ;;
    --layers) LAYERS="$2"; shift 2 ;;
    --bridge_root) BRIDGE_ROOT="$2"; shift 2 ;;
    --coco_root) COCO_ROOT="$2"; shift 2 ;;
    --model_name) MODEL_NAME="$2"; shift 2 ;;
    --python_bin) PYTHON_BIN="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$EVAL_ROOT" ]]; then
  EVAL_ROOT="$OUT_ROOT/eval_same_entity_full_metrics_rephrase_split"
fi
export CUDA_VISIBLE_DEVICES

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p "$EVAL_ROOT"

extract_selection() {
  local summary_json=$1
  local layer=$2
  "$PYTHON_BIN" - "$summary_json" "$layer" <<'PY'
import json
import sys

summary_json, layer = sys.argv[1], str(int(sys.argv[2]))
with open(summary_json, "r", encoding="utf-8") as f:
    data = json.load(f)
item = data["per_layer"][layer]
selected = item["selected"]
print("\t".join([
    selected["path"],
    item.get("status", "SELECTED"),
    str(selected.get("epoch", "")),
    str(selected.get("loss", "")),
    str(item.get("diff", "")),
]))
PY
}

extract_config() {
  local layer=$1
  "$PYTHON_BIN" - "$OUT_ROOT" "$layer" <<'PY'
from pathlib import Path
import sys

out_root, layer = Path(sys.argv[1]), int(sys.argv[2])
matches = sorted((out_root / "generated_configs").glob(f"*bridge-text-only-l{layer:02d}.yaml"))
if not matches:
    raise SystemExit(f"missing generated config for layer {layer}")
print(matches[0])
PY
}

append_metric_row() {
  local layer=$1
  local checkpoint=$2
  local output_root=$3
  local manifest=$4
  local status=$5
  "$PYTHON_BIN" - "$layer" "$checkpoint" "$output_root" "$manifest" "$status" <<'PY'
import json
import sys

layer, ckpt, output_root, manifest_path, status = sys.argv[1:6]
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)
data = manifest["mean_results"]

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
    status,
]
print("\t".join(row))
PY
}

for selection in $SELECTION_MODES; do
  summary_json="$OUT_ROOT/${selection}_ckpt_summary.json"
  summary_tsv="$EVAL_ROOT/${selection}_full_metrics_summary.tsv"
  if [[ ! -f "$summary_json" ]]; then
    echo "Missing checkpoint summary for selection=$selection: $summary_json" >&2
    exit 1
  fi
  echo -e "layer\tcheckpoint\toutput_root\trequest_acc\tgenerality_acc\tgenerality_text_acc\tgenerality_image_acc\tlocality_acc\tlocality_text_acc\tlocality_image_acc\tportability_acc\tportability_1hop_acc\tportability_2hop_acc\tstatus" > "$summary_tsv.tmp"

  for layer in $LAYERS; do
    IFS=$'\t' read -r ckpt status epoch loss diff < <(extract_selection "$summary_json" "$layer")
    cfg=$(extract_config "$layer")
    output_root="$EVAL_ROOT/layer_${layer}/${selection}"
    manifest="$output_root/eval_manifest.json"

    if [[ -z "$ckpt" || ! -f "$ckpt" ]]; then
      echo "Selected checkpoint missing for layer=$layer selection=$selection: $ckpt" >&2
      exit 1
    fi
    if [[ ! -f "$cfg" ]]; then
      echo "Missing config for layer=$layer: $cfg" >&2
      exit 1
    fi
    if [[ ! -f "$DATA_PATH" ]]; then
      echo "Missing eval data: $DATA_PATH" >&2
      exit 1
    fi

    if [[ ! -f "$manifest" ]]; then
      echo "[$(date '+%F %T')] eval text-only full metrics selection=$selection layer=$layer ckpt=$(basename "$ckpt")"
      args=(
        scripts/eval_bridge_text_only_full_metrics.py
        --config "$cfg"
        --ckpt-path "$ckpt"
        --data-path "$DATA_PATH"
        --eval-name "${selection}_same_entity_full_metrics_l${layer}"
        --bridge-root "$BRIDGE_ROOT"
        --coco-root "$COCO_ROOT"
        --output-root "$output_root"
        --device "$DEVICE"
      )
      if [[ -n "$MODEL_NAME" ]]; then
        args+=(--model-name "$MODEL_NAME")
      fi
      "$PYTHON_BIN" "${args[@]}"
    else
      echo "[$(date '+%F %T')] skip existing text-only full metrics selection=$selection layer=$layer"
    fi

    append_metric_row "$layer" "$ckpt" "$output_root" "$manifest" "$status" >> "$summary_tsv.tmp"
  done

  mv "$summary_tsv.tmp" "$summary_tsv"
  if [[ "$selection" == "target0003" ]]; then
    cp "$summary_tsv" "$EVAL_ROOT/selected_full_metrics_summary.tsv"
  fi
  echo "[$(date '+%F %T')] finished selection=$selection summary=$summary_tsv"
done
