import re


def normalize_token_label(label: str) -> str:
    text = str(label).replace("\u2581", " ").strip().lower()
    return re.sub(r"[^0-9a-z]+", "", text)


def select_anchor_positions(token_labels, token_positions, policy: str):
    if policy != "bridge_only":
        raise ValueError(f"Unsupported anchor policy: {policy}")

    candidates = [
        pos
        for label, pos in zip(token_labels, token_positions)
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
    if not anchor_positions:
        return []

    idx_by_position = {pos: i for i, pos in enumerate(token_positions)}
    anchor_pos = anchor_positions[-1]
    anchor_idx = idx_by_position[anchor_pos]
    start = max(0, anchor_idx - 1)
    end = min(len(token_positions), anchor_idx + 2)
    return token_positions[start:end]
