"""
PalaySense LGU Dashboard — Main Entry
=====================================
Renders the modern sidebar (collapsible groups, Material icons, active
highlight), the top header with year filter, and routes to the correct
subpage. Reconnects to the existing backend data layer.
"""
import base64
import streamlit as st

from . import theme
from . import data_layer as dl
from . import overview
from . import provincial_analytics
from . import municipal_analytics
from . import forecasting
from . import historical_comparison
from app_pages.upload_dataset import upload_dataset


# ------------------------------------------------------------------
# Logo helper
# ------------------------------------------------------------------
def _get_base64(path):
  try:
    with open(path, "rb") as f:
      return base64.b64encode(f.read()).decode()
  except Exception:
    return ""


# ------------------------------------------------------------------
# Sidebar navigation model — Style C: Grouped Comprehensive, LGU English, Minimal
# ------------------------------------------------------------------
# Each entry: (key, label, icon, group) — English for LGU/OPA (Tagalog was for farmers)
NAV_GROUPS = [
  {
    "label": "OVERVIEW",
    "items": [("overview", "Overview", "dashboard")],
  },
  {
    "label": "ANALYTICS",
    "items": [
      ("provincial", "Provincial", "location_city"),
      ("municipal", "Municipal", "location_on"),
      ("historical", "Comparison", "compare_arrows"),
    ],
  },
  {
    "label": "FORECAST",
    "items": [
      ("forecasting", "Forecast", "query_stats"),
    ],
  },
  {
    "label": "SYSTEM",
    "items": [
      ("import_data", "Import Data", "upload_file"),
      ("settings", "Settings", "settings"),
      ("logout", "Logout", "logout"),
    ],
  },
]

# Flatten: key -> label
_KEY_TO_LABEL = {k: label for g in NAV_GROUPS for (k, label, _) in g["items"]}


def _render_sidebar(active_page):
  with st.sidebar:
    # Style C — Compact, no-scroll, minimal professional (fits exactly) — left-aligned nav
    st.markdown("""
    <style>
    /* Compact desktop — tight spacing to fit without scroll — left-aligned */
    section[data-testid="stSidebar"] > div:first-child { padding-top: 0.3rem !important; gap: 2px !important; }
    section[data-testid="stSidebar"] .stButton > button {
      margin: 1px 0 !important; min-height: 32px !important; padding: 4px 8px 4px 10px !important;
      justify-content: flex-start !important; text-align: left !important; align-items: center !important;
    }
    section[data-testid="stSidebar"] .stButton > button > div { justify-content: flex-start !important; text-align: left !important; }
    section[data-testid="stSidebar"] .stButton > button p { text-align: left !important; width: 100% !important; }
    .ps-side-section { font-size:0.60rem !important; letter-spacing:0.6px !important; color:#A8C3B0 !important; margin:0.45rem 0 0.12rem 0 !important; font-weight:600 !important; text-align: left !important; }
    .ps-side-logo { text-align:center; padding:0.3rem 0 0.15rem 0; }
    /* Mobile: bottom navigation, no hidden text, white icons visible */
    @media (max-width: 768px) {
      section[data-testid="stSidebar"] {
        position: fixed !important; bottom: 0 !important; top: auto !important; left: 0 !important; right: 0 !important;
        height: 68px !important; width: 100% !important; min-width: 100% !important;
        background: #123524 !important; border-top: 1px solid rgba(255,255,255,0.15) !important;
        z-index: 999 !important; overflow-x: auto !important; overflow-y: hidden !important;
        padding: 0 !important;
      }
      section[data-testid="stSidebar"] > div:first-child {
        padding: 6px 8px !important; flex-direction: row !important; gap: 6px !important;
        overflow-x: auto !important; overflow-y: hidden !important; flex-wrap: nowrap !important;
        align-items: center !important;
      }
      /* Hide logo/dividers/labels on mobile — keep only buttons */
      .ps-side-logo, hr.ps-side-divider, .ps-side-section { display: none !important; }
      section[data-testid="stSidebar"] .stButton { flex: 0 0 auto; }
      section[data-testid="stSidebar"] .stButton > button {
        min-width: 64px !important; flex-direction: column !important; gap: 2px !important;
        font-size: 0.62rem !important; padding: 6px 6px !important; white-space: nowrap !important;
        background: transparent !important; border: none !important;
        justify-content: center !important; text-align: center !important;
      }
      section[data-testid="stSidebar"] .stButton > button > div { justify-content: center !important; }
      section[data-testid="stSidebar"] .stButton > button p { font-size: 0.62rem !important; line-height: 1 !important; text-align: center !important; }
      section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: rgba(255,255,255,0.12) !important; border-radius: 10px !important;
      }
      /* Content padding to avoid bottom bar overlap */
      .block-container { padding-bottom: 80px !important; }
      div[data-testid="stAppViewContainer"] { padding-bottom: 72px; }
    }
    /* Desktop: compact dividers */
    hr.ps-side-divider { border: none; border-top: 1px solid rgba(255,255,255,0.12); margin: 0.30rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    # Logo — minimal, centered
    logo = _get_base64("assets/logo.png")
    if logo:
      st.markdown(
        f'<div class="ps-side-logo"><img src="data:image/png;base64,{logo}" width="132" style="border-radius:6px;"/></div>',
        unsafe_allow_html=True,
      )
    else:
      st.markdown('<div class="ps-side-logo"><i class="material-symbols-outlined" style="font-size:1.5rem; color:#C8E6C9; vertical-align:middle;">agriculture</i> <span style="font-weight:700; color:#FFFFFF; font-size:0.9rem; margin-left:6px;">PalaySense</span></div>', unsafe_allow_html=True)
    st.markdown('<hr class="ps-side-divider">', unsafe_allow_html=True)

    for group in NAV_GROUPS:
      st.markdown(f'<p class="ps-side-section">{group["label"]}</p>', unsafe_allow_html=True)
      for key, label, icon in group["items"]:
        is_active = (active_page == key)
        if st.button(
          label,
          icon=f":material/{icon}:" if icon else None,
          use_container_width=True,
          type="primary" if is_active else "secondary",
          key=f"nav_{key}",
        ):
          st.session_state["lgu_page"] = key
          st.rerun()
      st.markdown('<hr class="ps-side-divider">', unsafe_allow_html=True)


# ------------------------------------------------------------------
# Main entry
# ------------------------------------------------------------------
def lgu_dashboard():
  # Toast on login
  if st.session_state.pop("login_success", False):
    st.toast("Logged in successfully!")

  theme.load_global_css()

  # Init active page
  if "lgu_page" not in st.session_state:
    st.session_state["lgu_page"] = "overview"
  active_page = st.session_state["lgu_page"]

  # Handle logout — show PalaySense loading screen (assets/logo.png) before redirect
  # Blocking loader guarantees visibility (same pattern as login), then redirect to home
  # Home will then show its own "Loading PalaySense..." loader via app.py page_change detection
  if active_page == "logout":
    try:
      from components.loading_screen import show_logout_loading
      show_logout_loading(duration_sec=1.0)
    except Exception:
      import time as _t
      _t.sleep(0.85)
    st.session_state.logout_success = True
    st.query_params["page"] = "home"
    st.rerun()

  # Load data — PalaySense loader covers this fetch (replaces tiny spinner)
  import time as _lgu_time
  from components.loading_screen import get_global_loading_html, _get_logo_base64, LGU_PAGE_LOADING_MESSAGES
  _lgu_msg = LGU_PAGE_LOADING_MESSAGES.get(active_page, ("Loading LGU Dashboard...", "Syncing latest records — please wait"))
  _lgu_loader = st.empty()
  _lgu_loader.markdown(
      get_global_loading_html(message=_lgu_msg[0], submessage=_lgu_msg[1], logo_base64=_get_logo_base64(), duration_ms=3000),
      unsafe_allow_html=True,
  )
  _lgu_t0 = _lgu_time.time()
  dr = dl.load_dashboard()
  df = dl.get_provincial_df(dr)
  _lgu_elapsed = _lgu_time.time() - _lgu_t0
  if _lgu_elapsed < 0.65:
      _lgu_time.sleep(0.65 - _lgu_elapsed)
  _lgu_loader.empty()

  # Sidebar
  _render_sidebar(active_page)

  # Route — each page renders its OWN single title header.
  # The user profile header (Hello, User) appears ONLY on the Dashboard.
  # The global YEAR filter has been removed from this wrapper; pages that
  # need year filtering render a compact YEAR dropdown inside their content.
  if active_page == "import_data":
    upload_dataset()
  elif active_page == "overview":
    overview.render(df, dr)
  elif active_page == "provincial":
    provincial_analytics.render(df, dr)
  elif active_page == "municipal":
    municipal_analytics.render(df, dr)
  elif active_page == "forecasting":
    forecasting.render(df, dr)
  elif active_page == "historical":
    historical_comparison.render(df, dr)
  elif active_page == "settings":
    theme.page_title("Settings", "Application preferences.")
    with theme.section_card(title="Settings",
                desc="Application preferences.", icon_name="settings"):
      st.info("Dashboard settings coming soon.")

  # Footer
  st.markdown("""
  <div style="text-align:center; padding:1rem 0 0.5rem 0; font-size:0.75rem; color:#9CA3AF; border-top:1px solid #E6EAE6; margin-top:1rem;">
    <i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#9CA3AF;">agriculture</i> PalaySense · Bataan Rice Monitoring System · v4.0
  </div>
  """, unsafe_allow_html=True)
