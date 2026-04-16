import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"e:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Reasonvqa")
TRAIN_DIR = ROOT / "Train"


def split_train(path: Path):
    counts = Counter()
    source_by_qid = {}
    outputs = {}
    output_counts = defaultdict(int)

    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)

            src = str(obj.get("source"))
            qid = int(obj["question_id"])
            counts[src] += 1
            source_by_qid[qid] = src

            folder = TRAIN_DIR / src
            folder.mkdir(parents=True, exist_ok=True)
            out_name = f"{src.lower()}_train.jsonl"
            out_path = folder / out_name

            if src not in outputs:
                outputs[src] = out_path.open("w", encoding="utf-8")

            outputs[src].write(raw + "\n")
            output_counts[src] += 1
            if idx % 200000 == 0:
                print(f"[{path.name}] processed={idx}", flush=True)

    for fp in outputs.values():
        fp.close()

    return counts, output_counts, source_by_qid


def split_train_ann(path: Path, source_by_qid):
    counts = Counter()
    unknown_qid = 0
    outputs = {}
    output_counts = defaultdict(int)

    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            qid = int(obj["question_id"])
            src = source_by_qid.get(qid)
            if src is None:
                unknown_qid += 1
                continue

            counts[src] += 1
            folder = TRAIN_DIR / src
            folder.mkdir(parents=True, exist_ok=True)
            out_name = f"{src.lower()}_train_ann.jsonl"
            out_path = folder / out_name

            if src not in outputs:
                outputs[src] = out_path.open("w", encoding="utf-8")

            outputs[src].write(raw + "\n")
            output_counts[src] += 1
            if idx % 200000 == 0:
                print(f"[{path.name}] processed={idx}", flush=True)

    for fp in outputs.values():
        fp.close()

    return counts, output_counts, unknown_qid


def main():
    train_path = ROOT / "train.jsonl"
    ann_path = ROOT / "train_ann.jsonl"
    if not train_path.exists() or not ann_path.exists():
        raise FileNotFoundError("Missing train.jsonl or train_ann.jsonl")

    none_dir = TRAIN_DIR / "None"
    if none_dir.exists():
        shutil.rmtree(none_dir)

    train_counts, train_written, source_by_qid = split_train(train_path)
    print(f"[{train_path.name}] source_counts={dict(train_counts)}")
    print(f"[{train_path.name}] written_counts={dict(train_written)}")
    if dict(train_counts) != dict(train_written):
        raise RuntimeError("Count mismatch for train.jsonl")

    ann_counts, ann_written, unknown_qid = split_train_ann(ann_path, source_by_qid)
    print(f"[{ann_path.name}] unknown_qid={unknown_qid}")
    print(f"[{ann_path.name}] source_counts={dict(ann_counts)}")
    print(f"[{ann_path.name}] written_counts={dict(ann_written)}")
    if unknown_qid != 0:
        raise RuntimeError("Found train_ann rows without matching question_id in train.jsonl")
    if dict(ann_counts) != dict(ann_written):
        raise RuntimeError("Count mismatch for train_ann.jsonl")

    print("DONE")


if __name__ == "__main__":
    main()
