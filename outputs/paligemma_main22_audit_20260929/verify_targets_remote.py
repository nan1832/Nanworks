"""Read-only per-layer verification of all 22 historical main records."""
import datetime,json,os,pathlib,socket
base=pathlib.Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tmp_archives_20260810/g09')
follow=base/'paligemma_followup_job3044208_20260715_112056'
targets={'evqa-pilot500':[1,4,5,6,7,8,17], 'mmke-entity':[0,1,2,3,5,6,7,8,9,10,11,12,13,16,17]}
rows=[]
for ds,layers in targets.items():
    name='paligemma_main_evqa_pilot500_job3044208_20260715_112056' if ds=='evqa-pilot500' else 'paligemma_main_mmke_entity_job3044208_20260715_112056'
    for layer in layers:
        paths=[follow/name/'paligemma-3b'/('layer_%02d'%layer)]
        if ds=='mmke-entity' and layer==16:
            paths.append(base/'paligemma_priority_reruns_job3044208_20260718_160000'/'4_mmke-entity_main-rollback_L16'/'paligemma-3b'/'layer_16')
        row={'dataset':ds,'layer':layer,'paths':[]}
        for p in paths:
            item={'path':str(p),'exists':p.exists(),'files':[],'errors':[]}
            if p.exists():
                for cur,dirs,files in os.walk(p,onerror=lambda e:item['errors'].append(str(e))):
                    dirs[:]=[d for d in dirs if d not in {'cache','train_cache','eval_cache','vead_train_cache'}]
                    for f in files:
                        q=pathlib.Path(cur)/f
                        item['files'].append({'path':str(q),'size':q.stat().st_size})
            item['file_count']=len(item['files'])
            row['paths'].append(item)
        rows.append(row)
print(json.dumps({'server_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'host':socket.gethostname(),'read_only':True,'rows':rows},ensure_ascii=False))
