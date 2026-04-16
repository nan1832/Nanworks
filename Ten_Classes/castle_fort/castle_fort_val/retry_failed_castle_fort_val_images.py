import json
import os
import random
import time
import urllib.request
import urllib.error

JSONL_PATH = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\castle_fort\castle_fort_val\30_castle_fort_val_image_urls.jsonl"
OUT_DIR = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\castle_fort\castle_fort_val\castle_fort_images"

# Longer wait window as requested
INTERVAL_MIN = 20
INTERVAL_MAX = 60

# Retry settings for failed IDs
MAX_RETRIES_PER_ID = 4


def load_items(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
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


def download_once(url, dest):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_items = load_items(JSONL_PATH)

    # Retry only missing files (= previous failed IDs)
    todo = []
    for image_id, image_url in all_items:
        out_path = os.path.join(OUT_DIR, f"{image_id}.jpg")
        if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
            todo.append((image_id, image_url))

    print(f"Total in jsonl: {len(all_items)}")
    print(f"Retry missing IDs only: {len(todo)}")

    ok = fail = 0
    for idx, (image_id, image_url) in enumerate(todo, 1):
        out_name = f"{image_id}.jpg"
        out_path = os.path.join(OUT_DIR, out_name)
        success = False

        for attempt in range(1, MAX_RETRIES_PER_ID + 1):
            try:
                download_once(image_url, out_path)
                success = True
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    backoff = random.randint(60, 180)
                    print(
                        f"[{idx}/{len(todo)}] 429 {out_name}, "
                        f"attempt {attempt}/{MAX_RETRIES_PER_ID}, backoff {backoff}s"
                    )
                    time.sleep(backoff)
                else:
                    print(
                        f"[{idx}/{len(todo)}] HTTP {e.code} {out_name}, "
                        f"attempt {attempt}/{MAX_RETRIES_PER_ID}"
                    )
                    break
            except Exception as e:
                print(
                    f"[{idx}/{len(todo)}] ERROR {out_name}, "
                    f"attempt {attempt}/{MAX_RETRIES_PER_ID}: {e}"
                )
                time.sleep(random.randint(30, 90))

        if success:
            ok += 1
            print(f"[{idx}/{len(todo)}] OK   {out_name}")
        else:
            fail += 1
            print(f"[{idx}/{len(todo)}] FAIL {out_name}")

        sleep_s = random.randint(INTERVAL_MIN, INTERVAL_MAX)
        print(f"           interval sleep {sleep_s}s")
        time.sleep(sleep_s)

    print("\n===== Retry Finished =====")
    print(f"Recovered: {ok}")
    print(f"Still fail: {fail}")
    print(f"Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
