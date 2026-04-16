import os, json, re
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration
import argparse

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def extract_response(text):
    m = re.search(r"ASSISTANT:\s*(.*)", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

def pick_letter(text):
    response = extract_response(text)
    m = re.search(r"\b([A-D])\b", response, flags=re.IGNORECASE)
    return m.group(1).upper() if m else None

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

def load_entity_name_map(ann_path):
    mp = {}
    with open(ann_path, 'r', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            qid = o.get("question_id")
            if qid is not None and qid not in mp:
                mp[qid] = o.get("entity_name", "")
    return mp

def run(split_dir, model_path, out_name, max_new_tokens=8):
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
            opts = o.get("answers") or o.get("options") or []
            options_block = "\n".join([f"{LETTERS[i]}) {opts[i]}" for i in range(len(opts))])
            prompt = f"USER: <image>\nEntity name: {entity_name}\nQuestion: {o['question']}\nOptions:\n{options_block}\nAnswer with the option letter only.\nASSISTANT:"
            inputs = processor(prompt, image, return_tensors="pt").to(model.device)
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            text = processor.batch_decode(gen, skip_special_tokens=True)[0].strip()
            letter = pick_letter(text)
            response = extract_response(text)
            choose_text = None
            if letter and letter in LETTERS[:len(opts)]:
                choose_text = opts[LETTERS.index(letter)]
            else:
                for i, a in enumerate(opts):
                    if a.lower() in response.lower():
                        letter = LETTERS[i]
                        choose_text = a
                        break
            label = o.get('label')
            correct_idx = None
            if isinstance(label, str):
                t = label.strip().upper()
                if len(t) == 1 and "A" <= t <= "Z":
                    correct_idx = LETTERS.index(t)
            elif isinstance(label, int):
                correct_idx = label
            if correct_idx is None:
                correct_idx = next((i for i, v in enumerate(o.get("correct", [])) if v == 1), None)
            correct_letter = LETTERS[correct_idx] if correct_idx is not None and correct_idx < len(LETTERS) else None
            acc = int(letter == correct_letter)
            correct += acc
            total += 1
            results.append({
                "question_id": qid,
                "image_id": o.get("image_id"),
                "entity_name": entity_name,
                "question": o.get("question"),
                "modelchoose_letter": letter,
                "modelchoose_text": choose_text,
                "correct_letter": correct_letter,
                "acc": acc,
                "raw": text
            })
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("saved:", out_path, len(results))
    print("choice_acc:", (correct / total) if total else 0.0)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--split_dir', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--max_new_tokens', type=int, default=8)
    a = p.parse_args()
    run(a.split_dir, a.model, a.out, a.max_new_tokens)
