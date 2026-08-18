"""
PalaySense LGU Dashboard — Provincial Analytics
===============================================
Consolidates all provincial-level price and yield analytics into a single
page. Reuses the existing provincial price/yield charts and the historical
price/yield trend charts. Filters are limited to provincial data only
(Year + Palay Type Fancy/Regular).

Layout:
  • Provincial Price tab: single combined chart with Fancy & Regular lines
    (lines shown dynamically based on the Palay Type filter).
  • Provincial Yield tab: Historical/Forecast quarterly yield line chart
    (Line/Bar toggle) on the left with a styled Yield Insight summary
    side-card on the right showing trend status, selected-year average,
    and predicted forecast.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import theme
from . import price_analytics
from . import yield_analytics
from . import data_layer as dl


def _provincial_price_tab(df, dr):
    """Provincial price chart with inline Year + Palay Type filters.

    Renders a single combined chart where the Fancy and Regular price lines
    are shown dynamically based on the Palay Type multiselect selection.
    """
    years = dl.get_available_years(df)
    if not years:
        st.info("No year data available.")
        return

    with theme.section_card(title="Provincial Price Analytics",
                            desc="Historical Fancy and Regular Palay price movements.",
                            icon_name="trending_up"):
        # Inline Year + Palay Type filters side by side
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox(
                "YEAR",
                options=years,
                index=len(years) - 1,
                key="prov_price_year",
            )
        with col2:
            palay_types = st.multiselect(
                "Palay Type",
                options=["Fancy", "Regular"],
                default=["Fancy", "Regular"],
                key="prov_price_palay_types",
            )
            if not palay_types:
                palay_types = ["Fancy", "Regular"]

        hist = dl.filter_by_year(df, year)
        if hist.empty:
            st.info("No data available for the selected year.")
            return

        # Single combined chart with dynamically added traces
        fig = go.Figure()
        if "Fancy" in palay_types:
            fig.add_trace(go.Scatter(x=hist["date"], y=hist["fancy_palay_price"],
                                     mode="lines+markers", name="Fancy Palay",
                                     line=dict(color=theme.FANCY_COLOR, width=2.5),
                                     marker=dict(size=4)))
        if "Regular" in palay_types:
            fig.add_trace(go.Scatter(x=hist["date"], y=hist["other_variety_price"],
                                     mode="lines+markers", name="Regular Palay",
                                     line=dict(color=theme.REGULAR_COLOR, width=2.5),
                                     marker=dict(size=4)))

        fig.update_layout(
            yaxis_title="₱ / kg",
            height=400, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(t=30, b=40, l=40, r=40),
            title="Palay Price per Palay Type" if len(fig.data) > 1 else None,
        )
        st.plotly_chart(fig, use_container_width=True, key=f"prov_price_{year}_{'_'.join(palay_types)}")


def _provincial_yield_tab(df, dr):
    """Provincial Yield Forecast component.

    Renders a two-column layout:
      • Left (col_chart): Plotly Line/Bar chart for Quarterly Yield
        combining Historical + Forecast series (forecast shown dashed).
      • Right (col_summary): styled Yield Insight Summary side-card showing
        trend status (e.g. "STRONG DECREASE -11.9%"), selected-year average,
        and the predicted forecast.
    Year filter is placed inline inside the card.
    """
    years = dl.get_available_years(df)
    if not years:
        st.info("No year data available.")
        return

    with theme.section_card(title="Provincial Yield Forecast",
                            desc="Historical / forecast quarterly yield performance.",
                            icon_name="eco"):
        # Inline Year filter + chart view toggle
        col_top1, col_top2 = st.columns(2)
        with col_top1:
            year = st.selectbox(
                "YEAR",
                options=years,
                index=len(years) - 1,
                key="prov_yield_year",
            )
        with col_top2:
            view = st.radio("Chart View", ["Line", "Bar"], horizontal=True, key="prov_yield_view")

        # Build historical quarterly series
        quarterly = dl.get_quarterly_yield(df)
        hist = quarterly[quarterly["year"] == year].copy()
        if hist.empty:
            st.info("No data available for the selected year.")
            return

        # Build forecast series (next 4 quarters) from the backend forecast
        forecast_values = getattr(dr, "forecast_quarterly_yield", None)
        latest_q = quarterly.iloc[-1]
        forecast_q = pd.period_range(
            start=pd.Period(latest_q["date_q"], freq="Q") + 1,
            periods=4, freq="Q"
        )
        forecast_df = pd.DataFrame({
            "date_q": forecast_q.to_timestamp(),
            "year": [p.year for p in forecast_q],
            "quarter": [p.quarter for p in forecast_q],
            "quarter_label": ["Q{} {}".format(p.quarter, p.year) for p in forecast_q],
            "Type": "Forecast",
        })
        if forecast_values is not None and len(forecast_values) >= 4:
            forecast_df["quarterly_yield_mt_per_ha"] = forecast_values[:4]
        else:
            # Fallback: flat continuation of the selected year's average
            forecast_df["quarterly_yield_mt_per_ha"] = hist["quarterly_yield_mt_per_ha"].mean()

        hist_plot = hist.copy()
        hist_plot["Type"] = "Historical"

        # Two-column layout: chart (left, wider) + summary side-card (right)
        col_chart, col_summary = st.columns([3, 1.2], gap="medium")

        with col_chart:
            if view == "Bar":
                # Bar view: historical quarters for the selected year
                bar_data = hist_plot.copy()
                fig = px.bar(
                    bar_data, x="quarter_label", y="quarterly_yield_mt_per_ha",
                    color="quarterly_yield_mt_per_ha",
                    color_continuous_scale=["#C8E6C9", "#66BB6A", "#2E7D32"],
                    text=bar_data["quarterly_yield_mt_per_ha"].round(2),
                )
                fig.update_layout(
                    yaxis_title="MT/ha", xaxis_title="Quarter",
                    height=400, showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family=theme.FONT, size=12),
                    margin=dict(t=30, b=40, l=40, r=40),
                )
                fig.update_traces(textposition="outside")
            else:
                # Combine historical (selected year) + forecast into one figure
                plot_df = pd.concat([hist_plot, forecast_df], ignore_index=True)
                fig = go.Figure()
                hist_part = plot_df[plot_df["Type"] == "Historical"]
                fc_part = plot_df[plot_df["Type"] == "Forecast"]
                fig.add_trace(go.Scatter(
                    x=hist_part["quarter_label"], y=hist_part["quarterly_yield_mt_per_ha"],
                    mode="lines+markers", name="Historical",
                    line=dict(color=theme.HISTORICAL_COLOR, width=3), marker=dict(size=7)))
                fig.add_trace(go.Scatter(
                    x=fc_part["quarter_label"], y=fc_part["quarterly_yield_mt_per_ha"],
                    mode="lines+markers", name="Forecast",
                    line=dict(color=theme.FORECAST_COLOR, width=3, dash="dash"), marker=dict(size=7)))
                fig.update_layout(
                    yaxis_title="MT/ha",
                    height=400, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family=theme.FONT, size=12),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
                    margin=dict(t=30, b=40, l=40, r=40),
                )

            st.plotly_chart(fig, use_container_width=True, key=f"prov_yield_{year}_{view}")

        with col_summary:
            st.markdown("<br>", unsafe_allow_html=True)
            # Yield Insight Summary computations
            hist_avg = hist["quarterly_yield_mt_per_ha"].mean()
            forecast_avg = np.mean(forecast_df["quarterly_yield_mt_per_ha"])
            if hist_avg:
                percent_change = ((forecast_avg - hist_avg) / hist_avg) * 100
            else:
                percent_change = 0.0

            # Trend status label
            if percent_change > 5:
                risk = "Strong Increase"
                risk_color = "#2E7D32"
            elif percent_change > 1:
                risk = "Slight Increase"
                risk_color = "#66BB6A"
            elif percent_change < -5:
                risk = "Strong Decrease"
                risk_color = "#C62828"
            elif percent_change < -1:
                risk = "Slight Decrease"
                risk_color = "#FF9800"
            else:
                risk = "Stable"
                risk_color = "#FFC107"

            arrow = "↑" if percent_change > 0 else "↓" if percent_change < 0 else "→"
            forecast_year1 = forecast_df["year"].max()

            # Styled Yield Insight Summary Side-Card
            st.markdown(f"""
                <div style='
                    background-color: var(--background-color, #ffffff);
                    padding: 1rem 1.2rem;
                    border-radius: 12px;
                    border-left: 5px solid {risk_color};
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                    margin-top: 40px;
                '>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='font-size: 0.85rem; color: #666666; font-weight: 500; text-transform: uppercase;'>{risk}</span>
                        <span style='font-size: 1.3rem; font-weight: 800; color: {risk_color};'>{arrow} {percent_change:+.1f}%</span>
                    </div>
                    <div style='display: flex; justify-content: space-between; font-size: 0.85rem; border-top: 1px solid #f5f5f5; padding-top: 0.4rem;'>
                        <span style='color: #888888;'>{year} Avg:</span>
                        <span style='font-weight: 600; color: #333333;'>{hist_avg:.2f} MT/ha</span>
                    </div>
                    <div style='display: flex; justify-content: space-between; font-size: 0.85rem;'>
                        <span style='color: #888888;'>Forecast ({forecast_year1}):</span>
                        <span style='font-weight: 600; color: #333333;'>{forecast_avg:.2f} MT/ha</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def render(df, dr):
    """Main Provincial Analytics page with tabbed sub-views.

    Focuses on active price/yield analytics. The historical PRICE trend
    graph has been moved to historical_comparison.py (Tab 2), and the
    long-range yield trends have been moved to historical_comparison.py.
    Year and Palay Type filters are placed inline inside each card.
    """
    theme.page_title("Provincial Analytics",
                     "Provincial price and yield analytics for Bataan.")

    tab_price, tab_yield = st.tabs([
        "💰 Provincial Price",
        "🌱 Provincial Yield",
    ])

    with tab_price:
        _provincial_price_tab(df, dr)
    with tab_yield:
        _provincial_yield_tab(df, dr)
