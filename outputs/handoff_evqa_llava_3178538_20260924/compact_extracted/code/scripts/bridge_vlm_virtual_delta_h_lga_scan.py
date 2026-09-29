import argparse
import csv
import json
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


def load_llm_layer_template(config_path: str) -> str:
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("llm_layer_tmp:"):
                value = stripped.split(":", 1)[1].strip()
                return value.strip("\"'")
    raise RuntimeError(f"Could not find llm_layer_tmp in config: {config_path}")


def layer_path(llm_layer_tmp: str, layer: int) -> str:
    return llm_layer_tmp.format(int(layer))


def tensor_from_layer_output(output: Any):
    if isinstance(output, tuple):
        output = output[0]
    return output


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


def answer_loss_positions(label_masks: Any, seq_len: int) -> set:
    import torch

    label_len = int(label_masks.shape[1])
    tail_start = max(seq_len - label_len, 0)
    mask = label_masks[0].detach()
    indices = torch.nonzero(mask > 0, as_tuple=False).reshape(-1).tolist()
    return {tail_start + int(idx) for idx in indices if tail_start + int(idx) < seq_len}


def prompt_text_indices(
    seq_len: int,
    vt_range: Tuple[int, int],
    llm_inpt: Dict[str, Any],
    label_masks: Any,
) -> List[int]:
    import torch

    attention_mask = llm_inpt.get("attention_mask")
    if attention_mask is None:
        valid = set(range(seq_len))
    else:
        mask = attention_mask[0].detach()
        valid = {
            int(idx)
            for idx in torch.nonzero(mask > 0, as_tuple=False).reshape(-1).tolist()
            if int(idx) < seq_len
        }

    vt_start, vt_end = int(vt_range[0]), int(vt_range[1])
    visual = set(range(vt_start, min(vt_end, seq_len)))
    answer_like = answer_loss_positions(label_masks, seq_len)

    indices = sorted(valid - visual - answer_like)
    if indices:
        return indices

    label_len = int(label_masks.shape[1])
    tail_start = max(seq_len - label_len, 0)
    fallback = sorted(idx for idx in (valid - visual) if idx < tail_start)
    return fallback


def grad_stats(old_grad: Any, new_grad: Any, eps: float) -> Dict[str, float]:
    import torch

    old_flat = old_grad.float().reshape(-1)
    new_flat = new_grad.float().reshape(-1)
    dot = float(torch.sum(old_flat * new_flat).item())
    old_norm = float(torch.linalg.vector_norm(old_flat).item())
    new_norm = float(torch.linalg.vector_norm(new_flat).item())
    joint = old_norm * new_norm
    numel = max(int(old_flat.numel()), 1)
    return {
        "dot": dot,
        "conflict": -dot,
        "dot_per_dim": dot / numel,
        "cos": dot / (joint + EPS),
        "old_norm": old_norm,
        "new_norm": new_norm,
        "joint_norm": joint,
        "old_nonzero_ratio": float((old_flat.abs() > eps).float().mean().item()),
        "new_nonzero_ratio": float((new_flat.abs() > eps).float().mean().item()),
        "numel": float(numel),
    }


def compute_virtual_delta_target_grad(
    vllm: Any,
    layer_module: Any,
    sample: Any,
    target: str,
    zero_grad_eps: float,
) -> Dict[str, Any]:
    import torch

    captured: Dict[str, Any] = {}

    def retain_hidden_hook(module, args, output):
        hidden = tensor_from_layer_output(output)
        if not torch.is_tensor(hidden):
            raise TypeError(f"Expected tensor layer output, got {type(hidden)!r}")
        if not hidden.requires_grad:
            raise RuntimeError(
                "Captured hidden state does not require grad. "
                "The LLM inputs must require grad for virtual Delta-h LGA."
            )
        hidden.retain_grad()
        captured["hidden"] = hidden

    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [sample.prompt],
        [sample.image],
        [target],
    )
    if vt_range is None:
        raise RuntimeError("Virtual Delta-h LGA requires a non-empty visual token range")
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

        grad = hidden.grad.detach().float().cpu().contiguous()
        if vt_end > grad.shape[1]:
            raise RuntimeError(f"Visual token range {vt_start}:{vt_end} exceeds seq len {grad.shape[1]}")
        text_idx = prompt_text_indices(int(grad.shape[1]), (vt_start, vt_end), llm_inpt, label_masks)
        if not text_idx:
            raise RuntimeError("No text prompt tokens remained after excluding visual and answer-loss positions")

        text_index = torch.tensor(text_idx, dtype=torch.long)
        visual_grad = grad[:, vt_start:vt_end, :]
        text_grad = grad.index_select(1, text_index)

        return {
            "loss": float(loss.detach().float().cpu().item()),
            "visual_grad": visual_grad,
            "text_grad": text_grad,
            "visual_span": (vt_start, vt_end),
            "text_token_count": len(text_idx),
            "seq_len": int(grad.shape[1]),
            "answer_loss_position_count": len(answer_loss_positions(label_masks, int(grad.shape[1]))),
            "visual_nonzero_ratio": float((visual_grad.abs() > zero_grad_eps).float().mean().item()),
            "text_nonzero_ratio": float((text_grad.abs() > zero_grad_eps).float().mean().item()),
        }
    finally:
        hook.remove()
        vllm.model.zero_grad(set_to_none=True)


def add_rank(rows: List[Dict[str, Any]], key: str, rank_key: str, descending: bool = True) -> None:
    ranked = sorted(rows, key=lambda row: float(row[key]), reverse=descending)
    for rank, row in enumerate(ranked, 1):
        row[rank_key] = rank


def rank_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for prefix in ["S_v", "S_t"]:
        stem = "visual" if prefix == "S_v" else "text"
        add_rank(rows, f"{prefix}_dot", f"{stem}_dot_rank", True)
        add_rank(rows, f"{prefix}_conflict", f"{stem}_conflict_rank", True)
        add_rank(rows, f"{prefix}_dot_per_dim", f"{stem}_dot_per_dim_rank", True)
        add_rank(rows, f"{prefix}_cos", f"{stem}_cos_rank", True)
        add_rank(rows, f"{prefix}_new_norm", f"{stem}_new_norm_rank", True)
        add_rank(rows, f"{prefix}_joint_norm", f"{stem}_joint_norm_rank", True)
    for row in rows:
        row["virtual_delta_h_visual_selected_by_dot"] = row["visual_dot_rank"] == 1
        row["virtual_delta_h_text_selected_by_dot"] = row["text_dot_rank"] == 1
    return sorted(rows, key=lambda row: row["visual_dot_rank"])


def top_layers(rows: List[Dict[str, Any]], rank_key: str, k: int = 5) -> List[int]:
    return [int(row["layer"]) for row in sorted(rows, key=lambda row: row[rank_key])[:k]]


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "main_scores": ["S_v_dot", "S_t_dot"],
        "gradient_target": "virtual_delta_h_at_layer_hidden_state",
        "base_model_trainable": False,
        "adapter_used": False,
        "forward_equivalence_max_diff": 0.0,
        "visual": {
            "top_by_dot": top_layers(rows, "visual_dot_rank"),
            "top_by_conflict": top_layers(rows, "visual_conflict_rank"),
            "top_by_dot_per_dim": top_layers(rows, "visual_dot_per_dim_rank"),
            "top_by_new_norm": top_layers(rows, "visual_new_norm_rank"),
            "selected_by_dot": top_layers(rows, "visual_dot_rank", 1)[0],
        },
        "text": {
            "top_by_dot": top_layers(rows, "text_dot_rank"),
            "top_by_conflict": top_layers(rows, "text_conflict_rank"),
            "top_by_dot_per_dim": top_layers(rows, "text_dot_per_dim_rank"),
            "top_by_new_norm": top_layers(rows, "text_new_norm_rank"),
            "selected_by_dot": top_layers(rows, "text_dot_rank", 1)[0],
        },
    }


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "layer",
        "layer_path",
        "n_request",
        "visual_token_start",
        "visual_token_end",
        "text_token_count_mean",
        "answer_loss_position_count_mean",
        "S_v_dot",
        "S_v_conflict",
        "S_v_dot_per_dim",
        "S_v_cos",
        "S_v_old_norm",
        "S_v_new_norm",
        "S_v_joint_norm",
        "S_v_positive_ratio",
        "S_v_zero_grad",
        "S_v_old_nonzero_ratio",
        "S_v_new_nonzero_ratio",
        "median_v_dot",
        "S_t_dot",
        "S_t_conflict",
        "S_t_dot_per_dim",
        "S_t_cos",
        "S_t_old_norm",
        "S_t_new_norm",
        "S_t_joint_norm",
        "S_t_positive_ratio",
        "S_t_zero_grad",
        "S_t_old_nonzero_ratio",
        "S_t_new_nonzero_ratio",
        "median_t_dot",
        "visual_dot_rank",
        "visual_conflict_rank",
        "visual_dot_per_dim_rank",
        "visual_cos_rank",
        "visual_new_norm_rank",
        "visual_joint_norm_rank",
        "text_dot_rank",
        "text_conflict_rank",
        "text_dot_per_dim_rank",
        "text_cos_rank",
        "text_new_norm_rank",
        "text_joint_norm_rank",
        "virtual_delta_h_visual_selected_by_dot",
        "virtual_delta_h_text_selected_by_dot",
        "forward_equivalence_max_diff",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_summary_md(path: str, model_name: str, rows: List[Dict[str, Any]]) -> None:
    def block(title: str, rank_key: str, cols: List[Tuple[str, str]]) -> List[str]:
        top = sorted(rows, key=lambda row: row[rank_key])[:5]
        lines = [
            f"## {title}",
            "",
            "| Rank | Layer | " + " | ".join(label for label, _ in cols) + " |",
            "|---:|---:|" + "|".join(["---:" for _ in cols]) + "|",
        ]
        for row in top:
            values = []
            for _, key in cols:
                value = row[key]
                if isinstance(value, float):
                    values.append(f"{value:.6g}")
                else:
                    values.append(str(value))
            lines.append(f"| {row[rank_key]} | {row['layer']} | " + " | ".join(values) + " |")
        lines.append("")
        return lines

    lines = [
        f"# Bridge30 {model_name} Virtual Delta-h LGA Summary",
        "",
        "Adapter used: `false`",
        "Base model trainable: `false`",
        "Loss: mean answer-token NLL",
        "Text scope: prompt tokens after excluding visual tokens and answer-loss positions",
        "Forward equivalence max diff: `0.0` (retention hook only)",
        "",
    ]
    lines += block(
        "Visual Dot Top-5",
        "visual_dot_rank",
        [
            ("S_v_dot", "S_v_dot"),
            ("Conflict", "S_v_conflict"),
            ("Dot/Dim", "S_v_dot_per_dim"),
            ("Cos", "S_v_cos"),
            ("New Norm", "S_v_new_norm"),
            ("Pos Ratio", "S_v_positive_ratio"),
        ],
    )
    lines += block(
        "Visual Conflict Top-5",
        "visual_conflict_rank",
        [
            ("Conflict", "S_v_conflict"),
            ("S_v_dot", "S_v_dot"),
            ("Dot/Dim", "S_v_dot_per_dim"),
            ("New Norm", "S_v_new_norm"),
        ],
    )
    lines += block(
        "Text Dot Top-5",
        "text_dot_rank",
        [
            ("S_t_dot", "S_t_dot"),
            ("Conflict", "S_t_conflict"),
            ("Dot/Dim", "S_t_dot_per_dim"),
            ("Cos", "S_t_cos"),
            ("New Norm", "S_t_new_norm"),
            ("Pos Ratio", "S_t_positive_ratio"),
        ],
    )
    lines += block(
        "Text Conflict Top-5",
        "text_conflict_rank",
        [
            ("Conflict", "S_t_conflict"),
            ("S_t_dot", "S_t_dot"),
            ("Dot/Dim", "S_t_dot_per_dim"),
            ("New Norm", "S_t_new_norm"),
        ],
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def init_accum() -> Dict[str, Any]:
    return {
        "v_dot": 0.0,
        "v_conflict": 0.0,
        "v_dot_per_dim": 0.0,
        "v_cos": 0.0,
        "v_old_norm": 0.0,
        "v_new_norm": 0.0,
        "v_joint_norm": 0.0,
        "v_old_nonzero_ratio": 0.0,
        "v_new_nonzero_ratio": 0.0,
        "v_positive_count": 0,
        "v_dots": [],
        "t_dot": 0.0,
        "t_conflict": 0.0,
        "t_dot_per_dim": 0.0,
        "t_cos": 0.0,
        "t_old_norm": 0.0,
        "t_new_norm": 0.0,
        "t_joint_norm": 0.0,
        "t_old_nonzero_ratio": 0.0,
        "t_new_nonzero_ratio": 0.0,
        "t_positive_count": 0,
        "t_dots": [],
        "n_request": 0,
        "visual_spans": set(),
        "text_token_count_sum": 0,
        "answer_loss_position_count_sum": 0,
    }


def run_virtual_delta_h_lga_scan(args: argparse.Namespace) -> None:
    import torch
    from utils import find_module, load_vllm_for_edit

    os.makedirs(args.output_dir, exist_ok=True)
    layers = parse_layers(args.layers)
    llm_layer_tmp = load_llm_layer_template(args.config_path)

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
        raise RuntimeError("No Virtual Delta-h LGA samples loaded")

    with open(os.path.join(args.output_dir, "old_answer_mapping_report.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, ensure_ascii=False, indent=2)

    if vllm is None:
        vllm = load_vllm_for_edit(args.model_name, args.device)
        configure_model_dtype(vllm, args.torch_dtype)

    vllm.model.eval()
    vllm.model.requires_grad_(False)
    print("gradient_target=virtual_delta_h_at_layer_hidden_state")
    print(f"base_requires_grad_params={count_trainable_params(vllm.model)}")
    print("adapter_used=False")

    accum: Dict[int, Dict[str, Any]] = {layer: init_accum() for layer in layers}
    sample_path = os.path.join(args.output_dir, "sample_virtual_delta_h_scores.jsonl")
    with open(sample_path, "w", encoding="utf-8") as sample_f:
        for layer in layers:
            layer_module_path = layer_path(llm_layer_tmp, layer)
            layer_module = find_module(vllm.model, layer_module_path)
            print(f"[virtual-delta-h] layer={layer} path={layer_module_path}", flush=True)
            for sample_idx, sample in enumerate(samples, 1):
                old_out = compute_virtual_delta_target_grad(
                    vllm,
                    layer_module,
                    sample,
                    str(sample.old_answer),
                    args.zero_grad_eps,
                )
                new_out = compute_virtual_delta_target_grad(
                    vllm,
                    layer_module,
                    sample,
                    sample.target_new,
                    args.zero_grad_eps,
                )
                if old_out["visual_span"] != new_out["visual_span"]:
                    raise RuntimeError(
                        f"Old/new visual spans differ for {sample.case_id}: "
                        f"{old_out['visual_span']} vs {new_out['visual_span']}"
                    )

                v_stats = grad_stats(old_out["visual_grad"], new_out["visual_grad"], args.zero_grad_eps)
                t_stats = grad_stats(old_out["text_grad"], new_out["text_grad"], args.zero_grad_eps)
                a = accum[layer]
                for stat_key, acc_key in [
                    ("dot", "v_dot"),
                    ("conflict", "v_conflict"),
                    ("dot_per_dim", "v_dot_per_dim"),
                    ("cos", "v_cos"),
                    ("old_norm", "v_old_norm"),
                    ("new_norm", "v_new_norm"),
                    ("joint_norm", "v_joint_norm"),
                    ("old_nonzero_ratio", "v_old_nonzero_ratio"),
                    ("new_nonzero_ratio", "v_new_nonzero_ratio"),
                ]:
                    a[acc_key] += float(v_stats[stat_key])
                for stat_key, acc_key in [
                    ("dot", "t_dot"),
                    ("conflict", "t_conflict"),
                    ("dot_per_dim", "t_dot_per_dim"),
                    ("cos", "t_cos"),
                    ("old_norm", "t_old_norm"),
                    ("new_norm", "t_new_norm"),
                    ("joint_norm", "t_joint_norm"),
                    ("old_nonzero_ratio", "t_old_nonzero_ratio"),
                    ("new_nonzero_ratio", "t_new_nonzero_ratio"),
                ]:
                    a[acc_key] += float(t_stats[stat_key])
                a["v_positive_count"] += 1 if v_stats["dot"] > 0 else 0
                a["t_positive_count"] += 1 if t_stats["dot"] > 0 else 0
                a["v_dots"].append(v_stats["dot"])
                a["t_dots"].append(t_stats["dot"])
                a["n_request"] += 1
                a["visual_spans"].add(old_out["visual_span"])
                a["text_token_count_sum"] += int(old_out["text_token_count"])
                a["answer_loss_position_count_sum"] += int(old_out["answer_loss_position_count"])

                sample_f.write(
                    json.dumps(
                        {
                            "case_id": sample.case_id,
                            "image_id": sample.image_id,
                            "layer": layer,
                            "layer_path": layer_module_path,
                            "old_answer": sample.old_answer,
                            "old_answer_short": sample.old_answer,
                            "target_new": sample.target_new,
                            "old_loss": old_out["loss"],
                            "new_loss": new_out["loss"],
                            "visual_token_start": old_out["visual_span"][0],
                            "visual_token_end": old_out["visual_span"][1],
                            "text_token_count": old_out["text_token_count"],
                            "answer_loss_position_count": old_out["answer_loss_position_count"],
                            "s_v_dot": v_stats["dot"],
                            "s_v_conflict": v_stats["conflict"],
                            "s_v_dot_per_dim": v_stats["dot_per_dim"],
                            "s_v_cos": v_stats["cos"],
                            "v_old_norm": v_stats["old_norm"],
                            "v_new_norm": v_stats["new_norm"],
                            "v_joint_norm": v_stats["joint_norm"],
                            "v_old_nonzero_ratio": v_stats["old_nonzero_ratio"],
                            "v_new_nonzero_ratio": v_stats["new_nonzero_ratio"],
                            "s_t_dot": t_stats["dot"],
                            "s_t_conflict": t_stats["conflict"],
                            "s_t_dot_per_dim": t_stats["dot_per_dim"],
                            "s_t_cos": t_stats["cos"],
                            "t_old_norm": t_stats["old_norm"],
                            "t_new_norm": t_stats["new_norm"],
                            "t_joint_norm": t_stats["joint_norm"],
                            "t_old_nonzero_ratio": t_stats["old_nonzero_ratio"],
                            "t_new_nonzero_ratio": t_stats["new_nonzero_ratio"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                print(f"[scan] layer={layer} sample={sample_idx}/{len(samples)}", flush=True)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    rows: List[Dict[str, Any]] = []
    for layer in layers:
        a = accum[layer]
        n = int(a["n_request"])
        if n <= 0:
            raise RuntimeError(f"No scores accumulated for layer {layer}")
        spans = sorted(a["visual_spans"])
        span_start = spans[0][0] if len(spans) == 1 else "mixed"
        span_end = spans[0][1] if len(spans) == 1 else "mixed"
        v_old_norm = a["v_old_norm"] / n
        v_new_norm = a["v_new_norm"] / n
        t_old_norm = a["t_old_norm"] / n
        t_new_norm = a["t_new_norm"] / n
        rows.append(
            {
                "model": args.model_name,
                "layer": layer,
                "layer_path": layer_path(llm_layer_tmp, layer),
                "n_request": n,
                "visual_token_start": span_start,
                "visual_token_end": span_end,
                "text_token_count_mean": a["text_token_count_sum"] / n,
                "answer_loss_position_count_mean": a["answer_loss_position_count_sum"] / n,
                "S_v_dot": a["v_dot"] / n,
                "S_v_conflict": a["v_conflict"] / n,
                "S_v_dot_per_dim": a["v_dot_per_dim"] / n,
                "S_v_cos": a["v_cos"] / n,
                "S_v_old_norm": v_old_norm,
                "S_v_new_norm": v_new_norm,
                "S_v_joint_norm": a["v_joint_norm"] / n,
                "S_v_positive_ratio": a["v_positive_count"] / n,
                "S_v_zero_grad": bool(v_old_norm < args.zero_grad_eps or v_new_norm < args.zero_grad_eps),
                "S_v_old_nonzero_ratio": a["v_old_nonzero_ratio"] / n,
                "S_v_new_nonzero_ratio": a["v_new_nonzero_ratio"] / n,
                "median_v_dot": float(median(a["v_dots"])),
                "S_t_dot": a["t_dot"] / n,
                "S_t_conflict": a["t_conflict"] / n,
                "S_t_dot_per_dim": a["t_dot_per_dim"] / n,
                "S_t_cos": a["t_cos"] / n,
                "S_t_old_norm": t_old_norm,
                "S_t_new_norm": t_new_norm,
                "S_t_joint_norm": a["t_joint_norm"] / n,
                "S_t_positive_ratio": a["t_positive_count"] / n,
                "S_t_zero_grad": bool(t_old_norm < args.zero_grad_eps or t_new_norm < args.zero_grad_eps),
                "S_t_old_nonzero_ratio": a["t_old_nonzero_ratio"] / n,
                "S_t_new_nonzero_ratio": a["t_new_nonzero_ratio"] / n,
                "median_t_dot": float(median(a["t_dots"])),
                "forward_equivalence_max_diff": 0.0,
            }
        )
    rows = rank_rows(rows)
    write_csv(os.path.join(args.output_dir, "virtual_delta_h_lga_layer_scores.csv"), rows)

    topk_payload = {
        "model": args.model_name,
        "data": "bridge30",
        "layers": layers,
        "n_request": len(samples),
        "text_scope": "prompt_tokens_excluding_visual_and_answer_loss_positions",
        "zero_grad_eps": args.zero_grad_eps,
        **summarize_rows(rows),
    }
    with open(os.path.join(args.output_dir, "topk_virtual_delta_h_layers.json"), "w", encoding="utf-8") as f:
        json.dump(topk_payload, f, ensure_ascii=False, indent=2)
    write_summary_md(os.path.join(args.output_dir, "summary.md"), args.model_name, rows)
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(json.dumps({"visual": topk_payload["visual"], "text": topk_payload["text"]}, ensure_ascii=False))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Request-only Bridge30 Virtual Delta-h LGA layer scan.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", required=True)
    parser.add_argument("--old-answers-path", required=True)
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--torch-dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--generate-old-answers-if-missing", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--zero-grad-eps", type=float, default=1e-8)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    run_virtual_delta_h_lga_scan(args)


if __name__ == "__main__":
    main()
