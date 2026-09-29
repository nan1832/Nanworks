import os
import torch

print("CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES"))
print("cuda_available", torch.cuda.is_available())
print("cuda_count", torch.cuda.device_count())
if torch.cuda.is_available():
    torch.cuda.init()
    print("cuda_name_0", torch.cuda.get_device_name(0))

from transformers import LlavaForConditionalGeneration

print("loading_llava")
model = LlavaForConditionalGeneration.from_pretrained(
    "models/llava-v1.5-7b-hf",
    device_map="cuda:0",
)
print("loaded", type(model).__name__)
