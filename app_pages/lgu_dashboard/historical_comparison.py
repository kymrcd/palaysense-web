"""
PalaySense LGU Dashboard — Historical Comparison
================================================
Consolidates all historical/trend views into a single page with 3 tabs:

  Tab 1: Municipal Production Comparison
  Tab 2: Provincial Price Trends
  Tab 3: Municipal Price Trends

Year filtering uses an unlimited st.multiselect (no arbitrary range limits).
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import theme


# ------------------------------------------------------------------
# Tab helpers
# ------------------------------------------------------------------
def _year_multiselect(df, key, label="Select Years"):
    """Unlimited multi-select year picker (no range slider)."""
    years = sorted(df["year"].dropna().unique().tolist())
    if not years:
        return []
    selected = st.multiselect(
        label,
        options=years,
        default=years,
        key=key,
        help="Select any number of years — no range limit.",
    )
    return selected


# ------------------------------------------------------------------
# Tab 1: Municipal Production Comparison
# ------------------------------------------------------------------
def _production_comparison_tab(dr):
    with theme.section_card(title="Municipal Production Comparison",
                            desc="Historical production comparison across municipalities.",
                            icon_name="compare_arrows"):
        muni = dr.municipality_df
        if muni is None or getattr(muni, "empty", True) or "palay_production" not in muni.columns:
            st.info("Municipality production dataset not available.")
            return

        m = muni.copy()
        m["year"] = pd.to_datetime(m["date"]).dt.year
        if "year" not in m.columns or m["year"].dropna().empty:
            st.info("No municipality year data.")
            return

        # Unlimited year selector (replaces the restricted range slider)
        selected_years = _year_multiselect(m, key="hist_prod_years", label="Select Years")
        if not selected_years:
            st.info("Please select at least one year.")
            return

        # Municipality multiselect
        munis = sorted(m["municipality"].dropna().unique().tolist())
        selected_munis = st.multiselect(
            "Municipalities", options=munis, default=munis, key="hist_prod_munis"
        )

        sub = m[m["year"].isin(selected_years)].copy()
        if selected_munis:
            sub = sub[sub["municipality"].isin(selected_munis)]

        if sub.empty:
            st.info("No data for the selected filters.")
            return

        # Aggregate by municipality + year
        agg = sub.groupby(["municipality", "year"])["palay_production"].sum().reset_index()

        fig = px.line(agg, x="year", y="palay_production", color="municipality", markers=True)
        fig.update_layout(
            yaxis_title="Production (MT)", xaxis_title="Year",
            height=460, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(t=30, b=40, l=40, r=40),
        )
        st.plotly_chart(fig, use_container_width=True, key="hist_prod_chart")


# ------------------------------------------------------------------
# Tab 2: Provincial Price Trends
# ------------------------------------------------------------------
def _provincial_price_trends_tab(df):
    with theme.section_card(title="Provincial Price Trends",
                            desc="Historical Fancy & Regular Palay price trends.",
                            icon_name="trending_up"):
        if df is None or df.empty or "year" not in df.columns:
            st.info("No provincial price data available.")
            return

        selected_years = _year_multiselect(df, key="hist_prov_price_years")
        if not selected_years:
            st.info("Please select at least one year.")
            return

        sub = df[df["year"].isin(selected_years)].copy()
        years_label = ', '.join(map(str, selected_years))

        # --- Combined Fancy vs Regular comparison chart (Tab 2) ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sub["date"], y=sub["fancy_palay_price"],
                                 mode="lines", name="Fancy Palay",
                                 line=dict(color=theme.FANCY_COLOR, width=2)))
        fig.add_trace(go.Scatter(x=sub["date"], y=sub["other_variety_price"],
                                 mode="lines", name="Regular Palay",
                                 line=dict(color=theme.REGULAR_COLOR, width=2)))
        fig.update_layout(
            yaxis_title="₱ / kg", xaxis_title="Date",
            height=420, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(t=30, b=40, l=40, r=40),
        )
        st.plotly_chart(fig, use_container_width=True, key="hist_prov_price_chart")

        # --- Side-by-side Fancy and Regular line charts ---
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            fig_f = go.Figure()
            fig_f.add_trace(go.Scatter(x=sub["date"], y=sub["fancy_palay_price"],
                                       mode="lines", name="Fancy Palay",
                                       line=dict(color=theme.FANCY_COLOR, width=2)))
            fig_f.update_layout(
                yaxis_title="₱ / kg",
                height=380, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family=theme.FONT, size=11),
                margin=dict(t=30, b=40, l=40, r=40),
            )
            st.plotly_chart(fig_f, use_container_width=True, key="hist_prov_fancy_chart")
        with col_b:
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatter(x=sub["date"], y=sub["other_variety_price"],
                                       mode="lines", name="Regular Palay",
                                       line=dict(color=theme.REGULAR_COLOR, width=2)))
            fig_r.update_layout(
                yaxis_title="₱ / kg",
                height=380, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family=theme.FONT, size=11),
                margin=dict(t=30, b=40, l=40, r=40),
            )
            st.plotly_chart(fig_r, use_container_width=True, key="hist_prov_regular_chart")


# ------------------------------------------------------------------
# Tab 3: Municipal Price Trends
# ------------------------------------------------------------------
# Rice type (Hybrid/Inbred) + classification (Premium/Ordinary) -> column prefix
_RICE_TYPE_PREFIX = {
    "Hybrid": "hybrid",
    "Inbred": "inbred",
}
_RICE_CLASS_SUFFIX = {
    "Premium": "premium",
    "Ordinary": "ordinary",
}
_SEASON_SUFFIX = {"Dry": "dry", "Wet": "wet"}

_MUNICIPALITY_COLORS = {
    "Abucay": "#1f77b4", "Bagac": "#ff7f0e", "Balanga": "#2ca02c",
    "Dinalupihan": "#d62728", "Hermosa": "#9467bd", "Limay": "#8c564b",
    "Mariveles": "#e377c2", "Morong": "#7f7f7f", "Orani": "#bcbd22",
    "Orion": "#17becf", "Pilar": "#ff9896", "Samal": "#98df8a",
}


def _municipal_price_trends_tab(dr):
    with theme.section_card(title="Municipal Price Trends",
                            desc="Historical municipal price trends by rice type, classification, and municipality.",
                            icon_name="location_on"):
        muni_hist = getattr(dr, "municipality_history_df", None)
        if muni_hist is None or getattr(muni_hist, "empty", True):
            st.info("Municipal price history dataset not available.")
            return

        history = muni_hist.copy()
        history = history[history["municipality"].notna()].copy()
        if "month" in history.columns:
            history["month"] = history["month"].str.title()

        # Filters (states preserved inside this tab)
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            # Season (Dry / Wet)
            selected_season = st.selectbox("Season", options=["Dry", "Wet"], key="hist_muni_season")
        with f2:
            # Municipal Rice Type (Hybrid / Inbred) — NOT provincial Fancy/Regular
            selected_rice_type = st.selectbox("Rice Type", options=["Hybrid", "Inbred"],
                                              key="hist_muni_ricetype")
        with f3:
            # Municipal Rice Classification (Premium / Ordinary)
            selected_class = st.selectbox("Rice Classification",
                                          options=["Premium", "Ordinary"],
                                          key="hist_muni_class")
        with f4:
            year_list = sorted(history["year"].dropna().unique().tolist())
            selected_years = st.multiselect("Year Selection", options=year_list, default=year_list,
                                            key="hist_muni_years")
        with f5:
            muni_list = sorted(history["municipality"].dropna().unique().tolist())
            selected_munis = st.multiselect("Municipality Selection", options=muni_list, default=muni_list,
                                            key="hist_muni_munis")

        if not selected_years:
            st.info("Please select at least one year.")
            return

        # Build the municipal-specific column name dynamically, e.g. "hybridpremium_dry"
        selected_column = (
            f"{_RICE_TYPE_PREFIX[selected_rice_type]}"
            f"{_RICE_CLASS_SUFFIX[selected_class]}_{_SEASON_SUFFIX[selected_season]}"
        )

        filtered = history[history["year"].isin(selected_years)].copy()
        if selected_munis:
            filtered = filtered[filtered["municipality"].str.upper().isin([m.upper() for m in selected_munis])]

        if filtered.empty or selected_column not in filtered.columns:
            st.info("No data for the selected filters.")
            return

        # Title-case municipality names to match color map
        filtered["municipality"] = filtered["municipality"].str.title()

        muni_label = ", ".join(title_m for title_m in [
            m.strip().title() for m in selected_munis
        ][:2]) + ("..." if len(selected_munis) > 2 else "")

        fig_hist = px.line(
            filtered,
            x="month",
            y=selected_column,
            color="municipality",
            color_discrete_map=_MUNICIPALITY_COLORS,
            markers=True,
        )
        fig_hist.update_xaxes(
            categoryorder="array",
            categoryarray=[
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ],
        )
        fig_hist.update_layout(
            xaxis_title="Month", yaxis_title="Price (₱/kg)",
            plot_bgcolor="white", paper_bgcolor="white", height=500,
            margin=dict(t=30, b=40, l=40, r=40),
        )
        st.plotly_chart(fig_hist, use_container_width=True, key="hist_muni_price_chart")


# ------------------------------------------------------------------
# Main page
# ------------------------------------------------------------------
def render(df, dr):
    theme.page_title("Historical Comparison",
                     "Compare municipalities and historical trends across the selected range.")

    tab_prod, tab_prov_price, tab_muni_price = st.tabs([
        ":material/bar_chart: Municipal Production Comparison",
        ":material/trending_up: Provincial Price Trends",
        ":material/label: Municipal Price Trends",
    ])

    with tab_prod:
        _production_comparison_tab(dr)
    with tab_prov_price:
        _provincial_price_trends_tab(df)
    with tab_muni_price:
        _municipal_price_trends_tab(dr)
