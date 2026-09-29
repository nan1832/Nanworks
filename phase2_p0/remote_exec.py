"""P0 transport: existing SSH identity, no credentials embedded."""
import argparse
import base64
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--node')
p.add_argument('--job-id',type=int)
p.add_argument('--python', default='/usr/bin/python3')
p.add_argument('--log', type=Path, required=True)
a = p.parse_args()
payload = base64.b64encode(a.source.read_bytes()).decode('ascii')
remote = f"echo {payload} | base64 -d | {a.python} -u -"
if a.job_id:
    import shlex
    if not a.node: raise ValueError('--job-id requires --node')
    remote = (f"srun --jobid={a.job_id} --overlap -w {shlex.quote(a.node)} --ntasks=1 "
              f"--cpus-per-task=2 --time=00:10:00 bash -c {shlex.quote(remote)}")
elif a.node:
    import shlex
    remote = f"ssh -o BatchMode=yes -o ConnectTimeout=12 {shlex.quote(a.node)} {shlex.quote(remote)}"
cmd = [r'C:\Windows\System32\OpenSSH\ssh.exe', '-i',
       str(Path.home()/'.ssh/id_ed25519_bridge'), '-o', 'BatchMode=yes',
       '-o', 'ConnectTimeout=12', 'ph_teacher3@10.68.162.201', remote]
a.log.parent.mkdir(parents=True, exist_ok=True)
with a.log.open('wb') as log:
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(process.stdout.readline, b''):
        log.write(line)
        log.flush()
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()
    raise SystemExit(process.wait())
