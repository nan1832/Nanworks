from pathlib import Path


def test_scheme2_source_guards_influence_mapper_under_it_flag():
    vead_path = (
        Path(__file__).resolve().parents[1]
        / "editor"
        / "vllm_editors"
        / "vead"
        / "vead.py"
    )
    text = vead_path.read_text(encoding="utf-8")
    start = text.index("    def organize_batch_data")
    end = text.index("    def train_a_batch", start)
    organize_batch_data_src = text[start:end]

    assert "if self.cfg.IT.add_it:" in organize_batch_data_src
    assert "infm_xy = None" in organize_batch_data_src
