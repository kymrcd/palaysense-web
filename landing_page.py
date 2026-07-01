import streamlit as st


def landing_page():
    if st.session_state.pop("logout_success", False):
        st.toast("Logged out successfully!", icon="✅")

    st.markdown("""
    <style>
    /* 1. IMPORT GOOGLE FONT */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght=400;500;600;700;800&display=swap');

    /* FONT: POPPINS */
    .hero-title, .hero-subtitle, .section-title, .feature-title, .stats-number, .about-heading {
        font-family: 'Poppins', sans-serif;
    }

    .block-container {
        padding-top: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100%;
    }

    /* HERO SECTION - Main Header*/
    .hero {
        min-height: 90vh;
        display: flex;
        align-items: center;
        padding: 0 8vw;
        margin-top: -35px;
        background:
            linear-gradient(
                rgba(0,0,0,0.55),
                rgba(0,0,0,0.55)
            ),
            url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=2070");
        background-size: cover;
        background-position: center;
    }

    .hero-content {
        max-width: 800px;
        color: white;
    }

    .hero-title {
        font-size: clamp(3rem, 6vw, 5rem);
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 10px;
    }

    .hero-subtitle {
        font-size: clamp(1.3rem, 2.5vw, 2rem);
        font-weight: 600;
        color: #FFD54F;
        margin-bottom: 20px;
        line-height: 1.3;
    }

    .hero-description {
        font-size: 1.1rem;
        line-height: 1.7;
        margin-bottom: 35px;
        opacity: 0.90;
        color: #f0f0f0;
    }

    .hero-buttons {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
    }

    .primary-btn {
        background: #2E7D32;
        color: white !important;
        text-decoration: none !important;
        padding: 14px 28px;
        border-radius: 10px;
        font-weight: 600;
        transition: 0.3s;
    }

    .primary-btn:hover {
        background: #1B5E20;
    }

    .secondary-btn {
        background: rgba(255,255,255,0.15);
        color: white !important;
        text-decoration: none !important;
        padding: 14px 28px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.3);
        font-weight: 600;
        transition: 0.3s;
    }

    .secondary-btn:hover {
        background: rgba(255,255,255,0.25);
    }

    .section-title {
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        color: #1B5E20;
        margin-top: 70px;
        margin-bottom: 30px;
    }

    .feature-grid, .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        padding: 0 8vw;
        margin-bottom: 50px;
    }

    .feature-card {
        background: white;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.08);
    }

    .feature-title {
        color: #1B5E20;
        font-weight: 700;
        font-size: 1.2rem;
        margin-bottom: 10px;
    }

    .stats-card {
        background: #F5F9F5;
        border-left: 5px solid #2E7D32;
        border-radius: 12px;
        padding: 25px;
        text-align: center;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.02);
    }

    .stats-number {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1B5E20;
        margin-bottom: 5px;
    }

    .stats-label {
        color: #555;
        font-size: 1rem;
    }

    /* ABOUT SECTION WRAPPER & CHILDS (GRADIENT APPLIED) */
    .about-wrapper {
        padding: 80px 8vw;
        background: linear-gradient(180deg, #F5F9F5 0%, #FFFFFF 100%) !important;
        border-top: 1px solid #E5E7EB;
        scroll-margin-top: 80px;
        display: block;
        width: 100%;
    }

    .about-inner {
        max-width: 1100px;
        margin: 0 auto;
    }

    .about-heading {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1B5E20;
        text-align: center;
        margin-bottom: 15px;
    }

    .about-divider {
        width: 60px;
        height: 4px;
        background-color: #FFD54F;
        margin: 0 auto 35px auto;
        border-radius: 2px;
    }

    .about-description {
        font-size: 1.1rem;
        line-height: 1.8;
        color: #4B5563;
        text-align: center;
        max-width: 850px;
        margin: 0 auto 50px auto;
    }

    .pillar-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 30px;
        margin-bottom: 60px;
    }

    .pillar-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }

    .pillar-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1B5E20;
        margin-bottom: 12px;
    }

    .pillar-text {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #6B7280;
    }

    .team-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #111827;
        text-align: center;
        margin-bottom: 30px;
    }
    
    .team-subtitle {
        font-size: 1rem;
        font-weight: 500;
        color: dark gray;
        text-align: center;
        margin-bottom: 10px;
    }

    .team-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 25px;
    }

    .team-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 30px 20px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
    }

    .team-avatar {
        width: 80px;
        height: 80px;
        background: #E8F5E9;
        color: #2E7D32;
        font-size: 2rem;
        line-height: 80px;
        border-radius: 50%;
        margin: 0 auto 15px auto;
        font-weight: 700;
    }

    .member-name {
        font-size: 1.15rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 4px;
    }

    .member-role {
        font-size: 0.88rem;
        font-weight: 600;
        color: #2E7D32;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

    # HERO SECTION
    st.markdown("""
    <div class="hero">
        <div class="hero-content">
            <div class="hero-title">PalaySense</div>
            <div class="hero-subtitle">Predictive Analytics for Sustainable Rice Farming</div>
            <div class="hero-description">
                Data-driven insights for rice production.
                Monitor agricultural trends, forecast rice yields,
                analyze market prices, and support smarter farming
                decisions through predictive analytics.
            </div>
            <div class="hero-buttons">
                <a href="?page=overview" target="_self" class="primary-btn"> Launch Dashboard </a>
                <a href="?page=login" target="_self" class="secondary-btn">LGU Portal</a>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # FEATURES SECTION
    st.markdown('<div class="section-title">Core Features</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-title">🌾 Yield Forecasting</div>
            Predict harvest output using historical production and environmental trends.
        </div>
        <div class="feature-card">
            <div class="feature-title">📈 Price Forecasting</div>
            Anticipate future rice market prices to support planning and decision-making.
        </div>
        <div class="feature-card">
            <div class="feature-title">🏛 LGU Insights</div>
            Provide local government units with accessible agricultural intelligence.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # AGRICULTURAL SNAPSHOT
    st.markdown('<div class="section-title">Agricultural Snapshot</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="stats-grid">
        <div class="stats-card">
            <div class="stats-number">4.7</div>
            <div class="stats-label">Tons / Hectare</div>
        </div>
        <div class="stats-card">
            <div class="stats-number">₱42</div>
            <div class="stats-label">Avg Rice Price / Kg</div>
        </div>
        <div class="stats-card">
            <div class="stats-number">92%</div>
            <div class="stats-label">Forecast Confidence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================================================
    # 🌟 ABOUT US COMPONENT BLOCK (With background gradient structure)
    # =========================================================================================
    st.markdown("""
    <div class="about-wrapper" id="about-us-section">
        <div class="about-inner">
            <div class="about-heading">About PalaySense</div>
            <div class="about-divider"></div>
            <div class="about-description">
                PalaySense is an innovative agricultural forecasting system engineered to empower regional development. 
                By utilizing advanced time-series analysis and machine learning workflows, our ecosystem translates historical 
                farming records into structural parameters—offering stakeholders clear clarity regarding expected harvest yields 
                and fluctuating market farmgate values across the province of Bataan.
            </div>
            <div class="pillar-grid">
                <div class="pillar-card">
                    <div class="pillar-title">Our Mission</div>
                    <div class="pillar-text">To bridge the gap between complex data science models and daily farming activities, giving local extension groups tools to maximize production strategies.</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-title">👁Our Vision</div>
                    <div class="pillar-text">To build a highly resilient, data-enabled agricultural ecosystem in Bataan where risk factor liabilities are reduced through algorithmic calculations.</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-title">⚡ Core Strategy</div>
                    <div class="pillar-text">By transforming massive spreadsheets into accessible, high-fidelity visual representations tailored specifically for local government management frameworks.</div>
                </div>
            </div>
            <div class="team-header">Meet The Capstone Team</div>
            <div class="team-subtitle">Bataan Peninsula State University - Main </div>
            <div class="team-grid">
                <div class="team-card">
                    <div class="team-avatar">SA</div>
                    <div class="member-name">Shanylou Aguilar</div>
                    <div class="member-role">Project Lead </div>
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
    """, unsafe_allow_html=True)