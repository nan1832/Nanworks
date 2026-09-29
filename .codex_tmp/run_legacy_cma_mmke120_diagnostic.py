#!/usr/bin/env python3
"""Read-only-formula diagnostic: replay mmke_120 through the historical runner."""

import argparse
import importlib.util
from pathlib import Path

PROJECT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
RUNNER = PROJECT / "scripts" / "run_cma_direct_candidate_layers.py"
spec = importlib.util.spec_from_file_location("legacy_cma_exact", RUNNER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

original_load = mod.load_edit_data


def load_only_mmke120(dataset_name, data_path, img_root, data_n=None):
    rows = original_load(dataset_name, data_path, img_root, 121)
    selected = [row for i, row in enumerate(rows) if mod.get_sample_id(row, i) == "mmke_120"]
    if len(selected) != 1:
        raise RuntimeError(f"expected one mmke_120 row, got {len(selected)}")
    return selected


mod.load_edit_data = load_only_mmke120
args = argparse.Namespace(
    model_name="qwen2.5-vl-3b",
    dataset_name="mmke-entity",
    out_dir="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_formal_multinoise_multiseed_v1_20260906/historical_control_exact_runner",
    device="cuda:0",
    data_path="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json",
    img_root="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image",
    data_n=None,
    noise_scales="1",
    repeats="2026",
    delta_logprob=0.05,
    eps=1e-8,
    epsilon_sigma=1e-6,
    min_valid_ratio=0.05,
    empty_cache_every=1,
    resume=False,
)
mod.run_one(args)
