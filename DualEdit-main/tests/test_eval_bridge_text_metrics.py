from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.eval_bridge_text_adapter_ckpt import (  # noqa: E402
    extract_assistant_answer,
    loose_match,
    normalize_answer,
    strict_match,
    summarize_rows,
)


def test_extract_assistant_answer_uses_last_assistant_span():
    raw = "USER: <image>\nWhat is this?\nASSISTANT: Liberty Bridge"
    assert extract_assistant_answer(raw) == "Liberty Bridge"


def test_strict_and_loose_match_normalize_outputs():
    assert normalize_answer(" Liberty Bridge ") == "liberty bridge"
    assert strict_match("Liberty Bridge", "liberty bridge") == 1
    assert strict_match("The Liberty Bridge", "liberty bridge") == 0
    assert loose_match("The bridge is Liberty Bridge.", "Liberty Bridge") == 1


def test_summarize_rows_groups_metrics_by_split():
    rows = [
        {"split": "request", "strict_acc": 1, "loose_acc": 1},
        {"split": "request", "strict_acc": 0, "loose_acc": 1},
        {"split": "generality.image_rephrase", "strict_acc": 1, "loose_acc": 1},
    ]
    summary = summarize_rows(rows)
    assert summary["request"]["count"] == 2
    assert summary["request"]["strict_acc"] == 0.5
    assert summary["request"]["loose_acc"] == 1.0
    assert summary["generality.image_rephrase"]["count"] == 1
    assert summary["generality.image_rephrase"]["strict_acc"] == 1.0
