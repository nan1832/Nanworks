"""One-shot completion stage for the already-running Qwen repair; launches no GPU work."""
from pathlib import Path
import json
import subprocess
import sys
import time
from datetime import datetime
from lga_ablation_remote import ssh,BASE
from run_visedit_model_pred_mmke_20260929 import write

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'outputs/visedit_model_pred_mmke_20260929'
REMOTE=BASE+'/server_results/visedit_model_pred_mmke_20260929/qwen_repair_bf16_v2/control/status.json'

def main():
    import msvcrt
    with (LOCAL/'qwen_repair/finalizer.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        last=None
        while True:
            try:
                code="from pathlib import Path\nprint(Path(%r).read_text())\n"%REMOTE
                status=json.loads(ssh(code,timeout=60))
            except Exception as e:
                write(LOCAL/'qwen_repair/finalizer_status.json',dict(state='WAITING_SERVER_STATUS',error=str(e),time=datetime.now().astimezone().isoformat()))
                time.sleep(30);continue
            signature=(status['state'],status.get('dataset'),status.get('dtype'))
            if signature!=last:
                print(json.dumps(status),flush=True);last=signature
            write(LOCAL/'qwen_repair/finalizer_status.json',dict(state='WAITING_REPAIR_COMPLETION',server=status,time=datetime.now().astimezone().isoformat()))
            if status['state']=='NEEDS_REPAIR':
                write(LOCAL/'qwen_repair/finalizer_status.json',dict(state='NEEDS_REPAIR',server=status));return 1
            if status['state']=='DONE':break
            time.sleep(30)
        for name in ['sync_visedit_model_pred_mmke_20260929.py','verify_visedit_qwen_repair_20260929.py']:
            write(LOCAL/'qwen_repair/finalizer_status.json',dict(state='SYNCING_AND_VERIFYING',step=name,time=datetime.now().astimezone().isoformat()))
            result=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            output=result.stdout.decode('utf-8',errors='replace');print(output,flush=True)
            if result.returncode:
                write(LOCAL/'qwen_repair/finalizer_status.json',dict(state='LOCAL_BACKFILL_FAILED',step=name,returncode=result.returncode,error=output[-8000:]));return result.returncode
        write(LOCAL/'qwen_repair/finalizer_status.json',dict(state='DONE',completion_receipt=str(LOCAL/'completion_receipt.json'),time=datetime.now().astimezone().isoformat()))
        return 0

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
