import argparse
import csv
import json
import os
import sys
from pathlib import Path
from statistics import median
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [REPO_ROOT, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from bridge_vlm_adapter_lga_scan import (  # noqa: E402
    configure_model_dtype,
    count_trainable_params,
    get_edit_signal,
    get_torch_dtype,
    set_adapter_trainable,
    set_all_seeds,
    zero_adapter_grad,
)
from bridge_vlm_lga_scan import (  # noqa: E402
    EPS,
    detach_llm_inputs,
    generate_old_answers,
    load_bridge_samples,
    parse_layers,
)


def adapter_layer_path(cfg: Any, layer: int) -> str:
    return cfg.llm_layer_tmp.format(int(layer))


def instrumented_adapter_hook_wrap(adapter: Any):
    def adapter_hook(module, args, output):
        if isinstance(output, tuple):
            updated = list(output)
            updated[0] = adapter(updated[0])
            return tuple(updated)
        return adapter(output)

    return adapter_hook


def create_instrumented_adapter(vllm: Any, cfg: Any, device: str, dtype: Any):
    import torch
    from editor.vllm_editors.vead.adpt_model import VisionEditAdaptor

    class InstrumentedVisionEditAdaptor(VisionEditAdaptor):
        def clear_capture(self):
            self.captured_delta_h_vis = None

        def forward(self, layer_outpt):
            self.clear_capture()
            if (
                not self.is_open
                or layer_outpt.shape[1] == 1
                or not self.inpt_has_img
            ):
                return layer_outpt
            if self.inpt_vt_begin is None or self.inpt_vt_end is None:
                raise BaseException("Have not set vision token range.")

            img_reps = layer_outpt[:, self.inpt_vt_begin : self.inpt_vt_end].clone()
            b1, l1, _ = img_reps.shape
            b2, l2, _ = self.edit_reps.shape
            if l1 != self.img_tok_n:
                raise BaseException("Number of selected vision token error.")
            if b1 != b2:
                raise BaseException("Batch size of input and editing signal are not matched.")

            if self.add_it:
                prompt_last_token_of_edit_reps = self.edit_reps[range(len(self.prompt_end)), self.prompt_end]
                inf_map = self.influence_mapper(img_reps, prompt_last_token_of_edit_reps)
                inf_map = torch.sigmoid(inf_map).unsqueeze(-1)
            else:
                inf_map = 1

            norm_img_reps = self.ln_img_reps(img_reps)
            norm_edit_reps = self.ln_edit_reps(self.edit_reps)
            x = self.mlp_begin(norm_img_reps)
            q = self.cross_att_q_mlp(x).reshape(
                b1,
                l1,
                self.cross_att_head_n,
                self.mid_dim // self.cross_att_head_n,
            )
            k = self.cross_att_k_mlp(norm_edit_reps).reshape(
                b1,
                l2,
                self.cross_att_head_n,
                self.mid_dim // self.cross_att_head_n,
            )
            v = self.cross_att_v_mlp(norm_edit_reps).reshape(
                b1,
                l2,
                self.cross_att_head_n,
                self.mid_dim // self.cross_att_head_n,
            )
            s = torch.einsum("blhm,buhm->bhlu", q, k)
            s = s / (self.mid_dim // self.cross_att_head_n) ** 0.5
            s = s + (self.edit_reps_att_mask.reshape(b1, 1, 1, l2) - 1) * 9999999999
            s = torch.softmax(s, 3)
            x = torch.einsum("bhlu,buhm->blhm", s, v).reshape(b1, l1, self.mid_dim)
            delta_h_vis = self.mlp_end(x) * inf_map
            if delta_h_vis.requires_grad:
                delta_h_vis.retain_grad()
            self.captured_delta_h_vis = delta_h_vis
            layer_outpt[:, self.inpt_vt_begin : self.inpt_vt_end] = img_reps + delta_h_vis
            return layer_outpt

    adapter = InstrumentedVisionEditAdaptor(
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
    adapter.clear_capture()
    set_adapter_trainable(adapter, True)
    return adapter


def compute_adapter_output_target_loss(vllm: Any, adapter: Any, sample: Any, target: str):
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


def read_captured_delta_grad(adapter: Any):
    captured = getattr(adapter, "captured_delta_h_vis", None)
    if captured is None:
        raise RuntimeError("Adapter delta_h_vis was not captured")
    if captured.grad is None:
        raise RuntimeError("Adapter delta_h_vis gradient was not captured")
    return captured.grad.detach().float().cpu().contiguous()


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
        "old_nonzero_ratio": float((old_flat != 0).float().mean().item()),
        "new_nonzero_ratio": float((new_flat != 0).float().mean().item()),
    }


def rank_adapter_output_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for key, rank_key, descending in [
        ("S_out_dot", "out_dot_rank", True),
        ("S_out_dot", "out_conflict_rank", False),
        ("S_out_new_norm", "out_new_norm_rank", True),
        ("S_out_cos", "out_cos_rank", True),
        ("S_out_joint_norm", "out_joint_norm_rank", True),
    ]:
        ranked = sorted(rows, key=lambda row: float(row[key]), reverse=descending)
        for rank, row in enumerate(ranked, 1):
            row[rank_key] = rank
    for row in rows:
        row["adapter_output_lga_selected_by_dot"] = row["out_dot_rank"] == 1
    return sorted(rows, key=lambda row: row["out_dot_rank"])


def summarize_adapter_output_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_dot = sorted(rows, key=lambda row: row["out_dot_rank"])
    by_conflict = sorted(rows, key=lambda row: row["out_conflict_rank"])
    by_new_norm = sorted(rows, key=lambda row: row["out_new_norm_rank"])
    by_cos = sorted(rows, key=lambda row: row["out_cos_rank"])

    def layers(top_rows):
        return [int(row["layer"]) for row in top_rows]

    return {
        "main_score": "S_out_dot",
        "gradient_target": "adapter_output_delta_h_vis_L",
        "base_model_trainable": False,
        "adapter_used": True,
        "capture_object": "delta_h_vis",
        "diagnostic_scores": [
            "S_out_cos",
            "S_out_new_norm",
            "S_out_old_norm",
            "S_out_joint_norm",
            "out_positive_ratio",
            "median_out_dot",
        ],
        "top_by_out_dot": {
            "top1": int(by_dot[0]["layer"]),
            "top3": layers(by_dot[:3]),
            "top5": layers(by_dot[:5]),
        },
        "top_by_out_conflict_dot": {
            "top1": int(by_conflict[0]["layer"]),
            "top3": layers(by_conflict[:3]),
            "top5": layers(by_conflict[:5]),
        },
        "top_by_out_new_norm": {
            "top1": int(by_new_norm[0]["layer"]),
            "top3": layers(by_new_norm[:3]),
            "top5": layers(by_new_norm[:5]),
        },
        "top_by_out_cos": {
            "top1": int(by_cos[0]["layer"]),
            "top3": layers(by_cos[:3]),
            "top5": layers(by_cos[:5]),
        },
        "selected_adapter_output_layer": {
            "by": "S_out_dot",
            "top1": int(by_dot[0]["layer"]),
        },
    }


def write_adapter_output_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "layer",
        "adapter_path",
        "capture_object",
        "visual_token_start",
        "visual_token_end",
        "n_request",
        "S_out_dot",
        "S_out_cos",
        "S_out_new_norm",
        "S_out_old_norm",
        "S_out_joint_norm",
        "out_positive_ratio",
        "median_out_dot",
        "out_old_grad_nonzero_ratio",
        "out_new_grad_nonzero_ratio",
        "out_dot_rank",
        "out_conflict_rank",
        "out_new_norm_rank",
        "out_cos_rank",
        "out_joint_norm_rank",
        "adapter_output_lga_selected_by_dot",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_adapter_output_summary_md(path: str, model_name: str, rows: List[Dict[str, Any]]) -> None:
    dot_rows = sorted(rows, key=lambda row: row["out_dot_rank"])[:5]
    conflict_rows = sorted(rows, key=lambda row: row["out_conflict_rank"])[:5]
    new_norm_rows = sorted(rows, key=lambda row: row["out_new_norm_rank"])[:5]
    lines = [
        f"# Bridge30 {model_name} Adapter-Output LGA Summary",
        "",
        "Gradient target: `adapter_output_delta_h_vis_L`",
        "Capture object: `delta_h_vis`",
        "Adapter used: `true`",
        "Main score: `S_out_dot`",
        "",
        "## Dot Top-5",
        "",
        "| Dot Rank | Layer | S_out_dot | S_out_cos | New Norm | Joint Norm | Conflict Rank |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in dot_rows:
        lines.append(
            f"| {row['out_dot_rank']} | {row['layer']} | {row['S_out_dot']:.6g} | "
            f"{row['S_out_cos']:.6g} | {row['S_out_new_norm']:.6g} | "
            f"{row['S_out_joint_norm']:.6g} | {row['out_conflict_rank']} |"
        )
    lines.extend(
        [
            "",
            "## Conflict Dot Top-5",
            "",
            "| Conflict Rank | Layer | S_out_dot | S_out_cos | New Norm | Dot Rank |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in conflict_rows:
        lines.append(
            f"| {row['out_conflict_rank']} | {row['layer']} | {row['S_out_dot']:.6g} | "
            f"{row['S_out_cos']:.6g} | {row['S_out_new_norm']:.6g} | {row['out_dot_rank']} |"
        )
    lines.extend(
        [
            "",
            "## New-Norm Top-5",
            "",
            "| New-Norm Rank | Layer | S_out_new_norm | S_out_dot | S_out_cos | Joint Norm |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in new_norm_rows:
        lines.append(
            f"| {row['out_new_norm_rank']} | {row['layer']} | {row['S_out_new_norm']:.6g} | "
            f"{row['S_out_dot']:.6g} | {row['S_out_cos']:.6g} | {row['S_out_joint_norm']:.6g} |"
        )
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_adapter_output_lga_scan(args: argparse.Namespace) -> None:
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
        raise RuntimeError("No Adapter-Output LGA samples loaded")

    with open(os.path.join(args.output_dir, "old_answer_mapping_report.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, ensure_ascii=False, indent=2)

    if vllm is None:
        vllm = load_vllm_for_edit(args.model_name, args.device)
        dtype = configure_model_dtype(vllm, args.torch_dtype)

    vllm.model.eval()
    vllm.model.requires_grad_(False)
    print("gradient_target=adapter_output_delta_h_vis_L")
    print(f"base_requires_grad_params={count_trainable_params(vllm.model)}")
    print("adapter_used=True")

    accum: Dict[int, Dict[str, Any]] = {
        layer: {
            "S_out_dot": 0.0,
            "S_out_cos": 0.0,
            "S_out_new_norm": 0.0,
            "S_out_old_norm": 0.0,
            "S_out_joint_norm": 0.0,
            "positive_count": 0,
            "dots": [],
            "out_old_grad_nonzero_ratio": 0.0,
            "out_new_grad_nonzero_ratio": 0.0,
            "n_request": 0,
            "visual_spans": set(),
        }
        for layer in layers
    }

    sample_path = os.path.join(args.output_dir, "sample_adapter_output_scores.jsonl")
    with open(sample_path, "w", encoding="utf-8") as sample_f:
        for layer in layers:
            set_all_seeds(args.seed)
            layer_path = adapter_layer_path(cfg, layer)
            layer_module = find_module(vllm.model, layer_path)
            adapter = create_instrumented_adapter(vllm, cfg, args.device, dtype)
            print(
                f"[adapter-output] layer={layer} path={layer_path} "
                f"adapter_trainable_params={count_trainable_params(adapter)}"
            )
            hook = layer_module.register_forward_hook(instrumented_adapter_hook_wrap(adapter))
            try:
                for sample_idx, sample in enumerate(samples, 1):
                    edit_reps, edit_mask, prompt_end = get_edit_signal(vllm, adapter, layer_path, sample)
                    adapter.set_edit_signal(edit_reps, edit_mask, prompt_end)
                    adapter.open_adaptor(True)

                    zero_adapter_grad(adapter)
                    old_loss = compute_adapter_output_target_loss(vllm, adapter, sample, str(sample.old_answer))
                    old_loss.backward()
                    old_grad = read_captured_delta_grad(adapter)
                    old_span = (int(adapter.inpt_vt_begin), int(adapter.inpt_vt_end))

                    zero_adapter_grad(adapter)
                    new_loss = compute_adapter_output_target_loss(vllm, adapter, sample, sample.target_new)
                    new_loss.backward()
                    new_grad = read_captured_delta_grad(adapter)
                    new_span = (int(adapter.inpt_vt_begin), int(adapter.inpt_vt_end))
                    if old_span != new_span:
                        raise RuntimeError(f"Old/new visual spans differ: {old_span} vs {new_span}")

                    stats = grad_stats(old_grad, new_grad)
                    accum[layer]["S_out_dot"] += stats["dot"]
                    accum[layer]["S_out_cos"] += stats["cos"]
                    accum[layer]["S_out_new_norm"] += stats["new_norm"]
                    accum[layer]["S_out_old_norm"] += stats["old_norm"]
                    accum[layer]["S_out_joint_norm"] += stats["joint_norm"]
                    accum[layer]["positive_count"] += 1 if stats["dot"] > 0 else 0
                    accum[layer]["dots"].append(stats["dot"])
                    accum[layer]["out_old_grad_nonzero_ratio"] += stats["old_nonzero_ratio"]
                    accum[layer]["out_new_grad_nonzero_ratio"] += stats["new_nonzero_ratio"]
                    accum[layer]["n_request"] += 1
                    accum[layer]["visual_spans"].add(old_span)

                    sample_f.write(
                        json.dumps(
                            {
                                "case_id": sample.case_id,
                                "image_id": sample.image_id,
                                "layer": layer,
                                "adapter_path": layer_path,
                                "capture_object": args.capture_object,
                                "visual_token_start": old_span[0],
                                "visual_token_end": old_span[1],
                                "old_answer": sample.old_answer,
                                "target_new": sample.target_new,
                                "old_loss": float(old_loss.detach().float().cpu().item()),
                                "new_loss": float(new_loss.detach().float().cpu().item()),
                                "s_out_dot": stats["dot"],
                                "s_out_cos": stats["cos"],
                                "out_old_norm": stats["old_norm"],
                                "out_new_norm": stats["new_norm"],
                                "out_joint_norm": stats["joint_norm"],
                                "out_old_grad_nonzero_ratio": stats["old_nonzero_ratio"],
                                "out_new_grad_nonzero_ratio": stats["new_nonzero_ratio"],
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
        spans = sorted(accum[layer]["visual_spans"])
        span_start = spans[0][0] if len(spans) == 1 else "mixed"
        span_end = spans[0][1] if len(spans) == 1 else "mixed"
        rows.append(
            {
                "model": args.model_name,
                "layer": layer,
                "adapter_path": adapter_layer_path(cfg, layer),
                "capture_object": args.capture_object,
                "visual_token_start": span_start,
                "visual_token_end": span_end,
                "n_request": n_request,
                "S_out_dot": accum[layer]["S_out_dot"],
                "S_out_cos": accum[layer]["S_out_cos"] / n_request,
                "S_out_new_norm": accum[layer]["S_out_new_norm"] / n_request,
                "S_out_old_norm": accum[layer]["S_out_old_norm"] / n_request,
                "S_out_joint_norm": accum[layer]["S_out_joint_norm"] / n_request,
                "out_positive_ratio": accum[layer]["positive_count"] / n_request,
                "median_out_dot": float(median(accum[layer]["dots"])),
                "out_old_grad_nonzero_ratio": accum[layer]["out_old_grad_nonzero_ratio"] / n_request,
                "out_new_grad_nonzero_ratio": accum[layer]["out_new_grad_nonzero_ratio"] / n_request,
            }
        )
    rows = rank_adapter_output_rows(rows)
    write_adapter_output_csv(os.path.join(args.output_dir, "adapter_output_lga_layer_scores.csv"), rows)

    topk_payload = {
        "model": args.model_name,
        "data": "bridge30",
        "layers": layers,
        "n_request": len(samples),
        "adapter_type": "InstrumentedVisionEditAdaptor",
        **summarize_adapter_output_rows(rows),
    }
    with open(os.path.join(args.output_dir, "topk_adapter_output_layers.json"), "w", encoding="utf-8") as f:
        json.dump(topk_payload, f, ensure_ascii=False, indent=2)
    write_adapter_output_summary_md(os.path.join(args.output_dir, "summary.md"), args.model_name, rows)
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(json.dumps(topk_payload["selected_adapter_output_layer"], ensure_ascii=False))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Request-only Bridge30 adapter-output VLM LGA layer scan.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--vead-config-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", required=True)
    parser.add_argument("--old-answers-path", required=True)
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--adapter-type", default="vision", choices=["vision"])
    parser.add_argument("--capture-object", default="delta_h_vis", choices=["delta_h_vis"])
    parser.add_argument("--score-mode", default="request_only_adapter_output_lga")
    parser.add_argument("--main-score", default="out_dot")
    parser.add_argument(
        "--diagnostics",
        default="out_cos,out_new_norm,out_old_norm,out_joint_norm,positive_ratio,median_dot",
    )
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
    if args.score_mode != "request_only_adapter_output_lga":
        raise ValueError("Only request_only_adapter_output_lga is supported")
    if args.main_score != "out_dot":
        raise ValueError("Only out_dot is supported as the main Adapter-Output LGA score")
    run_adapter_output_lga_scan(args)


if __name__ == "__main__":
    main()
