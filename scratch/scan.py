import sys, pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
path = sys.argv[1]
with pdfplumber.open(path) as pdf:
    n = len(pdf.pages)
    print("PAGES:", n)
    for i, p in enumerate(pdf.pages):
        t = p.extract_text() or ""
        head = " | ".join(t.split("\n")[:3])[:160]
        hit = "REV" if "Revenue from operations" in t or "Interest earned" in t else ""
        print(f"[{i+1}] {hit} {head}")
