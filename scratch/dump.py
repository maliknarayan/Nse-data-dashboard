import sys, pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
path = sys.argv[1]
pages = [int(x) for x in sys.argv[2].split(",")]
with pdfplumber.open(path) as pdf:
    for i in pages:
        print(f"########## PAGE {i} ##########")
        print(pdf.pages[i - 1].extract_text() or "(no text)")
