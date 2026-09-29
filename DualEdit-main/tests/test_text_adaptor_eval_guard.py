from pathlib import Path


def test_text_adaptor_source_contains_no_debug_breakpoints():
    adpt_model_path = (
        Path(__file__).resolve().parents[1]
        / "editor"
        / "vllm_editors"
        / "vead"
        / "adpt_model.py"
    )
    text = adpt_model_path.read_text(encoding="utf-8")
    assert "pdb.set_trace()" not in text


def test_eval_script_primes_adaptors_before_generation():
    eval_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "eval_bridge_text_adapter_ckpt.py"
    )
    text = eval_path.read_text(encoding="utf-8")
    assert "def _prepare_adaptors_for_generation(" in text
    assert "_prepare_adaptors_for_generation(editor, prompt, image)" in text
