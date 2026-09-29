#!/usr/bin/env python3
"""Strict per-sample LGA ablations; no optimizer, training, or target generation.

Run in the original server environment with --project-dir pointing to VisEdit-main.
The old model_pred cache is read only. A result is publishable only when every
originally admitted sample/layer is present and the historical means reproduce.
"""
import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import platform
import sys
import time
import traceback
from pathlib import Path

MODELS = {"blip2-opt-2.7b": 32, "instructblip-vicuna-7b": 32,
          "minigpt-4-vicuna-7b": 32, "llava-v1.5-7b": 32,
          "qwen2.5-vl-3b": 36, "paligemma-3b": 18, "smolvlm-1.7b": 24}
DATASETS = {"evqa-pilot500": 500, "mmke-visual": 214, "mmke-entity": 636}
PARAM_RUN = "lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900"
VISUAL_RUN = "ours_direct_7models_3datasets_g08_gpu0_20260626_131624"
QWEN_RUN = "ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304"
EPS = 1e-12
FIELDS = ("dot", "cos", "old_norm", "new_norm", "no_old_strength", "no_new_strength", "no_direction")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(tmp), str(path))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def cross_stats(stats):
    result = {k: float(stats[k]) for k in ("dot", "cos", "old_norm", "new_norm")}
    if not all(math.isfinite(v) for v in result.values()):
        raise ValueError("nonfinite gradient statistic")
    if min(result["old_norm"], result["new_norm"]) < 0:
        raise ValueError("negative norm")
    a, b, c = result["old_norm"], result["new_norm"], result["cos"]
    if not math.isclose(c, result["dot"] / (a * b + EPS), rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("cosine convention differs from original epsilon=1e-12")
    result.update(no_old_strength=c * b, no_new_strength=c * a, no_direction=a * b)
    if not all(math.isfinite(v) for v in result.values()):
        raise ValueError("nonfinite cross statistic")
    return result


def aggregate(records, expected_ids, num_layers):
    """Refuse partial cohorts, extra samples, missing layers, and duplicate IDs."""
    assert len(records) == len(expected_ids) == len(set(expected_ids))
    assert {r["sample_id"] for r in records} == set(expected_ids)
    assert all(set(r["layers"]) == {str(l) for l in range(num_layers)} for r in records)
    rows = []
    for layer in range(num_layers):
        values = [cross_stats(r["layers"][str(layer)]) for r in records]
        rows.append(dict(layer=layer, n=len(values), **{
            field: math.fsum(v[field] for v in values) / len(values) for field in FIELDS}))
    return rows


def original_dir(args):
    run = PARAM_RUN if args.space == "parameter" else QWEN_RUN if args.model.startswith("qwen") else VISUAL_RUN
    return Path(args.source_root) / run / args.dataset / args.model


def visual_all_grads(helper, vllm, modules, prompt, image, target):
    """Same layer-output derivative as original; capture all layers in one pass."""
    import torch
    (inputs, vt), labels, masks = vllm.prompts_imgs_target_to_xym([prompt], [image], [target])
    if vt is None or int(vt[1]) <= int(vt[0]) or masks.sum().item() <= 0:
        raise ValueError("invalid visual range or empty target mask")
    start, end = int(vt[0]), int(vt[1])
    inputs = helper.prepare_llm_inputs_for_hidden_grad(inputs)
    handles, hidden = [], {}
    def hook_for(layer):
        def capture(module, args, output):
            h = helper.tensor_from_layer_output(output)
            if not torch.is_tensor(h) or not h.requires_grad or layer in hidden:
                raise RuntimeError("invalid or repeated hidden output")
            h.retain_grad()
            hidden[layer] = h
        return capture
    vllm.model.zero_grad(set_to_none=True)
    try:
        for layer, module in modules.items():
            handles.append(module.register_forward_hook(hook_for(layer)))
        output = vllm.get_llm_outpt(inputs, vt)
        loss = vllm.label_loss(output.logits, labels, masks, average=True)
        if not torch.isfinite(loss):
            raise ValueError("nonfinite target loss")
        loss.backward()
        grads = {}
        for layer in modules:
            h = hidden[layer]
            if h.grad is None or end > h.shape[1]:
                raise RuntimeError("missing or invalid visual derivative")
            # Preserve the original sample-admission check, including prompt text.
            if not helper.prompt_text_indices(int(h.shape[1]), (start, end), inputs, masks):
                raise RuntimeError("no prompt text tokens")
            grads[layer] = h.grad[:, start:end, :].detach().float().cpu().contiguous()
        return float(loss.detach().float().cpu()), grads, [start, end]
    finally:
        for handle in handles:
            handle.remove()
        vllm.model.zero_grad(set_to_none=True)
        hidden.clear()


def prepare(args):
    project = Path(args.project_dir).resolve()
    sys.path.insert(0, str(project))
    sys.path.insert(0, str(project / "scripts"))
    os.chdir(str(project))
    import torch
    from p_track.p_track import PTrackConfig
    from utils import load_vllm_for_edit
    helper_name = "run_ours_direct_candidate_layers_qwen_chatfix" if args.model.startswith("qwen") or args.space == "parameter" else "run_ours_direct_candidate_layers"
    helper = importlib.import_module(helper_name)
    param = importlib.import_module("run_lga_param_direct_altmodelpred_candidate_layers") if args.space == "parameter" else None
    ds = helper.DEFAULT_DATASETS[args.dataset]
    source = original_dir(args)
    cache_path = source / "model_pred_cache.jsonl"
    cache_rows = read_jsonl(cache_path)
    cache = {str(r["sample_id"]): r for r in cache_rows}
    if len(cache) != len(cache_rows):
        raise RuntimeError("duplicate cached old answers; inspect before recomputation")
    score_path = source / ("layer_scores.csv" if param else "ours_direct_layer_scores.csv")
    with score_path.open(encoding="utf-8-sig") as stream:
        baseline = sorted(list(csv.DictReader(stream)), key=lambda r: int(r["layer"]))
    count_col = "valid_sample_count" if param else "n_request"
    expected_n = {int(r[count_col]) for r in baseline}
    assert len(expected_n) == 1 and len(baseline) == MODELS[args.model]
    data = helper.load_edit_data(args.dataset, ds["data_path"], ds["img_root"], None)
    assert len(data) == DATASETS[args.dataset]
    source_files = [cache_path, score_path, source / "summary.json", Path(ds["data_path"])]
    visual_ids = None
    if not param:
        sample_log = source / "ours_direct_sample_layer_scores.jsonl"
        source_files.append(sample_log)
        by_layer = {l: set() for l in range(MODELS[args.model])}
        for r in read_jsonl(sample_log):
            ids = by_layer[int(r["layer"])]
            if str(r["sample_id"]) in ids:
                raise RuntimeError("duplicate historical sample/layer")
            ids.add(str(r["sample_id"]))
        visual_ids = by_layer[0]
        assert all(ids == visual_ids for ids in by_layer.values()), "historical layer cohorts differ"
    cohort = []
    for i, row in enumerate(data):
        sid = str(helper.get_sample_id(row, i))
        item = cache.get(sid, {})
        req = row["request"]
        old, new = str(item.get("answer") or "").strip(), str(req["target_new"])
        if param:
            if not new.strip() or not param.model_pred_cache_row_ok(item):
                continue
            new = new.strip()
            if param.normalize_answer(old) == param.normalize_answer(new):
                continue
        elif sid not in visual_ids:
            continue
        if not old:
            raise RuntimeError("historically admitted sample has no frozen old answer")
        if item.get("prompt") != req["prompt"]:
            raise RuntimeError("frozen response prompt no longer matches data")
        cohort.append(dict(sample_i=i, sample_id=sid, old=old, new=new, row=row))
    assert len(cohort) == next(iter(expected_n)), "admission differs from historical counts; no silent cohort change"
    if visual_ids is not None:
        assert {r["sample_id"] for r in cohort} == visual_ids
    cfg_path = project / helper.CONFIG_PATHS[args.model]
    cfg = PTrackConfig.from_yaml(str(cfg_path))
    assert int(cfg.num_layers) == MODELS[args.model]
    source_files += [cfg_path, Path(helper.__file__), Path(__file__).resolve()]
    if param:
        source_files.append(Path(param.__file__))
    source_files += list((project / "editor/vllms_for_edit").rglob("*.py"))
    source_files += list((project / "utils").glob("*.py"))
    protocol = dict(schema=1, space=args.space, model=args.model, dataset=args.dataset,
                    source=str(source), files={str(p): sha(p) for p in sorted(set(source_files))},
                    cohort=[{k: r[k] for k in ("sample_i", "sample_id", "old", "new")} for r in cohort],
                    old_target="frozen_model_pred", new_target="alt", epsilon=EPS,
                    parameter_batch_size=args.layer_batch_size, baseline_rtol=1e-3, baseline_atol=1e-8,
                    torch=torch.__version__, python=platform.python_version(),
                    formulas={"no_old_strength": "mean(cos_i*new_norm_i)", "no_new_strength": "mean(cos_i*old_norm_i)", "no_direction": "mean(old_norm_i*new_norm_i)"})
    out = Path(args.out_root) / args.space / args.dataset / args.model
    out.mkdir(parents=True, exist_ok=True)
    protocol_path = out / "protocol.json"
    if protocol_path.exists():
        assert json.loads(protocol_path.read_text(encoding="utf-8")) == protocol, "protocol drift on resume"
    else:
        atomic_json(protocol_path, protocol)
    if args.preflight:
        print(json.dumps(dict(status="preflight_ok", out=str(out), sample_count=len(cohort)), ensure_ascii=False))
        return None
    torch.set_grad_enabled(True)
    vllm = load_vllm_for_edit(args.model, args.device)
    vllm.model.eval()
    for p in vllm.model.parameters():
        p.requires_grad_(False)
    if param and hasattr(vllm.model, "config"):
        vllm.model.config.use_cache = False
    return helper, param, cfg, baseline, cohort, out, vllm


def run(args):
    prepared = prepare(args)
    if prepared is None:
        return
    helper, param, cfg, baseline, cohort, out, vllm = prepared
    import torch
    import gc
    if param:
        modules = param.prepare_mlp_weight_modules(vllm, cfg, args.model, include_bias=False)
        assert all(item["params"] for item in modules)
        for item, previous in zip(modules, baseline):
            assert item["module_path"] == previous["module_path"]
            assert item["param_names"] == previous["param_names"].split(";")
            assert item["param_count"] == int(previous["param_count"])
            param.set_params_trainable(item["params"], False)
    else:
        modules = {l: helper.find_module(vllm.model, cfg.layer_module_tmp.format(l)) for l in range(int(cfg.num_layers))}
    started, processed = time.time(), 0
    validation_path = out / "multihook_validation.json"
    for item in cohort:
        path = out / "samples" / ("%06d.json" % item["sample_i"])
        rec = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "sample_id": item["sample_id"], "sample_i": item["sample_i"], "old": item["old"], "new": item["new"], "layers": {}}
        assert all(rec[k] == item[k] for k in ("sample_id", "sample_i", "old", "new"))
        if len(rec["layers"]) == int(cfg.num_layers):
            continue
        req = item["row"]["request"]
        try:
            if param:
                for start in range(0, len(modules), args.layer_batch_size):
                    batch = modules[start:start + args.layer_batch_size]
                    if all(str(b["layer"]) in rec["layers"] for b in batch):
                        continue
                    try:
                        for b in batch:
                            param.set_params_trainable(b["params"], True)
                        old_loss, old = param.compute_all_layer_grads_for_target(vllm, batch, req["prompt"], req["image"], item["old"])
                        new_loss, new = param.compute_all_layer_grads_for_target(vllm, batch, req["prompt"], req["image"], item["new"])
                        for b in batch:
                            l = b["layer"]
                            rec["layers"][str(l)] = dict(cross_stats(param.grad_pair_stats(old[l], new[l])), old_loss=old_loss, new_loss=new_loss)
                        atomic_json(path, rec)
                        del old, new
                    finally:
                        for b in batch:
                            param.set_params_trainable(b["params"], False)
                        vllm.model.zero_grad(set_to_none=True)
                        torch.cuda.empty_cache()
                        gc.collect()
            else:
                old_loss, old, old_span = visual_all_grads(helper, vllm, modules, req["prompt"], req["image"], item["old"])
                new_loss, new, new_span = visual_all_grads(helper, vllm, modules, req["prompt"], req["image"], item["new"])
                assert old_span == new_span
                if not validation_path.exists():
                    # Compare whole tensors, not merely final Top-3, at shallow/middle/deep layers.
                    checked = []
                    for l in sorted({0, int(cfg.num_layers) // 2, int(cfg.num_layers) - 1}):
                        for target, gradients in [(item["old"], old), (item["new"], new)]:
                            single = helper.compute_virtual_delta_target_grad(vllm, modules[l], req["prompt"], req["image"], target, 1e-8)
                            torch.testing.assert_close(gradients[l], single["visual_grad"], rtol=1e-5, atol=1e-7)
                            checked.append(dict(layer=l, target=target, max_abs_error=float((gradients[l] - single["visual_grad"]).abs().max())))
                    atomic_json(validation_path, dict(status="passed", sample_id=item["sample_id"], checks=checked))
                for l in modules:
                    rec["layers"][str(l)] = dict(cross_stats(helper.grad_stats(old[l], new[l], 1e-8)), old_loss=old_loss, new_loss=new_loss, visual_span=old_span)
                atomic_json(path, rec)
                del old, new
                torch.cuda.empty_cache()
                gc.collect()
        except Exception:
            atomic_json(out / "summary.json", dict(status="failed", sample_id=item["sample_id"], error=traceback.format_exc(), updated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")))
            raise
        processed += 1
        atomic_json(out / "progress.json", dict(status="running", sample_i=item["sample_i"], sample_id=item["sample_id"], newly_processed=processed, expected_samples=len(cohort), elapsed_seconds=time.time() - started))
        print(json.dumps(dict(sample_i=item["sample_i"], sample_id=item["sample_id"], completed_layers=len(rec["layers"])), ensure_ascii=False), flush=True)
        if args.stop_after and processed >= args.stop_after:
            atomic_json(out / "summary.json", dict(status="smoke_only", processed_this_run=processed))
            return
    records = [json.loads((out / "samples" / ("%06d.json" % item["sample_i"])).read_text(encoding="utf-8")) for item in cohort]
    rows = aggregate(records, [r["sample_id"] for r in cohort], int(cfg.num_layers))
    historical_fields = {"dot": "score_raw", "cos": "score_lga_cos", "old_norm": "score_old_grad_norm", "new_norm": "score_new_grad_norm"} if param else {
        "dot": "S_v_dot", "cos": "S_v_cos", "old_norm": "S_v_old_norm", "new_norm": "S_v_new_norm", "no_direction": "S_v_joint_norm"}
    checks = [dict(layer=row["layer"], field=k, recomputed=row[k], historical=float(previous[col]),
                   passed=math.isclose(row[k], float(previous[col]), rel_tol=1e-3, abs_tol=1e-8))
              for row, previous in zip(rows, baseline) for k, col in historical_fields.items()]
    atomic_json(out / "historical_reproduction.json", checks)
    output = out / "layer_scores.json"
    atomic_json(output, dict(space=args.space, dataset=args.dataset, model=args.model, rows=rows))
    summary = dict(status="done" if all(c["passed"] for c in checks) else "needs_reproduction_review",
                   updated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), space=args.space, dataset=args.dataset, model=args.model,
                   sample_count=len(cohort), total_samples=DATASETS[args.dataset], layers=int(cfg.num_layers),
                   baseline_check_count=len(checks), baseline_failures=sum(not c["passed"] for c in checks),
                   score_sha256=sha(output), protocol_sha256=sha(out / "protocol.json"),
                   reproduction_sha256=sha(out / "historical_reproduction.json"),
                   sample_files={p.name: sha(p) for p in sorted((out / "samples").glob("*.json"))},
                   no_training=True, original_source=str(original_dir(args)))
    atomic_json(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if summary["status"] != "done":
        raise RuntimeError("historical gradient means changed; automatic document import disabled")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--space", choices=["parameter", "visual"], required=True)
    parser.add_argument("--dataset", choices=list(DATASETS), required=True)
    parser.add_argument("--model", choices=list(MODELS), required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--layer-batch-size", type=int, default=4)
    parser.add_argument("--stop-after", type=int, default=0, help="Smoke test only; never publishes recommendations")
    parser.add_argument("--preflight", action="store_true", help="Verify sources and cohort; do not load model or use GPU")
    args = parser.parse_args()
    if args.layer_batch_size < 1:
        parser.error("--layer-batch-size must be positive")
    args.project_dir, args.source_root, args.out_root = [str(Path(p).resolve()) for p in (args.project_dir, args.source_root, args.out_root)]
    run(args)


if __name__ == "__main__":
    main()
