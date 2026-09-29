"""Render auditable performance reports from the frozen comparison outputs."""
import collections
import csv
import json
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/all_methods_performance_20260928"
REPORT=ROOT/"md/Location/ALL_Methods_Recommendation_Performance.md"
DETAIL=ROOT/"md/Location/ALL_Methods_Performance_Per_Combination.md"
def read(name):return list(csv.DictReader((OUT/name).open(encoding="utf-8-sig")))
def jr(name):return json.loads((OUT/name).read_text(encoding="utf-8"))
def link(label,path):return f"[{label}](<{path.as_posix()}>)"
def f(x,d=3):return "—" if x is None or x=="" else f"{float(x):.{d}f}"
def sgn(x):return "—" if x is None or x=="" else f"{float(x):+.3f}"
def pct(x):return "—" if x is None or x=="" else f"{float(x)*100:.1f}%"
def table(headers,rr):return "| "+" | ".join(headers)+" |\n|"+"|".join("---" for _ in headers)+"|\n"+"\n".join("| "+" | ".join(str(x) for x in row)+" |" for row in rr)+"\n\n"
def write_csv(name,rr):
    if not rr:return
    fields=list(dict.fromkeys(k for r in rr for k in r))
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as out:
        w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(rr)
protocol=jr("protocol.json");verification=jr("verification.json")
catalog=read("method_catalog_and_coverage.csv")
variants=[r["variant"] for r in catalog]
ID={v:f"M{i+1:02d}" for i,v in enumerate(variants)}
registry=jr("recommendation_registry.json")
R={(r["dataset"],r["model"],r["variant"]):r for r in registry}
measurements=jr("method_performance_all.json")
M={(r["policy"],r["dataset"],r["model"],r["variant"],r["k"]):r for r in measurements}
summary=read("method_summary_by_scope.csv")
S={(r["policy"],r["k"],r["coverage_filter"],r["scope_type"],r["scope"],r["variant"]):r for r in summary}
pairs=read("all_pairwise_comparisons.csv")
P={(r["policy"],r["k"],r["coverage_filter"],r["scope_type"],r["scope"],r["a"],r["b"]):r for r in pairs}
cohorts=read("fixed_cohort_comparisons.csv")
datasets=["evqa-pilot500","mmke-visual","mmke-entity"]
models=["blip2-opt-2.7b","instructblip-vicuna-7b","minigpt-4-vicuna-7b","llava-v1.5-7b","qwen2.5-vl-3b","paligemma-3b","smolvlm-1.7b"]

def describe(v):
    method,flavor=v.rsplit("/",1)
    space="参数梯度" if method.startswith("LGA-Param") or method.startswith("SaLEM") else "视觉隐状态梯度" if method.startswith(("LGA-Visual","Ours")) else "模块输出贡献度" if method.startswith("VisEdit") else "视觉污染恢复" if method.startswith("CMA") else "视觉扰动 KL" if method.startswith("Perturb") else "层深先验"
    if method.startswith("LGA"):
        formula="E[g_old·g_new]"
        if method.endswith("no-old-strength"):formula="E[bᵢcᵢ]"
        elif method.endswith("no-new-strength"):formula="E[aᵢcᵢ]"
        elif method.endswith("no-direction"):formula="E[aᵢbᵢ]"
    elif method=="Ours-main":formula="abs(E[cᵢ]) × E[bᵢ]"
    elif method=="Ours-no-direction":formula="E[bᵢ]"
    elif method=="Ours-no-strength":formula="abs(E[cᵢ])"
    elif method.startswith("VisEdit-Pre"):formula="高贡献区起点前置层"
    elif method.startswith("VisEdit-Direct"):formula="贡献分数直接降序（诊断）"
    elif method.startswith("CMA"):formula="CR；版本的噪声/seed 协议不同"
    elif method.startswith("SaLEM"):formula="参数梯度绝对值聚合"
    elif method.startswith("Perturb"):formula="robust KL；alt 全序列"
    else:formula="距离 (L−1)/2 最近"
    return space,formula

def pair(a,b,policy="observed_main",k=3,cf="all",stype="all",scope="all"):
    rr=P.get((policy,str(k),cf,stype,scope,a,b));reverse=False
    if rr is None:rr=P.get((policy,str(k),cf,stype,scope,b,a));reverse=True
    if rr is None:return dict(a=a,b=b,n=0,delta_best=None,delta_mean=None,best_wins=0,best_ties=0,best_losses=0,mean_wins=0,mean_ties=0,mean_losses=0,same_candidate_set=0)
    r=dict(rr)
    if reverse:
        for field in ["delta_best","delta_mean","median_delta_best","median_delta_mean"]:r[field]=-float(r[field]) if r[field] else None
        for metric in ["best","mean"]:
            r[metric+"_wins"],r[metric+"_losses"]=r[metric+"_losses"],r[metric+"_wins"]
            r["a_"+metric],r["b_"+metric]=r["b_"+metric],r["a_"+metric]
    r["a"],r["b"]=a,b
    return r

focused=[]
def add_contrast(title,a,b):focused.append((title,a,b))
for prefix in ["LGA-Param","LGA-Visual","LGA-Visual-no-direction","Ours-main","Ours-no-direction","Ours-no-strength"]:
    add_contrast(prefix+"：Tukey−Raw",prefix+"/tukey",prefix+"/raw")
for flavor in ["raw","tukey"]:
    add_contrast("Ours 方向项增量（"+flavor+"）","Ours-main/"+flavor,"Ours-no-direction/"+flavor)
    add_contrast("Ours 强度项增量（"+flavor+"）","Ours-main/"+flavor,"Ours-no-strength/"+flavor)
    add_contrast("LGA 视觉−参数（"+flavor+"）","LGA-Visual/"+flavor,"LGA-Param/"+flavor)
    add_contrast("视觉 LGA 方向项增量（"+flavor+"）","LGA-Visual/"+flavor,"LGA-Visual-no-direction/"+flavor)
add_contrast("CMA model_pred−alt（含协议差异）","CMA-model_pred/raw","CMA-alt-v1.3/raw")
add_contrast("VisEdit Pre model_pred−alt","VisEdit-Pre-model_pred/current","VisEdit-Pre-alt/current")
add_contrast("VisEdit Pre pred-field−alt（历史诊断）","VisEdit-Pre-pred-field/historical","VisEdit-Pre-alt/current")
for target,flavor in [("alt","current"),("model_pred","current"),("pred-field","historical")]:
    add_contrast("VisEdit Pre−Direct / "+target,"VisEdit-Pre-"+target+"/"+flavor,"VisEdit-Direct-"+target+"/diagnostic")
add_contrast("当前 Ours−中层","Ours-main/raw","Middle-Prior/raw")
add_contrast("当前 Ours−参数 LGA Tukey","Ours-main/raw","LGA-Param/tukey")
add_contrast("纯新范数−中层","Ours-no-direction/raw","Middle-Prior/raw")
add_contrast("当前 Ours−CMA model_pred","Ours-main/raw","CMA-model_pred/raw")

report="# 所有定位方法的推荐性能比较（2026-09-28 现有结果快照）\n\n"
report+=f"输入为 {link('SWeeplayers.md',ROOT/'md/Location/SWeeplayers.md')} 与 {link('ALL_Methods_Recommends_layers.md',ROOT/'md/Location/ALL_Methods_Recommends_layers.md')} 所链接的机器可读原件。扫层快照：**{protocol['sweep_updated_at']}**；推荐快照：**{protocol['recommendations_updated_at']}**。本次未重新训练、未改变推荐公式、未依据编辑成绩重排候选。\n\n"
report+="## 1. 这次算到了什么\n\n"
report+="原推荐表的 **31 个方法/目标/公式/过滤版本全部登记**；另对 VisEdit 三种目标增加贡献度直接选层的诊断对照，共 34 个版本。原推荐记录 624 行中，400 行有可用推荐、224 行缺原始定位统计；新增 Direct 诊断后共 680 行。缺失不等于低分。\n\n"
report+="主比较用 **396 条 main**，36 条 stable 单独计算，1 条 BLIP2 L18 复测保留但不择优替换原 main。分别计算 Top-1、Best/Mean/Regret/Hit@3 与 @5；所有方法两两比较还按数据集和模型拆分。结果是回顾性分析，不是新独立确认实验。\n\n"
main_tukey=pair("Ours-main/raw","LGA-Param/tukey")
direction=pair("Ours-main/raw","Ours-no-direction/raw")
tukey=pair("LGA-Param/tukey","LGA-Param/raw")
report+=f"当前 Ours 与参数 LGA-Tukey 的共同 **{main_tukey['n']} 组**中，ΔBest@3={sgn(main_tukey['delta_best'])}、ΔMean@3={sgn(main_tukey['delta_mean'])}，Best@3 胜/平/负={main_tukey['best_wins']}/{main_tukey['best_ties']}/{main_tukey['best_losses']}。但是，相对纯新梯度范数，共同 **{direction['n']} 组**的 ΔBest@3={sgn(direction['delta_best'])}、ΔMean@3={sgn(direction['delta_mean'])}，说明不能仅凭胜过参数 LGA 宣称方向项已获得支持。\n\n"
report+=f"参数 LGA 的 Tukey−Raw 在共同 **{tukey['n']} 组**中，ΔBest@3={sgn(tukey['delta_best'])}、ΔMean@3={sgn(tukey['delta_mean'])}。是否过滤、在哪个梯度空间过滤，需要逐版比较；不能套用一条统一结论。\n\n"
report+="## 2. 指标与可比边界\n\n"
report+="- **Top-1**：原推荐顺序的第一层，不按编辑分数重选。**Best@K**：事后在 K 个候选中取得的最高 Average，表示候选集合的最好潜力；**Mean@K**：这 K 层的平均 Average。Best@K 不等于无需试验就能部署的单层成绩。\n- 必须有 K 个合法候选且 K 个评测全部存在，才计算 Best/Mean@K。部分结果仅报告已评测数和缺失层，不计算部分均值冒充完整结果。Top-5 按现有全部排名/Pre 规则延长，没有按编辑效果补层。\n- Regret@K=同组合、同分析口径的已测最好 Average−Best@K；Hit@K 为是否包含该已测最优表现。它们不是全网络 oracle 的 Regret/Hit；同分容差为 1e-9 个百分点。\n- 每个组合等权。各方法自己可用组合的均值仅作描述；方法优劣用相同组合的配对表或固定共同组表。coverage80 要求比较双方定位有效样本比例≥80%。\n- 同时给出已测候选池内均匀随机选择 K 层的精确期望。候选池由既有实验选择形成，这只是条件随机参照，不能当作全网络随机实验。\n- 参数与视觉 LGA 沿用不同有效样本集合；CMA 两个目标版本也改变了噪声/seed 协议；这些比较衡量完整流程，不能只归因于梯度空间或目标。视觉有限零分末层按输入规则保留，候选含零梯度层时单独标记。\n\n"
report+=table(["分析口径","层结果数","用途"],[
    ["observed_main",verification['policy_outcome_counts']['observed_main'],"所有已登记 main，包括有实测值的失败/未足训练预算；主描述"],
    ["main_without_flagged",verification['policy_outcome_counts']['main_without_flagged'],"排除恢复/诊断训练、数值异常/数值保护、不收敛标签；不证明所有层都收敛"],
    ["verified50_main",verification['policy_outcome_counts']['verified50_main'],"再要求本次明确核验了完整 50 轮历史"],
    ["stable_only",verification['policy_outcome_counts']['stable_only'],"只用 stable，不填补 main 缺项；保留自身异常标签"],
])
report+="恢复原训练继续运行、修复 checkpoint 选择、已有 checkpoint 评测，不单凭名称认定改变配方。历史验收记录在主分析保留，在 verified50 中自然排除；排除清单见 flagged_outcomes.csv。Average 沿用台账，部分历史记录因分项四舍五入有 ≤0.010 的差异，未擅自重写。\n\n"

report+="## 3. 全部对象、公式与覆盖\n\n记 aᵢ、bᵢ 分别为旧/新梯度范数，cᵢ 为余弦；E 为逐样本聚合。每行是独立比较版本，编号贯穿后续明细。\n\n"
catrows=[]
for r in catalog:
    v=r['variant'];space,formula=describe(v)
    catrows.append([ID[v],v,space,formula,r['n_formula_ready']+"/"+r['n_registered'],r['top1_complete'],r['top3_complete'],r['top5_complete']])
report+=table(["编号","方法版本","对象","公式/规则","推荐可用/登记组","Top1可评","Top3完整","Top5完整"],catrows)
report+="原 31 版本中有 10 个 LGA 严格消融版本（参数去旧/去新/去方向，视觉去旧/去新，各分 Raw/Tukey）尚缺逐样本交叉统计，共 210 行；VisEdit-model_pred 的 MMKE 还缺 14 行。它们已进入登记和缺项清单，不能用层均值相乘伪造 E[ab]、E[bc]、E[ac]。VisEdit Direct 是本次附加诊断，不替换原 Pre。\n\n"

report+="## 4. 固定共同组合上的七类当前版本\n\n"
for cf,title in [("all","全部定位覆盖"),("coverage80","各方法定位覆盖均≥80%")]:
    rr=[r for r in cohorts if r['cohort']=='core7_current' and r['policy']=='observed_main' and r['k']=='3' and r['coverage_filter']==cf and r['scope']=='all']
    n=rr[0]['n'];groups=json.loads(rr[0]['groups'])
    report+=f"### 4.{1 if cf=='all' else 2} {title}：相同 {n} 组\n\n"
    report+="共同组合："+"；".join(groups)+"。\n\n"
    tr=[]
    for r in sorted(rr,key=lambda r:float(r['best']) if r['best'] else -999,reverse=True):
        v=r['variant'];firsts=[M['observed_main',*g.split('/'),v,1]['best'] for g in groups]
        tr.append([ID[v],v,f(statistics.mean(firsts)) if firsts else '—',f(r['best']),f(r['mean']),f(r['regret']),pct(r['hit']),sgn(r['delta_best_random'])])
    report+=table(["编号","方法","同组Top1","Best@3","Mean@3","已测Regret@3","已测Hit@3","ΔBest−池内随机"],tr)
report+="这里的排序只针对上述七个明确版本及共同组合，不代表所有公式的总体排名。所有可产生 21 组推荐的版本一起取 Top-3 完整交集，只剩 "
rr=[r for r in cohorts if r['cohort']=='all_complete21_variants' and r['policy']=='observed_main' and r['k']=='3' and r['coverage_filter']=='all' and r['scope']=='all']
report+=f"**{rr[0]['n']} 组**；若要求全部 34 个版本完成，则没有共同完整组。因此必须看下面的配对和分组结果。\n\n"

report+="## 5. 所有版本的可用范围描述（不可直接跨行排总名次）\n\n每列均值只使用该方法自己的完整组合，分母不同。先看覆盖，再看第 6 节共同组差值。\n\n"
tr=[]
for v in variants:
    ss=[S['observed_main',str(k),'all','all','all',v] for k in [1,3,5]]
    tr.append([ID[v],v,ss[0]['n_complete'],f(ss[0]['best']),ss[1]['n_complete'],f(ss[1]['best']),f(ss[1]['mean']),ss[2]['n_complete'],f(ss[2]['best']),f(ss[2]['mean'])])
report+=table(["编号","方法","N1","Top1","N3","Best@3","Mean@3","N5","Best@5","Mean@5"],tr)

report+="## 6. 目标、梯度对象、公式及过滤的配对比较\n\n差值均为 **A−B**；正值表示 A 较高。胜/平/负按 Best@3，集合相同数为双方三个候选忽略顺序后相同。每行都有自己的共同组合，不把不同行的差值当作同一批实验。\n\n"
tr=[];focused_rows=[]
for title,a,b in focused:
    r=pair(a,b)
    tr.append([title,ID[a]+"−"+ID[b],r['n'],sgn(r['delta_best']),sgn(r['delta_mean']),f"{r['best_wins']}/{r['best_ties']}/{r['best_losses']}",r['same_candidate_set']])
    focused_rows.append(dict(contrast=title,**r))
report+=table(["比较","A−B","共同N","ΔBest@3","ΔMean@3","Best胜/平/负","集合相同"],tr)
write_csv("focused_contrasts.csv",focused_rows)
report+="### 6.1 按任务拆分关键比较\n\n"
selected=[x for x in focused if x[0] in ["Ours 方向项增量（raw）","LGA-Param：Tukey−Raw","LGA 视觉−参数（raw）","当前 Ours−参数 LGA Tukey","CMA model_pred−alt（含协议差异）","VisEdit Pre model_pred−alt"]]
tr=[]
for title,a,b in selected:
    for d in datasets:
        r=pair(a,b,stype="dataset",scope=d)
        tr.append([title,d,r['n'],sgn(r['delta_best']),sgn(r['delta_mean']),f"{r['best_wins']}/{r['best_ties']}/{r['best_losses']}"])
report+=table(["比较","数据集","共同N","ΔBest@3","ΔMean@3","Best胜/平/负"],tr)
report+="### 6.2 按模型拆分方向项与过滤\n\n"
tr=[]
for title,a,b in selected[:2]:
    for model in models:
        r=pair(a,b,stype="model",scope=model)
        tr.append([title,model,r['n'],sgn(r['delta_best']),sgn(r['delta_mean']),f"{r['best_wins']}/{r['best_ties']}/{r['best_losses']}"])
report+=table(["比较","模型","共同N","ΔBest@3","ΔMean@3","Best胜/平/负"],tr)

report+="## 7. 训练状态、定位覆盖与 stable 敏感性\n\n以下不挑选最有利的过滤结果；切换口径后共同组合会变化，因而变化不能只归因于排除异常。两种梯度空间的样本定义差异也不会被 coverage80 自动消除。\n\n"
tr=[]
for title,a,b in [x for x in focused if x[0] in ["Ours 方向项增量（raw）","LGA-Param：Tukey−Raw","当前 Ours−参数 LGA Tukey"]]:
    for policy in ['observed_main','main_without_flagged','verified50_main','stable_only']:
        for cf in ['all','coverage80']:
            r=pair(a,b,policy=policy,cf=cf)
            tr.append([title,policy,cf,r['n'],sgn(r['delta_best']),sgn(r['delta_mean'])])
report+=table(["比较","训练/证据口径","定位覆盖限制","共同N","ΔBest@3","ΔMean@3"],tr)
report+="stable 的逐组合成绩与 main 单列保存在 method_performance_all.csv；本报告没有让别的模型使用 main、PaliGemma 自动改用 stable 后再混成一个主均值。\n\n"

report+="## 8. 分数与实际成绩的关联\n\n对同一组合已测且在当前排序中保留的层计算 Spearman，至少五层、分数和指标非恒定才给值。这里不保证覆盖全部网络层。Raw/Tukey 的参与层集合可能不同；Pre 是区间到候选层的转换，未把同层贡献分数冒充 Pre 自身分数；贡献度关联看 VisEdit Direct 诊断。下表为覆盖≥80%的模型相关系数等权均值，不是将所有层拼接回归，也不是显著性证明。\n\n"
corr=read("layer_score_correlations.csv")
cor_summary=[]
for v in variants:
    for d in datasets:
        rr=[r for r in corr if r['policy']=='observed_main' and r['variant']==v and r['dataset']==d and r['rho'] and r['coverage'] and float(r['coverage'])>=.8]
        vals=[]
        for met in ['Average','Rel','M-Gen','M-Loc']:
            sub=[float(r['rho']) for r in rr if r['metric']==met]
            vals.extend([len(sub),statistics.mean(sub) if sub else None])
        cor_summary.append(dict(variant=v,dataset=d,**dict(zip(['n_Average','rho_Average','n_Rel','rho_Rel','n_M-Gen','rho_M-Gen','n_M-Loc','rho_M-Loc'],vals))))
write_csv("correlation_summary_by_dataset.csv",cor_summary)
report+=table(["方法","任务","N模型","ρ Average","ρ Rel","ρ M-Gen","ρ M-Loc"],[[ID[r['variant']]+" "+r['variant'],r['dataset'],r['n_Average'],f(r['rho_Average']),f(r['rho_Rel']),f(r['rho_M-Gen']),f(r['rho_M-Loc'])] for r in cor_summary if r['variant'] in ['Ours-main/raw','Ours-no-direction/raw','LGA-Param/raw','LGA-Param/tukey','LGA-Visual/raw','VisEdit-Direct-alt/diagnostic']])

report+="## 9. 全量明细、缺项与复算\n\n"
report+=f"逐个模型×数据集查看全部 34 个版本的实际推荐层、Top1、Best/Mean@3、缺失层与 Top5 结果：{link('21 组完整明细',DETAIL)}。\n\n"
for label,name in [
    ("全部方法、配方口径与 K 的逐组性能","method_performance_all.csv"),
    ("所有方法两两配对（含分数据集、分模型）","all_pairwise_comparisons.csv"),
    ("固定共同组比较","fixed_cohort_comparisons.csv"),
    ("各方法分任务/模型汇总","method_summary_by_scope.csv"),
    ("定位未完成与评测缺失","missing_candidates_or_evaluations.csv"),
    ("缺失层涉及哪些方法","missing_layer_coverage.csv"),
    ("所有逐层分数相关性","layer_score_correlations.csv"),
    ("已测池最优与条件随机参照","observed_pool_and_random_reference.csv"),
    ("统计口径与输入哈希","protocol.json"),
    ("计算检查","verification.json"),
]:report+="- "+link(label,OUT/name)+"\n"
report+=f"\n复算脚本：{link('compare_all_method_recommendations_20260928.py',ROOT/'scripts/compare_all_method_recommendations_20260928.py')}；报告脚本：{link('report_all_method_performance_20260928.py',Path(__file__))}。脚本默认复用本目录冻结输入，确保这版结果可重现；新数据应另建快照，不能与这版共同组数混用。\n"

detail="# 所有方法推荐性能：21 组完整明细\n\n"
detail+=f"定义、方法编号与总体比较见 {link('分析报告',REPORT)}。本表使用 observed_main（396 条 main，包括有评测的异常/未足训练预算）；stable 等其余口径见 CSV。分数为 Average，未采用任何 stable 填补。\n\n"
detail+="`待定位`：公式/目标分数尚未完成；`缺 L…`：已有推荐但缺 main 评测；`候选不足`：Pre 或过滤后不足 K 层；`未登记`：该版本不在输入表的此组合范围。`†` 表示候选中含零视觉梯度层；`!` 表示候选中含已标记异常/未完成训练预算的 main 实测。不是按符号自动删层。\n\n"
detail+=table(["编号","方法版本"],[[ID[v],v] for v in variants])
group_winners=[]
def show_status(r):
    if r is None:return '未登记'
    if r['status']=='pending_formula':return '待定位'
    if r['status']=='insufficient_candidates':return '候选不足'
    if r['status']=='missing_evaluations':return f"{r['evaluated_count']}/{r['k']}；缺 {r['missing_layers']}"
    flags=[]
    if r['candidate_zero_gradient_layers']:flags.append('† '+r['candidate_zero_gradient_layers'])
    if r['candidate_flagged_layers']:flags.append('! '+r['candidate_flagged_layers'])
    return '完整'+('；'+'；'.join(flags) if flags else '')
for di,d in enumerate(datasets,1):
    detail+=f"## {di}. {d}\n\n"
    for mi,model in enumerate(models,1):
        detail+=f"### {di}.{mi} {model}\n\n"
        candidates=[M['observed_main',d,model,v,3] for v in variants if ('observed_main',d,model,v,3) in M]
        complete=[r for r in candidates if r['status']=='complete']
        if complete:
            best=max(r['best'] for r in complete);mean=max(r['mean'] for r in complete)
            bv=[ID[r['variant']] for r in complete if abs(r['best']-best)<1e-9];mv=[ID[r['variant']] for r in complete if abs(r['mean']-mean)<1e-9]
            detail+=f"在本组已有完整 Top-3 评测的版本中，Best@3 最高={f(best)}（{', '.join(bv)}）；Mean@3 最高={f(mean)}（{', '.join(mv)}）。这是已可比方法内的事后描述，未完成版本不能被判为更差。\n\n"
            group_winners.append(dict(dataset=d,model=model,complete_variant_count=len(complete),best3=best,best3_variants=bv,mean3=mean,mean3_variants=mv))
        tr=[]
        for v in variants:
            one=M.get(('observed_main',d,model,v,1));three=M.get(('observed_main',d,model,v,3));five=M.get(('observed_main',d,model,v,5))
            if three is None:tr.append([ID[v],'—','未登记','—','—','—','—','—']);continue
            tr.append([ID[v],three['candidates'] or '—',show_status(three),f(one['best']),f(three['best']),f(three['mean']),f(three['regret']),('L'+str(three['best_layer'])) if three['best_layer'] is not None else '—'])
        detail+=table(['方法','推荐 Top-3（原顺序）','Top3覆盖/标记','Top1','Best@3','Mean@3','已测Regret@3','Best所在层'],tr)
        detail+="Top-5 扩展（按原评分/Pre 规则）：\n\n"
        tr=[]
        for v in variants:
            r=M.get(('observed_main',d,model,v,5))
            if r and r['status']!='pending_formula':tr.append([ID[v],r['candidates'],show_status(r),f(r['best']),f(r['mean'])])
        detail+=table(['方法','Top-5','覆盖','Best@5','Mean@5'],tr)
write_csv('per_group_best_observed_methods.csv',group_winners)
REPORT.write_text(report,encoding='utf-8')
DETAIL.write_text(detail,encoding='utf-8')

# Append a short navigable pointer; leave all recommendation and result tables intact.
marker='<!-- ALL_METHODS_PERFORMANCE_20260928 -->'
for p in [ROOT/'md/Location/ALL_Methods_Recommends_layers.md',ROOT/'md/Location/SWeeplayers.md']:
    content=p.read_text(encoding='utf-8-sig')
    if marker not in content:
        backup=OUT/'manual_backups'/p.name;backup.parent.mkdir(exist_ok=True)
        if not backup.exists():backup.write_bytes(p.read_bytes())
        content=content.rstrip()+f"\n\n{marker}\n## 推荐性能比较（2026-09-28 快照）\n\n基于本文件对应的冻结数据，已计算所有已登记对象、目标、公式与 Raw/Tukey 版本的 Top-1、Top-3、Top-5 推荐性能，并区分 main/stable、公式缺项和评测缺项。见 {link('全部方法性能报告',REPORT)} 与 {link('21组逐方法明细',DETAIL)}；原定位推荐和扫层结果不变。\n"
        p.write_text(content,encoding='utf-8')
print(json.dumps({'report':str(REPORT),'detail':str(DETAIL),'report_lines':len(report.splitlines()),'detail_lines':len(detail.splitlines()),'variants':len(variants),'group_count':len(group_winners)},ensure_ascii=False,indent=2))
