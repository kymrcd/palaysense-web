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

load_css()

# Robust query_params parsing — handles both str and list returns across Streamlit versions
_raw_page = st.query_params.get("page", "home")
if isinstance(_raw_page, list):
    query_page = _raw_page[0] if _raw_page else "home"
else:
    query_page = str(_raw_page).strip() if _raw_page else "home"
if query_page not in ("home", "overview", "price_forecast", "yield_forecast", "login", "lgu_dashboard"):
    query_page = "home"

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