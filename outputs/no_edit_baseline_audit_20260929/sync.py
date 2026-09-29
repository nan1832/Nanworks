"""Verify server artifacts, synchronize compact evidence, and update only our ledger section."""
import argparse,base64,csv,datetime,hashlib,io,json,sys,time,traceback
from pathlib import Path
from remote import LOCAL,REMOTE,BASE,ssh
METRICS=["Rel","T-Gen","M-Gen","T-Loc","M-Loc","Average"]
ROOT=LOCAL.parents[1]
DOC=ROOT/"md/Location/SWeeplayers.md"
BEGIN="<!-- NO_EDIT_BASELINE_AUDIT_20260929_BEGIN -->"
END="<!-- NO_EDIT_BASELINE_AUDIT_20260929_END -->"
def write(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+".partial");t.write_text(data,encoding="utf-8");t.replace(p)
def collect():
    known={}
    for p in (LOCAL/"groups").glob("*/*/accepted.json"):
        known[p.parent.relative_to(LOCAL/"groups").as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    code="""import base64,datetime,hashlib,json,math
from pathlib import Path
root=Path(%r);known=%r
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
out=dict(time=datetime.datetime.now().astimezone().isoformat(),accepted=[],progress=[],errors=[],transfers={})
p=root/'control/status.json'
out['worker']=read(p) if p.exists() else {}
out['launch']=read(root/'control/launch.json')
for group in sorted((root/'groups').glob('*/*')):
    p=group/'accepted.json'
    if p.exists():
        a=read(p);rows=read(group/'accepted_scores.json')
        assert a['scores_sha256']==sha(group/'accepted_scores.json')
        assert a['spotcheck_sha256']==sha(group/'spotcheck.json')
        assert a['cohort_sha256']==sha(group/'cohort.json')
        assert a['alignment_sha256']==sha(group/'alignment.json')
        assert len(rows)==a['sample_count']
        values={m:100*sum(r['scores'][m] for r in rows)/len(rows) for m in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc']}
        values['Average']=sum(values.values())/5
        assert all(abs(values[k]-a['metrics'][k])<1e-8 for k in values)
        key=group.relative_to(root/'groups').as_posix()
        out['accepted'].append(a)
        if known.get(key)!=sha(p):
            out['transfers'][key]={n:base64.b64encode((group/n).read_bytes()).decode()
              for n in ['accepted.json','accepted_scores.json','spotcheck.json','alignment.json']}
    elif (group/'progress.json').exists():out['progress'].append(read(group/'progress.json'))
for p in (root/'control').glob('*_error.json'):out['errors'].append(read(p))
log=out['worker'].get('log')
if log and Path(log).exists():
    with Path(log).open('rb') as f:
        f.seek(max(0,Path(log).stat().st_size-2500));out['log_tail']=f.read().decode('utf-8','replace')
print(json.dumps(out))
"""%(REMOTE,known)
    result=json.loads(ssh(code,timeout=120))
    for key,files in result.pop("transfers").items():
        for name,body in files.items():
            p=LOCAL/"groups"/key/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(body))
    write(LOCAL/"latest_status.json",json.dumps(result,indent=2,ensure_ascii=False))
    return result
def render(snapshot):
    alignment=json.loads((LOCAL/"alignment.json").read_text(encoding="utf-8"))["groups"]
    accepted={(r["dataset"],r["model"]):r for r in snapshot["accepted"]}
    rows=[]
    for g in alignment:
        key=(g["dataset"],g["model"]);a=accepted.get(key)
        values=a["metrics"] if a else g["historical_metrics_reaggregated"]
        status=("本次完整重评" if a["mode"]=="FULL_CURRENT_COHORT_REEVALUATED" else "历史重算＋GPU抽检通过") if a else "历史重算；GPU核验待完成"
        rows.append(dict(dataset=g["dataset"],model=g["model"],samples=g["sample_count"],
                         status=status,verified=bool(a),mode=a["mode"] if a else "PENDING_GPU_VERIFICATION",
                         **values,historical_source=g["historical_results"],eval_data_sha256=g["eval_data_sha256"]))
    csvout=io.StringIO();writer=csv.DictWriter(csvout,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(LOCAL/"no_edit_baselines.csv",csvout.getvalue())
    # Arithmetic layer deltas are marked with baseline status; no new ranking or layer selection.
    baseline={(r["dataset"],r["model"]):r for r in rows}
    gains=[]
    ledger=ROOT/"outputs/sweep_ledger_20260928_110311/sweep_results.csv"
    for r in csv.DictReader(ledger.open(encoding="utf-8-sig")):
        model="qwen2.5-vl-3b-instruct" if r["model"].startswith("qwen") else r["model"]
        b=baseline.get((r["dataset"],model))
        if b is None or int(r["samples"])!=b["samples"]:continue
        out={k:r[k] for k in ["dataset","model","layer","recipe","epoch","samples"]}
        out["baseline_status"]=b["status"]
        out["comparison_scope"]="summary differences against aligned standard cohort; representative edited protocol verified"
        for metric in METRICS:
            out["Before_"+metric]=b[metric];out["After_"+metric]=float(r[metric])
            out["Delta_"+metric]=float(r[metric])-b[metric]
        gains.append(out)
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(gains[0]));w.writeheader();w.writerows(gains)
    write(LOCAL/"editing_gain_vs_no_edit.csv",s.getvalue())
    link=lambda name:f"[{name}](<{(LOCAL/name).as_posix()}>)"
    worker=snapshot["worker"]
    lines=[BEGIN,"","## 未编辑基线：当前评测集对齐与 GPU 核验（2026-09-29）","",
      f"服务器核验时间：**{snapshot['time']}**。已完成 GPU 核验/重评 **{len(accepted)}/21** 组。下表的状态区分历史重算、抽检通过和本次完整重评。",
      "",
      f"运行位置：**G08 / GPU 0 / Slurm Job 3435286**；控制状态 **{worker.get('state','UNKNOWN')}**。控制器 PID：{worker.get('pid','待确认')}。启动时间：{snapshot['launch']['time']}。",
      "G09 正在进行既有 MiniGPT4 训练；本队列使用 G08 的共享 GPU 锁，显存不足或其他组持锁时等待，不终止既有任务。",
      "",
      "### 对齐与评分口径","",
      "- 7 个骨干各评一次相同骨干、数据与输入配置的 no-edit 状态；不按插入层重复运行，不加载任何 adapter。",
      "- 已逐条匹配当前标准评测集的图像、问题和新目标 alt：E-VQA 2,093 条，MMKE-Visual 293 条，MMKE-Entity 954 条。配置缺失的两组以保存的编辑后逐样本输入核验。",
      "- 旧 MMKE-Entity 为 955 条；当前 954 条不包含旧索引 403（entity-eval-403-Brown_Swiss_cattle_10）。按既有评测集排除后重算，未根据分数选择样本。",
      "- Rel/T-Gen/M-Gen 为相同新目标上的 teacher-forcing token accuracy。T-Loc/M-Loc 是不编辑时的自一致性，基线为 100，不代表 locality 参考答案全答对。",
      "- 旧 MMKE locality 的 prompt/图像路径与当前协议存在差异，不能复用其预测文本作逐条 locality 分析；当前输入另做重复前向一致性抽检，表中 locality 表示 no-edit 恒等基线。",
      "- 每组预先固定 12 个均匀覆盖的样本作 GPU 核验。历史分数与重算相差超过保存时 4 位小数的舍入误差，或输入不匹配时，自动完整重评该组。抽检通过不冒充完整重评。",
      "- 历史逐样本分数只保存 4 位小数，重聚合的百分制误差上界约 0.005 个百分点；正式表保留三位小数，CSV 保存计算精度。",
      "- 本节的 21 组基线单独登记，不计入上文 433 条按层区分的训练结果；main、stable 和复测未被合并或择优替换。","",
      "### 未编辑模型结果（百分制）",""]
    for ds,title in [("evqa-pilot500","E-VQA：同一完整评测集"),("mmke-visual","MMKE-Visual"),("mmke-entity","MMKE-Entity：对齐后的 954 条")]:
        lines += [f"#### {title}","","| 模型 | N | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 核验状态 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in rows:
            if r["dataset"]==ds:
                lines.append("| "+r["model"]+" | "+str(r["samples"])+" | "+
                  " | ".join(f"{r[m]:.3f}" for m in METRICS)+" | "+r["status"]+" |")
        lines.append("")
    lines += ["### 编辑前后差值与证据","",
      "差值为同一指标的“编辑后 − 未编辑”，单位是百分点；重点同时检查新目标得分提升和 locality 保持。Average 上升不能代替五项明细，也不能单独证明某个定位方法优于其他选层方法。",
      f"已生成 {len(gains)} 条与原台账同组合、同样本数的汇总差值：{link('editing_gain_vs_no_edit.csv')}。差值保留 baseline_status；待 GPU 核验的基线不能冒充已验收新实验。差值表不重新排名或选择层，跨层输入绑定仍以原台账的标准协议为前提。",
      "",
      f"基线表：{link('no_edit_baselines.csv')}；输入对齐证据：{link('alignment.json')}；最新状态：{link('latest_status.json')}；启动记录：{link('launch.json')}。",
      f"服务器结果目录：{REMOTE}。逐样本分数、GPU 抽检、来源 SHA-256 与接受记录保存在各组子目录；本地 groups 目录同步已验收证据。",
      "",END]
    content=DOC.read_text(encoding="utf-8")
    backup=LOCAL/"SWeeplayers.before_no_edit.md"
    if not backup.exists():backup.write_text(content,encoding="utf-8")
    block="\n".join(lines)+"\n"
    if BEGIN in content:
        assert END in content
        a=content.index(BEGIN);b=content.index(END)+len(END)
        new=content[:a]+block.rstrip("\n")+content[b:]
    else:new=content.rstrip()+"\n\n"+block
    if new!=content:write(DOC,new)
    receipt=dict(time=snapshot["time"],verified_groups=len(accepted),baseline_rows=len(rows),
                 delta_rows=len(gains),worker_state=worker.get("state"),document=str(DOC),
                 document_sha256=hashlib.sha256(DOC.read_bytes()).hexdigest())
    write(LOCAL/"backfill_receipt.json",json.dumps(receipt,indent=2,ensure_ascii=False))
    return receipt
def main(loop):
    while True:
        try:
            s=collect();receipt=render(s);print(json.dumps(receipt,ensure_ascii=False),flush=True)
            if len(s["accepted"])==21:return
            if s["worker"].get("state") in ["ERROR","NEEDS_REPAIR","STOPPED"]:
                raise RuntimeError("Worker needs attention: "+json.dumps(s["worker"]))
        except Exception:
            write(LOCAL/"sync_error.log",traceback.format_exc())
            if not loop:raise
            print(traceback.format_exc(),flush=True)
        if not loop:return
        time.sleep(45)
if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap=argparse.ArgumentParser();ap.add_argument("--loop",action="store_true")
    main(ap.parse_args().loop)
