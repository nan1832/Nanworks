import os, subprocess, json

cwd = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset"

results = {}

trae_ralph = os.path.join(cwd, "Trae-Ralph")
results["Trae-Ralph_exists"] = os.path.exists(trae_ralph)
if os.path.exists(trae_ralph):
    results["Trae-Ralph_items"] = os.listdir(trae_ralph)

ralph_loop = os.path.join(cwd, "ralph-loop")
results["ralph-loop_exists"] = os.path.exists(ralph_loop)
if os.path.exists(ralph_loop):
    results["ralph-loop_items"] = os.listdir(ralph_loop)

r1 = subprocess.run(["npm", "--version"], capture_output=True, text=True, cwd=cwd)
r2 = subprocess.run(["node", "--version"], capture_output=True, text=True, cwd=cwd)
results["npm_version"] = r1.stdout.strip() or r1.stderr.strip()
results["node_version"] = r2.stdout.strip() or r2.stderr.strip()

r3 = subprocess.run(["npm", "list", "-g", "--depth=0"], capture_output=True, text=True, cwd=cwd)
results["npm_global_packages"] = r3.stdout.strip() or r3.stderr.strip()

with open(os.path.join(cwd, "final_check.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("done")