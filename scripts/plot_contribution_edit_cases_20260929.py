"""Publication-ready contribution/editing case figures from frozen local evidence."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
try:
    import matplotlib
except ImportError:
    sys.path.insert(0, "C:/Users/zhoun/AppData/Local/Temp/codex-vtrack-mpl-20260929")
    import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"outputs/visedit_contribution_cases_20260929"
FIGS = ROOT/"md/Location/related_work.md/figures/contribution_edit_cases_20260929"
REPORT = ROOT/"md/Location/related_work.md/贡献度归因与编辑效果不一致_案例分析_20260929.md"
load = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
A = load(DATA/"analysis.json")
LP = ROOT/"outputs/sweep_ledger_20260928_110311/ledger.json"
assert sha(LP) == A["inputs"]["ledger_sha256"]
ledger = load(LP)
pool = {(r["dataset"],r["model"],r["layer"]):r for r in ledger["rows"] if r["recipe"]=="main" and "paligemma" not in r["model"]}
lookup = {(r["dataset"],r["model"],r["target"],r["module"]):r for r in A["rows"]}
with (DATA/"layer_alignment.csv").open(encoding="utf-8-sig",newline="") as f:
    aligned = {(r["dataset"],r["model"],r["target"],r["module"],int(r["layer"])):r for r in csv.DictReader(f)}

for fn in ["msyh.ttc", "msyhbd.ttc"]:
    font_manager.fontManager.addfont("C:/Windows/Fonts/"+fn)
font_name=font_manager.FontProperties(fname="C:/Windows/Fonts/msyh.ttc").get_name()
plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":[font_name,"DejaVu Sans"],
                    "font.size":10,"axes.unicode_minus":False,"pdf.fonttype":3 if "--pre-only" in sys.argv else 42,
                    "svg.fonttype":"none","axes.spines.top":False,"axes.spines.right":False,
                    "axes.edgecolor":"#77828c","axes.labelcolor":"#27343e",
                    "text.color":"#24313a","xtick.color":"#50606b","ytick.color":"#50606b",
                    "axes.titlesize":11,"figure.facecolor":"white","savefig.facecolor":"white"})
BLUE, ORANGE, GRAY = "#2468A2", "#CE5B28", "#C6D1D8"
METRICS=["Rel","T-Gen","M-Gen","Average"]
COLORS=["#167D8D","#7954A6","#B7821D","#24313A"]
MARKERS=["o","s","^","D"]
TARGET={"alt":"alt","model_pred":"首预测位置"}
MINI,LLAVA,BLIP,SMOL,INST="minigpt-4-vicuna-7b","llava-v1.5-7b","blip2-opt-2.7b","smolvlm-1.7b","instructblip-vicuna-7b"

# Explicit cases selected in the accompanying report, not a method leaderboard.
CASES=[
 dict(id="fig01_minigpt4_evqa_alt",number=1,title="MiniGPT4 × E-VQA",ds="evqa-pilot500",model=MINI,ref=15,
      panels=[("alt","attn",31),("alt","mlp",30),("alt","attn+mlp",28)],heading="## 2. 主案例：",
      note="L31 的 EMA loss=10.223，存在高损失；L30/L28 分别为 0.481/0.349。三种峰值都弱于 L15，但不能据此认定所有归因方法无效。"),
 dict(id="fig03_minigpt4_evqa_nexttoken",number=3,title="MiniGPT4 × E-VQA · 首预测位置对照",ds="evqa-pilot500",model=MINI,ref=15,
      panels=[("model_pred","attn",26),("model_pred","mlp",30),("model_pred","attn+mlp",26)],heading="## 4. 补充反例：",
      note="首预测位置是原始图文输入末位的 next-token argmax，不是完整旧答案归因。L26/L30 的 EMA loss 为 0.374/0.481。"),
 dict(id="fig04_llava_evqa_alt",number=4,title="LLaVA × E-VQA",ds="evqa-pilot500",model=LLAVA,ref=15,
      panels=[("alt","mlp",30),("alt","attn+mlp",30)],heading="## 5. 跨模型补充与边界：",
      note="MLP 与联合贡献的全局峰值同为 L30，复用同一编辑结果。它们的峰值反例不等于实际 Pre 在所有指标上都失败。"),
 dict(id="fig05_minigpt4_mmke_visual",number=5,title="MiniGPT4 × MMKE-visual",ds="mmke-visual",model=MINI,ref=15,
      panels=[("alt","attn",31),("alt","mlp",28),("alt","attn+mlp",28),("model_pred","attn",26)],heading="### 6.1 ",
      note="alt 为视觉语义 KeyToken。L31 高损失（EMA=7.305）；首预测位置 attn 的 L26 也构成反例，EMA=0.789。L28 T-Gen 沿用台账 57.92。"),
 dict(id="fig06_llava_mmke_visual",number=6,title="LLaVA × MMKE-visual",ds="mmke-visual",model=LLAVA,ref=15,
      panels=[("model_pred","attn",28),("alt","mlp",28),("alt","attn+mlp",28)],heading="### 6.2 ",
      note="L28 分别是贡献第 2/4/5 名，均不是全局最高层。图示证明高贡献排序存在反例；三面板复用同一对层评测。"),
 dict(id="fig07_llava_mmke_entity",number=7,title="LLaVA × MMKE-entity",ds="mmke-entity",model=LLAVA,ref=15,
      panels=[("model_pred","attn",24),("alt","mlp",27),("alt","attn+mlp",27)],heading="### 6.3 ",
      note="alt 为实体 KeyToken。只有首预测位置 attn 的 L24 是全局峰值；Average 差距仅 0.344–0.590 个百分点，未作显著性断言。"),
 dict(id="fig08_instructblip_mmke_entity",number=8,title="InstructBLIP × MMKE-entity",ds="mmke-entity",model=INST,ref=15,
      panels=[("alt","attn",30),("alt","mlp",30),("alt","attn+mlp",30)],heading="### 6.4 ",
      note="两层均有高损失：L30 EMA=14.489，L15 EMA=11.116。此例是既定配方下的补充现象，不能作为排除优化困难后的机制证据。"),
 dict(id="fig09_blip2_evqa_nexttoken",number=9,title="BLIP2 × E-VQA · 首预测位置对照",ds="evqa-pilot500",model=BLIP,ref=15,
      panels=[("model_pred","attn",29),("model_pred","mlp",25),("model_pred","attn+mlp",26)],heading="### 6.5 ",
      note="L29/L25/L26 的 EMA loss=0.414/0.232/0.364，L15=0.337；图中均为首预测位置贡献。直接选峰的差距不能冒充 Pre 的差距。"),
 dict(id="fig10_smolvlm_evqa_alt",number=10,title="SmolVLM × E-VQA",ds="evqa-pilot500",model=SMOL,ref=12,
      panels=[("alt","attn",22),("alt","mlp",19),("alt","attn+mlp",22)],heading="### 6.6 ",
      note="L12 是固定中层集合 [11,12,10] 的第二候选，不是 Middle Top-1。L22/L19/L12 的 EMA loss=0.488/0.381/0.402。"),
]
FIGS.mkdir(parents=True,exist_ok=True)
pre_only = "--pre-only" in sys.argv
manifest=([r for r in load(FIGS/"figure_manifest.json")["figures"] if r["number"]!=2] if pre_only else [])
plot_rows=[]
captions={}


def decorate(ax,axis="y"):
    ax.grid(axis=axis,color="#e3e8ec",linewidth=.65,zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=9,length=3)


def save(fig, name):
    paths={}
    for ext in ["png","pdf","svg"]:
        p=FIGS/(name+"."+ext)
        fig.savefig(p,dpi=300)
        paths[ext]=p
    p=FIGS/(name+"_preview.png")
    fig.savefig(p,dpi=125)
    paths["preview"]=p
    plt.close(fig)
    return paths


def export_block(name, number, caption, paths):
    return (f"<!-- CASE_FIGURE_{name}_BEGIN -->\n\n"
            f"![图 {number}：{caption.split('。')[0]}](<{paths['png'].as_posix()}>)\n\n"
            f"**图 {number}｜{caption}**\n\n"
            f"[高清 PNG](<{paths['png'].as_posix()}>) · [矢量 PDF](<{paths['pdf'].as_posix()}>) · [可编辑 SVG](<{paths['svg'].as_posix()}>)\n\n"
            f"<!-- CASE_FIGURE_{name}_END -->\n\n")


for case in ([] if pre_only else CASES):
    ds,model,ref=case["ds"],case["model"],case["ref"]
    panels=case["panels"];n=len(panels)
    ar=[lookup[ds,model,t,m] for t,m,_ in panels]
    depth=ar[0]["depth"];layers=np.arange(depth)
    lows=pool[ds,model,ref]["metrics"]
    observed=[l for l in layers if (ds,model,int(l)) in pool]
    highs=sorted({h for _,_,h in panels})
    for l in highs+[ref]:
        r=pool[ds,model,l]
        v=r["verification"]
        assert r["training"]=="50轮已核验" and v["all_50_epochs_present"] and v["evaluation_verified"]
    deltas=[np.array([lows[m]-pool[ds,model,h]["metrics"][m] for m in METRICS]) for _,_,h in panels]
    assert all((d>0).all() for d in deltas)
    delta_max=max(d.max() for d in deltas)*1.30
    figsize=(16.0 if n==4 else 15.0,11.7)
    fig=plt.figure(figsize=figsize)
    gs=fig.add_gridspec(3,n,left=.060,right=.974,bottom=.130,top=.860,height_ratios=[1.03,.98,.80],hspace=.64,wspace=.30)
    fig.suptitle(f"图 {case['number']}  {case['title']}：高贡献与编辑收益不一致",fontsize=17,fontweight="bold",y=.978)
    fig.text(.5,.943,f"main 配方  |  归因样本 N={ar[0]['samples']}  |  编辑评测 N={pool[ds,model,ref]['samples']}  |  层号从 0 开始",ha="center",fontsize=10)
    fig.legend(handles=[Patch(color=ORANGE,label="案例中的高贡献层"),Patch(color=BLUE,label=f"低贡献参照 L{ref}"),Patch(color=GRAY,label="其他层贡献")],
               loc="upper center",bbox_to_anchor=(.5,.925),ncol=3,frameon=False,fontsize=10)
    comparisons=[]
    for j,(target,module,high) in enumerate(panels):
        vals=np.array([float(aligned[ds,model,target,module,int(l)]["positive_contribution"]) for l in layers])
        highrank=int(aligned[ds,model,target,module,high]["contribution_rank"])
        lowrank=int(aligned[ds,model,target,module,ref]["contribution_rank"])
        assert vals[high]>vals[ref] and highrank<=5
        source=lookup[ds,model,target,module]["source"]
        assert sha(ROOT/source)==next(s["sha256"] for s in A["sources"] if s["source"]==source)
        ax=fig.add_subplot(gs[0,j]);decorate(ax)
        colors=[ORANGE if l==high else BLUE if l==ref else GRAY for l in layers]
        ax.bar(layers,vals,color=colors,width=.82,zorder=3)
        ax.set_xlim(-.9,depth-.1);ax.set_ylim(0,vals.max()*1.31)
        ticks=sorted(set(range(0,depth,4))|{depth-1})
        ax.set_xticks(ticks);ax.set_xlabel("层号")
        ax.set_title(f"A{j+1}  {module} | {TARGET[target]}\nL{high} 第{highrank}名；L{ref} 第{lowrank}名",loc="left",fontsize=10.5,pad=9,y=1.04)
        if j==0:ax.set_ylabel("正向贡献度（原始分数）")
        ax.yaxis.set_major_locator(ticker.MaxNLocator(4))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda value, pos: f"{value:.3g}"))
        for l,col in [(ref,BLUE),(high,ORANGE)]:
            ax.annotate(f"L{l}\n{vals[l]:.3g}",(l,vals[l]),xytext=(0,4),textcoords="offset points",ha="center",va="bottom",fontsize=9,color=col)
        for l in layers:
            r=pool.get((ds,model,int(l)))
            plot_rows.append(dict(figure=case["id"],dataset=ds,model=model,target=target,module=module,layer=int(l),
                                  contribution=vals[l],global_rank=int(aligned[ds,model,target,module,int(l)]["contribution_rank"]),
                                  role="higher_contribution_case" if l==high else "lower_contribution_reference" if l==ref else "other",
                                  evaluated=r is not None,**(r["metrics"] if r else {})))
        da=fig.add_subplot(gs[2,j]);decorate(da,"x")
        y=np.arange(4);da.barh(y,deltas[j],color=[BLUE]*3+["#174B75"],height=.55,zorder=3)
        da.set_yticks(y,METRICS);da.invert_yaxis();da.set_xlim(0,delta_max)
        da.xaxis.set_major_locator(ticker.MaxNLocator(4));da.set_xlabel("参照层优势（百分点）")
        da.set_title(f"C{j+1}  L{ref} − L{high}（{module}）",loc="left",fontsize=10.5,pad=9)
        for yy,d in zip(y,deltas[j]):da.text(d+delta_max*.025,yy,f"+{d:.2f}",va="center",fontsize=10,color=BLUE)
        comparisons.append(dict(target=target,module=module,high_layer=high,high_rank=highrank,ref_layer=ref,ref_rank=lowrank,
                                high_contribution=float(vals[high]),ref_contribution=float(vals[ref]),
                                deltas=dict(zip(METRICS,map(float,deltas[j])))))
    ax=fig.add_subplot(gs[1,:]);decorate(ax)
    for high in highs:ax.axvspan(high-.40,high+.40,color=ORANGE,alpha=.095,zorder=0)
    ax.axvspan(ref-.40,ref+.40,color=BLUE,alpha=.13,zorder=0)
    for m,col,mark in zip(METRICS,COLORS,MARKERS):
        vals=np.array([pool[ds,model,int(l)]["metrics"][m] if (ds,model,int(l)) in pool else np.nan for l in layers])
        ax.plot(layers,vals,marker=mark,markersize=4.5,color=col,linewidth=1.1,label=m,zorder=3)
    for high in highs:ax.axvline(high,color=ORANGE,alpha=.55,linewidth=.8,linestyle="--")
    ax.axvline(ref,color=BLUE,alpha=.7,linewidth=.9,linestyle="--")
    ax.set_xlim(-.9,depth-.1);ax.set_xticks(ticks);ax.set_xlabel("与上排相同的层号；空缺位置表示没有真实评测，不插值、不记零")
    ax.set_ylabel("编辑后评测得分（%）")
    ax.set_title(f"B  已测层的真实编辑效果（{len(observed)}/{depth} 层）；背景色标出上排所选层",loc="left",fontsize=11,pad=12)
    ax.legend(ncol=4,loc="upper right",bbox_to_anchor=(1.005,1.25),frameon=False,fontsize=9)
    yy=[pool[ds,model,int(l)]["metrics"][m] for l in observed for m in METRICS]
    spread=max(yy)-min(yy);ax.set_ylim(max(0,min(yy)-max(2,spread*.12)),min(100,max(yy)+max(2,spread*.15)))
    fig.text(.06,.083,"读图：A 排贡献越高，柱越高；B 排为实际得分；C 排为低贡献参照层减去高贡献层，正值表示低贡献层编辑更好。",fontsize=9.4)
    fig.text(.06,.059,case["note"],fontsize=9.1,color="#76543e")
    fig.text(.06,.035,"仅展示已有实测反例，非总体胜率或显著性检验；T-Loc/M-Loc 详见正文。冻结台账：2026-09-28；PaliGemma 已排除。",fontsize=9,color="#657680")
    paths=save(fig,case["id"])
    caption=case["title"]+" 的贡献度—编辑效果对照。上排保留全部层的原始贡献分数，中排只显示真实已测层，底排分别比较 Rel、T-Gen、M-Gen 和 Average。"+case["note"]
    captions[case["id"]]=(case["heading"],export_block(case["id"],case["number"],caption,paths))
    manifest.append(dict(**case,comparisons=comparisons,outputs={k:p.relative_to(ROOT).as_posix() for k,p in paths.items()},
                         sha256={k:sha(p) for k,p in paths.items()}))
    print("Rendered "+case["id"],flush=True)

# Figure 2: actual Pre vs fixed Middle, including the LLaVA-EVQA mixed result.
pre_spec=[("MiniGPT4 · E-VQA", "evqa-pilot500",MINI,"alt","attn+mlp"),
          ("LLaVA · E-VQA", "evqa-pilot500",LLAVA,"alt","attn+mlp"),
          ("MiniGPT4 · MMKE-visual", "mmke-visual",MINI,"alt","attn+mlp"),
          ("LLaVA · MMKE-visual", "mmke-visual",LLAVA,"alt","attn+mlp"),
          ("LLaVA · MMKE-entity", "mmke-entity",LLAVA,"alt","attn+mlp"),
          ("InstructBLIP · MMKE-entity", "mmke-entity",INST,"alt","attn+mlp"),
          ("BLIP2 · E-VQA *", "evqa-pilot500",BLIP,"model_pred","attn+mlp"),
          ("SmolVLM · E-VQA *", "evqa-pilot500",SMOL,"alt","attn+mlp")]
fig,axs=plt.subplots(1,3,figsize=(15.5,7.8),sharey=True)
fig.subplots_adjust(left=.235,right=.963,top=.79,bottom=.23,wspace=.16)
fig.suptitle("图 2  实际 Pre 候选与固定中层：相同三层预算",fontsize=17,fontweight="bold",y=.957)
fig.text(.5,.91,"差值 = Middle − Pre（Average，百分点）；正值表示固定中层更好，负值表示 Pre 更好",ha="center",fontsize=10)
pre_records=[]
for j,(measure,title) in enumerate(zip(["top1","best3","mean3"],["Top-1","Best@3","Mean@3"])):
    ax=axs[j];decorate(ax,"x")
    vals=[]
    for label,ds,model,target,module in pre_spec:
        r=lookup[ds,model,target,module];assert r["pre_complete"] and r["middle_complete"]
        p=r["pre_performance"]["Average"][measure];m=r["middle_performance"]["Average"][measure]
        vals.append(m-p)
        pre_records.append(dict(label=label,dataset=ds,model=model,target=target,module=module,measure=measure,pre=p,middle=m,delta=m-p,
                                pre_layers=r["pre_layers"],middle_layers=r["middle_layers"]))
    ax.barh(range(len(vals)),vals,color=[BLUE if d>=0 else ORANGE for d in vals],height=.50,zorder=3)
    ax.axvline(0,color="#536570",linewidth=1)
    ax.set_yticks(range(len(vals)),[s[0] for s in pre_spec],fontsize=10)
    ax.set_title(title,fontsize=13,pad=15);ax.set_xlim(-2.15,13.0)
    ax.set_xticks([-2,0,3,6,9,12]);ax.set_xlabel("Middle − Pre（百分点）")
    for y,d in enumerate(vals):ax.text(d+(.16 if d>=0 else -.16),y,f"{d:+.3f}",ha="left" if d>=0 else "right",va="center",fontsize=10,color=BLUE if d>=0 else ORANGE)
axs[0].invert_yaxis()
fig.text(.08,.147,"LLaVA × E-VQA：Pre 的 Top-1 与 Mean@3 略好，Best@3 较低，不能据此声称所有 Pre 规则都失败。",fontsize=10)
fig.text(.08,.11,"本图选取各组合的联合贡献规则；BLIP2 为首预测位置目标，其余为 alt。相同候选集合不按模块重复计数。",fontsize=9.5)
fig.text(.08,.073,"* BLIP2 的中层 L14、SmolVLM 的中层 L10/L11 为历史验收；有完整评测，但训练历史证据等级低于逐轮复核层。",fontsize=9.2,color="#76543e")
fig.text(.08,.040,"仅比较三候选均有真实评测的集合；无误差条，未进行多种子显著性检验。所有数值与正文台账一致。",fontsize=9,color="#657680")
paths=save(fig,"fig02_pre_vs_middle")
caption="实际联合贡献 Pre 与 Middle 的三候选比较。正差值表示 Middle 更好，负差值表示 Pre 更好；保留 LLaVA × E-VQA 的反向结果。目标与历史验收层的标注见图，不将贡献峰值的差距冒充 Pre 的差距。"
captions["fig02_pre_vs_middle"]=("## 3. 实际 Pre 规则",export_block("fig02_pre_vs_middle",2,caption,paths))
manifest.append(dict(id="fig02_pre_vs_middle",number=2,comparisons=pre_records,
                     outputs={k:p.relative_to(ROOT).as_posix() for k,p in paths.items()},sha256={k:sha(p) for k,p in paths.items()}))

# Preserve prose and tables; add idempotent blocks at the start of each case.
before=REPORT.read_bytes();text=before.decode("utf-8-sig").replace("\r\n","\n")
backup=DATA/"related_work_report_before_figures.md"
if not backup.exists():backup.write_bytes(before)
for name,(heading,block) in captions.items():
    pattern=rf"<!-- CASE_FIGURE_{re.escape(name)}_BEGIN -->.*?<!-- CASE_FIGURE_{re.escape(name)}_END -->\n*"
    text=re.sub(pattern,"",text,flags=re.S)
    found=[m for m in re.finditer(r"(?m)^"+re.escape(heading)+r"[^\n]*\n",text)]
    assert len(found)==1,(name,heading)
    pos=found[0].end()
    text=text[:pos]+"\n"+block+text[pos:].lstrip("\n")
read_note=("<!-- CASE_FIGURES_GUIDE_BEGIN -->\n\n"
           "**配图说明：本文件已为原有与新增案例嵌入 9 张贡献度—编辑效果对照图，并加入 1 张 Pre 候选比较图。** "
           "每张案例图用同一层坐标展示贡献分数和真实编辑指标，底排给出成对差值；缺失评测不插值、不记零。"
           "橙色为所选高贡献层，蓝色为低贡献参照层。图中指标差距不代表统计显著性，M-Loc/T-Loc 的取舍仍以正文完整表为准。"
           "每图提供 300 dpi PNG、矢量 PDF 与 SVG。\n\n"
           "<!-- CASE_FIGURES_GUIDE_END -->\n\n")
text=re.sub(r"<!-- CASE_FIGURES_GUIDE_BEGIN -->.*?<!-- CASE_FIGURES_GUIDE_END -->\n*","",text,flags=re.S)
pos=text.index("\n\n")+2;text=text[:pos]+read_note+text[pos:]
assert REPORT.read_bytes()==before,"Document changed during rendering; preserve concurrent edits."
REPORT.write_text(text,encoding="utf-8",newline="\n")
if not pre_only:
    with (FIGS/"figure_data.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=list(dict.fromkeys(k for r in plot_rows for k in r))
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(plot_rows)
result=dict(report=REPORT.relative_to(ROOT).as_posix(),report_sha256=sha(REPORT),
            inputs={"ledger_sha256":sha(LP),"analysis_sha256":sha(DATA/"analysis.json"),"alignment_sha256":sha(DATA/"layer_alignment.csv")},
            count=len(manifest),matplotlib_version=matplotlib.__version__,font=font_name,figures=sorted(manifest,key=lambda r:r["number"]))
(FIGS/"figure_manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"figure_count":len(manifest),"report":str(REPORT),"figure_directory":str(FIGS)},ensure_ascii=False),flush=True)
