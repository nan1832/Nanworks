"""Calibrate pending InstructBLIP gates after accepted MiniGPT L8 evaluation."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
MODEL = 'instructblip-vicuna-7b'
DATASET = 'evqa-pilot500'
LAYERS = (20, 17)
MARGIN_MIB = 2048
PROBE_HEADROOM_MIB = 3072


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.partial')
    tmp.write_text(json.dumps(value, indent=2))
    tmp.replace(path)


def requirement(report, process_peak_mib):
    assert report['status'] == 'passed'
    assert report['completed_epochs'] == 1 and report['optimizer_batches'] == 250
    # Include allocator high-water values and at least 1 GiB of nonallocator overhead.
    overhead = max(1024, report.get('current_process_mib', 0) - report['current_reserved_mib'])
    peak = max(process_peak_mib, report.get('current_process_mib', 0),
               report['max_reserved_mib'] + overhead)
    return dict(observed_process_peak_mib=process_peak_mib,
                allocator_peak_reserved_mib=report['max_reserved_mib'],
                nonallocator_allowance_mib=overhead,
                accounted_peak_mib=peak, margin_mib=MARGIN_MIB,
                required_mib=int(math.ceil((peak + MARGIN_MIB) / 256) * 256),
                evidence_scope='preprocessing plus first complete 500-sample epoch; not a full-50-epoch guarantee')


def signature(command):
    files = [command[2], command[command.index('--config-path') + 1],
             command[command.index('--train-data') + 1], ROOT / 'probe.py']
    value = dict(command=command, file_sha256={str(p): sha(p) for p in files})
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest(), value


def free_memory():
    return int(subprocess.check_output(
        ['nvidia-smi', '-i', '0', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
        universal_newlines=True).strip())


def probe_layer(q, layer):
    job = q.t.spec(DATASET, MODEL, layer)
    command = q.t.command(job, 'train')
    fingerprint, evidence = signature(command)
    case = ROOT / ('layer_%02d' % layer)
    receipt_path = case / 'accepted_probe.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        assert receipt['fingerprint'] == fingerprint, 'Calibration inputs changed'
        assert sha(case / 'probe_report.json') == receipt['report_sha256']
        return receipt
    assert not case.exists(), 'Incomplete calibration attempt requires inspection: ' + str(case)
    q.t.pincheck()
    q.check_time()
    assert command[command.index('--epochs') + 1] == '50'
    assert command[command.index('--batch-size') + 1] == '2'
    assert '--synchronous-data-loading' in command and '--activation-checkpointing' in command
    assert '--resume-checkpoint' not in command and '--skip-eval' in command
    free_samples = []
    for i in range(3):
        free_samples.append(free_memory())
        if i < 2:
            time.sleep(5)
    budget = min(free_samples) - PROBE_HEADROOM_MIB
    assert budget > 4096, 'Insufficient free memory even for an isolated capped probe'
    case.mkdir()
    work = case / 'probe_work'
    work.mkdir()
    # Outputs and generated caches are isolated from formal training.
    probe_args = command[3:]
    probe_args[probe_args.index('--out-root') + 1] = str(work)
    request = dict(runner=command[2], runner_args=probe_args,
                   report=str(case / 'probe_report.json'), fingerprint=fingerprint,
                   allocator_budget_mib=budget, free_samples_mib=free_samples,
                   formal_command=command, protocol_evidence=evidence,
                   note='Same original arguments except isolated out-root; stop after one epoch in wrapper')
    atomic(case / 'request.json', request)
    env = os.environ.copy()
    env.update(PYTHONPATH=str(q.P) + ':' + env.get('PYTHONPATH', ''),
               CUDA_VISIBLE_DEVICES='0', PYTHONUNBUFFERED='1',
               PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
    args = [command[0], '-u', str(ROOT / 'probe.py'), '--request', str(case / 'request.json')]
    peak = 0
    started = time.monotonic()
    last_report = 0
    child = None
    try:
        with (case / 'probe.log').open('x') as log:
            child = subprocess.Popen(args, cwd=str(q.P), env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            atomic(case / 'launch.json', dict(pid=child.pid, command=args, started=time.time()))
            while child.poll() is None:
                memory = q.apps().get(child.pid, 0)
                peak = max(peak, memory)
                if time.monotonic() - last_report >= 60:
                    q.state('CALIBRATING_INSTRUCT_MEMORY', dataset=DATASET, model=MODEL,
                            layer=layer, child_pid=child.pid, allocator_budget_mib=budget,
                            observed_process_peak_mib=peak, log=str(case / 'probe.log'))
                    last_report = time.monotonic()
                if time.monotonic() - started > 10800:
                    raise RuntimeError('Memory probe exceeded three hours; inspect before retry')
                time.sleep(1)
    finally:
        # Only this calibration child can be stopped; existing training/other users are untouched.
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    report_path = case / 'probe_report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else dict(status='missing_report')
    if child.returncode != 0 or report.get('status') != 'passed':
        atomic(case / 'failed.json', dict(returncode=child.returncode, report=report,
                                         observed_process_peak_mib=peak, allocator_budget_mib=budget))
        raise RuntimeError('Measured probe failed; inspect %s. No guessed 76-GiB fallback or automatic retry.' % case)
    assert report['fingerprint'] == fingerprint
    assert not list(work.glob('layer_*/train.done'))
    assert not list(work.glob('layer_*/eval_full.done'))
    assert not list(work.glob('layer_*/selected_checkpoint.tsv'))
    receipt = dict(layer=layer, fingerprint=fingerprint, report_sha256=sha(report_path),
                   probe_code_sha256=sha(ROOT / 'probe.py'), elapsed_seconds=time.monotonic() - started,
                   formal_command=command, **requirement(report, peak))
    atomic(receipt_path, receipt)
    q.state('INSTRUCT_MEMORY_CALIBRATED', dataset=DATASET, model=MODEL, **receipt)
    return receipt


def ensure(q):
    assert os.uname()[1].split('.')[0] == 'g09'
    assert os.environ.get('SLURM_JOB_ID') == '3443209'
    dependency = q.OLD / 'accepted/mmke-entity/minigpt-4-vicuna-7b/layer_08'
    assert (dependency / 'SYNC_VERIFIED').is_file(), 'Must finish and archive L8 evaluation before profiling'
    q.t.validate_eval(q.t.spec('mmke-entity', 'minigpt-4-vicuna-7b', 8), dependency)
    claim = q.D / 'claims' / (DATASET + '_' + MODEL + '.lock')
    with claim.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipts = [probe_layer(q, layer) for layer in LAYERS]
    result = dict(state='CALIBRATED', required_mib=max(x['required_mib'] for x in receipts),
                  policy='maximum of both layer measurements plus 2048 MiB margin, rounded up to 256 MiB',
                  layers=receipts)
    atomic(ROOT / 'measured_gate.json', result)
    return result


def install(q):
    previous_gpu = q.gpu
    measured = []

    def gpu(phase, instruct=False):
        if phase != 'train' or not instruct:
            return previous_gpu(phase, instruct=instruct)
        if not measured:
            measured.append(ensure(q))
        unused, evidence = previous_gpu(phase, instruct=True)
        evidence = dict(evidence)
        evidence.update(required_mib=measured[0]['required_mib'],
                        gate_policy='measured_instruct_L20_L17_first_epoch_plus_margin',
                        calibration_path=str(ROOT / 'measured_gate.json'),
                        calibration_layer_peaks=[x['accounted_peak_mib'] for x in measured[0]['layers']])
        return evidence['free_mib'] >= evidence['required_mib'], evidence

    q.gpu = gpu
