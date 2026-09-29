#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

DATA = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json")
OUT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_formal_multinoise_multiseed_v1_20260906/manifests/full636.json")

rows = json.loads(DATA.read_text(encoding="utf-8"))
ids = [str(row.get("sample_id", f"mmke_{i}")) for i, row in enumerate(rows)]
if len(ids) != 636 or len(set(ids)) != 636:
    raise RuntimeError(f"expected 636 unique IDs, got rows={len(ids)}, unique={len(set(ids))}")
if ids != [f"mmke_{i}" for i in range(636)]:
    raise RuntimeError("dataset sample ID/order differs from audited mmke_0..mmke_635 manifest")
obj = {
    "purpose": "formal 636-sample CMA rerun",
    "selection_rule": "all 636 audited common localization sample IDs in immutable dataset order",
    "sample_ids": ids,
}
payload = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
OUT.parent.mkdir(parents=True, exist_ok=True)
tmp = OUT.with_suffix(".tmp")
tmp.write_text(payload, encoding="utf-8")
os.replace(tmp, OUT)
print(f"rows={len(ids)} unique={len(set(ids))} sha256={hashlib.sha256(payload.encode()).hexdigest()} out={OUT}")
