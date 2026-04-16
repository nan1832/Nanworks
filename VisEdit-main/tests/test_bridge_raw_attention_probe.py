import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_raw_attention_probe.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_raw_attention_probe", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeRawAttentionProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_map_text_tokens_to_merged_positions_handles_image_expansion(self):
        mapping = self.mod.map_text_tokens_to_merged_positions(
            input_ids=[11, 99, 21, 22],
            image_token_id=99,
            img_token_n=4,
        )

        self.assertEqual([item["token_id"] for item in mapping], [11, 21, 22])
        self.assertEqual([item["original_idx"] for item in mapping], [0, 2, 3])
        self.assertEqual([item["merged_idx"] for item in mapping], [0, 5, 6])

    def test_reshape_visual_attention_to_grid_uses_square_patch_layout(self):
        weights = list(range(576))
        grid = self.mod.reshape_visual_attention_to_grid(weights, vt_range=(1, 577))

        self.assertEqual((len(grid), len(grid[0])), (24, 24))
        self.assertEqual(float(grid[0][0]), 0.0)
        self.assertEqual(float(grid[0][1]), 1.0)
        self.assertEqual(float(grid[-1][-1]), 575.0)


if __name__ == "__main__":
    unittest.main()
