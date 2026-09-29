import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_vlm_adapter_output_lga_scan.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_vlm_adapter_output_lga_scan", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyConfig:
    llm_layer_tmp = "language_model.model.layers.{}"


class BridgeVlmAdapterOutputLgaScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_adapter_layer_path_uses_config_template(self):
        self.assertEqual(
            self.mod.adapter_layer_path(DummyConfig(), 11),
            "language_model.model.layers.11",
        )

    def test_rank_adapter_output_rows_adds_dot_conflict_and_new_norm_ranks(self):
        rows = [
            {
                "layer": 0,
                "S_out_dot": 3.0,
                "S_out_new_norm": 1.0,
                "S_out_cos": 0.2,
                "S_out_joint_norm": 1.0,
            },
            {
                "layer": 1,
                "S_out_dot": -5.0,
                "S_out_new_norm": 9.0,
                "S_out_cos": -0.4,
                "S_out_joint_norm": 4.0,
            },
            {
                "layer": 2,
                "S_out_dot": 1.0,
                "S_out_new_norm": 2.0,
                "S_out_cos": 0.5,
                "S_out_joint_norm": 2.0,
            },
        ]

        ranked = self.mod.rank_adapter_output_rows(rows)
        by_layer = {row["layer"]: row for row in ranked}

        self.assertEqual(by_layer[0]["out_dot_rank"], 1)
        self.assertEqual(by_layer[1]["out_conflict_rank"], 1)
        self.assertEqual(by_layer[1]["out_new_norm_rank"], 1)
        self.assertEqual(by_layer[2]["out_cos_rank"], 1)
        self.assertTrue(by_layer[0]["adapter_output_lga_selected_by_dot"])

    def test_summarize_adapter_output_rows_reports_three_topk_views(self):
        rows = []
        for layer, dot, new_norm, cos in [
            (0, -1.0, 8.0, 0.1),
            (1, 2.0, 2.0, 0.4),
            (2, -5.0, 5.0, -0.2),
            (3, 1.0, 9.0, 0.3),
            (4, 0.0, 1.0, 0.5),
        ]:
            rows.append(
                {
                    "layer": layer,
                    "S_out_dot": dot,
                    "S_out_new_norm": new_norm,
                    "S_out_cos": cos,
                    "S_out_joint_norm": new_norm,
                }
            )
        rows = self.mod.rank_adapter_output_rows(rows)

        summary = self.mod.summarize_adapter_output_rows(rows)

        self.assertEqual(summary["gradient_target"], "adapter_output_delta_h_vis_L")
        self.assertEqual(summary["top_by_out_dot"]["top3"], [1, 3, 4])
        self.assertEqual(summary["top_by_out_conflict_dot"]["top3"], [2, 0, 4])
        self.assertEqual(summary["top_by_out_new_norm"]["top3"], [3, 0, 2])


if __name__ == "__main__":
    unittest.main()
