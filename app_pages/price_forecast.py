import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import numpy as np
import math

# -------------------------
# UI helpers (design-only)
# -------------------------

def _divider(margin="2rem 0"):
  st.markdown(f"<hr style='margin: {margin}; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)


def _section_title(text, align="left", size="26px"):
  st.markdown(
    f"""
    <h2 style='text-align:{align}; color:#1B5E20; font-weight:800; font-size:{size}; margin: 0.2rem 0 1rem 0;'>
      {text}
    </h2>
    """,
    unsafe_allow_html=True,
  )


def _kpi_card(label, model_name, hist_avg, forecast, risk, risk_color):
  arrow = "↑" if forecast > hist_avg else "↓" if forecast < hist_avg else "→"
  change = 0 if hist_avg == 0 else ((forecast - hist_avg) / hist_avg) * 100
  st.markdown(
    f"""
    <div style='
      background-color: rgba(27, 94, 32, 0.03);
      padding: 1.1rem 1.2rem;
      border-radius: 14px;
      border: 1px solid rgba(27, 94, 32, 0.15);
      box-shadow: 0 10px 30px rgba(0,0,0,0.05);
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
    '>
      <div style='display:flex; justify-content:space-between; align-items:center; gap: 1rem;'>
        <div style='display:flex; flex-direction:column; gap:0.15rem;'>
          <span style='font-size:0.78rem; color:#2E7D32; font-weight:800; letter-spacing:0.3px; text-transform:uppercase;'>
            {label}
          </span>
          <span style='font-size:0.95rem; color:#1B5E20; font-weight:700;'>
            {risk}
          </span>
        </div>
        <div style='font-size:1.6rem; font-weight:900; color:{risk_color};'>
          {arrow} {change:+.1f}%
        </div>
      </div>

      <div style='display:flex; justify-content:space-between; font-size:0.9rem; border-top:1px solid #EEF2F3; padding-top:0.55rem;'>
        <span style='color:#6B7280;'>Hist. Avg</span>
        <span style='font-weight:900; color:#111827;'>₱{hist_avg:.2f}</span>
      </div>

      <div style='display:flex; justify-content:space-between; font-size:0.9rem;'>
        <span style='color:#6B7280;'>Forecast</span>
        <span style='font-weight:900; color:#111827;'>₱{forecast:.2f}</span>
      </div>

      <div style='text-align:right; font-size:0.78rem; color:#6B7280; margin-top:0.2rem;'><i class='material-symbols-outlined' style='font-size:14px; vertical-align:middle; margin-right:4px; color:#6B7280;'>smart_toy</i> {model_name}</div>
    </div>
    """,
    unsafe_allow_html=True,
  )


def _footer_banner(next_month_name, risk_text, risk_color="#1B5E20"):
  st.markdown(
    f"""
    <div style='
      text-align:center;
      padding: 1.3rem 1.2rem;
      background: linear-gradient(135deg, rgba(76,175,80,0.08), rgba(255,235,59,0.08));
      border-radius: 16px;
      border: 1px solid rgba(46,125,50,0.18);
      color: #1B5E20;
    '>
      <div style='font-size:1rem; font-weight:900;'>
        Forecast Cycle Updated: <span style='color:{risk_color}'>{next_month_name}</span>
      </div>
      <div style='margin-top:0.25rem; font-size:0.92rem; color:#2E7D32;'>
        Overall Dynamic Trend Assessment: <strong>{risk_text}</strong>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
  )


from data.Dashboard_Ready import reload_dashboard_data

# =========================
# CONFIG (centralized rules)
# =========================
CONFIG = {
  "forecast_horizon": 3,
  "risk_threshold": 3,
  "colors": {
    "up": "#4CAF50",
    "down": "#D32F2F",
    "stable": "#FFC107",
    "historical": "#4CAF50",
    "forecast": "#FFEB3B"
  },
  "currency": "₱"
}


def PriceForecast():
  dashboard_ready = reload_dashboard_data()

  provincial_df = dashboard_ready.provincial_df
  municipality_history_df = dashboard_ready.municipality_history_df
  forecast_3months_fancy = dashboard_ready.forecast_3months_fancy
  forecast_variety_3months = dashboard_ready.forecast_variety_3months
  model_name_fancy = dashboard_ready.model_name_fancy
  model_name_regular = dashboard_ready.model_name_regular
  mae_fancy = dashboard_ready.mae_fancy
  rmse_fancy = dashboard_ready.rmse_fancy
  r2_fancy = dashboard_ready.r2_fancy
  mae_regular = dashboard_ready.mae_regular
  rmse_regular = dashboard_ready.rmse_regular
  r2_regular = dashboard_ready.r2_regular
  df_municipal_forecasts = dashboard_ready.df_municipal_forecasts

  # =========================
  # DATA PREP
  # =========================
  base_df = provincial_df.copy()
  base_df["date"] = pd.to_datetime(base_df["date"])
  base_df = base_df.sort_values("date")
  base_df["year"] = base_df["date"].dt.year
  province_name = base_df["province"].iloc[0]

  latest = base_df.iloc[-1]

  # =========================================================
  # FORECAST DATES
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

  # =========================
  # TABLE
  # =========================
  st.markdown("<h3 style='color: #2E7D32; font-weight: 600; margin-bottom: 0.8rem;'>Price Projection</h3>",
        unsafe_allow_html=True)

  projection_table = pd.DataFrame({
    "Province": [province_name] * len(forecast_months),
    "Month": forecast_months.strftime("%B %Y"),
    "Fancy Palay": [f"{CONFIG['currency']}{x:.2f}" for x in forecast_3months_fancy],
    "Regular Palay": [f"{CONFIG['currency']}{x:.2f}" for x in forecast_variety_3months]
  })

  st.dataframe(projection_table, use_container_width=True, hide_index=True)

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
    tab_dry, tab_wet = st.tabs([":material/wb_sunny: Dry Season Forecasts", ":material/water_drop: Wet Season Forecasts"])

    # ========================================================
    # TAB 1: DRY SEASON VIEW
    # ========================================================
    with tab_dry:
      # Filter rows where target column contains "_dry"
      df_dry = df_filtered_muni[
        df_filtered_muni["Rice Type & Season"].str.contains("_dry", case=False, na=False)].copy()

      # Clean up the name for presentation (e.g., "hybridpremium_dry" -> "Hybrid Premium")
      _rice_type_map = {
        "hybridpremium": "Hybrid Premium",
        "hybridordinary": "Hybrid Ordinary",
        "inbredpremium": "Inbred Premium",
        "inbredordinary": "Inbred Ordinary",
      }
      raw_codes = df_dry["Rice Type & Season"].str.replace("_dry", "", case=False)
      df_dry["Rice Classification"] = raw_codes.map(_rice_type_map).fillna(
        raw_codes.str.replace("_", " ").str.title()
      )

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

      st.write("### :material/wb_sunny: Peak & Off-Peak Dry Season Metrics")
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
      _rice_type_map = {
        "hybridpremium": "Hybrid Premium",
        "hybridordinary": "Hybrid Ordinary",
        "inbredpremium": "Inbred Premium",
        "inbredordinary": "Inbred Ordinary",
      }
      raw_codes = df_wet["Rice Type & Season"].str.replace("_wet", "", case=False)
      df_wet["Rice Classification"] = raw_codes.map(_rice_type_map).fillna(
        raw_codes.str.replace("_", " ").str.title()
      )

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

      st.write("### :material/water_drop: Rain-fed & High-Moisture Wet Season Metrics")
      st.dataframe(
        df_wet_display,
        use_container_width=True,
        hide_index=True,
        height=280
      )
      st.caption(f"Displaying {len(df_wet_display)} wet season configurations.")

  except FileNotFoundError:
    st.warning(" Forecast dataset report not found. Please verify the background pipeline ran completely.")
  except Exception as e:
    st.error(f" Unable to render the municipal forecast data table: {str(e)}")

  st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

  # =========================
  # Provincial
  # =========================
  st.markdown(
    """
    <h2 style='text-align: center;
          color:#1B5E20;
          font-weight:700;
          margin-bottom: 1rem;'>
      Provincial-Level Palay Prices 
    </h2>
    """,
    unsafe_allow_html=True
  )

  # =========================
  # YEAR SELECTION
  # =========================
  selected_years = st.multiselect(
    "Filter Trend Line (Years)",
    options=sorted(base_df["year"].unique()),
    default=[base_df["year"].max()]
  )

  if not selected_years:
    selected_years = [base_df["year"].max()]

  #=============================
  #FANCY
  #-------------------------------
  st.markdown(
    """
    <h2 style='text-align: left;
          color:#1B5E20;
          font-size:25px;
          margin-bottom: 1rem;'>
      Provincial Fancy Palay
    </h2>
    """,
    unsafe_allow_html=True
  )

  # TITLES
  chart_title = (
    f"Fancy Palay Price Trend & Forecast ({selected_years[0]})"
    if len(selected_years) == 1
    else f"Fancy Palay Price Trends ({min(selected_years)}–{max(selected_years)})"
  )

  chart_title2 = (
    f"Regular Palay Price Trends ({selected_years[0]})"
    if len(selected_years) == 1
    else f"Regular Palay Price Trend & Forecast ({min(selected_years)}–{max(selected_years)})"
  )

  col1, col2 = st.columns([3, 1.2], gap="medium")

  with col1:
    # =========================
    # TABS
    # =========================
    tab1, tab2 = st.tabs([
      ":material/show_chart: Price Trends",
      ":material/query_stats: Forecast Trends"
    ])
    # --------------------------------
    # HISTORICAL CHART
    # --------------------------------
    with tab1:

      if len(selected_years) == 1:

        hist_df = base_df[base_df["year"].isin(selected_years)].copy()

        fig_hist = px.line(
          hist_df,
          x="date",
          y="fancy_palay_price",
          markers=True,
          title=f"Provincial Fancy Palay Price Trends ({selected_years[0]})",
          color_discrete_sequence=[CONFIG["colors"]["historical"]]
        )

      else:

        yearly = (
          base_df[base_df["year"].isin(selected_years)]
          .groupby("year")[["fancy_palay_price"]]
          .mean()
          .reset_index()
        )

        fig_hist = px.line(
          yearly,
          x="year",
          y="fancy_palay_price",
          markers=True,
          title=f"Provincial Fancy Palay Price Trends ({min(selected_years)}–{max(selected_years)})",
          color_discrete_sequence=[CONFIG["colors"]["historical"]]
        )

      fig_hist.update_layout(
        yaxis_title=f"{CONFIG['currency']} / kg",
        xaxis_title="Timeline",
        font_size=11,
        title_font_size=21,
        title_font_color="#1B5E20",
        height=400,
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis=dict(
          tickprefix=CONFIG["currency"],
          separatethousands=True,
          gridcolor="rgba(0,0,0,0.05)"
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0.05)")
      )

      st.plotly_chart(fig_hist, use_container_width=True)

    # --------------------------------
    # FORECAST CHART
    # --------------------------------
    with tab2:

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
            "Forecast": CONFIG["colors"]["forecast"],
          },
          title=chart_title,
        )

        fig.update_traces(
          selector=dict(name="Forecast"),
        )

      else:
        yearly = (
          base_df[base_df["year"].isin(selected_years)]
          .groupby("year")[["fancy_palay_price"]]
          .mean()
          .reset_index()
        )

        yearly["Type"] = "Historical"

        forecast_avg_fancy = np.mean(forecast_3months_fancy)

        forecast_yearly = pd.DataFrame(
          {
            "year": [latest["date"].year + 1],
            "fancy_palay_price": [forecast_avg_fancy],
            "Type": ["Forecast"],
          }
        )

        combined_df = pd.concat([yearly, forecast_yearly])

        fig = px.line(
          combined_df,
          x="year",
          y="fancy_palay_price",
          color="Type",
          markers=True,
          color_discrete_map={
            "Historical": CONFIG["colors"]["historical"],
            "Forecast": CONFIG["colors"]["forecast"],
          },
          title=chart_title,
        )

        fig.update_traces(
          selector=dict(name="Forecast"),
        )

      fig.update_layout(
        yaxis_title=f"{CONFIG['currency']} / kg",
        xaxis_title="Timeline",
        font_size=11,
        title_font_size=21,
        height=400,
        title_font_color="#1B5E20",
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis=dict(
          tickprefix=CONFIG["currency"],
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

    if len(selected_years) == 1:
      base_fancy_price = base_df[
        base_df["year"] == selected_years[0]
        ]["fancy_palay_price"].mean()
    else:
      base_fancy_price = base_df[
        base_df["year"].isin(selected_years)
      ]["fancy_palay_price"].mean()

    forecast_avg_f = np.mean(forecast_3months_fancy)

    fancy_change = (
      0
      if base_fancy_price == 0
      else ((forecast_avg_f - base_fancy_price) / base_fancy_price) * 100
    )

    if fancy_change > CONFIG["risk_threshold"]:
      risk = "Increasing"
      risk_color = CONFIG["colors"]["up"]
    elif fancy_change < -CONFIG["risk_threshold"]:
      risk = "Decreasing"
      risk_color = CONFIG["colors"]["down"]
    else:
      risk = "Stable"
      risk_color = CONFIG["colors"]["stable"]

    arrow = (
      "↑" if fancy_change > 0
      else "↓" if fancy_change < 0
      else "→"
    )

    st.markdown(
      f"""
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
          <span style='
          font-size: 0.85rem;
          color: #666666;
          font-weight: 500;
          text-transform: uppercase;
      '>
        {risk}
      </span>

      <span style='
        font-size: 1.3rem;
        font-weight: 800;
        color: {risk_color};
      '>
        {arrow} {fancy_change:+.1f}%
      </span>
      </div>

      <div style='
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        border-top: 1px solid #f5f5f5;
        padding-top: 0.4rem;
      '>
        <span style='color: #888888;'>Hist. Avg:</span>
        <span style='font-weight: 600; color: #333333;'>
          ₱{base_fancy_price:.2f}
        </span>
      </div>

      <div style='
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
      '>
        <span style='color: #888888;'>Forecast:</span>
        <span style='font-weight: 600; color: #333333;'>
          ₱{forecast_avg_f:.2f}
        </span>
      </div>
      </div>
      """,
      unsafe_allow_html=True,
    )

    st.markdown(
      f"<p style='color: #888888; font-size: 0.75rem; margin-top: 0.5rem; text-align: right;'><i class='material-symbols-outlined' style='font-size:14px; vertical-align:middle; margin-right:4px; color:#6B7280;'>smart_toy</i> {model_name_fancy}</p>",
      unsafe_allow_html=True)

  st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

  # =============================
  # FANCY
  # -------------------------------
  st.markdown(
    """
    <h2 style='text-align: left;
          color:#1B5E20;
          font-size:25px;
          margin-bottom: 1rem;'>
      Provincial Regular Palay
    </h2>
    """,
    unsafe_allow_html=True
  )
  col1, col2 = st.columns([3, 1.2], gap="medium")

  with col1:

    # =========================
    # 2 tabs
    # =========================
    tab1, tab2 = st.tabs([
      ":material/show_chart: Price Trends",
      ":material/query_stats: Forecast Trends"
    ])

    # --------------------------------
    # HISTORICAL CHART
    # --------------------------------
    with tab1:

      if len(selected_years) == 1:

        hist_df = base_df[base_df["year"].isin(selected_years)].copy()

        fig_hist = px.line(
          hist_df,
          x="date",
          y="other_variety_price",
          markers=True,
          title=f"Provincial Regular Palay Price Trends ({selected_years[0]})",
          color_discrete_sequence=[CONFIG["colors"]["historical"]]
        )

      else:

        yearly = (
          base_df[base_df["year"].isin(selected_years)]
          .groupby("year")[["other_variety_price"]]
          .mean()
          .reset_index()
        )

        fig_hist = px.line(
          yearly,
          x="year",
          y="other_variety_price",
          markers=True,
          title=f"Provincial Regular Palay Price Trends ({min(selected_years)}–{max(selected_years)})",
          color_discrete_sequence=[CONFIG["colors"]["historical"]]
        )

      fig_hist.update_layout(
        yaxis_title=f"{CONFIG['currency']} / kg",
        xaxis_title="Timeline",
        font_size=11,
        title_font_size=21,
        title_font_color="#1B5E20",
        height=400,
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis=dict(
          tickprefix=CONFIG["currency"],
          separatethousands=True,
          gridcolor="rgba(0,0,0,0.05)"
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0.05)")
      )

      st.plotly_chart(fig_hist, use_container_width=True)

    # --------------------------------
    # FORECAST CHART
    # --------------------------------
    with tab2:

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
            "Forecast": CONFIG["colors"]["forecast"],
          },
          title=chart_title2,
        )

        fig.update_traces(
          selector=dict(name="Forecast"),
        )

      else:
        yearly = (
          base_df[base_df["year"].isin(selected_years)]
          .groupby("year")[["other_variety_price"]]
          .mean()
          .reset_index()
        )

        yearly["Type"] = "Historical"

        forecast_avg_regular = np.mean(forecast_variety_3months)

        forecast_yearly_r = pd.DataFrame(
          {
            "year": [latest["date"].year + 1],
            "other_variety_price": [forecast_avg_regular],
            "Type": ["Forecast"],
          }
        )

        combined_df = pd.concat([yearly, forecast_yearly_r])

        fig = px.line(
          combined_df,
          x="year",
          y="other_variety_price",
          color="Type",
          markers=True,
          color_discrete_map={
            "Historical": CONFIG["colors"]["historical"],
            "Forecast": CONFIG["colors"]["forecast"],
          },
          title=chart_title2,
        )

        fig.update_traces(
          line=dict(width=3, dash="dash"),
          selector=dict(name="Forecast"),
        )

      fig.update_layout(
        yaxis_title=f"{CONFIG['currency']} / kg",
        xaxis_title="Timeline",
        font_size=11,
        title_font_size=21,
        height=400,
        title_font_color="#1B5E20",
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis=dict(
          tickprefix=CONFIG["currency"],
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

    if len(selected_years) == 1:
      base_regular_price = base_df[base_df["year"] == selected_years[0]]["other_variety_price"].mean()
    else:
      base_regular_price = base_df[base_df["year"].isin(selected_years)]["other_variety_price"].mean()

    forecast_avg_r = np.mean(forecast_variety_3months)

    regular_change = 0 if base_regular_price == 0 else (
                                  (
                                      forecast_avg_r - base_regular_price) / base_regular_price
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

    st.markdown(
      f"""
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
          <span style='font-size: 1.3rem; font-weight: 800; color: {risk_color};'>{arrow} {regular_change:+.1f}%</span>
        </div>
        <div style='display: flex; justify-content: space-between; font-size: 0.85rem; border-top: 1px solid #f5f5f5; padding-top: 0.4rem;'>
          <span style='color: #888888;'>Hist. Avg:</span>
          <span style='font-weight: 600; color: #333333;'>₱{base_regular_price:.2f}</span>
        </div>
        <div style='display: flex; justify-content: space-between; font-size: 0.85rem;'>
          <span style='color: #888888;'>Forecast:</span>
          <span style='font-weight: 600; color: #333333;'>₱{forecast_avg_r:.2f}</span>
        </div>
      </div>
      """,
      unsafe_allow_html=True
    )

    st.markdown(
      f"<p style='color: #888888; font-size: 0.75rem; margin-top: 0.5rem; text-align: right;'><i class='material-symbols-outlined' style='font-size:14px; vertical-align:middle; margin-right:4px; color:#6B7280;'>smart_toy</i> {model_name_regular}</p>",
      unsafe_allow_html=True)

  st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

  # --------------------------------
  # MUNICIPALITY
  # --------------------------------
  st.markdown(
    """
    <h2 style='text-align: center;
          color:#1B5E20;
          font-weight:700;
          margin-bottom: 1.5rem;'>
      Municipal-Level Palay Prices 
    </h2>
    """,
    unsafe_allow_html=True
  )

  # =========================
  # FILTERS
  # =========================
  df_municipal_f = municipality_history_df.copy()
  
  # Drop rows with NaN municipality (these are summary/aggregated rows, not per-municipality data)
  df_municipal_f = df_municipal_f[df_municipal_f["municipality"].notna()].copy()
  
  # Convert month to title case for consistent display
  if "month" in df_municipal_f.columns:
    df_municipal_f["month"] = df_municipal_f["month"].str.title()
  
  filter1, filter2, filter3, filter4 = st.columns(4)

  # Rice Type (Hardcoded)
  with filter1:
    selected_type = st.selectbox(
      "Rice Type",
      options=["Dry", "Wet"]
    )

  # Rice Classification (Hardcoded)
  with filter2:
    selected_class = st.selectbox(
      "Rice Classification",
      options=[
        "Hybrid Premium",
        "Hybrid Ordinary",
        "Inbred Premium",
        "Inbred Ordinary"
      ]
    )

  # Year (Dynamic)
  year_list = sorted(
    df_municipal_f["year"].dropna().unique().tolist()
  )

  with filter3:
    selected_year = st.selectbox(
      "Year Selection",
      options=year_list
    )

  # Municipality (Dynamic)
  muni_list = sorted(
    df_municipal_f["municipality"].dropna().unique().tolist()
  )

  muni_list.insert(0, "All Municipalities")

  with filter4:
    selected_muni = st.selectbox(
      "Municipality Selection",
      options=muni_list
    )

  column_map = {
    ("Dry", "Hybrid Premium"): "hybridpremium_dry",
    ("Wet", "Hybrid Premium"): "hybridpremium_wet",

    ("Dry", "Hybrid Ordinary"): "hybridordinary_dry",
    ("Wet", "Hybrid Ordinary"): "hybridordinary_wet",

    ("Dry", "Inbred Premium"): "inbredpremium_dry",
    ("Wet", "Inbred Premium"): "inbredpremium_wet",

    ("Dry", "Inbred Ordinary"): "inbredordinary_dry",
    ("Wet", "Inbred Ordinary"): "inbredordinary_wet",
  }

  selected_column = column_map[(selected_type, selected_class)]

  # ==========================================
  # FILTER HISTORICAL DATA
  # ==========================================

  filtered_history = df_municipal_f.copy()

  filtered_history = filtered_history[
    filtered_history["year"] == selected_year
    ]

  if selected_muni != "All Municipalities":
    filtered_history = filtered_history[
      filtered_history["municipality"].str.upper() ==
      selected_muni.upper()
      ]

  # =========================
  # FILTER FORECAST DATA
  # =========================

  forecast = df_municipal_forecasts.copy()

  forecast = forecast[
    forecast["Rice Type & Season"] == selected_column
    ]

  if selected_muni != "All Municipalities":
    forecast = forecast[
      forecast["Municipality"].str.upper() ==
      selected_muni.upper()
      ]

  #TABABABABA
  tab1, tab2 = st.tabs([
    ":material/show_chart: Price Trends",
    ":material/query_stats: Forecast Trends"
  ])

  with tab1:

    title = (
      f"Historical {selected_class} ({selected_type}) Price Trends ({selected_year})"
    )

    municipality_colors = {
      "Abucay": "#1f77b4",
      "Bagac": "#ff7f0e",
      "Balanga": "#2ca02c",
      "Dinalupihan": "#d62728",
      "Hermosa": "#9467bd",
      "Limay": "#8c564b",
      "Mariveles": "#e377c2",
      "Morong": "#7f7f7f",
      "Orani": "#bcbd22",
      "Orion": "#17becf",
      "Pilar": "#ff9896",
      "Samal": "#98df8a",
    }

    if selected_muni != "All Municipalities":
      title += f" - {selected_muni}"
    else:
      title += " - All Municipalities"

    # Convert municipality names to title case to match color map
    filtered_history["municipality"] = filtered_history["municipality"].str.title()

    fig_hist = px.line(
      filtered_history,
      x="month",
      y=selected_column,
      color="municipality",
      color_discrete_map= municipality_colors,
      markers=True,
      title=title
    )

    fig_hist.update_xaxes(
      categoryorder="array",
      categoryarray=[
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
      ]
    )

    fig_hist.update_layout(
      xaxis_title="Month",
      yaxis_title="Price (₱/kg)",
      title_font_size=18,
      title_font_color="#1B5E20",
      plot_bgcolor="white",
      paper_bgcolor="white",
      height=500
    )

    st.plotly_chart(fig_hist, use_container_width=True)

  with tab2:

    forecast_long = forecast.melt(
      id_vars=["Municipality"],
      value_vars=["Month 1", "Month 2", "Month 3"],
      var_name="Forecast Month",
      value_name="Price"
    )

    forecast_long["Forecast Month"] = forecast_long["Forecast Month"].replace({
      "Month 1": municipal_month_labels[0],
      "Month 2": municipal_month_labels[1],
      "Month 3": municipal_month_labels[2],
    })
    
    # Convert municipality to title case for consistent display
    forecast_long["Municipality"] = forecast_long["Municipality"].str.title()

    title = f"Forecast {selected_class} ({selected_type}) Price Trends"

    if selected_muni != "All Municipalities":
      title += f" - {selected_muni}"
    else:
      title += " - All Municipalities"

    fig_forecast = px.line(
      forecast_long,
      x="Forecast Month",
      y="Price",
      color="Municipality",
      color_discrete_map=municipality_colors, # same colors as historical
      markers=True,
      title=title
    )

    fig_forecast.update_layout(
      xaxis_title="Month",
      yaxis_title="Price (₱/kg)",
      title_font_size=18,
      title_font_color="#1B5E20",
      plot_bgcolor="white",
      paper_bgcolor="white",
      height=500,
      legend_title="Municipality"
    )

    st.plotly_chart(fig_forecast, use_container_width=True)

  # ========================
  # MODEL ACCURACY (MODERNIZED)
  # =========================
  st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)
  st.markdown("<h3 style='color: #1B5E20; font-weight: 600; margin-bottom: 1rem;'>Model Performance</h3>",
        unsafe_allow_html=True)

  # Clean flat cards grid
  st.markdown(f"""
  <div style="
    background-color: var(--background-color, #ffffff);
    padding: 1.2rem; 
    border-radius: 12px; 
    border-top: 4px solid #388e3c;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 1.5rem;
  ">
    <div style="display: flex; flex-wrap: wrap; justify-content: space-around; gap: 1.5rem;">
      <div style="text-align: center; flex: 1; min-width: 140px;">
        <p style="margin:0; font-size: 0.9rem; font-weight: 700; color: #2E7D32;">Fancy Palay Pipeline</p>
        <div style="display: flex; justify-content: center; gap: 0.8rem; margin-top: 0.4rem; font-size: 0.85rem;">
          <span>MAE: <b>{mae_fancy:.2f}</b></span> • 
          <span>RMSE: <b>{rmse_fancy:.2f}</b></span> • 
          <span>R²: <b>{r2_fancy:.3f}</b></span>
        </div>
      </div>
      <div style="border-left: 1px solid #f0f0f0; height: 40px; display: inline-block;" class="hide-mobile"></div>
      <div style="text-align: center; flex: 1; min-width: 140px;">
        <p style="margin:0; font-size: 0.9rem; font-weight: 700; color: #558B2F;">Regular Palay Pipeline</p>
        <div style="display: flex; justify-content: center; gap: 0.8rem; margin-top: 0.4rem; font-size: 0.85rem;">
          <span>MAE: <b>{mae_regular:.2f}</b></span> • 
          <span>RMSE: <b>{rmse_regular:.2f}</b></span> • 
          <span>R²: <b>{r2_regular:.3f}</b></span>
        </div>
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

  _footer_banner(next_month_name, risk, risk_color="#1B5E20")