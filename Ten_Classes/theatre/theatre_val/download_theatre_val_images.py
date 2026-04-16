import json
import os
import random
import time
import urllib.request

JSONL_PATH = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\theatre\theatre_val\30_theatre_val_image_urls.jsonl"
OUT_DIR = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\theatre\theatre_val\theatre_images"


def load_items(path):
    items = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            image_id = obj.get("image_id")
            image_url = obj.get("image_url")
            if image_id and image_url:
                items.append((image_id, image_url))
    return items


def download_one(url, out_path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(out_path, "wb") as f:
        f.write(data)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    items = load_items(JSONL_PATH)
    total = len(items)
    print(f"Total IDs: {total}")

    ok = skip = fail = 0
    for idx, (image_id, image_url) in enumerate(items, 1):
        out_name = f"{image_id}.jpg"
        out_path = os.path.join(OUT_DIR, out_name)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            skip += 1
            print(f"[{idx}/{total}] SKIP {out_name}")
        else:
            try:
                download_one(image_url, out_path)
                ok += 1
                print(f"[{idx}/{total}] OK   {out_name}")
            except Exception as e:
                fail += 1
                print(f"[{idx}/{total}] FAIL {out_name} ({e})")

        sleep_s = random.randint(1, 10)
        print(f"           sleep {sleep_s}s")
        time.sleep(sleep_s)

    print("\n===== Finished =====")
    print(f"Downloaded: {ok}")
    print(f"Skipped   : {skip}")
    print(f"Failed    : {fail}")
    print(f"Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
