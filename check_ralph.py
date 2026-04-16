import os
import sys

target = os.path.join(os.getcwd(), "ralph2")
if os.path.exists(target):
    items = os.listdir(target)
    print(f"ralph2 exists with {len(items)} items:")
    for i in items:
        print(i)
else:
    print("ralph2 does NOT exist")
    # check if ralph exists
    ralph = os.path.join(os.getcwd(), "ralph")
    if os.path.exists(ralph):
        items = os.listdir(ralph)
        print(f"ralph exists with {len(items)} items:")
        for i in items:
            print(i)
    else:
        print("ralph also does not exist")