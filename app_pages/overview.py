import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import plotly.graph_objects as go

# Only entry point into the data layer — all datasets are fetched inside
# overview_page() via reload_dashboard_data() and passed to helpers explicitly.
from data.Dashboard_Ready import reload_dashboard_data
from app_pages.lgu_dashboard import data_layer as dl

def _safe_column(df, col, default=0.0):
    """Safely get a DataFrame column, return Series of default if missing."""
    if df is None or df.empty:
        return pd.Series([default])
    if col not in df.columns:
        return pd.Series([default] * len(df))
    return df[col]

def _safe_index(arr, idx=0, default=0.0):
    """Safely index into a list/array, return default if out of bounds."""
    if arr is None or len(arr) == 0:
        return default
    try:
        return arr[idx]
    except (IndexError, TypeError):
        return default


def _safe_mean(values, default=0.0):
    """NaN-aware mean of a list/series, returning default when empty."""
    if values is None or len(values) == 0:
        return default
    try:
        s = pd.Series(values, dtype="float64").dropna()
        return float(s.mean()) if not s.empty else default
    except Exception:
        return default


def _safe_max(values, default=0.0):
    """NaN-aware max of a list/series, returning default when empty."""
    if values is None or len(values) == 0:
        return default
    try:
        s = pd.Series(values, dtype="float64").dropna()
        return float(s.max()) if not s.empty else default
    except Exception:
        return default


def _safe_min(values, default=0.0):
    """NaN-aware min of a list/series, returning default when empty."""
    if values is None or len(values) == 0:
        return default
    try:
        s = pd.Series(values, dtype="float64").dropna()
        return float(s.min()) if not s.empty else default
    except Exception:
        return default


def _pct_change(current, baseline):
    """Percent change from baseline, returning None for missing/NaN/zero baseline.

    Prevents the '₱0.00/kg (-100.0%)' KPI bug and ZeroDivisionError when the
    baseline is zero, NaN, or the forecast value is unavailable.
    """
    if current is None or baseline is None:
        return None
    try:
        c = float(current)
        b = float(baseline)
    except (TypeError, ValueError):
        return None
    if pd.isna(c) or pd.isna(b):
        return None
    if b == 0:
        return 0.0
    return ((c - b) / b) * 100


def _pick_column(df, candidates):
    """Return the first candidate column name present in df, else None."""
    if df is None:
        return None
    return next((c for c in candidates if c in df.columns), None)


def _align_forecast_arrays(fancy_arr, regular_arr):
    """Align two differently-sized forecast arrays onto a shared index.

    Both arrays are wrapped as pd.Series and merged with an OUTER join on
    their positional index. The shorter array (e.g. 3-month Regular) is
    right-padded with NaN up to the length of the longer array (6-month
    Fancy), so months 4-6 become NaN instead of raising a length mismatch.

    Returns:
        (fancy_series, regular_series): two pd.Series of identical length.
    """
    fancy_s = pd.Series(
        list(fancy_arr) if fancy_arr is not None else [],
        name="fancy_palay_price",
    )
    regular_s = pd.Series(
        list(regular_arr) if regular_arr is not None else [],
        name="other_variety_price",
    )

    # Outer join on the default RangeIndex -> both series get max length,
    # missing trailing months are NaN.
    aligned = pd.concat([fancy_s, regular_s], axis=1, join="outer").sort_index()

    return aligned["fancy_palay_price"], aligned["other_variety_price"]


def _group_by_period(df, period="ANNUAL", value_cols=None):
    """Group DataFrame by the specified period and return aggregated data with period labels.

    Args:
        df: DataFrame with 'date' column
        period: 'ANNUAL', 'QUARTERLY', or 'MONTHLY'
        value_cols: list of column names to aggregate (mean)

    Returns:
        DataFrame with 'period_label' column and aggregated values
    """
    if value_cols is None:
        value_cols = []
    if df is None or df.empty:
        return pd.DataFrame(columns=["period_label"] + value_cols)

    temp = df.copy()
    temp["date"] = pd.to_datetime(temp["date"])
    temp["year"] = temp["date"].dt.year
    temp["quarter"] = temp["date"].dt.quarter
    temp["month"] = temp["date"].dt.month
    temp["month_name"] = temp["date"].dt.strftime("%b")

    if period == "ANNUAL":
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str)
        return grouped
    elif period == "QUARTERLY":
        grouped = temp.groupby(["year", "quarter"]).mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str) + "-Q" + grouped["quarter"].astype(str)
        return grouped
    elif period == "MONTHLY":
        grouped = temp.groupby(["year", "month"]).mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped.apply(lambda r: f"{r['month_name']} {r['year']}", axis=1)
        return grouped
    else:
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str)
        return grouped


def _price_historical_chart(df, period="ANNUAL"):
    """Historical price chart grouped by the selected period with peak annotations."""
    value_cols = []
    if "fancy_palay_price" in df.columns:
        value_cols.append("fancy_palay_price")
    if "other_variety_price" in df.columns:
        value_cols.append("other_variety_price")
    if not value_cols:
        return go.Figure()

    grouped = _group_by_period(df, period, value_cols)
    if grouped.empty:
        return go.Figure()

    xaxis_title = "Year" if period == "ANNUAL" else ("Quarter" if period == "QUARTERLY" else "Month")
    fig = go.Figure()

    if "fancy_palay_price" in grouped.columns:
        fig.add_trace(go.Scatter(
            x=grouped["period_label"], y=grouped["fancy_palay_price"],
            mode="lines+markers", name="Fancy Palay",
            line=dict(color="#89a143", width=2.5), marker=dict(size=6),
        ))
        peak_idx = grouped["fancy_palay_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(
                x=peak_row["period_label"], y=peak_row["fancy_palay_price"],
                text=f"🔺 Peak: ₱{peak_row['fancy_palay_price']:.2f}/kg",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#16A34A",
                ax=0, ay=-50,
                font=dict(size=10, color="#15803D", weight="bold"),
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1, borderpad=4,
            )

    if "other_variety_price" in grouped.columns:
        fig.add_trace(go.Scatter(
            x=grouped["period_label"], y=grouped["other_variety_price"],
            mode="lines+markers", name="Regular Palay",
            line=dict(color="#d1a019", width=2.5), marker=dict(size=6),
        ))
        peak_idx = grouped["other_variety_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(
                x=peak_row["period_label"], y=peak_row["other_variety_price"],
                text=f"🔺 Peak: ₱{peak_row['other_variety_price']:.2f}/kg",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#6D28D9",
                ax=0, ay=50,
                font=dict(size=10, color="#6D28D9", weight="bold"),
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1, borderpad=4,
            )

    fig.update_layout(
        height=370, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=xaxis_title, yaxis_title="₱/kg",
        legend=dict(orientation="h", yanchor="bottom", y=-0.55, xanchor="center", x=0.5,
                    font=dict(size=11, family="Poppins")),
        plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
        xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
    )
    return fig


def _price_forecast_chart(provincial_df, fancy_forecast, regular_forecast):
    """Price forecast line chart (next 6 months) for Fancy & Regular.

    Fancy and Regular arrays are aligned via outer-join Series so they always
    share the same x axis; a missing month is NaN and is drawn as a gap
    (connectgaps=False) instead of breaking the layout.

    IMPORTANT: the x-axis is anchored to the LAST HISTORICAL DATE in the
    provincial data (where the forecast actually starts), NOT to the system
    clock. Using pd.Timestamp.today() would shift the whole line to e.g.
    September instead of January when the model runs on stale historical data.
    """
    fig = go.Figure()
    try:
        fancy_fc, regular_fc = _align_forecast_arrays(fancy_forecast, regular_forecast)
        if fancy_fc.dropna().empty and regular_fc.dropna().empty:
            return fig
        n = len(fancy_fc)

        # --- Anchor on the data, not the clock ---------------------------
        hist_dates = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
        if hist_dates.empty:
            raise ValueError("No valid historical dates in provincial data.")
        last_hist_date = hist_dates.max()
        fc_months = pd.date_range(
            start=last_hist_date + pd.DateOffset(months=1),
            periods=n, freq="MS"
        )
        # ------------------------------------------------------------

        fig.add_trace(go.Scatter(
            x=fc_months, y=fancy_fc.values,
            mode="lines+markers", name="Fancy Forecast",
            line=dict(color="#10B981", width=2.5, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
            connectgaps=False,
        ))
        fig.add_trace(go.Scatter(
            x=fc_months, y=regular_fc.values,
            mode="lines+markers", name="Regular Forecast",
            line=dict(color="#F5CD63", width=2.5, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
            connectgaps=False,
        ))
        fig.update_layout(
            height=370, margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=None, yaxis_title="₱/kg",
            legend=dict(orientation="h", yanchor="bottom", y=-0.55, xanchor="center", x=0.5,
                        font=dict(size=11, family="Poppins")),
            plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
            xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
        )
    except Exception:
        return go.Figure()
    return fig


def _yield_historical_chart(df, period="ANNUAL"):
    """Historical yield chart grouped by the selected period with peak annotation."""
    grouped = _group_by_period(df, period, ["quarterly_yield_mt_per_ha"])
    if grouped.empty or "quarterly_yield_mt_per_ha" not in grouped.columns:
        return go.Figure()

    xaxis_title = "Year" if period == "ANNUAL" else ("Quarter" if period == "QUARTERLY" else "Month")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grouped["period_label"], y=grouped["quarterly_yield_mt_per_ha"],
        mode="lines+markers", name="Historical Yield",
        line=dict(color="#7C3AED", width=3), marker=dict(size=7),
    ))

    peak_idx = grouped["quarterly_yield_mt_per_ha"].idxmax()
    if pd.notna(peak_idx):
        peak_row = grouped.loc[peak_idx]
        fig.add_annotation(
            x=peak_row["period_label"], y=peak_row["quarterly_yield_mt_per_ha"],
            text=f"🔺 Peak: {peak_row['quarterly_yield_mt_per_ha']:.2f} MT/ha",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
            ax=0, ay=-45,
            font=dict(size=10, color="#C2410C", weight="bold"),
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
        )

    fig.update_layout(
        height=350, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=xaxis_title, yaxis_title="MT/ha",
        legend=dict(orientation="h", yanchor="bottom", y=-0.40, xanchor="center", x=0.5,
                    font=dict(size=11, family="Poppins")),
        plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
        xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
    )
    return fig


def _yield_forecast_chart(provincial_df, yield_forecast):
    """Yield forecast line chart (next forecast quarters) with peak annotation.

    The quarter axis is anchored to the LAST HISTORICAL DATE in the provincial
    data (dynamic), never to pd.Timestamp.today().
    """
    fig = go.Figure()
    try:
        fc_yield = list(yield_forecast) if yield_forecast is not None else []
        if not fc_yield:
            return fig

        hist_dates = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
        if hist_dates.empty:
            raise ValueError("No valid historical dates in provincial data.")
        last_hist_date = hist_dates.max()

        fc_quarters = pd.period_range(
            start=pd.Period(last_hist_date, freq="Q") + 1,
            periods=len(fc_yield), freq="Q"
        )
        fc_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
        fig.add_trace(go.Scatter(
            x=fc_labels, y=fc_yield,
            mode="lines+markers", name="Forecast Yield",
            line=dict(color="#2E7D32", width=3, dash="dash"), marker=dict(size=8, symbol="diamond"),
        ))
        peak_val = _safe_max(fc_yield)
        peak_idx = fc_yield.index(peak_val) if peak_val in fc_yield else -1
        if 0 <= peak_idx < len(fc_labels):
            fig.add_annotation(
                x=fc_labels[peak_idx], y=peak_val,
                text=f"🔺 Peak: {peak_val:.2f} MT/ha",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
                ax=0, ay=-45,
                font=dict(size=10, color="#C2410C", weight="bold"),
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
            )
        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=None, yaxis_title="MT/ha",
            legend=dict(orientation="h", yanchor="bottom", y=-0.40, xanchor="center", x=0.5,
                        font=dict(size=11, family="Poppins")),
            plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
            xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
        )
    except Exception:
        return go.Figure()
    return fig


def _yield_summary_card(yield_forecast):
    """Yield Forecast Summary card (Avg / Peak / Low)."""
    try:
        yield_fc = list(yield_forecast) if yield_forecast is not None else []
    except Exception:
        yield_fc = []
    if not yield_fc:
        st.info("No data available for yield forecast.")
        return
    avg_y = _safe_mean(yield_fc)
    max_y = _safe_max(yield_fc)
    min_y = _safe_min(yield_fc)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem;
                border-radius:16px; border-left:6px solid #2E7D32;
                box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.95rem; line-height:1.8;">
        <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.5rem;">
            📊 Yield Forecast Summary
        </div>
        <div>📈 Average: <b>{avg_y:.2f} MT/ha</b></div>
        <div>🏆 Peak: <b>{max_y:.2f} MT/ha</b></div>
        <div>📉 Low: <b>{min_y:.2f} MT/ha</b></div>
        <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
        <div style="font-size:0.85rem; color:#2E7D32;">Based on next {len(yield_fc)} forecast quarters</div>
    </div>
    """, unsafe_allow_html=True)


def _render_municipal_season_tables(df_filtered_muni, month_labels):
    """Render the Dry/Wet municipal 3-month forecast tables inside tabs."""
    labels = month_labels if len(month_labels) >= 3 else ["Month 1", "Month 2", "Month 3"]

    tab_dry, tab_wet = st.tabs(["☀️ Dry Season Forecasts", "🌧️ Wet Season Forecasts"])

    def _render(df_season, keyword, heading, caption_label):
        sub = df_season[
            df_season["Rice Type & Season"].str.contains(keyword, case=False, na=False)
        ].copy()
        sub["Rice Classification"] = (
            sub["Rice Type & Season"]
            .str.replace(keyword, "", case=False)
            .str.replace("_", " ")
            .str.title()
        )
        display = (
            sub[["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]]
            .rename(columns={
                "Month 1": labels[0],
                "Month 2": labels[1],
                "Month 3": labels[2],
            })
        )
        st.write(f"### {heading}")
        if display.empty:
            st.info("📭 No data matches your filters.")
        else:
            fig_table = go.Figure(data=[go.Table(
                header=dict(
                    values=list(display.columns),
                    fill_color="#1B5E20",
                    font=dict(color="white", size=12, family="Poppins"),
                    align="left",
                ),
                cells=dict(
                    values=[display[col] for col in display.columns],
                    fill_color=[["#F9FAFB", "white"] * (len(display) // 2 + 1)][:len(display)],
                    font=dict(size=11, family="Poppins"),
                    align="left",
                    height=28,
                ),
            )])
            fig_table.update_layout(
                height=min(280, 60 + len(display) * 28),
                margin=dict(l=0, r=0, t=0, b=0),
            )
            st.plotly_chart(fig_table, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"Displaying {len(display)} {caption_label} configurations.")

    with tab_dry:
        _render(df_filtered_muni, "_dry", "☀️ Peak & Off-Peak Dry Season Metrics", "dry season")
    with tab_wet:
        _render(df_filtered_muni, "_wet", "🌧️ Rain-fed & High-Moisture Wet Season Metrics", "wet season")


def _insights_narrative(prov_year_df, quarterly_data, selected_muni_name,
                        fancy_forecast=None, regular_forecast=None):
    """Dynamic Insights Narrative / Storytelling Mode."""
    with st.expander("📝 Insights Narrative — Auto-generated market summary", expanded=True):
        try:
            hist_fancy = _safe_column(prov_year_df, "fancy_palay_price")
            hist_regular = _safe_column(prov_year_df, "other_variety_price")

            next_fancy = _safe_index(fancy_forecast, 0)
            next_regular = _safe_index(regular_forecast, 0)

            yield_qoq = 0
            if quarterly_data is not None and not quarterly_data.empty and len(quarterly_data) >= 2:
                q_current = quarterly_data["quarterly_yield_mt_per_ha"].iloc[-1]
                q_previous = quarterly_data["quarterly_yield_mt_per_ha"].iloc[-2]
                if (
                    pd.notna(q_current) and pd.notna(q_previous) and q_previous != 0
                ):
                    yield_qoq = ((q_current - q_previous) / q_previous) * 100

            avg_fancy = hist_fancy.mean() if not hist_fancy.empty else 0
            avg_regular = hist_regular.mean() if not hist_regular.empty else 0
            fancy_fc_vs_hist = _pct_change(next_fancy, avg_fancy) or 0.0
            regular_fc_vs_hist = _pct_change(next_regular, avg_regular) or 0.0

            prod_total = prov_year_df["production_total"].sum() if "production_total" in prov_year_df.columns else 0

            yield_trend_word = "growth" if yield_qoq > 0 else ("decline" if yield_qoq < 0 else "stability")
            price_trend_word = "upward" if fancy_fc_vs_hist > 0 else ("downward" if fancy_fc_vs_hist < 0 else "stable")

            if fancy_fc_vs_hist > 5:
                advisory = "consider holding Fancy Palay stocks for better pricing in the coming months."
            elif fancy_fc_vs_hist < -5:
                advisory = "consider selling Fancy Palay soon before prices drop further."
            else:
                advisory = "monitor market conditions closely before making bulk transactions."

            narrative_color = "#16A34A" if yield_qoq >= 0 else "#DC2626"
            price_color = "#16A34A" if fancy_fc_vs_hist >= 0 else "#DC2626"
        except Exception:
            yield_qoq = fancy_fc_vs_hist = regular_fc_vs_hist = 0
            yield_trend_word = price_trend_word = "stable"
            advisory = "monitor market conditions closely."
            narrative_color = price_color = "#1B5E20"
            prod_total = 0

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%);
                    border: 1px solid rgba(22, 163, 74, 0.2); border-radius: 16px;
                    padding: 24px 28px; box-shadow: 0 4px 16px rgba(0,0,0,0.03);">
            <div style="font-size: 1.1rem; font-weight: 700; color: #1B5E20; margin-bottom: 10px;">
                📊 Quarterly Market Summary
            </div>
            <div style="font-size: 0.95rem; line-height: 1.8; color: #374151;">
                In the latest monitoring period, <strong>Bataan's</strong> agricultural sector shows
                <strong>{'promising growth' if yield_qoq > 0 or fancy_fc_vs_hist > 0 else 'signs of adjustment'}</strong>.
                Provincial yield is expected to <strong>{'rise' if yield_qoq >= 0 else 'decline'}
                by <span style="color:{narrative_color};">{abs(yield_qoq):.1f}%</span></strong>
                compared to the previous quarter, while <strong>Fancy Palay</strong> prices show a
                <span style="color:{price_color};">{price_trend_word}</span> trend of
                <strong><span style="color:{price_color};">{abs(fancy_fc_vs_hist):.1f}%</span></strong>
                relative to the historical average.
                <br><br>
                For Regular Palay, the forecast indicates a
                <strong>{'rise' if regular_fc_vs_hist >= 0 else 'decline'} of
                <span style="color:{'#16A34A' if regular_fc_vs_hist >= 0 else '#DC2626'};">{abs(regular_fc_vs_hist):.1f}%</span></strong>
                compared to historical prices.
                Farmers are advised to <strong>{advisory}</strong>
                <br><br>
                <small style="color:#9CA3AF;">
                    💡 This narrative is auto-generated for <strong>{selected_muni_name}</strong>
                    across the selected period. Adjust filters to update insights.
                </small>
            </div>
        </div>
        """, unsafe_allow_html=True)


def overview_page():
    """
    Renders an accessible, farmer-centric agricultural dashboard for Bataan.
    Supports multi-year selections, 'All' municipality views, and Ecosystem toggle filters.
    """

    # Fetch ALL datasets inside the page via the single data-layer entry point.
    # No module-level globals are read here.
    dr = reload_dashboard_data()
    provincial_df = dr.provincial_df.copy()
    _prod_muni = getattr(dr, "municipal_production_df", None)
    municipality_df = (
        _prod_muni.copy()
        if _prod_muni is not None and not getattr(_prod_muni, "empty", True)
        else dr.municipality_df.copy()
    )
    df_municipal_forecasts = dr.df_municipal_forecasts.copy()
    forecast_3months_fancy = list(dr.forecast_3months_fancy)
    forecast_variety_3months = list(dr.forecast_variety_3months)
    forecast_quarterly_yield = list(dr.forecast_quarterly_yield)

    # Initialize display DataFrames to prevent UnboundLocalError
    df_dry_display = pd.DataFrame()
    df_wet_display = pd.DataFrame()

    # ========================================================
    # DATA PROCESSING & TEMPORAL MAPPING
    # ========================================================
    provincial_df = provincial_df.copy()
    provincial_df["date"] = pd.to_datetime(provincial_df["date"], errors="coerce")
    provincial_df = provincial_df.dropna(subset=["date"]).copy()
    provincial_sorted = provincial_df.sort_values("date").copy()

    df = provincial_sorted.copy()
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter

    latest_year = df["year"].max()
    provincial_latest = df[df["year"] == latest_year].copy().sort_values("date")
    latest = provincial_latest.iloc[-1] if not provincial_latest.empty else None
    latest_date = provincial_sorted["date"].max() if not provincial_sorted.empty else None

    # Quick backup conversion for municipality data
    muni = municipality_df.copy()
    if muni.empty:
        muni = pd.DataFrame(columns=["date", "year"])
    if "date" not in muni.columns:
        if "year" in muni.columns:
            muni["date"] = pd.to_datetime(muni["year"].astype(str) + "-06-15")
        else:
            muni["date"] = pd.Timestamp("2024-01-01")
    else:
        muni["date"] = pd.to_datetime(muni["date"], errors="coerce")
    muni["year"] = muni["date"].dt.year


    # =========================
    # HISTORICAL QUARTERLY DATA
    # =========================
    _yield_col = _pick_column(
        df,
        ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha", "Yield"],
    )
    if _yield_col is not None:
        quarterly_df = (
            df.groupby(["year", "quarter"])[_yield_col]
            .mean()
            .reset_index()
        )
    else:
        quarterly_df = pd.DataFrame(columns=["year", "quarter", "quarterly_yield_mt_per_ha"])

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
    latest_q = quarterly_df.iloc[-1] if not quarterly_df.empty else None
    _fc_quarter_start = (
        pd.Period(latest_q["date_q"], freq="Q") + 1
        if latest_q is not None
        else pd.Period(pd.Timestamp.today(), freq="Q") + 1
    )
    forecast_quarters = pd.period_range(
        start=_fc_quarter_start,
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

    _fc_yield_arr = list(forecast_quarterly_yield) if forecast_quarterly_yield is not None else []
    if len(_fc_yield_arr) == len(forecast_df):
        forecast_df["quarterly_yield_mt_per_ha"] = _fc_yield_arr
    else:
        forecast_df["quarterly_yield_mt_per_ha"] = [_fc_yield_arr[i] if i < len(_fc_yield_arr) else 0 for i in range(len(forecast_df))]
    forecast_df["Type"] = "Forecast"

    # ========================================================
    # TOP FILTER TOOLBAR
    # ========================================================
    st.markdown(
        """
        <style>
            div[data-testid="stColumn"] { margin-top: 0px !important; padding-top: 0px !important; padding-bottom: 0.2rem !important; }
            div[data-testid="stSelectbox"] { margin-top: 0px !important; padding-top: 0px !important; }
            div[data-testid="stSelectbox"] > div { border: none !important; background: transparent !important; box-shadow: none !important; }
            div[data-testid="stSelectbox"] div[role="combobox"] {
                border: 1px solid #1B5E20 !important;
                background-color: #FFFFFF !important;
                border-radius: 8px !important;
                box-shadow: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="margin-top:0.55rem; margin-bottom:0.2rem;"></div>', unsafe_allow_html=True)
    available_years = sorted(list(df["year"].dropna().unique()), reverse=False)
    if not available_years:
        available_years = [2024]

    st.session_state.setdefault("overview_start_year", available_years[0])
    st.session_state.setdefault("overview_end_year", available_years[-1])
    st.session_state.setdefault("overview_period", "ANNUAL")
    st.session_state.setdefault("overview_selected_muni", "All Municipalities")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4, gap="small")
    with filter_col1:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">YEAR RANGE</div>', unsafe_allow_html=True)
        selected_start_year = st.selectbox(
            "Start Year",
            options=available_years,
            key="overview_start_year",
            label_visibility="collapsed",
        )
    with filter_col2:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">TO</div>', unsafe_allow_html=True)
        selected_end_year = st.selectbox(
            "End Year",
            options=available_years,
            key="overview_end_year",
            label_visibility="collapsed",
        )
    with filter_col3:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">PERIOD</div>', unsafe_allow_html=True)
        selected_period = st.selectbox(
            "Period",
            options=["ANNUAL", "QUARTERLY", "MONTHLY"],
            key="overview_period",
            label_visibility="collapsed",
        )
    with filter_col4:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">MUNICIPALITY</div>', unsafe_allow_html=True)
        _muni_label_col = _pick_column(muni, ["municipality", "Municipality", "Mun", "Area"])
        all_munis_options = (
            sorted(muni[_muni_label_col].dropna().unique())
            if _muni_label_col is not None
            else []
        )
        muni_options = ["All Municipalities"] + all_munis_options
        if st.session_state["overview_selected_muni"] not in muni_options:
            st.session_state["overview_selected_muni"] = "All Municipalities"
        selected_muni = st.selectbox(
            "Municipality",
            options=muni_options,
            key="overview_selected_muni",
            label_visibility="collapsed",
        )

    selected_years = list(range(selected_start_year, selected_end_year + 1))
    selected_munis = [selected_muni] if selected_muni != "All Municipalities" else all_munis_options
    selected_eco = "All Types"
    overview_muni_label = selected_muni

    # ========================================================
    # SIDEBAR: SECTION NAVIGATION (Quick View)
    # ========================================================
    section_options = [
        "Buong Dashboard",
        "Yield Forecast",
        "Price Forecast",
        "Mga Payo (Advisories)",
        "Municipal Forecast",
        "Price Insights",
        "Yield Insights",
        "Municipal Analysis",
        "Production Rankings",
        "Insights Narrative",
    ]
    with st.sidebar:
        st.markdown(
            '<div style="font-weight:800; color:#1B5E20; font-size:1.05rem; margin-bottom:0.2rem;">'
            '<i class="material-symbols-outlined" style="font-size:20px;color:#2E7D32;vertical-align:middle;margin-right:6px;">agriculture</i>'
            'PalaySense Quick View</div>'
            '<div style="font-size:0.75rem; color:#6B7280; margin-bottom:0.8rem;">Pumili ng seksyon para mabilis na makita ang isang graph lamang.</div>',
            unsafe_allow_html=True,
        )
        section_choice = st.radio(
            "Ipakita ang:",
            options=section_options,
            index=0,
            key="overview_section",
        )
    show_all = section_choice == "Buong Dashboard"

    # ========================================================
    # DYNAMIC DATA FILTERING LOGIC
    # ========================================================
    # Filter by Year
    if selected_years:
        provincial_year = (
            df[df["year"].isin(selected_years)]
            .copy()
            .sort_values("date")
        )

        muni_filtered = muni[
            muni["year"].isin(selected_years)
        ]

    else:
        provincial_year = (
            df[df["year"] == available_years[0]]
            .copy()
            .sort_values("date")
        )

        muni_filtered = muni[
            muni["year"] == available_years[0]
            ]

    # Filter by Municipality
    if selected_munis and _muni_label_col is not None:
        muni_filtered = muni_filtered[
            muni_filtered[_muni_label_col].isin(selected_munis)
        ]
    else:
        muni_filtered = muni_filtered.iloc[0:0]

    # Filter quarterly_df to selected years for synchronized historical/forecast view
    if selected_years and not quarterly_df.empty:
        quarterly_df = quarterly_df[quarterly_df["year"].isin(selected_years)].copy()

    # ========================================================
    # METRIC GENERATION & VARIANCE CALCULATIONS
    # ========================================================
    # Align Fancy (6 months) vs Regular (3 months) ONCE, before any
    # DataFrame/chart is built. Months 4-6 of Regular become NaN.
    fc_fancy_s, fc_regular_s = _align_forecast_arrays(
        forecast_3months_fancy, forecast_variety_3months
    )

    if not provincial_year.empty:
        latest_selected = provincial_year.iloc[-1]

        avg_fancy_price = _safe_column(provincial_year, "fancy_palay_price").mean()
        avg_regular_price = _safe_column(provincial_year, "other_variety_price").mean()
        _prov_prod_col = _pick_column(
            provincial_year,
            ["production_total", "palay_production", "production", "volume", "production_mt"],
        )
        latest_production = (
            provincial_year.groupby("year")[_prov_prod_col].sum().mean()
            if _prov_prod_col is not None
            else 0
        )

        # Build the forecast axis from the ALIGNED (max) length so the
        # date range always matches the length of both price arrays.
        forecast_months = pd.date_range(
            start=latest_selected["date"] + pd.DateOffset(months=1),
            periods=len(fc_fancy_s),
            freq="MS"
        )
        next_month_name = forecast_months[0].strftime("%B %Y") if len(forecast_months) > 0 else "N/A"

        _fancy_0 = _safe_index(forecast_3months_fancy, 0)
        percent_change_fancy = _pct_change(_fancy_0, avg_fancy_price) or 0.0
        _regular_0 = _safe_index(forecast_variety_3months, 0)
        percent_change_regular = _pct_change(_regular_0, avg_regular_price) or 0.0
        avg_yield_forecast = _safe_mean(forecast_quarterly_yield)
    else:
        latest_production, percent_change_fancy, percent_change_regular = 0, 0, 0
        avg_yield_forecast = _safe_mean(forecast_quarterly_yield)
        avg_fancy_price = _safe_column(df, "fancy_palay_price").mean()
        avg_regular_price = _safe_column(df, "other_variety_price").mean()
        next_month_name = "N/A"
        forecast_months = pd.date_range(
            start=pd.Timestamp.today().to_period("M").to_timestamp() + pd.DateOffset(months=1),
            periods=len(fc_fancy_s),
            freq="MS"
        )

    next_fancy_pred = _safe_index(forecast_3months_fancy, 0)
    next_regular_pred = _safe_index(forecast_variety_3months, 0)

    # ========================================================
    # CHART GENERATION SETUP
    # ========================================================
    _hy_col = _pick_column(
        provincial_year,
        ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha", "Yield"],
    )
    if _hy_col is not None and "quarter" in provincial_year.columns:
        historical_yield = (
            provincial_year
            .groupby("quarter")[_hy_col]
            .mean()
            .reset_index()
        )
        historical_yield["Quarter"] = "Q" + historical_yield["quarter"].astype(str)
        historical_yield["Yield"] = historical_yield[_hy_col]
        historical_yield["Type"] = "Past Records"
    else:
        historical_yield = pd.DataFrame(columns=["Quarter", "Yield", "Type"])

    _fc_yield_list = list(forecast_quarterly_yield) if forecast_quarterly_yield is not None else []
    forecast_yield = pd.DataFrame({
        "Quarter": [f"Q{i}" for i in range(1, len(_fc_yield_list) + 1)],
        "Yield": _fc_yield_list,
        "Type": "Forecast"
    })
    yield_chart_df = pd.concat([historical_yield[["Quarter", "Yield", "Type"]], forecast_yield])

    # FORECAST DATAFRAMES (SHARED)
    # Use the already-aligned series (months 4-6 of Regular are NaN),
    # so pd.DataFrame never receives mismatched lengths.
    forecast_df_fancy = pd.DataFrame({
        "date": forecast_months,
        "fancy_palay_price": fc_fancy_s.values,
        "Type": "Forecast"
    })

    forecast_df_regular = pd.DataFrame({
        "date": forecast_months,
        "other_variety_price": fc_regular_s.values,
        "Type": "Forecast"
    })

    # ========================================================
    # PRICE DATA (Historical + Forecast)
    # ========================================================

    if len(selected_years) == 1:

        hist_df = provincial_year.copy()

        # Fancy Historical
        hist_fancy = hist_df[["date", "fancy_palay_price"]].rename(columns={
            "fancy_palay_price": "Price"
        })
        hist_fancy["Variety"] = "Fancy Palay"
        hist_fancy["Type"] = "Historical"

        # Fancy Forecast
        forecast_fancy = forecast_df_fancy.rename(columns={
            "fancy_palay_price": "Price"
        }).copy()
        forecast_fancy["Variety"] = "Fancy Palay"

        # Regular Historical
        hist_regular = hist_df[["date", "other_variety_price"]].rename(columns={
            "other_variety_price": "Price"
        })
        hist_regular["Variety"] = "Regular Palay"
        hist_regular["Type"] = "Historical"

        # Regular Forecast
        forecast_regular = forecast_df_regular.rename(columns={
            "other_variety_price": "Price"
        }).copy()
        forecast_regular["Variety"] = "Regular Palay"

        combined_price = pd.concat([
            hist_fancy,
            forecast_fancy,
            hist_regular,
            forecast_regular
        ])

        combined_price["Category"] = (
                combined_price["Variety"] + " - " + combined_price["Type"]
        )

    else:

        _yearly_fancy = _pick_column(provincial_year, ["fancy_palay_price"])
        _yearly_regular = _pick_column(provincial_year, ["other_variety_price"])
        _yearly_cols = [c for c in [_yearly_fancy, _yearly_regular] if c is not None]
        if "year" in provincial_year.columns and _yearly_cols:
            yearly = (
                provincial_year
                .groupby("year")[_yearly_cols]
                .mean()
                .reset_index()
            )
        else:
            yearly = pd.DataFrame(columns=["year", "fancy_palay_price", "other_variety_price"])

        hist_fancy = yearly[["year", "fancy_palay_price"]].rename(columns={
            "year": "date",
            "fancy_palay_price": "Price"
        })
        hist_fancy["Variety"] = "Fancy Palay"
        hist_fancy["Type"] = "Historical"

        hist_regular = yearly[["year", "other_variety_price"]].rename(columns={
            "year": "date",
            "other_variety_price": "Price"
        })
        hist_regular["Variety"] = "Regular Palay"
        hist_regular["Type"] = "Historical"

        forecast_fancy = pd.DataFrame({
            "date": [forecast_year1],
            "Price": [np.mean(forecast_3months_fancy)],
            "Variety": ["Fancy Palay"],
            "Type": ["Forecast"]
        })

        forecast_regular = pd.DataFrame({
            "date": [forecast_year1],
            "Price": [np.mean(forecast_variety_3months)],
            "Variety": ["Regular Palay"],
            "Type": ["Forecast"]
        })

        combined_price = pd.concat([
            hist_fancy,
            hist_regular,
            forecast_fancy,
            forecast_regular
        ])

        combined_price["Category"] = (
                combined_price["Variety"] + " - " + combined_price["Type"]
        )

    # Top 5 Municipalities Ranking (Historical Production) via the data layer.
    top5_municipalities = dl.get_top_5_producing_municipalities(muni_filtered, selected_years)

    # Total Production summed across the selected years. Prefer the provincial
    # annual records (authoritative scale); fall back to municipality data when
    # the provincial frame has no rows.
    total_production = dl.get_total_production(provincial_year, selected_years)
    if total_production is None:
        total_production = dl.get_total_production(muni_filtered, selected_years)
    prod_val = total_production if total_production is not None else 0

    # ========================================================
    # FRONT-END CSS
    # ========================================================
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');

        /* Main Container */
        .main-container { 
            font-family: 'Poppins', sans-serif; 
            padding: 0 1% 20px 1%; 
            background: #F8FAF9;
        }

        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 2rem !important;
            padding-bottom: 0rem !important;
        }

        /* Hero Banner - Modern Gradient */
        .hero-banner {
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 40%, #388E3C 100%);
            padding: 35px 40px;
            border-radius: 20px;
            color: white;
            margin-bottom: 28px;
            box-shadow: 0 12px 35px rgba(27, 94, 32, 0.2);
            position: relative;
            overflow: hidden;
            margin-top: -2.08rem;
        }
        .hero-banner::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 50%;
        }
        .hero-banner::after {
            content: '🌾';
            position: absolute;
            bottom: 10px;
            right: 30px;
            font-size: 80px;
            opacity: 0.1;
        }
        .hero-title { 
            font-size: clamp(1.8rem, 2.8vw, 2.5rem); 
            font-weight: 900; 
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        .hero-subtitle { 
            font-size: 1rem; 
            opacity: 0.92; 
            line-height: 1.6;
            font-weight: 400;
        }
        .hero-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.15);
            padding: 4px 16px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 8px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* KPI Cards - Glassmorphism */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }
        .metric-card {
            background: #FFFFFF;
            padding: 20px 22px;
            border-radius: 16px;
            border: 1px solid rgba(46, 125, 50, 0.08);
            position: relative;
            overflow: hidden;
        }
        .metric-card:hover {
            border-color: rgba(46, 125, 50, 0.2);
        }
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #2E7D32, #66BB6A);
        }
        .metric-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .metric-title { 
            font-size: 0.8rem; 
            font-weight: 600; 
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-icon {
            font-size: 1.2rem;
            opacity: 0.7;
        }
        .metric-data { 
            font-size: 1.8rem; 
            font-weight: 800; 
            color: #1B5E20;
            margin: 4px 0 2px 0;
            letter-spacing: -0.5px;
        }
        .metric-footer { 
            font-size: 0.7rem; 
            color: #9CA3AF;
            font-weight: 500;
        }
        .metric-change-positive {
            color: #16A34A;
            font-weight: 700;
        }
        .metric-change-negative {
            color: #DC2626;
            font-weight: 700;
        }

        /* Component Cards - Clean Design */
        .component-card {
            background: #FFFFFF;
            border-radius: 16px;
            border: 1px solid rgba(0, 0, 0, 0.05);
            padding: 22px 24px 24px 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
        }
        .component-card:hover {
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
        }
        .component-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        .component-header {
            font-size: 1.05rem;
            font-weight: 700;
            color: #111827;
        }
        .component-header-icon {
            font-size: 1.1rem;
            margin-right: 8px;
        }
        .component-desc {
            font-size: 0.8rem;
            color: #6B7280;
            margin-bottom: 16px;
            font-weight: 400;
        }

        /* Advisory Cards - Enhanced */
        .advisory-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            width: 100%;
            margin-top: 4px;
        }
        .advisory-card {
            display: flex;
            align-items: flex-start;
            padding: 16px 20px;
            border-radius: 12px;
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
        }
        .advisory-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        .card-status {
            border-left: 4px solid #0284C7;
            background: linear-gradient(135deg, #F0F9FF 0%, #FFFFFF 100%);
        }
        .card-marketing {
            border-left: 4px solid #16A34A;
            background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%);
        }
        .card-notice {
            border-left: 4px solid #EA580C;
            background: linear-gradient(135deg, #FFF7ED 0%, #FFFFFF 100%);
        }
        .card-optimization {
            border-left: 4px solid #7C3AED;
            background: linear-gradient(135deg, #F5F3FF 0%, #FFFFFF 100%);
        }
        .card-icon {
            font-size: 1.2rem;
            margin-right: 14px;
            margin-top: 2px;
        }
        .card-body {
            flex: 1;
            font-size: 0.88rem;
            line-height: 1.6;
            color: #374151;
        }
        .card-label {
            font-weight: 700;
            margin-right: 4px;
        }
        .label-status { color: #0369A1; }
        .label-marketing { color: #15803D; }
        .label-notice { color: #C2410C; }
        .label-optimization { color: #6D28D9; }
        .highlight-text {
            font-weight: 700;
            color: #1B5E20;
            background: rgba(27, 94, 32, 0.06);
            padding: 1px 6px;
            border-radius: 4px;
        }

        /* Custom Streamlit Overrides */
        .stSelectbox, .stMultiSelect {
            font-family: 'Poppins', sans-serif;
        }
        .stRadio > div {
            gap: 8px;
        }
        .stRadio label {
            font-family: 'Poppins', sans-serif;
            font-size: 0.85rem;
            padding: 6px 12px;
            border-radius: 8px;
            background: #F3F4F6;
        }
        .stRadio label:hover {
            background: #E8F5E9;
        }
        .stRadio [data-baseweb="radio"] {
            margin-right: 6px;
        }

        /* Sidebar enhancements */
        .css-1d391kg {
            background: #F8FAF9;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .hero-banner {
                padding: 24px 20px;
            }
            .metric-card {
                padding: 16px 18px;
            }
            .component-card {
                padding: 16px 18px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # ========================================================
    # LAYOUT RENDERING INTERFACE
    # ========================================================
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    # Hero Banner
    eco_display = "All Types" if selected_eco == "All Types" else selected_eco
    year_display = ", ".join(map(str, selected_years)) if selected_years else "All Years"

    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-title"> Bataan Rice Monitoring & Prediction</div>
        <div class="hero-subtitle">
            Data-driven insights for smarter farming decisions • 
            <strong>{eco_display}</strong> ecosystem 
        </div>
        <span class="hero-badge">📊 Live Dashboard • {len(selected_munis) if selected_munis else 0} municipalities selected</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI Row — each card checks `has_data` so empty selections show a clear
    # "No Data Available" fallback instead of ₱0.00 / -100.0% placeholders.
    if total_production is not None:
        prod_display = f"{total_production:,.0f} MT"
        prod_footer = "Historical total across selected period"
    else:
        prod_display = "No Data Available"
        prod_footer = "Historical/current production"

    yield_has_data = bool(forecast_quarterly_yield) and not pd.isna(avg_yield_forecast)
    fancy_has_data = (
        bool(forecast_3months_fancy)
        and not provincial_year.empty
        and not pd.isna(avg_fancy_price)
        and avg_fancy_price != 0
    )
    regular_has_data = (
        bool(forecast_variety_3months)
        and not provincial_year.empty
        and not pd.isna(avg_regular_price)
        and avg_regular_price != 0
    )

    fancy_color = "metric-change-positive" if percent_change_fancy >= 0 else "metric-change-negative"
    regular_color = "metric-change-positive" if percent_change_regular >= 0 else "metric-change-negative"
    fancy_arrow = "↑" if percent_change_fancy >= 0 else "↓"
    regular_arrow = "↑" if percent_change_regular >= 0 else "↓"

    yield_display = f"{avg_yield_forecast:.2f} MT/ha" if yield_has_data else "No Data Available"
    fancy_display = f"{fancy_arrow} {abs(percent_change_fancy):.1f}%" if fancy_has_data else "No Data Available"
    regular_display = f"{regular_arrow} {abs(percent_change_regular):.1f}%" if regular_has_data else "No Data Available"
    fancy_class = fancy_color if fancy_has_data else "metric-footer"
    regular_class = regular_color if regular_has_data else "metric-footer"

    if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Price Forecast",
                                      "Yield Insights", "Price Insights"):
        st.markdown(f"""
        <div class="kpi-row">
            <div class="metric-card">
                <div class="metric-card-header">
                    <div class="metric-title">🎯 Expected Yield</div>
                </div>
                <div class="metric-data">{yield_display}</div>
                <div class="metric-footer">Target weight per hectare this cycle</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-header">
                    <div class="metric-title">⭐ Fancy Price Trend</div>
                </div>
                <div class="metric-data {fancy_class}">{fancy_display}</div>
                <div class="metric-footer">Forecast for: {next_month_name}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-header">
                    <div class="metric-title">📦 Regular Price Trend</div>
                </div>
                <div class="metric-data {regular_class}">{regular_display}</div>
                <div class="metric-footer">Forecast for: {next_month_name}</div>
            </div>
            <div class="metric-card">
                <div class="metric-card-header">
                    <div class="metric-title">🏭 Total Production</div>
                </div>
                <div class="metric-data">{prod_display}</div>
                <div class="metric-footer">{prod_footer}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Plots Row 1
    chart_row1_col1, chart_row1_col2 = st.columns(2, gap="medium")

    with chart_row1_col1:
        if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Yield Insights"):
            st.markdown(
                '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon">📈</span>Provincial Yield Forecast</span></div><div class="component-desc">Historical harvest performance vs. AI-powered quarterly forecasts</div>',
                unsafe_allow_html=True)

            try:
                yield_subtab1, yield_subtab2 = st.tabs(["📈 Historical Yield Trend", "🔮 Yield Forecast"])
                with yield_subtab1:
                    st.plotly_chart(
                        _yield_historical_chart(provincial_year, selected_period),
                        use_container_width=True,
                        key=f"overview_yield_hist_{selected_start_year}_{selected_end_year}_{selected_period}",
                    )
                with yield_subtab2:
                    st.plotly_chart(
                        _yield_forecast_chart(provincial_df, forecast_quarterly_yield),
                        use_container_width=True,
                        key=f"overview_yield_fc_{selected_start_year}_{selected_end_year}",
                    )
            except Exception as e:
                st.warning(f"⚠️ Yield forecast chart could not render: {str(e)}")

            st.markdown("</div>", unsafe_allow_html=True)

    with chart_row1_col2:
        if show_all or section_choice in ("Buong Dashboard", "Price Forecast", "Price Insights"):
            st.markdown(
                '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon">📊</span>Provincial Price Forecast (6 Months)</span></div><div class="component-desc">Strategic buying & selling windows for optimal returns</div>',
                unsafe_allow_html=True)

            try:
                price_subtab1, price_subtab2 = st.tabs(["📈 Historical Price Trend", "🔮 Price Forecast"])
                with price_subtab1:
                    st.plotly_chart(
                        _price_historical_chart(provincial_year, selected_period),
                        use_container_width=True,
                        key=f"overview_price_hist_{selected_start_year}_{selected_end_year}_{selected_period}",
                    )
                with price_subtab2:
                    st.plotly_chart(
                        _price_forecast_chart(provincial_df, forecast_3months_fancy, forecast_variety_3months),
                        use_container_width=True,
                        key=f"overview_price_fc_{selected_start_year}_{selected_end_year}",
                    )
            except Exception as e:
                st.warning(f"⚠️ Price forecast chart could not render: {str(e)}")
            st.markdown("</div>", unsafe_allow_html=True)

    # ========================================================
    # MUNICIPAL 3-MONTH PRICE FORECAST WITH SEASONAL TABS
    # ========================================================
    if show_all or section_choice in ("Buong Dashboard", "Municipal Forecast", "Municipal Analysis"):
        st.markdown("""<hr style="border:1px solid #ddd; margin-top: 1rem; margin-bottom: 1rem;">""",
                    unsafe_allow_html=True)

        st.subheader("🌾 3-Month Municipal Price Forecast Summary")
        st.write(
            "Analyze the projected palay prices across different municipalities. "
            "Select a tab below to switch seasonal contexts:"
        )

        try:
            # Municipal forecasts loaded via dr.df_municipal_forecasts
            df_municipal_forecast = df_municipal_forecasts.copy()
            if df_municipal_forecast.empty:
                st.info("📭 Municipal forecast dataset not available yet. "
                        "Run the background pipeline to generate 3-month municipal forecasts.")
            else:
                # ----------------------------------------
                # Dynamic forecast month labels (anchored to data, not the clock)
                # ----------------------------------------
                if latest_date is not None and pd.notna(latest_date):
                    municipal_forecast_months = pd.date_range(
                        start=latest_date + pd.DateOffset(months=1),
                        periods=3,
                        freq="MS"
                    )
                    municipal_month_labels = municipal_forecast_months.strftime("%B %Y").tolist()
                else:
                    municipal_month_labels = ["Month 1", "Month 2", "Month 3"]

                muni_label_col = _pick_column(df_municipal_forecast, ["Municipality"])
                has_type_col = "Rice Type & Season" in df_municipal_forecast.columns
                has_month_cols = all(c in df_municipal_forecast.columns for c in ["Month 1", "Month 2", "Month 3"])
                if muni_label_col is None or not has_type_col or not has_month_cols:
                    st.info("📭 Municipal forecast file has an unexpected format "
                            "(expected Municipality / Rice Type & Season / Month 1-3).")
                else:
                    # 1. Interactive UI Filter for Municipalities
                    muni_list = list(df_municipal_forecast[muni_label_col].dropna().unique())
                    selected_muni = st.multiselect("Filter Municipalities:", options=muni_list, default=[])

                    # Apply global municipality filter first
                    df_filtered_muni = df_municipal_forecast.copy()
                    if selected_muni:
                        df_filtered_muni = df_filtered_muni[df_filtered_muni[muni_label_col].isin(selected_muni)]

                    # 2. CREATE VISUALLY APPEALING SEASONAL TABS
                    _render_municipal_season_tables(df_filtered_muni, municipal_month_labels)

        except FileNotFoundError:
            st.warning("⚠️ Forecast dataset report not found. Please verify the background pipeline ran completely.")
        except Exception as e:
            st.error(f"⚠️ Unable to render the municipal forecast data table: {str(e)}")

        st.markdown("""<hr style="border:1px solid #ddd; margin-top: 1rem; margin-bottom: 2rem;">""",
                    unsafe_allow_html=True)

    # Data Row 2 (Ranking & Smart Cards)
    chart_row2_col1, chart_row2_col2 = st.columns([2.90, 2])

    with chart_row2_col1:
        if show_all or section_choice in ("Buong Dashboard", "Production Rankings", "Municipal Analysis"):
            st.markdown(
                '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon">🏆</span>Top 5 Municipalities Ranking — Historical Production</span></div><div class="component-desc">Capacity comparison across the top-producing municipalities</div>',
                unsafe_allow_html=True)

            try:
                if not top5_municipalities.empty:
                    # Enhanced horizontal bar chart
                    fig_muni = px.bar(
                        top5_municipalities.sort_values("palay_production"),
                        x="palay_production",
                        y="municipality",
                        orientation="h",
                        color="palay_production",
                        color_continuous_scale=["#A5D6A7", "#2E7D32"],
                        text="palay_production"
                    )

                    fig_muni.update_traces(
                        texttemplate="%{text:,.0f} MT",
                        textposition="outside",
                        marker=dict(
                            line=dict(width=2, color='white'),
                            cornerradius=4
                        ),
                        hovertemplate="<b>%{y}</b><br>Production: %{x:,.0f} MT<extra></extra>"
                    )

                    fig_muni.update_layout(
                        height=380,
                        margin=dict(l=10, r=80, t=10, b=10),
                        xaxis_title="Metric Tons",
                        yaxis_title=None,
                        showlegend=False,
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        coloraxis_showscale=False,
                        hovermode="y unified",
                        yaxis={"categoryorder": "total ascending"}
                    )
                    fig_muni.update_xaxes(gridcolor="#F3F4F6", showgrid=True)
                    fig_muni.update_yaxes(gridcolor="#F3F4F6", showgrid=True)

                    st.plotly_chart(
                        fig_muni,
                        use_container_width=True,
                        key=f"municipality_production_fig_{selected_start_year}_{selected_end_year}"
                    )
                else:
                    st.info("📭 No matching data found for your current filters.")
            except Exception as e:
                st.warning(f"⚠️ Production rankings chart could not render: {str(e)}")

            st.markdown("</div>", unsafe_allow_html=True)

        # SMART FARMER CARDS INTERACTION VIEW
        with chart_row2_col2:
            if show_all or section_choice in ("Buong Dashboard", "Mga Payo (Advisories)"):
                st.markdown(f"""
                <div class="component-card">
                    <div class="component-header">Smart Agricultural Advisories</div>
                    <div class="component-desc">Live operational recommendations for <b>{selected_munis}</b>.</div>
                """, unsafe_allow_html=True)

                display_muni_name = "All Bataan Municipalities" if selected_munis == "All Municipalities" else selected_munis
                display_year_string = ", ".join(map(str, selected_years)) if selected_years else "Selected Years"

                if not muni_filtered.empty:
                    eco_msg = "⚠️ Rainfed setups should maximize water-retention fields and sync planting timelines with historical rainy quarters." if selected_eco == "Rainfed / Seasonal" else "✅ Water-Irrigated setups can securely aim for high-input Fancy Varieties due to reliable water schedules."

                    html_cards = f"""
                    <div class="advisory-container">
                    <div class="advisory-card card-status">
                    <div class="card-icon">📍</div>
                    <div class="card-body">
                    <span class="card-label label-status">Ecosystem Scope ({selected_eco}):</span>
                    Total output volume records captured for <span class="highlight-text">{display_muni_name}</span> across <span class="highlight-text">{display_year_string}</span> equals <span class="highlight-text">{prod_val:,.1f} MT</span>.
                    </div>
                    </div>
                    <div class="advisory-card card-marketing">
                    <div class="card-icon">💡</div>
                    <div class="card-body">
                    <span class="card-label label-marketing">Trading Target Advisory:</span>
                    Predictions indicate Premium Fancy varieties are heading toward <span class="highlight-text">₱{next_fancy_pred:.2f}/kg</span> next month, while regular commercial grades stabilize near <span class="highlight-text">₱{next_regular_pred:.2f}/kg</span>.
                    </div>
                    </div>
                    <div class="advisory-card card-optimization">
                    <div class="card-icon">💧</div>
                    <div class="card-body">
                    <span class="card-label label-optimization">Ecosystem Recommendation:</span>
                    {eco_msg}
                    </div>
                    </div>
                    </div>
                    """
                    st.markdown(html_cards, unsafe_allow_html=True)
                else:
                    st.warning(f"No active metrics found matching your current dashboard filter selections.")

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ---- Yield Forecast Summary ----
    if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Yield Insights"):
        _yield_summary_card(forecast_quarterly_yield)

    # ---- Insights Narrative ----
    if show_all or section_choice in ("Buong Dashboard", "Insights Narrative"):
        _insights_narrative(
            provincial_year, quarterly_df, overview_muni_label,
            fancy_forecast=forecast_3months_fancy,
            regular_forecast=forecast_variety_3months,
        )

    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 5px 0; font-size: 0.75rem; color: #9CA3AF; border-top: 1px solid #E5E7EB; margin-top: 10px;">
        🌾 Bataan Rice Monitoring System • Data-driven insights for sustainable agriculture • v2.0
    </div>
    """, unsafe_allow_html=True)
