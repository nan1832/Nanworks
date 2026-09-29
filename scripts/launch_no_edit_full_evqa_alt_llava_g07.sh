#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}
export CUDA_VISIBLE_DEVICES=1
export CUDA_DEVICE_ORDER=PCI_BUS_ID

PY_MAIN=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
SCRIPT=scripts/eval_evqa_no_edit_full_alt.py
EVAL_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
EVAL_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
RUN_ROOT=${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148}
STATUS="$RUN_ROOT/llava_rerun_status.log"
OUT="$RUN_ROOT/llava-v1.5-7b"

mkdir -p "$OUT"
echo "LLAVA_RERUN_ROOT=$RUN_ROOT" | tee -a "$STATUS"
echo "LLAVA_RERUN_START time=$(date) host=$(hostname) cuda_visible=$CUDA_VISIBLE_DEVICES" | tee -a "$STATUS"

echo "MODEL_START model=llava-v1.5-7b time=$(date)" | tee -a "$STATUS"
"$PY_MAIN" - <<PY > "$OUT/no_edit_eval_rerun_full.log" 2>&1
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
    "--model-name", "llava-v1.5-7b",
    "--out-root", "$RUN_ROOT",
    "--eval-data", "$EVAL_JSON",
    "--eval-img-root", "$EVAL_IMG",
    "--device", "cuda:0",
    "--overwrite",
]
runpy.run_path("$SCRIPT", run_name="__main__")
PY
rc=$?
echo "MODEL_END model=llava-v1.5-7b rc=$rc time=$(date)" | tee -a "$STATUS"

if [[ $rc -ne 0 ]]; then
  cat > "$OUT/no_edit_metrics.json" <<EOF
{
  "model": "llava-v1.5-7b",
  "status": "FAILED",
  "eval_samples": "",
  "Rel": "",
  "T-Gen": "",
  "M-Gen": "",
  "T-Loc": "",
  "M-Loc": "",
  "Average": "",
  "finished_at": "$(date '+%F %T')",
  "result_dir": "$OUT"
}
EOF
fi

"$PY_MAIN" "$SCRIPT" --out-root "$RUN_ROOT" --summarize-only >> "$STATUS" 2>&1 || true
echo "LLAVA_RERUN_DONE time=$(date)" | tee -a "$STATUS"
