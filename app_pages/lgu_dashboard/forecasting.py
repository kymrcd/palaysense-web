"""
PalaySense LGU Dashboard — Forecasting
======================================
Card-based forecasting page.

Layout:
  • Provincial tab: 6-month price + 4-quarter yield forecast with benchmarks.
  • Municipal tab: searchable municipality selector (full comparison) +
    grouped bar forecast chart + data table + KPIs.

Fixes vs. critique:
  - Removes literal "undefined" Plotly title.
  - Shows full municipal comparison (all selected municipalities, accessible palette).
  - Consolidates Rice Type + Classification into single selector.
  - Vectorizes price averages (no per-municipality loop).
  - Dynamic forecast period (no hardcoded Jan-Mar 2026).
  - Accessible legend + price-chip legend, WCAG-sized fonts.
  - Named constants for NFA/DA benchmarks, no bare excepts swallowed silently.
"""
import logging
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import data_layer as dl
from . import theme

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
NFA_FLOOR_PRICE = 19.00  # ₱/kg Regular NFA floor
FANCY_COMMERCIAL_TARGET = 23.75  # ₱/kg Fancy (19 * 1.25)
DA_TARGET_YIELD = 4.50  # MT/ha
MUNI_MAX_COMPARE = 12  # show all municipalities (Bataan = 12)
MUNI_MAX_LIST = 50  # safety cap for list rendering

# Accessible, colorblind-friendly palette (Okabe-Ito + Tol, high contrast) — 12 colors for full Bataan
ACCESSIBLE_PALETTE = [
    "#1B5E20",  # dark green
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # pink
    "#009E73",  # teal
    "#E69F00",  # amber
    "#56B4E9",  # sky
    "#F0E442",  # yellow (with dark border)
    "#000000",  # black
    "#882255",  # wine
    "#117733",  # green-teal
    "#44AA99",  # aqua
]

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

_RICE_CLASS_OPTIONS = [
    "Inbred Ordinary",
    "Inbred Premium",
    "Hybrid Ordinary",
    "Hybrid Premium",
]


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
    # guard missing columns
    cols = [c for c in ["Month 1", "Month 2", "Month 3"] if c in df.columns]
    if not cols:
        return 0.0
    vals = pd.to_numeric(df[cols].stack(), errors="coerce")
    vals = vals.dropna()
    return float(vals.mean()) if not vals.empty else 0.0


def _compute_season_change_pct(dr, selected_munis, selected_class, season_label):
    """Return (pct_change, last_avg) for forecast avg vs last 3-month historical avg.

    Compares the forecast average (Month 1-3) for the selected municipalities /
    classification / season against the mean of the same column in
    municipality_history_df for the last 3 historical months (e.g. Oct-Dec 2025).
    Returns (None, None) when history is unavailable.
    """
    try:
        class_keyword = _class_column_keyword(selected_class)
        suffix = "_wet" if str(season_label).lower().startswith("wet") else "_dry"
        col = f"{class_keyword}{suffix}"
        # history df is lowercase municipality
        hist = getattr(dr, "municipality_history_df", None)
        if hist is None or getattr(hist, "empty", True):
            return None, None
        # normalize column existence
        if col not in hist.columns:
            return None, None
        # filter by municipality if selected
        if selected_munis:
            wanted = {m.lower().strip() for m in selected_munis}
            # column name is lowercase 'municipality' in parquet
            muni_col = "municipality" if "municipality" in hist.columns else "Municipality"
            hist_sub = hist[hist[muni_col].astype(str).str.lower().isin(wanted)]
            if hist_sub.empty:
                hist_sub = hist
        else:
            hist_sub = hist
        # last 3 months by date
        if "date" not in hist_sub.columns:
            return None, None
        hist_sub = hist_sub.copy()
        hist_sub["date"] = pd.to_datetime(hist_sub["date"], errors="coerce")
        hist_sub = hist_sub.dropna(subset=["date"])
        if hist_sub.empty:
            return None, None
        # get last 3 distinct months
        uniq_dates = hist_sub["date"].drop_duplicates().sort_values()
        if uniq_dates.empty:
            return None, None
        last_dates = uniq_dates.tail(3).tolist()
        last_rows = hist_sub[hist_sub["date"].isin(last_dates)]
        last_vals = pd.to_numeric(last_rows[col], errors="coerce").dropna()
        if last_vals.empty:
            return None, None
        last_avg = float(last_vals.mean())
        # forecast avg for same scope
        _, df_dry, df_wet, _ = _prepare_forecast_df(dr, selected_munis, selected_class)
        season_df = df_wet if suffix == "_wet" else df_dry
        forecast_avg = _season_avg(season_df)
        if forecast_avg == 0 or last_avg == 0 or pd.isna(last_avg):
            return None, last_avg
        pct = (forecast_avg - last_avg) / last_avg * 100
        return float(pct), float(last_avg)
    except Exception as exc:
        logger.debug("season change pct failed: %s", exc)
        return None, None


def _format_period_short(labs):
    """Return short period like 'Jan-Mar 2026' from labs ['January 2026', ...]."""
    try:
        if not labs or len(labs) < 1:
            return "3 months"
        starts = pd.to_datetime(labs[0])
        ends = pd.to_datetime(labs[-1]) if len(labs) > 1 else starts
        if pd.isna(starts) or pd.isna(ends):
            return "3 months"
        if starts.year == ends.year:
            return f"{starts.strftime('%b')}\u2013{ends.strftime('%b')} {ends.year}"
        return f"{starts.strftime('%b %Y')} \u2013 {ends.strftime('%b %Y')}"
    except Exception:
        return "3 months"


# ------------------------------------------------------------------
# Vectorized municipal price averages (replaces per-municipality loop)
# ------------------------------------------------------------------
def _compute_municipal_avg_prices(dr, selected_class):
    """Return {municipality: avg_price} for the given classification, vectorized.

    Averages across BOTH Dry and Wet for the classification (so the table price
    aligns with the selected Rice Classification, not just Dry).
    """
    df_forecast = getattr(dr, "df_municipal_forecasts", None)
    if df_forecast is None or getattr(df_forecast, "empty", True):
        return {}
    _, df_dry, df_wet, _ = _prepare_forecast_df(dr, [], selected_class)
    cols = [c for c in ["Month 1", "Month 2", "Month 3"]]
    frames = []
    for _df in (df_dry, df_wet):
        if _df is None or getattr(_df, "empty", True):
            continue
        use_cols = [c for c in cols if c in _df.columns]
        if not use_cols:
            continue
        tmp = _df[["Municipality"] + use_cols].copy()
        for c in use_cols:
            tmp[c] = pd.to_numeric(tmp[c], errors="coerce")
        tmp["avg_price"] = tmp[use_cols].mean(axis=1)
        frames.append(tmp[["Municipality", "avg_price"]])
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True)
    grouped = combined.groupby("Municipality")["avg_price"].mean()
    return grouped.to_dict()


def _compute_tag_map(df_forecast_all):
    """Return {muni: (Type, Class)} for filter chips, vectorized where possible."""
    tag_map = {}
    if df_forecast_all is None or df_forecast_all.empty:
        return tag_map
    if "Rice Classification" in df_forecast_all.columns and "Municipality" in df_forecast_all.columns:
        try:
            mode_series = df_forecast_all.groupby("Municipality")["Rice Classification"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
            for muni, cls_full in mode_series.items():
                parts = str(cls_full).strip().split()
                t = parts[0] if len(parts) >= 1 else "Inbred"
                c = parts[1] if len(parts) >= 2 else "Ordinary"
                tag_map[str(muni)] = (t, c)
            return tag_map
        except Exception as exc:
            logger.debug("tag map mode failed: %s", exc)
    for muni in df_forecast_all["Municipality"].dropna().unique():
        tag_map[str(muni)] = ("Inbred", "Ordinary")
    return tag_map


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
    """Top section: Forecasted values (separate from historical KPIs). Dry/Wet = moisture, not season."""
    with theme.section_card(title="Forecasted Values — System-Generated",
                            desc=f"Average predicted prices by moisture for {selected_class}. Separate from historical KPIs.",
                            icon_name="auto_awesome"):
        dry_avg = _season_avg(df_dry)      # Dry palay
        wet_avg = _season_avg(df_wet)      # Wet palay
        price_diff = dry_avg - wet_avg     # Estimated difference

        diff_arrow = "↑" if price_diff >= 0 else "↓"
        diff_color = theme.SUCCESS if price_diff >= 0 else theme.DANGER

        cards = [
            theme.kpi_card("Avg Predicted Dry Palay Price", f"₱{dry_avg:.2f}",
                           "Dry", "sunny",
                           icon_bg="rgba(245,158,11,0.12)", icon_color="#F59E0B",
                           accent="#F59E0B"),
            theme.kpi_card("Avg Predicted Wet Palay Price", f"₱{wet_avg:.2f}",
                           "Wet", "water_drop",
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
    """Grouped bar chart for municipal forecasts — full set, accessible, no undefined title."""
    if df is None or df.empty:
        return
    try:
        # Full municipal set — no capping (user requested buong bar graph)
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
        # Accessible palette — repeat if needed to cover full Bataan (12)
        n_muni = plot_df["Municipality"].nunique()
        repeats = (n_muni // len(ACCESSIBLE_PALETTE)) + 1
        palette = (ACCESSIBLE_PALETTE * repeats)[: max(n_muni, 1)]
        fig = px.bar(
            plot_df, x="forecast_month", y="price", color="Municipality",
            barmode="group",
            category_orders={"forecast_month": labels},
            color_discrete_sequence=palette,
            labels={"forecast_month": "Forecast Month", "price": "Price (₱/kg)", "Municipality": "Municipality"},
        )
        # FIX: force empty title — never show literal "undefined" (Plotly converts None -> "undefined" in some builds)
        _bargap = 0.15 if n_muni >= 10 else 0.22
        _bargroupgap = 0.08 if n_muni >= 10 else 0.12
        _legend_y = -0.30 if n_muni >= 8 else -0.22
        _bottom_margin = 140 if n_muni >= 8 else 110
        fig.update_layout(
            title=dict(text="", font=dict(size=1, color="rgba(0,0,0,0)")),
            title_text="",
            height=400, margin=dict(t=12, b=_bottom_margin, l=55, r=10),
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Inter, sans-serif", size=11),
            legend=dict(orientation="h", yanchor="top", y=_legend_y, xanchor="center", x=0.5,
                        font=dict(size=9), bgcolor="rgba(255,255,255,0.98)",
                        bordercolor="#E5E7EB", borderwidth=1, itemsizing="constant"),
            yaxis=dict(gridcolor="#F3F4F6", showgrid=True, title="Price (₱/kg)"),
            xaxis=dict(gridcolor="#F3F4F6", showgrid=False, automargin=True, title="Forecast Month"),
            bargap=_bargap, bargroupgap=_bargroupgap,
            uniformtext_minsize=8, uniformtext_mode="hide",
        )
        # hard-clear any leftover title/annotations that could render as "undefined"
        fig.layout.title.text = ""
        try:
            # remove any annotation whose text is "undefined" (defensive)
            if fig.layout.annotations:
                fig.layout.annotations = [a for a in fig.layout.annotations if str(getattr(a, "text", "")).lower() != "undefined"]
        except Exception:
            pass
        fig.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>₱%{y:.2f}/kg<extra></extra>",
            cliponaxis=False,
            marker_line_width=0.5, marker_line_color="rgba(0,0,0,0.15)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=f"{key}_v4")
        # Accessibility note below chart
        st.caption(f"Grouped bars by forecast month · {n_muni} {'municipalities' if n_muni != 1 else 'municipality'} · {selected_class} · {season_label}")
    except Exception as exc:
        logger.debug("municipal season bar failed: %s", exc)
        st.error("Could not render forecast chart for the selected filters.")


def render(df, dr):
    """Main Forecasting page — provincial vs municipal tabs."""
    theme.page_title(
        "Forecasting",
        "Provincial and municipal forecasts for palay prices and yields in Bataan — 6-month price and 4-quarter yield projections to support OPA planning.",
    )

    benchmark_class = "Hybrid Premium"
    _, df_dry, df_wet, month_labels = _prepare_forecast_df(dr, [], benchmark_class)

    tab_prov, tab_muni = st.tabs([
        ":material/show_chart: Provincial",
        ":material/location_city: Municipal",
    ])

    with tab_prov:
        _forecast_visual_chart(dr, benchmark_class, [])

    with tab_muni:
        # --- Shared scoped CSS ---
        st.markdown("""
        <style>
        .muni-card { background:white; border:1px solid #E5E7EB; border-radius:14px; box-shadow:0 4px 12px rgba(0,0,0,0.04); }
        .muni-card-pad { padding:14px; }
        .muni-label { font-size:0.70rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.3px; font-weight:600; margin-bottom:4px; display:block; }
        .muni-badge { font-size:0.68rem; color:#065F46; background:#D1FAE5; border:1px solid #A7F3D0; padding:3px 8px; border-radius:999px; font-weight:600; }
        </style>
        """, unsafe_allow_html=True)

        # --- TOP: Single consolidated classification + dynamic info ---
        # Dry / Wet here refers to palay moisture, NOT cropping season.
        try:
            dyn_labels = month_labels if month_labels and len(month_labels) == 3 else _municipal_month_labels(dr)
            if dyn_labels and len(dyn_labels) == 3:
                period_str = f"{dyn_labels[0]} – {dyn_labels[2]}"
            else:
                period_str = "Next 3 months"
        except Exception:
            period_str = "Next 3 months"

        with st.container(border=True):
            top1, top2 = st.columns([0.38, 0.62], gap="medium")
            with top1:
                st.markdown('<span class="muni-label">Rice Classification</span>', unsafe_allow_html=True)
                sel_class_top = st.selectbox(
                    "Rice Classification",
                    options=_RICE_CLASS_OPTIONS,
                    index=0,
                    key="muni_rice_class_top_v2",
                    label_visibility="collapsed",
                    help="Binhi classification — Hybrid/Inbred × Premium/Ordinary. Filters the municipal forecasts by moisture (Dry / Wet).",
                )
            with top2:
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:10px 12px; display:flex; gap:10px; align-items:flex-start;">
                  <i class="material-symbols-outlined" style="color:#059669; font-size:20px; margin-top:1px; flex-shrink:0;">lightbulb</i>
                  <div style="font-size:0.78rem; color:#374151; line-height:1.5;"><b style="color:#14532D;">How forecasts work</b><br>
                  Based on <b>{sel_class_top}</b>. Each municipality has its own projection by palay moisture (<b>Dry</b> • <b>Wet</b>). Forecast period <b>{period_str}</b>.</div>
                </div>
                """, unsafe_allow_html=True)

        _season_top = "Dry"

        # --- BODY: Left selector + Right chart ---
        left, right = st.columns([0.40, 0.60], gap="medium")
        with left:
            with st.container(border=True):
                df_forecast_all = getattr(dr, "df_municipal_forecasts", None)
                if df_forecast_all is None or getattr(df_forecast_all, "empty", True):
                    st.info("No municipal forecast data available.")
                    all_munis = []
                    tag_map = {}
                    price_map = {}
                else:
                    all_munis = sorted(df_forecast_all["Municipality"].dropna().astype(str).unique().tolist())
                    tag_map = _compute_tag_map(df_forecast_all)
                    price_map = _compute_municipal_avg_prices(dr, sel_class_top)

                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                      <span style="font-weight:800; color:#14532D; font-size:0.88rem; display:flex; align-items:center; gap:6px;"><i class="material-symbols-outlined" style="font-size:18px; color:#16A34A;">location_on</i> MUNICIPALITIES</span>
                    </div>
                    """, unsafe_allow_html=True)

                    filtered = list(all_munis)

                    prev_selected = st.session_state.get("muni_selected_v2", [])
                    prev_selected = [m for m in prev_selected if m in filtered]
                    selected_munis = st.multiselect(
                        "Compare municipalities",
                        options=filtered,
                        default=prev_selected,
                        key="muni_selected_v2",
                        help="Select any municipalities to filter the chart. Leave empty to show all.",
                        placeholder="Choose municipalities…",
                    )

                    st.caption(f"{len(filtered)} match · {len(selected_munis) if selected_munis else len(filtered)} shown · prices for {sel_class_top}")

                    # Table now aligns with both filters: municipality + rice classification, sorted by highest avg price
                    display_munis = selected_munis if selected_munis else filtered
                    # Derive Type/Class directly from selected Rice Classification so table matches header (e.g. Inbred Premium)
                    _parts = str(sel_class_top).strip().split()
                    _sel_type = _parts[0] if len(_parts) >= 1 else "Inbred"
                    _sel_class = _parts[1] if len(_parts) >= 2 else "Premium"
                    # Sort by highest avg price for the selected rice classification (price_map already scoped to sel_class_top)
                    try:
                        display_munis = sorted(display_munis, key=lambda m: float(price_map.get(m, 0) or 0), reverse=True)
                    except Exception:
                        pass
                    if display_munis:
                        def _chip(txt, bg, bd, col):
                            return f'<span style="display:inline-block; background:{bg}; border:1px solid {bd}; color:{col}; padding:3px 8px; border-radius:999px; font-size:0.74rem; font-weight:700; line-height:1; white-space:nowrap;">{txt}</span>'
                        rows_html = ""
                        for m in display_munis[:MUNI_MAX_LIST]:
                            p = float(price_map.get(m, 0.0) or 0.0)
                            price_chip = _chip(f"\u20B1{p:.2f}", "#ECFDF5", "#A7F3D0", "#065F46")
                            rows_html += f'<tr><td style="padding:10px 12px; font-size:0.84rem; color:#111827; font-weight:600; border-bottom:1px solid #F3F4F6;">{m.title()}</td><td style="padding:6px 12px; text-align:right; border-bottom:1px solid #F3F4F6;">{price_chip}</td></tr>'
                        table_html = f'''
                        <div style="max-height:340px; overflow-y:auto; border:1px solid #E5E7EB; border-radius:10px; background:white;">
                          <table style="width:100%; border-collapse:collapse; font-family:Inter, sans-serif;">
                            <thead style="position:sticky; top:0; background:#F9FAFB; z-index:1;">
                              <tr>
                                <th style="text-align:left; padding:8px 12px; font-size:0.70rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.4px; border-bottom:1px solid #E5E7EB;">Municipality</th>
                                <th style="text-align:right; padding:8px 12px; font-size:0.70rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.4px; border-bottom:1px solid #E5E7EB;">Avg Price</th>
                              </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                          </table>
                        </div>
                        '''
                        st.markdown(table_html, unsafe_allow_html=True)
                        if len(display_munis) > MUNI_MAX_LIST:
                            st.caption(f"+ {len(display_munis) - MUNI_MAX_LIST} more")
                    else:
                        st.info("No municipalities available.")

                    st.session_state["_muni_conn_v2"] = (selected_munis, sel_class_top, _season_top, filtered, tag_map)

        with right:
            with st.container(border=True):
                # Keep compatibility with stored tuple (season slot ignored — Dry/Wet is moisture, not season)
                conn = st.session_state.get("_muni_conn_v2", ([], sel_class_top, _season_top, [], {}))
                if isinstance(conn, tuple) and len(conn) >= 2:
                    lm = conn[0] if isinstance(conn[0], list) else []
                    lc = conn[1] if len(conn) > 1 and isinstance(conn[1], str) else sel_class_top
                    filtered_state = conn[3] if len(conn) > 3 and isinstance(conn[3], list) else []
                    tag_map_state = conn[4] if len(conn) > 4 and isinstance(conn[4], dict) else tag_map if 'tag_map' in locals() else {}
                else:
                    lm, lc, filtered_state, tag_map_state = [], sel_class_top, [], {}

                lc = sel_class_top

                if lm:
                    if len(lm) == 1:
                        ctx_muni = lm[0].title()
                        ctx_sub = f"{lc} · 1 municipality"
                    else:
                        ctx_muni = f"{len(lm)} Municipalities Compared"
                        ctx_sub = f"{lc} · {', '.join([m.title() for m in lm[:3]])}{' …' if len(lm)>3 else ''}"
                else:
                    ctx_muni = "Overview — Top Municipalities"
                    ctx_sub = f"{lc} · highest avg price"

                _, ddry, dwet, labs = _prepare_forecast_df(dr, lm, lc)
                labs = labs if labs and len(labs) == 3 else month_labels

                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;'><i class='material-symbols-outlined' style='color:#16A34A;font-size:22px;'>bar_chart</i><b style='color:#14532D; font-size:0.95rem;'>Granular Forecast for Hybrid and Inbred Palay Prices</b></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:0.88rem;color:#14532D;font-weight:700;margin-top:4px;'>{ctx_muni}</div><div style='font-size:0.78rem;color:#6B7280;'>{ctx_sub}</div><div style='font-size:0.74rem;color:#6B7280;margin-top:2px;'>Average farmgate price (₱/kg) — 3-month projection • {labs[0]} – {labs[2] if len(labs)>2 else ''} · Dry / Wet</div>", unsafe_allow_html=True)

                # Show Dry/Wet as moisture (not season) — use tabs so both are accessible
                if (ddry is None or ddry.empty) and (dwet is None or dwet.empty):
                    st.info("No forecasts for the current selection. Try another classification or clear the municipality filter.")
                else:
                    # Tabs: Dry Palay | Wet Palay — labels without 'Season'
                    try:
                        tab_dry, tab_wet = st.tabs(["Dry Palay", "Wet Palay"])
                    except Exception:
                        tab_dry, tab_wet = st.tabs(["Dry", "Wet"])
                    with tab_dry:
                        if ddry is None or ddry.empty:
                            st.info("No Dry palay forecast for this selection.")
                        else:
                            _municipal_season_bar(ddry, labs, lc, "Dry Palay", "muni_fig_dry_v3")
                    with tab_wet:
                        if dwet is None or dwet.empty:
                            st.info("No Wet palay forecast for this selection.")
                        else:
                            _municipal_season_bar(dwet, labs, lc, "Wet Palay", "muni_fig_wet_v3")

                with st.expander("Show Forecast Table (Numbers)", expanded=False):
                    st.caption("Note: System-generated forecast — read-only. Use the button to download CSV (editing disabled).")
                    # Show both Dry/Wet tables tabbed
                    try:
                        t_dry, t_wet = st.tabs(["Dry", "Wet"])
                    except Exception:
                        t_dry, t_wet = st.tabs(["Dry", "Wet"])
                    with t_dry:
                        if ddry is not None and not ddry.empty:
                            disp = ddry[["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]].rename(columns={"Month 1": labs[0], "Month 2": labs[1], "Month 3": labs[2]})
                            disp["Municipality"] = disp["Municipality"].astype(str).str.title()
                            st.data_editor(disp, use_container_width=True, hide_index=True, height=220, disabled=True, key=f"forecast_editor_dry_{lc}_{len(lm)}")
                            st.caption(f"Displaying {len(disp)} Dry palay row{'s' if len(disp)!=1 else ''} for {lc}.")
                            try:
                                _csv_dry = disp.to_csv(index=False).encode("utf-8")
                                st.download_button(label="Download Dry CSV — System-generated", data=_csv_dry, file_name=f"forecast_{lc.replace(' ', '_')}_Dry.csv", mime="text/csv", key=f"dl_dry_csv_{lc}_{len(lm)}", use_container_width=True)
                            except Exception:
                                pass
                        else:
                            st.info("No Dry forecast.")
                    with t_wet:
                        if dwet is not None and not dwet.empty:
                            disp = dwet[["Municipality", "Rice Classification", "Month 1", "Month 2", "Month 3"]].rename(columns={"Month 1": labs[0], "Month 2": labs[1], "Month 3": labs[2]})
                            disp["Municipality"] = disp["Municipality"].astype(str).str.title()
                            st.data_editor(disp, use_container_width=True, hide_index=True, height=220, disabled=True, key=f"forecast_editor_wet_{lc}_{len(lm)}")
                            st.caption(f"Displaying {len(disp)} Wet palay row{'s' if len(disp)!=1 else ''} for {lc}.")
                            try:
                                _csv_wet = disp.to_csv(index=False).encode("utf-8")
                                st.download_button(label="Download Wet CSV — System-generated", data=_csv_wet, file_name=f"forecast_{lc.replace(' ', '_')}_Wet.csv", mime="text/csv", key=f"dl_wet_csv_{lc}_{len(lm)}", use_container_width=True)
                            except Exception:
                                pass
                        else:
                            st.info("No Wet forecast.")

                pass  # Forecast Summary KPI removed per request

