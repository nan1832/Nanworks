from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge_text_adapter_train import (  # noqa: E402
    _load_vllm_pair,
    build_arg_parser,
    make_run_manifest,
)


def test_scheme2_parser_accepts_bridge_specific_arguments():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--device",
            "cuda:0",
            "--config",
            "DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml",
            "--records_dir",
            "server_results/text-adapter-location/scheme2-l16/records",
            "--manifest_dir",
            "server_results/text-adapter-location/scheme2-l16",
        ]
    )
    assert args.device == "cuda:0"
    assert args.data_path.endswith("edit_30_bridge_train_only_vis.json")
    assert args.bridge_img_root.endswith("Ten_Classes/bridge")
    assert args.coco_img_root.endswith("VisEdit-main/data/easy-edit-mm/images")


def test_scheme2_config_is_text_only_layer16():
    candidates = [
        Path("DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml"),
        Path("configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml"),
    ]
    cfg_path = next((path for path in candidates if path.exists()), candidates[0])
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert "edit_layers: []" in text
    assert "edit_text_layers: [16]" in text
    assert "inf_mapper_lambda: 0.0" in text


def test_make_run_manifest_records_core_scheme2_fields():
    manifest = make_run_manifest(
        train_name="bridge_text_scheme2",
        config_path="DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml",
        data_path="Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json",
        bridge_img_root="Ten_Classes/bridge",
        coco_img_root="VisEdit-main/data/easy-edit-mm/images",
        records_dir="server_results/text-adapter-location/scheme2-l16/records",
        cache_root="server_results/text-adapter-location/scheme2-l16/cache",
        extra_devices=[1],
        single_gpu=False,
        epochs=500,
        batch_size=1,
    )
    assert manifest["experiment"] == "bridge_text_scheme2"
    assert manifest["edit_scope"] == "scheme2_text_only"
    assert manifest["config_path"].endswith("llava-v1.5-7b-bridge-text-only-l16.yaml")
    assert manifest["extra_devices"] == [1]


def test_single_gpu_reuses_same_vllm_instance_for_data_processing():
    calls = []

    def fake_loader(model_name, device):
        calls.append((model_name, device))
        return {"model_name": model_name, "device": device}

    vllm, vllm_data_proc = _load_vllm_pair(
        "llava-v1.5-7b",
        "cuda:0",
        "cuda:0",
        fake_loader,
    )

    assert len(calls) == 1
    assert vllm is vllm_data_proc
    assert vllm["device"] == "cuda:0"


def test_multi_gpu_loads_separate_vllm_instances_for_data_processing():
    calls = []

    def fake_loader(model_name, device):
        calls.append((model_name, device))
        return {"model_name": model_name, "device": device, "call_index": len(calls)}

    vllm, vllm_data_proc = _load_vllm_pair(
        "llava-v1.5-7b",
        "cuda:0",
        "cuda:1",
        fake_loader,
    )

    assert len(calls) == 2
    assert vllm is not vllm_data_proc
    assert vllm["device"] == "cuda:0"
    assert vllm_data_proc["device"] == "cuda:1"
