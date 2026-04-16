"""Create <class>_images inside each <class>_train and <class>_val under Ten_Classes."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
NAMES = [
    "bridge",
    "castle_fort",
    "church",
    "monastery",
    "mosque",
    "museum",
    "palace",
    "sculpture",
    "theatre",
    "tower",
]

for n in NAMES:
    for split in ("train", "val"):
        d = os.path.join(BASE, n, f"{n}_{split}", f"{n}_images")
        os.makedirs(d, exist_ok=True)
        print(d)
