from pathlib import Path
import json
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.plot_bridge_text_layer_sweep_loss import (  # noqa: E402
    collect_loss_rows_from_out_root,
    rows_from_inventory_payload,
)


def test_rows_from_inventory_payload_normalizes_layer_and_checkpoint_fields():
    payload = {
        "layer": 12,
        "checkpoints": [
            {"epoch": 10, "iter": 300, "loss": 0.9809, "loss_kind": "ema_loss"},
            {"epoch": 20, "iter": 600, "loss": 0.0319, "loss_kind": "ema_loss"},
        ],
    }
    rows = rows_from_inventory_payload(payload)
    assert rows == [
        {"layer": 12, "epoch": 10, "iter": 300, "loss": 0.9809, "loss_kind": "ema_loss"},
        {"layer": 12, "epoch": 20, "iter": 600, "loss": 0.0319, "loss_kind": "ema_loss"},
    ]


def test_collect_loss_rows_from_out_root_reads_multiple_layer_inventories(tmp_path):
    out_root = tmp_path / "scheme2-layer-sweep-e80-v2"
    for layer, losses in ((2, [0.10, 0.05]), (4, [0.20])):
        layer_dir = out_root / f"layer_{layer:02d}"
        layer_dir.mkdir(parents=True)
        payload = {
            "layer": layer,
            "checkpoint_dir": str(layer_dir / "checkpoints"),
            "checkpoints": [
                {
                    "epoch": (idx + 1) * 10,
                    "iter": (idx + 1) * 300,
                    "loss": loss,
                    "loss_kind": "ema_loss",
                }
                for idx, loss in enumerate(losses)
            ],
        }
        (layer_dir / "checkpoint_inventory.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    rows = collect_loss_rows_from_out_root(out_root)
    assert [(row["layer"], row["epoch"], row["loss"]) for row in rows] == [
        (2, 10, 0.10),
        (2, 20, 0.05),
        (4, 10, 0.20),
    ]
