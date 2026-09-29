from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_bridge_text_layer_sweep import (  # noqa: E402
    build_layer_config_payload,
    build_matched_loss_plan,
    build_target_loss_plan,
    layer_config_filename,
    parse_checkpoint_filename,
    select_best_checkpoint,
    select_checkpoint_for_target_loss,
)


def test_parse_checkpoint_filename_supports_ema_loss_names():
    meta = parse_checkpoint_filename("epoch-60-i-1800-ema_loss-0.0025")
    assert meta["epoch"] == 60
    assert meta["iter"] == 1800
    assert meta["loss_kind"] == "ema_loss"
    assert meta["loss"] == 0.0025


def test_select_best_checkpoint_picks_lowest_loss_then_earliest_epoch():
    checkpoints = [
        {"name": "epoch-20-i-600-ema_loss-0.0089", "epoch": 20, "iter": 600, "loss": 0.0089, "loss_kind": "ema_loss"},
        {"name": "epoch-30-i-900-ema_loss-0.0072", "epoch": 30, "iter": 900, "loss": 0.0072, "loss_kind": "ema_loss"},
        {"name": "epoch-40-i-1200-ema_loss-0.0072", "epoch": 40, "iter": 1200, "loss": 0.0072, "loss_kind": "ema_loss"},
    ]
    best = select_best_checkpoint(checkpoints)
    assert best["epoch"] == 30
    assert best["loss"] == 0.0072


def test_select_checkpoint_for_target_loss_picks_closest_loss():
    checkpoints = [
        {"name": "epoch-10-i-300-ema_loss-0.0244", "epoch": 10, "iter": 300, "loss": 0.0244, "loss_kind": "ema_loss"},
        {"name": "epoch-20-i-600-ema_loss-0.0089", "epoch": 20, "iter": 600, "loss": 0.0089, "loss_kind": "ema_loss"},
        {"name": "epoch-30-i-900-ema_loss-0.0072", "epoch": 30, "iter": 900, "loss": 0.0072, "loss_kind": "ema_loss"},
    ]
    chosen = select_checkpoint_for_target_loss(checkpoints, target_loss=0.0085)
    assert chosen["epoch"] == 20
    assert chosen["loss"] == 0.0089


def test_select_checkpoint_for_target_loss_prefers_absolute_nearest_loss():
    checkpoints = [
        {"name": "epoch-10-i-300-ema_loss-0.9809", "epoch": 10, "iter": 300, "loss": 0.9809, "loss_kind": "ema_loss"},
        {"name": "epoch-20-i-600-ema_loss-0.0319", "epoch": 20, "iter": 600, "loss": 0.0319, "loss_kind": "ema_loss"},
        {"name": "epoch-30-i-900-ema_loss-0.0271", "epoch": 30, "iter": 900, "loss": 0.0271, "loss_kind": "ema_loss"},
    ]
    chosen = select_checkpoint_for_target_loss(checkpoints, target_loss=0.0375)
    assert chosen["epoch"] == 20
    assert chosen["loss"] == 0.0319


def test_build_matched_loss_plan_uses_max_of_layer_min_losses():
    layer_to_checkpoints = {
        2: [
            {"name": "epoch-20-i-600-ema_loss-0.0120", "epoch": 20, "iter": 600, "loss": 0.0120, "loss_kind": "ema_loss"},
            {"name": "epoch-40-i-1200-ema_loss-0.0090", "epoch": 40, "iter": 1200, "loss": 0.0090, "loss_kind": "ema_loss"},
        ],
        4: [
            {"name": "epoch-20-i-600-ema_loss-0.0150", "epoch": 20, "iter": 600, "loss": 0.0150, "loss_kind": "ema_loss"},
            {"name": "epoch-40-i-1200-ema_loss-0.0060", "epoch": 40, "iter": 1200, "loss": 0.0060, "loss_kind": "ema_loss"},
        ],
    }
    plan = build_matched_loss_plan(layer_to_checkpoints)
    assert plan["target_loss"] == 0.0090
    assert plan["per_layer"][2]["selected"]["epoch"] == 40
    assert plan["per_layer"][4]["selected"]["epoch"] == 40


def test_build_layer_config_payload_overrides_text_layer_only():
    payload = {
        "edit_model_name": "llava-v1.5-7b",
        "edit_layers": [],
        "edit_text_layers": [16],
        "train_cfg": {"lr": 1.0e-4},
        "IT": {"add_it": False},
    }
    updated = build_layer_config_payload(payload, target_layer=24)
    assert updated["edit_layers"] == []
    assert updated["edit_text_layers"] == [24]
    assert payload["edit_text_layers"] == [16]


def test_layer_config_filename_uses_base_model_name_and_two_digit_layer():
    payload = {"edit_model_name": "blip2-opt-2.7b"}
    assert layer_config_filename(payload, 3) == "blip2-opt-2.7b-bridge-text-only-l03.yaml"


def test_build_target_loss_plan_marks_accept_and_miss_target():
    layer_to_checkpoints = {
        0: [
            {"name": "epoch-10-i-300-ema_loss-0.0004", "epoch": 10, "iter": 300, "loss": 0.0004, "loss_kind": "ema_loss"},
        ],
        1: [
            {"name": "epoch-10-i-300-ema_loss-0.0020", "epoch": 10, "iter": 300, "loss": 0.0020, "loss_kind": "ema_loss"},
        ],
    }
    plan = build_target_loss_plan(layer_to_checkpoints, target_loss=0.0003, tolerance=0.0001)
    assert plan["per_layer"][0]["status"] == "ACCEPT"
    assert plan["per_layer"][1]["status"] == "MISS_TARGET"
