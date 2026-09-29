import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_vlm_adapter_lga_scan.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_vlm_adapter_lga_scan", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyConfig:
    llm_layer_tmp = "language_model.model.layers.{}"


class BridgeVlmAdapterLgaScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_adapter_layer_path_uses_config_template(self):
        self.assertEqual(
            self.mod.adapter_layer_path(DummyConfig(), 3),
            "language_model.model.layers.3",
        )

    def test_rank_adapter_rows_adds_dot_and_conflict_ranks(self):
        rows = [
            {
                "layer": 0,
                "S_adapter_dot": 2.0,
                "S_adapter_cos": 0.3,
                "adapter_joint_norm": 2.0,
            },
            {
                "layer": 1,
                "S_adapter_dot": -5.0,
                "S_adapter_cos": -0.4,
                "adapter_joint_norm": 10.0,
            },
            {
                "layer": 2,
                "S_adapter_dot": 7.0,
                "S_adapter_cos": 0.1,
                "adapter_joint_norm": 4.0,
            },
        ]
        ranked = self.mod.rank_adapter_rows(rows)
        by_layer = {row["layer"]: row for row in ranked}

        self.assertEqual(by_layer[2]["dot_rank"], 1)
        self.assertTrue(by_layer[2]["adapter_lga_selected_by_dot"])
        self.assertEqual(by_layer[1]["conflict_dot_rank"], 1)
        self.assertEqual(by_layer[1]["conflict_cos_rank"], 1)
        self.assertGreater(by_layer[1]["adapter_norm_ratio"], by_layer[0]["adapter_norm_ratio"])

    def test_summarize_adapter_rows_reports_dot_and_conflict_topk(self):
        rows = self.mod.rank_adapter_rows(
            [
                {
                    "layer": 0,
                    "S_adapter_dot": 2.0,
                    "S_adapter_cos": 0.3,
                    "adapter_joint_norm": 2.0,
                },
                {
                    "layer": 1,
                    "S_adapter_dot": -5.0,
                    "S_adapter_cos": -0.4,
                    "adapter_joint_norm": 10.0,
                },
                {
                    "layer": 2,
                    "S_adapter_dot": 7.0,
                    "S_adapter_cos": 0.1,
                    "adapter_joint_norm": 4.0,
                },
            ]
        )
        summary = self.mod.summarize_adapter_rows(rows)
        self.assertEqual(summary["gradient_target"], "adapter_parameters_phi_L")
        self.assertEqual(summary["top_by_adapter_dot"]["top1"], 2)
        self.assertEqual(summary["top_by_adapter_conflict_dot"]["top1"], 1)
        self.assertEqual(summary["selected_adapter_golden_layer"]["top1"], 2)


if __name__ == "__main__":
    unittest.main()
