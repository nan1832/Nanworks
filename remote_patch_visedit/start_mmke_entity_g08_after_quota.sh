#!/usr/bin/env bash
set -euo pipefail

REPO="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
RUN_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000"
LOG="$RUN_ROOT/mmke_entity_noqwen_after_quota_20260617.nohup.log"

cd "$REPO"
setsid -f env \
  RUN_ROOT="$RUN_ROOT" \
  GPU_ID=0 \
  SKIP_QWEN=1 \
  MAX_USED_MIB=30000 \
  bash scripts/launch_mmke_entity_top3_union_train_eval_g07_gpu0.sh \
  > "$LOG" 2>&1 < /dev/null

sleep 1
pgrep -af launch_mmke_entity_top3_union_train_eval_g07_gpu0.sh || true
