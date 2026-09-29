ROOT_PATH = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main'
DATA_DIR  = f"{ROOT_PATH}/data/easy-edit-mm"
IMG_DIR   = f"{DATA_DIR}/images"
VQA_DIR   = f"{DATA_DIR}/vqa"
CAP_DIR   = f"{DATA_DIR}/caption"
model_path_map = {
    'llava-v1.5-7b': 'models/llava-v1.5-7b-hf',
    'blip2-opt-2.7b': 'models/blip2-opt-2.7b',
    'instructblip-vicuna-7b': 'models/instructblip-vicuna-7b',
    'qwen2.5-vl-7b-instruct': 'models/Qwen2.5-VL-7B-Instruct',
    'qwen2.5-vl-3b-instruct': 'models/Qwen2.5-VL-3B-Instruct',
    'minigpt-4-vicuna-7b': 'models/minigpt-4-vicuna-7b',
    'paligemma-3b': 'models/paligemma-3b-mix-224-modelscope',
    'smolvlm-1.7b': 'models/SmolVLM-Instruct',
}


