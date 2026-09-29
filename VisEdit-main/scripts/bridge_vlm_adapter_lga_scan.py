import argparse
import csv
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [REPO_ROOT, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from bridge_vlm_lga_scan import (  # noqa: E402
    EPS,
    chunked,
    collect_old_grads,
    compare_new_grads,
    detach_llm_inputs,
    generate_old_answers,
    load_bridge_samples,
    parse_layers,
)


def set_all_seeds(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def adapter_layer_path(cfg: Any, layer: int) -> str:
    return cfg.llm_layer_tmp.format(int(layer))


def adapter_hook_wrap(adapter: Any):
    def adapter_hook(module, args, output):
        if isinstance(output, tuple):
            updated = list(output)
            updated[0] = adapter(updated[0])
            return tuple(updated)
        return adapter(output)

    return adapter_hook


def set_adapter_trainable(adapter: Any, trainable: bool) -> None:
    adapter.requires_grad_(trainable)
    adapter.train(trainable)


def zero_adapter_grad(adapter: Any) -> None:
    for param in adapter.parameters():
        param.grad = None


def count_trainable_params(module: Any) -> int:
    return sum(param.numel() for param in module.parameters() if param.requires_grad)


def create_adapter(vllm: Any, cfg: Any, device: str, dtype: Any):
    from editor.vllm_editors.vead.adpt_model import VisionEditAdaptor

    adapter = VisionEditAdaptor(
        cfg.llm_hidden_size,
        cfg.adaptor_mid_dim,
        cfg.adaptor_cross_att_head_n,
        vllm.get_img_token_n(),
        cfg.IT.add_it,
        cfg.IT.mid_dim,
    ).to(device)
    if dtype is not None:
        adapter = adapter.to(dtype=dtype)
    adapter.open_adaptor(False)
    set_adapter_trainable(adapter, True)
    return adapter


def get_torch_dtype(raw: str):
    import torch

    if raw == "float16":
        return torch.float16
    if raw == "bfloat16":
        return torch.bfloat16
    if raw == "float32":
        return torch.float32
    raise ValueError(f"Unsupported dtype: {raw}")


def configure_model_dtype(vllm: Any, raw_dtype: str) -> Any:
    dtype = get_torch_dtype(raw_dtype)
    if raw_dtype in {"float16", "bfloat16"}:
        vllm.model.to(dtype=dtype)
    return dtype


def get_edit_signal(vllm: Any, adapter: Any, layer_path: str, sample: Any):
    import torch
    from utils.nethook import TraceDict

    adapter.open_adaptor(False)
    (llm_inpt, vt_range), label_ids, _ = vllm.prompts_imgs_target_to_xym(
        [sample.prompt],
        [sample.image],
        [sample.target_new],
    )
    with TraceDict(vllm.model, [layer_path], retain_output=True, stop=True) as traces:
        vllm.get_llm_outpt(llm_inpt, vt_range)
    edit_reps = traces[layer_path].output
    if not isinstance(edit_reps, torch.Tensor):
        edit_reps = edit_reps[0]
    edit_reps = edit_reps.detach()
    prompt_end = int(llm_inpt["inputs_embeds"].shape[1] - label_ids.shape[1])
    edit_mask = torch.ones([1, edit_reps.shape[1]], device=vllm.device, dtype=edit_reps.dtype)
    prompt_end_tensor = torch.tensor([prompt_end], device=vllm.device)
    return edit_reps, edit_mask, prompt_end_tensor


def compute_adapter_target_loss(vllm: Any, adapter: Any, sample: Any, target: str):
    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [sample.prompt],
        [sample.image],
        [target],
    )
    llm_inpt = detach_llm_inputs(llm_inpt)
    if vt_range is None:
        adapter.set_input_info(False, None, None)
    else:
        adapter.set_input_info(True, int(vt_range[0]), int(vt_range[1]))
    output = vllm.get_llm_outpt(llm_inpt, vt_range)
    return vllm.label_loss(output.logits, label_ids, label_masks, average=True)


def rank_adapter_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    joint_mean = sum(float(row["adapter_joint_norm"]) for row in rows) / max(len(rows), 1)
    for row in rows:
        row["adapter_norm_ratio"] = float(row["adapter_joint_norm"]) / (joint_mean + EPS)

    rank_specs = [
        ("S_adapter_dot", "dot_rank", True),
        ("S_adapter_cos", "cos_rank", True),
        ("adapter_joint_norm", "norm_rank", True),
        ("S_adapter_dot", "conflict_dot_rank", False),
        ("S_adapter_cos", "conflict_cos_rank", False),
    ]
    for key, rank_key, descending in rank_specs:
        ranked = sorted(rows, key=lambda row: float(row[key]), reverse=descending)
        for rank, row in enumerate(ranked, 1):
            row[rank_key] = rank

    for row in rows:
        row["adapter_lga_selected_by_dot"] = row["dot_rank"] == 1
    return sorted(rows, key=lambda row: row["dot_rank"])


def summarize_adapter_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_dot = sorted(rows, key=lambda row: row["dot_rank"])
    by_cos = sorted(rows, key=lambda row: row["cos_rank"])
    by_conflict_dot = sorted(rows, key=lambda row: row["conflict_dot_rank"])
    by_conflict_cos = sorted(rows, key=lambda row: row["conflict_cos_rank"])

    def layers(top_rows):
        return [int(row["layer"]) for row in top_rows]

    return {
        "main_score": "S_adapter_dot",
        "gradient_target": "adapter_parameters_phi_L",
        "base_model_trainable": False,
        "adapter_trainable": True,
        "diagnostic_scores": [
            "S_adapter_cos",
            "adapter_old_grad_norm",
            "adapter_new_grad_norm",
            "adapter_joint_norm",
            "adapter_norm_ratio",
        ],
        "top_by_adapter_dot": {
            "top1": int(by_dot[0]["layer"]),
            "top3": layers(by_dot[:3]),
            "top5": layers(by_dot[:5]),
        },
        "top_by_adapter_cos": {
            "top1": int(by_cos[0]["layer"]),
            "top3": layers(by_cos[:3]),
            "top5": layers(by_cos[:5]),
        },
        "top_by_adapter_conflict_dot": {
            "top1": int(by_conflict_dot[0]["layer"]),
            "top3": layers(by_conflict_dot[:3]),
            "top5": layers(by_conflict_dot[:5]),
        },
        "top_by_adapter_conflict_cos": {
            "top1": int(by_conflict_cos[0]["layer"]),
            "top3": layers(by_conflict_cos[:3]),
            "top5": layers(by_conflict_cos[:5]),
        },
        "selected_adapter_golden_layer": {
            "by": "S_adapter_dot",
            "top1": int(by_dot[0]["layer"]),
        },
    }


def write_adapter_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "layer",
        "adapter_type",
        "adapter_path",
        "n_request",
        "S_adapter_dot",
        "S_adapter_cos",
        "adapter_old_grad_norm",
        "adapter_new_grad_norm",
        "adapter_joint_norm",
        "adapter_norm_ratio",
        "dot_rank",
        "cos_rank",
        "norm_rank",
        "adapter_lga_selected_by_dot",
        "conflict_dot_rank",
        "conflict_cos_rank",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_adapter_summary_md(path: str, model_name: str, rows: List[Dict[str, Any]]) -> None:
    dot_rows = sorted(rows, key=lambda row: row["dot_rank"])[:5]
    conflict_rows = sorted(rows, key=lambda row: row["conflict_dot_rank"])[:5]
    lines = [
        f"# Bridge30 {model_name} Adapter-LGA Summary",
        "",
        "Gradient target: `adapter_parameters_phi_L`",
        "Main score: `S_adapter_dot`",
        "",
        "## Dot Top-5",
        "",
        "| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Rank |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in dot_rows:
        lines.append(
            f"| {row['dot_rank']} | {row['layer']} | {row['S_adapter_dot']:.6g} | "
            f"{row['S_adapter_cos']:.6g} | {row['adapter_joint_norm']:.6g} | "
            f"{row['adapter_norm_ratio']:.6g} | {row['conflict_dot_rank']} |"
        )
    lines.extend(
        [
            "",
            "## Conflict Dot Top-5",
            "",
            "| Conflict Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Dot Rank |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in conflict_rows:
        lines.append(
            f"| {row['conflict_dot_rank']} | {row['layer']} | {row['S_adapter_dot']:.6g} | "
            f"{row['S_adapter_cos']:.6g} | {row['adapter_joint_norm']:.6g} | "
            f"{row['adapter_norm_ratio']:.6g} | {row['dot_rank']} |"
        )
    lines.extend(
        [
            "",
            "Conflict ranks are diagnostic only; the adapter-LGA main result uses `S_adapter_dot`.",
            "",
        ]
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_adapter_lga_scan(args: argparse.Namespace) -> None:
    import torch
    from editor.vllm_editors.vead.vead import VEADConfig
    from utils import find_module, load_vllm_for_edit

    os.makedirs(args.output_dir, exist_ok=True)
    layers = parse_layers(args.layers)
    cfg = VEADConfig.from_yaml(args.vead_config_path)

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
        dtype = configure_model_dtype(vllm, args.torch_dtype)
        generate_old_answers(vllm, missing_samples, args.model_name, args.old_answers_path, args.max_new_tokens)
    else:
        dtype = get_torch_dtype(args.torch_dtype)

    samples, mapping_report = load_bridge_samples(
        args.data_path,
        args.bridge_root,
        args.old_answers_path,
        max_samples=args.max_samples,
        allow_missing_old_answers=False,
    )
    if not samples:
        raise RuntimeError("No Adapter-LGA samples loaded")

    with open(os.path.join(args.output_dir, "old_answer_mapping_report.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, ensure_ascii=False, indent=2)

    if vllm is None:
        vllm = load_vllm_for_edit(args.model_name, args.device)
        dtype = configure_model_dtype(vllm, args.torch_dtype)

    vllm.model.eval()
    vllm.model.requires_grad_(False)
    print("gradient_target=adapter_parameters_phi_L")
    print(f"base_requires_grad_params={count_trainable_params(vllm.model)}")

    accum: Dict[int, Dict[str, float]] = {
        layer: {
            "S_adapter_dot": 0.0,
            "S_adapter_cos": 0.0,
            "adapter_old_grad_norm": 0.0,
            "adapter_new_grad_norm": 0.0,
            "adapter_joint_norm": 0.0,
            "n_request": 0,
        }
        for layer in layers
    }

    sample_path = os.path.join(args.output_dir, "sample_adapter_layer_scores.jsonl")
    with open(sample_path, "w", encoding="utf-8") as sample_f:
        for layer in layers:
            set_all_seeds(args.seed)
            layer_path = adapter_layer_path(cfg, layer)
            layer_module = find_module(vllm.model, layer_path)
            adapter = create_adapter(vllm, cfg, args.device, dtype)
            print(f"[adapter] layer={layer} path={layer_path} adapter_trainable_params={count_trainable_params(adapter)}")
            hook = layer_module.register_forward_hook(adapter_hook_wrap(adapter))
            try:
                for sample_idx, sample in enumerate(samples, 1):
                    edit_reps, edit_mask, prompt_end = get_edit_signal(vllm, adapter, layer_path, sample)
                    adapter.set_edit_signal(edit_reps, edit_mask, prompt_end)
                    adapter.open_adaptor(True)

                    zero_adapter_grad(adapter)
                    old_loss = compute_adapter_target_loss(vllm, adapter, sample, str(sample.old_answer))
                    old_loss.backward()
                    old_grads = collect_old_grads({layer: adapter})

                    zero_adapter_grad(adapter)
                    new_loss = compute_adapter_target_loss(vllm, adapter, sample, sample.target_new)
                    new_loss.backward()
                    stats = compare_new_grads({layer: adapter}, old_grads)[layer]

                    accum[layer]["S_adapter_dot"] += stats["dot"]
                    accum[layer]["S_adapter_cos"] += stats["cos"]
                    accum[layer]["adapter_old_grad_norm"] += stats["old_norm"]
                    accum[layer]["adapter_new_grad_norm"] += stats["new_norm"]
                    accum[layer]["adapter_joint_norm"] += stats["joint_grad_norm"]
                    accum[layer]["n_request"] += 1

                    sample_f.write(
                        json.dumps(
                            {
                                "case_id": sample.case_id,
                                "image_id": sample.image_id,
                                "layer": layer,
                                "adapter_path": layer_path,
                                "old_answer": sample.old_answer,
                                "target_new": sample.target_new,
                                "old_loss": float(old_loss.detach().float().cpu().item()),
                                "new_loss": float(new_loss.detach().float().cpu().item()),
                                "s_adapter_dot": stats["dot"],
                                "s_adapter_cos": stats["cos"],
                                "adapter_old_grad_norm": stats["old_norm"],
                                "adapter_new_grad_norm": stats["new_norm"],
                                "adapter_joint_norm": stats["joint_grad_norm"],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    zero_adapter_grad(adapter)
                    adapter.open_adaptor(False)
                    print(f"[scan] layer={layer} sample={sample_idx}/{len(samples)}")
            finally:
                adapter.open_adaptor(False)
                hook.remove()
                del adapter
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
                "adapter_type": "VisionEditAdaptor",
                "adapter_path": adapter_layer_path(cfg, layer),
                "n_request": n_request,
                "S_adapter_dot": accum[layer]["S_adapter_dot"],
                "S_adapter_cos": accum[layer]["S_adapter_cos"] / n_request,
                "adapter_old_grad_norm": accum[layer]["adapter_old_grad_norm"] / n_request,
                "adapter_new_grad_norm": accum[layer]["adapter_new_grad_norm"] / n_request,
                "adapter_joint_norm": accum[layer]["adapter_joint_norm"] / n_request,
            }
        )
    rows = rank_adapter_rows(rows)
    write_adapter_csv(os.path.join(args.output_dir, "adapter_lga_layer_scores.csv"), rows)

    topk_payload = {
        "model": args.model_name,
        "data": "bridge30",
        "adapter_type": "VisionEditAdaptor",
        "layers": layers,
        "n_request": len(samples),
        **summarize_adapter_rows(rows),
    }
    with open(os.path.join(args.output_dir, "topk_adapter_layers.json"), "w", encoding="utf-8") as f:
        json.dump(topk_payload, f, ensure_ascii=False, indent=2)
    write_adapter_summary_md(os.path.join(args.output_dir, "summary.md"), args.model_name, rows)
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(json.dumps(topk_payload["selected_adapter_golden_layer"], ensure_ascii=False))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Request-only Bridge30 adapter-aware VLM LGA layer scan.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--vead-config-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", required=True)
    parser.add_argument("--old-answers-path", required=True)
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--adapter-type", default="vision", choices=["vision"])
    parser.add_argument("--score-mode", default="request_only_adapter_lga")
    parser.add_argument("--main-score", default="adapter_dot")
    parser.add_argument("--diagnostics", default="adapter_cos,adapter_grad_norm,adapter_norm_ratio")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--torch-dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--generate-old-answers-if-missing", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.score_mode != "request_only_adapter_lga":
        raise ValueError("Only request_only_adapter_lga is supported")
    if args.main_score != "adapter_dot":
        raise ValueError("Only adapter_dot is supported as the main Adapter-LGA score")
    run_adapter_lga_scan(args)


if __name__ == "__main__":
    main()
