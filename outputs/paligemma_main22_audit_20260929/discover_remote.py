"""Read-only: locate original PaliGemma main training evidence and archive containers."""
import datetime, json, os, pathlib, socket, subprocess

root = pathlib.Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
stamp = 'paligemma_followup_job3044208_20260715_112056'
priority = 'paligemma_priority_reruns_job3044208_20260718_160000'
roots = [root/'tmp_archives_20260810'/'g09'/stamp,
         root/'tmp_archives_20260810'/'g09'/priority,
         pathlib.Path('/tmp/ph_teacher3')/stamp,
         pathlib.Path('/tmp/ph_teacher3')/priority,
         pathlib.Path('/var/tmp/ph_teacher3')/stamp]

def inspect(p):
    if not p.exists(): return {'path':str(p), 'exists':False}
    z={'path':str(p), 'exists':True, 'files':[], 'errors':[]}
    for cur, dirs, files in os.walk(p, onerror=lambda e:z['errors'].append(str(e))):
        rel=pathlib.Path(cur).relative_to(p)
        dirs[:]=[d for d in dirs if d not in {'train_cache','eval_cache','vead_train_cache','cache','images'} and len(rel.parts)<6]
        z['files'].append({'dir':str(rel),'dirs':dirs[:], 'files':[{'name':f,'size':(pathlib.Path(cur)/f).stat().st_size} for f in files]})
    return z

z={'server_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
   'host':socket.gethostname(),'roots':[inspect(p) for p in roots], 'related':[]}
for parent in [root,root/'tmp_archives_20260810',root/'tmp_archives_20260810'/'g09']:
    if parent.exists():
        z['related'] += [{'path':str(p),'is_dir':p.is_dir(),'size':p.stat().st_size} for p in parent.iterdir() if any(s in p.name.lower() for s in ['pali','archive','3044208'])]
z['queue']=subprocess.run(['squeue','-u','ph_teacher3','-h','-o','%i|%j|%T|%N|%M|%L'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True).stdout
print(json.dumps(z,ensure_ascii=False))
