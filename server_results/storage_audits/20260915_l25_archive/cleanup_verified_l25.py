"""Extend the standard cleanup audit ONLY for explicitly authorized verified duplicate L25 artifacts.

The upstream tool protects result markers unconditionally. This wrapper retains
its scope, ownership, symlink, overlap, active-reference, frozen-manifest and
re-audit checks. A marker is exempted only if its exact archived copy was verified;
operational metadata has an exact documented source-prefix replacement.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,sys
A=Path('/var/tmp/ph_teacher3/cleanup_audits/20260915_l25_archive')
ROOT=Path('/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812')
SRC=ROOT/'evqa-pilot500/llava-v1.5-7b/layer_25'
CACHE=ROOT/'evqa-pilot500/llava-v1.5-7b/cache/layer_25'
DST=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065/evqa-pilot500/llava-v1.5-7b/layer_25')
spec=importlib.util.spec_from_file_location('safe',A/'safe_cleanup_manifest.py');safe=importlib.util.module_from_spec(spec);spec.loader.exec_module(safe)
spec=importlib.util.spec_from_file_location('verify',A/'verify_result_tree.py');verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
manifest=json.loads((A/'archive_manifest.json').read_text())
mapping={f['source']:f for f in manifest['files']}
rows=safe.read_manifest(A/'cleanup_manifest.tsv')
allowed={str(SRC),str(CACHE),*[p for p in mapping if '/logs/evqa-pilot500_llava-v1.5-7b_L25_' in p]}
assert {r['path'] for r in rows}<=allowed
assert json.loads((A/'cleanup_authorization.json').read_text())['scope']==rows
def check_archive():
 rec=verify.inspect_layer(DST,'evqa-pilot500',True)
 assert rec['complete'] and (DST/'SYNC_VERIFIED').is_file()
 assert rec['selected_checkpoint']['sha256']==manifest['selected_sha256']
 for f in mapping.values():
  p=Path(f['source']);d=Path(f['destination'])
  assert d.resolve().as_posix().startswith(str(DST)+'/') and not d.is_symlink()
  assert safe.sha256_file(p)==f['source_sha256'],'Source changed: '+str(p)
  assert safe.sha256_file(d)==f['destination_sha256'],'Archive changed: '+str(d)
  if f['rewritten_layer_prefix']:
   assert p.read_text().replace(str(SRC),str(DST))==d.read_text()
  else:assert f['source_sha256']==f['destination_sha256']
 # Every file under the result directory must have a verified durable counterpart.
 source_now={str(p) for p in SRC.rglob('*') if p.is_file()}
 assert source_now=={p for p in mapping if p.startswith(str(SRC)+'/')}
check_archive()
scan=safe.scan_candidate
def scan_verified(path,user):
 result=scan(path,user)
 protected=result['protected_markers']
 for name in protected:
  assert name in mapping,'Unarchived protected file: '+name
  assert safe.sha256_file(Path(name))==mapping[name]['source_sha256']
  assert safe.sha256_file(Path(mapping[name]['destination']))==mapping[name]['destination_sha256']
 result['verified_archived_markers']=protected
 result['protected_markers']=[]
 return result
safe.scan_candidate=scan_verified
mode=os.environ.get('L25_CLEANUP_MODE','audit')
assert mode in ['audit','delete']
args=['safe_cleanup_manifest.py','--root',str(ROOT),'--manifest',str(A/'cleanup_manifest.tsv'),'--mode',mode]
if mode=='audit':args+=['--audit-output',str(A/'cleanup_audit.json')]
else:
 frozen=json.loads((A/'cleanup_audit.json').read_text())
 assert not frozen['violations'],frozen['violations']
 args+=['--audit-report',str(A/'cleanup_audit.json'),'--delete-log',str(A/'cleanup_delete.json'),
  '--confirm-sha256',safe.sha256_file(A/'cleanup_manifest.tsv'),'--confirm-text','DELETE-EXACT-VALIDATED-MANIFEST']
sys.argv=args
rc=safe.main()
print(json.dumps({'mode':mode,'rc':rc,'report':json.loads((A/('cleanup_audit.json' if mode=='audit' else 'cleanup_delete.json')).read_text())}),flush=True)
raise SystemExit(rc)
