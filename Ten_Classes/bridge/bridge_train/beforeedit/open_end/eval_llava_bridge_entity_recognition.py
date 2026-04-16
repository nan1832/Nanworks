import os, json, re, argparse, hashlib
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration

QUESTION_TEMPLATES = [
    "What is the name of this bridge?",
    "Identify the bridge shown in this image.",
    "Which bridge is shown in the picture?",
    "Please tell me the name of the bridge in this image.",
    "What is this bridge called?"
]

def find_jsonl(split_dir):
    for name in os.listdir(split_dir):
        if name.endswith("_train.jsonl") or name.endswith("_val.jsonl"):
            return os.path.join(split_dir, name)
    raise FileNotFoundError("no *_train.jsonl or *_val.jsonl found")

def find_img_dir(split_dir):
    for d in ["images", "bridge_images"]:
        p = os.path.join(split_dir, d)
        if os.path.isdir(p):
            return p
    raise FileNotFoundError("images dir not found")

def extract_response(text):
    m = re.search(r"ASSISTANT:\s*(.*)", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

def choose_question(image_id):
    h = hashlib.md5(str(image_id).encode("utf-8")).hexdigest()
    idx = int(h, 16) % len(QUESTION_TEMPLATES)
    return QUESTION_TEMPLATES[idx]

def load_unique_images(q_path):
    items = []
    seen = set()
    with open(q_path, "r", encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            image_id = o.get("image_id")
            image_name = o.get("image_name") or (f"{image_id}.jpg" if image_id else None)
            if not image_id or not image_name:
                continue
            if image_id in seen:
                continue
            seen.add(image_id)
            items.append({"image_id": image_id, "image_name": image_name})
    return items

def run(split_dir, model_path, out_name, max_new_tokens=32):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    out_path = os.path.join(split_dir, out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    model = LlavaForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.float16, device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_path)

    images = load_unique_images(q_path)
    results = []
    total = len(images)

    for i, x in enumerate(images, 1):
        image_id = x["image_id"]
        image_name = x["image_name"]
        img_path = os.path.join(img_dir, image_name)
        image = Image.open(img_path).convert("RGB")
        question = choose_question(image_id)
        prompt = f"USER: <image>\n{question}\nAnswer briefly with the bridge name only.\nASSISTANT:"
        inputs = processor(prompt, image, return_tensors="pt").to(model.device)
        gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = processor.batch_decode(gen, skip_special_tokens=True)[0].strip()
        answer = extract_response(text)
        results.append({
            "image_id": image_id,
            "question": question,
            "answer": answer
        })
        if i % 20 == 0 or i == total:
            print(f"progress: {i}/{total}")

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("saved:", out_path, len(results))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split_dir", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max_new_tokens", type=int, default=32)
    a = p.parse_args()
    run(a.split_dir, a.model, a.out, a.max_new_tokens)
