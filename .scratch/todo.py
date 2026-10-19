import json, os, glob, sys

qdir = sys.argv[1]
path = os.path.join(qdir, "results-summary.json")
done = set()
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        done = set(r["source_pdf"] for r in json.load(f)["results"])
todo = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(qdir, "*.pdf")))]
todo = [t for t in todo if t not in done]
print("TODO %d" % len(todo))
for t in todo:
    print(t)
