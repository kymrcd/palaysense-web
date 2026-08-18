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
# Sidebar navigation model
# ------------------------------------------------------------------
# Each entry: (key, label, icon, group)
NAV_GROUPS = [
    {
        "label": "Data Management",
        "items": [("import_data", "Import Data", "upload_file")],
    },
    {
        "label": "Dashboard",
        "items": [
            ("overview", "Overview", "dashboard"),
            ("provincial", "Provincial Analytics", "location_city"),
            ("municipal", "Municipal Analytics", "location_on"),
            ("forecasting", "Forecasting", "query_stats"),
            ("historical", "Historical Comparison", "compare_arrows"),
        ],
    },
    {
        "label": "Settings",
        "items": [
            ("settings", "Settings", "settings"),
            ("logout", "Logout", "logout"),
        ],
    },
]

# Flatten: key -> label
_KEY_TO_LABEL = {k: label for g in NAV_GROUPS for (k, label, _) in g["items"]}


def _render_sidebar(active_page):
    with st.sidebar:
        # Logo
        logo = _get_base64("assets/logo.png")
        if logo:
            st.markdown(
                f'<div class="ps-side-logo"><img src="data:image/png;base64,{logo}" width="140" style="border-radius:6px;"/></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="ps-side-logo" style="font-size:1.6rem;">🌾</div>', unsafe_allow_html=True)
        st.markdown('<hr class="ps-side-divider">', unsafe_allow_html=True)

        for group in NAV_GROUPS:
            st.markdown(f'<p class="ps-side-section">{group["label"]}</p>', unsafe_allow_html=True)
            for key, label, icon in group["items"]:
                is_active = (active_page == key)
                # Use Streamlit's native Material icon in button labels
                # (streamlit 1.30+ supports icon=":material/name:")
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

    # Handle logout
    if active_page == "logout":
        st.session_state.logout_success = True
        st.query_params["page"] = "home"
        st.stop()

    # Load data
    dr = dl.load_dashboard()
    df = dl.get_provincial_df(dr)

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
        🌾 PalaySense · Bataan Rice Monitoring System · v4.0
    </div>
    """, unsafe_allow_html=True)
