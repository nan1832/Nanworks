#!/usr/bin/env bash
set -u

JOB=3044841
PROJECT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
ENTITY_ROOT=/tmp/ph_teacher3/mmke_entity_minigpt_llava_job3044841_20260726
VISUAL_ROOT=/tmp/ph_teacher3/mmke_visual_minigpt_llava_job3044841_20260726
L0_DIR="$ENTITY_ROOT/minigpt-4-vicuna-7b/layer_00"
CURRENT_SRUN_PID_FILE=/tmp/mmke_entity_minigpt_llava_job3044841_srun.pid
STATUS=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/job3044841_entity_l0_visual_then_entity_20260726.log

log() {
  echo "[$(date '+%F %T')] $*" | tee -a "$STATUS"
}

current_srun_alive() {
  local pid
  pid=$(cat "$CURRENT_SRUN_PID_FILE" 2>/dev/null || true)
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

l0_fully_evaluated() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 g09 \
    "test -s '$L0_DIR/train.done' && test -s '$L0_DIR/selected_checkpoint.tsv' && test -s '$L0_DIR/eval_full.done' && find '$L0_DIR' -type f -name results.json -size +0c -print -quit | grep -q ."
}

log "CHAIN_START job=$JOB policy=finish_entity_L0_then_visual20_then_resume_entity"

while ! l0_fully_evaluated; do
  if ! current_srun_alive; then
    log "CHAIN_ABORT current_entity_srun_not_alive before_L0_full_eval"
    exit 20
  fi
  progress=$(ssh -o BatchMode=yes -o ConnectTimeout=10 g09 \
    "f=\$(find '$ENTITY_ROOT/minigpt-4-vicuna-7b' -maxdepth 1 -type f -name 'train_L0_*.log' -printf '%T@ %p\\n' 2>/dev/null | sort -n | tail -n1 | cut -d' ' -f2-); if [[ -n \"\$f\" ]]; then stat -c 'mtime=%y size=%s' \"\$f\"; tail -c 5000 \"\$f\" | tr '\\r' '\\n' | grep -E 'Epoch [0-9]+:' | tail -n1; fi" 2>/dev/null || true)
  log "WAIT_ENTITY_L0 $progress"
  sleep 300
done

log "ENTITY_L0_FULL_EVAL_CONFIRMED selected_checkpoint=1 eval_full_done=1 results_json=1"
current_pid=$(cat "$CURRENT_SRUN_PID_FILE" 2>/dev/null || true)
if [[ -n "$current_pid" ]] && kill -0 "$current_pid" 2>/dev/null; then
  kill -TERM "$current_pid"
  log "CURRENT_ENTITY_QUEUE_STEP_TERM_SENT srun_pid=$current_pid after_L0_full_eval"
fi

for _ in $(seq 1 24); do
  if ! ssh -o BatchMode=yes -o ConnectTimeout=10 g09 \
      "pgrep -f '[r]un_mmke_minigpt_llava_lowmem_sweep.py.*$ENTITY_ROOT' >/dev/null"; then
    break
  fi
  sleep 5
done
if ssh -o BatchMode=yes -o ConnectTimeout=10 g09 \
    "pgrep -f '[r]un_mmke_minigpt_llava_lowmem_sweep.py.*$ENTITY_ROOT' >/dev/null"; then
  log "CHAIN_ABORT entity_python_still_alive_after_120s; visual_not_started"
  exit 21
fi

log "VISUAL_QUEUE_START root=$VISUAL_ROOT mini_layers=0,1,2,3,29 llava_layers=0,1,2,7,8,9,12,13,14,15,16,22,24,26,27 mode=normal_with_oom_lowmem_fallback"
srun --jobid="$JOB" --overlap --nodes=1 --ntasks=1 bash -lc \
  "cd '$PROJECT' && TASK=visual EXPECTED_JOB=$JOB OUT_ROOT='$VISUAL_ROOT' GPU_WAIT_MAX_USED_MIB=4096 INITIAL_MODE=normal bash scripts/launch_mmke_minigpt_llava_pending_job.sh" \
  2>&1 | tee -a "$STATUS"
visual_rc=${PIPESTATUS[0]}
log "VISUAL_QUEUE_EXIT rc=$visual_rc"

mini_done=$(ssh -o BatchMode=yes -o ConnectTimeout=10 g09 \
  "find '$VISUAL_ROOT/minigpt-4-vicuna-7b' -mindepth 2 -maxdepth 2 -type f -name eval_full.done -size +0c 2>/dev/null | wc -l" | tr -dc '0-9')
llava_done=$(ssh -o BatchMode=yes -o ConnectTimeout=10 g09 \
  "find '$VISUAL_ROOT/llava-v1.5-7b' -mindepth 2 -maxdepth 2 -type f -name eval_full.done -size +0c 2>/dev/null | wc -l" | tr -dc '0-9')
mini_done=${mini_done:-0}
llava_done=${llava_done:-0}
log "VISUAL_COMPLETION_CHECK minigpt=$mini_done/5 llava=$llava_done/15"

if [[ "$visual_rc" -ne 0 || "$mini_done" -ne 5 || "$llava_done" -ne 15 ]]; then
  log "CHAIN_PAUSE visual_not_fully_complete; entity_resume_not_started"
  exit 22
fi

log "ENTITY_QUEUE_RESUME root=$ENTITY_ROOT; completed_L0_will_be_skipped_by_markers"
srun --jobid="$JOB" --overlap --nodes=1 --ntasks=1 bash -lc \
  "cd '$PROJECT' && TASK=entity EXPECTED_JOB=$JOB OUT_ROOT='$ENTITY_ROOT' GPU_WAIT_MAX_USED_MIB=4096 INITIAL_MODE=normal bash scripts/launch_mmke_minigpt_llava_pending_job.sh" \
  2>&1 | tee -a "$STATUS"
entity_rc=${PIPESTATUS[0]}
log "CHAIN_END resumed_entity_rc=$entity_rc"
exit "$entity_rc"
