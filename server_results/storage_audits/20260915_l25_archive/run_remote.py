"""Run a reviewed Python evidence script through system SSH; save raw output."""
import argparse, base64, pathlib, shlex, subprocess, sys
p=argparse.ArgumentParser()
p.add_argument('source',type=pathlib.Path)
p.add_argument('--node')
p.add_argument('--python',default='/usr/bin/python3')
p.add_argument('--log',required=True,type=pathlib.Path)
a=p.parse_args()
payload=base64.b64encode(a.source.read_bytes()).decode('ascii')
remote=shlex.quote(a.python)+' -u -c '+shlex.quote("import base64;exec(compile(base64.b64decode('"+payload+"'),'<p0_remote>','exec'))")
if a.node:remote='ssh -o BatchMode=yes -o ConnectTimeout=10 '+shlex.quote(a.node)+' '+shlex.quote(remote)
cmd=[r'C:\Windows\System32\OpenSSH\ssh.exe','-i',str(pathlib.Path.home()/'.ssh/id_ed25519_bridge'),'-o','BatchMode=yes','-o','ConnectTimeout=10','bridge-server',remote]
with a.log.open('wb') as log:
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in iter(p.stdout.readline,b''):
        log.write(line);log.flush()
    rc=p.wait()
print('remote return code:',rc,'raw log:',a.log)
sys.exit(rc)
