"""
PalaySense LGU Dashboard — Design System & Reusable Components
=============================================================
Modern, government-grade agricultural dashboard theme.
Centralizes all colors, CSS, and small reusable UI renderers.
"""
import contextlib
import streamlit as st

# ------------------------------------------------------------------
# DESIGN TOKENS
# ------------------------------------------------------------------
FONT = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# Forest green palette
DARK_GREEN = "#123524"
PRIMARY = "#1E5C3A"
PRIMARY_LIGHT = "#2E7D32"
ACCENT = "#4CAF50"
BG = "#F4F6F4"
CARD_BG = "#FFFFFF"
BORDER = "#E6EAE6"
TEXT_PRIMARY = "#1F2937"
TEXT_SECONDARY = "#6B7280"
TEXT_MUTED = "#9CA3AF"

# Status colors
SUCCESS = "#16A34A"
WARNING = "#F59E0B"
DANGER = "#DC2626"
INFO = "#2563EB"
PURPLE = "#7C3AED"

# Chart colors
FANCY_COLOR = "#1B5E20"
REGULAR_COLOR = "#6D28D9"
HISTORICAL_COLOR = "#2E7D32"
FORECAST_COLOR = "#F57C00"

# --------------------------------------------------------------
# GLOBAL CSS
# --------------------------------------------------------------
_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

:root {
    --ps-bg: #F4F6F4;
    --ps-card: #FFFFFF;
    --ps-border: #E6EAE6;
    --ps-primary: #1E5C3A;
    --ps-primary-light: #2E7D32;
    --ps-dark: #123524;
    --ps-text: #1F2937;
    --ps-text-secondary: #6B7280;
    --ps-text-muted: #9CA3AF;
    --ps-success: #16A34A;
    --ps-warning: #F59E0B;
    --ps-danger: #DC2626;
    --ps-radius: 16px;
    --ps-font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

html, body, #root { font-family: var(--ps-font); background-color: var(--ps-bg); color: var(--ps-text); }
.stApp { background-color: var(--ps-bg); }
.block-container { padding-top: 1rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; padding-bottom: 2rem !important; max-width: 1400px !important; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; display: none; }
div[data-testid="stToolbar"], div[data-testid="stDecoration"], .stAppDeployButton { display: none; }

/* Material symbols base */
.material-symbols-outlined {
    font-family: 'Material Symbols Outlined' !important;
    font-weight: normal; font-style: normal; line-height: 1;
    letter-spacing: normal; text-transform: none; display: inline-block;
    white-space: nowrap; word-wrap: normal; direction: ltr;
    -webkit-font-smoothing: antialiased;
}

/* --- Top header banner (single white card) --- */
.ps-header-card {
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 18px;
    padding: 1rem 1.4rem 0.6rem 1.4rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 1.2rem;
}
.ps-header-card .ps-topbar-title { font-size: 2rem; font-weight: 800; color: var(--ps-dark); margin: 0; letter-spacing: -0.5px; }
.ps-header-card .ps-topbar-subtitle { font-size: 0.82rem; color: var(--ps-text-secondary); margin: 0.2rem 0 0 0; font-weight: 400; }
.ps-header-right { display: flex; align-items: center; justify-content: flex-end; gap: 0.8rem; }

/* Compact native selectbox inside the header card */
.ps-header-card div[data-testid="stSelectbox"] label {
    font-size: 0.68rem !important; font-weight: 600 !important;
    color: var(--ps-text-secondary) !important;
    text-transform: uppercase; letter-spacing: 0.4px;
    margin-bottom: 0.1rem !important;
}
.ps-header-card div[data-testid="stSelectbox"] > div {
    background: #F7F8F7 !important;
    border: 1px solid var(--ps-border) !important;
    border-radius: 10px !important;
    min-height: 38px !important; height: 38px !important;
    font-size: 0.85rem !important; color: var(--ps-dark) !important;
    font-weight: 600 !important;
}
.ps-header-card div[data-testid="stSelectbox"]:hover > div { border-color: var(--ps-primary) !important; }
.ps-header-card div[data-testid="stSelectbox"] span { color: var(--ps-dark) !important; font-weight: 600 !important; }

/* User chip */
.ps-user-chip { display: flex; align-items: center; gap: 0.6rem; }
.ps-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: linear-gradient(135deg, var(--ps-primary), var(--ps-primary-light));
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.95rem; box-shadow: 0 3px 8px rgba(30,92,58,0.25);
}
.ps-user-name { font-size: 0.85rem; font-weight: 700; color: var(--ps-dark); line-height: 1.1; }
.ps-user-role { font-size: 0.72rem; color: var(--ps-text-secondary); line-height: 1.1; }
.ps-updated-chip {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: rgba(22,163,74,0.08); color: var(--ps-success);
    border: 1px solid rgba(22,163,74,0.2); padding: 0.32rem 0.7rem;
    border-radius: 999px; font-size: 0.72rem; font-weight: 600; white-space: nowrap;
}

/* --- KPI cards --- */
.ps-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.ps-kpi {
    background: var(--ps-card); border: 1px solid var(--ps-border); border-radius: var(--ps-radius);
    padding: 1.1rem 1.2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    display: flex; flex-direction: column; gap: 0.3rem; position: relative; overflow: hidden;
    margin-bottom: 0.5rem; height: 100%;
}
.ps-kpi::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent); }
.ps-kpi-label { font-size: 0.72rem; font-weight: 600; color: var(--ps-text-secondary); text-transform: uppercase; letter-spacing: 0.4px; }
.ps-kpi-value { font-size: 1.6rem; font-weight: 800; color: #111827; letter-spacing: -0.5px; line-height: 1.1; }
.ps-kpi-sub { font-size: 0.75rem; color: var(--ps-text-muted); font-weight: 500; }

/* --- Compact KPI cards (5-up primary row) --- */
.ps-kpi--compact { padding: 0.75rem 0.85rem; gap: 0.15rem; }
.ps-kpi--compact .ps-kpi-label { font-size: 0.62rem; letter-spacing: 0.3px; }
.ps-kpi--compact .ps-kpi-value { font-size: 1.15rem; line-height: 1.15; }
.ps-kpi--compact .ps-kpi-sub { font-size: 0.66rem; }
.ps-kpi--compact .ps-kpi-icon { width: 30px; height: 30px; border-radius: 8px; margin-top: 0.15rem; }
.ps-kpi--compact .ps-kpi-icon i { font-size: 16px !important; }

/* --- Market Snapshot --- */
.ps-market-heading { font-size: 0.78rem; font-weight: 700; color: var(--ps-dark); text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.7rem; }
.ps-market-card {
    background: var(--ps-card); border: 1px solid var(--ps-border); border-radius: 14px;
    padding: 0.8rem 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    display: flex; flex-direction: column; gap: 0.35rem; height: 100%;
}
.ps-market-title { font-size: 0.72rem; font-weight: 600; color: var(--ps-text-secondary); text-transform: uppercase; letter-spacing: 0.4px; }
.ps-market-price { font-size: 1.5rem; font-weight: 800; color: var(--ps-dark); letter-spacing: -0.5px; line-height: 1; }
.ps-market-change { font-size: 0.78rem; font-weight: 700; display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.15rem 0.5rem; border-radius: 999px; }
.ps-market-change.ps-up { background: rgba(22,163,74,0.1); color: var(--ps-success); }
.ps-market-change.ps-down { background: rgba(220,38,38,0.08); color: var(--ps-danger); }
.ps-market-change.ps-flat { background: rgba(107,114,128,0.1); color: var(--ps-text-secondary); }
.ps-kpi-icon {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center; margin-top: 0.4rem;
}
.ps-pos { color: var(--ps-success); font-weight: 700; }
.ps-neg { color: var(--ps-danger); font-weight: 700; }

/* --- Section / component cards --- */
.ps-card {
    background: var(--ps-card); border: 1px solid var(--ps-border); border-radius: var(--ps-radius);
    padding: 1.2rem 1.3rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 1.2rem;
}
.ps-card-title { font-size: 1rem; font-weight: 700; color: var(--ps-dark); display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem; }
.ps-card-desc { font-size: 0.8rem; color: var(--ps-text-secondary); margin-bottom: 0.9rem; }
.ps-divider { border: none; border-top: 1px solid var(--ps-border); margin: 1.2rem 0; }

/* --- Sidebar overrides --- */
section[data-testid="stSidebar"] { background-color: var(--ps-dark) !important; border-right: none !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.4rem !important; }
.ps-side-logo { text-align: center; padding: 0.6rem 0 0.4rem 0; }
.ps-side-section { font-size: 0.7rem; font-weight: 400; color: #A8C3B0; text-transform: uppercase; letter-spacing: 0.4px; margin: 0.6rem 0 0.2rem 0; padding: 0 0.2rem; }
hr.ps-side-divider { border: none; border-top: 1px solid rgba(255,255,255,0.15); margin: 0.4rem 0; }
section[data-testid="stSidebar"] .stButton > button {
    width: 100% !important; border: none !important; background: transparent !important;
    color: rgba(255,255,255,0.85) !important; text-align: left !important;
    font-family: var(--ps-font) !important; font-size: 0.8rem !important; font-weight: 400 !important;
    padding: 0.35rem 0.6rem !important; border-radius: 8px !important; height: auto !important;
    box-shadow: none !important; line-height: 1.2 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.08) !important; color: #fff !important; }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: var(--ps-primary-light) !important; color: #fff !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] p { color: #fff !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] .stButton > button p { color: rgba(255,255,255,0.85) !important; font-size: 0.8rem !important; margin: 0 !important; }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] p { color: #fff !important; }

/* Sidebar selectboxes */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {
    background: #fff !important; border: 1px solid rgba(0,0,0,0.1) !important;
    border-radius: 8px !important; min-height: 30px !important; height: 30px !important;
    font-size: 0.75rem !important; color: #1F2937 !important; padding: 0 0.4rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] span { color: #1F2937 !important; font-size: 0.75rem !important; }
section[data-testid="stSidebar"] .ps-filter-label { display: block; font-size: 0.7rem; color: #A8C3B0; margin: 0.4rem 0 0.2rem 0; }

/* Filter chips row */
.ps-filter-row { display: flex; gap: 0.8rem; align-items: flex-end; margin-bottom: 1.2rem; flex-wrap: wrap; }

/* --- Plotly container --- */
.ps-plot { border-radius: var(--ps-radius); }

@media (max-width: 1200px) { .ps-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .ps-kpi-grid { grid-template-columns: 1fr; } .ps-topbar { flex-direction: column; align-items: flex-start; gap: 0.6rem; } }
</style>
"""


def load_global_css():
    """Inject the global dashboard CSS once."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------
# REUSABLE RENDERERS
# ------------------------------------------------------------------
def icon(name, size="20px", color=None):
    """Return a Material Symbols outlined icon element."""
    style = f"font-size:{size}; line-height:1;"
    if color:
        style += f" color:{color};"
    return f'<i class="material-symbols-outlined" style="{style}">{name}</i>'


def topbar(title, subtitle, as_of=""):
    """Render the top header as a single white card.

    The card shows the page title/subtitle on the left and the "updated"
    chip on the right. The user profile badge ("Hello, User") has been
    removed entirely as requested.
    """
    updated = f'<span class="ps-updated-chip">{icon("schedule", "15px")} As of {as_of} · Auto-updated</span>' if as_of else ""
    st.markdown(f"""<div class="ps-header-card"><div class="ps-topbar">""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap">
        <div>
            <div class="ps-topbar-title" style="font-size:2rem;font-weight:800;color:#123524;letter-spacing:-0.5px;line-height:1.2;">{title}</div>
            <div class="ps-topbar-subtitle">{subtitle}</div>
        </div>
        <div class="ps-header-right">
            {updated}
        </div>
    </div>
    """, unsafe_allow_html=True)


def close_header_card():
    """Close the header card opened by topbar()."""
    st.markdown("</div></div>", unsafe_allow_html=True)


def kpi_card(label, value, sub="", icon_name="", icon_bg="rgba(30,92,58,0.1)", icon_color="#1E5C3A", accent="#1E5C3A",
             compact=False):
    """Return a single KPI card as an HTML string (rendered by kpi_row).

    When `compact=True`, the card uses the smaller `.ps-kpi--compact` styling
    so five primary KPIs can fit on a single row with less scrolling.
    """
    extra_cls = " ps-kpi--compact" if compact else ""
    icon_html = f'<div class="ps-kpi-icon" style="background:{icon_bg};color:{icon_color};">{icon(icon_name, "22px")}</div>' if icon_name else ""
    return f"""
    <div class="ps-kpi{extra_cls}" style="--accent:{accent};">
        <span class="ps-kpi-label">{label}</span>
        <div class="ps-kpi-value">{value}</div>
        <span class="ps-kpi-sub">{sub}</span>
        {icon_html}
    </div>
    """


def market_price_card(title, price, pct_change, vs_label="vs previous period"):
    """Return a compact Market Snapshot price card.

    Shows the forecasted price (₱/kg) and a green/red percentage change
    versus the previous period.
    """
    if pct_change is None:
        change_html = '<span class="ps-market-change ps-flat">N/A</span>'
    elif pct_change > 0:
        change_html = f'<span class="ps-market-change ps-up">↑ {pct_change:.1f}%</span>'
    elif pct_change < 0:
        change_html = f'<span class="ps-market-change ps-down">↓ {abs(pct_change):.1f}%</span>'
    else:
        change_html = '<span class="ps-market-change ps-flat">→ 0.0%</span>'
    return f"""
    <div class="ps-market-card">
        <span class="ps-market-title">{title}</span>
        <div class="ps-market-price">₱{price:.2f}<span style="font-size:0.7rem;color:var(--ps-text-muted);font-weight:600;"> /kg</span></div>
        <div>{change_html} <span style="font-size:0.68rem;color:var(--ps-text-muted);">{vs_label}</span></div>
    </div>
    """


def kpi_row(cards):
    """Render KPI cards using native Streamlit columns.

    Each card is placed in its own column and rendered independently with
    unsafe_allow_html=True. This is the most robust approach — it does not
    depend on a single large HTML grid block, so cards always render even if
    the global CSS fails to load.
    """
    n = len(cards)
    cols = st.columns(n)
    for col, card in zip(cols, cards):
        with col:
            st.markdown(card, unsafe_allow_html=True)


@contextlib.contextmanager
def section_card(title=None, desc=None, icon_name=""):
    """Render a self-contained card section using Streamlit's native bordered container.

    The card header (icon + title + description) is rendered inside the container,
    and all content written within the ``with`` block is wrapped in a single
    bordered white card. This avoids the broken split open/close HTML tag pattern
    that produced empty floating white capsules.
    """
    with st.container(border=True):
        if title:
            icon_html = icon(icon_name, "18px", "#1E5C3A") if icon_name else ""
            st.markdown(f'<div class="ps-card-title">{icon_html} {title}</div>', unsafe_allow_html=True)
        if desc:
            st.markdown(f'<div class="ps-card-desc">{desc}</div>', unsafe_allow_html=True)
        yield


def page_title(title, caption=""):
    """Render a single, bold page title with an optional caption.

    Standardized for all child pages so there is exactly ONE title header,
    styled with `## **Title**` (bold) and a `st.caption` subtitle.
    """
    st.markdown(f"## **{title}**")
    if caption:
        st.caption(caption)


def year_filter(df, key="lgu_year_filter"):
    """Render a compact YEAR dropdown for pages that need it.

    Returns the selected year (int) or None if no years are available.
    """
    years = dl_get_years(df)
    if not years:
        return None
    selected = st.selectbox(
        "YEAR",
        options=years,
        index=len(years) - 1,
        key=key,
        help="Changing the year updates all KPIs and charts.",
    )
    return selected


def _lgu_imports():
    """Lazily import data_layer to avoid a circular import at module load."""
    from . import data_layer as _dl
    return _dl


def dl_get_years(df):
    """Return available years (uses data_layer if available, else inline)."""
    try:
        dl = _lgu_imports()
        return dl.get_available_years(df)
    except Exception:
        return sorted(df["year"].dropna().unique())


def divider():
    st.markdown('<hr class="ps-divider">', unsafe_allow_html=True)


def sidebar_icon(icon_name, color="#C8E6C9"):
    """Inline sidebar icon helper."""
    return f'<i class="material-symbols-outlined" style="font-size:18px; color:{color}; vertical-align:middle; margin-right:6px;">{icon_name}</i>'
