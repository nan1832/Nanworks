import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple


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
from bridge_vlm_adapter_output_lga_scan import (  # noqa: E402
    adapter_layer_path,
    instrumented_adapter_hook_wrap,
)
from bridge_vlm_lga_scan import (  # noqa: E402
    ANSWER_STUB,
    EPS,
    choose_old_answer,
    detach_llm_inputs,
    ensure_answer_stub,
    image_id_from_path,
    load_old_answers,
    parse_layers,
    read_jsonl,
    resolve_bridge_image_path,
)


@dataclass
class ComponentSample:
    component_id: str
    case_id: str
    family: str
    image_id: str
    prompt: str
    target: str
    image_path: Optional[str]
    image: Any

    @property
    def target_new(self) -> str:
        return self.target


@dataclass
class RelGenLocCase:
    case_id: str
    entity_name: str
    request: ComponentSample
    request_old_answer: str
    generality: List[Tuple[str, ComponentSample, str]]
    locality: Optional[ComponentSample]


def short_model_name(model_name: str) -> str:
    raw = model_name.lower()
    if "llava" in raw:
        return "llava"
    if "blip2" in raw:
        return "blip2"
    return raw.replace("/", "_").replace("\\", "_")


def default_request_old_answers_path(data_path: str, model_name: str) -> str:
    data_dir = Path(data_path).resolve().parent
    return str(
        data_dir
        / "beforeedit"
        / "open_end"
        / f"bridge_train_entity_recognition_{short_model_name(model_name)}.jsonl"
    )


def make_component(
    raw: Dict[str, Any],
    bridge_root: str,
    case_id: str,
    family: str,
    index: int,
) -> Optional[ComponentSample]:
    from PIL import Image

    rel_image = raw.get("image")
    image = None
    image_path = None
    image_id = "text_only"
    if rel_image:
        image_path = resolve_component_image_path(str(rel_image), bridge_root)
        image_id = image_id_from_path(str(rel_image))
        image = Image.open(image_path).convert("RGB")
    return ComponentSample(
        component_id=f"{case_id}:{family}:{index}",
        case_id=case_id,
        family=family,
        image_id=image_id,
        prompt=ensure_answer_stub(str(raw["prompt"])),
        target=str(raw.get("target") or raw.get("target_new") or ""),
        image_path=image_path,
        image=image,
    )


def resolve_component_image_path(rel_path: str, bridge_root: str) -> str:
    primary = resolve_bridge_image_path(rel_path, bridge_root)
    if os.path.exists(primary):
        return primary

    candidates = []
    if rel_path.startswith("val2014/"):
        candidates.append(REPO_ROOT / "data" / "easy-edit-mm" / "images" / rel_path)
        candidates.append(REPO_ROOT.parent / "data" / "easy-edit-mm" / "images" / rel_path)

    for candidate in candidates:
        if os.path.exists(candidate):
            return str(candidate)
    return primary


def load_relgenloc_cases(
    data_path: str,
    bridge_root: str,
    model_name: str,
    old_answers_path: Optional[str],
    max_samples: Optional[int],
    generality_mode: str,
    locality_mode: str,
) -> Tuple[List[RelGenLocCase], Dict[str, Any]]:
    with open(data_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    if old_answers_path is None:
        old_answers_path = default_request_old_answers_path(data_path, model_name)
    old_grouped, duplicate_image_ids = load_old_answers(old_answers_path)

    selected_items = raw_items[:max_samples] if max_samples is not None else raw_items
    cases: List[RelGenLocCase] = []
    missing_request_old: List[Dict[str, str]] = []
    skipped_no_image_loc = 0

    for idx, item in enumerate(selected_items):
        case_id = str(item.get("case_id", f"bridge_{idx}"))
        entity_name = str(item.get("entity_name") or item["request"]["target_new"])
        request = make_component(item["request"], bridge_root, case_id, "request", 0)
        if request is None:
            continue
        request_old = ""
        if request.image_id in old_grouped:
            request_old = str(
                choose_old_answer(old_grouped[request.image_id], item["request"]["prompt"]).get("answer", "")
            ).strip()
        if not request_old:
            missing_request_old.append({"case_id": case_id, "image_id": request.image_id})
            continue

        gen_components: List[Tuple[str, ComponentSample, str]] = []
        for family in ["text_rephrase", "image_rephrase"]:
            raw_gen_items = item.get("generality", {}).get(family, [])
            if generality_mode == "first_per_family":
                raw_gen_items = raw_gen_items[:1]
            for gen_idx, raw_gen in enumerate(raw_gen_items):
                component = make_component(raw_gen, bridge_root, case_id, f"generality.{family}", gen_idx)
                if component is not None and component.image is not None:
                    gen_components.append((family, component, ""))

        locality = None
        raw_loc_items = item.get("locality", {}).get("image_loc", [])
        if locality_mode == "image_loc_first_only":
            raw_loc_items = raw_loc_items[:1]
        for loc_idx, raw_loc in enumerate(raw_loc_items):
            component = make_component(raw_loc, bridge_root, case_id, "locality.image_loc", loc_idx)
            if component is not None and component.image is not None:
                locality = component
                break
        if locality is None:
            skipped_no_image_loc += 1

        cases.append(
            RelGenLocCase(
                case_id=case_id,
                entity_name=entity_name,
                request=request,
                request_old_answer=request_old,
                generality=gen_components,
                locality=locality,
            )
        )

    report = {
        "old_answer_source": old_answers_path,
        "total_cases": len(selected_items),
        "loaded_cases": len(cases),
        "missing_request_old": missing_request_old,
        "duplicate_image_ids": duplicate_image_ids,
        "generality_mode": generality_mode,
        "locality_mode": locality_mode,
        "skipped_no_image_loc": skipped_no_image_loc,
    }
    if missing_request_old:
        raise RuntimeError(f"Missing request old answers for {len(missing_request_old)} cases")
    if not cases:
        raise RuntimeError("No RelGenLoc cases loaded")
    return cases, report


def create_multi_capture_adapter(vllm: Any, cfg: Any, device: str, dtype: Any):
    import torch
    from editor.vllm_editors.vead.adpt_model import VisionEditAdaptor

    class MultiCaptureVisionEditAdaptor(VisionEditAdaptor):
        def clear_capture(self):
            self.captured_delta_h_vis_list = []

        def forward(self, layer_outpt):
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
                prompt_last_token = self.edit_reps[range(len(self.prompt_end)), self.prompt_end]
                inf_map = self.influence_mapper(img_reps, prompt_last_token)
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
            self.captured_delta_h_vis_list.append(delta_h_vis)
            layer_outpt[:, self.inpt_vt_begin : self.inpt_vt_end] = img_reps + delta_h_vis
            return layer_outpt

    adapter = MultiCaptureVisionEditAdaptor(
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


def load_vead_config_for_scan(fpath: str):
    import yaml
    from editor.vllm_editors.vead.vead import VEADConfig

    with open(fpath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data = dict(data)
    data.pop("port_lambda", None)
    data.pop("port_sample_n", None)
    data["train_cfg"] = VEADConfig.TrainConfig(**data["train_cfg"])
    data["IT"] = VEADConfig.InfluenceTrace(**data["IT"])
    return VEADConfig(**data)


def component_target_loss(vllm: Any, adapter: Any, component: ComponentSample, target: str):
    img_arg = None if component.image is None else [component.image]
    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [component.prompt],
        img_arg,
        [target],
    )
    llm_inpt = detach_llm_inputs(llm_inpt)
    if vt_range is None:
        adapter.set_input_info(False, None, None)
    else:
        adapter.set_input_info(True, int(vt_range[0]), int(vt_range[1]))
    output = vllm.get_llm_outpt(llm_inpt, vt_range)
    return vllm.label_loss(output.logits, label_ids, label_masks, average=True)


def component_logits(vllm: Any, adapter: Any, component: ComponentSample, target: str):
    img_arg = None if component.image is None else [component.image]
    (llm_inpt, vt_range), label_ids, label_masks = vllm.prompts_imgs_target_to_xym(
        [component.prompt],
        img_arg,
        [target],
    )
    llm_inpt = detach_llm_inputs(llm_inpt)
    if vt_range is None:
        adapter.set_input_info(False, None, None)
    else:
        adapter.set_input_info(True, int(vt_range[0]), int(vt_range[1]))
    output = vllm.get_llm_outpt(llm_inpt, vt_range)
    return output.logits, label_masks


def locality_kl_loss(vllm: Any, adapter: Any, component: ComponentSample):
    import torch

    adapter.open_adaptor(False)
    with torch.no_grad():
        pre_logits, label_masks = component_logits(vllm, adapter, component, component.target)
        pre_logits = pre_logits.detach()
    adapter.open_adaptor(True)
    post_logits, post_masks = component_logits(vllm, adapter, component, component.target)
    if post_masks.shape != label_masks.shape:
        raise RuntimeError("Locality label masks differ between pre and post passes")
    return vllm.logit_KL_loss(pre_logits, post_logits, label_masks, average=True)


def generate_answer_for_component(vllm: Any, model_name: str, component: ComponentSample, max_new_tokens: int) -> str:
    import torch

    question = component.prompt.replace(ANSWER_STUB, "").strip()
    if "llava" in model_name.lower():
        if component.image is None:
            prompt = f"USER: {question}\nAnswer briefly.\nASSISTANT:"
            inputs = vllm.processor(prompt, return_tensors="pt").to(vllm.device)
        else:
            prompt = f"USER: <image>\n{question}\nAnswer briefly with the bridge name only.\nASSISTANT:"
            inputs = vllm.processor(prompt, component.image, return_tensors="pt").to(vllm.device)
        with torch.no_grad():
            generated = vllm.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = vllm.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        if "ASSISTANT:" in text:
            text = text.split("ASSISTANT:", 1)[1].strip()
        return text or "unknown"

    prompts = [
        f"Question: {question} Answer briefly with the bridge name only. Answer:",
        f"{question} Answer:",
        question,
        "This bridge is called",
    ]
    for prompt in prompts:
        if component.image is None:
            continue
        inputs = vllm.processor(component.image, prompt, return_tensors="pt").to(vllm.device)
        with torch.no_grad():
            generated = vllm.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = vllm.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        if text:
            return text
    return "unknown"


def attach_generality_old_answers(
    vllm: Any,
    model_name: str,
    cases: List[RelGenLocCase],
    cache_path: str,
    max_new_tokens: int,
) -> None:
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    cached: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(cache_path):
        for row in read_jsonl(cache_path):
            answer = str(row.get("answer") or "").strip()
            component_id = str(row.get("component_id") or "").strip()
            if answer and component_id:
                cached[component_id] = row

    rows = list(cached.values())
    for case in cases:
        updated: List[Tuple[str, ComponentSample, str]] = []
        for family, component, _ in case.generality:
            answer = str(cached.get(component.component_id, {}).get("answer") or "").strip()
            if not answer:
                answer = generate_answer_for_component(vllm, model_name, component, max_new_tokens)
                row = {
                    "component_id": component.component_id,
                    "case_id": case.case_id,
                    "family": family,
                    "image_id": component.image_id,
                    "question": component.prompt.replace(ANSWER_STUB, ""),
                    "answer": answer,
                }
                rows.append(row)
                cached[component.component_id] = row
                print(f"[generality-old-answer] {component.component_id}: {answer}")
            updated.append((family, component, answer))
        case.generality = updated

    with open(cache_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def captured_grads(adapter: Any) -> List[Any]:
    captures = getattr(adapter, "captured_delta_h_vis_list", [])
    grads = []
    for captured in captures:
        if captured.grad is None:
            raise RuntimeError("A captured delta_h_vis tensor has no gradient")
        grads.append(captured.grad.detach().float().cpu().contiguous())
    return grads


def concat_grads(grads: Sequence[Any]):
    import torch

    if not grads:
        return torch.zeros(1, dtype=torch.float32)
    return torch.cat([grad.reshape(-1).float() for grad in grads])


def vector_stats(old_vec: Any, new_vec: Any) -> Dict[str, float]:
    import torch

    if old_vec.numel() != new_vec.numel():
        raise RuntimeError(f"Gradient vector lengths differ: {old_vec.numel()} vs {new_vec.numel()}")
    dot = float(torch.sum(old_vec * new_vec).item())
    old_norm = float(torch.linalg.vector_norm(old_vec).item())
    new_norm = float(torch.linalg.vector_norm(new_vec).item())
    joint = old_norm * new_norm
    return {
        "dot": dot,
        "cos": dot / (joint + EPS),
        "old_norm": old_norm,
        "new_norm": new_norm,
        "joint_norm": joint,
        "old_nonzero_ratio": float((old_vec != 0).float().mean().item()),
        "new_nonzero_ratio": float((new_vec != 0).float().mean().item()),
    }


def compute_side_loss(
    vllm: Any,
    adapter: Any,
    case: RelGenLocCase,
    side: str,
    weights: Dict[str, float],
) -> Tuple[Any, List[str]]:
    adapter.clear_capture()
    adapter.open_adaptor(True)
    losses = []
    labels: List[str] = []

    entity_target = case.request_old_answer if side == "old" else case.request.target
    if weights["entity"] > 0:
        losses.append(component_target_loss(vllm, adapter, case.request, entity_target) * weights["entity"])
        labels.append("entity")

    gen_losses = []
    gen_labels = []
    for family, component, old_answer in case.generality:
        target = old_answer if side == "old" else component.target
        gen_losses.append(component_target_loss(vllm, adapter, component, target))
        gen_labels.append(f"generality.{family}")
    if gen_losses and weights["generality"] > 0:
        losses.append(sum(gen_losses) / len(gen_losses) * weights["generality"])
        labels.extend(gen_labels)

    if case.locality is not None and weights["locality"] > 0:
        losses.append(locality_kl_loss(vllm, adapter, case.locality) * weights["locality"])
        labels.append("locality")

    if not losses:
        raise RuntimeError("No losses were built for RelGenLoc side")
    return sum(losses), labels


def compute_case_layer_scores(
    vllm: Any,
    adapter: Any,
    case: RelGenLocCase,
    weights: Dict[str, float],
) -> Dict[str, float]:
    old_loss, old_labels = compute_side_loss(vllm, adapter, case, "old", weights)
    old_loss_value = float(old_loss.detach().float().cpu().item())
    old_loss.backward()
    old_grads = captured_grads(adapter)

    zero_adapter_grad(adapter)
    new_loss, new_labels = compute_side_loss(vllm, adapter, case, "new", weights)
    new_loss_value = float(new_loss.detach().float().cpu().item())
    new_loss.backward()
    new_grads = captured_grads(adapter)

    if old_labels != new_labels:
        raise RuntimeError(f"Old/new component labels differ: {old_labels} vs {new_labels}")
    if len(old_grads) != len(new_grads):
        raise RuntimeError(f"Old/new captured gradient counts differ: {len(old_grads)} vs {len(new_grads)}")

    def by_label(prefix: str, grads: Sequence[Any]) -> List[Any]:
        return [grad for label, grad in zip(old_labels, grads) if label == prefix or label.startswith(prefix + ".")]

    total_stats = vector_stats(concat_grads(old_grads), concat_grads(new_grads))
    entity_stats = vector_stats(concat_grads(by_label("entity", old_grads)), concat_grads(by_label("entity", new_grads)))
    gen_stats = vector_stats(
        concat_grads(by_label("generality", old_grads)),
        concat_grads(by_label("generality", new_grads)),
    )
    loc_stats = vector_stats(
        concat_grads(by_label("locality", old_grads)),
        concat_grads(by_label("locality", new_grads)),
    )
    eg_old = concat_grads(by_label("entity", old_grads) + by_label("generality", old_grads))
    eg_new = concat_grads(by_label("entity", new_grads) + by_label("generality", new_grads))
    eg_stats = vector_stats(eg_old, eg_new)

    return {
        "old_loss": old_loss_value,
        "new_loss": new_loss_value,
        "s_total_norm": total_stats["new_norm"],
        "s_total_dot": total_stats["dot"],
        "s_total_cos": total_stats["cos"],
        "s_entity_norm": entity_stats["new_norm"],
        "s_generality_norm": gen_stats["new_norm"],
        "s_locality_norm": loc_stats["new_norm"],
        "s_entity_dot": entity_stats["dot"],
        "s_generality_dot": gen_stats["dot"],
        "s_eg_conflict": -eg_stats["dot"],
        "total_old_grad_nonzero_ratio": total_stats["old_nonzero_ratio"],
        "total_new_grad_nonzero_ratio": total_stats["new_nonzero_ratio"],
    }


def rank_relgenloc_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rank_specs = [
        ("S_total_norm", "total_norm_rank", True),
        ("S_total_dot", "total_dot_rank", True),
        ("S_total_cos", "total_cos_rank", True),
        ("S_eg_conflict", "eg_conflict_rank", True),
        ("S_entity_norm", "entity_norm_rank", True),
        ("S_generality_norm", "generality_norm_rank", True),
        ("S_locality_norm", "locality_norm_rank", True),
    ]
    for key, rank_key, descending in rank_specs:
        ranked = sorted(rows, key=lambda row: float(row[key]), reverse=descending)
        for rank, row in enumerate(ranked, 1):
            row[rank_key] = rank
    return sorted(rows, key=lambda row: row["total_norm_rank"])


def top_layers(rows: List[Dict[str, Any]], rank_key: str, k: int = 5, exclude_zero: bool = False) -> List[int]:
    ranked = sorted(rows, key=lambda row: row[rank_key])
    layers = []
    for row in ranked:
        if exclude_zero and row.get("zero_grad_flag"):
            continue
        layers.append(int(row["layer"]))
        if len(layers) >= k:
            break
    return layers


def summarize_relgenloc_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    zero_grad_layers = [int(row["layer"]) for row in rows if row.get("zero_grad_flag")]
    pool: List[int] = []
    for rank_key in ["total_norm_rank", "total_cos_rank", "eg_conflict_rank"]:
        for layer in top_layers(rows, rank_key, 5, exclude_zero=True):
            if layer not in pool:
                pool.append(layer)
    return {
        "main_score": "S_total_norm",
        "gradient_target": "adapter_output_delta_h_vis",
        "loss_mode": "relgenloc",
        "base_model_trainable": False,
        "adapter_used": True,
        "primary_total_norm_topk": top_layers(rows, "total_norm_rank", 5),
        "total_dot_topk": top_layers(rows, "total_dot_rank", 5),
        "total_cos_topk": top_layers(rows, "total_cos_rank", 5),
        "eg_conflict_topk": top_layers(rows, "eg_conflict_rank", 5),
        "entity_norm_topk": top_layers(rows, "entity_norm_rank", 5),
        "generality_norm_topk": top_layers(rows, "generality_norm_rank", 5),
        "locality_norm_topk": top_layers(rows, "locality_norm_rank", 5),
        "zero_grad_layers": zero_grad_layers,
        "recommended_candidate_pool": pool,
    }


def write_layer_scores_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "layer",
        "gradient_target",
        "adapter_path",
        "n_cases",
        "n_entity",
        "n_generality",
        "n_locality",
        "S_total_norm",
        "S_total_dot",
        "S_total_cos",
        "S_entity_norm",
        "S_generality_norm",
        "S_locality_norm",
        "S_entity_dot",
        "S_generality_dot",
        "S_eg_conflict",
        "total_old_grad_nonzero_ratio",
        "total_new_grad_nonzero_ratio",
        "median_total_norm",
        "zero_grad_flag",
        "nan_flag",
        "total_norm_rank",
        "total_dot_rank",
        "total_cos_rank",
        "eg_conflict_rank",
        "entity_norm_rank",
        "generality_norm_rank",
        "locality_norm_rank",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_summary_md(path: str, model_name: str, rows: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    top_norm = sorted(rows, key=lambda row: row["total_norm_rank"])[:5]
    top_cos = sorted(rows, key=lambda row: row["total_cos_rank"])[:5]
    top_conflict = sorted(rows, key=lambda row: row["eg_conflict_rank"])[:5]
    lines = [
        f"# Bridge30 {model_name} RelGenLoc Adapter GLA Summary",
        "",
        "Gradient target: `adapter_output_delta_h_vis`",
        "Loss mode: `1 * Entity + 1 * Generality + 1 * Locality`",
        "Main score: `S_total_norm`",
        f"Recommended candidate pool: `{summary['recommended_candidate_pool']}`",
        f"Zero-gradient layers: `{summary['zero_grad_layers']}`",
        "",
        "## Total-Norm Top-5",
        "",
        "| Rank | Layer | S_total_norm | S_total_dot | S_total_cos | Entity | Generality | Locality |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in top_norm:
        lines.append(
            f"| {row['total_norm_rank']} | {row['layer']} | {row['S_total_norm']:.6g} | "
            f"{row['S_total_dot']:.6g} | {row['S_total_cos']:.6g} | "
            f"{row['S_entity_norm']:.6g} | {row['S_generality_norm']:.6g} | "
            f"{row['S_locality_norm']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Total-Cos Top-5",
            "",
            "| Rank | Layer | S_total_cos | S_total_norm | S_eg_conflict |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top_cos:
        lines.append(
            f"| {row['total_cos_rank']} | {row['layer']} | {row['S_total_cos']:.6g} | "
            f"{row['S_total_norm']:.6g} | {row['S_eg_conflict']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Entity+Generality Conflict Top-5",
            "",
            "| Rank | Layer | S_eg_conflict | S_total_norm | S_total_cos |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top_conflict:
        lines.append(
            f"| {row['eg_conflict_rank']} | {row['layer']} | {row['S_eg_conflict']:.6g} | "
            f"{row['S_total_norm']:.6g} | {row['S_total_cos']:.6g} |"
        )
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_relgenloc_scan(args: argparse.Namespace) -> None:
    import torch
    from utils import find_module, load_vllm_for_edit

    os.makedirs(args.output_dir, exist_ok=True)
    layers = parse_layers(args.layers)
    cfg = load_vead_config_for_scan(args.vead_config_path)
    weights = {
        "entity": float(args.entity_weight),
        "generality": float(args.generality_weight),
        "locality": float(args.locality_weight),
    }
    if float(args.portability_weight) != 0.0:
        raise ValueError("RelGenLoc GLA for bridge-only-vis requires portability_weight=0")

    cases, data_report = load_relgenloc_cases(
        args.data_path,
        args.bridge_root,
        args.model_name,
        args.old_answers_path,
        args.max_samples,
        args.generality_mode,
        args.locality_mode,
    )
    with open(os.path.join(args.output_dir, "old_answer_mapping_report.json"), "w", encoding="utf-8") as f:
        json.dump(data_report, f, ensure_ascii=False, indent=2)

    vllm = load_vllm_for_edit(args.model_name, args.device)
    dtype = configure_model_dtype(vllm, args.torch_dtype)
    vllm.model.eval()
    vllm.model.requires_grad_(False)

    if args.generality_old_answers_path is None:
        args.generality_old_answers_path = os.path.join(
            args.output_dir,
            f"generality_old_answers_{short_model_name(args.model_name)}.jsonl",
        )
    attach_generality_old_answers(
        vllm,
        args.model_name,
        cases,
        args.generality_old_answers_path,
        args.max_new_tokens,
    )

    print("gradient_target=adapter_output_delta_h_vis")
    print("loss_mode=relgenloc")
    print(f"entity_weight={weights['entity']}")
    print(f"generality_weight={weights['generality']}")
    print(f"locality_weight={weights['locality']}")
    print(f"base_requires_grad_params={count_trainable_params(vllm.model)}")
    print("adapter_used=True")

    accum: Dict[int, Dict[str, Any]] = {
        layer: {
            "S_total_norm": 0.0,
            "S_total_dot": 0.0,
            "S_total_cos": 0.0,
            "S_entity_norm": 0.0,
            "S_generality_norm": 0.0,
            "S_locality_norm": 0.0,
            "S_entity_dot": 0.0,
            "S_generality_dot": 0.0,
            "S_eg_conflict": 0.0,
            "total_old_grad_nonzero_ratio": 0.0,
            "total_new_grad_nonzero_ratio": 0.0,
            "total_norms": [],
            "n_cases": 0,
            "n_entity": 0,
            "n_generality": 0,
            "n_locality": 0,
        }
        for layer in layers
    }

    sample_path = os.path.join(args.output_dir, "sample_component_scores.jsonl")
    with open(sample_path, "w", encoding="utf-8") as sample_f:
        for layer in layers:
            set_all_seeds(args.seed)
            layer_path = adapter_layer_path(cfg, layer)
            layer_module = find_module(vllm.model, layer_path)
            adapter = create_multi_capture_adapter(vllm, cfg, args.device, dtype)
            print(
                f"[relgenloc-gla] layer={layer} path={layer_path} "
                f"adapter_trainable_params={count_trainable_params(adapter)}"
            )
            hook = layer_module.register_forward_hook(instrumented_adapter_hook_wrap(adapter))
            try:
                for sample_idx, case in enumerate(cases, 1):
                    edit_reps, edit_mask, prompt_end = get_edit_signal(vllm, adapter, layer_path, case.request)
                    adapter.set_edit_signal(edit_reps, edit_mask, prompt_end)

                    zero_adapter_grad(adapter)
                    scores = compute_case_layer_scores(vllm, adapter, case, weights)
                    zero_adapter_grad(adapter)
                    adapter.open_adaptor(False)

                    for key in [
                        "S_total_norm",
                        "S_total_dot",
                        "S_total_cos",
                        "S_entity_norm",
                        "S_generality_norm",
                        "S_locality_norm",
                        "S_entity_dot",
                        "S_generality_dot",
                        "S_eg_conflict",
                        "total_old_grad_nonzero_ratio",
                        "total_new_grad_nonzero_ratio",
                    ]:
                        sample_key = key[0].lower() + key[1:] if key.startswith("S_") else key
                        if sample_key in scores:
                            accum[layer][key] += float(scores[sample_key])
                    accum[layer]["total_norms"].append(float(scores["s_total_norm"]))
                    accum[layer]["n_cases"] += 1
                    accum[layer]["n_entity"] += 1
                    accum[layer]["n_generality"] += len(case.generality)
                    accum[layer]["n_locality"] += 1 if case.locality is not None else 0

                    sample_f.write(
                        json.dumps(
                            {
                                "case_id": case.case_id,
                                "layer": layer,
                                "adapter_path": layer_path,
                                "request_old_answer": case.request_old_answer,
                                "request_target_new": case.request.target,
                                "n_generality": len(case.generality),
                                "has_locality": case.locality is not None,
                                **scores,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    print(f"[scan] layer={layer} sample={sample_idx}/{len(cases)}")
            finally:
                adapter.open_adaptor(False)
                hook.remove()
                del adapter
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    rows: List[Dict[str, Any]] = []
    for layer in layers:
        n_cases = int(accum[layer]["n_cases"])
        if n_cases <= 0:
            raise RuntimeError(f"No scores accumulated for layer {layer}")
        total_norm = accum[layer]["S_total_norm"] / n_cases
        values = [
            total_norm,
            accum[layer]["S_total_dot"],
            accum[layer]["S_total_cos"] / n_cases,
            accum[layer]["S_entity_norm"] / n_cases,
            accum[layer]["S_generality_norm"] / n_cases,
            accum[layer]["S_locality_norm"] / n_cases,
            accum[layer]["S_entity_dot"],
            accum[layer]["S_generality_dot"],
            accum[layer]["S_eg_conflict"],
        ]
        nan_flag = any(not math.isfinite(float(value)) for value in values)
        rows.append(
            {
                "model": args.model_name,
                "layer": layer,
                "gradient_target": args.gradient_target,
                "adapter_path": adapter_layer_path(cfg, layer),
                "n_cases": n_cases,
                "n_entity": int(accum[layer]["n_entity"]),
                "n_generality": int(accum[layer]["n_generality"]),
                "n_locality": int(accum[layer]["n_locality"]),
                "S_total_norm": total_norm,
                "S_total_dot": accum[layer]["S_total_dot"],
                "S_total_cos": accum[layer]["S_total_cos"] / n_cases,
                "S_entity_norm": accum[layer]["S_entity_norm"] / n_cases,
                "S_generality_norm": accum[layer]["S_generality_norm"] / n_cases,
                "S_locality_norm": accum[layer]["S_locality_norm"] / n_cases,
                "S_entity_dot": accum[layer]["S_entity_dot"],
                "S_generality_dot": accum[layer]["S_generality_dot"],
                "S_eg_conflict": accum[layer]["S_eg_conflict"],
                "total_old_grad_nonzero_ratio": accum[layer]["total_old_grad_nonzero_ratio"] / n_cases,
                "total_new_grad_nonzero_ratio": accum[layer]["total_new_grad_nonzero_ratio"] / n_cases,
                "median_total_norm": float(median(accum[layer]["total_norms"])),
                "zero_grad_flag": total_norm <= EPS,
                "nan_flag": nan_flag,
            }
        )

    rows = rank_relgenloc_rows(rows)
    layer_scores_path = os.path.join(args.output_dir, "layer_scores.csv")
    write_layer_scores_csv(layer_scores_path, rows)
    summary = summarize_relgenloc_rows(rows)
    topk_payload = {
        "model": args.model_name,
        "data": "bridge30",
        "layers": layers,
        "n_cases": len(cases),
        "adapter_type": "MultiCaptureVisionEditAdaptor",
        **summary,
    }
    with open(os.path.join(args.output_dir, "topk_layers.json"), "w", encoding="utf-8") as f:
        json.dump(topk_payload, f, ensure_ascii=False, indent=2)
    write_summary_md(os.path.join(args.output_dir, "summary.md"), args.model_name, rows, topk_payload)
    run_config = vars(args).copy()
    run_config.update(
        {
            "loss_mode": "relgenloc",
            "entity_weight": weights["entity"],
            "generality_weight": weights["generality"],
            "locality_weight": weights["locality"],
            "fluency_weight": 0.0,
            "include_influence_mapper_in_main_score": False,
            "base_requires_grad_params": 0,
            "adapter_used": True,
        }
    )
    with open(os.path.join(args.output_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(run_config, f, ensure_ascii=False, indent=2)
    print(json.dumps(topk_payload, ensure_ascii=False, indent=2))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge30 RelGenLoc adapter-output GLA layer scan.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--vead-config-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--bridge-root", required=True)
    parser.add_argument("--old-answers-path", default=None)
    parser.add_argument("--generality-old-answers-path", default=None)
    parser.add_argument("--layers", default="0-31")
    parser.add_argument("--gradient-target", default="adapter_output_delta_h_vis")
    parser.add_argument("--loss-mode", default="relgenloc")
    parser.add_argument("--entity-weight", type=float, default=1.0)
    parser.add_argument("--generality-weight", type=float, default=1.0)
    parser.add_argument("--locality-weight", type=float, default=1.0)
    parser.add_argument("--portability-weight", type=float, default=0.0)
    parser.add_argument("--generality-mode", default="first_per_family", choices=["first_per_family", "all"])
    parser.add_argument("--locality-mode", default="image_loc_first_only", choices=["image_loc_first_only"])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--torch-dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.loss_mode != "relgenloc":
        raise ValueError("Only relgenloc loss mode is supported")
    if args.gradient_target != "adapter_output_delta_h_vis":
        raise ValueError("Only adapter_output_delta_h_vis is supported")
    run_relgenloc_scan(args)


if __name__ == "__main__":
    main()
