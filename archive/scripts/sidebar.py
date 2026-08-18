import streamlit as st

def show_sidebar():
    with st.sidebar:
        st.markdown("## Filters")

        selected_municipality = st.selectbox(
            "Municipality",
            [
                "All Municipalities",
                "Abucay",
                "Bagac",
                "Balanga",
                "Dinalupihan",
                "Hermosa",
                "Limay",
                "Mariveles",
                "Morong",
                "Orani",
                "Orion",
                "Pilar",
                "Samal"
            ],
            key="filter_municipality"
        )

        selected_palaytype = st.selectbox(
            "Palay Variety",
            [
                "All Varieties",
                "Fancy Palay",
                "Regular Palay"
            ],
            key="filter_palay_variety"

        )
        selected_year_filter = st.selectbox(
            "Year",
            ["Latest", "2025", "2024", "2023", "2022", "2021"],
            key="filter_year"
        )

        apply_filters = st.button("Apply Filters", width="stretch")
        reset_filters = st.button("Reset", width="stretch")

        st.markdown("---")