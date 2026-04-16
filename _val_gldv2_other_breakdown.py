import json
import re
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(r"e:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset")
VAL_DIR = BASE / r"downloads\Reasonvqa\Val\GLDv2"
VAL_JSONL = VAL_DIR / "gldv2_val.jsonl"
ANN_JSONL = BASE / r"downloads\Reasonvqa\val_ann.jsonl"
FULL_TSV = BASE / r"DataDivision\Singleclass\GLDV2\Cluster\clusters_rank.tsv"
OUT_TOKEN_TSV = VAL_DIR / "gldv2_val_other_token_rank.tsv"
OUT_EXAMPLE_TSV = VAL_DIR / "gldv2_val_other_examples.tsv"

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

STOP = set("""
the of and de la le les el los das dos do du da di del saint st san santa sao
new old great little small big upper lower east west north south city town
""".split())

def tokenize(nname: str):
    nname = re.sub(r"[^a-z]+", " ", nname)
    toks = [t for t in nname.split() if len(t) >= 3 and t not in STOP]
    return toks

def main():
    if not VAL_JSONL.exists() or not ANN_JSONL.exists() or not FULL_TSV.exists():
        raise FileNotFoundError("Missing input files")

    clusters = load_clusters()
    patt = [(c, re.compile(r"\b" + re.escape(c) + r"\b", re.I)) for c in clusters]

    # qid -> image
    qid2img = {}
    with VAL_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            qid2img[int(o["question_id"])] = o["image_id"]

    # assign cluster; collect others' names
    other_names = {}
    with ANN_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            qid = int(o["question_id"])
            if qid not in qid2img:
                continue
            name = o.get("entity_name", "") or ""
            nname = norm(name)
            found = None
            for key, p in patt:
                if p.search(nname):
                    found = key
                    break
            if found is None:
                other_names[qid] = name

    # token stats
    tok_q = Counter()
    tok_imgs = defaultdict(set)
    examples = defaultdict(list)
    for qid, name in other_names.items():
        img = qid2img[qid]
        nname = norm(name)
        toks = tokenize(nname)
        # unigrams
        for t in toks:
            tok_q[t] += 1
            tok_imgs[t].add(img)
            if len(examples[t]) < 3:
                examples[t].append((qid, name))
        # bigrams
        for i in range(len(toks)-1):
            bg = toks[i] + " " + toks[i+1]
            tok_q[bg] += 1
            tok_imgs[bg].add(img)
            if len(examples[bg]) < 3:
                examples[bg].append((qid, name))

    # write token rank
    rows = [(t, len(tok_imgs[t]), tok_q[t]) for t in tok_q]
    rows.sort(key=lambda x: x[2], reverse=True)
    with OUT_TOKEN_TSV.open("w", encoding="utf-8") as f:
        f.write("token\timages\tquestions\n")
        for t, im, qn in rows:
            f.write(f"{t}\t{im}\t{qn}\n")

    # write examples
    with OUT_EXAMPLE_TSV.open("w", encoding="utf-8") as f:
        f.write("token\tqid\texample_entity_name\n")
        for t, _, _ in rows[:200]:
            for qid, name in examples[t]:
                f.write(f"{t}\t{qid}\t{name}\n")

    print(f"Saved {OUT_TOKEN_TSV}")
    print(f"Saved {OUT_EXAMPLE_TSV}")

if __name__ == "__main__":
    main()
