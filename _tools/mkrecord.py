import json
import sys
import datetime

# builds one result record from raw per-column line items, computes ebitda/growth/post_text

COLS = ("current", "yoy", "qoq")


def pct(cur, base):
    if cur is None or base is None or base == 0 or base < 0:
        return None
    return round((cur - base) / abs(base) * 100, 2)


def series(vals, kind="pct"):
    out = {c: vals.get(c) for c in COLS}
    if kind == "pct":
        out["yoy_pct"] = pct(vals.get("current"), vals.get("yoy"))
        out["qoq_pct"] = pct(vals.get("current"), vals.get("qoq"))
    elif kind == "bps":
        for k, base in (("yoy_bps", "yoy"), ("qoq_bps", "qoq")):
            c, b = vals.get("current"), vals.get(base)
            out[k] = round((c - b) * 100) if c is not None and b is not None else None
    return out


def fmt(v, dp=2):
    return f"{v:.{dp}f}"


def signed(v):
    return f"{'+' if v >= 0 else ''}{v:.2f}"


def line(label, s, unit):
    c, y, q = s["current"], s["yoy"], s["qoq"]
    if c is None:
        return ""
    yp, qp = s.get("yoy_pct"), s.get("qoq_pct")
    # negative/missing base -> no percentage, use the vs ... YoY & ... QoQ form
    if y is None or q is None or yp is None or qp is None:
        parts = [f"{label} {signed(c)} {unit}"]
        tail = []
        if y is not None:
            tail.append(f"{signed(y)} {unit} YoY")
        if q is not None:
            tail.append(f"{signed(q)} {unit} QoQ")
        txt = parts[0] + (" vs " + " & ".join(tail) if tail else "")
        pcts = []
        if yp is not None:
            pcts.append(f"({yp:+.2f}% YoY)")
        if qp is not None:
            pcts.append(f"({qp:+.2f}% QoQ)")
        return txt + ("\n" + " ".join(pcts) if pcts else "") + "\n"
    return (f"{label} {fmt(c)} {unit} vs {fmt(y)} {unit}\n"
            f"({yp:+.2f}% YoY┃{qp:+.2f}% QoQ)\n")


def build(raw):
    unit = raw.get("currency_unit", "Cr")
    f = {}
    for key in ("revenue", "other_income", "depreciation", "finance_cost", "pbt",
                "pbt_ex_exceptional", "pat", "pat_after_minority", "pat_before_jv",
                "pat_continuing_operations"):
        if key in raw:
            f[key] = series(raw[key])

    # banks: no ebitda, operating line is pre-provision operating profit
    if raw.get("bank"):
        for key in ("total_income", "operating_profit_(pre_provision)"):
            if key in raw:
                f[key] = series(raw[key])
        f["exceptional_item"] = {c: raw.get("exceptional_item", {}).get(c) for c in COLS}
        order = ["revenue", "total_income", "operating_profit_(pre_provision)", "pbt",
                 "pat", "pat_after_minority", "other_income", "exceptional_item"]
        f = {k: f[k] for k in order if k in f}
        labels = {"revenue": "Revenue", "total_income": "Total Income",
                  "operating_profit_(pre_provision)": "Operating Profit (Pre-Provision)",
                  "pbt": "PBT", "pat": "PAT",
                  "pat_after_minority": "PAT After Minority interest"}
        body = [f"{raw['company']} Q{raw['q']} Results:-",
                f"#Q{raw['q'][0]}Results #Q{raw['q']} #Stockmarket #Nifty #{raw['tag']}", ""]
        for k, s in f.items():
            if k in ("other_income", "exceptional_item"):
                continue
            t = line(labels[k], s, unit)
            if t:
                body.append(t)
        oi = f.get("other_income")
        if oi and oi["current"] is not None:
            body.append(f"Other Income {fmt(oi['current'])} {unit} vs {fmt(oi['yoy'])} {unit} YoY & {fmt(oi['qoq'])} {unit} QoQ\n")
        txt = "\n\n".join(l.rstrip("\n") for l in "\n".join(body).split("\n\n") if l.strip())
        return _wrap(raw, f, txt, unit)

    ebitda, margin = {}, {}
    for c in COLS:
        # some filings put JV/associate share above PBT; ebitda_base isolates own operations
        pbtx = raw.get("ebitda_base", raw.get("pbt_ex_exceptional", {})).get(c)
        dep = raw.get("depreciation", {}).get(c)
        fin = raw.get("finance_cost", {}).get(c)
        oi = raw.get("other_income", {}).get(c)
        rev = raw.get("revenue", {}).get(c)
        if None in (pbtx, dep, fin, oi):
            ebitda[c] = margin[c] = None
            continue
        e = raw.get("ebitda_override", {}).get(c)
        if e is None:
            e = round(pbtx + dep + fin - oi, 2)
        ebitda[c] = e
        margin[c] = round(e / rev * 100, 2) if rev else None
    f["ebitda"] = series(ebitda)
    f["ebitda_margin"] = series(margin, kind="bps")
    f["exceptional_item"] = {c: raw.get("exceptional_item", {}).get(c) for c in COLS}

    order = ["revenue", "ebitda", "ebitda_margin", "pbt_ex_exceptional", "pbt",
             "pat_before_jv", "pat_continuing_operations", "pat", "pat_after_minority",
             "other_income"]
    f = {k: f[k] for k in order if k in f} | {"exceptional_item": f["exceptional_item"]}

    labels = {
        "revenue": "Revenue", "ebitda": "EBITDA", "pbt": "PBT",
        "pbt_ex_exceptional": "PBT Ex-Exceptional Items", "pat": "PAT",
        "pat_after_minority": "PAT After Minority interest",
        "pat_before_jv": "PAT Before Share of JV & Associates",
        "pat_continuing_operations": "PAT from Continuing Operations",
    }
    # drop the ex-exceptional line when it equals reported pbt everywhere
    if "pbt_ex_exceptional" in f and "pbt" in f:
        same = all(f["pbt_ex_exceptional"][c] == f["pbt"][c] for c in COLS)
        if same:
            del f["pbt_ex_exceptional"]
        else:
            labels["pbt"] = "PBT (reported)"

    body = [f"{raw['company']} Q{raw['q']} Results:-",
            f"#Q{raw['q'][0]}Results #Q{raw['q']} #Stockmarket #Nifty #{raw['tag']}", ""]
    for k, s in f.items():
        if k in ("ebitda_margin", "other_income", "exceptional_item"):
            continue
        t = line(labels[k], s, unit)
        if t:
            body.append(t)
    m = f["ebitda_margin"]
    if m["current"] is not None:
        body.append(f"EBITDA Margin {m['current']:.2f}% vs {m['yoy']:.2f}% YoY & {m['qoq']:.2f}% QoQ\n")
    oi = f.get("other_income")
    if oi and oi["current"] is not None:
        body.append(f"Other Income {fmt(oi['current'])} {unit} vs {fmt(oi['yoy'])} {unit} YoY & {fmt(oi['qoq'])} {unit} QoQ\n")
    for c, lbl in (("current", f"This Q{raw['q'][0]}"), ("qoq", f"Last Q{raw['qoq_label']}")):
        ex = f["exceptional_item"].get(c)
        if ex:
            body.append(f"{lbl} Exceptional {'gain' if ex > 0 else 'loss'} of {abs(ex):.2f} {unit}\n")

    # margin line sits right after ebitda in the house format
    txt = "\n".join(body)
    lines = txt.split("\n\n")
    if m["current"] is not None:
        mline = f"EBITDA Margin {m['current']:.2f}% vs {m['yoy']:.2f}% YoY & {m['qoq']:.2f}% QoQ"
        lines = [l for l in lines if not l.startswith("EBITDA Margin")]
        for i, l in enumerate(lines):
            if l.startswith("EBITDA "):
                lines.insert(i + 1, mline)
                break
    txt = "\n\n".join(l.rstrip("\n") for l in lines if l.strip())

    return _wrap(raw, f, txt, unit)


def _wrap(raw, f, txt, unit):
    return {
        "company": raw["company"],
        "source_pdf": raw["source_pdf"],
        "quarter": "Q" + raw["q"],
        "basis": raw["basis"],
        "is_sme": raw.get("is_sme"),
        "currency_unit": unit,
        "financials": f,
        "verdict": raw["verdict"],
        "sub_verdict": raw["sub_verdict"],
        "tags": raw.get("tags", []),
        "verdict_reason": raw["verdict_reason"],
        "positives": raw.get("positives", []),
        "red_flags": raw.get("red_flags", []),
        "notes": raw.get("notes", ""),
        "qoq_base_reliable": raw.get("qoq_base_reliable", True),
        "post_text": txt,
        "analyzed_on": datetime.date.today().isoformat(),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with open(sys.argv[1], encoding="utf-8") as fh:
        raw = json.load(fh)
    rec = build(raw)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
    print(json.dumps(rec["financials"], indent=2))
    print("----POST----")
    print(rec["post_text"])
