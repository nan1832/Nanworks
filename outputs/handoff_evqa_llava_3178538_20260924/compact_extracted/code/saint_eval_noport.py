"""
Ablation evaluation script: loads a plain VEAD checkpoint (trained without
portability loss) and evaluates ALL metrics including portability.

Place this file in: VisEdit-main/saint_eval_noport.py

Usage:
  python saint_eval_noport.py \\
    -dvc cuda:0 \\
    -ckpt records/vead/llava-v1.5-7b/<run_dir>/epoch-XXX-i-XXXX-ema_loss-X.XXXX \\
    --split val \\
    -enp noport_ep300
"""

import os, argparse, torch
from copy import deepcopy
from tqdm import tqdm
from collections import defaultdict
from datetime import datetime

from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig
from evaluation.vllm_editor_eval import VLLMEditorEvaluation


def get_attr():
    parser = argparse.ArgumentParser(
        description='Ablation eval: plain VEAD (no portability training) on EditSaint')
    parser.add_argument('-dvc', '--device', type=str, default='cuda:0')
    parser.add_argument('-ckpt', '--editor_ckpt_path', type=str, required=True)
    parser.add_argument('--split', type=str, default='val',
                        choices=['train', 'val'])
    parser.add_argument('-enp', '--eval_name_postfix', type=str, default='')
    parser.add_argument('-dsn', '--data_sample_n', type=int, default=None)
    parser.add_argument('--config', type=str,
                        default=os.path.join(ROOT_PATH,
                            'configs/vead/llava-v1.5-7b-saint-noport.yaml'))
    return parser.parse_args()


def evaluate_portability(editor, eval_data, results, tokenizer):
    """Measure portability after single-edit — identical to saint_eval.py."""
    port_acc = defaultdict(lambda: [0, 0])
    for ed, rd in tqdm(zip(eval_data, results), desc='Portability eval',
                       total=len(eval_data)):
        editor.restore_to_original_model()
        editor.edit_one_piece(ed['request'])
        for hop_key in ['1hop', '2hop']:
            for q in ed.get('portability', {}).get(hop_key, []):
                (input_embeds, vt_range), label_ids, label_masks = \
                    editor.vllm.prompts_imgs_target_to_xym(
                        [q['prompt']], [q['image']], [q['target']])
                logits = editor.vllm.get_llm_outpt(input_embeds, vt_range).logits
                pre_y = torch.softmax(logits, -1).argmax(-1)
                pre_y = pre_y[:, -label_ids.shape[1]:]
                acc = float(((pre_y == label_ids) * label_masks).sum()
                            / label_masks.sum())
                pred_text = tokenizer.decode(pre_y[label_masks.to(bool)])
                hop_res = rd.setdefault('portability', {}).setdefault(hop_key, [])
                hop_res.append({'prompt': q['prompt'], 'target': q['target'],
                                'predict_after_edit': pred_text, 'acc': acc})
                port_acc[hop_key][0] += acc
                port_acc[hop_key][1] += 1
        editor.restore_to_original_model()
    return {hop: (s / n if n > 0 else 0.0) for hop, (s, n) in port_acc.items()}


def main():
    cfg = get_attr()
    device = cfg.device

    config = VEADPortConfig.from_yaml(cfg.config)
    vllm = load_vllm_for_edit(config.edit_model_name, device)
    editor = VEADWithPortability(vllm, config, device,
                  vllm_data_proc=None, data_proc_device=None,
                  train_data_cache_root=os.path.join(ROOT_PATH, 'data'))

    print(f'[Ablation] Loading checkpoint: {cfg.editor_ckpt_path}')
    i, epoch, loss, ema_loss = editor.load_ckpt(
        cfg.editor_ckpt_path, restrict=True, load_opt=False)
    print(f'Checkpoint: epoch={epoch}, iter={i}, ema_loss={ema_loss:.4f}')

    from dataset.edit_saint_loader import EditSaint
    split = cfg.split
    data_path    = os.path.join(ROOT_PATH, f'data/edit_saint/edit_saint_{split}.json')
    img_root_dir = os.path.join(ROOT_PATH, 'data/edit_saint')
    coco_img_dir = os.path.join(ROOT_PATH, 'data/easy-edit-mm/images')
    eval_data_obj = EditSaint(data_path, img_root_dir,
                               coco_img_dir=coco_img_dir,
                               data_n=cfg.data_sample_n)
    print(f'Loaded {len(eval_data_obj.data)} {split} samples')

    eval_name = f'EditSaint-{split}-noport'
    if cfg.eval_name_postfix:
        eval_name = f'{eval_name}-{cfg.eval_name_postfix}'
    result_dir = os.path.join('eval_results', 'vead', config.edit_model_name,
                               eval_name, 'single_edit')
    os.makedirs(result_dir, exist_ok=True)

    ev = VLLMEditorEvaluation(editor, eval_data_obj, eval_name, 'eval_results')
    results = ev.evaluate_single_edit()

    tokenizer = editor.vllm.get_llm_tokenizer()
    eval_data_raw = eval_data_obj.data_with_img
    port_mean = evaluate_portability(editor, eval_data_raw, results, tokenizer)

    ev.save_results(os.path.join(result_dir, 'results.json'), results)
    mean_res = ev.get_mean_results(results)
    mean_res['portability'] = port_mean
    mean_res['sample_count'] = len(results)
    ev.save_results(os.path.join(result_dir, 'mean_results.json'), mean_res)

    print('\n========== Ablation Evaluation Summary (NO portability training) ==========')
    print(f'  Split        : {split}')
    print(f'  Checkpoint   : epoch={epoch}, iter={i}, ema_loss={ema_loss:.4f}')
    print(f'  Samples      : {len(results)}')
    rel_acc = mean_res['reliability'].get('acc', float('nan'))
    print(f'  Reliability  : {rel_acc:.4f}')
    for gk, gv in mean_res['generality'].items():
        print(f'  Generality [{gk}] acc: {gv.get("acc", float("nan")):.4f}')
    for lk, lv in mean_res['locality'].items():
        print(f'  Locality   [{lk}] acc: {lv.get("acc", float("nan")):.4f}')
    for hk, hv in port_mean.items():
        print(f'  Portability[{hk}] acc: {hv:.4f}   ← key ablation result')
    print(f'  Results saved to: {result_dir}')
    print('==========================================================================')


if __name__ == '__main__':
    main()
