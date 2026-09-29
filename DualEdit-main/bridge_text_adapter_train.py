import argparse
import json
from pathlib import Path
import re
import shutil
import sys


DEFAULT_DATA_PATH = "Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json"
DEFAULT_BRIDGE_IMG_ROOT = "Ten_Classes/bridge"
DEFAULT_COCO_IMG_ROOT = "VisEdit-main/data/easy-edit-mm/images"
DEFAULT_CONFIG_PATH = "DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml"

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def resolve_existing_path(raw_path):
    path = Path(raw_path)
    if path.exists():
        return path
    anchors = [Path.cwd(), Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
    seen = set()
    for anchor in anchors:
        key = str(anchor)
        if key in seen:
            continue
        seen.add(key)
        candidate = (anchor / path).resolve()
        if candidate.exists():
            return candidate
    return path


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Train the scheme-2 bridge text adapter baseline.")
    parser.add_argument("--device", required=True, help="Primary CUDA device, e.g. cuda:0")
    parser.add_argument(
        "--extra_devices",
        type=int,
        nargs="*",
        default=[1],
        help="Extra CUDA device ids used for preprocessing when available.",
    )
    parser.add_argument("--single_gpu", action="store_true", help="Reuse the main device for data preprocessing.")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--train_name_prefix", default="bridge_text_scheme2")
    parser.add_argument("--save_ckpt_per_i", type=int, default=300)
    parser.add_argument("--log_per_i", type=int, default=10)
    parser.add_argument("--ema_alpha", type=float, default=0.1)
    parser.add_argument("--random_seed", type=int, default=42)
    parser.add_argument("--data_buffer_size", type=int, default=4)
    parser.add_argument("--data_n", type=int, default=None)
    parser.add_argument("--load_ckpt_path", default=None)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--data_path", default=DEFAULT_DATA_PATH)
    parser.add_argument("--bridge_img_root", default=DEFAULT_BRIDGE_IMG_ROOT)
    parser.add_argument("--coco_img_root", default=DEFAULT_COCO_IMG_ROOT)
    parser.add_argument("--records_dir", required=True)
    parser.add_argument("--manifest_dir", required=True)
    parser.add_argument("--cache_root", default=None)
    parser.add_argument("--stop_on_target_loss", action="store_true")
    parser.add_argument("--target_loss", type=float, default=0.0003)
    parser.add_argument("--target_tolerance", type=float, default=0.0001)
    return parser


def make_run_manifest(
    train_name,
    config_path,
    data_path,
    bridge_img_root,
    coco_img_root,
    records_dir,
    cache_root,
    extra_devices,
    single_gpu,
    epochs,
    batch_size,
):
    return {
        "experiment": train_name,
        "edit_scope": "scheme2_text_only",
        "config_path": str(config_path),
        "data_path": str(data_path),
        "bridge_img_root": str(bridge_img_root),
        "coco_img_root": str(coco_img_root),
        "records_dir": str(records_dir),
        "cache_root": None if cache_root is None else str(cache_root),
        "extra_devices": list(extra_devices),
        "single_gpu": bool(single_gpu),
        "epochs": int(epochs),
        "batch_size": int(batch_size),
    }


def _read_yaml(path):
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_data_proc_device(device, extra_devices, single_gpu):
    if single_gpu or not extra_devices:
        return device
    first = extra_devices[0]
    return first if isinstance(first, str) and first.startswith("cuda:") else f"cuda:{first}"


def _find_latest_checkpoint(ckpt_dir):
    ckpt_path = Path(ckpt_dir)
    if not ckpt_path.exists():
        return None
    candidates = [p for p in ckpt_path.iterdir() if p.is_file()]
    if not candidates:
        return None
    return str(max(candidates, key=lambda p: p.stat().st_mtime))


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


CKPT_NAME_RE = re.compile(
    r"^epoch-(?P<epoch>\d+)-i-(?P<iter>\d+)-(?P<kind>ema_loss|loss)-(?P<loss>\d+(?:\.\d+)?)$"
)


def _parse_checkpoint(path):
    match = CKPT_NAME_RE.match(Path(path).name)
    if not match:
        return None
    groups = match.groupdict()
    return {
        "path": str(path),
        "name": Path(path).name,
        "epoch": int(groups["epoch"]),
        "iter": int(groups["iter"]),
        "loss": float(groups["loss"]),
        "kind": groups["kind"],
    }


def _collect_checkpoints(ckpt_dir):
    root = Path(ckpt_dir)
    checkpoints = []
    if root.exists():
        for path in root.iterdir():
            if not path.is_file():
                continue
            meta = _parse_checkpoint(path)
            if meta:
                checkpoints.append(meta)
    return sorted(checkpoints, key=lambda item: (item["epoch"], item["iter"], item["loss"]))


def _checkpoint_sort_key(meta):
    return (meta["epoch"], meta["iter"], meta["loss"])


def _prune_checkpoints_for_training(ckpt_dir, target_loss, keep_selected_path=None, keep_latest=True):
    checkpoints = _collect_checkpoints(ckpt_dir)
    if not checkpoints:
        return {"kept": [], "removed": []}

    keep = set()
    if keep_selected_path:
        keep.add(str(Path(keep_selected_path).resolve()))
    if keep_latest:
        keep.add(str(Path(max(checkpoints, key=_checkpoint_sort_key)["path"]).resolve()))
    closest = min(checkpoints, key=lambda item: (abs(item["loss"] - target_loss), item["epoch"], item["iter"]))
    keep.add(str(Path(closest["path"]).resolve()))

    removed = []
    kept = []
    for meta in checkpoints:
        path = Path(meta["path"])
        resolved = str(path.resolve())
        if resolved in keep:
            kept.append(str(path))
            continue
        try:
            path.unlink()
            removed.append(str(path))
        except FileNotFoundError:
            pass
    return {"kept": kept, "removed": removed}


def _looks_like_storage_error(err):
    text = str(err).lower()
    markers = [
        "no space left",
        "pytorchstreamwriter",
        "inline_container",
        "unexpected pos",
        "failed writing file",
        "enforce fail",
        "storages",
    ]
    return any(marker in text for marker in markers)


def _install_target_checkpoint_callbacks(editor, args, manifest_dir):
    if not getattr(args, "stop_on_target_loss", False):
        return

    target_loss = float(args.target_loss)
    tolerance = float(args.target_tolerance)
    progress_path = Path(manifest_dir) / "target_hit_progress.json"

    def write_event(event):
        payload = {"target_loss": target_loss, "target_tolerance": tolerance, "events": []}
        if progress_path.exists():
            try:
                payload = json.loads(progress_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        payload.setdefault("events", []).append(event)
        _write_json(progress_path, payload)

    def after_save(ckpt_path, train_i, epoch, loss, ema_loss):
        loss_value = float(ema_loss if ema_loss is not None else loss)
        diff = abs(loss_value - target_loss)
        hit = diff <= tolerance + 1e-12
        prune_report = _prune_checkpoints_for_training(
            editor.save_ckpt_dir,
            target_loss=target_loss,
            keep_selected_path=ckpt_path if hit else None,
            keep_latest=not hit,
        )
        event = {
            "type": "checkpoint_saved",
            "checkpoint": str(ckpt_path),
            "epoch": int(epoch),
            "iter": int(train_i),
            "loss": loss_value,
            "diff": diff,
            "status": "ACCEPT" if hit else "CONTINUE",
            "prune_report": prune_report,
        }
        write_event(event)
        return hit

    def on_save_error(ckpt_path, err):
        if not _looks_like_storage_error(err):
            raise err
        prune_report = _prune_checkpoints_for_training(
            editor.save_ckpt_dir,
            target_loss=target_loss,
            keep_selected_path=None,
            keep_latest=True,
        )
        write_event(
            {
                "type": "checkpoint_save_error_cleanup",
                "checkpoint": str(ckpt_path),
                "error": str(err),
                "prune_report": prune_report,
            }
        )

    editor.after_save_ckpt_callback = after_save
    editor.handle_checkpoint_save_error = on_save_error
    editor.validate_checkpoint_after_save = True


def _load_edit_bridge_class():
    from dataset.edit_bridge_loader import EditBridge

    return EditBridge


def _load_vllm_pair(edit_model_name, device, data_proc_device, load_vllm_for_edit):
    vllm = load_vllm_for_edit(edit_model_name, device)
    if data_proc_device == device:
        return vllm, vllm
    vllm_data_proc = load_vllm_for_edit(edit_model_name, data_proc_device)
    return vllm, vllm_data_proc


def run_training(args):
    from editor.vllm_editors.vead.vead import VEAD, VEADConfig
    from utils import get_full_model_name, load_vllm_for_edit
    EditBridge = _load_edit_bridge_class()

    config_path = resolve_existing_path(args.config)
    data_path = resolve_existing_path(args.data_path)
    bridge_img_root = resolve_existing_path(args.bridge_img_root)
    coco_img_root = resolve_existing_path(args.coco_img_root)
    records_dir = Path(args.records_dir)
    manifest_dir = Path(args.manifest_dir)
    cache_root = Path(args.cache_root) if args.cache_root else resolve_existing_path("DualEdit-main/data")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)

    train_cfg = _read_yaml(config_path)
    edit_model_name = get_full_model_name(train_cfg["edit_model_name"])
    data_proc_device = _resolve_data_proc_device(args.device, args.extra_devices, args.single_gpu)

    manifest = make_run_manifest(
        train_name=args.train_name_prefix,
        config_path=config_path,
        data_path=data_path,
        bridge_img_root=bridge_img_root,
        coco_img_root=coco_img_root,
        records_dir=records_dir,
        cache_root=cache_root,
        extra_devices=[] if args.single_gpu else args.extra_devices,
        single_gpu=args.single_gpu,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
    _write_json(manifest_dir / "run_manifest.json", manifest)

    editor_cfg = VEADConfig.from_yaml(config_path)
    vllm, vllm_data_proc = _load_vllm_pair(
        edit_model_name,
        args.device,
        data_proc_device,
        load_vllm_for_edit,
    )
    editor = VEAD(
        vllm,
        editor_cfg,
        args.device,
        vllm_data_proc=vllm_data_proc,
        data_proc_device=data_proc_device,
        train_data_cache_root=str(cache_root),
    )

    train_data = EditBridge(
        data_path=str(data_path),
        img_root_dir=str(bridge_img_root),
        coco_img_dir=str(coco_img_root),
        data_n=args.data_n,
    )
    editor.train_init(
        train_data,
        args.batch_size,
        records_dir=str(records_dir),
        train_name_prefix=args.train_name_prefix,
        load_ckpt_path=args.load_ckpt_path,
        save_ckpt_per_i=args.save_ckpt_per_i,
        log_per_i=args.log_per_i,
        ema_alpha=args.ema_alpha,
        random_seed=args.random_seed,
        data_buffer_size=args.data_buffer_size,
        edit_model_name=edit_model_name,
        train_cfg=train_cfg,
        dataset_name=train_data.dataset_name(),
    )
    _install_target_checkpoint_callbacks(editor, args, manifest_dir)
    editor.train(args.epochs)

    manifest["resolved_save_ckpt_dir"] = editor.save_ckpt_dir
    manifest["latest_checkpoint"] = _find_latest_checkpoint(editor.save_ckpt_dir)
    manifest["train_data_cache_dir"] = editor.train_data_cache_dir
    _write_json(manifest_dir / "run_manifest.json", manifest)
    return manifest


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    run_training(args)


if __name__ == "__main__":
    main()
