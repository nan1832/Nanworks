from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_paligemma_after_visual_stable_followup_job3044208.sh"
)


def script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_followup_phase_order_and_layers_are_frozen():
    text = script_text()
    expected = [
        'run_phase "evqa-pilot500" "stable" "8,7,17,0,5,6,1,4"',
        'run_phase "mmke-entity" "stable" "8,9,7,12,11,10,17,16,13,5,6,3,2,1,0"',
        'run_phase "evqa-pilot500" "main" "8,7,17,0,5,6,1,4"',
        'run_phase "mmke-entity" "main" "8,9,7,12,11,10,17,16,13,5,6,3,2,1,0"',
    ]
    positions = [text.index(item) for item in expected]
    assert positions == sorted(positions)


def test_followup_requires_visual_stable_8_of_8_before_starting():
    text = script_text()
    assert "VISUAL_STABLE_ALL8_COMPLETION_DONE" in text
    assert "verify_visual_stable_all8" in text
    assert 'required_layers=(7 13 0 5 6 3 2 1)' in text
    assert '[[ "$done_count" -eq 8 ]]' in text


def test_training_and_evaluation_stop_only_after_two_hours_without_log_progress():
    text = script_text()
    assert "STALL_TIMEOUT_SECONDS=7200" in text
    assert "run_with_stall_timeout" in text
    assert 'stale_seconds=$((now - mtime))' in text
    assert '[[ "$stale_seconds" -ge "$STALL_TIMEOUT_SECONDS" ]]' in text
    assert 'timeout --preserve-status --kill-after=120s "$TRAIN_TIMEOUT_SECONDS"' not in text


def test_evaluation_is_guarded_against_using_training_json():
    text = script_text()
    assert '[[ "$train_json" != "$eval_json" ]]' in text
    assert '--eval-data "$eval_json"' in text
    assert "--skip-train" in text
    assert "--overwrite-eval" in text


def test_failures_are_recorded_and_do_not_abort_remaining_layers():
    text = script_text()
    assert "layer_status.csv" in text
    assert "TRAIN_STALLED" in text
    assert "EVAL_NOT_RUN" in text
    assert 'run_one "$dataset" "$mode" "$layer" || true' in text


def test_visual_repair_runs_normal_stable_layers_before_l0_special_case():
    repair = (
        SCRIPT.parent / "run_paligemma_visual_stable_repair_5_1_0_job3044208.sh"
    ).read_text(encoding="utf-8")
    assert 'run_repair_layer 5 "$STABLE_CONFIG"' in repair
    assert 'run_repair_layer 1 "$STABLE_CONFIG"' in repair
    assert 'run_repair_layer 0 "$L0_STABLE_CONFIG"' in repair
    assert repair.index('run_repair_layer 5 "$STABLE_CONFIG"') < repair.index(
        'run_repair_layer 1 "$STABLE_CONFIG"'
    )
    assert repair.index('run_repair_layer 1 "$STABLE_CONFIG"') < repair.index(
        'run_repair_layer 0 "$L0_STABLE_CONFIG"'
    )
    assert "STALL_TIMEOUT_SECONDS=7200" in repair
