"""Read-only compact progress snapshot for the two-group repair."""
import json
from pathlib import Path
import sys
from lga_ablation_remote import ssh,BASE
from run_visedit_model_pred_mmke_20260929 import write

sys.stdout.reconfigure(encoding='utf-8')
code='''
from pathlib import Path
import json,datetime
s=Path(%r)/'server_results'
r=s/'visedit_model_pred_mmke_20260929/qwen_repair_bf16_v2'
result=dict(time=datetime.datetime.now().astimezone().isoformat(),repair=json.loads((r/'control/status.json').read_text()),groups=[],diagnostics={})
for dtype in ['float16','bfloat16']:
 records=[json.loads(p.read_text()) for p in (r/'diagnostics').glob(dtype+'_*.json')]
 result['diagnostics'][dtype]=dict(checked=len(records),finite=sum(v['finite'] for v in records))
for ds in ['mmke-visual','mmke-entity']:
 folder=r/'results'/ds/'qwen2.5-vl-3b'
 p=folder/'summary.json'
 if not p.exists():p=folder/'progress.json'
 if p.exists():
  group={k:v for k,v in json.loads(p.read_text()).items() if k!='sample_files'}
  group['saved_sample_files']=len(list((folder/'samples').glob('*.json')))
  group['failure_files']=len(list((folder/'failures').glob('*.json')))
  result['groups'].append(group)
o=s/'ours_visual10_20260929'
q=json.loads((o/'control/status.json').read_text())
p=o/'raw/visual'/q.get('dataset','')/q.get('model','')/'progress.json'
result['other_queue']=dict(state=q['state'],model=q.get('model'),dataset=q.get('dataset'))
if p.exists():result['other_queue']['progress']=json.loads(p.read_text())
print(json.dumps(result))
'''%BASE
result=json.loads(ssh(code,timeout=60))
write(Path(__file__).resolve().parents[1]/'outputs/visedit_model_pred_mmke_20260929/qwen_repair/latest_progress.json',result)
compact=dict(time=result['time'],repair_state=result['repair']['state'],
             groups=[{k:g[k] for k in ['dataset','state','completed','total','saved_sample_files','failure_files'] if k in g} for g in result['groups']],
             diagnostics=result['diagnostics'])
if not result['groups']:compact['other_queue']=result['other_queue']
print(json.dumps(compact,ensure_ascii=False))
