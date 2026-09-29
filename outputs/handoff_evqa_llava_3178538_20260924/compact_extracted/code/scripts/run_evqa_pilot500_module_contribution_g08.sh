#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
PY=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python
DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
IMAGES=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
RUN_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_pilot500_module_contribution_$(date +%Y%m%d_%H%M%S)

cd "$ROOT"
mkdir -p "$RUN_ROOT"

models=(
  instructblip-vicuna-7b
  llava-v1.5-7b
  qwen2.5-vl-3b
  paligemma-3b
  smolvlm-1.7b
)

if [[ -d "$ROOT/models/minigpt-4-vicuna-7b" ]]; then
  models=(instructblip-vicuna-7b minigpt-4-vicuna-7b llava-v1.5-7b qwen2.5-vl-3b paligemma-3b smolvlm-1.7b)
else
  printf 'SKIP minigpt-4-vicuna-7b: missing %s\n' "$ROOT/models/minigpt-4-vicuna-7b" | tee "$RUN_ROOT/minigpt-4-vicuna-7b.SKIPPED"
fi

printf '%s\n' "${models[@]}" > "$RUN_ROOT/models_to_run.txt"
printf 'run_root=%s\n' "$RUN_ROOT" | tee "$RUN_ROOT/RUN_ROOT.txt"

for model in "${models[@]}"; do
  out="$RUN_ROOT/$model"
  mkdir -p "$out"
  printf '\n===== %s %s =====\n' "$(date '+%F %T')" "$model" | tee -a "$RUN_ROOT/run.log"
  "$PY" scripts/run_evqa_module_contribution_pilot500_multi.py \
    --model-name "$model" \
    --data-path "$DATA" \
    --img-root-dir "$IMAGES" \
    --out-dir "$out" \
    --data-n 500 \
    --key-mode alt \
    --device cuda:0 \
    2>&1 | tee "$out/run.log"
  printf 'DONE %s %s\n' "$(date '+%F %T')" "$model" | tee -a "$RUN_ROOT/run.log"
done

printf 'ALL_DONE %s\n' "$(date '+%F %T')" | tee -a "$RUN_ROOT/run.log"
