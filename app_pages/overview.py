import streamlit as st
import pandas as pd
import plotly.express as px

try:
    from data.Dashboard_Ready import (
        provincial_df,
        forecast_3months_fancy,
        forecast_variety_3months,
        forecast_quarterly_yield,
        municipality_df
    )
except ModuleNotFoundError:
    from data.Dashboard_Ready import (
        provincial_df,
        forecast_3months_fancy,
        forecast_variety_3months,
        forecast_quarterly_yield,
        municipality_df
    )


def overview_page():
    """
    Renders an accessible, farmer-centric agricultural dashboard for Bataan.
    Supports multi-year selections, 'All' municipality views, and Ecosystem toggle filters.
    """

    # ========================================================
    # DATA PROCESSING & TEMPORAL MAPPING
    # ========================================================
    provincial_df["date"] = pd.to_datetime(provincial_df["date"])
    provincial_sorted = provincial_df.sort_values("date").copy()

    df = provincial_sorted.copy()
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter

    latest_year = df["year"].max()
    provincial_latest = df[df["year"] == latest_year].copy().sort_values("date")
    latest = provincial_latest.iloc[-1]

    # Quick backup conversion for municipality data
    municipality_df["date"] = pd.to_datetime(municipality_df["date"])
    muni = municipality_df.copy()
    muni["year"] = muni["date"].dt.year

    # ========================================================
    # NEW FILTERS: MULTI-YEAR, ALL-MUNIS, & ECOSYSTEM INFO
    # ========================================================
    st.sidebar.markdown("### 🌾 Dashboard Controls")

    # 1. ECOSYSTEM FILTER (Irrigated vs Seasonal/Rainfed)
    eco_options = ["All Types", "Water-Irrigated", "Rainfed / Seasonal"]
    selected_eco = st.sidebar.radio("💧 Farm Ecosystem Type:", eco_options, key="sidebar_eco")

    # 2. MULTI-SELECT YEAR FILTER (Allows choosing 1, 2, or more years at once)
    available_years = sorted(list(df["year"].unique()), reverse=True)
    selected_years = st.sidebar.multiselect(
        "📅 Select Data Years:",
        options=available_years,
        default=[available_years[0]],
        key="sidebar_years"
    )

    # 3. MUNICIPALITY SELECTOR (With an "All Municipalities" option)
    all_munis_options = ["All Municipalities"] + sorted(list(muni["municipality"].unique()))
    selected_muni = st.sidebar.selectbox("📍 Select Town / City:", all_munis_options, key="sidebar_muni")

    # ========================================================
    # DYNAMIC DATA FILTERING LOGIC
    # ========================================================
    target_column = "ecosystem"

    if target_column in muni.columns and selected_eco != "All Types":
        mapped_value = "Irrigated" if selected_eco == "Water-Irrigated" else "Rainfed"
        muni = muni[muni[target_column].str.contains(mapped_value, case=False, na=False)]
        if target_column in df.columns:
            df = df[df[target_column].str.contains(mapped_value, case=False, na=False)]

    # Filter Dataframes based on Selected Years
    if selected_years:
        provincial_year = df[df["year"].isin(selected_years)].copy().sort_values("date")
        muni_filtered = muni[muni["year"].isin(selected_years)]
    else:
        provincial_year = df[df["year"] == available_years[0]].copy().sort_values("date")
        muni_filtered = muni[muni["year"] == available_years[0]]

    # Filter based on Municipality Selection ("All" vs Specific)
    if selected_muni != "All Municipalities":
        muni_filtered = muni_filtered[muni_filtered["municipality"] == selected_muni]

    # ========================================================
    # METRIC GENERATION & VARIANCE CALCULATIONS
    # ========================================================
    if not provincial_year.empty:
        latest_selected = provincial_year.iloc[-1]

        avg_fancy_price = provincial_year["fancy_palay_price"].mean()
        avg_regular_price = provincial_year["other_variety_price"].mean()
        latest_production = provincial_year.groupby("year")["production_total"].sum().mean()

        forecast_months = pd.date_range(
            start=latest_selected["date"] + pd.DateOffset(months=1),
            periods=3,
            freq="MS"
        )
        next_month_name = forecast_months[0].strftime("%B %Y")

        percent_change_fancy = ((forecast_3months_fancy[0] - avg_fancy_price) / avg_fancy_price) * 100
        percent_change_regular = ((forecast_variety_3months[0] - avg_regular_price) / avg_regular_price) * 100
        avg_yield_forecast = sum(forecast_quarterly_yield) / len(forecast_quarterly_yield)
    else:
        latest_production, percent_change_fancy, percent_change_regular, avg_yield_forecast = 0, 0, 0, 0
        next_month_name = "N/A"

    next_fancy_pred = forecast_3months_fancy[0]
    next_regular_pred = forecast_variety_3months[0]

    # ========================================================
    # CHART GENERATION SETUP
    # ========================================================
    historical_yield = (
        provincial_year
        .groupby("quarter")["quarterly_yield_mt_per_ha"]
        .mean()
        .reset_index()
    )
    historical_yield["Quarter"] = "Q" + historical_yield["quarter"].astype(str)
    historical_yield["Yield"] = historical_yield["quarterly_yield_mt_per_ha"]
    historical_yield["Type"] = "Past Records (Historical)"

    forecast_yield = pd.DataFrame({
        "Quarter": [f"Q{i}" for i in range(1, len(forecast_quarterly_yield) + 1)],
        "Yield": forecast_quarterly_yield,
        "Type": "System Prediction (Forecast)"
    })
    yield_chart_df = pd.concat([historical_yield[["Quarter", "Yield", "Type"]], forecast_yield])

    future_months = pd.date_range(start=latest["date"] + pd.DateOffset(months=1), periods=len(forecast_3months_fancy),
                                  freq="MS")
    price_df = pd.DataFrame({
        "Month": future_months.strftime("%b %Y"),
        "Fancy Palay": forecast_3months_fancy,
        "Regular Palay": forecast_variety_3months
    })
    price_long = price_df.melt(id_vars="Month", value_vars=["Fancy Palay", "Regular Palay"], var_name="Palay Variety",
                               value_name="Price (₱/kg)")

    top5 = muni_filtered.groupby("municipality")["palay_production"].sum().reset_index().sort_values(
        by="palay_production", ascending=True).tail(5)

    if not muni_filtered.empty:
        prod_val = muni_filtered["palay_production"].sum()
    else:
        prod_val = 0

    # ========================================================
    # FRONT-END CSS STYLING
    # ========================================================
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght=400;500;600;700;800&display=swap');
        .main-container { font-family: 'Poppins', sans-serif; padding: 5px 1%; }
        .hero-banner {
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
            padding: 30px; border-radius: 16px; color: white; margin-bottom: 25px;
            box-shadow: 0 8px 20px rgba(27,94,32,0.1);
        }
        .hero-title { font-size: clamp(1.6rem, 2.5vw, 2.2rem); font-weight: 800; margin-bottom: 6px; }
        .hero-subtitle { font-size: 1rem; opacity: 0.92; line-height: 1.5; }
        .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .metric-card { background: #FFFFFF; padding: 18px; border-radius: 14px; border: 1px solid #E5E7EB; display: flex; flex-direction: column; justify-content: space-between; }
        .metric-card-header { display: flex; justify-content: space-between; align-items: center; }
        .metric-title { font-size: 0.85rem; font-weight: 700; color: #4B5563; }
        .metric-data { font-size: 1.6rem; font-weight: 800; color: #1B5E20; margin: 8px 0 3px 0; }
        .metric-footer { font-size: 0.75rem; color: #9CA3AF; }
        .component-card { background: #FFFFFF; border-radius: 14px; border: 1px solid #E5E7EB; padding: 20px; margin-bottom: 20px; }
        .component-title-row { display: flex; justify-content: space-between; align-items: center; }
        .component-header { font-size: 1.1rem; font-weight: 700; color: #111827; }
        .component-desc { font-size: 0.82rem; color: #6B7280; margin-bottom: 15px; }

        /* ADVISORY STRUCTURE SYSTEM */
        .advisory-container { display: flex; flex-direction: column; gap: 12px; width: 100%; margin-top: 5px; }
        .advisory-card { display: flex; align-items: flex-start; padding: 14px 18px; border-radius: 10px; background-color: #FFFFFF; border: 1px solid #E5E7EB; }
        .card-status { border-left: 5px solid #0284C7; background-color: #F0F9FF; }
        .card-marketing { border-left: 5px solid #16A34A; background-color: #F0FDF4; }
        .card-notice { border-left: 5px solid #EA580C; background-color: #FFF7ED; }
        .card-optimization { border: 2px dashed #16A34A; background-color: #F4FBF7; }
        .card-icon { font-size: 1.25rem; margin-right: 12px; margin-top: 1px; }
        .card-body { flex: 1; font-size: 0.9rem; line-height: 1.5; color: #374151; }
        .card-label { font-weight: 700; margin-right: 4px; }
        .label-status { color: #0369A1; }
        .label-marketing { color: #15803D; }
        .label-notice { color: #C2410C; }
        .label-optimization { color: #15803D; }
        .highlight-text { font-weight: 700; color: #111827; }
    </style>
    """, unsafe_allow_html=True)

    # ========================================================
    # LAYOUT RENDERING INTERFACE
    # ========================================================
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-title">Bataan Rice Monitoring & Prediction Assistant</div>
        <div class="hero-subtitle">
            Showing records for ecosystem: <b>{selected_eco}</b> across selected periods. Filter or compare multiple parameters on the sidebar layout.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI Row
    st.markdown(f"""
    <div class="kpi-row">
        <div class="metric-card">
            <div class="metric-card-header"><div class="metric-title">Expected Yield Target</div></div>
            <div class="metric-data">{avg_yield_forecast:.2f} MT/ha</div>
            <div class="metric-footer">Target weight per hectare this cycle</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-header"><div class="metric-title">Fancy Price Trend</div></div>
            <div class="metric-data">{percent_change_fancy:+.1f}%</div>
            <div class="metric-footer">Forecast for: {next_month_name}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-header"><div class="metric-title">Regular Price Trend</div></div>
            <div class="metric-data">{percent_change_regular:+.1f}%</div>
            <div class="metric-footer">Forecast for: {next_month_name}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-header"><div class="metric-title">Total Active Filter Volume</div></div>
            <div class="metric-data">{prod_val:,.0f} MT</div>
            <div class="metric-footer">Total mass production calculated</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Plots Row 1
    chart_row1_col1, chart_row1_col2 = st.columns(2)

    with chart_row1_col1:
        st.markdown(
            '<div class="component-card"><div class="component-header">Yield Production Curves</div><div class="component-desc">Evaluating past harvest weights relative to algorithmic prediction goals.</div>',
            unsafe_allow_html=True)
        fig_yield = px.line(yield_chart_df, x="Quarter", y="Yield", color="Type", markers=True,
                            color_discrete_sequence=["#7B1FA2", "#2E7D32"])
        fig_yield.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title="MT/ha",
                                legend=dict(orientation="h", y=-0.25, x=0), plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_yield, use_container_width=True, key="yield_overview_fig")
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_row1_col2:
        st.markdown(
            '<div class="component-card"><div class="component-header">3-Month Strategic Buying Projections</div><div class="component-desc">Forecast values highlighting optimal trading months.</div>',
            unsafe_allow_html=True)
        fig_price = px.line(price_long, x="Month", y="Price (₱/kg)", color="Palay Variety", markers=True,
                            color_discrete_sequence=["#FFB300", "#1B5E20"])
        fig_price.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title="₱/kg",
                                legend=dict(orientation="h", y=-0.25, x=0), plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_price, use_container_width=True, key="price_overview_fig")
        st.markdown("</div>", unsafe_allow_html=True)

    # Data Row 2 (Ranking & Smart Cards)
    chart_row2_col1, chart_row2_col2 = st.columns(2)

    with chart_row2_col1:
        st.markdown(
            '<div class="component-card"><div class="component-header">Regional Production Rankings</div><div class="component-desc">Capacities tracked across active selection fields.</div>',
            unsafe_allow_html=True)
        if not top5.empty:
            fig_top5 = px.bar(top5, x="palay_production", y="municipality", orientation="h",
                              color_discrete_sequence=["#2E7D32"])
            fig_top5.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Metric Tons",
                                   yaxis_title=None, showlegend=False, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_top5, use_container_width=True, key="top5_overview_fig")
        else:
            st.info("No matching data entries found to build bar graphs.")
        st.markdown("</div>", unsafe_allow_html=True)

    # SMART FARMER CARDS INTERACTION VIEW
    with chart_row2_col2:
        st.markdown(f"""
        <div class="component-card">
            <div class="component-header">Smart Agricultural Advisories</div>
            <div class="component-desc">Live operational recommendations for <b>{selected_muni}</b>.</div>
        """, unsafe_allow_html=True)

        display_muni_name = "All Bataan Municipalities" if selected_muni == "All Municipalities" else selected_muni
        display_year_string = ", ".join(map(str, selected_years)) if selected_years else "Selected Years"

        if not muni_filtered.empty:
            eco_msg = "⚠️ Rainfed setups should maximize water-retention fields and sync planting timelines with historical rainy quarters." if selected_eco == "Rainfed / Seasonal" else "✅ Water-Irrigated setups can securely aim for high-input Fancy Varieties due to reliable water schedules."

            
            html_cards = f"""
<div class="advisory-container">
<div class="advisory-card card-status">
<div class="card-icon">📍</div>
<div class="card-body">
<span class="card-label label-status">Ecosystem Scope ({selected_eco}):</span>
Total output volume records captured for <span class="highlight-text">{display_muni_name}</span> across <span class="highlight-text">{display_year_string}</span> equals <span class="highlight-text">{prod_val:,.1f} MT</span>.
</div>
</div>
<div class="advisory-card card-marketing">
<div class="card-icon">💡</div>
<div class="card-body">
<span class="card-label label-marketing">Trading Target Advisory:</span>
Predictions indicate Premium Fancy varieties are heading toward <span class="highlight-text">₱{next_fancy_pred:.2f}/kg</span> next month, while regular commercial grades stabilize near <span class="highlight-text">₱{next_regular_pred:.2f}/kg</span>.
</div>
</div>
<div class="advisory-card card-optimization">
<div class="card-icon">💧</div>
<div class="card-body">
<span class="card-label label-optimization">Ecosystem Recommendation:</span>
{eco_msg}
</div>
</div>
</div>
"""
            st.markdown(html_cards, unsafe_allow_html=True)
        else:
            st.warning(f"No active metrics found matching your current dashboard filter selections.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
