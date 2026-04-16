import os
import json
import yaml
import argparse


def parse_int_list(s: str):
    return [int(x.strip()) for x in s.split(",") if x.strip() != ""]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-config", type=str, default="configs/vead/llava-v1.5-7b.yaml")
    parser.add_argument("--visual-layers", type=str, required=True)
    parser.add_argument("--text-layers", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="configs/vead_sweeps")
    parser.add_argument("--train-script", type=str, default="dualedit_train.py")
    parser.add_argument("--edit-model-name", type=str, default="llava-v1.5-7b")
    parser.add_argument("--data-name", type=str, default="EVQA")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--data-n", type=int, default=512)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--extra-devices", type=str, default="1")
    parser.add_argument("--name-prefix", type=str, default="sweep")
    return parser.parse_args()


def main():
    args = parse_args()
    visual_layers = parse_int_list(args.visual_layers)
    text_layers = parse_int_list(args.text_layers)

    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.base_config, "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)

    commands = []
    for lv in visual_layers:
        for lt in text_layers:
            cfg = dict(base_cfg)
            cfg["edit_layers"] = [int(lv)]
            cfg["edit_text_layers"] = [int(lt)]

            name = f"vead_llava_v{lv}_t{lt}.yaml"
            path = os.path.join(args.output_dir, name)
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

            cmd = (
                f"python {args.train_script} "
                f"-mn {args.edit_model_name} "
                f"-dna {args.data_name} "
                f"-bs {args.batch_size} "
                f"-dvc {args.device} "
                f"-dn {args.data_n} "
                f"-eps {args.epochs} "
                f"-edvc {args.extra_devices} "
                f"-tnp {args.name_prefix}_v{lv}_t{lt} "
                f"-cp {path}"
            )
            commands.append(
                {
                    "visual_layer": lv,
                    "text_layer": lt,
                    "config_path": path,
                    "train_command": cmd,
                }
            )

    with open(os.path.join(args.output_dir, "commands.json"), "w", encoding="utf-8") as f:
        json.dump(commands, f, ensure_ascii=False, indent=2)

    with open(os.path.join(args.output_dir, "run_all.sh"), "w", encoding="utf-8") as f:
        for c in commands:
            f.write(c["train_command"] + "\n")

    with open(os.path.join(args.output_dir, "run_all.ps1"), "w", encoding="utf-8") as f:
        for c in commands:
            f.write(c["train_command"] + "\n")

    print(f"generated={len(commands)}")
    print(os.path.join(args.output_dir, "commands.json"))


if __name__ == "__main__":
    main()
