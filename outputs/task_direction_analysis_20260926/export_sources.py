"""Read-only CPU export; no inference, training, or server mutations."""
from pathlib import Path
import json,gzip,base64,hashlib,collections
R=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
MODELS=['blip2-opt-2.7b','instructblip-vicuna-7b','minigpt-4-vicuna-7b','llava-v1.5-7b','qwen2.5-vl-3b','paligemma-3b','smolvlm-1.7b']
DATA={'evqa-pilot500':R/'evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json',
      'mmke-visual':R/'mmke_visual_top3_union_train_eval_7models_20260613_014644/data/vqa_mmke_visual_train_evqa_compat.json',
      'mmke-entity':R/'mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json'}
def emit(name,obj):
    b=json.dumps(obj,ensure_ascii=False).encode()
    print(json.dumps(dict(name=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),gzip_base64=base64.b64encode(gzip.compress(b)).decode())),flush=True)
for ds,p in DATA.items():
    b=p.read_bytes(); data=json.loads(b)
    emit(ds+'_data.json',dict(source=str(p),source_sha256=hashlib.sha256(b).hexdigest(),records=data))
    for model in MODELS:
        root=R/('ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304' if model=='qwen2.5-vl-3b' else 'ours_direct_7models_3datasets_g08_gpu0_20260626_131624')/ds/model
        p=root/'ours_direct_sample_layer_scores.jsonl'
        digest=hashlib.sha256();layerids=collections.defaultdict(set);first={};duplicates=0;fields=set();mismatch=0
        with p.open('rb') as f:
            for line in f:
                digest.update(line)
                if not line.strip():continue
                x=json.loads(line);fields.update(x)
                sid=x['sample_id'];l=int(x['layer'])
                if sid in layerids[l]: duplicates+=1
                layerids[l].add(sid)
                if sid not in first:first[sid]=x
                elif any(x[k]!=first[sid][k] for k in ['sample_i','old_answer','target_new']):mismatch+=1
        files={}
        for name in ['ours_direct_layer_scores.csv','ours_direct_summary.json','summary.json','model_pred_cache.jsonl']:
            p=root/name
            if p.exists():
                b=p.read_bytes();files[name]=dict(sha256=hashlib.sha256(b).hexdigest(),text=b.decode('utf-8'))
        emit(ds+'__'+model+'.json',dict(dataset=ds,model=model,source_root=str(root),
            sample_source_sha256=digest.hexdigest(),sample_schema=sorted(fields),duplicates=duplicates,
            answer_mismatch_across_layers=mismatch,layer_sample_counts={l:len(v) for l,v in layerids.items()},
            identical_sample_ids_all_layers=all(v==next(iter(layerids.values())) for v in layerids.values()),
            samples=list(first.values()),files=files))
