from pathlib import Path,PurePosixPath
import json,base64,hashlib
HERE=Path(__file__).resolve().parent
DEST=HERE/'downloaded_results'
manifest=[]
for line in (HERE/'exported_evidence.jsonl').read_text(encoding='utf-8').splitlines():
    if not line.startswith('{'): continue
    row=json.loads(line)
    if 'base64' not in row: raise RuntimeError(row)
    parts=PurePosixPath(row['relative']).parts
    if 'mmke_visual_top3_union_train_eval_7models_20260613_014644' in parts:
        layer=next(x for x in parts if x.startswith('layer_'))
        short=Path('main_original')/layer/parts[-1]
    elif 'paligemma_visual_main_nonconvergent_eval_20260926' in parts:
        layers=[x for x in parts if x.startswith('layer_')]
        short=Path('main_diagnostic')/(layers[0] if layers else 'root')/parts[-1]
    elif parts[0]=='VisEdit-main':
        short=Path('code')/parts[-1]
    else:
        short=Path('controller')/parts[-1]
    p=(DEST/short).resolve()
    assert p.is_relative_to(DEST.resolve())
    data=base64.b64decode(row.pop('base64'))
    assert len(data)==row['bytes']
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    assert str(p) not in [r['local_path'] for r in manifest], 'Short path collision'
    p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
    row['local_path']=str(p); manifest.append(row)
(HERE/'download_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(files=len(manifest),bytes=sum(r['bytes'] for r in manifest))))
for p in DEST.rglob('mean_results.json'):
    z=json.loads(p.read_text(encoding='utf-8'))
    print(str(p.relative_to(DEST)),str(z)[:600])
