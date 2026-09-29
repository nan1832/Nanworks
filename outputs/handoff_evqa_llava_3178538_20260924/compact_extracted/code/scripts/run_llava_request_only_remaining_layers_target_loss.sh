#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}
PYTHON_BIN=${PYTHON_BIN:-/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python3.11}
CONFIG_DIR=${CONFIG_DIR:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/configs/llava}
DATA_PATH=${DATA_PATH:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge/request_only/train/edit_30_bridge_train_request_only.json}
BRIDGE_ROOT=${BRIDGE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge}
OUT_ROOT=${OUT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava}
MODEL_NAME=${MODEL_NAME:-llava-v1.5-7b}
CONFIG_FILE_PREFIX=${CONFIG_FILE_PREFIX:-llava-v1.5-7b-bridge-request-only}
TRAIN_NAME_MODEL_TAG=${TRAIN_NAME_MODEL_TAG:-llava}

TARGET_LOSS=${TARGET_LOSS:-0.0003}
LOSS_TOL=${LOSS_TOL:-0.0001}
INITIAL_EPOCHS=${INITIAL_EPOCHS:-100}
EXTEND_EPOCHS=${EXTEND_EPOCHS:-20}
SAVE_CKPT_PER_I=${SAVE_CKPT_PER_I:-30}
RANDOM_SEED=${RANDOM_SEED:-2026}
CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
DEVICE=${DEVICE:-cuda:0}
DATA_BUFFER_SIZE=${DATA_BUFFER_SIZE:-1}
LAYERS=${LAYERS:-$(seq 2 31)}
CHECK_INTERVAL_SECONDS=${CHECK_INTERVAL_SECONDS:-60}
MIN_CKPT_BYTES=${MIN_CKPT_BYTES:-10485760}
FORCE_SELECT_AT_EPOCHS=${FORCE_SELECT_AT_EPOCHS:-}
LAST_PHASE_LOG=""

export CUDA_VISIBLE_DEVICES

cd "$REPO_ROOT"

summarize_checkpoints() {
  local layer_dir=$1
  local mode=$2
  "$PYTHON_BIN" - "$layer_dir" "$TARGET_LOSS" "$LOSS_TOL" "$mode" <<'PY'
import pathlib
import re
import sys

layer_dir = pathlib.Path(sys.argv[1])
target = float(sys.argv[2])
tol = float(sys.argv[3])
mode = sys.argv[4]

records = []
for path in layer_dir.glob("records/**/checkpoints/epoch-*"):
    match = re.search(r"epoch-(\d+)-i-(\d+)-ema_loss-([0-9.]+)$", path.name)
    if not match:
        continue
    if path.stat().st_size < 10 * 1024 * 1024:
        continue
    epoch = int(match.group(1))
    step = int(match.group(2))
    loss = float(match.group(3))
    diff = abs(loss - target)
    records.append((epoch, step, loss, diff, str(path)))

if not records:
    sys.exit(1)

if mode == "best":
    epoch, step, loss, diff, path = sorted(records, key=lambda x: (x[3], x[0], x[1]))[0]
elif mode == "latest":
    epoch, step, loss, diff, path = sorted(records, key=lambda x: (x[0], x[1]))[-1]
else:
    raise SystemExit(f"unknown mode: {mode}")

status = "ACCEPT" if diff <= tol + 1e-12 else "CONTINUE"
print(f"{status}\t{epoch}\t{step}\t{loss:.4f}\t{diff:.4f}\t{path}")
PY
}

layer_force_select_epoch() {
  local layer=$1
  "$PYTHON_BIN" - "$layer" "$FORCE_SELECT_AT_EPOCHS" <<'PY'
import sys

layer = sys.argv[1]
spec = sys.argv[2].replace(",", " ").split()

for item in spec:
    if ":" not in item:
        continue
    key, value = item.split(":", 1)
    if key == layer:
        print(int(value))
        break
PY
}

write_selected_checkpoint() {
  local selected_file=$1
  local layer=$2
  local selected_status=$3
  local epoch=$4
  local step=$5
  local loss=$6
  local diff=$7
  local path=$8
  {
    echo -e "layer\tstatus\ttarget_loss\ttolerance\tepoch\tstep\tema_loss\tdiff\tcheckpoint"
    echo -e "${layer}\t${selected_status}\t${TARGET_LOSS}\t${LOSS_TOL}\t${epoch}\t${step}\t${loss}\t${diff}\t${path}"
  } > "$selected_file"
}

prune_layer_checkpoints() {
  local layer_dir=$1
  local keep_path=$2
  "$PYTHON_BIN" - "$layer_dir" "$keep_path" <<'PY'
import pathlib
import sys

layer_dir = pathlib.Path(sys.argv[1]).resolve()
keep = pathlib.Path(sys.argv[2]).resolve()

if not layer_dir.exists():
    raise SystemExit(0)

removed = 0
for path in layer_dir.glob("records/**/checkpoints/epoch-*"):
    resolved = path.resolve()
    if resolved == keep:
        continue
    if layer_dir not in resolved.parents:
        raise SystemExit(f"refusing to remove outside layer dir: {resolved}")
    if path.is_file():
        path.unlink()
        removed += 1

print(f"pruned={removed} keep={keep}")
PY
}

cleanup_after_storage_error() {
  local current_layer_dir=$1
  "$PYTHON_BIN" - "$OUT_ROOT" "$current_layer_dir" "$MIN_CKPT_BYTES" <<'PY'
import pathlib
import re
import shutil
import sys

import torch

out = pathlib.Path(sys.argv[1]).resolve()
current = pathlib.Path(sys.argv[2]).resolve()
min_bytes = int(sys.argv[3])

if not out.exists():
    raise SystemExit(f"missing out root: {out}")
if out not in current.parents and current != out:
    raise SystemExit(f"refusing current layer outside out root: {current}")

keep = set()
selected_layer_dirs = set()
for selected in out.glob("**/selected_checkpoint.tsv"):
    try:
        row = selected.read_text().strip().splitlines()[-1].split("\t")
        ckpt = pathlib.Path(row[8]).resolve()
        if out not in ckpt.parents:
            raise SystemExit(f"selected checkpoint outside out root: {ckpt}")
        keep.add(ckpt)
        for parent in ckpt.parents:
            if parent.parent == out and parent.name.startswith("layer_"):
                selected_layer_dirs.add(parent)
                break
    except Exception as exc:
        print(f"WARN cannot parse selected file {selected}: {exc}")

def safe_unlink(path: pathlib.Path) -> int:
    resolved = path.resolve()
    if out not in resolved.parents:
        raise SystemExit(f"refusing to remove outside out root: {resolved}")
    if resolved in keep:
        return 0
    if path.is_file():
        size = path.stat().st_size
        path.unlink()
        return size
    return 0

removed = 0
freed = 0

# Completed layers only need their selected checkpoint for later evaluation.
for layer_dir in selected_layer_dirs:
    for ckpt in layer_dir.glob("records/**/checkpoints/epoch-*"):
        if ckpt.resolve() not in keep:
            freed += safe_unlink(ckpt)
            removed += 1
    cache = layer_dir / "cache"
    if cache.exists():
        if out not in cache.resolve().parents:
            raise SystemExit(f"refusing to remove cache outside out root: {cache}")
        size = sum(p.stat().st_size for p in cache.rglob("*") if p.is_file())
        shutil.rmtree(cache)
        freed += size
        removed += 1

# For the current unfinished layer, keep only the newest loadable checkpoint.
current_keep = None
records = []
for ckpt in current.glob("records/**/checkpoints/epoch-*"):
    match = re.search(r"epoch-(\d+)-i-(\d+)-ema_loss-([0-9.]+)$", ckpt.name)
    if not match:
        continue
    epoch = int(match.group(1))
    step = int(match.group(2))
    loss = float(match.group(3))
    if ckpt.stat().st_size < min_bytes:
        print(f"DELETE_PARTIAL {ckpt}")
        freed += safe_unlink(ckpt)
        removed += 1
        continue
    records.append((epoch, step, loss, ckpt))

for _, _, _, ckpt in sorted(records, key=lambda x: (x[0], x[1]), reverse=True):
    try:
        torch.load(str(ckpt), map_location="cpu")
        current_keep = ckpt.resolve()
        keep.add(current_keep)
        print(f"KEEP_CURRENT_LATEST_GOOD {current_keep}")
        break
    except Exception as exc:
        print(f"DELETE_BAD {ckpt} err={type(exc).__name__}: {exc}")
        freed += safe_unlink(ckpt)
        removed += 1

for _, _, _, ckpt in records:
    if ckpt.resolve() not in keep:
        freed += safe_unlink(ckpt)
        removed += 1

print(f"CLEANUP removed={removed} freed_gib={freed / 1024 / 1024 / 1024:.2f}")
PY
}

phase_failed_for_storage() {
  local phase_log=$1
  [[ -f "$phase_log" ]] && grep -Eqi 'No space left on device|PytorchStreamWriter failed writing file|file write failed|unexpected pos|inline_container' "$phase_log"
}

run_layer_phase() {
  local layer=$1
  local layer_dir=$2
  local end_epoch=$3
  local load_ckpt=${4:-}
  local cfg="$CONFIG_DIR/${CONFIG_FILE_PREFIX}-l${layer}.yaml"
  local phase_stamp
  phase_stamp=$(date '+%Y%m%d_%H%M%S')
  local phase_log="$layer_dir/train_to_epoch_${end_epoch}_${phase_stamp}.log"
  LAST_PHASE_LOG="$phase_log"
  local stopped_for_target=0

  if [[ ! -f "$cfg" ]]; then
    echo "Missing config: $cfg" >&2
    return 1
  fi

  mkdir -p "$layer_dir"
  echo "[$(date '+%F %T')] layer=$layer train_to_epoch=$end_epoch log=$phase_log"

  local cmd=(
    "$PYTHON_BIN" bridge_train_request_only.py
    --model-name "$MODEL_NAME"
    --config "$cfg"
    --data-path "$DATA_PATH"
    --bridge-root "$BRIDGE_ROOT"
    --cache-root "$layer_dir/cache"
    --records-dir "$layer_dir/records"
    --run-config-path "$layer_dir/run_config.json"
    --epochs "$end_epoch"
    --batch-size 1
    --save-ckpt-per-i "$SAVE_CKPT_PER_I"
    --random-seed "$RANDOM_SEED"
    --data-buffer-size "$DATA_BUFFER_SIZE"
    --device "$DEVICE"
    --single-gpu
    --train-name-prefix "bridge_request_only_${TRAIN_NAME_MODEL_TAG}_l${layer}_target0003"
  )

  if [[ -n "$load_ckpt" ]]; then
    cmd+=(--load-ckpt-path "$load_ckpt" --resume-next-epoch)
  else
    cmd+=(--reset-cache)
  fi

  "${cmd[@]}" > "$phase_log" 2>&1 &
  local train_pid=$!
  echo "[$(date '+%F %T')] layer=$layer train_pid=$train_pid"

  while kill -0 "$train_pid" 2>/dev/null; do
    if best_line=$(summarize_checkpoints "$layer_dir" best 2>/dev/null); then
      IFS=$'\t' read -r status best_epoch best_step best_loss best_diff best_path <<< "$best_line"
      if [[ "$status" == "ACCEPT" ]]; then
        echo "[$(date '+%F %T')] layer=$layer target reached during training epoch=$best_epoch loss=$best_loss; stopping pid=$train_pid"
        kill -TERM "$train_pid" 2>/dev/null || true
        stopped_for_target=1
        sleep 8
        if kill -0 "$train_pid" 2>/dev/null; then
          kill -INT "$train_pid" 2>/dev/null || true
          sleep 5
        fi
        if kill -0 "$train_pid" 2>/dev/null; then
          kill -KILL "$train_pid" 2>/dev/null || true
        fi
        break
      fi
    fi
    sleep "$CHECK_INTERVAL_SECONDS"
  done

  if ! wait "$train_pid"; then
    if [[ "$stopped_for_target" == "1" ]]; then
      return 0
    fi
    return 1
  fi
}

for layer in $LAYERS; do
  layer_dir="$OUT_ROOT/layer_${layer}_target0003"
  selected_file="$layer_dir/selected_checkpoint.tsv"
  mkdir -p "$layer_dir"

  if [[ -f "$selected_file" ]]; then
    echo "[$(date '+%F %T')] layer=$layer already selected: $(tail -n 1 "$selected_file")"
    continue
  fi

  echo "[$(date '+%F %T')] ==== layer=$layer start ===="

  while true; do
    force_select_epoch=$(layer_force_select_epoch "$layer")
    if best_line=$(summarize_checkpoints "$layer_dir" best 2>/dev/null); then
      IFS=$'\t' read -r status best_epoch best_step best_loss best_diff best_path <<< "$best_line"
      echo "[$(date '+%F %T')] layer=$layer best status=$status epoch=$best_epoch loss=$best_loss diff=$best_diff path=$best_path"
      if [[ "$status" == "ACCEPT" ]]; then
        write_selected_checkpoint "$selected_file" "$layer" "$status" "$best_epoch" "$best_step" "$best_loss" "$best_diff" "$best_path"
        echo "[$(date '+%F %T')] layer=$layer selected checkpoint saved to $selected_file"
        prune_layer_checkpoints "$layer_dir" "$best_path"
        break
      fi
      if [[ -n "$force_select_epoch" ]] && (( best_epoch >= force_select_epoch )); then
        write_selected_checkpoint "$selected_file" "$layer" "MISS_TARGET" "$best_epoch" "$best_step" "$best_loss" "$best_diff" "$best_path"
        echo "[$(date '+%F %T')] layer=$layer force-selected nearest checkpoint at epoch cap=$force_select_epoch loss=$best_loss diff=$best_diff; saved to $selected_file"
        prune_layer_checkpoints "$layer_dir" "$best_path"
        break
      fi
    fi

    if latest_line=$(summarize_checkpoints "$layer_dir" latest 2>/dev/null); then
      IFS=$'\t' read -r _ latest_epoch latest_step latest_loss latest_diff latest_path <<< "$latest_line"
      if [[ -n "$force_select_epoch" ]] && (( latest_epoch >= force_select_epoch )); then
        if best_line=$(summarize_checkpoints "$layer_dir" best 2>/dev/null); then
          IFS=$'\t' read -r status best_epoch best_step best_loss best_diff best_path <<< "$best_line"
          write_selected_checkpoint "$selected_file" "$layer" "MISS_TARGET" "$best_epoch" "$best_step" "$best_loss" "$best_diff" "$best_path"
          echo "[$(date '+%F %T')] layer=$layer reached epoch cap=$force_select_epoch without target; force-selected epoch=$best_epoch loss=$best_loss diff=$best_diff; saved to $selected_file"
          prune_layer_checkpoints "$layer_dir" "$best_path"
          break
        fi
      fi
      if (( latest_epoch < INITIAL_EPOCHS )); then
        end_epoch=$INITIAL_EPOCHS
      else
        end_epoch=$((latest_epoch + EXTEND_EPOCHS))
      fi
      if [[ -n "$force_select_epoch" ]] && (( end_epoch > force_select_epoch )); then
        end_epoch=$force_select_epoch
      fi
      if run_layer_phase "$layer" "$layer_dir" "$end_epoch" "$latest_path"; then
        phase_status=0
      else
        phase_status=$?
      fi
      if (( phase_status != 0 )); then
        if phase_failed_for_storage "$LAST_PHASE_LOG"; then
          echo "[$(date '+%F %T')] layer=$layer storage write failure detected; cleaning checkpoints/caches and continuing"
          cleanup_after_storage_error "$layer_dir"
          continue
        fi
        echo "[$(date '+%F %T')] layer=$layer failed; see log=$LAST_PHASE_LOG" >&2
        exit "$phase_status"
      fi
    else
      end_epoch=$INITIAL_EPOCHS
      if [[ -n "$force_select_epoch" ]] && (( end_epoch > force_select_epoch )); then
        end_epoch=$force_select_epoch
      fi
      if run_layer_phase "$layer" "$layer_dir" "$end_epoch" ""; then
        phase_status=0
      else
        phase_status=$?
      fi
      if (( phase_status != 0 )); then
        if phase_failed_for_storage "$LAST_PHASE_LOG"; then
          echo "[$(date '+%F %T')] layer=$layer storage write failure detected; cleaning checkpoints/caches and continuing"
          cleanup_after_storage_error "$layer_dir"
          continue
        fi
        echo "[$(date '+%F %T')] layer=$layer failed; see log=$LAST_PHASE_LOG" >&2
        exit "$phase_status"
      fi
    fi
  done
done

echo "[$(date '+%F %T')] all requested layers finished"
