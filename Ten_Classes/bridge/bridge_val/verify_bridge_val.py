import json
import os

JSONL = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\bridge\bridge_val\30_bridge_val_image_urls_dedup.jsonl"
IMGS  = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\bridge\bridge_val\bridge_images"

def load_ids(path):
    ids = set()
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            iid = obj.get("image_id")
            if iid:
                ids.add(iid)
    return ids

def load_files(d):
    ids = set()
    if not os.path.isdir(d):
        return ids
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            stem, ext = os.path.splitext(name)
            if ext.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                ids.add(stem)
    return ids

exp  = load_ids(JSONL)
act  = load_files(IMGS)
miss  = sorted(exp - act)
extra = sorted(act - exp)

print(f"expected : {len(exp)}")
print(f"actual   : {len(act)}")
print(f"matched  : {len(exp & act)}")
print(f"missing  : {len(miss)}")
print(f"extra    : {len(extra)}")
if miss:
    print("missing_ids:", miss)
if extra:
    print("extra_ids  :", extra)
