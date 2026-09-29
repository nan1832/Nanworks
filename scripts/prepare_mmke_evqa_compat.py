import argparse
import json
from pathlib import Path


REQUIRED_KEYS = [
    "src",
    "pred",
    "rephrase",
    "alt",
    "image",
    "image_rephrase",
    "loc",
    "loc_ans",
    "m_loc",
    "m_loc_q",
    "m_loc_a",
]


def resolve_relative_image(mmke_root, rel_path):
    if not rel_path:
        return rel_path, False
    rel_path = str(rel_path)
    if (mmke_root / "data_image" / rel_path).exists():
        return rel_path, True
    if rel_path.startswith("locality/"):
        entity_rel = f"entity/{Path(rel_path).name}"
        if (mmke_root / "data_image" / entity_rel).exists():
            return entity_rel, True
    return rel_path, False


def convert_split(mmke_root, task, split, out_json):
    src_json = mmke_root / "data_json" / f"{task}_{split}.json"
    rows = json.loads(src_json.read_text(encoding="utf-8"))
    out_rows = []
    missing_images = []
    remapped_m_loc = 0

    for index, row in enumerate(rows):
        new_row = {}
        for key in REQUIRED_KEYS:
            new_row[key] = row.get(key, "")

        for key in ["image", "image_rephrase", "m_loc"]:
            rel, ok = resolve_relative_image(mmke_root, new_row.get(key))
            if key == "m_loc" and rel != new_row.get(key):
                remapped_m_loc += 1
            new_row[key] = rel
            if not ok:
                missing_images.append({"index": index, "field": key, "path": rel})

        new_row["_mmke_task"] = task
        new_row["_mmke_split"] = split
        new_row["_mmke_index"] = index
        new_row["_knowledge_type"] = row.get("knowledge_type", "")
        new_row["_type_self"] = row.get("type_self", "")
        out_rows.append(new_row)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "source": str(src_json),
        "output": str(out_json),
        "task": task,
        "split": split,
        "samples": len(out_rows),
        "remapped_m_loc": remapped_m_loc,
        "missing_images": missing_images,
    }
    report_path = out_json.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing_images:
        raise SystemExit(f"missing images in {out_json}: {len(missing_images)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mmke-root", type=Path, required=True)
    parser.add_argument("--task", choices=["visual", "entity"], required=True)
    parser.add_argument("--split", choices=["train", "eval"], required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    convert_split(args.mmke_root, args.task, args.split, args.out_json)


if __name__ == "__main__":
    main()
