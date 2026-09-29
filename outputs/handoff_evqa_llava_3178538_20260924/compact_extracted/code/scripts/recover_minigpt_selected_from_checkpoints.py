#!/usr/bin/env python3
"""Recover selected_checkpoint.tsv/train.done after a missing-history selection failure.

The training runner completed all epochs and wrote checkpoint files, but its
synchronous loop did not invoke the history callback.  This utility selects
the minimum finite EMA checkpoint using the checkpoint's own serialized
metadata.  It does not evaluate or delete any checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

import torch


CKPT_RE = re.compile(r"^epoch-(\d+)-i-(\d+)-ema_loss-([^/]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def recover_layer(out_root: Path, layer: int) -> dict:
    layer_dir = out_root / f"layer_{layer:02d}"
    candidates = []
    for path in layer_dir.glob("records/**/checkpoints/epoch-*"):
        if not path.is_file() or path.name.endswith(".lock"):
            continue
        match = CKPT_RE.fullmatch(path.name)
        if not match:
            continue
        rounded_ema = float(match.group(3))
        if math.isfinite(rounded_ema):
            candidates.append((rounded_ema, int(match.group(1)), int(match.group(2)), path))
    if len(candidates) != 50:
        raise RuntimeError(f"L{layer}: expected 50 finite checkpoint files, found {len(candidates)}")

    # Four-decimal names define non-overlapping rounding intervals.  Load every
    # checkpoint tied at the smallest filename value, then compare exact EMA.
    min_rounded = min(row[0] for row in candidates)
    tied = [row for row in candidates if row[0] == min_rounded]
    exact = []
    for _, filename_epoch, filename_i, path in tied:
        payload = torch.load(path, map_location="cpu")
        epoch = int(payload["epoch"])
        train_i = int(payload["i"])
        loss = float(payload["loss"])
        ema_loss = float(payload["ema_loss"])
        if epoch != filename_epoch or train_i != filename_i:
            raise RuntimeError(f"L{layer}: checkpoint metadata/name mismatch: {path}")
        if not math.isfinite(loss) or not math.isfinite(ema_loss):
            raise RuntimeError(f"L{layer}: nonfinite selected candidate: {path}")
        if "train_modules" not in payload or "opt" not in payload:
            raise RuntimeError(f"L{layer}: incomplete checkpoint payload: {path}")
        exact.append((ema_loss, epoch, train_i, loss, path))
        del payload

    ema_loss, epoch, train_i, loss, selected = min(exact, key=lambda row: row[0])
    selected = selected.resolve()
    record = {
        "layer": layer,
        "status": "TRAIN_DONE",
        "epoch": epoch,
        "i": train_i,
        "loss": loss,
        "ema_loss": ema_loss,
        "checkpoint": str(selected),
    }

    header = ["layer", "status", "epoch", "i", "loss", "ema_loss", "checkpoint"]
    tsv_lines = ["\t".join(header), "\t".join(str(record[key]) for key in header)]
    atomic_text(layer_dir / "selected_checkpoint.tsv", "\n".join(tsv_lines) + "\n")
    atomic_text(layer_dir / "train.done", json.dumps(record, indent=2) + "\n")

    audit = {
        "reason": "recovered_after_synchronous_history_callback_omission",
        "checkpoint_count": len(candidates),
        "minimum_rounded_ema": min_rounded,
        "tied_minimum_candidates_loaded": len(tied),
        "selected": record,
        "selected_sha256": sha256(selected),
    }
    atomic_text(layer_dir / "selection_recovery.json", json.dumps(audit, indent=2) + "\n")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--layers", default="10,11")
    args = parser.parse_args()

    reports = []
    for layer_text in args.layers.split(","):
        layer = int(layer_text.strip())
        report = recover_layer(args.out_root, layer)
        reports.append(report)
        selected = report["selected"]
        print(
            f"RECOVERED L{layer} epoch={selected['epoch']} i={selected['i']} "
            f"loss={selected['loss']:.12g} ema={selected['ema_loss']:.12g} "
            f"sha256={report['selected_sha256']}"
        )

    summary = args.out_root / "selection_recovery_L10_L11.json"
    atomic_text(summary, json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
