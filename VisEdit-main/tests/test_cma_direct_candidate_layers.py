import importlib.util
from pathlib import Path


def load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_cma_direct_candidate_layers.py"
    spec = importlib.util.spec_from_file_location("run_cma_direct_candidate_layers", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_restoration_score_uses_clean_minus_corrupt_denominator():
    mod = load_module()

    assert mod.restoration_score(-2.0, -4.0, -1.0, 1e-8) == 2.0 / 3.00000001
    assert mod.restoration_score(-2.0, -1.0, -1.0, 1e-8) != mod.restoration_score(-2.0, -4.0, -1.0, 1e-8)


def test_rank_cma_layers_filters_invalid_and_keeps_raw_candidates():
    mod = load_module()
    rows = [
        {"layer": 0, "cr_seq_mean": 0.20, "valid_sample_count": 10},
        {"layer": 1, "cr_seq_mean": 0.50, "valid_sample_count": 0},
        {"layer": 2, "cr_seq_mean": float("nan"), "valid_sample_count": 10},
        {"layer": 3, "cr_seq_mean": 0.40, "valid_sample_count": 10},
        {"layer": 4, "cr_seq_mean": 0.30, "valid_sample_count": 10},
    ]

    ranked, summary = mod.rank_cma_layers(rows, topk=5, num_layers=5)

    assert summary["raw_top3_layers"] == ["L1", "L3", "L4"]
    assert summary["top3_layers"] == ["L3", "L4", "L0"]
    assert summary["top5_layers"] == ["L3", "L4", "L0"]
    assert summary["status"] == "done"

    by_layer = {row["layer"]: row for row in ranked}
    assert by_layer[1]["valid_for_cma_direct"] is False
    assert by_layer[1]["invalid_reason"] == "no_valid_restore_samples"
    assert by_layer[2]["invalid_reason"] == "nonfinite_cr_seq_mean"


def test_rank_cma_layers_requires_three_valid_layers():
    mod = load_module()
    _, summary = mod.rank_cma_layers(
        [
            {"layer": 0, "cr_seq_mean": 0.2, "valid_sample_count": 1},
            {"layer": 1, "cr_seq_mean": 0.1, "valid_sample_count": 1},
        ],
        topk=5,
        num_layers=2,
    )

    assert summary["status"] == "failed"
    assert summary["failure_reasons"] == ["valid_layer_count_lt_top3"]
