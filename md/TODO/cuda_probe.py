import os

import torch

visible = os.environ.get("CUDA_VISIBLE_DEVICES")
available = torch.cuda.is_available()
count = torch.cuda.device_count()
name = torch.cuda.get_device_name(0) if available and count else "NONE"

print(f"CUDA_VISIBLE_DEVICES={visible} available={available} count={count} name0={name}")
