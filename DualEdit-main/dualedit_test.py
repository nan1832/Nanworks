#%%
from utils import get_full_model_name, load_vllm_editor
from evaluation.vllm_editor_eval import VLLMEditorEvaluation
from utils.GLOBAL import ROOT_PATH
import os, argparse, sys, inspect

def get_attr():
    parser = argparse.ArgumentParser()
    parser.add_argument('-mn', '--edit_model_name', type=str, help='Editing model name: llava...', required=True)
    parser.add_argument('-enp', '--eval_name_postfix', type=str, default = '', help='Postfix name of this evaluation.')
    parser.add_argument('-dvc', '--device', type=str, help='CUDA device for editing.', required=True)
    parser.add_argument('-edvc', '--extra_devices', type=int, nargs='+', default = [], help='Extra CUDA devices, default empty.')
    parser.add_argument('-ckpt', '--editor_ckpt_path', type=str, default = None, help='Editor checkpoint path.')
    parser.add_argument('-dn', '--data_name', type=str, required = True, help = 'Evaluating dataset, including EVQA, EIC.')
    parser.add_argument('-dsn', '--data_sample_n', type=int, default = None, help = 'Sample number for evaluation.')
    parser.add_argument('-cp', '--config_path', type=str, default = None, help = 'Config path.')
    parser.add_argument('--data_path', type=str, default=None, help='Override eval data path.')
    parser.add_argument('--img_root_dir', type=str, default=None, help='Override image root directory.')
    parser.add_argument('--gating_mode', choices=['on', 'off'], default='on', help='Enable or disable adapter gating at eval time.')
    parser.add_argument('--gating_threshold', type=float, default=0.6, help='Cosine gating threshold.')
    args = parser.parse_args()
    return args


def resolve_path(path):
    if path is None:
        return None
    if os.path.exists(path):
        return path
    return os.path.join(ROOT_PATH, path)


def evaluator_accepts_editor_ckpt_path():
    params = inspect.signature(VLLMEditorEvaluation.__init__).parameters
    return 'editor_ckpt_path' in params


def build_eval_result_dir_path(cfg):
    base_dir = os.path.join('eval_results', 'vead', cfg.edit_model_name, cfg.evaluation_name)
    if evaluator_accepts_editor_ckpt_path():
        return os.path.join(base_dir, cfg.editor_ckpt_path.split('/')[-1], 'single_edit')
    return os.path.join(base_dir, 'single_edit')


def build_evaluator(editor, eval_data, cfg):
    kwargs = {}
    if evaluator_accepts_editor_ckpt_path():
        kwargs['editor_ckpt_path'] = cfg.editor_ckpt_path
    return VLLMEditorEvaluation(editor, eval_data, cfg.evaluation_name, 'eval_results', **kwargs)
 

if __name__ == '__main__':
    cfg = get_attr()
    cfg.edit_model_name = get_full_model_name(cfg.edit_model_name)
    cfg.evaluation_name = cfg.data_name.upper()
    if cfg.eval_name_postfix != '':
        cfg.evaluation_name = '%s-%s'%(cfg.evaluation_name, cfg.eval_name_postfix)
    # if has evaluated, skip
    eval_result_dir_path = build_eval_result_dir_path(cfg)
    if os.path.exists(eval_result_dir_path):
        print('Has evaluated: %s'%eval_result_dir_path)
        sys.exit()
    print(cfg)
    # load data
    config_path = resolve_path(cfg.config_path)
    editor = load_vllm_editor('vead', cfg.edit_model_name, cfg.device, cfg.extra_devices, cfg.editor_ckpt_path, False, config_path=config_path)
    from editor.vllm_editors.vead import adpt_model
    adpt_model.THREHSHOLD = float(cfg.gating_threshold)
    for adaptor in editor.adaptors.values():
        if hasattr(adaptor, 'open_gating'):
            adaptor.open_gating = (cfg.gating_mode == 'on')
    if cfg.data_name == 'EVQA':
        from dataset.vllm import EVQA
        data_path = cfg.data_path or os.path.join(ROOT_PATH, 'data/easy-edit-mm/vqa/vqa_eval.json')
        img_root_dir = cfg.img_root_dir or os.path.join(ROOT_PATH, 'data/easy-edit-mm/images')
        eval_data = EVQA(data_path, img_root_dir, cfg.data_sample_n)
    elif cfg.data_name == 'EIC':
        from dataset.vllm import EIC
        data_path = cfg.data_path or os.path.join(ROOT_PATH, 'data/easy-edit-mm/caption/caption_eval_edit.json')
        img_root_dir = cfg.img_root_dir or os.path.join(ROOT_PATH, 'data/easy-edit-mm/images')
        eval_data = EIC(data_path, img_root_dir, cfg.data_sample_n)
    # evaluate
    ev = build_evaluator(editor, eval_data, cfg)
    ev.evaluate_single_edit()

 
