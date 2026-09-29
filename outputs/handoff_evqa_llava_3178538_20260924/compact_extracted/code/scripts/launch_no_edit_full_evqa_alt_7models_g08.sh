#!/usr/bin/env bash
set -u

cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
export PYTHONPATH=$PWD:${PYTHONPATH:-}
export CUDA_VISIBLE_DEVICES=1

PY_MAIN=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python
PY_QWEN=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
SCRIPT=scripts/eval_evqa_no_edit_full_alt.py
EVAL_JSON=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
EVAL_IMG=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
RUN_ROOT=${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_$(date +%Y%m%d_%H%M%S)}
STATUS="$RUN_ROOT/run_status.log"

mkdir -p "$RUN_ROOT"
echo "NO_EDIT_RUN_ROOT=$RUN_ROOT" | tee -a "$STATUS"
echo "NO_EDIT_START time=$(date) host=$(hostname) cuda_visible=$CUDA_VISIBLE_DEVICES" | tee -a "$STATUS"

top3_pattern='launch_fixed_llava_pali_smol_top3_gpu1.sh|launch_minigpt4_after_fixed_gpu1.sh|launch_qwen_after_minigpt_gpu1.sh|run_evqa_pilot500_blip2_visedit_sweep.py'
while pgrep -u ph_teacher3 -f "$top3_pattern" >/dev/null 2>&1; do
  echo "WAIT_TOP3_CHAIN time=$(date)" | tee -a "$STATUS"
  sleep 600
done

wait_gpu1_free() {
  while true; do
    local used
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1 2>/dev/null | tr -d ' ')
    if [[ -n "${used:-}" && "$used" -lt 10000 ]]; then
      echo "GPU1_FREE used_mib=$used time=$(date)" | tee -a "$STATUS"
      break
    fi
    echo "WAIT_GPU1 used_mib=${used:-NA} time=$(date)" | tee -a "$STATUS"
    sleep 300
  done
}

run_model() {
  local model="$1"
  local py="$2"
  local out="$RUN_ROOT/$model"
  mkdir -p "$out"
  wait_gpu1_free
  echo "MODEL_START model=$model py=$py time=$(date)" | tee -a "$STATUS"
  "$py" "$SCRIPT" \
    --model-name "$model" \
    --out-root "$RUN_ROOT" \
    --eval-data "$EVAL_JSON" \
    --eval-img-root "$EVAL_IMG" \
    --device cuda:0 \
    > "$out/no_edit_eval.log" 2>&1
  local rc=$?
  echo "MODEL_END model=$model rc=$rc time=$(date)" | tee -a "$STATUS"
  if [[ $rc -ne 0 ]]; then
    cat > "$out/no_edit_metrics.json" <<EOF
{
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
  fi
  "$PY_MAIN" "$SCRIPT" --out-root "$RUN_ROOT" --summarize-only >> "$STATUS" 2>&1 || true
}

run_model instructblip-vicuna-7b "$PY_MAIN"
run_model blip2-opt-2.7b "$PY_MAIN"
run_model minigpt-4-vicuna-7b "$PY_MAIN"
run_model llava-v1.5-7b "$PY_MAIN"
run_model paligemma-3b "$PY_MAIN"
run_model smolvlm-1.7b "$PY_MAIN"
run_model qwen2.5-vl-3b-instruct "$PY_QWEN"

"$PY_MAIN" "$SCRIPT" --out-root "$RUN_ROOT" --summarize-only >> "$STATUS" 2>&1 || true
echo "NO_EDIT_ALL_DONE time=$(date)" | tee -a "$STATUS"
