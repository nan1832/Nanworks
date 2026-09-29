#!/usr/bin/env python3
"""Wait for Ours-Direct launcher, then repair/rerun failed groups.

This script is intended to run inside the same Slurm allocation/GPU visibility
as the original Ours-Direct launcher.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DATASETS = ["evqa-pilot500", "mmke-visual", "mmke-entity"]
MODELS = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b",
    "paligemma-3b",
    "smolvlm-1.7b",
]


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pid_alive(pid: int) -> bool:
    return pid > 0 and Path(f"/proc/{pid}").exists()


def ps_rows() -> List[Tuple[int, str]]:
    out = subprocess.check_output(["ps", "-eo", "pid=,cmd="], text=True, errors="replace")
    rows: List[Tuple[int, str]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        pid_s, _, cmd = line.partition(" ")
        try:
            rows.append((int(pid_s), cmd.strip()))
        except ValueError:
            continue
    return rows


def heavy_processes(patterns: Iterable[str]) -> List[Tuple[int, str]]:
    self_pid = os.getpid()
    hits = []
    for pid, cmd in ps_rows():
        if pid == self_pid:
            continue
        if any(p in cmd for p in patterns):
            hits.append((pid, cmd))
    return hits


def wait_until_idle(wait_pid: Optional[int], wait_patterns: List[str], poll_sec: int) -> None:
    if wait_pid:
        while pid_alive(wait_pid):
            print(f"[{now()}] waiting launcher pid={wait_pid}", flush=True)
            time.sleep(poll_sec)
    while True:
        hits = heavy_processes(wait_patterns)
        if not hits:
            return
        compact = "; ".join(f"{pid}:{cmd[:120]}" for pid, cmd in hits[:5])
        print(f"[{now()}] waiting GPU-heavy processes: {compact}", flush=True)
        time.sleep(poll_sec)


def run(cmd: List[str], cwd: Path, log_path: Optional[Path] = None) -> int:
    print(f"[{now()}] RUN: {' '.join(cmd)}", flush=True)
    if log_path is None:
        return subprocess.call(cmd, cwd=str(cwd))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n\n===== {now()} =====\n")
        f.write(" ".join(cmd) + "\n")
        f.flush()
        return subprocess.call(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)


def collect(project_root: Path, python_bin: str, run_root: Path) -> None:
    run(
        [
            python_bin,
            "scripts/run_ours_direct_candidate_layers.py",
            "collect",
            "--run-root",
            str(run_root),
        ],
        cwd=project_root,
        log_path=run_root / "logs" / "ours_direct_repair_collect.log",
    )


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "bad_summary", "error": repr(exc)}


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def to_float(row: Dict[str, str], key: str) -> Optional[float]:
    try:
        value = float(row.get(key, ""))
    except Exception:
        return None
    return value if math.isfinite(value) else None


def compute_abs_candidates(layer_csv: Path, topk: int = 5) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    if not layer_csv.exists():
        return [], [], []
    scored: List[Dict[str, Any]] = []
    with layer_csv.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("valid_for_ours_direct") and not truthy(row.get("valid_for_ours_direct")):
                continue
            if truthy(row.get("S_v_zero_grad")):
                continue
            cos = to_float(row, "S_v_cos")
            new_norm = to_float(row, "S_v_new_norm")
            depth2 = to_float(row, "S_v_depth2")
            n_request = to_float(row, "n_request")
            if cos is None or new_norm is None or depth2 is None or not n_request or n_request <= 0:
                continue
            score = abs(cos) * new_norm * depth2
            if not math.isfinite(score) or score <= 0:
                continue
            layer = int(float(row.get("layer", 0)))
            item = dict(row)
            item["S_ours_abs_direction"] = score
            item["_layer_int"] = layer
            scored.append(item)
    scored.sort(key=lambda r: (-float(r["S_ours_abs_direction"]), int(r["_layer_int"])))
    for rank, row in enumerate(scored, 1):
        row["abs_direction_rank"] = rank
        row.pop("_layer_int", None)
    top = [r.get("layer_name") or f"L{int(float(r['layer']))}" for r in scored[:topk]]
    return scored, top[:3], top[:5]


def write_abs_outputs(out_dir: Path, summary: Dict[str, Any]) -> Tuple[List[str], List[str], str]:
    layer_csv = Path(summary.get("layer_scores_csv") or out_dir / "ours_direct_layer_scores.csv")
    scored, top3, top5 = compute_abs_candidates(layer_csv)
    status = "computed_from_layer_scores" if scored else "no_valid_abs_direction_layer"
    if scored:
        fieldnames = list(scored[0].keys())
        score_csv = out_dir / "ours_direct_abs_direction_layer_scores.csv"
        with score_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(scored)
    abs_summary = {
        "dataset_key": summary.get("dataset_key"),
        "dataset": summary.get("dataset"),
        "model_key": summary.get("model_key"),
        "model": summary.get("model"),
        "method": "Ours-Direct-AbsDirection-Diagnostic",
        "formula": "abs(S_v_cos) * S_v_new_norm * ((l + 1) / num_layers)^2",
        "source_layer_scores_csv": str(layer_csv),
        "status": status,
        "top3_layers": top3,
        "top5_layers": top5,
        "computed_at": now(),
    }
    (out_dir / "summary_abs_direction.json").write_text(
        json.dumps(abs_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "ours_direct_abs_direction_candidates.json").write_text(
        json.dumps({"status": status, "top3_layers": top3, "top5_layers": top5}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return top3, top5, status


def unique_backup_path(path: Path, tag: str) -> Path:
    candidate = path.with_name(path.name + f".pre_repair_{tag}")
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        alt = path.with_name(path.name + f".pre_repair_{tag}_{i}")
        if not alt.exists():
            return alt
        i += 1


def clean_for_rerun(out_dir: Path, tag: str) -> None:
    if out_dir.exists():
        backup = unique_backup_path(out_dir, tag)
        shutil.move(str(out_dir), str(backup))
        print(f"[{now()}] backed up {out_dir} -> {backup}", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)


def should_gpu_rerun(summary: Optional[Dict[str, Any]], abs_status: str, out_dir: Path) -> Tuple[bool, str]:
    if summary is None:
        return True, "missing_summary"
    status = str(summary.get("status") or "")
    common_valid = summary.get("common_valid_sample_count")
    try:
        common_valid_n = int(common_valid)
    except Exception:
        common_valid_n = 0
    if status in {"done", "low_confidence"}:
        return False, status
    if abs_status == "computed_from_layer_scores" and common_valid_n > 0:
        return False, "repaired_by_abs_direction"
    if status == "failed" and common_valid_n <= 0:
        return True, "failed_no_common_valid_samples"
    if not (out_dir / "ours_direct_layer_scores.csv").exists():
        return True, "missing_layer_scores"
    return False, f"kept_{status or 'unknown'}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--python-bin", required=True)
    parser.add_argument("--wait-pid", type=int, default=0)
    parser.add_argument("--poll-sec", type=int, default=300)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--wait-perturb-kl", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    run_root = Path(args.run_root).resolve()
    repair_root = run_root / "repair"
    repair_root.mkdir(parents=True, exist_ok=True)
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    patterns = ["run_ours_direct_candidate_layers.py run-one"]
    if args.wait_perturb_kl:
        patterns.append("run_perturb_kl_direct_candidate_layers.py run-one")

    print(f"[{now()}] repair monitor started", flush=True)
    wait_until_idle(args.wait_pid or None, patterns, args.poll_sec)
    print(f"[{now()}] launcher/GPU-heavy processes are idle; collecting", flush=True)
    collect(project_root, args.python_bin, run_root)

    decision_rows: List[Dict[str, Any]] = []
    rerun_queue: List[Tuple[str, str, str]] = []
    for dataset in DATASETS:
        for model in MODELS:
            out_dir = run_root / dataset / model
            summary = read_json(out_dir / "summary.json")
            main_status = summary.get("status") if summary else "missing"
            top3_abs: List[str] = []
            top5_abs: List[str] = []
            abs_status = "no_summary"
            if summary and (out_dir / "ours_direct_layer_scores.csv").exists():
                top3_abs, top5_abs, abs_status = write_abs_outputs(out_dir, summary)
            rerun, reason = should_gpu_rerun(summary, abs_status, out_dir)
            decision_rows.append(
                {
                    "dataset": dataset,
                    "model": model,
                    "main_status": main_status,
                    "valid_samples": "" if not summary else summary.get("common_valid_sample_count", ""),
                    "main_top3": "" if not summary else ",".join(summary.get("top3_layers") or []),
                    "abs_top3": ",".join(top3_abs),
                    "abs_top5": ",".join(top5_abs),
                    "abs_status": abs_status,
                    "repair_action": "gpu_rerun" if rerun else reason,
                }
            )
            if rerun:
                rerun_queue.append((dataset, model, reason))

    decision_csv = repair_root / f"ours_direct_repair_decisions_{tag}.csv"
    with decision_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(decision_rows[0].keys()) if decision_rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(decision_rows)

    decision_md = repair_root / f"ours_direct_repair_decisions_{tag}.md"
    with decision_md.open("w", encoding="utf-8") as f:
        f.write("# Ours-Direct repair decisions\n\n")
        f.write(f"Run root: `{run_root}`\n\n")
        f.write("| Dataset | Model | Main Status | Valid | Main Top-3 | Abs Top-3 | Abs Top-5 | Abs Status | Action |\n")
        f.write("|---|---|---:|---:|---|---|---|---|---|\n")
        for r in decision_rows:
            f.write(
                f"| {r['dataset']} | {r['model']} | {r['main_status']} | {r['valid_samples']} | "
                f"{r['main_top3'] or '-'} | {r['abs_top3'] or '-'} | {r['abs_top5'] or '-'} | "
                f"{r['abs_status']} | {r['repair_action']} |\n"
            )
        f.write("\n## GPU rerun queue\n\n")
        if rerun_queue:
            for dataset, model, reason in rerun_queue:
                f.write(f"- {dataset} / {model}: {reason}\n")
        else:
            f.write("- empty\n")

    print(f"[{now()}] repair decisions: {decision_md}", flush=True)

    for dataset, model, reason in rerun_queue:
        out_dir = run_root / dataset / model
        print(f"[{now()}] GPU rerun {dataset}/{model}: {reason}", flush=True)
        clean_for_rerun(out_dir, tag)
        log_file = run_root / "logs" / f"ours_direct_repair_{dataset}_{model}_{tag}.log"
        status = run(
            [
                args.python_bin,
                "scripts/run_ours_direct_candidate_layers.py",
                "run-one",
                "--dataset-name",
                dataset,
                "--model-name",
                model,
                "--out-dir",
                str(out_dir),
                "--device",
                args.device,
                "--max-new-tokens",
                str(args.max_new_tokens),
            ],
            cwd=project_root,
            log_path=log_file,
        )
        print(f"[{now()}] rerun finished {dataset}/{model}: status={status}", flush=True)
        collect(project_root, args.python_bin, run_root)
        # Refresh abs-direction outputs for this rerun as well.
        summary = read_json(out_dir / "summary.json")
        if summary and (out_dir / "ours_direct_layer_scores.csv").exists():
            write_abs_outputs(out_dir, summary)

    collect(project_root, args.python_bin, run_root)
    print(f"[{now()}] repair monitor finished", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
