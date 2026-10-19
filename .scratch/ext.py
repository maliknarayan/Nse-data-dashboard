import sys, re, pdfplumber

path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "scan"
doc = pdfplumber.open(path)
pages = [(i, p.extract_text() or "") for i, p in enumerate(doc.pages)]

if mode == "scan":
    print("PAGES:", len(pages))
    print("=== HEAD ===")
    print("\n".join(t for _, t in pages[:2])[:1500])
    pat = re.compile(r"Revenue from operations|Total income|Total Income")
    hits = [i + 1 for i, t in pages if pat.search(t)]
    print("=== FINPAGES ===", hits)
elif mode == "pages":
    want = set(int(x) - 1 for x in sys.argv[3].split(","))
    for i, t in pages:
        if i in want:
            print("----- PAGE %d -----" % (i + 1))
            print(t)
else:
    for i, t in pages:
        print("----- PAGE %d -----" % (i + 1))
        print(t)
