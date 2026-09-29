import argparse
from copy import deepcopy
import gc
import json
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bridge_text_adapter_train import run_training  # noqa: E402
from scripts.eval_bridge_text_adapter_ckpt import run_evaluation  # noqa: E402


DEFAULT_LAYERS = list(range(2, 31, 2))
DEFAULT_BASE_CONFIG = "configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml"
DEFAULT_DATA_PATH = "Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json"
DEFAULT_BRIDGE_IMG_ROOT = "Ten_Classes/bridge"
DEFAULT_COCO_IMG_ROOT = "VisEdit-main/data/easy-edit-mm/images"
DEFAULT_OUT_ROOT = "server_results/text-adapter-location/scheme2-layer-sweep-e80"
CHECKPOINT_RE = re.compile(
    r"^epoch-(?P<epoch>\d+)-i-(?P<iter>\d+)-(?P<loss_kind>ema_loss|loss)-(?P<loss>\d+(?:\.\d+)?)$"
)


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


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_yaml(path):
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path, payload):
    import yaml

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


def build_layer_config_payload(base_payload, target_layer):
    payload = deepcopy(base_payload)
    payload["edit_layers"] = []
    payload["edit_text_layers"] = [int(target_layer)]
    return payload


def layer_config_filename(base_payload, target_layer):
    model_name = str(base_payload.get("edit_model_name", "model")).replace("/", "-")
    return f"{model_name}-bridge-text-only-l{int(target_layer):02d}.yaml"


def parse_checkpoint_filename(name):
    match = CHECKPOINT_RE.match(str(name))
    if not match:
        raise ValueError(f"Unsupported checkpoint filename: {name}")
    meta = match.groupdict()
    return {
        "name": str(name),
        "epoch": int(meta["epoch"]),
        "iter": int(meta["iter"]),
        "loss_kind": meta["loss_kind"],
        "loss": float(meta["loss"]),
    }


def collect_checkpoints(checkpoint_dir):
    checkpoint_dir = Path(checkpoint_dir)
    if not checkpoint_dir.exists():
        return []
    items = []
    for path in checkpoint_dir.iterdir():
        if not path.is_file():
            continue
        try:
            meta = parse_checkpoint_filename(path.name)
        except ValueError:
            continue
        meta["path"] = str(path)
        items.append(meta)
    return sorted(items, key=lambda item: (item["epoch"], item["iter"], item["loss"]))


def select_best_checkpoint(checkpoints):
    if not checkpoints:
        raise ValueError("No checkpoints available for best-loss selection.")
    return min(checkpoints, key=lambda item: (item["loss"], item["epoch"], item["iter"]))


def select_checkpoint_for_target_loss(checkpoints, target_loss):
    if not checkpoints:
        raise ValueError("No checkpoints available for matched-loss selection.")
    return min(
        checkpoints,
        key=lambda item: (
            abs(item["loss"] - target_loss),
            item["epoch"],
            item["iter"],
            item["loss"],
        ),
    )


def build_matched_loss_plan(layer_to_checkpoints):
    if not layer_to_checkpoints:
        raise ValueError("No layer checkpoints provided.")
    per_layer = {}
    best_losses = {}
    for layer, checkpoints in layer_to_checkpoints.items():
        best = select_best_checkpoint(checkpoints)
        per_layer[layer] = {"best": best}
        best_losses[layer] = best["loss"]
    target_loss = max(best_losses.values())
    for layer, checkpoints in layer_to_checkpoints.items():
        per_layer[layer]["selected"] = select_checkpoint_for_target_loss(checkpoints, target_loss)
    return {
        "selection": "matched",
        "target_loss": target_loss,
        "per_layer": per_layer,
    }


def build_best_loss_plan(layer_to_checkpoints):
    if not layer_to_checkpoints:
        raise ValueError("No layer checkpoints provided.")
    per_layer = {}
    for layer, checkpoints in layer_to_checkpoints.items():
        per_layer[layer] = {"selected": select_best_checkpoint(checkpoints)}
    return {"selection": "best", "per_layer": per_layer}


def build_target_loss_plan(layer_to_checkpoints, target_loss, tolerance):
    if not layer_to_checkpoints:
        raise ValueError("No layer checkpoints provided.")
    per_layer = {}
    for layer, checkpoints in layer_to_checkpoints.items():
        selected = select_checkpoint_for_target_loss(checkpoints, target_loss)
        diff = abs(selected["loss"] - target_loss)
        per_layer[layer] = {
            "selected": selected,
            "target_loss": float(target_loss),
            "diff": diff,
            "status": "ACCEPT" if diff <= tolerance + 1e-12 else "MISS_TARGET",
            "tolerance": float(tolerance),
        }
    return {
        "selection": "target0003",
        "target_loss": float(target_loss),
        "tolerance": float(tolerance),
        "per_layer": per_layer,
    }


def checkpoint_epoch(checkpoint):
    return int(checkpoint["epoch"])


def latest_checkpoint(checkpoints):
    if not checkpoints:
        raise ValueError("No checkpoints available for latest selection.")
    return max(checkpoints, key=lambda item: (item["epoch"], item["iter"]))


def _cleanup_torch_state():
    try:
        import torch
    except ImportError:
        return
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _make_layer_tag(layer):
    return f"layer_{int(layer):02d}"


def _render_layer_config(base_config_path, generated_config_dir, layer):
    base_payload = _read_yaml(base_config_path)
    payload = build_layer_config_payload(base_payload, layer)
    config_path = Path(generated_config_dir) / layer_config_filename(base_payload, layer)
    _write_yaml(config_path, payload)
    return config_path


def _make_train_args(args, layer, config_path, layer_root, epochs=None, load_ckpt_path=None):
    return SimpleNamespace(
        device=args.device,
        extra_devices=args.extra_devices,
        single_gpu=args.single_gpu,
        batch_size=args.batch_size,
        epochs=args.epochs if epochs is None else int(epochs),
        train_name_prefix=f"{args.train_name_prefix}_l{int(layer):02d}",
        save_ckpt_per_i=args.save_ckpt_per_i,
        log_per_i=args.log_per_i,
        ema_alpha=args.ema_alpha,
        random_seed=args.random_seed,
        data_buffer_size=args.data_buffer_size,
        data_n=args.data_n,
        load_ckpt_path=load_ckpt_path,
        stop_on_target_loss=bool(args.train_until_target),
        target_loss=args.target_loss,
        target_tolerance=args.target_tolerance,
        config=str(config_path),
        data_path=str(args.data_path),
        bridge_img_root=str(args.bridge_img_root),
        coco_img_root=str(args.coco_img_root),
        records_dir=str(layer_root / "records"),
        manifest_dir=str(layer_root),
        cache_root=str(layer_root / "cache"),
    )


def _make_eval_args(args, config_path, checkpoint_path, out_dir):
    return SimpleNamespace(
        device=args.device,
        ckpt=str(checkpoint_path),
        config=str(config_path),
        data_path=str(args.data_path),
        bridge_img_root=str(args.bridge_img_root),
        coco_img_root=str(args.coco_img_root),
        out_dir=str(out_dir),
        data_n=args.eval_data_n,
        max_new_tokens=args.max_new_tokens,
    )


def _collect_layer_outputs(out_root, layer):
    layer_root = Path(out_root) / _make_layer_tag(layer)
    checkpoint_dir = layer_root / "records"
    candidates = list(checkpoint_dir.glob("vead/*/*/checkpoints"))
    if not candidates:
        raise FileNotFoundError(f"No checkpoint directory found under {checkpoint_dir}")
    if len(candidates) > 1:
        candidates = sorted(candidates)
    checkpoints = collect_checkpoints(candidates[0])
    if not checkpoints:
        raise FileNotFoundError(f"No checkpoint files found under {candidates[0]}")
    return layer_root, candidates[0], checkpoints


def _find_generated_config(out_root, base_config_path, layer):
    generated_dir = Path(out_root) / "generated_configs"
    base_payload = _read_yaml(base_config_path)
    expected = generated_dir / layer_config_filename(base_payload, layer)
    if expected.exists():
        return expected
    candidates = sorted(generated_dir.glob(f"*bridge-text-only-l{int(layer):02d}.yaml"))
    if candidates:
        return candidates[0]
    return resolve_existing_path(base_config_path)


def _write_checkpoint_tsv(path, plan):
    lines = ["layer\tstatus\tepoch\tema_loss\tdiff\tcheckpoint\tpath"]
    target_loss = plan.get("target_loss")
    for raw_layer in sorted(plan["per_layer"], key=lambda value: int(value)):
        item = plan["per_layer"][raw_layer]
        selected = item["selected"]
        diff = item.get("diff")
        if diff is None and target_loss is not None:
            diff = abs(float(selected["loss"]) - float(target_loss))
        status = item.get("status", "SELECTED")
        diff_text = "" if diff is None else f"{float(diff):.6f}"
        lines.append(
            "\t".join(
                [
                    str(raw_layer),
                    status,
                    str(selected["epoch"]),
                    f"{float(selected['loss']):.6f}",
                    diff_text,
                    selected["name"],
                    selected["path"],
                ]
            )
        )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cleanup_unselected_checkpoints(layer_to_checkpoints, plans):
    keep_paths = set()
    for checkpoints in layer_to_checkpoints.values():
        if checkpoints:
            keep_paths.add(Path(latest_checkpoint(checkpoints)["path"]).resolve())
    for plan in plans.values():
        for item in plan["per_layer"].values():
            keep_paths.add(Path(item["selected"]["path"]).resolve())

    removed = []
    for checkpoints in layer_to_checkpoints.values():
        for checkpoint in checkpoints:
            path = Path(checkpoint["path"])
            try:
                resolved = path.resolve()
            except FileNotFoundError:
                continue
            if resolved in keep_paths or not path.is_file():
                continue
            path.unlink()
            removed.append(str(path))
    return removed


def _prune_layer_checkpoints(checkpoints, target_loss, retain_recent, retain_epoch_interval):
    if not checkpoints:
        return {"kept": [], "removed": []}

    keep_paths = set()
    keep_paths.add(Path(latest_checkpoint(checkpoints)["path"]).resolve())
    keep_paths.add(Path(select_best_checkpoint(checkpoints)["path"]).resolve())
    keep_paths.add(Path(select_checkpoint_for_target_loss(checkpoints, target_loss)["path"]).resolve())

    if retain_recent > 0:
        for checkpoint in sorted(checkpoints, key=lambda item: (item["epoch"], item["iter"]))[-retain_recent:]:
            keep_paths.add(Path(checkpoint["path"]).resolve())

    if retain_epoch_interval > 0:
        for checkpoint in checkpoints:
            if int(checkpoint["epoch"]) % retain_epoch_interval == 0:
                keep_paths.add(Path(checkpoint["path"]).resolve())

    removed = []
    kept = []
    for checkpoint in checkpoints:
        path = Path(checkpoint["path"])
        try:
            resolved = path.resolve()
        except FileNotFoundError:
            continue
        if resolved in keep_paths:
            kept.append(str(path))
            continue
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    return {"kept": kept, "removed": removed}


def _cleanup_layer_cache(layer_root):
    cache_dir = Path(layer_root) / "cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        return str(cache_dir)
    return None


def _prune_to_selected_checkpoint(checkpoints, selected_path):
    selected = str(Path(selected_path).resolve())
    removed = []
    kept = []
    for checkpoint in checkpoints:
        path = Path(checkpoint["path"])
        try:
            resolved = str(path.resolve())
        except FileNotFoundError:
            continue
        if resolved == selected:
            kept.append(str(path))
            continue
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    return {"kept": kept, "removed": removed}


def _train_one_layer(args, layer, config_path, layer_root, epochs, load_ckpt_path=None):
    manifest = run_training(
        _make_train_args(
            args,
            layer,
            config_path,
            layer_root,
            epochs=epochs,
            load_ckpt_path=load_ckpt_path,
        )
    )
    manifest["layer"] = int(layer)
    manifest["generated_config_path"] = str(config_path)
    manifest["requested_total_epochs"] = int(epochs)
    manifest["load_ckpt_path"] = load_ckpt_path
    _write_json(layer_root / "training_manifest.json", manifest)
    _cleanup_torch_state()
    return manifest


def _train_layer_until_target(args, layer, config_path, layer_root):
    total_epochs = int(args.epochs)
    load_ckpt_path = None
    progress = []
    while True:
        manifest = _train_one_layer(
            args,
            layer,
            config_path,
            layer_root,
            epochs=total_epochs,
            load_ckpt_path=load_ckpt_path,
        )
        _, _, checkpoints = _collect_layer_outputs(args.out_root, layer)
        plan = build_target_loss_plan(
            {int(layer): checkpoints},
            target_loss=args.target_loss,
            tolerance=args.target_tolerance,
        )
        selected = plan["per_layer"][int(layer)]["selected"]
        status = plan["per_layer"][int(layer)]["status"]
        progress.append(
            {
                "trained_to_epoch": total_epochs,
                "status": status,
                "selected": selected,
                "latest": latest_checkpoint(checkpoints),
                "manifest": manifest,
            }
        )
        if args.prune_checkpoints_during_train:
            if status == "ACCEPT":
                prune_report = _prune_to_selected_checkpoint(checkpoints, selected["path"])
            else:
                prune_report = _prune_layer_checkpoints(
                    checkpoints,
                    target_loss=args.target_loss,
                    retain_recent=args.retain_recent_checkpoints,
                    retain_epoch_interval=args.retain_epoch_interval,
                )
            progress[-1]["prune_report"] = prune_report
        _write_json(layer_root / "target0003_progress.json", {"layer": int(layer), "progress": progress})
        if status == "ACCEPT" or total_epochs >= args.max_epochs:
            break
        _, _, checkpoints_after_prune = _collect_layer_outputs(args.out_root, layer)
        load_ckpt_path = latest_checkpoint(checkpoints_after_prune)["path"]
        total_epochs = min(total_epochs + args.continue_increment, args.max_epochs)
    if args.cleanup_layer_cache:
        removed_cache = _cleanup_layer_cache(layer_root)
        if removed_cache:
            progress[-1]["removed_cache_dir"] = removed_cache
            _write_json(layer_root / "target0003_progress.json", {"layer": int(layer), "progress": progress})
    return progress[-1]["manifest"]


def train_layers(args):
    out_root = Path(args.out_root)
    layer_manifests = {}
    for layer in args.layers:
        layer_root = out_root / _make_layer_tag(layer)
        layer_root.mkdir(parents=True, exist_ok=True)
        config_path = _render_layer_config(args.base_config, out_root / "generated_configs", layer)
        if args.train_until_target:
            manifest = _train_layer_until_target(args, layer, config_path, layer_root)
        else:
            manifest = _train_one_layer(args, layer, config_path, layer_root, epochs=args.epochs)
            if args.prune_checkpoints_during_train:
                _, _, checkpoints = _collect_layer_outputs(args.out_root, layer)
                prune_report = _prune_layer_checkpoints(
                    checkpoints,
                    target_loss=args.target_loss,
                    retain_recent=args.retain_recent_checkpoints,
                    retain_epoch_interval=args.retain_epoch_interval,
                )
                _write_json(layer_root / "prune_report.json", prune_report)
            if args.cleanup_layer_cache:
                removed_cache = _cleanup_layer_cache(layer_root)
                if removed_cache:
                    _write_json(layer_root / "cache_cleanup.json", {"removed_cache_dir": removed_cache})
        layer_manifests[int(layer)] = manifest
    return layer_manifests


def collect_layer_checkpoints(args):
    out_root = Path(args.out_root)
    layer_to_checkpoints = {}
    layer_to_config = {}
    layer_to_root = {}
    for layer in args.layers:
        layer_root, checkpoint_dir, checkpoints = _collect_layer_outputs(out_root, layer)
        config_path = _find_generated_config(out_root, args.base_config, layer)
        layer_to_checkpoints[int(layer)] = checkpoints
        layer_to_config[int(layer)] = str(config_path)
        layer_to_root[int(layer)] = str(layer_root)
        _write_json(
            layer_root / "checkpoint_inventory.json",
            {
                "layer": int(layer),
                "checkpoint_dir": str(checkpoint_dir),
                "checkpoints": checkpoints,
            },
        )
    return layer_to_checkpoints, layer_to_config, layer_to_root


def evaluate_selection_plan(args, selection_name, selection_plan, layer_to_config, layer_to_root):
    results = {
        "selection": selection_name,
        "target_loss": selection_plan.get("target_loss"),
        "per_layer": {},
    }
    for layer, layer_plan in selection_plan["per_layer"].items():
        selected = layer_plan["selected"]
        layer_root = Path(layer_to_root[layer])
        out_dir = layer_root / f"eval_{selection_name}"
        eval_summary = run_evaluation(
            _make_eval_args(
                args,
                config_path=layer_to_config[layer],
                checkpoint_path=selected["path"],
                out_dir=out_dir,
            )
        )
        result = {
            "selected_checkpoint": selected,
            "eval_out_dir": str(out_dir),
            "summary_path": str(out_dir / "summary.json"),
            "metrics": eval_summary,
        }
        if "best" in layer_plan:
            result["best_checkpoint"] = layer_plan["best"]
        results["per_layer"][layer] = result
        _cleanup_torch_state()
    return results


def run_layer_sweep(args):
    args.base_config = resolve_existing_path(args.base_config)
    args.data_path = resolve_existing_path(args.data_path)
    args.bridge_img_root = resolve_existing_path(args.bridge_img_root)
    args.coco_img_root = resolve_existing_path(args.coco_img_root)
    Path(args.out_root).mkdir(parents=True, exist_ok=True)
    generated_config_dir = Path(args.out_root) / "generated_configs"
    generated_config_dir.mkdir(parents=True, exist_ok=True)
    for layer in args.layers:
        _render_layer_config(args.base_config, generated_config_dir, layer)

    run_manifest = {
        "layers": list(map(int, args.layers)),
        "epochs": int(args.epochs),
        "max_epochs": int(args.max_epochs),
        "continue_increment": int(args.continue_increment),
        "target_loss": float(args.target_loss),
        "target_tolerance": float(args.target_tolerance),
        "train_until_target": bool(args.train_until_target),
        "device": args.device,
        "single_gpu": bool(args.single_gpu),
        "base_config": str(args.base_config),
        "data_path": str(args.data_path),
        "bridge_img_root": str(args.bridge_img_root),
        "coco_img_root": str(args.coco_img_root),
        "selection_modes": list(args.selection_modes),
    }
    _write_json(Path(args.out_root) / "layer_sweep_manifest.json", run_manifest)

    if not args.skip_train:
        train_layers(args)

    layer_to_checkpoints, layer_to_config, layer_to_root = collect_layer_checkpoints(args)
    best_plan = build_best_loss_plan(layer_to_checkpoints)
    matched_plan = build_matched_loss_plan(layer_to_checkpoints)
    target_plan = build_target_loss_plan(
        layer_to_checkpoints,
        target_loss=args.target_loss,
        tolerance=args.target_tolerance,
    )
    plans = {
        "best": best_plan,
        "matched": matched_plan,
        "target0003": target_plan,
    }

    for name, plan in plans.items():
        _write_json(Path(args.out_root) / f"{name}_ckpt_summary.json", plan)
        _write_checkpoint_tsv(Path(args.out_root) / f"{name}_ckpt_summary.tsv", plan)

    if args.cleanup_unselected_checkpoints:
        removed = _cleanup_unselected_checkpoints(layer_to_checkpoints, plans)
        _write_json(Path(args.out_root) / "cleanup_unselected_checkpoints.json", {"removed": removed})

    reports = {}
    for selection_name in args.selection_modes:
        if args.skip_eval:
            continue
        reports[selection_name] = evaluate_selection_plan(
            args, selection_name, plans[selection_name], layer_to_config, layer_to_root
        )
        _write_json(Path(args.out_root) / f"{selection_name}_eval_report.json", reports[selection_name])
    return reports


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Train and evaluate a scheme-2 bridge text-adapter sweep across multiple text edit layers."
    )
    parser.add_argument("--device", required=True, help="Primary CUDA device, e.g. cuda:0")
    parser.add_argument("--layers", type=int, nargs="*", default=DEFAULT_LAYERS)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--max_epochs", type=int, default=700)
    parser.add_argument("--continue_increment", type=int, default=20)
    parser.add_argument("--target_loss", type=float, default=0.0003)
    parser.add_argument("--target_tolerance", type=float, default=0.0001)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--base_config", default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--data_path", default=DEFAULT_DATA_PATH)
    parser.add_argument("--bridge_img_root", default=DEFAULT_BRIDGE_IMG_ROOT)
    parser.add_argument("--coco_img_root", default=DEFAULT_COCO_IMG_ROOT)
    parser.add_argument("--out_root", default=DEFAULT_OUT_ROOT)
    parser.add_argument("--train_name_prefix", default="bridge_text_scheme2")
    parser.add_argument("--save_ckpt_per_i", type=int, default=300)
    parser.add_argument("--log_per_i", type=int, default=10)
    parser.add_argument("--ema_alpha", type=float, default=0.1)
    parser.add_argument("--random_seed", type=int, default=42)
    parser.add_argument("--data_buffer_size", type=int, default=4)
    parser.add_argument("--data_n", type=int, default=None)
    parser.add_argument("--eval_data_n", type=int, default=None)
    parser.add_argument("--max_new_tokens", type=int, default=32)
    parser.add_argument("--extra_devices", type=int, nargs="*", default=[1])
    parser.add_argument("--single_gpu", action="store_true")
    parser.add_argument("--skip_train", action="store_true")
    parser.add_argument("--skip_eval", action="store_true")
    parser.add_argument("--train_until_target", action="store_true")
    parser.add_argument("--cleanup_unselected_checkpoints", action="store_true")
    parser.add_argument("--prune_checkpoints_during_train", action="store_true")
    parser.add_argument("--retain_recent_checkpoints", type=int, default=3)
    parser.add_argument("--retain_epoch_interval", type=int, default=20)
    parser.add_argument("--cleanup_layer_cache", action="store_true")
    parser.add_argument(
        "--selection_modes",
        nargs="*",
        choices=["best", "matched", "target0003"],
        default=["best", "matched", "target0003"],
    )
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    run_layer_sweep(args)


if __name__ == "__main__":
    main()
