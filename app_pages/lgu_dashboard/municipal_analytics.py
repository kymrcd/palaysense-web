"""
PalaySense OPA Dashboard — Municipal Analytics
==============================================
Consolidates all municipality-related analytics into a single page.
Focuses on active municipal price forecasts and municipal yield analytics.

NOTE: The Provincial Yield Forecast component (Historical/Forecast quarterly
yield line chart + Yield Insight side-card) has been relocated to
provincial_analytics.py (Tab 2: Provincial Yield). The Municipal Yield tab
now shows strictly municipality-level yield metrics.

Municipal rice classifications are filtered granularly via dedicated
dropdowns (Rice Type = Hybrid/Inbred, Rice Classification = Premium/Ordinary)
rather than provincial Fancy/Regular labels.

The historical municipal PRICE trends have been moved to
historical_comparison.py (Tab 3: Municipal Price Trends).
"""
import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from . import theme

_MUNICIPALITY_COLORS = {
  # System-complementary palette - forest greens as base + muted harvest/water/earth accents
  # Greens from theme (DARK_GREEN #123524, PRIMARY #1E5C3A, PRIMARY_LIGHT #2E7D32)
  # Oranges/browns/blues are desaturated complements - not neon Plotly defaults
  "Abucay": "#123524",      # DARK_GREEN - forest base
  "Bagac": "#1E5C3A",        # PRIMARY
  "Balanga": "#2E7D32",      # PRIMARY_LIGHT
  "Dinalupihan": "#40916C",  # sage forest
  "Hermosa": "#81B29A",      # seafoam sage
  "Limay": "#E5A93C",        # amber / harvest gold - dry-season complement (theme amber)
  "Mariveles": "#D9822B",    # burnt orange - deeper harvest
  "Morong": "#8D6E63",       # earth brown - soil
  "Orani": "#A68A64",        # sand / clay
  "Orion": "#4A90A4",        # muted teal - water/irrigation
  "Pilar": "#5A7D9A",        # slate blue - cool complement
  "Samal": "#B56576",        # muted terracotta rose - warm accent
}

_MUNI_VARIETY_COLS = (
  "hybridpremium_dry", "hybridpremium_wet",
  "hybridordinary_dry", "hybridordinary_wet",
  "inbredpremium_dry", "inbredpremium_wet",
  "inbredordinary_dry", "inbredordinary_wet",
)

def _derive_municipal_columns(m):
  """Derive `palay_production`, `dry_season`, `wet_season` from the raw
  per-variety x season columns when they are missing from the municipal dataset
  (matches `data_layer._municipal_production_series` semantics)."""
  m = m.copy()
  available = [c for c in _MUNI_VARIETY_COLS if c in m.columns]
  if not available:
    return m
  if "palay_production" not in m.columns:
    m["palay_production"] = m[available].sum(axis=1, numeric_only=True)
  if "dry_season" not in m.columns:
    dry = [c for c in available if c.endswith("_dry")]
    if dry:
      m["dry_season"] = m[dry].sum(axis=1, numeric_only=True)
  if "wet_season" not in m.columns:
    wet = [c for c in available if c.endswith("_wet")]
    if wet:
      m["wet_season"] = m[wet].sum(axis=1, numeric_only=True)
  return m


def _primary_filters(dr):
  """Render granular municipal filters: Rice Type, Rice Classification, Year, Municipality.

  Returns (selected_class, selected_munis, selected_year) or None if unavailable.
  """
  df_forecast = getattr(dr, "df_municipal_forecasts", None)
  is_available = df_forecast is not None and not getattr(df_forecast, "empty", True)

  # Municipal Rice Type (Hybrid / Inbred) — NOT provincial Fancy/Regular
  rice_types = ["Hybrid", "Inbred"]
  # Municipal Rice Classifications (Premium / Ordinary) — dynamic per rice type
  class_options = ["Premium", "Ordinary"]

  # Municipality + Year options
  muni_list = []
  year_list = []
  if is_available:
    muni_list = sorted(df_forecast["Municipality"].dropna().unique().tolist())
  try:
    hist = dr.municipality_history_df
    if hist is not None and not getattr(hist, "empty", True):
      year_list = sorted(hist["year"].dropna().unique().tolist())
  except Exception:
    year_list = []

  # Inject scoped CSS so the filter labels use Plus Jakarta Sans and
  # blend seamlessly with the section card beneath them.
  st.markdown(
    """
    <style>
    /* Scoped to the municipal filter row only */
    .muni-filter-toolbar div[data-testid="stSelectbox"] label,
    .muni-filter-toolbar div[data-testid="stMultiSelect"] label {
      font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
      font-size: 0.72rem !important;
      font-weight: 600 !important;
      color: #6B7280 !important;
      letter-spacing: 0.3px !important;
    }
    .muni-filter-toolbar div[data-testid="stSelectbox"] > div,
    .muni-filter-toolbar div[data-testid="stMultiSelect"] > div {
      font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
      font-size: 0.78rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
  )

  # Compact one-line toolbar: Year | Rice Type | Classification | Municipalities
  with st.container():
    st.markdown('<div class="muni-filter-toolbar">', unsafe_allow_html=True)
    col_year, f1, f2, f4 = st.columns([0.9, 1, 1, 1.6], gap="small")
    with col_year:
      if year_list:
        selected_year = st.selectbox("Year", options=year_list, index=len(year_list) - 1, key="muni_year", label_visibility="visible")
      else:
        selected_year = None
        st.selectbox("Year", options=["N/A"], disabled=True, key="muni_year_na", label_visibility="visible")
    with f1:
      selected_rice_type = st.selectbox("Rice Type (Municipal)", options=rice_types, key="muni_rice_type")
    with f2:
      selected_class = st.selectbox("Rice Classification", options=[f"{selected_rice_type} {c}" for c in class_options], key="muni_rice_class")
    with f4:
      selected_munis = st.multiselect("Municipalities", options=muni_list, default=[], key="muni_munis", placeholder="All municipalities")
    st.markdown('</div>', unsafe_allow_html=True)

  return selected_class, selected_munis, selected_year


def _year_only_filter(dr, key="muni_year_simple"):
  """Render ONLY the Year filter in a compact single-column layout.

  Used by the high-level yield / production tabs where Rice Type,
  Rice Classification, and the Municipality multi-select are not
  applicable / redundant. ``key`` must be unique per invocation because
  native ``st.tabs`` renders every tab's content on each rerun.

  The dropdown is placed inside a ``st.columns([1, 4])`` row so it does
  not stretch awkwardly across the full screen width.
  """
  year_list = []
  try:
    hist = dr.municipality_history_df
    if hist is not None and not getattr(hist, "empty", True):
      year_list = sorted(hist["year"].dropna().unique().tolist())
  except Exception:
    year_list = []

  col_year, _ = st.columns([1, 4])
  with col_year:
    if year_list:
      selected_year = st.selectbox("Year", options=year_list,
                     index=len(year_list) - 1,
                     key=key, label_visibility="visible")
    else:
      selected_year = None
      st.selectbox("Year", options=["N/A"], disabled=True,
             key=f"{key}_na", label_visibility="visible")
  return selected_year


def _seasonal_info_tooltip():
  """Render a compact 'i' icon with a hover tooltip showing DA/PhilRice seasonal info.

  Replaces the previous always-visible st.info callout so the Dry/Wet season
  definitions only appear when the user hovers over the icon. Kept small so the
  Municipal Yield bar chart sits higher on the page.
  """
  st.markdown(
    """
    <style>
    .seasonal-tooltip { position: relative; display: inline-block; cursor: help; }
    .seasonal-tooltip .tooltip-text {
      visibility: hidden; width: 300px; background-color: #2b2b2b;
      color: #f5f5f5; text-align: left; border-radius: 6px; padding: 10px 12px;
      position: absolute; z-index: 1000; bottom: 130%; left: 50%;
      margin-left: -150px; font-size: 12px; line-height: 1.5;
      box-shadow: 0 4px 14px rgba(0,0,0,0.35); opacity: 0; transition: opacity 0.25s;
    }
    .seasonal-tooltip:hover .tooltip-text { visibility: visible; opacity: 1; }
    .seasonal-tooltip .tooltip-text::after {
      content: ""; position: absolute; top: 100%; left: 50%; margin-left: -6px;
      border-width: 6px; border-style: solid; border-color: #2b2b2b transparent transparent transparent;
    }
    </style>
    <div class="seasonal-tooltip">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:#E5A93C;color:#fff;"><i class="material-symbols-outlined" style="font-size:14px; line-height:1; color:#fff;">info</i></span>
      <span class="tooltip-text">
        <b><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:4px; color:#1B5E20;">agriculture</i> Cropping Seasons (DA / PhilRice)</b><br>
        <i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:4px; color:#F59E0B;">wb_sunny</i> <b>Dry Season:</b> Planted Nov–Dec | Harvested Mar–Apr
        (higher solar radiation, higher overall yield, irrigation-dependent).<br>
        <i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:4px; color:#2563EB;">water_drop</i> <b>Wet Season:</b> Planted May–Jul | Harvested Aug–Oct
        (prone to monsoon rains and typhoons, generally lower yield).
      </span>
    </div>
    """,
    unsafe_allow_html=True,
  )


def _render_municipal_crop_cycle_chart(df: pd.DataFrame, rice_type: str,
                    classification: str,
                    selected_municipalities: list):
  """
  Renders the actual 3-month municipal price forecast (Altair).

  Plots the real forecast values (Month 1-3 from ``df_municipal_forecasts``)
  for the user's Rice Type / Classification / Crop Cycle selection as a
  clustered bar chart: bars are grouped by forecast month on the X-axis,
  with each municipality offset side-by-side via the ``xOffset`` channel.
  The Y-axis uses ``alt.Scale(zero=False)`` with a tight domain (clamped
  around the min/max prices in the current selection) so small price
  changes in cents are visibly distinct. The X-axis is ordered by the
  actual forecast month labels contained in the uploaded dataset.
  """
  if df is None or df.empty:
    st.error(" Municipal forecast dataset is empty or unreadable.")
    return

  df = df.copy()
  # Standardize column headers to lowercase for safety
  df.columns = [str(col).lower() for col in df.columns]

  # 1. Municipality multi-select filter (empty selection = all municipalities)
  if selected_municipalities:
    selected_munis_lc = [str(m).lower() for m in selected_municipalities]
    df = df[df["municipality"].str.lower().isin(selected_munis_lc)]

  # 2. Interactive Crop Cycle Selector Dropdown — plain text (selectbox does not render :material: icons)
  selected_cycle = st.selectbox(
    "Select Crop Cycle to View:",
    ["☀️ Dry Season Crop Cycle", "🌧️ Wet Season Crop Cycle"],
    key=f"crop_cycle_picker_{rice_type}_{classification}",
  )

  st.write("---")

  # 3. Match the user's filters to the forecast row (e.g. hybridpremium_dry)
  base_key = f"{rice_type.lower()}{classification.lower()}".replace(" ", "")
  suffix = "_dry" if "Dry" in selected_cycle else "_wet"
  target_key = f"{base_key}{suffix}"

  type_col = "rice type & season"
  sub = df[df[type_col].str.lower() == target_key] if type_col in df.columns else pd.DataFrame()
  if sub.empty:
    st.warning(f"No forecast rows for '{target_key}' in the uploaded file.")
    return

  # 4. Dynamic forecast month labels + forecast year (from the uploaded file)
  label_map = {}
  for key, n in (("forecast_month_1_label", 1),
          ("forecast_month_2_label", 2),
          ("forecast_month_3_label", 3)):
    if key in sub.columns and sub[key].notna().any():
      label_map[f"month {n}"] = str(sub[key].iloc[0])
    else:
      label_map[f"month {n}"] = f"Month {n}"

  forecast_month_labels = [label_map[f"month {n}"] for n in range(1, 4)]
  forecast_year = next((int(str(label).split()[-1])
             for label in forecast_month_labels
             if str(label).split()[-1].isdigit()), 2026)

  # 5. Narrative per crop cycle — plain text to avoid :material: flash
  if "Dry" in selected_cycle:
    st.subheader(f"🌱 Dry Season Forecast: Mid to Late Harvesting Phase ({forecast_year})")
    st.caption(
      f" This tracks the price trend for palay planted late {forecast_year - 1}. "
      f"Peak harvesting happens from January to March {forecast_year}, "
      f"winding down completely by May {forecast_year}."
    )
  else:
    st.subheader(f"🌱 Wet Season Forecast: Overlapping Planting & Early Monsoon Harvest ({forecast_year})")
    st.caption(
      f" This tracks fields undergoing land preparation or planting from January to May {forecast_year}, "
      f"transitioning into wet season crop growth and heavy monsoon harvests "
      f"from June to December {forecast_year}."
    )

  # 6. Long-form data: one point per (forecast month, municipality)
  plot_df = (
    sub.melt(
      id_vars=["municipality"],
      value_vars=["month 1", "month 2", "month 3"],
      var_name="month_key",
      value_name="price",
    )
    .assign(forecast_month=lambda d: d["month_key"].map(label_map))
    .groupby(["forecast_month", "municipality"], as_index=False)["price"]
    .mean()
    .dropna(subset=["price"])
  )
  if plot_df.empty:
    st.info("No data available for the selected filters.")
    return

  # 7. Plotly grouped bar — compact, fits without scrolling
  plot_df["price"] = pd.to_numeric(plot_df["price"], errors="coerce")
  plot_df = plot_df.dropna(subset=["price"])
  if plot_df.empty:
    st.info("No price available for the selected filters.")
    return
  plot_df["municipality"] = plot_df["municipality"].astype(str).str.title()
  fig = px.bar(
    plot_df, x="forecast_month", y="price", color="municipality",
    barmode="group", text=plot_df["price"].round(2),
    category_orders={"forecast_month": forecast_month_labels},
    color_discrete_sequence=px.colors.qualitative.Set3,
    labels={"forecast_month": "Forecast Month", "price": "Price (₱/kg)", "municipality": "Municipality"},
    title=f"{rice_type} {classification} — {selected_cycle}",
  )
  fig.update_layout(
    height=340, margin=dict(t=35, b=120, l=45, r=10),
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Inter, sans-serif", size=11),
    legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="center", x=0.5, font=dict(size=10), bgcolor="rgba(255,255,255,0.95)", bordercolor="#E5E7EB", borderwidth=1),
    yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
    xaxis=dict(gridcolor="#F3F4F6", showgrid=False, automargin=True),
    title=dict(font=dict(size=13)),
    bargap=0.22, bargroupgap=0.10,
    uniformtext_minsize=8, uniformtext_mode="hide",
  )
  fig.update_traces(texttemplate=None, hovertemplate="Bayan: %{fullData.name}<br>%{x}<br>₱%{y:.2f}/kg<extra></extra>", cliponaxis=False)
  st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


# ------------------------------------------------------------------
# Historical Municipal Price — moved from Comparison > Municipal Price Trends
# Replaces the 3-month forecast that was incorrectly shown here.
# ------------------------------------------------------------------
_HIST_RICE_TYPE_PREFIX = {"Hybrid": "hybrid", "Inbred": "inbred"}
_HIST_RICE_CLASS_SUFFIX = {"Premium": "premium", "Ordinary": "ordinary"}
_HIST_SEASON_SUFFIX = {"Dry": "dry", "Wet": "wet"}


def _municipal_price_tab(dr):
  """Historical municipal PRICE trends — yearly bar / monthly drill-down.

  Data-science rule:
  * Multi-year selected (2+ years) -> grouped BAR chart of yearly mean price
    (fixes spaghetti/overplotting when 12 munis x 60 months are shown).
  * Single year selected -> clean monthly LINE chart (12 points per muni) if ≤2 munis, else BAR.

  Moved from historical_comparison.py Tab 3 so Analytics > Municipal >
  Municipal Prices shows HISTORY, while Forecast page shows forecasts.
  """
  with theme.section_card(title="Municipal Price Trends",
              desc="Historical municipal price trends by rice type, classification, and municipality.",
              icon_name="location_on"):
    muni_hist = getattr(dr, "municipality_history_df", None)
    if muni_hist is None or getattr(muni_hist, "empty", True):
      st.info("Municipal price history dataset not available.")
      return

    history = muni_hist.copy()
    history = history[history["municipality"].notna()].copy()
    if "month" in history.columns:
      history["month"] = history["month"].str.title()
    if "month_num" not in history.columns and "month" in history.columns:
      _mo = {m: i for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"], 1)}
      history["month_num"] = history["month"].map(_mo)

    # Filters — 5-column row to match previous Comparison layout
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
      selected_season = st.selectbox("Season", options=["Dry", "Wet"], key="muni_hist_season")
    with f2:
      selected_rice_type = st.selectbox("Rice Type", options=["Hybrid", "Inbred"], key="muni_hist_ricetype")
    with f3:
      selected_class = st.selectbox("Rice Classification", options=["Premium", "Ordinary"], key="muni_hist_class")
    with f4:
      year_list = sorted(history["year"].dropna().unique().tolist())
      _default_years = [2025] if 2025 in year_list else ([year_list[-1]] if year_list else [])
      selected_years = st.multiselect("Year Selection", options=year_list, default=_default_years, key="muni_hist_years")
    with f5:
      muni_list = sorted(history["municipality"].dropna().unique().tolist())
      _bal = next((m for m in muni_list if str(m).strip().lower() == "balanga city"), None)
      if _bal is None:
        _bal = next((m for m in muni_list if "balanga" in str(m).lower()), None)
      _default_munis = [_bal] if _bal else []
      selected_munis = st.multiselect("Municipality Selection", options=muni_list, default=_default_munis, key="muni_hist_munis")

    if not selected_years:
      st.info("Please select at least one year.")
      return

    selected_column = (
      f"{_HIST_RICE_TYPE_PREFIX[selected_rice_type]}"
      f"{_HIST_RICE_CLASS_SUFFIX[selected_class]}_{_HIST_SEASON_SUFFIX[selected_season]}"
    )

    filtered = history[history["year"].isin(selected_years)].copy()
    if selected_munis:
      filtered = filtered[filtered["municipality"].str.upper().isin([m.upper() for m in selected_munis])]

    if filtered.empty or selected_column not in filtered.columns:
      st.info("No data for the selected filters.")
      return

    filtered["municipality"] = filtered["municipality"].str.title()
    filtered[selected_column] = pd.to_numeric(filtered[selected_column], errors="coerce")
    filtered = filtered.dropna(subset=[selected_column])
    if filtered.empty:
      st.info("No valid price data for the selected filters.")
      return

    pretty_label = f"{selected_rice_type} {selected_class} ({selected_season} Season)"
    # global thin white download button style (visible as buttons)
    st.markdown("""<style>
    div[data-testid="stDownloadButton"] > button {
      background:white !important; color:#1B4332 !important; border:1px solid #D8EED8 !important;
      border-radius:8px !important; padding:4px 14px !important; font-size:0.82rem !important;
      font-weight:600 !important; box-shadow:0 1px 3px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stDownloadButton"] > button:hover { background:#F1F8E9 !important; border-color:#2D6A4F !important; }
    </style>""", unsafe_allow_html=True)

    # Effective municipality count (empty multiselect means All = 12)
    _effective_munis = selected_munis if selected_munis else muni_list
    _muni_count = len(_effective_munis)

    if len(selected_years) == 1:
      yr = selected_years[0]
      # Prepare CSV (export will be shown right below summary)
      _avg_tbl = filtered.groupby("municipality")[selected_column].mean().reset_index().sort_values(selected_column, ascending=False)
      _avg_tbl.columns = ["Municipality", "Avg Price (₱/kg)"]
      _avg_tbl["Avg Price (₱/kg)"] = _avg_tbl["Avg Price (₱/kg)"].round(2)
      _csv = _avg_tbl.to_csv(index=False).encode("utf-8")
      _fname = f"palaysense_municipal_price_{yr}_{selected_rice_type}_{selected_class}_{selected_season}.csv"
      if _muni_count <= 2:
        # --- single year + ≤2 muni: monthly LINE (readable, per-month) ---
        month_order = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        if "month_num" in filtered.columns:
          filtered = filtered.sort_values(["municipality", "month_num"])
        fig_hist = px.line(
          filtered, x="month", y=selected_column, color="municipality",
          color_discrete_map=_MUNICIPALITY_COLORS, markers=True,
        )
        fig_hist.update_xaxes(categoryorder="array", categoryarray=month_order)
        fig_hist.update_layout(
          xaxis_title="Month", yaxis_title="Price (₱/kg)",
          title=dict(text=f"{pretty_label} — {yr} Monthly Price (₱/kg)", font=dict(size=12, color="#123524")),
          plot_bgcolor="white", paper_bgcolor="white", height=340,
          hovermode="x unified", font=dict(family=theme.FONT, size=11),
          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
          yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
          margin=dict(t=30, b=30, l=40, r=20),
        )
        # side-by-side: chart + insight (insight right below summary export)
        col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart:
          st.plotly_chart(fig_hist, use_container_width=True, key="muni_hist_price_monthly")
        with col_insight:
          try:
            _is_single_muni = filtered["municipality"].nunique() == 1
            if _is_single_muni:
              _max_idx = filtered[selected_column].idxmax()
              _min_idx = filtered[selected_column].idxmin()
              _max_row = filtered.loc[_max_idx]
              _min_row = filtered.loc[_min_idx]
              _hi_m, _hi_v = str(_max_row["month"]), float(_max_row[selected_column])
              _lo_m, _lo_v = str(_min_row["month"]), float(_min_row[selected_column])
              _hi_label, _lo_label = "Peak Monthly Price:", "Lowest Monthly Price:"
              _hi_sub = f"{_hi_m} — ₱{_hi_v:.2f}/kg"
              _lo_sub = f"{_lo_m} — ₱{_lo_v:.2f}/kg"
            else:
              _overall = filtered.groupby("municipality")[selected_column].mean().sort_values(ascending=False)
              if _overall.empty:
                raise ValueError("empty")
              _hi_m, _hi_v = _overall.index[0], float(_overall.iloc[0])
              _lo_m, _lo_v = _overall.index[-1], float(_overall.iloc[-1])
              _hi_label, _lo_label = "Highest Average Price (Municipality):", "Lowest Average Price (Municipality):"
              _hi_sub, _lo_sub = f"{_hi_m} — ₱{_hi_v:.2f}/kg", f"{_lo_m} — ₱{_lo_v:.2f}/kg"
            _avg = float(filtered[selected_column].mean())
            _mm = filtered.groupby("month_num")[selected_column].mean().sort_index()
            if len(_mm) >= 2:
              _first, _last = float(_mm.iloc[0]), float(_mm.iloc[-1])
              _d = _last - _first
              if _d > 0.35:
                _t_text, _t_icon, _t_color = "INCREASING", "trending_up", "#1B4332"
              elif _d < -0.35:
                _t_text, _t_icon, _t_color = "DECREASING", "trending_down", "#DC2626"
              else:
                _t_text, _t_icon, _t_color = "STABLE", "trending_flat", "#6B7280"
            else:
              _t_text, _t_icon, _t_color = "STABLE", "trending_flat", "#6B7280"
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">insights</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem; letter-spacing:-0.2px;">Price Insight Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">{_hi_label}</span>
                    <b style="color:#1B4332; font-size:0.82rem;">{_hi_sub}</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#DC2626; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">{_lo_label}</span>
                    <b style="color:#DC2626; font-size:0.82rem;">{_lo_sub}</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">payments</i>
                  <span>Overall Mean Price:</span> <b style="color:#1B4332;">₱{_avg:.2f}/kg</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {yr} · {_effective_munis[0].title() if _is_single_muni else f"{_muni_count} Municipalities"}</div>
                <hr style="border:none; border-top:1px solid #D8EED8; margin:6px 0 3px 0;">
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:{_t_color}; font-size:14px;">{_t_icon}</i>
                  <span>Overall Price Trend:</span> <b style="color:{_t_color}; letter-spacing:0.3px;">{_t_text}</b>
                </div>
                <div style="font-size:0.68rem; color:#6B7280; margin-top:1px;">Based on monthly average prices across the year</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            # export right below summary — thin white
            st.download_button(
              label="⬇️ Export CSV",
              data=_csv,
              file_name=_fname,
              mime="text/csv",
              key=f"dl_muni_avg_after_{yr}_{selected_column}",
              use_container_width=True,
            )
          except Exception:
            pass
        st.markdown(f"<div style='text-align:center; font-size:0.72rem; color:#9CA3AF; font-style:italic; margin-top:6px;'>Monthly trend • {pretty_label} • {yr} — each point is monthly price per municipality</div>", unsafe_allow_html=True)
      else:
        # --- single year + >2 muni: BAR per municipality (yearly average, per-month only for ≤2 muni) ---
        _avg_sorted = _avg_tbl.sort_values("Avg Price (₱/kg)")
        fig_hist = px.bar(
          _avg_sorted, x="Municipality", y="Avg Price (₱/kg)",
          color="Municipality", color_discrete_map=_MUNICIPALITY_COLORS, text="Avg Price (₱/kg)",
        )
        fig_hist.update_traces(texttemplate="₱%{text:.2f}", textposition="outside", cliponaxis=False)
        fig_hist.update_layout(
          xaxis_title="Municipality", yaxis_title="Avg Price (₱/kg)",
          title=dict(text=f"{pretty_label} — {yr} Avg Price per Municipality (₱/kg)", font=dict(size=12, color="#123524")),
          plot_bgcolor="white", paper_bgcolor="white", height=340,
          hovermode="x unified", font=dict(family=theme.FONT, size=11),
          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
          yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(gridcolor="rgba(0,0,0,0.05)", tickangle=-25),
          margin=dict(t=30, b=60, l=40, r=20),
        )
        col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart:
          st.plotly_chart(fig_hist, use_container_width=True, key="muni_hist_price_bar_single")
        with col_insight:
          try:
            _overall = _avg_tbl.set_index("Municipality")["Avg Price (₱/kg)"].sort_values(ascending=False)
            _hi_m, _hi_v = _overall.index[0], float(_overall.iloc[0])
            _lo_m, _lo_v = _overall.index[-1], float(_overall.iloc[-1])
            _avg = float(_avg_tbl["Avg Price (₱/kg)"].mean())
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">insights</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem;">Price Insight Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Highest Average Price (Municipality):</span>
                    <b style="color:#1B4332; font-size:0.82rem;">{_hi_m} — ₱{_hi_v:.2f}/kg</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#DC2626; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Lowest Average Price (Municipality):</span>
                    <b style="color:#DC2626; font-size:0.82rem;">{_lo_m} — ₱{_lo_v:.2f}/kg</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">payments</i>
                  <span>Overall Mean Price:</span> <b style="color:#1B4332;">₱{_avg:.2f}/kg</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {yr} · {_muni_count} Municipalities</div>
                <hr style="border:none; border-top:1px solid #D8EED8; margin:6px 0 3px 0;">
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#6B7280; font-size:14px;">bar_chart</i>
                  <span>Display Mode:</span> <b style="color:#1B4332;">Yearly Average Price per Municipality (Bar Chart)</b>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.download_button(
              label="⬇️ Export CSV",
              data=_csv,
              file_name=_fname,
              mime="text/csv",
              key=f"dl_muni_avg_after_bar_{yr}_{selected_column}",
              use_container_width=True,
            )
          except Exception:
            pass
        st.markdown(f"<div style='text-align:center; font-size:0.72rem; color:#9CA3AF; font-style:italic; margin-top:6px;'>Yearly average • {pretty_label} • {yr} — each bar = municipality yearly mean (12 months)</div>", unsafe_allow_html=True)
    else:
      # --- MULTI-YEAR: yearly grouped bar chart (also for 2 munis + multi-year per request) ---
      yearly = (
        filtered.groupby(["municipality", "year"], as_index=False)[selected_column]
        .mean().rename(columns={selected_column: "avg_price"})
      )
      yearly["year_str"] = yearly["year"].astype(str)
      yearly = yearly.sort_values(["year", "municipality"])
      _pivot = yearly.pivot(index="municipality", columns="year_str", values="avg_price").round(2)
      try:
        _pivot = _pivot.reindex(sorted(_pivot.columns, key=lambda x: int(x)), axis=1)
      except Exception:
        pass
      _pivot_csv_df = _pivot.reset_index()
      _pivot_csv = _pivot_csv_df.to_csv(index=False).encode("utf-8")
      _show = yearly[["municipality", "year", "avg_price"]].copy()
      _show.columns = ["Municipality", "Year", "Avg Price (₱/kg)"]
      _show["Avg Price (₱/kg)"] = _show["Avg Price (₱/kg)"].round(2)
      _show = _show.sort_values(["Year", "Municipality"])
      _long_csv = _show.to_csv(index=False).encode("utf-8")
      _years_tag = "-".join(map(str, sorted(selected_years)))
      _base = f"{selected_rice_type}_{selected_class}_{selected_season}_{_years_tag}".replace(" ", "_")
      total_bars = len(yearly)
      fig_hist = px.bar(
        yearly, x="year_str", y="avg_price", color="municipality",
        barmode="group", color_discrete_map=_MUNICIPALITY_COLORS, text="avg_price",
        labels={"year_str": "Year", "avg_price": "Avg Price (₱/kg)", "municipality": "Municipality"},
      )
      fig_hist.update_traces(texttemplate="₱%{text:.1f}", textposition="outside", cliponaxis=False)
      chart_h = 340 if total_bars <= 40 else 400
      fig_hist.update_layout(
        title=dict(text=f"{pretty_label} — Yearly Average Price (₱/kg) by Municipality", font=dict(size=12, color="#123524")),
        yaxis_title="Avg Price (₱/kg)", xaxis_title="Year",
        plot_bgcolor="white", paper_bgcolor="white", height=chart_h,
        hovermode="x unified", font=dict(family=theme.FONT, size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.06)", range=[max(0, yearly["avg_price"].min() - 1), yearly["avg_price"].max() + 1]),
        xaxis=dict(gridcolor="rgba(0,0,0,0.05)", type="category"),
        margin=dict(t=30, b=30, l=40, r=20), bargap=0.22, bargroupgap=0.08,
      )
      col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
      with col_chart:
        st.plotly_chart(fig_hist, use_container_width=True, key="muni_hist_price_yearly")
      with col_insight:
        try:
          overall = yearly.groupby("municipality")["avg_price"].mean().sort_values(ascending=False)
          if not overall.empty:
            hi_m, hi_v = overall.index[0], overall.iloc[0]
            lo_m, lo_v = overall.index[-1], overall.iloc[-1]
            avg_price = float(yearly["avg_price"].mean())
            _ym = yearly.groupby("year")["avg_price"].mean().sort_index()
            if len(_ym) >= 2:
              _first, _last = float(_ym.iloc[0]), float(_ym.iloc[-1])
              _diff = _last - _first
              if _diff > 0.35:
                trend_text, trend_icon, trend_color = "INCREASING", "trending_up", "#1B4332"
              elif _diff < -0.35:
                trend_text, trend_icon, trend_color = "DECREASING", "trending_down", "#DC2626"
              else:
                trend_text, trend_icon, trend_color = "STABLE", "trending_flat", "#6B7280"
            else:
              trend_text, trend_icon, trend_color = "STABLE", "trending_flat", "#6B7280"
            years_lbl = ", ".join(map(str, sorted(selected_years)))
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">insights</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem; letter-spacing:-0.2px;">Price Insight Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:4px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px;">emoji_events</i>
                  <span>Highest Average Price (Municipality):</span> <b style="color:#1B4332;">{hi_m}<br>₱{hi_v:.2f}/kg</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#DC2626; font-size:14px;">trending_down</i>
                  <span>Lowest Average Price (Municipality):</span> <b style="color:#DC2626;">{lo_m}<br>₱{lo_v:.2f}/kg</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">payments</i>
                  <span>Overall Mean Price:</span> <b style="color:#1B4332;">₱{avg_price:.2f}/kg</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Years: {years_lbl}</div>
                <hr style="border:none; border-top:1px solid #D8EED8; margin:6px 0 3px 0;">
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:{trend_color}; font-size:14px;">{trend_icon}</i>
                  <span>Overall Price Trend:</span> <b style="color:{trend_color}; letter-spacing:0.3px;">{trend_text}</b>
                </div>
                <div style="font-size:0.68rem; color:#6B7280;">Price trend pattern across the selected years</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            # export right below summary — thin white (multi-year) — inside col_insight
            st.download_button(
              label="⬇️ Pivot CSV",
              data=_pivot_csv,
              file_name=f"palaysense_municipal_price_pivot_{_base}.csv",
              mime="text/csv",
              key=f"dl_muni_pivot_after_{_base}",
              use_container_width=True,
            )
            st.download_button(
              label="⬇️ Long CSV",
              data=_long_csv,
              file_name=f"palaysense_municipal_price_long_{_base}.csv",
              mime="text/csv",
              key=f"dl_muni_long_after_{_base}",
              use_container_width=True,
            )
          else:
            st.info("No insight data.")
        except Exception:
          pass
      st.markdown(f"<div style='text-align:center; font-size:0.72rem; color:#9CA3AF; font-style:italic; margin-top:6px;'>Yearly average • {pretty_label} • Years {_years_tag} — each bar = mean of 12 monthly prices</div>", unsafe_allow_html=True)


def _seasonal_distribution_pies(dr):
  """Dry vs Wet seasonal production distribution (pie charts)."""
  with theme.section_card(title="Seasonal Production Distribution",
              desc="Dry vs Wet season production split across municipalities.",
              icon_name="pie_chart"):
    # Filter rendered INSIDE the section card (compact Year dropdown).
    selected_year = _year_only_filter(dr, key="muni_year_season")

    muni = getattr(dr, "municipal_production_df", None)
    if muni is None or getattr(muni, "empty", True):
      muni = getattr(dr, "municipality_df", None)
    if muni is None or getattr(muni, "empty", True):
      st.info("Seasonal production dataset not available.")
      return

    m = _derive_municipal_columns(muni)
    if "dry_season" not in m.columns:
      st.info("Seasonal production dataset not available.")
      return

    m["date"] = pd.to_datetime(m["date"])
    m["year"] = m["date"].dt.year
    if selected_year is not None:
      m = m[m["year"] == selected_year]

    if m.empty:
      st.info("No seasonal data for the selected year.")
      return

    year_label = f"({selected_year})" if selected_year is not None else ""

    def _by_muni(col):
      return (
        m.groupby("municipality")[col].sum().reset_index()
        .sort_values(col, ascending=False)
      )

    dry = _by_muni("dry_season") if "dry_season" in m.columns else pd.DataFrame()
    wet = _by_muni("wet_season") if "wet_season" in m.columns else pd.DataFrame()

    # Toggle: Dry vs Wet — segmented control (fallback to tabs)
    tab_dry, tab_wet = st.tabs(["☀️ Dry Season", "🌧️ Wet Season"])

    with tab_dry:
      if not dry.empty:
        d_total = float(dry["dry_season"].sum())
        d_hi = dry.iloc[0] if not dry.empty else None
        d_lo = dry.iloc[-1] if not dry.empty else None
        fig = px.pie(dry, names="municipality", values="dry_season",
               color="municipality", color_discrete_map=_MUNICIPALITY_COLORS)
        fig.update_traces(textposition="inside", textinfo="percent", hovertemplate="%{label}<br>%{value:,.0f} MT (%{percent})<extra></extra>", marker=dict(line=dict(color="white", width=1.5)))
        fig.update_layout(title=dict(text=f"☀️ Dry Season {year_label}", x=0.5, xanchor="center", font=dict(size=13, color="#B45309")), height=380, margin=dict(t=50, b=40, l=20, r=20), showlegend=True, legend=dict(orientation="h", y=-0.1, font=dict(size=9)))
        col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart:
          st.plotly_chart(fig, use_container_width=True, key="muni_dry_pie")
        with col_insight:
          try:
            _hi_m, _hi_v = str(d_hi["municipality"]), float(d_hi["dry_season"])
            _lo_m, _lo_v = str(d_lo["municipality"]), float(d_lo["dry_season"])
            _avg = float(dry["dry_season"].mean())
            _hi_pct = (_hi_v / d_total * 100) if d_total else 0
            st.markdown(f"""
            <div style="background:#FFF8E1; border-left:4px solid #E5A93C; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#B45309; font-size:16px; line-height:1;">wb_sunny</i>
                <span style="font-weight:800; color:#78350F; font-size:0.85rem;">Dry Season Production Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Top Producing Municipality:</span>
                    <b style="color:#78350F; font-size:0.82rem;">{_hi_m} — {_hi_v:,.0f} MT ({_hi_pct:.1f}%)</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#6B7280; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Lowest Producing Municipality:</span>
                    <b style="color:#6B7280; font-size:0.82rem;">{_lo_m} — {_lo_v:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px;">analytics</i>
                  <span>Total Dry Season Production:</span> <b style="color:#78350F;">{d_total:,.0f} MT</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px;">functions</i>
                  <span>Mean Production per Municipality:</span> <b>{_avg:,.0f} MT</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #FDE68A; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {selected_year if selected_year else "All Years"} · {len(dry)} Municipalities</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
          except Exception:
            pass
      else:
        st.info("No dry season data.")

    with tab_wet:
      if not wet.empty:
        w_total = float(wet["wet_season"].sum())
        w_hi = wet.iloc[0] if not wet.empty else None
        w_lo = wet.iloc[-1] if not wet.empty else None
        fig = px.pie(wet, names="municipality", values="wet_season",
               color="municipality", color_discrete_map=_MUNICIPALITY_COLORS)
        fig.update_traces(textposition="inside", textinfo="percent", hovertemplate="%{label}<br>%{value:,.0f} MT (%{percent})<extra></extra>", marker=dict(line=dict(color="white", width=1.5)))
        fig.update_layout(title=dict(text=f"🌧️ Wet Season {year_label}", x=0.5, xanchor="center", font=dict(size=13, color="#2D6A4F")), height=380, margin=dict(t=50, b=40, l=20, r=20), showlegend=True, legend=dict(orientation="h", y=-0.1, font=dict(size=9)))
        col_chart2, col_insight2 = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart2:
          st.plotly_chart(fig, use_container_width=True, key="muni_wet_pie")
        with col_insight2:
          try:
            _hi_m, _hi_v = str(w_hi["municipality"]), float(w_hi["wet_season"])
            _lo_m, _lo_v = str(w_lo["municipality"]), float(w_lo["wet_season"])
            _avg = float(wet["wet_season"].mean())
            _hi_pct = (_hi_v / w_total * 100) if w_total else 0
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">water_drop</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem;">Wet Season Production Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Top Producing Municipality:</span>
                    <b style="color:#1B4332; font-size:0.82rem;">{_hi_m} — {_hi_v:,.0f} MT ({_hi_pct:.1f}%)</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#6B7280; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Lowest Producing Municipality:</span>
                    <b style="color:#6B7280; font-size:0.82rem;">{_lo_m} — {_lo_v:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">analytics</i>
                  <span>Total Wet Season Production:</span> <b style="color:#1B4332;">{w_total:,.0f} MT</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">functions</i>
                  <span>Mean Production per Municipality:</span> <b>{_avg:,.0f} MT</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {selected_year if selected_year else "All Years"} · {len(wet)} Municipalities</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
          except Exception:
            pass
      else:
        st.info("No wet season data.")


def _municipal_yield_tab(dr):
  """Municipal-level yield analytics with seasonal comparison.

  Renders a compact DA/PhilRice seasonal context tooltip, a compact Year
  filter, and three season sub-tabs (Both Seasons / Dry Season / Wet Season)
  with grouped/single Plotly bar charts per municipality — all inside one
  section card. No raw data table is rendered.
  """
  with theme.section_card(title="Municipal Yield Analytics",
              desc="Yield & production comparison across Bataan municipalities by season",
              icon_name="eco"):
    # -------
    # 1. COMPACT CALLOUT — DA / PhilRice seasonal definitions (hover tooltip)
    # -------
    _seasonal_info_tooltip()

    # Prefer authoritative production dataset (dry_season/wet_season), fallback to price history with derived totals
    muni = getattr(dr, "municipal_production_df", None)
    if muni is None or getattr(muni, "empty", True):
      muni = getattr(dr, "municipality_df", None)
    if muni is None or getattr(muni, "empty", True):
      st.info("Municipality yield dataset not available.")
      return

    # 2. COMPACT YEAR FILTER (inside the card, single column) — year list from actual muni source
    # Build year list from muni itself (production 2019-2025, not history 2015-2025) so dropdown only shows valid years
    _yl = []
    try:
      _tmp = muni.copy()
      if "date" in _tmp.columns:
        _tmp["date"] = pd.to_datetime(_tmp["date"], errors="coerce")
        _yl = sorted(_tmp["date"].dt.year.dropna().astype(int).unique().tolist())
      elif "year" in _tmp.columns:
        _yl = sorted(pd.to_numeric(_tmp["year"], errors="coerce").dropna().astype(int).unique().tolist())
    except Exception:
      _yl = []
    if _yl:
      col_year, _ = st.columns([1, 4])
      with col_year:
        selected_year = st.selectbox("Year", options=_yl, index=len(_yl)-1, key="muni_year_yield", label_visibility="visible")
    else:
      selected_year = _year_only_filter(dr, key="muni_year_yield")

    m = _derive_municipal_columns(muni)
    # Normalize date/year for filtering (production df has year col + date; history has monthly date)
    if "date" in m.columns:
      m["date"] = pd.to_datetime(m["date"], errors="coerce")
      m["_year"] = m["date"].dt.year
    elif "year" in m.columns:
      m["_year"] = pd.to_numeric(m["year"], errors="coerce").astype("Int64")
    else:
      m["_year"] = pd.NA

    # Optional year filter
    if selected_year is not None:
      m = m[m["_year"] == selected_year]

    if m.empty:
      st.info("No municipal yield data for the selected year.")
      return

    # Aggregate per-municipality production by season
    agg_cols = []
    for col in ["dry_season", "wet_season", "palay_production"]:
      if col in m.columns:
        agg_cols.append(col)

    if not agg_cols:
      st.info("No seasonal yield columns available in municipal dataset.")
      return

    summary = m.groupby("municipality", as_index=False)[agg_cols].sum()
    summary = summary.sort_values("palay_production", ascending=False) if "palay_production" in summary.columns else summary.sort_values("municipality")

    # ------------------------------------------------------------
    # 2. SEASON SUB-TABS ABOVE THE CHART
    # ------------------------------------------------------------
    # Scoped CSS: green Material Symbols icons on the 3 season sub-tabs.
    # `:has(button[role="tab"]:nth-child(3))` targets ONLY this 3-tab
    # group so the 2-tab Municipal Price forecast tabs are unaffected.
    st.markdown(
      """
      <style>
      div[data-testid="stTabs"]:has(button[role="tab"]:nth-child(3)) button[role="tab"] {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        color: #1B4332;
      }
      div[data-testid="stTabs"]:has(button[role="tab"]:nth-child(3)) button[role="tab"][aria-selected="true"] {
        color: #2D6A4F;
        border-bottom: 2px solid #2D6A4F;
      }
      div[data-testid="stTabs"]:has(button[role="tab"]:nth-child(3)) button[role="tab"]::before {
        font-family: 'Material Symbols Outlined';
        font-weight: normal;
        font-size: 1.1rem;
        vertical-align: middle;
        margin-right: 6px;
        color: #2D6A4F;
      }
      div[data-testid="stTabs"]:has(button[role="tab"]:nth-child(3)) button[role="tab"]:nth-child(1)::before { content: 'grid_view'; }
      div[data-testid="stTabs"]:has(button[role="tab"]:nth-child(3)) button[role="tab"]:nth-child(2)::before { content: 'wb_sunny'; }
      div[data-testid="stTabs"]:has(button[role="tab"]:nth-child(3)) button[role="tab"]:nth-child(3)::before { content: 'water_drop'; }
      </style>
      """,
      unsafe_allow_html=True,
    )

    has_dry = "dry_season" in summary.columns
    has_wet = "wet_season" in summary.columns

    tab_both, tab_dry, tab_wet = st.tabs([
      "Both Seasons",
      "Dry Season",
      "Wet Season",
    ])

    # Clean color mapping
    DRY_COLOR = "#E5A93C"  # Gold/Amber
    WET_COLOR = "#2D6A4F"  # Deep Green
    LAYOUT_MARGINS = dict(t=30, b=40, l=40, r=40)

    def _bar_layout(fig, x_title, y_title):
      fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=theme.FONT, size=12),
        margin=LAYOUT_MARGINS,
      )
      return fig

    # ------------------------------------------------------------
    # 3. PLOTLY BAR CHARTS + SIDE INSIGHTS
    # ------------------------------------------------------------
    with tab_both:
      if has_dry and has_wet:
        melted = summary.melt(
          id_vars="municipality",
          value_vars=["dry_season", "wet_season"],
          var_name="Season",
          value_name="Production (MT)",
        )
        melted["Season"] = melted["Season"].map({
          "dry_season": "Dry Season",
          "wet_season": "Wet Season",
        })
        fig = px.bar(
          melted,
          x="municipality",
          y="Production (MT)",
          color="Season",
          barmode="group",
          color_discrete_map={
            "Dry Season": DRY_COLOR,
            "Wet Season": WET_COLOR,
          },
          text="Production (MT)",
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside", marker_cornerradius=8)
        fig = _bar_layout(fig, "Municipality", "Production (MT)")
        fig.update_layout(showlegend=True, margin=LAYOUT_MARGINS)
        col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart:
          st.plotly_chart(fig, use_container_width=True, key="muni_yield_both")
        with col_insight:
          try:
            _total = summary["palay_production"].sum() if "palay_production" in summary.columns else summary[["dry_season","wet_season"]].sum().sum()
            _dry_total = float(summary["dry_season"].sum())
            _wet_total = float(summary["wet_season"].sum())
            _hi = summary.sort_values("palay_production", ascending=False).iloc[0] if "palay_production" in summary.columns else summary.iloc[0]
            _lo = summary.sort_values("palay_production", ascending=False).iloc[-1] if "palay_production" in summary.columns else summary.iloc[-1]
            _hi_m = str(_hi["municipality"]); _hi_v = float(_hi["palay_production"]) if "palay_production" in summary.columns else float(_hi["dry_season"]+_hi["wet_season"])
            _lo_m = str(_lo["municipality"]); _lo_v = float(_lo["palay_production"]) if "palay_production" in summary.columns else float(_lo["dry_season"]+_lo["wet_season"])
            _avg = float(summary["palay_production"].mean()) if "palay_production" in summary.columns else float(_total/len(summary))
            _dom = "Dry" if _dry_total > _wet_total else "Wet" if _wet_total > _dry_total else "Even"
            _dom_color = "#B45309" if _dom=="Dry" else "#2D6A4F" if _dom=="Wet" else "#6B7280"
            _gap = abs(_dry_total - _wet_total)
            _gap_pct = (_gap / _total * 100) if _total else 0
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">insights</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem;">Combined Seasonal Production Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Highest Total Production:</span>
                    <b style="color:#1B4332; font-size:0.82rem;">{_hi_m} — {_hi_v:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#DC2626; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Lowest Total Production:</span>
                    <b style="color:#DC2626; font-size:0.82rem;">{_lo_m} — {_lo_v:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">analytics</i>
                  <span>Mean Production per Municipality:</span> <b style="color:#1B4332;">{_avg:,.0f} MT</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:{_dom_color}; font-size:14px;">compare</i>
                  <span>Dominant Season:</span> <b style="color:{_dom_color};">{_dom} Season (+{_gap:,.0f} MT, {_gap_pct:.1f}%)</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {selected_year} · Dry Season: { _dry_total:,.0f} MT | Wet Season: { _wet_total:,.0f} MT</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
          except Exception:
            pass
      else:
        st.info("Dry / Wet season data not available for both seasons.")

    with tab_dry:
      if has_dry:
        fig = px.bar(
          summary,
          x="municipality",
          y="dry_season",
          color_discrete_sequence=[DRY_COLOR],
          text=summary["dry_season"],
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside", marker_cornerradius=8)
        fig = _bar_layout(fig, "Municipality", "Dry Season Production (MT)")
        col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart:
          st.plotly_chart(fig, use_container_width=True, key="muni_yield_dry")
        with col_insight:
          try:
            _s = summary.sort_values("dry_season", ascending=False)
            _hi_m, _hi_v = str(_s.iloc[0]["municipality"]), float(_s.iloc[0]["dry_season"])
            _lo_m, _lo_v = str(_s.iloc[-1]["municipality"]), float(_s.iloc[-1]["dry_season"])
            _avg = float(summary["dry_season"].mean())
            _total = float(summary["dry_season"].sum())
            _hi_pct = (_hi_v / _total * 100) if _total else 0
            st.markdown(f"""
            <div style="background:#FFF8E1; border-left:4px solid #E5A93C; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#B45309; font-size:16px; line-height:1;">wb_sunny</i>
                <span style="font-weight:800; color:#78350F; font-size:0.85rem;">Dry Season Production Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Top Producing Municipality:</span>
                    <b style="color:#78350F; font-size:0.82rem;">{_hi_m} — {_hi_v:,.0f} MT ({_hi_pct:.1f}%)</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#6B7280; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Lowest Producing Municipality:</span>
                    <b style="color:#6B7280; font-size:0.82rem;">{_lo_m} — {_lo_v:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px;">analytics</i>
                  <span>Mean Dry Season Production:</span> <b>{_avg:,.0f} MT</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px;">agriculture</i>
                  <span>Total Dry Season Production:</span> <b style="color:#78350F;">{_total:,.0f} MT</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #FDE68A; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {selected_year} · {len(summary)} Municipalities</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
          except Exception:
            pass
      else:
        st.info("Dry Season data not available.")

    with tab_wet:
      if has_wet:
        fig = px.bar(
          summary,
          x="municipality",
          y="wet_season",
          color_discrete_sequence=[WET_COLOR],
          text=summary["wet_season"],
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside", marker_cornerradius=8)
        fig = _bar_layout(fig, "Municipality", "Wet Season Production (MT)")
        col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
        with col_chart:
          st.plotly_chart(fig, use_container_width=True, key="muni_yield_wet")
        with col_insight:
          try:
            _s = summary.sort_values("wet_season", ascending=False)
            _hi_m, _hi_v = str(_s.iloc[0]["municipality"]), float(_s.iloc[0]["wet_season"])
            _lo_m, _lo_v = str(_s.iloc[-1]["municipality"]), float(_s.iloc[-1]["wet_season"])
            _avg = float(summary["wet_season"].mean())
            _total = float(summary["wet_season"].sum())
            _hi_pct = (_hi_v / _total * 100) if _total else 0
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">water_drop</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem;">Wet Season Production Summary</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Top Producing Municipality:</span>
                    <b style="color:#1B4332; font-size:0.82rem;">{_hi_m} — {_hi_v:,.0f} MT ({_hi_pct:.1f}%)</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#6B7280; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.75rem; color:#6B7280;">Lowest Producing Municipality:</span>
                    <b style="color:#6B7280; font-size:0.82rem;">{_lo_m} — {_lo_v:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">analytics</i>
                  <span>Mean Wet Season Production:</span> <b>{_avg:,.0f} MT</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">agriculture</i>
                  <span>Total Wet Season Production:</span> <b style="color:#1B4332;">{_total:,.0f} MT</b>
                </div>
                <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {selected_year} · {len(summary)} Municipalities</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
          except Exception:
            pass
      else:
        st.info("Wet Season data not available.")

def render(df, dr):
  """Main Municipal Analytics page with tabbed sub-views."""
  if dr is None or not getattr(dr, "has_provincial_data", False):
      st.info("No municipal data — municipal analytics hidden (0 values). Provincial data required. Upload via Import Data.")
      return
  theme.page_title("Municipal Analytics",
           "Municipality-level price and yield analytics.")

  tab1, tab2, tab3 = st.tabs([
    ":material/payments: Municipal Prices",
    ":material/eco: Municipal Yield",
    ":material/eco: Seasonal Distribution",
  ])

  with tab1:
    _municipal_price_tab(dr)

  with tab2:
    _municipal_yield_tab(dr)

  with tab3:
    _seasonal_distribution_pies(dr)