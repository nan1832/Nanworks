#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
RUNROOT="$ROOT/server_results/cma_modelpred_direct_formal_multinoise_multiseed_v1_20260906"
PREFLIGHT_PID=1815862
PY="$ROOT/envs/qwen25vl/bin/python"

echo "[$(date '+%F %T %Z')] waiting for preflight srun pid=$PREFLIGHT_PID"
while kill -0 "$PREFLIGHT_PID" 2>/dev/null; do
  sleep 30
done

"$PY" - "$RUNROOT/preflight50/canonical/summary.json" "$RUNROOT/preflight50/run_complete.json" <<'PY'
import json, pathlib, sys
summary_path, complete_path = map(pathlib.Path, sys.argv[1:])
if not summary_path.is_file() or not complete_path.is_file():
    raise SystemExit("preflight failed: final summary or run_complete missing")
s = json.loads(summary_path.read_text(encoding="utf-8"))
checks = {
    "method": s.get("method") == "CMA-ModelPred-Direct",
    "target": s.get("target_field") == "model_pred",
    "samples": s.get("total_unique_samples") == 50,
    "pairs": s.get("corruption_pairs_recorded") == 450,
    "finite": s.get("finite_corruption_pairs") == 450,
    "no_nonfinite": s.get("nonfinite_score_pair_count") == 0,
    "no_missing_restore": s.get("missing_restore_pair_count") == 0,
    "no_runtime_error": s.get("runtime_error_or_missing_pair_count") == 0,
    "target_manifest": s.get("target_manifest_rows") == 50,
    "prompt_match": s.get("cache_prompt_exact_match_samples") == 50 and s.get("cache_prompt_mismatch_samples") == 0,
}
failed = [k for k, ok in checks.items() if not ok]
print(json.dumps({"preflight_checks": checks, "summary": s}, ensure_ascii=False))
if failed:
    raise SystemExit("preflight failed checks: " + ",".join(failed))
PY

if pgrep -af "[r]un_cma_modelpred_direct_formal_multinoise_v1.py.*formal636"; then
  echo "formal636 already running; refusing duplicate launch"
  exit 0
fi

echo "[$(date '+%F %T %Z')] preflight accepted; launching formal636"
exec srun --jobid=3178538 --overlap -w g08 --ntasks=1 --cpus-per-task=4 bash "$RUNROOT/launch_formal636.sh"
