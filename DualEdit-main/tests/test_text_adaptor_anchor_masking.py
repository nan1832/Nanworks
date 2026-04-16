from pathlib import Path
import sys

import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from editor.vllm_editors.vead.adpt_model import TextEditAdaptor  # noqa: E402


def build_deterministic_adaptor():
    torch.manual_seed(0)
    adaptor = TextEditAdaptor(hidden_size=4, mid_dim=4, cross_att_head_n=1)
    adaptor.open_adaptor(True)
    adaptor.open_gating = False
    adaptor.set_input_info(True, 1, 3)
    adaptor.set_edit_signal(
        torch.randn(1, 2, 4),
        torch.ones(1, 2),
        torch.tensor([5]),
    )
    adaptor.set_prompt_end(torch.tensor([5]))
    return adaptor


def changed_positions(before, after):
    return ((after - before).abs().sum(-1).squeeze(0) > 1e-6).tolist()


def test_text_adaptor_only_updates_selected_anchor_positions():
    adaptor = build_deterministic_adaptor()
    adaptor.set_text_token_indices([[4]])
    layer = torch.randn(1, 5, 4)
    out = adaptor(layer.clone())
    assert changed_positions(layer, out) == [False, False, False, False, True]


def test_text_adaptor_leaves_sample_unchanged_when_anchor_list_is_empty():
    adaptor = build_deterministic_adaptor()
    adaptor.set_text_token_indices([[]])
    layer = torch.randn(1, 5, 4)
    out = adaptor(layer.clone())
    assert torch.allclose(out, layer)


def test_text_adaptor_falls_back_to_prompt_side_text_tokens_when_indices_are_none():
    adaptor = build_deterministic_adaptor()
    adaptor.set_text_token_indices(None)
    layer = torch.randn(1, 5, 4)
    out = adaptor(layer.clone())
    assert changed_positions(layer, out) == [False, False, False, True, True]
