import argparse
import json
import os

from dataset.edit_bridge_loader import EditBridge
from editor.vllm_editors.vead.vead_with_port import VEADPortConfig, VEADWithPortability
from evaluation.vllm_editor_eval import VLLMEditorEvaluation
from utils import load_vllm_for_edit


VISEDIT_ROOT = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"
TEN_CLASSES_ROOT = "/datapool/home/ph_teacher3/Lwy/zhounan/Ten_Classes"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--config", required=True)
    parser.add_argument("--ckpt-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--eval-name", required=True)
    parser.add_argument("--bridge-root", default=os.path.join(TEN_CLASSES_ROOT, "bridge"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--device", "-dvc", required=True)
    parser.add_argument("--data-n", "-dn", type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    config = VEADPortConfig.from_yaml(args.config)
    model_name = args.model_name or config.edit_model_name
    vllm = load_vllm_for_edit(model_name, args.device)
    editor = VEADWithPortability(vllm, config, args.device)
    editor.load_ckpt(args.ckpt_path, True, False)

    eval_data = EditBridge(
        args.data_path,
        img_root_dir=args.bridge_root,
        coco_img_dir=os.path.join(VISEDIT_ROOT, "data/easy-edit-mm/images"),
        data_n=args.data_n,
        img_path_map={"train/images": "bridge_train/bridge_images", "val/images": "bridge_val/bridge_images"},
    )
    evaluator = VLLMEditorEvaluation(editor, eval_data, args.eval_name, args.output_root)
    evaluator.evaluate_single_edit()

    manifest_path = os.path.join(args.output_root, "eval_manifest.json")
    os.makedirs(args.output_root, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()

