import json
import os
from pathlib import Path

import requests

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

from huggingface_hub import snapshot_download

ROOT = Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/minigpt-4-vicuna-7b")
VICUNA_REPO = "lmsys/vicuna-7b-v1.1"
MINIGPT4_REPO = "Vision-CAIR/MiniGPT-4"

FILES = {
    "eva_vit_g.pth": "https://storage.googleapis.com/sfr-vision-language-research/LAVIS/models/BLIP2/eva_vit_g.pth",
    "blip2_pretrained_flant5xxl.pth": "https://storage.googleapis.com/sfr-vision-language-research/LAVIS/models/BLIP2/blip2_pretrained_flant5xxl.pth",
}

BERT_BASE_UNCASED_CONFIG = {
    "architectures": ["BertForMaskedLM"],
    "attention_probs_dropout_prob": 0.1,
    "gradient_checkpointing": False,
    "hidden_act": "gelu",
    "hidden_dropout_prob": 0.1,
    "hidden_size": 768,
    "initializer_range": 0.02,
    "intermediate_size": 3072,
    "layer_norm_eps": 1e-12,
    "max_position_embeddings": 512,
    "model_type": "bert",
    "num_attention_heads": 12,
    "num_hidden_layers": 12,
    "pad_token_id": 0,
    "position_embedding_type": "absolute",
    "transformers_version": "4.6.0.dev0",
    "type_vocab_size": 2,
    "use_cache": True,
    "vocab_size": 30522,
}


def download_file(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 1024:
        print(f"[exists] {path} {path.stat().st_size}")
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    print(f"[download] {url} -> {path}", flush=True)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(path)
    print(f"[done] {path} {path.stat().st_size}", flush=True)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)

    minigpt4_dir = ROOT / "Vision-CAIR-MiniGPT-4"
    print(f"[minigpt4] {MINIGPT4_REPO} -> {minigpt4_dir}", flush=True)
    snapshot_download(
        repo_id=MINIGPT4_REPO,
        repo_type="model",
        local_dir=str(minigpt4_dir),
        max_workers=2,
        allow_patterns=["README.md", "pretrained_minigpt4.pth"],
    )

    vicuna_dir = ROOT / "vicuna-7b-v1.1"
    print(f"[vicuna] {VICUNA_REPO} -> {vicuna_dir}", flush=True)
    snapshot_download(
        repo_id=VICUNA_REPO,
        repo_type="model",
        local_dir=str(vicuna_dir),
        max_workers=2,
        ignore_patterns=["*.msgpack", "*.h5", "*.ot", "flax_model*", "tf_model*"],
    )

    for name, url in FILES.items():
        download_file(url, ROOT / name)

    (ROOT / "bert-base-uncased-config.json").write_text(
        json.dumps(BERT_BASE_UNCASED_CONFIG, indent=2),
        encoding="utf-8",
    )
    (ROOT / "processor_config.yaml").write_text("image_size: 224\n", encoding="utf-8")
    (ROOT / "model_config.yaml").write_text(
        "\n".join(
            [
                'vit_model: "eva_clip_g"',
                "image_size: 224",
                "num_query_token: 32",
                'llama_model: "vicuna-7b-v1.1"',
                'vit_path: "eva_vit_g.pth"',
                'bert_base_uncased_config_path: "bert-base-uncased-config.json"',
                'q_former_model: "blip2_pretrained_flant5xxl.pth"',
                'ckpt: "Vision-CAIR-MiniGPT-4/pretrained_minigpt4.pth"',
                "drop_path_rate: 0",
                "use_grad_checkpoint: false",
                'vit_precision: "fp16"',
                "freeze_vit: true",
                "has_qformer: true",
                "freeze_qformer: true",
                "low_resource: false",
                "max_txt_len: 160",
                'end_sym: "\\n"',
                'prompt_path: ""',
                'prompt_template: ""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    marker = {
        "status": "done",
        "model_dir": str(ROOT),
        "minigpt4_repo": MINIGPT4_REPO,
        "vicuna_repo": VICUNA_REPO,
        "files": sorted(p.name for p in ROOT.iterdir()),
    }
    (ROOT / ".download_complete.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
    print(json.dumps(marker, indent=2), flush=True)


if __name__ == "__main__":
    main()
