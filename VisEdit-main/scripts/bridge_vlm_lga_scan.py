import argparse
import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


ANSWER_STUB = " The answer is:"
EPS = 1e-8


@dataclass
class BridgeLGASample:
    case_id: str
    entity_name: str
    image_id: str
    prompt: str
    target_new: str
    old_answer: Optional[str]
    image_path: str
    image: Any = None


def parse_layers(raw: str) -> List[int]:
    layers: List[int] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            start_s, end_s = piece.split("-", 1)
            start, end = int(start_s), int(end_s)
            if end < start:
                raise ValueError(f"Descending layer range is not allowed: {piece}")
            layers.extend(range(start, end + 1))
        else:
            layers.append(int(piece))
    unique = sorted(set(layers))
    if not unique:
        raise ValueError("Expected at least one candidate layer")
    return unique


def chunked(items: Sequence[int], chunk_size: int) -> Iterable[List[int]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    for i in range(0, len(items), chunk_size):
        yield list(items[i : i + chunk_size])


def ensure_answer_stub(prompt: str) -> str:
    return prompt if prompt.endswith(ANSWER_STUB) else f"{prompt}{ANSWER_STUB}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def image_id_from_path(path: str) -> str:
    return Path(path).stem


def resolve_bridge_image_path(rel_path: str, bridge_root: str) -> str:
    img_path_map = {
        "train/images": "bridge_train/bridge_images",
        "val/images": "bridge_val/bridge_images",
    }
    remapped = rel_path
    for src_prefix, dst_prefix in img_path_map.items():
        if remapped.startswith(src_prefix):
            remapped = dst_prefix + remapped[len(src_prefix) :]
            break
    return os.path.join(bridge_root, remapped)


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def choose_old_answer(records: List[Dict[str, Any]], prompt: str) -> Dict[str, Any]:
    if not records:
        raise ValueError("records must not be empty")
    prompt_norm = normalize_text(prompt.replace(ANSWER_STUB, ""))
    best = records[0]
    best_score = -1.0
    for record in records:
        question = normalize_text(record.get("question", ""))
        score = 1.0 if question == prompt_norm else SequenceMatcher(None, prompt_norm, question).ratio()
        if score > best_score:
            best = record
            best_score = score
    return best


def load_old_answers(path: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in read_jsonl(path):
        image_id = str(row.get("image_id") or "").strip()
        answer = str(row.get("answer") or row.get("pred") or "").strip()
        if not image_id or not answer or answer == "<empty>":
            continue
        grouped.setdefault(image_id, []).append(row)
    duplicate_image_ids = sorted([key for key, values in grouped.items() if len(values) > 1])
    return grouped, duplicate_image_ids


def load_bridge_samples(
    data_path: str,
    bridge_root: str,
    old_answers_path: Optional[str],
    max_samples: Optional[int] = None,
    allow_missing_old_answers: bool = False,
) -> Tuple[List[BridgeLGASample], Dict[str, Any]]:
    from PIL import Image

    with open(data_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    old_grouped: Dict[str, List[Dict[str, Any]]] = {}
    duplicate_image_ids: List[str] = []
    if old_answers_path and os.path.exists(old_answers_path):
        old_grouped, duplicate_image_ids = load_old_answers(old_answers_path)

    samples: List[BridgeLGASample] = []
    missing_cases: List[Dict[str, str]] = []
    selected_items = raw_items[:max_samples] if max_samples is not None else raw_items
    for idx, item in enumerate(selected_items):
        if max_samples is not None and idx >= max_samples:
            break
        req = item["request"]
        rel_image = req["image"]
        image_id = image_id_from_path(rel_image)
        prompt = ensure_answer_stub(req["prompt"])
        old_answer: Optional[str] = None
        if image_id in old_grouped:
            old_answer = str(choose_old_answer(old_grouped[image_id], req["prompt"]).get("answer", "")).strip()
        else:
            missing_cases.append({"case_id": str(item.get("case_id", f"bridge_{idx}")), "image_id": image_id})
        if not old_answer and not allow_missing_old_answers:
            continue
        image_path = resolve_bridge_image_path(rel_image, bridge_root)
        samples.append(
            BridgeLGASample(
                case_id=str(item.get("case_id", f"bridge_{idx}")),
                entity_name=str(item.get("entity_name", req["target_new"])),
                image_id=image_id,
                prompt=prompt,
                target_new=str(req["target_new"]),
                old_answer=old_answer,
                image_path=image_path,
                image=Image.open(image_path).convert("RGB"),
            )
        )

    report = {
        "old_answer_source": old_answers_path,
        "total_cases": len(selected_items),
        "mapped_cases": sum(1 for sample in samples if sample.old_answer),
        "missing_cases": missing_cases,
        "duplicate_image_ids": duplicate_image_ids,
    }
    if missing_cases and not allow_missing_old_answers:
        raise RuntimeError(f"Missing old answers for {len(missing_cases)} cases. See mapping report.")
    return samples, report


def default_module_path(model_name: str, layer: int, module_kind: str) -> str:
    model_name_l = model_name.lower()
    module_kind = module_kind.lower()
    if "llava" in model_name_l:
        base = f"language_model.model.layers.{layer}"
        if module_kind == "mlp":
            return f"{base}.mlp"
        if module_kind in {"attn", "self_attn"}:
            return f"{base}.self_attn"
        if module_kind == "layer":
            return base
    if "blip2" in model_name_l:
        base = f"language_model.model.decoder.layers.{layer}"
        if module_kind == "mlp":
            return f"{base}.fc2"
        if module_kind in {"attn", "self_attn"}:
            return f"{base}.self_attn"
        if module_kind == "layer":
            return base
    raise ValueError(f"Unsupported model/module_kind pair: {model_name}, {module_kind}")


def set_module_trainable(module: Any, trainable: bool) -> None:
    for param in module.parameters():
        param.requires_grad_(trainable)


def zero_module_grads(modules: Dict[int, Any]) -> None:
    for module in modules.values():
        for param in module.parameters():
            param.grad = None


def gradient_similarity(old_values: Sequence[float], new_values: Sequence[float], eps: float = EPS) -> Dict[str, float]:
    if len(old_values) != len(new_values):
        raise ValueError("old_values and new_values must have the same length")
    dot = sum(float(a) * float(b) for a, b in zip(old_values, new_values))
    old_norm = math.sqrt(sum(float(a) * float(a) for a in old_values))
    new_norm = math.sqrt(sum(float(b) * float(b) for b in new_values))
    joint = old_norm * new_norm
    cos = dot / (joint + eps)
    return {
        "dot": dot,
        "old_norm": old_norm,
        "new_norm": new_norm,
        "joint_grad_norm": joint,
        "cos": cos,
    }


def collect_old_grads(modules: Dict[int, Any]) -> Dict[int, Dict[str, Any]]:
    import torch

    old: Dict[int, Dict[str, Any]] = {}
    for layer, module in modules.items():
        grads = []
        old_sq = 0.0
        for param in module.parameters():
            if param.grad is None:
                continue
            grad = param.grad.detach().float().cpu().contiguous()
            old_sq += float(torch.sum(grad * grad).item())
            grads.append(grad)
        old[layer] = {"grads": grads, "old_sq": old_sq}
    return old


def compare_new_grads(modules: Dict[int, Any], old: Dict[int, Dict[str, Any]], eps: float = EPS) -> Dict[int, Dict[str, float]]:
    import torch

    stats: Dict[int, Dict[str, float]] = {}
    for layer, module in modules.items():
        dot = 0.0
        new_sq = 0.0
        old_grads = old[layer]["grads"]
        grad_idx = 0
        for param in module.parameters():
            if param.grad is None:
                continue
            new_grad = param.grad.detach().float().cpu().contiguous()
            old_grad = old_grads[grad_idx]
            dot += float(torch.sum(old_grad * new_grad).item())
            new_sq += float(torch.sum(new_grad * new_grad).item())
            grad_idx += 1
        old_norm = math.sqrt(float(old[layer]["old_sq"]))
        new_norm = math.sqrt(float(new_sq))
        joint = old_norm * new_norm
        stats[layer] = {
            "dot": dot,
            "old_norm": old_norm,
            "new_norm": new_norm,
            "joint_grad_norm": joint,
            "cos": dot / (joint + eps),
        }
    return stats


def detach_llm_inputs(llm_inpt: Dict[str, Any]) -> Dict[str, Any]:
    detached = {}
    for key, value in llm_inpt.items():
        detached[key] = value.detach() if hasattr(value, "detach") else value
    return detached


def compute_target_loss(vllm: Any, sample: BridgeLGASample, target: str):
    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [sample.prompt],
        [sample.image],
        [target],
    )
    llm_inpt = detach_llm_inputs(llm_inpt)
    output = vllm.get_llm_outpt(llm_inpt, vt_range)
    return vllm.label_loss(output.logits, label_ids, label_masks, average=True)


def rank_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    joint_mean = sum(float(row["joint_grad_norm"]) for row in rows) / max(len(rows), 1)
    for row in rows:
        row["norm_ratio"] = float(row["joint_grad_norm"]) / (joint_mean + EPS)

    for key, rank_key in [
        ("S_lga_dot", "dot_rank"),
        ("S_lga_cos", "cos_rank"),
        ("joint_grad_norm", "norm_rank"),
    ]:
        ranked = sorted(rows, key=lambda row: float(row[key]), reverse=True)
        for rank, row in enumerate(ranked, 1):
            row[rank_key] = rank

    for row in rows:
        row["lga_selected_by_dot"] = row["dot_rank"] == 1
    return sorted(rows, key=lambda row: row["dot_rank"])


def summarize_rows(rows: List[Dict[str, Any]], topk: int) -> Dict[str, Any]:
    by_dot = sorted(rows, key=lambda row: row["dot_rank"])
    by_cos = sorted(rows, key=lambda row: row["cos_rank"])
    return {
        "main_score": "S_lga_dot",
        "diagnostic_scores": ["S_lga_cos", "old_grad_norm", "new_grad_norm", "joint_grad_norm", "norm_ratio"],
        "top_by_dot": {
            "top1": int(by_dot[0]["layer"]),
            "top3": [int(row["layer"]) for row in by_dot[: min(3, len(by_dot))]],
            "top5": [int(row["layer"]) for row in by_dot[: min(5, len(by_dot))]],
        },
        "top_by_cos": {
            "top1": int(by_cos[0]["layer"]),
            "top3": [int(row["layer"]) for row in by_cos[: min(3, len(by_cos))]],
            "top5": [int(row["layer"]) for row in by_cos[: min(5, len(by_cos))]],
        },
        "selected_golden_layer": {"by": "S_lga_dot", "top1": int(by_dot[0]["layer"])},
        "topk_rows": by_dot[:topk],
    }


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "layer",
        "module_kind",
        "module_path",
        "n_request",
        "S_lga_dot",
        "S_lga_cos",
        "old_grad_norm",
        "new_grad_norm",
        "joint_grad_norm",
        "norm_ratio",
        "dot_rank",
        "cos_rank",
        "norm_rank",
        "lga_selected_by_dot",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_summary_md(path: str, model_name: str, rows: List[Dict[str, Any]], topk: int) -> None:
    top_rows = sorted(rows, key=lambda row: row["dot_rank"])[:topk]
    lines = [
        f"# Bridge30 {model_name} Request-Only LGA Summary",
        "",
        "Main score: `S_lga_dot`",
        "",
        "| Dot Rank | Layer | S_lga_dot | S_lga_cos | Joint Norm | Norm Ratio | n_request |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in top_rows:
        lines.append(
            f"| {row['dot_rank']} | {row['layer']} | {row['S_lga_dot']:.6g} | "
            f"{row['S_lga_cos']:.6g} | {row['joint_grad_norm']:.6g} | "
            f"{row['norm_ratio']:.6g} | {row['n_request']} |"
        )
    lines.extend(
        [
            "",
            "Cosine, gradient norm, and norm ratio are diagnostic fields only.",
            "The selected LGA predicted golden layer is the layer with `dot_rank = 1`.",
            "",
        ]
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_old_answers(
    vllm: Any,
    samples: List[BridgeLGASample],
    model_name: str,
    output_path: str,
    max_new_tokens: int,
) -> None:
    import torch

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    rows = []
    seen_image_ids = set()
    if os.path.exists(output_path):
        for row in read_jsonl(output_path):
            answer = str(row.get("answer") or "").strip()
            image_id = str(row.get("image_id") or "").strip()
            if image_id and answer and answer != "<empty>":
                rows.append(row)
                seen_image_ids.add(image_id)
    for i, sample in enumerate(samples, 1):
        if sample.image_id in seen_image_ids:
            continue
        question = sample.prompt.replace(ANSWER_STUB, "")
        if "llava" in model_name.lower():
            prompt = f"USER: <image>\n{question}\nAnswer briefly with the bridge name only.\nASSISTANT:"
            inputs = vllm.processor(prompt, sample.image, return_tensors="pt").to(vllm.device)
            with torch.no_grad():
                generated = vllm.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            text = vllm.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
            if "ASSISTANT:" in text:
                text = text.split("ASSISTANT:", 1)[1].strip()
        else:
            text = ""
            blip2_prompts = [
                f"Question: {question} Answer briefly with the bridge name only. Answer:",
                f"{question} Answer:",
                question,
                "This bridge is called",
            ]
            for prompt in blip2_prompts:
                inputs = vllm.processor(sample.image, prompt, return_tensors="pt").to(vllm.device)
                with torch.no_grad():
                    generated = vllm.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
                candidate = vllm.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
                if candidate:
                    text = candidate
                    break
            if not text:
                text = "unknown"
        rows.append({"image_id": sample.image_id, "question": question, "answer": text})
        seen_image_ids.add(sample.image_id)
        print(f"[old-answer] {i}/{len(samples)} {sample.image_id}: {text}")
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Saved old answers: {output_path}")


def run_lga_scan(args: argparse.Namespace) -> None:
    import torch

    from utils import find_module, load_vllm_for_edit

    os.makedirs(args.output_dir, exist_ok=True)
    layers = parse_layers(args.layers)

    vllm = None
    provisional_samples, provisional_report = load_bridge_samples(
        args.data_path,
        args.bridge_root,
        old_answers_path=args.old_answers_path,
        max_samples=args.max_samples,
        allow_missing_old_answers=True,
    )
    if provisional_report["missing_cases"] and args.generate_old_answers_if_missing:
        missing_ids = {item["image_id"] for item in provisional_report["missing_cases"]}
        missing_samples = [sample for sample in provisional_samples if sample.image_id in missing_ids]
        vllm = load_vllm_for_edit(args.model_name, args.device)
        if args.torch_dtype == "float16":
            vllm.model.to(dtype=torch.float16)
        elif args.torch_dtype == "bfloat16":
            vllm.model.to(dtype=torch.bfloat16)
        generate_old_answers(vllm, missing_samples, args.model_name, args.old_answers_path, args.max_new_tokens)

    samples, mapping_report = load_bridge_samples(
        args.data_path,
        args.bridge_root,
        args.old_answers_path,
        max_samples=args.max_samples,
        allow_missing_old_answers=False,
    )
    if not samples:
        raise RuntimeError("No LGA samples loaded")

    with open(os.path.join(args.output_dir, "old_answer_mapping_report.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, ensure_ascii=False, indent=2)

    if vllm is None:
        vllm = load_vllm_for_edit(args.model_name, args.device)
        if args.torch_dtype == "float16":
            vllm.model.to(dtype=torch.float16)
        elif args.torch_dtype == "bfloat16":
            vllm.model.to(dtype=torch.bfloat16)

    vllm.model.eval()
    vllm.model.requires_grad_(False)

    accum: Dict[int, Dict[str, float]] = {
        layer: {
            "S_lga_dot": 0.0,
            "S_lga_cos": 0.0,
            "old_grad_norm": 0.0,
            "new_grad_norm": 0.0,
            "joint_grad_norm": 0.0,
            "n_request": 0,
        }
        for layer in layers
    }
    sample_layer_path = os.path.join(args.output_dir, "sample_layer_scores.jsonl")
    with open(sample_layer_path, "w", encoding="utf-8") as sample_f:
        for layer_chunk in chunked(layers, args.layer_chunk_size):
            modules = {
                layer: find_module(vllm.model, default_module_path(args.model_name, layer, args.module_kind))
                for layer in layer_chunk
            }
            for module in modules.values():
                set_module_trainable(module, True)

            for sample_idx, sample in enumerate(samples, 1):
                zero_module_grads(modules)
                old_loss = compute_target_loss(vllm, sample, str(sample.old_answer))
                old_loss.backward()
                old_grads = collect_old_grads(modules)

                zero_module_grads(modules)
                new_loss = compute_target_loss(vllm, sample, sample.target_new)
                new_loss.backward()
                stats_by_layer = compare_new_grads(modules, old_grads)

                for layer, stats in stats_by_layer.items():
                    accum[layer]["S_lga_dot"] += stats["dot"]
                    accum[layer]["S_lga_cos"] += stats["cos"]
                    accum[layer]["old_grad_norm"] += stats["old_norm"]
                    accum[layer]["new_grad_norm"] += stats["new_norm"]
                    accum[layer]["joint_grad_norm"] += stats["joint_grad_norm"]
                    accum[layer]["n_request"] += 1
                    sample_f.write(
                        json.dumps(
                            {
                                "case_id": sample.case_id,
                                "image_id": sample.image_id,
                                "layer": layer,
                                "module_path": default_module_path(args.model_name, layer, args.module_kind),
                                "old_answer": sample.old_answer,
                                "target_new": sample.target_new,
                                "old_loss": float(old_loss.detach().float().cpu().item()),
                                "new_loss": float(new_loss.detach().float().cpu().item()),
                                "s_lga_dot": stats["dot"],
                                "s_lga_cos": stats["cos"],
                                "old_grad_norm": stats["old_norm"],
                                "new_grad_norm": stats["new_norm"],
                                "joint_grad_norm": stats["joint_grad_norm"],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                zero_module_grads(modules)
                print(f"[scan] layers={layer_chunk} sample={sample_idx}/{len(samples)}")

            for module in modules.values():
                set_module_trainable(module, False)
            zero_module_grads(modules)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    rows: List[Dict[str, Any]] = []
    for layer in layers:
        n_request = int(accum[layer]["n_request"])
        if n_request <= 0:
            raise RuntimeError(f"No scores accumulated for layer {layer}")
        rows.append(
            {
                "model": args.model_name,
                "layer": layer,
                "module_kind": args.module_kind,
                "module_path": default_module_path(args.model_name, layer, args.module_kind),
                "n_request": n_request,
                "S_lga_dot": accum[layer]["S_lga_dot"],
                "S_lga_cos": accum[layer]["S_lga_cos"] / n_request,
                "old_grad_norm": accum[layer]["old_grad_norm"] / n_request,
                "new_grad_norm": accum[layer]["new_grad_norm"] / n_request,
                "joint_grad_norm": accum[layer]["joint_grad_norm"] / n_request,
            }
        )
    rows = rank_rows(rows)
    write_csv(os.path.join(args.output_dir, "lga_layer_scores.csv"), rows)

    summary = summarize_rows(rows, args.topk)
    topk_payload = {
        "model": args.model_name,
        "data": "bridge30",
        "module_kind": args.module_kind,
        "layers": layers,
        "n_request": len(samples),
        **{key: value for key, value in summary.items() if key != "topk_rows"},
    }
    with open(os.path.join(args.output_dir, "topk_layers.json"), "w", encoding="utf-8") as f:
        json.dump(topk_payload, f, ensure_ascii=False, indent=2)
    write_summary_md(os.path.join(args.output_dir, "summary.md"), args.model_name, rows, args.topk)
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(json.dumps(topk_payload["selected_golden_layer"], ensure_ascii=False))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Request-only Bridge30 VLM LGA layer scan.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--config-path", default=None)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", required=True)
    parser.add_argument("--old-answers-path", required=True)
    parser.add_argument("--old-answer-key", default="image_id")
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--module-kind", default="mlp", choices=["mlp", "self_attn", "attn", "layer"])
    parser.add_argument("--score-mode", default="request_only_lga")
    parser.add_argument("--main-score", default="dot")
    parser.add_argument("--diagnostics", default="cos,grad_norm,norm_ratio")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--torch-dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--layer-chunk-size", type=int, default=4)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--generate-old-answers-if-missing", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.score_mode != "request_only_lga":
        raise ValueError("Only request_only_lga is supported")
    if args.main_score != "dot":
        raise ValueError("Only dot is supported as the main LGA score")
    run_lga_scan(args)


if __name__ == "__main__":
    main()
