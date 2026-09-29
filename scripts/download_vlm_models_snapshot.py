import argparse
import json
import os
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download


DEFAULT_MODELS = [
    ("Qwen/Qwen2.5-VL-3B-Instruct", "Qwen2.5-VL-3B-Instruct"),
    ("google/paligemma2-3b-mix-224", "paligemma2-3b-mix-224"),
    ("mPLUG/mPLUG-Owl3-2B-241014", "mPLUG-Owl3-2B-241014"),
]


def parse_model(raw: str) -> tuple[str, str]:
    if "=" in raw:
        repo_id, local_name = raw.split("=", 1)
        return repo_id.strip(), local_name.strip()
    repo_id = raw.strip()
    return repo_id, repo_id.rsplit("/", 1)[-1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models-dir",
        default="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models",
    )
    parser.add_argument(
        "--model",
        action="append",
        help="repo_id or repo_id=local_dir_name. If omitted, downloads the default three VLMs.",
    )
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()

    models = [parse_model(item) for item in args.model] if args.model else DEFAULT_MODELS
    models_dir = Path(args.models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    api = HfApi()
    summary = []
    for repo_id, local_name in models:
        local_dir = models_dir / local_name
        local_dir.mkdir(parents=True, exist_ok=True)
        print(f"[model-info] {repo_id}", flush=True)
        try:
            info = api.model_info(repo_id)
            gated = getattr(info, "gated", None)
            print(
                json.dumps(
                    {
                        "repo_id": repo_id,
                        "private": info.private,
                        "gated": gated,
                        "sha": info.sha,
                        "local_dir": str(local_dir),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        except Exception as exc:
            print(f"[model-info-error] {repo_id}: {type(exc).__name__}: {exc}", flush=True)

        print(f"[download] {repo_id} -> {local_dir}", flush=True)
        try:
            path = snapshot_download(
                repo_id=repo_id,
                repo_type="model",
                local_dir=str(local_dir),
                max_workers=args.max_workers,
                local_files_only=args.local_files_only,
            )
            marker = local_dir / ".download_complete.json"
            payload = {"repo_id": repo_id, "local_dir": str(local_dir), "snapshot_path": path, "status": "done"}
            marker.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            summary.append(payload)
            print(f"[done] {repo_id} -> {path}", flush=True)
        except Exception as exc:
            payload = {"repo_id": repo_id, "local_dir": str(local_dir), "status": "error", "error": repr(exc)}
            (local_dir / ".download_error.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            summary.append(payload)
            print(f"[download-error] {repo_id}: {type(exc).__name__}: {exc}", flush=True)

    print(json.dumps({"models_dir": str(models_dir), "downloaded": summary}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    main()
