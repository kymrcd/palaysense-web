import streamlit as st


def top_navigation():
    """
    Displays the main navigation bar for the public-facing pages.

    Navigation is handled using Streamlit query parameters:
    ?page=home
    ?page=price_forecast
    ?page=yield_forecast
    ?page=login
    """

    # =====================================================
    # NAVIGATION BAR STYLES — reverted + fixed alignment for "About Us"
    # =====================================================
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap');

    /* Wrapper to scope top-nav buttons only */
    .topnav-wrap { margin: 0 -1rem; }

    /* Bottom border separating navbar from page content */
    .navbar-divider {
        margin-top: 0.6rem;
        margin-bottom: 1.2rem;
        border-bottom: 1px solid #e5e5e5;
    }

    /* Scope nav buttons — avoid leaking to sidebar */
    .topnav-wrap div[data-testid="stButton"] {
        margin-top: 0 !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .topnav-wrap div[data-testid="stButton"] > button {
        border: none !important;
        background: transparent !important;
        color: #1B5E20 !important;
        font-family: Poppins, sans-serif !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 12px !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        white-space: nowrap !important;
        line-height: 1 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .topnav-wrap div[data-testid="stButton"] > button:hover {
        color: #2E7D32 !important;
        background: rgba(27, 94, 32, 0.06) !important;
    }
    /* Keep divider tight */
    .topnav-wrap + .navbar-divider { margin-top: 0.4rem; }
    </style>
    """, unsafe_allow_html=True)

    # =====================================================
    # NAVBAR LAYOUT — equal-width nav items, About Us correctly sized
    # =====================================================
    st.markdown('<div class="topnav-wrap">', unsafe_allow_html=True)
    col_space, col_logo, col1, col2, col3, col5 = st.columns(
        [0.4, 1.6, 1, 1, 1.15, 1], gap="small", vertical_alignment="center"
    )

    # =====================================================
    # LOGO
    # =====================================================
    with col_logo:
        st.image("assets/logo.png", width=132)

    # =====================================================
    # NAVIGATION BUTTONS & ROUTING LOGIC
    # =====================================================
    _raw = st.query_params.get("page", "home")
    if isinstance(_raw, list):
        current_page = _raw[0] if _raw else "home"
    else:
        current_page = str(_raw).strip() if _raw else "home"

    with col1:
        if st.button("Home", use_container_width=True):
            st.query_params["page"] = "home"
            # st.rerun() is optional — query_params change already triggers rerun
            try:
                st.rerun()
            except Exception:
                pass

    with col2:
        if st.button("Overview", use_container_width=True):
            st.query_params["page"] = "overview"
            try:
                st.rerun()
            except Exception:
                pass

    # =====================================================
    # SINGLE-PAGE ANCHOR JUMP FOR "ABOUT US"
    # =====================================================
    with col3:
        if st.button("About Us", use_container_width=True):
            if current_page == "home":
                # Smooth scroll directly to the section without refreshing the page
                st.components.v1.html(
                    """
                    <script>
                        var element = window.parent.document.getElementById('about-us-section');
                        if (element) {
                            element.scrollIntoView({ behavior: 'smooth' });
                        }
                    </script>
                    """,
                    height=0,
                    width=0
                )
            else:
                # If on another page, go home first and pass the hash anchor directly to the window URL
                st.query_params["page"] = "home"
                st.components.v1.html(
                    """
                    <script>
                        window.parent.location.href = '?page=home#about-us-section';
                    </script>
                    """,
                    height=0,
                    width=0
                )

    with col5:
        if st.button("OPA Portal", use_container_width=True):
            st.query_params["page"] = "login"
            try:
                st.rerun()
            except Exception:
                pass

    st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # NAVBAR DIVIDER
    # =====================================================
    st.markdown(
        '<div class="navbar-divider"></div>',
        unsafe_allow_html=True
    )