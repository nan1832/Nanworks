from typing import List, Optional

import torch
from PIL.Image import Image as ImageClass

from ..base import BaseVLLMForEdit


class Qwen25VLForEdit(BaseVLLMForEdit):
    """Wrapper for Qwen2.5-VL-7B-Instruct in VEAD visual-adapter experiments."""

    IMAGE_TOKEN_TEXT = "<|vision_start|><|image_pad|><|vision_end|>"

    def __init__(self, model_path: str, device="cuda", image_size: int = 448) -> None:
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        self.image_size = image_size
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map=device,
            trust_remote_code=True,
        )
        self.processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
            use_fast=False,
        )
        # VEAD assumes a fixed number of visual tokens. Resize to a square before
        # Qwen's dynamic-resolution processor so every Bridge image yields 256 tokens.
        self.processor.image_processor.min_pixels = image_size * image_size
        self.processor.image_processor.max_pixels = image_size * image_size
        self.model = self.model.eval().requires_grad_(False)
        super().__init__(self.model, device, True)

    def _prepare_images(self, imgs: Optional[List[ImageClass]]):
        if imgs is None:
            return None
        return [img.convert("RGB").resize((self.image_size, self.image_size)) for img in imgs]

    def get_llm_tokenizer(self):
        return self.processor.tokenizer

    def get_llm_input_embeds(self, texts: List[str], imgs: Optional[List[ImageClass]] = None):
        imgs = self._prepare_images(imgs)
        if imgs is not None:
            inpt = self.processor(text=texts, images=imgs, return_tensors="pt", padding=True)
        else:
            inpt = self.get_llm_tokenizer()(texts, return_tensors="pt", padding=True)

        inpt = {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inpt.items()}
        input_ids = inpt["input_ids"]
        attention_mask = inpt["attention_mask"]
        inputs_embeds = self.model.model.embed_tokens(input_ids)
        image_grid_thw = inpt.get("image_grid_thw")

        vt_range = None
        if imgs is not None:
            pixel_values = inpt["pixel_values"].type(self.model.visual.dtype)
            image_embeds = self.model.visual(pixel_values, grid_thw=image_grid_thw)
            image_embeds = image_embeds.to(inputs_embeds.device, inputs_embeds.dtype)
            image_mask = input_ids == self.get_img_special_token_id()
            n_image_tokens = int(image_mask.sum().item())
            n_image_features = int(image_embeds.shape[0])
            if n_image_tokens != n_image_features:
                raise ValueError(
                    f"Qwen image features/tokens mismatch: tokens={n_image_tokens}, features={n_image_features}, "
                    f"grid={image_grid_thw.tolist() if image_grid_thw is not None else None}"
                )
            if n_image_tokens != self.get_img_token_n() * len(imgs):
                raise ValueError(
                    f"Qwen visual token count is not fixed at {self.get_img_token_n()} per image: "
                    f"tokens={n_image_tokens}, batch={len(imgs)}, grid={image_grid_thw.tolist()}"
                )
            inputs_embeds = inputs_embeds.masked_scatter(image_mask.unsqueeze(-1).expand_as(inputs_embeds), image_embeds)
            img_positions = torch.where(image_mask[0])[0]
            vt_range = [int(img_positions[0]), int(img_positions[-1]) + 1]

        llm_inpt = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "inputs_embeds": inputs_embeds,
            "image_grid_thw": image_grid_thw,
        }
        return llm_inpt, vt_range

    def get_llm_outpt(self, llm_inpt, vt_range=None):
        return self.model(
            input_ids=llm_inpt.get("input_ids"),
            inputs_embeds=llm_inpt["inputs_embeds"],
            attention_mask=llm_inpt.get("attention_mask"),
            image_grid_thw=llm_inpt.get("image_grid_thw"),
            output_attentions=None,
            output_hidden_states=None,
            return_dict=True,
            use_cache=False,
        )

    def get_img_special_token_str(self):
        return self.IMAGE_TOKEN_TEXT

    def get_img_special_token_id(self):
        return self.model.config.image_token_id

    def get_img_token_n(self):
        merge = self.model.config.vision_config.spatial_merge_size
        patch = self.model.config.vision_config.patch_size
        return (self.image_size // patch // merge) ** 2

    def is_q_former_based(self):
        return False
