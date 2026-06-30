import streamlit as st
import base64

st.set_page_config(
    page_title="PalaySense",
    layout="wide",
    initial_sidebar_state="collapsed"  # Forces any default sidebar completely out of view
)

# -----------------------------
# IMPORT PAGE MODULES
# -----------------------------
from landing_page import landing_page
from app_pages.overview import overview_page
from app_pages.yield_forecast import YieldForecast1 as yield_forecast
from app_pages.price_forecast import PriceForecast as price_forecast
from app_pages.lgu_dashboard import lgu_dashboard
from app_pages.login import login_page
from app_pages.about import about_page
from components.top_navigation import top_navigation
from components.styles import load_css

load_css()

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

query_page = st.query_params.get("page", "home")

# If the user is on the homepage, inject a tiny JavaScript utility.
# This maps the top navigation element to smoothly jump down to the About section.
if query_page == "home":
    st.markdown(
        """
        <script>
            // This code runs in the browser background to link your top navigation element 
            // directly to the #about-us-section element at the bottom of the landing page.
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
# ROUTER DISPATCHER PIPELINES
# -----------------------------
if query_page == "home":
    landing_page()

elif query_page == "overview":
    overview_page()

elif query_page == "price_forecast":
    price_forecast()

elif query_page == "yield_forecast":
    yield_forecast()

elif query_page == "login":
    login_page()

elif query_page == "about":
    about_page()

elif query_page == "lgu_dashboard":
    lgu_dashboard()