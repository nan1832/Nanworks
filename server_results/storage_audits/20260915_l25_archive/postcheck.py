"""Read current progress and assess other result leftovers without deleting them."""
from pathlib import Path
import datetime,json,os,socket,subprocess,sys
A=Path('/var/tmp/ph_teacher3/cleanup_audits/20260915_l25_archive')
node=socket.gethostname();role='job3150065' if node=='g08' else 'job3126082'
root=Path('/tmp/ph_teacher3/formal_top3_stage2_'+role+'_20260812')
shared=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812')/role
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True);return {'rc':p.returncode,'output':p.stdout}
out={'node':node,'time':datetime.datetime.now().astimezone().isoformat(),'tmp_size':run(['du','-sx','-B1','/tmp/ph_teacher3']),
 'gpu':run(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu','--format=csv']),
 'queue_tail':run(['tail','-n','5',str(root/'queue.status.log')]),'verified_roots':[],'cache_breakdown':[],'remaining_results':[]}
for dataset in ['evqa-pilot500','mmke-entity','mmke-visual']:
 for base in [root/dataset,shared/dataset]:
  if not base.is_dir():continue
  output=A/(node+'_'+('shared_' if str(base).startswith(str(shared)) else 'tmp_')+dataset+'_verifier.json')
  rr=run([sys.executable,str(A/'verify_result_tree.py'),'--root',str(base),'--dataset',dataset,'--output',str(output)])
  assert rr['rc']==0,rr
  manifest=json.loads(output.read_text())
  out['verified_roots'].append({'path':str(base),'dataset':dataset,'manifest':str(output),'complete_count':manifest['complete_count'],'incomplete_count':manifest['incomplete_count'],
    'layers':[{'model':r['model'],'layer':r['layer'],'complete':r['complete'],'errors':r['errors'],'metrics':r['evaluation']} for r in manifest['layers']]})
for dataset in root.iterdir():
 if not dataset.is_dir() or dataset.name not in ['evqa-pilot500','mmke-entity','mmke-visual']:continue
 for model in dataset.iterdir():
  if not model.is_dir():continue
  for cache in (model/'cache').glob('*'):
   out['cache_breakdown'].append({'path':str(cache),'disk':run(['du','-sx','-B1',str(cache)]),
      'children':[p.name for p in list(cache.iterdir())[:8]]})
  for layer in model.glob('layer_*'):
   if (layer/'eval_full.done').is_file():
    dest=shared/layer.relative_to(root)
    out['remaining_results'].append({'path':str(layer),'disk':run(['du','-sx','-B1',str(layer)]),
      'shared_path':str(dest),'shared_sync':(dest/'SYNC_VERIFIED').is_file(),
      'selected_file_is_symlink':(layer/'selected_checkpoint.tsv').is_symlink(),
      'children':[{'name':p.name,'symlink':p.is_symlink()} for p in layer.iterdir()]})
if node=='g08':
 names=[r['path'] for r in json.loads((A/'cleanup_authorization.json').read_text())['scope']]
 out['deleted_targets_absent']={n:not Path(n).exists() and not Path(n).is_symlink() for n in names}
 assert all(out['deleted_targets_absent'].values())
 active=root/'evqa-pilot500/llava-v1.5-7b'
 out['L0_preserved']={'cache_exists':(active/'cache/layer_00').is_dir(),'history_tail':run(['tail','-n','2',str(active/'layer_00/loss_history.csv')])}
 p=Path('/proc/71731');out['L0_process']={'exists':p.exists(),'cmd':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()}
 log=Path(os.readlink(p/'fd/1'))
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-2000));tail=f.read().decode(errors='replace').replace('\r','\n').splitlines()
 out['L0_progress']=tail[-4:]
print(json.dumps(out))
