from typing import List, Optional

import torch
from PIL.Image import Image as ImageClass

from ..base import BaseVLLMForEdit


class SmolVLMForEdit(BaseVLLMForEdit):
    """Wrapper for SmolVLM/Idefics3 models in VEAD visual-adapter experiments."""

    def __init__(self, model_path: str, device="cuda") -> None:
        from transformers import AutoProcessor, Idefics3ForConditionalGeneration

        self.model = Idefics3ForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map=device,
        )
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, use_fast=False)
        if hasattr(self.processor, "image_processor"):
            self.processor.image_processor.do_image_splitting = False
        self.model = self.model.eval().requires_grad_(False)
        super().__init__(self.model, device, True)

    def get_llm_tokenizer(self):
        return self.processor.tokenizer

    def get_llm_input_embeds(self, texts: List[str], imgs: Optional[List[ImageClass]] = None):
        if imgs is not None:
            batch_images = [[img] for img in imgs]
            inpt = self.processor(text=texts, images=batch_images, return_tensors="pt", padding=True)
        else:
            inpt = self.get_llm_tokenizer()(texts, return_tensors="pt", padding=True)
        inpt = {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inpt.items()}

        input_ids = inpt["input_ids"]
        inputs_embeds = self.model.model.text_model.get_input_embeddings()(input_ids)
        image_mask = input_ids == self.get_img_special_token_id()
        vt_range = None
        if imgs is not None:
            img_positions = torch.where(image_mask[0])[0]
            if len(img_positions) != self.get_img_token_n():
                raise ValueError(
                    f"SmolVLM visual token count mismatch: tokens={len(img_positions)}, expected={self.get_img_token_n()}"
                )
            vt_range = [int(img_positions[0]), int(img_positions[-1]) + 1]
            with torch.no_grad():
                pixel_values = inpt.get("pixel_values")
                pixel_attention_mask = inpt.get("pixel_attention_mask")
                batch_size, num_images, _, _, _ = pixel_values.shape
                pixel_values = pixel_values.to(dtype=self.model.model.dtype)
                flat_pixel_values = pixel_values.view(batch_size * num_images, *pixel_values.shape[2:])

                nb_values_per_image = flat_pixel_values.shape[1:].numel()
                real_images_inds = (flat_pixel_values == 0.0).sum(dim=(-1, -2, -3)) != nb_values_per_image
                flat_pixel_values = flat_pixel_values[real_images_inds].contiguous()

                if pixel_attention_mask is None:
                    pixel_attention_mask = torch.ones(
                        size=(flat_pixel_values.size(0), flat_pixel_values.size(2), flat_pixel_values.size(3)),
                        dtype=torch.bool,
                        device=flat_pixel_values.device,
                    )
                else:
                    pixel_attention_mask = pixel_attention_mask.view(
                        batch_size * num_images, *pixel_attention_mask.shape[2:]
                    )
                    pixel_attention_mask = pixel_attention_mask[real_images_inds].contiguous()

                patch_size = self.model.config.vision_config.patch_size
                patches_subgrid = pixel_attention_mask.unfold(dimension=1, size=patch_size, step=patch_size)
                patches_subgrid = patches_subgrid.unfold(dimension=2, size=patch_size, step=patch_size)
                patch_attention_mask = (patches_subgrid.sum(dim=(-1, -2)) > 0).bool()

                image_hidden_states = self.model.model.vision_model(
                    pixel_values=flat_pixel_values,
                    patch_attention_mask=patch_attention_mask,
                ).last_hidden_state
                image_hidden_states = self.model.model.connector(image_hidden_states)
                inputs_embeds = self.model.model.inputs_merger(
                    input_ids=input_ids,
                    inputs_embeds=inputs_embeds,
                    image_hidden_states=image_hidden_states,
                )

        return {
            "input_ids": input_ids,
            "attention_mask": inpt.get("attention_mask"),
            "inputs_embeds": inputs_embeds,
            "pixel_values": None,
            "pixel_attention_mask": None,
        }, vt_range

    def get_llm_outpt(self, llm_inpt, vt_range=None):
        input_ids = llm_inpt.get("input_ids")
        if input_ids is None and llm_inpt.get("inputs_embeds") is not None:
            if llm_inpt.get("attention_mask") is not None:
                input_ids = torch.zeros_like(llm_inpt["attention_mask"], dtype=torch.long)
            else:
                input_ids = torch.zeros(
                    llm_inpt["inputs_embeds"].shape[:2],
                    device=llm_inpt["inputs_embeds"].device,
                    dtype=torch.long,
                )
        return self.model(
            input_ids=input_ids,
            attention_mask=llm_inpt.get("attention_mask"),
            inputs_embeds=llm_inpt["inputs_embeds"],
            pixel_values=llm_inpt.get("pixel_values"),
            pixel_attention_mask=llm_inpt.get("pixel_attention_mask"),
            output_attentions=None,
            output_hidden_states=None,
            return_dict=True,
            use_cache=False,
        )

    def get_img_special_token_str(self):
        token = getattr(self.processor, "image_token", "<image>")
        return getattr(token, "content", str(token))

    def get_img_special_token_id(self):
        return self.model.config.image_token_id

    def get_img_token_n(self):
        return int(getattr(self.processor, "image_seq_len", self.model.config.image_seq_len))

    def is_q_former_based(self):
        return False
