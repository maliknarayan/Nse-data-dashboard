import sys
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
end = int(sys.argv[3]) if len(sys.argv) > 3 else 6
with pdfplumber.open(path) as doc:
    print("TOTALPAGES", len(doc.pages))
    for i in range(start - 1, min(end, len(doc.pages))):
        print(f"=== PAGE {i+1} ===")
        print(doc.pages[i].extract_text() or "")
