import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def resolve_existing_path(raw_path):
    path = Path(raw_path)
    if path.exists():
        return path
    anchors = [Path.cwd(), Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
    seen = set()
    for anchor in anchors:
        key = str(anchor)
        if key in seen:
            continue
        seen.add(key)
        candidate = (anchor / path).resolve()
        if candidate.exists():
            return candidate
    return path


def extract_assistant_answer(raw_text):
    text = str(raw_text).strip()
    if "ASSISTANT:" in text:
        return text.rsplit("ASSISTANT:", 1)[-1].strip()
    return text


def normalize_answer(text):
    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def strict_match(prediction, gold):
    return int(normalize_answer(prediction) == normalize_answer(gold))


def loose_match(prediction, gold):
    pred = normalize_answer(prediction)
    target = normalize_answer(gold)
    if not pred or not target:
        return 0
    return int(pred in target or target in pred)


def summarize_rows(rows):
    buckets = defaultdict(list)
    for row in rows:
        buckets[row["split"]].append(row)
    summary = {}
    for split, split_rows in buckets.items():
        count = len(split_rows)
        strict_total = sum(row["strict_acc"] for row in split_rows)
        loose_total = sum(row["loose_acc"] for row in split_rows)
        summary[split] = {
            "count": count,
            "strict_correct": strict_total,
            "strict_acc": strict_total / count if count else 0.0,
            "loose_correct": loose_total,
            "loose_acc": loose_total / count if count else 0.0,
        }
    return dict(summary)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Evaluate a bridge text-adapter checkpoint.")
    parser.add_argument("--device", required=True)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--data_path", required=True)
    parser.add_argument("--bridge_img_root", required=True)
    parser.add_argument("--coco_img_root", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--data_n", type=int, default=None)
    parser.add_argument("--max_new_tokens", type=int, default=32)
    return parser


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_edit_bridge_class():
    from dataset.edit_bridge_loader import EditBridge

    return EditBridge


def _iter_eval_items(case):
    request = case["request"]
    yield {
        "split": "request",
        "prompt": request["prompt"],
        "image": request.get("image"),
        "gold": request["target_new"],
    }
    for family in ("text_rephrase", "image_rephrase"):
        for item in case.get("generality", {}).get(family, []):
            yield {
                "split": f"generality.{family}",
                "prompt": item["prompt"],
                "image": item.get("image"),
                "gold": item["target"],
            }
    for family in ("text_loc", "image_loc"):
        for item in case.get("locality", {}).get(family, []):
            yield {
                "split": f"locality.{family}",
                "prompt": item["prompt"],
                "image": item.get("image"),
                "gold": item["target"],
            }


def _build_generation_prompt(prompt, has_image):
    if has_image:
        return f"USER: <image>\n{prompt}\nASSISTANT:"
    return f"USER: {prompt}\nASSISTANT:"


def _prepare_adaptors_for_generation(editor, prompt, image):
    import torch

    generation_prompt = _build_generation_prompt(prompt, image is not None)
    processor = editor.vllm.processor
    if image is not None:
        raw_inputs = processor(generation_prompt, image, return_tensors="pt")
        input_ids = raw_inputs["input_ids"]
        img_begin = int(
            torch.where(input_ids[0] == editor.vllm.get_img_special_token_id())[0][0].item()
        )
        img_token_n = editor.vllm.get_img_token_n()
        prompt_end = int(input_ids.shape[1] - 1 + img_token_n)
        vt_range = (img_begin, img_begin + img_token_n)
    else:
        raw_inputs = processor(text=generation_prompt, return_tensors="pt")
        prompt_end = int(raw_inputs["input_ids"].shape[1])
        vt_range = None

    prompt_end_tensor = torch.tensor([prompt_end], device=editor.device)
    has_image = vt_range is not None
    vt_begin, vt_end = vt_range if vt_range is not None else (None, None)
    for adaptor in editor.adaptors.values():
        adaptor.set_input_info(has_image, vt_begin, vt_end)
        adaptor.set_prompt_end(prompt_end_tensor)
        if hasattr(adaptor, "set_text_token_indices"):
            adaptor.set_text_token_indices(None)
    return generation_prompt, raw_inputs


def _generate_prediction(editor, prompt, image, max_new_tokens):
    import torch

    model = editor.vllm.model
    device = editor.device
    generation_prompt, inputs = _prepare_adaptors_for_generation(editor, prompt, image)
    inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}
    with torch.no_grad():
        generated = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    raw = editor.vllm.processor.batch_decode(generated, skip_special_tokens=True)[0]
    return extract_assistant_answer(raw), raw


def run_evaluation(args):
    from utils import load_vllm_editor

    EditBridge = _load_edit_bridge_class()
    config_path = resolve_existing_path(args.config)
    data_path = resolve_existing_path(args.data_path)
    bridge_img_root = resolve_existing_path(args.bridge_img_root)
    coco_img_root = resolve_existing_path(args.coco_img_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    editor = load_vllm_editor(
        "vead",
        "llava-v1.5-7b",
        args.device,
        [],
        args.ckpt,
        False,
        config_path=str(config_path),
    )
    eval_data = EditBridge(
        data_path=str(data_path),
        img_root_dir=str(bridge_img_root),
        coco_img_dir=str(coco_img_root),
        data_n=args.data_n,
    )

    rows = []
    for case_index, case in enumerate(eval_data.data):
        editor.restore_to_original_model()
        editor.edit_one_piece(case["request"])
        for item_index, item in enumerate(_iter_eval_items(case)):
            prediction, raw = _generate_prediction(editor, item["prompt"], item["image"], args.max_new_tokens)
            rows.append(
                {
                    "case_index": case_index,
                    "item_index": item_index,
                    "split": item["split"],
                    "prompt": item["prompt"],
                    "gold": item["gold"],
                    "prediction": prediction,
                    "strict_acc": strict_match(prediction, item["gold"]),
                    "loose_acc": loose_match(prediction, item["gold"]),
                    "raw": raw,
                }
            )

    summary = summarize_rows(rows)
    _write_jsonl(out_dir / "rows.jsonl", rows)
    _write_json(out_dir / "summary.json", summary)
    return summary


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    run_evaluation(args)


if __name__ == "__main__":
    main()
