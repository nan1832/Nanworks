"""Build evidence-tagged configuration from audited records, not manual examples."""
from pathlib import Path
import json

out=Path(__file__).resolve().parent
root=out.parent
bundle=next((root/'md/TODO/Second_prashe').glob('*_BLIP2_MMKE-Entity'))
actual=json.loads((bundle/'config/actual_run_config.json').read_text())
protocol=json.loads((out/'server_protocol_audit.json').read_text())
ranking=json.loads((out/'ranking_recomputed.json').read_text())
events=[json.loads(line) for line in (out/'probe_L0.log').read_text(encoding='utf-8').splitlines() if line.startswith('{')]
event={r['event']:r for r in events}
assert event['probe_complete']['status']=='passed'
def v(value,status,*evidence,note=None):
    r={'value':value,'evidence_status':status,'evidence':list(evidence)}
    if note:r['note']=note
    return r
def unknown(reason):return v(None,['待核验'],note=reason)
conf=['配置记录','源码确认']
observed=['本轮运行确认']
ck=['checkpoint内容确认','源码确认']
train_source='code/runner/run_blip2_mmke_entity_sweep.py:309-358'
cfg={
 'schema_version':'1.0',
 'scope':'P0 evidence audit and one-sample interface probe; not a training configuration to launch',
 'evidence_status_legend':{'配置记录':'YAML/CLI snapshot/records config', '源码确认':'actual code execution path',
  '运行日志确认':'historical training/evaluation log', 'checkpoint内容确认':'selected checkpoint metadata read on CPU',
  '本轮运行确认':'new P0 execution or remote inspection','待核验':'unknown or deliberately outside this audit'},
 'paths':{
  'local_project_root':v(str(root),observed),
  'server_project_root':v('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main',observed,'server_preflight.log'),
  'server_output':v('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/phase2_p0',observed,'stage_probe.log')},
 'layers':{
  'index_base':v(0,['源码确认'],'code/utils/model_factory_and_helpers.py:9-17','code/runner/run_blip2_mmke_entity_sweep.py:120-131'),
  'yaml_default':v([19],['配置记录'],'config/blip2-opt-2.7b.yaml:7'),
  'job3126082_cli_layers':v([1],conf,'launcher/launch_actual_job3126082.sh:279','config/actual_run_config.json:3'),
  'job3126082_effective_edit_layers':v([1],conf+['运行日志确认'],train_source,'runtime_log_excerpts.json'),
  'directory_rule':v('layer_{layer:02d}; no +1/-1 conversion',['源码确认'],train_source),
  'module_template':v('language_model.model.decoder.layers.{}',conf,'config/blip2-opt-2.7b.yaml:5','code/editor/vead.py:161-171'),
  'ours_formula':v('abs(S_v_cos) * S_v_new_norm',['排名记录','原始分数复算'],'ranking_recomputed.json'),
  'ours_top1':v(0,['排名记录','原始分数复算'],'ranking_recomputed.json'),
  'ours_top3':v([0,1,2],['排名记录','原始分数复算'],'ranking_recomputed.json'),
  'ours_valid_samples':v(284,['原始分数记录'],'ranking_recomputed.json'),
  'ours_total_samples':v(636,['排名记录','本轮运行确认'],'ranking_recomputed.json','server_preflight.log'),
  'ours_coverage':v(284/636,['原始分数复算'],'ranking_recomputed.json',note='低覆盖率；rank confirmed does not mean high-confidence localization'),
  'old_conflict_formula_top3':v([20,19,18],['历史排名记录'],'md/Location/OursDirect_repair_outputs_20260629/frozen_ours_direct_main_candidates.csv',note='旧深度加权公式，不是当前正式主公式'),
  'ranking_file_automatically_consumed_by_launcher':v(False,['源码确认'],'launcher/launch_actual_job3126082.sh:279',note='launcher硬编码补层1；没有读取排名文件的自动接口')},
 'model':{
  'name':v('blip2-opt-2.7b',conf,'config/blip2-opt-2.7b.yaml'),
  'wrapper_class':v(event['model_structure']['wrapper'],observed,'probe_L0.log'),
  'class':v(event['model_structure']['model'],observed,'probe_L0.log'),
  'language_model_class':v(event['model_structure']['language_model'],observed,'probe_L0.log'),
  'hidden_size':v(2560,conf+observed,'config/blip2-opt-2.7b.yaml:2','probe_L0.log'),
  'num_decoder_layers':v(32,observed,'probe_L0.log'),
  'visual_span_half_open':v([0,32],['源码确认']+observed,'code/model/blip2.py:62-81','probe_L0.log'),
  'visual_token_count':v(32,observed,'probe_L0.log'),
  'runtime_dtype':v('torch.float32',observed,'probe_L0.log'),
  'loader':v('utils.load_vllm_for_edit -> BLIP2OPTForEdit -> Blip2ForConditionalGeneration.from_pretrained',['源码确认','本轮运行确认'],'code/utils/model_factory_and_helpers.py:66-87','probe_L0.log'),
  'preprocessor':v('Blip2Processor.from_pretrained(model_path, use_fast=False); RGB PIL; tokenizer padding_side=right',conf+observed,'code/model/blip2.py:9-16','code/model/base_vllm.py:11-33','probe_L0.log'),
  'base_model_weight_sha256':unknown('本轮未对大型基础权重做全文件哈希；已复用服务器本地加载器和目录')},
 'adapter':{
  'class':v('editor.vllm_editors.vead.adpt_model.VisionEditAdaptor',conf,'code/editor/vead.py:168-170'),
  'constructor':v(event['model_structure']['adapter_constructor'],conf+observed,'probe_L0.log'),
  'active_forward':v('official_visual_forward',['源码确认']+observed,'code/runner/run_blip2_mmke_entity_sweep.py:50-116','probe_L0.log'),
  'hook_registration':v('register_forward_hook',['源码确认']+observed,'code/editor/vead.py:149-174','probe_L0.log'),
  'hook_position':v('post-block',['源码确认']+observed,'probe_L0.log'),
  'target_module':v('language_model.model.decoder.layers.0',observed,'probe_L0.log'),
  'actual_adapter_pre_hook':v(False,['源码确认'],'code/editor/vead.py:149-174',note='本轮额外pre-hook仅观测；Trace通用pre-hook不等于Adapter输入编辑'),
  'block_output_structure':v('tuple(Tensor, ...) -> list(Tensor, ...)',observed,'probe_L0.log'),
  'direct_write_slice':v('hidden_states[:, vt_begin:vt_end, :]',conf+observed,'code/runner/run_blip2_mmke_entity_sweep.py:94','probe_L0.log')},
 'training_protocol_L1':{
  'optimizer_class':v('torch.optim.Adam',['源码确认'],'code/editor/vead.py:728-731'),
  'optimizer_param_groups':v(protocol['L1']['optimizer_param_groups'],ck,'server_protocol_audit.json#L1'),
  'optimizer_scope':v('one parameter group per adaptor; includes InfluenceMapper; base VLM frozen',['源码确认'],'code/editor/vead.py:728-741'),
  'learning_rate':v(1e-4,conf+ck,'server_protocol_audit.json#L1'),
  'loss_weights':v({'rel_lambda':1,'gen_lambda':1,'loc_lambda':1,'inf_mapper_lambda':0.1},conf,'config/blip2-opt-2.7b.yaml:8-13','code/editor/vead.py:641-704'),
  'influence_trace':v({'add_it':True,'layers':list(range(20,31)),'test_n':1,'noise_level':0.7,'window':0,'vt_sample_n':24,'mid_dim':1024},conf,'config/blip2-opt-2.7b.yaml:14-21'),
  'epochs_budget':v(50,conf+['运行日志确认'],train_source,'runtime_log_excerpts.json'),
  'epochs_completed':v(50,['运行日志确认','训练历史复算'],'checkpoint_selection_recomputed.json'),
  'batch_size':v(2,conf+['运行日志确认'],'config/actual_run_config.json:5','runtime_log_excerpts.json'),
  'steps_per_epoch':v(318,['源码确认','运行日志确认'],train_source,'runtime_log_excerpts.json'),
  'steps_completed':v(15900,['运行日志确认','训练历史复算'],'checkpoint_selection_recomputed.json'),
  'cli_base_seed':v(20260601,conf,'config/actual_run_config.json:15'),
  'effective_seed_rule':v('cli_base_seed + layer',['源码确认'],'code/runner/run_blip2_mmke_entity_sweep.py:342'),
  'effective_seed':v(20260602,['源码确认','运行日志确认'],'runtime_log_excerpts.json'),
  'ema_alpha':v(0.1,conf,'config/actual_run_config.json:16','code/editor/base_editor_training.py:267'),
  'ema_initial_value':v(1,['源码确认'],'code/editor/base_editor_training.py:226'),
  'checkpoint_selection':v('minimum finite EMA among existing epoch checkpoints; EMA updated each batch',conf+['训练历史复算'],'code/runner/run_blip2_mmke_entity_sweep.py:225-241','checkpoint_selection_recomputed.json'),
  'scheduler':v('none in traced training path',['源码确认'],'code/editor/vead.py:728-731','code/editor/base_editor_training.py:217-286'),
  'data_buffer_size':v(4,conf,'config/actual_run_config.json:17'),
  'keep_top_ckpts':v(1,conf,'config/actual_run_config.json:18',note='训练清理保留EMA最优与loss最优并集；非始终仅1个'),
  'keep_last_ckpts':v(0,conf,'config/actual_run_config.json:19'),
  'historical_dependency_lock':unknown('已确认当前可运行环境；没有取得2026-08-01完整依赖锁文件')},
 'checkpoints':{},
 'data':{
  'loader_class':v('EVQA',conf+['运行日志确认'],'code/data/vllm_dataset.py:89-107','runtime_log_excerpts.json'),
  'train_path':v(actual['train_data'],['配置记录','本轮运行确认'],'config/actual_run_config.json','server_preflight.log'),
  'eval_path':v(actual['eval_data'],['配置记录','本轮运行确认'],'config/actual_run_config.json','server_preflight.log'),
  'image_root':v(actual['train_img_root'],['配置记录','本轮运行确认'],'server_preflight.log'),
  'train_count':v(636,['运行日志确认','本轮运行确认'],'runtime_log_excerpts.json','server_preflight.log'),
  'eval_count':v(954,['运行日志确认','本轮运行确认'],'runtime_log_excerpts.json','server_preflight.log'),
  'train_sample_n':v(None,['配置记录','源码确认'],'config/actual_run_config.json:13',note='None为已确认全量，不是未知'),
  'eval_sample_n':v(None,['配置记录','源码确认'],'config/actual_run_config.json:14',note='None为已确认全量，不是未知'),
  'sample_filter':v('first min(data_n, len(data)); data_n=None means all; no Ours valid-sample filtering in editor training',['源码确认'],'code/data/vllm_dataset.py:58-86'),
  'official_source_equivalence':unknown('P1应核对原始官方数据、转换规则、ID/图像对应、重复和train/eval隔离'),
  'new_dev_split_manifest':unknown('本轮未划分dev_train/dev_val')},
 'evaluation':{
  'entry':v('VLLMEditorEvaluation.evaluate_single_edit -> __get_results_after_edit__ -> get_mean_results',['源码确认','运行日志确认'],'code/evaluation/vllm_editor_eval.py:29-166','runtime_log_excerpts.json'),
  'rel_gen':v('masked teacher-forced per-sample token accuracy, then arithmetic mean',['源码确认'],'code/evaluation/vllm_editor_eval.py:66-89'),
  'locality':v('masked argmax token agreement with pre-edit logits on target-conditioned inputs',['源码确认'],'code/evaluation/vllm_editor_eval.py:41-48,90-98'),
  'generation_called':v(False,['源码确认'],'code/evaluation/vllm_editor_eval.py:29-98'),
  'generation_config':v(None,['源码确认'],'code/model/blip2.py:65-71',note='不适用：该训练/评测路径不调用generate；不能套用Ours定位生成model_pred的解码参数'),
  'use_cache':v(False,['源码确认'],'code/model/blip2.py:70'),
  'rounding_decimals':v(4,['源码确认'],'code/evaluation/vllm_editor_eval.py:151-166'),
  'average':v('mean(Rel,T-Gen,M-Gen,T-Loc,M-Loc), each converted to percent',['源码确认'],'code/runner/run_blip2_mmke_entity_sweep.py:156-163'),
  'portability':v(None,['未实现于第一阶段评测'],'code/evaluation/vllm_editor_eval.py',note='无Portability字段，不能填0或推断通过')},
 'edit_request_lifecycle':v('shared adaptor trained across requests; each test request encodes prompt+image+target_new with adaptor closed, sets edit signal, opens adaptor; restore disables adaptor and clears signal; no test-time optimizer update',['源码确认'],'code/editor/vead.py:204-257','code/evaluation/vllm_editor_eval.py:36-57'),
 'probe':{
  'status':v('passed',observed,'probe_L0.log'),
  'job_id':v('3178538',observed,'probe_L0.log'),
  'node':v('g08',observed,'probe_L0.log'),
  'layer':v(0,observed,'probe_L0.log'),
  'sample':v({'split':'eval','index':0,'image':'entity/Secret (South Korean group)+12.jpg'},observed,'server_preflight.log','probe_command.json'),
  'input_shape':v([1,201,2560],observed,'probe_L0.log'),
  'output_logits_shape':v([1,201,50304],observed,'probe_L0.log'),
  'hook_counts_by_stage':v(event['probe_complete']['counts'],observed,'probe_L0.log'),
  'max_visual_delta':v(event['adapter_output']['max_visual_delta'],observed,'probe_L0.log'),
  'max_nonvisual_delta':v(event['adapter_output']['max_nonvisual_delta'],observed,'probe_L0.log'),
  'parameter_updates':v(0,observed,'probe_L0.log'),
  'training_started':v(False,observed,'probe_L0.log'),
  'environment':v({k:event['environment'][k] for k in ['python','torch','transformers']},observed,'probe_L0.log')},
 'gates':{
  'static_evidence_audit':v('completed',observed,'p0_evidence_report.md'),
  'P1_data_audit':v('ready',observed,'p0_evidence_report.md',note='允许进入数据核验；不表示数据已通过P1'),
  'G1_P0_interface_prerequisites':v('satisfied',observed,'probe_L0.log'),
  'G1_training_launch_this_round':v(False,['用户范围限制'],note='本轮不启动训练'),
  'G1_remaining_before_launch':v(['complete P1 provenance/leakage/image checks','freeze strict phase1 vs new-dev protocol and layer-specific reference','schedule a training budget/resource window separately'],['待核验'],'p0_evidence_report.md')}
}
for name,record in protocol.items():
 if name not in ['L0','L1']:continue
 cfg['checkpoints'][name]={
   'layer':v(int(record['selected']['layer']),ck,'server_protocol_audit.json#'+name),
   'selected_epoch':v(record['checkpoint_metadata']['epoch'],ck,'server_protocol_audit.json#'+name),
   'selected_step':v(record['checkpoint_metadata']['i'],ck,'server_protocol_audit.json#'+name),
   'selected_ema':v(record['checkpoint_metadata']['ema_loss'],ck,'server_protocol_audit.json#'+name),
   'durable_path':v(record['selected']['checkpoint'],observed,'server_protocol_audit.json#'+name),
   'module_keys':v(record['module_keys'],ck,'server_protocol_audit.json#'+name),
   'epochs_completed':v(record['history']['last_epoch'],['训练历史复算'],'server_protocol_audit.json#'+name),
   'historical_metrics':v({k:record['eval_full.done'][k] for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average']},['历史评测完成记录'],'server_protocol_audit.json#'+name)}
cfg['checkpoints']['L0']['historical_effective_seed']=unknown('L0当前root run_config被L23覆盖；本轮尚未取得L0原始seed日志，不能把base+0当运行确认')
cfg['checkpoints']['L1']['effective_seed']=v(20260602,['运行日志确认'],'runtime_log_excerpts.json')
(out/'p0_effective_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Wrote p0_effective_config.json with explicit evidence statuses and nulls.')
