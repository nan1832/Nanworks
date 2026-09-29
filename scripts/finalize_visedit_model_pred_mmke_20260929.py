"""One-shot postprocessing dependency: wait for this queue to exit, then sync."""
import json
from pathlib import Path
import subprocess
import sys
import traceback
from datetime import datetime
from lga_ablation_remote import ssh, BASE

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT/'outputs/visedit_model_pred_mmke_20260929'


def main():
    receipt = LOCAL/'finalizer_status.json'
    def state(status, **extra):
        receipt.write_text(json.dumps(dict(state=status,time=datetime.now().astimezone().isoformat(),**extra),indent=2),encoding='utf-8')
    state('WAITING_QUEUE_EXIT', controller_pid=3538983)
    try:
        code = '''
import subprocess,json
from pathlib import Path
root=Path(__ROOT__)
nodecode="""
import subprocess,json
from pathlib import Path
root=Path(__ROOT__)
pid=3538983
cmd=Path('/proc')/str(pid)/'cmdline'
if cmd.exists():
 assert b'queue_visedit_model_pred_mmke_20260929.py' in cmd.read_bytes()
 subprocess.run(['tail','--pid='+str(pid),'-f','/dev/null'],check=True)
print((root/'control/status.json').read_text())
""".replace('__ROOT__',repr(str(root)))
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ServerAliveInterval=30','g08','python3 -'],input=nodecode,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
if p.returncode:raise RuntimeError(p.stderr+p.stdout)
print(p.stdout)
'''.replace('__ROOT__',repr(BASE+'/server_results/visedit_model_pred_mmke_20260929'),1)
        server = json.loads(ssh(code, timeout=21600))
        state('SYNCHRONIZING',server=server)
        subprocess.run([sys.executable,str(ROOT/'scripts/sync_visedit_model_pred_mmke_20260929.py')],cwd=str(ROOT),check=True)
        completion=LOCAL/'completion_receipt.json'
        if completion.exists() and json.loads(completion.read_text())['verified_groups']==14:
            state('DONE',completion_receipt=str(completion),server=server)
        else:
            state('NEEDS_REPAIR',server=server)
    except Exception:
        state('ERROR',error=traceback.format_exc())
        raise


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
