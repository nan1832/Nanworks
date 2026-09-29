"""One-shot, identity-checked pause authorized on 2026-09-26."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_llava_job3443209_20260926')
EXPECTED = {
    1868056: ('261796620', 'append_mmke_llava_l7_3443209.py follow'),
    1864444: ('261714540', 'resume_mmke_entity_llava_3443209.py launch'),
    1864449: ('261714577', 'launcher_scoped.sh job3126082'),
    1864776: ('261718634', 'scripts/run_mmke_llava_shared_gpu_sweep.py'),
}

def identity(pid):
    p = Path('/proc') / str(pid)
    stat = (p / 'stat').read_text().split(') ', 1)[1].split()
    cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
    assert stat[19] == EXPECTED[pid][0] and EXPECTED[pid][1] in cmd
    assert str(ROOT) in cmd and 'job_3443209/' in (p / 'cgroup').read_text()
    return {'pid': pid, 'start_ticks': stat[19], 'cmd': cmd, 'state': stat[0]}

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

assert os.uname()[1].split('.')[0] == 'g09'
if len(sys.argv) > 1 and sys.argv[1] == 'verify':
    for pid in EXPECTED:
        assert not (Path('/proc') / str(pid)).exists(), str(pid)
    p = ROOT / 'pause_for_priority3_20260926/pause.json'
    data = json.loads(p.read_text())
    assert sha(Path(data['backup'])) == data['sha256']
    data['state'] = 'PAUSED_VERIFIED'
    data['stopped_at'] = time.strftime('%F %T %Z')
    data['verification_note'] = 'Initial post-signal check encountered a transient zombie; all four PIDs now absent.'
    p.write_text(json.dumps(data, indent=2))
    print(json.dumps(data, indent=2))
    sys.exit(0)
processes = [identity(p) for p in EXPECTED]
layer = ROOT / 'work/mmke-entity/llava-v1.5-7b/layer_01'
cp = next(layer.glob('records/**/epoch-17-i-5406-ema_loss-0.7862'))
expected_hash = '18149e4dcc14c199d00eb768568d04b31637b1d4ccab574138b92e50fd6ddc37'
assert sha(cp) == expected_hash
dest = ROOT / 'pause_for_priority3_20260926'
dest.mkdir(exist_ok=False)
shutil.copy2(str(cp), str(dest / cp.name))
assert sha(dest / cp.name) == expected_hash
shutil.copy2(str(layer / 'loss_history.csv'), str(dest / 'loss_history.csv'))
data = {'time': time.strftime('%F %T %Z'), 'state': 'PAUSE_PREPARED',
        'processes': processes, 'checkpoint': str(cp), 'backup': str(dest / cp.name),
        'sha256': expected_hash, 'resume_epoch': 18, 'resume_i': 5407,
        'llava_remaining_order': [1, 0, 2, 13, 11, 12, 4, 7],
        'priority_queue': [['mmke-visual', 'instructblip-vicuna-7b', 20],
                           ['mmke-entity', 'instructblip-vicuna-7b', 20],
                           ['mmke-entity', 'smolvlm-1.7b', 8]],
        'note': 'Current partial epoch18 is not checkpointed; no automatic LLaVA restart.'}
(dest / 'pause.json').write_text(json.dumps(data, indent=2))
# First stop the tail waiter and prevent the main launcher advancing while trainer exits.
for pid in [1868056, 1864449, 1864444]:
    identity(pid)
    os.kill(pid, signal.SIGSTOP)
for pid in [1868056, 1864449, 1864444, 1864776]:
    try:
        identity(pid)
        os.kill(pid, signal.SIGTERM)
        os.kill(pid, signal.SIGCONT)
    except FileNotFoundError:
        pass
for _ in range(20):
    remaining = []
    for pid in EXPECTED:
        try:
            if identity(pid)['state'] != 'Z':
                remaining.append(pid)
        except FileNotFoundError:
            pass
    if not remaining:
        break
    time.sleep(1)
assert not remaining, 'Still alive: %s; inspect, no broad kill' % remaining
data['state'] = 'PAUSED_VERIFIED'
data['stopped_at'] = time.strftime('%F %T %Z')
(dest / 'pause.json').write_text(json.dumps(data, indent=2))
print(json.dumps(data, indent=2))
