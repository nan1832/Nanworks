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
    return ids


def load_actual_ids(images_dir):
    ids = []
    for name in os.listdir(images_dir):
        path = os.path.join(images_dir, name)
        if not os.path.isfile(path):
            continue
        stem, ext = os.path.splitext(name)
        if ext.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            ids.append(stem)
    return ids


def verify(name, jsonl_path, images_dir):
    expected = set(load_expected_ids(jsonl_path))
    actual = set(load_actual_ids(images_dir))

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    matched = len(expected & actual)

    print(f"[{name}]")
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
    base = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\bridge"

    verify(
        "bridge_train",
        os.path.join(base, "bridge_train", "30_bridge_image_urls.jsonl"),
        os.path.join(base, "bridge_train", "bridge_images"),
    )
    verify(
        "bridge_val",
        os.path.join(base, "bridge_val", "30_bridge_val_image_urls_dedup.jsonl"),
        os.path.join(base, "bridge_val", "bridge_images"),
    )


if __name__ == "__main__":
    main()
