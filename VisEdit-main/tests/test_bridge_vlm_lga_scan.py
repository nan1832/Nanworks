import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_vlm_lga_scan.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_vlm_lga_scan", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeVlmLgaScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_parse_layers_accepts_ranges_and_singletons(self):
        self.assertEqual(self.mod.parse_layers("0,2-4,8"), [0, 2, 3, 4, 8])

    def test_parse_layers_rejects_descending_ranges(self):
        with self.assertRaises(ValueError):
            self.mod.parse_layers("4-2")

    def test_answer_stub_is_appended_once(self):
        prompt = "What is the name of this bridge?"
        with_stub = self.mod.ensure_answer_stub(prompt)
        unchanged = self.mod.ensure_answer_stub(with_stub)
        self.assertEqual(with_stub, "What is the name of this bridge? The answer is:")
        self.assertEqual(unchanged, with_stub)

    def test_gradient_similarity_returns_dot_cos_and_norms(self):
        stats = self.mod.gradient_similarity([1.0, 2.0], [3.0, 4.0])
        self.assertAlmostEqual(stats["dot"], 11.0)
        self.assertAlmostEqual(stats["old_norm"], 5.0 ** 0.5)
        self.assertAlmostEqual(stats["new_norm"], 25.0 ** 0.5)
        self.assertAlmostEqual(stats["joint_grad_norm"], (5.0 ** 0.5) * 5.0)
        self.assertAlmostEqual(stats["cos"], 11.0 / (((5.0 ** 0.5) * 5.0) + self.mod.EPS))

    def test_rank_rows_uses_dot_as_selected_lga_layer(self):
        rows = [
            {"layer": 0, "S_lga_dot": 2.0, "S_lga_cos": 0.9, "joint_grad_norm": 2.0},
            {"layer": 1, "S_lga_dot": 5.0, "S_lga_cos": 0.1, "joint_grad_norm": 10.0},
        ]
        ranked = self.mod.rank_rows(rows)
        self.assertEqual(ranked[0]["layer"], 1)
        self.assertTrue(ranked[0]["lga_selected_by_dot"])
        self.assertEqual(ranked[0]["dot_rank"], 1)
        self.assertEqual(ranked[0]["cos_rank"], 2)

    def test_load_bridge_samples_maps_old_answer_by_image_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "bridge_train" / "bridge_images"
            image_dir.mkdir(parents=True)
            Image.new("RGB", (2, 2), color=(255, 0, 0)).save(image_dir / "GLDv2_test.jpg")
            data_path = root / "edit.json"
            data_path.write_text(
                json.dumps(
                    [
                        {
                            "case_id": "train_0",
                            "entity_name": "Target Bridge",
                            "request": {
                                "image": "train/images/GLDv2_test.jpg",
                                "prompt": "What is the name of this bridge?",
                                "target_new": "Target Bridge",
                            },
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            old_path = root / "old.jsonl"
            old_path.write_text(
                json.dumps(
                    {
                        "image_id": "GLDv2_test",
                        "question": "What is the name of this bridge?",
                        "answer": "Old Bridge",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            samples, report = self.mod.load_bridge_samples(str(data_path), str(root), str(old_path))

        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].old_answer, "Old Bridge")
        self.assertTrue(samples[0].prompt.endswith("The answer is:"))
        self.assertEqual(report["mapped_cases"], 1)
        self.assertEqual(report["missing_cases"], [])


if __name__ == "__main__":
    unittest.main()
