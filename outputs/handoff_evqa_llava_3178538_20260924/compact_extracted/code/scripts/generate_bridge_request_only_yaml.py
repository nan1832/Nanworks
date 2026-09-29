import argparse
from pathlib import Path


def parse_layers(value: str):
    layers = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            layers.extend(range(int(start), int(end) + 1))
        else:
            layers.append(int(part))
    return sorted(dict.fromkeys(layers))


def llava_yaml(layer: int) -> str:
    return f"""edit_model_name: "llava-v1.5-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{{}}"
llm_att_tmp: "language_model.model.layers.{{}}.self_attn"
edit_layers: [{layer}]
train_cfg:
  lr: 1.e-4
  rel_lambda: 1.0
  gen_lambda: 0.0
  loc_lambda: 0.0
  inf_mapper_lambda: 0.1
port_lambda: 0.0
port_sample_n: 1
IT:
  add_it: true
  layers: [19,20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
"""


def blip2_yaml(layer: int) -> str:
    return f"""edit_model_name: "blip2-opt-2.7b"
llm_hidden_size: 2560
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.decoder.layers.{{}}"
llm_att_tmp: "language_model.model.decoder.layers.{{}}.self_attn"
edit_layers: [{layer}]
train_cfg:
  lr: 1.e-4
  rel_lambda: 1.0
  gen_lambda: 0.0
  loc_lambda: 0.0
  inf_mapper_lambda: 0.1
port_lambda: 0.0
port_sample_n: 1
IT:
  add_it: true
  layers: [20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
"""


def instructblip_yaml(layer: int) -> str:
    return f"""edit_model_name: "instructblip-vicuna-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{{}}"
llm_att_tmp: "language_model.model.layers.{{}}.self_attn"
edit_layers: [{layer}]
train_cfg:
  lr: 1.e-4
  rel_lambda: 1.0
  gen_lambda: 0.0
  loc_lambda: 0.0
  inf_mapper_lambda: 0.1
port_lambda: 0.0
port_sample_n: 1
IT:
  add_it: true
  layers: [20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
"""


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--layers", default="0-31")
    args = parser.parse_args()

    root = Path(args.output_root)
    for layer in parse_layers(args.layers):
        write(
            root / "llava" / f"llava-v1.5-7b-bridge-request-only-l{layer}.yaml",
            llava_yaml(layer),
        )
        write(
            root / "blip2" / f"blip2-opt-2.7b-bridge-request-only-l{layer}.yaml",
            blip2_yaml(layer),
        )
        write(
            root / "instructblip" / f"instructblip-vicuna-7b-bridge-request-only-l{layer}.yaml",
            instructblip_yaml(layer),
        )


if __name__ == "__main__":
    main()
