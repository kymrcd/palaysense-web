"""
PalaySense LGU Dashboard — Yield Analytics
==========================================
Subpages: Provincial / Municipal / Forecast.
Reuses the existing yield forecast logic (yield_forecast.py) wrapped in
the new design system with a clean header.
"""
import streamlit as st

from . import theme
from . import data_layer as dl


def render(df, dr, active_page):
    if active_page == "provincial":
        theme.page_title("Provincial Yield Analytics",
                         "Historical quarterly yield performance.")
        year = theme.year_filter(df, key="lgu_yield_year")
        if year is None:
            st.info("No year data available.")
            return
        _render_provincial(df, year, dr)
    elif active_page == "municipal":
        theme.page_title("Municipal Yield Analytics",
                         "Yield data across Bataan municipalities.")
        _render_municipal(dr)
    else:
        theme.page_title("Yield Forecast",
                         "Quarterly forward-looking yield projections.")
        _render_forecast(dr)


def _render_provincial(df, year, dr):
    import plotly.graph_objects as go
    quarterly = dl.get_quarterly_yield(df)
    hist = quarterly[quarterly["year"] == year].copy()
    if hist.empty:
        st.info("No data available for the selected year.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["quarter_label"], y=hist["quarterly_yield_mt_per_ha"],
                             mode="lines+markers", name="Yield",
                             line=dict(color=theme.HISTORICAL_COLOR, width=3), marker=dict(size=7)))
    fig.update_layout(
        yaxis_title="MT/ha",
        height=400, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family=theme.FONT, size=12),
        yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
        margin=dict(t=30, b=40, l=40, r=40),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"prov_yield_{year}")


def _render_municipal(dr):
    from app_pages.yield_forecast import YieldForecast1
    with theme.section_card(title="Municipal Yield",
                            desc="Yield-related data across municipalities.",
                            icon_name="eco"):
        YieldForecast1()


def _render_forecast(dr):
    from app_pages.yield_forecast import YieldForecast1
    with theme.section_card(title="Quarterly Yield Forecast",
                            desc="Projected provincial yield for the next four quarters.",
                            icon_name="query_stats"):
        YieldForecast1()
