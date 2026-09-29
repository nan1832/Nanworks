"""Transport for this explicitly authorized baseline audit. No import-time work."""
import json
import os
from pathlib import Path
import subprocess
import sys

LOCAL = Path(__file__).resolve().parent
BASE = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2"
PROJECT = BASE + "/VisEdit-main"
REMOTE = BASE + "/server_results/no_edit_baseline_audit_20260929/aligned_v2"
SSH = r"C:\Windows\System32\OpenSSH\ssh.exe"


def ssh(code, timeout=180):
    args = [SSH, "-i", str(Path.home()/".ssh/id_ed25519_bridge"),
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
            "bridge-server", "python3 -"]
    p = subprocess.run(args, input=code.encode("utf-8"), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "replace") + p.stdout.decode("utf-8", "replace"))
    return p.stdout.decode("utf-8")


def node(code, hostname, timeout=180):
    bridge = """import subprocess
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',%r,'python3 -'],
input=%r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=%r)
print(p.stdout,end='')
if p.returncode:raise RuntimeError(p.stderr)
""" % (hostname, code, timeout-15)
    return ssh(bridge, timeout)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    code = Path(sys.argv[1]).read_text(encoding="utf-8")
    result = node(code, sys.argv[3]) if len(sys.argv) > 3 else ssh(code)
    if len(sys.argv) > 2:
        (LOCAL/sys.argv[2]).write_text(result, encoding="utf-8")
        print(json.dumps(dict(saved=str(LOCAL/sys.argv[2]),characters=len(result))))
    else:
        print(result, end="")
