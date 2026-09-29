import os
from huggingface_hub import snapshot_download


TARGET_DIR = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b"


def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    snapshot_download(
        repo_id="Salesforce/blip2-opt-2.7b",
        local_dir=TARGET_DIR,
        local_dir_use_symlinks=False,
        ignore_patterns=[
            "*.h5",
            "*.msgpack",
            "flax_model.msgpack",
            "tf_model.h5",
            "rust_model.ot",
            "*.onnx",
        ],
    )
    print("download_complete")


if __name__ == "__main__":
    main()
