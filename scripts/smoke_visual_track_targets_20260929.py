"""GPU validation of the actual short/long-answer paths before resuming six groups."""
import argparse
import importlib
import os
import sys
from pathlib import Path

import run_visual_track_targets_20260929_inputfix as runner


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project',required=True)
    ap.add_argument('--model',choices=['smolvlm-1.7b','qwen2.5-vl-3b'],required=True)
    ap.add_argument('--receipt',required=True)
    args=ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID')=='3443209'
    project=Path(args.project).resolve()
    sys.path[:0]=[str(project),str(project/'scripts')]
    os.chdir(str(project))
    import torch
    import numpy as np
    from p_track.p_track import PTrackConfig
    from utils import load_vllm_for_edit
    helper=importlib.import_module('run_ours_direct_candidate_layers_qwen_chatfix' if args.model.startswith('qwen') else 'run_ours_direct_candidate_layers')
    torch.manual_seed(123);np.random.seed(123)
    model=load_vllm_for_edit(args.model,'cuda:0');helper.set_model_eval(model)
    tokenizer=model.get_llm_tokenizer();embedding=runner.embedder(model)
    cfg=PTrackConfig.from_yaml(str(project/helper.CONFIG_PATHS[args.model]))
    modules={l:helper.find_module(model.model,cfg.layer_module_tmp.format(l)) for l in range(cfg.num_layers)}
    assert len(modules)==runner.MODELS[args.model]
    records=[]
    with torch.inference_mode():
        for ds in runner.DATASETS:
            dc=helper.DEFAULT_DATASETS[ds]
            data=helper.load_edit_data(ds,dc['data_path'],dc['img_root'],3)
            cache=helper.load_model_pred_cache(runner.source_dir(project.parent,args.model,ds)/'model_pred_cache.jsonl')
            for i,row in enumerate(data):
                sid=str(helper.get_sample_id(row,i));req=row['request']
                original,vt=model.get_llm_input_embeds([req['prompt']],[req['image']])
                saved_prefix=original['inputs_embeds'].clone();prefix=saved_prefix.shape[1]
                none=runner.capture(model,helper,modules,original,vt,{'prediction_positions':[prefix-1]})
                cases={}
                for variant in ['alt','model_pred']:
                    answer=str(req['target_new']) if variant=='alt' else cache[sid]['answer'].strip()
                    ids,meta=runner.target_ids(tokenizer,req['prompt'],answer)
                    layout=runner.answer_layout(prefix,ids,tokenizer.all_special_ids)
                    inputs=runner.append_answer(original,ids,embedding)
                    assert torch.equal(inputs['inputs_embeds'][:,:prefix],saved_prefix)
                    result=runner.capture(model,helper,modules,inputs,vt,layout)
                    delta=max(abs(a['first_predict_cos']-b['first_predict_cos']) for a,b in zip(result,none)) if layout['valid_token_indices'][0]==0 else None
                    # bfloat16 full-sequence kernels can differ slightly by sequence length.
                    if delta is not None:assert delta<=0.03125,('First predictor changed',ds,sid,variant,delta)
                    assert torch.equal(original['inputs_embeds'],saved_prefix)
                    assert len(result)==runner.MODELS[args.model]
                    cases[variant]={'tokens':layout['valid_token_count'],'first_predict_max_abs_delta':delta,'layers':len(result)}
                records.append({'dataset':ds,'sample_id':sid,'variants':cases,'input_fields':list(original)})
                assert all(not m._forward_hooks for m in modules.values())
                print({'model':args.model,'dataset':ds,'sample':i,'status':'ok'},flush=True)
    assert len(records)==9
    assert any(r['variants']['alt']['tokens']>10 for r in records if r['dataset'].startswith('mmke'))
    runner.atomic(args.receipt,{'status':'passed','model':args.model,'sample_count':len(records),'runner_sha256':runner.sha(Path(runner.__file__)),'cases':records})


if __name__=='__main__':main()
