"""Authorized memory-eligible scheduling; original scientific protocol is frozen."""
import hashlib
import importlib.util
import os
import time
from pathlib import Path

D = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926')
QUEUE = D / 'control/two_gpu_queue.py'
QUEUE_SHA = 'e3f71a8ca7db25099d5271048683e8f035a656c915179b5c81f1132dfef906dd'
ORDER = [('evqa-pilot500', 'instructblip-vicuna-7b', 20),
         ('evqa-pilot500', 'instructblip-vicuna-7b', 17),
         ('mmke-entity', 'minigpt-4-vicuna-7b', 8)]
MINIGPT_OBSERVED_MIB = 70118
MINIGPT_MARGIN_MIB = 2048


class ReconsiderEligibility(Exception):
    pass


def memory_gate(original_gpu):
    def gpu(phase, instruct=False):
        unused, evidence = original_gpu(phase, instruct=instruct)
        evidence = dict(evidence)
        if phase == 'train' and not instruct:
            evidence['required_mib'] = MINIGPT_OBSERVED_MIB + MINIGPT_MARGIN_MIB
            evidence['adjacent_layer_sampled_peak_mib'] = MINIGPT_OBSERVED_MIB
            evidence['margin_mib'] = MINIGPT_MARGIN_MIB
            evidence['peak_is_sampled_not_guaranteed'] = True
        evidence['gate_policy'] = 'memory_eligible_with_historical_margin_20260928'
        evidence['other_processes_allowed'] = True
        # Other processes are reported, not stopped or required to disappear.
        return evidence['free_mib'] >= evidence['required_mib'], evidence
    return gpu


def install(q):
    original_execute = q.execute_group
    q.gpu = memory_gate(q.gpu)
    entered = []

    def gate(phase):
        good = 0
        while good < 3:
            ready, evidence = q.gpu(phase, instruct=q.CURRENT['model'] == 'instructblip-vicuna-7b')
            if phase == 'train' and not ready:
                q.state('TRAIN_GATE_CHANGED_RESELECT', phase=phase, **evidence)
                raise ReconsiderEligibility()
            good = good + 1 if ready else 0
            q.state('GPU_GATE', phase=phase, stable=good, **evidence)
            if good < 3:
                time.sleep(20)

    def completed(task):
        ds, model, layer = task
        dest = q.OLD / 'accepted' / ds / model / ('layer_%02d' % layer)
        if not (dest / 'SYNC_VERIFIED').is_file():
            return False
        q.t.validate_eval(q.t.spec(ds, model, layer), dest)
        return True

    def execute_group(ds, model, layers):
        if (ds, model, list(layers)) == ('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8]):
            assert not entered, 'Duplicate scheduler entry'
            entered.append('entered')
            original_execute(ds, model, [7])  # Unchanged verification of completed L7.
            pending = [task for task in ORDER if not completed(task)]
            while pending:
                candidates = []
                selected = None
                # A trained layer's evaluation is a dependency, not backfillable compute.
                for task in pending:
                    job = q.t.spec(*task)
                    if (q.t.layer(job) / 'train.done').exists():
                        q.t.validate(job)
                        selected = task
                        break
                if selected is None:
                    for task in pending:
                        ready, evidence = q.gpu('train', instruct=task[1] == 'instructblip-vicuna-7b')
                        candidates.append(dict(task=task, eligible=ready, **evidence))
                        if ready and selected is None:
                            selected = task
                if selected is None:
                    q.state('WAITING_FOR_ANY_ELIGIBLE_LAYER', pending=pending, candidates=candidates)
                    time.sleep(20)
                    continue
                q.state('ELIGIBLE_LAYER_SELECTED', selected=selected, pending=pending, candidates=candidates)
                try:
                    original_execute(selected[0], selected[1], [selected[2]])
                except ReconsiderEligibility:
                    # No process/log was started; release group lock and choose anew.
                    time.sleep(20)
                    continue
                assert completed(selected), 'Cannot advance before verified archival'
                pending.remove(selected)
            entered.append('completed')
        elif (ds, model, list(layers)) == ('evqa-pilot500', 'instructblip-vicuna-7b', [17, 20]):
            assert entered == ['entered', 'completed']
            assert all(completed(task) for task in ORDER)
            q.state('ALL_REMAINING_LAYERS_VERIFIED_NO_DUPLICATE_RUN')
        else:
            raise RuntimeError('Unexpected task: ' + repr((ds, model, layers)))

    q.gate = gate
    q.execute_group = execute_group


def main():
    assert os.uname()[1].split('.')[0] == 'g09' and os.environ.get('SLURM_JOB_ID') == '3443209'
    assert hashlib.sha256(QUEUE.read_bytes()).hexdigest() == QUEUE_SHA
    spec = importlib.util.spec_from_file_location('frozen_queue_eligible', str(QUEUE))
    q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q)
    assert q.load(D / 'instruct_assignment.json')['owner'] == 'g09'
    original_state = q.state

    def state(name, **kwargs):
        kwargs.setdefault('scheduling', 'eligible_first_then_shorter_first')
        kwargs.setdefault('preference_if_eligible', ORDER)
        kwargs.setdefault('g08_llava_waiter_unchanged', True)
        if name in ('GPU_GATE', 'TRAIN_GATE_CHANGED_RESELECT') and hasattr(q, 'CURRENT'):
            for key in ('dataset', 'model', 'layer'):
                kwargs.setdefault(key, q.CURRENT[key])
        original_state(name, **kwargs)

    q.state = state
    install(q)
    try:
        q.follow()
    except Exception as error:
        q.state('STOPPED_ERROR_NO_CONFIG_FALLBACK', error=repr(error))
        raise


if __name__ == '__main__':
    main()
