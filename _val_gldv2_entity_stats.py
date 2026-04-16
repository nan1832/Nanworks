import json
from collections import defaultdict
from pathlib import Path
import csv

BASE = Path(r"e:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset")
VAL_DIR = BASE / r"downloads\Reasonvqa\Val\GLDv2"
VAL_JSONL = VAL_DIR / "gldv2_val.jsonl"
VAL_ANN_JSONL = VAL_DIR / "gldv2_val_ann.jsonl"
OUT_CSV = VAL_DIR / "gldv2_val_entity_stats.csv"

def main():
    if not VAL_JSONL.exists() or not VAL_ANN_JSONL.exists():
        raise FileNotFoundError("Missing GLDv2 val files")

    qid2img = {}
    with VAL_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            qid = int(o["question_id"])
            qid2img[qid] = o["image_id"]

    ent_imgs = defaultdict(set)   # entity -> set(image_id)
    ent_qs = defaultdict(int)     # entity -> question count

    with VAL_ANN_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            qid = int(o["question_id"])
            if qid not in qid2img:
                continue
            entity = o.get("entity_name") or "UNKNOWN"
            ent_qs[entity] += 1
            ent_imgs[entity].add(qid2img[qid])

    rows = []
    for ent, qn in ent_qs.items():
        rows.append((ent, len(ent_imgs[ent]), qn))
    rows.sort(key=lambda x: x[2], reverse=True)

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entity_name", "images", "questions"])
        for ent, im, qn in rows:
            w.writerow([ent, im, qn])

    print(f"entities={len(rows)}")
    print(f"saved: {OUT_CSV}")

if __name__ == "__main__":
    main()
