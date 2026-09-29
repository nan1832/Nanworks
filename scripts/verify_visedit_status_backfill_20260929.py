"""Validate the completed status backfill against local per-group receipts."""
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'outputs/visedit_model_pred_mmke_20260929'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    status = load(BASE/'sync_status.json')
    assert len(status['verified_complete_groups']) == 12
    groups = [g for g in status['groups'] if g['state'] == 'DONE']
    assert len(groups) == 12
    for group in groups:
        folder = BASE/'results'/group['dataset']/group['model']
        summary, verified = load(folder/'summary.json'), load(folder/'local_verification.json')
        assert verified['passed'] and verified['summary_sha256'] == sha(folder/'summary.json')
        assert verified['samples_verified'] == summary['total'] == summary['completed']
        assert len(verified['variants_verified']) == 3
    doc = ROOT/'md/Location/ALL_Methods_Recommends_layers.md'
    main = ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
    text = doc.read_text(encoding='utf-8')
    assert '已核验回填 12/14 组' in text
    assert '205/214' in text and '20/636' in text
    rows = load(ROOT/'outputs/all_methods_recommendations_20260928/visedit_full_rankings.json')
    complete = [r for r in rows if r['target']=='model_pred' and r['dataset'].startswith('mmke') and r['status']=='done' and not r['historical']]
    assert len(complete) == 36 and all(r['attribution_scope']=='next_token_argmax' for r in complete)
    assert not any(r['model']=='qwen2.5-vl-3b' for r in complete)
    before = (BASE/'status_check_20260929'/doc.name).read_text(encoding='utf-8')
    for start,end in [('## 1. 中层先验','## 6. VisEdit'),('## 7. Ours','## 附录 B.')]:
        a=before.split(start,1)[1].split(end,1)[0]
        b=text.split(start,1)[1].split(end,1)[0]
        def normalize(value):
            # Concurrent Ours work refreshed only its timestamp and manifest link;
            # the observed two-line diff is retained in status_check_20260929.
            value=re.sub(r'结果核验时间：\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+0800', '结果核验时间：<timestamp>', value)
            value=re.sub(r'ours_visual10_20260929/snapshots/[0-9a-f]+/manifest.json', 'ours_visual10_20260929/snapshots/<snapshot>/manifest.json', value)
            return re.sub(r'\n\s*\n','\n\n',value)
        assert normalize(a) == normalize(b), start
    boundary = '## 3. 数据集分表'.encode()
    assert (BASE/'status_check_20260929'/main.name).read_bytes().split(boundary,1)[1] == main.read_bytes().split(boundary,1)[1]
    receipt = dict(verified_groups=12,module_variants=36,attribution_scope='next_token_argmax',full_response_attribution_completed=False,
                   unrelated_method_sections_preserved=True,real_editing_ledger_preserved=True,
                   concurrent_ours_reference_refresh_only=True,
                   checked_at=datetime.now().astimezone().isoformat(),documents={str(p.relative_to(ROOT)):sha(p) for p in [doc,main]})
    (BASE/'backfill_verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    finalizer = dict(state='NEEDS_REPAIR',completed_groups=12,total_groups=14,local_backfill_verified=True,
                     attribution_scope='next_token_argmax',full_response_attribution_completed=False,
                     time=receipt['checked_at'],server_finished_at=status['worker']['time'],
                     reason='Qwen nonfinite output; stale SSH finalizer replaced by direct verified backfill.')
    (BASE/'finalizer_status.json').write_text(json.dumps(finalizer,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    main()
