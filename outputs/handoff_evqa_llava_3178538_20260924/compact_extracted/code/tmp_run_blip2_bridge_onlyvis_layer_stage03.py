import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


VIS_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
RUN_ROOT = VIS_ROOT.parent
TEN_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge")
PY = Path("/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python")
DATA = VIS_ROOT / "data" / "bridge" / "edit_30_bridge_train_only_vis.json"
VAL_DIR = TEN_ROOT / "bridge_val"
VAL_EDIT_DATA = VAL_DIR / "edit_30_bridge_val_eval_only_vis.json"
OUT_DIR = VAL_DIR / "onlyvis" / "open_end"
JOB_LOG_DIR = VIS_ROOT / "records" / "job_logs"


def run_cmd(args):
    print("RUN:", " ".join(str(a) for a in args), flush=True)
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_DATASETS_OFFLINE"] = "1"
    subprocess.run([str(a) for a in args], check=True, cwd=str(RUN_ROOT), env=env)


def parse_args():
    parser = argparse.ArgumentParser(description="Train/eval BLIP2 bridge only-vis for one edit layer.")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--target_loss", type=float, default=0.30)
    return parser.parse_args()


def ensure_layout():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JOB_LOG_DIR.mkdir(parents=True, exist_ok=True)
    vead_link = RUN_ROOT / "VEAD"
    models_link = RUN_ROOT / "models"
    if not vead_link.exists():
        vead_link.symlink_to(VIS_ROOT, target_is_directory=True)
    if not models_link.exists():
        models_link.symlink_to(VIS_ROOT / "models", target_is_directory=True)


def pick_closest_ckpt(ckpt_dir: Path, target_loss: float):
    best = None
    best_gap = None
    for ckpt in ckpt_dir.iterdir():
        name = ckpt.name
        if "ema_loss-" not in name:
            continue
        try:
            ema_loss = float(name.split("ema_loss-")[-1])
        except ValueError:
            continue
        gap = abs(ema_loss - target_loss)
        if best is None or gap < best_gap:
            best = {"path": ckpt, "ema_loss": ema_loss}
            best_gap = gap
    if best is None:
        raise RuntimeError(f"No checkpoint with ema_loss found in {ckpt_dir}")
    return best


def summarize_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    total = len(rows)
    strict = sum(int(r.get("strict_acc", 0)) for r in rows)
    loose = sum(int(r.get("loose_acc", 0)) for r in rows)
    return {
        "path": str(path),
        "total": total,
        "strict_correct": strict,
        "strict_acc": (strict / total) if total else 0.0,
        "loose_correct": loose,
        "loose_acc": (loose / total) if total else 0.0,
    }


def main():
    args = parse_args()
    ensure_layout()

    layer = args.layer
    tag = f"l{layer}"
    config_path = TEN_ROOT / f"blip2-opt-2.7b-bridge-only-vis-{tag}.yaml"
    cache_root = VIS_ROOT / f"data_bridge_noport_onlyvis_blip2_{tag}"
    train_name = f"blip2_bridge_noport_only_vis_{tag}"

    if cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)

    run_cmd(
        [
            PY,
            VIS_ROOT / "bridge_train_only_vis.py",
            "-dvc",
            "cuda:0",
            "-edvc",
            "0",
            "-bs",
            "1",
            "-eps",
            str(args.epochs),
            "-tnp",
            train_name,
            "-sci",
            "100",
            "-lpi",
            "1",
            "--config",
            config_path,
            "--data_path",
            DATA,
            "--cache_root",
            cache_root,
        ]
    )

    # bridge_train_only_vis.py writes records relative to RUN_ROOT because run_cmd
    # executes with cwd=RUN_ROOT, so checkpoints live under /Visedit2/records.
    records_root = RUN_ROOT / "records" / "vead" / "blip2-opt-2.7b"
    run_dirs = sorted(records_root.glob(f"{train_name}-*"))
    if not run_dirs:
        raise RuntimeError(f"No training run found for {train_name}")
    run_dir = run_dirs[-1]
    ckpt_info = pick_closest_ckpt(run_dir / "checkpoints", args.target_loss)
    ckpt = ckpt_info["path"]

    entity_out = OUT_DIR / f"bridge_val_entity_recog_ckpt_blip2_{tag}_{ckpt.name.replace('.', '_')}.jsonl"
    open_out = OUT_DIR / f"bridge_val_openend_ckpt_blip2_{tag}_{ckpt.name.replace('.', '_')}.jsonl"
    summary_out = JOB_LOG_DIR / f"bridge_blip2_{tag}_{ckpt.name.replace('.', '_')}_eval_summary.json"

    run_cmd(
        [
            PY,
            VIS_ROOT / "tmp_eval_blip2_bridge_ckpt.py",
            "--split_dir",
            VAL_DIR,
            "--visedit_root",
            VIS_ROOT,
            "--device",
            "cuda:0",
            "--ckpt_path",
            ckpt,
            "--config_path",
            config_path,
            "--edit_data_path",
            VAL_EDIT_DATA,
            "--entity_out",
            entity_out,
            "--open_out",
            open_out,
            "--summary_out",
            summary_out,
        ]
    )

    final_summary = {
        "layer": layer,
        "target_loss": args.target_loss,
        "selected_checkpoint": str(ckpt),
        "selected_ema_loss": ckpt_info["ema_loss"],
        "entity_recognition": summarize_jsonl(entity_out),
        "open_end": summarize_jsonl(open_out),
        "run_dir": str(run_dir),
        "eval_summary_path": str(summary_out),
    }
    final_path = JOB_LOG_DIR / f"bridge_blip2_{tag}_stage03_summary.json"
    final_path.write_text(json.dumps(final_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(final_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
