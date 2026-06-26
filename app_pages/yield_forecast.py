import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import numpy as np

def YieldForecast1():

    # Import data and model outputs
    from data.Dashboard_Ready import (
        provincial_df,
        forecast_quarterly_yield,
        mae_yield,
        rmse_yield,
        r2_yield,
        model_name_yield,
    )
    # =========================
    # DATE PREPARATION
    # =========================
    provincial_df["date"] = pd.to_datetime(provincial_df["date"])
    provincial_df = provincial_df.sort_values("date")

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

    # Back Button to go back to Public Dashboard
    if st.button("← Back to Public Dashboard"):
        st.session_state.page = "Overview"
        st.rerun()

    # Show main title
    st.markdown(
        "<h2 style='text-align: center; color: #2E7D32;'>Quarterly Provincial Yield Forecast</h2>",
        unsafe_allow_html=True
    )

    # Show projection section title
    st.markdown(
        "<h3 style='color: #2E7D32;'>Yield Projection</h3>",
        unsafe_allow_html=True
    )

    # Create projection table
    projection_table = pd.DataFrame({
        "Quarter": forecast_quarters.strftime("%B %Y"),
        "Yield (MT/ha)": forecast_quarterly_yield,
    })

    # Display table
    st.dataframe(projection_table, width="stretch", hide_index=True)

    # Add divider line
    st.markdown("---")

    # Let user choose year
    selected_years = st.multiselect(
        "Year Selection",
        options=sorted(df["year"].unique()),
        default=[df["year"].max()],
    )

    # If no selection, use latest year
    if not selected_years:
        selected_years = [df["year"].max()]

    # Show chart title
    st.markdown(
        "<h3 style='color: #2E7D32;'>Provincial Yield Forecast</h3>",
        unsafe_allow_html=True
    )

    # Set chart title
    chart_title = (
        f"Yield Trend ({selected_years[0]})"
        if len(selected_years) == 1
        else f"Yield Trends ({min(selected_years)} - {max(selected_years)})"
    )

    # Combine historical and forecast data
    combined_data = pd.concat([quarterly_df, forecast_df])

    # Sort combined data
    combined_data = combined_data.sort_values("date_q")

    # Create layout with two columns
    col1, col2 = st.columns([3, 1])

    with col1:
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
                    "Forecast": "#F57C00"
                }
            )

            # Make forecast line dashed
            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

            # Set axis labels
            fig.update_layout(
                yaxis_title="Quarterly Yield (MT/ha)",
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
                forecast_df
                .groupby("year")["quarterly_yield_mt_per_ha"]
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
                    "Forecast": "#F57C00"
                }
            )

            # Make forecast dashed
            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

            # Labels
            fig.update_layout(
                yaxis_title="Average Yield (MT/ha)",
                xaxis_title="Year",
            )

        # Show chart
        st.plotly_chart(fig, width="stretch")

    with col2:

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
            context_label = f"based on {selected_years[0]} avg"
        else:
            context_label = f"based on {len(selected_years)}-year avg"

        st.markdown(f"""

            <div style='
                background: linear-gradient(135deg, {risk_color}22 0%, {risk_color}44 100%); 
                padding: 1.8rem 1.2rem; 
                border-radius: 20px; 
                text-align: center; 
                border: 2px solid {risk_color};
                min-height: 320px;
                display: flex; 
                flex-direction: column; 
                justify-content: center;
                margin-top: 3.0rem;
                box-shadow: 0 6px 20px rgba(0,0,0,0.1);
            '>
                <div style='font-size: 1.8rem; font-weight: bold; color: {risk_color}; margin-bottom: 0.8rem;'>
                    {risk}
                </div>
                <div style='font-size: 1.6rem; color: #2E7D32; font-weight: 700;'>
                    {arrow} {percent_change:+.1f}%
                </div>
                <div style='font-size: 1rem; color: black; margin-top: 0.5rem;'>
                    {context_label}:<br>{latest_yield:.2f} MT/ha
                </div>
                <div style='font-size: 1rem; color: black; margin-top: 0.5rem;'>
                    Forecast {forecast_year1} Avg:<br>{forecast_avg:.2f} MT/ha
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Add divider line
    st.markdown("---")

    # MODEL PERFORMANCE - yield
    st.markdown(f"""
        <h2 style='color: black;'>Model Accuracy</h2>
        <p style='color: black; font-size: 1rem; margin-top: -10px;'>
            Model used: {model_name_yield}
        </p>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #43A047 0%, #66BB6A 100%);
        padding: 0.7rem 1.2rem; 
        border-radius: 20px; 
        text-align: center;
        box-shadow: 0 8px 20px rgba(76, 175, 80, 0.4);
        margin-bottom: 1rem;
        transition: transform 0.3s, box-shadow 0.3s;
        font-family: 'Poppins', sans-serif;
    ">
        <h4 style="
            color: white; 
            margin: 0 0 0.5rem 0; 
            font-size: 1.2rem;
            text-shadow: 0 2px 5px rgba(0,0,0,0.3);
        ">Fancy Palay</h4>
        <div style="
            display: flex; 
            justify-content: space-around; 
            gap: 1rem; 
            padding-top: 0.3rem;
        ">
            <div style="
                font-size: 0.95rem; 
                color: white; 
                padding-right: 0.5rem; 
                border-right: 1px solid #ffffff88;
            ">MAE<br><b>{mae_yield:.2f}</b></div>
            <div style="
                font-size: 0.95rem; 
                color: white; 
                padding-right: 0.5rem; 
                border-right: 1px solid #ffffff88;
            ">RMSE<br><b>{rmse_yield:.2f}</b></div>
            <div style="
                font-size: 0.95rem; 
                color: white;
            ">R²<br><b>{r2_yield:.3f}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------
    # METRICS EXPLANATION (COLLAPSIBLE)
    # -----------------------------
    with st.expander("ℹ️ What do these metrics mean?"):
        components.html("""
            <div style="background:#f9fbf9;
                        padding:1.2rem 1.5rem;
                        border-radius:15px;
                        box-shadow:0 4px 12px rgba(0,0,0,0.05);">

                <div style="display:flex; flex-direction:column; gap:0.8rem; font-size:0.95rem; color:#333;">

                    <div>
                        <b>MAE (Mean Absolute Error)</b><br>
                        This measures the average difference between predicted and actual values.<br>
                        <span style="color:#2e7d32;">Lower value = more accurate predictions overall.</span>
                    </div>

                    <div>
                        <b>RMSE (Root Mean Squared Error)</b><br>
                        This measures prediction error while giving more weight to large mistakes.<br>
                        <span style="color:#2e7d32;">Lower value = fewer large prediction errors.</span>
                    </div>

                    <div>
                        <b>R² (R-squared / Coefficient of Determination)</b><br>
                        This shows how well the model explains the variation in the actual data.<br>
                        <span style="color:#2e7d32;">Closer to 1 = better model fit and prediction accuracy.</span>
                    </div>
                </div>
            </div>
        """, height=220)

    # FOOTER
    st.markdown("---")
    # Footer
    st.markdown(f"""
        <div style='
            text-align: center; 
            padding: 2rem; 
            background: linear-gradient(90deg, #E8F5E8 0%, #F1F8E9 100%);
            border-radius: 20px; 
            color: #2E7D32;
            margin-top: 0rem;
        '>
            <p style='margin: 0; font-size: 1.1rem; font-weight: 600;'>Forecast updated: {next_month_name}</p>
            <p style='margin: 0.3rem 0 0 0; font-size: 0.95rem; color: #558B2F;'>Overall Yield Projection: <strong>{risk}</strong></p>
        </div>
        """, unsafe_allow_html=True)

