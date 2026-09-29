"""CPU-only checks for cross moments and incomplete-resume rejection."""
import json
import tempfile
import unittest
from pathlib import Path

from run_lga_two_space_ablation import aggregate, atomic_json, cross_stats


def stats(a, b, cosine):
    dot = a * b * cosine
    return dict(dot=dot, cos=dot / (a * b + 1e-12), old_norm=a, new_norm=b)


class CrossMomentTests(unittest.TestCase):
    def test_normalize_one_side_before_averaging(self):
        samples = [dict(sample_id="a", layers={"0": stats(1, 10, 1)}),
                   dict(sample_id="b", layers={"0": stats(9, 2, -1)})]
        row = aggregate(samples, ["a", "b"], 1)[0]
        self.assertAlmostEqual(row["no_old_strength"], 4)
        self.assertAlmostEqual(row["no_new_strength"], -4)
        self.assertAlmostEqual(row["dot"], -4)
        self.assertAlmostEqual(row["no_direction"], 14)
        self.assertNotAlmostEqual(row["cos"] * row["new_norm"], row["no_old_strength"])
        self.assertNotAlmostEqual(row["old_norm"] * row["new_norm"], row["no_direction"])

    def test_zero_visual_gradient_is_finite_zero(self):
        result = cross_stats(stats(0, 0, 0))
        self.assertTrue(all(x == 0 for x in result.values()))

    def test_partial_extra_or_duplicate_samples_cannot_publish(self):
        a = dict(sample_id="a", layers={"0": stats(1, 1, 1)})
        with self.assertRaises(AssertionError):
            aggregate([a], ["a", "b"], 1)
        with self.assertRaises(AssertionError):
            aggregate([a, a], ["a", "b"], 1)
        with self.assertRaises(AssertionError):
            aggregate([a], ["a"], 2)
        with self.assertRaises(AssertionError):
            aggregate([a], ["b"], 1)

    def test_inconsistent_cosine_is_rejected(self):
        with self.assertRaises(ValueError):
            cross_stats(dict(dot=1, cos=-1, old_norm=1, new_norm=1))

    def test_atomic_sample_resume_preserves_full_precision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samples/000001.json"
            first = dict(sample_id="a", layers={"0": cross_stats(stats(1, 2, .3))})
            atomic_json(path, first)
            resumed = json.loads(path.read_text(encoding="utf-8"))
            resumed["layers"]["1"] = cross_stats(stats(8, 3, -.2))
            atomic_json(path, resumed)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), resumed)
            self.assertEqual(resumed["layers"]["0"], first["layers"]["0"])
            self.assertEqual(len(aggregate([resumed], ["a"], 2)), 2)


if __name__ == "__main__":
    unittest.main()
