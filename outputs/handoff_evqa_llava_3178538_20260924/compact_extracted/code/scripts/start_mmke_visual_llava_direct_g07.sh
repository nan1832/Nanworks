#!/usr/bin/env bash
set -euo pipefail

REPO="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
RUN_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644"
LOG="$RUN_ROOT/mmke_visual_llava_direct_20260617.nohup.log"

cd "$REPO"
nohup env GPU_ID=0 bash scripts/launch_mmke_visual_llava_direct_g07.sh > "$LOG" 2>&1 < /dev/null &
sleep 1
pgrep -af launch_mmke_visual_llava_direct_g07.sh || true
