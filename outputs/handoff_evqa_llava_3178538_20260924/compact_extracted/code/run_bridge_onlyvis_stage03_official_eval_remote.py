import json
import os
import subprocess
import sys
from pathlib import Path


RUN_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
PYTHON = "/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python"
SUMMARY_PATH = RUN_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_official_eval_summary.json"


STAGES = [
    {
        "layer": "l1",
        "ema_loss": 0.3015,
        "ckpt": RUN_ROOT / "records" / "vead" / "llava-v1.5-7b" /
        "bridge_noport_only_vis_l1-2026.04.12-06.43.51" / "checkpoints" /
        "epoch-67-i-2000-ema_loss-0.3015",
        "config": RUN_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l1.yaml",
        "postfix": "stage03-official-l1",
    },
    {
        "layer": "l18",
        "ema_loss": 0.3012,
        "ckpt": RUN_ROOT / "records" / "vead" / "llava-v1.5-7b" /
        "bridge_noport_only_vis-2026.04.07-09.24.21" / "checkpoints" /
        "epoch-184-i-5500-ema_loss-0.3012",
        "config": RUN_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l18.yaml",
        "postfix": "stage03-official-l18",
    },
    {
        "layer": "l20",
        "ema_loss": 0.3003,
        "ckpt": RUN_ROOT / "records" / "vead" / "llava-v1.5-7b" /
        "bridge_noport_only_vis_l20_resume400-2026.04.11-20.37.31" / "checkpoints" /
        "epoch-166-i-5000-ema_loss-0.3003",
        "config": RUN_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l20.yaml",
        "postfix": "stage03-official-l20",
    },
]


def result_dir(postfix: str) -> Path:
    return RUN_ROOT / "eval_results" / "vead" / "llava-v1.5-7b" / f"EditBridge-val-{postfix}" / "single_edit"


def mean_result_path(postfix: str) -> Path:
    return result_dir(postfix) / "mean_results.json"


def run_one(stage: dict) -> dict:
    out_path = mean_result_path(stage["postfix"])
    if not out_path.exists():
        cmd = [
            PYTHON,
            str(RUN_ROOT / "bridge_Bport_eval.py"),
            "-dvc", "cuda:0",
            "-ckpt", str(stage["ckpt"]),
            "--split", "val",
            "-enp", stage["postfix"],
            "--config", str(stage["config"]),
        ]
        env = os.environ.copy()
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["HF_DATASETS_OFFLINE"] = "1"
        subprocess.run(cmd, cwd=str(RUN_ROOT), env=env, check=True)

    with open(out_path, "r", encoding="utf-8") as f:
        mean_res = json.load(f)

    return {
        "layer": stage["layer"],
        "ema_loss": stage["ema_loss"],
        "checkpoint": stage["ckpt"].name,
        "result_dir": str(result_dir(stage["postfix"])),
        "reliability_acc": mean_res.get("reliability", {}).get("acc"),
        "generality_text_rephrase_acc": mean_res.get("generality", {}).get("text_rephrase", {}).get("acc"),
        "generality_image_rephrase_acc": mean_res.get("generality", {}).get("image_rephrase", {}).get("acc"),
        "locality_text_loc_acc": mean_res.get("locality", {}).get("text_loc", {}).get("acc"),
        "locality_image_loc_acc": mean_res.get("locality", {}).get("image_loc", {}).get("acc"),
        "portability_overall_acc": mean_res.get("portability", {}).get("overall", {}).get("acc"),
        "portability_overall_count": mean_res.get("portability", {}).get("overall", {}).get("count"),
        "portability_1hop_acc": mean_res.get("portability", {}).get("per_hop", {}).get("1hop", {}).get("acc"),
        "portability_1hop_count": mean_res.get("portability", {}).get("per_hop", {}).get("1hop", {}).get("count"),
        "portability_2hop_acc": mean_res.get("portability", {}).get("per_hop", {}).get("2hop", {}).get("acc"),
        "portability_2hop_count": mean_res.get("portability", {}).get("per_hop", {}).get("2hop", {}).get("count"),
    }


def main() -> int:
    records = []
    for stage in STAGES:
        print(f"=== stage03 official eval: {stage['layer']} ===", flush=True)
        records.append(run_one(stage))

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"saved summary -> {SUMMARY_PATH}", flush=True)

    subprocess.run(
        [PYTHON, str(RUN_ROOT / "render_bridge_onlyvis_stage03_official_table.py")],
        cwd=str(RUN_ROOT),
        check=True,
    )
    print("rendered official stage03 tables", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
