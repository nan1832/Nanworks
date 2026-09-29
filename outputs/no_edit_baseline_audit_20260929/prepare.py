import base64,csv,json,sys
from pathlib import Path
from remote import ssh,BASE,REMOTE,LOCAL
sys.stdout.reconfigure(encoding="utf-8")
root=LOCAL.parents[1]
groups={}
for r in csv.DictReader((root/"outputs/sweep_ledger_20260928_110311/sweep_results.csv").open(encoding="utf-8-sig")):
    if r["recipe"]!="main" or not r["source"].startswith(BASE+"/"):continue
    k=(r["dataset"],r["model"])
    groups.setdefault(k,[]).append(r["source"])
requests=[dict(dataset=d,model=m,sources=list(dict.fromkeys(paths)))
          for (d,m),paths in sorted(groups.items())]
assert len(requests)==21,len(requests)
(LOCAL/"requests.json").write_text(json.dumps(requests,indent=2),encoding="utf-8")
files={name:base64.b64encode((LOCAL/name).read_bytes()).decode()
       for name in ["requests.json","align_remote.py"]}
code="""import base64,json,hashlib
from pathlib import Path
root=Path(%r);root.mkdir(exist_ok=True)
for name,body in %r.items():
    p=root/name;data=base64.b64decode(body)
    if p.exists() and p.read_bytes()!=data:
        assert name=='align_remote.py' and not (root/'control/launch.json').exists()
        old=p.read_bytes();backup=p.with_name(p.name+'.'+hashlib.sha256(old).hexdigest()[:12]+'.bak')
        backup.write_bytes(old);p.write_bytes(data)
    else:p.write_bytes(data)
exec(compile((root/'align_remote.py').read_text(),str(root/'align_remote.py'),'exec'))
"""%(REMOTE,files)
result=ssh(code,timeout=180)
(LOCAL/"alignment.json").write_text(result,encoding="utf-8")
out=json.loads(result)
for g in out["groups"]:
    print(json.dumps({k:g.get(k) for k in ["dataset","model","status","sample_count","matched",
                                         "missing_indices","excluded","locality_input_differences"]}))
