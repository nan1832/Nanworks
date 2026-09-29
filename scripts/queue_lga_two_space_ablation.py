#!/usr/bin/env python3
"""Wait behind verified existing experiments, then run isolated LGA ablations.

Uses the project's existing advisory GPU lock. Never kills a process, changes an
old experiment, or treats an exited/failed old controller as successful completion.
"""
import argparse
import fcntl
import json
import os
import socket
import subprocess
import time
import traceback
from pathlib import Path

from run_lga_two_space_ablation import MODELS, DATASETS, atomic_json, sha

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJECT = BASE / 'VisEdit-main'
RESULTS = BASE / 'server_results'
ROOT = RESULTS / 'lga_two_spaces_ablation_20260928'
PYTHON = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
QWEN_PYTHON = str(BASE / 'envs/qwen25vl/bin/python')
JOBS = {'g08': '3435286', 'g09': '3443209'}


def load(path):
    return json.loads(Path(path).read_text())


def state(node, name, **kwargs):
    value = dict(state=name, node=node, time=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                 job=JOBS[node], pid=os.getpid(), **kwargs)
    atomic_json(ROOT / 'control' / (node + '_status.json'), value)
    print(json.dumps(value), flush=True)


def check_job(node):
    info = subprocess.check_output(['squeue', '-j', JOBS[node], '-h', '-o', '%T %N %L'], universal_newlines=True).strip().split()
    if len(info) != 3 or info[:2] != ['RUNNING', node]:
        raise RuntimeError('Allocation no longer running on expected node: ' + repr(info))
    if info[2] != 'UNLIMITED':
        days, clock = info[2].split('-', 1) if '-' in info[2] else ('0', info[2])
        seconds = int(days) * 86400 + sum(int(v) * 60 ** i for i, v in enumerate(reversed(clock.split(':'))))
        if seconds < 86400:
            raise RuntimeError('Less than 24 hours allocation time remains; resume later from sample files')


def predecessor_done(node):
    if node == 'g08':
        p = RESULTS / 'evqa_llava_job3435286_20260924/resume_L4_wait_memory_20260928/completion_verified.json'
        if not p.is_file():
            return False, str(p)
        receipt = load(p)
        assert receipt['status'] == 'TRAIN50_FULL2093_VERIFIED_SHARED'
        assert receipt['results_on_shared_storage'] is True
    else:
        p = RESULTS / 'tukey_top3_two_gpu_20260926/control/g09/DONE.json'
        if not p.is_file():
            return False, str(p)
        assert load(p)['state'] == 'CARD_QUEUE_DONE_LLAVA_STAYS_PAUSED'
    return True, str(p)


def gpu_snapshot():
    line = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-gpu=memory.free,utilization.gpu', '--format=csv,noheader,nounits'], universal_newlines=True).strip()
    free, utilization = [int(x.strip()) for x in line.split(',')]
    return dict(free_mib=free, utilization=utilization)


def ready_lock(node, space):
    threshold = 74000 if space == 'parameter' else 60000
    stable = 0
    while True:
        if (ROOT / 'control' / ('STOP_' + node)).exists():
            raise RuntimeError('Stop marker requested; no new group started')
        check_job(node)
        done, evidence = predecessor_done(node)
        if not done:
            state(node, 'WAITING_PREVIOUS_EXPERIMENTS', completion_marker=evidence, space=space)
            time.sleep(30)
            continue
        snapshot = gpu_snapshot()
        stable = stable + 1 if snapshot['free_mib'] >= threshold else 0
        state(node, 'WAITING_GPU_MEMORY', space=space, required_mib=threshold, stable=stable, **snapshot)
        if stable >= 3:
            lock_path = RESULTS / 'gpu_locks' / (node + '_gpu0.lock')
            assert lock_path.parent.is_dir()
            lock = lock_path.open('a')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lock.close()
                stable = 0
                state(node, 'WAITING_PROJECT_GPU_LOCK', space=space)
            else:
                if gpu_snapshot()['free_mib'] >= threshold:
                    return lock
                lock.close()
                stable = 0
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', choices=list(JOBS), required=True)
    args = parser.parse_args()
    node = args.node
    assert socket.gethostname().split('.')[0] == node
    assert os.environ.get('SLURM_JOB_ID') == JOBS[node]
    control = ROOT / 'control'
    control.mkdir(parents=True, exist_ok=True)
    own = (control / (node + '_controller.lock')).open('a')
    fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
    pins = load(control / 'code_pins.json')
    def pincheck():
        for path, digest in pins.items():
            assert sha(path) == digest, 'Code changed: ' + path
    pincheck()
    space = 'visual' if node == 'g08' else 'parameter'
    failures = []
    for model in MODELS:
        for ds in DATASETS:
            out = ROOT / 'results' / space / ds / model
            summary_path = out / 'summary.json'
            if summary_path.exists() and load(summary_path).get('status') == 'done':
                continue
            lock = ready_lock(node, space)
            try:
                pincheck()
                command = [QWEN_PYTHON if space == 'parameter' or model.startswith('qwen') else PYTHON,
                           str(ROOT / 'code/run_lga_two_space_ablation.py'), '--project-dir', str(PROJECT),
                           '--source-root', str(RESULTS), '--out-root', str(ROOT / 'results'),
                           '--space', space, '--dataset', ds, '--model', model]
                env = os.environ.copy()
                env.update(CUDA_VISIBLE_DEVICES='0', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                           OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONUNBUFFERED='1')
                out.mkdir(parents=True, exist_ok=True)
                log = out / ('run_' + time.strftime('%Y%m%d_%H%M%S') + '.log')
                with log.open('xb') as stream:
                    child = subprocess.Popen(command, cwd=str(PROJECT), env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
                    state(node, 'RUNNING_ABLATION', space=space, dataset=ds, model=model, child_pid=child.pid, log=str(log))
                    while child.poll() is None:
                        time.sleep(30)
                    summary = load(summary_path) if summary_path.exists() else {}
                    if child.returncode or summary.get('status') != 'done':
                        failures.append(dict(space=space, dataset=ds, model=model, returncode=child.returncode, status=summary.get('status', 'failed_before_summary'), log=str(log)))
                        state(node, 'GROUP_NEEDS_INSPECTION', failures=failures)
                    else:
                        state(node, 'GROUP_VERIFIED', space=space, dataset=ds, model=model, sample_count=summary['sample_count'])
            finally:
                lock.close()
    state(node, 'FINISHED_WITH_FAILURES' if failures else 'ALL_ASSIGNED_GROUPS_DONE', space=space, failures=failures)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        node = socket.gethostname().split('.')[0]
        if node in JOBS:
            state(node, 'STOPPED_REQUIRES_INSPECTION', error=traceback.format_exc())
        raise
