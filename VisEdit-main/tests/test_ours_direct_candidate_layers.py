import importlib.util
from pathlib import Path


def load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_ours_direct_candidate_layers.py"
    spec = importlib.util.spec_from_file_location("run_ours_direct_candidate_layers", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rank_ours_direct_filters_invalid_layers_and_keeps_raw_candidates():
    mod = load_module()
    rows = [
        {
            "layer": 0,
            "S_v_cos": -0.5,
            "S_v_new_norm": 2.0,
            "S_v_zero_grad": "False",
            "visual_token_start": 0,
            "visual_token_end": 4,
        },
        {
            "layer": 1,
            "S_v_cos": 0.25,
            "S_v_new_norm": 9.0,
            "S_v_zero_grad": "False",
            "visual_token_start": 0,
            "visual_token_end": 4,
        },
        {
            "layer": 2,
            "S_v_cos": -0.25,
            "S_v_new_norm": 8.0,
            "S_v_zero_grad": "True",
            "visual_token_start": 0,
            "visual_token_end": 4,
        },
        {
            "layer": 3,
            "S_v_cos": -0.5,
            "S_v_new_norm": 4.0,
            "S_v_zero_grad": "False",
            "visual_token_start": 0,
            "visual_token_end": 4,
        },
    ]

    ranked, summary = mod.rank_ours_direct_layers(rows, topk=3, num_layers=4)

    assert summary["raw_top3_layers"] == ["L3", "L0", "L1"]
    assert summary["top3_layers"] == ["L3", "L0"]
    assert summary["cleaned_top3_layers"] == ["L3", "L0"]
    assert summary["invalid_layers"] == [{"layer": "L2", "reason": "S_v_zero_grad"}]

    by_layer = {row["layer"]: row for row in ranked}
    assert by_layer[3]["S_v_neg_cos"] == 0.5
    assert by_layer[3]["S_v_depth2"] == 1.0
    assert by_layer[3]["S_ours"] == 2.0
    assert by_layer[0]["S_ours"] == 0.0625
    assert by_layer[1]["S_ours"] == 0.0


def test_rank_ours_direct_reports_no_valid_layers():
    mod = load_module()
    ranked, summary = mod.rank_ours_direct_layers(
        [
            {
                "layer": 0,
                "S_v_cos": "nan",
                "S_v_new_norm": 1.0,
                "S_v_zero_grad": "False",
                "visual_token_start": 0,
                "visual_token_end": 4,
            }
        ],
        topk=3,
        num_layers=1,
    )

    assert ranked[0]["valid_for_ours_direct"] is False
    assert summary["status"] == "failed"
    assert summary["failure_reasons"] == ["no_valid_ours_direct_layer"]
