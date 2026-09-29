#!/usr/bin/env bash
set -euo pipefail

REPO="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
RUN_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644"
LOG="$RUN_ROOT/mmke_visual_skipdone_noqwen_after_quota_20260617.nohup.log"

cd "$REPO"
nohup env \
  RUN_ROOT="$RUN_ROOT" \
  GPU_ID=0 \
  SKIP_QWEN=1 \
  bash scripts/launch_mmke_visual_top3_union_skipdone_atomic_g07.sh \
  > "$LOG" 2>&1 < /dev/null &

sleep 1
pgrep -af launch_mmke_visual_top3_union_skipdone_atomic_g07.sh || true
