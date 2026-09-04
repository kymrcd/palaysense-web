"""
PalaySense LGU Dashboard — Overview (Dashboard page)
====================================================
Decision-support layout for the Office of the Provincial Agriculturist (OPA).

Top section:
 • Primary KPI row (5 compact cards):
   Total Production, Average Yield, Harvested Area, Supply Status, Forecast Period
 • Market Snapshot (2 compact cards): Regular & Fancy forecast price with % change.

Below: the two main trend charts (Provincial Price Trend + Provincial Yield Trend)
with dashed forecasts. Reuses the existing backend data layer and calculations.

Additional restored visuals from the backup:
 • Provincial Quarterly Production Bar Chart (Q1–Q4) + Production Insight Summary card
 • Top 5 Municipalities horizontal bar + Dry/Wet seasonal pie charts
 • Yield Forecast Summary card (Avg/Peak/Low) beside the yield trend.
 • Insights Narrative / Storytelling Mode
 • Peak price annotations on price charts
 • Section tabs for Historical/Forecast navigation
 • Sidebar Quick View radiobuttons for section navigation
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app_pages.lgu_dashboard import theme
from app_pages.lgu_dashboard import data_layer as dl


def _format_signed(num, suffix="", decimals=0):
  sign = "+" if num >= 0 else ""
  return f"{sign}{num:,.{decimals}f}{suffix}"


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


def _pct_vs_hist(fc, avg):
  """% change of a forecast value vs a historical average (NaN/zero-safe).

  Returns 0.0 when the forecast is missing or the baseline is NaN/zero,
  preventing the '₱0.00/kg (-100.0%)' KPI bug.
  """
  if fc is None or avg is None:
    return 0.0
  try:
    c = float(fc)
    b = float(avg)
  except (TypeError, ValueError):
    return 0.0
  if pd.isna(c) or pd.isna(b) or b == 0:
    return 0.0
  return ((c - b) / b) * 100


def _safe_mean(values, default=0.0):
  if values is None or len(values) == 0:
    return default
  try:
    s = pd.Series(values, dtype="float64").dropna()
    return float(s.mean()) if not s.empty else default
  except Exception:
    return default


def _safe_max(values, default=0.0):
  if values is None or len(values) == 0:
    return default
  try:
    s = pd.Series(values, dtype="float64").dropna()
    return float(s.max()) if not s.empty else default
  except Exception:
    return default


def _safe_min(values, default=0.0):
  if values is None or len(values) == 0:
    return default
  try:
    s = pd.Series(values, dtype="float64").dropna()
    return float(s.min()) if not s.empty else default
  except Exception:
    return default


def _pick_column(df, candidates):
  if df is None:
    return None
  return next((c for c in candidates if c in df.columns), None)


def _pct_change(current, baseline):
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


# ------------------------------------------------------------------
# BENCHMARK REFERENCE LINE HELPERS
# ------------------------------------------------------------------
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
    fig.add_hline(
      y=y, line_dash="dot", line_width=1.2, line_color=line_color, opacity=0.6,
      annotation_text=label, annotation_position=annotation_position,
      annotation=dict(font=dict(size=10, color=line_color), bgcolor="rgba(255,255,255,0.85)"),
    )
  except Exception:
    try:
      fig.add_hline(y=y, line_dash="dot", line_width=1.2, line_color=line_color, opacity=0.6, annotation_text=label, annotation_position=annotation_position)
    except Exception:
      pass
  return fig


def _benchmark_yield_config(benchmark_option, historical_avg):
  opt = str(benchmark_option).strip() if benchmark_option is not None else ""
  if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
    if historical_avg is None or pd.isna(historical_avg):
      return None
    try:
      v = float(historical_avg)
    except (TypeError, ValueError):
      return None
    if pd.isna(v):
      return None
    return (v, f"Bataan 10-Yr Avg Yield ({v:.2f} MT/ha)", "#616161")
  if opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline", "DA Target (4.50 MT/ha)", "DA Target", "DA Target Yield (4.50 MT/ha)"):
    return (4.50, "DA Target Yield (4.50 MT/ha)", "#2E7D32")
  return None


def _benchmark_price_config(benchmark_option, historical_avg):
  opt = str(benchmark_option).strip() if benchmark_option is not None else ""
  if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
    if historical_avg is None or pd.isna(historical_avg):
      return None
    try:
      v = float(historical_avg)
    except (TypeError, ValueError):
      return None
    if pd.isna(v):
      return None
    return (v, f"Bataan 10-Yr Avg Regular Price (\u20B1{v:.2f}/kg)", "#616161")
  if opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline", "NFA Floor Price (\u20B119.00/kg)", "NFA Floor Price"):
    return (19.00, "NFA Procurement Floor Price (\u20B119.00/kg)", "#EF4444")
  return None


def _normalize_benchmarks(benchmark_option):
  if benchmark_option is None:
    return set()
  if isinstance(benchmark_option, (list, set, tuple)):
    return {str(o).strip() for o in benchmark_option if str(o).strip() and str(o).strip() not in ("Itago (None)", "Wala")}
  s = str(benchmark_option).strip()
  if not s or s in ("Itago (None)", "Wala"):
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
        if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
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
        elif opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline", "DA Target (4.50 MT/ha)", "DA Target"):
          cfg = _benchmark_yield_config(opt, None)
          if cfg is not None:
            y_val, label, color = cfg
            pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
            fig = _add_benchmark_ref_line(fig, y_val, label, line_color=color, annotation_position=pos)
        continue
      if chart_type == "price":
        if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
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
        elif opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline"):
          fig = _add_benchmark_ref_line(fig, 19.00, "NFA Floor Price (\u20B119.00/kg)", line_color="#EF4444", annotation_position="bottom left")
          fig = _add_benchmark_ref_line(fig, 23.75, "Fancy Commercial Target (\u20B123.75/kg)", line_color="#F59E0B", annotation_position="top left")
        elif opt in ("NFA Floor Price (\u20B119.00/kg)", "NFA Floor Price"):
          fig = _add_benchmark_ref_line(fig, 19.00, "NFA Floor Price (\u20B119.00/kg)", line_color="#EF4444", annotation_position="bottom left")
        continue
    except Exception:
      continue
  return fig


def _period_suffix(period: str) -> str:
  if not period:
    return ""
  p = str(period).strip().upper()
  if p == "ANNUAL":
    return ""
  if p in ("SEMESTER 1", "SEM 1"):
    return " \u2022 Sem 1"
  if p in ("SEMESTER 2", "SEM 2"):
    return " \u2022 Sem 2"
  if p == "QUARTER 1":
    return " \u2022 Q1"
  if p == "QUARTER 2":
    return " \u2022 Q2"
  if p == "QUARTER 3":
    return " \u2022 Q3"
  if p == "QUARTER 4":
    return " \u2022 Q4"
  if p == "QUARTERLY":
    return " \u2022 Quarterly"
  if p == "MONTHLY":
    return " \u2022 Monthly"
  return ""


def _kpi_subtext_total_production(start_year: int, end_year: int, period: str, muni_name: str, has_data: bool = True) -> str:
  suffix = _period_suffix(period)
  muni_is_all = (not muni_name or muni_name == "All Municipalities")
  if start_year == end_year:
    y = end_year
    base = f"Total for {y}" if muni_is_all else f"Sum for {muni_name} ({y})"
    return f"{base}{suffix}" if suffix else base
  else:
    base = f"Sum across {start_year} \u2013 {end_year}"
    if not muni_is_all:
      base += f" \u2022 {muni_name}"
    return f"{base}{suffix}" if suffix else base


def _kpi_subtext_yield_or_area(*, start_year: int, end_year: int, period: str, muni_name: str, delta: float | None, prev_year: int | None, has_prev: bool, unit: str, decimals: int = 2) -> str:
  suffix = _period_suffix(period)
  muni_is_all = (not muni_name or muni_name == "All Municipalities")
  muni_suffix = "" if muni_is_all else f" \u2022 {muni_name}"
  if start_year == end_year:
    if has_prev and delta is not None and prev_year is not None:
      try:
        d = float(delta)
        if pd.isna(d):
          raise ValueError
      except Exception:
        has_prev = False
      else:
        sign = "+" if d >= 0 else ""
        delta_str = f"{sign}{d:,.{decimals}f}{unit} vs {prev_year}"
        return f"{delta_str}{suffix}" if suffix else delta_str
    base = f"Data as of {end_year}"
    if not muni_is_all:
      base += f" \u2022 {muni_name}"
    return f"{base}{suffix}" if suffix else base
  else:
    base = f"Average across {start_year} \u2013 {end_year}"
    if not muni_is_all:
      base += f" \u2022 {muni_name}"
    return f"{base}{suffix}" if suffix else base


def _filter_df_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
  if df is None or df.empty or "date" not in df.columns:
    return df
  p = str(period).strip().upper() if period else "ANNUAL"
  try:
    d = pd.to_datetime(df["date"], errors="coerce")
    months = d.dt.month
    quarters = d.dt.quarter
  except Exception:
    return df
  if p in ("SEMESTER 1", "SEM 1"):
    return df[months.between(1, 6)]
  if p in ("SEMESTER 2", "SEM 2"):
    return df[months.between(7, 12)]
  if p == "QUARTER 1":
    return df[quarters == 1]
  if p == "QUARTER 2":
    return df[quarters == 2]
  if p == "QUARTER 3":
    return df[quarters == 3]
  if p == "QUARTER 4":
    return df[quarters == 4]
  return df


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
  if p in ("SEMESTER 1", "SEM 1"):
    temp = temp[temp["semester"] == 1]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + " Sem 1"
    return grouped
  if p in ("SEMESTER 2", "SEM 2"):
    temp = temp[temp["semester"] == 2]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + " Sem 2"
    return grouped
  if p == "QUARTER 1":
    temp = temp[temp["quarter"] == 1]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q1"
    return grouped
  if p == "QUARTER 2":
    temp = temp[temp["quarter"] == 2]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q2"
    return grouped
  if p == "QUARTER 3":
    temp = temp[temp["quarter"] == 3]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q3"
    return grouped
  if p == "QUARTER 4":
    temp = temp[temp["quarter"] == 4]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q4"
    return grouped
  if p == "ANNUAL":
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str)
    return grouped
  elif p == "QUARTERLY":
    grouped = temp.groupby(["year", "quarter"]).mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q" + grouped["quarter"].astype(str)
    return grouped
  elif p == "MONTHLY":
    grouped = temp.groupby(["year", "month"]).mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped.apply(lambda r: f"{r['month_name']} {r['year']}", axis=1)
    return grouped
  else:
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str)
    return grouped


def _base_layout(fig, yaxis_title="", xaxis_title="Date"):
  """Apply the shared PalaySense plot styling to a figure."""
  fig.update_layout(
    yaxis_title=yaxis_title, xaxis_title=xaxis_title,
    height=300, hovermode="x unified",
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family=theme.FONT, size=11),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
    xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
    margin=dict(t=30, b=40, l=40, r=40),
  )
  return fig


def _price_historical_chart(df, year=None, period="ANNUAL", benchmark_option="Wala"):
  """Line chart for the selected year range and period with peak + benchmark."""
  if year is None:
    hist = df.copy()
  else:
    hist = dl.filter_by_year(df, year)
  if hist.empty:
    return go.Figure()
  value_cols = []
  if "fancy_palay_price" in hist.columns:
    value_cols.append("fancy_palay_price")
  if "other_variety_price" in hist.columns:
    value_cols.append("other_variety_price")
  if not value_cols:
    return go.Figure()
  grouped = _group_by_period(hist, period, value_cols)
  if grouped.empty:
    return go.Figure()
  _p = str(period).strip().upper() if period else "ANNUAL"
  if _p == "ANNUAL":
    xaxis_title = "Year"
  elif _p in ("SEMESTER 1", "SEM 1", "SEMESTER 2", "SEM 2"):
    xaxis_title = "Year (Semester)"
  elif _p in ("QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"):
    xaxis_title = "Year"
  elif _p == "QUARTERLY":
    xaxis_title = "Quarter"
  elif _p == "MONTHLY":
    xaxis_title = "Month"
  else:
    xaxis_title = "Year"
  fig = go.Figure()
  if "fancy_palay_price" in grouped.columns:
    fig.add_trace(go.Scatter(
      x=grouped["period_label"], y=grouped["fancy_palay_price"],
      mode="lines+markers", name="Fancy Palay",
      line=dict(color=theme.FANCY_COLOR, width=2.5), marker=dict(size=4),
    ))
    peak_idx = grouped["fancy_palay_price"].idxmax()
    if pd.notna(peak_idx):
      peak_row = grouped.loc[peak_idx]
      fig.add_annotation(
        x=peak_row["period_label"], y=peak_row["fancy_palay_price"],
        text=f"▲ Peak: ₱{peak_row['fancy_palay_price']:.2f}/kg",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#16A34A",
        ax=0, ay=-50, font=dict(size=10, color="#15803D", weight="bold"),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1, borderpad=4,
      )
  if "other_variety_price" in grouped.columns:
    fig.add_trace(go.Scatter(
      x=grouped["period_label"], y=grouped["other_variety_price"],
      mode="lines+markers", name="Regular Palay",
      line=dict(color=theme.REGULAR_COLOR, width=2.5), marker=dict(size=4),
    ))
    peak_idx = grouped["other_variety_price"].idxmax()
    if pd.notna(peak_idx):
      peak_row = grouped.loc[peak_idx]
      fig.add_annotation(
        x=peak_row["period_label"], y=peak_row["other_variety_price"],
        text=f"▲ Peak: ₱{peak_row['other_variety_price']:.2f}/kg",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#6D28D9",
        ax=0, ay=50, font=dict(size=10, color="#6D28D9", weight="bold"),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1, borderpad=4,
      )
  fig = _apply_benchmarks_to_fig(fig, hist, "price", benchmark_option)
  fig.update_layout(height=370, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=xaxis_title, yaxis_title="₱/kg",
    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11, family=theme.FONT)),
    plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
    xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
  return fig


def _price_forecast_chart(df, dr, benchmark_option="Wala"):
  """Line chart: ONLY forecasted price values with benchmark + aligned arrays."""
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
    fig.add_trace(go.Scatter(
      x=fc_months, y=fancy_s.values,
      mode="lines+markers", name="Fancy Forecast",
      line=dict(color=theme.FANCY_COLOR, width=2.5, dash="dash"),
      marker=dict(size=6, symbol="diamond"), connectgaps=False,
    ))
    fig.add_trace(go.Scatter(
      x=fc_months, y=regular_s.values,
      mode="lines+markers", name="Regular Forecast",
      line=dict(color=theme.REGULAR_COLOR, width=2.5, dash="dash"),
      marker=dict(size=6, symbol="diamond"), connectgaps=False,
    ))
    fig = _apply_benchmarks_to_fig(fig, df, "price", benchmark_option)
    fig.update_layout(height=370, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title="₱/kg",
      legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11, family=theme.FONT)),
      plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
      xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    return fig
  except Exception:
    pass
  if not fig.data:
    return go.Figure()
  return _base_layout(fig, yaxis_title="₱ / kg", xaxis_title="Date")


def _yield_historical_chart(df, year=None, period="ANNUAL", benchmark_option="Wala"):
  """Line chart for historical yield with period + benchmark."""
  quarterly = dl.get_quarterly_yield(df)
  if year is None:
    hist = quarterly.copy()
  else:
    hist = quarterly[quarterly["year"] == year].copy()
  if hist.empty:
    return go.Figure()
  _p = str(period).strip().upper() if period else "ANNUAL"
  if _p in ("ANNUAL", "SEMESTER 1", "SEM 1", "SEMESTER 2", "SEM 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"):
    if not hist.empty:
      if _p == "ANNUAL":
        hist_grouped = hist.groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
        hist_grouped["period_label"] = hist_grouped["year"].astype(str)
        xaxis_title = "Year"
      elif _p in ("SEMESTER 1", "SEM 1"):
        hist["semester"] = np.where(hist["quarter"] <= 2, 1, 2)
        hist_grouped = hist[hist["semester"] == 1].groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
        hist_grouped["period_label"] = hist_grouped["year"].astype(str) + " Sem 1"
        xaxis_title = "Year (Semester)"
      elif _p in ("SEMESTER 2", "SEM 2"):
        hist["semester"] = np.where(hist["quarter"] <= 2, 1, 2)
        hist_grouped = hist[hist["semester"] == 2].groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
        hist_grouped["period_label"] = hist_grouped["year"].astype(str) + " Sem 2"
        xaxis_title = "Year (Semester)"
      else:
        qnum = int(_p.split()[-1])
        hist_grouped = hist[hist["quarter"] == qnum].groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
        hist_grouped["period_label"] = hist_grouped["year"].astype(str) + f"-Q{qnum}"
        xaxis_title = "Year"
    else:
      hist_grouped = pd.DataFrame()
      xaxis_title = "Year"
  elif _p == "MONTHLY" and not hist.empty:
    hist_grouped = hist.copy()
    hist_grouped["period_label"] = "Q" + hist_grouped["quarter"].astype(str) + " " + hist_grouped["year"].astype(str)
    xaxis_title = "Period"
  else:
    hist_grouped = hist.copy()
    hist_grouped["period_label"] = "Q" + hist_grouped["quarter"].astype(str) + " " + hist_grouped["year"].astype(str)
    xaxis_title = "Quarter"
  if hist_grouped.empty:
    return go.Figure()
  fig = go.Figure()
  fig.add_trace(go.Scatter(
    x=hist_grouped["period_label"], y=hist_grouped["quarterly_yield_mt_per_ha"],
    mode="lines+markers", name="Historical Yield",
    line=dict(color=theme.HISTORICAL_COLOR, width=3), marker=dict(size=7),
  ))
  peak_idx = hist_grouped["quarterly_yield_mt_per_ha"].idxmax()
  if pd.notna(peak_idx):
    peak_row = hist_grouped.loc[peak_idx]
    fig.add_annotation(
      x=peak_row["period_label"], y=peak_row["quarterly_yield_mt_per_ha"],
      text=f"▲ Peak: {peak_row['quarterly_yield_mt_per_ha']:.2f} MT/ha",
      showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
      ax=0, ay=-45, font=dict(size=10, color="#C2410C", weight="bold"),
      bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
    )
  fig = _apply_benchmarks_to_fig(fig, hist, "yield", benchmark_option)
  fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=xaxis_title, yaxis_title="MT/ha",
    legend=dict(orientation="h", yanchor="bottom", y=-0.30, xanchor="center", x=0.5, font=dict(size=11, family=theme.FONT)),
    plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
    xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
  return fig


def _yield_forecast_chart(dr, df, benchmark_option="Wala"):
  """Line chart: ONLY forecasted yield with benchmark."""
  fig = go.Figure()
  try:
    yield_fc = list(dr.forecast_quarterly_yield) if dr.forecast_quarterly_yield else []
    if not yield_fc:
      return fig
    latest = dl.get_latest_date(df)
    anchor = latest if latest is not None and not pd.isna(latest) else pd.Timestamp.today()
    fc_quarters = pd.period_range(start=pd.Period(anchor, freq="Q") + 1, periods=len(yield_fc), freq="Q")
    fc_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
    fig.add_trace(go.Scatter(
      x=fc_labels, y=yield_fc, mode="lines+markers", name="Forecast Yield",
      line=dict(color=theme.FORECAST_COLOR, width=3, dash="dash"), marker=dict(size=8, symbol="diamond"),
    ))
    peak_val = float(pd.Series(yield_fc).max())
    peak_idx = yield_fc.index(peak_val) if peak_val in yield_fc else -1
    if 0 <= peak_idx < len(fc_labels):
      fig.add_annotation(
        x=fc_labels[peak_idx], y=peak_val, text=f"▲ Peak: {peak_val:.2f} MT/ha",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
        ax=0, ay=-45, font=dict(size=10, color="#C2410C", weight="bold"),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
      )
    fig = _apply_benchmarks_to_fig(fig, dl.get_quarterly_yield(df), "yield", benchmark_option)
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title="MT/ha",
      legend=dict(orientation="h", yanchor="bottom", y=-0.30, xanchor="center", x=0.5, font=dict(size=11, family=theme.FONT)),
      plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
      xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    return fig
  except Exception:
    pass
  if not fig.data:
    return go.Figure()
  return _base_layout(fig, yaxis_title="Yield (MT/ha)", xaxis_title="Quarter")


def _supply_status_display(raw_status):
  """Map the backend supply status to the OPA labels (Surplus / Balanced / At Risk)."""
  if raw_status == "Surplus":
    return "Surplus"
  if raw_status == "Balanced":
    return "Balanced"
  return "At Risk"


def _production_quarterly(df, year):
  """Provincial Quarterly Production Bar Chart + Production Insight Summary card."""
  with theme.section_card(title="Provincial Quarterly Production",
              desc="Production per quarter with high/low insight.",
              icon_name="bar_chart"):
    if df is None or getattr(df, "empty", True) or "date" not in df.columns:
        st.info("No production data — no chart to display (0 values).")
        return
    prod = df.copy()
    prod["year"] = pd.to_datetime(prod["date"]).dt.year
    prod["quarter"] = pd.to_datetime(prod["date"]).dt.quarter
    sub = prod[prod["year"] == year] if year is not None else prod

    if sub.empty:
      st.info("No production data for the selected year.")
      return

    if "production_total" not in sub.columns:
      st.info("No production_total column available.")
      return
    q_avg = sub.groupby("quarter")["production_total"].mean().reset_index()
    q_avg["quarter"] = "Q" + q_avg["quarter"].astype(str)

    col1, col2 = st.columns([2.2, 1], gap="medium")
    with col1:
      fig = px.bar(
        q_avg, x="quarter", y="production_total", color="quarter",
        labels={"quarter": "Quarter", "production_total": "Production (MT)"},
        color_discrete_map={"Q1": "#FF9800", "Q2": "#C62828",
                  "Q3": "#66BB6A", "Q4": "#FFB2C8"},
      )
      fig.update_layout(
        yaxis_title="Production (MT)", xaxis_title="Quarter",
        showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family=theme.FONT, size=12),
        margin=dict(t=30, b=40, l=40, r=40),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
      )
      fig.update_traces(marker_line_width=0)
      st.plotly_chart(fig, use_container_width=True, key=f"overview_prod_q_{year}")

    with col2:
      if not q_avg.empty:
        highest = q_avg.loc[q_avg["production_total"].idxmax()]
        lowest = q_avg.loc[q_avg["production_total"].idxmin()]
        avg_p = q_avg["production_total"].mean()
        trend = ("increasing" if q_avg["production_total"].iloc[-1]
             > q_avg["production_total"].iloc[0] else "decreasing")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.5rem;
              border-radius:16px; border-left:6px solid #2E7D32;
              box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.95rem; line-height:1.7;">
          <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.8rem;">
            <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Production Insight Summary
          </div>
          <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">emoji_events</i> Highest Production: <b style="color:#2E7D32;">{highest['quarter']}</b></div>
          <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_down</i> Lowest Production: <b style="color:#C62828;">{lowest['quarter']}</b></div>
          <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Average Production: <b>{avg_p:,.0f} MT</b></div>
          <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.8rem 0;">
          <div style="font-size:0.95rem; font-weight:600; color:#1B5E20;">
            <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_up</i> Overall trend:
            <span style="color:#2E7D32; font-weight:700;">{trend.upper()}</span>
             pattern over the selected period
          </div>
        </div>
        """, unsafe_allow_html=True)


def _top_municipalities_and_seasonal(dr, start_year, end_year):
  """Top 5 Municipalities Ranking (Historical Production) + Dry/Wet seasonal pies."""
  with theme.section_card(title="Top Municipalities & Seasonal Distribution",
              desc="Municipal production ranking and dry/wet season split.",
              icon_name="leaderboard"):
    muni = getattr(dr, "municipal_production_df", None)
    if muni is None or getattr(muni, "empty", True):
      muni = getattr(dr, "municipality_history_df", None)
    top5 = dl.get_top_5_producing_municipalities(muni, (start_year, end_year))

    if top5.empty:
      st.info("No municipality production data for the selected period.")
      return

    plot_top5 = top5.sort_values("palay_production")
    fig_top = px.bar(
      plot_top5,
      x="palay_production", y="municipality", orientation="h",
      color="palay_production",
      color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
      text=plot_top5["palay_production"].round(0).astype(int),
    )
    fig_top.update_layout(
      title=f"Top 5 Municipalities by Total Production ({start_year} – {end_year})",
      xaxis_title="Production (MT)", yaxis_title="Municipality",
      showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
      height=380, margin=dict(t=30, b=40, l=40, r=40),
      yaxis={"categoryorder": "total ascending"},
    )
    fig_top.update_traces(texttemplate='%{text:,}', textposition='outside')
    st.plotly_chart(fig_top, use_container_width=True,
            key=f"overview_top5_{start_year}_{end_year}")

    dry = dl.get_municipal_seasonal_production(muni, (start_year, end_year), season="dry")
    wet = dl.get_municipal_seasonal_production(muni, (start_year, end_year), season="wet")

    col_a, col_b = st.columns(2)
    with col_a:
      if not dry.empty:
        fig = px.pie(dry, names="municipality", values="production",
               color_discrete_sequence=px.colors.sequential.Greens[0:5][::-1])
        fig.update_layout(height=340, margin=dict(t=30, b=40, l=40, r=40))
        st.plotly_chart(fig, use_container_width=True,
                key=f"overview_dry_{start_year}_{end_year}")
      else:
        st.info("No dry season data.")
    with col_b:
      if not wet.empty:
        fig = px.pie(wet, names="municipality", values="production",
               color_discrete_sequence=px.colors.sequential.Teal[0:5][::-1])
        fig.update_layout(height=340, margin=dict(t=30, b=40, l=40, r=40))
        st.plotly_chart(fig, use_container_width=True,
                key=f"overview_wet_{start_year}_{end_year}")
      else:
        st.info("No wet season data.")


def _yield_summary_card(dr):
  """Yield Forecast Summary card (Avg / Peak / Low) — placed beside yield trend."""
  with theme.section_card(title="Yield Forecast Summary",
              desc="Forward-looking yield metrics for the next 4 quarters.",
              icon_name="query_stats"):
    try:
      yield_fc = list(dr.forecast_quarterly_yield)
    except Exception:
      yield_fc = []

    if not yield_fc:
      st.info("No data available for yield forecast.")
    else:
      s = pd.Series(yield_fc, dtype="float64").dropna()
      if s.empty:
        st.info("No data available for yield forecast.")
      else:
        avg_y = float(s.mean())
        max_y = float(s.max())
        min_y = float(s.min())
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem;
              border-radius:16px; border-left:6px solid #2E7D32;
              box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.95rem; line-height:1.8;">
          <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.5rem;">
            <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Yield Forecast Summary
          </div>
          <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_up</i> Average: <b>{avg_y:.2f} MT/ha</b></div>
          <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">emoji_events</i> Peak: <b>{max_y:.2f} MT/ha</b></div>
          <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_down</i> Low: <b>{min_y:.2f} MT/ha</b></div>
          <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
          <div style="font-size:0.85rem; color:#2E7D32;">Based on next 4 forecast quarters</div>
        </div>
        """, unsafe_allow_html=True)


def _insights_narrative(filtered_df, dr, end_year, selected_muni, selected_eco):
  """Dynamic Insights Narrative / Storytelling Mode."""
  with theme.section_card(title="Insights Narrative",
              desc="Auto-generated market summary based on your current filter selections.",
              icon_name="auto_stories"):
    try:
      hist_fancy = _safe_column(filtered_df, "fancy_palay_price")
      hist_regular = _safe_column(filtered_df, "other_variety_price")

      fancy_forecast = _safe_index(dr.forecast_3months_fancy, 0) if dr.forecast_3months_fancy else None
      regular_forecast = _safe_index(dr.forecast_variety_3months, 0) if dr.forecast_variety_3months else None

      # Calculate QoQ yield change
      quarterly = dl.get_quarterly_yield(filtered_df)
      yield_qoq = 0
      if len(quarterly) >= 2:
        q_current = quarterly["quarterly_yield_mt_per_ha"].iloc[-1]
        q_previous = quarterly["quarterly_yield_mt_per_ha"].iloc[-2]
        if pd.notna(q_current) and pd.notna(q_previous) and q_previous != 0:
          yield_qoq = ((q_current - q_previous) / q_previous) * 100

      # Forecast vs historical
      avg_fancy = hist_fancy.mean() if not hist_fancy.empty else None
      avg_regular = hist_regular.mean() if not hist_regular.empty else None
      fancy_fc_vs_hist = _pct_vs_hist(fancy_forecast, avg_fancy)
      regular_fc_vs_hist = _pct_vs_hist(regular_forecast, avg_regular)

      # Production total
      prod_total = filtered_df["production_total"].sum() if "production_total" in filtered_df.columns else 0

      # Determine trend words
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
        <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Quarterly Market Summary
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
          <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">lightbulb</i> This narrative is auto-generated for <strong>{'All Municipalities' if selected_muni == 'All Municipalities' else selected_muni}</strong>
          across the selected period. Adjust filters to update insights.
        </small>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_top_filter_bar(df):
  """Render a top horizontal filter toolbar for the overview page."""
  if df is None or getattr(df, "empty", True) or "year" not in df.columns:
      return None, None, "ANNUAL", "All Municipalities"
  years = sorted(pd.Series(df["year"].dropna().astype(int).unique()).tolist())
  if not years:
    return None, None, "ANNUAL", "All Municipalities"
  st.session_state.setdefault("lgu_start_year", years[0])
  st.session_state.setdefault("lgu_end_year", years[-1])
  st.session_state.setdefault("lgu_period", "ANNUAL")
  _valid_periods = ["ANNUAL", "SEMESTER 1", "SEMESTER 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4", "QUARTERLY", "MONTHLY"]
  if st.session_state.get("lgu_period") not in _valid_periods:
    st.session_state["lgu_period"] = "ANNUAL"
  st.session_state.setdefault("lgu_selected_muni", "All Municipalities")

  st.markdown(
    """
    <div style="margin:0.3rem 0 1rem 0; padding:0.8rem 1rem; border:1px solid #D8E6DA; border-radius:14px; background:#F8FBF7;">
    </div>
    """,
    unsafe_allow_html=True,
  )

  col1, col2, col3, col4 = st.columns([1.0, 1.0, 1.0, 1.2], gap="small")
  with col1:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">YEAR RANGE</div>', unsafe_allow_html=True)
    start_year = st.selectbox(
      "Start Year",
      options=years,
      index=years.index(st.session_state["lgu_start_year"]),
      key="lgu_start_year",
      label_visibility="collapsed",
    )
  with col2:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">TO</div>', unsafe_allow_html=True)
    end_year = st.selectbox(
      "End Year",
      options=years,
      index=years.index(st.session_state["lgu_end_year"]),
      key="lgu_end_year",
      label_visibility="collapsed",
    )
  with col3:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">PERIOD</div>', unsafe_allow_html=True)
    period_opts = ["ANNUAL", "SEMESTER 1", "SEMESTER 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"]
    # keep legacy fallback if somehow still stored
    _cur = st.session_state["lgu_period"]
    if _cur not in period_opts:
      _cur = "ANNUAL"
      st.session_state["lgu_period"] = "ANNUAL"
    period = st.selectbox(
      "Period",
      options=period_opts,
      index=period_opts.index(_cur),
      key="lgu_period",
      label_visibility="collapsed",
    )
  with col4:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">MUNICIPALITY</div>', unsafe_allow_html=True)
    muni_options = ["All Municipalities"]
    muni_options.extend(sorted(pd.Series(df.get("municipality", pd.Series(dtype="object")).dropna().unique()).tolist()))
    selected_muni = st.selectbox(
      "Municipality",
      options=muni_options,
      index=0 if st.session_state["lgu_selected_muni"] not in muni_options else muni_options.index(st.session_state["lgu_selected_muni"]),
      key="lgu_selected_muni",
      label_visibility="collapsed",
    )
  return start_year, end_year, period, selected_muni





def render(df, dr):
  """Main decision-support dashboard content for the OPA."""
  # Initialize display DataFrames to prevent UnboundLocalError
  df_dry_display = pd.DataFrame()
  df_wet_display = pd.DataFrame()

  theme.topbar(
    "Overview",
    "Provincial Palay Overview and Forecast Summary",
    as_of=dl.get_latest_month_label(df),
  )
  theme.close_header_card()

  # Banner — true empty vs clean state
  is_true_empty = not getattr(dr, "has_provincial_data", False)
  has_fc = getattr(dr, "has_forecasts", False)
  if is_true_empty:
      st.info("ℹ️ No data — showing 0 values and empty graphs. Upload data via Import Data to populate.")
  elif not has_fc:
      st.info("ℹ️ Forecasts are being prepared — historical graphs below are available. Upload data via Import Data to generate forecasts.")

  # Always show all sections
  show_all = True

  # Top Filter Toolbar — keep graphs/KPIs visible even when empty (show 0 / empty line)
  start_year, end_year, period, selected_muni = _render_top_filter_bar(df)
  if start_year is None:
      st.info("No year data available — showing empty KPIs and graphs (0 values, no line). Upload data to populate.")
      filtered_df = pd.DataFrame(columns=df.columns) if not df.empty else pd.DataFrame()
      start_year = end_year = 0
      period = "ANNUAL"
      selected_muni = "All Municipalities"
  else:
      filtered_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
  metrics = dl.get_year_metrics(filtered_df, end_year, dr)

  # ---- Dynamic KPI subtexts (period + muni aware, like farmer) ----
  total_production = dl.get_total_production(filtered_df, (start_year, end_year))
  if total_production is not None:
    total_display = f"{total_production:,.0f} MT"
    total_sub = _kpi_subtext_total_production(start_year, end_year, period, selected_muni)
  else:
    total_display = "0 MT"
    total_sub = "No data — 0 MT"

  # Average Yield dynamic subtext (historical mean, period-filtered, delta vs prev year)
  _yield_candidates = ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha", "Yield"]
  _yield_col = _pick_column(filtered_df, _yield_candidates) or _pick_column(df, _yield_candidates)
  _y_has_prev = False; _y_delta = None; _y_prev_year = None; _yield_display_val = None
  try:
    _y_cur_df = _filter_df_by_period(filtered_df, period)
    if _yield_col and not _y_cur_df.empty and _yield_col in _y_cur_df.columns:
      _y_cur_series = pd.to_numeric(_y_cur_df[_yield_col], errors="coerce").dropna()
      _yield_display_val = float(_y_cur_series.mean()) if not _y_cur_series.empty else None
    if start_year == end_year:
      _y_prev_year = end_year - 1
      _prev_raw = df[df["year"] == _y_prev_year].copy() if "year" in df.columns else pd.DataFrame()
      _prev_df = _filter_df_by_period(_prev_raw, period)
      if _yield_col and not _prev_df.empty and _yield_col in _prev_df.columns:
        _prev_series = pd.to_numeric(_prev_df[_yield_col], errors="coerce").dropna()
        _y_prev = float(_prev_series.mean()) if not _prev_series.empty else None
      else:
        _y_prev = None
      if _yield_display_val is not None and _y_prev is not None and not pd.isna(_y_prev) and _y_prev != 0:
        _y_delta = float(_yield_display_val - _y_prev); _y_has_prev = True
  except Exception:
    _y_has_prev = False; _y_delta = None
  if start_year == end_year and _yield_display_val is None:
    _yield_sub = f"Data as of {end_year}{_period_suffix(period)}"
    if selected_muni != "All Municipalities":
      _yield_sub += f" \u2022 {selected_muni}"
  else:
    _yield_sub = _kpi_subtext_yield_or_area(start_year=start_year, end_year=end_year, period=period, muni_name=selected_muni, delta=_y_delta, prev_year=_y_prev_year, has_prev=_y_has_prev, unit=" MT/ha", decimals=2)
  # Fallback value if period slice empty
  if _yield_display_val is not None and not pd.isna(_yield_display_val):
    yield_display = f"{_yield_display_val:.2f} MT/ha"
  else:
    yield_display = f"{metrics['yield']:.2f} MT/ha" if metrics['yield'] else "0 MT/ha"
    if _yield_display_val is None:
      # keep dynamic subtext even when falling back to metrics
      pass

  # Harvested Area dynamic subtext (keep provincial source, but period-aware subtext)
  _harv_candidates = ["harvested_total", "harvested_annual", "harvested_area", "area_harvested", "Harvested_Area", "harvested", "area"]
  _harv_col = _pick_column(filtered_df, _harv_candidates) or _pick_column(df, _harv_candidates)
  _h_has_prev = False; _h_delta = None; _h_prev_year = None; _harv_display_val = None
  try:
    def _harv_total_for_frame(frame, col, p):
      if frame is None or frame.empty or col not in frame.columns:
        return None
      f = _filter_df_by_period(frame, p)
      if f.empty:
        return None
      if "year" in f.columns:
        per_year = pd.to_numeric(f[col], errors="coerce").groupby(f["year"]).mean().dropna()
        per_year = per_year[per_year > 0]
        return float(per_year.sum()) if not per_year.empty else None
      vals = pd.to_numeric(f[col], errors="coerce").dropna()
      return float(vals.sum()) if not vals.empty else None
    _harv_display_val = _harv_total_for_frame(filtered_df, _harv_col, period) if _harv_col else None
    if start_year == end_year and _harv_col:
      _h_prev_year = end_year - 1
      _prev_prov = df[df["year"] == _h_prev_year].copy() if "year" in df.columns else pd.DataFrame()
      _prev_col = _pick_column(_prev_prov, _harv_candidates) or _harv_col
      _h_prev = _harv_total_for_frame(_prev_prov, _prev_col, period) if _prev_col else None
      if _harv_display_val is not None and _h_prev is not None and not pd.isna(_h_prev):
        _h_delta = float(_harv_display_val - _h_prev); _h_has_prev = True
        if _harv_display_val == 0 and _h_prev == 0:
          _h_has_prev = False
  except Exception:
    _h_has_prev = False; _h_delta = None
  if start_year == end_year and _harv_display_val is None:
    _harv_sub = f"Data as of {end_year}{_period_suffix(period)}"
    if selected_muni != "All Municipalities":
      _harv_sub += f" \u2022 {selected_muni}"
    _h_has_prev = False
  else:
    _harv_sub = _kpi_subtext_yield_or_area(start_year=start_year, end_year=end_year, period=period, muni_name=selected_muni, delta=_h_delta, prev_year=_h_prev_year, has_prev=_h_has_prev, unit=" ha", decimals=0)
  harv_display = f"{_harv_display_val:,.0f} ha" if _harv_display_val is not None and not pd.isna(_harv_display_val) else f"{metrics['harvested']:,.0f} ha" if metrics['harvested'] else "0 ha"

  fc_start, fc_end, fc_months = dl.get_forecast_period(dr)
  # True empty (no forecasts) → force "No data" for Forecast Period, not months from today
  if not getattr(dr, "has_forecasts", False):
      fc_start = fc_end = "No data"
      fc_months = 0
  supply_status, supply_ratio = dl.get_supply_status(dr, end_year)
  supply_display = _supply_status_display(supply_status)

  # ---- Present-month picker (farmer logic) ----
  _hist_last = dl.get_latest_date(df)
  _today_m = pd.Timestamp.today().to_period("M").to_timestamp()
  fancy_raw = list(dr.forecast_3months_fancy) if hasattr(dr, "forecast_3months_fancy") and dr.forecast_3months_fancy else []
  regular_raw = list(dr.forecast_variety_3months) if hasattr(dr, "forecast_variety_3months") and dr.forecast_variety_3months else []
  fancy_s, regular_s = _align_forecast_arrays(fancy_raw, regular_raw)
  _fc_len = len(fancy_s) if len(fancy_s) > 0 else 3
  if not getattr(dr, "has_forecasts", False):
      forecast_months = pd.DatetimeIndex([])
      forecast_range_label = "No data"
      last_avail_month = "No data"
      next_month_name = "No data"
      is_awaiting_lgu = False
      days_stale = 999
  else:
      if _hist_last is not None and not pd.isna(_hist_last):
          _fc_start = (_hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp()
      else:
          _fc_start = _today_m
      forecast_months = pd.date_range(start=_fc_start, periods=_fc_len, freq="MS")
      if len(forecast_months) > 0:
          forecast_range_label = f"{forecast_months[0].strftime('%b %Y')} \u2013 {forecast_months[-1].strftime('%b %Y')}" if len(forecast_months) > 1 else forecast_months[0].strftime("%b %Y")
          last_avail_month = forecast_months[-1].strftime("%B %Y")
          if _today_m in forecast_months:
              next_month_name = _today_m.strftime("%B %Y")
          else:
              next_month_name = forecast_months[-1].strftime("%B %Y")
          is_awaiting_lgu = _today_m > forecast_months[-1]
          days_stale = (pd.Timestamp.today() - _hist_last).days if _hist_last is not None and not pd.isna(_hist_last) else 999
      else:
          forecast_range_label = f"{fc_start} \u2013 {fc_end}"; last_avail_month = fc_end; next_month_name = fc_end; is_awaiting_lgu = False; days_stale = 999
  # Map values to months for exact loc lookup — empty-safe (no ValueError when no forecasts)
  if len(forecast_months) == len(fancy_s) and not fancy_s.empty:
      fancy_indexed = pd.Series(fancy_s.values, index=forecast_months)
  elif fancy_raw:
      fancy_indexed = pd.Series(fancy_raw, index=forecast_months[:len(fancy_raw)])
  else:
      fancy_indexed = pd.Series(dtype=float)
  if len(forecast_months) == len(regular_s) and not regular_s.empty:
      regular_indexed = pd.Series(regular_s.values, index=forecast_months)
  elif regular_raw:
      regular_indexed = pd.Series(regular_raw, index=forecast_months[:len(regular_raw)])
  else:
      regular_indexed = pd.Series(dtype=float)
  def _forecast_value_for_month(indexed, fallback_list):
    if not indexed.empty and _today_m in indexed.index:
      v = indexed.loc[_today_m]
      if not pd.isna(v):
        return float(v)
    s = indexed.dropna()
    if not s.empty:
      return float(s.iloc[-1])
    return _safe_index(fallback_list, 0)
  fancy_forecast = _forecast_value_for_month(fancy_indexed, fancy_raw) if fancy_raw else None
  regular_forecast = _forecast_value_for_month(regular_indexed, regular_raw) if regular_raw else None
  hist = filtered_df
  if not hist.empty:
    hist_fancy = _safe_column(hist, "fancy_palay_price").mean()
    hist_regular = _safe_column(hist, "other_variety_price").mean()
    fancy_change = _pct_change(fancy_forecast, hist_fancy)
    regular_change = _pct_change(regular_forecast, hist_regular)
    if fancy_change is None: fancy_change = 0.0
    if regular_change is None: regular_change = 0.0
  else:
    fancy_change = regular_change = None
  _price_period_suf = _period_suffix(period)
  fancy_vs_label = f"vs hist avg \u2022 Forecast for: {next_month_name}{_price_period_suf}"
  regular_vs_label = f"vs hist avg \u2022 Forecast for: {next_month_name}{_price_period_suf}"

  # ---- Data-Reminder: Banner (Option1) ----
  if show_all:
    # Banner visible always for demo (both states); color indicates status
    if is_awaiting_lgu or days_stale > 95:
      st.markdown(f"""
      <div style="background: linear-gradient(135deg, #FEF2F2 0%, #FFFFFF 100%); border:1px solid #FECACA; border-left:6px solid #DC2626; border-radius:14px; padding:0.85rem 1.1rem; margin-bottom:1rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap;">
        <div><span style="font-weight:800; color:#991B1B; font-size:0.85rem;">⚠️ Data Update Needed</span><span style="color:#6B7280; font-size:0.80rem; margin-left:8px;">Last historical: <b>{_hist_last.strftime('%b %Y') if _hist_last is not None and not pd.isna(_hist_last) else 'N/A'}</b> • Forecast until <b>{last_avail_month}</b> • Today beyond horizon — LGU should encode next cycle.</span></div>
        <div style="font-size:0.75rem; color:#991B1B; background:#FEE2E2; padding:4px 10px; border-radius:999px; font-weight:700;">{days_stale} days since last update</div>
      </div>
      """, unsafe_allow_html=True)
      if st.button("Go to Import Data", key="banner_import_critical", type="primary"):
        st.session_state["lgu_page"] = "import_data"; st.rerun()
    elif days_stale > 60:
      st.markdown(f"""
      <div style="background: linear-gradient(135deg, #FFFBEB 0%, #FFFFFF 100%); border:1px solid #FDE68A; border-left:6px solid #F59E0B; border-radius:14px; padding:0.85rem 1.1rem; margin-bottom:1rem; display:flex; align-items:center; justify-content:space-between; gap:1rem;">
        <div><span style="font-weight:800; color:#92400E; font-size:0.85rem;">ℹ️ Data Due Soon</span><span style="color:#6B7280; font-size:0.80rem; margin-left:8px;">Last: <b>{_hist_last.strftime('%b %Y') if _hist_last is not None and not pd.isna(_hist_last) else 'N/A'}</b> • Forecast valid until <b>{last_avail_month}</b> — prepare next encoding.</span></div>
        <div style="font-size:0.75rem; color:#92400E; background:#FEF3C7; padding:4px 10px; border-radius:999px; font-weight:700;">{days_stale} days stale</div>
      </div>
      """, unsafe_allow_html=True)
    else:
      st.markdown(f"""
      <div style="background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%); border:1px solid #BBF7D0; border-left:6px solid #16A34A; border-radius:14px; padding:0.70rem 1.1rem; margin-bottom:1rem; display:flex; align-items:center; gap:8px;">
        <span style="font-weight:700; color:#166534; font-size:0.82rem;">✅ Data Up-to-Date</span><span style="color:#6B7280; font-size:0.80rem;">Last: <b>{_hist_last.strftime('%b %Y') if _hist_last is not None and not pd.isna(_hist_last) else 'N/A'}</b> • Forecast: <b>{forecast_range_label}</b></span>
      </div>
      """, unsafe_allow_html=True)

  # ---- Primary KPI Row (5 compact cards) - UI kept, Option2 stale styling on Forecast Period ----
  if show_all:
    _fc_accent = "#DC2626" if is_awaiting_lgu or days_stale > 95 else "#7C3AED"
    _fc_icon_bg = "rgba(220,38,38,0.12)" if is_awaiting_lgu or days_stale > 95 else "rgba(124,58,237,0.1)"
    _fc_icon_color = "#DC2626" if is_awaiting_lgu or days_stale > 95 else "#7C3AED"
    _fc_sub = f"Update Needed • {forecast_range_label}" if is_awaiting_lgu or days_stale > 95 else f"{fc_months}-Month Rolling • {forecast_range_label}"
    theme.kpi_row([
      theme.kpi_card(
        "Total Production",
        total_display,
        total_sub,
        icon_name="inventory_2", icon_bg="rgba(22,163,74,0.1)", icon_color="#16A34A", accent="#16A34A",
        compact=True,
      ),
      theme.kpi_card(
        "Average Yield",
        yield_display,
        _yield_sub,
        icon_name="eco", icon_bg="rgba(245,158,11,0.1)", icon_color="#F59E0B", accent="#F59E0B",
        compact=True,
      ),
      theme.kpi_card(
        "Harvested Area",
        harv_display,
        _harv_sub,
        icon_name="landscape", icon_bg="rgba(37,99,235,0.1)", icon_color="#2563EB", accent="#2563EB",
        compact=True,
      ),
      theme.kpi_card(
        "Supply Status",
        supply_display,
        (f"Ratio: {supply_ratio:.0f}%" if isinstance(supply_ratio, (int, float)) and supply_ratio != "N/A" else "Supply / demand"),
        icon_name="monitoring",
        icon_bg="rgba(220,38,38,0.1)" if supply_display == "At Risk" else "rgba(22,163,74,0.1)",
        icon_color="#DC2626" if supply_display == "At Risk" else "#16A34A",
        accent="#DC2626" if supply_display == "At Risk" else "#16A34A",
        compact=True,
      ),
      theme.kpi_card(
        "Forecast Period",
        "No data" if not getattr(dr, "has_forecasts", False) else (f"{forecast_months[0].strftime('%b %Y')} – {forecast_months[-1].strftime('%b %Y')}" if len(forecast_months)>0 else f"{fc_start} – {fc_end}"),
        _fc_sub if getattr(dr, "has_forecasts", False) else "No data — awaiting upload",
        icon_name="calendar_month", icon_bg=_fc_icon_bg, icon_color=_fc_icon_color, accent=_fc_accent,
        compact=True,
      ),
    ])

    # ---- Market Snapshot ----
    st.markdown(
      f'<div class="ps-market-heading">{theme.icon("storefront", "16px", "#1E5C3A")} Market Snapshot — Forecast Prices</div>',
      unsafe_allow_html=True,
    )
    m1, m2 = st.columns(2, gap="medium")
    with m1:
      if regular_forecast is not None:
        st.markdown(
          theme.market_price_card(
            "Regular Palay Forecast Price",
            regular_forecast,
            regular_change,
            vs_label=regular_vs_label,
          ),
          unsafe_allow_html=True,
        )
      else:
        st.markdown(
          '<div class="ps-market-card"><span class="ps-market-title">Regular Palay Forecast Price</span>'
          '<div class="ps-market-price" style="font-size:1rem;">No Data Available</div></div>',
          unsafe_allow_html=True,
        )
    with m2:
      if fancy_forecast is not None:
        st.markdown(
          theme.market_price_card(
            "Fancy Palay Forecast Price",
            fancy_forecast,
            fancy_change,
            vs_label=fancy_vs_label,
          ),
          unsafe_allow_html=True,
        )
      else:
        st.markdown(
          '<div class="ps-market-card"><span class="ps-market-title">Fancy Palay Forecast Price</span>'
          '<div class="ps-market-price" style="font-size:1rem;">No Data Available</div></div>',
          unsafe_allow_html=True,
        )
    if is_awaiting_lgu:
      st.caption(f"Showing latest available forecast ({last_avail_month}). Status: Pending Next Cycle Data Input.")

    theme.divider()

  # ---- Benchmark header control (like farmer) ----
  if show_all:
    st.markdown("""
    <div style="margin: 1.2rem 0 0.6rem 0; border-top: 2px solid #C8E6C9; padding-top: 0.9rem; display:flex; align-items:center; gap:10px;">
      <span style="display:flex; align-items:center; gap:6px; font-weight:700; color:#1B5E20; font-size:1.02rem; white-space:nowrap;">
        <i class="material-symbols-outlined" style="font-size:19px; color:#1B5E20; vertical-align:middle;">show_chart</i>
        Provincial Yield & Price Forecast
      </span>
      <span style="flex:1; height:1px; background:#E8F5E9; margin-left:4px;"></span>
    </div>
    """, unsafe_allow_html=True)
    hdr_col1, hdr_col2 = st.columns([0.78, 0.22], vertical_alignment="center")
    with hdr_col1:
      try:
        _benchmark_opt = st.segmented_control("Benchmark / Reference Line:", options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"], key="lgu_benchmark_toggle", default="Wala")
        if _benchmark_opt is None:
          _benchmark_opt = "Wala"
      except Exception:
        _benchmark_opt = st.radio("Benchmark / Reference Line:", options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"], horizontal=True, key="lgu_benchmark_toggle")
      if _benchmark_opt in ("3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
        _benchmark_opt = "Presyo sa Merkado"
      elif _benchmark_opt in ("NFA / DA Policy Baseline",):
        _benchmark_opt = "Target ng Gobyerno"
      elif _benchmark_opt in ("Itago (None)",):
        _benchmark_opt = "Wala"
    with hdr_col2:
      with st.popover(":material/info: Gabay sa Benchmark"):
        st.markdown("""
### **Ano ang ibig sabihin ng mga guhit (Benchmark Lines)?**
* **Presyo sa Merkado (3-Yr Rolling Avg):** Karaniwang presyo sa Bataan sa huling 12 quarters (tail 12) — inflation-aware. Yield: 10-yr mean.
* **Target ng Gobyerno:** Regular **₱19.00/kg** NFA floor, Fancy **₱23.75/kg** (19×1.25), Yield **4.50 MT/ha** DA target.
* **Wala:** Walang guhit — linya lang ng forecast/historical.
""")
  else:
    _benchmark_opt = st.session_state.get("lgu_benchmark_toggle", "Wala")

  # ---- Charts (with PERIOD + benchmark) — skeleton while Plotly figures generate ----
  if show_all:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
      with st.container(border=True):
        st.markdown("### :material/show_chart: Provincial Price Trend")
        st.caption("Historical or forecast price — dotted lines are benchmarks (dot 1.2, opacity 0.6).")
        price_subtab1, price_subtab2 = st.tabs([":material/show_chart: Historical Price Trend", ":material/query_stats: Price Forecast"])
        with price_subtab1:
          with st.skeleton(height=370):
            _fig_price_hist = _price_historical_chart(filtered_df, None, period, _benchmark_opt)
          st.plotly_chart(_fig_price_hist,
                  width="stretch", key=f"price_hist_{start_year}_{end_year}_{period}_{_benchmark_opt}")
        with price_subtab2:
          with st.skeleton(height=370):
            _fig_price_fc = _price_forecast_chart(df, dr, _benchmark_opt)
          st.plotly_chart(_fig_price_fc,
                  width="stretch", key=f"price_fc_{start_year}_{end_year}_{_benchmark_opt}")
    with c2:
      with st.container(border=True):
        st.markdown("### :material/eco: Provincial Yield Trend")
        st.caption("Historical or forecast yield — benchmarks help judge vs DA/10-yr average.")
        yield_subtab1, yield_subtab2 = st.tabs([":material/show_chart: Historical Yield Trend", ":material/query_stats: Yield Forecast"])
        with yield_subtab1:
          with st.skeleton(height=350):
            _fig_yield_hist = _yield_historical_chart(filtered_df, None, period, _benchmark_opt)
          st.plotly_chart(_fig_yield_hist,
                  width="stretch", key=f"yield_hist_{start_year}_{end_year}_{period}_{_benchmark_opt}")
        with yield_subtab2:
          with st.skeleton(height=350):
            _fig_yield_fc = _yield_forecast_chart(dr, df, _benchmark_opt)
          st.plotly_chart(_fig_yield_fc,
                  width="stretch", key=f"yield_fc_{start_year}_{end_year}_{_benchmark_opt}")
    theme.divider()

  # ---- Provincial Quarterly Production + Insight Summary ----
  if show_all:
    with st.skeleton(height=380):
      _production_quarterly(filtered_df, end_year)

    # ---- Top Municipalities + Seasonal Distribution ----
    with st.skeleton(height=400):
      _top_municipalities_and_seasonal(dr, start_year, end_year)

  # ---- Yield Forecast Summary card ----
  if show_all:
    with st.skeleton(height=180):
      _yield_summary_card(dr)

  # ---- Model Benchmark vs Baselines (defense-grade evaluation) ----
  if show_all:
    with st.skeleton(height=420):
      _model_benchmark(dr)

  # ---- Insights Narrative ----
  if show_all:
    _insights_narrative(filtered_df, dr, end_year, selected_muni, "All Types")

  # ---- Footer ----
  st.markdown("""
  <div style="text-align: center; padding: 10px 0 5px 0; font-size: 0.75rem; color: #9CA3AF;
        border-top: 1px solid #E5E7EB; margin-top: 10px;">
    <i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#9CA3AF;">agriculture</i> PalaySense LGU Dashboard • Provincial Palay Overview and Forecast Summary • v2.0
  </div>
  """, unsafe_allow_html=True)


def _model_benchmark(dr):
  """Model Benchmark vs Baselines (defense-grade evaluation section).

  Shows the selected forecast model's held-out RMSE against the Naive and
  Seasonal Naive baselines, plus the walk-forward (rolling-origin) mean ± std
  as a robustness check. Data comes from the evaluation blocks the pipeline
  writes into metrics.json.
  """
  ev = dr.model_evaluation
  if ev is None or ev.empty:
    return

  st.markdown("### :material/science: Model Benchmark vs Baselines")
  st.caption(
    "Bars = held-out test RMSE for the selected model vs Naive / Seasonal Naive baselines. "
    "Diamonds = walk-forward (rolling-origin) mean RMSE ± 1 std over multiple origins."
  )

  x = ev["Forecast"].tolist()
  wf_rmse = [v if v is not None else 0.0 for v in ev["Walk-Forward RMSE"].tolist()]
  wf_err = [v if v is not None else 0.0 for v in ev["Walk-Forward ±"].tolist()]

  fig = go.Figure()
  fig.add_trace(go.Bar(
    x=x, y=[v if v is not None else 0.0 for v in ev["RMSE (test)"].tolist()],
    name="Selected Model (test)", marker_color="#2D6A4F", width=0.22,
  ))
  fig.add_trace(go.Bar(
    x=x, y=[v if v is not None else 0.0 for v in ev["Naive RMSE (test)"].tolist()],
    name="Naive", marker_color="#D4A373", width=0.22,
  ))
  fig.add_trace(go.Bar(
    x=x, y=[v if v is not None else 0.0 for v in ev["Seas. Naive RMSE (test)"].tolist()],
    name="Seasonal Naive", marker_color="#8B9BAE", width=0.22,
  ))
  fig.add_trace(go.Scatter(
    x=x, y=wf_rmse, mode="markers+lines", name="Walk-Forward (mean ± std)",
    marker=dict(symbol="diamond", size=12, color="#1E3A8A"),
    line=dict(color="#1E3A8A", width=1.5, dash="dot"),
    error_y=dict(type="data", array=wf_err, thickness=1.5, color="#1E3A8A"),
  ))
  fig.update_layout(
    barmode="group",
    height=380,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    yaxis_title="RMSE",
    xaxis_title="",
    template="plotly_white",
  )
  st.plotly_chart(fig, use_container_width=True, key="model_benchmark")

  # Compact detail table (defense-ready numbers)
  detail = ev.copy()
  for col in detail.columns:
    if "Beats" in col:
      detail[col] = detail[col].map(
        lambda v: "Yes" if v is True else ("No" if v is False else "n/a")
      )
  st.markdown(
    '<div class="ps-market-heading">Benchmark Summary</div>',
    unsafe_allow_html=True,
  )
  st.dataframe(detail, use_container_width=True, hide_index=True)
