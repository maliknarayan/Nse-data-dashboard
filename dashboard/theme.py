"""Design system for the dashboard — lavender canvas, white rounded cards,
indigo + coral palette, Inter type. Mirrors the reference SaaS layout.
"""

from __future__ import annotations

# palette — Fillow purple accent + semantic green/red, drives all charts
INDIGO = "#886CC0"
INDIGO_DK = "#6C4FA8"
CORAL = "#FC2E53"
GREEN = "#09BD3C"
RED = "#FC2E53"
BG = "#EEF1FB"
CARD = "#FFFFFF"
INK = "#2B2D42"
MUTED = "#8B8FA3"

# sequential/diverging use across native charts
UP = GREEN
DOWN = CORAL

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {{
    font-family: 'Poppins', -apple-system, Segoe UI, sans-serif !important;
}}
h1,h2,h3,h4,h5,h6, p, label, li, a,
.stMarkdown, .stMarkdown *, [data-testid="stMarkdownContainer"],
[data-testid="stMetricValue"], [data-testid="stMetricLabel"],
[data-testid="stDataFrame"], [data-testid="stDataFrame"] *,
.stat-value, .stat-title, .stat-sub, .hero, .hero *, .topbar, .topbar *,
.badge, .sect, .sect *, .brand, .brand * {{
    font-family: 'Poppins', -apple-system, Segoe UI, sans-serif !important;
}}
.stApp {{ background: {BG}; }}

/* hide ONLY Deploy/menu/decoration/footer. Keep the header + native sidebar
   toggle fully intact so open/close always works. */
[data-testid="stHelp"] {{ display: none !important; }}
/* hide Deploy + hamburger only — keep toolbar so the expand-sidebar button survives */
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], #MainMenu {{ display: none !important; }}
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
h1, h2, h3, h4, h5 {{ color: {INK} !important; font-weight: 700; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.15rem !important; }}
h3 {{ font-size: 1rem !important; color: {INK}; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

/* bordered containers -> cards. !important beats Streamlit's own native theme
   background (still set in .streamlit/config.toml) which otherwise wins the fight. */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {CARD} !important;
    border: 1px solid rgba(108,99,255,0.08) !important;
    border-radius: 18px;
    box-shadow: 0 8px 26px rgba(60,64,120,0.07);
    padding: 0.6rem 0.9rem;
}}

/* native metric -> soft card */
[data-testid="stMetric"] {{
    background: {CARD} !important;
    border-radius: 16px;
    padding: 14px 18px;
    box-shadow: 0 6px 20px rgba(60,64,120,0.06);
}}
[data-testid="stMetricValue"] {{ font-size: 1.7rem; font-weight: 700; color: {INK} !important; }}
[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-weight: 600; }}

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
/* Fillow metismenu — animated primary pill bar on active nav item */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {{
    position:relative; overflow:hidden; transition:all 0.5s;
}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:before {{
    content:""; position:absolute; left:0; top:0; height:100%; width:0;
    background:{INDIGO}; border-top-right-radius:3.563rem; border-bottom-right-radius:3.563rem;
    transition:all 0.5s;
}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked):before {{
    width:0.3rem;
}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div:has(> [data-testid="stMarkdownContainer"]) > *:first-child {{ display:none; }}

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

/* stat card -> .card-body layout (padding lives on the body now) */
.stat-card {{ padding:0 !important; overflow:hidden; }}
.stat-card .card-body {{ padding:1.5rem !important; display:flex; flex-direction:column; gap:3px; }}
.stat-card.mini .card-body {{ padding:1.1rem 1.25rem !important; }}

/* sector heatmap tiles */
.hm-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(110px,1fr));
  gap:8px; }}
.hm-tile {{ border-radius:10px; padding:10px 12px; }}
.hm-l {{ font-size:0.72rem; font-weight:600; opacity:0.85; text-transform:uppercase;
  letter-spacing:0.02em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.hm-v {{ font-size:1.05rem; font-weight:800; margin-top:2px; }}

/* Fillow-style HTML tables (roomy) — used by T.table(); theme-safe via inherit */
.dash-table {{ overflow-x:auto; border-radius:12px; }}
.table {{ width:100%; border-collapse:separate; border-spacing:0; font-size:0.9rem; color:inherit; }}
.table th, .table td {{ padding:0.85rem 0.9rem; vertical-align:middle;
  border-bottom:1px solid rgba(140,140,150,0.16); white-space:nowrap; }}
.table thead th {{ text-transform:capitalize; font-weight:600; letter-spacing:0.02em;
  color:inherit; border-bottom:1px solid rgba(140,140,150,0.28); }}
.table tbody tr {{ transition:background .15s ease; }}
.table tbody tr:hover td {{ background:rgba(136,108,192,0.08); }}
.table tbody tr:last-child td {{ border-bottom:none; }}
.table td:last-child, .table th:last-child {{ text-align:right; }}

/* Fillow progress bars */
[data-testid="stMarkdownContainer"]:has(> .progress),
[data-testid="stMarkdownContainer"]:has(> .pg-label) {{ margin:0.75rem 0 1rem !important; display:block; }}
.progress {{ height:8px; background:rgba(140,140,150,0.16); border-radius:999px;
  overflow:hidden; margin:6px 0 2px; }}
.progress-bar {{ height:100%; border-radius:999px; background:{INDIGO}; animation:pggrow 1s ease; }}
.progress-bar.success {{ background:{GREEN}; }}
.progress-bar.danger {{ background:{CORAL}; }}
.progress-bar.warning {{ background:#FFC107; }}
.progress-bar.primary {{ background:{INDIGO}; }}
.pg-label {{ font-size:.75rem; color:{MUTED}; margin-bottom:2px;
  display:flex; justify-content:space-between; font-weight:600; }}
@keyframes pggrow {{ from {{ width:0; }} }}

/* consistent vertical rhythm for every custom HTML block, on every page */
[data-testid="stMarkdownContainer"]:has(> .hero),
[data-testid="stMarkdownContainer"]:has(> .stat-row),
[data-testid="stMarkdownContainer"]:has(> .sect),
[data-testid="stMarkdownContainer"]:has(> .app-footer),
[data-testid="stMarkdownContainer"]:has(> .dash-table) {{ margin:0.75rem 0 1rem !important; }}
[data-testid="stMarkdownContainer"]:has(> .badge) {{ margin:0.5rem 0 !important; }}

/* app footer */
.app-footer {{ display:flex; align-items:center; justify-content:space-between; gap:16px;
  flex-wrap:wrap; margin-top:40px; padding:18px 22px; border-radius:14px;
  border:1px solid rgba(108,99,255,0.10); background:{CARD};
  font-size:0.8rem; color:{MUTED}; }}
.app-footer b {{ color:inherit; }}
.app-footer .af-mid {{ opacity:0.85; }}
.app-footer .af-right {{ font-weight:600; }}
</style>
"""


# ==================== AURORA THEME (premium dark fintech) ===================
# institutional trading-desk look: near-black navy canvas, glassmorphism cards,
# blue accent, fintech green/red. Additive override applied on top of the base.
AURORA = """
<style>
:root {
  --a-bg:#070B14; --a-bg2:#0F172A; --a-card:rgba(15,23,42,0.88); --a-card-solid:#101827;
  --a-line:rgba(255,255,255,0.08); --a-line2:rgba(255,255,255,0.14);
  --a-ink:#FFFFFF; --a-muted:#94A3B8;
  --a-pos:#00C853; --a-neg:#FF3B30; --a-accent:#3B82F6; --a-warn:#FFC107;
}

/* canvas — one faint top glow; avoids banding on wide monitors */
.stApp {
  background:
    radial-gradient(1100px 520px at 50% -12%, rgba(59,130,246,0.06), transparent 62%),
    var(--a-bg) !important;
  color:var(--a-ink) !important;
}
h1,h2,h3,h4,h5 { color:var(--a-ink) !important; letter-spacing:-0.01em; }
.stMarkdown, .stMarkdown p, label, .stCaption, [data-testid="stCaptionContainer"] { color:var(--a-muted) !important; }

/* subtle fade-in for content surfaces */
@keyframes a-fade { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }

/* data panels — flat and calm; inset top-highlight fakes elevation, no blur/motion */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:rgba(15,23,42,0.70) !important; border:1px solid rgba(255,255,255,0.06) !important;
  border-radius:18px !important; padding:24px !important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05), 0 1px 2px rgba(0,0,0,0.30) !important;
  transition:border-color .2s ease;
  animation:a-fade .35s ease both;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color:rgba(255,255,255,0.12) !important; }
[data-testid="stVerticalBlockBorderWrapper"] h4 {
  border-left:none !important; padding:0 0 12px 0 !important; margin:0 0 16px 0 !important;
  border-bottom:1px solid var(--a-line) !important;
  font-size:1.05rem !important; font-weight:600 !important; }

/* KPI cards — the only elevated surface; crisp numbers, no glow, no stripe */
[data-testid="stMetric"], .stat-card {
  background:var(--a-card) !important; border:1px solid var(--a-line) !important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05), 0 8px 24px rgba(0,0,0,0.35) !important;
  animation:a-fade .35s ease both; }
.stat-card { transition:border-color .2s ease; }
.stat-card:hover { border-color:var(--a-line2) !important; }
.stat-card::before { display:none !important; }
.stat-title { color:var(--a-muted) !important; }
.stat-value { color:var(--a-ink) !important; font-variant-numeric:tabular-nums; text-shadow:none !important; }
.stat-value.up { color:var(--a-pos) !important; }
.stat-value.down { color:var(--a-neg) !important; }
.stat-value.neutral { color:var(--a-accent) !important; }
.stat-sub { color:var(--a-muted) !important; }
[data-testid="stMetricValue"] { color:var(--a-ink) !important; font-variant-numeric:tabular-nums; }
[data-testid="stMetricLabel"] { color:var(--a-muted) !important; }

/* hero */
.hero { background:linear-gradient(120deg, #0E1B33 0%, #0B1424 55%, #070B14 100%) !important;
  border:1px solid var(--a-line) !important; border-radius:20px !important;
  box-shadow:0 18px 48px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.10) !important; }
.hero h1 { color:#fff !important; } .hero .sub { color:var(--a-muted) !important; }
.hero::after { background:radial-gradient(circle, rgba(59,130,246,0.22), transparent 70%) !important; }

/* sticky frosted topbar */
.topbar { position:sticky; top:8px; z-index:20;
  background:rgba(15,23,42,0.72) !important; border:1px solid var(--a-line) !important;
  border-radius:16px !important; -webkit-backdrop-filter:blur(18px); backdrop-filter:blur(18px);
  box-shadow:0 12px 34px rgba(0,0,0,0.45) !important; }
.topbar .tb-name, .topbar .tb-v { color:var(--a-ink) !important; }
.topbar .tb-logo { background:linear-gradient(135deg,var(--a-accent),#1D4ED8) !important; color:#fff !important;
  box-shadow:0 4px 14px rgba(59,130,246,0.45) !important; }
.topbar .tb-k, .topbar .tb-tag { color:var(--a-muted) !important; }
.topbar .tb-v { font-variant-numeric:tabular-nums; }
.topbar .tb-v.up { color:var(--a-pos) !important; } .topbar .tb-v.down { color:var(--a-neg) !important; }

/* sidebar rail */
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0B1220 0%, #070B14 100%) !important;
  border-right:1px solid var(--a-line); }
[data-testid="stSidebar"] * { color:var(--a-ink) !important; }
.brand .logo { background:linear-gradient(135deg,var(--a-accent),#1D4ED8) !important; color:#fff !important;
  box-shadow:0 4px 14px rgba(59,130,246,0.40); }
.brand .tg, [data-testid="stSidebar"] .stCaption { color:var(--a-muted) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
  border-radius:11px; transition:background .18s ease, box-shadow .18s ease; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background:rgba(255,255,255,0.06) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
  background:rgba(59,130,246,0.16) !important; box-shadow:inset 3px 0 0 var(--a-accent), 0 0 24px rgba(59,130,246,0.12) !important; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:rgba(59,130,246,0.10) !important; border:1px solid var(--a-line) !important; }

/* buttons — solid accent, quiet hover, no lift */
.stButton>button { background:var(--a-accent) !important; color:#fff !important;
  border:1px solid rgba(255,255,255,0.10) !important; border-radius:10px !important; font-weight:600;
  box-shadow:0 1px 2px rgba(0,0,0,0.30) !important; transition:filter .15s ease, background .15s ease; }
.stButton>button:hover { background:#2563EB !important; filter:brightness(1.05); }
.stButton>button:active { filter:brightness(0.95); }

/* inputs — glass with focus glow */
.stTextInput input, .stTextArea textarea, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div { background:rgba(9,14,26,0.9) !important; color:var(--a-ink) !important;
  border:1px solid var(--a-line) !important; border-radius:12px !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:#5B657A !important; }
.stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus {
  border-color:var(--a-accent) !important; box-shadow:0 0 0 3px rgba(59,130,246,0.22) !important; }

/* pill tabs */
.stTabs [data-baseweb="tab"] { background:var(--a-card-solid) !important; color:var(--a-muted) !important;
  border:1px solid var(--a-line) !important; box-shadow:none !important; }
.stTabs [aria-selected="true"] { background:var(--a-accent) !important; color:#fff !important; border-color:transparent !important; }

/* tables */
[data-testid="stDataFrame"] { border:1px solid var(--a-line) !important; border-radius:14px !important;
  box-shadow:0 14px 34px rgba(0,0,0,0.42) !important; }
[data-testid="stDataFrame"] thead tr th { background:#0B1220 !important; color:var(--a-ink) !important; }

/* callouts */
[data-testid="stAlert"] { background:rgba(15,23,42,0.85) !important; color:var(--a-ink) !important;
  border:1px solid var(--a-line) !important; border-radius:14px !important;
  -webkit-backdrop-filter:blur(10px); backdrop-filter:blur(10px); }

/* badges */
.badge.up { background:rgba(0,200,83,0.16) !important; color:var(--a-pos) !important; }
.badge.down { background:rgba(255,59,48,0.16) !important; color:var(--a-neg) !important; }
.badge.neutral { background:rgba(59,130,246,0.16) !important; color:var(--a-accent) !important; }

/* footer */
.app-footer { background:var(--a-card) !important; border:1px solid var(--a-line) !important; color:var(--a-muted) !important; }

/* section title */
.sect .t { color:var(--a-ink) !important; } .sect .s { color:var(--a-muted) !important; }

/* scrollbar */
::-webkit-scrollbar-thumb { background:rgba(59,130,246,0.35) !important; border-radius:10px; }
::-webkit-scrollbar-thumb:hover { background:rgba(59,130,246,0.55) !important; }

/* ---- premium refinement: 8px rhythm, type scale, hierarchy ---- */
.block-container { padding-top:24px !important; padding-bottom:48px !important; }
[data-testid="stHorizontalBlock"] { gap:24px !important; }
.stat-row { gap:16px !important; margin:8px 0 16px !important; }

h1 { font-weight:800 !important; }
h2 { font-size:1.2rem !important; font-weight:700 !important; margin-bottom:8px !important; }
[data-testid="stVerticalBlockBorderWrapper"] h4 {
  font-size:0.98rem !important; font-weight:700 !important; letter-spacing:0 !important;
  color:var(--a-ink) !important; margin:0 0 16px !important; }

/* big market values */
.stat-value { font-weight:800 !important; letter-spacing:-0.02em !important; line-height:1.1 !important; }
.stat-title { font-size:0.7rem !important; font-weight:600 !important; letter-spacing:0.08em !important; }
.stat-sub { margin-top:6px !important; line-height:1.3 !important; }
[data-testid="stMetricValue"] { font-weight:800 !important; letter-spacing:-0.02em !important; }

/* softened accent — thin gradient fade, not a solid slab */
.stat-card::before { width:3px !important;
  background:linear-gradient(180deg, var(--a-accent), transparent 85%) !important; }
.stat-card:has(.up)::before { background:linear-gradient(180deg, var(--a-pos), transparent 85%) !important; }
.stat-card:has(.down)::before { background:linear-gradient(180deg, var(--a-neg), transparent 85%) !important; }
.stat-card:has(.neutral)::before { background:linear-gradient(180deg, var(--a-accent), transparent 85%) !important; }

/* hairline dividers + calmer captions */
hr, [data-testid="stMarkdown"] hr { border:none !important; border-top:1px solid var(--a-line) !important; margin:16px 0 !important; }
.stCaption, [data-testid="stCaptionContainer"] { line-height:1.45 !important; }

/* soften hero glow */
.hero::after { opacity:0.75; }

/* sidebar toggle — visible on dark canvas */
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarCollapseButton"] svg { color:#FFFFFF !important; fill:#FFFFFF !important; }
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
  background:rgba(15,23,42,0.72) !important; border:1px solid var(--a-line) !important;
  border-radius:10px !important; -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px);
  box-shadow:0 8px 22px rgba(0,0,0,0.45) !important; }
[data-testid="stSidebarCollapsedControl"] button svg, [data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] button svg, [data-testid="collapsedControl"] svg {
  color:var(--a-accent) !important; fill:var(--a-accent) !important; }
</style>
"""


# ==================== STOCKSCANS THEME (light SaaS fintech) ==================
# modeled on stockscans.in — Untitled-UI tokens: gray-50 canvas, white cards,
# 1px #EAECF0 borders, blue accent, semantic green/red, 8px radius, Inter.
STOCKSCANS = """
<style>
:root {
  --s-bg:#F9FAFB; --s-card:#FFFFFF; --s-panel:#F2F4F7;
  --s-line:#EAECF0; --s-line2:#D0D5DD;
  --s-ink:#101828; --s-ink2:#344054; --s-muted:#475467; --s-muted2:#667085; --s-faint:#98A2B3;
  --s-accent:#286CD2; --s-accent-dk:#175CD3; --s-accent-bg:#EFF8FF;
  --s-pos:#039855; --s-pos-bg:#ECFDF3; --s-neg:#D92D20; --s-neg-bg:#FEF3F2;
  --s-warn:#DC6803; --s-warn-bg:#FFFAEB;
}

/* canvas + type */
.stApp { background:var(--s-bg) !important; color:var(--s-ink) !important; }
h1,h2,h3,h4,h5 { color:var(--s-ink) !important; letter-spacing:-0.01em; }
.stMarkdown, .stMarkdown p { color:var(--s-ink2) !important; }
label, .stCaption, [data-testid="stCaptionContainer"] { color:var(--s-muted2) !important; }
@keyframes s-fade { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }

/* cards — white, hairline border, whisper shadow, no blur */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--s-card) !important; border:1px solid var(--s-line) !important;
  border-radius:12px !important; padding:24px !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.05) !important;
  transition:border-color .2s ease, box-shadow .2s ease; animation:s-fade .35s ease both; }
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color:var(--s-line2) !important; box-shadow:0 4px 12px rgba(16,24,40,0.08) !important; }
[data-testid="stVerticalBlockBorderWrapper"] h4 {
  color:var(--s-ink) !important; border-left:none !important;
  padding:0 0 12px 0 !important; margin:0 0 16px 0 !important;
  border-bottom:1px solid var(--s-line) !important;
  font-size:1.05rem !important; font-weight:600 !important; }

/* KPI cards */
[data-testid="stMetric"], .stat-card {
  background:var(--s-card) !important; border:1px solid var(--s-line) !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.05) !important; animation:s-fade .35s ease both; }
.stat-card { transition:border-color .2s ease, box-shadow .2s ease; }
.stat-card:hover { border-color:var(--s-line2) !important; box-shadow:0 4px 12px rgba(16,24,40,0.08) !important; }
.stat-card::before { display:none !important; }
.stat-title { color:var(--s-muted2) !important; }
.stat-value { color:var(--s-ink) !important; text-shadow:none !important; font-variant-numeric:tabular-nums; }
.stat-value.up { color:var(--s-pos) !important; }
.stat-value.down { color:var(--s-neg) !important; }
.stat-value.neutral { color:var(--s-accent) !important; }
.stat-sub { color:var(--s-muted2) !important; }
[data-testid="stMetricValue"] { color:var(--s-ink) !important; font-variant-numeric:tabular-nums; }
[data-testid="stMetricLabel"] { color:var(--s-muted2) !important; }

/* hero — clean light header panel, no billboard gradient */
.hero { background:var(--s-card) !important; border:1px solid var(--s-line) !important;
  border-radius:12px !important; box-shadow:0 1px 2px rgba(16,24,40,0.05) !important; }
.hero h1 { color:var(--s-ink) !important; } .hero .sub { color:var(--s-muted) !important; }
.hero::after { background:radial-gradient(circle, rgba(40,108,210,0.10), transparent 70%) !important; opacity:1; }

/* sticky topbar — white, subtle border */
.topbar { position:sticky; top:8px; z-index:20;
  background:rgba(255,255,255,0.85) !important; border:1px solid var(--s-line) !important;
  border-radius:12px !important; -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px);
  box-shadow:0 1px 2px rgba(16,24,40,0.05) !important; }
.topbar .tb-name, .topbar .tb-v { color:var(--s-ink) !important; }
.topbar .tb-logo { background:var(--s-accent) !important; color:#fff !important; box-shadow:none !important; }
.topbar .tb-k, .topbar .tb-tag { color:var(--s-muted2) !important; }
.topbar .tb-v { font-variant-numeric:tabular-nums; }
.topbar .tb-v.up { color:var(--s-pos) !important; } .topbar .tb-v.down { color:var(--s-neg) !important; }

/* sidebar — white rail, dark text (override base indigo) */
[data-testid="stSidebar"] { background:var(--s-card) !important; border-right:1px solid var(--s-line) !important; }
[data-testid="stSidebar"] * { color:var(--s-ink2) !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { color:var(--s-ink) !important; }
.brand .logo { background:var(--s-accent) !important; color:#fff !important; box-shadow:none !important; }
.brand .nm { color:var(--s-ink) !important; } .brand .tg, [data-testid="stSidebar"] .stCaption { color:var(--s-muted2) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
  color:var(--s-ink2) !important; border-radius:8px; transition:background .15s ease; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background:var(--s-panel) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
  background:var(--s-accent-bg) !important; color:var(--s-accent-dk) !important;
  box-shadow:inset 3px 0 0 var(--s-accent) !important; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:var(--s-panel) !important; border:1px solid var(--s-line) !important; }
[data-testid="stSidebar"] .stButton>button { background:var(--s-accent) !important; color:#fff !important; border:none; }

/* buttons — solid accent, quiet hover */
.stButton>button { background:var(--s-accent) !important; color:#fff !important;
  border:1px solid var(--s-accent-dk) !important; border-radius:8px !important; font-weight:600;
  box-shadow:0 1px 2px rgba(16,24,40,0.06) !important; transition:background .15s ease; }
.stButton>button:hover { background:var(--s-accent-dk) !important; }

/* inputs — white with focus ring */
.stTextInput input, .stTextArea textarea, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div { background:var(--s-card) !important; color:var(--s-ink) !important;
  border:1px solid var(--s-line2) !important; border-radius:8px !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:var(--s-faint) !important; }
.stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus {
  border-color:var(--s-accent) !important; box-shadow:0 0 0 4px rgba(40,108,210,0.15) !important; }

/* pill tabs */
.stTabs [data-baseweb="tab"] { background:var(--s-card) !important; color:var(--s-muted) !important;
  border:1px solid var(--s-line) !important; box-shadow:none !important; }
.stTabs [aria-selected="true"] { background:var(--s-accent) !important; color:#fff !important; border-color:transparent !important; }

/* tables */
[data-testid="stDataFrame"] { border:1px solid var(--s-line) !important; border-radius:10px !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.05) !important; }
[data-testid="stDataFrame"] thead tr th { background:var(--s-bg) !important; color:var(--s-ink2) !important; }

/* callouts */
[data-testid="stAlert"] { background:var(--s-accent-bg) !important; color:var(--s-ink2) !important;
  border:1px solid var(--s-line) !important; border-radius:10px !important; }

/* badges */
.badge.up { background:var(--s-pos-bg) !important; color:var(--s-pos) !important; }
.badge.down { background:var(--s-neg-bg) !important; color:var(--s-neg) !important; }
.badge.neutral { background:var(--s-accent-bg) !important; color:var(--s-accent) !important; }

/* section title + dividers */
.sect .t { color:var(--s-ink) !important; } .sect .s { color:var(--s-muted2) !important; }
hr, [data-testid="stMarkdown"] hr { border-top:1px solid var(--s-line) !important; }

/* footer */
.app-footer { background:var(--s-card) !important; border:1px solid var(--s-line) !important; color:var(--s-muted2) !important; }

/* scrollbar */
::-webkit-scrollbar-thumb { background:var(--s-line2) !important; border-radius:10px; }
::-webkit-scrollbar-thumb:hover { background:var(--s-faint) !important; }

/* sidebar toggle — visible on light canvas */
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarCollapseButton"] svg { color:var(--s-ink2) !important; fill:var(--s-ink2) !important; }
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
  background:var(--s-card) !important; border:1px solid var(--s-line) !important;
  border-radius:10px !important; box-shadow:0 4px 12px rgba(16,24,40,0.12) !important; }
[data-testid="stSidebarCollapsedControl"] button svg, [data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] button svg, [data-testid="collapsedControl"] svg {
  color:var(--s-accent) !important; fill:var(--s-accent) !important; }
</style>
"""


# ==================== FILLOW THEME (Fillow Saas admin — dark) ================
# modeled on fillow.vercel.app/index-2.html — charcoal #161717 canvas,
# #202020 cards, muted purple accent #886CC0, Poppins, ~9px radius, pill buttons.
FILLOW = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
:root {
  --f-bg:#161717; --f-card:#202020; --f-panel:#262626;
  --f-line:#2B2B2B; --f-line2:#3A3A3A;
  --f-ink:#FFFFFF; --f-body:#B3B3B3; --f-muted:#828690; --f-faint:#6B6E77;
  --f-accent:#886CC0; --f-accent-dk:#6C4FA8; --f-accent-bg:rgba(136,108,192,0.12);
  --f-pos:#09BD3C; --f-pos-bg:rgba(9,189,60,0.12); --f-neg:#FC2E53; --f-neg-bg:rgba(252,46,83,0.12);
  --f-warn:#FF9F0A; --f-warn-bg:rgba(255,159,10,0.12);
}

/* font + canvas */
html, body, [class*="css"], .stApp { font-family:'Poppins', -apple-system, Segoe UI, sans-serif !important; }
.stApp { background:var(--f-bg) !important; color:var(--f-body) !important; }
h1,h2,h3,h4,h5 { color:var(--f-ink) !important; font-weight:600 !important; letter-spacing:0 !important; }
.stMarkdown, .stMarkdown p { color:var(--f-body) !important; }
label, .stCaption, [data-testid="stCaptionContainer"] { color:var(--f-muted) !important; }
@keyframes f-fade { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }

/* Fillow .card — no border, soft shadow, 1.875rem body, transition .5s */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--f-card) !important; border:0 solid transparent !important;
  border-radius:0.75rem !important; padding:1.875rem !important;
  box-shadow:0 0.3125rem 0.625rem rgba(0,0,0,0.22) !important;
  transition:all .5s ease-in-out; animation:f-fade .35s ease both; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow:0 0.5rem 1rem rgba(0,0,0,0.34) !important; }
/* Fillow .card-title + .card-header divider — 1.25rem, 600, capitalize */
[data-testid="stVerticalBlockBorderWrapper"] h4 {
  color:var(--f-ink) !important; border-left:none !important;
  font-size:1.25rem !important; font-weight:600 !important; text-transform:capitalize !important;
  padding:0 0 1.25rem 0 !important; margin:0 0 1.5rem 0 !important;
  border-bottom:1px solid var(--f-line) !important; }
@media (max-width:576px) { [data-testid="stVerticalBlockBorderWrapper"] { padding:1rem !important; } }

/* KPI cards */
/* KPI + metric cards share the .card style — no border, soft shadow, .5s */
[data-testid="stMetric"], .stat-card {
  background:var(--f-card) !important; border:0 solid transparent !important;
  border-radius:0.75rem !important;
  box-shadow:0 0.3125rem 0.625rem rgba(0,0,0,0.22) !important;
  transition:all .5s ease-in-out; animation:f-fade .35s ease both; }
.stat-card:hover, [data-testid="stMetric"]:hover { box-shadow:0 0.5rem 1rem rgba(0,0,0,0.34) !important; }
.stat-card::before { display:none !important; }
.stat-title { color:var(--f-muted) !important; }
.stat-value { color:var(--f-ink) !important; text-shadow:none !important; font-variant-numeric:tabular-nums; }
.stat-value.up { color:var(--f-pos) !important; }
.stat-value.down { color:var(--f-neg) !important; }
.stat-value.neutral { color:var(--f-accent) !important; }
.stat-sub { color:var(--f-muted) !important; }
[data-testid="stMetricValue"] { color:var(--f-ink) !important; font-variant-numeric:tabular-nums; }
[data-testid="stMetricLabel"] { color:var(--f-muted) !important; }

/* hero — charcoal panel with faint purple wash */
.hero { background:linear-gradient(120deg, #241E33 0%, #202020 60%, #161717 100%) !important;
  border:1px solid var(--f-line) !important; border-radius:12px !important;
  box-shadow:0 0 26px rgba(0,0,0,0.25) !important; }
.hero h1 { color:var(--f-ink) !important; } .hero .sub { color:var(--f-muted) !important; }
.hero::after { background:radial-gradient(circle, rgba(136,108,192,0.25), transparent 70%) !important; opacity:1; }

/* sticky topbar */
.topbar { position:sticky; top:8px; z-index:20;
  background:var(--f-card) !important; border:1px solid var(--f-line) !important;
  border-radius:12px !important; box-shadow:0 0 26px rgba(0,0,0,0.20) !important; }
.topbar .tb-name, .topbar .tb-v { color:var(--f-ink) !important; }
.topbar .tb-logo { background:var(--f-accent) !important; color:#fff !important; box-shadow:none !important; }
.topbar .tb-k, .topbar .tb-tag { color:var(--f-muted) !important; }
.topbar .tb-v { font-variant-numeric:tabular-nums; }
.topbar .tb-v.up { color:var(--f-pos) !important; } .topbar .tb-v.down { color:var(--f-neg) !important; }

/* sidebar — charcoal rail, muted nav, purple active */
[data-testid="stSidebar"] { background:var(--f-card) !important; border-right:1px solid var(--f-line) !important; }
[data-testid="stSidebar"] * { color:var(--f-muted) !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { color:var(--f-ink) !important; }
.brand .logo { background:var(--f-accent) !important; color:#fff !important; box-shadow:none !important; }
.brand .nm { color:var(--f-ink) !important; } .brand .tg, [data-testid="stSidebar"] .stCaption { color:var(--f-muted) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
  color:var(--f-muted) !important; border-radius:8px; font-weight:500; transition:background .15s ease, color .15s ease; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background:rgba(255,255,255,0.04) !important; color:var(--f-body) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
  background:var(--f-accent-bg) !important; color:var(--f-accent) !important;
  box-shadow:inset 3px 0 0 var(--f-accent) !important; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:var(--f-panel) !important; border:1px solid var(--f-line) !important; }
[data-testid="stSidebar"] .stButton>button { background:var(--f-accent) !important; color:#fff !important; border:none; border-radius:999px !important; }

/* buttons — pill, purple */
.stButton>button { background:var(--f-accent) !important; color:#fff !important;
  border:none !important; border-radius:999px !important; font-weight:600; padding:8px 22px !important;
  box-shadow:0 8px 20px rgba(136,108,192,0.30) !important; transition:background .15s ease, filter .15s ease; }
.stButton>button:hover { background:var(--f-accent-dk) !important; filter:brightness(1.05); }

/* inputs */
.stTextInput input, .stTextArea textarea, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div { background:#1A1A1A !important; color:var(--f-ink) !important;
  border:1px solid var(--f-line2) !important; border-radius:10px !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:var(--f-faint) !important; }
.stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus {
  border-color:var(--f-accent) !important; box-shadow:0 0 0 3px rgba(136,108,192,0.20) !important; }

/* pill tabs */
.stTabs [data-baseweb="tab"] { background:var(--f-panel) !important; color:var(--f-muted) !important;
  border:1px solid var(--f-line) !important; border-radius:999px !important; box-shadow:none !important; }
.stTabs [aria-selected="true"] { background:var(--f-accent) !important; color:#fff !important; border-color:transparent !important; }

/* tables */
[data-testid="stDataFrame"] { border:1px solid var(--f-line) !important; border-radius:10px !important;
  box-shadow:0 0 26px rgba(0,0,0,0.20) !important; }
[data-testid="stDataFrame"] thead tr th { background:#1A1A1A !important; color:var(--f-body) !important; }

/* callouts */
[data-testid="stAlert"] { background:var(--f-panel) !important; color:var(--f-body) !important;
  border:1px solid var(--f-line) !important; border-radius:10px !important; }

/* badges — Fillow rounded tags */
.badge { border-radius:999px !important; }
.badge.up { background:var(--f-pos-bg) !important; color:var(--f-pos) !important; }
.badge.down { background:var(--f-neg-bg) !important; color:var(--f-neg) !important; }
.badge.neutral { background:var(--f-accent-bg) !important; color:var(--f-accent) !important; }

/* footer */
.app-footer { background:var(--f-card) !important; border:1px solid var(--f-line) !important; color:var(--f-muted) !important; }

/* section title + dividers */
.sect .t { color:var(--f-ink) !important; } .sect .s { color:var(--f-muted) !important; }
hr, [data-testid="stMarkdown"] hr { border-top:1px solid var(--f-line) !important; }

/* scrollbar */
::-webkit-scrollbar-thumb { background:var(--f-line2) !important; border-radius:10px; }
::-webkit-scrollbar-thumb:hover { background:var(--f-accent) !important; }

/* sidebar toggle — visible on charcoal */
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarCollapseButton"] svg { color:var(--f-ink) !important; fill:var(--f-ink) !important; }
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
  background:var(--f-card) !important; border:1px solid var(--f-line) !important;
  border-radius:10px !important; box-shadow:0 8px 22px rgba(0,0,0,0.45) !important; }
[data-testid="stSidebarCollapsedControl"] button svg, [data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] button svg, [data-testid="collapsedControl"] svg {
  color:var(--f-accent) !important; fill:var(--f-accent) !important; }
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

/* T.table() HTML tables -> match the brutalist card style: grid borders, zebra, bold caps header */
.table { color:var(--z-ink) !important; border-collapse:collapse !important; }
.table th, .table td { border-bottom:2px solid var(--z-line) !important;
  border-right:2px solid var(--z-line) !important; color:var(--z-ink) !important; }
.table th:last-child, .table td:last-child { border-right:none !important; }
.table thead th { background:var(--z-yellow) !important; color:var(--z-ink) !important;
  border-bottom:3px solid var(--z-line) !important; text-transform:uppercase !important;
  font-weight:800 !important; letter-spacing:0.03em !important; }
.table tbody tr:nth-child(even) td { background:rgba(17,17,17,0.04) !important; }
.table tbody tr:hover td { background:var(--z-cyan) !important; }
.dash-table { border:3px solid var(--z-line) !important; border-radius:4px !important; box-shadow:5px 5px 0 var(--z-line) !important; }

/* footer -> cream card, black rule */
.app-footer { background:#FBF9F1 !important; border:3px solid var(--z-line) !important;
  border-radius:4px !important; box-shadow:5px 5px 0 var(--z-line) !important; color:var(--z-ink) !important; }

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
    return (f'<div class="{cls}"><div class="card-body">'
            f'<div class="stat-title">{title}</div>'
            f'<div class="stat-value {tone}">{a}{value}</div>'
            f'<div class="stat-sub">{sub}</div></div></div>')


def stat_row(cards: list[str]) -> str:
    return '<div class="stat-row">' + "".join(cards) + "</div>"


def hero(title: str, sub: str) -> str:
    return f'<div class="hero"><h1>{title}</h1><div class="sub">{sub}</div></div>'


OVERRIDES = """
<style>
/* keep Streamlit's own header (holds the expand button when collapsed) visible + on top */
header[data-testid="stHeader"] { z-index:1000001 !important; background:transparent !important; }

/* attach the theme popover to the header row — same surface, no floating gap */
/* topbar + theme picker genuinely share one container -> lay out as one row */
.st-key-topbar_row { margin:0 0 0.75rem !important; }
/* wrapper bg/border adapt to whichever theme is active via CSS var fallback chain —
   never hardcode a dark surface, or light themes get dark-text-on-dark-box */
.st-key-topbar_row [data-testid="stHorizontalBlock"] {
  background:var(--a-card, var(--s-card, var(--f-card, rgba(127,127,140,0.08))));
  border:1px solid var(--a-line, var(--s-line, var(--f-line, rgba(127,127,140,0.18))));
  border-radius:16px !important; padding:8px 14px !important; align-items:center !important;
  gap:10px !important; margin:0 !important; overflow:hidden !important;
  flex-wrap:nowrap !important; }
/* exempt the topbar row from the mobile column-stacking rule in RESPONSIVE */
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
  min-width:0 !important; width:auto !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
  flex:1 1 auto !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
  flex:0 0 150px !important; }
.st-key-topbar_row .topbar { position:static !important; overflow:visible;
  min-width:0; flex-wrap:wrap; }
.st-key-topbar_row .topbar .tb-right { flex-wrap:wrap; row-gap:4px; }
.st-key-topbar_row [data-testid="stColumn"] { padding:0 !important; margin:0 !important; }
.st-key-topbar_row [data-testid="stElementContainer"] { margin:0 !important; padding:0 !important; }
.st-key-topbar_row .topbar { background:transparent !important; border:none !important;
  box-shadow:none !important; margin:0 !important; padding:10px 6px !important; }
.st-key-topbar_row [data-testid="stWidgetLabel"] { display:none !important; }
.st-key-topbar_row [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  min-height:38px; border-radius:10px !important; font-weight:600;
  background:var(--a-panel, var(--s-panel, var(--f-panel, rgba(127,127,140,0.10)))) !important;
  border:1px solid var(--a-line, var(--s-line, var(--f-line, rgba(127,127,140,0.20)))) !important;
  color:inherit !important; }
.st-key-topbar_row .topbar { background:transparent !important; border:none !important;
  box-shadow:none !important; margin:0 !important; padding:6px 0 !important; }
.st-key-topbar_row [data-testid="stSelectbox"] label { display:none !important; }
.st-key-topbar_row [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  min-height:38px; border-radius:10px !important; font-weight:600;
  background:var(--a-panel, var(--s-panel, var(--f-panel, rgba(127,127,140,0.10)))) !important;
  border:1px solid var(--a-line, var(--s-line, var(--f-line, rgba(127,127,140,0.20)))) !important;
  color:inherit !important; }

/* expand-sidebar button (collapsed state) + in-sidebar collapse button — accent chip, always visible */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {
  background:#886CC0 !important; border-radius:10px !important;
  z-index:1000002 !important; box-shadow:0 6px 18px rgba(0,0,0,0.45) !important;
  position:relative; }
[data-testid="stExpandSidebarButton"] span, [data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] svg {
  color:#FFFFFF !important; fill:#FFFFFF !important; }

/* legacy collapsed-control fallback (older Streamlit) */
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
  background:#886CC0 !important; border:none !important; border-radius:10px !important;
  z-index:1000000 !important; box-shadow:0 6px 18px rgba(0,0,0,0.45) !important; }
[data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg {
  color:#FFFFFF !important; fill:#FFFFFF !important; }

/* sidebar nav — no radio dot, clean consistent pills */
[data-testid="stSidebar"] [role="radiogroup"] { gap:4px !important; }
[data-testid="stSidebar"] [role="radiogroup"] > label { margin:0 !important; }
/* hide ONLY the radio circle (the row child that isn't the text), keep the label */
[data-testid="stSidebar"] [role="radiogroup"] label div:has(> [data-testid="stMarkdownContainer"]) > *:first-child {
  display:none !important; }
[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] {
  display:block !important; }
[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
  display:block !important; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding:10px 14px !important; border-radius:10px !important; width:100% !important;
  min-height:0 !important; align-items:center !important; cursor:pointer; }
[data-testid="stSidebar"] [role="radiogroup"] label p {
  margin:0 !important; font-size:0.9rem !important; font-weight:600 !important;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
/* light sidebar spacing tidy (non-structural) */
[data-testid="stSidebar"] hr { margin:0.6rem 0 !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  text-transform:uppercase; letter-spacing:0.05em; font-size:0.68rem; opacity:0.72; }
</style>
"""


def table(df, hover: bool = True, height: int | None = None) -> str:
    """Roomy Fillow-style HTML table — replaces congested canvas st.dataframe.
    Accepts a plain DataFrame or a pandas Styler (gradients/formats survive)."""
    cls = "table table-hover" if hover else "table"
    if hasattr(df, "to_html") and hasattr(df, "data"):  # Styler
        try:
            html = df.hide(axis="index").to_html(table_attributes=f'class="{cls}"')
        except Exception:
            html = df.to_html()
    else:
        html = df.to_html(classes=cls, index=False, border=0, escape=False)
    wrap_style = f' style="max-height:{height}px;overflow-y:auto;"' if height else ""
    return f'<div class="dash-table"{wrap_style}>{html}</div>'


def progress(pct: float, tone: str = "primary", label: str = "") -> str:
    """Fillow-style progress bar. tone: primary|success|danger|warning."""
    pct = max(0.0, min(100.0, pct))
    lab = f'<div class="pg-label"><span>{label}</span></div>' if label else ""
    return (f'{lab}<div class="progress"><div class="progress-bar {tone}" '
            f'style="width:{pct:.1f}%"></div></div>')


MOUSE_GLOW_CSS = """
<style>
.mouse-glow { position:fixed; inset:0; z-index:0; pointer-events:none;
  background:radial-gradient(600px circle at var(--mx,50%) var(--my,50%),
    rgba(136,108,192,0.10), transparent 70%);
  transition:background 60ms linear; }
.stApp > div:first-child { position:relative; z-index:1; }
</style>
<div class="mouse-glow"></div>
"""

MOUSE_GLOW_JS = """
<script>
try {
  const doc = window.parent.document;
  doc.documentElement.style.setProperty('--mx', '50%');
  doc.documentElement.style.setProperty('--my', '50%');
  doc.addEventListener('mousemove', function(e) {
    doc.documentElement.style.setProperty('--mx', e.clientX + 'px');
    doc.documentElement.style.setProperty('--my', e.clientY + 'px');
  });
} catch (e) {}
</script>
"""


def heatmap(rows: list[tuple]) -> str:
    """rows = list of (label, pct_change). Renders a compact colored-tile heatmap."""
    tiles = []
    for label, pc in rows:
        pc = pc or 0.0
        inten = min(abs(pc) / 3.0, 1.0)
        color = GREEN if pc >= 0 else CORAL
        bg = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},{0.15+0.55*inten:.2f})"
        tiles.append(f'<div class="hm-tile" style="background:{bg}">'
                     f'<div class="hm-l">{label}</div><div class="hm-v">{pc:+.2f}%</div></div>')
    return f'<div class="hm-grid">{"".join(tiles)}</div>'


def footer(asof: str | None = None) -> str:
    right = f'Snapshot as of {asof}' if asof else 'No snapshot yet'
    return (f'<div class="app-footer"><div class="af-left">📈 <b>NSE Alpha</b> · '
            f'Investor Intelligence</div>'
            f'<div class="af-mid">Educational, from public NSE/BSE data — not investment advice.</div>'
            f'<div class="af-right">{right}</div></div>')
