import importlib.util
import os
import sys
import unittest
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_attr_localize_scan.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def find_bridge_root() -> Path:
    search_roots = [
        REPO_ROOT.parent,
        REPO_ROOT.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
        Path.cwd().parent.parent,
    ]
    for base in search_roots:
        candidate = base / "Ten_Classes" / "bridge"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Ten_Classes/bridge not found from test search roots")


BRIDGE_ROOT = find_bridge_root()
BRIDGE_JSON = BRIDGE_ROOT / "bridge_train" / "edit_30_bridge_train_only_vis.json"


def load_script_module():
    spec = importlib.util.spec_from_file_location("bridge_attr_localize_scan", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeAttrLocalizeScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_load_bridge_samples_resolves_first_case(self):
        samples = self.mod.load_bridge_samples(str(BRIDGE_JSON), str(BRIDGE_ROOT), max_samples=1)
        self.assertEqual(len(samples), 1)

        sample = samples[0]
        self.assertEqual(sample.sample_id, "train_0")
        self.assertEqual(sample.target_text, "Chikugo River Lift Bridge")
        self.assertTrue(sample.prompt.endswith("The answer is:"))
        self.assertTrue(sample.image_path.endswith("GLDv2_084bb592a552d066.jpg"))
        self.assertTrue(os.path.exists(sample.image_path))
        self.assertGreater(sample.image.size[0], 0)
        self.assertGreater(sample.image.size[1], 0)

    def test_apply_noise_to_hidden_changes_only_selected_tokens(self):
        hidden = torch.zeros(1, 4, 3)
        updated = self.mod.apply_noise_to_hidden(hidden, [1, 3], noise_level=0.5)

        self.assertEqual(updated.shape, hidden.shape)
        self.assertTrue(torch.equal(updated[0, 0], hidden[0, 0]))
        self.assertTrue(torch.equal(updated[0, 2], hidden[0, 2]))
        self.assertFalse(torch.equal(updated[0, 1], hidden[0, 1]))
        self.assertFalse(torch.equal(updated[0, 3], hidden[0, 3]))


if __name__ == "__main__":
    unittest.main()
