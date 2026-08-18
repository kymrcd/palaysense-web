import streamlit as st


def landing_page():
    if st.session_state.pop("logout_success", False):
        st.toast("Logged out successfully!")

    st.markdown(
        """
    <style>
    /* 1. IMPORT GOOGLE FONTS */
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* BASE TYPOGRAPHY & SCALING (Slightly compact for balanced zoom) */
    body, p, div, span, a {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    .hero-title, .hero-subtitle, .section-title, .feature-title, .stats-number, .about-heading, .pillar-title {
        font-family: 'DM Serif Display', serif !important;
    }

    .block-container {
        padding-top: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }

    /* HERO SECTION - Refined Hierarchy & Compact Spacing */
    .hero {
        min-height: 75vh;
        display: flex;
        align-items: center;
        padding: 0 8vw;
        margin-top: -35px;
        background:
            linear-gradient(
                90deg,
                rgba(12, 29, 15, 0.90) 0%,
                rgba(18, 43, 22, 0.72) 45%,
                rgba(18, 43, 22, 0.25) 100%
            ),
            url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=2070");
        background-size: cover;
        background-position: center;
    }

    .hero-content {
        max-width: 620px;
        color: white;
        padding: 30px 0;
    }

    .hero-title {
        font-size: 40px;
        font-weight: 400;
        line-height: 1.15;
        margin-bottom: 10px;
        letter-spacing: -0.3px;
        color: #FFFFFF;
    }

    .hero-subtitle {
        font-size: 17px;
        font-weight: 400;
        color: #E2C067;
        margin-bottom: 16px;
        line-height: 1.45;
    }

    .hero-description {
        font-size: 14px;
        line-height: 1.6;
        margin-bottom: 26px;
        color: #D1D5DB;
        font-weight: 400;
    }

    .hero-buttons {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }

    .primary-btn {
        background: #2D6A4F;
        color: #FFFFFF !important;
        text-decoration: none !important;
        padding: 10px 24px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13.5px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(45, 106, 79, 0.3);
        display: inline-block;
    }

    .primary-btn:hover {
        background: #1B4332;
        transform: translateY(-1px);
    }

    .secondary-btn {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(6px);
        color: #FFFFFF !important;
        text-decoration: none !important;
        padding: 10px 24px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.25);
        font-weight: 600;
        font-size: 13.5px;
        transition: all 0.2s ease;
        display: inline-block;
    }

    .secondary-btn:hover {
        background: #FFFFFF;
        border-color: #FFFFFF;
        color: #1B4332 !important;
        transform: translateY(-1px);
    }

    /* SECTION TITLES */
    .section-title {
        text-align: center;
        font-size: 1.75rem;
        font-weight: 400;
        color: #1B4332;
        margin-top: 50px;
        margin-bottom: 24px;
        letter-spacing: -0.3px;
    }

    /* FEATURE & STATS GRIDS */
    .feature-grid, .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 18px;
        padding: 0 8vw;
        margin-bottom: 40px;
    }

    /* FEATURE CARD */
    .feature-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 20px 22px;
        border: 1px solid #E2E8F0;
        box-shadow: 0px 3px 12px rgba(0, 0, 0, 0.03);
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
        color: #4B5563;
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: #2D6A4F;
        opacity: 0;
        transition: opacity 0.2s ease;
    }

    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0px 8px 20px rgba(0, 0, 0, 0.06);
    }

    .feature-card:hover::before {
        opacity: 1;
    }

    .feature-title {
        color: #1B4332;
        font-weight: 400;
        font-size: 1.1rem;
        margin-bottom: 8px;
    }

    /* STATS CARD */
    .stats-card {
        background: #F8FAF8;
        border-radius: 10px;
        padding: 22px 18px;
        text-align: center;
        border: 1px solid #E2E8F0;
        border-top: 3px solid #2D6A4F;
        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.02);
    }

    .stats-number {
        font-size: 2rem;
        font-weight: 400;
        color: #1B4332;
        margin-bottom: 4px;
        line-height: 1;
    }

    .stats-label {
        color: #64748B;
        font-size: 0.82rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* ABOUT SECTION WRAPPER */
    .about-wrapper {
        padding: 60px 8vw;
        background: linear-gradient(180deg, #F4F7F4 0%, #FFFFFF 100%) !important;
        border-top: 1px solid #E2E8F0;
        scroll-margin-top: 60px;
        display: block;
        width: 100%;
    }

    .about-inner {
        max-width: 960px;
        margin: 0 auto;
    }

    .about-heading {
        font-size: 2rem;
        font-weight: 400;
        color: #1B4332;
        text-align: center;
        margin-bottom: 8px;
    }

    .about-divider {
        width: 40px;
        height: 3px;
        background-color: #D4A373;
        margin: 0 auto 20px auto;
        border-radius: 2px;
    }

    .about-description {
        font-size: 0.95rem;
        line-height: 1.7;
        color: #4B5563;
        text-align: center;
        max-width: 720px;
        margin: 0 auto 40px auto;
    }

    .pillar-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 20px;
        margin-bottom: 50px;
    }

    .pillar-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 22px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }

    .pillar-title {
        font-size: 1.1rem;
        font-weight: 400;
        color: #1B4332;
        margin-bottom: 8px;
    }

    .pillar-text {
        font-size: 0.88rem;
        line-height: 1.55;
        color: #64748B;
    }

    /* TEAM SECTION */
    .team-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0F172A;
        text-align: center;
        margin-bottom: 4px;
    }

    .team-subtitle {
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748B;
        text-align: center;
        margin-bottom: 30px;
    }

    .team-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 18px;
    }

    .team-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 22px 14px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }

    .team-avatar {
        width: 56px;
        height: 56px;
        background: #E8F5E9;
        color: #2D6A4F;
        font-size: 1.1rem;
        line-height: 56px;
        border-radius: 50%;
        margin: 0 auto 12px auto;
        font-weight: 700;
        border: 2px solid #D8F3DC;
    }

    .member-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 3px;
    }

    .member-role {
        font-size: 0.75rem;
        font-weight: 600;
        color: #2D6A4F;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # HERO SECTION
    st.markdown(
        """
    <div class="hero">
        <div class="hero-content">
            <div class="hero-title">Empowering Bataan's Palay Agriculture</div>
            <div class="hero-subtitle">Delivering data-driven forecasts and actionable insights to support 
                                        smarter agricultural planning and sustainable palay production.</div>
            <div class="hero-description">
                Data-driven insights for palay production.
                Monitor agricultural trends, forecast palay yields,
                analyze market prices, and support smarter farming
                decisions through predictive analytics.
            </div>
            <div class="hero-buttons">
                <a href="?page=overview" target="_self" class="primary-btn"> Launch Dashboard </a>
                <a href="?page=login" target="_self" class="secondary-btn">LGU Portal</a>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # FEATURES SECTION
    st.markdown(
        '<div class="section-title">Core Features</div>', unsafe_allow_html=True
    )
    st.markdown(
        """
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-title">Yield Forecasting</div>
            Predict harvest output using historical production and environmental trends.
        </div>
        <div class="feature-card">
            <div class="feature-title">Price Forecasting</div>
            Anticipate future palay market prices to support planning and decision-making.
        </div>
        <div class="feature-card">
            <div class="feature-title">LGU Insights</div>
            Provide local government units with accessible agricultural intelligence.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # AGRICULTURAL SNAPSHOT
    st.markdown(
        '<div class="section-title">Agricultural Snapshot</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <div class="stats-grid">
        <div class="stats-card">
            <div class="stats-number">4.7</div>
            <div class="stats-label">Tons / Hectare</div>
        </div>
        <div class="stats-card">
            <div class="stats-number">₱42</div>
            <div class="stats-label">Avg Palay Price / Kg</div>
        </div>
        <div class="stats-card">
            <div class="stats-number">92%</div>
            <div class="stats-label">Forecast Confidence</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ABOUT US COMPONENT BLOCK
    st.markdown(
        """
    <div class="about-wrapper" id="about-us-section">
        <div class="about-inner">
            <div class="about-heading">About PalaySense</div>
            <div class="about-divider"></div>
            <div class="about-description">
                PalaySense is a decision-support platform that helps farmers and 
                local government units monitor agricultural trends, forecast palay yields, 
                and anticipate market price changes using historical data and predictive analytics.
            </div>
            <div class="pillar-grid">
                <div class="pillar-card">
                    <div class="pillar-title">Our Mission</div>
                    <div class="pillar-text">To bridge the gap between complex data science models and daily farming activities, giving local extension groups tools to maximize production strategies.</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-title">Our Vision</div>
                    <div class="pillar-text">To build a highly resilient, data-enabled agricultural ecosystem in Bataan where risk factor liabilities are reduced through algorithmic calculations.</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-title">Core Strategy</div>
                    <div class="pillar-text">By transforming massive spreadsheets into accessible, high-fidelity visual representations tailored specifically for local government management frameworks.</div>
                </div>
            </div>
            <div class="team-header">Meet The Capstone Team</div>
            <div class="team-subtitle">Bataan Peninsula State University - Main</div>
            <div class="team-grid">
                <div class="team-card">
                    <div class="team-avatar">SA</div>
                    <div class="member-name">Shanylou Aguilar</div>
                    <div class="member-role">Project Lead</div>
                </div>
                <div class="team-card">
                    <div class="team-avatar">JD</div>
                    <div class="member-name">Jela Marie Dela Cruz</div>
                    <div class="member-role">Lead Software Engineer</div>
                </div>
                <div class="team-card">
                    <div class="team-avatar">KM</div>
                    <div class="member-name">Kyla Mercado</div>
                    <div class="member-role">UI/UX Designer</div>
                </div>
                <div class="team-card">
                    <div class="team-avatar">JS</div>
                    <div class="member-name">Jerben Carl Santos</div>
                    <div class="member-role">Data & Research Analyst</div>
                </div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )