from .base import BaseVLLMForEdit
from .llava.llava import LlavaForEdit
from .blip2.blip2 import BLIP2OPTForEdit

try:
    from .minigpt4.minigpt4 import MiniGPT4ForEdit
except ModuleNotFoundError:
    MiniGPT4ForEdit = None
