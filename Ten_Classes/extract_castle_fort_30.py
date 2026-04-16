"""
Extract 30 castle_fort entities that appear in BOTH train and val sets.
Outputs 4 files:
  castle_fort/castle_fort_train/30_castle_fort_train.jsonl
  castle_fort/castle_fort_train/30_castle_fort_train_ann.jsonl
  castle_fort/castle_fort_val/30_castle_fort_val.jsonl
  castle_fort/castle_fort_val/30_castle_fort_val_ann.jsonl

Usage:
  python extract_castle_fort_30.py
"""

import json
import os
import random

random.seed(42)

TARGET_CLASS = "castle / fort"
SAFE_NAME = "castle_fort"
N_ENTITIES = 30

TRAIN_ANN = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Reasonvqa\Train\GLDv2\gldv2_train_ann_classified.jsonl"
TRAIN_QA  = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Reasonvqa\Train\GLDv2\gldv2_train.jsonl"
VAL_ANN   = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Reasonvqa\Val\GLDv2\gldv2_val_ann_classified.jsonl"
VAL_QA    = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Reasonvqa\Val\GLDv2\gldv2_val.jsonl"

OUT_TRAIN_DIR = os.path.join(os.path.dirname(__file__), "castle_fort", "castle_fort_train")
OUT_VAL_DIR   = os.path.join(os.path.dirname(__file__), "castle_fort", "castle_fort_val")


def collect_entity_ids(ann_path, target_class):
    entity_ids = set()
    with open(ann_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("coarse_class") == target_class:
                entity_ids.add(obj["entity_id"])
    return entity_ids


def collect_qids_for_entities(ann_path, target_class, entity_ids):
    qid_to_line = {}
    with open(ann_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("coarse_class") == target_class and obj["entity_id"] in entity_ids:
                qid_to_line[obj["question_id"]] = line
    return qid_to_line


def extract_qa_by_qids(qa_path, target_qids):
    lines = []
    with open(qa_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj["question_id"] in target_qids:
                lines.append(line)
    return lines


def main():
    print(f"[1/6] Collecting {TARGET_CLASS} entity_ids from train...")
    train_entities = collect_entity_ids(TRAIN_ANN, TARGET_CLASS)
    print(f"       Found {len(train_entities)} train entities")

    print(f"[2/6] Collecting {TARGET_CLASS} entity_ids from val...")
    val_entities = collect_entity_ids(VAL_ANN, TARGET_CLASS)
    print(f"       Found {len(val_entities)} val entities")

    common = sorted(train_entities & val_entities)
    print(f"       Common entities: {len(common)}")

    if len(common) < N_ENTITIES:
        print(f"WARNING: Only {len(common)} common entities, less than {N_ENTITIES}. Using all.")
        selected = common
    else:
        selected = sorted(random.sample(common, N_ENTITIES))
    selected_set = set(selected)
    print(f"       Selected {len(selected)} entities: {selected[:5]}...")

    print(f"[3/6] Extracting train ann lines...")
    train_ann_qid_to_line = collect_qids_for_entities(TRAIN_ANN, TARGET_CLASS, selected_set)
    train_qids = set(train_ann_qid_to_line.keys())
    print(f"       Found {len(train_qids)} train ann lines")

    print(f"[4/6] Extracting train QA lines...")
    train_qa_lines = extract_qa_by_qids(TRAIN_QA, train_qids)
    print(f"       Found {len(train_qa_lines)} train QA lines")

    print(f"[5/6] Extracting val ann lines...")
    val_ann_qid_to_line = collect_qids_for_entities(VAL_ANN, TARGET_CLASS, selected_set)
    val_qids = set(val_ann_qid_to_line.keys())
    print(f"       Found {len(val_qids)} val ann lines")

    print(f"[6/6] Extracting val QA lines...")
    val_qa_lines = extract_qa_by_qids(VAL_QA, val_qids)
    print(f"       Found {len(val_qa_lines)} val QA lines")

    os.makedirs(OUT_TRAIN_DIR, exist_ok=True)
    os.makedirs(OUT_VAL_DIR, exist_ok=True)

    with open(os.path.join(OUT_TRAIN_DIR, f"30_{SAFE_NAME}_train.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(train_qa_lines) + "\n")

    with open(os.path.join(OUT_TRAIN_DIR, f"30_{SAFE_NAME}_train_ann.jsonl"), "w", encoding="utf-8") as f:
        for qid in sorted(train_ann_qid_to_line.keys()):
            f.write(train_ann_qid_to_line[qid] + "\n")

    with open(os.path.join(OUT_VAL_DIR, f"30_{SAFE_NAME}_val.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(val_qa_lines) + "\n")

    with open(os.path.join(OUT_VAL_DIR, f"30_{SAFE_NAME}_val_ann.jsonl"), "w", encoding="utf-8") as f:
        for qid in sorted(val_ann_qid_to_line.keys()):
            f.write(val_ann_qid_to_line[qid] + "\n")

    train_entities_in_output = set()
    for qid, line in train_ann_qid_to_line.items():
        obj = json.loads(line)
        train_entities_in_output.add(obj["entity_id"])
    val_entities_in_output = set()
    for qid, line in val_ann_qid_to_line.items():
        obj = json.loads(line)
        val_entities_in_output.add(obj["entity_id"])

    print(f"\n========== Summary ==========")
    print(f"  Class          : {TARGET_CLASS}")
    print(f"  Selected entities: {len(selected)}")
    print(f"  Train: {len(train_qa_lines)} QA lines, {len(train_ann_qid_to_line)} ann lines, {len(train_entities_in_output)} entities")
    print(f"  Val  : {len(val_qa_lines)} QA lines, {len(val_ann_qid_to_line)} ann lines, {len(val_entities_in_output)} entities")
    print(f"  Output train dir: {OUT_TRAIN_DIR}")
    print(f"  Output val dir  : {OUT_VAL_DIR}")
    print("=============================")

    with open(os.path.join(os.path.dirname(__file__), "castle_fort", "selected_entities.json"), "w", encoding="utf-8") as f:
        entity_info = []
        for eid in selected:
            entity_info.append({"entity_id": eid})
        name_map = {}
        for line in train_ann_qid_to_line.values():
            obj = json.loads(line)
            name_map[obj["entity_id"]] = obj["entity_name"]
        for item in entity_info:
            item["entity_name"] = name_map.get(item["entity_id"], "")
        json.dump(entity_info, f, indent=2, ensure_ascii=False)
    print(f"  Entity list saved to: castle_fort/selected_entities.json")


if __name__ == "__main__":
    main()
