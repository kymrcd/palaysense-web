import streamlit as st
import base64
import pandas as pd
import plotly.express as px

# -----------------------------
# IMPORT PAGE MODULES
# ----------------------------
from app_pages.price_forecast import PriceForecast as price_forecast
from app_pages.palay_production import PalayProduction as crop_production
from app_pages.yield_forecast import YieldForecast1 as yield_forecast
from app_pages.upload_dataset import upload_dataset
from data.Dashboard_Ready import reload_dashboard_data

# =========================
# CONFIG (centralized rules)
# =========================
CONFIG = {
    "forecast_horizon": 3,
    "risk_threshold": 3,
    "colors": {
        "up": "#4CAF50",
        "down": "#FF9800",
        "stable": "#FFC107",
        "historical": "#4CAF50",
        "forecast": "#FFEB3B"
    },
    "currency": "₱"
}

_MUNI_VARIETY_COLS = (
    "hybridpremium_dry", "hybridpremium_wet",
    "hybridordinary_dry", "hybridordinary_wet",
    "inbredpremium_dry", "inbredpremium_wet",
    "inbredordinary_dry", "inbredordinary_wet",
)


def _derive_municipal_columns(mf):
    """Derive `palay_production`, `dry_season`, `wet_season` from the raw
    per-variety x season columns when they are missing from the municipal dataset
    (matches `data_layer._municipal_production_series` semantics)."""
    mf = mf.copy()
    available = [c for c in _MUNI_VARIETY_COLS if c in mf.columns]
    if not available:
        return mf
    if "palay_production" not in mf.columns:
        mf["palay_production"] = mf[available].sum(axis=1, numeric_only=True)
    if "dry_season" not in mf.columns:
        dry = [c for c in available if c.endswith("_dry")]
        if dry:
            mf["dry_season"] = mf[dry].sum(axis=1, numeric_only=True)
    if "wet_season" not in mf.columns:
        wet = [c for c in available if c.endswith("_wet")]
        if wet:
            mf["wet_season"] = mf[wet].sum(axis=1, numeric_only=True)
    return mf


def lgu_dashboard():
    if st.session_state.pop("login_success", False):
        st.toast("Logged in successfully!")

    dashboard_ready = reload_dashboard_data()

    # Import datasets and forecast results
    provincial_df = dashboard_ready.provincial_df
    supply_df = dashboard_ready.supply_df
    forecast_3months_fancy = dashboard_ready.forecast_3months_fancy
    forecast_variety_3months = dashboard_ready.forecast_variety_3months
    forecast_quarterly_yield = dashboard_ready.forecast_quarterly_yield
    municipality_df = dashboard_ready.municipality_df
    municipality_history_df = dashboard_ready.municipality_history_df
    _prod_muni = getattr(dashboard_ready, "municipal_production_df", None)
    if _prod_muni is not None and not getattr(_prod_muni, "empty", True):
        municipality_df = _prod_muni
    df_municipal_forecasts = dashboard_ready.df_municipal_forecasts

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

    # =========================
    # DATA PREP
    # =========================
    base_df = provincial_df.copy()
    base_df["date"] = pd.to_datetime(base_df["date"])
    base_df = base_df.sort_values("date")
    base_df["year"] = base_df["date"].dt.year
    province_name = base_df["province"].iloc[0]

    latest_provincial_record = base_df.iloc[-1]

    # =========================================================
    #  FORECAST DATES (PROVINCIAL FORECAST)
    # =========================================================
    provincial_forecast_months = pd.date_range(
        start=latest_provincial_record["date"] + pd.DateOffset(months=1),
        periods=CONFIG["forecast_horizon"],
        freq="MS"
    )

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
    # FORECAST PREPARATION (YEILD)
    # =========================
    latest_q = quarterly_df.iloc[-1]

    forecast_quarters = pd.period_range(
        start=pd.Period(latest_q["date_q"], freq="Q") + 1,
        periods=4,
        freq="Q"
    )

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

    # -----------------------------
    # SESSION STATE FOR PAGE
    # -----------------------------
    if "page" not in st.session_state:
        st.session_state.page = "Overview"

    # -----------------------------
    # HEADER - Modern shadcn-style
    # -----------------------------
    page_title_map = {
        "Overview": "Palay Market Overview",
        "Data Upload": "Dataset Management",
        "Price Forecast": "3-Month Palay Price Forecast",
        "Price Trends": "Palay Price Trends",
        "Yield Forecast": "Quarterly Provincial Yield Forecast",
        "Yield Trends": "Palay Yield Trends",
        "Crop Production": "Palay Production",
    }
    current_page_title = page_title_map.get(st.session_state.page, "Dashboard")
    current_page_subtitle = {
        "Overview": "Comprehensive agricultural insights and forecast data for Bataan province.",
        "Data Upload": "Upload and manage provincial and municipal datasets.",
        "Price Forecast": "Predictive analysis of Fancy and Regular palay prices.",
        "Price Trends": "Historical price movements and forecast projections.",
        "Yield Forecast": "Quarterly yield predictions and performance metrics.",
        "Yield Trends": "Historical yield trends and forward-looking projections.",
        "Crop Production": "Production, harvesting, and sufficiency analysis.",
    }.get(st.session_state.page, "")

    st.markdown(f"""
    <div class="ps-header">
        <div class="ps-header-left">
            <h1 class="ps-header-title">{current_page_title}</h1>
            <p class="ps-header-subtitle">{current_page_subtitle}</p>
        </div>
        <div class="ps-user-card">
            <div class="ps-avatar">U</div>
            <div class="ps-user-info">
                <span class="ps-user-greeting">Hello, User</span>
                <span class="ps-user-role">Bataan PIA</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------
    # SIDEBAR — handled by global CSS in styles.py
    # -----------------------------
    st.markdown("""
    <style>
        /* Import Google Material Symbols Font */
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

        .material-symbols-outlined {
            font-family: 'Material Symbols Outlined' !important;
            font-weight: normal;
            font-style: normal;
            font-size: 10px;
            line-height: 1;
            letter-spacing: normal;
            text-transform: none;
            display: inline-block;
            white-space: nowrap;
            word-wrap: normal;
            direction: ltr;
            -webkit-font-smoothing: antialiased;
        }
    </style>
    """, unsafe_allow_html=True)

    # ─── SIDEBAR ICON HELPER ───
    def _sidebar_icon(icon_name):
        """Render a Material Symbol icon in the sidebar inline with text."""
        return f'<i class="material-symbols-outlined" style="font-size:18px; color:#C8E6C9; vertical-align:middle; margin-right:6px;">{icon_name}</i>'

    with st.sidebar:
        # ─── LOGO — NO TOP GAP ───
        st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:center; padding:0; margin:0;">
                <img src="data:image/png;base64,{logo_base64}" width="150" style="border-radius:4px; display:block;"/>
            </div>
            <hr class="ps-sidebar-divider">
            """, unsafe_allow_html=True)

        # ─── DATA MANAGEMENT ───
        st.markdown('<p class="ps-sidebar-section">Data Management</p>', unsafe_allow_html=True)
        if st.button(" Import Data",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Data Upload" else "secondary",
                     key="data_upload_btn"):
            st.session_state.page = "Data Upload"
            st.rerun()

        st.markdown('<hr class="ps-sidebar-divider">', unsafe_allow_html=True)

        # ─── DASHBOARD ───
        st.markdown('<p class="ps-sidebar-section">Dashboard</p>', unsafe_allow_html=True)
        if st.button(" Overview",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Overview" else "secondary",
                     key="overview_btn"):
            st.session_state.page = "Overview"
            st.rerun()

        st.markdown('<hr class="ps-sidebar-divider">', unsafe_allow_html=True)

        # ─── PALAY PRICE ───
        st.markdown('<p class="ps-sidebar-section">Palay Price</p>', unsafe_allow_html=True)
        if st.button(" Forecast",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Price Forecast" else "secondary",
                     key="price_btn"):
            st.session_state.page = "Price Forecast"
            st.rerun()

        if st.button(" Trends",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Price Trends" else "secondary",
                     key="price_trends_btn"):
            st.session_state.page = "Price Trends"
            st.rerun()

        st.markdown('<hr class="ps-sidebar-divider">', unsafe_allow_html=True)

        # ─── PALAY YIELD ───
        st.markdown('<p class="ps-sidebar-section">Palay Yield</p>', unsafe_allow_html=True)
        if st.button(" Forecast",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Yield Forecast" else "secondary",
                     key="yield_btn"):
            st.session_state.page = "Yield Forecast"
            st.rerun()

        if st.button(" Trends",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Yield Trends" else "secondary",
                     key="yield_trends_btn"):
            st.session_state.page = "Yield Trends"
            st.rerun()

        st.markdown('<hr class="ps-sidebar-divider">', unsafe_allow_html=True)

        # ─── PRODUCTION ───
        st.markdown('<p class="ps-sidebar-section">Production</p>', unsafe_allow_html=True)
        if st.button(" Crop Production",
                     use_container_width=True,
                     type="primary" if st.session_state.page == "Crop Production" else "secondary",
                     key="CropProduction_btn"):
            st.session_state.page = "Crop Production"
            st.rerun()

        st.markdown('<hr class="ps-sidebar-divider">', unsafe_allow_html=True)

        # ─── FILTERS SECTION ───
        st.markdown('<p class="ps-sidebar-section">Filter</p>', unsafe_allow_html=True)

        # Municipality filter label + selectbox
        st.markdown(
            f'<p class="ps-sidebar-section" style="font-size:0.7rem !important; margin-bottom:2px !important;">{_sidebar_icon("location_on")} Municipality</p>',
            unsafe_allow_html=True)
        selected_municipality = st.selectbox(
            "",
            [
                "All Municipalities",
                "Abucay", "Bagac", "Balanga", "Dinalupihan",
                "Hermosa", "Limay", "Mariveles", "Morong",
                "Orani", "Orion", "Pilar", "Samal"
            ],
            key="sidebar_filter_municipality",
            label_visibility="collapsed"
        )

        # Year filter label + selectbox
        st.markdown(
            f'<p class="ps-sidebar-section" style="font-size:0.7rem !important; margin-bottom:2px !important; margin-top:4px !important;">{_sidebar_icon("calendar_today")} Year</p>',
            unsafe_allow_html=True)
        selected_year_filter = st.selectbox(
            "",
            ["Latest", "2025", "2024", "2023", "2022", "2021"],
            key="sidebar_filter_year",
            label_visibility="collapsed"
        )

        st.markdown('<hr class="ps-sidebar-divider">', unsafe_allow_html=True)

        # ─── LOGOUT ───
        if st.button(" Logout",
                     use_container_width=True,
                     type="secondary",
                     key="logout_btn"):
            st.session_state.logout_success = True
            st.query_params["page"] = "home"
            st.rerun()
    # ----------------------------------------------------
    # ROUTING LOGIC EXECUTION FOR ROUTED WORKSPACES
    # ----------------------------------------------------

    # 1. CHANGE THIS FROM 'if' TO 'elif' so it chains together, and add the Upload route above it:
    if st.session_state.page == "Data Upload":
        upload_dataset()

    elif st.session_state.page == "Crop Production":
        crop_production()

    elif st.session_state.page == "Price Forecast":
        price_forecast()

    elif st.session_state.page == "Yield Forecast":
        yield_forecast()

    elif st.session_state.page == "Price Trends":
        # ─── PRICE TRENDS ─────────────────────────────────────
        st.markdown("""
        <div style="margin-bottom: 2rem;">
            <h1 style="color:#2E7D32; font-size:2.5rem;">📉 Palay Price Trends</h1>
            <p style="color:#666; font-size:1rem;">Historical price movements and forecast projections for Fancy and Regular Palay.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""<hr style="border:1px solid #ddd; margin-top:-20px; margin-bottom:1.5rem;">""", unsafe_allow_html=True)

        # Build historical price dataframe
        price_trend_df = provincial_df.copy()
        price_trend_df = price_trend_df.sort_values("date")

        # Fancy Palay Price Trend
        fig_fancy = px.line(
            price_trend_df,
            x="date",
            y="fancy_palay_price",
            title="Fancy Palay Price Trend",
            labels={"date": "Date", "fancy_palay_price": "Price (₱)"},
            color_discrete_sequence=["#2E7D32"]
        )

        # Add forecast line for fancy
        forecast_fancy_df = pd.DataFrame({
            "date": provincial_forecast_months,
            "fancy_palay_price": forecast_3months_fancy
        })
        fig_fancy.add_scatter(
            x=forecast_fancy_df["date"],
            y=forecast_fancy_df["fancy_palay_price"],
            mode="lines+markers",
            name="Forecast",
            line=dict(color="#FF9800", dash="dash"),
            marker=dict(size=8)
        )

        fig_fancy.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="x unified",
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # Regular Palay Price Trend
        fig_regular = px.line(
            price_trend_df,
            x="date",
            y="other_variety_price",
            title="Regular Palay Price Trend",
            labels={"date": "Date", "other_variety_price": "Price (₱)"},
            color_discrete_sequence=["#1565C0"]
        )

        # Add forecast line for regular
        forecast_regular_df = pd.DataFrame({
            "date": provincial_forecast_months,
            "other_variety_price": forecast_variety_3months
        })
        fig_regular.add_scatter(
            x=forecast_regular_df["date"],
            y=forecast_regular_df["other_variety_price"],
            mode="lines+markers",
            name="Forecast",
            line=dict(color="#FF9800", dash="dash"),
            marker=dict(size=8)
        )

        fig_regular.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="x unified",
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_fancy, use_container_width=True)
        with col2:
            st.plotly_chart(fig_regular, use_container_width=True)

        # Price comparison chart
        st.markdown("""<hr style="border:1px solid #ddd; margin:1.5rem 0;">""", unsafe_allow_html=True)
        st.subheader("📊 Price Comparison: Fancy vs Regular Palay")

        fig_compare = px.line(
            price_trend_df,
            x="date",
            y=["fancy_palay_price", "other_variety_price"],
            labels={"date": "Date", "value": "Price (₱)", "variable": "Variety"},
            color_discrete_map={
                "fancy_palay_price": "#2E7D32",
                "other_variety_price": "#1565C0"
            }
        )
        fig_compare.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="x unified",
            margin=dict(l=40, r=20, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        # Rename legend
        fig_compare.for_each_trace(lambda t: t.update(name="Fancy Palay" if t.name == "fancy_palay_price" else "Regular Palay"))
        st.plotly_chart(fig_compare, use_container_width=True)

        st.caption("💡 Historical data shown with dashed forecast line for next 3 months.")

    elif st.session_state.page == "Yield Trends":
        # ─── YIELD TRENDS ─────────────────────────────────────
        st.markdown("""
        <div style="margin-bottom: 2rem;">
            <h1 style="color:#2E7D32; font-size:2.5rem;">📉 Palay Yield Trends</h1>
            <p style="color:#666; font-size:1rem;">Historical quarterly yield trends and projections for Bataan province.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""<hr style="border:1px solid #ddd; margin-top:-20px; margin-bottom:1.5rem;">""", unsafe_allow_html=True)

        # Historical yield data
        yield_trend_df = quarterly_df.copy()

        fig_yield = px.bar(
            yield_trend_df,
            x="quarter_label",
            y="quarterly_yield_mt_per_ha",
            title="Historical Quarterly Yield (MT/ha)",
            labels={"quarter_label": "Quarter", "quarterly_yield_mt_per_ha": "Yield (MT/ha)"},
            color="quarterly_yield_mt_per_ha",
            color_continuous_scale=["#C8E6C9", "#66BB6A", "#2E7D32"],
            text=yield_trend_df["quarterly_yield_mt_per_ha"].round(2)
        )
        fig_yield.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=40, r=20, t=50, b=80),
            showlegend=False,
            xaxis_tickangle=-45
        )
        fig_yield.update_traces(textposition="outside")
        st.plotly_chart(fig_yield, use_container_width=True)

        # Yield forecast projection
        st.markdown("""<hr style="border:1px solid #ddd; margin:1.5rem 0;">""", unsafe_allow_html=True)
        st.subheader("🌱 Yield Forecast Projection")

        forecast_yield_df = pd.DataFrame({
            "Quarter": forecast_quarters.strftime("%B %Y"),
            "Forecasted Yield (MT/ha)": forecast_quarterly_yield
        })

        col1, col2 = st.columns([1.5, 1])
        with col1:
            fig_yield_forecast = px.bar(
                forecast_yield_df,
                x="Quarter",
                y="Forecasted Yield (MT/ha)",
                color="Forecasted Yield (MT/ha)",
                color_continuous_scale=["#FFF176", "#FBC02D", "#F57C00"],
                text=forecast_yield_df["Forecasted Yield (MT/ha)"].round(2)
            )
            fig_yield_forecast.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=40, r=20, t=30, b=60),
                showlegend=False
            )
            fig_yield_forecast.update_traces(textposition="outside")
            st.plotly_chart(fig_yield_forecast, use_container_width=True)

        with col2:
            avg_yield = forecast_yield_df["Forecasted Yield (MT/ha)"].mean()
            max_yield = forecast_yield_df["Forecasted Yield (MT/ha)"].max()
            min_yield = forecast_yield_df["Forecasted Yield (MT/ha)"].min()

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.8rem; border-radius:16px; border-left:6px solid #2E7D32; box-shadow:0 6px 18px rgba(0,0,0,0.08);">
                <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.8rem;">
                    📊 Yield Forecast Summary
                </div>
                <div style="margin-bottom:0.4rem;">📈 Average: <b>{avg_yield:.2f} MT/ha</b></div>
                <div style="margin-bottom:0.4rem;">🏆 Peak: <b>{max_yield:.2f} MT/ha</b></div>
                <div style="margin-bottom:0.4rem;">📉 Low: <b>{min_yield:.2f} MT/ha</b></div>
                <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.8rem 0;">
                <div style="font-size:0.9rem; color:#2E7D32;">Based on next 4 quarters</div>
            </div>
            """, unsafe_allow_html=True)

        st.caption("💡 Yield trends show historical performance with forward-looking projections.")

    elif st.session_state.page == "Overview":

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

            latest_selected_year_record = provincial_year.iloc[-1]

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
            overview_forecast_months = pd.date_range(
                start=latest_selected_year_record["date"] + pd.DateOffset(months=1),
                periods=3,
                freq='MS'
            )

            overview_forecast_period = overview_forecast_months[0].strftime("%B %Y")

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
            overview_forecast_period = "No forecast"

        # -----------------------------
        # SELF-SUFFICIENCY RATIO (SSR)
        # -----------------------------
        latest_ratio = "No data available"
        supply_status = "Not available"

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
        
        year_label = f"({current_year})" if len(
            selected_years) == 1 else f"({min(selected_years)}-{max(selected_years)})"


        st.markdown(f"""
        <div class="ps-filter-container">
            <!-- Filters handled by actual Streamlit selectboxes below -->
        </div>
        """, unsafe_allow_html=True)

        fancy_arrow = "↑" if percent_change >= 0 else "↓"
        regular_arrow = "↑" if percent_change2 >= 0 else "↓"

        # -----------------------------
        # COMPACT KPI CARDS + STATUS
        # -----------------------------
        # Color helpers for card accents
        _card_border = "#E6EAE6"
        _card_bg = "#FFFFFF"
        _card_shadow = "0 1px 3px rgba(0,0,0,0.06)"

        def _kpi_card(icon, icon_bg, icon_color, label, value, change, change_color):
            """Render an inline-styled KPI card with an icon square box underneath."""
            return f"""
            <div style="background:{_card_bg};border:1px solid {_card_border};border-radius:14px;padding:1rem 1.1rem;display:flex;flex-direction:column;gap:0.25rem;box-shadow:{_card_shadow};">
                <span style="font-size:0.72rem;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.4px;">{label}</span>
                <div style="font-size:1.5rem;font-weight:800;color:#1F2937;letter-spacing:-0.5px;line-height:1.1;">{value}</div>
                <span style="font-size:0.72rem;font-weight:500;color:{change_color};margin-top:0.1rem;">{change}</span>
                <div style="width:40px;height:40px;margin-top:0.5rem;border-radius:10px;display:flex;align-items:center;justify-content:center;background:{icon_bg};color:{icon_color};">
                    <i class="material-symbols-outlined" style="font-size:22px;line-height:1;">{icon}</i>
                </div>
            </div>
            """

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:0.65rem;">
            {_kpi_card('currency_peso', 'rgba(30,92,58,0.1)', '#1E5C3A', 'Fancy Palay', f"{fancy_arrow} {abs(percent_change):.1f}%", overview_forecast_period, '#16A34A' if percent_change >= 0 else '#DC2626')}
            {_kpi_card('agriculture', 'rgba(107,114,128,0.1)', '#6B7280', 'Regular Palay', f"{regular_arrow} {abs(percent_change2):.1f}%", overview_forecast_period, '#16A34A' if percent_change2 >= 0 else '#DC2626')}
            {_kpi_card('trending_up', 'rgba(22,163,74,0.1)', '#16A34A', 'Production', f"{latest_production:,.0f}", f"MT {year_label}", '#6B7280')}
            {_kpi_card('eco', 'rgba(245,158,11,0.1)', '#F59E0B', 'Harvested', f"{latest_harvested:,.0f}", f"ha {year_label}", '#6B7280')}
        </div>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.65rem;margin-bottom:1.25rem;">
            <div style="background:{_card_bg};border:1px solid {_card_border};border-radius:14px;box-shadow:{_card_shadow};display:flex;align-items:center;justify-content:space-between;padding:0.75rem 1.25rem;">
                <div>
                    <div style="font-size:0.6rem;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.3px;">Supply</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{'#16A34A' if supply_status == 'Surplus' else '#DC2626' if supply_status == 'Deficit' else '#F59E0B'};margin-top:0.1rem;">{supply_status}</div>
                </div>
                <i class="material-symbols-outlined" style="font-size:1.8rem;color:{'#16A34A' if supply_status == 'Surplus' else '#DC2626' if supply_status == 'Deficit' else '#F59E0B'};">{'check_circle' if supply_status == 'Surplus' else 'warning' if supply_status == 'Balanced' else 'error'}</i>
            </div>
            <div style="background:{_card_bg};border:1px solid {_card_border};border-radius:14px;box-shadow:{_card_shadow};display:flex;align-items:center;justify-content:space-between;padding:0.75rem 1.25rem;">
                <div>
                    <div style="font-size:0.6rem;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.3px;">Forecast</div>
                    <div style="font-size:1.1rem;font-weight:700;color:#1E5C3A;margin-top:0.1rem;">{overview_forecast_period}</div>
                </div>
                <i class="material-symbols-outlined" style="font-size:1.8rem;color:#1E5C3A;">calendar_month</i>
            </div>
        </div>
        
        """, unsafe_allow_html=True)

        st.markdown('<hr class="ps-divider">', unsafe_allow_html=True)

        # ----------------------------------------------------
        # PROVINCIAL FORECAST TABLES (Card Wrapped)
        # ----------------------------------------------------
        yield_col, price_col = st.columns(2, gap="medium")

        # ==========================
        # YIELD FORECAST
        # ==========================
        with yield_col:
            st.markdown('<div class="ps-chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="ps-chart-title"><i class="material-symbols-outlined">eco</i> Provincial Yield Forecast</div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-chart-desc">View the projected provincial palay yield for the upcoming quarters.</div>', unsafe_allow_html=True)

            yield_projection_table = pd.DataFrame({
                "Province": [province_name] * len(forecast_quarters),
                "Month/Period": forecast_quarters.strftime("%B %Y"),
                "Yield (MT/ha)": forecast_quarterly_yield,
            })

            st.dataframe(
                yield_projection_table,
                width="stretch",
                hide_index=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # ==========================
        # PRICE FORECAST
        # ==========================
        with price_col:
            st.markdown('<div class="ps-chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="ps-chart-title"><i class="material-symbols-outlined">agriculture</i> Provincial Palay Price Forecast</div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-chart-desc">View the projected provincial prices for Fancy and Regular Palay over the next three months.</div>', unsafe_allow_html=True)

            price_projection_table = pd.DataFrame({
                "Province": [province_name] * len(provincial_forecast_months),
                "Month": provincial_forecast_months.strftime("%B %Y"),
                "Fancy Palay": [f"{CONFIG['currency']}{x:.2f}" for x in forecast_3months_fancy],
                "Regular Palay": [f"{CONFIG['currency']}{x:.2f}" for x in forecast_variety_3months]
            })

            st.dataframe(
                price_projection_table,
                width="stretch",
                hide_index=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<hr class="ps-divider">', unsafe_allow_html=True)

        # -----------------------------
        # MUNICIPAL FORECAST CARD
        # -----------------------------
        st.markdown('<div class="ps-chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ps-chart-title"><i class="material-symbols-outlined">agriculture</i> Municipal Palay Price Forecast</div>', unsafe_allow_html=True)
        st.markdown('<div class="ps-chart-desc">View the projected monthly palay prices across the municipalities of Bataan. Use the tabs below to compare forecasts for the Dry Season and Wet Season.</div>', unsafe_allow_html=True)

        try:
            # Use the dataframe already loaded by dashboard_ready.py
            df_municipal_forecast = df_municipal_forecasts.copy()

            # ----------------------------------------
            # Dynamic forecast month labels (municipal)
            # ----------------------------------------
            muni_last_year = int(municipality_history_df["year"].max())
            muni_last_month_data = municipality_history_df[municipality_history_df["year"] == muni_last_year]
            muni_last_month = int(muni_last_month_data["month_num"].max()) if "month_num" in muni_last_month_data.columns else 12
            muni_latest_date = pd.Timestamp(year=muni_last_year, month=muni_last_month, day=1)

            municipal_forecast_months = pd.date_range(
                start=muni_latest_date + pd.DateOffset(months=1),
                periods=3,
                freq="MS"
            )

            municipal_month_labels = municipal_forecast_months.strftime("%B %Y").tolist()

            # 1. Interactive UI Filter for Municipalities
            muni_list = list(df_municipal_forecast["Municipality"].unique())
            selected_muni = st.multiselect("Filter Municipalities:", options=muni_list, default=[])

            # Apply global municipality filter first
            df_filtered_muni = df_municipal_forecast.copy()
            if selected_muni:
                df_filtered_muni = df_filtered_muni[df_filtered_muni["Municipality"].isin(selected_muni)]

            # 2. CREATE VISUALLY APPEALING SEASONAL TABS
            tab_dry, tab_wet = st.tabs(["☀️ Dry Season Forecasts", "🌧️ Wet Season Forecasts"])

            # ========================================================
            # TAB 1: DRY SEASON VIEW
            # ========================================================
            with tab_dry:
                # Filter rows where target column contains "_dry"
                df_dry = df_filtered_muni[
                    df_filtered_muni["Rice Type & Season"].str.contains("_dry", case=False, na=False)].copy()

                # Clean up the name for presentation (e.g., "hybridpremium_dry" -> "Hybrid Premium")
                df_dry["Rice Classification"] = df_dry["Rice Type & Season"].str.replace("_dry", "",
                                                                                         case=False).str.replace("_",
                                                                                                                 " ").str.title()

                # Reorder columns for a neat presentation layout
                df_dry_display = (
                    df_dry[
                        ["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]
                    ]
                    .rename(columns={
                        "Month 1": municipal_month_labels[0],
                        "Month 2": municipal_month_labels[1],
                        "Month 3": municipal_month_labels[2],
                    })
                )

                st.write("### ☀️ Peak & Off-Peak Dry Season Metrics")
                st.dataframe(
                    df_dry_display,
                    use_container_width=True,
                    hide_index=True,
                    height=280
                )
                st.caption(f"Displaying {len(df_dry_display)} dry season configurations.")

            # ========================================================
            # TAB 2: WET SEASON VIEW
            # ========================================================
            with tab_wet:
                # Filter rows where target column contains "_wet"
                df_wet = df_filtered_muni[
                    df_filtered_muni["Rice Type & Season"].str.contains("_wet", case=False, na=False)].copy()

                # Clean up the name for presentation (e.g., "hybridpremium_wet" -> "Hybrid Premium")
                df_wet["Rice Classification"] = df_wet["Rice Type & Season"].str.replace("_wet", "",
                                                                                         case=False).str.replace("_",
                                                                                                                 " ").str.title()

                df_wet_display = (
                    df_wet[
                        ["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]
                    ]
                    .rename(columns={
                        "Month 1": municipal_month_labels[0],
                        "Month 2": municipal_month_labels[1],
                        "Month 3": municipal_month_labels[2],
                    })
                )

                st.write("### 🌧️ Rain-fed & High-Moisture Wet Season Metrics")
                st.dataframe(
                    df_wet_display,
                    use_container_width=True,
                    hide_index=True,
                    height=280
                )
                st.caption(f"Displaying {len(df_wet_display)} wet season configurations.")

        except FileNotFoundError:
            st.warning("⚠️ Forecast dataset report not found. Please verify the background pipeline ran completely.")
        except Exception as e:
            st.error(f"⚠️ Unable to render the municipal forecast data table: {str(e)}")

        # Close the municipal forecast card
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<hr class="ps-divider">', unsafe_allow_html=True)

        # -----------------------------
        # PRODUCTION PER QUARTER CARD
        # -----------------------------
        st.markdown('<div class="ps-chart-card">', unsafe_allow_html=True)

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
            <h3 style='color: black; font-weight:500; margin-top: -.8rem;'>
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

        # Prepare municipality data (guard against provincial-only / missing date)
        if (
            municipality_df is None
            or getattr(municipality_df, "empty", True)
            or "date" not in getattr(municipality_df, "columns", [])
        ):
            st.warning("⚠️ Municipality dataset is not ready (missing 'date'). Skipping municipal analysis.")
            mf = pd.DataFrame(columns=["date", "municipality"])
        else:
            municipality_df["date"] = pd.to_datetime(municipality_df["date"])
            mf = _derive_municipal_columns(municipality_df.copy())
            mf["year"] = mf["date"].dt.year

        if mf.empty or "year" not in mf.columns:
            st.info("📭 Municipality dataset not available for the selected upload. Skipping municipal charts.")
            return
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
                .sort_values(by="palay_production", ascending=False)
                .head(5)
            )
        else:
            # NORMAL TOTAL for 1–2 years
            top5 = (
                mfiltered_mf
                .groupby("municipality")["palay_production"]
                .sum()
                .reset_index()
                .sort_values(by="palay_production", ascending=False)
                .head(5)
            )

        plot_top5 = top5.sort_values("palay_production")

        fig_top5 = px.bar(
            plot_top5,
            x="palay_production",
            y="municipality",
            orientation="h",
            color="palay_production",
            color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
            text=plot_top5["palay_production"].round(0).astype(int),
            title=f"Top 5 Municipalities by Total Production {latest_year_m}" if len(selected_municipality_y) == 1
            else f"Top 5 Municipalities by Average Production ({min(selected_municipality_y)} - {max(selected_municipality_y)})"
        )

        fig_top5.update_layout(
            xaxis_title="Production (MT)",
            yaxis_title="Municipality",
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
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
                .sort_values(by="dry_season", ascending=False)
                .head(5)
            )
        else:
            dry_top5 = (
                mfiltered_mf
                .groupby("municipality")["dry_season"]
                .sum()
                .reset_index()
                .sort_values(by="dry_season", ascending=False)
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
                .sort_values(by="wet_season", ascending=False)
                .head(5)
            )
        else:
            wet_top5 = (
                mfiltered_mf
                .groupby("municipality")["wet_season"]
                .sum()
                .reset_index()
                .sort_values(by="wet_season", ascending=False)
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

        # Close production card
        st.markdown('</div>', unsafe_allow_html=True)

        # Footer
        st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; 
                        background: linear-gradient(90deg, #E8F5E8 0%, #F1F8E9 100%);
                        border-radius: 15px; color: #2E7D32;'>
                <p style='margin: 0; font-size: 1rem; font-weight: 500;'> Forecast updated: {overview_forecast_period}</p>
            </div>
        """, unsafe_allow_html=True)
