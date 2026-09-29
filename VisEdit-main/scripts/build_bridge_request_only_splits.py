import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def to_request_only(rows):
    out = []
    for row in rows:
        item = {
            "case_id": row.get("case_id"),
            "entity_id": row.get("entity_id"),
            "entity_name": row.get("entity_name"),
            "request": copy.deepcopy(row["request"]),
            "generality": {"text_rephrase": [], "image_rephrase": []},
            "locality": {"text_loc": [], "image_loc": []},
            "portability": {"1hop": [], "2hop": []},
        }
        out.append(item)
    return out


def write_manifest(path: Path, source_path: Path, output_paths):
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": str(source_path),
        "source_sha256": sha256_file(source_path),
        "outputs": [
            {
                "path": str(p),
                "sha256": sha256_file(p),
                "sample_count": len(load_json(p)),
            }
            for p in output_paths
        ],
    }
    dump_json(path, payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-source", required=True)
    parser.add_argument("--val-source", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    train_source = Path(args.train_source)
    val_source = Path(args.val_source)
    output_root = Path(args.output_root)

    train_rows = load_json(train_source)
    val_rows = load_json(val_source)

    train_request = output_root / "train" / "edit_30_bridge_train_request_only.json"
    val_request = output_root / "val" / "edit_30_bridge_val_request_only.json"
    val_full = output_root / "val" / "edit_30_bridge_val_full_metrics.json"

    dump_json(train_request, to_request_only(train_rows))
    dump_json(val_request, to_request_only(val_rows))
    dump_json(val_full, val_rows)

    write_manifest(output_root / "train" / "manifest.json", train_source, [train_request])
    write_manifest(output_root / "val" / "manifest.json", val_source, [val_request, val_full])

    print(f"Wrote {train_request} ({len(train_rows)} samples)")
    print(f"Wrote {val_request} ({len(val_rows)} samples)")
    print(f"Wrote {val_full} ({len(val_rows)} samples)")


if __name__ == "__main__":
    main()

