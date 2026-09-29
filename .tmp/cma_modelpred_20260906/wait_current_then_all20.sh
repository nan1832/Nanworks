#!/usr/bin/env bash
set -euo pipefail

ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
PROJECT="$ROOT/VisEdit-main"
RESULTS="$ROOT/server_results"
CURRENT="$RESULTS/cma_modelpred_direct_formal_multinoise_multiseed_v1_20260906/formal636"
RUNROOT="$RESULTS/cma_modelpred_direct_all20_multinoise_multiseed_v1_20260906"
HELPER="$RUNROOT/run_modelpred_combo_on_gpu.sh"
PY="$ROOT/envs/qwen25vl/bin/python"
JOB=3178538

mkdir -p "$RUNROOT"
echo "[$(date '+%F %T %Z')] waiting for current MMKE-entity/Qwen completion"
while [[ ! -s "$CURRENT/run_complete.json" ]]; do
  sleep 60
done

"$PY" - "$CURRENT/canonical/summary.json" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); s=json.loads(p.read_text(encoding="utf-8"))
required={
 "method": s.get("method")=="CMA-ModelPred-Direct",
 "dataset": s.get("dataset","mmke-entity")=="mmke-entity",
 "model": s.get("model","qwen2.5-vl-3b")=="qwen2.5-vl-3b",
 "samples": s.get("target_manifest_rows")==636,
 "pairs": s.get("corruption_pairs_recorded")==5724,
 "finite": s.get("finite_corruption_pairs")==5724,
 "no_nonfinite": s.get("nonfinite_score_pair_count")==0,
 "no_missing": s.get("missing_restore_pair_count")==0,
 "no_runtime": s.get("runtime_error_or_missing_pair_count")==0,
 "prompt": s.get("cache_prompt_mismatch_samples")==0,
}
bad=[k for k,v in required.items() if not v]
print(json.dumps({"current_validation":required,"summary":s},ensure_ascii=False))
if bad: raise SystemExit("current combination failed validation: "+",".join(bad))
PY

cat > "$RUNROOT/queue.tsv" <<'EOF'
mmke-visual	qwen2.5-vl-3b
evqa-pilot500	qwen2.5-vl-3b
mmke-visual	paligemma-3b
evqa-pilot500	paligemma-3b
mmke-entity	paligemma-3b
mmke-visual	smolvlm-1.7b
evqa-pilot500	smolvlm-1.7b
mmke-entity	smolvlm-1.7b
mmke-visual	blip2-opt-2.7b
evqa-pilot500	blip2-opt-2.7b
mmke-entity	blip2-opt-2.7b
mmke-visual	instructblip-vicuna-7b
evqa-pilot500	instructblip-vicuna-7b
mmke-entity	instructblip-vicuna-7b
mmke-visual	minigpt-4-vicuna-7b
evqa-pilot500	minigpt-4-vicuna-7b
mmke-entity	minigpt-4-vicuna-7b
mmke-visual	llava-v1.5-7b
evqa-pilot500	llava-v1.5-7b
mmke-entity	llava-v1.5-7b
EOF

while IFS=$'\t' read -r dataset model; do
  [[ -n "$dataset" && -n "$model" ]] || continue
  combo="$RUNROOT/$dataset/$model"
  smoke="$combo/smoke2"
  formal="$combo/formal"
  mkdir -p "$smoke" "$formal"

  if [[ "$model" == "qwen2.5-vl-3b" ]]; then
    cache_root="$RESULTS/ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304"
  else
    cache_root="$RESULTS/ours_direct_7models_3datasets_g08_gpu0_20260626_131624"
  fi
  cache="$cache_root/$dataset/$model/model_pred_cache.jsonl"
  config="$PROJECT/configs/p_track/$model.yaml"
  case "$dataset" in
    evqa-pilot500)
      expected=500
      data_path="$RESULTS/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json"
      image_root="$RESULTS/evqa_proxy_train500_eval500_20260528/images"
      ;;
    mmke-visual)
      expected=214
      data_path="$RESULTS/mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json"
      image_root="$ROOT/datasets/MMKE-Bench/data_image"
      ;;
    mmke-entity)
      expected=636
      data_path="$RESULTS/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json"
      image_root="$ROOT/datasets/MMKE-Bench/data_image"
      ;;
    *) echo "unknown dataset $dataset" >&2; exit 2;;
  esac

  "$PY" - "$cache" "$expected" "$smoke/input_manifest.json" "$formal/input_manifest.json" <<'PY'
import json, pathlib, sys
cache=pathlib.Path(sys.argv[1]); expected=int(sys.argv[2])
smoke=pathlib.Path(sys.argv[3]); formal=pathlib.Path(sys.argv[4])
rows=[json.loads(x) for x in cache.read_text(encoding="utf-8").splitlines() if x.strip()]
ids=[str(x.get("sample_id","")) for x in rows]
if len(ids)!=expected or len(set(ids))!=expected or any(not x for x in ids):
    raise SystemExit(f"cache manifest invalid: rows={len(ids)} unique={len(set(ids))} expected={expected}")
base={"selection_rule":"all IDs in immutable model_pred cache order","sample_count":expected,"sample_ids":ids}
formal.write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding="utf-8")
smoke.write_text(json.dumps({**base,"sample_count":2,"sample_ids":ids[:2]},ensure_ascii=False,indent=2),encoding="utf-8")
PY

  case "$model" in
    instructblip-vicuna-7b|minigpt-4-vicuna-7b|llava-v1.5-7b) required_free=45000;;
    *) required_free=30000;;
  esac

  while :; do
    free_mib=$(ssh -o BatchMode=yes g08 /usr/bin/nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1 | tr -d ' ')
    if [[ "$free_mib" =~ ^[0-9]+$ ]] && (( free_mib >= required_free )); then break; fi
    echo "[$(date '+%F %T %Z')] wait memory dataset=$dataset model=$model free_mib=${free_mib:-NA} required=$required_free"
    sleep 60
  done

  if [[ ! -s "$smoke/run_complete.json" ]]; then
    echo "[$(date '+%F %T %Z')] smoke dataset=$dataset model=$model free_mib=$free_mib"
    srun --jobid="$JOB" --overlap -w g08 --ntasks=1 --cpus-per-task=4 \
      bash "$HELPER" "$dataset" "$model" smoke "$smoke/input_manifest.json" "$smoke" "$cache" "$data_path" "$image_root" "$config" \
      >"$smoke/run.log" 2>&1
  fi
  "$PY" - "$smoke/canonical/summary.json" <<'PY'
import json,sys
s=json.load(open(sys.argv[1],encoding="utf-8"))
bad=[]
for k,v in {"samples":s.get("target_manifest_rows")==2,"pairs":s.get("corruption_pairs_recorded")==18,
            "finite":s.get("finite_corruption_pairs")==18,"nonfinite":s.get("nonfinite_score_pair_count")==0,
            "missing":s.get("missing_restore_pair_count")==0,"runtime":s.get("runtime_error_or_missing_pair_count")==0,
            "prompt":s.get("cache_prompt_mismatch_samples")==0}.items():
    if not v: bad.append(k)
if bad: raise SystemExit("smoke validation failed: "+",".join(bad))
PY

  while :; do
    free_mib=$(ssh -o BatchMode=yes g08 /usr/bin/nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1 | tr -d ' ')
    if [[ "$free_mib" =~ ^[0-9]+$ ]] && (( free_mib >= required_free )); then break; fi
    echo "[$(date '+%F %T %Z')] wait formal memory dataset=$dataset model=$model free_mib=${free_mib:-NA} required=$required_free"
    sleep 60
  done

  if [[ ! -s "$formal/run_complete.json" ]]; then
    echo "[$(date '+%F %T %Z')] formal dataset=$dataset model=$model expected=$expected free_mib=$free_mib"
    srun --jobid="$JOB" --overlap -w g08 --ntasks=1 --cpus-per-task=4 \
      bash "$HELPER" "$dataset" "$model" formal "$formal/input_manifest.json" "$formal" "$cache" "$data_path" "$image_root" "$config" \
      >"$formal/run.log" 2>&1
  fi
  "$PY" - "$formal/canonical/summary.json" "$expected" <<'PY'
import json,sys
s=json.load(open(sys.argv[1],encoding="utf-8")); n=int(sys.argv[2])
checks={"samples":s.get("target_manifest_rows")==n,"pairs":s.get("corruption_pairs_recorded")==n*9,
        "finite":s.get("finite_corruption_pairs")==n*9,"nonfinite":s.get("nonfinite_score_pair_count")==0,
        "missing":s.get("missing_restore_pair_count")==0,"runtime":s.get("runtime_error_or_missing_pair_count")==0,
        "prompt":s.get("cache_prompt_mismatch_samples")==0}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"validation":checks,"summary":s},ensure_ascii=False))
if bad: raise SystemExit("formal validation failed: "+",".join(bad))
PY
  echo "[$(date '+%F %T %Z')] COMPLETE dataset=$dataset model=$model"
done < "$RUNROOT/queue.tsv"

touch "$RUNROOT/ALL20_COMPLETE"
echo "[$(date '+%F %T %Z')] ALL20 COMPLETE"
