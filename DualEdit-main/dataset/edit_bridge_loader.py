import json
import os
from copy import deepcopy
import importlib.util
from pathlib import Path

from tqdm import tqdm

try:
    from .vllm import BaseVLLMEditData
except ImportError:
    _VMLL_PATH = Path(__file__).resolve().with_name("vllm.py")
    _spec = importlib.util.spec_from_file_location("dualedit_dataset_vllm", _VMLL_PATH)
    _module = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_module)
    BaseVLLMEditData = _module.BaseVLLMEditData


class EditBridge(BaseVLLMEditData):
    def __init__(self, data_path, img_root_dir, coco_img_dir=None, data_n=None, img_path_map=None):
        if coco_img_dir is None:
            coco_img_dir = img_root_dir
        if img_path_map is None:
            img_path_map = {
                "train/images": "bridge_train/bridge_images",
                "val/images": "bridge_val/bridge_images",
            }

        with open(data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if data_n is not None:
            raw_data = raw_data[:data_n]

        def remap(rel_path):
            if rel_path is None:
                return None
            for src, dst in img_path_map.items():
                if rel_path.startswith(src):
                    return dst + rel_path[len(src) :]
            return rel_path

        def resolve_bridge(rel_path):
            return None if rel_path is None else os.path.join(img_root_dir, remap(rel_path))

        def resolve_coco(rel_path):
            return None if rel_path is None else os.path.join(coco_img_dir, rel_path)

        data_with_img_path = []
        for item in tqdm(raw_data, desc="Preparing EditBridge data"):
            new_item = {
                "request": {
                    "image": resolve_bridge(item["request"]["image"]),
                    "prompt": f"{item['request']['prompt']} The answer is:",
                    "target_new": item["request"]["target_new"],
                    "anchor_policy": "bridge_only",
                    "edit_span_policy": "bridge_only",
                },
                "generality": {"text_rephrase": [], "image_rephrase": []},
                "locality": {"text_loc": [], "image_loc": []},
                "portability": {"1hop": [], "2hop": []},
            }

            for g in item.get("generality", {}).get("text_rephrase", []):
                new_item["generality"]["text_rephrase"].append(
                    {
                        "image": resolve_bridge(g.get("image")) if g.get("image") else None,
                        "prompt": f"{g['prompt']} The answer is:",
                        "target": g["target"],
                        "anchor_policy": "bridge_only",
                        "edit_span_policy": "bridge_only",
                    }
                )
            for g in item.get("generality", {}).get("image_rephrase", []):
                new_item["generality"]["image_rephrase"].append(
                    {
                        "image": resolve_bridge(g.get("image")) if g.get("image") else None,
                        "prompt": f"{g['prompt']} The answer is:",
                        "target": g["target"],
                        "anchor_policy": "bridge_only",
                        "edit_span_policy": "bridge_only",
                    }
                )
            for loc in item.get("locality", {}).get("text_loc", []):
                new_item["locality"]["text_loc"].append(
                    {
                        "image": None,
                        "prompt": f"{loc['prompt']}?",
                        "target": loc["target"],
                    }
                )
            for loc in item.get("locality", {}).get("image_loc", []):
                new_item["locality"]["image_loc"].append(
                    {
                        "image": resolve_coco(loc.get("image")) if loc.get("image") else None,
                        "prompt": f"{loc['prompt']} The answer is:",
                        "target": loc["target"],
                    }
                )
            for port_name in ("1hop", "2hop"):
                for port in item.get("portability", {}).get(port_name, []):
                    port_item = {
                        key: value
                        for key, value in port.items()
                        if key not in {"image", "prompt", "target"}
                    }
                    port_item.update(
                        {
                            "image": resolve_bridge(port.get("image")) if port.get("image") else None,
                            "prompt": f"{port['prompt']} The answer is:",
                            "target": port["target"],
                        }
                    )
                    new_item["portability"][port_name].append(port_item)

            data_with_img_path.append(new_item)

        data_with_img = deepcopy(data_with_img_path)
        for item in tqdm(data_with_img, desc="Loading images"):
            self.__load_imgs_for_data_with_img_path__(item)
        super().__init__(data_with_img, data_with_img_path)

    def dataset_name(self):
        return "EditBridgeTextAdapter"
