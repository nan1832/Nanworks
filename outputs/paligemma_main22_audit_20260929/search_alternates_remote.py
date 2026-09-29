"""Read-only last-pass search outside the already audited server_results tree."""
import datetime,json,os,pathlib,socket
host=socket.gethostname()
project=pathlib.Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
roots=[project] if host=='login01' else []
if host!='login01':
    for r in ['/tmp','/var/tmp']:
        with os.scandir(r) as entries:
            for entry in entries:
                try:
                    if entry.stat(follow_symlinks=False).st_uid==os.getuid() and entry.is_dir(follow_symlinks=False):
                        roots.append(pathlib.Path(entry.path))
                except OSError:
                    continue
skip={'server_results','cache','eval_cache','train_cache','vead_train_cache','node_cache','images','data_image','data','datasets','models','tokenizers','site-packages','__pycache__','.git','envs','hf_cache','venv','.venv','node_modules'}
z={'host':host,'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'roots':[str(p) for p in roots],'files':[],'containers':[],'errors':[],'visited':0}
for root in roots:
    if not root.exists():continue
    for cur,dirs,files in os.walk(root,onerror=lambda e:z['errors'].append(str(e))):
        z['visited']+=1
        p=pathlib.Path(cur)
        dirs[:]=[d for d in dirs if d not in skip and not d.startswith('.') and len(p.relative_to(root).parts)<16]
        for name in files:
            f=p/name
            if name.endswith(('.tar','.tar.gz','.tgz','.zip','.tar.zst','.tar.xz')):
                z['containers'].append({'path':str(f),'size':f.stat().st_size})
            if 'paligemma' in str(f).lower() and (name.startswith('epoch-') or name.endswith(('.log','.tsv','.csv','.json')) or name in {'train.done','eval_full.done'}):
                z['files'].append({'path':str(f),'size':f.stat().st_size})
print(json.dumps(z,ensure_ascii=False))
