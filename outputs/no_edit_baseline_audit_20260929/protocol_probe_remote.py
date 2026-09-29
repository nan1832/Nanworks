import datetime,hashlib,json,os,subprocess
from pathlib import Path
B=Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2")
P=B/"VisEdit-main";S=B/"server_results"
out=dict(time=datetime.datetime.now().astimezone().isoformat(),sources={},controls={},lists={})
for relative in ["scripts/run_mmke_minigpt_llava_lowmem_sweep.py",
                 "scripts/run_mmke_llava_shared_gpu_sweep.py",
                 "scripts/eval_evqa_no_edit_full_alt.py",
                 "scripts/eval_mmke_no_edit_alt_7models.py",
                 "dataset/vllm.py","utils/__init__.py","utils/GLOBAL.py",
                 "editor/vllms_for_edit/instructblip.py",
                 "editor/vllms_for_edit/paligemma.py"]:
    p=P/relative
    if p.exists():
        b=p.read_bytes();out["sources"][str(p)]=dict(sha256=hashlib.sha256(b).hexdigest(),text=b.decode())
root=S/"ours_visual10_20260929"
for name in ["code","control"]:
    d=root/name
    if not d.exists():continue
    out["lists"][str(d)]=[p.name for p in d.iterdir()]
    for p in d.iterdir():
        if p.suffix==".py":
            out["sources"][str(p)]=dict(text=p.read_text())
        elif p.suffix==".json" and p.stat().st_size<100000:
            out["controls"][str(p)]=json.loads(p.read_text())
for rel in ["server_results/gpu_locks/g08_gpu0.lock",
            "datasets/MMKE-Bench/data_json/entity_eval.json",
            "datasets/MMKE-Bench/data_json/visual_eval.json"]:
    p=B/rel
    if p.exists():
        entry=dict(size=p.stat().st_size,inode=p.stat().st_ino)
        if p.suffix==".json":
            data=json.loads(p.read_text());entry.update(count=len(data),first=data[0])
        out["lists"][str(p)]=entry
print(json.dumps(out))
