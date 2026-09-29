"""
EditSaint dataset loader for VisEdit training.

Place this file in: VisEdit-main/dataset/edit_saint_loader.py
Then import: from dataset.edit_saint_loader import EditSaint

Data format (from edit_saint_train.json):
  Each sample has: request, generality, locality, portability
  portability contains '1hop' and '2hop' lists of
    {'image': path, 'prompt': str, 'target': str, ...}

Image root directories:
  img_root_dir  : root for edit/generality/portability images
                  e.g. VisEdit-main/data/edit_saint/
                  (stores train/images/*.jpg and val/images/*.jpg)
  coco_img_dir  : root for locality image_loc images (val2014/...)
                  e.g. VisEdit-main/data/easy-edit-mm/images/
                  (stores val2014/COCO_val2014_*.jpg)
"""

import os, json
from copy import deepcopy
from tqdm import tqdm
from .vllm import BaseVLLMEditData


class EditSaint(BaseVLLMEditData):
    def __init__(self, data_path: str, img_root_dir: str,
                 coco_img_dir: str = None, data_n=None):
        """
        Args:
            data_path   : path to edit_saint_train.json or edit_saint_val.json
            img_root_dir: root dir for edit/generality/portability images
                          (e.g. VisEdit-main/data/edit_saint/)
            coco_img_dir: root dir for locality val2014 images
                          (e.g. VisEdit-main/data/easy-edit-mm/images/)
                          If None, falls back to img_root_dir.
            data_n      : optionally limit number of samples
        """
        if coco_img_dir is None:
            coco_img_dir = img_root_dir
        print('Load EditSaint from: %s' % data_path)
        print('  Edit/Gen/Port images root : %s' % img_root_dir)
        print('  Locality COCO images root : %s' % coco_img_dir)
        with open(data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        if data_n is not None:
            raw_data = raw_data[:data_n]

        data_with_img_path = []
        for d in tqdm(raw_data, 'Preparing EditSaint data'):
            new_d = {
                'request': {},
                'generality': {'text_rephrase': [], 'image_rephrase': []},
                'locality': {'text_loc': [], 'image_loc': []},
                'portability': {'1hop': [], '2hop': []},
            }
            # request
            new_d['request']['image'] = os.path.join(img_root_dir, d['request']['image'])
            new_d['request']['prompt'] = '%s The answer is:' % d['request']['prompt']
            new_d['request']['target_new'] = d['request']['target_new']
            # generality
            for g in d['generality'].get('text_rephrase', []):
                new_d['generality']['text_rephrase'].append({
                    'image': os.path.join(img_root_dir, g['image']) if g.get('image') else None,
                    'prompt': '%s The answer is:' % g['prompt'],
                    'target': g['target'],
                })
            for g in d['generality'].get('image_rephrase', []):
                new_d['generality']['image_rephrase'].append({
                    'image': os.path.join(img_root_dir, g['image']) if g.get('image') else None,
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
                    img_path = os.path.join(coco_img_dir, img_path)
                new_d['locality']['image_loc'].append({
                    'image': img_path,
                    'prompt': '%s The answer is:' % loc['prompt'],
                    'target': loc['target'],
                })
            # portability (NEW)
            for hop_key in ['1hop', '2hop']:
                for p in d['portability'].get(hop_key, []):
                    new_d['portability'][hop_key].append({
                        'image': os.path.join(img_root_dir, p['image']) if p.get('image') else None,
                        'prompt': '%s The answer is:' % p['prompt'],
                        'target': p['target'],
                    })
            data_with_img_path.append(new_d)

        data_with_img = deepcopy(data_with_img_path)
        for d in tqdm(data_with_img, 'Loading images'):
            self.__load_imgs_for_data_with_img_path__(d)

        super().__init__(data_with_img, data_with_img_path)

    def dataset_name(self):
        return 'EditSaint'
