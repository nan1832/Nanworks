import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_raw_attention_probe_blip2.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_raw_attention_probe_blip2", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeRawAttentionProbeBlip2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_map_blip2_text_tokens_to_merged_positions_offsets_by_query_tokens(self):
        mapping = self.mod.map_blip2_text_tokens_to_merged_positions(
            input_ids=[101, 102, 103],
            query_token_n=4,
        )

        self.assertEqual([item["token_id"] for item in mapping], [101, 102, 103])
        self.assertEqual([item["original_idx"] for item in mapping], [0, 1, 2])
        self.assertEqual([item["merged_idx"] for item in mapping], [4, 5, 6])

    def test_reshape_query_attention_to_grid_uses_fixed_column_count(self):
        grid = self.mod.reshape_query_attention_to_grid(list(range(32)), cols=8)

        self.assertEqual((len(grid), len(grid[0])), (4, 8))
        self.assertEqual(float(grid[0][0]), 0.0)
        self.assertEqual(float(grid[0][7]), 7.0)
        self.assertEqual(float(grid[-1][-1]), 31.0)


if __name__ == "__main__":
    unittest.main()
