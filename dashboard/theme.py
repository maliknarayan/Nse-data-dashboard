"""Design system for the dashboard — lavender canvas, white rounded cards,
indigo + coral palette, Inter type. Mirrors the reference SaaS layout.
"""

from __future__ import annotations

# palette
INDIGO = "#6C63FF"
INDIGO_DK = "#4B45C6"
CORAL = "#F2724B"
GREEN = "#22B07D"
RED = "#EF5B5B"
BG = "#EEF1FB"
CARD = "#FFFFFF"
INK = "#2B2D42"
MUTED = "#8B8FA3"

# sequential/diverging use across native charts
UP = GREEN
DOWN = CORAL

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, Segoe UI, sans-serif;
}}
.stApp {{ background: {BG}; }}

/* hide Streamlit chrome + help tooltips for a clean production frontend */
[data-testid="stHelp"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
#MainMenu {{ visibility: hidden !important; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
footer {{ visibility: hidden !important; }}
/* hide heading anchor link icons */
.stMarkdown a[href^="#"] svg {{ display: none; }}

/* tighten top padding, widen content */
.block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1500px; }}

/* headings */
h1, h2, h3 {{ color: {INK}; font-weight: 700; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.15rem !important; }}
h3 {{ font-size: 1rem !important; color: {INK}; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

/* bordered containers -> cards */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {CARD};
    border: 1px solid rgba(108,99,255,0.08) !important;
    border-radius: 18px;
    box-shadow: 0 8px 26px rgba(60,64,120,0.07);
    padding: 0.6rem 0.9rem;
}}

/* native metric -> soft card */
[data-testid="stMetric"] {{
    background: {CARD};
    border-radius: 16px;
    padding: 14px 18px;
    box-shadow: 0 6px 20px rgba(60,64,120,0.06);
}}
[data-testid="stMetricValue"] {{ font-size: 1.7rem; font-weight: 700; color: {INK}; }}
[data-testid="stMetricLabel"] {{ color: {MUTED}; font-weight: 600; }}

/* sidebar -> indigo rail */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {INDIGO} 0%, {INDIGO_DK} 100%);
}}
[data-testid="stSidebar"] * {{ color: #fff !important; }}
[data-testid="stSidebar"] [data-testid="stMetric"] {{
    background: rgba(255,255,255,0.12); box-shadow: none;
}}
[data-testid="stSidebar"] .stButton>button {{
    background: rgba(255,255,255,0.16); color:#fff; border:none;
    border-radius: 12px; font-weight:600;
}}

/* tabs -> pill row */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{
    background: #fff; border-radius: 12px; padding: 8px 16px;
    font-weight: 600; color: {MUTED}; box-shadow: 0 3px 10px rgba(60,64,120,0.05);
}}
.stTabs [aria-selected="true"] {{ background: {INDIGO}; color: #fff !important; }}

/* buttons */
.stButton>button {{
    background: {INDIGO}; color:#fff; border:none; border-radius: 12px;
    padding: 8px 18px; font-weight: 600;
}}
.stButton>button:hover {{ background: {INDIGO_DK}; }}

/* custom stat cards */
.stat-row {{ display:flex; gap:16px; flex-wrap:wrap; margin: 4px 0 8px; }}
.stat-card {{
    flex:1 1 160px; min-width:150px; background:{CARD}; border-radius:18px;
    padding:18px 20px; box-shadow:0 8px 24px rgba(60,64,120,0.07);
}}
/* mini cards pack left instead of stretching when a row wraps */
.stat-card.mini {{ flex:0 1 190px; }}
.stat-title {{ color:{MUTED}; font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.03em; }}
.stat-value {{ font-size:1.9rem; font-weight:800; color:{INK}; margin-top:4px; }}
.stat-value.up {{ color:{GREEN}; }}
.stat-value.down {{ color:{CORAL}; }}
.stat-value.neutral {{ color:{INDIGO}; }}
.stat-sub {{ color:{MUTED}; font-size:0.82rem; margin-top:2px; }}

.hero {{
    background: linear-gradient(120deg, {INDIGO} 0%, {INDIGO_DK} 100%);
    border-radius: 20px; padding: 20px 26px; color:#fff; margin-bottom: 14px;
    box-shadow: 0 10px 30px rgba(75,69,198,0.25);
}}
.hero h1 {{ color:#fff !important; margin:0; font-size:1.5rem; }}
.hero .sub {{ color: rgba(255,255,255,0.85); font-size:0.9rem; margin-top:4px; }}

/* card hover lift */
[data-testid="stVerticalBlockBorderWrapper"] {{ transition: box-shadow .2s, transform .2s; }}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    box-shadow: 0 14px 36px rgba(60,64,120,0.13);
}}

/* sidebar radio -> vertical nav menu */
[data-testid="stSidebar"] .stRadio > label {{ display:none; }}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {{ gap:3px; }}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {{
    padding:9px 14px; border-radius:11px; width:100%; cursor:pointer;
    font-weight:600; color:rgba(255,255,255,0.82) !important;
    transition: background .15s;
}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {{
    background:rgba(255,255,255,0.10);
}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {{
    background:rgba(255,255,255,0.22);
}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {{ display:none; }}

/* pill badge */
.badge {{ display:inline-block; padding:5px 14px; border-radius:999px;
          font-weight:700; font-size:0.9rem; }}
.badge.up {{ background:rgba(34,176,125,0.15); color:{GREEN}; }}
.badge.down {{ background:rgba(239,91,91,0.15); color:{RED}; }}
.badge.neutral {{ background:rgba(108,99,255,0.12); color:{INDIGO}; }}

/* section title */
.sect {{ margin:2px 0 10px; }}
.sect .t {{ font-size:1.15rem; font-weight:700; color:{INK}; }}
.sect .s {{ font-size:0.85rem; color:{MUTED}; margin-top:1px; }}
</style>
"""


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="badge {tone}">{text}</span>'


def section(title: str, sub: str = "") -> str:
    s = f'<div class="s">{sub}</div>' if sub else ""
    return f'<div class="sect"><div class="t">{title}</div>{s}</div>'


def stat_card(title: str, value, sub: str = "", tone: str = "neutral",
              arrow: bool = False, mini: bool = False) -> str:
    a = ""
    if arrow:
        a = "▲ " if tone == "up" else ("▼ " if tone == "down" else "")
    cls = "stat-card mini" if mini else "stat-card"
    return (f'<div class="{cls}"><div class="stat-title">{title}</div>'
            f'<div class="stat-value {tone}">{a}{value}</div>'
            f'<div class="stat-sub">{sub}</div></div>')


def stat_row(cards: list[str]) -> str:
    return '<div class="stat-row">' + "".join(cards) + "</div>"


def hero(title: str, sub: str) -> str:
    return f'<div class="hero"><h1>{title}</h1><div class="sub">{sub}</div></div>'
