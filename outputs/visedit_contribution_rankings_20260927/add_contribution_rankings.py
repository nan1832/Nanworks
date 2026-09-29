"""Add actual contribution rankings alongside, not in place of, Pre candidates."""
import ast
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
LEDGER = ROOT / "md/Location/6location_7model_3datas_top_3_5_layers_outcome.md"
INPUT = ROOT / "outputs/visedit_target_variants_20260927/visedit_target_candidates_21x2.csv"
MODELS = {
    "BLIP2-OPT-2.7B": "blip2-opt-2.7b",
    "InstructBLIP-Vicuna-7B": "instructblip-vicuna-7b",
    "MiniGPT-4-Vicuna-7B": "minigpt-4-vicuna-7b",
    "LLaVA-v1.5-7B": "llava-v1.5-7b",
    "Qwen2.5-VL-3B": "qwen2.5-vl-3b",
    "PaliGemma-3B": "paligemma-3b",
    "SmolVLM-Instruct-1.7B": "smolvlm-1.7b",
}
source_script = ROOT / "VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py"
tree = ast.parse(source_script.read_text(encoding="utf-8"))
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"moving_average", "find_high_region", "pre_candidates"}]
assert len(functions) == 3
ns = {"np": np}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_script), "exec"), ns)

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def layer_list(xs):
    return ",".join("L" + str(int(x)) for x in xs)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

manifest = read_json(OUT / "source_manifest.json")
for entry in manifest["files"]:
    assert sha(OUT / "raw" / entry["relative_path"]) == entry["sha256"]
rows = list(csv.DictReader(INPUT.open(encoding="utf-8-sig", newline="")))
assert len(rows) == 42
results = []
all_scores = []
sources = {}
for r in rows:
    r = dict(r)
    additions = dict(contribution_top5="", contribution_top5_scores="", peak_layer="", peak_score="",
                     contribution_score_source="", contribution_score_sha256="", ranking_status="pending_model_pred_scores")
    if r["status"] == "done":
        mmke = r["dataset"].startswith("MMKE-")
        p = (OUT / "raw" / r["dataset"].lower() / MODELS[r["model"]] / "layer_scores.csv") if mmke else ROOT / r["source"]
        cfg = read_json(p.with_name("config.json"))
        summary = read_json(p.with_name("summary.json"))
        expected_mode = "dataset_key_token" if mmke else r["target_mode"]
        assert cfg["key_mode"] == summary["key_mode"] == expected_mode
        n = int(r["sample_count"])
        assert cfg["sample_count"] == n
        assert summary["valid_sample_count" if mmke else "sample_count"] == n
        scores = list(csv.DictReader(p.open(encoding="utf-8-sig", newline="")))
        assert [int(s["layer"]) for s in scores] == list(range(len(scores)))
        vals = np.array([float(s["score_positive"]) for s in scores])
        assert np.isfinite(vals).all()
        expected = [max(0, float(s["attn_mean"])) + max(0, float(s["mlp_mean"])) for s in scores]
        assert np.allclose(vals, expected, rtol=1e-7, atol=1e-12)
        archived_order = sorted(range(len(scores)), key=lambda i:int(scores[i]["rank_positive"]))
        assert sorted(int(s["rank_positive"]) for s in scores) == list(range(1,len(scores)+1))
        assert all(vals[a] >= vals[b] for a,b in zip(archived_order, archived_order[1:]))
        top = archived_order[:5]
        summary_top = summary["top5_direct_layers"] if mmke else summary["top10_positive"][:5]
        assert top == summary_top
        # Ensure contribution files belong to the same protocol/version as current Pre candidates.
        smooth = ns["moving_average"](vals, 3)
        region, threshold, _ = ns["find_high_region"](smooth, 0.5)
        assert region is not None
        assert layer_list(ns["pre_candidates"](region[0],3)) == r["top3"]
        assert layer_list(ns["pre_candidates"](region[0],5)) == r["top5"]
        if mmke:
            assert summary["top3_pre_layers"] == ns["pre_candidates"](region[0],3)
            assert summary["top5_pre_layers"] == ns["pre_candidates"](region[0],5)
        additions = dict(contribution_top5=layer_list(top),
                         contribution_top5_scores=json.dumps([float(vals[i]) for i in top]),
                         peak_layer="L"+str(top[0]), peak_score=float(vals[top[0]]),
                         contribution_score_source=p.relative_to(ROOT).as_posix(),
                         contribution_score_sha256=sha(p), ranking_status="done")
        for item in [p,p.with_name("config.json"),p.with_name("summary.json")]:
            sources[item.relative_to(ROOT).as_posix()] = sha(item)
        for rank,i in enumerate(archived_order,1):
            all_scores.append(dict(dataset=r["dataset"],model=r["model"],method=r["method"],
                                   layer=i,score_positive=float(vals[i]),rank_positive=rank,
                                   score_positive_smoothed=float(smooth[i]),
                                   source=additions["contribution_score_source"]))
    r.update(additions)
    results.append(r)

def write_csv(path, data):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

write_csv(OUT / "visedit_candidates_and_contribution_top5.csv", results)
write_csv(OUT / "visedit_all_layer_contribution_rankings.csv", all_scores)
lookup={(r["dataset"],r["model"],r["method"]):r for r in results}
backup=OUT / "backups" / LEDGER.name
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    backup.write_bytes(LEDGER.read_bytes())
before=backup.read_text(encoding="utf-8-sig")
assert LEDGER.read_text(encoding="utf-8-sig")==before, "Ledger changed since snapshot"
start="### 2.2 VisEdit-Contrib-Pre-alt 与 VisEdit-Contrib-Pre-model_pred"
end="#### 2.2.1 MMKE strict KeyToken 与历史 FirstToken 差异诊断"
prefix,tail=before.split(start,1)
section,suffix=tail.split(end,1)
header="| Dataset | Model | Method | Top-3 | Top-5 | 状态/目标粒度 |"
newheader="| Dataset | Model | Method | Pre 候选 Top-3 | Pre 候选 Top-5 | 贡献度 Top-5（高→低） | 最高贡献层（分数） | 状态/目标粒度 |"
note="""**新增贡献度排序列（2026-09-27）：** “贡献度 Top-5”按各层**未经平滑**的 `score_positive = max(0, attn_mean) + max(0, mlp_mean)` 从高到低排列，Attention/MLP 贡献先按定位样本取均值；“最高贡献层”是该排序第一层，括号内为其分数（显示 6 位有效数字，完整精度保存在 CSV）。同分沿用原始 `rank_positive` 顺序。每行仅在该数据集、模型与目标版本内排序，不把不同组合的分数混排。

`Pre 候选 Top-3/Top-5` 仍由平滑后的高贡献区起点向前取层；因此最高贡献层与首个推荐编辑层可以不同。MMKE-alt 采用已完成的 KeyToken 分数，不使用历史 FirstToken 峰值代替。缺 model_pred 分数的十四组继续标为待计算。

"""
assert section.count(header)==1
section=section.replace(header,note+newheader,1)
lines=section.splitlines()
updated=[];count=0
for line in lines:
    if line=="|---|---|---|---|---|---|":
        updated.append("|---|---|---|---|---|---|---|---|")
    elif line.startswith("| "):
        cells=[v.strip() for v in line.strip("|").split("|")]
        key=tuple(cells[:3])
        if key in lookup:
            r=lookup[key]
            assert len(cells)==6
            if r["ranking_status"]=="done":
                top=r["contribution_top5"]
                peak=f"{r['peak_layer']} ({r['peak_score']:.6g})"
            else:
                top=peak="待计算"
            cells=cells[:5]+[top,peak,cells[5]]
            line="| "+" | ".join(cells)+" |"
            count+=1
        updated.append(line)
    else:
        updated.append(line)
assert count==42
csvpath=(OUT/"visedit_candidates_and_contribution_top5.csv").as_posix()
layerpath=(OUT/"visedit_all_layer_contribution_rankings.csv").as_posix()
sourcepath=(OUT/"source_manifest.json").as_posix()
section="\n".join(updated).rstrip()+f"\n\n完整精度及逐行来源见 [候选与贡献度 Top-5 CSV](<{csvpath}>)；全部层排名见 [逐层贡献度表](<{layerpath}>)；MMKE 原始 KeyToken 文件只读取自服务器归档，见 [来源清单与 SHA-256](<{sourcepath}>)。\n\n"
after=prefix+start+section+end+suffix
assert after.split(start,1)[0]==before.split(start,1)[0]
assert after.split(end,1)[1]==before.split(end,1)[1]
# Independently check every rendered value and preservation of existing Pre columns/status.
rendered=[l for l in section.splitlines() if l.startswith("| ") and "VisEdit-Contrib-Pre-" in l]
assert len(rendered)==42
for line in rendered:
    c=[v.strip() for v in line.strip("|").split("|")]
    assert len(c)==8
    r=lookup[tuple(c[:3])]
    assert c[3]==(r["top3"] or "待计算") and c[4]==(r["top5"] or "待计算")
    if r["ranking_status"]=="done":
        assert c[5]==r["contribution_top5"] and c[6].startswith(c[5].split(",")[0]+" (")
    else:
        assert c[5]==c[6]=="待计算"
LEDGER.write_text(after,encoding="utf-8")
verification=dict(candidate_rows=42,ranked_groups=28,pending_groups=14,
                  layer_score_rows=len(all_scores),
                  archived_rank_and_summary_match=True,all_pre_candidates_reproduced=True,
                  all_content_outside_section_2_2_main_table_unchanged=True,
                  ledger_sha256=sha(LEDGER),source_sha256=sources,
                  ranking_rule="unsmoothed score_positive descending, archived rank_positive breaks ties",
                  peak_display_precision="6 significant digits; full precision in CSV")
(OUT/"verification.json").write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in verification.items() if k!="source_sha256"},ensure_ascii=False,indent=2))
print("Examples:")
for r in results:
    if r["model"]=="BLIP2-OPT-2.7B" and r["ranking_status"]=="done":
        print(r["dataset"],r["method"],r["contribution_top5"],r["peak_layer"],r["peak_score"])
