import json
import os
import sys
import datetime
import tempfile

qdir, recfile = sys.argv[1], sys.argv[2]
path = os.path.join(qdir, "results-summary.json")
data = {"quarter": os.path.basename(qdir.rstrip("\\/")), "directory": qdir, "results": []}
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
data.setdefault("results", [])
with open(recfile, encoding="utf-8") as f:
    rec = json.load(f)
data["results"] = [r for r in data["results"] if r.get("source_pdf") != rec["source_pdf"]]
data["results"].append(rec)
data["count"] = len(data["results"])
data["last_updated"] = datetime.datetime.now().isoformat(timespec="seconds")
fd, tmp = tempfile.mkstemp(dir=qdir, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
os.replace(tmp, path)
print("written:", path, "count:", data["count"], "|", rec["company"])
