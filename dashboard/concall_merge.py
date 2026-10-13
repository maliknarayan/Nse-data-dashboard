"""Rebuild a quarter's concalls-summary.json from the per-company snapshots.

Replaces the read-merge-write step concall-reader used to run once per transcript.
Run once after a batch:  python -m dashboard.concall_merge concall-data/Q1FY27
"""

import datetime
import glob
import json
import os
import sys
import tempfile

SUMMARY = "concalls-summary.json"
# snapshots sit in the quarter root and in result-json/ after the tidy-up move
SNAPSHOT_DIRS = (".", "result-json")


def snapshots(qdir: str) -> list[str]:
    found = []
    for sub in SNAPSHOT_DIRS:
        for p in glob.glob(os.path.join(qdir, sub, "*.json")):
            if os.path.basename(p) != SUMMARY:
                found.append(p)
    return sorted(found)


def load(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"skip (unreadable): {os.path.basename(path)} — {exc}")
        return None
    if not isinstance(rec, dict) or not rec.get("company"):
        print(f"skip (not a snapshot): {os.path.basename(path)}")
        return None
    rec.setdefault("source_md", os.path.basename(path).replace(".json", ".md"))
    rec.setdefault(
        "analyzed_on",
        datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat(),
    )
    return rec


def key_of(rec: dict) -> str:
    """Same identity loader.concall_index uses — the transcript, not the company string.

    Company names drift between runs ("MM Forgings" vs "MM Forgings Limited"), so
    keying on the name alone double-counts the same call.
    """
    src = str(rec.get("source_pdf") or "").strip()
    # snapshots record the pdf inconsistently — full path in some, basename in others
    return (os.path.basename(src.replace("\\", "/")) or str(rec.get("company"))).strip().lower()


def existing(qdir: str) -> list[dict]:
    """Records already in the summary — keeps a company whose snapshot went corrupt."""
    path = os.path.join(qdir, SUMMARY)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("concalls") or []
    except (OSError, json.JSONDecodeError):
        return []


def build(qdir: str) -> dict:
    by_call: dict[str, dict] = {}
    for rec in existing(qdir):
        if isinstance(rec, dict) and rec.get("company"):
            by_call[key_of(rec)] = rec
    for path in snapshots(qdir):
        rec = load(path)
        if rec is None:
            continue
        prev = by_call.get(key_of(rec))
        # newest analysis of a given transcript wins
        if prev is None or str(rec.get("analyzed_on") or "") >= str(prev.get("analyzed_on") or ""):
            by_call[key_of(rec)] = rec
    concalls = sorted(by_call.values(), key=lambda r: r["company"].lower())
    return {
        "quarter": os.path.basename(qdir.rstrip("\\/")),
        "directory": qdir,
        "count": len(concalls),
        "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
        "concalls": concalls,
    }


def write(qdir: str, data: dict) -> str:
    path = os.path.join(qdir, SUMMARY)
    fd, tmp = tempfile.mkstemp(dir=qdir, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    qdir = os.path.abspath(argv[1])
    if not os.path.isdir(qdir):
        print(f"not a directory: {qdir}")
        return 1
    data = build(qdir)
    print("written:", write(qdir, data), "count:", data["count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
