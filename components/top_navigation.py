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
    # NAVIGATION BAR STYLES
    # =====================================================
    st.markdown("""
    <style>

    /* Bottom border separating navbar from page content */
    .navbar-divider {
        margin-top: -1rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid #e5e5e5;
    }

    /* Navigation buttons */
    div[data-testid="stButton"] > button {
        border: none;
        background: transparent;

        color: #1B5E20;

        font-family: Poppins, sans-serif;
        font-size: 1.2rem;
        font-weight: 600;

        width: 100%;
        height: 45px;

        transition: 0.3s;
    }

    /* Hover effect */
    div[data-testid="stButton"] > button:hover {
        color: #2E7D32;
        background: rgba(27, 94, 32, 0.05);
    }

    </style>
    """, unsafe_allow_html=True)

    # =====================================================
    # NAVBAR LAYOUT
    # =====================================================
    # Column structure:
    # [Left Margin | Logo | Home | Price | Yield | About | LGU]
    col_space, col_logo, col1, col2, col3, col4, col5 = st.columns(
        [0.5, 2, 1, 1, 1, 2, 1]
    )

    # =====================================================
    # LOGO
    # =====================================================
    with col_logo:
        st.image("assets/logo.png", width=150)

    # =====================================================
    # NAVIGATION BUTTONS & ROUTING LOGIC
    # =====================================================
    current_page = st.query_params.get("page", "home")

    with col1:
        if st.button("Home", use_container_width=True):
            st.query_params["page"] = "home"
            st.rerun()

    with col2:
        if st.button("Overview", use_container_width=True):
            st.query_params["page"] = "overview"
            st.rerun()

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
        if st.button("LGU Portal", use_container_width=True):
            st.query_params["page"] = "login"
            st.rerun()

    # =====================================================
    # NAVBAR DIVIDER
    # =====================================================
    st.markdown(
        '<div class="navbar-divider"></div>',
        unsafe_allow_html=True
    )