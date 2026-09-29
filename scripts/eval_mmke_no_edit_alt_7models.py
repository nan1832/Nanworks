import argparse
import csv
import json
import os
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

import torch
from PIL import Image
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from utils import get_full_model_name, load_vllm_for_edit


MODEL_ORDER = [
    "blip2-opt-2.7b",
    "instructblip-vicuna-7b",
    "minigpt-4-vicuna-7b",
    "llava-v1.5-7b",
    "qwen2.5-vl-3b-instruct",
    "paligemma-3b",
    "smolvlm-1.7b",
]
TASK_ORDER = ["visual", "entity"]
METRIC_COLUMNS = ["Rel", "T-Gen", "M-Gen", "T-Loc", "M-Loc", "Average"]


def now():
    return time.strftime("%F %T")


def log(msg):
    print(f"[{now()}] {msg}", flush=True)


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def set_decimal(value, decimal=4):
    if isinstance(value, list):
        return [set_decimal(item, decimal) for item in value]
    if isinstance(value, dict) or isinstance(value, defaultdict):
        return {key: set_decimal(item, decimal) for key, item in value.items()}
    if isinstance(value, float):
        return round(value, decimal)
    return value


def fmt(value):
    if value is None or value == "":
        return "-"
    return f"{float(value):.2f}"


def pct(value):
    return None if value is None else value * 100.0


def set_eval_mode(vllm):
    if hasattr(vllm, "eval"):
        try:
            vllm.eval()
        except Exception:
            pass
    for attr in ["llm", "model", "vllm", "language_model"]:
        module = getattr(vllm, attr, None)
        if hasattr(module, "eval"):
            try:
                module.eval()
            except Exception:
                pass


def load_image(path):
    if path is None:
        return None
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def resolve_image(data_root, rel_path, allow_missing=False):
    if not rel_path:
        return None
    rel_path = str(rel_path)
    path = data_root / "data_image" / rel_path
    if path.exists():
        return path
    path = data_root / rel_path
    if path.exists():
        return path
    if rel_path.startswith("locality/"):
        path = data_root / "data_image" / "entity" / Path(rel_path).name
        if path.exists():
            return path
    if allow_missing:
        log(f"[warn] image not found, skip image-dependent score: {rel_path}")
        return None
    raise FileNotFoundError(f"Image not found for {rel_path}")


def decode_token_ids(tokenizer, ids):
    try:
        return tokenizer.decode(ids)
    except TypeError:
        return tokenizer.decode(ids.detach().cpu().tolist())


def accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks):
    assert len(label_ids) == 1 and len(label_masks) == 1
    logits = vllm.get_llm_outpt(input_embeds, vt_range).logits
    pred_ids = logits.argmax(-1)
    pred_ids = pred_ids[:, -label_ids.shape[1] :]
    mask = label_masks.to(bool)
    denom = mask.sum()
    if int(denom.item()) == 0:
        return None, pred_ids
    acc = ((pred_ids == label_ids) * mask).sum() / denom
    return float(acc), pred_ids


def make_prompt(question):
    question = (question or "").strip()
    if question.endswith(":"):
        return question
    return f"{question} The answer is:"


def score_text_target(vllm, tokenizer, prompt, image_path, target):
    image = load_image(image_path) if image_path is not None else None
    (input_embeds, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [make_prompt(prompt)], [image], [target or ""]
    )
    acc, pred_ids = accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks)
    pred = decode_token_ids(tokenizer, pred_ids[label_masks.to(bool)])
    return acc, pred


def consistency_score(vllm, tokenizer, prompt, image_path, reference_target):
    image = load_image(image_path) if image_path is not None else None
    (input_embeds, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [make_prompt(prompt)], [image], [reference_target or ""]
    )
    _, before_ids = accuracy_and_prediction(vllm, input_embeds, vt_range, label_ids, label_masks)
    pred_before = decode_token_ids(tokenizer, before_ids[label_masks.to(bool)])

    image2 = load_image(image_path) if image_path is not None else None
    (input_embeds2, vt_range2), _, label_masks2 = vllm.prompts_imgs_target_to_xym(
        [make_prompt(prompt)], [image2], [reference_target or ""]
    )
    acc, after_ids = accuracy_and_prediction(vllm, input_embeds2, vt_range2, before_ids, label_masks2)
    pred_after = decode_token_ids(tokenizer, after_ids[label_masks2.to(bool)])
    return acc, pred_before, pred_after


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def metrics_from_results(model_name, task, split, target_mode, results):
    rel = pct(mean([row["reliability"]["acc"] for row in results]))
    t_gen = pct(mean([row["generality"]["text_rephrase"]["acc"] for row in results]))
    m_gen = pct(mean([row["generality"]["image_rephrase"]["acc"] for row in results]))
    t_loc = pct(mean([row["locality"]["text_loc"]["acc"] for row in results]))
    m_loc = pct(mean([row["locality"]["image_loc"]["acc"] for row in results]))
    avg_items = [x for x in [rel, t_gen, m_gen, t_loc, m_loc] if x is not None]
    return {
        "task": task,
        "split": split,
        "target_mode": target_mode,
        "model": model_name,
        "eval_samples": len(results),
        "Rel": rel,
        "T-Gen": t_gen,
        "M-Gen": m_gen,
        "T-Loc": t_loc,
        "M-Loc": m_loc,
        "Average": sum(avg_items) / len(avg_items) if avg_items else None,
        "status": "DONE",
        "finished_at": now(),
    }


def sample_id(task, split, index, row):
    image = str(row.get("image", ""))
    return f"{task}-{split}-{index}-{Path(image).stem}"


def evaluate_no_edit(args):
    model_name = get_full_model_name(args.model_name)
    data_path = args.data_root / "data_json" / f"{args.task}_{args.split}.json"
    model_dir = args.out_root / args.task / args.target_mode / model_name
    done_path = model_dir / "no_edit_metrics.json"
    if done_path.exists() and not args.overwrite:
        log(f"[skip] {args.task}/{args.target_mode}/{model_name} already done: {done_path}")
        return json.loads(done_path.read_text(encoding="utf-8"))

    model_dir.mkdir(parents=True, exist_ok=True)
    run_config = {k: str(v) for k, v in vars(args).items()}
    run_config["model_name_normalized"] = model_name
    save_json(model_dir / "run_config.json", run_config)

    if str(args.device).startswith("cuda"):
        log(
            "[cuda] visible_devices=%s available=%s count=%s"
            % (os.environ.get("CUDA_VISIBLE_DEVICES"), torch.cuda.is_available(), torch.cuda.device_count())
        )
        if torch.cuda.is_available():
            torch.cuda.init()
            log("[cuda] initialized before data loading")

    log(f"[data] loading MMKE {args.task}/{args.split}: {data_path}")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if args.eval_sample_n is not None:
        data = data[: args.eval_sample_n]
    log(f"[data] samples={len(data)} target={args.target_mode}")

    log(f"[model] loading {model_name} on {args.device}")
    vllm = load_vllm_for_edit(model_name, args.device)
    set_eval_mode(vllm)
    tokenizer = vllm.get_llm_tokenizer()

    results = []
    with torch.inference_mode():
        for idx, row in enumerate(tqdm(data, desc=f"no-edit {args.task}/{model_name}")):
            target = row.get(args.target_mode, "")
            main_image = resolve_image(args.data_root, row.get("image"))
            rephrase_image = resolve_image(args.data_root, row.get("image_rephrase") or row.get("image"))
            m_loc_image = resolve_image(args.data_root, row.get("m_loc"), allow_missing=True) if row.get("m_loc") else None

            rel_acc, rel_pred = score_text_target(vllm, tokenizer, row.get("src"), main_image, target)
            tgen_acc, tgen_pred = score_text_target(vllm, tokenizer, row.get("rephrase") or row.get("src"), main_image, target)
            mgen_acc, mgen_pred = score_text_target(vllm, tokenizer, row.get("src"), rephrase_image, target)

            tloc_acc, tloc_before, tloc_after = consistency_score(
                vllm, tokenizer, row.get("loc"), None, row.get("loc_ans", "")
            )
            if row.get("m_loc") and m_loc_image is None:
                mloc_acc, mloc_before, mloc_after = None, "", ""
            else:
                mloc_acc, mloc_before, mloc_after = consistency_score(
                    vllm, tokenizer, row.get("m_loc_q"), m_loc_image, row.get("m_loc_a", "")
                )

            results.append(
                {
                    "sample_id": sample_id(args.task, args.split, idx, row),
                    "knowledge_type": row.get("knowledge_type"),
                    "type_self": row.get("type_self"),
                    "reliability": {
                        "prompt": row.get("src"),
                        "image": row.get("image"),
                        "target": target,
                        "predict_no_edit": rel_pred,
                        "acc": rel_acc,
                    },
                    "generality": {
                        "text_rephrase": {
                            "prompt": row.get("rephrase") or row.get("src"),
                            "image": row.get("image"),
                            "target": target,
                            "predict_no_edit": tgen_pred,
                            "acc": tgen_acc,
                        },
                        "image_rephrase": {
                            "prompt": row.get("src"),
                            "image": row.get("image_rephrase") or row.get("image"),
                            "target": target,
                            "predict_no_edit": mgen_pred,
                            "acc": mgen_acc,
                        },
                    },
                    "locality": {
                        "text_loc": {
                            "prompt": row.get("loc"),
                            "target": row.get("loc_ans"),
                            "predict_before_no_edit": tloc_before,
                            "predict_after_no_edit": tloc_after,
                            "acc": tloc_acc,
                        },
                        "image_loc": {
                            "prompt": row.get("m_loc_q"),
                            "image": row.get("m_loc"),
                            "target": row.get("m_loc_a"),
                            "predict_before_no_edit": mloc_before,
                            "predict_after_no_edit": mloc_after,
                            "acc": mloc_acc,
                        },
                    },
                }
            )

    metrics = metrics_from_results(model_name, args.task, args.split, args.target_mode, results)
    metrics["result_dir"] = str(model_dir)
    save_json(model_dir / "no_edit_results.json", set_decimal(results))
    save_json(model_dir / "no_edit_metrics.json", set_decimal(metrics))
    log(f"[done] {args.task}/{args.target_mode}/{model_name} avg={metrics['Average']:.2f} rel={metrics['Rel']:.2f}")
    return metrics


def row_for_summary(out_root, task, target_mode, model):
    path = out_root / task / target_mode / model / "no_edit_metrics.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"task": task, "target_mode": target_mode, "model": model, "status": "PENDING"}


def summarize_root(out_root, target_mode):
    rows = []
    for task in TASK_ORDER:
        for model in MODEL_ORDER:
            rows.append(row_for_summary(out_root, task, target_mode, model))

    fields = ["task", "split", "target_mode", "model", "eval_samples", *METRIC_COLUMNS, "status", "finished_at", "result_dir"]
    csv_path = out_root / f"no_edit_mmke_{target_mode}_7models_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})

    md_lines = [
        f"# No-Edit MMKE {target_mode} Baseline Metrics",
        "",
        "| Task | Split | Model | Samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        md_lines.append(
            "| {task} | {split} | {model} | {n} | {rel} | {tgen} | {mgen} | {tloc} | {mloc} | {avg} | {status} |".format(
                task=row.get("task", ""),
                split=row.get("split", "-"),
                model=row.get("model", ""),
                n=row.get("eval_samples", "-"),
                rel=fmt(row.get("Rel")),
                tgen=fmt(row.get("T-Gen")),
                mgen=fmt(row.get("M-Gen")),
                tloc=fmt(row.get("T-Loc")),
                mloc=fmt(row.get("M-Loc")),
                avg=fmt(row.get("Average")),
                status=row.get("status", "-"),
            )
        )
    md_path = out_root / f"no_edit_mmke_{target_mode}_7models_metrics.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    log(f"[summary] wrote {csv_path} and {md_path}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--task", choices=TASK_ORDER, default="visual")
    parser.add_argument("--split", choices=["train", "eval"], default="train")
    parser.add_argument("--target-mode", choices=["alt", "pred"], default="alt")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench"),
    )
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--eval-sample-n", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    if args.summarize_only:
        summarize_root(args.out_root, args.target_mode)
        return
    if not args.model_name:
        raise ValueError("--model-name is required unless --summarize-only is set")
    evaluate_no_edit(args)
    summarize_root(args.out_root, args.target_mode)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
