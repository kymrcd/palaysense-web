import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import numpy as np

from data.Dashboard_Ready import reload_dashboard_data


def YieldForecast1():
    dashboard_ready = reload_dashboard_data()

    provincial_df = dashboard_ready.provincial_df
    forecast_quarterly_yield = dashboard_ready.forecast_quarterly_yield
    mae_yield = dashboard_ready.mae_yield
    rmse_yield = dashboard_ready.rmse_yield
    r2_yield = dashboard_ready.r2_yield
    model_name_yield = dashboard_ready.model_name_yield
    # =========================
    # DATE PREPARATION
    # =========================
    provincial_df["date"] = pd.to_datetime(provincial_df["date"])
    provincial_df = provincial_df.sort_values("date")
    province_name = provincial_df["province"].iloc[0]

    # Get latest row dynamically
    latest = provincial_df.iloc[-1]

    # =========================
    # FEATURE ENGINEERING
    # =========================
    df = provincial_df.copy()

    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter

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

    # -----------------------------
    # FORECAST CALCULATION
    # -----------------------------
    forecast_months = pd.date_range(
        start=latest["date"] + pd.DateOffset(months=1),
        periods=4,
        freq='MS'
    )

    next_month_name = forecast_months[0].strftime("%B %Y")

    # =========================
    # PROJECTION SECTION
    # =========================
    # Show projection section title
    st.markdown(
        "<h3 style='color: #2E7D32; font-weight: 600; margin-bottom: 0.8rem;'>Yield Projection Table</h3>",
        unsafe_allow_html=True
    )

    # Create projection table
    yield_projection_table = pd.DataFrame({
        "Province": [province_name] * len(forecast_quarters),
        "Month/Period": forecast_quarters.strftime("%B %Y"),
        "Yield (MT/ha)": forecast_quarterly_yield,
    })

    # Display table
    st.dataframe(yield_projection_table, use_container_width=True, hide_index=True)

    # Add divider line
    st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    # Let user choose year
    selected_years = st.multiselect(
        "Filter Timeline (Years)",
        options=sorted(df["year"].unique()),
        default=[df["year"].max()],
    )

    # If no selection, use latest year
    if not selected_years:
        selected_years = [df["year"].max()]

    # Show chart title
    st.markdown(
        "<h3 style='color: #2E7D32; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.5rem;'>Provincial Yield Forecast</h3>",
        unsafe_allow_html=True
    )

    # Set chart title
    chart_title = (
        f"Yield Trend ({selected_years[0]})"
        if len(selected_years) == 1
        else f"Yield Trends and Forecast ({min(selected_years)} - {max(selected_years)})"
    )

    # Combine historical and forecast data
    combined_data = pd.concat([quarterly_df, forecast_df])

    col1, col2 = st.columns([3, 1.2], gap="medium")
    with col1:


        tab1, tab2 = st.tabs([
            ":material/show_chart: Yield Trends",
            ":material/query_stats: Forecast Trends"
        ])

        # ==========================
        # HISTORICAL
        # ==========================
        with tab1:

            if len(selected_years) == 1:

                hist_df = quarterly_df[
                    quarterly_df["year"] == selected_years[0]
                    ]

                fig_hist = px.line(
                    hist_df,
                    x="quarter_label",
                    y="quarterly_yield_mt_per_ha",
                    markers=True,
                    title=f"Historical Yield Trends ({selected_years[0]})",
                    color_discrete_sequence=["#388e3c"]
                )

                fig_hist.update_layout(
                    yaxis_title="Yield (MT/ha)",
                    xaxis_title="Quarter"
                )

            else:

                historical_avg = (
                    quarterly_df[
                        quarterly_df["year"].isin(selected_years)
                    ]
                    .groupby("year")["quarterly_yield_mt_per_ha"]
                    .mean()
                    .reset_index()
                )

                fig_hist = px.line(
                    historical_avg,
                    x="year",
                    y="quarterly_yield_mt_per_ha",
                    markers=True,
                    title=f"Historical Yield Trends ({min(selected_years)}–{max(selected_years)})",
                    color_discrete_sequence=["#388e3c"]
                )

                fig_hist.update_layout(
                    yaxis_title="Avg Yield (MT/ha)",
                    xaxis_title="Year"
                )

            fig_hist.update_layout(
                font_size=11,
                title_font_size=18,
                title_font_color="#1B5E20",
                height=350,
                margin=dict(t=40, b=20, l=10, r=10),
                plot_bgcolor="white",
                paper_bgcolor="white",
                yaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
                xaxis=dict(gridcolor="rgba(0,0,0,0.05)")
            )

            st.plotly_chart(fig_hist, use_container_width=True)

        # ==========================
        # FORECAST
        # ==========================
        with tab2:

            # If one year is selected
            if len(selected_years) == 1:
                year = selected_years[0]

                # Filter historical data for selected year
                hist_df = quarterly_df[quarterly_df["year"] == year]

                plot_df = pd.concat([hist_df, forecast_df])

                # Create line chart
                fig = px.line(
                    plot_df,
                    x="quarter_label",
                    y="quarterly_yield_mt_per_ha",
                    color="Type",
                    markers=True,
                    title=chart_title,
                    color_discrete_map={
                        "Historical": "#388e3c",
                        "Forecast": "#F57C00",
                    },
                )

                # Make forecast line dashed
                fig.update_traces(
                    selector=dict(name="Forecast"),
                )

                # Set axis labels
                fig.update_layout(
                    yaxis_title="Yield (MT/ha)",
                    xaxis_title="Quarter",
                )

            else:
                # Compute yearly average for historical
                historical_avg = (
                    quarterly_df[quarterly_df["year"].isin(selected_years)]
                    .groupby("year")["quarterly_yield_mt_per_ha"]
                    .mean()
                    .reset_index()
                )

                historical_avg["Type"] = "Historical"

                # Compute yearly average for forecast (next year)
                forecast_avg = (
                    forecast_df.groupby("year")["quarterly_yield_mt_per_ha"]
                    .mean()
                    .reset_index()
                )

                forecast_avg["Type"] = "Forecast"

                # Combine both
                yearly_avg = pd.concat([historical_avg, forecast_avg])

                # Create line chart
                fig = px.line(
                    yearly_avg,
                    x="year",
                    y="quarterly_yield_mt_per_ha",
                    color="Type",
                    markers=True,
                    title=chart_title,
                    color_discrete_map={
                        "Historical": "#388e3c",
                        "Forecast": "#F57C00",
                    },
                )

                # Make forecast dashed
                fig.update_traces(
                    selector=dict(name="Forecast"),
                )

                # Labels
                fig.update_layout(
                    yaxis_title="Avg Yield (MT/ha)",
                    xaxis_title="Year",
                )

            # Modern plot layout configurations (Clean & Transparent)
            fig.update_layout(
                font_size=11,
                title_font_size=21,
                height=400,
                margin=dict(t=40, b=20, l=10, r=10),
                plot_bgcolor="white",
                paper_bgcolor="white",
                yaxis=dict(
                    separatethousands=True,
                    gridcolor="rgba(0,0,0,0.05)",
                ),
                xaxis=dict(
                    gridcolor="rgba(0,0,0,0.05)",
                ),
            )

            st.plotly_chart(fig, use_container_width=True)


    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Get latest actual yield
        selected_hist = quarterly_df[quarterly_df["year"].isin(selected_years)]

        # Get the average of selected year/s
        hist_avg = selected_hist["quarterly_yield_mt_per_ha"].mean()

        # Forecast (future)
        forecast_avg = np.mean(forecast_quarterly_yield)

        # Percent change
        percent_change = ((forecast_avg - hist_avg) / hist_avg) * 100

        # For display
        latest_yield = hist_avg

        # Set risk label based on change
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

        if len(selected_years) == 1:
            context_label = f"{selected_years[0]} Avg"
        else:
            context_label = f"{len(selected_years)}-Yr Avg"

        # COMPACT MODERN METRIC CARD (No heavy gradients, tight footprint)
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
                    <span style='color: #888888;'>{context_label}:</span>
                    <span style='font-weight: 600; color: #333333;'>{latest_yield:.2f} MT/ha</span>
                </div>
                <div style='display: flex; justify-content: space-between; font-size: 0.85rem;'>
                    <span style='color: #888888;'>Forecast ({forecast_year1}):</span>
                    <span style='font-weight: 600; color: #333333;'>{forecast_avg:.2f} MT/ha</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Add divider line
    st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    # =========================
    # MODEL PERFORMANCE (MODERN)
    # =========================
    st.markdown(f"""
        <h3 style='color: #1B5E20; font-weight: 600; margin-bottom: 0.2rem;'>Model Performance</h3>
        <p style='color: #666666; font-size: 0.85rem; margin-bottom: 1rem;'>Engine Pipeline: <b>{model_name_yield}</b></p>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="
        background-color: var(--background-color, #ffffff);
        padding: 1.2rem; 
        border-radius: 12px; 
        border-top: 4px solid #388e3c;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    ">
        <div style="
            display: flex; 
            justify-content: space-around; 
            align-items: center;
            gap: 1rem;
        ">
            <div style="text-align: center; flex: 1; border-right: 1px solid #f0f0f0;">
                <span style="font-size: 0.8rem; color: #666666; text-transform: uppercase;">MAE</span>
                <h3 style="margin: 0.2rem 0 0 0; font-size: 1.6rem; font-weight: 700; color: #333333;">{mae_yield:.2f}</h3>
            </div>
            <div style="text-align: center; flex: 1; border-right: 1px solid #f0f0f0;">
                <span style="font-size: 0.8rem; color: #666666; text-transform: uppercase;">RMSE</span>
                <h3 style="margin: 0.2rem 0 0 0; font-size: 1.6rem; font-weight: 700; color: #333333;">{rmse_yield:.2f}</h3>
            </div>
            <div style="text-align: center; flex: 1;">
                <span style="font-size: 0.8rem; color: #666666; text-transform: uppercase;">R² Score</span>
                <h3 style="margin: 0.2rem 0 0 0; font-size: 1.6rem; font-weight: 700; color: #388e3c;">{r2_yield:.3f}</h3>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------
    # METRICS EXPLANATION (COLLAPSIBLE)
    # -----------------------------
    with st.expander(" Understanding Accuracy Metrics"):
        components.html("""
            <div style="background:#ffffff;
                        padding:0.5rem 0.8rem;
                        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <div style="display:flex; flex-direction:column; gap:0.8rem; font-size:0.9rem; color:#444;">
                    <div>
                        <b style="color:#2e7d32;">MAE (Mean Absolute Error)</b> — Average sizing of errors between predictions and reality. Lower scores indicate tight overall forecasts.
                    </div>
                    <div>
                        <b style="color:#2e7d32;">RMSE (Root Mean Squared Error)</b> — Gauges predictive variation, penalizing outliers heavily. Lower values mean less high-variance mistakes.
                    </div>
                    <div>
                        <b style="color:#2e7d32;">R² Score (Coefficient of Determination)</b> — Measures explained variation. Values near 1.0 signify a highly reliable model fit.
                    </div>
                </div>
            </div>
        """, height=160)

    # =========================
    # FOOTER SECTION (CLEAN BANNER)
    # =========================
    st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='
            text-align: center; 
            padding: 1.5rem; 
            background: #F4F9F4;
            border-radius: 12px; 
            border: 1px solid #E2EFE2;
            color: #2E7D32;
        '>
            <p style='margin: 0; font-size: 1rem; font-weight: 600;'>Forecast Cycle Updated: <span style='color: #1B5E20;'>{next_month_name}</span></p>
            <p style='margin: 0.2rem 0 0 0; font-size: 0.9rem; color: #558B2F;'>Overall Dynamic Trend Assessment: <strong>{risk}</strong></p>
        </div>
        """, unsafe_allow_html=True)