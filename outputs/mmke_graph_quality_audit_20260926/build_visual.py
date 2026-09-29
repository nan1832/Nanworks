"""Materialize verified audit data into the literal HTML template; no network."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
data=json.loads((p/'audit_evidence.json').read_text(encoding='utf8'))
fragment=(p/'mmke-graph-audit.template.html').read_text(encoding='utf8').replace('__AUDIT_JSON__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
assert len(fragment.encode('utf8'))<1_000_000
(p/'mmke-graph-audit.html').write_text(fragment,encoding='utf8')
print('fragment bytes',len(fragment.encode('utf8')))
