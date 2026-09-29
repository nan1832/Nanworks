import os
import torch

print("env", os.environ.get("CUDA_VISIBLE_DEVICES"), flush=True)
print("available", torch.cuda.is_available(), flush=True)
print("count", torch.cuda.device_count(), flush=True)
torch.cuda.init()
print("name0", torch.cuda.get_device_name(0), flush=True)
