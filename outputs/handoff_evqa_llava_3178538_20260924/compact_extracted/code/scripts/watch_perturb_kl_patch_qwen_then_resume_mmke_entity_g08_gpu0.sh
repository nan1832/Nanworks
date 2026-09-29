#!/usr/bin/env bash
set -u

PROJECT_ROOT="${PROJECT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
SERVER_RESULTS="${SERVER_RESULTS:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results}"
RUN_ROOT="${PERTURB_KL_RUN_ROOT:-${SERVER_RESULTS}/perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701}"
PY_BASE="${PY_BASE:-/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python}"
PY_QWEN="${PY_QWEN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
MAIN_PID="${MAIN_PID:-}"
LOG_ROOT="${RUN_ROOT}/logs"
PATCH_FAILED_TSV="${RUN_ROOT}/qwen_patch_failed_jobs.tsv"

mkdir -p "$LOG_ROOT"
cd "$PROJECT_ROOT" || exit 2

export PATH="/usr/bin:/usr/local/cuda/bin:${PATH:-}"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

echo "[QWEN_PATCH_START] $(date)"
echo "[INFO] host=$(hostname) CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
echo "[INFO] run_root=${RUN_ROOT}"
echo "[INFO] py_qwen=${PY_QWEN}"
echo "[INFO] py_base=${PY_BASE}"

if [[ -z "$MAIN_PID" ]]; then
  MAIN_PID="$(pgrep -af 'run_perturb_kl_direct_then_resume_mmke_entity_g08_gpu0_safe.sh' | awk '{print $1}' | sort -n | head -n 1 || true)"
fi

if [[ -n "$MAIN_PID" ]]; then
  echo "[WAIT_MAIN] pid=${MAIN_PID}"
  while kill -0 "$MAIN_PID" 2>/dev/null; do
    sleep "${WAIT_INTERVAL_SEC:-300}"
  done
  echo "[MAIN_DONE] pid=${MAIN_PID} $(date)"
else
  echo "[WAIT_MAIN_SKIPPED] no main pid found"
fi

if [[ ! -x "$PY_QWEN" ]]; then
  echo "[QWEN_ENV_MISSING] $PY_QWEN"
  exit 10
fi

set +e
"$PY_QWEN" -c 'from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration; print("Qwen2.5-VL import: OK")'
env_rc=$?
set -e
if [[ "$env_rc" -ne 0 ]]; then
  echo "[QWEN_ENV_BAD] import failed rc=${env_rc}"
  exit 11
fi

echo -e "dataset\tmodel\trc\tlog" > "$PATCH_FAILED_TSV"

QWEN_DATASETS=(
  evqa-pilot500
  mmke-visual
  mmke-entity
)

summary_is_done() {
  local summary_path="$1"
  [[ -f "$summary_path" ]] || return 1
  "$PY_QWEN" - "$summary_path" <<'PY'
import json, sys
p = sys.argv[1]
try:
    data = json.load(open(p, encoding="utf-8"))
except Exception:
    sys.exit(1)
sys.exit(0 if data.get("status") == "done" else 1)
PY
}

for dataset in "${QWEN_DATASETS[@]}"; do
  model="qwen2.5-vl-3b"
  out_dir="${RUN_ROOT}/${dataset}/${model}"
  log_file="${LOG_ROOT}/${dataset}__${model}.qwen_patch.log"
  mkdir -p "$out_dir"

  if [[ -f "${out_dir}/DONE" ]] && summary_is_done "${out_dir}/summary.json"; then
    echo "[SKIP_QWEN_DONE] dataset=${dataset} model=${model}"
    continue
  fi

  echo "[RUN_QWEN_PATCH] $(date) dataset=${dataset} model=${model} log=${log_file}"
  set +e
  "$PY_QWEN" scripts/run_perturb_kl_direct_candidate_layers.py run-one \
    --dataset-name "$dataset" \
    --model-name "$model" \
    --out-dir "$out_dir" \
    --device cuda:0 \
    --noise-scales "${NOISE_SCALES:-0.1,0.5,1,3}" \
    --repeats "${PERTURB_REPEATS:-2026,2027,2028}" \
    --resume \
    > "$log_file" 2>&1
  rc=$?
  set -e

  if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL_QWEN_PATCH] dataset=${dataset} model=${model} rc=${rc}; see ${log_file}"
    echo -e "${dataset}\t${model}\t${rc}\t${log_file}" >> "$PATCH_FAILED_TSV"
  else
    echo "[DONE_QWEN_PATCH] dataset=${dataset} model=${model}"
  fi

  "$PY_QWEN" scripts/run_perturb_kl_direct_candidate_layers.py collect \
    --run-root "$RUN_ROOT" \
    > "${LOG_ROOT}/collect_qwen_patch_latest.log" 2>&1 || true

  nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits || true
done

"$PY_QWEN" scripts/run_perturb_kl_direct_candidate_layers.py collect \
  --run-root "$RUN_ROOT" \
  > "${LOG_ROOT}/collect_qwen_patch_final.log" 2>&1 || true

DONE_COUNT=$(find "$RUN_ROOT" -mindepth 3 -maxdepth 3 -type f -name DONE | wc -l)
SUMMARY_COUNT=$(find "$RUN_ROOT" -mindepth 3 -maxdepth 3 -type f -name summary.json | wc -l)
PATCH_FAIL_COUNT=$(awk 'NR>1 && NF>0 {n++} END {print n+0}' "$PATCH_FAILED_TSV")
FAILED_SUMMARY_COUNT=$(grep -RIl --include='summary.json' '"status": "failed"' "$RUN_ROOT" 2>/dev/null | wc -l)

echo "[QWEN_PATCH_FINAL_CHECK] done=${DONE_COUNT}/21 summaries=${SUMMARY_COUNT}/21 patch_failures=${PATCH_FAIL_COUNT} failed_summaries=${FAILED_SUMMARY_COUNT}"

if [[ "$DONE_COUNT" -ne 21 || "$SUMMARY_COUNT" -ne 21 || "$PATCH_FAIL_COUNT" -ne 0 || "$FAILED_SUMMARY_COUNT" -ne 0 ]]; then
  echo "[RESUME_MMKE_ENTITY_SKIPPED_AFTER_QWEN_PATCH] Candidate-layer experiments are incomplete or failed."
  cat "$PATCH_FAILED_TSV" || true
  exit 4
fi

echo "[RESUME_MMKE_ENTITY_AFTER_QWEN_PATCH] $(date)"

if [[ -x scripts/resume_mmke_entity_top3_nonpali_g07.sh ]]; then
  set +e
  GPU_ID=0 MAX_USED_MIB="${MAX_USED_MIB:-4096}" PY_BASE="$PY_BASE" \
    bash scripts/resume_mmke_entity_top3_nonpali_g07.sh \
    > "${RUN_ROOT}/resume_mmke_entity_after_qwen_patch.log" 2>&1
  resume_rc=$?
  set -e
  echo "[RESUME_MMKE_ENTITY_AFTER_QWEN_PATCH_DONE] rc=${resume_rc} $(date)"
  exit "$resume_rc"
else
  echo "[RESUME_MMKE_ENTITY_MISSING] scripts/resume_mmke_entity_top3_nonpali_g07.sh"
  exit 3
fi
