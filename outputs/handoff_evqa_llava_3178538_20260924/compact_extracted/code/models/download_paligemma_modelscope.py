import json
from pathlib import Path
from modelscope.hub.snapshot_download import snapshot_download

model_id = 'AI-ModelScope/paligemma-3b-mix-224'
local_dir = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/models/paligemma-3b-mix-224-modelscope')
local_dir.mkdir(parents=True, exist_ok=True)
print(json.dumps({'model_id': model_id, 'local_dir': str(local_dir)}, ensure_ascii=False), flush=True)
path = snapshot_download(model_id, local_dir=str(local_dir))
payload = {'model_id': model_id, 'local_dir': str(local_dir), 'snapshot_path': path, 'status': 'done', 'source': 'modelscope'}
(local_dir / '.download_complete.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
