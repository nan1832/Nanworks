import subprocess, json

r1 = subprocess.run(["npm", "--version"], capture_output=True, text=True)
r2 = subprocess.run(["node", "--version"], capture_output=True, text=True)
r3 = subprocess.run(["npm", "list", "-g"], capture_output=True, text=True)

results = {
    "npm_version": r1.stdout.strip() or r1.stderr.strip(),
    "node_version": r2.stdout.strip() or r2.stderr.strip(),
    "npm_list": r3.stdout.strip() or r3.stderr.strip(),
}

with open("check_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("done")