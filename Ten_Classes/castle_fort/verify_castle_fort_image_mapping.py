import json
import os


def load_expected_ids(jsonl_path):
    ids = []
    with open(jsonl_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            image_id = obj.get("image_id")
            if image_id:
                ids.append(image_id)
    return set(ids)


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


def verify(split_name, expected_jsonl, images_dir):
    expected = load_expected_ids(expected_jsonl)
    actual = load_actual_ids(images_dir)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    matched = len(expected & actual)

    print(f"[{split_name}]")
    print(f"  expected_ids: {len(expected)}")
    print(f"  actual_files: {len(actual)}")
    print(f"  matched     : {matched}")
    print(f"  missing     : {len(missing)}")
    print(f"  extra       : {len(extra)}")
    if missing:
        print("  missing_sample:", ", ".join(missing[:10]))
    if extra:
        print("  extra_sample  :", ", ".join(extra[:10]))
    print()


def main():
    base = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\castle_fort"
    verify(
        "castle_fort_train",
        os.path.join(base, "castle_fort_train", "30_castle_fort_image_urls.jsonl"),
        os.path.join(base, "castle_fort_train", "castle_fort_images"),
    )
    verify(
        "castle_fort_val",
        os.path.join(base, "castle_fort_val", "30_castle_fort_val_image_urls.jsonl"),
        os.path.join(base, "castle_fort_val", "castle_fort_images"),
    )


if __name__ == "__main__":
    main()
