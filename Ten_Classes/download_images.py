"""
Download images for a given class from its *_train or *_val jsonl.
Each unique image_id is downloaded once, saved as image_name in the target dir.

Strategy to avoid Wikimedia 429 rate-limit:
  1. Convert original commons URLs to thumbnail URLs (800px) - much less restricted.
  2. Polite delay (2-4s) between requests with jitter.
  3. Exponential back-off on 429 (up to MAX_RETRIES attempts).
  4. Rotate User-Agent strings.

Usage:
  python download_images.py --jsonl <path_to_jsonl> --out <output_dir>

Example:
  python download_images.py --jsonl bridge/bridge_train/30_bridge_train.jsonl --out bridge/bridge_train/bridge_images
"""

import argparse
import json
import os
import random
import re
import time
import urllib.request
import urllib.error

BASE_DELAY   = 2.5   # seconds between requests
MAX_RETRIES  = 6
BACKOFF_BASE = 4.0   # on 429: wait BACKOFF_BASE^attempt seconds

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (compatible; research-bot/1.0; +mailto:example@example.com)",
]


def to_thumbnail_url(url, width=800):
    """
    Convert a Wikimedia commons direct URL to its thumbnail URL.
    e.g. https://upload.wikimedia.org/wikipedia/commons/a/ab/Foo.jpg
      -> https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Foo.jpg/800px-Foo.jpg
    Returns original url unchanged if pattern doesn't match.
    """
    m = re.match(
        r"(https://upload\.wikimedia\.org/wikipedia/commons/)([0-9a-f]/[0-9a-f]{2}/)(.*)",
        url,
    )
    if m:
        prefix, hash_path, filename = m.groups()
        return f"{prefix}thumb/{hash_path}{filename}/{width}px-{filename}"
    return url


def download_one(url, dest, attempt_thumb_first=True):
    """Try thumbnail URL first, fall back to original."""
    urls_to_try = []
    if attempt_thumb_first:
        thumb = to_thumbnail_url(url)
        if thumb != url:
            urls_to_try.append(("thumb", thumb))
    urls_to_try.append(("original", url))

    for label, u in urls_to_try:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    u,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(dest, "wb") as f:
                    f.write(data)
                return True, label
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = BACKOFF_BASE ** attempt + random.uniform(0, 3)
                    print(f"    429 rate-limit ({label}), retry {attempt}/{MAX_RETRIES} in {wait:.1f}s ...")
                    time.sleep(wait)
                elif e.code in (403, 404):
                    # No point retrying
                    break
                else:
                    print(f"    HTTP {e.code} ({label}): {e}")
                    break
            except Exception as e:
                print(f"    Error ({label}) attempt {attempt}: {e}")
                time.sleep(BACKOFF_BASE)
                break
    return False, None


def download_images(jsonl_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    # Collect unique (image_name, image_url) pairs
    seen = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            img_name = obj.get("image_name", "")
            img_url  = obj.get("image_url", "")
            if img_name and img_url and img_name not in seen:
                seen[img_name] = img_url

    total = len(seen)
    print(f"Found {total} unique images to download → {out_dir}")

    ok = skip = fail = 0
    for i, (name, url) in enumerate(seen.items(), 1):
        dest = os.path.join(out_dir, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            skip += 1
            print(f"[{i}/{total}] SKIP: {name}")
            continue

        success, via = download_one(url, dest)
        if success:
            ok += 1
            print(f"[{i}/{total}] OK ({via}): {name}")
        else:
            fail += 1
            print(f"[{i}/{total}] FAIL: {name}")

        time.sleep(BASE_DELAY + random.uniform(0, 1.5))

    print(f"\n===== Done =====")
    print(f"  Downloaded : {ok}")
    print(f"  Skipped    : {skip}")
    print(f"  Failed     : {fail}")
    print(f"  Output dir : {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--out",   required=True)
    args = parser.parse_args()
    download_images(args.jsonl, args.out)
