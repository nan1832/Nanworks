import json, pathlib
r=pathlib.Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
out={}
for p in (r/'tmp_archives_20260810'/'g09').glob('paligemma*/ARCHIVE_MANIFEST.txt'):
    out[str(p)]=p.read_text(errors='replace')
p=r/'tmp_archives_20260810'/'g09'/'archive_audit.tsv'
out[str(p)]=p.read_text(errors='replace') if p.exists() else None
for p in r.glob('paligemma_after_visual_stable_followup*'):
    if p.is_dir():
        for f in p.iterdir():
            if f.is_file() and f.stat().st_size<200000:
                out[str(f)]=f.read_text(errors='replace')
print(json.dumps(out,ensure_ascii=False))
