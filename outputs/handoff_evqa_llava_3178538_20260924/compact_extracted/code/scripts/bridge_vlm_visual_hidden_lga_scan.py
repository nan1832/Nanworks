import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [REPO_ROOT, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from bridge_vlm_adapter_lga_scan import (  # noqa: E402
    configure_model_dtype,
    count_trainable_params,
    get_torch_dtype,
)
from bridge_vlm_lga_scan import (  # noqa: E402
    EPS,
    generate_old_answers,
    load_bridge_samples,
    parse_layers,
)


def visual_layer_path(cfg: Any, layer: int) -> str:
    return cfg.llm_layer_tmp.format(int(layer))


def prepare_llm_inputs_for_hidden_grad(llm_inpt: Dict[str, Any]) -> Dict[str, Any]:
    prepared = {}
    for key, value in llm_inpt.items():
        if key == "inputs_embeds":
            prepared[key] = value.detach().clone().requires_grad_(True)
        elif hasattr(value, "detach"):
            prepared[key] = value.detach()
        else:
            prepared[key] = value
    return prepared


def tensor_from_layer_output(output: Any):
    if isinstance(output, tuple):
        output = output[0]
    return output


def grad_stats(old_grad: Any, new_grad: Any) -> Dict[str, float]:
    import torch

    old_flat = old_grad.float().reshape(-1)
    new_flat = new_grad.float().reshape(-1)
    dot = float(torch.sum(old_flat * new_flat).item())
    old_norm = float(torch.linalg.vector_norm(old_flat).item())
    new_norm = float(torch.linalg.vector_norm(new_flat).item())
    joint = old_norm * new_norm
    return {
        "dot": dot,
        "cos": dot / (joint + EPS),
        "old_norm": old_norm,
        "new_norm": new_norm,
        "joint_norm": joint,
    }


def compute_visual_hidden_target_grad(
    vllm: Any,
    layer_module: Any,
    sample: Any,
    target: str,
) -> Tuple[float, Any, Tuple[int, int]]:
    import torch

    captured: Dict[str, Any] = {}

    def retain_hidden_hook(module, args, output):
        hidden = tensor_from_layer_output(output)
        if not torch.is_tensor(hidden):
            raise TypeError(f"Expected tensor layer output, got {type(hidden)!r}")
        if not hidden.requires_grad:
            raise RuntimeError(
                "Captured hidden state does not require grad. "
                "The LLM inputs must require grad for visual-hidden LGA."
            )
        hidden.retain_grad()
        captured["hidden"] = hidden

    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [sample.prompt],
        [sample.image],
        [target],
    )
    if vt_range is None:
        raise RuntimeError("Visual-hidden LGA requires a non-empty visual token range")
    vt_start, vt_end = int(vt_range[0]), int(vt_range[1])
    if vt_end <= vt_start:
        raise RuntimeError(f"Invalid visual token range: {vt_range}")

    llm_inpt = prepare_llm_inputs_for_hidden_grad(llm_inpt)
    vllm.model.zero_grad(set_to_none=True)
    hook = layer_module.register_forward_hook(retain_hidden_hook)
    try:
        output = vllm.get_llm_outpt(llm_inpt, vt_range)
        loss = vllm.label_loss(output.logits, label_ids, label_masks, average=True)
        loss.backward()
        hidden = captured.get("hidden")
        if hidden is None or hidden.grad is None:
            raise RuntimeError("Layer hidden gradient was not captured")
        if vt_end > hidden.grad.shape[1]:
            raise RuntimeError(
                f"Visual token range {vt_start}:{vt_end} exceeds hidden sequence length {hidden.grad.shape[1]}"
            )
        visual_grad = hidden.grad[:, vt_start:vt_end, :].detach().float().cpu().contiguous()
        return float(loss.detach().float().cpu().item()), visual_grad, (vt_start, vt_end)
    finally:
        hook.remove()
        vllm.model.zero_grad(set_to_none=True)


def rank_visual_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for key, rank_key, descending in [
        ("S_vis_dot", "vis_dot_rank", True),
        ("S_vis_new_norm", "vis_new_norm_rank", True),
        ("S_vis_cos", "vis_cos_rank", True),
        ("S_vis_joint_norm", "vis_joint_norm_rank", True),
    ]:
        ranked = sorted(rows, key=lambda row: float(row[key]), reverse=descending)
        for rank, row in enumerate(ranked, 1):
            row[rank_key] = rank

    for row in rows:
        row["visual_hidden_lga_selected_by_dot"] = row["vis_dot_rank"] == 1
    return sorted(rows, key=lambda row: row["vis_dot_rank"])


def summarize_visual_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_dot = sorted(rows, key=lambda row: row["vis_dot_rank"])
    by_new_norm = sorted(rows, key=lambda row: row["vis_new_norm_rank"])
    by_cos = sorted(rows, key=lambda row: row["vis_cos_rank"])
    by_joint = sorted(rows, key=lambda row: row["vis_joint_norm_rank"])

    def layers(top_rows):
        return [int(row["layer"]) for row in top_rows]

    return {
        "main_score": "S_vis_dot",
        "gradient_target": "visual_token_hidden_state_h_vis_L",
        "base_model_trainable": False,
        "adapter_used": False,
        "diagnostic_scores": [
            "S_vis_cos",
            "S_vis_new_norm",
            "S_vis_old_norm",
            "S_vis_joint_norm",
            "vis_positive_ratio",
            "median_vis_dot",
        ],
        "top_by_vis_dot": {
            "top1": int(by_dot[0]["layer"]),
            "top3": layers(by_dot[:3]),
            "top5": layers(by_dot[:5]),
        },
        "top_by_vis_new_norm": {
            "top1": int(by_new_norm[0]["layer"]),
            "top3": layers(by_new_norm[:3]),
            "top5": layers(by_new_norm[:5]),
        },
        "top_by_vis_cos": {
            "top1": int(by_cos[0]["layer"]),
            "top3": layers(by_cos[:3]),
            "top5": layers(by_cos[:5]),
        },
        "top_by_vis_joint_norm": {
            "top1": int(by_joint[0]["layer"]),
            "top3": layers(by_joint[:3]),
            "top5": layers(by_joint[:5]),
        },
        "selected_visual_hidden_layer": {
            "by": "S_vis_dot",
            "top1": int(by_dot[0]["layer"]),
        },
    }


def write_visual_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "layer",
        "capture_point",
        "token_scope",
        "layer_path",
        "visual_token_start",
        "visual_token_end",
        "n_request",
        "S_vis_dot",
        "S_vis_cos",
        "S_vis_new_norm",
        "S_vis_old_norm",
        "S_vis_joint_norm",
        "vis_positive_ratio",
        "median_vis_dot",
        "vis_dot_rank",
        "vis_new_norm_rank",
        "vis_cos_rank",
        "vis_joint_norm_rank",
        "visual_hidden_lga_selected_by_dot",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_visual_summary_md(path: str, model_name: str, rows: List[Dict[str, Any]]) -> None:
    dot_rows = sorted(rows, key=lambda row: row["vis_dot_rank"])[:5]
    new_norm_rows = sorted(rows, key=lambda row: row["vis_new_norm_rank"])[:5]
    lines = [
        f"# Bridge30 {model_name} Visual-Hidden LGA Summary",
        "",
        "Gradient target: `visual_token_hidden_state_h_vis_L`",
        "Adapter used: `false`",
        "Main score: `S_vis_dot`",
        "",
        "## Visual Dot Top-5",
        "",
        "| Dot Rank | Layer | S_vis_dot | S_vis_cos | New Norm | Joint Norm | Positive Ratio |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in dot_rows:
        lines.append(
            f"| {row['vis_dot_rank']} | {row['layer']} | {row['S_vis_dot']:.6g} | "
            f"{row['S_vis_cos']:.6g} | {row['S_vis_new_norm']:.6g} | "
            f"{row['S_vis_joint_norm']:.6g} | {row['vis_positive_ratio']:.6g} |"
        )

    lines.extend(
        [
            "",
            "## Visual New-Norm Top-5",
            "",
            "| New-Norm Rank | Layer | S_vis_new_norm | S_vis_dot | S_vis_cos | Joint Norm |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in new_norm_rows:
        lines.append(
            f"| {row['vis_new_norm_rank']} | {row['layer']} | {row['S_vis_new_norm']:.6g} | "
            f"{row['S_vis_dot']:.6g} | {row['S_vis_cos']:.6g} | {row['S_vis_joint_norm']:.6g} |"
        )
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_visual_hidden_lga_scan(args: argparse.Namespace) -> None:
    import torch
    from editor.vllm_editors.vead.vead import VEADConfig
    from utils import find_module, load_vllm_for_edit

    os.makedirs(args.output_dir, exist_ok=True)
    layers = parse_layers(args.layers)
    cfg = VEADConfig.from_yaml(args.config_path)

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
        configure_model_dtype(vllm, args.torch_dtype)
        generate_old_answers(vllm, missing_samples, args.model_name, args.old_answers_path, args.max_new_tokens)
    else:
        get_torch_dtype(args.torch_dtype)

    samples, mapping_report = load_bridge_samples(
        args.data_path,
        args.bridge_root,
        args.old_answers_path,
        max_samples=args.max_samples,
        allow_missing_old_answers=False,
    )
    if not samples:
        raise RuntimeError("No Visual-Hidden LGA samples loaded")

    with open(os.path.join(args.output_dir, "old_answer_mapping_report.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, ensure_ascii=False, indent=2)

    if vllm is None:
        vllm = load_vllm_for_edit(args.model_name, args.device)
        configure_model_dtype(vllm, args.torch_dtype)

    vllm.model.eval()
    vllm.model.requires_grad_(False)
    print("gradient_target=visual_token_hidden_state_h_vis_L")
    print(f"base_requires_grad_params={count_trainable_params(vllm.model)}")
    print("adapter_used=False")

    accum: Dict[int, Dict[str, Any]] = {
        layer: {
            "S_vis_dot": 0.0,
            "S_vis_cos": 0.0,
            "S_vis_new_norm": 0.0,
            "S_vis_old_norm": 0.0,
            "S_vis_joint_norm": 0.0,
            "positive_count": 0,
            "dots": [],
            "n_request": 0,
            "visual_spans": set(),
        }
        for layer in layers
    }

    sample_path = os.path.join(args.output_dir, "sample_visual_hidden_scores.jsonl")
    with open(sample_path, "w", encoding="utf-8") as sample_f:
        for layer in layers:
            layer_path = visual_layer_path(cfg, layer)
            layer_module = find_module(vllm.model, layer_path)
            print(f"[visual-hidden] layer={layer} path={layer_path}")
            for sample_idx, sample in enumerate(samples, 1):
                old_loss, old_grad, old_span = compute_visual_hidden_target_grad(
                    vllm,
                    layer_module,
                    sample,
                    str(sample.old_answer),
                )
                new_loss, new_grad, new_span = compute_visual_hidden_target_grad(
                    vllm,
                    layer_module,
                    sample,
                    sample.target_new,
                )
                if old_span != new_span:
                    raise RuntimeError(f"Old/new visual spans differ for {sample.case_id}: {old_span} vs {new_span}")
                stats = grad_stats(old_grad, new_grad)

                accum[layer]["S_vis_dot"] += stats["dot"]
                accum[layer]["S_vis_cos"] += stats["cos"]
                accum[layer]["S_vis_new_norm"] += stats["new_norm"]
                accum[layer]["S_vis_old_norm"] += stats["old_norm"]
                accum[layer]["S_vis_joint_norm"] += stats["joint_norm"]
                accum[layer]["positive_count"] += 1 if stats["dot"] > 0 else 0
                accum[layer]["dots"].append(stats["dot"])
                accum[layer]["n_request"] += 1
                accum[layer]["visual_spans"].add(old_span)

                sample_f.write(
                    json.dumps(
                        {
                            "case_id": sample.case_id,
                            "image_id": sample.image_id,
                            "layer": layer,
                            "layer_path": layer_path,
                            "capture_point": args.capture_point,
                            "token_scope": args.token_scope,
                            "visual_token_start": old_span[0],
                            "visual_token_end": old_span[1],
                            "old_answer": sample.old_answer,
                            "target_new": sample.target_new,
                            "old_loss": old_loss,
                            "new_loss": new_loss,
                            "s_vis_dot": stats["dot"],
                            "s_vis_cos": stats["cos"],
                            "vis_old_norm": stats["old_norm"],
                            "vis_new_norm": stats["new_norm"],
                            "vis_joint_norm": stats["joint_norm"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                print(f"[scan] layer={layer} sample={sample_idx}/{len(samples)}")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    rows: List[Dict[str, Any]] = []
    for layer in layers:
        n_request = int(accum[layer]["n_request"])
        if n_request <= 0:
            raise RuntimeError(f"No scores accumulated for layer {layer}")
        spans = sorted(accum[layer]["visual_spans"])
        span_start = spans[0][0] if len(spans) == 1 else "mixed"
        span_end = spans[0][1] if len(spans) == 1 else "mixed"
        rows.append(
            {
                "model": args.model_name,
                "layer": layer,
                "capture_point": args.capture_point,
                "token_scope": args.token_scope,
                "layer_path": visual_layer_path(cfg, layer),
                "visual_token_start": span_start,
                "visual_token_end": span_end,
                "n_request": n_request,
                "S_vis_dot": accum[layer]["S_vis_dot"],
                "S_vis_cos": accum[layer]["S_vis_cos"] / n_request,
                "S_vis_new_norm": accum[layer]["S_vis_new_norm"] / n_request,
                "S_vis_old_norm": accum[layer]["S_vis_old_norm"] / n_request,
                "S_vis_joint_norm": accum[layer]["S_vis_joint_norm"] / n_request,
                "vis_positive_ratio": accum[layer]["positive_count"] / n_request,
                "median_vis_dot": float(median(accum[layer]["dots"])),
            }
        )
    rows = rank_visual_rows(rows)
    write_visual_csv(os.path.join(args.output_dir, "visual_hidden_lga_layer_scores.csv"), rows)

    topk_payload = {
        "model": args.model_name,
        "data": "bridge30",
        "layers": layers,
        "n_request": len(samples),
        "capture_point": args.capture_point,
        "token_scope": args.token_scope,
        **summarize_visual_rows(rows),
    }
    with open(os.path.join(args.output_dir, "topk_visual_hidden_layers.json"), "w", encoding="utf-8") as f:
        json.dump(topk_payload, f, ensure_ascii=False, indent=2)
    write_visual_summary_md(os.path.join(args.output_dir, "summary.md"), args.model_name, rows)
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(json.dumps(topk_payload["selected_visual_hidden_layer"], ensure_ascii=False))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Request-only Bridge30 visual-hidden LGA layer scan.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", required=True)
    parser.add_argument("--old-answers-path", required=True)
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--capture-point", default="adapter_hook", choices=["adapter_hook", "layer_output"])
    parser.add_argument("--token-scope", default="visual", choices=["visual", "visual_prefix"])
    parser.add_argument("--score-mode", default="request_only_visual_hidden_lga")
    parser.add_argument("--main-score", default="vis_dot")
    parser.add_argument(
        "--diagnostics",
        default="vis_cos,vis_new_norm,vis_old_norm,vis_joint_norm,positive_ratio,median_dot",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--torch-dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--generate-old-answers-if-missing", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.score_mode != "request_only_visual_hidden_lga":
        raise ValueError("Only request_only_visual_hidden_lga is supported")
    if args.main_score != "vis_dot":
        raise ValueError("Only vis_dot is supported as the main Visual-Hidden LGA score")
    run_visual_hidden_lga_scan(args)


if __name__ == "__main__":
    main()
