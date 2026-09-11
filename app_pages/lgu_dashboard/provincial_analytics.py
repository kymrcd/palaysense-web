"""
PalaySense LGU Dashboard — Provincial Analytics
===============================================
Consolidates all provincial-level price and yield analytics into a single
page. Reuses the existing provincial price/yield charts and the historical
price/yield trend charts. Filters are limited to provincial data only
(Year + Palay Type Fancy/Regular).

Layout:
   • Production tab: Combo Bar+Line (harvested vs production) with slider + Quarterly Production bar
   • Yield tab: Bar with benchmark (Market/Government/None) + insight side-card
   • Price tab: Grouped bar Fancy vs Regular per YEAR (rounded edges)
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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

    with theme.section_card(title="Provincial Palay Price Trend Analysis",
                            desc="Fancy vs. Regular Palay (₱/kg).",
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

        # Bar graph (rounded edges) — requested replacement for line chart
        fig = go.Figure()
        if "Fancy" in palay_types:
            fig.add_trace(go.Bar(x=hist["date"], y=hist["fancy_palay_price"], name="Fancy Palay",
                                 marker_color="#10B981", marker_cornerradius=8,
                                 text=[f"₱{v:.2f}" if pd.notna(v) else "—" for v in hist["fancy_palay_price"]], textposition="outside",
                                 hovertemplate="%{x|%b %Y}<br>Fancy: ₱%{y:.2f}/kg<extra></extra>"))
        if "Regular" in palay_types:
            fig.add_trace(go.Bar(x=hist["date"], y=hist["other_variety_price"], name="Regular Palay",
                                 marker_color="#6366F1", marker_cornerradius=8,
                                 text=[f"₱{v:.2f}" if pd.notna(v) else "—" for v in hist["other_variety_price"]], textposition="outside",
                                 hovertemplate="%{x|%b %Y}<br>Regular: ₱%{y:.2f}/kg<extra></extra>"))

        fig.update_layout(
            yaxis_title="₱ / kg",
            height=380, barmode="group", bargap=0.28, bargroupgap=0.1,
            hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=11),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(family="Inter, sans-serif", size=10)),
            yaxis=dict(gridcolor="#F1F5F9", showgrid=True), xaxis=dict(gridcolor="#F1F5F9", showgrid=False),
            margin=dict(t=30, b=60, l=40, r=40),
            title="Monthly Price Comparison by Palay Variety" if len(fig.data) > 1 else None,
        )
        st.plotly_chart(fig, use_container_width=True, key=f"prov_price_{year}_{'_'.join(palay_types)}")


def _provincial_yield_tab(df, dr):
    years = dl.get_available_years(df)
    if not years:
        st.info("No year data available.")
        return

    with theme.section_card(title="Quarterly Crop Productivity & Yield Performance",
                            desc="Select a benchmark to see the target yield.",
                            icon_name="eco"):
        b_col1, b_col2 = st.columns([0.74, 0.26], vertical_alignment="center")
        with b_col1:
            try:
                _yield_benchmark = st.segmented_control("Benchmark / Reference Line:", options=["Government Target", "None"], key="prov_yield_benchmark", default="None")
                if _yield_benchmark is None: _yield_benchmark = "None"
            except Exception:
                _yield_benchmark = st.radio("Benchmark / Reference Line:", options=["Government Target", "None"], horizontal=True, key="prov_yield_benchmark")
            if _yield_benchmark in ("Target ng Gobyerno", "NFA / DA Policy Baseline", "DA Target (4.50 MT/ha)", "DA Target"): _yield_benchmark = "Government Target"
            elif _yield_benchmark in ("Wala", "Itago (None)", "Hide (None)"): _yield_benchmark = "None"
        with b_col2:
            with st.popover(":material/info: Benchmark Guide"):
                st.markdown("**Government Target:** DA **4.50 MT/ha** · **None:** no line")
        year = st.selectbox(
            "YEAR",
            options=years,
            index=len(years) - 1,
            key="prov_yield_year",
        )
        view = "Bar"

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
                    color_continuous_scale=["#C8E6C9", "#66BB6A", "#2E7D32"]
                )
                fig.update_layout(
                    yaxis_title="MT/ha", xaxis_title="Quarter",
                    height=280, showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family=theme.FONT, size=11),
                    margin=dict(t=20, b=30, l=40, r=20),
                )
                fig.update_traces(textposition="outside", marker_cornerradius=8)
                # Benchmark — apply dotted 4.50 / 10-yr avg
                try:
                    from .forecasting import _apply_benchmarks_to_fig
                    fig = _apply_benchmarks_to_fig(fig, hist, "yield", _yield_benchmark, provincial_df=df)
                except Exception:
                    pass
            else:
                # Combine historical (selected year) + forecast into one figure
                plot_df = pd.concat([hist_plot, forecast_df], ignore_index=True)
                fig = go.Figure()
                hist_part = plot_df[plot_df["Type"] == "Historical"]
                fc_part = plot_df[plot_df["Type"] == "Forecast"]
                fig.add_trace(go.Scatter(
                    x=hist_part["quarter_label"], y=hist_part["quarterly_yield_mt_per_ha"],
                    mode="lines+markers", name="Historical",
                    line=dict(color=theme.HISTORICAL_COLOR, width=2.5), marker=dict(size=6)))
                fig.add_trace(go.Scatter(
                    x=fc_part["quarter_label"], y=fc_part["quarterly_yield_mt_per_ha"],
                    mode="lines+markers", name="Forecast",
                    line=dict(color=theme.FORECAST_COLOR, width=2.5, dash="dash"), marker=dict(size=6)))
                fig.update_layout(
                    yaxis_title="MT/ha",
                    height=280, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family=theme.FONT, size=11),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
                    yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
                    margin=dict(t=20, b=30, l=40, r=20),
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

        # Quarterly Production & Top Municipalities now in Production tab


def _provincial_quarterly_production(df, year):
    """Moved from Overview — compact 280px bar + Insight card, single-year filter."""
    with theme.section_card(title="Provincial Quarterly Production",
                            desc="Production per quarter with high/low insight.",
                            icon_name="bar_chart"):
        if df is None or getattr(df, "empty", True) or "date" not in df.columns:
            st.info("No production data — no chart to display (0 values).")
            return
        prod = df.copy()
        prod["year"] = pd.to_datetime(prod["date"]).dt.year
        prod["quarter"] = pd.to_datetime(prod["date"]).dt.quarter
        sub = prod[prod["year"] == year] if year is not None else prod
        if sub.empty:
            st.info("No production data for the selected year.")
            return
        if "production_total" not in sub.columns:
            st.info("No production_total column available.")
            return
        q_avg = sub.groupby("quarter")["production_total"].mean().reset_index()
        q_avg["quarter"] = "Q" + q_avg["quarter"].astype(str)
        col1, col2 = st.columns([2.2, 1], gap="medium")
        with col1:
            fig = px.bar(q_avg, x="quarter", y="production_total", color="quarter",
                         labels={"quarter": "Quarter", "production_total": "Production (MT)"},
                         color_discrete_map={"Q1": "#FF9800", "Q2": "#C62828", "Q3": "#66BB6A", "Q4": "#FFB2C8"})
            fig.update_layout(yaxis_title="Production (MT)", xaxis_title="Quarter", showlegend=False,
                              plot_bgcolor="white", paper_bgcolor="white", font=dict(family=theme.FONT, size=12),
                              height=280, margin=dict(t=20, b=30, l=40, r=20),
                              xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#F3F4F6"))
            fig.update_traces(marker_line_width=0, marker_cornerradius=8)
            st.plotly_chart(fig, use_container_width=True, key=f"prov_yield_prod_q_{year}")
        with col2:
            if not q_avg.empty:
                highest = q_avg.loc[q_avg["production_total"].idxmax()]
                lowest = q_avg.loc[q_avg["production_total"].idxmin()]
                avg_p = q_avg["production_total"].mean()
                trend = ("increasing" if q_avg["production_total"].iloc[-1] > q_avg["production_total"].iloc[0] else "decreasing")
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem; border-radius:16px; border-left:6px solid #2E7D32; box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.90rem; line-height:1.6;">
                  <div style="font-size:0.95rem; font-weight:700; color:#1B5E20; margin-bottom:0.6rem;"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Production Insight Summary</div>
                  <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">emoji_events</i> Highest Production: <b style="color:#2E7D32;">{highest['quarter']}</b></div>
                  <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_down</i> Lowest Production: <b style="color:#C62828;">{lowest['quarter']}</b></div>
                  <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Average Production: <b>{avg_p:,.0f} MT</b></div>
                  <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
                  <div style="font-size:0.88rem; font-weight:600; color:#1B5E20;"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_up</i> Overall trend: <span style="color:#2E7D32; font-weight:700;">{trend.upper()}</span> pattern</div>
                </div>
                """, unsafe_allow_html=True)


def _provincial_top_municipalities(dr, year):
    """Moved from Overview — compact Top5 + seasonal pies, single-year (was year-range)."""
    with theme.section_card(title="Top Municipalities & Seasonal Distribution",
                            desc="Municipal production ranking and dry/wet season split.",
                            icon_name="leaderboard"):
        muni = getattr(dr, "municipal_production_df", None)
        if muni is None or getattr(muni, "empty", True):
            muni = getattr(dr, "municipality_history_df", None)
        # single-year -> pass (year, year) tuple to existing data_layer helper
        top5 = dl.get_top_5_producing_municipalities(muni, (year, year))
        if top5.empty:
            st.info("No municipality production data for the selected year.")
            return
        plot_top5 = top5.sort_values("palay_production")
        fig_top = px.bar(plot_top5, x="palay_production", y="municipality", orientation="h",
                         color="palay_production", color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
                         text=plot_top5["palay_production"].round(0).astype(int))
        fig_top.update_layout(title=f"Top 5 Municipalities by Total Production ({year})",
                              xaxis_title="Production (MT)", yaxis_title="Municipality",
                              showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                              height=300, margin=dict(t=20, b=30, l=40, r=20),
                              yaxis={"categoryorder": "total ascending"})
        fig_top.update_traces(texttemplate='%{text:,}', textposition='outside', marker_cornerradius=8)
        st.plotly_chart(fig_top, use_container_width=True, key=f"prov_yield_top5_{year}")
        dry = dl.get_municipal_seasonal_production(muni, (year, year), season="dry")
        wet = dl.get_municipal_seasonal_production(muni, (year, year), season="wet")
        col_a, col_b = st.columns(2)
        with col_a:
            if not dry.empty:
                fig = px.pie(dry, names="municipality", values="production", color_discrete_sequence=px.colors.sequential.Greens[0:5][::-1])
                fig.update_layout(height=260, margin=dict(t=20, b=30, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True, key=f"prov_yield_dry_{year}")
            else:
                st.info("No dry season data.")
        with col_b:
            if not wet.empty:
                fig = px.pie(wet, names="municipality", values="production", color_discrete_sequence=px.colors.sequential.Teal[0:5][::-1])
                fig.update_layout(height=260, margin=dict(t=20, b=30, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True, key=f"prov_yield_wet_{year}")
            else:
                st.info("No wet season data.")


def _historical_production_vs_area(df):
    """Single high-impact Combo Chart — Bar (harvested) + Dual Y-Axis Line (production). Replaces multi-select year tags."""
    if df is None or df.empty or "year" not in df.columns:
        st.info("No provincial production data.")
        return
    years = sorted(pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique().tolist())
    if not years:
        st.info("No year data.")
        return
    min_year, max_year = int(min(years)), int(max(years))
    # clamp default to 2015–2025 if within range
    def_min = max(min_year, 2015); def_max = min(max_year, 2025)
    if def_min > def_max: def_min, def_max = min_year, max_year

    with theme.section_card(title="Historical Palay Production Volume vs. Harvested Area", desc="Harvested area as bars (Gold) vs total production as line (Forest Green) — filter by year range.", icon_name="bar_chart"):
        sel_range = st.slider("Select Year Range", min_value=min_year, max_value=max_year, value=(def_min, def_max), key="prov_combo_year_slider")
        filtered = df[(df["year"] >= sel_range[0]) & (df["year"] <= sel_range[1])].copy()
        if filtered.empty:
            st.info("No data for selected range.")
            return
        # annual aggregates — harvested_total MUST be sum (not mean) to get ~80k ha
        agg = filtered.groupby("year").agg({"harvested_total":"sum", "production_total":"sum"}).reset_index() if "harvested_total" in filtered.columns and "production_total" in filtered.columns else pd.DataFrame()
        if agg.empty or "harvested_total" not in agg.columns or "production_total" not in agg.columns:
            st.info("Required columns harvested_total / production_total not found.")
            return
        agg = agg.sort_values("year")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=agg["year"], y=agg["harvested_total"], name="Harvested Area", marker_color="#F59E0B", marker_line_width=0, hovertemplate="Year %{x}<br>Harvested: %{y:,.2f} ha<extra></extra>", text=[f"{int(round(float(v))):,}" if pd.notna(v) else "—" for v in agg["harvested_total"]], textposition="outside", textfont=dict(size=10, family="Inter, sans-serif", color="#92400E"), marker_cornerradius=8), secondary_y=False)
        fig.add_trace(go.Scatter(x=agg["year"], y=agg["production_total"], name="Total Production", mode="lines+markers", line=dict(color="#15803D", width=3), marker=dict(size=8, color="#15803D", line=dict(width=1, color="white")), hovertemplate="Year %{x}<br>Production: %{y:,.2f} MT<extra></extra>"), secondary_y=True)
        fig.update_layout(height=380, margin=dict(l=14,r=14,t=80,b=40), title=dict(text="Historical Palay Production Volume vs. Harvested Area", font=dict(family="Inter, sans-serif", size=14, color="#1F2937"), x=0.5, xanchor="center"), legend=dict(orientation="h", yanchor="bottom", y=0.98, xanchor="center", x=0.5, font=dict(family="Inter, sans-serif", size=11)), hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter, sans-serif", size=11), bargap=0.35)
        fig.update_xaxes(title_text=None, tickmode="linear", dtick=1, gridcolor="#F1F5F9", showgrid=False)
        fig.update_yaxes(title_text="Harvested Area (Hectares)", secondary_y=False, gridcolor="#F1F5F9", showgrid=True, tickformat=",", rangemode="tozero")
        fig.update_yaxes(title_text="Total Production (Metric Tons)", secondary_y=True, showgrid=False, tickformat=",")
        st.plotly_chart(fig, use_container_width=True, key=f"prov_combo_{sel_range[0]}_{sel_range[1]}")


def _production_tab(df, dr):
    """Production tab — combo + quarterly production for OPA historical supply view."""
    _historical_production_vs_area(df)
    # Yearly quarterly production needs a YEAR selector (separate from Yield tab)
    years = dl.get_available_years(df)
    if not years:
        return
    year = st.selectbox("YEAR", options=years, index=len(years)-1, key="prov_prod_year")
    _provincial_quarterly_production(df, year)


def render(df, dr):
    """Main Provincial Analytics page with tabbed sub-views.

    Focuses on active price/yield analytics. The historical PRICE trend
    graph has been moved to historical_comparison.py (Tab 2), and the
    long-range yield trends have been moved to historical_comparison.py.
    Year and Palay Type filters are placed inline inside each card.
    """
    if dr is None or not getattr(dr, "has_provincial_data", False):
        st.info("No provincial data — provincial analytics hidden (0 values). Upload data via Import Data.")
        return
    theme.page_title("Provincial Analytics",
                     "Provincial price and yield analytics for Bataan.")

    tab_prod, tab_yield, tab_price = st.tabs([
        ":material/inventory_2: Production",
        ":material/eco: Yield",
        ":material/payments: Price",
    ])

    with tab_prod:
        _production_tab(df, dr)
    with tab_yield:
        _provincial_yield_tab(df, dr)
    with tab_price:
        _provincial_price_tab(df, dr)
