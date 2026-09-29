"""Read-only disk and progress inventory, limited to this project's experiment roots."""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,statistics,socket
R=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
T=Path('/tmp/ph_teacher3')
role='job3150065' if socket.gethostname()=='g08' else 'job3126082'
base=T/('formal_top3_stage2_'+role+'_20260812')
shared=R/'server_results/formal_top3_stage2_20260812'/role
def run(args,timeout=90):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=timeout)
  return {'rc':p.returncode,'output':p.stdout}
 except subprocess.TimeoutExpired:return {'timeout':timeout}
def du(p):
 if not p.exists():return 0
 a=run(['du','-sx','-B1',str(p)])
 return int(a['output'].split()[0]) if a.get('rc')==0 else a
def tail(p,n=8):
 if not p.is_file():return None
 return run(['tail','-n',str(n),str(p)])['output']
out={'node':socket.gethostname(),'time':datetime.datetime.now().astimezone().isoformat(),'df':run(['df','-B1','/tmp',str(R)]),
 'tmp_top':run(['du','-x','-B1','--max-depth=1',str(T)]),'roots':[],'processes':[]}
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  cwd=os.readlink(proc/'cwd')
  if not cwd.startswith(str(R)) or not any(k in cmd for k in ['scripts/','sync_completed','launch_formal']):continue
  if ' -c ' in cmd:continue
  out['processes'].append({'pid':int(proc.name),'cmd':cmd,'cwd':cwd,'stdout':os.readlink(proc/'fd/1'),'cgroup':(proc/'cgroup').read_text(),
    'parent':next(l for l in (proc/'status').read_text().splitlines() if l.startswith('PPid:'))})
 except OSError:pass
# Known experiment names; skip cache/weights when finding marker-bearing layer directories.
for root in T.iterdir():
 if not root.is_dir() or root.is_symlink():continue
 if not root.name.startswith(('formal_top3_stage2_','cma_modelpred_','mmke_','evqa_','mabscos_')):continue
 item={'path':str(root),'disk_bytes':du(root),'layers':[]}
 for parent,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in ['cache','records','eval_full','eval_cache','images','data']]
  p=Path(parent)
  if not re.fullmatch(r'layer_\d+',p.name):continue
  dirs[:]=[]
  row={'path':str(p),'disk_bytes':du(p),'children':{q.name:du(q) for q in p.iterdir()},
    'train_done':(p/'train.done').is_file(),'eval_done':(p/'eval_full.done').is_file()}
  sel=p/'selected_checkpoint.tsv'
  if sel.is_file():
   rows=list(csv.DictReader(sel.open(),delimiter='\t'))
   row['selected']=rows[-1] if rows else None
   if rows:row['checkpoint_exists']=Path(rows[-1]['checkpoint']).is_file()
  if row['eval_done']:
   row['eval']=json.loads((p/'eval_full.done').read_text())
   row['results']=[{'path':str(f),'bytes':f.stat().st_size} for f in (p/'eval_full').rglob('results.json')]
  if root==base:
   dest=shared/p.relative_to(base)
   row['shared_path']=str(dest);row['shared_exists']=dest.exists();row['shared_sync']=(dest/'SYNC_VERIFIED').is_file()
  item['layers'].append(row)
 out['roots'].append(item)
out['queue_tail']=tail(base/'queue.status.log',5)
if role=='job3150065':
 combo=base/'evqa-pilot500/llava-v1.5-7b'
 out['cache_dirs']={str(p):du(p) for p in (combo/'cache').glob('*')}
 out['eval_cache_bytes']=du(combo/'eval_cache')
 out['L25_logs']=[{'path':str(p),'bytes':p.stat().st_size} for p in (base/'logs').glob('evqa-pilot500_llava-v1.5-7b_L25_*')]
 p=combo/'layer_00/loss_history.csv';rows=list(csv.DictReader(p.open()))
 epochs=[{'epoch':int(r['epoch']),'time':r['time'],'step':int(r['i'])} for r in rows]
 intervals=[(datetime.datetime.strptime(b['time'],'%Y-%m-%d %H:%M:%S')-datetime.datetime.strptime(a['time'],'%Y-%m-%d %H:%M:%S')).total_seconds()/3600 for a,b in zip(epochs,epochs[1:]) if b['epoch']==a['epoch']+1]
 out['L0_history']={'last':epochs[-1],'last_10':epochs[-10:],'last_5_epoch_hours':intervals[-5:],'median_last_5_hours':statistics.median(intervals[-5:])}
 log=next(p for p in out['processes'] if '--layers 0 ' in p['cmd'])['stdout']
 f=Path(log)
 with f.open('rb') as h:h.seek(max(0,f.stat().st_size-8000));lines=h.read().decode(errors='replace').replace('\r','\n').splitlines()
 out['L0_log']={'path':log,'mtime':f.stat().st_mtime,'tail':lines[-5:]}
 out['model_root_files']=[{'path':str(p),'bytes':p.stat().st_size} for p in combo.iterdir() if p.is_file()]
print(json.dumps(out))
