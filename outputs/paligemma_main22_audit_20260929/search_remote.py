"""Read-only evidence search, scoped to the user's project and temporary directories."""
import datetime, json, os, pathlib, socket

project=pathlib.Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
host=socket.gethostname()
roots=[project/'server_results',project/'records',pathlib.Path('/var/tmp/ph_teacher3')]
if host!='login01': roots=[pathlib.Path('/tmp/ph_teacher3'),pathlib.Path('/var/tmp/ph_teacher3')]
skip={'cache','eval_cache','train_cache','vead_train_cache','node_cache','images','data_image','data','datasets','models','tokenizers','site-packages','__pycache__','.git'}
z={'host':host,'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'roots':[str(x) for x in roots],'files':[],'containers':[],'directories':[],'texts':{},'errors':[],'visited':0}
stems=['paligemma_followup_job3044208_20260715_112056','paligemma_priority_reruns_job3044208_20260718_160000']
for root in roots:
    if not root.exists():continue
    for cur,dirs,files in os.walk(root,onerror=lambda e:z['errors'].append(str(e))):
        z['visited']+=1
        p=pathlib.Path(cur)
        dirs[:]=[d for d in dirs if d not in skip and not d.startswith('.') and len(p.relative_to(root).parts)<17]
        if 'paligemma' in str(p).lower() and (p.name.startswith('layer_') or p.name in stems):
            z['directories'].append({'path':str(p),'files':files,'dirs':dirs[:]})
        original=any(s in str(p) for s in stems)
        for name in files:
            f=p/name
            if name.endswith(('.tar','.tar.gz','.tgz','.zip','.tar.zst','.tar.xz')):
                z['containers'].append({'path':str(f),'size':f.stat().st_size})
            if original or ('paligemma' in str(f).lower() and name in {'loss_history.csv','selected_checkpoint.tsv','train.done','eval_full.done','selection_audit.json','run_config.json'}):
                z['files'].append({'path':str(f),'size':f.stat().st_size})
            if original and name=='ARCHIVE_MANIFEST.txt':z['texts'][str(f)]=f.read_text(errors='replace')
if host=='login01':
    for p in [project,project.parent,project/'server_results'/'tmp_archives_20260810'/'g09']:
        if p.exists():
            z['texts'][str(p)+'::listing']='\n'.join(x.name for x in p.iterdir())
    p=project/'server_results'/'tmp_archives_20260810'/'g09'/'archive_audit.tsv'
    if p.exists():z['texts'][str(p)]=p.read_text(errors='replace')
print(json.dumps(z,ensure_ascii=False))
