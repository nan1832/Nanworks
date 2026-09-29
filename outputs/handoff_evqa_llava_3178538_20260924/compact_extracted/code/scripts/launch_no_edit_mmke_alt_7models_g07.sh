#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}
export CUDA_VISIBLE_DEVICES=1
export CUDA_DEVICE_ORDER=PCI_BUS_ID

PY_MAIN=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
PY_QWEN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
SCRIPT=scripts/eval_mmke_no_edit_alt_7models.py
DATA_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench
MMKE_SPLIT=${MMKE_SPLIT:-eval}
RUN_ROOT=${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_${MMKE_SPLIT}_7models_$(date +%Y%m%d_%H%M%S)}
STATUS="$RUN_ROOT/run_status.log"

mkdir -p "$RUN_ROOT"
echo "NO_EDIT_MMKE_RUN_ROOT=$RUN_ROOT" | tee -a "$STATUS"
echo "NO_EDIT_MMKE_START time=$(date) host=$(hostname) cuda_visible=$CUDA_VISIBLE_DEVICES split=$MMKE_SPLIT" | tee -a "$STATUS"

wait_gpu1_free() {
  local py="$1"
  while true; do
    local used
    local cuda_ok
    used=$(env -u CUDA_VISIBLE_DEVICES nvidia-smi --id=1 --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -dc '0-9')
    if [[ -z "${used:-}" ]]; then
      used=0
    fi
    cuda_ok=$(CUDA_VISIBLE_DEVICES=1 "$py" - <<'PY' 2>/dev/null | tail -n 1
import torch
print("1" if torch.cuda.is_available() and torch.cuda.device_count() > 0 else "0")
PY
)
    if [[ "$used" =~ ^[0-9]+$ && "$used" -lt 10000 && "$cuda_ok" == "1" ]]; then
      echo "GPU1_FREE used_mib=$used cuda_ok=$cuda_ok time=$(date)" | tee -a "$STATUS"
      break
    fi
    echo "WAIT_GPU1 used_mib=${used:-NA} cuda_ok=${cuda_ok:-NA} time=$(date)" | tee -a "$STATUS"
    sleep 300
  done
}

run_one() {
  local task="$1"
  local model="$2"
  local py="$3"
  local out="$RUN_ROOT/$task/alt/$model"
  mkdir -p "$out"
  wait_gpu1_free "$py"
  echo "MODEL_START task=$task model=$model py=$py time=$(date)" | tee -a "$STATUS"
  "$py" - <<PY > "$out/no_edit_eval.log" 2>&1
import os
import runpy
import sys
import torch

print("[launcher-cuda] visible_devices=%s available=%s count=%s" % (
    os.environ.get("CUDA_VISIBLE_DEVICES"),
    torch.cuda.is_available(),
    torch.cuda.device_count(),
), flush=True)
if torch.cuda.is_available():
    torch.cuda.init()
    print("[launcher-cuda] initialized", flush=True)

sys.argv = [
    "$SCRIPT",
    "--task", "$task",
    "--split", "$MMKE_SPLIT",
    "--target-mode", "alt",
    "--model-name", "$model",
    "--data-root", "$DATA_ROOT",
    "--out-root", "$RUN_ROOT",
    "--device", "cuda:0",
    "--overwrite",
]
runpy.run_path("$SCRIPT", run_name="__main__")
PY
  local rc=$?
  echo "MODEL_END task=$task model=$model rc=$rc time=$(date)" | tee -a "$STATUS"
  if [[ $rc -ne 0 ]]; then
    cat > "$out/no_edit_metrics.json" <<EOF
{
  "task": "$task",
  "split": "$MMKE_SPLIT",
  "target_mode": "alt",
  "model": "$model",
  "status": "FAILED",
  "eval_samples": "",
  "Rel": "",
  "T-Gen": "",
  "M-Gen": "",
  "T-Loc": "",
  "M-Loc": "",
  "Average": "",
  "finished_at": "$(date '+%F %T')",
  "result_dir": "$out"
}
EOF
    "$PY_MAIN" "$SCRIPT" --out-root "$RUN_ROOT" --target-mode alt --summarize-only >> "$STATUS" 2>&1 || true
  fi
}

for task in visual entity; do
  run_one "$task" blip2-opt-2.7b "$PY_MAIN"
  run_one "$task" instructblip-vicuna-7b "$PY_MAIN"
  run_one "$task" minigpt-4-vicuna-7b "$PY_MAIN"
  run_one "$task" llava-v1.5-7b "$PY_MAIN"
  run_one "$task" qwen2.5-vl-3b-instruct "$PY_QWEN"
  run_one "$task" paligemma-3b "$PY_MAIN"
  run_one "$task" smolvlm-1.7b "$PY_MAIN"
done

"$PY_MAIN" "$SCRIPT" --out-root "$RUN_ROOT" --target-mode alt --summarize-only >> "$STATUS" 2>&1 || true
echo "NO_EDIT_MMKE_ALL_DONE time=$(date)" | tee -a "$STATUS"
