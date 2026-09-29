#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${JOB_ID:-3044841}"
PYTHON_BIN="${PYTHON_BIN:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python}"
PROJECT_ROOT="${PROJECT_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main}"
MMKE_ROOT="${MMKE_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench}"
RUN_ROOT="${RUN_ROOT:-/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_keytoken_mmke_7models_$(date +%Y%m%d_%H%M%S)}"
DEVICE="${DEVICE:-cuda:0}"
PILOT_DATA_N="${PILOT_DATA_N:-50}"
SMOKE_DATA_N="${SMOKE_DATA_N:-8}"
FULL_DATA_N="${FULL_DATA_N:-999999}"

mkdir -p "${RUN_ROOT}"
echo "${RUN_ROOT}" > "${RUN_ROOT}/RUN_ROOT.txt"
cd "${PROJECT_ROOT}"

models=(
  blip2-opt-2.7b
  instructblip-vicuna-7b
  minigpt-4-vicuna-7b
  llava-v1.5-7b
  qwen2.5-vl-3b
  paligemma-3b
  smolvlm-1.7b
)

dataset_json() {
  local dataset="$1"
  if [[ "${dataset}" == "mmke-visual" ]]; then
    echo "${MMKE_ROOT}/data_json/visual_train.json"
  elif [[ "${dataset}" == "mmke-entity" ]]; then
    echo "${MMKE_ROOT}/data_json/entity_train.json"
  else
    echo "unknown dataset ${dataset}" >&2
    return 2
  fi
}

is_done() {
  local out_dir="$1"
  [[ -f "${out_dir}/summary.json" ]] || return 1
  "${PYTHON_BIN}" - "${out_dir}/summary.json" <<'PY'
import json, sys, time
p=sys.argv[1]
last=None
for _ in range(20):
    try:
        d=json.load(open(p, encoding="utf-8"))
        break
    except Exception as e:
        last=e
        time.sleep(0.5)
else:
    print(f"summary_not_ready: {last}", file=sys.stderr)
    sys.exit(1)
sys.exit(0 if d.get("status") == "done" else 1)
PY
}

check_done_or_fail() {
  local out_dir="$1"
  "${PYTHON_BIN}" - "${out_dir}/summary.json" <<'PY'
import json, sys, time
p=sys.argv[1]
last=None
for _ in range(20):
    try:
        d=json.load(open(p, encoding="utf-8"))
        break
    except Exception as e:
        last=e
        time.sleep(0.5)
else:
    print(json.dumps({"status":"summary_not_ready","failure_reason":str(last)}, ensure_ascii=False))
    sys.exit(1)
status=d.get("status")
print(json.dumps({
  "dataset": d.get("dataset"),
  "model": d.get("model"),
  "status": status,
  "valid": d.get("valid_sample_count"),
  "total": d.get("total_sample_count"),
  "top3_pre": d.get("top3_pre_layers"),
  "top5_pre": d.get("top5_pre_layers"),
  "failure_reason": d.get("failure_reason"),
}, ensure_ascii=False))
sys.exit(0 if status == "done" else 1)
PY
}

run_one() {
  local phase="$1"
  local dataset="$2"
  local model="$3"
  local data_n="$4"
  local out_dir="${RUN_ROOT}/${phase}/${dataset}/${model}"
  local data_path
  data_path="$(dataset_json "${dataset}")"
  mkdir -p "${out_dir}"

  if is_done "${out_dir}"; then
    echo "[$(date '+%F %T')] skip done phase=${phase} dataset=${dataset} model=${model}" | tee -a "${RUN_ROOT}/run.log"
    return 0
  fi

  echo "[$(date '+%F %T')] start phase=${phase} dataset=${dataset} model=${model} data_n=${data_n} job=${JOB_ID}" | tee -a "${RUN_ROOT}/run.log"
  srun --jobid="${JOB_ID}" --overlap --ntasks=1 --cpus-per-task=8 \
    "${PYTHON_BIN}" scripts/run_visedit_keytoken_candidate_layers.py \
      --model-name "${model}" \
      --dataset-name "${dataset}" \
      --data-path "${data_path}" \
      --img-root-dir "${MMKE_ROOT}/data_image" \
      --out-dir "${out_dir}" \
      --data-n "${data_n}" \
      --device "${DEVICE}" \
      > "${out_dir}/run.log" 2>&1
  check_done_or_fail "${out_dir}" | tee -a "${RUN_ROOT}/run.log"
  echo "[$(date '+%F %T')] done phase=${phase} dataset=${dataset} model=${model}" | tee -a "${RUN_ROOT}/run.log"
}

collect() {
  "${PYTHON_BIN}" - "${RUN_ROOT}" <<'PY'
import csv, json, sys
from pathlib import Path
root = Path(sys.argv[1])
rows = []
for summary in sorted(root.glob("*/*/*/summary.json")):
    try:
        d = json.load(open(summary, encoding="utf-8"))
    except Exception as exc:
        rows.append({
            "phase": summary.parts[-4],
            "dataset": summary.parts[-3],
            "model": summary.parts[-2],
            "status": "summary_unreadable",
            "valid": "",
            "total": "",
            "top3_pre": "",
            "top5_pre": "",
            "failure_reason": str(exc),
        })
        continue
    rows.append({
        "phase": summary.parts[-4],
        "dataset": d.get("dataset"),
        "model": d.get("model"),
        "status": d.get("status"),
        "valid": d.get("valid_sample_count"),
        "total": d.get("total_sample_count"),
        "top3_pre": ",".join(f"L{x}" for x in d.get("top3_pre_layers", [])),
        "top5_pre": ",".join(f"L{x}" for x in d.get("top5_pre_layers", [])),
        "failure_reason": d.get("failure_reason", ""),
    })
out = root / "visedit_keytoken_candidates_summary.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["phase","dataset","model","status","valid","total","top3_pre","top5_pre","failure_reason"])
    w.writeheader()
    w.writerows(rows)
print(out)
PY
}

echo "[$(date '+%F %T')] RUN_ROOT=${RUN_ROOT}" | tee -a "${RUN_ROOT}/run.log"

# Phase 1: two LLaVA MMKE pilots.
run_one pilot mmke-visual llava-v1.5-7b "${PILOT_DATA_N}"
run_one pilot mmke-entity llava-v1.5-7b "${PILOT_DATA_N}"
collect | tee -a "${RUN_ROOT}/run.log"

# Phase 2: small 7-model smoke tests on both MMKE datasets.
for dataset in mmke-visual mmke-entity; do
  for model in "${models[@]}"; do
    run_one smoke "${dataset}" "${model}" "${SMOKE_DATA_N}"
  done
done
collect | tee -a "${RUN_ROOT}/run.log"

# Phase 3: full 2 datasets x 7 models.
for dataset in mmke-visual mmke-entity; do
  for model in "${models[@]}"; do
    run_one full "${dataset}" "${model}" "${FULL_DATA_N}"
  done
done

collect | tee -a "${RUN_ROOT}/run.log"
echo "[$(date '+%F %T')] all done" | tee -a "${RUN_ROOT}/run.log"
