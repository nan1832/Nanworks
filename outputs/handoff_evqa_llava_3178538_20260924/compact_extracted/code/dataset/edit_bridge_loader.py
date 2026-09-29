"""
EditBridge dataset loader for VisEdit training with portability.

Place this file in: VisEdit-main/dataset/edit_bridge_loader.py
Then import: from dataset.edit_bridge_loader import EditBridge

Data format (from edit_30_bridge_train.json):
  Each sample has: request, generality, locality, portability
  portability contains '2hop' list of
    {'image': path, 'prompt': str, 'target': str, ...}

Image path mapping:
  JSON stores relative paths like 'train/images/GLDv2_xxx.jpg'.
  On disk, bridge images live at 'bridge_train/bridge_images/GLDv2_xxx.jpg'.
  The loader remaps these automatically via img_path_map.

  Locality COCO images use paths like 'val2014/COCO_val2014_xxx.jpg',
  resolved relative to coco_img_dir.
"""

import os, json
from copy import deepcopy
from tqdm import tqdm
from .vllm import BaseVLLMEditData


class EditBridge(BaseVLLMEditData):
    def __init__(self, data_path: str, img_root_dir: str,
                 coco_img_dir: str = None, data_n=None,
                 img_path_map: dict = None):
        """
        Args:
            data_path    : path to edit_30_bridge_train.json
            img_root_dir : root dir for bridge images
                           e.g. /path/to/Ten_Classes/bridge/
            coco_img_dir : root dir for locality val2014 images
                           e.g. /path/to/VisEdit-main/data/easy-edit-mm/images/
                           If None, falls back to img_root_dir.
            data_n       : optionally limit number of samples
            img_path_map : dict mapping JSON path prefixes to disk path prefixes
                           e.g. {'train/images': 'bridge_train/bridge_images'}
                           Applied to all non-COCO image paths.
        """
        if coco_img_dir is None:
            coco_img_dir = img_root_dir
        if img_path_map is None:
            img_path_map = {'train/images': 'bridge_train/bridge_images'}

        print('Load EditBridge from: %s' % data_path)
        print('  Bridge images root : %s' % img_root_dir)
        print('  Locality COCO root : %s' % coco_img_dir)

        with open(data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        if data_n is not None:
            raw_data = raw_data[:data_n]

        def remap(rel_path):
            """Apply img_path_map prefix substitution."""
            if rel_path is None:
                return None
            for src, dst in img_path_map.items():
                if rel_path.startswith(src):
                    return dst + rel_path[len(src):]
            return rel_path

        def resolve_bridge_img(rel_path):
            if rel_path is None:
                return None
            return os.path.join(img_root_dir, remap(rel_path))

        def resolve_coco_img(rel_path):
            if rel_path is None:
                return None
            return os.path.join(coco_img_dir, rel_path)

        data_with_img_path = []
        for d in tqdm(raw_data, 'Preparing EditBridge data'):
            new_d = {
                'request': {},
                'generality': {'text_rephrase': [], 'image_rephrase': []},
                'locality': {'text_loc': [], 'image_loc': []},
                'portability': {'1hop': [], '2hop': []},
            }

            # request
            new_d['request']['image'] = resolve_bridge_img(d['request']['image'])
            new_d['request']['prompt'] = '%s The answer is:' % d['request']['prompt']
            new_d['request']['target_new'] = d['request']['target_new']

            # generality
            for g in d['generality'].get('text_rephrase', []):
                new_d['generality']['text_rephrase'].append({
                    'image': resolve_bridge_img(g['image']) if g.get('image') else None,
                    'prompt': '%s The answer is:' % g['prompt'],
                    'target': g['target'],
                })
            for g in d['generality'].get('image_rephrase', []):
                new_d['generality']['image_rephrase'].append({
                    'image': resolve_bridge_img(g['image']) if g.get('image') else None,
                    'prompt': '%s The answer is:' % g['prompt'],
                    'target': g['target'],
                })

            # locality — text_loc has no image; image_loc uses COCO val2014
            for loc in d['locality'].get('text_loc', []):
                new_d['locality']['text_loc'].append({
                    'image': None,
                    'prompt': '%s?' % loc['prompt'],
                    'target': loc['target'],
                })
            for loc in d['locality'].get('image_loc', []):
                img_path = loc.get('image')
                if img_path:
                    img_path = resolve_coco_img(img_path)
                new_d['locality']['image_loc'].append({
                    'image': img_path,
                    'prompt': '%s The answer is:' % loc['prompt'],
                    'target': loc['target'],
                })

            # portability (1hop + 2hop)
            for hop_key in ['1hop', '2hop']:
                for p in d.get('portability', {}).get(hop_key, []):
                    new_d['portability'][hop_key].append({
                        'image': resolve_bridge_img(p['image']) if p.get('image') else None,
                        'prompt': '%s The answer is:' % p['prompt'],
                        'target': p['target'],
                    })

            data_with_img_path.append(new_d)

        data_with_img = deepcopy(data_with_img_path)
        for d in tqdm(data_with_img, 'Loading images'):
            self.__load_imgs_for_data_with_img_path__(d)

        super().__init__(data_with_img, data_with_img_path)

    def dataset_name(self):
        return 'EditBridge'
