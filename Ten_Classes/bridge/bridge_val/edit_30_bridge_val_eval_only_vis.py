import os, json, re, argparse, sys
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration
from tqdm import tqdm


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


def infer_split_name(split_dir):
    name = os.path.basename(os.path.normpath(split_dir)).lower()
    return 'val' if 'val' in name else 'train'


def get_default_edit_data_path(visedit_root, split_name):
    return os.path.join(visedit_root, 'data', 'bridge', f'edit_30_bridge_{split_name}.json')


def ensure_visedit_imports(visedit_root):
    if visedit_root not in sys.path:
        sys.path.insert(0, visedit_root)
    from utils.GLOBAL import ROOT_PATH
    from utils import load_vllm_for_edit
    from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig
    return ROOT_PATH, load_vllm_for_edit, VEADWithPortability, VEADPortConfig


def build_editor(ckpt_path, device, config_path, visedit_root):
    ROOT_PATH, load_vllm_for_edit, VEADWithPortability, VEADPortConfig = ensure_visedit_imports(visedit_root)
    config = VEADPortConfig.from_yaml(config_path)
    vllm = load_vllm_for_edit(config.edit_model_name, device)
    editor = VEADWithPortability(
        vllm, config, device,
        vllm_data_proc=None, data_proc_device=None,
        train_data_cache_root=os.path.join(ROOT_PATH, 'data')
    )
    editor.load_ckpt(ckpt_path, restrict=True, load_opt=False)
    return editor


def extract_response(text):
    m = re.search(r"ASSISTANT:\s*(.*)", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def normalize_text(s):
    s = str(s).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()


def loose_match(pred, gold):
    p = normalize_text(pred)
    g = normalize_text(gold)
    if not p or not g:
        return 0
    return int((p in g) or (g in p))


def strict_match(pred, gold):
    return int(normalize_text(pred) == normalize_text(gold))


def get_gold_from_item(item):
    if item.get('target'):
        return item['target']
    answers = item.get('answers') or item.get('options') or []
    correct = item.get('correct') or []
    idx = next((i for i, v in enumerate(correct) if v == 1), None)
    if idx is None:
        return ''
    if idx >= len(answers):
        return ''
    return answers[idx]


def load_request_map(edit_data_path, split_dir):
    img_dir = find_img_dir(split_dir)
    with open(edit_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    request_map = {}
    for item in data:
        req = item.get('request', {})
        rel_img = req.get('image')
        if not rel_img:
            continue
        image_id = os.path.splitext(os.path.basename(rel_img))[0]
        image_path = os.path.join(img_dir, f'{image_id}.jpg')
        if not os.path.exists(image_path):
            continue
        open_questions = req.get('open_questions') or []
        question_map = {}
        for q in open_questions:
            qid = q.get('question_id')
            if qid is not None:
                question_map[qid] = q
        request_map[image_id] = {
            'image': Image.open(image_path).convert("RGB"),
            'prompt': f"{req['prompt']} The answer is:",
            'target_new': req['target_new'],
            'question_map': question_map,
            'entity_id': item.get('entity_id'),
            'entity_name': item.get('entity_name')
        }
    return request_map


def resolve_out_path(split_dir, out_name):
    if os.path.isabs(out_name):
        return out_name
    return os.path.join(split_dir, out_name)


def run(split_dir, model_path, out_name, max_new_tokens=64, ckpt_path=None, device='cuda:0',
        config_path=None, edit_data_path=None, visedit_root='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main'):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    out_path = resolve_out_path(split_dir, out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    editor = None
    request_map = None
    if ckpt_path:
        split_name = infer_split_name(split_dir)
        if config_path is None:
            config_path = os.path.join(visedit_root, 'configs', 'vead', 'llava-v1.5-7b-bridge-only-vis.yaml')
        if edit_data_path is None:
            edit_data_path = get_default_edit_data_path(visedit_root, split_name)
        editor = build_editor(ckpt_path, device, config_path, visedit_root)
        request_map = load_request_map(edit_data_path, split_dir)
        model = editor.vllm.model
        processor = editor.vllm.processor
        run_device = device
    else:
        model = LlavaForConditionalGeneration.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")
        processor = AutoProcessor.from_pretrained(model_path)
        run_device = model.device

    with open(q_path, 'r', encoding='utf-8') as f:
        samples = [json.loads(line) for line in f]

    if request_map is not None:
        print(f"loaded requests: {len(request_map)} images, total questions: {len(samples)}")

    strict_correct, loose_correct, total = 0, 0, 0
    results = []
    progress = tqdm(samples, total=len(samples), desc='OpenEnd Eval', dynamic_ncols=True)
    for o in progress:
        item = dict(o)
        if editor is not None:
            editor.restore_to_original_model()
            req = request_map.get(o['image_id'])
            if req is None:
                raise KeyError(f"No edit request found for image_id={o['image_id']} in {edit_data_path}")
            q_entry = None
            if req['question_map']:
                q_entry = req['question_map'].get(o.get('question_id'))
                if q_entry is None:
                    raise KeyError(f"No open question found for question_id={o.get('question_id')} under image_id={o['image_id']} in {edit_data_path}")
            editor.edit_one_piece(req)
            if q_entry is not None:
                item['question'] = q_entry.get('question', item.get('question'))
                item['target'] = q_entry.get('target', item.get('target'))
                item['answers'] = q_entry.get('answers', item.get('answers'))
                item['correct'] = q_entry.get('correct', item.get('correct'))

        img_name = item.get('image_name') or f"{item['image_id']}.jpg"
        img_path = os.path.join(img_dir, img_name)
        image = Image.open(img_path).convert("RGB")
        prompt = f"USER: <image>\n{item['question']}\nASSISTANT:"
        inputs = processor(prompt, image, return_tensors="pt").to(run_device)
        with torch.no_grad():
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = processor.batch_decode(gen, skip_special_tokens=True)[0].strip()
        pred = extract_response(text)
        gold = get_gold_from_item(item)
        s_acc = strict_match(pred, gold)
        l_acc = loose_match(pred, gold)

        strict_correct += s_acc
        loose_correct += l_acc
        total += 1

        results.append({
            "question_id": item.get("question_id"),
            "image_id": item.get("image_id"),
            "question": item.get("question"),
            "pred": pred,
            "gold": gold,
            "strict_acc": s_acc,
            "loose_acc": l_acc,
            "raw": text
        })
        progress.set_postfix(strict=strict_correct / total if total else 0.0, loose=loose_correct / total if total else 0.0)
    progress.close()

    with open(out_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("saved:", out_path, len(results))
    print("strict_acc:", (strict_correct / total) if total else 0.0)
    print("loose_acc:", (loose_correct / total) if total else 0.0)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--split_dir', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--max_new_tokens', type=int, default=64)
    p.add_argument('--ckpt', type=str, default=None)
    p.add_argument('--device', type=str, default='cuda:0')
    p.add_argument('--config', type=str, default=None)
    p.add_argument('--edit_data_path', type=str, default=None)
    p.add_argument('--visedit_root', type=str, default='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
    a = p.parse_args()
    run(a.split_dir, a.model, a.out, a.max_new_tokens, a.ckpt, a.device, a.config, a.edit_data_path, a.visedit_root)
