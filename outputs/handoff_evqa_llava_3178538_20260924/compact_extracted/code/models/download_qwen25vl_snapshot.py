from huggingface_hub import snapshot_download
from pathlib import Path

repo_id = "Qwen/Qwen2.5-VL-7B-Instruct"
local_dir = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/Qwen2.5-VL-7B-Instruct")
local_dir.mkdir(parents=True, exist_ok=True)
print(f"Downloading {repo_id} -> {local_dir}", flush=True)
path = snapshot_download(
    repo_id=repo_id,
    repo_type="model",
    local_dir=str(local_dir),
    resume_download=True,
    max_workers=2,
)
print(f"DONE {path}", flush=True)
