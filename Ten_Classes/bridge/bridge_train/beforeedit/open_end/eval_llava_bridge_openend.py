import os, json
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration
import argparse

def find_jsonl(split_dir):
    for name in os.listdir(split_dir):
        if name.endswith('_val.jsonl') or name.endswith('_train.jsonl'):
            return os.path.join(split_dir, name)
    raise FileNotFoundError('no *_val.jsonl or *_train.jsonl found')

def find_img_dir(split_dir):
    for d in ['images', 'bridge_images']:
        p = os.path.join(split_dir, d)
        if os.path.isdir(p):
            return p
    raise FileNotFoundError('images dir not found')

def norm(s):
    return str(s).strip().lower()

def run(split_dir, model_path, out_name, max_new_tokens=64):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    out_path = os.path.join(split_dir, out_name)
    model = LlavaForConditionalGeneration.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")
    processor = AutoProcessor.from_pretrained(model_path)
    results, correct, total = [], 0, 0
    with open(q_path, 'r', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            img_name = o.get('image_name') or f"{o['image_id']}.jpg"
            img_path = os.path.join(img_dir, img_name)
            image = Image.open(img_path).convert("RGB")
            prompt = f"USER: <image>\n{o['question']}\nASSISTANT:"
            inputs = processor(prompt, image, return_tensors="pt").to(model.device)
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            text = processor.batch_decode(gen, skip_special_tokens=True)[0].strip()
            gold = o.get('answer') or o.get('target') or ''
            acc = int(norm(text) == norm(gold))
            correct += acc
            total += 1
            results.append({
                "question_id": o.get("question_id"),
                "image_id": o.get("image_id"),
                "question": o.get("question"),
                "pred": text,
                "gold": gold,
                "acc": acc
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
