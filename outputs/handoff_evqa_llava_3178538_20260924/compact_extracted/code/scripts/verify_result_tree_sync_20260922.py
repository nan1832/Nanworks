#!/usr/bin/env python3
"""Build a machine-readable completion manifest for an HPC result tree."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

SAMPLES = {"evqa-pilot500": 2093, "mmke-visual": 293, "mmke-entity": 954}
METRICS = ("Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average")
MODELS = (
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b",
    "paligemma-3b",
    "smolvlm-1.7b",
)


def infer_model(path: Path) -> str:
    text = str(path).lower()
    for model in MODELS:
        if model in text:
            return model
    if "blip2" in text:
        return "blip2-opt-2.7b"
    return "unknown"


def load_json(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}, "JSON root is not an object"
        return value, None
    except Exception as exc:  # noqa: BLE001 - report malformed experiment files
        return {}, f"invalid JSON: {exc}"


def selected_row(path: Path) -> Tuple[Dict[str, str], Optional[str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        if not rows:
            return {}, "selected checkpoint table has no data row"
        row = rows[-1]
        if not row.get("checkpoint"):
            return row, "selected checkpoint path is missing"
        return row, None
    except Exception as exc:  # noqa: BLE001
        return {}, f"invalid selected checkpoint table: {exc}"


def result_files(layer_dir: Path) -> List[Path]:
    eval_dir = layer_dir / "eval_full"
    if not eval_dir.is_dir():
        return []
    return sorted(path for path in eval_dir.rglob("results.json") if path.is_file() and path.stat().st_size > 0)


def complete_metrics(data: Dict[str, Any]) -> bool:
    return all(key in data and isinstance(data[key], (int, float)) for key in METRICS)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: Path, layer_dir: Path, *, calculate_hash: bool = True) -> Dict[str, Any]:
    return {
        "path": str(path),
        "relative_path": path.relative_to(layer_dir).as_posix(),
        "size": path.stat().st_size,
        "sha256": sha256_file(path) if calculate_hash else None,
    }


def inspect_layer(layer_dir: Path, dataset: str, hash_checkpoints: bool) -> Dict[str, Any]:
    layer = int(layer_dir.name.split("_", 1)[1])
    errors = []  # type: List[str]
    train = layer_dir / "train.done"
    selected = layer_dir / "selected_checkpoint.tsv"
    evaluation = layer_dir / "eval_full.done"

    if not train.is_file():
        errors.append("missing_train.done")
    if not selected.is_file() or selected.stat().st_size == 0:
        errors.append("missing_or_empty_selected_checkpoint.tsv")
        selected_data = {}  # type: Dict[str, str]
    else:
        selected_data, selected_error = selected_row(selected)
        if selected_error:
            errors.append(selected_error)

    checkpoint = Path(selected_data.get("checkpoint", "")) if selected_data.get("checkpoint") else None
    if checkpoint is not None and (not checkpoint.is_file() or checkpoint.stat().st_size == 0):
        errors.append("selected_physical_checkpoint_missing_or_empty")

    if not evaluation.is_file() or evaluation.stat().st_size == 0:
        errors.append("missing_or_empty_eval_full.done")
        eval_data = {}  # type: Dict[str, Any]
    else:
        eval_data, eval_error = load_json(evaluation)
        if eval_error:
            errors.append(eval_error)
        if eval_data.get("status") != "EVAL_DONE":
            errors.append("eval_status_is_not_EVAL_DONE")
        samples = eval_data.get("eval_samples", eval_data.get("samples"))
        try:
            samples = int(samples)
        except (TypeError, ValueError):
            samples = None
        if samples != SAMPLES[dataset]:
            errors.append(f"unexpected_eval_samples:{samples}")

    results = result_files(layer_dir)
    if not results and not complete_metrics(eval_data):
        errors.append("missing_complete_evaluation_metrics")

    artifacts = [path for path in (train, selected, evaluation) if path.is_file()]
    artifacts.extend(results)
    for name in ("selection_repair.done", "resume.done"):
        marker = layer_dir / name
        if marker.is_file():
            artifacts.append(marker)

    return {
        "dataset": dataset,
        "model": infer_model(layer_dir),
        "layer": layer,
        "layer_dir": str(layer_dir),
        "complete": not errors,
        "errors": errors,
        "selected": selected_data,
        "selected_checkpoint": (
            {
                "path": str(checkpoint),
                "relative_path": f"selected_checkpoint/{checkpoint.name}",
                "size": checkpoint.stat().st_size,
                "sha256": sha256_file(checkpoint) if hash_checkpoints else None,
            }
            if checkpoint is not None and checkpoint.is_file()
            else None
        ),
        "evaluation": {key: eval_data.get(key) for key in ("status", "eval_samples", *METRICS)},
        "artifacts": [artifact_record(path, layer_dir) for path in artifacts],
    }


def inspect_tree(root: Path, dataset: str, hash_checkpoints: bool) -> Dict[str, Any]:
    root = root.resolve(strict=True)
    layers = []  # type: List[Dict[str, Any]]
    for base, dirs, _files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in {"cache", "records", "eval_full"}]
        current = Path(base)
        if re.fullmatch(r"layer_\d+", current.name):
            layers.append(inspect_layer(current, dataset, hash_checkpoints))
            dirs[:] = []
    layers.sort(key=lambda item: (item["model"], item["layer"]))
    return {
        "root": str(root),
        "dataset": dataset,
        "expected_eval_samples": SAMPLES[dataset],
        "complete_count": sum(bool(item["complete"]) for item in layers),
        "incomplete_count": sum(not item["complete"] for item in layers),
        "layers": layers,
    }


def write_output(path: Optional[Path], data: Dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    temp = path.with_suffix(path.suffix + ".partial")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--dataset", required=True, choices=tuple(SAMPLES))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="return nonzero if any discovered layer is incomplete")
    parser.add_argument(
        "--hash-checkpoints",
        action="store_true",
        help="also hash the large selected checkpoint files before optional synchronization",
    )
    args = parser.parse_args()
    data = inspect_tree(args.root, args.dataset, args.hash_checkpoints)
    write_output(args.output, data)
    return 2 if args.strict and data["incomplete_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
