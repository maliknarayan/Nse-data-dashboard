import sys, os, re, glob, pdfplumber

qdir = sys.argv[1]
files = sorted(glob.glob(os.path.join(qdir, "*.pdf")))
pat = re.compile(r"Revenue from operations|Total income|Total Income")
for f in files:
    print("########## " + os.path.basename(f))
    try:
        doc = pdfplumber.open(f)
        pages = [(i, p.extract_text() or "") for i, p in enumerate(doc.pages)]
        head = "\n".join(t for _, t in pages[:2])
        print("PAGES: %d  CHARS: %d" % (len(pages), sum(len(t) for _, t in pages)))
        print(head[:900])
        print("FINPAGES:", [i + 1 for i, t in pages if pat.search(t)][:20])
    except Exception as e:
        print("ERROR:", e)
    print()
