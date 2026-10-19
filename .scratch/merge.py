import json, os, sys, time, datetime, tempfile

qdir, recfile = sys.argv[1], sys.argv[2]
path = os.path.join(qdir, "results-summary.json")
lock = path + ".lock"

# crude cross-process lock; another agent run writes this same file
fd = None
for _ in range(120):
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        break
    except FileExistsError:
        time.sleep(0.5)
if fd is None:
    print("LOCK TIMEOUT")
    sys.exit(1)

try:
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
    h, tmp = tempfile.mkstemp(dir=qdir, suffix=".tmp")
    with os.fdopen(h, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    print("written:", path, "count:", data["count"])
finally:
    os.close(fd)
    os.unlink(lock)
