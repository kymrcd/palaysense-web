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
    the seasonal tabs Dry Season Forecasts and Wet Season Forecasts.
    The local filters (Rice Type / Classification / Municipality) live here
    and ONLY scope the table DataFrames.

Strictly NO purely historical past data on this page.
"""
import numpy as np
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


# --- Benchmark & forecast chart helpers — moved from overview.py (now forecast-only, compact 290/280) ---
def _pick_column(df, candidates):
    if df is None:
        return None
    return next((c for c in candidates if c in df.columns), None)

def _add_benchmark_ref_line(fig, y_value, label, line_color="#78909C", annotation_position="top left"):
    if fig is None or y_value is None:
        return fig
    try:
        y = float(y_value)
    except (TypeError, ValueError):
        return fig
    if pd.isna(y):
        return fig
    try:
        fig.add_hline(y=y, line_dash="dot", line_width=1.2, line_color=line_color, opacity=0.6,
                      annotation_text=label, annotation_position=annotation_position,
                      annotation=dict(font=dict(size=10, color=line_color), bgcolor="rgba(255,255,255,0.85)"))
    except Exception:
        try:
            fig.add_hline(y=y, line_dash="dot", line_width=1.2, line_color=line_color, opacity=0.6, annotation_text=label, annotation_position=annotation_position)
        except Exception:
            pass
    return fig

def _benchmark_yield_config(benchmark_option, historical_avg):
    opt = str(benchmark_option).strip() if benchmark_option else ""
    if opt in ("Market Price", "Market Price (3-Year Average)", "Market Price (3-Yr Average)", "Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
        if historical_avg is None or pd.isna(historical_avg):
            return None
        try:
            v = float(historical_avg)
        except (TypeError, ValueError):
            return None
        if pd.isna(v):
            return None
        return (v, f"Bataan 10-Yr Avg Yield ({v:.2f} MT/ha)", "#616161")
    if opt in ("Government Target", "Government Target (NFA/DA)", "Target ng Gobyerno", "NFA / DA Policy Baseline", "DA Target (4.50 MT/ha)", "DA Target"):
        return (4.50, "DA Target Yield (4.50 MT/ha)", "#2E7D32")
    return None

def _normalize_benchmarks(benchmark_option):
    if benchmark_option is None:
        return set()
    _none_vals = ("None", "Hide (None)", "Itago (None)", "Wala")
    if isinstance(benchmark_option, (list, set, tuple)):
        return {str(o).strip() for o in benchmark_option if str(o).strip() and str(o).strip() not in _none_vals}
    s = str(benchmark_option).strip()
    if not s or s in _none_vals:
        return set()
    return {s}

def _apply_benchmarks_to_fig(fig, df, chart_type, benchmark_options, provincial_df=None):
    opts = _normalize_benchmarks(benchmark_options)
    if not opts:
        return fig
    src_df = provincial_df if provincial_df is not None and chart_type in ("yield", "price") else df
    if src_df is None:
        src_df = df
    for opt in opts:
        try:
            if chart_type == "yield":
                if opt in ("Market Price", "Market Price (3-Year Average)", "Market Price (3-Yr Average)", "Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
                    _col = "quarterly_yield_mt_per_ha"
                    _col = _col if src_df is not None and _col in src_df.columns else _pick_column(src_df, ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha"])
                    hist_avg = None
                    if _col and src_df is not None and _col in src_df.columns:
                        hist_avg = pd.to_numeric(src_df[_col], errors="coerce").dropna().mean()
                        if pd.isna(hist_avg):
                            hist_avg = None
                    cfg = _benchmark_yield_config(opt, hist_avg)
                    if cfg is not None:
                        y_val, label, color = cfg
                        pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
                        fig = _add_benchmark_ref_line(fig, y_val, label, line_color=color, annotation_position=pos)
                elif opt in ("Government Target", "Government Target (NFA/DA)", "Target ng Gobyerno", "NFA / DA Policy Baseline", "DA Target (4.50 MT/ha)", "DA Target"):
                    cfg = _benchmark_yield_config(opt, None)
                    if cfg is not None:
                        y_val, label, color = cfg
                        pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
                        fig = _add_benchmark_ref_line(fig, y_val, label, line_color=color, annotation_position=pos)
                continue
            if chart_type == "price":
                if opt in ("Market Price", "Market Price (3-Year Average)", "Market Price (3-Yr Average)", "Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
                    rolling_regular_avg = None
                    rolling_fancy_avg = None
                    try:
                        if src_df is not None and "other_variety_price" in src_df.columns:
                            rolling_regular_avg = pd.to_numeric(src_df["other_variety_price"], errors="coerce").dropna().tail(12).mean()
                            if pd.isna(rolling_regular_avg):
                                rolling_regular_avg = None
                        if src_df is not None and "fancy_palay_price" in src_df.columns:
                            rolling_fancy_avg = pd.to_numeric(src_df["fancy_palay_price"], errors="coerce").dropna().tail(12).mean()
                            if pd.isna(rolling_fancy_avg):
                                rolling_fancy_avg = None
                    except Exception:
                        pass
                    if rolling_regular_avg is not None and not pd.isna(rolling_regular_avg):
                        try:
                            v = float(rolling_regular_avg)
                            label = f"Regular 3-Yr Rolling Avg (\u20B1{v:.2f}/kg)"
                            pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
                            fig = _add_benchmark_ref_line(fig, v, label, line_color="#616161", annotation_position=pos)
                        except Exception:
                            pass
                    if rolling_fancy_avg is not None and not pd.isna(rolling_fancy_avg):
                        try:
                            v = float(rolling_fancy_avg)
                            label = f"Fancy 3-Yr Rolling Avg (\u20B1{v:.2f}/kg)"
                            pos = "bottom left" if fig.layout.shapes is None or len(fig.layout.shapes) == 1 else "top left"
                            fig = _add_benchmark_ref_line(fig, v, label, line_color="#78909C", annotation_position=pos)
                        except Exception:
                            pass
                elif opt in ("Government Target", "Government Target (NFA/DA)", "Target ng Gobyerno", "NFA / DA Policy Baseline"):
                    fig = _add_benchmark_ref_line(fig, 19.00, "NFA Floor Price (\u20B119.00/kg)", line_color="#EF4444", annotation_position="bottom left")
                    fig = _add_benchmark_ref_line(fig, 23.75, "Fancy Commercial Target (\u20B123.75/kg)", line_color="#F59E0B", annotation_position="top left")
                continue
        except Exception:
            continue
    return fig

def _align_forecast_arrays(fancy_arr, regular_arr):
    fancy_s = pd.Series(list(fancy_arr) if fancy_arr is not None else [], name="fancy_palay_price")
    regular_s = pd.Series(list(regular_arr) if regular_arr is not None else [], name="other_variety_price")
    aligned = pd.concat([fancy_s, regular_s], axis=1, join="outer").sort_index()
    return aligned["fancy_palay_price"], aligned["other_variety_price"]

def _group_by_period(df, period="ANNUAL", value_cols=None):
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
    temp["semester"] = np.where(temp["month"] <= 6, 1, 2)
    p = str(period).strip().upper() if period else "ANNUAL"
    if p in ("DRY SEASON", "SEMESTER 1", "SEM 1"):
        temp = temp[temp["semester"] == 1]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str) + " Dry"
        return grouped
    if p in ("WET SEASON", "SEMESTER 2", "SEM 2"):
        temp = temp[temp["semester"] == 2]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str) + " Wet"
        return grouped
    if p == "ANNUAL":
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str)
        return grouped
    else:
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str)
        return grouped

def _price_forecast_chart_compact(df, dr, benchmark_option="None"):
    """Price forecast dashed with benchmark — forecast only, 290px."""
    fig = go.Figure()
    try:
        fancy_raw = list(dr.forecast_3months_fancy) if dr.forecast_3months_fancy else []
        regular_raw = list(dr.forecast_variety_3months) if dr.forecast_variety_3months else []
        if not fancy_raw and not regular_raw:
            return fig
        latest = dl.get_latest_date(df)
        if latest is None or pd.isna(latest):
            return fig
        fancy_s, regular_s = _align_forecast_arrays(fancy_raw, regular_raw)
        n = len(fancy_s)
        start = latest + pd.DateOffset(months=1)
        fc_months = pd.date_range(start=start, periods=n, freq="MS")
        fig.add_trace(go.Scatter(x=fc_months, y=fancy_s.values, mode="lines+markers", name="Fancy Forecast",
                                 line=dict(color=theme.FANCY_COLOR, width=2.5, dash="dash"), marker=dict(size=6, symbol="diamond"), connectgaps=True,
                                 hovertemplate="%{x|%b %Y}<br>Fancy: ₱%{y:.2f}/kg<extra></extra>"))
        fig.add_trace(go.Scatter(x=fc_months, y=regular_s.values, mode="lines+markers", name="Regular Forecast",
                                 line=dict(color=theme.REGULAR_COLOR, width=2.5, dash="dash"), marker=dict(size=6, symbol="diamond"), connectgaps=True,
                                 hovertemplate="%{x|%b %Y}<br>Regular: ₱%{y:.2f}/kg<extra></extra>"))
        # Peak annotations — restore (was missing)
        try:
            if fancy_s.dropna().size:
                idx = int(fancy_s.idxmax())
                if 0 <= idx < len(fc_months):
                    fig.add_annotation(x=fc_months[idx], y=float(fancy_s.iloc[idx]), text=f"▲ Peak: ₱{float(fancy_s.iloc[idx]):.2f}/kg", showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(size=9, color="#15803D"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1)
        except Exception:
            pass
        try:
            if regular_s.dropna().size:
                idx = int(regular_s.idxmax())
                if 0 <= idx < len(fc_months):
                    fig.add_annotation(x=fc_months[idx], y=float(regular_s.iloc[idx]), text=f"▲ Peak: ₱{float(regular_s.iloc[idx]):.2f}/kg", showarrow=True, arrowhead=2, ax=0, ay=30, font=dict(size=9, color="#6D28D9"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1)
        except Exception:
            pass
        fig = _apply_benchmarks_to_fig(fig, df, "price", benchmark_option)
        fig.update_layout(height=290, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title="₱/kg",
                          legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=10, family=theme.FONT)),
                          plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
                          xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
        return fig
    except Exception:
        pass
    return go.Figure()

def _price_historical_chart_compact(df, period="ANNUAL", benchmark_option="None"):
    """Historical price line with peak + benchmark, compact."""
    value_cols = []
    if "fancy_palay_price" in df.columns: value_cols.append("fancy_palay_price")
    if "other_variety_price" in df.columns: value_cols.append("other_variety_price")
    if not value_cols: return go.Figure()
    grouped = _group_by_period(df, period, value_cols)
    if grouped.empty: return go.Figure()
    fig = go.Figure()
    if "fancy_palay_price" in grouped.columns:
        fig.add_trace(go.Scatter(x=grouped["period_label"], y=grouped["fancy_palay_price"], mode="lines+markers", name="Fancy Palay", line=dict(color=theme.FANCY_COLOR, width=2.5), marker=dict(size=4), connectgaps=True, hovertemplate="%{x}<br>Fancy: ₱%{y:.2f}/kg<extra></extra>"))
        peak_idx = grouped["fancy_palay_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(x=peak_row["period_label"], y=peak_row["fancy_palay_price"], text=f"▲ Peak: ₱{peak_row['fancy_palay_price']:.2f}/kg", showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(size=9, color="#15803D"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1)
    if "other_variety_price" in grouped.columns:
        fig.add_trace(go.Scatter(x=grouped["period_label"], y=grouped["other_variety_price"], mode="lines+markers", name="Regular Palay", line=dict(color=theme.REGULAR_COLOR, width=2.5), marker=dict(size=4), connectgaps=True, hovertemplate="%{x}<br>Regular: ₱%{y:.2f}/kg<extra></extra>"))
        peak_idx = grouped["other_variety_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(x=peak_row["period_label"], y=peak_row["other_variety_price"], text=f"▲ Peak: ₱{peak_row['other_variety_price']:.2f}/kg", showarrow=True, arrowhead=2, ax=0, ay=30, font=dict(size=9, color="#6D28D9"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1)
    fig = _apply_benchmarks_to_fig(fig, df, "price", benchmark_option)
    fig.update_layout(height=290, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Year", yaxis_title="₱/kg",
                      legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=10, family=theme.FONT)),
                      plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
                      xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    return fig

def _yield_forecast_bar_compact(dr, df, benchmark_option="None"):
    """Yield FORECAST as BAR (hero) — Q4 2026–Q3 2027 style, compact, with benchmark dot lines."""
    try:
        yield_fc = list(dr.forecast_quarterly_yield) if dr.forecast_quarterly_yield else []
        if not yield_fc: return go.Figure()
        latest = dl.get_latest_date(df)
        anchor = latest if latest is not None and not pd.isna(latest) else pd.Timestamp.today()
        fc_quarters = pd.period_range(start=pd.Period(anchor, freq="Q") + 1, periods=len(yield_fc), freq="Q")
        fc_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
        # BAR hero — rounded, matches screenshot
        ydf = pd.DataFrame({"Quarter": fc_labels, "Yield": yield_fc})
        fig = px.bar(ydf, x="Quarter", y="Yield", color="Yield", color_continuous_scale=["#8D4004", "#E67E22", "#F39C12", "#F1C40F"], text=ydf["Yield"].round(2))
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white", height=290, margin=dict(l=10, r=10, t=10, b=10),
                          font=dict(family=theme.FONT, size=11), yaxis_title="MT/ha", xaxis_title=None)
        fig.update_traces(textposition="outside", marker_line_width=0, marker_cornerradius=8, hovertemplate="%{x}<br>Forecast: %{y:.2f} MT/ha<extra></extra>")
        # convert to go.Figure to add benchmark hlines + peak annotation
        fig_go = go.Figure(fig)
        # peak
        try:
            peak_val = float(pd.Series(yield_fc).max())
            peak_idx = yield_fc.index(peak_val)
            fig_go.add_annotation(x=fc_labels[peak_idx], y=peak_val, text=f"▲ Peak: {peak_val:.2f} MT/ha", showarrow=True, arrowhead=2, ax=0, ay=-35, font=dict(size=9, color="#C2410C"), bgcolor="rgba(255,255,255,0.95)", bordercolor="#F57C00", borderwidth=1)
        except Exception:
            pass
        fig_go = _apply_benchmarks_to_fig(fig_go, dl.get_quarterly_yield(df), "yield", benchmark_option)
        # y-axis 0.05 steps, zoomed to show movement closer
        try:
            _mn, _mx = float(pd.Series(yield_fc).min()), float(pd.Series(yield_fc).max())
            import math
            _lo = math.floor((_mn - 0.08) / 0.05) * 0.05
            _hi = math.ceil((_mx + 0.10) / 0.05) * 0.05
            if benchmark_option == "Government Target":
                _hi = max(_hi, 4.60)
            fig_go.update_yaxes(range=[_lo, _hi], dtick=0.05, tickformat=".2f")
        except Exception:
            pass
        fig_go.update_traces(marker_cornerradius=8, hovertemplate="%{x}<br>Forecast: %{y:.2f} MT/ha<extra></extra>", hoverlabel=dict(bgcolor="white", font_size=11))
        fig_go.update_layout(height=290, margin=dict(l=10, r=10, t=35, b=10), showlegend=False, bargap=0.4, bargroupgap=0.1)
        return fig_go
    except Exception:
        return go.Figure()

def _yield_historical_chart_compact(df, benchmark_option="None"):
    """Historical yield — compact line, with benchmark."""
    quarterly = dl.get_quarterly_yield(df)
    if quarterly.empty: return go.Figure()
    # group by year for historical trend
    hist = quarterly.groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
    hist["period_label"] = hist["year"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["period_label"], y=hist["quarterly_yield_mt_per_ha"], mode="lines+markers", name="Historical Yield", line=dict(color="#2E7D32", width=2.5), marker=dict(size=6)))
    peak_idx = hist["quarterly_yield_mt_per_ha"].idxmax()
    if pd.notna(peak_idx):
        peak_row = hist.loc[peak_idx]
        fig.add_annotation(x=peak_row["period_label"], y=peak_row["quarterly_yield_mt_per_ha"], text=f"▲ Peak: {peak_row['quarterly_yield_mt_per_ha']:.2f} MT/ha", showarrow=True, arrowhead=2, ax=0, ay=-25, font=dict(size=9, color="#C2410C"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1)
    fig = _apply_benchmarks_to_fig(fig, quarterly, "yield", benchmark_option)
    fig.update_layout(height=290, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Year", yaxis_title="MT/ha",
                      legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=10, family=theme.FONT)),
                      plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
                      xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    return fig

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
    """Top section: Forecasted values (separate from historical KPIs)."""
    with theme.section_card(title="Forecasted Values — System-Generated",
                            desc=f"Average predicted prices by season for {selected_class}. Separate from historical KPIs.",
                            icon_name="auto_awesome"):
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
    """Benchmark bar + 2 dashboard cards — insights INSIDE respective graph."""
    try:
        prov_df = dr.provincial_df.copy()
    except Exception:
        prov_df = dl.get_provincial_df(dr)
    hist_df = prov_df

    # Shared metrics for both inside-insights (aligned with Decision Support Panel)
    try:
        fancy_fc = list(dr.forecast_3months_fancy) if hasattr(dr, "forecast_3months_fancy") and dr.forecast_3months_fancy else []
        regular_fc = list(dr.forecast_variety_3months) if hasattr(dr, "forecast_variety_3months") and dr.forecast_variety_3months else []
        hist_fancy = pd.to_numeric(prov_df["fancy_palay_price"], errors="coerce").dropna() if "fancy_palay_price" in prov_df.columns else pd.Series(dtype=float)
        hist_regular = pd.to_numeric(prov_df["other_variety_price"], errors="coerce").dropna() if "other_variety_price" in prov_df.columns else pd.Series(dtype=float)
        avg_fancy = float(hist_fancy.mean()) if not hist_fancy.empty else None
        avg_regular = float(hist_regular.mean()) if not hist_regular.empty else None
        def _pct(cur, base):
            if cur is None or base is None: return None
            try: c,b = float(cur), float(base)
            except: return None
            if pd.isna(c) or pd.isna(b) or b==0: return None
            return (c-b)/b*100
        next_fancy = float(pd.Series(fancy_fc).dropna().iloc[0]) if fancy_fc else None
        next_regular = float(pd.Series(regular_fc).dropna().iloc[0]) if regular_fc else None
        fancy_pct = _pct(next_fancy, avg_fancy)
        regular_pct = _pct(next_regular, avg_regular)
        vals = [v for v in [fancy_pct, regular_pct] if v is not None]
        price_outlook = float(sum(vals)/len(vals)) if vals else 0.0
        y_list = [float(x) for x in (list(dr.forecast_quarterly_yield) if hasattr(dr, "forecast_quarterly_yield") and dr.forecast_quarterly_yield else []) if pd.notna(x)]
        if y_list:
            avg_yield = float(sum(y_list)/len(y_list)); low_yield = float(min(y_list))
            supply_shortfall = (avg_yield - 4.50)/4.50*100
        else:
            avg_yield = low_yield = supply_shortfall = 0.0
        try:
            latest = dl.get_latest_date(prov_df)
            price_month = (latest + pd.DateOffset(months=1)).strftime("%b %Y") if latest is not None and not pd.isna(latest) else pd.Timestamp.today().strftime("%b %Y")
            q = dl.get_quarterly_yield(prov_df)
            latest_q = q.iloc[-1]
            fc_quarters = pd.period_range(start=pd.Period(latest_q["date_q"], freq="Q") + 1, periods=4, freq="Q")
            yield_period = f"Q{fc_quarters[0].quarter} {fc_quarters[0].year} – Q{fc_quarters[-1].quarter} {fc_quarters[-1].year}"
        except Exception:
            price_month = pd.Timestamp.today().strftime("%b %Y")
            yield_period = "Next 4 quarters"
    except Exception:
        price_outlook = supply_shortfall = 0.0
        avg_yield = low_yield = 0.0
        fancy_pct = regular_pct = None
        price_month = pd.Timestamp.today().strftime("%b %Y")
        yield_period = "Next 4 quarters"

    hdr_col1, hdr_col2 = st.columns([0.74, 0.26], vertical_alignment="center")
    with hdr_col1:
        try:
            _benchmark_opt = st.segmented_control("Benchmark / Reference Line:", options=["Market Price", "Government Target", "None"], key="fc_benchmark_toggle", default="None")
            if _benchmark_opt is None: _benchmark_opt = "None"
        except Exception:
            _benchmark_opt = st.radio("Benchmark / Reference Line:", options=["Market Price", "Government Target", "None"], horizontal=True, key="fc_benchmark_toggle")
        if _benchmark_opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average", "Market Price (3-Year Average)", "Market Price (3-Yr Average)"): _benchmark_opt = "Market Price"
        elif _benchmark_opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline"): _benchmark_opt = "Government Target"
        elif _benchmark_opt in ("Wala", "Itago (None)", "Hide (None)"): _benchmark_opt = "None"
    with hdr_col2:
        with st.popover(":material/info: Benchmark Guide"):
            st.markdown("""
**What do the benchmark lines mean?**
* **Market Price (3-Yr Rolling Avg):** Average Bataan price over last 12 quarters — inflation-aware. Yield: 10-year mean.
* **Government Target:** Regular **₱19.00/kg** NFA floor, Fancy **₱23.75/kg** (19×1.25), Yield **4.50 MT/ha** DA target.
* **None:** No reference line.
""")

    col_price, col_yield = st.columns(2, gap="medium")

    with col_price:
        with st.container(border=True):
            st.markdown("### :material/show_chart: Provincial Price Trend")
            st.caption("Forecast price — dotted lines are benchmarks.")
            fig = _price_forecast_chart_compact(hist_df, dr, _benchmark_opt)
            if fig.data:
                st.plotly_chart(fig, use_container_width=True, key=f"fc_priceF_{_benchmark_opt}")
            else:
                st.info("Price forecast data not available.")
            # Insight INSIDE price graph — safe when no data (demo empty)
            fancy_txt = f"{fancy_pct:+.1f}%" if fancy_pct is not None else "—"
            regular_txt = f"{regular_pct:+.1f}%" if regular_pct is not None else "—"
            outlook_txt = f"{price_outlook:+.1f}%" if price_outlook is not None else "—"
            if fancy_pct is None and regular_pct is None:
                st.info("Price outlook not available — no historical or forecast data.")
            else:
                st.markdown(f"""
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #F59E0B; border-radius:8px; padding:8px 10px; margin-top:8px;">
                  <div style="font-size:0.80rem; color:#92400E; font-weight:700;">Price · {price_month}</div>
                  <div style="font-size:0.80rem; color:#444;">Fancy {fancy_txt} · Regular {regular_txt} → {outlook_txt} overall</div>
                  <div style="font-size:0.78rem; color:#92400E; font-weight:600;">Reading: {"Stable vs hist avg" if (price_outlook is not None and price_outlook>=-1) else "Softer than hist avg" if price_outlook is not None else "No data"}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_yield:
        with st.container(border=True):
            st.markdown("### :material/eco: Provincial Yield Trend")
            st.caption("Forecast yield — benchmarks help judge vs DA/10-yr average.")
            fig = _yield_forecast_bar_compact(dr, hist_df, _benchmark_opt)
            if fig.data:
                st.plotly_chart(fig, use_container_width=True, key=f"fc_yieldF_{_benchmark_opt}")
            else:
                st.info("Yield forecast data not available.")
            # Insight INSIDE yield graph
            st.markdown(f"""
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #16A34A; border-radius:8px; padding:8px 10px; margin-top:8px;">
              <div style="font-size:0.80rem; color:#166534; font-weight:700;">Yield · {yield_period}</div>
              <div style="font-size:0.80rem; color:#444;">Avg {avg_yield:.2f} MT/ha · Gap {supply_shortfall:+.1f}% vs 4.50 · Low {low_yield:.2f}</div>
              <div style="font-size:0.78rem; color:#166534; font-weight:600;">Reading: {"At/above DA 4.50" if supply_shortfall>=0 else "Below DA 4.50 — early warning"}</div>
            </div>
            """, unsafe_allow_html=True)


def _municipal_season_bar(df, labels, selected_class, season_label, key):
    """Grouped bar chart for municipal forecasts — same data as tables, chart view.

    Reuses the already-filtered season DataFrame (df_dry / df_wet). Melts
    Month 1-3 to long form so each forecast month groups municipalities
    side-by-side. Returns silently on empty data.
    """
    if df is None or df.empty:
        return
    try:
        plot_df = (
            df[["Municipality", "Month 1", "Month 2", "Month 3"]]
            .melt(id_vars=["Municipality"], value_vars=["Month 1", "Month 2", "Month 3"],
                  var_name="month_key", value_name="price")
        )
        _map = {"Month 1": labels[0], "Month 2": labels[1], "Month 3": labels[2]}
        plot_df["forecast_month"] = plot_df["month_key"].map(_map)
        plot_df["price"] = pd.to_numeric(plot_df["price"], errors="coerce")
        plot_df = plot_df.dropna(subset=["price"])
        if plot_df.empty:
            st.info("No price available for the selected filters.")
            return
        plot_df["Municipality"] = plot_df["Municipality"].astype(str).str.title()
        fig = px.bar(
            plot_df, x="forecast_month", y="price", color="Municipality",
            barmode="group",
            category_orders={"forecast_month": labels},
            color_discrete_sequence=px.colors.qualitative.Set3,
            labels={"forecast_month": "Forecast Month", "price": "Price (₱/kg)", "Municipality": "Municipality"},
            title=f"{selected_class} — {season_label}",
        )
        fig.update_layout(
            height=340, margin=dict(t=35, b=120, l=45, r=10),
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Inter, sans-serif", size=11),
            legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="center", x=0.5,
                        font=dict(size=10), bgcolor="rgba(255,255,255,0.95)",
                        bordercolor="#E5E7EB", borderwidth=1),
            yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
            xaxis=dict(gridcolor="#F3F4F6", showgrid=False, automargin=True),
            title=dict(font=dict(size=13)),
            bargap=0.22, bargroupgap=0.10,
            uniformtext_minsize=8, uniformtext_mode="hide",
        )
        fig.update_traces(hovertemplate="Bayan: %{fullData.name}<br>%{x}<br>₱%{y:.2f}/kg<extra></extra>",
                          cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True},
                        key=key)
    except Exception:
        return


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

        tab_dry, tab_wet = st.tabs([":material/wb_sunny: Dry Season Forecasts", ":material/water_drop: Wet Season Forecasts"])

        labels = month_labels if len(month_labels) == 3 else ["Month 1", "Month 2", "Month 3"]

        def _display(df, heading, season_label, chart_key):
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
            _municipal_season_bar(df, labels, selected_class, season_label, chart_key)
            st.dataframe(display, use_container_width=True, hide_index=True, height=300)
            st.caption(f"Displaying {len(display)} season configurations.")

        with tab_dry:
            _display(df_dry, ":material/wb_sunny: Peak & Off-Peak Dry Season Metrics", "Dry Season Crop Cycle", "fc_dry_chart")
        with tab_wet:
            _display(df_wet, ":material/water_drop: Rain-fed & High-Moisture Wet Season Metrics", "Wet Season Crop Cycle", "fc_wet_chart")


def _render_forecast_insights(df, dr):
    """Now inside respective graph cards — kept as no-op for backward compat."""
    return


def render(df, dr):
    """Main Forecasting page — pure forecast data (no historical graphs)."""
    theme.page_title("Forecasting",
                     "Peak and Off-Peak forecast data for palay across Bataan municipalities.")

    # Stable default benchmark for forecast visuals (unaffected by table filters).
    benchmark_class = "Hybrid Premium"
    _, df_dry, df_wet, month_labels = _prepare_forecast_df(dr, [], benchmark_class)

    # Top section: forecasted values (system-generated, separate from historical KPIs)
    _render_summary_kpis(df_dry, df_wet, benchmark_class)

    # Middle section: price & yield forecast visual chart + yield summary card
    _forecast_visual_chart(dr, benchmark_class, [])

    # Insights — Planning Division centric, below both graphs
    _render_forecast_insights(df, dr)

    # Bottom section: pure forecast data tables (filters scoped locally to tables)
    _render_forecast_tables(dr, month_labels)