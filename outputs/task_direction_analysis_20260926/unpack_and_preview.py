from pathlib import Path
import json,base64,gzip,hashlib,csv,io,shutil
H=Path(__file__).resolve().parent;D=H/'inputs';D.mkdir(exist_ok=True)
manifest=[]
for line in (H/'source_bundle.jsonl').read_text(encoding='utf-8').splitlines():
    if not line.startswith('{'):continue
    r=json.loads(line);b=gzip.decompress(base64.b64decode(r.pop('gzip_base64')))
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert Path(r['name']).name==r['name'];(D/r['name']).write_bytes(b);manifest.append(r)
(H/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
root=H.parents[1]
for src,name in [('md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md','outcome_ledger_snapshot.md'),
                 ('outputs/visual_lga_vs_main_20260925/verified_outcomes_with_flags.csv','previous_outcomes.csv'),
                 ('outputs/paligemma_visual_server_audit_20260926/paligemma_visual_observed_results.csv','pali_main_stable_snapshot.csv')]:
    if not (D/name).exists():shutil.copy2(root/src,D/name)
for p in sorted(D.glob('*__*.json')):
    z=json.loads(p.read_text(encoding='utf-8'));rr=list(csv.DictReader(io.StringIO(z['files']['ours_direct_layer_scores.csv']['text'])))
    valid=[r for r in rr if r['S_v_zero_grad'].lower()!='true' and not r.get('invalid_reason','')]
    print(z['dataset'],z['model'],len(z['samples']),len(valid),sum(float(r['S_v_cos'])<0 for r in valid),
          round(sum(float(r['S_v_cos']) for r in valid)/len(valid),4),
          round(sum(float(r['S_v_positive_ratio']) for r in valid)/len(valid),4))
