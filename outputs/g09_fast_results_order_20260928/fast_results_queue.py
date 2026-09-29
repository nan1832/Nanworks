"""User-approved G09 order only; frozen runners, locks and VRAM gates retained."""
import hashlib
import importlib.util
import os
from pathlib import Path

D = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926')
QUEUE = D / 'control/two_gpu_queue.py'
EVAL_POLICY = D / 'control/g09/eval_memory_gate_20260928/g09_eval_memory_gate.py'
QUEUE_SHA = 'e3f71a8ca7db25099d5271048683e8f035a656c915179b5c81f1132dfef906dd'
POLICY_SHA = '3cbbdc1e67d4e6e9339a662e9754bc5d2f00cc8b665f22e34df64e292a2a46fa'
ORDER = [('evqa-pilot500', 'instructblip-vicuna-7b', 20),
         ('evqa-pilot500', 'instructblip-vicuna-7b', 17),
         ('mmke-entity', 'minigpt-4-vicuna-7b', 8)]


def module(path, name, expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, str(path)
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def install_order(q):
    original_execute = q.execute_group
    visited = []

    def execute_group(dataset, model, layers):
        if (dataset, model, list(layers)) == ('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8]):
            assert not visited, 'Duplicate entry to reordered queue'
            visited.append('entered')
            # Validate/skip already accepted L7 through the unchanged implementation.
            original_execute(dataset, model, [7])
            q.state('APPROVED_FAST_RESULTS_ORDER', approved_order=ORDER)
            original_execute('evqa-pilot500', 'instructblip-vicuna-7b', [20, 17])
            original_execute(dataset, model, [8])
            visited.append('completed')
        elif (dataset, model, list(layers)) == ('evqa-pilot500', 'instructblip-vicuna-7b', [17, 20]):
            # The original fallback is now satisfied; verify, never train it twice.
            assert visited == ['entered', 'completed']
            for layer in (20, 17):
                job = q.t.spec(dataset, model, layer)
                dest = q.OLD / 'accepted' / dataset / model / ('layer_%02d' % layer)
                assert (dest / 'SYNC_VERIFIED').is_file()
                q.t.validate_eval(job, dest)
            q.state('INSTRUCT_GROUP_ALREADY_COMPLETED_IN_PRIORITY_ORDER')
        else:
            raise RuntimeError('Unexpected request to G09 reordered queue: ' + repr((dataset, model, layers)))

    q.execute_group = execute_group


def main():
    assert os.uname()[1].split('.')[0] == 'g09' and os.environ.get('SLURM_JOB_ID') == '3443209'
    q = module(QUEUE, 'frozen_two_gpu_queue_fast_order', QUEUE_SHA)
    policy = module(EVAL_POLICY, 'unchanged_eval_memory_policy', POLICY_SHA)
    assert q.load(D / 'instruct_assignment.json')['owner'] == 'g09'
    q.gpu = policy.make_gpu_gate(q.gpu)  # Keep the previously approved eval-only change.
    original_state = q.state

    def state(name, **kwargs):
        kwargs.setdefault('approved_order', ORDER)
        kwargs.setdefault('g08_llava_waiter_unchanged', True)
        if name == 'GPU_GATE' and hasattr(q, 'CURRENT'):
            for key in ('dataset', 'model', 'layer'):
                kwargs.setdefault(key, q.CURRENT[key])
        original_state(name, **kwargs)

    q.state = state
    install_order(q)
    try:
        q.follow()
    except Exception as error:
        q.state('STOPPED_ERROR_NO_CONFIG_FALLBACK', error=repr(error))
        raise


if __name__ == '__main__':
    main()
