"""Check figure artifacts, plotted data, and preservation of the case-report prose."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[1]
FIGS=ROOT/"md/Location/related_work.md/figures/contribution_edit_cases_20260929"
DATA=ROOT/"outputs/visedit_contribution_cases_20260929"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=load(FIGS/"figure_manifest.json")
report=ROOT/manifest["report"]
assert sha(report)==manifest["report_sha256"]
assert manifest["count"]==10 and len(manifest["figures"])==10
assert sorted(r["number"] for r in manifest["figures"])==list(range(1,11))
for fig in manifest["figures"]:
    for format_name,relative in fig["outputs"].items():
        p=ROOT/relative
        assert p.is_file() and p.stat().st_size>10000
        assert sha(p)==fig["sha256"][format_name]
        if format_name in ["png","preview"]:
            assert p.read_bytes()[:8]==b"\x89PNG\r\n\x1a\n"
            b=p.read_bytes()
            width,height=int.from_bytes(b[16:20],"big"),int.from_bytes(b[20:24],"big")
            assert width>1000 and height>800
            if format_name=="png":assert width>=4500
        elif format_name=="pdf":assert p.read_bytes().startswith(b"%PDF-")
        elif format_name=="svg":assert ET.parse(p).getroot().tag.endswith("svg")
ledger=load(ROOT/"outputs/sweep_ledger_20260928_110311/ledger.json")
pool={(r["dataset"],r["model"],r["layer"]):r for r in ledger["rows"] if r["recipe"]=="main"}
with (DATA/"layer_alignment.csv").open(encoding="utf-8-sig",newline="") as f:
    aligned={(r["dataset"],r["model"],r["target"],r["module"],int(r["layer"])):r for r in csv.DictReader(f)}
count=0
with (FIGS/"figure_data.csv").open(encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        assert "paligemma" not in r["model"]
        key=(r["dataset"],r["model"],r["target"],r["module"],int(r["layer"]))
        src=aligned[key]
        assert float(r["contribution"])==float(src["positive_contribution"])
        assert int(r["global_rank"])==int(src["contribution_rank"])
        actual=pool.get((r["dataset"],r["model"],int(r["layer"])))
        assert (r["evaluated"]=="True")==bool(actual)
        for m in ["Rel","T-Gen","M-Gen","T-Loc","M-Loc","Average"]:
            if actual:assert float(r[m])==actual["metrics"][m]
            else:assert not r[m]
        count+=1
for fig in manifest["figures"]:
    for c in fig["comparisons"]:
        if fig["number"]==2:
            for layers_name,score_name in [("pre_layers","pre"),("middle_layers","middle")]:
                vals=[pool[c["dataset"],c["model"],l]["metrics"]["Average"] for l in c[layers_name]]
                expected={"top1":vals[0],"best3":max(vals),"mean3":sum(vals)/3}[c["measure"]]
                assert abs(expected-c[score_name])<1e-10
            assert abs(c["delta"]-(c["middle"]-c["pre"]))<1e-10
        else:
            ref=pool[fig["ds"],fig["model"],c["ref_layer"]]
            high=pool[fig["ds"],fig["model"],c["high_layer"]]
            assert c["ref_contribution"]<c["high_contribution"]
            for metric,value in c["deltas"].items():
                assert abs(value-(ref["metrics"][metric]-high["metrics"][metric]))<1e-10
text=report.read_text(encoding="utf-8")
assert text.count("![图 ")==10
assert "\ufffd" not in text
links=re.findall(r'\]\(<([^>]+)>\)',text)
assert all(Path(p).is_file() for p in links)
stripped=re.sub(r"<!-- CASE_FIGURE_.*?_BEGIN -->.*?<!-- CASE_FIGURE_.*?_END -->\n*","",text,flags=re.S)
stripped=re.sub(r"<!-- CASE_FIGURES_GUIDE_BEGIN -->.*?<!-- CASE_FIGURES_GUIDE_END -->\n*","",stripped,flags=re.S)
before=(DATA/"related_work_report_before_figures.md").read_text(encoding="utf-8-sig")
assert stripped==before,"Figure insertion changed existing prose or tables."
result=dict(passed=True,figures=10,artifact_files=40,checked_plot_rows=count,all_missing_metrics_blank=True,
            old_prose_and_tables_preserved=True,report_sha256=sha(report),valid_links=len(links))
(FIGS/"verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
