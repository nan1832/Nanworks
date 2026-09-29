from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'no_edit_baseline_audit_20260929'))
from remote import ssh
code=r"""
from pathlib import Path
import json,re,datetime
r=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/memory_calibration_20260929')
out={'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
for name,path in [('status',r/'priority_pause/status.json'),('gate',r/'measured_gate.json'),('outcome',r/'priority_pause/profile_outcome.json'),('resume',r/'priority_pause/resume_launch.json')]:
 if path.exists():out[name]=json.loads(path.read_text())
for layer in [20,17]:
 p=r/('layer_%02d'%layer)
 info={}
 for name in ['accepted_probe.json','failed.json','probe_report.json']:
  if (p/name).exists():info[name]=json.loads((p/name).read_text())
 log=p/'probe.log'
 if log.exists():
  with log.open('rb') as f:
   f.seek(max(0,log.stat().st_size-12000));raw=f.read().decode('utf-8','replace')
  lines=[x for x in re.split(r'[\r\n]+',raw) if x.strip()]
  info['log_tail']=lines[-4:]
  info['log_mtime']=datetime.datetime.fromtimestamp(log.stat().st_mtime,datetime.timezone(datetime.timedelta(hours=8))).isoformat()
 if info:out[str(layer)]=info
log=r/'priority_pause/resume_L8_epoch41.log'
if log.exists():
 with log.open('rb') as f:
  f.seek(max(0,log.stat().st_size-8000));raw=f.read().decode('utf-8','replace')
 out['resume_log_tail']=[x for x in re.split(r'[\r\n]+',raw) if x.strip()][-5:]
print(json.dumps(out,ensure_ascii=False,indent=2))
"""
result=ssh(code)
Path(__file__).with_name('latest_status.json').write_text(result,encoding='utf-8')
data=json.loads(result)
def compact(x):
    if isinstance(x,dict):return {k:compact(v) for k,v in x.items() if k not in ['formal_command','command']}
    if isinstance(x,list):return [compact(v) for v in x]
    if isinstance(x,str):return x.replace(chr(0),'')
    return x
print(json.dumps(compact(data),ensure_ascii=False,indent=2))
