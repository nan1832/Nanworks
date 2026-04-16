import json
import os

BASE_DIR = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\castle_fort\castle_fort_val"
INPUT_JSONL = os.path.join(BASE_DIR, "30_castle_fort_val_image_urls.jsonl")
IMAGES_DIR = os.path.join(BASE_DIR, "castle_fort_images")
OUTPUT_JSONL = os.path.join(BASE_DIR, "failed_ids.jsonl")


def main():
    expected = []
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            image_id = obj.get("image_id")
            image_url = obj.get("image_url")
            if image_id and image_url:
                expected.append((image_id, image_url))

    existing = set()
    if os.path.isdir(IMAGES_DIR):
        for name in os.listdir(IMAGES_DIR):
            path = os.path.join(IMAGES_DIR, name)
            if not os.path.isfile(path):
                continue
            if not name.lower().endswith(".jpg"):
                continue
            stem = os.path.splitext(name)[0]
            if os.path.getsize(path) > 0:
                existing.add(stem)

    failed = [(iid, url) for iid, url in expected if iid not in existing]

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for iid, url in failed:
            f.write(json.dumps({"image_id": iid, "image_url": url}, ensure_ascii=False) + "\n")

    print(f"Expected IDs: {len(expected)}")
    print(f"Downloaded: {len(existing)}")
    print(f"Failed IDs: {len(failed)}")
    print(f"Output: {OUTPUT_JSONL}")


if __name__ == "__main__":
    main()
