import json
import os
from glob import glob


BASE = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes"
CLASSES = ["monastery", "mosque", "museum", "palace", "sculpture", "theatre", "tower"]


def load_expected_ids(jsonl_path):
    ids = set()
    with open(jsonl_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            image_id = obj.get("image_id")
            if image_id:
                ids.add(image_id)
    return ids


def load_actual_ids(images_dir):
    ids = set()
    if not os.path.isdir(images_dir):
        return ids
    for name in os.listdir(images_dir):
        path = os.path.join(images_dir, name)
        if not os.path.isfile(path):
            continue
        stem, ext = os.path.splitext(name)
        if ext.lower() in {".jpg", ".jpeg", ".png", ".webp"} and os.path.getsize(path) > 0:
            ids.add(stem)
    return ids


def pick_image_urls_jsonl(split_dir):
    candidates = sorted(glob(os.path.join(split_dir, "*image_urls*.jsonl")))
    if not candidates:
        return None
    # Prefer dedup file if present
    for c in candidates:
        if "dedup" in os.path.basename(c).lower():
            return c
    return candidates[0]


def verify_one(class_name, split):
    split_dir = os.path.join(BASE, class_name, f"{class_name}_{split}")
    jsonl_path = pick_image_urls_jsonl(split_dir)
    images_dir = os.path.join(split_dir, f"{class_name}_images")

    if not jsonl_path:
        return {
            "class": class_name,
            "split": split,
            "status": "no_image_urls_jsonl",
        }

    expected = load_expected_ids(jsonl_path)
    actual = load_actual_ids(images_dir)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    return {
        "class": class_name,
        "split": split,
        "status": "ok",
        "jsonl": os.path.basename(jsonl_path),
        "expected": len(expected),
        "actual": len(actual),
        "matched": len(expected & actual),
        "missing_n": len(missing),
        "extra_n": len(extra),
        "missing_sample": missing[:8],
        "extra_sample": extra[:8],
    }


def main():
    results = []
    for c in CLASSES:
        for split in ("train", "val"):
            results.append(verify_one(c, split))

    for r in results:
        print(f"[{r['class']} | {r['split']}]")
        if r["status"] != "ok":
            print(f"  status: {r['status']}")
            print()
            continue
        print(f"  jsonl       : {r['jsonl']}")
        print(f"  expected_ids: {r['expected']}")
        print(f"  actual_files: {r['actual']}")
        print(f"  matched     : {r['matched']}")
        print(f"  missing     : {r['missing_n']}")
        print(f"  extra       : {r['extra_n']}")
        if r["missing_n"] > 0:
            print(f"  missing_sample: {', '.join(r['missing_sample'])}")
        if r["extra_n"] > 0:
            print(f"  extra_sample  : {', '.join(r['extra_sample'])}")
        print()


if __name__ == "__main__":
    main()
