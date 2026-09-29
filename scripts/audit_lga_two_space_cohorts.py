#!/usr/bin/env python3
"""Check all 42 historical cohorts without loading model weights or decoding images.

Uses the original dataset parsers and checks image path existence. This metadata
audit does not replace the runner's real-image preflight or GPU smoke comparison.
"""
import argparse
import csv
import importlib
import json
import os
import sys
from pathlib import Path

from run_lga_two_space_ablation import MODELS, DATASETS, original_dir, read_jsonl, atomic_json, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', required=True)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    project = Path(args.project_dir).resolve()
    sys.path[:0] = [str(project), str(project / 'scripts')]
    os.chdir(str(project))
    from PIL import Image
    class MetadataImage:
        def __init__(self, path):
            if not Path(path).is_file():
                raise FileNotFoundError(path)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def convert(self, mode):
            return self
        def copy(self):
            return None
    Image.open = MetadataImage
    helpers = {False: importlib.import_module('run_ours_direct_candidate_layers'),
               True: importlib.import_module('run_ours_direct_candidate_layers_qwen_chatfix')}
    cached_data, records = {}, []
    for space in ['parameter', 'visual']:
        for ds in DATASETS:
            for model in MODELS:
                args.space, args.dataset, args.model = space, ds, model
                helper = helpers[space == 'parameter' or model.startswith('qwen')]
                key = (helper.__name__, ds)
                if key not in cached_data:
                    info = helper.DEFAULT_DATASETS[ds]
                    cached_data[key] = helper.load_edit_data(ds, info['data_path'], info['img_root'], None)
                data = cached_data[key]
                source = original_dir(args)
                cache_path = source / 'model_pred_cache.jsonl'
                cache_rows = read_jsonl(cache_path)
                cache = {str(r['sample_id']): r for r in cache_rows}
                assert len(cache) == len(cache_rows)
                ids = set()
                for i, row in enumerate(data):
                    sid = str(helper.get_sample_id(row, i))
                    item = cache.get(sid, {})
                    req = row['request']
                    old, new = str(item.get('answer') or '').strip(), str(req['target_new']).strip()
                    if not old:
                        continue
                    if space == 'parameter':
                        normalize = lambda x: ' '.join(x.strip().lower().split())
                        if not new or item.get('status') != 'ok' or normalize(old) == normalize(new):
                            continue
                    assert item['prompt'] == req['prompt']
                    ids.add(sid)
                score_path = source / ('layer_scores.csv' if space == 'parameter' else 'ours_direct_layer_scores.csv')
                with score_path.open(encoding='utf-8-sig') as stream:
                    rows = list(csv.DictReader(stream))
                counts = {int(r['valid_sample_count' if space == 'parameter' else 'n_request']) for r in rows}
                assert len(counts) == 1 and len(rows) == MODELS[model]
                if space == 'visual':
                    sample_path = source / 'ours_direct_sample_layer_scores.jsonl'
                    layer_ids = {l: set() for l in range(MODELS[model])}
                    for r in read_jsonl(sample_path):
                        sid, layer = str(r['sample_id']), int(r['layer'])
                        assert sid not in layer_ids[layer]
                        layer_ids[layer].add(sid)
                    assert all(x == layer_ids[0] for x in layer_ids.values())
                    assert layer_ids[0] <= ids
                    ids = layer_ids[0]
                assert len(ids) == next(iter(counts))
                records.append(dict(space=space, dataset=ds, model=model, samples=len(ids), total=len(data),
                                    layers=len(rows), cache_sha256=sha(cache_path), score_sha256=sha(score_path),
                                    cohort_sha256=__import__('hashlib').sha256(json.dumps(sorted(ids)).encode()).hexdigest(),
                                    status='cohort_verified_no_model_execution'))
    atomic_json(args.output, dict(records=records, passed=len(records), images='paths checked; decoding deferred to real runner'))
    print(json.dumps(dict(passed=len(records), output=args.output)))


if __name__ == '__main__':
    main()
