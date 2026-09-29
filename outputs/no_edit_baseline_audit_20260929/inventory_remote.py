import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

B=Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2")
S=B/"server_results"
def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     universal_newlines=True,timeout=30)
    return dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
out=dict(time=datetime.datetime.now().astimezone().isoformat(),
         host=os.uname()[1],jobs=run(["squeue","-u","ph_teacher3","-o","%i %j %T %M %l %R %b"]),
         baselines=[],control={})
for name in ["no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148",
             "no_edit_mmke_alt_eval_7models_20260612_161034"]:
    root=S/name
    item=dict(path=str(root),exists=root.exists(),files=[])
    if root.exists():
        for p in sorted(root.rglob("*.json")):
            if p.name not in ["no_edit_metrics.json","mean_results.json","run_config.json",
                              "no_edit_results.json","results.json"]:
                continue
            v=json.loads(p.read_text())
            r=dict(path=str(p),bytes=p.stat().st_size,
                   sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            if isinstance(v,list):
                r.update(count=len(v),first=v[0] if v else None)
            else:r["data"]=v
            item["files"].append(r)
    out["baselines"].append(item)
for rel in ["visedit_model_pred_mmke_20260929/control/status.json",
            "visedit_model_pred_mmke_20260929/qwen_repair_bf16_v2/control/status.json",
            "lga_two_spaces_ablation_20260928/control/g08_status.json",
            "lga_two_spaces_ablation_20260928/control/g09_status.json",
            "visual_track_cosine_20260928/priority_switch/status.json",
            "tukey_top3_two_gpu_20260926/control/g08/status.json"]:
    p=S/rel
    if p.exists():out["control"][rel]=json.loads(p.read_text())
print(json.dumps(out,ensure_ascii=True))
