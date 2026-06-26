import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import numpy as np

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

def PriceForecast():
    from data.Dashboard_Ready import (
        provincial_df,
        forecast_3months_fancy,
        forecast_variety_3months,
        model_name_fancy,
        model_name_regular,
        mae_fancy, rmse_fancy, r2_fancy,
        mae_regular, rmse_regular, r2_regular
    )

    # =========================
    # DATA PREP
    # =========================
    base_df = provincial_df.copy()
    base_df["date"] = pd.to_datetime(base_df["date"])
    base_df = base_df.sort_values("date")
    base_df["year"] = base_df["date"].dt.year

    latest = base_df.iloc[-1]

    # =========================================================
    #  FORECAST DATES
    # =========================================================
    forecast_months = pd.date_range(
        start=latest["date"] + pd.DateOffset(months=1),
        periods=CONFIG["forecast_horizon"],
        freq="MS"
    )

    next_month_name = forecast_months[0].strftime("%B %Y")

    # FORECAST DATAFRAMES (SHARED)
    forecast_df_fancy = pd.DataFrame({
        "date": forecast_months,
        "fancy_palay_price": forecast_3months_fancy,
        "Type": "Forecast"
    })

    forecast_df_regular = pd.DataFrame({
        "date": forecast_months,
        "other_variety_price": forecast_variety_3months,
        "Type": "Forecast"
    })

    # MAIN TITLE
    st.markdown(
        "<h2 style='text-align: center; color: #2E7D32; margin-bottom: 0rem;'>3-Month Provincial Palay Price Forecast</h2>",
        unsafe_allow_html=True
    )

    # =========================
    # TABLE
    # =========================
    st.markdown("<h3 style='color:#2E7D32;'>Price Projection</h3>", unsafe_allow_html=True)

    projection_table = pd.DataFrame({
        "Month": forecast_months.strftime("%B %Y"),
        "Fancy Palay": [f"{CONFIG['currency']}{x:.2f}" for x in forecast_3months_fancy],
        "Regular Palay": [f"{CONFIG['currency']}{x:.2f}" for x in forecast_variety_3months]
    })

    st.dataframe(projection_table, width="stretch", hide_index=True)

    st.markdown("---")

    # =========================
    # YEAR SELECTION
    # =========================
    selected_years = st.multiselect(
        "Year Selection",
        options=sorted(base_df["year"].unique()),
        default=[base_df["year"].max()]
    )

    if not selected_years:
        selected_years = [base_df["year"].max()]

    # TITLES
    chart_title = (
        f"Fancy Palay Price Trends ({selected_years[0]})"
        if len(selected_years) == 1
        else f"Fancy Palay Price Trends ({min(selected_years)}–{max(selected_years)})"
    )

    chart_title2 = (
        f"Regular Palay Price Trends ({selected_years[0]})"
        if len(selected_years) == 1
        else f"Regular Palay Price Trends ({min(selected_years)}–{max(selected_years)})"
    )

    # =========================
    # FANCY PALAY
    # =========================
    st.markdown("<h3 style='color: #2E7D32;'>Fancy Palay</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:

        if len(selected_years) == 1:

            hist_df = base_df[base_df["year"].isin(selected_years)].copy()
            hist_df["Type"] = "Historical"

            combined_df = pd.concat([hist_df, forecast_df_fancy])

            fig = px.line(
                combined_df,
                x="date",
                y="fancy_palay_price",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": CONFIG["colors"]["historical"],
                    "Forecast": CONFIG["colors"]["forecast"]
                },
                title=chart_title
            )

            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

        else:

            yearly = (
                base_df[base_df["year"].isin(selected_years)]
                .groupby("year")[["fancy_palay_price"]]
                .mean()
                .reset_index()
            )
            yearly["Type"] = "Historical"

            forecast_avg_fancy = np.mean(forecast_3months_fancy)

            forecast_yearly = pd.DataFrame({
                "year": [latest["date"].year + 1],
                "fancy_palay_price": [forecast_avg_fancy],
                "Type": ["Forecast"]
            })

            combined_df = pd.concat([yearly, forecast_yearly])

            fig = px.line(
                combined_df,
                x="year",
                y="fancy_palay_price",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": CONFIG["colors"]["historical"],
                    "Forecast": CONFIG["colors"]["forecast"]
                },
                title=chart_title
            )

            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

        fig.update_layout(
            yaxis_title=f"{CONFIG['currency']} Fancy Palay Price",
            xaxis_title="Month/Year",
            font_size=12,
            title_font_size=16,
            height=350,
            title_font_color="#2E7D32",
            margin=dict(t=40, b=20, l=20, r=20),
            yaxis=dict(tickprefix=CONFIG["currency"], separatethousands=True)
        )

        st.plotly_chart(fig, width="stretch")

    # =========================
    # KPI FANCY
    # =========================
    with col2:

        if len(selected_years) == 1:
            base_fancy_price = base_df[base_df["year"] == selected_years[0]]["fancy_palay_price"].mean()
        else:
            base_fancy_price = base_df[base_df["year"].isin(selected_years)]["fancy_palay_price"].mean()

        forecast_avg_f = np.mean(forecast_3months_fancy)

        fancy_change = 0 if base_fancy_price == 0 else (
            (forecast_avg_f - base_fancy_price) / base_fancy_price
        ) * 100

        if fancy_change > CONFIG["risk_threshold"]:
            risk = "Increasing"
            risk_color = CONFIG["colors"]["up"]
        elif fancy_change < -CONFIG["risk_threshold"]:
            risk = "Decreasing"
            risk_color = CONFIG["colors"]["down"]
        else:
            risk = "Stable"
            risk_color = CONFIG["colors"]["stable"]

        arrow = "↑" if fancy_change > 0 else "↓" if fancy_change < 0 else "→"

        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, {risk_color}22 0%, {risk_color}44 100%);
                padding: 1.8rem 1.2rem;
                border-radius: 20px;
                text-align: center;
                border: 3px solid {risk_color};
                min-height: 280px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            '>
                <div style='font-size: 1.8rem; font-weight: bold; color: {risk_color};'>{risk}</div>
                <div style='font-size: 1.6rem; color: #2E7D32;'>{arrow} {fancy_change:+.1f}%</div>
                <div style='font-size: 1rem;'>Avg: ₱{base_fancy_price:.2f}</div>
                <div style='font-size: 1rem;'>Forecast: ₱{forecast_avg_f:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"Model used: {model_name_fancy}")

    st.markdown("---")

    # =========================
    # REGULAR PALAY
    # =========================
    st.markdown("<h3 style='color: #2E7D32;'>Regular Palay</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:

        if len(selected_years) == 1:

            df = base_df[base_df["year"].isin(selected_years)].copy()
            df["Type"] = "Historical"

            combined_df = pd.concat([df, forecast_df_regular])

            fig = px.line(
                combined_df,
                x="date",
                y="other_variety_price",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": CONFIG["colors"]["historical"],
                    "Forecast": CONFIG["colors"]["forecast"]
                },
                title=chart_title2
            )

            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

        else:

            yearly = (
                base_df[base_df["year"].isin(selected_years)]
                .groupby("year")[["other_variety_price"]]
                .mean()
                .reset_index()
            )
            yearly["Type"] = "Historical"

            forecast_avg_regular = np.mean(forecast_variety_3months)

            forecast_yearly_r = pd.DataFrame({
                "year": [latest["date"].year + 1],
                "other_variety_price": [forecast_avg_regular],
                "Type": ["Forecast"]
            })

            combined_df = pd.concat([yearly, forecast_yearly_r])

            fig = px.line(
                combined_df,
                x="year",
                y="other_variety_price",
                color="Type",
                markers=True,
                color_discrete_map={
                    "Historical": CONFIG["colors"]["historical"],
                    "Forecast": CONFIG["colors"]["forecast"]
                },
                title=chart_title2
            )

            fig.update_traces(line=dict(width=3, dash="dash"), selector=dict(name="Forecast"))

        fig.update_layout(
            yaxis_title=f"{CONFIG['currency']} Regular Palay Price",
            xaxis_title="Month/Year",
            font_size=12,
            title_font_size=16,
            height=350,
            title_font_color="#2E7D32",
            margin=dict(t=40, b=20, l=20, r=20),
            yaxis=dict(tickprefix=CONFIG["currency"], separatethousands=True)
        )

        st.plotly_chart(fig,width="stretch")

    with col2:

        if len(selected_years) == 1:
            base_regular_price = base_df[base_df["year"] == selected_years[0]]["other_variety_price"].mean()
        else:
            base_regular_price = base_df[base_df["year"].isin(selected_years)]["other_variety_price"].mean()

        forecast_avg_r = np.mean(forecast_variety_3months)

        regular_change = 0 if base_regular_price == 0 else (
            (forecast_avg_r - base_regular_price) / base_regular_price
        ) * 100

        if regular_change > CONFIG["risk_threshold"]:
            risk = "Increasing"
            risk_color = CONFIG["colors"]["up"]
        elif regular_change < -CONFIG["risk_threshold"]:
            risk = "Decreasing"
            risk_color = CONFIG["colors"]["down"]
        else:
            risk = "Stable"
            risk_color = CONFIG["colors"]["stable"]

        arrow = "↑" if regular_change > 0 else "↓" if regular_change < 0 else "→"

        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, {risk_color}22 0%, {risk_color}44 100%);
                padding: 1.8rem 1.2rem;
                border-radius: 20px;
                text-align: center;
                border: 3px solid {risk_color};
                min-height: 280px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            '>
                <div style='font-size: 1.8rem; font-weight: bold; color: {risk_color};'>{risk}</div>
                <div style='font-size: 1.6rem; color: #2E7D32;'>{arrow} {regular_change:+.1f}%</div>
                <div style='font-size: 1rem;'>Avg: ₱{base_regular_price:.2f}</div>
                <div style='font-size: 1rem;'>Forecast: ₱{forecast_avg_r:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"Model used: {model_name_regular}")

    # MODEL PERFORMANCE - Rice field cards
    st.markdown("---")
    st.markdown("## Model Accuracy")

    cards_col1, cards_col2 = st.columns(2)

    with cards_col1:
        # Fancy Palay Card
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
                    padding: 0.5rem 1rem; border-radius: 20px; text-align: center;
                    box-shadow: 0 6px 15px rgba(76, 175, 80, 0.3); margin-bottom: 1rem;'>
            <h4 style='color: white; margin: 0 0 0.3rem 0; font-size: 1.1rem;'>Fancy Palay</h4>
            <div style='display: flex; justify-content: space-around; gap: 1rem; padding-top: 0.3rem;'>
                <div style='font-size: 0.9rem; color: white; padding-right: 0.5rem; border-right: 1px solid #ffffff88;'>MAE<br>{mae_fancy:.2f}</div>
                <div style='font-size: 0.9rem; color: white; padding-right: 0.5rem; border-right: 1px solid #ffffff88;'>RMSE<br>{rmse_fancy:.2f}</div>
                <div style='font-size: 0.9rem; color: white;'>R²<br>{r2_fancy:.3f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cards_col2:
        # Other Variety Card
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #8BC34A 0%, #9CCC65 100%);
                    padding: 0.5rem 1rem; border-radius: 20px; text-align: center;
                    box-shadow: 0 6px 15px rgba(139, 195, 74, 0.3); margin-bottom: 1rem;'>
            <h4 style='color: white; margin: 0 0 0.3rem 0; font-size: 1.1rem;'>Regular Palay</h4>
            <div style='display: flex; justify-content: space-around; gap: 1rem; padding-top: 0.3rem;'>
                <div style='font-size: 0.9rem; color: white; padding-right: 0.5rem; border-right: 1px solid #ffffff88;'>MAE<br>{mae_regular:.2f}</div>
                <div style='font-size: 0.9rem; color: white; padding-right: 0.5rem; border-right: 1px solid #ffffff88;'>RMSE<br>{rmse_regular:.2f}</div>
                <div style='font-size: 0.9rem; color: white;'>R²<br>{r2_regular:.3f}</div>
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
        <p style='margin: 0.3rem 0 0 0; font-size: 0.95rem; color: #558B2F;'>Overall Market Direction: <strong>{risk}</strong></p>
    </div>
    """, unsafe_allow_html=True)
