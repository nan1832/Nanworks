import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(r"e:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset")
VAL_DIR = BASE / r"downloads\Reasonvqa\Val\GLDv2"
VAL_JSONL = VAL_DIR / "gldv2_val.jsonl"
ANN_JSONL = BASE / r"downloads\Reasonvqa\val_ann.jsonl"
FULL_TSV = BASE / r"DataDivision\Singleclass\GLDV2\Cluster\clusters_rank.tsv"
OUT_TSV = VAL_DIR / "gldv2_val_clusters_rank.tsv"

def norm(txt: str) -> str:
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii").lower()

def load_clusters():
    cats = []
    with FULL_TSV.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue
            parts = line.strip().split("\t")
            if not parts or len(parts[0]) == 0:
                continue
            cats.append(parts[0])
    return cats

def main():
    if not VAL_JSONL.exists():
        raise FileNotFoundError(str(VAL_JSONL))
    if not ANN_JSONL.exists():
        raise FileNotFoundError(str(ANN_JSONL))
    if not FULL_TSV.exists():
        raise FileNotFoundError(str(FULL_TSV))

    clusters = load_clusters()
    patt = [(c, re.compile(r"\b" + re.escape(c) + r"\b", re.I)) for c in clusters]

    qid2img = {}
    with VAL_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            qid2img[int(o["question_id"])] = o["image_id"]

    q_cluster = {}
    with ANN_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            qid = int(o["question_id"])
            if qid not in qid2img:
                continue
            name = o.get("entity_name", "")
            nname = norm(name)
            found = None
            for key, p in patt:
                if p.search(nname):
                    found = key
                    break
            if found is None:
                found = "other"
            q_cluster[qid] = found

    img_set = defaultdict(set)
    q_cnt = defaultdict(int)
    for qid, img in qid2img.items():
        c = q_cluster.get(qid, "other")
        q_cnt[c] += 1
        img_set[c].add(img)

    rows = [(c, len(img_set[c]), q_cnt[c]) for c in q_cnt]
    rows.sort(key=lambda x: x[2], reverse=True)

    with OUT_TSV.open("w", encoding="utf-8") as f:
        f.write("cluster\timages\tquestions\n")
        for c, im, qs in rows:
            f.write(f"{c}\t{im}\t{qs}\n")

    print(f"Saved {OUT_TSV}")

if __name__ == "__main__":
    main()
