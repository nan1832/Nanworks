"""Archive only the authorized completed EVQA/LLaVA L25; never delete here."""
from pathlib import Path
import csv,datetime,hashlib,importlib.util,json,math,os,shutil,subprocess
A=Path('/var/tmp/ph_teacher3/cleanup_audits/20260915_l25_archive')
ROOT=Path('/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812')
SRC=ROOT/'evqa-pilot500/llava-v1.5-7b/layer_25'
SH=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065')
DST=SH/'evqa-pilot500/llava-v1.5-7b/layer_25'
TMP=DST.with_name(DST.name+'.partial_20260915_archive')
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def h(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):d.update(b)
 return d.hexdigest()
def load(name):
 spec=importlib.util.spec_from_file_location(name,A/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
verify=load('verify_result_tree');clean=load('safe_cleanup_manifest')
assert SRC.resolve(strict=True)==SRC and not SRC.is_symlink()
assert not DST.exists() and not TMP.exists(),'Destination/staging already exists; inspect before proceeding'
record=verify.inspect_layer(SRC,'evqa-pilot500',True)
save(A/'source_verifier.json',{'dataset':'evqa-pilot500','layers':[record]})
assert record['complete'],record['errors']
assert int(record['selected']['layer'])==25
assert all(math.isfinite(record['evaluation'][k]) for k in verify.METRICS)
sel=Path(record['selected']['checkpoint']).resolve(strict=True)
assert sel.is_relative_to(SRC) if hasattr(sel,'is_relative_to') else str(sel).startswith(str(SRC)+'/')
results=verify.result_files(SRC);assert len(results)==1
assert len(json.loads(results[0].read_text()))==2093
eval_data=json.loads((SRC/'eval_full.done').read_text());assert eval_data['eval_samples']==2093
assert Path(eval_data['checkpoint']).resolve()==sel
assert abs(sum(eval_data[k] for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc'])/5-eval_data['Average'])<1e-6
logs=sorted((ROOT/'logs').glob('evqa-pilot500_llava-v1.5-7b_L25_*'))
assert len(logs)>=2
candidates=[SRC,ROOT/'evqa-pilot500/llava-v1.5-7b/cache/layer_25',*logs]
assert not clean.active_references(candidates),'L25 referenced by a running process'
source_files=[]
for parent,dirs,names in os.walk(SRC,followlinks=False):
 for name in dirs+names:
  p=Path(parent)/name;assert not p.is_symlink(),str(p)
 for name in names:
  p=Path(parent)/name
  assert p.stat().st_uid==os.getuid()
  if 'checkpoints' in p.parts and p!=sel:raise RuntimeError('Unexpected nonselected checkpoint; inspect before archiving')
  source_files.append(p)
print(json.dumps({'phase':'verified_source','selected_sha256':h(sel),'source_files':len(source_files),'results_count':2093}),flush=True)
TMP.mkdir(parents=True)
mapping=[]
text_suffixes={'.json','.tsv','.csv','.yaml','.yml','.md','.txt','.done'}
for p in source_files:
 rel=p.relative_to(SRC);dest=TMP/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 before=h(p);shutil.copy2(str(p),str(dest))
 transformed=False
 if p.suffix in text_suffixes:
  raw=p.read_text();changed=raw.replace(str(SRC),str(DST))
  if changed!=raw:dest.write_text(changed);transformed=True
 after=h(dest)
 assert before==h(p),'source mutated while copying'
 if not transformed:assert before==after
 mapping.append({'source':str(p),'destination':str(DST/rel),'source_sha256':before,'destination_sha256':after,'source_bytes':p.stat().st_size,'destination_bytes':dest.stat().st_size,'rewritten_layer_prefix':transformed})
pro=TMP/'provenance';pro.mkdir(exist_ok=True)
for p in logs:
 dest=pro/'logs'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(str(p),str(dest));assert h(p)==h(dest)
 mapping.append({'source':str(p),'destination':str(DST/'provenance/logs'/p.name),'source_sha256':h(p),'destination_sha256':h(dest),'source_bytes':p.stat().st_size,'destination_bytes':dest.stat().st_size,'rewritten_layer_prefix':False})
for name in ['selected_checkpoint.tsv','train.done','eval_full.done']:
 dest=pro/'source_metadata'/name;dest.parent.mkdir(exist_ok=True);shutil.copy2(str(SRC/name),str(dest))
# Preserve snapshots as snapshots: active model run_config is L0, not historical L25 configuration.
for p in [ROOT/'layer_status.csv',ROOT/'queue.status.log',SRC.parent/'run_config.json']:
 if p.is_file():shutil.copy2(str(p),str(pro/('snapshot_'+p.name)))
scripts=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts')
for name in ['launch_formal_top3_stage2_20260812.sh','run_mmke_llava_shared_gpu_sweep.py']:
 shutil.copy2(str(scripts/name),str(pro/name))
metadata={'time':datetime.datetime.now().astimezone().isoformat(),'source_node':'g08','actual_job':3178538,'historical_queue_role':'job3150065',
 'source':str(SRC),'destination':str(DST),'selected_sha256':record['selected_checkpoint']['sha256'],'eval_samples':2093,
 'current_config_snapshot_warning':'snapshot_run_config.json belongs to active L0 invocation; L25 saved config is inside records and original L25 train/eval logs retained',
 'files':mapping,'cache_policy':'cache/layer_25 reproducible cache excluded from durable archive; authorized cleanup after verification'}
save(TMP/'ARCHIVE_MANIFEST.json',metadata)
# Atomic publish; destination did not previously exist.
assert not DST.exists();TMP.rename(DST)
final=verify.inspect_layer(DST,'evqa-pilot500',True);assert final['complete'],final['errors']
assert final['selected_checkpoint']['sha256']==record['selected_checkpoint']['sha256']
for item in mapping:
 assert h(Path(item['destination']))==item['destination_sha256']
 assert h(Path(item['source']))==item['source_sha256']
for name in ['train.done','selected_checkpoint.tsv','eval_full.done']:
 assert str(SRC) not in (DST/name).read_text(),'operational metadata still references temporary source'
save(DST/'SYNC_VERIFIED',{'time':datetime.datetime.now().astimezone().isoformat(),'selected_sha256':h(Path(final['selected']['checkpoint'])),'files_verified':len(mapping),'eval_samples':2093,'archive_manifest':'ARCHIVE_MANIFEST.json'})
# Enrich verifier compact artifacts with config, mean results, logs and archival provenance.
known={a['path'] for a in final['artifacts']}
for p in DST.rglob('*'):
 if p.is_file() and 'checkpoints' not in p.parts and p.stat().st_size<30*1024*1024 and str(p) not in known:
  final['artifacts'].append(verify.artifact_record(p,DST));known.add(str(p))
manifest={'root':str(DST),'dataset':'evqa-pilot500','complete_count':1,'incomplete_count':0,'layers':[final]}
save(A/'archive_verifier.json',manifest)
save(A/'archive_manifest.json',metadata)
cleanup_rows=[{'path':str(p),'reason':'L25 durable archive verified; '+('reproducible preprocessing cache' if '/cache/' in str(p) else 'exact source copy archived with SHA256')} for p in candidates if p.exists()]
with (A/'cleanup_manifest.tsv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=['path','reason'],delimiter='\t');writer.writeheader();writer.writerows(cleanup_rows)
save(A/'cleanup_authorization.json',{'user_authorized':'Archive EVQA-pilot500 LLaVA L25 to shared directory then remove its tmp data','scope':cleanup_rows,'excludes':['L0 active data','all other layers','shared archives','queue-wide logs/locks/config']})
print(json.dumps({'phase':'archive_verified','destination':str(DST),'selected_sha256':h(Path(final['selected']['checkpoint'])),'files_verified':len(mapping),'cleanup_candidates':cleanup_rows}),flush=True)
