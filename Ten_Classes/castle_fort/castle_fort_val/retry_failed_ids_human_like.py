import json
import os
import random
import time
import urllib.error
import urllib.request

BASE_DIR = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\Ten_Classes\castle_fort\castle_fort_val"
FAILED_JSONL = os.path.join(BASE_DIR, "failed_ids.jsonl")
OUT_DIR = os.path.join(BASE_DIR, "castle_fort_images")

# Human-like pacing
MIN_WAIT = 20
MAX_WAIT = 60
MAX_RETRIES = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def load_failed_items(path):
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


def download_with_retry(image_id, image_url, out_path):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                image_url,
                headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            with open(out_path, "wb") as f:
                f.write(data)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                backoff = random.randint(90, 240)
                print(f"    429 for {image_id}, retry {attempt}/{MAX_RETRIES}, backoff {backoff}s")
                time.sleep(backoff)
            elif e.code == 404:
                print(f"    404 for {image_id}, stop retry")
                return False
            else:
                print(f"    HTTP {e.code} for {image_id}, stop retry")
                return False
        except Exception as e:
            backoff = random.randint(60, 150)
            print(f"    Error for {image_id} ({e}), retry {attempt}/{MAX_RETRIES}, backoff {backoff}s")
            time.sleep(backoff)
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    items = load_failed_items(FAILED_JSONL)
    print(f"Retry target IDs: {len(items)}")

    ok = skip = fail = 0
    for idx, (image_id, image_url) in enumerate(items, 1):
        out_path = os.path.join(OUT_DIR, f"{image_id}.jpg")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            skip += 1
            print(f"[{idx}/{len(items)}] SKIP {image_id}.jpg")
        else:
            success = download_with_retry(image_id, image_url, out_path)
            if success:
                ok += 1
                print(f"[{idx}/{len(items)}] OK   {image_id}.jpg")
            else:
                fail += 1
                print(f"[{idx}/{len(items)}] FAIL {image_id}.jpg")

        wait_s = random.randint(MIN_WAIT, MAX_WAIT)
        print(f"           sleep {wait_s}s")
        time.sleep(wait_s)

    print("\n===== Human-like Retry Finished =====")
    print(f"Recovered: {ok}")
    print(f"Skipped  : {skip}")
    print(f"StillFail: {fail}")
    print(f"Output   : {OUT_DIR}")


if __name__ == "__main__":
    main()
