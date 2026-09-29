"""Read-only fetch, independent local reaggregation, then backfill verified groups."""
import base64
import csv
import gzip
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import zlib
from datetime import datetime
import numpy as np
from lga_ablation_remote import ssh, BASE
from run_visedit_model_pred_mmke_20260929 import aggregate, sha, write

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'outputs/visedit_model_pred_mmke_20260929'
REMOTE = BASE + '/server_results/visedit_model_pred_mmke_20260929'


def main(verify_local=False):
    known = {str(p.parent.relative_to(LOCAL/'results')).replace('\\', '/'): sha(p)
             for p in (LOCAL/'results').glob('*/*/summary.json') if (p.parent/'local_verification.json').exists()}
    code = '''
import base64,hashlib,json,zlib,datetime
from pathlib import Path
root=Path(__ROOT__)
known=__KNOWN__
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
payload=dict(server_collected_at=datetime.datetime.now().astimezone().isoformat(),groups=[],files={})
status=root/'control/status.json'
payload['worker']=json.loads(status.read_text()) if status.exists() else {}
repair=root/'qwen_repair_bf16_v2'
if (repair/'control/status.json').exists():
 payload['original_worker']=payload['worker']
 payload['repair_worker']=json.loads((repair/'control/status.json').read_text())
 payload['worker']=payload['repair_worker']
 for name in ['diagnosis.json','control/status.json']:
  p=repair/name
  if p.exists():payload['files']['qwen_repair_bf16_v2/'+name]=base64.b64encode(p.read_bytes()).decode()
log=payload['worker'].get('log')
if log and Path(log).exists():payload['worker']['log_tail']=Path(log).read_text(errors='replace')[-2500:]
for ds,total in [('mmke-visual',214),('mmke-entity',636)]:
 for model in ['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b','qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']:
  folder=root/'results'/ds/model
  if model=='qwen2.5-vl-3b' and (repair/'results'/ds/model/'protocol.json').exists():folder=repair/'results'/ds/model
  entry=dict(dataset=ds,model=model,total=total,state='PENDING',completed=0)
  if (folder/'progress.json').exists():entry.update(json.loads((folder/'progress.json').read_text()))
  entry['saved_samples']=len(list((folder/'samples').glob('*.json')))
  if (folder/'summary.json').exists():
   summary=json.loads((folder/'summary.json').read_text())
   assert summary['state']=='DONE' and summary['total']==summary['completed']==total and summary['failed']==0
   assert sha(folder/'protocol.json')==summary['protocol_sha256']
   assert sha(folder/'contribution_layer.csv')==summary['contribution_sha256']
   assert sha(folder/'recommendations.json')==summary['recommendation_sha256']
   entry.update({k:v for k,v in summary.items() if k!='sample_files'})
   if known.get(ds+'/'+model)!=sha(folder/'summary.json'):
    for name,h in summary['sample_files'].items():
     assert Path(name).name==name and sha(folder/'samples'/name)==h
    sample_files=([folder/'samples.json.gz'] if 'sample_bundle_sha256' in summary else list((folder/'samples').glob('*.json')))
    if 'sample_bundle_sha256' in summary:assert sha(folder/'samples.json.gz')==summary['sample_bundle_sha256']
    for p in sample_files+[folder/name for name in ['protocol.json','summary.json','recommendations.json','contribution_layer.csv']]:
     payload['files']['results/'+ds+'/'+model+'/'+str(p.relative_to(folder))]=base64.b64encode(p.read_bytes()).decode()
  payload['groups'].append(entry)
print(base64.b64encode(zlib.compress(json.dumps(payload).encode(),6)).decode())
'''.replace('__ROOT__', repr(REMOTE)).replace('__KNOWN__', repr(known))
    if verify_local:
        audit = json.loads((LOCAL/'latest_status_check.json').read_text(encoding='utf-8'))
        payload = dict(server_collected_at=audit['collected_at'], worker=audit['worker'], groups=audit['groups'], files={},
                       verification_mode='local reaggregation against saved live server audit; no new server query')
    else:
        payload = json.loads(zlib.decompress(base64.b64decode(ssh(code, timeout=600).strip())))
    for name, encoded in payload.pop('files').items():
        p = (LOCAL/name).resolve()
        assert p.is_relative_to(LOCAL.resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(encoded))
    verified = []
    for group in payload['groups']:
        if group['state'] != 'DONE':
            continue
        folder = LOCAL/'results'/group['dataset']/group['model']
        summary = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        protocol = json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
        for name, field in [('protocol.json','protocol_sha256'),('contribution_layer.csv','contribution_sha256'),('recommendations.json','recommendation_sha256')]:
            assert sha(folder/name) == summary[field] == group[field]
        previous=folder/'local_verification.json'
        if previous.exists():
            receipt=json.loads(previous.read_text(encoding='utf-8'))
            if receipt.get('passed') and receipt.get('summary_sha256')==sha(folder/'summary.json') and receipt.get('samples_verified')==summary['total']:
                verified.append(group['dataset']+'/'+group['model'])
                continue
        bundle=None
        if 'sample_bundle_sha256' in summary:
            assert sha(folder/'samples.json.gz')==summary['sample_bundle_sha256']
            bundle=json.loads(gzip.decompress((folder/'samples.json.gz').read_bytes()))
            assert set(bundle)==set(summary['sample_files'])
        records = []
        for name, h in sorted(summary['sample_files'].items()):
            raw=base64.b64decode(bundle[name]) if bundle is not None else (folder/'samples'/name).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == h
            sample = json.loads(raw)
            assert sample['protocol_sha256'] == summary['protocol_sha256']
            records.append(sample)
        assert [r['sample_idx'] for r in records] == list(range(summary['total']))
        rows, variants = aggregate(records, protocol['num_layers'], LOCAL/'source_snapshot')
        stored = list(csv.DictReader((folder/'contribution_layer.csv').open()))
        for got, expected in zip(stored, rows):
            for key, value in expected.items():
                assert np.isclose(float(got[key]), value, rtol=1e-12, atol=1e-15), (key, got[key], value)
        reference = json.loads((folder/'recommendations.json').read_text(encoding='utf-8'))
        for variant in variants:
            for field in ['ranking', 'top5', 'maximum_layer', 'high_region', 'pre_top3', 'high_layers']:
                assert variants[variant][field] == reference[variant][field]
            assert np.allclose(variants[variant]['scores'], reference[variant]['scores'], rtol=1e-12, atol=1e-15)
        receipt = dict(passed=True, summary_sha256=sha(folder/'summary.json'), samples_verified=len(records),
                       variants_verified=list(variants), original_formula_parity=summary['original_formula_parity'],
                       torch_dtype=protocol['torch_dtype'],attribution_scope='next_token_argmax',
                       sample_storage='samples.json.gz' if bundle is not None else 'individual JSON',
                       checked_at=datetime.now().astimezone().isoformat())
        write(folder/'local_verification.json', receipt)
        verified.append(group['dataset']+'/'+group['model'])
    payload['verified_complete_groups'] = verified
    payload['synced_at'] = datetime.now().astimezone().isoformat()
    write(LOCAL/'sync_status.json', payload)
    backup = LOCAL/'backups'; backup.mkdir(exist_ok=True)
    for name in ['ALL_Methods_Recommends_layers.md','6location_7model_3datas_top_3_5_layers_outcome.md']:
        p=ROOT/'md/Location'/name
        if not (backup/name).exists():
            (backup/name).write_bytes(p.read_bytes())
    # Other authorized work may have advanced the ledger since the first backup.
    # Preserve the state immediately before this rebuild, not an obsolete snapshot.
    before_doc = (ROOT/'md/Location/ALL_Methods_Recommends_layers.md').read_text(encoding='utf-8')
    before_main = (ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md').read_bytes()
    result = subprocess.run([sys.executable,str(ROOT/'scripts/build_all_method_recommendations.py')],cwd=str(ROOT),
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr+result.stdout)
    doc = ROOT/'md/Location/ALL_Methods_Recommends_layers.md'
    old_doc = before_doc
    new_doc = doc.read_text(encoding='utf-8')
    for start, end in [('## 1. 中层先验', '## 6. VisEdit'), ('## 7. Ours', '## 附录 B.')]:
        old_section = old_doc.split(start,1)[1].split(end,1)[0]
        new_section = new_doc.split(start,1)[1].split(end,1)[0]
        # Existing generated VisualTrack section can add a blank line at its boundary.
        def normalize(value):
            value=re.sub(r'结果核验时间：\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+0800','结果核验时间：<timestamp>',value)
            value=re.sub(r'ours_visual10_20260929/snapshots/[0-9a-f]+/manifest.json','ours_visual10_20260929/snapshots/<snapshot>/manifest.json',value)
            return re.sub(r'\n\s*\n','\n\n',value)
        assert normalize(old_section) == normalize(new_section), start
    main = ROOT/'md/Location/6location_7model_3datas_top_3_5_layers_outcome.md'
    boundary = '## 3. 数据集分表'.encode()
    assert before_main.split(boundary,1)[1] == main.read_bytes().split(boundary,1)[1]
    receipt = dict(verified_groups=len(verified), module_variants=3*len(verified),
                   attribution_scope='next_token_argmax', full_response_attribution_completed=False,
                   unrelated_method_sections_preserved=True, real_editing_ledger_preserved=True,
                   checked_at=datetime.now().astimezone().isoformat(), documents={str(p.relative_to(ROOT)):sha(p) for p in [doc,main]})
    write(LOCAL/'backfill_verification.json', receipt)
    if len(verified) == 14:
        receipt.update(state='DONE', samples=7*(214+636), groups=verified)
        write(LOCAL/'completion_receipt.json',receipt)
    worker = {k:v for k,v in payload['worker'].items() if k not in ['command','log_tail','outcomes']}
    print(json.dumps(dict(verified_groups=len(verified),total=14,worker=worker,
                         groups=[{k:r[k] for k in ['dataset','model','state','completed','total','saved_samples']} for r in payload['groups']]), ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    # Prevent a completion callback and a manual/heartbeat sync from writing together.
    with (LOCAL/'sync.lock').open('a+b') as lock:
        if lock.tell() == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        if sys.platform == 'win32':
            import msvcrt
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                print('Another VisEdit synchronization is already running.')
                raise SystemExit(0)
        main(verify_local='--verify-local' in sys.argv)
