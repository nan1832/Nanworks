"""Forward-only representation alignment, at decoder block outputs.

No target answer is fed to the forward pass. Keeps both all-training and the
historical visual-gradient cohort, so differences in sample admission are explicit.
Run only inside a scheduler-allocated GPU job. Existing experiments are read-only.
"""
import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

MODELS={"blip2-opt-2.7b":32,"instructblip-vicuna-7b":32,"minigpt-4-vicuna-7b":32,"llava-v1.5-7b":32,"qwen2.5-vl-3b":36,"paligemma-3b":18,"smolvlm-1.7b":24}
DATASETS={"evqa-pilot500":500,"mmke-visual":214,"mmke-entity":636}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(str(tmp),str(p))
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def source_dir(base,model,ds):
    run='ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304' if model.startswith('qwen') else 'ours_direct_7models_3datasets_g08_gpu0_20260626_131624'
    return base/'server_results'/run/ds/model

def run(args):
    if not os.environ.get('SLURM_JOB_ID'):raise RuntimeError('Run in an allocated Slurm job')
    project=Path(args.project).resolve();base=project.parent
    sys.path[:0]=[str(project),str(project/'scripts')];os.chdir(str(project))
    import torch
    import numpy as np
    from p_track.p_track import PTrackConfig
    from utils import load_vllm_for_edit
    helper=importlib.import_module('run_ours_direct_candidate_layers_qwen_chatfix' if args.model.startswith('qwen') else 'run_ours_direct_candidate_layers')
    torch.manual_seed(123);np.random.seed(123)
    cfg_path=project/helper.CONFIG_PATHS[args.model]
    cfg=PTrackConfig.from_yaml(str(cfg_path))
    assert int(cfg.num_layers)==MODELS[args.model]
    vllm=load_vllm_for_edit(args.model,'cuda:0')
    helper.set_model_eval(vllm)
    modules={l:helper.find_module(vllm.model,cfg.layer_module_tmp.format(l)) for l in range(int(cfg.num_layers))}
    for ds in DATASETS:
        out=Path(args.out)/ds/args.model
        out.mkdir(parents=True,exist_ok=True)
        old=source_dir(base,args.model,ds)
        log=old/'ours_direct_sample_layer_scores.jsonl'
        ids={l:set() for l in modules}
        with log.open() as f:
            for line in f:
                r=json.loads(line);ids[int(r['layer'])].add(str(r['sample_id']))
        match=ids[0]
        assert all(s==match for s in ids.values())
        with (old/'ours_direct_layer_scores.csv').open() as f:
            counts={int(r['n_request']) for r in csv.DictReader(f)}
        assert counts=={len(match)}
        data_cfg=helper.DEFAULT_DATASETS[ds]
        data=helper.load_edit_data(ds,data_cfg['data_path'],data_cfg['img_root'],None)
        assert len(data)==DATASETS[ds]
        sample_ids=[str(helper.get_sample_id(r,i)) for i,r in enumerate(data)]
        assert len(set(sample_ids))==len(sample_ids) and match<=set(sample_ids)
        protocol=dict(schema=1,model=args.model,dataset=ds,total_samples=len(data),historical_gradient_samples=len(match),matched_sample_ids=sorted(match),all_sample_ids=sample_ids,formula='mean_i cosine(mean_visual_tokens(h_i_layer), h_i_layer[last_prompt_position])',position='last prompt position predicting the first answer token; prompt+image only',target='none; independent of alt/model_pred',module_template=cfg.layer_module_tmp,layer_count=len(modules),precision='native hidden dtype as original bridge code; also record float32 diagnostic',epsilon=1e-8,files={str(p):sha(p) for p in [cfg_path,Path(helper.__file__),Path(__file__).resolve(),Path(data_cfg['data_path']),log,old/'ours_direct_layer_scores.csv']},torch=torch.__version__)
        if (out/'protocol.json').exists():assert read(out/'protocol.json')==protocol,'protocol drift'
        else:atomic(out/'protocol.json',protocol)
        started=time.time();failures=[]
        for i,(row,sid) in enumerate(zip(data,sample_ids)):
            path=out/'samples'/('%06d.json'%i)
            if path.exists():
                r=read(path);assert r['sample_id']==sid
                if r['status']=='ok':continue
            req=row['request'];captured={};handles=[]
            try:
                with torch.inference_mode():
                    inputs,vt=vllm.get_llm_input_embeds([req['prompt']],[req['image']])
                    start,end=int(vt[0]),int(vt[1])
                    seq_len=int(inputs['inputs_embeds'].shape[1]);track=seq_len-1
                    assert 0<=start<end<=seq_len and not start<=track<end
                    def hook(l):
                        def capture(module,inp,output):
                            h=helper.tensor_from_layer_output(output).detach()
                            assert h.ndim==3 and h.shape[0]==1 and h.shape[1]==seq_len and l not in captured
                            v=h[0,start:end].mean(dim=0);t=h[0,track]
                            vn=torch.norm(v);tn=torch.norm(t)
                            zero=bool(vn==0 or tn==0)
                            native=0.0 if zero else float(torch.nn.functional.cosine_similarity(v.unsqueeze(0),t.unsqueeze(0),dim=-1,eps=1e-8)[0])
                            vf=h[0,start:end].float().mean(dim=0);tf=t.float()
                            fp32=float(torch.nn.functional.cosine_similarity(vf.unsqueeze(0),tf.unsqueeze(0),dim=-1,eps=1e-8)[0])
                            record=dict(layer=l,visual_track_cos=native,visual_track_cos_fp32=fp32,visual_rep_norm=float(vn),track_norm=float(tn),zero_vector=zero)
                            assert all(math.isfinite(record[k]) for k in ['visual_track_cos','visual_track_cos_fp32','visual_rep_norm','track_norm'])
                            captured[l]=record
                        return capture
                    for l,module in modules.items():handles.append(module.register_forward_hook(hook(l)))
                    answer=vllm.get_llm_outpt(inputs,vt)
                    assert set(captured)==set(modules)
                    del answer
                rec=dict(status='ok',sample_i=i,sample_id=sid,matched_gradient_cohort=sid in match,prompt=req['prompt'],visual_range=[start,end],track_position=track,sequence_length=seq_len,layers=[captured[l] for l in modules])
                atomic(path,rec)
            except Exception as e:
                rec=dict(status='failed',sample_i=i,sample_id=sid,error=repr(e),traceback=traceback.format_exc())
                atomic(path,rec);failures.append(rec)
                if len(failures)>=3:raise RuntimeError('Three failed inputs; stop and inspect rather than silently reduce coverage')
            finally:
                for handle in handles:handle.remove()
                captured.clear()
            if i%25==0 or i==len(data)-1:
                progress=dict(status='running',dataset=ds,model=args.model,processed=i+1,total=len(data),failures=len(failures),elapsed_seconds=time.time()-started,job_id=os.environ['SLURM_JOB_ID'])
                atomic(out/'progress.json',progress);print(json.dumps(progress),flush=True)
        records=[read(out/'samples'/('%06d.json'%i)) for i in range(len(data))]
        assert all(r['status']=='ok' for r in records),'Incomplete cohort; no complete-score claim'
        rows=[]
        for cohort in ['all_train','matched_gradient']:
            rr=[r for r in records if cohort=='all_train' or r['matched_gradient_cohort']]
            assert len(rr)==(len(data) if cohort=='all_train' else len(match))
            for l in modules:
                values=[r['layers'][l] for r in rr]
                rows.append(dict(cohort=cohort,layer=l,n=len(rr),**{k:float(np.mean([v[k] for v in values],dtype=np.float64)) for k in ['visual_track_cos','visual_track_cos_fp32','visual_rep_norm','track_norm']},zero_vectors=sum(v['zero_vector'] for v in values)))
        atomic(out/'layer_scores.json',dict(model=args.model,dataset=ds,rows=rows))
        with (out/'layer_scores.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        summary=dict(status='done',dataset=ds,model=args.model,sample_count=len(data),matched_sample_count=len(match),layers=len(modules),elapsed_seconds=time.time()-started,protocol_sha256=sha(out/'protocol.json'),scores_sha256=sha(out/'layer_scores.json'),sample_files={p.name:sha(p) for p in sorted((out/'samples').glob('*.json'))},job_id=os.environ['SLURM_JOB_ID'])
        atomic(out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='sample_files'}),flush=True)
        del data,records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--out',required=True);p.add_argument('--model',choices=list(MODELS),required=True)
    run(p.parse_args())
