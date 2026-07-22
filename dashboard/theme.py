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

/* hide ONLY Deploy/menu/decoration/footer. Keep the header + native sidebar
   toggle fully intact so open/close always works. */
[data-testid="stHelp"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
footer {{ visibility: hidden !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
/* the « collapse button lives on the indigo sidebar -> make it white/visible */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] svg {{ color:#fff !important; fill:#fff !important; }}
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

/* global font smoothing */
* {{ -webkit-font-smoothing: antialiased; }}

/* refined scrollbars */
::-webkit-scrollbar {{ width:10px; height:10px; }}
::-webkit-scrollbar-thumb {{ background:rgba(108,99,255,0.35); border-radius:10px; }}
::-webkit-scrollbar-track {{ background:transparent; }}

/* dataframe: branded header, zebra, rounded */
[data-testid="stDataFrame"] {{ border-radius:12px; overflow:hidden; border:1px solid rgba(108,99,255,0.10); }}
[data-testid="stDataFrame"] thead tr th {{
    background:#F3F2FF !important; color:{INK} !important; font-weight:700 !important;
}}

/* card section headings (h4) get an accent tick */
[data-testid="stVerticalBlockBorderWrapper"] h4 {{
    border-left:3px solid {INDIGO}; padding-left:10px; margin-bottom:8px;
}}

/* inputs rounded */
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea,
.stDateInput input {{ border-radius:10px !important; }}

/* brand block in sidebar */
.brand {{ display:flex; align-items:center; gap:10px; padding:4px 2px 0; }}
.brand .logo {{ width:34px; height:34px; border-radius:10px; background:rgba(255,255,255,0.2);
    display:flex; align-items:center; justify-content:center; font-size:1.2rem; }}
.brand .nm {{ font-weight:800; font-size:1.05rem; color:#fff; line-height:1; }}
.brand .tg {{ font-size:0.72rem; color:rgba(255,255,255,0.75); }}

/* hero refinement */
.hero {{ position:relative; overflow:hidden; }}
.hero::after {{ content:""; position:absolute; right:-40px; top:-40px; width:180px; height:180px;
    background:radial-gradient(circle, rgba(255,255,255,0.18), transparent 70%); }}
</style>
"""


# ==================== MODERN POLISH (design refinement layer) ===============
POLISH = f"""
<style>
/* vertical rhythm + breathing room */
.block-container {{ padding-top:1.2rem; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ padding:1.05rem 1.2rem !important; margin-bottom:2px; }}
[data-testid="stHorizontalBlock"] {{ gap:16px; }}

/* stat cards: accent stripe + stronger hierarchy */
.stat-card {{ position:relative; overflow:hidden; padding:20px 22px !important;
  box-shadow:0 1px 2px rgba(60,64,120,0.06), 0 10px 28px rgba(60,64,120,0.08) !important; }}
.stat-card::before {{ content:""; position:absolute; left:0; top:0; height:100%; width:5px; background:{INDIGO}; }}
.stat-card:has(.up)::before {{ background:{GREEN}; }}
.stat-card:has(.down)::before {{ background:{CORAL}; }}
.stat-card:has(.neutral)::before {{ background:{INDIGO}; }}
.stat-title {{ letter-spacing:.06em; font-size:.72rem; }}
.stat-value {{ font-size:2rem; letter-spacing:-.02em; }}
.stat-sub {{ font-size:.8rem; }}

/* hero: richer gradient + depth */
.hero {{ background:linear-gradient(120deg,{INDIGO} 0%, {INDIGO_DK} 60%, #372FA6 100%) !important;
  padding:22px 28px !important; box-shadow:0 12px 34px rgba(75,69,198,0.30) !important; }}
.hero h1 {{ font-size:1.6rem; }}

/* section headings inside cards */
[data-testid="stVerticalBlockBorderWrapper"] h4 {{ font-size:1.02rem !important; margin:2px 0 10px; }}

/* callouts (st.info/success/warning) -> soft rounded */
[data-testid="stAlert"] {{ border-radius:14px !important; border:none !important;
  box-shadow:0 4px 14px rgba(60,64,120,0.06); }}

/* buttons: gradient + lift */
.stButton>button {{ background:linear-gradient(135deg,{INDIGO},{INDIGO_DK}) !important;
  box-shadow:0 6px 16px rgba(75,69,198,0.28); }}
.stButton>button:hover {{ transform:translateY(-1px); }}

/* sidebar nav active: left accent bar */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {{
  box-shadow:inset 3px 0 0 #fff; }}

/* dataframe polish */
[data-testid="stDataFrame"] {{ box-shadow:0 6px 18px rgba(60,64,120,0.06); }}

/* inputs focus ring */
.stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus {{
  border-color:{INDIGO} !important; box-shadow:0 0 0 3px rgba(108,99,255,0.15) !important; }}
</style>
"""


# ==================== AURORA THEME (premium dark fintech) ===================
# dark canvas, teal + gold accents, glowing key numbers. Retail-friendly but
# high perceived value. Additive override applied on top of modern base.
AURORA = """
<style>
:root {
  --a-bg:#0E1117; --a-card:#1A1F2E; --a-line:#2A3142; --a-ink:#E6E9F0;
  --a-muted:#8A93A6; --a-teal:#00E0B8; --a-gold:#F5C451; --a-red:#FF5C7A; --a-indigo:#7C83FF;
}
.stApp { background:var(--a-bg) !important; color:var(--a-ink) !important; }
h1,h2,h3,h4,h5 { color:var(--a-ink) !important; }
.stMarkdown, .stMarkdown p, label, .stCaption, [data-testid="stCaptionContainer"] { color:var(--a-muted) !important; }

/* cards */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--a-card) !important; border:1px solid var(--a-line) !important;
  border-radius:16px !important; box-shadow:0 8px 30px rgba(0,0,0,0.35) !important; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color:rgba(0,224,184,0.35) !important; }
[data-testid="stVerticalBlockBorderWrapper"] h4 { border-left-color:var(--a-teal) !important; }

/* metrics + stat cards + glow */
[data-testid="stMetric"], .stat-card { background:var(--a-card) !important; border:1px solid var(--a-line) !important;
  box-shadow:0 8px 24px rgba(0,0,0,0.35) !important; }
.stat-title { color:var(--a-muted) !important; }
.stat-value { color:var(--a-ink) !important; }
.stat-value.up { color:var(--a-teal) !important; text-shadow:0 0 18px rgba(0,224,184,0.45); }
.stat-value.down { color:var(--a-red) !important; text-shadow:0 0 18px rgba(255,92,122,0.35); }
.stat-value.neutral { color:var(--a-gold) !important; text-shadow:0 0 18px rgba(245,196,81,0.30); }
.stat-card::before { background:var(--a-teal) !important; }
.stat-card:has(.up)::before { background:var(--a-teal) !important; }
.stat-card:has(.down)::before { background:var(--a-red) !important; }
.stat-card:has(.neutral)::before { background:var(--a-gold) !important; }
[data-testid="stMetricValue"] { color:var(--a-ink) !important; }

/* hero */
.hero { background:linear-gradient(120deg,#12303A 0%, #14203A 55%, #0E1117 100%) !important;
  border:1px solid var(--a-line) !important; box-shadow:0 12px 40px rgba(0,224,184,0.10) !important; }
.hero h1 { color:#fff !important; } .hero .sub { color:var(--a-muted) !important; }
.hero::after { background:radial-gradient(circle, rgba(0,224,184,0.20), transparent 70%) !important; }

/* topbar */
.topbar { background:var(--a-card) !important; border:1px solid var(--a-line) !important; }
.topbar .tb-name, .topbar .tb-v { color:var(--a-ink) !important; }
.topbar .tb-logo { background:linear-gradient(135deg,var(--a-teal),#0AA88C) !important; color:#04201B !important; }
.topbar .tb-k, .topbar .tb-tag { color:var(--a-muted) !important; }
.topbar .tb-v.up { color:var(--a-teal) !important; } .topbar .tb-v.down { color:var(--a-red) !important; }

/* sidebar */
[data-testid="stSidebar"] { background:#12151F !important; border-right:1px solid var(--a-line); }
[data-testid="stSidebar"] * { color:var(--a-ink) !important; }
.brand .logo { background:linear-gradient(135deg,var(--a-teal),#0AA88C) !important; color:#04201B !important; }
.brand .tg, [data-testid="stSidebar"] .stCaption { color:var(--a-muted) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background:rgba(255,255,255,0.05) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
  background:rgba(0,224,184,0.14) !important; box-shadow:inset 3px 0 0 var(--a-teal) !important; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:rgba(0,224,184,0.10) !important; }

/* buttons */
.stButton>button { background:linear-gradient(135deg,var(--a-teal),#0AA88C) !important; color:#04201B !important;
  border:none !important; box-shadow:0 6px 18px rgba(0,224,184,0.30) !important; font-weight:700; }

/* inputs */
.stTextInput input, .stTextArea textarea, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div { background:#0F1420 !important; color:var(--a-ink) !important;
  border:1px solid var(--a-line) !important; }

/* tables */
[data-testid="stDataFrame"] { border:1px solid var(--a-line) !important; box-shadow:0 8px 24px rgba(0,0,0,0.35) !important; }
[data-testid="stDataFrame"] thead tr th { background:#0F1420 !important; color:var(--a-ink) !important; }

/* callouts */
[data-testid="stAlert"] { background:#141A28 !important; color:var(--a-ink) !important; }

/* badges */
.badge.up { background:rgba(0,224,184,0.15) !important; color:var(--a-teal) !important; }
.badge.down { background:rgba(255,92,122,0.15) !important; color:var(--a-red) !important; }
.badge.neutral { background:rgba(245,196,81,0.15) !important; color:var(--a-gold) !important; }

/* scrollbar */
::-webkit-scrollbar-thumb { background:rgba(0,224,184,0.30) !important; }
</style>
"""


# ============================ ZINE THEME (neo-brutalist) ====================
# additive override applied on top of the modern CSS when selected
ZINE = """
<style>
:root {
  --z-bg:#EDE9DD; --z-ink:#111111; --z-yellow:#F4D63B; --z-pink:#FF6FB5;
  --z-cyan:#66D9E8; --z-line:#111111;
}
.stApp { background:var(--z-bg) !important; color:var(--z-ink) !important; }
h1,h2,h3,h4 { color:var(--z-ink) !important; font-weight:800 !important; letter-spacing:-.01em; }

/* cards -> hard border + offset shadow */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:#FBF9F1 !important; border:3px solid var(--z-line) !important;
  border-radius:4px !important; box-shadow:6px 6px 0 var(--z-line) !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover { transform:translate(-1px,-1px); box-shadow:8px 8px 0 var(--z-line) !important; }
[data-testid="stVerticalBlockBorderWrapper"] h4 { border-left:none !important; padding-left:0 !important; }

/* metrics + stat cards */
[data-testid="stMetric"], .stat-card {
  background:#fff !important; border:3px solid var(--z-line) !important;
  border-radius:4px !important; box-shadow:5px 5px 0 var(--z-line) !important;
}
.stat-title { color:var(--z-ink) !important; opacity:.7; }
.stat-value.up { color:#0F9D58 !important; } .stat-value.down { color:#E8542B !important; }
.stat-value.neutral { color:var(--z-ink) !important; }

/* hero -> yellow sticker block */
.hero { background:var(--z-yellow) !important; color:var(--z-ink) !important;
  border:3px solid var(--z-line) !important; border-radius:4px !important;
  box-shadow:8px 8px 0 var(--z-line) !important; }
.hero h1 { color:var(--z-ink) !important; } .hero .sub { color:var(--z-ink) !important; opacity:.75; }
.hero::after { display:none; }

/* sidebar -> cream with black rules */
[data-testid="stSidebar"] { background:var(--z-bg) !important; border-right:3px solid var(--z-line); }
[data-testid="stSidebar"] * { color:var(--z-ink) !important; }
.brand .logo { background:var(--z-cyan) !important; border:3px solid var(--z-line); border-radius:4px; }
.brand .nm { color:var(--z-ink) !important; } .brand .tg { color:var(--z-ink) !important; opacity:.7; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:var(--z-cyan) !important; }

/* nav radio -> sticker items, active = yellow block */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
  color:var(--z-ink) !important; border:2px solid transparent; border-radius:4px;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background:#fff; border-color:var(--z-line); }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
  background:var(--z-yellow) !important; border:2px solid var(--z-line);
  box-shadow:3px 3px 0 var(--z-line);
}
[data-testid="stSidebar"] .stButton>button { background:var(--z-pink) !important; color:var(--z-ink) !important;
  border:3px solid var(--z-line) !important; border-radius:4px; box-shadow:3px 3px 0 var(--z-line); font-weight:700; }

/* badges + buttons */
.badge { border:2px solid var(--z-line) !important; border-radius:4px !important; }
.badge.up { background:var(--z-cyan) !important; color:var(--z-ink) !important; }
.badge.down { background:var(--z-pink) !important; color:var(--z-ink) !important; }
.badge.neutral { background:var(--z-yellow) !important; color:var(--z-ink) !important; }
.stButton>button { border:3px solid var(--z-line) !important; border-radius:4px !important;
  box-shadow:4px 4px 0 var(--z-line) !important; }

/* tables -> bordered, black header */
[data-testid="stDataFrame"] { border:3px solid var(--z-line) !important; border-radius:4px !important; box-shadow:5px 5px 0 var(--z-line); }
[data-testid="stDataFrame"] thead tr th { background:var(--z-ink) !important; color:#fff !important; }

.stCaption, [data-testid="stCaptionContainer"] { font-family:'Courier New',monospace; color:#555 !important; }
</style>
"""


RESPONSIVE = """
<style>
/* tablet + mobile: stack Streamlit columns, full-width cards */
@media (max-width: 900px) {
  .block-container { padding-left:.7rem !important; padding-right:.7rem !important; }
  [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; gap:10px !important; }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    min-width:100% !important; flex:1 1 100% !important; width:100% !important; }
  .stat-row { flex-direction:column; }
  .stat-card { min-width:100% !important; flex:1 1 100% !important; }
  .topbar { flex-direction:column; align-items:flex-start; gap:10px; }
  .topbar .tb-right { flex-wrap:wrap; gap:14px; justify-content:flex-start; }
  .topbar .tb-chip { text-align:left; }
  .hero { padding:16px 18px !important; }
  .hero h1 { font-size:1.25rem !important; }
}
/* phones */
@media (max-width: 600px) {
  .stat-value { font-size:1.6rem !important; }
  h2 { font-size:1.05rem !important; }
  [data-testid="stMetricValue"] { font-size:1.4rem !important; }
  .brand .nm { font-size:.95rem; }
}
/* tables always scroll horizontally instead of squishing */
[data-testid="stDataFrame"] > div { overflow-x:auto; }
</style>
"""


def brand(name: str = "NSE Alpha", tagline: str = "Investor Intelligence") -> str:
    return (f'<div class="brand"><div class="logo">📈</div>'
            f'<div><div class="nm">{name}</div><div class="tg">{tagline}</div></div></div>')


TOPBAR_CSS = f"""
<style>
.topbar {{ display:flex; align-items:center; justify-content:space-between;
  background:{CARD}; border:1px solid rgba(108,99,255,0.10); border-radius:16px;
  padding:12px 20px; margin-bottom:12px; box-shadow:0 6px 20px rgba(60,64,120,0.06); }}
.topbar .tb-left {{ display:flex; align-items:center; gap:12px; }}
.topbar .tb-logo {{ width:34px; height:34px; border-radius:10px; background:{INDIGO};
  color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.1rem; }}
.topbar .tb-name {{ font-weight:800; color:{INK}; font-size:1.05rem; line-height:1; }}
.topbar .tb-tag {{ font-size:.72rem; color:{MUTED}; }}
.topbar .tb-right {{ display:flex; align-items:center; gap:18px; }}
.topbar .tb-chip {{ text-align:right; }}
.topbar .tb-k {{ font-size:.68rem; color:{MUTED}; text-transform:uppercase; letter-spacing:.05em; }}
.topbar .tb-v {{ font-weight:700; color:{INK}; font-size:.95rem; }}
.topbar .tb-v.up {{ color:{GREEN}; }} .topbar .tb-v.down {{ color:{CORAL}; }}
</style>
"""


def topbar(chips: list[tuple]) -> str:
    """chips = list of (label, value, tone). Renders the right-side stat cluster."""
    r = ""
    for k, v, tone in chips:
        r += f'<div class="tb-chip"><div class="tb-k">{k}</div><div class="tb-v {tone}">{v}</div></div>'
    return (f'<div class="topbar"><div class="tb-left"><div class="tb-logo">📈</div>'
            f'<div><div class="tb-name">NSE Alpha</div>'
            f'<div class="tb-tag">Investor Intelligence</div></div></div>'
            f'<div class="tb-right">{r}</div></div>')


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
