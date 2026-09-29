"""Read compact, explicitly selected localization artifacts through read-only SSH."""
from pathlib import Path
import base64
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/all_methods_recommendations_20260928"
REMOTE = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results"
MODELS = ["blip2-opt-2.7b", "instructblip-vicuna-7b", "minigpt-4-vicuna-7b", "llava-v1.5-7b", "qwen2.5-vl-3b", "paligemma-3b", "smolvlm-1.7b"]
DATASETS = ["evqa-pilot500", "mmke-visual", "mmke-entity"]


def main():
    targets = []
    roots = {
        "salem": ("salem_candidate_layers_7models_3data_current_alloc_20260621_203335", ["salem_layer_scores.csv", "summary.json"]),
        "perturb": ("perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701", ["perturb_kl_layer_scores.csv", "summary.json"]),
        "cma_alt": ("cma_direct_v13_full_g09_gpu0_20260703_134818", ["cma_direct_layer_scores.csv", "summary.json"]),
        "lga_param": ("lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900", ["layer_scores.csv", "summary.json"]),
    }
    for ds in DATASETS:
        for model in MODELS:
            for family, (run, names) in roots.items():
                for name in names:
                    targets.append(dict(local=f"raw/{family}/{ds}/{model}/{name}", remote=f"{REMOTE}/{run}/{ds}/{model}/{name}"))
            run = "ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304" if model.startswith("qwen") else "ours_direct_7models_3datasets_g08_gpu0_20260626_131624"
            for name in ["ours_direct_layer_scores.csv", "summary.json"]:
                targets.append(dict(local=f"raw/visual/{ds}/{model}/{name}", remote=f"{REMOTE}/{run}/{ds}/{model}/{name}"))
            if (ds, model) == ("mmke-entity", "qwen2.5-vl-3b"):
                run = "cma_modelpred_direct_formal_multinoise_multiseed_v1_20260906/formal636"
            else:
                run = f"cma_modelpred_direct_all20_multinoise_multiseed_v1_20260906/{ds}/{model}/formal"
            for name in ["cma_layer_scores.csv", "summary.json", "stability_by_alpha_seed.json"]:
                targets.append(dict(local=f"raw/cma_model_pred/{ds}/{model}/{name}", remote=f"{REMOTE}/{run}/canonical/{name}"))
    for name in ["cma_formal_top3_top5.json", "cma_coverage_summary.json", "frozen_config.json", "cma_layer_alpha_seed_scores.csv"]:
        targets.append(dict(local=f"raw/cma_alt_formal_qwen_entity/{name}", remote=f"{REMOTE}/cma_direct_formal_multinoise_multiseed_v1_20260906/formal636/{name}"))
    code = """
import json,base64,hashlib,datetime
from pathlib import Path
targets=json.loads(base64.b64decode(TARGETS))
records=[]
for item in targets:
    p=Path(item['remote'])
    if not p.is_file():
        records.append(dict(item,status='missing'));continue
    if p.stat().st_size > 5000000:raise RuntimeError('compact artifact size limit: '+str(p))
    b=p.read_bytes()
    records.append(dict(item,status='ok',size=len(b),sha256=hashlib.sha256(b).hexdigest(),content=base64.b64encode(b).decode()))
print(json.dumps(dict(collected_at=datetime.datetime.now().astimezone().isoformat(),records=records)))
""".replace("TARGETS", repr(base64.b64encode(json.dumps(targets).encode()).decode()))
    process = subprocess.run(["ssh.exe", "-i", str(Path(os.environ["USERPROFILE"]) / ".ssh/id_ed25519_bridge"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "bridge-server", "python3 -"], input=code.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if process.returncode:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace"))
    bundle = json.loads(process.stdout)
    OUT.mkdir(exist_ok=True)
    for record in bundle["records"]:
        if record["status"] == "ok":
            b = base64.b64decode(record.pop("content"))
            assert hashlib.sha256(b).hexdigest() == record["sha256"]
            p = OUT / record["local"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
    (OUT / "server_source_manifest.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"collected_at": bundle["collected_at"], "downloaded": sum(r["status"] == "ok" for r in bundle["records"]), "missing": [r for r in bundle["records"] if r["status"] != "ok"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
