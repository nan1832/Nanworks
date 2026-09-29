"""Reconcile recorded sweep completion with the specific norm-vs-main comparison."""
from pathlib import Path
from statistics import mean
import csv
import hashlib
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sources = {}


def read(p):
    b = p.read_bytes()
    sources[str(p)] = hashlib.sha256(b).hexdigest()
    return b.decode("utf-8-sig")


def rc(p):
    return list(csv.DictReader(read(p).splitlines()))


def table(headers, rr):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] +
                     ["| " + " | ".join(str(x) for x in r) + " |" for r in rr])


METHODS = ("main_abs_cos_new_norm", "new_norm_only")
rr = [r for r in rc(OUT / "candidate_topk.csv") if r["method"] in METHODS]
candidates = {(r["dataset"], r["model"], r["method"]): r for r in rr}
outcomes = rc(ROOT / "outputs/visual_lga_vs_main_20260925/verified_outcomes_with_flags.csv")
ymap = {(r["dataset"], r["model"], int(r["layer"])): r for r in outcomes}
metrics = {(r["dataset"], r["model"], r["method"]): r for r in rc(OUT / "method_metrics.csv")
           if r["profile"] == "clean" and r["k"] == "3" and r["method"] in METHODS}
matrix = []
for ds, model in sorted({(r["dataset"], r["model"]) for r in rr}):
    row = dict(dataset=ds, model=model, gradient_coverage=float(candidates[ds, model, METHODS[0]]["coverage"]))
    for method, label in zip(METHODS, ("ours", "norm")):
        chosen = candidates[ds, model, method]["top3"]
        ls = [int(x[1:]) for x in chosen.split(",")]
        existing = [ymap.get((ds, model, l)) for l in ls]
        row[label+"_top3"] = chosen
        row[label+"_recorded_complete"] = all(r and r["historical_exclusion"] in ("", "stable_only") for r in existing)
        row[label+"_main_complete"] = all(r and not r["clean_exclusion"] for r in existing)
        row[label+"_absent_layers"] = ",".join(f"L{l}" for l, r in zip(ls, existing) if r is None)
        row[label+"_excluded_layers"] = ",".join(f"L{l}:{r['clean_exclusion']}" for l, r in zip(ls, existing) if r and r["clean_exclusion"])
    row["pair_recorded_complete"] = row["ours_recorded_complete"] and row["norm_recorded_complete"]
    row["pair_main_complete"] = row["ours_main_complete"] and row["norm_main_complete"]
    row["pair_main_coverage80"] = row["pair_main_complete"] and row["gradient_coverage"] >= .8
    matrix.append(row)

counts = {k: sum(r[k] for r in matrix) for k in ("ours_recorded_complete", "ours_main_complete", "pair_recorded_complete", "pair_main_complete", "pair_main_coverage80")}
assert counts == dict(ours_recorded_complete=19, ours_main_complete=18, pair_recorded_complete=17, pair_main_complete=16, pair_main_coverage80=15)
formal = json.loads(read(ROOT / "outputs/localization_audit_20260922/formal8_union_status.json"))
formal_covered = sum(all(c["states"][str(l)]["status"] in ("evaluated_main_historical_acceptance", "evaluated_stable_only", "diagnostic_eval_only") for l in c["top3"]) for c in formal["combinations"])
assert formal_covered == 19
summaries = []
for label, selector in (("同配置完整配对，不按梯度覆盖率排除", "pair_main_complete"), ("同配置完整配对，另加覆盖率至少80%", "pair_main_coverage80")):
    selected = [r for r in matrix if r[selector]]
    out = dict(scope=label, n=len(selected))
    for method, side in zip(METHODS, ("ours", "norm")):
        mm = [metrics[r["dataset"], r["model"], method] for r in selected]
        for col in ("best", "mean"):
            out[side+"_"+col] = mean(float(r[col]) for r in mm)
    summaries.append(out)
with (OUT / "组数口径_21组合明细.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(matrix[0])); w.writeheader(); w.writerows(matrix)
with (OUT / "组数口径_16与15组汇总.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summaries[0])); w.writeheader(); w.writerows(summaries)

doc = """# 19组、16组与15组：实验记录口径核对

核对日期：2026-09-25。范围：当前已回填本地台账、9月22日八方法覆盖审计、9月24日归档，以及上一轮9月25日分析用的锁定结果。不把尚未核验／回填的运行进展提前算作完整成绩。

**用户所说的19/21组符合现有扫层台账的覆盖口径。上次15组是附加筛选后的两公式消融子集，不是实验完成组数。** 上次最终回答没有将这些分母明确分开，需要澄清。

## 一、当前记录分别是多少组

| 问题 | 组数 | 具体含义 |
|---|---:|---|
| 正式八方法 Top-3 联合候选已有评测覆盖 | 19/21 | 缺口集中在 EVQA×LLaVA、MMKE-entity×LLaVA；含两组 PaliGemma 的协议例外 |
| Ours 自身 Top-3 已有评测 | 19/21 | 同样两组 LLaVA 在已回填结果中未齐 |
| Ours 自身 Top-3，排除 stable-only | 18/21 | 再排 MMKE-visual×PaliGemma |
| Ours 与纯范数双方 Top-3 都有评测，允许展示 stable | 17/21 | 再要求纯范数新增候选层有结果；含 stable 的结果不能直接当作主配置公平比较 |
| Ours 与纯范数双方 Top-3 完整、同配置可比 | **16/21** | 排除上述 stable-only；保留有真实编辑评测但梯度覆盖率较低的 BLIP2 组，并标注覆盖率 |
| 上次额外要求梯度覆盖率至少80%的子集 | **15/21** | 进一步排除 MMKE-entity×BLIP2，284/636=44.654% |

80%是上一轮复核采用的分析筛选条件，不是“真实扫层实验完成”的验收条件，也未被本轮证明为应当唯一采用的阈值。应同时报告16组完整配对和15组覆盖率筛选敏感性结果。

历史正式七方法公平表的17组，是比较所有正式方法的另一集合；它不是这里“允许stable的两公式17组”。历史验收表保留恢复早停／数值异常标签，不能把历史17组进一步表述为已重新审计全部满足标准50轮。

## 二、为什么19组会变成15组

从19组已有覆盖的组合开始，以下四组在上次分析被额外排除：

| 组合 | Ours Top-3 | 纯范数 Top-3 | 原因 |
|---|---|---|---|
| EVQA×InstructBLIP | L1,L0,L11 | L1,L0,L9 | Ours已齐，但纯范数L9无本地合格评测记录；不在既有正式八方法Top-3必跑并集中 |
| MMKE-visual×LLaVA | L0,L3,L1 | L5,L0,L6 | 正式扫层并集已有覆盖，但纯范数新增L5/L6未齐；不是整组正式扫层未完成 |
| MMKE-visual×PaliGemma | L5,L4,L3 | L4,L5,L3 | L3/L5已有stable结果，不是没有结果；上次排除混合配置 |
| MMKE-entity×BLIP2 | L0,L1,L2 | L0,L1,L2 | 双方编辑评测已齐、候选集合相同；只因归档梯度覆盖率44.654%被额外筛除 |

因此：**19 − 2个纯范数候选缺口组合 − 1个stable-only组合 = 16；再减1个低梯度覆盖组合 = 15。**

“正式方法候选并集完成”不代表每层、每个后来新增消融公式的候选层都已完成训练评测。EVQA×InstructBLIP L9、MMKE-visual×LLaVA L5/L6正属于这种差别。主手册3.4.8的Top-5附加缺口也列有这些层。

## 三、16组与15组分别重算

"""
doc += table(["范围", "组数", "Ours Best@3", "纯范数 Best@3", "Ours Mean@3", "纯范数 Mean@3"], [[r["scope"],r["n"],f'{r["ours_best"]:.3f}',f'{r["norm_best"]:.3f}',f'{r["ours_mean"]:.3f}',f'{r["norm_mean"]:.3f}'] for r in summaries])
doc += """

补回低覆盖BLIP2后是16组，并未改变双方相同候选集合的性质；只改变汇总分母和绝对均值。不能将原15组数值直接改标签为19组。若希望完成19组的两公式比较，需要先取得新增候选层结果，并明确PaliGemma配置及低覆盖的处理口径。

## 四、来源与时效

- `md/Location/6location_7model_3datas_top_3_5_layers_outcome.md` 第3.4.8节（1284行起）：19/21已有覆盖及协议例外；1312、1321行列出上述纯范数相关缺层。
- `md/TODO/Second_prashe/Firstprash_testvalue_our_direct_recommend.md` 第45行：Ours已有评测19组、排除stable-only后18组。
- 本目录 `candidate_topk.csv`、`method_metrics.csv` 与上一轮 `verified_outcomes_with_flags.csv`：逐层重算16组／15组。
- 9月25日运行记录已提到EVQA×LLaVA推进到L4，说明运行状态可能领先于已回填台账；本核对不据此推定未读到的L2/L4最终成绩。即使L2随后补齐，两公式配对仍需要纯范数额外的L3，不能据L2完成直接增加两公式配对组数。

本文件修正统计口径的说明，不修改训练状态、候选层或原始实验成绩。机器可读逐组证据见 `组数口径_21组合明细.csv`。
"""
(OUT / "组数口径核对_19组与15组.md").write_text(doc,encoding="utf-8")
(OUT / "group_count_verification.json").write_text(json.dumps(dict(counts=counts,formal8_recorded_coverage=formal_covered,summaries=summaries,sources=sources),ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(dict(counts=counts,summaries=summaries),ensure_ascii=False,indent=2))
