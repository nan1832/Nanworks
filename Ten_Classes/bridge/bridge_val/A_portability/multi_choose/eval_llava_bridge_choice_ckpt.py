import os, json, re, argparse, sys
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration
from tqdm import tqdm

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
        choice_questions = req.get('choice_questions') or []
        question_map = {}
        for q in choice_questions:
            question_id = q.get('question_id')
            if question_id is not None:
                question_map[question_id] = q
        request_map[image_id] = {
            'image': Image.open(image_path).convert("RGB"),
            'prompt': f"{req['prompt']} The answer is:",
            'target_new': req['target_new'],
            'question_map': question_map,
            'entity_id': item.get('entity_id'),
            'entity_name': item.get('entity_name')
        }
    return request_map


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


def run(split_dir, model_path, out_name, max_new_tokens=8, ckpt_path=None, device='cuda:0',
        config_path=None, edit_data_path=None, visedit_root='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main'):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    out_path = os.path.join(split_dir, out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    editor = None
    request_map = None
    if ckpt_path:
        split_name = infer_split_name(split_dir)
        if config_path is None:
            config_path = os.path.join(visedit_root, 'configs', 'vead', 'llava-v1.5-7b-bridge.yaml')
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

    results, correct, total = [], 0, 0
    with open(q_path, 'r', encoding='utf-8') as f:
        samples = [json.loads(line) for line in f]

    entity_total = 0
    entity_rank = {}
    if request_map:
        ordered_entity_ids = []
        for req in request_map.values():
            entity_id = req.get('entity_id')
            if entity_id and entity_id not in entity_rank:
                ordered_entity_ids.append(entity_id)
                entity_rank[entity_id] = len(ordered_entity_ids)
        entity_total = len(ordered_entity_ids)
        print(f"loaded requests: {entity_total} entities, {len(request_map)} images, {len(samples)} questions")

    current_entity_id = None
    progress = tqdm(samples, total=len(samples), desc='Evaluating', dynamic_ncols=True)
    for o in progress:
            if editor is not None:
                editor.restore_to_original_model()
                req = request_map.get(o['image_id'])
                if req is None:
                    raise KeyError(f"No edit request found for image_id={o['image_id']} in {edit_data_path}")
                entity_id = req.get('entity_id')
                entity_name = req.get('entity_name') or ''
                if entity_id != current_entity_id:
                    current_entity_id = entity_id
                    entity_idx = entity_rank.get(entity_id, 0)
                    progress.set_description(f"Entity {entity_idx}/{entity_total}: {entity_name or entity_id}")
                q_entry = None
                if req['question_map']:
                    q_entry = req['question_map'].get(o.get('question_id'))
                    if q_entry is None:
                        raise KeyError(f"No choice question found for question_id={o.get('question_id')} under image_id={o['image_id']} in {edit_data_path}")
                editor.edit_one_piece(req)
                item = dict(o)
                if q_entry is not None:
                    item['question'] = q_entry.get('question', o.get('question'))
                    item['answers'] = q_entry.get('answers') or q_entry.get('options') or o.get('answers') or o.get('options') or []
                    item['correct'] = q_entry.get('correct', o.get('correct'))
                    if q_entry.get('correct_letter') is not None:
                        item['label'] = q_entry['correct_letter']
            else:
                item = o

            img_name = item.get('image_name') or f"{item['image_id']}.jpg"
            img_path = os.path.join(img_dir, img_name)
            image = Image.open(img_path).convert("RGB")
            opts = item.get("answers") or item.get("options") or []
            options_block = "\n".join([f"{LETTERS[i]}) {opts[i]}" for i in range(len(opts))])
            prompt = f"USER: <image>\n{item['question']}\nOptions:\n{options_block}\nAnswer with the option letter only.\nASSISTANT:"
            inputs = processor(prompt, image, return_tensors="pt").to(run_device)
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
            label = item.get('label')
            correct_idx = None
            if isinstance(label, str):
                correct_idx = LETTERS.index(label.strip().upper())
            elif isinstance(label, int):
                correct_idx = label
            if correct_idx is None:
                correct_idx = next((i for i, v in enumerate(item.get("correct", [])) if v == 1), None)
            correct_letter = LETTERS[correct_idx] if correct_idx is not None else None
            acc = int(letter == correct_letter)
            correct += acc
            total += 1
            results.append({
                "question_id": item.get("question_id"),
                "image_id": item.get("image_id"),
                "question": item.get("question"),
                "modelchoose_letter": letter,
                "modelchoose_text": choose_text,
                "correct_letter": correct_letter,
                "acc": acc,
                "raw": text
            })
            progress.set_postfix(question_id=item.get("question_id"), acc=correct / total if total else 0.0)

    progress.close()

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
    p.add_argument('--ckpt', type=str, default=None)
    p.add_argument('--device', type=str, default='cuda:0')
    p.add_argument('--config', type=str, default=None)
    p.add_argument('--edit_data_path', type=str, default=None)
    p.add_argument('--visedit_root', type=str, default='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
    a = p.parse_args()
    run(a.split_dir, a.model, a.out, a.max_new_tokens, a.ckpt, a.device, a.config, a.edit_data_path, a.visedit_root)
