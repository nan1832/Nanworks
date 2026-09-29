from pathlib import Path
import base64
O=Path(__file__).resolve().parent
files={
 'verify_result_tree.py':Path('C:/Users/zhoun/.codex/skills/hpc-sync-server-results/scripts/verify_result_tree.py'),
 'safe_cleanup_manifest.py':Path('C:/Users/zhoun/.codex/skills/hpc-clean-redundant-data/scripts/safe_cleanup_manifest.py')}
lines=["from pathlib import Path",'import base64',"out=Path('/var/tmp/ph_teacher3/cleanup_audits/20260915_l25_archive')","out.mkdir(parents=True,exist_ok=True)"]
for name,p in files.items():lines.append("(out/%r).write_bytes(base64.b64decode(%r))"%(name,base64.b64encode(p.read_bytes()).decode()))
lines.append("print('reviewed audit tools staged',str(out))")
(O/'stage_tools.py').write_text('\n'.join(lines)+'\n',encoding='utf-8')
