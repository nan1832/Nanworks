import os, json, re, argparse, sys, hashlib
from PIL import Image
import torch
from tqdm import tqdm
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


def strict_match(pred, gold):
    return int(normalize_text(pred) == normalize_text(gold))


def loose_match(pred, gold):
    p = normalize_text(pred)
    g = normalize_text(gold)
    if not p or not g:
        return 0
    return int((p in g) or (g in p))


def choose_question(image_id):
    h = hashlib.md5(str(image_id).encode("utf-8")).hexdigest()
    idx = int(h, 16) % len(QUESTION_TEMPLATES)
    return QUESTION_TEMPLATES[idx]


def load_entity_by_question(ann_path):
    q2ent = {}
    with open(ann_path, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            q2ent[d['question_id']] = (d.get('entity_id'), d.get('entity_name'))
    return q2ent


def load_unique_images_with_entity(q_path, q2ent):
    seen = set()
    items = []
    with open(q_path, 'r', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            image_id = o.get('image_id')
            image_name = o.get('image_name') or (f"{image_id}.jpg" if image_id else None)
            if not image_id or not image_name:
                continue
            if image_id in seen:
                continue
            seen.add(image_id)
            entity_id, entity_name = q2ent.get(o.get('question_id'), (None, None))
            items.append({
                'image_id': image_id,
                'image_name': image_name,
                'entity_id': entity_id,
                'entity_name': entity_name
            })
    return items


def load_entity_request_map(edit_data_path, split_dir):
    img_dir = find_img_dir(split_dir)
    with open(edit_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    entity_req = {}
    for item in data:
        req = item.get('request', {})
        rel_img = req.get('image')
        if not rel_img:
            continue
        image_id = os.path.splitext(os.path.basename(rel_img))[0]
        image_path = os.path.join(img_dir, f'{image_id}.jpg')
        if not os.path.exists(image_path):
            continue
        entity_id = item.get('entity_id')
        if not entity_id:
            continue
        entity_req[entity_id] = {
            'image': Image.open(image_path).convert("RGB"),
            'prompt': f"{req['prompt']} The answer is:",
            'target_new': req['target_new']
        }
    return entity_req


def resolve_out_path(split_dir, out_name):
    if os.path.isabs(out_name):
        return out_name
    return os.path.join(split_dir, out_name)


def run(split_dir, model_path, out_name, max_new_tokens=32, ckpt_path=None, device='cuda:0',
        config_path=None, edit_data_path=None, visedit_root='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main',
        ann_path=None):
    q_path = find_jsonl(split_dir)
    img_dir = find_img_dir(split_dir)
    out_path = resolve_out_path(split_dir, out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    split_name = infer_split_name(split_dir)
    if ann_path is None:
        ann_path = os.path.join(split_dir, f'30_bridge_{split_name}_ann.jsonl')

    q2ent = load_entity_by_question(ann_path)
    images = load_unique_images_with_entity(q_path, q2ent)

    editor = None
    entity_req_map = None
    if ckpt_path:
        if config_path is None:
            config_path = os.path.join(visedit_root, 'configs', 'vead', 'llava-v1.5-7b-bridge-only-vis.yaml')
        if edit_data_path is None:
            edit_data_path = get_default_edit_data_path(visedit_root, split_name)
        editor = build_editor(ckpt_path, device, config_path, visedit_root)
        entity_req_map = load_entity_request_map(edit_data_path, split_dir)
        model = editor.vllm.model
        processor = editor.vllm.processor
        run_device = device
    else:
        model = LlavaForConditionalGeneration.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")
        processor = AutoProcessor.from_pretrained(model_path)
        run_device = model.device

    strict_correct, loose_correct, total = 0, 0, 0
    results = []
    progress = tqdm(images, total=len(images), desc='Entity Recognition', dynamic_ncols=True)
    for o in progress:
        if editor is not None:
            req = entity_req_map.get(o.get('entity_id'))
            if req is None:
                raise KeyError(f"No edit request found for entity_id={o.get('entity_id')} image_id={o.get('image_id')} in {edit_data_path}")
            editor.restore_to_original_model()
            editor.edit_one_piece(req)

        img_path = os.path.join(img_dir, o['image_name'])
        image = Image.open(img_path).convert("RGB")
        question = choose_question(o['image_id'])
        prompt = f"USER: <image>\n{question}\nAnswer briefly with the bridge name only.\nASSISTANT:"
        inputs = processor(prompt, image, return_tensors="pt").to(run_device)
        with torch.no_grad():
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = processor.batch_decode(gen, skip_special_tokens=True)[0].strip()
        pred = extract_response(text)
        gold = o.get('entity_name') or ''
        s_acc = strict_match(pred, gold)
        l_acc = loose_match(pred, gold)
        strict_correct += s_acc
        loose_correct += l_acc
        total += 1
        results.append({
            'image_id': o.get('image_id'),
            'entity_id': o.get('entity_id'),
            'entity_name': gold,
            'question': question,
            'pred': pred,
            'strict_acc': s_acc,
            'loose_acc': l_acc,
            'raw': text
        })
        progress.set_postfix(strict=strict_correct / total if total else 0.0, loose=loose_correct / total if total else 0.0)
    progress.close()

    with open(out_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('saved:', out_path, len(results))
    print('strict_acc:', (strict_correct / total) if total else 0.0)
    print('loose_acc:', (loose_correct / total) if total else 0.0)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--split_dir', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--max_new_tokens', type=int, default=32)
    p.add_argument('--ckpt', type=str, default=None)
    p.add_argument('--device', type=str, default='cuda:0')
    p.add_argument('--config', type=str, default=None)
    p.add_argument('--edit_data_path', type=str, default=None)
    p.add_argument('--visedit_root', type=str, default='/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
    p.add_argument('--ann_path', type=str, default=None)
    a = p.parse_args()
    run(a.split_dir, a.model, a.out, a.max_new_tokens, a.ckpt, a.device, a.config, a.edit_data_path, a.visedit_root, a.ann_path)
