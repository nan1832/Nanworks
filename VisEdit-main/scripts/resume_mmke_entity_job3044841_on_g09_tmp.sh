#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
LEGACY_RUN_ROOT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000"
ORIGINAL_LAUNCHER="$PROJECT_ROOT/scripts/launch_mmke_entity_3p4_pending_epoch50_job3044841.sh"
SCRATCH_ROOT="${SCRATCH_ROOT:-/tmp/ph_teacher3/mmke_entity_job3044841_$(date +%Y%m%d_%H%M%S)}"

case "$SCRATCH_ROOT" in
  /tmp/ph_teacher3/mmke_entity_job3044841_*) ;;
  *) echo "Refusing unsafe scratch root: $SCRATCH_ROOT" >&2; exit 2 ;;
esac

[[ "$(hostname -s)" == "g09" ]] || {
  echo "This wrapper must run on g09, got $(hostname -s)" >&2
  exit 3
}
[[ -x "$ORIGINAL_LAUNCHER" ]] || {
  echo "Launcher is not executable: $ORIGINAL_LAUNCHER" >&2
  exit 4
}
[[ -s "$LEGACY_RUN_ROOT/data/vqa_mmke_entity_train_evqa_compat.json" ]] || exit 5
[[ -s "$LEGACY_RUN_ROOT/data/vqa_mmke_entity_eval_evqa_compat.json" ]] || exit 6

mkdir -p "$SCRATCH_ROOT"
ln -s "$LEGACY_RUN_ROOT/data" "$SCRATCH_ROOT/data"

# Make already completed layers visible read-only so the original launcher skips
# them. A layer is linked only after all completion evidence has been verified.
linked=0
for legacy_layer in "$LEGACY_RUN_ROOT"/*/layer_*; do
  [[ -d "$legacy_layer" ]] || continue
  [[ -f "$legacy_layer/train.done" ]] || continue
  [[ -f "$legacy_layer/eval_full.done" ]] || continue
  [[ -s "$legacy_layer/selected_checkpoint.tsv" ]] || continue
  selected="$(tail -n 1 "$legacy_layer/selected_checkpoint.tsv" | awk -F '\t' '{print $NF}' | tr -d '\r')"
  [[ -f "$selected" ]] || continue

  model="$(basename "$(dirname "$legacy_layer")")"
  layer_name="$(basename "$legacy_layer")"
  mkdir -p "$SCRATCH_ROOT/$model"
  ln -s "$legacy_layer" "$SCRATCH_ROOT/$model/$layer_name"
  linked=$((linked + 1))
done

cat > "$SCRATCH_ROOT/resume_metadata.txt" <<EOF
job=3044841
host=$(hostname -s)
physical_gpu=GPU1
slurm_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}
scratch_root=$SCRATCH_ROOT
legacy_results_read_only=$LEGACY_RUN_ROOT
train_data_read_only=$LEGACY_RUN_ROOT/data/vqa_mmke_entity_train_evqa_compat.json
eval_data_read_only=$LEGACY_RUN_ROOT/data/vqa_mmke_entity_eval_evqa_compat.json
linked_completed_layers=$linked
started_at=$(date '+%F %T %z')
EOF

echo "SCRATCH_READY root=$SCRATCH_ROOT linked_completed_layers=$linked"
echo "DATA_READ_ONLY train=$LEGACY_RUN_ROOT/data/vqa_mmke_entity_train_evqa_compat.json eval=$LEGACY_RUN_ROOT/data/vqa_mmke_entity_eval_evqa_compat.json"

export GPU_ID=0
export RUN_ROOT="$SCRATCH_ROOT"
exec "$ORIGINAL_LAUNCHER"
