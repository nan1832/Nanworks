"""Dispatch the user-authorized eval inside the existing allocation, without altering other processes."""
from pathlib import Path
import base64, subprocess, shlex, sys
HERE=Path(__file__).resolve().parent
payload=base64.b64encode((HERE/'eval_existing_main_l3_l5.py').read_bytes()).decode('ascii')
py='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
remote='printf %s '+shlex.quote(payload)+' | base64 -d | '+shlex.quote(py)+' -u -'
cmd=['C:\\Windows\\System32\\OpenSSH\\ssh.exe','-i',str(Path.home()/'.ssh/id_ed25519_bridge'),
     '-o','BatchMode=yes','-o','ConnectTimeout=12','ph_teacher3@10.68.162.201',
     'srun --jobid=3435286 --overlap -w g08 --ntasks=1 --cpus-per-task=2 --time=00:30:00 bash -c '+shlex.quote(remote)]
with (HERE/'eval_execution.log').open('wb') as log:
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline,b''):
        log.write(line); log.flush()
        sys.stdout.buffer.write(line); sys.stdout.buffer.flush()
    raise SystemExit(proc.wait())
