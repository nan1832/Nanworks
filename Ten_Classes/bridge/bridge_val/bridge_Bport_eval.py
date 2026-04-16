"""
Evaluation script for EditBridge (B-group portability on val set).

Place this file in: VisEdit-main/bridge_Bport_eval.py

Evaluates:
  - Reliability (entity recognition after edit)
  - Generality  (text/image rephrase)
  - Locality    (text/image, KL-based)
  - Portability (B-group 1hop + 2hop questions on val set)
    * Also reports per-property and per-entity breakdown

----------------------------------------------------------------------
Server paths:
  Model        : /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
  Ten_Classes  : /datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes
  VisEdit root : /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
----------------------------------------------------------------------

Usage:
  python bridge_Bport_eval.py \
    -dvc cuda:0 \
    -ckpt records/vead/llava-v1.5-7b/bridge_port-YYYY.MM.DD-HH.MM.SS/epoch-XXX-i-YYY-ema_loss-Z.ZZZZ \
    -enp bridge_Bport_ep300

  Add --split train to evaluate A-group portability on train set (using edit_30_bridge_train.json).
"""

import os, json, argparse, torch
from copy import deepcopy
from tqdm import tqdm
from collections import defaultdict, OrderedDict
from datetime import datetime

from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from editor.vllm_editors.vead.vead_with_port import VEADWithPortability, VEADPortConfig
from evaluation.vllm_editor_eval import VLLMEditorEvaluation

VISEDIT_ROOT = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main'
TEN_CLASSES_ROOT = '/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes'


def get_attr():
    parser = argparse.ArgumentParser(description='Evaluate VEAD+Port on EditBridge B-group')
    parser.add_argument('-dvc', '--device', type=str, default='cuda:0')
    parser.add_argument('-ckpt', '--editor_ckpt_path', type=str, required=True,
                        help='Path to checkpoint file')
    parser.add_argument('--split', type=str, default='val', choices=['train', 'val'],
                        help='val = B-group eval; train = A-group eval')
    parser.add_argument('-enp', '--eval_name_postfix', type=str, default='',
                        help='Postfix for result directory name')
    parser.add_argument('-dsn', '--data_sample_n', type=int, default=None,
                        help='Limit number of eval samples')
    parser.add_argument('--config', type=str,
                        default=os.path.join(ROOT_PATH,
                            'configs/vead/llava-v1.5-7b-bridge.yaml'),
                        help='Path to bridge config yaml')
    return parser.parse_args()


def evaluate_portability_detailed(editor, eval_data, raw_json_data, tokenizer):
    """
    Evaluate portability after single-edit, with detailed per-property
    and per-entity breakdowns.

    Returns:
        port_results : list of dicts (one per sample), each with
                       {'1hop': [...], '2hop': [...]} of per-question results
        summary      : dict with overall, per-hop, per-property, per-entity stats
    """
    port_results = []
    all_records = []

    for i, (ed, raw_d) in enumerate(tqdm(
            zip(eval_data, raw_json_data), desc='Portability eval',
            total=len(eval_data))):
        editor.restore_to_original_model()
        editor.edit_one_piece(ed['request'])

        sample_port = {}
        entity_id = raw_d.get('entity_id', f'entity_{i}')
        entity_name = raw_d.get('entity_name', '')

        for hop_key in ['1hop', '2hop']:
            hop_list_ed = ed.get('portability', {}).get(hop_key, [])
            hop_list_raw = raw_d.get('portability', {}).get(hop_key, [])
            sample_hop_results = []

            for j, q in enumerate(hop_list_ed):
                (input_embeds, vt_range), label_ids, label_masks = \
                    editor.vllm.prompts_imgs_target_to_xym(
                        [q['prompt']], [q['image']], [q['target']])
                logits = editor.vllm.get_llm_outpt(input_embeds, vt_range).logits
                pre_y = torch.softmax(logits, -1).argmax(-1)
                pre_y = pre_y[:, -label_ids.shape[1]:]
                acc = float(((pre_y == label_ids) * label_masks).sum() / label_masks.sum())
                pred_text = tokenizer.decode(pre_y[label_masks.to(bool)])

                raw_q = hop_list_raw[j] if j < len(hop_list_raw) else {}
                prop = raw_q.get('property', 'unknown')
                route_desc = raw_q.get('route_desc', '')

                result_item = {
                    'prompt': q['prompt'],
                    'target': q['target'],
                    'predict_after_edit': pred_text,
                    'acc': acc,
                    'property': prop,
                    'route_desc': route_desc,
                }
                sample_hop_results.append(result_item)
                all_records.append({
                    'entity_id': entity_id,
                    'entity_name': entity_name,
                    'hop': hop_key,
                    'property': prop,
                    'acc': acc,
                    'target': q['target'],
                    'predict': pred_text,
                })

            if sample_hop_results:
                sample_port[hop_key] = sample_hop_results
        port_results.append(sample_port)
        editor.restore_to_original_model()

    # Build summary
    summary = build_portability_summary(all_records)
    return port_results, summary


def build_portability_summary(records):
    """Build multi-level summary from flat record list."""
    if not records:
        return {'overall': {'acc': 0, 'count': 0}}

    summary = {}

    # Overall
    total_acc = sum(r['acc'] for r in records)
    total_n = len(records)
    summary['overall'] = {'acc': total_acc / total_n, 'count': total_n}

    # Per hop
    hop_stats = defaultdict(lambda: [0.0, 0])
    for r in records:
        hop_stats[r['hop']][0] += r['acc']
        hop_stats[r['hop']][1] += 1
    summary['per_hop'] = {h: {'acc': s / n, 'count': n}
                          for h, (s, n) in sorted(hop_stats.items())}

    # Per property
    prop_stats = defaultdict(lambda: [0.0, 0])
    for r in records:
        prop_stats[r['property']][0] += r['acc']
        prop_stats[r['property']][1] += 1
    summary['per_property'] = {p: {'acc': s / n, 'count': n}
                               for p, (s, n) in sorted(prop_stats.items())}

    # Per entity
    ent_stats = defaultdict(lambda: {'acc_sum': 0.0, 'count': 0, 'name': ''})
    for r in records:
        e = ent_stats[r['entity_id']]
        e['acc_sum'] += r['acc']
        e['count'] += 1
        e['name'] = r['entity_name']
    summary['per_entity'] = {
        eid: {'entity_name': v['name'],
              'acc': v['acc_sum'] / v['count'],
              'count': v['count']}
        for eid, v in sorted(ent_stats.items())
    }

    # Per hop x property
    hp_stats = defaultdict(lambda: [0.0, 0])
    for r in records:
        hp_stats[(r['hop'], r['property'])][0] += r['acc']
        hp_stats[(r['hop'], r['property'])][1] += 1
    summary['per_hop_property'] = {
        f"{h}|{p}": {'acc': s / n, 'count': n}
        for (h, p), (s, n) in sorted(hp_stats.items())
    }

    return summary


def main():
    cfg = get_attr()
    device = cfg.device
    split = cfg.split

    # 1. Load config & build editor
    config = VEADPortConfig.from_yaml(cfg.config)
    vllm = load_vllm_for_edit(config.edit_model_name, device)
    editor = VEADWithPortability(
        vllm, config, device,
        vllm_data_proc=None, data_proc_device=None,
        train_data_cache_root=os.path.join(ROOT_PATH, 'data')
    )

    # 2. Load checkpoint
    print(f'Loading checkpoint: {cfg.editor_ckpt_path}')
    i, epoch, loss, ema_loss = editor.load_ckpt(cfg.editor_ckpt_path,
                                                  restrict=True, load_opt=False)
    print(f'Checkpoint: epoch={epoch}, iter={i}, ema_loss={ema_loss:.4f}')

    # 3. Load dataset
    from dataset.edit_bridge_loader import EditBridge

    if split == 'val':
        data_path = os.path.join(VISEDIT_ROOT, 'data/bridge/edit_30_bridge_val.json')
        bridge_img_root = os.path.join(TEN_CLASSES_ROOT, 'bridge')
        img_path_map = {'val/images': 'bridge_val/bridge_images'}
    else:
        data_path = os.path.join(VISEDIT_ROOT, 'data/bridge/edit_30_bridge_train.json')
        bridge_img_root = os.path.join(TEN_CLASSES_ROOT, 'bridge')
        img_path_map = {'train/images': 'bridge_train/bridge_images'}

    coco_img_dir = os.path.join(VISEDIT_ROOT, 'data/easy-edit-mm/images')

    eval_data_obj = EditBridge(
        data_path,
        img_root_dir=bridge_img_root,
        coco_img_dir=coco_img_dir,
        data_n=cfg.data_sample_n,
        img_path_map=img_path_map,
    )
    print(f'Loaded {len(eval_data_obj.data)} {split} samples')

    # Load raw JSON for metadata (entity_id, property, route_desc)
    with open(data_path, 'r', encoding='utf-8') as f:
        raw_json_data = json.load(f)
    if cfg.data_sample_n:
        raw_json_data = raw_json_data[:cfg.data_sample_n]

    # 4. Build result dir
    eval_name = f'EditBridge-{split}'
    if cfg.eval_name_postfix:
        eval_name = f'{eval_name}-{cfg.eval_name_postfix}'
    result_dir = os.path.join('eval_results', 'vead', config.edit_model_name,
                               eval_name, 'single_edit')
    os.makedirs(result_dir, exist_ok=True)
    print(f'Results will be saved to: {result_dir}')

    # 5. Standard eval (reliability / generality / locality)
    ev = VLLMEditorEvaluation(editor, eval_data_obj, eval_name, 'eval_results')
    results = ev.evaluate_single_edit()

    # 6. Portability eval (B-group for val, A-group for train)
    tokenizer = editor.vllm.get_llm_tokenizer()
    eval_data_raw = eval_data_obj.data_with_img
    port_results, port_summary = evaluate_portability_detailed(
        editor, eval_data_raw, raw_json_data, tokenizer)

    # Merge portability results into per-sample results
    for r, pr in zip(results, port_results):
        r['portability'] = pr

    # 7. Save results
    ev.save_results(os.path.join(result_dir, 'results.json'), results)

    mean_res = ev.get_mean_results(results)
    mean_res['portability'] = port_summary
    mean_res['sample_count'] = len(results)
    ev.save_results(os.path.join(result_dir, 'mean_results.json'), mean_res)

    # Save portability detail separately for easy analysis
    ev.save_results(os.path.join(result_dir, 'portability_detail.json'), {
        'summary': port_summary,
        'per_sample': port_results,
    })

    # 8. Print summary
    group_label = 'B-group' if split == 'val' else 'A-group'
    print(f'\n{"="*60}')
    print(f'  Evaluation Summary ({group_label} on {split} set)')
    print(f'{"="*60}')
    print(f'  Checkpoint   : epoch={epoch}, iter={i}, ema_loss={ema_loss:.4f}')
    print(f'  Samples      : {len(results)}')

    rel_acc = mean_res['reliability'].get('acc', float('nan'))
    print(f'  Reliability  : {rel_acc:.4f}')
    for gk, gv in mean_res['generality'].items():
        print(f'  Generality [{gk}] acc: {gv.get("acc", float("nan")):.4f}')
    for lk, lv in mean_res['locality'].items():
        print(f'  Locality   [{lk}] acc: {lv.get("acc", float("nan")):.4f}')

    print(f'\n  --- Portability ({group_label}) ---')
    ps = port_summary
    print(f'  Overall      : {ps["overall"]["acc"]:.4f}  (n={ps["overall"]["count"]})')
    for h, hv in ps.get('per_hop', {}).items():
        print(f'  {h:12s}  : {hv["acc"]:.4f}  (n={hv["count"]})')

    print(f'\n  --- Per Property ---')
    for p, pv in ps.get('per_property', {}).items():
        print(f'  {p:30s} : {pv["acc"]:.4f}  (n={pv["count"]})')

    print(f'\n  --- Per Entity ---')
    for eid, ev_data in ps.get('per_entity', {}).items():
        print(f'  {eid:12s} {ev_data["entity_name"]:35s} : '
              f'{ev_data["acc"]:.4f}  (n={ev_data["count"]})')

    print(f'\n  Results saved to: {result_dir}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
