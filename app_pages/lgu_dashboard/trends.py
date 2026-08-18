"""
PalaySense LGU Dashboard — Trends & Patterns
============================================
Historical-only analytics page (no forecasting).
Subpages: Price Trends / Yield Trends / Historical Comparison.
Uses the existing cleaned historical datasets.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import theme
from . import data_layer as dl


def render(df, dr, active_page):
    if active_page == "price":
        theme.page_title("Price Trends",
                         "Historical price movements across municipalities.")
        _render_price_trends(df, dr)
    elif active_page == "yield":
        theme.page_title("Yield Trends",
                         "Historical yield performance over time.")
        _render_yield_trends(df)
    else:
        theme.page_title("Historical Comparison",
                         "Compare every municipality across the selected range.")
        _render_historical_comparison(dr)


def _filters_metric(df):
    """Metric selector: Price or Yield."""
    metric = st.selectbox("Metric", ["Price", "Yield"], key="trend_metric")
    return metric


def _render_price_trends(df, dr):
    with theme.section_card():
        # Range filter
        years = sorted(df["year"].unique())
        if len(years) < 2:
            st.info("Not enough year data for a range comparison.")
            return
        lo, hi = st.select_slider("Range", options=years, value=(years[0], years[-1]), key="price_range")
        sub = df[(df["year"] >= lo) & (df["year"] <= hi)].copy()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sub["date"], y=sub["fancy_palay_price"],
                                 mode="lines", name="Fancy Palay",
                                 line=dict(color=theme.FANCY_COLOR, width=2)))
        fig.add_trace(go.Scatter(x=sub["date"], y=sub["other_variety_price"],
                                 mode="lines", name="Regular Palay",
                                 line=dict(color=theme.REGULAR_COLOR, width=2)))
        fig.update_layout(
            yaxis_title="₱ / kg",
            height=420, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(t=30, b=40, l=40, r=40),
        )
        st.plotly_chart(fig, use_container_width=True, key="price_trends_all")


def _render_yield_trends(df):
    with theme.section_card():
        quarterly = dl.get_quarterly_yield(df)
        years = sorted(quarterly["year"].unique())
        if len(years) < 2:
            st.info("Not enough year data.")
            return
        lo, hi = st.select_slider("Range", options=years, value=(years[0], years[-1]), key="yield_range")
        sub = quarterly[(quarterly["year"] >= lo) & (quarterly["year"] <= hi)].copy()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sub["quarter_label"], y=sub["quarterly_yield_mt_per_ha"],
                                 mode="lines+markers", name="Yield",
                                 line=dict(color=theme.HISTORICAL_COLOR, width=3), marker=dict(size=6)))
        fig.update_layout(
            yaxis_title="MT/ha",
            height=420, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=12),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(t=30, b=40, l=40, r=40),
        )
        st.plotly_chart(fig, use_container_width=True, key="yield_trends_all")


def _render_historical_comparison(dr):
    with theme.section_card():

        muni = dr.municipality_df
        if muni is None or getattr(muni, "empty", True) or "palay_production" not in muni.columns:
            st.info("Municipality production dataset not available.")
            return

        m = muni.copy()
        m["year"] = pd.to_datetime(m["date"]).dt.year
        years = sorted(m["year"].dropna().unique())
        if len(years) < 1:
            st.info("No municipality year data.")
            return

        # Filters
        f1, f2 = st.columns(2)
        with f1:
            lo, hi = st.select_slider("Range", options=years, value=(years[0], years[-1]), key="hist_range")
        with f2:
            munis = sorted(m["municipality"].dropna().unique())
            selected = st.multiselect("Municipalities", options=munis, default=munis, key="hist_munis")

        sub = m[(m["year"] >= lo) & (m["year"] <= hi)].copy()
        if selected:
            sub = sub[sub["municipality"].isin(selected)]

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
        st.plotly_chart(fig, use_container_width=True, key="hist_compare")
