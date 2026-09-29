"""One request, original BLIP2 preprocessing and actual VEAD hooks, no training.

The edit-signal pass stops at the selected block; then one full edited query pass
is performed. Counters are reported separately. Requires an explicitly selected
checkpoint and layer; never guesses that a training layer is Ours Top-1.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

def emit(event, **values):
    print(json.dumps({'event':event, 'time':time.time(), **values}, default=str), flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--project-root',type=Path,required=True)
    p.add_argument('--runner',default='scripts/run_evqa_pilot500_blip2_visedit_sweep.py')
    p.add_argument('--config',default='configs/vead/blip2-opt-2.7b.yaml')
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--image-root',type=Path,required=True)
    p.add_argument('--layer',type=int,required=True)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--device',default='cuda:0')
    a=p.parse_args()
    root=a.project_root.resolve()
    for path in [root/a.runner,root/a.config,a.data,a.checkpoint]:
        if not path.is_file(): raise FileNotFoundError(path)
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    os.chdir(root)
    sys.path.insert(0,str(root))
    import torch
    import transformers
    emit('environment',host=platform.node(),python=platform.python_version(),torch=torch.__version__,
         transformers=transformers.__version__,layer=a.layer,checkpoint=str(a.checkpoint),
         slurm_job_id=os.environ.get('SLURM_JOB_ID'))
    if a.device.startswith('cuda'):
        free,total=torch.cuda.mem_get_info(a.device)
        emit('gpu_memory',free=free,total=total)
        if free<24*1024**3: raise RuntimeError('Less than 24 GiB free; defer probe to avoid competing for memory')
    spec=importlib.util.spec_from_file_location('phase1_actual_runner',root/a.runner)
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)  # Applies official_visual_forward and RGB file-close patch; no main().
    emit('runner_loaded',file=str(root/a.runner),sha256=hashlib.sha256((root/a.runner).read_bytes()).hexdigest(),
         adapter_forward=runner.VisionEditAdaptor.forward.__name__)
    data=runner.EVQA(str(a.data),str(a.image_root),1)
    request=data.data[0]['request']
    vllm=runner.load_vllm_for_edit('blip2-opt-2.7b',a.device)
    cfg=runner.make_config(root/a.config,a.layer)
    editor=runner.VEAD(vllm,cfg,a.device,None,None,str(root/'phase2_p0/probe_cache_unused'))
    runner.assert_current_editor_binding(editor,a.layer)
    editor.load_ckpt(str(a.checkpoint),True,False)
    editor.set_train(False)
    from utils import find_module
    module_path=cfg.llm_layer_tmp.format(a.layer)
    block=find_module(vllm.model,module_path)
    adaptor=editor.adaptors[module_path]
    params=list(vllm.model.parameters())+list(adaptor.parameters())
    versions=[t._version for t in params]
    assert not any(t.requires_grad for t in params)
    counters=Counter()
    state={'stage':'edit_signal','before':None}
    handles=[]
    def structure(x):
        if torch.is_tensor(x):return {'type':'Tensor','shape':list(x.shape),'dtype':str(x.dtype),'device':str(x.device)}
        if isinstance(x,dict):return {k:structure(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)):return {'type':type(x).__name__,'items':[structure(v) for v in x]}
        return {'type':type(x).__name__}
    def record(name,**fields):
        counters[state['stage']+'/'+name]+=1
        emit(name,stage=state['stage'],**fields)
    def block_pre(m,args,kwargs):record('block_pre_observer',args=structure(args),kwargs=structure(kwargs))
    def block_raw(m,args,out):record('block_output_before_adapter',output=structure(out))
    def block_post(m,args,out):record('block_output_after_adapter',output=structure(out))
    def adapter_pre(m,args):
        state['before']=args[0].detach().clone()
        record('adapter_input',input=structure(args),is_open=m.is_open,
               visual_span=[getattr(m,'inpt_vt_begin',None),getattr(m,'inpt_vt_end',None)])
    def adapter_post(m,args,out):
        before=state['before']
        diff=(out-before).abs()
        begin,end=getattr(m,'inpt_vt_begin',None),getattr(m,'inpt_vt_end',None)
        inside=outside=None
        if begin is not None:
            inside=float(diff[:,begin:end].max())
            pieces=[diff[:,:begin].reshape(-1),diff[:,end:].reshape(-1)]
            other=torch.cat(pieces)
            outside=float(other.max()) if other.numel() else 0.0
            assert outside==0.0, 'Adapter modified tokens outside visual span'
        assert torch.isfinite(out).all(), 'Nonfinite Adapter output'
        record('adapter_output',output=structure(out),max_visual_delta=inside,max_nonvisual_delta=outside)
    handles.append(block.register_forward_pre_hook(block_pre,with_kwargs=True))
    handles.append(block.register_forward_hook(block_raw,prepend=True))
    handles.append(block.register_forward_hook(block_post))
    handles.append(adaptor.register_forward_pre_hook(adapter_pre))
    handles.append(adaptor.register_forward_hook(adapter_post))
    emit('model_structure',wrapper=type(vllm).__name__,model=type(vllm.model).__name__,
         language_model=type(vllm.model.language_model).__name__,block=type(block).__name__,
         hidden_size=vllm.model.language_model.config.hidden_size,
         num_layers=len(vllm.model.language_model.model.decoder.layers),
         visual_token_count=vllm.get_img_token_n(),module_path=module_path,
         adapter_constructor={'hidden_size':cfg.llm_hidden_size,'mid_dim':cfg.adaptor_mid_dim,
          'cross_att_head_n':cfg.adaptor_cross_att_head_n,'img_tok_n':vllm.get_img_token_n(),
          'add_it':cfg.IT.add_it,'infm_dim':cfg.IT.mid_dim},
         actual_edit_hook='post-block register_forward_hook; observer pre-hook does not edit')
    try:
        with torch.no_grad():
            editor.edit_one_piece(request)
            state['stage']='edited_query'
            (inputs,span),labels,masks=vllm.prompts_imgs_target_to_xym(
                [request['prompt']],[request['image']],[request['target_new']])
            emit('prepared_inputs',input=structure(inputs),visual_span=span,
                 labels=structure(labels),masks=structure(masks))
            output=vllm.get_llm_outpt(inputs,span)
            assert torch.isfinite(output.logits).all(), 'Nonfinite logits'
            emit('forward_output',type=type(output).__name__,logits=structure(output.logits))
        assert versions==[t._version for t in params], 'Parameter version changed during probe'
        assert all(t.grad is None for t in params)
        for stage in ['edit_signal','edited_query']:
            for event in ['block_pre_observer','block_output_before_adapter','block_output_after_adapter','adapter_input','adapter_output']:
                assert counters[stage+'/'+event]==1,(stage,event,counters)
        emit('probe_complete',status='passed',counts=dict(counters),parameter_updates=0,
             training_started=False,layer=a.layer,scope='single-request checkpoint interface; not a training reproduction')
    finally:
        for h in handles:h.remove()
        editor.restore_to_original_model()
        for h in editor.adaptors_hooks.values():h.remove()

if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc()
        emit('probe_complete',status='failed',training_started=False)
        raise
