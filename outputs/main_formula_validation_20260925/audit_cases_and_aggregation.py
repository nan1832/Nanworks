"""Audit cached per-sample diagnostics without model inference or source writes."""
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean
import csv
import hashlib
import json
import math
import re
import string
import sys

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PAIRED = ROOT.parent / "phase2_p3/g1_paired_official955_20260921"
sources = {}


def read(path):
    b = path.read_bytes()
    sources[str(path)] = hashlib.sha256(b).hexdigest()
    return b.decode("utf-8-sig")


def wc(name, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def normalize(s):
    s = s.casefold().translate(str.maketrans("", "", string.punctuation))
    return " ".join(re.sub(r"\b(a|an|the)\b", " ", s).split())


def word_f1(pred, target):
    a, b = normalize(pred).split(), normalize(target).split()
    if not a or not b:
        return float(a == b)
    overlap = sum((Counter(a) & Counter(b)).values())
    return 2.0 * overlap / (len(a) + len(b))


read(ROOT.parent / "phase2_p3/additional_metrics.py")
read(PAIRED / "ALL_DONE")
records, configs, summaries = {}, {}, {}
metric_checks = 0
for mode in ("free", "teacher"):
    configs[mode] = json.loads(read(PAIRED / mode / "config.json"))
    summaries[mode] = json.loads(read(PAIRED / mode / "summary.json"))
    rr = [json.loads(x) for x in read(PAIRED / mode / "samples.jsonl").splitlines() if x.strip()]
    assert len(rr) == len({r["sample_id"] for r in rr}) == 955
    assert len({r["source_record_index"] for r in rr}) == 955
    assert [r["source_record_index"] for r in rr] == list(range(955))
    assert configs[mode]["parameter_updates"] == 0
    assert summaries[mode]["status"] == "PAIRED_EVALUATION_COMPLETE"
    records[mode] = {r["sample_id"]: r for r in rr}
    for sample in rr:
        for r in sample["rows"]:
            for side in ("before", "after"):
                # Recompute string metrics independently of the saved score.
                assert abs(word_f1(r[side]["prediction"], r["target"]) - r[side]["token_f1"]) < 1e-10
                assert float(normalize(r[side]["prediction"]) == normalize(r["target"])) == r[side]["exact_match"]
                metric_checks += 2
assert records["free"].keys() == records["teacher"].keys()
assert configs["free"]["checkpoint_sha256"] == configs["teacher"]["checkpoint_sha256"]
assert configs["free"]["data_sha256"] == configs["teacher"]["data_sha256"]

flat, by_sample, group_rows = [], {}, defaultdict(list)
for sid, sample in records["free"].items():
    teacher = {(r["group"], r["item_index"]): r for r in records["teacher"][sid]["rows"]}
    assert len(teacher) == len(sample["rows"])
    for r in sample["rows"]:
        t = teacher[r["group"], r["item_index"]]
        assert all(t[c] == r[c] for c in ("prompt", "target", "image_path"))
        group_rows[r["group"]].append(r)
        if r["group"] != "reliability":
            continue
        row = dict(sample_id=sid, source_record_index=sample["source_record_index"],
                   free_before_f1=r["before"]["token_f1"], free_after_f1=r["after"]["token_f1"],
                   free_delta_f1=r["after"]["token_f1"]-r["before"]["token_f1"],
                   free_before_em=r["before"]["exact_match"], free_after_em=r["after"]["exact_match"],
                   truncated_before=r["before"]["truncated"], truncated_after=r["after"]["truncated"],
                   teacher_before_acc=t["before"]["token_accuracy"], teacher_after_acc=t["after"]["token_accuracy"],
                   teacher_delta_acc=t["after"]["token_accuracy"]-t["before"]["token_accuracy"])
        flat.append(row)
        by_sample[sid] = r, t
assert len(flat) == 955

overall = []
for g, rr in sorted(group_rows.items()):
    saved = summaries["free"]["metrics"][g]
    a, b = mean(r["before"]["token_f1"] for r in rr), mean(r["after"]["token_f1"] for r in rr)
    assert abs(saved["token_f1"]["before"]-a) < 1e-10
    assert abs(saved["token_f1"]["after"]-b) < 1e-10
    overall.append(dict(group=g, question_count=len(rr), before_f1=a, after_f1=b,
                        delta_f1_pp=100*(b-a), before_em=mean(r["before"]["exact_match"] for r in rr),
                        after_em=mean(r["after"]["exact_match"] for r in rr),
                        truncated_before=sum(r["before"]["truncated"] for r in rr),
                        truncated_after=sum(r["after"]["truncated"] for r in rr)))

# Transparent retrospective illustration rule: median change within each sign
# bucket, tie broken by source index. These are examples, not independent tests.
buckets = {"F1提高": [r for r in flat if r["free_delta_f1"] > 1e-12],
           "F1持平": [r for r in flat if abs(r["free_delta_f1"]) <= 1e-12],
           "F1下降": [r for r in flat if r["free_delta_f1"] < -1e-12]}
selected, case_index = [], []
for label, rr in buckets.items():
    if not rr:
        continue
    ordered = sorted(rr, key=lambda r: (r["free_delta_f1"], r["source_record_index"]))
    row = ordered[(len(ordered)-1)//2]
    sid = row["sample_id"]
    selected.append(dict(selection=label, bucket_count=len(rr), **row,
                         free_reliability=by_sample[sid][0], teacher_reliability=by_sample[sid][1],
                         all_free_rows=records["free"][sid]["rows"]))
    case_index.append(dict(selection=label, bucket_count=len(rr), **row))
# A fixed-index metric interpretation example, disclosed separately from medians.
row0 = next(r for r in flat if r["source_record_index"] == 0)
sid0 = row0["sample_id"]
selected.append(dict(selection="固定源索引0：检查F1与关键实体是否一致", bucket_count="", **row0,
                     free_reliability=by_sample[sid0][0], teacher_reliability=by_sample[sid0][1],
                     all_free_rows=records["free"][sid0]["rows"]))
# A purpose-selected positive illustration, not an estimate of semantic success.
# The extraction heuristic is disclosed; never convert its hit count to accuracy.
entity_examples = []
for row in flat:
    r, t = by_sample[row["sample_id"]]
    match = re.search(r"corresponds to ([^\n]+?)\.(?:\s|$)", r["target"])
    if not match or len(normalize(match[1])) < 3:
        continue
    entity = normalize(match[1])
    before = " " + normalize(r["before"]["prediction"]) + " "
    after_first_line = " " + normalize(r["after"]["prediction"].split("\n")[0]) + " "
    if (" " + entity + " ") not in before and (" " + entity + " ") in after_first_line:
        if row["free_delta_f1"] > 0 and not row["truncated_after"]:
            entity_examples.append((row, match[1]))
if entity_examples:
    row, entity = min(entity_examples, key=lambda x: x[0]["source_record_index"])
    sid = row["sample_id"]
    selected.append(dict(selection="目标实体出现且编辑后未截断的示例", bucket_count=len(entity_examples),
                         selection_target_entity=entity, **row,
                         free_reliability=by_sample[sid][0], teacher_reliability=by_sample[sid][1],
                         all_free_rows=records["free"][sid]["rows"]))
wc("free_generation_reliability_955.csv", sorted(flat, key=lambda r: r["source_record_index"]))
wc("free_generation_group_recheck.csv", overall)
wc("selected_case_index.csv", case_index)
(OUT / "selected_real_cases.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

# Aggregation-order diagnosis on the separate May bridge-training cache.
agg_rows, agg_tops = [], []
for model in ("blip2", "llava"):
    base = ROOT / f"server_results/bridge_vlm_visual_hidden_lga_{model}_train30"
    config = json.loads(read(base / "run_config.json"))
    archived = {int(r["layer"]): r for r in csv.DictReader(read(base / "visual_hidden_lga_layer_scores.csv").splitlines())}
    raw = [json.loads(x) for x in read(base / "sample_visual_hidden_scores.jsonl").splitlines() if x.strip()]
    groups = defaultdict(list)
    for r in raw:
        assert r["capture_point"] == "adapter_hook"
        groups[r["layer"]].append(r)
    assert len(groups) == 32
    ids = None
    for l, rr in sorted(groups.items()):
        this_ids = {r["case_id"] for r in rr}
        assert len(rr) == len(this_ids) == 30
        if ids is None:
            ids = this_ids
        assert ids == this_ids
        c = [r["s_vis_cos"] for r in rr]
        n = [r["vis_new_norm"] for r in rr]
        assert all(math.isfinite(x) for x in c+n)
        assert all(abs(x) <= 1.000001 for x in c)
        assert all(abs(r["s_vis_dot"]) <= r["vis_joint_norm"]*1.0001+1e-10 for r in rr)
        assert abs(mean(c)-float(archived[l]["S_vis_cos"])) < 1e-10
        assert abs(mean(n)-float(archived[l]["S_vis_new_norm"])) < 1e-10
        joint = [x*y for x, y in zip(c, n)]
        valid = mean(n) > 0 and mean(r["vis_old_norm"] for r in rr) > 0
        row = dict(model=model, layer=l, n=30, valid=valid, mean_cos=mean(c), mean_new_norm=mean(n),
                   current_product=abs(mean(c))*mean(n),
                   mean_absolute_projection=mean(abs(x) for x in joint),
                   absolute_mean_projection=abs(mean(joint)),
                   new_norm_only=mean(n),
                   positive_cos_count=sum(x > 0 for x in c), negative_cos_count=sum(x < 0 for x in c))
        agg_rows.append(row)
    for formula in ("current_product", "mean_absolute_projection", "absolute_mean_projection", "new_norm_only"):
        ordered = sorted([r for r in agg_rows if r["model"] == model and r["valid"]], key=lambda r: (-r[formula], r["layer"]))
        agg_tops.append(dict(model=model, formula=formula, samples=30, valid_layers=len(ordered),
                             top1=f'L{ordered[0]["layer"]}', top3=",".join(f'L{r["layer"]}' for r in ordered[:3]),
                             top5=",".join(f'L{r["layer"]}' for r in ordered[:5]),
                             scope="May bridge train30 diagnostic only; no formal 21-combination editing comparison"))
wc("bridge30_aggregation_layer_scores.csv", agg_rows)
wc("bridge30_aggregation_topk.csv", agg_tops)
summary = dict(raw_string_metric_checks=metric_checks, paired_unique_samples=955,
               group_summaries=overall, case_bucket_counts={k: len(v) for k, v in buckets.items()},
               teacher_improved_free_nonimproved=sum(r["teacher_delta_acc"] > 1e-12 and r["free_delta_f1"] <= 1e-12 for r in flat),
               selected_case_indices=[dict(selection=r["selection"], source_record_index=r["source_record_index"],
                                          free_delta_f1=r["free_delta_f1"], teacher_delta_acc=r["teacher_delta_acc"]) for r in selected],
               aggregation_topk=agg_tops, paired_config=configs["free"], source_sha256=sources)
(OUT / "case_aggregation_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k not in ("source_sha256", "paired_config", "group_summaries")}, ensure_ascii=False, indent=2))
for r in selected:
    q = r["free_reliability"]
    print(json.dumps(dict(selection=r["selection"], index=r["source_record_index"],
                         target=q["target"][:300], before=q["before"]["prediction"][:300],
                         after=q["after"]["prediction"][:420]), ensure_ascii=False))
