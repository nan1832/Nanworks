import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


VIS_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main")
RUN_ROOT = VIS_ROOT.parent
TEN_ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes/bridge")
PY = Path("/datapool/home/ph_teacher3/.conda/envs/visedit/bin/python")
MODEL_PATH = VIS_ROOT / "models" / "llava-v1.5-7b-hf"
ENTITY_SCRIPT = VIS_ROOT / "eval_llava_bridge_entity_recognition_ckpt.py"
OPENEND_SCRIPT = VIS_ROOT / "edit_30_bridge_val_eval_only_vis.py"
OFFICIAL_SCRIPT = VIS_ROOT / "bridge_Bport_eval.py"
VAL_DIR = TEN_ROOT / "bridge_val"
VAL_EDIT_DATA = VAL_DIR / "edit_30_bridge_val_eval_only_vis.json"
OUT_DIR = VAL_DIR / "onlyvis" / "open_end"
SUMMARY_PATH = VIS_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_frontlayers_summary.json"
TABLE_MD = VIS_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_frontlayers_table.md"
TABLE_CSV = VIS_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_frontlayers_table.csv"
TABLE_TEX = VIS_ROOT / "records" / "job_logs" / "bridge_onlyvis_stage03_frontlayers_table.tex"
TARGET_LOSS = 0.30
TRAIN_EPOCHS = 220

CKPT_RE = re.compile(r"epoch-(\d+)-i-(\d+)-ema_loss-([0-9.]+)")

STAGES = [
    {
        "layer": "l0",
        "prefix": "bridge_noport_only_vis_l0",
        "train_script_name": "bridge_train_only_vis_l0safe.py",
        "config": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l0.yaml",
        "cache_root": VIS_ROOT / "data_bridge_noport_onlyvis_l0",
    },
    {
        "layer": "l2",
        "prefix": "bridge_noport_only_vis_l2",
        "train_script_name": "bridge_train_only_vis.py",
        "config": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l2.yaml",
        "cache_root": VIS_ROOT / "data_bridge_noport_onlyvis_l2",
    },
    {
        "layer": "l3",
        "prefix": "bridge_noport_only_vis_l3",
        "train_script_name": "bridge_train_only_vis.py",
        "config": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l3.yaml",
        "cache_root": VIS_ROOT / "data_bridge_noport_onlyvis_l3",
    },
    {
        "layer": "l4",
        "prefix": "bridge_noport_only_vis_l4",
        "train_script_name": "bridge_train_only_vis.py",
        "config": VIS_ROOT / "configs" / "vead" / "llava-v1.5-7b-bridge-only-vis-l4.yaml",
        "cache_root": VIS_ROOT / "data_bridge_noport_onlyvis_l4",
    },
]


def run_cmd(args, cwd: Path):
    print("RUN:", " ".join(str(a) for a in args), flush=True)
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_DATASETS_OFFLINE"] = "1"
    subprocess.run([str(a) for a in args], check=True, cwd=str(cwd), env=env)


def ensure_layout():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    vead_link = RUN_ROOT / "VEAD"
    models_link = RUN_ROOT / "models"
    if not vead_link.exists():
        vead_link.symlink_to(VIS_ROOT, target_is_directory=True)
    if not models_link.exists():
        models_link.symlink_to(VIS_ROOT / "models", target_is_directory=True)


def parse_ckpt(path: Path):
    match = CKPT_RE.fullmatch(path.name)
    if not match:
        return None
    epoch, step, ema_loss = match.groups()
    return {
        "ckpt_path": str(path),
        "checkpoint": path.name,
        "epoch": int(epoch),
        "step": int(step),
        "ema_loss": float(ema_loss),
    }


def list_ckpts(prefix: str):
    root = VIS_ROOT / "records" / "vead" / "llava-v1.5-7b"
    rows = []
    for record_dir in sorted(root.glob(f"{prefix}-*")):
        ckpt_dir = record_dir / "checkpoints"
        if not ckpt_dir.exists():
            continue
        for ckpt_path in ckpt_dir.glob("epoch-*-i-*-ema_loss-*"):
            meta = parse_ckpt(ckpt_path)
            if meta is None:
                continue
            meta["record_dir"] = str(record_dir)
            rows.append(meta)
    return rows


def has_final_epoch_ckpt(prefix: str):
    return any(row["epoch"] >= TRAIN_EPOCHS for row in list_ckpts(prefix))


def select_closest_ckpt(prefix: str):
    rows = [row for row in list_ckpts(prefix) if row["epoch"] <= TRAIN_EPOCHS]
    if not rows:
        raise FileNotFoundError(f"No checkpoints found for prefix={prefix}")
    for row in rows:
        row["loss_gap"] = abs(row["ema_loss"] - TARGET_LOSS)
    rows.sort(key=lambda row: (row["loss_gap"], -row["epoch"], -row["step"]))
    return rows[0]


def summarize_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    total = len(rows)
    strict = sum(int(row.get("strict_acc", 0)) for row in rows)
    loose = sum(int(row.get("loose_acc", 0)) for row in rows)
    return {
        "path": str(path),
        "total": total,
        "strict_correct": strict,
        "strict_acc": (strict / total) if total else 0.0,
        "loose_correct": loose,
        "loose_acc": (loose / total) if total else 0.0,
    }


def official_result_dir(postfix: str):
    return VIS_ROOT / "eval_results" / "vead" / "llava-v1.5-7b" / f"EditBridge-val-{postfix}" / "single_edit"


def official_mean_result_path(postfix: str):
    return official_result_dir(postfix) / "mean_results.json"


def official_metrics(mean_res: dict):
    return {
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


def pct(value):
    if value is None:
        return "-"
    return f"{float(value) * 100.0:.2f}"


def fmt_ratio(block: dict, key: str):
    correct_key = "strict_correct" if key == "strict_acc" else "loose_correct"
    return f"{block[correct_key]}/{block['total']} ({pct(block[key])}\\%)"


def train_stage(stage: dict):
    if has_final_epoch_ckpt(stage["prefix"]):
        print(f"SKIP training {stage['layer']}: found epoch >= {TRAIN_EPOCHS}", flush=True)
        return
    train_script = VIS_ROOT / stage["train_script_name"]
    run_cmd(
        [
            PY,
            train_script,
            "-dvc",
            "cuda:0",
            "--single_gpu",
            "-eps",
            str(TRAIN_EPOCHS),
            "-tnp",
            stage["prefix"],
            "--config",
            stage["config"],
            "--cache_root",
            stage["cache_root"],
            "--reset_cache",
        ],
        cwd=VIS_ROOT,
    )


def run_custom_eval(stage: dict, ckpt_meta: dict):
    tag = stage["layer"]
    entity_out = OUT_DIR / f"bridge_val_entity_recog_ckpt_stage03front_{tag}.jsonl"
    openend_out = OUT_DIR / f"bridge_val_openend_onlyvis_ckpt_stage03front_{tag}.jsonl"

    if entity_out.exists():
        entity_out.unlink()
    if openend_out.exists():
        openend_out.unlink()

    run_cmd(
        [
            PY,
            ENTITY_SCRIPT,
            "--split_dir",
            VAL_DIR,
            "--model",
            MODEL_PATH,
            "--out",
            entity_out,
            "--ckpt",
            ckpt_meta["ckpt_path"],
            "--device",
            "cuda:0",
            "--config",
            stage["config"],
            "--edit_data_path",
            VAL_EDIT_DATA,
            "--visedit_root",
            VIS_ROOT,
        ],
        cwd=RUN_ROOT,
    )

    run_cmd(
        [
            PY,
            OPENEND_SCRIPT,
            "--split_dir",
            VAL_DIR,
            "--model",
            MODEL_PATH,
            "--out",
            openend_out,
            "--ckpt",
            ckpt_meta["ckpt_path"],
            "--device",
            "cuda:0",
            "--config",
            stage["config"],
            "--edit_data_path",
            VAL_EDIT_DATA,
            "--visedit_root",
            VIS_ROOT,
        ],
        cwd=RUN_ROOT,
    )

    return {
        "entity_recognition": summarize_jsonl(entity_out),
        "open_end_qa": summarize_jsonl(openend_out),
    }


def run_official_eval(stage: dict, ckpt_meta: dict):
    postfix = f"stage03front-official-{stage['layer']}"
    out_dir = official_result_dir(postfix)
    if out_dir.parent.exists():
        shutil.rmtree(out_dir.parent)
    run_cmd(
        [
            PY,
            OFFICIAL_SCRIPT,
            "-dvc",
            "cuda:0",
            "-ckpt",
            ckpt_meta["ckpt_path"],
            "--split",
            "val",
            "-enp",
            postfix,
            "--config",
            stage["config"],
        ],
        cwd=VIS_ROOT,
    )
    mean_path = official_mean_result_path(postfix)
    mean_res = json.loads(mean_path.read_text(encoding="utf-8"))
    metrics = official_metrics(mean_res)
    metrics["result_dir"] = str(out_dir)
    metrics["mean_results_path"] = str(mean_path)
    return metrics


def render_tables(rows):
    fieldnames = [
        "layer",
        "ema_loss",
        "entity_strict",
        "entity_loose",
        "open_strict",
        "open_loose",
        "reliability",
        "gen_text",
        "gen_image",
        "loc_text",
        "loc_image",
        "port_overall",
        "port_1hop",
        "port_2hop",
        "checkpoint",
    ]
    csv_rows = []
    md_lines = [
        "# Bridge only-vis front-layer stage-0.30 comparison",
        "",
        "| Layer | EMA loss | Entity strict | Entity loose | Open-end strict | Open-end loose | Reliability | Gen-text | Gen-image | Loc-text | Loc-image | Port overall | 1-hop | 2-hop | Checkpoint |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    tex_lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\small",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\caption{Loss-matched stage-$0.30$ comparison for front-layer only-vision adapter insertion on the bridge validation set.}",
        "\\label{tab:bridge_onlyvis_stage03_frontlayers}",
        "\\begin{tabular}{lcccccccccccccc}",
        "\\toprule",
        "Layer & EMA Loss & Entity Strict (\\%) & Entity Loose (\\%) & Open-end Strict (\\%) & Open-end Loose (\\%) & Reliability & Gen-text & Gen-image & Loc-text & Loc-image & Port overall & 1-hop & 2-hop & Checkpoint \\\\",
        "\\midrule",
    ]

    for row in rows:
        entity = row["entity_recognition"]
        open_end = row["open_end_qa"]
        official = row["official"]
        csv_row = {
            "layer": row["layer"],
            "ema_loss": f"{row['selected_ckpt']['ema_loss']:.4f}",
            "entity_strict": pct(entity["strict_acc"]),
            "entity_loose": pct(entity["loose_acc"]),
            "open_strict": pct(open_end["strict_acc"]),
            "open_loose": pct(open_end["loose_acc"]),
            "reliability": f"{official['reliability_acc']:.4f}",
            "gen_text": f"{official['generality_text_rephrase_acc']:.4f}",
            "gen_image": f"{official['generality_image_rephrase_acc']:.4f}",
            "loc_text": f"{official['locality_text_loc_acc']:.4f}",
            "loc_image": f"{official['locality_image_loc_acc']:.4f}",
            "port_overall": f"{official['portability_overall_acc']:.4f}",
            "port_1hop": f"{official['portability_1hop_acc']:.4f}",
            "port_2hop": f"{official['portability_2hop_acc']:.4f}",
            "checkpoint": row["selected_ckpt"]["checkpoint"],
        }
        csv_rows.append(csv_row)
        md_lines.append(
            f"| {row['layer']} | {csv_row['ema_loss']} | {fmt_ratio(entity, 'strict_acc')} | "
            f"{fmt_ratio(entity, 'loose_acc')} | {fmt_ratio(open_end, 'strict_acc')} | "
            f"{fmt_ratio(open_end, 'loose_acc')} | {csv_row['reliability']} | {csv_row['gen_text']} | "
            f"{csv_row['gen_image']} | {csv_row['loc_text']} | {csv_row['loc_image']} | "
            f"{csv_row['port_overall']} | {csv_row['port_1hop']} | {csv_row['port_2hop']} | "
            f"`{csv_row['checkpoint']}` |"
        )
        tex_lines.append(
            f"{row['layer'][1:]} & {csv_row['ema_loss']} & {csv_row['entity_strict']} & {csv_row['entity_loose']} & "
            f"{csv_row['open_strict']} & {csv_row['open_loose']} & {csv_row['reliability']} & {csv_row['gen_text']} & "
            f"{csv_row['gen_image']} & {csv_row['loc_text']} & {csv_row['loc_image']} & {csv_row['port_overall']} & "
            f"{csv_row['port_1hop']} & {csv_row['port_2hop']} & \\texttt{{{csv_row['checkpoint']}}} \\\\"
        )

    tex_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}"])

    with TABLE_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    TABLE_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    TABLE_TEX.write_text("\n".join(tex_lines) + "\n", encoding="utf-8")


def main():
    ensure_layout()
    all_rows = []
    for stage in STAGES:
        print(f"=== stage03 front-layer pipeline: {stage['layer']} ===", flush=True)
        train_stage(stage)
        ckpt_meta = select_closest_ckpt(stage["prefix"])
        custom = run_custom_eval(stage, ckpt_meta)
        official = run_official_eval(stage, ckpt_meta)
        all_rows.append(
            {
                "layer": stage["layer"],
                "prefix": stage["prefix"],
                "train_script_name": stage["train_script_name"],
                "config": str(stage["config"]),
                "cache_root": str(stage["cache_root"]),
                "record_dir": ckpt_meta["record_dir"],
                "selected_ckpt": ckpt_meta,
                "entity_recognition": custom["entity_recognition"],
                "open_end_qa": custom["open_end_qa"],
                "official": official,
            }
        )

    payload = {
        "stage_loss_target": TARGET_LOSS,
        "train_epoch_cap": TRAIN_EPOCHS,
        "rows": all_rows,
    }
    SUMMARY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    render_tables(all_rows)
    print(SUMMARY_PATH, flush=True)
    print(TABLE_MD, flush=True)
    print(TABLE_CSV, flush=True)
    print(TABLE_TEX, flush=True)


if __name__ == "__main__":
    main()
