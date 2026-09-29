import argparse
import hashlib
import json
import os
import re
import sys
from typing import Dict, List, Tuple

import torch
from PIL import Image
from tqdm import tqdm


QUESTION_TEMPLATES = [
    "What is the name of this bridge?",
    "Identify the bridge shown in this image.",
    "Which bridge is shown in the picture?",
    "Please tell me the name of the bridge in this image.",
    "What is this bridge called?",
]


def normalize_text(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip()


def strict_match(pred: str, gold: str) -> int:
    return int(normalize_text(pred) == normalize_text(gold))


def loose_match(pred: str, gold: str) -> int:
    p = normalize_text(pred)
    g = normalize_text(gold)
    if not p or not g:
        return 0
    return int((p in g) or (g in p))


def choose_question(image_id: str) -> str:
    h = hashlib.md5(str(image_id).encode("utf-8")).hexdigest()
    idx = int(h, 16) % len(QUESTION_TEMPLATES)
    return QUESTION_TEMPLATES[idx]


def find_jsonl(split_dir: str) -> str:
    for name in os.listdir(split_dir):
        if name.endswith("_val.jsonl") or name.endswith("_train.jsonl"):
            return os.path.join(split_dir, name)
    raise FileNotFoundError("no *_val.jsonl or *_train.jsonl found")


def find_img_dir(split_dir: str) -> str:
    for d in ["images", "bridge_images"]:
        p = os.path.join(split_dir, d)
        if os.path.isdir(p):
            return p
    raise FileNotFoundError("images dir not found")


def infer_split_name(split_dir: str) -> str:
    name = os.path.basename(os.path.normpath(split_dir)).lower()
    return "val" if "val" in name else "train"


def ensure_visedit_imports(visedit_root: str):
    if visedit_root not in sys.path:
        sys.path.insert(0, visedit_root)
    from utils.GLOBAL import ROOT_PATH
    from utils import load_vllm_for_edit
    from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig

    return ROOT_PATH, load_vllm_for_edit, VEADWithPortability, VEADPortConfig


def build_editor(ckpt_path: str, device: str, config_path: str, visedit_root: str):
    root_path, load_vllm_for_edit, vead_cls, vead_cfg_cls = ensure_visedit_imports(visedit_root)
    config = vead_cfg_cls.from_yaml(config_path)
    vllm = load_vllm_for_edit(config.edit_model_name, device)
    editor = vead_cls(
        vllm,
        config,
        device,
        vllm_data_proc=None,
        data_proc_device=None,
        train_data_cache_root=os.path.join(root_path, "data"),
    )
    editor.load_ckpt(ckpt_path, restrict=True, load_opt=False)
    return editor


def generate_answer(editor, image: Image.Image, prompt: str, max_new_tokens: int) -> str:
    processor = editor.vllm.processor
    model = editor.vllm.model
    inputs = processor(images=image, text=prompt, return_tensors="pt")
    inputs = {k: v.to(editor.device) if hasattr(v, "to") else v for k, v in inputs.items()}
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    prompt_norm = normalize_text(prompt)
    text_norm = normalize_text(text)
    if text_norm.startswith(prompt_norm):
        text = text[len(prompt) :].strip()
    return text.strip()


def load_entity_by_question(ann_path: str) -> Dict[str, Tuple[str, str]]:
    q2ent = {}
    with open(ann_path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            q2ent[d["question_id"]] = (d.get("entity_id"), d.get("entity_name"))
    return q2ent


def load_unique_images_with_entity(q_path: str, q2ent: Dict[str, Tuple[str, str]]) -> List[Dict]:
    seen = set()
    items = []
    with open(q_path, "r", encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            image_id = o.get("image_id")
            image_name = o.get("image_name") or (f"{image_id}.jpg" if image_id else None)
            if not image_id or not image_name or image_id in seen:
                continue
            seen.add(image_id)
            entity_id, entity_name = q2ent.get(o.get("question_id"), (None, None))
            items.append(
                {
                    "image_id": image_id,
                    "image_name": image_name,
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                }
            )
    return items


def get_gold_from_item(item: Dict) -> str:
    if item.get("target"):
        return item["target"]
    answers = item.get("answers") or item.get("options") or []
    correct = item.get("correct") or []
    idx = next((i for i, v in enumerate(correct) if v == 1), None)
    if idx is None or idx >= len(answers):
        return ""
    return answers[idx]


def load_request_map(edit_data_path: str) -> Dict[str, Dict]:
    split_dir = os.path.dirname(edit_data_path)
    bridge_root = os.path.dirname(split_dir)
    with open(edit_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    request_map = {}
    for item in data:
        req = item.get("request", {})
        rel_img = req.get("image")
        if not rel_img:
            continue
        image_id = os.path.splitext(os.path.basename(rel_img))[0]
        if rel_img.startswith("val/images"):
            resolved_img = os.path.join(bridge_root, "bridge_val", "bridge_images", os.path.basename(rel_img))
        elif rel_img.startswith("train/images"):
            resolved_img = os.path.join(bridge_root, "bridge_train", "bridge_images", os.path.basename(rel_img))
        else:
            resolved_img = os.path.join(bridge_root, rel_img)
        question_map = {}
        for q in req.get("open_questions") or []:
            qid = q.get("question_id")
            if qid is not None:
                question_map[qid] = q
        request_map[image_id] = {
            "request": {
                "image": Image.open(resolved_img).convert("RGB"),
                "prompt": f"{req['prompt']} The answer is:",
                "target_new": req["target_new"],
            },
            "question_map": question_map,
            "entity_id": item.get("entity_id"),
        }
    return request_map


def load_entity_request_map(edit_data_path: str) -> Dict[str, Dict]:
    split_dir = os.path.dirname(edit_data_path)
    bridge_root = os.path.dirname(split_dir)
    with open(edit_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entity_req = {}
    for item in data:
        req = item.get("request", {})
        entity_id = item.get("entity_id")
        if entity_id:
            rel_img = req.get("image")
            if not rel_img:
                continue
            if rel_img.startswith("val/images"):
                resolved_img = os.path.join(bridge_root, "bridge_val", "bridge_images", os.path.basename(rel_img))
            elif rel_img.startswith("train/images"):
                resolved_img = os.path.join(bridge_root, "bridge_train", "bridge_images", os.path.basename(rel_img))
            else:
                resolved_img = os.path.join(bridge_root, rel_img)
            entity_req[entity_id] = {
                "image": Image.open(resolved_img).convert("RGB"),
                "prompt": f"{req['prompt']} The answer is:",
                "target_new": req["target_new"],
            }
    return entity_req


def save_jsonl(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def eval_entity_recognition(editor, split_dir: str, edit_data_path: str, out_path: str, max_new_tokens: int = 24):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    split_name = infer_split_name(split_dir)
    ann_path = os.path.join(split_dir, f"30_bridge_{split_name}_ann.jsonl")
    q2ent = load_entity_by_question(ann_path)
    images = load_unique_images_with_entity(q_path, q2ent)
    entity_req_map = load_entity_request_map(edit_data_path)

    strict_correct, loose_correct = 0, 0
    rows = []
    progress = tqdm(images, total=len(images), desc="BLIP2 Entity", dynamic_ncols=True)
    for item in progress:
        req = entity_req_map.get(item.get("entity_id"))
        if req is None:
            raise KeyError(f"No edit request found for entity_id={item.get('entity_id')} in {edit_data_path}")
        editor.restore_to_original_model()
        editor.edit_one_piece(req)

        image = Image.open(os.path.join(img_dir, item["image_name"])).convert("RGB")
        question = choose_question(item["image_id"]) + " Answer briefly with the bridge name only."
        pred = generate_answer(editor, image, question, max_new_tokens=max_new_tokens)
        gold = item.get("entity_name") or ""
        s_acc = strict_match(pred, gold)
        l_acc = loose_match(pred, gold)
        strict_correct += s_acc
        loose_correct += l_acc
        rows.append(
            {
                "image_id": item["image_id"],
                "entity_id": item.get("entity_id"),
                "entity_name": gold,
                "question": question,
                "pred": pred,
                "strict_acc": s_acc,
                "loose_acc": l_acc,
            }
        )
        n = len(rows)
        progress.set_postfix(strict=strict_correct / n if n else 0.0, loose=loose_correct / n if n else 0.0)
    progress.close()
    save_jsonl(out_path, rows)
    return {
        "count": len(rows),
        "strict_correct": strict_correct,
        "loose_correct": loose_correct,
        "strict_acc": strict_correct / len(rows) if rows else 0.0,
        "loose_acc": loose_correct / len(rows) if rows else 0.0,
        "out_path": out_path,
    }


def eval_open_end(editor, split_dir: str, edit_data_path: str, out_path: str, max_new_tokens: int = 32):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    request_map = load_request_map(edit_data_path)
    with open(q_path, "r", encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]

    strict_correct, loose_correct = 0, 0
    rows = []
    progress = tqdm(samples, total=len(samples), desc="BLIP2 OpenEnd", dynamic_ncols=True)
    for item in progress:
        req_bundle = request_map.get(item["image_id"])
        if req_bundle is None:
            raise KeyError(f"No edit request found for image_id={item['image_id']} in {edit_data_path}")
        q_entry = req_bundle["question_map"].get(item.get("question_id"))
        if q_entry is None:
            raise KeyError(
                f"No open question found for question_id={item.get('question_id')} under image_id={item['image_id']} in {edit_data_path}"
            )
        editor.restore_to_original_model()
        editor.edit_one_piece(req_bundle["request"])

        image_name = item.get("image_name") or f"{item['image_id']}.jpg"
        image = Image.open(os.path.join(img_dir, image_name)).convert("RGB")
        prompt = q_entry.get("question", item["question"])
        pred = generate_answer(editor, image, prompt, max_new_tokens=max_new_tokens)
        gold = q_entry.get("target") or get_gold_from_item(item)
        s_acc = strict_match(pred, gold)
        l_acc = loose_match(pred, gold)
        strict_correct += s_acc
        loose_correct += l_acc
        rows.append(
            {
                "question_id": item.get("question_id"),
                "image_id": item.get("image_id"),
                "question": prompt,
                "pred": pred,
                "gold": gold,
                "strict_acc": s_acc,
                "loose_acc": l_acc,
            }
        )
        n = len(rows)
        progress.set_postfix(strict=strict_correct / n if n else 0.0, loose=loose_correct / n if n else 0.0)
    progress.close()
    save_jsonl(out_path, rows)
    return {
        "count": len(rows),
        "strict_correct": strict_correct,
        "loose_correct": loose_correct,
        "strict_acc": strict_correct / len(rows) if rows else 0.0,
        "loose_acc": loose_correct / len(rows) if rows else 0.0,
        "out_path": out_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate edited BLIP2 bridge checkpoint.")
    parser.add_argument("--split_dir", required=True)
    parser.add_argument("--visedit_root", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--ckpt_path", required=True)
    parser.add_argument("--config_path", required=True)
    parser.add_argument("--edit_data_path", required=True)
    parser.add_argument("--entity_out", required=True)
    parser.add_argument("--open_out", required=True)
    parser.add_argument("--summary_out", default=None)
    parser.add_argument("--entity_max_new_tokens", type=int, default=24)
    parser.add_argument("--open_max_new_tokens", type=int, default=32)
    args = parser.parse_args()

    editor = build_editor(args.ckpt_path, args.device, args.config_path, args.visedit_root)
    entity_summary = eval_entity_recognition(
        editor,
        args.split_dir,
        args.edit_data_path,
        args.entity_out,
        args.entity_max_new_tokens,
    )
    open_summary = eval_open_end(
        editor,
        args.split_dir,
        args.edit_data_path,
        args.open_out,
        args.open_max_new_tokens,
    )
    summary = {
        "model": "blip2-opt-2.7b",
        "mode": "edited",
        "checkpoint": args.ckpt_path,
        "config_path": args.config_path,
        "edit_data_path": args.edit_data_path,
        "entity_recognition": entity_summary,
        "open_end": open_summary,
    }
    if args.summary_out:
        os.makedirs(os.path.dirname(args.summary_out), exist_ok=True)
        with open(args.summary_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
