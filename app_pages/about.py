import streamlit as st


def about_page():

    st.title("About PalaySense")

    st.markdown("""
    PalaySense is a forecasting and decision-support dashboard designed
    to provide accessible insights on palay production, yield trends,
    and market prices in the Province of Bataan.
    """)

    st.markdown("---")

    st.header("Our Mission")

    st.write("""
    To help farmers, researchers, local government units, and the public
    make informed decisions through data-driven agricultural forecasting.
    """)

    st.header("Objectives")

    st.markdown("""
    - Forecast palay yield trends
    - Forecast palay market prices
    - Monitor provincial production performance
    - Improve accessibility of agricultural information
    - Support evidence-based planning
    """)

    st.header("Data Sources")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("Philippine Statistics Authority (PSA)")

    with col2:
        st.info("Palay Production Survey")

    with col3:
        st.info("PhilRice")

    st.header("Target Users")

    st.markdown("""
    - Farmers
    - Agricultural stakeholders
    - Researchers
    - Students
    - Local Government Units
    """)

    st.header("Project Team")

    st.write("""
    BS Data Science Students

    Bataan Peninsula State University
    """)

    st.markdown("---")

    st.caption(
        "PalaySense • Forecasting Dashboard for Bataan"
    )