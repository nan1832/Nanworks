import json
import re
import unicodedata

p = r"e:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\DataDivision\Singleclass\GLDV2\Church\edit_saint\edit_port_results\results.json"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", (s or "")).lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def walk(x, path="root"):
    if isinstance(x, dict):
        if "target" in x and "predict_after_edit" in x:
            yield path, x
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")


data = json.load(open(p, "r", encoding="utf-8"))
total = 0
hit = 0
ptotal = 0
phit = 0
for path, obj in walk(data):
    total += 1
    t = norm(obj.get("target", ""))
    pr = norm(obj.get("predict_after_edit", ""))
    ok = bool(t and t in pr)
    if ok:
        hit += 1
    if ".portability." in path:
        ptotal += 1
        if ok:
            phit += 1

acc = hit / total * 100 if total else 0
print(f"total={total}")
print(f"hit={hit}")
print(f"acc={acc:.2f}%")
if ptotal:
    pacc = phit / ptotal * 100
    print(f"portability_total={ptotal}")
    print(f"portability_hit={phit}")
    print(f"portability_acc={pacc:.2f}%")
