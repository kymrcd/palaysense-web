import streamlit as st

def load_css():
    st.markdown("""
    <style>

    .block-container {
        max-width: 100% !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
    }

    /* GLOBAL */
    html, body {
        font-family: 'Poppins', sans-serif;
        background-color: #f6f8f5;
    }

    /* HERO SECTION */
    .hero {
        background:
            linear-gradient(rgba(14, 56, 22, 0.65),
            rgba(14, 56, 22, 0.65)),
            url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=2070");
        background-size: cover;
        background-position: center;
        min-height: 90vh;
        width: 100%;
        border-radius: 20px;
        padding: 5vw;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        color: white;
    }

    .hero h1 {
        font-size: clamp(2.5rem, 6vw, 5rem);
        color: white;
        margin-bottom: 10px;
    }

    .hero p {
        font-size: clamp(1rem, 2vw, 1.4rem);
        color: white;
    }

    /* FEATURE CARDS */
    .grid {
        display: flex;
        gap: 20px;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 30px;
    }

    .card {
        width: 280px;
        background: white;
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.08);
        transition: transform 0.2s ease;
    }

    .card:hover {
        transform: translateY(-5px);
    }

    .card h3 {
        color: #2e5d34;
    }

    .card p {
        color: #555;
        font-size: 14px;
    }

    .cta {
        margin-top: 50px;
        text-align: center;
        padding: 40px;
        background: #e7f5ea;
        border-radius: 16px;
    }

    </style>
    """, unsafe_allow_html=True)