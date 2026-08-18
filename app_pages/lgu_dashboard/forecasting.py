"""
PalaySense LGU Dashboard — Forecasting
======================================
Card-based forecasting page.

Layout:
  • Top Section: Summary KPI cards (horizontal row) using a stable default
    benchmark classification (Hybrid Premium).
  • Middle Section: NEW Price & Yield Forecast visual chart (line with dashed
    forecast + yield forecast bar) + Yield Forecast Summary side-card.
  • Bottom Section: Pure forecast data tables inside card containers, using
    the seasonal tabs ☀️ Dry Season Forecasts and 🌧️ Wet Season Forecasts.
    The local filters (Rice Type / Classification / Municipality) live here
    and ONLY scope the table DataFrames.

Strictly NO purely historical past data on this page.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import theme
from . import data_layer as dl

# Rice type/season -> presentation label mapping
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


def _class_column_keyword(selected_class):
    """Return the forecast column keyword for a selected municipal classification."""
    return _RICE_CLASS_KEYWORDS.get(selected_class, selected_class.lower().replace(" ", ""))


def _prepare_forecast_df(dr, selected_munis, selected_class):
    """Return (df_filtered, df_dry, df_wet, month_labels)."""
    df_forecast = getattr(dr, "df_municipal_forecasts", None)
    if df_forecast is None or getattr(df_forecast, "empty", True):
        return None, None, None, []

    month_labels = _municipal_month_labels(dr)

    df_filtered = df_forecast.copy()
    if selected_munis:
        df_filtered = df_filtered[df_filtered["Municipality"].isin(selected_munis)]

    # Filter strictly by the selected municipal rice classification keyword
    class_keyword = _class_column_keyword(selected_class)
    df_filtered = df_filtered[
        df_filtered["Rice Type & Season"].str.contains(f"^{class_keyword}", case=False, na=False)
    ].copy()

    def _season(df, keyword):
        sub = df[df["Rice Type & Season"].str.contains(keyword, case=False, na=False)].copy()
        raw = sub["Rice Type & Season"].str.replace(keyword, "", case=False)
        sub["Rice Classification"] = raw.map(_RICE_TYPE_MAP).fillna(
            raw.str.replace("_", " ").str.title()
        )
        return sub

    df_dry = _season(df_filtered, "_dry")
    df_wet = _season(df_filtered, "_wet")

    return df_filtered, df_dry, df_wet, month_labels


def _season_avg(df):
    """Average predicted price across all dry OR wet configurations."""
    if df is None or df.empty:
        return 0.0
    vals = pd.to_numeric(df[["Month 1", "Month 2", "Month 3"]].stack(), errors="coerce")
    vals = vals.dropna()
    return float(vals.mean()) if not vals.empty else 0.0


def _render_table_filters(dr):
    """Compact 3-column local filter row for the Forecast Data Tables.

    Rendered inside the Forecast Data Tables card, right above the
    Dry/Wet tabs. The returned values ONLY scope the table DataFrames.
    """
    df_forecast = getattr(dr, "df_municipal_forecasts", None)
    if df_forecast is None or getattr(df_forecast, "empty", True):
        return [], "Hybrid Premium"

    muni_list = sorted(df_forecast["Municipality"].dropna().unique().tolist())

    c1, c2, c3 = st.columns(3)
    with c1:
        rice_type = st.selectbox("Rice Type", options=["Hybrid", "Inbred"], key="fc_rice_type")
    with c2:
        selected_class = st.selectbox(
            "Rice Classification",
            options=[f"{rice_type} Premium", f"{rice_type} Ordinary"],
            key="fc_rice_class",
        )
    with c3:
        selected_munis = st.multiselect("Municipalities", options=muni_list, default=[],
                                        key="fc_munis")
    return selected_munis, selected_class


def _render_summary_kpis(df_dry, df_wet, selected_class):
    """Top section: Summary KPI cards in a neat horizontal row."""
    with theme.section_card(title="Forecast Summary",
                            desc=f"Average predicted prices by season for {selected_class}.",
                            icon_name="query_stats"):
        dry_avg = _season_avg(df_dry)      # Dry Season (Peak)
        wet_avg = _season_avg(df_wet)      # Wet Season (Off-Peak)
        price_diff = dry_avg - wet_avg     # Estimated difference

        diff_arrow = "↑" if price_diff >= 0 else "↓"
        diff_color = theme.SUCCESS if price_diff >= 0 else theme.DANGER

        cards = [
            theme.kpi_card("Avg Predicted Dry Season Price", f"₱{dry_avg:.2f}",
                           "Peak season estimate", "sunny",
                           icon_bg="rgba(245,158,11,0.12)", icon_color="#F59E0B",
                           accent="#F59E0B"),
            theme.kpi_card("Avg Predicted Wet Season Price", f"₱{wet_avg:.2f}",
                           "Off-peak season estimate", "water_drop",
                           icon_bg="rgba(37,99,235,0.12)", icon_color="#2563EB",
                           accent="#2563EB"),
            theme.kpi_card("Estimated Price Difference", f"{diff_arrow} ₱{abs(price_diff):.2f}",
                           "Dry vs Wet estimate gap", "compare_arrows",
                           icon_bg="rgba(30,92,58,0.1)", icon_color=diff_color,
                           accent=diff_color),
        ]

        theme.kpi_row(cards)


def _forecast_visual_chart(dr, selected_class, selected_munis):
    """Middle section: Price forecast line (dashed) + Yield forecast bar + summary card.

    Uses ONLY forecast data (no historical past data).
    """
    with theme.section_card(title="Price & Yield Forecast Visuals",
                            desc=f"Forward-looking projections for {selected_class}.",
                            icon_name="insights"):
        # ---- Price forecast (Fancy/Regular dashed) ----
        try:
            fancy = list(dr.forecast_3months_fancy)
        except Exception:
            fancy = []
        try:
            regular = list(dr.forecast_variety_3months)
        except Exception:
            regular = []

        # Forecast month labels from provincial history
        try:
            prov_df = dr.provincial_df.copy()
            prov_df["date"] = pd.to_datetime(prov_df["date"])
            start = prov_df["date"].max() + pd.DateOffset(months=1)
            fc_months = pd.date_range(start=start, periods=max(len(fancy), 1), freq="MS")
            fc_labels = fc_months.strftime("%b %Y").tolist()
        except Exception:
            fc_labels = [f"Month {i+1}" for i in range(max(len(fancy), 1))]

        # ---- Yield forecast (4 quarters) ----
        try:
            yield_fc = list(dr.forecast_quarterly_yield)
        except Exception:
            yield_fc = []
        try:
            q = dl.get_quarterly_yield(prov_df)
            latest_q = q.iloc[-1]
            fc_quarters = pd.period_range(
                start=pd.Period(latest_q["date_q"], freq="Q") + 1, periods=4, freq="Q"
            )
            yield_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
        except Exception:
            yield_labels = [f"Q{i+1}" for i in range(max(len(yield_fc), 1))]

        col_price, col_yield = st.columns(2, gap="medium")

        with col_price:
            st.markdown("### 📈 Price Forecast")
            if fancy or regular:
                fig = go.Figure()
                if fancy:
                    fig.add_trace(go.Scatter(
                        x=fc_labels, y=fancy, mode="lines+markers", name="Fancy Forecast",
                        line=dict(color=theme.FANCY_COLOR, width=2.5, dash="dash"),
                        marker=dict(size=7, symbol="diamond"),
                    ))
                if regular:
                    fig.add_trace(go.Scatter(
                        x=fc_labels, y=regular, mode="lines+markers", name="Regular Forecast",
                        line=dict(color=theme.REGULAR_COLOR, width=2.5, dash="dash"),
                        marker=dict(size=7, symbol="diamond"),
                    ))
                fig.update_layout(
                    yaxis_title="₱ / kg", xaxis_title="Month",
                    height=340, hovermode="x unified",
                    plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family=theme.FONT, size=11),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=30, b=40, l=40, r=40),
                )
                st.plotly_chart(fig, use_container_width=True, key="fc_price_chart")
            else:
                st.info("Price forecast data not available.")

        with col_yield:
            st.markdown("### 🌱 Yield Forecast")
            if yield_fc:
                ydf = pd.DataFrame({"Quarter": yield_labels,
                                    "Forecasted Yield (MT/ha)": yield_fc})
                avg_y = ydf["Forecasted Yield (MT/ha)"].mean()
                max_y = ydf["Forecasted Yield (MT/ha)"].max()
                min_y = ydf["Forecasted Yield (MT/ha)"].min()

                fig_y = px.bar(
                    ydf, x="Quarter", y="Forecasted Yield (MT/ha)",
                    color="Forecasted Yield (MT/ha)",
                    color_continuous_scale=["#FFF176", "#FBC02D", "#F57C00"],
                    text=ydf["Forecasted Yield (MT/ha)"].round(2),
                )
                fig_y.update_layout(
                    showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                    height=300, margin=dict(t=30, b=40, l=40, r=40),
                )
                fig_y.update_traces(textposition="outside")
                st.plotly_chart(fig_y, use_container_width=True, key="fc_yield_bar")

                # Yield Forecast Summary side-card
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem;
                            border-radius:16px; border-left:6px solid #2E7D32;
                            box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.9rem; line-height:1.7;">
                    <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.5rem;">
                        📊 Yield Forecast Summary
                    </div>
                    <div>📈 Average: <b>{avg_y:.2f} MT/ha</b></div>
                    <div>🏆 Peak: <b>{max_y:.2f} MT/ha</b></div>
                    <div>📉 Low: <b>{min_y:.2f} MT/ha</b></div>
                    <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
                    <div style="font-size:0.85rem; color:#2E7D32;">Based on next 4 forecast quarters</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Yield forecast data not available.")


def _render_forecast_tables(dr, month_labels):
    """Bottom section: pure forecast data tables inside card containers.

    The local filters (Rice Type / Classification / Municipality) render in a
    compact 3-column row right above the Dry/Wet tabs. They ONLY scope the
    tables' DataFrames, leaving top-level KPIs/charts unaffected.
    """
    with theme.section_card(title="Forecast Data Tables",
                            desc="Monthly predictions per municipality and rice classification.",
                            icon_name="table_view"):
        # Localized filters — scoped strictly to the table data below.
        selected_munis, selected_class = _render_table_filters(dr)
        df_filtered, df_dry, df_wet, _ = _prepare_forecast_df(dr, selected_munis, selected_class)

        if df_filtered is None:
            st.info("No forecast configurations available for the selected filters.")
            return

        tab_dry, tab_wet = st.tabs(["☀️ Dry Season Forecasts", "🌧️ Wet Season Forecasts"])

        labels = month_labels if len(month_labels) == 3 else ["Month 1", "Month 2", "Month 3"]

        def _display(df, heading):
            if df is None or df.empty:
                st.info("No forecast configurations for this season.")
                return
            display = (
                df[["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]]
                .rename(columns={
                    "Month 1": labels[0],
                    "Month 2": labels[1],
                    "Month 3": labels[2],
                })
            )
            st.markdown(f"### {heading}")
            st.dataframe(display, use_container_width=True, hide_index=True, height=300)
            st.caption(f"Displaying {len(display)} season configurations.")

        with tab_dry:
            _display(df_dry, "☀️ Peak & Off-Peak Dry Season Metrics")
        with tab_wet:
            _display(df_wet, "🌧️ Rain-fed & High-Moisture Wet Season Metrics")


def render(df, dr):
    """Main Forecasting page — pure forecast data (no historical graphs)."""
    theme.page_title("Forecasting",
                     "Peak and Off-Peak forecast data for palay across Bataan municipalities.")

    # Stable default benchmark for top-level KPIs/chart (unaffected by table filters).
    benchmark_class = "Hybrid Premium"
    _, df_dry, df_wet, month_labels = _prepare_forecast_df(dr, [], benchmark_class)

    # Top section: summary KPI cards
    _render_summary_kpis(df_dry, df_wet, benchmark_class)

    # Middle section: price & yield forecast visual chart + yield summary card
    _forecast_visual_chart(dr, benchmark_class, [])

    # Bottom section: pure forecast data tables (filters scoped locally to tables)
    _render_forecast_tables(dr, month_labels)