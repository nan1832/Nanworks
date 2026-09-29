import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_vlm_visual_hidden_lga_scan.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_vlm_visual_hidden_lga_scan", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyConfig:
    llm_layer_tmp = "language_model.model.layers.{}"


class BridgeVlmVisualHiddenLgaScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_visual_layer_path_uses_config_template(self):
        self.assertEqual(
            self.mod.visual_layer_path(DummyConfig(), 7),
            "language_model.model.layers.7",
        )

    def test_rank_visual_rows_adds_expected_ranks(self):
        rows = [
            {
                "layer": 0,
                "S_vis_dot": -3.0,
                "S_vis_new_norm": 4.0,
                "S_vis_cos": -0.3,
                "S_vis_joint_norm": 2.0,
            },
            {
                "layer": 1,
                "S_vis_dot": 2.0,
                "S_vis_new_norm": 2.0,
                "S_vis_cos": 0.1,
                "S_vis_joint_norm": 3.0,
            },
            {
                "layer": 2,
                "S_vis_dot": 1.0,
                "S_vis_new_norm": 8.0,
                "S_vis_cos": 0.5,
                "S_vis_joint_norm": 1.0,
            },
        ]

        ranked = self.mod.rank_visual_rows(rows)
        by_layer = {row["layer"]: row for row in ranked}

        self.assertEqual(by_layer[1]["vis_dot_rank"], 1)
        self.assertEqual(by_layer[2]["vis_new_norm_rank"], 1)
        self.assertEqual(by_layer[2]["vis_cos_rank"], 1)
        self.assertEqual(by_layer[1]["vis_joint_norm_rank"], 1)
        self.assertTrue(by_layer[1]["visual_hidden_lga_selected_by_dot"])

    def test_summarize_visual_rows_reports_dot_and_new_norm_topk(self):
        rows = []
        for layer, dot, new_norm, cos in [
            (0, 0.0, 1.0, 0.1),
            (1, 3.0, 5.0, 0.2),
            (2, 2.0, 7.0, 0.4),
            (3, 1.0, 3.0, 0.3),
            (4, -1.0, 9.0, 0.0),
        ]:
            rows.append(
                {
                    "layer": layer,
                    "S_vis_dot": dot,
                    "S_vis_new_norm": new_norm,
                    "S_vis_cos": cos,
                    "S_vis_joint_norm": new_norm,
                }
            )
        rows = self.mod.rank_visual_rows(rows)

        summary = self.mod.summarize_visual_rows(rows)

        self.assertEqual(summary["gradient_target"], "visual_token_hidden_state_h_vis_L")
        self.assertEqual(summary["top_by_vis_dot"]["top3"], [1, 2, 3])
        self.assertEqual(summary["top_by_vis_new_norm"]["top3"], [4, 2, 1])
        self.assertEqual(summary["top_by_vis_cos"]["top3"], [2, 3, 1])


if __name__ == "__main__":
    unittest.main()
