"""
PalaySense LGU Dashboard — Municipal Analytics
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
  "Abucay": "#1f77b4", "Bagac": "#ff7f0e", "Balanga": "#2ca02c",
  "Dinalupihan": "#d62728", "Hermosa": "#9467bd", "Limay": "#8c564b",
  "Mariveles": "#e377c2", "Morong": "#7f7f7f", "Orani": "#bcbd22",
  "Orion": "#17becf", "Pilar": "#ff9896", "Samal": "#98df8a",
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

  # Compact top toolbar: Year dropdown takes only ~20-25% of the width.
  with st.container():
    st.markdown('<div class="muni-filter-toolbar">', unsafe_allow_html=True)
    col_year, _ = st.columns([1, 4])
    with col_year:
      if year_list:
        selected_year = st.selectbox("Year",
                       options=year_list,
                       index=len(year_list) - 1,
                       key="muni_year",
                       label_visibility="visible")
      else:
        selected_year = None
        st.selectbox("Year", options=["N/A"], disabled=True,
               key="muni_year_na", label_visibility="visible")

    # Remaining filters in a 3-column row beneath the Year toolbar.
    f1, f2, f4 = st.columns(3)
    with f1:
      selected_rice_type = st.selectbox("Rice Type (Municipal)",
                       options=rice_types, key="muni_rice_type")
    with f2:
      selected_class = st.selectbox(
        "Rice Classification",
        options=[f"{selected_rice_type} {c}" for c in class_options],
        key="muni_rice_class",
      )
    with f4:
      selected_munis = st.multiselect("Municipalities", options=muni_list,
                      default=[], key="muni_munis")
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

  # 2. Interactive Crop Cycle Selector Dropdown
  selected_cycle = st.selectbox(
    "Piliin ang Agrikultural na Siklo (Crop Cycle) na Nais Tingnan:",
    [":material/wb_sunny: Dry Season Crop Cycle", ":material/water_drop: Wet Season Crop Cycle"],
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

  # 5. Narrative per crop cycle
  if "Dry" in selected_cycle:
    st.subheader(
      f":material/agriculture: Dry Season Forecast: Mid to Late Harvesting Phase ({forecast_year})"
    )
    st.caption(
      f" This tracks the price trend for palay planted late {forecast_year - 1}. "
      f"Peak harvesting happens from January to March {forecast_year}, "
      f"winding down completely by May {forecast_year}."
    )
  else:
    st.subheader(
      f":material/agriculture: Wet Season Forecast: Overlapping Planting & Early Monsoon Harvest ({forecast_year})"
    )
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

  # 7. Altair clustered bar chart — zoomed Y-axis (zero=False) + tight
  #  domain around the min/max prices in the active selection so that
  #  changes in cents are visibly distinct.
  price_min = plot_df["price"].min()
  price_max = plot_df["price"].max()
  price_pad = max((price_max - price_min) * 0.08, 0.05)
  y_domain = [price_min - price_pad, price_max + price_pad]

  chart = (
    alt.Chart(plot_df)
    .mark_bar()
    .encode(
      x=alt.X("forecast_month:N", title="Forecast Month",
          sort=forecast_month_labels),
      xOffset="municipality:N",
      y=alt.Y("price:Q", title="Price (₱/kg)",
          scale=alt.Scale(zero=False, domain=y_domain)),
      color=alt.Color("municipality:N",
              legend=alt.Legend(title="Municipality")),
      tooltip=[
        "forecast_month:N",
        "municipality:N",
        alt.Tooltip("price:Q", title="Price (₱/kg)", format=".2f"),
      ],
    )
    .properties(height=400,
          title=f"{rice_type} {classification} — {selected_cycle}")
  )
  st.altair_chart(chart, use_container_width=True)


def _municipal_price_tab(dr):
  """Active municipal price forecast line chart filtered by
  municipal rice classification + single year + municipality."""
  with theme.section_card(title="Municipal Price Forecast",
              desc="Per-municipality palay price forecasts by rice variety and season.",
              icon_name="location_on"):
    # Filters rendered INSIDE the section card (below the header).
    selected_class, selected_munis, selected_year = _primary_filters(dr)
    if selected_class is None:
      st.info("Municipal forecast dataset not available.")
      return

    df_forecast = getattr(dr, "df_municipal_forecasts", None)
    if df_forecast is None or getattr(df_forecast, "empty", True):
      st.info("Municipal forecast dataset not available yet. "
          "Run the background pipeline to generate municipal price forecasts.")
      return

    # Actual 3-month forecast line chart connected to the user's filters.
    rice_type, _, classification = selected_class.partition(" ")
    _render_municipal_crop_cycle_chart(
      df_forecast,
      rice_type=rice_type or "Hybrid",
      classification=classification or "Premium",
      selected_municipalities=selected_munis,
    )


def _top_municipalities_bar(dr):
  """Top municipalities by production (horizontal bar)."""
  with theme.section_card(title="Top Municipalities by Production",
              desc="Ranking of municipalities by palay production.",
              icon_name="leaderboard"):
    # Filter rendered INSIDE the section card (compact Year dropdown).
    selected_year = _year_only_filter(dr, key="muni_year_top")

    muni = getattr(dr, "municipal_production_df", None)
    if muni is None or getattr(muni, "empty", True):
      muni = getattr(dr, "municipality_df", None)
    if muni is None or getattr(muni, "empty", True):
      st.info("Municipality production dataset not available.")
      return

    m = _derive_municipal_columns(muni)
    if "palay_production" not in m.columns:
      st.info("Municipality production dataset not available.")
      return

    m["date"] = pd.to_datetime(m["date"])
    m["year"] = m["date"].dt.year
    if selected_year is not None:
      m = m[m["year"] == selected_year]

    if m.empty:
      st.info("No production data for the selected year.")
      return

    top5 = (
      m.groupby("municipality")["palay_production"]
      .sum().reset_index()
      .sort_values("palay_production", ascending=False)
      .head(5)
    )

    plot_top5 = top5.sort_values("palay_production")

    year_label = f"({selected_year})" if selected_year is not None else ""
    fig = px.bar(
      plot_top5,
      x="palay_production", y="municipality", orientation="h",
      color="palay_production",
      color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
      text=plot_top5["palay_production"].round(0).astype(int),
    )
    fig.update_layout(
      xaxis_title="Production (MT)", yaxis_title="Municipality",
      showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
      height=380, margin=dict(t=30, b=40, l=40, r=40),
      yaxis={"categoryorder": "total ascending"},
    )
    fig.update_traces(texttemplate='%{text:,}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True, key="muni_top5_bar")


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

    def _top5(col):
      return (
        m.groupby("municipality")[col].sum().reset_index()
        .sort_values(col, ascending=False).head(5)
      )

    dry = _top5("dry_season") if "dry_season" in m.columns else pd.DataFrame()
    wet = _top5("wet_season") if "wet_season" in m.columns else pd.DataFrame()

    col1, col2 = st.columns(2)
    with col1:
      if not dry.empty:
        fig = px.pie(dry, names="municipality", values="dry_season",
               color_discrete_sequence=px.colors.sequential.Greens[0:5][::-1])
        fig.update_layout(height=360, margin=dict(t=30, b=40, l=40, r=40))
        st.plotly_chart(fig, use_container_width=True, key="muni_dry_pie")
      else:
        st.info("No dry season data.")
    with col2:
      if not wet.empty:
        fig = px.pie(wet, names="municipality", values="wet_season",
               color_discrete_sequence=px.colors.sequential.Teal[0:5][::-1])
        fig.update_layout(height=360, margin=dict(t=30, b=40, l=40, r=40))
        st.plotly_chart(fig, use_container_width=True, key="muni_wet_pie")
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

    # 2. COMPACT YEAR FILTER (inside the card, single column).
    selected_year = _year_only_filter(dr, key="muni_year_yield")

    muni = getattr(dr, "municipality_df", None)
    if muni is None or getattr(muni, "empty", True):
      st.info("Municipality yield dataset not available.")
      return

    m = muni.copy()
    m["date"] = pd.to_datetime(m["date"])
    m["_year"] = m["date"].dt.year

    # Optional year filter
    if selected_year is not None:
      m = m[m["_year"] == selected_year]

    if m.empty:
      st.info("No municipal yield data for the selected filter.")
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
    # 3. PLOTLY BAR CHARTS
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
        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside")
        fig = _bar_layout(fig, "Municipality", "Production (MT)")
        fig.update_layout(showlegend=True, margin=LAYOUT_MARGINS)
        st.plotly_chart(fig, use_container_width=True, key="muni_yield_both")
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
        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside")
        fig = _bar_layout(fig, "Municipality", "Dry Season Production (MT)")
        st.plotly_chart(fig, use_container_width=True, key="muni_yield_dry")
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
        fig.update_traces(texttemplate='%{text:,.0f}', textposition="outside")
        fig = _bar_layout(fig, "Municipality", "Wet Season Production (MT)")
        st.plotly_chart(fig, use_container_width=True, key="muni_yield_wet")
      else:
        st.info("Wet Season data not available.")

def render(df, dr):
  """Main Municipal Analytics page with tabbed sub-views."""
  if dr is None or not getattr(dr, "has_provincial_data", False):
      st.info("No municipal data — municipal analytics hidden (0 values). Provincial data required. Upload via Import Data.")
      return
  theme.page_title("Municipal Analytics",
           "Municipality-level price and yield analytics.")

  tab1, tab2, tab3, tab4 = st.tabs([
    ":material/payments: Municipal Prices",
    ":material/eco: Municipal Yield",
    ":material/emoji_events: Top Municipalities",
    ":material/eco: Seasonal Distribution",
  ])

  with tab1:
    _municipal_price_tab(dr)

  with tab2:
    _municipal_yield_tab(dr)

  with tab3:
    _top_municipalities_bar(dr)

  with tab4:
    _seasonal_distribution_pies(dr)
