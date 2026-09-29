"""One isolated, original-protocol epoch for memory measurement, not a formal run."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


class ProfileComplete(BaseException):
    pass


def atomic(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.partial')
    tmp.write_text(json.dumps(value, indent=2))
    tmp.replace(path)


def own_memory():
    output = subprocess.check_output(
        ['nvidia-smi', '--query-compute-apps=pid,used_memory',
         '--format=csv,noheader,nounits'], universal_newlines=True)
    for line in output.splitlines():
        pid, memory = line.split(',')
        if int(pid) == os.getpid():
            return int(memory)
    return 0


def install_epoch_probe(runner, report, torch):
    original = runner.train_with_synchronous_loading

    def profile(editor, total_epochs):
        assert total_epochs == 50 and editor.train_epoch == 1
        assert editor.data_generator.sample_count == 500
        report.update(stage='full_first_epoch', requested_epochs=total_epochs,
                      sample_count=500, optimizer_batches=0)
        train_batch = editor.train_a_batch

        def measured_batch(*args, **kwargs):
            result = train_batch(*args, **kwargs)
            report['optimizer_batches'] += 1
            return result

        editor.train_a_batch = measured_batch
        original(editor, 1)
        torch.cuda.synchronize()
        assert report['optimizer_batches'] == 250
        report.update(stage='complete_first_epoch', completed_epochs=1)
        # Stop before train_one_layer can select a formal checkpoint or write train.done.
        raise ProfileComplete()

    runner.train_with_synchronous_loading = profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    report_path = Path(request['report'])
    report = dict(status='running', pid=os.getpid(), stage='import',
                  budget_mib=request['allocator_budget_mib'],
                  fingerprint=request['fingerprint'], started=time.time())
    torch = None
    exit_code = 1
    try:
        import torch
        total = torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(
            request['allocator_budget_mib'] * 1024 ** 2 / total, 0)
        spec = importlib.util.spec_from_file_location('original_training_runner', request['runner'])
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        install_epoch_probe(runner, report, torch)
        report['stage'] = 'model_load_and_preprocessing'
        sys.argv = [request['runner']] + request['runner_args']
        runner.main()
        raise RuntimeError('Runner returned without completing the required probe epoch')
    except ProfileComplete:
        report['status'] = 'passed'
        exit_code = 0
    except Exception as error:
        report.update(status='oom' if 'out of memory' in str(error).lower() else 'failed',
                      error=repr(error), traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        if torch is not None and torch.cuda.is_initialized():
            report.update(max_allocated_mib=torch.cuda.max_memory_allocated(0) / 1024 ** 2,
                          max_reserved_mib=torch.cuda.max_memory_reserved(0) / 1024 ** 2,
                          current_reserved_mib=torch.cuda.memory_reserved(0) / 1024 ** 2)
            try:
                report['current_process_mib'] = own_memory()
            except Exception as error:
                report['process_query_error'] = repr(error)
        report['finished'] = time.time()
        atomic(report_path, report)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
