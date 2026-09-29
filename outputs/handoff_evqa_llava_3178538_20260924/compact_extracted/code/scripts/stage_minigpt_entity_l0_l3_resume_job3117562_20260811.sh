#!/usr/bin/env bash
set -euo pipefail

SRC=/var/tmp/ph_teacher3/job3044841_20260728/mmke_entity_minigpt4
DURABLE=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/resume_handoff_job3044841_20260728/mmke_entity_minigpt4
RUN=/tmp/ph_teacher3/formal_top3_minigpt_entity_job3117562_20260811/mmke-entity/minigpt-4-vicuna-7b

mkdir -p "$DURABLE/L0" "$DURABLE/L3_epoch19_switch_20260728_0940"
cp -p "$SRC/L0/epoch-28-i-8904-ema_loss-1.4432" "$DURABLE/L0/"
cp -p "$SRC/L3_epoch19_switch_20260728_0940/epoch-19-i-6042-ema_loss-2.4269" "$DURABLE/L3_epoch19_switch_20260728_0940/"

srun --overlap --jobid=3117562 --nodes=1 --ntasks=1 bash -s -- "$DURABLE" "$RUN" <<'REMOTE'
set -euo pipefail
DURABLE=$1
RUN=$2

stage_one() {
  local layer=$1 epoch=$2 i=$3 loss=$4 ema=$5 src=$6 ll exp ckpt_dir dst
  printf -v ll '%02d' "$layer"
  exp="pilot500_blip2_visedit_L${ll}-lr-1-t-1-v-1"
  ckpt_dir="$RUN/layer_${ll}/records/vead/minigpt-4-vicuna-7b/$exp/checkpoints"
  mkdir -p "$ckpt_dir"
  dst="$ckpt_dir/$(basename "$src")"
  cp -p "$src" "$dst"
  {
    printf 'time,layer,epoch,i,loss,ema_loss,ckpt_path,kept\n'
    printf '2026-08-11 20:00:00,%s,%s,%s,%s,%s,%s,1\n' "$layer" "$epoch" "$i" "$loss" "$ema" "$dst"
  } >"$RUN/layer_${ll}/loss_history.csv"
  sha256sum "$src" "$dst"
}

stage_one 0 28 8904 0.8833264112472534 1.4431506244387435 \
  "$DURABLE/L0/epoch-28-i-8904-ema_loss-1.4432"
stage_one 3 19 6042 2.4269 2.4269 \
  "$DURABLE/L3_epoch19_switch_20260728_0940/epoch-19-i-6042-ema_loss-2.4269"
REMOTE
