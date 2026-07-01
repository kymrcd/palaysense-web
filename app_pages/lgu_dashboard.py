import streamlit as st
import base64
import pandas as pd
import plotly.express as px

# -----------------------------
# IMPORT PAGE MODULES
# ----------------------------
from app_pages.price_forecast import PriceForecast as price_forecast
from app_pages.palay_production import  PalayProduction as crop_production
from app_pages.yield_forecast import YieldForecast1 as yield_forecast
from landing_page import landing_page as landing_page

def lgu_dashboard():

    # Import datasets and forecast results
    try:
        from data.Dashboard_Ready import (
            provincial_df,
            supply_df,
            forecast_3months_fancy, forecast_variety_3months, forecast_quarterly_yield,
            municipality_df
        )

    except ModuleNotFoundError:
        from data.Dashboard_Ready import (
            provincial_df,
            supply_df,
            forecast_3months_fancy, forecast_variety_3months, forecast_quarterly_yield,
            municipality_df
        )

    # -----------------------------
    # PREPARE DATA
    # -----------------------------
    provincial_df["date"] = pd.to_datetime(provincial_df["date"])
    provincial_df = provincial_df.sort_values("date")

    df = provincial_df.copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")

    # Get latest year automatically
    latest_year = provincial_df["date"].dt.year.max()

    provincial_latest = provincial_df[
        provincial_df["date"].dt.year == latest_year
        ].copy()

    provincial_latest = provincial_latest.sort_values("date")

    latest = provincial_latest.iloc[-1]
    data_year = latest_year

    # -----------------------------
    # PAGE SETTINGS
    # -----------------------------

    # -----------------------------
    # IMAGE HELPERS
    # -----------------------------
    def get_base64(image_path):
        """Convert an image file to base64 so it can be embedded in HTML."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def get_bytes(image_path):
        """Read image bytes for Streamlit page icon."""
        with open(image_path, "rb") as f:
            return f.read()

    logo_path = "assets/logo.png"
    logo_base64 = get_base64(logo_path)

    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #FAFAFA;
    }

    .main {
        background-color: #FAFAFA;
    }
    </style>
    """, unsafe_allow_html=True)

    # -----------------------------
    # SESSION STATE FOR PAGE
    # -----------------------------
    if "page" not in st.session_state:
        st.session_state.page = "Overview"

    st.markdown("""
    <!-- Load Poppins -->
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">

    <style>
    /* Apply font globally */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Headers */
    h1, h2, h3 {
        font-weight: 600 !important;
        letter-spacing: -0.3px;
    }

    /* Subtext / labels */
    p, span, label {
        font-weight: 400 !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        font-family: 'Poppins', sans-serif !important;
    }

    /* Buttons */
    button {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
    }

    /* Optional: smoother look */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    </style>
    """, unsafe_allow_html=True)

    # -----------------------------
    # HEADER
    # -----------------------------
    # Display header with logo and title
    st.markdown(f"""
    <style>
    /* Header styling */
    .header {{
        background: linear-gradient(195deg, #66bb6a, #2e7d32, #66bb6a, #2e7d32, #388e3c);
        padding: 0px 20px;
        border-radius: 10px;
        margin-top: -33px;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}
    .header .title-row {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .header h1 {{ color: white; font-size: 30px; margin:0; }}
    .header h3 {{ color: #e0e0e0; font-size:16px; font-weight:normal; margin:0px 0 0 50px; margin-top:-18px; }}

    </style>

    <div class="header">
        <div class="title-row">
            <img src="data:image/png;base64,{logo_base64}" width="180" style="border-radius: 8px;"/>
        </div>
        <h3>Forecasting Dashboard for Bataan</h3>
    </div>

    """, unsafe_allow_html=True)

    # -----------------------------
    # SIDEBAR
    # -----------------------------
    st.markdown("""
    <style>

    [data-testid="stSidebar"] {
        background: #1b3b2f;
    }

    /* Apply text color to all sidebar elements */
    [data-testid="stSidebar"] * {
        color: #E0F2E9 !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        margin-bottom: 10px !important;
        border-radius: 10px !important;
        border: 2px solid transparent !important;
        padding: 12px 14px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.25s ease !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #66BB6A 0%, #4CAF50 100%) !important;
        color: #FFFFFF !important;
        border: 2px solid #81C784 !important;
        box-shadow: 0 2px 8px rgba(102, 187, 106, 0.25) !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: rgba(102, 187, 106, 0.10) !important;
        color: #D7F2DC !important;
        border: 2px solid rgba(102, 187, 106, 0.3) !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-0.5px) !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.15) !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%) !important;
        box-shadow: 0 3px 10px rgba(102, 187, 106, 0.3) !important;
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    [data-testid="stSidebar"] {background-color: #06402B !important;}
    [data-testid="stSidebar"] * {color: white !important;}
    [data-testid="stMetric"] {background-color: #f2f2f2; padding: 18px; border-radius: 12px; border:1px solid #e0e0e0;}
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # Logo
        st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:center; margin-bottom:-10px;">
                <img src="data:image/png;base64,{logo_base64}" width="180" style="border-radius:8px; margin-top:-85px;"/>
            </div>
            <hr style="border:1px solid white;margin-top:-16px;">
            """, unsafe_allow_html=True)

        st.markdown("   ", unsafe_allow_html=True)

        # Overview Button
        if st.button(" **Dashboard**",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Overview" else "secondary",
                     key="overview_btn"):
            st.session_state.page = "Overview"
            st.rerun()

        # Crop Production Button
        if st.button(" **Crop Production**",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Crop Production" else "secondary",
                     key="CropProduction_btn"):
            st.session_state.page = "Crop Production"
            st.rerun()

        # Price Forecast Button
        if st.button(" **Price Forecast**",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Price Forecast" else "secondary",
                     key="price_btn"):
            st.session_state.page = "Price Forecast"
            st.rerun()

        # Yield Forecast Button
        if st.button(" **Yield Forecast**",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Yield Forecast" else "secondary",
                     key="yield_btn"):
            st.session_state.page = "Yield Forecast"
            st.rerun()

        if st.button(
                "**Logout**",
                use_container_width=True,
                type="secondary",
                key="logout_btn"
        ):
            st.session_state.logout_success = True
            st.query_params["page"] = "home"
            st.rerun()

    # ----------------------------
    # OVERVIEW PAGE
    # -----------------------------

    if st.session_state.page == "Overview":

        # -----------------------------
        # YEAR FILTER
        # -----------------------------
        selected_years = st.multiselect(
            "Year Selection",
            options=sorted(df["year"].unique()),
            default=[df["year"].max()]
        )

        if not selected_years:
            selected_years = [df["year"].max()]

        selected_year = selected_years[-1]

        # metrics
        provincial_year = provincial_df[
            provincial_df["date"].dt.year.isin(selected_years)
        ].copy()

        provincial_year = provincial_year.sort_values("date")

        # -----------------------------
        # METRICS COMPUTATION
        # -----------------------------
        if not provincial_year.empty:

            latest2 = provincial_year.iloc[-1]

            month_name = latest2["date"].strftime("%B %Y")

            latest_fancy_price = provincial_year["fancy_palay_price"].mean()
            latest_other_price = provincial_year["other_variety_price"].mean()

            latest_production = provincial_year.groupby(
                provincial_year["date"].dt.year
            )["production_total"].sum().mean()

            latest_harvested = provincial_year.groupby(
                provincial_year["date"].dt.year
            )["harvested_total"].sum().mean()

            # -----------------------------
            # FORECAST CALCULATION
            # -----------------------------
            forecast_months = pd.date_range(
                start=latest2["date"] + pd.DateOffset(months=1),
                periods=3,
                freq='MS'
            )

            next_month_name = forecast_months[0].strftime("%B %Y")

            # Fancy price change
            price_change = forecast_3months_fancy[0] - latest_fancy_price
            percent_change = (price_change / latest_fancy_price) * 100

            # Regular price change
            price_change2 = forecast_variety_3months[0] - latest_other_price
            percent_change2 = (price_change2 / latest_other_price) * 100

        else:
            latest = None
            latest_production = 0
            latest_harvested = 0
            percent_change = 0
            percent_change2 = 0
            next_month_name = "No forecast"

        # -----------------------------
        # SELF-SUFFICIENCY RATIO (SSR)
        # -----------------------------

        required_cols = ["net_production_clean_rice", "actual_consumption"]

        if all(col in supply_df.columns for col in required_cols):

            # Ensure date is datetime
            supply_df["date"] = pd.to_datetime(supply_df["date"])

            # Filter based on selected year
            if "Select All" in selected_years:
                supply_filtered = supply_df.copy()
            else:
                supply_filtered = supply_df[
                    supply_df["date"].dt.year.isin(selected_years)
                ].copy()

            # Compute SSR
            supply_filtered["self_sufficiency_ratio"] = (
                    supply_filtered["net_production_clean_rice"] /
                    supply_filtered["actual_consumption"] * 100
            )

            if supply_filtered.empty:
                latest_ratio = "No data available"
            else:
                supply_filtered["self_sufficiency_ratio"] = (
                        supply_filtered["net_production_clean_rice"] /
                        supply_filtered["actual_consumption"] * 100
                )

                latest_ratio = supply_filtered["self_sufficiency_ratio"].mean()

            # Interpret SSR
            if latest_ratio == "No data available":
                supply_status = "Not available"
            else:
                if latest_ratio > 105:
                    supply_status = "Surplus"
                elif latest_ratio < 95:
                    supply_status = "Deficit"
                else:
                    supply_status = "Balanced"

        current_year = selected_year

        # Clean title with dynamic year
        if len(selected_years) == 1:
            title = f"Palay Market Overview ({current_year})"
        else:
            title = f"Palay Market Overview ({min(selected_years)} - {max(selected_years)})"

        html_title = f"""
        <div style="margin-bottom: 2rem;">
            <h1 style="color:#2E7D32; font-size:2.5rem;">
                {title}
            </h1>
        </div>
        """
        st.markdown(html_title, unsafe_allow_html=True)

        st.markdown("""<hr style="border:1px solid #ddd; margin-top: -30px;">""", unsafe_allow_html=True)

        st.markdown("""
        <style>
        /* Metric value */
        div[data-testid="stMetricValue"] {
            font-size: 25px !important;
        }

        /* Metric label */
        div[data-testid="stMetricLabel"] {
            font-size: 14px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Row 1: Price Changes
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown("**🔥 Fancy Palay**")
            st.metric(
                f"Price Change ({next_month_name})",
                f"{percent_change:+.1f}%",
                delta=None,
                label_visibility="collapsed"
            )

        with col2:
            st.markdown("**🌾 Regular Palay**")

            st.metric(
                f"Price Change ({next_month_name})",
                f"{percent_change2:+.1f}%",
                delta=None,
                label_visibility="collapsed"
            )

        with col3:
            year_label = f"({current_year})" if len(
                selected_years) == 1 else f"({min(selected_years)}-{max(selected_years)})"
            st.markdown("**📈 Production**")

            st.metric(
                f"Total {year_label}",
                f"{latest_production:,.0f} MT",
                delta=None,
                label_visibility="collapsed",
            )

        with col4:
            st.markdown("**🌱 Harvested**")
            st.metric(
                f"Area {year_label}",
                f"{latest_harvested:,.0f} ha",
                delta=None,
                label_visibility="collapsed"
            )

        with col5:
            st.markdown("**⚖️ Self-Sufficiency**")

            if isinstance(latest_ratio, (int, float)):
                st.metric(
                    "SSR",
                    f"{latest_ratio:.1f}%",
                    delta=None,
                    label_visibility="collapsed"
                )
            else:
                st.metric(
                    "SSR",
                    "Not Available",
                    delta=None,
                    label_visibility="collapsed"
                )

        # Row 3: Status Cards (full width)
        status_col1, status_col2 = st.columns(2)

        with status_col1:
            # Sufficiency Status Card
            status_color = "#4CAF50" if supply_status == "Surplus" else "#F44336" if supply_status == "Deficit" else "#FF9800"
            st.markdown(f"""
                <div style='
                    background: linear-gradient(135deg, {status_color}20, {status_color}10); 
                    padding: 1rem; 
                    border-radius: 12px; 
                    border-left: 5px solid {status_color};
                    text-align: center;
                '>
                    <h3 style='color: {status_color}; margin: 0 0 0.5rem 0; font-size: 1.8rem;'>
                        {supply_status}
                    </h3>
                    <p style='margin: 0; color: #666; font-weight: 500;'>Supply Status</p>
                </div>
            """, unsafe_allow_html=True)

        with status_col2:
            # Forecast Next Month
            st.markdown(f"""
                <div style='
                    background: linear-gradient(135deg, #FFE0B2 0%, #FFF3E0 100%);
                    padding: 1rem; 
                    border-radius: 12px; 
                    border-left: 5px solid #F57C00;
                    text-align: center;
                '>
                    <h3 style='color: #F57C00; margin: 0 0 0.5rem 0; font-size: 1.5rem;'>
                        {next_month_name}
                    </h3>
                    <p style='margin: 0; color: #666; font-weight: 500;'>Forecast Period</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("""<hr style="border:1px solid #ddd; margin-bottom: 1rem;">""", unsafe_allow_html=True)

        # ----------------------------------------------------
        # START OF PRICE FORECAST
        # Create line charts for price trends
        # One for regular palay
        # One for fancy palay
        # Includes historical + forecast data

        st.markdown(
            "<h2 style='text-align: left; color: black; font-size: 25px;'>Provincial Palay Price Forecast</h2>",
            unsafe_allow_html=True
        )

        # Visualization
        col1, col2 = st.columns(2, gap="large")

        with col1:
            historical_df1 = provincial_latest[["date", "other_variety_price"]].copy()
            historical_df1["Type"] = "Historical"

            # Generate next 3 months for price forecast
            forecast_months2 = pd.date_range(
                start=latest["date"] + pd.DateOffset(months=1),
                periods=3,
                freq='MS'
            )

            forecast_df1 = pd.DataFrame({
                "date": forecast_months2,  # Make sure these dates are in 2025
                "other_variety_price": forecast_variety_3months,
                "Type": "Forecast"
            })

            combined_df1 = pd.concat([historical_df1, forecast_df1])

            fig = px.line(
                combined_df1,
                x="date",
                y="other_variety_price",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": "#388e3c",
                    "Forecast": "#FFEB3B"
                }
            )

            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

            fig.update_layout(
                yaxis_title="Regular Price",
                xaxis_title="Month",
                title_font_color="#2E7D32",
                yaxis=dict(
                    tickprefix="₱",
                    separatethousands=True
                ),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    y=-0.3,
                    x=0,
                    xanchor="left",
                    yanchor="top"
                ),
                title=dict(
                    text=f"Price Trend for Regular Palay ({data_year})"
                )
            )
            fig.update_traces(line=dict(width=3))

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            historical_df = provincial_latest[["date", "fancy_palay_price"]].copy()
            historical_df["Type"] = "Historical"

            forecast_df = pd.DataFrame({
                "date": forecast_months2,  # Make sure these dates are in 2025
                "fancy_palay_price": forecast_3months_fancy,
                "Type": "Forecast"
            })

            combined_df = pd.concat([historical_df, forecast_df])

            fig = px.line(
                combined_df,
                x="date",
                y="fancy_palay_price",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": "#388e3c",
                    "Forecast": "#FFEB3B"
                }
            )

            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

            fig.update_layout(
                yaxis_title="Fancy Price",
                xaxis_title="Month",
                title_font_color="#2E7D32",
                yaxis=dict(
                    tickprefix="₱",
                    separatethousands=True
                ),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    y=-0.3,
                    x=0,
                    xanchor="left",
                    yanchor="top"
                ),
                title=dict(
                    text=f"Price Trend for Fancy Palay ({data_year})"
                )
            )
            fig.update_traces(line=dict(width=3))

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("""<hr style="border:1px solid #ddd; margin:-10px 0; margin-top: 1rem;">""", unsafe_allow_html=True)

        # ----------------------------
        # YIELD INFO
        # ----------------------------
        # Create line chart for yield (historical + forecast)
        st.markdown(
            "<h3 style='color: black; font-size: 25px; margin-top: 1.5rem;'>"
            "Provincial Yield Forecast</h3>",
            unsafe_allow_html=True
        )

        # Visualization
        # Historical
        historical_yield = provincial_latest.copy()

        historical_yield["year"] = historical_yield["date"].dt.year
        historical_yield["quarter_label"] = (
                "Q" + historical_yield["quarter"].astype(str) + " " + historical_yield["year"].astype(str)
        )

        historical_yield = historical_yield.groupby("quarter_label")["quarterly_yield_mt_per_ha"].mean().reset_index()
        historical_yield["Type"] = "Historical"

        # Forecast (numeric quarters)
        forecast_year2 = data_year + 1

        forecast_yield = pd.DataFrame({
            "quarter_label": [f"Q{i} {forecast_year2}" for i in range(1, 5)],
            "quarterly_yield_mt_per_ha": forecast_quarterly_yield,
            "Type": "Forecast"
        })

        combined_data_yield = pd.concat([historical_yield, forecast_yield])

        fig = px.line(
            combined_data_yield,
            x="quarter_label",
            y="quarterly_yield_mt_per_ha",
            color="Type",
            markers=True,
            color_discrete_map={
                "Historical": "#388e3c",
                "Forecast": "#F57C00"
            }
        )

        fig.update_traces(line=dict(width=2, dash="dash"), selector=dict(name="Forecast"))

        fig.update_layout(
            yaxis_title="MT per hectare",
            xaxis_title="Quarter",
            title_font_color="#256029",
            showlegend=True,
            yaxis=dict(separatethousands=True),
            legend=dict(
                orientation="h",
                y=-0.3,
                x=0,
                xanchor="left",
                yanchor="top"
            ),
            title=dict(
                text=f"Palay Yield Trends and Forecast (MT/ha) ({data_year} - {forecast_year2})"
            )
        )

        fig.update_traces(line=dict(width=3))

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""<hr style="border:1px solid #ddd; margin:-10px 0; margin-top: 1rem;">""", unsafe_allow_html=True)

        # -----------------------------
        # PRODUCTION PER QUARTER
        # -----------------------------

        # Filter selected years
        production_df = provincial_df[
            provincial_df["date"].dt.year.isin(selected_years)
        ].copy()

        # Extract year and quarter
        production_df["year"] = production_df["date"].dt.year
        production_df["quarter"] = production_df["date"].dt.quarter

        # Average per year per quarter
        year_quarter_avg = (
            production_df
            .groupby(["year", "quarter"])["production_total"]
            .mean()
            .reset_index()
        )

        # Average across selected years per quarter
        production_quarterly = (
            year_quarter_avg
            .groupby("quarter")["production_total"]
            .mean()
            .reset_index()
        )

        # Format quarter labels
        production_quarterly["quarter"] = "Q" + production_quarterly["quarter"].astype(str)

        # Title
        if len(selected_years) == 1:
            titlebar = f"Provincial Quarterly Palay Production ({current_year})"
        else:
            titlebar = f"Provincial Quarterly Palay Production ({min(selected_years)} - {max(selected_years)})"

        st.markdown(
            f"""
            <h3 style='color: black; font-weight:500; margin-top: 1.5rem;'>
                {titlebar}
            </h3>
            """,
            unsafe_allow_html=True
        )

        # Bar chart
        fig = px.bar(
            production_quarterly,
            x="quarter",
            y="production_total",
            color="quarter",
            labels={"quarter": "Quarter", "production_total": "Production (MT)"},
            color_discrete_map={
                "Q1": "#FF9800",
                "Q2": "#C62828",
                "Q3": "#66BB6A",
                "Q4": "#FFB2C8"
            }
        )

        # Clean layout
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font={"family": "Inter, sans-serif", "size": 13, "color": "#374151"},
            margin=dict(l=50, r=20, t=40, b=40),
            showlegend=False,
            xaxis={"showgrid": False},
            yaxis={"showgrid": True, "gridcolor": "#F3F4F6"},
        )

        # Remove borders
        fig.update_traces(marker_line_width=0, marker_line_color=None)

        # Create columns
        col1, col2 = st.columns([2.2, 1])

        with col1:
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            highest_q = production_quarterly.loc[
                production_quarterly["production_total"].idxmax()
            ]

            lowest_q = production_quarterly.loc[
                production_quarterly["production_total"].idxmin()
            ]

            avg_prod = production_quarterly["production_total"].mean()

            trend = (
                "increasing"
                if production_quarterly["production_total"].iloc[-1]
                   > production_quarterly["production_total"].iloc[0]
                else "decreasing"
            )

            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #E8F5E9, #F1F8E9);
                padding: 1.5rem;
                border-radius: 16px;
                border-left: 6px solid #2E7D32;
                box-shadow: 0 6px 18px rgba(0,0,0,0.08);
                font-size: 0.95rem;
                line-height: 1.7;
                margin-top: 4.5rem;
            ">
            <div style="
                font-size: 1rem;
                font-weight: 700;
                color: #1B5E20;
                margin-bottom: 0.8rem;
            ">
                📊 Production Insight Summary
            </div>

            <div style="margin-bottom: 0.4rem;">
                🏆 Highest Production: <b style="color:#2E7D32;">{highest_q['quarter']}</b>
            </div>

            <div style="margin-bottom: 0.4rem;">
                📉 Lowest Production: <b style="color:#C62828;">{lowest_q['quarter']}</b>
            </div>

            <div style="margin-bottom: 0.8rem;">
                📊 Average Production: <b>{avg_prod:,.0f} MT</b>
            </div>

            <hr style="border: none; border-top: 1px solid #C8E6C9; margin: 0.8rem 0;">

            <div style="
                font-size: 0.95rem;
                font-weight: 600;
                color: #1B5E20;
            ">
                📈 Overall trend:
                <span style="color:#2E7D32; font-weight:700;">
                    {trend.upper()}
                </span>
                 pattern over the selected period
            </div>

            </div>
            """, unsafe_allow_html=True)

        st.markdown("""<hr style="border:1px solid #E5E7EB; margin: 1.5rem 0;">""", unsafe_allow_html=True)

        # -----------------------------
        # TOP MUNICIPALITIES ANALYSIS
        # -----------------------------
        st.markdown(
            "<h3 style='margin-top:20px;'>Top Municipalities by Production</h3>",
            unsafe_allow_html=True
        )

        # Prepare municipality data
        municipality_df["date"] = pd.to_datetime(municipality_df["date"])
        mf = municipality_df.copy()
        mf["year"] = mf["date"].dt.year

        selected_municipality_y = st.multiselect(
            "Year Selection",
            options=sorted(mf["year"].unique()),
            default=[mf["year"].max()],
            help="Select one or more year"
        )
        # fallback to latest year if empty
        if not selected_municipality_y:
            selected_municipality_y = [mf["year"].max()]

        # Filter based on selected years
        mfiltered_mf = mf[mf["year"].isin(selected_municipality_y)]

        n_years = len(selected_municipality_y)
        latest_year_m = selected_municipality_y[-1]

        # -----------------------------
        # TOP 5 MUNICIPALITIES (TOTAL PRODUCTION)
        # -----------------------------
        if n_years > 2:
            # AVERAGE per year first, then rank
            top5 = (
                mfiltered_mf
                .groupby(["municipality", "year"])["palay_production"]
                .sum()
                .reset_index()
                .groupby("municipality")["palay_production"]
                .mean()
                .reset_index()
                .sort_values(by="palay_production", ascending=True)
                .head(5)
            )
        else:
            # NORMAL TOTAL for 1–2 years
            top5 = (
                mfiltered_mf
                .groupby("municipality")["palay_production"]
                .sum()
                .reset_index()
                .sort_values(by="palay_production", ascending=True)
                .head(5)
            )

        fig_top5 = px.bar(
            top5,
            x="palay_production",
            y="municipality",
            orientation="h",
            color="palay_production",
            color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
            text=top5["palay_production"].round(0).astype(int),
            title=f"Top 5 Municipalities by Total Production {latest_year_m}" if len(selected_municipality_y) == 1
            else f"Top 5 Municipalities by Average Production ({min(selected_municipality_y)} - {max(selected_municipality_y)})"
        )

        fig_top5.update_layout(
            xaxis_title="Production (MT)",
            yaxis_title="Municipality",
            showlegend=False
        )

        # Format numbers
        fig_top5.update_traces(
            texttemplate='%{text:,}',
            textposition='outside'
        )

        st.plotly_chart(fig_top5, use_container_width=True)

        # -----------------------------
        # SEASONAL DISTRIBUTION (PIE CHARTS)
        # -----------------------------
        st.markdown(
            "<h3 style='margin-top:20px;'>Seasonal Production Distribution</h3>",
            unsafe_allow_html=True
        )

        # DRY SEASON TOP 5
        if n_years > 2:
            dry_top5 = (
                mfiltered_mf
                .groupby(["municipality", "year"])["dry_season"]
                .sum()
                .reset_index()
                .groupby("municipality")["dry_season"]
                .mean()
                .reset_index()
                .sort_values(by="dry_season", ascending=True)
                .head(5)
            )
        else:
            dry_top5 = (
                mfiltered_mf
                .groupby("municipality")["dry_season"]
                .sum()
                .reset_index()
                .sort_values(by="dry_season", ascending=True)
                .head(5)
            )

        fig_dry = px.pie(
            dry_top5,
            names="municipality",
            values="dry_season",
            title=f"Dry Season Production {latest_year_m} (Top 5)" if len(selected_municipality_y) == 1
            else f"Dry Season Production ({min(selected_municipality_y)} - {max(selected_municipality_y)})",
            color_discrete_sequence=px.colors.sequential.Greens[0:5][::-1]
        )

        # WET SEASON TOP 5
        if n_years > 2:
            wet_top5 = (
                mfiltered_mf
                .groupby(["municipality", "year"])["wet_season"]
                .sum()
                .reset_index()
                .groupby("municipality")["wet_season"]
                .mean()
                .reset_index()
                .sort_values(by="wet_season", ascending=True)
                .head(5)
            )
        else:
            wet_top5 = (
                mfiltered_mf
                .groupby("municipality")["wet_season"]
                .sum()
                .reset_index()
                .sort_values(by="wet_season", ascending=True)
                .head(5)
            )

        fig_wet = px.pie(
            wet_top5,
            names="municipality",
            values="wet_season",
            title=f"Wet Season Production {latest_year_m} (Top 5)" if len(selected_municipality_y) == 1
            else f"Wet Season Production ({min(selected_municipality_y)} - {max(selected_municipality_y)})",
            color_discrete_sequence=px.colors.sequential.Teal[0:5][::-1]
        )

        # DISPLAY SIDE BY SIDE
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(fig_dry, use_container_width=True)

        with col2:
            st.plotly_chart(fig_wet, use_container_width=True)

        st.markdown("""<hr style="border:1px solid #ddd; margin-top: 1rem; margin-bottom: 1rem;">""",
                    unsafe_allow_html=True)

        # Footer
        st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; 
                        background: linear-gradient(90deg, #E8F5E8 0%, #F1F8E9 100%);
                        border-radius: 15px; color: #2E7D32;'>
                <p style='margin: 0; font-size: 1rem; font-weight: 500;'> Forecast updated: {next_month_name}</p>
            </div>
        """, unsafe_allow_html=True)

    # -----------------------------
    # PRICE FORECAST PAGE
    # -----------------------------

    # If the user selects the Price Forecast page
    # call the render() function from the Price_Forecast_Page module
    if st.session_state.page == "Price Forecast":
        price_forecast()

    elif st.session_state.page == "Crop Production":
        crop_production()

    elif st.session_state.page == "Yield Forecast":
        yield_forecast()