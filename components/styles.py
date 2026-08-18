import streamlit as st

def load_css():
    st.markdown("""
    <style>
    /* =============================================================
       PALAYSENSE DESIGN SYSTEM - Modern shadcn-inspired UI
       ============================================================= */

    /* ---------- FONTS ---------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* ---------- CSS VARIABLES ---------- */
    :root {
        --sidebar-bg: #123524;
        --sidebar-active: #1E5C3A;
        --sidebar-hover: rgba(255,255,255,0.10);
        --sidebar-text: #FFFFFF;
        --sidebar-muted: #B0BEC5;
        --primary: #1E5C3A;
        --primary-light: #2E7D32;
        --primary-dark: #0F2B1A;
        --bg: #F7F8F5;
        --card-bg: #FFFFFF;
        --border: #E6EAE6;
        --text-primary: #1F2937;
        --text-secondary: #6B7280;
        --text-muted: #9CA3AF;
        --success: #16A34A;
        --warning: #F59E0B;
        --danger: #DC2626;
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 16px;
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --transition: all 0.2s ease;
    }

    /* ---------- GLOBAL ---------- */
    html, body, #root {
        font-family: var(--font-sans);
        background-color: var(--bg);
        color: var(--text-primary);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    .stApp {
        background-color: var(--bg);
    }

    .block-container {
        padding-top: 0.35rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 0.35rem !important;
    }

    .element-container { margin: 0 !important; }
    div[data-testid="column"] { gap: 0.5rem !important; }
    .row-widget.stHorizontal { gap: 0.5rem !important; }

    /* ---------- HIDE STREAMLIT DEFAULTS ---------- */
    #MainMenu { visibility: hidden; display: none; }
    header[data-testid="stHeader"] { visibility: hidden; display: none; height: 0; }
    footer { visibility: hidden; display: none; }
    .stAppDeployButton { display: none !important; }
    div[data-testid="stToolbar"] { display: none; }
    div[data-testid="stDecoration"] { display: none; }

    /* ---------- STREAMLIT COMPONENTS ---------- */
    .stButton > button {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border) !important;
        background: var(--card-bg) !important;
        color: var(--text-primary) !important;
        padding: 0.25rem 0.75rem !important;
        font-size: 0.78rem !important;
        height: 30px !important;
        line-height: 1 !important;
        box-shadow: none !important;
        transition: var(--transition) !important;
    }
    .stButton > button:hover {
        border-color: var(--primary) !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--primary-light) !important;
    }

    div[data-testid="stSelectbox"] > div {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border) !important;
        background: var(--card-bg) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.78rem !important;
        min-height: 30px !important;
        height: 30px !important;
        padding: 0 0.5rem !important;
        box-shadow: none !important;
    }
    div[data-testid="stSelectbox"] > div:hover {
        border-color: var(--primary) !important;
    }
    div[data-testid="stSelectbox"] label {
        font-size: 0.72rem !important;
        color: var(--text-secondary) !important;
    }

    div[data-testid="stMultiSelect"] > div {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border) !important;
        background: var(--card-bg) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.78rem !important;
        min-height: 30px !important;
    }

    div[data-testid="stExpander"] {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        background: var(--card-bg) !important;
        box-shadow: var(--shadow-sm) !important;
        overflow: hidden;
    }

    div[data-testid="stTabs"] { margin-bottom: 0.15rem !important; }
    div[data-testid="stTabs"] button {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        font-size: 0.78rem !important;
        border-radius: var(--radius-sm) !important;
        padding: 0.3rem 0.65rem !important;
        border: none !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        gap: 0.3rem !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
    }

    div[data-testid="stDataFrame"] {
        border: none !important;
        border-radius: var(--radius-md) !important;
        overflow: hidden;
        font-family: var(--font-sans) !important;
    }

    /* ---------- PLOTLY ---------- */
    .js-plotly-plot { border-radius: var(--radius-md) !important; }
    .main-svg { border-radius: var(--radius-md) !important; }

/* ---------- KPI GRID & HEADER ---------- */
    .ps-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem;
        margin-bottom: 0.65rem;
    }
    .ps-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.6rem;
        padding-top: 0;
    }

    /* ---------- KPI CARDS ---------- */
    .ps-kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1rem 1.1rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: var(--transition);
        position: relative;
        overflow: hidden;
    }
    .ps-kpi-card:hover {
        box-shadow: 0 6px 18px rgba(30, 92, 58, 0.08);
        transform: translateY(-2px);
        border-color: rgba(30, 92, 58, 0.25);
    }
    .ps-kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--primary-light));
    }
    .ps-kpi-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 0.35rem;
    }
    .ps-kpi-icon .material-symbols-outlined {
        font-size: 22px;
        line-height: 1;
    }
    .ps-kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .ps-kpi-value {
        font-size: 1.5rem;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: -0.5px;
        line-height: 1.1;
    }
    .ps-kpi-change {
        font-size: 0.72rem;
        font-weight: 500;
        color: var(--text-muted);
        margin-top: 0.1rem;
    }
    .ps-kpi-change.positive { color: var(--success); }
    .ps-kpi-change.negative { color: var(--danger); }

    /* ---------- PS CARD (Supply / Forecast) ---------- */
    .ps-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: var(--transition);
    }
    .ps-card:hover {
        box-shadow: 0 6px 18px rgba(30, 92, 58, 0.08);
        border-color: rgba(30, 92, 58, 0.25);
    }
    .ps-card .material-symbols-outlined {
        font-size: 28px;
        line-height: 1;
    }

    /* ---------- DIVIDER ---------- */
    hr.ps-divider {
        border: none;
        border-top: 1px solid var(--border);
        margin: 1.25rem 0;
    }

    /* ---------- CHART CARDS ---------- */
    .ps-chart-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.25rem 1.35rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: var(--transition);
    }
    .ps-chart-card:hover {
        box-shadow: 0 6px 18px rgba(30, 92, 58, 0.08);
    }
    .ps-chart-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.2rem;
    }
    .ps-chart-title .material-symbols-outlined {
        font-size: 20px;
        color: var(--primary);
        line-height: 1;
    }
    .ps-chart-desc {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-bottom: 0.9rem;
        font-weight: 400;
    }

    /* =============================================================
       COMPACT FIT SIDEBAR STYLING
       ============================================================= */

    /* Sidebar container base */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        min-width: 240px !important;
        max-width: 240px !important;
        width: 240px !important;
        border-right: none !important;
    }

    /* Hide header gap & reduce top padding */
    div[data-testid="stSidebarHeader"] {
        display: none !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding: 0.15rem 0.5rem 0.25rem 0.5rem !important;
    }

    /* Sidebar Section Titles: Forced non-bold and normal casing */
    .ps-sidebar-section,
    section[data-testid="stSidebar"] .ps-sidebar-section,
    section[data-testid="stSidebar"] p.ps-sidebar-section {
        font-size: 0.72rem !important;
        font-weight: 400 !important;
        font-style: normal !important;
        letter-spacing: 0.3px !important;
        text-transform: none !important;
        color: #C8D6C9 !important;
        padding: 0.15rem 0.2rem 0.05rem 0.2rem !important;
        margin: 0 !important;
        line-height: 1 !important;
        opacity: 1 !important;
    }

    /* Distinct Sidebar Horizontal Dividers */
    hr.ps-sidebar-divider,
    section[data-testid="stSidebar"] hr.ps-sidebar-divider {
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
        margin: 0.3rem 0 !important;
        padding: 0 !important;
        display: block !important;
        height: 0 !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* Sidebar Navigation Buttons */
    section[data-testid="stSidebar"] .stButton {
        margin: 0 !important;
        padding: 0 !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        border: none !important;
        background: transparent !important;
        font-family: var(--font-sans) !important;
        font-weight: 400 !important;
        font-size: 0.78rem !important;
        padding: 0.2rem 0.5rem !important;
        border-radius: 6px !important;
        color: rgba(255, 255, 255, 0.88) !important;
        text-align: left !important;
        margin: 0 !important;
        box-shadow: none !important;
        transition: var(--transition) !important;
        height: 26px !important;
        min-height: 26px !important;
        line-height: 1 !important;
    }
    section[data-testid="stSidebar"] .stButton > button p {
        color: rgba(255, 255, 255, 0.88) !important;
        font-weight: 400 !important;
        font-size: 0.78rem !important;
        margin: 0 !important;
        line-height: 1 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: var(--sidebar-hover) !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--sidebar-active) !important;
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }

    /* Sidebar Selectboxes Fix: Prevent text overlay */
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] {
        margin-top: 0.1rem !important;
        margin-bottom: 0.2rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 6px !important;
        min-height: 26px !important;
        height: 26px !important;
        padding: 0 0.4rem !important;
        font-size: 0.72rem !important;
        color: #1F2937 !important;
        position: relative !important;
        top: 0 !important;
        line-height: 24px !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] span {
        color: #1F2937 !important;
        font-size: 0.72rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Filter label class */
    section[data-testid="stSidebar"] .ps-filter-label {
        display: block !important;
        font-size: 0.68rem !important;
        font-weight: 400 !important;
        text-transform: none !important;
        color: #C8D6C9 !important;
        padding: 0.15rem 0 0.05rem 0 !important;
        margin: 0 !important;
        line-height: 1.2 !important;
        letter-spacing: 0.2px !important;
        vertical-align: middle !important;
    }
    section[data-testid="stSidebar"] .ps-filter-label .material-symbols-outlined {
        font-size: 14px !important;
        vertical-align: middle !important;
        margin-right: 3px !important;
    }

    /* Compact Layout Helpers */
    section[data-testid="stSidebar"] .element-container { margin: 0 !important; padding: 0 !important; }
    section[data-testid="stSidebar"] [data-testid="column"] { padding: 0 !important; margin: 0 !important; }
    section[data-testid="stSidebar"] .row-widget.stHorizontal { margin: 0 !important; padding: 0 !important; gap: 0 !important; }
    section[data-testid="stSidebar"] .stMarkdown { margin: 0 !important; padding: 0 !important; }


    /* ---------- RESPONSIVE ---------- */
    @media (max-width: 1200px) {
        .ps-kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 768px) {
        .ps-kpi-grid { grid-template-columns: 1fr; }
        .ps-header { flex-direction: column; gap: 0.5rem; }
    }
    </style>
    """, unsafe_allow_html=True)