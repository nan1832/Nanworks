from pathlib import Path
import json
A=Path('/var/tmp/ph_teacher3/cleanup_audits/20260915_l25_archive')
names=['archive_verifier.json','archive_manifest.json','source_verifier.json','cleanup_audit.json','cleanup_delete.json','cleanup_authorization.json','cleanup_manifest.tsv']
print(json.dumps({n:(A/n).read_text() for n in names if (A/n).is_file()}))
