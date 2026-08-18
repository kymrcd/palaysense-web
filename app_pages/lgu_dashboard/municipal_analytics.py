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
import pandas as pd
import plotly.express as px
import streamlit as st

from . import theme

# Rice type/season -> forecast column mapping (for presentation labels only)
_RICE_TYPE_MAP = {
    "hybridpremium": "Hybrid Premium",
    "hybridordinary": "Hybrid Ordinary",
    "inbredpremium": "Inbred Premium",
    "inbredordinary": "Inbred Ordinary",
}

# Granular municipal rice classification -> forecast column keyword
_RICE_CLASS_KEYWORDS = {
    "Hybrid Premium": "hybridpremium",
    "Hybrid Ordinary": "hybridordinary",
    "Inbred Premium": "inbredpremium",
    "Inbred Ordinary": "inbredordinary",
}

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


def _municipal_month_labels(dr):
    """Compute the 3 forecast month labels from municipal history."""
    try:
        history = dr.municipality_history_df
        muni_last_year = int(history["year"].max())
        last_year_rows = history[history["year"] == muni_last_year]
        if "month_num" in last_year_rows.columns:
            muni_last_month = int(last_year_rows["month_num"].max())
        else:
            muni_last_month = 12
        latest_date = pd.Timestamp(year=muni_last_year, month=muni_last_month, day=1)
        months = pd.date_range(start=latest_date + pd.DateOffset(months=1),
                               periods=3, freq="MS")
        return months.strftime("%B %Y").tolist()
    except Exception:
        return ["Month 1", "Month 2", "Month 3"]


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
            <span style="display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:#E5A93C;color:#fff;font-weight:700;font-size:12px;">ⓘ</span>
            <span class="tooltip-text">
                <b>🌾 Cropping Seasons (DA / PhilRice)</b><br>
                ☀️ <b>Dry Season:</b> Planted Nov–Dec | Harvested Mar–Apr
                (higher solar radiation, higher overall yield, irrigation-dependent).<br>
                🌧️ <b>Wet Season:</b> Planted May–Jul | Harvested Aug–Oct
                (prone to monsoon rains and typhoons, generally lower yield).
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _class_column_keyword(selected_class):
    """Return the forecast column keyword for a selected municipal classification."""
    return _RICE_CLASS_KEYWORDS.get(selected_class, selected_class.lower().replace(" ", ""))


def _municipal_price_tab(dr):
    """Active municipal price forecast (Dry / Wet season tables) filtered by
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
            st.info("Municipal forecast dataset not available.")
            return

        # Dynamic forecast month labels
        municipal_month_labels = _municipal_month_labels(dr)

        # Compute the classification keyword (e.g. "hybridpremium")
        class_keyword = _class_column_keyword(selected_class)

        df_filtered = df_forecast.copy()
        if selected_munis:
            df_filtered = df_filtered[df_filtered["Municipality"].isin(selected_munis)]
        # Filter strictly by the selected municipal rice classification
        df_filtered = df_filtered[
            df_filtered["Rice Type & Season"].str.contains(f"^{class_keyword}", case=False, na=False)
        ].copy()

        if df_filtered.empty:
            st.info(f"No forecast configurations for {selected_class}.")
            return

        tab_dry, tab_wet = st.tabs(["☀️ Dry Season Forecasts", "🌧️ Wet Season Forecasts"])

        labels = municipal_month_labels if len(municipal_month_labels) == 3 else ["Month 1", "Month 2", "Month 3"]

        def _display_season(df_season, keyword, season_label):
            if df_season is None or df_season.empty:
                st.info(f"No {season_label} forecast configurations for {selected_class}.")
                return
            sub = df_season[df_season["Rice Type & Season"].str.contains(keyword, case=False, na=False)].copy()
            raw_codes = sub["Rice Type & Season"].str.replace(keyword, "", case=False)
            sub["Rice Classification"] = raw_codes.map(_RICE_TYPE_MAP).fillna(
                raw_codes.str.replace("_", " ").str.title()
            )
            display = (
                sub[["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]]
                .rename(columns={
                    "Month 1": labels[0],
                    "Month 2": labels[1],
                    "Month 3": labels[2],
                })
            )
            st.write(f"### {season_label} Metrics — {selected_class}")
            st.dataframe(display, use_container_width=True, hide_index=True, height=280)
            st.caption(f"Displaying {len(display)} {season_label.lower()} configurations.")

        with tab_dry:
            _display_season(df_filtered, "_dry", "☀️ Peak & Off-Peak Dry Season")
        with tab_wet:
            _display_season(df_filtered, "_wet", "🌧️ Rain-fed & High-Moisture Wet Season")


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
        DRY_COLOR = "#E5A93C"   # Gold/Amber
        WET_COLOR = "#2D6A4F"   # Deep Green
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
    theme.page_title("Municipal Analytics",
                     "Municipality-level price and yield analytics.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Municipal Prices",
        "🌱 Municipal Yield",
        "🏆 Top Municipalities",
        "🍃 Seasonal Distribution",
    ])

    with tab1:
        _municipal_price_tab(dr)

    with tab2:
        _municipal_yield_tab(dr)

    with tab3:
        _top_municipalities_bar(dr)

    with tab4:
        _seasonal_distribution_pies(dr)
