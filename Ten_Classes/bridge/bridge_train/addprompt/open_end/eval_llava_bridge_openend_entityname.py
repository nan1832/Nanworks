import os, json, re, argparse
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration

def find_jsonl(split_dir):
    for name in os.listdir(split_dir):
        if name.endswith('_val.jsonl') or name.endswith('_train.jsonl'):
            return os.path.join(split_dir, name)
    raise FileNotFoundError('no *_val.jsonl or *_train.jsonl found')

def find_ann_jsonl(split_dir):
    for name in os.listdir(split_dir):
        if name.endswith('_ann.jsonl'):
            return os.path.join(split_dir, name)
    raise FileNotFoundError('no *_ann.jsonl found')

def find_img_dir(split_dir):
    for d in ['images', 'bridge_images']:
        p = os.path.join(split_dir, d)
        if os.path.isdir(p):
            return p
    raise FileNotFoundError('images dir not found')

def extract_response(text):
    m = re.search(r"ASSISTANT:\s*(.*)", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

def normalize(s):
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^[\s\.,;:!?\-–—\"'\(\)\[\]]+|[\s\.,;:!?\-–—\"'\(\)\[\]]+$", "", s)
    return s

def get_gold_answer(item):
    if item.get("answer"):
        return item["answer"]
    if item.get("target"):
        return item["target"]
    answers = item.get("answers") or item.get("options") or []
    if len(answers) > 0:
        correct = item.get("correct", [])
        if isinstance(correct, list):
            idx = next((i for i, v in enumerate(correct) if v == 1), None)
            if idx is not None and idx < len(answers):
                return answers[idx]
        label = item.get("label")
        if isinstance(label, int) and 0 <= label < len(answers):
            return answers[label]
        if isinstance(label, str):
            t = label.strip().upper()
            if len(t) == 1 and "A" <= t <= "Z":
                idx = ord(t) - ord("A")
                if 0 <= idx < len(answers):
                    return answers[idx]
    return ""

def load_entity_name_map(ann_path):
    mp = {}
    with open(ann_path, 'r', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            qid = o.get("question_id")
            if qid is not None and qid not in mp:
                mp[qid] = o.get("entity_name", "")
    return mp

def run(split_dir, model_path, out_name, max_new_tokens=64):
    q_path = find_jsonl(split_dir)
    ann_path = find_ann_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    out_path = os.path.join(split_dir, out_name)
    entity_name_map = load_entity_name_map(ann_path)
    model = LlavaForConditionalGeneration.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")
    processor = AutoProcessor.from_pretrained(model_path)
    results, correct, total = [], 0, 0

    with open(q_path, 'r', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            qid = o.get("question_id")
            entity_name = entity_name_map.get(qid, "")
            img_name = o.get('image_name') or f"{o['image_id']}.jpg"
            img_path = os.path.join(img_dir, img_name)
            image = Image.open(img_path).convert("RGB")
            prompt = f"USER: <image>\nEntity name: {entity_name}\nQuestion: {o['question']}\nAnswer briefly.\nASSISTANT:"
            inputs = processor(prompt, image, return_tensors="pt").to(model.device)
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            raw_text = processor.batch_decode(gen, skip_special_tokens=True)[0].strip()
            pred = extract_response(raw_text)
            gold = get_gold_answer(o)
            acc = int(normalize(pred) == normalize(gold))
            correct += acc
            total += 1
            results.append({
                "question_id": qid,
                "image_id": o.get("image_id"),
                "image_name": o.get("image_name"),
                "entity_name": entity_name,
                "question": o.get("question"),
                "pred": pred,
                "gold": gold,
                "acc": acc,
                "raw": raw_text
            })

    with open(out_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("saved:", out_path, len(results))
    print("openend_acc:", (correct / total) if total else 0.0)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--split_dir', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--max_new_tokens', type=int, default=64)
    a = p.parse_args()
    run(a.split_dir, a.model, a.out, a.max_new_tokens)
