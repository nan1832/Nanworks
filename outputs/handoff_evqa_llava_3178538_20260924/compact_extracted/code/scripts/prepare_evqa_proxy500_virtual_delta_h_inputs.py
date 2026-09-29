import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert E-VQA proxy500 JSON into request-only inputs for virtual-delta-h LGA."
    )
    parser.add_argument("--evqa-path", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-samples", type=int, default=500)
    args = parser.parse_args()

    evqa_path = Path(args.evqa_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with evqa_path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    selected = rows[: args.max_samples]
    bridge_rows = []
    old_rows = []
    missing = []

    for idx, row in enumerate(selected):
        image = str(row.get("image") or "").strip()
        src = str(row.get("src") or "").strip()
        alt = str(row.get("alt") or "").strip()
        pred = str(row.get("pred") or "").strip()
        if not image or not src or not alt or not pred:
            missing.append(
                {
                    "idx": idx,
                    "has_image": bool(image),
                    "has_src": bool(src),
                    "has_alt": bool(alt),
                    "has_pred": bool(pred),
                }
            )
            continue

        image_id = Path(image).stem
        case_id = str(row.get("case_id") or row.get("id") or f"evqa_proxy500_{idx:04d}")
        bridge_rows.append(
            {
                "case_id": case_id,
                "entity_name": str(row.get("entity_name") or alt),
                "request": {
                    "image": image,
                    "prompt": src,
                    "target_new": alt,
                },
            }
        )
        old_rows.append(
            {
                "image_id": image_id,
                "question": src,
                "answer": pred,
                "pred": pred,
                "case_id": case_id,
            }
        )

    bridge_path = out_dir / "evqa_proxy500_request_only_bridge_format.json"
    old_path = out_dir / "evqa_proxy500_old_answers_from_pred.jsonl"
    report_path = out_dir / "prepare_evqa_proxy500_virtual_delta_h_inputs_report.json"

    bridge_path.write_text(json.dumps(bridge_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with old_path.open("w", encoding="utf-8") as f:
        for row in old_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "evqa_path": str(evqa_path),
        "max_samples": args.max_samples,
        "input_rows": len(rows),
        "selected_rows": len(selected),
        "bridge_rows": len(bridge_rows),
        "old_answer_rows": len(old_rows),
        "new_knowledge_field": "alt",
        "old_knowledge_field": "pred",
        "bridge_data_path": str(bridge_path),
        "old_answers_path": str(old_path),
        "missing_rows": missing,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if missing:
        raise SystemExit(f"Found {len(missing)} rows missing required fields; see {report_path}")


if __name__ == "__main__":
    main()
