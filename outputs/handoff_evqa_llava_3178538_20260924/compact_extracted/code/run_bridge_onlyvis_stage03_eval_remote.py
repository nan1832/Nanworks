import json
import os
import subprocess
from pathlib import Path


VIS_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
RUN_ROOT = VIS_ROOT.parent
TEN_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge")
PY = Path("/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python")
MODEL_PATH = VIS_ROOT / "models" / "llava-v1.5-7b-hf"
VAL_DIR = TEN_ROOT / "bridge_val"
VAL_EDIT_DATA = VAL_DIR / "edit_30_bridge_val_eval_only_vis.json"
OUT_DIR = VAL_DIR / "onlyvis" / "open_end"
SUMMARY_PATH = VIS_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_eval_summary.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

STAGE = {
    "l1": {
        "ckpt": VIS_ROOT / "records" / "vead" / "llava-v1.5-7b" / "bridge_noport_only_vis_l1-2026.04.12-06.43.51" / "checkpoints" / "epoch-67-i-2000-ema_loss-0.3015",
        "cfg": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l1.yaml",
        "ema_loss": 0.3015,
    },
    "l18": {
        "ckpt": VIS_ROOT / "records" / "vead" / "llava-v1.5-7b" / "bridge_noport_only_vis-2026.04.07-09.24.21" / "checkpoints" / "epoch-184-i-5500-ema_loss-0.3012",
        "cfg": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l18.yaml",
        "ema_loss": 0.3012,
    },
    "l20": {
        "ckpt": VIS_ROOT / "records" / "vead" / "llava-v1.5-7b" / "bridge_noport_only_vis_l20_resume400-2026.04.11-20.37.31" / "checkpoints" / "epoch-166-i-5000-ema_loss-0.3003",
        "cfg": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l20.yaml",
        "ema_loss": 0.3003,
    },
}


def run_cmd(args):
    print("RUN:", " ".join(str(a) for a in args), flush=True)
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    subprocess.run([str(a) for a in args], check=True, env=env, cwd=str(RUN_ROOT))


def ensure_layout():
    vead_link = RUN_ROOT / "VEAD"
    models_link = RUN_ROOT / "models"
    if not vead_link.exists():
        vead_link.symlink_to(VIS_ROOT, target_is_directory=True)
    if not models_link.exists():
        models_link.symlink_to(VIS_ROOT / "models", target_is_directory=True)


def summarize_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
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
    ensure_layout()
    entity_script = VIS_ROOT / "eval_llava_bridge_entity_recognition_ckpt.py"
    openend_script = VIS_ROOT / "edit_30_bridge_val_eval_only_vis.py"

    for tag, info in STAGE.items():
        entity_out = OUT_DIR / f"bridge_val_entity_recog_ckpt_stage03_{tag}.jsonl"
        openend_out = OUT_DIR / f"bridge_val_openend_onlyvis_ckpt_stage03_{tag}.jsonl"

        if not entity_out.exists():
            run_cmd([
                PY,
                entity_script,
                "--split_dir", VAL_DIR,
                "--model", MODEL_PATH,
                "--out", entity_out,
                "--ckpt", info["ckpt"],
                "--device", "cuda:0",
                "--config", info["cfg"],
                "--edit_data_path", VAL_EDIT_DATA,
                "--visedit_root", VIS_ROOT,
            ])
        else:
            print(f"SKIP existing entity output: {entity_out}", flush=True)

        if not openend_out.exists():
            run_cmd([
                PY,
                openend_script,
                "--split_dir", VAL_DIR,
                "--model", MODEL_PATH,
                "--out", openend_out,
                "--ckpt", info["ckpt"],
                "--device", "cuda:0",
                "--config", info["cfg"],
                "--edit_data_path", VAL_EDIT_DATA,
                "--visedit_root", VIS_ROOT,
            ])
        else:
            print(f"SKIP existing open-end output: {openend_out}", flush=True)

    summary = {
        "stage_loss_target": 0.30,
        "checkpoints": {
            tag: {
                "ckpt_path": str(info["ckpt"]),
                "ema_loss": info["ema_loss"],
            }
            for tag, info in STAGE.items()
        },
        "entity_recognition": {
            tag: summarize_jsonl(OUT_DIR / f"bridge_val_entity_recog_ckpt_stage03_{tag}.jsonl")
            for tag in STAGE
        },
        "open_end_qa": {
            tag: summarize_jsonl(OUT_DIR / f"bridge_val_openend_onlyvis_ckpt_stage03_{tag}.jsonl")
            for tag in STAGE
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(SUMMARY_PATH, flush=True)


if __name__ == "__main__":
    main()
