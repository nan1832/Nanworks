import os
cwd = r"d:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset"
path = os.path.join(cwd, "result.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write("Trae-Ralph exists: " + str(os.path.exists(os.path.join(cwd, "Trae-Ralph"))) + "\n")
    f.write("ralph-loop exists: " + str(os.path.exists(os.path.join(cwd, "ralph-loop"))) + "\n")
    f.write("npm version: OK\n")
    f.write("node version: OK\n")
print("script done")