import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_vlm_relgenloc_adapter_gla_scan.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_vlm_relgenloc_adapter_gla_scan", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeVlmRelGenLocAdapterGlaScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_short_model_name_maps_supported_models(self):
        self.assertEqual(self.mod.short_model_name("llava-v1.5-7b"), "llava")
        self.assertEqual(self.mod.short_model_name("blip2-opt-2.7b"), "blip2")

    def test_rank_relgenloc_rows_adds_expected_ranks(self):
        rows = [
            {
                "layer": 0,
                "S_total_norm": 3.0,
                "S_total_dot": -2.0,
                "S_total_cos": 0.2,
                "S_eg_conflict": 9.0,
                "S_entity_norm": 1.0,
                "S_generality_norm": 2.0,
                "S_locality_norm": 3.0,
            },
            {
                "layer": 1,
                "S_total_norm": 7.0,
                "S_total_dot": 4.0,
                "S_total_cos": 0.1,
                "S_eg_conflict": 1.0,
                "S_entity_norm": 9.0,
                "S_generality_norm": 1.0,
                "S_locality_norm": 2.0,
            },
            {
                "layer": 2,
                "S_total_norm": 1.0,
                "S_total_dot": 1.0,
                "S_total_cos": 0.8,
                "S_eg_conflict": 4.0,
                "S_entity_norm": 2.0,
                "S_generality_norm": 8.0,
                "S_locality_norm": 1.0,
            },
        ]

        ranked = self.mod.rank_relgenloc_rows(rows)
        by_layer = {row["layer"]: row for row in ranked}

        self.assertEqual(by_layer[1]["total_norm_rank"], 1)
        self.assertEqual(by_layer[1]["total_dot_rank"], 1)
        self.assertEqual(by_layer[2]["total_cos_rank"], 1)
        self.assertEqual(by_layer[0]["eg_conflict_rank"], 1)
        self.assertEqual(by_layer[1]["entity_norm_rank"], 1)
        self.assertEqual(by_layer[2]["generality_norm_rank"], 1)

    def test_summarize_excludes_zero_grad_from_candidate_pool(self):
        rows = []
        for layer, norm, cos, conflict, zero_grad in [
            (0, 0.0, 0.9, 10.0, True),
            (1, 7.0, 0.2, 1.0, False),
            (2, 3.0, 0.8, 8.0, False),
            (3, 2.0, 0.7, 9.0, False),
            (4, 1.0, 0.6, 2.0, False),
        ]:
            rows.append(
                {
                    "layer": layer,
                    "S_total_norm": norm,
                    "S_total_dot": norm,
                    "S_total_cos": cos,
                    "S_eg_conflict": conflict,
                    "S_entity_norm": norm,
                    "S_generality_norm": norm,
                    "S_locality_norm": norm,
                    "zero_grad_flag": zero_grad,
                }
            )
        rows = self.mod.rank_relgenloc_rows(rows)

        summary = self.mod.summarize_relgenloc_rows(rows)

        self.assertEqual(summary["main_score"], "S_total_norm")
        self.assertEqual(summary["primary_total_norm_topk"][0], 1)
        self.assertIn(0, summary["zero_grad_layers"])
        self.assertNotIn(0, summary["recommended_candidate_pool"])
        self.assertIn(2, summary["recommended_candidate_pool"])


if __name__ == "__main__":
    unittest.main()
