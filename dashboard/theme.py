"""Design system for the dashboard.

One shared "skeleton" stylesheet (SKELETON) drives every themed component —
cards, hero, topbar, sidebar nav, buttons, inputs, tabs, tables, badges,
footer, progress bars, heatmap tiles — entirely through CSS custom properties
(``--t-*``). Each theme is then just a small ``:root`` token block (colors +
shape: radius/shadow/hover) concatenated with SKELETON. This replaces five
near-duplicate ~150-line theme blocks with one skeleton + five ~30-line token
sets, so a fix to (say) the footer or sidebar toggle lands on every theme at
once instead of needing a separate patch per theme.

Public API is unchanged from before this consolidation: same module-level
color constants, same string constants (CSS/POLISH/RESPONSIVE/OVERRIDES/
MOUSE_GLOW_CSS/MOUSE_GLOW_JS/TOPBAR_CSS/FILLOW/AURORA/STOCKSCANS/ZINE), same
helper functions with identical HTML/class output — app.py needs no changes.
"""

from __future__ import annotations

# palette — Fillow purple accent + semantic green/red, drives all charts
# (module-level; charts.py reads these directly regardless of active UI theme)
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


# ============================================================================
# SHARED SKELETON — every themed component, driven entirely by --t-* tokens.
# Each theme below supplies the token values; this stylesheet never changes
# per theme. Concatenated as: THEME_CONSTANT = <theme's :root tokens> + SKELETON
# ============================================================================
SKELETON = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {
  font-family:'Poppins', -apple-system, Segoe UI, sans-serif !important; }
h1,h2,h3,h4,h5,h6, p, label, li, a,
.stMarkdown, .stMarkdown *, [data-testid="stMarkdownContainer"],
[data-testid="stMetricValue"], [data-testid="stMetricLabel"],
[data-testid="stDataFrame"], [data-testid="stDataFrame"] *,
.stat-value, .stat-title, .stat-sub, .hero, .hero *, .topbar, .topbar *,
.badge, .sect, .sect *, .brand, .brand * {
  font-family:'Poppins', -apple-system, Segoe UI, sans-serif !important; }

/* canvas */
.stApp {
  background:
    radial-gradient(1100px 520px at 50% -12%, var(--t-glow, transparent), transparent 62%),
    var(--t-bg) !important;
  color:var(--t-body) !important;
}
h1,h2,h3,h4,h5 { color:var(--t-ink) !important; font-weight:700 !important; letter-spacing:-0.01em; }
.stMarkdown, .stMarkdown p { color:var(--t-body) !important; }
label, .stCaption, [data-testid="stCaptionContainer"] { color:var(--t-muted) !important; }
.block-container { padding-top:1.4rem !important; padding-bottom:3rem; max-width:1500px; }
* { -webkit-font-smoothing:antialiased; }

@keyframes t-fade { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }

/* hide Deploy + hamburger only — toolbar itself stays so the expand button survives */
[data-testid="stHelp"] { display:none !important; }
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], #MainMenu { display:none !important; }
[data-testid="stDecoration"] { display:none !important; }
footer { visibility:hidden !important; }
header[data-testid="stHeader"] { background:transparent !important; z-index:1000001 !important; }
.stMarkdown a[href^="#"] svg { display:none; }

/* sidebar collapse/expand toggle — accent chip, theme-matched, always visible */
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarCollapseButton"] svg { color:var(--t-ink) !important; fill:var(--t-ink) !important; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {
  background:var(--t-accent) !important; border-radius:10px !important;
  z-index:1000002 !important; box-shadow:0 6px 18px rgba(0,0,0,0.35) !important; position:relative; }
[data-testid="stExpandSidebarButton"] span, [data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] { color:#fff !important; fill:#fff !important; }
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
  background:var(--t-card) !important; border:1px solid var(--t-line) !important;
  border-radius:10px !important; z-index:1000000 !important; box-shadow:0 8px 22px rgba(0,0,0,0.30) !important; }
[data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg {
  color:var(--t-accent) !important; fill:var(--t-accent) !important; }

/* cards — shape (radius/shadow/hover) fully parameterized so Zine's brutalist
   look and the soft-shadow themes share one rule instead of duplicating it */
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--t-card) !important; border:var(--t-border-w) solid var(--t-line) !important;
  border-radius:var(--t-radius) !important; padding:var(--t-card-pad) !important;
  box-shadow:var(--t-shadow) !important; transition:all .35s ease; animation:t-fade .35s ease both; }
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color:var(--t-line2) !important; box-shadow:var(--t-shadow-hover) !important;
  transform:var(--t-hover-transform); }
[data-testid="stVerticalBlockBorderWrapper"] h4 {
  color:var(--t-ink) !important; border-left:none !important; text-transform:capitalize !important;
  font-size:1.15rem !important; font-weight:600 !important;
  padding:0 0 0.9rem 0 !important; margin:0 0 1.1rem 0 !important;
  border-bottom:var(--t-border-w) solid var(--t-line) !important; }
@media (max-width:576px) { [data-testid="stVerticalBlockBorderWrapper"] { padding:1rem !important; } }

/* KPI + metric cards share the card shape */
[data-testid="stMetric"], .stat-card {
  background:var(--t-card) !important; border:var(--t-border-w) solid var(--t-line) !important;
  border-radius:var(--t-radius) !important; box-shadow:var(--t-shadow) !important;
  transition:all .35s ease; animation:t-fade .35s ease both; padding:0 !important; overflow:hidden; }
.stat-card:hover, [data-testid="stMetric"]:hover {
  border-color:var(--t-line2) !important; box-shadow:var(--t-shadow-hover) !important;
  transform:var(--t-hover-transform); }
.stat-card .card-body { padding:1.5rem !important; display:flex; flex-direction:column; gap:3px; }
.stat-card.mini .card-body { padding:1.1rem 1.25rem !important; }
.stat-card::before { content:""; position:absolute; left:0; top:0; height:100%; width:3px;
  background:linear-gradient(180deg, var(--t-accent), transparent 85%); }
.stat-card:has(.up)::before { background:linear-gradient(180deg, var(--t-pos), transparent 85%); }
.stat-card:has(.down)::before { background:linear-gradient(180deg, var(--t-neg), transparent 85%); }
.stat-title { color:var(--t-muted) !important; font-size:0.7rem !important; font-weight:600 !important;
  text-transform:uppercase; letter-spacing:0.08em; }
.stat-value { color:var(--t-ink) !important; font-weight:800 !important; letter-spacing:-0.02em !important;
  line-height:1.1 !important; font-variant-numeric:tabular-nums; text-shadow:none !important; }
.stat-value.up { color:var(--t-pos) !important; }
.stat-value.down { color:var(--t-neg) !important; }
.stat-value.neutral { color:var(--t-accent) !important; }
.stat-sub { color:var(--t-muted) !important; margin-top:6px !important; line-height:1.3 !important; }
[data-testid="stMetricValue"] { color:var(--t-ink) !important; font-weight:800 !important;
  font-variant-numeric:tabular-nums; letter-spacing:-0.02em !important; }
[data-testid="stMetricLabel"] { color:var(--t-muted) !important; font-weight:600; }

/* hero */
.hero { position:relative; overflow:hidden; background:var(--t-hero-bg) !important;
  border:var(--t-border-w) solid var(--t-line) !important; border-radius:var(--t-radius-lg) !important;
  padding:22px 28px !important; margin-bottom:14px; box-shadow:var(--t-shadow) !important; color:#fff; }
.hero h1 { color:var(--t-hero-ink) !important; margin:0; font-size:1.6rem; }
.hero .sub { color:var(--t-hero-sub) !important; font-size:0.9rem; margin-top:4px; }
.hero::after { content:""; position:absolute; right:-40px; top:-40px; width:180px; height:180px;
  background:radial-gradient(circle, var(--t-accent-fade), transparent 70%); }

/* sticky topbar row */
.topbar { position:sticky; top:8px; z-index:20; display:flex; align-items:center;
  justify-content:space-between; background:var(--t-card) !important;
  border:var(--t-border-w) solid var(--t-line) !important; border-radius:16px !important;
  padding:12px 20px; margin-bottom:12px; box-shadow:var(--t-shadow) !important; }
.topbar .tb-left { display:flex; align-items:center; gap:12px; }
.topbar .tb-logo { width:34px; height:34px; border-radius:10px; background:var(--t-accent);
  color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.1rem; }
.topbar .tb-name { font-weight:800; color:var(--t-ink) !important; font-size:1.05rem; line-height:1; }
.topbar .tb-tag { font-size:.72rem; color:var(--t-muted) !important; }
.topbar .tb-right { display:flex; align-items:center; gap:18px; flex-wrap:wrap; row-gap:4px; }
.topbar .tb-chip { text-align:right; }
.topbar .tb-k { font-size:.68rem; color:var(--t-muted) !important; text-transform:uppercase; letter-spacing:.05em; }
.topbar .tb-v { font-weight:700; color:var(--t-ink) !important; font-size:.95rem; font-variant-numeric:tabular-nums; }
.topbar .tb-v.up { color:var(--t-pos) !important; } .topbar .tb-v.down { color:var(--t-neg) !important; }

/* topbar + theme picker share one container (see app.py st.container(key="topbar_row")) */
.st-key-topbar_row { margin:0 0 0.75rem !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] {
  background:var(--t-card); border:var(--t-border-w) solid var(--t-line);
  border-radius:16px !important; padding:8px 14px !important; align-items:center !important;
  gap:10px !important; margin:0 !important; overflow:hidden !important; flex-wrap:nowrap !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
  min-width:0 !important; width:auto !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child { flex:1 1 auto !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child { flex:0 0 150px !important; }
.st-key-topbar_row [data-testid="stColumn"], .st-key-topbar_row [data-testid="stElementContainer"] {
  padding:0 !important; margin:0 !important; }
.st-key-topbar_row .topbar { position:static !important; background:transparent !important; border:none !important;
  box-shadow:none !important; margin:0 !important; padding:10px 6px !important; overflow:visible; min-width:0; flex-wrap:wrap; }
.st-key-topbar_row [data-testid="stWidgetLabel"] { display:none !important; }
.st-key-topbar_row [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  min-height:38px; border-radius:10px !important; font-weight:600;
  background:var(--t-panel) !important; border:1px solid var(--t-line) !important; color:inherit !important; }

/* brand block in sidebar */
.brand { display:flex; align-items:center; gap:10px; padding:4px 2px 0; }
.brand .logo { width:34px; height:34px; border-radius:10px; background:var(--t-accent);
  color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.2rem; }
.brand .nm { font-weight:800; font-size:1.05rem; color:var(--t-sidebar-ink) !important; line-height:1; }
.brand .tg { font-size:0.72rem; color:var(--t-sidebar-muted) !important; }

/* sidebar rail */
[data-testid="stSidebar"] { background:var(--t-sidebar-bg) !important; border-right:1px solid var(--t-line); }
[data-testid="stSidebar"] * { color:var(--t-sidebar-ink) !important; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color:var(--t-sidebar-muted) !important; text-transform:uppercase; letter-spacing:0.05em; font-size:0.68rem; opacity:0.85; }
[data-testid="stSidebar"] hr { margin:0.6rem 0 !important; border-color:var(--t-line) !important; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:var(--t-panel) !important; box-shadow:none !important; }
[data-testid="stSidebar"] .stButton>button { background:var(--t-accent) !important; color:#fff !important; border:none; }

/* sidebar nav — animated primary pill bar on active item, no radio dot */
[data-testid="stSidebar"] .stRadio > label { display:none; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap:3px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
  position:relative; overflow:hidden; padding:9px 14px; border-radius:11px; width:100%;
  cursor:pointer; font-weight:600; color:var(--t-sidebar-ink) !important; transition:all 0.3s; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:before {
  content:""; position:absolute; left:0; top:0; height:100%; width:0; background:var(--t-accent);
  border-top-right-radius:3.563rem; border-bottom-right-radius:3.563rem; transition:all 0.5s; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background:var(--t-panel) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) { background:var(--t-accent-bg) !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked):before { width:0.3rem; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child { display:none; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div:has(> [data-testid="stMarkdownContainer"]) > *:first-child {
  display:none !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
  display:block !important; }

/* buttons */
.stButton>button { background:var(--t-accent) !important; color:#fff !important; border:none !important;
  border-radius:var(--t-radius-btn) !important; padding:8px 18px; font-weight:600;
  box-shadow:var(--t-shadow-btn) !important; transition:filter .15s ease, background .15s ease, transform .15s ease; }
.stButton>button:hover { background:var(--t-accent-dk) !important; filter:brightness(1.05); }

/* inputs */
.stTextInput input, .stTextArea textarea, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div { background:var(--t-input-bg) !important;
  color:var(--t-ink) !important; border:1px solid var(--t-line2) !important;
  border-radius:var(--t-radius-sm) !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:var(--t-muted) !important; }
.stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus {
  border-color:var(--t-accent) !important; box-shadow:0 0 0 3px var(--t-accent-fade) !important; }

/* pill tabs */
.stTabs [data-baseweb="tab-list"] { gap:6px; }
.stTabs [data-baseweb="tab"] { background:var(--t-card) !important; color:var(--t-muted) !important;
  border:1px solid var(--t-line) !important; border-radius:var(--t-radius-sm) !important;
  padding:8px 16px; font-weight:600; box-shadow:none !important; }
.stTabs [aria-selected="true"] { background:var(--t-accent) !important; color:#fff !important; border-color:transparent !important; }

/* tables (native st.dataframe container only — canvas rows are unreachable by CSS) */
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden;
  border:1px solid var(--t-line) !important; box-shadow:var(--t-shadow) !important; }
[data-testid="stDataFrame"] thead tr th { background:var(--t-panel) !important; color:var(--t-ink) !important; font-weight:700 !important; }

/* T.table() HTML tables — roomy Fillow-style, theme-adaptive via inherit + tokens */
.dash-table { overflow-x:auto; border-radius:var(--t-radius); border:var(--t-border-w) solid var(--t-line);
  box-shadow:var(--t-shadow); }
.table { width:100%; border-collapse:var(--t-table-collapse); border-spacing:0; font-size:0.9rem; color:inherit; }
.table th, .table td { padding:0.85rem 0.9rem; vertical-align:middle;
  border-bottom:var(--t-border-w) solid var(--t-line); border-right:var(--t-table-vline) var(--t-line);
  white-space:nowrap; }
.table th:last-child, .table td:last-child { border-right:none; text-align:right; }
.table thead th { text-transform:var(--t-table-head-case); font-weight:700; letter-spacing:0.02em;
  color:var(--t-ink); background:var(--t-accent-bg); border-bottom:calc(var(--t-border-w) + 1px) solid var(--t-line); }
.table tbody tr:nth-child(even) td { background:var(--t-zebra); }
.table tbody tr:hover td { background:var(--t-accent-bg); }
.table tbody tr:last-child td { border-bottom:none; }

/* callouts */
[data-testid="stAlert"] { border-radius:14px !important; border:1px solid var(--t-line) !important;
  background:var(--t-accent-bg) !important; color:var(--t-body) !important; box-shadow:none !important; }

/* badges */
.badge { display:inline-block; padding:5px 14px; border-radius:999px; font-weight:700; font-size:0.9rem;
  border:var(--t-badge-border); }
.badge.up { background:var(--t-pos-bg) !important; color:var(--t-pos) !important; }
.badge.down { background:var(--t-neg-bg) !important; color:var(--t-neg) !important; }
.badge.neutral { background:var(--t-accent-bg) !important; color:var(--t-accent) !important; }

/* section title */
.sect { margin:2px 0 10px; }
.sect .t { font-size:1.15rem; font-weight:700; color:var(--t-ink) !important; }
.sect .s { font-size:0.85rem; color:var(--t-muted) !important; margin-top:1px; }

/* progress bars */
.progress { height:8px; background:var(--t-line); border-radius:999px; overflow:hidden; margin:6px 0 2px; }
.progress-bar { height:100%; border-radius:999px; background:var(--t-accent); animation:pggrow 1s ease; }
.progress-bar.success { background:var(--t-pos); }
.progress-bar.danger { background:var(--t-neg); }
.progress-bar.warning { background:#FFC107; }
.progress-bar.primary { background:var(--t-accent); }
.pg-label { font-size:.75rem; color:var(--t-muted); margin-bottom:2px; display:flex;
  justify-content:space-between; font-weight:600; }
@keyframes pggrow { from { width:0; } }

/* sector heatmap tiles */
.hm-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(110px,1fr)); gap:8px; }
.hm-tile { border-radius:10px; padding:10px 12px; }
.hm-l { font-size:0.72rem; font-weight:600; opacity:0.85; text-transform:uppercase;
  letter-spacing:0.02em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.hm-v { font-size:1.05rem; font-weight:800; margin-top:2px; }

/* app footer */
[data-testid="stMarkdownContainer"]:has(> .hero),
[data-testid="stMarkdownContainer"]:has(> .stat-row),
[data-testid="stMarkdownContainer"]:has(> .sect),
[data-testid="stMarkdownContainer"]:has(> .app-footer),
[data-testid="stMarkdownContainer"]:has(> .dash-table),
[data-testid="stMarkdownContainer"]:has(> .progress),
[data-testid="stMarkdownContainer"]:has(> .pg-label) { margin:0.75rem 0 1rem !important; display:block; }
[data-testid="stMarkdownContainer"]:has(> .badge) { margin:0.5rem 0 !important; }
.stat-row { display:flex; gap:16px; flex-wrap:wrap; margin:8px 0 16px; }
.app-footer { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  margin-top:40px; padding:18px 22px; border-radius:14px; border:var(--t-border-w) solid var(--t-line);
  background:var(--t-card); font-size:0.8rem; color:var(--t-muted); box-shadow:var(--t-shadow); }
.app-footer b { color:inherit; }
.app-footer .af-mid { opacity:0.85; }
.app-footer .af-right { font-weight:600; }

/* scrollbar */
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-thumb { background:var(--t-line2); border-radius:10px; }
::-webkit-scrollbar-thumb:hover { background:var(--t-accent); }
[data-testid="stDataFrame"] > div { overflow-x:auto; }
</style>
"""


def _theme_css(tokens: str) -> str:
    return f"<style>:root {{ {tokens} }}</style>{SKELETON}"


# ============================== theme token sets ============================
# Each block below is ONLY color + shape tokens — the SKELETON above supplies
# every rule. Add a theme by adding one token block; never touch SKELETON.

_FILLOW_TOKENS = """
  --t-bg:#161717; --t-card:#202020; --t-panel:#262626; --t-input-bg:#1A1A1A;
  --t-line:#2B2B2B; --t-line2:#3A3A3A;
  --t-ink:#FFFFFF; --t-body:#B3B3B3; --t-muted:#828690;
  --t-sidebar-bg:#202020; --t-sidebar-ink:#828690; --t-sidebar-muted:#828690;
  --t-accent:#886CC0; --t-accent-dk:#6C4FA8; --t-accent-bg:rgba(136,108,192,0.12); --t-accent-fade:rgba(136,108,192,0.25);
  --t-pos:#09BD3C; --t-pos-bg:rgba(9,189,60,0.12); --t-neg:#FC2E53; --t-neg-bg:rgba(252,46,83,0.12);
  --t-hero-bg:linear-gradient(120deg,#241E33 0%,#202020 60%,#161717 100%); --t-hero-ink:#FFFFFF; --t-hero-sub:#828690;
  --t-glow:transparent; --t-zebra:rgba(255,255,255,0.03);
  --t-radius:0.75rem; --t-radius-lg:0.9rem; --t-radius-btn:999px; --t-radius-sm:10px;
  --t-border-w:0px; --t-badge-border:none; --t-table-vline:0px solid; --t-table-collapse:collapse; --t-table-head-case:capitalize;
  --t-shadow:0 0.3125rem 0.625rem rgba(0,0,0,0.22); --t-shadow-hover:0 0.5rem 1rem rgba(0,0,0,0.34);
  --t-shadow-btn:0 8px 20px rgba(136,108,192,0.30); --t-hover-transform:none; --t-card-pad:1.875rem;
"""

_AURORA_TOKENS = """
  --t-bg:#070B14; --t-card:rgba(15,23,42,0.70); --t-panel:#0F1420; --t-input-bg:rgba(9,14,26,0.9);
  --t-line:rgba(255,255,255,0.06); --t-line2:rgba(255,255,255,0.14);
  --t-ink:#FFFFFF; --t-body:#94A3B8; --t-muted:#94A3B8;
  --t-sidebar-bg:#0B1220; --t-sidebar-ink:#FFFFFF; --t-sidebar-muted:#94A3B8;
  --t-accent:#3B82F6; --t-accent-dk:#2563EB; --t-accent-bg:rgba(59,130,246,0.16); --t-accent-fade:rgba(59,130,246,0.22);
  --t-pos:#00C853; --t-pos-bg:rgba(0,200,83,0.16); --t-neg:#FF3B30; --t-neg-bg:rgba(255,59,48,0.16);
  --t-hero-bg:linear-gradient(120deg,#0E1B33 0%,#0B1424 55%,#070B14 100%); --t-hero-ink:#FFFFFF; --t-hero-sub:#94A3B8;
  --t-glow:rgba(59,130,246,0.06); --t-zebra:rgba(255,255,255,0.03);
  --t-radius:18px; --t-radius-lg:20px; --t-radius-btn:12px; --t-radius-sm:12px;
  --t-border-w:1px; --t-badge-border:none; --t-table-vline:0px solid; --t-table-collapse:collapse; --t-table-head-case:none;
  --t-shadow:inset 0 1px 0 rgba(255,255,255,0.05), 0 8px 24px rgba(0,0,0,0.35);
  --t-shadow-hover:inset 0 1px 0 rgba(255,255,255,0.05), 0 8px 24px rgba(0,0,0,0.35);
  --t-shadow-btn:0 1px 2px rgba(0,0,0,0.30); --t-hover-transform:none; --t-card-pad:24px;
"""

_STOCKSCANS_TOKENS = """
  --t-bg:#F9FAFB; --t-card:#FFFFFF; --t-panel:#F2F4F7; --t-input-bg:#FFFFFF;
  --t-line:#EAECF0; --t-line2:#D0D5DD;
  --t-ink:#101828; --t-body:#344054; --t-muted:#667085;
  --t-sidebar-bg:#FFFFFF; --t-sidebar-ink:#344054; --t-sidebar-muted:#667085;
  --t-accent:#286CD2; --t-accent-dk:#175CD3; --t-accent-bg:#EFF8FF; --t-accent-fade:rgba(40,108,210,0.15);
  --t-pos:#039855; --t-pos-bg:#ECFDF3; --t-neg:#D92D20; --t-neg-bg:#FEF3F2;
  --t-hero-bg:#FFFFFF; --t-hero-ink:#101828; --t-hero-sub:#475467;
  --t-glow:rgba(40,108,210,0.06); --t-zebra:rgba(16,24,40,0.02);
  --t-radius:12px; --t-radius-lg:12px; --t-radius-btn:8px; --t-radius-sm:8px;
  --t-border-w:1px; --t-badge-border:none; --t-table-vline:0px solid; --t-table-collapse:collapse; --t-table-head-case:none;
  --t-shadow:0 1px 2px rgba(16,24,40,0.05); --t-shadow-hover:0 4px 12px rgba(16,24,40,0.08);
  --t-shadow-btn:0 1px 2px rgba(16,24,40,0.06); --t-hover-transform:none; --t-card-pad:24px;
"""

_ZINE_TOKENS = """
  --t-bg:#EDE9DD; --t-card:#FBF9F1; --t-panel:#FFFFFF; --t-input-bg:#FFFFFF;
  --t-line:#111111; --t-line2:#111111;
  --t-ink:#111111; --t-body:#111111; --t-muted:#555555;
  --t-sidebar-bg:#EDE9DD; --t-sidebar-ink:#111111; --t-sidebar-muted:#111111;
  --t-accent:#66D9E8; --t-accent-dk:#4CC4D4; --t-accent-bg:#F4D63B; --t-accent-fade:rgba(17,17,17,0.15);
  --t-pos:#0F9D58; --t-pos-bg:#66D9E8; --t-neg:#E8542B; --t-neg-bg:#FF6FB5;
  --t-hero-bg:#F4D63B; --t-hero-ink:#111111; --t-hero-sub:#111111;
  --t-glow:transparent; --t-zebra:rgba(17,17,17,0.04);
  --t-radius:4px; --t-radius-lg:4px; --t-radius-btn:4px; --t-radius-sm:4px;
  --t-border-w:3px; --t-badge-border:2px solid #111111; --t-table-vline:2px solid; --t-table-collapse:collapse; --t-table-head-case:uppercase;
  --t-shadow:6px 6px 0 #111111; --t-shadow-hover:8px 8px 0 #111111;
  --t-shadow-btn:4px 4px 0 #111111; --t-hover-transform:translate(-1px,-1px); --t-card-pad:1.2rem;
"""

_MODERN_TOKENS = """
  --t-bg:#EEF1FB; --t-card:#FFFFFF; --t-panel:#F3F2FF; --t-input-bg:#FFFFFF;
  --t-line:rgba(108,99,255,0.10); --t-line2:rgba(108,99,255,0.22);
  --t-ink:#2B2D42; --t-body:#2B2D42; --t-muted:#8B8FA3;
  --t-sidebar-bg:linear-gradient(180deg,#886CC0 0%,#6C4FA8 100%); --t-sidebar-ink:#FFFFFF; --t-sidebar-muted:rgba(255,255,255,0.75);
  --t-accent:#886CC0; --t-accent-dk:#6C4FA8; --t-accent-bg:rgba(136,108,192,0.12); --t-accent-fade:rgba(136,108,192,0.18);
  --t-pos:#09BD3C; --t-pos-bg:rgba(9,189,60,0.15); --t-neg:#FC2E53; --t-neg-bg:rgba(252,46,83,0.15);
  --t-hero-bg:linear-gradient(120deg,#886CC0 0%,#6C4FA8 60%,#372FA6 100%); --t-hero-ink:#FFFFFF; --t-hero-sub:rgba(255,255,255,0.85);
  --t-glow:rgba(136,108,192,0.08); --t-zebra:rgba(43,45,66,0.03);
  --t-radius:18px; --t-radius-lg:20px; --t-radius-btn:12px; --t-radius-sm:10px;
  --t-border-w:1px; --t-badge-border:none; --t-table-vline:0px solid; --t-table-collapse:collapse; --t-table-head-case:none;
  --t-shadow:0 8px 26px rgba(60,64,120,0.07); --t-shadow-hover:0 14px 36px rgba(60,64,120,0.13);
  --t-shadow-btn:0 6px 16px rgba(136,108,192,0.28); --t-hover-transform:none; --t-card-pad:24px;
"""

# ============================ public theme constants =========================
# app.py does st.markdown(T.FILLOW / T.AURORA / T.STOCKSCANS / T.ZINE, ...) —
# same names, same call sites as before this consolidation. "Modern" (no extra
# block applied by app.py) now also gets its tokens injected via CSS below,
# so the base look no longer depends on leftover Streamlit config.toml colors.
FILLOW = _theme_css(_FILLOW_TOKENS)
AURORA = _theme_css(_AURORA_TOKENS)
STOCKSCANS = _theme_css(_STOCKSCANS_TOKENS)
ZINE = _theme_css(_ZINE_TOKENS)

# CSS = always-applied base layer (before any theme picker choice is read),
# so first paint uses Modern's tokens instead of Streamlit's native theme.
CSS = _theme_css(_MODERN_TOKENS)

# POLISH: kept as a public name for API stability; the refinement it used to
# add (8px rhythm, type scale, card-header divider) now lives in SKELETON.
POLISH = ""


RESPONSIVE = """
<style>
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
@media (max-width: 600px) {
  .stat-value { font-size:1.6rem !important; }
  h2 { font-size:1.05rem !important; }
  [data-testid="stMetricValue"] { font-size:1.4rem !important; }
  .brand .nm { font-size:.95rem; }
}
/* exempt the topbar row from the mobile column-stacking rule above */
.st-key-topbar_row [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
  min-width:0 !important; width:auto !important; }
[data-testid="stDataFrame"] > div { overflow-x:auto; }
</style>
"""

# OVERRIDES kept for API stability; its job (sidebar toggle, topbar-row layout)
# now lives directly in SKELETON with theme-adaptive tokens instead of one
# hardcoded-dark block bolted on afterward. Left empty to avoid double-styling.
OVERRIDES = ""


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


def brand(name: str = "NSE Alpha", tagline: str = "Investor Intelligence") -> str:
    return (f'<div class="brand"><div class="logo">📈</div>'
            f'<div><div class="nm">{name}</div><div class="tg">{tagline}</div></div></div>')


# TOPBAR_CSS kept for API stability (app.py calls st.markdown(T.TOPBAR_CSS)).
# Actual topbar styling now lives in SKELETON via --t-* tokens.
TOPBAR_CSS = ""


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


def table(df, hover: bool = True, height: int | None = None) -> str:
    """Roomy HTML table — replaces congested canvas st.dataframe.
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
    """Progress bar. tone: primary|success|danger|warning."""
    pct = max(0.0, min(100.0, pct))
    lab = f'<div class="pg-label"><span>{label}</span></div>' if label else ""
    return (f'{lab}<div class="progress"><div class="progress-bar {tone}" '
            f'style="width:{pct:.1f}%"></div></div>')


def footer(asof: str | None = None) -> str:
    right = f'Snapshot as of {asof}' if asof else 'No snapshot yet'
    return (f'<div class="app-footer"><div class="af-left">📈 <b>NSE Alpha</b> · '
            f'Investor Intelligence</div>'
            f'<div class="af-mid">Educational, from public NSE/BSE data — not investment advice.</div>'
            f'<div class="af-right">{right}</div></div>')
