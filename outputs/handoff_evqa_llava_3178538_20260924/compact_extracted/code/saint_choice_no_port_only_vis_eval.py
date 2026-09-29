"""
Evaluate a trained VEAD checkpoint (with or without portability) on the
Saint-Catherine multiple-choice validation set.

For every question the script:
  1. Finds the edit request for the corresponding image.
  2. Calls editor.edit_one_piece(request) to mount the adapter.
  3. Runs free-form generation; extracts the first A-D letter.
  4. Compares against the gold answer (always "A" – the dataset places the
     correct option first).

Output format is identical to saint_catherine_val_choice_llava.jsonl so
results can be compared directly with the unedited LLaVA baseline.

Place this file in: VisEdit-main/saint_choice_eval.py

Usage (port checkpoint):
  python saint_choice_eval.py \\
    -dvc cuda:0 \\
    -ckpt records/vead/llava-v1.5-7b/saint_port-2026.03.18-18.10.44/epoch-300-i-1200-ema_loss-0.2326 \\
    --config configs/vead/llava-v1.5-7b-saint.yaml \\
    --val_jsonl /path/to/saint_catherine_val.jsonl \\
    --img_root  data/edit_saint \\
    --edit_val  data/edit_saint/edit_saint_val.json \\
    -o saint_choice_edited_port.jsonl

Usage (noport checkpoint):
  python saint_choice_eval.py \\
    -dvc cuda:0 \\
    -ckpt records/vead/llava-v1.5-7b/<noport_run>/epoch-XXX-... \\
    --config configs/vead/llava-v1.5-7b-saint-noport.yaml \\
    --val_jsonl /path/to/saint_catherine_val.jsonl \\
    --img_root  data/edit_saint \\
    --edit_val  data/edit_saint/edit_saint_val.json \\
    -o saint_choice_edited_noport.jsonl
"""

import os
import re
import json
import argparse
from collections import defaultdict

import torch
from PIL import Image
from tqdm import tqdm

from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def get_args():
    parser = argparse.ArgumentParser(
        description='Evaluate VEAD adapter on Saint-Catherine MCQ val set')
    parser.add_argument('-dvc', '--device', type=str, default='cuda:0')
    parser.add_argument('-ckpt', '--editor_ckpt_path', type=str, required=True,
                        help='Path to VEAD checkpoint (no extension)')
    parser.add_argument('--config', type=str,
                        default=os.path.join(ROOT_PATH,
                            'configs/vead/llava-v1.5-7b-saint.yaml'),
                        help='YAML config; use saint.yaml for port, '
                             'saint-noport.yaml for noport checkpoints')
    parser.add_argument('--val_jsonl', type=str, required=True,
                        help='Path to saint_catherine_val.jsonl '
                             '(the MCQ annotation file)')
    parser.add_argument('--img_root', type=str,
                        default=os.path.join(ROOT_PATH, 'data/edit_saint'),
                        help='Root dir for edit_saint images '
                             '(contains val/images/*.jpg)')
    parser.add_argument('--img_split', type=str, default='val',
                        help='Sub-folder under img_root, default: val')
    parser.add_argument('--edit_val', type=str,
                        default=os.path.join(ROOT_PATH,
                            'data/edit_saint/edit_saint_val.json'),
                        help='edit_saint_val.json – used to find edit requests')
    parser.add_argument('-o', '--output', type=str,
                        default='saint_choice_edited.jsonl',
                        help='Output JSONL file path')
    parser.add_argument('--max_new_tokens', type=int, default=5,
                        help='Max new tokens for generation (default 5)')
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
LETTER_IDX = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
IDX_LETTER = {'A': 0, 'B': 1, 'C': 2, 'D': 3}


def build_prompt(question: str, answers: list) -> str:
    """Build the same prompt format used in saint_catherine_val_choice_llava.jsonl."""
    opts = '\n'.join(f'{LETTER_IDX[i]}) {ans}' for i, ans in enumerate(answers))
    return (f'USER: \n{question}\n'
            f'Options:\n{opts}\n'
            f'Answer with the option letter only.\nASSISTANT:')


def extract_letter(text: str) -> str:
    """Return the first A-D letter found in generated text, else '?'."""
    m = re.search(r'\b([A-D])\b', text.strip().upper())
    if m:
        return m.group(1)
    # fallback: first character if it is A-D
    if text.strip() and text.strip()[0].upper() in 'ABCD':
        return text.strip()[0].upper()
    return '?'


def load_edit_requests(edit_val_path: str, img_root: str, img_split: str) -> dict:
    """
    Returns a dict: image_id -> edit_request dict
    where edit_request = {'image': PIL.Image, 'prompt': str, 'target_new': str}
    edit_one_piece() requires image to be a PIL Image object, not a path string.
    """
    with open(edit_val_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    img_dir = os.path.join(img_root, img_split, 'images')
    requests = {}
    for d in raw:
        req = d['request']
        # image field is stored as e.g. "val/images/GLDv2_xxx.jpg"
        img_rel = req['image']
        img_filename = os.path.basename(img_rel)          # GLDv2_xxx.jpg
        image_id = os.path.splitext(img_filename)[0]      # GLDv2_xxx
        abs_path = os.path.join(img_dir, img_filename)
        pil_image = Image.open(abs_path).convert('RGB')   # load as PIL Image
        requests[image_id] = {
            'image': pil_image,
            'prompt': req['prompt'] + ' The answer is:',
            'target_new': req['target_new'],
        }
    return requests


def load_val_questions(val_jsonl_path: str) -> list:
    """Load saint_catherine_val.jsonl into a list of dicts."""
    questions = []
    with open(val_jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def load_editor(config_path: str, ckpt_path: str, device: str):
    """
    Auto-detect config type (VEADPortConfig vs VEADConfig) and return
    a loaded editor with the checkpoint weights.
    """
    with open(config_path, 'r') as f:
        import yaml
        cfg_dict = yaml.safe_load(f)

    has_port = 'port_lambda' in cfg_dict

    vllm = load_vllm_for_edit(
        cfg_dict['edit_model_name'] if 'edit_model_name' in cfg_dict
        else cfg_dict.get('model_name', 'llava-v1.5-7b'),
        device
    )

    if has_port:
        from editor.vllm_editors.vead.vead_with_port import (
            VEADWithPortability, VEADPortConfig)
        config = VEADPortConfig.from_yaml(config_path)
        editor = VEADWithPortability(
            vllm, config, device,
            vllm_data_proc=None, data_proc_device=None,
            train_data_cache_root=os.path.join(ROOT_PATH, 'data'))
    else:
        from editor.vllm_editors.vead.vead import VEAD, VEADConfig
        config = VEADConfig.from_yaml(config_path)
        editor = VEAD(
            vllm, config, device,
            vllm_data_proc=None, data_proc_device=None,
            train_data_cache_root=os.path.join(ROOT_PATH, 'data'))

    print(f'Loading checkpoint: {ckpt_path}')
    i, epoch, loss, ema_loss = editor.load_ckpt(ckpt_path, restrict=True, load_opt=False)
    print(f'Checkpoint: epoch={epoch}, iter={i}, ema_loss={ema_loss:.4f}')
    return editor


# ─────────────────────────────────────────────────────────────────────────────
# Generation helper
# ─────────────────────────────────────────────────────────────────────────────
def generate_answer(editor, prompt: str, image_path: str,
                    answers: list, max_new_tokens: int = 5) -> str:
    """
    Generate next token and constrain prediction to A/B/C/D, matching baseline behavior.

    We compute logits for the next token and pick the best among candidate token
    ids corresponding to letters A-D (considering both plain and leading-space variants).
    """
    vllm = editor.vllm
    if image_path and os.path.exists(image_path):
        image = Image.open(image_path).convert('RGB')
    else:
        image = None

    # keep a single-token dummy target to locate prompt end
    dummy_target = 'A'
    (llm_inpt, vt_range), label_ids, label_masks = \
        vllm.prompts_imgs_target_to_xym(
            [prompt], [image], [dummy_target])

    with torch.no_grad():
        outpt = vllm.get_llm_outpt(llm_inpt, vt_range)
        logits = outpt.logits  # (1, seq_len, vocab_size)

    # label_ids covers the target tokens at the end of the sequence;
    # the first generated token is at position (seq_len - label_len)
    seq_len = llm_inpt['inputs_embeds'].shape[1]
    label_len = label_ids.shape[1]
    prompt_len = seq_len - label_len
    next_token_logits = logits[0, prompt_len - 1, :]
    tokenizer = vllm.get_llm_tokenizer()

    # candidate ids for A/B/C/D (plain and with leading space)
    def last_id(text):
        ids = tokenizer.encode(text, add_special_tokens=False)
        return ids[-1] if ids else None

    candidates = {
        'A': [last_id('A'), last_id(' A')],
        'B': [last_id('B'), last_id(' B')],
        'C': [last_id('C'), last_id(' C')],
        'D': [last_id('D'), last_id(' D')],
    }
    best_letter, best_logit = None, None
    for letter, id_list in candidates.items():
        scores = []
        for tid in id_list:
            if tid is not None and tid < next_token_logits.shape[-1]:
                scores.append(float(next_token_logits[tid]))
        if scores:
            score = max(scores)
            if best_logit is None or score > best_logit:
                best_logit = score
                best_letter = letter

    # return chosen letter or fallback '?'
    return best_letter if best_letter is not None else '?'


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    args = get_args()

    # 1. Load editor + checkpoint
    editor = load_editor(args.config, args.editor_ckpt_path, args.device)

    # 2. Load edit requests (for activating the adapter per image)
    edit_requests = load_edit_requests(
        args.edit_val, args.img_root, args.img_split)
    print(f'Loaded {len(edit_requests)} edit requests')

    # 3. Load MCQ questions
    questions = load_val_questions(args.val_jsonl)
    print(f'Loaded {len(questions)} MCQ questions')

    # 4. Group questions by image_id (same image only needs one adapter activation)
    by_image = defaultdict(list)
    for q in questions:
        by_image[q['image_id']].append(q)

    # 5. Evaluate
    results = []
    n_correct = 0

    for image_id, qs in tqdm(by_image.items(), desc='Images'):
        # Activate adapter for this image
        editor.restore_to_original_model()

        if image_id not in edit_requests:
            print(f'[WARN] No edit request found for image_id={image_id}, '
                  f'skipping adapter activation.')
            req = None
        else:
            req = edit_requests[image_id]
            editor.edit_one_piece(req)

        img_path = os.path.join(
            args.img_root, args.img_split, 'images', f'{image_id}.jpg')

        for q in qs:
            question_id = q['question_id']
            question     = q['question']
            answers      = q['answers']          # list of 4 strings
            # correct is always index 0 → letter "A"
            correct_letter = 'A'

            prompt = build_prompt(question, answers)
            # Full raw string mirrors the existing baseline format
            raw_prefix = (f'USER:  \n{question}\nOptions:\n'
                          + '\n'.join(f'{LETTER_IDX[i]}) {a}'
                                      for i, a in enumerate(answers))
                          + '\nAnswer with the option letter only.\nASSISTANT:')

            try:
                gen_text = generate_answer(
                    editor, prompt, img_path, answers, args.max_new_tokens)
            except Exception as e:
                print(f'[ERROR] q_id={question_id}: {e}')
                gen_text = '?'

            chosen_letter = extract_letter(gen_text)
            chosen_text   = (answers[IDX_LETTER[chosen_letter]]
                             if chosen_letter in IDX_LETTER else '?')
            consistence    = (chosen_letter == correct_letter)
            raw_full       = raw_prefix + ' ' + (gen_text.strip() if gen_text else '?')

            if consistence:
                n_correct += 1

            results.append({
                'question_id':      question_id,
                'image_id':         image_id,
                'question':         question,
                'modelchoose_letter': chosen_letter,
                'modelchoose_text':   chosen_text,
                'correct_letter':   correct_letter,
                'consistence':      consistence,
                'raw':              raw_full,
            })

        editor.restore_to_original_model()

    # Sort back to original question order
    results.sort(key=lambda x: x['question_id'])

    # 6. Save
    out_path = args.output
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    acc = n_correct / len(results) if results else 0.0
    print(f'\n========== MCQ Evaluation Summary ==========')
    print(f'  Questions : {len(results)}')
    print(f'  Correct   : {n_correct}')
    print(f'  Accuracy  : {acc:.4f}  ({n_correct}/{len(results)})')
    print(f'  Saved to  : {out_path}')
    print(f'=============================================')


if __name__ == '__main__':
    main()
