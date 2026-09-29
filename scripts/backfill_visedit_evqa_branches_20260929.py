"""Backfill EVQA VisEdit branches from existing, server-verified layer scores."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/visedit_evqa_backfill_20260929'
SERVER_CHECKED_AT = '2026-09-29T20:03:47.407516+08:00'
# SHA-256 values read through SSH from the seven server layer tables.
SERVER_SHA256 = {
    'blip2-opt-2.7b': 'b344297cc95204ca75fc230387e18344e1bd18abf65190f5534441dc3adf8fb1',
    'instructblip-vicuna-7b': 'fe2b6035e29a13820b9d22faf20efab6a39dcda09c8a77de56c40fe69c200920',
    'minigpt-4-vicuna-7b': 'e1ce85b85c5d6f01667926fa3f32f6c0e255bfe502c8afd36659b3a0f10b6c95',
    'llava-v1.5-7b': 'bcc03f825c3b233e1e6a04202043febd2316f89dbd5271b04f290b96d6083faf',
    'qwen2.5-vl-3b': 'e5c428f54371a27e8ef1805b3d101468d7bbf8ed0ecdce4c28960ae746f13419',
    'paligemma-3b': '63055b0354ecfb87dc9a54e38b2e4c1c502e65098e4018f8066454f5feb2a836',
    'smolvlm-1.7b': '28446a19761dc33b8bb9853d298c94725eea48dc559679a50fc087f8a3027e58',
}


def main():
    source = ROOT / 'scripts/build_all_method_recommendations.py'
    spec = importlib.util.spec_from_file_location('builder', source)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    tree = ast.parse(source.read_text(encoding='utf-8-sig'))
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    canonical = ROOT / 'VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py'
    ns = {'np': np}
    rules = [n for n in ast.parse(canonical.read_text(encoding='utf-8-sig')).body
             if isinstance(n, ast.FunctionDef) and n.name in {'moving_average', 'find_high_region', 'pre_candidates'}]
    assert len(rules) == 3
    exec(compile(ast.Module(body=rules, type_ignores=[]), str(canonical), 'exec'), ns)
    derive = next(n for n in funcs['visedit_sources'].body if isinstance(n, ast.FunctionDef) and n.name == 'derive')
    ctx = dict(vars(builder), ns=ns)
    exec(compile(ast.Module(body=[derive], type_ignores=[]), str(source), 'exec'), ctx)

    old_vis = builder.rjson(builder.OUT / 'visedit_full_rankings.json')
    evqa = [v for v in old_vis if v['dataset'] == 'evqa-pilot500' and v['target'] == 'model_pred'
            and v.get('module') == 'attn+mlp' and not v['historical']]
    assert len(evqa) == 7 and {v['model'] for v in evqa} == set(builder.MODELS)
    evidence = []
    for v in evqa:
        model, path = v['model'], ROOT / v['source']
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha == SERVER_SHA256[model], model
        config, summary = builder.rjson(path.with_name('config.json')), builder.rjson(path.with_name('summary.json'))
        assert config['key_mode'] == summary['key_mode'] == 'model_pred'
        assert config['sample_count'] == summary['sample_count'] == 500
        rows = builder.rcsv(path)
        assert all(math.isfinite(float(r[k])) for r in rows for k in ['attn_mean', 'mlp_mean', 'score_positive'])
        for module in ['attn+mlp', 'attn', 'mlp']:
            ctx['derive']('evqa-pilot500', model, 'model_pred', path, v['token_rule'],
                          builder.ls(v['top3']) if module == 'attn+mlp' else None, module=module)
            new = builder.VIS[-1]
            assert len(new['top3']) == len(set(new['top3'])) == 3
            assert set(new['contribution_ranking']) == set(range(builder.MODELS[model][1]))
            if module == 'attn+mlp':
                for field in ['top3', 'high_region', 'contribution_ranking', 'contribution_scores']:
                    assert new[field] == v[field], (model, field)
                assert math.isclose(new['threshold'], v['threshold'], abs_tol=1e-12)
        evidence.append(dict(model=model, local_source=v['source'], server_source=summary['outputs']['layer_csv'],
                             sha256=sha, sample_count=500, layers=len(rows)))
        print('verified', model, flush=True)

    additions = [v for v in builder.VIS if v['module'] != 'attn+mlp']
    assert len(additions) == 14
    vis_key = lambda v: (v['dataset'], v['model'], v['target'], v.get('module', 'attn+mlp'), v['historical'])
    addition_keys = {vis_key(v) for v in additions}
    combined = [v for v in old_vis if vis_key(v) not in addition_keys] + additions
    current = [v for v in combined if v['target'] == 'model_pred' and not v['historical'] and v['status'] == 'done']
    expected = {(d, m, module) for d in builder.DATASETS for m in builder.MODELS for module in ['attn', 'mlp', 'attn+mlp']}
    assert len(current) == 63 and {(v['dataset'], v['model'], v['module']) for v in current} == expected

    # Render the same tables as the corrected full builder, without rebuilding other methods.
    table_loop = next(n for n in funcs['make_document'].body if isinstance(n, ast.For)
                      and isinstance(n.target, ast.Name) and n.target.id == 'ds' and 'contribution_ranking' in ast.unparse(n))
    render = dict(vars(builder), VIS=combined, lines=[])
    exec(compile(ast.Module(body=[table_loop], type_ignores=[]), str(source), 'exec'), render)
    tables = '\n'.join(render['lines']) + '\n'
    strings = [n.value for n in ast.walk(funcs['make_document']) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    joined = [n for n in ast.walk(funcs['make_document']) if isinstance(n, ast.JoinedStr)]

    def literal(prefix):
        return next(s for s in strings if s.startswith(prefix))

    def formatted(prefix):
        node = next(n for n in joined if n.values and isinstance(n.values[0], ast.Constant)
                    and str(n.values[0].value).startswith(prefix))
        return eval(compile(ast.Expression(body=node), str(source), 'eval'), {'vis_done': 14})

    original_bytes = builder.DOC.read_bytes()
    original = original_bytes.decode('utf-8-sig')
    document = original
    replacements = [
        (r'^\*\*(?:定义更正|当前 VisEdit 口径).*$', literal('**当前 VisEdit 口径')),
        (r'^\*\*2026-09-29 (?:MMKE 首预测位置对照|关键 token 归因).*$', formatted('**2026-09-29 关键 token 归因')),
        (r'^单模块排名与 Pre 使用.*$', literal('单模块排名与 Pre 使用')),
        (r'^- VisEdit-model_pred-NextTokenArgmax：.*$', formatted('- VisEdit-model_pred-NextTokenArgmax：')),
    ]
    for pattern, replacement in replacements:
        document, count = re.subn(pattern, lambda _: replacement, document, flags=re.M)
        assert count == 1, pattern
    start, end = document.index('### 6.1 '), document.index('## 7. ')
    document = document[:start] + tables + document[end:]
    old_evqa_note = r'^EVQA 单模块回填核验：.*\n\n'
    document = re.sub(old_evqa_note, '', document, flags=re.M)
    note = ('EVQA 单模块回填核验：服务器于北京时间 2026-09-29 20:03 核验七份层表，本地 SHA-256 全部一致；'
            '每组摘要记录 500 个样本。新增 attn、MLP 共 14 行，联合分支推荐保持一致。'
            '见[回填与覆盖核验](../../outputs/visedit_evqa_backfill_20260929/verification.json)。\n\n')
    heading = '### 6.1 EVQA-pilot500\n\n'
    assert document.count(heading) == 1
    document = document.replace(heading, heading + note)
    assert original.split('## 6. ')[0] == document.split('## 6. ')[0]
    protected = lambda s: s[s.index('## 7. '):s.index('## 附录 B.')]
    assert protected(original) == protected(document)
    mmke = lambda s: [line for line in s[s.index('### 6.2 '):s.index('## 7. ')].splitlines() if line.startswith('|')]
    assert mmke(original) == mmke(document)
    for ds in builder.DATASETS:
        rows = [v for v in current if v['dataset'] == ds]
        assert len(rows) == 21
        for v in rows:
            assert len(v['top3']) == 3 and set(v['top3']) <= set(range(builder.MODELS[v['model']][1]))

    rec_path = builder.OUT / 'recommendations.json'
    rec_doc = builder.rjson(rec_path)
    rec_key = lambda r: (r['method'], r['dataset'], r['model'], r['flavor'])
    add_recs = [r for r in builder.RECS if r['module'] != 'attn+mlp']
    add_rec_keys = {rec_key(r) for r in add_recs}
    old_recs = rec_doc['records']
    rec_doc['records'] = [r for r in old_recs if rec_key(r) not in add_rec_keys] + add_recs
    assert len({rec_key(r) for r in rec_doc['records']}) == len(rec_doc['records'])
    score_path = builder.OUT / 'all_layer_scores.csv'
    old_scores = builder.rcsv(score_path)
    add_scores = [r for r in builder.SCORES if r['module'] != 'attn+mlp']
    score_group = lambda r: (r['method'], r['dataset'], r['model'], r['flavor'])
    added_groups = {score_group(r) for r in add_scores}
    scores = [r for r in old_scores if score_group(r) not in added_groups] + add_scores
    assert len(add_scores) == 412
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    rec_doc['updated_at'] = stamp
    inputs_path = builder.OUT / 'input_sha256.json'
    inputs = builder.rjson(inputs_path)
    inputs.update({k: v for k, v in builder.SOURCES.items() if k.startswith('downloads/')})
    inputs[source.relative_to(ROOT).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    inputs[canonical.relative_to(ROOT).as_posix()] = hashlib.sha256(canonical.read_bytes()).hexdigest()
    assert builder.DOC.read_bytes() == original_bytes, 'Main table changed during backfill; retry with latest file'
    OUT.mkdir(parents=True, exist_ok=True)
    backups = OUT / 'backups'
    backups.mkdir(exist_ok=True)
    targets = [builder.DOC, rec_path, builder.OUT / 'recommendations.csv', score_path,
               builder.OUT / 'visedit_full_rankings.json', inputs_path]
    for path in targets:
        backup = backups / path.name
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    builder.writejson(builder.OUT / 'visedit_full_rankings.json', combined)
    builder.writejson(rec_path, rec_doc)
    builder.writecsv(builder.OUT / 'recommendations.csv', rec_doc['records'])
    builder.writecsv(score_path, scores)
    builder.writejson(inputs_path, inputs)
    builder.DOC.write_bytes(document.encode('utf-8'))
    verification = dict(updated_at=stamp, server_checked_at=SERVER_CHECKED_AT, passed=True,
                        target='model_pred-NextTokenArgmax', server_sources=evidence,
                        evqa_added_branch_records=14, evqa_added_layer_scores=412,
                        model_pred_combinations=21, model_pred_branch_records=63,
                        coverage_by_module=dict(Counter(v['module'] for v in current)),
                        evqa_joint_results_unchanged=True, mmke_table_rows_unchanged=True,
                        other_methods_and_sections_7_through_A_unchanged=True,
                        protected_section_sha256=hashlib.sha256(protected(document).encode()).hexdigest(),
                        no_model_execution=True, no_server_mutation=True,
                        document_before_sha256=hashlib.sha256(original_bytes).hexdigest(),
                        output_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets})
    builder.writejson(OUT / 'verification.json', verification)
    builder.writejson(OUT / 'evqa_branch_recommendations.json', builder.VIS)
    print(json.dumps({k: v for k, v in verification.items() if k not in {'server_sources', 'output_sha256'}}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
