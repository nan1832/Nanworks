"""Use the existing g08 allocation, respecting its shared project GPU lock."""
import datetime,fcntl,json,os,subprocess,time
from pathlib import Path
B=Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2")
ROOT=B/"server_results/no_edit_baseline_audit_20260929/aligned_v2";CONTROL=ROOT/"control"
MODELS=["blip2-opt-2.7b","llava-v1.5-7b","smolvlm-1.7b","instructblip-vicuna-7b",
        "minigpt-4-vicuna-7b","paligemma-3b","qwen2.5-vl-3b-instruct"]
PY="/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python"
QPY=str(B/"envs/qwen25vl/bin/python")
def now():return datetime.datetime.now().astimezone().isoformat()
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+".partial");t.write_text(json.dumps(d,indent=2));t.replace(p)
def state(name,**kw):
    d=dict(state=name,time=now(),node="g08",job="3435286",pid=os.getpid(),**kw)
    write(CONTROL/"status.json",d);print(json.dumps(d),flush=True)
def allocation():
    assert os.uname()[1].split(".")[0]=="g08"
    assert "job_3435286" in Path("/proc/self/cgroup").read_text()
    assert subprocess.check_output(["squeue","-j","3435286","-h","-o","%T %N"],
                                   universal_newlines=True).strip()=="RUNNING g08"
def free():
    return int(subprocess.check_output(["nvidia-smi","-i","0","--query-gpu=memory.free",
               "--format=csv,noheader,nounits"],universal_newlines=True).strip())
def main():
    CONTROL.mkdir(exist_ok=True);allocation()
    own=(CONTROL/"controller.lock").open("a");fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
    outcomes=[]
    for model in MODELS:
        accepted=list((ROOT/"groups").glob("*/"+model+"/accepted.json"))
        if len(accepted)==3:continue
        stable=0;lock=None
        while lock is None:
            allocation()
            if (CONTROL/"STOP").exists():state("STOPPED",outcomes=outcomes);return
            available=free();stable=stable+1 if available>=60000 else 0
            if stable>=2:
                f=(B/"server_results/gpu_locks/g08_gpu0.lock").open("a")
                try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:f.close();stable=0
                else:lock=f
            if lock is None:
                state("WAITING_MEMORY_OR_EXISTING_GROUP",model=model,free_mib=available,
                      required_mib=60000,outcomes=outcomes);time.sleep(15)
        try:
            allocation();assert free()>=60000
            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES="0",SLURM_JOB_ID="3435286",
                 HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",OMP_NUM_THREADS="2",
                 MKL_NUM_THREADS="2",PYTHONUNBUFFERED="1")
            command=[QPY if model.startswith("qwen") else PY,"-u",str(ROOT/"code/evaluate.py"),"--model",model]
            log=CONTROL/(model+"_"+time.strftime("%H%M%S")+".log")
            with log.open("x") as stream:
                child=subprocess.Popen(command,cwd=str(B/"VisEdit-main"),env=env,stdin=subprocess.DEVNULL,
                     stdout=stream,stderr=subprocess.STDOUT)
                state("RUNNING",model=model,child_pid=child.pid,log=str(log),command=command,outcomes=outcomes)
                rc=child.wait()
            outcomes.append(dict(model=model,returncode=rc,log=str(log),time=now()))
            write(CONTROL/"outcomes.json",outcomes)
        finally:lock.close()
    complete=len(list((ROOT/"groups").glob("*/*/accepted.json")))
    state("DONE" if complete==21 else "NEEDS_REPAIR",completed_groups=complete,outcomes=outcomes)
if __name__=="__main__":
    try:main()
    except Exception as exc:state("ERROR",error=repr(exc));raise
