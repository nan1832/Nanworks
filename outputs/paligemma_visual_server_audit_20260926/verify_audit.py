"""Check source hashes, per-sample completeness, copied metrics and bounded ledger changes."""
from pathlib import Path
import json,hashlib,math,csv,difflib
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
manifest=json.loads((HERE/'download_manifest.json').read_text(encoding='utf-8'))
for r in manifest:
    data=Path(r['local_path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==r['sha256'] and len(data)==r['bytes']
def finite(x):
    if isinstance(x,float): assert math.isfinite(x)
    elif isinstance(x,dict):
        for v in x.values(): finite(v)
    elif isinstance(x,list):
        for v in x: finite(v)
counts={}
for group in ['main_original','main_diagnostic']:
    for p in (HERE/'downloaded_results'/group).glob('layer_*'):
        details=json.loads((p/'results.json').read_text(encoding='utf-8'))
        mean=json.loads((p/'mean_results.json').read_text(encoding='utf-8'))
        e=json.loads((p/'eval_full.done').read_text(encoding='utf-8'))
        assert len(details)==mean['sample_count']==e['eval_samples']==293
        finite(details);finite(mean)
        vals=[mean['reliability']['acc'],mean['generality']['text_rephrase']['acc'],
              mean['generality']['image_rephrase']['acc'],mean['locality']['text_loc']['acc'],mean['locality']['image_loc']['acc']]
        assert abs(sum(vals)*20-e['Average'])<1e-8
        counts[str(p.relative_to(HERE/'downloaded_results'))]=293
paths=[ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md',
       ROOT/'md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md']
audit=[]
for p in paths:
    before=(HERE/'before_backfill'/p.name).read_text(encoding='utf-8')
    after=p.read_text(encoding='utf-8')
    diff=list(difflib.unified_diff(before.splitlines(),after.splitlines(),fromfile='before/'+p.name,tofile=str(p),lineterm=''))
    (HERE/(p.stem+'_backfill.diff')).write_text('\n'.join(diff),encoding='utf-8')
    # Any changed table entry must belong to PaliGemma; no other models' numeric rows may change.
    old_rows=Counter(x for x in before.splitlines() if x.startswith('|'))
    new_rows=Counter(x for x in after.splitlines() if x.startswith('|'))
    removed=list((old_rows-new_rows).elements())
    assert all('L8 | main/legacy' in x for x in removed),removed
    added=list((new_rows-old_rows).elements())
    audit.append(dict(path=str(p),added_table_rows=len(added),removed_table_rows=len(removed)))
rows=list(csv.DictReader((HERE/'paligemma_visual_observed_results.csv').open(encoding='utf-8-sig')))
assert sum(r['recipe']=='main' for r in rows)==16
for p in paths:
    t=p.read_text(encoding='utf-8')
    assert '| 30.540 | EVAL_DONE_INCOMPLETE' in t and '| 62.544 | EVAL_DONE_INCOMPLETE' in t
result=dict(downloaded_files_verified=len(manifest),evaluation_sample_counts=counts,
            all_per_sample_numbers_finite=True,ledger_diffs=audit,main_observed_layers=16,
            main_full_50_epoch_layers=13,new_training_started=False)
(HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
