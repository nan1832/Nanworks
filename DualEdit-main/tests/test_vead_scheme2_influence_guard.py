from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


torch = pytest.importorskip("torch")


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import editor.vllm_editors.vead.vead as vead_module  # noqa: E402
from editor.vllm_editors.vead.vead import VEAD  # noqa: E402


def _make_dummy_xym():
    inputs_embeds = torch.randn(1, 4, 3)
    vt_range = (0, 1)
    label_ids = torch.tensor([[1, 2]], dtype=torch.long)
    label_masks = torch.tensor([[1, 1]], dtype=torch.long)
    return ((inputs_embeds, vt_range), label_ids, label_masks)


def test_scheme2_organize_batch_data_skips_influence_mapper_when_it_disabled(
    tmp_path, monkeypatch
):
    edit_dir = tmp_path / "edit_signal"
    xym_dir = tmp_path / "xym"
    edit_dir.mkdir()
    xym_dir.mkdir()

    torch.save(
        {"edit_reps": [torch.randn(2, 3)], "prompt_end": 1},
        edit_dir / "text_adaptor",
    )
    torch.save(
        (
            _make_dummy_xym(),
            {"gen_stub": _make_dummy_xym()},
            {"loc_stub": _make_dummy_xym()},
        ),
        xym_dir / "layer_0.pt",
    )

    editor = VEAD.__new__(VEAD)
    editor.adaptors = {"text_adaptor": object()}
    editor.data_proc_device = "cpu"
    editor.mid_inpt_start_layer = "layer_0.pt"
    editor.device = "cpu"
    editor.cfg = SimpleNamespace(IT=SimpleNamespace(add_it=False))

    def fail_if_called(*args, **kwargs):
        raise AssertionError(
            "influence mapper should not run when scheme2 disables IT"
        )

    editor.__get_xy_for_influence_mapper__ = fail_if_called
    monkeypatch.setattr(vead_module, "move_to_device", lambda value, device: value)

    batch = VEAD.organize_batch_data(editor, [(str(edit_dir), str(xym_dir))])

    assert batch[-1] is None
