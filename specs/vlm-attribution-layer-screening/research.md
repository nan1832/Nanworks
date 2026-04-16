# Research

## Goal

Use DualEdit-style modality-aware localization and VisEdit-style target-centric localization to screen candidate edit layers before running actual vision-language model editing.

The immediate objective is not to edit the model yet. The immediate objective is to compute per-layer evidence for:

- visual representation usefulness
- key text token trajectory
- attention-based relative importance
- perturbation-based sensitivity
- MLP contribution

and then convert these signals into a short list of candidate edit layers.

## Current Context

### What the papers suggest

- DualEdit treats text and vision as separate pathways and argues that the best text edit layer and best visual edit layer do not have to be the same.
- DualEdit uses two probes before selecting layers:
  - attention statistics as a relative importance probe
  - Gaussian noise perturbation plus output KL divergence as a stronger sensitivity probe
- VisEdit centers localization around the target prediction token and further distinguishes attention contribution from MLP contribution.
- VisEdit also supports coarse-to-fine localization: first decide which layer matters, then decide which tokens or patches matter inside that layer.

### What the current local experiments suggest

- In the current bridge setup, explicit entity-name prompting gives a large gain, so image-to-entity anchoring is already a known bottleneck.
- Visual-only editing can strongly improve train-time entity recognition while still failing to produce strong validation strict open-end QA or unseen portability.
- Therefore the first localization pass should distinguish:
  - identity or anchoring layers
  - relation or knowledge-access layers

This means the layer-screening procedure should not rely on one metric only.

## Nearby Repo Context

### Recommended first backbone

Use `LLaVA-v1.5-7B` as the first backbone for layer screening.

Why:

- the current bridge experiments already use LLaVA
- local configs already exist for `edit_layers: [18]` and for DualEdit-style `edit_text_layers: [16]`, `edit_layers: [19]`
- both DualEdit and VisEdit code paths in the repo already provide LLaVA wrappers

### Existing local code that already helps

#### DualEdit LLaVA wrapper

File: `DualEdit-main/editor/vllms_for_edit/llava/llava.py`

Useful facts:

- the visual tower is called with `output_hidden_states=True`
- image features are taken from `vision_tower(...)`
- language-side hidden states are taken from `self.model.language_model(..., output_hidden_states=True)`
- the image token span is already exposed through `vt_range`

This means the local code already gives direct access to:

- per-layer vision hidden states before projection merge
- language model hidden states after image-text merge
- the visual token range inside the merged sequence

#### VisEdit p_track

Files:

- `VisEdit-main/p_track/p_track.py`
- `VisEdit-main/configs/p_track/llava-v1.5-7b.yaml`
- `VisEdit-main/contribution_module.py`
- `VisEdit-main/contribution_visual_reps.py`

Useful facts:

- LLaVA is configured as a 32-layer language model
- layer path: `language_model.model.layers.{}`
- attention path: `language_model.model.layers.{}.self_attn`
- MLP path: `language_model.model.layers.{}.mlp`
- norm path: `language_model.model.norm`
- vocab head path: `language_model.lm_head`

This means the local code already contains a practical tracing route for:

- layer representations
- attention-module outputs
- MLP outputs
- projection of intermediate states back to vocabulary space

## Recommended Research Decision

Freeze the first-pass scope as:

- backbone: `LLaVA-v1.5-7B`
- level of analysis: layer-level first, patch-level later
- unit of text analysis: key text token and target prediction token
- unit of visual analysis: merged visual token span and its projected representations

Do not start with BLIP2 and LLaVA together. First make the full pipeline run on LLaVA, then port the same protocol to BLIP2.

## What To Compute

### 1. Visual representation per layer

Collect two visual representations:

- visual tower hidden state at each vision layer if available
- merged visual token representations inside the language model after image-text merge

The practically useful one for edit-layer screening is the second one, because later editing is applied in the language model stack.

Minimum artifact:

- mean-pooled visual token representation per layer
- optionally token-wise visual representations for later region-level refinement

### 2. Key text token per layer

Track at least two token types:

- the target prediction token position, usually the final answer position
- a semantic anchor token from the prompt, such as the entity token or the queried attribute token

Recommendation:

- use the final predicted answer token as the primary tracked token
- when the prompt contains an explicit entity mention, also trace the entity token as a secondary anchor

This follows VisEdit more closely than tracing the full sentence indiscriminately.

### 3. Attention-based relative importance

For every language layer:

- record attention-module outputs
- compare contributions from visual token span to the target token
- compare contributions from text tokens to the target token

Use this as a relative ranking only.

Do not treat attention score alone as causal evidence.

### 4. Perturbation-based sensitivity

Run DualEdit-style perturbation on a per-layer basis:

- perturb visual tokens only
- perturb key text token only
- perturb both together

After perturbation, measure output change with:

- logits KL divergence against the clean forward pass
- optionally change in target-token probability

This is the strongest first-pass signal for edit-layer screening.

### 5. MLP contribution

Use VisEdit-style module tracking to compare:

- attention output contribution
- MLP output contribution

At minimum, do one of these:

- trace attention and MLP outputs for the target token and convert them to vocabulary-space evidence
- ablate or noise-perturb the MLP output at each layer and measure the change in target-token distribution

The main purpose is to answer:

- is the layer influential because of attention routing
- or because the MLP is injecting task-relevant knowledge

## Recommended Layer-Screening Procedure

### Stage 1: Build clean tracing

For one image-question pair:

1. run a clean forward pass
2. save `vt_range`
3. save hidden states for all 32 language layers
4. save attention-module outputs for all 32 layers
5. save MLP outputs for all 32 layers
6. identify the final target prediction token

Deliverable:

- one complete trace record for one sample

### Stage 2: Attention ranking

For a small pilot set:

1. compute visual-to-target and text-to-target attention-related signals across layers
2. summarize where the strongest peaks appear
3. mark 3-5 candidate visual-side layers and 3-5 candidate text-side layers

Deliverable:

- attention-based candidate layer shortlist

### Stage 3: Perturbation ranking

For the same pilot set:

1. perturb visual tokens by layer
2. perturb key text token by layer
3. perturb both together by layer
4. compute KL divergence and target-token probability drop

Deliverable:

- causal sensitivity ranking for visual, text, and joint perturbation

### Stage 4: Module decomposition

For top candidate layers:

1. compare attention-module and MLP-module contributions
2. identify whether each candidate layer is:
   - routing-dominant
   - MLP-dominant
   - mixed

Deliverable:

- functional interpretation for each shortlisted layer

### Stage 5: Final candidate set

Select:

- one to three candidate visual edit layers
- one to three candidate text edit layers
- optionally one shared layer only if the evidence supports it

Do not force a shared layer if the rankings disagree.

## How To Score Candidate Layers

Use a simple combined screening table.

For each layer, record:

- attention score rank
- visual perturbation KL rank
- text perturbation KL rank
- joint perturbation KL rank
- MLP contribution rank
- stability across sampled examples

Then classify the layer:

- `visual-anchor layer`
- `text-anchor layer`
- `cross-modal interaction layer`
- `relation-writing layer`
- `prototype-memory layer`

This classification is more useful than a single scalar score.

## Recommended Outputs From The Research Phase

Before moving to requirements, the research phase should produce:

1. a finalized target backbone and module path table
2. a finalized definition of the key tracked token
3. a finalized list of per-layer signals to compute
4. a pilot protocol for attention, perturbation, and MLP contribution
5. a candidate-layer ranking template

## Risks

- Attention peaks may not match perturbation peaks.
- Visual-only sensitive layers may reflect entity anchoring rather than relation access.
- Target token choice may be unstable across different prompt formats.
- MLP contribution can look large simply because the predicted token is already easy, not because the layer is edit-worthy.
- If the sample set is too small, the chosen layers may overfit one prompt template or one entity type.

## Constraints

- The current phase is still research; no actual editing benchmark should be used as proof of layer quality yet.
- The first pass should reuse existing local code as much as possible instead of writing a new framework immediately.
- Candidate layers should be selected on open-end style outputs, not on position-biased multiple-choice data.

## Recommended Next Phase

Continue to requirements once these three choices are explicitly fixed:

1. exact target backbone: `LLaVA-v1.5-7B`
2. exact tracked token definition: final answer token plus optional entity anchor token
3. exact first-pass signals: attention, perturbation KL, and attention-vs-MLP contribution

At that point, `requirements.md` can define:

- what scripts to build
- what files to save
- what pilot sample size to use
- what rule will convert measured signals into selected edit layers
