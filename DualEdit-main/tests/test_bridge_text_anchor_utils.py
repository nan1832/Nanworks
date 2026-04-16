from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.bridge_text_anchor_utils import (  # noqa: E402
    expand_anchor_positions,
    normalize_token_label,
    select_anchor_positions,
)


def test_select_anchor_positions_returns_bridge_only_position():
    token_labels = ["<bos>", "What", " is", " this", " bridge", "?", " The", " answer", " is", ":"]
    token_positions = [0, 579, 580, 584, 585, 586, 587, 588, 589, 590]
    assert select_anchor_positions(token_labels, token_positions, "bridge_only") == [585]


def test_expand_anchor_positions_returns_this_bridge_qmark_span():
    token_labels = ["<bos>", "What", " is", " this", " bridge", "?", " The", " answer", " is", ":"]
    token_positions = [0, 579, 580, 584, 585, 586, 587, 588, 589, 590]
    assert expand_anchor_positions(token_labels, token_positions, [585], "this_bridge_qmark") == [584, 585, 586]


def test_normalize_token_label_strips_llava_prefix_noise():
    assert normalize_token_label(" bridge") == "bridge"
    assert normalize_token_label("<0x0A>") == "0x0a"
