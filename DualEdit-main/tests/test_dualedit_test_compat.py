from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import sys


DUALEDIT_ROOT = Path(__file__).resolve().parents[1]
DUALEDIT_TEST_PATH = DUALEDIT_ROOT / "dualedit_test.py"


def load_dualedit_test_with_stubs(eval_class):
    utils_module = ModuleType("utils")
    utils_module.get_full_model_name = lambda name: name
    utils_module.load_vllm_editor = lambda *args, **kwargs: None

    global_module = ModuleType("utils.GLOBAL")
    global_module.ROOT_PATH = "DualEdit-main"
    utils_module.GLOBAL = global_module

    evaluation_pkg = ModuleType("evaluation")
    eval_module = ModuleType("evaluation.vllm_editor_eval")
    eval_module.VLLMEditorEvaluation = eval_class
    evaluation_pkg.vllm_editor_eval = eval_module

    sys.modules["utils"] = utils_module
    sys.modules["utils.GLOBAL"] = global_module
    sys.modules["evaluation"] = evaluation_pkg
    sys.modules["evaluation.vllm_editor_eval"] = eval_module

    spec = importlib.util.spec_from_file_location("dualedit_test_stubbed", DUALEDIT_TEST_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_cfg():
    return SimpleNamespace(
        edit_model_name="llava-v1.5-7b",
        evaluation_name="EVQA-target0231-l12",
        editor_ckpt_path="server_results/checkpoints/epoch-40-i-1200-ema_loss-0.0211",
    )


def normalize_path_text(path):
    return str(path).replace("\\", "/")


def test_build_eval_result_dir_path_includes_checkpoint_name_when_supported():
    class EvalWithCkpt:
        def __init__(self, editor, eval_data, evaluation_name=None, results_dir="eval_results", seed=0, editor_ckpt_path=None):
            pass

    dualedit_module = load_dualedit_test_with_stubs(EvalWithCkpt)
    path = dualedit_module.build_eval_result_dir_path(make_cfg())
    assert normalize_path_text(path).endswith(
        "EVQA-target0231-l12/epoch-40-i-1200-ema_loss-0.0211/single_edit"
    )


def test_build_eval_result_dir_path_falls_back_when_checkpoint_name_not_supported():
    class EvalWithoutCkpt:
        def __init__(self, editor, eval_data, evaluation_name=None, results_dir="eval_results", seed=0):
            pass

    dualedit_module = load_dualedit_test_with_stubs(EvalWithoutCkpt)
    path = dualedit_module.build_eval_result_dir_path(make_cfg())
    assert normalize_path_text(path).endswith("EVQA-target0231-l12/single_edit")


def test_build_evaluator_only_passes_editor_ckpt_path_when_supported():
    calls = []

    class EvalWithoutCkpt:
        def __init__(self, editor, eval_data, evaluation_name=None, results_dir="eval_results", seed=0):
            calls.append(
                {
                    "editor": editor,
                    "eval_data": eval_data,
                    "evaluation_name": evaluation_name,
                    "results_dir": results_dir,
                }
            )

    dualedit_module = load_dualedit_test_with_stubs(EvalWithoutCkpt)
    evaluator = dualedit_module.build_evaluator("editor_obj", "eval_data_obj", make_cfg())
    assert isinstance(evaluator, EvalWithoutCkpt)
    assert calls == [
        {
            "editor": "editor_obj",
            "eval_data": "eval_data_obj",
            "evaluation_name": "EVQA-target0231-l12",
            "results_dir": "eval_results",
        }
    ]
