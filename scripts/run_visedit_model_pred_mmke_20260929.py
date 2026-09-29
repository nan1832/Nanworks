"""Resume-safe MMKE model-pred contribution extraction using the archived runner."""
import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import types


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(p)


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def reference(source, project):
    """Load the frozen original script, changing only its filesystem root."""
    path = Path(source) / 'scripts__run_evqa_module_contribution_pilot500_multi.py'
    text = path.read_text()
    needle = 'PROJECT_ROOT = Path(__file__).resolve().parents[1]'
    assert text.count(needle) == 1
    text = text.replace(needle, 'PROJECT_ROOT = Path(' + repr(str(project)) + ')')
    module = types.ModuleType('archived_contribution')
    module.__file__ = str(path)
    exec(compile(text, str(path), 'exec'), module.__dict__)
    return module


def pre_functions(source):
    import numpy as np
    tree = ast.parse((Path(source) / 'scripts__run_visedit_keytoken_candidate_layers.py').read_text())
    names = ['moving_average', 'find_high_region', 'pre_candidates']
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(nodes) == 3
    ns = {'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<original Pre functions>', 'exec'), ns)
    return ns


def aggregate(records, n_layers, source):
    import numpy as np
    ps = {k: np.array([r['p'][k] for r in records], dtype=np.float64) for k in ['layer', 'att', 'mlp']}
    vs = {k: np.array([r['v'][k] for r in records], dtype=np.float64) for k in ps}
    assert all(a.shape == (len(records), n_layers) and np.isfinite(a).all() for a in list(ps.values()) + list(vs.values()))
    # Match the original signed_contribution, including its epsilon convention.
    eps = 1e-12
    denom = np.maximum(np.maximum(np.abs(vs['att']).max(1), np.abs(vs['mlp']).max(1)), eps)[:, None]
    means = {}
    for k in ['att', 'mlp']:
        scaled = vs[k] / denom
        means[k] = (np.sign(scaled) * np.sqrt(np.abs(scaled) + eps) * np.sqrt(np.maximum(ps[k], 0))).mean(0)
    att, mlp = means['att'], means['mlp']
    pos = np.maximum(att, 0) + np.maximum(mlp, 0)
    def ranks(v):
        r = np.empty(len(v), dtype=np.int64)
        r[np.argsort(-v)] = np.arange(1, len(v) + 1)
        return r
    rp, rs, ra = ranks(pos), ranks(att + mlp), ranks(np.abs(att) + np.abs(mlp))
    rows = [dict(layer=i, attn_mean=float(att[i]), mlp_mean=float(mlp[i]), score_positive=float(pos[i]),
                 score_signed=float(att[i]+mlp[i]), score_abs=float(abs(att[i])+abs(mlp[i])),
                 rank_positive=int(rp[i]), rank_signed=int(rs[i]), rank_abs=int(ra[i])) for i in range(n_layers)]
    pre = pre_functions(source)
    variants = {}
    for name, score in [('attn', np.maximum(att, 0)), ('mlp', np.maximum(mlp, 0)), ('attn+mlp', pos)]:
        smooth = pre['moving_average'](score, 3)
        region, threshold, high = pre['find_high_region'](smooth, 0.5)
        ranking = [int(x) for x in np.argsort(-score)]
        variants[name] = dict(scores=score.tolist(), ranking=ranking, top5=ranking[:5], maximum_layer=ranking[0],
                              maximum_score=float(score[ranking[0]]), high_region=list(region) if region else [],
                              threshold=threshold, high_layers=high, smoothed=smooth.tolist(),
                              pre_top3=pre['pre_candidates'](region[0], 3) if region else [])
        if name != 'attn+mlp':
            signed = att if name == 'attn' else mlp
            variants[name]['signed_ranking'] = [int(x) for x in np.argsort(-signed)]
    return rows, variants


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--model', required=True)
    args = parser.parse_args()
    root, project = Path(args.root), Path(args.project)
    source = root / 'source_snapshot'
    ref = reference(source, project)
    import torch
    import numpy as np
    from PIL import Image
    import transformers
    cfgpath = project / 'configs/p_track' / (args.model + '.yaml')
    cfg = ref.PTrackConfig.from_yaml(str(cfgpath))
    spec = dict(ref.MODEL_SPECS.get(args.model, {'loader': 'visedit', 'model_path': 'models/blip2-opt-2.7b'}))
    runner = ref.build_runner(args.model, spec, cfg, 'cuda:0', 'auto', None)
    if hasattr(runner, 'predict_id'):
        original_predict = runner.predict_id
        def capture(word, logits):
            assert torch.isfinite(logits[0, -1]).all()
            target = original_predict(word, logits)
            runner.last_target_id = int(target)
            return target
        runner.predict_id = capture
        tokenizer = runner.tokenizer
    else:
        original_tracking = runner.pt.p_tracking
        def capture_tracking(*a, **kw):
            assert torch.isfinite(runner.pt.outpt[0, -1]).all()
            runner.last_target_id = int(torch.softmax(runner.pt.outpt[0, -1], 0).argmax())
            return original_tracking(*a, **kw)
        runner.pt.p_tracking = capture_tracking
        tokenizer = runner.pt.tokenizer
    base = project.parent / 'datasets/MMKE-Bench'
    failures = []
    for dataset, expected in [('visual', 214), ('entity', 636)]:
        out = root / 'results' / ('mmke-' + dataset) / args.model
        datafile = base / 'data_json' / (dataset + '_train.json')
        raw = json.loads(datafile.read_text())
        assert len(raw) == expected
        protocol = dict(dataset='mmke-' + dataset, model=args.model, key_mode='model_pred', sample_count=len(raw),
                        dataset_path=str(datafile), dataset_sha256=sha(datafile), cfg_path=str(cfgpath), cfg_sha256=sha(cfgpath),
                        source_sha256={p.name: sha(p) for p in source.iterdir() if p.is_file()},
                        runner_sha256=sha(__file__), torch_version=torch.__version__, transformers_version=transformers.__version__,
                        target_rule='next-token argmax at final prompt position, no answer teacher forcing',
                        prompt_rule="row['src'] + ' The answer is:'", loader=spec['loader'], torch_dtype='original auto',
                        contribution_rule='sign(v/M)*sqrt(abs(v/M)+1e-12)*sqrt(max(p,0)); M=max_abs_attn_mlp_per_sample',
                        aggregate_rule='mean signed contribution first; clip each module mean to nonnegative; sum for attn+mlp',
                        pre_rule='window=3; mean+0.5 population std; longest high region; precede by up to 3 layers',
                        tie_rule='numpy argsort(-scores), matching original contribution rank_positive', num_layers=cfg.num_layers)
        if (out / 'protocol.json').exists():
            assert json.loads((out / 'protocol.json').read_text()) == protocol
        else:
            write(out / 'protocol.json', protocol)
        protocol_sha = sha(out / 'protocol.json')
        records = []
        start = time.time()
        errors = []
        for i, row in enumerate(raw):
            sample = out / 'samples' / ('%06d.json' % i)
            try:
                if sample.exists():
                    result = json.loads(sample.read_text())
                    assert result['protocol_sha256'] == protocol_sha and result['sample_idx'] == i
                else:
                    path = Path(row['image'])
                    if not path.is_absolute():
                        path = base / 'data_image' / path
                    with Image.open(path) as im:
                        image = im.convert('RGB').copy()
                    prompt = str(row['src']) + ' The answer is:'
                    with torch.no_grad():
                        p, v = runner.trace_one(prompt, image, None)
                    assert all(len(a) == cfg.num_layers and np.isfinite(a).all() for a in list(p.values()) + list(v.values()))
                    result = dict(sample_idx=i, sample_id=row.get('case_id', row.get('id', i)), prompt=prompt,
                                  image=str(path), image_sha256=sha(path), protocol_sha256=protocol_sha,
                                  target_id=runner.last_target_id, target_token=tokenizer.decode([runner.last_target_id]), p=p, v=v)
                    write(sample, result)
                records.append(result)
            except Exception:
                error = dict(sample_idx=i, error=traceback.format_exc(), time=now())
                errors.append(error)
                write(out / 'failures' / ('%06d.json' % i), error)
                print(json.dumps(error), flush=True)
                if hasattr(runner, 'pt') and hasattr(runner.pt, 'td'):
                    del runner.pt.td
                torch.cuda.empty_cache()
                # A repeated loader/input error must be repaired, not repeated hundreds of times.
                if len(errors) >= 3:
                    break
            if (i + 1) % 10 == 0 or i + 1 == len(raw):
                progress = dict(time=now(), dataset='mmke-' + dataset, model=args.model, completed=len(records), total=len(raw),
                                failed=len(errors), elapsed_seconds=time.time()-start, state='RUNNING')
                write(out / 'progress.json', progress)
                print(json.dumps(progress), flush=True)
        if len(records) != len(raw):
            failures.append(dataset)
            write(out / 'progress.json', dict(state='INCOMPLETE', completed=len(records), total=len(raw), failed=len(errors), time=now()))
            continue
        rows, variants = aggregate(records, cfg.num_layers, source)
        ps = {k: np.array([r['p'][k] for r in records]) for k in ['layer', 'att', 'mlp']}
        vs = {k: np.array([r['v'][k] for r in records]) for k in ps}
        a, m = ref.signed_contribution(vs, ps)
        assert np.allclose(a.mean(0), [r['attn_mean'] for r in rows], rtol=0, atol=1e-15)
        assert np.allclose(m.mean(0), [r['mlp_mean'] for r in rows], rtol=0, atol=1e-15)
        with (out / 'contribution_layer.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        write(out / 'recommendations.json', variants)
        write(out / 'summary.json', dict(state='DONE', time=now(), dataset='mmke-' + dataset, model=args.model,
                                        completed=len(records), total=len(raw), failed=0, protocol_sha256=protocol_sha,
                                        contribution_sha256=sha(out/'contribution_layer.csv'), recommendation_sha256=sha(out/'recommendations.json'),
                                        original_formula_parity=True, elapsed_seconds=time.time()-start,
                                        sample_files={p.name: sha(p) for p in sorted((out/'samples').glob('*.json'))}))
        print('DONE', dataset, args.model, len(records), flush=True)
    if failures:
        raise RuntimeError('Incomplete datasets: ' + ', '.join(failures))


if __name__ == '__main__':
    main()
