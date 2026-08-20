"""Plain-English definitions for the market jargon the dashboard shows.

Use it three ways::

    st.metric("Delivery %", v, help=G.h("delivery_pct"))   # native widget tooltip
    st.markdown(G.head("Smart Money", "bulk_deal", "block_deal"), ...)  # heading + ⓘ
    G.legend("accumulation", "distribution")               # expander of definitions

Keys are snake_case; every entry is one sentence a first-time investor can read.
"""

from __future__ import annotations

import html

import streamlit as st

TERMS: dict[str, tuple[str, str]] = {
    # ---------------------------------------------------------- price action
    "accumulation": ("Accumulation",
        "Steady buying by large players over days — price moves up slowly on rising "
        "volume and delivery, suggesting shares are moving into strong hands."),
    "distribution": ("Distribution",
        "The opposite of accumulation — large holders selling into strength; price "
        "stalls or drifts down while volume stays high."),
    "breakout": ("Breakout",
        "Price closing decisively above a level it repeatedly failed to cross, "
        "usually on above-average volume."),
    "breakdown": ("Breakdown",
        "Price closing below a support level it had been holding, often the mirror "
        "image of a breakout."),
    "momentum": ("Momentum",
        "How fast and consistently a price is moving in one direction; strong "
        "momentum tends to persist in the short term."),
    "gap_up": ("Gap up / gap down",
        "Today's open is above (or below) yesterday's close with no trading in "
        "between — usually news-driven."),
    "ltp": ("LTP",
        "Last Traded Price — the price of the most recent completed trade."),
    "vwap": ("VWAP",
        "Volume-Weighted Average Price — the average price paid through the day, "
        "weighted by how much traded at each price. A common fair-value benchmark."),
    "week52": ("52-week high / low",
        "The highest and lowest price over the past year. Stocks near their 52-week "
        "high often show strength; near the low, weakness."),
    "circuit": ("Circuit limit",
        "Exchange-set daily price band. Once hit, trading in that stock is frozen or "
        "restricted for the day."),

    # ---------------------------------------------------------- volume & flow
    "volume": ("Volume",
        "Number of shares traded. High volume means conviction behind a move."),
    "turnover": ("Turnover",
        "Rupee value traded (price × quantity) — a better size measure than share "
        "count when comparing across stocks."),
    "delivery_pct": ("Delivery %",
        "Share of the day's volume actually delivered to demat accounts instead of "
        "squared off intraday. High delivery = real investor buying, not day trading."),
    "bulk_deal": ("Bulk deal",
        "A trade of more than 0.5% of a company's listed shares, disclosed to the "
        "exchange the same day. Signals a large buyer or seller."),
    "block_deal": ("Block deal",
        "A single negotiated trade of at least ₹10 crore executed in a special window — "
        "typically institution to institution."),
    "fii": ("FII / FPI",
        "Foreign Institutional (Portfolio) Investors — overseas funds. Their net "
        "buying or selling moves Indian indices heavily."),
    "dii": ("DII",
        "Domestic Institutional Investors — Indian mutual funds, insurers and banks. "
        "Often the counterweight to FII flows."),
    "participant_oi": ("Participant-wise OI",
        "NSE's daily breakdown of who holds derivative positions — FII, DII, Pro "
        "(proprietary desks) and Clients (retail)."),
    "short_selling": ("Short selling",
        "Selling shares you don't own, expecting to buy them back cheaper. Rising "
        "short interest signals bearish positioning."),
    "smart_money": ("Smart money",
        "Shorthand for institutional and large-investor flows — bulk deals, block "
        "deals and FII/DII activity — assumed to be better informed."),

    # ---------------------------------------------------------- breadth
    "advance_decline": ("Advance / decline",
        "How many stocks closed up versus down. Measures whether a rally is broad "
        "or driven by a few heavyweights."),
    "ad_ratio": ("A/D ratio",
        "Advances divided by declines. Above 1 means more stocks rose than fell."),
    "market_breadth": ("Market breadth",
        "How widely participation is spread across stocks — strong indices on weak "
        "breadth is a warning sign."),

    # ---------------------------------------------------------- derivatives
    "fno": ("F&O",
        "Futures and Options — contracts whose value derives from an underlying "
        "stock or index."),
    "oi": ("Open Interest (OI)",
        "Total contracts currently open and unsettled. Rising OI means new money is "
        "entering the position."),
    "change_oi": ("Change in OI",
        "Day-on-day change in open interest — read together with price to tell a "
        "long build-up from short covering."),
    "long_buildup": ("Long build-up",
        "Price up and open interest up — new buyers taking fresh long positions."),
    "short_buildup": ("Short build-up",
        "Price down and open interest up — new sellers taking fresh short positions."),
    "short_covering": ("Short covering",
        "Price up but open interest down — existing shorts buying back to exit."),
    "long_unwinding": ("Long unwinding",
        "Price down and open interest down — existing longs booking out."),
    "pcr": ("Put-Call Ratio (PCR)",
        "Put OI divided by call OI. Above 1 is usually read as bearish positioning, "
        "often used as a contrarian sentiment gauge."),
    "strike": ("Strike price",
        "The price at which an option can be exercised."),
    "expiry": ("Expiry",
        "The date a derivatives contract settles. Indian equity F&O expires monthly, "
        "indices weekly."),
    "itm_otm": ("ITM / ATM / OTM",
        "In-, At- or Out-of-the-money — whether an option currently has intrinsic "
        "value relative to the spot price."),
    "premium": ("Premium",
        "The price paid for an option contract."),
    "rollover": ("Rollover",
        "Carrying a position from the expiring contract to the next month. High "
        "rollover shows traders keeping their view."),
    "ban_list": ("Securities in ban",
        "Stocks where F&O open interest has crossed 95% of market-wide limits — no "
        "new positions allowed until it falls back."),
    "iv": ("Implied Volatility (IV)",
        "The volatility the option's price implies. High IV means options are "
        "expensive and a big move is expected."),
    "vix": ("India VIX",
        "The market's expected 30-day Nifty volatility. Spikes signal fear."),
    "daily_volatility": ("Daily volatility",
        "NSE's estimate of a stock's typical one-day price swing, used to set margins."),
    "var_margin": ("VaR margin",
        "Value-at-Risk margin — the deposit the exchange demands to cover a likely "
        "worst-case one-day loss."),

    # ---------------------------------------------------------- valuation
    "pe": ("P/E ratio",
        "Price divided by earnings per share — what you pay for ₹1 of annual profit. "
        "Meaningful only against the company's own history and its peers."),
    "pb": ("P/B ratio",
        "Price divided by book value per share — how the market prices the company's "
        "net assets."),
    "eps": ("EPS",
        "Earnings Per Share — net profit divided by the number of shares."),
    "market_cap": ("Market cap",
        "Share price × total shares — the market's price tag for the whole company."),
    "free_float": ("Free float",
        "Shares actually available to trade, excluding promoter and locked-in holdings."),
    "dividend_yield": ("Dividend yield",
        "Annual dividend divided by share price, as a percentage."),

    # ---------------------------------------------------------- fundamentals
    "revenue": ("Revenue",
        "Total income from sales before any costs are deducted — the top line."),
    "ebitda": ("EBITDA",
        "Earnings before interest, tax, depreciation and amortisation — a rough proxy "
        "for operating cash generation."),
    "pat": ("PAT",
        "Profit After Tax — the bottom line left for shareholders."),
    "operating_margin": ("Operating margin",
        "Operating profit as a percentage of revenue — how much of each rupee of "
        "sales survives operating costs."),
    "standalone": ("Standalone",
        "The parent company's own numbers, excluding subsidiaries."),
    "consolidated": ("Consolidated",
        "The parent plus all subsidiaries combined — usually the truer picture of "
        "group performance."),
    "audited": ("Audited / unaudited",
        "Audited figures have been signed off by auditors — typically the full-year "
        "results. Quarterly numbers are usually unaudited or limited-reviewed."),
    "balance_sheet": ("Balance sheet",
        "A snapshot of what the company owns and owes on one date."),
    "cash_flow": ("Cash flow statement",
        "Where cash actually came from and went — operating, investing and financing."),
    "pnl": ("Profit & loss (P&L)",
        "Income statement for a period — revenue down to net profit."),
    "cross_foot": ("Cross-foot check",
        "A validation that a statement's parts add up to its stated total; a break "
        "usually means an extraction error or an unusual disclosure."),

    # ---------------------------------------------------------- corporate
    "corporate_action": ("Corporate action",
        "Any company event that changes the shares or their value — dividend, bonus, "
        "split, rights issue or buyback."),
    "ex_date": ("Ex-date",
        "The first day a stock trades without the entitlement. Buy on or after it and "
        "you don't get the dividend or bonus."),
    "record_date": ("Record date",
        "The cut-off date the company uses to decide who is eligible for a corporate "
        "action."),
    "bonus": ("Bonus issue",
        "Free extra shares to existing holders. Share count rises, price adjusts down; "
        "your total value is unchanged."),
    "split": ("Stock split",
        "One share divided into several to lower the price per share. Total value is "
        "unchanged."),
    "buyback": ("Buyback",
        "The company purchasing its own shares, reducing share count."),
    "rights_issue": ("Rights issue",
        "New shares offered to existing holders, usually at a discount."),
    "promoter_pledge": ("Promoter pledge",
        "Promoter shares pledged as loan collateral. High pledge is a governance and "
        "forced-selling risk."),
    "concall": ("Earnings concall",
        "The management conference call after results, where guidance and analyst "
        "questions surface details the filing doesn't."),
    "guidance": ("Guidance",
        "Management's own forecast for revenue, margin or growth ahead."),

    # ---------------------------------------------------------- data plumbing
    "bhavcopy": ("Bhav copy",
        "The exchange's official end-of-day price file for every scrip."),
    "snapshot": ("Snapshot",
        "A live-only dataset captured at collection time — it cannot be backfilled "
        "for past dates."),
    "conviction_score": ("Conviction score",
        "This dashboard's own composite rank blending delivery, flows, momentum and "
        "valuation signals. A screening aid, not a recommendation."),
}

CSS = """
<style>
.gl-tip{position:relative;display:inline-block;margin-left:.28rem;cursor:help;
  font-size:.78em;opacity:.55;vertical-align:super;font-weight:600;}
.gl-tip:hover{opacity:1;}
.gl-term{border-bottom:1px dotted currentColor;cursor:help;}
.gl-head{display:inline-flex;align-items:baseline;gap:.15rem;flex-wrap:wrap;}
</style>
"""


def _entry(key: str) -> tuple[str, str]:
    return TERMS.get(key, (key.replace("_", " ").title(), ""))


def h(key: str) -> str:
    """Definition string for a Streamlit widget's `help=` argument."""
    label, body = _entry(key)
    return f"**{label}** — {body}" if body else label


def icon(key: str) -> str:
    """A hoverable ⓘ carrying the definition. Needs unsafe_allow_html."""
    label, body = _entry(key)
    return f'<span class="gl-tip" title="{html.escape(f"{label} — {body}", quote=True)}">ⓘ</span>'


def term(key: str, text: str | None = None) -> str:
    """Inline dotted-underline term with the definition on hover."""
    label, body = _entry(key)
    return (f'<span class="gl-term" title="{html.escape(f"{label} — {body}", quote=True)}">'
            f'{html.escape(text or label)}</span>')


def head(title: str, *keys: str, level: int = 4) -> str:
    """Markdown heading followed by one ⓘ per term."""
    return f'{"#" * level} {title}' + "".join(icon(k) for k in keys)


def legend(*keys: str, title: str = "What do these terms mean?") -> None:
    """Collapsed expander listing the definitions for the terms on a page."""
    keys = keys or tuple(TERMS)
    with st.expander(f"ⓘ {title}"):
        for k in keys:
            label, body = _entry(k)
            st.markdown(f"**{label}** — {body}")


def sidebar() -> None:
    """Searchable glossary of every term, parked in the sidebar."""
    with st.sidebar.expander("ⓘ Glossary"):
        q = st.text_input("Search terms", key="gl_search",
                          placeholder="accumulation, OI, delivery…").strip().lower()
        shown = 0
        for label, body in TERMS.values():
            if q and q not in label.lower() and q not in body.lower():
                continue
            st.markdown(f"**{label}** — {body}")
            shown += 1
        if not shown:
            st.caption("No term matches that search.")


def caption(key: str) -> None:
    """One-line st.caption of a single definition."""
    label, body = _entry(key)
    st.caption(f"ⓘ **{label}** — {body}")
