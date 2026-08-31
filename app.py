import streamlit as st
import base64

st.set_page_config(
    page_title="PalaySense",
    layout="wide",
    initial_sidebar_state="expanded"  # Show farmer/LGU sidebar navigation by default
)

# -----------------------------
# IMPORT PAGE MODULES
# -----------------------------
from components.top_navigation import top_navigation
from components.styles import load_css
from components.loading_screen import show_blocking_page_loading

load_css()

# Robust query_params parsing — handles both str and list returns across Streamlit versions
_raw_page = st.query_params.get("page", "home")
if isinstance(_raw_page, list):
    query_page = _raw_page[0] if _raw_page else "home"
else:
    query_page = str(_raw_page).strip() if _raw_page else "home"
if query_page not in ("home", "overview", "price_forecast", "yield_forecast", "login", "lgu_dashboard"):
    query_page = "home"

# --- Global PalaySense loading screen (assets/logo.png) — shown on EVERY page load & navigation ---
# Uses blocking placeholder + sleep (like login) so the overlay is GUARANTEED visible
# Covers: home, overview, price_forecast, yield_forecast, login, lgu_dashboard + LGU sub-pages + logout
# Detect page / sub-page transitions via session_state to avoid showing on every widget rerun
_lgu_page_now = st.session_state.get("lgu_page", "overview")
_prev_query = st.session_state.get("_prev_query_page", None)
_prev_lgu = st.session_state.get("_prev_lgu_page", None)
_is_initial = "_prev_query_page" not in st.session_state
_is_page_change = (_prev_query is not None and _prev_query != query_page)
# Exclude logout from subpage blocking — lgu_dashboard shows its own show_logout_loading
_is_lgu_subpage_change = (
    query_page == "lgu_dashboard"
    and _prev_query == "lgu_dashboard"
    and _prev_lgu is not None
    and _prev_lgu != _lgu_page_now
    and _lgu_page_now != "logout"
)
_should_show_blocking = _is_initial or _is_page_change or _is_lgu_subpage_change

if _should_show_blocking:
    if query_page == "lgu_dashboard":
        show_blocking_page_loading("lgu_dashboard", duration_sec=0.75, subpage_key=_lgu_page_now)
    else:
        # Short nav feedback — page-level loader will cover actual data fetch
        show_blocking_page_loading(query_page, duration_sec=0.65)

# Persist for next run
st.session_state["_prev_query_page"] = query_page
st.session_state["_prev_lgu_page"] = _lgu_page_now

# Show top navigation ONLY for public/farmer pages
if query_page != "lgu_dashboard":
    top_navigation()

# -----------------------------
# IMAGE HELPERS
# -----------------------------
def get_base64(image_path):
    """Convert an image file to base64 so it can be embedded in HTML."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def get_bytes(image_path):
    """Read image bytes for Streamlit page icon."""
    with open(image_path, "rb") as f:
        return f.read()


logo_path = "assets/logo.png"
logo_base64 = get_base64(logo_path)
logo_bytes = get_bytes(logo_path)

# -----------------------------
# PAGE ROUTING & TOP NAVIGATION ANCHOR LINK INTERCEPTOR
# -----------------------------
if query_page == "home":
    st.markdown(
        """
        <script>
            window.addEventListener('DOMContentLoaded', (event) => {
                const links = window.parent.document.querySelectorAll('a');
                links.forEach(link => {
                    if (link.textContent.toLowerCase().includes('about')) {
                        link.setAttribute('href', '#about-us-section');
                        link.setAttribute('target', '_self');
                    }
                });
            });
        </script>
        """,
        unsafe_allow_html=True
    )

# -----------------------------
# ROUTER DISPATCHER PIPELINES (DITO NA TAYO MAG-IMPORT!)
# -----------------------------
if query_page == "home":
    from landing_page import landing_page
    landing_page()

elif query_page == "overview":
    from app_pages.overview import overview_page
    overview_page()

elif query_page == "price_forecast":
    from app_pages.price_forecast import PriceForecast as price_forecast
    price_forecast()

elif query_page == "yield_forecast":
    from app_pages.yield_forecast import YieldForecast1 as yield_forecast
    yield_forecast()

elif query_page == "login":
    from app_pages.login import login_page
    login_page()

elif query_page == "lgu_dashboard":
    from app_pages.lgu_dashboard import lgu_dashboard
    lgu_dashboard()