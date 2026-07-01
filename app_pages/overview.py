import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

    # =========================
    # HISTORICAL QUARTERLY DATA
    # =========================
    quarterly_df = (
        df.groupby(["year", "quarter"])["quarterly_yield_mt_per_ha"]
        .mean()
        .reset_index()
    )

    quarterly_df["date_q"] = pd.PeriodIndex(
        quarterly_df["year"].astype(str) + "Q" + quarterly_df["quarter"].astype(str),
        freq="Q"
    ).to_timestamp()

    quarterly_df["quarter_label"] = (
            "Q" + quarterly_df["quarter"].astype(str) +
            " " + quarterly_df["year"].astype(str)
    )

    quarterly_df["Type"] = "Historical"
    quarterly_df = quarterly_df.sort_values("date_q")

    # =========================
    # FORECAST PREPARATION
    # =========================
    latest_q = quarterly_df.iloc[-1]

    forecast_quarters = pd.period_range(
        start=pd.Period(latest_q["date_q"], freq="Q") + 1,
        periods=4,
        freq="Q"
    )

    # Forecast reference year
    forecast_year1 = forecast_quarters[-1].year

    forecast_df = pd.DataFrame({
        "date_q": forecast_quarters.to_timestamp()
    })

    forecast_df["year"] = forecast_df["date_q"].dt.year
    forecast_df["quarter"] = forecast_df["date_q"].dt.quarter

    forecast_df["quarter_label"] = (
            "Q" + forecast_df["quarter"].astype(str) +
            " " + forecast_df["year"].astype(str)
    )

    forecast_df["quarterly_yield_mt_per_ha"] = forecast_quarterly_yield
    forecast_df["Type"] = "Forecast"

    # ========================================================
    # NEW FILTERS: MULTI-YEAR, ALL-MUNIS, & ECOSYSTEM INFO
    # ========================================================
    st.sidebar.markdown("""
    <style>
        .sidebar-header {
            font-family: 'Poppins', sans-serif;
            font-weight: 700;
            font-size: 1.1rem;
            color: #2E7D32;
            padding: 10px 0 5px 0;
            border-bottom: 2px solid #E8F5E9;
            margin-bottom: 15px;
        }
        .filter-label {
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            font-size: 0.85rem;
            color: #1B5E20;
            margin: 10px 0 5px 0;
        }
        .radio-label {
            font-family: 'Poppins', sans-serif;
            font-size: 0.8rem;
            color: #4B5563;
            font-weight: 500;
        }
    </style>
    <div class="sidebar-header">🌾 Dashboard Controls</div>
    """, unsafe_allow_html=True)

    # 1. ECOSYSTEM FILTER (Irrigated vs Seasonal/Rainfed)
    st.sidebar.markdown('<div class="filter-label">💧 Farm Ecosystem Type</div>', unsafe_allow_html=True)
    eco_options = ["All Types", "Water-Irrigated", "Rainfed / Seasonal"]
    selected_eco = st.sidebar.radio(
        "",
        eco_options,
        key="sidebar_eco",
        label_visibility="collapsed"
    )

    # 2. MULTI-SELECT YEAR FILTER
    st.sidebar.markdown('<div class="filter-label">📅 Select Data Years</div>', unsafe_allow_html=True)
    available_years = sorted(list(df["year"].unique()), reverse=True)
    selected_years = st.sidebar.multiselect(
        "",
        options=available_years,
        default=[available_years[0]],
        key="sidebar_years",
        label_visibility="collapsed"
    )

    # 3. MULTI-SELECT MUNICIPALITY FILTER
    st.sidebar.markdown('<div class="filter-label">📍 Select Town / City</div>', unsafe_allow_html=True)
    all_munis_options = sorted(muni["municipality"].unique())

    selected_munis = st.sidebar.multiselect(
        "",
        options=all_munis_options,
        default=all_munis_options,
        key="sidebar_munis",
        label_visibility="collapsed"
    )

    # If a specific municipality is selected together with "All Municipalities",
    # remove "All Municipalities"
    if "All Municipalities" in selected_munis and len(selected_munis) > 1:
        selected_munis.remove("All Municipalities")

    # ========================================================
    # DYNAMIC DATA FILTERING LOGIC
    # ========================================================
    target_column = "ecosystem"

    if target_column in muni.columns and selected_eco != "All Types":
        mapped_value = (
            "Irrigated"
            if selected_eco == "Water-Irrigated"
            else "Rainfed"
        )

        muni = muni[
            muni[target_column].str.contains(
                mapped_value,
                case=False,
                na=False
            )
        ]

        if target_column in df.columns:
            df = df[
                df[target_column].str.contains(
                    mapped_value,
                    case=False,
                    na=False
                )
            ]

    # Filter by Year
    if selected_years:
        provincial_year = (
            df[df["year"].isin(selected_years)]
            .copy()
            .sort_values("date")
        )

        muni_filtered = muni[
            muni["year"].isin(selected_years)
        ]

    else:
        provincial_year = (
            df[df["year"] == available_years[0]]
            .copy()
            .sort_values("date")
        )

        muni_filtered = muni[
            muni["year"] == available_years[0]
            ]

    # Filter by Municipality
    if selected_munis:
        muni_filtered = muni_filtered[
            muni_filtered["municipality"].isin(selected_munis)
        ]
    else:
        muni_filtered = muni_filtered.iloc[0:0]

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
    historical_yield["Type"] = "Past Records"

    forecast_yield = pd.DataFrame({
        "Quarter": [f"Q{i}" for i in range(1, len(forecast_quarterly_yield) + 1)],
        "Yield": forecast_quarterly_yield,
        "Type": "Forecast"
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

    municipality_production = (
        muni_filtered
        .groupby("municipality")["palay_production"]
        .sum()
        .reset_index()
        .sort_values(by="palay_production", ascending=True)
    )

    if not muni_filtered.empty:
        prod_val = muni_filtered["palay_production"].sum()
    else:
        prod_val = 0

    # ========================================================
    # FRONT-END CSS
    # ========================================================
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');

        /* Main Container */
        .main-container { 
            font-family: 'Poppins', sans-serif; 
            padding: 0 1% 20px 1%; 
            background: #F8FAF9;
        }

        /* Hero Banner - Modern Gradient */
        .hero-banner {
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 40%, #388E3C 100%);
            padding: 35px 40px;
            border-radius: 20px;
            color: white;
            margin-bottom: 28px;
            box-shadow: 0 12px 35px rgba(27, 94, 32, 0.2);
            position: relative;
            overflow: hidden;
        }
        .hero-banner::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 50%;
        }
        .hero-banner::after {
            content: '🌾';
            position: absolute;
            bottom: 10px;
            right: 30px;
            font-size: 80px;
            opacity: 0.1;
        }
        .hero-title { 
            font-size: clamp(1.8rem, 2.8vw, 2.5rem); 
            font-weight: 900; 
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        .hero-subtitle { 
            font-size: 1rem; 
            opacity: 0.92; 
            line-height: 1.6;
            font-weight: 400;
        }
        .hero-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.15);
            padding: 4px 16px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 8px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* KPI Cards - Glassmorphism */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }
        .metric-card {
            background: #FFFFFF;
            padding: 20px 22px;
            border-radius: 16px;
            border: 1px solid rgba(46, 125, 50, 0.08);
            position: relative;
            overflow: hidden;
        }
        .metric-card:hover {
            border-color: rgba(46, 125, 50, 0.2);
        }
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #2E7D32, #66BB6A);
        }
        .metric-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .metric-title { 
            font-size: 0.8rem; 
            font-weight: 600; 
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-icon {
            font-size: 1.2rem;
            opacity: 0.7;
        }
        .metric-data { 
            font-size: 1.8rem; 
            font-weight: 800; 
            color: #1B5E20;
            margin: 4px 0 2px 0;
            letter-spacing: -0.5px;
        }
        .metric-footer { 
            font-size: 0.7rem; 
            color: #9CA3AF;
            font-weight: 500;
        }
        .metric-change-positive {
            color: #16A34A;
            font-weight: 700;
        }
        .metric-change-negative {
            color: #DC2626;
            font-weight: 700;
        }

        /* Component Cards - Clean Design */
        .component-card {
            background: #FFFFFF;
            border-radius: 16px;
            border: 1px solid rgba(0, 0, 0, 0.05);
            padding: 22px 24px 24px 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
        }
        .component-card:hover {
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
        }
        .component-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        .component-header {
            font-size: 1.05rem;
            font-weight: 700;
            color: #111827;
        }
        .component-header-icon {
            font-size: 1.1rem;
            margin-right: 8px;
        }
        .component-desc {
            font-size: 0.8rem;
            color: #6B7280;
            margin-bottom: 16px;
            font-weight: 400;
        }

        /* Advisory Cards - Enhanced */
        .advisory-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            width: 100%;
            margin-top: 4px;
        }
        .advisory-card {
            display: flex;
            align-items: flex-start;
            padding: 16px 20px;
            border-radius: 12px;
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
        }
        .advisory-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        .card-status {
            border-left: 4px solid #0284C7;
            background: linear-gradient(135deg, #F0F9FF 0%, #FFFFFF 100%);
        }
        .card-marketing {
            border-left: 4px solid #16A34A;
            background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%);
        }
        .card-notice {
            border-left: 4px solid #EA580C;
            background: linear-gradient(135deg, #FFF7ED 0%, #FFFFFF 100%);
        }
        .card-optimization {
            border-left: 4px solid #7C3AED;
            background: linear-gradient(135deg, #F5F3FF 0%, #FFFFFF 100%);
        }
        .card-icon {
            font-size: 1.2rem;
            margin-right: 14px;
            margin-top: 2px;
        }
        .card-body {
            flex: 1;
            font-size: 0.88rem;
            line-height: 1.6;
            color: #374151;
        }
        .card-label {
            font-weight: 700;
            margin-right: 4px;
        }
        .label-status { color: #0369A1; }
        .label-marketing { color: #15803D; }
        .label-notice { color: #C2410C; }
        .label-optimization { color: #6D28D9; }
        .highlight-text {
            font-weight: 700;
            color: #1B5E20;
            background: rgba(27, 94, 32, 0.06);
            padding: 1px 6px;
            border-radius: 4px;
        }

        /* Custom Streamlit Overrides */
        .stSelectbox, .stMultiSelect {
            font-family: 'Poppins', sans-serif;
        }
        .stRadio > div {
            gap: 8px;
        }
        .stRadio label {
            font-family: 'Poppins', sans-serif;
            font-size: 0.85rem;
            padding: 6px 12px;
            border-radius: 8px;
            background: #F3F4F6;
        }
        .stRadio label:hover {
            background: #E8F5E9;
        }
        .stRadio [data-baseweb="radio"] {
            margin-right: 6px;
        }

        /* Sidebar enhancements */
        .css-1d391kg {
            background: #F8FAF9;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .hero-banner {
                padding: 24px 20px;
            }
            .metric-card {
                padding: 16px 18px;
            }
            .component-card {
                padding: 16px 18px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # ========================================================
    # LAYOUT RENDERING INTERFACE
    # ========================================================
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    # Hero Banner
    eco_display = "All Types" if selected_eco == "All Types" else selected_eco
    year_display = ", ".join(map(str, selected_years)) if selected_years else "All Years"

    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-title"> Bataan Rice Monitoring & Prediction</div>
        <div class="hero-subtitle">
            Data-driven insights for smarter farming decisions • 
            <strong>{eco_display}</strong> ecosystem • 
            <strong>{year_display}</strong>
        </div>
        <span class="hero-badge">📊 Live Dashboard • {len(selected_munis) if selected_munis else 0} municipalities selected</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI Row
    # Determine color classes for changes
    fancy_color = "metric-change-positive" if percent_change_fancy >= 0 else "metric-change-negative"
    regular_color = "metric-change-positive" if percent_change_regular >= 0 else "metric-change-negative"
    fancy_arrow = "↑" if percent_change_fancy >= 0 else "↓"
    regular_arrow = "↑" if percent_change_regular >= 0 else "↓"

    st.markdown(f"""
    <div class="kpi-row">
        <div class="metric-card">
            <div class="metric-card-header">
                <div class="metric-title">🎯 Expected Yield</div>
            </div>
            <div class="metric-data">{avg_yield_forecast:.2f} MT/ha</div>
            <div class="metric-footer">Target weight per hectare this cycle</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-header">
                <div class="metric-title">⭐ Fancy Price Trend</div>
            </div>
            <div class="metric-data {fancy_color}">{fancy_arrow} {abs(percent_change_fancy):.1f}%</div>
            <div class="metric-footer">Forecast for: {next_month_name}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-header">
                <div class="metric-title">📦 Regular Price Trend</div>
            </div>
            <div class="metric-data {regular_color}">{regular_arrow} {abs(percent_change_regular):.1f}%</div>
            <div class="metric-footer">Forecast for: {next_month_name}</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-header">
                <div class="metric-title">🏭 Total Production</div>
            </div>
            <div class="metric-data">{prod_val:,.0f} MT</div>
            <div class="metric-footer">Across selected municipalities</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Plots Row 1
    chart_row1_col1, chart_row1_col2 = st.columns(2, gap="medium")

    with chart_row1_col1:
        st.markdown(
            '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon">📈</span>Yield Production Curves</span></div><div class="component-desc">Historical harvest performance vs. AI-powered quarterly forecasts</div>',
            unsafe_allow_html=True)

        # ===========================
        # ONE YEAR SELECTED
        # ===========================
        if len(selected_years) == 1:

            year = selected_years[0]

            hist_df = quarterly_df[
                quarterly_df["year"] == year
                ]

            plot_df = pd.concat([hist_df, forecast_df])

            fig = px.line(
                plot_df,
                x="quarter_label",
                y="quarterly_yield_mt_per_ha",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": "#7C3AED",
                    "Forecast": "#2E7D32",
                },
                line_shape="spline"
            )

            fig.update_traces(
                marker=dict(
                    size=8,
                    line=dict(width=2, color="white")
                ),
                line=dict(width=3)
            )

            fig.update_traces(
                selector=dict(name="Forecast"),
                line=dict(
                    dash="dash",
                    width=3
                )
            )

            fig.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=None,
                yaxis_title="MT/ha",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.40,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11, family="Poppins")
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified"
            )

            fig.update_xaxes(
                gridcolor="#F3F4F6",
                showgrid=True
            )

            fig.update_yaxes(
                gridcolor="#F3F4F6",
                showgrid=True
            )

        # ===========================
        # MULTIPLE YEARS
        # ===========================
        else:

            historical_avg = (
                quarterly_df[
                    quarterly_df["year"].isin(selected_years)
                ]
                .groupby("year")["quarterly_yield_mt_per_ha"]
                .mean()
                .reset_index()
            )

            historical_avg["Type"] = "Historical"

            forecast_avg = (
                forecast_df
                .groupby("year")["quarterly_yield_mt_per_ha"]
                .mean()
                .reset_index()
            )

            forecast_avg["Type"] = "Forecast"

            yearly_avg = pd.concat([
                historical_avg,
                forecast_avg
            ])

            fig = px.line(
                yearly_avg,
                x="year",
                y="quarterly_yield_mt_per_ha",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": "#7C3AED",
                    "Forecast": "#2E7D32",
                },
                line_shape="spline"
            )

            fig.update_traces(
                marker=dict(
                    size=8,
                    line=dict(width=2, color="white")
                ),
                line=dict(width=3)
            )

            fig.update_traces(
                selector=dict(name="Forecast"),
                line=dict(
                    dash="dash",
                    width=3
                )
            )

            fig.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=None,
                yaxis_title="Average Yield (MT/ha)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y= -0.40,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11, family="Poppins")
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified"
            )

            fig.update_xaxes(
                gridcolor="#F3F4F6",
                showgrid=True
            )

            fig.update_yaxes(
                gridcolor="#F3F4F6",
                showgrid=True
            )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with chart_row1_col2:
        st.markdown(
            '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon">📊</span>3-Month Price Forecast</span></div><div class="component-desc">Strategic buying & selling windows for optimal returns</div>',
            unsafe_allow_html=True)

        # Enhanced price chart
        fig_price = px.line(
            price_long,
            x="Month",
            y="Price (₱/kg)",
            color="Palay Variety",
            markers=True,
            color_discrete_sequence=["#F59E0B", "#1B5E20"],
            line_shape="spline"
        )
        fig_price.update_traces(
            marker=dict(size=8, line=dict(width=2, color='white')),
            line=dict(width=3)
        )

        fig_price.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=None,
            yaxis_title="₱/kg",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.40,
                xanchor="center",
                x=0.5,
                font=dict(size=11, family="Poppins")
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="x unified"
        )
        fig_price.update_xaxes(gridcolor="#F3F4F6", showgrid=True)
        fig_price.update_yaxes(gridcolor="#F3F4F6", showgrid=True)
        st.plotly_chart(fig_price, use_container_width=True, key="price_overview_fig")
        st.markdown("</div>", unsafe_allow_html=True)

    # Data Row 2 (Ranking & Smart Cards)
    chart_row2_col1, chart_row2_col2 = st.columns([2.90,2])

    with chart_row2_col1:
        st.markdown(
            '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon">🏆</span>Municipal Production Rankings</span></div><div class="component-desc">Capacity comparison across active municipalities</div>',
            unsafe_allow_html=True)

        if not municipality_production.empty:
            # Enhanced horizontal bar chart
            fig_muni = px.bar(
                municipality_production,
                x="palay_production",
                y="municipality",
                orientation="h",
                color="palay_production",
                color_continuous_scale=["#A5D6A7", "#2E7D32"],
                text="palay_production"
            )

            fig_muni.update_traces(
                texttemplate="%{text:,.0f} MT",
                textposition="outside",
                marker=dict(
                    line=dict(width=2, color='white'),
                    cornerradius=4
                ),
                hovertemplate="<b>%{y}</b><br>Production: %{x:,.0f} MT<extra></extra>"
            )

            fig_muni.update_layout(
                height=500,
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis_title="Metric Tons",
                yaxis_title=None,
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                coloraxis_showscale=False,
                hovermode="y unified"
            )
            fig_muni.update_xaxes(gridcolor="#F3F4F6", showgrid=True)
            fig_muni.update_yaxes(gridcolor="#F3F4F6", showgrid=True)

            st.plotly_chart(
                fig_muni,
                use_container_width=True,
                key="municipality_production_fig"
            )
        else:
            st.info("📭 No matching data found for your current filters.")

        st.markdown("</div>", unsafe_allow_html=True)

    # SMART FARMER CARDS INTERACTION VIEW
        # SMART FARMER CARDS INTERACTION VIEW
        with chart_row2_col2:
            st.markdown(f"""
            <div class="component-card">
                <div class="component-header">Smart Agricultural Advisories</div>
                <div class="component-desc">Live operational recommendations for <b>{selected_munis}</b>.</div>
            """, unsafe_allow_html=True)

            display_muni_name = "All Bataan Municipalities" if selected_munis == "All Municipalities" else selected_munis
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

    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 15px 0 5px 0; font-size: 0.75rem; color: #9CA3AF; border-top: 1px solid #E5E7EB; margin-top: 10px;">
        🌾 Bataan Rice Monitoring System • Data-driven insights for sustainable agriculture • v2.0
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)