"""Turn word boxes into (label, period, value) triples.

Column identity comes from x-geometry, never from token order — real filings
order the quarter block [current, YoY, prior] as often as [current, prior, YoY],
and a positional parser silently swaps periods without raising. Group headers
("Quarter ended", "Year ended") sit centred over their column block, so each
numeric column is assigned to the nearest group-label centre.
"""

from __future__ import annotations

import datetime as dt
import re

from . import taxonomy as TX

Word = tuple[float, float, float, float, str]

# rows within this many points share a baseline
ROW_TOL = 3.5
# numeric right edges within this many points belong to one column
COL_TOL = 7.0

_NUM = re.compile(r"^[(_\[]?-?[\d][\d,.\s]*[)\]]?$")
# a printed figure always carries decimals; years and roman-numeral markers do not
_FIG = re.compile(r"^[(_\[]?-?[\d][\d,.\s]*\.\s?\d{1,2}[)\]]?$")
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_UNITS = [
    (r"in\s*million", 1e6), (r"in\s*mn", 1e6),
    (r"in\s*lakh", 1e5), (r"in\s*lac", 1e5),
    (r"in\s*crore", 1e7), (r"in\s*cr\b", 1e7),
    (r"in\s*thousand", 1e3),
]
_GROUPS = [
    (r"nine month", "nine_month"), (r"six month", "half_year"),
    (r"half year", "half_year"), (r"quarter ended", "quarter"),
    (r"year ended", "year"), (r"year to date", "ytd"), (r"as at", "as_at"),
]


def canon(tok: str) -> str:
    """Repair the numeric OCR damage seen in real filings.

    '1,1 10.45' -> '1,110.45' (space injected mid-number)
    '(70. 10)'  -> '(70.10)'  (space after the decimal point)
    '89,39'     -> '89.39'    (decimal point read as a comma)

    The decimal-comma fix is safe because every figure in these statements
    carries two decimals, and Indian grouping never leaves a 2-digit final
    group ('1,23,456' ends in a 3-digit group).
    """
    t = tok.strip().lstrip("_[").rstrip("]")
    t = re.sub(r"[.,]\s+(?=\d)", lambda m: m.group(0)[0], t)
    t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)
    if "." not in t and re.search(r",\d{2}$", t):
        i = t.rfind(",")
        t = t[:i] + "." + t[i + 1:]
    return t


_DASH = re.compile(r"^[-—–]$")


def is_nil(tok: str) -> bool:
    """A printed dash — the filing reports this line as nil, which is not the
    same as not reporting it at all."""
    return bool(_DASH.match(tok.strip()))


def is_number(tok: str) -> bool:
    t = canon(tok)
    return bool(_NUM.match(t)) and any(c.isdigit() for c in t)


def is_figure(tok: str) -> bool:
    """Stricter than is_number — used to find the columns, so header years
    ('2025') and row markers ('1', 'Ill') must not qualify."""
    return bool(_FIG.match(canon(tok)))


def to_value(tok: str) -> float | None:
    """Parse a printed figure. Returns None for a blank/dash — never 0."""
    t = canon(tok).replace(" ", "")
    if t in {"", "-", "—", "–", "nil"}:
        return None
    neg = t.startswith("(") or t.endswith(")")
    t = t.strip("()").replace(",", "")
    # OCR renders thousands separators as periods: 2.613.39 -> 2613.39
    if t.count(".") > 1:
        head, _, tail = t.rpartition(".")
        t = head.replace(".", "") + "." + tail
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def group_rows(words: list[Word]) -> list[tuple[float, list[Word]]]:
    """Cluster words into visual rows by baseline."""
    rows: list[tuple[float, list[Word]]] = []
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        if rows and abs(w[1] - rows[-1][0]) <= ROW_TOL:
            rows[-1][1].append(w)
        else:
            rows.append((w[1], [w]))
    return [(y, sorted(g, key=lambda w: w[0])) for y, g in rows]


def detect_unit(text: str) -> float | None:
    low = text.lower().replace("\n", " ")
    for pat, scale in _UNITS:
        if re.search(pat, low):
            return scale
    return None


def detect_statement(text: str) -> str | None:
    low = text.lower()
    if "cash flow" in low:
        return TX.CF
    if "balance sheet" in low or "assets and liabilities" in low:
        return TX.BS
    if "financial results" in low:
        return TX.PNL
    return None


def detect_basis(text: str) -> str:
    low = text.lower()
    if "consolidated" in low:
        return "consolidated"
    return "standalone"


def column_bands(rows: list[tuple[float, list[Word]]]) -> list[tuple[float, float, float]]:
    """(right_edge, x0, x1) per figure column.

    Figures are right-aligned so clustering happens on the right edge, but the
    full span is kept too: header dates and group labels are centre-aligned, and
    matching those against a right edge biases every token into the next column.
    """
    pairs: list[tuple[float, float]] = []
    for _, g in rows:
        figs = [w for w in g if is_figure(w[4])]
        if len(figs) >= 2:
            pairs.extend((w[2], w[0]) for w in figs)
    if not pairs:
        return []
    pairs.sort()
    clusters: list[list[tuple[float, float]]] = [[pairs[0]]]
    for p in pairs[1:]:
        if p[0] - clusters[-1][-1][0] <= COL_TOL:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    # a real column appears on most data rows; drop stray alignments
    top = max(len(c) for c in clusters)
    keep = [c for c in clusters if len(c) >= max(3, top // 3)] or clusters
    return [(sum(x1 for x1, _ in c) / len(c),
             min(x0 for _, x0 in c), max(x1 for x1, _ in c)) for c in keep]


def vcentre(band: tuple[float, float, float]) -> float:
    """Visual centre of a column — what centred header text aligns to."""
    return (band[1] + band[2]) / 2


def _centre(w: Word) -> float:
    return (w[0] + w[2]) / 2


def _nearest_band(x: float, bands: list[tuple[float, float, float]]) -> int:
    """For right-aligned figures — compare against the column's right edge."""
    return min(range(len(bands)), key=lambda i: abs(bands[i][0] - x))


def _nearest_vband(x: float, bands: list[tuple[float, float, float]]) -> int:
    """For centred header text — compare against the column's visual centre."""
    return min(range(len(bands)), key=lambda i: abs(vcentre(bands[i]) - x))


def _dates_from(tokens: list[str]) -> dt.date | None:
    """Pull a date out of header tokens, tolerating fused '312024'."""
    parts: list[str] = []
    for t in tokens:
        t = t.strip().strip("|,")
        # OCR fuses day and year
        m = re.fullmatch(r"(\d{1,2})(\d{4})", t)
        if m:
            parts.extend(m.groups())
        else:
            parts.append(t)
    blob = " ".join(parts).lower()
    mon = next((_MONTHS[k] for k in sorted(_MONTHS, key=len, reverse=True)
                if re.search(rf"\b{k}\b", blob)), None)
    if not mon:
        return None
    nums = re.findall(r"\b(\d{1,4})\b", blob)
    day = next((int(n) for n in nums if 1 <= int(n) <= 31 and len(n) <= 2), None)
    year = next((int(n) for n in nums if len(n) == 4 and 1990 < int(n) < 2100), None)
    if not (day and year):
        return None
    try:
        return dt.date(year, mon, day)
    except ValueError:
        return None


def fiscal_label(end: dt.date, period_type: str) -> str:
    """Indian FY label — FY26 spans Apr-2025..Mar-2026."""
    fy = end.year if end.month <= 3 else end.year + 1
    yy = f"FY{fy % 100:02d}"
    if period_type == "quarter":
        q = {6: "Q1", 9: "Q2", 12: "Q3", 3: "Q4"}.get(end.month)
        return f"{q}{yy}" if q else f"{end.isoformat()}"
    return {"half_year": f"H1{yy}", "nine_month": f"9M{yy}",
            "year": yy, "as_at": f"AsAt-{end.isoformat()}",
            "ytd": f"YTD{yy}"}.get(period_type, yy)


# words further apart than this belong to different header labels
LABEL_GAP = 20.0


def _runs(g: list[Word], gap: float = LABEL_GAP) -> list[list[Word]]:
    """Split a row into space-separated phrases."""
    out: list[list[Word]] = []
    for w in g:
        if out and w[0] - out[-1][-1][2] <= gap:
            out[-1].append(w)
        else:
            out.append([w])
    return out


def _group_labels(header: list[tuple[float, list[Word]]]) -> list[tuple[float, str]]:
    """(centre, period_type) for each group header, e.g. 'Nine Month Ended'.

    Read as whole phrases — a run's centre is the centre of the column block it
    spans, which is what makes the column-to-group mapping fall out.
    """
    best: list[tuple[float, str]] = []
    for _, g in header:
        found: list[tuple[float, str]] = []
        for run in _runs(g):
            blob = " ".join(w[4] for w in run).lower()
            for pat, ptype in _GROUPS:
                if re.search(pat, blob):
                    found.append(((run[0][0] + run[-1][2]) / 2, ptype))
                    break
        if len(found) > len(best):
            best = found
    return sorted(best)


# cash flow is always cumulative from 1 April, so its span follows the end month
_CF_SPAN = {6: "quarter", 9: "half_year", 12: "nine_month", 3: "year"}
_TITLE_WORDS = ("statement", "balance sheet", "cash flow", "assets and liabilities")


def parse_periods(rows: list[tuple[float, list[Word]]],
                  bands: list[tuple[float, float, float]],
                  first_data_y: float,
                  statement: str = TX.PNL) -> list[dict | None]:
    """One period descriptor per column band."""
    header = [(y, g) for y, g in rows if y < first_data_y]
    labels = _group_labels(header)

    def date_tokens(g: list[Word]) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        for w in g:
            if any(c.isdigit() for c in w[4]) or w[4].lower().strip(".,|") in _MONTHS:
                out.setdefault(_nearest_vband(_centre(w), bands), []).append(w[4])
        return out

    # date row: the header row whose tokens resolve to the most dates
    best: tuple[int, list[Word]] = (0, [])
    for _, g in header:
        hits = sum(1 for toks in date_tokens(g).values() if _dates_from(toks))
        if hits > best[0]:
            best = (hits, g)
    date_row = best[1]

    # audited flag row
    audited: dict[int, bool] = {}
    for _, g in header:
        for w in g:
            low = w[4].lower().strip("_ |")
            if low in ("audited", "unaudited"):
                audited[_nearest_vband(_centre(w), bands)] = low == "audited"

    dates: list[dt.date | None] = []
    for i in range(len(bands)):
        toks = [w[4] for w in date_row if _nearest_vband(_centre(w), bands) == i]
        dates.append(_dates_from(toks))

    # BS/CF headers wrap across lines ('March 31,' and '2025' on separate rows);
    # pool every non-title header row for the columns that came up empty
    if not all(dates):
        pooled: dict[int, list[str]] = {}
        for _, g in header:
            blob = " ".join(w[4] for w in g).lower()
            if any(t in blob for t in _TITLE_WORDS):
                continue
            for bi, toks in date_tokens(g).items():
                pooled.setdefault(bi, []).extend(toks)
        for i in range(len(bands)):
            if dates[i] is None:
                dates[i] = _dates_from(pooled.get(i, []))

    if statement == TX.BS:
        ptypes: list[str | None] = ["as_at"] * len(bands)
    elif statement == TX.CF:
        ptypes = [_CF_SPAN.get(d.month) if d else None for d in dates]
    else:
        ptypes = _assign_groups(dates, labels, bands)

    out: list[dict | None] = []
    for i, end in enumerate(dates):
        ptype = ptypes[i]
        if not end or not ptype:
            out.append(None)
            continue
        out.append({"period_end": end.isoformat(), "period_type": ptype,
                    "fiscal_label": fiscal_label(end, ptype),
                    "audited": audited.get(i)})
    return out


def _geometry_groups(labels: list[tuple[float, str]],
                     bands: list[tuple[float, float, float]]) -> list[str | None]:
    """Fallback: split columns at the midpoints between label centres."""
    if not labels:
        return [None] * len(bands)
    bounds = [(labels[i][0] + labels[i + 1][0]) / 2 for i in range(len(labels) - 1)]
    out = []
    for b in bands:
        x, idx = vcentre(b), 0
        while idx < len(bounds) and x > bounds[idx]:
            idx += 1
        out.append(labels[idx][1])
    return out


def _assign_groups(dates: list[dt.date | None], labels: list[tuple[float, str]],
                   bands: list[tuple[float, float, float]]) -> list[str | None]:
    """Map each column to a period type using the dates, not pixel centres.

    Cumulative blocks restate the primary column's period end, so the first
    repeat of ``dates[0]`` is exactly where the quarter block stops. Label
    centres sit only a point or two from a column boundary in real filings, so
    geometry is the fallback rather than the rule.
    """
    n = len(bands)
    fallback = _geometry_groups(labels, bands)
    if not labels or dates[0] is None:
        return fallback
    if len(labels) == 1:
        return [labels[0][1]] * n

    split = next((i for i in range(1, n) if dates[i] == dates[0]), None)
    if split is None:
        return fallback

    out: list[str | None] = [labels[0][1]] * split
    rest = list(range(split, n))
    if len(labels) == 2:
        out += [labels[1][1]] * len(rest)
        return out

    # trailing fiscal-year-end columns form the final 'year ended' block
    tail = 0
    for i in reversed(rest):
        d = dates[i]
        if d is not None and d.month == 3 and d != dates[0]:
            tail += 1
        else:
            break
    if tail == 0 or tail == len(rest):
        return fallback
    out += [labels[1][1]] * (len(rest) - tail)
    out += [labels[-1][1]] * tail
    return out


def parse_lines(rows: list[tuple[float, list[Word]]],
                bands: list[tuple[float, float, float]],
                statement: str) -> list[tuple[str, int, str]]:
    """(tag, band index, raw token) for every recognised line item."""
    left_edge = min(b[1] for b in bands)
    out = []
    for _, g in rows:
        # only decimal-bearing tokens count as figures — every value in these
        # statements is printed to 2 places, so a bare integer is an OCR fragment
        # ('58' left over from '1.58'), not a number to trust
        nums = [w for w in g
                if (is_figure(w[4]) or is_nil(w[4])) and w[0] >= left_edge - 30]
        if not nums:
            continue
        label = " ".join(w[4] for w in g if w[2] < left_edge - 25)
        hit = TX.match(label, statement)
        if not hit:
            continue
        tag, _ = hit
        for w in nums:
            out.append((tag, _nearest_band(_centre(w), bands), w[4]))
    return out
