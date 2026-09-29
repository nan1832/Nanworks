from typing import List, Optional

import torch
from PIL.Image import Image as ImageClass

from ..base import BaseVLLMForEdit


class PaliGemmaForEdit(BaseVLLMForEdit):
    """Wrapper for PaliGemma models in VEAD visual-adapter experiments."""

    def __init__(self, model_path: str, device="cuda") -> None:
        from transformers import AutoProcessor, PaliGemmaForConditionalGeneration

        self.model = PaliGemmaForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map=device,
        )
        self.processor = AutoProcessor.from_pretrained(model_path, use_fast=False)
        self.model = self.model.eval().requires_grad_(False)
        super().__init__(self.model, device, False)

    def get_llm_tokenizer(self):
        return self.processor.tokenizer

    def get_llm_input_embeds(self, texts: List[str], imgs: Optional[List[ImageClass]] = None):
        if imgs is not None:
            inpt = self.processor(images=imgs, text=texts, return_tensors="pt", padding=True)
        else:
            inpt = self.get_llm_tokenizer()(texts, return_tensors="pt", padding=True)
        inpt = {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inpt.items()}

        input_ids = inpt["input_ids"]
        attention_mask = inpt.get("attention_mask")
        inputs_embeds = self.model.get_input_embeddings()(input_ids)
        vt_range = None

        if imgs is not None:
            vision_dtype = next(self.model.vision_tower.parameters()).dtype
            pixel_values = inpt["pixel_values"].to(dtype=vision_dtype)
            image_features = self.model.get_image_features(pixel_values)
            image_features = image_features.to(inputs_embeds.device, inputs_embeds.dtype)
            image_mask = input_ids == self.get_img_special_token_id()
            if int(image_mask.sum().item()) != int(image_features.shape[0] * image_features.shape[1]):
                raise ValueError(
                    "PaliGemma image feature/token mismatch: "
                    f"tokens={int(image_mask.sum().item())}, features={tuple(image_features.shape)}"
                )
            inputs_embeds = inputs_embeds.masked_scatter(image_mask.unsqueeze(-1).expand_as(inputs_embeds), image_features)
            img_positions = torch.where(image_mask[0])[0]
            vt_range = [int(img_positions[0]), int(img_positions[-1]) + 1]

        position_ids = None
        if attention_mask is not None:
            position_ids = attention_mask.long().cumsum(-1).clamp(min=1)

        return {
            "attention_mask": attention_mask,
            "inputs_embeds": inputs_embeds,
            "position_ids": position_ids,
        }, vt_range

    def get_llm_outpt(self, llm_inpt, vt_range=None):
        return self.model.language_model(
            inputs_embeds=llm_inpt["inputs_embeds"],
            attention_mask=llm_inpt.get("attention_mask"),
            position_ids=llm_inpt.get("position_ids"),
            output_attentions=None,
            output_hidden_states=None,
            return_dict=True,
            use_cache=False,
        )

    def get_img_special_token_str(self):
        return None

    def get_img_special_token_id(self):
        return self.model.config.image_token_index

    def get_img_token_n(self):
        size = self.processor.image_processor.size
        image_size = size.get("height", size.get("shortest_edge", 224)) if isinstance(size, dict) else int(size)
        patch_size = self.model.config.vision_config.patch_size
        return (image_size // patch_size) ** 2

    def is_q_former_based(self):
        return False
