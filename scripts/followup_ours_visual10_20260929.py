"""Authorized, bounded repair of three visual10 groups after the current queue.

The original queue, source data, frozen answers, thresholds and failed artifacts
remain intact. One fresh, historical layer-major rerun is allowed per group.
Only a complete rerun passing the original verifier may publish recommendations.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
ROOT = BASE / 'server_results/ours_visual10_20260929'
FOLLOWUP = ROOT / 'followup_20260929'
TARGETS = [('mmke-entity', 'paligemma-3b'),
           ('evqa-pilot500', 'qwen2.5-vl-3b'),
           ('mmke-visual', 'qwen2.5-vl-3b')]
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
QPY = str(BASE / 'envs/qwen25vl/bin/python')
FIELDS = {'dot': 'S_v_dot', 'cos': 'S_v_cos',
          'old_norm': 'S_v_old_norm', 'new_norm': 'S_v_new_norm',
          'no_direction': 'S_v_joint_norm'}


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.partial.' + str(os.getpid()))
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp), str(path))


def emit(state, **values):
    value = dict(state=state, time=now(), pid=os.getpid(), job='3435286',
                 node='g08', followup=True, **values)
    write(FOLLOWUP / 'status.json', value)
    print(json.dumps(value, ensure_ascii=False), flush=True)


def original():
    sys.path.insert(0, str(ROOT / 'code'))
    import ours_visual10_20260929
    return ours_visual10_20260929


def process_identity(pid):
    p = Path('/proc') / str(pid)
    try:
        stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        return dict(pid=int(pid), start_ticks=stat[19], state=stat[0],
                    cmd=(p / 'cmdline').read_bytes().replace(b'\0', b' ').decode())
    except FileNotFoundError:
        return None


def same_live_process(expected, actual):
    return bool(actual and actual['state'] != 'Z' and
                all(expected[k] == actual[k] for k in ['pid', 'start_ticks', 'cmd']))


def gate_ready(queue_state, summary_state, controller_alive, child_alive):
    return (queue_state in ['FINISHED_WITH_PENDING', 'DONE'] and
            summary_state in ['done', 'needs_reproduction_review'] and
            not controller_alive and not child_alive)


def check_allocation():
    assert os.uname()[1].split('.')[0] == 'g08', 'Wrong node'
    assert 'job_3435286' in Path('/proc/self/cgroup').read_text(), 'Wrong Slurm allocation'
    state = subprocess.check_output(
        ['squeue', '-j', '3435286', '-h', '-o', '%T %N'], universal_newlines=True).strip()
    assert state == 'RUNNING g08', 'Allocation no longer RUNNING on g08: ' + state
    assert not (FOLLOWUP / 'STOP').exists(), 'Follow-up STOP requested'


def check_pins():
    for name, digest in read(FOLLOWUP / 'contract.json')['pins'].items():
        assert sha(name) == digest, 'Pinned code changed: ' + name


def wait_for_original():
    contract = read(FOLLOWUP / 'contract.json')
    deadline = time.monotonic() + 48 * 3600
    while time.monotonic() < deadline:
        check_allocation()
        check_pins()
        s = read(ROOT / 'control/status.json')
        p = ROOT / 'raw/visual/mmke-entity/instructblip-vicuna-7b/summary.json'
        summary = read(p) if p.exists() else {}
        alive = [same_live_process(x, process_identity(x['pid']))
                 for x in contract['wait_processes']]
        if gate_ready(s['state'], summary.get('status'), alive[0], alive[1]):
            assert summary.get('sample_count') == 636, 'Current computation is not complete'
            return
        if not any(alive) and s['state'] in ['FINISHED_WITH_PENDING', 'DONE']:
            raise RuntimeError('Current InstructBLIP computation did not finish; follow-up gate stays closed')
        if (ROOT / 'control/failure.json').exists() and not any(alive):
            raise RuntimeError('Original controller failed; do not infer successful completion')
        emit('WAITING_CURRENT_GROUP', original_queue_state=s['state'],
             model='instructblip-vicuna-7b', dataset='mmke-entity',
             current_summary=summary.get('status', 'running'), original_processes_alive=alive)
        time.sleep(60)
    raise RuntimeError('48 hour wait limit reached')


def verify_inputs(protocol):
    changed = [name for name, digest in protocol['files'].items()
               if not Path(name).is_file() or sha(name) != digest]
    assert not changed, 'Protocol inputs changed: ' + repr(changed)


def mean_checks(rows, historical):
    assert len(rows) == len(historical)
    checks = []
    for row, h in zip(rows, historical):
        assert int(row['layer']) == int(h['layer'])
        for field, column in FIELDS.items():
            actual, expected = float(row[field]), float(h[column])
            assert math.isfinite(actual) and math.isfinite(expected)
            error = abs(actual - expected)
            tolerance = max(1e-8, 1e-3 * max(abs(actual), abs(expected)))
            checks.append(dict(layer=int(row['layer']), field=field, actual=actual,
                               expected=expected, abs_error=error, allowed_error=tolerance,
                               tolerance_ratio=error / tolerance,
                               passed=math.isclose(actual, expected, rel_tol=1e-3, abs_tol=1e-8)))
    return checks


def validate_records(records, protocol, layers, formula_check):
    cohort = {x['sample_id']: x for x in protocol['cohort']}
    assert len(cohort) == len(protocol['cohort']) == len(records)
    assert {x['sample_id'] for x in records} == set(cohort)
    for record in records:
        assert all(record[k] == cohort[record['sample_id']][k]
                   for k in ['sample_id', 'sample_i', 'old', 'new'])
        assert set(record['layers']) == {str(l) for l in range(layers)}
        for pair in record['layers'].values():
            formula_check(pair)


def diagnose(dataset, model):
    mod = original()
    import run_lga_two_space_ablation as helper
    out = ROOT / 'raw/visual' / dataset / model
    s, protocol = read(out / 'summary.json'), read(out / 'protocol.json')
    verify_inputs(protocol)
    for name, field in [('protocol.json', 'protocol_sha256'),
                        ('layer_scores.json', 'score_sha256'),
                        ('historical_reproduction.json', 'reproduction_sha256')]:
        assert sha(out / name) == s[field], 'Prior artifact changed: ' + name
    assert set(p.name for p in (out / 'samples').glob('*.json')) == set(s['sample_files'])
    records = []
    for name, digest in s['sample_files'].items():
        p = out / 'samples' / name
        assert sha(p) == digest, 'Prior sample changed: ' + str(p)
        records.append(read(p))
    validate_records(records, protocol, mod.MODELS[model], mod.formula_values)
    baseline = mod.baseline(dataset, model)
    assert len(records) == s['sample_count'] == int(baseline[0]['n_request'])
    rows = helper.aggregate(records, [x['sample_id'] for x in records], mod.MODELS[model])
    recorded_rows = read(out / 'layer_scores.json')['rows']
    for a, b in zip(rows, recorded_rows):
        assert int(a['layer']) == int(b['layer'])
        assert all(math.isclose(a[k], b[k], rel_tol=1e-12, abs_tol=1e-15) for k in FIELDS)
    checks = mean_checks(rows, baseline)
    failures = [x for x in checks if not x['passed']]
    field_counts = dict(collections.Counter(x['field'] for x in failures))
    report = dict(time=now(), dataset=dataset, model=model, samples=len(records),
                  original_summary_status=s['status'], checks=checks, failures=len(failures),
                  failed_fields=field_counts, failed_layers=sorted({x['layer'] for x in failures}),
                  source_hashes_match=True, cohort_and_targets_match=True,
                  stored_scores_reaggregate=True, old_summary_sha256=sha(out / 'summary.json'),
                  diagnosis='historical_gradient_statistics_mismatch' if failures else 'reproduction_passed',
                  root_cause='Not yet established; failed statistics are quantified, not excused.',
                  retry_strategy='One fresh layer-major run using the historical single-layer helper; unchanged dtype, targets and thresholds.')
    write(FOLLOWUP / 'diagnostics' / dataset / (model + '.json'), report)
    return report


def gpu_lock(dataset, model):
    import fcntl
    stable = 0
    while True:
        check_allocation()
        check_pins()
        free = int(subprocess.check_output(
            ['nvidia-smi', '-i', '0', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
            universal_newlines=True).strip())
        stable = stable + 1 if free >= 60000 else 0
        emit('WAITING_REPAIR_GPU', dataset=dataset, model=model, free_mib=free,
             required_mib=60000, stable=stable)
        if stable >= 3:
            handle = (BASE / 'server_results/gpu_locks/g08_gpu0.lock').open('a')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                stable = 0
            else:
                free2 = int(subprocess.check_output(
                    ['nvidia-smi', '-i', '0', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                    universal_newlines=True).strip())
                if free2 >= 60000:
                    return handle
                handle.close()
                stable = 0
        time.sleep(20)


def retry_group(dataset, model):
    """Fresh results only: no reuse of the old failed gradient records."""
    assert (dataset, model) in TARGETS
    check_allocation()
    check_pins()
    mod = original()
    import run_lga_two_space_ablation as collector
    import torch
    old_out = ROOT / 'raw/visual' / dataset / model
    old_protocol = read(old_out / 'protocol.json')
    verify_inputs(old_protocol)
    args = argparse.Namespace(project_dir=str(BASE / 'VisEdit-main'), source_root=str(BASE / 'server_results'),
                              out_root=str(FOLLOWUP / 'retry_raw'), space='visual', dataset=dataset,
                              model=model, device='cuda:0', layer_batch_size=4, stop_after=0, preflight=False)
    helper, _, cfg, baseline, cohort, out, vllm = collector.prepare(args)
    protocol = read(out / 'protocol.json')
    assert protocol['cohort'] == old_protocol['cohort'], 'Retry cohort/targets drifted'
    assert protocol['files'] == old_protocol['files'], 'Retry input implementation drifted'
    assert protocol['torch'] == old_protocol['torch'], 'Torch version drifted'
    assert protocol['python'] == old_protocol['python'], 'Python version drifted'
    assert not (out / 'summary.json').exists(), 'Bounded retry already attempted'
    # No backend/precision changes. Record the runtime for numerical diagnosis.
    runtime = dict(time=now(), mode='historical_single_layer_layer_major',
                   dtype_counts=dict(collections.Counter(str(p.dtype) for p in vllm.model.parameters())),
                   torch=torch.__version__, cpu_threads=torch.get_num_threads(),
                   cuda=torch.version.cuda, deterministic=torch.are_deterministic_algorithms_enabled())
    write(out / 'execution.json', runtime)
    modules = {l: helper.find_module(vllm.model, cfg.layer_module_tmp.format(l))
               for l in range(mod.MODELS[model])}
    historical = {}
    with (mod.source(dataset, model) / 'ours_direct_sample_layer_scores.jsonl').open(encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            historical[str(x['sample_id']), int(x['layer'])] = x
    report = read(FOLLOWUP / 'diagnostics' / dataset / (model + '.json'))
    probe_layer = report['failed_layers'][0] if report['failed_layers'] else 0
    probe_samples = {0, len(cohort)//2, len(cohort)-1}
    records = {x['sample_id']: dict(sample_id=x['sample_id'], sample_i=x['sample_i'],
                                   old=x['old'], new=x['new'], layers={}) for x in cohort}
    probes, started, completed = [], time.time(), 0
    for layer, module in modules.items():
        check_allocation()
        check_pins()
        layer_records = []
        for i, item in enumerate(cohort):
            req = item['row']['request']
            a = helper.compute_virtual_delta_target_grad(vllm, module, req['prompt'], req['image'], item['old'], 1e-8)
            b = helper.compute_virtual_delta_target_grad(vllm, module, req['prompt'], req['image'], item['new'], 1e-8)
            stats = collector.cross_stats(helper.grad_stats(a['visual_grad'], b['visual_grad'], 1e-8))
            mod.formula_values(stats)
            old = historical[item['sample_id'], layer]
            assert str(old['old_answer']).strip() == item['old'] and str(old['target_new']) == item['new']
            assert list(a['visual_span']) == list(old['visual_span']), 'Historical visual token span changed'
            assert list(a['visual_span']) == list(b['visual_span'])
            if layer == probe_layer and i in probe_samples:
                a2 = helper.compute_virtual_delta_target_grad(vllm, module, req['prompt'], req['image'], item['old'], 1e-8)
                b2 = helper.compute_virtual_delta_target_grad(vllm, module, req['prompt'], req['image'], item['new'], 1e-8)
                previous = read(old_out / 'samples' / ('%06d.json' % item['sample_i']))['layers'][str(layer)]
                probes.append(dict(sample_i=item['sample_i'], layer=layer,
                    old_loss=a['loss'], historical_old_loss=old['old_loss'],
                    new_loss=b['loss'], historical_new_loss=old['new_loss'],
                    repeat_old_max_abs=float((a['visual_grad']-a2['visual_grad']).abs().max()),
                    repeat_new_max_abs=float((b['visual_grad']-b2['visual_grad']).abs().max()),
                    repeat_old_close=bool(torch.allclose(a['visual_grad'],a2['visual_grad'],rtol=1e-5,atol=1e-7)),
                    repeat_new_close=bool(torch.allclose(b['visual_grad'],b2['visual_grad'],rtol=1e-5,atol=1e-7)),
                    stats=stats, prior_stats={k:previous[k] for k in ['dot','cos','old_norm','new_norm']}))
                write(out / 'numerical_probe.json', dict(time=now(), probes=probes))
                del a2, b2
            records[item['sample_id']]['layers'][str(layer)] = stats
            layer_records.append(dict(sample_id=item['sample_id'], sample_i=item['sample_i'], stats=stats))
            del a, b
            completed += 1
            vllm.model.zero_grad(set_to_none=True)
            if (i+1) % 25 == 0:
                torch.cuda.empty_cache()
            if (i+1) % 25 == 0 or i+1 == len(cohort):
                progress = dict(time=now(), dataset=dataset, model=model, layer=layer,
                                sample_in_layer=i+1, samples_per_layer=len(cohort),
                                completed_pairs=completed, total_pairs=len(cohort)*len(modules),
                                elapsed_seconds=time.time()-started)
                write(out / 'progress.json', progress)
                print(json.dumps(progress), flush=True)
        write(out / 'layer_checkpoints' / ('L%02d.json' % layer), layer_records)
    records = [records[x['sample_id']] for x in cohort]
    validate_records(records, protocol, len(modules), mod.formula_values)
    rows = collector.aggregate(records, [x['sample_id'] for x in cohort], len(modules))
    checks = mean_checks(rows, baseline)
    verify_inputs(protocol)
    for record in records:
        write(out / 'samples' / ('%06d.json' % record['sample_i']), record)
    write(out / 'layer_scores.json', dict(rows=rows))
    write(out / 'historical_reproduction.json', checks)
    s = dict(status='done' if all(x['passed'] for x in checks) else 'needs_reproduction_review',
             time=now(), sample_count=len(records), collector_sha256=sha(__file__),
             score_sha256=sha(out/'layer_scores.json'), protocol_sha256=sha(out/'protocol.json'),
             reproduction_sha256=sha(out/'historical_reproduction.json'),
             baseline_failures=sum(not x['passed'] for x in checks),
             sample_files={p.name:sha(p) for p in (out/'samples').glob('*.json')},
             execution='historical_single_layer_layer_major', prior_output=str(old_out))
    write(out/'summary.json', s)
    write(out/'comparison.json', dict(prior_failures=report['failures'], retry_failures=s['baseline_failures'],
          repeat_probe_close=all(x['repeat_old_close'] and x['repeat_new_close'] for x in probes),
          conclusion='Fresh historical-order rerun passed.' if s['status']=='done' else 'Mismatch persists; do not publish or relax thresholds.',
          root_cause='Exact numerical source not proven; see field errors and repeated-gradient probes.'))
    if s['status'] != 'done':
        return 2
    mod.verify_full(out, dataset, model, baseline)
    return 0


def publish_retry(dataset, model):
    mod = original()
    p = FOLLOWUP / 'retry_raw/visual' / dataset / model
    baseline = mod.baseline(dataset, model)
    rows, evidence = mod.verify_full(p, dataset, model, baseline)
    gpath = ROOT / 'published' / dataset / (model + '.json')
    g = read(gpath)
    assert g['status'] == 'pending_cross_terms', 'Another result was published; preserve it for review'
    backup = FOLLOWUP / 'pre_publish' / dataset / (model + '.json')
    assert not backup.exists(), 'Already published by this follow-up'
    write(backup, g)
    g.update(time=now(), status='done', evidence=evidence,
             repair_provenance=str(p / 'comparison.json'),
             formulas={k:dict(mod.rank([row[k] for row in rows]),
                             source_kind='verified_sample_products') for k in mod.FORMULAS})
    write(gpath, g)
    manifest = read(ROOT / 'manifest.json')
    for relative in manifest['files']:
        manifest['files'][relative] = sha(ROOT / relative)
    groups = [read(ROOT / relative) for relative in manifest['files']]
    manifest.update(time=now(), complete_groups=sum(x['status']=='done' for x in groups),
                    complete_formula_groups=sum(len(x['formulas']) for x in groups),
                    followup=str(FOLLOWUP))
    write(ROOT / 'manifest.json', manifest)


def queue():
    import fcntl
    check_allocation()
    own = (FOLLOWUP / 'controller.lock').open('a')
    fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
    check_pins()
    wait_for_original()
    outcomes = []
    for dataset, model in TARGETS:
        check_allocation()
        check_pins()
        if read(ROOT/'published'/dataset/(model+'.json'))['status'] == 'done':
            outcomes.append(dict(dataset=dataset,model=model,state='ALREADY_VERIFIED'))
            continue
        emit('DIAGNOSING_VISUAL10',dataset=dataset,model=model,outcomes=outcomes)
        try:
            report = diagnose(dataset, model)
            assert report['failures'] > 0, 'Prior failure is not reproducible; inspect rather than rerun blindly'
            lock = gpu_lock(dataset, model)
            try:
                env = os.environ.copy()
                env.update(CUDA_VISIBLE_DEVICES='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                           OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
                log = FOLLOWUP / 'logs' / (dataset+'_'+model+'.log')
                log.parent.mkdir(parents=True,exist_ok=True)
                with log.open('x') as stream:
                    child = subprocess.Popen([QPY if model.startswith('qwen') else PY, '-B', '-u',
                        str(Path(__file__).resolve()),'retry','--dataset',dataset,'--model',model],
                        cwd=str(BASE/'VisEdit-main'),env=env,stdin=subprocess.DEVNULL,
                        stdout=stream,stderr=subprocess.STDOUT)
                    emit('RUNNING_VISUAL10_REPAIR',dataset=dataset,model=model,child_pid=child.pid,
                         log=str(log),prior_failures=report['failures'],outcomes=outcomes)
                    code = child.wait()
                if code == 0:
                    publish_retry(dataset,model)
                outcomes.append(dict(dataset=dataset,model=model,returncode=code,log=str(log),
                                     state='VERIFIED_AND_PUBLISHED' if code==0 else 'RETRY_NEEDS_INSPECTION'))
            finally:
                lock.close()
        except Exception:
            error=traceback.format_exc()
            write(FOLLOWUP/'errors'/dataset/(model+'.json'),dict(time=now(),error=error))
            outcomes.append(dict(dataset=dataset,model=model,state='BLOCKED',error=error))
        write(FOLLOWUP/'outcomes.json',outcomes)
    complete = read(ROOT/'manifest.json')['complete_groups']
    emit('DONE' if complete==21 else 'FINISHED_WITH_PENDING',outcomes=outcomes,
         complete_groups=complete,scope='Only the three user-authorized groups; no further automatic retries.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['queue','retry'])
    parser.add_argument('--dataset');parser.add_argument('--model')
    args=parser.parse_args()
    if args.action=='retry':
        sys.exit(retry_group(args.dataset,args.model))
    try:
        queue()
    except Exception:
        emit('STOPPED_REQUIRES_INSPECTION',error=traceback.format_exc())
        raise
