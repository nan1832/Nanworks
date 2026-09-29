"""Three forward-only visual/answer alignment variants with a fixed prompt prefix.

No target tokens enter the image/Q-former encoder. Answer variants use every
valid next-token prediction position; token means are averaged equally by sample.
"""
import argparse
import csv
import hashlib
import importlib
import inspect
import json
import math
import os
import statistics
import sys
import time
import traceback
from pathlib import Path

MODELS={'blip2-opt-2.7b':32,'instructblip-vicuna-7b':32,'minigpt-4-vicuna-7b':32,'llava-v1.5-7b':32,'qwen2.5-vl-3b':36,'paligemma-3b':18,'smolvlm-1.7b':24}
DATASETS={'evqa-pilot500':500,'mmke-visual':214,'mmke-entity':636}
VARIANTS=['none','alt','model_pred']

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');os.replace(str(tmp),str(p))

def source_dir(base,model,ds):
    run='ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304' if model.startswith('qwen') else 'ours_direct_7models_3datasets_g08_gpu0_20260626_131624'
    return base/'server_results'/run/ds/model

def answer_layout(prefix_length,token_ids,special_ids):
    """p[t] predicts y[t]; p[t]+1 is the position that has already read y[t]."""
    assert prefix_length>0 and token_ids
    valid=[t for t,i in enumerate(token_ids) if i not in set(special_ids)]
    if not valid:raise ValueError('No ordinary answer tokens')
    return dict(prediction_positions=[prefix_length-1+t for t in valid],read_positions=[prefix_length+t for t in valid],valid_token_indices=valid,valid_token_count=len(valid),total_token_count=len(token_ids),excluded_special_tokens=len(token_ids)-len(valid))

def equal_sample_mean(values):
    if not values or any(not v for v in values):raise ValueError('Empty sample')
    return statistics.mean(statistics.mean(v) for v in values)

def embedder(vllm):
    for obj in [vllm.model,getattr(vllm.model,'language_model',None),getattr(vllm.model,'llama_model',None)]:
        if obj is not None and callable(getattr(obj,'get_input_embeddings',None)):
            result=obj.get_input_embeddings()
            if result is not None:return result
    raise RuntimeError('No language token embedding module')

def append_answer(inputs,ids,embedding):
    """Keep the exact image+prompt prefix. Never feed a target to Q-former."""
    import torch
    allowed={'inputs_embeds','input_ids','attention_mask','position_ids','image_grid_thw'}
    assert set(inputs)<=allowed, 'Audit new model input fields: '+str(set(inputs)-allowed)
    result=dict(inputs);prefix=inputs['inputs_embeds'];n=prefix.shape[1]
    tokens=torch.tensor([ids],dtype=torch.long,device=prefix.device)
    result['inputs_embeds']=torch.cat([prefix,embedding(tokens).to(prefix.dtype)],dim=1)
    if inputs.get('input_ids') is not None:result['input_ids']=torch.cat([inputs['input_ids'],tokens],dim=1)
    mask=inputs.get('attention_mask')
    if mask is not None:
        assert mask.ndim==2 and mask.shape[1]==n and bool(mask.bool().all()),'Batch=1 unpadded prompt required'
        result['attention_mask']=torch.cat([mask,torch.ones((1,len(ids)),device=mask.device,dtype=mask.dtype)],dim=1)
    pos=inputs.get('position_ids')
    if pos is not None:
        assert pos.shape[-1]==n
        tail=pos[...,-1:]+torch.arange(1,len(ids)+1,device=pos.device,dtype=pos.dtype)
        result['position_ids']=torch.cat([pos,tail],dim=-1)
    return result

def target_ids(tokenizer,prompt,target):
    # Match the existing teacher-forcing target ids when the text prefix is stable.
    # For a BPE merge at the join, use a recorded continuation tokenization instead.
    text=(' ' if prompt[-1]!=' ' and target[0]!=' ' else '')+target
    p=tokenizer(prompt,add_special_tokens=True)['input_ids']
    full=tokenizer(prompt+text,add_special_tokens=True)['input_ids']
    stable=full[:len(p)]==p
    ids=full[len(p):] if stable else tokenizer(text,add_special_tokens=False)['input_ids']
    if not ids:raise ValueError('Empty tokenized answer')
    return ids,dict(tokenization='native_target_suffix' if stable else 'explicit_continuation_prefix_boundary_mismatch',text_prefix_stable=stable)

def capture(vllm,helper,modules,inputs,vt,layout):
    import torch
    collected={};handles=[];n=inputs['inputs_embeds'].shape[1]
    begin,end=map(int,vt);assert 0<=begin<end<=n
    positions=layout['prediction_positions'];read_positions=layout.get('read_positions',[])
    assert positions and min(positions)>=end and max(positions)<n
    def hook(layer):
        def save(module,inp,out):
            h=helper.tensor_from_layer_output(out).detach()
            assert h.ndim==3 and h.shape[:2]==(1,n) and layer not in collected
            v=h[0,begin:end].mean(0);vf=h[0,begin:end].float().mean(0)
            def cos(ps,fp32=False):
                t=h[0,ps];vv=vf if fp32 else v;t=t.float() if fp32 else t
                c=torch.nn.functional.cosine_similarity(vv[None,:],t,dim=-1,eps=1e-8)
                zero=(torch.norm(vv)==0)|(torch.norm(t,dim=-1)==0)
                c=torch.where(zero,torch.zeros_like(c),c)
                if not bool(torch.isfinite(c).all()):raise ValueError('Nonfinite cosine')
                return c.float().cpu().tolist(),int(zero.sum())
            native,zeros=cos(positions);fp32,_=cos(positions,True)
            read_cos,_=cos(read_positions) if read_positions else ([],0)
            collected[layer]=dict(layer=layer,visual_track_cos=statistics.mean(native),visual_track_cos_fp32=statistics.mean(fp32),first_predict_cos=native[0],last_predict_cos=native[-1],answer_read_cos=statistics.mean(read_cos) if read_cos else None,visual_rep_norm=float(torch.norm(vf)),zero_pairs=zeros)
        return save
    try:
        for layer,module in modules.items():handles.append(module.register_forward_hook(hook(layer)))
        output=vllm.get_llm_outpt(inputs,vt);del output
        assert set(collected)==set(modules)
        return [collected[l] for l in modules]
    finally:
        for handle in handles:handle.remove()

def run(args):
    if not os.environ.get('SLURM_JOB_ID'):raise RuntimeError('Use an allocated GPU job')
    project=Path(args.project).resolve();base=project.parent
    sys.path[:0]=[str(project),str(project/'scripts')];os.chdir(str(project))
    import torch
    import numpy as np
    from p_track.p_track import PTrackConfig
    from utils import load_vllm_for_edit
    helper=importlib.import_module('run_ours_direct_candidate_layers_qwen_chatfix' if args.model.startswith('qwen') else 'run_ours_direct_candidate_layers')
    torch.manual_seed(123);np.random.seed(123)
    cfg_path=project/helper.CONFIG_PATHS[args.model];cfg=PTrackConfig.from_yaml(str(cfg_path))
    assert cfg.num_layers==MODELS[args.model]
    vllm=load_vllm_for_edit(args.model,'cuda:0');helper.set_model_eval(vllm)
    for p in vllm.model.parameters():p.requires_grad_(False)
    tokenizer=vllm.get_llm_tokenizer();embedding=embedder(vllm)
    special_ids=sorted(set(tokenizer.all_special_ids))
    modules={l:helper.find_module(vllm.model,cfg.layer_module_tmp.format(l)) for l in range(cfg.num_layers)}
    for ds in DATASETS:
        out=Path(args.out)/ds/args.model;old=source_dir(base,args.model,ds)
        match_by_layer={l:set() for l in modules}
        source_scores=old/'ours_direct_sample_layer_scores.jsonl'
        with source_scores.open() as stream:
            for line in stream:
                r=json.loads(line);match_by_layer[int(r['layer'])].add(str(r['sample_id']))
        matched=match_by_layer[0];assert all(v==matched for v in match_by_layer.values())
        cache_path=old/'model_pred_cache.jsonl';cache=helper.load_model_pred_cache(cache_path)
        dcfg=helper.DEFAULT_DATASETS[ds];data=helper.load_edit_data(ds,dcfg['data_path'],dcfg['img_root'],None)
        ids=[str(helper.get_sample_id(r,i)) for i,r in enumerate(data)]
        assert len(ids)==DATASETS[ds] and len(set(ids))==len(ids) and matched<=set(ids)
        assert all(cache.get(s,{}).get('status')=='ok' and cache[s].get('answer','').strip() for s in matched)
        files=[cfg_path,Path(helper.__file__),Path(__file__).resolve(),Path(dcfg['data_path']),source_scores,cache_path,Path(inspect.getfile(type(vllm)))]
        protocol=dict(schema=2,model=args.model,dataset=ds,variants=VARIANTS,matched_sample_ids=sorted(matched),all_sample_ids=ids,aggregation='mean over ordinary answer prediction tokens within sample; then equal mean over samples',prefix='one prompt+image encoding shared across all variants; no answer fed to image/Q-former',target_source='alt=request.target_new; model_pred=frozen historical cache, not dataset pred',old_answer_length='use the whole cached answer; do not silently regenerate beyond the historical generation limit',answer_tokens='native teacher-forcing suffix if text prefix stable, otherwise explicit continuation; record fallback',positions='prediction of y_t at P-1+t; read-token diagnostic at P+t',special_ids=special_ids,precision='native cosine; fp32 diagnostic',ranking='signed descending Raw and Tukey kappa=1, no result-dependent flipping',files={str(p):sha(p) for p in files},torch=torch.__version__)
        if (out/'protocol.json').exists():assert read(out/'protocol.json')==protocol,'Protocol drift'
        else:atomic(out/'protocol.json',protocol)
        start_time=time.time();failures=[]
        for i,(row,sid) in enumerate(zip(data,ids)):
            path=out/'samples'/('%06d.json'%i)
            if path.exists():
                prev=read(path);assert prev['sample_id']==sid
                if prev['status']=='ok':continue
            req=row['request'];rec=dict(sample_i=i,sample_id=sid,matched_gradient_cohort=sid in matched,variants={})
            try:
                with torch.inference_mode():
                    original,vt=vllm.get_llm_input_embeds([req['prompt']],[req['image']]);prefix=original['inputs_embeds'].shape[1]
                    none_layout=dict(prediction_positions=[prefix-1],valid_token_count=1,total_token_count=0,excluded_special_tokens=0)
                    none=capture(vllm,helper,modules,original,vt,none_layout)
                    rec['variants']['none']=dict(status='ok',layout=none_layout,layers=none)
                    for variant in ['alt','model_pred']:
                        target=str(req['target_new']) if variant=='alt' else str(cache.get(sid,{}).get('answer') or '').strip()
                        if not target.strip():
                            rec['variants'][variant]=dict(status='unavailable',reason='empty_historical_model_pred' if variant=='model_pred' else 'empty_alt');continue
                        token_ids,meta=target_ids(tokenizer,req['prompt'],target)
                        layout=answer_layout(prefix,token_ids,special_ids)
                        inputs=append_answer(original,token_ids,embedding)
                        layers=capture(vllm,helper,modules,inputs,vt,layout)
                        # When first target token is ordinary, its predictor must see only the fixed prefix.
                        first_delta=max(abs(a['first_predict_cos']-b['first_predict_cos']) for a,b in zip(layers,none)) if layout['valid_token_indices'][0]==0 else None
                        rec['variants'][variant]=dict(status='ok',target=target,token_ids=token_ids,layout=layout,tokenization=meta,first_predict_max_abs_delta_vs_none=first_delta,layers=layers)
                        del inputs
                    rec.update(status='ok',prompt=req['prompt'],visual_range=list(vt),prefix_length=prefix)
                    del original
                if sid in matched:assert all(rec['variants'][v]['status']=='ok' for v in VARIANTS)
                atomic(path,rec)
            except Exception as exc:
                rec.update(status='failed',error=repr(exc),traceback=traceback.format_exc());atomic(path,rec);failures.append(sid)
                if len(failures)>=3:raise RuntimeError('Three failed samples; inspect before continuing')
            if i%25==0 or i==len(data)-1:
                progress=dict(status='running',dataset=ds,model=args.model,processed=i+1,total=len(data),failures=len(failures),elapsed_seconds=time.time()-start_time,job_id=os.environ['SLURM_JOB_ID'])
                atomic(out/'progress.json',progress);print(json.dumps(progress),flush=True)
        records=[read(out/'samples'/('%06d.json'%i)) for i in range(len(data))]
        assert all(r['status']=='ok' for r in records),'Incomplete forward run'
        rows=[];counts={};diagnostics={}
        for variant in VARIANTS:
            available=[r for r in records if r['variants'][variant]['status']=='ok'];counts[variant]=len(available)
            delta=[r['variants'][variant].get('first_predict_max_abs_delta_vs_none') for r in available]
            delta=[d for d in delta if d is not None]
            diagnostics[variant]=dict(available_samples=len(available),max_first_predict_delta=max(delta) if delta else None,token_counts=[r['variants'][variant]['layout']['valid_token_count'] for r in available],tokenization_fallbacks=sum(r['variants'][variant].get('tokenization',{}).get('text_prefix_stable') is False for r in available))
            for cohort in ['matched_gradient','available_train']:
                rr=[r for r in available if cohort=='available_train' or r['matched_gradient_cohort']]
                if cohort=='matched_gradient':assert len(rr)==len(matched)
                for layer in modules:
                    v=[r['variants'][variant]['layers'][layer] for r in rr]
                    rows.append(dict(variant=variant,cohort=cohort,layer=layer,n=len(rr),**{key:statistics.mean(z[key] for z in v) for key in ['visual_track_cos','visual_track_cos_fp32','first_predict_cos','last_predict_cos','visual_rep_norm']},answer_read_cos=statistics.mean(z['answer_read_cos'] for z in v) if variant!='none' else None,zero_pairs=sum(z['zero_pairs'] for z in v)))
        atomic(out/'layer_scores.json',dict(schema=2,model=args.model,dataset=ds,rows=rows));atomic(out/'diagnostics.json',diagnostics)
        with (out/'layer_scores.csv').open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        summary=dict(status='done',schema=2,dataset=ds,model=args.model,sample_count=len(records),matched_sample_count=len(matched),available_counts=counts,protocol_sha256=sha(out/'protocol.json'),scores_sha256=sha(out/'layer_scores.json'),diagnostics_sha256=sha(out/'diagnostics.json'),sample_files={p.name:sha(p) for p in sorted((out/'samples').glob('*.json'))},job_id=os.environ['SLURM_JOB_ID'])
        atomic(out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='sample_files'}),flush=True)
        del data,records

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);parser.add_argument('--out',required=True);parser.add_argument('--model',choices=list(MODELS),required=True)
    run(parser.parse_args())

if __name__=='__main__':main()
