#!/usr/bin/env bash
set -u

SERVER_RESULTS=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results
CONTROL=$SERVER_RESULTS/paligemma_visual_stable_all8_completion_job3044208_20260714_210005
STATUS=$CONTROL/status.log
WATCH_LOG=$CONTROL/two_hour_watchdog.log
MODEL_ROOT=$SERVER_RESULTS/paligemma_stable_mmke_visual_pending8_job3044208_20260713_204917/paligemma-3b
LIMIT_SECONDS=7200

echo "WATCHDOG_START limit_seconds=$LIMIT_SECONDS time=$(date)" >> "$WATCH_LOG"
while true; do
  if grep -q "VISUAL_STABLE_ALL8_COMPLETION_DONE" "$STATUS" 2>/dev/null; then
    echo "WATCHDOG_EXIT completion_marker=1 time=$(date)" >> "$WATCH_LOG"
    exit 0
  fi
  found_launcher=0
  if pgrep -f "run_paligemma_mmke_visual_stable_all8_completion_job3044208.sh" >/dev/null 2>&1; then
    found_launcher=1
  fi
  while read -r pid etimes; do
    [[ -n "$pid" && -n "$etimes" ]] || continue
    exe=$(readlink -f "/proc/$pid/exe" 2>/dev/null || true)
    case "$exe" in
      *python*)
        if [[ "$etimes" -ge "$LIMIT_SECONDS" ]]; then
          echo "WATCHDOG_STOP pid=$pid etimes=$etimes reason=over_2h time=$(date)" >> "$WATCH_LOG"
          kill -TERM "$pid" 2>/dev/null || true
          sleep 20
          kill -KILL "$pid" 2>/dev/null || true
        fi
        ;;
    esac
  done < <(
    ps -eo pid=,etimes=,args= |
      awk -v root="$MODEL_ROOT" '$0 ~ root && $0 ~ /run_evqa_pilot500_blip2_visedit_sweep_pali_stable.py/ {print $1, $2}'
  )
  if [[ "$found_launcher" -eq 0 ]]; then
    echo "WATCHDOG_WAIT launcher_missing completion_marker=0 time=$(date)" >> "$WATCH_LOG"
  fi
  sleep 60
done
