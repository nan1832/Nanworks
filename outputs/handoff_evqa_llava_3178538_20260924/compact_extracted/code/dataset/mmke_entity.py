#!/usr/bin/env python3
"""VisEdit Dataset wrapper around the audited MMKE-Entity transformation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PIL import Image

from dataset.vllm import BaseVLLMEditData
from phase2_p3.mmke_entity_loader import load_evaluation_view, training_view


def _load_images(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "image":
                if child is not None:
                    with Image.open(child) as opened:
                        value[key] = opened.convert("RGB").copy()
            else:
                _load_images(child)
    elif isinstance(value, list):
        for child in value:
            _load_images(child)
    # Metadata scalars are intentionally left untouched.


class MMKEEntity(BaseVLLMEditData):
    """Dataset with an explicit training/evaluation field boundary.

    ``mode='train'`` strips every evaluation-only answer before ``self.data``
    is exposed to VEAD. ``mode='eval'`` retains associated QA and portability
    for the P3 evaluator.
    """

    def __init__(
        self,
        data_path: str,
        img_root_dir: str,
        data_n=None,
        mode: str = "train",
        load_images: bool = True,
    ):
        if mode not in {"train", "eval"}:
            raise ValueError("mode must be 'train' or 'eval'")
        full = load_evaluation_view(Path(data_path), Path(img_root_dir), data_n)
        self.full_evaluation_data_with_img_path = deepcopy(full)
        data_with_img_path = [training_view(row) for row in full] if mode == "train" else full
        data_with_img = deepcopy(data_with_img_path)
        if load_images:
            for row in data_with_img:
                _load_images(row)
        self.mode = mode
        super().__init__(data_with_img, data_with_img_path)

    def dataset_name(self):
        return f"MMKEEntity-{self.mode}"
