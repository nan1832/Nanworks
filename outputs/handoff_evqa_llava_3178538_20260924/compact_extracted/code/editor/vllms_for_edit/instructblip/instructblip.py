from typing import List, Optional

import torch
from PIL.Image import Image as ImageClass

from ..base import BaseVLLMForEdit


class InstructBLIPVicunaForEdit(BaseVLLMForEdit):
    """Wrapper for Salesforce InstructBLIP Vicuna models."""

    def __init__(self, model_path: str, device="cuda") -> None:
        from transformers import InstructBlipForConditionalGeneration, InstructBlipProcessor

        self.model = InstructBlipForConditionalGeneration.from_pretrained(model_path, device_map=device)
        self.processor = InstructBlipProcessor.from_pretrained(model_path, use_fast=False)
        self.model = self.model.eval().requires_grad_(False)
        super().__init__(self.model, device, False)

    def get_llm_tokenizer(self):
        return self.processor.tokenizer

    def get_llm_input_embeds(self, texts: List[str], imgs: Optional[List[ImageClass]] = None):
        """Return Vicuna input embeddings with optional InstructBLIP visual query prefix."""

        def build_visual_llm_inputs(pixel_values, qformer_input_ids, qformer_attention_mask, input_ids, attention_mask):
            vision_outputs = self.model.vision_model(
                pixel_values=pixel_values,
                output_attentions=None,
                output_hidden_states=None,
                return_dict=True,
            )
            image_embeds = vision_outputs[0]
            image_attention_mask = torch.ones(image_embeds.size()[:-1], dtype=torch.long, device=self.device)

            query_tokens = self.model.query_tokens.expand(image_embeds.shape[0], -1, -1)
            query_attention_mask = torch.ones(query_tokens.size()[:-1], dtype=torch.long, device=self.device)
            qformer_attention_mask = torch.cat(
                [query_attention_mask, qformer_attention_mask.to(self.device)],
                dim=1,
            )
            query_outputs = self.model.qformer(
                input_ids=qformer_input_ids.to(self.device),
                attention_mask=qformer_attention_mask,
                query_embeds=query_tokens,
                encoder_hidden_states=image_embeds,
                encoder_attention_mask=image_attention_mask,
                output_attentions=None,
                output_hidden_states=None,
                return_dict=True,
            )
            query_output = query_outputs[0][:, : query_tokens.size(1), :]

            language_model_inputs = self.model.language_projection(query_output)
            language_model_attention_mask = torch.ones(
                language_model_inputs.size()[:-1],
                dtype=torch.long,
                device=self.device,
            )
            inputs_embeds = self.model.language_model.get_input_embeddings()(input_ids.to(self.device))
            inputs_embeds = torch.cat([language_model_inputs, inputs_embeds], dim=1)
            attention_mask = torch.cat(
                [language_model_attention_mask, attention_mask.to(self.device)],
                dim=1,
            )
            return {"attention_mask": attention_mask, "inputs_embeds": inputs_embeds}

        if imgs is not None:
            inpt = self.processor(images=imgs, text=texts, return_tensors="pt", padding=True)
            inpt = {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inpt.items()}
            llm_inpt = build_visual_llm_inputs(
                inpt["pixel_values"],
                inpt["qformer_input_ids"],
                inpt["qformer_attention_mask"],
                inpt["input_ids"],
                inpt["attention_mask"],
            )
        else:
            inpt = self.get_llm_tokenizer()(texts, return_tensors="pt", padding=True).to(self.device)
            inputs_embeds = self.model.language_model.get_input_embeddings()(inpt.input_ids)
            llm_inpt = {"attention_mask": inpt.attention_mask, "inputs_embeds": inputs_embeds}

        vt_range = None if imgs is None else [0, self.get_img_token_n()]
        return llm_inpt, vt_range

    def get_llm_outpt(self, llm_inpt, vt_range=None):
        return self.model.language_model(
            inputs_embeds=llm_inpt["inputs_embeds"],
            attention_mask=llm_inpt["attention_mask"],
            output_attentions=None,
            output_hidden_states=None,
            return_dict=True,
            use_cache=False,
        )

    def get_img_special_token_str(self):
        return None

    def get_img_special_token_id(self):
        return None

    def get_img_token_n(self):
        return self.model.config.num_query_tokens

    def is_q_former_based(self):
        return True
