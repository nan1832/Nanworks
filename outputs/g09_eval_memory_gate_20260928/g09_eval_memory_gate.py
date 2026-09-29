"""Authorized G09 evaluation-only scheduling change; frozen protocol unchanged."""
import hashlib
import importlib.util
import os
from pathlib import Path

D = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926')
SOURCE = D / 'control/two_gpu_queue.py'
EXPECTED_SHA = 'e3f71a8ca7db25099d5271048683e8f035a656c915179b5c81f1132dfef906dd'


def make_gpu_gate(original_gpu):
    def gpu(phase, instruct=False):
        ready, evidence = original_gpu(phase, instruct=instruct)
        if phase == 'eval':
            # Project GPU/controller/combination locks remain in the frozen queue.
            # Require the unchanged free-memory threshold and three stable samples.
            evidence = dict(evidence)
            evidence['gate_policy'] = 'g09_eval_free_memory_only_user_authorized_20260928'
            evidence['other_processes_allowed'] = True
            ready = evidence['free_mib'] >= evidence['required_mib']
        return ready, evidence
    return gpu


def main():
    assert os.uname()[1].split('.')[0] == 'g09'
    assert os.environ.get('SLURM_JOB_ID') == '3443209'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
    spec = importlib.util.spec_from_file_location('frozen_two_gpu_queue', str(SOURCE))
    q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q)
    assert q.NODE == 'g09' and q.JOB[q.NODE] == '3443209'
    q.gpu = make_gpu_gate(q.gpu)
    try:
        q.follow()
    except Exception as error:
        q.state('STOPPED_ERROR_NO_CONFIG_FALLBACK', error=repr(error))
        raise


if __name__ == '__main__':
    main()
