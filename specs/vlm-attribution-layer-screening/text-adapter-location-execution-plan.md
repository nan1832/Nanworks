# Text Adapter Location Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-stage bridge-name-recognition experiment pipeline for `llava-v1.5-7b` that first runs Scheme 2 (layer-16 text adapter baseline with anchor-only editing) and then runs Scheme 1 (same setup plus explicit bridge-anchor representation alignment), using the same bridge data and the same evaluation protocol.

**Architecture:** Reuse the existing `DualEdit-main` text-adapter training stack, but add one shared prerequisite: anchor-only text editing on the prompt-side `" bridge"` token instead of editing the full prompt text span. After that, keep Scheme 2 and Scheme 1 identical in layer, data, and evaluation, and change only the loss: Scheme 2 uses generation-based losses only; Scheme 1 adds an anchor alignment loss that pulls the layer-16 bridge anchor toward the gold-answer representation.

**Tech Stack:** Python 3.11, PyTorch, HuggingFace Transformers/LLaVA, existing `DualEdit-main` and `VisEdit-main` bridge data/eval scripts, `pytest`, PowerShell.

---

## File Structure

- Create: `DualEdit-main/scripts/bridge_text_anchor_utils.py`
  Purpose: Locate merged-token positions for `"bridge"` or the `"this bridge ?"` span from `LLaVA` processor inputs, and expose reusable helpers for dataset/eval code.
- Create: `DualEdit-main/dataset/edit_bridge_loader.py`
  Purpose: Local bridge dataset loader for `DualEdit-main`, derived from `Ten_Classes/bridge/edit_bridge_loader.py`, with explicit anchor metadata fields.
- Modify: `DualEdit-main/editor/vllm_editors/vead/adpt_model.py`
  Purpose: Make `TextEditAdaptor` honor caller-provided anchor token indices so only the selected anchor/span gets updated.
- Modify: `DualEdit-main/editor/vllm_editors/vead/vead.py`
  Purpose: Propagate anchor indices into text adaptors for every request/generality/locality batch; later extend the same path with Scheme 1 anchor losses.
- Create: `DualEdit-main/tests/test_bridge_text_anchor_utils.py`
  Purpose: Unit tests for anchor selection and merged-position resolution policies.
- Create: `DualEdit-main/tests/test_text_adaptor_anchor_masking.py`
  Purpose: Unit tests proving non-anchor prompt tokens stay unchanged when anchor-only masking is active.
- Create: `DualEdit-main/bridge_text_adapter_train.py`
  Purpose: Shared experiment entrypoint for Scheme 2 and Scheme 1 on bridge data.
- Create: `DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml`
  Purpose: Scheme 2 config, text-only adapter at layer 16, no explicit anchor loss.
- Create: `DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-anchor-l16.yaml`
  Purpose: Scheme 1 config, same as Scheme 2 plus anchor-alignment weight.
- Create: `DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py`
  Purpose: Unified evaluator for request, generality, and locality for bridge text-adapter runs.
- Create: `DualEdit-main/tests/test_eval_bridge_text_metrics.py`
  Purpose: Unit tests for strict/loose matching, summary aggregation, and split routing.
- Create: `DualEdit-main/scripts/compare_bridge_text_adapter_runs.py`
  Purpose: Load Scheme 2 and Scheme 1 summaries and emit a side-by-side markdown/JSON comparison.

## Shared Experimental Constraints

- Use `llava-v1.5-7b` only.
- Use text adapter only.
- Primary edit layer: `16`.
- Primary anchor policy: `bridge_only`.
- Primary anchor token: prompt-side `" bridge"` in the question.
- Shared training data: `Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json`.
- Shared evaluation families:
  - `request`: bridge-name recognition.
  - `generality`: `text_rephrase` and `image_rephrase`.
  - `locality`: `text_loc` and `image_loc`.
- Do not train on portability in either Scheme 2 or Scheme 1.
- Report the same metrics for both schemes before claiming any improvement.

## Anchor Coverage Audit

- `request`: `30 / 30` prompts contain the `bridge` anchor.
- `generality.image_rephrase`: `57 / 57` prompts contain the `bridge` anchor.
- `generality.text_rephrase`: `0 / 30` prompts contain the `bridge` anchor in the current JSON.
- `locality.text_loc`: `0 / 30` prompts contain the `bridge` anchor.
- `locality.image_loc`: `0 / 30` prompts contain the `bridge` anchor.
- Consequence for the main protocol:
  - anchor-only text editing is trainable on `request` and `image_rephrase`;
  - `text_rephrase` remains an evaluation split in the main comparison unless a separate bridge-bearing rewrite set is created later;
  - `locality` is still evaluated, but under anchor-only masking its training loss should be expected to stay at or near zero because no editable anchor exists in those prompts.

## Output Layout

- Training outputs:
  - `server_results/text-adapter-location/scheme2-l16/`
  - `server_results/text-adapter-location/scheme1-l16-anchor/`
- Evaluation outputs:
  - `server_results/text-adapter-location/scheme2-l16/eval/`
  - `server_results/text-adapter-location/scheme1-l16-anchor/eval/`
- Comparison outputs:
  - `server_results/text-adapter-location/comparison/`

### Task 1: Add Bridge Anchor Utilities And Local Bridge Loader

**Files:**
- Create: `DualEdit-main/scripts/bridge_text_anchor_utils.py`
- Create: `DualEdit-main/dataset/edit_bridge_loader.py`
- Test: `DualEdit-main/tests/test_bridge_text_anchor_utils.py`

- [ ] **Step 1: Write the failing tests for anchor policy resolution**

```python
from scripts.bridge_text_anchor_utils import (
    normalize_token_label,
    select_anchor_positions,
    expand_anchor_positions,
)


def test_select_anchor_positions_returns_bridge_only_position():
    token_labels = ["<bos>", "What", " is", " this", " bridge", "?", " The", " answer", " is", ":"]
    token_positions = [0, 579, 580, 584, 585, 586, 587, 588, 589, 590]
    assert select_anchor_positions(token_labels, token_positions, "bridge_only") == [585]


def test_expand_anchor_positions_returns_this_bridge_qmark_span():
    token_labels = ["<bos>", "What", " is", " this", " bridge", "?", " The", " answer", " is", ":"]
    token_positions = [0, 579, 580, 584, 585, 586, 587, 588, 589, 590]
    assert expand_anchor_positions(token_labels, token_positions, [585], "this_bridge_qmark") == [584, 585, 586]


def test_normalize_token_label_strips_llava_prefix_noise():
    assert normalize_token_label(" bridge") == "bridge"
    assert normalize_token_label("<0x0A>") == "0x0a"
```

- [ ] **Step 2: Run the test file and verify it fails**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_text_anchor_utils.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `scripts.bridge_text_anchor_utils` or missing function names.

- [ ] **Step 3: Write the anchor utility module and bridge loader**

```python
# DualEdit-main/scripts/bridge_text_anchor_utils.py
import os
import re


def normalize_token_label(label: str) -> str:
    text = str(label).replace("▁", " ").strip().lower()
    text = re.sub(r"[^0-9a-z]+", "", text)
    return text


def select_anchor_positions(token_labels, token_positions, policy: str):
    if policy != "bridge_only":
        raise ValueError(f"Unsupported anchor policy: {policy}")
    candidates = [
        pos for label, pos in zip(token_labels, token_positions)
        if normalize_token_label(label) == "bridge"
    ]
    if not candidates:
        raise ValueError("No bridge token found in prompt token labels")
    return [candidates[-1]]


def expand_anchor_positions(token_labels, token_positions, anchor_positions, span_policy: str):
    if span_policy == "bridge_only":
        return list(anchor_positions)
    if span_policy != "this_bridge_qmark":
        raise ValueError(f"Unsupported span policy: {span_policy}")
    idx_by_position = {pos: i for i, pos in enumerate(token_positions)}
    anchor_pos = anchor_positions[-1]
    anchor_idx = idx_by_position[anchor_pos]
    start = max(0, anchor_idx - 1)
    end = min(len(token_positions), anchor_idx + 2)
    return token_positions[start:end]
```

```python
# DualEdit-main/dataset/edit_bridge_loader.py
import os
import json
from copy import deepcopy
from tqdm import tqdm
from dataset.vllm import BaseVLLMEditData


class EditBridge(BaseVLLMEditData):
    def __init__(self, data_path, img_root_dir, coco_img_dir=None, data_n=None, img_path_map=None):
        if coco_img_dir is None:
            coco_img_dir = img_root_dir
        if img_path_map is None:
            img_path_map = {"train/images": "bridge_train/bridge_images"}

        with open(data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if data_n is not None:
            raw_data = raw_data[:data_n]

        def remap(rel_path):
            for src, dst in img_path_map.items():
                if rel_path and rel_path.startswith(src):
                    return dst + rel_path[len(src):]
            return rel_path

        def resolve_bridge(rel_path):
            return None if rel_path is None else os.path.join(img_root_dir, remap(rel_path))

        def resolve_coco(rel_path):
            return None if rel_path is None else os.path.join(coco_img_dir, rel_path)

        data_with_img_path = []
        for item in tqdm(raw_data, desc="Preparing EditBridge data"):
            new_item = {
                "request": {
                    "image": resolve_bridge(item["request"]["image"]),
                    "prompt": f"{item['request']['prompt']} The answer is:",
                    "target_new": item["request"]["target_new"],
                    "anchor_policy": "bridge_only",
                    "edit_span_policy": "bridge_only",
                },
                "generality": {"text_rephrase": [], "image_rephrase": []},
                "locality": {"text_loc": [], "image_loc": []},
                "portability": {"1hop": [], "2hop": []},
            }
            for g in item["generality"].get("text_rephrase", []):
                new_item["generality"]["text_rephrase"].append({
                    "image": resolve_bridge(g["image"]) if g.get("image") else None,
                    "prompt": f"{g['prompt']} The answer is:",
                    "target": g["target"],
                    "anchor_policy": "bridge_only",
                    "edit_span_policy": "bridge_only",
                })
            for g in item["generality"].get("image_rephrase", []):
                new_item["generality"]["image_rephrase"].append({
                    "image": resolve_bridge(g["image"]) if g.get("image") else None,
                    "prompt": f"{g['prompt']} The answer is:",
                    "target": g["target"],
                    "anchor_policy": "bridge_only",
                    "edit_span_policy": "bridge_only",
                })
            for loc in item["locality"].get("text_loc", []):
                new_item["locality"]["text_loc"].append({
                    "image": None,
                    "prompt": f"{loc['prompt']}?",
                    "target": loc["target"],
                })
            for loc in item["locality"].get("image_loc", []):
                new_item["locality"]["image_loc"].append({
                    "image": resolve_coco(loc["image"]) if loc.get("image") else None,
                    "prompt": f"{loc['prompt']} The answer is:",
                    "target": loc["target"],
                })
            data_with_img_path.append(new_item)

        data_with_img = deepcopy(data_with_img_path)
        for item in tqdm(data_with_img, desc="Loading images"):
            self.__load_imgs_for_data_with_img_path__(item)
        super().__init__(data_with_img, data_with_img_path)

    def dataset_name(self):
        return "EditBridgeTextAdapter"
```

- [ ] **Step 4: Run the tests again and verify they pass**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_text_anchor_utils.py -v
```

Expected: PASS with 3 passed tests.

- [ ] **Step 5: Save the code milestone**

Run:

```powershell
if (git rev-parse --is-inside-work-tree 2>$null) { git add DualEdit-main/scripts/bridge_text_anchor_utils.py DualEdit-main/dataset/edit_bridge_loader.py DualEdit-main/tests/test_bridge_text_anchor_utils.py; git commit -m "feat: add bridge anchor utilities and loader" } else { "skip-commit: no git repo" }
```

Expected: either a git commit is created, or the command prints `skip-commit: no git repo`.

### Task 2: Make `TextEditAdaptor` Respect Anchor-Only Positions

**Files:**
- Modify: `DualEdit-main/editor/vllm_editors/vead/adpt_model.py`
- Modify: `DualEdit-main/editor/vllm_editors/vead/vead.py`
- Test: `DualEdit-main/tests/test_text_adaptor_anchor_masking.py`

- [ ] **Step 1: Write the failing tests for anchor-only masking**

```python
import torch
from editor.vllm_editors.vead.adpt_model import TextEditAdaptor


def make_identity(linear):
    with torch.no_grad():
        linear.weight.zero_()
        linear.bias.zero_()
        eye = torch.eye(linear.weight.shape[0], linear.weight.shape[1])
        linear.weight.copy_(eye)


def build_deterministic_adaptor():
    adaptor = TextEditAdaptor(hidden_size=4, mid_dim=4, cross_att_head_n=1)
    make_identity(adaptor.mlp_begin)
    make_identity(adaptor.cross_att_q_mlp)
    make_identity(adaptor.cross_att_k_mlp)
    make_identity(adaptor.cross_att_v_mlp)
    make_identity(adaptor.mlp_end)
    adaptor.open_adaptor(True)
    adaptor.set_input_info(True, 1, 3)
    adaptor.set_edit_signal(
        torch.ones(1, 2, 4),
        torch.ones(1, 2),
        torch.tensor([6]),
    )
    adaptor.set_prompt_end(torch.tensor([6]))
    return adaptor


def test_text_adaptor_only_updates_selected_anchor_positions():
    adaptor = build_deterministic_adaptor()
    adaptor.set_text_token_indices([[4]])
    layer = torch.zeros(1, 6, 4)
    out = adaptor(layer.clone())
    changed = (out - layer).abs().sum(-1).squeeze(0) > 0
    assert changed.tolist() == [False, False, False, False, True, False]


def test_text_adaptor_leaves_sample_unchanged_when_anchor_list_is_empty():
    adaptor = build_deterministic_adaptor()
    adaptor.set_text_token_indices([[]])
    layer = torch.zeros(1, 6, 4)
    out = adaptor(layer.clone())
    assert torch.equal(out, layer)


def test_text_adaptor_falls_back_to_prompt_side_text_tokens_when_indices_are_none():
    adaptor = build_deterministic_adaptor()
    adaptor.set_text_token_indices(None)
    layer = torch.zeros(1, 6, 4)
    out = adaptor(layer.clone())
    changed = (out - layer).abs().sum(-1).squeeze(0) > 0
    assert changed.tolist() == [False, False, False, True, True, False]
```

- [ ] **Step 2: Run the test file and verify it fails**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_text_adaptor_anchor_masking.py -v
```

Expected: FAIL because `TextEditAdaptor.forward()` still edits the full prompt-side text span and ignores `self.text_token_indices`.

- [ ] **Step 3: Implement anchor-only masking in the adaptor and editor wrapper**

```python
# DualEdit-main/editor/vllm_editors/vead/adpt_model.py
class TextEditAdaptor(nn.Module):
    ...
    def _fallback_prompt_text_indices(self, sample_idx: int):
        prompt_end = int(self.prompt_end[sample_idx]) if self.prompt_end.dim() > 0 else int(self.prompt_end.item())
        if self.inpt_vt_end is not None:
            return list(range(self.inpt_vt_end, prompt_end))
        return list(range(1, prompt_end))

    def _resolve_text_indices(self, sample_idx: int):
        if self.text_token_indices is None:
            return self._fallback_prompt_text_indices(sample_idx)
        raw_indices = self.text_token_indices[sample_idx]
        prompt_end = int(self.prompt_end[sample_idx]) if self.prompt_end.dim() > 0 else int(self.prompt_end.item())
        valid = []
        for idx in raw_indices:
            idx = int(idx)
            if idx < 0 or idx >= prompt_end:
                continue
            if self.inpt_vt_begin is not None and self.inpt_vt_end is not None:
                if self.inpt_vt_begin <= idx < self.inpt_vt_end:
                    continue
            valid.append(idx)
        return sorted(set(valid))

    def forward(self, layer_outpt):
        ...
        text_indices = [self._resolve_text_indices(i) for i in range(batch_size)]
        if all(len(indices) == 0 for indices in text_indices):
            return [layer_outpt] if is_list_input else layer_outpt
        ...
        for i, indices in enumerate(text_indices):
            if len(indices) == 0:
                continue
            ...
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
class VEAD(VLLMBaseEditorWithTraining):
    ...
    def set_text_anchor_indices_for_adaptors(self, text_token_indices):
        for k, adaptor in self.adaptors.items():
            if k.startswith("text_"):
                adaptor.set_text_token_indices(text_token_indices)

    def clear_text_anchor_indices_for_adaptors(self):
        self.set_text_anchor_indices_for_adaptors(None)

    def init_wrap_get_llm_outpt(self):
        def get_llm_outpt_wrap(get_llm_outpt_func):
            def wrapped_get_llm_outpt(llm_inpt, vt_range):
                ...
                for adaptor in self.adaptors.values():
                    adaptor.set_input_info(has_img, vt_begin, vt_end)
                return get_llm_outpt_func(llm_inpt, vt_range)
```

Implementation notes:

- Do not overwrite caller-supplied anchor indices inside `init_wrap_get_llm_outpt`.
- Empty anchor lists must become a clean no-op instead of raising.
- Keep the old fallback path so non-bridge experiments still behave the same when `text_token_indices` is `None`.

- [ ] **Step 4: Run the masking tests again and verify they pass**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_text_adaptor_anchor_masking.py -v
```

Expected: PASS with 3 passed tests.

- [ ] **Step 5: Save the code milestone**

Run:

```powershell
if (git rev-parse --is-inside-work-tree 2>$null) { git add DualEdit-main/editor/vllm_editors/vead/adpt_model.py DualEdit-main/editor/vllm_editors/vead/vead.py DualEdit-main/tests/test_text_adaptor_anchor_masking.py; git commit -m "feat: support anchor-only text adaptor masking" } else { "skip-commit: no git repo" }
```

Expected: either a git commit is created, or the command prints `skip-commit: no git repo`.

### Task 3: Propagate Bridge Anchor Indices Through `VEAD` And Add The Scheme 2 Runner

**Files:**
- Modify: `DualEdit-main/scripts/bridge_text_anchor_utils.py`
- Modify: `DualEdit-main/editor/vllm_editors/vead/vead.py`
- Create: `DualEdit-main/bridge_text_adapter_train.py`
- Create: `DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml`
- Test: `DualEdit-main/tests/test_bridge_text_training_smoke.py`

- [ ] **Step 1: Write the failing smoke tests for anchor coverage and Scheme 2 config**

```python
from pathlib import Path
import yaml

from scripts.bridge_text_anchor_utils import summarize_bridge_anchor_coverage


def test_bridge_anchor_coverage_matches_current_dataset():
    summary = summarize_bridge_anchor_coverage(
        "Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json"
    )
    assert summary["request"]["anchor_found"] == 30
    assert summary["generality.image_rephrase"]["anchor_found"] == 57
    assert summary["generality.text_rephrase"]["anchor_found"] == 0
    assert summary["locality.image_loc"]["anchor_found"] == 0


def test_scheme2_config_is_text_only_layer16():
    cfg_path = Path("DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert data["edit_layers"] == []
    assert data["edit_text_layers"] == [16]
    assert data["IT"]["add_it"] is False
```

- [ ] **Step 2: Run the smoke tests and verify they fail**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_text_training_smoke.py -v
```

Expected: FAIL because the anchor coverage helper, the new config, and the bridge training entrypoint do not exist yet.

- [ ] **Step 3: Extend the anchor utilities and wire anchor indices through preprocessing/training**

```python
# DualEdit-main/scripts/bridge_text_anchor_utils.py
import json


def build_merged_token_positions(input_ids, image_token_id, image_token_span):
    merged_positions = []
    offset = 0
    for idx, token_id in enumerate(input_ids):
        merged_positions.append(idx + offset)
        if token_id == image_token_id:
            offset += image_token_span - 1
    return merged_positions


def resolve_anchor_indices(tokenizer, prompt, has_image, image_token_id, image_token_span,
                           anchor_policy="bridge_only", span_policy="bridge_only"):
    tokenized = tokenizer(prompt, return_tensors="pt", padding=False)
    input_ids = tokenized["input_ids"][0].tolist()
    token_labels = tokenizer.convert_ids_to_tokens(input_ids)
    merged_positions = build_merged_token_positions(input_ids, image_token_id, image_token_span)
    anchor_positions = select_anchor_positions(token_labels, merged_positions, anchor_policy)
    return expand_anchor_positions(token_labels, merged_positions, anchor_positions, span_policy)


def summarize_bridge_anchor_coverage(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    counts = {
        "request": {"anchor_found": 0, "total": 0},
        "generality.image_rephrase": {"anchor_found": 0, "total": 0},
        "generality.text_rephrase": {"anchor_found": 0, "total": 0},
        "locality.image_loc": {"anchor_found": 0, "total": 0},
        "locality.text_loc": {"anchor_found": 0, "total": 0},
    }
    for item in data:
        prompt = item["request"]["prompt"]
        counts["request"]["total"] += 1
        counts["request"]["anchor_found"] += int("bridge" in prompt.lower())
        for g in item["generality"].get("image_rephrase", []):
            counts["generality.image_rephrase"]["total"] += 1
            counts["generality.image_rephrase"]["anchor_found"] += int("bridge" in g["prompt"].lower())
        for g in item["generality"].get("text_rephrase", []):
            counts["generality.text_rephrase"]["total"] += 1
            counts["generality.text_rephrase"]["anchor_found"] += int("bridge" in g["prompt"].lower())
        for loc in item["locality"].get("image_loc", []):
            counts["locality.image_loc"]["total"] += 1
            counts["locality.image_loc"]["anchor_found"] += int("bridge" in loc["prompt"].lower())
        for loc in item["locality"].get("text_loc", []):
            counts["locality.text_loc"]["total"] += 1
            counts["locality.text_loc"]["anchor_found"] += int("bridge" in loc["prompt"].lower())
    return counts
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
from scripts.bridge_text_anchor_utils import resolve_anchor_indices


def _pack_xym_entry(xym, anchor_indices):
    return {"xym": xym, "anchor_indices": anchor_indices}


class VEAD(VLLMBaseEditorWithTraining):
    ...
    def _resolve_prompt_anchor_indices(self, prompt, has_image, anchor_policy, span_policy):
        tokenizer = self.vllm.get_llm_tokenizer()
        image_token_id = self.vllm.get_img_special_token_id()
        image_token_span = self.vllm.get_img_token_n()
        return resolve_anchor_indices(
            tokenizer,
            prompt,
            has_image,
            image_token_id,
            image_token_span,
            anchor_policy=anchor_policy,
            span_policy=span_policy,
        )

    def preprocess_train_data(self, raw_data, start_i=0, end_i=None):
        ...
        rel_anchor = self._resolve_prompt_anchor_indices(
            d["request"]["prompt"],
            d["request"]["image"] is not None,
            d["request"].get("anchor_policy", "bridge_only"),
            d["request"].get("edit_span_policy", "bridge_only"),
        )
        rel_data = _pack_xym_entry(((input_embeds, vt_range), label_ids, label_masks), rel_anchor)
        ...
        gen_anchor = self._resolve_prompt_anchor_indices(
            d["generality"][gen_name][0]["prompt"],
            d["generality"][gen_name][0]["image"] is not None,
            d["generality"][gen_name][0].get("anchor_policy", "bridge_only"),
            d["generality"][gen_name][0].get("edit_span_policy", "bridge_only"),
        )
        gen_data[gen_name] = _pack_xym_entry(((input_embeds, vt_range), label_ids, label_masks), gen_anchor)
        ...
        loc_data[loc_name] = _pack_xym_entry(((input_embeds, vt_range), label_ids, label_masks), [])
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
class VEAD(VLLMBaseEditorWithTraining):
    ...
    def organize_batch_data(self, a_batch_of_training_data_paths):
        ...
        rel_entries, gen_entries, loc_entries = [], [], []
        ...
        rd, gd, ld = torch.load(path, map_location=self.data_proc_device)
        rel_entries.append(rd)
        gen_entries.append(gd)
        loc_entries.append(ld)
        ...
        rel_xym = organize_middle_xym([entry["xym"] for entry in rel_entries])
        rel_anchor_indices = [entry["anchor_indices"] for entry in rel_entries]
        ...
        gen_xym[gen_name] = organize_middle_xym([entry[gen_name]["xym"] for entry in gen_entries])
        gen_anchor_indices[gen_name] = [entry[gen_name]["anchor_indices"] for entry in gen_entries]
        ...
        loc_xym[loc_name] = organize_middle_xym([entry[loc_name]["xym"] for entry in loc_entries])
        loc_anchor_indices[loc_name] = [entry[loc_name]["anchor_indices"] for entry in loc_entries]
        ...
        infm_xy = None
        if self.cfg.IT.add_it:
            infm_xy = self.__get_xy_for_influence_mapper__(rel_xym, gen_xym, loc_xym)
        return move_to_device(
            (
                (batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end),
                (rel_xym, rel_anchor_indices),
                (gen_xym, gen_anchor_indices),
                (loc_xym, loc_anchor_indices),
                infm_xy,
            ),
            self.device,
        )
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
class VEAD(VLLMBaseEditorWithTraining):
    ...
    def train_a_batch(self, a_batch_of_training_data):
        ((batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end),
         (rel_xym, rel_anchor_indices),
         (gen_xym, gen_anchor_indices),
         (loc_xym, loc_anchor_indices),
         infm_xy) = a_batch_of_training_data
        ...
        self.set_text_anchor_indices_for_adaptors(rel_anchor_indices)
        ...
        for loss_name, sp in gen_xym.items():
            self.set_text_anchor_indices_for_adaptors(gen_anchor_indices[loss_name])
            ...
        for loss_name, sp in loc_xym.items():
            self.set_text_anchor_indices_for_adaptors(loc_anchor_indices[loss_name])
            ...
```

Implementation notes:

- This task is where anchor indices start flowing through the actual training path.
- `text_rephrase` and `locality` anchor lists will be empty in the main protocol; that is expected and must be logged instead of treated as an error.
- Keep the batch shape stable even when some samples have `[]` anchor indices.
- Guard influence-trace preprocessing with `if self.cfg.IT.add_it:` so Scheme 2 does not build unused IT tensors.

- [ ] **Step 4: Create the Scheme 2 config and bridge training entrypoint**

```yaml
# DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml
edit_model_name: "llava-v1.5-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"
edit_layers: []
edit_text_layers: [16]
train_cfg:
  lr: 1.0e-4
  rel_lambda: 1.0
  gen_lambda: 1.0
  loc_lambda: 1.0
  inf_mapper_lambda: 0.0
IT:
  add_it: false
  layers: []
  test_n: 1
  noise_level: 0.0
  window: 0
  vt_sample_n: 1
  mid_dim: 1024
```

```python
# DualEdit-main/bridge_text_adapter_train.py
import argparse
import json
import os
import yaml

from utils.GLOBAL import ROOT_PATH
from utils import load_vllm_for_edit
from editor.vllm_editors.vead.vead import VEAD, VEADConfig
from dataset.edit_bridge_loader import EditBridge
from scripts.bridge_text_anchor_utils import summarize_bridge_anchor_coverage


def build_default_paths():
    workspace_root = os.path.abspath(os.path.join(ROOT_PATH, ".."))
    return {
        "data_path": os.path.join(workspace_root, "Ten_Classes", "bridge", "bridge_train", "edit_30_bridge_train_only_vis.json"),
        "bridge_img_root": os.path.join(workspace_root, "Ten_Classes", "bridge"),
        "coco_img_root": os.path.join(workspace_root, "VisEdit-main", "data", "easy-edit-mm", "images"),
        "records_dir": os.path.join(workspace_root, "server_results", "text-adapter-location", "scheme2-l16", "records"),
        "manifest_dir": os.path.join(workspace_root, "server_results", "text-adapter-location", "scheme2-l16"),
    }


def main():
    ...
    with open(args.config, "r", encoding="utf-8") as f:
        train_cfg = yaml.safe_load(f)
    config = VEADConfig.from_yaml(args.config)
    vllm = load_vllm_for_edit(config.edit_model_name, args.device)
    data_proc_device = args.device if args.single_gpu else f"cuda:{args.extra_devices[0]}"
    vllm_data_proc = vllm if args.single_gpu else load_vllm_for_edit(config.edit_model_name, data_proc_device)
    editor = VEAD(vllm, config, args.device, vllm_data_proc, data_proc_device, args.cache_root)
    train_data = EditBridge(args.data_path, args.bridge_img_root, args.coco_img_root, args.data_n)
    os.makedirs(args.manifest_dir, exist_ok=True)
    with open(os.path.join(args.manifest_dir, "anchor_coverage.json"), "w", encoding="utf-8") as f:
        json.dump(summarize_bridge_anchor_coverage(args.data_path), f, indent=2)
    editor.train_init(
        train_data,
        args.batch_size,
        records_dir=args.records_dir,
        train_name_prefix=args.train_name_prefix,
        load_ckpt_path=args.load_ckpt_path,
        save_ckpt_per_i=args.save_ckpt_per_i,
        log_per_i=args.log_per_i,
        ema_alpha=args.ema_alpha,
        random_seed=args.random_seed,
        data_buffer_size=args.data_buffer_size,
        edit_model_name=config.edit_model_name,
        train_cfg=train_cfg,
        dataset_name=train_data.dataset_name(),
    )
    editor.train(args.epochs)
```

- [ ] **Step 5: Run the smoke tests again and verify they pass**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_text_training_smoke.py -v
```

Expected: PASS with 2 passed tests.

- [ ] **Step 6: Save the code milestone**

Run:

```powershell
if (git rev-parse --is-inside-work-tree 2>$null) { git add DualEdit-main/scripts/bridge_text_anchor_utils.py DualEdit-main/editor/vllm_editors/vead/vead.py DualEdit-main/bridge_text_adapter_train.py DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml DualEdit-main/tests/test_bridge_text_training_smoke.py; git commit -m "feat: add bridge layer16 text-only training path" } else { "skip-commit: no git repo" }
```

Expected: either a git commit is created, or the command prints `skip-commit: no git repo`.

### Task 4: Build A Unified Evaluator For Request, Generality, And Locality

**Files:**
- Create: `DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py`
- Create: `DualEdit-main/tests/test_eval_bridge_text_metrics.py`

- [ ] **Step 1: Write the failing tests for evaluation metrics and summary aggregation**

```python
from scripts.eval_bridge_text_adapter_ckpt import strict_match, loose_match, summarize_rows


def test_strict_match_normalizes_case_and_punctuation():
    assert strict_match("Golden Gate Bridge.", "golden gate bridge") == 1


def test_loose_match_accepts_substring_overlap():
    assert loose_match("the Golden Gate Bridge", "Golden Gate Bridge") == 1


def test_summarize_rows_groups_by_split():
    rows = [
        {"split": "request", "strict_acc": 1, "loose_acc": 1},
        {"split": "request", "strict_acc": 0, "loose_acc": 1},
        {"split": "generality.image_rephrase", "strict_acc": 1, "loose_acc": 1},
    ]
    summary = summarize_rows(rows)
    assert summary["request"]["count"] == 2
    assert summary["request"]["strict_acc"] == 0.5
    assert summary["generality.image_rephrase"]["strict_acc"] == 1.0
```

- [ ] **Step 2: Run the metric tests and verify they fail**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_eval_bridge_text_metrics.py -v
```

Expected: FAIL because the evaluator and helper functions do not exist yet.

- [ ] **Step 3: Implement the evaluator**

```python
# DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py
import argparse
import json
import os
import re
from collections import defaultdict


def normalize_text(s):
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip()


def strict_match(pred, gold):
    return int(normalize_text(pred) == normalize_text(gold))


def loose_match(pred, gold):
    p = normalize_text(pred)
    g = normalize_text(gold)
    if not p or not g:
        return 0
    return int((p in g) or (g in p))


def summarize_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["split"]].append(row)
    summary = {}
    for split, split_rows in grouped.items():
        n = len(split_rows)
        summary[split] = {
            "count": n,
            "strict_acc": sum(r["strict_acc"] for r in split_rows) / n,
            "loose_acc": sum(r["loose_acc"] for r in split_rows) / n,
        }
    return summary
```

```python
# DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py
def build_eval_rows(edit_data):
    rows = []
    for item_idx, item in enumerate(edit_data):
        rows.append({
            "sample_id": item_idx,
            "split": "request",
            "prompt": item["request"]["prompt"],
            "image": item["request"]["image"],
            "target": item["request"]["target_new"],
            "edit_request": item["request"],
        })
        for split_name in ["text_rephrase", "image_rephrase"]:
            for sub_idx, sample in enumerate(item["generality"].get(split_name, [])):
                rows.append({
                    "sample_id": item_idx,
                    "split": f"generality.{split_name}",
                    "prompt": sample["prompt"],
                    "image": sample.get("image"),
                    "target": sample["target"],
                    "edit_request": item["request"],
                })
        for split_name in ["text_loc", "image_loc"]:
            for sub_idx, sample in enumerate(item["locality"].get(split_name, [])):
                rows.append({
                    "sample_id": item_idx,
                    "split": f"locality.{split_name}",
                    "prompt": sample["prompt"],
                    "image": sample.get("image"),
                    "target": sample["target"],
                    "edit_request": item["request"],
                })
    return rows
```

```python
# DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py
def run(...):
    ...
    rows = build_eval_rows(edit_data.data_with_img)
    outputs = []
    for row in rows:
        editor.restore_to_original_model()
        editor.edit_one_piece(row["edit_request"])
        pred = generate_answer(editor.vllm.model, editor.vllm.processor, row["prompt"], row["image"], device)
        outputs.append({
            **row,
            "pred": pred,
            "strict_acc": strict_match(pred, row["target"]),
            "loose_acc": loose_match(pred, row["target"]),
        })
    summary = summarize_rows(outputs)
    with open(os.path.join(out_dir, "rows.jsonl"), "w", encoding="utf-8") as f:
        for row in outputs:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
```

Implementation notes:

- Always evaluate Scheme 2 and Scheme 1 with the same script.
- Keep `text_rephrase` in evaluation even though it is not anchor-covered in the primary training protocol.
- Save both row-level outputs and split-level summaries so later comparison does not need to regenerate predictions.

- [ ] **Step 4: Run the metric tests again and verify they pass**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_eval_bridge_text_metrics.py -v
```

Expected: PASS with 3 passed tests.

- [ ] **Step 5: Save the code milestone**

Run:

```powershell
if (git rev-parse --is-inside-work-tree 2>$null) { git add DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py DualEdit-main/tests/test_eval_bridge_text_metrics.py; git commit -m "feat: add unified bridge text-adapter evaluator" } else { "skip-commit: no git repo" }
```

Expected: either a git commit is created, or the command prints `skip-commit: no git repo`.
### Task 5: Execute Scheme 2 End-To-End

**Files / outputs:**
- Use: `DualEdit-main/bridge_text_adapter_train.py`
- Use: `DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py`
- Write: `server_results/text-adapter-location/scheme2-l16/anchor_coverage.json`
- Write: `server_results/text-adapter-location/scheme2-l16/eval/rows.jsonl`
- Write: `server_results/text-adapter-location/scheme2-l16/eval/summary.json`
- Write: `server_results/text-adapter-location/scheme2-l16/run_manifest.json`

- [ ] **Step 1: Run the unit tests from Tasks 1-4 before training**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_text_anchor_utils.py DualEdit-main/tests/test_text_adaptor_anchor_masking.py DualEdit-main/tests/test_bridge_text_training_smoke.py DualEdit-main/tests/test_eval_bridge_text_metrics.py -v
```

Expected: PASS on all tests before any long-running training job starts.

- [ ] **Step 2: Launch the Scheme 2 training run**

Run:

```powershell
python DualEdit-main/bridge_text_adapter_train.py `
  --device cuda:0 `
  --extra_devices 1 `
  --batch_size 1 `
  --epochs 500 `
  --train_name_prefix bridge_text_scheme2 `
  --config DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml `
  --records_dir server_results/text-adapter-location/scheme2-l16/records `
  --manifest_dir server_results/text-adapter-location/scheme2-l16 `
  --cache_root server_results/text-adapter-location/scheme2-l16/cache
```

If only one GPU is available, run:

```powershell
python DualEdit-main/bridge_text_adapter_train.py `
  --device cuda:0 `
  --single_gpu `
  --batch_size 1 `
  --epochs 500 `
  --train_name_prefix bridge_text_scheme2 `
  --config DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml `
  --records_dir server_results/text-adapter-location/scheme2-l16/records `
  --manifest_dir server_results/text-adapter-location/scheme2-l16 `
  --cache_root server_results/text-adapter-location/scheme2-l16/cache
```

Expected:

- checkpoints are created under `server_results/text-adapter-location/scheme2-l16/records/.../checkpoints/`;
- `anchor_coverage.json` is written and shows the same counts as the audit above;
- TensorBoard logs are created for the run.

- [ ] **Step 3: Resolve the checkpoint to evaluate**

Run:

```powershell
$scheme2Ckpt = Get-ChildItem -LiteralPath 'server_results/text-adapter-location/scheme2-l16/records' -Recurse -File |
  Where-Object { $_.DirectoryName -like '*checkpoints*' } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName
$scheme2Ckpt
```

Expected: the command prints a concrete checkpoint path.

- [ ] **Step 4: Evaluate Scheme 2 on request, generality, and locality**

Run:

```powershell
python DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py `
  --device cuda:0 `
  --ckpt $scheme2Ckpt `
  --config DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml `
  --data_path Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json `
  --bridge_img_root Ten_Classes/bridge `
  --coco_img_root VisEdit-main/data/easy-edit-mm/images `
  --out_dir server_results/text-adapter-location/scheme2-l16/eval
```

Expected:

- `rows.jsonl` exists with row-level predictions for all splits;
- `summary.json` exists with split-level strict/loose metrics;
- the run is now frozen as the Scheme 2 baseline.

- [ ] **Step 5: Save a Scheme 2 manifest**

Run:

```powershell
@"
{
  "scheme": "scheme2-l16",
  "config": "DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml",
  "ckpt": "$scheme2Ckpt",
  "eval_summary": "server_results/text-adapter-location/scheme2-l16/eval/summary.json"
}
"@ | Set-Content -LiteralPath 'server_results/text-adapter-location/scheme2-l16/run_manifest.json'
```

Expected: `run_manifest.json` exists and records the exact checkpoint and evaluation summary used for later comparison.

### Task 6: Add Scheme 1 Anchor Representation Alignment Loss

**Files:**
- Modify: `DualEdit-main/editor/vllm_editors/vead/vead.py`
- Modify: `DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml`
- Create: `DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-anchor-l16.yaml`
- Test: `DualEdit-main/tests/test_bridge_anchor_alignment_loss.py`

- [ ] **Step 1: Write the failing tests for anchor loss helpers**

```python
import torch

from editor.vllm_editors.vead.vead import (
    cosine_anchor_alignment_loss,
    gather_mean_anchor_reps,
)


def test_gather_mean_anchor_reps_averages_selected_positions():
    layer_out = torch.tensor([
        [[0.0, 0.0], [1.0, 1.0], [3.0, 3.0], [0.0, 0.0]]
    ])
    reps, mask = gather_mean_anchor_reps(layer_out, [[1, 2]])
    assert mask.tolist() == [True]
    assert torch.allclose(reps[0], torch.tensor([2.0, 2.0]))


def test_cosine_anchor_alignment_loss_ignores_empty_anchor_samples():
    anchor = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
    target = torch.tensor([[1.0, 0.0], [1.0, 0.0]])
    valid = torch.tensor([True, False])
    loss = cosine_anchor_alignment_loss(anchor, target, valid)
    assert torch.allclose(loss, torch.tensor(0.0))
```

- [ ] **Step 2: Run the anchor-loss tests and verify they fail**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_anchor_alignment_loss.py -v
```

Expected: FAIL because the anchor loss helpers and config field do not exist yet.

- [ ] **Step 3: Add the anchor-loss helpers and cache target representations**

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
@dataclass
class VEADConfig(BaseConfig):
    @dataclass
    class TrainConfig():
        lr: float
        rel_lambda: float
        gen_lambda: float
        loc_lambda: float
        inf_mapper_lambda: float
        anchor_lambda: float = 0.0
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
import torch.nn.functional as F


def gather_mean_anchor_reps(layer_output, anchor_indices):
    reps, valid = [], []
    hidden_size = layer_output.shape[-1]
    for batch_i, indices in enumerate(anchor_indices):
        if len(indices) == 0:
            reps.append(torch.zeros(hidden_size, device=layer_output.device, dtype=layer_output.dtype))
            valid.append(False)
            continue
        reps.append(layer_output[batch_i, indices].mean(0))
        valid.append(True)
    return torch.stack(reps, 0), torch.tensor(valid, device=layer_output.device, dtype=torch.bool)


def cosine_anchor_alignment_loss(anchor_reps, target_reps, valid_mask):
    if valid_mask.sum() == 0:
        return anchor_reps.new_tensor(0.0)
    cos = F.cosine_similarity(anchor_reps[valid_mask], target_reps[valid_mask], dim=-1)
    return (1 - cos).mean()
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
class VEAD(VLLMBaseEditorWithTraining):
    ...
    def preprocess_train_data(self, raw_data, start_i=0, end_i=None):
        ...
        for k in edit_reps.keys():
            save_path = os.path.join(edit_signal_dir_i, k)
            save_data = {"edit_reps": edit_reps[k], "prompt_end": prompt_end[k]}
            if k.startswith("text_"):
                prompt_end_i = int(prompt_end[k])
                target_token_count = int(label_masks[0].sum().item())
                target_positions = list(range(prompt_end_i, prompt_end_i + target_token_count))
                anchor_indices = self._resolve_prompt_anchor_indices(
                    r["prompt"],
                    r["image"] is not None,
                    r.get("anchor_policy", "bridge_only"),
                    r.get("edit_span_policy", "bridge_only"),
                )
                save_data["anchor_indices"] = anchor_indices
                save_data["anchor_target_rep"] = edit_reps[k][0, target_positions].mean(0).cpu()
            torch.save(save_data, save_path)
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
class VEAD(VLLMBaseEditorWithTraining):
    ...
    def organize_batch_data(self, a_batch_of_training_data_paths):
        ...
        batch_anchor_targets = {}
        for k, v in edit_signal.items():
            if not k.startswith("text_"):
                continue
            targets = []
            for signal in v:
                target = signal.get("anchor_target_rep")
                if target is None:
                    target = torch.zeros(self.cfg.llm_hidden_size, device=self.data_proc_device)
                targets.append(target.to(self.data_proc_device))
            batch_anchor_targets[k] = torch.stack(targets, 0)
        ...
        return move_to_device(
            (
                (batch_edit_reps, batch_edit_reps_att_mask, batch_prompt_end, batch_anchor_targets),
                (rel_xym, rel_anchor_indices),
                (gen_xym, gen_anchor_indices),
                (loc_xym, loc_anchor_indices),
                infm_xy,
            ),
            self.device,
        )
```

```python
# DualEdit-main/editor/vllm_editors/vead/vead.py
class VEAD(VLLMBaseEditorWithTraining):
    ...
    def _compute_anchor_loss_for_split(self, xym_data, anchor_indices, batch_anchor_targets):
        if not self.text_enabled or self.cfg.train_cfg.anchor_lambda <= 0:
            return torch.tensor(0.0, device=self.device), {}
        (mid_inpt, vt_range), _, _ = xym_data
        actual_text_keys = [k[5:] for k in self.adaptors.keys() if k.startswith("text_")]
        if not actual_text_keys:
            return torch.tensor(0.0, device=self.device), {}
        with TraceDict(self.vllm.model, actual_text_keys, retain_output=True, stop=False) as td:
            self.infer_from_mid_layer(self.vllm, mid_inpt, vt_range, self.mid_inpt_start_layer_i, mid_inpt["inputs_embeds"])
        total_loss = torch.tensor(0.0, device=self.device)
        logs = {}
        for text_key, actual_key in zip([k for k in self.adaptors.keys() if k.startswith("text_")], actual_text_keys):
            layer_out = td[actual_key].output
            layer_out = layer_out[0] if not isinstance(layer_out, torch.Tensor) else layer_out
            anchor_reps, valid_mask = gather_mean_anchor_reps(layer_out, anchor_indices)
            anchor_loss = cosine_anchor_alignment_loss(anchor_reps, batch_anchor_targets[text_key], valid_mask)
            logs[f"anchor_valid/{text_key}"] = int(valid_mask.sum().item())
            logs[f"anchor_loss/{text_key}"] = float(anchor_loss)
            total_loss = total_loss + anchor_loss
        return total_loss * self.cfg.train_cfg.anchor_lambda, logs
```

- [ ] **Step 4: Add the Scheme 1 config and patch Scheme 2 config to include `anchor_lambda: 0.0`**

```yaml
# DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml
train_cfg:
  lr: 1.0e-4
  rel_lambda: 1.0
  gen_lambda: 1.0
  loc_lambda: 1.0
  inf_mapper_lambda: 0.0
  anchor_lambda: 0.0
```

```yaml
# DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-anchor-l16.yaml
edit_model_name: "llava-v1.5-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"
edit_layers: []
edit_text_layers: [16]
train_cfg:
  lr: 1.0e-4
  rel_lambda: 1.0
  gen_lambda: 1.0
  loc_lambda: 1.0
  inf_mapper_lambda: 0.0
  anchor_lambda: 0.1
IT:
  add_it: false
  layers: []
  test_n: 1
  noise_level: 0.0
  window: 0
  vt_sample_n: 1
  mid_dim: 1024
```

Implementation notes:

- The main Scheme 1 comparison should differ from Scheme 2 only by `anchor_lambda > 0`.
- Use the request answer hidden states as the target representation, averaged over the gold answer token span.
- Keep `anchor_lambda = 0.1` for the first main run; only sweep `[0.05, 0.1, 0.2]` if the primary comparison is unstable.

- [ ] **Step 5: Run the anchor-loss tests again and verify they pass**

Run:

```powershell
python -m pytest DualEdit-main/tests/test_bridge_anchor_alignment_loss.py -v
```

Expected: PASS with 2 passed tests.

- [ ] **Step 6: Save the code milestone**

Run:

```powershell
if (git rev-parse --is-inside-work-tree 2>$null) { git add DualEdit-main/editor/vllm_editors/vead/vead.py DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-only-l16.yaml DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-anchor-l16.yaml DualEdit-main/tests/test_bridge_anchor_alignment_loss.py; git commit -m "feat: add bridge anchor alignment loss" } else { "skip-commit: no git repo" }
```

Expected: either a git commit is created, or the command prints `skip-commit: no git repo`.

### Task 7: Execute Scheme 1 And Compare It Against Scheme 2

**Files / outputs:**
- Use: `DualEdit-main/bridge_text_adapter_train.py`
- Use: `DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py`
- Create: `DualEdit-main/scripts/compare_bridge_text_adapter_runs.py`
- Write: `server_results/text-adapter-location/scheme1-l16-anchor/eval/summary.json`
- Write: `server_results/text-adapter-location/comparison/scheme1_vs_scheme2.json`
- Write: `server_results/text-adapter-location/comparison/scheme1_vs_scheme2.md`

- [ ] **Step 1: Implement the comparison script**

```python
# DualEdit-main/scripts/compare_bridge_text_adapter_runs.py
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_split_metrics(base_summary, new_summary):
    splits = sorted(set(base_summary) | set(new_summary))
    rows = []
    for split in splits:
        b = base_summary.get(split, {})
        n = new_summary.get(split, {})
        rows.append({
            "split": split,
            "scheme2_strict": b.get("strict_acc"),
            "scheme1_strict": n.get("strict_acc"),
            "strict_delta": None if b.get("strict_acc") is None or n.get("strict_acc") is None else n["strict_acc"] - b["strict_acc"],
            "scheme2_loose": b.get("loose_acc"),
            "scheme1_loose": n.get("loose_acc"),
            "loose_delta": None if b.get("loose_acc") is None or n.get("loose_acc") is None else n["loose_acc"] - b["loose_acc"],
        })
    return rows
```

- [ ] **Step 2: Train Scheme 1 with the same runner**

Run:

```powershell
python DualEdit-main/bridge_text_adapter_train.py `
  --device cuda:0 `
  --extra_devices 1 `
  --batch_size 1 `
  --epochs 500 `
  --train_name_prefix bridge_text_scheme1 `
  --config DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-anchor-l16.yaml `
  --records_dir server_results/text-adapter-location/scheme1-l16-anchor/records `
  --manifest_dir server_results/text-adapter-location/scheme1-l16-anchor `
  --cache_root server_results/text-adapter-location/scheme1-l16-anchor/cache
```

- [ ] **Step 3: Resolve and evaluate the Scheme 1 checkpoint**

Run:

```powershell
$scheme1Ckpt = Get-ChildItem -LiteralPath 'server_results/text-adapter-location/scheme1-l16-anchor/records' -Recurse -File |
  Where-Object { $_.DirectoryName -like '*checkpoints*' } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName

python DualEdit-main/scripts/eval_bridge_text_adapter_ckpt.py `
  --device cuda:0 `
  --ckpt $scheme1Ckpt `
  --config DualEdit-main/configs/vead/llava-v1.5-7b-bridge-text-anchor-l16.yaml `
  --data_path Ten_Classes/bridge/bridge_train/edit_30_bridge_train_only_vis.json `
  --bridge_img_root Ten_Classes/bridge `
  --coco_img_root VisEdit-main/data/easy-edit-mm/images `
  --out_dir server_results/text-adapter-location/scheme1-l16-anchor/eval
```

- [ ] **Step 4: Compare Scheme 1 against Scheme 2**

Run:

```powershell
python DualEdit-main/scripts/compare_bridge_text_adapter_runs.py `
  --scheme2 server_results/text-adapter-location/scheme2-l16/eval/summary.json `
  --scheme1 server_results/text-adapter-location/scheme1-l16-anchor/eval/summary.json `
  --out_json server_results/text-adapter-location/comparison/scheme1_vs_scheme2.json `
  --out_md server_results/text-adapter-location/comparison/scheme1_vs_scheme2.md
```

Expected:

- the comparison file reports deltas for `request`, `generality.image_rephrase`, `generality.text_rephrase`, `locality.image_loc`, and `locality.text_loc`;
- the only intentional difference between runs is the anchor loss.

- [ ] **Step 5: Save the final manifest**

Run:

```powershell
$scheme2Manifest = Get-Content -LiteralPath 'server_results/text-adapter-location/scheme2-l16/run_manifest.json' | ConvertFrom-Json

@"
{
  "scheme2_ckpt": "$($scheme2Manifest.ckpt)",
  "scheme1_ckpt": "$scheme1Ckpt",
  "scheme2_summary": "server_results/text-adapter-location/scheme2-l16/eval/summary.json",
  "scheme1_summary": "server_results/text-adapter-location/scheme1-l16-anchor/eval/summary.json",
  "comparison_json": "server_results/text-adapter-location/comparison/scheme1_vs_scheme2.json",
  "comparison_md": "server_results/text-adapter-location/comparison/scheme1_vs_scheme2.md"
}
"@ | Set-Content -LiteralPath 'server_results/text-adapter-location/comparison/final_manifest.json'
```

## Acceptance Criteria

- Task 1 confirms bridge-anchor resolution and span expansion with unit tests.
- Task 2 proves the text adaptor can edit only caller-specified anchor indices and leave non-anchor prompt tokens unchanged.
- Task 3 produces a runnable Scheme 2 training path with anchor coverage logged to disk and no unintended influence-trace preprocessing when `IT.add_it: false`.
- Task 4 produces a unified evaluator that writes both row-level outputs and split-level summaries.
- Task 5 produces one frozen Scheme 2 checkpoint, one evaluation summary, and one run manifest.
- Task 6 adds anchor alignment loss without changing the model layer, dataset, or evaluation protocol, and updates Scheme 2 config to keep `anchor_lambda: 0.0`.
- Task 7 produces one frozen Scheme 1 checkpoint and one comparison report against Scheme 2.

## Self-Review Checklist

- [ ] `edit_text_layers` is `[16]` in both Scheme 2 and Scheme 1 configs.
- [ ] `edit_layers` stays `[]` for both runs.
- [ ] `portability` remains excluded from training.
- [ ] Anchor-only masking is active for text adaptors and unit-tested.
- [ ] `request` and `image_rephrase` anchor coverage matches the audit counts above.
- [ ] `text_rephrase` is treated as evaluation-only in the main protocol unless a separate bridge-bearing rewrite set is created later.
- [ ] Scheme 2 and Scheme 1 use the same evaluator and the same summary format.
- [ ] The comparison report clearly states that Scheme 1 changes only `anchor_lambda`.

## Execution Handoff

Plan saved at:

- `specs/vlm-attribution-layer-screening/text-adapter-location-execution-plan.md`

Recommended execution mode:

- Preferred: run the tasks in order from Task 1 to Task 7, one milestone at a time, and do not start Scheme 1 before Scheme 2 is frozen.
- Alternative: if implementation work is parallelized later, keep Task 2 and Task 3 on the critical path first because all later experiments depend on anchor-only masking and anchor-index propagation.

