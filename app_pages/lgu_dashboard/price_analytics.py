"""
PalaySense LGU Dashboard — Price Analytics
==========================================
Subpages: Provincial / Municipal / Forecast.
Reuses the existing price forecast logic (price_forecast.py) but wraps
it in the new design system with a clean header.
"""
import streamlit as st

from . import theme
from . import data_layer as dl


def render(df, dr, active_page):
    if active_page == "provincial":
        theme.page_title("Provincial Price Analytics",
                         "Historical price movements and yearly averages for Fancy and Regular Palay.")
        year = theme.year_filter(df, key="lgu_price_year")
        if year is None:
            st.info("No year data available.")
            return
        _render_provincial(df, year, dr)
    elif active_page == "municipal":
        theme.page_title("Municipal Price Analytics",
                         "Palay prices across Bataan municipalities.")
        _render_municipal(dr)
    else:
        theme.page_title("Price Forecast",
                         "3-month forward-looking price projections.")
        _render_forecast(dr)


def _render_provincial(df, year, dr, palay_types=("Fancy", "Regular")):
    hist = dl.filter_by_year(df, year)
    if hist.empty:
        st.info("No data available for the selected year.")
        return

    import plotly.graph_objects as go
    fig = go.Figure()
    if "Fancy" in palay_types:
        fig.add_trace(go.Scatter(x=hist["date"], y=hist["fancy_palay_price"],
                                 mode="lines+markers", name="Fancy Palay",
                                 line=dict(color=theme.FANCY_COLOR, width=2.5), marker=dict(size=4)))
    if "Regular" in palay_types:
        fig.add_trace(go.Scatter(x=hist["date"], y=hist["other_variety_price"],
                                 mode="lines+markers", name="Regular Palay",
                                 line=dict(color=theme.REGULAR_COLOR, width=2.5), marker=dict(size=4)))
    fig.update_layout(
        yaxis_title="₱ / kg",
        height=400, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family=theme.FONT, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
        margin=dict(t=30, b=40, l=40, r=40),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"prov_price_{year}")


def _render_municipal(dr):
    from app_pages.price_forecast import PriceForecast
    # The existing PriceForecast handles municipal tables + model performance.
    # We wrap it minimally; it already renders its own content.
    with theme.section_card(title="Municipal Price Forecast",
                            desc="Per-municipality palay price data by rice variety and season.",
                            icon_name="location_on"):
        PriceForecast()


def _render_forecast(dr):
    from app_pages.price_forecast import PriceForecast
    with theme.section_card(title="3-Month Price Forecast",
                            desc="Projected Fancy and Regular palay prices for the next three months.",
                            icon_name="insights"):
        PriceForecast()
