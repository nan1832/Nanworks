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


def resolve_bridge_image(root_bridge_dir: str, rel_path: str) -> str:
    if rel_path.startswith("val/images"):
        rel_path = "bridge_val/bridge_images" + rel_path[len("val/images") :]
    elif rel_path.startswith("train/images"):
        rel_path = "bridge_train/bridge_images" + rel_path[len("train/images") :]
    return os.path.join(root_bridge_dir, rel_path)


def save_jsonl(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ensure_visedit_imports(visedit_root: str):
    if visedit_root not in sys.path:
        sys.path.insert(0, visedit_root)
    from utils import load_vllm_for_edit

    return load_vllm_for_edit


def generate_answer(vllm, image: Image.Image, prompt: str, max_new_tokens: int) -> str:
    processor = vllm.processor
    model = vllm.model
    inputs = processor(images=image, text=prompt, return_tensors="pt")
    inputs = {k: v.to(vllm.device) if hasattr(v, "to") else v for k, v in inputs.items()}
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    prompt_norm = normalize_text(prompt)
    text_norm = normalize_text(text)
    if text_norm.startswith(prompt_norm):
        text = text[len(prompt) :].strip()
    return text.strip()


def eval_entity_recognition(vllm, split_dir: str, out_path: str, max_new_tokens: int = 24):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    split_name = infer_split_name(split_dir)
    ann_path = os.path.join(split_dir, f"30_bridge_{split_name}_ann.jsonl")
    q2ent = load_entity_by_question(ann_path)
    images = load_unique_images_with_entity(q_path, q2ent)

    strict_correct, loose_correct = 0, 0
    rows = []
    progress = tqdm(images, total=len(images), desc="BLIP2 Entity", dynamic_ncols=True)
    for item in progress:
        image = Image.open(os.path.join(img_dir, item["image_name"])).convert("RGB")
        question = choose_question(item["image_id"]) + " Answer briefly with the bridge name only."
        pred = generate_answer(vllm, image, question, max_new_tokens=max_new_tokens)
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


def eval_open_end(vllm, split_dir: str, out_path: str, max_new_tokens: int = 32):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    with open(q_path, "r", encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]

    strict_correct, loose_correct = 0, 0
    rows = []
    progress = tqdm(samples, total=len(samples), desc="BLIP2 OpenEnd", dynamic_ncols=True)
    for item in progress:
        image_name = item.get("image_name") or f"{item['image_id']}.jpg"
        image = Image.open(os.path.join(img_dir, image_name)).convert("RGB")
        prompt = item["question"]
        pred = generate_answer(vllm, image, prompt, max_new_tokens=max_new_tokens)
        gold = get_gold_from_item(item)
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


def eval_portability(vllm, root_bridge_dir: str, edit_data_path: str):
    tokenizer = vllm.get_llm_tokenizer()
    with open(edit_data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    all_records = []
    per_sample = []
    progress = tqdm(raw_data, total=len(raw_data), desc="BLIP2 Portability", dynamic_ncols=True)
    for item in progress:
        sample_result = {"entity_id": item.get("entity_id"), "entity_name": item.get("entity_name"), "1hop": [], "2hop": []}
        for hop_key in ["1hop", "2hop"]:
            for q in item.get("portability", {}).get(hop_key, []):
                image_path = resolve_bridge_image(root_bridge_dir, q["image"]) if q.get("image") else None
                image = Image.open(image_path).convert("RGB") if image_path else None
                prompt = f"{q['prompt']} The answer is:"
                target = q["target"]
                (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym([prompt], [image], [target])
                with torch.no_grad():
                    logits = vllm.get_llm_outpt(llm_inpt, vt_range).logits
                pre_y = torch.softmax(logits, -1).argmax(-1)
                pre_y = pre_y[:, -label_ids.shape[1] :]
                acc = float(((pre_y == label_ids) * label_masks).sum() / label_masks.sum())
                pred_text = tokenizer.decode(pre_y[label_masks.to(bool)])
                rec = {
                    "prompt": prompt,
                    "target": target,
                    "predict_after_edit": pred_text,
                    "acc": acc,
                    "property": q.get("property", "unknown"),
                    "route_desc": q.get("route_desc", ""),
                }
                sample_result[hop_key].append(rec)
                all_records.append(
                    {
                        "entity_id": item.get("entity_id"),
                        "entity_name": item.get("entity_name"),
                        "hop": hop_key,
                        "property": q.get("property", "unknown"),
                        "acc": acc,
                    }
                )
        per_sample.append(sample_result)
    progress.close()

    def summarize(records: List[Dict]):
        if not records:
            return {"overall": {"acc": 0.0, "count": 0}, "per_hop": {}}
        total = len(records)
        out = {
            "overall": {"acc": sum(r["acc"] for r in records) / total, "count": total},
            "per_hop": {},
        }
        for hop in ["1hop", "2hop"]:
            hop_rows = [r for r in records if r["hop"] == hop]
            if hop_rows:
                out["per_hop"][hop] = {
                    "acc": sum(r["acc"] for r in hop_rows) / len(hop_rows),
                    "count": len(hop_rows),
                }
        return out

    return {
        "summary": summarize(all_records),
        "per_sample": per_sample,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate unedited BLIP2 on bridge validation.")
    parser.add_argument("--split_dir", required=True)
    parser.add_argument("--visedit_root", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--edit_data_path", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--entity_max_new_tokens", type=int, default=24)
    parser.add_argument("--open_max_new_tokens", type=int, default=32)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    load_vllm_for_edit = ensure_visedit_imports(args.visedit_root)
    vllm = load_vllm_for_edit("blip2-opt-2.7b", args.device)

    entity_out = os.path.join(args.out_dir, "bridge_val_entity_recog_blip2_unedited.jsonl")
    open_out = os.path.join(args.out_dir, "bridge_val_openend_blip2_unedited.jsonl")
    port_out = os.path.join(args.out_dir, "bridge_val_portability_blip2_unedited.json")
    summary_out = os.path.join(args.out_dir, "bridge_val_blip2_unedited_summary.json")

    entity_summary = eval_entity_recognition(vllm, args.split_dir, entity_out, args.entity_max_new_tokens)
    open_summary = eval_open_end(vllm, args.split_dir, open_out, args.open_max_new_tokens)
    port_results = eval_portability(vllm, os.path.dirname(args.split_dir), args.edit_data_path)

    with open(port_out, "w", encoding="utf-8") as f:
        json.dump(port_results, f, ensure_ascii=False, indent=2)

    summary = {
        "model": "blip2-opt-2.7b",
        "mode": "unedited",
        "split_dir": args.split_dir,
        "edit_data_path": args.edit_data_path,
        "entity_recognition": entity_summary,
        "open_end": open_summary,
        "portability": port_results["summary"],
        "outputs": {
            "entity_jsonl": entity_out,
            "open_jsonl": open_out,
            "portability_json": port_out,
        },
    }
    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
