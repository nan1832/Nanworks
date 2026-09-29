"""Read-only retrieval of archived MMKE KeyToken layer scores, no GPU jobs."""
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
REMOTE = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_keytoken_mmke_7models_job3044841_20260704_192247/full"
MODELS = ["blip2-opt-2.7b", "instructblip-vicuna-7b", "minigpt-4-vicuna-7b", "llava-v1.5-7b", "qwen2.5-vl-3b", "paligemma-3b", "smolvlm-1.7b"]
FILES = ["layer_scores.csv", "config.json", "summary.json", "high_contribution_region.json"]
script = """
import os,json,base64,hashlib
root=ROOT_VALUE
models=MODELS_VALUE
names=FILES_VALUE
result=[]
for ds in ['mmke-visual','mmke-entity']:
 for model in models:
  for name in names:
   rel='/'.join([ds,model,name]);path=os.path.join(root,rel)
   with open(path,'rb') as f:data=f.read()
   result.append({'relative_path':rel,'remote_path':path,'sha256':hashlib.sha256(data).hexdigest(),'data':base64.b64encode(data).decode('ascii')})
print(json.dumps(result))
""".replace("ROOT_VALUE", repr(REMOTE)).replace("MODELS_VALUE", repr(MODELS)).replace("FILES_VALUE", repr(FILES))
args = ["C:/Windows/System32/OpenSSH/ssh.exe", "-i", str(Path.home()/".ssh/id_ed25519_bridge"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "ph_teacher3@10.68.162.201", "/usr/bin/python3", "-"]
proc = subprocess.run(args, input=script, capture_output=True, encoding="utf-8", timeout=60, check=True)
files = json.loads(proc.stdout)
assert len(files) == 56
manifest = []
for row in files:
    data = base64.b64decode(row.pop("data"))
    assert hashlib.sha256(data).hexdigest() == row["sha256"]
    dest = OUT / "raw" / row["relative_path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        assert dest.read_bytes() == data, "Existing raw archive differs"
    else:
        dest.write_bytes(data)
    manifest.append(row)
(OUT / "source_manifest.json").write_text(json.dumps({"date":"2026-09-27", "source":REMOTE, "operation":"read-only archive fetch", "files":manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"downloaded_files":len(manifest),"groups":14,"example_config":json.loads((OUT/"raw/mmke-visual/blip2-opt-2.7b/config.json").read_text(encoding="utf-8")),"example_summary":json.loads((OUT/"raw/mmke-visual/blip2-opt-2.7b/summary.json").read_text(encoding="utf-8"))},ensure_ascii=False,indent=2))
