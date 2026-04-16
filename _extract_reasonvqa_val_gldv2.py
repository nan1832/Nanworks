import json
from pathlib import Path

ROOT = Path(r"e:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Reasonvqa")
VAL_DIR = ROOT / "Val" / "GLDv2"

VAL_JSONL = ROOT / "val.jsonl"
VAL_ANN_JSONL = ROOT / "val_ann.jsonl"


def main():
    if not VAL_JSONL.exists() or not VAL_ANN_JSONL.exists():
        raise FileNotFoundError("Missing val.jsonl or val_ann.jsonl under downloads/Reasonvqa")

    VAL_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 读取 val.jsonl，筛选 source==GLDv2；建立 question_id -> keep 标记
    keep_qids = set()
    total_val = 0
    gld_val = 0
    out_val = VAL_DIR / "gldv2_val.jsonl"
    with VAL_JSONL.open("r", encoding="utf-8") as fin, out_val.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            total_val += 1
            obj = json.loads(line)
            if str(obj.get("source")) == "GLDv2":
                fout.write(line + "\n")
                gld_val += 1
                qid = int(obj["question_id"])
                keep_qids.add(qid)

    # 2) 读取 val_ann.jsonl，按 question_id 过滤
    total_ann = 0
    gld_ann = 0
    out_ann = VAL_DIR / "gldv2_val_ann.jsonl"
    with VAL_ANN_JSONL.open("r", encoding="utf-8") as fin, out_ann.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            total_ann += 1
            obj = json.loads(line)
            qid = int(obj["question_id"])
            if qid in keep_qids:
                fout.write(line + "\n")
                gld_ann += 1

    print(f"[val.jsonl] total={total_val} GLDv2={gld_val}")
    print(f"[val_ann.jsonl] total={total_ann} GLDv2={gld_ann} (matched by question_id)")
    print(f"Written:\n  {out_val}\n  {out_ann}")


if __name__ == "__main__":
    main()
